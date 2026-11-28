"""Kiểm quy tắc Harrison: nến đóng, không nhìn trước và cổng nghiên cứu."""
import json
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from so_cong_khai import bieu_do, harrison


def frames(sign=1):
    end = pd.Timestamp('2026-11-26T12:00Z')
    out = {}
    for tf, minutes in harrison.MINUTES.items():
        idx = pd.date_range(end=end - pd.Timedelta(minutes=minutes), periods=400, freq=f'{minutes}min')
        close = 3500 + sign * np.arange(400) * .2
        op = close - sign * .2
        op[-1] = close[-1] + sign * .1
        out[tf] = pd.DataFrame({'open': op, 'high': np.maximum(op, close) + .5,
                                'low': np.minimum(op, close) - .5, 'close': close}, index=idx)
    return out


class Harrison(unittest.TestCase):
    def test_ema_trung_cua_so_300_cua_luat_goc(self):
        s = pd.Series(np.random.default_rng(42).normal(size=650).cumsum())
        for span in (20, 50):
            actual = harrison.ema(s, span)
            for j in (59, 298, 299, 300, 649):
                expected = s.iloc[max(0, j - 299):j + 1].ewm(span=span, adjust=False).mean().iloc[-1]
                self.assertAlmostEqual(actual.iloc[j], expected, places=10)

    def test_khong_dung_nen_dang_chay_va_muc_gia_hai_chieu(self):
        now = pd.Timestamp('2026-11-26T12:00:30Z')
        for sign in (1, -1):
            fr = frames(sign)
            with patch.object(harrison, 'load_report', return_value={'selected': 'A', 'gate_passed': True}):
                p = harrison.analyze(fr, 3579, 3579.2, now)
                # Nến đang chạy cố tình đảo mọi EMA; phải bị loại trước khi tính.
                running = {tf: pd.concat([b, pd.DataFrame({'open': [10.], 'high': [90000.], 'low': [1.], 'close': [2.]},
                                                          index=[pd.Timestamp('2026-11-26T12:00Z')])]) for tf, b in fr.items()}
                q = harrison.analyze(running, 3579, 3579.2, now)
            self.assertTrue(p['co'])
            self.assertTrue(p['hieu_luc'])
            self.assertEqual(p, q)
            self.assertEqual(p['huong'], 'MUA' if sign > 0 else 'BAN')
            self.assertAlmostEqual((p['vao'] - p['sl']) * sign, 20)
            self.assertAlmostEqual((p['tp'][0] - p['vao']) * sign, 5)
            self.assertEqual(p['rr'], [.25])

    def test_khong_nhin_truoc_tai_ranh_gio_dong(self):
        fr = frames()
        table = harrison.indicators(fr)
        when = pd.Timestamp('2026-11-26T11:59:59Z')
        before = harrison.features(table, when)
        for b in fr.values():
            b.iloc[-1, b.columns.get_loc('close')] = 10000
        self.assertEqual(before, harrison.features(harrison.indicators(fr), when))

    def test_nghien_cuu_khong_thanh_tin_hieu_du_dieu_kien(self):
        with patch.object(harrison, 'load_report', return_value={'selected': 'A', 'gate_passed': False}):
            p = harrison.analyze(frames(), 3579, 3579.2, pd.Timestamp('2026-11-26T12:01Z'))
        self.assertTrue(p['co'])
        self.assertFalse(p['hieu_luc'])
        self.assertIn('chưa qua', ' '.join(p['vi_sao_het']))

    def test_chan_spread_gia_cu_lich_tin_va_thieu_du_lieu(self):
        with patch.object(harrison, 'load_report', return_value={'selected': 'A', 'gate_passed': True}):
            for ask, now, reasons in [(3580, '12:01', []), (3579.2, '12:06', []), (3579.2, '12:01', ['Đang né tin.'])]:
                p = harrison.analyze(frames(), 3579, ask, pd.Timestamp(f'2026-11-26T{now}Z'), reasons)
                self.assertFalse(p['hieu_luc'])
            thin = {tf: b.tail(30) for tf, b in frames().items()}
            self.assertFalse(harrison.analyze(thin, 3579, 3579.2, pd.Timestamp('2026-11-26T12:01Z'))['co'])
            empty = {tf: b.iloc[:0] for tf, b in frames().items()}
            self.assertFalse(harrison.analyze(empty, 3579, 3579.2)['co'])

    def test_bao_cao_thieu_hong_sai_phien_ban_deu_khong_mo_cong(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'r.json'
            self.assertEqual(harrison.load_report(p), {})
            for raw in ('{', '[]', 'null', '{"version":"khac","gate_passed":true}'):
                p.write_text(raw, encoding='utf-8')
                self.assertEqual(harrison.load_report(p), {})
        with patch.object(harrison, 'load_report', return_value={'selected': 'khac', 'gate_passed': True}):
            self.assertFalse(harrison.analyze(frames(), 3579, 3579.2, pd.Timestamp('2026-11-26T12:01Z'))['hieu_luc'])

    def test_bao_cao_da_phat_hanh_khop_ma_va_cong(self):
        import hashlib
        r = harrison.load_report()
        self.assertEqual(r['selected'], 'A')
        self.assertFalse(r['gate_passed'])
        self.assertEqual(r['original_signal_mismatches'], 0)
        self.assertEqual(r['candidates']['original']['stats']['all']['trades'], 4100)
        actual = hashlib.sha256(Path(harrison.__file__).read_bytes()).hexdigest()
        expected = next(v for k, v in r['source_sha256'].items() if k.replace('\\', '/') == 'so_cong_khai/harrison.py')
        self.assertEqual(expected, actual)
        self.assertEqual(r['gate_passed'], all(g['passed'] for g in r['gates']))

    @unittest.skipUnless(shutil.which('node'), 'Cần Node để kiểm UI')
    def test_giao_dien_luon_hien_chung_cu_ke_ca_khong_co_setup(self):
        fn = bieu_do.JS.split('function harrisonHtml(p)', 1)[1].split('function kcHtml(p)', 1)[0]
        js = "const document={documentElement:{lang:'vi'}};const esc=x=>String(x).replaceAll('<','&lt;');\nfunction harrisonHtml(p)" + fn
        p = {'co': False, 'harrison': {'report': harrison.load_report(), 'status': '<img>', 'checks': [], 'scope': 'XAUUSD', 'version': harrison.VERSION}}
        js += '\nprocess.stdout.write(harrisonHtml(' + json.dumps(p, ensure_ascii=False) + '));'
        out = subprocess.run([shutil.which('node')], input=js, capture_output=True, encoding='utf-8', timeout=10)
        self.assertEqual(out.returncode, 0, out.stderr)
        for text in ('81,57', '81,39', 'Cổng kiểm chứng', 'Tất cả bộ lọc', '2020–2022', '&lt;img>'):
            self.assertIn(text, out.stdout)
        self.assertNotIn('<img>', out.stdout)


if __name__ == '__main__':
    unittest.main()
