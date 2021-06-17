import os
import pickle
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Optional, Union

from hpc.hpc_job import HpcJobManager, JobState

from .net import Socket, Client


class ProgressServerJobInfo(object):
    def __init__(self, job_id: Union[str, int], total: int, valid_line_reg: Optional[str],
                 file: str, **_):
        """
        代表一个编码任务的进度条相关的信息
        :param job_id: HPC任务的id
        :param total: 该任务的总共进度，如果文件有多个，则该数包含各个文件的总和
        :param valid_line_reg: 获取文件有效输出行的正则表达式
        :param file: 追踪的目标文件，如有多个，用英文逗号分隔
        :param _: 忽略
        """
        self.job_id: Union[str, int] = job_id
        self.total: int = total
        self.valid_line_reg: str = valid_line_reg
        self.file: str = file

    def serialize(self) -> bytes:
        """
        将当前对象序列化
        :return: 序列化后的结果
        """
        return pickle.dumps(self)

    @staticmethod
    def deserialize(msg: bytes):
        """
        反序列化
        :param msg: ProgressServerJobInfo 对象的序列化结果
        :return: ProgressServerJobInfo
        """
        return pickle.loads(msg)


class Callback(object):
    def on_state_change(self, state: JobState, job_info: Optional[ProgressServerJobInfo], *args):
        """
        编码状态改变时的回调
        :param state:  编码状态
        :param job_info:  编码任务信息
        :param args: 额外的参数
        """
        pass

    def on_progress_change(self, state: JobState, job_info: ProgressServerJobInfo, progress: int):
        """
        编码任务进行过程中，进度改变时的回调
        :param state:  编码状态
        :param job_info: 编码任务信息
        :param progress: 当前的进度(未标准化),
        """
        pass


class Cache(object):
    """
    缓存，线程安全
    """
    lock_dict = dict()
    init_lock = Lock()

    def __init__(self, cache_file: Optional[str]):
        self.cache_file = cache_file
        self.mem_cache = dict()

        if cache_file is None:
            return

        Cache.init_lock.acquire()
        self.lock = Cache.lock_dict.get(os.path.abspath(cache_file))
        if self.lock is None:
            self.lock = Lock()
            Cache.lock_dict[os.path.abspath(cache_file)] = self.lock
        Cache.init_lock.release()

        if os.path.exists(self.cache_file) and os.path.isdir(self.cache_file):
            self.cache_file = os.path.join(cache_file, "cache.dat")
        if not os.path.exists(self.cache_file):
            os.makedirs(os.path.dirname(os.path.abspath(self.cache_file)), exist_ok=True)
            self._write(dict())

    def _read(self):
        data = dict()
        if self.cache_file is not None and os.path.exists(self.cache_file):
            with self.lock:
                with open(self.cache_file, "rb") as cache:
                    data = pickle.load(cache)
            if not isinstance(data, dict):
                data = dict()
        return data

    def _write(self, obj):
        if self.cache_file is not None:
            with self.lock:
                with open(self.cache_file, "wb+") as cache:
                    pickle.dump(obj, cache)

    def cache_load(self):
        """
        从文件加载缓存，并返回
        :return:
        """
        self.mem_cache.update(self._read())
        return self.mem_cache

    def cache_save_one(self, job_info: ProgressServerJobInfo):
        """
        缓存一个对象
        :param job_info: 待缓存对象
        """
        self.mem_cache[job_info.job_id] = job_info
        self._write(self.mem_cache)

    def cache_delete_one(self, key):
        """
        根据键，删除一个缓存对象
        :param key: 键
        """
        try:
            self.mem_cache.pop(key)
            self._write(self.mem_cache)
        except KeyError:
            pass

    def cache_delete_all(self):
        """
        清空缓存
        """
        self.mem_cache.clear()
        self._write(self.mem_cache)

    def __str__(self):
        return str(self.mem_cache)


class ProgressManager(Socket, Cache):
    def __init__(self, host: str, port: int, max_clients: int,
                 callback: Optional[Callback] = None,
                 cache_file: str = None):
        """
        创建一个Progress服务器，用于更新任务的进度，即在指定的时候回调指定的方法
        :param host: 主机名
        :param port: 端口号
        :param max_clients: 最大监听数量
        :param callback: 状态更新的回调接口
        :param cache_file: 缓存文件名称，如果指定了该参数，进度条服务器状态会保存，以便重启后能正常恢复进度条任务
        """
        if callback is None:
            callback = Callback()
        self.max_clients = max_clients
        self.current_clients = 0
        self.callback = callback
        self.executor = ThreadPoolExecutor(self.max_clients)
        Cache.__init__(self, cache_file)
        Socket.__init__(self, host=host, port=port)

    def init(self):
        # 绑定端口号
        self.socket.bind((self.host, self.port))
        # 设置最大连接数，超过后排队
        self.socket.listen(self.max_clients)
        # 加载缓存
        load_cache_dict = self.cache_load()
        for _, v in load_cache_dict.items():
            self.executor.submit(self._handle_a_job, v)

    def _handle_a_job(self, job_info: ProgressServerJobInfo):
        def count_one(filename: str):
            t = 0
            with open(filename) as fp:
                for line in fp:
                    t += 1 if job_info.valid_line_reg is None or \
                              len(job_info.valid_line_reg.strip()) == 0 or \
                              re.match(job_info.valid_line_reg, line) else 0
            return t

        self.callback.on_state_change(JobState.Configuring, job_info=job_info)
        self.cache_save_one(job_info)
        self.callback.on_state_change(JobState.Submitted, job_info=job_info)

        # State: Configuring Running Finished Failed Canceled
        job_state: JobState = HpcJobManager.view(job_info.job_id)
        while job_state in (JobState.Configuring, JobState.Queued, JobState.Submitted):
            self.callback.on_state_change(JobState.Queued, job_info=job_info)
            time.sleep(0.001)
            job_state = HpcJobManager.view(job_info.job_id)

        pre_count = 0
        job_files = job_info.file.split(",")
        sleep_time = 1
        pre_time = time.time()
        self.callback.on_state_change(JobState.Running, job_info=job_info)
        while job_state == JobState.Running:
            time.sleep(sleep_time)
            job_state = HpcJobManager.view(job_info.job_id)
            count = 0
            for file in job_files:
                count += count_one(file)
            if count != pre_count:
                pre_count = count
                self.callback.on_progress_change(JobState.Running, job_info=job_info, progress=count)
                sleep_time = (time.time() - pre_time) / 100
                pre_time = time.time()
        self.callback.on_state_change(job_state, job_info=job_info)
        self.cache_delete_one(job_info.job_id)

    def _handler(self, client: socket.socket):
        self.current_clients += 1
        job = None
        try:
            job = ProgressServerJobInfo.deserialize(Client(sock=client).recv())
            self._handle_a_job(job)
        except pickle.UnpicklingError or TypeError or OSError:
            self.callback.on_state_change(JobState.Unknown, job_info=job)
        self.current_clients -= 1

    def start(self):
        """
        开始运行进度管理器
        :return:
        """
        while True:
            try:
                # 建立客户端连接
                client_socket, _ = self.socket.accept()
                self.executor.submit(self._handler, client_socket)
            except socket.error or KeyboardInterrupt:
                self.executor.shutdown()
                self.callback.on_state_change(JobState.Unknown, job_info=None)
                break

    def stop(self):
        """
        停止进度管理器
        :return:
        """
        self.socket.close()
        self.executor.shutdown()

    @staticmethod
    def notice(job_info: ProgressServerJobInfo):
        """
        通知管理器，新建一个任务
        :param job_info: 任务描述信息
        """
        if job_info is None:
            return
        Client().send(job_info.serialize()).close()
