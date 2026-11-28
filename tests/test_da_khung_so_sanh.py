# -*- coding: utf-8 -*-
"""Nhiều biểu đồ: so sánh giá theo con trỏ, liên kết thu phóng không để trống, ghim điểm (27/11/2026).

Chạy thật mã JS của trang trên bộ biểu đồ giả của test_da_khung_realtime (Node, không cần trình duyệt)."""
import unittest

from test_da_khung_realtime import page

BON = {'o': [{'tf': 'H1'}, {'tf': 'M15'}, {'tf': 'M5'}, {'tf': 'H4'}]}


class SoSanhNhieuKhung(unittest.TestCase):
    def test_lien_ket_thu_phong_cung_mep_phai_va_khong_de_trong(self):
        """H1 nhìn 85 giờ, M15 chỉ có 60 nến (15 giờ): M15 bắt đầu ở nến đầu tiên của nó, mép phải cùng thời điểm với H1."""
        r = page("""nodes['#dk-dtg'].events.click();const h1=DK.O[0],m15=DK.O[1];h1.el.querySelector('.dk-c').events.pointerdown();
const ts=h1.chart.timeScale();ts.setVisibleLogicalRange({from:-25,to:63});ts.sub({from:0,to:1});
const t=(o,l)=>{const cs=o.cs,n=cs.length,d={H1:3600,M15:900,M5:300,H4:14400}[o.tf];return l>=n-1?cs[n-1][0]+(l-(n-1))*d:cs[Math.floor(l)][0]+(l-Math.floor(l))*d};
const v=m15.chart.timeScale().range;console.log(JSON.stringify({from:v.from,phai:t(m15,v.to)===t(h1,63)}));""", BON)
        self.assertEqual(r, {'from': 0, 'phai': True})

    def test_cung_so_nen_khung_lon_van_thay_nhieu_nen(self):
        """M15 đang xem 40 nến: H1 cũng hiện 40 nến, mép phải cùng thời điểm (không chỉ vài nến như kiểu cùng thời gian)."""
        r = page("""const m15=DK.O[1],h1=DK.O[0];m15.el.querySelector('.dk-c').events.wheel();const ts=m15.chart.timeScale();
ts.setVisibleLogicalRange({from:20,to:60});ts.sub({from:0,to:1});const v=h1.chart.timeScale().range;
const t=(o,l)=>{const cs=o.cs,n=cs.length,d={H1:3600,M15:900,M5:300,H4:14400}[o.tf];return l>=n-1?cs[n-1][0]+(l-(n-1))*d:cs[Math.floor(l)][0]+(l-Math.floor(l))*d};
console.log(JSON.stringify({so:Math.round(v.to-v.from),phai:Math.abs(t(h1,v.to)-t(m15,60))<1}));""", {**BON, 'dongTg': 1, 'lk': 'nen'})
        self.assertEqual(r, {'so': 40, 'phai': True})

    def test_chi_cuon_giu_do_phong_tung_o(self):
        r = page("""const m15=DK.O[1],h1=DK.O[0];h1.chart.timeScale().setVisibleLogicalRange({from:30,to:55});m15.el.querySelector('.dk-c').events.wheel();
const ts=m15.chart.timeScale();ts.setVisibleLogicalRange({from:10,to:60});ts.sub({from:0,to:1});const v=h1.chart.timeScale().range;console.log(JSON.stringify(Math.round(v.to-v.from)));""",
                 {**BON, 'dongTg': 1, 'lk': 'cuon'})
        self.assertEqual(r, 25)

    def test_tat_lien_ket_thi_cac_o_doc_lap(self):
        r = page("""const h1=DK.O[0],m15=DK.O[1],before=m15.chart.timeScale().sets;h1.el.querySelector('.dk-c').events.pointerdown();
const ts=h1.chart.timeScale();ts.setVisibleLogicalRange({from:0,to:30});ts.sub({from:0,to:1});console.log(JSON.stringify(m15.chart.timeScale().sets-before));""",
                 {**BON, 'dongTg': 0})
        self.assertEqual(r, 0)

    def test_con_tro_hien_bang_gia_moi_o_va_vi_tri_gia(self):
        """Trỏ vào H1 ở thời điểm nến M15 thứ 50: mọi ô có bảng giá của nến khung mình; cùng mã thì ghi giá trỏ trên đỉnh nến."""
        r = page("""const h1=DK.O[0],m15=DK.O[1],t=m15.cs[50][0];charts[0].cross({time:t,point:{x:10,y:150}});
console.log(JSON.stringify(DK.O.map(o=>({an:o.leg?o.leg.hidden:true,html:o.leg?o.leg.innerHTML:''}))));""", BON)
        self.assertTrue(all(not x['an'] for x in r), r)
        self.assertIn('<b>M15</b>', r[1]['html'])
        self.assertIn('Giá trỏ 150,00 · trên đỉnh nến +50,00', r[1]['html'])           # nến giả có giá 100, chuột ở giá 150

    def test_tat_dong_bo_con_tro_chi_o_dang_tro_co_bang(self):
        r = page("""charts[0].cross({time:DK.O[0].cs[40][0],point:{x:10,y:120}});console.log(JSON.stringify(DK.O.map(o=>!!o.leg&&!o.leg.hidden)));""", {**BON, 'dongTro': 0})
        self.assertEqual(r, [True, False, False, False])

    def test_bam_khong_keo_de_ghim_va_esc_de_bo(self):
        r = page("""const h1=DK.O[0],area=h1.el.querySelector('.dk-c'),t=DK.O[2].cs[55][0];charts[0].cross({time:t,point:{x:10,y:90}});
area.events.pointerdown({button:0,clientX:50,clientY:50});area.events.pointerup({clientX:51,clientY:50});charts[0].cross(null);flush();
const ghim=DK.O.map(o=>o.leg&&!o.leg.hidden&&o.leg.innerHTML.includes('Điểm ghim')),di=DK.O[1].leg.innerHTML.includes('Từ điểm ghim tới giá hiện tại: +10,00');
events.keydown({key:'Escape',target:{tagName:'DIV'}});console.log(JSON.stringify({ghim,di,bo:DK.O.every(o=>!o.leg||o.leg.hidden)}));""", BON)
        self.assertEqual(r['ghim'], [True] * 4)
        self.assertTrue(r['di'])                                                       # ghim ở 90, giá hiện tại 100
        self.assertTrue(r['bo'])

    def test_keo_chuot_khong_ghim(self):
        r = page("""const area=DK.O[0].el.querySelector('.dk-c');charts[0].cross({time:DK.O[0].cs[45][0],point:{x:10,y:90}});
area.events.pointerdown({button:0,clientX:50,clientY:50});area.events.pointerup({clientX:90,clientY:50});charts[0].cross(null);flush();
console.log(JSON.stringify(DK.O.some(o=>o.leg&&!o.leg.hidden)));""", BON)
        self.assertFalse(r)


if __name__ == '__main__':
    unittest.main()
