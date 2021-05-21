from enum import Enum


class Mode(Enum):
    AI = "AI"
    RA = "RA"
    LB = "LB"
    LP = "LP"
    IBBB = "IBBB"
    IPPP = "IPPP"
    OTHER = "OTHER"


class TaskType(Enum):
    ENCODE_DECODE = 1
    SCAN_ANCHOR = 2
    SCAN_TEST = 3
    CLEAN = 4
    EXIT = 0


class LoggerOutputType(Enum):
    STDOUT = 0
    STDERR = 1
    NORMAL = 2
    EXCEL = 3


class ParamType(object):
    # options for encoder
    CfgEncoder = "encoder_cfg"
    CfgSequence = "sequence_cfg"
    Sequence = "sequence"
    Width = "width"
    Height = "height"
    Fps = "fps"
    BitDepth = "bit_depth"
    QP = "qp"
    Frames = "frames"
    IntraPeriod = "intra_period"
    SkipFrames = "skip_frames"
    TemporalSampling = "temporal_sampling"
    OutBitStream = "out_bit_stream"
    OutReconstruction = "out_reconstruction"

    # options for decoder
    InBitStream = "in_bit_stream"
    DecodeYUV = "decoder_yuv"

    # options for bitstream merger
    MergeInBitStream = "merge_in_bit_stream"
    MergeOutBitStream = "merge_out_bit_stream"

    ExtraParam = "extra_param"


class PatKey(object):
    Line_Psnr_Y = "lpy"
    Line_Psnr_U = "lpu"
    Line_Psnr_V = "lpv"
    Line_Bit = "lb"
    Line_Time = "lt"
    Summary_Psnr_Y = "spy"
    Summary_Psnr_U = "spu"
    Summary_Psnr_V = "spv"
    Summary_Bitrate = "sb"
    Summary_Encode_Time = "set"
    Summary_Decode_Time = "sdt"

    @staticmethod
    def line_patterns():
        return [
            PatKey.Line_Psnr_Y,
            PatKey.Line_Psnr_U,
            PatKey.Line_Psnr_V,
            PatKey.Line_Bit,
            PatKey.Line_Time,
        ]

    @staticmethod
    def summary_patterns():
        return [
            PatKey.Summary_Bitrate,
            PatKey.Summary_Psnr_Y,
            PatKey.Summary_Psnr_U,
            PatKey.Summary_Psnr_V,
            PatKey.Summary_Encode_Time,
        ]

    @staticmethod
    def summary_patterns_dec():
        return [PatKey.Summary_Decode_Time]

    @staticmethod
    def line_psnr_patters():
        return PatKey.line_patterns[0:3]

    @staticmethod
    def summary_psnr_patters():
        return PatKey.summary_patterns[1:4]


class ConfigKey(object):
    CFG_DIR = "dir_cfg"
    CFG_PAT = "pat_cfg"
    TMP_DIR = "dir_tmp"

    BIN_DIR = "dir_bin"
    REC_DIR = "dir_rec"
    DEC_DIR = "dir_dec"
    STDOUT_DIR = "dir_stdout"
    STDERR_DIR = "dir_stderr"

    PREFIX_ENCODE = "prefix_encode"
    PREFIX_DECODE = "prefix_decode"

    SUFFIX_STDOUT = "suffix_stdout"
    SUFFIX_STDERR = "suffix_stderr"
