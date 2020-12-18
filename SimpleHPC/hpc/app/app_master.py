from typing import Union

from hpc.core.hpc_job import HpcJobManager
from hpc.core.net import ProgressServer


def update_progress(jid: Union[str, int], progress: Union[float, int], info: str):
    HpcJobManager.modify(jid, progress=int(progress), progressmsg=info)


def main():
    ProgressServer(callback=update_progress).start()


if __name__ == '__main__':
    main()
