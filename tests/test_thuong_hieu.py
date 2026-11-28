"""Tên hiển thị cố định: đặt tên khác trong cau-hinh.json cũng không đổi được tên trên trang."""
import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import thuong_hieu, trang, web  # noqa: E402

GIA = 'Ten Gia Mao XYZ'


class ThuongHieuTest(unittest.TestCase):
    def test_ten_co_dinh(self):
        self.assertEqual(thuong_hieu.TEN, 'Harry · Gold Research')

    def test_thanh_dau_bo_qua_ten_truyen_vao(self):
        h = trang.thanh_dau(GIA, 'hieu-suat', '')
        self.assertNotIn(GIA, h)
        self.assertIn('Harry', h)

    def test_cau_hinh_khong_doi_duoc_ten(self):
        with tempfile.TemporaryDirectory() as d:
            ch = Path(d) / 'cau-hinh.json'
            ch.write_text(json.dumps({'ten': GIA, 'gia': {}}), encoding='utf-8')
            srv = web.tao_may_chu(str(ch), port=0)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            u = f'http://127.0.0.1:{srv.server_address[1]}'
            try:
                for p in ('/hieu-suat', '/tin-tuc', '/cong-cu', '/hoc-giao-dich'):
                    html = urllib.request.urlopen(u + p, timeout=30).read().decode('utf-8')
                    self.assertNotIn(GIA, html, p)
                    self.assertIn('Gold Research', html, p)
            finally:
                srv.shutdown()
                srv.server_close()
                trang.MIEN_TRU = trang.MIEN_TRU_GOC

    def test_cau_hinh_mau_khong_con_khoa_ten(self):
        mau = json.loads((Path(__file__).resolve().parent.parent / 'cau-hinh.mau.json').read_text(encoding='utf-8'))
        self.assertNotIn('ten', mau)


if __name__ == '__main__':
    unittest.main()
