# -*- coding: utf-8 -*-
"""Trang Bắt đầu sử dụng (/bat-dau) cho người mới cài bản chia sẻ, và lời mời ở trang Thị trường (trang đầu của bản chia sẻ)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import bat_dau_trang, dich, thi_truong_trang, trang  # noqa: E402

GOC = Path(__file__).resolve().parent.parent / 'so_cong_khai'


class BatDau(unittest.TestCase):
    def test_trang_co_nam_buoc_tu_kiem(self):
        h = bat_dau_trang.trang_bat_dau('Harry')
        for i in ('b-mt5', 'b-tk', 'b-bd', 'b-cc', 'b-them'):
            self.assertIn(f'id="{i}"', h)
        self.assertIn("json('/api/tinh-trang')", h)                          # mỗi bước tự kiểm bằng dữ liệu thật
        self.assertIn("json('/api/tai-khoan')", h)

    def test_chi_doc_khong_gui_gi(self):
        js = bat_dau_trang.JS
        self.assertNotIn("method:'POST'", js)
        self.assertNotRegex(js, r"fetch\('/api/(?!tinh-trang|tai-khoan)")

    def test_co_tuyen_va_muc_menu(self):
        self.assertIn("if path == '/bat-dau':", (GOC / 'web.py').read_text(encoding='utf-8'))
        self.assertTrue(any(m[0] == 'hoc' and any(c[2] == '/bat-dau' for c in m[3]) for m in trang.MENU if m[3]))

    def test_moi_nguoi_moi_o_trang_thi_truong(self):
        h = thi_truong_trang.trang_thi_truong('Harry')
        self.assertIn('id="tt-moi" hidden', h)                                 # ẩn sẵn, chỉ hiện khi chưa xem trang bắt đầu
        self.assertIn('href="/bat-dau"', h)
        self.assertIn('localStorage.getItem("so-bat-dau")', h)

    def test_ban_tieng_anh_nhan_dung_muc_tinh_trang(self):
        """Lỗi đã gặp: bản tiếng Anh báo "MT5 is not connected yet" dù đã nối, vì /api/tinh-trang trả tên mục đã dịch còn mã so với tên tiếng Việt
        nằm sau === (bộ dịch cố ý không đổi chuỗi so sánh). Tên mục phải nằm trong chuỗi thường để được dịch cùng."""
        h = dich.dich_html(bat_dau_trang.trang_bat_dau('x'), dich.tu_dien('en'))
        self.assertIn("gia:'Live prices from MT5'", h)
        self.assertNotIn("==='Giá trực tiếp", h)

    def test_dich_du_tieng_anh(self):
        thu = set()
        from so_cong_khai.thuong_hieu import TEN                                # noqa: PLC0415
        dich.dich_html(bat_dau_trang.trang_bat_dau(TEN), dich.tu_dien('en'), thu)
        self.assertEqual(sorted(thu), [])


if __name__ == '__main__':
    unittest.main()
