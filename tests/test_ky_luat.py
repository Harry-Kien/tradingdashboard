"""Bài kiểm cho Kỷ luật giao dịch: ky_luat.cham (hàm thuần), ky_luat.ghep_lenh (ghép lần khớp MT5 thành lệnh) và đường dẫn /ky-luat."""
from functools import partial
from http_owner import owner_urlopen
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace as N

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import ky_luat as K, trang, web  # noqa: E402

T0 = datetime(2026, 11, 23, 2, 0, tzinfo=timezone.utc)          # 9:00 sáng thứ Hai giờ Việt Nam


def L(i, mo_phut, dai_phut, lai, lot=0.1, sl=3490.0, rr=100.0, **k):
    mo = T0 + timedelta(minutes=mo_phut)
    return {'id': i, 'ma': 'XAUUSD', 'chieu': 'MUA', 'mo': mo.isoformat(), 'dong': (mo + timedelta(minutes=dai_phut)).isoformat(), 'lot': lot,
            'vao': 3500.0, 'ra': 3500.0, 'sl': sl, 'dong_boi_sl': False, 'lai': lai, 'nguon': 'Đặt tay', 'von_truoc': 10000.0,
            'von_dau_ngay': 10000.0, 'rui_ro_tien': rr, 'tien_lien_quan': ['USD'], **k}


def loi(kq, i):
    return {l['k'] for x in kq['lenh'] if x['id'] == i for l in x['loi']}


class ChamTest(unittest.TestCase):
    def test_lenh_dung_quy_tac_va_tong_hop(self):
        kq = K.cham([L(1, 0, 30, 120.0), L(2, 120, 30, -100.0)])
        self.assertEqual(kq['n'], 2)
        self.assertEqual(kq['diem'], 100)
        self.assertEqual(kq['pham']['n'], 0)
        self.assertEqual(kq['dat']['lai'], 20.0)
        self.assertEqual(kq['chuoi_thua_dai_nhat'], 1)
        self.assertEqual(kq['lo_lon_nhat']['pct'], 1.0)
        self.assertEqual((kq['rui_ro_tb_pct'], kq['rui_ro_max_pct']), (1.0, 1.0))

    def test_khong_dung_lo(self):
        kq = K.cham([L(1, 0, 30, -50.0, sl=None, rr=None)])
        self.assertEqual(loi(kq, 1), {'khong_sl'})
        kq = K.cham([L(1, 0, 30, -50.0, sl=None, rr=None, dong_boi_sl=True)])       # dừng lỗ thêm sau, lệnh đóng bởi dừng lỗ: không tính lỗi
        self.assertEqual(loi(kq, 1), set())

    def test_rui_ro_vuot_muc(self):
        kq = K.cham([L(1, 0, 30, -300.0, rr=300.0)])                                # 3% > 2%
        self.assertEqual(loi(kq, 1), {'rui_ro'})
        self.assertEqual(K.cham([L(1, 0, 30, -300.0, rr=300.0)], {'rui_ro_lenh_toi_da_pct': 5})['diem'], 100)

    def test_vao_gap_va_tang_lot_sau_thua(self):
        kq = K.cham([L(1, 0, 30, -100.0), L(2, 35, 30, 50.0, lot=0.3)])            # vào 5 phút sau lệnh thua, lot gấp 3
        self.assertEqual(loi(kq, 2), {'gap', 'tang_lot'})
        kq = K.cham([L(1, 0, 30, 100.0), L(2, 35, 30, 50.0, lot=0.3)])             # lệnh trước thắng: không phải gỡ
        self.assertEqual(loi(kq, 2), set())
        kq = K.cham([L(1, 0, 30, -100.0), L(2, 60, 30, 50.0, lot=0.3)])            # 30 phút sau: không gấp, nhưng vẫn tăng lot
        self.assertEqual(loi(kq, 2), {'tang_lot'})

    def test_vao_khi_da_cham_lo_ngay(self):
        kq = K.cham([L(1, 0, 10, -200.0), L(2, 30, 10, -150.0), L(3, 120, 10, 80.0)])
        self.assertEqual(loi(kq, 3), {'qua_lo'})                                    # đã lỗ 3,5% > 3% trước khi vào lệnh 3
        self.assertEqual(kq['ngay_cham_gioi_han'], [])                              # cả ngày lỗ 2,7%: chưa chạm
        self.assertEqual(K.cham([L(1, 0, 10, -350.0)])['ngay_cham_gioi_han'], ['2026-11-23'])

    def test_qua_so_lenh_ngay(self):
        ds = [L(i, i * 60, 10, 10.0) for i in range(4)]
        self.assertEqual(loi(K.cham(ds, {'so_lenh_ngay_toi_da': 3}), 3), {'qua_nhieu'})
        self.assertEqual(K.cham(ds, {'so_lenh_ngay_toi_da': 0})['diem'], 100)

    def test_tin_manh(self):
        tin = [{'t': (T0 + timedelta(minutes=10)).isoformat(), 'tien': 'USD', 'ten': 'CPI m/m'}]
        kq = K.cham([L(1, 0, 30, -50.0)], tin=tin, tin_tu=T0 - timedelta(days=1))
        self.assertEqual(loi(kq, 1), {'tin'})
        self.assertEqual(kq['lenh'][0]['loi'][0]['ten'], 'CPI m/m')
        kq = K.cham([L(1, 0, 30, -50.0)], tin=[{**tin[0], 'tien': 'JPY'}], tin_tu=T0 - timedelta(days=1))
        self.assertEqual(loi(kq, 1), set())
        kq = K.cham([L(1, 0, 30, -50.0)], tin=tin, tin_tu=T0 + timedelta(hours=1))   # lịch tin chưa phủ lúc vào
        self.assertEqual((loi(kq, 1), kq['khong_kiem_tin']), (set(), 1))
        self.assertIsNone(K.cham([L(1, 0, 30, -50.0)])['khong_kiem_tin'])

    def test_lai_lo_nhom_pham_quy_tac(self):
        kq = K.cham([L(1, 0, 30, 200.0), L(2, 120, 30, -400.0, rr=400.0), L(3, 300, 30, -50.0, sl=None, rr=None)])
        self.assertEqual((kq['dat']['lai'], kq['pham']['lai'], kq['pham']['n'], kq['diem']), (200.0, -450.0, 2, 33))
        r = {x['k']: x for x in kq['quy_tac']}
        self.assertEqual((r['rui_ro']['n'], r['rui_ro']['lai'], r['khong_sl']['n']), (1, -400.0, 1))
        self.assertEqual([x['id'] for x in kq['lenh']], [3, 2, 1])                  # mới nhất trước
        json.dumps(kq)

    def test_khong_co_lenh(self):
        kq = K.cham([])
        self.assertEqual((kq['n'], kq['diem'], kq['lo_lon_nhat']), (0, None, None))


class GhepLenhTest(unittest.TestCase):
    def test_ghep_va_so_du_truoc_lenh(self):
        t = int(T0.timestamp())
        d = lambda **k: N(**{'commission': 0.0, 'swap': 0.0, 'fee': 0.0, 'magic': 0, 'symbol': 'XAUUSD', 'volume': 0.1, 'reason': 0, 'order': 0, **k})   # noqa: E731
        deals = [d(time=t - 86400, type=2, entry=0, profit=10000.0, price=0.0, position_id=0, symbol=''),
                 d(time=t, type=0, entry=0, profit=0.0, price=3500.0, position_id=11, order=101, commission=-1.0),
                 d(time=t + 600, type=1, entry=1, profit=-100.0, price=3490.0, position_id=11, order=102, reason=4, commission=-1.0),
                 d(time=t + 900, type=1, entry=0, profit=0.0, price=3489.0, position_id=12, order=103, volume=0.2),
                 d(time=t + 1200, type=0, entry=1, profit=120.0, price=3483.0, position_id=12, order=104, volume=0.2),
                 d(time=t + 1300, type=0, entry=0, profit=0.0, price=3484.0, position_id=13, order=105)]    # còn mở: bỏ qua
        orders = [N(ticket=101, sl=3490.0), N(ticket=103, sl=0.0)]
        s = N(digits=2, trade_tick_value=1.0, trade_tick_size=0.01, trade_contract_size=100.0, currency_profit='USD', currency_base='XAU')
        so_du_hien = 10000.0 - 1.0 - 101.0 + 120.0
        gd = {x['id']: x for x in K.ghep_lenh(deals, orders, {'XAUUSD': s}, 'USD', so_du_hien, T0 - timedelta(days=2))}
        self.assertEqual(set(gd), {11, 12})
        a, b = gd[11], gd[12]
        self.assertEqual((a['chieu'], a['sl'], a['lai'], a['von_truoc'], a['rui_ro_tien'], a['dong_boi_sl']), ('MUA', 3490.0, -102.0, 10000.0, 100.0, True))
        self.assertEqual((b['chieu'], b['sl'], b['rui_ro_tien'], b['lai'], b['von_truoc']), ('BAN', None, None, 120.0, 9898.0))
        kq = K.cham(list(gd.values()))
        self.assertEqual(loi(kq, 12), {'khong_sl', 'gap', 'tang_lot'})


class SoDuDauNgayTest(unittest.TestCase):
    """Số dư đầu ngày (giờ VN) phải là số dư SAU các lệnh đóng trước nửa đêm; lệnh vào nhiều lần dùng giá vào trung bình."""

    def test_von_dau_ngay_va_gia_trung_binh(self):
        d = lambda **k: N(**{'commission': 0.0, 'swap': 0.0, 'fee': 0.0, 'magic': 0, 'symbol': 'XAUUSD', 'volume': 0.1, 'reason': 0, 'order': 0, **k})   # noqa: E731
        dem = int(datetime(2026, 11, 23, 16, 50, tzinfo=timezone.utc).timestamp())          # 23:50 giờ VN
        sang = int(datetime(2026, 11, 24, 2, 0, tzinfo=timezone.utc).timestamp())          # 09:00 giờ VN hôm sau
        deals = [d(time=dem - 86400, type=2, entry=0, profit=1000.0, price=0.0, position_id=0, symbol=''),
                 d(time=dem - 600, type=0, entry=0, profit=0.0, price=3500.0, position_id=1, order=11),
                 d(time=dem, type=1, entry=1, profit=-30.0, price=3497.0, position_id=1, order=12),
                 d(time=sang, type=0, entry=0, profit=0.0, price=3500.0, position_id=2, order=21, volume=0.1),
                 d(time=sang + 60, type=0, entry=0, profit=0.0, price=3510.0, position_id=2, order=22, volume=0.3),
                 d(time=sang + 600, type=1, entry=1, profit=20.0, price=3512.0, position_id=2, order=23, volume=0.4)]
        s = N(digits=2, trade_tick_value=1.0, trade_tick_size=0.01, trade_contract_size=100.0, currency_profit='USD', currency_base='XAU')
        gd = {x['id']: x for x in K.ghep_lenh(deals, [N(ticket=21, sl=3490.0)], {'XAUUSD': s}, 'USD', 990.0, datetime(2026, 11, 20, tzinfo=timezone.utc))}
        self.assertEqual((gd[1]['von_truoc'], gd[1]['von_dau_ngay']), (1000.0, 1000.0))
        self.assertEqual((gd[2]['von_truoc'], gd[2]['von_dau_ngay']), (970.0, 970.0))        # trước đây ra 1000: lấy số dư TRƯỚC lệnh đóng lúc 23:50
        self.assertEqual((gd[2]['vao'], gd[2]['lot']), (3507.5, 0.4))                          # (3500×0,1 + 3510×0,3) / 0,4
        self.assertAlmostEqual(gd[2]['rui_ro_tien'], (3507.5 - 3490.0) * 100 * 0.4)


class LocNguonTest(unittest.TestCase):
    def test_nhan_ca_ten_tieng_anh(self):
        gd = [{'id': 1, 'nguon': 'Đặt tay'}, {'id': 2, 'nguon': 'EA M'}]
        self.assertEqual([x['id'] for x in K.loc_nguon(gd, 'Manual')], [1])          # trang tiếng Anh gửi tên đã dịch
        self.assertEqual([x['id'] for x in K.loc_nguon(gd, 'Đặt tay')], [1])
        self.assertEqual([x['id'] for x in K.loc_nguon(gd, 'EA M')], [2])
        self.assertEqual(len(K.loc_nguon(gd, None)), 2)


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
                html = open_owner(u + '/ky-luat', timeout=30).read().decode('utf-8')
                self.assertIn('Kỷ luật giao dịch', html)
                self.assertIn('aria-current="page"', html)
                for q in ('ngay=0', 'ngay=abc', 'ngay=400', 'q_rui_ro_lenh_toi_da_pct=x', 'q_lo_ngay_toi_da_pct=inf', 'q_so_lenh_ngay_toi_da=nan'):
                    with self.assertRaises(urllib.error.HTTPError) as c:
                        open_owner(f'{u}/api/ky-luat?{q}', timeout=30)
                    self.assertEqual(c.exception.code, 400, q)
                j = json.loads(open_owner(u + '/api/ky-luat?ngay=7', timeout=60).read())   # không có MT5: báo rõ, không lỗi máy chủ
                self.assertFalse(j['san_sang'])
            finally:
                srv.shutdown()
                srv.server_close()
                trang.MIEN_TRU = trang.MIEN_TRU_GOC


if __name__ == '__main__':
    unittest.main()
