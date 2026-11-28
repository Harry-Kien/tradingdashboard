"""Vị thế của các mã vàng chéo không được vẽ lên chart vàng/USD."""
import unittest
from unittest.mock import patch

from so_cong_khai import gia


class GiaViTheMa(unittest.TestCase):
    def test_vang_usd_khong_lan_vang_eur_hay_vang_247(self):
        records = [{'ma': k} for k in ('XAUUSDp', 'XAUEURp', 'XAUUSD247p', 'EURUSDp')]
        records += [{'loai': 'tin_hieu', 'nguon': 'bot'}, {'nguon': 'khong_ro'}]
        with patch.object(gia, 'lenh_dang_mo', return_value=records):
            result = gia.lenh_cho_vang({'gia': {'ma_vang': 'XAUUSDp'}})
        self.assertEqual(result, [records[0], records[4]])

    def test_ton_trong_ma_vang_cua_san(self):
        records = [{'ma': 'GOLD.demo'}, {'ma': 'XAUUSDp'}, {'ma': 'XAUEURp'}]
        with patch.object(gia, 'lenh_dang_mo', return_value=records):
            result = gia.lenh_cho_vang({'gia': {'ma_vang': 'GOLD.demo'}})
        self.assertEqual(result, [records[0]])


if __name__ == '__main__':
    unittest.main()
