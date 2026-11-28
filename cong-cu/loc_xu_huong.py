# -*- coding: utf-8 -*-
"""Lọc theo xu hướng nhiều khung cho tám phương pháp: có giữ được lợi thế khi chỉ vào thuận xu hướng D1 (L5), hoặc khi D1, H4, H1 cùng chiều (L6)?

Câu hỏi, hai bộ lọc, cổng và điều kiện "có lãi ổn định" đã ghi TRƯỚC khi đo ở cong-cu/CHUAN_HOA_DANG_KY.md (phần "Lọc theo xu hướng nhiều khung").
Bản nền là công thức trên phiếu của từng phương pháp (so_cong_khai/phieu.py, CONG_THUC), chấm bằng đúng phép mô phỏng của cong-cu/diem_vao.py (spread
từng nến, phí, trượt giá lúc tin, phí qua đêm; mỗi tín hiệu chấm riêng). Chỉ đọc tệp nến; không nối MT5, không đặt lệnh, không sửa luật nào.
Kết quả ở out/loc-xu-huong.json; bảng in ra màn hình.

    python -X utf8 cong-cu/loc_xu_huong.py
"""
import json
import sys
import time
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diem_vao as DV  # noqa: E402 - cùng phép mô phỏng, cùng cổng
from so_cong_khai import gia, hoc, phuong_phap as PP  # noqa: E402
from so_cong_khai.phieu import CONG_THUC  # noqa: E402

TEN = {'nen': 'bản nền (công thức trên phiếu)', 'L5': 'bỏ khi ngược xu hướng D1', 'L6': 'chỉ giữ khi D1, H4, H1 cùng chiều lệnh'}
NAM_TOI_THIEU = 10          # năm có ít nhất chừng này lệnh mới được tính vào số năm có lãi
NAM_ON_DINH = 7             # "có lãi ổn định": ít nhất chừng này năm có tổng R dương


def xu_huong(khung: pd.DataFrame, dai: timedelta, luc: pd.DatetimeIndex) -> np.ndarray:
    """Dấu của EMA20 − EMA50 trên giá đóng, theo nến ĐÃ ĐÓNG trước từng mốc `luc` (nến mở lúc t đóng lúc t + `dai`)."""
    d = np.sign(PP._ema(khung['close'].astype(float), 20) - PP._ema(khung['close'].astype(float), 50)).fillna(0.0)
    d.index = d.index + dai
    d = d[~d.index.duplicated(keep='last')].sort_index()
    return d.reindex(luc, method='ffill').fillna(0.0).to_numpy() if len(luc) else np.array([])


def loc_moi(th: list, fr: dict) -> dict:
    """{'L5', 'L6': mảng bool, True = tín hiệu BỊ bỏ}."""
    luc = pd.DatetimeIndex([pd.Timestamp(s['t']) for s in th])
    d1 = xu_huong(fr['D1'], timedelta(days=1), luc)
    h4 = xu_huong(fr['H4'], timedelta(hours=4), luc)
    h1 = xu_huong(fr['H1'], timedelta(hours=1), luc)
    chieu = np.array([1.0 if s['huong'] == 'MUA' else -1.0 for s in th])
    return {'L5': d1 * chieu < 0, 'L6': ~((d1 * chieu > 0) & (h4 * chieu > 0) & (h1 * chieu > 0))}


def theo_nam(df: pd.DataFrame) -> dict:
    k = df[df['khop']]
    nam = {int(y): [int(len(g)), round(float(g['r'].sum()), 1), round(float(g['r'].mean()), 3)] for y, g in k.groupby('nam')}
    du = [v for v in nam.values() if v[0] >= NAM_TOI_THIEU]
    return {'nam': nam, 'so_nam': len(du), 'nam_lai': sum(v[1] > 0 for v in du)}


def on_dinh(hp: dict, tn: dict) -> bool:
    c, k = hp['chinh'], hp['kiem']
    return bool(c['n'] and k['n'] and c['r_tb'] > 0 and k['r_tb'] > 0 and tn['nam_lai'] >= NAM_ON_DINH)


if __name__ == '__main__':
    cfg = json.loads((DV.GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    t0 = time.time()
    m1 = hoc._m1_dai(g, 2015)
    fr = hoc._khung(m1, g)
    S = DV.nap_spread(g, m1.index, float(g.get('spread', 0.17)))
    tin = gia.tin_usd(g)[0] if g.get('lich_tin') else []
    D = DV.du_lieu(m1, S, tin)
    print(f'Vàng từ 2015: {len(m1):,} nến 1 phút · nạp {time.time() - t0:.0f} giây', flush=True)
    KQ: dict = {'cat_nam': DV.CAT_NAM, 'den': m1.index[-1].isoformat(), 'pp': {}, 'so_phep_so': 0, 'ap_dung': {}, 'on_dinh': {}}
    for ma in PP.DS:
        t1 = time.time()
        ct = CONG_THUC[ma]
        th = DV.tin_hieu(ma, fr['M15'], fr['H1'])
        nen = DV.chay(D, th, ma, vao=ct['vao'], sl=ct['sl'], tp=ct['tp'])
        bc = DV.boi_canh(D, th, fr['M15'], fr['H4'])
        bo = np.zeros(len(th), bool)
        for v in ct['loc']:
            if v in ('L6', 'H1', 'H2'):
                continue                                                  # bản nền của phép đo này: công thức phiếu trước L6 và hợp lưu
            bo |= bc[v]
        moi = loc_moi(th, fr)
        so = nen['so'].to_numpy()
        ban = {'nen': nen[~bo[so]], 'L5': nen[~(bo | moi['L5'])[so]], 'L6': nen[~(bo | moi['L6'])[so]]}
        bang = {k: DV.hai_phan(v) for k, v in ban.items()}
        nam = {k: theo_nam(v) for k, v in ban.items()}
        KQ['so_phep_so'] += 2
        giu, doi, vi = DV.chon(bang, 'nen')
        print(f'\n══════ {PP.DS[ma]["ten"]} ({ma}) · {len(th):,} tín hiệu · công thức phiếu {ct["vao"]}/{ct["sl"]}/{ct["tp"]}'
              + (f' + {",".join(ct["loc"])}' if ct['loc'] else '') + ' ══════\n' + DV.DAU_BANG)
        for k in ban:
            print(DV.dong(TEN[k], bang[k]) + f'\n     năm có lãi {nam[k]["nam_lai"]}/{nam[k]["so_nam"]} · '
                  + ' '.join(f'{y}:{v[1]:+.0f}' for y, v in nam[k]['nam'].items()))
        od = on_dinh(bang[giu], nam[giu])
        print(f'  → giữ {giu}: {vi} · {"CÓ LÃI ỔN ĐỊNH" if od else "chưa có lợi thế"} ({time.time() - t1:.0f} giây)'.replace('.', ','), flush=True)
        KQ['pp'][ma] = {'ten': PP.DS[ma]['ten'], 'cong_thuc': {**ct, 'loc': list(ct['loc'])}, 'bang': bang, 'theo_nam': nam, 'giu': giu, 'doi': doi, 'vi': vi,
                        'on_dinh': od}
        KQ['ap_dung'][ma] = giu
        KQ['on_dinh'][ma] = od
    print(f'\nSố phép so lần này: {KQ["so_phep_so"]} (cộng dồn với 107 phép so của cong-cu/diem_vao.py)')
    print('Giữ theo cổng: ' + json.dumps(KQ['ap_dung'], ensure_ascii=False) + '\nCó lãi ổn định: ' + json.dumps(KQ['on_dinh'], ensure_ascii=False))
    (DV.GOC / 'out').mkdir(exist_ok=True)
    (DV.GOC / 'out' / 'loc-xu-huong.json').write_text(json.dumps(KQ, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'Xong sau {time.time() - t0:.0f} giây. Kết quả: out/loc-xu-huong.json')
