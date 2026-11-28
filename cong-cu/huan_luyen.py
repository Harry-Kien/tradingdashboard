# -*- coding: utf-8 -*-
"""Huấn luyện mô hình học máy để CHỌN điểm vào, rồi kiểm xem lựa chọn đó có đứng vững ngoài mẫu không.

Dữ liệu: mọi tín hiệu của tám phương pháp trên nến vàng 1 phút từ 2015, mỗi tín hiệu kèm 14 đặc trưng chỉ tính từ nến ĐÃ ĐÓNG lúc đó
(không nhìn tương lai) và kết quả khi chốt ở 1R, 2R. Kỷ luật chia ba quãng:
  HỌC 2015–2021 (mô hình chỉ thấy quãng này) · CHỌN NGƯỠNG 2022–2024 · THI 2025–2026 (chỉ nhìn một lần, sau khi đã chốt ngưỡng).
Hai mô hình của scikit-learn có sẵn trên máy: hồi quy logistic và cây tăng cường (HistGradientBoosting). Chỉ đọc tệp nến; không nối MT5.

    python -X utf8 cong-cu/huan_luyen.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nghien_cuu import cham_doc_lap  # noqa: E402
from so_cong_khai import gia, hoc, phuong_phap as PP  # noqa: E402

DAC = ['rui_atr', 'bien_do', 'gio_sin', 'gio_cos', 'thu', 'thuan_h1', 'thuan_d1', 'cach_ema50', 'rsi', 'vi_tri_24h', 'di_4h', 'than_nen', 'bien_nen', 'cho']


def du_lieu() -> pd.DataFrame:
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    m1 = hoc._m1_dai(g, 2015)
    fr = hoc._khung(m1, g)
    T = m1.index.as_unit('ns').asi8
    O, H, L, C = (m1[k].to_numpy(dtype=float) for k in ('open', 'high', 'low', 'close'))
    sp = float(g.get('spread', 0.17))
    m15, h1, d1 = fr['M15'], fr['H1'], fr['D1']
    c = m15['close']
    atr = PP._atr(m15)
    # đặc trưng của từng nến M15, đều chỉ dùng nến đó trở về trước
    f = pd.DataFrame(index=m15.index)
    f['atr'] = atr
    f['cach_ema50'] = (c - c.ewm(span=50, adjust=False, min_periods=50).mean()) / atr
    f['rsi'] = gia.rsi_wilder(c) - 50
    cao, thap = m15['high'].rolling(96).max(), m15['low'].rolling(96).min()
    f['vi_tri_24h'] = (c - thap) / (cao - thap) - 0.5
    f['di_4h'] = (c - c.shift(16)) / atr
    f['than_nen'] = (c - m15['open']) / atr
    f['bien_nen'] = (m15['high'] - m15['low']) / atr
    ti = hoc.ty_le_bien_do(h1).dropna()
    xu_d1 = np.sign(d1['close'] - d1['close'].ewm(span=200, adjust=False, min_periods=200).mean()).shift(1)
    parts = []
    for ma in PP.DS:
        th = PP.quet(ma, m15, h1)
        df = cham_doc_lap(th, T, O, H, L, C, sp, PP.PHI)
        if not len(df):
            continue
        nen = pd.DatetimeIndex(df['t']) - pd.Timedelta(minutes=15)             # giờ mở của nến tín hiệu
        x = f.reindex(nen)
        dau = np.where(df['huong'] == 'MUA', 1.0, -1.0)
        ch = PP._chieu_h1(h1, pd.DatetimeIndex(df['t']))
        xd = np.nan_to_num(xu_d1.reindex(pd.DatetimeIndex(df['t']).normalize(), method='ffill').to_numpy())
        k = ti.index.searchsorted(pd.DatetimeIndex(df['t']) - pd.Timedelta(hours=1), side='right') - 1
        gio = pd.DatetimeIndex(df['t']).hour + pd.DatetimeIndex(df['t']).minute / 60
        out = pd.DataFrame({
            't': df['t'].to_numpy(), 'ma': ma, 'nam': pd.DatetimeIndex(df['t']).year, 'r1': df['r1'].to_numpy(), 'r2': df['r2'].to_numpy(),
            'rui_atr': df['rui'].to_numpy() / x['atr'].to_numpy(), 'bien_do': [float(ti.iloc[i]) if i >= 0 else np.nan for i in k],
            'gio_sin': np.sin(gio / 24 * 2 * np.pi), 'gio_cos': np.cos(gio / 24 * 2 * np.pi), 'thu': pd.DatetimeIndex(df['t']).day_of_week,
            'thuan_h1': ch * dau, 'thuan_d1': xd * dau,                         # các đặc trưng có chiều được nhân với chiều lệnh: dương là thuận
            'cach_ema50': x['cach_ema50'].to_numpy() * dau, 'rsi': x['rsi'].to_numpy() * dau, 'vi_tri_24h': x['vi_tri_24h'].to_numpy() * dau,
            'di_4h': x['di_4h'].to_numpy() * dau, 'than_nen': x['than_nen'].to_numpy() * dau, 'bien_nen': x['bien_nen'].to_numpy(),
            'cho': float(bool(PP.DS[ma].get('cho')))})
        parts.append(out)
    d = pd.concat(parts, ignore_index=True).replace([np.inf, -np.inf], np.nan).dropna(subset=DAC)
    for i, ma in enumerate(PP.DS):
        d[f'pp_{ma}'] = (d['ma'] == ma).astype(float)
    return d


def so(d, cot):
    return (len(d), float((d[cot] > 0).mean() * 100) if len(d) else float('nan'), float(d[cot].mean()) if len(d) else float('nan'))


def thu(d, cot, ten, mo_hinh):
    X = DAC + [c for c in d.columns if c.startswith('pp_')]
    q = {k: d[(d['nam'] >= a) & (d['nam'] <= b)] for k, a, b in (('hoc', 2015, 2021), ('chon', 2022, 2024), ('thi', 2025, 2026))}
    y = lambda x: (x[cot] > 0).astype(int)                                     # noqa: E731
    mo_hinh.fit(q['hoc'][X], y(q['hoc']))
    p = {k: mo_hinh.predict_proba(v[X])[:, 1] for k, v in q.items()}
    auc = {k: roc_auc_score(y(v), p[k]) for k, v in q.items()}
    print(f'\n--- {ten} · đích: có lãi khi chốt ở {cot[1:]}R ---')
    print('    AUC (0,50 là đoán mò):  HỌC {hoc:.3f} · CHỌN NGƯỠNG {chon:.3f} · THI {thi:.3f}'.format(**auc))
    kq = {}
    for phan in (0.5, 0.2, 0.1, 0.05):                                         # giữ lại phần trên cùng theo điểm của mô hình
        nguong = np.quantile(p['chon'], 1 - phan)                              # ngưỡng chốt trên quãng CHỌN NGƯỠNG, rồi áp nguyên cho quãng THI
        dong = []
        for k in ('chon', 'thi'):
            tat, giu = so(q[k], cot), so(q[k][p[k] >= nguong], cot)
            dong.append(f'{k.upper():<5} tất cả n={tat[0]:>5} thắng {tat[1]:>5.1f}% {tat[2]:>+6.3f}R → giữ n={giu[0]:>5} thắng {giu[1]:>5.1f}% {giu[2]:>+6.3f}R')
            kq[(phan, k)] = (tat, giu)
        print(f'    giữ {phan * 100:>3.0f}% điểm cao nhất: ' + '   |   '.join(dong))
    return auc, kq


if __name__ == '__main__':
    t0 = time.time()
    d_ = du_lieu()
    print(f'{len(d_):,} tín hiệu có đủ đặc trưng, {d_["nam"].min()}–{d_["nam"].max()} ({time.time() - t0:.0f} giây); '
          f'học {int((d_["nam"] <= 2021).sum()):,} · chọn ngưỡng {int(((d_["nam"] >= 2022) & (d_["nam"] <= 2024)).sum()):,} · thi {int((d_["nam"] >= 2025).sum()):,}')
    tong = []
    for cot_ in ('r1', 'r2'):
        for ten_, mh in (('Hồi quy logistic', make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=500))),
                         ('Cây tăng cường', HistGradientBoostingClassifier(max_depth=3, max_iter=200, learning_rate=0.05, l2_regularization=1.0, random_state=0))):
            tong.append((cot_, ten_, *thu(d_, cot_, ten_, mh)))
    print('\n=== TỔNG KẾT: giữ 10% điểm cao nhất, quãng THI 2025–2026 ===')
    for cot_, ten_, auc_, kq_ in tong:
        tat, giu = kq_[(0.1, 'thi')]
        print(f'{ten_:<18} chốt {cot_[1:]}R: AUC thi {auc_["thi"]:.3f} · tất cả thắng {tat[1]:.1f}% {tat[2]:+.3f}R · mô hình chọn n={giu[0]} thắng {giu[1]:.1f}% {giu[2]:+.3f}R')
