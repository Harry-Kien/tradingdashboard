"""Tóm tắt nhiều nguồn giữ đúng đơn vị, không ghi báo cáo hoặc tiết lộ cấu hình."""
import json
from functools import partial
from http_owner import owner_cookie, owner_urlopen
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from so_cong_khai import tong_quan_so, web
import test_so as fixtures


class TongQuanSoTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.SoTest()
        self.fixture.setUp()
        self.cfg = self.fixture.cfg

    def tearDown(self):
        self.fixture.tearDown()

    def test_giu_rieng_demo_tp1_ty_le_thang_va_r(self):
        before = {p.name: p.read_bytes() for p in self.fixture.d.iterdir() if p.is_file()}
        result = tong_quan_so.doc(self.cfg)
        rows = {r['id']: r for r in result['so']}
        self.assertEqual(set(rows), {'tk-1', 'tk-2', 'bot', 'xu-huong', 'dinh-day'})
        self.assertEqual(rows['tk-1']['don_vi'], 'USD')
        self.assertEqual(rows['tk-1']['gia_tri'], 160)
        self.assertEqual(rows['tk-1']['mo'], 1)  # chỉ nhãn mở THEO SỔ, không coi là xác minh MT5
        self.assertTrue(rows['tk-1']['thieu'])
        self.assertEqual(rows['bot']['don_vi'], 'TP1')
        self.assertEqual(rows['bot']['gia_tri'], 3)
        self.assertEqual(rows['xu-huong']['don_vi'], 'win')
        self.assertEqual(rows['dinh-day']['don_vi'], 'R')
        self.assertEqual(rows['dinh-day']['gia_tri'], -1.02)
        self.assertEqual(result['nguon'], 'journal')
        self.assertEqual(result['pham_vi'], 'all')
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.fixture.d.iterdir() if p.is_file()})
        json.dumps(result, allow_nan=False)

    def test_nguon_hong_khong_lam_mat_nguon_khac_hay_lo_duong_dan(self):
        (self.fixture.d / 'bot.db').unlink()
        result = tong_quan_so.doc(self.cfg)
        self.assertEqual(len(result['so']), 4)
        self.assertEqual(result['loi'], ['Bot tín hiệu vàng'])
        self.assertNotIn(str(self.fixture.d), json.dumps(result))

    def test_chua_khai_so_khong_tao_du_lieu_gia(self):
        result = tong_quan_so.doc({})
        self.assertEqual(result['so'], [])
        self.assertEqual(result['loi'], [])

    def test_thieu_mau_khong_bao_ty_le_0_phan_tram(self):
        empty = {'loi': [], 'bot': {'decided': 0, 'tp1': 0, 'rows': [], 'closed': 0},
                 'xu_huong': {'n': 0, 'closed': 0, 'win': 0, 'rows': []}}
        with patch('so_cong_khai.__main__.gom', return_value=empty):
            result = tong_quan_so.doc({})
        self.assertTrue(all(row['pct'] is None for row in result['so']))

    def test_gon_duong_bieu_do_giu_hai_dau_va_cuc_tri(self):
        values = [100.0] * 1000
        values[500], values[501], values[-1] = -5000, 9000, 234
        curve = [(None, v) for v in values]
        result = tong_quan_so._tia(curve)
        self.assertLessEqual(len(result), 50)
        self.assertEqual((result[0], result[-1]), (100, 234))
        self.assertIn(-5000, result)
        self.assertIn(9000, result)

    def test_api_chi_doc_khong_goi_xay_va_khong_xuat_tep(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'c.json'
            config.write_text(json.dumps(self.cfg), encoding='utf-8')
            server = web.tao_may_chu(str(config), port=0)
            owner_cookie(config.parent)
            open_owner = partial(owner_urlopen, root=config.parent)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                with patch.object(web, 'xay', side_effect=AssertionError('Không ghi báo cáo')):
                    with open_owner(f'http://127.0.0.1:{server.server_port}/api/tong-quan/so', timeout=5) as response:
                        result = json.load(response)
                        self.assertEqual(response.status, 200)
                        self.assertEqual(len(result['so']), 5)
                        self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ['c.json', 'du-lieu'])
                self.assertFalse((self.fixture.d / 'out').exists())
            finally:
                server.shutdown()
                server.server_close()


if __name__ == '__main__':
    unittest.main()
