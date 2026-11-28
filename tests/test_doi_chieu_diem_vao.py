# -*- coding: utf-8 -*-
"""Các khối dựng của cong-cu/doi_chieu_diem_vao.py (bản dựng lại độc lập của luật vào lệnh) phải cho đúng con số mà cách tính quen thuộc
bằng pandas cho ra. Dữ liệu giả, không đọc tệp nến, không nạp mã của chủ dự án."""
import importlib.util
import math
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

_spec = importlib.util.spec_from_file_location('doi_chieu_diem_vao', Path(__file__).resolve().parent.parent / 'cong-cu' / 'doi_chieu_diem_vao.py')
DV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(DV)


def _m1(n=3000, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.date_range('2026-03-02 00:00', periods=n, freq='1min', tz='UTC')
    idx = idx.delete(list(range(400, 437)) + list(range(1500, 1503)))          # hai quãng thiếu nến, một quãng dài hơn một nến M15
    c = 3000 + np.cumsum(rng.normal(0, 0.4, len(idx))).round(2)
    o = np.r_[c[0], c[:-1]]
    h = (np.maximum(o, c) + rng.uniform(0, 0.5, len(idx))).round(2)
    l = (np.minimum(o, c) - rng.uniform(0, 0.5, len(idx))).round(2)
    return pd.DataFrame({'open': o, 'high': h, 'low': l, 'close': c}, index=idx)


class KhoiDung(unittest.TestCase):
    def setUp(self):
        self.m1 = _m1()
        self.M = (DV.giay(self.m1.index), *(self.m1[k].to_numpy(dtype=float) for k in ('open', 'high', 'low', 'close')))

    def test_ghep_nen_trung_voi_resample(self):
        for dai, quy in ((300, '5min'), (900, '15min'), (3600, '1h')):
            t, o, h, l, c = DV.ghep(*self.M, dai)
            b = self.m1.resample(quy, origin='epoch', label='left', closed='left').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
            self.assertTrue(np.array_equal(t, DV.giay(b.index)), quy)
            for x, k in zip((o, h, l, c), ('open', 'high', 'low', 'close')):
                self.assertTrue(np.array_equal(x, b[k].to_numpy()), (quy, k))

    def test_ema_trung_voi_ewm(self):
        c = self.M[4]
        for n in (20, 50, 200):
            a, b = DV.ema(c, n), pd.Series(c).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()
            self.assertTrue(np.isnan(a[:n - 1]).all() and not np.isnan(a[n - 1:]).any())
            self.assertTrue(np.allclose(a[n - 1:], b[n - 1:], rtol=0, atol=1e-8))

    def test_atr_trung_voi_rolling(self):
        _, _, h, l, c = DV.ghep(*self.M, 900)
        prev = pd.Series(c).shift(1)
        tr = pd.concat([pd.Series(h - l), (pd.Series(h) - prev).abs(), (pd.Series(l) - prev).abs()], axis=1).max(axis=1)
        tr.iloc[0] = h[0] - l[0]
        b = tr.rolling(14, min_periods=14).mean().to_numpy()
        a = DV.atr_tb(h, l, c, 14)
        self.assertTrue(np.isnan(a[:13]).all())
        self.assertTrue(np.allclose(a[13:], b[13:], rtol=0, atol=1e-9))

    def test_nen_khung_lon_chi_dung_khi_da_dong(self):
        dong = np.array([100, 200, 300])                                       # lúc ĐÓNG của ba nến khung lớn
        gt = np.array([1.0, 2.0, 3.0])
        ra = DV.da_dong(dong, gt, np.array([99, 100, 150, 200, 299, 300, 999]))
        self.assertTrue(np.isnan(ra[0]))                                       # chưa nến nào đóng
        self.assertEqual(ra[1:].tolist(), [1.0, 1.0, 2.0, 2.0, 3.0, 3.0])      # đóng đúng lúc quyết định thì được dùng; nến đang chạy thì không


class DungMucBot(unittest.TestCase):
    R = SimpleNamespace(SL_MIN=17.0, SL_MAX=28.0, TP_COUNT=6)
    LV = SimpleNamespace(TP_R=(0.5, 1.0, 1.5, 2.0, 2.5, 3.0), TP_FIRST=3.0, TP_STEP=7.0)

    def test_lay_ung_vien_dau_tien_co_dung_lo_trong_khoang(self):
        # mua, Bid mở 3000,00, spread 0,17 → vào 3000,17. Mức 2990 cách 10,17 (quá gần), 2980 cách 20,17 (nhận), 2975 không được xét tới.
        vao, sl, tps = DV.bot_dung(True, [2990.0, 2980.0, 2975.0], 17.0, 3000.0, 0.17, self.R, self.LV, 0.05)
        self.assertEqual((vao, sl), (3000.17, 2980.0))
        rr = 3000.17 - 2980.0
        self.assertEqual(tps, tuple(float(3000 + math.floor(m * rr + 0.5)) for m in self.LV.TP_R))

    def test_khong_muc_nao_hop_thi_dung_khoang_du_phong(self):
        vao, sl, tps = DV.bot_dung(False, [3005.0], 17.0, 3000.0, 0.17, self.R, self.LV, 0.05)   # bán khớp ở Bid; 3005 chỉ cách 5 giá
        self.assertEqual((vao, sl), (3000.0, 3017.0))
        self.assertEqual(tps[0], 3000.0 - 9.0)                                 # 0,5 × 17 = 8,5 → làm tròn 9
        self.assertTrue(all(a > b for a, b in zip(tps, tps[1:])))              # lệnh bán: các mức chốt thấp dần
        self.assertIsNone(DV.bot_dung(False, [3005.0], None, 3000.0, 0.17, self.R, self.LV, 0.05))

    def test_spread_qua_rong_thi_khong_vao(self):
        self.assertIsNone(DV.bot_dung(True, [2980.0], None, 3000.0, 2.0, self.R, self.LV, 0.05))


if __name__ == '__main__':
    unittest.main()
