# -*- coding: utf-8 -*-
"""Độ sâu thị trường (do_sau.py): đọc sổ lệnh sàn gửi về MT5 bằng MT5 giả; chỉ đọc; sàn không gửi thì nói rõ, không bịa số."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import do_sau, song  # noqa: E402


class MT5Gia:
    def __init__(self, so=None, nhan=True):
        self.so, self.nhan, self.goi = so, nhan, []

    def market_book_add(self, ma):
        self.goi.append(('add', ma))
        return self.nhan

    def market_book_release(self, ma):
        self.goi.append(('release', ma))
        return True

    def market_book_get(self, ma):
        return self.so

    def symbol_info(self, ma):
        return NS(digits=2)


class DoSau(unittest.TestCase):
    def setUp(self):
        do_sau._dk.clear()

    def _doc(self, mt5, ma='XAUUSDp'):
        with mock.patch.object(song, 'khung_song', return_value={'nguon': 'mt5'}), mock.patch.dict(song._tt, {'mt5': mt5, 'sym': 'XAUUSDp'}):
            return do_sau.doc({}, ma)

    def test_doc_va_sap_xep(self):
        so = (NS(type=1, price=3572.5, volume=2000, volume_dbl=2000.0), NS(type=1, price=3571.9, volume=1000, volume_dbl=1000.0),
              NS(type=2, price=3571.2, volume=500, volume_dbl=500.0), NS(type=2, price=3571.6, volume=3000, volume_dbl=3000.0))
        kq = self._doc(MT5Gia(so))
        self.assertTrue(kq['san_sang'] and kq['co_kl'])
        self.assertEqual(kq['ban'], [[3571.9, 1000.0], [3572.5, 2000.0]])       # bán: gần giá nhất trước
        self.assertEqual(kq['mua'], [[3571.6, 3000.0], [3571.2, 500.0]])        # mua: gần giá nhất trước

    def test_san_khong_gui_thi_noi_ro(self):
        self.assertFalse(self._doc(MT5Gia(nhan=False))['san_sang'])
        m = MT5Gia(so=None)
        self.assertTrue(self._doc(m)['dang_cho'])                               # vừa đăng ký: đang chờ
        self.assertIn('không gửi sổ lệnh', self._doc(m)['ly_do'])              # lần sau vẫn trống: sàn không gửi

    def test_khong_khoi_luong(self):
        kq = self._doc(MT5Gia((NS(type=1, price=60500.5, volume=0, volume_dbl=0.0), NS(type=2, price=60500.1, volume=0, volume_dbl=0.0))), 'BTCUSDTp')
        self.assertTrue(kq['san_sang'])
        self.assertFalse(kq['co_kl'])

    def test_chi_doc_va_gioi_han_dang_ky(self):
        m = MT5Gia((NS(type=1, price=1.1, volume=1, volume_dbl=1.0),))
        for i in range(do_sau.TOI_DA_MA + 2):
            self._doc(m, f'MA{i}')
        self.assertLessEqual(len(do_sau._dk), do_sau.TOI_DA_MA)
        self.assertTrue(any(g[0] == 'release' for g in m.goi))
        src = Path(do_sau.__file__).read_text(encoding='utf-8')
        for cam in ('order_send', 'order_check', 'positions_'):
            self.assertNotIn(cam, src)

    def test_trang_co_bang(self):
        from so_cong_khai import bieu_do                                      # noqa: PLC0415
        h = bieu_do.trang_bieu_do('Harry')
        self.assertIn("fetch('/api/so-lenh'", h)
        self.assertIn("if path == '/api/so-lenh':", (Path(do_sau.__file__).parent / 'web.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
