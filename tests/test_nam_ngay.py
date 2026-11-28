"""Five-day evaluation must retain late exits and preserve quoted targets."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

spec=importlib.util.spec_from_file_location('recent_days',Path(__file__).resolve().parents[1]/'cong-cu/backtest_nam_ngay_20261128.py')
recent=importlib.util.module_from_spec(spec);spec.loader.exec_module(recent)


class RecentDays(unittest.TestCase):
    def bars(self,n=4):
        index=pd.date_range('2026-11-27T10:00Z',periods=n,freq='min')
        return pd.DataFrame({'open':100.,'high':100.1,'low':99.9,'close':100.},index=index)

    def plan(self,bars,tf='M5'):
        return {'at':bars.index[0].value,'tf':tf,'side':'MUA','entry':100.,'sl':99.,'tp':101.5,'atr':2.}

    def test_final_day_trade_with_observed_tp_is_not_discarded(self):
        bars=self.bars();bars.iloc[1,bars.columns.get_loc('high')]=102.
        trades,_=recent.simulate(bars,np.zeros(len(bars)),[self.plan(bars)])
        self.assertTrue(trades[0]['closed'])
        self.assertEqual(trades[0]['reason'],'TP')

    def test_unresolved_trade_stays_open_outside_win_denominator(self):
        bars=self.bars();trades,_=recent.simulate(bars,np.zeros(len(bars)),[self.plan(bars)])
        summary=recent.stats(trades)
        self.assertEqual((summary['entered'],summary['open'],summary['closed']),(1,1,0))
        self.assertIsNone(summary['win_pct'])

    def test_slippage_does_not_move_fixed_target_to_improve_r(self):
        bars=self.bars();bars.iloc[1,bars.columns.get_loc('high')]=102.
        trades,_=recent.simulate(bars,np.full(len(bars),.2),[self.plan(bars)])
        self.assertAlmostEqual(trades[0]['entry_fill'],100.25)
        self.assertEqual(trades[0]['tp_fixed'],101.5)
        self.assertLess(trades[0]['r'],1.5)

    def test_ambiguous_minute_loses_and_adverse_gap_uses_open(self):
        bars=self.bars();bars.iloc[1]=[100.,102.,98.,100.]
        trades,_=recent.simulate(bars,np.zeros(len(bars)),[self.plan(bars)])
        self.assertEqual(trades[0]['reason'],'SL')
        self.assertTrue(trades[0]['ambiguous_m1'])
        bars.iloc[1]=[97.,98.,96.,97.]
        trades,_=recent.simulate(bars,np.zeros(len(bars)),[self.plan(bars)])
        self.assertEqual(trades[0]['reason'],'SL_GAP')
        self.assertLess(trades[0]['exit_fill'],97.)

    def test_cross_frame_calls_are_merged_by_close_and_side(self):
        bars=self.bars()
        merged=recent.merge([self.plan(bars,tf) for tf in ('M5','M15','M30')])
        self.assertEqual(len(merged),1)
        self.assertEqual(merged[0]['tf'],'M30')
        self.assertEqual(merged[0]['contributing_frames'],'M30,M15,M5')

    def test_open_position_prevents_fabricated_extra_trades(self):
        bars=self.bars();a=self.plan(bars);b={**a,'at':a['at']+recent.MINUTE}
        trades,counts=recent.simulate(bars,np.zeros(len(bars)),[a,b])
        self.assertEqual(len(trades),1)
        self.assertEqual(counts['blocked_by_open_position'],1)


if __name__=='__main__':
    unittest.main()
