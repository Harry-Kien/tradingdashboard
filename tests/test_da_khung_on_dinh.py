"""Giữ vùng nhìn nhưng tiếp tục nhận giá; chọn mã và khung độc lập."""
import unittest

from so_cong_khai import da_khung_realtime
from test_chart_pro import node
from test_da_khung_realtime import page


class Viewport(unittest.TestCase):
    def test_lam_moi_khong_xoa_lich_su_dang_xem_va_gioi_han_bo_nho(self):
        r = node(da_khung_realtime.JS + "const cs=Array.from({length:600},(_,i)=>[1000+i*60,1,1,1,1]),old=DKRT.snapshot({candles:cs},'M1'),fresh=DKRT.snapshot({candles:cs.slice(200)},'M1'),s=DKRT.merge(fresh,old);console.log(JSON.stringify({n:s.cs.length,first:s.cs[0][0],e20:s.e20.length,e50:s.e50.length}));")
        self.assertEqual(r, {'n': 600, 'first': 1000, 'e20': 600, 'e50': 600})

    def test_neo_thoi_gian_giu_phan_le_va_khoang_trong_sau_thay_lich_su(self):
        r = node(da_khung_realtime.JS + "const cs=Array.from({length:100},(_,i)=>[1000+i*60,1,1,1,1]),v=DKRT.view(cs,{from:20.25,to:105.75}),next=cs.slice(10).concat([[7000,1,1,1,1]]);console.log(JSON.stringify({locked:DKRT.rebase(next,v),follow:DKRT.rebase(next,v,true)}));")
        self.assertEqual(r, {'locked': {'from': 10.25, 'to': 95.75}, 'follow': {'from': 11.25, 'to': 96.75}})

    def test_mac_dinh_moi_va_cau_hinh_cu_deu_chon_rieng_tung_o(self):
        for config in ({}, {'dongMa': 1, 'dongKhung': 1}):
            r = page("const o=DK.O[1],m=o.el.querySelector('.dk-ma'),t=o.el.querySelector('.dk-tf');m.value='EURUSDp';m.events.change({target:m});await settle();t.value='M10';t.events.change({target:t});await settle();flush();console.log(JSON.stringify({ma:DK.O.map(x=>x.ma),tf:DK.O.map(x=>x.tf),lock:DK.ST.giu}));", config)
            self.assertEqual(r, {'ma': ['XAUUSDp', 'EURUSDp', 'XAUUSDp', 'XAUUSDp'], 'tf': ['M5', 'M10', 'H1', 'H4'], 'lock': 1})

    def test_tai_lai_khong_keo_ve_mac_dinh_hoac_doi_truc_gia(self):
        r = page("const o=DK.O[0],ts=o.chart.timeScale(),ps=o.chart.priceScale('right');ts.setVisibleLogicalRange({from:8.25,to:64.75});ps.setVisibleRange({from:91,to:109});await DK.tai(o);await settle();flush();console.log(JSON.stringify({view:ts.range,price:ps.range,auto:ps.auto}));")
        self.assertEqual(r, {'view': {'from': 8.25, 'to': 64.75}, 'price': {'from': 91, 'to': 109}, 'auto': False})

    def test_tick_sang_nen_moi_khong_goi_dat_lai_vung_nhin(self):
        r = page("const o=DK.O[0],ts=o.chart.timeScale(),before=ts.sets,last=o.cs.at(-1)[0];quotes.set(o.ma,{q:[120,121,(last+300)*1000]});DK.apGia([o.ma]);flush();console.log(JSON.stringify({sets:ts.sets-before,close:o.cs.at(-1)[4],auto:o.chart.priceScale('right').auto,shift:o.chart.opts.timeScale.shiftVisibleRangeOnNewBar}));")
        self.assertEqual(r, {'sets': 0, 'close': 120, 'auto': False, 'shift': False})

    def test_dong_bo_thoi_gian_chi_tu_thao_tac_nguoi_dung(self):
        r = page("nodes['#dk-dtg'].events.click();const o=DK.O[0],ts=o.chart.timeScale(),other=DK.O[1].chart.timeScale(),r={from:1,to:2};ts.sub(r);const before=other.sets;o.el.querySelector('.dk-c').events.pointerdown();ts.sub(r);console.log(JSON.stringify({automatic:before,user:other.sets-before}));")
        self.assertEqual(r, {'automatic': 2, 'user': 1})                # bật Liên kết thu phóng thì căn ngay các ô một lần; sau đó chỉ theo thao tác người dùng

    def test_nut_hien_tai_co_gia_lai_roi_khoa_truc(self):
        r = page("const o=DK.O[0],ps=o.chart.priceScale('right');o.el.querySelector('.dk-now').events.click();const reset=ps.auto;flush();console.log(JSON.stringify({reset,locked:!ps.auto,view:o.chart.timeScale().range}));")
        self.assertTrue(r['reset'])
        self.assertTrue(r['locked'])
        self.assertEqual(r['view'], {'from': -39, 'to': 65})

    def test_bat_tat_giu_khung_va_tach_tung_o(self):
        r = page("const lock=top.children.find(x=>x.textContent==='Giữ khung nhìn'),split=top.children.find(x=>x.textContent==='Tách từng ô');nodes['#dk-dma'].events.click();await settle();split.events.click();lock.events.click();const unlocked=DK.O.every(o=>o.chart.priceScale('right').auto&&o.chart.opts.timeScale.shiftVisibleRangeOnNewBar);lock.events.click();flush();console.log(JSON.stringify({unlocked,locked:DK.O.every(o=>!o.chart.priceScale('right').auto),ma:DK.ST.dongMa,tf:DK.ST.dongKhung}));")
        self.assertEqual(r, {'unlocked': True, 'locked': True, 'ma': 0, 'tf': 0})

    def test_luu_dong_bo_v2_duoc_ton_trong(self):
        r = page("console.log(JSON.stringify([DK.ST.dongMa,DK.ST.dongKhung,DK.ST.giu]));", {'v': 2, 'dongMa': 1, 'dongKhung': 1, 'giu': 0})
        self.assertEqual(r, [1, 1, 0])

    def test_tom_tat_khong_bien_mat_sau_khi_doi_ca_nhom_ma(self):
        r = page("const m=DK.O[0].el.querySelector('.dk-ma');m.value='EURUSDp';m.events.change({target:m});await settle();flush();const first=!!summary.innerHTML;m.value='XAUUSDp';m.events.change({target:m});await settle();flush();console.log(JSON.stringify({first,back:!!summary.innerHTML,slot:summary.innerHTML.includes('dk-consensus')}));", {'v': 2, 'dongMa': 1})
        self.assertEqual(r, {'first': True, 'back': True, 'slot': True})
