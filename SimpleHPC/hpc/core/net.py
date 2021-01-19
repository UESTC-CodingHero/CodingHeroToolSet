import json
import shelve
import os
import re
import socket
import time
from abc import ABCMeta
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Optional, Union

from hpc.core.hpc_job import HpcJobManager, HpcJobState

HOST = socket.gethostname()
PORT = 20202
BUFFER_SIZE = 2048
MAX_CLIENTS = 2048


class ProgressServerJobInfo(object):
    def __init__(self, job_id: Union[str, int], total: int, valid_line_reg: Optional[str], end_line_reg: Optional[str],
                 file: str):
        self.job_id: Union[str, int] = job_id
        self.total: int = total
        self.valid_line_reg: str = valid_line_reg
        self.end_line_reg: str = end_line_reg
        self.file: str = file


def to_json(job_id: Union[str, int], total: int, valid_line_reg: Optional[str], end_line_reg: Optional[str], file: str):
    temp = dict()
    temp["0"] = job_id
    temp["1"] = total
    temp["2"] = valid_line_reg
    temp["3"] = end_line_reg
    temp["4"] = file
    return json.dumps(temp)


def from_json(msg: str):
    temp = json.loads(msg)
    return temp["0"], int(temp["1"]), temp["2"], temp["3"], temp["4"]


class Socket(object):
    def __init__(self, port: int = PORT, host: str = HOST, sock: Optional[socket.socket] = None):
        """
        使用给定的参数，创建一个TCP Socket或者封装一个已存在的原始socket
        :param port: socket端口号，默认为20202
        :param host: 主机名，默认为当前主机名
        :param sock: 原始socket
        """
        self.port = port
        self.host = host
        if sock is None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.init()
        else:
            self.socket = sock

    def init(self):
        raise NotImplementedError

    def send(self, msg: str):
        """
        发送消息
        :param msg: 消息内容
        :return:
        """
        if self.socket is not None:
            try:
                self.socket.send(msg.encode("utf-8"))
            except OSError as _:
                pass
        return self

    def recv(self, buffer_size=BUFFER_SIZE):
        """
        接收消息
        :param buffer_size: 接收消息的buffer大小，默认为2048
        :return: 接收到的消息，或者抛出OSError异常
        """
        if self.socket is not None:
            try:
                return str(self.socket.recv(buffer_size), encoding="utf-8")
            except OSError as e:
                raise e

    def close(self):
        """
        关闭当前socket
        :return:
        """
        if self.socket is not None:
            self.socket.close()
            self.socket = None


class LogCollectionServer(Socket):
    # TODO 实现日志自动化收集
    def init(self):
        pass


class EmailNotificationServer(Socket):
    # TODO 实现邮件通知
    def init(self):
        pass


class ProgressServer(Socket):
    lock = Lock()
    timeout = 10

    class Callback(metaclass=ABCMeta):

        def on_error(self, e: Exception):
            """
            用于处理异常
            :param e: 异常消息
            :return:
            """
            raise NotImplemented

        def on_submit(self, job_id, **kwargs):
            """
            用于任务提交时的回调
            :return:
            """
            raise NotImplemented

        def on_waiting(self):
            """
            用于任务等待时的回调
            :return:
            """
            raise NotImplemented

        def on_running(self):
            """
            用于任务开始运行时的回调
            :return:
            """
            raise NotImplemented

        def on_update(self, job_id: Union[str, int], progress: Union[int, float], msg: str):
            """
            用于更新进度条的回调
            :param job_id: 任务ID
            :param progress: 进度，百分制
            :param msg: 进度说明
            """
            raise NotImplemented

        def on_finish(self, state: HpcJobState):
            """
            用于任务结束时的回调
            @:param state: 任务结束时的状态
            :return:
            """
            raise NotImplemented

    def __init__(self, port: int = PORT, host: str = HOST, max_clients: int = MAX_CLIENTS, callback: Callback = None,
                 cache_file: str = None):
        """
        创建一个Progress服务器，用于更新任务的进度，即在指定的时候回调指定的方法
        :param port: 端口号，默认为20202
        :param host: 主机名，默认为当前主机名
        :param max_clients: 最大监听数量，默认为2048
        :param callback: 更新进度条的回调接口
        :param cache_file: 缓存文件名称，如果指定了该参数，进度条服务器状态会保存，以便重启后能正常恢复进度条任务
        """
        self.max_clients = max_clients
        self.current_clients = 0
        self.callback = callback
        self.executor = ThreadPoolExecutor(self.max_clients)
        self.states = dict()
        self.cache_file = cache_file
        super().__init__(port, host)

    def init(self):
        # 绑定端口号
        self.socket.bind((self.host, self.port))
        # 设置最大连接数，超过后排队
        self.socket.listen(self.max_clients)
        # 加载缓存
        if self.cache_file is not None:
            with shelve.open(self.cache_file) as cache:
                for k, v in cache.items():
                    self.executor.submit(self.handle_a_job, v)

    def handle_a_job(self, job_info: ProgressServerJobInfo):
        def cache_if_possible():
            if self.cache_file:
                with shelve.open(self.cache_file) as cache:
                    # clear firstly, in order to reduce space or memory.
                    # do not call cache.clear(), for it does not clear the cache in fact
                    for k in cache.keys():
                        del cache[k]
                    for k, v in self.states.items():
                        cache[str(k)] = v

        ProgressServer.lock.acquire(timeout=ProgressServer.timeout)
        self.states[job_info.job_id] = job_info
        cache_if_possible()
        ProgressServer.lock.release()
        if self.callback is not None:
            self.callback.on_submit(job_info.job_id, total=job_info.total, valid_line_reg=job_info.valid_line_reg,
                                    end_line_reg=job_info.end_line_reg,
                                    file=job_info.file)
        sleep_time = 1

        # State: Configuring Running Finished Failed Canceled
        job_state: HpcJobState = HpcJobManager.view(job_info.job_id)
        while job_state == HpcJobState.Configuring or job_state == HpcJobState.Queued or job_state == HpcJobState.Submitted:
            time.sleep(sleep_time)
            if self.callback is not None:
                self.callback.on_waiting()
            job_state = HpcJobManager.view(job_info.job_id)
        pre_count = 0
        count = 0
        sleep_time = 1
        start_time = -1
        if self.callback is not None:
            self.callback.on_running()
        while job_state == HpcJobState.Running:
            time.sleep(sleep_time)
            job_state = HpcJobManager.view(job_info.job_id)
            if not os.path.exists(job_info.file):
                job_state = HpcJobManager.view(job_info.job_id)
                break
            with open(job_info.file) as fp:
                count = 0
                num_of_lines = 0
                for line in fp:
                    num_of_lines += 1
                    m = job_info.valid_line_reg is None or re.match(job_info.valid_line_reg, line)
                    if m:
                        count += 1
                if count != pre_count:
                    if start_time != -1:
                        sleep_time = (time.time() - start_time) / 20
                    start_time = time.time()
                    pre_count = count
                    if self.callback is not None:
                        self.callback.on_update(job_info.job_id, count * 100 / job_info.total,
                                                f"{count}/{job_info.total}")
                elif start_time == -1 and num_of_lines > 0:
                    start_time = time.time()
        if self.callback is not None:
            self.callback.on_finish(job_state)
            if count == job_info.total:
                self.callback.on_update(job_info.job_id, 100,
                                        f"Finished")
        ProgressServer.lock.acquire(timeout=ProgressServer.timeout)
        self.states.pop(job_info.job_id)
        cache_if_possible()
        ProgressServer.lock.release()

    def handler(self, client: socket.socket):
        try:
            msg = Client(sock=client).recv()
            state = ProgressServerJobInfo(*from_json(msg))
            self.handle_a_job(state)
        except json.decoder.JSONDecodeError or TypeError or OSError as e:
            if self.callback is not None:
                self.callback.on_error(e)
        self.current_clients -= 1

    def start(self):
        while True:
            try:
                # 建立客户端连接
                client_socket, _ = self.socket.accept()
                self.current_clients += 1
                self.executor.submit(self.handler, client_socket)
            except socket.error or KeyboardInterrupt as e:
                print(e)
                break


class Client(Socket):
    def __init__(self, port=PORT, host=HOST, sock=None):
        # 创建 socket 对象
        super().__init__(port, host, sock)

    def init(self):
        try:
            self.socket.connect((self.host, self.port))
        except ConnectionRefusedError as _:
            pass


class Progress(object):
    @staticmethod
    def notice(job_id: int, total: int, valid_line_reg: Optional[str], end_line_reg: Optional[str], file: str):
        if file is None or file == os.devnull or total < 1 or job_id < 0:
            return
        Client().send(to_json(job_id, total, valid_line_reg, end_line_reg, file)).close()


if __name__ == '__main__':
    Progress.notice(1020, 3, "V", "E", "C:\\Users\\XueliCHENG\\Desktop\\test.txt")
