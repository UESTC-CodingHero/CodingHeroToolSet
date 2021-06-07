from yuv.yuv_io import YuvReader
from yuv.yuv_io import YuvWriter
from yuv.com_def import Sequence, Region
from yuv.com_def import Format, BitDepth
from yuv.tools import Cut, Concat


def test_io():
    yuv_dir = r"G:\AVS3_Test_Sequences"
    name = r"MarketPlace_1920x1080_60.yuv"
    name_new = r"new_MarketPlace_1920x1080_60fps_10bit_420.yuv"
    seq = Sequence(yuv_dir, name, 1920, 1080, 60, fmt=Format.YUV420, bit_depth=BitDepth.BitDepth10)
    seq_new = Sequence(yuv_dir, name_new, 1920, 1080, 60, fmt=Format.YUV420, bit_depth=BitDepth.BitDepth10)

    def do_read_write(append):
        reader = YuvReader(seq)
        writer = YuvWriter(seq_new, append=append)
        for frame in reader:
            frame >>= 2
            writer.write(frame)
        reader.close()
        writer.close()

    do_read_write(False)
    do_read_write(True)


def test_tools():
    yuv_dir = r"G:\AVS3_Test_Sequences"
    name = r"MarketPlace_1920x1080_60fps_10bit_420.yuv"
    name_new = r"cut_MarketPlace_1920x1080_60fps_10bit_420.yuv"
    seq = Sequence(yuv_dir, name, 1920, 1080, 60, fmt=Format.YUV420, bit_depth=BitDepth.BitDepth10)
    seq_new = Sequence(yuv_dir, name_new, 1920, 1080, 60, fmt=Format.YUV420, bit_depth=BitDepth.BitDepth10)
    region = Region(0, 0, 64, 64)
    cut = Cut()
    cut.cut_seq(seq, region, seq_new)

    concat = Concat()
    seq = Sequence(yuv_dir, name, 1920, 1080, 60, fmt=Format.YUV420, bit_depth=BitDepth.BitDepth10)
    seq_new = Sequence(yuv_dir, name_new, 1920, 1080, 60, fmt=Format.YUV420, bit_depth=BitDepth.BitDepth10)
    concat.concat_seq([seq, seq], seq_new)


def main():
    test_io()
    # test_tools()


if __name__ == '__main__':
    main()
