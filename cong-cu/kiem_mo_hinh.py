# -*- coding: utf-8 -*-
"""Kiểm mô hình chọn điểm vào theo cách khắt khe nhất có thể với dữ liệu đang có:

1. CUỐN CHIẾU THEO NĂM: với mỗi năm Y từ 2019 tới nay, mô hình chỉ học các tín hiệu TRƯỚC năm Y, ngưỡng "điểm từ 90" cũng lấy từ quãng đó,
   rồi mới chấm các tín hiệu của năm Y. Không năm nào được mô hình nhìn thấy trước.
2. MÔ PHỎNG GIAO DỊCH: các tín hiệu được chọn đi qua đúng phép chấm của webapp (phuong_phap.cham): mỗi lúc một lệnh, chốt ở 2R, giữ tối đa
   24 giờ, nến chạm cả hai thì tính dừng lỗ. Chạy hai lần: chi phí của cấu hình, và chi phí GẤP ĐÔI (spread lẫn phí) để xem còn đứng không.
Chỉ đọc tệp nến; không nối MT5.

    python -X utf8 cong-cu/kiem_mo_hinh.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import hoc, mo_hinh as M, phuong_phap as PP  # noqa: E402

TU = 2019


def tom(ls, ten):
    if not ls:
        print(f'  {ten}: không có lệnh')
        return
    d = pd.DataFrame(ls)
    d['nam'] = pd.DatetimeIndex(pd.to_datetime(d['t'])).year
    luy = d['r'].cumsum().to_numpy()
    sut = float((np.maximum.accumulate(luy) - luy).max())
    chuoi = max(len(x) for x in ''.join('1' if v <= 0 else '0' for v in d['r']).split('0'))
    thang = d.groupby(pd.DatetimeIndex(pd.to_datetime(d['t'])).to_period('M'))['r'].sum()
    print(f'  {ten}: {len(d)} lệnh · thắng {(d["r"] > 0).mean() * 100:.1f}% · {d["r"].mean():+.3f}R mỗi lệnh (sai số chuẩn {d["r"].std() / len(d) ** .5:.3f}) · tổng {d["r"].sum():+.1f}R '
          f'· sụt giảm lớn nhất {sut:.1f}R · chuỗi không lãi dài nhất {chuoi} · {int((thang > 0).sum())}/{len(thang)} tháng có lãi')
    print('     theo năm: ' + '  '.join(f'{n}: {x["r"].mean():+.2f}R ({len(x)})' for n, x in d.groupby('nam')))


if __name__ == '__main__':
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    d = M.du_lieu(cfg)                                              # các tín hiệu đã có kết quả, dùng để HỌC
    m1 = hoc._m1_dai(g, 2015)
    fr = hoc._khung(m1, g)
    f = M.bang_nen(fr['M15'])
    # mọi tín hiệu (kể cả cái về sau không khớp), kèm đặc trưng: đây là thứ mô hình thấy lúc phải quyết định
    rows, sig = [], []
    for ma in PP.DS:
        th = PP.quet(ma, fr['M15'], fr['H1'])
        if not th:
            continue
        t = pd.DatetimeIndex([s['t'] for s in th])
        b = M._bang(f, fr['H1'], fr['D1'], t, np.array([1.0 if s['huong'] == 'MUA' else -1.0 for s in th]), np.array([abs(s['vao'] - s['sl']) for s in th]), ma)
        b.insert(0, 't', t)
        b.insert(1, 'ma', ma)
        b.insert(2, 'huong', [s['huong'] for s in th])
        rows.append(b)
        sig += th
    a = M.them_dong_thuan(pd.concat(rows, ignore_index=True)).replace([np.inf, -np.inf], np.nan)
    a['nam'] = pd.DatetimeIndex(a['t']).year
    X = M.cot()
    print(f'{len(d):,} tín hiệu có kết quả để học · {len(a):,} tín hiệu phải quyết định · các năm thi: {TU}–{int(a["nam"].max())}')

    chon_idx, dong = [], []
    for nam in range(TU, int(a['nam'].max()) + 1):
        hoc_ = d[d['nam'] < nam]
        th_ = M._hoc(hoc_)                                          # chỉ học dữ liệu trước năm thi
        nguong = np.quantile(M._p(hoc_[X].to_numpy(dtype=float), *th_), 0.9)
        thi = d[d['nam'] == nam]
        p_thi = M._p(thi[X].to_numpy(dtype=float), *th_)
        cao = thi[p_thi >= nguong]
        dong.append(f'  {nam}: học {len(hoc_):>6,} · mọi tín hiệu {thi["r2"].mean():+.3f}R (thắng {(thi["r2"] > 0).mean() * 100:.1f}%) → điểm từ 90: n={len(cao):>4} '
                    f'thắng {(cao["r2"] > 0).mean() * 100:.1f}% {cao["r2"].mean():+.3f}R · ở 1R thắng {(cao["r1"] > 0).mean() * 100:.1f}% {cao["r1"].mean():+.3f}R')
        q = a[(a['nam'] == nam)].dropna(subset=M.DAC)
        chon_idx += list(q.index[M._p(q[X].to_numpy(dtype=float), *th_) >= nguong])
    print('\n=== 1. CUỐN CHIẾU THEO NĂM (mỗi tín hiệu chấm riêng, chốt 2R) ===')
    print('\n'.join(dong))

    chon = [sig[i] for i in sorted(chon_idx)]
    sp = float(g.get('spread', 0.17))
    print(f'\n=== 2. MÔ PHỎNG GIAO DỊCH: {len(chon):,} tín hiệu được chọn trong {TU}–{int(a["nam"].max())}, mỗi lúc một lệnh, chốt 2R ===')
    tom(PP.cham(chon, m1, sp), 'chi phí của cấu hình')
    tom(PP.cham(chon, m1, sp * 2, phi=PP.PHI * 2), 'chi phí GẤP ĐÔI')
    tom(PP.cham(chon, m1, sp, tp_r=1.0), 'chốt ở 1R, chi phí của cấu hình')
    print('\n  Để so sánh, MỌI tín hiệu cùng quãng, cùng cách mô phỏng:')
    tom(PP.cham([s for s, n in zip(sig, a['nam']) if n >= TU], m1, sp), 'không lọc')
