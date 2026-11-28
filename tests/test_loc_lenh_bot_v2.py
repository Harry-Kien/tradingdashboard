# -*- coding: utf-8 -*-
"""Đặc trưng liên thị trường của cong-cu/loc_lenh_bot_v2.py không được nhìn trước: chỉ dùng giá trị có chỉ số (giờ đóng nến, giờ phát hành) ≤ lúc vào lệnh."""
import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

spec = importlib.util.spec_from_file_location('loc_lenh_bot_v2', Path(__file__).resolve().parent.parent / 'cong-cu' / 'loc_lenh_bot_v2.py')
V2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V2)


class KhongNhinTruoc(unittest.TestCase):
    def test_truoc_lay_gia_tri_da_co(self):
        s = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(['2026-01-01 10:00', '2026-01-01 11:00', '2026-01-01 12:00'], utc=True))
        t = pd.DatetimeIndex(pd.to_datetime(['2026-01-01 09:59', '2026-01-01 11:00', '2026-01-01 11:59'], utc=True))
        v = V2.truoc(s, t)
        self.assertTrue(np.isnan(v[0]))
        self.assertEqual(v[1:].tolist(), [2.0, 2.0])                      # đúng giờ đóng thì dùng được; trước đó thì chưa

    def test_cot_chi_dung_tu_thu_bay(self):
        cot = [{'ngay': '2026-01-06', 'oi': 100, 'mm_mua': 60, 'mm_ban': 20}, {'ngay': '2026-01-13', 'oi': 100, 'mm_mua': 70, 'mm_ban': 20}]
        h1 = pd.Series(np.linspace(100, 110, 400), index=pd.date_range('2025-12-20', periods=400, freq='1h', tz='UTC'))
        luc = pd.to_datetime(['2026-01-09 23:00', '2026-01-10 00:00', '2026-01-17 01:00'], utc=True)
        V2.doc_tho = lambda ten: h1                                        # không đọc tệp thật trong bài kiểm
        F = V2.dac_trung_moi(luc.as_unit('ns').asi8,np.array([True, True, False]), h1, cot)
        self.assertEqual(F['cot_mm_pct'].tolist(), [0.0, 40.0, -50.0])  # thứ Sáu chưa có bản tin; thứ Bảy có; lệnh BÁN đổi dấu
        self.assertEqual(F['cot_mm_doi'].iloc[2], -10.0)


if __name__ == '__main__':
    unittest.main()
