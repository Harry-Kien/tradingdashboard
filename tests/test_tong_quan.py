"""Trang chủ thống nhất, không dựng sổ hoặc phụ thuộc MT5 để trả HTML."""
import json
from functools import partial
from http_owner import owner_cookie, owner_urlopen
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from so_cong_khai import dich, tong_quan, trang, web
from so_cong_khai.thuong_hieu import TEN


class TongQuanTest(unittest.TestCase):
    def test_trang_chu_khong_doc_so_ghi_tep_hay_chuyen_huong(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'c.json'
            config.write_text(json.dumps({'gia': {'ma_nguon': []}}), encoding='utf-8')
            server = web.tao_may_chu(str(config), port=0)
            owner_cookie(config.parent)
            open_owner = partial(owner_urlopen, root=config.parent)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                with patch.object(web, 'xay', side_effect=AssertionError('Không dựng sổ từ trang chủ')) as build:
                    for path in ('/', '/index.html'):
                        url = f'http://127.0.0.1:{server.server_port}{path}'
                        with open_owner(url, timeout=5) as response:
                            html = response.read().decode('utf-8')
                            self.assertEqual(response.status, 200)
                            self.assertEqual(response.url, url)
                            self.assertIn('Tổng quan phiên giao dịch', html)
                            self.assertIn('href="/so-cong-khai"', html)
                    build.assert_not_called()
                self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ['c.json', 'du-lieu'])
            finally:
                server.shutdown()
                server.server_close()

    def test_tieng_anh_dich_day_du(self):
        missing = set()
        html = dich.dich_phan_hoi(tong_quan.trang_tong_quan(TEN).encode(), 'text/html', 'en', missing).decode()
        self.assertEqual(sorted(missing), [])
        self.assertIn('<html lang="en"', html)
        self.assertIn('Your trading overview', html)

    def test_menu_so_khong_trung_trang_chu(self):
        entries = [item for group in trang.MENU if group[3] for item in group[3]]
        self.assertTrue(any(item[0] == 'so-cong-khai' and item[2] == '/so-cong-khai' for item in entries))
        overview = tong_quan.trang_tong_quan(TEN)
        self.assertIn('href="/" aria-current="page"', overview)
        self.assertNotIn('id="refresh"', overview)  # nút chung này gây tự tải lại cả trang và mất tương tác


if __name__ == '__main__':
    unittest.main()
