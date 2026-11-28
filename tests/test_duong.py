"""Bài kiểm cho so_cong_khai.duong: gốc chương trình tách khỏi gốc dữ liệu. Chạy từ mã nguồn thì hai gốc trùng nhau như trước;
bản đóng gói thì dữ liệu nằm ở %LOCALAPPDATA%. Không đụng dữ liệu thật (mọi thư mục ghi là thư mục tạm)."""
import json
import os
import sys
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import duong  # noqa: E402


class DuongTest(unittest.TestCase):
    def test_ma_nguon_thi_hai_goc_trung_nhau(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('HGR_DU_LIEU', None)
            self.assertFalse(duong.DONG_GOI)
            self.assertEqual(duong.goc_du_lieu(), GOC)
            self.assertEqual(duong.goc_chuong_trinh(), GOC)

    def test_bien_moi_truong_de_len(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(os.environ, {'HGR_DU_LIEU': t}):
            self.assertEqual(duong.goc_du_lieu(), Path(t))

    def test_dong_goi_thi_du_lieu_o_localappdata(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.object(duong, 'DONG_GOI', True), \
                mock.patch.dict(os.environ, {'LOCALAPPDATA': t}):
            os.environ.pop('HGR_DU_LIEU', None)
            self.assertEqual(duong.goc_du_lieu(), Path(t) / 'HarryGoldResearch')

    def test_goc_du_lieu_co_dau(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / 'Nguyễn Văn A' / 'Dữ liệu'
            with mock.patch.dict(os.environ, {'HGR_DU_LIEU': str(d)}):
                p = duong.chuan_bi()
                self.assertTrue(p.is_file())
                self.assertEqual(json.loads(p.read_text(encoding='utf-8'))['gia']['mt5']['chi_demo'], True)
                self.assertTrue((d / 'du-lieu').is_dir() and (d / 'out').is_dir())

    def test_chuan_bi_khong_ghi_de(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(os.environ, {'HGR_DU_LIEU': t}):
            (Path(t) / 'cau-hinh.json').write_text('{"ten": "cu"}', encoding='utf-8')
            duong.chuan_bi()
            self.assertEqual(json.loads((Path(t) / 'cau-hinh.json').read_text(encoding='utf-8')), {'ten': 'cu'})

    def test_lenh_mo_dun(self):
        self.assertEqual(duong.lenh_mo_dun('a.b', 'x')[1:], ['-X', 'utf8', '-m', 'a.b', 'x'])
        with mock.patch.object(duong, 'DONG_GOI', True):
            self.assertEqual(duong.lenh_mo_dun('a.b', 'x')[1:], ['--mo-dun', 'a.b', 'x'])


if __name__ == '__main__':
    unittest.main()
