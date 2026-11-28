"""Bài kiểm cho phần tính chỉ báo của cây nến đang chạy trên trang biểu đồ (JS, chạy bằng Node nếu máy có).

Trang tính tiếp EMA20/EMA50, Bollinger 20 và RSI14 theo từng tick từ số của nến đã đóng. Kết quả phải trùng công thức của
gia.goi: lấy nến đã đóng cuối cùng làm "nến đang chạy", xóa số máy chủ ở vị trí đó, để JS tính lại và so."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from so_cong_khai import bieu_do, gia  # noqa: E402
from test_gia import _kho  # noqa: E402

KIEM = r"""
const fs=require('fs'),[js,dl]=process.argv.slice(2).map(f=>fs.readFileSync(f,'utf8'));
const a=js.indexOf('function cbDung'),b=js.indexOf('// đồng hồ đếm ngược');if(a<0||b<a)throw new Error('không thấy khối chỉ báo trong JS');
const S=JSON.parse(dl),K=['ema20','ema50','bb_tren','bb_duoi','rsi'],D={candles:S.candles.map(x=>x.slice()),live:S.candles.length-1};
for(const k of K)D[k]=S[k].slice();const want={};for(const k of K){want[k]=S[k][D.live];D[k][D.live]=null}
// eval chỉ chạy đoạn JS của chính dự án (bieu_do.JS do bài kiểm tự ghi ra), không có dữ liệu ngoài; cần eval để các hàm thấy biến D, CBS ở đây
let CBS=null;eval(js.slice(a,b));cbSong();
const got={};for(const k of K)got[k]=D[k][D.live];console.log(JSON.stringify({want,got}));
"""


@unittest.skipUnless(shutil.which('node'), 'máy không có Node.js')
class ChiBaoTickTest(unittest.TestCase):
    def test_chi_bao_nen_dang_chay_trung_cong_thuc_may_chu(self):
        gia._nho.clear()
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            _kho(d, datetime(2026, 11, 16, tzinfo=timezone.utc), 4 * 1440 + 7)
            (d / 'bd.js').write_text(bieu_do.JS, encoding='utf-8')
            (d / 'kiem.js').write_text(KIEM, encoding='utf-8')
            for tf in ('M5', 'M15', 'H1'):
                g = {'kho_m1': str(d), 'ma_nguon': [], 'so_thang': 4}
                (d / 'd.json').write_text(json.dumps(gia.goi({'gia': g}, tf, 600, datetime(2026, 11, 20, 0, 30, tzinfo=timezone.utc))),
                                          encoding='utf-8')
                r = subprocess.run(['node', str(d / 'kiem.js'), str(d / 'bd.js'), str(d / 'd.json')], capture_output=True, text=True,
                                   encoding='utf-8', timeout=60)
                self.assertEqual(r.returncode, 0, r.stderr)
                kq = json.loads(r.stdout)
                for k, v in kq['want'].items():
                    self.assertIsNotNone(v, f'{tf} {k}')
                    # số gốc (nến trước) và số để so đều đã làm tròn 2 chữ số, mỗi bên sai tối đa 0,005
                    self.assertAlmostEqual(kq['got'][k], v, delta=0.011, msg=f'{tf} {k}')
        gia._nho.clear()


if __name__ == '__main__':
    unittest.main()
