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
    def test_recover_selected_program_and_external_csv_with_checksums(self):
        import hashlib
        from so_cong_khai.local_runtime import build_id
        with tempfile.TemporaryDirectory() as tmp:
            root, program, dest = Path(tmp)/'data', Path(tmp)/'release', Path(tmp)/'backups'
            _du_an(root)
            (program/'so_cong_khai').mkdir(parents=True)
            (program/'so_cong_khai/web.py').write_text('x=1',encoding='utf-8')
            (program/'so_cong_khai/dich').mkdir()
            (program/'so_cong_khai/dich/en.json').write_text('{}',encoding='utf-8')
            (program/'so_cong_khai/api-token.txt').write_text('excluded',encoding='utf-8')
            source=Path(tmp)/'EA_events.csv';source.write_text('time,event\n1,closed\n',encoding='utf-8')
            (root/'cau-hinh.json').write_text(json.dumps({'tai_khoan':[{'ea':[{'tep':str(source)}]}]}),encoding='utf-8')
            (root/'du-lieu/local-release.json').write_text(json.dumps({'program_root':str(program),'build':build_id(program/'so_cong_khai')}),encoding='utf-8')
            result=S.tao(root,dest);self.assertTrue(result['ok'],result)
            with zipfile.ZipFile(result['tep']) as z:
                meta=json.loads(z.read('KHOI_PHUC.json'))
                for arc, digest in meta['sha256'].items():self.assertEqual(hashlib.sha256(z.read(arc)).hexdigest(),digest)
                self.assertEqual(z.read('nguon-ngoai/tk-1/ea-1.csv'),source.read_bytes())
                self.assertIn('chuong-trinh/so_cong_khai/dich/en.json',z.namelist())
                self.assertNotIn('chuong-trinh/so_cong_khai/api-token.txt',z.namelist())
                restored=Path(tmp)/'restored'
                z.extractall(restored)
                self.assertEqual(build_id(restored/'chuong-trinh/so_cong_khai'),meta['build'])
            source.unlink()
            self.assertFalse(S.tao(root,dest,now=datetime(2026,11,28))['ok'])

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
