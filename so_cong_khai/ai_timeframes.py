"""One closed-candle context contract for M5/M15/M30 chart readers."""
from __future__ import annotations

import math

from . import gia

VERSION = 'topdown-context-v1'
ENTRY_FRAMES = ('M5', 'M15', 'M30')
BRIDGE = {'M5': 'M15', 'M15': 'M30', 'M30': 'H1'}


def required(tf: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys((tf, BRIDGE.get(tf, 'H1'), 'H1', 'H4', 'D1')))


def number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def direction(frame: dict) -> int:
    values = [frame.get(k) for k in ('close', 'ema20', 'ema50')]
    if not all(number(x) for x in values):
        return 0
    close, fast, slow = values
    return 1 if fast > slow and close > slow else -1 if fast < slow and close < slow else 0


def assess(snapshot: dict) -> dict:
    tf, frames, at = snapshot['timeframe'], snapshot['frames'], snapshot['captured_at']
    rows, missing = [], []
    for frame_tf in required(tf):
        frame = frames.get(frame_tf) or {}
        opened = frame.get('last_closed_candle_open_at')
        seconds = gia.KHUNG[frame_tf] * 60
        closed = opened + seconds if number(opened) else None
        valid = (number(at) and closed is not None and closed <= at
                 and -5 <= at - opened <= max(2 * seconds + 5, 300))
        if frame_tf == 'D1' and not number(frame.get('ema200')):
            valid = False
        if not valid or any(not number(frame.get(k)) for k in ('close', 'ema20', 'ema50')):
            missing.append(frame_tf)
        role = 'entry' if frame_tf == tf else 'macro' if frame_tf == 'D1' else 'bridge' if frame_tf == BRIDGE.get(tf) else 'trend'
        rows.append({'timeframe': frame_tf, 'role': role, 'direction': direction(frame) if valid else 0,
                     'closed_at': closed, 'valid': valid})
    higher = [r['direction'] for r in rows if r['timeframe'] != tf]
    higher_bias = higher[0] if higher and higher[0] and len(set(higher)) == 1 else 0
    daily = frames.get('D1') or {}
    macro_ok = bool(higher_bias and number(daily.get('ema200')) and number(daily.get('close'))
                    and (daily['close'] - daily['ema200']) * higher_bias > 0)
    entry_bias = rows[0]['direction']
    aligned = bool(not missing and higher_bias and macro_ok and entry_bias == higher_bias)
    status = ('missing' if missing else 'macro_conflict' if higher_bias and not macro_ok else
              'higher_conflict' if not higher_bias else 'wait_entry' if entry_bias != higher_bias else 'aligned')
    return {'version': VERSION, 'entry_timeframe': tf, 'bridge_timeframe': BRIDGE.get(tf, 'H1'),
            'required': list(required(tf)), 'rows': rows, 'missing': missing, 'status': status,
            'higher_bias': higher_bias, 'bias': higher_bias if aligned else 0, 'aligned': aligned,
            'macro_ema200_ok': macro_ok, 'closed_candles_only': True, 'profitability_proven': False}


def filter_candidates(snapshot: dict, choices: list[dict]) -> list[dict]:
    """Block contradictory reference scenarios; never authorizes an order."""
    if snapshot['timeframe'] not in ENTRY_FRAMES:
        return choices
    context = assess(snapshot)
    if not context['aligned']:
        return []
    side = 'MUA' if context['bias'] > 0 else 'BAN'
    return [c for c in choices if c['side'] == side]


def from_frames(frames: dict, tf: str, at: float) -> dict:
    """Use exactly the same 240 CLOSED bars and formulas as the AI snapshot."""
    import pandas as pd  # noqa: PLC0415
    from . import ai_chart  # noqa: PLC0415 - called after both modules initialize
    flat = {}
    for frame_tf in required(tf):
        bars = frames.get(frame_tf)
        if bars is None or bars.empty:
            continue
        closed = bars[bars.index + pd.Timedelta(minutes=gia.KHUNG[frame_tf]) <= pd.Timestamp(at, unit='s', tz='UTC')].iloc[-240:]
        if not closed.empty:
            flat[frame_tf] = ai_chart._indicators(closed)
    return assess({'timeframe': tf, 'frames': flat, 'captured_at': at})
