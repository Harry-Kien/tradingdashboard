# -*- coding: utf-8 -*-
"""Thanh công cụ vẽ theo nhóm và các công cụ vẽ thêm (bieu_do_cong_cu.py, 27/11/2026).

Chạy thật mã JS trong Node với canvas giả: mỗi công cụ mới phải vẽ được (cả lúc đang đặt dở) và trả về chấm kéo + hàm bắt chuột;
mọi công cụ có sẵn trong bieu_do.py phải nằm trong một nhóm của thanh mới (không rơi mất công cụ nào khi đổi sang thanh nhóm)."""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from so_cong_khai import bieu_do, bieu_do_cong_cu

JS = bieu_do_cong_cu.JS

GIA = r"""
globalThis.window=globalThis;const store=new Map();globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v))};
globalThis.document={addEventListener(){},querySelector:()=>null};globalThis.addEventListener=()=>{};globalThis.matchMedia=()=>({matches:false});
const goi=[];const X=new Proxy({},{get:(t,k)=>k in t?t[k]:k==='measureText'?(s=>({width:String(s).length*6})):(...a)=>{goi.push(k)},set:(t,k,v)=>{t[k]=v;return true}});
const cs=[];for(let i=0;i<60;i++){const o=100+Math.sin(i/5)*8;cs.push([i,o,o+3,o-3,o+Math.cos(i)*2])}
const ts={logicalToCoordinate:l=>l*10,coordinateToLogical:x=>x/10,getVisibleLogicalRange:()=>({from:0,to:80})};
const doan=(x1,y1,x2,y2,x,yy)=>{const dx=x2-x1,dy=y2-y1,L=dx*dx+dy*dy||1,k=Math.max(0,Math.min(1,((x-x1)*dx+(yy-y1)*dy)/L));return Math.hypot(x-x1-k*dx,yy-y1-k*dy)};
const VE={tam:null,ds:[]};
const C={X,y:p=>(200-p)*4,pw:800,ph:400,P:{bg:'#fff',fg:'#111',mute:'#888',tp:'#0a0',sl:'#a00',vao:'#00f'},cs,dt:1,ts,ix:t=>t,vx:t=>t*10,chu:(t,x,y)=>String(t).length*6,cham(){},doan,
 tg:s=>s+'s',atr:2,vePct:f=>f*100+'%',veNd:()=>[],veLw:()=>1,fp:v=>Number(v).toFixed(2),f2:v=>Number(v).toFixed(2),vn:t=>String(t),VE};
const LW={nen:{coordinateToPrice:y=>200-y/4}},D={candles:cs};
"""

CHAY = r"""
const kq={},VEX=window.VEX;
for(const[k,d]of Object.entries(VEX)){try{
  const h={id:'x'+k,k,a:{t:10,p:100},b:{t:30,p:110}};
  if(d.n){const n=d.n===99?4:d.n;h.pts=[];for(let i=0;i<n;i++)h.pts.push({t:10+i*5,p:100+(i%2?6:-4)});h.a=h.pts[0];delete h.b}
  if(k==='dabut')h.pts=[{t:10,p:100},{t:15,p:104},{t:20,p:101}];
  if(d.chu)h.chu='Ghi chú thử cho công cụ '+k;
  if(d.them)Object.assign(h,d.them(h.a,{x:100,y:100},(x,y)=>({t:x/10,p:200-y/4}),{bt:3}));
  if(d.c)h.c=d.c(h,LW,D);
  if(d.tao===1||d.chu){if(!d.them||!('b' in d.them(h.a,{x:1,y:1},()=>({t:1,p:1}),{})))delete h.b}
  const xa=C.vx(h.a.t),ya=C.y(h.a.p),xb=h.b?C.vx(h.b.t):null,yb=h.b?C.y(h.b.p):null;
  const g=d.ve(h,C,true,'#f00',xa,ya,xb,yb);
  const dang=d.n?(()=>{const t={...h,pts:h.pts.slice(0,2)};VE.tam=t;const r=d.ve(t,C,false,'#f00',xa,ya,xb,yb);VE.tam=null;return!!r})():true;
  const muc=(g&&g.nut&&g.nut[0])?[g.nut[0][1],g.nut[0][2]]:[xa,ya];
  kq[k]={ok:!!g&&Array.isArray(g.nut)&&typeof g.trong==='function',trung:g?!!g.trong(muc[0],muc[1])||g.nut.length>0:false,dang,ten:d.ten,goi:d.goi}
 }catch(e){kq[k]={loi:String(e&&e.stack||e)}}}
const VEC={tro:['Chọn','M0 0','']};for(const[k,d]of Object.entries(VEX))VEC[k]=[d.ten,d.d,d.goi];
for(const n of window.VNH.NHOM)for(const r of n.ds)if(Array.isArray(r)&&!VEC[r[0]])VEC[r[0]]=['cũ '+r[0],'M0 0',''];
const nut=(k,[ten],kieu)=>`<button data-${kieu}="${k}" title="${ten}"></button>`;
const html=window.VNH.html({cong:'fib',bt:null},VEC,nut);
console.log(JSON.stringify({kq,html,cuoi:JSON.parse(localStorage.getItem('so-ve-nhom')||'{}')}));
"""


def _chay():
    node = shutil.which('node')
    if not node:
        raise unittest.SkipTest('không có node')
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / 'cc.js'
        f.write_text(GIA + JS + CHAY, encoding='utf-8')
        r = subprocess.run([node, str(f)], capture_output=True, text=True, encoding='utf-8', timeout=60)  # noqa: S603
    if r.returncode:
        raise AssertionError(r.stderr[-3000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


class CongCuVeThem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kq = _chay()

    def test_moi_cong_cu_ve_duoc(self):
        kq = self.kq['kq']
        self.assertGreaterEqual(len(kq), 33)
        for k, v in kq.items():
            self.assertNotIn('loi', v, (k, v.get('loi')))
            self.assertTrue(v['ok'], k)
            self.assertTrue(v['trung'], k)
            self.assertTrue(v['dang'], k)
            self.assertRegex(k, r'^[a-z0-9_]{1,20}$')                         # khớp bộ lọc loại hình của máy chủ (hinh_ve.py)
            self.assertTrue(v['ten'] and v['goi'], k)

    def test_cong_cu_moi_khong_trung_cong_cu_cu(self):
        cu = set(re.findall(r"(?<![A-Za-z0-9_])([a-z0-9_]+):\['", bieu_do.JS.split(' VEC={', 1)[1].split(' NHIEU=', 1)[0]))
        self.assertIn('xu', cu)
        self.assertFalse(cu & set(self.kq['kq']), cu & set(self.kq['kq']))

    def test_moi_cong_cu_cu_nam_trong_mot_nhom(self):
        cu = set(re.findall(r"(?<![A-Za-z0-9_])([a-z0-9_]+):\['", bieu_do.JS.split(' VEC={', 1)[1].split(' NHIEU=', 1)[0])) - {'tro'}
        nhom = JS.split('const NHOM=[', 1)[1].split('];', 1)[0]
        for k in cu | set(self.kq['kq']):
            self.assertIn(f"['{k}'", nhom, k)

    def test_thanh_nhom(self):
        h = self.kq['html']
        for g in ('duong', 'fib', 'mau', 'dubao', 'hinh', 'chu', 'bt'):
            self.assertIn(f'data-g="{g}"', h)
            self.assertIn(f'data-nh="{g}"', h)
        self.assertIn('data-c="fib"', h)                                       # nhóm mang công cụ đang cầm
        self.assertEqual(self.kq['cuoi'].get('fib'), 'fib')
        self.assertTrue(h.startswith('<button data-c="tro"'))

    def test_noi_vao_trang(self):
        b = bieu_do.JS
        self.assertIn('const VEX=window.VEX||{};for(const[k,v]of Object.entries(VEX)){VEC[k]=[v.ten,v.d,v.goi];if(v.n)NHIEU[k]=v.n}', b)
        self.assertIn('if(VEX[h.k])g=VEX[h.k].ve(h,VC,sel,col,xa,ya,xb,yb);', b)
        self.assertIn('if(window.VNH)VNH.gan(VTB,{VE,VEC,veCong,veTb});', b)
        self.assertIn('if(VEX[h.k]&&VEX[h.k].c){if(!h.c)h.c=VEX[h.k].c(h,LW,D)}', b)
        nguon = Path(bieu_do.__file__).read_text(encoding='utf-8')
        self.assertIn('<script>{bieu_do_cong_cu.JS}</script><script>{JS}</script>', nguon)      # mô-đun nạp trước mã chính
        self.assertIn('{bieu_do_cong_cu.CSS}', nguon)

    def test_trang_dung_cu_phap(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('không có node')
        with tempfile.TemporaryDirectory() as d:
            for i, s in enumerate((JS, bieu_do.JS)):
                f = Path(d) / f'{i}.js'
                f.write_text(s, encoding='utf-8')
                r = subprocess.run([node, '--check', str(f)], capture_output=True, text=True, encoding='utf-8', timeout=60)  # noqa: S603
                self.assertEqual(r.returncode, 0, r.stderr[-2000:])

    def test_do_dai_nen_khong_lay_hai_nen_dau(self):
        """Lỗi đã gặp: dt = cs[1]-cs[0]; D1 bắt đầu thứ Sáu → thứ Hai thì dt = 3 ngày, hình vẽ bên phải nến cuối lệch chỗ."""
        node = shutil.which('node')
        if not node:
            self.skipTest('không có node')
        b = bieu_do.JS
        self.assertNotIn('cs[1][0]-cs[0][0]', b)
        self.assertNotIn('cs[1][0]-cs[0][0]', JS)
        tfs = re.search(r'const TFS=\{[^}]*\};', b).group(0)
        ham = re.search(r'const dtNen=cs=>\{.*?\};', b).group(0)
        ngay = 86400
        cs = [[0, 1], [3 * ngay, 1]] + [[3 * ngay + i * ngay, 1] for i in range(1, 10)]
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'dt.js'
            f.write_text(f'let tf="D1";{tfs}{ham}const cs={json.dumps(cs)};const a=dtNen(cs);tf="MN1";console.log(JSON.stringify([a,dtNen(cs)]))', encoding='utf-8')
            r = subprocess.run([node, str(f)], capture_output=True, text=True, timeout=30)  # noqa: S603
        self.assertEqual(json.loads(r.stdout), [ngay, ngay])                   # D1 theo bảng; khung lạ thì khoảng nhỏ nhất của nến cuối

    def test_chu_khong_vao_html(self):
        """Chữ người dùng gõ chỉ vẽ bằng fillText; tên nhóm, tên công cụ đi qua esc."""
        self.assertNotIn('innerHTML=h.chu', JS)
        self.assertIn('<span>${esc(VEC[k][0])}</span>', JS)


if __name__ == '__main__':
    unittest.main()
