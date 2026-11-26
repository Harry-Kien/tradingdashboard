"""Bài kiểm bảo mật: mô phỏng các kiểu tấn công vào webapp chạy trên máy (127.0.0.1) từ một trang web độc hại mà người dùng lỡ mở.

- DNS rebinding: trang lạ trỏ tên miền của nó về 127.0.0.1 rồi đọc số liệu như cùng nguồn. Khi đó tiêu đề Host là tên miền lạ: mọi yêu cầu
  đọc lẫn ghi phải bị từ chối.
- Gửi hộ lệnh (CSRF): trang lạ gửi POST tới 127.0.0.1 để hỏi AI (tốn tiền), thêm tài khoản hay đổi cài đặt: phải bị từ chối.
- Nhúng khung để lừa bấm (clickjacking): mọi trang phải cấm bị nhúng.
Không nối MT5 thật, không gọi AI thật."""
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import web  # noqa: E402

DOC = ['/', '/bieu-do', '/api/tai-khoan', '/api/cac-tai-khoan', '/api/hieu-suat?ngay=30', '/api/cai-dat', '/api/gia?tf=M15', '/api/nhat-ky',
       '/api/song?tf=M15', '/api/thi-truong/luong']
GHI = [('/api/ai', {}), ('/api/cac-tai-khoan', {'viec': 'them', 'duong': r'C:\x\terminal64.exe'}), ('/api/cai-dat', {'viec': 'luu', 'gia_tri': {'tin_tuc.bat': False}})]


class BaoMatTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name) / 'cau-hinh.json'
        self.cfg = {'gia': {'ma_nguon': [], 'mt5': {'bat': False}}, 'ai': {'bat': False}}
        self.p.write_text(json.dumps(self.cfg), encoding='utf-8')
        self.srv = web.tao_may_chu(str(self.p), port=0)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.port = self.srv.server_address[1]

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()

    def _goi(self, phuong, duong, tieu_de=None, than=None):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=30)
        c.putrequest(phuong, duong, skip_host=True)
        for k, v in {'Host': f'127.0.0.1:{self.port}', **(tieu_de or {})}.items():
            c.putheader(k, v)
        b = json.dumps(than).encode() if than is not None else b''
        c.putheader('Content-Length', str(len(b)))
        c.endheaders(b)
        r = c.getresponse()
        return r.status, dict(r.getheaders()), r.read(200)

    def test_dns_rebinding_khong_doc_duoc(self):
        for duong in DOC:
            for host in ('evil.example', 'evil.example:%d' % self.port, '127.0.0.1.evil.example', 'localhost.evil.example:1'):
                ma, _, _ = self._goi('GET', duong, {'Host': host})
                self.assertEqual(ma, 403, f'{duong} Host={host}')

    def test_dia_chi_cua_may_van_mo_duoc(self):
        for host in (f'127.0.0.1:{self.port}', f'localhost:{self.port}', f'[::1]:{self.port}', 'localhost'):
            self.assertEqual(self._goi('GET', '/api/cai-dat', {'Host': host})[0], 200, host)

    def test_khong_gui_ho_lenh_ghi(self):
        for duong, than in GHI:
            for td in ({},                                                          # thiếu tiêu đề riêng (form của trang lạ)
                       {'X-So-Cong-Khai': '1', 'Host': 'evil.example:%d' % self.port},   # DNS rebinding
                       {'X-So-Cong-Khai': '1', 'Origin': 'https://evil.example'}):        # trang lạ gửi kèm tiêu đề (CORS chặn, vẫn kiểm)
                self.assertEqual(self._goi('POST', duong, td, than)[0], 403, f'{duong} {td}')
        self.assertEqual(json.loads(self.p.read_text(encoding='utf-8')), self.cfg)       # cấu hình không bị đổi

    def test_cam_nhung_khung_va_lo_dia_chi(self):
        for duong in ('/', '/bieu-do', '/cai-dat', '/api/cai-dat'):
            _, td, _ = self._goi('GET', duong)
            self.assertEqual(td.get('X-Frame-Options'), 'DENY', duong)
            self.assertIn("frame-ancestors 'none'", td.get('Content-Security-Policy', ''), duong)
            self.assertEqual(td.get('Referrer-Policy'), 'no-referrer', duong)
            self.assertEqual(td.get('X-Content-Type-Options'), 'nosniff', duong)


if __name__ == '__main__':
    unittest.main()
