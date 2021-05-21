from codec.manifest import *
from codec.common import ConfigKey
Codec(
    "UAVS3E",
    {
        ParamType.CfgEncoder: "--config ",
        ParamType.CfgSequence: None,
        ParamType.Sequence: "-i ",
        ParamType.Width: "-w ",
        ParamType.Height: "-h ",
        ParamType.Fps: "--fps_num ",
        ParamType.BitDepth: "-d ",
        ParamType.QP: "-q ",

        ParamType.Frames: "-f ",
        ParamType.IntraPeriod: "-p ",
        ParamType.SkipFrames: "--skip_frames ",
        ParamType.TemporalSampling: "--TemporalSubsampleRatio ",
        ParamType.OutBitStream: "-o ",
        ParamType.OutReconstruction: "-r ",

        ParamType.InBitStream: "-i ",
        ParamType.DecodeYUV: "-o ",

        ParamType.MergeInBitStream: "-i ",
        ParamType.MergeOutBitStream: "-o ",

        ParamType.ExtraParam: None,
    },
    "avs3",
    ConfigKey.STDERR_DIR,
    rf"\s*(\d+)\s*\(\w\)\|\s*(\d+\.\d+)\|\s*(?P<{PatKey.Line_Psnr_Y}>\d+\.\d+)\s+(?P<{PatKey.Line_Psnr_U}>\d+\.\d+)\s+(?P<{PatKey.Line_Psnr_V}>\d+\.\d+)\|\s*(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\|\s*(?P<{PatKey.Line_Bit}>\d+)",
    rf"\s*PSNR Y\(dB\)\s*: (?P<{PatKey.Summary_Psnr_Y}>\d+\.\d+)",
    rf"\s*PSNR U\(dB\)\s*: (?P<{PatKey.Summary_Psnr_U}>\d+\.\d+)",
    rf"\s*PSNR V\(dB\)\s*: (?P<{PatKey.Summary_Psnr_V}>\d+\.\d+)",
    rf"\s*bitrate\(kbps\)\s*: (?P<{PatKey.Summary_Bitrate}>\d+\.\d+)",
    rf"Total encoding time\s+=\s*\d+\.\d+ msec, (?P<{PatKey.Summary_Encode_Time}>\d+\.\d+) sec",
    rf"total decoding time\s+=\s*\d+\s*msec, (?P<{PatKey.Summary_Decode_Time}>\d+\.\d+) sec",
)
