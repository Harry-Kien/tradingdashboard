"""Bài kiểm cho bản demo tĩnh (cong-cu/xuat_demo.py) và cửa sổ Ảnh chia sẻ trên trang /hieu-suat."""
import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import dich, hieu_suat_trang  # noqa: E402

_spec = importlib.util.spec_from_file_location('xuat_demo', GOC / 'cong-cu' / 'xuat_demo.py')
xuat_demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(xuat_demo)


class XuatDemoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tam = tempfile.TemporaryDirectory()
        cls.ra = Path(cls.tam.name)
        # Xuất dữ liệu minh họa phải độc lập máy chủ/MT5 đang chạy trên máy chủ dự án.
        with mock.patch.object(xuat_demo, 'chup_thi_truong', return_value=None), mock.patch.object(xuat_demo, '_lay') as live_read:
            xuat_demo.main([str(cls.ra)])
            live_read.assert_not_called()

    @classmethod
    def tearDownClass(cls):
        cls.tam.cleanup()

    def test_du_tep_va_du_lieu_minh_hoa(self):
        for lang in ('', 'en/'):
            self.assertTrue((self.ra / f'{lang}index.html').is_file())
            for n in xuat_demo.NGAY:
                for c in xuat_demo.CHIEU:
                    j = json.loads((self.ra / f'{lang}du-lieu/hs-{n}-{c or "all"}.json').read_text(encoding='utf-8'))
                    self.assertTrue(j['mau'])                                         # chỉ dữ liệu giả lập, không bao giờ là tài khoản thật
                    self.assertIn(j['tai_khoan']['so'], ('MINH HỌA', 'SAMPLE'))
                    self.assertIsNone(j['tai_khoan']['so_du'])
        self.assertTrue((self.ra / '.nojekyll').exists())
        self.assertTrue(list((self.ra / 'tinh' / 'phong').glob('*.woff2')))

    def test_duong_dan_tuong_doi(self):
        for f in (self.ra / 'hieu-suat.html', self.ra / 'en' / 'hieu-suat.html'):
            s = f.read_text(encoding='utf-8')
            self.assertNotIn('url(/tinh', s)                                          # chạy được ở thư mục con của GitHub Pages
            self.assertIn('"du-lieu/hs-"', s)
            self.assertIn('og:image', s)

    def test_trang_gioi_thieu(self):
        for lang, f in (('vi', self.ra / 'index.html'), ('en', self.ra / 'en' / 'index.html')):
            s = f.read_text(encoding='utf-8')
            self.assertIn(f'<html lang="{lang}"', s)
            self.assertNotIn('url(/tinh', s)
            for lk in ('href="ke-hoach.html"', 'href="ky-luat.html"', 'href="hieu-suat.html"', 'href="thi-truong.html"', 'og:image'):
                self.assertIn(lk, s, (lang, lk))
            if lang == 'en':
                chu = re.sub(r'<(script|style)\b.*?</\1>|<[^>]+>', ' ', s, flags=re.S).replace('Tiếng Việt', '')
                self.assertIsNone(dich._VI.search(chu), 'bản tiếng Anh còn tiếng Việt')

    def test_ban_tieng_anh_da_dich(self):
        s = (self.ra / 'en' / 'hieu-suat.html').read_text(encoding='utf-8')
        self.assertIn('<html lang="en"', s)
        self.assertIn('Live demo', s)
        j = json.loads((self.ra / 'en/du-lieu/hs-90-all.json').read_text(encoding='utf-8'))
        self.assertFalse(any(dich._VI.search(x['nguon']) for x in j['lenh']))

    def test_cong_khai_chi_gia_lap_va_khong_giu_du_lieu_cu(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'website'
            target.mkdir()
            (target / '.nojekyll').write_text('')
            (target / 'owner-secret.json').write_text('OWNER_PRIVATE_CANARY')
            with mock.patch.object(xuat_demo, '_lay', side_effect=AssertionError('Live API read')), mock.patch.object(xuat_demo.urllib.request, 'urlopen', side_effect=AssertionError('Network read')):
                xuat_demo.main([str(target)])
            self.assertFalse((target / 'owner-secret.json').exists())
            manifest = json.loads((target / 'privacy-manifest.json').read_text())
            self.assertEqual(manifest['data_source'], 'synthetic_only')
            self.assertFalse(manifest['owner_data'])
            for lang in ('', 'en/'):
                self.assertTrue((target / (lang + 'tong-quan.html')).is_file())
                account = json.loads((target / (lang + 'du-lieu/overview/account.json')).read_text(encoding='utf-8'))
                self.assertTrue(account['mau'])
                self.assertEqual(account['so'], 'SAMPLE')
            self.assertFalse(list(target.rglob('*.jpg')), 'Không mang ảnh chụp tài khoản cũ vào website')

    def test_tu_choi_nguon_ca_nhan_va_thu_muc_chua_xac_dinh(self):
        with self.assertRaises(ValueError):
            xuat_demo.main(['--goc', 'http://127.0.0.1:8765'])
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'data.json'
            p.write_text('keep me')
            with self.assertRaises(ValueError):
                xuat_demo.main([temp])
            self.assertEqual(p.read_text(), 'keep me')


class ChupThiTruongTest(unittest.TestCase):
    def test_bo_ten_san_va_thong_so_tai_khoan(self):
        goc_lay = xuat_demo._lay
        that = {'san_sang': True, 'luc': '2026-11-25T06:00:00+00:00', 'ds': [{'ma': 'EURUSDp'}],
                'tai_khoan': {'tien': 'USD', 'don_bay': 500, 'goi_ky_quy': 80.0, 'dung_lenh': 20.0, 'san': 'Sàn Thật Ltd'}}
        xuat_demo._lay = lambda goc, p, timeout=60: json.loads(json.dumps(that)) if p == '/api/thi-truong' else {'ma': 'EURUSDp'}
        try:
            c = xuat_demo.chup_thi_truong('http://x')
        finally:
            xuat_demo._lay = goc_lay
        self.assertEqual(c['tt']['tai_khoan'], xuat_demo.TK_CHUNG)
        self.assertNotIn('Sàn Thật', json.dumps(c, ensure_ascii=False, default=str))
        self.assertEqual(set(c['kt']), {'EURUSDp'})

    def test_khong_co_webapp_thi_bo_qua(self):
        self.assertIsNone(xuat_demo.chup_thi_truong('http://127.0.0.1:9'))

    def test_o_trang_thai_ghi_anh_chup(self):
        from datetime import datetime, timezone
        js = xuat_demo.js_chup(datetime(2026, 11, 25, 6, 50, tzinfo=timezone.utc))
        self.assertIn('Ảnh chụp', js)
        self.assertIn('13:50 25/11/2026', js)                                         # giờ Việt Nam


class AnhChiaSeTest(unittest.TestCase):
    def test_trang_co_cua_so_anh_chia_se(self):
        s = hieu_suat_trang.trang_hieu_suat('Thử <b>')
        self.assertIn('id="hs-chia"', s)
        self.assertEqual(s.count('<dialog'), 1)
        self.assertIn('data-ten="Thử &lt;b&gt;"', s)                                 # tên được thoát HTML
        self.assertIn('id="the-tien"', s)
        self.assertNotRegex(s, re.compile(r'<input type="checkbox" id="the-tien" checked'))   # mặc định không hiện số tiền



class LocCongKhaiTest(unittest.TestCase):
    """Demo chỉ giới thiệu trang đã có ở kho công khai: bỏ mục menu, mục tìm nhanh và nút kênh Telegram mà kho chưa có."""

    def test_loc_theo_kho(self):
        with tempfile.TemporaryDirectory() as d:
            s = Path(d) / 'so_cong_khai'
            s.mkdir()
            (s / 'web.py').write_text("if path == '/ke-hoach':\n    pass\nif path in ('/', '/thi-truong'):\n    pass\n", encoding='utf-8')
            (s / 'thuong_hieu.py').write_text("TEN = 'x'\n", encoding='utf-8')
            cu, xuat_demo.KHO_MAY = xuat_demo.KHO_MAY, Path(d)
            try:
                html = ('<a class="nv-i" href="/ke-hoach"><b>KH</b></a><a class="nv-i" href="/telegram"><b>TG</b></a>'
                        '<a class="nv-d" href="/thi-truong#bang-gia">TT</a><a class="nv-d" href="/sao-luu">SL</a>'
                        '<a class="nv-tg" href="https://t.me/x"><span>Kênh</span></a>'
                        '<div data-tim="' + json.dumps([{'t': 'A', 'h': '/ke-hoach'}, {'t': 'B', 'h': '/telegram'}]).replace('"', '&quot;') + '"></div>')
                ra = xuat_demo.loc_cong_khai(html)
            finally:
                xuat_demo.KHO_MAY = cu
        self.assertIn('href="/ke-hoach"', ra)
        self.assertIn('href="/thi-truong#bang-gia"', ra)
        for x in ('href="/telegram"', 'href="/sao-luu"', 'nv-tg'):
            self.assertNotIn(x, ra)
        tim = json.loads(re.search(r'data-tim="([^"]*)"', ra).group(1).replace('&quot;', '"'))
        self.assertEqual([x['h'] for x in tim], ['/ke-hoach'])

    def test_khong_co_kho_thi_giu_nguyen(self):
        cu, xuat_demo.KHO_MAY = xuat_demo.KHO_MAY, Path(tempfile.gettempdir()) / 'khong-co-kho-nay'
        try:
            self.assertEqual(xuat_demo.loc_cong_khai('<a class="nv-i" href="/telegram">x</a>'), '<a class="nv-i" href="/telegram">x</a>')
        finally:
            xuat_demo.KHO_MAY = cu

if __name__ == '__main__':
    unittest.main()
