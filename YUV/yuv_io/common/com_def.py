from enum import Enum


class BitDepth(Enum):
    BitDepth8 = 8
    BitDepth10 = 10
    BitDepth12 = 12
    BitDepth16 = 16


class Format(Enum):
    YUV444 = 0
    YUV422 = 1
    YUV420 = 2
    YUV400 = 3



