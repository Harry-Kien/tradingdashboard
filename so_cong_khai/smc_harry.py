"""Hai phương pháp miễn phí trên chart, dùng chung quy tắc với bài kiểm hồi cứu."""
from __future__ import annotations

import json
import math
import os
from bisect import bisect_left
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import ban_tin_cau_truc as CT, da_ma, gia, phuong_phap as PP, song, tin_hieu_ngan as T

PHIEN_BAN = 'harry-chart-1'
DICH_R = 1.25
SPREAD_ATR = .10
TUOI_TICK = 15
CHAM_NEN = 12
TEN = {'harry_smc': 'Harry SMC', 'harry_xu_huong': 'Harry Xu hướng'}
QUY_TAC = {
    'harry_smc': 'FVG/iFVG H1 còn hiệu lực, đã chạm vùng, rồi có CHoCH cùng chiều xu hướng H1/H4 trên nến đã đóng.',
    'harry_xu_huong': 'Phá vỡ hoặc hồi EMA đã xác nhận, cùng chiều H4 có ADX14 từ 20 và RSI14 ở vùng động lượng.',
}


def fvg_repo(h1: pd.DataFrame) -> dict[int, tuple[int, float, float]]:
    """Chỉ lấy biên và hướng FVG từ thư viện. Chỉ số là nến thứ ba, khi FVG được biết."""
    os.environ.setdefault('SMC_CREDIT', '0')  # Tránh lỗi mã hóa console Windows khi nhập thư viện.
    from smartmoneyconcepts import smc

    zones = {}
    # Hai nến chồng lấn đủ để ba nến của mọi FVG nằm cùng một khối.
    for start in range(0, len(h1) - 2, 1024):
        f = smc.fvg(h1.iloc[start:start + 1026].reset_index(drop=True), join_consecutive=False)
        for i in np.flatnonzero(f['FVG'].notna().to_numpy()):
            if 0 < i < len(f) - 1:
                zones[start + int(i) + 1] = (int(f['FVG'].iat[i]), float(f['Bottom'].iat[i]), float(f['Top'].iat[i]))
    return zones


def boi_canh(fr: dict) -> tuple:
    """Chụp sổ FVG tại từng lần đóng H1 và tính chỉ báo trên các khung lớn."""
    from ta.trend import ADXIndicator

    h1, h4 = fr['H1'], fr['H4']
    trend = [(T._ema(b['close'], 20) - T._ema(b['close'], 50)).shift(freq=pd.Timedelta(hours=k))
             for b, k in ((h1, 1), (h4, 4))]
    adx = ADXIndicator(h4['high'], h4['low'], h4['close'], window=14).adx().shift(freq=pd.Timedelta(hours=4))
    book = list(CT.phat_vung(h1, fvg_repo(h1)))
    times = np.array([s[0] for s in book], dtype=np.int64)
    return trend[0], trend[1], adx, times, book


def dieu_kien(fr: dict, tf: str, context: tuple | None = None) -> dict[str, pd.DataFrame]:
    """Trả thiết lập cho từng nến. Kết quả tại một mốc chỉ dùng dữ liệu đã đóng đến mốc đó."""
    from ta.momentum import RSIIndicator

    trend_h1, trend_h4, adx_h4, times, book = context if context is not None else boi_canh(fr)
    b = fr[tf]
    d = T.dieu_kien(b, fr['H1'], tf)
    step = T.KHUNG[tf] * 60
    opened = b.index.as_unit('s').asi8
    closed = b.index + pd.Timedelta(seconds=step)
    h1 = trend_h1.reindex(closed, method='ffill', tolerance=pd.Timedelta(hours=2)).to_numpy()
    h4 = trend_h4.reindex(closed, method='ffill', tolerance=pd.Timedelta(hours=8)).to_numpy()
    adx = adx_h4.reindex(closed, method='ffill', tolerance=pd.Timedelta(hours=8)).to_numpy()
    rsi = RSIIndicator(d['close'], window=14).rsi().to_numpy()
    side = d['phia'].to_numpy()
    momentum = np.where(side > 0, (rsi >= 50) & (rsi <= 70), (rsi >= 30) & (rsi <= 50))
    xu_huong = d.assign(phia=np.where((side * h4 > 0) & (adx >= 20) & momentum, side, 0))

    high, low, close = (b[c].to_numpy(dtype=float) for c in ('high', 'low', 'close'))
    atr = d['atr'].to_numpy()
    phia = np.zeros(len(b), dtype=np.int8)
    day, dinh, duoi, tren, moc = (np.full(len(b), np.nan) for _ in range(5))
    loai = np.full(len(b), '', dtype='<U4')
    for _, i, level, direction, kind in PP._pha_cau_truc(high, low, close)[0]:
        if (kind != 'CHoCH' or i < 2 or opened[i] - opened[i - 2] != 2 * step or not (atr[i] > 0)
                or not (direction * h1[i] > 0 and direction * h4[i] > 0)
                or not 0 <= direction * (close[i] - level) <= .35 * atr[i]):
            continue
        t = opened[i] + step
        j = times.searchsorted(t, side='right') - 1
        if j < 0 or t - times[j] > 7200:
            continue
        recent = slice(max(0, i - CHAM_NEN + 1), i + 1)
        zones = sorted(book[j][1], key=lambda z: (abs(close[i] - (z.duoi + z.tren) / 2), -z.tu))
        for z in zones:
            if z.chieu != direction or direction * (close[i] - (z.tren if direction > 0 else z.duoi)) < 0:
                continue
            touch = np.flatnonzero((opened[recent] >= max(z.tu, t - CHAM_NEN * step))
                                   & (low[recent] <= z.tren) & (high[recent] >= z.duoi))
            if not len(touch):
                continue
            start = recent.start + touch[-1]
            phia[i], loai[i], moc[i] = direction, z.loai, level
            day[i], dinh[i] = min(z.duoi, low[start:i + 1].min()), max(z.tren, high[start:i + 1].max())
            duoi[i], tren[i] = z.duoi, z.tren
            break
    smc = d.assign(phia=phia, loai=loai, day=day, dinh=dinh, duoi=duoi, tren=tren, moc=moc)
    return {'harry_smc': smc, 'harry_xu_huong': xu_huong}


def the(ma: str, tf: str, ten: str, *, thong_ke: str = '') -> dict:
    return {'ma': f'{ma}:{tf}', 'ten': f'{ten} · {tf}', 'ten_ngan': ten, 'chip': ma, 'nhom': 'pp', 'khung': tf,
            'co': False, 'hieu_luc': False, 'quan_sat': True, 'kieu': 'Quan sát miễn phí',
            'thong_ke': f'{QUY_TAC[ma]} {thong_ke}'.strip()}


def _tick_ms(tick) -> int:
    return int(getattr(tick, 'time_msc', 0) or getattr(tick, 'time', 0) * 1000)


def _vet_tick(mt5, ma: str, now: datetime, tick_ms: int):
    """Đọc tối đa cửa sổ hiệu lực của nến xác nhận từ cùng phiên MT5."""
    if not tick_ms or not -5 <= now.timestamp() - tick_ms / 1000 <= TUOI_TICK:
        return None
    tu = now - timedelta(seconds=T.HAN_GIAY + 1)
    den = datetime.fromtimestamp(tick_ms / 1000, timezone.utc) + timedelta(seconds=1)
    try:
        with song._khoa:
            if mt5 is not song._tt.get('mt5'):
                return None
            rows = mt5.copy_ticks_range(ma, tu, den, mt5.COPY_TICKS_INFO)
        if rows is not None and len(rows):
            ms, bid, ask = rows['time_msc'], rows['bid'], rows['ask']
            hop_le = (ms <= tick_ms) & np.isfinite(bid) & np.isfinite(ask) & (bid > 0) & (ask >= bid)
            return ms[hop_le], bid[hop_le]
    except (AttributeError, OSError, RuntimeError, ValueError):
        pass  # Mất đoạn tick thì giữ thẻ ở trạng thái chờ xác minh.
    return None


def muc_live(p: dict, r, dong, now, tick, *, buoc: float, so_le: int, stops: float, gan_tin: bool, vet) -> dict:
    if not r.phia:
        return {**p, 'vi_sao': 'Nến vừa đóng chưa xác nhận đủ điều kiện.'}
    het = dong + timedelta(seconds=T.HAN_GIAY)
    if now > het:
        return {**p, 'vi_sao': T.TRANG_THAI['qua_han']}
    if gan_tin:
        return {**p, 'vi_sao': T.TRANG_THAI['tin_manh']}
    if not math.isfinite(buoc) or buoc <= 0 or not math.isfinite(stops) or stops < 0:
        return {**p, 'vi_sao': 'Thiếu thông số bước giá từ MT5.'}
    ms, tu = _tick_ms(tick), int(dong.timestamp() * 1000)
    if ms < tu or not -5 <= now.timestamp() - ms / 1000 <= TUOI_TICK:
        return {**p, 'vi_sao': T.TRANG_THAI['gia_cu']}
    if vet is None:
        return {**p, 'vi_sao': 'Đang chờ lịch sử tick kể từ nến xác nhận.'}
    times, bids = vet
    history = bids[(times >= tu) & (times <= ms)]
    if not len(history):
        return {**p, 'vi_sao': 'Đang chờ lịch sử tick kể từ nến xác nhận.'}
    bid, ask = float(tick.bid), float(tick.ask)
    if max(abs(bid - r.close), np.abs(history - r.close).max()) > .25 * r.atr:
        return {**p, 'vi_sao': 'Đã bỏ lỡ điểm vào vì giá rời vùng xác nhận. Chờ nến xác nhận mới.'}
    tt, x = T.muc_gia(r, bid, ask, buoc, so_le, dich_r=DICH_R, spread_atr=SPREAD_ATR, stops=stops)
    ok = tt == 'dat'
    vung = [float(r.duoi), float(r.tren)] if p['chip'] == 'harry_smc' else None
    ly_do = (f'{r.loai} H1 · CHoCH tại {r.moc:.{so_le}f} trên nến {p["khung"]} đã đóng.' if vung
             else f'{T.LOAI[r.loai]} · H1/H4 đồng hướng, ADX14 và RSI14 đạt bộ lọc.')
    return {**p, 'co': True, 'hieu_luc': ok, 'huong': 'MUA' if r.phia > 0 else 'BAN', 'nen': dong.isoformat(),
            'vao': x.get('vao'), 'sl': x.get('sl'), 'tp': [x['tp']] if ok else [], 'rr': [x['rr']] if ok else [],
            'rui_ro_gia': abs(x['vao'] - x['sl']) if ok else None, 'vung': vung, 'ly_do': ly_do,
            'vi_sao_het': [T.TRANG_THAI[tt]] if not ok else [], 'rt': 'sai_muc' if tt == 'muc_gia' else tt,
            'thuc_thi': {'loai': 'tt', 'tu': dong.isoformat(), 'het': het.isoformat(), 'atr': float(r.atr),
                         'moc': float(r.close), 'cho_tick': True,
                         'ngan': {'day': float(r.day), 'dinh': float(r.dinh), 'buoc': buoc, 'dich_r': DICH_R,
                                  'spread_atr': SPREAD_ATR, 'stops': stops, 'xoa_khi_cho': True, 'khoa_gia_xa': True}}}


def _thong_ke(cfg, ma, out: Path) -> dict:
    if ma != da_ma.ma_vang(cfg) or not ma.upper().startswith('XAUUSD'):
        return {}
    try:
        report = json.loads((out / 'harry-smc.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return report.get('khung', {}) if report.get('phien_ban') == PHIEN_BAN else {}


def vung_theo_doi(context: tuple, tick, now: datetime) -> list[dict]:
    """Vùng H1 gần giá hiện tại để đọc trước khi có xác nhận từ khung nhỏ."""
    ms = _tick_ms(tick)
    if not ms or not -5 <= now.timestamp() - ms / 1000 <= TUOI_TICK:
        return []
    bid, ask = float(tick.bid), float(tick.ask)
    t, zones, atr = context[-1][-1]
    if not (math.isfinite(bid) and math.isfinite(ask) and 0 < bid <= ask and 0 <= now.timestamp() - t <= 7200 and atr > 0):
        return []
    price = (bid + ask) / 2
    nearby = []
    for z in sorted(zones, key=lambda v: (max(v.duoi - price, price - v.tren, 0), -v.tu)):
        if max(z.duoi - price, price - z.tren, 0) > 3 * atr:
            break
        if any(z.duoi < n['tren'] and z.tren > n['duoi'] for n in nearby):
            continue
        nearby.append({'duoi': z.duoi, 'tren': z.tren, 'chieu': z.chieu, 't': z.tu, 'loai': z.loai})
        if len(nearby) == 2:
            break
    return nearby


def doc(cfg: dict, ma: str, khung: tuple[str, ...], out: Path, now: datetime | None = None) -> list[dict]:
    ma = ma or da_ma.ma_vang(cfg)
    stats = _thong_ke(cfg, ma, out)
    cards = {}
    for tf in khung:
        for chip, ten in TEN.items():
            kq = stats.get(tf, {}).get(chip, {}).get('cuoi', {})
            do = 'Chưa có backtest cho mã này.'
            if kq.get('so'):
                do = (f'Kiểm XAUUSD từ 2023: {kq["so"]} lệnh, thắng ròng {kq["thang_pct"]:.2f}%, '
                      f'{kq["r_moi_lenh"]:+.4f}R/lệnh sau chi phí, {kq["r_stress"]:+.4f}R/lệnh khi tăng chi phí. '
                      'Đang theo dõi dưới dạng quan sát.')
            cards[tf, chip] = the(chip, tf, ten, thong_ke=do)
    g = cfg['gia']
    mt5 = da_ma._mt5(g)
    if mt5 is None:
        return [{**p, 'vi_sao': 'Đang chờ kết nối MT5.'} for p in cards.values()]
    fr = {}
    with song._khoa:
        s = mt5.symbol_info(ma)
        if not s or not getattr(s, 'visible', False) or getattr(s, 'custom', False):
            return [{**p, 'vi_sao': 'Mã cần có trong Market Watch MT5.'} for p in cards.values()]
        for tf in (*khung, 'H1', 'H4'):
            try:
                fr[tf] = da_ma._nen(mt5, ma, tf, 360)
            except (RuntimeError, AttributeError):
                continue
        tick = mt5.symbol_info_tick(ma)
    now = now or datetime.now(timezone.utc)
    fr = {tf: CT.da_dong(b, tf, now) for tf, b in fr.items()}
    if min(len(fr.get(tf, ())) for tf in ('H1', 'H4')) < 240:
        return [{**p, 'vi_sao': 'Cần ít nhất 240 nến H1 và H4 đã đóng.'} for p in cards.values()]
    context = boi_canh(fr)
    zones = vung_theo_doi(context, tick, now)
    tin, _ = gia.tin_usd(g) if g.get('lich_tin') else ([], None)
    tin = sorted(tin)
    rong = timedelta(minutes=15)
    point = float(s.point)
    buoc = float(getattr(s, 'trade_tick_size', 0) or point)
    stops = max(0, int(getattr(s, 'trade_stops_level', 0) or 0)) * point
    vet, da_doc_tick = None, False
    j = bisect_left(tin, now - rong)
    for tf in khung:
        if len(fr.get(tf, ())) < 240:
            for chip in TEN:
                cards[tf, chip]['vi_sao'] = f'Cần ít nhất 240 nến {tf} đã đóng.'
            continue
        dong = fr[tf].index[-1] + timedelta(minutes=T.KHUNG[tf])
        i = bisect_left(tin, dong - rong)
        gan_tin = (i < len(tin) and tin[i] <= dong + rong) or (j < len(tin) and tin[j] <= now + rong)
        for chip, d in dieu_kien(fr, tf, context).items():
            r = d.iloc[-1]
            if r.phia and not da_doc_tick and not gan_tin and (now - dong).total_seconds() <= T.HAN_GIAY:
                vet = _vet_tick(mt5, ma, now, _tick_ms(tick))
                da_doc_tick = True
            row = muc_live(cards[tf, chip], r, dong, now, tick, buoc=buoc, so_le=int(s.digits),
                           stops=stops, gan_tin=gan_tin, vet=vet)
            if chip == 'harry_smc':
                row['vung_theo_doi'] = zones
            cards[tf, chip] = row
    return list(cards.values())
