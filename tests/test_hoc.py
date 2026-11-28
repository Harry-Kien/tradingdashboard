"""Bài kiểm cho phần học từ dữ liệu nhiều năm: phân loại bối cảnh, tách nửa học/kiểm, lời nhận xét, và việc nhớ kết quả."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from so_cong_khai import bieu_do, gia, hoc, phan_tich, song  # noqa: E402
from test_gia import MA_THAT, _kho  # noqa: E402

T0 = datetime(2026, 1, 5, tzinfo=timezone.utc)


def _l(gio, huong, usd):
    return {'t': (T0 + timedelta(hours=gio)).isoformat(), 'huong': huong, 'usd': usd}


class BoiCanhTest(unittest.TestCase):
    def test_phien_theo_gio_utc(self):
        ten = [hoc.phien(T0 + timedelta(hours=h)) for h in (0, 6, 7, 11, 12, 19, 20, 23)]
        self.assertEqual(ten, ['Á', 'Á', 'Âu', 'Âu', 'Mỹ', 'Mỹ', 'cuối ngày', 'cuối ngày'])
        self.assertEqual(hoc.phien(pd.Timestamp('2026-01-05 14:00', tz='Asia/Ho_Chi_Minh')), 'Âu')      # 14:00 giờ Việt Nam là 07:00 UTC

    def test_muc_bien_do(self):
        self.assertEqual([hoc.muc(x) for x in (0.5, 0.8, 1.0, 1.25, 1.3, None, float('nan'))], ['thấp', 'vừa', 'vừa', 'vừa', 'cao', None, None])

    def test_nhan_xet(self):
        s = lambda n, tb: {'n': n, 'usd_tb': tb}                                                       # noqa: E731
        self.assertEqual(hoc.nhan_xet(s(40, 1.0), s(35, 0.2))[0], 'giu')
        self.assertEqual(hoc.nhan_xet(s(40, -1.0), s(35, -0.2))[0], 'lo')
        self.assertEqual(hoc.nhan_xet(s(40, 1.0), s(35, -0.2))[0], 'khong_on')
        self.assertEqual(hoc.nhan_xet(s(40, 1.0), s(29, 5.0))[0], 'chua_du')                           # nửa kiểm thiếu mẫu thì không khen
        self.assertEqual(hoc.nhan_xet({'n': 0}, s(500, 5.0))[0], 'chua_du')                            # chiều chưa từng có lệnh ở nửa học

    def test_ty_le_thang_hoa_von(self):
        s = hoc._so([_l(i, 'MUA', u) for i, u in enumerate([4.0, 4.0, -2.0, -2.0, -2.0, 0.0])])
        self.assertEqual((s['lai_tb'], s['lo_tb']), (4.0, 1.5))                                       # lệnh hòa tính vào phần không thắng
        self.assertEqual(s['hoa_von'], round(1.5 / 5.5 * 100, 1))
        self.assertEqual(s['ty_le'] > s['hoa_von'], s['usd_tb'] > 0)                                  # thắng vượt hòa vốn đúng khi kỳ vọng dương
        thua = hoc._so([_l(i, 'MUA', u) for i, u in enumerate([1.0, 1.0, 1.0, -9.0])])               # thắng 75% mà vẫn lỗ
        self.assertGreater(thua['hoa_von'], thua['ty_le'])
        self.assertLess(thua['usd_tb'], 0)
        self.assertEqual(hoc._so([_l(0, 'MUA', -1.0)])['hoa_von'], 100.0)
        self.assertEqual(hoc._so([_l(0, 'MUA', 2.0)])['hoa_von'], 0.0)
        rng = np.random.default_rng(7)
        for _ in range(200):
            x = hoc._so([_l(i, 'MUA', float(u)) for i, u in enumerate(rng.normal(0.1, 3, 30))])
            if abs(x['ty_le'] - x['hoa_von']) > 0.2:                                                  # bỏ qua sai số làm tròn sát ngưỡng
                self.assertEqual(x['ty_le'] > x['hoa_von'], x['usd_tb'] > 0)

    def test_sut_giam_va_chuoi_thua(self):
        s = hoc._so([_l(i, 'MUA', u) for i, u in enumerate([1.0, -2.0, -1.0, 3.0, -4.0])])
        self.assertEqual((s['sut_max'], s['chuoi_thua']), (4.0, 2))                                  # đỉnh +1 xuống đáy −3; hai lệnh thua liền
        self.assertEqual(hoc.sut_giam([-1.0, -1.0, 0.0, 5.0]), {'sut_max': 2.0, 'chuoi_thua': 3})      # lỗ ngay từ đầu cũng là sụt giảm; lệnh hòa nối chuỗi
        self.assertEqual(hoc.sut_giam([2.0, 1.0]), {'sut_max': 0.0, 'chuoi_thua': 0})

    def test_mo_phong_chuoi_lenh(self):
        rng = np.random.default_rng(3)
        self.assertIsNone(hoc.mo_phong([1.0] * 29))                                                    # dưới 30 lệnh: không mô phỏng
        lai = list(rng.choice([10.0, -5.0], size=3000, p=[0.4, 0.6]))                                  # kỳ vọng +1 mỗi lệnh
        a = hoc.mo_phong(lai)
        self.assertEqual(a, hoc.mo_phong(lai))                                                         # cùng hạt giống thì cùng số
        tb = float(np.mean(lai))
        self.assertTrue(a['tb_ci'][0] < tb < a['tb_ci'][1], (a, tb))
        self.assertGreater(a['tb_ci'][0], 0)
        self.assertEqual(a['xs_lai'], 1.0)
        self.assertLessEqual(a['sut_p50'], a['sut_p95'])
        hoa = list(rng.normal(0, 5, 3000) - 0.0)
        b = hoc.mo_phong(hoa)
        self.assertTrue(b['tb_ci'][0] < 0 < b['tb_ci'][1], b)                                         # không lợi thế: khoảng chứa 0
        self.assertTrue(0.05 < b['xs_lai'] < 0.95, b)
        it = hoc.mo_phong(lai[:300])
        self.assertGreater(it['tb_ci'][1] - it['tb_ci'][0], a['tb_ci'][1] - a['tb_ci'][0])           # ít lệnh hơn thì khoảng rộng hơn
        # cùng các lệnh, xếp thua thành từng cụm 20 lệnh liền nhau: lấy mẫu theo khối giữ cụm nên sụt giảm mô phỏng sâu hơn khi xếp xen kẽ
        cum = ([3.0] * 20 + [-2.0] * 20) * 30
        xen = [3.0, -2.0] * 600
        self.assertGreater(hoc.mo_phong(cum)['sut_p50'], 3 * hoc.mo_phong(xen)['sut_p50'])
        json.dumps(a)

    def test_theo_ky_nam_va_thang(self):
        ls = ([{'t': f'2019-03-0{i % 9 + 1}T10:00:00+00:00', 'huong': 'MUA', 'usd': 2.0} for i in range(12)]          # 2019: 12 lệnh, +24
              + [{'t': f'2020-05-0{i % 9 + 1}T10:00:00+00:00', 'huong': 'BAN', 'usd': -1.0} for i in range(15)]        # 2020: 15 lệnh, −15
              + [{'t': '2021-01-04T10:00:00+00:00', 'huong': 'MUA', 'usd': 50.0}])                                      # 2021: 1 lệnh, không đủ để tính
        k = hoc.theo_ky(ls)
        self.assertEqual([r[0] for r in k['ds']], [2019, 2020, 2021])
        self.assertEqual(k['ds'][0], [2019, 12, 100.0, 2.0, 24.0])
        self.assertEqual((k['so_ky'], k['ky_lai']), (2, 1))                 # năm chỉ 1 lệnh không được tính là "năm có lãi"
        t = hoc.theo_ky(ls, 'thang')
        self.assertEqual([r[0] for r in t['ds']], ['2019-03', '2020-05', '2021-01'])
        self.assertIsNone(hoc.theo_ky([]))
        r = hoc._them_mo_phong({'tat_ca': hoc._so(ls)}, ls)
        self.assertEqual(r['tat_ca']['theo_ky']['ky'], 'nam')
        json.dumps(r)

    def test_hoa_hong_tu_cai_dat(self):
        self.assertEqual(hoc.hoa_hong({'hoc': {'hoa_hong_lot': 7}}), 7.0)
        for cfg in ({}, {'hoc': None}, {'hoc': {'hoa_hong_lot': 'abc'}}, {'hoc': {'hoa_hong_lot': -3}}, {'hoc': {'hoa_hong_lot': 1e6}}):
            self.assertEqual(hoc.hoa_hong(cfg), 0.0, cfg)

    def test_thong_ke_tach_hoc_va_kiem(self):
        ti = pd.Series(1.0, index=pd.date_range(T0 - timedelta(days=2), periods=400, freq='1h'))
        ti.iloc[200:] = 1.5                                                                           # từ giữa chừng biên độ thành "cao"
        lenh = [_l(13 + 24 * d, 'BAN', 2.0) for d in range(40)] + [_l(13 + 24 * d, 'BAN', -1.0) for d in range(40, 80)] + [_l(8, 'MUA', 3.0)]
        cat = T0 + timedelta(days=40)
        r = hoc.thong_ke(lenh, ti, cat)
        b = r['BAN']
        self.assertEqual((b['n'], b['hoc']['n'], b['kiem']['n'], b['nhan_xet']), (80, 40, 40, 'khong_on'))
        self.assertEqual((b['hoc']['usd_tb'], b['kiem']['usd_tb'], b['ty_le']), (2.0, -1.0, 50.0))
        self.assertEqual(r['BAN|Mỹ']['n'], 80)
        self.assertEqual(r['BAN|Mỹ|vừa']['n'] + r['BAN|Mỹ|cao']['n'], 80)
        self.assertEqual(r['MUA|Âu']['nhan_xet'], 'chua_du')
        self.assertNotIn('MUA|Mỹ', r)

    def test_quang_dai_tach_cac_nam_truoc_quang_chon(self):
        def l(nam, huong, usd):
            return {'t': f'{nam}-03-01T10:00:00+00:00', 'huong': huong, 'usd': usd}
        lenh = [l(2015, 'MUA', -1.0)] * 3 + [l(2016, 'MUA', 2.0), l(2016, 'BAN', -4.0)] + [l(2024, 'MUA', 5.0)] * 2
        r = hoc.quang_dai(lenh, 2024)
        t = r['truoc']
        self.assertEqual((r['tu_nam'], t['den_nam'], t['n'], t['usd_tb'], t['nam_lai'], t['so_nam']), (2015, 2023, 5, -1.0, 0, 2))
        self.assertEqual((r['sau']['n'], r['sau']['usd_tb']), (2, 5.0))
        self.assertEqual(r['theo_nam'], [[2015, 3, 0.0, -1.0, -3.0], [2016, 2, 50.0, -1.0, -2.0], [2024, 2, 100.0, 5.0, 10.0]])
        self.assertEqual((r['theo']['MUA']['truoc']['n'], r['theo']['BAN']['truoc']['usd_tb'], r['theo']['BAN']['sau']['n']), (4, -4.0, 0))
        self.assertEqual((r['theo']['MUA']['dat'], r['theo']['BAN']['dat']), (False, False))            # MUA: 4 lệnh, chưa đủ mẫu; BÁN: lỗ
        nhieu = [l(2015 + i % 9, 'MUA', 1.0) for i in range(30)] + [l(2015 + i % 9, 'BAN', -1.0) for i in range(30)] + [l(2024, 'BAN', 9.0)] * 40
        d = hoc.quang_dai(nhieu, 2024)['theo']
        self.assertEqual((d['MUA']['dat'], d['BAN']['dat']), (True, False))                           # lãi của quãng gần đây không cứu được các năm trước
        self.assertIsNone(hoc.quang_dai([l(2024, 'MUA', 1.0)], 2024))                                  # không có lệnh nào trước quãng chọn: không có gì để nêu
        json.dumps(r)

    def test_trang_neu_cac_nam_truoc_quang_chon(self):
        html = bieu_do.trang_bieu_do('Thử')
        for must in ('Các năm trước quãng này', 'r.dai', 'năm có lãi', 'số giá cố định', 'đặt dừng lỗ theo biên độ', 'quãng gần đây cũng không', 'daiDat(p)', 'các năm trước quãng này cũng phải có lãi', 'Kỷ luật xét cả dòng này'):
            self.assertIn(must, html)

    def test_lenh_truoc_quang_chon_chi_tinh_mot_lan(self):
        dem = []
        fn = lambda: dem.append(1) or [{'t': '2015-03-01T10:00:00+00:00', 'huong': 'MUA', 'usd': 1.0}]      # noqa: E731
        with tempfile.TemporaryDirectory() as d:
            a = hoc.nho_truoc(Path(d), 'dinh_day', [1, 'a'], fn)
            b = hoc.nho_truoc(Path(d), 'dinh_day', [1, 'a'], fn)                                       # cùng khóa: đọc lại từ tệp
            self.assertEqual((a, len(dem)), (b, 1))
            hoc.nho_truoc(Path(d), 'dinh_day', [2, 'a'], fn)                                           # khóa khác (dữ liệu hay mã luật đổi): tính lại
            self.assertEqual(len(dem), 2)
            (Path(d) / 'hoc_truoc_dinh_day.json').write_text('{hỏng', encoding='utf-8')
            self.assertEqual(hoc.nho_truoc(Path(d), 'dinh_day', [2, 'a'], fn), a)                      # tệp hỏng: tính lại, không văng lỗi
        hoc.nho_truoc(None, 'dinh_day', [1, 'a'], fn)                                                  # không có thư mục: vẫn tính
        self.assertEqual(len(dem), 4)

    def test_boi_canh_luc(self):
        idx = pd.date_range(T0, periods=600, freq='1h')
        k = np.arange(600)
        h1 = pd.DataFrame({'open': 100.0, 'high': 101.0 + (k > 560) * 3, 'low': 99.0, 'close': 100.0}, index=idx)
        r = hoc.boi_canh_luc(h1, idx[-1].to_pydatetime() + timedelta(hours=1, minutes=5))
        self.assertEqual((r['phien'], r['bien_do']), ('Á', 'cao'))
        self.assertGreater(r['bien_do_ty_le'], 1.25)


class HocTest(unittest.TestCase):
    def setUp(self):
        gia._nho.clear()
        song._tt.update(deps=None, mt5=None, fr=None, thu=0.0, luc=0.0)
        hoc._tt.update(key=None, kq=None, dang=False, loi=None, bat_dau=None)
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.start = datetime(2026, 9, 7, tzinfo=timezone.utc)
        _kho(self.d, self.start, 75 * 1440)
        self.out = self.d / 'out'
        self.cfg = {'ten': 'Thử', 'thu_muc_ra': str(self.out), 'gia': {'kho_m1': str(self.d), 'ma_nguon': MA_THAT, 'so_thang': 4}}
        self.that = hoc.chay

    def tearDown(self):
        hoc.chay = self.that
        gia._nho.clear()
        self.tmp.cleanup()

    @unittest.skipUnless(all(os.path.isdir(p) for p in MA_THAT), 'không có mã của dự án trên máy này')
    def test_chay_tren_ma_that_khi_khong_co_tep_nhieu_nam(self):
        kq = hoc.chay(self.cfg)                                                                       # không có tệp nhiều năm: dùng kho nến
        self.assertEqual(kq['loi'], [])
        self.assertEqual((set(kq['luat']), kq['so_ngay']), ({'bot', 'ba_khung', 'dinh_day', 'pha_vo', 'ict', 'ict_fvg', 'elliott', 'wyckoff', 'price_action', 'fib', 'ema_hoi'}, 75))
        self.assertTrue(kq['tu'] < kq['cat'] < kq['den'])
        for ma, r in kq['luat'].items():
            self.assertEqual(sum(s['n'] for k, s in r['theo'].items() if '|' not in k), r['tat_ca']['n'], ma)
            for k, s in r['theo'].items():
                self.assertEqual(s['hoc']['n'] + s['kiem']['n'], s['n'], (ma, k))
                self.assertIn(s['nhan_xet'], ('giu', 'lo', 'khong_on', 'chua_du'))
        json.dumps(kq)

    @unittest.skipUnless(all(os.path.isdir(p) for p in MA_THAT), 'không có mã của dự án trên máy này')
    def test_phan_tich_co_boi_canh_hien_tai(self):
        r = phan_tich.phan_tich(self.cfg, self.start + timedelta(days=75, minutes=3))
        self.assertIn(r['boi_canh']['phien'], ('Á', 'Âu', 'Mỹ', 'cuối ngày'))
        self.assertIn(r['boi_canh']['bien_do'], ('thấp', 'vừa', 'cao'))

    def test_nho_ket_qua(self):
        dem = []
        hoc.chay = lambda cfg: dem.append(1) or {'luat': {}, 'loi': []}
        a = hoc.lay(self.cfg, self.out, cho=True)
        b = hoc.lay(self.cfg, self.out)
        self.assertTrue(a['san_sang'] and b['san_sang'])
        hoc._tt.update(key=None, kq=None)
        self.assertTrue(hoc.lay(self.cfg, self.out)['san_sang'])                                       # đọc lại từ out/hoc.json
        self.assertEqual(len(dem), 1)

    def test_trang_va_ma_nguon(self):
        html = bieu_do.trang_bieu_do('Thử')
        for must in ('/api/hoc', 'bối cảnh giống lúc này', 'Nửa học', 'không phải dự báo', 'bản đồ và điều kiện lúc này', 'Vẽ bản đồ ICT lên biểu đồ', 'Trang không ép ra lệnh'):
            self.assertIn(must, html)
        src = Path(hoc.__file__).read_text(encoding='utf-8')
        for banned in ('order_send', 'order_check', 'TRADE_ACTION', 'positions_get', 'MetaTrader5'):
            self.assertNotIn(banned, src)


if __name__ == '__main__':
    unittest.main()
