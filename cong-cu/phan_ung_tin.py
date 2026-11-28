# -*- coding: utf-8 -*-
"""Phản ứng của giá vàng khi tin Mỹ mức cao ra (2015–11/2026), trên nến 1 phút đã sửa lệch giờ. Cách đo và cổng ghi TRƯỚC ở
cong-cu/CHUAN_HOA_DANG_KY.md (phần "Phản ứng của giá vàng khi tin Mỹ ra").

Mô tả theo từng loại tin: giá thường chạy bao xa sau 1, 15, 60 phút, bao nhiêu lần chạy quá 10 giá trong 15 phút, spread nở bao nhiêu. Rồi thử bốn
quy tắc đoán chiều (chọn trên 2015–2021, xác nhận trên 2022–2026). Không đoán theo độ bất ngờ (lịch không có số thực tế và dự báo).
Chỉ đọc tệp; không nối MT5. Kết quả ở out/phan-ung-tin.json (webapp đọc để hiện bên cạnh tin sắp ra) và out/phan-ung-tin.txt.

    python -X utf8 cong-cu/phan_ung_tin.py
"""
import csv
import importlib.util
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import hoc  # noqa: E402

UU_TIEN = ['Nonfarm Payrolls', 'CPI m/m', 'Core CPI m/m', 'Fed Interest Rate Decision', 'FOMC Press Conference', 'Core PCE Price Index m/m',
           'Retail Sales m/m', 'Core Retail Sales m/m', 'PPI m/m', 'GDP q/q', 'ISM Manufacturing PMI', 'ISM Non-Manufacturing PMI',
           'ADP Nonfarm Employment Change', 'JOLTS Job Openings', 'Initial Jobless Claims', 'Durable Goods Orders m/m',
           'Philadelphia Fed Manufacturing Index', 'CB Consumer Confidence Index']
TOI_THIEU_LOAI = 40
CAT = 2022
QUY_TAC = {'a': 'đi tiếp chiều 60 phút trước tin', 'b': 'đi ngược chiều 60 phút trước tin', 'c': 'theo xu hướng H1 (EMA20 so với EMA50)',
           'd': 'đi tiếp chiều phút đầu tiên sau tin (tính từ phút 1 tới phút 60)'}


def _nap(ten: str):
    spec = importlib.util.spec_from_file_location(ten, GOC / 'cong-cu' / f'{ten}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def lan_ra_tin(tep: Path, tu: str = '2015') -> list[tuple[pd.Timestamp, str]]:
    """[(giờ UTC, tên)] các lần ra tin USD mức cao; tin cùng phút gộp lại, đặt tên theo danh sách ưu tiên."""
    gom = defaultdict(list)
    with open(tep, encoding='utf-8') as f:
        for x in csv.DictReader(f):
            if x['importance'] == '3' and x['currency'] == 'USD' and x['time'] >= tu:
                gom[x['time']].append(x['event'])
    ra = []
    for t, ten in gom.items():
        uu = [n for n in UU_TIEN if n in ten]
        ra.append((pd.Timestamp(t.replace('.', '-'), tz='UTC'), uu[0] if uu else sorted(ten)[0]))
    return sorted(ra)


def do(m1: pd.DataFrame, S: np.ndarray, ema_h1: pd.Series, tin: list) -> pd.DataFrame:
    """Một dòng cho mỗi lần ra tin có đủ nến: các dịch chuyển (giá) và các dấu hiệu dùng cho bốn quy tắc."""
    T = m1.index.as_unit('ns').asi8
    C = m1['close'].to_numpy(dtype=float)
    PH = 60 * 10 ** 9
    tv = pd.Series(S).rolling(1440, min_periods=300).median().to_numpy()
    rows = []
    for t, ten in tin:
        v = t.value
        j0 = int(np.searchsorted(T, v, side='left')) - 1                    # nến cuối kết thúc đúng lúc tin ra
        if j0 < 61 or T[j0] < v - 5 * PH:
            continue
        def toi(phut):
            k = int(np.searchsorted(T, v + phut * PH, side='left')) - 1
            return C[k] if k > j0 and T[k] >= v + (phut - 5) * PH else np.nan
        p0, p1 = C[j0], toi(1)
        k60 = int(np.searchsorted(T, v - 60 * PH, side='left')) - 1
        truoc = p0 - C[k60] if k60 >= 0 and T[k60] >= v - 66 * PH else np.nan
        a, b = j0 + 1, int(np.searchsorted(T, v + 5 * PH, side='left'))
        sp = float(np.nanmax(S[a:b]) / tv[j0]) if b > a and np.isfinite(tv[j0]) and tv[j0] > 0 else np.nan
        e = ema_h1[ema_h1.index <= t]
        rows.append({'t': t, 'nam': t.year, 'ten': ten, 'd1': p1 - p0, 'd15': toi(15) - p0, 'd60': toi(60) - p0, 'truoc60': truoc,
                     'xu_h1': float(np.sign(e.iloc[-1])) if len(e) else 0.0, 'phut1': p1 - p0, 'sau1_60': toi(60) - p1, 'spread_x': sp})
    return pd.DataFrame(rows)


def chinh_xac(df: pd.DataFrame, qt: str) -> tuple[int, int]:
    """(số lần đoán, số lần đúng chiều) của quy tắc `qt` trên các dòng của df."""
    if qt in 'abc':
        doan = {'a': np.sign(df['truoc60']), 'b': -np.sign(df['truoc60']), 'c': df['xu_h1']}[qt]
        that = np.sign(df['d15'])
    else:
        doan, that = np.sign(df['phut1']), np.sign(df['sau1_60'])
    ok = (doan != 0) & (that != 0) & doan.notna() & that.notna()
    return int(ok.sum()), int((doan[ok] == that[ok]).sum())


if __name__ == '__main__':
    from scipy.stats import binomtest                                       # noqa: E402
    DV = _nap('diem_vao')
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    t0 = time.time()
    m1 = hoc._m1_dai(g, 2015)
    fr = hoc._khung(m1, g)
    h1 = fr['H1']['close']
    ema = h1.ewm(span=20, adjust=False).mean() - h1.ewm(span=50, adjust=False).mean()
    ema.index = ema.index + pd.Timedelta(hours=1)                           # giá trị của một nến H1 chỉ dùng được khi nến đã đóng
    S = DV.nap_spread(g, m1.index, float(g.get('spread', 0.17)))
    tin = lan_ra_tin(Path(os.path.expandvars(g['lich_tin'])))
    df = do(m1, S, ema, tin)
    print(f'{len(tin):,} lần ra tin USD mức cao · {len(df):,} lần có đủ nến · {time.time() - t0:.0f} giây', flush=True)
    KQ: dict = {'den': m1.index[-1].isoformat(), 'so_lan': int(len(df)), 'loai': [], 'quy_tac': {}}
    q = lambda s, p: round(float(np.nanquantile(np.abs(s), p)), 2)          # noqa: E731
    for ten, x in df.groupby('ten'):
        if len(x) < TOI_THIEU_LOAI:
            continue
        KQ['loai'].append({'ten': ten, 'n': int(len(x)), 'd1_tv': q(x['d1'], .5), 'd15_tv': q(x['d15'], .5), 'd15_p90': q(x['d15'], .9), 'd60_tv': q(x['d60'], .5),
                           'qua10_15': round(float((np.abs(x['d15']) > 10).mean() * 100), 1), 'len15': round(float((x['d15'] > 0).mean() * 100), 1),
                           'spread_x': round(float(np.nanmedian(x['spread_x'])), 1) if x['spread_x'].notna().any() else None,
                           'gan_day_d15_tv': q(x[x['nam'] >= 2024]['d15'], .5) if (x['nam'] >= 2024).sum() >= 10 else None,
                           'gan_day_d15_p90': q(x[x['nam'] >= 2024]['d15'], .9) if (x['nam'] >= 2024).sum() >= 10 else None})
    KQ['loai'].sort(key=lambda z: -z['d15_tv'])
    hoc_m, kiem_m = df['nam'] < CAT, df['nam'] >= CAT
    for k in QUY_TAC:
        n1, d1_ = chinh_xac(df[hoc_m], k)
        n2, d2_ = chinh_xac(df[kiem_m], k)
        KQ['quy_tac'][k] = {'ten': QUY_TAC[k], 'hoc': [n1, d1_, round(d1_ / n1 * 100, 1) if n1 else None], 'kiem': [n2, d2_, round(d2_ / n2 * 100, 1) if n2 else None],
                            'p_kiem': float(binomtest(d2_, n2, 0.5, alternative='greater').pvalue) if n2 else None}
    chon = max(KQ['quy_tac'], key=lambda k: KQ['quy_tac'][k]['hoc'][2] or 0)
    x = KQ['quy_tac'][chon]
    qua = x['kiem'][0] >= 100 and (x['kiem'][2] or 0) >= 55 and (x['p_kiem'] or 1) < 0.05
    KQ['chon'], KQ['qua_cong'] = chon, bool(qua)
    chu = [f"PHẢN ỨNG CỦA GIÁ VÀNG KHI TIN MỸ MỨC CAO RA · {len(df):,} lần ra tin 2015–11/2026 · nến 1 phút đã sửa lệch giờ",
           '', 'Theo loại tin (dịch chuyển tính bằng giá; trung vị trị tuyệt đối; "lên" = tỷ lệ lần giá cao hơn sau 15 phút):',
           f"{'loại tin':42s} {'lần':>5s} {'1 phút':>7s} {'15 phút':>8s} {'15p, 10% lần':>13s} {'60 phút':>8s} {'>10 giá/15p':>11s} {'lên':>6s} {'spread x':>9s}"]
    for z in KQ['loai']:
        chu.append(f"{z['ten'][:42]:42s} {z['n']:5d} {z['d1_tv']:7.2f} {z['d15_tv']:8.2f} {z['d15_p90']:13.2f} {z['d60_tv']:8.2f} {z['qua10_15']:10.1f}% {z['len15']:5.1f}% "
                   f"{(str(z['spread_x']) + 'x') if z['spread_x'] else '—':>9s}")
    chu += ['', 'Đoán chiều (chọn trên 2015–2021, xác nhận trên 2022–2026):']
    for k, z in KQ['quy_tac'].items():
        chu.append(f"  ({k}) {z['ten']:58s} 2015–2021: {z['hoc'][1]}/{z['hoc'][0]} = {z['hoc'][2]}% · 2022–2026: {z['kiem'][1]}/{z['kiem'][0]} = {z['kiem'][2]}% (p = {z['p_kiem']:.3f})")
    chu.append(f"\nQuy tắc tốt nhất trên phần học: ({chon}) → {'QUA CỔNG' if qua else 'KHÔNG QUA CỔNG: chiều giá sau tin không đoán được bằng các quy tắc này'}")
    txt = '\n'.join(chu).replace('.', ',').replace(',py', '.py')
    print(txt)
    (GOC / 'out').mkdir(exist_ok=True)
    (GOC / 'out' / 'phan-ung-tin.json').write_text(json.dumps(KQ, ensure_ascii=False, indent=1), encoding='utf-8')
    (GOC / 'out' / 'phan-ung-tin.txt').write_text(txt + '\n', encoding='utf-8')
    print(f'\nXong sau {time.time() - t0:.0f} giây. Kết quả: out/phan-ung-tin.json và .txt')
