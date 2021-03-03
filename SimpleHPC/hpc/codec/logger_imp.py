import os
import re

from hpc.codec.logger_abc import AbsLogScanner, Record
from hpc.core.helper import rmdir
from typing import Optional
from hpc.codec.mode import Mode
from hpc.codec.resource import AVS3_CTC_TEMPLATE


def _trim_non_digital(s: str):
    ret = ""
    started = False

    def is_digital(c):
        return ord('9') >= ord(c) >= ord('0')

    for ch in s:
        if started and not is_digital(ch):
            break
        if is_digital(ch):
            started = True
            ret += ch
    return ret


class HpmScanner(AbsLogScanner):
    def __init__(self, enc_log_dir: str, dec_log_dir: Optional[str], seqs: list, mode: Mode,
                 output_excel: str = None,
                 template: str = None,
                 is_anchor: bool = False,
                 is_separate: bool = False):
        if template is None and output_excel is not None:
            template = AVS3_CTC_TEMPLATE

        super().__init__(enc_log_dir, dec_log_dir, seqs, mode, output_excel, template, is_anchor, is_separate)

    def _scan_a_file(self, abs_path, remove_first_I: int = False):
        file = os.path.basename(abs_path)
        _id, name = self._in_dict(file)
        if _id is None or name is None:
            return None
        record = Record(_id, self.mode, name)
        if self.is_separate:
            record.qp = int(_trim_non_digital(file.split("_")[-2]))
        else:
            record.qp = int(_trim_non_digital(file.split("_")[-1].split(".")[0]))
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
                    # second
                    sp = line.split("=")[1].strip().split(" ")
                    record.encode_time = float(sp[2])
        if remove_first_I:
            found = False
            psnr_y = psnr_u = psnr_v = bits = time = ssim_y = 0
            fps = 0
            with open(os.path.join(abs_path), "r") as fp:
                for line in fp:
                    line = line.strip()
                    if "FPS" in line and ":" in line:
                        fps = int(line.split(":")[1].strip())
                        continue
                    match = re.match(HpmScanner.get_valid_line_reg(), line)
                    if match:
                        if "( I)" in line:
                            found = True
                            psnr_y = float(match.group(3))
                            psnr_u = float(match.group(4))
                            psnr_v = float(match.group(5))
                            bits = int(match.group(6))
                            time = int(match.group(7))
                            ssim_y = float(match.group(8))
                            break
            if found and fps > 0:
                record.psnr_y = (record.psnr_y * record.frames - psnr_y) / (record.frames - 1)
                record.psnr_u = (record.psnr_u * record.frames - psnr_u) / (record.frames - 1)
                record.psnr_v = (record.psnr_v * record.frames - psnr_v) / (record.frames - 1)
                record.ssim_y = (record.ssim_y * record.frames - ssim_y) / (record.frames - 1)
                record.frames -= 1
                record.bits -= bits
                record.bitrate = record.bits * record.frames / fps
                record.encode_time = (record.encode_time * 1000 - time) / 1000
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
        if self.is_separate:
            enc_files = list(filter(lambda fn: len(re.findall(r"\d+x\d+_\d+\S*_\d+_\d+\.\S+", fn)) > 0, enc_files))
            for _id, seq in enumerate(self.seqs):
                cur_seq_log_files = [f for f in enc_files if seq in f]
                # key is qp, value is file list
                temp_dict = dict()
                for file in cur_seq_log_files:
                    qp = int(_trim_non_digital(file.split("_")[-2]))
                    qp_files = temp_dict.get(qp) or list()
                    qp_files.append(file)
                    # sort by sub index
                    qp_files.sort(key=lambda fn: int(str(fn).split("_")[-1].split(".")[0]))
                    temp_dict[qp] = qp_files
                for qp, files in temp_dict.items():
                    record = Record(_id, self.mode, seq)
                    fps = int(_trim_non_digital(files[0].split("_")[-3]))
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
                    records = [self._scan_a_file(os.path.join(self.enc_log_dir, f), remove_first_I=(i > 0))
                               for i, f in enumerate(files)]
                    for r in records:
                        if r is None:
                            print("WARNING")
                            continue
                        assert r.qp == qp
                        record.frames += r.frames
                        record.psnr_y += r.psnr_y * r.frames
                        record.psnr_u += r.psnr_u * r.frames
                        record.psnr_v += r.psnr_v * r.frames
                        record.ssim_y += r.ssim_y * r.frames
                        record.bits += r.bits
                        record.encode_time += r.encode_time
                    if record.frames != 0:
                        # read size from concat bitstream
                        fd = "_".join(str(files[0]).split("_")[1:-1]) + ".bin"
                        fdd = os.path.join(self.enc_log_dir, "..", "bin")
                        temp = os.listdir(fdd)
                        temp = list(filter(lambda fn: fd in fn, temp))
                        if len(temp) == 1:
                            fd = temp[0]
                            fd = os.path.join(fdd, fd)
                            # in bytes
                            record.bits = os.stat(fd).st_size
                            # video end code
                            record.bits -= 4
                            # md5
                            record.bits -= record.frames * 23

                            # to bits
                            record.bits <<= 3

                            record.psnr_y /= record.frames
                            record.psnr_u /= record.frames
                            record.psnr_v /= record.frames
                            record.ssim_y /= record.frames
                            record.bitrate = fps * record.bits / record.frames / 1000
                    self._add_record(record)
        else:
            for enc_file, dec_file in zip(enc_files, dec_files):
                _id, name = self._in_dict(enc_file)
                if _id is None or name is None:
                    continue
                if name is not None:
                    record = self._scan_a_file(os.path.join(self.enc_log_dir, enc_file), remove_first_I=False)
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
                record.qp = int(_trim_non_digital(enc_file.split("_")[-1].split(".")[0]))
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


class SupportCodec:
    HPM = HpmScanner
    UAVS3 = Uavs3eScanner
    HM = HMScanner
