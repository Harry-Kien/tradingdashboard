"""Cùng điều kiện nến trong replay và live; giá, hạn, lịch tin và lưu cảnh báo."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from so_cong_khai import cai_dat, canh_bao, tin_hieu_ngan as T


DONG = pd.Timestamp('2026-11-27 14:00:00', tz='UTC')
NOW = DONG + pd.Timedelta(seconds=10)


def _nen(phut, huong=1):
    index = pd.date_range(end=DONG - pd.Timedelta(minutes=phut), periods=250, freq=f'{phut}min')
    c = 3500 + huong * np.arange(250) / 10
    o = c - .08 * huong
    h = np.maximum(o, c) + .16
    l = np.minimum(o, c) - .16
    c[-1] += .20 * huong
    if huong > 0:
        h[-1] = c[-1] + .04
    else:
        l[-1] = c[-1] - .04
    return pd.DataFrame({'open': o, 'high': h, 'low': l, 'close': c}, index=index)


def _fixture(huong=1):
    fr = {tf: _nen(p, huong) for tf, p in {**T.KHUNG, 'H1': 60}.items()}
    bid = float(fr['M5']['close'].iloc[-1])
    return fr, SimpleNamespace(bid=bid, ask=bid + .02, time_msc=int(NOW.timestamp() * 1000))


class TinHieuNganTest(unittest.TestCase):
    def test_ba_khung_hai_chieu_va_gia_theo_hop_dong(self):
        for huong in (-1, 1):
            fr, tick = _fixture(huong)
            ds = T.quet(fr, NOW, tick, buoc_gia=.01, so_le=2)
            self.assertEqual([x['tf'] for x in ds], ['M5', 'M15', 'M30'])
            self.assertTrue(all(x['trang_thai'] == 'dat' and x['loai'] == 'pha_vo' for x in ds), ds)
            for x in ds:
                self.assertEqual(x['dong'], DONG.isoformat())
                self.assertEqual(x['vao'], round(tick.ask if huong == 1 else tick.bid, 2))
                self.assertGreater(huong * (x['vao'] - x['sl']), 0)
                self.assertGreaterEqual(x['rr'], 1.5)

    def test_ema_hoi_quay_len_co_tin_hieu_rieng(self):
        fr, _ = _fixture()
        b = fr['M5'].copy()
        ema = T._ema(b['close'], 20).iloc[-2]
        b.iloc[-1] = [ema - .11, ema + .39, ema - .18, ema + .34]
        b.iloc[-2] = [ema - .01, ema + .17, ema - .30, ema + .11]
        r = T.dieu_kien(b, fr['H1'], 'M5').iloc[-1]
        self.assertEqual((r.phia, r.loai), (1, 'hoi_ema'))

    def test_nen_dang_chay_va_h1_tuong_lai_khong_anh_huong(self):
        fr, tick = _fixture()
        a = T.quet(fr, NOW, tick, buoc_gia=.01, so_le=2)
        h1 = fr['H1']
        b = {k: pd.concat([df, pd.DataFrame([[3600., 3601., 5., 5.]], columns=df.columns, index=[DONG])]) for k, df in fr.items()}
        self.assertEqual(T.quet(b, NOW, tick, buoc_gia=.01, so_le=2), a)
        for tf in T.KHUNG:
            r1 = T.dieu_kien(fr[tf], h1, tf).iloc[-1]
            r2 = T.dieu_kien(fr[tf].iloc[-T.MAU:], b['H1'].iloc[-T.MAU:], tf).iloc[-1]
            pd.testing.assert_series_equal(r1, r2)

    def test_loai_gia_cu_spread_lon_tin_manh_gia_di_xa_va_het_han(self):
        fr, tick = _fixture()
        for want, t, kwargs, now in (
            ('gia_cu', None, {}, NOW),
            ('gia_cu', SimpleNamespace(**{**vars(tick), 'time_msc': int(DONG.timestamp() * 1000) - 1}), {}, NOW),
            ('gia_cu', SimpleNamespace(**{**vars(tick), 'time_msc': tick.time_msc - 60_000}), {}, NOW),
            ('spread', SimpleNamespace(**{**vars(tick), 'ask': tick.bid + 2}), {}, NOW),
            ('gia_di_xa', SimpleNamespace(**{**vars(tick), 'bid': tick.bid + 2, 'ask': tick.ask + 2}), {}, NOW),
            ('tin_manh', tick, {'gan_tin': True}, NOW),
            ('qua_han', tick, {}, DONG + pd.Timedelta(seconds=T.HAN_GIAY + 1)),
        ):
            with self.subTest(want=want):
                ds = T.quet(fr, now, t, buoc_gia=.01, so_le=2, **kwargs)
                self.assertTrue(all(a['trang_thai'] == want and 'vao' not in a for a in ds), ds)
                json.dumps(ds, allow_nan=False)

    def test_doc_mt5_doc_vi_tri_mot_va_gom_canh_bao_khong_lap(self):
        fr, tick = _fixture()
        s = SimpleNamespace(visible=True, trade_calc_mode=4, trade_tick_size=.01, point=.01, digits=2)
        calls = []

        def rates(ma, tf, vi_tri, n):
            calls.append((ma, tf, vi_tri, n))
            df = fr[tf]
            return df.assign(time=df.index.as_unit('s').asi8).tail(n).to_records(index=False)

        mt = SimpleNamespace(symbol_info=lambda m: s, copy_rates_from_pos=rates, symbol_info_tick=lambda m: tick,
                             **{'TIMEFRAME_' + tf: tf for tf in fr})
        with patch.object(T.da_ma, '_mt5', return_value=mt):
            kq = T.doc({'gia': {}}, 'XAUUSDp', NOW)
        self.assertEqual(calls, [('XAUUSDp', tf, 1, T.MAU) for tf in (*T.KHUNG, 'H1')])
        alerts = canh_bao.ngan_han(kq)
        self.assertEqual(len(alerts), 1)
        self.assertIn('M5/M15/M30', alerts[0]['tieu_de'])
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.assertEqual(len(canh_bao.ghi_moi(out, alerts, NOW)), 1)
            self.assertEqual(canh_bao.ghi_moi(out, alerts, NOW), [])
        self.assertEqual(cai_dat.kiem('canh_bao.ma_ngan_han', 'XAUUSDp,EURUSD.p XAUUSDp'), 'XAUUSDp EURUSD.p')


if __name__ == '__main__':
    unittest.main()
