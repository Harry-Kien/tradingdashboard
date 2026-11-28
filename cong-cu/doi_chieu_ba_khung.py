# -*- coding: utf-8 -*-
"""Đối chiếu phép chấm luật xu hướng ba khung của chủ dự án (tools.ai_trend_news.simulate, chỉ đọc) với một bộ chấm độc lập: Backtesting.py.

Cùng danh sách quyết định của luật (tools.ai_trend_history.decisions), cùng nến 1 phút, cùng quy tắc: mỗi lúc một lệnh, vào ở giá mở nến 1 phút
đầu tiên sau khi nến M15 đóng, chốt cách giá vào 5, dừng cách 20, giữ tới khi chạm một trong hai, bỏ tín hiệu trong 15 phút quanh tin USD mạnh.
Spread và phí đặt bằng 0 ở cả hai bên để chỉ so phần khớp và thoát lệnh.

Chỗ hai bộ chấm xử khác nhau, được đếm riêng: khi nến mở cửa nhảy qua mức dừng lỗ hoặc chốt lời, bộ chấm của dự án tính thoát đúng ở mức đã đặt
(−20 hoặc +5), còn Backtesting.py tính thoát ở giá mở. Ở phía dừng lỗ, con số của Backtesting.py sát thực tế hơn; tổng chênh lệch cho biết bộ chấm
của dự án nhẹ tay bao nhiêu. Công cụ này không sửa gì trong dự án của chủ dự án. Chỉ đọc tệp nến; không nối MT5.

    python -X utf8 cong-cu/doi_chieu_ba_khung.py [năm bắt đầu, mặc định 2015]
"""
import json
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import gia, hoc  # noqa: E402


def chay_bt(m1: pd.DataFrame, lenh: dict):
    df = pd.DataFrame({'Open': m1['open'].to_numpy(), 'High': m1['high'].to_numpy(), 'Low': m1['low'].to_numpy(), 'Close': m1['close'].to_numpy()},
                      index=m1.index.tz_localize(None))
    tu_choi = []

    class BaKhung(Strategy):
        def init(self):
            pass

        def next(self):
            if self.position:
                return
            x = lenh.get(len(self.data) - 1)
            if x and not self.orders:
                try:
                    (self.buy if x[0] else self.sell)(size=1, sl=x[1], tp=x[2])
                except ValueError:
                    tu_choi.append(len(self.data) - 1)

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        st = Backtest(df, BaKhung, cash=1e9, commission=0.0, spread=0.0, trade_on_close=False, exclusive_orders=False, finalize_trades=False).run()
    return st['_trades'], len(tu_choi)


if __name__ == '__main__':
    tu_nam = int(sys.argv[1]) if len(sys.argv) > 1 else 2015
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    gia._nap_ma(g)
    from ai import rule_trend as RT, snapshot as SN                        # noqa: E402 - mã của chủ dự án, chỉ đọc
    from tools import ai_trend_history as TH, ai_trend_news as TN          # noqa: E402

    t0 = time.time()
    m1 = hoc._m1_dai(g, tu_nam)
    fr = hoc._khung(m1, g)
    tin, _ = SN.load_high_usd_news(Path(os.path.expandvars(g['lich_tin'])))

    def tran(df):
        out = df.reset_index(names='time')
        out['time'] = out['time'].dt.tz_localize(None)
        return out
    frames = {tf: tran(fr[tf]) for tf in ('D1', 'H4', 'H1', 'M15')}
    mn = tran(m1)
    decs = TH.decisions(frames, mn['time'].iloc[0], mn['time'].iloc[-1] + pd.Timedelta(minutes=1))
    cua = TN.Windows([pd.Timestamp(t).tz_convert('UTC').tz_localize(None) for t in tin])
    print(f'Vàng từ {tu_nam}: {len(m1):,} nến 1 phút · {len(decs):,} quyết định của luật · spread và phí bằng 0 ở cả hai bộ chấm · {time.time() - t0:.0f} giây', flush=True)

    # bộ chấm của chủ dự án, spread 0 và phí 0
    cu_sp, cu_ex = TH.SPREAD, TH.EXTRA
    TH.SPREAD = TH.EXTRA = 0.0
    try:
        a = pd.DataFrame(TN.simulate(decs, mn, cua, skip_news=True, news_costs=False))
    finally:
        TH.SPREAD, TH.EXTRA = cu_sp, cu_ex
    a['vao_t'] = [mn['time'].iloc[int(np.searchsorted(mn['time'].values, np.datetime64(t)))] for t in a['t']]      # nến 1 phút mà lệnh khớp
    a['ra_t'] = pd.to_datetime(a['t_exit'])

    # Backtesting.py: cùng quyết định (đã bỏ tín hiệu lúc có tin), lệnh đặt ở nến j−1 để khớp ở giá mở nến j
    T = mn['time'].values
    O = m1['open'].to_numpy(dtype=float)
    lenh = {}
    for t, side in decs:
        if cua.covers(t):
            continue
        j = int(np.searchsorted(T, np.datetime64(pd.Timestamp(t)), side='left'))
        if j >= len(T) or j == 0 or pd.Timestamp(T[j]) - pd.Timestamp(t) > TH.MAX_ENTRY_LAG:
            continue
        mua = side == 'MUA'
        d = 1 if mua else -1
        lenh.setdefault(j - 1, (mua, round(float(O[j]) - d * RT.SL_USD, 2), round(float(O[j]) + d * RT.TP_USD, 2)))
    t1 = time.time()
    b, tu_choi = chay_bt(m1, lenh)
    b = b.assign(vao_t=pd.to_datetime(b['EntryTime']), ra_bt=pd.to_datetime(b['ExitTime']), usd_bt=(b['ExitPrice'] - b['EntryPrice']) * np.sign(b['Size']))
    print(f'Bộ chấm của dự án: {len(a):,} lệnh, tổng {a["usd"].sum():+.2f} giá · Backtesting.py: {len(b):,} lệnh, tổng {b["usd_bt"].sum():+.2f} giá'
          f' · {time.time() - t1:.0f} giây' + (f' · Backtesting.py từ chối {tu_choi} lệnh' if tu_choi else ''), flush=True)

    m = a.merge(b, on='vao_t', how='outer', indicator=True)
    ca = m[m['_merge'] == 'both'].copy()
    le = m[m['_merge'] != 'both']
    mo = pd.Series(O, index=m1.index.tz_localize(None))
    cung_ra = (ca['ra_t'] - ca['ra_bt']).abs() <= pd.Timedelta(minutes=1)
    khop = cung_ra & ((ca['usd'] - ca['usd_bt']).abs() <= 0.011)
    tai_mo = np.abs(ca['ExitPrice'].to_numpy() - mo.reindex(ca['ra_bt']).to_numpy()) < 1e-6
    sl_nhay = ~khop & cung_ra & tai_mo & (ca['usd'] < 0) & (ca['usd_bt'] < ca['usd'])          # mở cửa nhảy qua dừng lỗ: thực tế lỗ hơn 20
    tp_nhay = ~khop & cung_ra & tai_mo & (ca['usd'] > 0) & (ca['usd_bt'] > ca['usd'])          # mở cửa nhảy qua chốt lời: thực tế lãi hơn 5
    khac = ~(khop | sl_nhay | tp_nhay)
    print(f'\nCùng nến vào: {len(ca):,} · chỉ một bên có: {len(le)} · giống hệt (nến thoát và giá thoát): {int(khop.sum()):,} ({khop.mean() * 100:.1f}%)')
    print(f'Mở cửa nhảy qua dừng lỗ: {int(sl_nhay.sum())} lệnh; bộ chấm của dự án tính nhẹ hơn tổng cộng {float((ca["usd"] - ca["usd_bt"])[sl_nhay].sum()):.2f} giá '
          f'(lệnh nặng nhất {float((ca["usd_bt"])[sl_nhay].min()) if sl_nhay.any() else 0:.2f} thay cho −{RT.SL_USD:g})')
    print(f'Mở cửa nhảy qua chốt lời: {int(tp_nhay.sum())} lệnh; bộ chấm của dự án tính thấp hơn tổng cộng {float((ca["usd_bt"] - ca["usd"])[tp_nhay].sum()):.2f} giá')
    print(f'Khác chưa giải thích được: {int(khac.sum())}')
    for _, x in ca[khac].head(5).iterrows():
        print(f'   khác: vào {x["vao_t"]} {x["side"]} · dự án ra {x["ra_t"]} {x["usd"]:+.2f} · Backtesting.py ra {x["ra_bt"]} {x["usd_bt"]:+.2f}')
    for _, x in le.head(5).iterrows():
        print(f'   chỉ {"dự án" if x["_merge"] == "left_only" else "Backtesting.py"}: vào {x["vao_t"]}')
    if tu_choi and len(le):
        print(f'   (Backtesting.py từ chối {tu_choi} lệnh vì giá mở nhảy xa hơn khoảng chốt lời so với giá đóng nến trước; khi đó nó đứng ngoài và nhận tín hiệu kế tiếp,\n'
              f'    nên vài dòng chỉ có ở một bên. Đây là giới hạn của thư viện, không phải lỗi của bộ chấm.)')
    ca['nam'] = ca['vao_t'].dt.year
    print('\nTheo năm (không chi phí): lệnh · tổng theo bộ chấm của dự án · tổng theo Backtesting.py · lệnh nhảy qua dừng lỗ')
    for nam, x in ca.groupby('nam'):
        print(f'   {nam}: {len(x):>5} · {x["usd"].sum():+9.2f} · {x["usd_bt"].sum():+9.2f} · {int(sl_nhay[x.index].sum())}')
    sys.exit(1 if int(khac.sum()) or (len(le) and not tu_choi) else 0)
