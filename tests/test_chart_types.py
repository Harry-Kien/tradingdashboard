"""Kiểu chart thật: giá gốc, cập nhật đuôi, Heikin Ashi, lưu riêng và bàn phím."""
import importlib.util
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from so_cong_khai import bieu_do, bieu_do_chi_bao, chart_kieu, chart_realtime, dich, trang


@unittest.skipUnless(shutil.which('node'), 'Cần Node')
class ChartTypeMath(unittest.TestCase):
    def js(self, body):
        r = subprocess.run(['node', '-e', chart_kieu.CORE_JS + '\n' + body], capture_output=True, text=True, encoding='utf-8', check=True)
        return json.loads(r.stdout)

    def test_heikin_formula_and_input_unchanged(self):
        got = self.js('const cs=[[1,10,15,8,14],[2,14,18,11,12]],before=JSON.stringify(cs);console.log(JSON.stringify({ha:CTMath.heikin(cs),same:JSON.stringify(cs)===before}))')
        self.assertEqual(got['ha'], [[1, 12, 15, 8, 11.75], [2, 11.875, 18, 11, 13.75]])
        self.assertTrue(got['same'])

    def test_cached_heikin_matches_full_recalculation_on_tick_append_and_rollback(self):
        got = self.js('''const cs=Array.from({length:100},(_,i)=>[i+1,10+i,15+i,8+i,12+i]),cache=CTMath.cache(),ok=[];
const check=()=>ok.push(JSON.stringify(cache.read(cs).rows)===JSON.stringify(CTMath.heikin(cs)));check();cs[99][4]+=1;check();cs.push([101,110,115,108,113]);check();cs[98][2]+=5;check();cs.splice(50);check();console.log(JSON.stringify(ok))''')
        self.assertEqual(got, [True] * 5)

    def test_hollow_body_and_previous_close_color_are_independent(self):
        got = self.js("const cs=[[1,10,12,8,10],[2,8,11,7,9],[3,12,14,10,11]];console.log(JSON.stringify([CTMath.hollow(cs,1,'green','red'),CTMath.hollow(cs,2,'green','red')]))")
        self.assertEqual((got[0]['color'], got[0]['borderColor']), ('rgba(0,0,0,0)', 'red'))
        self.assertEqual((got[1]['color'], got[1]['borderColor']), ('green', 'green'))

    def test_baseline_uses_revealed_data_and_explicit_custom_price(self):
        got = self.js("const cs=[[1,1,1,1,10],[2,1,1,1,20]];console.log(JSON.stringify([CTMath.base(cs,'avg200'),CTMath.base(cs,'first'),CTMath.base(cs,'custom',15),CTMath.base(cs.slice(0,1),'avg200')]))")
        self.assertEqual(got, [15, 10, 15, 10])

    def test_english_translation_keeps_javascript_valid(self):
        r = subprocess.run(['node', '--check'], input=dich.dich_js(bieu_do_chi_bao.JS, {}), capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Cần Playwright')
class ChartTypesBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1280, 'height': 900})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.context.route('http://types.test/**', lambda r: r.fulfill(body='<html lang="vi"><head><style>' + trang.CSS + bieu_do_chi_bao.CSS + '</style></head><body><div id="cp"><div class="tools t2"></div><div class="stage"><div id="lw" style="width:900px;height:450px"></div></div></div></body></html>', content_type='text/html'))
        self.page.goto('http://types.test/')
        vendor = Path(bieu_do.__file__).resolve().parents[1] / 'tinh/lightweight-charts-5.3.0/lightweight-charts.standalone.production.js'
        self.page.add_script_tag(path=str(vendor))
        self.page.add_script_tag(content=chart_realtime.JS)
        self.page.add_script_tag(content='''
window.HVD_CHU={id:'tester',chu:true};window.palette={bull:'#26a69a',bear:'#ef5350',wick:'#26a69a',wickDn:'#ef5350',bg:'#080b08',fg:'#efefef'};
window.D={ma:'XAUUSD',tf:'H1',nguon:'luu',live:99,candles:[],vol:{}};for(let i=0;i<100;i++)D.candles.push([1700000000+i*3600,100+i,105+i,98+i,102+i]);
window.chart=LightweightCharts.createChart(document.querySelector('#lw'),{width:900,height:450});window.LW={chart,nen:chart.addSeries(LightweightCharts.CandlestickSeries),idx:new Map(),khDao:'',tCuoi:D.candles.at(-1)[0]};
window.render=()=>{LW.nen.setData(D.candles.map((r,i)=>{LW.idx.set(r[0],i);const raw={time:r[0],open:r[1],high:r[2],low:r[3],close:r[4]};return window.CBCN?CBCN.nenData(raw):raw}));if(window.CBCN)CBCN.ve()};render();
window.BDCB=window.BDMN=()=>({D:window.D,LW,P:palette});window.BDPL={chan:false,ve:()=>render()};
let sgVe=0,SG=null,sgBen=0;const pal=()=>palette,on={},fp=String,lwDoc=()=>{},lwPhu=()=>{},demVe=()=>{},ptDoi=()=>{},plCach=()=>{},srcVe=()=>{},botTT=()=>{};
''')
        a = bieu_do.JS.index('function sgKe(){')
        b = bieu_do.JS.index("document.addEventListener('visibilitychange'", a)
        self.page.add_script_tag(content=bieu_do.JS[a:b] + '\nwindow.applyTick=()=>sgKe();')
        self.page.add_script_tag(content=bieu_do_chi_bao.JS)
        self.page.evaluate('render();chart.timeScale().setVisibleLogicalRange({from:20,to:90})')

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def kind(self, k):
        self.page.locator('#ct-kind').select_option(k)
        self.assertEqual(self.page.evaluate('CBCN.kieu()'), k)

    def test_every_chart_type_preserves_raw_data_and_viewport(self):
        raw = self.page.evaluate('JSON.stringify(D.candles)')
        for k, name in [('nen', None), ('rong', 'Candlestick'), ('ha', 'Candlestick'), ('thanh', 'Bar'), ('hlc', 'Bar'), ('duong', 'Line'), ('bac', 'Line'), ('diem', 'Line'), ('vung', 'Area'), ('coso', 'Baseline')]:
            with self.subTest(kind=k):
                self.kind(k)
                state = self.page.evaluate('({raw:JSON.stringify(D.candles),series:CBCN.kieuThongTin().series?.seriesType(),range:chart.timeScale().getVisibleLogicalRange(),base:LW.nen.data().at(-1)})')
                self.assertEqual(state['raw'], raw)
                self.assertEqual(state.get('series'), name)
                self.assertEqual(state['range'], {'from': 20, 'to': 90})
                if k != 'nen':
                    self.assertEqual(state['base']['color'], 'rgba(0,0,0,0)')

    def test_live_tick_updates_overlay_immediately_without_ghost_candles(self):
        for k in ['ha', 'rong', 'hlc', 'bac', 'diem', 'vung', 'coso']:
            with self.subTest(kind=k):
                self.kind(k)
                self.page.evaluate('D.candles.at(-1)[2]+=2;D.candles.at(-1)[4]+=1;applyTick()')
                state = self.page.evaluate('({raw:D.candles.at(-1),base:LW.nen.data().at(-1),shown:CBCN.kieuThongTin().series.data().at(-1)})')
                self.assertEqual(state['base']['color'], 'rgba(0,0,0,0)')
                expected = sum(state['raw'][1:]) / 4 if k == 'ha' else state['raw'][4]
                self.assertEqual(state['shown'].get('value', state['shown'].get('close')), expected)

    def test_new_candle_updates_previous_bar_and_appends_one_overlay_bar(self):
        self.kind('ha')
        self.page.evaluate('const t=D.candles.at(-1)[0]+3600;D.candles.push([t,202,210,200,208]);D.live=100;applyTick()')
        state = self.page.evaluate('({n:CBCN.kieuThongTin().series.data().length,base:LW.nen.data().slice(-2)})')
        self.assertEqual(state['n'], 101)
        self.assertTrue(all(r['color'] == 'rgba(0,0,0,0)' for r in state['base']))

    def test_step_markers_and_hlc_have_distinct_native_options(self):
        for k, prop, value in [('bac', 'lineType', 1), ('diem', 'pointMarkersVisible', True), ('hlc', 'openVisible', False)]:
            self.kind(k)
            self.assertEqual(self.page.evaluate('(p)=>CBCN.kieuThongTin().series.options()[p]', prop), value)

    def test_replay_rollback_has_no_future_overlay_candles(self):
        self.kind('ha')
        self.page.evaluate('BDPL.chan=true;D.candles=D.candles.slice(0,20);D.live=-1;render()')
        state = self.page.evaluate('({n:CBCN.kieuThongTin().series.data().length,last:CBCN.kieuThongTin().series.data().at(-1).time,raw:D.candles.at(-1)[0]})')
        self.assertEqual(state['n'], 20)
        self.assertEqual(state['last'], state['raw'])

    def test_baseline_custom_price_and_symbol_isolation(self):
        self.kind('coso')
        self.page.locator('#ct-help').click()
        self.page.locator('#ct-base-mode').select_option('custom')
        self.page.locator('#ct-base-price').fill('175.5')
        self.page.locator('#ct-dialog form button').click()
        self.assertEqual(self.page.evaluate('CBCN.kieuThongTin().series.options().baseValue.price'), 175.5)
        self.page.keyboard.press('Escape')
        self.page.evaluate("dispatchEvent(new Event('chart-context-changing'));D.ma='EURUSD';render()")
        self.assertEqual(self.page.evaluate('CBCN.kieuThongTin().baseline.mode'), 'avg200')
        self.page.evaluate("D.ma='XAUUSD';render()")
        self.assertEqual(self.page.evaluate('CBCN.kieuThongTin().baseline.value'), 175.5)

    def test_modal_keyboard_and_mobile_bounds(self):
        self.page.set_viewport_size({'width': 320, 'height': 640})
        self.kind('ha')
        self.assertIn('không phải giá khớp', self.page.locator('.ct-note').text_content())
        self.page.locator('#ct-help').click()
        self.page.keyboard.press('/')
        self.assertTrue(self.page.locator('.cbcn-nen').first.evaluate('e=>e.hidden'))
        self.page.keyboard.press('Shift+Tab')
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'ct-reset')
        self.page.keyboard.press('Tab')
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'ct-close')
        self.assertFalse(self.page.locator('#ct-dialog').evaluate('e=>e.scrollWidth>e.clientWidth'))
        self.page.keyboard.press('Escape')
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'ct-help')

    def test_preferences_are_scoped_to_user_and_storage_failure_still_changes_type(self):
        self.kind('bac')
        got = self.page.evaluate("({own:localStorage.getItem('so-kieu-bd:u_tester'),global:localStorage.getItem('so-kieu-bd'),other:localStorage.getItem('so-kieu-bd:u_other')})")
        self.assertEqual(got, {'own': 'bac', 'global': None, 'other': None})
        self.page.evaluate("()=>{Storage.prototype.setItem=()=>{throw new Error('blocked')};return true}")
        self.kind('hlc')
        self.page.locator('#ct-help').click()
        self.assertIn('phiên này', self.page.locator('#ct-message').text_content())
