"""HTTP thật: khách, tài khoản khác và phiên cũ không đọc kho MT5 của chủ."""
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from so_cong_khai import tai_khoan_chart as auth, web


class IsolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.cfg = cls.root / 'config.json'
        cls.cfg.write_text('{"gia":{},"tai_khoan":[]}', encoding='utf-8')
        cls.owner, token = auth.vao('owner-test', 'long-password-1234', True, cls.root)
        cls.owner_cookie = auth.cookie_header(token).split(';')[0]
        cls.reader, token = auth.vao('reader-test', 'long-password-1234', True, cls.root)
        cls.reader_cookie = auth.cookie_header(token).split(';')[0]
        cls.srv = web.tao_may_chu(str(cls.cfg), port=0)
        cls.url = 'http://127.0.0.1:' + str(cls.srv.server_port)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.tmp.cleanup()

    def request(self, path, cookie='', body=None, extra=None):
        headers = {'Cookie': cookie, **(extra or {})}
        if body is not None:
            headers.update({'X-So-Cong-Khai': '1', 'Content-Type': 'application/json'})
        req = urllib.request.Request(self.url + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        try:
            response = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as e:
            response = e
        with response:
            return response.status, response.headers, response.read()

    def test_private_routes_deny_before_readers(self):
        routes = ['/api/tai-khoan', '/api/tong-quan/so', '/api/thi-truong', '/api/gia', '/api/song',
                  '/api/thi-truong/luong', '/api/hieu-suat', '/api/hieu-suat.csv', '/api/so.json',
                  '/api/canh-bao', '/api/giam-sat', '/api/cai-dat', '/api/cac-tai-khoan', '/api/app',
                  '/api/vi-the', '/api/nhat-ky', '/api/phieu', '/api/telegram', '/api/sao-luu',
                  '/api/ai-giai-thich', '/api/private-added-in-future', '/threads/private.json', '/telegram/anh/private.png']
        with patch.object(web.tai_khoan, 'doc', side_effect=AssertionError('private reader called')), patch.object(web, 'xay', side_effect=AssertionError('report generated')):
            for cookie, expected in [('', 401), (self.reader_cookie, 403)]:
                for path in routes:
                    with self.subTest(cookie=bool(cookie), path=path):
                        code, headers, body = self.request(path + '?uid=' + self.owner['id'], cookie)
                        self.assertEqual(code, expected)
                        self.assertEqual(headers['Cache-Control'], 'no-store')
                        self.assertNotIn(b'owner-test', body)
                        self.assertNotIn(str(self.root).encode(), body)
            for path in ('/api/app', '/api/phieu', '/api/cac-tai-khoan', '/api/telegram', '/api/sao-luu', '/api/ai-giai-thich'):
                self.assertEqual(self.request(path, self.reader_cookie, {'uid': self.owner['id']})[0], 403)
                self.assertEqual(self.request(path, '', {})[0], 401)

    def test_owner_and_forged_identity(self):
        with patch.object(web.tai_khoan, 'doc', return_value={'san_sang': True, 'von': 1234.56}) as read:
            code, _, body = self.request('/api/tai-khoan', self.owner_cookie)
            self.assertEqual(code, 200)
            self.assertEqual(json.loads(body)['von'], 1234.56)
            read.assert_called_once()
            self.assertEqual(self.request('/api/tai-khoan', self.owner_cookie, extra={'X-Chart-Owner': self.reader['id']})[0], 409)
            self.assertEqual(self.request('/api/tai-khoan', self.reader_cookie, extra={'X-Chart-Owner': self.owner['id']})[0], 403)
            self.assertEqual(self.request('/api/%74ai-khoan', self.reader_cookie)[0], 403)

    def test_scoped_chart_data_and_context(self):
        for cookie, user in [(self.owner_cookie, self.owner), (self.reader_cookie, self.reader)]:
            code, _, body = self.request('/api/khong-gian', cookie)
            self.assertEqual(code, 200)
            self.assertEqual(json.loads(body)['nguoi']['id'], user['id'])
            self.assertNotIn('hash', json.loads(body)['nguoi'])
            self.assertEqual(self.request('/api/hinh-ve?ma=EURUSD', cookie, extra={'X-Chart-Owner': user['id']})[0], 200)
        self.assertIsNone(json.loads(self.request('/api/khong-gian')[2])['nguoi'])

    def test_logout_expired_and_broken_store(self):
        user, token = auth.vao('expiry-test', 'long-password-1234', True, self.root, now=1)
        self.assertEqual(self.request('/api/tai-khoan', auth.cookie_header(token).split(';')[0])[0], 401)
        user, token = auth.vao('logout-test', 'long-password-1234', True, self.root)
        cookie = auth.cookie_header(token).split(';')[0]
        self.assertEqual(self.request('/api/tai-khoan-chart', cookie, {'viec': 'dang_xuat'})[0], 200)
        self.assertIsNone(json.loads(self.request('/api/khong-gian', cookie)[2])['nguoi'])
        store = auth._tep(self.root)
        original = store.read_bytes()
        try:
            store.write_text('{broken', encoding='utf-8')
            self.assertEqual(self.request('/api/tai-khoan')[0], 503)
            self.assertEqual(self.request('/')[0], 503)
        finally:
            store.write_bytes(original)

    def test_login_gate_no_embedded_owner_data(self):
        for cookie in ('', self.reader_cookie):
            for path in ('/', '/so-cong-khai', '/tai-khoan', '/cai-dat'):
                code, _, body = self.request(path, cookie)
                self.assertEqual(code, 200)
                self.assertIn(b'id="entry"', body)
                self.assertNotIn(b'data-money', body)
                self.assertNotIn(self.owner['id'].encode(), body)

    def test_loopback_and_proxy_boundary(self):
        with self.assertRaises(ValueError):
            web.tao_may_chu(str(self.cfg), host='0.0.0.0', port=0)
        for key in ('Forwarded', 'X-Forwarded-For', 'X-Forwarded-Host', 'X-Forwarded-Proto'):
            self.assertEqual(self.request('/api/tai-khoan', self.owner_cookie, extra={key: 'public.example'})[0], 403)

    def test_background_snapshot_session_is_short_and_revoked(self):
        with auth.phien_noi_bo(self.root) as token:
            cookie = auth.cookie_header(token).split(';')[0]
            self.assertEqual(auth.hien_tai(cookie, self.root)['id'], self.owner['id'])
            self.assertIsNone(auth.hien_tai(cookie, self.root, now=10**12))
        self.assertIsNone(auth.hien_tai(cookie, self.root))

    def test_fresh_install_requires_owner_before_reading_mt5(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / 'config.json'
            config.write_text('{"gia":{}}')
            server = web.tao_may_chu(str(config), port=0)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                url = f'http://127.0.0.1:{server.server_port}'
                with patch.object(web.tai_khoan, 'doc', side_effect=AssertionError('MT5 accessed before account setup')):
                    with self.assertRaises(urllib.error.HTTPError) as error:
                        urllib.request.urlopen(url + '/api/tai-khoan', timeout=5)
                    self.assertEqual(error.exception.code, 401)
                    with urllib.request.urlopen(url + '/', timeout=5) as response:
                        self.assertIn('Tạo tài khoản chủ', response.read().decode())
                self.assertEqual(list(Path(temp).iterdir()), [config])
            finally:
                server.shutdown()
                server.server_close()


if __name__ == '__main__':
    unittest.main()
