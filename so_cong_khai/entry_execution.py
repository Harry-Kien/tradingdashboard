"""Versioned experimental entry/SL/TP plans. Pure; no broker or alert authority."""
from __future__ import annotations

import math

VERSION = 'entry-execution-research-v2'
ENTRIES = ('market', 'stop', 'retest')
STOPS = ('structure2', 'swing5', 'atr125')
EXITS = ('rr1', 'rr15', 'rr2', 'split_be')
HOLDS = (12, 36)
FAMILIES = ('goc', 'ket_hop')
BASELINE = 'goc/market/structure2/rr15/12'


def candidates():
    return [f'{family}/{entry}/{stop}/{exit_}/{hold}'
            for family in FAMILIES for entry in ENTRIES for stop in STOPS
            for exit_ in EXITS for hold in HOLDS]


def plan(row: dict, candidate: str, bid: float, ask: float, minutes: int, *, step=.01, digits=2):
    """Lock all order prices after confirmation; never recalculate TP from a worse fill."""
    family, entry_type, stop_type, exit_type, hold_text = candidate.split('/')
    hold = int(hold_text)
    if family not in FAMILIES or entry_type not in ENTRIES or stop_type not in STOPS or exit_type not in EXITS or hold not in HOLDS:
        raise ValueError('Unknown registered candidate')
    numbers = [row[k] for k in ('atr','close','high','low','day','dinh','low5','high5')]+[bid,ask,step]
    if not all(isinstance(v,(float,int)) and math.isfinite(v) and v>0 for v in numbers) or ask<bid:
        return None
    sign=int(row['phia']); atr=float(row['atr']); spread=ask-bid
    if sign not in (-1,1) or minutes not in (5,15,30) or spread>.15*atr or abs(bid-row['close'])>.25*atr:
        return None
    def grid(price, up):
        return round((math.ceil(price/step-1e-8) if up else math.floor(price/step+1e-8))*step,digits)
    quoted=ask if sign>0 else bid
    if entry_type=='market':
        entry=quoted
    elif entry_type=='stop':
        # Candle high/low is Bid; a buy stop is triggered by Ask.
        entry=(row['high']+spread+.05*atr) if sign>0 else (row['low']-.05*atr)
        if (entry-quoted)*sign<=0:
            return None
    else:
        entry=row['close']-sign*.382*(row['high']-row['low'])+(spread if sign>0 else 0)
        if (entry-quoted)*sign>=0:
            return None
    entry=grid(entry,sign>0)
    if stop_type=='structure2':
        sl=min(row['day']-.12*atr,entry-.65*atr) if sign>0 else max(row['dinh']+.12*atr,entry+.65*atr)
    elif stop_type=='swing5':
        sl=min(row['low5']-.15*atr,entry-.65*atr) if sign>0 else max(row['high5']+.15*atr,entry+.65*atr)
    else:
        sl=entry-sign*1.25*atr
    sl=grid(sl,sign<0); risk=(entry-sl)*sign
    # Baseline has the production scanner's exact 2.5 ATR ceiling.
    max_atr=2.5 if candidate==BASELINE else 3.
    if not 0<risk<=max_atr*atr or spread>.15*risk or sl<=0:
        return None
    if entry_type=='market' and (quoted-sl)*sign<=0:
        return None
    rr={'rr1':1.,'rr15':1.5,'rr2':2.,'split_be':2.}[exit_type]
    tp=grid(entry+sign*rr*risk,sign>0)
    tp1=grid(entry+sign*risk,sign>0) if exit_type=='split_be' else None
    if tp<=0 or (tp-entry)*sign<=0:
        return None
    return {'version':VERSION,'candidate':candidate,'side':'MUA' if sign>0 else 'BAN',
            'entry_type':entry_type,'entry':entry,'sl':sl,'tp':tp,'tp1':tp1,
            'exit_type':exit_type,'atr':atr,'hold_minutes':hold*minutes,'wait_minutes':3*minutes,
            'signal_high':float(row['high']),'signal_low':float(row['low'])}


def historical_failures(candidate, baseline):
    """Fail closed on missing/NaN evidence; win rate alone never promotes a rule."""
    failures=[]
    metrics=('closed','mean_r','win_pct','max_closed_drawdown_r')
    def valid(r):
        return all(type(r.get(k)) in (int,float) and math.isfinite(r[k]) for k in metrics)
    for period in ('development','validation','confirmation'):
        for cost in ('base','stress'):
            c=candidate.get(period,{}).get(cost,{})
            b=baseline.get(period,{}).get(cost,{})
            if not valid(c) or not valid(b):
                failures.append(f'{period}/{cost}:invalid_metrics');continue
            if c['closed']<100:
                failures.append(f'{period}/{cost}:sample_below_100')
            if c['mean_r']<=0:
                failures.append(f'{period}/{cost}:nonpositive_expectancy')
            if c['mean_r']<=b['mean_r']:
                failures.append(f'{period}/{cost}:expectancy_not_improved')
            if cost=='base':
                if c['closed']<b['closed']:
                    failures.append(f'{period}:fewer_entries')
                if c['win_pct']<b['win_pct']:
                    failures.append(f'{period}:win_rate_lower')
                if c['max_closed_drawdown_r']>max(1.,1.1*b['max_closed_drawdown_r']):
                    failures.append(f'{period}:drawdown_increased')
    return failures


def promotion_failures(candidate, baseline, evidence):
    failures=historical_failures(candidate,baseline)
    for key in ('independent_future_sample','prospective_positive_after_costs','live_replay_parity','walk_forward_positive_after_costs'):
        if evidence.get(key) is not True:
            failures.append(key+':unproven')
    count=evidence.get('prospective_closed')
    if type(count) is not int or count<200:
        failures.append('prospective_sample_below_200')
    ci=evidence.get('selection_adjusted_ci95')
    if not isinstance(ci,(list,tuple)) or len(ci)!=2 or not all(type(x) in (int,float) and math.isfinite(x) for x in ci) or not 0<ci[0]<=ci[1]:
        failures.append('selection_adjusted_lower_bound_not_positive')
    return failures
