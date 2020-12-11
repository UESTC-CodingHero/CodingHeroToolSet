import re
import socket
from concurrent.futures import ThreadPoolExecutor
import os
import time
import json

HOST = socket.gethostname()
PORT = 20202
BUFFER_SIZE = 2048
MAX_CLIENTS = 256


def to_json(job_id, total: int, valid_line_reg: str, end_line_reg: str, file: str):
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
    def __init__(self, port: int = PORT, host: str = HOST, sock=None):
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
        if self.socket is not None:
            self.socket.send(msg.encode("utf-8"))

    def recv(self, buffer_size=BUFFER_SIZE):
        if self.socket is not None:
            return str(self.socket.recv(buffer_size), encoding="utf-8")

    def close(self):
        if self.socket is not None:
            self.socket.close()


class LogCollectionServer(Socket):
    # TODO 实现日志自动化收集
    def init(self):
        pass


class EmailNotificationServer(Socket):
    # TODO 实现邮件通知
    def init(self):
        pass


class ProgressServer(Socket):
    def __init__(self, port=PORT, host=HOST, max_clients=MAX_CLIENTS, callback=None):
        # 创建 socket 对象
        self.max_clients = max_clients
        self.current_clients = 0
        self.callback = callback
        super().__init__(port, host)

    def init(self):
        # 绑定端口号
        self.socket.bind((self.host, self.port))
        # 设置最大连接数，超过后排队
        self.socket.listen(self.max_clients)

    @staticmethod
    def handler(self, client):
        msg = Client(sock=client).recv()

        job_id, total, valid_line_reg, end_line_reg, file = from_json(msg)
        print(time.strftime("%Y-%m-%d %H:%M:%S"), job_id, os.path.basename(file))
        pre_count = 0
        sleep_time = 1

        # 如果10天还未运行（说明被用户取消了），则取消对该任务的监控
        # State: Configuring Running Finished Failed Canceled
        day10 = 10 * 24 * 60 * 60
        while pre_count < day10:
            if os.path.exists(file):
                break
            time.sleep(sleep_time)
            pre_count += 1
        pre_count = 0
        sleep_time = 1
        start_time = -1
        while True:
            end = False
            if not os.path.exists(file):
                break
            with open(file) as fp:
                count = 0
                num_of_lines = 0
                for line in fp:
                    num_of_lines += 1
                    m = re.match(valid_line_reg, line)
                    if m:
                        count += 1
                    if re.match(end_line_reg, line):
                        assert count == total
                        count = total
                        end = True
                        break
                if count != pre_count:
                    if start_time == -1:
                        start_time = time.time()
                    else:
                        sleep_time = (time.time() - start_time) / 5
                        start_time = time.time()
                    pre_count = count
                    if self.callback is not None and callable(self.callback):
                        self.callback(job_id, count * 100 / total, f"{count}/{total}")
                elif start_time == -1 and num_of_lines > 0:
                    start_time = time.time()
            if end:
                # TODO log parser or log merge
                # 经过这儿的才是正常完成的任务
                break
            time.sleep(sleep_time)
        print(time.strftime("%Y-%m-%d %H:%M:%S"), job_id, os.path.basename(file), "Finished")
        self.current_clients -= 1

    def start(self):
        print(time.strftime("%Y-%m-%d %H:%M:%S"), "Start Server...")
        executor = ThreadPoolExecutor(self.max_clients)
        while True:
            # 建立客户端连接
            try:
                client_socket, _ = self.socket.accept()
                self.current_clients += 1
                executor.submit(ProgressServer.handler, self, client_socket)
                if self.current_clients < 0:
                    break
            except Exception as _:
                pass
        executor.shutdown()
        print(time.strftime("%Y-%m-%d %H:%M:%S"), "Stop Server...")


class Client(Socket):
    def __init__(self, port=PORT, host=HOST, sock=None):
        # 创建 socket 对象
        super().__init__(port, host, sock)

    def init(self):
        self.socket.connect((self.host, self.port))
