# -*- coding: utf-8 -*-
"""Sao lưu toàn bộ (so_cong_khai.sao_luu): chép đúng tệp, bỏ tệp giống khóa, tệp nén đọc lại được, giữ đúng số bản, nơi cất phải ngoài dự án."""
import json
import os
import tempfile
import time
import unittest
import zipfile
from datetime import datetime
from pathlib import Path

from so_cong_khai import sao_luu as S


def _du_an(goc: Path) -> None:
    for ten, nd in {'so_cong_khai/a.py': 'x=1', 'du-lieu/nhat-ky-diem-vao.json': '[]', 'cau-hinh.json': '{}', 'out/diem-vao.json': '{}',
                    'out/chup.png': 'anh', 'tinh/logo.webp': 'logo', '.env': 'KHOA=1', 'du-lieu/api-token.txt': 't', 'khoa.pem': 'k',
                    'so_cong_khai/__pycache__/a.pyc': 'b', 'out/kiem-giao-dien/x.json': '{}', 'out/nghien-cuu.pkl': 'p'}.items():
        p = goc / ten
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(nd, encoding='utf-8')


class ChonTep(unittest.TestCase):
    def test_chep_va_bo(self):
        with tempfile.TemporaryDirectory() as d:
            goc = Path(d) / 'duan'
            _du_an(goc)
            ten = sorted(p.relative_to(goc).as_posix() for p in S.danh_sach_tep(goc))
        self.assertEqual(ten, ['cau-hinh.json', 'du-lieu/nhat-ky-diem-vao.json', 'out/diem-vao.json', 'so_cong_khai/a.py', 'tinh/logo.webp'])


class TaoBan(unittest.TestCase):
    def test_tao_kiem_va_giu(self):
        with tempfile.TemporaryDirectory() as d:
            goc, dich = Path(d) / 'duan', Path(d) / 'noi-cat'
            _du_an(goc)
            for i in range(4):
                kq = S.tao(goc, dich, now=datetime(2026, 11, 25, 10, i), giu=3)
                self.assertTrue(kq['ok'], kq)
            ban = S.cac_ban(dich)
            self.assertEqual([p.name for p in ban], ['so-cong-khai-20261125-100300.zip', 'so-cong-khai-20261125-100200.zip', 'so-cong-khai-20261125-100100.zip'])
            with zipfile.ZipFile(ban[0]) as z:
                self.assertIsNone(z.testzip())
                ds = set(z.namelist())
            self.assertIn('du-lieu/nhat-ky-diem-vao.json', ds)
            self.assertIn('DOC_TOI.txt', ds)
            self.assertNotIn('.env', ds)
            self.assertEqual(kq['so_tep'], 6)                                   # 5 tệp dự án + du-lieu/sao-luu.json do lần đầu ghi ra
            self.assertEqual(json.loads((goc / 'du-lieu' / 'sao-luu.json').read_text(encoding='utf-8'))['lan_cuoi']['tep'], str(ban[0]))
            self.assertFalse(list(dich.glob('*.dang-ghi')))

    def test_tuoi(self):
        with tempfile.TemporaryDirectory() as d:
            dich = Path(d)
            self.assertIsNone(S.tuoi_gio(dich))
            p = dich / 'so-cong-khai-20261124-090000.zip'
            p.write_bytes(b'')
            cu = time.time() - 30 * 3600
            os.utime(p, (cu, cu))
            self.assertAlmostEqual(S.tuoi_gio(dich), 30, delta=0.1)


class NoiCat(unittest.TestCase):
    def test_dat_noi(self):
        with tempfile.TemporaryDirectory() as d:
            goc = Path(d) / 'duan'
            _du_an(goc)
            self.assertFalse(S.dat_noi('', goc)[0])
            self.assertFalse(S.dat_noi('tuong-doi', goc)[0])
            ok, ly_do = S.dat_noi(str(goc / 'sao-luu'), goc)
            self.assertFalse(ok)
            self.assertIn('ngoài thư mục dự án', ly_do)
            ok, _ = S.dat_noi(str(Path(d) / 'noi-khac'), goc)
            self.assertTrue(ok)
            self.assertEqual(S.noi(goc), Path(d) / 'noi-khac')
            self.assertTrue((Path(d) / 'noi-khac').is_dir())

    def test_suc_khoe(self):
        with tempfile.TemporaryDirectory() as d:
            goc = Path(d) / 'duan'
            _du_an(goc)
            S.dat_noi(str(Path(d) / 'noi-khac'), goc)
            self.assertEqual(S.muc_suc_khoe(goc)['muc'], 'chu_y')              # chưa có bản nào
            S.tao(goc)
            m = S.muc_suc_khoe(goc)
            self.assertIn('Bản mới nhất cách đây 0 giờ', m['chi_tiet'])        # cùng ổ đĩa tạm nên có thể là 'chu_y' (cùng ổ cứng)
            self.assertIn(m['muc'], ('tot', 'chu_y'))


if __name__ == '__main__':
    unittest.main()
