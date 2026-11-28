# -*- coding: utf-8 -*-
"""Đo ĐỒNG THUẬN giữa các phương pháp: khi nhiều phương pháp cùng báo một chiều trong 2 giờ thì điểm vào có tốt hơn không.

Với mỗi tín hiệu, đếm số phương pháp KHÁC cũng có tín hiệu cùng chiều (và ngược chiều) trong 2 giờ trước đó, tính tới đúng lúc tín hiệu
(không nhìn tương lai). Rồi:
  1. Bảng tỷ lệ thắng và trung bình R theo số phương pháp đồng thuận, ở ba quãng 2015–2021, 2022–2024, 2025–2026.
  2. Huấn luyện lại mô hình có thêm hai đặc trưng đồng thuận (học 2015–2021) và so với mô hình cũ trên hai quãng sau.
Chỉ đọc tệp nến; không nối MT5.

    python -X utf8 cong-cu/dong_thuan.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import mo_hinh  # noqa: E402

QUANG = (('2015–2021', 2015, 2021), ('2022–2024', 2022, 2024), ('2025–2026', 2025, 2026))


def so(d, cot='r2'):
    return f'n={len(d):>6} thắng {(d[cot] > 0).mean() * 100:>5.1f}% {d[cot].mean():>+6.3f}R' if len(d) else f'n={0:>6}'


if __name__ == '__main__':
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    d = mo_hinh.du_lieu(cfg)
    if 'dt_cung' not in d:
        d = mo_hinh.them_dong_thuan(d)
    print(f'{len(d):,} tín hiệu, {d["nam"].min()}–{d["nam"].max()}')
    for cot in ('r1', 'r2'):
        print(f'\n=== Theo số phương pháp KHÁC cùng chiều trong 2 giờ, chốt ở {cot[1:]}R ===')
        for k, nhan in ((0, 'không có'), (1, 'một'), (2, 'từ hai')):
            x = d[d['dt_cung'] == k] if k < 2 else d[d['dt_cung'] >= 2]
            print(f'  {nhan:<8} ' + '   |   '.join(f'{ten}: {so(x[(x["nam"] >= a) & (x["nam"] <= b)], cot)}' for ten, a, b in QUANG))
        print(f'=== Theo số phương pháp KHÁC ngược chiều trong 2 giờ, chốt ở {cot[1:]}R ===')
        for k, nhan in ((0, 'không có'), (1, 'từ một')):
            x = d[d['dt_nguoc'] == 0] if k == 0 else d[d['dt_nguoc'] >= 1]
            print(f'  {nhan:<8} ' + '   |   '.join(f'{ten}: {so(x[(x["nam"] >= a) & (x["nam"] <= b)], cot)}' for ten, a, b in QUANG))
    print('\n=== Mô hình cũ so với mô hình có thêm hai đặc trưng đồng thuận (học 2015–2021, đích 2R) ===')
    hoc = d[d['nam'] <= 2021]
    for ten, X in (('cũ', [c for c in mo_hinh.cot() if not c.startswith('dt_')]), ('có đồng thuận', [c for c in mo_hinh.cot() if not c.startswith('dt_')] + ['dt_cung', 'dt_nguoc'])):
        m = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=500)).fit(hoc[X], (hoc['r2'] > 0).astype(int))
        ng = np.quantile(m.predict_proba(hoc[X])[:, 1], 0.9)
        dong = []
        for q, a, b in QUANG[1:]:
            x = d[(d['nam'] >= a) & (d['nam'] <= b)]
            p = m.predict_proba(x[X])[:, 1]
            dong.append(f'{q}: AUC {roc_auc_score((x["r2"] > 0).astype(int), p):.3f} · 10% cao nhất {so(x[p >= ng])}')
        he = dict(zip(X, m[-1].coef_[0]))
        print(f'  {ten:<14} ' + '   |   '.join(dong) + (f'   (hệ số: cùng {he["dt_cung"]:+.3f}, ngược {he["dt_nguoc"]:+.3f})' if 'dt_cung' in he else ''))
