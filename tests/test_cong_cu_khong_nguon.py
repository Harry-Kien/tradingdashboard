"""Công cụ thuần số vẫn dùng được khi không có giá/thông số MT5."""
import unittest

from so_cong_khai import cong_cu, thi_truong_trang
from test_chart_pro import node

HARNESS = r"""
const els={},callbacks=[],defaults={'von':'1000','rr-pct':'1','fb-cao':'4000','fb-thap':'3900','rk-vao':'100','rk-sl':'90','rk-tp':'120','fb-w':'50','ct-n':'2','ct-m':'3'};
const el=id=>els[id]||(els[id]={id,value:defaults[id]||'',innerHTML:'',dataset:{},options:[],checked:false,handlers:[],addEventListener(k,f){if(k==='input')this.handlers.push(f)},querySelectorAll:()=>[]});
window.document={activeElement:null,querySelector:s=>el(s.slice(1)),querySelectorAll:s=>s==='.cc input'?Object.keys(defaults).map(el):[]};
window.location={search:''};window.localStorage={getItem:()=>null,setItem(){}};
window.TT={esc:String,fmt:(v,d=2)=>v==null?'—':Number(v).toFixed(d),pct:v=>v+'%',cls:v=>v>=0?'gain':'loss',S:{},by:()=>new Map(),nhomOpt:()=>'',pill(){},on:f=>callbacks.push(f),batDau(){for(const f of callbacks)f('anh',[]);return Promise.resolve({})}};
JS_CODE
const change=(id,value)=>{const e=el(id);e.value=String(value);for(const f of e.handlers)f()};
TEST_CODE
"""


def run(code):
    return node(HARNESS.replace('JS_CODE', cong_cu.JS).replace('TEST_CODE', code))


class OfflineCalculators(unittest.TestCase):
    def test_fibonacci_rr_va_chuoi_thua_tinh_duoc_khi_khong_co_ma(self):
        r = run("console.log(JSON.stringify({fib:el('fb-kq').innerHTML,rr:el('rk-kq').innerHTML,ct:el('ct-kq').innerHTML}));")
        self.assertIn('3976.40000', r['fib'])
        self.assertIn('1 : 2.00', r['rr'])
        self.assertIn('37.5%', r['ct'])  # LLW, WLL và LLL trong 8 chuỗi độc lập
        self.assertIn('98.0% vốn', r['ct'])

    def test_sl_tp_cung_phia_khong_duoc_bao_rr_hap_dan(self):
        r = run("change('rk-sl',110);console.log(JSON.stringify(el('rk-kq').innerHTML));")
        self.assertIn('hai phía khác nhau', r)
        self.assertNotIn('Kỳ vọng mỗi lệnh', r)

    def test_chuoi_dai_hon_tong_so_lenh_co_xac_suat_0(self):
        r = run("change('ct-n',5);console.log(JSON.stringify(el('ct-kq').innerHTML));")
        self.assertIn('0.0%', r)
        self.assertIn('trong 3 lệnh', r)

    def test_chan_dau_vao_rat_lon_khong_cap_phat_mang_vo_han(self):
        r = run("change('ct-n',1000000000);console.log(JSON.stringify(el('ct-kq').innerHTML));")
        self.assertIn('1–500', r)

    def test_tyle_thang_ngoai_0100_khong_duoc_tinh_ky_vong(self):
        r = run("change('fb-w',120);console.log(JSON.stringify({rr:el('rk-kq').innerHTML,ct:el('ct-kq').innerHTML}));")
        self.assertNotIn('Kỳ vọng mỗi lệnh', r['rr'])
        self.assertIn('tỷ lệ thắng 0–100%', r['ct'])

    def test_khong_mo_luong_gia_khi_phan_thi_truong_tat(self):
        source = thi_truong_trang.JS_CHUNG
        # Hàm batDau có hai dòng; dùng phần kế tiếp làm ranh giới thay vì cắt mất callback.
        start, end = source.index('function batDau('), source.index('function pill(')
        functions = source[start:end]
        result = node("""
let opened=0,disabled=true,started=null,refresh=null;const tai=async()=>({tat:disabled}),noi=()=>opened++,document={visibilityState:'visible',addEventListener:()=>{}},setInterval=f=>{refresh=f},addEventListener=()=>{};let tt={};const phat=()=>{};
""" + functions + """
(async()=>{await batDau();const off=opened;disabled=false;await batDau();if(opened!==off)throw Error('Repeated start opened another stream');await refresh();console.log(JSON.stringify({off,on:opened}))})();
""")
        self.assertEqual(result, {'off': 0, 'on': 1})


if __name__ == '__main__':
    unittest.main()
