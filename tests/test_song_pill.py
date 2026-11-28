# -*- coding: utf-8 -*-
"""Lỗi đã gặp (26/11/2026): khi MT5 tắt, nhãn "Chưa có giá trực tiếp · <lý do>" để white-space:nowrap nên trên điện thoại trang rộng tới 2169px
(kiem_giao_dien báo cuộn ngang). Trạng thái lỗi phải được xuống dòng và không rộng quá khung chứa."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import thi_truong_trang  # noqa: E402


class SongPill(unittest.TestCase):
    def test_trang_thai_loi_xuong_dong(self):
        css = Path(thi_truong_trang.__file__).read_text(encoding='utf-8')
        m = re.search(r'\.song-pill\.loi\{([^}]*)\}', css)
        self.assertIsNotNone(m)
        self.assertIn('white-space:normal', m.group(1))
        self.assertIn('max-width:100%', m.group(1))


if __name__ == '__main__':
    unittest.main()
