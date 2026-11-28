# -*- coding: utf-8 -*-
"""PBO (cong-cu/kiem_pbo.py): toàn nhiễu thì PBO quanh 0,5; có một chiến lược có lãi thật thì PBO gần 0."""
import importlib.util
import unittest
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location('kiem_pbo', Path(__file__).resolve().parent.parent / 'cong-cu' / 'kiem_pbo.py')
KP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(KP)


class Pbo(unittest.TestCase):
    def test_toan_nhieu(self):
        M = np.random.default_rng(1).normal(0, 1, (480, 40))
        x = KP.pbo(M, 8)
        self.assertEqual(x['so_cach'], 70)
        self.assertGreater(x['pbo'], 0.3)
        self.assertLess(x['pbo'], 0.8)

    def test_co_mot_chien_luoc_that(self):
        g = np.random.default_rng(2)
        M = g.normal(0, 1, (480, 40))
        M[:, 7] += 0.6
        x = KP.pbo(M, 8)
        self.assertLess(x['pbo'], 0.05)
        self.assertLess(x['lo_ngoai_mau'], 0.05)

    def test_chi_so_cot_khong_bien_dong(self):
        self.assertEqual(KP.chi_so(np.zeros((10, 2))).tolist(), [0.0, 0.0])


if __name__ == '__main__':
    unittest.main()
