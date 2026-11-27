"""Bài kiểm cho Kế hoạch vốn và lệnh (ke_hoach.py: hàm thuần) và đường dẫn /ke-hoach."""
from functools import partial
from http_owner import owner_urlopen
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import ke_hoach as K, trang, web  # noqa: E402


class VonTest(unittest.TestCase):
    def test_muc_can_bang(self):
        kh = K.ke_hoach_von(1000, 'can_bang')
        self.assertEqual((kh['rui_ro_tien'], kh['lo_ngay_tien'], kh['tong_mo_tien'], kh['so_lenh_cung_luc'], kh['so_lenh_thua_ngay']), (10.0, 30.0, 40.0, 4, 3))
        self.assertEqual((kh['thua_lien_mat_20'], kh['thua_lien_mat_50']), (23, 69))     # 0,99^23 < 0,8; 0,99^69 < 0,5

    def test_tu_dat_va_loi(self):
        kh = K.ke_hoach_von(500, rui_ro_pct=60)
        self.assertEqual((kh['muc'], kh['thua_lien_mat_50'], kh['lo_ngay_pct']), ('tu_dat', 1, 100.0))
        for bad in ((0, 'can_bang', None), (100, 'can_bang', 0), (100, 'can_bang', 150)):
            with self.assertRaises(ValueError):
                K.ke_hoach_von(*bad)

    def test_mo_phong(self):
        a = K.mo_phong(1, 50, 2, so_lenh=100, lan=500)
        b = K.mo_phong(1, 50, 2, so_lenh=100, lan=500)
        self.assertEqual(a, b)                                                  # cùng hạt giống: cùng kết quả
        self.assertEqual((a['ky_vong_r'], a['hoa_von_pct']), (0.5, 33.3))
        self.assertGreater(a['trung_vi_pct'], 0)
        self.assertEqual(a['xs_sut_50'], 0.0)
        c = K.mo_phong(10, 50, 1, so_lenh=100, lan=500)                         # rủi ro 10% không có lợi thế: hay sụt nặng
        self.assertGreater(c['xs_sut_50'], 50)
        self.assertLess(c['trung_vi_pct'], 0)
        with self.assertRaises(ValueError):
            K.mo_phong(0, 50, 2)


class MucTest(unittest.TestCase):
    # đáy fractal ở 95 (vị trí 3), đỉnh fractal ở 110 (vị trí 8); giá đang 100
    CAO = [101, 102, 101, 100, 102, 104, 106, 108, 110, 107, 105, 103, 102]
    THAP = [99, 98, 97, 95, 97, 99, 101, 103, 105, 102, 100, 99, 98]

    def test_mua_cau_truc(self):
        m = K.goi_y_muc('MUA', 100.0, self.CAO, self.THAP, atr=4.0, spread=0.2, so_le=2)
        self.assertEqual(m['chon'], 'cau_truc')                                 # 5,6 giá = 1,4 ATR: trong khoảng 0,5–3 ATR
        self.assertAlmostEqual(m['sl']['cau_truc']['gia'], 94.4)                # 95 − (0,2 + 0,4)
        self.assertAlmostEqual(m['sl']['bien_dong']['gia'], 94.0)
        tp = {t['k']: t for t in m['tp']}
        self.assertAlmostEqual(tp['2R']['gia'], 111.2)
        self.assertEqual(tp['cau_truc']['gia'], 110)

    def test_ban_va_qua_xa_thi_theo_bien_dong(self):
        m = K.goi_y_muc('BAN', 100.0, self.CAO, self.THAP, atr=1.0, spread=0.0, so_le=2)
        self.assertEqual(m['chon'], 'bien_dong')                                # đỉnh 110 cách 10,1 ATR: quá xa
        self.assertAlmostEqual(m['sl']['bien_dong']['gia'], 101.5)
        self.assertEqual({t['k'] for t in m['tp']}, {'1R', '2R', '3R', 'cau_truc'})

    def test_khong_co_nen(self):
        m = K.goi_y_muc('MUA', 100.0, [], [], atr=None)
        self.assertEqual((m['chon'], m['tp']), (None, []))
        with self.assertRaises(ValueError):
            K.goi_y_muc('LEN', 1, [], [], None)


class LenhTest(unittest.TestCase):
    def test_lot_va_ky_quy(self):
        l = K.tinh_lenh(10000, 1, 3500, 3490, [3510, 3520], gt1=100, ky_quy_1lot=3500, dung_lenh_pct=50)
        self.assertEqual((l['lot'], l['rui_ro_tien'], l['rui_ro_that_pct'], l['duoi_lot_min']), (0.1, 100.0, 1.0, False))
        self.assertEqual([t['lai_tien'] for t in l['tp']], [100.0, 200.0])
        self.assertEqual((l['ky_quy'], l['ky_quy_pct']), (350.0, 3.5))
        self.assertAlmostEqual(l['kc_dung_lenh'], (10000 - 175) / 10)            # còn 9.825 USD trước khi sàn đóng lệnh
        self.assertFalse(l['dung_lenh_truoc_sl'])

    def test_von_nho_duoi_lot_min_va_dung_lenh_truoc_sl(self):
        l = K.tinh_lenh(300, 1, 3500, 3425, [3650], gt1=100, ky_quy_1lot=3500, dung_lenh_pct=50)
        self.assertTrue(l['duoi_lot_min'])
        self.assertEqual(l['lot'], 0.01)
        self.assertEqual((l['rui_ro_tien'], l['rui_ro_that_pct']), (75.0, 25.0))
        l = K.tinh_lenh(300, 50, 3500, 3200, [], gt1=100, ky_quy_1lot=3500, dung_lenh_pct=50)
        self.assertTrue(l['dung_lenh_truoc_sl'])                                 # lỗ 300 giá × 0,01 lot > vốn còn trước mức đóng lệnh

    def test_loi(self):
        with self.assertRaises(ValueError):
            K.tinh_lenh(100, 1, 10, 10, [], gt1=1)


class LapTest(unittest.TestCase):
    """lap() với bảng giá và MT5 giả: vốn nhỏ phải vào lot tối thiểu thì mô phỏng theo rủi ro thật."""

    class Bang:
        import threading as _t
        _dk = _t.Lock()
        dac_ta = {'XAU': {'goc': 'XAUUSD', 'so_le': 2, 'diem': 0.01, 'gt1': 100.0, 'lot_min': 0.01, 'lot_buoc': 0.01, 'lot_max': 50, 'ky_quy_1lot': 3500.0,
                          'muc_dung': 0}}
        gia = {'XAU': [3500.0, 3500.3, 0]}
        kt = {'XAU': {'H1': {'atr': 20.0}}}
        tai_khoan = {'tien': 'USD', 'don_bay': 100, 'dung_lenh': 50.0}

        def _cfg(self):
            return {}, {}

        def _mt5_fn(self, g):
            return None

    def test_von_nho(self):
        kq = K.lap({}, self.Bang(), 'XAU', 'MUA', 'H1', von=300.0)
        self.assertEqual((kq['vao'], kq['muc']['chon'], kq['lenh']['lot'], kq['lenh']['duoi_lot_min']), (3500.3, 'bien_dong', 0.01, True))
        self.assertEqual(kq['mo_phong']['theo_rui_ro_that'], 10.0)                # 30 giá × 100 × 0,01 = 30 USD = 10% của 300
        self.assertEqual(kq['lenh']['thua_lien_mat_50'], 7)
        self.assertIn('chưa đọc được nến từ MT5', kq['thieu'])
        self.assertNotIn('theo_rui_ro_that', K.lap({}, self.Bang(), 'XAU', 'MUA', 'H1', von=100000.0)['mo_phong'])

    def test_ma_khong_so_le_va_san_dong_lenh_bang_tien(self):
        b = self.Bang()
        b.dac_ta = {'IDX': {**self.Bang.dac_ta['XAU'], 'goc': 'IDX', 'so_le': 0, 'diem': 1.0, 'gt1': 1.0}}
        b.gia, b.kt = {'IDX': [20000.0, 20001.0, 0]}, {'IDX': {'H1': {'atr': 33.3}}}
        kq = K.lap({}, b, 'IDX', 'MUA', 'H1', von=10000.0)
        self.assertEqual(kq['so_le'], 0)
        self.assertEqual(kq['muc']['sl']['bien_dong']['gia'], 19951.0)                      # 20001 − 49,95 làm tròn tới đơn vị, không thành 2 số lẻ
        self.assertIsNotNone(kq['lenh']['kc_dung_lenh'])
        b.tai_khoan = {**self.Bang.tai_khoan, 'dung_lenh_tien': True}
        self.assertNotIn('kc_dung_lenh', K.lap({}, b, 'IDX', 'MUA', 'H1', von=10000.0)['lenh'])

    def test_loi(self):
        with self.assertRaises(ValueError):
            K.lap({}, self.Bang(), 'XAU', 'MUA', 'D1', von=100.0)
        with self.assertRaises(ValueError):
            K.lap({}, self.Bang(), 'KHONG', 'MUA', 'H1', von=100.0)
        with self.assertRaises(ValueError):
            K.lap({}, self.Bang(), 'XAU', 'MUA', 'H1', von=100.0, sl=3600.0)       # dừng lỗ sai phía


class WebTest(unittest.TestCase):
    def test_duong_dan(self):
        with tempfile.TemporaryDirectory() as d:
            ch = Path(d) / 'cau-hinh.json'
            ch.write_text(json.dumps({'gia': {}}), encoding='utf-8')
            srv = web.tao_may_chu(str(ch), port=0)
            open_owner = partial(owner_urlopen, root=ch.parent)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            u = f'http://127.0.0.1:{srv.server_address[1]}'
            try:
                html = open_owner(u + '/ke-hoach', timeout=30).read().decode('utf-8')
                self.assertIn('Kế hoạch vốn và lệnh', html)
                self.assertIn('aria-current="page"', html)
                for q in ('chieu=MUA', 'ma=X&chieu=LEN', 'ma=X&chieu=MUA&khung=D1', 'ma=X&chieu=MUA&von=-5', 'ma=X&chieu=MUA&rui_ro=0',
                          'ma=X&chieu=MUA&thang=150', 'ma=X&chieu=MUA&vao=abc', 'ma=X&chieu=MUA&von=inf', 'ma=X&chieu=MUA&von=1e999',
                          'ma=X&chieu=MUA&sl=nan', 'ma=X&chieu=MUA&rr=inf'):
                    with self.assertRaises(urllib.error.HTTPError) as c:
                        open_owner(f'{u}/api/ke-hoach?{q}', timeout=30)
                    self.assertEqual(c.exception.code, 400, q)
            finally:
                srv.shutdown()
                srv.server_close()
                trang.MIEN_TRU = trang.MIEN_TRU_GOC


if __name__ == '__main__':
    unittest.main()
