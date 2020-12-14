import hashlib
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Union


def get_hash(max_len=4, seed=None):
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
        file = seed[0]
        with open(file, 'rb') as f:
            _md5.update(f.read())
    else:
        _md5.update(str(seed).encode("utf-8"))
    hashcode = str(_md5.hexdigest())
    hash_len = len(hashcode)
    max_len = max_len if max_len <= hash_len else hash_len
    return hashcode[0:max_len].upper()


def run_cmd(cmd: Union[str, list], fetch_console=False):
    """
    新开一个进程执行传入的命令
    如果fetch_console为True,则可返回命令的标准输出。
    如果fetch_console为False, 执行的命令会直接输出到控制台。

    :param cmd: 命令行或者命令行列表
    :param fetch_console:是否获取命令行输出
    :return: 如果指定了fetch_console则返回命令行的标准输出，或者多个命令的标准输出列表，否则返回None
    """
    if cmd is None:
        return None
    if isinstance(cmd, list):
        assert len(cmd) != 0
        p = ThreadPoolExecutor(len(cmd))
        all_task = [p.submit(run_cmd, c, fetch_console) for c in cmd]
        return [future.result() for future in as_completed(all_task)]
    else:
        if fetch_console:
            stdout = str(os.popen(cmd).read()).strip()
            return stdout
        else:
            os.system(cmd)
    return None


if __name__ == '__main__':
    r = run_cmd(["echo hello", "echo world"], fetch_console=True)
    print(r)
    r = get_hash(max_len=32)
    print(r)
