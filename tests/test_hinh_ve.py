"""Lưu hình vẽ trên máy chủ (hinh_ve.py): đọc, ghi, phiên bản, kiểm đầu vào, chặn đường dẫn lạ; trang Biểu đồ có lớp đồng bộ."""
import tempfile
import unittest
from pathlib import Path

from so_cong_khai import hinh_ve


class HinhVeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.goc = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_doc_ghi_va_phien_ban(self):
        self.assertEqual(hinh_ve.doc('XAU', self.goc), {'ds': [], 'ban': None, 'luc': None})
        ds = [{'id': 'a1', 'k': 'xu', 'a': {'t': 1, 'p': 2}, 'b': {'t': 3, 'p': 4}}]
        self.assertEqual(hinh_ve.luu('XAU', ds, self.goc, now=10)['ban'], 1)
        self.assertEqual(hinh_ve.luu('XAU', ds + [{'id': 'b2', 'k': 'ngang', 'a': {'t': 1, 'p': 5}}], self.goc, now=11)['ban'], 2)
        x = hinh_ve.doc('XAU', self.goc)
        self.assertEqual((x['ban'], len(x['ds']), x['luc']), (2, 2, 11))
        self.assertEqual(hinh_ve.doc('EURUSDp', self.goc)['ban'], None)           # mỗi mã một tệp

    def test_giu_ban_con_hinh_gan_nhat(self):
        """Lỡ xóa hết (hay kịch bản thử xóa bộ nhớ trình duyệt): bản còn hình gần nhất nằm ở <mã>.truoc.json; ghi bản rỗng lần nữa không đè lên nó."""
        ds = [{'id': f'h{i}', 'k': 'ngang', 'a': {'t': 1, 'p': i}} for i in range(6)]
        hinh_ve.luu('XAU', ds, self.goc)
        hinh_ve.luu('XAU', [], self.goc)
        hinh_ve.luu('XAU', [], self.goc)
        import json
        truoc = json.loads((self.goc / 'du-lieu' / 'hinh-ve' / 'XAU.truoc.json').read_text(encoding='utf-8'))
        self.assertEqual(len(truoc['ds']), 6)
        self.assertIn("v==='[]'&&n0>=5&&!daHoi&&!confirm(", hinh_ve.JS)
        self.assertIn('const daHoi=window.HVD_DA_HOI===true;window.HVD_DA_HOI=false;', hinh_ve.JS)   # cờ dùng một lần

    def test_tu_choi(self):
        for ma in ('', '..', 'a/b', '..\\x', 'x' * 41):
            with self.subTest(ma=ma), self.assertRaises(ValueError):
                hinh_ve.luu(ma, [], self.goc)
        for ds in ({'id': 'a'}, [1], [{'k': 'xu'}], [{'id': 'a', 'k': 'xu'}] * (hinh_ve.TOI_DA_HINH + 1),
                   [{'id': 'a', 'k': '<img src=x onerror=alert(1)>'}], [{'id': '"><script>', 'k': 'xu'}],         # chặn chèn HTML (stored XSS)
                   [{'id': 'a', 'k': 'xu', 'mau': 'red;background:url(x)'}],
                   [{'id': 'a', 'k': 'chu', 'chu': 'x' * (hinh_ve.TOI_DA_BYTE + 10)}]):
            with self.assertRaises(ValueError):
                hinh_ve.luu('XAU', ds, self.goc)
        self.assertFalse((self.goc / 'du-lieu' / 'hinh-ve' / 'XAU.json').exists())

    def test_trang_co_lop_dong_bo(self):
        from so_cong_khai import bieu_do
        h = bieu_do.trang_bieu_do('Harry')
        self.assertIn('window.HVD=', h)
        self.assertIn("'so-ve:'+(g.ma||'XAU')", hinh_ve.JS)                      # cùng khóa với công cụ vẽ (veKhoa)
        self.assertIn("veKhoa=()=>'so-ve:'+(ma||'XAU')", bieu_do.JS)
        self.assertIn('if(g2.VE.keo||g2.VE.tam)return', hinh_ve.JS)            # không thay hình khi đang kéo hay đang vẽ
        self.assertIn("if(document.querySelector('.venhap,.mnp,.cbv-nen'))return", hinh_ve.JS)   # đang gõ chữ, menu hay hộp cảnh báo mở
        self.assertIn('if(!dau&&v!==DONG[k])return', hinh_ve.JS)                # còn thay đổi chưa gửi thì không nạp đè
        self.assertIn('v!==DONG[k]&&v!==choV){choV=v;', hinh_ve.JS)              # lỗi đã gặp: hẹn lại mỗi 0,5 giây nên không bao giờ gửi


if __name__ == '__main__':
    unittest.main()
