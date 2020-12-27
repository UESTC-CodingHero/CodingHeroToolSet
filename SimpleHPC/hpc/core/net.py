import json
import os
import re
import socket
import time
from abc import ABCMeta
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Union

from hpc.core.hpc_job import HpcJobManager, HpcJobState

HOST = socket.gethostname()
PORT = 20202
BUFFER_SIZE = 2048
MAX_CLIENTS = 2048


def to_json(job_id: int, total: int, valid_line_reg: Optional[str], end_line_reg: Optional[str], file: str):
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

    def __init__(self, port: int = PORT, host: str = HOST, max_clients: int = MAX_CLIENTS, callback: Callback = None):
        """
        创建一个Progress服务器，用于更新任务的进度，即在指定的时候回调指定的方法
        :param port: 端口号，默认为20202
        :param host: 主机名，默认为当前主机名
        :param max_clients: 最大监听数量，默认为2048
        :param callback: 更新进度条的回调接口
        """
        self.max_clients = max_clients
        self.current_clients = 0
        self.callback = callback
        super().__init__(port, host)

    def init(self):
        # 绑定端口号
        self.socket.bind((self.host, self.port))
        # 设置最大连接数，超过后排队
        self.socket.listen(self.max_clients)

    def handler(self, client: socket.socket):
        try:
            msg = Client(sock=client).recv()
            job_id, total, valid_line_reg, end_line_reg, file = from_json(msg)
            if self.callback is not None:
                self.callback.on_submit(job_id, total=total, valid_line_reg=valid_line_reg, end_line_reg=end_line_reg,
                                        file=file)
            sleep_time = 1

            # State: Configuring Running Finished Failed Canceled
            state: HpcJobState = HpcJobManager.view(job_id)
            while state == HpcJobState.Configuring or state == HpcJobState.Queued or state == HpcJobState.Submitted:
                time.sleep(sleep_time)
                if self.callback is not None:
                    self.callback.on_waiting()
                state = HpcJobManager.view(job_id)
            pre_count = 0
            sleep_time = 1
            start_time = -1
            if self.callback is not None:
                self.callback.on_running()
            while state == HpcJobState.Running:
                if not os.path.exists(file):
                    state = HpcJobManager.view(job_id)
                    break
                with open(file) as fp:
                    count = 0
                    num_of_lines = 0
                    for line in fp:
                        num_of_lines += 1
                        m = valid_line_reg is None or re.match(valid_line_reg, line)
                        if m:
                            count += 1
                        if end_line_reg is not None and re.match(end_line_reg, line):
                            state = HpcJobManager.view(job_id)
                        elif end_line_reg is None:
                            state = HpcJobManager.view(job_id)
                    if count != pre_count:
                        if start_time == -1:
                            start_time = time.time()
                        else:
                            sleep_time = (time.time() - start_time) / 5
                            start_time = time.time()
                        pre_count = count
                        if self.callback is not None:
                            self.callback.on_update(job_id, count * 100 / total, f"{count}/{total}")
                    elif start_time == -1 and num_of_lines > 0:
                        start_time = time.time()
                time.sleep(sleep_time)
            if self.callback is not None:
                self.callback.on_finish(state)
        except json.decoder.JSONDecodeError or TypeError or OSError as e:
            if self.callback is not None:
                self.callback.on_error(e)
        self.current_clients -= 1

    def start(self):
        with ThreadPoolExecutor(self.max_clients) as executor:
            while True:
                try:
                    # 建立客户端连接
                    client_socket, _ = self.socket.accept()
                    self.current_clients += 1
                    executor.submit(self.handler, client_socket)
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
