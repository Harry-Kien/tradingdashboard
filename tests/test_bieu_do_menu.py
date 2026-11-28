# -*- coding: utf-8 -*-
"""Menu chuột phải của trang Biểu đồ (26/11/2026): nằm trong bieu_do_menu.py và đọc biểu đồ qua bốn chỗ móc trong bieu_do.py.
Thiếu một chỗ móc thì menu hỏng âm thầm (mọi bài kiểm Python khác vẫn qua), nên kiểm từng chỗ."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import bieu_do, bieu_do_menu, dich  # noqa: E402


class MenuChuotPhai(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = bieu_do.trang_bieu_do('Harry')

    def test_trang_nap_menu(self):
        self.assertIn('.mnp{', self.h)
        self.assertIn("window.MNP={ve()", self.h)
        self.assertLess(self.h.index('window.BDMN=()=>'), self.h.index("window.MNP={ve()"))   # hàm lộ ra trước khi menu đọc

    def test_moc_lo_du_ham(self):
        moc = re.search(r'window\.BDMN=\(\)=>\(\{([^}]*)\}\)', bieu_do.JS).group(1)
        for k in re.findall(r'\bg\.(\w+)', bieu_do_menu.JS):
            self.assertIn(k, [field.split(':', 1)[0] for field in moc.split(',')], f'menu dùng g.{k} nhưng BDMN không có')

    def test_hinh_an_va_khoa(self):
        self.assertIn('VE.ds){if(h.an)continue;', bieu_do.JS)                  # ẩn riêng một hình
        self.assertIn('if(hh&&hh.khoa){veTb();lwPhu();return}', bieu_do.JS)     # hình khóa: chỉ chọn, không kéo

    def test_ve_lai_duong_canh_bao(self):
        self.assertIn('if(window.MNP)try{MNP.ve()}', bieu_do.JS)

    def test_phat_lai_khong_no_canh_bao(self):
        """Phát lại nến cũ (bieu_do_phat_lai.py) thay D bằng bản cắt: giá cũ không được làm cảnh báo giá nổ."""
        self.assertIn('if(CBV()||window.PHAT_LAI||!g.D', bieu_do_menu.JS)
        self.assertIn('ve(){if(window.PHAT_LAI)return;', bieu_do_menu.JS)

    def test_dung_canh_bao_may_chu(self):
        """Có hệ thống cảnh báo của máy chủ (canh_bao_ve.py, window.CBV) thì menu dùng nó, không lưu cảnh báo trong trình duyệt nữa, và chuyển
        cảnh báo cũ sang máy chủ một lần."""
        js = bieu_do_menu.JS
        self.assertIn('c.themGia(+so(g,p))', js)
        self.assertIn("if(k==='cbv'){const c=CBV();if(c)c.mo(id);return}", js)
        self.assertIn('function chuyenBao(g)', js)
        h = bieu_do.trang_bieu_do('Harry')
        self.assertLess(h.index('window.MNP={ve()'), h.index('window.CBV='))       # CBV nạp sau menu và bọc MNP.ve

    def test_thoat_ky_tu_truong_cua_hinh(self):
        """Hình vẽ đồng bộ từ máy chủ về mọi máy (hinh_ve.py), nên trường của hình phải được thoát ký tự trước khi vào HTML của menu
        (rà soát bảo mật 26/11/2026: h.k chứa thẻ HTML từng có thể chạy mã qua MN.innerHTML)."""
        js = bieu_do_menu.JS
        self.assertIn('const ten=esc((g.VEC[h.k]||[h.k])[0])', js)
        self.assertIn('data-v="${esc(o.v)}"', js)
        self.assertIn('<span>${esc(chu)}</span>', js)

    def test_khong_dat_lenh(self):
        """Menu chỉ tính và mở trang Kiểm tra lệnh, không gọi API đặt lệnh nào."""
        self.assertNotRegex(bieu_do_menu.JS, r"fetch\(")
        self.assertIn("window.open('/kiem-lenh?'", bieu_do_menu.JS)

    def test_ten_thuong_hieu_co_dinh(self):
        from so_cong_khai.thuong_hieu import TEN                               # noqa: PLC0415
        self.assertIn(TEN, bieu_do_menu.JS)

    def test_dich_du_tieng_anh(self):
        thu = set()
        dich.dich_html(self.h, dich.tu_dien('en'), thu)
        cua_menu = lambda k: re.search(r"['>`]\s*" + re.escape(k.split('{')[0].strip()) + r"\s*(?:['<`]|\$\{)", bieu_do_menu.JS)  # noqa: E731
        thieu = [k for k in thu if k.split('{')[0].strip() and cua_menu(k)]
        self.assertEqual(thieu, [])


if __name__ == '__main__':
    unittest.main()
