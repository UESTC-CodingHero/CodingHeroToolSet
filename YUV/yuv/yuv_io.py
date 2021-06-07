import os
from abc import ABC
from typing import BinaryIO, Optional, NoReturn, IO, ClassVar

import numpy as np

from yuv.com_def import BitDepth, Format, Component
from yuv.com_def import Sequence, Frame, _get_uv_wh


class YuvIO(object):
    def __init__(self, seq: Sequence, mode: str):
        assert 'b' in mode
        self.sequence: Sequence = seq
        self.mode: str = mode
        self.fp: Optional[BinaryIO] = None
        # set the size for each plane
        uv_w, uv_h = _get_uv_wh(seq.width, seq.height, seq.fmt)
        self._pixel_area_y = seq.width * seq.height
        self._pixel_area_u = uv_w * uv_h
        self._pixel_area_v = self._pixel_area_u
        self._pixel_area_yuv = self._pixel_area_y + self._pixel_area_u + self._pixel_area_v

        shift = 0 if seq.bit_depth == BitDepth.BitDepth8 else 1
        self._frame_size_y = self._pixel_area_y << shift
        self._frame_size_u = self._pixel_area_u << shift
        self._frame_size_v = self._pixel_area_v << shift
        self._frame_size_yuv = self._frame_size_y + self._frame_size_u + self._frame_size_v

        self.open()

    def open(self) -> NoReturn:
        """
        如果IO流未打开，则打开IO流
        :return:
        """
        if not os.path.exists(self.sequence.path):
            os.makedirs(self.sequence.path)
        if self.fp is None:
            self.fp: IO = open(self.sequence.full_name(), self.mode)

    def close(self) -> NoReturn:
        """
        如果文件IO流已打开，则关闭文件的IO流
        :return:
        """
        if self.fp is not None:
            self.fp.close()
            self.fp = None

    def seek(self, frames) -> NoReturn:
        """
        移动文件指针，以帧为单位移动
        :param frames: 移动的帧数，负数表示向前移动，正数表示向后移动
        :return:
        """
        return self.fp.seek(frames * self._frame_size_yuv, os.SEEK_CUR)

    def read(self) -> Frame:
        raise NotImplemented

    def write(self, frame: Frame):
        raise NotImplemented

    def frames(self) -> int:
        """
        获取当前序列的总帧数
        :return: 当前序列的总帧数
        """
        # 记录原始的文件指针位置
        old_pos = self.fp.tell()

        # 移动文件指针到文件尾，并计算文件大小
        self.fp.seek(0, os.SEEK_END)
        total_bytes = self.fp.tell()

        # 恢复文件指针
        self.fp.seek(old_pos, os.SEEK_SET)

        # 计算总帧数
        return total_bytes // self._frame_size_yuv

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return self


class YuvReader(YuvIO, ABC):
    def __init__(self, seq: Sequence):
        super().__init__(seq, "rb")

    def read(self) -> Frame:
        """
        读取一帧图像
        :return:
        """

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

    def __next__(self) -> Frame:
        try:
            return self.read()
        except Exception as e:
            print(e)
            raise StopIteration

    def __iter__(self):
        return self


class YuvWriter(YuvIO, ABC):
    def __init__(self, seq: Sequence, append: bool = False):
        if append:
            super().__init__(seq, "ab+")
        else:
            super().__init__(seq, "wb+")

    def write(self, frame: Frame) -> ClassVar:
        """
        向文件写入一帧图像
        :param frame:
        :return:
        """
        frame[Component.COMP_Y].get().tofile(self.fp)
        if frame.fmt != Format.YUV400:
            frame[Component.COMP_U].get().tofile(self.fp)
            frame[Component.COMP_V].get().tofile(self.fp)
        return self
