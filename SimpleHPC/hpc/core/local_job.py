from enum import Enum
import logging
from hpc.core.helper import run_cmd


class JobState(Enum):
    Configuring = "Configuring"
    Submitted = "Submitted"
    Queued = "Queued"
    Running = "Running"
    Finished = "Finished"
    Failed = "Failed"
    Canceled = "Canceled"
    All = "All"


class JobManager(object):
    cmd_set = dict()
    state_set = dict()
    task_id_set = dict()
    g_id = 0

    @staticmethod
    def new(**kwargs):
        JobManager.g_id += 1
        JobManager.cmd_set[JobManager.g_id] = list()
        JobManager.state_set[JobManager.g_id] = JobState.Configuring
        return JobManager.g_id

    @staticmethod
    def add(job_id, command: str, **kwargs):
        if command is None or job_id is None or JobManager.cmd_set.get(job_id) is None:
            return False
        pre_task_id = JobManager.task_id_set.get(job_id) if JobManager.task_id_set.get(job_id) else 0
        task_id = pre_task_id + 1
        workdir = kwargs.get("workdir")
        stdout = kwargs.get("stdout")
        stderr = kwargs.get("stderr")
        depend = kwargs.get("depend")
        name = kwargs.get("name")
        cmd = command.format(**kwargs)
        JobManager.cmd_set[job_id].append([task_id, name, cmd, workdir, stdout, stderr, depend])
        JobManager.task_id_set[job_id] = task_id
        return True

    @staticmethod
    def submit(job_id, **kwargs):
        if job_id is None or JobManager.cmd_set.get(job_id) is None:
            return False
        success = True
        for _, _, cmd, workdir, stdout, stderr, _ in JobManager.cmd_set[job_id]:
            logging.info(cmd)
            success = run_cmd(cmd, workdir=workdir, stdout=stdout, stderr=stderr) and success
        JobManager.state_set[job_id] = JobState.Finished if success else JobState.Failed

    @staticmethod
    def view(job_id):
        return JobManager.state_set.get(job_id)

    @staticmethod
    def modify(job_id, **kwargs):
        return False
