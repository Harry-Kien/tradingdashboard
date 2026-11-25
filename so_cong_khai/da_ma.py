"""Nhiều mã CFD: đọc giá và nến của các mã ĐANG HIỆN trong Market Watch của MT5 demo, và tính phần phân tích không phụ thuộc
thang giá của từng mã: xu hướng D1/H4/H1, ATR, RSI, hỗ trợ/kháng cự, khoảng trống giá, khối lệnh.

Chỉ đọc. Mô-đun không chọn thêm mã vào Market Watch (muốn thêm thì chủ máy tự thêm trong MT5), không đặt lệnh, và dùng chung
phiên nối an toàn của song.py (chỉ nối vào MT5 đang mở, chỉ nhận tài khoản demo).

Bốn luật ra điểm vào của hệ thống (hai kiểu của bot, luật ba khung, luật đỉnh/đáy) được viết và đo riêng cho vàng: khoảng dừng lỗ
và mức chốt lời của chúng là con số của vàng. Áp cho mã khác sẽ cho mức giá vô nghĩa, nên ở đây KHÔNG gọi các luật đó.
Các hàm chỉ báo dùng lại của dự án (EMA, ATR, đỉnh/đáy 2 giờ, vùng giá) đều tính theo tỷ lệ nên dùng được cho mọi mã."""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from . import gia, phuong_phap, song

NHOM = {'Forex': 'Ngoại hối', 'Commodities': 'Hàng hóa', 'Indices': 'Chỉ số', 'Crypto': 'Tiền mã hóa'}
SO_NEN = {'M5': 900, 'M15': 900, 'M30': 600, 'H1': 900, 'H4': 900, 'D1': 900}
GIAI_THICH = ('Ba luật trong sổ của bạn (bot tín hiệu, luật ba khung, luật đỉnh/đáy) được viết và đo riêng cho vàng: khoảng dừng lỗ và '
              'mức chốt lời của chúng là con số của vàng, nên không áp cho mã này. Các phương pháp tùy chọn bên dưới tính theo ATR nên áp được, '
              'và được chạy lại trên nến 5 phút của chính mã này từ đầu năm (xem số đo trong từng thẻ). Số đo đó chưa đầy một năm và chưa trừ phí hoa hồng: '
              'coi là dấu hiệu để theo dõi, chưa phải bằng chứng.')
GIAI_CHIA_SE = ('Bản chia sẻ này không có luật vào lệnh riêng của ai: các phương án dưới đây là những phương pháp tùy chọn tính theo ATR, '
                'được chạy lại trên nến 5 phút của chính mã này lấy từ MT5 của bạn (xem số đo trong từng thẻ). Số đo đó chưa trừ phí hoa hồng: '
                'coi là dấu hiệu để theo dõi, chưa phải bằng chứng, và không phải lời khuyên đầu tư.')
_nho: dict = {}


def _vang_chia_se(cfg: dict, ma: str) -> bool:
    """Mã vàng trên bản chia sẻ (máy không có luật riêng của chủ dự án): trang ghi lời giải thích của bản chia sẻ."""
    return ma == ma_vang(cfg) and gia.ban_chia_se(cfg['gia'])


def ma_vang(cfg: dict) -> str:
    return (cfg.get('gia') or {}).get('ma_vang') or song._tt.get('sym') or 'XAUUSDp'


def _mt5(g: dict):
    """Phiên MT5 đang nối (None nếu chưa bật hoặc không nối được). Bài kiểm thay hàm này bằng một MT5 giả."""
    if song.khung_song(g) is None:
        return None
    return song._tt.get('mt5')


def _lam_tron(x, d: int):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if x != x else round(x, d)


def _nen(mt5, sym: str, tf: str, n: int, vi_tri: int = 1) -> pd.DataFrame:
    """Nến đã đóng (vi_tri=1) của một mã, chỉ số là giờ mở nến UTC. Giờ máy chủ của sàn là UTC."""
    r = mt5.copy_rates_from_pos(sym, getattr(mt5, 'TIMEFRAME_' + tf), vi_tri, n)
    if r is None or len(r) == 0:
        raise RuntimeError(f'MT5 không trả nến {tf} của {sym}')
    df = pd.DataFrame(r)
    df.index = pd.to_datetime(df['time'], unit='s', utc=True)
    return df[['open', 'high', 'low', 'close']].astype(float)


def _hien(mt5) -> dict:
    return {s.name: s for s in (mt5.symbols_get() or []) if getattr(s, 'visible', False)}


def _nhom(path: str) -> str:
    dau = (path or '').split('\\')[0].split('_')[0]
    return NHOM.get(dau, dau or 'Khác')


def _chi_bao(g: dict):
    R, RT, _, SN = gia._nap_ma(g)
    return R, RT, SN


def _vung(SN, src: pd.DataFrame, atr_h1: float, d: int) -> list[tuple[str, dict]]:
    """Khoảng trống giá và khối lệnh của một mã bất kỳ: [('fvg' | 'ob', vùng)]. Hai hàm của dự án làm tròn giá về 2 chữ số (đủ cho vàng),
    nên với mã có nhiều chữ số hơn thì nhân giá lên trước khi gọi rồi chia lại, để không mất độ chính xác."""
    k = 10 ** max(0, d - 2)
    to = src.copy()
    to[['open', 'high', 'low', 'close']] = to[['open', 'high', 'low', 'close']] * k
    out = []
    for loai, rows in (('fvg', SN.fvg_zones(to, 0.1 * atr_h1 * k, 8)), ('ob', SN.order_blocks(to, 1.0 * atr_h1 * k, 8))):
        out += [(loai, {**z, 'duoi': z['duoi'] / k, 'tren': z['tren'] / k}) for z in rows]
    return out


def danh_sach(cfg: dict, now: datetime | None = None) -> dict:
    """Mọi mã đang hiện trong Market Watch: giá, thay đổi so với giá đóng cửa ngày trước, xu hướng ba khung, ATR và RSI khung H1."""
    g = cfg['gia']
    now = now or datetime.now(timezone.utc)
    cu = _nho.get('ds')
    if cu and time.monotonic() - cu[0] < 15:
        return cu[1]
    mt5 = _mt5(g)
    if mt5 is None:
        return {'san_sang': False, 'ly_do': song.ly_do() or 'chưa nối được MT5', 'ds': []}
    R, RT, _ = _chi_bao(g)
    vang, ds = ma_vang(cfg), []
    with song._khoa:
        hien = _hien(mt5)
    for ten, s in hien.items():                                               # khóa từng mã, không khóa cả vòng: Market Watch có thể có gần trăm mã,
        # và bảng giá trực tiếp (thi_truong.py) cần chen vào đọc tick giữa các mã
        d = int(s.digits)
        row = {'ma': ten, 'ten': s.description, 'nhom': _nhom(s.path), 'so_le': d, 'la_vang': ten == vang}
        try:
            with song._khoa:
                tick = mt5.symbol_info_tick(ten)
                d1, h4, h1 = _nen(mt5, ten, 'D1', 300), _nen(mt5, ten, 'H4', 300), _nen(mt5, ten, 'H1', 300)
            bid = float(tick.bid) if tick and tick.bid else float(h1['close'].iloc[-1])
            huong = RT.directions(d1['close'], h4['close'], h1['close'])
            atr = float(R.atr_sma(h1, 14).iloc[-1])
            row.update(bid=_lam_tron(bid, d), ask=_lam_tron(tick.ask, d) if tick and tick.ask else None,
                       doi_ngay=_lam_tron((bid / float(d1['close'].iloc[-1]) - 1) * 100, 2),
                       xu_huong={k: int(v) for k, v in huong.items()}, atr_h1=_lam_tron(atr, d), atr_pct=_lam_tron(atr / bid * 100, 2),
                       rsi_h1=_lam_tron(gia.rsi_wilder(h1['close']).iloc[-1], 1), tia=[_lam_tron(v, d) for v in h1['close'].iloc[-48:]],
                       tuoi_phut=max(0, int((now.timestamp() - tick.time) // 60)) if tick else None)
        except Exception as e:                                             # noqa: BLE001 - một mã lỗi không chặn các mã khác
            row['loi'] = f'{type(e).__name__}: {e}'
        ds.append(row)
    ds.sort(key=lambda r: (not r['la_vang'], r['nhom'], r['ma']))
    out = {'san_sang': True, 'ds': ds, 'luc': now.isoformat()}
    _nho['ds'] = (time.monotonic(), out)
    return out


def _doc(cfg: dict, ma: str, tfs) -> tuple:
    g = cfg['gia']
    mt5 = _mt5(g)
    if mt5 is None:
        raise ValueError(f'chưa có giá trực tiếp từ MT5 ({song.ly_do() or "chưa nối"}); các mã ngoài vàng chỉ đọc được khi MT5 demo đang mở')
    with song._khoa:
        hien = _hien(mt5)
        if ma not in hien:
            raise ValueError(f'mã {ma} không có trong Market Watch của MT5; mở MT5 và thêm mã đó vào Market Watch')
        s = hien[ma]
        fr = {tf: _nen(mt5, ma, tf, SO_NEN[tf]) for tf in tfs}
        tick = mt5.symbol_info_tick(ma)
        chay = {}
        for tf in tfs:
            try:
                x = _nen(mt5, ma, tf, 1, 0)
                chay[tf] = (x.index[-1], *[float(v) for v in x.iloc[-1]])
            except Exception:                                                  # noqa: BLE001 - thiếu nến đang chạy thì vẫn vẽ nến đã đóng
                pass
    return s, fr, tick, chay


def _boi_canh(g: dict, fr: dict, bid: float, d: int, het: datetime) -> tuple[dict, list]:
    """Phần không phụ thuộc thang giá, tính bằng các hàm chỉ báo của dự án. Trả (bối cảnh, lỗi)."""
    R, RT, SN = _chi_bao(g)
    loi, bc = [], {}
    try:
        snap = R.snapshot(fr['M15'].iloc[-320:], fr['H1'].iloc[-300:], fr['H4'].iloc[-300:], fr['D1'].iloc[-900:], 'M15')
        bc['bot'] = {k: (int(v) if k in ('H1', 'H4', 'D1', 'trend') else _lam_tron(v, d)) for k, v in snap.items()}
    except Exception as e:                                                     # noqa: BLE001
        loi.append(f'Xu hướng: {type(e).__name__}: {e}')
    try:
        atr_h1 = float(R.atr_sma(fr['H1'], 14).iloc[-1])
        src = fr['M15'].iloc[-300:].reset_index(names='time')
        zs = [dict(z, loai='Khoảng trống giá' if loai == 'fvg' else 'Khối lệnh') for loai, z in _vung(SN, src, atr_h1, d)]
        tren = min((z for z in zs if z['duoi'] > bid), key=lambda z: z['duoi'], default=None)
        duoi = max((z for z in zs if z['tren'] < bid), key=lambda z: z['tren'], default=None)
        bc['vung'] = {k: ({'loai': z['loai'], 'duoi': _lam_tron(z['duoi'], d), 'tren': _lam_tron(z['tren'], d)} if z else None)
                      for k, z in (('tren', tren), ('duoi', duoi))}
    except Exception as e:                                                     # noqa: BLE001
        loi.append(f'Vùng giá: {type(e).__name__}: {e}')
    if g.get('lich_tin'):
        try:
            news, _ = gia.tin_usd(g)
            nxt = next((t for t in news if t > het), None)
            bc['tin'] = {'sap_toi': nxt.isoformat() if nxt else None, 'dang_ne': bool(SN.in_news_blackout(het, news))}
        except Exception as e:                                                 # noqa: BLE001
            loi.append(f'Lịch tin USD: {type(e).__name__}: {e}')
    return bc, loi


def goi(cfg: dict, ma: str, tf: str = 'M15', n: int = 600, now: datetime | None = None) -> dict:
    """Dữ liệu biểu đồ cho một mã ngoài vàng, cùng dạng với gia.goi nhưng không có phần luật và không có lệnh."""
    if tf not in SO_NEN:
        raise ValueError(f'khung không hỗ trợ: {tf}')
    g = cfg['gia']
    now = now or datetime.now(timezone.utc)
    s, fr, tick, chay = _doc(cfg, ma, sorted({tf, 'M15', 'H1', 'H4', 'D1'}))
    d = int(s.digits)
    R, _, SN = _chi_bao(g)
    bars = fr[tf]
    n = max(50, min(int(n), 1500))
    close = bars['close']
    mid, sd = close.rolling(20).mean(), close.rolling(20).std(ddof=0)
    over = {'ema20': close.ewm(span=20, adjust=False, min_periods=20).mean(), 'ema50': close.ewm(span=50, adjust=False, min_periods=50).mean(),
            'bb_tren': mid + 2 * sd, 'bb_duoi': mid - 2 * sd}
    view = bars.iloc[-n:]
    day = lambda x, k=d: [_lam_tron(v, k) for v in x.iloc[-n:].tolist()]        # noqa: E731
    het = (datetime.fromtimestamp(tick.time, timezone.utc) if tick else (fr['M15'].index[-1] + timedelta(minutes=15)).to_pydatetime())
    bid = float(tick.bid) if tick and tick.bid else float(fr['M15']['close'].iloc[-1])
    out = {'ma': ma, 'ten': s.description, 'nhom': _nhom(s.path), 'so_le': d, 'khac_vang': True, 'chia_se': _vang_chia_se(cfg, ma), 'tf': tf,
           'candles': [[gia._giay(t), *(_lam_tron(v, d) for v in (o, h, l, c))] for t, o, h, l, c in
                       zip(view.index, view['open'], view['high'], view['low'], view['close'])],
           **{k: day(v) for k, v in over.items()}, 'rsi': day(gia.rsi_wilder(close), 2), 'vung': [], 'tin': [], 'lenh': [],
           'nguon': 'mt5', 'bid': _lam_tron(bid, d), 'ask': _lam_tron(tick.ask, d) if tick and tick.ask else None, 'ly_do_khong_song': None}
    if tf in chay and out['candles'] and gia._giay(chay[tf][0]) > out['candles'][-1][0]:
        out['dang_chay'] = [gia._giay(chay[tf][0])] + [_lam_tron(v, d) for v in chay[tf][1:]]
    bc, loi = _boi_canh(g, fr, bid, d, het)
    try:
        if tf in ('M5', 'M15', 'M30'):
            sup, res = R.levels_sr(bars, tf, 2)
            out['ho_tro'], out['khang_cu'] = day(sup), day(res)
        if tf != 'D1':
            atr_h1 = float(R.atr_sma(fr['H1'], 14).iloc[-1])
            src = bars.iloc[-300:].reset_index(names='time')
            out['vung'] += [{'loai': loai, 'huong': z['huong'], 't': gia._giay(pd.Timestamp(z['thoi_diem_utc'], tz='UTC')),
                             'duoi': _lam_tron(z['duoi'], d), 'tren': _lam_tron(z['tren'], d)} for loai, z in _vung(SN, src, atr_h1, d)]
        if g.get('lich_tin') and len(view):
            news, _ = gia.tin_usd(g)
            a, b = view.index[0].to_pydatetime(), het + timedelta(days=3)
            out['tin'] = [gia._giay(t) for t in news if a <= t <= b]
    except Exception as e:                                                     # noqa: BLE001
        loi.append(f'Vùng giá và hỗ trợ/kháng cự: {type(e).__name__}: {e}')
    out['luat'] = {'het': het.isoformat(), 'tuoi_phut': max(0, int((now - het).total_seconds() // 60)), 'loi': loi, **bc}
    return out


def phan_tich(cfg: dict, ma: str, now: datetime | None = None) -> dict:
    """Bối cảnh của một mã ngoài vàng. Không có phương án vào lệnh: xem GIAI_THICH."""
    g = cfg['gia']
    now = now or datetime.now(timezone.utc)
    s, fr, tick, _ = _doc(cfg, ma, ['M15', 'H1', 'H4', 'D1'])
    d = int(s.digits)
    het = (datetime.fromtimestamp(tick.time, timezone.utc) if tick else (fr['M15'].index[-1] + timedelta(minutes=15)).to_pydatetime())
    bid = float(tick.bid) if tick and tick.bid else float(fr['M15']['close'].iloc[-1])
    ask = float(tick.ask) if tick and tick.ask else bid
    tuoi = max(0, int((now - het).total_seconds() // 60))
    bc, loi = _boi_canh(g, fr, bid, d, het)
    snap = bc.pop('bot', {})
    cs = _vang_chia_se(cfg, ma)
    out = {'ma': ma, 'ten': s.description, 'so_le': d, 'khac_vang': True, 'chia_se': cs, 'giai_thich': GIAI_CHIA_SE if cs else GIAI_THICH,
           'luc': now.isoformat(), 'het': het.isoformat(),
           'tuoi_phut': tuoi, 'nguon': 'mt5', 'bid': _lam_tron(bid, d), 'ask': _lam_tron(ask, d), 'phuong_an': [], 'canh_bao': [], 'loi': loi,
           'dong_thuan': {'MUA': 0, 'BAN': 0, 'khong': 0}, 'con_hieu_luc': 0,
           'boi_canh': {'xu_huong': {k: snap[k] for k in ('D1', 'H4', 'H1', 'trend') if k in snap}, 'atr_m15': snap.get('atr'),
                        'ho_tro': snap.get('support'), 'khang_cu': snap.get('resistance'), 'spread': _lam_tron(ask - bid, d),
                        'vung': bc.get('vung') or {}, 'tin': bc.get('tin') or {}}}
    try:                                                       # phiên và biên độ lúc này, cùng cách tính với phần đo trên dữ liệu của mã
        from . import hoc                                      # noqa: PLC0415 - hoc nạp da_ma gián tiếp qua hoc_ma
        out['boi_canh'].update(hoc.boi_canh_luc(fr['H1'], het))
    except Exception as e:                                                 # noqa: BLE001
        out['loi'].append(f'Bối cảnh phiên và biên độ: {type(e).__name__}: {e}')
    chung = []
    if tuoi > 20:
        out['canh_bao'].append(f'Giá đã cũ {tuoi} phút (thị trường của mã này đang nghỉ, hoặc MT5 mất kết nối).')
        chung.append(f'Giá đã cũ {tuoi} phút.')
    if (bc.get('tin') or {}).get('dang_ne'):
        out['canh_bao'].append('Đang trong 15 phút quanh một tin USD mạnh.')
        chung.append('Đang trong 15 phút quanh một tin USD mạnh.')
    try:
        out['ict'] = phuong_phap.ban_do_ict(fr['M15'], fr['H1'], bid, now, d)
    except Exception as e:                                                 # noqa: BLE001
        out['loi'].append(f'Bản đồ ICT: {type(e).__name__}: {e}')
    out['phuong_phap'] = []                                    # các phương pháp tính theo ATR nên áp được cho mã này; số đo trên dữ liệu của nó nằm ở hoc_ma
    for pp in phuong_phap.DS:
        try:
            out['phuong_phap'].append(phuong_phap.phuong_an(pp, fr['M15'], fr['H1'], bid, ask, now, chung, d))
        except Exception as e:                                             # noqa: BLE001
            out['loi'].append(f'{phuong_phap.DS[pp]["ten"]}: {type(e).__name__}: {e}')
    return out
