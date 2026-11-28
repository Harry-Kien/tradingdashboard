# -*- coding: utf-8 -*-
"""Khung chỉ để xem (26/11/2026, như menu khung của TradingView): M2, M3, M10, H2, H3, W1, MN1. Đọc thẳng từ MT5 qua đường chung;
vòng nến của luật (song.SO_NEN) không đổi, phím 1–7 vẫn là 7 khung chính."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import bieu_do, da_ma, gia, song  # noqa: E402

XEM = ('M2', 'M3', 'M10', 'H2', 'H3', 'W1', 'MN1')


class KhungXem(unittest.TestCase):
    def test_may_chu_nhan_khung_xem(self):
        for tf in XEM:
            self.assertIn(tf, song.KHUNG_XEM)
            self.assertIn(tf, gia.KHUNG)
            self.assertIn(tf, da_ma.SO_NEN)

    def test_vong_nen_cua_luat_khong_doi(self):
        """Vòng nến của EA/luật không biết các khung này: thêm vào SO_NEN sẽ làm mất kết nối MT5 mỗi lần đọc."""
        self.assertEqual(sorted(song.SO_NEN), ['D1', 'H1', 'H4', 'M1', 'M15', 'M30', 'M5'])
        self.assertNotIn('M2', gia._QUY)

    def test_trang_co_bang_khung_khac_sau_bay_nut_chinh(self):
        h = bieu_do.trang_bieu_do('Harry')
        seg = h[h.index('class="seg tf"'):]
        seg = seg[:seg.index('</details>')]
        tfs = re.findall(r'data-tf="(\w+)"', seg)
        self.assertEqual(tfs[:7], ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'])       # phím 1–7 theo thứ tự nút
        self.assertEqual(tuple(tfs[7:]), XEM)
        self.assertIn('class="tfk"', seg)

    def test_bang_khac_khong_bi_cat(self):
        """Lỗi người dùng báo (26/11/2026): .seg có overflow:hidden nên bảng "Khác" mở mà không thấy. Bài thử bấm bằng máy không phát hiện được."""
        self.assertIn('.seg.tf{overflow:visible}', bieu_do.CSS)
        self.assertIn('.tfk:not([open]) .tfk-pop{display:none}', bieu_do.CSS)


if __name__ == '__main__':
    unittest.main()
