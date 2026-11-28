"""Kết quả phân tích mới phải tới giao diện, và không lọt vào mã khác hoặc phát lại nến."""
import json
import shutil
import subprocess
import unittest

from so_cong_khai import bieu_do


NODE = shutil.which('node')


@unittest.skipUnless(NODE, 'máy không có Node.js')
class PhanTichRealtime(unittest.TestCase):
    def test_nhanh_theo_yeu_cau_khong_muon_so_do_cua_nhanh_cho_nen(self):
        src = bieu_do.JS
        key = src[src.index('function hocKhoa('):src.index('function hocHtml(')]
        score = src[src.index('function diem('):src.index('function daiDat(')]
        js = "const PTR={boi_canh:{}},HOC={san_sang:true,luat:{bot:{theo:{BAN:{nhan_xet:'giu'}}}}};" + key + score
        js += "console.log(JSON.stringify(['bot:nen','bot:xu_huong'].map(ma=>diem({ma,co:true,huong:'BAN'}))));"
        r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(r.returncode, 0, r.stderr)
        a, b = json.loads(r.stdout)
        self.assertEqual(a['ma'], 'giu')
        self.assertIsNone(b)

    def chay(self, tu=0, doi_ma=False, phat_lai=False, da_phat_lai=False, quay_lai=False, doi_khung=False):
        dau = bieu_do.JS.index('// --- Đợt 0:')                              # gồm khối độ tươi phân tích (PTR_GOC, ptApDung, ptDoi) ngay trước ptTai
        bieu_do.JS.index('let ptDang=0,ptCho=0,ptLan=0;async function ptTai', dau)
        cuoi = bieu_do.JS.index("$('#pt-btn').addEventListener", dau)
        ca = json.dumps({'tu': tu, 'doiMa': doi_ma, 'phatLai': phat_lai, 'daPhatLai': da_phat_lai, 'quayLai': quay_lai, 'doiKhung': doi_khung})
        js = 'const ca=' + ca + ';\n' + r"""
let PTR={marker:'old'},ma='XAUUSD',planTat=1,plan=null,ppChon='tat',ppMuc='',view={},LW=null,tf='M15';
let KC={san_sang:true},HOC={san_sang:true},window={BDPL:{chan:ca.daPhatLai}};
const BDPL=window.BDPL;let chartEpoch=0;
let PTB={hidden:false,innerHTML:''},renders=[],requests=0,draws=0;
const response={marker:'fresh',phuong_phap:[],phuong_an:[]};
const button={disabled:false,textContent:'',setAttribute(){},removeAttribute(){}};
const localStorage={getItem:()=>null,setItem(){}};
const $=s=>button;
const fetch=async()=>{requests++;if(ca.doiKhung)tf='M30';if(ca.doiMa)ma='EURUSD';if(ca.phatLai)window.BDPL.chan=true;if(ca.quayLai)chartEpoch+=2;
 return {ok:true,json:async()=>response}};
const ppNhom=()=>[],ptDs=()=>[],totNhat=()=>null,ppTot=()=>null;
const bat=()=>true,ppKhoa=()=>'',draw=()=>{draws++},dvKiem=()=>{},nkTai=()=>{};
const kcTai=()=>{},hocTai=()=>{},hep=()=>false,fsOn=()=>false,lwNay=()=>{};
const ptVe=()=>renders.push(PTR.marker),esc=x=>String(x),dvVe=()=>{};
const _el=()=>({className:'',textContent:'',setAttribute(){},before(){},after(){}});
const document={createElement:_el,querySelector:()=>_el(),getElementById:()=>_el(),addEventListener(){},head:{insertAdjacentHTML(){}}};
const addEventListener=()=>{},setInterval=()=>{},matchMedia=()=>({matches:false});
""" + bieu_do.JS[dau:cuoi] + r"""
ptTai(ca.tu).then(()=>process.stdout.write(JSON.stringify({marker:PTR.marker,renders,requests,draws,
 enabled:!button.disabled,busy:ptDang}))).catch(e=>{console.error(e);process.exitCode=1});
"""
        r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_bam_phan_tich_hien_ket_qua_moi(self):
        r = self.chay()
        self.assertEqual(r['marker'], 'fresh')
        self.assertEqual(r['renders'], ['fresh'])
        self.assertEqual((r['requests'], r['draws'], r['enabled'], r['busy']), (1, 1, True, 0))

    def test_quay_lai_cung_ma_van_loai_phan_hoi_cua_lan_chon_truoc(self):
        r = self.chay(quay_lai=True)
        self.assertEqual(r['marker'], 'old')
        self.assertEqual(r['draws'], 0)

    def test_tu_dong_cap_nhat_ket_qua_moi(self):
        r = self.chay(tu=1)
        self.assertEqual((r['marker'], r['renders'], r['draws']), ('fresh', ['fresh'], 1))

    def test_doi_ma_khong_nhan_ket_qua_ma_cu(self):
        r = self.chay(doi_ma=True)
        self.assertEqual((r['marker'], r['renders'], r['draws']), ('old', [], 0))
        self.assertEqual((r['enabled'], r['busy']), (True, 0))

    def test_doi_khung_phan_tich_khong_nhan_ket_qua_cu(self):
        r = self.chay(doi_khung=True)
        self.assertEqual((r['marker'], r['renders'], r['draws']), ('old', [], 0))
        self.assertEqual((r['enabled'], r['busy']), (True, 0))

    def test_vao_phat_lai_khi_dang_cho_khong_ve_gia_hien_tai(self):
        r = self.chay(phat_lai=True)
        self.assertEqual((r['marker'], r['renders'], r['draws']), ('old', [], 0))
        self.assertEqual((r['enabled'], r['busy']), (True, 0))

    def test_dang_phat_lai_khong_goi_api(self):
        r = self.chay(da_phat_lai=True)
        self.assertEqual((r['marker'], r['requests'], r['draws']), ('old', 0, 0))


if __name__ == '__main__':
    unittest.main()
