"""Kiểm hồi quy review: HTTP thật, tệp tạm, không gọi MT5/AI/Telegram."""
import csv
import http.client
import io
import json
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from so_cong_khai import ai_chi_bao, ai_hoi, bao_mat_http, gia_su, hieu_suat, sao_luu, tin_tuc, web


class HttpReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.cfg = Path(cls.tmp.name) / 'cfg.json'
        cls.cfg.write_text(json.dumps({'gia': {'mt5': {'bat': False}}, 'ai': {'bat': False}}), encoding='utf-8')
        cls.srv = web.tao_may_chu(str(cls.cfg), port=0)
        cls.port = cls.srv.server_port
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.thread.join()
        cls.tmp.cleanup()

    def post(self, body=b'{}', headers=None, path='/api/cai-dat', raw_headers=None):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=2)
        try:
            c.putrequest('POST', path, skip_host=True)
            h = {'Host': f'127.0.0.1:{self.port}', 'X-So-Cong-Khai': '1', 'Content-Length': str(len(body)), **(headers or {})}
            for k, v in h.items():
                c.putheader(k, v)
            for k, v in raw_headers or []:
                c.putheader(k, v)
            c.endheaders(body)
            r = c.getresponse()
            return r.status, r.read()
        finally:
            c.close()

    def test_json_sai_tra_400(self):
        for body in (b'[]', b'null', b'1', b'"x"', b'{', b'\xff', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}', b'[' * 1500):
            with self.subTest(body=body[:30]):
                self.assertEqual(self.post(body)[0], 400)

    def test_do_dai_sai_khong_treo(self):
        for n in ('-1', 'abc', '1.5'):
            with self.subTest(n=n):
                self.assertEqual(self.post(headers={'Content-Length': n})[0], 400)
        self.assertEqual(self.post(headers={'Content-Length': '8193'})[0], 413)

    def test_than_thieu_het_han_tra_408(self):
        with mock.patch.object(bao_mat_http, 'HAN_DOC', 0.1):
            self.assertEqual(self.post(headers={'Content-Length': '30'})[0], 408)

    def test_id_tai_khoan_sai_khong_gay_500(self):
        for ident in (None, [], {}, True, -1, 'x'):
            with self.subTest(ident=ident):
                body = json.dumps({'viec': 'xoa', 'id': ident}).encode()
                self.assertEqual(self.post(body, path='/api/cac-tai-khoan')[0], 400)

    def test_khong_chap_nhan_than_cat_cut(self):
        c = socket.create_connection(('127.0.0.1', self.port), timeout=2)
        try:
            c.sendall(f'POST /api/cai-dat HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\nX-So-Cong-Khai: 1\r\nContent-Length: 30\r\n\r\n{{}}'.encode())
            c.shutdown(socket.SHUT_WR)
            self.assertIn(b' 400 ', c.recv(4096).split(b'\r\n')[0])
        finally:
            c.close()

    def test_header_mo_ho_bi_chan(self):
        self.assertEqual(self.post(raw_headers=[('Content-Length', '2')])[0], 400)
        self.assertEqual(self.post(headers={'Transfer-Encoding': 'chunked'})[0], 400)
        self.assertEqual(self.post(raw_headers=[('Host', 'evil.example')])[0], 403)

    def test_origin_khac_cong_va_sai_dinh_dang_bi_chan(self):
        for origin in ('http://127.0.0.1:1', f'https://127.0.0.1:{self.port}', 'http://[', 'null',
                       f'http://user@127.0.0.1:{self.port}', f'http://127.0.0.1:{self.port}/fake'):
            with self.subTest(origin=origin):
                self.assertEqual(self.post(headers={'Origin': origin})[0], 403)
        self.assertEqual(self.post(headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)

    def test_ghi_hop_le_van_hoat_dong(self):
        body = json.dumps({'viec': 'luu', 'gia_tri': {'tin_tuc.bat': False}}).encode()
        status, _ = self.post(body, {'Origin': f'http://127.0.0.1:{self.port}'})
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(self.cfg.read_text(encoding='utf-8'))['tin_tuc']['bat'])


class DuLieuReview(unittest.TestCase):
    def test_ai_khong_nhan_dong_thoi_giu_han_muc(self):
        # Giả lập một lượt mạng đang xử lý, mọi cửa vào dùng chung chốt hạn mức.
        with ai_hoi._luot_hoi:
            for fn, args in ((ai_hoi.hoi, ({}, Path('.'))),
                             (ai_chi_bao.hoi, ({}, Path('.'), {})),
                             (gia_su.hoi, ({}, Path('.'), None, 'rui_ro', 'test'))):
                with self.subTest(fn=fn.__module__):
                    self.assertFalse(fn(*args)['ok'])
        self.assertFalse(ai_hoi._luot_hoi.locked())

    def test_ai_chi_bao_sai_kieu_duoc_tu_choi(self):
        for body in ({'tf': 'M15', 'chi_bao': {}, 'nen': []},
                     {'tf': 'M15', 'chi_bao': [{'gia_tri': []}], 'nen': []},
                     {'tf': 'M15', 'chi_bao': [{'tham_so': 'x'}], 'nen': []},
                     {'tf': 'M15', 'chi_bao': [{'dau': {}}], 'nen': []},
                     {'tf': 'M15', 'chi_bao': [{'ten': 'x'}], 'nen': [[1e100, 1, 2, 0, 1]] * 20}):
            with self.subTest(body=body):
                self.assertFalse(ai_chi_bao.hoi({}, Path('.'), body)['ok'])

    def test_csv_chan_cong_thuc_nhung_giu_so_am(self):
        for chu in ('=1+1', '+SUM(1,2)', '-cmd', '@SUM(1)', '\t=1', '\r=1', '\n=1', '  =1'):
            with self.subTest(chu=chu):
                s = hieu_suat.csv_lenh([{'ma': chu, 'rong': -12.5}])
                rows = list(csv.reader(io.StringIO(s.lstrip('\ufeff'))))
                self.assertTrue(rows[1][1].startswith("'"))
                self.assertEqual(rows[1][12], '-12.5')

    def test_rss_thuc_the_bi_chan_ke_ca_utf16_va_prolog_dai(self):
        xml = '<!DOCTYPE rss [<!ENTITY x "secret">]><rss><item><title>&x;</title></item></rss>'
        for body in (xml.encode('utf-16'), ('<!--' + ' ' * 21000 + '-->' + xml).encode()):
            with self.subTest(prefix=body[:10]):
                with self.assertRaises(ValueError):
                    tin_tuc._phan_tich_xml(body)

    def test_sao_luu_bo_thu_muc_khoa_va_lien_ket_ngoai(self):
        with tempfile.TemporaryDirectory() as d:
            goc = Path(d) / 'du-an'
            for ten in ('.SeCrEtS/data.txt', 'Credentials/data.txt', '.env.local/data.txt', 'du-lieu/api-token.txt', 'ok.txt'):
                p = goc / ten
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('test', encoding='utf-8')
            self.assertEqual([p.relative_to(goc).as_posix() for p in sao_luu.danh_sach_tep(goc)], ['ok.txt'])


if __name__ == '__main__':
    unittest.main()
