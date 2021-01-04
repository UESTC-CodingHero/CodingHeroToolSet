from typing import List, NoReturn, Optional
from common.com_def import Region, MetaData, Frame, Sequence
from yuv_io.yuv_io import YuvReader, YuvWriter
import numpy as np
import copy
from enum import Enum


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
                        assert MetaData(frame) == MetaData(pre_frame)
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
    def me(frame: Frame, region: Region, ref_frame: Frame, search_range: int = None, method: Method = Method.FULL):
        region_in_ref = copy.copy(region)
        region_in_ref.x -= search_range
        region_in_ref.y -= search_range
        region_in_ref.width = search_range << 1
        region_in_ref.height = search_range << 1
        ref_frame.ensure_roi(region_in_ref)
