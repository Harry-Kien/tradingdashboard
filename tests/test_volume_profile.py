# -*- coding: utf-8 -*-
"""Volume Profile trên biểu đồ (bieu_do_cong_cu.py, 28/11/2026): POC, vùng giá trị 70%, tách nến tăng/giảm, thiếu tick volume."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from so_cong_khai import bieu_do_cong_cu

GIA = """globalThis.window=globalThis;globalThis.localStorage={getItem:()=>null,setItem(){}};globalThis.document={addEventListener(){},querySelector:()=>null};
globalThis.addEventListener=()=>{};globalThis.matchMedia=()=>({matches:false});"""


def chay(code):
    node = shutil.which('node')
    if not node:
        raise unittest.SkipTest('không có node')
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / 'vp.js'
        f.write_text(GIA + bieu_do_cong_cu.JS + code, encoding='utf-8')
        r = subprocess.run([node, str(f)], capture_output=True, text=True, encoding='utf-8', timeout=60)  # noqa: S603
    if r.returncode:
        raise AssertionError(r.stderr[-2000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


class VolumeProfile(unittest.TestCase):
    def test_poc_va_vung_gia_tri(self):
        """Bốn nến ở 100–110 với khối lượng nhỏ, hai nến dồn khối lượng lớn ở 104–105: POC nằm trong 104–105, vùng giá trị chứa ≥ 70%."""
        r = chay("""const cs=[[1,100,110,100,109,0],[2,109,110,100,101],[3,101,110,100,108],[4,108,110,100,102],[5,104,105,104,105],[6,105,105,104,104]],
vol={1:100,2:100,3:100,4:100,5:2000,6:1500};const p=VNH.vpTinh(cs,vol,0,5,10);let va=0;for(let k=p.va[0];k<=p.va[1];k++)va+=p.tot[k];
console.log(JSON.stringify({poc:p.giaPoc,va:va/p.sum,tong:Math.round(p.sum),co:p.co,len:Math.round([...p.up].reduce((a,b)=>a+b,0)),xuong:Math.round([...p.dn].reduce((a,b)=>a+b,0)),hop:p.val<=p.giaPoc&&p.giaPoc<=p.vah}))""")
        self.assertTrue(104 <= r['poc'] <= 105, r)
        self.assertGreaterEqual(r['va'], 0.7)
        self.assertEqual(r['tong'], 3900)                                              # khối lượng được bảo toàn khi chia theo hàng giá
        self.assertEqual((r['co'], r['len'], r['xuong']), (6, 2200, 1700))             # nến tăng 1,3,5; nến giảm 2,4,6
        self.assertTrue(r['hop'])

    def test_thieu_tick_volume_bao_ro(self):
        r = chay("const cs=[[1,1,2,1,2],[2,2,3,2,3]];console.log(JSON.stringify([VNH.vpTinh(cs,null,0,1,10),VNH.vpTinh(cs,{1:5},0,1,10).thieu]))")
        self.assertEqual(r[0], {'loi': 'Thiếu tick volume cho đoạn này'})
        self.assertEqual(r[1], 1)

    def test_vpvr_chi_tinh_doan_dang_xem(self):
        """Tắt thì không vẽ; bật thì chỉ tính các nến trong vùng nhìn (nến 0–9 khối lượng khổng lồ ở 200 nằm ngoài vùng, không được tính)."""
        r = chay("""const goi=[];const X=new Proxy({},{get:(t,k)=>k in t?t[k]:k==='measureText'?(s=>({width:String(s).length*6})):(...a)=>{goi.push(k)},set:(t,k,v)=>{t[k]=v;return true}});
const cs=[],vol={};for(let i=0;i<40;i++){const b=i<10?200:100+(i%3);cs.push([i,b,b+1,b-1,b+.5]);vol[i]=i<10?1e6:(i===25?5000:100)}
const C={X,y:p=>400-p,pw:800,ph:400,P:{tp:'#0a0',sl:'#a00',mute:'#888'},cs,vol,ts:{getVisibleLogicalRange:()=>({from:15,to:39})},chu:(t)=>{goi.push('chu:'+t)},fp:v=>v.toFixed(2)};
VNH.datVpvr(false);const tat=VNH.veVpvr(C);VNH.datVpvr(true);const p=VNH.veVpvr(C);
const html=VNH.html({cong:'tro',bt:0},{tro:['Chọn','M0 0','']},(k,[t],kieu)=>'<b data-'+kieu+'="'+k+'"></b>');
console.log(JSON.stringify({tat,co:p.co,poc:p.giaPoc,ve:goi.some(x=>String(x).startsWith('chu:POC')),nut:html.includes('data-vpvr')}))""")
        self.assertIsNone(r['tat'])
        self.assertEqual(r['co'], 25)                                                  # nến 15–39 (vùng nhìn 15–39)
        self.assertTrue(99 <= r['poc'] <= 103, r)                                      # khối lượng 1e6 ở giá 200 ngoài vùng không kéo POC lên
        self.assertTrue(r['ve'] and r['nut'])

    def test_nam_trong_nhom_khoi_luong(self):
        nhom = bieu_do_cong_cu.JS.split('const NHOM=[', 1)[1].split('];', 1)[0]
        self.assertIn("'Khối lượng',['vpvung'],['vpneo'],['vpphien'],['avwap']", nhom)


if __name__ == '__main__':
    unittest.main()
