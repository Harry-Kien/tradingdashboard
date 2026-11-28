"""Ngày giờ, CSV riêng tư và trục thời gian thật với series ẩn."""
import csv
import importlib.util
import io
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from so_cong_khai import chart_du_lieu, dich, trang


@unittest.skipUnless(shutil.which('node'), 'Cần Node')
class CandleDataCore(unittest.TestCase):
    def test_translated_script_remains_valid_javascript(self):
        # Bộ dịch HTML/JS của máy chủ cũng phải đọc đúng regex có dấu nháy.
        translated = dich.dich_js(chart_du_lieu.JS, {})
        result = subprocess.run(['node', '--check'], input=translated, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)

    def js(self, body):
        result = subprocess.run(['node', '-e', chart_du_lieu.CORE_JS + '\n' + body], capture_output=True, text=True, encoding='utf-8', check=True)
        return json.loads(result.stdout)

    def test_dates_validate_and_convert_timezone(self):
        got = self.js("console.log(JSON.stringify([CandleData.parse('2024-02-29T07:30',420),CandleData.parse('2024-02-29T00:30',0),CandleData.parse('2025-02-29T00:00',0),CandleData.parse('2026-01-01T24:00',0),CandleData.parse('2026-13-01T00:00',0)]))")
        self.assertEqual(got[0], got[1])
        self.assertIsInstance(got[0], int)
        self.assertEqual(got[2:], [None, None, None])

    def test_market_gap_nearest_and_outside_loaded_history(self):
        got = self.js('const cs=[[100],[200],[500]];console.log(JSON.stringify([90,100,150,190,350,499,500,501].map(t=>CandleData.nearest(cs,t))))')
        self.assertEqual(got, [-1, 0, 0, 1, 1, 2, 2, -1])

    def test_calendar_ranges_clamp_month_end_and_leap_year(self):
        got = self.js("console.log(JSON.stringify([['2024-03-31T08:30:00Z','1m'],['2024-02-29T08:30:00Z','1y'],['2026-03-01T08:30:00Z','5d']].map(([t,k])=>new Date(CandleData.cutoff(Date.parse(t)/1000,k)*1000).toISOString())))")
        self.assertEqual(got, ['2024-02-29T08:30:00.000Z', '2023-02-28T08:30:00.000Z', '2026-02-24T08:30:00.000Z'])

    def test_uses_time_axis_mapping_instead_of_candle_array_index(self):
        got = self.js('const ts={timeToIndex:t=>t===100?900:t===200?950:null,getVisibleLogicalRange:()=>({from:40,to:140})};console.log(JSON.stringify([CandleData.centered(ts,100),CandleData.span(ts,[[100],[200]],0,1),CandleData.centered(ts,300)]))')
        self.assertEqual(got, [{'from': 850, 'to': 950}, {'from': 899, 'to': 951}, None])

    def test_csv_whitelist_missing_volume_and_forming_candle(self):
        got = self.js("const D={candles:[[100,2,4,1,3],[200,-2,0,-4,-3],[300,3,5,2,4]],vol:{100:8,300:9},live:2,account:'SECRET',positions:['PRIVATE'],token:'TOKEN'};console.log(JSON.stringify(CandleData.csv(D,'=BAD','M15','loaded',null,false)))")
        rows = list(csv.DictReader(io.StringIO(got['text'].lstrip('\ufeff'))))
        self.assertEqual(got['count'], 2)
        self.assertEqual(rows[0]['tick_volume'], '8')
        self.assertEqual(rows[1]['tick_volume'], '')
        self.assertEqual(rows[1]['open'], '-2')
        self.assertEqual(rows[0]['symbol'], "'=BAD")
        self.assertEqual(rows[0]['status'], 'closed')
        self.assertNotIn('SECRET', got['text'])
        self.assertNotIn('PRIVATE', got['text'])
        self.assertNotIn('TOKEN', got['text'])

    def test_csv_visible_uses_shared_axis_and_replay_excludes_future(self):
        got = self.js("const D={candles:[[100,2,4,1,3],[200,3,5,2,4]],vol:{100:8,200:9,300:99},live:1};const ts={timeToIndex:t=>t===100?900:950,getVisibleLogicalRange:()=>({from:940,to:960})};console.log(JSON.stringify(CandleData.csv(D,'XAUUSD','H1','visible',ts,true)))")
        rows = list(csv.DictReader(io.StringIO(got['text'].lstrip('\ufeff'))))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'forming')
        self.assertEqual(rows[0]['tick_volume'], '9')
        self.assertNotIn('99', got['text'])

    def test_csv_rejects_corrupt_rows_and_handles_quoted_symbols(self):
        got = self.js("console.log(JSON.stringify(CandleData.csv({candles:[[100,2,1,4,3],[200,1,3,0,2],[300,null,3,0,2]]},'a,\"b','H1','loaded',null,false)))")
        rows = list(csv.DictReader(io.StringIO(got['text'].lstrip('\ufeff'))))
        self.assertEqual(got['skipped'], 2)
        self.assertEqual(rows[0]['symbol'], 'a,"b')


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Cần Playwright')
class CandleDataBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.runtime = sync_playwright().start()
        cls.browser = cls.runtime.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.runtime.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 900}, accept_downloads=True)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.set_content('<html lang="vi"><head><style>' + trang.CSS + chart_du_lieu.CSS + '</style></head><body><div id="cp"><div class="tools t2"></div><div id="lw" style="width:900px;height:450px"></div></div></body></html>')
        vendor = Path(chart_du_lieu.__file__).resolve().parents[1] / 'tinh/lightweight-charts-5.3.0/lightweight-charts.standalone.production.js'
        self.page.add_script_tag(path=str(vendor))
        self.page.add_script_tag(content='''
window.D={ma:'XAUUSD',tf:'H1',nguon:'mt5',candles:[],vol:{},live:99};
for(let i=0;i<100;i++){const t=1700000000+i*3600;D.candles.push([t,10+i,12+i,9+i,11+i]);D.vol[t]=i+10}
window.chart=LightweightCharts.createChart(document.querySelector('#lw'),{width:900,height:450});
const s=chart.addSeries(LightweightCharts.CandlestickSeries);s.setData(D.candles.map(c=>({time:c[0],open:c[1],high:c[2],low:c[3],close:c[4]})));
const old=chart.addSeries(LightweightCharts.LineSeries,{visible:false});old.setData(Array.from({length:3000},(_,i)=>({time:1690000000+i*3600,value:10})));
chart.timeScale().setVisibleLogicalRange({from:40,to:100});
window.toasts=[];window.BDMN=()=>({D:window.D,LW:{chart},ma:D?.ma,tf:D?.tf,toast:x=>toasts.push(x)});
window.CBCN={moc:[]};window.chartKeys=0;document.addEventListener('keydown',()=>window.chartKeys++);
''')
        self.page.add_script_tag(content=chart_du_lieu.JS)

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def open(self):
        self.page.locator('#cd-open').click()
        self.assertTrue(self.page.locator('#cd-dialog').evaluate('e=>e.open'))

    def test_data_updates_without_losing_keyboard_focus(self):
        self.open()
        self.assertEqual(self.page.locator('#cd-value-close').text_content(), '110')
        self.assertEqual(self.page.locator('#cd-value-state').text_content(), 'Chưa đóng')
        self.page.locator('#cd-prev').click()
        self.assertEqual(self.page.locator('#cd-value-close').text_content(), '109')
        self.assertEqual(self.page.locator('#cd-value-state').text_content(), 'Đã đóng')
        self.page.locator('#cd-latest').click()
        self.page.evaluate('D.candles.at(-1)[4]=111;D.candles.at(-1)[2]=112;CBCN.moc.forEach(f=>f(BDMN()))')
        self.page.wait_for_function('document.querySelector("#cd-value-close").textContent==="111"')
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'cd-latest')

    def test_alt_g_go_to_date_maps_actual_shared_axis_and_enter_works(self):
        self.page.keyboard.press('Alt+g')
        self.page.locator('#cd-date').fill('2023-11-16T05:13:20')  # UTC+7 -> candle 24
        target = self.page.evaluate('D.candles[24][0]')
        self.page.locator('#cd-date').fill(self.page.evaluate('(t)=>new Date((t+25200)*1000).toISOString().slice(0,19)', target))
        self.page.locator('#cd-date').press('Enter')
        self.page.wait_for_function('!document.querySelector("#cd-dialog").open')
        self.page.wait_for_function('(t)=>chart.timeScale().getVisibleLogicalRange().from>1000', arg=target)
        state = self.page.evaluate('(t)=>({range:chart.timeScale().getVisibleLogicalRange(),i:chart.timeScale().timeToIndex(t,false)})', target)
        self.assertLess(state['range']['from'], state['i'])
        self.assertGreater(state['range']['to'], state['i'])
        self.assertGreater(state['i'], 1000)

    def test_outside_history_keeps_dialog_open_with_explanation(self):
        self.page.keyboard.press('Alt+g')
        self.page.locator('#cd-date').fill('2020-01-01T12:00')
        self.page.locator('#cd-form button').click()
        self.assertTrue(self.page.locator('#cd-dialog').evaluate('e=>e.open'))
        self.assertIn('ngoài lịch sử', self.page.locator('#cd-status').text_content())

    def test_quick_range_ends_at_last_candle_on_shared_axis(self):
        self.page.keyboard.press('Alt+g')
        self.page.locator('#cd-ranges [data-range="1d"]').click()
        self.page.wait_for_function('chart.timeScale().getVisibleLogicalRange().from>1000')
        got = self.page.evaluate('''(()=>{const t=chart.timeScale(),r=t.getVisibleLogicalRange();return {r,a:t.timeToIndex(D.candles[75][0],false),b:t.timeToIndex(D.candles[99][0],false)}})()''')
        self.assertEqual(got['r'], {'from': got['a'] - 1, 'to': got['b'] + 1})

    def test_visible_csv_exports_candles_on_actual_axis_only(self):
        self.page.evaluate('const t=chart.timeScale();t.setVisibleLogicalRange({from:t.timeToIndex(D.candles[10][0],false),to:t.timeToIndex(D.candles[20][0],false)})')
        self.page.wait_for_function('chart.timeScale().getVisibleLogicalRange().from>1000')
        self.open()
        with self.page.expect_download() as event:
            self.page.locator('#cd-export').click()
        rows = list(csv.DictReader(io.StringIO(Path(event.value.path()).read_text(encoding='utf-8-sig'))))
        self.assertEqual(len(rows), 11)
        self.assertEqual((rows[0]['tick_volume'], rows[-1]['tick_volume']), ('20', '30'))

    def test_csv_download_and_no_future_from_replay(self):
        self.page.evaluate('D.candles=D.candles.slice(0,20);D.live=19;window.BDPL={chan:true}')
        self.open()
        self.page.locator('#cd-scope').select_option('loaded')
        with self.page.expect_download() as event:
            self.page.locator('#cd-export').click()
        rows = list(csv.DictReader(io.StringIO(Path(event.value.path()).read_text(encoding='utf-8-sig'))))
        self.assertEqual(len(rows), 19)
        self.assertEqual(rows[-1]['tick_volume'], '28')
        self.assertIn('PHÁT LẠI', self.page.locator('#cd-context').text_content())

    def test_dialog_keyboard_isolation_tabs_and_context_change(self):
        self.open()
        self.page.keyboard.press('Shift+Tab')
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'cd-forming')
        self.page.keyboard.press('Tab')
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'cd-close')
        self.page.locator('#cd-data-tab').focus()
        self.page.keyboard.press('ArrowRight')
        self.assertFalse(self.page.locator('#cd-nav').evaluate('e=>e.hidden'))
        self.page.keyboard.press('f')
        self.assertEqual(self.page.evaluate('window.chartKeys'), 0)
        self.page.evaluate('dispatchEvent(new Event("chart-context-changing"));window.D=null')
        self.assertFalse(self.page.locator('#cd-dialog').evaluate('e=>e.open'))
        self.open()
        self.assertTrue(self.page.locator('#cd-export').is_disabled())

    def test_mobile_bounds_and_escape_restores_button(self):
        self.page.set_viewport_size({'width': 320, 'height': 640})
        self.open()
        box = self.page.locator('#cd-dialog').bounding_box()
        self.assertGreaterEqual(box['x'], 0)
        self.assertLessEqual(box['x'] + box['width'], 320)
        self.assertFalse(self.page.locator('#cd-dialog').evaluate('e=>e.scrollWidth>e.clientWidth'))
        self.page.keyboard.press('Escape')
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'cd-open')
