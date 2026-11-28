"""Chạy JS đồng bộ thật để tái hiện mất mạng, đổi mã và chỉnh khi đang lưu."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from so_cong_khai import hinh_ve

HARNESS = r"""
globalThis.window=globalThis;
const uid='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',ls={},events={},statuses=[],posts=[];
let offline=OFFLINE,hook=null,changedUser=false,symbol='XAUUSDp';
const A={id:'a',k:'ngang',a:{t:1,p:3500}},B={id:'b',k:'ngang',a:{t:2,p:3600}};
const VE={ds:LOCAL,keo:null,tam:null,cu:[],lai:[]};
const server={XAUUSDp:{ds:REMOTE,ban:3},EURUSDp:{ds:[],ban:null}};
window.HVD_CHU={id:uid,ten:'alpha',chu:true};window.HVD_MA=m=>m||'XAUUSDp';window.HVD_KHOA=m=>'so-ve:u_'+uid+':'+HVD_MA(m);
const key=()=>HVD_KHOA(symbol);ls[key()]=JSON.stringify(VE.ds);if(BASE!==null)ls['so-ve-dong:u_'+uid+':XAUUSDp']=JSON.stringify({base:BASE,ban:1});
globalThis.localStorage={getItem:k=>ls[k]??null,setItem:(k,v)=>{ls[k]=String(v)},get length(){return Object.keys(ls).length},key:i=>Object.keys(ls)[i]};
globalThis.document={visibilityState:'visible',querySelector:()=>null};
globalThis.setInterval=()=>0;globalThis.setTimeout=()=>1;globalThis.clearTimeout=()=>{};globalThis.confirm=()=>true;
globalThis.addEventListener=(n,f)=>events[n]=f;window.HVD_UI={paint:(s,t)=>statuses.push([s,t])};
const draft=ds=>{VE.ds=ds;ls[key()]=JSON.stringify(ds);if(window.HVD)HVD.doi()};
window.BDMN=()=>({ma:symbol,VE,veKhoa:key,veLuu:()=>draft(VE.ds),veTb(){},lwPhu(){}});
globalThis.fetch=async(u,opt={})=>{if(offline)throw Error('offline');if(changedUser)return{ok:false,status:409,json:async()=>({doi_tai_khoan:true})};
 const b=opt.body?JSON.parse(opt.body):null,ma=b?b.ma:new URL(u,'http://local').searchParams.get('ma'),s=server[ma];
 if(b){posts.push(b);if(hook){const f=hook;hook=null;f()};if(b.ban_co_so!==s.ban)return{ok:false,status:409,json:async()=>({xung_dot:true,...structuredClone(s)})};s.ds=structuredClone(b.ds);s.ban=(s.ban||0)+1;return{ok:true,status:200,json:async()=>({ok:true,chu:uid,...structuredClone(s)})}}
 return{ok:true,status:200,json:async()=>({chu:uid,...structuredClone(s)})}};
JS_CODE
const settle=async()=>{for(let i=0;i<5;i++)await new Promise(r=>setImmediate(r))};
(async()=>{await settle();TEST_CODE})();
"""


def run(local, remote, base, code, offline=False):
    node = shutil.which('node')
    if not node:
        raise unittest.SkipTest('Cần Node')
    js = HARNESS.replace('OFFLINE', json.dumps(offline)).replace('LOCAL', json.dumps(local)).replace('REMOTE', json.dumps(remote)).replace('BASE', json.dumps(base))
    js = js.replace('JS_CODE', hinh_ve.JS).replace('TEST_CODE', code)
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / 'sync.js'
        f.write_text(js, encoding='utf-8')
        p = subprocess.run([node, str(f)], capture_output=True, text=True, encoding='utf-8', timeout=20)  # noqa: S603
    if p.returncode:
        raise AssertionError(p.stderr[-1500:])
    return json.loads(p.stdout.strip().splitlines()[-1])


def item(id_='a', p=3500):
    return {'id': id_, 'k': 'ngang', 'a': {'t': 1, 'p': p}}


class Sync(unittest.TestCase):
    def test_ghep_thay_doi_khac_hinh_khong_mat_sua_doi_o_hai_noi(self):
        base = [item(), item('b', 3600)]
        r = run([item(p=3550), base[1]], [base[0], item('b', 3650)], base,
                'await HVD.gui();console.log(JSON.stringify(server.XAUUSDp.ds));')
        self.assertEqual({h['id']: h['a']['p'] for h in r}, {'a': 3550, 'b': 3650})

    def test_cung_hinh_bi_dung_lai_va_giu_ca_hai_theo_lua_chon(self):
        r = run([item(p=3550)], [item(p=3600)], [item()], """
await HVD.gui();const before=posts.length;HVD.giaiQuyet('both');await HVD.gui();
console.log(JSON.stringify({before,ds:server.XAUUSDp.ds}));
""")
        self.assertEqual(r['before'], 0)
        self.assertEqual(sorted(h['a']['p'] for h in r['ds']), [3550, 3600])
        self.assertEqual(len({h['id'] for h in r['ds']}), 2)

    def test_chinh_tiep_trong_luc_gui_khong_bi_ack_cu_nap_de(self):
        r = run([item()], [], [], """
hook=()=>draft([A,B]);await HVD.gui();const pending=structuredClone(VE.ds);await HVD.gui();
console.log(JSON.stringify({pending,ds:server.XAUUSDp.ds,posts:posts.length}));
""")
        self.assertEqual([h['id'] for h in r['pending']], ['a', 'b'])
        self.assertEqual([h['id'] for h in r['ds']], ['a', 'b'])
        self.assertEqual(r['posts'], 2)

    def test_mat_mang_giu_nhap_va_gui_lai(self):
        r = run([item()], [], [], """
const first=await HVD.gui(),draftSaved=JSON.parse(ls[key()]);offline=false;await HVD.gui();
console.log(JSON.stringify({first,draftSaved,ds:server.XAUUSDp.ds}));
""", offline=True)
        self.assertFalse(r['first'])
        self.assertEqual(r['draftSaved'], r['ds'])
        self.assertEqual(r['ds'], [item()])

    def test_doi_ma_truoc_khi_gui_van_gui_dung_chart_cu(self):
        r = run([item()], [item()], [item()], """
draft([A,B]);symbol='EURUSDp';draft([{...A,id:'eur'}]);await HVD.gui();await settle();await HVD.gui();
console.log(JSON.stringify(server));
""")
        self.assertEqual([h['id'] for h in r['XAUUSDp']['ds']], ['a', 'b'])
        self.assertEqual([h['id'] for h in r['EURUSDp']['ds']], ['eur'])

    def test_phien_da_doi_khong_day_nhap_cua_nguoi_cu_sang_nguoi_moi(self):
        r = run([item()], [item()], [item()], """
changedUser=true;draft([A,B]);await HVD.gui();await HVD.gui();console.log(JSON.stringify({posts:posts.length,ds:server.XAUUSDp.ds,status:statuses.at(-1)[0]}));
""")
        self.assertEqual((r['posts'], r['ds'], r['status']), (0, [item()], 'error'))

    def test_nhap_nhap_cu_chua_gui_va_khong_lap_lai_hay_ghi_de(self):
        r = run([item()], [item()], [item()], """
ls['so-ve:XAU']=JSON.stringify([{...A,a:{t:1,p:3550}},B]);const original=ls['so-ve:XAU'];
const first=await HVD.nhapCuLocal(),second=await HVD.nhapCuLocal();
console.log(JSON.stringify({first,second,ds:server.XAUUSDp.ds,oldKept:ls['so-ve:XAU']===original}));
""")
        self.assertEqual((r['first'], r['second'], r['oldKept']), (2, 0, True))
        self.assertEqual(sorted(h['a']['p'] for h in r['ds']), [3500, 3550, 3600])
