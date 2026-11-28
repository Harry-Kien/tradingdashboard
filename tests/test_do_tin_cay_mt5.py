"""Trạng thái giá và nhật ký: kiểm độc lập, không cần kho nến hay mã EA ngoài repo."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from so_cong_khai import gia, song, suc_khoe


class TinCayMt5Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.out = Path(self.temp.name)
        self.cfg = {'gia': {'ma_nguon': [], 'mt5': {'bat': False}}}
        self.het = datetime(2026, 11, 27, 6, 0, tzinfo=timezone.utc)
        self.quote = patch.object(gia, 'khung', return_value=None)
        self.quote.start()

    def tearDown(self):
        self.quote.stop()
        self.temp.cleanup()

    def _so(self):
        return {'loi': [], 'tai_khoan': [{'id': 'tk-1', 'ten': 'Demo', 'loi': [], 'tom': {'last_time': self.het, 'orphans': []}}]}

    def _muc(self, result, prefix):
        return next(item for item in result['muc'] if item['ten'].startswith(prefix))

    def test_gia_tat_khong_phai_ket_noi_thanh_cong(self):
        with patch.object(song, 'khung_song', return_value=None):
            result = suc_khoe.kiem(self.cfg, self.out, self._so(), now=self.het)
        price = self._muc(result, 'Giá trực tiếp')
        self.assertEqual(price['id'], 'mt5-price')
        self.assertEqual(price['muc'], 'tot')  # tắt chủ động không phải lỗi hệ thống
        self.assertFalse(price['ket_noi'])
        self.assertFalse(price['gia_moi'])

    def test_co_phien_mt5_nhung_gia_cu_khong_bao_la_gia_moi(self):
        with patch.object(song, 'khung_song', return_value={'het': self.het}), patch.object(song, 'thong_tin', return_value={}):
            result = suc_khoe.kiem(self.cfg, self.out, self._so(), now=self.het + timedelta(minutes=30))
        price = self._muc(result, 'Giá trực tiếp')
        self.assertTrue(price['ket_noi'])
        self.assertFalse(price['gia_moi'])
        self.assertEqual(price['muc'], 'chu_y')
        with patch.object(song, 'khung_song', return_value={'het': self.het}), patch.object(song, 'thong_tin', return_value={}):
            result = suc_khoe.kiem(self.cfg, self.out, self._so(), now=self.het + timedelta(seconds=10))
        self.assertTrue(self._muc(result, 'Giá trực tiếp')['gia_moi'])

    def test_nhat_ky_cu_khong_ket_luan_ea_da_tat(self):
        data = self._so()
        data['tai_khoan'][0]['tom']['last_time'] = self.het - timedelta(hours=30)
        with patch.object(song, 'khung_song', return_value={'het': self.het}), patch.object(song, 'thong_tin', return_value={}):
            result = suc_khoe.kiem(self.cfg, self.out, data, now=self.het)
        item = self._muc(result, 'Nhật ký EA')
        self.assertIn('không phải tín hiệu EA còn chạy', item['lam'])
        self.assertNotIn('EA hoặc MT5 của tài khoản này có thể đã tắt', item['lam'])


if __name__ == '__main__':
    unittest.main()
