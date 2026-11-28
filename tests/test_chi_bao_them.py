# -*- coding: utf-8 -*-
"""Chỉ báo thêm của biểu đồ (so_cong_khai/chi_bao_them.py): đối chiếu với các trường hợp biết trước đáp số, không phải tính lại bằng chính công thức."""
import unittest

import numpy as np
import pandas as pd

from so_cong_khai import chi_bao_them as CB


def _nen(dong, rong=1.0, freq='15min', bat_dau='2026-11-20'):
    idx = pd.date_range(bat_dau, periods=len(dong), freq=freq, tz='UTC')
    c = pd.Series(np.asarray(dong, dtype=float), index=idx)
    return pd.DataFrame({'open': c, 'high': c + rong / 2, 'low': c - rong / 2, 'close': c})


class CongThuc(unittest.TestCase):
    def test_atr_cua_bien_do_khong_doi(self):
        b = _nen([100.0] * 60, rong=2.0)                                   # đỉnh − đáy luôn 2, đóng không đổi
        self.assertAlmostEqual(float(CB.atr(b, 14).iloc[-1]), 2.0, places=9)

    def test_stoch_o_dinh_va_o_day(self):
        len_ = _nen(np.arange(40, dtype=float), rong=0.0)                    # đóng luôn ở đỉnh 14 nến
        k, d = CB.stoch(len_)
        self.assertAlmostEqual(float(k.iloc[-1]), 100.0)
        self.assertAlmostEqual(float(d.iloc[-1]), 100.0)
        xuong = _nen(np.arange(40, 0, -1, dtype=float), rong=0.0)           # đóng luôn ở đáy
        self.assertAlmostEqual(float(CB.stoch(xuong)[0].iloc[-1]), 0.0)

    def test_macd_cua_gia_di_ngang_bang_0(self):
        m, s, h = CB.macd(pd.Series([50.0] * 100))
        self.assertAlmostEqual(float(m.iloc[-1]), 0.0)
        self.assertAlmostEqual(float(h.iloc[-1]), 0.0)
        tang = CB.macd(pd.Series(np.arange(100, dtype=float)))[0]
        self.assertGreater(float(tang.iloc[-1]), 0)                         # giá tăng đều: EMA nhanh trên EMA chậm

    def test_supertrend_doi_chieu_khi_gia_dao(self):
        dong = list(np.linspace(100, 150, 80)) + list(np.linspace(150, 90, 40))
        b = _nen(dong, rong=1.0)
        line, chieu = CB.supertrend(b)
        self.assertEqual(chieu.iloc[60], 1.0)                               # đang tăng: đường nằm dưới giá
        self.assertLess(line.iloc[60], b['close'].iloc[60])
        self.assertEqual(chieu.iloc[-1], -1.0)                              # sau cú đảo mạnh: đường nằm trên giá
        self.assertGreater(line.iloc[-1], b['close'].iloc[-1])

    def test_ichimoku_dung_dinh_nghia_va_dich_26_nen(self):
        rng = np.random.default_rng(1)
        b = _nen(100 + rng.normal(0, 1, 200).cumsum(), rong=1.0)
        ic = CB.ichimoku(b)
        i = 150
        self.assertAlmostEqual(float(ic['tenkan'].iloc[i]), (b['high'].iloc[i - 8:i + 1].max() + b['low'].iloc[i - 8:i + 1].min()) / 2)
        sa_goc = (ic['tenkan'] + ic['kijun']) / 2
        self.assertAlmostEqual(float(ic['span_a'].iloc[i]), float(sa_goc.iloc[i - 26]))   # mây ở nến i tính từ nến i − 26
        self.assertAlmostEqual(float(ic['chikou'].iloc[i]), float(b['close'].iloc[i + 26]))
        self.assertEqual(len(ic['a_sau']), 26)
        self.assertAlmostEqual(float(ic['a_sau'][-1]), float(sa_goc.iloc[-1]))

    def test_pivot_co_dien(self):
        idx = pd.date_range('2026-11-20', periods=96 * 2, freq='15min', tz='UTC')
        b = pd.DataFrame({'open': 100.0, 'high': 100.0, 'low': 100.0, 'close': 100.0}, index=idx)
        ngay1 = b.index < pd.Timestamp('2026-11-21', tz='UTC')
        b.loc[ngay1, 'high'] = 110.0
        b.loc[ngay1, 'low'] = 90.0
        b.loc[b.index[ngay1][-1], 'close'] = 105.0                          # ngày trước: H 110, L 90, C 105
        p = CB.pivot_ngay(b)
        P = (110 + 90 + 105) / 3
        self.assertEqual(p['ngay'], '2026-11-20')
        for k, v in {'P': P, 'R1': 2 * P - 90, 'S1': 2 * P - 110, 'R2': P + 20, 'S2': P - 20, 'R3': 110 + 2 * (P - 90), 'S3': 90 - 2 * (110 - P)}.items():
            self.assertAlmostEqual(p[k], v, msg=k)
        self.assertIsNone(CB.pivot_ngay(b.iloc[:50]))                       # chưa có ngày trọn nào trước ngày của nến cuối


class DauRa(unittest.TestCase):
    def test_moi_mang_dai_dung_n_va_may_phia_truoc(self):
        rng = np.random.default_rng(2)
        b = _nen(3500 + rng.normal(0, 3, 1500).cumsum(), rong=4.0)
        o = CB.tinh(b, 300, so_le=2, buoc_giay=900)
        for k in ('ema200', 'macd', 'macd_tin', 'macd_cot', 'stoch_k', 'stoch_d', 'atr14', 'st', 'st_chieu',
                  'ichi_tenkan', 'ichi_kijun', 'ichi_span_a', 'ichi_span_b', 'ichi_chikou'):
            self.assertEqual(len(o[k]), 300, k)
        self.assertIsNotNone(o['ema200'][0])                                # có đủ nến phía trước phần hiển thị
        self.assertEqual(o['ichi_chikou'][-26:], [None] * 26)               # Chikou vẽ sớm 26 nến: 26 nến cuối chưa có
        t_cuoi = int(b.index[-1].timestamp())
        self.assertEqual([x[0] for x in o['ichi_sau'][:2]], [t_cuoi + 900, t_cuoi + 1800])
        self.assertIn(set(v for v in o['st_chieu'] if v is not None), ({1}, {-1}, {1, -1}))
        self.assertTrue(all(v is None or 0 <= v <= 100 for v in o['stoch_k']))


if __name__ == '__main__':
    unittest.main()
