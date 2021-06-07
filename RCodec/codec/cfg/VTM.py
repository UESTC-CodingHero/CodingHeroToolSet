from codec.manifest import *
from codec.common import ConfigKey
from codec._runner.codec_cfg import Encoder, Decoder, Merger

Codec(
    Encoder(
        "VTM",
        {
            ParamType.CfgEncoder: "-c ",
            ParamType.CfgSequence: "-c ",
            ParamType.Sequence: "-i ",
            ParamType.Width: "--SourceWidth=",
            ParamType.Height: "--SourceHeight=",
            ParamType.Fps: "--FrameRate=",
            ParamType.BitDepth: "--InputBitDepth=",
            ParamType.QP: "--QP=",

            ParamType.Frames: "--FramesToBeEncoded=",
            ParamType.IntraPeriod: "--IntraPeriod=",
            ParamType.SkipFrames: "--FrameSkip=",
            ParamType.TemporalSampling: "--TemporalSubsampleRatio=",
            ParamType.OutBitStream: "-b ",
            ParamType.OutReconstruction: "-o ",

            ParamType.ExtraParam: None,
        },
        "h266",
        ConfigKey.STDOUT_DIR,
        rf"\s*POC\s+(\d+)\s+LId:\s+(\d)\s+TId:\s*(\d)\s*\( \w+, \w-SLICE,\s+QP\s*(\d+)\s*\)\s*(?P<{PatKey.Line_Bit}>\d+)\s*bits\s*\[Y\s*(?P<{PatKey.Line_Psnr_Y}>\d+\.\d+)\s*dB\s*U\s*(?P<{PatKey.Line_Psnr_U}>\d+\.\d+)\s*dB\s*V\s*(?P<{PatKey.Line_Psnr_V}>\d+\.\d+)\s*dB\]\s*\[ET\s*(?P<{PatKey.Line_Time}>\d+)\s*\].*",
        rf"\s*(\d+)\s+a+\s+(?P<{PatKey.Summary_Bitrate}>\d+\.\d+)\s+(?P<{PatKey.Summary_Psnr_Y}>\d+\.\d+)\s+(?P<{PatKey.Summary_Psnr_U}>\d+\.\d+)\s+(?P<{PatKey.Summary_Psnr_V}>\d+\.\d+)\s+(\d+\.\d+)\s*",
        rf"\s*(\d+)\s+a+\s+(?P<{PatKey.Summary_Bitrate}>\d+\.\d+)\s+(?P<{PatKey.Summary_Psnr_Y}>\d+\.\d+)\s+(?P<{PatKey.Summary_Psnr_U}>\d+\.\d+)\s+(?P<{PatKey.Summary_Psnr_V}>\d+\.\d+)\s+(\d+\.\d+)\s*",
        rf"\s*(\d+)\s+a+\s+(?P<{PatKey.Summary_Bitrate}>\d+\.\d+)\s+(?P<{PatKey.Summary_Psnr_Y}>\d+\.\d+)\s+(?P<{PatKey.Summary_Psnr_U}>\d+\.\d+)\s+(?P<{PatKey.Summary_Psnr_V}>\d+\.\d+)\s+(\d+\.\d+)\s*",
        rf"\s*(\d+)\s+a+\s+(?P<{PatKey.Summary_Bitrate}>\d+\.\d+)\s+(?P<{PatKey.Summary_Psnr_Y}>\d+\.\d+)\s+(?P<{PatKey.Summary_Psnr_U}>\d+\.\d+)\s+(?P<{PatKey.Summary_Psnr_V}>\d+\.\d+)\s+(\d+\.\d+)\s*",
        rf"\s*Total Time:\s+(?P<{PatKey.Summary_Encode_Time}>\d+\.\d+) sec.+",
    ),
    Decoder(
        "VTM",
        {
            ParamType.InBitStream: "-b ",
            ParamType.DecodeYUV: "-o ",

            ParamType.ExtraParam: None,
        },
        ConfigKey.STDOUT_DIR,
        rf"\s*Total Time:\s+(?P<{PatKey.Summary_Decode_Time}>\d+\.\d+) sec.+",
    ),
    Merger(
        "VTM",
        {
            ParamType.MergeInBitStream: " ",
            ParamType.MergeOutBitStream: " ",

            ParamType.ExtraParam: None,
        },
    )

)
