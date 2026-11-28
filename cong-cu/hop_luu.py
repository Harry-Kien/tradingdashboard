# -*- coding: utf-8 -*-
"""Hợp lưu giữa các phương pháp: một tín hiệu có tốt hơn khi phương pháp KHÁC cũng báo cùng chiều trong 60 phút tính tới lúc đó không?

Câu hỏi, hai bộ lọc (H1: ít nhất một phương pháp khác; H2: ít nhất hai), cổng và điều kiện "có lãi ổn định" đã ghi TRƯỚC khi đo ở
cong-cu/CHUAN_HOA_DANG_KY.md (phần "Hợp lưu giữa các phương pháp"). Bản nền là công thức đang dùng trên phiếu (phieu.CONG_THUC, kể cả L6), chấm bằng
đúng phép mô phỏng của cong-cu/diem_vao.py. Chỉ đọc tệp nến; không nối MT5, không đặt lệnh, không sửa luật nào. Kết quả ở out/hop-luu.json.

    python -X utf8 cong-cu/hop_luu.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diem_vao as DV  # noqa: E402 - cùng phép mô phỏng, cùng cổng
import loc_xu_huong as LX  # noqa: E402 - cùng bộ lọc L6, cùng cách tính năm có lãi
from so_cong_khai import gia, hoc, phuong_phap as PP  # noqa: E402
from so_cong_khai.phieu import CONG_THUC  # noqa: E402

CUA_SO = 60 * 60 * 10 ** 9      # 60 phút tính tới giờ tín hiệu (gồm cả cùng nến M15)
TEN = {'nen': 'bản nền (công thức trên phiếu)', 'H1': 'giữ khi ít nhất 1 phương pháp khác cùng chiều trong 60 phút',
       'H2': 'giữ khi ít nhất 2 phương pháp khác cùng chiều trong 60 phút'}


def _ns(s: dict) -> int:
    return pd.Timestamp(s['t']).value


def dem_hop_luu(TH: dict) -> dict:
    """{ma: mảng số phương pháp KHÁC có tín hiệu thô cùng chiều trong [t − 60 phút, t]} cho từng tín hiệu của từng phương pháp."""
    moc = {}
    for ma, th in TH.items():
        for h in ('MUA', 'BAN'):
            moc[(ma, h)] = np.sort(np.array([_ns(s) for s in th if s['huong'] == h], dtype=np.int64))
    out = {}
    for ma, th in TH.items():
        dem = np.zeros(len(th), dtype=int)
        for i, s in enumerate(th):
            t, h = _ns(s), s['huong']
            for khac in TH:
                if khac == ma:
                    continue
                a = moc[(khac, h)]
                if len(a) and np.searchsorted(a, t, side='right') > np.searchsorted(a, t - CUA_SO, side='left'):
                    dem[i] += 1
        out[ma] = dem
    return out


_HL: dict = {}


def bo_loc(ma: str, th: list, fr: dict, bc: dict, loc, DVm=DV) -> np.ndarray:
    """Mảng bool, True = tín hiệu BỊ bỏ bởi một trong các bộ lọc `loc` của phiếu: L1–L4 lấy từ `bc` (diem_vao.boi_canh), L6 theo xu hướng ba
    khung (loc_xu_huong), H1/H2 theo hợp lưu (cần tín hiệu thô của mọi phương pháp, tính một lần cho mỗi bộ nến)."""
    bo = np.zeros(len(th), bool)
    for v in loc:
        if v == 'L6':
            bo |= LX.loc_moi(th, fr)['L6']
        elif v in ('H1', 'H2'):
            k = (id(fr['M15']), len(fr['M15']), ma)
            if k not in _HL:
                _HL[k] = dem_hop_luu({m: (th if m == ma else DVm.tin_hieu(m, fr['M15'], fr['H1'])) for m in PP.DS})[ma]
            bo |= _HL[k] < int(v[1])
        else:
            bo |= bc[v]
    return bo


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
    TH = {ma: DV.tin_hieu(ma, fr['M15'], fr['H1']) for ma in PP.DS}
    HL = dem_hop_luu(TH)
    KQ: dict = {'cat_nam': DV.CAT_NAM, 'den': m1.index[-1].isoformat(), 'pp': {}, 'so_phep_so': 0, 'ap_dung': {}, 'on_dinh': {}}
    for ma in PP.DS:
        t1 = time.time()
        ct, th = CONG_THUC[ma], TH[ma]
        nen = DV.chay(D, th, ma, vao=ct['vao'], sl=ct['sl'], tp=ct['tp'])
        bc = DV.boi_canh(D, th, fr['M15'], fr['H4'])
        bo = bo_loc(ma, th, fr, bc, [v for v in ct['loc'] if v not in ('H1', 'H2')])   # bản nền: công thức phiếu TRƯỚC khi có hợp lưu
        so = nen['so'].to_numpy()
        ban = {'nen': nen[~bo[so]], 'H1': nen[~(bo | (HL[ma] < 1))[so]], 'H2': nen[~(bo | (HL[ma] < 2))[so]]}
        bang = {k: DV.hai_phan(v) for k, v in ban.items()}
        nam = {k: LX.theo_nam(v) for k, v in ban.items()}
        KQ['so_phep_so'] += 2
        giu, doi, vi = DV.chon(bang, 'nen')
        print(f'\n══════ {PP.DS[ma]["ten"]} ({ma}) · {len(th):,} tín hiệu · công thức phiếu {ct["vao"]}/{ct["sl"]}/{ct["tp"]}'
              + (f' + {",".join(ct["loc"])}' if ct['loc'] else '') + f' · có hợp lưu ≥1: {int((HL[ma] >= 1).sum()):,}, ≥2: {int((HL[ma] >= 2).sum()):,} ══════\n'
              + DV.DAU_BANG)
        for k in ban:
            print(DV.dong(TEN[k], bang[k]) + f'\n     năm có lãi {nam[k]["nam_lai"]}/{nam[k]["so_nam"]} · '
                  + ' '.join(f'{y}:{v[1]:+.0f}' for y, v in nam[k]['nam'].items()))
        od = LX.on_dinh(bang[giu], nam[giu])
        print(f'  → giữ {giu}: {vi} · {"CÓ LÃI ỔN ĐỊNH" if od else "chưa có lợi thế"} ({time.time() - t1:.0f} giây)'.replace('.', ','), flush=True)
        KQ['pp'][ma] = {'ten': PP.DS[ma]['ten'], 'cong_thuc': {**ct, 'loc': list(ct['loc'])}, 'bang': bang, 'theo_nam': nam, 'giu': giu, 'doi': doi, 'vi': vi,
                        'on_dinh': od}
        KQ['ap_dung'][ma] = giu
        KQ['on_dinh'][ma] = od
    print(f'\nSố phép so lần này: {KQ["so_phep_so"]} (cộng dồn với 123 phép so trước đó)')
    print('Giữ theo cổng: ' + json.dumps(KQ['ap_dung'], ensure_ascii=False) + '\nCó lãi ổn định: ' + json.dumps(KQ['on_dinh'], ensure_ascii=False))
    (DV.GOC / 'out').mkdir(exist_ok=True)
    (DV.GOC / 'out' / 'hop-luu.json').write_text(json.dumps(KQ, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'Xong sau {time.time() - t0:.0f} giây. Kết quả: out/hop-luu.json')
