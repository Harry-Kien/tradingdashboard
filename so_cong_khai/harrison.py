"""Harrison 3 Khung: quy tắc gốc và bốn bộ lọc chốt trước khi đo.

Hàm thuần, chỉ nến đã đóng, không nối MT5, không gửi tin hay đặt lệnh.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = 'harrison-3khung-research-1'
TP, SL = 5.0, 20.0
CANDIDATES = {'A': 'Nhịp hồi nhỏ', 'B': 'Xu hướng H1 đủ mạnh', 'C': 'Hồi gần EMA20', 'D': 'Nhịp hồi nhỏ và H1 đủ mạnh'}
REPORT = Path(__file__).resolve().parent.parent / 'tinh' / 'harrison-nghien-cuu.json'
MINUTES = {'M15': 15, 'H1': 60, 'H4': 240, 'D1': 1440}


def ema(s: pd.Series, span: int) -> pd.Series:
    """EMA adjust=False của tối đa 300 nến, giống quy tắc gốc."""
    v = s.to_numpy(dtype=float)
    out = s.ewm(span=span, adjust=False).mean().to_numpy(copy=True)
    if len(v) >= 300:
        a = 2.0 / (span + 1)
        w = a * (1 - a) ** np.arange(299, -1, -1)
        w[0] = (1 - a) ** 299
        out[299:] = np.convolve(v, w[::-1], mode='valid')
    return pd.Series(out, index=s.index)


def indicators(fr: dict) -> dict:
    out = {}
    for tf in MINUTES:
        b = fr[tf]
        close = b['close'].astype(float)
        fast, slow = ema(close, 20), ema(close, 50)
        high, low, prev = b['high'], b['low'], close.shift(1)
        tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14, min_periods=14).mean()
        out[tf] = pd.DataFrame({'direction': np.sign(fast - slow), 'ema': fast, 'atr': atr,
                               'gap': (fast - slow).abs() / atr.replace(0, np.nan), 'slope': fast - fast.shift(3),
                               'body': (close - b['open']).abs() / atr.replace(0, np.nan),
                               'range': (high - low) / atr.replace(0, np.nan),
                               'near': (close - fast).abs() / atr.replace(0, np.nan),
                               'candle': np.sign(close - b['open']), 'count': np.arange(1, len(b) + 1)},
                              index=b.index)
        out[tf].index = out[tf].index + pd.Timedelta(minutes=MINUTES[tf])
    return out


def features(table: dict, when) -> dict:
    t = pd.Timestamp(when)
    if t.tzinfo is None:
        t = t.tz_localize('UTC')
    rows = {}
    for tf, df in table.items():
        j = int(df.index.searchsorted(t, side='right')) - 1
        if j < 0 or df.iloc[j]['count'] < 60:
            return {}
        rows[tf] = df.iloc[j]
    direction = int(rows['H1']['direction'])
    base = direction != 0 and all(int(rows[k]['direction']) == direction for k in ('D1', 'H4')) and int(rows['M15']['candle']) == -direction
    small = bool(rows['M15']['body'] <= .5 and rows['M15']['range'] <= 1.5)
    strong = bool(rows['H1']['gap'] >= .5 and rows['H1']['slope'] * direction > 0)
    near = bool(rows['M15']['near'] <= .75)
    return {'base': base, 'side': 'MUA' if direction > 0 else 'BAN', 'small': small, 'strong': strong, 'near': near,
            'A': small, 'B': strong, 'C': near, 'D': small and strong,
            'body_atr': float(rows['M15']['body']), 'range_atr': float(rows['M15']['range']),
            'near_atr': float(rows['M15']['near']), 'h1_gap_atr': float(rows['H1']['gap'])}


def allowed(f: dict, candidate: str, spread: float) -> bool:
    return bool(f.get('base') and f.get(candidate) and 0 <= spread <= .1 * TP)


def load_report(path: Path | None = None) -> dict:
    try:
        r = json.loads((path or REPORT).read_text(encoding='utf-8'))
        return r if isinstance(r, dict) and r.get('version') == VERSION else {}
    except (OSError, ValueError, TypeError):
        return {}


def analyze(fr: dict, bid: float, ask: float, now: datetime | None = None, reasons: list | None = None) -> dict:
    """Phương án nghiên cứu. Cổng lịch sử chưa đạt thì chỉ tham khảo, không ghi như tín hiệu đạt cổng."""
    now = pd.Timestamp(now or datetime.now(timezone.utc))
    now = now.tz_localize('UTC') if now.tzinfo is None else now.tz_convert('UTC')
    fr = {tf: fr[tf].loc[fr[tf].index + pd.Timedelta(minutes=minutes) <= now] for tf, minutes in MINUTES.items()}
    report = load_report()
    selected = report.get('selected', 'A')
    if selected not in CANDIDATES:
        selected = 'A'
        report = {}  # không dùng báo cáo của cấu hình không tồn tại để mở cổng
    last = fr['M15'].index[-1] + timedelta(minutes=15) if len(fr['M15']) else now.floor('15min')
    f = features(indicators(fr), last) if all(len(b) for b in fr.values()) else {}
    minute = last.hour * 60 + last.minute
    window = last.weekday() < 5 and 420 <= minute <= 1200
    checks = [{'ten': 'D1, H4, H1 cùng chiều và M15 hồi ngược', 'dat': bool(f.get('base'))},
              {'ten': 'Giờ đóng M15 trong 07:00–20:00 UTC, thứ Hai–thứ Sáu', 'dat': window},
              {'ten': 'Spread không quá 10% khoảng chốt lời', 'dat': 0 <= ask - bid <= .5},
              {'ten': CANDIDATES.get(selected, selected), 'dat': bool(f.get(selected))}]
    technically_valid = bool(f and window and allowed(f, selected, ask - bid))
    why = list(reasons or [])
    age = max(0., (now - last.to_pydatetime()).total_seconds() / 60)
    if age > 5:
        why.append('Nến tín hiệu đã quá hạn vào lệnh 5 phút.')
    if not report.get('gate_passed'):
        why.append('Ứng viên chưa qua đủ cổng kiểm chứng; chỉ để nghiên cứu.')
    name = 'Harrison 3 Khung'
    evidence = {'version': VERSION, 'selected': selected, 'candidate': CANDIDATES.get(selected, selected),
                'gate_passed': bool(report.get('gate_passed')), 'checks': checks, 'report': report,
                'status': 'Kiểm tiến cứu' if report.get('gate_passed') else 'Nghiên cứu — chưa đạt cổng',
                'scope': 'XAUUSD · M15 · TP 5 giá / SL 20 giá', 'signal_time': last.isoformat()}
    out = {'ma': 'harrison', 'ten': name, 'ten_ngan': name, 'chip': 'harrison', 'nhom': 'pp',
           'truong_phai': 'Theo xu hướng nhiều khung và nhịp hồi', 'kieu': CANDIDATES.get(selected, selected),
           'co': technically_valid, 'hieu_luc': technically_valid and not why,
           'vi_sao': 'Chưa đủ điều kiện Harrison; xem từng điều kiện trong phần kiểm chứng.', 'vi_sao_het': why if technically_valid else [],
           'thong_ke': 'Bộ lọc được chọn trên 2015–2019; kiểm hồi cứu 2020–2022 và 2023–2026. Không phải ngoài mẫu mới.',
           'ghi_chu': ['Nhãn Harrison là tên bộ quy tắc, không chứng minh tính mới hoặc lợi nhuận tương lai.'], 'harrison': evidence,
           'nen': last.isoformat(), 'con_phut': None, 'ly_do': 'Ba khung cùng chiều, M15 hồi ngược; ' + CANDIDATES.get(selected, selected) + '.'}
    if technically_valid:
        side = f['side']
        sign = 1 if side == 'MUA' else -1
        entry = round(ask if sign > 0 else bid, 2)
        out.update(huong=side, vao=entry, sl=round(entry - sign * SL, 2), tp=[round(entry + sign * TP, 2)], rr=[TP / SL],
                   rui_ro_gia=SL, vung=None)
    return out
