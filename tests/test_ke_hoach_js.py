"""Bản JavaScript của Kế hoạch vốn và lệnh (ke_hoach_js.JS_TINH, dùng ở demo tĩnh) phải ra cùng kết quả với ke_hoach.lap trên cùng đầu vào.
Chạy bằng Node.js; máy không có Node thì bỏ qua. Mô phỏng dùng bộ sinh số ngẫu nhiên khác nên chỉ so theo sai số thống kê."""
import json
import random
import shutil
import subprocess
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import ke_hoach, ke_hoach_js  # noqa: E402

NODE = shutil.which('node')
TK = {'tien': 'USD', 'don_bay': 100, 'dung_lenh': 50.0}


def _raw(seed: int, gia: float, buoc: float, so_le: int, dt: dict) -> dict:
    rng = random.Random(seed)
    cao, thap, g = [], [], gia
    for _ in range(119):
        g += rng.uniform(-buoc, buoc)
        h, lo = g + rng.uniform(0, buoc), g - rng.uniform(0, buoc)
        cao.append(round(h, so_le))
        thap.append(round(lo, so_le))
    return {'ma': dt['goc'], 'khung': 'H1', 'dac_ta': dt, 'bid': round(g, so_le), 'ask': round(g + buoc / 20, so_le), 'atr': buoc * 1.3, 'cao': cao, 'thap': thap}


VANG = {'goc': 'XAUUSD', 'so_le': 2, 'diem': 0.01, 'gt1': 100.0, 'lot_min': 0.01, 'lot_buoc': 0.01, 'lot_max': 50.0, 'ky_quy_1lot': 3460.0, 'muc_dung': 0}
EUR = {'goc': 'EURUSD', 'so_le': 5, 'diem': 0.00001, 'gt1': 100000.0, 'lot_min': 0.01, 'lot_buoc': 0.01, 'lot_max': 100.0, 'ky_quy_1lot': 1095.0, 'muc_dung': 10}


class _Bang:
    def __init__(self, raw):
        self._dk = threading.Lock()
        self.dac_ta = {raw['ma']: raw['dac_ta']}
        self.gia = {raw['ma']: [raw['bid'], raw['ask'], 0]}
        self.kt = {raw['ma']: {'H1': {'atr': raw['atr']}}}
        self.tai_khoan = TK
        self.raw = raw

    def _cfg(self):
        return {}, {}

    def _mt5_fn(self, g):
        return object()

    def _rates(self, mt5, ma, khung, n):
        return {'high': self.raw['cao'] + [0.0], 'low': self.raw['thap'] + [0.0]}     # thêm nến đang chạy: lap bỏ nến cuối


@unittest.skipUnless(NODE, 'máy không có Node.js')
class KhopPythonTest(unittest.TestCase):
    def test_cung_ket_qua(self):
        canh = [(_raw(1, 3460, 12, 2, VANG), {'chieu': 'MUA', 'von': 470.0}),
                (_raw(2, 3460, 12, 2, VANG), {'chieu': 'BAN', 'von': 10000.0, 'muc': 'an_toan'}),
                (_raw(3, 3460, 30, 2, VANG), {'chieu': 'MUA', 'von': 5000.0, 'muc': 'manh', 'thang': 40, 'rr': 1.5}),
                (_raw(4, 1.095, 0.0015, 5, EUR), {'chieu': 'BAN', 'von': 500.0, 'muc': 'tu_dat', 'rui_ro': 3.0}),
                (_raw(5, 1.095, 0.0015, 5, EUR), {'chieu': 'MUA', 'von': 2000.0, 'vao': 1.1, 'sl': 1.098})]
        js = ke_hoach_js.JS_TINH + ';const ds=JSON.parse(require("fs").readFileSync(0,"utf8"));' \
            'console.log(JSON.stringify(ds.map(([r,p])=>KH.lap(r,p,' + json.dumps(TK) + '))));'
        out = subprocess.run([NODE, '-e', js], input=json.dumps(canh), capture_output=True, text=True, encoding='utf-8', timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        kq_js = json.loads(out.stdout)
        for (raw, p), j in zip(canh, kq_js):
            py = ke_hoach.lap({}, _Bang(raw), raw['ma'], p['chieu'], 'H1', p.get('vao'), p.get('sl'), p['von'], p.get('muc', 'can_bang'),
                              p.get('rui_ro'), p.get('thang', 50.0), p.get('rr', 2.0))
            py = json.loads(json.dumps(py))
            mp_py, mp_js = py.pop('mo_phong'), j.pop('mo_phong')
            self._gan(py, j, p)
            self.assertEqual(mp_py.get('theo_rui_ro_that'), mp_js.get('theo_rui_ro_that'), p)
            for k in ('ky_vong_r', 'hoa_von_pct', 'so_lenh', 'lan'):
                self.assertEqual(mp_py[k], mp_js[k], (p, k))
            for k, sai in (('xs_sut_20', 4), ('xs_sut_50', 4), ('trung_vi_pct', max(6, abs(mp_py['trung_vi_pct']) * 0.1)), ('sut_trung_vi_pct', 3)):
                self.assertAlmostEqual(mp_py[k], mp_js[k], delta=sai, msg=(p, k))

    def _gan(self, a, b, p, duong='kq'):
        """So hai cây JSON: số được lệch một đơn vị ở chữ số làm tròn cuối (Python làm tròn nửa về số chẵn, JS làm tròn nửa lên)."""
        if isinstance(a, dict):
            self.assertEqual(set(a), set(b), (p, duong))
            for k in a:
                self._gan(a[k], b[k], p, f'{duong}.{k}')
        elif isinstance(a, list):
            self.assertEqual(len(a), len(b), (p, duong))
            for i, (x, y) in enumerate(zip(a, b)):
                self._gan(x, y, p, f'{duong}[{i}]')
        elif isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)):
            self.assertAlmostEqual(a, b, delta=max(1e-9, abs(a) * 1e-9, 10 ** -(len(str(a).split('.')[-1]) if '.' in str(a) else 0)), msg=(p, duong))
        else:
            self.assertEqual(a, b, (p, duong))


if __name__ == '__main__':
    unittest.main()
