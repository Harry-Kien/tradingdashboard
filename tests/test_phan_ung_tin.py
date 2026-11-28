# -*- coding: utf-8 -*-
"""Phản ứng giá khi tin ra (cong-cu/phan_ung_tin.py): gộp tin cùng phút theo ưu tiên, mốc giá là nến kết thúc đúng lúc tin ra, các quy tắc đoán chiều."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

spec = importlib.util.spec_from_file_location('phan_ung_tin', Path(__file__).resolve().parent.parent / 'cong-cu' / 'phan_ung_tin.py')
PU = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PU)


class PhanUngTin(unittest.TestCase):
    def test_gop_tin_cung_phut(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'l.csv'
            p.write_text('time,currency,importance,event,country\n2024.06.07 12:30,USD,3,Unemployment Rate,US\n2024.06.07 12:30,USD,3,Nonfarm Payrolls,US\n'
                         '2024.06.07 14:00,USD,2,Tin vừa,US\n2024.06.10 14:00,USD,3,Zeta,US\n', encoding='utf-8')
            self.assertEqual([(t.strftime('%m-%d %H:%M'), n) for t, n in PU.lan_ra_tin(p, '2024')], [('06-07 12:30', 'Nonfarm Payrolls'), ('06-10 14:00', 'Zeta')])

    def test_do_moc_gia_va_quy_tac(self):
        idx = pd.date_range('2024-06-07 10:00', periods=240, freq='1min', tz='UTC')
        c = np.full(240, 100.0)
        c[:150] = np.linspace(95, 100, 150)                                # đi lên trong 60 phút trước tin (tin lúc 12:30 = vị trí 150)
        c[150:] = 100 - np.arange(90) * 0.2                               # rồi giảm sau tin
        m1 = pd.DataFrame({'close': c}, index=idx)
        ema = pd.Series([1.0], index=[pd.Timestamp('2024-06-07 11:00', tz='UTC')])
        df = PU.do(m1, np.full(240, 0.2), ema, [(pd.Timestamp('2024-06-07 12:30', tz='UTC'), 'Nonfarm Payrolls')])
        x = df.iloc[0]
        self.assertAlmostEqual(x['d1'], -0.0, places=6)                    # nến 12:30 đóng lúc 12:31 vẫn ở 100
        self.assertAlmostEqual(x['d15'], -2.8, places=6)                   # nến 12:44: 100 − 14 × 0,2
        self.assertGreater(x['truoc60'], 0)
        self.assertEqual(PU.chinh_xac(df, 'a'), (1, 0))                    # đi tiếp chiều lên: sai
        self.assertEqual(PU.chinh_xac(df, 'b'), (1, 1))                    # đi ngược: đúng
        self.assertEqual(PU.chinh_xac(df, 'c'), (1, 0))


if __name__ == '__main__':
    unittest.main()
