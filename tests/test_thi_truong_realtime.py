"""Luồng bảng giá và các phản hồi chậm chạy bằng JS thật, không gọi MT5."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from so_cong_khai import thi_truong_trang as page
from so_cong_khai import thi_truong
from test_chart_pro import node

ENV = r'''
const NOW=Date.now(),streams=[],intervals=[],storage={},toasts=[],events={};let quota=false,waitFetch=null,calls=0;
const make=()=>({children:[],appendChild(e){this.children.push(e);if(e.className==='toast')toasts.push(e.innerHTML)},setAttribute(){},remove(){}});
globalThis.document={documentElement:{lang:'vi'},visibilityState:'visible',createElement:make,body:make(),addEventListener:(n,f)=>events[n]=f};
globalThis.localStorage={getItem:k=>storage[k]??null,setItem:(k,v)=>{if(quota)throw Error('quota');storage[k]=v}};
globalThis.addEventListener=(n,f)=>events[n]=f;globalThis.setInterval=(f,ms)=>(intervals.push({f,ms}),intervals.length);globalThis.setTimeout=()=>1;globalThis.clearTimeout=()=>{};
Object.defineProperty(globalThis,'navigator',{value:{},configurable:true});
globalThis.EventSource=class{constructor(){streams.push(this);this.handlers={}}addEventListener(n,f){this.handlers[n]=f}};
const base=()=>({san_sang:true,ds:[{ma:'XAU',goc:'XAU',so_le:2,diem:.01,q:[100,101,NOW]}],lop:{}});
globalThis.fetch=async()=>{calls++;if(waitFetch)return waitFetch();return{ok:true,json:async()=>base()}};
CODE
const settle=async()=>{for(let i=0;i<6;i++)await new Promise(r=>setImmediate(r))};
const send=(q,s=true)=>streams[0].handlers.gia({data:JSON.stringify({s,q})});
(async()=>{await TT.batDau();await settle();TEST})();
'''


def run(code, extra=''):
    return node(ENV.replace('CODE', extra + page.JS_CHUNG).replace('TEST', code))


class Quotes(unittest.TestCase):
    def test_gia_anh_nen_duoc_chia_se_nhung_khong_gia_ket_noi_sse(self):
        r = run("streams[0].onerror();let changed=[];TT.on((k,ds)=>{if(k==='gia')changed.push(ds)});TT.tuAnh('XAU',[112,113,NOW+50]);TT.tuAnh('XAU',[90,91,NOW+49]);console.log(JSON.stringify({q:TT.by().get('XAU').q.slice(0,2),connected:TT.tt.ket_noi,changed}));")
        self.assertEqual(r, {'q': [112, 113], 'connected': False, 'changed': [['XAU']]})

    def test_bat_dau_nhieu_lan_khong_nhan_doi_sse_va_timer(self):
        r = run("await TT.batDau();await TT.batDau();console.log(JSON.stringify({streams:streams.length,intervals:intervals.length,calls}));")
        self.assertEqual(r, {'streams': 1, 'intervals': 1, 'calls': 1})

    def test_tick_cu_va_khong_hop_le_khong_ghi_de(self):
        r = run("send({XAU:[105,106,NOW+10]});send({XAU:[90,91,NOW+9]});send({XAU:[100,99,NOW+11]});send({XAU:[100,101,1e300]});console.log(JSON.stringify(TT.by().get('XAU').q));")
        self.assertEqual(r[:2], [105, 106])

    def test_http_den_muon_khong_ghi_de_tick_trong_luc_cho(self):
        r = run("let release;waitFetch=()=>new Promise(r=>release=r);const p=TT.tai(),p2=TT.tai();send({XAU:[110,111,NOW+20]});release({ok:true,json:async()=>({...base(),ds:[{...base().ds[0],q:[101,102,NOW+1]}]})});await Promise.all([p,p2]);console.log(JSON.stringify({same:p===p2,calls,q:TT.by().get('XAU').q}));")
        self.assertTrue(r['same'])
        self.assertEqual(r['calls'], 2)
        self.assertEqual(r['q'][:2], [110, 111])

    def test_tat_ca_ma_cu_van_duoc_danh_dau_chua_co_tick_moi(self):
        r = run("console.log(JSON.stringify(TT.nghi({q:[100,101,NOW-301000]})));")
        self.assertTrue(r)

    def test_get_thanh_cong_khong_che_loi_sse(self):
        r = run("send({XAU:[101,102,NOW+1]});streams[0].onerror();await TT.tai();console.log(JSON.stringify(TT.tt));")
        self.assertFalse(r['ok'])
        self.assertFalse(r['ket_noi'])

    def test_khong_co_sse_chi_tao_mot_vong_polling(self):
        r = run("for(let i=0;i<3;i++){await TT.tai();TT.noi()}console.log(JSON.stringify({streams:streams.length,polls:intervals.filter(x=>x.ms===3000).length,mode:TT.tt.kieu}));", 'window.EventSource=undefined;')
        self.assertEqual(r, {'streams': 0, 'polls': 1, 'mode': 'poll'})

    def test_canh_bao_khong_bao_thanh_cong_khi_quota_day(self):
        r = run("quota=true;const a=TT.CB.them('XAU',110,'x');console.log(JSON.stringify({a,error:TT.CB.loi,ds:TT.CB.ds()}));")
        self.assertIsNone(r['a'])
        self.assertTrue(r['error'])
        self.assertEqual(r['ds'], [])

    def test_canh_bao_cung_mili_giay_khong_trung_id(self):
        r = run("Date.now=()=>NOW;const a=TT.CB.them('XAU',110,''),b=TT.CB.them('XAU',120,'');console.log(JSON.stringify({different:a.id!==b.id,n:TT.CB.ds().length}));")
        self.assertEqual(r, {'different': True, 'n': 2})

    def test_kho_canh_bao_hong_khong_bi_ghi_de_thanh_rong(self):
        r = run("storage['tt-canh']='{bad';const a=TT.CB.them('XAU',110,'');console.log(JSON.stringify({a,kept:storage['tt-canh']}));")
        self.assertEqual(r, {'a': None, 'kept': '{bad'})

    def test_tick_cu_khong_kich_hoat_canh_bao_va_khong_bao_lap_khi_luu_loi(self):
        r = run("TT.CB.them('XAU',110,'');send({XAU:[120,121,NOW-1]});const old=TT.CB.ds()[0].da;quota=true;send({XAU:[120,121,NOW+1]});const first=toasts.length;send({XAU:[121,122,NOW+2]});console.log(JSON.stringify({old,once:first===toasts.length,done:!!TT.CB.ds()[0].da}));")
        self.assertIsNone(r['old'])
        self.assertTrue(r['once'])
        self.assertTrue(r['done'])


class BackendQuotes(unittest.TestCase):
    def test_tick_hong_khong_lam_mat_gia_tot_hoac_bao_san_sang(self):
        t = SimpleNamespace(bid=100, ask=101, time=1, time_msc=2000)
        mt = SimpleNamespace(symbol_info_tick=lambda _: t)
        b = thi_truong.BangGia(lambda: {'gia': {}}, mt5_fn=lambda _: mt)
        b.dac_ta = {'XAU': {}}
        self.assertEqual(b.doc_gia(), 1)
        for bid, ask, stamp in [(99, 100, 1999), (100, 99, 2001), (float('nan'), 101, 2002), (100, 101, float('nan'))]:
            t.bid, t.ask, t.time_msc = bid, ask, stamp
            with patch.object(thi_truong.song, 'khung_song', return_value=None):
                self.assertEqual(b.doc_gia(), 0)
            self.assertEqual(b.gia['XAU'], [100, 101, 2000])
        self.assertFalse(b.san_sang)


class LateResponses(unittest.TestCase):
    def test_bien_dong_doi_ma_nhanh_ke_ca_quay_lai_cung_ma(self):
        a = page.JS.index('async function bienDong(){')
        b = page.JS.index('function bdVe(){', a)
        r = node(r'''
const select={options:[1],dataset:{n:'2'}},out={innerHTML:''},$=s=>s==='#bd-ma'?select:out,T={by:()=>new Map([['A',{}],['B',{}]])},esc=String;
let bdMa='A',bdKq=null,bdSeq=0,bdCtl=null,bdLan=0,calls=0,releases=[],drawn=[];const bdVe=()=>drawn.push(bdKq.tag);
globalThis.fetch=async url=>{const tag=++calls;await new Promise(r=>releases.push(r));return{ok:true,json:async()=>({ma:new URL(url,'http://x').searchParams.get('ma'),tag})}};
''' + page.JS[a:b] + r'''
(async()=>{const first=bienDong();bdMa='B';const second=bienDong();bdMa='A';const third=bienDong();releases[2]();await third;releases[0]();releases[1]();await Promise.all([first,second]);console.log(JSON.stringify({ma:bdKq.ma,tag:bdKq.tag,drawn}));})();
''')
        self.assertEqual(r, {'ma': 'A', 'tag': 3, 'drawn': [3]})

    def test_ky_thuat_phan_hoi_cu_khong_ghi_de(self):
        a = page.JS.index('async function ktTai(){')
        b = page.JS.index('function ktVe(){', a)
        r = node(r'''
let ktMa='A',ktCT=null,ktSeq=0,ktCtl=null,ktLan=0,releases=[],drawn=[];const out={innerHTML:''},$=()=>out,esc=String,ktVe=()=>drawn.push(ktCT.tag);
globalThis.fetch=async url=>{const tag=releases.length+1;await new Promise(r=>releases.push(r));return{ok:true,json:async()=>({tag})}};
''' + page.JS[a:b] + r'''
(async()=>{const first=ktTai();ktMa='B';const second=ktTai();ktMa='A';const third=ktTai();releases[2]();await third;releases[0]();releases[1]();await Promise.all([first,second]);console.log(JSON.stringify(drawn));})();
''')
        self.assertEqual(r, [3])

    def test_sap_xep_lai_theo_gia_moi_giu_dong_dom(self):
        a = page.JS.index('function soSanh(')
        b = page.JS.index('function bangGia(){', a)
        r = node(r'''
const ds=[{ma:'A',v:1},{ma:'B',v:2},{ma:'C',v:null}],locDs=()=>ds.slice(),khoa=x=>x.v,sx={k:'ngay',d:-1};let rows=ds.map(x=>({dataset:{ma:x.ma}})),focus=0;
const button={isConnected:true,focus:()=>focus++},body={querySelectorAll:()=>rows,contains:()=>true,appendChild:r=>{rows=rows.filter(x=>x!==r);rows.push(r)}},$=()=>body;globalThis.document={activeElement:button};
''' + page.JS[a:b] + r'''
const originals=rows.slice();sapLai();const first=rows.map(x=>x.dataset.ma);ds[0].v=5;sapLai();console.log(JSON.stringify({first,second:rows.map(x=>x.dataset.ma),kept:rows.every(x=>originals.includes(x)),focus}));
''')
        self.assertEqual(r['first'], ['B', 'A', 'C'])
        self.assertEqual(r['second'], ['A', 'B', 'C'])
        self.assertTrue(r['kept'])
