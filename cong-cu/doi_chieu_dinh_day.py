# -*- coding: utf-8 -*-
"""Đối chiếu phép chấm luật đỉnh/đáy 8 giờ của chủ dự án (ai.scorer, chỉ đọc) với một bộ chấm độc lập: Backtesting.py.

Cái được kiểm: phần THOÁT LỆNH và tính lãi lỗ. Cùng nến 1 phút, cùng các lệnh mà luật đã vào (giá vào, dừng lỗ, ba mức chốt lời). Mỗi lệnh
chia ba phần bằng nhau, mỗi phần chốt ở một mức; sau khi phần đầu chốt thì dừng lỗ của phần còn lại dời về giá vào, có hiệu lực từ nến kế tiếp;
quá hạn giữ (số giờ tối đa của dự án, hoặc giờ đóng lệnh thứ Sáu) thì đóng phần còn lại. Spread, trượt giá và phí qua đêm đặt bằng 0 ở cả hai
bên để chỉ so phần khớp và thoát lệnh.

Cái KHÔNG được kiểm ở đây: việc luật chọn nến nào để vào. Danh sách lệnh lấy nguyên từ lần chạy lại bằng mã của dự án
(so_cong_khai.kiem_chung._dinh_day), ghi lại bằng cách bọc tạm ai.scorer.score trong bộ nhớ và trả lại ngay sau đó.

Chỗ hai bộ chấm xử khác nhau, đếm riêng:
- nến mở cửa nhảy qua mức chốt lời: bộ chấm của dự án tính đúng ở mức đã đặt, Backtesting.py tính ở giá mở (có lợi hơn);
- hết hạn giữ: bộ chấm của dự án đóng ở giá đóng của nến cuối cùng trước hạn, Backtesting.py chỉ đóng được ở giá mở nến kế tiếp. Công cụ quy
  giá thoát của Backtesting.py về giá đóng nến trước rồi mới so, nên phần này vẫn được so chính xác;
- tín hiệu ra sau giờ đóng lệnh thứ Sáu: bộ chấm của dự án đóng ngay với lãi lỗ 0; công cụ chỉ kiểm con số đó đúng bằng 0.
Công cụ này không sửa gì trong dự án của chủ dự án. Chỉ đọc tệp nến; không nối MT5.

    python -X utf8 cong-cu/doi_chieu_dinh_day.py [năm bắt đầu, mặc định 2015]
"""
import json
import os
import sys
import time
import warnings
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import gia, hoc, kiem_chung  # noqa: E402


def chay_bt(m1: pd.DataFrame, dat: dict, het: dict):
    """dat: {nến j−1: [(số lệnh, mua?, sl, (tp1, tp2, tp3))]} để khớp ở giá mở nến j. het: {nến cuối trước hạn giữ: [số lệnh]}."""
    df = pd.DataFrame({'Open': m1['open'].to_numpy(), 'High': m1['high'].to_numpy(), 'Low': m1['low'].to_numpy(), 'Close': m1['close'].to_numpy()},
                      index=m1.index.tz_localize(None))
    tu_choi = set()

    class DinhDay(Strategy):
        def init(self):
            pass

        def next(self):
            k = len(self.data) - 1
            if self.trades:
                con = {}
                for t in self.trades:
                    con.setdefault(t.tag[0], []).append(t)
                for ts in con.values():                                     # phần chốt ở TP1 đã đóng: dời dừng lỗ của phần còn lại về giá vào
                    if len(ts) < 3 and all(t.tag[1] != 0 for t in ts):
                        for t in ts:
                            if t.sl != t.entry_price:
                                t.sl = t.entry_price
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
        st = Backtest(df, DinhDay, cash=1e9, commission=0.0, spread=0.0, trade_on_close=False, exclusive_orders=False, hedging=True,
                      finalize_trades=False).run()
    return st['_trades'], tu_choi


if __name__ == '__main__':
    tu_nam = int(sys.argv[1]) if len(sys.argv) > 1 else 2015
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    gia._nap_ma(g)
    from ai import config as C, scorer as SC, snapshot as SN              # noqa: E402 - mã của chủ dự án, chỉ đọc

    t0 = time.time()
    m1 = hoc._m1_dai(g, tu_nam)
    fr = hoc._khung(m1, g)
    tin, _ = SN.load_high_usd_news(Path(os.path.expandvars(g['lich_tin'])))

    # Chạy lại luật bằng mã của dự án với mọi chi phí bằng 0, ghi lại từng lệnh và kết quả chấm. Các hằng số chi phí và hàm score chỉ bị thay
    # trong bộ nhớ của tiến trình này và được trả lại ngay.
    ghi, goc_score = [], SC.score
    cu = {k: getattr(C, k) for k in ('SLIP_NORMAL', 'SLIP_NEWS', 'FIN_LONG_PCT', 'FIN_SHORT_PCT')}

    def score(v, t, bars, now, news):
        o = goc_score(v, t, bars, now, news)
        if o is not None and o.trang_thai == 'da_dong' and o.r is not None:
            ghi.append((v, pd.Timestamp(t), o))
        return o
    SC.score = score
    for k in cu:
        setattr(C, k, 0.0)
    try:
        kq_da = kiem_chung._dinh_day(g, m1, fr, 0.0, tin)
    finally:
        SC.score = goc_score
        for k, x in cu.items():
            setattr(C, k, x)
    assert len(ghi) == len(kq_da['lenh']), (len(ghi), len(kq_da['lenh']))
    print(f'Vàng từ {tu_nam}: {len(m1):,} nến 1 phút · luật đỉnh/đáy vào {len(ghi):,} lệnh (spread, trượt giá và phí qua đêm bằng 0 ở cả hai bộ chấm)'
          f' · {time.time() - t0:.0f} giây', flush=True)

    T = m1.index
    O, CL = m1['open'].to_numpy(dtype=float), m1['close'].to_numpy(dtype=float)
    gio, phut = C.FRIDAY_CLOSE_UTC
    dat, het, tt = {}, {}, []
    for n, (v, t, o) in enumerate(ghi):
        j = int(T.searchsorted(t, side='left'))                                  # nến 1 phút đầu tiên từ lúc có tín hiệu: lệnh khớp ở giá mở nến này
        thu_sau = (t + timedelta(days=(4 - t.weekday()) % 7)).replace(hour=gio, minute=phut, second=0, microsecond=0)
        han = min(thu_sau, t + timedelta(hours=C.MAX_HOLD_HOURS))
        jd = int(T.searchsorted(han, side='left'))                               # nến đầu tiên mở từ hạn giữ trở đi
        tt.append((j, jd, han))
        if jd <= j or j == 0:
            continue                                                             # tín hiệu ra sau giờ đóng lệnh thứ Sáu: không có gì để chạy
        dat.setdefault(j - 1, []).append((n, v.huong == 'MUA', v.sl, (v.tp1, v.tp2, v.tp3)))
        if jd < len(T):
            het.setdefault(jd - 1, []).append(n)
    t1 = time.time()
    b, tu_choi = chay_bt(m1, dat, het)
    b = b.assign(n=[x[0] for x in b['Tag']])
    print(f'Backtesting.py: {len(b):,} phần lệnh của {b["n"].nunique():,} lệnh · {time.time() - t1:.0f} giây'
          + (f' · từ chối {len(tu_choi)} lệnh (giá mở nhảy qua mức chốt hoặc dừng lỗ so với giá đóng nến trước)' if tu_choi else ''), flush=True)

    theo_n = {n: p for n, p in b.groupby('n')}
    hang = []
    for n, (v, t, o) in enumerate(ghi):
        j, jd, han = tt[n]
        du_an = float(o.r) * abs(o.gia_khop - v.sl)                              # lãi lỗ trung bình mỗi phần, tính bằng giá
        co = {'nam': t.year, 'vao': t, 'huong': v.huong, 'ket': o.ket_thuc, 'du_an': du_an, 'bt': None}
        if jd <= j or j == 0:
            hang.append({**co, 'loai': 'sau_thu_sau' if abs(du_an) < 1e-9 else 'khac'})
            continue
        if n in tu_choi:
            hang.append({**co, 'loai': 'tu_choi'})
            continue
        p = theo_n.get(n)
        if p is None or len(p) != 3:
            hang.append({**co, 'loai': 'thieu'})
            continue
        dau = np.sign(p['Size'].to_numpy())
        vao, ra, nen_ra = p['EntryPrice'].to_numpy(), p['ExitPrice'].to_numpy().copy(), p['ExitBar'].to_numpy()
        het_han = nen_ra == jd                                                   # phần bị đóng vì hết hạn: quy về giá đóng của nến trước hạn
        ra[het_han] = CL[jd - 1]
        bt = float(((ra - vao) * dau).mean())
        co['bt'] = bt
        if abs(bt - du_an) <= 0.011:
            hang.append({**co, 'loai': 'khop_het_han' if het_han.any() else 'khop'})
            continue
        tp_nhay = ((((ra - vao) * dau) > 0) & ~het_han & (np.abs(ra - O[nen_ra]) < 1e-6)).any()
        hang.append({**co, 'loai': 'tp_nhay' if tp_nhay and bt > du_an else 'khac'})
    kq = pd.DataFrame(hang)
    so = kq['loai'].value_counts()
    co = kq[kq['bt'].notna()]
    giong = int(so.get('khop', 0)) + int(so.get('khop_het_han', 0))
    print(f'\nLệnh so được: {len(co):,} · giống hệt (lãi lỗ lệch không quá 0,01 giá mỗi lệnh): {giong:,} ({giong / max(len(co), 1) * 100:.1f}%),'
          f' trong đó {int(so.get("khop_het_han", 0)):,} lệnh đóng vì hết hạn giữ')
    d = kq[kq['loai'] == 'tp_nhay']
    print(f'Mở cửa nhảy qua mức chốt lời (bộ chấm của dự án tính ở mức đã đặt, thấp hơn thực tế): {len(d)} lệnh, chênh tổng cộng '
          f'{float((d["bt"] - d["du_an"]).sum()):+.2f} giá (Backtesting.py trừ dự án)')
    print(f'Tín hiệu ra sau giờ đóng lệnh thứ Sáu, dự án đóng ngay với lãi lỗ 0: {int(so.get("sau_thu_sau", 0))} lệnh')
    if so.get('tu_choi', 0):
        print(f'Backtesting.py từ chối, không so được: {int(so["tu_choi"])} lệnh (giới hạn của thư viện, không phải lỗi của bộ chấm)')
    khac = kq[kq['loai'].isin(('khac', 'thieu'))]
    print(f'Khác chưa giải thích được: {len(khac)}')
    for _, x in khac.head(8).iterrows():
        print(f'   {x["loai"]}: vào {x["vao"]} {x["huong"]} · dự án {x["du_an"]:+.2f} ({x["ket"]}) · Backtesting.py {x["bt"] if x["bt"] is None else round(x["bt"], 2)}')
    print('\nTheo năm (không chi phí, giá mỗi lệnh ở 0,01 lot): lệnh · tổng theo bộ chấm của dự án · tổng theo Backtesting.py')
    for nam, x in co.groupby('nam'):
        print(f'   {nam}: {len(x):>4} · {x["du_an"].sum():+9.2f} · {x["bt"].sum():+9.2f}')
    print(f'   Cả quãng: {len(co):>4} · {co["du_an"].sum():+9.2f} · {co["bt"].sum():+9.2f}')
    sys.exit(1 if len(khac) else 0)
