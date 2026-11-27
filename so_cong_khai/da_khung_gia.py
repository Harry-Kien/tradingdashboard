"""Gói nến nhẹ cho nhiều biểu đồ: chỉ khung được chọn, OHLC và EMA20/50."""
from . import da_ma, gia, song


def goi(cfg: dict, ma: str, tf: str, n: int = 400) -> dict:
    if tf not in da_ma.SO_NEN:
        raise ValueError(f'khung không hỗ trợ: {tf}')
    ma = ma or da_ma.ma_vang(cfg)
    n = max(50, min(int(n), 600))
    mt = da_ma._mt5(cfg['gia'])
    if mt is None:
        raise gia.ChuaCoGia('MT5 chưa nối; nhiều biểu đồ cần nguồn giá trực tiếp')
    with song._khoa:
        symbols = da_ma._hien(mt)
        if ma not in symbols:
            raise ValueError(f'mã {ma} không có trong Market Watch của MT5')
        dg = int(symbols[ma].digits)
        bars = da_ma._nen(mt, ma, tf, n + 150)
        tick = mt.symbol_info_tick(ma)
        live = da_ma._nen(mt, ma, tf, 1, 0)
    view = bars.iloc[-n:]
    number = lambda v: da_ma._lam_tron(v, dg)  # noqa: E731
    out = {'ma': ma, 'tf': tf, 'so_le': dg, 'nguon': 'mt5',
           'candles': [[gia._giay(t), *[number(v) for v in row]] for t, row in zip(view.index, view[['open', 'high', 'low', 'close']].to_numpy())],
           'bid': number(tick.bid) if tick else None, 'ask': number(tick.ask) if tick else None,
           'tick_ms': int(getattr(tick, 'time_msc', 0) or tick.time * 1000) if tick else None}
    for span in (20, 50):
        out[f'ema{span}'] = [number(v) for v in bars['close'].ewm(span=span, adjust=False, min_periods=span).mean().iloc[-n:]]
    if len(live) and live.index[-1] > view.index[-1]:
        out['dang_chay'] = [gia._giay(live.index[-1]), *[number(v) for v in live[['open', 'high', 'low', 'close']].iloc[-1]]]
    return out
