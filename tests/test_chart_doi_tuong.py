"""Chạy thao tác thật: quyền sửa, hoàn tác, đồng bộ, khóa và bản sao độc lập."""
import json
import unittest

from so_cong_khai import bieu_do, chart_doi_tuong, dich
from test_chart_pro import node


BASE = chart_doi_tuong.CORE_JS + """
let allowed=true,saves=0,paint=0,next=0;const history=[];
const original=[{id:'a',k:'xu',a:{t:1,p:10},b:{t:2,p:20},khoa:1},{id:'b',k:'chu',a:{t:3,p:30},chu:'Đỉnh tháng 11'}];
const V={ds:JSON.parse(JSON.stringify(original)),chon:null,cu:[],lai:[],goc:JSON.stringify(original)};
const g={D:{candles:[]},VE:V,VEC:{xu:['Đường xu hướng'],chu:['Ghi chú']},veDuoc:()=>allowed,moiId:()=> 'new_'+(++next),
 veCong(){},veTb:()=>paint++,lwPhu(){},veLuu(){history.push(V.goc);V.goc=JSON.stringify(V.ds);saves++}};
const run=(action,id='b')=>CHART_OBJECTS.act(g,action,id);
"""


class DrawingManager(unittest.TestCase):
    def js(self, code):
        return node(BASE + code)

    def test_tim_khong_dau_va_thu_tu_lop(self):
        r = self.js("console.log(JSON.stringify({all:CHART_OBJECTS.list(g).map(h=>h.id),q:CHART_OBJECTS.list(g,'dinh thang').map(h=>h.id),tool:CHART_OBJECTS.list(g,'duong xu').map(h=>h.id)}));")
        self.assertEqual(r, {'all': ['b', 'a'], 'q': ['b'], 'tool': ['a']})

    def test_tat_ca_thao_tac_sua_deu_can_quyen(self):
        r = self.js("allowed=false;const result=['hide','lock','duplicate','delete','front','back'].map(a=>run(a));console.log(JSON.stringify({result,saves,ds:V.ds}));")
        self.assertEqual(r['result'], ['denied'] * 6)
        self.assertEqual(r['saves'], 0)
        self.assertEqual(len(r['ds']), 2)
        self.assertNotIn('an', r['ds'][1])

    def test_dang_doi_khung_ve_do_phat_lai_khong_sua(self):
        r = self.js("g.D=null;const pending=run('delete');g.D={};V.tam={};const draft=run('hide');V.tam=null;window.PHAT_LAI=1;const replay=run('duplicate');console.log(JSON.stringify({pending,draft,replay,saves}));")
        self.assertEqual(r, {'pending': 'busy', 'draft': 'busy', 'replay': 'busy', 'saves': 0})

    def test_hinh_khoa_khong_xoa_duoc_mo_khoa_roi_moi_xoa(self):
        r = self.js("const locked=run('delete','a');run('lock','a');const result=run('delete','a');console.log(JSON.stringify({locked,result,saves,ids:V.ds.map(h=>h.id),undo:JSON.parse(history.at(-1)).map(h=>h.id)}));")
        self.assertEqual(r, {'locked': 'locked', 'result': 'ok', 'saves': 2, 'ids': ['b'], 'undo': ['a', 'b']})

    def test_an_hien_va_chon_khong_ghi_them_ban_luu(self):
        r = self.js("run('hide');const hidden=run('select');run('hide');const selected=run('select');console.log(JSON.stringify({hidden,selected,saves,chon:V.chon,an:!!V.ds[1].an}));")
        self.assertEqual(r, {'hidden': 'hidden', 'selected': 'ok', 'saves': 2, 'chon': 'b', 'an': False})

    def test_nhan_ban_khong_sua_toa_do_hay_khoa_ban_goc(self):
        r = self.js("run('duplicate','a');const copy=V.ds.at(-1);copy.a.p=999;console.log(JSON.stringify({original:V.ds[0],copy,history:history.length,saves}));")
        self.assertEqual(r['original']['a']['p'], 10)
        self.assertTrue(r['original']['khoa'])
        self.assertNotIn('khoa', r['copy'])
        self.assertNotEqual(r['copy']['id'], r['original']['id'])
        self.assertEqual(r['history'], 1)
        self.assertEqual(r['saves'], 1)

    def test_doi_lop_va_du_lieu_bi_xoa_tu_tab_khac(self):
        r = self.js("run('front','a');const front=V.ds.map(h=>h.id);run('back','a');V.ds=V.ds.filter(h=>h.id!=='b');const gone=run('hide');console.log(JSON.stringify({front,back:V.ds.map(h=>h.id),gone,saves}));")
        self.assertEqual(r, {'front': ['b', 'a'], 'back': ['a'], 'gone': 'missing', 'saves': 2})

    def test_gioi_han_ban_sao_ton_trong_kho_may_chu(self):
        r = self.js("V.ds[1].chu='a'.repeat(410000);const huge=run('duplicate');V.ds[1].chu='';g.moiId=()=> 'b';const duplicateId=run('duplicate');console.log(JSON.stringify({huge,duplicateId,saves,n:V.ds.length}));")
        self.assertEqual(r, {'huge': 'limit', 'duplicateId': 'limit', 'saves': 0, 'n': 2})

    def test_moc_nap_dung_thu_tu_va_khong_lo_lop_html(self):
        html = bieu_do.trang_bieu_do('Thử')
        self.assertLess(html.index('window.BDMN=()=>'), html.index('window.CHART_OBJECTS='))
        self.assertIn('veHoan,veLam', bieu_do.JS)
        self.assertIn('esc(h.chu||h.id)', chart_doi_tuong.JS)
        self.assertIn("addEventListener('chart-context-changing',close)", chart_doi_tuong.JS)
        self.assertIn('if(keep)', chart_doi_tuong.JS)
        self.assertNotRegex(chart_doi_tuong.JS, r'fetch\(|window\.open\(|sendOrder|order_send')

    def test_nhan_tieng_anh(self):
        missing = set()
        dich.dich_html('<script>' + chart_doi_tuong.JS + '</script>', dich.tu_dien('en'), missing)
        self.assertEqual(sorted(missing), [], json.dumps(sorted(missing), ensure_ascii=False))
