# -*- coding: utf-8 -*-
"""Phép mô phỏng của cong-cu/diem_vao.py trên nến dựng tay: khớp đúng bên giá, lệnh chờ giới hạn và lệnh chờ dừng, dừng lỗ và chốt lời cùng nến,
mở cửa nhảy qua dừng lỗ, chốt một phần rồi dời về hòa vốn, độ đi ngược/đi thuận, trượt giá lúc tin, phí qua đêm, và cổng chấp nhận."""
import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

_spec = importlib.util.spec_from_file_location('diem_vao', Path(__file__).resolve().parent.parent / 'cong-cu' / 'diem_vao.py')
DV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(DV)
PP = DV.PP

T0 = datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)                 # thứ Ba, giữa phiên: không qua đêm trong vài giờ đầu
PHI = DV.PHI


def _m1(gia, spread=0.2, n=1800, bat_dau=T0, tin=()):
    """n nến 1 phút đi ngang quanh 100 (mở = đóng = 100, đỉnh 100,1, đáy 99,9); `gia`: {vị trí: (mở, đỉnh, đáy, đóng)} ghi đè."""
    a = np.tile(np.array([100.0, 100.1, 99.9, 100.0]), (n, 1))
    for k, v in gia.items():
        a[k] = v
    m = pd.DataFrame(a, columns=['open', 'high', 'low', 'close'], index=pd.date_range(bat_dau, periods=n, freq='1min'))
    sp = np.full(n, spread) if np.isscalar(spread) else np.asarray(spread, dtype=float)
    return DV.du_lieu(m, sp, list(tin))


def _th(huong='MUA', kieu='thi_truong', vao=100.0, sl=98.0, atr=2.0, **them):
    return dict({'t': pd.Timestamp(T0), 'i': 0, 'huong': huong, 'kieu': kieu, 'vao': vao, 'sl': sl, 'atr': atr, 'vung': None, 'muc_tieu': None,
                 'nen_h': 100.5, 'nen_l': 99.5}, **them)


class VaoNgay(unittest.TestCase):
    def test_mua_khop_o_ask_va_chot_2r(self):
        D = _m1({30: (100.0, 104.7, 100.0, 104.0)})                     # Bid chạm 104,6 = 2R từ giá khớp 100,2
        x = DV.mo_phong(D, _th(), 'pha_vo')
        self.assertTrue(x['khop'])
        self.assertAlmostEqual(x['gia'], 100.2)                         # mua khớp ở Ask = 100 + 0,2
        self.assertAlmostEqual(x['rui'], 2.2)
        self.assertEqual(x['ket'], 'TP')
        self.assertAlmostEqual(x['r'], (2 * 2.2 - PHI) / 2.2)

    def test_ban_khop_o_bid_va_dung_lo_tinh_theo_ask(self):
        D = _m1({30: (100.0, 101.85, 100.0, 101.0)})                    # Bid 101,85 → Ask 102,05 ≥ dừng lỗ 102
        x = DV.mo_phong(D, _th('BAN', sl=102.0), 'pha_vo')
        self.assertAlmostEqual(x['gia'], 100.0)                         # bán khớp ở Bid
        self.assertEqual(x['ket'], 'SL')
        self.assertAlmostEqual(x['r'], (-2.0 - PHI) / 2.0)
        D2 = _m1({30: (100.0, 101.7, 100.0, 101.0)})                    # Ask mới 101,9: chưa chạm
        self.assertNotEqual(DV.mo_phong(D2, _th('BAN', sl=102.0), 'pha_vo')['ket'], 'SL')

    def test_dung_lo_va_chot_loi_cung_nen_thi_tinh_thua(self):
        D = _m1({30: (100.0, 105.0, 97.9, 100.0)})
        self.assertEqual(DV.mo_phong(D, _th(), 'pha_vo')['ket'], 'SL')

    def test_mo_cua_nhay_qua_dung_lo_thi_thoat_o_gia_mo(self):
        D = _m1({30: (97.0, 97.2, 96.8, 97.0)})                         # mở cửa 97, dưới dừng lỗ 98
        x = DV.mo_phong(D, _th(), 'pha_vo')
        self.assertAlmostEqual(x['r'], (97.0 - 100.2 - PHI) / 2.2)      # lỗ hơn 1R

    def test_di_nguoc_va_di_thuan(self):
        D = _m1({10: (100.0, 100.1, 99.1, 100.0), 30: (100.0, 104.7, 100.0, 104.0)})
        x = DV.mo_phong(D, _th(), 'pha_vo')
        self.assertAlmostEqual(x['mae'], (100.2 - 99.1) / 2.2)          # đi ngược sâu nhất tới 99,1 trước khi về đích
        self.assertAlmostEqual(x['mfe'], (104.7 - 100.2) / 2.2)

    def test_chi_phi_cu_dung_spread_co_dinh(self):
        D = _m1({30: (100.0, 106.0, 100.0, 104.0)}, spread=1.0)
        self.assertAlmostEqual(DV.mo_phong(D, _th(), 'pha_vo', chi_phi_cu=0.17)['gia'], 100.17)
        self.assertAlmostEqual(DV.mo_phong(D, _th(), 'pha_vo')['gia'], 101.0)


class LenhCho(unittest.TestCase):
    def test_gioi_han_chi_khop_khi_ask_cham_muc(self):
        s = _th(kieu='gioi_han', vao=99.0, sl=97.5, vung=[98.5, 99.5])
        D = _m1({20: (100.0, 100.0, 98.85, 99.5)})                      # Bid 98,85 → Ask 99,05: CHƯA chạm 99
        self.assertEqual(DV.mo_phong(D, s, 'ict'), {'khop': False, 'vi': 'khong_khop'})
        D = _m1({20: (100.0, 100.0, 98.75, 99.5), 60: (99.5, 102.1, 99.5, 102.0)})    # Ask 98,95 ≤ 99: khớp ở 99
        x = DV.mo_phong(D, s, 'ict')
        self.assertAlmostEqual(x['gia'], 99.0)
        self.assertEqual(x['ket'], 'TP')                                # 2R = 99 + 3 = 102

    def test_cham_dung_lo_truoc_khi_khop_thi_huy(self):
        s = _th(kieu='gioi_han', vao=99.0, sl=97.5, vung=[98.5, 99.5])
        D = _m1({10: (100.0, 100.0, 99.3, 99.4), 11: (99.4, 99.4, 97.0, 97.2)})       # nến 11 vừa khớp vừa thủng dừng lỗ: vẫn khớp, rồi thua
        self.assertEqual(DV.mo_phong(D, s, 'ict')['ket'], 'SL')
        s2 = _th('BAN', kieu='gioi_han', vao=101.0, sl=102.5, vung=[100.5, 101.5])
        gian = np.full(1800, 0.2)
        gian[7] = 2.0                                                   # nến 7: Bid chưa tới 101 nhưng spread giãn, Ask = 102,6 đã chạm dừng lỗ: hủy
        D = _m1({5: (100.0, 100.5, 100.0, 100.4), 7: (100.0, 100.6, 99.9, 100.0), 9: (100.0, 101.2, 99.9, 100.0)}, spread=gian)
        self.assertEqual(DV.mo_phong(D, s2, 'ict')['vi'], 'cham_sl_truoc')

    def test_mep_gan_mep_xa(self):
        s = _th(kieu='gioi_han', vao=99.0, sl=97.5, vung=[98.5, 99.5])
        D = _m1({20: (100.0, 100.0, 99.2, 99.6)})                       # Ask xuống 99,4: chỉ chạm mép gần 99,5
        self.assertAlmostEqual(DV.mo_phong(D, s, 'ict', vao='V1')['gia'], 99.5)
        self.assertFalse(DV.mo_phong(D, s, 'ict', vao='V0')['khop'])
        self.assertFalse(DV.mo_phong(D, s, 'ict', vao='V2')['khop'])
        self.assertAlmostEqual(DV.mo_phong(D, s, 'ict', vao='V3')['gia'], 100.2)       # vào ngay

    def test_cho_dung_khop_khi_gia_vuot_va_xau_hon_khi_nhay(self):
        D = _m1({20: (100.0, 100.35, 100.0, 100.3)})                    # Ask lên 100,55 ≥ đỉnh nến tín hiệu 100,5
        self.assertAlmostEqual(DV.mo_phong(D, _th(), 'pha_vo', vao='V2')['gia'], 100.5)
        D = _m1({20: (101.0, 101.2, 100.9, 101.0)})                     # mở cửa đã vượt: khớp ở Ask của giá mở
        self.assertAlmostEqual(DV.mo_phong(D, _th(), 'pha_vo', vao='V2')['gia'], 101.2)
        D = _m1({})
        self.assertEqual(DV.mo_phong(D, _th(), 'pha_vo', vao='V2')['vi'], 'khong_khop')

    def test_cho_hoi_ve_giua_nen(self):
        D = _m1({20: (100.0, 100.0, 99.55, 99.9)})                      # Ask xuống 99,75 ≤ giữa nến tín hiệu 99,8
        self.assertAlmostEqual(DV.mo_phong(D, _th(nen_h=100.3, nen_l=99.3), 'pha_vo', vao='V1')['gia'], 99.8)

    def test_xac_nhan_nen_m5(self):
        gia = {k: (100.0, 100.05, 99.9, 99.95) for k in range(0, 10)}   # hai nến M5 đầu đóng dưới mở: chưa xác nhận
        gia.update({10: (100.0, 100.3, 100.0, 100.2), 14: (100.2, 100.4, 100.2, 100.3)})    # nến M5 thứ ba đóng trên mở
        D = _m1(gia)
        x = DV.mo_phong(D, _th(), 'pha_vo', vao='V3')
        self.assertEqual(pd.Timestamp(x['t_vao'], tz='UTC'), pd.Timestamp(T0) + pd.Timedelta(minutes=15))
        self.assertAlmostEqual(x['gia'], 100.2)                         # giá mở nến 1 phút kế tiếp + spread

    def test_fib_ba_muc(self):
        s = _th(kieu='gioi_han', vao=96.18, sl=89.0, atr=4.0, vung=[96.18, 97.5])       # nhịp 90 → 100: 50% = 95 … ở đây dùng số tròn cho dễ
        s['vung'] = [100 - 0.618 * 10, 95.0]
        s['vao'] = 100 - 0.618 * 10                                                    # 93,82
        self.assertAlmostEqual(DV.muc_cho(s, 'fib', 'V1')[1], 95.0)
        self.assertAlmostEqual(DV.muc_cho(s, 'fib', 'V2')[1], 100 - 0.786 * 10)
        self.assertEqual(DV.muc_cho(s, 'fib', 'V3')[0], 'tt')


class DungLoChotLoi(unittest.TestCase):
    def test_bon_cach_dung_lo(self):
        s = _th()
        self.assertAlmostEqual(DV.muc_sl(s, 'ema_hoi', 'S0', 100.2, 0.2), 98.0)
        self.assertAlmostEqual(DV.muc_sl(s, 'ema_hoi', 'S1', 100.2, 0.2), 100.2 - 1.5 * 2.0)
        self.assertAlmostEqual(DV.muc_sl(s, 'pha_vo', 'S1', 100.2, 0.2), 99.5 - 0.1 * 2.0)   # Phá vỡ: sau đáy nến tín hiệu
        self.assertAlmostEqual(DV.muc_sl(s, 'ema_hoi', 'S2', 100.2, 0.2), 97.8)
        self.assertAlmostEqual(DV.muc_sl(s, 'ema_hoi', 'S3', 100.2, 0.2), 97.0)
        self.assertAlmostEqual(DV.muc_sl(_th('BAN', sl=102.0), 'ema_hoi', 'S3', 100.0, 0.2), 103.0)

    def test_chot_1r_va_muc_tieu(self):
        D = _m1({30: (100.0, 102.5, 100.0, 102.4)})                     # 1R = 102,4
        self.assertEqual(DV.mo_phong(D, _th(), 'pha_vo', tp='T1')['ket'], 'TP')
        self.assertNotEqual(DV.mo_phong(D, _th(), 'pha_vo', tp='T0')['ket'], 'TP')
        x = DV.mo_phong(D, _th(muc_tieu=101.5), 'pha_vo', tp='T2')
        self.assertAlmostEqual(x['r'], (101.5 - 100.2 - PHI) / 2.2)
        self.assertEqual(DV.mo_phong(D, _th(), 'pha_vo', tp='T2')['vi'], 'khong_muc_tieu')
        self.assertEqual(DV.mo_phong(D, _th(muc_tieu=99.0), 'pha_vo', tp='T2')['vi'], 'khong_muc_tieu')   # mục tiêu nằm sai phía

    def test_chot_theo_boi_so_r(self):
        D = _m1({30: (100.0, 101.0, 100.0, 100.9)})                     # vào 100,2, rủi ro 2,2: 0,25R = 100,75 chạm, 0,5R = 101,3 chưa chạm
        x = DV.mo_phong(D, _th(), 'pha_vo', tp='R0.25')
        self.assertEqual(x['ket'], 'TP')
        self.assertAlmostEqual(x['r'], (0.25 * 2.2 - PHI) / 2.2)
        self.assertNotEqual(DV.mo_phong(D, _th(), 'pha_vo', tp='R0.5')['ket'], 'TP')
        self.assertEqual(DV.mo_phong(D, _th(), 'pha_vo', tp='R2')['ket'], DV.mo_phong(D, _th(), 'pha_vo', tp='T0')['ket'])

    def test_chot_nua_roi_hoa_von(self):
        cao = {k: (102.0, 102.1, 101.9, 102.0) for k in range(31, 40)}                  # sau khi đạt 1R giá ở lại vùng 102
        D = _m1({30: (100.0, 102.5, 100.0, 102.4), **cao, 40: (102.0, 102.0, 100.1, 100.3)})   # rồi quay về giá vào 100,2
        x = DV.mo_phong(D, _th(), 'pha_vo', tp='T3')
        self.assertEqual(x['ket'], 'Hòa vốn')
        self.assertAlmostEqual(x['r'], (0.5 * 2.2 + 0.5 * 0.0 - PHI) / 2.2)
        D = _m1({30: (100.0, 102.5, 100.0, 102.4), **cao, 40: (102.0, 104.7, 102.0, 104.6)})   # đạt 1R rồi 2R
        x = DV.mo_phong(D, _th(), 'pha_vo', tp='T3')
        self.assertEqual(x['ket'], 'TP2')
        self.assertAlmostEqual(x['r'], (0.5 * 2.2 + 0.5 * 4.4 - PHI) / 2.2)

    def test_khong_dat_chot_loi(self):
        D = _m1({30: (100.0, 108.0, 100.0, 100.0)})
        x = DV.mo_phong(D, _th(), 'pha_vo', khong_tp=True)
        self.assertEqual(x['ket'], 'Hết giờ')
        self.assertAlmostEqual(x['mfe'], (108.0 - 100.2) / 2.2)


class ThangNhieuMuc(unittest.TestCase):
    """Luật bot: sáu phần bằng nhau ở 0,5R … 3R; khoảng dừng lỗ nhận theo số giá tuyệt đối."""

    def _th(self, **kw):
        return _th(sl=98.2, atr=6.0, thang=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0], rui_khoang=(1.0, 35.0), **kw)       # vào 100,2 → rủi ro 2,0

    def test_chot_ba_muc_roi_dung_lo(self):
        D = _m1({30: (100.0, 103.3, 100.0, 103.0), 40: (103.0, 103.0, 98.0, 98.1)})       # chạm 101,2 · 102,2 · 103,2 rồi về dừng lỗ
        x = DV.mo_phong(D, self._th(), 'bot', tp='TL')
        self.assertEqual(x['ket'], 'SL')
        self.assertAlmostEqual(x['r'], ((0.5 + 1.0 + 1.5) / 6 * 2.0 + 3 / 6 * -2.0 - PHI) / 2.0)

    def test_du_sau_muc(self):
        D = _m1({30: (100.0, 106.3, 100.0, 106.0)})
        x = DV.mo_phong(D, self._th(), 'bot', tp='TL')
        self.assertEqual(x['ket'], 'TP')
        self.assertAlmostEqual(x['r'], (10.5 / 6 * 2.0 - PHI) / 2.0)                        # trung bình 1,75R

    def test_doi_ve_hoa_von_sau_muc_dau(self):
        cao = {k: (101.5, 101.6, 101.4, 101.5) for k in range(31, 40)}
        D = _m1({30: (100.0, 101.3, 100.0, 101.2), **cao, 40: (101.5, 101.5, 100.1, 100.3)})   # đạt 0,5R rồi quay về giá vào
        co = DV.mo_phong(D, self._th(), 'bot', tp='TLB')
        self.assertEqual(co['ket'], 'Hòa vốn')
        self.assertAlmostEqual(co['r'], (0.5 / 6 * 2.0 - PHI) / 2.0)
        khong = DV.mo_phong(D, self._th(), 'bot', tp='TL')                                    # không dời: phần còn lại vẫn chạy tiếp
        self.assertNotEqual(khong['ket'], 'Hòa vốn')

    def test_khoang_dung_lo_tuyet_doi(self):
        D = _m1({30: (100.0, 106.3, 100.0, 106.0)})
        self.assertEqual(DV.mo_phong(D, _th(sl=98.2, atr=6.0, thang=[1.0], rui_khoang=(10.0, 35.0)), 'bot', tp='TL')['vi'], 'rui_ro')   # rủi ro 2 giá < 10
        self.assertEqual(DV.muc_cho(self._th(), 'bot', 'V2'), ('dung', 100.5))               # luật bot thuộc nhóm vào ngay: chờ phá ở đỉnh nến tín hiệu


class ChiPhi(unittest.TestCase):
    def test_truot_gia_luc_tin(self):
        D = _m1({30: (100.0, 104.7, 100.0, 104.0)}, tin=[pd.Timestamp(T0) + pd.Timedelta(minutes=5)])
        x = DV.mo_phong(D, _th(), 'pha_vo')                             # vào ngay trong 15 phút quanh tin: cộng trượt giá; thoát ở chốt lời thì không
        self.assertAlmostEqual(x['r'], (2 * 2.2 - PHI - DV.TRUOT_TIN) / 2.2)

    def test_phi_qua_dem(self):
        bat = datetime(2026, 6, 2, 20, 0, tzinfo=timezone.utc)          # thứ Ba 20:00 UTC; 00:00 giờ Athens là 21:00 UTC
        self.assertEqual(DV.so_dem(pd.Timestamp(bat).value, pd.Timestamp(bat).value + 30 * DV.PHUT), 0)
        self.assertEqual(DV.so_dem(pd.Timestamp(bat).value, pd.Timestamp(bat).value + 90 * DV.PHUT), 1)
        thu_tu = datetime(2026, 6, 3, 20, 0, tzinfo=timezone.utc)
        self.assertEqual(DV.so_dem(pd.Timestamp(thu_tu).value, pd.Timestamp(thu_tu).value + 90 * DV.PHUT), 3)   # đêm thứ Tư nhân ba
        D = _m1({90: (100.0, 104.7, 100.0, 104.0)}, bat_dau=bat)
        s = _th()
        s['t'] = pd.Timestamp(bat)
        x = DV.mo_phong(D, s, 'pha_vo')
        self.assertAlmostEqual(x['r'], (2 * 2.2 - PHI - 100.2 * 0.0181 / 100) / 2.2)


class CongVaSoDo(unittest.TestCase):
    def test_so_do(self):
        df = pd.DataFrame({'nam': 2020, 'khop': [True, True, True, False], 'r': [2.0, -1.0, -1.0, np.nan], 't_ra': [1, 2, 3, 0]})
        x = DV.so_do(df)
        self.assertEqual((x['tin_hieu'], x['n'], x['khop_pct'], x['thang']), (4, 3, 75.0, 33.3))
        self.assertAlmostEqual(x['tong'], 0.0)
        self.assertAlmostEqual(x['pf'], 1.0)
        self.assertAlmostEqual(x['dd'], 2.0)

    def test_cong_va_chon(self):
        b = lambda n1, r1, n2, r2, t2: {'chinh': {'n': n1, 'r_tb': r1}, 'kiem': {'n': n2, 'r_tb': r2, 'tong': t2}}   # noqa: E731
        goc = b(900, -0.10, 500, -0.05, -25.0)
        self.assertEqual(DV.chon({'V0': goc, 'V1': b(700, -0.02, 400, -0.01, -4.0)}, 'V0')[:2], ('V1', True))
        self.assertEqual(DV.chon({'V0': goc, 'V1': b(700, -0.20, 400, 0.30, 120.0)}, 'V0')[:2], ('V0', False))      # kém trên phần chỉnh: không được chọn dù đẹp ở phần kiểm tra
        self.assertEqual(DV.chon({'V0': goc, 'V1': b(700, -0.02, 99, 0.30, 30.0)}, 'V0')[:2], ('V0', False))        # mẫu nhỏ
        self.assertEqual(DV.chon({'V0': goc, 'V1': b(700, -0.02, 400, -0.06, -24.0)}, 'V0')[:2], ('V0', False))     # không hơn ở phần kiểm tra
        self.assertEqual(DV.chon({'V0': goc, 'V1': b(700, -0.02, 400, -0.04, -30.0)}, 'V0')[:2], ('V0', False))     # R/lệnh hơn nhưng tổng R thấp hơn


if __name__ == '__main__':
    unittest.main()
