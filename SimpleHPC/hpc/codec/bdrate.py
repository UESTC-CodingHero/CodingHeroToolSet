import math as m
from typing import Union
import sys


class BDRate(object):
    @staticmethod
    def __pchipend(h1: float, h2: float, delta1: float, delta2: float):
        d = ((2 * h1 + h2) * delta1 - h1 * delta2) / (h1 + h2)
        if d * delta1 < 0:
            d = 0
        elif delta1 * delta2 < 0 and abs(d) > abs(3 * delta1):
            d = 3 * delta1
        return d

    def __bd_rint(self, rate: Union[list, tuple], psnr: Union[list, tuple], min_psnr: float, max_psnr: float):
        assert len(rate) == len(psnr) == 4
        assert max_psnr > min_psnr
        log_rate = [m.log(r, 10.0) for r in reversed(rate)]
        log_psnr = list(reversed(psnr))

        H = [lp - log_psnr[i] for i, lp in enumerate(log_psnr[1:])]
        delta = [(lr - log_rate[i]) / H[i] for i, lr in enumerate(log_rate[1:])]

        d = [0.0 for _ in range(4)]
        d[0] = self.__pchipend(H[0], H[1], delta[0], delta[1])
        d[1:3] = [3 * (H[i - 1] + H[i]) / ((2 * H[i] + H[i - 1]) / delta[i - 1] + (H[i] + 2 * H[i - 1]) / delta[i])
                  for i in range(1, 3)]
        d[3] = self.__pchipend(H[2], H[1], delta[2], delta[1])

        c = [(3 * delta[i] - 2 * d[i] - d[i + 1]) / H[i] for i in range(3)]
        b = [(d[i] - 2 * delta[i] + d[i + 1]) / (H[i] * H[i]) for i in range(3)]

        result = 0
        for i in range(3):
            s0 = log_psnr[i]
            s1 = log_psnr[i + 1]

            s0 = min(max(s0, min_psnr), max_psnr) - log_psnr[i]
            s1 = min(max(s1, min_psnr), max_psnr) - log_psnr[i]

            if s1 > s0:
                result += (s1 - s0) * log_rate[i]
                result += (s1 * s1 - s0 * s0) * d[i] / 2
                result += (s1 * s1 * s1 - s0 * s0 * s0) * c[i] / 3
                result += (s1 * s1 * s1 * s1 - s0 * s0 * s0 * s0) * b[i] / 4
        return result

    def bd_rate(self, anchor_rate: Union[list, tuple], anchor_psnr: Union[list, tuple],
                test_rate: Union[list, tuple], test_psnr: Union[list, tuple]):
        assert len(anchor_psnr) == len(anchor_rate) == 4
        assert len(anchor_psnr) == len(test_rate)
        assert len(test_rate) == len(test_psnr)

        min_psnr = max(min(anchor_psnr), min(test_psnr))
        max_psnr = min(max(anchor_psnr), max(test_psnr))

        v_a = self.__bd_rint(anchor_rate, anchor_psnr, min_psnr, max_psnr)
        v_b = self.__bd_rint(test_rate, test_psnr, min_psnr, max_psnr)
        avg = (v_b - v_a) / (max_psnr - min_psnr)
        return pow(10, avg) - 1


def main(*args):
    if len(args) == 0:
        args = sys.argv
    assert len(args) == 16

    # a = args[0:4]
    # b = args[4:8]
    # c = args[8:12]
    # d = args[12:16]
    # print(a, b, c, d)

    a = [5192.256, 8932.608, 13757.472, 19933.248]
    b0 = [36.9643, 40.1423, 42.4961, 44.2163]
    b1 = [45.0681, 46.7267, 47.8077, 48.8923]
    b2 = [43.1246, 45.7796, 47.3345, 48.7496]

    c = [6318.144, 10516.8, 16169.088, 23664.576]
    d0 = [38.0322, 40.9453, 43.1589, 44.8481]
    d1 = [45.7003, 47.3182, 48.346, 49.3839]
    d2 = [44.2088, 46.6201, 48.0437, 49.353]
    a0 = BDRate().bd_rate(a, b0, c, d0)
    print(a0 * 100)
    a0 = BDRate().bd_rate(a, b1, c, d1)
    print(a0 * 100)
    a0 = BDRate().bd_rate(a, b2, c, d2)
    print(a0 * 100)

if __name__ == "__main__":
    main(77588.6659,
         41846.5297,
         25031.4032,
         14262.7459,
         40.8032,
         40.1512,
         39.4182,
         38.1947,
         76649.7859,
         41628.5968,
         24995.3384,
         14279.8184,
         40.8003,
         40.1571,
         39.4312,
         38.212)
