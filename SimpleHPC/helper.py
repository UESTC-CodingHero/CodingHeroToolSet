import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Union


def run_cmd(cmd: Union[str, list], fetch_console=False):
    if cmd is None:
        return ""
    if isinstance(cmd, list):
        assert len(cmd) != 0
        p = ThreadPoolExecutor(len(cmd))
        all_task = [p.submit(run_cmd, c) for c in cmd]
        return [future.result() for future in as_completed(all_task)]
    else:
        if fetch_console:
            stdout = str(os.popen(cmd).read()).strip()
            return stdout
        else:
            os.system(cmd)
    return ""
