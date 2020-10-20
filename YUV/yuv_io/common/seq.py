from .com_def import Format, BitDepth
import os
import numpy as np


def get_uv_property(width: int, height: int, fmt: Format):
    # TODO: 根据YUV格式，计算UV的宽高
    if fmt == Format.YUV444:
        width_uv = width
        height_uv = height
    elif fmt == Format.YUV422:
        width_uv = width
        height_uv = height
    elif fmt == Format.YUV420:
        width_uv = width >> 1
        height_uv = height >> 1
    else:
        width_uv = 0
        height_uv = 0
    return width_uv, height_uv


class Frame(object):
    def __init__(self, width: int, height: int, bit_depth: BitDepth, fmt: Format,
                 buff_y: np.ndarray, buff_u: np.ndarray, buff_v: np.ndarray):
        self.width: int = width
        self.height: int = height
        self.bit_depth: BitDepth = bit_depth
        self.fmt: Format = fmt
        # 将Y分量reshape到指定分辨率的二维数组
        assert width * height == buff_y.flatten().shape[0]
        self.buff_y: np.ndarray = np.resize(buff_y, (self.height, self.width))

        # 将U、V分量reshape到指定分辨率的二维数组
        width_uv, height_uv = get_uv_property(self.width, self.height, self.fmt)
        assert width_uv * height_uv == buff_u.flatten().shape[0] == buff_v.flatten().shape[0]
        self.buff_u: np.ndarray = np.resize(buff_u, (height_uv, width_uv))
        self.buff_v: np.ndarray = np.resize(buff_v, (height_uv, width_uv))

    def __str__(self):
        return "shape: " + str(self.buff_y.shape)

    def __ilshift__(self, other: int):
        self.buff_y <<= other
        self.buff_u <<= other
        self.buff_v <<= other
        return self

    def __lshift__(self, other: int):
        return self.__ilshift__(other)

    def __irshift__(self, other: int):
        self.buff_y += (other >> 1)
        self.buff_u += (other >> 1)
        self.buff_v += (other >> 1)

        self.buff_y >>= other
        self.buff_u >>= other
        self.buff_v >>= other
        return self

    def __rshift__(self, other: int):
        return self.__irshift__(other)

    def cvt_bit_depth(self, target_bit_depth: BitDepth):
        bd_diff = target_bit_depth.value - self.bit_depth.value
        if bd_diff > 0:
            self << bd_diff
        elif bd_diff < 0:
            self >> (-bd_diff)

        self.bit_depth = target_bit_depth

    def roi(self, x, y, w, h):
        _w, _h = w, h = min(w, self.width), min(h, self.height)

        by = self.buff_y[y:y + h, x:x + w]
        x, y = get_uv_property(x, y, self.fmt)
        w, h = get_uv_property(w, h, self.fmt)

        bu = self.buff_u[y:y + h, x:x + w]
        bv = self.buff_v[y:y + h, x:x + w]

        return Frame(_w, _h, self.bit_depth, self.fmt, by, bu, bv)


class Sequence(object):
    def __init__(self, path: str, name: str, width: int, height: int, fmt: Format, bit_depth: BitDepth, fps: int):
        self.path = path
        self.name = name
        self.width = width
        self.height = height
        self.fmt = fmt
        self.bit_depth = bit_depth
        self.fps = fps

    def full_name(self):
        return os.path.join(self.path, self.name)
