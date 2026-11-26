# -*- coding: utf-8 -*-
"""Gia sư giao dịch (so_cong_khai.gia_su), với Claude GIẢ: không gọi mạng, không tốn tiền; sổ và buổi học ghi vào thư mục tạm."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

from so_cong_khai import gia_su as G

NOW = datetime(2026, 11, 26, 8, tzinfo=timezone.utc)
BAN_DO = '```\nQuản lý rủi ro         overall: ███░░░░░░░ 30%\nRủi ro mỗi lệnh  [████░░░░░░]  2/5\n```'


class ClaudeGia:
    def __init__(self, dung='end_turn', loi=None, chu=None):
        self.goi, self.dung, self.loi, self.chu = [], dung, loi, chu
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **k):
        if self.loi:
            raise self.loi
        self.goi.append(json.loads(json.dumps(k, default=lambda o: vars(o))))    # chụp lại đúng những gì được gửi
        khoi = [NS(type='thinking', thinking='', signature=f'sig{len(self.goi)}'),
                NS(type='text', text=self.chu or f'Câu hỏi số {len(self.goi)}: rủi ro mỗi lệnh là gì?', citations=None)]
        return NS(content=khoi, stop_reason=self.dung, model=G.MODEL,
                  usage=NS(input_tokens=1000, output_tokens=200, cache_creation_input_tokens=2000, cache_read_input_tokens=0))


class GiaSu(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.out = Path(self.d.name) / 'out'
        self.goc = Path(self.d.name)
        G.PHIEN.clear()
        self.p = mock.patch.object(G, 'co_khoa', return_value=True)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        G.PHIEN.clear()
        self.d.cleanup()

    def hoi(self, c, phien, cd, cau, cfg=None, lang='vi'):
        return G.hoi(cfg or {}, self.out, phien, cd, cau, client=c, now=NOW, lang=lang, goc=self.goc)

    def test_buoi_hoc_gui_lai_nguyen_khoi_va_bo_dem(self):
        c = ClaudeGia()
        kq = self.hoi(c, None, 'rui_ro', '')
        self.assertTrue(kq['ok'])
        k = c.goi[0]
        self.assertEqual((k['model'], k['output_config'], k['fallbacks']), ('claude-opus-5-5', {'effort': 'medium'}, 'default'))
        self.assertIn('server-side-fallback-2026-07-01', k['betas'])
        self.assertNotIn('cache_control', k['system'][0])
        self.assertEqual(k['system'][-1]['cache_control'], {'type': 'ephemeral'})
        self.assertIn('maieutic', k['system'][0]['text'].lower())                  # kỹ năng của Jane Street nằm trong lời nhắc
        self.assertIn('ĐÚNG MỘT câu hỏi', k['system'][0]['text'])
        self.assertIn('Ngôn ngữ: tiếng Việt', k['system'][1]['text'])
        self.assertEqual(k['messages'][0]['content'][0]['text'], 'Hãy dạy tôi chủ đề "Quản lý rủi ro và tính khối lượng lệnh" tới mức thành thạo.')
        kq2 = self.hoi(c, kq['phien'], 'rui_ro', 'Là số tiền mất nếu chạm dừng lỗ')
        self.assertEqual(kq2['phien'], kq['phien'])
        m = c.goi[1]['messages']
        self.assertEqual([x['role'] for x in m], ['user', 'assistant', 'user'])
        self.assertEqual(m[0]['content'], 'Hãy dạy tôi chủ đề "Quản lý rủi ro và tính khối lượng lệnh" tới mức thành thạo.')   # lượt cũ không còn dấu bộ đệm
        self.assertEqual(m[1]['content'][0], {'type': 'thinking', 'thinking': '', 'signature': 'sig1'})   # khối suy nghĩ gửi lại nguyên vẹn
        self.assertNotIn('citations', m[1]['content'][1])
        self.assertEqual(m[2]['content'][0]['cache_control'], {'type': 'ephemeral'})   # chỉ lượt mới nhất mang dấu bộ đệm
        so = [json.loads(x) for x in (self.out / 'gia-su.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual(len(so), 2)
        self.assertAlmostEqual(so[0]['usd'], (1000 * 4 + 200 * 20 + 2000 * 5) / 1e6)
        self.assertNotIn('Là số tiền mất', json.dumps(so, ensure_ascii=False))     # sổ chi phí không ghi nội dung

    def test_hoc_tiep_sau_khi_tat_webapp(self):
        c = ClaudeGia(chu='Xong phần kiểm tra.\n' + BAN_DO + '\nBạn muốn bắt đầu từ đâu?')
        kq = self.hoi(c, None, 'scalp', '')
        self.hoi(c, kq['phien'], 'scalp', 'Từ rủi ro')
        G.PHIEN.clear()                                                              # như khi tắt rồi mở lại webapp
        b = G.doc_buoi(kq['phien'], self.goc)
        self.assertEqual(b['chu_de'], 'scalp')
        self.assertEqual([x['ai'] for x in b['hien']], [True, False, True])           # lời mở đầu tự động không hiện
        self.assertEqual(b['hien'][1]['chu_gs'], 'Từ rủi ro')
        kq3 = self.hoi(c, kq['phien'], 'scalp', 'Tiếp')
        self.assertEqual(kq3['phien'], kq['phien'])
        self.assertEqual(len(c.goi[2]['messages']), 5)                               # hội thoại đọc lại từ đĩa
        ds = G.buoi_gan_day(self.goc)
        self.assertEqual((ds[0]['phien'], ds[0]['luot']), (kq['phien'], 3))
        self.assertIn('██', ds[0]['ban_do'])
        self.assertIsNone(G.doc_buoi('../../x', self.goc))                           # mã buổi lạ không đọc ra ngoài thư mục

    def test_luong_chu_hien_dan(self):
        c = ClaudeGia(chu='Câu hỏi: rủi ro mỗi lệnh là gì?')

        class Luong:
            def __init__(self, **k):
                self.r = c.create(**k)
                self.text_stream = iter(['Câu hỏi: ', 'rủi ro mỗi lệnh ', 'là gì?'])

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def get_final_message(self):
                return self.r
        c.beta.messages.stream = Luong
        nhan = []
        kq = G.hoi({}, self.out, None, 'rui_ro', '', client=c, now=NOW, goc=self.goc, khi_chu=nhan.append)
        self.assertTrue(kq['ok'])
        self.assertEqual(''.join(nhan), kq['tra_loi'])
        self.assertEqual(len(nhan), 3)
        self.assertEqual(G.doc_buoi(kq['phien'], self.goc)['luot'], 1)                # buổi học vẫn được lưu như lượt thường

    def test_tieng_anh_theo_trang(self):
        c = ClaudeGia()
        self.hoi(c, None, 'ky_vong', '', lang='en')
        self.assertIn('Ngôn ngữ: English', c.goi[0]['system'][1]['text'])
        self.assertTrue(c.goi[0]['messages'][0]['content'][0]['text'].startswith('Teach me'))

    def test_gioi_han_luot_ngan_sach_va_dau_vao(self):
        c = ClaudeGia()
        cfg = {'gia_su': {'luot_moi_ngay': 1}}
        self.assertTrue(self.hoi(c, None, 'scalp', '', cfg)['ok'])
        kq = self.hoi(c, None, 'scalp', '', cfg)
        self.assertFalse(kq['ok'])
        self.assertIn('đủ 1 lượt', kq['ly_do'])
        self.assertFalse(self.hoi(c, None, 'scalp', '', {'gia_su': {'ngan_sach_usd': 0.01}})['ok'])
        self.assertFalse(self.hoi(c, None, 'khong_co', '')['ok'])
        self.assertFalse(self.hoi(c, None, 'scalp', 'x' * 1501)['ok'])
        self.assertFalse(self.hoi(c, None, 'scalp', '', {'gia_su': {'bat': False}})['ok'])
        self.assertEqual(len(c.goi), 1)

    def test_tu_choi_va_loi_mang(self):
        kq = self.hoi(ClaudeGia(dung='refusal'), None, 'ky_vong', '')
        self.assertFalse(kq['ok'])
        self.assertEqual(G.PHIEN[kq['phien']]['msgs'], [])                         # lượt bị từ chối không vào hội thoại
        LoiMang = type('APIConnectionError', (Exception,), {})
        kq = self.hoi(ClaudeGia(loi=LoiMang('x')), None, 'ky_vong', '')
        self.assertEqual(kq['ly_do'], 'Không nối được tới Anthropic (mạng); thử lại sau.')

    def test_ky_nang_va_giay_phep(self):
        self.assertTrue((G.THU_MUC / 'SKILL.md').read_text(encoding='utf-8').startswith('---\nname: "socratic-tutor"'))
        self.assertIn('Jane Street Group, LLC', (G.THU_MUC / 'LICENSE.md').read_text(encoding='utf-8'))
        self.assertEqual(len(G.chu_de()), 20)
        for cd in G.chu_de():
            self.assertTrue(G.noi_dung(cd['id']), cd['id'])


if __name__ == '__main__':
    unittest.main()
