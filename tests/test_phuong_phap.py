"""Bài kiểm cho ba phương pháp tùy chọn: mỗi quy tắc phải bắt đúng mẫu hình dựng tay, và phần chấm lệnh phải xử đúng từng trường hợp
(chốt lời, dừng lỗ, cả hai trong một nến, lệnh chờ không khớp, lệnh chờ bị hủy, hết giờ)."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import phuong_phap as PP  # noqa: E402

T0 = datetime(2026, 6, 1, tzinfo=timezone.utc)


def _m15(n, gia=100.0):
    """n nến M15 đi ngang quanh `gia`: mở = đóng = gia, đỉnh +0,5, đáy −0,5 (ATR = 1)."""
    idx = pd.date_range(T0, periods=n, freq='15min')
    return pd.DataFrame({'open': gia, 'high': gia + 0.5, 'low': gia - 0.5, 'close': gia}, index=idx)


def _h1(m15):
    return m15.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()


def _dat(df, i, **kw):
    for k, v in kw.items():
        df.iloc[i, df.columns.get_loc(k)] = v


def _m1(bat_dau, gia):
    """Nến 1 phút bắt đầu từ `bat_dau`; `gia`: danh sách (mở, đỉnh, đáy, đóng)."""
    idx = pd.date_range(bat_dau, periods=len(gia), freq='1min')
    return pd.DataFrame(gia, columns=['open', 'high', 'low', 'close'], index=idx)


class QuetTest(unittest.TestCase):
    def test_pha_vo_dinh_va_day(self):
        m = _m15(120)
        _dat(m, 119, open=100.0, close=101.2, high=101.3, low=99.9)
        th = PP.quet('pha_vo', m, _h1(m))
        self.assertEqual([(s['i'], s['huong'], s['kieu']) for s in th], [(119, 'MUA', 'thi_truong')])
        s = th[0]
        self.assertAlmostEqual(s['vao'] - s['sl'], PP.SL_PHA_ATR * s['atr'], places=6)
        self.assertEqual(s['t'], m.index[119] + timedelta(minutes=15))                      # giờ nến ĐÓNG
        m2 = _m15(120)
        _dat(m2, 119, open=100.0, close=98.8, high=100.1, low=98.7)
        self.assertEqual([s['huong'] for s in PP.quet('pha_vo', m2, _h1(m2))], ['BAN'])
        m3 = _m15(120)
        _dat(m3, 119, open=100.45, close=100.6, high=100.7, low=100.4)                       # vượt đỉnh nhưng thân nến quá nhỏ
        self.assertEqual(PP.quet('pha_vo', m3, _h1(m3)), [])

    def test_ict_quet_day_roi_de_lai_khoang_trong(self):
        m = _m15(120)
        _dat(m, 112, low=98.9)                                                               # quét đáy 5 giờ (99,5) rồi đóng trở lại 100
        _dat(m, 114, open=100.0, close=102.0, high=102.1, low=100.0)                         # nến bật mạnh
        _dat(m, 115, open=102.0, close=102.5, high=102.6, low=101.2)                         # đáy 101,2 nằm trên đỉnh nến 113 (100,5): khoảng trống giá
        th = PP.quet('ict', m, _h1(m))
        s = next(x for x in th if x['i'] == 115)
        self.assertEqual((s['huong'], s['kieu']), ('MUA', 'gioi_han'))
        self.assertAlmostEqual(s['vao'], (101.2 + 100.5) / 2)                                # giữa khoảng trống
        self.assertAlmostEqual(s['sl'], 98.9 - PP.DEM_ATR * s['atr'], places=6)              # ngay dưới điểm quét
        m2 = _m15(120)                                                                       # có khoảng trống nhưng không có lần quét trước đó
        _dat(m2, 114, open=100.0, close=102.0, high=102.1, low=100.0)
        _dat(m2, 115, open=102.0, close=102.5, high=102.6, low=101.2)
        self.assertEqual([x for x in PP.quet('ict', m2, _h1(m2)) if x['huong'] == 'MUA'], [])

    def test_hoi_ve_ema_theo_xu_huong(self):
        n = 400
        idx = pd.date_range(T0, periods=n, freq='15min')
        c = 100 + 0.1 * np.arange(n)
        m = pd.DataFrame({'open': c - 0.05, 'high': c + 0.3, 'low': c - 0.3, 'close': c}, index=idx)
        self.assertEqual(PP.quet('ema_hoi', m, _h1(m)), [])                                  # tăng đều, không nến nào chạm EMA20
        _dat(m, n - 1, low=c[-1] - 1.2)                                                      # nến cuối rút chân xuống chạm EMA20 rồi đóng tăng
        th = PP.quet('ema_hoi', m, _h1(m))
        self.assertEqual([(s['i'], s['huong']) for s in th], [(n - 1, 'MUA')])
        self.assertLess(th[0]['sl'], c[-1] - 1.2)

    def test_phuong_phap_la(self):
        with self.assertRaises(ValueError):
            PP.quet('khong_co', _m15(120), _h1(_m15(120)))
        self.assertEqual(PP.quet('pha_vo', _m15(30), _h1(_m15(30))), [])                     # chưa đủ nến thì không có tín hiệu


class SongVaChayLaiTest(unittest.TestCase):
    """Tín hiệu trang sống thấy (quet trên 400 nến M15 gần nhất, không có nến tương lai) phải trùng với tín hiệu của phép chạy lại
    (quet một lần trên toàn bộ lịch sử). Trùng nhau cũng có nghĩa quet() không nhìn trước."""

    def test_moi_phuong_phap_cung_tin_hieu_luc_song_va_luc_chay_lai(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('kiem_song_chay_lai', Path(__file__).resolve().parent.parent / 'cong-cu' / 'kiem_song_chay_lai.py')
        k = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(k)
        rng = np.random.default_rng(3)
        n = 2400                                                                             # 25 ngày nến M15 đi ngẫu nhiên, có xu hướng đổi chiều
        buoc = rng.normal(0, 1.0, n) + np.repeat(rng.normal(0, 0.25, n // 80), 80)
        c = 2000 + np.cumsum(buoc)
        o = np.concatenate([[c[0]], c[:-1]])
        idx = pd.date_range(T0, periods=n, freq='15min')
        m = pd.DataFrame({'open': o, 'high': np.maximum(o, c) + np.abs(rng.normal(0, 0.6, n)), 'low': np.minimum(o, c) - np.abs(rng.normal(0, 0.6, n)), 'close': c}, index=idx)
        h1 = _h1(m)
        tong = 0
        for ma in PP.DS:
            co = [s['i'] for s in PP.quet(ma, m, h1) if s['i'] >= 900]
            cat = sorted({i + 1 for i in co} | set(range(900, n, 23)))
            dung, lech, _ = k.so_sanh(ma, m, h1, cat)
            self.assertEqual(lech, [], ma)
            tong += dung
        self.assertGreater(tong, 100)                                                        # phép so có thật sự gặp tín hiệu


class ChamTest(unittest.TestCase):
    def setUp(self):
        self.t = pd.Timestamp(T0 + timedelta(days=3))
        self.mua = {'t': self.t, 'huong': 'MUA', 'kieu': 'thi_truong', 'vao': 100.0, 'sl': 98.0, 'atr': 1.0}
        self.phang = [(100.0, 100.2, 99.9, 100.0)]

    def test_chot_loi_va_dung_lo(self):
        # vào ở giá mở 100 + spread 0,2 = 100,2; rủi ro 2,2; TP = 104,6
        tp = PP.cham([self.mua], _m1(self.t, self.phang * 3 + [(104.0, 104.7, 103.9, 104.5)] + self.phang * 1500), 0.2)
        self.assertEqual((tp[0]['ket'], tp[0]['usd'], tp[0]['r']), ('TP', round(4.4 - PP.PHI, 2), round((4.4 - PP.PHI) / 2.2, 2)))
        sl = PP.cham([self.mua], _m1(self.t, self.phang * 3 + [(99.0, 99.1, 97.9, 98.5)] + self.phang * 1500), 0.2)
        self.assertEqual((sl[0]['ket'], sl[0]['usd']), ('SL', round(-2.2 - PP.PHI, 2)))
        hai = PP.cham([self.mua], _m1(self.t, self.phang * 3 + [(100.0, 105.0, 97.0, 100.0)] + self.phang * 1500), 0.2)
        self.assertEqual(hai[0]['ket'], 'SL')                                                # nến chạm cả hai thì tính dừng lỗ

    def test_lenh_ban_thoat_theo_ask(self):
        ban = {**self.mua, 'huong': 'BAN', 'sl': 102.0}                                      # vào ở Bid 100; SL khi Ask = đỉnh + 0,2 ≥ 102
        r = PP.cham([ban], _m1(self.t, self.phang * 2 + [(101.0, 101.8, 100.9, 101.5)] + self.phang * 1500), 0.2)
        self.assertEqual(r[0]['ket'], 'SL')
        r = PP.cham([ban], _m1(self.t, self.phang * 2 + [(101.0, 101.7, 100.9, 101.5)] + self.phang * 1500), 0.2)
        self.assertEqual(r[0]['ket'], 'Hết giờ')                                             # Ask chỉ tới 101,9: chưa chạm

    def test_het_gio_va_con_mo_cuoi_du_lieu(self):
        r = PP.cham([self.mua], _m1(self.t, self.phang * (PP.GIU_PHUT + 10)), 0.2)
        self.assertEqual((r[0]['ket'], r[0]['usd']), ('Hết giờ', round(100.0 - 100.2 - PP.PHI, 2)))
        self.assertEqual(PP.cham([self.mua], _m1(self.t, self.phang * 200), 0.2), [])        # lệnh còn mở tới hết dữ liệu: không chấm

    def test_lenh_cho(self):
        cho = {**self.mua, 'kieu': 'gioi_han', 'vao': 99.0, 'sl': 97.0}
        khong = PP.cham([cho], _m1(self.t, self.phang * 2000), 0.2)
        self.assertEqual(khong, [])                                                          # giá không về mức chờ: không có lệnh
        khop = PP.cham([cho], _m1(self.t, self.phang * 5 + [(99.5, 99.6, 98.7, 99.0)] + [(99.0, 103.2, 98.9, 103.0)] + self.phang * 1500), 0.2)
        self.assertEqual((khop[0]['vao'], khop[0]['ket'], khop[0]['usd']), (99.0, 'TP', round(4.0 - PP.PHI, 2)))
        huy = PP.cham([cho], _m1(self.t, self.phang * 5 + [(99.5, 99.6, 96.5, 96.8)] + self.phang * 1500), 0.2)
        self.assertEqual(huy[0]['ket'], 'SL')                                                # cùng một nến vừa khớp vừa thủng dừng lỗ: tính dừng lỗ
        muon = PP.cham([cho], _m1(self.t, self.phang * (PP.CHO_NEN * 15 + 5) + [(99.5, 99.6, 98.7, 99.0)] + self.phang * 1500), 0.2)
        self.assertEqual(muon, [])                                                           # về mức chờ sau 4 giờ: lệnh chờ đã hết hạn

    def test_gia_mo_nhay_qua_dung_lo_thi_thoat_o_gia_mo(self):
        # MUA vào 100,2 (rủi ro 2,2, SL 98): nến sau mở ở 97, dưới hẳn SL → thoát ở 97 chứ không phải ở 98
        r = PP.cham([self.mua], _m1(self.t, self.phang * 3 + [(97.0, 97.2, 96.8, 97.0)] + self.phang * 1500), 0.2)
        self.assertEqual((r[0]['ket'], r[0]['usd'], r[0]['r']), ('SL', round(-3.2 - PP.PHI, 2), round((-3.2 - PP.PHI) / 2.2, 2)))
        # BÁN vào 100 (SL 102, thoát theo Ask): nến sau mở ở 103 → Ask 103,2
        ban = {**self.mua, 'huong': 'BAN', 'sl': 102.0}
        r = PP.cham([ban], _m1(self.t, self.phang * 3 + [(103.0, 103.1, 102.8, 103.0)] + self.phang * 1500), 0.2)
        self.assertEqual((r[0]['ket'], r[0]['usd'], r[0]['r']), ('SL', round(-3.2 - PP.PHI, 2), round((-3.2 - PP.PHI) / 2.0, 2)))
        # mở cửa nhảy qua chốt lời (TP 104,6): vẫn chỉ tính ở mức chốt lời, không cộng phần nhảy có lợi
        r = PP.cham([self.mua], _m1(self.t, self.phang * 3 + [(106.0, 106.2, 105.9, 106.0)] + self.phang * 1500), 0.2)
        self.assertEqual((r[0]['ket'], r[0]['usd']), ('TP', round(4.4 - PP.PHI, 2)))
        # nến chạm SL trong lúc chạy (mở cửa chưa qua SL): vẫn thoát đúng ở SL
        r = PP.cham([self.mua], _m1(self.t, self.phang * 3 + [(98.5, 98.6, 97.0, 97.2)] + self.phang * 1500), 0.2)
        self.assertEqual(r[0]['usd'], round(-2.2 - PP.PHI, 2))
        # lệnh chờ: nến khớp cũng thủng SL thì lỗ đúng 1R; nến SAU nến khớp mở dưới SL thì thoát ở giá mở
        cho = {**self.mua, 'kieu': 'gioi_han', 'vao': 99.0, 'sl': 97.0}
        r = PP.cham([cho], _m1(self.t, self.phang * 5 + [(99.5, 99.6, 96.5, 96.8)] + self.phang * 1500), 0.2)
        self.assertEqual(r[0]['usd'], round(-2.0 - PP.PHI, 2))
        r = PP.cham([cho], _m1(self.t, self.phang * 5 + [(99.5, 99.6, 98.7, 99.0), (96.0, 96.2, 95.9, 96.0)] + self.phang * 1500), 0.2)
        self.assertEqual((r[0]['ket'], r[0]['usd']), ('SL', round(-3.0 - PP.PHI, 2)))

    def test_tin_hieu_moi_thay_lenh_cho_cu(self):
        # A: chờ mua 98 (SL 96) lúc t. B đến sau 30 phút. Lúc B đến mà A chưa khớp thì A bị hủy, như trang Biểu đồ chỉ hiện tín hiệu mới nhất.
        a = {**self.mua, 'kieu': 'gioi_han', 'vao': 98.0, 'sl': 96.0}
        b = {**self.mua, 't': self.t + pd.Timedelta(minutes=30), 'kieu': 'gioi_han', 'vao': 99.5, 'sl': 97.5}
        # phút 40 giá về 99,2 (khớp B), phút 45 về 97,5 (thủng SL của B, và chạm cả mức chờ của A)
        m1 = _m1(self.t, self.phang * 40 + [(99.8, 99.9, 99.2, 99.6)] + self.phang * 4 + [(99.0, 99.1, 97.5, 97.6)] + self.phang * 1500)
        r = PP.cham([a, b], m1, 0.2)
        self.assertEqual([(x['vao'], x['ket'], x['usd']) for x in r], [(99.5, 'SL', round(-2.0 - PP.PHI, 2))])     # không được chọn A nhờ biết trước rằng sau đó A sẽ khớp
        # A khớp TRƯỚC khi B đến: lệnh là A, B rơi vào lúc A còn mở nên bỏ
        m1 = _m1(self.t, self.phang * 10 + [(98.5, 98.6, 97.7, 98.0)] + self.phang * 3000)
        r = PP.cham([a, b], m1, 0.2)
        self.assertEqual([(x['vao'], x['ket']) for x in r], [(98.0, 'Hết giờ')])
        # B (chờ bán 101) đến rồi không bao giờ khớp; giá về mức chờ của A sau khi B đã đến: A đã bị hủy, không có lệnh nào
        ban = {**self.mua, 't': self.t + pd.Timedelta(minutes=30), 'huong': 'BAN', 'kieu': 'gioi_han', 'vao': 101.0, 'sl': 103.0}
        m1 = _m1(self.t, self.phang * 40 + [(98.5, 98.6, 97.7, 98.0)] + self.phang * 3000)
        self.assertEqual(PP.cham([a, ban], m1, 0.2), [])
        self.assertEqual(len(PP.cham([a], m1, 0.2)), 1)                                      # chỉ có A thì A vẫn khớp ở phút 40

    def test_lenh_cho_da_bi_gia_vuot_luc_tin_hieu_den_thi_bo(self):
        # Trang Biểu đồ báo "tín hiệu đã qua" khi giá đã ở bên kia mức chờ ngay lúc tín hiệu đến; phép chấm cũng không được tính lệnh đó.
        cho = {**self.mua, 'kieu': 'gioi_han', 'vao': 99.0, 'sl': 97.0}
        self.assertEqual(PP.cham([cho], _m1(self.t, [(98.9, 99.0, 98.8, 98.9)] + self.phang * 3000), 0.2), [])
        self.assertEqual(PP.cham([cho], _m1(self.t, [(99.0, 99.1, 98.9, 99.0)] + self.phang * 3000), 0.2), [])       # Bid mở đúng bằng mức chờ: cũng coi là đã qua
        ban = {**self.mua, 'huong': 'BAN', 'kieu': 'gioi_han', 'vao': 101.0, 'sl': 103.0}
        self.assertEqual(PP.cham([ban], _m1(self.t, [(101.2, 101.3, 101.1, 101.2)] + self.phang * 3000), 0.2), [])
        # nến đầu mở chưa vượt, rồi trong nến mới chạm: vẫn khớp ở mức chờ
        r = PP.cham([cho], _m1(self.t, [(99.5, 99.6, 98.7, 99.4)] + self.phang * 3000), 0.2)
        self.assertEqual([(x['vao'], x['ket']) for x in r], [(99.0, 'Hết giờ')])
        # nến SAU mở cửa nhảy qua mức chờ: vẫn khớp, và vẫn chỉ tính ở mức chờ (không cộng phần nhảy có lợi)
        r = PP.cham([cho], _m1(self.t, self.phang * 5 + [(98.5, 98.6, 98.4, 98.5)] + self.phang * 3000), 0.2)
        self.assertEqual([(x['vao'], x['ket']) for x in r], [(99.0, 'Hết giờ')])

    def test_cham_doc_lap_cung_quy_tac_lenh_cho(self):
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location('nghien_cuu', Path(__file__).resolve().parent.parent / 'cong-cu' / 'nghien_cuu.py')
        nc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(nc)
        cho = {**self.mua, 'kieu': 'gioi_han', 'vao': 99.0, 'sl': 97.0}

        def doc_lap(nen):
            m1 = _m1(self.t, nen)
            T = m1.index.as_unit('ns').asi8
            O, H, L, C = (m1[k].to_numpy(dtype=float) for k in ('open', 'high', 'low', 'close'))
            return nc.cham_doc_lap([cho], T, O, H, L, C, 0.2, PP.PHI)

        self.assertEqual(len(doc_lap([(98.9, 99.0, 98.8, 98.9)] + self.phang * 3000)), 0)                             # đã bị giá vượt lúc tín hiệu đến: bỏ
        nen = self.phang * 5 + [(99.5, 99.6, 98.7, 99.0)] + [(99.0, 103.2, 98.9, 103.0)] + self.phang * 3000
        d = doc_lap(nen)
        self.assertEqual(len(d), 1)
        self.assertAlmostEqual(float(d['r2'].iloc[0]), PP.cham([cho], _m1(self.t, nen), 0.2)[0]['usd'] / 2.0, places=2)   # rủi ro 2,0: cùng kết quả với cham()

    def test_moi_luc_mot_lenh_va_don_vi_gio(self):
        sau = {**self.mua, 't': self.t + pd.Timedelta(minutes=30)}
        m1 = _m1(self.t, self.phang * 3000)
        self.assertEqual(len(PP.cham([self.mua, sau], m1, 0.2)), 1)                          # lệnh thứ hai rơi vào lúc lệnh đầu còn mở
        giay = m1.copy()
        giay.index = giay.index.as_unit('s')                                                 # bảng nến lưu giờ theo giây vẫn phải chấm được
        self.assertEqual(len(PP.cham([self.mua], giay, 0.2)), 1)


class HienTaiTest(unittest.TestCase):
    def test_pha_vo_luc_nay_va_het_hieu_luc(self):
        m = _m15(120)
        _dat(m, 119, open=100.0, close=101.2, high=101.3, low=99.9)
        dong = (m.index[119] + timedelta(minutes=15)).to_pydatetime()
        p = PP.phuong_an('pha_vo', m, _h1(m), 101.2, 101.4, dong + timedelta(minutes=2), [])
        self.assertTrue(p['co'] and p['hieu_luc'])
        self.assertEqual((p['huong'], p['vao'], p['nhom'], p['rr']), ('MUA', 101.4, 'pp', [1.0, 2.0]))
        self.assertAlmostEqual(p['tp'][1] - p['vao'], 2 * p['rui_ro_gia'], places=1)
        self.assertEqual((p['muc_tieu']['gia'], p['muc_tieu']['ten'][:11]), (101.5, 'đo biên độ:'))    # đỉnh 100,5 cộng chiều cao vùng 1,0
        self.assertGreater(p['muc_tieu']['r'], 0)
        tre = PP.phuong_an('pha_vo', m, _h1(m), 101.2, 101.4, dong + timedelta(minutes=12), [])
        self.assertFalse(tre['hieu_luc'])
        self.assertIn('12 phút trước', tre['vi_sao_het'][0])
        cu = PP.phuong_an('pha_vo', m, _h1(m), 101.2, 101.4, dong + timedelta(minutes=2), ['Giá đã cũ 300 phút.'])
        self.assertEqual((cu['hieu_luc'], cu['vi_sao_het']), (False, ['Giá đã cũ 300 phút.']))
        khong = PP.phuong_an('pha_vo', _m15(120), _h1(_m15(120)), 100.0, 100.2, dong, [])
        self.assertEqual((khong['co'], khong['hieu_luc']), (False, False))
        self.assertTrue(khong['vi_sao'])

    def test_ict_lenh_cho_con_song_da_khop_va_het_han(self):
        m = _m15(120)
        _dat(m, 112, low=98.9)
        _dat(m, 114, open=100.0, close=102.0, high=102.1, low=100.0)
        _dat(m, 115, open=102.0, close=102.5, high=102.6, low=101.2)
        for i in range(116, 120):
            _dat(m, i, open=102.5, close=102.5, high=102.9, low=102.1)                       # giá đứng trên, chưa quay về mức chờ 100,85
        luc = (m.index[119] + timedelta(minutes=15)).to_pydatetime() + timedelta(minutes=1)
        p, _ = PP.hien_tai('ict', m, _h1(m), 102.5, 102.7, luc)
        self.assertEqual((p['huong'], p['kieu']), ('MUA', PP.DS['ict']['kieu']))
        self.assertAlmostEqual(p['vao'], 100.85)
        self.assertEqual(p['vung'], [100.5, 101.2])
        self.assertEqual(p['con_phut'], PP.CHO_NEN * 15 - 61)                                # tín hiệu ở nến 115, đã qua 4 nến và 1 phút
        self.assertEqual(p['muc_tieu'], 102.6)                                               # thanh khoản đối diện: đỉnh 5 giờ tính tới nến tín hiệu
        pa = PP.phuong_an('ict', m, _h1(m), 102.5, 102.7, luc, [])
        self.assertEqual((pa['muc_tieu']['gia'], pa['muc_tieu']['r']), (102.6, round((102.6 - 100.85) / (100.85 - p['sl']), 2)))
        self.assertIsNone(PP.hien_tai('ict', m, _h1(m), 100.7, 100.8, luc)[0])               # giá hiện tại đã về mức chờ: coi như đã khớp
        self.assertIn('quá 4 giờ', PP.hien_tai('ict', m, _h1(m), 102.5, 102.7, luc + timedelta(hours=4))[1])


def _tang(n=400, buoc=0.1):
    """n nến M15 tăng đều: H1 có xu hướng tăng, không nến nào để lại khoảng trống giá."""
    idx = pd.date_range(T0, periods=n, freq='15min')
    c = 100 + buoc * np.arange(n)
    return pd.DataFrame({'open': c - buoc / 2, 'high': c + 0.3, 'low': c - 0.3, 'close': c}, index=idx), c


class IctTest(unittest.TestCase):
    def test_hoi_ve_khoang_trong_sau_khi_pha_cau_truc(self):
        m, c = _tang()
        self.assertEqual(PP.quet('ict_fvg', m, _h1(m)), [])                                  # tăng đều: không có khoảng trống giá
        n = len(m)
        _dat(m, n - 2, open=c[n - 3], close=c[n - 3] + 2.0, high=c[n - 3] + 2.1, low=c[n - 3] - 0.1)   # nến bật mạnh
        _dat(m, n - 1, open=c[n - 3] + 2.0, close=c[n - 3] + 2.6, high=c[n - 3] + 2.7, low=c[n - 3] + 1.5)   # đáy nằm trên đỉnh nến n−3
        th = PP.quet('ict_fvg', m, _h1(m))
        self.assertEqual([(s['i'], s['huong'], s['kieu']) for s in th], [(n - 1, 'MUA', 'gioi_han')])
        duoi, tren = c[n - 3] + 0.3, c[n - 3] + 1.5
        self.assertAlmostEqual(th[0]['vao'], (duoi + tren) / 2)                              # giữa khoảng trống
        self.assertEqual([round(v, 6) for v in th[0]['vung']], [round(duoi, 6), round(tren, 6)])
        self.assertLess(th[0]['sl'], c[n - 3] - 0.3)                                         # dưới điểm bắt đầu nhịp bật
        g, cg = _tang(buoc=-0.1)                                                             # H1 giảm thì nhịp bật lên không phải tín hiệu
        _dat(g, n - 2, open=cg[n - 3], close=cg[n - 3] + 2.0, high=cg[n - 3] + 2.1, low=cg[n - 3] - 0.1)
        _dat(g, n - 1, open=cg[n - 3] + 2.0, close=cg[n - 3] + 2.6, high=cg[n - 3] + 2.7, low=cg[n - 3] + 1.5)
        self.assertEqual(PP.quet('ict_fvg', g, _h1(g)), [])

    def test_hai_mo_hinh_chung_mot_nut(self):
        self.assertEqual((PP.DS['ict']['chip'], PP.DS['ict_fvg']['chip']), ('ict', 'ict'))
        m = _m15(120)
        p = PP.phuong_an('ict_fvg', m, _h1(m), 100.0, 100.2, (m.index[-1] + timedelta(minutes=16)).to_pydatetime(), [])
        self.assertEqual((p['chip'], p['co'], p['nhom']), ('ict', False, 'pp'))
        self.assertEqual(PP.phuong_an('pha_vo', m, _h1(m), 100.0, 100.2, T0 + timedelta(days=2), [])['chip'], 'pha_vo')

    def test_ban_do_khi_chua_du_nen(self):
        m = _m15(100)
        self.assertEqual(PP.ban_do_ict(m, _h1(m), 100.0, T0 + timedelta(days=2)), {'du': False})

    def test_ban_do_co_khoang_trong_quet_va_diem_vao(self):
        m = _m15(200)
        _dat(m, 192, low=98.9)                                                               # quét đáy 5 giờ rồi đóng trở lại
        _dat(m, 194, open=100.0, close=102.0, high=102.1, low=100.0)
        _dat(m, 195, open=102.0, close=102.5, high=102.6, low=101.2)                         # khoảng trống giá tăng 100,5–101,2
        for i in range(196, 200):
            _dat(m, i, open=102.5, close=102.5, high=102.9, low=102.1)
        luc = (m.index[199] + timedelta(minutes=16)).to_pydatetime()
        b = PP.ban_do_ict(m, _h1(m), 102.5, luc)
        self.assertTrue(b['du'] and b['co_lenh'])
        self.assertEqual(b['huong_xet'], 'MUA')
        self.assertEqual([(z['duoi'], z['tren'], z['huong'], z['da_cham']) for z in b['fvg']], [(100.5, 101.2, 'tang', False)])
        self.assertEqual(b['fvg'][0]['t'], int(m.index[193].timestamp()))                    # hộp bắt đầu từ nến đầu của bộ ba
        self.assertIn({'t': int(m.index[192].timestamp()), 'gia': 98.9, 'loai': 'day'}, b['quet'])
        self.assertEqual((b['bsl'], b['ssl'], b['t_tk']), (102.9, 98.9, int(m.index[180].timestamp())))
        self.assertEqual((b['cau_truc'][-1]['huong'], b['cau_truc'][-1]['loai']), ('tang', 'BOS'))    # nến bật đóng vượt đỉnh đi ngang
        self.assertEqual(b['vi_tri'], 'premium')                                             # giá ở nửa trên của biên độ 98,9–102,9
        dk = b['dieu_kien']
        self.assertEqual(len(dk), 5)
        self.assertEqual([x['dat'] for x in dk][1:], [True, False, True, True])              # cấu trúc ✓, mua ở premium ✗, đã quét đáy ✓, có điểm vào ✓
        self.assertIn('100,85', dk[4]['chi_tiet'])                                           # số viết kiểu Việt Nam
        self.assertIn('98,90', dk[3]['chi_tiet'])
        p = PP.phuong_an('ict', m, _h1(m), 102.5, 102.7, luc, [])
        self.assertIn('100,5–101,2', p['ly_do'])                                             # lý do cũng viết dấu phẩy thập phân
        lap = m.copy()                                                                       # giá quay về lấp hết khoảng trống: không còn trong bản đồ
        _dat(lap, 199, open=102.5, close=100.4, high=102.6, low=100.3)
        self.assertEqual(PP.ban_do_ict(lap, _h1(lap), 100.4, luc)['fvg'], [])

    def test_ban_do_khong_co_gi_khi_di_ngang(self):
        m = _m15(200)
        b = PP.ban_do_ict(m, _h1(m), 100.0, (m.index[-1] + timedelta(minutes=16)).to_pydatetime())
        self.assertEqual((b['fvg'], b['quet'], b['cau_truc'], b['co_lenh'], b['huong_xet']), ([], [], [], False, None))
        self.assertEqual([x['dat'] for x in b['dieu_kien']], [False, None, None, False, False])
        self.assertEqual(len(b['kich_ban']), 1)


def _song(gia):
    """Nến M15 nối tiếp theo chuỗi giá đóng `gia`: mở bằng đóng nến trước, đỉnh và đáy rộng thêm 0,3."""
    idx = pd.date_range(T0, periods=len(gia), freq='15min')
    c = np.array(gia, dtype=float)
    o = np.concatenate([[c[0]], c[:-1]])
    return pd.DataFrame({'open': o, 'high': np.maximum(o, c) + 0.3, 'low': np.minimum(o, c) - 0.3, 'close': c}, index=idx)


class ElliottTest(unittest.TestCase):
    PHANG = [100.0] * 100
    S12 = [101.0, 102.0, 103.0, 104.0, 105.0, 104.2, 103.4, 102.6, 103.4, 104.2, 105.0]       # sóng 1 lên 105, sóng 2 hồi về 102,6

    def test_zigzag_chi_xac_nhan_sau_khi_dao_chieu_du_lon(self):
        m = _song(self.PHANG + self.S12)
        piv = PP._zigzag(m['high'].to_numpy(), m['low'].to_numpy(), PP._atr(m).to_numpy())
        self.assertEqual([(q[1], round(q[2], 1)) for q in piv], [('L', 99.7), ('H', 105.3), ('L', 102.3)])
        self.assertTrue(all(q[3] > q[0] for q in piv))                                       # điểm xoay luôn được xác nhận ở một nến SAU nó

    def test_vao_song_3_khi_nen_dong_vuot_dinh_song_1(self):
        m = _song(self.PHANG + self.S12)
        self.assertEqual(PP.quet('elliott', m, _h1(m)), [])                                  # chưa có nến nào đóng trên 105,3
        m = _song(self.PHANG + self.S12 + [105.8])
        th = PP.quet('elliott', m, _h1(m))
        self.assertEqual([(s['i'], s['huong'], s['kieu']) for s in th], [(len(m) - 1, 'MUA', 'thi_truong')])
        s = th[0]
        self.assertAlmostEqual(s['sl'], 102.3 - PP.DEM_ATR * s['atr'], places=6)             # ngay dưới cuối sóng 2
        self.assertAlmostEqual(s['muc_tieu'], 102.3 + PP.E_MR * (105.3 - 99.7), places=6)    # sóng 3 = 1,618 × sóng 1, tính từ cuối sóng 2
        self.assertEqual([(q['nhan'], round(q['gia'], 1)) for q in s['song']], [('0', 99.7), ('1', 105.3), ('2', 102.3)])
        self.assertEqual(len(PP.quet('elliott', _song(self.PHANG + self.S12 + [105.8, 106.5, 107.0]), _h1(m))), 1)    # mỗi cặp sóng 1–2 chỉ một tín hiệu

    def test_song_2_hoi_qua_sau_hoac_bi_thung_thi_khong_vao(self):
        sau = self.PHANG + [101.0, 102.0, 103.0, 104.0, 105.0, 103.5, 102.0, 100.6, 102.0, 103.5, 105.0, 105.8]    # hồi 86% của sóng 1
        self.assertEqual(PP.quet('elliott', _song(sau), _h1(_song(sau))), [])
        thung = self.PHANG + self.S12[:-1] + [103.0, 101.9, 103.5, 105.0, 105.8]            # giá thủng cuối sóng 2 (102,3) trước khi vượt đỉnh sóng 1
        self.assertEqual([s for s in PP.quet('elliott', _song(thung), _h1(_song(thung))) if s['song'][2]['gia'] == 102.3], [])

    def test_kich_ban_cho_va_phuong_an(self):
        m = _song(self.PHANG + self.S12)
        luc = (m.index[-1] + timedelta(minutes=16)).to_pydatetime()
        cho = PP.elliott_cho(m)
        self.assertEqual((cho['huong'], cho['kich_hoat'], [q['nhan'] for q in cho['song']]), ('MUA', 105.3, ['0', '1', '2']))
        self.assertIn('Chờ nến M15 đóng trên 105,30', cho['chu'])
        p = PP.phuong_an('elliott', m, _h1(m), 105.0, 105.2, luc, [])
        self.assertEqual((p['co'], p['cho']['kich_hoat'], p['vi_sao']), (False, 105.3, cho['chu']))
        dang = PP.elliott_cho(_song(self.PHANG + self.S12[:7]))                              # sóng 1 xong, sóng 2 mới hồi, chưa được xác nhận
        self.assertEqual(([q['nhan'] for q in dang['song']], 'kich_hoat' in dang), (['0', '1'], False))
        self.assertIn('sóng 2 đang hồi', dang['chu'])
        m2 = _song(self.PHANG + self.S12 + [105.8])
        p2 = PP.phuong_an('elliott', m2, _h1(m2), 105.8, 106.0, (m2.index[-1] + timedelta(minutes=16)).to_pydatetime(), [])
        self.assertTrue(p2['co'] and p2['hieu_luc'])
        self.assertEqual((p2['huong'], [q['nhan'] for q in p2['song']], p2['muc_tieu']['ten'][:6]), ('MUA', ['0', '1', '2'], 'sóng 3'))

    def test_chot_o_muc_tieu_ly_thuyet(self):
        t = pd.Timestamp(T0 + timedelta(days=3))
        mua = {'t': t, 'huong': 'MUA', 'kieu': 'thi_truong', 'vao': 100.0, 'sl': 98.0, 'atr': 1.0, 'muc_tieu': 101.0}
        phang = [(100.0, 100.2, 99.9, 100.0)]
        m1 = _m1(t, phang * 3 + [(100.5, 101.1, 100.4, 101.0)] + phang * 1500)
        self.assertEqual(PP.cham([mua], m1, 0.0, phi=0.0)[0]['ket'], 'Hết giờ')              # chốt ở 2R (104) thì chưa tới
        self.assertEqual(PP.cham([mua], m1, 0.0, phi=0.0, tp_r=0.5)[0]['ket'], 'TP')         # chốt ở 0,5R (101) thì tới
        self.assertEqual(PP.cham([mua], m1, 0.0, phi=0.0, tp_r=1.0)[0]['ket'], 'Hết giờ')    # chốt ở 1R (102) thì chưa
        r = PP.cham([mua], m1, 0.0, phi=0.0, theo_muc_tieu=True)
        self.assertEqual((r[0]['ket'], r[0]['usd'], r[0]['r']), ('TP', 1.0, 0.5))            # chốt ở mục tiêu 101: +1,0 = 0,5R
        self.assertEqual(PP.cham([{**mua, 'muc_tieu': 99.0}], m1, 0.0, phi=0.0, theo_muc_tieu=True), [])     # mục tiêu nằm sai phía: bỏ qua
        self.assertEqual(PP.cham([{k: v for k, v in mua.items() if k != 'muc_tieu'}], m1, 0.0, phi=0.0, theo_muc_tieu=True), [])


if __name__ == '__main__':
    unittest.main()
