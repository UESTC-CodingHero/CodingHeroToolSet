from typing import Union

from hpc.core.hpc_job import HpcJobManager, HpcJobState
from hpc.core.net import ProgressServer
import logging
import os
from threading import Lock, Condition

logging.basicConfig(level=logging.DEBUG,
                    format="[%(asctime)s] [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")


class HpcProgressCallback(ProgressServer.Callback):
    def __init__(self):
        self.id = 0
        self.file = None
        self.lock = Lock()
        self.cond = Condition(self.lock)

    def on_error(self, e: Exception):
        logging.error(str(e))
        self.lock.acquire()
        self.cond.notify_all()
        self.lock.release()

    def on_submit(self, job_id: Union[str, int], **kwargs):
        self.id = job_id
        self.file = kwargs.pop("file")
        logging.info(f"{job_id} {os.path.basename(self.file)}")
        return

    def on_waiting(self):
        self.lock.acquire()
        self.cond.wait()
        self.lock.release()

    def on_running(self):
        logging.info(f"{self.id} In Running...")
        return

    def on_finish(self, state: HpcJobState):
        if state == HpcJobState.Failed:
            logging.warning(f"{self.id} Failed...")
        elif state == HpcJobState.Canceled:
            logging.warning(f"{self.id} Cancelled...")
        elif state == HpcJobState.Finished:
            logging.info(f"{self.id} Finished...")
        else:
            logging.error(f"{self.id} Unknown Ending State")
        self.lock.acquire()
        self.cond.notify_all()
        self.lock.release()
        return

    def on_update(self, jid: Union[str, int], progress: Union[float, int], info: str):
        if progress < 0 or progress > 100:
            logging.warning(f"{self.id} Invalid Progress: {progress}...")
            progress = 99
        HpcJobManager.modify(jid, progress=int(progress), progressmsg=info)


def main():
    logging.info("Start Server...")
    try:
        p = os.path.expanduser("~")
    except:
        p = os.environ["HOME"]
    sub_dir = ".progress_server_cache"
    if not os.path.exists(os.path.join(p, sub_dir)):
        os.makedirs(os.path.join(p, sub_dir))
    # only the file name, without suffix
    cache = "all_jobs"
    ProgressServer(callback=HpcProgressCallback(), cache_file=os.path.join(p, sub_dir, cache)).start()

    logging.info("Stop Server...")


if __name__ == '__main__':
    main()
