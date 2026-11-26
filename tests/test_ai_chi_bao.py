# -*- coding: utf-8 -*-
"""AI đọc chỉ báo (so_cong_khai.ai_chi_bao): kiểm dữ liệu gửi lên, chung chốt chặn và sổ với Hỏi AI, không gọi Anthropic thật (Claude giả)."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from so_cong_khai import ai_chi_bao, ai_hoi, song

NOW = datetime(2026, 11, 26, 13, 0, tzinfo=timezone.utc)


def _body(**k):
    nen = [[1764150000 + 900 * i, 4000 + i, 4002 + i, 3999 + i, 4001 + i] for i in range(70)]
    b = {'tf': 'M15', 'ma': 'XAUUSD', 'lang': 'vi', 'nen': nen,
         'chi_bao': [{'ten': 'UT Bot (dừng lỗ dời theo ATR)', 'tham_so': {'a': 1, 'n': 10}, 'gia_tri': {'UT Bot': [4060.5, 4059.1]}, 'dau': [{'len': 1, 'cach': 3}]}]}
    b.update(k)
    return b


class ClaudeGia:
    def __init__(self, chu='Bức tranh chung: tăng.', dung='end_turn'):
        self.goi, self.chu, self.dung = [], chu, dung
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.goi.append(kw)
        return SimpleNamespace(content=[SimpleNamespace(type='text', text=self.chu)], stop_reason=self.dung, model=kw['model'],
                               usage=SimpleNamespace(input_tokens=3000, output_tokens=700, cache_creation_input_tokens=0, cache_read_input_tokens=0))


class AiChiBao(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.cfg = {'ai': {'bat': True, 'moi_ngay': 2, 'ngan_sach_usd': 5}, 'gia': {}}
        self.ly_do = song.ly_do
        song.ly_do = lambda: None                                  # coi như đang có giá trực tiếp

    def tearDown(self):
        song.ly_do = self.ly_do
        self.tmp.cleanup()

    def test_lam_sach(self):
        d = ai_chi_bao.lam_sach(_body(chi_bao=[{'ten': 'x' * 500, 'gia_tri': {'a': ['nan', 1e999, 3]}, 'dau': [{'len': 0, 'cach': 2}]}] * 40))
        self.assertEqual(len(d['chi_bao']), ai_chi_bao.TOI_DA_CB)
        self.assertEqual(len(d['chi_bao'][0]['ten']), 80)
        self.assertEqual(d['chi_bao'][0]['gia_tri']['a'], [None, None])
        self.assertEqual(d['chi_bao'][0]['dau_gan'], [{'chieu': 'BAN', 'cach_nen': 2}])
        self.assertEqual(ai_chi_bao.lam_sach(_body(tf='MN1'))['tf'], 'MN1')           # khung chỉ để xem cũng đọc được
        self.assertEqual(ai_chi_bao.lam_sach(_body(tf='MN1'))['tf'], 'MN1')           # khung chỉ để xem cũng đọc được
        for xau in (_body(tf='W2'), _body(chi_bao=[]), _body(nen=[[1, 2, 3, 4, 5]] * 5)):
            with self.assertRaises(ValueError):
                ai_chi_bao.lam_sach(xau)

    def test_hoi_va_chung_so_voi_hoi_ai(self):
        c = ClaudeGia()
        r = ai_chi_bao.hoi(self.cfg, self.out, _body(), client=c, now=NOW)
        self.assertTrue(r['ok'], r)
        self.assertEqual(r['tra_loi'], 'Bức tranh chung: tăng.')
        self.assertIn('không phải lời khuyên đầu tư', r['mien_tru'])
        kw = c.goi[0]
        self.assertEqual(kw['model'], 'claude-opus-5-5')
        self.assertIn('Vietnamese', kw['system'])
        self.assertIn('never promise', kw['system'])
        self.assertIn('UT Bot', kw['messages'][0]['content'])
        self.assertIn('2025-11-26 09:40,4000.0,4002.0,3999.0,4001.0', kw['messages'][0]['content'])
        rec = ai_hoi.doc_so(self.out)
        self.assertEqual((len(rec), rec[0]['loai']), (1, 'doc_chi_bao'))
        self.assertAlmostEqual(rec[0]['chi_phi_usd'], (3000 * 4 + 700 * 20) / 1e6)
        st = ai_hoi.trang_thai(self.cfg, self.out, NOW)
        self.assertEqual(st['hom_nay'], 1)                         # tính chung lượt với Hỏi AI
        self.assertEqual(st['gan_day'], [])                        # nhưng không hiện trong khung kết quả của Hỏi AI
        ai_chi_bao.hoi(self.cfg, self.out, _body(), client=c, now=NOW)
        r = ai_chi_bao.hoi(self.cfg, self.out, _body(), client=c, now=NOW)
        self.assertFalse(r['ok'])
        self.assertTrue(any('đủ 2 lượt' in x for x in r['chan']))
        self.assertEqual(len(c.goi), 2)

    def test_tat_va_tu_choi(self):
        c = ClaudeGia()
        r = ai_chi_bao.hoi({'ai': {'bat': False}, 'gia': {}}, self.out, _body(), client=c, now=NOW)
        self.assertFalse(r['ok'])
        self.assertIn('Phần AI đang tắt trong cấu hình.', r['chan'])
        self.assertEqual(c.goi, [])
        r = ai_chi_bao.hoi(self.cfg, self.out, _body(), client=ClaudeGia('', 'refusal'), now=NOW)
        self.assertFalse(r['ok'])
        self.assertEqual(len(ai_hoi.doc_so(self.out)), 1)          # lượt bị từ chối vẫn ghi sổ (đã tốn tiền)
        r = ai_chi_bao.hoi(self.cfg, self.out, _body(lang='en'), client=ClaudeGia('Overall: up.'), now=NOW)
        self.assertIn('not investment advice', r['mien_tru'])

    def test_ma_nguon_khong_dat_lenh(self):
        src = Path(ai_chi_bao.__file__).read_text(encoding='utf-8')
        for cam in ('order_send', 'TRADE_ACTION', 'MetaTrader5'):
            self.assertNotIn(cam, src)
        json.dumps(ai_chi_bao.MIEN_TRU)


if __name__ == '__main__':
    unittest.main()
