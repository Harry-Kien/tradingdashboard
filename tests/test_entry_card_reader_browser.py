"""Thẻ điểm vào mở lớn bằng DOM thật: giữ giá, bộ lọc, bàn phím và lựa chọn thu gọn."""
import importlib.util
import unittest

from so_cong_khai import bieu_do, bieu_do_ban, trang


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Cần Playwright')
class EntryReaderBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.runtime = sync_playwright().start()
        cls.browser = cls.runtime.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.runtime.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 900})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        card = '''<div class="ppt"><button class="ppx" aria-selected="true">Tất cả phương pháp</button>
<button class="ppx">Fibonacci</button></div><div class="pl"><div class="plh"><b>Fibonacci: hồi 61,8% sau nhịp đẩy</b>
<span class="hl xau">Kỷ luật: đứng ngoài</span></div><div class="plg">'''
        for label, value in [('Mức chờ', '3.655,88'), ('Dừng lỗ', '3.681,57'), ('Chốt lời 1', '3.630,18'), ('Chốt lời 2', '3.604,48'), ('Mục tiêu lý thuyết', '3.616,15')]:
            card += f'<div><small>{label}</small><b>{value}</b><i>Thông tin mức giá</i></div>'
        card += '''</div><details class="plct"><summary>Số đo và giải thích</summary><p class="why">Đây là thông tin tham khảo. Không có cam kết lợi nhuận.</p></details>
<div class="pln"><button class="dvv">Vẽ lên biểu đồ</button><button class="dvm">Xem phân tích đầy đủ</button></div></div>'''
        html = '<html data-theme="dark"><head><style>' + trang.CSS + bieu_do.CSS + bieu_do_ban.CSS + '''</style></head><body>
<nav class="nv">Harry</nav><main><div class="top"><div class="stamp">Nguồn giá</div></div><div class="desk"><div class="trai">
<section class="chartp" id="cp"><div class="tools"><button id="fs-btn">Toàn màn hình</button></div><div class="stage"><div id="lw"></div></div>
<div id="dv">''' + card + '''</div><p class="hint">Hướng dẫn</p></section><div class="duoi"><aside class="panel" id="ai">AI</aside></div></div><aside class="col"></aside></div></main>
<script>window.draws=0;window.chartKeys=0;window.cardRef=document.querySelector('#dv');
document.querySelectorAll('.ppx').forEach(b=>b.onclick=()=>{document.querySelectorAll('.ppx').forEach(x=>x.setAttribute('aria-selected',String(x===b)))});
document.querySelector('.dvv').onclick=()=>window.draws++;
document.addEventListener('keydown',()=>window.chartKeys++);</script><script>''' + bieu_do_ban.JS + '</script></body></html>'
        self.context.route('http://reader.test/**', lambda route: route.fulfill(body=html, content_type='text/html'))
        self.page.goto('http://reader.test/')

    def tearDown(self):
        self.assertEqual(self.errors, [])
        self.context.close()

    def open_reader(self):
        self.page.locator('#dv-expand').click()
        self.assertTrue(self.page.locator('#dv-reader').evaluate('e=>e.open'))

    def test_open_escape_restores_same_node_and_focus(self):
        self.open_reader()
        self.assertTrue(self.page.evaluate('cardRef===document.querySelector("#dv")'))
        self.assertTrue(self.page.locator('#dv details').evaluate('e=>e.open'))
        self.page.keyboard.press('Escape')
        self.page.wait_for_function('!document.querySelector("#dv-reader").open')
        self.assertEqual(self.page.locator('#dv').evaluate('e=>e.parentElement.id'), 'cp')
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'dv-expand')
        self.assertEqual(self.page.evaluate('window.chartKeys'), 0)
        self.assertFalse(self.page.locator('html').evaluate('e=>e.classList.contains("dv-reading")'))

    def test_filters_live_update_and_draw_keep_working(self):
        self.open_reader()
        self.page.locator('.ppx').nth(1).click()
        self.assertEqual(self.page.locator('.ppx').nth(1).get_attribute('aria-selected'), 'true')
        self.page.locator('#dv .plg b').first.evaluate("e=>e.textContent='3.660,00'")
        self.assertEqual(self.page.locator('#dv .plg b').first.text_content(), '3.660,00')
        self.page.locator('.dvv').click()
        self.page.wait_for_function('!document.querySelector("#dv-reader").open')
        self.assertEqual(self.page.evaluate('window.draws'), 1)
        self.page.locator('.dvv').click()
        self.assertEqual(self.page.evaluate('window.draws'), 2)

    def test_collapsed_preference_and_reading_from_collapsed_state(self):
        self.page.locator('#dv-btn').click()
        self.assertFalse(self.page.locator('#dv').is_visible())
        self.open_reader()
        self.assertTrue(self.page.locator('#dv').is_visible())
        self.page.locator('.dv-reader-head button').click()
        self.page.wait_for_function('document.querySelector("#dv").parentElement.id==="cp"')
        self.assertFalse(self.page.locator('#dv').is_visible())
        self.page.reload()
        self.assertFalse(self.page.locator('#dv').is_visible())
        self.assertTrue(self.page.locator('#dv-expand').is_visible())

    def test_mobile_laptop_and_fullscreen_fit_and_preserve_chart(self):
        for width, height in [(390, 844), (1024, 650), (1920, 1080)]:
            with self.subTest(viewport=width):
                self.page.set_viewport_size({'width': width, 'height': height})
                self.page.locator('#cp').evaluate('e=>e.classList.add("max")')
                self.open_reader()
                box=self.page.locator('#dv-reader').bounding_box()
                self.assertGreaterEqual(box['x'], 0);self.assertGreaterEqual(box['y'], 0)
                self.assertLessEqual(box['x']+box['width'],width+1);self.assertLessEqual(box['y']+box['height'],height+1)
                self.assertTrue(self.page.locator('.dv-reader-body').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
                self.assertTrue(self.page.locator('#dv .plg i').first.is_visible())
                self.page.locator('.dv-reader-head button').click()
                self.page.wait_for_function('document.querySelector("#dv").parentElement.id==="cp"')
                self.assertTrue(self.page.locator('#cp').evaluate('e=>e.classList.contains("max")'))
                self.page.locator('#cp').evaluate('e=>e.classList.remove("max")')

    def test_storage_blocked_and_unavailable_data_close_cleanly(self):
        self.page.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw Error('blocked')}})")
        self.page.reload()
        self.open_reader()
        self.page.locator('#dv').evaluate('e=>e.hidden=true')
        self.page.wait_for_function('!document.querySelector("#dv-reader").open')
        self.assertFalse(self.page.locator('#dv-head').is_visible())
        self.assertEqual(self.page.locator('#dv').evaluate('e=>e.parentElement.id'), 'cp')

    def test_tab_cycles_inside_reader_and_live_render_restores_focus(self):
        self.open_reader()
        self.page.locator('.dvm').focus()
        self.page.keyboard.press('Tab')
        self.assertEqual(self.page.evaluate('document.activeElement.closest("header").className'), 'dv-reader-head')
        self.page.keyboard.press('Shift+Tab')
        self.assertTrue(self.page.locator('.dvm').evaluate('e=>e===document.activeElement'))
        self.page.locator('.ppx').nth(1).focus()
        self.page.locator('#dv').evaluate('e=>e.innerHTML=e.innerHTML')
        self.page.wait_for_function('document.activeElement.textContent==="Fibonacci"')
        self.assertTrue(self.page.locator('.ppx').nth(1).evaluate('e=>e===document.activeElement'))
        self.page.keyboard.press('Escape')
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'dv-expand')


if __name__ == '__main__':
    unittest.main()
