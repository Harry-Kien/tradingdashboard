"""Bài kiểm cho giá trực tiếp và phần hỏi AI. Không nối MT5 thật, không gọi API thật: cả hai được thay bằng đồ giả."""
import json
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from so_cong_khai import ai_hoi, gia, song  # noqa: E402
from test_gia import MA_THAT, _kho  # noqa: E402


class _Deps:
    def __init__(self, fr, tick):
        self.fr, self.tick, self.calls = fr, tick, 0

    def get_tick(self):
        return self.tick

    def get_bars(self, tf, n):
        self.calls += 1
        return None if self.fr is None else self.fr[tf].iloc[-n:].reset_index(names='time')


class SongTest(unittest.TestCase):
    def setUp(self):
        gia._nho.clear()
        song._tt.update(deps=None, mt5=None, fr=None, thu=0.0, luc=0.0, ly_do='chưa thử nối')
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.start = datetime(2026, 9, 7, 0, 0, tzinfo=timezone.utc)
        _kho(self.d, self.start, 75 * 1440)
        self.g = {'kho_m1': str(self.d), 'ma_nguon': MA_THAT, 'so_thang': 4, 'mt5': {'bat': True, 'terminal': 'X:\\gia\\terminal64.exe'}}
        self.kho = gia.khung(self.g)
        self.now = self.kho['het'] + timedelta(seconds=20)
        self.tick = (3811.2, 3811.37, self.kho['het'] + timedelta(seconds=5))

    def tearDown(self):
        song._tt.update(deps=None, mt5=None, fr=None, thu=0.0, luc=0.0)
        gia._nho.clear()
        self.tmp.cleanup()

    def test_tat_trong_cau_hinh_thi_khong_noi(self):
        called = []
        self.assertIsNone(song.khung_song({'mt5': {'bat': False}}, noi=lambda *a: called.append(1)))
        self.assertEqual(called, [])
        self.assertIn('đang tắt', song.ly_do())

    def test_khong_noi_duoc_thi_tra_ly_do_va_khong_thu_lai_ngay(self):
        n = []

        def noi(cfgm, g):
            n.append(1)
            return None, None, 'MT5 chưa mở'
        self.assertIsNone(song.khung_song(self.g, noi=noi))
        self.assertIsNone(song.khung_song(self.g, noi=noi))
        self.assertEqual((len(n), song.ly_do()), (1, 'MT5 chưa mở'))

    def test_noi_duoc_thi_tra_khung_va_gia(self):
        deps = _Deps(self.kho, self.tick)
        mt5 = types.SimpleNamespace(shutdown=lambda: None)
        fr = song.khung_song(self.g, noi=lambda cfgm, g: (mt5, deps, None))
        self.assertEqual((fr['nguon'], fr['bid'], fr['ask'], fr['het']), ('mt5', 3811.2, 3811.37, self.tick[2]))
        self.assertEqual(list(fr['M15'].columns), ['open', 'high', 'low', 'close'])
        self.assertIsNone(song.ly_do())
        before = deps.calls
        self.assertIs(song.khung_song(self.g, noi=None), fr)                       # trong vài giây: dùng lại, không hỏi MT5 nữa
        self.assertEqual(deps.calls, before)

    def test_nen_dang_chay_chi_de_ve(self):
        t0 = int((self.kho['M15'].index[-1] + timedelta(minutes=15)).timestamp())

        def rates(sym, tf, pos, n):
            self.assertEqual((sym, pos, n), ('XAUUSDp', 0, 1))
            return [{'time': t0 if tf == 'M15' else 1, 'open': 3800.0, 'high': 3803.0, 'low': 3799.0, 'close': 3801.5}]
        mt5 = types.SimpleNamespace(shutdown=lambda: None, copy_rates_from_pos=rates, **{'TIMEFRAME_' + tf: tf for tf in song.SO_NEN})
        song._tt['sym'] = 'XAUUSDp'
        fr = song.khung_song(self.g, noi=lambda cfgm, g: (mt5, _Deps(self.kho, self.tick), None))
        self.assertEqual(fr['dang_chay']['M15'], [t0, 3800.0, 3803.0, 3799.0, 3801.5])
        d = gia.goi({'gia': self.g}, 'M15', 100, self.now)                       # dùng lại khung vừa lấy (còn trong vài giây)
        self.assertEqual((d['nguon'], d['dang_chay'][0], len(d['candles'])), ('mt5', t0, 100))   # nến đang chạy không lẫn vào nến đã đóng
        self.assertNotIn('dang_chay', gia.goi({'gia': self.g}, 'H1', 100, self.now))             # nến cũ hơn nến đã đóng thì bỏ

    def test_tick_doc_thang_nen_dang_chay(self):
        def rates(sym, tf, pos, n):
            self.assertEqual((sym, tf, pos, n), ('XAUUSDp', 'M5', 0, 1))
            return [{'time': 1795537800, 'open': 3800.0, 'high': 3803.0, 'low': 3799.0, 'close': 3801.5}]
        tk = types.SimpleNamespace(time_msc=1795537950285, bid=3801.5, ask=3801.67)
        mt5 = types.SimpleNamespace(shutdown=lambda: None, copy_rates_from_pos=rates, symbol_info_tick=lambda sym: tk,
                                    **{'TIMEFRAME_' + tf: tf for tf in song.SO_NEN})
        song._tt.update(mt5=mt5, deps=object(), sym='XAUUSDp')
        self.assertEqual(song.tick(self.g, 'M5'), {'ms': 1795537950285, 'bid': 3801.5, 'ask': 3801.67,
                                                   'nen': [1795537800, 3800.0, 3803.0, 3799.0, 3801.5]})
        with self.assertRaises(ValueError):
            song.tick(self.g, 'M7')                                          # M1, W1 đã có (26/11/2026); M7 không phải khung của hệ thống

    def test_tick_khi_chua_noi_thi_none(self):
        self.assertIsNone(song.tick({'mt5': {'bat': False}}, 'M15'))

    def test_tick_gui_khoi_luong_du_dinh_dang_numpy_mt5(self):
        import numpy as np
        rates = np.array([(1795537800, 3800., 3803., 3799., 3801.5, 42)],
                         dtype=[('time', 'i8'), ('open', 'f8'), ('high', 'f8'), ('low', 'f8'), ('close', 'f8'), ('tick_volume', 'i8')])
        tk = types.SimpleNamespace(time_msc=1795537950285, bid=3801.5, ask=3801.67)
        mt5 = types.SimpleNamespace(copy_rates_from_pos=lambda *a: rates, symbol_info_tick=lambda s: tk, TIMEFRAME_M5='M5')
        song._tt.update(mt5=mt5, deps=object(), sym='XAUUSDp')
        self.assertEqual(song.tick(self.g, 'M5')['vol'], 42)

    def test_mat_ket_noi_thi_bo_phien(self):
        closed = []
        mt5 = types.SimpleNamespace(shutdown=lambda: closed.append(1))
        self.assertIsNone(song.khung_song(self.g, noi=lambda cfgm, g: (mt5, _Deps(None, None), None)))
        self.assertEqual(closed, [1])
        self.assertIn('mất kết nối', song.ly_do())

    def test_mo_dun_khong_co_loi_goi_dat_lenh(self):
        for name in ('song.py', 'ai_hoi.py', 'gia.py', 'web.py', 'bieu_do.py'):
            src = (Path(song.__file__).parent / name).read_text(encoding='utf-8')
            for banned in ('order_send', 'order_check', 'TRADE_ACTION', 'positions_get', 'orders_get', 'history_deals'):
                self.assertNotIn(banned, src, f'{name} chứa {banned}')

    # ---- hỏi AI
    def _song(self, tuoi_giay=5):
        fr = dict(self.kho, nguon='mt5', bid=self.tick[0], ask=self.tick[1], het=self.now - timedelta(seconds=tuoi_giay))
        return lambda g: fr

    def _cfg(self, **ai):
        return {'gia': self.g, 'ai': {'bat': True, 'moi_ngay': 2, 'ngan_sach_usd': 1.0, **ai}}

    @unittest.skipUnless(all(os.path.isdir(p) for p in MA_THAT), 'không có mã của dự án trên máy này')
    def test_hoi_ai_ghi_so_va_kiem_tra(self):
        for p in MA_THAT:
            if p not in sys.path:
                sys.path.insert(0, p)
        from ai import schema
        seen = []

        def analyze(text):
            seen.append(text)
            sig = schema.Signal(hanh_dong='DUNG_NGOAI', kieu_vao='khong_co', loai_lenh='thi_truong', gia_vao=None, sl=None, tp1=None, tp2=None,
                                tp3=None, gia_huy=None, hieu_luc_phut=30, do_tin_cay=40, ly_do='Giá đi ngang giữa hai vùng.', dieu_kien_huy='Không có.')
            return types.SimpleNamespace(kind='signal', signal=sig, raw_text='', model_served='gia-lap', tokens={}, cost_usd=0.08, error=None)
        out = self.d / 'out'
        song._tt['deps'] = object()                                                  # coi như đang có giá trực tiếp
        r = ai_hoi.hoi(self._cfg(), out, analyze=analyze, now=self.now, khung_song=self._song())
        self.assertTrue(r['ok'], r)
        self.assertEqual(len(seen), 1)
        self.assertIn('XAU', seen[0].upper())
        rec = ai_hoi.doc_so(out)[0]
        self.assertEqual((rec['tin_hieu']['hanh_dong'], rec['kiem_tra']['trang_thai'], rec['chi_phi_usd']), ('DUNG_NGOAI', 'dung_ngoai', 0.08))
        st = ai_hoi.trang_thai(self._cfg(), out, self.now)
        self.assertEqual((st['hom_nay'], st['da_tieu_usd']), (1, 0.08))
        ai_hoi.hoi(self._cfg(), out, analyze=analyze, now=self.now, khung_song=self._song())
        r3 = ai_hoi.hoi(self._cfg(), out, analyze=analyze, now=self.now, khung_song=self._song())      # lượt thứ ba: quá 2 lượt/ngày
        self.assertFalse(r3['ok'])
        self.assertTrue(any('đủ 2 lượt' in c for c in r3['chan']))
        self.assertEqual(len(seen), 2)

    def test_ba_chot_chan(self):
        out = self.d / 'out'
        analyze = lambda text: self.fail('không được gọi AI')                         # noqa: E731
        song._tt['deps'] = object()
        r = ai_hoi.hoi(self._cfg(), out, analyze=analyze, now=self.now, khung_song=self._song(tuoi_giay=600))
        self.assertTrue(any('cũ hơn 2 phút' in c for c in r['chan']))
        r = ai_hoi.hoi(self._cfg(), out, analyze=analyze, now=self.now, khung_song=lambda g: None)
        self.assertFalse(r['ok'])
        out.mkdir(exist_ok=True)
        (out / 'ai-hoi.jsonl').write_text(json.dumps({'luc': (self.now - timedelta(days=3)).isoformat(), 'chi_phi_usd': 0.97}) + '\n', encoding='utf-8')
        r = ai_hoi.hoi(self._cfg(), out, analyze=analyze, now=self.now, khung_song=self._song())
        self.assertTrue(any('ngân sách' in c for c in r['chan']))
        r = ai_hoi.hoi(self._cfg(bat=False), out, analyze=analyze, now=self.now, khung_song=self._song())
        self.assertTrue(any('đang tắt' in c for c in r['chan']))

    def test_thieu_khoa_thi_khong_goi_api_that(self):
        os.environ.pop('ANTHROPIC_API_KEY', None)
        if (Path.home() / '.config' / 'anthropic').exists():
            self.skipTest('máy này có khóa trong ~/.config/anthropic')
        song._tt['deps'] = object()
        r = ai_hoi.hoi(self._cfg(), self.d / 'out', analyze=None, now=self.now, khung_song=self._song())
        self.assertFalse(r['ok'])
        self.assertTrue(any('khóa API' in c for c in r['chan']))


if __name__ == '__main__':
    unittest.main()
