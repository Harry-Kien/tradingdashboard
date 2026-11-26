"""Bài kiểm cho trang Cài đặt: kiểm dữ liệu từng mục, ghi an toàn (sai một mục là không ghi gì, có bản .bak), nối lại MT5 khi đổi phần
kết nối, và máy chủ chỉ nhận lệnh ghi từ chính máy này (tiêu đề riêng, Host, Origin). Không nối MT5 thật."""
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import cai_dat, song, web  # noqa: E402


class KiemTest(unittest.TestCase):
    def test_hop_le(self):
        self.assertIs(cai_dat.kiem('gia.mt5.chi_demo', False), False)
        self.assertEqual(cai_dat.kiem('gia.ma_vang', 'XAUUSD.r'), 'XAUUSD.r')
        self.assertIsNone(cai_dat.kiem('gia.mt5.lech_gio_san', None))
        self.assertEqual(cai_dat.kiem('gia.mt5.lech_gio_san', 2), 2)
        self.assertEqual(cai_dat.kiem('gia.mt5.lech_gio_san', 5.5), 5.5)
        self.assertEqual(cai_dat.kiem('thi_truong.chu_ky_giay', 0.1), 0.1)
        self.assertEqual(cai_dat.kiem('gia.mt5.terminal', ''), '')
        self.assertEqual(cai_dat.kiem('hoc.hoa_hong_lot', 7), 7.0)
        self.assertEqual(cai_dat.kiem('hoc.hoa_hong_lot', 0), 0.0)
        self.assertEqual(cai_dat.kiem('gia.spread', 0.25), 0.25)

    def test_tu_choi(self):
        sai = [('khong_co', 1), ('ten', 'Tên mới'), ('gia.mt5.chi_demo', 'false'), ('gia.ma_vang', 'XAU USD'),
               ('gia.mt5.lech_gio_san', 2.3), ('gia.mt5.lech_gio_san', 20), ('gia.mt5.lech_gio_san', True), ('thi_truong.chu_ky_giay', 0.001),
               ('hoc.hoa_hong_lot', -1), ('hoc.hoa_hong_lot', 500), ('hoc.hoa_hong_lot', '7'), ('gia.spread', -0.1), ('gia.spread', 9),
               ('gia.mt5.terminal', r'C:\Windows\notepad.exe'), ('gia.mt5.terminal', r'X:\khong-co\terminal64.exe')]
        for k, v in sai:
            with self.assertRaises(ValueError, msg=f'{k}={v!r}'):
                cai_dat.kiem(k, v)

    def test_duong_mt5_that(self):
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / 'terminal64.exe'
            f.write_bytes(b'')
            self.assertEqual(cai_dat.kiem('gia.mt5.terminal', f'"{f}"'), str(f))


class GhiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name) / 'cau-hinh.json'
        self.goc = {'ten': 'Cũ', 'gia': {'ma_nguon': [], 'mt5': {'bat': True, 'terminal': '', 'chi_demo': True}}, 'khac': {'giu': 1}}
        self.p.write_text(json.dumps(self.goc, ensure_ascii=False, indent=2), encoding='utf-8')
        self.ngat, self.cu = [], song.ngat
        song.ngat = lambda: self.ngat.append(1)

    def tearDown(self):
        song.ngat = self.cu
        self.tmp.cleanup()

    def test_ghi_va_sao_luu(self):
        kq = cai_dat.ghi(self.p, {'ten': 'Mới', 'tin_tuc.bat': False})                  # tên thương hiệu cố định: gửi lên thì bỏ qua
        self.assertEqual((kq['doi'], kq['noi_lai']), (['tin_tuc.bat'], False))
        moi = json.loads(self.p.read_text(encoding='utf-8'))
        self.assertEqual((moi['ten'], moi['tin_tuc'], moi['khac']), ('Cũ', {'bat': False}, {'giu': 1}))     # mục khác giữ nguyên
        self.assertEqual(json.loads((self.p.parent / 'cau-hinh.json.bak').read_text(encoding='utf-8')), self.goc)
        self.assertEqual(self.ngat, [])

    def test_sai_mot_muc_thi_khong_ghi_gi(self):
        truoc = self.p.read_text(encoding='utf-8')
        with self.assertRaises(ValueError):
            cai_dat.ghi(self.p, {'tin_tuc.bat': False, 'gia.mt5.lech_gio_san': 99})
        self.assertEqual(self.p.read_text(encoding='utf-8'), truoc)
        self.assertFalse((self.p.parent / 'cau-hinh.json.bak').exists())

    def test_doi_phan_mt5_thi_noi_lai(self):
        kq = cai_dat.ghi(self.p, {'gia.mt5.chi_demo': False, 'gia.mt5.lech_gio_san': 3})
        self.assertTrue(kq['noi_lai'])
        self.assertEqual(self.ngat, [1])
        self.assertEqual(json.loads(self.p.read_text(encoding='utf-8'))['gia']['mt5'], {'bat': True, 'terminal': '', 'chi_demo': False, 'lech_gio_san': 3})

    def test_khong_doi_gi(self):
        self.assertEqual(cai_dat.ghi(self.p, {'ten': 'Khác hẳn'})['doi'], [])
        self.assertEqual(json.loads(self.p.read_text(encoding='utf-8'))['ten'], 'Cũ')
        self.assertFalse((self.p.parent / 'cau-hinh.json.bak').exists())


class MayChuTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name) / 'cau-hinh.json'
        self.p.write_text(json.dumps({'ten': 'Cũ', 'gia': {'ma_nguon': [], 'mt5': {'bat': False}}}), encoding='utf-8')
        self.srv = web.tao_may_chu(str(self.p), port=0)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.port = self.srv.server_address[1]

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()

    def _post(self, tieu_de):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=30)
        body = json.dumps({'viec': 'luu', 'gia_tri': {'tin_tuc.bat': False}})
        c.request('POST', '/api/cai-dat', body, {'Content-Type': 'application/json', **tieu_de})
        r = c.getresponse()
        return r.status, json.loads(r.read() or b'{}')

    def test_chi_nhan_tu_chinh_may(self):
        for td in ({}, {'X-So-Cong-Khai': '1', 'Host': 'evil.example:8765'}, {'X-So-Cong-Khai': '1', 'Origin': 'https://evil.example'}):
            self.assertEqual(self._post(td)[0], 403, td)
        self.assertNotIn('tin_tuc', json.loads(self.p.read_text(encoding='utf-8')))
        ma, j = self._post({'X-So-Cong-Khai': '1', 'Origin': f'http://127.0.0.1:{self.port}'})
        self.assertEqual((ma, j['doi']), (200, ['tin_tuc.bat']))
        self.assertEqual(json.loads(self.p.read_text(encoding='utf-8'))['tin_tuc'], {'bat': False})

    def test_doc_va_trang(self):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=30)
        c.request('GET', '/api/cai-dat')
        j = json.loads(c.getresponse().read())
        self.assertNotIn('ten', j['gia_tri'])
        self.assertIn('gia.mt5.terminal', j['gia_tri'])
        self.assertIn('ket_noi', j)
        c.request('GET', '/cai-dat')
        self.assertIn('id="cd"', c.getresponse().read().decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
