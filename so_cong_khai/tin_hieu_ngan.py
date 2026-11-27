"""Quét phá vỡ và hồi về EMA trên M5, M15, M30 bằng nến đã đóng."""
from __future__ import annotations

import math
from bisect import bisect_left
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import da_ma, gia, song


KHUNG = {'M5': 5, 'M15': 15, 'M30': 30}
HAN_GIAY = 120
TUOI_GIA = 30
MAU = 240
PHIEN_BAN = 'ngan-1'
LOAI = {'pha_vo': 'Phá vỡ', 'hoi_ema': 'Hồi về EMA'}
PHIEN_NGHIEN_CUU = 'ngan-2'
UNG_VIEN = {
    f'{loc}-{rr:g}': (loc, rr, gioi_han_spread)
    for loc, gioi_han_spread in (('goc', .15), ('dong_thuan', .10), ('hoi_sau', .10), ('quet_nguoc', .08))
    for rr in (.35, .50, .70, 1.5)
}
TRANG_THAI = {
    'thieu_nen': 'Chưa đủ nến đã đóng',
    'cho_dieu_kien': 'Chưa có thiết lập',
    'qua_han': 'Nến xác nhận đã quá hạn',
    'gia_cu': 'Chưa có giá MT5 mới',
    'tin_manh': 'Tạm dừng quanh tin USD mạnh',
    'gia_di_xa': 'Giá đã rời vùng xác nhận',
    'spread': 'Spread vượt giới hạn',
    'muc_gia': 'Khoảng dừng lỗ không phù hợp',
    'dat': 'Đạt bộ lọc',
}


def _ema(gia_dong, n):
    """EMA có cửa sổ khởi tạo cố định để cùng nến cho cùng số khi live và replay."""
    so = 4 * n
    v = gia_dong.to_numpy()
    kq = np.full(len(v), np.nan)
    if len(v) >= so:
        alpha = 2 / (n + 1)
        w = (1 - alpha) ** np.arange(so)
        w[:-1] *= alpha
        kq[so - 1:] = np.convolve(v, w, mode='valid')
    return pd.Series(kq, index=gia_dong.index)


def _ohlc(b):
    x = b[['open', 'high', 'low', 'close']].astype(float)
    if not x.index.is_monotonic_increasing or x.index.has_duplicates or x.index.tz is None:
        raise ValueError('Nến tín hiệu phải có giờ UTC, tăng dần và không trùng.')
    o, h, l, c = (x[k] for k in x.columns)
    return x.where(np.isfinite(x).all(axis=1) & (x > 0).all(axis=1) & (h >= x[['open', 'low', 'close']].max(axis=1))
                   & (l <= np.minimum(o, c)), np.nan)


def dieu_kien(bars: pd.DataFrame, h1: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Cùng công thức cho lịch sử và live. Chỉ ghép H1 đã đóng tại giờ đóng nến tín hiệu."""
    phut = KHUNG[tf]
    x = _ohlc(bars)
    o, h, l, c = (x[k] for k in x.columns)
    c1 = c.shift()
    e20, e50 = _ema(c, 20), _ema(c, 50)
    atr = pd.concat([h - l, (h - c1).abs(), (l - c1).abs()], axis=1).max(axis=1, skipna=False).rolling(14).mean()
    dinh, day = h.shift().rolling(12).max(), l.shift().rolling(12).min()
    t = x.index + pd.Timedelta(minutes=phut)
    ch = _ohlc(h1)['close']
    huong_h1 = (_ema(ch, 20) - _ema(ch, 50)).where(ch.notna())
    huong_h1.index += pd.Timedelta(hours=1)
    h1_da_dong = huong_h1.reindex(t, method='ffill', tolerance=pd.Timedelta(hours=2)).to_numpy()
    lien = x.index.to_series().diff().eq(pd.Timedelta(minutes=phut))
    chung = lien & lien.shift(fill_value=False) & (atr > 0) & ((c - o).abs() >= .22 * atr) & ((h - l) <= 2.2 * atr)
    mua = chung & (h1_da_dong > 0) & (e20 > e50) & (e20 > e20.shift(3)) & (c > o) & (c - l >= .65 * (h - l))
    ban = chung & (h1_da_dong < 0) & (e20 < e50) & (e20 < e20.shift(3)) & (c < o) & (h - c >= .65 * (h - l))
    pv_mua = mua & (c >= dinh + .06 * atr) & (c - dinh <= .65 * atr)
    pv_ban = ban & (c <= day - .06 * atr) & (day - c <= .65 * atr)
    ema = e20.shift()
    ema_mua = mua & (l <= ema) & (l >= ema - .55 * atr) & (c > ema) & (c > c1) & (c - ema <= 1.10 * atr)
    ema_ban = ban & (h >= ema) & (h <= ema + .55 * atr) & (c < ema) & (c < c1) & (ema - c <= 1.10 * atr)
    phia = np.select([pv_mua | ema_mua, pv_ban | ema_ban], [1, -1], default=0)
    bien_do = h - l
    dong_thuan = (phia * h1_da_dong >= .5 * atr) & (phia * (e20 - e50) >= .4 * atr) & ((c - o).abs() >= .4 * atr)
    hoi_sau = np.select([mua & (l <= ema - .15 * atr) & (l >= ema - .9 * atr) & (c > ema + .04 * atr) & (c > c1),
                         ban & (h >= ema + .15 * atr) & (h <= ema + .9 * atr) & (c < ema - .04 * atr) & (c < c1)], [1, -1], default=0)
    quet_nguoc = np.select([
        chung & (h1_da_dong > 0) & (l < day - .04 * atr) & (c > day + .06 * atr) & (c > o) & ((c - l) >= .7 * bien_do),
        chung & (h1_da_dong < 0) & (h > dinh + .04 * atr) & (c < dinh - .06 * atr) & (c < o) & ((h - c) >= .7 * bien_do),
    ], [1, -1], default=0)
    return pd.DataFrame({
        'close': c, 'atr': atr, 'phia': phia,
        'loai': np.select([pv_mua | pv_ban, ema_mua | ema_ban], ['pha_vo', 'hoi_ema'], default=''),
        'day': np.minimum(l, l.shift()), 'dinh': np.maximum(h, h.shift()),
        'dong_thuan': dong_thuan, 'hoi_sau': hoi_sau, 'quet_nguoc': quet_nguoc,
    }, index=x.index)


def loc_ung_vien(d: pd.DataFrame, ung_vien: str) -> pd.DataFrame:
    """Bộ lọc ứng viên dùng chung ở nghiên cứu hồi cứu và tiến cứu."""
    loc, _, _ = UNG_VIEN[ung_vien]
    if loc == 'goc':
        return d
    if loc == 'dong_thuan':
        return d[d['dong_thuan']]
    return d.assign(phia=d[loc], loai=loc)


def muc_gia(r, bid: float, ask: float, buoc_gia: float, so_le: int, *, dich_r: float = 1.5, spread_atr: float = .15) -> tuple[str, dict]:
    """Dùng giá có thể giao dịch (Ask khi mua, Bid khi bán) và bước giá của hợp đồng."""
    if not all(math.isfinite(x) and x > 0 for x in (bid, ask, buoc_gia)) or ask < bid:
        return 'gia_cu', {}
    if abs(bid - r.close) > .25 * r.atr:
        return 'gia_di_xa', {}
    if ask - bid > spread_atr * r.atr:
        return 'spread', {}

    def lam(x, len_tren):
        q = x / buoc_gia
        return round((math.ceil(q - 1e-8) if len_tren else math.floor(q + 1e-8)) * buoc_gia, so_le)

    mua = r.phia > 0
    vao = lam(ask if mua else bid, mua)
    sl = lam(min(r.day - .12 * r.atr, vao - .65 * r.atr) if mua else max(r.dinh + .12 * r.atr, vao + .65 * r.atr), not mua)
    rui_ro = abs(vao - sl)
    tp = lam(vao + r.phia * dich_r * rui_ro, mua)
    if min(vao, sl, tp) <= 0 or not 0 < rui_ro <= 2.5 * r.atr or (mua and sl >= bid) or (not mua and sl <= ask):
        return 'muc_gia', {}
    if ask - bid > .15 * rui_ro:
        return 'spread', {}
    return 'dat', {'vao': vao, 'sl': sl, 'tp': tp, 'rr': round(abs(tp - vao) / rui_ro, 2)}


def quet(fr: dict, now: datetime, tick, *, buoc_gia: float, so_le: int, gan_tin: bool = False,
         ung_vien: dict[str, str] | None = None) -> list[dict]:
    """Mỗi khung có một trạng thái; chỉ trả mức giá cho thiết lập còn hiệu lực."""
    h1 = fr.get('H1')
    ds = []
    tick_ms = int(getattr(tick, 'time_msc', 0) or getattr(tick, 'time', 0) * 1000)
    for tf, phut in KHUNG.items():
        ma_uv = ung_vien.get(tf) if ung_vien is not None else None
        if ung_vien is not None and ma_uv is None:
            continue
        a = {'tf': tf, 'trang_thai': 'thieu_nen'}
        ds.append(a)
        if ma_uv:
            a['ung_vien'] = ma_uv
        b = fr.get(tf)
        if b is None or h1 is None:
            continue
        b = b[b.index + pd.Timedelta(minutes=phut) <= now].iloc[-MAU:]
        h = h1[h1.index + pd.Timedelta(hours=1) <= now].iloc[-MAU:]
        if len(b) < 200 or len(h) < 200:
            continue
        dong = b.index[-1] + pd.Timedelta(minutes=phut)
        a.update(dong=dong.isoformat(), het=(dong + pd.Timedelta(seconds=HAN_GIAY)).isoformat())
        d = dieu_kien(b, h, tf)
        d = loc_ung_vien(d, ma_uv) if ma_uv else d
        if d.empty or d.index[-1] != b.index[-1] or not d.iloc[-1].phia:
            a['trang_thai'] = 'cho_dieu_kien'
            continue
        r = d.iloc[-1]
        a.update(loai=r.loai, huong='MUA' if r.phia > 0 else 'BÁN', moc=float(r.close), atr=float(r.atr), day=float(r.day), dinh=float(r.dinh))
        if (now - dong).total_seconds() > HAN_GIAY:
            a['trang_thai'] = 'qua_han'
        elif gan_tin:
            a['trang_thai'] = 'tin_manh'
        elif tick is None or tick_ms / 1000 < dong.timestamp() or not -5 <= now.timestamp() - tick_ms / 1000 <= TUOI_GIA:
            a['trang_thai'] = 'gia_cu'
        else:
            _, dich_r, spread_atr = UNG_VIEN[ma_uv] if ma_uv else UNG_VIEN['goc-1.5']
            a['trang_thai'], gia_dat = muc_gia(r, float(tick.bid), float(tick.ask), buoc_gia, so_le,
                                              dich_r=dich_r, spread_atr=spread_atr)
            a.update(gia_dat)
    return ds


def doc(cfg: dict, ma: str, now: datetime | None = None, *, khung: str | None = None, ung_vien: dict[str, str] | None = None) -> dict:
    """Lấy nến đã đóng từ terminal đang nối, dùng chung phiên đọc của webapp."""
    ma = ma or da_ma.ma_vang(cfg)
    if len(ma) > 64 or not ma.isprintable():
        raise ValueError('Mã không hợp lệ.')
    g = cfg.get('gia') or {}
    mt5 = da_ma._mt5(g)
    ket_qua = {'ma': ma, 'luc': (now or datetime.now(timezone.utc)).isoformat(), 'phien_ban': PHIEN_BAN, 'ds': []}
    if mt5 is None:
        return {**ket_qua, 'ly_do': song.ly_do() or 'Chưa nối MT5'}
    with song._khoa:
        s = mt5.symbol_info(ma)
        if not s or not getattr(s, 'visible', False):
            raise ValueError('Mã chưa có trong Market Watch.')
        if getattr(s, 'custom', False) or getattr(s, 'trade_calc_mode', -1) not in (0, 2, 3, 4, 5):
            return {**ket_qua, 'ly_do': 'Bộ quét chỉ dùng mã Forex và CFD từ MT5.'}
        fr = {}
        for tf in (*(KHUNG if khung is None else (khung,)), 'H1'):
            try:
                fr[tf] = da_ma._nen(mt5, ma, tf, MAU)
            except RuntimeError:
                continue
        tick = mt5.symbol_info_tick(ma)
        tk = mt5.account_info() if hasattr(mt5, 'account_info') else None
    try:
        tin, phu_toi = gia.tin_usd(g) if g.get('lich_tin') else ([], None)
    except (OSError, ValueError, RuntimeError):
        tin, phu_toi = [], None
    now = now or datetime.now(timezone.utc)
    rong = timedelta(minutes=15)
    vitri = bisect_left(tin, now - rong)
    gan_tin = vitri < len(tin) and tin[vitri] <= now + rong
    buoc = float(getattr(s, 'trade_tick_size', 0) or s.point)
    tham_so = {'buoc_gia': buoc, 'so_le': int(s.digits), 'gan_tin': gan_tin}
    ds = quet(fr, now, tick, **tham_so)
    return {**ket_qua, 'luc': now.isoformat(), 'nguon': 'mt5', 'may_chu': str(getattr(tk, 'server', '') or ''),
            'tien_tk': str(getattr(tk, 'currency', '') or ''), 'buoc_gia': buoc, 'gia_tick': float(getattr(s, 'trade_tick_value_loss', 0) or 0),
            'bid': float(tick.bid) if tick else None, 'ask': float(tick.ask) if tick else None,
            'tick_ms': int(getattr(tick, 'time_msc', 0) or getattr(tick, 'time', 0) * 1000),
            'so_le': int(s.digits), 'lich_tin': bool(phu_toi and phu_toi >= now),
            'ds': ds if khung is None else [a for a in ds if a['tf'] == khung],
            **({'nghien_cuu': quet(fr, now, tick, ung_vien=ung_vien, **tham_so)} if ung_vien else {})}
