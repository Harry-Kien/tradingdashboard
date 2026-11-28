# -*- coding: utf-8 -*-
"""Chỉ báo thêm ngày 28/11/2026 (so_cong_khai.bieu_do_chi_bao): Pivot Points nhiều kiểu và kỳ, trung bình động khung lớn (MTF),
Auto Fibonacci, Elder Force Index. Đối chiếu với định nghĩa gốc viết lại bằng pandas. Không có Node thì bỏ qua."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from test_bieu_do_chi_bao import NODE, VO, _nen

from so_cong_khai import bieu_do_chi_bao as M


@unittest.skipUnless(NODE, 'không có Node')
class ChiBao2811(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = _nen(4000, 11)                                                     # khoảng 41 ngày M15: đủ nhiều tuần và qua một lần đổi tháng
        cs = [[int(t.timestamp()), o, h, l, c, int(v)] for t, o, h, l, c, v in zip(cls.b.index, cls.b['open'], cls.b['high'], cls.b['low'], cls.b['close'], cls.b['vol'])]
        js = VO + M.JS + r"""
const cs=JSON.parse(require('fs').readFileSync(process.argv[2],'utf8')),H=cs.map(r=>r[2]),L=cs.map(r=>r[3]),C=cs.map(r=>r[4]),O=cs.map(r=>r[1]),V=cs.map(r=>r[5]),T=cs.map(r=>r[0]);
const t=(k,p)=>CBCN.LIB[k].tinh(H,L,C,O,{...Object.fromEntries(CBCN.LIB[k].ts.map(x=>[x[0],x[2]])),...p},V,T).map(x=>[x[0],x[1]]);
const out={pv1:t('piv',{kieu:1,ky:1}),pv2:t('piv',{kieu:2,ky:2}),pv3:t('piv',{kieu:3,ky:3}),pv4:t('piv',{kieu:4,ky:1}),pv9:t('piv',{kieu:9,ky:0}),
 ema:t('mtf',{phut:60,n:20,loai:1}),sma:t('mtf',{phut:60,n:20,loai:2}),d1:t('mtf',{phut:1440,n:3,loai:1}),efi:t('efi',{n:13}),afib:t('afib',{pt:.5}),
 khongT:CBCN.LIB.mtf.tinh(H,L,C,O,{phut:60,n:20,loai:1,gio:0}).map(x=>x[1].filter(v=>v!=null).length)};
process.stdout.write(JSON.stringify(out));"""
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'cs.json').write_text(json.dumps(cs), encoding='utf-8')
            (Path(d) / 't.js').write_text(js, encoding='utf-8')
            r = subprocess.run([NODE, str(Path(d) / 't.js'), str(Path(d) / 'cs.json')], capture_output=True, text=True, encoding='utf-8', timeout=120)  # noqa: S603
        if r.returncode:
            raise AssertionError(r.stderr[-2000:])
        cls.o = json.loads(r.stdout)

    def khop(self, js, ky_vong, ten, tol=1e-6):
        a = np.array([np.nan if v is None else v for v in js], dtype=float)
        b = np.asarray(ky_vong, dtype=float)
        self.assertEqual(len(a), len(b), ten)
        self.assertTrue(np.array_equal(np.isnan(a), np.isnan(b)), f'{ten}: chỗ trống khác nhau')
        m = ~np.isnan(b)
        self.assertGreater(m.sum(), 100, ten)
        self.assertLess(float(np.max(np.abs(a[m] - b[m]))), tol, ten)

    def _ky_truoc(self, nhom):
        b = self.b
        g = pd.DataFrame({'h': b['high'], 'l': b['low'], 'c': b['close']}).groupby(nhom).agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).shift(1)
        return g.reindex(nhom)

    def test_pivot_co_dien_ngay(self):
        k = self._ky_truoc(self.b.index.floor('D'))
        h, l, c = k['h'].to_numpy(), k['l'].to_numpy(), k['c'].to_numpy()
        p = (h + l + c) / 3
        mong = [p, 2 * p - l, p + h - l, h + 2 * (p - l), 2 * p - h, p - (h - l), l - 2 * (h - p)]
        ten = [x[0] for x in self.o['pv1']]
        self.assertEqual(ten, ['P', 'R1', 'R2', 'R3', 'S1', 'S2', 'S3'])
        for j in range(7):
            self.khop(self.o['pv1'][j][1], mong[j], 'Pivot cổ điển ' + ten[j])

    def test_pivot_fibonacci_tuan_bat_dau_thu_hai(self):
        i = self.b.index
        k = self._ky_truoc(i.normalize() - pd.to_timedelta(i.day_of_week, unit='D'))
        h, l, c = k['h'].to_numpy(), k['l'].to_numpy(), k['c'].to_numpy()
        p, r = (h + l + c) / 3, h - l
        for j, v in enumerate([p, p + .382 * r, p + .618 * r, p + r, p - .382 * r, p - .618 * r, p - r]):
            self.khop(self.o['pv2'][j][1], v, f'Pivot Fibonacci tuần {j}')

    def test_pivot_camarilla_thang_va_woodie(self):
        k = self._ky_truoc(self.b.index.tz_localize(None).to_period('M').to_timestamp())
        h, l, c = k['h'].to_numpy(), k['l'].to_numpy(), k['c'].to_numpy()
        r = h - l
        for j, v in enumerate([(h + l + c) / 3, c + r * 1.1 / 12, c + r * 1.1 / 6, c + r * 1.1 / 4, c - r * 1.1 / 12, c - r * 1.1 / 6, c - r * 1.1 / 4]):
            self.khop(self.o['pv3'][j][1], v, f'Pivot Camarilla tháng {j}')
        k = self._ky_truoc(self.b.index.floor('D'))
        h, l, c = k['h'].to_numpy(), k['l'].to_numpy(), k['c'].to_numpy()
        p = (h + l + 2 * c) / 4
        self.khop(self.o['pv4'][0][1], p, 'Woodie P')
        self.khop(self.o['pv4'][1][1], 2 * p - l, 'Woodie R1')
        self.khop(self.o['pv9'][0][1], self.o['pv4'][0][1], 'kiểu 9, kỳ 0 được kẹp về Woodie, ngày')

    def test_mtf_khop_nen_khung_lon_khi_dong(self):
        c = self.b['close']
        h1 = c.resample('1h').last()
        cuoi = ~c.index.floor('h').duplicated(keep='last')                        # nến M15 cuối cùng của mỗi giờ
        for khoa, mong, ten in (('ema', h1.ewm(span=20, adjust=False, min_periods=20).mean(), 'EMA 20 H1'),
                                ('sma', h1.rolling(20).mean(), 'SMA 20 H1')):
            self.assertEqual(self.o[khoa][0][0], ten)
            a = np.array([np.nan if v is None else v for v in self.o[khoa][0][1]], dtype=float)
            self.khop(a[cuoi], mong.to_numpy(), ten)
        self.assertEqual(self.o['d1'][0][0], 'EMA 3 D1')
        self.assertEqual(self.o['khongT'], [0])                                    # thiếu giờ nến thì không vẽ

    def test_mtf_khong_nhin_truoc(self):
        """Nến M15 đầu giờ chỉ dùng các nến H1 đã đóng và giá đóng hiện tại, không dùng giá đóng cuối giờ (chưa xảy ra)."""
        c = self.b['close']
        h1 = c.resample('1h').last().ewm(span=20, adjust=False, min_periods=20).mean().shift(1)
        dau = ~c.index.floor('h').duplicated(keep='first')
        al = 2 / 21
        mong = al * c[dau].to_numpy() + (1 - al) * h1.to_numpy()
        a = np.array([np.nan if v is None else v for v in self.o['ema'][0][1]], dtype=float)[dau]
        m = ~np.isnan(mong)
        self.assertLess(float(np.max(np.abs(a[m] - mong[m]))), 1e-6)

    def test_elder_force_index(self):
        b = self.b
        f = ((b['close'] - b['close'].shift()) * b['vol'].astype(float)).ewm(span=13, adjust=False, min_periods=13).mean()
        self.khop(self.o['efi'][0][1], f, 'EFI 13')

    def test_auto_fibonacci(self):
        ten = [x[0] for x in self.o['afib']]
        self.assertEqual(ten, ['Fib 0', 'Fib 23.6', 'Fib 38.2', 'Fib 50', 'Fib 61.8', 'Fib 78.6', 'Fib 100'])
        v = [np.array([np.nan if x is None else x for x in s[1]], dtype=float) for s in self.o['afib']]
        dau = int(np.argmax(~np.isnan(v[0])))
        self.assertTrue(all(np.isnan(s[:dau]).all() and not np.isnan(s[dau:]).any() and np.ptp(s[dau:]) == 0 for s in v))   # mỗi mức là một đường ngang từ đầu sóng
        f0, f100 = v[0][-1], v[6][-1]
        self.assertAlmostEqual(v[3][-1], (f0 + f100) / 2)
        self.assertAlmostEqual(v[4][-1], f0 - (f0 - f100) * .618)
        b = self.b
        self.assertIn(round(f100, 9), {round(b['high'].iloc[dau], 9), round(b['low'].iloc[dau], 9)})   # mức 100% là đỉnh hoặc đáy ở đầu sóng
        self.assertGreaterEqual(abs(f0 - f100) / f100 * 100, .5)                   # sóng đủ độ đảo chiều tối thiểu

    def test_chuoi_rong_phang_khong_loi(self):
        js = VO + M.JS + r"""const e=[];for(const k of ['piv','mtf','afib','efi']){const d=CBCN.LIB[k],p=Object.fromEntries(d.ts.map(t=>[t[0],t[2]]));
 for(const n of [0,1,30,800])for(const g of [0,100]){const a=Array(n).fill(g),T=a.map((_,i)=>1767571200+i*900);
  for(const t of [T,undefined])try{for(const o of d.tinh(a,a,a,a,p,Array(n).fill(0),t))if(o[1].length!==n||o[1].some(x=>x!==null&&!Number.isFinite(x)))e.push(k+':'+n+':so')}catch(x){e.push(k+':'+n+':'+x.message)}}}
process.stdout.write(JSON.stringify(e))"""
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 't.js').write_text(js, encoding='utf-8')
            r = subprocess.run([NODE, str(Path(d) / 't.js')], capture_output=True, text=True, encoding='utf-8', timeout=60)  # noqa: S603
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        self.assertEqual(json.loads(r.stdout), [])


if __name__ == '__main__':
    unittest.main()
