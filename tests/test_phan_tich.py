"""Bài kiểm cho nút Phân tích: gọi đúng hàm luật của dự án và trả mức giá nhất quán. Kho nến dựng giả, không nối MT5."""
from functools import partial
from http_owner import owner_urlopen
import json
import os
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from so_cong_khai import bieu_do, gia, phan_tich, song, web  # noqa: E402
from test_gia import MA_THAT, _kho  # noqa: E402



def setUpModule():                                  # không để lịch mạng thật trên máy (du-lieu/lich-tin-mang.json) lọt vào bài kiểm tra này
    from so_cong_khai import gia as _g
    _g._LICH_MANG_THAT, _g.LICH_MANG = _g.LICH_MANG, Path(__file__).parent / 'khong-co-lich-mang.json'
    _g._MANG.clear()


def tearDownModule():
    from so_cong_khai import gia as _g
    _g.LICH_MANG = _g._LICH_MANG_THAT
    _g._MANG.clear()


class PhanTichTest(unittest.TestCase):
    def setUp(self):
        gia._nho.clear()
        song._tt.update(deps=None, mt5=None, fr=None, thu=0.0, luc=0.0)
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.start = datetime(2026, 9, 7, tzinfo=timezone.utc)
        _kho(self.d, self.start, 75 * 1440)
        self.cfg = {'ten': 'Thử', 'thu_muc_ra': str(self.d / 'out'), 'gia': {'kho_m1': str(self.d), 'ma_nguon': MA_THAT, 'so_thang': 4}}
        self.het = self.start + timedelta(days=75)

    def tearDown(self):
        gia._nho.clear()
        self.tmp.cleanup()

    @unittest.skipUnless(all(os.path.isdir(p) for p in MA_THAT), 'không có mã của dự án trên máy này')
    def test_thu_vung_sl_tiep_va_chan_gia_cu_duoi_mot_phut(self):
        fr = gia.khung(self.cfg['gia'])
        R, *_ = gia._nap_ma(self.cfg['gia'])
        bid = float(fr['M5']['close'].iloc[-1])
        bar = fr['M5'].index[-1]
        bad = R.Setup('M5', 'BUY', bar, 2., 1., 1440, 'vùng quá sát', sl_price=bid - 1)
        good = R.Setup('M5', 'BUY', bar, 2., 20., 1440, 'vùng hợp lệ', sl_price=bid - 20)
        live = dict(fr, nguon='mt5', bid=bid, ask=bid + 0.17, het=self.het)
        now = self.het + timedelta(seconds=30)
        with mock.patch.object(R, 'candidates', return_value=[bad, good]), mock.patch.object(song, 'khung_song', return_value=live):
            r = phan_tich.phan_tich(self.cfg, now)
        p = r['phuong_an'][0]
        self.assertTrue(p['co'])
        self.assertEqual(p['nen'], bar.isoformat())
        self.assertIn('vùng hợp lệ', p['ly_do'])
        self.assertTrue(p['chat_luong_call']['gia_dat'])
        old = dict(live, het=now - timedelta(seconds=61))
        with mock.patch.object(R, 'candidates', return_value=[good]), mock.patch.object(song, 'khung_song', return_value=old):
            r = phan_tich.phan_tich(self.cfg, now)
        p = r['phuong_an'][0]
        self.assertEqual(r['tuoi_phut'], 1)
        self.assertFalse(p['hieu_luc'])
        self.assertFalse(p['chat_luong_call']['gia_dat'])
        self.assertTrue(any('60 giây' in x for x in p['vi_sao_het']))
        if p.get('phieu'):
            self.assertNotEqual(p['phieu']['trang_thai'], 'con_hieu_luc')

    @unittest.skipUnless(all(os.path.isdir(p) for p in MA_THAT), 'không có mã của dự án trên máy này')
    def test_bon_phuong_an_va_muc_gia_nhat_quan(self):
        r = phan_tich.phan_tich(self.cfg, self.het + timedelta(minutes=3))
        self.assertEqual(r['loi'], [])
        self.assertEqual([p['ma'] for p in r['phuong_an']], ['bot:nen', 'bot:xu_huong', 'ba_khung', 'dinh_day'])
        bn = r['phuong_an'][0]
        if bn['co']:                                                   # có tín hiệu nến: phương án mang phiếu theo công thức đã đo
            self.assertIn(bn['phieu']['loai'], ('tt', 'gh', 'dung'))                 # theo công thức của lần đo gần nhất
            self.assertEqual((bn['phieu']['huong'], bn['phieu']['i_chinh']), (bn['huong'], 0))
        else:
            self.assertNotIn('phieu', bn)
        self.assertNotIn('phieu', r['phuong_an'][1])                   # lệnh theo yêu cầu chưa được đo kiểu vào này
        bx = r['phuong_an'][1]
        self.assertIn('chưa có kiểm định riêng', bx['thong_ke'])
        self.assertFalse(bx.get('hieu_luc'))
        self.assertFalse(any('67,2' in g for g in bx.get('ghi_chu', [])))
        self.assertEqual(sum(r['dong_thuan'].values()), 4)
        self.assertEqual(set(r['boi_canh']['xu_huong']), {'D1', 'H4', 'H1', 'trend'})
        for p in r['phuong_an']:
            self.assertTrue(p['thong_ke'])
            if not p['co']:
                self.assertTrue(p['vi_sao'])
                continue
            self.assertIn(p['huong'], ('MUA', 'BAN'))
            s = 1 if p['huong'] == 'MUA' else -1
            self.assertGreater((p['vao'] - p['sl']) * s, 0, p)                 # SL nằm đúng phía
            for t, rr in zip(p['tp'], p['rr']):
                self.assertGreater((t - p['vao']) * s, 0, p)                   # TP nằm đúng phía
                self.assertAlmostEqual(rr, abs(t - p['vao']) / p['rui_ro_gia'], places=1)
            self.assertAlmostEqual(p['rui_ro_gia'], abs(p['vao'] - p['sl']), places=2)
        json.dumps(r)

    @unittest.skipUnless(all(os.path.isdir(p) for p in MA_THAT), 'không có mã của dự án trên máy này')
    def test_luat_ba_khung_dung_muc_cua_luat(self):
        for p in MA_THAT:
            if p not in sys.path:
                sys.path.insert(0, p)
        r = phan_tich.phan_tich(self.cfg, self.het + timedelta(minutes=3))
        bk = next(p for p in r['phuong_an'] if p['ma'] == 'ba_khung')
        if bk['co']:
            from ai import rule_trend as RT
            self.assertAlmostEqual(abs(bk['vao'] - bk['sl']), RT.SL_USD, places=1)
            self.assertAlmostEqual(abs(bk['tp'][0] - bk['vao']), RT.TP_USD, places=1)

    def test_gia_cu_thi_canh_bao(self):
        r = phan_tich.phan_tich(self.cfg, self.het + timedelta(hours=5))
        self.assertEqual(r['tuoi_phut'], 300)
        self.assertTrue(any('không dùng để vào lệnh' in c for c in r['canh_bao']))
        moi = phan_tich.phan_tich(self.cfg, self.het + timedelta(minutes=2))
        self.assertFalse(any('Giá đã cũ' in c for c in moi['canh_bao']))

    @unittest.skipUnless(all(os.path.isdir(p) for p in MA_THAT), 'không có mã của dự án trên máy này')
    def test_con_hieu_luc(self):
        cu = phan_tich.phan_tich(self.cfg, self.het + timedelta(hours=5))
        self.assertEqual(cu['con_hieu_luc'], 0)                                # giá cũ 5 giờ: không phương án nào còn hiệu lực
        for p in cu['phuong_an']:
            self.assertFalse(p['hieu_luc'])
            if p['co']:
                self.assertTrue(any('Giá đã cũ 300 phút' in x for x in p['vi_sao_het']), p)
            else:
                self.assertEqual(p['vi_sao_het'], [])
        moi = phan_tich.phan_tich(self.cfg, self.het + timedelta(minutes=1))
        for p in moi['phuong_an']:
            self.assertEqual(p['hieu_luc'], bool(p['co']) and not p['vi_sao_het'], p)
            self.assertFalse(any('Giá đã cũ' in x for x in p['vi_sao_het']))
            self.assertNotIn('_ly', p)
        self.assertEqual(moi['con_hieu_luc'], sum(p['hieu_luc'] for p in moi['phuong_an']))
        tre = phan_tich.phan_tich(self.cfg, self.het + timedelta(minutes=12))  # nến M15 đóng đã 12 phút: luật theo nến không còn hiệu lực
        for p in tre['phuong_an']:
            if p['co'] and p['ma'] in ('ba_khung', 'dinh_day', 'bot:nen'):
                self.assertFalse(p['hieu_luc'], p)

    def test_lich_tin_sap_toi(self):
        f = self.d / 'lich.csv'
        f.write_text('time,currency,importance,event,country\n2026.11.20 13:30,USD,3,Tin da qua,US\n2026.11.24 15:00,USD,3,Core PCE Price Index m/m,US\n'
                     '2026.11.24 15:00,EUR,3,Tin EUR,EU\n2026.11.25 13:30,USD,2,Tin muc vua,US\n2026.11.25 19:00,USD,3,FOMC Minutes,US\nhong,USD,3,x,US\n', encoding='utf-8')
        cfg = {'gia': {'lich_tin': str(f)}}
        now = datetime(2026, 11, 21, 3, 0, tzinfo=timezone.utc)
        r = gia.tin_sap_toi(cfg, now, 5)
        self.assertEqual([x['ten'] for x in r], ['Core PCE Price Index m/m', 'FOMC Minutes'])
        self.assertEqual((r[0]['luc'], r[0]['con']), ('2026-11-24T15:00:00+00:00', 'còn 3 ngày'))
        self.assertEqual(gia.tin_sap_toi({'gia': {}}, now), [])
        self.assertEqual(gia.tin_sap_toi({'gia': {'lich_tin': str(self.d / 'khong-co.csv')}}, now), [])

    def test_khong_nap_duoc_ma_thi_bao_ro(self):
        cfg = {**self.cfg, 'gia': {**self.cfg['gia'], 'ma_nguon': [str(self.d / 'khong-co')]}}
        saved = {k: sys.modules.pop(k) for k in list(sys.modules) if k.split('.')[0] in ('tinhieu', 'ai')}
        path = list(sys.path)
        sys.path[:] = [p for p in sys.path if p not in MA_THAT]
        try:
            r = phan_tich.phan_tich(cfg, self.het)
        finally:
            sys.path[:] = path
            sys.modules.update(saved)
        self.assertEqual(r['phuong_an'], [])
        self.assertTrue(any('Không nạp được mã luật' in e for e in r['loi']))

    def test_trang_co_nut_va_duong_dan(self):
        html = bieu_do.trang_bieu_do('Thử')
        for must in ('id="pt-btn"', 'Phân tích điểm vào', 'id="fs-btn"', 'Toàn màn hình', '/api/phan-tich', 'requestFullscreen', 'không phải lời khuyên đầu tư'):
            self.assertIn(must, html)
        src = Path(phan_tich.__file__).read_text(encoding='utf-8')
        for banned in ('order_send', 'order_check', 'TRADE_ACTION', 'positions_get'):
            self.assertNotIn(banned, src)

    def test_qua_may_chu(self):
        cfgp = self.d / 'c.json'
        cfgp.write_text(json.dumps(self.cfg), encoding='utf-8')
        srv = web.tao_may_chu(str(cfgp), port=0)
        open_owner = partial(owner_urlopen, root=cfgp.parent)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            with open_owner(f'http://127.0.0.1:{srv.server_address[1]}/api/phan-tich', timeout=30) as r:
                j = json.loads(r.read())
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertIn('phuong_an', j)
        self.assertIn('boi_canh', j)


if __name__ == '__main__':
    unittest.main()
