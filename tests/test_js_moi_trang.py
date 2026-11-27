# -*- coding: utf-8 -*-
"""Mã JavaScript của MỌI trang webapp hợp cú pháp, cả bản tiếng Việt lẫn bản đã dịch sang tiếng Anh (`node --check`). Không cần máy chủ.

Vì sao: mã JS của các trang nằm trong chuỗi Python, nên bài kiểm Python bình thường không thấy lỗi JS. Ngày 26/11/2026 một lần chèn mã sai chỗ
làm cả trang Biểu đồ không chạy mà mọi bài kiểm vẫn qua. Bộ dịch cũng sửa chuỗi trong JS, nên kiểm cả bản tiếng Anh."""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from so_cong_khai import renko_trang, tong_quan
from so_cong_khai import (bat_dau_trang, bieu_do, cai_dat, da_khung_trang, cong_cu, dich, hieu_suat_trang, hoc_giao_dich, ke_hoach_trang, kien_thuc, kiem_lenh_trang,
                          kiem_tin_hieu_trang, ky_luat_trang, nhat_ky_trang, nhieu_tai_khoan, sao_luu, tai_khoan, telegram_nhom, thi_truong_trang, tin_tuc_trang)

TEN = 'Harry'
TRANG = {
    '/': lambda: tong_quan.trang_tong_quan(TEN),
    '/bieu-do': lambda: bieu_do.trang_bieu_do(TEN), '/cai-dat': lambda: cai_dat.trang_cai_dat(TEN), '/cong-cu': lambda: cong_cu.trang_cong_cu(TEN),
    '/hieu-suat': lambda: hieu_suat_trang.trang_hieu_suat(TEN), '/hoc-giao-dich': lambda: hoc_giao_dich.trang_hoc(TEN),
    '/ke-hoach': lambda: ke_hoach_trang.trang_ke_hoach(TEN), '/kien-thuc': lambda: kien_thuc.trang_kien_thuc(TEN),
    '/kiem-lenh': lambda: kiem_lenh_trang.trang_kiem_lenh(TEN), '/ky-luat': lambda: ky_luat_trang.trang_ky_luat(TEN),
    '/nhat-ky': lambda: nhat_ky_trang.trang_nhat_ky(TEN), '/cac-tai-khoan': lambda: nhieu_tai_khoan.trang_cac_tai_khoan(TEN),
    '/sao-luu': lambda: sao_luu.trang_sao_luu(TEN), '/tai-khoan': lambda: tai_khoan.trang_tai_khoan(TEN),
    '/telegram': lambda: telegram_nhom.trang_telegram(TEN), '/thi-truong': lambda: thi_truong_trang.trang_thi_truong(TEN),
    '/tin-tuc': lambda: tin_tuc_trang.trang_tin_tuc(TEN), '/bat-dau': lambda: bat_dau_trang.trang_bat_dau(TEN),
    '/da-khung': lambda: da_khung_trang.trang_da_khung(TEN), '/renko': lambda: renko_trang.trang_renko(TEN), '/kiem-tin-hieu': lambda: kiem_tin_hieu_trang.trang_kiem_tin_hieu(TEN),
}


@unittest.skipUnless(shutil.which('node'), 'máy không có Node.js')
class JsMoiTrang(unittest.TestCase):
    def test_cu_phap_ca_hai_ngon_ngu(self):
        en = dich.tu_dien('en')
        with tempfile.TemporaryDirectory() as d:
            for duong, dung in TRANG.items():
                goc = dung()
                self.assertIn('<title>', goc, duong)
                for lang, h in (('vi', goc), ('en', dich.dich_html(goc, en))):
                    for i, js in enumerate(re.findall(r'<script>(.*?)</script>', h, re.S)):
                        tep = Path(d) / f'{duong.strip("/")}-{lang}-{i}.js'
                        tep.write_text(js, encoding='utf-8')
                        r = subprocess.run(['node', '--check', str(tep)], capture_output=True, text=True, encoding='utf-8')
                        with self.subTest(trang=duong, lang=lang, doan=i):
                            self.assertEqual(r.returncode, 0, r.stderr[:500])


if __name__ == '__main__':
    unittest.main()
