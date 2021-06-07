from typing import Optional

from ..common import PatKey, ConfigKey

_DEFAULT_DICT = dict()
_DEFAULT_SUF = ""
_DEFAULT_DIR = ConfigKey.STDOUT_DIR
_DEFAULT_PAT = ".+"


class ParamExe(object):
    def __init__(self, name: str, param_key: Optional[dict] = None, ):
        self.name = name
        self.param_key = param_key if param_key else _DEFAULT_DICT


class Decoder(ParamExe):
    def __init__(self, name: str, param_key: Optional[dict] = None, log_dir_type: str = _DEFAULT_DIR,
                 p_summary_decode_time: str = _DEFAULT_PAT):
        super().__init__(name, param_key)
        self.log_dir_type = log_dir_type

        self.pattern = dict()
        self.pattern[PatKey.Summary_Decode_Time] = p_summary_decode_time


class Merger(ParamExe):
    def __init__(self, name: str,
                 param_key: Optional[dict] = None):
        super().__init__(name, param_key)


class Encoder(ParamExe):
    def __init__(self, name: str,
                 param_key: Optional[dict] = None,
                 suffix: str = _DEFAULT_SUF,
                 log_dir_type: str = _DEFAULT_DIR,
                 p_log_line: str = _DEFAULT_PAT,
                 p_summary_psnr_y: str = _DEFAULT_PAT,
                 p_summary_psnr_u: str = _DEFAULT_PAT,
                 p_summary_psnr_v: str = _DEFAULT_PAT,
                 p_summary_bitrate: str = _DEFAULT_PAT,
                 p_summary_encode_time: str = _DEFAULT_PAT):
        super().__init__(name, param_key)
        self.suffix = suffix
        self.log_dir_type = log_dir_type

        self.pattern = dict()
        self.pattern[PatKey.Line_Psnr_Y] = p_log_line
        self.pattern[PatKey.Line_Psnr_U] = p_log_line
        self.pattern[PatKey.Line_Psnr_V] = p_log_line
        self.pattern[PatKey.Line_Bit] = p_log_line
        self.pattern[PatKey.Line_Time] = p_log_line
        self.pattern[PatKey.Summary_Psnr_Y] = p_summary_psnr_y
        self.pattern[PatKey.Summary_Psnr_U] = p_summary_psnr_u
        self.pattern[PatKey.Summary_Psnr_V] = p_summary_psnr_v
        self.pattern[PatKey.Summary_Bitrate] = p_summary_bitrate
        self.pattern[PatKey.Summary_Encode_Time] = p_summary_encode_time
