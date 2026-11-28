# -*- coding: utf-8 -*-
"""Đối chiếu phép chạy lại của webapp (phuong_phap.cham) với một bộ chấm độc lập: thư viện Backtesting.py (AGPL-3.0).

Cùng một danh sách tín hiệu, cùng nến 1 phút, cùng quy tắc (mỗi lúc một lệnh, vào ở giá mở nến kế tiếp, dừng lỗ theo tín hiệu, chốt lời ở 2R,
giữ tối đa 24 giờ), spread và phí đặt bằng 0 để chỉ so đúng phần khớp lệnh và thoát lệnh. Nếu hai bộ chấm ra cùng lệnh, cùng điểm thoát thì
số đo của webapp không phải do lỗi của phép chấm. Chỉ đọc tệp nến; không nối MT5.

Lệnh chờ (ICT, ICT FVG, Fibonacci) được so ở phần hai. Bên Backtesting.py, tín hiệu đến khi chưa có lệnh nào đang mở thành một lệnh chờ sống
4 giờ; tín hiệu kế tiếp đến mà lệnh chờ chưa khớp thì lệnh chờ đó bị hủy. Lần đối chiếu đầu cho thấy cham() cũ KHÔNG có quy tắc hủy này: nó
xét từng tín hiệu theo thứ tự đến và cho tín hiệu đến trước cả 4 giờ để khớp, nên khi hai lệnh chờ chồng nhau nó chọn lệnh nhờ biết trước
lệnh nào về sau sẽ khớp (vàng 2026, không chi phí: ICT +2.027 giá so với +1.364; ICT FVG +1.322 so với −55). cham() đã được sửa theo đó.
Tín hiệu lệnh chờ mà giá đã ở bên kia mức chờ ngay ở nến đầu tiên thì cả hai bên đều bỏ (trang Biểu đồ báo "tín hiệu đã qua").
Ba chỗ hai bộ chấm còn xử khác nhau và được đếm riêng:
nến mở cửa đã vượt mức chờ (Backtesting.py khớp ở giá mở, tốt hơn mức chờ; webapp tính ở mức chờ), nến khớp chạm luôn dừng lỗ (webapp tính
dừng lỗ ngay; Backtesting.py không xét dừng lỗ trong nến khớp, ở đây chiến lược đóng ở giá mở nến kế tiếp), và hai lệnh chờ khớp cùng một nến.

Chỗ khác nhau CÓ CHỦ Ý: khi nến mở cửa nhảy qua mức chốt lời, Backtesting.py khớp ở giá mở (lãi hơn mức đã đặt), còn webapp chỉ tính ở mức chốt
lời cho thận trọng. Các lệnh như vậy được đếm riêng. Khi mở cửa nhảy qua dừng lỗ thì cả hai đều thoát ở giá mở (webapp được sửa theo kết quả
của chính phép đối chiếu này). Lệnh hết 24 giờ: webapp thoát ở giá đóng nến cuối, Backtesting.py ở giá mở nến kế tiếp; hai giá này thường
bằng nhau, chỉ lệch khi tệp nến thiếu một quãng ngay sau đó, và trường hợp ấy cũng được đếm riêng. Thoát với mã 1 nếu còn chỗ khác chưa
giải thích được.

    python -X utf8 cong-cu/doi_chieu_backtesting.py [năm] [--chi-lenh-cho | --bo-lenh-cho]      # mặc định: năm hiện tại của dữ liệu
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
from so_cong_khai import hoc, phuong_phap as PP  # noqa: E402

THI_TRUONG = [m for m, v in PP.DS.items() if not v.get('cho')]
LENH_CHO = [m for m, v in PP.DS.items() if v.get('cho')]


def bang_lenh(sig, T, O):
    """{vị trí nến ĐẶT lệnh: (mua?, dừng lỗ, chốt lời)}: lệnh đặt ở nến j−1 để Backtesting.py khớp ở giá mở nến j, đúng như cham()."""
    n, phut, out = len(T), 60 * 10 ** 9, {}
    for s in sorted(sig, key=lambda s: s['t']):
        t0 = pd.Timestamp(s['t']).value
        j = int(np.searchsorted(T, t0, side='left'))
        if j >= n or j == 0 or T[j] - t0 > PP.TRE_PHUT * phut:
            continue
        mua = s['huong'] == 'MUA'
        rui = (O[j] - s['sl']) * (1 if mua else -1)
        if rui <= 0:
            continue
        out.setdefault(j - 1, (mua, float(s['sl']), float(O[j] + (1 if mua else -1) * PP.TP_R * rui)))
    return out


def chay_bt(m1, lenh):
    df = pd.DataFrame({'Open': m1['open'].to_numpy(), 'High': m1['high'].to_numpy(), 'Low': m1['low'].to_numpy(), 'Close': m1['close'].to_numpy()},
                      index=m1.index.tz_localize(None))
    tu_choi = []

    class Chien(Strategy):
        def init(self):
            pass

        def next(self):
            i = len(self.data) - 1
            if self.position:
                if i - self.trades[0].entry_bar >= PP.GIU_PHUT - 1:           # hết 24 giờ: đóng ở giá mở nến kế tiếp
                    self.position.close()
                return
            x = lenh.get(i)
            if x and not self.orders:
                try:
                    (self.buy if x[0] else self.sell)(size=1, sl=x[1], tp=x[2])
                except ValueError:                                             # giá đóng nến đặt lệnh đã nằm ngoài khoảng SL–TP
                    tu_choi.append(i)

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        st = Backtest(df, Chien, cash=1e9, commission=0.0, spread=0.0, trade_on_close=False, exclusive_orders=False, finalize_trades=False).run()
    return st['_trades'], len(tu_choi)


def bang_cho(sig, T, O):
    """{vị trí nến ĐẶT lệnh: [None | (số tín hiệu, mua?, mức chờ, dừng lỗ, chốt lời, nến cuối còn hiệu lực)]}: đặt ở nến j−1 để có thể khớp từ nến j.
    None đứng trước mỗi tín hiệu: dấu hủy lệnh chờ cũ."""
    n, phut, out = len(T), 60 * 10 ** 9, {}
    for so, s in enumerate(sorted(sig, key=lambda s: s['t'])):
        t0 = pd.Timestamp(s['t']).value
        j = int(np.searchsorted(T, t0, side='left'))
        if j >= n or j == 0:
            continue
        out.setdefault(j - 1, []).append(None)                                # tín hiệu nào đến cũng hủy lệnh chờ cũ, kể cả khi chính nó không đặt được
        if T[j] - t0 > PP.TRE_PHUT * phut:
            continue
        mua = s['huong'] == 'MUA'
        dau = 1 if mua else -1
        if (O[j] <= s['vao']) if mua else (O[j] >= s['vao']):
            continue                                                          # giá đã ở bên kia mức chờ lúc tín hiệu đến: không đặt lệnh
        rui = (s['vao'] - s['sl']) * dau
        if rui <= 0:
            continue
        cuoi = min(n, int(np.searchsorted(T, t0 + PP.CHO_NEN * 15 * phut, side='left')))
        if cuoi > j:
            out.setdefault(j - 1, []).append((so, mua, float(s['vao']), float(s['sl']), float(s['vao'] + dau * PP.TP_R * rui), cuoi - 1))
    return out


def chay_bt_cho(m1, lenh):
    """Trả (bảng lệnh, {số tín hiệu của lệnh có nến khớp chạm dừng lỗ}, {số tín hiệu của lệnh khớp cùng nến với một lệnh khác}, số lệnh bị từ chối)."""
    df = pd.DataFrame({'Open': m1['open'].to_numpy(), 'High': m1['high'].to_numpy(), 'Low': m1['low'].to_numpy(), 'Close': m1['close'].to_numpy()},
                      index=m1.index.tz_localize(None))
    H, L = df['High'].to_numpy(), df['Low'].to_numpy()
    han, cham_sl, trung, tu_choi = {}, set(), set(), []

    class Cho(Strategy):
        def init(self):
            pass

        def next(self):
            i = len(self.data) - 1
            cho = [o for o in self.orders if not o.is_contingent and o.limit]
            if self.position:
                for o in cho:
                    o.cancel()                                                 # đã có lệnh khớp: bỏ mọi lệnh chờ còn lại
                tr = sorted(self.trades, key=lambda t: t.tag)
                for t in tr[1:]:                                               # hai lệnh chờ khớp cùng một nến: giữ tín hiệu đến trước
                    trung.add(t.tag)
                    t.close()
                t = tr[0]
                if len(tr) > 1:
                    trung.add(t.tag)
                if t.entry_bar == i and t.sl is not None and ((L[i] <= t.sl) if t.is_long else (H[i] >= t.sl)):
                    cham_sl.add(t.tag)                                         # nến khớp chạm luôn dừng lỗ: thư viện không xét, đóng ở giá mở nến kế tiếp
                    t.close()
                elif i - t.entry_bar >= PP.GIU_PHUT - 1:                       # hết 24 giờ
                    t.close()
                else:
                    return
            else:
                for o in cho:
                    if han.get(o.tag, i) <= i:
                        o.cancel()                                             # lệnh chờ hết 4 giờ
            for x in lenh.get(i, ()):
                for o in [o for o in self.orders if not o.is_contingent and o.limit]:
                    o.cancel()                                                 # tín hiệu mới đến: lệnh chờ cũ chưa khớp bị thay
                if x is None:
                    continue
                try:
                    (self.buy if x[1] else self.sell)(size=1, limit=x[2], sl=x[3], tp=x[4], tag=x[0])
                    han[x[0]] = x[5]
                except ValueError:
                    tu_choi.append(i)

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        st = Backtest(df, Cho, cash=1e9, commission=0.0, spread=0.0, trade_on_close=False, exclusive_orders=False, finalize_trades=False).run()
    return st['_trades'], cham_sl, trung, len(tu_choi)


def so_lenh_cho(nam, m1n, fr, T, O, mo, ke):
    """Phần hai: ba phương pháp dùng lệnh chờ. Trả số lệnh khác nhau chưa giải thích được."""
    print(f'\n— LỆNH CHỜ ({", ".join(LENH_CHO)}) —')
    tong = dict(a=0, b=0, m=0, khop=0, mo_vuot=0, cham_sl=0, tp_nhay=0, thieu=0, trung=0, le=0, khac=0)
    for ma in LENH_CHO:
        t1 = time.time()
        sig = sorted((s for s in PP.quet(ma, fr['M15'], fr['H1']) if pd.Timestamp(s['t']).year == nam), key=lambda s: s['t'])
        a = pd.DataFrame(PP.cham(sig, m1n, 0.0, phi=0.0))
        b, cham_sl, trung, tu_choi = chay_bt_cho(m1n, bang_cho(sig, T, O))
        if not len(a) or not len(b):
            print(f'{ma}: webapp {len(a)} lệnh, Backtesting.py {len(b)} lệnh')
            continue
        a['vao_t'] = pd.to_datetime(a['t']).dt.tz_localize(None)
        a['ra_t'] = pd.to_datetime(a['ra']).dt.tz_localize(None)
        b = b.assign(vao_t=pd.to_datetime(b['EntryTime']), ra_bt=pd.to_datetime(b['ExitTime']), r_bt=(b['ExitPrice'] - b['EntryPrice']) * np.sign(b['Size']))
        m = a.merge(b, on='vao_t', how='outer', indicator=True)
        ca = m[m['_merge'] == 'both'].copy()
        le_a, le_b = m[m['_merge'] == 'left_only'], m[m['_merge'] == 'right_only']
        ca['rui'] = (ca['usd'] / ca['r']).abs().replace([np.inf, -np.inf], np.nan)
        sai = ca['rui'].fillna(1) * 0.02 + 0.05
        cung_ra = (ca['ra_t'] - ca['ra_bt']).abs() <= pd.Timedelta(minutes=1)
        cung_vao = (ca['vao'] - ca['EntryPrice']).abs() <= 1e-6
        khop = cung_ra & cung_vao & ((ca['usd'] - ca['r_bt']).abs() <= sai)
        la_trung = ca['Tag'].isin(trung) & ~khop
        la_cham = ca['Tag'].isin(cham_sl) & ~khop & ~la_trung & cung_vao & (ca['ket'] == 'SL') & (ca['ra_t'] == ca['vao_t'])
        mo_vuot = ~khop & ~la_trung & ~cung_vao & (np.abs(ca['EntryPrice'].to_numpy() - mo.reindex(ca['vao_t']).to_numpy()) < 1e-6) \
            & ((ca['EntryPrice'] - ca['vao']) * np.sign(ca['Size']) < 0)                                            # mở cửa đã vượt mức chờ: khớp tốt hơn mức chờ
        tp_nhay = ~khop & ~la_trung & cung_vao & cung_ra & (ca['ket'] == 'TP') & (ca['r_bt'] > ca['usd']) \
            & (np.abs(ca['ExitPrice'].to_numpy() - mo.reindex(ca['ra_bt']).to_numpy()) < 1e-6)
        thieu = ~khop & ~la_trung & cung_vao & (ca['ket'] == 'Hết giờ') & (ca['ra_bt'] - ca['ra_t'] > pd.Timedelta(minutes=1)) \
            & (ke.reindex(ca['ra_t']).to_numpy() == ca['ra_bt'].to_numpy())
        khac = ~(khop | la_trung | la_cham | mo_vuot | tp_nhay | thieu)
        for k, v in dict(a=len(a), b=len(b), m=len(ca), khop=int(khop.sum()), mo_vuot=int(mo_vuot.sum()), cham_sl=int(la_cham.sum()), tp_nhay=int(tp_nhay.sum()),
                         thieu=int(thieu.sum()), trung=int(la_trung.sum()), le=len(le_a) + len(le_b), khac=int(khac.sum())).items():
            tong[k] += v
        print(f'\n{ma}: {len(sig)} tín hiệu · webapp {len(a)} lệnh ({a["usd"].sum():+.2f} giá) · Backtesting.py {len(b)} lệnh ({b["r_bt"].sum():+.2f} giá) · {time.time() - t1:.0f} giây'
              + (f' · Backtesting.py từ chối {tu_choi} lệnh' if tu_choi else ''))
        print(f'   cùng nến khớp: {len(ca)} · cùng giá khớp, nến thoát, giá thoát: {int(khop.sum())} · mở cửa vượt mức chờ: {int(mo_vuot.sum())} '
              f'({float((ca["r_bt"] - ca["usd"])[mo_vuot].sum()):+.2f} giá) · nến khớp chạm dừng lỗ: {int(la_cham.sum())} ({float((ca["r_bt"] - ca["usd"])[la_cham].sum()):+.2f} giá) '
              f'· nhảy qua chốt lời: {int(tp_nhay.sum())} · hết giờ trước quãng thiếu nến: {int(thieu.sum())} · hai lệnh khớp cùng nến: {int(la_trung.sum())} '
              f'· chỉ một bên có: webapp {len(le_a)}, Backtesting.py {len(le_b)} · khác chưa giải thích: {int(khac.sum())}')
        for _, x in ca[khac].head(4).iterrows():
            print(f'   khác: khớp {x["vao_t"]} webapp {x["vao"]:.2f} / BT {x["EntryPrice"]:.2f} · webapp ra {x["ra_t"]} {x["ket"]} {x["usd"]:+.2f} · BT ra {x["ra_bt"]} {x["r_bt"]:+.2f}')
        for _, x in le_a.head(3).iterrows():
            print(f'   chỉ webapp: khớp {x["vao_t"]} {x["huong"]} {x["vao"]:.2f} ra {x["ra_t"]} {x["ket"]} {x["usd"]:+.2f}')
        for _, x in le_b.head(3).iterrows():
            print(f'   chỉ Backtesting.py: khớp {x["vao_t"]} {x["EntryPrice"]:.2f} ra {x["ra_bt"]} {x["r_bt"]:+.2f} (tín hiệu số {x["Tag"]})')
    print(f'\nTỔNG LỆNH CHỜ: webapp {tong["a"]} · Backtesting.py {tong["b"]} · cùng nến khớp {tong["m"]} · giống hệt {tong["khop"]} '
          f'({tong["khop"] / max(1, max(tong["a"], tong["b"])) * 100:.1f}%) · mở cửa vượt mức chờ {tong["mo_vuot"]} · nến khớp chạm dừng lỗ {tong["cham_sl"]} · nhảy qua chốt lời {tong["tp_nhay"]} '
          f'· hết giờ trước quãng thiếu nến {tong["thieu"]} · hai lệnh khớp cùng nến {tong["trung"]} · chỉ một bên có {tong["le"]} · khác chưa giải thích {tong["khac"]}')
    return tong['khac'] + tong['le']


if __name__ == '__main__':
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    m1 = hoc._m1_dai(g, 2024)
    so = [x for x in sys.argv[1:] if x.isdigit()]
    nam = int(so[0]) if so else int(m1.index[-1].year)
    fr = hoc._khung(m1, g)
    m1n = m1[m1.index.year == nam]
    T = m1n.index.as_unit('ns').asi8
    O = m1n['open'].to_numpy(dtype=float)
    mo = pd.Series(O, index=m1n.index.tz_localize(None))
    print(f'Vàng năm {nam}: {len(m1n):,} nến 1 phút, {m1n.index[0].date()} → {m1n.index[-1].date()} · spread và phí bằng 0 ở cả hai bộ chấm')
    tong = [0, 0, 0, 0, 0, 0]
    ke = pd.Series(mo.index[1:], index=mo.index[:-1])                     # giờ của nến kế tiếp có trong tệp
    for ma in (THI_TRUONG if '--chi-lenh-cho' not in sys.argv else []):
        t1 = time.time()
        sig = [s for s in PP.quet(ma, fr['M15'], fr['H1']) if pd.Timestamp(s['t']).year == nam]
        a = pd.DataFrame(PP.cham(sig, m1n, 0.0, phi=0.0))
        b, tu_choi = chay_bt(m1n, bang_lenh(sig, T, O))
        if not len(a) or not len(b):
            print(f'{ma}: webapp {len(a)} lệnh, Backtesting.py {len(b)} lệnh')
            continue
        a['vao_t'] = pd.to_datetime(a['t']).dt.tz_localize(None)
        a['ra_t'] = pd.to_datetime(a['ra']).dt.tz_localize(None)
        b = b.assign(vao_t=pd.to_datetime(b['EntryTime']), r_bt=(b['ExitPrice'] - b['EntryPrice']) * np.sign(b['Size']))
        m = a.merge(b, on='vao_t', how='inner')
        m['rui'] = (m['usd'] / m['r']).abs().replace([np.inf, -np.inf], np.nan)
        lech_ra = (m['ra_t'] - pd.to_datetime(m['ExitTime'])).abs() <= pd.Timedelta(minutes=1)
        lech_gia = (m['usd'] - m['r_bt']).abs()
        khop_het = lech_ra & (lech_gia <= m['rui'].fillna(1) * 0.02 + 0.05)
        tp_nhay = (~khop_het & lech_ra & (m['ket'] == 'TP') & (m['r_bt'] > m['usd'])
                   & (np.abs(m['ExitPrice'].to_numpy() - mo.reindex(pd.to_datetime(m['ExitTime'])).to_numpy()) < 1e-6))    # mở cửa nhảy qua chốt lời
        thieu = (~khop_het & (m['ket'] == 'Hết giờ') & (pd.to_datetime(m['ExitTime']) - m['ra_t'] > pd.Timedelta(minutes=1))
                 & (ke.reindex(m['ra_t']).to_numpy() == pd.to_datetime(m['ExitTime']).to_numpy()))                   # hết giờ ngay trước một quãng thiếu nến
        tong[0] += len(a); tong[1] += len(b); tong[2] += len(m); tong[3] += int(khop_het.sum()); tong[4] += int(tp_nhay.sum()); tong[5] += int(thieu.sum())
        print(f'\n{ma}: webapp {len(a)} lệnh ({a["usd"].sum():+.2f} giá, thắng {(a["usd"] > 0).mean() * 100:.1f}%) · Backtesting.py {len(b)} lệnh ({b["r_bt"].sum():+.2f} giá, thắng {(b["r_bt"] > 0).mean() * 100:.1f}%)'
              f' · {time.time() - t1:.0f} giây' + (f' · Backtesting.py từ chối {tu_choi} lệnh' if tu_choi else ''))
        print(f'   cùng nến vào: {len(m)}/{max(len(a), len(b))} · trong đó cùng nến thoát và cùng giá thoát: {int(khop_het.sum())}/{len(m)}'
              + (f' · mở cửa nhảy qua chốt lời (webapp cố ý tính thấp hơn): {int(tp_nhay.sum())} lệnh, {float((m["r_bt"] - m["usd"])[tp_nhay].sum()):+.2f} giá' if tp_nhay.any() else ''))
        for _, x in m[thieu].iterrows():
            print(f'   hết giờ ngay trước quãng thiếu nến {x["ra_t"]} → {x["ExitTime"]}: webapp {x["usd"]:+.2f}, Backtesting.py {x["r_bt"]:+.2f}')
        khac = m[~khop_het & ~tp_nhay & ~thieu].head(4)
        for _, x in khac.iterrows():
            print(f'   khác: vào {x["vao_t"]} · webapp ra {x["ra_t"]} {x["ket"]} {x["usd"]:+.2f} · Backtesting.py ra {x["ExitTime"]} {x["r_bt"]:+.2f}')
    print(f'\nTỔNG: webapp {tong[0]} lệnh · Backtesting.py {tong[1]} lệnh · cùng nến vào {tong[2]} · cùng cả điểm thoát {tong[3]} '
          f'({tong[3] / max(1, max(tong[0], tong[1])) * 100:.1f}% số lệnh) · khác có chủ ý ở chốt lời {tong[4]} · hết giờ ngay trước quãng thiếu nến {tong[5]} · khác chưa giải thích được {tong[2] - sum(tong[3:])}')
    con = so_lenh_cho(nam, m1n, fr, T, O, mo, ke) if '--bo-lenh-cho' not in sys.argv else 0
    sys.exit(1 if con or tong[2] - sum(tong[3:]) or not tong[0] == tong[1] == tong[2] else 0)
