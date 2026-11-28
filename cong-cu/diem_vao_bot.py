# -*- coding: utf-8 -*-
"""Đo điểm vào của luật bot tín hiệu theo đúng cách đã làm với tám phương pháp (cong-cu/diem_vao.py): độ đi ngược/đi thuận, kiểu vào, dừng lỗ, chốt
lời, bối cảnh. Biến thể và cổng ghi TRƯỚC khi đo ở cong-cu/CHUAN_HOA_DANG_KY.md (phần "Điểm vào của luật bot tín hiệu").

Bộ tín hiệu là đúng các lệnh mà bộ kiểm của bot đã vào (tinhieu.backtest.simulate, cấu hình webapp đang dùng). Mỗi lệnh được chấm RIÊNG bằng phép mô
phỏng của cong-cu/diem_vao.py: spread của từng nến, phí 0,18, trượt giá lúc tin, phí qua đêm, giữ tối đa 24 giờ. Chọn trên 2015–2021, xác nhận trên
2022 trở đi. Công cụ CHỈ ĐO: mã của bot (<LOCAL_RULES_ROOT>\\tinhieu) không bị sửa; vài hàm của nó chỉ bị bọc tạm trong bộ nhớ để ghi lại lệnh rồi được
trả lại ngay. Chỉ đọc tệp nến; không nối MT5. Kết quả ghi ở out/diem-vao-bot.json.

    python -X utf8 cong-cu/diem_vao_bot.py
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import gia, hoc, kiem_chung  # noqa: E402

KHOANG = (10.0, 35.0)             # khoảng dừng lỗ (giá) được nhận, tính từ giá khớp thật; bot dùng 17–28
ATR_GIA = 6.0                     # để S3 ("lùi thêm 0,5 ATR" trong phép mô phỏng chung) thành đúng "lùi thêm 3 giá"
TEN_VAO = {'V0': 'vào ngay (hiện tại)', 'V1': 'chờ hồi về giữa nến tín hiệu', 'V2': 'chờ phá đỉnh/đáy nến tín hiệu', 'V3': 'xác nhận nến M5'}
TEN_SL = {'S0': 'mức của bot (hiện tại)', 'S2': 'thêm đệm spread', 'S3': 'lùi thêm 3 giá'}
TEN_TP = {'TL': 'sáu phần 0,5R–3R (hiện tại)', 'T1': 'chốt hết ở 1R', 'T0': 'chốt hết ở 2R', 'TLB': 'sáu phần, dời về hòa vốn sau mức đầu'}
TEN_LOC = {'L1': 'bỏ khi trong 60 phút quanh tin', 'L2': 'bỏ khi spread trên 2 lần trung vị'}


def _nap(ten: str):
    spec = importlib.util.spec_from_file_location(ten, GOC / 'cong-cu' / f'{ten}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def lenh_cua_bot(g: dict, m1: pd.DataFrame, d1: pd.DataFrame, sp: float, khung: tuple) -> tuple[list, list]:
    """(các lệnh bộ kiểm của bot đã vào, tín hiệu bot đã dựng cho từng lệnh). Bọc tạm levels.build và backtest.simulate để ghi lại, rồi trả lại."""
    from tinhieu import backtest as BT, levels as LV                    # noqa: PLC0415 - mã của chủ dự án, chỉ đọc
    ghi, tho = {}, []
    goc_build, goc_sim = LV.build, BT.simulate

    def build(setup, bid, ask, now, seq):
        s = goc_build(setup, bid, ask, now, seq)
        if s is not None:
            ghi[(int(pd.Timestamp(now).timestamp()), s.code)] = s
        return s

    def simulate(setups, m1_, *a, **k):
        out = goc_sim(setups, m1_, *a, **k)
        tho.append(out)
        return out
    LV.build, BT.simulate = build, simulate
    try:
        kiem_chung._bot(g, m1, d1, sp, khung)
    finally:
        LV.build, BT.simulate = goc_build, goc_sim
    lenh = tho[0]
    return lenh, [ghi[(int(pd.Timestamp(x['entry_time']).timestamp()), x['tf'])] for x in lenh]


def thanh_tin_hieu(lenh: list, tin_hieu: list, D: dict, m15: pd.DataFrame, cac_muc: list) -> list[dict]:
    """Đưa lệnh của bot về dạng tín hiệu mà phép mô phỏng chung nhận: giờ, chiều, dừng lỗ, đỉnh và đáy nến tín hiệu, thang chốt lời."""
    T, H, L = D['T'], D['H'], D['L']
    dai = {'M5': 5, 'M15': 15, 'M30': 30}
    ra = []
    for x, s in zip(lenh, tin_hieu):
        t = pd.Timestamp(x['entry_time'])
        j = int(np.searchsorted(T, t.value, side='left'))
        j0 = int(np.searchsorted(T, t.value - dai[x['tf']] * 60 * 10 ** 9, side='left'))
        if j0 >= j:
            continue
        i15 = int(m15.index.searchsorted(t - pd.Timedelta(minutes=15), side='right')) - 1
        ra.append({'t': t, 'i': max(i15, 0), 'huong': 'MUA' if s.side == 'BUY' else 'BAN', 'kieu': 'thi_truong', 'vao': float(s.entry), 'sl': float(s.sl), 'atr': ATR_GIA,
                   'vung': None, 'muc_tieu': None, 'nen_h': float(H[j0:j].max()), 'nen_l': float(L[j0:j].min()), 'thang': list(cac_muc), 'rui_khoang': KHOANG,
                   'usd_bot': float(x['usd']), 'khung': x['tf']})
    return ra


if __name__ == '__main__':
    DV = _nap('diem_vao')
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    gia._nap_ma(g)
    from tinhieu import levels as LV                                    # noqa: E402
    t0 = time.time()
    m1 = hoc._m1_dai(g, 2015)
    fr = hoc._khung(m1, g)
    sp0 = float(g.get('spread', 0.17))
    khung = tuple((cfg.get('kiem_chung') or {}).get('khung_bot', ('M5', 'M15')))
    D = DV.du_lieu(m1, DV.nap_spread(g, m1.index, sp0), gia.tin_usd(g)[0] if g.get('lich_tin') else [])
    lenh, sig = lenh_cua_bot(g, m1, fr['D1'], sp0, khung)
    th = thanh_tin_hieu(lenh, sig, D, fr['M15'], LV.TP_R)
    print(f'Luật bot, vàng từ 2015, khung {", ".join(khung)}: bộ kiểm của bot vào {len(lenh):,} lệnh, tổng {sum(x["usd"] for x in lenh):+,.0f} giá theo cách chấm của bot · '
          f'đưa vào phép đo {len(th):,} lệnh · {time.time() - t0:.0f} giây', flush=True)
    KQ: dict = {'cat_nam': DV.CAT_NAM, 'so_lenh_bot': len(lenh), 'so_phep_so': 0, 'den': m1.index[-1].isoformat()}
    # A. mốc
    cu, moi = DV.chay(D, th, 'bot', tp='TL', chi_phi_cu=sp0), DV.chay(D, th, 'bot', tp='TL')
    KQ['A'] = {'cu': DV.hai_phan(cu), 'moi': DV.hai_phan(moi)}
    print('\nA. Mốc: bản hiện tại của bot, chấm bằng phép mô phỏng chung\n' + DV.DAU_BANG)
    print(DV.dong('chi phí cũ (spread 0,17 cố định + phí 0,18)', KQ['A']['cu']))
    print(DV.dong('chi phí mới (spread từng nến, tin, qua đêm)', KQ['A']['moi']))
    # B. đi ngược, đi thuận
    k = moi[moi['khop']]
    kh = DV.chay(D, th, 'bot', tp='TL', khong_tp=True)
    kh = kh[kh['khop']]
    pv = lambda x, q: round(float(np.quantile(x, q)), 2) if len(x) else None      # noqa: E731
    lai, lo = k[k['r'] > 0], k[k['r'] <= 0]
    KQ['B'] = {'n_lai': int(len(lai)), 'n_lo': int(len(lo)), 'mae_lai': [pv(lai['mae'], q) for q in (0.5, 0.75, 0.9)], 'mfe_lo': [pv(lo['mfe'], q) for q in (0.5, 0.75, 0.9)],
               'lo_tung_dat_nua_r': round(float((lo['mfe'] >= 0.5).mean() * 100), 1) if len(lo) else None,
               'khong_tp_dat': {str(x): round(float((kh['mfe'] >= x).mean() * 100), 1) for x in (0.5, 1, 2, 3)},
               'khong_tp_cham_sl': round(float((kh['ket'] == 'SL').mean() * 100), 1), 'khong_tp_het_gio': round(float((kh['ket'] == 'Hết giờ').mean() * 100), 1)}
    b = KQ['B']
    print(f'\nB. Đi ngược, đi thuận (R; trung vị / phân vị 75 / phân vị 90)\n'
          f'  Lệnh CÓ LÃI ({b["n_lai"]:,}): đi ngược tối đa {b["mae_lai"]}\n'
          f'  Lệnh LỖ ({b["n_lo"]:,}): đi thuận tối đa {b["mfe_lo"]} · {b["lo_tung_dat_nua_r"]}% lệnh lỗ đã từng đạt mức chốt đầu (0,5R)\n'
          f'  Không đặt chốt lời: tỷ lệ từng đạt 0,5R / 1R / 2R / 3R: {b["khong_tp_dat"]} · trong 24 giờ {b["khong_tp_cham_sl"]}% chạm dừng lỗ, {b["khong_tp_het_gio"]}% hết giờ mà chưa chạm '
          f'(dừng lỗ của bot rộng 17–28 giá nên phần lớn lệnh không đi hết 1R trong một ngày; không so được với mức 50 / 33 / 25% của tám phương pháp)')

    def buoc(ten, tieu_de, ten_ban, ds, goc, **co_dinh):
        bang = {}
        for v in ds:
            bang[v] = DV.hai_phan(DV.chay(D, th, 'bot', **{**co_dinh, ten: v}))
        KQ['so_phep_so'] += len(ds) - 1
        giu, doi, vi = DV.chon(bang, goc)
        print(f'\n{tieu_de}\n' + DV.DAU_BANG)
        for v in ds:
            print(DV.dong(f'{v} {ten_ban[v]}', bang[v]))
        print(f'  → giữ {giu}: {vi}')
        return {'bang': bang, 'giu': giu, 'doi': doi, 'vi': vi}

    KQ['C'] = buoc('vao', 'C. Kiểu vào', TEN_VAO, ('V0', 'V1', 'V2', 'V3'), 'V0', sl='S0', tp='TL')
    KQ['D1'] = buoc('sl', 'D1. Dừng lỗ', TEN_SL, ('S0', 'S2', 'S3'), 'S0', vao=KQ['C']['giu'], tp='TL')
    KQ['D2'] = buoc('tp', 'D2. Chốt lời', TEN_TP, ('TL', 'T1', 'T0', 'TLB'), 'TL', vao=KQ['C']['giu'], sl=KQ['D1']['giu'])
    # C: lệnh chờ bỏ lỡ lệnh loại nào
    ngay = moi.set_index('so')
    KQ['C']['lo'] = {}
    for v in ('V1', 'V2', 'V3'):
        x = DV.chay(D, th, 'bot', vao=v, tp='TL').set_index('so')
        bo = ngay.reindex(x.index[~x['khop'].to_numpy()])
        bo = bo[bo['khop'] == True]                                    # noqa: E712
        co = ngay.reindex(x.index[x['khop'].to_numpy()])
        co = co[co['khop'] == True]                                    # noqa: E712
        if len(bo) and len(co):
            KQ['C']['lo'][v] = {'n_lo': int(len(bo)), 'r_lo': round(float(bo['r'].mean()), 3), 'n_khop': int(len(co)), 'r_khop': round(float(co['r'].mean()), 3)}
            print(f'     {v}: nếu vào ngay, {len(bo):,} lệnh KHÔNG khớp cho {bo["r"].mean():+.3f}R mỗi lệnh; {len(co):,} lệnh có khớp cho {co["r"].mean():+.3f}R'.replace('.', ','))
    # E. bối cảnh
    giu = dict(vao=KQ['C']['giu'], sl=KQ['D1']['giu'], tp=KQ['D2']['giu'])
    bc = DV.boi_canh(D, th, fr['M15'], fr['H4'])
    nen = DV.chay(D, th, 'bot', **giu)
    bang = {'không lọc': DV.hai_phan(nen)}
    giu_l = []
    print('\nE. Bối cảnh (mỗi bộ lọc xét riêng)\n' + DV.DAU_BANG + '\n' + DV.dong('không lọc', bang['không lọc']))
    for v in ('L1', 'L2'):
        bang[v] = DV.hai_phan(nen[~bc[v][nen['so'].to_numpy()]])
        KQ['so_phep_so'] += 1
        tot = bang[v]['chinh']['n'] >= DV.TOI_THIEU and bang[v]['chinh']['r_tb'] > bang['không lọc']['chinh']['r_tb']
        dat, vi = DV.cong(bang['không lọc'], bang[v]) if tot else (False, 'không cải thiện trên phần chỉnh')
        if dat:
            giu_l.append(v)
        print(DV.dong(f'{v} {TEN_LOC[v]} (bỏ {int(bc[v][nen["so"].to_numpy()].sum()):,})', bang[v]) + f'\n     → {"GIỮ" if dat else "không giữ"}: {vi}')
    KQ['E'] = {'bang': bang, 'giu': giu_l}
    bo = np.zeros(len(th), bool)
    for v in giu_l:
        bo |= bc[v]
    KQ['cuoi'] = DV.hai_phan(nen[~bo[nen['so'].to_numpy()]])
    KQ['ap_dung'] = {**giu, 'loc': giu_l}
    print('\nBản cuối theo cổng (' + ', '.join(list(giu.values()) + giu_l) + ')\n' + DV.DAU_BANG + '\n' + DV.dong('bản hiện tại của bot', KQ['A']['moi']) + '\n' + DV.dong('bản cuối', KQ['cuoi']))
    theo_nam = nen[nen['khop']].groupby('nam')['r'].agg(['size', 'sum'])
    KQ['theo_nam'] = {int(y): [int(r['size']), round(float(r['sum']), 1)] for y, r in theo_nam.iterrows()}
    print('Bản cuối theo năm (lệnh, tổng R): ' + ' · '.join(f'{y}: {v[0]}, {v[1]:+.1f}' for y, v in KQ['theo_nam'].items()).replace('.', ','))
    print(f'\nSố phép so đã làm (không kể bản hiện tại): {KQ["so_phep_so"]}')
    (GOC / 'out').mkdir(exist_ok=True)
    (GOC / 'out' / 'diem-vao-bot.json').write_text(json.dumps(KQ, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'Xong sau {time.time() - t0:.0f} giây. Kết quả: out/diem-vao-bot.json')
