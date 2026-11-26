"""Bài kiểm cho Kiểm tra trước khi vào lệnh (kiem_lenh.cham là hàm thuần) và đường dẫn /api/kiem-lenh."""
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import dich, kiem_lenh as K, trang, web  # noqa: E402

NOW = datetime(2026, 11, 25, 6, 0, tzinfo=timezone.utc)
DU = {'von': 10000.0, 'tien': 'USD', 'gia_tri_1_gia_1_lot': 100.0, 'lot_min': 0.01, 'lot_buoc': 0.01, 'lot_max': 50.0,
      'bid': 3500.0, 'ask': 3500.3, 'atr_m15': 6.0, 'tin': [], 'tien_lien_quan': ['USD'], 'now': NOW, 'lo_hom_nay': 0.0,
      'rui_ro_dang_mo': 0.0, 'vi_the': [], 'tuong_quan': {}, 'ky_thuat': {'H1': 0.2, 'H4': 0.1}}
LENH = {'ma': 'XAUUSD', 'chieu': 'MUA', 'vao': 3500.3, 'sl': 3490.3, 'tp': 3520.3, 'rui_ro_pct': 1.0}


def muc(kq, k):
    return next((m for m in kq['muc'] if m['k'] == k), None)


class ChamTest(unittest.TestCase):
    def test_lenh_chuan_dat_va_tinh_dung_khoi_luong(self):
        kq = K.cham(LENH, DU)
        self.assertEqual(kq['ket_luan'], 'dat')
        self.assertAlmostEqual(kq['lot'], 0.1)                                # 1% của 10.000 = 100 USD; 10 giá × 100 USD/lot → 0,1 lot
        self.assertAlmostEqual(kq['rui_ro_tien'], 100.0)
        self.assertEqual((kq['rr'], kq['hoa_von_pct']), (2.0, 33.3))

    def test_khong_co_dung_lo_la_khong_nen(self):
        kq = K.cham({**LENH, 'sl': None}, DU)
        self.assertEqual(kq['ket_luan'], 'khong_nen')
        self.assertEqual(muc(kq, 'sl')['muc'], 'xau')

    def test_dung_lo_sai_phia(self):
        self.assertEqual(K.cham({**LENH, 'sl': 3510.0}, DU)['ket_luan'], 'khong_nen')
        self.assertEqual(K.cham({**LENH, 'chieu': 'BAN', 'vao': 3500.0, 'sl': 3490.0}, DU)['ket_luan'], 'khong_nen')

    def test_tin_manh_sap_ra(self):
        tin = [{'t': (NOW + timedelta(minutes=12)).isoformat(), 'tien': 'USD', 'ten': 'Non-Farm Payrolls'}]
        kq = K.cham(LENH, {**DU, 'tin': tin})
        self.assertEqual(muc(kq, 'tin')['muc'], 'xau')
        self.assertIn('12 phút', muc(kq, 'tin')['vi']['tieu'])
        self.assertIn('in 12 min', muc(kq, 'tin')['en']['tieu'])
        kq = K.cham(LENH, {**DU, 'tin': [{**tin[0], 'tien': 'JPY'}]})        # tin của đồng tiền không liên quan
        self.assertEqual(muc(kq, 'tin')['muc'], 'tot')

    def test_cham_gioi_han_lo_ngay(self):
        kq = K.cham(LENH, {**DU, 'lo_hom_nay': -320.0})
        self.assertEqual(muc(kq, 'ngay')['muc'], 'xau')
        self.assertEqual(kq['ket_luan'], 'khong_nen')

    def test_rui_ro_qua_lon_va_tong_rui_ro(self):
        self.assertEqual(muc(K.cham({**LENH, 'rui_ro_pct': 3.0}, DU), 'rui_ro')['muc'], 'chu_y')
        self.assertEqual(muc(K.cham({**LENH, 'rui_ro_pct': 10.0}, DU), 'rui_ro')['muc'], 'xau')
        self.assertEqual(muc(K.cham(LENH, {**DU, 'rui_ro_dang_mo': 560.0}), 'tong')['muc'], 'xau')   # 5,6% + 1% > 6%

    def test_dung_lo_qua_sat_va_spread(self):
        kq = K.cham({**LENH, 'sl': 3498.3, 'tp': 3504.3}, DU)                  # 2 giá = 0,33 ATR
        self.assertEqual(muc(kq, 'atr')['muc'], 'chu_y')
        kq = K.cham({**LENH, 'sl': 3499.3, 'tp': 3503.3}, {**DU, 'atr_m15': 1.0})   # spread 0,3 trên dừng lỗ 1 = 30%
        self.assertEqual(muc(kq, 'spread')['muc'], 'chu_y')

    def test_vao_gap_sau_lenh_thua_va_cung_mot_cuoc(self):
        kq = K.cham(LENH, {**DU, 'thua_gan_nhat': {'dong': (NOW - timedelta(minutes=5)).isoformat(), 'lot': 0.1}})
        self.assertEqual(muc(kq, 'gap')['muc'], 'chu_y')
        kq = K.cham(LENH, {**DU, 'vi_the': [{'ma': 'XAGUSD', 'chieu': 'MUA'}], 'tuong_quan': {'XAGUSD': 0.85}})
        self.assertEqual(muc(kq, 'tq')['muc'], 'chu_y')
        kq = K.cham(LENH, {**DU, 'vi_the': [{'ma': 'XAGUSD', 'chieu': 'BAN'}], 'tuong_quan': {'XAGUSD': 0.85}})   # ngược chiều: phòng hộ
        self.assertIsNone(muc(kq, 'tq'))

    def test_nguoc_ky_thuat_manh_hai_khung(self):
        kq = K.cham(LENH, {**DU, 'ky_thuat': {'H1': -0.7, 'H4': -0.6}})
        self.assertEqual(muc(kq, 'kt')['muc'], 'chu_y')

    def test_duoi_lot_toi_thieu_hien_so_that(self):
        kq = K.cham(LENH, {**DU, 'von': 300.0})                               # 1% = 3 USD → 0,003 lot < 0,01
        self.assertEqual(kq['ket_luan'], 'khong_nen')
        self.assertEqual(kq['lot'], 0.01)
        self.assertAlmostEqual(kq['rui_ro_tien'], 10.0)

    def test_ban_tieng_anh_khong_sot_tieng_viet(self):
        from so_cong_khai import dich
        canh = [({**LENH, 'sl': None}, DU), ({**LENH, 'sl': 3510.0}, DU), ({**LENH, 'tp': 3490.0}, DU), ({**LENH, 'tp': None}, DU),
                ({**LENH, 'tp': 3505.3}, DU), ({**LENH, 'rui_ro_pct': 3.0}, DU), ({**LENH, 'rui_ro_pct': 10.0}, DU), (LENH, {**DU, 'von': 300.0}),
                (LENH, {**DU, 'lo_hom_nay': -320.0}), (LENH, {**DU, 'lo_hom_nay': -100.0}), (LENH, {**DU, 'rui_ro_dang_mo': 560.0}),
                (LENH, {**DU, 'tin': [{'t': (NOW - timedelta(minutes=5)).isoformat(), 'tien': 'USD', 'ten': 'CPI m/m'}]}),
                (LENH, {**DU, 'bid': 3500.0, 'ask': 3501.5, 'spread_thuong': 0.3}), ({**LENH, 'sl': 3498.3, 'tp': 3504.3}, DU),
                (LENH, {**DU, 'thua_gan_nhat': {'dong': (NOW - timedelta(minutes=5)).isoformat(), 'lot': 0.1}}),
                (LENH, {**DU, 'vi_the': [{'ma': 'XAGUSD', 'chieu': 'MUA'}], 'tuong_quan': {'XAGUSD': 0.85}}),
                (LENH, {**DU, 'ky_thuat': {'H1': -0.7, 'H4': -0.6}}), (LENH, DU)]
        for l, du in canh:
            kq = K.cham(l, du)
            chu = ' '.join(m['en']['tieu'] + ' ' + m['en']['noi'] for m in kq['muc']) + kq['ket_luan_chu']['en']
            self.assertIsNone(dich._VI.search(chu), chu[:120])

    def test_lich_su_cua_nguoi_dung(self):
        def ls(n, rong, gio=3, chieu='MUA', ma='XAUUSD'):                    # NOW là 06:00 UTC: phiên Á (0–7 giờ UTC)
            return [{'ma': ma, 'chieu': chieu, 'mo': (NOW - timedelta(days=i + 1)).replace(hour=gio).isoformat(), 'rong': rong, 'r': rong / 100}
                    for i in range(n)]
        m = muc(K.cham(LENH, {**DU, 'lich_su': ls(12, -40.0)}), 'lich_su')
        self.assertEqual(m['muc'], 'chu_y')
        self.assertIn('phiên Á', m['vi']['tieu'])                                # đủ 12 lệnh cùng mã, chiều, phiên: chọn nhóm cụ thể nhất
        self.assertIn('-480', m['vi']['tieu'])
        m = muc(K.cham(LENH, {**DU, 'lich_su': ls(6, -40.0) + ls(6, 90.0, gio=10)}), 'lich_su')
        self.assertEqual(m['muc'], 'tot')                                         # phiên Á chỉ 6 lệnh: dùng cả 12 lệnh MUA (tổng +300)
        self.assertNotIn('phiên', m['vi']['tieu'])
        m = muc(K.cham(LENH, {**DU, 'lich_su': ls(4, -40.0) + ls(8, 50.0, chieu='BAN')}), 'lich_su')
        self.assertEqual(m['muc'], 'tin')                                         # MUA chỉ 4 lệnh: chỉ báo kết quả chung của mã, không kết luận
        self.assertIn('(4 lệnh)', m['vi']['tieu'])
        self.assertIn('12 lệnh XAUUSD', m['vi']['noi'])
        m = muc(K.cham(LENH, {**DU, 'lich_su': ls(3, -40.0)}), 'lich_su')
        self.assertEqual(m['muc'], 'tin')
        self.assertEqual(muc(K.cham(LENH, {**DU, 'lich_su': ls(12, 0.0)}), 'lich_su')['muc'], 'tin')          # hòa vốn: không khen
        lech = ls(11, -10.0) + [{**ls(1, 500.0)[0], 'mo': (NOW - timedelta(days=30)).replace(hour=3).isoformat()}]
        m = muc(K.cham(LENH, {**DU, 'lich_su': lech}), 'lich_su')
        self.assertEqual(m['muc'], 'tin')                                         # tổng +390 nhưng chỉ nhờ một lệnh +500
        self.assertIn('lợi thế', m['vi']['tieu'])
        self.assertIsNone(muc(K.cham(LENH, DU), 'lich_su'))                       # không có lịch sử: bỏ mục
        self.assertEqual(K.cham(LENH, {**DU, 'lich_su': ls(12, -40.0)})['ket_luan'], 'can_nhac')
        for l in (ls(12, -40.0), ls(12, 40.0), ls(3, 1.0), ls(3, 1.0) + ls(9, 2.0, chieu='MUA')):
            m = muc(K.cham({**LENH, 'chieu': 'BAN', 'vao': 3500.0, 'sl': 3510.0, 'tp': 3480.0}, {**DU, 'lich_su': [{**x, 'chieu': 'BAN'} for x in l]}), 'lich_su')
            self.assertIsNone(dich._VI.search(m['en']['tieu'] + ' ' + m['en']['noi']), m['en'])

    def test_lot_cham_tran_va_lenh_mo_chua_tinh(self):
        kq = K.cham({**LENH, 'rui_ro_pct': 50.0}, {**DU, 'lot_max': 1.0})               # 5.000 USD / 1.000 USD mỗi lot = 5 lot > tối đa 1
        self.assertEqual((kq['lot'], kq['rui_ro_tien']), (1.0, 1000.0))                    # tiền rủi ro theo đúng lot đã chặn
        t = muc(K.cham(LENH, {**DU, 'mo_chua_tinh': 2}), 'tong')
        self.assertEqual(t['muc'], 'chu_y')
        self.assertIn('2 open trade', t['en']['noi'])

    def test_thieu_du_lieu_thi_bo_muc(self):
        kq = K.cham(LENH, {'now': NOW})
        self.assertEqual({m['k'] for m in kq['muc']}, {'rui_ro', 'rr'})
        json.dumps(kq, default=str)


class WebTest(unittest.TestCase):
    def test_duong_dan(self):
        with tempfile.TemporaryDirectory() as d:
            ch = Path(d) / 'cau-hinh.json'
            ch.write_text(json.dumps({'gia': {}}), encoding='utf-8')
            srv = web.tao_may_chu(str(ch), port=0)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            u = f'http://127.0.0.1:{srv.server_address[1]}'
            try:
                html = urllib.request.urlopen(u + '/kiem-lenh', timeout=30).read().decode('utf-8')
                self.assertIn('Kiểm tra trước khi vào lệnh', html)
                self.assertIn('aria-current="page"', html)
                for q in ('chieu=MUA&vao=1', 'ma=X&chieu=LEN&vao=1', 'ma=X&chieu=MUA&vao=abc', 'ma=X&chieu=MUA&vao=1&rui_ro=500',
                          'ma=X&chieu=MUA&vao=inf', 'ma=X&chieu=BAN&vao=1&sl=nan', 'ma=X&chieu=MUA&vao=1e999', 'ma=X&chieu=MUA&vao=-5'):
                    with self.assertRaises(urllib.error.HTTPError) as c:
                        urllib.request.urlopen(f'{u}/api/kiem-lenh?{q}', timeout=30)
                    self.assertEqual(c.exception.code, 400, q)
            finally:
                srv.shutdown()
                srv.server_close()
                trang.MIEN_TRU = trang.MIEN_TRU_GOC


if __name__ == '__main__':
    unittest.main()
