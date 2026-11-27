# -*- coding: utf-8 -*-
"""Bộ chuyển MCP (so_cong_khai.mcp_may_chu): mặc định tắt, chỉ công cụ đọc/tính, chỉ GET tới 127.0.0.1, kiểm tham số, không có công cụ đặt lệnh."""
import io
import tempfile
import unittest
import urllib.parse
from pathlib import Path

from so_cong_khai import mcp_may_chu as M


class Mo:
    def __init__(self):
        self.url = []

    def __call__(self, req, timeout=None):
        self.url.append((req.get_method(), req.full_url))
        return io.BytesIO(b'{"ok": true}')


class Mcp(unittest.TestCase):
    def test_mac_dinh_tat(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'c.json'
            p.write_text('{}', encoding='utf-8')
            self.assertEqual(M.main(['--cau-hinh', str(p)]), 1)

    def test_khong_co_cong_cu_nguy_hiem(self):
        ten = {t['name'] for t in M.danh_sach_cong_cu()}
        for cam in ('dat', 'dong', 'sua', 'xoa', 'order', 'shell', 'sql', 'tep', 'file'):
            self.assertFalse(any(cam in t for t in ten), cam)
        self.assertTrue(all(t['inputSchema']['additionalProperties'] is False for t in M.danh_sach_cong_cu()))

    def test_goi_dung_duong_va_kiem_tham_so(self):
        mo = Mo()
        r = M.xu_ly({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'dieu_kien_phuong_phap', 'arguments': {'snapshot_id': 'SN-abc', 'phuong_phap': 'harrison'}}},
                    'http://127.0.0.1:8765', mo)
        self.assertFalse(r['result']['isError'])
        phuong, url = mo.url[0]
        u = urllib.parse.urlparse(url)
        self.assertEqual((phuong, u.hostname, u.path, urllib.parse.parse_qs(u.query)), ('GET', '127.0.0.1', '/api/loi/dieu-kien', {'sn': ['SN-abc'], 'pp': ['harrison']}))
        for sai in ({'name': 'dat_lenh', 'arguments': {}}, {'name': 'doc_phieu', 'arguments': {}}, {'name': 'doc_phieu', 'arguments': {'id': 'x', 'duong': '/etc'}},
                    {'name': 'kiem_rui_ro', 'arguments': {'ma': 'XAU', 'chieu': 'MUA', 'vao': 'nhiều'}}):
            self.assertTrue(M.xu_ly({'id': 2, 'method': 'tools/call', 'params': sai}, 'http://127.0.0.1:8765', mo)['result']['isError'], sai)
        self.assertEqual(len(mo.url), 1)                                                   # tham số sai không gửi gì đi
        self.assertIsNone(M.xu_ly({'method': 'notifications/initialized'}, 'x', mo))
        self.assertEqual(M.xu_ly({'id': 3, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18'}}, 'x', mo)['result']['capabilities'], {'tools': {}})
        self.assertIn('error', M.xu_ly({'id': 4, 'method': 'resources/read'}, 'x', mo))


if __name__ == '__main__':
    unittest.main()
