import os
import re

from hpc.codec.logger_abc import AbsLogScanner, Record
from hpc.core.helper import rmdir
from typing import Optional
from hpc.codec.mode import Mode
from hpc.codec.resource import AVS3_CTC_TEMPLATE


class HpmScanner(AbsLogScanner):
    def __init__(self, enc_log_dir: str, dec_log_dir: Optional[str], seqs: list, mode: Mode,
                 output_excel: str = None,
                 template: str = None,
                 is_anchor: bool = False,
                 is_separate: bool = False):
        if template is None and output_excel is not None:
            template = AVS3_CTC_TEMPLATE

        super().__init__(enc_log_dir, dec_log_dir, seqs, mode, output_excel, template, is_anchor, is_separate)

    def _scan_a_file(self, abs_path):
        file = os.path.basename(abs_path)
        _id, name = self._in_dict(file)
        assert name is not None
        record = Record(_id, self.mode, name)
        if self.is_separate:
            record.qp = int(file.split("_")[-2])
        else:
            record.qp = int(file.split("_")[-1].split(".")[0])
        with open(os.path.join(abs_path), "r") as fp:
            for line in fp:
                line = line.strip()
                if "PSNR Y(dB)" in line:
                    record.psnr_y = float(line.split(":")[1].strip())
                elif "PSNR U(dB)" in line:
                    record.psnr_u = float(line.split(":")[1].strip())
                elif "PSNR V(dB)" in line:
                    record.psnr_v = float(line.split(":")[1].strip())
                elif "MsSSIM_Y" in line:
                    record.ssim_y = float(line.split(":")[1].strip())
                elif "Total bits(bits)" in line:
                    record.bits = int(line.split(":")[1].strip())
                elif "bitrate(kbps)" in line:
                    record.bitrate = float(line.split(":")[1].strip())
                elif "Encoded frame count" in line:
                    record.frames = int(line.split("=")[1].strip())
                elif "Total encoding time" in line:
                    sp = line.split("=")[1].strip().split(" ")
                    record.encode_time = float(sp[2])
        return record

    def scan(self, filter_func_enc: callable = None, filter_func_dec: callable = None, rm_log: bool = False):
        enc_files = os.listdir(self.enc_log_dir)
        if callable(filter_func_enc):
            enc_files = list(filter(filter_func_enc, enc_files))
        dec_files = os.listdir(self.dec_log_dir)
        if callable(filter_func_dec):
            dec_files = list(filter(filter_func_dec, dec_files))
        if len(dec_files) != len(enc_files):
            dec_files = [""] * len(enc_files)
        # TODO do merge first
        if self.is_separate:
            enc_files = list(filter(lambda fn: len(re.findall(r"\d+x\d+_\d+\S*_\d+_\d+\.\S+", fn)) > 0, enc_files))
            for _id, seq in enumerate(self.seqs):
                cur_seq_log_files = [f for f in enc_files if seq in f]
                # key is qp, value is file list
                temp_dict = dict()
                for file in cur_seq_log_files:
                    qp = int(file.split("_")[-2])
                    qp_files = temp_dict.get(qp) or list()
                    qp_files.append(file)
                    qp_files.sort(key=lambda fn: int(str(fn).split("-")[-1].split(".")[0]))
                    temp_dict[qp] = qp_files
                for qp, files in temp_dict.items():
                    record = Record(_id, self.mode, seq)
                    record.qp = qp
                    record.frames = 0
                    record.psnr_y = 0
                    record.psnr_u = 0
                    record.psnr_v = 0
                    record.bitrate = 0
                    record.bits = 0
                    record.encode_time = 0
                    record.decode_time = 0
                    record.ssim_y = 0
                    records = [self._scan_a_file(os.path.join(self.enc_log_dir, f)) for f in files]
                    for r in records:
                        assert r.qp == qp
                        record.frames += r.frames
                        record.psnr_y += r.psnr_y * r.frames
                        record.psnr_u += r.psnr_u * r.frames
                        record.psnr_v += r.psnr_v * r.frames
                        record.ssim_y += r.ssim_y * r.frames
                        record.bitrate += r.bitrate * r.frames
                        record.bits += r.bits
                        record.encode_time += r.encode_time

        else:
            for enc_file, dec_file in zip(enc_files, dec_files):
                _id, name = self._in_dict(enc_file)
                assert name is not None
                if name is not None:
                    record = self._scan_a_file(os.path.join(self.enc_log_dir, enc_file))
                    record.decode_time = \
                        self._get_decode_time(dec_file,
                                              r"\s*total decoding time\s+=\s*\d+\s*msec,\s*(\d+\.\d+)\s*sec",
                                              enc_file)
                    self._add_record(record)
        if rm_log:
            rmdir(self.enc_log_dir)
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
    def scan(self, filter_func_enc: callable = None, filter_func_dec: callable = None, rm_log: bool = False):
        self.is_separate = False
        return super().scan(filter_func_enc, filter_func_dec, rm_log)

    @staticmethod
    def get_valid_line_reg():
        return r"\s*(\d+)\s*\(\s*[I|P|B]\)\|\s*(\d+\.\d+)\|\s*(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\|.+"

    @staticmethod
    def get_end_line_reg():
        return r"Encoded\s*frame\s*count\s+=\s*(\d+)"


class HMScanner(AbsLogScanner):
    def scan(self, filter_func_enc: callable = None, filter_func_dec: callable = None, rm_log: bool = False):
        enc_files = os.listdir(self.enc_log_dir)
        if callable(filter_func_enc):
            enc_files = list(filter(filter_func_enc, enc_files))
        dec_files = os.listdir(self.dec_log_dir)
        if callable(filter_func_dec):
            dec_files = list(filter(filter_func_dec, dec_files))
        if len(dec_files) != len(enc_files):
            dec_files = [""] * len(enc_files)
        for enc_file, dec_file in zip(enc_files, dec_files):
            _id, name = self._in_dict(enc_file)
            assert name is not None
            if name is not None:
                record = Record(_id, self.mode, name)
                record.qp = int(enc_file.split("_")[-1].split(".")[0])
                with open(os.path.join(self.enc_log_dir, enc_file), "r") as fp:
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

                record.decode_time = self._get_decode_time(dec_file,
                                                           r"\s*Total Time:\s+(\d+\.\d+)\s*sec.",
                                                           enc_file)

                self._add_record(record)
        if rm_log:
            rmdir(self.enc_log_dir)
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


# class Scanner(object):
#     def __init__(self,
#                  enc_log_dir: str,
#                  dec_log_dir: str,
#                  seqs: list,
#                  mode: Mode,
#                  scanner: str = None,
#                  output_excel: str = None,
#                  template: str = None,
#                  is_anchor: bool = False,
#                  is_parallel: bool = False):
#         """
#         :param enc_log_dir: 编码日志目录
#         :param dec_log_dir: 解码日志目录
#         :param seqs: 要扫描的日志名称简写
#         :param mode: 模式，"AI"\"LDB"\"LDP"\"RA"之一，用于决定excel表中的sheet
#         :param scanner: Scanner的名称，目前支持"HPM"\"UAVS3E"
#         :param output_excel: 指定输出的excel表格的名称
#         :param template: 指定excel表格模板的名称
#         :param is_anchor: 指定当前数据是否是anchor，用于决定Excel中sheet
#         :param is_parallel: 指定当前日志是否是并行编码的，仅适用于HPM分片编码
#         """
#         if scanner is None:
#             scanner = HpmScanner.__name__.lower()
#         if scanner.lower() in HpmScanner.__name__.lower():
#             self.scanner: AbsLogScanner = HpmScanner(enc_log_dir, dec_log_dir, seqs, mode, output_excel, template,
#                                                      is_anchor, is_parallel)
#         else:
#             is_parallel = False
#             self.scanner: AbsLogScanner = Uavs3eScanner(enc_log_dir, dec_log_dir, seqs, mode, output_excel, template,
#                                                         is_anchor, is_parallel)
#
#     def scan(self, filter_func_enc: callable = None, filter_func_dec: callable = None, rm_log: bool = False):
#         """
#         :param filter_func_enc: 用于过滤文件夹中的非目标编码日志文件
#         :param filter_func_dec: 用于过滤文件夹中的非目标解码日志文件
#         :param rm_log: 当扫描完成时，是否删除log文件
#         :return: 字典列表
#         """
#         return self.scanner.scan(filter_func_enc, filter_func_dec, rm_log)
#
#     def output(self):
#         self.scanner.output()


class SupportCodec:
    HPM = HpmScanner
    UAVS3 = Uavs3eScanner
    HM = HMScanner
