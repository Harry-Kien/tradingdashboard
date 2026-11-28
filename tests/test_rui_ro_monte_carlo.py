# -*- coding: utf-8 -*-
"""Monte Carlo rủi ro (cong-cu/rui_ro_monte_carlo.py): lấy mẫu theo khối đúng dạng, và xác suất mất nửa vốn tăng theo mức rủi ro mỗi lệnh."""
import importlib.util
import unittest
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location('rui_ro_mc', Path(__file__).resolve().parent.parent / 'cong-cu' / 'rui_ro_monte_carlo.py')
MC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MC)


class MonteCarlo(unittest.TestCase):
    def test_chi_so_khoi(self):
        g = np.random.default_rng(0)
        k = MC.chi_so_khoi(50, 1000, 10, g)
        self.assertTrue(((k >= 0) & (k < 50)).all())
        lien = np.mean(np.diff(k) % 50 == 1)
        self.assertGreater(lien, 0.85)                                  # phần lớn là bước nối tiếp trong khối

    def test_rui_ro_tang_theo_muc(self):
        r = np.r_[np.full(45, 1.0), np.full(55, -1.0)]                  # chuỗi lỗ nhẹ
        x = MC.mo_phong(r, 200, lan=400, muc_rui=(0.01, 0.1, 0.5))
        v = list(x['mat_nua_von'].values())
        self.assertLessEqual(v[0], v[1])
        self.assertLessEqual(v[1], v[2])
        self.assertGreater(v[2], 90.0)                                  # rủi ro 50% mỗi lệnh: gần như chắc chắn có lúc mất nửa vốn
        self.assertGreater(x['tong_r']['ty_le_nam_lo'], 50)

    def test_chuoi_co_lai_ro(self):
        r = np.random.default_rng(3).permutation(np.r_[np.full(70, 1.0), np.full(30, -1.0)])     # thắng thua xen kẽ ngẫu nhiên
        x = MC.mo_phong(r, 200, lan=300)
        self.assertEqual(x['tong_r']['ty_le_nam_lo'], 0.0)
        self.assertEqual(x['mat_nua_von']['0.5%'], 0.0)


if __name__ == '__main__':
    unittest.main()
