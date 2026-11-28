"""Snapshot AI phải đọc đúng mã, không gộp mọi cặp chứa XAU thành vàng USD."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from so_cong_khai import da_ma, gia, loi_nghiep_vu, phan_tich


class SnapshotSymbol(unittest.TestCase):
    def setUp(self):
        self.cfg = {'gia': {'ma_vang': 'XAUUSDp'}}
        self.now = datetime(2026, 11, 27, tzinfo=timezone.utc)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def snapshot(self, symbol):
        raw = {'ma': symbol, 'tf': 'M15', 'bid': 100., 'ask': 100.2, 'nguon': 'mt5', 'candles': [], 'het': self.now.isoformat()}
        with patch.object(gia, 'goi', return_value=raw) as gold, patch.object(da_ma, 'goi', return_value=raw) as asset, \
                patch.object(phan_tich, 'phan_tich', return_value={}) as gold_analysis, \
                patch.object(da_ma, 'phan_tich', return_value={}) as asset_analysis:
            result = loi_nghiep_vu.chup(self.cfg, symbol, now=self.now, thu_muc=Path(self.tmp.name))
        return result, gold, asset, gold_analysis, asset_analysis

    def test_cac_cap_vang_khac_phai_dung_dung_ma(self):
        for symbol in ('XAUEURp', 'XAUJPYp', 'XAUAUDp', 'XAUUSD247p'):
            with self.subTest(symbol=symbol):
                result, gold, asset, gold_analysis, asset_analysis = self.snapshot(symbol)
                gold.assert_not_called()
                gold_analysis.assert_not_called()
                asset.assert_called_once_with(self.cfg, symbol, 'M15', 300)
                asset_analysis.assert_called_once_with(self.cfg, symbol)
                self.assertEqual(result['ma'], symbol)

    def test_ma_vang_mac_dinh_va_bo_trong(self):
        for symbol in ('', 'XAUUSDp'):
            with self.subTest(symbol=symbol):
                _, gold, asset, gold_analysis, asset_analysis = self.snapshot(symbol)
                gold.assert_called_once_with(self.cfg, 'M15', 300)
                gold_analysis.assert_called_once_with(self.cfg)
                asset.assert_not_called()
                asset_analysis.assert_not_called()

    def test_vang_mac_dinh_tuy_cau_hinh(self):
        self.cfg['gia']['ma_vang'] = 'GOLD.demo'
        _, gold, asset, _, _ = self.snapshot('GOLD.demo')
        gold.assert_called_once_with(self.cfg, 'M15', 300)
        asset.assert_not_called()

    def test_btc_va_forex_khong_di_qua_luat_vang(self):
        for symbol in ('BTCUSDTp', 'EURUSDp'):
            with self.subTest(symbol=symbol):
                _, gold, asset, gold_analysis, asset_analysis = self.snapshot(symbol)
                gold.assert_not_called()
                gold_analysis.assert_not_called()
                asset.assert_called_once_with(self.cfg, symbol, 'M15', 300)
                asset_analysis.assert_called_once_with(self.cfg, symbol)
