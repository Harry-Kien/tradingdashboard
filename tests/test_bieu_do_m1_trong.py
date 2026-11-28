# -*- coding: utf-8 -*-
"""Khung M1 (chỉ để xem) và chế độ "Biểu đồ trống" của trang Biểu đồ. Kho nến 1 phút dựng giả trong thư mục tạm; không gọi MT5."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from so_cong_khai import bieu_do, da_ma, gia, song
from tests.test_gia import _kho


class KhungM1(unittest.TestCase):
    def setUp(self):
        gia._nho.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.start = datetime(2026, 11, 16, tzinfo=timezone.utc)
        _kho(self.d, self.start, 2 * 1440 + 7)
        self.cfg = {'ten': 'Thử', 'gia': {'kho_m1': str(self.d), 'ma_nguon': [], 'so_thang': 4}}
        self.now = self.start + timedelta(days=2, minutes=30)

    def tearDown(self):
        gia._nho.clear()
        self.tmp.cleanup()

    def test_khung_m1_tu_kho_nen(self):
        self.assertEqual(gia.KHUNG['M1'], 1)
        self.assertIn('M1', song.SO_NEN)
        self.assertIn('M1', da_ma.SO_NEN)
        self.assertNotIn('M1', gia._QUY)                       # phần học nhiều năm (hoc._khung) không phải dựng thêm M1
        fr = gia.khung(self.cfg['gia'])
        self.assertEqual(fr['M1'].index[-1].to_pydatetime(), self.start + timedelta(days=2, minutes=6))   # nến 1 phút cuối đã đóng
        d = gia.goi(self.cfg, 'M1', 300, self.now)
        self.assertEqual((d['tf'], len(d['candles']), len(d['ema20'])), ('M1', 300, 300))
        self.assertEqual(d['candles'][-1][0] - d['candles'][-2][0], 60)
        self.assertIsNotNone(d['ema200'][-1])                  # đủ nến khởi động cho chỉ báo dài
        json.dumps(d)


class BieuDoTrong(unittest.TestCase):
    def test_nut_va_cac_cho_an(self):
        h = bieu_do.trang_bieu_do('Harry')
        self.assertIn('id="trong-btn"', h)
        self.assertIn("localStorage.getItem('so-trong')==='1'", h)
        self.assertIn("get('anh')!=='1'", h)                   # ảnh gửi Telegram không bao giờ ở chế độ trống
        self.assertIn('if(price!=null&&(giu||!TRONG))', h)     # đường giá của hệ thống ẩn, giá Ask vẫn giữ
        self.assertIn("ngang(D.ask,P.ask,'',0,1,undefined,1)", h)
        self.assertIn('if(TRONG){HIT.length=0;veVe(X,', h)       # lớp phủ chỉ còn hình người dùng vẽ
        self.assertIn('TRONG_ON={...on};for(const k in on)on[k]=0', h)   # tắt chỉ báo hệ thống, nhớ để bật lại
        self.assertIn('data-tf="M1"', h)
        self.assertIn("k>='1'&&k<='7'", h)


if __name__ == '__main__':
    unittest.main()
