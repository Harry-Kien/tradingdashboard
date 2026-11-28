# -*- coding: utf-8 -*-
"""Biểu đồ phủ kín chiều cao khung trên máy tính (bieu_do_cong_cu.py, 28/11/2026): chỉ bật khi JS đã tính (lớp bd-day), giữ dòng ghi công
Lightweight Charts (.ban-chan) ngay dưới biểu đồ, hàng phụ xuống dưới, không áp ở Toàn màn hình; JS không lỗi khi không có DOM thật."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from so_cong_khai import bieu_do_cong_cu


class BieuDoDay(unittest.TestCase):
    def test_luat_css(self):
        css = bieu_do_cong_cu.CSS
        khoi = css.split('@media(min-width:981px) and (min-height:600px){', 1)[1].split('}}', 1)[0]
        self.assertIn('.chartp.bd-day:not(.max)>.stage{flex:none;height:max(320px,var(--cao-bd,320px))', khoi)
        self.assertIn('.chartp.bd-day:not(.max)>.ban-chan{order:1', khoi)            # ghi công thư viện luôn trong màn hình đầu
        for k in ('.pt-presentation', '.ptk', '.hv-save', '.hv-health'):
            self.assertIn(f'.chartp.bd-day:not(.max)>{k}', khoi)
        self.assertNotIn('.max>', khoi)

    def test_js_khong_loi_khi_thieu_dom(self):
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('không có node')
        js = bieu_do_cong_cu.JS[bieu_do_cong_cu.JS.index('// 28/11/2026: máy tính — chiều cao biểu đồ'):]
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'a.js'
            f.write_text('globalThis.document={};globalThis.window=globalThis;' + js + ';console.log(typeof window.BDDAY)', encoding='utf-8')
            r = subprocess.run([node, str(f)], capture_output=True, text=True, encoding='utf-8', timeout=30)  # noqa: S603
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        self.assertEqual(r.stdout.strip(), 'undefined')                                # thoát sớm, không gắn gì


if __name__ == '__main__':
    unittest.main()
