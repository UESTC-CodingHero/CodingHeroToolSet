import re
import socket
from concurrent.futures import ThreadPoolExecutor
import os
import time
import json
import logging
from hpc.core.hpc_job import HpcJobManager, HpcJobState
from typing import Optional

HOST = socket.gethostname()
PORT = 20202
BUFFER_SIZE = 2048
MAX_CLIENTS = 1024


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
            try:
                self.socket.send(msg.encode("utf-8"))
            except OSError as _:
                pass
        return self

    def recv(self, buffer_size=BUFFER_SIZE):
        if self.socket is not None:
            try:
                return str(self.socket.recv(buffer_size), encoding="utf-8")
            except OSError as e:
                raise e

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
        logging.basicConfig(level=logging.DEBUG,
                            format="[%(asctime)s] [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    def init(self):
        # 绑定端口号
        self.socket.bind((self.host, self.port))
        # 设置最大连接数，超过后排队
        self.socket.listen(self.max_clients)

    @staticmethod
    def handler(self, client):
        msg = Client(sock=client).recv()
        try:
            job_id, total, valid_line_reg, end_line_reg, file = from_json(msg)
            logging.info(f"{job_id} {os.path.basename(file)}")
            sleep_time = 1

            # State: Configuring Running Finished Failed Canceled
            state: HpcJobState = HpcJobManager.view(job_id)
            while state == HpcJobState.Configuring or state == HpcJobState.Queued or state == HpcJobState.Submitted:
                time.sleep(sleep_time)
                state = HpcJobManager.view(job_id)
            pre_count = 0
            sleep_time = 1
            start_time = -1
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
                            if count != total:
                                logging.warning("Parsing Over. But the count is mismatch")
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
                        if self.callback is not None and callable(self.callback):
                            self.callback(job_id, count * 100 / total, f"{count}/{total}")
                    elif start_time == -1 and num_of_lines > 0:
                        start_time = time.time()
                time.sleep(sleep_time)
            logging.info(f"{job_id} {os.path.basename(file)} {state.value}")
        except json.decoder.JSONDecodeError or TypeError as _:
            logging.error(f"Invalid Message: {msg}")
        self.current_clients -= 1

    def start(self):
        logging.info("Start Server...")
        executor = ThreadPoolExecutor(self.max_clients)
        while True:
            try:
                # 建立客户端连接
                client_socket, _ = self.socket.accept()
                self.current_clients += 1
                executor.submit(ProgressServer.handler, self, client_socket)
            except socket.error or KeyboardInterrupt as e:
                print(e)
                break
        executor.shutdown()
        logging.info("Stop Server...")


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
        Client().send(to_json(job_id, total, valid_line_reg, end_line_reg, file))


if __name__ == '__main__':
    Client().send(to_json(1020, 3, "V", "E", "C:\\Users\\XueliCHENG\\Desktop\\test.txt")).close()
