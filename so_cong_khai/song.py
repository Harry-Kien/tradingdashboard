"""Giá trực tiếp từ MT5, CHỈ ĐỌC, cho trang biểu đồ.

Hai đường nối, cùng các chốt an toàn: chỉ nối vào một MT5 ĐANG MỞ, không bao giờ tự mở MT5, mặc định chỉ nhận tài khoản demo.
- Máy có mã EA Promax (máy của chủ dự án): dùng đúng hàm nối của dự án đó (tools.ai_signal_loop._attach).
- Máy không có (bản chia sẻ cho người khác): dùng noi_mt5.noi, tự tìm MT5 đang mở và mã vàng của sàn.
Cả hai đường đều được bọc bởi noi_mt5.LechGio: mọi giờ nến và tick đã đổi về UTC dù sàn chạy giờ nào.
Sau khi nối chỉ đọc nến và giá; mô-đun này không có lời gọi đặt lệnh nào. Không nối được thì trả None kèm lý do,
và trang tự dùng kho nến 1 phút (nếu máy có)."""
from __future__ import annotations

import os
import sys
import threading
import time
from datetime import timedelta
from pathlib import Path

from . import noi_mt5

SO_NEN = {'M5': 900, 'M15': 900, 'M30': 400, 'H1': 1000, 'H4': 1000, 'D1': 900}
LUU_LECH = Path(__file__).resolve().parent.parent / 'out' / 'lech-gio-san.json'
_khoa = threading.Lock()
_tt: dict = {'deps': None, 'mt5': None, 'ly_do': 'chưa thử nối', 'thu': 0.0, 'luc': 0.0, 'fr': None}


def ly_do() -> str | None:
    """Vì sao đang không có giá trực tiếp (None khi đang có)."""
    return None if _tt['deps'] is not None else _tt['ly_do']


def thong_tin() -> dict:
    """Mã vàng, đường nối và độ lệch giờ của sàn đang dùng (cho trang tình trạng)."""
    return {'ma': _tt.get('sym'), 'duong': _tt.get('duong'), 'lech_gio': (_tt.get('lech') or 0) / 3600, 'lech_nguon': _tt.get('lech_nguon')}


def _ma_ea(g: dict):
    """(tools.ai_signal_loop, ai.config) của EA Promax nếu máy có mã đó; None nếu không có, hoặc cấu hình ép nối độc lập (gia.mt5.noi = "doc_lap")."""
    if (g.get('mt5') or {}).get('noi') == 'doc_lap':
        return None
    co = False
    for p in g.get('ma_nguon', []):
        p = os.path.expandvars(p)
        if os.path.isdir(p):
            co = True
            if p not in sys.path:
                sys.path.insert(0, p)
    if not co:
        return None
    try:
        from tools import ai_signal_loop as L                    # noqa: PLC0415
        from ai import config as C                               # noqa: PLC0415
    except ImportError:
        return None
    return L, C


def _noi(cfgm: dict, g: dict):
    import MetaTrader5 as mt5                                    # noqa: PLC0415 - chỉ nạp khi bật giá trực tiếp
    ea = _ma_ea(g)
    if ea is not None:
        L, C = ea
        why = L._attach(mt5, os.path.expandvars(cfgm.get('terminal') or ''))
        if why is not None:
            return None, None, str(why)
        ma, duong = C.SYMBOL, 'EA Promax'
    else:
        _, why = noi_mt5.noi(mt5, cfgm)
        if why is not None:
            return None, None, why
        ma, duong = noi_mt5.tim_ma_vang(mt5, g.get('ma_vang')), 'độc lập'
        if ma is None:
            mt5.shutdown()
            return None, None, 'Sàn trong MT5 này không có mã vàng (XAUUSD hoặc GOLD). Ghi đúng tên mã vào gia.ma_vang trong cau-hinh.json.'
        mt5.symbol_select(ma, True)
    lech, nguon = noi_mt5.lech_gio(mt5, cfgm, ma, LUU_LECH)
    m = noi_mt5.LechGio(mt5, lech)                               # mọi giờ đọc ra đã là UTC
    _tt.update(sym=ma, duong=duong, lech=lech, lech_nguon=nguon)
    deps = L._mt5_deps(m, None, None, None, None) if ea is not None else noi_mt5.Doc(m, ma)
    return m, deps, None


def _nen_dang_chay(mt5, sym) -> dict:
    """Cây nến ĐANG CHẠY của từng khung (vị trí 0). Chỉ để vẽ; mọi luật vẫn tính trên nến đã đóng."""
    out = {}
    for tf in SO_NEN:
        r = mt5.copy_rates_from_pos(sym, getattr(mt5, 'TIMEFRAME_' + tf), 0, 1)
        if r is not None and len(r):
            x = r[0]
            out[tf] = [int(x['time']), float(x['open']), float(x['high']), float(x['low']), float(x['close'])]
    return out


def tick(g: dict, tf: str, sym: str | None = None) -> dict | None:
    """Tick mới nhất và cây nến ĐANG CHẠY của một khung, đọc thẳng từ MT5 (mỗi lần dưới 0,1 ms), cho luồng đẩy giá của trang biểu đồ.

    Trả {'ms': giờ tick theo mili giây, 'bid', 'ask', 'nen': [giờ mở, mở, cao, thấp, đóng]}; None khi chưa nối được MT5 hoặc mã chưa có tick.
    Chỉ đọc, chỉ để vẽ: luật vẫn tính trên nến đã đóng qua khung_song."""
    if tf not in SO_NEN:
        raise ValueError(f'khung không hỗ trợ: {tf}')
    if _tt['mt5'] is None and khung_song(g) is None:              # chưa nối: nối theo đúng đường an toàn (có giãn cách thử lại)
        return None
    with _khoa:
        mt5 = _tt['mt5']
        if mt5 is None:
            return None
        sym = sym or _tt.get('sym')
        try:
            t = mt5.symbol_info_tick(sym)
            r = mt5.copy_rates_from_pos(sym, getattr(mt5, 'TIMEFRAME_' + tf), 0, 1)
        except Exception:                                        # noqa: BLE001 - lỗi đọc: lần sau thử lại, khung_song tự nối lại nếu mất phiên
            return None
    if t is None or not t.bid:
        return None
    out = {'ms': int(t.time_msc), 'bid': float(t.bid), 'ask': float(t.ask)}
    if r is not None and len(r):
        x = r[0]
        out['nen'] = [int(x['time']), float(x['open']), float(x['high']), float(x['low']), float(x['close'])]
    return out


def ngat() -> None:
    with _khoa:
        if _tt['mt5'] is not None:
            try:
                _tt['mt5'].shutdown()
            except Exception:                                    # noqa: BLE001
                pass
        _tt.update(deps=None, mt5=None, fr=None, ly_do='đã ngắt')


def khung_song(g: dict, noi=_noi) -> dict | None:
    """Khung nến đã đóng lấy thẳng từ MT5 (cùng dạng với gia.khung) kèm bid, ask. None nếu chưa bật hoặc không nối được."""
    cfgm = g.get('mt5') or {}
    if not cfgm.get('bat'):
        _tt['ly_do'] = 'giá trực tiếp đang tắt trong cấu hình'
        return None
    with _khoa:
        now = time.monotonic()
        if _tt['fr'] is not None and now - _tt['luc'] < float(cfgm.get('nho_giay', 4)):
            return _tt['fr']
        if _tt['deps'] is None:
            if _tt['thu'] and now - _tt['thu'] < float(cfgm.get('thu_lai_giay', 60)):
                return None                                      # vừa thử nối không được: chưa thử lại vội
            _tt['thu'] = now
            try:
                _tt['mt5'], _tt['deps'], why = noi(cfgm, g)
            except Exception as e:                               # noqa: BLE001
                _tt['mt5'], _tt['deps'], why = None, None, f'{type(e).__name__}: {e}'
            if _tt['deps'] is None:
                _tt['ly_do'] = why or 'không nối được MT5'
                return None
        deps = _tt['deps']
        try:
            tick = deps.get_tick()
            fr = {}
            for tf, n in SO_NEN.items():
                df = deps.get_bars(tf, n)
                if df is None or len(df) < 60:
                    raise RuntimeError(f'MT5 chưa trả đủ nến {tf}')
                fr[tf] = df.set_index('time')[['open', 'high', 'low', 'close']]
        except Exception as e:                                   # noqa: BLE001 - mất kết nối: bỏ phiên, lần sau nối lại
            try:
                _tt['mt5'].shutdown()
            except Exception:                                    # noqa: BLE001
                pass
            _tt.update(deps=None, mt5=None, fr=None, ly_do=f'mất kết nối MT5: {e}')
            return None
        het = fr['M5'].index[-1] + timedelta(minutes=5)
        fr['het'] = (tick[2] if tick else het.to_pydatetime())
        fr['nguon'] = 'mt5'
        if tick:
            fr['bid'], fr['ask'] = tick[0], tick[1]
        try:
            fr['dang_chay'] = _nen_dang_chay(_tt['mt5'], _tt.get('sym'))
        except Exception:                                        # noqa: BLE001 - thiếu nến đang chạy thì vẫn vẽ nến đã đóng
            fr['dang_chay'] = {}
        _tt.update(fr=fr, luc=now)
        return fr
