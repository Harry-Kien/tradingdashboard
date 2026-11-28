"""Bản tin đa khung từ OHLC đã đóng và Bid/Ask MT5, dùng cho Telegram và xem trước."""
from __future__ import annotations

import hashlib
import io
import math
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

from . import da_ma, phuong_phap, song
from .doc_so import VN

PHIEN_BAN = 'cau-truc-h1-1'
KHUNG = {'H4': 240, 'H1': 60, 'M30': 30, 'M15': 15, 'M5': 5}
TUOI_TICK = 30
SONG_GIO = 120
TEN_CHIEU = {1: 'tăng', -1: 'giảm', 0: 'trung tính'}


@dataclass(frozen=True)
class Vung:
    duoi: float
    tren: float
    chieu: int
    tu: int
    loai: str = 'FVG'


def ma_vung(v: Vung) -> str:
    s = (v.tu, v.chieu, v.loai, float(v.duoi), float(v.tren))
    return hashlib.sha256(repr(s).encode()).hexdigest()[:16]


def da_dong(b: pd.DataFrame, tf: str, moc: datetime) -> pd.DataFrame:
    phut = KHUNG[tf]
    if b.index.tz is None or b.index.has_duplicates or not b.index.is_monotonic_increasing:
        raise ValueError(f'Nến {tf} cần có múi giờ và thứ tự tăng dần.')
    x = b.loc[b.index + pd.Timedelta(minutes=phut) <= moc, ['open', 'high', 'low', 'close']]
    return x.loc[np.isfinite(x).all(axis=1) & (x > 0).all(axis=1) &
                 (x['high'] >= x[['open', 'close', 'low']].max(axis=1)) & (x['low'] <= x[['open', 'close']].min(axis=1))]


def phat_vung(h1: pd.DataFrame, fvg_repo: dict[int, tuple[int, float, float]] | None = None):
    """Phát trạng thái sau mỗi lần đóng H1; iFVG cần nến đóng xuyên biên, chỉ đảo vai một lần."""
    gio = h1.index.as_unit('s').asi8 + 3600
    mo, h, l, c = (h1[k].to_numpy(dtype=float) for k in ('open', 'high', 'low', 'close'))
    atr = phuong_phap._atr(h1).to_numpy()
    con = []
    for j, t in enumerate(gio):
        t = int(t)
        if not math.isfinite(atr[j]) or atr[j] <= 0:
            yield t, (), atr[j]
            continue
        moi = []
        for v in con:
            if t - v.tu > SONG_GIO * 3600:
                continue
            xu = v.duoi - .05 * atr[j] if v.chieu > 0 else v.tren + .05 * atr[j]
            if v.chieu * (c[j] - xu) < 0:
                if v.loai == 'FVG':
                    moi.append(replace(v, chieu=-v.chieu, tu=t, loai='iFVG'))
            else:
                moi.append(v)
        if j >= 2 and gio[j] - gio[j - 2] == 7200:
            luc = c[j - 1] - mo[j - 1]
            a = atr[j]
            if fvg_repo is not None:
                z = fvg_repo.get(j)
                if z and z[0] * luc >= .40 * a and z[2] - z[1] >= .08 * a:
                    moi.append(Vung(z[1], z[2], z[0], t))
            elif luc >= .40 * a and l[j] - h[j - 2] >= .08 * a:
                moi.append(Vung(h[j - 2], l[j], 1, t))
            elif luc <= -.40 * a and l[j - 2] - h[j] >= .08 * a:
                moi.append(Vung(h[j], l[j - 2], -1, t))
        con = moi
        yield t, tuple(con), atr[j]


def xu_huong(b: pd.DataFrame) -> int:
    if len(b) < 50:
        return 0
    c = b['close']
    a = phuong_phap._atr(b).iloc[-1]
    lech = c.ewm(span=20, adjust=False).mean().iloc[-1] - c.ewm(span=50, adjust=False).mean().iloc[-1]
    return int(np.sign(lech)) if math.isfinite(a) and abs(lech) >= .12 * a else 0


def xac_nhan(b: pd.DataFrame, tf: str, v: Vung, px: float, atr: float, *, cham_tick: int | None = None) -> dict:
    """Chỉ đếm lần đổi cấu trúc đã đóng, phát sinh từ nến chạm vùng gần nhất trở đi."""
    kq = {'tf': tf, 'tt': 'chua_cham'}
    b = b.iloc[-64:]
    if len(b) < 24:
        return {**kq, 'tt': 'thieu_nen'}
    phut = KHUNG[tf]
    mo = b.index.as_unit('s').asi8
    h, l, c = (b[k].to_numpy(dtype=float) for k in ('high', 'low', 'close'))
    cham = np.flatnonzero((mo >= v.tu) & (l <= v.tren) & (h >= v.duoi)) if cham_tick is None else np.flatnonzero(
        (mo * 1000 <= cham_tick) & (cham_tick < (mo + phut * 60) * 1000))
    if not len(cham):
        return kq
    pha, _ = phuong_phap._pha_cau_truc(h, l, c)
    # Chỉ cần chờ cú chạm mới nếu cú trước đã quá khung quan sát; giữ cùng một lần hồi nhiều nến.
    dot = cham[np.r_[True, np.diff(cham) > 2]][-1]
    dau = int(dot)
    kq.update(tt='cho_xac_nhan', cham=int(mo[dau] + phut * 60))
    for _, i, gia, chieu, loai in reversed(pha):
        if i < dau:
            break
        if loai != 'CHoCH' or chieu != v.chieu:
            continue
        if any(j > i and d != v.chieu for _, j, _, d, _ in pha):
            return {**kq, 'tt': 'cau_truc_doi_lai'}
        thuan = chieu * (px - gia)
        tt = 'xac_nhan' if len(b) - 1 - i <= 3 and 0 <= thuan <= .35 * atr else 'qua_xac_nhan'
        return {**kq, 'tt': tt, 'moc': float(gia), 'luc': int(mo[i] + phut * 60)}
    return kq


def lap(ma: str, fr: dict, bid: float, ask: float, tick_ms: int, moc: datetime, so_le: int, *, dang_theo_doi=None) -> dict:
    if not re.fullmatch(r'[\w.#+-]{1,32}', ma) or not all(math.isfinite(x) and x > 0 for x in (bid, ask)) or ask < bid or tick_ms <= 0:
        raise ValueError('Mã hoặc Bid/Ask của nguồn giá không hợp lệ.')
    nen = {k: da_dong(fr[k], k, moc) for k in KHUNG}
    h1 = nen['H1'].iloc[-(SONG_GIO * 2 + 20):]
    if len(h1) < 80 or len(nen['H4']) < 50:
        raise ValueError('Cần ít nhất 80 nến H1 và 50 nến H4 đã đóng.')
    t, ds, atr = list(phat_vung(h1))[-1]
    if not math.isfinite(atr) or atr <= 0:
        raise ValueError('Biên độ H1 không hợp lệ.')
    tuoi = moc.timestamp() - tick_ms / 1000
    tuoi_h1 = moc.timestamp() - t
    gia_moi = -5 <= tuoi <= TUOI_TICK and 0 <= tuoi_h1 <= 2 * 3600
    h4, huong = xu_huong(nen['H4'].iloc[-240:]), xu_huong(h1)
    px = (bid + ask) / 2
    cung = [v for v in ds if v.chieu == huong and (
        v.duoi <= px + .08 * atr if huong > 0 else v.tren >= px - .08 * atr)]
    cung.sort(key=lambda v: (abs(px - (v.duoi + v.tren) / 2), -v.tu))
    vung = []
    for v in cung:
        if any(min(v.tren, z['tren']) > max(v.duoi, z['duoi']) for z in vung):
            continue
        if abs(px - (v.duoi + v.tren) / 2) > 3 * atr:
            continue
        id_ = ma_vung(v)
        cham = (dang_theo_doi or {}).get(id_)
        dk = [xac_nhan(nen[k], k, v, ask if v.chieu > 0 else bid, atr, cham_tick=cham) for k in ('M5', 'M15', 'M30')]
        vung.append({**v.__dict__, 'id': id_, 'vo_hieu': v.duoi - .05 * atr if huong > 0 else v.tren + .05 * atr,
                     'cach_atr': max(v.duoi - px, px - v.tren, 0) / atr, 'xac_nhan': dk})
        if len(vung) == 2:
            break
    if not gia_moi:
        tt = 'gia_cu'
    elif not huong or h4 == -huong:
        tt = 'lech_khung'
    elif not vung:
        tt = 'chua_co_vung'
    elif any(d['tt'] == 'xac_nhan' for z in vung for d in z['xac_nhan']):
        tt = 'da_xac_nhan'
    else:
        tt = 'cho_xac_nhan'
    nen_so = [[int(i.timestamp()), *map(float, r)] for i, *r in h1.iloc[-65:].itertuples(name=None)]
    kq = {'phien_ban': PHIEN_BAN, 'ma': ma, 'luc': moc.isoformat(), 'nen_h1_dong': t, 'tick_ms': tick_ms, 'nguon': 'MT5',
          'gia_moi': gia_moi, 'bid': bid, 'ask': ask, 'so_le': so_le, 'h1': huong, 'h4': h4, 'trang_thai': tt, 'vung': vung,
          'nen': nen_so}
    kq['bang_chung'] = hashlib.sha256(repr(kq).encode('utf-8')).hexdigest()[:14]
    return kq


def doc(cfg: dict, ma: str = '', *, dang_theo_doi=None) -> dict:
    g = cfg['gia']
    ma = ma or da_ma.ma_vang(cfg)
    if not re.fullmatch(r'[\w.#+-]{1,32}', ma):
        raise ValueError('Mã không hợp lệ.')
    mt5 = da_ma._mt5(g)
    if mt5 is None:
        raise ValueError('Chưa có kết nối MT5 để xác minh giá và nến.')
    with song._khoa:
        s = mt5.symbol_info(ma)
        if s is None or not getattr(s, 'visible', False):
            raise ValueError(f'Mã {ma} chưa có trong Market Watch.')
        fr = {k: da_ma._nen(mt5, ma, k, 280) for k in KHUNG}
        tick = mt5.symbol_info_tick(ma)
        tk = mt5.account_info() if hasattr(mt5, 'account_info') else None
    if tick is None:
        raise ValueError('MT5 chưa trả Bid/Ask cho mã này.')
    ms = int(getattr(tick, 'time_msc', 0) or tick.time * 1000)
    kq = lap(ma, fr, float(tick.bid), float(tick.ask), ms, datetime.now(timezone.utc), int(s.digits), dang_theo_doi=dang_theo_doi)
    kq['feed'] = hashlib.sha256(str(getattr(tk, 'server', '')).encode()).hexdigest()[:12]
    return kq


TT = {'gia_cu': 'Dữ liệu lưu gần nhất · chỉ xem lại', 'lech_khung': 'Đứng ngoài · xu hướng chưa đồng thuận',
      'chua_co_vung': 'Đứng ngoài · chưa có vùng H1 phù hợp', 'da_xac_nhan': 'Đã thấy xác nhận cấu trúc · theo dõi tiếp',
      'cho_xac_nhan': 'Chờ xác nhận ở khung nhỏ'}
DK = {'chua_cham': 'chưa chạm', 'thieu_nen': 'thiếu nến', 'cho_xac_nhan': 'chờ đóng nến phá cấu trúc',
      'cau_truc_doi_lai': 'cấu trúc đã đổi lại', 'xac_nhan': 'đã xác nhận', 'qua_xac_nhan': 'xác nhận đã cũ hoặc giá đi xa'}


def so(kq, px):
    return f'{px:,.{kq["so_le"]}f}'.translate(str.maketrans(',.', '.,'))


def van_ban(kq: dict) -> str:
    ma, t = escape(kq['ma']), datetime.fromtimestamp(kq['tick_ms'] / 1000, VN)
    ngay = datetime.fromtimestamp(kq['nen_h1_dong'], VN)
    ra = [f'<b>HARRY GOLD RESEARCH · {ma}</b>',
          f'<b>{TT[kq["trang_thai"]]}</b>',
          f'MT5 {t:%H:%M:%S %d/%m} UTC+7 · Bid {so(kq, kq["bid"])} · Ask {so(kq, kq["ask"])}',
          f'H1 {TEN_CHIEU[kq["h1"]]} · H4 {TEN_CHIEU[kq["h4"]]} · nến H1 đóng {ngay:%H:%M} UTC+7']
    for i, z in enumerate(kq['vung'], 1):
        dau = 'dưới' if z['chieu'] > 0 else 'trên'
        ra.append(f'\n<b>{i}. {z["loai"]} H1 · {so(kq, z["duoi"])}–{so(kq, z["tren"])}</b>\n'
                  + ('Vùng dự phòng nếu nhịp hồi xuyên vùng 1. ' if i == 2 else '')
                  + f'Theo dõi CHoCH {"tăng" if z["chieu"] > 0 else "giảm"} sau cú chạm. '
                  f'Vô hiệu nếu H1 đóng {dau} {so(kq, z["vo_hieu"])}.')
        ra.append('  '.join(f'{d["tf"]} {DK[d["tt"]]}' + (f' ({so(kq, d["moc"])})' if 'moc' in d else '') for d in z['xac_nhan']))
    ra.append(f'\n<code>{kq["bang_chung"]}</code> · Nghiên cứu cấu trúc giá. Không phải lời khuyên đầu tư.')
    return '\n'.join(ra)


def anh_png(kq: dict) -> bytes:
    """Ảnh từ dữ liệu của bản tin, tránh xuất tài khoản hoặc hình vẽ cá nhân."""
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415

    def font(co, dam=False):
        for f in (Path('C:/Windows/Fonts') / ('segoeuib.ttf' if dam else 'segoeui.ttf'),
                  'DejaVuSans-Bold.ttf' if dam else 'DejaVuSans.ttf'):
            try:
                return ImageFont.truetype(str(f), co)
            except OSError:
                continue
        return ImageFont.load_default(size=co)

    im = Image.new('RGB', (1200, 710), '#0c1320')
    dr = ImageDraw.Draw(im)
    dr.text((38, 26), 'HARRY GOLD RESEARCH', font=font(22, True), fill='#75dfbf')
    dr.text((38, 57), f'{kq["ma"]}  ·  Cấu trúc H1', font=font(39, True), fill='#f1f5f9')
    dr.text((38, 111), TT[kq['trang_thai']], font=font(22), fill='#d1dbed')
    cs, zs = kq['nen'], kq['vung']
    left, right, top, bottom = 45, 1060, 165, 576
    lo = min([r[3] for r in cs] + [v['duoi'] for v in zs])
    hi = max([r[2] for r in cs] + [v['tren'] for v in zs])
    pad = max(.03 * (hi - lo), 10 ** -kq['so_le'])
    lo, hi = lo - pad, hi + pad
    y = lambda v: round(bottom - (v - lo) * (bottom - top) / (hi - lo))  # noqa: E731
    size = (right - left - 85) / len(cs)
    dt = datetime.fromtimestamp(kq['tick_ms'] / 1000, VN)
    for j in range(6):
        p = lo + j * (hi - lo) / 5
        dr.line((left, y(p), right, y(p)), fill='#253246')
        dr.text((right + 10, y(p) - 9), so(kq, p), font=font(17), fill='#9bacc5')
    for v, col, line in zip(zs, ('#214e48', '#3b3c58'), ('#8be0be', '#c0b6f6')):
        j = next((i for i, r in enumerate(cs) if r[0] + 3600 >= v['tu']), 0)
        x = min(round(left + j * size), right - 155)
        dr.rectangle((x, y(v['tren']), right, y(v['duoi'])), fill=col, outline=line, width=1)
    for i, (t, o, h, l, c) in enumerate(cs):
        x = round(left + (i + .5) * size)
        col = '#7fdfbd' if c >= o else '#f28393'
        dr.line((x, y(h), x, y(l)), fill=col, width=2)
        d = max(2, round(size * .28))
        dr.rectangle((x-d, min(y(o), y(c)), x+d, max(y(o), y(c))+1), fill=col)
        if i % 13 == 0:
            dr.text((x, bottom+16), datetime.fromtimestamp(t, VN).strftime('%d/%m %H:%M'), font=font(15), fill='#9bacc5')
    for i, v in enumerate(zs):
        x = left + i * 520
        dr.text((x, 626), f'{i+1}. {v["loai"]}  {so(kq, v["duoi"])}–{so(kq, v["tren"])}', font=font(21, True),
                fill=('#8be0be', '#c0b6f6')[i])
    dr.text((left, 671), f'Nguồn MT5 · {dt:%H:%M:%S %d/%m} UTC+7 · {kq["bang_chung"]}', font=font(17), fill='#9bacc5')
    out = io.BytesIO()
    im.save(out, format='PNG')
    return out.getvalue()
