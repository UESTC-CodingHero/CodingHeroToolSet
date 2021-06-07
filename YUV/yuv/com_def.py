from enum import Enum
import os

import cv2
import numpy as np
import re
from typing import Optional, Union, Dict, List


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


class Component(Enum):
    COMP_Y = 0
    COMP_U = 1
    COMP_V = 2


def _clip3(v, min_v, max_v):
    return max(min_v, min(max_v, v))


def _get_uv_wh(width: int, height: int, fmt: Format):
    """
    根据YUV格式，计算UV的宽高

    :param width: 亮度分量的宽度
    :param height: 亮度分量的高度
    :param fmt: 视频帧的格式
    :return: U、V分量的宽和高
    """
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

    def __ilshift__(self, shift: int):
        self.x <<= shift
        self.y <<= shift
        self.width <<= shift
        self.height <<= shift
        return self

    def __lshift__(self, shift: int):
        r = Region(self.x, self.y, self.width, self.height)
        r <<= shift
        return r

    def __irshift__(self, shift: int):
        self.x >>= shift
        self.y >>= shift
        self.width >>= shift
        self.height >>= shift
        return self

    def __rshift__(self, shift: int):
        r = Region(self.x, self.y, self.width, self.height)
        r >>= shift
        return r

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


class Plane(MetaData):
    def __init__(self, buff: np.ndarray, bit_depth: BitDepth):
        h, w = buff.shape
        MetaData.__init__(self, Region(0, 0, w, h), fmt=Format.YUV400, bit_depth=bit_depth)
        self.buff = buff

    def __ilshift__(self, shift: int):
        self.buff <<= shift
        return self

    def __lshift__(self, shift: int):
        return Plane(self.buff << shift, bit_depth=self.bit_depth)

    def __irshift__(self, shift: int):
        self.buff += (shift >> 1)
        self.buff >>= shift
        return self

    def __rshift__(self, shift: int):
        buff = self.buff + (shift >> 1)
        buff >>= shift
        return Plane(buff, bit_depth=self.bit_depth)

    def __getitem__(self, region: Region):
        self.ensure_roi(region)
        return self.buff[region.y:region.y + region.height, region.x:region.x + region.width]

    def get(self):
        return self.buff

    @property
    def width(self):
        return self.region.width

    @property
    def height(self):
        return self.region.height

    @property
    def size(self):
        return self.width * self.height

    def cvt_bit_depth(self, target_bit_depth: BitDepth):
        bd_diff = target_bit_depth.value - self.bit_depth.value
        if bd_diff > 0:
            self.__ilshift__(bd_diff)
        elif bd_diff < 0:
            self.__irshift__(-bd_diff)

        self.bit_depth = target_bit_depth
        return self

    def update(self, buff):
        self.__init__(buff, self.bit_depth)

    def ensure_roi(self, region: Region):
        region.x = _clip3(region.x, 0, self.width)
        region.y = _clip3(region.y, 0, self.height)

        if region.x + region.width > self.width:
            region.width = self.width - region.x
        if region.y + region.height > self.height:
            region.height = self.height - region.y


class Frame(Dict[Component, Plane], MetaData):
    @property
    def width(self):
        return self.region.width

    @property
    def height(self):
        return self.region.height

    @property
    def size(self):
        return self[Component.COMP_Y].size

    def __init__(self, width: int, height: int, bit_depth: BitDepth, fmt: Format,
                 buff_y: np.ndarray,
                 buff_u: Optional[np.ndarray] = None,
                 buff_v: Optional[np.ndarray] = None):
        MetaData.__init__(self, region=Region(0, 0, width, height), fmt=fmt, bit_depth=bit_depth)
        # 将Y分量reshape到指定分辨率的二维数组
        assert width * height == buff_y.size
        self[Component.COMP_Y] = Plane(np.resize(buff_y, (self.height, self.width)), bit_depth=bit_depth)

        if self.fmt != Format.YUV400:
            # 将U、V分量reshape到指定分辨率的二维数组
            width_uv, height_uv = _get_uv_wh(self.width, self.height, self.fmt)
            assert width_uv * height_uv == buff_u.flatten().shape[0] == buff_v.flatten().shape[0]
            self[Component.COMP_U] = Plane(np.resize(buff_u, (height_uv, width_uv)), bit_depth=bit_depth)
            self[Component.COMP_V] = Plane(np.resize(buff_v, (height_uv, width_uv)), bit_depth=bit_depth)

    def __ilshift__(self, shift: int):
        buff_y = self.get(Component.COMP_Y).__ilshift__(shift).get()
        buff_u, buff_v = None, None
        if self.fmt != Format.YUV400:
            buff_u = self.get(Component.COMP_U).__ilshift__(shift).get()
            buff_v = self.get(Component.COMP_V).__ilshift__(shift).get()
        return Frame(self.width, self.height, self.bit_depth, self.fmt, buff_y, buff_u, buff_v)

    def __lshift__(self, shift: int):
        self[Component.COMP_Y] = self.get(Component.COMP_Y).__ilshift__(shift)
        if self.fmt != Format.YUV400:
            self[Component.COMP_U] = self.get(Component.COMP_U).__ilshift__(shift)
            self[Component.COMP_V] = self.get(Component.COMP_V).__ilshift__(shift)

    def __irshift__(self, shift: int):
        self[Component.COMP_Y] = self.get(Component.COMP_Y).__irshift__(shift)
        if self.fmt != Format.YUV400:
            self[Component.COMP_U] = self.get(Component.COMP_U).__irshift__(shift)
            self[Component.COMP_V] = self.get(Component.COMP_V).__irshift__(shift)
        return self

    def __rshift__(self, shift: int):
        return self.__irshift__(shift)

    def cvt_bit_depth(self, target_bit_depth: BitDepth):
        self[Component.COMP_Y] = self.get(Component.COMP_Y).cvt_bit_depth(target_bit_depth)
        if self.fmt != Format.YUV400:
            self[Component.COMP_U] = self.get(Component.COMP_U).cvt_bit_depth(target_bit_depth)
            self[Component.COMP_V] = self.get(Component.COMP_V).cvt_bit_depth(target_bit_depth)
        self.bit_depth = target_bit_depth
        return self

    def update(self, buff_y: np.ndarray, buff_u: Optional[np.ndarray] = None, buff_v: Optional[np.ndarray] = None):
        self.get(Component.COMP_Y).update(buff_y)
        if self.fmt != Format.YUV400:
            if buff_u is not None:
                self.get(Component.COMP_U).update(buff_u)
            if buff_v is not None:
                self.get(Component.COMP_V).update(buff_v)

    def __getitem__(self, item: Union[Component, Region]):
        if isinstance(item, Component):
            return self.get(item)
        w, h = item.width, item.height
        by = self[Component.COMP_Y][item]
        bu, bv = None, None
        if self.fmt != Format.YUV400:
            if self.fmt == Format.YUV420:
                item = item >> 1
            if self.fmt == Format.YUV422:
                item.y = item.y >> 1
                item.height = item.height >> 1
            bu = self[Component.COMP_U][item]
            bv = self[Component.COMP_V][item]

        return Frame(w, h, self.bit_depth, self.fmt, by, bu, bv)

    def roi(self, region: Region):
        return self.__getitem__(region)

    def ctu_all(self, ctu_size, include_incomplete_border=False) -> List:
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

    def save(self, file_name):
        if self.fmt == Format.YUV420:
            u = np.reshape(self[Component.COMP_U].get(), (self[Component.COMP_U].size // self.width, self.width))
            v = np.reshape(self[Component.COMP_V].get(), (self[Component.COMP_V].size // self.width, self.width))
            yuv = np.concatenate([self[Component.COMP_Y].get(), u, v])
            flag = cv2.COLOR_YUV2BGR_I420
        elif self.fmt == Format.YUV422:
            u = cv2.resize(self[Component.COMP_U].get(), (self.width, self.height))
            v = cv2.resize(self[Component.COMP_V].get(), (self.width, self.height))
            yuv = np.array([self[Component.COMP_Y].get(), u, v])
            yuv = np.swapaxes(yuv, 0, 1)
            yuv = np.swapaxes(yuv, 1, 2)
            flag = cv2.COLOR_YUV2BGR
        elif self.fmt == Format.YUV444:
            yuv = np.array([self[Component.COMP_Y].get(), self[Component.COMP_U].get(), self[Component.COMP_V].get()])
            yuv = np.swapaxes(yuv, 0, 1)
            yuv = np.swapaxes(yuv, 1, 2)
            flag = cv2.COLOR_YUV2BGR
        else:  # self.fmt == Format.YUV400:
            yuv = self[Component.COMP_Y].get()
            flag = None
        image = cv2.cvtColor(yuv, flag) if flag else yuv
        cv2.imwrite(file_name, image)


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
        if self.width is None or self.height is None:
            raise ValueError("Width and Height must be provided")

    def full_name(self):
        return os.path.join(self.path, self.name)
