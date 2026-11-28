# -*- coding: utf-8 -*-
"""Giữ máy thức (so_cong_khai.giu_thuc), với hàm Windows GIẢ: không đổi trạng thái thật của máy."""
import unittest

from so_cong_khai import giu_thuc as G


class GiuThuc(unittest.TestCase):
    def setUp(self):
        self.cu = dict(G.TT)

    def tearDown(self):
        G.TT.clear()
        G.TT.update(self.cu)

    def test_goi_dung_co(self):
        nhan = []
        self.assertTrue(G.bat(lambda co: nhan.append(co) or 0x80000000))
        self.assertEqual(nhan, [0x80000001])                                   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED, không giữ màn hình sáng
        self.assertEqual(G.muc_suc_khoe({'giu_may_thuc': True})['muc'], 'tot')

    def test_that_bai_va_tat(self):
        self.assertFalse(G.bat(lambda co: 0))
        self.assertEqual(G.muc_suc_khoe({'giu_may_thuc': True})['muc'], 'chu_y')
        self.assertEqual(G.muc_suc_khoe({})['muc'], 'tot')
        G.TT.update(thu=False)
        self.assertIsNone(G.muc_suc_khoe({'giu_may_thuc': True}))               # không chạy trong webapp: không báo gì


if __name__ == '__main__':
    unittest.main()
