# -*- coding: utf-8 -*-
"""Dò lỗi mã bằng Ruff (cấu hình ở ruff.toml: chỉ các nhóm bắt lỗi thật). Máy không cài Ruff thì bỏ qua.

Vì sao có bài này: nhiều phiên cùng sửa mã; một tên chưa định nghĩa hay một lỗi cú pháp nằm trong nhánh ít chạy sẽ chỉ nổ lúc đang chạy thật
(có khi giữa lúc đăng tin lên kênh). Ruff bắt các lỗi đó ngay khi chạy bộ kiểm."""
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent


@unittest.skipUnless(importlib.util.find_spec('ruff'), 'máy không cài Ruff (python -m pip install ruff)')
class Ruff(unittest.TestCase):
    def test_khong_co_loi(self):
        r = subprocess.run([sys.executable, '-m', 'ruff', 'check', 'so_cong_khai', 'cong-cu', 'tests', '--no-cache', '--output-format', 'concise'],
                           cwd=GOC, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-1000:])


if __name__ == '__main__':
    unittest.main()
