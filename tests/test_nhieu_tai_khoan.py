# -*- coding: utf-8 -*-
"""Các tài khoản đã nối (so_cong_khai.nhieu_tai_khoan, doc_mot_tai_khoan). Mọi bài dùng MT5 GIẢ và danh sách tiến trình giả: không nối MT5 thật.
Kiểm: chỉ nối MT5 đang mở; đọc được tài khoản tiền thật nhưng chỉ đọc (MT5 giả không có hàm đặt lệnh nào, gọi tới là lỗi); che số tài khoản; rủi ro
nếu mọi dừng lỗ bị chạm; danh sách chỉ lưu đường dẫn, không có mật khẩu; tổng theo loại tiền."""
from functools import partial
from http_owner import owner_urlopen
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS

from so_cong_khai import doc_mot_tai_khoan as DM, nhieu_tai_khoan as NT

T5 = r'C:\MT5 Thu\terminal64.exe'


class _Mt5Gia:
    """Chỉ có hàm đọc; mọi lời gọi khác (order_send, positions_close…) sẽ ném AttributeError."""
    ORDER_TYPE_BUY, ORDER_TYPE_SELL, ACCOUNT_TRADE_MODE_DEMO = 0, 1, 0

    def __init__(self, mode=2):
        self.mode, self.goi, self.dong = mode, [], 0

    def initialize(self, path):
        self.goi.append(path)
        return True

    def shutdown(self):
        self.dong += 1

    def last_error(self):
        return (1, 'ok')

    def terminal_info(self):
        return NS(connected=True, path=str(Path(T5).parent))

    def account_info(self):
        return NS(login=12345678, server='Exness-Real9', trade_mode=self.mode, currency='USD', balance=1000.0, equity=990.0, profit=-10.0, margin=50.0,
                  margin_free=940.0, margin_level=1980.0, leverage=500)

    def positions_get(self):
        return [NS(symbol='XAUUSD', type=0, volume=0.1, price_open=3500.0, sl=3480.0, tp=3540.0, profit=-10.0),
                NS(symbol='EURUSD', type=1, volume=0.2, price_open=1.1, sl=0.0, tp=0.0, profit=0.0)]

    def order_calc_profit(self, kieu, ma, lot, vao, ra):
        return (ra - vao) * lot * 100 if kieu == 0 else (vao - ra) * lot * 100

    def history_deals_get(self, a, b):
        return []

    def history_orders_get(self, a, b):
        return []


def _procs(*duong):
    return lambda: [('terminal64.exe', 10 + i, d) for i, d in enumerate(duong)]


class DocMot(unittest.TestCase):
    def test_doc_tai_khoan_that_chi_doc(self):
        m = _Mt5Gia(mode=2)
        kq = DM.doc_tu(m, T5, 90, datetime(2026, 11, 25, tzinfo=timezone.utc), procs_fn=_procs(T5), window_fn=lambda pid: True, sleep=lambda s: None)
        self.assertTrue(kq['ok'])
        self.assertEqual((kq['tai_khoan']['loai'], kq['tai_khoan']['that'], kq['tai_khoan']['so']), ('TIỀN THẬT', True, '•••678'))
        self.assertNotIn('12345678', json.dumps(kq))                       # số tài khoản được che
        self.assertEqual(kq['rui_ro'], {'tong': 200.0, 'pct': 20.2, 'khong_sl': 1, 'khong_tinh': 0})   # 0,1 lot × 20 giá × 100
        self.assertEqual((len(kq['lenh_mo']), kq['tong']), (2, None))
        self.assertEqual((m.goi, m.dong), ([T5], 1))                      # nối đúng MT5 đó rồi ngắt

    def test_mt5_chua_mo_thi_khong_noi(self):
        m = _Mt5Gia()
        kq = DM.doc_tu(m, T5, procs_fn=_procs(r'D:\Khac\terminal64.exe'), window_fn=lambda pid: True, sleep=lambda s: None)
        self.assertFalse(kq['ok'])
        self.assertIn('chưa mở', kq['ly_do'])
        self.assertEqual(m.goi, [])                                       # không gọi initialize: không bao giờ tự mở MT5

    def test_doc_mot_qua_tien_trinh_rieng(self):
        def chay(lenh, **k):
            self.assertIn('so_cong_khai.doc_mot_tai_khoan', lenh)
            return NS(stdout='dòng rác\n{"ok": true, "von": 1.0}\n', stderr='')
        self.assertEqual(NT.doc_mot(T5, 30, chay), {'ok': True, 'von': 1.0})
        self.assertFalse(NT.doc_mot(T5, 30, lambda *a, **k: NS(stdout='', stderr='lỗi'))['ok'])


class DanhSach(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name) / 'tk.json'
        NT._nho.clear()

    def tearDown(self):
        self.tmp.cleanup()
        NT._nho.clear()
        NT._mo.update(luc=0.0, ds=None)

    def test_them_chi_mt5_dang_mo_va_khong_trung(self):
        ok, nhan = NT.them(r'D:\Khac\terminal64.exe', 'X', self.p, procs_fn=_procs(T5))
        self.assertFalse(ok)
        self.assertIn('đang mở', nhan)
        self.assertTrue(NT.them(T5, '  Exness   thật  ', self.p, procs_fn=_procs(T5))[0])
        self.assertFalse(NT.them(T5.upper(), 'Lần hai', self.p, procs_fn=_procs(T5))[0])
        ds = json.loads(self.p.read_text(encoding='utf-8'))
        self.assertEqual([(x['id'], x['ten'], x['duong']) for x in ds], [(1, 'Exness thật', T5)])
        self.assertEqual(set(ds[0]), {'id', 'ten', 'duong', 'them_luc'})   # không có mật khẩu hay số tài khoản
        self.assertTrue(NT.xoa(1, self.p)[0])
        self.assertEqual(json.loads(self.p.read_text(encoding='utf-8')), [])

    def test_xem_cong_tong_theo_loai_tien(self):
        NT.them(T5, 'A', self.p, procs_fn=_procs(T5, r'C:\MT5 B\terminal64.exe'))
        NT.them(r'C:\MT5 B\terminal64.exe', 'B', self.p, procs_fn=_procs(T5, r'C:\MT5 B\terminal64.exe'))
        doc = lambda that, von, rr: {'ok': True, 'tai_khoan': {'tien': 'USD', 'that': that}, 'von': von, 'treo': 1.0, 'rui_ro': {'tong': rr}, 'lenh_mo': [1],   # noqa: E731
                                     'tong': {'rong': 5.0}}
        NT._nho.update({1: doc(True, 1000.0, 50.0), 2: doc(False, 3000.0, 30.0)})
        NT._mo.update(luc=9e18, ds=[T5])                                  # không đọc tiến trình thật trong bài kiểm
        x = NT.xem(self.p)
        self.assertEqual(x['tong']['USD'], {'von': 4000.0, 'treo': 2.0, 'rui_ro': 80.0, 'lenh_mo': 2, 'so_tk': 2, 'that': 1, 'rong': 10.0, 'rui_ro_pct': 2.0})
        self.assertEqual(x['mt5_chua_them'], [])

    def test_trang(self):
        h = NT.trang_cac_tai_khoan('Thử')
        for must in ('Các tài khoản đã nối', 'Chỉ đọc', 'không hỏi hay lưu mật khẩu', "'X-So-Cong-Khai':'1'"):
            self.assertIn(must, h)


if __name__ == '__main__':
    unittest.main()


class WebPost(unittest.TestCase):
    """POST /api/cac-tai-khoan phải có tiêu đề riêng X-So-Cong-Khai, để trang web khác không tự thêm hay bỏ tài khoản được."""

    def test_thieu_tieu_de_thi_tu_choi(self):
        import threading
        import urllib.error
        import urllib.request
        from so_cong_khai import web
        with tempfile.TemporaryDirectory() as d:
            cfgp = Path(d) / 'c.json'
            cfgp.write_text(json.dumps({'ten': 'Thử', 'thu_muc_ra': str(Path(d) / 'out'), 'gia': {}}), encoding='utf-8')
            srv = web.tao_may_chu(str(cfgp), port=0)
            open_owner = partial(owner_urlopen, root=cfgp.parent)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                url = f'http://127.0.0.1:{srv.server_address[1]}/api/cac-tai-khoan'
                yc = urllib.request.Request(url, data=b'{"viec":"xoa","id":1}', method='POST', headers={'Content-Type': 'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as e:
                    open_owner(yc, timeout=10)
                self.assertEqual(e.exception.code, 403)                     # thiếu tiêu đề riêng: mọi lệnh POST bị từ chối (xem test_bao_mat)
                yc2 = urllib.request.Request(url, data=b'{"viec":"la"}', method='POST', headers={'Content-Type': 'application/json', 'X-So-Cong-Khai': '1'})
                with self.assertRaises(urllib.error.HTTPError) as e2:
                    open_owner(yc2, timeout=10)
                self.assertEqual(e2.exception.code, 400)                    # có tiêu đề nhưng việc không hợp lệ
            finally:
                srv.shutdown()
                srv.server_close()
