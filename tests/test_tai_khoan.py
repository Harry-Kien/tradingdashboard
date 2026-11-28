"""Bài kiểm cho trang Tài khoản: dùng một MT5 giả. Kiểm số liệu, rủi ro tới SL, việc che số tài khoản, và rằng mô-đun chỉ đọc."""
from functools import partial
from http_owner import owner_urlopen
import json
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import tai_khoan, trang, web  # noqa: E402

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
T = int(NOW.timestamp())


class MT5Gia:
    ACCOUNT_TRADE_MODE_DEMO = 0

    def __init__(self, che_do=0):
        self.che_do = che_do
        self.goi = []

    def __getattr__(self, ten):                                    # mọi hàm khác bị gọi tới đều làm bài kiểm hỏng
        raise AssertionError(f'mô-đun gọi hàm MT5 không được phép: {ten}')

    def account_info(self):
        self.goi.append('account_info')
        return N(login=987654313, trade_mode=self.che_do, leverage=100, balance=1000.0, equity=1040.0, profit=40.0, margin=70.0, margin_free=970.0,
                 margin_level=1485.7, currency='USD', server='May-Chu-Thu', name='TEN KHONG DUOC HIEN')

    def symbol_info(self, ten):
        self.goi.append('symbol_info')
        return {'XAUUSDp': N(digits=2, trade_contract_size=100.0, currency_profit='USD'),
                'USDJPYp': N(digits=3, trade_contract_size=100000.0, currency_profit='JPY')}[ten]

    def positions_get(self):
        self.goi.append('positions_get')
        return (N(symbol='XAUUSDp', type=1, volume=0.02, price_open=3600.0, sl=3620.0, tp=3560.0, price_current=3580.0, profit=40.0, swap=-0.2, time=T - 3600, magic=20261026),
                N(symbol='XAUUSDp', type=0, volume=0.01, price_open=3500.0, sl=3510.0, tp=0.0, price_current=3580.0, profit=80.0, swap=0.0, time=T - 7200, magic=0),
                N(symbol='XAUUSDp', type=0, volume=0.01, price_open=3570.0, sl=0.0, tp=0.0, price_current=3580.0, profit=10.0, swap=0.0, time=T - 600, magic=555),
                N(symbol='USDJPYp', type=0, volume=0.10, price_open=158.0, sl=157.5, tp=0.0, price_current=158.2, profit=12.0, swap=0.0, time=T - 600, magic=0))

    def orders_get(self):
        self.goi.append('orders_get')
        return (N(symbol='XAUUSDp', type=3, volume_current=0.01, price_open=3650.0, sl=3670.0, tp=0.0, time_setup=T - 100, magic=20261030),)

    def history_deals_get(self, a, b):
        self.goi.append('history_deals_get')
        d = lambda **k: N(**{'commission': 0.0, 'swap': 0.0, 'fee': 0.0, 'magic': 20261026, 'symbol': 'XAUUSDp', 'comment': '', 'volume': 0.01, 'price': 3500.0, **k})   # noqa: E731
        return (d(time=T - 86400 * 3, type=2, entry=0, profit=1000.0, comment='nap', symbol=''),
                d(time=T - 86400 * 3 + 5, type=5, entry=0, profit=-100.0, comment='dieu chinh', symbol=''),
                d(time=T - 86400 * 2, type=0, entry=0, profit=0.0),                                  # khớp MỞ: không tính
                d(time=T - 86400 * 2 + 600, type=1, entry=1, profit=30.0, commission=-0.5, swap=-0.1),   # đóng lệnh MUA, lãi ròng 29,40
                d(time=T - 86400, type=0, entry=1, profit=-20.0, commission=-0.5),                       # đóng lệnh BÁN, lỗ ròng 20,50
                d(time=T - 3000, type=1, entry=1, profit=5.0))


class TaiKhoanTest(unittest.TestCase):
    def setUp(self):
        self.that = tai_khoan._mt5
        self.mt5 = MT5Gia()
        tai_khoan._mt5 = lambda g: self.mt5
        self.cfg = {'ten': 'Thử', 'gia': {}, 'mt5_xem': {'magic': {'555': 'EA thử'}}}

    def tearDown(self):
        tai_khoan._mt5 = self.that

    def test_so_lieu_tai_khoan(self):
        r = tai_khoan.doc(self.cfg, NOW)
        self.assertTrue(r['san_sang'])
        self.assertEqual((r['so_du'], r['von'], r['treo'], r['ky_quy'], r['ky_quy_con'], r['muc_ky_quy'], r['don_bay'], r['tien']), (1000.0, 1040.0, 40.0, 70.0, 970.0, 1485.7, 100, 'USD'))
        self.assertEqual((r['loai'], r['so']), ('DEMO', '•••313'))
        chu = json.dumps(r, ensure_ascii=False)
        self.assertNotIn('987654313', chu)                                                           # số tài khoản đầy đủ không ra ngoài
        self.assertNotIn('TEN KHONG DUOC HIEN', chu)                                                 # tên chủ tài khoản cũng không

    def test_lenh_mo_va_rui_ro(self):
        r = tai_khoan.doc(self.cfg, NOW)
        self.assertEqual([(p['ma'], p['huong'], p['nguon']) for p in r['lenh']],
                         [('XAUUSDp', 'BAN', 'EA E'), ('XAUUSDp', 'MUA', 'Đặt tay'), ('XAUUSDp', 'MUA', 'EA thử'), ('USDJPYp', 'MUA', 'Đặt tay')])
        # lệnh 1: BÁN 0,02 lot, SL cách 20 giá: 20 × 0,02 × 100 = 40. Lệnh 2: SL đã kéo qua giá vào: 0. Lệnh 3: không có SL. Lệnh 4: lãi lỗ tính bằng JPY, chưa cộng.
        self.assertEqual([p['rui_ro'] for p in r['lenh']], [40.0, 0.0, None, None])
        self.assertEqual(r['rui_ro'], {'tong': 40.0, 'pct': 3.85, 'khong_sl': 1, 'khong_tinh': 1})
        self.assertEqual((r['lenh'][2]['sl'], r['lenh'][3]['so_le'], r['lenh'][3]['vao']), (None, 3, 158.0))
        self.assertEqual([(o['loai'], o['nguon'], o['gia']) for o in r['cho']], [('BÁN giới hạn', 'EA BB', 3650.0)])

    def test_lich_su_chi_tinh_lan_khop_dong(self):
        r = tai_khoan.doc(self.cfg, NOW)
        self.assertEqual(r['tom'], {'ngay': 30, 'n': 3, 'thang': 2, 'thua': 1, 'tong': 13.9, 'lai_gop': 34.4, 'lo_gop': -20.5})
        self.assertEqual([(x['huong'], x['lai']) for x in r['da_dong']], [('MUA', 5.0), ('BAN', -20.5), ('MUA', 29.4)])      # mới nhất trước; khớp BÁN là đóng lệnh MUA
        self.assertEqual([(x['loai'], x['tien']) for x in r['nap_rut']], [('Nạp hoặc rút', 1000.0), ('Điều chỉnh', -100.0)])
        self.assertAlmostEqual(sum(d['lai'] for d in r['theo_ngay']), 13.9, places=6)

    def test_chi_goi_ham_doc(self):
        tai_khoan.doc(self.cfg, NOW)
        self.assertEqual(set(self.mt5.goi), {'account_info', 'symbol_info', 'positions_get', 'orders_get', 'history_deals_get'})
        src = Path(tai_khoan.__file__).read_text(encoding='utf-8')
        for banned in ('order_send', 'order_check', 'TRADE_ACTION', 'symbol_select(', 'login(', 'password'):
            self.assertNotIn(banned, src)

    def test_tai_khoan_khong_phai_demo_thi_tu_choi(self):
        self.mt5 = MT5Gia(che_do=2)
        r = tai_khoan.doc(self.cfg, NOW)
        self.assertFalse(r['san_sang'])
        self.assertIn('không phải tài khoản demo', r['ly_do'])
        self.assertEqual(self.mt5.goi, ['account_info'])                                             # không đọc thêm gì của tài khoản đó
        self.assertNotIn('so_du', r)

    def _tom(self, **kw):
        g = lambda giay: datetime.fromtimestamp(T + giay, timezone.utc)                              # noqa: E731
        rows = [{'ea': 'EA E', 'side': 'BUY', 'lots': 0.01, 'opened': g(-86400 * 2 - 100), 'closed_at': g(-86400 * 2 + 630), 'pnl': 29.4},      # MT5 đóng lệch 30 giây
                {'ea': 'EA E', 'side': 'SELL', 'lots': 0.01, 'opened': g(-86400 - 500), 'closed_at': g(-86400 + 20), 'pnl': -20.5}]
        return {'rows': rows, 'orphans': [{'side': 'BUY', 'lots': 0.01, 'opened': g(-4000)}], 'opens': [], 'equity_change': 53.9, **kw}

    def test_doi_chieu_tim_lenh_thieu_va_khop_von(self):
        dc = tai_khoan.doi_chieu(self.cfg, {'EA E'}, self._tom(), NOW)
        # MT5 có 3 lệnh đã đóng của EA E (+29,40, −20,50, +5,00); nhật ký chỉ có 2. Vốn đổi 53,90 = 13,90 đã chốt + 40,00 đang treo.
        self.assertEqual((dc['n_nhat_ky'], dc['n_mt5'], dc['so_cap'], dc['tong_mt5'], dc['tong_nhat_ky']), (2, 3, 2, 13.9, 8.9))
        self.assertEqual([(x['huong'], x['lai']) for x in dc['thieu_nhat_ky']], [('MUA', 5.0)])
        self.assertEqual((dc['thieu_mt5'], dc['lech_cap'], dc['treo'], dc['nap_rut']), ([], [], 40.0, 0.0))  # nạp và điều chỉnh xảy ra trước lệnh đầu nên không tính
        self.assertEqual((dc['con_lech'], dc['khop']), (0.0, True))
        html = trang._doi_chieu_html(dc)
        for must in ('Đối chiếu với lịch sử MT5', 'Đã khớp', 'Nhật ký của EA thiếu dòng đóng của 1 lệnh', '+5,00'):
            self.assertIn(must, html)
        json.dumps(dc)

    def test_doi_chieu_khi_khong_khop_hoac_khac_tai_khoan(self):
        dc = tai_khoan.doi_chieu(self.cfg, {'EA E'}, self._tom(equity_change=100.0), NOW)
        self.assertEqual((dc['khop'], dc['con_lech']), (False, 46.1))
        self.assertIn('Còn lệch +46,10 USD', trang._doi_chieu_html(dc))
        tom = self._tom()
        tom['rows'][0]['lots'] = 0.05                                                                # khối lượng khác: không ghép, báo thiếu ở cả hai phía
        dc = tai_khoan.doi_chieu(self.cfg, {'EA E'}, tom, NOW)
        self.assertEqual((dc['so_cap'], len(dc['thieu_mt5']), len(dc['thieu_nhat_ky'])), (1, 1, 2))
        self.assertIsNone(tai_khoan.doi_chieu(self.cfg, {'EA khác'}, self._tom(), NOW))              # MT5 đang nối không có lệnh của EA này
        self.mt5 = MT5Gia(che_do=2)
        self.assertIsNone(tai_khoan.doi_chieu(self.cfg, {'EA E'}, self._tom(), NOW))                 # không phải demo thì không đọc

    def test_chua_noi_mt5(self):
        tai_khoan._mt5 = lambda g: None
        self.assertFalse(tai_khoan.doc(self.cfg, NOW)['san_sang'])

    def test_loi_doc_khong_duoc_bien_thanh_khong_co_lenh(self):
        for method in ('positions_get', 'orders_get', 'history_deals_get'):
            with self.subTest(method=method), patch.object(self.mt5, method, return_value=None):
                result = tai_khoan.doc(self.cfg, NOW)
                self.assertFalse(result['san_sang'])
                self.assertNotIn('lenh', result)
                self.assertNotIn('rui_ro', result)
        with patch.object(self.mt5, 'history_deals_get', return_value=None):
            self.assertIsNone(tai_khoan.lich_su(self.cfg, NOW, NOW))
            self.assertIsNone(tai_khoan.doi_chieu(self.cfg, {'EA E'}, self._tom(), NOW))

    def test_doi_chieu_dung_so_cuoi_va_khong_ghep_cheo_ea_ma(self):
        self.assertIsNone(tai_khoan.doi_chieu(self.cfg, {'EA E'}, self._tom(), NOW, so_cuoi='999'))
        self.assertIsNotNone(tai_khoan.doi_chieu(self.cfg, {'EA E'}, self._tom(), NOW, so_cuoi='313'))
        for field, value in (('ea', 'EA M'), ('ma', 'EURUSDp')):
            tom = self._tom()
            tom['rows'][0][field] = value
            result = tai_khoan.doi_chieu(self.cfg, {'EA E'}, tom, NOW)
            self.assertEqual(result['so_cap'], 1)
            self.assertEqual(len(result['thieu_mt5']), 1)

    def test_tu_choi_anh_chup_lan_hai_tai_khoan(self):
        original = self.mt5.account_info()
        changed = N(**{**vars(original), 'login': 555555})
        with patch.object(self.mt5, 'account_info', side_effect=[original, changed]):
            result = tai_khoan.doc(self.cfg, NOW)
            self.assertFalse(result['san_sang'])
            self.assertNotIn('von', result)
        with patch.object(self.mt5, 'account_info', side_effect=[original, changed]):
            self.assertIsNone(tai_khoan.lich_su(self.cfg, NOW, NOW))

    def test_trang_va_duong_dan(self):
        html = tai_khoan.trang_tai_khoan('Thử')
        for must in ('Tài khoản MT5', 'Chỉ đọc', '/api/tai-khoan', 'href="/tai-khoan"', 'aria-current="page"', 'không phải lời khuyên đầu tư'):
            self.assertIn(must, html)
        self.assertIn('href="/tai-khoan"', trang.thanh_dau('Thử', 'tong'))
        with tempfile.TemporaryDirectory() as tmp:
            cfgp = Path(tmp) / 'c.json'
            cfgp.write_text(json.dumps({**self.cfg, 'thu_muc_ra': str(Path(tmp) / 'out')}), encoding='utf-8')
            srv = web.tao_may_chu(str(cfgp), port=0)
            open_owner = partial(owner_urlopen, root=cfgp.parent)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                goc = f'http://127.0.0.1:{srv.server_address[1]}'
                with open_owner(goc + '/api/tai-khoan', timeout=20) as r:
                    self.assertEqual(json.loads(r.read())['so'], '•••313')
                with open_owner(goc + '/tai-khoan', timeout=20) as r:
                    self.assertIn('Tài khoản MT5', r.read().decode('utf-8'))
            finally:
                srv.shutdown()
                srv.server_close()


if __name__ == '__main__':
    unittest.main()
