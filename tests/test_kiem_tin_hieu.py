"""Kiểm chứng tín hiệu nhóm Telegram (kiem_tin_hieu.py): đọc tin dán từ Telegram, dò trên nến 1 phút, tổng hợp."""
import unittest
from datetime import datetime, timezone

from so_cong_khai import kiem_tin_hieu as k

DAN = """Gold VIP Signals, [25.11.2026 14:05]
XAUUSD SELL NOW 3540-3545
SL 3552
TP1 3535
TP2 3530
TP3 3520

Gold VIP Signals, [25.11.2026 16:30]
GOLD BUY LIMIT 3500
SL: 3492
TP: 3505/3510/3520

Gold VIP Signals, [25.11.2026 18:00]
Cập nhật: TP1 đã chạm, xin chúc mừng anh em!

Gold VIP Signals, [26.11.2026 09:15]
EURUSD BUY 1,0850
Stop loss 1,0830
Take profit 1,0880
"""


class DocTinTest(unittest.TestCase):
    def test_doc_nhieu_kieu(self):
        ds, loi = k.doc_tin(DAN, mui_gio=7, nam=2026)
        self.assertEqual(len(ds), 3, loi)
        a, b, c = ds
        self.assertEqual((a['chieu'], a['ma'], a['ngay'], a['vung'], a['sl'], a['tp']), ('BAN', 'XAUUSD', True, [3540.0, 3545.0], 3552.0, [3535.0, 3530.0, 3520.0]))
        self.assertEqual(a['gio'], datetime(2026, 11, 25, 7, 5, tzinfo=timezone.utc))         # 14:05 giờ Việt Nam
        self.assertEqual((b['chieu'], b['ma'], b['ngay'], b['vung'], b['sl'], b['tp']), ('MUA', 'XAUUSD', False, [3500.0], 3492.0, [3505.0, 3510.0, 3520.0]))
        self.assertEqual((c['ma'], c['vung'], c['sl'], c['tp']), ('EURUSD', [1.085], 1.083, [1.088]))
        self.assertEqual(loi, [])                                                        # tin "Cập nhật" không có BUY/SELL: bỏ qua, không báo lỗi

    def test_so(self):
        for s, v in (('3,540.5', 3540.5), ('3.540,5', 3540.5), ('1.0850', 1.085), ('1,0850', 1.085), ('3540', 3540.0), ('1.234.567', 1234567.0)):
            self.assertEqual(k.so(s), v, s)

    def test_bao_loi_ro(self):
        ds, loi = k.doc_tin('[25.11.2026 10:00]\nXAUUSD BUY 3500\nTP 3510', nam=2026)
        self.assertEqual(ds, [])
        self.assertIn('không thấy dừng lỗ', loi[0])
        ds, loi = k.doc_tin('XAUUSD BUY 3500 SL 3490 TP 3510', nam=2026)
        self.assertIn('không thấy giờ', loi[0])
        ds, loi = k.doc_tin('[25.11.2026 10:00]\nXAUUSD BUY 3500 SL 3510 TP 3520', nam=2026)
        self.assertIn('đúng thứ tự', loi[0])


class DocTinKhoTest(unittest.TestCase):
    """27/11/2026: các kiểu tin mà bản đầu đọc sai (rà soát độc lập)."""
    G = 'Nhóm, [25.11.2026 14:05]\n'

    def mot(self, chu):
        ds, loi = k.doc_tin(self.G + chu, nam=2026)
        self.assertEqual(len(ds), 1, loi)
        return ds[0]

    def test_tp_ngan_bang_gach_va_phay_lien(self):
        self.assertEqual(self.mot('XAUUSD SELL NOW\nSL 3552\nTP 3535 - 3530 - 3520')['tp'], [3535.0, 3530.0, 3520.0])
        self.assertEqual(self.mot('XAUUSD BUY NOW\nSL 3490\nTP: 3510,3520')['tp'], [3510.0, 3520.0])
        self.assertEqual(self.mot('XAUUSD SELL NOW\nSL 3552\nTP: 3535,3530,3520')['tp'], [3535.0, 3530.0, 3520.0])
        self.assertEqual(self.mot('EURUSD BUY NOW\nSL 1.0830\nTP 1.0850,1.0880')['tp'], [1.085, 1.088])
        self.assertEqual(self.mot('XAUUSD SELL NOW\nSL 3,552.50\nTP 3,540.50')['sl'], 3552.5)      # dấu nghìn vẫn đúng

    def test_so_la_khong_thanh_tp(self):
        self.assertEqual(self.mot('XAUUSD SELL NOW\nSL 3552\nTP1: 3535 | 50 pips')['tp'], [3535.0])

    def test_stop_loss_tren_dong_lenh_van_la_vao_ngay(self):
        x = self.mot('BUY NOW 3540 STOP LOSS 3530 TP 3560')
        self.assertTrue(x['ngay'])
        self.assertTrue(self.mot('XAUUSD BUY STOP 3540\nSL 3530\nTP 3560')['vung'])                 # BUY STOP vẫn là lệnh chờ
        self.assertTrue(self.mot('MUA vàng cho anh em\nSL 3530\nTP 3560')['ngay'])                  # "cho" không phải lệnh chờ

    def test_nhan_khung_khong_phai_gia_vao(self):
        x = self.mot('SELL GOLD 3540 (M15)\nSL 3550\nTP 3530')
        self.assertEqual(x['vung'], [3540.0])

    def test_gio_am_pm(self):
        ds, _ = k.doc_tin('Nhóm, [25.11.2026 2:05 PM]\nXAUUSD SELL NOW\nSL 3552\nTP 3535', mui_gio=7, nam=2026)
        self.assertEqual(ds[0]['gio'], datetime(2026, 11, 25, 7, 5, tzinfo=timezone.utc))             # 14:05 giờ VN
        ds, _ = k.doc_tin('Group, [11/25/2026 2:05 PM]\nXAUUSD SELL NOW\nSL 3552\nTP 3535', mui_gio=7, nam=2026)
        self.assertEqual(ds[0]['gio'], datetime(2026, 11, 25, 7, 5, tzinfo=timezone.utc))             # kiểu Mỹ: tháng trước


def nen(t0, ds):
    """ds: [(open, high, low, close)] mỗi phút từ t0."""
    return [(t0 + 60 * i, *x) for i, x in enumerate(ds)]


class ChamTest(unittest.TestCase):
    T0 = int(datetime(2026, 11, 25, 7, 5, tzinfo=timezone.utc).timestamp())

    def tin(self, **x):
        return {'chieu': 'BAN', 'gio': datetime.fromtimestamp(self.T0, timezone.utc), 'sl': 3552.0, 'tp': [3535.0, 3530.0], 'ngay': True, 'vung': None, **x}

    def test_ban_ngay_cham_het_tp(self):
        kq = k.cham(self.tin(), nen(self.T0, [(3542, 3543, 3538, 3539), (3539, 3540, 3534, 3535), (3535, 3536, 3529, 3530)]))
        self.assertEqual((kq['trang_thai'], kq['vao'], kq['tp_cham']), ('het_tp', 3542, 2))
        self.assertAlmostEqual(kq['r_tp1'], 0.7, 3)                                      # TP1 cách 7 giá, rủi ro 10 giá
        self.assertAlmostEqual(kq['r_chia'], (0.7 + 1.2) / 2, 3)

    def test_cung_nen_cham_ca_hai_thi_tinh_sl(self):
        kq = k.cham(self.tin(), nen(self.T0, [(3542, 3553, 3534, 3540)]))
        self.assertEqual((kq['trang_thai'], kq['r_tp1'], kq['r_chia']), ('thua', -1.0, -1.0))

    def test_tp1_roi_ve_sl_va_hoa_von(self):
        d = nen(self.T0, [(3542, 3543, 3534, 3536), (3536, 3545, 3536, 3544), (3544, 3553, 3544, 3550)])
        kq = k.cham(self.tin(), d)
        self.assertEqual((kq['trang_thai'], kq['tp_cham'], kq['r_tp1'], kq['r_chia']), ('tp_roi_sl', 1, 0.7, -0.15))   # vào 3542, TP1 3535, SL 3552
        kq = k.cham(self.tin(), d, ve_hoa_von=True)                                      # dời SL về giá vào sau TP1
        self.assertEqual((kq['trang_thai'], kq['r_chia']), ('hoa_von', 0.35))

    def test_lenh_cho_khong_khop_va_khop(self):
        x = self.tin(chieu='MUA', ngay=False, vung=[3500.0], sl=3492.0, tp=[3505.0])
        d = nen(self.T0, [(3510, 3512, 3506, 3508)] * 300)
        self.assertEqual(k.cham(x, d, cho_gio=4)['trang_thai'], 'khong_khop')
        d = nen(self.T0, [(3510, 3512, 3506, 3508), (3508, 3509, 3499, 3501), (3501, 3506, 3500, 3505)])
        kq = k.cham(x, d)
        self.assertEqual((kq['trang_thai'], kq['vao']), ('het_tp', 3500.0))

    def test_r_co_dau_khi_gia_da_qua_tp(self):
        """Bán ngay ở 3533 khi TP1 3535 nằm phía trên: chạm 'TP1' là lỗ 0,105R, không phải lãi."""
        x = self.tin(tp=[3535.0])
        kq = k.cham(x, nen(self.T0, [(3533, 3536, 3532, 3534)]))
        self.assertEqual(kq['trang_thai'], 'het_tp')
        self.assertLess(kq['r_tp1'], 0)

    def test_tp_truoc_luc_khop_lenh_cho_khong_tinh(self):
        """Bán chờ 3540, TP 3530: nến có đáy 3529 và đỉnh 3541 không biết đáy trước hay sau lúc khớp, nên không tính TP trên nến khớp."""
        x = self.tin(ngay=False, vung=[3540.0], tp=[3530.0])
        d = nen(self.T0, [(3536, 3538, 3535, 3537), (3537, 3541, 3529, 3539), (3539, 3540, 3536, 3538)])
        kq = k.cham(x, d)
        self.assertEqual((kq['vao'], kq['tp_cham'], kq['trang_thai']), (3540.0, 0, 'dang_mo'))

    def test_tong_hop_lo_tp1_gan(self):
        ds = [{'kq': {'trang_thai': 'het_tp', 'tp_cham': 1, 'r_tp1': 0.3, 'r_chia': 0.3, 'r_cac_tp': [0.3]}}] * 8 + \
             [{'kq': {'trang_thai': 'thua', 'tp_cham': 0, 'r_tp1': -1.0, 'r_chia': -1.0, 'r_cac_tp': [0.3]}}] * 2
        t = k.tong_hop(ds)
        self.assertEqual((t['ty_le_tp1'], t['ty_le_thua'], t['tp1_cach_tb']), (80.0, 20.0, 0.3))
        self.assertAlmostEqual(t['r_tp1_tb'], (8 * 0.3 - 2) / 10, 3)                      # "thắng 80%" mà lãi chỉ +0,04R mỗi lệnh


class MT5Gia:
    """MT5 giả: ghi lại giờ được hỏi; trả nến 1 phút đúng khoảng đó."""
    TIMEFRAME_M1 = 1

    def __init__(self):
        self.hoi = []

    def copy_rates_range(self, sym, tf, a, b):
        self.hoi.append((a, b))
        t0 = int(a.timestamp())
        return [{'time': t0 + 60 * i, 'open': 3542, 'high': 3543, 'low': 3534, 'close': 3535} for i in range(5)]


class KiemTest(unittest.TestCase):
    def test_hoi_mt5_bang_gio_utc_co_mui_gio(self):
        """Lỗi đã gặp: truyền giờ không kèm múi giờ thì thư viện MT5 hiểu là giờ máy tính (GMT+7), nến lệch 7 tiếng."""
        from unittest import mock
        m = MT5Gia()
        with mock.patch('so_cong_khai.da_ma._hien', return_value={'XAUUSDp': None}):
            kq = k.kiem({}, '[25.11.2026 14:05]\nXAUUSD SELL NOW\nSL 3552\nTP1 3535', mt5=m, now=datetime(2026, 11, 26, tzinfo=timezone.utc))
        a, b = m.hoi[0]
        self.assertIsNotNone(a.tzinfo)
        self.assertEqual(a, datetime(2026, 11, 25, 7, 4, tzinfo=timezone.utc))
        self.assertEqual(kq['ds'][0]['kq']['trang_thai'], 'het_tp')

    def test_lich_su_ho_khong_cham(self):
        x = {'chieu': 'BAN', 'gio': datetime(2026, 11, 25, 7, 5, tzinfo=timezone.utc), 'sl': 3552.0, 'tp': [3535.0], 'ngay': True, 'vung': None}
        t = int(x['gio'].timestamp()) + 3600
        self.assertEqual(k.cham(x, [(t, 3542, 3543, 3534, 3535)])['trang_thai'], 'khong_du_lieu')


class TimMaTest(unittest.TestCase):
    def test_tim_ma_san(self):
        hien = ['XAUUSDp', 'EURUSDp', 'USTECp', 'BTCUSDTp']
        self.assertEqual(k.tim_ma('XAUUSD', hien), 'XAUUSDp')
        self.assertEqual(k.tim_ma('NAS100', hien), 'USTECp')
        self.assertEqual(k.tim_ma('BTCUSD', hien), 'BTCUSDTp')
        self.assertIsNone(k.tim_ma('GBPJPY', hien))


if __name__ == '__main__':
    unittest.main()
