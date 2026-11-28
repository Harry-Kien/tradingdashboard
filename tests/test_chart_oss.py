"""Run the vendored math, adapters and actual worker; independent numeric checks."""
import hashlib
import json
import unittest

import numpy as np
import pandas as pd

from so_cong_khai import bieu_do_chi_bao as chart
from so_cong_khai import chi_bao_nguon_mo as oss
from test_bieu_do_chi_bao import VO, _nen
from test_chart_pro import node


def library(code):
    return node(VO + chart.JS + code)


class OpenSourceIndicators(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = _nen(900)
        data = [cls.b[k].tolist() for k in ('high', 'low', 'close', 'open', 'vol')]
        cls.arrays = json.dumps(data)
        cls.output = library('const [H,L,C,O,V]=' + cls.arrays + ''';
const out={};for(const [k,d]of Object.entries(CBCN.LIB).filter(([k])=>k.startsWith('oss_'))){
const p=Object.fromEntries(d.ts.map(t=>[t[0],t[2]]));out[k]=d.tinh(H,L,C,O,p,V)}
console.log(JSON.stringify(out));''')

    def match(self, key, expected, warm, j=0, tol=1e-6):
        actual = np.array([np.nan if x is None else x for x in self.output['oss_' + key][j][1]])
        expected = np.array(expected, dtype=float)
        expected[:warm] = np.nan
        np.testing.assert_allclose(actual, expected, atol=tol, rtol=1e-8, equal_nan=True, err_msg=key)

    def test_formula_price_and_volatility_independent_pandas(self):
        b = self.b
        c, h, l, o = (b[k] for k in ('close', 'high', 'low', 'open'))
        self.match('trima', c.rolling(11).mean().rolling(10).mean(), 19)
        self.match('apo', c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean(), 25)
        self.match('qstick', (c-o).rolling(14).mean(), 13)
        self.match('slope', (c-c.shift(14))/14, 14)
        self.match('ibs', 100*(c-l)/(h-l), 0)
        mid, sd = c.rolling(20).mean(), c.rolling(20).std(ddof=0)
        self.match('percentb', 100*(c-(mid-2*sd))/(4*sd), 19)
        dd = 100*(c-c.rolling(14).max())/c.rolling(14).max()
        self.match('ui', np.sqrt((dd*dd).rolling(14).mean()), 26)
        factor = 1+4*(h-l)/(h+l)
        self.match('ab', (h*factor).rolling(20).mean(), 19, 0)
        self.match('ab', c.rolling(20).mean(), 19, 1)
        self.match('ab', (l*(2-factor)).rolling(20).mean(), 19, 2)

    def test_t3_sma_seed_and_trailing_regression(self):
        c = self.b['close'].to_numpy()
        emas = []
        current = c.copy()
        for _ in range(6):
            start = np.flatnonzero(np.isfinite(current))[0]
            result = np.full(len(c), np.nan)
            seed = start+4
            result[seed] = current[start:seed+1].mean()
            for i in range(seed+1, len(c)):
                result[i] = result[i-1]+(current[i]-result[i-1])/3
            emas.append(result)
            current = result
        a = .7
        t3 = -a**3*emas[5]+(3*a*a+3*a**3)*emas[4]+(-6*a*a-3*a-3*a**3)*emas[3]+(1+3*a+3*a*a+a**3)*emas[2]
        self.match('t3', t3, 24)
        forecast = pd.Series(c).rolling(14).apply(lambda x: np.polyval(np.polyfit(np.arange(14), x, 1), 13), raw=True)
        self.match('cfo', 100*(c-forecast)/c, 13)

    def test_volume_formulas_independent_pandas(self):
        b = self.b
        c, v, h, l = (b[k] for k in ('close', 'vol', 'high', 'low'))
        force = c.diff().fillna(0)*v
        self.match('force', force.ewm(span=13, adjust=False).mean(), 13)
        self.match('vpt', (v*c.pct_change().fillna(0)).cumsum(), 1)
        nvi = np.full(len(c), 1000.)
        for i in range(1, len(c)):
            nvi[i] = nvi[i-1]*(c.iloc[i]/c.iloc[i-1] if v.iloc[i]<v.iloc[i-1] else 1)
        self.match('nvi', nvi, 1)
        ad = (((2*c-h-l)/(h-l))*v).cumsum()
        self.match('chaikin', ad.ewm(span=3, adjust=False).mean()-ad.ewm(span=10, adjust=False).mean(), 9)
        pvo = 100*(v.ewm(span=12, adjust=False).mean()-v.ewm(span=26, adjust=False).mean())/v.ewm(span=26, adjust=False).mean()
        signal = pvo.ewm(span=9, adjust=False).mean()
        for j, expected in enumerate((pvo, signal, pvo-signal)):
            self.match('pvo', expected, 33, j)
        emv = ((h+l)/2).diff().fillna(0)*(h-l)*1e8/v
        self.match('emv', emv.rolling(14).mean(), 13, tol=.001)

    def test_registry_alignment_flat_empty_and_no_nonfinite(self):
        result = library('''
const keys=Object.keys(CBCN.LIB).filter(k=>k.startsWith('oss_')),errors=[];
for(const k of keys){const d=CBCN.LIB[k],p=Object.fromEntries(d.ts.map(t=>[t[0],t[2]]));
 for(const size of [0,1,30,800])for(const price of [0,100]){
 const a=Array(size).fill(price),v=Array(size).fill(0);
 try{const out=d.tinh(a,a,a,a,p,v);for(const o of out)if(o[1].length!==size||o[1].some(x=>x!==null&&!Number.isFinite(x)))errors.push(k+':values')}
 catch(e){errors.push(k+':'+size+':'+e.message)}}}
console.log(JSON.stringify({count:Object.keys(CBCN.LIB).length,added:keys.length,patterns:HGR_OSS.candlePatterns.length,errors}));''')
        self.assertEqual(result, {'count': 98, 'added': 19, 'patterns': 27, 'errors': []})   # 98 = 75 + 19 mã nguồn mở + 4 ngày 28/11 (piv, mtf, afib, efi)
        for key, output in self.output.items():
            for series in output:
                self.assertEqual(len(series[1]), 900, key)
                self.assertTrue(any(x is not None for x in series[1]), key)

    def test_future_append_does_not_rewrite_past(self):
        result = library('const [H,L,C,O,V]=' + self.arrays + ''';
const errors=[];for(const[k,d]of Object.entries(CBCN.LIB).filter(([k])=>k.startsWith('oss_'))){
const p=Object.fromEntries(d.ts.map(t=>[t[0],t[2]])),a=d.tinh(H,L,C,O,p,V),cut=760,b=d.tinh(H.slice(0,cut),L.slice(0,cut),C.slice(0,cut),O.slice(0,cut),p,V.slice(0,cut));
if(k==='oss_candles'){for(let j=0;j<2;j++)if(JSON.stringify(a[j][3].filter(m=>m.i<cut-1&&m.i>=400))!==JSON.stringify(b[j][3].filter(m=>m.i>=400)))errors.push(k)}
else a.forEach((o,j)=>{if(o[1].slice(0,cut).some((v,i)=>v!==b[j][1][i]&&Math.abs(v-b[j][1][i])>1e-8))errors.push(k)})}
console.log(JSON.stringify(errors));''')
        self.assertEqual(result, [])

    def test_missing_volume_is_blank_and_gap_restarts_state(self):
        result = library('''
const C=Array.from({length:100},(_,i)=>100+Math.sin(i)),H=C.map(v=>v+1),L=C.map(v=>v-1),V=C.map((v,i)=>i===40?null:100+i),errors=[];
for(const k of ['force','emv','chaikin','pvo','vpt','nvi']){const d=CBCN.LIB['oss_'+k],p=Object.fromEntries(d.ts.map(t=>[t[0],t[2]]));
const blank=d.tinh(H,L,C,C,p),gap=d.tinh(H,L,C,C,p,V),tail=d.tinh(H.slice(41),L.slice(41),C.slice(41),C.slice(41),p,V.slice(41));
if(blank.some(o=>o[1].some(v=>v!==null)))errors.push(k+':missing');
gap.forEach((o,j)=>{if(o[1][40]!==null||JSON.stringify(o[1].slice(41))!==JSON.stringify(tail[j][1]))errors.push(k+':gap')})}
console.log(JSON.stringify(errors));''')
        self.assertEqual(result, [])

    def test_candle_first_window_confirmation_and_labels(self):
        result = library('''
const d=CBCN.LIB.oss_candles,H=[25.10,30.87,31],L=[20.82,14.93,27],O=[23.25,15.36,28],C=[21.44,27.89,29];
const run=(size,p)=>d.tinh(H.slice(0,size),L.slice(0,size),C.slice(0,size),O.slice(0,size),p)[0][3];
console.log(JSON.stringify({live:run(2,{c:0,l:1}),pending:run(2,{}),confirmed:run(3,{}),invalid:d.tinh([1,2],[4,5],C.slice(0,2),O.slice(0,2),{c:0})[0][3]}));''')
        self.assertTrue(any(m['i'] == 1 and 'Bullish Engulfing' in m['text'] for m in result['live']))
        self.assertFalse(any(m['i'] == 1 for m in result['pending']))
        confirmed = next(m for m in result['confirmed'] if m['i'] == 1)
        self.assertEqual(confirmed['text'], '')
        self.assertIn('Bullish Engulfing', confirmed['patterns'])
        self.assertEqual(result['invalid'], [])

    @unittest.skipUnless(hasattr(chart, 'WORKER_JS'), 'Shared legacy chart has no worker')
    def test_actual_worker_full_tail_and_pattern_confirmation(self):
        result = library('const [H,L,C,O,V]=' + self.arrays + ''';
const cs=C.map((v,i)=>[100000+i*60,O[i],H[i],L[i],v]),vol=Object.fromEntries(cs.map((r,i)=>[r[0],V[i]])),
specs=Object.entries(CBCN.LIB).filter(([k])=>k.startsWith('oss_')).map(([k,d])=>({id:k,k,p:Object.fromEntries(d.ts.map(t=>[t[0],t[2]]))}));
let message;globalThis.self={postMessage:x=>message=x};
''' + chart.WORKER_JS + '''
const errors=[];for(const from of [0,898]){self.onmessage({data:{id:1,cs,vol,specs,from}});
for(const x of specs){const expected=CBCN.LIB[x.k].tinh(H,L,C,O,x.p,V),actual=message.items.find(v=>v.id===x.id);
if(actual.error){errors.push(x.k+':error');continue}
expected.forEach((o,j)=>{if(JSON.stringify(o[1].slice(from))!==JSON.stringify(actual.out[j].values)||JSON.stringify((o[3]||[]).slice(-300))!==JSON.stringify(actual.out[j].markers||[]))errors.push(x.k+':mismatch')})}}
console.log(JSON.stringify(errors));''')
        self.assertEqual(result, [])

    def test_vendored_files_and_built_hash_keep_licenses(self):
        root = oss.THU_MUC
        manifest = json.loads((root/'PROVENANCE.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((root/'indicators.js').read_bytes()).hexdigest(), manifest['bundle_sha256'])
        for path, digest in manifest['source_sha256'].items():
            self.assertEqual(hashlib.sha256((root/'source'/path).read_bytes()).hexdigest(), digest, path)
        for repo in ('indicatorts', 'technicalindicators'):
            self.assertIn((root/(repo+'-LICENSE.txt')).read_text(encoding='utf-8'), oss.BUNDLE)
        self.assertNotIn('</script', oss.BUNDLE.lower())

    def test_pattern_renderer_keeps_price_axis_clean_and_ai_gets_names(self):
        result = node(VO + '''
const series=[],markers=[],bars=[[1,23.25,25.10,20.82,21.44],[2,15.36,30.87,14.93,27.89],[3,28,31,27,29]];
const chart={panes:()=>[{getSeries:()=>series}],removeSeries(){},addSeries(kind,options){const s={options,data:[],setData(a){this.data=a},update(){},applyOptions(){},createPriceLine(){}};series.push(s);return s}};
document.documentElement={lang:'vi'};
const D={candles:bars,vol:{},live:3},LW={chart,khDao:'',nen:{options:()=>({upColor:'green',downColor:'red'}),applyOptions(){},attachPrimitive(){}}};
window.BDCB=()=>({LW,D});window.LightweightCharts={LineSeries:'line',createSeriesMarkers:(s)=>({setMarkers(a){markers.push(a)}})};
localStorage.getItem=k=>k==='so-cbcn1'?JSON.stringify({ds:[{id:'p',k:'oss_candles',p:{l:1},mau:'#0f0'}]}):null;
''' + chart.JS + '''
CBCN.ve();const ai=CBCN.tomTat().chi_bao[0];
console.log(JSON.stringify({options:series.map(s=>s.options),markers,ai}));''')
        for options in result['options']:
            self.assertFalse(options['lineVisible'])
            self.assertFalse(options['lastValueVisible'])
            self.assertFalse(options['crosshairMarkerVisible'])
        self.assertTrue(any('Bullish Engulfing' in m.get('text', '') for group in result['markers'] for m in group))
        self.assertEqual(result['ai']['gia_tri'], {})
        self.assertTrue(any('Bullish Engulfing' in m.get('mau', []) for m in result['ai']['dau']))

    def test_parameter_form_and_change_handler_apply_declared_limits(self):
        start = chart.JS.index("NEN.addEventListener('change'")
        end = chart.JS.index("TIM.addEventListener", start)
        result = library('''
let change;const NEN={addEventListener:(name,fn)=>change=fn},LIB=CBCN.LIB,S={ds:[]},luu=()=>{},doi=()=>{};
''' + chart.JS[start:end] + '''
const cases=[['oss_t3','a',2,1],['oss_t3','a',0,0],['oss_candles','c',5,1],['oss_candles','l',0,0],['oss_ab','k',40,20],['oss_nvi','b',5000,5000],['oss_cfo','n',1,14]],errors=[];
for(const[k,key,value,expected]of cases){S.ds=[{id:'a',k,p:Object.fromEntries(LIB[k].ts.map(t=>[t[0],t[2]]))}];
const target={value:String(value),dataset:{ts:key},hasAttribute:()=>false,closest:()=>({dataset:{id:'a'}})};
change({target});if(S.ds[0].p[key]!==expected||+target.value!==expected)errors.push(k+':'+key)}
console.log(JSON.stringify(errors));''')
        self.assertEqual(result, [])
        self.assertIn('max="${mx??1000}"', chart.JS)


if __name__ == '__main__':
    unittest.main()
