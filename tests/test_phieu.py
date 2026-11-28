# -*- coding: utf-8 -*-
"""Phiếu vào lệnh (so_cong_khai/phieu.py): công thức đã qua cổng, mức giá của phiếu, và trạng thái lúc sống của từng loại lệnh."""
import importlib.util
import json
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from so_cong_khai import phieu, phuong_phap as PP

T0 = datetime(2026, 6, 1, tzinfo=timezone.utc)


def _m15(n, gia=100.0):
    idx = pd.date_range(T0, periods=n, freq='15min')
    return pd.DataFrame({'open': gia, 'high': gia + 0.5, 'low': gia - 0.5, 'close': gia}, index=idx)


def _khung(m15, quy):
    return m15.resample(quy).agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()


def _dat(df, i, **kw):
    for k, v in kw.items():
        df.iloc[i, df.columns.get_loc(k)] = v


class CongThuc(unittest.TestCase):
    def test_du_tam_phuong_phap_va_ma_hop_le(self):
        self.assertEqual(set(phieu.CONG_THUC), set(PP.DS))
        for ma, ct in phieu.CONG_THUC.items():
            self.assertIn(ct['vao'], ('V0', 'V1', 'V2', 'V3'), ma)
            self.assertIn(ct['sl'], ('S0', 'S1', 'S2', 'S3'), ma)
            self.assertEqual(ct['tp'], 'T0', ma)
            self.assertTrue(set(ct['loc']) <= {'L1', 'L2', 'L3', 'L4', 'L6', 'H2'}, ma)
            self.assertNotEqual(phieu.muc_cho({'huong': 'MUA', 'vao': 1.0, 'vung': [0.5, 1.5], 'nen_h': 2.0, 'nen_l': 0.0}, ma, ct['vao'])[0], 'xn', ma)   # lúc sống chưa hỗ trợ xác nhận M5

    def test_cong_cu_do_dung_chung_ham(self):
        spec = importlib.util.spec_from_file_location('diem_vao', Path(__file__).resolve().parent.parent / 'cong-cu' / 'diem_vao.py')
        dv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dv)
        self.assertIs(dv.muc_cho, phieu.muc_cho)                         # mức giá trên phiếu là mức đã được đo
        self.assertIs(dv.muc_sl, phieu.muc_sl)

    def test_so_do_doc_tu_tep(self):
        with tempfile.TemporaryDirectory() as d:
            tep = Path(d) / 'diem-vao.json'
            self.assertIsNone(phieu.so_do('ict', tep))
            tep.write_text(json.dumps({'cat_nam': 2022, 'so_phep_so': 107, 'pp': {'ict': {'A': {'moi': {'chinh': 1}}, 'cuoi': {'chinh': 2}}}}), encoding='utf-8')
            self.assertEqual(phieu.so_do('ict', tep), {'goc': {'chinh': 1}, 'phieu': {'chinh': 2}, 'so_phep_so': 107, 'cat_nam': 2022})
            self.assertIsNone(phieu.so_do('fib', tep))


# Công thức trước khi có bộ lọc xu hướng nhiều khung (L6): các bài kiểm cơ chế lúc sống dùng giá đi ngang, nơi L6 luôn chặn tín hiệu.
TRUOC_L6 = {ma: dict(ct, loc=tuple(k for k in ct['loc'] if k not in ('L6', 'H2'))) for ma, ct in phieu.CONG_THUC.items()}


class LucSong(unittest.TestCase):
    """Cơ chế lúc sống (mức giá, trạng thái lệnh chờ). Chạy với công thức trước L6; L6 được kiểm riêng ở XuHuongNhieuKhung."""
    def setUp(self):
        p = mock.patch.dict(phieu.CONG_THUC, TRUOC_L6)
        p.start()
        self.addCleanup(p.stop)

    def _pha_vo(self):
        m = _m15(120)
        _dat(m, 119, open=100.0, close=101.0, high=101.1, low=100.0)      # nến cuối đóng vượt đỉnh 8 giờ, thân 1 ATR
        return m, m.index[-1].to_pydatetime() + timedelta(minutes=16)

    def _lap(self, m, now, bid, ask=None, tin=()):
        return phieu.lap('pha_vo', m, _khung(m, '1h'), _khung(m, '4h'), bid, ask if ask is not None else bid + 0.05, now, list(tin), 0.17)

    def test_cho_dung_o_dinh_nen_tin_hieu_va_dung_lo_noi_them(self):
        m, now = self._pha_vo()
        s = next(x for x in PP.quet('pha_vo', m, _khung(m, '1h')) if x['i'] == 119)
        f = self._lap(m, now, 101.0)
        self.assertEqual((f['huong'], f['loai'], f['trang_thai']), ('MUA', 'dung', 'con_hieu_luc'))
        self.assertAlmostEqual(f['vao'], 101.1)                           # đỉnh nến tín hiệu
        self.assertAlmostEqual(f['sl'], round(s['sl'] - 0.5 * s['atr'], 2))
        rui = 101.1 - (s['sl'] - 0.5 * s['atr'])
        self.assertAlmostEqual(f['tp'][1], round(101.1 + 2 * rui, 2))
        self.assertEqual(f['con_phut'], 239)
        self.assertEqual([d['bat_buoc'] for d in f['dieu_kien']], [False, False, False, True, False])   # công thức trước L6: chỉ bộ lọc H4
        self.assertTrue(f['khac_luat_goc'])

    def test_da_khop_va_da_huy(self):
        m, now = self._pha_vo()
        self.assertEqual(self._lap(m, now, 101.2)['trang_thai'], 'da_khop')       # Ask đã vượt đỉnh nến tín hiệu
        self.assertEqual(self._lap(m, now, 98.0)['trang_thai'], 'da_huy')         # giá chạm dừng lỗ trước khi lệnh được kích hoạt
        self.assertEqual(self._lap(m, now + timedelta(hours=5), 101.0)['trang_thai'], 'het_han')

    def test_spread_gian_thi_dieu_kien_spread_chua_dat(self):
        m, now = self._pha_vo()
        f = self._lap(m, now, 100.5, ask=101.0)                           # spread 0,5 > 2 × 0,17
        self.assertFalse(next(d for d in f['dieu_kien'] if d['ma'] == 'L2')['dat'])
        self.assertEqual(f['trang_thai'], 'con_hieu_luc')                 # với Phá vỡ, bộ lọc spread không bắt buộc

    def test_tin_gan_thi_dieu_kien_tin_chua_dat(self):
        m, now = self._pha_vo()
        f = self._lap(m, now, 101.0, tin=[now + timedelta(minutes=30)])
        self.assertFalse(next(d for d in f['dieu_kien'] if d['ma'] == 'L1')['dat'])

    def test_khong_co_tin_hieu_thi_khong_co_phieu(self):
        m = _m15(120)
        self.assertIsNone(phieu.lap('pha_vo', m, _khung(m, '1h'), _khung(m, '4h'), 100.0, 100.05, m.index[-1].to_pydatetime() + timedelta(minutes=16), [], 0.17))

    def test_ict_vao_ngay_chi_trong_vai_phut(self):
        m = _m15(120)
        _dat(m, 116, low=98.9)                                            # quét đáy 5 giờ
        _dat(m, 118, open=100.0, close=102.0, high=102.1, low=100.0)      # nến đẩy
        _dat(m, 119, open=102.0, close=102.5, high=102.6, low=101.2)      # khoảng trống giá 100,5–101,2
        luc = m.index[-1].to_pydatetime() + timedelta(minutes=16)
        lap = lambda now: phieu.lap('ict', m, _khung(m, '1h'), _khung(m, '4h'), 102.5, 102.55, now, [], 0.17)   # noqa: E731
        f = lap(luc)
        self.assertEqual((f['loai'], f['huong']), ('tt', 'MUA'))          # phiếu của ICT: vào ngay, không chờ về giữa khoảng trống
        self.assertAlmostEqual(f['vao'], 102.55)                          # mua ở Ask
        self.assertIn(f['trang_thai'], ('con_hieu_luc', 'rui_ro'))
        self.assertEqual(lap(luc + timedelta(minutes=10))['trang_thai'], 'qua_tre')
        self.assertEqual((f['vao_luc'], f['ket_cuc']), ('hien_tai', None))


def _xu_huong(tang: bool, freq: str, n: int = 120):
    """Nến của một khung đi một chiều đều (tăng hoặc giảm), kết thúc trước T0 để mọi nến đều đã đóng lúc tín hiệu."""
    buoc = 1.0 if tang else -1.0
    idx = pd.date_range(end=T0 - pd.Timedelta(freq), periods=n, freq=freq)
    c = pd.Series([100.0 + buoc * i for i in range(n)], index=idx)
    return pd.DataFrame({'open': c, 'high': c + 0.5, 'low': c - 0.5, 'close': c})


class XuHuongNhieuKhung(unittest.TestCase):
    """Bộ lọc L6 (D1, H4, H1 cùng chiều lệnh), qua cổng ngày 25/11/2026 ở bốn phương pháp (cong-cu/loc_xu_huong.py)."""
    S = {'huong': 'MUA', 't': pd.Timestamp(T0), 'i': 5, 'vao': 100.0, 'sl': 99.0}

    def _dk(self, d1, h4, h1, huong='MUA'):
        m = _m15(10)
        return phieu.dieu_kien(dict(self.S, huong=huong), m, h4, [], 0.1, 0.17, h1, d1)['L6']

    def test_ca_ba_khung_cung_chieu(self):
        up = {k: _xu_huong(True, f) for k, f in (('d1', '1D'), ('h4', '4h'), ('h1', '1h'))}
        dn = {k: _xu_huong(False, f) for k, f in (('d1', '1D'), ('h4', '4h'), ('h1', '1h'))}
        self.assertTrue(self._dk(**up))
        self.assertFalse(self._dk(**up, huong='BAN'))
        self.assertTrue(self._dk(**dn, huong='BAN'))
        self.assertFalse(self._dk(dn['d1'], up['h4'], up['h1']))          # chỉ D1 ngược chiều cũng không đạt
        self.assertFalse(self._dk(None, up['h4'], up['h1']))              # thiếu D1: coi là chưa đạt

    def test_khong_nhin_truoc_nen_chua_dong(self):
        d1 = _xu_huong(True, '1D')
        sau = pd.DataFrame({'open': 0.0, 'high': 0.0, 'low': 0.0, 'close': [1e6]}, index=[pd.Timestamp(T0)])   # nến D1 mở đúng lúc tín hiệu: chưa đóng
        self.assertEqual(phieu.xu(pd.concat([d1, sau]), pd.Timedelta(days=1), pd.Timestamp(T0)), phieu.xu(d1, pd.Timedelta(days=1), pd.Timestamp(T0)))

    def test_cong_thuc_bon_phuong_phap_qua_cong(self):
        self.assertEqual({m for m, ct in phieu.CONG_THUC.items() if 'L6' in ct['loc']}, {'pha_vo', 'ict', 'wyckoff', 'ema_hoi'})

    def test_phieu_thieu_xu_huong_thi_bi_loc(self):
        m = _m15(120)
        _dat(m, 119, open=100.0, close=101.0, high=101.1, low=100.0)
        f = phieu.lap('pha_vo', m, _khung(m, '1h'), _khung(m, '4h'), 101.0, 101.05, m.index[-1].to_pydatetime() + timedelta(minutes=16), [], 0.17)
        self.assertEqual(f['trang_thai'], 'bi_loc')                       # giá đi ngang: không khung nào có xu hướng
        self.assertIn(phieu.TEN_LOC['L6'], f['loc_hong'])
        self.assertTrue(next(d for d in f['dieu_kien'] if d['ma'] == 'L6')['bat_buoc'])

    def test_so_do_dung_ban_co_l6(self):
        with tempfile.TemporaryDirectory() as d:
            tep = Path(d) / 'diem-vao.json'
            tep.write_text(json.dumps({'cat_nam': 2022, 'so_phep_so': 107, 'pp': {'ict': {'A': {'moi': {'chinh': 1}}, 'cuoi': {'chinh': 2}}}}), encoding='utf-8')
            (Path(d) / 'loc-xu-huong.json').write_text(json.dumps({'so_phep_so': 16, 'pp': {'ict': {'giu': 'L6', 'bang': {'L6': {'chinh': 3}}}}}), encoding='utf-8')
            self.assertEqual(phieu.so_do('ict', tep), {'goc': {'chinh': 1}, 'phieu': {'chinh': 3}, 'so_phep_so': 123, 'cat_nam': 2022})


class QuaHanVaoNgay(unittest.TestCase):
    """Phiếu vào ngay đã quá hạn: giá vào phải là giá lúc tín hiệu đến chứ không phải giá hiện tại. Lỗi ngày 24/11/2026: phiếu MUA lấy giá hiện tại
    (đã rơi qua dừng lỗ) làm giá vào, nên dừng lỗ nằm TRÊN giá vào và hai mức chốt nằm DƯỚI."""

    def _ict_mua(self, sau):
        m = _m15(120 + len(sau))
        _dat(m, 116, low=98.9)                                            # quét đáy 5 giờ
        _dat(m, 118, open=100.0, close=102.0, high=102.1, low=100.0)      # nến đẩy
        _dat(m, 119, open=102.0, close=102.5, high=102.6, low=101.2)      # khoảng trống giá 100,5–101,2: tín hiệu MUA ở nến 119
        for k, (o, h, l, c) in enumerate(sau):
            _dat(m, 120 + k, open=o, high=h, low=l, close=c)
        return m

    def _lap(self, m, bid):
        return phieu.lap('ict', m, _khung(m, '1h'), _khung(m, '4h'), bid, bid + 0.05, m.index[-1].to_pydatetime() + timedelta(minutes=16), [], 0.17)

    def _dung_phia(self, f):
        dau = 1 if f['huong'] == 'MUA' else -1
        self.assertGreater((f['vao'] - f['sl']) * dau, 0, f)              # dừng lỗ ở phía thua
        self.assertGreater((f['tp'][0] - f['vao']) * dau, 0, f)           # chốt lời ở phía thắng
        self.assertGreater((f['tp'][1] - f['tp'][0]) * dau, 0, f)

    def test_gia_da_roi_qua_dung_lo_thi_muc_van_dung_phia(self):
        m = self._ict_mua([(102.5, 102.6, 102.0, 102.1), (102.1, 102.2, 96.9, 97.0), (97.0, 97.1, 96.9, 97.0)])
        f = self._lap(m, 97.0)                                            # giá hiện tại 97, dưới cả dừng lỗ
        self.assertEqual((f['huong'], f['nen'], f['trang_thai']), ('MUA', (m.index[119] + timedelta(minutes=15)).isoformat(), 'qua_tre'))   # 'nen' là giờ đóng nến tín hiệu
        self._dung_phia(f)
        self.assertAlmostEqual(f['vao'], 102.55)                          # giá mở nến ngay sau tín hiệu (102,5) cộng spread: giá mà phép đo đã vào
        self.assertEqual((f['vao_luc'], f['ket_cuc']), ('tin_hieu', 'sl'))

    def test_qua_han_ma_da_cham_chot_2r(self):
        m = self._ict_mua([(102.5, 102.6, 102.4, 102.5), (102.5, 120.0, 102.4, 119.0)])
        f = self._lap(m, 119.0)
        self.assertEqual((f['trang_thai'], f['vao_luc'], f['ket_cuc']), ('qua_tre', 'tin_hieu', 'tp'))
        self._dung_phia(f)

    def test_qua_han_ma_chua_cham_muc_nao(self):
        m = self._ict_mua([(102.5, 102.6, 102.4, 102.5)])
        f = self._lap(m, 102.5)
        self.assertEqual((f['trang_thai'], f['vao_luc'], f['ket_cuc']), ('qua_tre', 'tin_hieu', None))

    def test_moi_phieu_deu_co_muc_dung_phia(self):
        import numpy as np
        rng = np.random.default_rng(7)
        n = 700
        c = 2000 + np.cumsum(rng.normal(0, 1.5, n))
        o = np.concatenate([[c[0]], c[:-1]])
        m = pd.DataFrame({'open': o, 'high': np.maximum(o, c) + rng.uniform(0, 1.5, n), 'low': np.minimum(o, c) - rng.uniform(0, 1.5, n), 'close': c},
                         index=pd.date_range(T0, periods=n, freq='15min'))
        dem = 0
        for cuoi in range(420, n, 7):
            x = m.iloc[:cuoi]
            h1, h4 = _khung(x, '1h'), _khung(x, '4h')
            for ma in phieu.CONG_THUC:
                for lech in (-40.0, 0.0, 40.0):                           # giá hiện tại đã chạy xa về cả hai phía
                    bid = float(x['close'].iloc[-1]) + lech
                    f = phieu.lap(ma, x, h1, h4, bid, bid + 0.2, x.index[-1].to_pydatetime() + timedelta(minutes=16), [], 0.17)
                    if f:
                        self._dung_phia(f)
                        dem += 1
        self.assertGreater(dem, 50)


class GhiNhatKy(unittest.TestCase):
    """Phiếu còn hiệu lực được ghi vào nhật ký điểm vào như một dòng riêng (mã 'phieu:…'), rồi được chấm theo đúng loại lệnh của nó."""

    def setUp(self):
        from so_cong_khai import nhat_ky
        self.nk = nhat_ky
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = {'nhat_ky': {'bat': True, 'tep': str(Path(self.tmp.name) / 'nk.json')}, 'gia': {'ma_vang': 'XAUUSDp'}}
        self.luc = datetime(2026, 6, 1, 10, 2, tzinfo=timezone.utc)

    def tearDown(self):
        self.tmp.cleanup()

    def _phieu(self, **kw):
        f = {'ma': 'pha_vo', 'ten': 'Phá vỡ đỉnh/đáy', 'huong': 'MUA', 'loai': 'dung', 'ten_loai': 'Lệnh chờ dừng', 'trang_thai': 'con_hieu_luc', 'vao': 101.0, 'sl': 99.0,
             'tp': [103.0, 105.0], 'rr': [1.0, 2.0], 'con_phut': 240, 'nen': '2026-06-01T10:00:00+00:00', 'ly_do': 'thử'}
        f.update(kw)
        return f

    def _ghi(self, f, goc_hieu_luc=False, now=None):
        goc = {'ma': f['ma'], 'ten': f['ten'], 'nhom': 'pp', 'co': goc_hieu_luc, 'hieu_luc': goc_hieu_luc, 'huong': f['huong'], 'vao': 100.5, 'sl': 99.5, 'tp': [101.5, 102.5],
               'rr': [1.0, 2.0], 'nen': f['nen'], 'con_phut': None, 'kieu': 'vào ngay', 'phieu': f}
        return self.nk.ghi(self.cfg, {'phuong_an': [], 'phuong_phap': [goc], 'bid': 100.5, 'boi_canh': {}}, now or self.luc)

    def _m5(self, gia):
        idx = pd.date_range(datetime(2026, 6, 1, 10, 5, tzinfo=timezone.utc), periods=len(gia), freq='5min')
        return pd.DataFrame(gia, columns=['open', 'high', 'low', 'close'], index=idx)

    def test_ghi_mot_dong_rieng_va_khong_ghi_trung(self):
        moi = self._ghi(self._phieu())
        self.assertEqual([(x['ma'], x['nhom'], x['loai'], x['tt'], x['vao'], x['sl'], x['tp']) for x in moi],
                         [('phieu:pha_vo', 'phieu', 'dung', 'cho_khop', 101.0, 99.0, [103.0, 105.0])])
        self.assertEqual(self._ghi(self._phieu(), now=self.luc + timedelta(minutes=1)), [])          # cùng nến tín hiệu: không ghi lại
        hai = self._ghi(self._phieu(ma='ict', loai='tt', ten_loai='Vào ngay', con_phut=None), goc_hieu_luc=True)
        self.assertEqual(sorted((x['ma'], x['tt']) for x in hai), [('ict', 'dang_mo'), ('phieu:ict', 'dang_mo')])   # luật gốc và phiếu là hai dòng riêng

    def test_phieu_khong_con_hieu_luc_thi_khong_ghi(self):
        for tt in ('bi_loc', 'da_khop', 'da_huy', 'het_han', 'qua_tre', 'rui_ro'):
            self.assertEqual(self._ghi(self._phieu(trang_thai=tt)), [], tt)

    def test_cho_dung_mua_khop_khi_gia_vuot_roi_thang(self):
        rec = self._ghi(self._phieu())[0]
        bars = self._m5([(100.5, 100.8, 100.3, 100.6),            # Ask cao nhất 100,9: chưa vượt 101
                         (100.6, 101.2, 100.5, 101.1),            # vượt 101: khớp
                         (101.1, 105.2, 101.0, 105.0)])           # chạm chốt lời 2 (105)
        self.assertTrue(self.nk.cap_nhat(rec, bars, 0.1))
        self.assertEqual((rec['tt'], rec['r']), ('thang', 2.0))
        self.assertEqual(rec['khop'], '2026-06-01T10:15:00+00:00')

    def test_cho_dung_khac_lenh_gioi_han(self):
        bars = self._m5([(100.5, 100.6, 100.2, 100.3)] * 3)        # giá đi xuống, không bao giờ vượt 101
        dung = self._ghi(self._phieu())[0]
        self.nk.cap_nhat(dung, bars, 0.1)
        self.assertEqual(dung['tt'], 'cho_khop')                    # lệnh chờ dừng mua ở 101 chưa khớp
        gh = self._ghi(self._phieu(ma='fib', loai='gh', ten_loai='Lệnh chờ giới hạn', vao=100.4, sl=98.4, tp=[102.4, 104.4]))[0]
        self.nk.cap_nhat(gh, bars, 0.1)
        self.assertEqual(gh['tt'], 'dang_mo')                       # lệnh chờ giới hạn mua ở 100,4 thì đã khớp

    def test_cham_dung_lo_truoc_khi_kich_hoat_thi_huy(self):
        rec = self._ghi(self._phieu())[0]
        self.nk.cap_nhat(rec, self._m5([(100.5, 100.6, 98.9, 99.0)]), 0.1)
        self.assertEqual(rec['tt'], 'huy')

    def test_ban_cho_dung_va_thua(self):
        rec = self._ghi(self._phieu(huong='BAN', vao=100.0, sl=102.0, tp=[98.0, 96.0]))[0]
        bars = self._m5([(100.5, 100.6, 100.2, 100.3),            # Bid thấp nhất 100,2: chưa thủng 100
                         (100.3, 100.4, 99.8, 99.9),              # thủng 100: khớp
                         (99.9, 102.0, 99.8, 101.9)])             # Ask = 102,1 chạm dừng lỗ
        self.nk.cap_nhat(rec, bars, 0.1)
        self.assertEqual((rec['tt'], rec['r']), ('thua', -1.0))



class HopLuu(unittest.TestCase):
    """Bộ lọc hợp lưu H2 (ít nhất 2 phương pháp khác cùng chiều trong 60 phút), qua cổng ngày 26/11/2026 ở Sóng Elliott (cong-cu/hop_luu.py)."""

    def test_chi_elliott_dung_h2(self):
        self.assertEqual({m for m, ct in phieu.CONG_THUC.items() if 'H2' in ct['loc']}, {'elliott'})
        self.assertIn('H2', phieu.TEN_LOC)

    def test_dem_dung_cua_so_60_phut_va_cung_chieu(self):
        t = pd.Timestamp('2026-11-20 10:00', tz='UTC')
        ds = {'pha_vo': [{'t': t - pd.Timedelta(minutes=45), 'huong': 'MUA'}],                        # trong 60 phút, cùng chiều: tính
              'ict': [{'t': t, 'huong': 'MUA'}],                                                      # cùng lúc: tính
              'fib': [{'t': t - pd.Timedelta(minutes=75), 'huong': 'MUA'}],                           # quá 60 phút: không tính
              'ema_hoi': [{'t': t + pd.Timedelta(minutes=15), 'huong': 'MUA'}],                       # sau tín hiệu (tương lai): không tính
              'wyckoff': [{'t': t - pd.Timedelta(minutes=15), 'huong': 'BAN'}]}                       # ngược chiều: không tính
        with mock.patch.object(PP, 'quet', side_effect=lambda ma, m15, h1: ds.get(ma, [])):
            self.assertEqual(phieu.hop_luu('elliott', {'t': t, 'huong': 'MUA'}, None, None), 2)
            self.assertEqual(phieu.hop_luu('pha_vo', {'t': t, 'huong': 'MUA'}, None, None), 1)  # không tự đếm chính mình

    def test_cong_cu_do_dung_cung_cach_dem(self):
        spec = importlib.util.spec_from_file_location('hop_luu', Path(__file__).resolve().parent.parent / 'cong-cu' / 'hop_luu.py')
        hl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hl)
        t = pd.Timestamp('2026-11-20 10:00', tz='UTC')
        TH = {m: [] for m in PP.DS}
        TH['elliott'] = [{'t': t, 'huong': 'MUA'}, {'t': t + pd.Timedelta(hours=3), 'huong': 'BAN'}]
        TH['pha_vo'] = [{'t': t - pd.Timedelta(minutes=45), 'huong': 'MUA'}]
        TH['ict'] = [{'t': t, 'huong': 'MUA'}]
        TH['fib'] = [{'t': t - pd.Timedelta(minutes=75), 'huong': 'MUA'}]
        self.assertEqual(list(hl.dem_hop_luu(TH)['elliott']), [2, 0])


if __name__ == '__main__':
    unittest.main()


class PhieuBot(unittest.TestCase):
    """Phiếu cho luật bot: lệnh chờ dừng ở đỉnh (MUA) hoặc đáy (BÁN) nến tín hiệu, dừng lỗ của bot, thang chốt tính lại từ giá vào của phiếu."""
    NEN = datetime(2026, 6, 1, 10, 15, tzinfo=timezone.utc)

    def _pa(self, **kw):
        p = {'ma': 'bot:nen', 'ten': 'Luật bot tín hiệu', 'co': True, 'hieu_luc': True, 'huong': 'MUA', 'vao': 3000.0, 'sl': 2980.0,
             'tp': [3010.0, 3020.0], 'ly_do': 'thử'}
        p.update(kw)
        return p

    V2 = {'vao': 'V2', 'sl': 'S0', 'tp': 'TL'}

    def _lap(self, pa, bid, now=None, nen_h=3003.0, nen_l=2995.0, ct=None):
        return phieu.lap_bot(pa, self.NEN, nen_h, nen_l, 'M5', bid, bid + 0.2, now or self.NEN + timedelta(minutes=2), (0.5, 1.0, 2.0), ct=ct or self.V2)

    def test_cho_dung_o_dinh_nen_va_thang_chot_tinh_lai(self):
        f = self._lap(self._pa(), 3000.5)
        self.assertEqual((f['ma'], f['loai'], f['huong'], f['trang_thai']), ('bot', 'dung', 'MUA', 'con_hieu_luc'))
        self.assertEqual((f['vao'], f['sl']), (3003.0, 2980.0))
        self.assertEqual(f['tp'], [3014.5, 3026.0, 3049.0])                # rủi ro 23 giá từ giá vào của phiếu
        self.assertEqual(f['nen'], self.NEN.isoformat())
        self.assertEqual(f['con_phut'], 238)
        self.assertEqual(f['i_chinh'], 0)                                  # chấm thắng thua theo TP1 như lệnh gốc của bot

    def test_cong_thuc_vao_ngay_lui_3_gia_chot_2r(self):
        f = self._lap(self._pa(), 3000.0, ct={'vao': 'V0', 'sl': 'S3', 'tp': 'T0'})
        self.assertEqual((f['loai'], f['vao'], f['sl'], f['tp'], f['rr'], f['trang_thai']), ('tt', 3000.2, 2977.0, [3046.6], [2.0], 'con_hieu_luc'))
        self.assertIsNone(f['con_phut'])
        self.assertIsNone(self._lap(self._pa(), 3000.0, ct={'vao': 'V3', 'sl': 'S0', 'tp': 'TL'}))     # xác nhận M5 chưa làm được lúc sống

    def test_mac_dinh_doc_tu_so_do(self):
        f = phieu.lap_bot(self._pa(), self.NEN, 3003.0, 2995.0, 'M5', 3000.0, 3000.2, self.NEN + timedelta(minutes=2), (0.5, 1.0))
        sd = phieu.so_do_bot()
        if sd and sd.get('ap_dung'):
            self.assertEqual(f['cong_thuc']['vao'], sd['ap_dung']['vao'])

    def test_ban_o_day_nen(self):
        f = self._lap(self._pa(huong='BAN', vao=3000.0, sl=3020.0), 2999.0)
        self.assertEqual((f['vao'], f['sl'], f['trang_thai']), (2995.0, 3020.0, 'con_hieu_luc'))

    def test_trang_thai(self):
        self.assertEqual(self._lap(self._pa(), 3003.0)['trang_thai'], 'da_khop')          # Ask đã vượt đỉnh nến tín hiệu
        self.assertEqual(self._lap(self._pa(), 2979.0)['trang_thai'], 'da_huy')           # giá chạm dừng lỗ trước khi kích hoạt
        self.assertEqual(self._lap(self._pa(), 3000.5, now=self.NEN + timedelta(hours=5))['trang_thai'], 'het_han')
        self.assertEqual(self._lap(self._pa(sl=2995.0), 3000.5)['trang_thai'], 'rui_ro')  # rủi ro 8 giá, ngoài khoảng 10–35
        self.assertEqual(self._lap(self._pa(hieu_luc=False), 3000.5)['trang_thai'], 'qua_tre')

    def test_khong_co_lenh_thi_khong_co_phieu(self):
        self.assertIsNone(self._lap(self._pa(co=False), 3000.5))
        self.assertIsNone(self._lap(self._pa(ma='bot:xu_huong'), 3000.5))                # lệnh theo yêu cầu chưa được đo kiểu vào này

    def test_ghi_nhat_ky_va_cham_theo_tp1(self):
        from so_cong_khai import nhat_ky
        with tempfile.TemporaryDirectory() as d:
            cfg = {'nhat_ky': {'bat': True, 'tep': str(Path(d) / 'nk.json')}, 'gia': {'ma_vang': 'XAUUSDp'}}
            pa = self._pa()
            pa['phieu'] = self._lap(pa, 3000.5)
            moi = nhat_ky.ghi(cfg, {'phuong_an': [pa], 'phuong_phap': [], 'bid': 3000.5, 'boi_canh': {}}, self.NEN + timedelta(minutes=2))
            rec = next(x for x in moi if x['ma'] == 'phieu:bot')
            self.assertEqual((rec['nhom'], rec['loai'], rec['tt'], rec['i_chinh']), ('phieu', 'dung', 'cho_khop', 0))
            idx = pd.date_range(datetime(2026, 6, 1, 10, 20, tzinfo=timezone.utc), periods=2, freq='5min')
            bars = pd.DataFrame([(3001.0, 3004.0, 3000.0, 3003.5), (3003.5, 3015.0, 3003.0, 3014.8)], columns=['open', 'high', 'low', 'close'], index=idx)
            nhat_ky.cap_nhat(rec, bars, 0.2)
            self.assertEqual((rec['tt'], rec['r']), ('thang', 0.5))        # chạm TP1 (0,5R) là thắng, như lệnh gốc của bot
