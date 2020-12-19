import re
import os
from hpc.core.helper import rmdir
from hpc.codec.logger_abc import AbsLogScanner, Record
from hpc.codec.mode import Mode


class HpmScanner(AbsLogScanner):
    def scan(self, filter_func=None, rm_log=False):
        files = os.listdir(self.log_dir)
        if callable(filter_func):
            files = filter(filter_func, files)
        # TODO do merge first
        if self.is_separate:
            for seq in self.seqs:
                pass
        for file in files:
            _id, name = self._in_dict(file)
            assert name is not None
            if name is not None:
                record = Record(_id, self.mode, name)
                record.qp = int(file[-6:-4])
                with open(os.path.join(self.log_dir, file), "r") as fp:
                    for line in fp:
                        line = line.strip()
                        if "PSNR Y(dB)" in line:
                            record.psnr_y = float(line.strip("PSNR Y(dB)").strip().strip(":").strip())
                        elif "PSNR U(dB)" in line:
                            record.psnr_u = float(line.strip("PSNR U(dB)").strip().strip(":").strip())
                        elif "PSNR V(dB)" in line:
                            record.psnr_v = float(line.strip("PSNR V(dB)").strip().strip(":").strip())
                        elif "bitrate(kbps)" in line:
                            record.bitrate = float(line.strip("bitrate(kbps)").strip().strip(":").strip())
                        elif "Total encoding time" in line:
                            sp = line.strip("Total encoding time").strip().strip("=").strip().split(" ")
                            record.encode_time = float(sp[2])
                            break
                self._add_record(record)
        if rm_log:
            rmdir(self.log_dir)
        self.records = dict(sorted(self.records.items(), key=lambda kv: kv[0]))
        return self.records

    @staticmethod
    def get_valid_line_reg():
        return r"\s*(\d+)\s+\(\s*[I^|P^|B]\)\s+(\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+" \
               r"(\d+)\s+(\d+)\s+(0\.\d+).+"

    @staticmethod
    def get_end_line_reg():
        return r"Encoded\s*frame\s*count\s+=\s*(\d+)"


class Uavs3eScanner(HpmScanner):
    def scan(self, filter_func=None, rm_log=False):
        file = os.path.join(self.log_dir, "psnr.txt")
        assert os.path.exists(file)
        with open(file, "r") as fp:
            for line in fp:
                matched = re.match(r"(\S+) {4}(\S+) (\S+) (\S+) (\S+) {4}(\S+) (\S+) (\S+) {4}(\S+)", line)
                assert matched is not None
                if matched:
                    file_name = matched.group(1)
                    _id, name = self._in_dict(file_name)
                    assert name is not None
                    record = Record(_id, self.mode, name)
                    record.qp = int(file_name[-6:-4])
                    record.bitrate = float(matched.group(2))
                    record.psnr_y = float(matched.group(3))
                    record.psnr_u = float(matched.group(4))
                    record.psnr_v = float(matched.group(5))
                    record.encode_time = float(matched.group(9))
                    self._add_record(record)
        if rm_log:
            rmdir(file)
        self.records = dict(sorted(self.records.items(), key=lambda kv: kv[0]))
        return self.records

    @staticmethod
    def get_valid_line_reg():
        return r"\s*(\d+)\s*\(\s*[I|P|B]\)\|\s*(\d+\.\d+)\|\s*(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\|.+"

    @staticmethod
    def get_end_line_reg():
        return r"Encoded\s*frame\s*count\s+=\s*(\d+)"


class HMScanner(AbsLogScanner):
    def scan(self, filter_func=None, rm_log=False):
        files = os.listdir(self.log_dir)
        if callable(filter_func):
            files = filter(filter_func, files)
        for file in files:
            _id, name = self._in_dict(file)
            assert name is not None
            if name is not None:
                record = Record(_id, self.mode, name)
                record.qp = int(file[-6:-4])
                with open(os.path.join(self.log_dir, file), "r") as fp:
                    for line in fp:
                        line = line.strip()
                        m = re.match(r"\s*(\d+)\s+a\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)",
                                     line)
                        if m:
                            record.bitrate = float(m.group(2))
                            record.psnr_y = float(m.group(3))
                            record.psnr_u = float(m.group(4))
                            record.psnr_v = float(m.group(5))
                            continue
                        m = re.match(r"\s*Total Time:\s+(\d+\.\d+) sec\.", line)
                        if m:
                            record.encode_time = float(m.group(1))
                            break
                self._add_record(record)
        if rm_log:
            rmdir(self.log_dir)
        self.records = dict(sorted(self.records.items(), key=lambda kv: kv[0]))
        return self.records

    @staticmethod
    def get_valid_line_reg():
        # POC    0 TId: 0 ( I-SLICE, nQP 22 QP 22 )     175504 bits [Y 42.1911 dB    U 42.9498 dB    V 43.4990 dB] [ET     1 ] [L0 ] [L1 ]
        return r"\s*POC\s+(\d+)\s+TId:\s*(\d)\s*\( [I|P|B]-SLICE, nQP\s*(\d+)\s*QP\s*(\d+)\s*\)\s*(\d+)\s*bits\s*" \
               r"\[Y\s*(\d+\.\d+)\s*dB\s*U\s*(\d+\.\d+)\s*dB\s*V\s*(\d+\.\d+)\s*dB\]\s*\[ET\s*(\d+)\s*\].*"

    @staticmethod
    def get_end_line_reg():
        return r"SUMMARY --------------------------------------------------------"


class Scanner(object):
    def __init__(self,
                 log_dir: str,
                 seqs: list,
                 mode: Mode,
                 scanner: str = None,
                 output_excel: str = None,
                 template: str = None,
                 is_anchor: bool = False,
                 is_parallel: bool = False):
        """
        :param log_dir: 日志目录
        :param seqs: 要扫描的日志名称简写
        :param mode: 模式，"AI"\"LDB"\"LDP"\"RA"之一，用于决定excel表中的sheet
        :param scanner: Scanner的名称，目前支持"HPM"\"UAVS3E"
        :param output_excel: 指定输出的excel表格的名称
        :param template: 指定excel表格模板的名称
        :param is_anchor: 指定当前数据是否是anchor，用于决定Excel中sheet
        :param is_parallel: 指定当前日志是否是并行编码的，仅适用于HPM分片编码
        """
        if scanner is None:
            scanner = HpmScanner.__name__.lower()
        if scanner.lower() in HpmScanner.__name__.lower():
            self.scanner: AbsLogScanner = HpmScanner(log_dir, seqs, mode, output_excel, template, is_anchor,
                                                     is_parallel)
        else:
            is_parallel = False
            self.scanner: AbsLogScanner = Uavs3eScanner(log_dir, seqs, mode, output_excel, template, is_anchor,
                                                        is_parallel)

    def scan(self, filter_func: callable = None, rm_log=False):
        """
        :param filter_func: 用于过滤文件夹中的非目标文件
        :param rm_log: 当扫描完成时，是否删除log文件
        :return: 字典列表
        """
        return self.scanner.scan(filter_func, rm_log)

    def output(self):
        self.scanner.output()
