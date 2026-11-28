"""Chạy hàm vẽ thật bằng Node: đổi khung và Tự co giá phải về nến mới nhất."""
import unittest

from so_cong_khai import bieu_do, chart_realtime
from test_chart_pro import node


HARNESS = """
let tf='M15',ma='',chartEpoch=0;
const AP={hidden:false},stage={dataset:{},setAttribute(){}};
const $=id=>id==='#tu-co'?AP:id==='.stage'?stage:{textContent:''};
const defN=()=>100,requestAnimationFrame=()=>{},lwPhu=()=>{},lwDoc=()=>{};
let D={tf:'M15',candles:Array.from({length:900},(_,i)=>[i+1,10,12,9,11]),_chart_epoch:0};
const ts={range:{from:50,to:150},sets:0,getVisibleLogicalRange(){return {...this.range}},
 setVisibleLogicalRange(r){this.range={...r};this.sets++}};
const ps={auto:false,applyOptions(o){this.auto=o.autoScale}};
const series=()=>({applyOptions(){},setData(){},update(){},removePriceLine(){},priceScale:()=>ps});
let LW={chart:{timeScale:()=>ts,applyOptions(){}},nen:series(),key:'XAU|M15',idx:new Map(),
 lines:[],dao:[],khDao:'',e20:series(),e50:series(),bbt:series(),bbd:series(),e200:series(),
 stU:series(),stD:series(),it:series(),ik:series(),ia:series(),ib:series(),ic:series()};
const pal=()=>({bg:'#000',fg:'#fff',grid:'#111'}),dg=2,on={},plan=null,TRONG=false,tkLenh=()=>[],lenhHien=()=>[];
"""


class LatestCandles(unittest.TestCase):
    def run_js(self, code):
        a = bieu_do.JS.index('function lwNay(')
        b = bieu_do.JS.index('function lwZoom(', a)
        c = bieu_do.JS.index('function lwDraw(')
        d = bieu_do.JS.index('// lớp phủ:', c)
        return node(HARNESS + bieu_do.JS[a:b] + bieu_do.JS[c:d] + code)

    def test_tu_co_dat_lai_ca_hai_truc_va_xoa_lenh_cuon_cu(self):
        r = self.run_js("""
LW.cho={from:1,to:50};lwNay();lwDraw();
console.log(JSON.stringify({range:ts.range,auto:ps.auto,pending:LW.veMoi,cho:LW.cho,hidden:AP.hidden}));
""")
        self.assertEqual(r, {'range': {'from': 800, 'to': 904}, 'auto': True,
                             'pending': False, 'cho': None, 'hidden': True})

    def test_dung_moc_thoi_gian_khi_chi_bao_cu_con_tren_truc_chung(self):
        r = self.run_js("""
ts.timeToIndex=t=>5000+(t-1)*4;LW.hov=true;LW.hoverTime=1;lwNay();
console.log(JSON.stringify({range:ts.range,auto:ps.auto,hover:LW.hov,time:LW.hoverTime}));
""")
        self.assertEqual(r, {'range': {'from': 8200, 'to': 8601}, 'auto': True, 'hover': False, 'time': None})

    def test_cho_chuoi_moi_duoc_chart_nhan_truoc_khi_co_gia(self):
        r = self.run_js("""
ts.timeToIndex=()=>null;lwNay();
console.log(JSON.stringify({range:ts.range,pending:LW.veMoi,sets:ts.sets,hidden:AP.hidden}));
""")
        self.assertEqual(r, {'range': {'from': 50, 'to': 150}, 'pending': True, 'sets': 0, 'hidden': False})

    def test_bam_khi_khung_moi_chua_tai_xong(self):
        r = self.run_js("""
tf='H4';lwNay();const wait={range:ts.range,pending:LW.veMoi,auto:ps.auto};
D={tf:'H4',candles:Array.from({length:300},(_,i)=>[i+1,20,22,19,21]),_chart_epoch:0};lwDraw();
console.log(JSON.stringify({wait,range:ts.range,auto:ps.auto,pending:LW.veMoi}));
""")
        self.assertEqual(r['wait'], {'range': {'from': 50, 'to': 150}, 'pending': True, 'auto': False})
        self.assertEqual(r['range'], {'from': 200, 'to': 304})
        self.assertTrue(r['auto'])
        self.assertFalse(r['pending'])

    def test_doi_a_b_a_khong_nhan_nham_du_lieu_a_cu(self):
        a = bieu_do.JS.index('const loadGate=')
        b = bieu_do.JS.index('async function load(', a)
        r = self.run_js(chart_realtime.JS + """
const sgK=()=>ma+'|'+tf,sgDong=()=>{},VE={},LWO=null;
let sgNap=0,SG=null,CBS=null,sgMS=0,sgVe=0,LECH=null,mouse=null,drag=null,view={n:50,off:70};
globalThis.CustomEvent=function(t,o){this.type=t;this.detail=o.detail};window.dispatchEvent=()=>{};
""" + bieu_do.JS[a:b].replace('chartEpoch=0', 'unusedEpoch=0') + """
tf='H1';chartSwitch();tf='M15';chartSwitch();lwDraw();
const wait={pending:LW.veMoi,range:ts.range,view};
D={...D,_chart_epoch:chartEpoch};lwDraw();
console.log(JSON.stringify({wait,range:ts.range,auto:ps.auto,epoch:chartEpoch,pending:LW.veMoi}));
""")
        self.assertEqual(r['wait'], {'pending': True, 'range': {'from': 50, 'to': 150}, 'view': {'n': 100, 'off': 0}})
        self.assertEqual(r['range'], {'from': 800, 'to': 904})
        self.assertEqual(r['epoch'], 2)
        self.assertTrue(r['auto'])
        self.assertFalse(r['pending'])

    def test_ban_nho_dem_roi_ban_moi_va_lich_su_ghep_khong_troi(self):
        r = self.run_js("""
LW.veMoi=true;lwDraw();
// Bản thật bổ sung nến đang chạy; sau đó nạp thêm 1000 nến cũ.
D.candles.push([901,11,13,10,12]);lwDraw();
D.candles=Array.from({length:1000},(_,i)=>[i-999,10,12,9,11]).concat(D.candles);lwDraw();
console.log(JSON.stringify({range:ts.range,last:D.candles.length-1,auto:ps.auto}));
""")
        self.assertEqual(r['range'], {'from': 1800, 'to': 1904})
        self.assertLessEqual(r['range']['from'], r['last'])
        self.assertGreaterEqual(r['range']['to'], r['last'])

    def test_tick_va_tai_dinh_ky_giu_vung_xem_lich_su(self):
        r = self.run_js("""
lwNay();ts.range={from:100,to:200};ps.auto=false;AP.hidden=false;
for(let i=0;i<100;i++){D.candles[899][4]=10+i/100;lwDraw()}
console.log(JSON.stringify({range:ts.range,auto:ps.auto,hidden:AP.hidden}));
""")
        self.assertEqual(r, {'range': {'from': 100, 'to': 200}, 'auto': False, 'hidden': False})

    def test_doi_ma_va_du_lieu_it_nen(self):
        r = self.run_js("""
ma='EURUSDp';lwNay();const pending=LW.veMoi;
D={tf:'M15',ma,khac_vang:true,candles:[[1,1,2,.5,1.5]],_chart_epoch:0};lwDraw();
console.log(JSON.stringify({pending,range:ts.range,auto:ps.auto}));
""")
        self.assertEqual(r, {'pending': True, 'range': {'from': -.5, 'to': 5}, 'auto': True})

    def test_chua_co_du_lieu_van_giu_yeu_cau(self):
        r = self.run_js("""
D=null;lwNay();const pending=LW.veMoi;D={tf:'M15',candles:[],_chart_epoch:0};lwNay();
console.log(JSON.stringify({pending,empty:LW.veMoi,sets:ts.sets}));
""")
        self.assertEqual(r, {'pending': True, 'empty': True, 'sets': 0})

    def test_vang_mac_dinh_khung_m1_co_ten_ma_mt5(self):
        r = self.run_js("""
tf='M1';D={...D,tf,khac_vang:true,ma:'XAUUSDp'};LW.veMoi=true;lwDraw();
console.log(JSON.stringify({range:ts.range,auto:ps.auto,pending:LW.veMoi}));
""")
        self.assertEqual(r, {'range': {'from': 800, 'to': 904}, 'auto': True, 'pending': False})
