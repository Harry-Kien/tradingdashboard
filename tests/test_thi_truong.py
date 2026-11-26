"""Bài kiểm cho bảng giá trực tiếp (thi_truong.py) và ba trang mới: dùng một MT5 giả, không nối MT5 thật.
Kiểm phân loại mã, kích thước pip, chỉ thêm mã vào Market Watch khi cấu hình bật, luồng SSE chỉ gửi mã có giá mới,
lời gọi tính toán không phải lời gọi đặt lệnh, lịch tin, và các đường dẫn của webapp."""
import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import thi_truong as T, trang, web  # noqa: E402

HET = int(datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc).timestamp())
TF = ['M5', 'D1', 'W1', 'MN1', 'H1', 'M15', 'H4']


class MT5Gia:
    ORDER_TYPE_BUY, ORDER_TYPE_SELL = 0, 1

    def __init__(self):
        for i, tf in enumerate(TF):
            setattr(self, 'TIMEFRAME_' + tf, i)
        self.goi, self.chon = [], []
        self.ma = {  # tên: (số lẻ, giá, path, hiện, trade_mode, tick_value, cs)
            'EURUSDp': (5, 1.1, 'Forex_PRO\\Major\\EURUSDp', True, 4, 1.0, 100000),
            'GBPUSDp': (5, 1.3, 'Forex_PRO\\Major\\GBPUSDp', True, 4, 1.0, 100000),
            'EURGBPp': (5, 0.85, 'Forex_PRO\\Minor\\EURGBPp', False, 4, 1.3, 100000),
            'USDJPYp': (3, 150.0, 'Forex_PRO\\Major\\USDJPYp', False, 4, 0.66, 100000),
            'XAUUSDp': (2, 3600.0, 'Commodities_PRO\\XAU\\XAUUSDp', True, 4, 1.0, 100),
            'US30p': (2, 49000.0, 'Indices_PRO\\US30p', False, 4, 0.01, 1),
            'BTCUST': (1, 60000.0, 'RefSymbols\\BTCUST', False, 4, 1.0, 1),
            'ETHBTCp': (6, 0.03, 'Crypto_PRO\\ETHBTCp', False, 0, 1.0, 1),
        }
        self.dich = 0.0

    def symbols_get(self):
        return [SimpleNamespace(name=k, digits=v[0], point=10.0 ** -v[0], path=v[2], description=k[:-1], visible=v[3] or k in self.chon,
                                trade_mode=v[4], trade_tick_value=v[5], trade_tick_size=10.0 ** -v[0], trade_contract_size=v[6],
                                volume_min=0.01, volume_step=0.01, volume_max=100.0, currency_base=k[:3], currency_profit=k[3:6], currency_margin=k[:3],
                                trade_calc_mode=0, trade_stops_level=0, swap_mode=0, swap_long=-1.0, swap_short=0.5, swap_rollover3days=3, ask=v[1])
                for k, v in self.ma.items()]

    def account_info(self):
        return SimpleNamespace(currency='USD', leverage=100, margin_so_call=50.0, margin_so_so=20.0, company='Thử')

    def symbol_select(self, ten, bat):
        self.goi.append(('symbol_select', ten, bat))
        self.chon.append(ten)
        return True

    def symbol_info_tick(self, ten):
        v = self.ma[ten]
        if not (v[3] or ten in self.chon):
            return None
        g = v[1] * (1 + self.dich) if ten == 'EURUSDp' else v[1]
        return SimpleNamespace(bid=g, ask=g + 10.0 ** -v[0] * 2, time=HET, time_msc=HET * 1000)

    def copy_rates_from_pos(self, ten, tf, vi_tri, n):
        self.goi.append(('rates', ten, tf, n))
        g = self.ma[ten][1]
        k = np.arange(n)
        c = g * (1 + 0.001 * np.sin(k / 5.0 + (hash(ten) % 7)))
        r = np.zeros(n, dtype=[('time', 'i8'), ('open', 'f8'), ('high', 'f8'), ('low', 'f8'), ('close', 'f8')])
        r['time'] = HET - 3600 * (n - 1 - k)
        r['open'], r['close'] = np.roll(c, 1), c
        r['open'][0] = c[0]
        r['high'], r['low'] = np.maximum(r['open'], c) * 1.0005, np.minimum(r['open'], c) * 0.9995
        return r

    def order_calc_margin(self, kieu, ten, lot, gia):
        self.goi.append(('order_calc_margin', ten))
        return lot * self.ma[ten][6] * gia / 100

    def order_calc_profit(self, kieu, ten, lot, vao, ra):
        self.goi.append(('order_calc_profit', ten))
        return (ra - vao) * (1 if kieu == 0 else -1) * lot * self.ma[ten][6]


class PhanLoaiTest(unittest.TestCase):
    def test_goc_bo_duoi_san(self):
        self.assertEqual([T.goc(x) for x in ('EURUSDp', 'US30.cash', 'HK-HSIp', 'XAUUSD', 'GER40', 'BTCUSDTp')],
                         ['EURUSD', 'US30', 'HK-HSI', 'XAUUSD', 'GER40', 'BTCUSDT'])

    def test_phan_loai_theo_thu_muc_va_theo_ten(self):
        ca = {('EURUSDp', 'Forex_PRO\\Major\\EURUSDp'): 'fx_chinh', ('EURGBPp', 'Forex_PRO\\Minor\\EURGBPp'): 'fx_cheo',
              ('USDZARp', 'Forex_PRO\\Exotic\\USDZARp'): 'fx_ngoai_lai', ('XAUEURp', 'Commodities_PRO\\XAU\\XAUEURp'): 'kim_loai',
              ('BRENTp', 'Commodities_PRO\\BRENTp'): 'nang_luong', ('US30p', 'Indices_PRO\\US30p'): 'chi_so', ('BTCUSDTp', 'Crypto_PRO\\BTCUSDTp'): 'crypto',
              ('GBPJPY', ''): 'fx_cheo', ('USDCAD', ''): 'fx_chinh', ('USDTRY', ''): 'fx_ngoai_lai', ('XAGUSD', ''): 'kim_loai', ('USOIL', ''): 'nang_luong'}
        for (ten, path), lop in ca.items():
            self.assertEqual(T.phan_loai(ten, path), lop, ten)

    def test_kich_thuoc_pip(self):
        self.assertEqual(T.kich_thuoc_pip('fx_chinh', 5, 1e-5), 1e-4)
        self.assertAlmostEqual(T.kich_thuoc_pip('fx_chinh', 3, 1e-3), 0.01)
        self.assertIsNone(T.kich_thuoc_pip('kim_loai', 2, 0.01))


class BangGiaTest(unittest.TestCase):
    def tao(self, them=False):
        self.mt5 = MT5Gia()
        cfg = {'gia': {}, 'thi_truong': {'them_vao_market_watch': them}}
        return T.BangGia(lambda: cfg, mt5_fn=lambda g: self.mt5)

    def test_khong_them_ma_khi_cau_hinh_tat(self):
        b = self.tao(False)
        b.doc_dac_ta()
        self.assertEqual(sorted(b.dac_ta), ['EURUSDp', 'GBPUSDp', 'XAUUSDp'])
        self.assertFalse([g for g in self.mt5.goi if g[0] == 'symbol_select'])

    def test_them_ma_giao_dich_duoc_khi_bat_bo_ma_tham_chieu_va_ma_tat(self):
        b = self.tao(True)
        b.doc_dac_ta()
        self.assertEqual(sorted(b.dac_ta), ['EURGBPp', 'EURUSDp', 'GBPUSDp', 'US30p', 'USDJPYp', 'XAUUSDp'])
        self.assertEqual(sorted(g[1] for g in self.mt5.goi if g[0] == 'symbol_select'), ['EURGBPp', 'US30p', 'USDJPYp'])
        b.doc_dac_ta()                                                     # lần sau không chọn lại
        self.assertEqual(len([g for g in self.mt5.goi if g[0] == 'symbol_select']), 3)
        j = b.dac_ta['USDJPYp']
        self.assertEqual((j['lop'], j['cap'], j['biet_danh']), ('fx_chinh', ['USD', 'JPY'], 'Gopher'))
        self.assertAlmostEqual(j['pip'], 0.01)
        self.assertAlmostEqual(j['gt_pip'], 6.6, places=4)                # 0,66 mỗi điểm 0,001 → 6,6 mỗi pip 0,01
        self.assertEqual(b.dac_ta['EURUSDp']['ky_quy_1lot'], 1100.0)
        self.assertEqual(b.tai_khoan['don_bay'], 100)

    def test_chi_goi_ham_doc_va_ham_tinh(self):
        b = self.tao(True)
        b.doc_dac_ta()
        b.doc_gia()
        b.doc_moc(bat_buoc=True)
        b.tinh('EURUSDp', 'mua', 1.0, 1.1, 1.101)
        cam = {'order_send', 'order_check', 'positions_get', 'Buy', 'Sell'}
        self.assertFalse(cam & {g[0] for g in self.mt5.goi})
        self.assertFalse(any(hasattr(self.mt5, x) and x in cam for x in dir(self.mt5)))

    def test_moc_va_anh_chup(self):
        b = self.tao(False)
        b.doc_gia()
        self.assertTrue(b.san_sang)
        b.doc_moc(bat_buoc=True)
        a = b.anh_chup()
        eur = next(x for x in a['ds'] if x['ma'] == 'EURUSDp')
        self.assertEqual(len(eur['tia']), 49)
        self.assertEqual(set(eur['ref']), {'1h', '4h', 'ngay', 'tuan', 'thang'})
        self.assertIsNotNone(eur['adr'])
        self.assertEqual(eur['q'][0], 1.1)
        self.assertIsNotNone(a['tuong_quan'])
        self.assertEqual(a['tuong_quan']['ma_tran'][0][0], 1.0)

    def test_luong_chi_gui_ma_co_gia_moi(self):
        b = self.tao(False)
        b.doc_gia()
        goi = []

        class Dung(Exception):
            pass

        def gui(x):
            goi.append(x)
            if sum(1 for g in goi if g.startswith(b'event:')) >= 2:
                raise Dung

        def doi_gia():
            self.mt5.dich = 0.001
            b.doc_gia()
        threading.Timer(0.15, doi_gia).start()
        with self.assertRaises(Dung):
            b.luong(gui, het_giay=5, nhip=0.01, cho=2)
        ev = [json.loads(g.split(b'data: ', 1)[1]) for g in goi if g.startswith(b'event:')]
        self.assertTrue(ev[0]['day_du'])
        self.assertEqual(set(ev[0]['q']), {'EURUSDp', 'GBPUSDp', 'XAUUSDp'})
        self.assertEqual(set(ev[1]['q']), {'EURUSDp'})                    # lần sau chỉ mã có giá mới
        self.assertAlmostEqual(ev[1]['q']['EURUSDp'][0], 1.1011)

    def test_mat_ket_noi(self):
        b = T.BangGia(lambda: {'gia': {}}, mt5_fn=lambda g: None)
        b.doc_gia()
        self.assertFalse(b.san_sang)
        self.assertTrue(b.ly_do)

    def test_tinh_kiem_tham_so(self):
        b = self.tao(False)
        b.doc_dac_ta()
        r = b.tinh('EURUSDp', 'ban', 0.5, 1.1, 1.09)
        self.assertEqual((r['lai'], r['ky_quy']), (500.0, 550.0))
        for x in (('KHONG', 'mua', 1, 1, None), ('EURUSDp', 'xx', 1, 1, None), ('EURUSDp', 'mua', 0, 1, None), ('EURUSDp', 'mua', 1, -1, None)):
            with self.assertRaises(ValueError):
                b.tinh(*x)


class KyThuatTest(unittest.TestCase):
    def test_nhan_theo_nguong_tradingview(self):
        self.assertEqual([T.nhan_kt(x) for x in (0.8, 0.5, 0.2, 0.1, 0.0, -0.1, -0.3, -0.5, -0.51, None)],
                         ['Mua mạnh', 'Mua', 'Mua', 'Trung tính', 'Trung tính', 'Trung tính', 'Bán', 'Bán', 'Bán mạnh', '—'])

    def test_xu_huong_tang_thi_duong_trung_binh_nghieng_mua(self):
        c = np.linspace(100, 130, 260) + 0.2 * np.sin(np.arange(260) / 3)    # tăng đều, lắc nhỏ hơn độ trễ của đường trung bình 10
        r = T.ky_thuat(c, c + 0.5, c - 0.5, c, chi_tiet=True)
        self.assertEqual(r['dem_ma'], {'mua': 12, 'ban': 0, 'trung': 0})
        self.assertGreater(r['d'], 0.1)
        self.assertEqual(len(r['dd']), 7)
        g = 260 - np.linspace(0, 30, 260)                                    # đảo chiều: giảm đều
        self.assertLess(T.ky_thuat(g, g + 0.5, g - 0.5, g)['m'], -0.9)

    def test_it_nen_tra_none(self):
        self.assertIsNone(T.ky_thuat([1] * 30, [1] * 30, [1] * 30, [1] * 30))

    def test_bien_dong_theo_gio_viet_nam(self):
        t0 = int(datetime(2026, 11, 16, 0, 0, tzinfo=timezone.utc).timestamp())    # thứ Hai 00:00 UTC = 07:00 giờ Việt Nam
        t = [t0 + 3600 * i for i in range(24 * 5)]
        hi = [10.0 + (5.0 if (i % 24) == 13 else 1.0) for i in range(len(t))]        # 13:00 UTC = 20:00 giờ VN chạy mạnh nhất
        r = T.bien_dong_theo_gio(t, hi, [10.0] * len(t))
        best = max(r['gio'], key=lambda g: g['tb'] or 0)
        self.assertEqual(best['h'], 20)
        self.assertAlmostEqual(best['tb'], 5.0)


class ThanhDauTest(unittest.TestCase):
    def test_muc_dang_xem_va_nhom(self):
        from so_cong_khai import trang
        h = trang.thanh_dau('Harry · Gold Research', 'kien-thuc')
        self.assertIn('aria-current="page">Kiến thức', h)
        self.assertIn('nv-a on', h)                                          # nhóm "Học" được tô sáng
        for href in ('/', '/thi-truong#ky-thuat', '/bieu-do', '/cong-cu', '/nhat-ky', '/tai-khoan', '/hoc-giao-dich', '/kien-thuc'):
            self.assertIn(f'href="{href}"', h)
        self.assertNotIn('nv-a on', trang.thanh_dau('Thử', 'tong'))           # Tổng quan là mục đơn, không tô nhóm "Sổ giao dịch"


class LichTinTest(unittest.TestCase):
    def test_doc_lich_va_bao_sap_het(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'lich.csv'
            f.write_text('time,currency,importance,event,country\n2026.11.20 13:30,USD,3,Nonfarm Payrolls,US\n'
                         '2026.11.20 14:00,USD,1,Nho,US\n2026.11.21 10:00,EUR,2,CPI,EU\n2026.11.01 10:00,USD,3,Cu,US\n', encoding='utf-8')
            r = T.lich_tin({'gia': {'lich_tin': str(f)}}, datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc))
            self.assertTrue(r['co'])
            self.assertEqual([e['ten'] for e in r['ds']], ['Nonfarm Payrolls', 'CPI'])     # bỏ tin mức 1 và tin đã quá xa
            self.assertTrue(r['sap_het'])
        self.assertFalse(T.lich_tin({'gia': {'lich_tin': str(Path(d) / 'khong-co.csv')}})['co'])


class LichMangTest(unittest.TestCase):
    NGUON = [{'title': 'Non-Farm Employment Change', 'country': 'USD', 'date': '2026-11-20T08:30:00-05:00', 'impact': 'High', 'forecast': '150K', 'previous': '120K'},
             {'title': 'German ifo', 'country': 'EUR', 'date': '2026-11-21T04:00:00-05:00', 'impact': 'Medium', 'forecast': '', 'previous': '88.1'},
             {'title': 'Bank Holiday', 'country': 'JPY', 'date': '2026-11-23T00:00:00-05:00', 'impact': 'Holiday', 'forecast': '', 'previous': ''},
             {'title': 'hong', 'country': 'GBP', 'date': 'khong-phai-ngay', 'impact': 'Low'}]

    def setUp(self):
        from so_cong_khai import lich_mang
        self.L = lich_mang
        lich_mang._tt.update(lan_tai=None, loi=None, thu_sau=0.0, nho=None)

    def test_chuan_hoa_doi_gio_va_muc(self):
        ds = self.L.chuan_hoa(self.NGUON)
        self.assertEqual(len(ds), 3)                                          # bỏ dòng ngày hỏng
        self.assertEqual(ds[0]['t'], '2026-11-20T13:30:00+00:00')              # 08:30 New York = 13:30 UTC
        self.assertEqual([e['muc'] for e in ds], [3, 2, 0])
        self.assertEqual((ds[0]['du_bao'], ds[0]['truoc']), ('150K', '120K'))

    def test_gop_giu_tuan_cu_va_cap_nhat_dong_trung(self):
        now = datetime(2026, 11, 25, tzinfo=timezone.utc)
        cu = [{'t': '2026-11-01T00:00:00+00:00', 'tien': 'USD', 'muc': 3, 'ten': 'A'}, {'t': '2026-08-01T00:00:00+00:00', 'tien': 'USD', 'muc': 3, 'ten': 'Rat cu'},
              {'t': '2026-11-20T13:30:00+00:00', 'tien': 'USD', 'muc': 3, 'ten': 'Non-Farm Employment Change', 'du_bao': ''}]
        ds = self.L.gop(cu, self.L.chuan_hoa(self.NGUON), now)
        self.assertEqual([e['ten'] for e in ds][:2], ['A', 'Non-Farm Employment Change'])
        self.assertNotIn('Rat cu', [e['ten'] for e in ds])                    # cũ hơn 60 ngày thì bỏ
        self.assertEqual(sum(e['ten'] == 'Non-Farm Employment Change' for e in ds), 1)
        self.assertEqual(next(e for e in ds if e['tien'] == 'USD' and e['ten'].startswith('Non'))['du_bao'], '150K')

    def test_tai_loi_thi_giu_du_lieu_cu(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = {'lich_mang': {'tep': 'lich.json'}}
            r = self.L.tai(cfg, Path(d), tai_url=lambda u: self.NGUON, now=datetime(2026, 11, 22, tzinfo=timezone.utc))
            self.assertIsNone(r['loi'])
            self.assertEqual(len(self.L.doc(cfg, Path(d))['ds']), 3)

            def hong(u):
                raise OSError('mất mạng')
            r = self.L.tai(cfg, Path(d), tai_url=hong)
            self.assertIn('mất mạng', r['loi'])
            self.assertEqual(len(self.L.doc(cfg, Path(d))['ds']), 3)          # vẫn còn bản đã lưu

    def test_lich_tong_gop_mang_va_ea(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'ea.csv'
            f.write_text('time,currency,importance,event,country\n2026.11.20 13:30,USD,3,NFP ban EA,US\n2026.11.25 13:30,USD,3,Sau tuan nay,US\n', encoding='utf-8')
            cfg = {'gia': {'lich_tin': str(f)}, 'lich_mang': {'tep': 'lich.json'}}
            now = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
            self.L.tai(cfg, Path(d), tai_url=lambda u: self.NGUON, now=now)
            r = T.lich_tong(cfg, Path(d), now)
            ten = [e['ten'] for e in r['ds']]
            self.assertIn('Non-Farm Employment Change', ten)
            self.assertNotIn('NFP ban EA', ten)                                # trùng khoảng lịch mạng: lấy bản mạng
            self.assertIn('Sau tuan nay', ten)                                 # sau chỗ lịch mạng phủ: lấy thêm từ EA
            self.assertEqual({e['nguon'] for e in r['ds']}, {'mang', 'ea'})
            self.assertIn('EUR', r['tien_te'])
            self.assertFalse(r['sap_het'])
            r2 = T.lich_tong({**cfg, 'lich_mang': {'bat': False}}, Path(d), now)   # tắt lịch mạng: chỉ còn lịch EA
            self.assertEqual({e['nguon'] for e in r2['ds']}, {'ea'})


class WebTest(unittest.TestCase):
    def test_duong_dan_moi(self):
        mt5 = MT5Gia()
        with tempfile.TemporaryDirectory() as d:
            ch = Path(d) / 'cau-hinh.json'
            ch.write_text(json.dumps({'ten': 'Thử', 'gia': {}, 'thi_truong': {'bat': True}}), encoding='utf-8')
            b = T.BangGia(lambda: json.loads(ch.read_text(encoding='utf-8')), mt5_fn=lambda g: mt5)
            b.doc_gia()
            srv = web.tao_may_chu(str(ch), port=0, bang=b)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            u = f'http://127.0.0.1:{srv.server_address[1]}'
            try:
                for p, chu in (('/thi-truong', 'Thị trường Forex'), ('/cong-cu', 'Công cụ giao dịch'), ('/hoc-giao-dich', '16 phong cách')):
                    html = urllib.request.urlopen(u + p).read().decode('utf-8')
                    self.assertIn(chu, html)
                    self.assertIn('href="/thi-truong#bang-gia"', html)
                    self.assertIn('class="nv-tim-b"', html)                       # ô tìm nhanh Ctrl+K có ở mọi trang
                ma = json.loads(urllib.request.urlopen(u + '/api/thi-truong/ma').read())
                self.assertEqual({x['ma'] for x in ma['ds']}, {'EURUSDp', 'GBPUSDp', 'XAUUSDp'})
                b.doc_moc(bat_buoc=True)
                kt = json.loads(urllib.request.urlopen(u + '/api/thi-truong/ky-thuat?ma=EURUSDp').read())
                self.assertEqual(set(kt['khung']), {'M15', 'H1', 'H4', 'D1'})
                self.assertIn(kt['khung']['H1']['nhan'], ('Mua mạnh', 'Mua', 'Trung tính', 'Bán', 'Bán mạnh'))
                bd = json.loads(urllib.request.urlopen(u + '/api/thi-truong/bien-dong?ma=EURUSDp').read())
                self.assertEqual(len(bd['gio']), 24)
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(u + '/api/thi-truong/ky-thuat?ma=KHONG')
                j = json.loads(urllib.request.urlopen(u + '/api/thi-truong').read())
                self.assertTrue(j['san_sang'])
                self.assertEqual(len(j['ds']), 3)
                self.assertIn('lich', j)
                t = json.loads(urllib.request.urlopen(u + '/api/tinh?ma=EURUSDp&loai=mua&lot=1&vao=1.1&ra=1.2').read())
                self.assertAlmostEqual(t['lai'], 10000.0)
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(u + '/api/tinh?ma=EURUSDp&loai=mua&lot=abc&vao=1')
                r = urllib.request.urlopen(u + '/api/thi-truong/luong', timeout=5)
                self.assertIn('text/event-stream', r.headers['Content-Type'])
                dong = b''
                while b'event: gia' not in dong:
                    dong += r.read1(4096)
                r.close()
            finally:
                srv.shutdown()
                srv.server_close()
                trang.MIEN_TRU = trang.MIEN_TRU_GOC                   # máy chủ đổi câu miễn trừ theo cấu hình: trả lại cho bài khác


if __name__ == '__main__':
    unittest.main()
