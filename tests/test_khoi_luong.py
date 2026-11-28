# -*- coding: utf-8 -*-
"""Tick volume của MT5 cho chỉ báo Khối lượng đột biến: song.khoi_luong đọc nến đã đóng (chỉ đọc, có nhớ vài giây), da_ma.goi gắn mảng 'vol'
khớp từng nến. Dùng MT5 giả; không nối MT5 thật."""
from functools import partial
from http_owner import owner_urlopen
import json
import os
import sys
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from so_cong_khai import da_ma, song  # noqa: E402
from test_da_ma import HET, MT5Gia  # noqa: E402
from test_gia import MA_THAT  # noqa: E402


class MT5CoKhoiLuong(MT5Gia):
    def copy_rates_from_pos(self, ten, tf, vi_tri, n):
        r = super().copy_rates_from_pos(ten, tf, vi_tri, n)
        r['tick_volume'] = (r['time'] // 60) % 97 + 10
        return r


class KhoiLuong(unittest.TestCase):
    def setUp(self):
        self.cu = dict(song._tt)
        self.mt5 = MT5CoKhoiLuong()
        song._tt.update(mt5=self.mt5, sym='XAUUSDp', kl={})

    def tearDown(self):
        song._tt.clear()
        song._tt.update(self.cu)

    def test_doc_va_nho(self):
        kl = song.khoi_luong('M15', None, 50)
        self.assertEqual(len(kl), 50)
        t, v = max(kl.items())
        self.assertEqual(v, (t // 60) % 97 + 10)
        self.assertEqual(self.mt5.goi[-1][2:], (1, 50))                         # nến đã đóng (vị trí 1)
        song.khoi_luong('M15', None, 50)
        self.assertEqual(len(self.mt5.goi), 1)                                   # lần sau trong vài giây lấy từ bộ nhớ
        with self.assertRaises(ValueError):
            song.khoi_luong('M7')
        song._tt['mt5'] = None
        song._tt['kl'] = {}
        self.assertIsNone(song.khoi_luong('M15'))

    def test_doc_nhieu_nen_nho_lau_hon_va_tuyen_web(self):
        import tempfile
        import threading
        import urllib.request

        from so_cong_khai import web
        song.khoi_luong('H1', None, 5000)
        song.khoi_luong('H1', None, 300)                                         # ít nến hơn bản đã nhớ: lấy từ bộ nhớ
        self.assertEqual(len(self.mt5.goi), 1)
        that = song.khung_song
        song.khung_song = lambda g: {}                                           # coi như đang nối MT5 (MT5 giả ở trên)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                cfgp = Path(tmp) / 'c.json'
                cfgp.write_text(json.dumps({'ten': 'Thử', 'gia': {'ma_vang': 'XAUUSDp'}, 'thu_muc_ra': str(Path(tmp) / 'out')}), encoding='utf-8')
                srv = web.tao_may_chu(str(cfgp), port=0)
                open_owner = partial(owner_urlopen, root=cfgp.parent)
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                goc = f'http://127.0.0.1:{srv.server_address[1]}'
                with open_owner(goc + '/api/khoi-luong?tf=M15&n=999999') as r:
                    j = json.loads(r.read())
                self.assertEqual((len(j['t']), len(j['v']), j['ly_do']), (60000, 60000, None))   # chặn ở 60.000 nến
                self.assertEqual(j['t'], sorted(j['t']))
                self.assertEqual(j['v'][-1], (j['t'][-1] // 60) % 97 + 10)
                for xau in ('/api/khoi-luong?tf=M7', '/api/khoi-luong?tf=M15&ma=EUR%27%3B'):
                    with self.assertRaises(urllib.error.HTTPError) as e:
                        open_owner(goc + xau)
                    self.assertEqual(e.exception.code, 400)
                srv.shutdown()
        finally:
            song.khung_song = that

    def test_ma_nguon_chi_doc(self):
        src = Path(song.__file__).read_text(encoding='utf-8')
        for banned in ('order_send', 'order_check', 'TRADE_ACTION', 'positions_get'):
            self.assertNotIn(banned, src)

    @unittest.skipUnless(all(os.path.isdir(p) for p in MA_THAT), 'không có mã của dự án trên máy này')
    def test_bieu_do_ma_khac_co_vol(self):
        that = da_ma._mt5
        da_ma._mt5 = lambda g: self.mt5
        da_ma._nho.clear()
        try:
            d = da_ma.goi({'ten': 'Thử', 'gia': {'ma_nguon': MA_THAT, 'ma_vang': 'XAUUSDp'}}, 'EURUSDp', 'M15', 200, HET + timedelta(minutes=2))
        finally:
            da_ma._mt5 = that
            da_ma._nho.clear()
        v = json.loads(json.dumps(d))['vol']                                          # qua JSON: khóa là giờ mở nến dạng chữ
        self.assertEqual(len(v), len(d['candles']))
        self.assertTrue(all(v[str(c[0])] == (c[0] // 60) % 97 + 10 for c in d['candles']))


class CongCuDo(unittest.TestCase):
    def test_do_dung_dinh_nghia(self):
        import importlib.util

        import numpy as np
        import pandas as pd
        sp = importlib.util.spec_from_file_location('do_khoi_luong', Path(__file__).resolve().parent.parent / 'cong-cu' / 'do_khoi_luong.py')
        M = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(M)
        self.assertEqual((M.N_NEN, M.NGUONG, M.THAN, M.SAU), (20, 2.0, 0.5, 4))       # đúng như đã ghi trước, không đổi
        r = np.random.default_rng(3)
        n = 800
        c = 2000 + np.cumsum(r.normal(.2, 3, n))
        o = np.r_[c[0], c[:-1]]
        b = pd.DataFrame({'t': 1767225600 + 900 * np.arange(n), 'open': o, 'high': np.maximum(o, c) + 1, 'low': np.minimum(o, c) - 1, 'close': c,
                          'vol': r.integers(100, 200, n) * np.where(r.random(n) < .08, 5, 1)})
        k = M.do(b)
        self.assertGreater(k['dot_bien']['so_lan'], 0)
        self.assertGreater(k['moc']['so_lan'], k['dot_bien']['so_lan'])
        self.assertIn(k['ket_luan'], ('chưa đủ dữ liệu', 'có lợi thế trên mẫu này', 'chưa thấy lợi thế'))
        src = (Path(__file__).resolve().parent.parent / 'cong-cu' / 'do_khoi_luong.py').read_text(encoding='utf-8')
        self.assertNotIn('MetaTrader5', src)                                           # chỉ đọc qua webapp, không tự nối MT5


if __name__ == '__main__':
    unittest.main()
