import os
from typing import Optional

from hpc.helper import path_join


def copy_del_rename(src: str,
                    dst: str = None,
                    new_name: Optional[str] = None) -> (Optional[str], Optional[str], Optional[str]):
    """
    获取复制文件到目标文件夹的命令，如果提供了第三个参数，则会在目标文件夹将文件改名为新文件名
    :param src: 源文件
    :param dst: 目标文件夹
    :param new_name: 新文件名称，不能加路径
    :return: DOS 命令行
    """
    file_name = os.path.basename(src)
    cp_cmd = None
    del_cmd = f"del {src}" if src != os.devnull else None
    ren_cmd = None
    if dst is not None:
        dst_file = path_join(file_name, dst)
        cp_cmd = f"copy /y {src} {dst}"
    else:
        dst_file = src
    if new_name is not None and len(new_name) > 0:
        ren_cmd = f"rename {dst_file} {new_name}"
    return cp_cmd, del_cmd, ren_cmd


def memory(w: int, h: int, bd: int = 10):
    """
    计算编码当前序列需要的最少内存，单位为MB.
    假设像素格式为YUV420、最小BUFFER帧数为 100，额外需要的其他内存为 100MB

    照此计算，假设存在一个4K的序列(4000x2000)，只需分配2.5GB的内存
    我们的小服务器内存至少也是32GB+，正常节点是40GB/48GB，大服务器内存是192GB，可用内存比物理内存少一点
    最大分辨率全部任务跑满(用2个核)：小服务器 24核，12个任务则30GB，大服务器40核，20个任务只需50G
    :param w: 宽度
    :param h: 高度
    :param bd: 比特深度
    :return:
    """
    # In old .BAT scripts: mem = w * h // 1940 + 83
    assert bd == 8 or bd == 10 or bd == 12 or bd == 16
    return int(w * h * 3 // 2 * 100 * ((bd + 7) >> 3) / 1000_000) + 100
