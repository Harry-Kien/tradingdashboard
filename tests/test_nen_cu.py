"""Bài kiểm cho phần nến lùi về đầu năm: vàng ghép từ kho nến 1 phút, mã khác đọc từ một MT5 giả; các chuỗi chỉ báo phải dài bằng
chuỗi nến, chỉ gồm nến của năm đang xem, bị cắt đúng ở mức trần, và không có lời gọi chọn mã hay đặt lệnh."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from so_cong_khai import bieu_do, da_ma, gia, nen_cu, song  # noqa: E402
from test_da_ma import HET, MT5Gia  # noqa: E402
from test_gia import MA_THAT, _kho  # noqa: E402


class NenCuVangTest(unittest.TestCase):
    def setUp(self):
        gia._nho.clear()
        nen_cu._nho.clear()
        song._tt.update(deps=None, mt5=None, fr=None, thu=0.0, luc=0.0)
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.start = datetime(2025, 12, 29, tzinfo=timezone.utc)                    # kho bắt đầu từ cuối năm trước
        _kho(self.d, self.start, 12 * 1440)
        self.cfg = {'ten': 'Thử', 'gia': {'kho_m1': str(self.d), 'ma_nguon': MA_THAT, 'so_thang': 4}}
        self.now = self.start + timedelta(days=12, minutes=3)

    def tearDown(self):
        gia._nho.clear()
        nen_cu._nho.clear()
        self.tmp.cleanup()

    def test_chi_gom_nen_cua_nam_dang_xem(self):
        r = nen_cu.goi(self.cfg, '', 'M15', self.now)
        dau_nam = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
        self.assertEqual((r['nam'], r['ma'], r['cat_bot']), (2026, '', False))
        self.assertEqual(r['candles'][0][0], dau_nam)                                # nến của 29–31/12/2025 không có mặt
        self.assertEqual(r['so_nen'], 9 * 96)                                        # 9 ngày của 2026, mỗi ngày 96 nến M15
        t = [c[0] for c in r['candles']]
        self.assertEqual(t, sorted(set(t)))
        for k in ('ema20', 'ema50', 'bb_tren', 'bb_duoi', 'rsi'):
            self.assertEqual(len(r[k]), r['so_nen'], k)
        self.assertIsNone(r['ema50'][0])                                             # chỉ báo tính từ nến đầu năm: 49 nến đầu chưa có EMA50
        self.assertIsNotNone(r['ema50'][60])
        json.dumps(r)

    def test_m1_chi_lui_20_ngay(self):
        now = self.start + timedelta(days=12, minutes=3)
        r = nen_cu.goi(self.cfg, '', 'M1', now)
        tu = int(max(datetime(2026, 1, 1, tzinfo=timezone.utc), now - timedelta(days=20)).timestamp())
        self.assertEqual(r['candles'][0][0], tu)
        self.assertEqual(r['candles'][1][0] - r['candles'][0][0], 60)
        self.assertEqual(len(r['ema20']), len(r['candles']))
        self.assertEqual(len(r["candles"]), 9 * 1440)                                # 9 ngày của 2026, mỗi ngày 1.440 nến M1

    def test_khung_ngay_va_khung_la(self):
        r = nen_cu.goi(self.cfg, '', 'D1', self.now)
        self.assertTrue(all(datetime.fromtimestamp(c[0], timezone.utc).weekday() != 6 for c in r['candles']))    # không có nến Chủ nhật
        with self.assertRaises(ValueError):
            nen_cu.goi(self.cfg, '', 'M7', self.now)                        # M1, W1 đã có (26/11/2026); M7 không phải khung của hệ thống

    def test_cat_o_muc_tran(self):
        cu = nen_cu.TOI_DA
        nen_cu.TOI_DA = 100
        try:
            r = nen_cu.goi(self.cfg, '', 'M5', self.now)
        finally:
            nen_cu.TOI_DA = cu
        self.assertEqual((r['so_nen'], r['cat_bot']), (100, True))
        self.assertEqual(r['candles'][-1][0], int((self.start + timedelta(days=12, minutes=-5)).timestamp()))    # giữ phần mới nhất


class NenCuMaKhacTest(unittest.TestCase):
    def setUp(self):
        nen_cu._nho.clear()
        self.mt5 = MT5Gia()
        self.that = da_ma._mt5
        da_ma._mt5 = lambda g: self.mt5
        self.cfg = {'ten': 'Thử', 'gia': {'ma_nguon': MA_THAT, 'ma_vang': 'XAUUSDp'}}

    def tearDown(self):
        da_ma._mt5 = self.that
        nen_cu._nho.clear()

    def test_doc_tu_mt5_va_lam_tron_theo_ma(self):
        r = nen_cu.goi(self.cfg, 'EURUSDp', 'H1', HET)
        dau_nam = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
        self.assertEqual((r['ma'], r['nam']), ('EURUSDp', 2026))
        self.assertGreaterEqual(r['candles'][0][0], dau_nam)
        self.assertLess(r['candles'][0][0], dau_nam + 3600)
        self.assertTrue(all(len(str(c[4]).split('.')[-1]) <= 5 for c in r['candles'][:50]))
        self.assertEqual(len(r['rsi']), r['so_nen'])
        goi = [g for g in self.mt5.goi if g[0] == 'EURUSDp']
        self.assertEqual(len(goi), 1)                                                # một lần đọc, nến đã đóng (vị trí 1)
        self.assertEqual(goi[0][2], 1)
        nen_cu.goi(self.cfg, 'EURUSDp', 'H1', HET)
        self.assertEqual(len([g for g in self.mt5.goi if g[0] == 'EURUSDp']), 1)     # lần sau lấy từ bộ nhớ

    def test_ma_khong_hien_va_khong_co_mt5(self):
        with self.assertRaises(ValueError):
            nen_cu.goi(self.cfg, 'AUDUSDp', 'H1', HET)                               # mã không hiện trong Market Watch
        da_ma._mt5 = lambda g: None
        with self.assertRaises(ValueError):
            nen_cu.goi(self.cfg, 'BTCUSDTp', 'H1', HET)

    def test_ma_nguon_chi_doc(self):
        src = Path(nen_cu.__file__).read_text(encoding='utf-8')
        for banned in ('order_send', 'order_check', 'TRADE_ACTION', 'symbol_select', 'positions_get'):
            self.assertNotIn(banned, src)
        html = bieu_do.trang_bieu_do('Thử')
        for must in ('/api/gia-cu', 'id="his"', 'id="dv"', 'Rê chuột vào từng ghi chú', 'Chưa mô hình nào trong dữ liệu đạt tỷ lệ thắng 90%'):
            self.assertIn(must, html)


if __name__ == '__main__':
    unittest.main()
