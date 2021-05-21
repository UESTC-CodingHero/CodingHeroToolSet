import socket

from typing import Optional

HOST = socket.gethostname()
PORT = 20202
BUFFER_SIZE = 4096
MAX_CLIENTS = 4096


class Socket(object):
    def __init__(self, host: str = HOST, port: int = PORT, sock: Optional[socket.socket] = None):
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

    def send(self, msg: bytes):
        """
        发送消息
        :param msg: 消息内容
        :return:
        """
        if self.socket is not None:
            try:
                self.socket.send(msg)
            except OSError as _:
                pass
        return self

    def recv(self, buffer_size=BUFFER_SIZE) -> bytes:
        """
        接收消息
        :param buffer_size: 接收消息的buffer大小，默认为4096
        :return: 接收到的消息，或者抛出OSError异常
        """
        if self.socket is not None:
            try:
                return self.socket.recv(buffer_size)
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


class Client(Socket):
    def __init__(self, host=HOST, port=PORT, sock=None):
        # 创建 socket 对象
        super().__init__(host=host, port=port, sock=sock)

    def init(self):
        try:
            self.socket.connect((self.host, self.port))
        except ConnectionRefusedError as _:
            pass
