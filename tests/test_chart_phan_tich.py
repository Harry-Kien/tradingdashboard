"""Mật độ chỉ thay trình bày: giữ giá SL/TP và trạng thái phương án."""
import unittest

from so_cong_khai import bieu_do, chart_phan_tich, dich
from test_chart_pro import node

VO = r'''
let changed,paint=0;const saved={},select={value:'',addEventListener:(n,f)=>changed=f},parts={},panel={hidden:true,innerHTML:'',textContent:''};
const bar={hidden:true,querySelector:s=>parts[s]||(parts[s]={dataset:{},events:{},setAttribute(k,v){this[k]=v},addEventListener(k,f){this.events[k]=f}})};
globalThis.localStorage={getItem:()=>MODE,setItem:(k,v)=>saved[k]=v};
globalThis.document={getElementById:k=>k==='pt-density'?select:k==='pt-levels'?panel:null,querySelector:s=>s==='.pt-current'?bar:null};
'''


def run(code, mode=None):
    import json  # noqa: PLC0415
    return node(VO.replace('MODE', json.dumps(mode)) + chart_phan_tich.JS + code)


class Presentation(unittest.TestCase):
    def test_mac_dinh_tinh_gon_va_doi_che_do_duoc_luu(self):
        r = run("const first=PTUI.gon();PTUI.onChange=()=>paint++;select.value='du';changed();console.log(JSON.stringify({first,after:PTUI.gon(),saved,paint}));")
        self.assertEqual(r, {'first': True, 'after': False, 'saved': {'so-nhan-phan-tich': 'du'}, 'paint': 1})

    def test_nho_lai_che_do_chi_tiet(self):
        self.assertFalse(run('console.log(JSON.stringify(PTUI.gon()));', 'du'))

    def test_khong_cho_chon_mat_do_khi_dang_dung_canvas_du_phong(self):
        self.assertTrue(run('PTUI.paint(null,true,false);console.log(JSON.stringify(select.disabled));'))

    def test_mo_muc_gia_giu_dung_so_le_va_r_khong_sua_phuong_an(self):
        r = run("const p={huong:'MUA',ten:'A',vao:.12345,sl:.12,tp:[.125,.13],rr:[.5,2],hieu_luc:true,kieu:'Lệnh chờ'},before=JSON.stringify(p);PTUI.paint(p,false,true,v=>v.toFixed(5));const hidden=panel.hidden;parts['.pt-level-toggle'].events.click();console.log(JSON.stringify({hidden,opened:!panel.hidden,html:panel.innerHTML,same:before===JSON.stringify(p)}));")
        self.assertTrue(r['hidden'])
        self.assertTrue(r['opened'])
        self.assertTrue(r['same'])
        for value in ('0.12345', '0.12000', '0.12500', '0.13000', '0,5R', '2R'):
            self.assertIn(value, r['html'])

    def test_doi_gia_cung_phuong_phap_van_cap_nhat_bang(self):
        r = run("const p={ten:'A',huong:'MUA',vao:100,sl:90,tp:[120]};PTUI.paint(p,false);p.vao=101;PTUI.paint(p,false);console.log(JSON.stringify(panel.innerHTML));")
        self.assertIn('101', r)

    def test_replay_an_ca_bang_gia_dang_mo(self):
        r = run("PTUI.paint({huong:'MUA',vao:100,sl:90,tp:[120]},false);parts['.pt-level-toggle'].events.click();PTUI.paint(null,true);console.log(JSON.stringify({hidden:panel.hidden,closed:parts['.pt-level-toggle']['aria-expanded'],cleared:panel.textContent}));")
        self.assertEqual(r, {'hidden': True, 'closed': 'false', 'cleared': ''})

    def test_muc_gia_thieu_va_ly_do_het_hieu_luc_khong_bi_bo_qua(self):
        r = run("PTUI.paint({huong:'MUA',vao:100,sl:NaN,tp:[],hieu_luc:false,vi_sao_het:['Giá đã qua điểm vào <script>alert(1)</script>']},false);console.log(JSON.stringify(panel.innerHTML));")
        self.assertIn('Chưa đủ mức giá', r)
        self.assertIn('&lt;script&gt;', r)
        self.assertNotIn('<script>', r)

    def test_vung_mau_gioi_han_trong_plot_ke_ca_man_hinh_hep(self):
        for width in (80, 300, 1200):
            for x in (-50, 30, 1500):
                a, b = run(f'console.log(JSON.stringify(PTUI.mien({x},{width})));')
                self.assertLessEqual(0, a)
                self.assertLessEqual(a, b)
                self.assertLessEqual(b, width)
                self.assertLessEqual(b - a, 320)

    def test_fvg_chon_gan_nhat_moi_phia_khong_sua_du_lieu_goc(self):
        r = run("const fs=[{duoi:99,tren:101},{duoi:102,tren:103},{duoi:104,tren:105},{duoi:96,tren:97},{duoi:94,tren:95}],before=JSON.stringify(fs);console.log(JSON.stringify({ds:PTUI.fvg(fs,100),same:before===JSON.stringify(fs)}));")
        self.assertTrue(r['same'])
        self.assertEqual(r['ds'], [{'duoi': 99, 'tren': 101}, {'duoi': 102, 'tren': 103}, {'duoi': 96, 'tren': 97}])

    def test_qua_han_va_tham_khao_khong_hien_con_hieu_luc(self):
        r = run("const out=[];for(const p of [{huong:'MUA',ten:'A',cu:true,hieu_luc:true},{huong:'BÁN',ten:'B',hieu_luc:false},{huong:'MUA',ten:'C'}]){const s=JSON.stringify(p);PTUI.paint(p,false);out.push([parts['.pt-validity'].textContent,s===JSON.stringify(p)])}PTUI.paint(null,true);console.log(JSON.stringify({out,hidden:bar.hidden}));")
        self.assertEqual(r, {'out': [['Đã quá hạn', True], ['Chỉ tham khảo', True], ['Chưa xác định hiệu lực', True]], 'hidden': True})

    def test_duong_gia_thuc_giu_nguyen_muc_gia_va_the_gia(self):
        a = bieu_do.JS.index(' const ngang=')
        b = bieu_do.JS.index('\n else{const tkv=', a)
        js = bieu_do.JS[a:b]
        for mode in (None, 'du'):
            r = run("const lines=[],gon=PTUI.gon(),TRONG=false,on={},D={},plan={vao:100,sl:95,tp:[105,110],rr:[1,2],huong:'MUA',rui_ro_gia:5},P={vao:'#08ffb5',sl:'#ff5a5f',tp:'#8dff08'},LW={lines:[],nen:{createPriceLine:x=>(lines.push(x),x)}},fp=String,f2=String;" + js + '\nconsole.log(JSON.stringify(lines));', mode)
            self.assertEqual([x['price'] for x in r], [100, 95, 105, 110])
            self.assertTrue(all(x['axisLabelVisible'] for x in r))
            self.assertTrue(all(x['lineVisible'] == (mode == 'du') for x in r))

    def test_giao_dien_moi_dich_day_du_sang_tieng_anh(self):
        missing = set()
        d = dich.tu_dien('en')
        dich.dich_html(chart_phan_tich.HTML, d, missing)
        dich.dich_js(chart_phan_tich.JS, d, missing)
        self.assertEqual(missing, set())

    def test_lop_canvas_thuc_tinh_gon_khong_lap_nhan_vao_ra_va_vung_mau_nhe(self):
        a = bieu_do.JS.index('function lwPhu(){')
        b = bieu_do.JS.index('if(window.PTUI)PTUI.onChange=', a)
        setup = r'''
const noop=()=>{},labels=[],fills=[],X=new Proxy({measureText:t=>({width:t.length*6}),fillText:t=>labels.push(t),fillRect:(x,y,w,h)=>fills.push({w,a:X.globalAlpha})},{get:(o,k)=>k in o?o[k]:noop});
const D={candles:[[1,100,102,99,100],[901,100,102,99,100]]},LWE={clientWidth:800,clientHeight:500},LWO={width:800,height:500,style:{},getContext:()=>X};
const LW={nen:{priceToCoordinate:v=>250-(v-100)*5},chart:{priceScale:()=>({width:()=>64}),panes:()=>[{getHeight:()=>450}],timeScale:()=>({logicalToCoordinate:i=>100+i*5})}};
const P={bg:'#101010',fg:'#dddddd',tp:'#8dff08',sl:'#ff5a5f',vao:'#08ffb5',mute:'#999999'},pal=()=>P,dtNen=()=>900,veVe=noop,ictOn=()=>false,fp=String,f2=String,esc=String;
const on={},TRONG=false,ANH=false,TK=null,PTR=null,KC=null,kieu='toi',HIT=[],kcHien=null;
const plan={huong:'MUA',ten:'Method',vao:100,sl:95,tp:[105,110],rr:[1,2]},before=JSON.stringify(plan);
'''
        for mode in (None, 'du'):
            r = run(setup + bieu_do.JS[a:b] + "lwPhu();console.log(JSON.stringify({labels,fills,same:before===JSON.stringify(plan)}));", mode)
            self.assertTrue(r['same'])
            self.assertEqual(any('Ra ·' in x for x in r['labels']), mode == 'du')
            if mode is None:
                self.assertTrue(all(x['a'] <= .075 and x['w'] <= 320 for x in r['fills']))
