"""Rà soát luồng thực: cạnh tranh ghi mẫu, cách ly cảnh báo và replay."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from so_cong_khai import bieu_do_phat_lai, canh_bao_ve as cbv, mau_chi_bao as mcb
from so_cong_khai import loi_nghiep_vu, web
import test_chart_auth_http as auth_http
from test_chart_pro import node
from test_phat_lai import VO


class TemplateStore(unittest.TestCase):
    def test_hai_nguoi_ghi_cung_ban_chi_mot_ban_thanh_cong(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mcb.luu({'A': []}, [], root, ban_co_so=None)
            mcb.luu({'A': [{'k': 'ema'}]}, [], root, ban_co_so=1)
            with self.assertRaises(mcb.XungDot) as cm:
                mcb.luu({'B': []}, [], root, ban_co_so=1)
            self.assertEqual(cm.exception.hien_tai['ban'], 2)
            self.assertIn('A', mcb.doc(root)['mau'])

    def test_kho_hong_khong_bi_thay_bang_kho_rong(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mcb.luu({'A': []}, [], root)
            p = root / 'du-lieu/mau-chi-bao.json'
            p.write_text('{bad', encoding='utf-8')
            with self.assertRaises(mcb.KhoLoi):
                mcb.luu({}, [], root)
            self.assertEqual(p.read_text(encoding='utf-8'), '{bad')

    def test_ghep_mau_doc_lap_va_favorites(self):
        r = node(mcb.JS.split('const U=')[0] + """
const b={mau:{A:[]},sao:['ema']},l={mau:{A:[],B:[]},sao:[]},r={mau:{A:[],C:[]},sao:['ema','rsi']};
console.log(JSON.stringify(MCB_MERGE(b,l,r)));})();
""")
        self.assertEqual(r, {'mau': {'A': [], 'C': [], 'B': []}, 'sao': ['rsi'], 'conflicts': []})

    def test_cung_ten_khac_noi_dung_giu_ca_hai_khong_de_len_ten_khac(self):
        r = node(mcb.JS.split('const U=')[0] + """
const a={mau:{A:[]},sao:[]},l={mau:{A:[{k:'ema'}],'A (1)':[]},sao:[]},r={mau:{A:[{k:'rsi'}]},sao:[]};
console.log(JSON.stringify(MCB_MERGE(a,l,r,'both')));})();
""")
        self.assertEqual(r['conflicts'], ['A'])
        self.assertEqual(r['mau']['A'], [{'k': 'rsi'}])
        self.assertEqual(r['mau']['A (2)'], [{'k': 'ema'}])


class PlanRouting(unittest.TestCase):
    def test_cham_phieu_dung_ma_khong_lay_nen_xauusd_cho_xaueur(self):
        for symbol, gold in (('XAUEUR', 'XAUUSDp'), ('XAUUSD247', 'XAUUSDp'), ('GOLD.demo', 'GOLD.demo')):
            with mock.patch.object(web.da_ma, 'ma_vang', return_value=gold), mock.patch.object(web.gia, 'goi', return_value={'candles': []}) as g, mock.patch.object(web.da_ma, 'goi', return_value={'candles': []}) as other, mock.patch.object(web.phieu_ke_hoach, 'cham_mo_phong', return_value={'ok': True}):
                self.assertEqual(web._cham_phieu({}, {'theo_doi': True, 'ma': symbol}), {'ok': True})
                self.assertEqual(g.call_count, int(symbol == gold))
                if symbol != gold:
                    self.assertEqual(other.call_args.args[1], symbol)

    def test_snapshot_khong_gui_so_vo_cuc_cho_ai(self):
        for number in (float('inf'), float('-inf'), float('nan'), '1e999'):
            self.assertIsNone(loi_nghiep_vu._so(number))


class AlertStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.a = cbv.kho_rieng('a' * 32, self.root)
        self.b = cbv.kho_rieng('b' * 32, self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_cach_ly_canh_bao_va_id_khong_trung_cung_mili_giay(self):
        payload = {'ma': 'XAUUSDp', 'tf': 'M15', 'loai': 'ngang', 'dk': 'cat_len', 'diem': [[1795700000, 3500]], 'gia_tao': 3490}
        a = cbv.them(payload, self.a, now=1795700000)[2]
        b = cbv.them(payload, self.b, now=1795700000)[2]
        self.assertNotEqual(a['id'], b['id'])
        self.assertFalse(cbv.xoa(a['id'], self.b))
        self.assertEqual(len(cbv.doc(self.a)['ds']), 1)
        self.assertEqual(len(cbv.cac_kho(self.root)), 2)

    def test_kho_canh_bao_hong_khong_tu_xoa(self):
        self.a.thu_muc.mkdir(parents=True)
        p = self.a.thu_muc / cbv.TEP
        p.write_text('{bad', encoding='utf-8')
        with self.assertRaises(ValueError):
            cbv.xoa('x', self.a)
        self.assertEqual(p.read_text(encoding='utf-8'), '{bad')

    def test_noi_telegram_chi_chap_nhan_ma_mot_lan_cua_dung_tai_khoan(self):
        a, b = cbv.tao_ma_noi(self.a, now=1000.9), cbv.tao_ma_noi(self.b, now=1000.9)
        self.assertNotEqual(a['lenh'], b['lenh'])
        reply = {'ok': True, 'result': [{'message': {'text': a['lenh'], 'date': 1001, 'chat': {'id': 12345, 'type': 'private', 'first_name': 'Tester'}, 'from': {'id': 12345}}}]}
        with mock.patch.object(cbv.telegram_nhom, 'token', return_value='test-only'), mock.patch.object(cbv.telegram_nhom, 'cai', return_value={'chat': '-100'}):
            self.assertFalse(cbv.kiem_ma_noi(self.b, goi=lambda *a: reply, now=1002)[0])
            self.assertTrue(cbv.kiem_ma_noi(self.a, goi=lambda *a: reply, now=1002)[0])
            self.assertFalse(cbv.kiem_ma_noi(self.a, goi=lambda *a: reply, now=1003)[0])
        self.assertEqual(cbv.cai(self.a)['chat_rieng'], '12345')
        self.assertEqual(cbv.cai(self.b)['chat_rieng'], '')
        self.assertNotIn('noi_hash', cbv.cai(self.a))

    def test_ma_het_han_nhom_va_tin_forward_khong_duoc_noi(self):
        a = cbv.tao_ma_noi(self.a, now=1000)
        message = {'text': a['lenh'], 'date': 1001, 'chat': {'id': 12345, 'type': 'group'}, 'from': {'id': 12345}}
        with mock.patch.object(cbv.telegram_nhom, 'token', return_value='test-only'):
            self.assertFalse(cbv.kiem_ma_noi(self.a, goi=lambda *a: {'ok': True, 'result': [{'message': message}]}, now=1002)[0])
            message['chat']['type'] = 'private'
            message['forward_origin'] = {'type': 'user'}
            self.assertFalse(cbv.kiem_ma_noi(self.a, goi=lambda *a: {'ok': True, 'result': [{'message': message}]}, now=1002)[0])
            self.assertFalse(cbv.kiem_ma_noi(self.a, now=1601)[0])

    def test_worker_kiem_cac_kho_va_kho_hong_khong_chan_kho_tot(self):
        self.a.thu_muc.mkdir(parents=True)
        (self.a.thu_muc / cbv.TEP).write_text('{bad', encoding='utf-8')
        cbv._ghi({'ds': [], 'da_bao': []}, self.b)
        v = cbv.VongCanhVe(lambda *a: {})
        with mock.patch.object(cbv, 'cac_kho', return_value=[self.a, self.b]), mock.patch.object(cbv.telegram_nhom, '_tep', side_effect=lambda n: self.root / 'du-lieu' / n):
            v.mot_vong()
        self.assertIsNotNone(v.tt['luc'])
        self.assertIn('JSONDecodeError', v.tt['loi'])


class HTTPReview(unittest.TestCase):
    setUp, tearDown = auth_http.ChartHTTP.setUp, auth_http.ChartHTTP.tearDown
    start, stop, req, signup = auth_http.ChartHTTP.start, auth_http.ChartHTTP.stop, auth_http.ChartHTTP.req, auth_http.ChartHTTP.signup

    def test_api_mau_cas_thieu_co_so_va_tab_cu(self):
        uid = self.signup(self.a, 'cas_owner')
        data = {'mau': {'A': []}, 'sao': []}
        self.assertEqual(self.req(self.a, '/api/mau-chi-bao', data, uid)[0], 400)
        data['ban_co_so'] = None
        self.assertEqual(self.req(self.a, '/api/mau-chi-bao', data, uid)[0], 200)
        status, j, _ = self.req(self.a, '/api/mau-chi-bao', data, uid)
        self.assertEqual((status, j['xung_dot'], j['ban']), (409, True, 1))

    def test_api_canh_bao_dang_nhap_cach_ly_va_khong_lo_danh_sach_chat(self):
        path = '/api/canh-bao-ve'
        self.assertEqual(self.req(self.a, path)[0], 401)
        a, b = self.signup(self.a, 'alert_alpha'), self.signup(self.b, 'alert_beta')
        yc = {'viec': 'them', 'ma': 'XAUUSDp', 'tf': 'M15', 'loai': 'ngang', 'diem': [[1795700000, 3500]], 'gia_tao': 3490, 'ghi_chu': 'Giá cũ 25 phút'}
        status, j, _ = self.req(self.a, path, yc, a)
        self.assertEqual(status, 200, j)
        id_ = j['canh_bao']['id']
        self.assertEqual(self.req(self.b, path, uid=b)[1]['ds'], [])
        self.assertEqual(self.req(self.b, path, {'viec': 'xoa', 'id': id_}, b)[0], 400)
        self.assertEqual(self.req(self.b, path, uid=a)[0], 409)
        self.assertEqual(self.req(self.a, path + '?lang=en', uid=a)[1]['ds'][0]['ghi_chu'], yc['ghi_chu'])
        self.assertEqual(self.req(self.b, path, {'viec': 'tim_chat'}, b)[0], 400)
        self.assertEqual(self.req(self.b, path, {'viec': 'chon_chat', 'id': '12345'}, b)[0], 400)
        self.assertEqual(self.req(self.b, path, {'viec': 'tao_ma_noi'}, b)[0], 200)


def replay(code, extra='', bars=None):
    if not shutil.which('node'):
        raise unittest.SkipTest('Cần Node')
    if bars is None:
        bars = [[1767225600 + 900 * i, 4000., 4005., 3995., 4000.] for i in range(400)]
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        (p / 'bars.json').write_text(json.dumps(bars), encoding='utf-8')
        (p / 'run.js').write_text(VO + extra + bieu_do_phat_lai.JS + code, encoding='utf-8')
        r = subprocess.run([shutil.which('node'), str(p / 'run.js'), str(p / 'bars.json')], capture_output=True, text=True, encoding='utf-8', timeout=20)  # noqa: S603
    if r.returncode:
        raise AssertionError(r.stderr[-2000:])
    return json.loads(r.stdout)


class ReplayReview(unittest.TestCase):
    def test_thoat_khoi_phuc_ban_ve_moi_nhat_truoc_khi_doi_khoa_ve(self):
        r = replay("CBPL.batDau(200);CBPL.thoat(false);console.log(JSON.stringify({ds:VE.ds,cu:VE.cu}));", """
const VE={ds:[{id:'original'}],cu:['old'],lai:[],goc:'old',an:false},BDMN=()=>({VE,veCong(){},veTb(){}});window.BDMN=BDMN;
window.HVD={truocLuyen:()=> 'scope',sauLuyen:(key,fallback)=>{if(!window.PHAT_LAI||key!=='scope')throw Error('wrong restore phase');return{ds:[...fallback,{id:'new_from_peer'}],luuLoi:false}}};
""")
        self.assertEqual(r, {'ds': [{'id': 'original'}, {'id': 'new_from_peer'}], 'cu': []})

    def test_ban_ve_that_khong_lo_vao_replay_va_duoc_tra_lai(self):
        r = replay("""
CBPL.batDau(200);const hidden=VE.ds.length;VE.ds.push({id:'scratch'});CBPL.thoat(false);
console.log(JSON.stringify({hidden,restored:VE.ds}));
""", "const VE={ds:[{id:'future'}],cu:[],lai:[],goc:'old',an:false},BDMN=()=>({VE,veCong(){},veTb(){}});window.BDMN=BDMN;")
        self.assertEqual(r, {'hidden': 0, 'restored': [{'id': 'future'}]})

    def test_lui_chon_qua_lenh_da_biet_ket_qua_tao_phien_moi(self):
        r = replay("""
CBPL.batDau(200);CBPL.vao(1);CBPL.tien();CBPL.dong(4010,cs[201][0],'Tay');CBPL.batDau(100);
console.log(JSON.stringify({remaining:CBPL.PL.ds.length,saved:Object.keys(ls),history:JSON.parse(ls['so-phat-lai:u_a']).so.length}));
""", "window.HVD_CHU={id:'a'};const ls={};localStorage.setItem=(k,v)=>ls[k]=v;")
        self.assertEqual(r, {'remaining': 0, 'saved': ['so-phat-lai:u_a'], 'history': 1})

    def test_gap_da_cham_tp_tai_gia_mo_khong_bi_tinh_sl_ve_sau(self):
        r = replay("CBPL.batDau(200);CBPL.vao(1);cs[201]=[cs[201][0],4035,4040,3980,4000];CBPL.tien();console.log(JSON.stringify(CBPL.PL.ds[0]));")
        self.assertEqual((r['ly'], r['ra']), ('TP', 4035))

    def test_it_nen_khong_lam_crash_va_khong_chan_luong_gia(self):
        r = replay("CBPL.batDau(20);console.log(JSON.stringify({on:CBPL.PL.on,chan:BDPL.chan}));", bars=[[i + 1, 1, 2, .5, 1] for i in range(30)])
        self.assertEqual(r, {'on': 0, 'chan': False})

    def test_lich_su_tai_khoan_b_khong_doc_kho_cu_chua_gan_chu(self):
        r = replay("CBPL.batDau(200);console.log(JSON.stringify({on:CBPL.PL.on}));", "window.HVD_CHU={id:'b',chu:false};localStorage.getItem=k=>{if(k==='so-phat-lai')throw Error('must not read legacy');return null};")
        self.assertEqual(r['on'], 1)


if __name__ == '__main__':
    unittest.main()
