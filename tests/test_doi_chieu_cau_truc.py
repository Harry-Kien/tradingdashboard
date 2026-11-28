# -*- coding: utf-8 -*-
"""Bản dựng lại độc lập của phá cấu trúc (cong-cu/doi_chieu_cau_truc.py) phải trùng hẳn so_cong_khai.phuong_phap._pha_cau_truc, kể cả khi đỉnh/đáy
bằng nhau, và vòng lặp quét thanh khoản viết tay phải đúng định nghĩa."""
import importlib.util
import unittest
from pathlib import Path

import numpy as np

from so_cong_khai import phuong_phap as PP

spec = importlib.util.spec_from_file_location('doi_chieu_cau_truc', Path(__file__).resolve().parent.parent / 'cong-cu' / 'doi_chieu_cau_truc.py')
DC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(DC)


def _chuoi(n, hat, lam_tron=None):
    g = np.random.default_rng(hat)
    c = 100 + np.cumsum(g.normal(0, 1, n))
    o = np.r_[c[0], c[:-1]]
    h, l = np.maximum(o, c) + g.uniform(0, 1, n), np.minimum(o, c) - g.uniform(0, 1, n)
    if lam_tron:                                                       # làm tròn thô để có nhiều đỉnh/đáy bằng nhau
        h, l, c = np.round(h / lam_tron) * lam_tron, np.round(l / lam_tron) * lam_tron, np.round(c / lam_tron) * lam_tron
    return h, l, c


class PhaCauTruc(unittest.TestCase):
    def test_trung_hang_tren_chuoi_ngau_nhien(self):
        for hat, tron in ((1, None), (2, None), (3, 1.0), (4, 2.0)):
            h, l, c = _chuoi(3000, hat, tron)
            a, ca = PP._pha_cau_truc(h, l, c)
            b, cb = DC.pha_doc_lap(h, l, c, PP.K_SWING)
            self.assertGreater(len(a), 50)
            self.assertEqual(a, b, hat)
            self.assertTrue(np.array_equal(ca, cb), hat)

    def test_dinh_day_hoa_cung_tinh(self):
        x = np.array([1, 2, 3, 5, 3, 2, 1, 2, 5, 2, 1, 0, 0])
        self.assertEqual(DC.dinh_day(x, 2, True).tolist(), [3, 8])

    def test_quet_tay(self):
        h = np.r_[np.full(21, 10.0), 11.0, 10.0]
        l = np.r_[np.full(21, 9.0), 8.0, 9.0]
        c = np.r_[np.full(21, 9.5), 9.5, 9.5]
        self.assertEqual(DC.quet_tay(h, l, c, 20, 0), [(21, 'day'), (21, 'dinh')])   # một nến vừa quét đáy vừa quét đỉnh rồi đóng ở giữa


if __name__ == '__main__':
    unittest.main()
