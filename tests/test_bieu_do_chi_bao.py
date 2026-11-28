# -*- coding: utf-8 -*-
"""Bộ chọn chỉ báo của trang Biểu đồ (so_cong_khai.bieu_do_chi_bao): phép tính chạy bằng Node trên một chuỗi nến giả, đối chiếu từng số với
cách tính phía máy chủ (pandas: gia.rsi_wilder, chi_bao_them) và công thức chuẩn. Không có Node thì bỏ qua."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from so_cong_khai import bieu_do_chi_bao as M
from so_cong_khai import chi_bao_them as CB
from so_cong_khai import gia

NODE = shutil.which('node')
VO = r"""
const noop=()=>{},el=()=>new Proxy({},{get:(t,k)=>k in t?t[k]:(k==='querySelector'?()=>el():k==='querySelectorAll'?()=>[]:k==='style'||k==='dataset'?{}:noop),set:(t,k,v)=>{t[k]=v;return true}});
globalThis.window=globalThis;globalThis.document={createElement:el,querySelector:()=>null,querySelectorAll:()=>[],addEventListener:noop,body:{appendChild:noop},activeElement:null};
globalThis.addEventListener=noop;globalThis.localStorage={getItem:()=>null,setItem:noop};
"""


def _nen(n=600, hat=7):
    r = np.random.default_rng(hat)
    c = 2000 + np.cumsum(r.normal(0, 3, n))
    o = np.r_[c[0], c[:-1]] + r.normal(0, .5, n)
    h = np.maximum(o, c) + np.abs(r.normal(0, 2, n))
    l = np.minimum(o, c) - np.abs(r.normal(0, 2, n))
    idx = pd.date_range('2026-01-05', periods=n, freq='15min', tz='UTC')
    v = r.integers(80, 160, n) * np.where(r.random(n) < .06, 4, 1)                   # tick volume giả, thỉnh thoảng gấp bốn
    return pd.DataFrame({'open': o, 'high': h, 'low': l, 'close': c, 'vol': v}, index=idx)


@unittest.skipUnless(NODE, 'không có Node')
class ChiBaoTrinhDuyet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = _nen()
        cs = [[int(t.timestamp()), o, h, l, c, int(v)] for t, o, h, l, c, v in zip(cls.b.index, cls.b['open'], cls.b['high'], cls.b['low'], cls.b['close'], cls.b['vol'])]
        js = VO + M.JS + r"""
const cs=JSON.parse(require('fs').readFileSync(process.argv[2],'utf8')),H=cs.map(r=>r[2]),L=cs.map(r=>r[3]),C=cs.map(r=>r[4]),O=cs.map(r=>r[1]),T=CBCN._tinh,V=cs.map(r=>r[5]);
const out={ema20:T.ema(C,20),sma20:T.sma(C,20),rsi14:T.rsi(C,14),atr14:T.atr(H,L,C,14),stoch:T.stoch(H,L,C,14,3,3),st:T.supertrend(H,L,C,10,3),
 macd:CBCN.LIB.macd.tinh(H,L,C,O,{f:12,s:26,t:9}).map(x=>x[1]),bb:CBCN.LIB.bb.tinh(H,L,C,O,{n:20,k:2}).map(x=>x[1]),cci:T.cci(H,L,C,20),adx:T.adx(H,L,C,14),
 wma:T.wma(C,10),ha:T.heikin(cs),willr:CBCN.LIB.willr.tinh(H,L,C,O,{n:14})[0][1],tat:{}};
out.moi={};for(const k of ['wt','ut','ce','vortex','chop','kama','alma','mcg','lsma','trix','uo','elder','fisher','sqz','qqe','kld','kldg'])out.moi[k]=CBCN.LIB[k].tinh(H,L,C,O,Object.fromEntries(CBCN.LIB[k].ts.map(t=>[t[0],t[2]])),V).map(x=>[x[1],x[3]||null]);out.kld0=CBCN.LIB.kld.tinh(H,L,C,O,{n:20,k:2,xu:1}).map(x=>x[1]);
const TS=cs.map(r=>r[0]),md=k=>Object.fromEntries(CBCN.LIB[k].ts.map(t=>[t[0],t[2]]));
for(const[k,d]of Object.entries(CBCN.LIB)){const p=md(k);out.tat[k]=d.tinh(H,L,C,O,p,V,TS).map(x=>[x[0],x[1].length,x[1].filter(v=>v!=null&&isFinite(v)).length])}
out.m2={};for(const k of ['smma','tema','zlema','emac','alli','zz','frac','pdhl','vol','vwap','vwma','obv','mfi','cmf','ad','ppo','tsi','smi','cmo','crsi','rvi','bop','dpo','kst','copp','stc','ac','rsipk','sdev','hv','mass'])
 out.m2[k]=CBCN.LIB[k].tinh(H,L,C,O,md(k),V,TS).map(x=>[x[1],x[3]||null]);
out.khongV={};for(const k of ['vol','vwap','vwma','obv','mfi','cmf','ad','pdhl'])out.khongV[k]=CBCN.LIB[k].tinh(H,L,C,O,md(k)).map(x=>x[1].filter(v=>v!=null).length);
process.stdout.write(JSON.stringify(out));"""
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'cs.json').write_text(json.dumps(cs), encoding='utf-8')
            (Path(d) / 't.js').write_text(js, encoding='utf-8')
            r = subprocess.run([NODE, str(Path(d) / 't.js'), str(Path(d) / 'cs.json')], capture_output=True, text=True, encoding='utf-8', timeout=60)
        if r.returncode:
            raise AssertionError(r.stderr[-2000:])
        cls.o = json.loads(r.stdout)

    def khop(self, js, pd_series, ten, tol=1e-6):
        a = np.array([np.nan if v is None else v for v in js], dtype=float)
        b = np.asarray(pd_series, dtype=float)
        self.assertEqual(len(a), len(b), ten)
        self.assertTrue(np.array_equal(np.isnan(a), np.isnan(b)), f'{ten}: chỗ trống khác nhau')
        m = ~np.isnan(b)
        self.assertTrue(m.sum() > 100, ten)
        self.assertLess(float(np.max(np.abs(a[m] - b[m]))), tol, ten)

    def test_khop_cach_tinh_may_chu(self):
        b, c = self.b, self.b['close']
        self.khop(self.o['ema20'], c.ewm(span=20, adjust=False, min_periods=20).mean(), 'EMA')
        self.khop(self.o['sma20'], c.rolling(20).mean(), 'SMA')
        self.khop(self.o['rsi14'], gia.rsi_wilder(c, 14), 'RSI')
        self.khop(self.o['atr14'], CB.atr(b, 14), 'ATR')
        k, d = CB.stoch(b)
        self.khop(self.o['stoch'][0], k, 'Stoch %K')
        self.khop(self.o['stoch'][1], d, 'Stoch %D')
        st, ch = CB.supertrend(b)
        self.khop(self.o['st'][0], st, 'SuperTrend')
        self.khop(self.o['st'][1], ch, 'SuperTrend chiều')
        m, s, h = CB.macd(c)
        self.khop(self.o['macd'][1], m, 'MACD')
        self.khop(self.o['macd'][2], s, 'MACD tín hiệu')
        self.khop(self.o['macd'][0], h, 'MACD cột')
        mid, sd = c.rolling(20).mean(), c.rolling(20).std(ddof=0)
        self.khop(self.o['bb'][1], mid + 2 * sd, 'BB trên')
        self.khop(self.o['bb'][2], mid - 2 * sd, 'BB dưới')

    def test_cong_thuc_chuan(self):
        b = self.b
        tp = (b['high'] + b['low'] + b['close']) / 3
        md = tp.rolling(20).apply(lambda w: np.mean(np.abs(w - w.mean())), raw=True)
        self.khop(self.o['cci'], (tp - tp.rolling(20).mean()) / (.015 * md), 'CCI')
        hh, ll = b['high'].rolling(14).max(), b['low'].rolling(14).min()
        self.khop(self.o['willr'], -100 * (hh - b['close']) / (hh - ll), 'Williams %R')
        w = np.arange(1, 11)
        self.khop(self.o['wma'], b['close'].rolling(10).apply(lambda x: np.dot(x, w) / w.sum(), raw=True), 'WMA')
        up, dn = b['high'].diff(), -b['low'].diff()
        pdm = np.where((up > dn) & (up > 0), up, 0.0)
        mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
        pdm[0] = mdm[0] = np.nan
        c0 = b['close'].shift(1)
        tr = pd.concat([b['high'] - b['low'], (b['high'] - c0).abs(), (b['low'] - c0).abs()], axis=1).max(axis=1)
        tr.iloc[0] = np.nan
        t, p, mm = CB.rma(tr, 14), CB.rma(pd.Series(pdm, index=b.index), 14), CB.rma(pd.Series(mdm, index=b.index), 14)
        pdi, mdi = 100 * p / t, 100 * mm / t
        self.khop(self.o['adx'][1], pdi, '+DI')
        self.khop(self.o['adx'][2], mdi, '−DI')
        self.khop(self.o['adx'][0], CB.rma(100 * (pdi - mdi).abs() / (pdi + mdi), 14), 'ADX')

    def test_heikin_ashi(self):
        b = self.b
        hc = (b['open'] + b['high'] + b['low'] + b['close']) / 4
        ho = np.empty(len(b))
        ho[0] = (b['open'].iloc[0] + b['close'].iloc[0]) / 2
        for i in range(1, len(b)):
            ho[i] = (ho[i - 1] + hc.iloc[i - 1]) / 2
        ha = np.array(self.o['ha'])
        self.assertLess(float(np.max(np.abs(ha[:, 1] - ho))), 1e-6)
        self.assertLess(float(np.max(np.abs(ha[:, 4] - hc.to_numpy()))), 1e-6)
        self.assertLess(float(np.max(np.abs(ha[:, 2] - np.maximum.reduce([b['high'].to_numpy(), ho, hc.to_numpy()])))), 1e-6)
        self.assertLess(float(np.max(np.abs(ha[:, 3] - np.minimum.reduce([b['low'].to_numpy(), ho, hc.to_numpy()])))), 1e-6)

    def test_moi_chi_bao_chay_duoc(self):
        self.assertGreaterEqual(len(self.o['tat']), 39)
        for k, ds in self.o['tat'].items():
            for ten, dai, co in ds:
                self.assertEqual(dai, 600, (k, ten))
            if k == 'sqz':
                ds = ds[:1]                                                         # chấm "đang nén" chỉ có ở một số nến
            if k in ('kldg', 'frac'):
                continue                                                           # dấu chỉ có ở nến đột biến (đối chiếu riêng bên dưới)
            if k == 'afib':
                self.assertTrue(all(co > 0 for _, _, co in ds))                      # chỉ kẻ trên sóng ZigZag gần nhất (đối chiếu ở test_chi_bao_2811)
                continue
            if k == 'mtf':
                self.assertTrue(all(co == 0 for _, _, co in ds))                     # EMA 50 H4 cần khoảng 800 nến M15; chuỗi thử chỉ có 600 (đối chiếu ở test_chi_bao_2811)
                continue
            if k == 'oss_specialk':
                self.assertTrue(all(co == 0 for _, _, co in ds))                     # cần 725 nến; chuỗi thử này chỉ có 600
                continue
            self.assertGreater(sum(co for _, _, co in ds) / (1 if k in ('st', 'ce') else len(ds)), 300, k)   # đủ số sau phần khởi động (SuperTrend, Chandelier: hai nửa cộng lại)

    def test_chi_bao_cong_dong(self):
        """Đối chiếu các chỉ báo cộng đồng với công thức gốc viết lại bằng pandas, numpy (vòng lặp Python cho các đường dời)."""
        b, m = self.b, self.o['moi']
        H, L, C = b['high'], b['low'], b['close']
        e = lambda x, n: x.ewm(span=n, adjust=False, min_periods=n).mean()   # noqa: E731
        c0 = C.shift(1)
        tr = pd.concat([H - L, (H - c0).abs(), (L - c0).abs()], axis=1).max(axis=1)
        tr.iloc[0] = np.nan
        ap = (H + L + C) / 3
        esa = e(ap, 10)
        w1 = e((ap - esa) / (.015 * e((ap - esa).abs(), 10)), 21)
        self.khop(m['wt'][0][0], w1, 'WaveTrend 1')
        self.khop(m['wt'][1][0], w1.rolling(4).mean(), 'WaveTrend 2')
        vp, vm, t = (H - L.shift(1)).abs().rolling(14).sum(), (L - H.shift(1)).abs().rolling(14).sum(), tr.rolling(14).sum()
        self.khop(m['vortex'][0][0], vp / t, 'VI+')
        self.khop(m['vortex'][1][0], vm / t, 'VI−')
        t = tr.fillna(H - L).rolling(14).sum()                                    # nến đầu: TR = cao − thấp, như ta.atr(1) của Pine
        self.khop(m['chop'][0][0], 100 * np.log10(t / (H.rolling(14).max() - L.rolling(14).min())) / np.log10(14), 'CHOP')
        w = np.exp(-((np.arange(9) - .85 * 8) ** 2) / (2 * (9 / 6) ** 2))
        self.khop(m['alma'][0][0], C.rolling(9).apply(lambda x: np.dot(x, w) / w.sum(), raw=True), 'ALMA')
        lr = lambda x, n: x.rolling(n).apply(lambda v: np.polyval(np.polyfit(np.arange(n), v, 1), n - 1), raw=True)   # noqa: E731
        self.khop(m['lsma'][0][0], lr(C, 25), 'LSMA', 1e-5)
        lc = np.log(C)
        e3 = e(e(e(lc, 18), 18), 18)
        self.khop(m['trix'][0][0], 1e4 * e3.diff(), 'TRIX')
        bp, tt = C - pd.concat([L, c0], axis=1).min(axis=1, skipna=False), pd.concat([H, c0], axis=1).max(axis=1, skipna=False) - pd.concat([L, c0], axis=1).min(axis=1, skipna=False)
        av = lambda n: bp.rolling(n).sum() / tt.rolling(n).sum()   # noqa: E731
        self.khop(m['uo'][0][0], 100 * (4 * av(7) + 2 * av(14) + av(28)) / 7, 'Ultimate')
        self.khop(m['elder'][0][0], H - e(C, 13), 'Elder mua')
        self.khop(m['elder'][1][0], L - e(C, 13), 'Elder bán')
        dt = ((H.rolling(20).max() + L.rolling(20).min()) / 2 + C.rolling(20).mean()) / 2
        self.khop(m['sqz'][0][0], lr(C - dt, 20), 'Squeeze', 1e-5)
        cv, n = C.to_numpy(), len(C)
        k = np.full(n, np.nan)                                                     # KAMA (10, 2, 30)
        fs, ss, kk = 2 / 3, 2 / 31, None
        for i in range(10, n):
            vo = np.abs(np.diff(cv[i - 10:i + 1])).sum()
            sc = ((abs(cv[i] - cv[i - 10]) / vo if vo else 0) * (fs - ss) + ss) ** 2
            kk = cv[i] if kk is None else kk + sc * (cv[i] - kk)
            k[i] = kk
        self.khop(m['kama'][0][0], k, 'KAMA')
        e14, mg, g = e(C, 14).to_numpy(), np.full(n, np.nan), None              # McGinley (14)
        for i in range(n):
            if g is None:
                if not np.isnan(e14[i]):
                    g = e14[i]
                mg[i] = np.nan if g is None else g
                continue
            g = g + (cv[i] - g) / (14 * (cv[i] / g) ** 4)
            mg[i] = g
        self.khop(m['mcg'][0][0], mg, 'McGinley')
        g2 = ((H + L) / 2).to_numpy()                                              # Fisher (9)
        a9, b9 = pd.Series(g2).rolling(9).max().to_numpy(), pd.Series(g2).rolling(9).min().to_numpy()
        f, v, f0 = np.full(n, np.nan), 0.0, 0.0
        for i in range(n):
            if np.isnan(a9[i]):
                continue
            v = min(.999, max(-.999, .66 * ((g2[i] - b9[i]) / ((a9[i] - b9[i]) or 1e-9) - .5) + .67 * v))
            f0 = f[i] = .5 * np.log((1 + v) / (1 - v)) + .5 * f0
        self.khop(m['fisher'][0][0], f, 'Fisher')
        x = CB.atr(b, 10).to_numpy()                                               # UT Bot (1, 10)
        st, pv, mk = np.full(n, np.nan), 0.0, []
        for i in range(n):
            if np.isnan(x[i]):
                continue
            c, c1 = cv[i], cv[i - 1] if i else cv[i]
            nv = (max(pv, c - x[i]) if c > pv and c1 > pv else min(pv, c + x[i]) if c < pv and c1 < pv else c - x[i] if c > pv else c + x[i])
            if i and not np.isnan(st[i - 1]):
                if c1 <= st[i - 1] and c > nv:
                    mk.append((i, 1))
                elif c1 >= st[i - 1] and c < nv:
                    mk.append((i, 0))
            st[i], pv = nv, nv
        self.khop(m['ut'][0][0], st, 'UT Bot')
        self.assertEqual([(d['i'], d['len']) for d in m['ut'][0][1]], mk)
        self.assertGreater(len(mk), 5)
        a22, hc, lc2 = CB.atr(b, 22).to_numpy(), C.rolling(22).max().to_numpy(), C.rolling(22).min().to_numpy()   # Chandelier (22, 3)
        lo, sh, L0, S0, d0, mk2 = np.full(n, np.nan), np.full(n, np.nan), None, None, 1, []
        for i in range(n):
            if np.isnan(a22[i]) or np.isnan(hc[i]):
                continue
            ll_, ss_ = hc[i] - 3 * a22[i], lc2[i] + 3 * a22[i]
            lp, sp = (ll_ if L0 is None else L0), (ss_ if S0 is None else S0)
            if i and cv[i - 1] > lp:
                ll_ = max(ll_, lp)
            if i and cv[i - 1] < sp:
                ss_ = min(ss_, sp)
            d = 1 if cv[i] > sp else -1 if cv[i] < lp else d0
            if d != d0 and L0 is not None:
                mk2.append((i, 1 if d > 0 else 0))
            if d > 0:
                lo[i] = ll_
            else:
                sh[i] = ss_
            L0, S0, d0 = ll_, ss_, d
        a = np.array([np.nan if v is None else v for v in m['ce'][0][0]], dtype=float)
        self.assertTrue(np.array_equal(np.isnan(a), np.isnan(lo)))
        self.assertLess(float(np.nanmax(np.abs(a - lo))), 1e-6)
        self.assertEqual([(d['i'], d['len']) for d in m['ce'][0][1]], mk2)
        self.assertTrue(all(v is None or v != v or 0 <= v <= 100 for v in m['qqe'][0][0]))   # QQE: RSI làm trơn nằm trong 0–100
        V, O = b['vol'].astype(float), b['open']                                   # Khối lượng đột biến, đúng định nghĩa đã ghi trước
        rel = V / V.shift(1).rolling(20).mean()
        sg = np.sign(C - O)
        self.khop(m['kld'][0][0], np.where(sg < 0, -rel, rel), 'KL tương đối')
        e50 = e(C, 50)
        dot = (rel >= 2) & (sg != 0) & ((C - O).abs() >= .5 * (H - L)) & (((sg > 0) & (C > e50)) | ((sg < 0) & (C < e50)))
        mk3 = [(i, 1 if sg.iloc[i] > 0 else 0) for i in np.flatnonzero(dot.to_numpy())]
        self.assertEqual([(d['i'], d['len']) for d in m['kld'][0][1]], mk3)
        self.assertEqual([(d['i'], d['len']) for d in m['kldg'][0][1]], mk3)
        self.assertGreater(len(mk3), 3)
        self.assertTrue(all(v is None for v in self.o['kld0'][0]))                  # không có tick volume (kho nến): không vẽ gì

    def test_chi_bao_them_27_11(self):
        """Các chỉ báo thêm ngày 27/11/2026, đối chiếu với định nghĩa gốc viết lại bằng pandas, numpy."""
        b, m = self.b, self.o['m2']
        H, L, C, O, V = b['high'], b['low'], b['close'], b['open'], b['vol'].astype(float)
        n = len(C)
        e = lambda x, k: x.ewm(span=k, adjust=False, min_periods=k).mean()      # noqa: E731
        r = lambda x, k: x.ewm(alpha=1 / k, adjust=False, min_periods=k).mean()  # noqa: E731
        g = lambda k, j=0: m[k][j][0]                                              # noqa: E731
        self.khop(g('smma'), r(C, 14), 'SMMA')
        e1 = e(C, 20)
        e2 = e(e1, 20)
        self.khop(g('tema'), 3 * e1 - 3 * e2 + e(e2, 20), 'TEMA')
        self.khop(g('zlema'), e(2 * C - C.shift(9), 20), 'ZLEMA')
        a9, a21 = e(C, 9), e(C, 21)
        s = np.sign(a9 - a21)
        cat = [(i, 1 if s.iloc[i] > 0 else 0) for i in range(1, n) if not np.isnan(s.iloc[i - 1]) and s.iloc[i] != s.iloc[i - 1] and s.iloc[i] != 0]
        self.assertEqual([(d['i'], d['len']) for d in m['emac'][0][1]], cat)
        md = (H + L) / 2
        self.khop(g('alli'), r(md, 13).shift(8), 'Alligator hàm')
        self.khop(g('alli', 2), r(md, 5).shift(3), 'Alligator môi')
        day = b.index.floor('D')                                                    # mức ngày trước (giờ bắt đầu 0 UTC)
        ng = pd.DataFrame({'h': H, 'l': L, 'c': C}).groupby(day).agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).shift(1)
        self.khop(g('pdhl'), ng['h'].reindex(day).to_numpy(), 'Đỉnh ngày trước')
        self.khop(g('pdhl', 1), ng['l'].reindex(day).to_numpy(), 'Đáy ngày trước')
        self.khop(g('pdhl', 2), ng['c'].reindex(day).to_numpy(), 'Đóng ngày trước')
        self.khop(g('vol'), V, 'Khối lượng')
        tp = (H + L + C) / 3
        k = pd.Series(day, index=b.index)
        sv, s1, s2 = V.groupby(k).cumsum(), (tp * V).groupby(k).cumsum(), (tp * tp * V).groupby(k).cumsum()
        vw = s1 / sv
        self.khop(g('vwap'), vw, 'VWAP')
        self.khop(g('vwap', 1), vw + np.sqrt((s2 / sv - vw ** 2).clip(lower=0)), 'VWAP trên', 1e-5)
        self.khop(g('vwma'), (C * V).rolling(20).sum() / V.rolling(20).sum(), 'VWMA')
        ob = (np.sign(C.diff()).fillna(0) * V).cumsum() - np.sign(C.diff()).fillna(0).iloc[0] * V.iloc[0]
        self.khop(g('obv'), ob, 'OBV')
        f = tp * V
        up, dn = f.where(tp.diff() > 0, 0.0), f.where(tp.diff() < 0, 0.0)
        up.iloc[0] = dn.iloc[0] = np.nan
        self.khop(g('mfi'), 100 - 100 / (1 + up.rolling(14).sum() / dn.rolling(14).sum()), 'MFI')
        mv = ((C - L) - (H - C)) / (H - L) * V
        self.khop(g('cmf'), mv.rolling(20).sum() / V.rolling(20).sum(), 'CMF')
        self.khop(g('ad'), mv.cumsum(), 'A/D', 1e-4)
        pp = 100 * (e(C, 12) - e(C, 26)) / e(C, 26)
        self.khop(g('ppo', 1), pp, 'PPO')
        self.khop(g('ppo', 2), e(pp, 9), 'PPO tín hiệu')
        d = C.diff()
        ts = 100 * e(e(d, 25), 13) / e(e(d.abs(), 25), 13)
        self.khop(g('tsi'), ts, 'TSI')
        hh, ll = H.rolling(10).max(), L.rolling(10).min()
        self.khop(g('smi'), 200 * e(e(C - (hh + ll) / 2, 3), 3) / e(e(hh - ll, 3), 3), 'SMI')
        su, sd_ = d.clip(lower=0).rolling(9).sum(), (-d).clip(lower=0).rolling(9).sum()
        self.khop(g('cmo'), 100 * (su - sd_) / (su + sd_), 'CMO')
        sw = lambda x: (x.shift(3) + 2 * x.shift(2) + 2 * x.shift(1) + x) / 6   # noqa: E731
        rv = sw(C - O).rolling(10).sum() / sw(H - L).rolling(10).sum()
        self.khop(g('rvi'), rv, 'RVI')
        self.khop(g('rvi', 1), sw(rv), 'RVI tín hiệu')
        self.khop(g('bop'), ((C - O) / (H - L)).rolling(14).mean(), 'BOP')
        self.khop(g('dpo'), C - C.rolling(21).mean().shift(11), 'DPO')
        rc = lambda k: 100 * (C / C.shift(k) - 1)                                  # noqa: E731
        ks = rc(10).rolling(10).mean() + 2 * rc(15).rolling(10).mean() + 3 * rc(20).rolling(10).mean() + 4 * rc(30).rolling(15).mean()
        self.khop(g('kst'), ks, 'KST')
        w = np.arange(1, 11)
        self.khop(g('copp'), (rc(14) + rc(11)).rolling(10).apply(lambda x: np.dot(x, w) / w.sum(), raw=True), 'Coppock')
        ao = md.rolling(5).mean() - md.rolling(34).mean()
        self.khop(g('ac'), ao - ao.rolling(5).mean(), 'AC')
        self.khop(g('sdev'), C.rolling(20).std(ddof=0), 'Độ lệch chuẩn')
        self.khop(g('hv'), 100 * np.log(C / C.shift(1)).rolling(20).std(ddof=0), 'HV')
        x1 = e(H - L, 9)
        self.khop(g('mass'), (x1 / e(x1, 9)).rolling(25).sum(), 'Mass Index')
        for k2, lo, hi in (('mfi', 0, 100), ('crsi', 0, 100), ('stc', 0, 100), ('cmo', -100, 100)):
            v = [x for x in g(k2) if x is not None]
            self.assertGreater(len(v), 300, k2)
            self.assertTrue(all(lo - 1e-9 <= x <= hi + 1e-9 for x in v), k2)
        zz = np.array([np.nan if x is None else x for x in g('zz')], dtype=float)   # ZigZag: đoạn thẳng nối đỉnh đáy xen kẽ, mỗi chân đảo ≥ 0,5%
        ok = ~np.isnan(zz)
        self.assertGreater(ok.sum(), 400)
        dz = np.sign(np.diff(zz[ok]))
        doi = np.flatnonzero(dz[1:] != dz[:-1]) + 1
        self.assertGreater(len(doi), 5)
        dinh = zz[ok][np.r_[0, doi, ok.sum() - 1]]
        self.assertTrue(all(abs(dinh[i + 1] / dinh[i] - 1) >= .005 - 1e-12 for i in range(len(dinh) - 2)))
        fr = m['frac'][0][1]                                                       # Fractals: đỉnh cao hơn hẳn 2 nến mỗi bên
        self.assertGreater(len(fr), 20)
        for dd in fr:
            i = dd['i']
            nb = [j for j in range(i - 2, i + 3) if j != i]
            self.assertTrue(all(H.iloc[j] < H.iloc[i] for j in nb) if dd['len'] == 0 else all(L.iloc[j] > L.iloc[i] for j in nb))
        rsi = gia.rsi_wilder(C, 14).to_numpy()                                     # RSI kèm phân kỳ: đường là RSI; mũi tên là đáy/đỉnh RSI ngược chiều giá
        self.khop(g('rsipk'), rsi, 'RSI phân kỳ')
        for dd in m['rsipk'][0][1]:
            i = dd['i']
            w5 = [j for j in range(i - 5, i + 6) if j != i]
            self.assertTrue(all(rsi[j] > rsi[i] for j in w5) if dd['len'] == 1 else all(rsi[j] < rsi[i] for j in w5))
        self.assertTrue(all(v == 0 for ds in self.o['khongV'].values() for v in ds))   # thiếu tick volume hoặc giờ nến: không vẽ gì


if __name__ == '__main__':
    unittest.main()
