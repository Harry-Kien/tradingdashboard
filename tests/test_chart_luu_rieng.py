"""Lưu bền, cách ly người dùng, CAS, phục hồi và đăng nhập qua lần mở lại."""
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from so_cong_khai import hinh_ve as H, luu_ben, tai_khoan_chart as A

USER_A, USER_B = 'a' * 32, 'b' * 32


def shape(id_='a', p=3500):
    return {'id': id_, 'k': 'ngang', 'a': {'t': 1795700000, 'p': p}}


class Store(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_hai_nguoi_cung_ma_khong_thay_hinh_cua_nhau(self):
        H.luu('XAUUSDp', [shape()], self.root, chu=USER_A, ban_co_so=None)
        self.assertEqual(H.doc('XAUUSDp', self.root, USER_B)['ds'], [])
        H.luu('XAUUSDp', [shape(p=3600)], self.root, chu=USER_B, ban_co_so=None)
        self.assertEqual(H.doc('XAUUSDp', self.root, USER_A)['ds'], [shape()])
        self.assertEqual(H.doc('XAUUSDp', self.root, USER_B)['ds'], [shape(p=3600)])

    def test_cas_tu_choi_tab_cu_khong_ghi_de(self):
        H.luu('XAUUSDp', [shape()], self.root, chu=USER_A, ban_co_so=None)
        with self.assertRaises(H.XungDot):
            H.luu('XAUUSDp', [], self.root, chu=USER_A, ban_co_so=None)
        H.luu('XAUUSDp', [shape(p=3600)], self.root, chu=USER_A, ban_co_so=1)
        with self.assertRaises(H.XungDot):
            H.luu('XAUUSDp', [shape(p=3700)], self.root, chu=USER_A, ban_co_so=1)
        self.assertEqual(H.doc('XAUUSDp', self.root, USER_A)['ds'], [shape(p=3600)])

    def test_hai_yeu_cau_cung_luc_chi_mot_ban_duoc_ghi(self):
        H.luu('XAUUSDp', [shape()], self.root, chu=USER_A)
        def write(p):
            try:
                H.luu('XAUUSDp', [shape(p=p)], self.root, chu=USER_A, ban_co_so=1)
                return 'saved'
            except H.XungDot:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(write, (3600, 3700)))
        self.assertEqual(sorted(result), ['conflict', 'saved'])
        self.assertEqual(H.doc('XAUUSDp', self.root, USER_A)['ban'], 2)

    def test_phuc_hoi_sau_xoa_la_phien_ban_moi(self):
        H.luu('XAUUSDp', [shape()], self.root, chu=USER_A, ban_co_so=None)
        H.luu('XAUUSDp', [], self.root, chu=USER_A, ban_co_so=1)
        x = H.khoi_phuc('XAUUSDp', 1, 2, self.root, USER_A)
        self.assertEqual((x['ban'], x['ds']), (3, [shape()]))
        self.assertEqual([x['ban'] for x in H.lich_su('XAUUSDp', self.root, USER_A)], [3, 2, 1])
        with self.assertRaises(ValueError):
            H.khoi_phuc('XAUUSDp', 1, None, self.root, USER_B)

    def test_ban_chinh_hong_lay_lai_lich_su_khong_reset_rong(self):
        H.luu('XAUUSDp', [shape()], self.root, chu=USER_A)
        p = H._tep('XAUUSDp', self.root, USER_A)
        p.write_text('{broken', encoding='utf-8')
        x = H.doc('XAUUSDp', self.root, USER_A)
        self.assertEqual(x['ds'], [shape()])
        H.luu('XAUUSDp', [shape()], self.root, chu=USER_A, ban_co_so=1)
        self.assertFalse(H.doc('XAUUSDp', self.root, USER_A).get('phuc_hoi'))
        bad = H._tep('OTHER', self.root, USER_A)
        bad.write_text('{broken', encoding='utf-8')
        with self.assertRaises(H.KhoLoi):
            H.luu('OTHER', [], self.root, chu=USER_A)

    def test_ghi_loi_khong_lam_mat_ban_dang_dung(self):
        p = self.root / 'data.json'
        luu_ben.ghi_json(p, {'ok': 1})
        with patch.object(luu_ben.os, 'replace', side_effect=OSError('disk error')), self.assertRaises(OSError):
            luu_ben.ghi_json(p, {'ok': 2})
        self.assertEqual(json.loads(p.read_text()), {'ok': 1})
        self.assertEqual(list(self.root.glob('*.tmp')), [])

    def test_nhap_ban_cu_khong_xoa_nguon_va_khong_nhan_doi(self):
        H.luu('XAU', [shape()], self.root)
        H.luu('XAUUSDp', [shape(p=3600)], self.root, chu=USER_A)
        a = H.nhap_cu(USER_A, 'XAUUSDp', self.root)
        b = H.nhap_cu(USER_A, 'XAUUSDp', self.root)
        self.assertEqual((a['so_hinh'], b['so_hinh']), (1, 0))
        self.assertEqual(H.doc('XAU', self.root)['ds'], [shape()])
        self.assertEqual(len(H.doc('XAUUSDp', self.root, USER_A)['ds']), 2)

    def test_so_phien_ban_duoc_gioi_han_va_du_lieu_sai_bi_chan(self):
        for i in range(H.GIU_PHIEN_BAN + 4):
            H.luu('XAUUSDp', [shape(p=3500 + i)], self.root, chu=USER_A)
        self.assertEqual(len(H.lich_su('XAUUSDp', self.root, USER_A)), H.GIU_PHIEN_BAN)
        for ds in ([shape(p=float('nan'))], [shape(), shape()], [{'id': 'a', 'k': 'xu', 'a': None}]):
            with self.assertRaises(ValueError):
                H.luu('XAUUSDp', ds, self.root, chu=USER_A)
        for who in ('../x', 'not-a-user', '..'):
            with self.assertRaises(ValueError):
                H.doc('XAUUSDp', self.root, who)


class Accounts(unittest.TestCase):
    setUp = Store.setUp
    tearDown = Store.tearDown
    def test_dang_nhap_lai_het_han_dang_xuat_va_mat_khau_khong_luu_ro(self):
        u, token = A.vao('harrison', 'a-test-password-12345', True, self.root, now=1000)
        cookie = A.cookie_header(token)
        self.assertEqual(A.hien_tai(cookie, self.root, now=1001), u)
        self.assertIsNone(A.hien_tai(cookie, self.root, now=1000 + A.HAN))
        raw = A._tep(self.root).read_text()
        self.assertNotIn('a-test-password-12345', raw)
        self.assertNotIn(token, raw)
        u2, _ = A.vao('HARRISON', 'a-test-password-12345', False, self.root, now=1002)
        self.assertEqual(u['id'], u2['id'])
        A.ra(cookie, self.root)
        self.assertIsNone(A.hien_tai(cookie, self.root, now=1003))
        self.assertIn('HttpOnly; SameSite=Strict', cookie)
        with self.assertRaises(A.LoiTaiKhoan):
            A.vao('harrison', 'a-wrong-password-12345', False, self.root, now=1004)

    def test_tai_khoan_dau_la_chu_va_kho_hong_khong_tu_tao_lai(self):
        u, _ = A.vao('owner', 'a-test-password-12345', True, self.root)
        v, _ = A.vao('other', 'a-test-password-12345', True, self.root)
        self.assertTrue(u['chu'])
        self.assertFalse(v['chu'])
        A._tep(self.root).write_text('{bad')
        with self.assertRaises(A.LoiTaiKhoan):
            A.vao('third', 'a-test-password-12345', True, self.root)
