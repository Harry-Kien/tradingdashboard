"""Entry, gap, partial-exit and approval behavior must not inflate results."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from so_cong_khai import entry_execution as E

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('execution_replay',ROOT/'cong-cu/entry_execution_replay.py')
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)
spec=importlib.util.spec_from_file_location('old_execution_replay',ROOT/'cong-cu/backtest_nam_ngay_20261128.py')
OLD=importlib.util.module_from_spec(spec);spec.loader.exec_module(OLD)


class EntryExecution(unittest.TestCase):
    def bars(self,n=6):
        return pd.DataFrame({'open':100.,'high':100.2,'low':99.8,'close':100.},
                            index=pd.date_range('2026-01-05',periods=n,freq='min',tz='UTC'))

    def p(self,b,**kw):
        return {'at':b.index[0].value,'tf':'M5','side':'MUA','entry_type':'market','entry':100.,'sl':99.,
                'tp':102.,'tp1':101.,'exit_type':'rr2','atr':2.,'hold_minutes':4,'wait_minutes':3,**kw}

    def test_market_replay_matches_existing_fixed_target_engine(self):
        b=self.bars();b.loc[b.index[2],'high']=103.
        p=self.p(b);sp=np.full(len(b),.17)
        new,_=R.simulate(b,sp,[p]);old,_=OLD.simulate(b,sp,[p])
        for key in ('entry_fill','risk_fill','r','exit_time','tp_fixed','sl_fixed'):
            self.assertEqual(new[0][key],old[0][key])

    def test_buy_stop_uses_ask_and_adverse_gap(self):
        b=self.bars();b.iloc[1]=[103.,103.2,102.8,103.]
        p=self.p(b,entry_type='stop',entry=101.,sl=99.,tp=105.)
        trades,_=R.simulate(b,np.full(len(b),.2),[p])
        self.assertAlmostEqual(trades[0]['entry_fill'],103.25)
        self.assertEqual(trades[0]['tp_fixed'],105.)

    def test_sell_stop_triggers_bid_not_ask(self):
        b=self.bars();b.loc[b.index[1],'low']=98.9
        p=self.p(b,side='BAN',entry_type='stop',entry=99.,sl=101.,tp=97.)
        trades,_=R.simulate(b,np.full(len(b),.2),[p])
        self.assertAlmostEqual(trades[0]['entry_fill'],98.95)

    def test_limit_touch_without_penetration_is_not_a_fill(self):
        b=self.bars();b['low']=99.
        p=self.p(b,entry_type='retest',entry=99.,sl=98.,tp=101.)
        trades,counts=R.simulate(b,np.zeros(len(b)),[p])
        self.assertEqual(trades,[]);self.assertEqual(counts['expired'],1)

    def test_pending_fill_minute_does_not_claim_earlier_high_as_tp(self):
        b=self.bars();b.iloc[0]=[100.,103.,98.9,99.]
        p=self.p(b,entry_type='retest',entry=99.,sl=98.,tp=102.,hold_minutes=2)
        trades,_=R.simulate(b,np.zeros(len(b)),[p])
        self.assertEqual(trades[0]['reason'],'TIME')

    def test_both_barriers_stop_first(self):
        b=self.bars();b.iloc[1]=[100.,103.,98.,100.]
        trades,_=R.simulate(b,np.zeros(len(b)),[self.p(b)])
        self.assertEqual(trades[0]['reason'],'SL')
        self.assertTrue(trades[0]['ambiguous_m1'])

    def test_gap_past_target_is_not_dropped_to_hide_cost(self):
        b=self.bars();b.iloc[0]=[103.,103.2,102.8,103.]
        p=self.p(b,entry_type='stop',entry=101.,sl=99.,tp=102.)
        trades,_=R.simulate(b,np.full(len(b),.2),[p])
        self.assertEqual(trades[0]['reason'],'GAP_LEVEL_INVALID')
        self.assertLess(trades[0]['r'],0)

    def test_stop_fill_cannot_exit_at_a_gap_before_its_entry(self):
        b=self.bars();b.iloc[0]=[98.,101.,97.,100.]
        p=self.p(b,entry_type='stop',entry=100.5,sl=99.,tp=103.)
        trades,_=R.simulate(b,np.zeros(len(b)),[p])
        self.assertFalse(trades[0]['entry_at_open'])
        self.assertAlmostEqual(trades[0]['legs'][0]['price'],98.95)

    def test_archive_end_does_not_fake_an_expired_pending_order(self):
        b=self.bars(1)
        p=self.p(b,entry_type='stop',entry=101.,sl=99.,tp=103.)
        trades,counts=R.simulate(b,np.zeros(len(b)),[p])
        self.assertEqual(trades,[])
        self.assertEqual(counts['pending_unresolved'],1)
        self.assertEqual(counts['expired'],0)

    def test_partial_stop_moves_only_on_following_minute(self):
        b=self.bars();b.iloc[1]=[100.5,101.2,100.,100.7]
        b.iloc[2]=[100.,100.2,99.8,100.]
        trades,_=R.simulate(b,np.zeros(len(b)),[self.p(b,exit_type='split_be')])
        t=trades[0]
        self.assertEqual(t['reason'],'SPLIT_BE')
        self.assertEqual(t['legs'][0]['at'],b.index[1].isoformat())
        self.assertEqual(t['legs'][1]['at'],b.index[2].isoformat())
        self.assertEqual(sum(x['fraction'] for x in t['legs']),1.)

    def test_unresolved_partial_is_open_not_a_winning_closed_trade(self):
        b=self.bars(2);b.iloc[1]=[100.5,101.2,100.4,100.7]
        trades,_=R.simulate(b,np.zeros(len(b)),[self.p(b,exit_type='split_be')])
        self.assertFalse(trades[0]['closed']);self.assertIsNone(trades[0]['r'])

    def test_context_change_cancels_waiting_order_before_fill(self):
        b=self.bars();b.iloc[2]=[102.,103.,101.,102.]
        p=self.p(b,entry_type='stop',entry=101.,sl=99.,tp=104.,context_until=b.index[1].value)
        trades,counts=R.simulate(b,np.zeros(len(b)),[p])
        self.assertEqual(trades,[]);self.assertEqual(counts['cancelled_context'],1)

    def test_grid_and_invalid_price_handling(self):
        self.assertEqual(len(E.candidates()),144)
        self.assertEqual(len(set(E.candidates())),144)
        row={'atr':1.,'close':100.,'high':101.,'low':99.,'day':99.,'dinh':101.,'low5':98.,'high5':102.,'phia':1}
        p=E.plan(row,E.BASELINE,100.,100.10,5)
        self.assertTrue(p['sl']<p['entry']<p['tp'])
        self.assertIsNone(E.plan({**row,'atr':float('nan')},E.BASELINE,100.,100.17,5))

    def test_nan_and_missing_evidence_never_approve(self):
        row={'closed':300,'mean_r':.2,'win_pct':65.,'max_closed_drawdown_r':5.}
        baseline={p:{c:{**row,'mean_r':.1,'win_pct':60.} for c in ('base','stress')}
                  for p in ('development','validation','confirmation')}
        candidate={p:{c:row.copy() for c in ('base','stress')} for p in baseline}
        self.assertEqual(E.historical_failures(candidate,baseline),[])
        good={'independent_future_sample':True,'prospective_positive_after_costs':True,'live_replay_parity':True,
              'walk_forward_positive_after_costs':True,'prospective_closed':200,'selection_adjusted_ci95':[.01,.1]}
        self.assertEqual(E.promotion_failures(candidate,baseline,good),[])
        self.assertTrue(E.promotion_failures(candidate,baseline,{**good,'selection_adjusted_ci95':[float('nan'),1.]}))
        candidate['validation']['base']['mean_r']=float('nan')
        self.assertTrue(E.promotion_failures(candidate,baseline,good))


if __name__=='__main__':
    unittest.main()
