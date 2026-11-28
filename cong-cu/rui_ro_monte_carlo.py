# -*- coding: utf-8 -*-
"""Rủi ro theo Monte Carlo: với chuỗi R mỗi lệnh đã đo, một năm giao dịch có thể tệ tới đâu, và vốn có thể bị cắt một nửa với xác suất bao nhiêu ở
từng mức rủi ro mỗi lệnh. Cách đo ghi TRƯỚC ở cong-cu/CHUAN_HOA_DANG_KY.md (phần "rủi ro theo Monte Carlo"). Đây là phép tính cho các mức rủi ro
cho trước, không phải khuyến nghị mức rủi ro hay lời khuyên đầu tư. Chỉ đọc tệp nến; không nối MT5; không sửa luật nào.

    python -X utf8 cong-cu/rui_ro_monte_carlo.py
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
LAN = 10_000
KHOI_TB = 10
MUC_RUI = (0.005, 0.01, 0.02, 0.05, 0.10, 0.25)
CAT = 2022


def _nap(ten: str):
    spec = importlib.util.spec_from_file_location(ten, GOC / 'cong-cu' / f'{ten}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def chi_so_khoi(n_goc: int, n: int, khoi_tb: float, g: np.random.Generator) -> np.ndarray:
    """Chỉ số của một chuỗi `n` lệnh lấy mẫu lại kiểu stationary bootstrap (khối liên tiếp, độ dài theo phân phối hình học, nối vòng)."""
    ra = np.empty(n, dtype=int)
    i = int(g.integers(n_goc))
    for k in range(n):
        if k and g.random() < 1.0 / khoi_tb:
            i = int(g.integers(n_goc))
        ra[k] = i
        i = (i + 1) % n_goc
    return ra


def mo_phong(r: np.ndarray, n_nam: int, lan: int = LAN, khoi_tb: float = KHOI_TB, muc_rui=MUC_RUI, hat: int = 0) -> dict:
    """Giả lập `lan` năm, mỗi năm `n_nam` lệnh lấy mẫu lại từ `r` (R mỗi lệnh)."""
    g = np.random.default_rng(hat)
    tong, sut, chuoi = np.empty(lan), np.empty(lan), np.empty(lan)
    chay = np.zeros(len(muc_rui))
    for k in range(lan):
        x = r[chi_so_khoi(len(r), n_nam, khoi_tb, g)]
        luy = np.r_[0.0, np.cumsum(x)]
        tong[k], sut[k] = luy[-1], (np.maximum.accumulate(luy) - luy).max()
        thua = (x <= 0).astype(int)
        dai, cur = 0, 0
        for v in thua:
            cur = cur + 1 if v else 0
            dai = max(dai, cur)
        chuoi[k] = dai
        for j, f in enumerate(muc_rui):
            von = np.cumprod(np.maximum(1 + f * x, 0.0))
            chay[j] += von.min() <= 0.5
    q = lambda a, p: round(float(np.quantile(a, p)), 1)            # noqa: E731
    return {'so_lenh_nam': int(n_nam), 'tong_r': {'trung_vi': q(tong, 0.5), 'p5': q(tong, 0.05), 'ty_le_nam_lo': round(float((tong < 0).mean() * 100), 1)},
            'sut_giam_r': {'trung_vi': q(sut, 0.5), 'p95': q(sut, 0.95)}, 'chuoi_thua_p95': int(np.quantile(chuoi, 0.95)),
            'mat_nua_von': {f'{f * 100:g}%': round(float(c / lan * 100), 1) for f, c in zip(muc_rui, chay)}}


if __name__ == '__main__':
    t0 = time.time()
    LB, LS = _nap('loc_lenh_bot'), _nap('diem_vao_luat_so')
    from so_cong_khai import gia, kiem_chung                           # noqa: E402
    ctx = LB.nap(json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8')))
    DV, D, fr = ctx['DV'], ctx['D'], ctx['fr']
    chuoi_r = {}
    L = LB.lenh_bot(ctx)
    df = DV.chay(D, L['th_all'], 'bot', tp='TL')
    chuoi_r['Luật bot (bản hiện tại)'] = df[df['khop']]
    tin = gia.tin_usd(ctx['g'])[0] if ctx['g'].get('lich_tin') else []
    bk = LS.thanh_tin_hieu(kiem_chung._ba_khung(ctx['g'], ctx['m1'], fr, ctx['sp0'], tin)['lenh'], 'ba_khung', fr['M15'])
    for ten, tp in (('Ba khung (bản hiện tại, chốt 0,25R)', 'R0.25'), ('Ba khung chốt 2R (bản qua cổng)', 'T0')):
        x = DV.chay(D, bk, 'bot', sl='S1', tp=tp)
        chuoi_r[ten] = x[x['khop']]
    KQ, chu = {}, ['RỦI RO THEO MONTE CARLO · 10.000 năm giả lập mỗi dòng · lấy mẫu lại theo khối (trung bình 10 lệnh) · không phải khuyến nghị mức rủi ro']
    for ten, x in chuoi_r.items():
        for nhan, m in (('2015–2021', x['nam'] < CAT), ('2022–2026', x['nam'] >= CAT)):
            r = x.loc[m, 'r'].to_numpy(dtype=float)
            nam = x.loc[m, 'nam']
            so_nam = nam.nunique() if nhan == '2015–2021' else (nam.nunique() - 1 + 330 / 365)    # 2026 mới qua khoảng 11 tháng
            kq = mo_phong(r, int(round(len(r) / so_nam)))
            KQ[f'{ten} · {nhan}'] = dict(kq, r_tb=round(float(r.mean()), 4), so_lenh=int(len(r)))
            mv = ' · '.join(f'{k}: {v:.1f}%' for k, v in kq['mat_nua_von'].items())
            chu.append(f"\n{ten} · dữ liệu {nhan} ({len(r):,} lệnh, {r.mean():+.3f}R mỗi lệnh, {kq['so_lenh_nam']} lệnh mỗi năm)\n"
                       f"  Tổng R một năm: trung vị {kq['tong_r']['trung_vi']:+.1f} · 5% năm tệ nhất dưới {kq['tong_r']['p5']:+.1f} · năm lỗ {kq['tong_r']['ty_le_nam_lo']:.1f}%\n"
                       f"  Sụt giảm lớn nhất trong năm: trung vị {kq['sut_giam_r']['trung_vi']:.1f}R · 5% năm tệ nhất trên {kq['sut_giam_r']['p95']:.1f}R · "
                       f"chuỗi thua liền (5% năm tệ nhất) từ {kq['chuoi_thua_p95']} lệnh\n"
                       f"  Xác suất vốn có lúc còn một nửa, theo rủi ro mỗi lệnh: {mv}")
    txt = '\n'.join(chu).replace('.', ',').replace(',py', '.py')
    print(txt)
    (GOC / 'out' / 'rui-ro-monte-carlo.json').write_text(json.dumps(KQ, ensure_ascii=False, indent=1), encoding='utf-8')
    (GOC / 'out' / 'rui-ro-monte-carlo.txt').write_text(txt + '\n', encoding='utf-8')
    print(f'\nXong sau {time.time() - t0:.0f} giây. Kết quả: out/rui-ro-monte-carlo.json và .txt')
