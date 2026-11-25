"""Chỉ báo chung cho bản chia sẻ (máy không có mã EA Promax và bot tín hiệu của chủ dự án).

Chỉ gồm các định nghĩa chuẩn, cùng cách tính với các hàm cùng tên trong mã của chủ dự án để số liệu khớp nhau:
ATR14 trung bình đơn, hỗ trợ/kháng cự là đáy/đỉnh của N giờ gần nhất, hướng EMA20 so với EMA50, khoảng trống giá (FVG) ba nến
còn chưa lấp, khối lệnh (order block) chưa bị phá. KHÔNG có luật vào lệnh nào của chủ dự án ở đây: bản chia sẻ dùng các phương
pháp tùy chọn (phuong_phap.py) tính theo ATR.

Dùng qua gia._nap_ma(g), trả (R, RT, None, SN) như mã thật: R.atr_sma, R.levels_sr, R.sr_bars, RT.directions, SN.fvg_zones, SN.order_blocks."""
from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pandas as pd

KHUNG = {'M1': '1min', 'M5': '5min', 'M15': '15min', 'M30': '30min', 'H1': '1h', 'H4': '4h', 'D1': '1D'}


def atr_sma(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ATR: trung bình đơn `period` nến của biên độ thật (true range); nến đầu lấy cao − thấp."""
    prev = df['close'].shift(1)
    tr = pd.concat([df['high'] - df['low'], (df['high'] - prev).abs(), (df['low'] - prev).abs()], axis=1).max(axis=1)
    tr.iloc[0] = df['high'].iloc[0] - df['low'].iloc[0]
    return tr.rolling(period, min_periods=period).mean()


def sr_bars(tf: str, hours: int = 2) -> int:
    """Số nến của khung `tf` trong `hours` giờ."""
    return int(pd.Timedelta(hours=hours) / pd.Timedelta(KHUNG[tf]))


def levels_sr(bars: pd.DataFrame, tf: str, hours: int = 2) -> tuple[pd.Series, pd.Series]:
    """(hỗ trợ, kháng cự) tại mỗi nến: đáy thấp nhất và đỉnh cao nhất của `hours` giờ gần nhất, gồm cả nến đó."""
    n = sr_bars(tf, hours)
    return bars['low'].astype(float).rolling(n).min(), bars['high'].astype(float).rolling(n).max()


def ema_direction(closes) -> int:
    """+1 nếu EMA20 trên EMA50, −1 nếu dưới, 0 nếu bằng hoặc chưa đủ 60 nến."""
    s = pd.Series(list(closes), dtype='float64')
    if len(s) < 60:
        return 0
    d = float(s.ewm(span=20, adjust=False).mean().iloc[-1] - s.ewm(span=50, adjust=False).mean().iloc[-1])
    return (d > 0) - (d < 0)


def directions(d1, h4, h1) -> dict:
    return {'D1': ema_direction(d1), 'H4': ema_direction(h4), 'H1': ema_direction(h1)}


def _gio(df: pd.DataFrame, i: int) -> str:
    t = df['time'].iloc[i] if 'time' in df else df.index[i]
    return pd.Timestamp(t).strftime('%Y-%m-%d %H:%M')


def _r2(x) -> float | None:
    x = float(x)
    return None if math.isnan(x) or math.isinf(x) else round(x, 2)


def fvg_zones(df: pd.DataFrame, min_size: float, keep: int = 5) -> list[dict]:
    """Khoảng trống giá ba nến còn chưa lấp, cũ trước mới sau; chỉ trả phần CÒN LẠI của mỗi vùng.
    Tăng: đáy nến sau cao hơn đỉnh nến trước của một nến giữa. Giảm: đỉnh nến sau thấp hơn đáy nến trước.
    Giá quay lại tới đâu thì vùng bị cắt tới đó; phần còn lại hẹp hơn min_size thì bỏ. Giờ ghi là giờ mở của nến giữa."""
    h, l = df['high'].to_numpy(dtype=float), df['low'].to_numpy(dtype=float)
    n, out = len(df), []
    # đáy thấp nhất / đỉnh cao nhất từ nến i+2 trở đi, tính một lần từ cuối lên
    sau_thap = np.append(np.minimum.accumulate(l[::-1])[::-1], math.inf)
    sau_cao = np.append(np.maximum.accumulate(h[::-1])[::-1], -math.inf)
    for i in range(1, n - 1):
        if l[i + 1] > h[i - 1]:
            lo, hi, huong = h[i - 1], min(l[i + 1], sau_thap[i + 2]), 'tang'
        elif h[i + 1] < l[i - 1]:
            lo, hi, huong = max(h[i + 1], sau_cao[i + 2]), l[i - 1], 'giam'
        else:
            continue
        if hi - lo >= min_size:
            out.append({'huong': huong, 'thoi_diem_utc': _gio(df, i), 'duoi': _r2(lo), 'tren': _r2(hi)})
    return out[-keep:]


def order_blocks(df: pd.DataFrame, min_move: float, keep: int = 5) -> list[dict]:
    """Khối lệnh chưa bị phá, cũ trước mới sau; vùng là từ đáy tới đỉnh của nến khối lệnh.
    Tăng: nến giảm ngay trước một nến tăng, và trong ba nến sau nó có nến đóng cao hơn đỉnh của nó ít nhất min_move.
    Hết hiệu lực khi về sau có nến ĐÓNG dưới đáy vùng. Giảm thì ngược lại."""
    o, h, l, c = (df[k].to_numpy(dtype=float) for k in ('open', 'high', 'low', 'close'))
    n, out = len(df), []
    for i in range(n - 1):
        if c[i] < o[i] and c[i + 1] > o[i + 1]:
            huong, cham = 'tang', [j for j in range(i + 1, min(i + 4, n)) if c[j] >= h[i] + min_move]
        elif c[i] > o[i] and c[i + 1] < o[i + 1]:
            huong, cham = 'giam', [j for j in range(i + 1, min(i + 4, n)) if c[j] <= l[i] - min_move]
        else:
            continue
        if not cham:
            continue
        sau = slice(cham[0] + 1, n)
        if huong == 'tang':
            pha, cham_lai = bool((c[sau] < l[i]).any()), bool((l[sau] <= h[i]).any())
        else:
            pha, cham_lai = bool((c[sau] > h[i]).any()), bool((h[sau] >= l[i]).any())
        if not pha:
            out.append({'huong': huong, 'thoi_diem_utc': _gio(df, i), 'duoi': _r2(l[i]), 'tren': _r2(h[i]), 'da_cham_lai': cham_lai})
    return out[-keep:]


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def _da_dong(luc: pd.DatetimeIndex, gia_tri: pd.Series, dai: str) -> np.ndarray:
    """Giá trị của nến khung lớn ĐÃ ĐÓNG gần nhất tại mỗi thời điểm `luc`; NaN nếu chưa có."""
    hi = pd.DataFrame({'t': gia_tri.index + pd.Timedelta(dai), 'v': gia_tri.to_numpy(dtype=float)}).sort_values('t')
    return pd.merge_asof(pd.DataFrame({'t': luc}), hi, on='t', direction='backward')['v'].to_numpy()


def snapshot(bars: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame, d1: pd.DataFrame, tf: str = 'M5') -> dict:
    """Số đọc chỉ báo tại nến ĐÃ ĐÓNG cuối cùng của khung `tf`. Hướng từng khung, tính trên nến khung lớn đã đóng:
    H1 và H4 là EMA20 so với EMA50, D1 là giá đóng so với EMA200 (cần đủ 600 nến ngày). `trend` của bản chia sẻ là
    định nghĩa trung tính "cả ba khung cùng chiều" (khác bộ lọc riêng của bot chủ dự án), 0 nếu lệch nhau."""
    close = bars['close'].astype(float)
    mid, sd = close.rolling(20).mean().iloc[-1], close.rolling(20).std(ddof=0).iloc[-1]
    ht, kc = levels_sr(bars, tf)
    luc = bars.index[-1:] + pd.Timedelta(KHUNG[tf])
    phan = []
    for df, dai in ((h1, '1h'), (h4, '4h')):
        c = df['close'].astype(float)
        phan.append(_da_dong(luc, np.sign(_ema(c, 20) - _ema(c, 50)), dai))
    c = d1['close'].astype(float)
    phan.append(_da_dong(luc, np.sign(c - _ema(c, 200).where(np.arange(len(c)) >= 600)), '1D'))
    h1d, h4d, d1d = (int(np.nan_to_num(x, nan=0.0)[0]) for x in phan)
    xu = h1d if h1d != 0 and h1d == h4d == d1d else 0
    return {'H1': h1d, 'H4': h4d, 'D1': d1d, 'trend': xu, 'close': float(close.iloc[-1]), 'ema20': float(_ema(close, 20).iloc[-1]),
            'upper': float(mid + 2 * sd), 'mid': float(mid), 'lower': float(mid - 2 * sd),
            'support': float(ht.iloc[-1]), 'resistance': float(kc.iloc[-1]), 'atr': float(atr_sma(bars).iloc[-1])}


R = SimpleNamespace(atr_sma=atr_sma, levels_sr=levels_sr, sr_bars=sr_bars, snapshot=snapshot, TIMEFRAMES=KHUNG, KINDS=())
RT = SimpleNamespace(directions=directions, ema_direction=ema_direction)
SN = SimpleNamespace(fvg_zones=fvg_zones, order_blocks=order_blocks)
