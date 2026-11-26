"""Bài kiểm cho Phân tích hiệu suất (hieu_suat.py): ghép lần khớp thành lệnh, chỉ số, sụt vốn, vốn đầu kỳ, nhận xét có ngưỡng đủ mẫu,
dữ liệu minh họa, CSV, và trang /hieu-suat với một MT5 giả (chỉ hàm đọc và hàm tính, không đặt lệnh, chỉ tài khoản demo)."""
import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import dich, hieu_suat as H, tai_khoan, trang, web  # noqa: E402

T0 = int(datetime(2026, 11, 2, 1, 0, tzinfo=timezone.utc).timestamp())       # thứ Hai, 08:00 giờ Việt Nam


def deal(ticket, t, typ, entry, pos, vol=0.1, price=1.1, profit=0.0, comm=0.0, swap=0.0, magic=0, order=0, sym='EURUSD'):
    return SimpleNamespace(ticket=ticket, time=t, time_msc=t * 1000, type=typ, entry=entry, position_id=pos, volume=vol, price=price, profit=profit,
                           commission=comm, swap=swap, fee=0.0, magic=magic, symbol=sym, comment='', order=order)


def mau_deals():
    """Nạp 1000, lệnh A mua thắng +50 (có SL), lệnh B bán thua −20 (không SL), lệnh C mua còn mở, rút 100 sau lệnh đầu."""
    return [deal(1, T0 - 3600, 2, 0, 0, vol=0, price=0, profit=1000),
            deal(2, T0, 0, 0, 11, price=1.1000, order=101, comm=-0.5), deal(3, T0 + 1800, 1, 1, 11, price=1.1050, profit=50, comm=-0.5),
            deal(4, T0 + 7200, 2, 0, 0, vol=0, price=0, profit=-100),
            deal(5, T0 + 9000, 1, 0, 12, price=1.1040, order=102), deal(6, T0 + 18000, 0, 1, 12, price=1.1060, profit=-20, swap=-1),
            deal(7, T0 + 20000, 0, 0, 13, price=1.1, order=103)]


ORDERS = [SimpleNamespace(ticket=101, sl=1.0975, tp=1.1050), SimpleNamespace(ticket=102, sl=0.0, tp=0.0), SimpleNamespace(ticket=103, sl=0.0, tp=0.0)]


class GhepTest(unittest.TestCase):
    def test_ghep_lenh_va_bo_lenh_con_mo(self):
        lenh, nap = H.ghep_lenh(mau_deals(), ORDERS, rui_ro=lambda m, c, l, v, sl: abs(v - sl) * l * 100000)
        self.assertEqual([x['id'] for x in lenh], [11, 12])                          # lệnh 13 còn mở: bỏ
        a, b = lenh
        self.assertEqual((a['chieu'], a['rong'], a['phut'], a['sl']), ('MUA', 49.0, 30.0, 1.0975))
        self.assertAlmostEqual(a['r'], 49 / 25, places=2)                             # rủi ro 25 pip × 0,1 lot = 25 USD
        self.assertEqual((b['chieu'], b['rong'], b['sl'], b['r']), ('BAN', -21.0, None, None))
        self.assertEqual([x['tien'] for x in nap], [1000.0, -100.0])

    def test_von_dau_chi_tru_nap_rut_sau_lenh_dau(self):
        lenh, nap = H.ghep_lenh(mau_deals(), ORDERS)
        # số dư hiện tại = 1000 + 49 − 100 − 21 = 928 → vốn trước lệnh đầu là 1000 (nạp trước lệnh đầu là vốn ban đầu)
        self.assertAlmostEqual(H.von_dau(928.0, lenh, nap), 1000.0)


class PhanTichTest(unittest.TestCase):
    def test_chi_so_va_sut_von(self):
        lenh, _ = H.ghep_lenh(mau_deals(), ORDERS)
        r = H.phan_tich(lenh, 1000.0, 'USD')
        t = r['tong']
        self.assertEqual((t['n'], t['thang'], t['thua'], t['rong']), (2, 1, 1, 28.0))
        self.assertAlmostEqual(t['pf'], 49 / 21, places=2)
        self.assertEqual(t['dd_max'], 21.0)
        self.assertAlmostEqual(t['dd_pct'], 21 / 1049 * 100, places=1)
        self.assertEqual(t['khong_sl'], 1)
        self.assertEqual([p['v'] for p in r['duong_von']], [49.0, 28.0])
        self.assertEqual(r['ngay'], [{'ngay': '2026-11-02', 'rong': 28.0, 'n': 2}])
        self.assertEqual(r['bang']['phien'][0]['k'], 'Á')                               # mở lúc 01:00 UTC
        self.assertEqual(r['nhan_xet'][0]['muc'], 'tin')                                # chỉ 2 lệnh: nhắc chưa đủ mẫu
        json.dumps(r)

    def test_khong_co_lenh(self):
        r = H.phan_tich([], 1000.0)
        self.assertEqual(r['tong']['n'], 0)
        self.assertEqual(r['nhan_xet'][0]['vi']['tieu'], 'Chưa có lệnh đã đóng')
        self.assertEqual(r['nhan_xet'][0]['en']['tieu'], 'No closed trades yet')

    def test_du_lieu_minh_hoa_co_nhan_xet(self):
        now = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
        lenh, dau = H.mau(now=now)
        r = H.phan_tich(lenh, dau)
        self.assertGreaterEqual(r['tong']['n'], 200)
        self.assertLess(lenh[-1]['dong'], now.isoformat())                              # không có lệnh ở tương lai
        muc = {n['muc'] for n in r['nhan_xet']}
        self.assertIn('xau', muc)
        self.assertTrue(any('Giữ lệnh thua lâu hơn' in n['vi']['tieu'] for n in r['nhan_xet']))
        self.assertTrue(all(not dich._VI.search(n['en']['tieu'] + n['en']['noi']) for n in r['nhan_xet']))   # bản tiếng Anh không sót tiếng Việt
        self.assertEqual(H.mau(now=now)[0], lenh)                                       # cố định theo hạt giống
        self.assertIn('1.234,50 USD', H._fmt(1234.5, 'USD'))                             # số kiểu Việt Nam

    def test_nhan_xet_tra_thu(self):
        base = datetime(2026, 11, 3, 8, tzinfo=timezone.utc)
        lenh = []
        for i in range(12):
            mo = base + timedelta(hours=i)
            thua = i % 2 == 0
            lenh.append({'id': i, 'ma': 'X', 'chieu': 'MUA', 'lot': 0.1 if thua else 0.3, 'mo': mo.isoformat(), 'dong': (mo + timedelta(minutes=50)).isoformat(),
                         'phut': 50, 'lai': -10 if thua else -5, 'phi': 0, 'swap': 0, 'rong': -10 if thua else -5, 'sl': 1, 'r': None, 'nguon': 'Đặt tay'})
        r = H.phan_tich(lenh, 1000)
        self.assertTrue(any('tăng khối lượng ngay sau lệnh thua' in n['vi']['tieu'] for n in r['nhan_xet']))

    def test_lenh_hoa_von_khong_vao_chuoi_thua(self):
        base = datetime(2026, 11, 3, 8, tzinfo=timezone.utc)
        kq = [-5, 0, 0, -5, 10]
        lenh = [{'id': i, 'ma': 'X', 'chieu': 'MUA', 'lot': 0.1, 'mo': (base + timedelta(hours=i)).isoformat(), 'dong': (base + timedelta(hours=i, minutes=30)).isoformat(),
                 'phut': 30, 'lai': r, 'phi': 0, 'swap': 0, 'rong': r, 'sl': None, 'r': None, 'nguon': 'Đặt tay'} for i, r in enumerate(kq)]
        t = H.phan_tich(lenh, 1000)['tong']
        self.assertEqual((t['thua'], t['chuoi_thua'], t['chuoi_thang']), (2, 2, 1))

    def test_minh_hoa_khong_co_lenh_tuong_lai(self):
        for d in range(0, 14):                                                       # đổi ngày chạy: kể cả cuối tuần
            now = datetime(2026, 11, 16, 9, tzinfo=timezone.utc) + timedelta(days=d, hours=d * 5)
            lenh, _ = H.mau(now=now)
            for x in lenh:
                self.assertLessEqual(x['mo'], x['dong'])
                self.assertLess(x['dong'], now.isoformat())
                self.assertGreaterEqual(x['phut'], 0)

    def test_csv(self):
        s = H.csv_lenh(H.mau()[0][:3])
        self.assertTrue(s.startswith('﻿id,ma,chieu'))
        self.assertEqual(len(s.strip().splitlines()), 4)


class MT5Gia:
    ACCOUNT_TRADE_MODE_DEMO, ORDER_TYPE_BUY, ORDER_TYPE_SELL = 0, 0, 1

    def __init__(self, demo=True):
        self.demo, self.goi = demo, []

    def account_info(self):
        return SimpleNamespace(trade_mode=0 if self.demo else 2, balance=928.0, currency='USD', login=12345678, server='Demo-1')

    def history_deals_get(self, a, b):
        self.goi.append('history_deals_get')
        return mau_deals()

    def history_orders_get(self, a, b):
        self.goi.append('history_orders_get')
        return ORDERS

    def order_calc_profit(self, kieu, ma, lot, vao, ra):
        self.goi.append('order_calc_profit')
        return (ra - vao) * lot * 100000 * (1 if kieu == 0 else -1)


class TrangTest(unittest.TestCase):
    def setUp(self):
        self.goc = tai_khoan._mt5
        H._nho.clear()

    def tearDown(self):
        tai_khoan._mt5 = self.goc
        H._nho.clear()
        trang.MIEN_TRU = trang.MIEN_TRU_GOC

    def test_doc_mt5_gia_chi_ham_doc(self):
        m = MT5Gia()
        tai_khoan._mt5 = lambda g: m
        r = H.lay({'gia': {}}, 0)
        self.assertTrue(r['san_sang'])
        self.assertEqual(r['tai_khoan']['so'], '•••678')
        self.assertEqual(r['tong']['n'], 2)
        self.assertAlmostEqual(r['tong']['so_du_dau'], 1000.0)
        self.assertLessEqual(set(m.goi), {'history_deals_get', 'history_orders_get', 'order_calc_profit'})

    def test_tu_choi_tai_khoan_that_tru_khi_cho_phep(self):
        m = MT5Gia(demo=False)
        tai_khoan._mt5 = lambda g: m
        self.assertFalse(H.lay({'gia': {}}, 0)['san_sang'])
        H._nho.clear()
        self.assertTrue(H.lay({'gia': {'mt5': {'chi_demo': False}}}, 0)['san_sang'])

    def test_khong_nho_ket_qua_loi(self):
        tai_khoan._mt5 = lambda g: None                                              # chưa nối MT5
        self.assertFalse(H.lay({'gia': {}}, 0)['san_sang'])
        m = MT5Gia()
        tai_khoan._mt5 = lambda g: m                                                 # vừa nối xong: lần gọi kế tiếp phải thấy ngay
        self.assertTrue(H.lay({'gia': {}}, 0)['san_sang'])

    def test_duong_dan_web(self):
        m = MT5Gia()
        tai_khoan._mt5 = lambda g: m
        with tempfile.TemporaryDirectory() as d:
            ch = Path(d) / 'cau-hinh.json'
            ch.write_text(json.dumps({'ten': 'Thử', 'gia': {}}), encoding='utf-8')
            srv = web.tao_may_chu(str(ch), port=0)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            u = f'http://127.0.0.1:{srv.server_address[1]}'
            try:
                html = urllib.request.urlopen(u + '/hieu-suat').read().decode('utf-8')
                self.assertIn('Phân tích hiệu suất giao dịch', html)
                self.assertIn('aria-current="page"', html)
                j = json.loads(urllib.request.urlopen(u + '/api/hieu-suat?ngay=0&chieu=MUA').read())
                self.assertEqual(j['tong']['n'], 1)
                j = json.loads(urllib.request.urlopen(u + '/api/hieu-suat?ngay=30&mau=1').read())
                self.assertTrue(j['mau'])
                r = urllib.request.urlopen(u + '/api/hieu-suat.csv?ngay=0')
                self.assertIn('text/csv', r.headers['Content-Type'])
                self.assertEqual(len(r.read().decode('utf-8-sig').strip().splitlines()), 3)
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(u + '/api/hieu-suat?ngay=abc')
            finally:
                srv.shutdown()
                srv.server_close()


if __name__ == '__main__':
    unittest.main()
