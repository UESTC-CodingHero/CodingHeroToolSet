import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Union


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
    r = run_cmd("echo hello world", fetch_console=True)
    print(r)