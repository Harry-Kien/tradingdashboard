"""Nhãn lệnh đang mở ở trang Tổng quan: chiều lệnh là chữ Mua/Bán trong thẻ riêng nên bản tiếng Anh ra Buy/Sell với mọi tên EA."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import dich, trang  # noqa: E402

D = json.loads((Path(__file__).resolve().parent.parent / 'so_cong_khai' / 'dich' / 'en.json').read_text(encoding='utf-8'))


class NhanLenhTest(unittest.TestCase):
    def test_tieng_anh_dich_chieu_lenh(self):
        for o, en in (({'ten': 'EA Lạ Tên', 'huong': 'SELL', 'lot': 0.02}, 'Sell'), ({'ten': 'Bot 7', 'huong': 'BUY'}, 'Buy')):
            h = trang._nhan_lenh(o)
            self.assertIn('text-transform:uppercase', h)
            self.assertIn(f'>{en}<', dich.dich_html(h, D))
        self.assertIn('0.02', trang._nhan_lenh({'ten': 'EA E', 'huong': 'SELL', 'lot': 0.02}))

    def test_thieu_ten_thi_dung_nhan_va_thoat_html(self):
        self.assertEqual(trang._nhan_lenh({'nhan': 'A <b>'}), 'A &lt;b&gt;')
        self.assertIn('&lt;x&gt;', trang._nhan_lenh({'ten': '<x>', 'huong': 'BUY'}))


if __name__ == '__main__':
    unittest.main()
