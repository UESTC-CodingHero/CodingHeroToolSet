from .common.seq import Sequence, Frame
from .common.com_def import BitDepth, Format
from typing import BinaryIO, Optional
import os
import numpy as np


class YuvReader(object):
    def __init__(self, seq: Sequence):
        self.sequence: Sequence = seq
        self.fp: Optional[BinaryIO] = None

        # set the size for each plane
        _pixel_area_y = seq.width * seq.height
        if seq.fmt == Format.YUV444:
            _pixel_area_u = _pixel_area_y
            _pixel_area_v = _pixel_area_y
        elif seq.fmt == Format.YUV422:
            _pixel_area_u = _pixel_area_y
            _pixel_area_v = _pixel_area_y
        elif seq.fmt == Format.YUV420:
            _pixel_area_u = _pixel_area_y >> 2
            _pixel_area_v = _pixel_area_u
        else:
            _pixel_area_u = 0
            _pixel_area_v = 0
        shift = 0 if seq.bit_depth == BitDepth.BitDepth8 else 0

        self._frame_size_y = _pixel_area_y << shift
        self._frame_size_u = _pixel_area_u << shift
        self._frame_size_v = _pixel_area_v << shift

        self._frame_size_yuv = self._frame_size_y + self._frame_size_u + self._frame_size_v

    def open(self):
        if self.fp is None:
            self.fp: BinaryIO = open(self.sequence.full_name(), "rb")

    def seek(self, frames):
        if self.fp is None:
            raise IOError("The file is not opened")
        self.fp.seek(frames * self._frame_size_yuv, os.SEEK_CUR)

    def read(self) -> Frame:
        if self.fp is None:
            self.open()

        def read_frame(dtype):
            return Frame(self.sequence.width, self.sequence.height,
                         self.sequence.bit_depth, self.sequence.fmt,
                         np.fromfile(self.fp, dtype=dtype, count=self._frame_size_y),
                         np.fromfile(self.fp, dtype=dtype, count=self._frame_size_u),
                         np.fromfile(self.fp, dtype=dtype, count=self._frame_size_v))

        if self.sequence.bit_depth == BitDepth.BitDepth8:
            return read_frame(np.uint8)
        else:
            return read_frame(np.uint16)

    def __next__(self):
        try:
            frame = self.read()
            return frame
        except:
            raise StopIteration

    def __iter__(self):
        return self
