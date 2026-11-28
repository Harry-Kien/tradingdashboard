"""Kiểm luồng bắt đầu bằng trình duyệt với API giả; không nối MT5 thật."""
import importlib.util
import json
import unittest

from so_cong_khai import bat_dau_trang, dich, tong_quan
from so_cong_khai.thuong_hieu import TEN


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Playwright là thư viện kiểm giao diện tùy chọn')
class LamQuenBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
        cls.runtime = sync_playwright().start()
        try:
            cls.browser = cls.runtime.chromium.launch()
        except Exception as error:  # noqa: BLE001 - máy kiểm không cài Chromium thì bỏ qua
            cls.runtime.stop()
            raise unittest.SkipTest('Chưa có Chromium cho Playwright') from error

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.runtime.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 390, 'height': 844})
        self.page = self.context.new_page()
        self.errors, self.requests = [], []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.state = {'connected': False, 'fresh': False, 'account': True, 'fail': False}
        self.context.route('**/*', self.route)
        self.origin = 'http://127.0.0.1:19876'

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])
        self.assertFalse(any(method != 'GET' for _, method in self.requests))

    def route(self, route):
        from urllib.parse import urlparse  # noqa: PLC0415
        request = route.request
        path = urlparse(request.url).path
        self.requests.append((path, request.method))
        if path in ('/', '/bat-dau'):
            html = tong_quan.trang_tong_quan(TEN) if path == '/' else bat_dau_trang.trang_bat_dau(TEN)
            if 'lang=en' in (request.headers.get('cookie') or ''):
                html = dich.dich_phan_hoi(html.encode(), 'text/html', 'en').decode()
            return route.fulfill(content_type='text/html', body=html)
        if self.state['fail'] and path in ('/api/tai-khoan', '/api/tinh-trang'):
            return route.fulfill(status=503, body='unavailable')
        payload = {}
        if path == '/api/tinh-trang':
            payload = {'muc': [{'id': 'mt5-price', 'ten': 'Giá trực tiếp từ MT5', 'muc': 'tot',
                                'chi_tiet': 'Connection test', 'ket_noi': self.state['connected'], 'gia_moi': self.state['fresh']}],
                       'dem': {'tot': 1, 'chu_y': 0, 'loi': 0}}
        elif path == '/api/tai-khoan':
            payload = {'san_sang': self.state['account'], 'loai': 'DEMO', 'so': '•••123', 'tien': 'USD',
                       'von': 1000, 'treo': 0, 'lenh': [], 'cho': [], 'rui_ro': {}, 'may_chu': 'Test', 'don_bay': 100}
        elif path == '/api/thi-truong':
            payload = {'san_sang': False, 'ds': [], 'lich': {'co': False}}
        elif path == '/api/canh-bao':
            payload = {'ds': []}
        elif path == '/api/tong-quan/so':
            payload = {'so': [], 'loi': []}
        elif path == '/api/giam-sat':
            payload = {'san_sang': False, 'ds': []}
        elif path.endswith('.woff2'):
            return route.abort()
        return route.fulfill(json=payload)

    def open(self, path='/bat-dau'):
        self.page.goto(self.origin + path, wait_until='networkidle')

    def test_tat_gia_khong_duoc_bao_ket_noi_va_hoan_tat(self):
        self.open()
        self.assertEqual(self.page.locator('#b-mt5').get_attribute('data-tt'), 'can')
        self.assertIn('Chưa nối được MT5', self.page.locator('#b-mt5 .bd-kq').inner_text())
        self.assertEqual(self.page.locator('.lq-count').text_content(), '1 / 4')

    def test_ket_noi_co_gia_cu_van_ghi_ro_can_xem(self):
        self.state['connected'] = True
        self.open()
        self.assertIn('Đã nối MT5', self.page.locator('#b-mt5 .bd-kq').inner_text())
        self.assertEqual(self.page.locator('#b-mt5').get_attribute('data-tt'), 'can')
        self.assertEqual(self.page.locator('.lq-count').text_content(), '2 / 4')
        self.state['fresh'] = True
        self.page.locator('#bd-refresh').click()
        self.page.wait_for_function("!document.querySelector('#bd-refresh').disabled")
        self.assertEqual(self.page.locator('#b-mt5').get_attribute('data-tt'), 'tot')

    def test_chi_luu_xac_nhan_thu_cong_khong_luu_ket_noi(self):
        self.state.update(connected=True, fresh=True)
        self.open()
        for name in ('chart', 'risk'):
            self.page.locator(f'[data-lq-confirm="{name}"]').check()
        self.assertEqual(self.page.locator('.lq-count').text_content(), '4 / 4')
        saved = json.loads(self.page.evaluate("localStorage.getItem('demo:so-lam-quen-v1')"))
        self.assertEqual(saved, {'chart': True, 'risk': True})
        self.open('/')
        self.assertEqual(self.page.locator('.lq-count').text_content(), '4 / 4')
        self.state.update(connected=False, account=False)
        self.page.locator('#tq-refresh').click()
        self.page.wait_for_function("!document.querySelector('#tq-refresh').disabled")
        self.assertEqual(self.page.locator('.lq-count').text_content(), '2 / 4')
        self.assertNotIn('hoàn tất', self.page.locator('[data-lq-next]').text_content())

    def test_loi_cap_nhat_khong_giu_ket_noi_da_xac_minh(self):
        self.state.update(connected=True, fresh=True)
        self.open()
        self.assertEqual(self.page.locator('.lq-count').text_content(), '2 / 4')
        self.state['fail'] = True
        self.page.locator('#bd-refresh').click()
        self.page.wait_for_function("!document.querySelector('#bd-refresh').disabled")
        self.assertEqual(self.page.locator('.lq-count').text_content(), '0 / 4')
        self.assertEqual(self.page.locator('#b-tk').get_attribute('data-tt'), 'can')
        self.assertEqual(self.page.locator('[data-lq-step="mt5"] small').inner_text(), 'Chưa kiểm tra kết nối')

    def test_kho_luu_bi_chan_van_thu_duoc_va_bao_ro(self):
        self.context.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw Error('blocked')}})")
        self.open()
        self.page.locator('[data-lq-confirm="chart"]').check()
        self.assertTrue(self.page.locator('.lq-save').is_visible())
        self.assertEqual(self.page.locator('.lq-count').text_content(), '2 / 4')

    def test_tieng_anh_mobile_va_khong_tran_ngang(self):
        self.context.add_cookies([{'name': 'lang', 'value': 'en', 'url': self.origin}])
        self.state.update(connected=True, fresh=True)
        self.open()
        self.assertEqual(self.page.locator('.lq h2').inner_text(), 'Get started with confidence')
        self.assertIn('Verified', self.page.locator('[data-lq-step="mt5"] small').inner_text())
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        self.open('/')
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))


if __name__ == '__main__':
    unittest.main()
