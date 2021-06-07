import copy
from enum import Enum
from typing import List, NoReturn, Optional, Union

import cv2
import numpy as np

from yuv.com_def import Region, MetaData, Plane, Frame, Sequence, Format, Component
from yuv.yuv_io import YuvReader, YuvWriter


class Converter(object):
    @staticmethod
    def rgb2yuv(rgb: tuple):
        # @formatter:off
        matrix = np.array([
            [ 0.299,     0.587,     0.114],
            [-0.169,    -0.331,     0.499],
            [ 0.499,    -0.418,    -0.0813]
        ])
        # @formatter:on
        return tuple(
            (np.matmul(matrix, np.array([list(rgb)]).T).astype(np.int) + np.array([[0], [128], [128]])).flatten())

    @staticmethod
    def yuv2rgb(yuv):
        # @formatter:off
        matrix = np.array([
            [ 1,     0,         1.402],
            [ 1,    -0.334,    -0.714],
            [ 1,    1.772,      0]
        ])
        # @formatter:on
        return tuple(
            np.matmul(matrix, np.array([list(yuv)]).T - np.array([[0], [128], [128]])).astype(np.int).flatten())


class Concat(object):
    """
    YUV 图像拼接器
    TODO：按空域拼接
    """

    @staticmethod
    def concat(frames_list: List[List[Frame]], position: np.ndarray = None) -> List[Frame]:
        """
        将帧列表的列表拼接在一起，类似numpy的flatten方法
        :param frames_list: 帧列表的列表
        :param position: 如果传入该列表，则按空域拼接. 该参数的信息与frame_list 一一对应
        :return:帧列表
        """

        def check_res():
            """
            检查每一帧的元数据是否相同
            :return:
            """
            pre_frame: Optional[Frame] = None
            for _frames in frames_list:
                _frames: List[Frame] = _frames
                for frame in _frames:
                    frame: Frame = frame
                    if pre_frame is not None:
                        assert frame.width == pre_frame.width
                        assert frame.height == pre_frame.height
                    pre_frame = frame

        check_res()
        result = list()
        for frames in frames_list:
            result.extend(frames)
        return result

    @staticmethod
    def concat_seq(seq_list: List[Sequence], target_seq: Sequence) -> NoReturn:
        """
        拼接多个序列
        :param seq_list: 序列对象列表
        :param target_seq: 待写入的目标文件序列对象
        :return:
        """

        def check_res():
            """
            检查每一帧的元数据是否相同
            :return:
            """
            pre_seq: Optional[Sequence] = None
            for _seq in seq_list:
                _seq: Sequence = _seq
                if pre_seq is not None:
                    assert MetaData(_seq) == MetaData(pre_seq)
                pre_seq = _seq

        check_res()

        writer = YuvWriter(target_seq)
        for seq in seq_list:
            reader = YuvReader(seq)
            for frame in reader:
                writer.write(frame)
            reader.close()
        writer.close()


class Cut(object):
    """
    文件裁剪器，裁剪指定区域
    """

    @staticmethod
    def cut(frame: Frame, region: Region) -> Frame:
        """
        将传入的帧按照给定的区域裁剪，并返回一帧
        :param frame: 帧对象
        :param region: 裁剪区域
        :return: 裁剪后的帧对象
        """
        return frame.roi(region)

    @staticmethod
    def cut_seq(seq: Sequence, region: Region, target_seq: Sequence) -> NoReturn:
        """
        将序列裁剪
        :param seq:序列对象
        :param region:裁剪区域
        :param target_seq:目标序列
        :return:None
        """

        writer = YuvWriter(target_seq)
        reader = YuvReader(seq)
        for frame in reader:
            writer.write(Cut.cut(frame, region))
        reader.close()
        writer.close()


class MotionEstimate(object):
    class Method(Enum):
        FULL = 0
        STEP3 = 1
        DIAM = 2

    @staticmethod
    def _full_me(unit: np.ndarray, ref: np.ndarray, center=None):
        height, width = ref.shape
        uh, uw = unit.shape
        assert uh <= height
        assert uw <= width
        dist = 1 << 32
        for h in range(height - uh):
            for w in range(width - uw):
                pass

    @staticmethod
    def _step3_me(unit: np.ndarray, ref: np.ndarray, center=None):
        pass

    @staticmethod
    def _diam_me(unit: np.ndarray, ref: np.ndarray, center=None):
        pass

    @staticmethod
    def me(plane: Plane, region: Region, ref_plane: Plane, search_range: int = None, method: Method = Method.FULL):
        region = copy.copy(region)
        region.x -= search_range
        region.y -= search_range
        region.width = search_range << 1
        region.height = search_range << 1
        ref_plane.ensure_roi(region)
        funcs = {
            MotionEstimate.Method.FULL: MotionEstimate._full_me,
            MotionEstimate.Method.STEP3: MotionEstimate._step3_me,
            MotionEstimate.Method.DIAM: MotionEstimate._diam_me,
        }
        return funcs[method](plane.get(), ref_plane.get(), region)


class Mask(object):
    @staticmethod
    def _add_colored_points(frame: Frame, points: list, color_yuv: tuple):
        scale = frame.bit_depth.value - 8
        yuv = np.array(color_yuv) << scale

        for point in points:
            x, y = point
            if x < 0 or y < 0 or x >= frame.width or y >= frame.height:
                continue
            frame.get(Component.COMP_Y).get()[y, x] = yuv[0]
            frame.get(Component.COMP_U).get()[y >> 1, x >> 1] = yuv[1]
            frame.get(Component.COMP_V).get()[y >> 1, x >> 1] = yuv[2]

    @staticmethod
    def _calc_line_width(line_width: int):
        line_width = max(1, line_width)
        half_line_width_0 = (line_width - 1) >> 1
        half_line_width_1 = line_width - half_line_width_0
        return line_width, half_line_width_0, half_line_width_1

    @staticmethod
    def draw_line_hor(frame: Frame, y: int, x0: int, x1: int, color_rgb: tuple = (255, 255, 255), line_width: int = 1):
        line_width, half_line_width_0, half_line_width_1 = Mask._calc_line_width(line_width)
        points = list()
        y_range = (y - half_line_width_0, y + half_line_width_1)
        for y in range(*y_range):
            for x in range(x0, x1):
                points.append((x, y))
        Mask._add_colored_points(frame, points=points, color_yuv=Converter.rgb2yuv(color_rgb))

    @staticmethod
    def draw_line_ver(frame: Frame, x: int, y0: int, y1: int, color_rgb: tuple = (255, 255, 255), line_width: int = 1):
        line_width, half_line_width_0, half_line_width_1 = Mask._calc_line_width(line_width)
        points = list()
        x_range = (x - half_line_width_0, x + half_line_width_1)
        for y in range(y0, y1):
            for x in range(*x_range):
                points.append((x, y))
        Mask._add_colored_points(frame, points=points, color_yuv=Converter.rgb2yuv(color_rgb))

    @staticmethod
    def draw_grid(frame: Frame, grid_width: int, grid_height: int, color_rgb: tuple = (255, 255, 255),
                  line_width: int = 1, region: Region = None):
        if region is None:
            region = Region(0, 0, frame.width, frame.height)
        for h in range(0, region.height // grid_height + 1):
            Mask.draw_line_hor(frame, region.y + h * grid_height, region.x, region.x + region.width, color_rgb,
                               line_width)
        for w in range(0, region.width // grid_width + 1):
            Mask.draw_line_ver(frame, region.x + w * grid_width, region.y, region.y + region.height, color_rgb,
                               line_width)

    @staticmethod
    def draw_border(frame: Frame, color_rgb: tuple = (255, 255, 255), line_width: int = 1):
        Mask.draw_grid(frame, frame.width - line_width, frame.height - line_width, color_rgb, line_width)

    @staticmethod
    def draw_frame_with_sub_frame(frame: Frame, sub_frame: Frame, x: int, y: int):
        pos_x, pos_y = x, y
        for y in range(0, sub_frame.height):
            for x in range(0, sub_frame.width):
                color = (sub_frame[Component.COMP_Y].get()[y, x],
                         sub_frame[Component.COMP_U].get()[y >> 1, x >> 1],
                         sub_frame[Component.COMP_V].get()[y >> 1, x >> 1],
                         )
                Mask._add_colored_points(frame, [(x + pos_x, y + pos_y)], color)


class Scaler(object):
    @staticmethod
    def scale(frame: Frame, scale: Union[float, int]):
        h, w = frame.height, frame.width
        h, w = int(h * scale + 0.5), int(w * scale + 0.5)
        h, w = h >> 1 << 1, w >> 1 << 1
        y = cv2.resize(frame[Component.COMP_Y].get(), (w, h))
        u = v = None
        if frame.fmt != Format.YUV400:
            u = cv2.resize(frame[Component.COMP_U].get(), (w >> frame.uv_scale()[0], h >> frame.uv_scale()[1]))
            v = cv2.resize(frame[Component.COMP_V].get(), (w >> frame.uv_scale()[0], h >> frame.uv_scale()[1]))
        return Frame(width=w, height=h, bit_depth=frame.bit_depth, fmt=frame.fmt, buff_y=y, buff_u=u, buff_v=v)


if __name__ == '__main__':
    rgb = (222, 0, 0)
    print(Converter.rgb2yuv(rgb))
    print(Converter.yuv2rgb(Converter.rgb2yuv(rgb)))
