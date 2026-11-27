# -*- coding: utf-8 -*-
"""Độ sâu thị trường ngay trên biểu đồ và trang Renko có đường trung bình, đường xu hướng (27/11/2026)."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from so_cong_khai import dich, do_sau, renko_trang

MUC_LON = r"""
function mucLon(j){const ds=[...(j.mua||[]).map(r=>[r[0],r[1],'mua']),...(j.ban||[]).map(r=>[r[0],r[1],'ban'])].filter(r=>r[1]>0);if(ds.length<3)return[];
 const xs=ds.map(r=>r[1]).sort((a,b)=>a-b),tv=xs[Math.floor(xs.length/2)];return ds.filter(r=>r[1]>=tv*2).sort((a,b)=>b[1]-a[1]).slice(0,3)}
"""


class DoSauTrenBieuDo(unittest.TestCase):
    def test_cong_tac_va_lop(self):
        js = do_sau.JS
        for must in ('id="dsau-tren"', "localStorage.getItem('so-dsau-tren')", "LOP.id='dsau-lop'", "title:'Mức lớn'", 'removePriceLine', 'if(window.PHAT_LAI){boLop();return}'):
            self.assertIn(must, js)
        self.assertIn(MUC_LON.strip().splitlines()[0][:60], js)

    def test_muc_lon_chay_that(self):
        """Mức lớn: khối lượng ít nhất gấp đôi trung vị, tối đa ba mức, lớn nhất trước."""
        node = shutil.which('node')
        if not node:
            self.skipTest('không có node')
        self.assertIn(MUC_LON.strip(), do_sau.JS)
        j = {'mua': [[100, 5], [99.9, 40], [99.8, 6]], 'ban': [[100.1, 4], [100.2, 7], [100.3, 25]]}
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'm.js'
            f.write_text(MUC_LON + f'console.log(JSON.stringify(mucLon({json.dumps(j)})))', encoding='utf-8')
            r = subprocess.run([node, str(f)], capture_output=True, text=True, timeout=30)  # noqa: S603
        self.assertEqual(json.loads(r.stdout), [[99.9, 40, 'mua'], [100.3, 25, 'ban']])


class RenkoThem(unittest.TestCase):
    def test_trung_binh_va_duong_ve(self):
        js = renko_trang.JS
        for must in ("tb:10}", "'so-rk-ve:'", 'const neo=i=>', 'const viTriNeo=q=>', "$('#rk-ve')", "$('#rk-xoa')", 'VEL.pop()'):
            self.assertIn(must, js)
        h = renko_trang.trang_renko('x')
        for must in ('id="rk-tb"', 'id="rk-ve"', 'id="rk-xoa"'):
            self.assertIn(must, h)

    def test_cau_trang_thai_dich_tron_cau(self):
        """Bản cũ ghép mảnh ("gạch" + "cuối" + "tăng" + "từ") nên tiếng Anh ra "brick last up from"; giờ mỗi trường hợp là một câu trọn."""
        d = dich.tu_dien('en')
        for k in ('Gạch cuối tăng, bắt đầu lúc %t', 'Cột cuối là cột O (giảm), bắt đầu lúc %t', '%n viên gạch dựng từ %c nến', 'Cỡ ô: %o (ATR14)'):
            self.assertIn(k, renko_trang.JS)
            self.assertIn(k, d)
        self.assertNotIn("'gạch':'cột'} cuối", renko_trang.JS)


if __name__ == '__main__':
    unittest.main()
