"""Kiểm toán công cụ vẽ: công thức, tọa độ, dữ liệu thiếu và bảo vệ hình khóa."""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from so_cong_khai import bieu_do, bieu_do_cong_cu, dich, hinh_ve
from test_bieu_do_cong_cu import CHAY, GIA


def node(code, js=None):
    exe = shutil.which('node')
    if not exe:
        raise unittest.SkipTest('Cần Node để chạy mã vẽ thật')
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'test.js'
        p.write_text(GIA + (bieu_do_cong_cu.JS if js is None else js) + '\n(()=>{\n' + code + '\n})();', encoding='utf-8')
        run = subprocess.run([exe, str(p)], capture_output=True, text=True, encoding='utf-8', timeout=20)  # noqa: S603
    if run.returncode:
        raise AssertionError(run.stderr)
    return json.loads(run.stdout.strip().splitlines()[-1])


class VeNangCap(unittest.TestCase):
    def test_ban_tieng_anh_ve_duoc_va_giu_dung_loai_hinh(self):
        missing = set()
        js = dich.dich_js(bieu_do_cong_cu.JS, dich.tu_dien('en'), missing)
        self.assertEqual(missing, set())
        r = node(CHAY, js=js)
        self.assertEqual(r['kq']['hcnxoay']['ten'], 'Rotated rectangle')
        self.assertEqual(r['kq']['avwap']['ten'], 'Anchored VWAP · tick volume')
        for key, value in r['kq'].items():
            self.assertNotIn('loi', value, (key, value))
            self.assertTrue(value['ok'], key)

    def test_vwap_hlc3_co_trong_so_tu_diem_neo(self):
        r = node("console.log(JSON.stringify(VNH.tinhVwap([[1,0,12,6,9],[2,0,24,12,18],[3,0,30,18,24]],{1:1,2:3,3:2},2)))")
        self.assertEqual(r['loi'], '')
        self.assertEqual(r['ds'][0], [2, 18])
        self.assertAlmostEqual(r['ds'][1][1], (18 * 3 + 24 * 2) / 5)

    def test_vwap_khong_gia_lap_volume_va_khong_dung_nen_tuong_lai(self):
        r = node("""
const cs=[[1,0,12,6,9],[2,0,24,12,18]];
console.log(JSON.stringify([
 VNH.tinhVwap(cs,{1:1},1),VNH.tinhVwap(cs,{1:1,2:NaN},1),
 VNH.tinhVwap(cs,{1:1,2:-1},1),VNH.tinhVwap(cs,{1:0,2:0},1),
 VNH.tinhVwap(cs,{1:1,2:3},0),VNH.tinhVwap(cs,{1:1,2:3},3),
 VNH.tinhVwap(cs.slice(0,1),{1:1,2:999},1)]));
""")
        for bad in r[:6]:
            self.assertEqual(bad['ds'], [])
            self.assertTrue(bad['loi'])
        self.assertEqual(r[-1]['ds'], [[1, 9]])

    def test_vwap_bo_qua_nen_volume_khong(self):
        r = node("console.log(JSON.stringify(VNH.tinhVwap([[1,0,12,6,9],[2,0,24,12,18]],{1:0,2:3},1)))")
        self.assertEqual(r['ds'], [[2, 18]])

    def test_vwap_tren_chart_bo_nen_dang_chay_chua_co_volume(self):
        r = node("""
C.cs=[[1,0,12,6,9],[2,0,24,12,18],[3,0,30,18,24]];C.vol={1:1,2:3};C.live=2;
const ps=[],labels=[];X.moveTo=(...p)=>ps.push(p);X.lineTo=(...p)=>ps.push(p);C.chu=t=>labels.push(t);
const h={a:{t:1,p:9}};VEX.avwap.ve(h,C,true,'#f00',10,764);
console.log(JSON.stringify({ps,labels}));
""")
        self.assertEqual(len(r['ps']), 2)
        self.assertAlmostEqual(r['ps'][-1][1], (200 - (9 + 18 * 3) / 4) * 4)
        self.assertIn('nến đóng', r['labels'][0])

    def test_cung_tron_di_qua_diem_dieu_khien(self):
        r = node("""
const ps=[];X.moveTo=(...p)=>ps.push(p);X.lineTo=(...p)=>ps.push(p);
const h={a:{t:10,p:100},b:{t:30,p:100},c:{t:20,p:125}};
const g=VEX.cung.ve(h,C,true,'#f00',100,400,300,400);
console.log(JSON.stringify({first:ps[0],last:ps.at(-1),mid:ps[48],hit:g.trong(200,300),outside:g.trong(200,440)}));
""")
        for a, b in zip(r['first'], [100, 400]):
            self.assertAlmostEqual(a, b)
        for a, b in zip(r['last'], [300, 400]):
            self.assertAlmostEqual(a, b)
        for a, b in zip(r['mid'], [200, 300]):
            self.assertAlmostEqual(a, b)
        self.assertTrue(r['hit'])
        self.assertFalse(r['outside'])

    def test_chu_nhat_xoay_co_goc_vuong(self):
        r = node("""
const ps=[];X.moveTo=(...p)=>ps.push(p);X.lineTo=(...p)=>ps.push(p);
const h={a:{t:10,p:100},b:{t:30,p:120},c:{t:25,p:90}};
VEX.hcnxoay.ve(h,C,true,'#f00',100,400,300,320);
console.log(JSON.stringify(ps));
""")
        self.assertEqual(len(r), 4)
        u = [r[1][i] - r[0][i] for i in (0, 1)]
        v = [r[2][i] - r[1][i] for i in (0, 1)]
        self.assertAlmostEqual(sum(a * b for a, b in zip(u, v)), 0)

    def test_chu_ky_neo_ngoai_man_hinh_van_xuat_hien(self):
        r = node("""
C.ts.getVisibleLogicalRange=()=>({from:100,to:110});
const h={a:{t:0,p:100},b:{t:5,p:100}};
const a=VEX.chuky.ve(h,C,true,'#f00',0,400,50,400);
const b=VEX.chukynen.ve(h,C,true,'#f00',0,400,50,400);
console.log(JSON.stringify([a.trong(1000.5,20),b.trong(1000,20)]));
""")
        self.assertEqual(r, [True, True])

    def test_hinh_khoa_khong_bi_xoa_bang_thanh_cong_cu(self):
        fn = re.search(r'function veDuoc\(\)\{.*?\}\n', bieu_do.JS).group() + re.search(r'function veXoa\(\)\{.*?\}\n', bieu_do.JS).group()
        r = node("""
let saved=0;const veLuu=()=>saved++,veTb=()=>{},lwPhu=()=>{};
VE.ds=[{id:'locked',khoa:1},{id:'open'}];VE.chon='locked';
""" + fn + """
veXoa();const locked={ds:VE.ds.slice(),saved};VE.chon='open';veXoa();
console.log(JSON.stringify({locked,ds:VE.ds,saved}));
""")
        self.assertEqual(len(r['locked']['ds']), 2)
        self.assertEqual(r['locked']['saved'], 0)
        self.assertEqual(r['ds'], [{'id': 'locked', 'khoa': 1}])
        self.assertEqual(r['saved'], 1)

    def test_cong_cu_moi_luu_va_doc_lai_duoc(self):
        keys = ('avwap', 'fibnem', 'pitchfan', 'hcnxoay', 'cung', 'congkep', 'dagiac', 'muitrai', 'muiphai', 'chukynen', 'vungquat')
        ds = [{'id': 'upgrade_' + k, 'k': k, 'a': {'t': 100, 'p': 200},
               'b': {'t': 200, 'p': 210}, 'c': {'t': 150, 'p': 230},
               'pts': [{'t': 100 + i, 'p': 200 + i} for i in range(4)]} for k in keys]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hinh_ve.luu('XAUUSDp', ds, goc=root)
            self.assertEqual(hinh_ve.doc('XAUUSDp', goc=root)['ds'], ds)


if __name__ == '__main__':
    unittest.main()
