"""Closed-candle entry experiment. Pure functions, never submits broker orders."""
from __future__ import annotations

import math


def confirmed(snap: dict, choices: list[dict], min_rr: float = 1.5, *, quality: bool = False) -> list[dict]:
    """Confirm a reclaim or a two-candle breakout retest using past candles only.

    Entry is a quote reference AFTER confirmation, never an assumed earlier EMA fill.
    This experimental confirmation has no profitability claim or execution authority.
    """
    cs = snap['candles']
    if len(cs)<22:
        return []
    frame = snap['frames'][snap['timeframe']]
    atr, ema = frame.get('atr14_sma'), frame.get('ema20')
    if not atr or atr<=0 or ema is None:
        return []
    current, previous = cs[-1], cs[-2]
    span = current[2]-current[3]
    if span<=0:
        return []
    out=[]
    for choice in choices:
        side=1 if choice['side']=='MUA' else -1
        close, op = current[4], current[1]
        if (close-op)*side<=0:
            continue
        if choice['id'].startswith('pullback'):
            ok=current[3]<=ema<=current[2] and (close-ema)*side>0
            kind='ema20_reclaim'
        else:
            level=max(row[2] for row in cs[-22:-2]) if side>0 else min(row[3] for row in cs[-22:-2])
            ok=(previous[4]-level)*side>0 and current[3]<=level<=current[2] and (close-level)*side>0
            kind='breakout_retest'
        if not ok:
            continue
        entry=snap['ask'] if side>0 else snap['bid']
        risk=(entry-choice['sl'])*side
        minimum=max(.5*atr, max(0,snap.get('stops_level_points',0))*snap['point'])
        if not minimum<=risk<=6*atr or abs(entry-close)>atr:
            continue
        if quality:
            separation=abs(frame['ema20']-frame['ema50'])/atr
            location=(close-current[3])/span if side>0 else (current[2]-close)/span
            if not (.75*atr<=risk<=4*atr and abs(close-op)/span>=.25 and location>=.6 and separation>=.1):
                continue
        step=snap.get('tick_size') or snap['point']
        targets=[]
        for rr in (min_rr,max(2.,min_rr+.5)):
            price=entry+side*risk*rr
            grid=math.ceil(price/step-1e-9) if side>0 else math.floor(price/step+1e-9)
            targets.append(round(grid*step,snap['digits']))
        if min(targets)<=0:
            continue
        out.append({**choice,'entry':entry,'tp':targets,'rr':[(p-entry)*side/risk for p in targets],
                    'state':'confirmed_on_closed_candle','confirmation':kind,
                    'signal_candle_open_at':current[0],
                    'execution_note':'Closed-candle confirmation only; quote reference is not a guaranteed fill or an order.'})
    return out
