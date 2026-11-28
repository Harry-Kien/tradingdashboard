"""Bài kiểm cho phần nhiều mã CFD: dùng một MT5 giả, không nối MT5 thật. Kiểm rằng chỉ đọc mã đang hiện, làm tròn đúng số chữ số
của từng mã, không gọi luật vào lệnh của vàng, và không có lời gọi chọn mã hay đặt lệnh."""
import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from so_cong_khai import bieu_do, da_ma, gia, tai_khoan_chart, trang, web  # noqa: E402
from test_gia import MA_THAT  # noqa: E402

HET = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
PHUT = {'M5': 5, 'M15': 15, 'M30': 30, 'H1': 60, 'H4': 240, 'D1': 1440}


class MT5Gia:
    """Đủ những gì da_ma dùng: symbols_get, symbol_info_tick, copy_rates_from_pos. Ghi lại mọi lời gọi để kiểm."""

    def __init__(self):
        for i, tf in enumerate(PHUT):
            setattr(self, 'TIMEFRAME_' + tf, i)
        self.goi = []
        self.ma = {'XAUUSDp': (2, 3800.0, 'Commodities_PRO\\XAU\\XAUUSDp', 'Gold vs US Dollar', True),
                   'EURUSDp': (5, 1.09, 'Forex_PRO\\Major\\EURUSDp', 'Euro vs US Dollar', True),
                   'BTCUSDTp': (1, 60000.0, 'Crypto_PRO\\BTCUSDTp', 'Bitcoin vs USDT', True),
                   'AUDUSDp': (5, 0.65, 'Forex_PRO\\Major\\AUDUSDp', 'Australian Dollar vs US Dollar', False)}

    def symbols_get(self):
        return [SimpleNamespace(name=k, digits=v[0], path=v[2], description=v[3], visible=v[4]) for k, v in self.ma.items()]

    def symbol_info(self, ten):
        s = next((s for s in self.symbols_get() if s.name == ten), None)
        if s:
            s.point = 10. ** -s.digits
        return s

    def symbol_info_tick(self, ten):
        g = self.ma[ten][1]
        return SimpleNamespace(bid=g, ask=g * 1.0001, time=int(HET.timestamp()))

    def copy_rates_from_pos(self, ten, tf, vi_tri, n):
        self.goi.append((ten, tf, vi_tri, n))
        ten_tf = list(PHUT)[tf]
        g, buoc = self.ma[ten][1], PHUT[ten_tf] * 60
        cuoi = int(HET.timestamp()) // buoc * buoc - (buoc if vi_tri else 0)
        t = cuoi - buoc * np.arange(n - 1, -1, -1)
        k = np.arange(n)
        c = g * (1 + 0.004 * np.sin(k / 9.0) + 0.00002 * (k - n))
        o = np.roll(c, 1)
        o[0] = c[0]
        r = np.zeros(n, dtype=[('time', 'i8'), ('open', 'f8'), ('high', 'f8'), ('low', 'f8'), ('close', 'f8'), ('tick_volume', 'i8')])
        r['time'], r['open'], r['close'] = t, o, c
        r['high'], r['low'] = np.maximum(o, c) * 1.0005, np.minimum(o, c) * 0.9995
        return r


@unittest.skipUnless(all(os.path.isdir(p) for p in MA_THAT), 'không có mã của dự án trên máy này')
class DaMaTest(unittest.TestCase):
    def setUp(self):
        self.mt5 = MT5Gia()
        self.that = da_ma._mt5
        da_ma._mt5 = lambda g: self.mt5
        da_ma._nho.clear()
        self.cfg = {'ten': 'Thử', 'gia': {'ma_nguon': MA_THAT, 'ma_vang': 'XAUUSDp'}}

    def tearDown(self):
        da_ma._mt5 = self.that
        da_ma._nho.clear()

    def test_danh_sach_chi_gom_ma_dang_hien(self):
        r = da_ma.danh_sach(self.cfg, HET + timedelta(minutes=2))
        self.assertTrue(r['san_sang'])
        self.assertEqual([x['ma'] for x in r['ds']], ['XAUUSDp', 'EURUSDp', 'BTCUSDTp'])          # vàng trước; AUDUSDp không hiện thì không đọc
        self.assertNotIn('AUDUSDp', {g[0] for g in self.mt5.goi})
        eur = r['ds'][1]
        self.assertEqual((eur['nhom'], eur['so_le'], eur['la_vang'], eur['tuoi_phut']), ('Ngoại hối', 5, False, 2))
        self.assertEqual(set(eur['xu_huong']), {'D1', 'H4', 'H1'})
        self.assertEqual(eur['bid'], 1.09)
        self.assertEqual(len(eur['tia']), 48)
        self.assertTrue(0 < eur['atr_pct'] < 5 and 0 <= eur['rsi_h1'] <= 100)
        self.assertEqual(r['ds'][2]['nhom'], 'Tiền mã hóa')
        json.dumps(r)

    def test_bieu_do_ma_khac_khong_co_luat_vang(self):
        d = da_ma.goi(self.cfg, 'EURUSDp', 'M15', 200, HET + timedelta(minutes=2))
        self.assertTrue(d['khac_vang'])
        self.assertEqual((d['ma'], d['so_le'], len(d['candles']), d['lenh']), ('EURUSDp', 5, 200, []))
        self.assertEqual(len(str(d['candles'][-1][4]).split('.')[1]) <= 5, True)                   # làm tròn theo số chữ số của mã
        self.assertGreater(abs(d['candles'][-1][4] - round(d['candles'][-1][4], 2)), 0)            # không bị làm tròn về 2 chữ số như vàng
        for k in ('bot_tin_hieu', 'ba_khung', 'dinh_day', 'bot_cho'):
            self.assertNotIn(k, d['luat'])                                                        # không gọi luật vào lệnh của vàng
        self.assertEqual(set(d['luat']['bot']) >= {'D1', 'H4', 'H1', 'trend', 'atr', 'support', 'resistance'}, True)
        self.assertIn('dang_chay', d)
        self.assertEqual(len(d['ho_tro']), 200)
        json.dumps(d)

    def test_phan_tich_ma_khac_chi_co_boi_canh(self):
        p = da_ma.phan_tich(self.cfg, 'BTCUSDTp', HET + timedelta(hours=3))
        self.assertEqual((p['phuong_an'], p['con_hieu_luc'], p['khac_vang']), ([], 0, True))
        self.assertIn('đo riêng cho vàng', p['giai_thich'])
        self.assertEqual(set(p['boi_canh']['xu_huong']), {'D1', 'H4', 'H1', 'trend'})
        self.assertTrue(any('Giá đã cũ 180 phút' in c for c in p['canh_bao']))

    def test_ma_khong_hien_hoac_khong_co_thi_tu_choi(self):
        for ma in ('AUDUSDp', 'KHONGCO'):
            with self.assertRaises(ValueError):
                da_ma.goi(self.cfg, ma, 'M15')
        with self.assertRaises(ValueError):
            da_ma.goi(self.cfg, 'EURUSDp', 'M7')

    def test_qua_may_chu(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            cfgp = Path(tmp) / 'c.json'
            cfgp.write_text(json.dumps({**self.cfg, 'thu_muc_ra': str(Path(tmp) / 'out')}), encoding='utf-8')
            _, token = tai_khoan_chart.vao('owner_ma_test', 'test-market-owner-password-1234', True, Path(tmp))
            headers = {'Cookie': tai_khoan_chart.cookie_header(token).split(';', 1)[0]}
            srv = web.tao_may_chu(str(cfgp), port=0)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            goc = f'http://127.0.0.1:{srv.server_address[1]}'

            def mo(path):
                return urllib.request.urlopen(urllib.request.Request(goc + path, headers=headers), timeout=30)

            try:
                with mo('/api/ma') as r:
                    self.assertEqual(len(json.loads(r.read())['ds']), 3)
                with mo('/api/gia?ma=EURUSDp&tf=H1&n=60') as r:
                    self.assertTrue(json.loads(r.read())['khac_vang'])
                with mo('/api/phan-tich?ma=EURUSDp') as r:
                    data = json.loads(r.read())
                    self.assertEqual(data['phuong_an'], [])
                    self.assertEqual({p['ma'] for p in data['phuong_phap'] if p.get('chip', '').startswith('harry_')},
                                     {'harry_smc:M15', 'harry_xu_huong:M15'})
                with self.assertRaises(urllib.error.HTTPError) as e:
                    mo('/api/gia?ma=AUDUSDp').close()
                self.assertEqual(e.exception.code, 400)
            finally:
                srv.shutdown()
                srv.server_close()


class KhongCanMT5Test(unittest.TestCase):
    def test_chua_noi_mt5_thi_bao_ro(self):
        that = da_ma._mt5
        da_ma._mt5 = lambda g: None
        da_ma._nho.clear()
        try:
            r = da_ma.danh_sach({'gia': {}})
            self.assertEqual((r['san_sang'], r['ds']), (False, []))
            with self.assertRaises(ValueError):
                da_ma.goi({'gia': {}}, 'EURUSDp')
        finally:
            da_ma._mt5 = that

    def test_thu_vien_bieu_do_phuc_vu_tu_may(self):
        import hashlib
        import tempfile
        f = web.HERE / 'tinh' / 'lightweight-charts-5.3.0' / 'lightweight-charts.standalone.production.js'
        html = bieu_do.trang_bieu_do('Thử')
        for must in ('<script src="/tinh/lightweight-charts.js">', 'id="lw"', 'TradingView Lightweight Charts', "get('ve')!=='cu'", 'attributionLogo:false', 'Copyright (c) 2026 TradingView, Inc.', 'href="https://www.tradingview.com/"'):
            self.assertIn(must, html)                                                               # có ghi nguồn, và có đường lui về lớp vẽ cũ
        self.assertNotIn('cdn.jsdelivr.net', html)                                                   # lúc chạy không gọi ra mạng
        with tempfile.TemporaryDirectory() as tmp:
            cfgp = Path(tmp) / 'c.json'
            cfgp.write_text(json.dumps({'ten': 'Thử', 'gia': {}, 'thu_muc_ra': str(Path(tmp) / 'out')}), encoding='utf-8')
            srv = web.tao_may_chu(str(cfgp), port=0)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            goc = f'http://127.0.0.1:{srv.server_address[1]}/tinh/lightweight-charts.js'
            try:
                if f.is_file():
                    with urllib.request.urlopen(goc, timeout=20) as r:
                        than = r.read()
                        self.assertEqual(r.headers.get('Content-Type'), 'text/javascript; charset=utf-8')
                    self.assertEqual(len(than), 198600)
                    self.assertEqual(hashlib.sha256(than).hexdigest(), '338a625ece52c5b85fb026e222dad5d0f365f745060afbfae96bda91636142e9')   # đúng tệp đã kiểm, không bị sửa
                    self.assertIn(hashlib.sha256(than).hexdigest(), (web.HERE / 'tinh' / 'NGUON.md').read_text(encoding='utf-8'))
                else:
                    with self.assertRaises(urllib.error.HTTPError) as e:
                        urllib.request.urlopen(goc, timeout=20)
                    self.assertEqual(e.exception.code, 404)
                with self.assertRaises(urllib.error.HTTPError) as e:                                # không mở được tệp nào khác trong thư mục đó
                    urllib.request.urlopen(goc.replace('lightweight-charts.js', 'NGUON.md'), timeout=20)
                self.assertEqual(e.exception.code, 404)
            finally:
                srv.shutdown()
                srv.server_close()

    def test_trang_va_ma_nguon(self):
        html = bieu_do.trang_bieu_do('Thử')
        for must in ('id="ma"', '/api/ma', 'id="bot-tt"', 'data-bo="gon"', 'Vẽ mức tham chiếu lên biểu đồ', 'Bot tín hiệu'):
            self.assertIn(must, html)
        self.assertIn('id="ds-ma"', trang._KHOI_MA)
        src = Path(da_ma.__file__).read_text(encoding='utf-8')
        for banned in ('order_send', 'order_check', 'TRADE_ACTION', 'positions_get', 'symbol_select('):
            self.assertNotIn(banned, src)
        self.assertEqual(gia._so(1.23456), 1.23)                                                   # hàm làm tròn của vàng không đổi


if __name__ == '__main__':
    unittest.main()
