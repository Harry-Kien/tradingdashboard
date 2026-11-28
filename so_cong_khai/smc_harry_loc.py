"""Ứng viên Harry SMC dùng chung cho hồi cứu và theo dõi tick MT5."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import smc_harry as H, tin_hieu_ngan as T

PHIEN = 'harry-smc-loc-1'
DICH = (.40, .55, .70, .85, 1.0, 1.25)
LOC = ('cau_truc', 'cau_truc_manh', 'rut_chan', 'rut_chan_manh', 'hop_luu', 'hop_luu_manh')
SPREAD_ATR = .10
PHI_LOT = 28.
PHI_STRESS_LOT = 53.
TEP_KHOA = 'harry-smc-loc-khoa.json'


def dau_nguon() -> dict[str, str]:
    paths = [Path(__file__), *(Path(m.__file__) for m in (H, H.CT, H.PP, T))]
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def nap_khoa(out: Path) -> dict:
    saved = json.loads((out / TEP_KHOA).read_text(encoding='utf-8'))
    if saved['phien'] != PHIEN or saved['nguon'] != dau_nguon():
        raise ValueError('Bản khóa Harry SMC khác phiên bản mã đang chạy.')
    for tf, row in saved['chon'].items():
        if tf not in T.KHUNG or row['loc'] not in LOC or row['tp_r'] not in DICH:
            raise ValueError('Bản khóa Harry SMC có cấu hình ngoài tập ứng viên.')
    return saved


def ung_vien(fr: dict, tf: str, context: tuple) -> pd.DataFrame:
    """Tìm tiếp diễn phá cấu trúc hoặc rút chân sau khi chạm FVG/iFVG H1 đã xác nhận."""
    h1_dir, h4_dir, adx, times, book = context
    b = fr[tf]
    d = T.dieu_kien(b, fr['H1'], tf)
    o, h, l, c = (b[k].to_numpy(float) for k in ('open', 'high', 'low', 'close'))
    atr = d['atr'].to_numpy()
    step = T.KHUNG[tf] * 60
    opened = b.index.as_unit('s').asi8
    closed = b.index + pd.Timedelta(seconds=step)
    h1 = h1_dir.reindex(closed, method='ffill', tolerance=pd.Timedelta(hours=2)).to_numpy()
    h4 = h4_dir.reindex(closed, method='ffill', tolerance=pd.Timedelta(hours=8)).to_numpy()
    a4 = adx.reindex(closed, method='ffill', tolerance=pd.Timedelta(hours=8)).to_numpy()
    session = (closed.hour >= 7) & (closed.hour < 15)  # UTC. Kỳ nắm giữ 12 nến kết thúc trước rollover của hợp đồng vàng.
    side = np.sign(np.nan_to_num(h1))
    base = session & (side * h4 > 0) & np.isfinite(atr) & (atr > 0) & (h > l)
    not_gap = np.r_[False, False, opened[2:] - opened[:-2] == 2 * step] if len(b) >= 2 else np.zeros(len(b), bool)
    body = side * (c - o)
    valid = base & not_gap & (body >= .2 * atr) & (h - l <= 2.5 * atr)
    struct = np.zeros(len(b), dtype=bool)
    for _, i, level, s, _ in H.PP._pha_cau_truc(h, l, c)[0]:
        struct[i] = s == side[i] and 0 <= s * (c[i] - level) <= .65 * atr[i]
    prev_l = b['low'].shift().rolling(3).min().to_numpy()
    prev_h = b['high'].shift().rolling(3).max().to_numpy()
    swept = np.where(side > 0, (l < prev_l) & (c >= prev_l + .06 * atr) & (c - l >= .67 * (h - l)),
                     (h > prev_h) & (c <= prev_h - .06 * atr) & (h - c >= .67 * (h - l)))
    rows = []
    for i in np.flatnonzero(valid & (struct | swept)):
        t = opened[i] + step
        j = times.searchsorted(t, side='right') - 1
        if j < 0 or t - times[j] > 7200:
            continue
        s = side[i]
        recent = slice(max(0, i - H.CHAM_NEN + 1), i + 1)
        for z in sorted(book[j][1], key=lambda z: (abs(c[i] - (z.duoi + z.tren) / 2), -z.tu)):
            edge = z.tren if s > 0 else z.duoi
            if z.chieu != s or not 0 <= s * (c[i] - edge) <= 1.3 * atr[i]:
                continue
            touch = np.flatnonzero((opened[recent] >= max(z.tu, t - H.CHAM_NEN * step))
                                   & (l[recent] <= z.tren) & (h[recent] >= z.duoi))
            if not len(touch):
                continue
            begin = recent.start + touch[-1]
            if swept[i] and begin != i and not struct[i]:
                continue  # Rút chân phải chạm vùng ngay trên nến quét.
            strong = a4[i] >= 23 and body[i] >= .32 * atr[i] and s * h4[i] >= .4 * atr[i]
            rows.append((b.index[i], c[i], atr[i], int(s), z.loai, l[begin:i + 1].min(), h[begin:i + 1].max(),
                         bool(struct[i]), bool(swept[i] and begin == i), bool(strong)))
            break
    return pd.DataFrame(rows, columns=['luc', 'close', 'atr', 'phia', 'loai', 'day', 'dinh', 'cau_truc', 'rut_chan', 'manh']).set_index('luc')


def loc(d: pd.DataFrame, ten: str) -> pd.DataFrame:
    base, _, _ = ten.partition('_manh')
    hit = d['cau_truc'] | d['rut_chan'] if base == 'hop_luu' else d[base]
    return d.loc[(hit & d['manh'] if ten.endswith('_manh') else hit).to_numpy(dtype=bool)]
