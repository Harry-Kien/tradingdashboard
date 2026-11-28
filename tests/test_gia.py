"""Bài kiểm cho lớp giá và trang biểu đồ. Kho nến 1 phút được dựng giả trong thư mục tạm."""
import json
from functools import partial
from http_owner import owner_cookie, owner_urlopen
import math
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import bieu_do, gia, web  # noqa: E402

MA_THAT = [r'D:\Tele dự báo', r'D:\EA Promax']


def _kho(d: Path, start: datetime, minutes: int) -> None:
    """Nến 1 phút đi theo hình sin quanh 3.800, liên tục, bắt đầu đúng đầu giờ."""
    rows, by_month = [], {}
    for i in range(minutes):
        t = start + timedelta(minutes=i)
        mid = 3800 + 40 * math.sin(i / 300) + 15 * math.sin(i / 37)
        o, c = mid, 3800 + 40 * math.sin((i + 1) / 300) + 15 * math.sin((i + 1) / 37)
        rows.append((t, o, max(o, c) + 0.4, min(o, c) - 0.4, c))
    for t, o, h, l, c in rows:
        by_month.setdefault(f'{t:%Y-%m}', []).append(f'{t.isoformat()},{o:.2f},{h:.2f},{l:.2f},{c:.2f}')
    for m, lines in by_month.items():
        (d / f'XAUUSDp_M1_{m}.csv').write_text('time,open,high,low,close\n' + '\n'.join(lines) + '\n', encoding='utf-8')


class GiaTest(unittest.TestCase):
    def setUp(self):
        gia._nho.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.start = datetime(2026, 11, 16, 0, 0, tzinfo=timezone.utc)          # thứ Hai
        _kho(self.d, self.start, 4 * 1440 + 7)                                     # 4 ngày và 7 phút lẻ
        self.cfg = {'ten': 'Thử', 'gia': {'kho_m1': str(self.d), 'ma_nguon': [], 'so_thang': 4}}
        self.now = self.start + timedelta(days=4, minutes=30)

    def tearDown(self):
        gia._nho.clear()
        self.tmp.cleanup()

    def test_chi_giu_nen_da_dong(self):
        fr = gia.khung(self.cfg['gia'])
        self.assertEqual(fr['het'], self.start + timedelta(days=4, minutes=7))
        # 7 phút lẻ: nến M5 00:00 đã đóng, nến M5 00:05 và nến M15 00:00 chưa đóng nên bị bỏ
        self.assertEqual(fr['M5'].index[-1].to_pydatetime(), self.start + timedelta(days=4))
        self.assertEqual(fr['M15'].index[-1].to_pydatetime(), self.start + timedelta(days=3, hours=23, minutes=45))
        self.assertEqual(fr['H4'].index[-1].to_pydatetime(), self.start + timedelta(days=3, hours=20))
        self.assertEqual(len(fr['D1']), 4)
        first = fr['M15'].iloc[0]
        self.assertAlmostEqual(first['open'], 3800.0, places=1)
        self.assertGreaterEqual(first['high'], max(first['open'], first['close']))

    def test_goi_tra_nen_va_chi_bao(self):
        d = gia.goi(self.cfg, 'M15', 100, self.now)
        self.assertEqual((d['tf'], len(d['candles']), len(d['ema20']), len(d['bb_tren'])), ('M15', 100, 100, 100))
        t, o, h, l, c = d['candles'][-1]
        self.assertEqual(t, int((self.start + timedelta(days=3, hours=23, minutes=45)).timestamp()))
        self.assertTrue(l <= min(o, c) <= max(o, c) <= h)
        self.assertIsNotNone(d['ema50'][-1])
        self.assertGreater(d['bb_tren'][-1], d['bb_duoi'][-1])
        self.assertEqual(d['luat']['tuoi_phut'], 23)
        json.dumps(d)                                                              # phải ghi được thành JSON

    def test_khong_nap_duoc_ma_thi_bieu_do_van_len(self):
        self.cfg['gia']['ma_nguon'] = [str(self.d / 'khong-co')]
        saved = {k: sys.modules.pop(k) for k in list(sys.modules) if k == 'tinhieu' or k.startswith('tinhieu.') or k == 'ai' or k.startswith('ai.')}
        path = list(sys.path)
        sys.path[:] = [p for p in sys.path if p not in MA_THAT]
        try:
            d = gia.goi(self.cfg, 'H1', 60, self.now)
        finally:
            sys.path[:] = path
            sys.modules.update(saved)
        self.assertEqual(len(d['candles']), 60)
        self.assertTrue(any('Không nạp được mã chỉ báo' in e for e in d['luat']['loi']))

    def test_khung_la_va_gioi_han_so_nen(self):
        with self.assertRaises(ValueError):
            gia.goi(self.cfg, 'M2', 100, self.now)
        self.assertEqual(len(gia.goi(self.cfg, 'M5', 5, self.now)['candles']), 50)        # tối thiểu 50
        self.assertEqual(len(gia.goi(self.cfg, 'M5', 99999, self.now)['candles']), 1153)   # hết dữ liệu: 4 ngày × 288, thêm nến 00:00 đã đóng

    @unittest.skipUnless(all(os.path.isdir(p) for p in MA_THAT), 'không có mã của dự án trên máy này')
    def test_goi_ham_that_cua_du_an(self):
        _kho(self.d, self.start - timedelta(days=40), 40 * 1440)                         # đủ nến cho EMA50 H4
        gia._nho.clear()
        self.cfg['gia']['ma_nguon'] = MA_THAT
        d = gia.goi(self.cfg, 'M15', 300, self.now)
        L = d['luat']
        self.assertIn('ba_khung', L, L['loi'])
        self.assertEqual(set(L['ba_khung']['huong']), {'D1', 'H4', 'H1'})
        self.assertIn(L['ba_khung']['quyet_dinh'], ('MUA', 'BAN', None))
        self.assertIn('ho_tro', d)
        self.assertIsInstance(L['bot_tin_hieu'], list)
        self.assertIn(L['dinh_day']['hanh_dong'], ('MUA', 'BAN', 'DUNG_NGOAI'))
        for z in d['vung']:
            self.assertIn(z['loai'], ('fvg', 'ob'))
            self.assertLessEqual(z['duoi'], z['tren'])

    def test_rsi_va_lenh_dang_mo(self):
        import pandas as pd
        tang = gia.rsi_wilder(pd.Series([float(i) for i in range(60)]))
        self.assertTrue(tang.iloc[:13].isna().all())
        self.assertAlmostEqual(tang.iloc[-1], 100.0)
        dao = gia.rsi_wilder(pd.Series([100 + (1 if i % 2 else -1) for i in range(200)], dtype=float))
        self.assertTrue(40 < dao.iloc[-1] < 60)
        d = gia.goi(self.cfg, 'M15', 100, self.now)
        self.assertEqual(len(d['rsi']), 100)
        self.assertTrue(all(v is None or 0 <= v <= 100 for v in d['rsi']))
        self.assertEqual(d['lenh'], [])                                            # không khai sổ bot hay EA thì không có lệnh
        ea = self.d / 'EA_X_events.csv'
        ea.write_text('time_server,event,equity,detail\n2026.11.19 10:00:00,sell,100.00,lots=0.02 price=3700.00 sl=3775.00 tp=3600.00\n', encoding='utf-8')
        gia._lenh_nho.update(luc=0.0, key=None)
        ds = gia.lenh_dang_mo({'tai_khoan': [{'ten': 'Demo', 'ea': [{'ten': 'EA X', 'tep': str(ea)}]}]})
        o = {k: v for k, v in ds[0].items() if k in ('nhan', 'ten', 'lot', 'huong', 'vao', 'sl', 'tp', 'loai')}
        self.assertEqual((len(ds), o), (1, {'nhan': 'EA X BÁN 0.02', 'ten': 'EA X', 'lot': 0.02, 'huong': 'SELL', 'vao': 3700.0, 'sl': 3775.0, 'tp': [3600.0], 'loai': 'demo'}))
        self.assertEqual((ds[0]['nguon'], ds[0]['xac_minh']), ('nhat_ky_ea', False))    # không nối MT5: chỉ là "theo nhật ký, chưa xác minh" (vi_the.py)

    def test_trang_kien_thuc(self):
        from so_cong_khai import kien_thuc
        html = kien_thuc.trang_kien_thuc('Thử')
        for must in ('Kiến thức', 'Luật xu hướng ba khung', 'Tỷ lệ thắng hòa vốn', 'Trong hệ thống của bạn', 'href="/bieu-do"',
                     'aria-current="page">Kiến thức', 'không phải lời khuyên đầu tư'):
            self.assertIn(must, html)
        self.assertGreaterEqual(sum(len(m) for _, m in kien_thuc.MUC), 20)

    def test_trang_bieu_do(self):
        html = bieu_do.trang_bieu_do('Thử')
        for must in ('<canvas id="cv"', 'data-tf="M15" aria-pressed="true"', 'data-k="fvg"', 'Khối lệnh', '/api/gia?tf=', 'không đặt lệnh',
                     'id="theme"', 'href="/"', 'id="rk"', 'Tính khối lượng lệnh', 'đang chạy', 'data-kieu="mt5"', 'data-k="rsi"',
                     'data-k="lenh"', 'href="/kien-thuc"', 'aria-current="page">Biểu đồ', 'Tahoma'):
            self.assertIn(must, html)

    def test_bam_phan_tich_khi_the_dang_chon_khong_co_diem_vao(self):
        # Thẻ phương pháp được nhớ giữa các lần mở trang. Người dùng bấm "Phân tích điểm vào" khi thẻ đang nhớ (ví dụ ICT/SMC) chưa có điểm vào
        # thì chỉ thấy "Chưa có điểm vào", dù phương pháp khác đang có. Bấm nút phải đưa về thẻ có điểm vào, và thẻ trống phải chỉ sang thẻ có.
        html = bieu_do.trang_bieu_do('Thử')
        for must in ("!['harry_smc','harry_xu_huong'].includes(ppChon)",  # giữ hai thẻ có vùng theo dõi khi đang chờ
                     "!ppNhom(ppChon).some(p=>p.co)&&ppNhom('tat').some(p=>p.co)){ppChon='tat'",
                     'Phương pháp khác đang có điểm vào', 'class="ictb ppj"', "el.querySelectorAll('.ppx,.ppj')",
                     'Webapp không trả lời'):
            self.assertIn(must, html)

    def test_ky_luat_dat_khong_duoc_doc_la_bang_chung(self):
        # Đo ngày 23/11/2026: chỉ 11% bối cảnh đủ mẫu "có lãi cả hai nửa", ít hơn mức 25% mà may rủi tạo ra; SPA trên cả tập p = 0,08.
        html = bieu_do.trang_bieu_do('Thử')
        for must in ('<b>Kỷ luật: đạt.</b>', 'chưa phải bằng chứng có lợi thế', 'khoảng một phần tư'):
            self.assertIn(must, html)

    def test_o_rieng_cho_lenh_cua_bot_tin_hieu(self):
        html = bieu_do.trang_bieu_do('Thử')
        for must in ('data-k="bot"', 'Lệnh của bot tín hiệu', 'lenh:1,bot:1,rsi:0', 'lenh:1,bot:1,rsi:1',            # ô mới, mặc định bật ở cả hai bộ
                     "o.loai==='tin_hieu'?on.bot:on.lenh"):                                                       # lệnh EA demo theo ô cũ, lệnh bot theo ô mới
            self.assertIn(must, html)
        for cu in ('for(const o of D.lenh||[]){', 'for(const l of D.lenh||[]){'):                               # không còn chỗ vẽ nào bỏ qua ô mới
            self.assertNotIn(cu, html)

    def test_qua_may_chu(self):
        cfgp = self.d / 'c.json'
        cfgp.write_text(json.dumps({**self.cfg, 'thu_muc_ra': str(self.d / 'out')}), encoding='utf-8')
        srv = web.tao_may_chu(str(cfgp), port=0)
        owner_cookie(cfgp.parent)
        open_owner = partial(owner_urlopen, root=cfgp.parent)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{srv.server_address[1]}'
        try:
            with open_owner(base + '/bieu-do', timeout=10) as r:
                self.assertIn('Biểu đồ vàng', r.read().decode('utf-8'))
            with open_owner(base + '/kien-thuc', timeout=10) as r:
                self.assertIn('Nghĩa là gì', r.read().decode('utf-8'))
            with open_owner(base + '/api/gia?tf=H1&n=80', timeout=20) as r:
                self.assertEqual(len(json.loads(r.read())['candles']), 80)
            with self.assertRaises(urllib.error.HTTPError) as e:
                open_owner(base + '/api/gia?tf=XYZ', timeout=10)
            self.assertEqual(e.exception.code, 400)
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == '__main__':
    unittest.main()
