# -*- coding: utf-8 -*-
"""Hai phép đối chiếu dùng thư viện ngoài (arch, smartmoneyconcepts): cong-cu/doi_chieu_spa.py và cong-cu/doi_chieu_fvg.py.
Dữ liệu giả, không đọc tệp nến. Máy chưa cài thư viện nào thì bài của thư viện đó được bỏ qua, không tính là hỏng."""
import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent


def _nap(ten: str):
    spec = importlib.util.spec_from_file_location(ten, GOC / 'cong-cu' / f'{ten}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CO_ARCH = importlib.util.find_spec('arch') is not None
CO_SMC = importlib.util.find_spec('smartmoneyconcepts') is not None


@unittest.skipUnless(CO_ARCH, 'chưa cài arch')
class SpaHaiBan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dc = _nap('doi_chieu_spa')
        cls.gia = {ten: d for ten, d, _ in cls.dc.du_lieu_gia()}

    def test_nhieu_thuan_hai_ban_gan_nhau_va_khong_keu_co_lai(self):
        a, b = self.dc.hai_ban(self.gia['Nhiễu thuần, 40 chiến lược'], lan=2000)
        for k in ('duoi', 'nhat_quan', 'tren'):
            self.assertLessEqual(abs(a[k] - b[k]), 0.06, k)
            self.assertGreater(min(a[k], b[k]), 0.10, k)

    def test_chien_luoc_co_lai_that_thi_ca_hai_ban_deu_thay(self):
        a, b = self.dc.hai_ban(self.gia['Một chiến lược có lãi thật giữa 39 chiến lược nhiễu'], lan=2000)
        self.assertLess(a['nhat_quan'], 0.01)
        self.assertLess(b['nhat_quan'], 0.01)
        self.assertTrue(self.dc.dat(a, b))

    def test_tieu_chi_dat(self):
        g = lambda x: {'duoi': x, 'nhat_quan': x, 'tren': x}             # noqa: E731
        self.assertTrue(self.dc.dat(g(0.30), g(0.34)))
        self.assertFalse(self.dc.dat(g(0.30), g(0.40)))                  # lệch quá 0,05
        self.assertFalse(self.dc.dat(g(0.03), g(0.07)))                  # lệch trong ngưỡng nhưng kết luận ở mức 5% khác nhau
        self.assertTrue(self.dc.dat(g(0.001), g(0.008)))


@unittest.skipUnless(CO_SMC, 'chưa cài smartmoneyconcepts')
class FvgThuVien(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dc = _nap('doi_chieu_fvg')

    def _nen(self, n=40):
        o = np.full(n, 100.0)
        df = pd.DataFrame({'open': o, 'high': o + 1, 'low': o - 1, 'close': o + 0.2})      # đi ngang: không có khoảng trống nào
        return df

    def test_thay_khoang_trong_tang_va_giam_dung_hai_mep(self):
        df = self._nen()
        df.iloc[10] = [100.0, 108.0, 100.0, 107.5]                        # nến giữa tăng mạnh
        df.iloc[11] = [107.5, 109.0, 104.0, 108.0]                        # đáy 104 cao hơn đỉnh 101 của nến 9 → khoảng trống tăng 101–104
        df.iloc[12:20] = [108.0, 109.0, 107.0, 108.0]
        df.iloc[20] = [108.0, 108.0, 99.0, 99.5]                          # nến giữa giảm mạnh
        df.iloc[21] = [99.5, 102.0, 98.0, 99.0]                           # đỉnh 102 thấp hơn đáy 107 của nến 19 → khoảng trống giảm 102–107
        df.iloc[22:] = [99.0, 100.0, 98.0, 99.0]
        ra = self.dc.fvg_thu_vien(df)
        self.assertEqual(ra[10], (1, 101.0, 104.0))
        self.assertEqual(ra[20], (-1, 102.0, 107.0))

    def test_khong_sot_khoang_trong_o_cho_noi_hai_khuc(self):
        df = self._nen(60)
        cu = self.dc.KHUC
        try:
            self.dc.KHUC = 10                                             # khúc ngắn để chỗ nối rơi đúng vào các nến của khoảng trống
            for giua in (9, 10, 11, 19, 20):
                x = df.copy()
                x.iloc[giua] = [100.0, 108.0, 100.0, 107.5]
                x.iloc[giua + 1] = [107.5, 109.0, 104.0, 108.0]
                x.iloc[giua + 2:] = [108.0, 109.0, 107.0, 108.0]
                self.assertEqual(self.dc.fvg_thu_vien(x).get(giua), (1, 101.0, 104.0), giua)
        finally:
            self.dc.KHUC = cu


if __name__ == '__main__':
    unittest.main()
