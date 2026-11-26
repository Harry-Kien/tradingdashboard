"""Nến lùi về đầu năm cho biểu đồ.

Biểu đồ nạp 900 nến gần nhất mỗi 5 giây để nhẹ. Phần này trả MỘT LẦN toàn bộ nến đã đóng từ ngày 1 tháng 1 của năm đang xem
(tối đa TOI_DA nến mỗi khung), kèm EMA20, EMA50, Bollinger và RSI tính trên chính chuỗi đó; trang ghép phần cũ vào trước phần đang chạy.

- Vàng: ghép từ tệp nến 1 phút nhiều năm của dự án và kho nến của webapp (cùng nguồn với phần "học từ dữ liệu nhiều năm").
- Mã khác: đọc từ MT5 demo đang mở (chỉ đọc nến của mã đang hiện trong Market Watch; không chọn mã, không đặt lệnh). MT5 có bao nhiêu
  lịch sử thì trả bấy nhiêu; khóa `tu` cho biết nến đầu tiên thật sự có.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pandas as pd

from . import da_ma, gia, hoc, song

TOI_DA = 40_000            # số nến tối đa mỗi khung; M5 của một mã chạy 24/7 vì thế chỉ lùi được khoảng 139 ngày
NHO_GIAY = 600             # nến cũ của mã khác vàng được nhớ chừng này giây (phần mới do biểu đồ tự nạp mỗi 5 giây)
_nho: dict = {}


def _vang(g: dict, tu: datetime) -> dict:
    """Mọi khung của vàng từ `tu`, ghép từ nến 1 phút. Nhớ theo tệp nguồn nên chỉ đọc lại khi tệp đổi."""
    key = ('vang', tu.year, gia._chu_ky(g))
    if _nho.get('vang_key') != key:
        m1 = hoc._m1_dai(g, tu.year)
        m1 = m1[m1.index >= tu]
        het = m1.index[-1] + timedelta(minutes=1)
        fr = {'M1': m1[m1.index + timedelta(minutes=1) <= het]}
        for tf, rule in gia._QUY.items():
            b = m1.resample(rule, origin='epoch', label='left', closed='left').agg(gia._OHLC).dropna()
            fr[tf] = b[b.index + timedelta(minutes=gia.KHUNG[tf]) <= het]
        d1 = m1.resample('1D').agg(gia._OHLC).dropna()
        fr['D1'] = d1[(d1.index + timedelta(days=1) <= het) & (d1.index.day_of_week != 6)]
        _nho.update(vang_key=key, vang=fr)
    return _nho['vang']


def _ma_khac(cfg: dict, ma: str, tf: str, tu: datetime, now: datetime) -> tuple[pd.DataFrame, int]:
    key, luc = ('ma', ma, tf, tu.year), time.monotonic()
    cu = _nho.get(key)
    if cu and luc - cu[0] < NHO_GIAY:
        return cu[1], cu[2]
    g = cfg['gia']
    mt5 = da_ma._mt5(g)
    if mt5 is None:
        raise ValueError(f'chưa có giá trực tiếp từ MT5 ({song.ly_do() or "chưa nối"}); nến cũ của mã ngoài vàng chỉ đọc được khi MT5 demo đang mở')
    n = max(100, min(TOI_DA, int((now - tu).total_seconds() // (gia.KHUNG[tf] * 60)) + 5))
    with song._khoa:
        hien = da_ma._hien(mt5)
        if ma not in hien:
            raise ValueError(f'mã {ma} không có trong Market Watch của MT5')
        d, bars = int(hien[ma].digits), None
        while bars is None:
            try:
                bars = da_ma._nen(mt5, ma, tf, n)
            except RuntimeError:                                   # MT5 chưa có đủ chừng đó nến: xin ít hơn
                if n <= 1000:
                    raise
                n //= 2
    _nho[key] = (luc, bars, d)
    return bars, d


def goi(cfg: dict, ma: str = '', tf: str = 'M15', now: datetime | None = None) -> dict:
    """Nến đã đóng của một khung từ đầu năm tới giờ, cũ trước mới sau, cùng dạng với phần nến của /api/gia."""
    if tf not in gia.KHUNG:
        raise ValueError(f'khung không hỗ trợ: {tf}')
    now = now or datetime.now(timezone.utc)
    tu = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    if tf == 'M1':                                                 # M1 rất dày: chỉ lùi 20 ngày (khoảng 29.000 nến)
        tu = max(tu, now - timedelta(days=20))
    vang = not ma or ma == da_ma.ma_vang(cfg)
    if vang:
        gia.can_gia(cfg['gia'])
    if vang and gia.chia_se_song(cfg['gia']):     # bản chia sẻ không có kho nến 1 phút nhiều năm: lấy thẳng từ MT5 như mọi mã
        ma, vang = da_ma.ma_vang(cfg), False
    if vang:
        bars, d = _vang(cfg['gia'], datetime(now.year, 1, 1, tzinfo=timezone.utc))[tf], 2
        if tf == 'M1':                                             # chỉ báo chỉ tính trên phần cần (kèm 1 ngày khởi động), không trên cả năm
            bars = bars[bars.index >= tu - timedelta(days=1)]
    else:
        bars, d = _ma_khac(cfg, ma, tf, tu, now)
    close = bars['close']
    mid, sd = close.rolling(20).mean(), close.rolling(20).std(ddof=0)
    over = {'ema20': close.ewm(span=20, adjust=False, min_periods=20).mean(), 'ema50': close.ewm(span=50, adjust=False, min_periods=50).mean(),
            'bb_tren': mid + 2 * sd, 'bb_duoi': mid - 2 * sd, 'rsi': gia.rsi_wilder(close)}
    lt = da_ma._lam_tron
    try:                                                           # chỉ báo thêm, cùng công thức với /api/gia (chi_bao_them.py), tính trên cả chuỗi
        from . import chi_bao_them                                 # noqa: PLC0415
        them = {k: v for k, v in chi_bao_them.tinh(bars, len(bars), lt, d, gia.KHUNG[tf] * 60).items() if isinstance(v, list) and len(v) == len(bars)
                and k != 'ichi_sau'}
    except Exception:                                              # noqa: BLE001 - thiếu chỉ báo thêm thì vẫn trả nến
        them = {}
    chon = bars.index >= tu
    bars, over = bars[chon], {k: v[chon] for k, v in over.items()}
    them = {k: [x for x, m in zip(v, chon) if m] for k, v in them.items()}
    cat = len(bars) >= TOI_DA                                      # chạm trần thì phần đầu năm đã bị cắt bớt
    if cat:
        bars, over = bars.iloc[-TOI_DA:], {k: v.iloc[-TOI_DA:] for k, v in over.items()}
        them = {k: v[-TOI_DA:] for k, v in them.items()}
    return {'tf': tf, 'ma': '' if vang else ma, 'nam': now.year, 'so_nen': len(bars), 'cat_bot': cat,
            'tu': bars.index[0].isoformat() if len(bars) else None,
            'candles': [[gia._giay(t), lt(o, d), lt(h, d), lt(l, d), lt(c, d)] for t, o, h, l, c in
                        zip(bars.index, bars['open'], bars['high'], bars['low'], bars['close'])],
            **{k: [lt(x, 2 if k == 'rsi' else d) for x in v.tolist()] for k, v in over.items()}, **them}
