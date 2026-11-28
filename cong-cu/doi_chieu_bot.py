# -*- coding: utf-8 -*-
"""Đối chiếu phép chấm luật bot tín hiệu của chủ dự án (tinhieu.backtest.simulate và tinhieu.tracker, chỉ đọc) với một bộ chấm độc lập:
Backtesting.py.

Cái được kiểm: phần THOÁT LỆNH và tính lãi lỗ. Cùng nến 1 phút, cùng các lệnh mà bộ chấm của dự án đã vào (giá vào, dừng lỗ, sáu mức chốt lời,
hạn giữ), mỗi lệnh chia đều làm sáu phần, mỗi phần chốt ở một mức, phần còn lại thoát ở dừng lỗ hoặc lúc hết hạn giữ. Spread và trượt giá đặt
bằng 0 ở cả hai bên để chỉ so phần khớp và thoát lệnh.

Cái KHÔNG được kiểm ở đây: việc chọn tín hiệu nào được vào (tối đa ba lệnh cùng lúc, chờ TP1 mới gọi lệnh mới trên cùng khung). Danh sách lệnh
lấy nguyên từ bộ chấm của dự án.

Chỗ hai bộ chấm xử khác nhau, đếm riêng:
- nến mở cửa nhảy qua mức chốt lời: bộ chấm của dự án tính đúng ở mức đã đặt, Backtesting.py tính ở giá mở (có lợi hơn);
- nến hết hạn giữ: bộ chấm của dự án đóng hết ở giá mở nến đó, Backtesting.py còn xét dừng lỗ và chốt lời trong chính nến đó.
Công cụ này không sửa gì trong dự án của chủ dự án. Chỉ đọc tệp nến; không nối MT5.

    python -X utf8 cong-cu/doi_chieu_bot.py [năm bắt đầu, mặc định 2015]
"""
import json
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


def chay_bt(m1: pd.DataFrame, dat: dict, het: dict):
    """dat: {nến j−1: [(số lệnh, mua?, sl, (tp…))]} để khớp ở giá mở nến j. het: {nến trước nến hết hạn: [số lệnh]}."""
    df = pd.DataFrame({'Open': m1['open'].to_numpy(), 'High': m1['high'].to_numpy(), 'Low': m1['low'].to_numpy(), 'Close': m1['close'].to_numpy()},
                      index=m1.index.tz_localize(None))
    tu_choi = set()

    class Bot(Strategy):
        def init(self):
            pass

        def next(self):
            k = len(self.data) - 1
            for n in het.get(k, ()):
                for t in self.trades:
                    if t.tag[0] == n:
                        t.close()
            for n, mua, sl, tps in dat.get(k, ()):
                for i, tp in enumerate(tps):
                    try:
                        (self.buy if mua else self.sell)(size=1, sl=sl, tp=tp, tag=(n, i))
                    except ValueError:
                        tu_choi.add(n)

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        st = Backtest(df, Bot, cash=1e9, commission=0.0, spread=0.0, trade_on_close=False, exclusive_orders=False, hedging=True,
                      finalize_trades=False).run()
    return st['_trades'], tu_choi


if __name__ == '__main__':
    tu_nam = int(sys.argv[1]) if len(sys.argv) > 1 else 2015
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    gia._nap_ma(g)
    from tinhieu import backtest as BT, levels as LV, rules as R          # noqa: E402 - mã của chủ dự án, chỉ đọc

    t0 = time.time()
    m1 = hoc._m1_dai(g, tu_nam)
    fr = hoc._khung(m1, g)
    khung_bot = tuple((cfg.get('kiem_chung') or {}).get('khung_bot', ('M5', 'M15')))
    mb = m1.assign(spread=0.0)
    h1, h4 = BT.resample(mb, '1h'), BT.resample(mb, '4h')
    setups = []
    for tf in khung_bot:
        setups += R.scan(BT.resample(mb, R.TIMEFRAMES[tf]), h1, h4, fr['D1'], tf)

    # Ghi lại tín hiệu mà bộ chấm của dự án dựng (mức dừng lỗ, sáu mức chốt, hạn giữ) bằng cách bọc tạm levels.build trong bộ nhớ; trả lại ngay sau đó.
    ghi, goc_build = {}, LV.build

    def build(setup, bid, ask, now, seq):
        s = goc_build(setup, bid, ask, now, seq)
        if s is not None:
            ghi[(pd.Timestamp(now), s.code)] = s
        return s
    LV.build = build
    try:
        a = BT.simulate(setups, mb, slip=0.0)
    finally:
        LV.build = goc_build
    print(f'Vàng từ {tu_nam}: {len(m1):,} nến 1 phút · khung {", ".join(khung_bot)} · {len(setups):,} tín hiệu · bộ chấm của dự án vào {len(a):,} lệnh '
          f'(spread và trượt giá bằng 0 ở cả hai bộ chấm) · {time.time() - t0:.0f} giây', flush=True)

    T = m1.index
    dat, het, thong_tin = {}, {}, []
    for n, x in enumerate(a):
        s = ghi[(pd.Timestamp(x['entry_time']), x['tf'])]
        i = int(T.searchsorted(pd.Timestamp(x['entry_time']), side='left'))
        j = int(T.searchsorted(pd.Timestamp(s.expires), side='left'))            # nến đầu tiên từ lúc hết hạn giữ: bộ chấm của dự án đóng ở giá mở nến này
        dat.setdefault(i - 1, []).append((n, s.sign == 1, s.sl, s.tps))
        if j < len(T):
            het.setdefault(j - 1, []).append(n)
        thong_tin.append((i, j, s))
    t1 = time.time()
    b, tu_choi = chay_bt(m1, dat, het)
    b = b.assign(n=[t[0] for t in b['Tag']], usd=(b['ExitPrice'] - b['EntryPrice']) * np.sign(b['Size']))
    O = m1['open'].to_numpy(dtype=float)
    print(f'Backtesting.py: {len(b):,} phần lệnh của {b["n"].nunique():,} lệnh · {time.time() - t1:.0f} giây'
          + (f' · từ chối {len(tu_choi)} lệnh (giá mở nhảy qua mức chốt đầu hoặc dừng lỗ so với giá đóng nến trước)' if tu_choi else ''), flush=True)

    hang = []
    for n, x in enumerate(a):
        if n in tu_choi:
            continue
        i, j, s = thong_tin[n]
        p = b[b['n'] == n]
        if len(p) != len(s.tps):
            hang.append((n, x, None, 'thieu'))
            continue
        usd_bt = float(p['usd'].mean())
        if abs(usd_bt - x['usd']) <= 0.011:
            hang.append((n, x, usd_bt, 'khop'))
            continue
        tai_het = (p['ExitBar'] == j).any()
        tp_nhay = ((p['usd'] > 0) & (np.abs(p['ExitPrice'].to_numpy() - O[p['ExitBar'].to_numpy()]) < 1e-6)).any()
        hang.append((n, x, usd_bt, 'het_gio' if tai_het else 'tp_nhay' if tp_nhay and usd_bt > x['usd'] else 'khac'))
    kq = pd.DataFrame([{'nam': pd.Timestamp(x['entry_time']).year, 'vao': x['entry_time'], 'huong': x['side'], 'du_an': x['usd'], 'bt': u, 'loai': loai}
                       for _, x, u, loai in hang])
    so = kq['loai'].value_counts()
    co = kq[kq['loai'] != 'thieu']
    print(f'\nLệnh so được: {len(co):,} · giống hệt (lãi lỗ lệch không quá 0,01 giá mỗi lệnh): {int(so.get("khop", 0)):,} ({so.get("khop", 0) / max(len(co), 1) * 100:.1f}%)')
    for loai, ten in (('tp_nhay', 'Mở cửa nhảy qua mức chốt lời (bộ chấm của dự án tính ở mức đã đặt, thấp hơn thực tế)'),
                      ('het_gio', 'Nến hết hạn giữ (bộ chấm của dự án đóng ở giá mở; Backtesting.py còn xét dừng lỗ, chốt lời trong nến đó)')):
        d = kq[kq['loai'] == loai]
        print(f'{ten}: {len(d)} lệnh, chênh tổng cộng {float((d["bt"] - d["du_an"]).sum()):+.2f} giá (Backtesting.py trừ dự án)')
    khac = kq[kq['loai'].isin(('khac', 'thieu'))]
    print(f'Khác chưa giải thích được: {len(khac)}')
    for _, x in khac.head(8).iterrows():
        print(f'   {x["loai"]}: vào {x["vao"]} {x["huong"]} · dự án {x["du_an"]:+.2f} · Backtesting.py {x["bt"] if x["bt"] is None else round(x["bt"], 2)}')
    print('\nTheo năm (không chi phí, giá mỗi lệnh ở 0,01 lot): lệnh · tổng theo bộ chấm của dự án · tổng theo Backtesting.py')
    for nam, x in co.groupby('nam'):
        print(f'   {nam}: {len(x):>4} · {x["du_an"].sum():+9.2f} · {x["bt"].sum():+9.2f}')
    print(f'   Cả quãng: {len(co):>4} · {co["du_an"].sum():+9.2f} · {co["bt"].sum():+9.2f}')
    sys.exit(1 if len(khac) else 0)
