"""Tài khoản và bản vẽ qua HTTP thật, cookie thật, khởi động lại máy chủ thật."""
import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from so_cong_khai import web


class ChartHTTP(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = self.root / 'cau-hinh.json'
        self.cfg.write_text(json.dumps({'ten': 'Test', 'gia': {}, 'tai_khoan': []}), encoding='utf-8')
        self.start()
        self.a = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.b = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def start(self):
        self.server = web.tao_may_chu(str(self.cfg), port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def tearDown(self):
        self.stop()
        self.tmp.cleanup()

    def req(self, client, path, data=None, uid=None):
        headers = {'X-So-Cong-Khai': '1', 'Content-Type': 'application/json'}
        if uid:
            headers['X-Chart-Owner'] = uid
        req = urllib.request.Request(self.base + path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
        try:
            r = client.open(req, timeout=20)
        except urllib.error.HTTPError as e:
            r = e
        with r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}, dict(r.headers)

    def signup(self, client, username):
        status, d, headers = self.req(client, '/api/tai-khoan-chart', {'viec': 'dang_ky', 'ten': username, 'mat_khau': 'only-test-password-01234'})
        self.assertEqual(status, 200, d)
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertNotIn('mat_khau', d)
        return d['nguoi']['id']

    def test_chu_them_ma_broker_vao_market_watch(self):
        da_them = []
        ma = SimpleNamespace(name='EURUSD.raw', digits=5, path='Forex', description='EUR/USD', visible=False)

        def chon(ten, bat):
            da_them.append((ten, bat))
            ma.visible = bat
            return True

        mt = SimpleNamespace(symbols_get=lambda: [ma], symbol_info=lambda ten: ma if ten == ma.name else None, symbol_select=chon)
        dm, api = '/api/ma/danh-muc', '/api/cai-dat'
        a = self.signup(self.a, 'owner_watch')
        b = self.signup(self.b, 'viewer_watch')
        data = {'viec': 'them_ma', 'ma': ma.name}
        with patch.object(web.da_ma, '_mt5', return_value=mt), patch.dict(web.song._tt, {'mt5': mt}):
            self.assertEqual(self.req(self.b, dm, uid=b)[0], 403)
            self.assertEqual(self.req(self.b, api, data, b)[0], 403)
            self.assertFalse(self.req(self.a, dm, uid=a)[1]['ds'][0]['market_watch'])
            self.assertEqual(self.req(self.a, '/api/ma?gon=1')[1]['ds'], [])
            self.assertEqual(self.req(self.a, api, {'viec': 'them_ma', 'ma': 'unknown'}, a)[0], 400)
            self.assertEqual(da_them, [])
            self.assertEqual(self.req(self.a, api, data, a)[0], 200)
            self.assertTrue(self.req(self.a, dm, uid=a)[1]['ds'][0]['market_watch'])
            self.assertEqual(self.req(self.a, '/api/ma?gon=1')[1]['ds'][0]['ma'], ma.name)
            self.assertEqual(da_them, [(ma.name, True)])

    def test_mau_chi_bao_rieng_va_tab_cu_khong_gui_sang_tai_khoan_khac(self):
        path = '/api/mau-chi-bao'
        self.assertEqual(self.req(self.a, path)[0], 401)
        a = self.signup(self.a, 'template_alpha')
        b = self.signup(self.b, 'template_beta')
        data = {'mau': {'Giá cũ 25 phút': [{'k': 'ema', 'p': {'n': 20}}]}, 'sao': ['ema', 'natr'], 'ban_co_so': None}
        self.assertEqual(self.req(self.a, path, data, a)[0], 200)
        self.assertEqual(self.req(self.b, path, uid=b)[1]['mau'], {})
        self.assertEqual(self.req(self.b, path, uid=a)[0], 409)
        self.assertEqual(self.req(self.b, path, data, a)[0], 409)
        self.assertEqual(self.req(self.a, path + '?lang=en', uid=a)[1]['mau'], data['mau'])
        self.stop()
        self.start()
        self.assertEqual(self.req(self.a, path, uid=a)[1]['sao'], data['sao'])

    def test_chu_dau_nhap_mau_cu_mot_lan_khong_ghi_de_mau_rieng(self):
        from so_cong_khai import mau_chi_bao
        old = {'Bộ cũ': [{'k': 'ema', 'p': {'n': 9}}]}
        mau_chi_bao.luu(old, ['ema'], self.root)
        a = self.signup(self.a, 'template_owner')
        b = self.signup(self.b, 'template_other')
        self.assertEqual(self.req(self.b, '/api/tai-khoan-chart', {'viec': 'nhap_cu'}, b)[0], 403)
        j = self.req(self.a, '/api/tai-khoan-chart', {'viec': 'nhap_cu'}, a)[1]
        self.assertEqual(j['so_mau'], 1)
        self.assertEqual(self.req(self.a, '/api/mau-chi-bao', uid=a)[1]['mau'], old)
        personal = {'Bộ mới': [{'k': 'natr', 'p': {'n': 14}}]}
        self.req(self.a, '/api/mau-chi-bao', {'mau': personal, 'sao': [], 'ban_co_so': 1}, a)
        j = self.req(self.a, '/api/tai-khoan-chart', {'viec': 'nhap_cu'}, a)[1]
        self.assertEqual(j['so_mau'], 0)
        self.assertEqual(self.req(self.a, '/api/mau-chi-bao', uid=a)[1]['mau'], personal)
        self.assertEqual(mau_chi_bao.doc(self.root)['mau'], old)

    def test_luu_dang_xuat_dang_nhap_va_khoi_dong_lai(self):
        uid = self.signup(self.a, 'user_alpha')
        ds = [{'id': 'note', 'k': 'chu', 'a': {'t': 1795700000, 'p': 3500}, 'chu': 'Giá cũ 25 phút'}]
        self.assertEqual(self.req(self.a, '/api/hinh-ve', {'ma': 'XAUUSDp', 'ds': ds, 'ban_co_so': None}, uid)[0], 200)
        self.assertEqual(self.req(self.a, '/api/tai-khoan-chart', {'viec': 'dang_xuat'})[0], 200)
        self.assertEqual(self.req(self.a, '/api/hinh-ve?ma=XAUUSDp', uid=uid)[0], 401)
        self.assertEqual(self.req(self.a, '/api/tai-khoan-chart', {'viec': 'dang_nhap', 'ten': 'user_alpha', 'mat_khau': 'only-test-password-01234'})[0], 200)
        self.stop()
        self.start()
        # Cookie tồn tại qua restart; ngôn ngữ không được thay nội dung ghi chú cá nhân.
        status, saved, _ = self.req(self.a, '/api/hinh-ve?ma=XAUUSDp&lang=en', uid=uid)
        self.assertEqual((status, saved['ds']), (200, ds))
        self.assertEqual(self.req(self.a, '/api/tai-khoan-chart')[1]['nguoi']['id'], uid)

    def test_cach_ly_cas_va_khong_nhan_uid_tu_client(self):
        ua, ub = self.signup(self.a, 'user_alpha'), self.signup(self.b, 'user_beta')
        ds = [{'id': 'a', 'k': 'ngang', 'a': {'t': 1, 'p': 2}}]
        self.assertEqual(self.req(self.a, '/api/hinh-ve', {'ma': 'XAUUSDp', 'ds': ds, 'ban_co_so': None}, ua)[0], 200)
        self.assertEqual(self.req(self.b, '/api/hinh-ve?ma=XAUUSDp', uid=ub)[1]['ds'], [])
        self.assertEqual(self.req(self.b, '/api/hinh-ve?ma=XAUUSDp', uid=ua)[0], 409)
        self.assertEqual(self.req(self.b, '/api/hinh-ve', {'ma': 'XAUUSDp', 'ds': [], 'ban_co_so': None, 'chu': ua}, ub)[0], 200)
        self.assertEqual(self.req(self.a, '/api/hinh-ve?ma=XAUUSDp', uid=ua)[1]['ds'], ds)
        status, conflict, _ = self.req(self.a, '/api/hinh-ve', {'ma': 'XAUUSDp', 'ds': [], 'ban_co_so': None}, ua)
        self.assertEqual((status, conflict['xung_dot'], conflict['ds']), (409, True, ds))
        self.assertEqual(self.req(self.b, '/api/tai-khoan-chart', {'viec': 'nhap_cu'})[0], 403)
        self.assertEqual(self.req(self.a, '/api/hinh-ve', {'ma': 'XAUUSDp', 'ds': []}, ua)[0], 400)

    def test_lich_su_phuc_hoi_va_khong_lo_tep_tai_khoan(self):
        uid = self.signup(self.a, 'user_alpha')
        ds = [{'id': 'a', 'k': 'ngang', 'a': {'t': 1, 'p': 2}}]
        self.req(self.a, '/api/hinh-ve', {'ma': 'XAUUSDp', 'ds': ds, 'ban_co_so': None}, uid)
        self.req(self.a, '/api/hinh-ve', {'ma': 'XAUUSDp', 'ds': [], 'ban_co_so': 1}, uid)
        versions = self.req(self.a, '/api/hinh-ve/lich-su?ma=XAUUSDp', uid=uid)[1]['ds']
        self.assertEqual([v['ban'] for v in versions], [2, 1])
        status, restored, _ = self.req(self.a, '/api/hinh-ve', {'viec': 'khoi_phuc', 'ma': 'XAUUSDp', 'ban': 1, 'ban_co_so': 2}, uid)
        self.assertEqual((status, restored['ban'], restored['ds']), (200, 3, ds))
        with self.assertRaises(urllib.error.HTTPError) as denied:
            self.a.open(self.base + '/du-lieu/tai-khoan-chart.json')
        self.assertEqual(denied.exception.code, 404)
