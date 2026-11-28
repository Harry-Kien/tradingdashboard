# -*- coding: utf-8 -*-
"""Hiệu chuẩn xác suất của điểm mô hình: khi mô hình nói "xác suất chạm 2R là p" thì thực tế có đúng khoảng p không?

Cuốn chiếu theo năm như cong-cu/kiem_mo_hinh.py (mỗi năm thi, mô hình chỉ học các năm trước). Trên các tín hiệu ngoài mẫu:
- bảng tin cậy: chia theo mười nhóm xác suất dự báo, so xác suất dự báo trung bình với tỷ lệ thắng thật của nhóm;
- điểm Brier của mô hình so với chuẩn ngây thơ (luôn nói tỷ lệ thắng của quãng học), càng thấp càng tốt;
- độ dốc hiệu chuẩn: hồi quy kết quả thật theo logit của xác suất dự báo. Bằng 1 là chuẩn; dưới 1 là mô hình quá tự tin (xác suất tản ra rộng
  hơn mức dữ liệu cho phép); gần 0 là xác suất không mang thông tin.
Chỉ đọc tệp nến; không nối MT5.

    python -X utf8 cong-cu/kiem_hieu_chuan.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import mo_hinh as M  # noqa: E402

TU = 2019

if __name__ == '__main__':
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    d = M.du_lieu(cfg)
    X, cac = M.cot(), []
    for nam in range(TU, int(d['nam'].max()) + 1):
        hoc_, thi = d[d['nam'] < nam], d[d['nam'] == nam].copy()
        th_ = M._hoc(hoc_)
        thi['p'] = M._p(thi[X].to_numpy(dtype=float), *th_)
        thi['p0'] = float((hoc_['r2'] > 0).mean())                      # chuẩn ngây thơ: tỷ lệ thắng của quãng học
        cac.append(thi)
    a = pd.concat(cac, ignore_index=True)
    y = (a['r2'] > 0).to_numpy(dtype=float)
    p, p0 = a['p'].to_numpy(), a['p0'].to_numpy()
    print(f'Cuốn chiếu {TU}–{int(a["nam"].max())}: {len(a):,} tín hiệu ngoài mẫu · tỷ lệ thắng thật ở 2R {y.mean() * 100:.1f}% · '
          f'xác suất mô hình: từ {p.min() * 100:.1f}% tới {p.max() * 100:.1f}%, 80% số tín hiệu nằm trong {np.quantile(p, 0.1) * 100:.1f}–{np.quantile(p, 0.9) * 100:.1f}%')
    print('\n=== Bảng tin cậy (mười nhóm bằng nhau theo xác suất dự báo) ===')
    a['nhom'] = pd.qcut(a['p'], 10, labels=False, duplicates='drop')
    for k, x in a.groupby('nhom'):
        print(f'  nhóm {int(k) + 1:>2}: dự báo {x["p"].mean() * 100:5.1f}% · thật {(x["r2"] > 0).mean() * 100:5.1f}% · lệch {((x["r2"] > 0).mean() - x["p"].mean()) * 100:+5.1f} điểm · {x["r2"].mean():+.3f}R ({len(x):,})')
    b_mh, b_nt = float(((p - y) ** 2).mean()), float(((p0 - y) ** 2).mean())
    print(f'\nĐiểm Brier: mô hình {b_mh:.5f} · chuẩn ngây thơ {b_nt:.5f} · mô hình {"tốt hơn" if b_mh < b_nt else "KÉM hơn"} {(abs(b_nt - b_mh)) / b_nt * 100:.2f}%')
    lg = np.log(p / (1 - p)).reshape(-1, 1)
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(lg, y.astype(int))
    print(f'Độ dốc hiệu chuẩn: {float(lr.coef_[0][0]):.2f} (1 là chuẩn; dưới 1 là quá tự tin; gần 0 là không mang thông tin) · hệ số chặn {float(lr.intercept_[0]):+.2f}')
    print('Theo năm: ' + ' · '.join(f'{n}: dự báo {x["p"].mean() * 100:.1f}% thật {(x["r2"] > 0).mean() * 100:.1f}%' for n, x in a.groupby('nam')))
