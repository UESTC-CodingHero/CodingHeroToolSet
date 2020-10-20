from abc import ABC

import numpy as np

from yuv_io.yuv_io import YuvIO
from .common.com_def import BitDepth
from .common.seq import Sequence, Frame


class YuvReader(YuvIO, ABC):
    def __init__(self, seq: Sequence):
        super().__init__(seq, "rb")

    def read(self) -> Frame:
        """
        读取一帧图像
        :return:
        """
        self._check_open()

        def read_frame(data_type):
            return Frame(self.sequence.width, self.sequence.height,
                         self.sequence.bit_depth, self.sequence.fmt,
                         np.fromfile(self.fp, dtype=data_type, count=self._pixel_area_y),
                         np.fromfile(self.fp, dtype=data_type, count=self._pixel_area_u),
                         np.fromfile(self.fp, dtype=data_type, count=self._pixel_area_v))

        if self.sequence.bit_depth == BitDepth.BitDepth8:
            return read_frame(np.uint8)
        else:
            return read_frame(np.uint16)

    def __next__(self):
        try:
            frame = self.read()
            return frame
        except Exception as e:
            print(e)
            raise StopIteration

    def __iter__(self):
        return self
