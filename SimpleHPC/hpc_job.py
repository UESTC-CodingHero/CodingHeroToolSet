import re
import copy
import optparse

from core.net import Client, to_json
from core.helper import run_cmd

# 2个$符号中间的字符串识别为正则表达式
REGEX_SYM = "$"
# 2个#符号中间的字符串识别为 python 语言表达式
PYTHON_SYM = "#"
# []符号中间的字符串识别为 数组 语言表达式
ARR_SYM = "[]"
# ()符号中间的字符串识别为 数组 语言表达式，该表达式为备选数组
ARR_VICE_SYM = "()"


def find_out_all_python_iters(s):
    """
    给定包含数组的字符串，则提取出来各个数组的字符串
    给定单个逗号分割的字符串，则以逗号为分割点，实现分割功能，约等于str.split(",")
    """

    count = 0
    start = 0
    result = []
    costumed = False
    d_count = 0
    for i, ch in enumerate(s):
        if ch == REGEX_SYM or ch == PYTHON_SYM:
            if d_count == 0:
                d_count += 1
            else:
                d_count -= 1

        if d_count == 1:
            continue
        if ch == ARR_SYM[0] or ch == ARR_VICE_SYM[0]:
            if count == 0:
                start = i
                costumed = False
            count += 1
        elif ch == ARR_SYM[1] or ch == ARR_VICE_SYM[1]:
            count -= 1
            if count == 0:
                result.append(s[start: i + 1])
                start = i + 1
                costumed = True
        elif ch == "," and not costumed:
            if count == 0:
                result.append(s[start: i])
                start = i + 1
        elif i == len(s) - 1 and not costumed:
            result.append(s[start: i + 1])
    return result


def str_to_python_iter_or_str(s: str):
    # 字符串
    if s.startswith("'") and s.endswith("'") or s.startswith('"') and s.endswith('"'):
        return s.strip().strip("'\"")
    else:
        # 将（）替换为 []，以便python统一识别为list
        s = s.replace(ARR_VICE_SYM[0], ARR_SYM[0])
        s = s.replace(ARR_VICE_SYM[1], ARR_SYM[1])
    if s.startswith(ARR_SYM[0]) and s.endswith(ARR_SYM[1]):
        # 数组
        exec("temp=" + s)
        result = locals()["temp"]
        return result
    else:  # 字符串
        return s.strip()


class ArgumentsParser(object):
    class HpcArgumentsParser(object):
        def __init__(self, hpc: str):
            parser = optparse.OptionParser()
            parser.add_option("--name")
            parser.add_option("--project", default="Default Project")
            parser.add_option("--cores", default=2, choices=["1", "2", "3", "4", "5"])
            parser.add_option("--nodes", default="*")
            parser.add_option("--groups", default="E2680", choices=["E2680", "X5680"])
            parser.add_option("--memory")
            parser.add_option("--priority", default="2000")
            parser.add_option("--workdir")
            parser.add_option("--stdout")
            parser.add_option("--stderr")
            parser.add_option("--file", default="nul")
            parser.add_option("--total", default="")
            parser.add_option("--valid_line_reg", default="")
            parser.add_option("--end_line_reg", default="")
            self.hpc, _ = parser.parse_args(hpc.split())

        def __call__(self, *args, **kwargs):
            return self.hpc

    def __init__(self, hpc: str, cmd: str, args: str):
        self.hpc: str = hpc
        self.cmd: str = cmd
        self.hpc = self.hpc.replace("{_idx}", "!~!~!")
        self.cmd = self.cmd.replace("{_idx}", "!~!~!")

        self.args, self.kwargs = self._args_refine(args)
        self._key_replace()
        self._py_replace()
        self._iter_expand()

    @staticmethod
    def _args_refine(args_list):
        kwargs = {v.split("=")[0]: v.split("=")[1] for v in args_list if "=" in v and "{" not in v and "}" not in v}
        todo_kwargs = {v.split("=")[0]: v.split("=")[1].format(**kwargs) for v in args_list if
                       "=" in v and "{" in v and "}" in v}
        kwargs.update(todo_kwargs)

        args = [v.format(**kwargs) for v in args_list if "=" not in v]
        args = [v.format(*args) for v in args]
        return args, kwargs

    def _key_replace(self):
        self.cmd = self.cmd.format(*self.args, **self.kwargs)
        self.hpc = self.hpc.format(*self.args, **self.kwargs)

    def _py_replace(self):
        """
        2个#号之间的代码解释为python代码
        #python code#
        :return:
        """

        def py_parse(s: str):
            rs = re.findall(f"{PYTHON_SYM}.+?{PYTHON_SYM}", s)
            for r in rs:
                exec("temp=" + str(r[1:-1]))
                s = s.replace(r, str(locals()["temp"]))
            return s

        self.cmd = py_parse(self.cmd)
        self.hpc = py_parse(self.hpc)

    def _iter_expand(self):
        def expand(single_str: str) -> list:
            iters = find_out_all_python_iters(single_str)
            if len(iters) == 0:
                return [single_str]
            for i, it in enumerate(iters):
                single_str = single_str.replace(it, "{" + str(i) + "}", 1)
            iters = [str_to_python_iter_or_str(t) for t in iters]
            if isinstance(iters[0], str):
                iters = [iters]
            results_list = []
            for pos_args in zip(*iters):
                results = []
                length = 1
                result = []
                temp = []
                for i, pos_arg in enumerate(pos_args):
                    if isinstance(pos_arg, list):
                        length = len(pos_arg)
                        result.append(pos_arg[0])
                        temp.append((i, pos_arg[1:]))
                    else:
                        result.append(str(pos_arg))
                results.append(result)
                for i in range(length - 1):
                    result = copy.deepcopy(result)
                    for pos_arg in temp:
                        j, v = pos_arg
                        result[j] = v[i]
                    results.append(result)
                results_list.append(results)
            temp = []
            for results in results_list:
                temp0 = []
                for result in results:
                    temp0.append(single_str.format(*result))
                temp.append(temp0)
            return temp

        self.hpc = expand(self.hpc)
        self.cmd = expand(self.cmd)

    def generate(self):
        for hpc_list, cmd_list in zip(self.hpc, self.cmd):
            for hpc in hpc_list:
                yield ArgumentsParser.HpcArgumentsParser(hpc)(), cmd_list

    @staticmethod
    def get_hpc(hpc):
        return hpc.project, hpc.name, hpc.cores, hpc.nodes, hpc.groups, hpc.memory, hpc.priority, hpc.workdir, hpc.stdout, hpc.stderr

    def __str__(self):
        return str(self.hpc) + "\t" + str(self.cmd)


class HpcRunner(object):
    def __init__(self, args: ArgumentsParser):
        self.args = args

    @staticmethod
    def job_run(hpc, cmd, dependency=None):
        """
            The command can reference as following:
            https://docs.microsoft.com/en-us/powershell/high-performance-computing/overview?view=hpc16-ps
            https://docs.microsoft.com/en-us/powershell/high-performance-computing/job?view=hpc16-ps
        """
        job = "job"
        project, name, c, n, g, m, p, d, out, err = ArgumentsParser.get_hpc(hpc)
        # job new
        text = run_cmd(f"{job} new /projectname:{project} /jobname:{name}", fetch_console=True)
        jid = int(text.split()[3])

        # job add
        if dependency is not None and len(str(dependency)) > 0:
            run_cmd(
                f"{job} add {jid} /name:{name} /depend{dependency} /numcores:{c} /workdir:{d} /stdout:{out} /stderr:{err} {cmd}")
        else:
            run_cmd(f"{job} add {jid} /name:{name} /numcores:{c} /workdir:{d} /stdout:{out} /stderr:{err} {cmd}")

        # job submit
        if str(n) == "*" or str(n) == "":
            run_cmd(f"{job} submit /id:{jid} /nodegroup:{g} /memorypernode:{m} /priority:{p}")
        else:
            run_cmd(f"{job} submit /id:{jid} /nodegroup:{g} /requestednodes:{n} /memorypernode:{m} /priority:{p}")

        # 如果设置了这一堆东西（基本上是专门为编码器设置的）
        if hpc.file != "nul":
            if hpc.file == "stdout":
                hpc.file = hpc.stdout
            elif hpc.file == "stderr":
                hpc.file = hpc.stderr
            try:
                assert hpc.valid_line_reg[0] == hpc.valid_line_reg[-1] == '$'
                assert hpc.end_line_reg[0] == hpc.end_line_reg[-1] == '$'
                hpc.valid_line_reg = hpc.valid_line_reg[1:-1]
                hpc.end_line_reg = hpc.end_line_reg[1:-1]
                Client().send(to_json(jid, hpc.total, hpc.valid_line_reg, hpc.end_line_reg, hpc.file))
            except Exception as e:
                print(e)

        return jid, name

    def run(self):
        for hpc, cmd_list in self.args.generate():
            for cmd in cmd_list:
                self.job_run(hpc, cmd)


def main(hpc: str, exe_key: str, exe_value: str):
    p = ArgumentsParser(hpc, exe_key, exe_value)
    r = HpcRunner(p)
    r.run()


if __name__ == '__main__':
    mp = optparse.OptionParser()
    mp.add_option("--hpc")
    mp.add_option("--cmd")
    values, arg = mp.parse_args()
    main(values.hpc, values.cmd, arg)
