# -*- coding: utf-8 -*-
"""Nối MT5 chậm không được làm treo cả webapp (27/11/2026).

Lỗi đã gặp: MT5 vừa mở chưa sẵn sàng, bước nối đứng chờ khoảng 60 giây trong lúc giữ khóa chung của luồng giá, nên mọi trang và API cần giá
treo theo, mỗi 60 giây lại treo lần nữa. Giờ bước nối chạy ngoài khóa: yêu cầu khác trả None ngay (trang dùng kho nến), chỉ một luồng nối."""
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import song  # noqa: E402


class NoiKhongTreo(unittest.TestCase):
    def test_dang_noi_thi_luong_khac_khong_cho(self):
        g = {'mt5': {'bat': True, 'thu_lai_giay': 0}}
        goi = []

        def noi_cham(cfgm, gg):
            goi.append(1)
            time.sleep(3)
            return None, None, 'MT5 chưa sẵn sàng'

        with mock.patch.dict(song._tt, {'fr': None, 'luc': 0, 'deps': None, 'mt5': None, 'thu': 0, 'dang_noi': False}):
            t = threading.Thread(target=song.khung_song, args=(g,), kwargs={'noi': noi_cham})
            t.start()
            time.sleep(.3)
            t0 = time.monotonic()
            self.assertIsNone(song.khung_song(g, noi=noi_cham))                # không đứng chờ luồng đang nối
            with song._khoa:                                                   # khóa chung cũng không bị giữ trong lúc nối
                pass
            self.assertLess(time.monotonic() - t0, 1)
            t.join(10)
            self.assertEqual(len(goi), 1)                                      # chỉ một luồng nối
            self.assertFalse(song._tt['dang_noi'])
            self.assertEqual(song._tt['ly_do'], 'MT5 chưa sẵn sàng')

    def test_noi_loi_van_nha_co(self):
        g = {'mt5': {'bat': True, 'thu_lai_giay': 0}}

        def noi_loi(cfgm, gg):
            raise RuntimeError('hỏng')

        with mock.patch.dict(song._tt, {'fr': None, 'luc': 0, 'deps': None, 'mt5': None, 'thu': 0, 'dang_noi': False}):
            self.assertIsNone(song.khung_song(g, noi=noi_loi))
            self.assertFalse(song._tt['dang_noi'])
            self.assertIn('RuntimeError', song._tt['ly_do'])


if __name__ == '__main__':
    unittest.main()
