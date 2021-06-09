import os
import re
from enum import Enum

from .helper import run_cmd


class JobState(Enum):
    Configuring = "Configuring"
    Submitted = "Submitted"
    Queued = "Queued"
    Running = "Running"
    Finished = "Finished"
    Failed = "Failed"
    Canceled = "Canceled"
    Unknown = "Unknown"


class JobManager(object):
    SCHEDULER_EXE = ""
    cmd_set = dict()
    state_set = dict()
    task_id_set = dict()
    g_id = 0

    @staticmethod
    def new(**kwargs) -> (int, bool):
        """
        新建一个job，返回job id和是否成功
        :param kwargs:
        :return:
        """
        JobManager.g_id += 1
        JobManager.cmd_set[JobManager.g_id] = list()
        JobManager.state_set[JobManager.g_id] = JobState.Configuring
        return JobManager.g_id, True

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
    def run_cmd(cmd_set):
        success = True
        for _, name, cmd, workdir, stdout, stderr, depend in cmd_set:
            success = run_cmd(JobManager.SCHEDULER_EXE + " " + cmd,
                              workdir=workdir, stdout=stdout, stderr=stderr) and success
        return success

    @staticmethod
    def submit(job_id, **kwargs):
        if job_id is None or JobManager.cmd_set.get(job_id) is None:
            return False
        from concurrent.futures import ProcessPoolExecutor
        executor: ProcessPoolExecutor = kwargs.get("executor") or None
        task = None
        if executor is None:
            success = JobManager.run_cmd(JobManager.cmd_set[job_id])
            JobManager.state_set[job_id] = JobState.Finished if success else JobState.Failed
        else:
            task = executor.submit(JobManager.run_cmd, JobManager.cmd_set[job_id])
            JobManager.state_set[job_id] = JobState.Finished if task is not None else JobState.Failed
        return task

    @staticmethod
    def view(job_id):
        return JobManager.state_set.get(job_id)

    @staticmethod
    def modify(job_id, **kwargs):
        return True


class HpcJobConfig(object):
    HPC_EXE = "job"
    HPC_SCHEDULER = "DellServer" if not os.getenv("CCP_SCHEDULER") else os.getenv("CCP_SCHEDULER")

    def __init__(self, cores=2, nodes=None, groups="E2680", priority=2000):
        self.cores = cores
        self.nodes = nodes
        self.groups = groups
        self.priority = priority


class HpcJobManager(object):
    """
    HpcJobManager 用于封装HPC提供的常用命令操作，具体包括new/add/submit/view/modify
    具体请参考下面的文档:
    https://docs.microsoft.com/en-us/powershell/high-performance-computing/overview?view=hpc16-ps
    https://docs.microsoft.com/en-us/powershell/high-performance-computing/job?view=hpc16-ps
    """
    JOB_NEW_ARGS = ["askednodes", "corespernode", "customproperties", "emailaddress", "estimatedprocessmemory",
                    "exclusive", "faildependenttasks", "failontaskfailure", "holduntil", "jobenv", "jobfile", "jobname",
                    "jobtemplate", "license", "memorypernode", "nodegroup",
                    "nodegroupop", "notifyoncompletion", "notifyonstart",
                    ["numcores", "numnodes", "numprocessors", "numsockets"],
                    "orderby", "progress", "parentjobids", "priority", "progress",
                    "progressmsg", "priority", "Runtime", "rununtilcanceled",
                    "scheduler", "singlenode", "taskexecutionfailureretrylimit", "validexitcodes"]
    JOB_ADD_ARGS = ["depend", "env",
                    "exclusive", "name",
                    ["numcores", "numnodes", "numprocessors", "numsockets"],
                    "parametric", "requirednodes",
                    "rerunnable", "runtime",
                    "scheduler", "stderr",
                    "stdin", "stdout",
                    "taskfile", "type",
                    "validexitcodes", "workdir"
                    ]
    JOB_SUBMIT_ARGS = ["password", "user", "scheduler", "holduntil", "memorypernode",
                       "requestednodes", "nodegroup", "priority"]

    JOB_MODIFY_ARGS = [["addexcludednodes", "clearexcludednodes", "removeexcludednodes"],
                       "askednodes", "corespernode", "customproperties", "emailaddress", "estimatedprocessmemory",
                       "exclusive", "faildependenttasks", "failontaskfailure",
                       "holduntil", "jobenv", "jobfile", "jobname", "jobtemplate", "license",
                       "memorypernode", "nodegroup", "nodegroupop", "notifyoncompletion", "notifyonstart",
                       "nodegroupop",
                       ["numcores", "numnodes", "numprocessors", "numsockets"],
                       "orderby", "parentjobids", "password", "priority", "progress", "progressmsg",
                       "projectname", "removeexcludednodes", "requestednodes", "runtime", "rununtilcanceled",
                       "scheduler", "singlenode", "taskexecutionfailureretrylimit", "user", "validexitcodes"
                       ]

    @staticmethod
    def check_env():
        """
        判断当前平台是否有HPC集群环境，判断依据为当前平台上有 “job”命令
        :return:
        """
        return os.system(f"where {HpcJobConfig.HPC_EXE} > nul 2>&1") == 0

    @staticmethod
    def _filter_and_concat_params(kd, kwargs):
        cmd = ""
        for valid_key in kd:
            if len(kwargs) == 0:
                break

            if isinstance(valid_key, list):
                for key in valid_key:
                    if key in kwargs.keys():
                        value = kwargs.pop(key)
                        if value is not None and len(str(value)) > 0:
                            cmd += f" /{key}:{value}"
                        break
            else:
                if valid_key in kwargs.keys():
                    value = kwargs.pop(valid_key)
                    if value is not None and len(str(value)) > 0:
                        cmd += f" /{valid_key}:{value}"
        return cmd

    @staticmethod
    def new(**kwargs) -> (int, bool):
        def _parse_job_id(text: str) -> (int, bool):
            """
            根据“job new”命令的输出，解析工作的ID。
            例如: Created job, ID: 190707

            :param text: “job new”命令的输出
            :return: the job id
            """
            try:
                return int(text.split()[3]), True
            except ValueError as _:
                return 0, False

        cmd = f"{HpcJobConfig.HPC_EXE} new {HpcJobManager._filter_and_concat_params(HpcJobManager.JOB_NEW_ARGS, kwargs)}"

        out_text = run_cmd(cmd, fetch_console=True)
        return _parse_job_id(out_text)

    @staticmethod
    def add(job_id: int, command: str, **kwargs) -> bool:
        if job_id is None or command is None:
            return False
        cmd = f"{HpcJobConfig.HPC_EXE} add {job_id} {HpcJobManager._filter_and_concat_params(HpcJobManager.JOB_ADD_ARGS, kwargs)} {command}"
        return run_cmd(cmd)

    @staticmethod
    def submit(job_id, **kwargs):
        if job_id is None:
            return False
        cmd = f"{HpcJobConfig.HPC_EXE} submit /id:{job_id} {HpcJobManager._filter_and_concat_params(HpcJobManager.JOB_SUBMIT_ARGS, kwargs)}"
        run_cmd(cmd)

    @staticmethod
    def view(job_id):
        if job_id is None:
            return False
        text = run_cmd(f"{HpcJobConfig.HPC_EXE} view {job_id}", fetch_console=True)

        state = "Unknown"
        for line in text.split("\n"):
            line = line.strip()
            # eg: State                            : Running
            m = re.match(r"State\s+:\s*(\w+)", line)
            if m:
                state = m.group(1)
        return JobState(state)

    @staticmethod
    def modify(job_id: int, **kwargs):
        if job_id is None:
            return False
        cmd = f"{HpcJobConfig.HPC_EXE} modify {job_id} {HpcJobManager._filter_and_concat_params(HpcJobManager.JOB_MODIFY_ARGS, kwargs)}"
        return run_cmd(cmd)
