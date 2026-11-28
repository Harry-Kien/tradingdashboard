# -*- coding: utf-8 -*-
"""Các hàm lõi của cong-cu/loc_lenh_bot.py: kiểm định chéo có tách khoảng (không để lệnh chồng lấn rò từ phần kiểm sang phần học), ngưỡng giữ,
và phép so với lọc ngẫu nhiên."""
import importlib.util
import unittest
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location('loc_lenh_bot', Path(__file__).resolve().parent.parent / 'cong-cu' / 'loc_lenh_bot.py')
LB = importlib.util.module_from_spec(spec)
spec.loader.exec_module(LB)
GIO = 3600 * 10 ** 9


class KhoiTach(unittest.TestCase):
    def test_khong_co_lenh_cham_khoi_kiem_trong_phan_hoc(self):
        g = np.random.default_rng(1)
        t_vao = np.sort(g.integers(0, 2000, 300)) * GIO
        t_ra = t_vao + g.integers(1, 30, 300) * GIO
        for hoc, kiem in LB.khoi_tach(t_vao, t_ra, 5, 24 * GIO):
            a, b = t_vao[kiem].min() - 24 * GIO, t_ra[kiem].max() + 24 * GIO
            self.assertFalse(np.any((t_ra[hoc] >= a) & (t_vao[hoc] <= b)))
            self.assertEqual(len(np.intersect1d(hoc, kiem)), 0)
        self.assertEqual(sorted(np.concatenate([k for _, k in LB.khoi_tach(t_vao, t_ra, 5, 24 * GIO)]).tolist()), list(range(300)))

    def test_lenh_dai_vat_qua_ranh_bi_bo(self):
        t_vao = np.array([0, 10, 20, 30, 40, 50]) * GIO
        t_ra = t_vao + GIO
        t_ra[1] = 45 * GIO                                             # lệnh thứ hai mở rất lâu, chạm khối cuối
        hoc, kiem = LB.khoi_tach(t_vao, t_ra, 3, 0)[2]
        self.assertEqual(kiem.tolist(), [4, 5])
        self.assertNotIn(1, hoc.tolist())
        self.assertEqual(hoc.tolist(), [0, 2, 3])

    def test_chua_xep_theo_gio_thi_bao_loi(self):
        with self.assertRaises(AssertionError):
            LB.khoi_tach(np.array([5, 1]) * GIO, np.array([6, 2]) * GIO, 2, 0)


class NguongVaNgauNhien(unittest.TestCase):
    def test_nguong_giu_dung_ty_le(self):
        p = np.linspace(0, 1, 1001)
        self.assertAlmostEqual((p >= LB.nguong(p, 0.3)).mean(), 0.3, places=2)

    def test_p_ngau_nhien(self):
        r = np.r_[np.full(50, 1.0), np.full(50, -1.0)]
        self.assertLess(LB.p_ngau_nhien(r, 20, 1.0, 500), 0.01)        # chọn đúng 20 lệnh thắng: ngẫu nhiên gần như không làm được
        self.assertGreater(LB.p_ngau_nhien(r, 20, 0.0, 500), 0.3)       # mức trung bình: ngẫu nhiên làm được thường xuyên

    def test_so_do(self):
        x = LB.so_do(np.array([1.0, -1.0, 2.0, -1.0, -1.0]))
        self.assertEqual((x['n'], x['thang'], x['tong'], x['dd']), (5, 40.0, 0.0, 2.0))


if __name__ == '__main__':
    unittest.main()
