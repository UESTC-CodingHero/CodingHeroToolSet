from abc import ABC

from yuv_io.yuv_io import YuvIO
from .common.seq import Sequence, Frame


class YuvWriter(YuvIO, ABC):
    def __init__(self, seq: Sequence, append: bool = False):
        if append:
            super().__init__(seq, "ab")
        else:
            super().__init__(seq, "wb+")

    def write(self, frame: Frame):
        """
        向文件写入一帧图像
        :param frame:
        :return:
        """
        if self.fp is None:
            self.open()
        frame.buff_y.tofile(self.fp)
        frame.buff_u.tofile(self.fp)
        frame.buff_v.tofile(self.fp)
