"""Đồng bộ mẫu chỉ báo (mau_chi_bao.py): đọc, ghi, phiên bản, giữ bản còn mẫu, chặn dữ liệu lạ (đi vào HTML trên mọi máy); trang có lớp đồng bộ."""
import json
import tempfile
import unittest
from pathlib import Path

from so_cong_khai import mau_chi_bao as mcb

MAU = {'Lướt sóng M5': [{'k': 'ema', 'p': {'n': 9}, 'mau': '#4da3ff'}, {'k': 'ema', 'p': {'n': 21}}, {'k': 'rsi', 'p': {'n': 14}, 'an': False}],
       'Xu hướng H4': [{'k': 'supertrend', 'p': {'n': 10, 'k': 3}}]}


class MauChiBaoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.goc = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_doc_ghi_phien_ban(self):
        self.assertEqual(mcb.doc(self.goc)['ban'], None)
        self.assertEqual(mcb.luu(MAU, ['ema', 'rsi'], self.goc, now=5)['ban'], 1)
        x = mcb.doc(self.goc)
        self.assertEqual((x['ban'], x['mau'], x['sao']), (1, MAU, ['ema', 'rsi']))
        self.assertEqual(mcb.luu({}, [], self.goc)['ban'], 2)
        self.assertEqual(mcb.luu({}, [], self.goc)['ban'], 3)
        truoc = json.loads((self.goc / 'du-lieu' / 'mau-chi-bao.truoc.json').read_text(encoding='utf-8'))
        self.assertEqual(truoc['mau'], MAU)                                       # bản rỗng không đè lên bản còn mẫu

    def test_chan_du_lieu_la(self):
        xau = [({'<img src=x onerror=1>': []}, []), ({'a"b': []}, []), ({'M5': [{'k': '<b>'}]}, []), ({'M5': [{'k': 'ema', 'mau': 'red;x:url(a)'}]}, []),
               ({'M5': [{'k': 'ema', 'p': {'n': float('inf')}}]}, []), ({'M5': [{'k': 'ema', '<x>': 1}]}, []), ({}, ['<script>']), ([], []),
               ({f'm{i}': [] for i in range(mcb.TOI_DA_MAU + 1)}, []),
               ({'M5': [{'k': 'ema', 'p': {'n': 10 ** 400}}]}, [])]                      # lỗi đã gặp: số quá lớn làm isfinite ném OverflowError (lỗi 500)
        for mau, sao in xau:
            with self.subTest(mau=str(mau)[:40], sao=sao), self.assertRaises(ValueError):
                mcb.luu(mau, sao, self.goc)
        self.assertFalse((self.goc / 'du-lieu' / 'mau-chi-bao.json').exists())

    def test_trang_co_lop_dong_bo_va_moc(self):
        from so_cong_khai import bieu_do, bieu_do_chi_bao
        h = bieu_do.trang_bieu_do('Harry')
        self.assertIn('window.MCB=', h)
        self.assertIn("K=window.HVD_CB_KEY||'so-cbcn1'", mcb.JS)
        self.assertIn("CBKEY=window.HVD_CB_KEY||'so-cbcn1'", bieu_do_chi_bao.JS)  # cùng khóa theo tài khoản
        self.assertIn('dongBo:x=>{', bieu_do_chi_bao.JS)
        self.assertIn('&&n0>=3&&!confirm(', mcb.JS)                                # hỏi lại trước khi xóa sạch trên mọi máy


if __name__ == '__main__':
    unittest.main()
