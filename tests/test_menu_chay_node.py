# -*- coding: utf-8 -*-
"""Chạy thật mã JS của menu chuột phải (bieu_do_menu.JS) trong Node với biểu đồ giả, không cần trình duyệt.

Lỗi đã gặp (26/11/2026): một chú thích // chèn giữa dòng nuốt mất `const ds=…;const cur=…`, vòng kiểm cảnh báo cục bộ ném ReferenceError mỗi giây
và cảnh báo "Giá chạm" không bao giờ báo. `node --check` không bắt được vì cú pháp vẫn hợp lệ; bài này chạy vòng đó và đòi cảnh báo phải nổ."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from so_cong_khai import bieu_do_menu

GIA = r"""
const nghe=[];const timers=[];globalThis.setInterval=(f)=>{timers.push(f);return timers.length};globalThis.setTimeout=(f)=>0;
globalThis.requestAnimationFrame=f=>0;
const el=()=>new Proxy(function(){},{get:(t,k)=>k==='getBoundingClientRect'?()=>({left:0,top:0,right:800,bottom:500,width:800,height:500})
  :k==='addEventListener'?(e,f)=>nghe.push([e,f]):k==='classList'?{add(){},remove(){},contains:()=>false,toggle(){}}:k==='dataset'?{}:k==='style'?{}
  :k==='querySelector'?()=>null:k==='querySelectorAll'?()=>[]:k==='appendChild'?()=>{}:k==='clientWidth'?800:k==='clientHeight'?500:undefined,set:()=>true});
const store=new Map();globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
globalThis.document={querySelector:s=>s==='.mnp-bao'?null:el(),documentElement:{classList:{contains:()=>false},clientWidth:1200},body:el(),
  createElement:()=>el(),addEventListener(){},fullscreenElement:null};
globalThis.addEventListener=()=>{};globalThis.removeEventListener=()=>{};globalThis.innerHeight=900;
const bao=[];const D={candles:[[1,99,101,98,100],[2,100,102,99,101]],bid:101,khac_vang:false};
const nen={createPriceLine:o=>o,removePriceLine:()=>{},priceScale:()=>({options:()=>({})}),coordinateToPrice:()=>100,priceToCoordinate:()=>10};
globalThis.window=globalThis;
window.BDMN=()=>({LW:{nen,chart:{panes:()=>[{getHeight:()=>400}],timeScale:()=>({coordinateToLogical:()=>1})}},D,VE:{ds:[],cong:'tro',an:false},VEC:{},ma:'XAUUSDp',
  dg:2,tf:'M15',TRONG:false,P:{bg:'#000',fg:'#fff'},fp:v=>Number(v).toFixed(2),f2:v=>Number(v).toFixed(2),vnN:t=>String(t),esc:s=>String(s),veLuu(){},veTb(){},
  veCong(){},veToa:()=>null,veTrung:()=>null,veXoa(){},moiId:()=>'id'+Math.random(),xong(){},lwPhu(){},lwNay(){},datTrong(){},ctabDat(){},rk:{},rkLuu(){},rkDraw(){},
  toast:a=>bao.push(a.tieu_de),beep(){},tkMa:()=>'XAUUSDp'});
"""
CHAY = r"""
localStorage.setItem('so-bao:XAUUSDp',JSON.stringify([{id:'a',p:100.5,len:true,luc:0}]));
window.MNP.ve();                                     // lần vẽ đầu: gắn D đang xem
let loi=null;for(const f of timers)try{f()}catch(e){loi=String(e)}
console.log(JSON.stringify({loi,bao,con:JSON.parse(localStorage.getItem('so-bao:XAUUSDp')||'[]').length}));
"""


@unittest.skipUnless(shutil.which('node'), 'máy không có Node.js')
class MenuChayNode(unittest.TestCase):
    def test_canh_bao_cuc_bo_no_khi_khong_co_may_chu(self):
        with tempfile.TemporaryDirectory() as d:
            tep = Path(d) / 'menu.js'
            tep.write_text(GIA + bieu_do_menu.JS + CHAY, encoding='utf-8')
            r = subprocess.run(['node', str(tep)], capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        kq = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertIsNone(kq['loi'], kq['loi'])                               # vòng kiểm không được ném lỗi
        self.assertEqual(kq['bao'], ['Giá chạm 100.50'])                       # giá 101 vượt mức 100,5 → báo đúng một lần
        self.assertEqual(kq['con'], 0)                                        # cảnh báo đã báo thì bỏ khỏi danh sách


if __name__ == '__main__':
    unittest.main()
