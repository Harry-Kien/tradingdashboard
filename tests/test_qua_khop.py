"""Bài kiểm cho điểm khớp quá khứ (PBO bằng CSCV, Deflated Sharpe) bằng dữ liệu giả có đáp án biết trước."""
import itertools
import math
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import qua_khop as Q  # noqa: E402


def pbo_tho(X, S):
    """Cách tính độc lập, vòng lặp thô, để đối chiếu với Q.pbo."""
    T, N = X.shape
    X = X[T - (T // S) * S:]
    k = np.split(X, S)
    dem = tong = 0
    for chon in itertools.combinations(range(S), S // 2):
        A = np.vstack([k[i] for i in chon])
        B = np.vstack([k[i] for i in range(S) if i not in chon])
        sa = [A[:, j].mean() / A[:, j].std(ddof=1) for j in range(N)]
        sb = [B[:, j].mean() / B[:, j].std(ddof=1) for j in range(N)]
        n = max(range(N), key=lambda j: sa[j])
        hang = 1 + sum(1 for j in range(N) if sb[j] < sb[n])
        w = hang / (N + 1)
        dem += math.log(w / (1 - w)) <= 0
        tong += 1
    return dem / tong


class PboTest(unittest.TestCase):
    def test_khop_cach_tinh_tho(self):
        X = np.random.default_rng(1).normal(0, 1, (48, 6))
        self.assertAlmostEqual(Q.pbo(X, 8)['pbo'], pbo_tho(X, 8), places=12)

    def test_toan_ngau_nhien_thi_quanh_mot_nua(self):
        g = [Q.pbo(np.random.default_rng(s).normal(0, 1, (128, 20)), 16)['pbo'] for s in range(6)]
        self.assertTrue(0.3 < float(np.mean(g)) < 0.7, g)

    def test_co_loi_the_that_thi_gan_khong(self):
        X = np.random.default_rng(2).normal(0, 1, (128, 20))
        X[:, 7] += 0.8                                                       # một cấu hình có lợi thế thật
        r = Q.pbo(X, 16)
        self.assertLess(r['pbo'], 0.05)
        self.assertLess(r['lo_khi_kiem'], 0.05)

    def test_thieu_du_lieu(self):
        with self.assertRaises(ValueError):
            Q.pbo(np.zeros((20, 5)), 16)


class DsrTest(unittest.TestCase):
    def test_psr_hieu_chuan_dung(self):
        """Chiến lược không có lợi thế: tỷ lệ PSR > 95% phải quanh 5% (đúng nghĩa xác suất)."""
        rng = np.random.default_rng(3)
        vuot = 0
        for _ in range(4000):
            x = rng.normal(0, 1, 60)
            sr = x.mean() / x.std(ddof=1)
            d = x - x.mean()
            m2 = (d ** 2).mean()
            vuot += Q.psr(sr, 0.0, 60, (d ** 3).mean() / m2 ** 1.5, (d ** 4).mean() / m2 ** 2) > 0.95
        self.assertTrue(0.035 < vuot / 4000 < 0.07, vuot / 4000)

    def test_nguong_tang_theo_so_lan_thu(self):
        self.assertEqual(Q.sr0(0.01, 1), 0.0)
        self.assertLess(Q.sr0(0.01, 5), Q.sr0(0.01, 50))
        self.assertLess(Q.sr0(0.01, 50), Q.sr0(0.01, 500))

    def test_dsr_phan_biet_loi_the_that(self):
        rng = np.random.default_rng(4)
        idx = pd.date_range('2015-01-31', periods=130, freq='ME', tz='UTC')
        M = pd.DataFrame(rng.normal(0, 1, (130, 24)), index=idx, columns=[f'c{i}' for i in range(24)])
        M['c3'] += 0.9
        d = Q.dsr(M)
        self.assertGreater(d['cot']['c3']['dsr'], 0.95)
        nhieu = [v['dsr'] for k, v in d['cot'].items() if k != 'c3']
        self.assertLess(float(np.mean(nhieu)), 0.5)
        self.assertLess(d['cot']['c0']['dsr'], d['cot']['c0']['psr'] + 1e-12)      # trừ hao số lần thử: DSR không cao hơn PSR


class DanhGiaTest(unittest.TestCase):
    def _lenh(self, rng, n, loi=0.0):
        t = pd.date_range('2015-01-02', '2026-11-20', periods=n, tz='UTC')
        return [{'t': x.isoformat(), 'usd': float(v)} for x, v in zip(t, rng.normal(loi, 5, n))]

    def test_danh_gia_day_du(self):
        rng = np.random.default_rng(5)
        chon = {f'pp{i}': self._lenh(rng, 1500) for i in range(10)}
        them = {'bot': self._lenh(rng, 400)}
        r = Q.danh_gia(chon, them)
        self.assertEqual((r['ky'], r['so_cau_hinh'], r['pbo']['S']), ('tháng', 11, 16))
        self.assertIn('bot', r['dsr']['cot'])
        self.assertEqual(r['dsr']['n_thu'], 11)

    def test_du_lieu_ngan_dung_tuan(self):
        rng = np.random.default_rng(6)
        t = pd.date_range('2026-01-02', '2026-11-20', periods=600, tz='UTC')
        chon = {f'pp{i}': [{'t': x.isoformat(), 'usd': float(v)} for x, v in zip(t, rng.normal(0, 1, 600))] for i in range(8)}
        r = Q.danh_gia(chon)
        self.assertEqual(r['ky'], 'tuần')
        self.assertEqual(r['pbo']['S'], 8)


if __name__ == '__main__':
    unittest.main()
