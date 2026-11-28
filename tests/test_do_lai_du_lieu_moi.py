# -*- coding: utf-8 -*-
"""Đo lại trên dữ liệu mới (cong-cu/do_lai_du_lieu_moi.py): luật kết luận đã đăng ký, tóm tắt nhật ký, khối ở trang Kiến thức và lời nhắc tự kiểm."""
import importlib.util
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location('do_lai', Path(__file__).resolve().parent.parent / 'cong-cu' / 'do_lai_du_lieu_moi.py')
DL = importlib.util.module_from_spec(spec)
spec.loader.exec_module(DL)


class PhanDinh(unittest.TestCase):
    def test_duoi_30_lenh_chua_ket_luan(self):
        x = DL.phan_dinh([1.0] * 29, 0.1)
        self.assertEqual((x['ket'], x['ci90'], x['n']), ('chua_du', None, 29))
        self.assertEqual(DL.phan_dinh([], 0.1)['ket'], 'chua_du')

    def test_ba_ket_luan(self):
        self.assertEqual(DL.phan_dinh(np.r_[np.full(40, 1.0), np.full(20, -1.0)], 0.1)['ket'], 'co_lai')
        lo = DL.phan_dinh(np.r_[np.full(15, 1.0), np.full(45, -1.0)], 0.1)
        self.assertEqual((lo['ket'], lo['kem_ky_vong']), ('lo_ro', True))
        self.assertEqual(DL.phan_dinh(np.r_[np.full(30, 1.0), np.full(30, -1.0)], 0.0)['ket'], 'chua_ro')

    def test_kem_ky_vong_ro(self):
        r = np.r_[np.full(36, 1.0), np.full(24, -1.0)]                 # trung bình +0,2R
        self.assertFalse(DL.phan_dinh(r, 0.1)['kem_ky_vong'])
        self.assertTrue(DL.phan_dinh(r, 0.9)['kem_ky_vong'])            # cận trên vẫn dưới mức đã đo ở phần kiểm

    def test_lap_lai_duoc(self):
        r = np.random.default_rng(3).normal(0.05, 1, 80)
        self.assertEqual(DL.phan_dinh(r, 0.1), DL.phan_dinh(r, 0.1))


class NhatKy(unittest.TestCase):
    def test_bo_dong_trung_va_lenh_chua_xong(self):
        ds = [{'id': 1, 'ten': 'A', 'tt': 'thang', 'r': 2.0}, {'id': 2, 'ten': 'A', 'tt': 'thua', 'r': -1.0}, {'id': 3, 'ten': 'A', 'tt': 'thang', 'r': 2.0, 'trung_voi': 1},
              {'id': 4, 'ten': 'B', 'tt': 'dang_mo', 'r': None}, {'id': 5, 'ten': 'B', 'tt': 'het_gio', 'r': 0.3}]
        t = DL.tom_nhat_ky(ds)
        self.assertEqual(t['A'], {'n': 2, 'thang': 1, 'tong_r': 1.0})
        self.assertEqual(t['Tất cả'], {'n': 2, 'thang': 1, 'tong_r': 1.0})
        self.assertNotIn('B', t)


class TrangVaTuKiem(unittest.TestCase):
    KQ = {'luc': '2026-12-26T01:00:00+00:00', 'tu': '2026-11-25T00:00:00+00:00', 'den': '2026-12-25T21:00:00+00:00', 'so_ngay': 30, 'doi_chieu': False,
          'muc': [{'nhom': 'Luật bot', 'ten': 'Luật bot · bản hiện tại (vào ngay)', 'n': 42, 'thang': 52.4, 'r_tb': -0.21, 'tong': -8.8, 'ky_vong': 0.175,
                   'ci90': [-0.4, -0.02], 'ket': 'lo_ro', 'kem_ky_vong': True},
                  {'nhom': 'Công thức phiếu', 'ten': 'Fibonacci', 'n': 3, 'thang': 33.3, 'r_tb': 0.1, 'tong': 0.3, 'ky_vong': -0.026, 'ci90': None, 'ket': 'chua_du',
                   'kem_ky_vong': False}],
          'nhat_ky': {'Tất cả': {'n': 10, 'thang': 4, 'tong_r': -1.5}}}

    def test_khoi_kien_thuc(self):
        from so_cong_khai import kien_thuc
        with tempfile.TemporaryDirectory() as d:
            tep = Path(d) / 'du-lieu-moi.json'
            self.assertIn('Chưa chạy lần nào', kien_thuc.du_lieu_moi_html(tep))
            tep.write_text(json.dumps(self.KQ), encoding='utf-8')
            h = kien_thuc.du_lieu_moi_html(tep)
        for must in ('Kiểm trên dữ liệu mới', '30 ngày', 'đang lỗ rõ · kém kỳ vọng rõ', 'chưa đủ lệnh', '−' if False else '-0,210', '+0,175', '10 lệnh, thắng 4'):
            self.assertIn(must, h)
        self.assertIn('id="du-lieu-moi"', kien_thuc.trang_kien_thuc('Thử'))

    def test_tu_kiem_nhac_luat_lo_ro(self):
        from datetime import datetime, timezone
        from so_cong_khai import suc_khoe
        # Lỗi đã gặp (26/11/2026): bài này từng ghi số giả vào out/du-lieu-moi.json THẬT rồi ghi trả lại; hai lượt kiểm chạy cùng lúc thì lượt sau
        # "khôi phục" đúng bản giả, và trang Biểu đồ báo luật bot "đang lỗ rõ" theo số giả. Giờ chỉ dùng tệp tạm.
        that_tep = Path(suc_khoe.__file__).resolve().parent.parent / 'out' / 'du-lieu-moi.json'
        truoc = that_tep.read_bytes() if that_tep.exists() else None
        with tempfile.TemporaryDirectory() as d:
            tam = Path(d) / 'du-lieu-moi.json'
            tam.write_text(json.dumps(self.KQ), encoding='utf-8')
            that = suc_khoe.song.khung_song
            suc_khoe.song.khung_song = lambda *a, **k: None                       # không bao giờ nối MT5 trong bài kiểm
            try:
                with mock.patch.object(suc_khoe, 'TEP_DU_LIEU_MOI', tam):
                    kq = suc_khoe.kiem({'gia': {}}, Path(d), d={}, now=datetime(2026, 12, 27, tzinfo=timezone.utc))
            finally:
                suc_khoe.song.khung_song = that
        self.assertEqual(that_tep.read_bytes() if that_tep.exists() else None, truoc)      # tệp thật không bị đụng tới
        m = next(x for x in kq['muc'] if x['ten'] == 'Đo lại trên dữ liệu mới')
        self.assertEqual(m['muc'], 'chu_y')
        self.assertIn('Luật bot · bản hiện tại', m['chi_tiet'])


if __name__ == '__main__':
    unittest.main()
