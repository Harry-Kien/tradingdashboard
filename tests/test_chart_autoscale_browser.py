"""Nút về hiện tại với thư viện chart thật, gồm mốc thời gian từ chuỗi ẩn."""
import importlib.util
import unittest
from pathlib import Path

from so_cong_khai import bieu_do


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Cần Playwright')
class AutoScaleBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.runtime = sync_playwright().start()
        try:
            cls.browser = cls.runtime.chromium.launch()
        except Exception as e:
            cls.runtime.stop()
            raise unittest.SkipTest('Chưa cài Chromium') from e

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.runtime.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 900})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.set_content('<div id="lw" style="width:1300px;height:700px"></div><button id="tu-co">Tự co giá</button>')
        vendor = Path(bieu_do.__file__).resolve().parents[1] / 'tinh/lightweight-charts-5.3.0/lightweight-charts.standalone.production.js'
        self.page.add_script_tag(path=str(vendor))
        a, b = bieu_do.JS.index('function lwNay('), bieu_do.JS.index('function lwZoom(')
        self.page.add_script_tag(content='''
const $=s=>document.querySelector(s),tf='H4',ma='',chartEpoch=0,defN=()=>100;
const lwDoc=()=>{},lwPhu=()=>{};
const chart=LightweightCharts.createChart($('#lw'),{width:1300,height:700});
const s=chart.addSeries(LightweightCharts.CandlestickSeries);
let D={tf:'H4',_chart_epoch:0,candles:[]},LW={chart,nen:s,cho:{from:1,to:10},hov:true,hoverTime:1};
for(let i=0;i<600;i++){const t=1700000000+i*14400,p=4400+i*.2;D.candles.push([t,p,p+3,p-3,p+1])}
s.setData(D.candles.map(c=>({time:c[0],open:c[1],high:c[2],low:c[3],close:c[4]})));
''' + bieu_do.JS[a:b] + '''
$('#tu-co').addEventListener('click',()=>lwNay());
window.inspect=()=>{const ts=chart.timeScale(),last=D.candles.at(-1),range=ts.getVisibleLogicalRange(),i=ts.timeToIndex(last[0]);
const x=ts.timeToCoordinate(last[0]),y=s.priceToCoordinate(last[4]);
return {range,i,x,y,auto:s.priceScale().options().autoScale,price:s.priceScale().getVisibleRange(),hover:LW.hov,hidden:$('#tu-co').hidden}};
window.displace=()=>{chart.timeScale().setVisibleLogicalRange({from:20,to:100});s.priceScale().setVisibleRange({from:3500,to:3700});$('#tu-co').hidden=false};
window.addOldHiddenSeries=()=>{const old=chart.addSeries(LightweightCharts.LineSeries,{visible:false});
old.setData(Array.from({length:3000},(_,i)=>({time:1690000000+i*3600,value:3600+i*.1})));};
''')

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def assert_current_visible(self):
        self.page.locator('#tu-co').click()
        self.page.wait_for_function('(()=>{const p=inspect();return p.x>0&&p.x<1250&&p.y>0&&p.y<650})()')
        state = self.page.evaluate('inspect()')
        self.assertTrue(state['auto'])
        self.assertTrue(state['hidden'])
        self.assertLessEqual(state['range']['from'], state['i'])
        self.assertGreaterEqual(state['range']['to'], state['i'])

    def test_reset_after_horizontal_and_vertical_drag(self):
        self.page.evaluate('displace()')
        self.assert_current_visible()

    def test_hidden_indicator_from_previous_timeframe_does_not_misplace_latest(self):
        self.page.evaluate('addOldHiddenSeries();displace()')
        self.assert_current_visible()

    def test_live_price_stays_visible_after_reset(self):
        self.page.evaluate('addOldHiddenSeries();displace()')
        self.assert_current_visible()
        self.page.evaluate('''const last=D.candles.at(-1);last[2]+=300;last[4]+=300;
s.update({time:last[0],open:last[1],high:last[2],low:last[3],close:last[4]});''')
        self.page.wait_for_function('(()=>{const p=inspect();return p.y>0&&p.y<650})()')
        self.assertTrue(self.page.evaluate('inspect().auto'))
        self.assertFalse(self.page.evaluate('inspect().hover'))

    def test_button_on_mobile(self):
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.page.evaluate("chart.resize(370,650);addOldHiddenSeries();displace()")
        self.page.locator('#tu-co').click()
        self.page.wait_for_function('(()=>{const p=inspect();return p.x>0&&p.x<370&&p.y>0&&p.y<650})()')


if __name__ == '__main__':
    unittest.main()
