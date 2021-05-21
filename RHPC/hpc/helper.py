import hashlib
import logging
import os
import shutil
import subprocess as sp
import sys
import time
from typing import Union, List, Tuple, Optional, IO


def path_join(current: str, *parent: Union[Tuple[str], List[str], str]) -> str:
    """
    将路径拼接成完整的全路径
    :param current: 当前文件名或路径名
    :param parent: 父文件名，1个或多个
    :return:
    """
    return os.path.join(*parent, current)


def mkdir(new_dir: str, parent_dir: Optional[Union[Tuple[str], List[str], str]] = None) -> Optional[str]:
    """
    创建目录
    :param new_dir: 待创建目录的名称
    :param parent_dir: 其父目录名称
    :return:
    """
    if parent_dir is not None:
        new_dir = path_join(new_dir, parent_dir)
    try:
        if not os.path.exists(new_dir):
            os.makedirs(new_dir, exist_ok=True)
        return new_dir
    except OSError as _:
        return None


def rmdir(directory: str, parent_dir: str = None) -> bool:
    """
    删除指定目录
    :param directory: 待删除目录的名称
    :param parent_dir: 其父目录名称
    :return:
    """
    if parent_dir is not None:
        directory = path_join(directory, parent_dir)
    try:
        shutil.rmtree(directory)
        return True
    except FileNotFoundError as _:
        return False


def clean_dir(directory: str, parent_dir: str = None) -> None:
    """
    清除目录内容
    :param directory: 待清空目录的名称
    :param parent_dir: 其父目录名称
    :return:
    """
    if rmdir(directory, parent_dir):
        mkdir(directory, parent_dir)


def copy_to(file, dst) -> None:
    """
    复制文件、路径到指定目录
    :param file: 文件名称或路径名
    :param dst: 目标文件名或者目标路径名
    :return:
    """
    if os.path.exists(dst) and os.path.isdir(dst):
        copy_to(file, path_join(os.path.basename(file), dst))
    else:
        shutil.copyfile(file, dst)


def get_hash(max_len: int = 4, seed: Optional[Union[list, str]] = None) -> str:
    """
    获取HASHCODE
    :param max_len: 返回hashcode的前N位
    :param seed: 如果未设置(为None或者空字符串或者空列表)，则使用系统时间作为 待hash字符串
    如果设置了，先判断是否为文件，如果为文件，则计算该文件的hash值，否则将其看作字符串，计算该字符串的hash值
    :return:
    """
    _md5 = hashlib.md5()
    if seed is None or (isinstance(seed, list) or isinstance(seed, str)) and len(seed) == 0:
        seed = time.time()
    if (isinstance(seed, list) and len(seed) == 1 and os.path.exists(seed[0]) or
            isinstance(seed, str) and os.path.exists(seed)):
        if isinstance(seed, list):
            file = seed[0]
        else:
            file = seed
        with open(file, 'rb') as f:
            f.seek(0, os.SEEK_END)
            length = f.tell()
            read = 0
            f.seek(0, os.SEEK_SET)
            while read < length:
                r = min(length - read, 4096)
                _md5.update(f.read(r))
                read += r
    else:
        _md5.update(str(seed).encode("utf-8"))
    hashcode = str(_md5.hexdigest())
    hash_len = len(hashcode)
    if max_len > hash_len:
        logging.warning(f"The specified max length({max_len}) is greater than the hash code length({hash_len}).")
        max_len = hash_len

    return hashcode[:max_len].upper()


def run_cmd(cmd: Union[str, list],
            fetch_console: bool = False,
            workdir: Optional[str] = None,
            stdout: Optional[Union[str, IO]] = None,
            stderr: Optional[Union[str, IO]] = None) -> Optional[Union[List[str], str, bool]]:
    """
    新开一个进程执行传入的命令

    :param cmd: 命令行或者命令行列表
    :param fetch_console:是否获取命令行输出
    :param workdir:是否获取命令行输出
    :param stdout:是否获取命令行输出
    :param stderr:是否获取命令行输出
    :return: 如果指定了fetch_console则返回命令行的标准输出，或者多个命令的标准输出列表，否则返回None
    """
    if cmd is None:
        return None
    if workdir is None:
        workdir = os.curdir
    if stdout is None:
        stdout = sys.stdout
    if stderr is None:
        stderr = sys.stderr

    if isinstance(cmd, list):
        assert len(cmd) != 0
        return [run_cmd(c, fetch_console, workdir, stdout, stderr) for c in cmd]
    else:
        # 备份原先的工作目录
        cur = os.getcwd()
        os.chdir(workdir)

        if fetch_console:
            result = os.popen(cmd).read().strip()
        else:
            try:
                if isinstance(stdout, str):
                    stdout = open(stdout, "w+")
                if isinstance(stderr, str):
                    stderr = open(stderr, "w+")
                p = sp.Popen(cmd, shell=True, stdout=stdout, stderr=stderr)
                p.wait()
                if stdout != sys.stdout:
                    stdout.close()
                if stderr != sys.stderr:
                    stderr.close()
                result = True
            except KeyboardInterrupt as e:
                raise e
            except OSError or TimeoutError:
                result = False

        # 还原原先的工作目录
        os.chdir(cur)
        return result
