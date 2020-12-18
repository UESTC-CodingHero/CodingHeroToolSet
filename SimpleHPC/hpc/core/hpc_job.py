import os
import re
from enum import Enum

from hpc.core.helper import run_cmd


class HpcJobState(Enum):
    Configuring = "Configuring"
    Submitted = "Submitted"
    Queued = "Queued"
    Running = "Running"
    Finished = "Finished"
    Failed = "Failed"
    Canceled = "Canceled"
    All = "All"


class HpcJobManager(object):
    """
        The command can reference as following:
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
    JOB_SUBMIT_ARGS = ["password", "user", "scheduler", "holduntil", "memorypernode", "nodegroup", "priority"]

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
        return os.system("where job > nul 2>&1") == 0

    @staticmethod
    def __filter_params(kd, kwargs):
        cmd = ""
        for k, v in kwargs.items():
            if k in kd and v is not None and len(str(v)) > 0 and v != os.devnull:
                cmd += f" /{k}:{v}"
        return cmd

    @staticmethod
    def new(**kwargs):
        if not HpcJobManager.check_env():
            return False

        def _parse_job_id(text: str) -> int:
            """
            parse the job id from the job new command's output, eg: Created job, ID: 190707

            :param text: the output of `job new` command
            :return: the job id
            """
            try:
                return int(text.split()[3])
            except ValueError as _:
                return 0

        cmd = f"job new {HpcJobManager.__filter_params(HpcJobManager.JOB_NEW_ARGS, kwargs)}"

        out_text = run_cmd(cmd, fetch_console=True)
        return _parse_job_id(out_text)

    @staticmethod
    def add(job_id, command, **kwargs):
        if not HpcJobManager.check_env() or command is None or job_id is None:
            return False
        cmd = f"job add {job_id} {HpcJobManager.__filter_params(HpcJobManager.JOB_ADD_ARGS, kwargs)} {command}"
        run_cmd(cmd)
        return True

    @staticmethod
    def submit(job_id, **kwargs):
        if not HpcJobManager.check_env():
            return False
        cmd = f"job submit /id:{job_id} {HpcJobManager.__filter_params(HpcJobManager.JOB_SUBMIT_ARGS, kwargs)}"
        run_cmd(cmd)

    @staticmethod
    def view(job_id):
        if not HpcJobManager.check_env():
            return False
        # State                            : Running
        text = run_cmd(f"job view {job_id}", fetch_console=True)
        state = "UNKNOWN"
        for line in text.split("\n"):
            line = line.strip()
            m = re.match(r"State\s+:\s*(\w+)", line)
            if m:
                state = m.group(1)
        return HpcJobState(state)

    @staticmethod
    def modify(job_id, **kwargs):
        if not HpcJobManager.check_env():
            return False
        cmd = f"job modify {job_id} {HpcJobManager.__filter_params(HpcJobManager.JOB_MODIFY_ARGS, kwargs)}"
        run_cmd(cmd)
