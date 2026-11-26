"""Thị trường: bảng giá TRỰC TIẾP của mọi mã Forex và CFD mà sàn cung cấp trong MT5 demo, đẩy về trình duyệt theo thời gian thực.

Hai luồng nền:
- luồng giá (mặc định 0,5 giây một lần) đọc tick của mọi mã (88 mã mất khoảng 2 ms) và báo cho các kết nối SSE đang mở;
- luồng mốc (30 giây một lần) đọc thông số hợp đồng, ký quỹ 1 lot, và các mốc giá để tính thay đổi: giá 1 giờ và 4 giờ trước
  (nến M5), giá đóng cửa hôm trước, mở cửa tuần và tháng, biên độ hôm nay, biên độ trung bình 14 ngày (ADR), đường giá 4 giờ;
  10 phút một lần tính ma trận tương quan trên 240 nến H1.

Chỉ đọc giá. Mô-đun KHÔNG đặt, sửa hay đóng lệnh. Hai lời gọi tính toán thuần của MT5 được dùng: order_calc_margin (ký quỹ cần cho một
khối lượng) và order_calc_profit (lãi lỗ giữa hai mức giá); cả hai chỉ tính, không gửi gì lên sàn.

MT5 chỉ trả tick cho mã đang nằm trong Market Watch. Khi `thi_truong.them_vao_market_watch` là true, mô-đun thêm các mã giao dịch được của
sàn vào Market Watch (symbol_select) để có giá trực tiếp cho tất cả; muốn bỏ thì đặt false và tự ẩn mã trong MT5. Tắt hẳn phần này bằng
`"thi_truong": {"bat": false}` trong cau-hinh.json. Dùng chung phiên nối an toàn của song.py (chỉ nối MT5 đang mở, chỉ nhận tài khoản demo)."""
from __future__ import annotations

import csv
import json
import math
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import song

# --------------------------------------------------------------------------- phân loại và kiến thức tĩnh
LOP = {'fx_chinh': 'Forex chính', 'fx_cheo': 'Forex chéo', 'fx_ngoai_lai': 'Forex ngoại lai', 'kim_loai': 'Kim loại',
       'nang_luong': 'Năng lượng', 'chi_so': 'Chỉ số', 'crypto': 'Tiền mã hóa', 'khac': 'Khác'}
CHINH = ('USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD')
TIEN_TE = {
    'USD': {'ten': 'Đô la Mỹ', 'nh': 'Fed', 'nuoc': 'Mỹ', 'ghi': 'Đồng tiền dự trữ của thế giới; mạnh lên khi thị trường sợ rủi ro hoặc Fed giữ lãi suất cao.'},
    'EUR': {'ten': 'Euro', 'nh': 'ECB', 'nuoc': 'Khu vực đồng euro', 'ghi': 'Đồng tiền giao dịch nhiều thứ hai; nhạy với chênh lệch lãi suất ECB và Fed.'},
    'GBP': {'ten': 'Bảng Anh', 'nh': 'BoE', 'nuoc': 'Anh', 'ghi': 'Biến động mạnh trong phiên London; nhạy với lạm phát và lãi suất của BoE.'},
    'JPY': {'ten': 'Yên Nhật', 'nh': 'BoJ', 'nuoc': 'Nhật Bản', 'ghi': 'Tiền trú ẩn và tiền đi vay cho carry trade vì lãi suất thấp; mạnh lên khi thị trường hoảng.'},
    'CHF': {'ten': 'Franc Thụy Sĩ', 'nh': 'SNB', 'nuoc': 'Thụy Sĩ', 'ghi': 'Tiền trú ẩn; SNB từng can thiệp mạnh (bỏ sàn EURCHF tháng 1/2015).'},
    'CAD': {'ten': 'Đô la Canada', 'nh': 'BoC', 'nuoc': 'Canada', 'ghi': 'Tiền hàng hóa: thường đi cùng giá dầu.'},
    'AUD': {'ten': 'Đô la Úc', 'nh': 'RBA', 'nuoc': 'Úc', 'ghi': 'Tiền hàng hóa và khẩu vị rủi ro; nhạy với kinh tế Trung Quốc, quặng sắt, vàng.'},
    'NZD': {'ten': 'Đô la New Zealand', 'nh': 'RBNZ', 'nuoc': 'New Zealand', 'ghi': 'Tiền hàng hóa (sữa, nông sản); thường đi cùng AUD.'},
    'CNH': {'ten': 'Nhân dân tệ (ngoài khơi)', 'nh': 'PBoC', 'nuoc': 'Trung Quốc', 'ghi': 'Giao dịch ngoài Trung Quốc đại lục; biên độ do PBoC định hướng.'},
    'HKD': {'ten': 'Đô la Hồng Kông', 'nh': 'HKMA', 'nuoc': 'Hồng Kông', 'ghi': 'Neo vào USD trong dải 7,75–7,85.'},
    'SGD': {'ten': 'Đô la Singapore', 'nh': 'MAS', 'nuoc': 'Singapore', 'ghi': 'MAS điều hành theo rổ tiền tệ thay vì lãi suất.'},
    'ZAR': {'ten': 'Rand Nam Phi', 'nh': 'SARB', 'nuoc': 'Nam Phi', 'ghi': 'Tiền mới nổi, lãi suất cao, biến động mạnh, spread rộng.'},
}
BIET_DANH = {'EURUSD': 'Fiber', 'GBPUSD': 'Cable', 'USDJPY': 'Gopher', 'USDCHF': 'Swissie', 'AUDUSD': 'Aussie', 'NZDUSD': 'Kiwi',
             'USDCAD': 'Loonie', 'EURJPY': 'Yuppy', 'GBPJPY': 'Guppy', 'EURGBP': 'Chunnel', 'XAUUSD': 'Vàng', 'XAGUSD': 'Bạc',
             'US30': 'Dow Jones 30 · Mỹ', 'US500': 'S&P 500 · Mỹ', 'USTEC': 'Nasdaq 100 · Mỹ', 'GER30': 'DAX · Đức', 'GER40': 'DAX · Đức',
             'UK100': 'FTSE 100 · Anh', 'FRANCE': 'CAC 40 · Pháp', 'FRA40': 'CAC 40 · Pháp', 'EUR50': 'Euro Stoxx 50', 'JAPAN': 'Nikkei 225 · Nhật',
             'JP225': 'Nikkei 225 · Nhật', 'HK-HSI': 'Hang Seng · Hồng Kông', 'HK50': 'Hang Seng · Hồng Kông', 'CHINAH': 'Hang Seng China Enterprises',
             'AUS200': 'S&P/ASX 200 · Úc', 'BRENT': 'Dầu Brent', 'UKOIL': 'Dầu Brent', 'CRUDE': 'Dầu WTI', 'USOIL': 'Dầu WTI', 'WTI': 'Dầu WTI',
             'BTCUSDT': 'Bitcoin', 'ETHUSDT': 'Ethereum', 'BTCUSD': 'Bitcoin', 'ETHUSD': 'Ethereum', 'SOLUSDT': 'Solana', 'XRPUSDT': 'XRP',
             'BNBUSDT': 'BNB', 'ADAUSDT': 'Cardano', 'DOGEUSDT': 'Dogecoin', 'ETHBTC': 'Ethereum/Bitcoin', 'XAUUSD247': 'Vàng 24/7'}
KIEU_TINH = {0: 'Forex', 1: 'Hợp đồng tương lai', 2: 'CFD', 3: 'CFD chỉ số', 4: 'CFD có đòn bẩy', 5: 'Forex không đòn bẩy',
             32: 'Cổ phiếu (sàn)', 33: 'Hợp đồng tương lai (sàn)', 34: 'Trái phiếu', 35: 'Cổ phiếu MOEX', 36: 'Trái phiếu MOEX', 38: 'Ký quỹ đảm bảo'}
SWAP_KIEU = {0: 'Tắt', 1: 'Điểm', 2: 'Tiền gốc', 3: 'Tiền ký quỹ', 4: 'Tiền tài khoản', 5: 'Lãi suất năm (giá hiện tại)',
             6: 'Lãi suất năm (giá mở)', 7: 'Mở lại theo giá đóng', 8: 'Mở lại theo bid'}
THU = ('Chủ nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy')
TUONG_QUAN_MA = ('EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD', 'USDJPY', 'USDCHF', 'USDCAD', 'EURJPY', 'GBPJPY', 'EURGBP', 'XAUUSD', 'XAGUSD',
                 'BRENT', 'CRUDE', 'US500', 'USTEC', 'US30', 'GER30', 'JAPAN', 'BTCUSDT', 'ETHUSDT')
_ISO = set(TIEN_TE) | {'SEK', 'NOK', 'DKK', 'PLN', 'HUF', 'CZK', 'TRY', 'MXN', 'RUB', 'INR', 'THB', 'ILS', 'CNY', 'KRW', 'TWD', 'BRL'}


def goc(ten: str) -> str:
    """Tên chuẩn bỏ đuôi của sàn: 'EURUSDp' → 'EURUSD', 'US30.cash' → 'US30', 'HK-HSIp' → 'HK-HSI'."""
    x = re.sub(r'\.[A-Za-z0-9]+$', '', ten)
    return re.sub(r'(?<=[A-Z0-9])[a-z_]+$', '', x) or ten


def phan_loai(ten: str, path: str = '') -> str:
    """Lớp tài sản theo thư mục mã của sàn; sàn khác cách đặt thư mục thì đoán theo tên."""
    p, g = (path or '').replace('/', '\\'), goc(ten).upper()
    dau = p.split('\\')[0].lower()
    if dau.startswith('forex') or (len(g) == 6 and g[:3] in _ISO and g[3:] in _ISO):
        if '\\major' in p.lower() or (g[:3] in CHINH and g[3:] in CHINH and 'USD' in (g[:3], g[3:])):
            return 'fx_chinh'
        if '\\exotic' in p.lower() or not (g[:3] in CHINH and g[3:] in CHINH):
            return 'fx_ngoai_lai'
        return 'fx_cheo'
    if g[:3] in ('XAU', 'XAG', 'XPT', 'XPD') or 'metal' in p.lower():
        return 'kim_loai'
    if 'crypto' in dau or g.startswith(('BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'BNB', 'LTC')):
        return 'crypto'
    if 'indic' in dau or 'index' in dau:
        return 'chi_so'
    if dau.startswith(('commod', 'energ')) or any(k in g for k in ('OIL', 'BRENT', 'CRUDE', 'WTI', 'NGAS', 'GAS')):
        return 'nang_luong'
    return 'khac'


def kich_thuoc_pip(lop: str, so_le: int, diem: float) -> float | None:
    """Một pip của cặp tiền: 0,0001 (0,01 với cặp có JPY). Chỉ định nghĩa cho Forex; CFD tính theo điểm giá."""
    if not lop.startswith('fx'):
        return None
    return diem * 10 if so_le in (3, 5) else diem


def _so(x, d: int | None = None):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if x != x or math.isinf(x):
        return None
    return round(x, d) if d is not None else x


# --------------------------------------------------------------------------- tổng hợp chỉ báo kỹ thuật
KHUNG_KT = ('M15', 'H1', 'H4', 'D1')
def nhan_kt(x: float | None) -> str:
    """Nhãn của điểm tổng hợp trong [-1, 1], cùng ngưỡng với bảng Technical Ratings của TradingView:
    (0,5; 1] mua mạnh, (0,1; 0,5] mua, [−0,1; 0,1] trung tính, [−0,5; −0,1) bán, [−1; −0,5) bán mạnh."""
    if x is None:
        return '—'
    return 'Mua mạnh' if x > 0.5 else 'Mua' if x > 0.1 else 'Trung tính' if x >= -0.1 else 'Bán' if x >= -0.5 else 'Bán mạnh'


def ky_thuat(o, h, l, c, chi_tiet: bool = False) -> dict | None:
    """Bỏ phiếu của 12 đường trung bình (SMA, EMA 10/20/30/50/100/200: giá trên đường là mua, dưới là bán) và 7 chỉ báo dao động
    (RSI14, Stochastic 14-3-3, CCI20, ADX14, MACD 12-26-9, Momentum 10, Williams %R 14) theo luật của TradingView: dao động chỉ báo
    mua khi ở vùng quá bán VÀ đang quay lên (và ngược lại), nên phần lớn thời gian là trung tính. Điểm mỗi nhóm = trung bình phiếu (−1..1);
    điểm tổng = trung bình hai nhóm. Đây là mô tả trạng thái chỉ báo, không phải tín hiệu đã kiểm chứng.
    o, h, l, c: dãy số theo thời gian, phần tử cuối là nến mới nhất. Trả None nếu chưa đủ 60 nến."""
    import numpy as np                                              # noqa: PLC0415
    import pandas as pd                                             # noqa: PLC0415
    c = pd.Series(np.asarray(c, dtype=float))
    h = pd.Series(np.asarray(h, dtype=float))
    l = pd.Series(np.asarray(l, dtype=float))
    if len(c) < 60:
        return None
    gia = float(c.iloc[-1])
    ma = []
    for n in (10, 20, 30, 50, 100, 200):
        if len(c) < n:
            continue
        for loai, s in (('SMA', c.rolling(n).mean()), ('EMA', c.ewm(span=n, adjust=False).mean())):
            v = float(s.iloc[-1])
            ma.append((f'{loai} {n}', v, 1 if gia > v else -1 if gia < v else 0))
    hai = lambda s: (float(s.iloc[-1]), float(s.iloc[-2]))           # noqa: E731
    dd = []
    d = c.diff()
    rs = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean() / (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean().replace(0, np.nan)
    rsi = (100 - 100 / (1 + rs)).fillna(100)
    r0, r1 = hai(rsi)
    dd.append(('RSI 14', r0, 1 if r0 < 30 and r0 > r1 else -1 if r0 > 70 and r0 < r1 else 0))
    ll, hh = l.rolling(14).min(), h.rolling(14).max()
    rng = (hh - ll).replace(0, np.nan)
    k = (100 * (c - ll) / rng).rolling(3).mean()
    dk = k.rolling(3).mean()
    k0, d0 = float(k.iloc[-1]), float(dk.iloc[-1])
    dd.append(('Stochastic %K 14-3-3', k0, 1 if k0 < 20 and k0 > d0 else -1 if k0 > 80 and k0 < d0 else 0))
    tp = (h + l + c) / 3
    cc = []
    for j in (-1, -2):
        w = tp.iloc[len(tp) + j - 19: len(tp) + j + 1].to_numpy()
        md = float(np.mean(np.abs(w - w.mean()))) or float('nan')
        cc.append((w[-1] - w.mean()) / (0.015 * md))
    dd.append(('CCI 20', cc[0], 1 if cc[0] < -100 and cc[0] > cc[1] else -1 if cc[0] > 100 and cc[0] < cc[1] else 0))
    up, dn = h.diff(), -l.diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0))
    mdm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0))
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean().replace(0, np.nan)
    pdi = 100 * pdm.ewm(alpha=1 / 14, adjust=False).mean() / atr
    mdi = 100 * mdm.ewm(alpha=1 / 14, adjust=False).mean() / atr
    adx = (100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)).ewm(alpha=1 / 14, adjust=False).mean()
    a0, a1 = hai(adx)
    p0, m0 = float(pdi.iloc[-1]), float(mdi.iloc[-1])
    dd.append(('ADX 14', a0, (1 if p0 > m0 else -1) if a0 > 20 and a0 > a1 else 0))
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    sig = macd.ewm(span=9, adjust=False).mean()
    m0_, s0 = float(macd.iloc[-1]), float(sig.iloc[-1])
    dd.append(('MACD 12-26-9', m0_, 1 if m0_ > s0 else -1 if m0_ < s0 else 0))
    mom = c - c.shift(10)
    o0, o1 = hai(mom)
    dd.append(('Momentum 10', o0, 1 if o0 > o1 else -1 if o0 < o1 else 0))
    wr = -100 * (hh - c) / rng
    w0, w1 = hai(wr)
    dd.append(('Williams %R 14', w0, 1 if w0 < -80 and w0 > w1 else -1 if w0 > -20 and w0 < w1 else 0))
    dem = lambda ds: {'mua': sum(1 for x in ds if x[2] > 0), 'ban': sum(1 for x in ds if x[2] < 0), 'trung': sum(1 for x in ds if x[2] == 0)}  # noqa: E731
    dm = sum(x[2] for x in ma) / len(ma)
    do = sum(x[2] for x in dd) / len(dd)
    tong = (dm + do) / 2
    out = {'d': round(tong, 3), 'm': round(dm, 3), 'o': round(do, 3), 'rsi': _so(r0, 1), 'adx': _so(a0, 1), 'atr': _so(float(atr.iloc[-1]), 8)}
    if chi_tiet:
        out.update(nhan=nhan_kt(tong), nhan_ma=nhan_kt(dm), nhan_dd=nhan_kt(do), dem_ma=dem(ma), dem_dd=dem(dd), gia=gia,
                   ma=[{'ten': t, 'gt': _so(v, 8), 'p': p} for t, v, p in ma], dd=[{'ten': t, 'gt': _so(v, 4), 'p': p} for t, v, p in dd])
    return out


def bien_dong_theo_gio(t, h, l, lech_gio: int = 7) -> dict:
    """Biên độ trung bình (cao − thấp) của nến H1 theo giờ trong ngày (giờ địa phương = UTC + lech_gio) và theo thứ trong tuần."""
    gio = [[] for _ in range(24)]
    thu: dict = {}
    for ts, hi, lo in zip(t, h, l):
        d = datetime.fromtimestamp(int(ts), timezone.utc) + timedelta(hours=lech_gio)
        gio[d.hour].append(float(hi) - float(lo))
        thu.setdefault(d.weekday(), {}).setdefault(d.date(), []).append((float(hi), float(lo)))
    tb = lambda v: sum(v) / len(v) if v else None                    # noqa: E731
    ngay = {k: tb([max(x[0] for x in ds) - min(x[1] for x in ds) for ds in v.values() if len(ds) >= 12]) for k, v in thu.items()}
    return {'gio': [{'h': i, 'tb': tb(v), 'n': len(v)} for i, v in enumerate(gio)],
            'thu': [{'t': k, 'tb': ngay.get(k)} for k in range(7) if ngay.get(k) is not None]}


def _mt5(g: dict):
    """Phiên MT5 đang nối (None nếu chưa bật hoặc không nối được). Bài kiểm thay hàm này bằng một MT5 giả."""
    if song._tt.get('mt5') is None and song.khung_song(g) is None:
        return None
    return song._tt.get('mt5')


# --------------------------------------------------------------------------- lịch tin kinh tế
_LICH: dict = {}


def lich_tin(cfg: dict, now: datetime | None = None, lui_gio: int = 12, toi_ngay: int = 7) -> dict:
    """Sự kiện kinh tế quanh lúc này từ tệp lịch MT5 mà EA xuất ra (`gia.lich_tin`, giờ UTC). Nhớ kết quả đọc, chỉ đọc lại khi tệp đổi."""
    now = now or datetime.now(timezone.utc)
    p = (cfg.get('gia') or {}).get('lich_tin')
    if not p:
        return {'co': False, 'ly_do': 'chưa khai tệp lịch tin (gia.lich_tin)', 'ds': []}
    f = Path(os.path.expandvars(p))
    try:
        st = f.stat()
    except OSError:
        return {'co': False, 'ly_do': f'không thấy tệp lịch tin {f.name}', 'ds': []}
    key = (str(f), st.st_mtime_ns, st.st_size)
    if _LICH.get('key') != key:
        rows = []
        with f.open(encoding='utf-8-sig', newline='') as fh:
            for r in csv.DictReader(fh):
                try:
                    t = datetime.strptime(r['time'].strip(), '%Y.%m.%d %H:%M').replace(tzinfo=timezone.utc)
                    rows.append((t, r.get('currency', '').strip().upper(), int(float(r.get('importance') or 0)),
                                 r.get('event', '').strip(), r.get('country', '').strip()))
                except (KeyError, ValueError):
                    continue
        rows.sort(key=lambda x: x[0])
        _LICH.update(key=key, rows=rows, sua=datetime.fromtimestamp(st.st_mtime, timezone.utc))
    rows = _LICH['rows']
    a, b = now - timedelta(hours=lui_gio), now + timedelta(days=toi_ngay)
    ds = [{'t': t.isoformat(), 'tien': c, 'muc': m, 'ten': e, 'nuoc': n} for t, c, m, e, n in rows if a <= t <= b and m >= 2]
    het = rows[-1][0] if rows else None
    tien = sorted({r[1] for r in rows[-2000:]})
    return {'co': True, 'ds': ds, 'phu_toi': het.isoformat() if het else None, 'tien_te': tien,
            'sap_het': het is None or het < now + timedelta(days=3), 'sua_luc': _LICH['sua'].isoformat()}


def lich_tong(cfg: dict, goc: Path, now: datetime | None = None, lui_gio: int = 12, toi_ngay: int = 7) -> dict:
    """Lịch cho trang Thị trường: lịch nhiều đồng tiền tải từ mạng (lich_mang.py) cộng phần lịch USD của EA nằm SAU chỗ lịch mạng còn phủ.
    Không có lịch mạng (tắt, chưa tải được) thì trả nguyên lịch của EA. Mỗi sự kiện có trường `nguon`: 'mang' hoặc 'ea'."""
    from . import lich_mang                                                  # noqa: PLC0415
    now = now or datetime.now(timezone.utc)
    ea = lich_tin(cfg, now, lui_gio, toi_ngay)
    lm = cfg.get('lich_mang') or {}
    mang = lich_mang.doc(cfg, goc).get('ds', []) if lm.get('bat', True) else []
    tt = {**lich_mang.trang_thai(), 'bat': bool(lm.get('bat', True)), 'so': len(mang)}
    for e in ea.get('ds', []):
        e['nguon'] = 'ea'
    if not mang:
        return {**ea, 'mang': tt}
    a, b = (now - timedelta(hours=lui_gio)).isoformat(), (now + timedelta(days=toi_ngay)).isoformat()
    het_mang = max(e['t'] for e in mang)
    ds = [{**e, 'nguon': 'mang'} for e in mang if a <= e['t'] <= b]
    ds += [e for e in ea.get('ds', []) if e['t'] > het_mang]
    ds.sort(key=lambda e: (e['t'], -e['muc'], e['tien']))
    phu = max([het_mang] + ([ea['phu_toi']] if ea.get('phu_toi') else []))
    moi = bool(tt.get('lan_tai')) and not tt.get('loi')
    return {'co': True, 'ds': ds, 'phu_toi': phu, 'tien_te': sorted({e['tien'] for e in ds}), 'mang': tt, 'ea': {k: ea.get(k) for k in ('co', 'phu_toi', 'sua_luc', 'ly_do')},
            'sap_het': not moi and phu < (now + timedelta(days=3)).isoformat(), 'sua_luc': ea.get('sua_luc')}


# --------------------------------------------------------------------------- bộ máy giá
class BangGia:
    """Giữ bảng giá của mọi mã và báo cho các luồng SSE. `lay_cfg()` trả cấu hình hiện tại; `mt5_fn(g)` trả phiên MT5 (thay được khi kiểm)."""

    def __init__(self, lay_cfg, chu_ky: float = 0.5, mt5_fn=None):
        self._lay_cfg, self.chu_ky = lay_cfg, max(0.02, float(chu_ky))       # một lượt đọc 88 mã chỉ ~2 ms: đọc dày được, giá đi theo tick
        self._mt5_fn = mt5_fn or _mt5
        self._dk = threading.Condition()
        self.phien = 0                      # tăng mỗi khi có giá mới hoặc trạng thái đổi
        self.gia: dict = {}                 # mã -> [bid, ask, giây_ms của tick]
        self.doi: dict = {}                 # mã -> phiên lần cuối giá đổi
        self.dac_ta: dict = {}              # mã -> thông số hợp đồng
        self.moc: dict = {}                 # mã -> mốc giá (đổi chậm)
        self.tuong_quan: dict | None = None
        self.tai_khoan: dict = {}
        self.san_sang, self.ly_do = False, 'đang khởi động'
        self.ly_do_moc: str | None = None
        self.da_them: set = set()
        self._luc = {'dac_ta': 0.0, 'moc': 0.0, 'tq': 0.0, 'kt': 0.0}
        self.kt: dict = {}                  # mã -> {khung: tóm tắt chỉ báo kỹ thuật}
        self._bd: dict = {}                 # mã -> (lúc, biến động theo giờ)
        self._chay = False

    # ---- vòng nền
    def start(self) -> 'BangGia':
        if not self._chay:
            self._chay = True
            threading.Thread(target=self._vong_gia, name='bang-gia', daemon=True).start()
            threading.Thread(target=self._vong_moc, name='bang-gia-moc', daemon=True).start()
        return self

    def _cfg(self) -> tuple[dict, dict]:
        cfg = self._lay_cfg()
        return cfg['gia'], cfg.get('thi_truong') or {}

    def _vong_gia(self) -> None:
        while self._chay:
            try:
                self.doc_gia()
            except Exception as e:                                   # noqa: BLE001 - vòng nền không được chết
                self._dat_trang_thai(False, f'{type(e).__name__}: {e}')
            time.sleep(self.chu_ky if self.san_sang else 5.0)

    def _vong_moc(self) -> None:
        while self._chay:
            try:
                self.doc_moc()
            except Exception as e:                                   # noqa: BLE001
                self.ly_do_moc = f'{type(e).__name__}: {e}'
            time.sleep(5.0)

    def _dat_trang_thai(self, ok: bool, ly_do: str | None = None) -> None:
        with self._dk:
            if ok != self.san_sang or (not ok and ly_do != self.ly_do):
                self.san_sang, self.ly_do = ok, (None if ok else ly_do)
                self.phien += 1
                self._dk.notify_all()

    # ---- đọc giá (nhanh)
    def doc_gia(self) -> int:
        """Một lượt đọc tick của mọi mã đã biết. Trả số mã có giá mới."""
        g, _ = self._cfg()
        mt5 = self._mt5_fn(g)
        if mt5 is None:
            self._dat_trang_thai(False, song.ly_do() or 'chưa nối được MT5')
            return 0
        if not self.dac_ta:                                          # lượt đầu: cần danh sách mã trước
            self.doc_dac_ta(mt5)
        moi, co = {}, 0
        with song._khoa:
            for ten in self.dac_ta:
                t = mt5.symbol_info_tick(ten)
                if t is None or not t.bid:
                    continue
                co += 1
                v = [float(t.bid), float(t.ask or t.bid), int(getattr(t, 'time_msc', 0) or int(t.time) * 1000)]
                if self.gia.get(ten) != v:
                    moi[ten] = v
        if self.dac_ta and not co:                                   # MT5 không trả tick nào: có thể vừa mất kết nối; để song.py soát và nối lại
            song.khung_song(g)
            self._dat_trang_thai(False, song.ly_do() or 'MT5 không trả giá của mã nào (mất kết nối với máy chủ của sàn?)')
            return 0
        with self._dk:
            doi = bool(moi) or not self.san_sang
            if moi:
                self.phien += 1
                for ten, v in moi.items():
                    self.gia[ten] = v
                    self.doi[ten] = self.phien
            if not self.san_sang:
                self.san_sang, self.ly_do = True, None
                self.phien += 1
            if doi:
                self._dk.notify_all()
        return len(moi)

    # ---- thông số hợp đồng (chậm)
    def doc_dac_ta(self, mt5=None) -> int:
        g, tt = self._cfg()
        mt5 = mt5 or self._mt5_fn(g)
        if mt5 is None:
            return 0
        them = bool(tt.get('them_vao_market_watch', False))
        out = {}
        with song._khoa:
            ds = list(mt5.symbols_get() or [])
            ai = mt5.account_info()
        for s in ds:
            path = getattr(s, 'path', '') or ''
            if path.lower().startswith('refsymbols') or getattr(s, 'trade_mode', 4) == 0:
                continue                                             # mã tham chiếu hoặc sàn tắt giao dịch: bỏ
            if not getattr(s, 'visible', False):
                if not them:
                    continue
                if s.name not in self.da_them:
                    with song._khoa:
                        ok = mt5.symbol_select(s.name, True)
                    if ok:
                        self.da_them.add(s.name)
                    else:
                        continue
            lop = phan_loai(s.name, path)
            d = int(s.digits)
            diem = float(s.point)
            tv, ts = float(getattr(s, 'trade_tick_value', 0) or 0), float(getattr(s, 'trade_tick_size', 0) or 0)
            gt1 = tv / ts if ts else None                            # giá trị 1,0 giá cho 1 lot, theo tiền tài khoản
            pip = kich_thuoc_pip(lop, d, diem)
            ky_quy = None
            try:
                gia_tham = float(getattr(s, 'ask', 0) or 0) or (self.gia.get(s.name) or [0, 0])[1]
                if gia_tham:
                    with song._khoa:
                        ky_quy = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, s.name, 1.0, gia_tham)
            except Exception:                                        # noqa: BLE001 - thiếu ký quỹ thì để trống
                ky_quy = None
            swm = int(getattr(s, 'swap_mode', 0) or 0)
            g0 = goc(s.name)
            out[s.name] = {
                'ma': s.name, 'goc': g0, 'ten': getattr(s, 'description', '') or g0, 'lop': lop, 'biet_danh': BIET_DANH.get(g0.upper(), ''),
                'so_le': d, 'diem': diem, 'pip': pip, 'co_hd': _so(getattr(s, 'trade_contract_size', None)),
                'gt1': _so(gt1, 6), 'gt_pip': _so(gt1 * pip, 4) if gt1 and pip else None, 'gt_diem': _so(gt1 * diem, 6) if gt1 else None,
                'lot_min': _so(getattr(s, 'volume_min', None)), 'lot_buoc': _so(getattr(s, 'volume_step', None)), 'lot_max': _so(getattr(s, 'volume_max', None)),
                'tien_goc': getattr(s, 'currency_base', ''), 'tien_lai': getattr(s, 'currency_profit', ''), 'tien_kq': getattr(s, 'currency_margin', ''),
                'kieu_tinh': KIEU_TINH.get(int(getattr(s, 'trade_calc_mode', -1)), str(getattr(s, 'trade_calc_mode', ''))),
                'ky_quy_1lot': _so(ky_quy, 2), 'muc_dung': int(getattr(s, 'trade_stops_level', 0) or 0),
                'swap': {'dai': _so(getattr(s, 'swap_long', None)), 'ngan': _so(getattr(s, 'swap_short', None)), 'kieu': SWAP_KIEU.get(swm, str(swm)),
                         'bat': swm != 0, 'ngay_3': THU[int(getattr(s, 'swap_rollover3days', 3)) % 7],
                         'usd_dai': _so(s.swap_long * diem * gt1, 2) if swm == 1 and gt1 else (_so(s.swap_long, 2) if swm == 4 else None),
                         'usd_ngan': _so(s.swap_short * diem * gt1, 2) if swm == 1 and gt1 else (_so(s.swap_short, 2) if swm == 4 else None)},
            }
            if lop.startswith('fx'):
                out[s.name]['cap'] = [g0[:3].upper(), g0[3:6].upper()]
        with self._dk:
            self.dac_ta = out
            if ai is not None:
                self.tai_khoan = {'tien': getattr(ai, 'currency', 'USD'), 'don_bay': int(getattr(ai, 'leverage', 0) or 0),
                                  'goi_ky_quy': _so(getattr(ai, 'margin_so_call', None)), 'dung_lenh': _so(getattr(ai, 'margin_so_so', None)),
                                  'dung_lenh_tien': int(getattr(ai, 'margin_so_mode', 0) or 0) == 1,   # 1 = mức gọi/đóng lệnh tính bằng tiền, không phải %
                                  'san': getattr(ai, 'company', '')}
            self.phien += 1
            self._dk.notify_all()
        self._luc['dac_ta'] = time.monotonic()
        return len(out)

    # ---- mốc giá (chậm)
    def _rates(self, mt5, ten: str, tf: str, n: int):
        with song._khoa:
            r = mt5.copy_rates_from_pos(ten, getattr(mt5, 'TIMEFRAME_' + tf), 0, n)
        return r if r is not None and len(r) else None

    def doc_moc(self, bat_buoc: bool = False) -> int:
        g, tt = self._cfg()
        mt5 = self._mt5_fn(g)
        if mt5 is None:
            return 0
        mono = time.monotonic()
        if bat_buoc or not self.dac_ta or mono - self._luc['dac_ta'] > 60:
            self.doc_dac_ta(mt5)
        if not bat_buoc and mono - self._luc['moc'] < float(tt.get('moc_giay', 30)):
            return 0
        n = 0
        for ten in list(self.dac_ta):
            try:
                m = self._moc_mot(mt5, ten)
            except Exception:                                        # noqa: BLE001 - một mã lỗi không chặn mã khác
                continue
            if m:
                with self._dk:
                    self.moc[ten] = m
                n += 1
        self._luc['moc'] = time.monotonic()
        if bat_buoc or mono - self._luc['kt'] > float(tt.get('ky_thuat_giay', 60)):
            for ten in list(self.dac_ta):
                kq = {}
                for tf in KHUNG_KT:
                    try:
                        r = self._rates(mt5, ten, tf, 260)
                        if r is not None:
                            x = ky_thuat(r['open'], r['high'], r['low'], r['close'])
                            if x:
                                kq[tf] = x
                    except Exception:                                # noqa: BLE001
                        continue
                if kq:
                    with self._dk:
                        self.kt[ten] = kq
            self._luc['kt'] = time.monotonic()
        if bat_buoc or mono - self._luc['tq'] > 600 or self.tuong_quan is None:
            try:
                self.tuong_quan = self.tinh_tuong_quan(mt5)
            except Exception as e:                                   # noqa: BLE001
                self.tuong_quan = {'loi': f'{type(e).__name__}: {e}'}
            self._luc['tq'] = time.monotonic()
        with self._dk:
            self.phien += 1
            self._dk.notify_all()
        return n

    def _moc_mot(self, mt5, ten: str) -> dict | None:
        d = self.dac_ta[ten]['so_le']
        m5, d1 = self._rates(mt5, ten, 'M5', 49), self._rates(mt5, ten, 'D1', 22)
        if m5 is None or d1 is None:
            return None
        w1, mn = self._rates(mt5, ten, 'W1', 1), self._rates(mt5, ten, 'MN1', 1)
        c5 = [float(x) for x in m5['close']]
        hom = d1[-1]
        xong = d1[:-1]
        adr = [float(h - l) for h, l in zip(xong['high'][-14:], xong['low'][-14:])]
        return {
            'luc_nen': int(m5['time'][-1]),
            'tia': [round(v, d) for v in c5],
            'ref': {'1h': round(c5[-13], d) if len(c5) >= 13 else None, '4h': round(c5[0], d) if len(c5) >= 49 else None,
                    'ngay': round(float(xong['close'][-1]), d) if len(xong) else None,
                    'tuan': round(float(w1['open'][-1]), d) if w1 is not None else None,
                    'thang': round(float(mn['open'][-1]), d) if mn is not None else None},
            'hom_nay': {'mo': round(float(hom['open']), d), 'cao': round(float(hom['high']), d), 'thap': round(float(hom['low']), d), 't': int(hom['time'])},
            'hom_qua': ({'cao': round(float(xong['high'][-1]), d), 'thap': round(float(xong['low'][-1]), d), 'dong': round(float(xong['close'][-1]), d),
                         'mo': round(float(xong['open'][-1]), d)} if len(xong) else None),
            'adr': round(sum(adr) / len(adr), d) if adr else None,
        }

    def tinh_tuong_quan(self, mt5, khung: str = 'H1', n: int = 241) -> dict | None:
        """Tương quan Pearson của lợi suất log trên `n` nến, chỉ những giờ mọi mã cùng có giá."""
        import numpy as np                                          # noqa: PLC0415
        import pandas as pd                                         # noqa: PLC0415
        theo_goc = {}
        for ten, s in self.dac_ta.items():
            theo_goc.setdefault(s['goc'].upper(), ten)
        chon = [theo_goc[k] for k in TUONG_QUAN_MA if k in theo_goc]
        cot = {}
        for ten in chon:
            r = self._rates(mt5, ten, khung, n)
            if r is not None and len(r) > 60:
                cot[ten] = pd.Series([float(x) for x in r['close']], index=[int(x) for x in r['time']])
        if len(cot) < 3:
            return None
        df = pd.DataFrame(cot).dropna()
        lr = np.log(df).diff().dropna()
        if len(lr) < 50:
            return {'loi': f'chỉ có {len(lr)} giờ chung giữa các mã, chưa đủ để tính'}
        c = lr.corr().round(2)
        ma = list(c.columns)
        return {'ma': ma, 'goc': [self.dac_ta[m]['goc'] for m in ma], 'ma_tran': [[_so(c.loc[a, b], 2) for b in ma] for a in ma],
                'so_nen': len(lr), 'khung': khung, 'luc': datetime.now(timezone.utc).isoformat()}

    # ---- dữ liệu ra
    def anh_chup(self) -> dict:
        """Toàn bộ bảng: thông số + mốc + giá hiện tại, cho /api/thi-truong."""
        with self._dk:
            ds = []
            for ten, s in self.dac_ta.items():
                ds.append({**s, **(self.moc.get(ten) or {}), 'q': self.gia.get(ten), 'kt': self.kt.get(ten)})
            return {'san_sang': self.san_sang, 'ly_do': self.ly_do, 'phien': self.phien, 'luc': datetime.now(timezone.utc).isoformat(),
                    'lop': LOP, 'tien_te': TIEN_TE, 'tai_khoan': self.tai_khoan, 'ds': ds, 'tuong_quan': self.tuong_quan,
                    'da_them_vao_market_watch': len(self.da_them)}

    def _goi_tin(self, tu: int) -> dict:
        q = {ten: v for ten, v in self.gia.items() if tu < 0 or self.doi.get(ten, 0) > tu}
        return {'v': self.phien, 's': self.san_sang, 'ly': self.ly_do, 'q': q, 'day_du': tu < 0}

    def luong(self, gui, het_giay: float = 600.0, nhip: float = 0.03, cho: float = 15.0) -> None:
        """Ghi luồng Server-Sent Events: lần đầu gửi đủ giá, sau đó chỉ các mã có giá mới, nhiều nhất `1/nhip` lần mỗi giây.
        `gui(bytes)` ném lỗi khi trình duyệt đóng kết nối: hàm dừng. Hết `het_giay` thì đóng để trình duyệt tự nối lại (EventSource)."""
        gui(b'retry: 2000\n\n')
        v, t0 = -1, time.monotonic()
        while time.monotonic() - t0 < het_giay:
            with self._dk:
                if v >= 0:
                    self._dk.wait_for(lambda: self.phien != v, timeout=cho)   # noqa: B023 - wait_for gọi hàm ngay trong khối khóa, v chưa đổi
                if self.phien == v:
                    goi = None
                else:
                    goi = self._goi_tin(v)
                    v = self.phien
            if goi is None:
                gui(b': giu-ket-noi\n\n')
                continue
            gui(b'event: gia\ndata: ' + json.dumps(goi, ensure_ascii=False, separators=(',', ':')).encode('utf-8') + b'\n\n')
            time.sleep(nhip)

    def chi_tiet_ky_thuat(self, ma: str) -> dict:
        """Bảng chỉ báo đầy đủ của một mã trên bốn khung, tính lại ngay lúc hỏi (gồm cả nến đang chạy), kèm pivot cổ điển của ngày trước."""
        g, _ = self._cfg()
        if ma not in self.dac_ta:
            raise ValueError(f'không có mã {ma}')
        mt5 = self._mt5_fn(g)
        if mt5 is None:
            raise ValueError(f'chưa nối được MT5 ({song.ly_do() or "chưa nối"})')
        out = {'ma': ma, 'goc': self.dac_ta[ma]['goc'], 'so_le': self.dac_ta[ma]['so_le'], 'khung': {}, 'luc': datetime.now(timezone.utc).isoformat()}
        for tf in KHUNG_KT:
            r = self._rates(mt5, ma, tf, 260)
            if r is not None:
                x = ky_thuat(r['open'], r['high'], r['low'], r['close'], chi_tiet=True)
                if x:
                    out['khung'][tf] = x
        return out

    def bien_dong(self, ma: str, so_nen: int = 720) -> dict:
        """Biên độ trung bình theo giờ (giờ Việt Nam) và theo thứ trên khoảng 30 ngày nến H1 gần nhất. Nhớ 10 phút."""
        g, _ = self._cfg()
        if ma not in self.dac_ta:
            raise ValueError(f'không có mã {ma}')
        cu = self._bd.get(ma)
        if cu and time.monotonic() - cu[0] < 600:
            return cu[1]
        mt5 = self._mt5_fn(g)
        if mt5 is None:
            raise ValueError(f'chưa nối được MT5 ({song.ly_do() or "chưa nối"})')
        with song._khoa:
            r = mt5.copy_rates_from_pos(ma, mt5.TIMEFRAME_H1, 1, so_nen)
        if r is None or not len(r):
            raise ValueError(f'MT5 không trả nến H1 của {ma}')
        out = {'ma': ma, 'goc': self.dac_ta[ma]['goc'], 'so_nen': len(r), 'tu': int(r['time'][0]), 'den': int(r['time'][-1]),
               **bien_dong_theo_gio(r['time'], r['high'], r['low'])}
        self._bd[ma] = (time.monotonic(), out)
        return out

    def tinh(self, ma: str, loai: str, lot: float, vao: float, ra: float | None = None) -> dict:
        """Ký quỹ và lãi lỗ chính xác theo MT5 (hai hàm tính thuần, không gửi lệnh)."""
        g, _ = self._cfg()
        if ma not in self.dac_ta:
            raise ValueError(f'không có mã {ma}')
        if loai not in ('mua', 'ban') or not (0 < lot <= 1000) or not (vao > 0) or (ra is not None and not ra > 0):
            raise ValueError('tham số không hợp lệ')
        mt5 = self._mt5_fn(g)
        if mt5 is None:
            raise ValueError(f'chưa nối được MT5 ({song.ly_do() or "chưa nối"})')
        kieu = mt5.ORDER_TYPE_BUY if loai == 'mua' else mt5.ORDER_TYPE_SELL
        with song._khoa:
            kq = mt5.order_calc_margin(kieu, ma, float(lot), float(vao))
            lai = mt5.order_calc_profit(kieu, ma, float(lot), float(vao), float(ra)) if ra is not None else None
        return {'ma': ma, 'ky_quy': _so(kq, 2), 'lai': _so(lai, 2), 'tien': self.tai_khoan.get('tien', 'USD')}


_BANG: dict = {}


def bang(lay_cfg=None) -> BangGia | None:
    """Bảng giá dùng chung của webapp (None nếu chưa tạo)."""
    if lay_cfg is not None and 'b' not in _BANG:
        cfg = lay_cfg()
        tt = cfg.get('thi_truong') or {}
        if not tt.get('bat', True):
            return None
        _BANG['b'] = BangGia(lay_cfg, tt.get('chu_ky_giay', 0.5))
    return _BANG.get('b')
