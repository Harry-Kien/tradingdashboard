# -*- coding: utf-8 -*-
"""Tỷ lệ thắng theo từng năm khi chỉ đổi mức chốt lời. Phép đo MÔ TẢ: không chọn biến thể, không đổi công thức nào. Cách đo ghi TRƯỚC ở
cong-cu/CHUAN_HOA_DANG_KY.md (phần "Tỷ lệ thắng theo năm và mức chốt lời").

Hai bộ lệnh: (1) tám phương pháp gộp lại, mỗi phương pháp theo đúng công thức phiếu (so_cong_khai/phieu.py); (2) các lệnh của luật bot tín hiệu,
vào ngay, dừng lỗ của bot. Mức chốt (chốt hết một lần): 0,25R · 0,5R · 1R · 2R; luật bot thêm thang sáu mức hiện tại. Phép mô phỏng chung của
cong-cu/diem_vao.py. Trước khi in số, kiểm rằng mức 2R của bộ (1) trùng "bản cuối" ở out/diem-vao.json và thang sáu mức của bộ (2) trùng bản hiện
tại ở out/diem-vao-bot.json. Chỉ đọc tệp nến; không nối MT5; mã của bot không bị sửa.

    python -X utf8 cong-cu/ty_le_thang_nam.py
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import gia, hoc, phieu, phuong_phap as PP  # noqa: E402

MUC = ('R0.25', 'R0.5', 'R1', 'R2')
TEN = {'R0.25': '0,25R', 'R0.5': '0,5R', 'R1': '1R', 'R2': '2R', 'TL': 'thang 6 mức'}


def _nap(ten: str):
    spec = importlib.util.spec_from_file_location(ten, GOC / 'cong-cu' / f'{ten}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def hoa_von(tp: str):
    """Tỷ lệ thắng hòa vốn trước chi phí khi thắng được +x R và thua −1R: 1 / (1 + x)."""
    return round(100 / (1 + float(tp[1:])), 1) if tp.startswith('R') else None


def bang_nam(df: pd.DataFrame) -> dict:
    """{năm: [lệnh, % thắng, R mỗi lệnh, tổng R]} cho các lệnh đã khớp; thêm khóa 'tat_ca'."""
    k = df[df['khop']]
    ra = {}
    for y, x in list(k.groupby('nam')) + [('tat_ca', k)]:
        r = x['r'].to_numpy()
        ra[str(y)] = [int(len(r)), round(float((r > 0).mean() * 100), 1), round(float(r.mean()), 3), round(float(r.sum()), 1)] if len(r) else [0, None, None, 0.0]
    return ra


def tom_tat(b: dict) -> dict:
    nam = {y: v for y, v in b.items() if y != 'tat_ca' and v[0]}
    return {'nam_tu_75': sum(1 for v in nam.values() if v[1] is not None and v[1] >= 75), 'nam_duong': sum(1 for v in nam.values() if v[3] > 0), 'so_nam': len(nam)}


def in_bang(tieu: str, cac: dict) -> str:
    nams = sorted({y for b in cac.values() for y in b if y != 'tat_ca'})
    dong = [tieu, 'Mỗi ô: % lệnh thắng · R mỗi lệnh (sau chi phí)', 'Năm   ' + ''.join(f'{TEN[t]:>22s}' for t in cac)]
    for y in nams + ['tat_ca']:
        o = ''
        for b in cac.values():
            v = b.get(y)
            o += f'{"—":>22s}' if not v or not v[0] else f'{v[1]:6.1f}% {v[2]:+7.3f}R ({v[0]:5d})'.rjust(22)
        dong.append(f'{("Cả kỳ" if y == "tat_ca" else y):6s}' + o)
    dong.append('Năm ≥75% thắng ' + ''.join(f'{str(tom_tat(b)["nam_tu_75"]) + "/" + str(tom_tat(b)["so_nam"]):>22s}' for b in cac.values()))
    dong.append('Năm tổng R dương' + ''.join(f'{str(tom_tat(b)["nam_duong"]) + "/" + str(tom_tat(b)["so_nam"]):>21s}' for b in cac.values()))
    dong.append('Hòa vốn (trước phí)' + ''.join(f'{(str(hoa_von(t)) + "%") if hoa_von(t) else "—":>19s}' for t in cac))
    return '\n'.join(dong).replace('.', ',')


if __name__ == '__main__':
    DV = _nap('diem_vao')
    DB = _nap('diem_vao_bot')
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    gia._nap_ma(g)
    t0 = time.time()
    m1 = hoc._m1_dai(g, 2015)
    fr = hoc._khung(m1, g)
    sp0 = float(g.get('spread', 0.17))
    D = DV.du_lieu(m1, DV.nap_spread(g, m1.index, sp0), gia.tin_usd(g)[0] if g.get('lich_tin') else [])
    print(f'Nạp {len(m1):,} nến 1 phút · {time.time() - t0:.0f} giây', flush=True)
    cu = json.loads((GOC / 'out' / 'diem-vao.json').read_text(encoding='utf-8'))
    cu_bot = json.loads((GOC / 'out' / 'diem-vao-bot.json').read_text(encoding='utf-8'))
    KQ: dict = {'pp': {}, 'gop': {}, 'bot': {}, 'tom_tat': {}}

    # (1) tám phương pháp theo công thức phiếu
    gop = {t: [] for t in MUC}
    for ma in PP.DS:
        ct = phieu.CONG_THUC[ma]
        th = DV.tin_hieu(ma, fr['M15'], fr['H1'])
        bc = DV.boi_canh(D, th, fr['M15'], fr['H4'])
        bo = _nap('hop_luu').bo_loc(ma, th, fr, bc, ct['loc'], DV)          # mọi bộ lọc trên phiếu, kể cả L6 và hợp lưu
        KQ['pp'][ma] = {}
        for t in MUC:
            df = DV.chay(D, th, ma, vao=ct['vao'], sl=ct['sl'], tp=t)
            df = df[~bo[df['so'].to_numpy()]]
            if t == 'R2':                                               # kiểm: phải trùng bản cuối đã đo
                hp = DV.hai_phan(df)
                for phan in ('chinh', 'kiem'):
                    a, b = hp[phan], cu['pp'][ma]['cuoi'][phan]
                    assert (a['n'], a['thang'], a['r_tb']) == (b['n'], b['thang'], b['r_tb']), (ma, phan, a, b)
            KQ['pp'][ma][t] = bang_nam(df)
            gop[t].append(df)
        print(f'{ma}: {len(th):,} tín hiệu · 2R trùng bản cuối đã đo', flush=True)
    for t in MUC:
        KQ['gop'][t] = bang_nam(pd.concat(gop[t]))

    # (2) luật bot
    from tinhieu import levels as LV                                    # noqa: E402
    khung = tuple((cfg.get('kiem_chung') or {}).get('khung_bot', ('M5', 'M15')))
    lenh, sig = DB.lenh_cua_bot(g, m1, fr['D1'], sp0, khung)
    thb = DB.thanh_tin_hieu(lenh, sig, D, fr['M15'], LV.TP_R)
    for t in ('TL',) + MUC:
        df = DV.chay(D, thb, 'bot', tp=t)
        if t == 'TL':
            hp = DV.hai_phan(df)
            for phan in ('chinh', 'kiem'):
                a, b = hp[phan], cu_bot['A']['moi'][phan]
                assert (a['n'], a['thang'], a['r_tb']) == (b['n'], b['thang'], b['r_tb']), ('bot', phan, a, b)
        KQ['bot'][t] = bang_nam(df)
    print(f'luật bot: {len(thb):,} lệnh · thang sáu mức trùng bản hiện tại đã đo', flush=True)

    KQ['tom_tat'] = {'gop': {t: tom_tat(KQ['gop'][t]) for t in MUC}, 'bot': {t: tom_tat(KQ['bot'][t]) for t in KQ['bot']},
                     'hoa_von': {t: hoa_von(t) for t in MUC}}
    chu = [in_bang('\n(1) TÁM PHƯƠNG PHÁP GỘP, THEO CÔNG THỨC PHIẾU · chỉ đổi mức chốt lời', KQ['gop']),
           in_bang(f'\n(2) LUẬT BOT TÍN HIỆU ({len(thb):,} lệnh, vào ngay, dừng lỗ của bot) · chỉ đổi mức chốt lời', KQ['bot'])]
    chu.append('\nTỪNG PHƯƠNG PHÁP, CẢ KỲ 2015–2026: % thắng · R mỗi lệnh')
    for ma in PP.DS:
        chu.append(f'{ma:13s}' + ''.join(f'{KQ["pp"][ma][t]["tat_ca"][1]:6.1f}% {KQ["pp"][ma][t]["tat_ca"][2]:+7.3f}R'.rjust(22) for t in MUC).replace('.', ','))
    txt = '\n'.join(chu)
    print(txt)
    (GOC / 'out').mkdir(exist_ok=True)
    (GOC / 'out' / 'ty-le-thang-nam.json').write_text(json.dumps(KQ, ensure_ascii=False, indent=1), encoding='utf-8')
    (GOC / 'out' / 'ty-le-thang-nam.txt').write_text(txt + '\n', encoding='utf-8')
    print(f'\nGhi out/ty-le-thang-nam.json và .txt · {time.time() - t0:.0f} giây')
