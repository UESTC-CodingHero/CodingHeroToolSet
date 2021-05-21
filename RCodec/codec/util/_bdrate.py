from math import log10
from typing import Sequence, Union


def _clip3(v, min_v, max_v):
    return min(max(v, min_v), max_v)


class _BDRate(object):
    @staticmethod
    def _pchipend(h1: float, h2: float, delta1: float, delta2: float):
        d = ((2 * h1 + h2) * delta1 - h1 * delta2) / (h1 + h2)
        if d * delta1 < 0:
            d = 0
        elif delta1 * delta2 < 0 and abs(d) > abs(3 * delta1):
            d = 3 * delta1
        return d

    @staticmethod
    def _bd_rint(rate: Sequence[float], psnr: Sequence[float], min_psnr: float, max_psnr: float):
        assert len(rate) == len(psnr)
        assert len(rate) >= 4
        assert max_psnr > min_psnr
        n = len(rate)
        log_rate = [log10(r) for r in reversed(rate)]
        log_psnr = list(reversed(psnr))

        H = [lp - log_psnr[i] for i, lp in enumerate(log_psnr[1:])]
        delta = [(lr - log_rate[i]) / H[i] for i, lr in enumerate(log_rate[1:])]

        d = [0.0 for _ in range(n)]
        d[0] = _BDRate._pchipend(H[0], H[1], delta[0], delta[1])
        d[1:n - 1] = [3 * (H[i - 1] + H[i]) / ((2 * H[i] + H[i - 1]) / delta[i - 1] + (H[i] + 2 * H[i - 1]) / delta[i])
                      for i in range(1, n - 1)]
        d[n - 1] = _BDRate._pchipend(H[2], H[1], delta[2], delta[1])

        c = [(3 * delta[i] - 2 * d[i] - d[i + 1]) / H[i] for i in range(n - 1)]
        b = [(d[i] - 2 * delta[i] + d[i + 1]) / (H[i] * H[i]) for i in range(n - 1)]

        result = 0
        for i in range(n - 1):
            s0 = log_psnr[i]
            s1 = log_psnr[i + 1]

            s0 = _clip3(s0, min_psnr, max_psnr) - log_psnr[i]
            s1 = _clip3(s1, min_psnr, max_psnr) - log_psnr[i]

            if s1 > s0:
                result += (s1 - s0) * log_rate[i]
                result += (s1 * s1 - s0 * s0) * d[i] / 2
                result += (s1 * s1 * s1 - s0 * s0 * s0) * c[i] / 3
                result += (s1 * s1 * s1 * s1 - s0 * s0 * s0 * s0) * b[i] / 4
        return result

    @staticmethod
    def calc(anchor_rate: Union[list, tuple], anchor_psnr: Union[list, tuple],
             test_rate: Union[list, tuple], test_psnr: Union[list, tuple]):
        assert len(anchor_psnr) == len(test_rate)
        assert len(anchor_psnr) >= 4
        assert len(test_rate) == len(test_psnr)

        min_psnr = max(min(anchor_psnr), min(test_psnr))
        max_psnr = min(max(anchor_psnr), max(test_psnr))

        v_a = _BDRate._bd_rint(anchor_rate, anchor_psnr, min_psnr, max_psnr)
        v_b = _BDRate._bd_rint(test_rate, test_psnr, min_psnr, max_psnr)
        avg = (v_b - v_a) / (max_psnr - min_psnr)
        return pow(10, avg) - 1


bd_rate = _BDRate.calc
