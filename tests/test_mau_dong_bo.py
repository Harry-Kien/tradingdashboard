"""Chạy toàn bộ JS đồng bộ mẫu để kiểm mất mạng, xung đột và phản hồi chậm."""
import json
import unittest
from unittest import mock

from so_cong_khai import bieu_do, mau_chi_bao
from test_chart_pro import node
import test_chart_dong_bo as drawing_sync


HARNESS = r"""
const uid='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',key='so-cbcn1:u_'+uid,ls={},events={},posts=[];
const initial=LOCAL,base=BASE,server={...REMOTE,ban:3};let offline=false,hook=null,switched=false;
window.HVD_CHU={id:uid};window.HVD_CB_KEY=key;ls[key]=JSON.stringify(initial);ls[key+'-meta-v2']=JSON.stringify({base,ban:1});
const copy=x=>JSON.parse(JSON.stringify(x));
window.localStorage={getItem:k=>ls[k]??null,setItem:(k,v)=>ls[k]=String(v)};
window.document={visibilityState:'visible',querySelector:()=>null};
window.addEventListener=(k,f)=>events[k]=f;window.setInterval=()=>0;window.confirm=()=>true;
window.CBCN={dongBo:x=>ls[key]=JSON.stringify({...JSON.parse(ls[key]),mau:x.mau,sao:x.sao})};
window.fetch=async(url,o={})=>{if(offline)throw Error('offline');if(switched)return{status:409,ok:false,json:async()=>({doi_tai_khoan:true})};
 if(o.method==='POST'){const b=JSON.parse(o.body);posts.push(copy(b));if(hook){const f=hook;hook=null;f()}
 if(b.ban_co_so!==server.ban)return{status:409,ok:false,json:async()=>({ok:false,xung_dot:true,chu:uid,...copy(server)})};
 server.mau=copy(b.mau);server.sao=copy(b.sao);server.ban++;return{ok:true,status:200,json:async()=>({ok:true,chu:uid,ban:server.ban})}}
 return{ok:true,status:200,json:async()=>({chu:uid,...copy(server)})}};
JS_CODE
const settle=async()=>{for(let i=0;i<5;i++)await new Promise(r=>setImmediate(r))};
(async()=>{await settle();TEST_CODE})();
"""


def run(local, remote, base, code):
    js = HARNESS.replace('LOCAL', json.dumps(local)).replace('REMOTE', json.dumps(remote)).replace('BASE', json.dumps(base))
    return node(js.replace('JS_CODE', mau_chi_bao.JS).replace('TEST_CODE', code))


def state(**templates):
    return {'mau': templates, 'sao': []}


class TemplateSync(unittest.TestCase):
    def test_ghep_doc_lap_sau_do_gui_dung_ban_co_so(self):
        r = run(state(A=[], B=[]), state(A=[], C=[]), state(A=[]), 'await MCB.gui();console.log(JSON.stringify({server,posts}));')
        self.assertEqual(set(r['server']['mau']), {'A', 'B', 'C'})
        self.assertEqual(r['posts'][0]['ban_co_so'], 3)

    def test_cung_mau_xung_dot_dung_gui_cho_lua_chon(self):
        r = run(state(A=[{'k': 'ema'}]), state(A=[{'k': 'rsi'}]), state(A=[]), """
await MCB.gui();const before=posts.length;MCB.resolve('both');await settle();
console.log(JSON.stringify({before,server}));
""")
        self.assertEqual(r['before'], 0)
        self.assertEqual(len(r['server']['mau']), 2)

    def test_sua_tiep_trong_luc_post_khong_bi_ack_cu_ghi_de(self):
        r = run(state(A=[], B=[]), state(A=[]), state(A=[]), """
hook=()=>{const v=JSON.parse(ls[key]);v.mau.C=[];ls[key]=JSON.stringify(v)};await MCB.gui();
const after=JSON.parse(ls[key]);await MCB.gui();console.log(JSON.stringify({after,server}));
""")
        self.assertEqual(set(r['after']['mau']), {'A', 'B', 'C'})
        self.assertEqual(set(r['server']['mau']), {'A', 'B', 'C'})

    def test_post_409_ghep_ban_moi_khong_de_len_thay_doi_tab_khac(self):
        r = run(state(A=[], B=[]), state(A=[]), state(A=[]), """
hook=()=>{server.mau.C=[];server.ban++};await MCB.gui();await MCB.gui();console.log(JSON.stringify(server));
""")
        self.assertEqual(set(r['mau']), {'A', 'B', 'C'})

    def test_mat_mang_giu_nhap_roi_gui_lai(self):
        r = run(state(A=[], B=[]), state(A=[]), state(A=[]), """
offline=true;await MCB.gui();const draft=JSON.parse(ls[key]);offline=false;await MCB.gui();
console.log(JSON.stringify({draft,server}));
""")
        self.assertIn('B', r['draft']['mau'])
        self.assertIn('B', r['server']['mau'])

    def test_doi_phien_khong_gui_sang_chu_moi(self):
        r = run(state(A=[], B=[]), state(A=[]), state(A=[]), """
switched=true;await MCB.gui();switched=false;await MCB.gui();console.log(JSON.stringify({posts:posts.length,server}));
""")
        self.assertEqual(r['posts'], 0)
        self.assertNotIn('B', r['server']['mau'])


class DrawingSyncSafety(unittest.TestCase):
    def test_phan_hoi_den_muon_khi_vao_replay_khong_bi_ghi_de_sau_khi_thoat(self):
        h = drawing_sync.HARNESS.replace('const key=()=>HVD_KHOA(symbol);', "const key=()=>(window.PHAT_LAI?'so-ve-luyen:':'')+HVD_KHOA(symbol);")
        a = drawing_sync.item()
        with mock.patch.object(drawing_sync, 'HARNESS', h):
            r = drawing_sync.run([a], [a], [a], """
const scope=HVD.truocLuyen();server.XAUUSDp.ds=[A,B];server.XAUUSDp.ban++;
const pending=HVD.nap();window.PHAT_LAI=true;draft([{id:'practice',k:'ngang',a:{t:9,p:3700}}]);await pending;
const restored=HVD.sauLuyen(scope,[A]);window.PHAT_LAI=false;VE.ds=restored.ds;ls[key()]=JSON.stringify(VE.ds);await HVD.gui();
console.log(JSON.stringify({ds:server.XAUUSDp.ds,posts:posts.length}));
""")
        self.assertEqual({x['id'] for x in r['ds']}, {'a', 'b'})
        self.assertEqual(r['posts'], 0)

    def test_mat_bo_nho_cuc_bo_van_giu_nhap_trong_ram_khi_doi_che_do(self):
        h = drawing_sync.HARNESS.replace('const key=()=>HVD_KHOA(symbol);', "const key=()=>(window.PHAT_LAI?'so-ve-luyen:':'')+HVD_KHOA(symbol);")
        a = drawing_sync.item()
        with mock.patch.object(drawing_sync, 'HARNESS', h):
            r = drawing_sync.run([a], [a], [a], """
VE.luuLoi=true;draft([A,B]);const scope=HVD.truocLuyen(),get=localStorage.getItem;
localStorage.getItem=k=>k===scope?JSON.stringify([A]):get(k);window.PHAT_LAI=true;VE.ds=[{id:'practice'}];
console.log(JSON.stringify(HVD.sauLuyen(scope,[A])));
""")
        self.assertEqual({x['id'] for x in r['ds']}, {'a', 'b'})
        self.assertTrue(r['luuLoi'])

    def test_nhap_luyen_tap_khong_gui_vao_kho_that(self):
        h = drawing_sync.HARNESS.replace('const key=()=>HVD_KHOA(symbol);', "const key=()=>(window.PHAT_LAI?'so-ve-luyen:':'')+HVD_KHOA(symbol);")
        a = drawing_sync.item()
        with mock.patch.object(drawing_sync, 'HARNESS', h):
            r = drawing_sync.run([a], [a], [a], """
window.PHAT_LAI=true;draft([{id:'practice',k:'ngang',a:{t:9,p:3700}}]);const ok=await HVD.gui();
console.log(JSON.stringify({ok,server:server.XAUUSDp.ds,posts:posts.length}));
""")
        self.assertFalse(r['ok'])
        self.assertEqual(r['server'], [a])
        self.assertEqual(r['posts'], 0)

    def test_loi_bo_nho_va_mat_mang_can_canh_bao_truoc_khi_dong(self):
        a = drawing_sync.item()
        r = drawing_sync.run([a], [a], [a], """
offline=true;VE.luuLoi=true;draft([A,B]);await HVD.gui();let prevented=false;
events.beforeunload({preventDefault:()=>prevented=true});console.log(JSON.stringify({prevented}));
""")
        self.assertTrue(r['prevented'])

    def test_nhan_nguon_gia_khong_bao_song_khi_chua_co_tick(self):
        js = bieu_do.JS.split('function srcVe(){', 1)[1].split('setInterval(srcVe', 1)[0]
        r = node("""
const sr={innerHTML:''},$=()=>sr,D={nguon:'mt5'},ES={};let SG=null,esLoi=0;
""" + 'function srcVe(){' + js + """
srcVe();const waiting=sr.innerHTML;SG={ms:Date.now()-180000};srcVe();console.log(JSON.stringify({waiting,stale:sr.innerHTML}));
""")
        self.assertIn('đang chờ tick đầu tiên', r['waiting'])
        self.assertIn('chưa có tick mới', r['stale'])
        self.assertNotIn('thị trường đang nghỉ', r['stale'])


if __name__ == '__main__':
    unittest.main()
