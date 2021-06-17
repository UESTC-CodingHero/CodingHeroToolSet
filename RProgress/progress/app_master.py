import logging
import os
from threading import Lock, Condition
from typing import Optional

from hpc.helper import mkdir, path_join, run_cmd
from hpc.hpc_job import HpcJobManager, JobState

from progress.lib.handler import ProgressManager, Callback, ProgressServerJobInfo
from progress.lib.net import HOST, PORT, MAX_CLIENTS

logging.basicConfig(level=logging.DEBUG,
                    format="[%(asctime)s] [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")


class _HpcProgressCallback(Callback):
    def __init__(self):
        self.lock = Lock()
        self.cond = Condition(self.lock)

    def on_state_change(self, state: JobState, job_info: Optional[ProgressServerJobInfo], *args):
        def default():
            if job_info is not None:
                logging.info(f"{job_info.job_id} {state.value}")
            with self.lock:
                self.cond.notify_all()

        msg_dict = {
            JobState.Configuring: lambda: {},
            JobState.Submitted: lambda: {
                logging.info(f"{job_info.job_id} {[os.path.basename(f) for f in job_info.file.split(',')]}")
            },
            JobState.Queued: lambda: {
                self.lock.acquire(),
                self.cond.wait(),
                self.lock.release(),
            },
        }

        (msg_dict.get(state) or default)()

    def on_progress_change(self, state: JobState, job_info: ProgressServerJobInfo, progress: int):
        info = f"{progress}/{job_info.total}"
        progress = 100 * progress // job_info.total
        if progress < 0 or progress > 100:
            logging.warning(f"{job_info.job_id} Invalid Progress: {progress}...")
            info = f"{info} Invalid!!!"
            progress = 99
        HpcJobManager.modify(job_info.job_id, progress=int(progress), progressmsg=info)


def main():
    exe_name = "progress_server.exe"
    if exe_name in run_cmd(f'tasklist /FI "PID ne {os.getppid()}"', fetch_console=True):
        logging.error(f"{exe_name} is already running...")
        exit(-1)
    logging.info("Start Server...")
    try:
        p = os.path.expanduser("~")
    except:
        p = os.environ["HOME"]
    cache_file = ".progress_manager_cache"
    cache_file = mkdir(new_dir=cache_file, parent_dir=p)
    if cache_file is not None:
        cache_filename = "job_info"
        cache_file = path_join(cache_filename, cache_file)

    manager = ProgressManager(host=HOST, port=PORT, max_clients=MAX_CLIENTS, callback=_HpcProgressCallback(),
                              cache_file=cache_file)
    try:
        manager.start()
    finally:
        manager.stop()
    logging.info("Stop Server...")


if __name__ == '__main__':
    main()
