import os, sys
from typing import Optional
from hpc.core.helper import path_join

if sys.platform == "win32":
    def copy_del_rename(src: str, dst: str = None, new_name: Optional[str] = None, local=False):
        """
        获取复制文件到目标文件夹的命令，如果提供了第三个参数，则会在目标文件夹将文件改名为新文件名
        :param src: 源文件
        :param dst: 目标文件夹
        :param new_name: 新文件名称，不能加路径
        :param local: 是否在本地执行该命令
        :return: DOS 命令行
        """
        file_name = os.path.basename(src)
        if dst is not None:
            dst_file = path_join(file_name, dst)
            current_cmd = rf"copy /y {src} {dst} & del {src}"
        else:
            current_cmd = rf"del {src}"
            dst_file = src
        if new_name is not None:
            current_cmd = f"{current_cmd} & rename {dst_file} {new_name}"
        if not local:
            current_cmd = current_cmd.replace("&", "^&")
        return current_cmd
else:
    def copy_del_rename(src: str, dst: str, new_name: Optional[str] = None, local: bool = False):
        """
        获取复制文件到目标文件夹的命令，如果提供了第三个参数，则会在目标文件夹将文件改名为新文件名
        :param src: 源文件
        :param dst: 目标文件夹
        :param new_name: 新文件名称，不能加路径
        :param local: 是否在本地执行该命令
        :return: DOS 命令行
        """
        return None


def memory(w: int, h: int, bd: int = 10):
    """
    计算编码当前序列需要的最少内存，单位为MB.
    假设像素格式为YUV444、最小DPB为64，额外需要的其他内存为100MB
    :param w: 宽度
    :param h: 高度
    :param bd: 比特深度
    :return:
    """
    return int(w * h * 3 * 64 * ((bd + 7) >> 3) / 1000_000) + 100
