"""Bài kiểm cho bản chia sẻ: nối MT5 độc lập (không có mã EA Promax), đổi giờ sàn về UTC, chỉ báo chung, nhận biết bản chia sẻ,
trang chủ chuyển sang Thị trường, và bộ quét thông tin riêng của cong-cu/dong_goi.py. Không nối MT5 thật: dùng đồ giả."""
import importlib.util
import json
from http_owner import owner_cookie
import sys
import tempfile
import threading
import types
import unittest
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import chi_bao, gia, kien_thuc, kiem_chung, noi_mt5, trang, web  # noqa: E402

T5 = r'C:\MT5\terminal64.exe'


class ChonTerminalTest(unittest.TestCase):
    def test_khong_co_mt5(self):
        self.assertEqual(noi_mt5.chon_terminal(None, [])[2], noi_mt5.CHUA_MO)

    def test_mot_mt5_thi_tu_nhan(self):
        self.assertEqual(noi_mt5.chon_terminal(None, [('terminal64.exe', 7, T5)]), (T5, (7,), None))

    def test_nhieu_mt5_thi_doi_ghi_duong_dan(self):
        duong, _, ly = noi_mt5.chon_terminal(None, [('terminal64.exe', 7, T5), ('terminal64.exe', 8, r'D:\Khac\terminal64.exe')])
        self.assertIsNone(duong)
        self.assertIn('đang mở 2 MT5', ly)                                           # số thay cho đường dẫn: lớp dịch khớp được
        self.assertIn('Cài đặt', ly)
        self.assertEqual(noi_mt5.chon_terminal(T5.lower(), [('terminal64.exe', 7, T5), ('terminal64.exe', 8, r'D:\Khac\terminal64.exe')])[1], (7,))

    def test_mt5_da_ghi_chua_mo(self):
        self.assertIn('chưa mở', noi_mt5.chon_terminal(T5, [('terminal64.exe', 8, r'D:\Khac\terminal64.exe')])[2])

    def test_dang_chay_strategy_tester_thi_khong_noi(self):
        self.assertIn('Strategy Tester', noi_mt5.chon_terminal(None, [('terminal64.exe', 7, T5), ('metatester64.exe', 9, r'C:\MT5\metatester64.exe')])[2])


class _Mt5Gia:
    """MT5 giả: initialize ghi lại đường dẫn; tài khoản demo hoặc không; có thể 'tự mở' thêm một MT5 khi initialize."""
    def __init__(self, demo=True, tu_mo=False, ok=True):
        self.demo, self.tu_mo, self.ok, self.dong, self.goi = demo, tu_mo, ok, 0, []

    def initialize(self, path):
        self.goi.append(path)
        return self.ok

    def shutdown(self):
        self.dong += 1

    def last_error(self):
        return (-6, 'Authorization failed')

    def terminal_info(self):
        return types.SimpleNamespace(connected=True, path=r'C:\MT5')

    def account_info(self):
        return types.SimpleNamespace(trade_mode=0 if self.demo else 2, server='San-Demo')


class NoiTest(unittest.TestCase):
    def _noi(self, mt5, procs_sau=None, cfgm=None):
        lan = {'n': 0}
        truoc = [('terminal64.exe', 7, T5)]

        def procs():
            lan['n'] += 1
            return procs_sau if (procs_sau is not None and lan['n'] >= 3) else truoc
        dong = []
        kq = noi_mt5.noi(mt5, cfgm or {}, procs_fn=procs, window_fn=lambda pid: True, sleep=lambda s: None, dong_fn=dong.append)
        return kq, dong

    def test_noi_duoc_tai_khoan_demo(self):
        m = _Mt5Gia()
        (duong, ly), _ = self._noi(m)
        self.assertEqual((duong, ly, m.goi), (T5, None, [T5]))

    def test_tu_choi_tai_khoan_that_theo_mac_dinh(self):
        m = _Mt5Gia(demo=False)
        (duong, ly), _ = self._noi(m)
        self.assertIsNone(duong)
        self.assertIn('DEMO', ly)
        self.assertEqual(m.dong, 1)                                              # đã ngắt
        (duong, ly), _ = self._noi(_Mt5Gia(demo=False), cfgm={'chi_demo': False})
        self.assertEqual(duong, T5)

    def test_thu_vien_tu_mo_them_mt5_thi_ngat_va_dong_ban_moi(self):
        m = _Mt5Gia()
        (duong, ly), dong = self._noi(m, procs_sau=[('terminal64.exe', 7, T5), ('terminal64.exe', 99, T5)])
        self.assertEqual((duong, ly, dong, m.dong), (None, noi_mt5.TU_MO, [99], 1))

    def test_chua_dang_nhap(self):
        (duong, ly), _ = self._noi(_Mt5Gia(ok=False))
        self.assertIn('chưa đăng nhập', ly)

    def test_mt5_dang_tat_thi_khong_goi_initialize(self):
        m = _Mt5Gia()
        kq = noi_mt5.noi(m, {}, procs_fn=lambda: [('terminal64.exe', 7, T5)], window_fn=lambda pid: False, sleep=lambda s: None)
        self.assertEqual((kq, m.goi), ((None, noi_mt5.DANG_DOI), []))


class _Tick:
    def __init__(self, t, bid=1.0, ask=1.1):
        self.time, self.time_msc, self.bid, self.ask = t, t * 1000 + 250, bid, ask


class _Mt5Gio:
    TIMEFRAME_M15 = 15

    def __init__(self, ticks, server='San-A'):
        self.ticks, self.server = ticks, server

    def symbols_get(self):
        return [types.SimpleNamespace(name=n, visible=True) for n in self.ticks]

    def symbol_info_tick(self, s):
        t = self.ticks.get(s)
        return None if t is None else _Tick(t)

    def account_info(self):
        return types.SimpleNamespace(server=self.server)

    def copy_rates_from_pos(self, sym, tf, pos, n):
        return np.array([(1_000_000, 1.0, 2.0, 0.5, 1.5)], dtype=[('time', '<i8'), ('open', '<f8'), ('high', '<f8'), ('low', '<f8'), ('close', '<f8')])


class GioSanTest(unittest.TestCase):
    def test_do_lech_lam_tron_nua_gio(self):
        now = 1_800_000_000
        self.assertEqual(noi_mt5.do_lech(_Mt5Gio({'XAUUSD': now + 7200 - 3}), 'XAUUSD', now), 7200)
        self.assertEqual(noi_mt5.do_lech(_Mt5Gio({'XAUUSD': now - 1}), 'XAUUSD', now), 0)
        self.assertEqual(noi_mt5.do_lech(_Mt5Gio({'XAUUSD': now + 10800 + 30}), 'XAUUSD', now), 10800)

    def test_cuoi_tuan_dung_ma_con_chay(self):
        now = 1_800_000_000
        m = _Mt5Gio({'XAUUSD': now - 2 * 86400, 'BTCUSD': now + 7200})               # vàng nghỉ, crypto vẫn chạy
        self.assertEqual(noi_mt5.do_lech(m, 'XAUUSD', now), 7200)
        self.assertIsNone(noi_mt5.do_lech(_Mt5Gio({'XAUUSD': now - 2 * 86400}), 'XAUUSD', now))

    def test_thu_tu_uu_tien(self):
        with tempfile.TemporaryDirectory() as t:
            luu = Path(t) / 'lech.json'
            m_cu = _Mt5Gio({'XAUUSD': 1})                                          # tick quá cũ: không đo được
            self.assertEqual(noi_mt5.lech_gio(m_cu, {}, 'XAUUSD', luu)[0], 0)
            luu.write_text(json.dumps({'San-A': 10800}), encoding='utf-8')
            self.assertEqual(noi_mt5.lech_gio(m_cu, {}, 'XAUUSD', luu), (10800, 'lần đo trước'))
            self.assertEqual(noi_mt5.lech_gio(m_cu, {'lech_gio_san': 2}, 'XAUUSD', luu), (7200, 'theo cấu hình'))

    def test_boc_doi_gio_ve_utc(self):
        m = noi_mt5.LechGio(_Mt5Gio({'XAUUSD': 1_000_000 + 7200}), 7200)
        self.assertEqual(int(m.copy_rates_from_pos('XAUUSD', 15, 0, 1)['time'][0]), 1_000_000 - 7200)
        t = m.symbol_info_tick('XAUUSD')
        self.assertEqual((t.time, t.time_msc, t.bid), (1_000_000, 1_000_000_250, 1.0))
        self.assertEqual(m.server, 'San-A')                                         # thuộc tính khác đi thẳng tới thư viện
        g = noi_mt5.LechGio(_Mt5Gio({'XAUUSD': 5}), 0)
        self.assertIsInstance(g.symbol_info_tick('XAUUSD'), _Tick)                  # lệch 0: không bọc

    def test_lenh_va_lich_su_doi_gio_ve_utc(self):
        class Ban:
            def __init__(self, **k):
                self.__dict__.update(k)

            def _asdict(self):
                return dict(self.__dict__)
        goi = {}

        class Mt5:
            def history_deals_get(self, a, b, group=None):
                goi['tu'], goi['toi'] = a, b
                return (Ban(time=1_000_000 + 7200, time_msc=(1_000_000 + 7200) * 1000 + 5, profit=12.5, type=0),)

            def history_orders_get(self, a, b):
                return (Ban(time_setup=1_000_000 + 7200, time_done=1_000_100 + 7200, time_expiration=0, time_setup_msc=0, type=2),)

            def positions_get(self):
                return (Ban(time=2_000_000 + 7200, time_update=2_000_060 + 7200, time_msc=(2_000_000 + 7200) * 1000, symbol='XAUUSD'),)

            def orders_get(self):
                return None
        m = noi_mt5.LechGio(Mt5(), 7200)
        tu = datetime(2026, 11, 20, tzinfo=timezone.utc)
        d = m.history_deals_get(tu, tu, group='*XAU*')[0]
        self.assertEqual((goi['tu'], d.time, d.time_msc, d.profit, d.type), (datetime(2026, 11, 20, 2, tzinfo=timezone.utc), 1_000_000, 1_000_000_005, 12.5, 0))
        o = m.history_orders_get(tu, tu)[0]
        self.assertEqual((o.time_setup, o.time_done, o.time_expiration, o.time_setup_msc), (1_000_000, 1_000_100, 0, 0))     # 0 là "không có": giữ 0
        p = m.positions_get()[0]
        self.assertEqual((p.time, p.time_update, p.time_msc, p.symbol), (2_000_000, 2_000_060, 2_000_000_000, 'XAUUSD'))
        self.assertEqual(p._asdict()['time'], 2_000_000)
        self.assertIsNone(m.orders_get())
        self.assertIsInstance(noi_mt5.LechGio(Mt5(), 0).positions_get()[0], Ban)        # lệch 0: trả nguyên bản

    def test_tim_ma_vang(self):
        m = _Mt5Gio({'EURUSD': 1, 'XAUUSD.r': 1, 'XAUUSDm': 1})
        self.assertEqual(noi_mt5.tim_ma_vang(m), 'XAUUSDm')
        self.assertEqual(noi_mt5.tim_ma_vang(m, 'XAUUSD.r'), 'XAUUSD.r')
        self.assertEqual(noi_mt5.tim_ma_vang(_Mt5Gio({'GOLD': 1, 'EURUSD': 1})), 'GOLD')
        self.assertIsNone(noi_mt5.tim_ma_vang(_Mt5Gio({'EURUSD': 1})))


class ChiBaoTest(unittest.TestCase):
    def _nen(self, n=900, f='15min'):
        t = pd.date_range('2026-01-05', periods=n, freq=f, tz='UTC')
        c = 3000 + np.cumsum(np.sin(np.arange(n) / 7.0) * 3 - 0.2)
        return pd.DataFrame({'open': c - 1, 'high': c + 4, 'low': c - 5, 'close': c}, index=t)

    def test_snapshot_va_vung(self):
        m15, h1, h4, d1 = self._nen(), self._nen(300, '1h'), self._nen(300, '4h'), self._nen(900, '1D')
        s = chi_bao.snapshot(m15, h1, h4, d1, 'M15')
        self.assertTrue({'H1', 'H4', 'D1', 'trend', 'atr', 'support', 'resistance'} <= set(s))
        self.assertEqual(s['trend'], s['H1'] if s['H1'] == s['H4'] == s['D1'] else 0)
        self.assertAlmostEqual(s['support'], float(m15['low'].iloc[-8:].min()))
        src = m15.reset_index(names='time')
        for z in chi_bao.fvg_zones(src, 0.1, 8) + chi_bao.order_blocks(src, 0.5, 8):
            self.assertLess(z['duoi'], z['tren'])
            self.assertIn(z['huong'], ('tang', 'giam'))


class NhanBietTest(unittest.TestCase):
    def test_ban_chia_se_khi_khong_co_ma_rieng(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(gia.ban_chia_se({'ma_nguon': []}))
            self.assertTrue(gia.ban_chia_se({'ma_nguon': [str(Path(t) / 'khong-co')]}))
            self.assertFalse(gia.ban_chia_se({'ma_nguon': [t]}))

    def test_nap_ma_tra_chi_bao_chung(self):
        saved = {k: sys.modules.pop(k) for k in list(sys.modules) if k.split('.')[0] in ('ai', 'tinhieu')}
        path = list(sys.path)
        try:
            sys.path[:] = [p for p in sys.path if 'EA Promax' not in p and 'Tele' not in p]
            R, RT, RF, SN = gia._nap_ma({'ma_nguon': [r'X:\khong-co']})
            self.assertIs(R, chi_bao.R)
            self.assertIsNone(RF)
        finally:
            sys.path[:] = path
            sys.modules.update(saved)

    def test_chua_noi_mt5_thi_bao_ly_do_thay_vi_loi_tim_tep(self):
        from so_cong_khai import hoc, phan_tich, song
        g = {'ma_nguon': [], 'kho_m1': '', 'mt5': {'bat': True, 'terminal': ''}}
        cu = song.khung_song
        song.khung_song = lambda g: None
        song._tt['ly_do'] = 'Máy đang mở nhiều MT5: A; B.'
        try:
            for goi in (lambda: gia.goi({'gia': g}, 'M15', 60), lambda: phan_tich.phan_tich({'gia': g})):
                with self.assertRaises(gia.ChuaCoGia) as e:
                    goi()
                self.assertIn('nhiều MT5', str(e.exception))
            self.assertIn('nhiều MT5', hoc.lay({'gia': g}, Path(tempfile.gettempdir()))['loi'][0])
        finally:
            song.khung_song = cu

    def test_kiem_chung_bao_ro_ban_chia_se(self):
        r = kiem_chung.lay({'gia': {'ma_nguon': []}}, Path(tempfile.gettempdir()))
        self.assertTrue(r['chia_se'])
        self.assertFalse(r['san_sang'])


class TrangChuTest(unittest.TestCase):
    def tearDown(self):
        trang.MIEN_TRU = trang.MIEN_TRU_GOC                                     # máy chủ đổi câu miễn trừ theo cấu hình: trả lại cho bài khác

    def _chay(self, cfg, duong='/'):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'c.json'
            p.write_text(json.dumps(cfg), encoding='utf-8')
            srv = web.tao_may_chu(str(p), port=0)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                class Khong(urllib.request.HTTPRedirectHandler):
                    def redirect_request(self, *a, **k):
                        return None
                try:
                    r = urllib.request.build_opener(Khong).open(urllib.request.Request(f'http://127.0.0.1:{srv.server_address[1]}{duong}', headers={'Cookie': owner_cookie(p.parent)}), timeout=30)
                    return r.status, r.read().decode('utf-8')
                except urllib.error.HTTPError as e:
                    return e.code, e.headers.get('Location')
            finally:
                srv.shutdown()
                srv.server_close()

    def test_ban_chia_se_co_trang_tong_quan_thong_nhat(self):
        cfg = json.loads((GOC / 'cau-hinh.mau.json').read_text(encoding='utf-8'))
        code, html = self._chay(cfg)
        self.assertEqual(code, 200)
        self.assertIn('Tổng quan phiên giao dịch', html)
        self.assertIn('href="/bat-dau"', html)

    def test_ban_chia_se_dung_cau_mien_tru_chung_va_kien_thuc_chung(self):
        cfg = json.loads((GOC / 'cau-hinh.mau.json').read_text(encoding='utf-8'))
        ma, html = self._chay(cfg, '/kien-thuc')
        self.assertEqual(ma, 200)
        self.assertIn(trang.MIEN_TRU_CHIA_SE, html)
        self.assertNotIn('chạy bóng, không phải kết quả tiền thật', html)
        for rieng in ('Các luật của bạn', '17 đến 28', 'EA Promax', 'id="du-lieu-moi"'):
            self.assertNotIn(rieng, html)

    def test_cau_mien_tru_khong_lay_sang_luot_khac(self):
        cfg = json.loads((GOC / 'cau-hinh.mau.json').read_text(encoding='utf-8'))
        self.assertIn(trang.MIEN_TRU_CHIA_SE, self._chay(cfg, '/kien-thuc')[1])      # luồng của lượt yêu cầu: câu bản chia sẻ
        self.assertEqual(trang.MIEN_TRU, trang.MIEN_TRU_GOC)                          # luồng của bài kiểm không bị đổi
        self.assertIn(trang.MIEN_TRU_GOC, kien_thuc.trang_kien_thuc('Thử'))

    def test_cau_hinh_mau_khong_co_duong_dan_rieng(self):
        noi = (GOC / 'cau-hinh.mau.json').read_text(encoding='utf-8')
        self.assertNotRegex(noi, r'[A-Za-z]:\\\\|%[A-Z]+%')
        cfg = json.loads(noi)
        self.assertTrue(cfg['gia']['mt5']['chi_demo'])
        self.assertEqual(cfg['gia']['ma_nguon'], [])


class DongGoiTest(unittest.TestCase):
    def test_quet_bat_duoc_duong_dan_rieng(self):
        spec = importlib.util.spec_from_file_location('dong_goi', GOC / 'cong-cu' / 'dong_goi.py')
        dg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dg)
        with tempfile.TemporaryDirectory() as t:
            a, b = Path(t) / 'a.py', Path(t) / 'b.md'
            a.write_text("P = r'D:\\\\Du An Rieng\\\\gia'\n", encoding='utf-8')
            b.write_text('không có gì riêng', encoding='utf-8')
            thay = dg.quet([(a, 'a.py'), (b, 'b.md')], [r'D:\Du An Rieng'])
            self.assertEqual(len(thay), 1)
            self.assertIn('a.py', thay[0])
        self.assertNotIn('cau-hinh.json', [x for _, x in dg.danh_sach()])
        goc_kt = (GOC / 'so_cong_khai' / 'kien_thuc.py').read_text(encoding='utf-8')
        moi = dg.kien_thuc_chia_se(goc_kt)
        compile(moi, 'kien_thuc.py', 'exec')
        self.assertIn('17 đến 28', goc_kt)                                      # tệp gốc của chủ dự án giữ nguyên
        for rieng in ('17 đến 28', 'sáu TP', 'Luật bot'):
            self.assertNotIn(rieng, moi)


if __name__ == '__main__':
    unittest.main()
