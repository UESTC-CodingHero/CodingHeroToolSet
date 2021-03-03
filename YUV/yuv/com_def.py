from enum import Enum
import os
import numpy as np
import re
from typing import Optional, Union


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


class Region(object):
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.width = w
        self.height = h

    def __eq__(self, other):
        return (self.x == other.x and
                self.y == other.y and
                self.width == other.width and
                self.height == other.height)

    def __str__(self):
        return f"{self.x}, {self.y}, {self.width}, {self.height}"


class MetaData(object):
    def __init__(self, region: Region, fmt: Format = None, bit_depth: BitDepth = None):
        self.region = region
        self.fmt = fmt
        self.bit_depth = bit_depth

    def __eq__(self, other):
        return (self.region == other.region and
                self.fmt == other.fmt and
                self.bit_depth == other.bit_depth)

    def uv_scale(self):
        if self.fmt == Format.YUV400:
            raise ValueError("YUV400 no uv")
        if self.fmt == Format.YUV444:
            return 0, 0
        if self.fmt == Format.YUV420:
            return 1, 1
        if self.fmt == Format.YUV422:
            return 1, 0


class Frame(Region, MetaData):
    def __init__(self, width: int, height: int, bit_depth: BitDepth, fmt: Format,
                 buff_y: np.ndarray,
                 buff_u: Optional[np.ndarray] = None,
                 buff_v: Optional[np.ndarray] = None):
        Region.__init__(self, 0, 0, width, height)
        MetaData.__init__(self, self, fmt, bit_depth)

        # 将Y分量reshape到指定分辨率的二维数组
        assert width * height == buff_y.size
        self.buff_y: np.ndarray = np.resize(buff_y, (self.height, self.width))

        if self.fmt != Format.YUV400:
            # 将U、V分量reshape到指定分辨率的二维数组
            width_uv, height_uv = get_uv_property(self.width, self.height, self.fmt)
            assert width_uv * height_uv == buff_u.flatten().shape[0] == buff_v.flatten().shape[0]
            self.buff_u: np.ndarray = np.resize(buff_u, (height_uv, width_uv))
            self.buff_v: np.ndarray = np.resize(buff_v, (height_uv, width_uv))

    def __ilshift__(self, shift: int):
        self.buff_y <<= shift
        if self.fmt != Format.YUV400:
            self.buff_u <<= shift
            self.buff_v <<= shift
        return self

    def __lshift__(self, shift: int):
        return self.__ilshift__(shift)

    def __irshift__(self, shift: int):
        self.buff_y += (shift >> 1)
        self.buff_y >>= shift

        if self.fmt != Format.YUV400:
            self.buff_u += (shift >> 1)
            self.buff_v += (shift >> 1)
            self.buff_u >>= shift
            self.buff_v >>= shift
        return self

    def __rshift__(self, shift: int):
        return self.__irshift__(shift)

    def cvt_bit_depth(self, target_bit_depth: BitDepth):
        bd_diff = target_bit_depth.value - self.bit_depth.value
        if bd_diff > 0:
            self << bd_diff
        elif bd_diff < 0:
            self >> (-bd_diff)

        self.bit_depth = target_bit_depth

    def ensure_roi(self, region: Region):
        region.x = min(max(region.x, 0), self.width)
        region.y = min(max(region.y, 0), self.height)

        if region.x + region.width > self.width:
            region.width = self.width - region.x
        if region.y + region.height > self.height:
            region.height = self.height - region.y

    def update(self, y, u=None, v=None):
        self.buff_y = y
        if self.fmt != Format.YUV400:
            if u is not None:
                self.buff_u = u
            if v is not None:
                self.buff_v = v
        else:
            self.buff_u = None
            self.buff_v = None

    def __getitem__(self, item: Union[int, Region]):
        if isinstance(item, int):
            if item == 0:
                return self.buff_y
            elif item == 1:
                return self.buff_u
            elif item == 2:
                return self.buff_v
            else:
                raise ValueError("Supported component is [0, 1, 2]. ")
        self.ensure_roi(item)
        x, y, w, h = item.x, item.y, item.width, item.height
        _w, _h = w, h = min(w, self.width), min(h, self.height)

        by = self.buff_y[y:y + h, x:x + w]

        bu, bv = None, None
        if self.fmt != Format.YUV400:
            x, y = get_uv_property(x, y, self.fmt)
            w, h = get_uv_property(w, h, self.fmt)
            bu = self.buff_u[y:y + h, x:x + w]
            bv = self.buff_v[y:y + h, x:x + w]

        return Frame(_w, _h, self.bit_depth, self.fmt, by, bu, bv)

    def roi(self, region: Region):
        return self[region]

    def ctu_all(self, ctu_size, include_incomplete_border=False):
        ctu = list()
        ih = self.height // ctu_size
        iw = self.width // ctu_size
        if include_incomplete_border:
            ih += 1 if self.height % ctu_size != 0 else 0
            iw += 1 if self.width % ctu_size != 0 else 0
        for h in range(ih):
            for w in range(iw):
                x = w * ctu_size
                y = h * ctu_size
                region = Region(x, y, ctu_size, ctu_size)
                ctu.append(self.roi(region))
        return ctu


class Sequence(Region, MetaData):
    def __init__(self, seq_path: str, name: str, width: int = None, height: int = None,
                 fps_num: int = None, fps_den: int = 1,
                 bit_depth: BitDepth = BitDepth.BitDepth8, fmt: Format = Format.YUV420):
        Region.__init__(self, 0, 0, width, height)
        MetaData.__init__(self, self, fmt, bit_depth)
        self.path = seq_path
        self.name = name
        self.fmt = fmt
        self.bit_depth = bit_depth
        self.fps_num = fps_num
        self.fps_den = fps_den
        m = re.match(r".+?_(\d+)x(\d+)_(\d+)(_\S+)?.yuv", name)
        if m and self.width is None:
            self.width = int(m.group(1))
        if m and self.height is None:
            self.height = int(m.group(2))
        if m and self.fps_num is None:
            self.fps_num = int(m.group(3))

    def full_name(self):
        return os.path.join(self.path, self.name)
