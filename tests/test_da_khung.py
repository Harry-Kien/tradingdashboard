# -*- coding: utf-8 -*-
"""Trang Đa khung (/da-khung): nhiều khung của một mã trên một màn hình, chạy theo tick bằng MỘT luồng, con trỏ đồng bộ."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import da_khung_trang, dich, trang  # noqa: E402
from so_cong_khai.thuong_hieu import TEN  # noqa: E402

GOC = Path(__file__).resolve().parent.parent / 'so_cong_khai'


class DaKhung(unittest.TestCase):
    def test_dung_luong_gia_dung_chung(self):
        """Trình duyệt chỉ có khoảng 6 kết nối mỗi máy chủ: 4 luồng SSE (mỗi ô một mã) sẽ làm nghẽn cả webapp. Trang không tự mở luồng nào mà dùng
        luồng giá dùng chung window.TT (một kết nối cho mọi mã, mọi tab)."""
        self.assertEqual(len(re.findall(r'new EventSource\(', da_khung_trang.JS)), 0)
        self.assertIn("TT.on((l,ds)=>{if(l==='gia'&&ds)apGia(ds)", da_khung_trang.JS)
        from so_cong_khai import thi_truong_trang                                 # noqa: PLC0415
        self.assertIn(thi_truong_trang.JS_CHUNG, da_khung_trang.trang_da_khung(TEN))

    def test_bo_cuc_va_dong_bo(self):
        h = da_khung_trang.trang_da_khung(TEN)
        for v in ('data-v="2"', 'data-v="4"', 'data-v="1+3"', 'id="dk-dma"', 'id="dk-dkh"', 'id="dk-dtro"', 'id="dk-dtg"'):
            self.assertIn(v, h)
        self.assertIn("addEventListener('dblclick'", da_khung_trang.JS)             # bấm đúp một ô mở trang Biểu đồ

    def test_con_tro_dong_bo_va_tai_lai(self):
        js = da_khung_trang.JS
        self.assertIn('subscribeCrosshairMove', js)
        self.assertIn('setCrosshairPosition(gia,k.cs[j][0],k.nen)', js)
        self.assertIn('if(r.fresh)retry(o)', js)                              # sang nến mới thì đồng bộ lại, có gom yêu cầu

    def test_chi_doc(self):
        self.assertNotIn("method:'POST'", da_khung_trang.JS)

    def test_tuyen_menu_va_ghi_nguon(self):
        self.assertIn("if path == '/da-khung':", (GOC / 'web.py').read_text(encoding='utf-8'))
        self.assertTrue(any(c[2] == '/da-khung' for m in trang.MENU if m[3] for c in m[3]))
        h = da_khung_trang.trang_da_khung(TEN)
        self.assertIn('attributionLogo:false', h)
        self.assertIn('Copyright (c) 2026 TradingView, Inc.', h)               # tắt logo thì phải ghi nguồn (Apache-2.0, NOTICE)

    def test_dich_du_tieng_anh(self):
        thu = set()
        dich.dich_html(da_khung_trang.trang_da_khung(TEN), dich.tu_dien('en'), thu)
        self.assertEqual(sorted(thu), [])


if __name__ == '__main__':
    unittest.main()
