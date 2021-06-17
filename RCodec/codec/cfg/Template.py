# 这个是模板文件, 之所以以py作为后缀，是为了方便写该文件时能使用IDE的代码提示功能
# 该py文件仅仅当作字符串解析，然后调用python的exec执行，并且导入的包会被忽略，也仅仅忽略文件头以#开头的注释。
from codec.manifest import *
from codec.common import ConfigKey
from codec._runner.codec_cfg import Encoder, Decoder, Merger

Codec(
    Encoder(
        name="Template",  # 该编解码器的名称，必须唯一，一方面是用于日志自动解析，一方面是以便未来扩展功能
        param_key={  # 该字典定义了编码器、解码器、码流拼接器的命令行参数
            ParamType.CfgEncoder: None,
            ParamType.CfgSequence: None,
            ParamType.Sequence: None,
            ParamType.Width: None,
            ParamType.Height: None,
            ParamType.Fps: None,
            ParamType.BitDepth: None,
            ParamType.QP: None,

            ParamType.Frames: None,
            ParamType.IntraPeriod: None,
            ParamType.SkipFrames: None,
            ParamType.TemporalSampling: None,
            ParamType.OutBitStream: None,
            ParamType.OutReconstruction: None,

            ParamType.ExtraParam: "",
        },
        suffix="temp",  # 生成的码流后缀
        log_dir_type=ConfigKey.STDOUT_DIR,  # 编解码日志的目录
        # 编解码日志每一行的log正则表达式，用于进度条更新
        p_log_line=rf"(?P<{PatKey.Line_Psnr_Y}>\d+\.\d+)\s+(?P<{PatKey.Line_Psnr_U}>\d+\.\d+)\s+(?P<{PatKey.Line_Psnr_V}>\d+\.\d+)\s+(?P<{PatKey.Line_Bit}>\d+)\s+(?P<{PatKey.Line_Time}>\d+).+",
        # 编码日志的psnr、码率、编解码时间正则表达式，用于填写excel表格
        p_summary_psnr_y=rf"(?P<{PatKey.Summary_Psnr_Y}>\d+\.\d+)",
        p_summary_psnr_u=rf"(?P<{PatKey.Summary_Psnr_U}>\d+\.\d+)",
        p_summary_psnr_v=rf"(?P<{PatKey.Summary_Psnr_V}>\d+\.\d+)",
        p_summary_bitrate=rf"(?P<{PatKey.Summary_Bitrate}>\d+\.\d+)",
        p_summary_encode_time=rf"(?P<{PatKey.Summary_Encode_Time}>\d+\.\d+)",
    ),
    Decoder(
        name="Template",  # 该编解码器的名称，必须唯一，一方面是用于日志自动解析，一方面是以便未来扩展功能
        param_key={  # 该字典定义了编码器、解码器、码流拼接器的命令行参数
            ParamType.InBitStream: None,
            ParamType.DecodeYUV: None,
            ParamType.ExtraParam: "",
        },
        log_dir_type=ConfigKey.STDOUT_DIR,  # 编解码日志的目录
        p_summary_decode_time=rf"(?P<{PatKey.Summary_Decode_Time}>\d+\.\d+)",
    ),
    Merger(
        name="Template",  # 该编解码器的名称，必须唯一，一方面是用于日志自动解析，一方面是以便未来扩展功能
        param_key={  # 该字典定义了编码器、解码器、码流拼接器的命令行参数
            ParamType.MergeInBitStream: None,
            ParamType.MergeOutBitStream: None,
            ParamType.ExtraParam: "",
        },
    )

)
