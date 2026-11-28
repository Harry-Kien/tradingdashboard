"""Kiểm chi phí mô phỏng và khôi phục bất đồng bộ bằng JavaScript thật."""
import unittest

from so_cong_khai import bieu_do_phat_lai, dich, replay_chi_phi
from test_chart_pro import function, node
from test_chart_dong_bo import item, run
from test_revue_complete import replay


def model(code):
    return node(replay_chi_phi.JS + code)


class ReplayCosts(unittest.TestCase):
    def test_replay_tieng_anh_khong_sot_cac_doan_giao_dien_moi(self):
        missing = set()
        dich.dich_js(bieu_do_phat_lai.JS, dich.tu_dien('en'), missing)
        self.assertEqual(missing, set())

    def test_khong_chi_phi_giu_dung_r_cu(self):
        r = model("const l=CPPL.vao(100,1,10,1,2,{});console.log(JSON.stringify(CPPL.dong(l,120)));")
        self.assertEqual((r['r'], r['r_goc'], r['chi_phi_r']), (2, 2, 0))

    def test_gia_khong_doi_hai_chieu_deu_mat_spread_hai_lan_truot_va_phi(self):
        r = model("console.log(JSON.stringify([0,1].map(d=>CPPL.dong(CPPL.vao(100,d,10,1,2,{spread:2,slip:1,phi_r:.05}),100))));")
        for x in r:
            self.assertAlmostEqual(x['r'], -.45)
            self.assertAlmostEqual(x['r_truoc_phi'], -.4)
            self.assertAlmostEqual(x['r_goc'] - x['chi_phi_r'], x['r'])

    def test_ban_sl_dung_ask_truoc_khi_bid_cham(self):
        r = model("const l=CPPL.vao(100,0,10,1,2,{spread:2});console.log(JSON.stringify(CPPL.kiem(l,[1,100,108,99,102])));")
        self.assertEqual(r, {'gia_bid': 108, 'ly': 'SL'})

    def test_ban_tp_khong_khop_khi_chi_bid_cham(self):
        r = model("const l=CPPL.vao(100,0,10,1,2,{spread:2});console.log(JSON.stringify(CPPL.kiem(l,[1,95,100,80,90])));")
        self.assertIsNone(r)

    def test_gap_tp_duoc_xet_truoc_sl_trong_nen(self):
        r = model("const l=CPPL.vao(100,1,10,1,2,{spread:2,slip:1});console.log(JSON.stringify(CPPL.kiem(l,[1,125,130,80,100])));")
        self.assertEqual(r, {'gia_bid': 125, 'ly': 'TP'})

    def test_cham_hai_moc_khong_biet_thu_tu_tinh_sl_truoc(self):
        r = model("const l=CPPL.vao(100,1,10,1,2,{spread:2});console.log(JSON.stringify(CPPL.kiem(l,[1,100,125,80,105])));")
        self.assertEqual(r, {'gia_bid': 92, 'ly': 'SL'})

    def test_phi_cua_lenh_la_ban_chup_khong_doi_theo_cau_hinh_moi(self):
        r = model("const c={spread:2,slip:1,phi_r:.05},l=CPPL.vao(100,1,10,1,2,c);c.spread=50;console.log(JSON.stringify(CPPL.dong(l,100)));")
        self.assertAlmostEqual(r['r'], -.45)

    def test_chi_phi_am_vo_cuc_null_va_khoang_sl_qua_nho_bi_chan(self):
        r = model("console.log(JSON.stringify([null,[],{slip:-1},{spread:Infinity},{phi_r:NaN},{phi_r:101}].map(CPPL.chiPhi).concat([CPPL.vao(100,1,10,1,2,{spread:10})])));")
        self.assertEqual(r, [None] * 7)

    def test_replay_tich_hop_tinh_rong_va_luu_tom_tat_co_phien_ban(self):
        r = replay("CBPL.batDau(200);CBPL.vao(1);CBPL.dong(4000,1,'Tay');const trade=CBPL.PL.ds[0];CBPL.thoat(false);console.log(JSON.stringify({trade,saved}));",
                   "let saved;localStorage.getItem=()=>JSON.stringify({chi_phi:{spread:2,slip:1,phi_r:.05}});localStorage.setItem=(k,v)=>{saved=JSON.parse(v)};")
        self.assertAlmostEqual(r['trade']['r'], -(4 / 15 + .05))
        self.assertEqual(r['saved']['so'][0]['thang'], 0)
        self.assertEqual(r['saved']['so'][0]['mo_hinh'], 'bid-ask-cost-v1')
        self.assertAlmostEqual(r['saved']['so'][0]['chi_phi_r'], 4 / 15 + .05)

    def test_replay_ho_so_chi_phi_null_khong_lam_hong_khoi_dong(self):
        r = replay("CBPL.batDau(200);CBPL.vao(1);console.log(JSON.stringify(CBPL.PL.lenh.chi_phi));", "localStorage.getItem=()=>JSON.stringify({chi_phi:null});")
        self.assertEqual(r, {'spread': 0, 'slip': 0, 'phi_r': 0})

    def test_bam_mua_doc_truc_tiep_chi_phi_vua_nhap_chua_blur(self):
        r = replay("CBPL.batDau(200);CBPL.vao(1);console.log(JSON.stringify(CBPL.PL.lenh.chi_phi));", """
document.createElement=()=>{const e=el();e.querySelectorAll=s=>s==='[data-cost]'?[{dataset:{cost:'spread'},value:'0.2'},{dataset:{cost:'slip'},value:'0.05'},{dataset:{cost:'phi_r'},value:'0.05'}]:[];return e};
""")
        self.assertEqual(r, {'spread': .2, 'slip': .05, 'phi_r': .05})

    def test_o_chi_phi_rong_khong_duoc_am_tham_tinh_bang_khong(self):
        r = replay("CBPL.batDau(200);CBPL.vao(1);console.log(JSON.stringify(CBPL.PL.lenh));", """
document.createElement=()=>{const e=el();e.querySelectorAll=s=>s==='[data-cost]'?[{dataset:{cost:'spread'},value:''}]:[];return e};
""")
        self.assertIsNone(r)


class RestoreLock(unittest.TestCase):
    def test_khoa_chinh_sua_dung_ham_chart_thuc(self):
        r = node(function('veDuoc') + "window.HVD_CHO_VE=()=>true;window.HVD_KHOI_PHUC=true;const a=veDuoc();window.HVD_KHOI_PHUC=false;console.log(JSON.stringify([a,veDuoc()]));")
        self.assertEqual(r, [False, True])

    def test_khong_vao_replay_khi_dang_khoi_phuc(self):
        self.assertEqual(replay("HVD_KHOI_PHUC=true;CBPL.batDau(200);console.log(JSON.stringify(CBPL.PL.on));"), 0)

    def test_khoi_phuc_cho_phan_hoi_khoa_gui_va_cam_lap_thao_tac(self):
        r = run([item()], [item()], [item()], """
const original=fetch;let release;fetch=async(u,o={})=>{const b=o.body&&JSON.parse(o.body);if(b&&b.viec==='khoi_phuc'){await new Promise(r=>release=r);return{ok:true,json:async()=>({ok:true,chu:uid,ban:4,ds:[{...A,a:{t:1,p:3400}}]})}}return original(u,o)};
const task=HVD.khoiPhuc(1);await settle();const locked=HVD_KHOI_PHUC,send=await HVD.gui();let duplicate=false;try{await HVD.khoiPhuc(1)}catch(e){duplicate=true}release();await task;
console.log(JSON.stringify({locked,send,duplicate,done:HVD_KHOI_PHUC,ds:VE.ds,paint:statuses.some(x=>x[0]==='restoring')}));
""")
        self.assertEqual([r[k] for k in ('locked', 'send', 'duplicate', 'done', 'paint')], [True, False, True, False, True])
        self.assertEqual(r['ds'][0]['a']['p'], 3400)

    def test_mat_mang_van_mo_khoa_va_giu_ban_hien_tai(self):
        r = run([item()], [item()], [item()], """
const original=fetch;fetch=async(u,o={})=>{if(o.body&&JSON.parse(o.body).viec==='khoi_phuc')throw Error('offline');return original(u,o)};
let error=false;try{await HVD.khoiPhuc(1)}catch(e){error=true}console.log(JSON.stringify({error,locked:HVD_KHOI_PHUC,ds:VE.ds}));
""")
        self.assertEqual(r, {'error': True, 'locked': False, 'ds': [item()]})

    def test_phan_hoi_doi_tai_khoan_khong_duoc_ap_len_chart(self):
        r = run([item()], [item()], [item()], """
const original=fetch;fetch=async(u,o={})=>{if(o.body&&JSON.parse(o.body).viec==='khoi_phuc')return{ok:true,json:async()=>({ok:true,chu:'other',ban:4,ds:[B]})};return original(u,o)};
try{await HVD.khoiPhuc(1)}catch(e){}console.log(JSON.stringify({locked:HVD_KHOI_PHUC,ds:VE.ds,status:statuses.at(-1)[0]}));
""")
        self.assertEqual(r, {'locked': False, 'ds': [item()], 'status': 'error'})

    def test_503_khong_co_chu_khong_bi_nham_la_doi_tai_khoan(self):
        r = run([item()], [item()], [item()], """
const original=fetch;fetch=async(u,o={})=>{if(o.body&&JSON.parse(o.body).viec==='khoi_phuc')return{ok:false,status:503,json:async()=>({ok:false,ly_do:'unavailable'})};return original(u,o)};
let error=false;try{await HVD.khoiPhuc(1)}catch(e){error=true}console.log(JSON.stringify({error,locked:HVD_KHOI_PHUC,retry:await HVD.gui(),ds:VE.ds}));
""")
        self.assertEqual(r, {'error': True, 'locked': False, 'retry': True, 'ds': [item()]})

    def test_409_khong_co_chu_duoc_ghep_va_tiep_tuc_dong_bo(self):
        r = run([item()], [item()], [item()], """
const original=fetch;fetch=async(u,o={})=>{if(o.body&&JSON.parse(o.body).viec==='khoi_phuc'){server.XAUUSDp={ban:4,ds:[{...A,a:{t:1,p:3400}}]};return{ok:false,status:409,json:async()=>({ok:false,xung_dot:true,...server.XAUUSDp})}}return original(u,o)};
let error=false;try{await HVD.khoiPhuc(1)}catch(e){error=true}console.log(JSON.stringify({error,locked:HVD_KHOI_PHUC,retry:await HVD.gui(),ds:VE.ds}));
""")
        self.assertEqual(r, {'error': True, 'locked': False, 'retry': True, 'ds': [item(p=3400)]})

    def test_thay_doi_vuot_qua_ui_van_khong_bi_phan_hoi_cu_ghi_de(self):
        r = run([item()], [item()], [item()], """
const original=fetch;fetch=async(u,o={})=>{if(o.body&&JSON.parse(o.body).viec==='khoi_phuc'){draft([{...A,a:{t:1,p:3550}},B]);return{ok:true,json:async()=>({ok:true,chu:uid,ban:4,ds:[{...A,a:{t:1,p:3400}}]})}}return original(u,o)};
let error=false;try{await HVD.khoiPhuc(1)}catch(e){error=true}console.log(JSON.stringify({error,locked:HVD_KHOI_PHUC,ds:VE.ds,status:statuses.at(-1)[0]}));
""")
        self.assertTrue(r['error'])
        self.assertFalse(r['locked'])
        self.assertEqual(r['ds'], [item(p=3550), {'id': 'b', 'k': 'ngang', 'a': {'t': 2, 'p': 3600}}])
        self.assertEqual(r['status'], 'conflict')
