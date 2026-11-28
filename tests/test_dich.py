"""Bài kiểm cho lớp song ngữ (so_cong_khai/dich.py): dịch đúng đoạn trọn vẹn, giữ số, không đụng mã, chú thích, regex và chuỗi trong phép so sánh,
thoát dấu nháy đúng kiểu chuỗi, chọn ngôn ngữ theo cookie và ?lang=, và từ điển tiếng Anh không làm hỏng ô {n}."""
from functools import partial
from http_owner import owner_urlopen
import json
import re
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import dich, trang, web  # noqa: E402

D = {'Xin chào': "Hello 'x'", 'tăng ·': 'up ·', 'giảm': 'down', 'Đang': 'NO', 'Đang tải…': 'Loading…', 'Giá cũ {0} phút': 'Price {0} min old',
     'Thêm vào danh sách theo dõi': 'Add to watchlist', 'Mua': 'Buy', '__locale__': 'en-US', '{0} và {1}': '{1} and {0}'}


class DichTest(unittest.TestCase):
    def test_khoa_thay_so(self):
        self.assertEqual(dich.khoa('  Giá cũ  25 phút '), ('Giá cũ {0} phút', ['25']))
        self.assertEqual(dich.khoa('Khung M15 có 1.234,5 lệnh')[0], 'Khung M15 có {0} lệnh')     # M15 là tên, không phải số
        self.assertEqual(dich.khoa('EMA20 âm 0,12R và −0,35R'), ('EMA20 âm {0}R và −{1}R', ['0,12', '0,35']))   # lấy trọn số, không cắt dở

    def test_dich_doan_giu_khoang_trang_va_doi_cho_so(self):
        self.assertEqual(dich.dich_doan(' Giá cũ 7 phút ', D), ' Price 7 min old ')
        self.assertEqual(dich.dich_doan('3 và 4', D), '4 and 3')
        thu = set()
        self.assertEqual(dich.dich_doan('Chưa có', D, thu), 'Chưa có')
        self.assertEqual(thu, {'Chưa có'})
        self.assertEqual(dich.dich_doan('EURUSD', D), 'EURUSD')                                   # không phải tiếng Việt: giữ nguyên

    def test_js_khong_dung_ma_chu_thich_regex_so_sanh(self):
        js = (r"""b=`Đang`===s;a===`Đang`?1:'Xin chào';x.startsWith('Đang');if(s=='Đang')f();y=`<b>${n}</b> tăng · ${m} giảm`;r=/['"]/g;"""
              r"""z="Giá cũ 25 phút";k=n.toLocaleString('vi-VN');// chú thích: 'Đang tải…'""" '\n' r"""t=`${a?`Mua`:'Đang tải…'}`;""")
        ra = dich.dich_js(js, D)
        self.assertIn("b=`Đang`===s;a===`Đang`?1:'Hello \\'x\\''", ra)                            # so sánh giữ nguyên, nháy được thoát
        self.assertIn("x.startsWith('Đang');if(s=='Đang')", ra)
        self.assertIn('y=`<b>${n}</b> up · ${m} down`', ra)
        self.assertIn(r"""r=/['"]/g;""", ra)
        self.assertIn('z="Price 25 min old"', ra)
        self.assertIn("toLocaleString('en-US')", ra)
        self.assertIn("// chú thích: 'Đang tải…'", ra)
        self.assertIn("t=`${a?`Buy`:'Loading…'}`;", ra)

    def test_html_thuoc_tinh_script_va_the_do_dang(self):
        h = '<p title="Xin chào">Đang tải…</p><script>let a=\'Mua\',b=`<td><button class="sao" title="Thêm vào danh sách theo dõi" x="${y}">★</button>`;</script><b> Giá cũ 3 phút </b>'
        ra = dich.dich_html(h, D)
        self.assertIn('title="Hello &#x27;x&#x27;">Loading…</p>', ra)
        self.assertIn("let a='Buy'", ra)
        self.assertIn('title="Add to watchlist" x="${y}"', ra)
        self.assertIn('<b> Price 3 min old </b>', ra)

    def test_json_giu_ma_va_duong_dan(self):
        x = dich.dich_json({'ly_do': 'Giá cũ 7 phút', 'ma': 'Mua', 'link': 'Mua', 'ds': ['Mua', 'x', 3]}, D)
        self.assertEqual(x, {'ly_do': 'Price 7 min old', 'ma': 'Mua', 'link': 'Mua', 'ds': ['Buy', 'x', 3]})

    def test_gia_tri_trong_ma_khong_bi_dich(self):
        """Lỗi đã gặp: 'mua' trong `chieu={rr:'mua'}` bị dịch thành 'buy' nên /api/tinh trả 400. Giá trị không dấu, không khoảng trắng là mã."""
        d = dict(dich.tu_dien('en')) or D
        js = "chieu={rr:'mua',pl:'ban',fb:'tang'};k='dinh_day|2026|MUA';f('#pl-vao');x='tn-xem'"
        self.assertEqual(dich.dich_js(js, {**d, 'mua': 'buy', 'ban': 'sell'}), js)
        self.assertTrue(dich.la_tieng_viet('% mua'))
        self.assertTrue(dich.la_tieng_viet('Mua'))

    def test_nhan_lenh_dang_mo_dich_moi_ten_ea(self):
        """Lỗi đã gặp: nhãn "EA E BÁN 0.02" đến từ API thành một khóa có tên EA nên bản tiếng Anh còn tiếng Việt. Trang Biểu đồ ghép nhãn từ
        'ten', 'lot' và chữ Mua/Bán của chính trang, nên mọi tên EA đều ra BUY/SELL."""
        from so_cong_khai import bieu_do                                           # noqa: PLC0415
        en = dich.dich_html(bieu_do.trang_bieu_do('Thử'), dich.tu_dien('en'))
        self.assertIn("(o.huong==='BUY'?'Buy':'Sell').toUpperCase()", en)
        self.assertEqual(dich.dich_json({'ten': 'EA Z', 'lot': 0.02, 'huong': 'SELL'}, D), {'ten': 'EA Z', 'lot': 0.02, 'huong': 'SELL'})

    def test_chon_ngon_ngu(self):
        self.assertEqual(dich.ngon_ngu(None), 'vi')
        self.assertEqual(dich.ngon_ngu('a=1; lang=en'), 'en')
        self.assertEqual(dich.ngon_ngu('lang=en', 'x=1&lang=vi'), 'vi')                            # ?lang= thắng cookie
        self.assertEqual(dich.ngon_ngu('lang=fr'), 'vi')

    def test_tu_dien_tieng_anh_hop_le(self):
        d = dich.tu_dien('en')
        if not d:
            self.skipTest('chưa có từ điển tiếng Anh')
        for k, v in d.items():
            if k.startswith('__'):
                continue
            self.assertEqual(sorted(set(re.findall(r'\{\d+\}', k))), sorted(set(re.findall(r'\{\d+\}', v))), k)
            ten_rieng = v.replace('López', '').replace('Tele dự báo', '')                         # tên người, tên dự án: giữ nguyên
            self.assertFalse(dich._VI.search(ten_rieng), f'bản dịch còn tiếng Việt: {k!r} → {v!r}')

    def test_may_chu_dich_theo_cookie(self):
        goc = dich.tu_dien
        dich.tu_dien = lambda lang: D
        try:
            with tempfile.TemporaryDirectory() as d:
                ch = Path(d) / 'cau-hinh.json'
                ch.write_text(json.dumps({'ten': 'Thử', 'gia': {}}), encoding='utf-8')
                srv = web.tao_may_chu(str(ch), port=0)
                open_owner = partial(owner_urlopen, root=ch.parent)
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                u = f'http://127.0.0.1:{srv.server_address[1]}'
                try:
                    vi = open_owner(u + '/cong-cu').read().decode('utf-8')
                    self.assertIn('<html lang="vi"', vi)
                    r = open_owner(u + '/cong-cu?lang=en')
                    en = r.read().decode('utf-8')
                    self.assertIn('<html lang="en"', en)
                    self.assertIn('lang=en', r.headers.get('Set-Cookie', ''))
                    self.assertNotEqual(vi, en)
                    rq = urllib.request.Request(u + '/api/tin-tuc', headers={'Cookie': 'lang=en'})
                    json.loads(open_owner(rq).read())                                  # JSON vẫn hợp lệ sau khi dịch
                finally:
                    srv.shutdown()
                    srv.server_close()
                    trang.MIEN_TRU = trang.MIEN_TRU_GOC                   # máy chủ đổi câu miễn trừ theo cấu hình: trả lại cho bài khác
        finally:
            dich.tu_dien = goc


if __name__ == '__main__':
    unittest.main()
