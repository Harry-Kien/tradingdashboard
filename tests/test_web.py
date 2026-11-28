"""Bài kiểm cho webapp cục bộ: dựng máy chủ trên cổng trống với sổ giả rồi gọi thật qua HTTP."""
import inspect
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from so_cong_khai import tai_khoan_chart, threads, tong_hop, web  # noqa: E402
from test_so import SoTest  # noqa: E402


class WebTest(SoTest):
    def setUp(self):
        super().setUp()
        self.cfg['threads'] = {'thu_muc': str(self.d / 'TA'), 'kenh': 'harry', 'tai_khoan': 'tk_thu', 'ngon_ngu': 'en'}
        threads.tao_ban_nhap(self.cfg, 'tuan', *tong_hop.tuan_theo_ma('2026-W47'), self.d / 'out' / 'threads',
                             tong_hop.tuan_theo_ma('2026-W47')[0])
        self.cfgp = self.d / 'c.json'
        self.cfgp.write_text(json.dumps(self.cfg), encoding='utf-8')
        _, token = tai_khoan_chart.vao('owner_web_test', 'test-web-owner-password-1234', True, self.d)
        self.cookie = tai_khoan_chart.cookie_header(token).split(';', 1)[0]
        self.srv = web.tao_may_chu(str(self.cfgp), port=0)
        self.url = f'http://127.0.0.1:{self.srv.server_address[1]}'
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        super().tearDown()

    def _get(self, path):
        with self._open(path) as r:
            return r.status, r.headers.get('Content-Type'), r.read()

    def _open(self, path):
        req = urllib.request.Request(self.url + path, headers={'Cookie': self.cookie})
        return urllib.request.urlopen(req, timeout=10)

    def test_luong_gia_day_tick_ngay(self):
        that, x = web.song.tick, {'ms': 1, 'bid': 3801.5, 'ask': 3801.67, 'nen': [1795537800, 3800.0, 3803.0, 3799.0, 3801.5]}
        web.song.tick = lambda g, tf, ma=None: dict(x)
        try:
            with self._open('/api/song?tf=M5') as r:
                self.assertEqual(r.headers.get('Content-Type'), 'text/event-stream; charset=utf-8')
                self.assertEqual(r.readline(), b'retry: 1000\n')
                r.readline()
                line = r.readline()
            self.assertTrue(line.startswith(b'data: '))
            self.assertEqual(json.loads(line[6:]), x)
            with self.assertRaises(urllib.error.HTTPError) as e:
                self._get('/api/song?tf=M7')
            self.assertEqual(e.exception.code, 400)
        finally:
            web.song.tick = that

    def test_api_cot_khi_chua_bat_khong_goi_mang(self):
        code, kind, body = self._get('/api/cot')
        self.assertEqual((code, kind), (200, 'application/json; charset=utf-8'))
        self.assertEqual(json.loads(body), {'bat': False})                         # cấu hình thử không bật COT

    def test_phong_chu_phuc_vu_tu_may(self):
        code, kind, body = self._get('/tinh/phong/be-vietnam-pro-400-vietnamese.woff2')
        self.assertEqual((code, kind), (200, 'font/woff2'))
        self.assertEqual(body[:4], b'wOF2')
        for xau in ('/tinh/phong/khong-co.woff2', '/tinh/phong/phong.json', '/tinh/phong/..%2F..%2Fcau-hinh.json'):
            with self.assertRaises(urllib.error.HTTPError) as e:              # chỉ đúng các tệp phông đã biết tên mới được trả
                self._get(xau)
            self.assertEqual(e.exception.code, 404)
        html = self._get('/')[2].decode('utf-8')
        self.assertIn('@font-face', html)
        self.assertIn('url(/tinh/phong/be-vietnam-pro-400-vietnamese.woff2)', html)
        self.assertNotIn('fonts.googleapis', html)                           # trang không gọi ra mạng để lấy phông
        self.assertNotIn('fonts.gstatic', html)

    def test_so_cong_khai(self):
        code, kind, body = self._get('/so-cong-khai')
        html = body.decode('utf-8')
        self.assertEqual((code, kind), (200, 'text/html; charset=utf-8'))
        for must in ('Sổ công khai', 'id="theme"', 'id="refresh"', 'tự tải lại mỗi 2 phút', 'Dữ liệu đọc tới', 'href="#tk-1"', 'href="#bot"',
                     ':root[data-theme="dark"]', 'id="hien-tai"', 'Lệnh đang mở (', 'Cảnh báo gần đây (', 'href="/kien-thuc"'):
            self.assertIn(must, html)
        for khong in ('id="tuan"', 'Bản nháp bài Threads', 'href="#tuan"'):   # khối Tuần này đã bỏ (26/11/2026)
            self.assertNotIn(khong, html)

    def test_trang_tinh_khong_co_nut_lam_moi(self):
        self._get('/so-cong-khai')
        tinh = (self.d / 'out' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('id="refresh"', tinh)
        self.assertIn('id="theme"', tinh)

    def test_doc_lai_so_moi_lan_tai(self):
        self.assertIn('gọi 5 lệnh', self._get('/so-cong-khai')[2].decode('utf-8').replace('Lệnh đã gọi</span><b>5', 'gọi 5 lệnh'))
        (self.d / 'bot.db').unlink()                                   # sổ biến mất giữa chừng: trang vẫn lên và nói rõ
        html = self._get('/so-cong-khai')[2].decode('utf-8')
        self.assertIn('Không đọc được sổ', html)

    def test_api_va_anh(self):
        code, kind, body = self._get('/api/so.json')
        self.assertEqual((code, kind), (200, 'application/json; charset=utf-8'))
        self.assertIn('tat_ca', json.loads(body))
        code, kind, body = self._get('/threads/harry-botlog-tuan-2026w47.image.png')
        self.assertEqual((code, kind, body[:4]), (200, 'image/png', b'\x89PNG'))

    def test_khong_cho_di_ra_ngoai_thu_muc(self):
        for bad in ('/threads/../so-cong-khai.json', '/threads/..%2F..%2Fc.json', '/threads/harry-botlog-tuan-2026w47.draft.json',
                    '/c.json', '/threads/'):
            with self.assertRaises(urllib.error.HTTPError) as e:
                self._get(bad)
            self.assertEqual(e.exception.code, 404, bad)

    def test_chi_nghe_o_may_nay(self):
        self.assertEqual(self.srv.server_address[0], '127.0.0.1')

    def test_api_app_doc_duoc(self):
        code, kind, body = self._get('/api/app')
        self.assertEqual((code, kind), (200, 'application/json; charset=utf-8'))
        j = json.loads(body)
        self.assertIn('phien_ban', j)
        self.assertIn('cap_nhat', j)

    def test_api_app_ghi_can_cung_may(self):
        def gui(tieu_de):
            rq = urllib.request.Request(self.url + '/api/app', data=json.dumps({'viec': 'xoa_het'}).encode('utf-8'), method='POST',
                                        headers={'Content-Type': 'application/json', 'Cookie': self.cookie, **tieu_de})
            try:
                with urllib.request.urlopen(rq, timeout=10) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                with e:
                    return e.code, json.loads(e.read() or b'{}')
        for td in ({}, {'X-So-Cong-Khai': '1', 'Origin': 'https://evil.example'}):
            self.assertEqual(gui(td)[0], 403, td)
        # đối chứng: đúng tiêu đề thì tới được vo_app.lam (việc lạ nên 400, không làm gì)
        self.assertEqual(gui({'X-So-Cong-Khai': '1'}), (400, {'loi': 'Việc không hỗ trợ.'}))


class KhoiDongTest(unittest.TestCase):
    def test_khoi_dong_khong_dung_stdout(self):
        """Kiểm tĩnh (rang-buoc R2): gọi thật web.khoi_dong là bật vòng Telegram đăng lên kênh công khai, nên bài kiểm không bao giờ gọi nó."""
        s = inspect.getsource(web.khoi_dong)
        for cam in ('sys.stdout', 'print(', 'giu_thuc'):
            self.assertNotIn(cam, s)
        self.assertIn('khoi_dong(', inspect.getsource(web.main))


if __name__ == '__main__':
    unittest.main()
