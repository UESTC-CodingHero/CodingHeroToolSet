from .common.seq import Sequence, Frame
from typing import BinaryIO, Optional
import os
import numpy as np


class YuvWriter(object):
    def __init__(self, seq: Sequence, append: bool = False):
        self.sequence: Sequence = seq
        self.append: bool = append
        self.fp: Optional[BinaryIO] = None

    def open(self):
        if self.fp is None:
            if self.append:
                self.fp: BinaryIO = open(self.sequence.full_name(), "ab")
            else:
                self.fp: BinaryIO = open(self.sequence.full_name(), "wb+")

    def write(self, frame: Frame):
        if self.fp is None:
            self.open()
        frame.buff_y.tofile(self.fp)
        frame.buff_u.tofile(self.fp)
        frame.buff_v.tofile(self.fp)
