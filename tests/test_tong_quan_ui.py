"""Tương tác của Tổng quan kết hợp: dữ liệu đa nguồn, bộ lọc, mật độ và riêng tư."""
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

import test_lam_quen as fixtures


class TongQuanUiTest(fixtures.LamQuenBrowserTest):
    def setUp(self):
        super().setUp()
        self.state['ledger_fail'] = False
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.rows = [
            {'id': 'tk-1', 'ten': 'Demo fixture', 'loai': 'demo', 'don_vi': 'USD', 'gia_tri': 1234.56, 'thay_doi': 234.56,
             'pct': 23.456, 'n': 10, 'mo': 1, 'tia': [1000, 1200, 1100, 1234.56], 'luc': self.timestamp},
            {'id': 'bot', 'ten': 'Signal fixture', 'loai': 'signal', 'don_vi': 'TP1', 'gia_tri': 3, 'mau': 5, 'pct': 60,
             'n': 5, 'mo': 0, 'tia': [], 'luc': self.timestamp},
            {'id': 'xu-huong', 'ten': 'Shadow fixture', 'loai': 'shadow', 'don_vi': 'win', 'gia_tri': 2, 'mau': 4, 'pct': 50,
             'n': 4, 'mo': 0, 'tia': [], 'luc': self.timestamp},
        ]

    def route(self, route):
        path = urlparse(route.request.url).path
        if path == '/api/tong-quan/so':
            self.requests.append((path, route.request.method))
            if self.state['ledger_fail']:
                return route.fulfill(status=503, body='unavailable')
            return route.fulfill(json={'so': self.rows, 'loi': []})
        if path == '/api/thi-truong':
            self.requests.append((path, route.request.method))
            tick = int(datetime.now(timezone.utc).timestamp() * 1000)
            return route.fulfill(json={'luc': self.timestamp, 'lich': {'co': False}, 'ds': [
                {'ma': 'XAUUSDp', 'goc': 'XAUUSD', 'q': [3600, 3600.2, tick], 'so_le': 2, 'ref': {'ngay': 3500},
                 'tia': [3500, 3530, 3600], 'kt': {'M15': {'atr': 10}, 'H1': {'d': 1}}, 'hom_nay': {'thap': 3500, 'cao': 3610}},
                {'ma': 'EURUSDp', 'goc': 'EURUSD', 'q': [1.1, 1.1001, tick], 'so_le': 5, 'ref': {'ngay': 1.09},
                 'tia': [1.09, 1.095, 1.1], 'kt': {}, 'hom_nay': {'thap': 1.09, 'cao': 1.11}},
            ]})
        return super().route(route)

    def refresh(self):
        self.page.locator('#tq-refresh').click()
        self.page.wait_for_function("!document.querySelector('#tq-refresh').disabled")

    def test_bo_loc_loai_so_luu_qua_tai_lai(self):
        self.open('/')
        self.assertEqual(self.page.locator('#tq-ledgers tr').count(), 3)
        self.page.locator('[data-ledger-filter="demo"]').click()
        self.assertEqual(self.page.locator('#tq-ledgers tr').count(), 1)
        self.assertIn('Demo fixture', self.page.locator('#tq-ledgers').inner_text())
        self.page.reload(wait_until='networkidle')
        self.assertEqual(self.page.locator('#tq-ledgers tr').count(), 1)
        self.page.locator('[data-ledger-filter="signal"]').focus()
        self.page.keyboard.press('Space')
        self.assertIn('Signal fixture', self.page.locator('#tq-ledgers').inner_text())

    def test_mat_do_va_chon_ma_duoc_luu(self):
        self.open('/')
        self.page.locator('button[data-density="comfortable"]').click()
        self.page.locator('#tq-symbol').select_option('EURUSDp')
        self.assertEqual(self.page.locator('#tq-feature-price').inner_text(), '1,10000')
        self.assertIn('EURUSDp', self.page.locator('#tq-feature-link').get_attribute('href'))
        self.page.reload(wait_until='networkidle')
        self.assertEqual(self.page.locator('main.tq').get_attribute('data-density'), 'comfortable')
        self.assertEqual(self.page.locator('#tq-symbol').input_value(), 'EURUSDp')

    def test_an_tien_ap_dung_ca_so_va_sau_cap_nhat(self):
        self.open('/')
        self.page.locator('#tq-privacy').click()
        self.assertTrue(self.page.locator('#tq-ledgers [data-money]').count() >= 2)
        self.assertEqual(self.page.locator('#tq-ledgers [data-money][aria-hidden="true"]').count(),
                         self.page.locator('#tq-ledgers [data-money]').count())
        self.refresh()
        self.assertEqual(self.page.locator('#tq-ledgers [data-money][aria-hidden="true"]').count(),
                         self.page.locator('#tq-ledgers [data-money]').count())

    def test_loi_mot_nguon_khong_xoa_so_cu_va_bao_cu(self):
        self.open('/')
        self.state['ledger_fail'] = True
        self.refresh()
        self.assertEqual(self.page.locator('#tq-ledgers tr').count(), 3)
        self.assertIn('có thể đã cũ', self.page.locator('#tq-ledger-state').inner_text())
        self.assertNotEqual(self.page.locator('#tq-equity').inner_text(), '—')

    def test_escape_du_lieu_so_va_khong_tao_html_tu_ten(self):
        self.rows[0]['ten'] = '<img src=x onerror=alert(1)>'
        self.open('/')
        self.assertEqual(self.page.locator('#tq-ledgers img').count(), 0)
        self.assertIn('<img', self.page.locator('#tq-ledgers').inner_text())
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))

    def test_mo_chi_tiet_va_chuan_bi_khong_tai_lai_trang(self):
        self.open('/')
        original = self.page.url
        self.page.locator('#tq-system-open').click()
        self.assertTrue(self.page.locator('#tq-system').evaluate('(el)=>el.open'))
        self.page.locator('#tq-daily-panel summary').click()
        self.page.locator('[data-daily="0"]').check()
        self.assertEqual(self.page.locator('#tq-count').inner_text(), '1 / 4')
        saved = json.loads(self.page.evaluate("localStorage.getItem('demo:tq-daily')"))
        self.assertEqual(saved['done'], [0])
        self.assertEqual(self.page.url.split('#')[0], original)
