"""Chỉ báo kỹ thuật thêm cho biểu đồ, theo công thức chuẩn (cùng tham số mặc định với TradingView), chỉ trên nến ĐÃ ĐÓNG.

- EMA200.
- MACD(12, 26, 9): đường MACD = EMA12 − EMA26, đường tín hiệu = EMA9 của MACD, cột = MACD − tín hiệu.
- Stochastic chậm (14, 3, 3): %K thô = 100·(đóng − đáy 14)/(đỉnh 14 − đáy 14); %K = SMA3 của %K thô; %D = SMA3 của %K.
- ATR(14) kiểu Wilder (RMA), cùng cách với ATR của MT5 và TradingView.
- SuperTrend(10, 3): dải trên/dưới = (đỉnh+đáy)/2 ± 3·ATR(10) Wilder, dải "chốt" chỉ được nới khi giá đóng phá qua; đường đổi phía khi giá đóng
  vượt dải. Trả giá trị đường và chiều (+1 tăng, −1 giảm).
- Ichimoku (9, 26, 52): Tenkan = (đỉnh 9 + đáy 9)/2; Kijun = (đỉnh 26 + đáy 26)/2; Senkou A = (Tenkan + Kijun)/2 và Senkou B = (đỉnh 52 + đáy 52)/2,
  cả hai vẽ lùi về sau 26 nến (mây ở nến i tính từ nến i − 26), kèm 26 nến mây phía trước nến cuối; Chikou = giá đóng vẽ sớm 26 nến.
- Điểm xoay chiều (pivot) cổ điển theo ngày UTC đã đóng gần nhất: P = (H + L + C)/3, R1 = 2P − L, S1 = 2P − H, R2 = P + (H − L), S2 = P − (H − L),
  R3 = H + 2(P − L), S3 = L − 2(H − P).
Hàm thuần: nhận DataFrame nến (open, high, low, close; chỉ số là giờ mở nến UTC), không đọc MT5. Không có khối lượng nên không có VWAP."""
from __future__ import annotations

import numpy as np
import pandas as pd

AM = 400                                  # số nến thêm phía trước phần hiển thị để các chỉ báo dài (EMA200, Ichimoku 52) kịp ổn định
ICHI = (9, 26, 52)


def rma(x: pd.Series, n: int) -> pd.Series:
    """Trung bình trượt kiểu Wilder (hệ số 1/n), như RMA của TradingView."""
    return x.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def atr(b: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c0 = b['high'].astype(float), b['low'].astype(float), b['close'].astype(float).shift(1)
    tr = pd.concat([h - l, (h - c0).abs(), (l - c0).abs()], axis=1).max(axis=1)
    tr.iloc[0] = float(h.iloc[0] - l.iloc[0])
    return rma(tr, n)


def macd(c: pd.Series, nhanh: int = 12, cham: int = 26, tin: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    m = c.ewm(span=nhanh, adjust=False, min_periods=nhanh).mean() - c.ewm(span=cham, adjust=False, min_periods=cham).mean()
    s = m.ewm(span=tin, adjust=False, min_periods=tin).mean()
    return m, s, m - s


def stoch(b: pd.DataFrame, n: int = 14, k: int = 3, d: int = 3) -> tuple[pd.Series, pd.Series]:
    hh, ll = b['high'].rolling(n).max(), b['low'].rolling(n).min()
    tho = 100 * (b['close'] - ll) / (hh - ll).replace(0, np.nan)
    kk = tho.rolling(k).mean()
    return kk, kk.rolling(d).mean()


def supertrend(b: pd.DataFrame, n: int = 10, he_so: float = 3.0) -> tuple[pd.Series, pd.Series]:
    """(giá trị đường, chiều) của SuperTrend; chiều +1 khi đường nằm dưới giá (xu hướng tăng), −1 khi nằm trên."""
    h, l, c = (b[x].to_numpy(dtype=float) for x in ('high', 'low', 'close'))
    a = atr(b, n).to_numpy()
    giua = (h + l) / 2
    tren_co, duoi_co = giua + he_so * a, giua - he_so * a
    m = len(c)
    tren, duoi, line, chieu = (np.full(m, np.nan) for _ in range(4))
    for i in range(m):
        if np.isnan(a[i]):
            continue
        if i == 0 or np.isnan(tren[i - 1]):
            tren[i], duoi[i], chieu[i] = tren_co[i], duoi_co[i], 1.0
        else:
            tren[i] = tren_co[i] if (tren_co[i] < tren[i - 1] or c[i - 1] > tren[i - 1]) else tren[i - 1]
            duoi[i] = duoi_co[i] if (duoi_co[i] > duoi[i - 1] or c[i - 1] < duoi[i - 1]) else duoi[i - 1]
            if chieu[i - 1] < 0:
                chieu[i] = 1.0 if c[i] > tren[i] else -1.0
            else:
                chieu[i] = -1.0 if c[i] < duoi[i] else 1.0
        line[i] = duoi[i] if chieu[i] > 0 else tren[i]
    return pd.Series(line, index=b.index), pd.Series(chieu, index=b.index)


def ichimoku(b: pd.DataFrame, a: int = ICHI[0], k: int = ICHI[1], s: int = ICHI[2]) -> dict:
    """Các đường của Ichimoku theo đúng nến (đã dịch 26 nến như cách vẽ chuẩn) và mây 26 nến phía trước nến cuối ('a_sau', 'b_sau')."""
    hh = lambda n: b['high'].rolling(n).max()                                    # noqa: E731
    ll = lambda n: b['low'].rolling(n).min()                                     # noqa: E731
    tenkan, kijun = (hh(a) + ll(a)) / 2, (hh(k) + ll(k)) / 2
    sa, sb = (tenkan + kijun) / 2, (hh(s) + ll(s)) / 2
    return {'tenkan': tenkan, 'kijun': kijun, 'span_a': sa.shift(k), 'span_b': sb.shift(k), 'chikou': b['close'].shift(-k),
            'a_sau': sa.iloc[-k:].to_numpy(), 'b_sau': sb.iloc[-k:].to_numpy()}


def pivot_ngay(b: pd.DataFrame) -> dict | None:
    """Pivot cổ điển từ ngày UTC đã đóng gần nhất trước ngày của nến cuối. None khi chưa đủ một ngày trọn."""
    if not len(b):
        return None
    ngay = b.resample('1D').agg({'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    truoc = ngay[ngay.index < b.index[-1].normalize()]
    if not len(truoc):
        return None
    H, L, C = (float(truoc[x].iloc[-1]) for x in ('high', 'low', 'close'))
    P = (H + L + C) / 3
    return {'ngay': truoc.index[-1].strftime('%Y-%m-%d'), 'P': P, 'R1': 2 * P - L, 'S1': 2 * P - H, 'R2': P + (H - L), 'S2': P - (H - L),
            'R3': H + 2 * (P - L), 'S3': L - 2 * (H - P)}


def tron(x, k: int):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if x != x else round(x, k)


def tinh(bars: pd.DataFrame, n: int, lam_tron=tron, so_le: int = 2, buoc_giay: int = 900) -> dict:
    """Các chỉ báo thêm cho `n` nến cuối của `bars`, mỗi chỉ báo một mảng dài đúng `n` (None ở chỗ chưa đủ nến).
    `lam_tron(x, so_le)`: hàm làm tròn của nơi gọi. `buoc_giay`: độ dài một nến (giây), để đặt giờ cho 26 nến mây phía trước."""
    b = bars.iloc[-(n + AM):][['open', 'high', 'low', 'close']].astype(float)
    c = b['close']
    cat = lambda x, k=so_le: [lam_tron(v, k) for v in x.iloc[-n:].tolist()]       # noqa: E731
    m, s, hst = macd(c)
    kk, dd = stoch(b)
    st, chieu = supertrend(b)
    ic = ichimoku(b)
    cuoi = int(pd.Timestamp(b.index[-1]).timestamp())
    out = {'ema200': cat(c.ewm(span=200, adjust=False, min_periods=200).mean()),
           'macd': cat(m, so_le + 1), 'macd_tin': cat(s, so_le + 1), 'macd_cot': cat(hst, so_le + 1),
           'stoch_k': cat(kk, 2), 'stoch_d': cat(dd, 2), 'atr14': cat(atr(b, 14), so_le),
           'st': cat(st), 'st_chieu': [None if v is None else int(v) for v in cat(chieu, 0)],
           **{f'ichi_{k}': cat(ic[k]) for k in ('tenkan', 'kijun', 'span_a', 'span_b', 'chikou')},
           'ichi_sau': [[cuoi + (i + 1) * buoc_giay, lam_tron(a, so_le), lam_tron(bb, so_le)] for i, (a, bb) in enumerate(zip(ic['a_sau'], ic['b_sau']))]}
    pv = pivot_ngay(b)
    out['pivot'] = {k: (v if k == 'ngay' else lam_tron(v, so_le)) for k, v in pv.items()} if pv else None
    return out
