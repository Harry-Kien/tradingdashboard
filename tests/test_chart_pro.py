"""Chạy mã thật: chặn khách sửa hình, tail update, tick cũ và công thức mới."""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from so_cong_khai import bieu_do, bieu_do_chi_bao, bieu_do_menu, chart_luu_giao_dien, chart_realtime
from test_bieu_do_chi_bao import VO


def node(js):
    exe = shutil.which('node')
    if not exe:
        raise unittest.SkipTest('Cần Node')
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / 'test.js'
        p.write_text('globalThis.window=globalThis;\n' + js, encoding='utf-8')
        r = subprocess.run([exe, str(p)], capture_output=True, encoding='utf-8', text=True, timeout=30)  # noqa: S603
    if r.returncode:
        raise AssertionError(r.stderr[-3000:])
    return json.loads(r.stdout)


def function(name):
    return re.search(r'function ' + name + r'\(.*?\}\n', bieu_do.JS).group()


class LoginGate(unittest.TestCase):
    def test_khach_phai_dang_nhap_tai_khoan_duoc_ve(self):
        for user, expected in ((None, False), ({'id': 'a', 'ten': 'alpha'}, True)):
            r = node(chart_luu_giao_dien.boot(user) + """
let asked=0;window.HVD_UI={account:()=>asked++};
console.log(JSON.stringify({ok:HVD_CHO_VE(),asked}));
""")
            self.assertEqual(r, {'ok': expected, 'asked': int(not expected)})

    def test_thiet_lap_chi_bao_tach_theo_tai_khoan_khong_nhan_nham_cu(self):
        script = """
const ls={'so-cbcn1':'{"sao":["ema"]}'},localStorage={getItem:k=>ls[k]??null,setItem:(k,v)=>ls[k]=v};
"""
        owner = {'id': 'a', 'ten': 'a', 'chu': True}
        other = {'id': 'b', 'ten': 'b', 'chu': False}
        r = node(script + chart_luu_giao_dien.boot(owner) + chart_luu_giao_dien.boot(other) + "console.log(JSON.stringify({key:HVD_CB_KEY,ls}));")
        self.assertEqual(r['key'], 'so-cbcn1:u_b')
        self.assertIn('so-cbcn1:u_a', r['ls'])
        self.assertNotIn('so-cbcn1:u_b', r['ls'])

    def test_chon_cong_cu_hoan_tac_xoa_khong_doi_hinh_khach(self):
        r = node(chart_luu_giao_dien.boot() + """
let asked=0,saved=0;window.HVD_UI={account:()=>asked++};
const VE={ds:[{id:'a'}],chon:'a',cong:'tro',cu:['[]'],lai:['[]']};
const veLuu=()=>saved++,veTb=()=>{},lwPhu=()=>{};
""" + ''.join(function(k) for k in ('veDuoc', 'veHoan', 'veLam', 'veXoa', 'veCong')) + """
veCong('xu');veHoan();veLam();veXoa();console.log(JSON.stringify({VE,asked,saved}));
""")
        self.assertEqual(r['saved'], 0)
        self.assertEqual(r['asked'], 4)
        self.assertEqual(r['VE']['ds'], [{'id': 'a'}])
        self.assertEqual(r['VE']['cong'], 'tro')

    def test_menu_chuot_phai_khong_lach_dang_nhap(self):
        a = bieu_do_menu.JS.index('function lamBieuDo(')
        b = bieu_do_menu.JS.index('// --- menu khi', a)
        c = bieu_do_menu.JS.index('function lamHinh(')
        d = bieu_do_menu.JS.index('// --- sửa chữ', c)
        r = node("""
let asked=0;const g={VE:{ds:[{id:'a',k:'xu'}]},veDuoc:()=>{asked++;return false}},G=()=>g;
""" + bieu_do_menu.JS[a:b] + bieu_do_menu.JS[c:d] + """
for(const k of ['ve','vt','hienan','xoahet'])lamBieuDo(k,'ngang',{t:1,p:2},null);
for(const k of ['nban','khoa','suachu','mau','xoa'])lamHinh(k,'red','a');
console.log(JSON.stringify({ds:g.VE.ds,asked}));
""")
        self.assertEqual(r, {'ds': [{'id': 'a', 'k': 'xu'}], 'asked': 9})


SERIES = """
const calls=[],s={setData:a=>calls.push(['full',a]),update:x=>calls.push(['tail',x])};
const cs=Array.from({length:30000},(_,i)=>({time:i+1,value:i}));
const send=(source=cs,tail=true)=>CHART_RT.gui(s,source.length,i=>source[i],source,tail);
"""


class Realtime(unittest.TestCase):
    def test_chi_bao_that_tu_tick_thay_doi_high_low_volume_khong_doi_close(self):
        r = node(VO + """
const series=[],bars=Array.from({length:100},(_,i)=>[i+1,10,12,9,10]),vol=Object.fromEntries(bars.map(x=>[x[0],1]));
const make=()=>({data:[],full:0,tail:0,setData(a){this.data=a.map(x=>({...x}));this.full++},update(x){this.data[this.data.length-1]={...x};this.tail++},applyOptions(){},createPriceLine(){}});
const chart={panes:()=>[{getSeries:()=>series}],removeSeries(){},addSeries(){const s=make();series.push(s);return s}};
const D={candles:bars,vol},LW={chart,khDao:'',nen:{options:()=>({upColor:'green',downColor:'red'}),applyOptions(){}}};
window.BDCB=()=>({LW,D});window.LightweightCharts={LineSeries:'line',HistogramSeries:'hist'};
localStorage.getItem=()=>JSON.stringify({ds:[{id:'a',k:'natr',p:{n:3},mau:'#f00'},{id:'v',k:'vol',p:{n:20},mau:'#0f0'}]});
document.visibilityState='visible';
""" + bieu_do_chi_bao.JS + """
CBCN.ve();bars[99][2]=20;bars[99][3]=5;vol[100]=99;CBCN.tick();
setTimeout(()=>console.log(JSON.stringify(series.map(s=>({full:s.full,tail:s.tail,last:s.data.at(-1)})))),300);
""")
        self.assertTrue(all(s['full'] == 1 and s['tail'] == 1 for s in r))
        self.assertAlmostEqual(r[0]['last']['value'], 100 * (2 / 3 * 3 + 1 / 3 * 15) / 10)
        self.assertEqual(r[1]['last']['value'], 99)

    def test_mot_nghin_tick_chi_cap_nhat_duoi_khong_nap_lai_30000_nen(self):
        r = node(chart_realtime.JS + SERIES + """
send();for(let i=0;i<1000;i++){cs[29999]={time:30000,value:i};send()}
console.log(JSON.stringify({full:calls.filter(x=>x[0]==='full').length,tail:calls.filter(x=>x[0]==='tail').length,last:calls.at(-1)}));
""")
        self.assertEqual((r['full'], r['tail']), (1, 1000))
        self.assertEqual(r['last'], ['tail', {'time': 30000, 'value': 999}])

    def test_nen_moi_cap_nhat_ca_nen_vua_dong(self):
        r = node(chart_realtime.JS + SERIES + """
send();calls.length=0;cs[29999].value=99;cs.push({time:30001,value:100});send();
console.log(JSON.stringify(calls));
""")
        self.assertEqual(r, [['tail', {'time': 30000, 'value': 99}], ['tail', {'time': 30001, 'value': 100}]])

    def test_doi_lich_su_cung_so_nen_phai_nap_lai(self):
        r = node(chart_realtime.JS + SERIES + """
send();calls.length=0;const next=cs.map(x=>({...x}));next[1].value=55;send(next);
console.log(JSON.stringify({method:calls[0][0],corrected:calls[0][1][1]}));
""")
        self.assertEqual(r, {'method': 'full', 'corrected': {'time': 2, 'value': 55}})

    def test_chi_bao_sua_qua_khu_khong_duoc_dung_tail(self):
        r = node(chart_realtime.JS + SERIES + """
send();calls.length=0;cs[1].value=77;send(cs,false);
console.log(JSON.stringify({method:calls[0][0],corrected:calls[0][1][1]}));
""")
        self.assertEqual(r, {'method': 'full', 'corrected': {'time': 2, 'value': 77}})

    def test_update_loi_thi_phuc_hoi_toan_bo_chuoi(self):
        r = node(chart_realtime.JS + SERIES + """
send();calls.length=0;s.update=()=>{throw Error('stale index')};cs.at(-1).value=22;send();
console.log(JSON.stringify({method:calls[0][0],last:calls[0][1].at(-1)}));
""")
        self.assertEqual(r, {'method': 'full', 'last': {'time': 30000, 'value': 22}})

    def test_tick_cu_va_ohlc_hong_bi_loai(self):
        r = node(chart_realtime.JS + """
const x={ms:100,bid:10,ask:11,nen:[1,10,12,9,11]};
console.log(JSON.stringify([CHART_RT.hopLe(x,99),CHART_RT.hopLe(x,100),CHART_RT.hopLe(x,101),CHART_RT.hopLe({...x,bid:NaN},0),CHART_RT.hopLe({...x,nen:[1,10,8,9,11]},0)]));
""")
        self.assertEqual(r, [True, True, False, False, False])

    def test_ap_tick_ohlc_va_volume_khi_gia_dong_khong_doi(self):
        a = bieu_do.JS.index('function sgAp(')
        b = bieu_do.JS.index('// chỉ báo của cây', a)
        r = node(chart_realtime.JS + """
const D={nguon:'mt5',candles:[[1,10,11,9,10]],vol:{1:1}},sgK=()=>'',IND=[],cbSong=()=>{};
let sgMS=0,LW=null,sgNap=0;
""" + bieu_do.JS[a:b] + """
const ok=sgAp({k:'',ms:100,bid:10,ask:11,nen:[1,10,14,8,10],vol:20});
const old=sgAp({k:'',ms:99,bid:10,ask:11,nen:[1,10,11,9,10],vol:1});
console.log(JSON.stringify({ok,old,c:D.candles[0],vol:D.vol[1]}));
""")
        self.assertEqual(r, {'ok': True, 'old': False, 'c': [1, 10, 14, 8, 10], 'vol': 20})

    def test_do_p95_chi_tinh_thoi_gian_trinh_duyet_va_gioi_han_120_mau(self):
        r = node(chart_realtime.JS + """
let t=0;globalThis.performance={now:()=>t};
for(let i=1;i<=200;i++){CHART_RT.nhan();t+=i;CHART_RT.xong()}
CHART_RT.boTick();console.log(JSON.stringify(CHART_RT.thongTin()));
""")
        self.assertEqual((r['so_mau'], r['p95'], r['gan_nhat'], r['bo']), (120, 194, 200, 1))


class NewIndicators(unittest.TestCase):
    def calc(self, close):
        return node(VO + bieu_do_chi_bao.JS + '\nconst C=' + json.dumps(close) + ";const H=C.map(c=>c+1),L=C.map(c=>c-1),O=C;console.log(JSON.stringify(Object.fromEntries(['zscore','er','natr'].map(k=>[k,CBCN.LIB[k].tinh(H,L,C,O,{n:3})[0][1]]))));")

    def test_doi_chieu_cong_thuc_tay(self):
        r = self.calc([10, 11, 12, 13, 14, 15])
        self.assertEqual(r['zscore'][:2], [None, None])
        self.assertAlmostEqual(r['zscore'][-1], 1 / (2 / 3) ** .5)
        self.assertEqual(r['er'], [None, None, None, 1, 1, 1])
        self.assertAlmostEqual(r['natr'][-1], 100 * 2 / 15)

    def test_chuoi_phang_khong_nan_va_khong_dung_nen_tuong_lai(self):
        a, b = self.calc([10] * 8), self.calc([10] * 8 + [500, 1, 800])
        for key in a:
            self.assertEqual(a[key], b[key][:8])
        self.assertEqual(a['zscore'][-1], 0)
        self.assertEqual(a['er'][-1], 0)


if __name__ == '__main__':
    unittest.main()
