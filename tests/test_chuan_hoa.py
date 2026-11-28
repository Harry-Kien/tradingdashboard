# -*- coding: utf-8 -*-
"""Chuẩn hóa theo sách (24/11/2026): khoảng trống giá phải có nến giữa cùng chiều; hàm phá cấu trúc không nhìn trước; công tắc hợp lưu ICT chỉ
bỏ bớt tín hiệu chứ không thêm. Luật và cổng: cong-cu/CHUAN_HOA_DANG_KY.md."""
import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from so_cong_khai import phuong_phap as PP

T0 = datetime(2026, 6, 1, tzinfo=timezone.utc)


def _m15(n, gia=100.0):
    idx = pd.date_range(T0, periods=n, freq='15min')
    return pd.DataFrame({'open': gia, 'high': gia + 0.5, 'low': gia - 0.5, 'close': gia}, index=idx)


def _h1(m15):
    return m15.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()


def _dat(df, i, **kw):
    for k, v in kw.items():
        df.iloc[i, df.columns.get_loc(k)] = v


class CongTac(unittest.TestCase):
    """Mỗi bài tự đặt công tắc rồi trả lại, để không phụ thuộc giá trị mặc định."""

    def setUp(self):
        self.cu = PP.FVG_NEN_GIUA, PP.ICT_HOP_LUU

    def tearDown(self):
        PP.FVG_NEN_GIUA, PP.ICT_HOP_LUU = self.cu

    def _quet_day_roi_trong(self, giua_tang: bool):
        m = _m15(120)
        _dat(m, 112, low=98.9)                                                               # quét đáy 5 giờ rồi đóng trở lại
        if giua_tang:
            _dat(m, 114, open=100.0, close=102.0, high=102.1, low=100.0)                     # nến giữa là nến đẩy tăng
        else:
            _dat(m, 114, open=101.9, close=101.0, high=102.1, low=100.0)                     # cùng đỉnh đáy nhưng thân nến giảm
        _dat(m, 115, open=102.0, close=102.5, high=102.6, low=101.2)                         # đáy 101,2 trên đỉnh nến 113 (100,5)
        return [x for x in PP.quet('ict', m, _h1(m)) if x['i'] == 115]

    def test_mac_dinh_dang_bat_dinh_nghia_chuan_va_tat_hop_luu(self):
        self.assertTrue(PP.FVG_NEN_GIUA)                                                     # thay đổi 1 đã áp dụng
        self.assertFalse(PP.ICT_HOP_LUU)                                                     # thay đổi 2 không qua cổng

    def test_khoang_trong_can_nen_giua_cung_chieu(self):
        PP.ICT_HOP_LUU = False
        PP.FVG_NEN_GIUA = True
        self.assertEqual(len(self._quet_day_roi_trong(True)), 1)
        self.assertEqual(self._quet_day_roi_trong(False), [])                                # nến giữa giảm: không còn là khoảng trống giá tăng
        PP.FVG_NEN_GIUA = False
        self.assertEqual(len(self._quet_day_roi_trong(False)), 1)                            # định nghĩa cũ vẫn nhận

    def test_ban_do_ict_cung_dinh_nghia(self):
        PP.FVG_NEN_GIUA = True
        m = _m15(200)
        _dat(m, 150, open=101.9, close=101.0, high=102.1, low=100.0)                         # nến giữa giảm
        for i in range(151, 200):
            _dat(m, i, open=103.0, close=103.0, high=103.5, low=102.5)                       # giá ở trên, không quay về lấp
        vung = PP.ban_do_ict(m, _h1(m), 103.0, T0)['fvg']
        self.assertEqual([z for z in vung if z['huong'] == 'tang'], [])
        PP.FVG_NEN_GIUA = False
        vung = PP.ban_do_ict(m, _h1(m), 103.0, T0)['fvg']
        # định nghĩa cũ nhận cả hai: nến giữa 150 giảm (100,5–102,5) và nến giữa 151 không tăng không giảm (102,1–102,5)
        self.assertEqual(sorted((z['duoi'], z['tren']) for z in vung if z['huong'] == 'tang'), [(100.5, 102.5), (102.1, 102.5)])

    def test_hop_luu_chi_bo_bot_tin_hieu(self):
        rng = np.random.default_rng(3)
        n = 3000
        c = 100 + np.cumsum(rng.normal(0, 0.6, n))
        o = np.r_[c[0], c[:-1]]
        m = pd.DataFrame({'open': o, 'high': np.maximum(o, c) + rng.uniform(0, 0.4, n), 'low': np.minimum(o, c) - rng.uniform(0, 0.4, n), 'close': c},
                         index=pd.date_range(T0, periods=n, freq='15min'))
        for ma in ('ict', 'ict_fvg'):
            PP.ICT_HOP_LUU = False
            day_du = {(x['i'], x['huong'], x['vao'], x['sl']) for x in PP.quet(ma, m, _h1(m))}
            PP.ICT_HOP_LUU = True
            loc = {(x['i'], x['huong'], x['vao'], x['sl']) for x in PP.quet(ma, m, _h1(m))}
            self.assertTrue(loc <= day_du, ma)                                               # không sinh tín hiệu mới, không đổi mức giá
            self.assertLess(len(loc), len(day_du), ma)


class PhaCauTruc(unittest.TestCase):
    def test_khong_nhin_truoc(self):
        rng = np.random.default_rng(5)
        n = 600
        c = 100 + np.cumsum(rng.normal(0, 0.5, n))
        h, l = c + rng.uniform(0, 0.4, n), c - rng.uniform(0, 0.4, n)
        _, day_du = PP._pha_cau_truc(h, l, c)
        for cat in (150, 300, 451, 599):
            _, mot_phan = PP._pha_cau_truc(h[:cat], l[:cat], c[:cat])
            self.assertTrue(np.array_equal(mot_phan, day_du[:cat]), cat)                     # cắt bớt dữ liệu phía sau thì phần trước không đổi

    def test_bos_va_choch(self):
        gia = [10, 10, 10, 10, 12, 10, 10, 10, 10, 10, 13, 13, 13, 13, 13, 13, 9, 13, 13, 13, 13, 8, 8, 8]
        c = np.array(gia, dtype=float)
        ds, chieu = PP._pha_cau_truc(c + 0.1, c - 0.1, c)
        # nến 10 đóng vượt đỉnh đã xác nhận gần nhất → BOS tăng; nến 16 đóng dưới đáy đã xác nhận gần nhất → đổi chiều (CHoCH giảm)
        self.assertEqual([(x[1], x[3], x[4]) for x in ds][:2], [(10, 1, 'BOS'), (16, -1, 'CHoCH')])
        self.assertEqual((chieu[9], chieu[10], chieu[15], chieu[16]), (0, 1, 1, -1))


class CongCuDo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('chuan_hoa', Path(__file__).resolve().parent.parent / 'cong-cu' / 'chuan_hoa.py')
        cls.ch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.ch)

    def test_cong_cua_thay_doi_2(self):
        b = lambda n1, r1, n2, r2: {'hoc': {'n': n1, 'r_tb': r1}, 'kiem': {'n': n2, 'r_tb': r2}}      # noqa: E731
        self.assertTrue(self.ch.qua_cong(b(3000, -0.12, 1400, -0.03), b(400, -0.05, 250, 0.01))[0])
        self.assertFalse(self.ch.qua_cong(b(3000, -0.12, 1400, -0.03), b(400, -0.05, 199, 0.20))[0])   # nửa KIỂM thiếu lệnh
        self.assertFalse(self.ch.qua_cong(b(3000, -0.12, 1400, -0.03), b(400, -0.05, 250, -0.04))[0])  # kém hơn ở nửa KIỂM

    def test_do_tra_lai_cong_tac(self):
        cu = PP.FVG_NEN_GIUA, PP.ICT_HOP_LUU
        m = _m15(200)
        m1 = pd.DataFrame({'open': 100.0, 'high': 100.1, 'low': 99.9, 'close': 100.0}, index=pd.date_range(T0, periods=200 * 15, freq='1min'))
        kq = self.ch.do('ict', m, _h1(m), m1, 0.17)
        self.assertEqual(set(kq), {'B0', 'B1', 'B2'})
        self.assertEqual((PP.FVG_NEN_GIUA, PP.ICT_HOP_LUU), cu)


if __name__ == '__main__':
    unittest.main()
