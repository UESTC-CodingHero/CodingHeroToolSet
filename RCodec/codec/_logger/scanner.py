"""
此文件用于扫描编码日志，并提供编码的summary
具体工作方式为：

根据编码log的目录，遍历每个合法的编码log文件，编码log的合法性由filter_func来验证
然后打开该log文件，根本不同的编码器，读取summary信息，生成Record。

一个Record记录一个序列在特定QP下的Summary，也就是Excel表中的一行，通常一个序列有4个QP，也就是4个Record
整个文件夹中的全部log都会保存到records这个变量中，此结构为字典，键为序列ID，值为该序列对应的4个Record列表

最终，将Record保存到指定的文件中或者输出到屏幕

"""
import os
import re
import sys
from enum import Enum
from typing import Optional, Union, IO, Sequence, Dict, Callable
from hpc.helper import path_join
from .excel_handler import Excel, ExcelHelper
from .record import Record
from ..common import Mode, PatKey, ConfigKey
from .._runner.codec_runner import Codec


class _ScanType(Enum):
    LIN = 0b01  # line
    SUM = 0b10  # summary
    BOT = 0b11  # both

    def __contains__(self, item):
        return item.value & self.value != 0


class LogScanner(object):
    def __init__(self, codec: Codec,
                 enc_log_dir: str, dec_log_dir: Optional[str],
                 seqs: Sequence[str], qps: Sequence[int], mode: Mode, is_separate: bool = False):
        """
        初始化一个日志扫描器

        :param codec: 编码器
        :param enc_log_dir: 编码日志文件所在的目录
        :param dec_log_dir: 解码日志文件所在的目录
        :param seqs: 需要扫描的序列列表，序列的ID由序列在该列表的顺序确定
        :param qps: 需要扫描的QP列表
        :param mode: 当前编码的模式，用于确定在输出excel的位置
        :param is_separate: 是否为分片编码。
        """
        self.codec: Codec = codec
        self.enc_log_dir: str = enc_log_dir
        self.dec_log_dir: str = dec_log_dir
        self.mode: Mode = mode
        self.seqs: Sequence[str] = seqs
        self.qps: Sequence[int] = qps
        self.is_separate: bool = is_separate
        self.records: Dict[int, Sequence[Record]] = dict()

    def _add_record(self, record: Record):
        """
        统一管理，将一个新的记录添加到成员变量中
        :param record: 新的记录
        """
        # 此处已经根据ID排序
        if record is None:
            return
        self.records[record.id] = (self.records.get(record.id) or list()) + [record]

    def _log_check(self, log_dir: str, log_file: str):
        if log_file is None or not os.path.exists(os.path.join(log_dir, log_file)):
            return None, None, None
        file = os.path.basename(log_file)
        _id = ExcelHelper.seq_id(self.seqs, file)
        if _id is None:
            return None, None, None
        return _id, self.seqs[_id], file

    def _scan_log(self, log_dir: str, log_file: str, key_set: Sequence[type(PatKey.Summary_Psnr_Y)],
                  record: Record) -> Record:
        with open(os.path.join(log_dir, log_file)) as fp:
            for line in fp:
                line = line.strip()
                for key in key_set:
                    m = re.match(self.codec.pattern[key], line)
                    if m:
                        record[key] = m.group(key)
        return record

    def _scan_enc_log(self, enc_file: str, scan_type=_ScanType.BOT) -> Optional[Record]:
        """
        从编码文件中获取编码信息
        :param enc_file: 编码日志文件
        :return: 一个record记录
        """
        _id, name, file = self._log_check(self.enc_log_dir, enc_file)
        if _id is None or name is None or file is None:
            return None
        record = Record(_id, self.mode, name)
        if self.is_separate:
            record.qp = int(file.split("_")[-2])
        else:
            record.qp = int(file.split("_")[-1].split(".")[0])
        key_set = list()
        if _ScanType.LIN in scan_type:
            key_set += PatKey.line_patterns()
        if _ScanType.SUM in scan_type:
            key_set += PatKey.summary_patterns()
        record = self._scan_log(self.enc_log_dir, enc_file, key_set, record)
        return record

    def _scan_dec_log(self, dec_file: Optional[str]) -> Optional[Record]:
        """
        从解码文件中获取解码时间
        :param dec_file: 解码日志文件
        :return: 解码时间
        """
        _id, name, file = self._log_check(self.dec_log_dir, dec_file)
        if _id is None or name is None or file is None:
            return None
        record = Record(_id, self.mode, name)
        record.qp = int(file.split("_")[-1].split(".")[0])
        key_set = PatKey.summary_patterns_dec()
        record = self._scan_log(self.dec_log_dir, dec_file, key_set, record)
        return record

    def scan(self,
             filter_func_enc: Optional[Callable[[str], bool]] = None,
             filter_func_dec: Optional[Callable[[str], bool]] = None):
        """
        执行扫描任务。从给定的文件夹中，挑选指定的文件进行解析
        :param filter_func_enc: 过滤掉不关心的编码日志文件
        :param filter_func_dec: 过滤掉不关心的解码日志文件
        :return: 字典。key为所在序列的ID，value为当前序列对应的不同QP下的Record列表
        """
        enc_files = os.listdir(self.enc_log_dir)
        if filter_func_enc:
            enc_files = list(filter(filter_func_enc, enc_files))

        dec_files = os.listdir(self.dec_log_dir)
        if filter_func_dec:
            dec_files = list(filter(filter_func_dec, dec_files))

        # 为了zip，在没有解码日志的情况下，后面的代码也能正常work
        if len(dec_files) != len(enc_files):
            dec_files = [None] * len(enc_files)

        # 如果是 separate 模式，log文件名格式为 prefix_name_wxh_fps_qp_idx.xxx
        # 如果非 separate 模式，log文件名格式为 prefix_name_wxh_fps_qp.xxx
        if self.is_separate:
            for _id, seq in enumerate(self.seqs):
                cur_seq_log_files = [f for f in enc_files if seq in f]
                # key is qp, value is file list
                temp_dict = dict()
                for file in cur_seq_log_files:
                    qp = int(file.split("_")[-2])
                    qp_files = temp_dict.get(qp) or list()
                    qp_files.append(file)
                    temp_dict[qp] = qp_files

                for qp, files in temp_dict.items():
                    # 根据每个子片段的序号排序,
                    files.sort(key=lambda fn: int(str(fn).split("_")[-1].split(".")[0]))

                    record = Record(_id, self.mode, seq)
                    record.qp = qp

                    join = os.path.join
                    records = [self._scan_enc_log(join(self.enc_log_dir, f), scan_type=_ScanType.BOT) for f in files]

                    # 对于PSNR的计算，将每个子流log的平均PSNR乘以帧数，求和后再减去非第一个子流的首帧的PSNR,时间也是类似的
                    # 求和
                    fps = int(files[0].split("_")[-3])
                    frames = 0
                    for i, record_temp in enumerate(records):
                        # @formatter:off
                        for (key_summary, key_line) in [zip(PatKey.summary_psnr_patters(), PatKey.line_psnr_patters())]:
                            record[key_summary] += record_temp[key_summary] * len(record_temp[key_line])
                        record[PatKey.Summary_Encode_Time] += record_temp[PatKey.Summary_Encode_Time]
                        frames += len(record_temp[PatKey.Line_Psnr_Y])
                        # @formatter:on

                    # 减去首帧的PSNR和时间
                    for i, record_temp in enumerate(records):
                        if i != 0:
                            frames -= 1
                            for (key_summary, key_line) in [
                                zip(PatKey.summary_psnr_patters() + [PatKey.Summary_Encode_Time],
                                    PatKey.line_psnr_patters() + [PatKey.Line_Time])]:
                                assert isinstance(record_temp[key_line], Record.Container)
                                record[key_summary] = record[key_summary] - record_temp[key_line][0]

                    # 对 PSNR 取平均
                    for key_summary in [PatKey.Summary_Psnr_Y, PatKey.Summary_Psnr_U, PatKey.Summary_Psnr_V]:
                        record[key_summary] = record[key_summary] / frames

                    # 计算bitrate
                    # 读取拼接码流的文件大小, 拼接码流文件名格式: a_prefix_name_wxh_fps_qp.suffix
                    bitstream_dir = self.codec.info.sub_dirs[ConfigKey.BIN_DIR]
                    temp = os.listdir(bitstream_dir)
                    temp = list(filter(lambda fn: seq in fn and str(qp) in fn and fn.endswith(self.codec.suffix), temp))
                    if len(temp) == 1:
                        fd = path_join(temp[0], bitstream_dir)
                        # in bytes
                        record.bits = os.stat(fd).st_size

                        # FIXME: HPM需要减掉以下2个部分，其他编码器未知。。。
                        if self.codec.name.upper() == "HPM":
                            # video end code
                            record.bits -= 4
                            # md5
                            record.bits -= frames * 23

                        # to bits
                        record.bits <<= 3

                        record.bitrate = fps * record.bits / frames / 1000
                    self._add_record(record)
        else:
            for enc_file, dec_file in zip(enc_files, dec_files):
                _id = ExcelHelper.seq_id(self.seqs, enc_file)
                if _id is None:
                    continue
                record = self._scan_enc_log(enc_file, scan_type=_ScanType.SUM)
                record_dec = self._scan_dec_log(dec_file)
                if record_dec is not None:
                    assert record_dec.id == record.id and record.qp == record_dec.qp
                    record[PatKey.Summary_Decode_Time] = record_dec[PatKey.Summary_Decode_Time]
                self._add_record(record)
        self.records = dict(sorted(self.records.items(), key=lambda kv: kv[0]))
        return self.records

    def output(self, filename: Optional[Union[IO, str]] = None, is_anchor: bool = True) -> bool:
        """
        将日志信息输出到标准输出或普通文本文件或者Excel文件
        当未指定"filename"时，输出到标准输出
        如果仅指定了"filename"，没有额外参数时，输出到普通文本文件
        如果指定了"filename"，并且有参数"anchor"和"excel"，则将"filename"作为输入文件并将结果输出到"excel"指定的文件
        """
        if filename is None:
            target = sys.stdout
        elif isinstance(filename, IO):
            target = filename
        elif not ExcelHelper.is_excel_file(filename):
            target = open(filename, "w+")
        else:
            if not os.path.exists(filename):
                target = Excel.from_template(self.seqs, self.qps, mode=self.mode)
            else:
                target = Excel(filename)
                if self.mode not in target:
                    target.new_mode_sheet(self.seqs, self.qps, self.mode)
        try:
            if target:
                if isinstance(target, Excel):
                    ExcelHelper.fill_raw_data(target, is_anchor, self.records, seqs=self.seqs, qps=self.qps)
                    target.save(filename)
                else:
                    for name, records4 in self.records.items():
                        records4 = sorted(records4, key=lambda r: int(r.qp))
                        for record in records4:
                            print(record, file=target)
                if filename is not None and filename != sys.stderr and filename != sys.stdout:
                    print(f"Save to '{filename}'")
                    target.close()
                return True
            return False
        except Exception as e:
            print(e)
            return False
