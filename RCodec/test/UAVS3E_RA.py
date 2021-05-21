from codec.common import Mode
from codec.manifest import SupportedCodec


def main():
    # 加载自定义配置, 空参数为默认配置
    SupportedCodec.init(global_cfg=None)

    # 两种方式获取编码器均可
    codec = SupportedCodec.UAVS3E
    # codec = SupportedCodec.find_by_name("UAVS3E")

    encoder = "uavs3e.exe"
    decoder = "app_decoder.exe"
    merger = None
    mode = Mode.RA
    cfg = "config.txt"

    gen_bin = True
    gen_rec = False
    gen_dec = False
    par_enc = False

    who = "who"
    email = "who@uestc.edu.cn"

    seqs_dir = r"D:\YUV\AVS3_Test_Sequences"

    # 一般来说，E2680 设置2个核, X5680 设置3个核，以防止服务器负载大、温度高
    cores = 2
    # X5680: Node01,Node02,Node03,Node04,Node05,Node06,Node07,Node08,Node09,Node10
    # E2680：R720Node01,R720Node02,R720Node03,R720Node04
    nodes = None

    #  X5680,E2680
    groups = "E2680"

    priority = 2200

    # @formatter:off
    seq_info = [
        # name                  width   height  fps     bits    frames   intra_period  ts      skip     path
        ["Tango2",              3840,   2160,   60,     10,     294,        64,          1,      0,      seqs_dir],
        ["ParkRunning3",        3840,   2160,   50,     10,     300,        48,          1,      0,      seqs_dir],
        ["Campfire",            3840,   2160,   30,     10,     300,        32,          1,      0,      seqs_dir],
        ["DaylightRoad2",       3840,   2160,   60,     10,     300,        64,          1,      0,      seqs_dir],

        ["MarketPlace",         1920,   1080,   60,     10,     600,        64,          1,      0,      seqs_dir],
        ["RitualDance",         1920,   1080,   60,     10,     600,        64,          1,      0,      seqs_dir],
        ["Cactus",              1920,   1080,   50,     8,      500,        48,          1,      0,      seqs_dir],
        ["BasketballDrive",     1920,   1080,   50,     8,      500,        48,          1,      0,      seqs_dir],

        ["City",                1280,   720,    60,     8,      600,        64,          1,      0,      seqs_dir],
        ["Crew",                1280,   720,    60,     8,      600,        64,          1,      0,      seqs_dir],
        ["vidyo1",              1280,   720,    60,     8,      600,        64,          1,      0,      seqs_dir],
        ["vidyo3",              1280,   720,    60,     8,      600,        64,          1,      0,      seqs_dir],
    ]
    # @formatter:on

    qp_list = [27, 32, 38, 45]

    codec.go(encoder=encoder, decoder=decoder, merger=merger,
             mode=mode, who=who, email=email,
             gen_bin=gen_bin, gen_dec=gen_dec, gen_rec=gen_rec, par_enc=par_enc,
             qp_list=qp_list, seq_info=seq_info, cores=cores, nodes=nodes, groups=groups, priority=priority,
             cfg=cfg, cfg_seq=None, extra_param="--fps_den 1", with_hash=True)


if __name__ == '__main__':
    main()
