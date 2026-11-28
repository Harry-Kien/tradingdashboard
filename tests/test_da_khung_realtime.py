"""Kiểm thực JavaScript: nến chạy, EMA, hàng đợi và phản hồi đến muộn."""
import json
import unittest

from so_cong_khai import da_khung_realtime as rt, da_khung_giao_dien as ui
from test_chart_pro import node


class Engine(unittest.TestCase):
    def js(self, code):
        return node(rt.JS + code)

    def test_ghep_nen_dang_chay_va_ema_tu_nen_dong(self):
        r = self.js("const cs=Array.from({length:60},(_,i)=>[900*(i+1),100,100,100,100]);const s=DKRT.snapshot({candles:cs,ema20:cs.map(()=>100),ema50:cs.map(()=>100),dang_chay:[54900,101,104,99,103]},'M15');console.log(JSON.stringify({n:s.cs.length,c:s.cs.at(-1),e20:s.e20.at(-1),e50:s.e50.at(-1)}));")
        self.assertEqual(r['n'], 61)
        self.assertEqual(r['c'], [54900, 101, 104, 99, 103])
        self.assertAlmostEqual(r['e20'], 100 + 3 * 2 / 21)
        self.assertAlmostEqual(r['e50'], 100 + 3 * 2 / 51)

    def test_ema_khong_lam_min_lap_lai_tren_cung_mot_nen(self):
        r = self.js("const cs=Array.from({length:60},(_,i)=>[900*(i+1),100,100,100,100]),s=DKRT.snapshot({candles:cs,ema20:cs.map(()=>100),ema50:cs.map(()=>100)},'M15');DKRT.tick(s,[101,102,54001000]);DKRT.tick(s,[102,103,54002000]);console.log(JSON.stringify({c:s.cs.at(-1),e:s.e20.at(-1)}));")
        self.assertEqual(r['c'], [54000, 100, 102, 100, 102])
        self.assertAlmostEqual(r['e'], 100 + 2 * 2 / 21)

    def test_tick_cu_va_nan_khong_ghi_de_gia_moi(self):
        r = self.js("const s=DKRT.snapshot({candles:[[900,100,101,99,100]]},'M15');DKRT.tick(s,[101,102,901000]);const before=JSON.stringify(s);const bad=[[90,91,900999],[NaN,100,902000],[100,99,902000],[100,101,1e300]].map(q=>DKRT.tick(s,q));console.log(JSON.stringify({bad,same:before===JSON.stringify(s)}));")
        self.assertTrue(r['same'])
        self.assertEqual(r['bad'], [False] * 4)

    def test_nen_moi_danh_dau_cho_nen_goc_khong_gia_lam_du_ohlc(self):
        r = self.js("const s=DKRT.snapshot({candles:[[900,100,101,99,100]]},'M15');console.log(JSON.stringify({hit:DKRT.tick(s,[104,105,1810000]),s}));")
        self.assertTrue(r['hit']['fresh'])
        self.assertTrue(r['s']['provisional'])
        self.assertEqual(r['s']['cs'][-1], [1800, 104, 104, 104, 104])

    def test_thang_hai_khong_bi_tinh_30_ngay(self):
        r = self.js("const t=Date.UTC(2024,1,1)/1000,s=DKRT.snapshot({candles:[[t,100,100,100,100]]},'MN1');DKRT.tick(s,[102,103,Date.UTC(2024,2,1)]);console.log(JSON.stringify(s.cs.at(-1)[0]));")
        self.assertEqual(r, 1709251200)

    def test_anh_chup_cu_khong_keo_close_high_low_lui_lai(self):
        r = self.js("const j={candles:[[900,100,101,99,100]],tick_ms:901000},old=DKRT.snapshot(j,'M15');DKRT.tick(old,[105,106,902000]);DKRT.tick(old,[103,104,903000]);const s=DKRT.merge(DKRT.snapshot(j,'M15'),old);console.log(JSON.stringify(s.cs.at(-1)));")
        self.assertEqual(r, [900, 100, 105, 99, 103])

    def test_nguon_moi_duoc_quyen_chot_close_nhung_giu_high_da_quan_sat(self):
        r = self.js("const old=DKRT.snapshot({candles:[[900,100,105,99,103]],tick_ms:903000},'M15');const s=DKRT.merge(DKRT.snapshot({candles:[[900,100,104,99,101]],tick_ms:904000},'M15'),old);console.log(JSON.stringify(s.cs.at(-1)));")
        self.assertEqual(r, [900, 100, 105, 99, 101])

    def test_du_lieu_hong_va_sai_tf_bao_loi(self):
        r = self.js("console.log(JSON.stringify([{candles:[[900,100,90,99,100]]},{tf:'H1',candles:[[900,100,101,99,100]]},{candles:[[900,100,101,99,100],[900,100,101,99,100]]}].map(j=>{try{DKRT.snapshot(j,'M15');return false}catch(e){return true}})));")
        self.assertEqual(r, [True] * 3)

    def test_gioi_han_bo_nho(self):
        r = self.js("const s=DKRT.snapshot({candles:[[60,100,100,100,100]]},'M1');for(let i=2;i<1000;i++)DKRT.tick(s,[100,101,i*60000]);console.log(JSON.stringify([s.cs.length,s.e20.length,s.e50.length]));")
        self.assertEqual(r, [600, 600, 600])

    def test_load_trung_chi_mot_get_va_gioi_han_ba_get(self):
        r = node("let calls=0,running=0,max=0,releases=[];globalThis.fetch=async()=>{calls++;running++;max=Math.max(max,running);await new Promise(r=>releases.push(r));running--;return{ok:true,json:async()=>({candles:[[100,1,1,1,1]]})}};" + rt.JS + """
(async()=>{const a=DKRT.load('XAU','M15'),b=DKRT.load('XAU','M15'),tasks=[a,b,...Array.from({length:6},(_,i)=>DKRT.load('M'+i,'H1'))];const same=a===b;while(releases.length||running){releases.splice(0).forEach(r=>r());await new Promise(r=>setImmediate(r))}await Promise.all(tasks);console.log(JSON.stringify({same,calls,max}));})();
""")
        self.assertEqual(r, {'same': True, 'calls': 7, 'max': 3})


HARNESS = r'''
const noop=()=>{},NOW=Date.now(),events={},frames=[],timers=[],getCalls=[],quotes=new Map(),charts=[];let ttSub=null,hold=null;
const make=()=>({dataset:{},style:{setProperty:noop},hidden:false,value:'',textContent:'',innerHTML:'',events:{},children:[],classList:{toggle:noop},setAttribute(k,v){this[k]=v},removeAttribute(k){delete this.dataset[k.replace('data-','')]},addEventListener(n,f){this.events[n]=f},appendChild(n){this.children.push(n)},getBoundingClientRect:()=>({top:150}),querySelector(s){return this.parts[s]||(this.parts[s]=make())},parts:{},closest:()=>main});
const main=make(),grid=make(),top=make(),summary=make(),status=make(),buttons=['2','4','1+3'].map(v=>Object.assign(make(),{dataset:{v}})),nodes={'#dk-luoi':grid,'.dk-thanh':top,'#dk-tom':summary,'#dk-song':status};
for(const k of['dk-dma','dk-dkh','dk-dtro','dk-dtg'])nodes['#'+k]=make();
globalThis.document={querySelector:s=>nodes[s]||null,querySelectorAll:s=>s==='#dk-bo button'?buttons:[],createElement:make,documentElement:make(),visibilityState:'visible',addEventListener:(n,f)=>events[n]=f};
globalThis.localStorage={getItem:()=>CONFIG,setItem:noop};globalThis.getComputedStyle=()=>({getPropertyValue:()=>''});globalThis.location={search:'',href:''};globalThis.scrollY=0;
globalThis.matchMedia=()=>({matches:false});globalThis.requestAnimationFrame=f=>(frames.push(f),frames.length);globalThis.setInterval=noop;globalThis.setTimeout=(f,ms)=>(timers.push({f,ms}),timers.length);globalThis.clearTimeout=noop;globalThis.addEventListener=(n,f)=>events[n]=f;
globalThis.ResizeObserver=class{observe(){}};globalThis.MutationObserver=class{observe(){}};
const TF={M5:300,M15:900,H1:3600,H4:14400,M10:600};
const snapshot=(ma,tf)=>{const step=TF[tf]||900,t=Math.floor(NOW/1000/step)*step,b=ma==='EURUSDp'?1.1:100,cs=Array.from({length:60},(_,i)=>[t-(60-i)*step,b,b,b,b]);return{ma,tf,nguon:'mt5',so_le:ma==='EURUSDp'?5:2,tick_ms:NOW,candles:cs,ema20:cs.map(()=>b),ema50:cs.map(()=>b),dang_chay:[t,b,b,b,b]}};
quotes.set('XAUUSDp',{q:[100,101,NOW],so_le:2});quotes.set('EURUSDp',{q:[1.1,1.1002,NOW],so_le:5});
globalThis.fetch=async url=>{if(url.startsWith('/api/ma'))return{ok:true,json:async()=>({ds:[{ma:'XAUUSDp',la_vang:true,nhom:'Kim loại'},{ma:'EURUSDp',nhom:'Forex'}]})};getCalls.push(url);const u=new URL(url,'http://local'),ma=u.searchParams.get('ma'),tf=u.searchParams.get('tf');if(hold&&hold(ma,tf))await new Promise(r=>holds.push(r));return{ok:true,json:async()=>snapshot(ma,tf)}};const holds=[];
const series=()=>({data:[],full:0,updates:0,applyOptions(o){this.options=o},setData(a){this.full++;this.data=a.map(x=>({...x}))},update(x){this.updates++;if(this.data.at(-1)?.time===x.time)this.data[this.data.length-1]=x;else this.data.push(x)},coordinateToPrice:y=>y});
globalThis.LightweightCharts={CandlestickSeries:'c',LineSeries:'l',createChart:(_,opts)=>{const ps={range:{from:90,to:110},auto:true,applyOptions(o){if('autoScale'in o)this.auto=o.autoScale},getVisibleRange(){return this.range},setVisibleRange(r){this.range={...r}}},ts={range:null,sets:0,getVisibleLogicalRange(){return this.range},getVisibleRange:()=>null,setVisibleLogicalRange(r){this.range={...r};this.sets++},setVisibleRange(r){this.timeRange=r;this.sets++;this.sub?.(r)},subscribeVisibleTimeRangeChange(f){this.sub=f}};const c={opts,series:[],applyOptions(o){Object.assign(this.opts.timeScale,o.timeScale||{})},priceScale:()=>ps,timeScale:()=>ts,addSeries(){const s=series();this.series.push(s);return s},subscribeCrosshairMove(f){this.cross=f},clearCrosshairPosition(){this.cleared=(this.cleared||0)+1},setCrosshairPosition(...a){this.crossAt=a},remove(){this.dead=true}};charts.push(c);return c}};
globalThis.TT={by:()=>quotes,tt:{ok:true,ket_noi:true},nghi:()=>false,on:f=>ttSub=f,batDau:noop};
RT
UI
const settle=async()=>{for(let i=0;i<20;i++)await new Promise(r=>setImmediate(r))},flush=()=>{for(let i=0;frames.length&&i<10;i++)frames.splice(0).forEach(f=>f())};
(async()=>{await settle();flush();TEST})();
'''


def page(code, config=None):
    script = HARNESS.replace('CONFIG', json.dumps(json.dumps(config or {}))).replace('RT\n', rt.JS).replace('UI\n', ui.JS).replace('TEST', code)
    return node(script)


class Integration(unittest.TestCase):
    def test_bon_o_cung_ma_khung_chi_tai_mot_lan(self):
        r = page("console.log(JSON.stringify({calls:getCalls.length,last:DK.O.map(o=>o.cs.at(-1)[4]),same:summary.innerHTML.includes('trùng mã và khung')}));", {'o': [{'tf': 'M10'}] * 4})
        self.assertEqual(r, {'calls': 1, 'last': [100] * 4, 'same': True})

    def test_tick_trong_luc_cho_http_khong_mat_va_bon_o_khop_nhau(self):
        r = page("getCalls.length=0;hold=()=>true;for(const o of DK.O)DK.tai(o);await settle();for(let i=1;i<=20;i++){quotes.set('XAUUSDp',{q:[100+i,101+i,NOW+i]});DK.apGia(['XAUUSDp'])}flush();hold=null;holds.splice(0).forEach(f=>f());await settle();flush();console.log(JSON.stringify({values:DK.O.map(o=>o.cs.at(-1)[4]),high:DK.O.map(o=>o.cs.at(-1)[2]),calls:getCalls.length}));", {'o': [{'tf': 'M15'}] * 4})
        self.assertEqual(r, {'values': [120] * 4, 'high': [120] * 4, 'calls': 1})

    def test_mot_nghin_tick_chi_ve_mot_khung_hinh(self):
        r = page("for(const c of charts)for(const s of c.series)s.updates=0;const before=charts.map(c=>c.series[0].full);for(let i=1;i<=1000;i++){quotes.set('XAUUSDp',{q:[100+i/100,101+i/100,NOW+i]});DK.apGia(['XAUUSDp'])}const queued=frames.length;flush();console.log(JSON.stringify({queued,updates:charts.map(c=>c.series[0].updates),same:before.every((n,i)=>n===charts[i].series[0].full)}));", {'o': [{'tf': 'M15'}] * 4})
        self.assertEqual(r, {'queued': 1, 'updates': [1] * 4, 'same': True})

    def test_doi_ma_khong_bi_phan_hoi_ma_cu_ghi_de(self):
        r = page("DK.ST.dongMa=0;const o=DK.O[0],m=o.el.querySelector('.dk-ma');hold=ma=>ma==='EURUSDp';m.value='EURUSDp';m.events.change({target:m});await settle();m.value='XAUUSDp';m.events.change({target:m});await settle();holds.splice(0).forEach(f=>f());await settle();flush();console.log(JSON.stringify({ma:o.ma,value:o.cs.at(-1)[4],href:o.el.querySelector('.dk-mo').href}));")
        self.assertEqual(r['ma'], 'XAUUSDp')
        self.assertEqual(r['value'], 100)
        self.assertIn('tf=M5', r['href'])

    def test_dong_bo_khung_tu_o_dang_chon_ke_ca_cau_hinh_o_an(self):
        r = page("DK.O[1].el.events.pointerdown();nodes['#dk-dkh'].events.click();await settle();buttons[0].events.click();await settle();const o=DK.O[1],select=o.el.querySelector('.dk-tf');select.value='M10';select.events.change({target:select});await settle();console.log(JSON.stringify(DK.ST.o.map(c=>c.tf)));")
        self.assertEqual(r, ['M10'] * 4)

    def test_phong_o_khong_lam_mat_cac_chart(self):
        r = page("const o=DK.O[2];o.el.querySelector('.dk-focus').events.click();const focused=DK.O.map(q=>q.el.hidden);o.el.querySelector('.dk-focus').events.click();console.log(JSON.stringify({focused,restored:DK.O.map(q=>q.el.hidden),charts:charts.length}));")
        self.assertEqual(r, {'focused': [True, True, False, True], 'restored': [False] * 4, 'charts': 4})

    def test_so_le_fx_va_link_giu_dung_khung(self):
        r = page("DK.ST.dongMa=0;const o=DK.O[0],m=o.el.querySelector('.dk-ma');m.value='EURUSDp';m.events.change({target:m});await settle();console.log(JSON.stringify({digits:o.nen.options.priceFormat.precision,href:o.el.querySelector('.dk-mo').href}));")
        self.assertEqual(r['digits'], 5)
        self.assertIn('ma=EURUSDp&tf=M5', r['href'])
