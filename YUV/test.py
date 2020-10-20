from yuv_io.yuv_reader import YuvReader
from yuv_io.yuv_writer import YuvWriter
from yuv_io.common.seq import Sequence
from yuv_io.common.com_def import Format, BitDepth


class Test():
    def __init__(self, i):
        self.i = i

    x = property(lambda self: self.i, lambda self, i: None, doc="Hello World")


def main():
    yuv_dir = r"G:\AVS3_Test_Sequences"
    name = r"MarketPlace_1920x1080_60fps_10bit_420.yuv"
    name_new = r"new_MarketPlace_1920x1080_60fps_10bit_420.yuv"
    seq = Sequence(yuv_dir, name, 1920, 1080, Format.YUV420, BitDepth.BitDepth10, 60)
    seq_new = Sequence(yuv_dir, name_new, 1920, 1080, Format.YUV420, BitDepth.BitDepth10, 60)

    reader = YuvReader(seq)
    writer = YuvWriter(seq_new, append=False)
    for frame in reader:
        # writer.write(frame)
        r = frame.roi(0, 0, 100000, 600000)
        print(r.buff_y.shape)
        break


if __name__ == '__main__':
    main()
