"""Bài kiểm cho phần kiểm chứng lịch sử: số tóm tắt đúng, kết quả được nhớ lại, và chạy được trên mã thật của dự án."""
from functools import partial
from http_owner import owner_urlopen
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from so_cong_khai import bieu_do, gia, kiem_chung, song, web  # noqa: E402
from test_gia import MA_THAT, _kho  # noqa: E402


def _l(huong, usd, tp_dat=None, ket='SL', t='2026-10-01T00:00:00+00:00'):
    x = {'t': t, 'ra': t, 'huong': huong, 'vao': 3800.0, 'usd': usd, 'ket': ket}
    if tp_dat is not None:
        x['tp_dat'] = tp_dat
    return x


class TomTest(unittest.TestCase):
    def test_so_do(self):
        ls = [_l('MUA', 10.0, 2, 'TP6'), _l('BAN', -20.0, 0), _l('BAN', -5.0, 1), _l('BAN', 4.0, 1, 'TIME'), _l('MUA', -20.0, 0)]
        s = kiem_chung.tom(ls)
        self.assertEqual((s['n'], s['thang'], s['ty_le'], s['tong'], s['usd_tb']), (5, 2, 40.0, -31.0, -6.2))
        self.assertEqual((s['tp1'], s['tp2'], s['sl_tron'], s['chuoi_thua']), (60.0, 20.0, 40.0, 2))
        self.assertEqual(s['pf'], round(14 / 45, 2))
        self.assertEqual([x['usd'] for x in s['gan_day']], [-20.0, 4.0, -5.0, -20.0, 10.0])     # mới nhất trước
        ban = kiem_chung.tom(ls, 'BAN')
        self.assertEqual((ban['n'], ban['thang'], ban['tong']), (3, 1, -21.0))
        self.assertEqual(kiem_chung.tom(ls, 'MUA')['n'] + ban['n'], s['n'])

    def test_khong_co_lenh_va_khong_co_cot_tp(self):
        self.assertEqual(kiem_chung.tom([]), {'n': 0})
        s = kiem_chung.tom([_l('MUA', 4.82, ket='TP'), _l('MUA', 4.82, ket='TP')])
        self.assertNotIn('tp1', s)
        self.assertIsNone(s['pf'])                                             # chưa có lệnh lỗ thì không có hệ số lợi nhuận


class KiemChungTest(unittest.TestCase):
    def setUp(self):
        # These tests exercise private-rule cache orchestration using a fake
        # calculation, independently of whether the author's rule folders exist.
        private_mode = patch.object(gia, 'ban_chia_se', return_value=False)
        private_mode.start()
        self.addCleanup(private_mode.stop)
        gia._nho.clear()
        song._tt.update(deps=None, mt5=None, fr=None, thu=0.0, luc=0.0)
        kiem_chung._tt.update(key=None, kq=None, dang=False, loi=None, bat_dau=None)
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.start = datetime(2026, 9, 7, tzinfo=timezone.utc)
        _kho(self.d, self.start, 75 * 1440)
        self.out = self.d / 'out'
        self.cfg = {'ten': 'Thử', 'thu_muc_ra': str(self.out), 'gia': {'kho_m1': str(self.d), 'ma_nguon': MA_THAT, 'so_thang': 4}}
        self.that = kiem_chung.chay

    def tearDown(self):
        kiem_chung.chay = self.that
        gia._nho.clear()
        self.tmp.cleanup()

    @unittest.skipUnless(all(os.path.isdir(p) for p in MA_THAT), 'không có mã của dự án trên máy này')
    def test_chay_tren_ma_that(self):
        kq = kiem_chung.chay(self.cfg)
        self.assertEqual(kq['loi'], [])
        self.assertEqual(set(kq['luat']), {'bot', 'ba_khung', 'dinh_day'})
        self.assertEqual(kq['so_ngay'], 75)
        self.assertFalse(kq['co_lich_tin'])
        for ma, r in kq['luat'].items():
            self.assertTrue(r['cach'], ma)
            self.assertEqual(r['MUA']['n'] + r['BAN']['n'], r['tat_ca']['n'], ma)
            self.assertEqual(len(r['diem']), r['tat_ca']['n'], ma)
            for t, d, vao, usd in r['diem']:
                self.assertIn(d, (1, -1))
                self.assertGreater(vao, 0)
                self.assertTrue(self.start.timestamp() <= t <= (self.start + timedelta(days=76)).timestamp())
        self.assertEqual(kq['luat']['ba_khung']['hoa_von'], 80.7)
        json.dumps(kq)

    def test_nho_ket_qua_trong_bo_nho_va_tren_dia(self):
        dem = []
        kiem_chung.chay = lambda cfg: dem.append(1) or {'luat': {}, 'loi': [], 'so_ngay': 75}
        a = kiem_chung.lay(self.cfg, self.out, cho=True)
        b = kiem_chung.lay(self.cfg, self.out)
        self.assertTrue(a['san_sang'] and b['san_sang'])
        self.assertEqual(len(dem), 1)
        self.assertTrue((self.out / 'kiem-chung.json').exists())
        kiem_chung._tt.update(key=None, kq=None)                               # như khi khởi động lại máy chủ
        c = kiem_chung.lay(self.cfg, self.out)
        self.assertTrue(c['san_sang'])
        self.assertEqual(len(dem), 1)                                          # đọc từ tệp, không tính lại

    def test_kho_nen_sang_ngay_moi_thi_tinh_lai(self):
        dem = []
        kiem_chung.chay = lambda cfg: dem.append(1) or {'luat': {}, 'loi': []}
        kiem_chung.lay(self.cfg, self.out, cho=True)
        _kho(self.d, self.start, 76 * 1440)
        gia._nho.clear()
        kiem_chung.lay(self.cfg, self.out, cho=True)
        self.assertEqual(len(dem), 2)

    def test_chay_nen_khong_chan_trang(self):
        mo = threading.Event()
        kiem_chung.chay = lambda cfg: mo.wait(10) and {'luat': {}, 'loi': []}
        a = kiem_chung.lay(self.cfg, self.out)
        b = kiem_chung.lay(self.cfg, self.out)                                 # gọi lần hai khi đang tính: không mở thêm luồng
        self.assertEqual((a['san_sang'], a['dang_tinh'], b['dang_tinh']), (False, True, True))
        mo.set()
        for _ in range(100):
            if kiem_chung.lay(self.cfg, self.out)['san_sang']:
                break
            time.sleep(0.05)
        self.assertTrue(kiem_chung.lay(self.cfg, self.out)['san_sang'])

    def test_loi_thi_bao_ro(self):
        def hong(cfg):
            raise RuntimeError('hỏng thử')
        kiem_chung.chay = hong
        r = kiem_chung.lay(self.cfg, self.out, cho=True)
        self.assertFalse(r['san_sang'])
        self.assertIn('hỏng thử', r['loi'][0])

    def test_qua_may_chu_va_trang(self):
        kiem_chung.chay = lambda cfg: {'luat': {}, 'loi': [], 'so_ngay': 75}
        kiem_chung.lay(self.cfg, self.out, cho=True)
        cfgp = self.d / 'c.json'
        cfgp.write_text(json.dumps(self.cfg), encoding='utf-8')
        srv = web.tao_may_chu(str(cfgp), port=0)
        open_owner = partial(owner_urlopen, root=cfgp.parent)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            with open_owner(f'http://127.0.0.1:{srv.server_address[1]}/api/kiem-chung', timeout=30) as r:
                j = json.loads(r.read())
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertTrue(j['san_sang'])
        html = bieu_do.trang_bieu_do('Thử')
        for must in ('/api/kiem-chung', 'Kiểm chứng', 'không phải kiểm ngoài mẫu', 'Mẫu nhỏ'):
            self.assertIn(must, html)
        src = Path(kiem_chung.__file__).read_text(encoding='utf-8')
        for banned in ('order_send', 'order_check', 'TRADE_ACTION', 'positions_get', 'MetaTrader5'):
            self.assertNotIn(banned, src)


if __name__ == '__main__':
    unittest.main()
