# -*- coding: utf-8 -*-
"""Đo điểm vào của hai luật trong sổ chạy bóng, luật xu hướng ba khung và luật đỉnh/đáy, theo đúng cách đã làm với tám phương pháp và luật bot:
kiểu vào (C) rồi mức chốt lời (D), chọn trên 2015–2021 và chỉ nhận khi qua cổng trên 2022–11/2026. Biến thể và cổng ghi TRƯỚC khi đo ở
cong-cu/CHUAN_HOA_DANG_KY.md (phần "Điểm vào của luật ba khung và luật đỉnh/đáy").

Bộ tín hiệu là đúng các lệnh mà bộ kiểm của từng luật đã vào (so_cong_khai.kiem_chung._ba_khung, _dinh_day). Mỗi lệnh được chấm RIÊNG bằng phép
mô phỏng chung của cong-cu/diem_vao.py. Chỉ ĐO: mã của EA Promax không bị sửa. Chỉ đọc tệp nến; không nối MT5. Kết quả ở out/diem-vao-luat-so.json
và .txt.

    python -X utf8 cong-cu/diem_vao_luat_so.py
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import gia, hoc, kiem_chung, phuong_phap as PP  # noqa: E402

TEN_VAO = {'V0': 'vào ngay (hiện tại)', 'V1': 'chờ hồi về giữa nến tín hiệu', 'V2': 'chờ phá đỉnh/đáy nến tín hiệu', 'V3': 'xác nhận nến M5'}
LUAT = {
    'ba_khung': {'ten': 'Luật xu hướng ba khung', 'tp_goc': 'R0.25', 'tp': ('R0.25', 'R0.5', 'T1', 'T0'), 'sl': 'S1',
                 'ten_tp': {'R0.25': 'chốt cách 5 giá = 0,25R (hiện tại)', 'R0.5': 'chốt cách 10 giá = 0,5R', 'T1': 'chốt cách 20 giá = 1R', 'T0': 'chốt cách 40 giá = 2R'}},
    'dinh_day': {'ten': 'Luật đỉnh/đáy', 'tp_goc': 'R1.5', 'tp': ('R1.5', 'R0.5', 'T1', 'T0'), 'sl': 'S0',
                 'ten_tp': {'R1.5': 'chốt ở 1,5R (hiện tại)', 'R0.5': 'chốt ở 0,5R', 'T1': 'chốt ở 1R', 'T0': 'chốt ở 2R'}},
}
SL_BA_KHUNG = 20.0


def _nap(ten: str):
    spec = importlib.util.spec_from_file_location(ten, GOC / 'cong-cu' / f'{ten}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def thanh_tin_hieu(lenh: list, luat: str, m15: pd.DataFrame) -> list[dict]:
    """Đưa lệnh của bộ kiểm về dạng tín hiệu của phép mô phỏng chung. Nến tín hiệu: nến M15 đóng ngay trước (hoặc đúng) lúc vào.
    Ba khung: dừng lỗ cách giá khớp 20 (cách S1 với ATR quy đổi). Đỉnh/đáy: dừng lỗ ở mức luật đã đặt (giá vào − chiều × khoảng rủi ro)."""
    H, L = m15['high'].to_numpy(dtype=float), m15['low'].to_numpy(dtype=float)
    ra = []
    for x in lenh:
        t = pd.Timestamp(x['t'])
        i = int(m15.index.searchsorted(t - pd.Timedelta(minutes=15), side='right')) - 1
        if i < 0:
            continue
        mua = x['huong'] == 'MUA'
        s = {'t': m15.index[i] + pd.Timedelta(minutes=15), 'i': i, 'huong': x['huong'], 'kieu': 'thi_truong', 'vao': float(x['vao']), 'vung': None, 'muc_tieu': None,
             'nen_h': float(H[i]), 'nen_l': float(L[i])}
        if luat == 'ba_khung':
            s.update(sl=float(x['vao']) - (1 if mua else -1) * SL_BA_KHUNG, atr=SL_BA_KHUNG / PP.SL_PHA_ATR, rui_khoang=(SL_BA_KHUNG - 0.5, SL_BA_KHUNG + 0.5))
        else:
            s.update(sl=float(x['vao']) - (1 if mua else -1) * float(x['rui_ro']), atr=1.0, rui_khoang=(0.3, 300.0))
        ra.append(s)
    return ra


if __name__ == '__main__':
    DV = _nap('diem_vao')
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    gia._nap_ma(g)
    t0 = time.time()
    m1 = hoc._m1_dai(g, 2015)
    fr = hoc._khung(m1, g)
    sp0 = float(g.get('spread', 0.17))
    tin = gia.tin_usd(g)[0] if g.get('lich_tin') else []
    D = DV.du_lieu(m1, DV.nap_spread(g, m1.index, sp0), tin)
    KQ: dict = {'cat_nam': DV.CAT_NAM, 'luat': {}, 'so_phep_so': 0}
    chu = []
    for luat, cf in LUAT.items():
        bo = kiem_chung._ba_khung(g, m1, fr, sp0, tin) if luat == 'ba_khung' else kiem_chung._dinh_day(g, m1, fr, sp0, tin)
        th = thanh_tin_hieu(bo['lenh'], luat, fr['M15'])
        kq = KQ['luat'][luat] = {'ten': cf['ten'], 'so_lenh': len(bo['lenh']), 'tin_hieu': len(th)}
        chu.append(f"\n══════ {cf['ten']} · bộ kiểm của luật vào {len(bo['lenh']):,} lệnh · đưa vào phép đo {len(th):,} · {time.time() - t0:.0f} giây ══════")

        def buoc(ten, tieu_de, ds, goc, ten_ban, **co_dinh):
            bang = {v: DV.hai_phan(DV.chay(D, th, 'bot', **{**co_dinh, ten: v})) for v in ds}
            KQ['so_phep_so'] += len(ds) - 1
            giu, doi, vi = DV.chon(bang, goc)
            chu.append(tieu_de + '\n' + DV.DAU_BANG)
            chu.extend(DV.dong(f'{v} {ten_ban[v]}', bang[v]) for v in ds)
            chu.append(f'  → giữ {giu}: {vi}')
            return {'bang': bang, 'giu': giu, 'doi': doi, 'vi': vi}

        kq['C'] = buoc('vao', 'C. Kiểu vào', ('V0', 'V1', 'V2', 'V3'), 'V0', TEN_VAO, sl=cf['sl'], tp=cf['tp_goc'])
        kq['D'] = buoc('tp', 'D. Chốt lời', cf['tp'], cf['tp_goc'], cf['ten_tp'], sl=cf['sl'], vao=kq['C']['giu'])
        cuoi = DV.chay(D, th, 'bot', sl=cf['sl'], vao=kq['C']['giu'], tp=kq['D']['giu'])
        kq['cuoi'] = DV.hai_phan(cuoi)
        kq['ap_dung'] = {'vao': kq['C']['giu'], 'tp': kq['D']['giu']}
        theo_nam = cuoi[cuoi['khop']].groupby('nam')['r'].agg(['size', 'sum', lambda r: (r > 0).mean() * 100])
        kq['theo_nam'] = {int(y): [int(v.iloc[0]), round(float(v.iloc[1]), 1), round(float(v.iloc[2]), 1)] for y, v in theo_nam.iterrows()}
        goc_ = kq['C']['bang']['V0']
        chu.append(f"Bản cuối theo cổng ({kq['C']['giu']}, {kq['D']['giu']})\n" + DV.DAU_BANG + '\n' + DV.dong('bản hiện tại của luật', goc_) + '\n' + DV.dong('bản cuối', kq['cuoi']))
        chu.append('Bản cuối theo năm (lệnh, tổng R, % thắng): ' + ' · '.join(f'{y}: {v[0]}, {v[1]:+.1f}, {v[2]:.1f}%' for y, v in kq['theo_nam'].items()).replace('.', ','))
    chu.append(f"\nSố phép so đã làm (không kể bản hiện tại): {KQ['so_phep_so']}")
    txt = '\n'.join(chu)
    print(txt)
    (GOC / 'out').mkdir(exist_ok=True)
    (GOC / 'out' / 'diem-vao-luat-so.json').write_text(json.dumps(KQ, ensure_ascii=False, indent=1), encoding='utf-8')
    (GOC / 'out' / 'diem-vao-luat-so.txt').write_text(txt + '\n', encoding='utf-8')
    print(f'\nXong sau {time.time() - t0:.0f} giây. Kết quả: out/diem-vao-luat-so.json và .txt')
