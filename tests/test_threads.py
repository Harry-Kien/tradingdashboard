"""Bài kiểm cho phần tạo bài Threads. Hàng chờ của Thread Auto được dựng giả trong thư mục tạm."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from so_cong_khai import doc_so, threads, tong_hop  # noqa: E402
from test_so import _bot_db  # noqa: E402


class ThreadsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        _bot_db(self.d / 'bot.db')
        self.ta = self.d / 'ThreadAuto'
        (self.ta / 'data' / 'out').mkdir(parents=True)
        self.queue = self.ta / 'data' / 'editorial-queue.json'
        self.queue.write_text(json.dumps([{'id': 'cu', 'channel': 'harry', 'approved': True}]), encoding='utf-8')
        self.cfg = {'ten': 'Thử', 'bot_db': str(self.d / 'bot.db'),
                    'threads': {'thu_muc': str(self.ta), 'kenh': 'harry', 'tai_khoan': 'tk_thu', 'ngon_ngu': 'en'}}
        self.w = tong_hop.tuan_theo_ma('2026-W47')
        self.now = datetime(2026, 11, 21, 1, 0, tzinfo=timezone.utc)
        self.out = self.d / 'out' / 'threads'

    def tearDown(self):
        self.tmp.cleanup()

    def _nhap(self, loai='tuan', **kw):
        return threads.tao_ban_nhap({**self.cfg, **kw}, loai, *self.w, self.out, self.now)

    def test_bai_tuan_tieng_anh(self):
        r = self._nhap()
        t = r['text']
        self.assertLessEqual(len(t), 500)
        for must in ('week 47 (16 Nov–22 Nov)', 'not trades', 'Calls: 4 · closed 3 · open 1', 'Reached TP1: 2 of 3 decided',
                     'Stopped before any TP: 1 of 3', 'All 4 calls were SELL', 'Under 30 closed calls', 'Not financial advice', '#XAUUSD'):
            self.assertIn(must, t)
        self.assertNotIn('#1', t.replace('#XAUUSD', '').replace('#Forex', ''))      # không tạo thẻ chủ đề từ số lệnh

    def test_bai_ngay_co_danh_sach_va_khong_qua_dai(self):
        day = datetime(2026, 11, 18, tzinfo=doc_so.VN)
        b = tong_hop.tom_bot(doc_so.doc_bot(str(self.d / 'bot.db')), day, day.replace(day=19))
        t = threads.chu_bai('ngay', b, day, 'vi')
        self.assertIn('sổ ngày 18/11', t)
        self.assertIn('3 · BÁN 3860 · TP1 rồi chạm SL', t)
        self.assertIn('không phải lệnh thật', t)
        rows = [dict(b['rows'][0], call=100 + i) for i in range(40)]
        dai = threads.chu_bai('ngay', {**b, 'rows': rows, 'n': 40}, day, 'en')
        self.assertLessEqual(len(dai), 500)
        self.assertIn('more in the log', dai)
        self.assertIn('Not financial advice', dai)

    def test_khong_co_lenh(self):
        day = datetime(2026, 12, 1, tzinfo=doc_so.VN)
        b = tong_hop.tom_bot([], day, day.replace(day=2))
        self.assertIn('No calls in this period.', threads.chu_bai('ngay', b, day, 'en'))

    def test_ban_nhap_luon_chua_duyet_va_co_anh(self):
        r = self._nhap()
        d = r['draft']
        self.assertIs(d['approved'], False)
        self.assertEqual((d['channel'], d['account'], d['id']), ('harry', 'tk_thu', 'harry-botlog-tuan-2026w47'))
        self.assertEqual((d['notBefore'], d['expiresAt']), ('2026-11-21T01:00:00.000Z', '2026-11-22T01:00:00.000Z'))
        from PIL import Image
        with Image.open(self.out / 'harry-botlog-tuan-2026w47.image.png') as anh:
            self.assertEqual(anh.size, (1080, 1350))

    def test_dua_vao_hang_cho(self):
        r = self._nhap()
        threads.dua_vao_hang_cho(r['draft'], self.out, self.ta)
        q = json.loads(self.queue.read_text(encoding='utf-8'))
        self.assertEqual([d['id'] for d in q], ['cu', 'harry-botlog-tuan-2026w47'])
        self.assertIs(q[-1]['approved'], False)
        self.assertTrue((self.ta / 'data' / 'out' / 'harry-botlog-tuan-2026w47.caption.txt').exists())
        self.assertTrue((self.ta / 'data' / 'out' / 'harry-botlog-tuan-2026w47.image.png').exists())
        self.assertTrue((self.out / 'editorial-queue.truoc-harry-botlog-tuan-2026w47.json').exists())
        with self.assertRaises(ValueError):                    # không thêm trùng
            threads.dua_vao_hang_cho(r['draft'], self.out, self.ta)

    def test_tu_choi_bai_da_duyet_va_khi_dang_khoa(self):
        r = self._nhap()
        with self.assertRaises(ValueError):
            threads.dua_vao_hang_cho({**r['draft'], 'approved': True}, self.out, self.ta)
        (self.ta / 'data' / 'operation-lock.json').write_text('{}', encoding='utf-8')
        with self.assertRaises(RuntimeError):
            threads.dua_vao_hang_cho(r['draft'], self.out, self.ta)
        self.assertEqual(len(json.loads(self.queue.read_text(encoding='utf-8'))), 1)      # hàng chờ không đổi

    def test_mac_dinh_khong_dung_thread_auto(self):
        cfgp = self.d / 'c.json'
        cfgp.write_text(json.dumps({**self.cfg, 'thu_muc_ra': str(self.d / 'out')}), encoding='utf-8')
        self.assertEqual(threads.main(['--cau-hinh', str(cfgp), '--tuan', '2026-W47']), 0)
        self.assertEqual(len(json.loads(self.queue.read_text(encoding='utf-8'))), 1)
        self.assertEqual(list((self.ta / 'data' / 'out').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
