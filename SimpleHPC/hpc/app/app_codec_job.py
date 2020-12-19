import copy
import os
import re
from enum import Enum
from typing import Union, Optional, Type

from hpc.codec.codec_util import copy_del_rename
from hpc.codec.codec_util import memory
from hpc.codec.mode import Mode
from hpc.codec.logger_abc import AbsLogScanner
from hpc.core.helper import mkdir
from hpc.core.helper import path_join
from hpc.core.hpc_job import HpcJobManager
from hpc.core.local_job import JobManager
from hpc.core.net import Progress


class ProgressDIR(Enum):
    STDOUT = 0
    STDERR = 1
    NONE = 2


def main_codec(seq_info: list, qp_list: list, mode: Mode,
               who: str, email: str, hashcode: str,
               seqs_dir: str, temp_dir: str, workdir: str,
               bin_dir: str, rec_dir: str, dec_dir: str, stdout_dir: str, stderr_dir: str,
               gen_bin: bool, gen_rec: bool, gen_dec: bool, par_enc: bool,
               cores: int, nodes: Optional[str], groups: Optional[str], priority: Union[str, int],
               codec: Union[AbsLogScanner, Type[AbsLogScanner]],
               encoder_command: str, merger_command: Optional[str], decoder_command: Optional[str],
               track: ProgressDIR = ProgressDIR.STDOUT,
               sampling: int = 1,
               **extra_param):
    """
    执行一批编解码任务
    :param seq_info:
    :param qp_list:
    :param mode:
    :param who:
    :param email:
    :param hashcode:
    :param seqs_dir:
    :param temp_dir:
    :param workdir:
    :param bin_dir:
    :param rec_dir:
    :param dec_dir:
    :param stdout_dir:
    :param stderr_dir:
    :param gen_bin:
    :param gen_rec:
    :param gen_dec:
    :param par_enc:
    :param cores:
    :param nodes:
    :param groups:
    :param priority:
    :param codec:
    :param encoder_command:
    :param merger_command:
    :param decoder_command:
    :param track:
    :param sampling:
    :param extra_param:
    :return:
    """
    KEY_LOCAL = "local"
    local = extra_param.get(KEY_LOCAL) if extra_param.get(KEY_LOCAL) else not HpcJobManager.check_env()

    manager = HpcJobManager
    if local:
        manager = JobManager

    def refine_par():
        nonlocal bin_dir, rec_dir, dec_dir, par_enc, gen_rec, gen_dec, merger_command, decoder_command
        if not gen_bin:
            bin_dir = None
        if not gen_rec:
            rec_dir = None
        if not gen_dec:
            dec_dir = None
            decoder_command = None
        if "hpm" not in str(codec).lower():
            merger_command = None
            par_enc = False
        if merger_command is None:
            par_enc = False
        if decoder_command is None:
            gen_dec = False
            dec_dir = None
        if mode != Mode.RA:
            par_enc = False

    def ensure_dir():
        for d in [bin_dir, dec_dir, rec_dir, stdout_dir, stderr_dir]:
            if d is not None and len(str(d)) > 0:
                mkdir(d, workdir)
        if local:
            mkdir(temp_dir)

    refine_par()
    ensure_dir()
    job_id_list = list()
    for seq in seq_info:
        if len(seq) == 8:
            name, width, height, fps, bit_depth, frames, ip, skip = seq
        elif len(seq) == 7:
            name, width, height, fps, bit_depth, frames, ip = seq
            skip = None
        else:
            return False
        name = rf"{name}_{width}x{height}_{fps}"
        extra_param["name"] = name
        mem = memory(width, height)
        for qp in qp_list:
            name_qp = f"{name}_{qp}"
            job_name = f"{who}_{hashcode}_{mode.value}_{name}_{qp}"
            job_id = manager.new(jobname=job_name, priority=priority, emailaddress=email)
            if job_id:
                rcs = 1
                frames_list = list()
                skip_list = list()
                skip_list.append(0)
                if par_enc:
                    rcs = (frames + ip - 1) // ip
                    encoded_frames = 0
                    for i in range(rcs):
                        if i != 0:
                            skip_list.append(encoded_frames)
                        frames_list.append(min(ip + 1, frames - encoded_frames))
                        encoded_frames += ip
                else:
                    frames_list.append(frames)

                def get_name(file_name, idx, prefix, suffix):
                    if par_enc and idx >= 0:
                        return f"{prefix}_{file_name}_{idx + 1}.{suffix}"
                    else:
                        return f"{prefix}_{file_name}.{suffix}"

                copy_bin_cmd_list = list()
                copy_rec_cmd_list = list()
                encoder_cmd_list = list()
                bitstream_list = list()
                bitstream = None

                for idx in range(rcs):
                    if par_enc:
                        extra_param["skip_frames"] = skip_list[idx]
                    if gen_bin:
                        bitstream = get_name(job_name, idx, "bin", "bin")
                        bitstream = path_join(bitstream, temp_dir)
                        copy_bin_cmd = copy_del_rename(bitstream, bin_dir, get_name(name_qp, idx, "bin", "bin"),
                                                       local=local)
                    else:
                        bitstream = os.devnull
                        copy_bin_cmd = None

                    if gen_rec:
                        reconstruction = get_name(job_name, idx, "rec", "yuv")
                        reconstruction = path_join(reconstruction, temp_dir)
                        copy_rec_cmd = copy_del_rename(reconstruction, rec_dir, get_name(name_qp, idx, "rec", "yuv"),
                                                       local=local)
                    else:
                        reconstruction = os.devnull
                        copy_rec_cmd = None

                    # 离线编解码命令
                    if skip is not None:
                        encoder_cmd = encoder_command.format(rf"{seqs_dir}\{name}.yuv",
                                                             width, height, fps, bit_depth, frames_list[idx], ip, skip,
                                                             qp, bitstream, reconstruction, **extra_param)
                    else:
                        encoder_cmd = encoder_command.format(rf"{seqs_dir}\{name}.yuv",
                                                             width, height, fps, bit_depth, frames_list[idx], ip,
                                                             qp, bitstream, reconstruction, **extra_param)
                    bitstream_list.append(bitstream)
                    copy_bin_cmd_list.append(copy_bin_cmd)
                    copy_rec_cmd_list.append(copy_rec_cmd)
                    encoder_cmd_list.append(encoder_cmd)

                if par_enc and gen_bin and len(bitstream_list) > 1 and "-i" in merger_command:
                    bitstream = get_name(job_name, -1, "bin", "bin")
                    bitstream = path_join(bitstream, temp_dir)
                    t = re.findall(r"-i\s+{}", merger_command)[0]
                    merger_command = merger_command.replace(t, " ".join([t] * len(bitstream_list)))
                    merger_cmd = merger_command.format(*bitstream_list, bitstream)
                    copy_bin_cmd = copy_del_rename(bitstream, bin_dir, get_name(name_qp, -1, "bin", "bin"), local=local)
                    copy_bin_cmd_list.append(copy_bin_cmd)
                else:
                    merger_cmd = None
                if gen_bin and gen_dec:
                    decode = get_name(job_name, -1, "dec", "yuv")
                    decode = path_join(decode, temp_dir)
                    decoder_cmd = decoder_command.format(bitstream, decode)
                    copy_dec_cmd = copy_del_rename(decode, dec_dir, get_name(name_qp, -1, "dec", "yuv"), local=local)
                else:
                    decoder_cmd = None
                    copy_dec_cmd = None

                depend = []
                # encode copy_rec merge decode copy_dec copy_bin
                prefixes = ["encode", "", "", "decode", "", ""]
                commands = [encoder_cmd_list, copy_rec_cmd_list, merger_cmd, decoder_cmd,
                            copy_dec_cmd, copy_bin_cmd_list]
                for i, (prefix, cmd) in enumerate(zip(prefixes, commands)):
                    if isinstance(cmd, str):
                        if prefix is None or len(prefix) == 0:
                            stdout = None
                            stderr = None
                        else:
                            stdout = path_join(get_name(name_qp, -1, prefix, "out"), stdout_dir)
                            stderr = path_join(get_name(name_qp, -1, prefix, "err"), stderr_dir)
                        task_name = f"{i}_{job_name}"
                        success = manager.add(job_id, cmd, name=task_name, numcores=cores,
                                              workdir=workdir, stdout=stdout, stderr=stderr,
                                              depend=",".join(depend))
                        if success:
                            depend.append(task_name)
                    elif isinstance(cmd, list) or isinstance(cmd, tuple):
                        temp_depend = copy.deepcopy(depend)
                        for j, c in enumerate(cmd):
                            if prefix is None or len(prefix) == 0:
                                stdout = None
                                stderr = None
                            else:
                                stdout = path_join(get_name(name_qp, j, prefix, "out"), stdout_dir)
                                stderr = path_join(get_name(name_qp, j, prefix, "err"), stderr_dir)
                            task_name = f"{i}_{j}_{job_name}"
                            success = manager.add(job_id, c, name=task_name, numcores=cores,
                                                  workdir=workdir, stdout=stdout, stderr=stderr,
                                                  depend=",".join(temp_depend))
                            if success:
                                depend.append(task_name)
                        del temp_depend

                manager.submit(job_id, nodegroup=groups, requestednodes=nodes, memorypernode=mem)
                job_id_list.append(job_id)
                track_file = None
                if track != ProgressDIR.NONE and not local:
                    if par_enc:
                        if track == ProgressDIR.STDOUT:
                            track_file = path_join(get_name(name_qp, 0, prefixes[0], "out"), stdout_dir)
                        elif track == ProgressDIR.STDERR:
                            track_file = path_join(get_name(name_qp, 0, prefixes[0], "err"), stderr_dir)
                    else:
                        if track == ProgressDIR.STDOUT:
                            track_file = path_join(get_name(name_qp, -1, prefixes[0], "out"), stdout_dir)
                        elif track == ProgressDIR.STDERR:
                            track_file = path_join(get_name(name_qp, -1, prefixes[0], "err"), stderr_dir)
                    Progress.notice(job_id, (frames + sampling - 1) // sampling,
                                    codec.get_valid_line_reg(), codec.get_end_line_reg(), track_file)
    return job_id_list


if __name__ == '__main__':
    pass
