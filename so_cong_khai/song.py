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

# khung CHỈ ĐỂ XEM (phút mỗi nến; MN1 lấy 30 ngày làm bước ước lượng): đọc thẳng từ MT5 khi người dùng chọn, không nằm trong vòng nến của luật
KHUNG_XEM = {'M2': 2, 'M3': 3, 'M10': 10, 'H2': 120, 'H3': 180, 'W1': 10080, 'MN1': 43200}
SO_NEN = {'M1': 1300, 'M5': 900, 'M15': 900, 'M30': 400, 'H1': 1000, 'H4': 1000, 'D1': 900}   # M1: 900 nến xem + 400 nến khởi động chỉ báo
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
            return None, None, 'Sàn trong MT5 này không có mã vàng (XAUUSD hoặc GOLD). Chọn đúng mã vàng ở trang Cài đặt (/cai-dat).'
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
    if tf not in SO_NEN and tf not in KHUNG_XEM:
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


def khoi_luong(tf: str, sym: str | None = None, n: int = 1500) -> dict[int, int] | None:
    """Tick volume (số lần giá đổi trong nến) của n nến ĐÃ ĐÓNG gần nhất, {giờ mở nến (giây UTC): tick volume}. None khi chưa nối MT5 hoặc lỗi đọc.

    Vàng CFD không có khối lượng giao dịch thật; đây chỉ là thước đo độ sôi động. Đọc thẳng từ MT5 (chỉ đọc), nhớ vài giây cho mỗi mã và khung."""
    if tf not in SO_NEN and tf not in KHUNG_XEM:
        raise ValueError(f'khung không hỗ trợ: {tf}')
    with _khoa:
        mt5 = _tt['mt5']
        if mt5 is None:
            return None
        sym = sym or _tt.get('sym')
        k, now, n = (sym, tf), time.monotonic(), int(n)
        nho = _tt.setdefault('kl', {})
        if k in nho and nho[k][2] >= n and now - nho[k][0] < (4 if n <= 2000 else 60):   # đọc nhiều nến cũ: nhớ lâu hơn
            return nho[k][1]
        try:
            r = mt5.copy_rates_from_pos(sym, getattr(mt5, 'TIMEFRAME_' + tf), 1, n)
        except Exception:                                        # noqa: BLE001 - thiếu khối lượng thì biểu đồ vẫn vẽ
            return None
        if r is None or not len(r) or 'tick_volume' not in (r.dtype.names or ()):
            return None
        out = {int(x['time']): int(x['tick_volume']) for x in r}
        nho[k] = (now, out, n)
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
        can_noi = _tt['deps'] is None
        if can_noi:
            if _tt.get('dang_noi') or (_tt['thu'] and now - _tt['thu'] < float(cfgm.get('thu_lai_giay', 60))):
                return None                                      # đang nối ở luồng khác, hoặc vừa thử không được: chưa thử lại vội
            _tt['thu'] = now
            _tt['dang_noi'] = True
    if can_noi:
        # Nối NGOÀI khóa (27/11/2026). Lỗi đã gặp: MT5 vừa mở chưa sẵn sàng, mt5.initialize đứng chờ tới 60 giây trong lúc giữ _khoa,
        # nên mọi trang và API cần giá đều treo theo (webapp như chết) và cứ mỗi 60 giây lại treo lần nữa. Giờ lúc đang nối, các yêu cầu khác
        # trả None ngay (trang dùng kho nến như khi chưa nối), chỉ một luồng nối tại một thời điểm.
        try:
            m, d, why = noi(cfgm, g)
        except Exception as e:                                   # noqa: BLE001
            m, d, why = None, None, f'{type(e).__name__}: {e}'
        with _khoa:
            _tt['dang_noi'] = False
            _tt['mt5'], _tt['deps'] = m, d
            if d is None:
                _tt['ly_do'] = why or 'không nối được MT5'
                return None
    with _khoa:
        now = time.monotonic()
        deps = _tt['deps']
        if deps is None:
            return None
        try:
            tick = deps.get_tick()
            fr = {}
            for tf, n in SO_NEN.items():
                if tf == 'M1':                                   # vòng của EA không có M1: đọc riêng ngay dưới
                    continue
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
        try:                                                     # M1 chỉ để xem: đọc thẳng nến đã đóng; lỗi thì biểu đồ M1 lấy từ kho nến
            r = _tt['mt5'].copy_rates_from_pos(_tt.get('sym'), _tt['mt5'].TIMEFRAME_M1, 1, SO_NEN['M1'])
            if r is not None and len(r) >= 60:
                import pandas as pd                              # noqa: PLC0415
                m1 = pd.DataFrame(r)
                m1.index = pd.to_datetime(m1['time'], unit='s', utc=True)
                fr['M1'] = m1[['open', 'high', 'low', 'close']].astype(float)
        except Exception:                                        # noqa: BLE001
            pass
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
