"""Free, deterministic chart reading. No LLM, API key, training or order execution.

Uses the same trusted closed-candle MT5 snapshot as the paid analyst. Candidate
levels are conditional references, never profitability forecasts or trade orders.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time
from collections import OrderedDict
from pathlib import Path

from . import ai_chart, ai_store

VERSION = 'chart-rules-v1'
_lock = threading.Lock()
_recent: OrderedDict = OrderedDict()


def _rate(root: Path, uid: str, now: float) -> None:
    key = (str(root.resolve()), uid)
    with _lock:
        previous = _recent.get(key)
        if previous is not None and 0 <= now-previous < 2:
            raise ai_store.StoreError('Đợi 2 giây trước lần phân tích miễn phí tiếp theo.', 429)
        _recent[key] = now
        _recent.move_to_end(key)
        while len(_recent)>1024:
            _recent.popitem(last=False)


def direction(frame: dict) -> int:
    values = [frame.get(k) for k in ('close', 'ema20', 'ema50')]
    if not all(type(v) in (int, float) and math.isfinite(v) for v in values):
        return 0
    close, fast, slow = values
    return 1 if fast>slow and close>slow else -1 if fast<slow and close<slow else 0


def analyze(root: Path, cfg: dict, user: dict, body: dict, *, snapshot_fn=None, clock=None) -> dict:
    clock = clock or time.time
    if not user or not isinstance(user.get('id'), str) or not re.fullmatch('[a-f0-9]{32}', user['id']):
        raise ai_store.StoreError('Đăng nhập tài khoản biểu đồ để phân tích.', 401)
    if not user.get('chu'):
        raise ai_store.StoreError('Dữ liệu MT5 trên máy thuộc tài khoản chủ; dùng bản cài riêng để phân tích dữ liệu của bạn.', 403)
    if body.get('image') or body.get('question'):
        raise ai_store.StoreError('Chế độ quy tắc miễn phí không đọc ảnh hoặc trả lời câu hỏi tự do.')
    # Browser indicators are neither needed nor accepted as market evidence here.
    request = ai_chart.clean({k: v for k, v in body.items() if k in ('ma', 'tf', 'mode', 'lang', 'replay')})
    _rate(root, user['id'], clock())
    conf = ai_store.settings(root)
    snap = (snapshot_fn or ai_chart.snapshot)(cfg, request['ma'], request['tf'], conf['quote_max_age'])
    en = request['lang']=='en'
    text = lambda vi, english: english if en else vi  # noqa: E731
    frames = snap['frames']
    direction_by_tf = {tf: direction(f) for tf, f in frames.items()}
    needed = tuple(dict.fromkeys((request['tf'], 'H1', 'H4', 'D1')))
    directions = [direction_by_tf.get(tf, 0) for tf in needed]
    aligned = len(directions)>=3 and len(set(directions))==1 and directions[0]!=0
    bias = directions[0] if aligned else 0
    main = frames[request['tf']]
    rsi = main.get('rsi14')
    atr = main.get('atr14_sma')
    spread_ratio = snap['spread']/atr if ai_chart._num(atr) and atr>0 else None
    agreement, conflicts, watch, selected = [], [], [], []
    if aligned:
        agreement.append(text('Các khung cùng chiều theo EMA20/EMA50 và giá đóng.', 'Timeframes agree on EMA20/EMA50 and closing price.'))
    else:
        conflicts.append(text('Đa khung chưa đồng thuận hoặc thiếu EMA; giữ trạng thái đứng ngoài.', 'Timeframes disagree or EMA data is missing; stand aside.'))
    daily = frames.get('D1') or {}
    ema200 = daily.get('ema200')
    daily_ok = ai_chart._num(ema200) and (daily['close']-ema200)*bias>0 if bias else False
    if bias and not daily_ok:
        conflicts.append(text('Giá đóng D1 chưa xác nhận cùng phía EMA200 hoặc chưa đủ dữ liệu.', 'D1 close does not confirm the same side of EMA200, or data is insufficient.'))
    momentum_ok = ai_chart._num(rsi) and (40<=rsi<=70 if bias>0 else 30<=rsi<=60) if bias else False
    if bias and not momentum_ok:
        conflicts.append(text('RSI14 chưa nằm trong khoảng xác nhận của bộ quy tắc; không đuổi giá.', 'RSI14 is outside the rule confirmation range; avoid chasing price.'))
    spread_ok = spread_ratio is not None and spread_ratio<=.15
    if not spread_ok:
        conflicts.append(text('Spread quá lớn so với ATR hoặc chưa đủ dữ liệu biến động.', 'Spread is too large relative to ATR, or volatility data is insufficient.'))
    if aligned and daily_ok and momentum_ok and spread_ok:
        side = 'MUA' if bias>0 else 'BAN'
        for candidate in ai_chart.candidates(snap, conf):
            if candidate['side']!=side:
                continue
            if en:
                conditions = {
                    'breakout_buy':'A candle closes above the prior 20-bar high, followed by a retest of the breakout area.',
                    'breakout_sell':'A candle closes below the prior 20-bar low, followed by a retest of the breakout area.',
                    'pullback_buy':'Pull back to EMA20 with a closed bullish confirmation candle while EMA20 remains above EMA50.',
                    'pullback_sell':'Pull back to EMA20 with a closed bearish confirmation candle while EMA20 remains below EMA50.',
                }
                candidate = {**candidate,'condition':conditions[candidate['id']],
                             'execution_note':'Conditional reference levels, not confirmed entries; account for spread, slippage, commission and broker stop rules.'}
            selected.append({**candidate, 'reason': text('Đa khung, EMA200 D1, RSI và spread vượt qua các điều kiện kiểm tra.', 'Timeframes, D1 EMA200, RSI and spread pass the rule checks.'),
                             'trigger': text('Chưa xác nhận vào lệnh. Chờ đúng điều kiện máy chủ và nến đã đóng; không vào chỉ vì thấy mức giá.', 'Entry is not confirmed. Wait for the server condition and a closed candle; a displayed price is insufficient.'),
                             'invalidation': text('Hủy khi đa khung mất đồng thuận, giá chạm SL, spread tăng hoặc ảnh chụp hết hạn.', 'Invalidate on timeframe disagreement, SL touch, spread widening, or snapshot expiry.')})
            if len(selected)==2:
                break
    watch += [text('Chưa có lịch tin kinh tế trong snapshot này; cần kiểm tra trước khi cân nhắc giao dịch.', 'Economic news is unavailable in this snapshot; check it before considering a trade.'),
              text('R:R là tỷ lệ mức giá tham chiếu trước chi phí, không phải xác suất thắng.', 'R:R describes reference price distances before costs, not a win probability.'),
              text('Bộ quy tắc chưa được chứng minh có lợi nhuận; nhiều chỉ báo đồng thuận vẫn có thể sai.', 'These rules have no demonstrated profitability; indicator agreement can still be wrong.')]
    summary = text('Có kịch bản tham chiếu cần chờ xác nhận.' if selected else 'ĐỨNG NGOÀI · Chưa có kịch bản vượt qua các điều kiện kiểm tra.',
                   'Conditional reference scenarios need confirmation.' if selected else 'STAND ASIDE · No scenario passes the rule checks.')
    trend = text('Xu hướng đồng thuận tăng.' if bias>0 else 'Xu hướng đồng thuận giảm.' if bias<0 else 'Các khung chưa thống nhất hướng.',
                 'Aligned upward trend.' if bias>0 else 'Aligned downward trend.' if bias<0 else 'Timeframes have no common direction.')
    checks = [
        {'id': 'alignment', 'label': text('Đồng thuận đa khung', 'Timeframe alignment'), 'passed': aligned},
        {'id': 'daily_ema200', 'label': 'D1 / EMA200', 'passed': bool(daily_ok)},
        {'id': 'momentum', 'label': 'RSI14', 'passed': bool(momentum_ok)},
        {'id': 'spread', 'label': 'Spread / ATR14', 'passed': spread_ok},
    ]
    return {'ok': True, 'analysis': {'summary': summary, 'trend': trend, 'agreement': agreement, 'conflicts': conflicts, 'watch': watch,
                                    'scenarios': selected, 'answer': ''},
            'ma': request['ma'], 'tf': request['tf'], 'mode': request['mode'], 'engine': 'rules', 'training': 'not_trained', 'read_only': True,
            'snapshot_at': snap['captured_at'], 'quote_at': snap['quote_at'], 'bid': snap['bid'], 'ask': snap['ask'],
            'reference_atr': atr, 'digits': snap['digits'], 'expires_at': snap['captured_at']+conf['quote_max_age'],
            'expired': clock()-snap['captured_at']>conf['quote_max_age'],
            'snapshot_sha': hashlib.sha256(json.dumps(snap, sort_keys=True, allow_nan=False).encode()).hexdigest(),
            'provider': 'local_rules', 'model': VERSION, 'prompt_version': VERSION, 'vision_used': False,
            'chi_phi_usd': 0, 'cost_is_estimate': False,
            'checks': checks, 'evidence': [{'timeframe': tf, 'direction': direction_by_tf[tf], **frame} for tf, frame in frames.items()],
            'mien_tru': text('Phân tích bằng quy tắc tại máy chủ, không gửi dữ liệu tới AI bên ngoài. Không phải mô hình đã huấn luyện, không đặt lệnh và không hứa lợi nhuận.',
                             'Server-side rule analysis; no external AI data transmission. This is not a trained model, does not execute orders and promises no profit.')}
