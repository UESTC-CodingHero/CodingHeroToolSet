from codec.common import Mode
from codec.manifest import SupportedCodec


def main():
    # 加载自定义配置, 空参数为默认配置
    SupportedCodec.init(global_cfg=None)

    # 两种方式获取编码器均可
    codec = SupportedCodec.HM
    # codec = SupportedCodec.find_by_name("HM")

    encoder = "TAppEncoder.exe"
    decoder = "TAppDecoder.exe"
    merger = None
    mode = Mode.LB
    cfg = "cfg/encoder_lowdelay_P_main.cfg"

    gen_bin = True
    gen_rec = False
    gen_dec = False
    par_enc = False

    who = "who"
    email = "who@uestc.edu.cn"

    seqs_dir = r"D:\YUV\HEVC_Test_Sequences"

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
        # name                          width   height  fps bits    frames   intra_period  ts      skip     path
        ["Traffic_crop",                2560,   1600,   30,  10,     150,        -1,        1,      0,      seqs_dir],
        ["PeopleOnStreet_crop",         2560,   1600,   30,  10,     150,        -1,        1,      0,      seqs_dir],
        ["NebutaFestival_crop",         2560,   1600,   60,  10,     300,        -1,        1,      0,      seqs_dir],
        ["SteamLocomotiveTrain_crop",   2560,   1600,   60,  10,     300,        -1,        1,      0,      seqs_dir],

        ["Kimono1",                     1920,   1080,   24,  8,      240,        -1,        1,      0,      seqs_dir],
        ["ParkScene",                   1920,   1080,   24,  8,      240,        -1,        1,      0,      seqs_dir],
        ["Cactus",                      1920,   1080,   50,  8,      500,        -1,        1,      0,      seqs_dir],
        ["BasketballDrive",             1920,   1080,   50,  8,      500,        -1,        1,      0,      seqs_dir],
        ["BQTerrace",                   1920,   1080,   60,  8,      600,        -1,        1,      0,      seqs_dir],

        ["BasketballDrill",             832,    480,    50,  8,      500,        -1,        1,      0,      seqs_dir],
        ["BQMall",                      832,    480,    60,  8,      600,        -1,        1,      0,      seqs_dir],
        ["PartyScene",                  832,    480,    50,  8,      500,        -1,        1,      0,      seqs_dir],
        ["RaceHorses",                  832,    480,    30,  8,      300,        -1,        1,      0,      seqs_dir],

        ["BasketballPass",              416,    240,    50,  8,      500,        -1,        1,      0,      seqs_dir],
        ["BQSquare",                    416,    240,    60,  8,      600,        -1,        1,      0,      seqs_dir],
        ["BlowingBubbles",              416,    240,    50,  8,      500,        -1,        1,      0,      seqs_dir],
        ["RaceHorses",                  416,    240,    30,  8,      300,        -1,        1,      0,      seqs_dir],

        ["FourPeople",                  1280,   720,    60,  8,      600,        -1,        1,      0,      seqs_dir],
        ["Johnny",                      1280,   720,    60,  8,      600,        -1,        1,      0,      seqs_dir],
        ["KristenAndSara",              1280,   720,    60,  8,      600,        -1,        1,      0,      seqs_dir],

        ["BasketballDrillText",         832,    480,    50,  8,      500,        -1,        1,      0,      seqs_dir],
        ["ChinaSpeed",                  1024,   768,    30,  8,      500,        -1,        1,      0,      seqs_dir],
        ["SlideEditing",                1280,   720,    30,  8,      300,        -1,        1,      0,      seqs_dir],
        ["SlideShow",                   1280,   720,    20,  8,      500,        -1,        1,      0,      seqs_dir],
    ]
    # @formatter:on

    qp_list = [22, 27, 32, 37]

    codec.go(encoder=encoder, decoder=decoder, merger=merger,
             mode=mode, who=who, email=email,
             gen_bin=gen_bin, gen_dec=gen_dec, gen_rec=gen_rec, par_enc=par_enc,
             qp_list=qp_list, seq_info=seq_info, cores=cores, nodes=nodes, groups=groups, priority=priority,
             cfg=cfg, cfg_seq=None, extra_param="--SEIDecodedPictureHash=0", with_hash=True)


if __name__ == '__main__':
    main()
