# -*- coding: utf-8 -*-
"""Trang Renko và Điểm & Hình (/renko): chạy thật thuật toán JS trong Node với chuỗi giá biết trước kết quả."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import dich, renko_trang, trang  # noqa: E402
from so_cong_khai.thuong_hieu import TEN  # noqa: E402

GOC = Path(__file__).resolve().parent.parent / 'so_cong_khai'


class Renko(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'máy không có Node.js')
    def test_thuat_toan(self):
        js = renko_trang.JS
        ham = re.search(r'function renko\(.*?\nfunction tinh', js, re.S).group(0).rsplit('function tinh', 1)[0]
        ma = ham + r"""
const cs=g=>g.map((v,i)=>[i,v,v,v,v]);
const r=renko(cs([100,100.4,101,103.2,102.5,101.5,100.9,99]),1).map(k=>[k[0],k[1],k[2]]);
const p=diemHinh(cs([100,101,103.5,102,100.4,99.2,98.9,100,102.3]),1,3).map(k=>[k[0],k[1],k[2]]);
console.log(JSON.stringify({r,p}));"""
        with tempfile.TemporaryDirectory() as d:
            tep = Path(d) / 'rk.js'
            tep.write_text(ma, encoding='utf-8')
            kq = subprocess.run(['node', str(tep)], capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(kq.returncode, 0, kq.stderr[-500:])
        x = json.loads(kq.stdout.strip())
        # Renko cỡ ô 1: lên 100→103 (3 gạch tăng); 101,5 chưa đủ 2 ô; 100,9 đủ 2 ô → gạch giảm 102→101; 99 → thêm 2 gạch giảm
        self.assertEqual(x['r'], [[100, 101, 1], [101, 102, 1], [102, 103, 1], [101, 102, -1], [100, 101, -1], [99, 100, -1]])
        # Điểm & Hình cỡ ô 1, đảo 3 ô: cột X 100→103. Ô X trên cùng là 102–103, nên phải về tới 99 mới đủ 3 ô O (99,2 chưa đủ; 98,9 đủ):
        # cột O từ 102 xuống 99. Sau đó 102,3 chưa lên đủ 3 ô từ đáy (cần 103) nên vẫn là cột O.
        self.assertEqual(x['p'], [[100, 103, 1], [99, 102, -1]])

    def test_trang_tuyen_menu_va_dich(self):
        h = renko_trang.trang_renko(TEN)
        self.assertIn('id="rk-cv"', h)
        self.assertNotIn("method:'POST'", renko_trang.JS)
        self.assertIn("if path == '/renko':", (GOC / 'web.py').read_text(encoding='utf-8'))
        self.assertTrue(any(c[2] == '/renko' for m in trang.MENU if m[3] for c in m[3]))
        thu = set()
        dich.dich_html(h, dich.tu_dien('en'), thu)
        self.assertEqual(sorted(thu), [])


if __name__ == '__main__':
    unittest.main()
