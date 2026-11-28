# -*- coding: utf-8 -*-
"""Kiểm định SPA (thư viện arch) cho các công thức trên phiếu vào lệnh: sau khi tính tới việc có tám công thức cùng được xem, có công thức nào có
lãi kỳ vọng lớn hơn 0 một cách có ý nghĩa thống kê không?

Mỗi công thức (so_cong_khai/phieu.CONG_THUC) được chấm bằng đúng phép mô phỏng của cong-cu/diem_vao.py (mỗi tín hiệu chấm riêng, spread từng nến,
trượt giá lúc tin, phí qua đêm), rồi gộp lãi lỗ theo tuần của giờ thoát lệnh (đơn vị R; tuần không có lệnh tính 0). Chuẩn so sánh là không vào lệnh.
Ba quãng: phần chỉnh 2015–2021, phần kiểm tra 2022 trở đi, và cả quãng. Hai tập: tám công thức trên phiếu; và mười sáu (thêm tám luật gốc).
Đọc giá trị p "nhất quán": dưới 0,05 nghĩa là công thức tốt nhất của tập khó giải thích chỉ bằng may rủi.

Giới hạn phải nhớ khi đọc: các công thức này đã được CHỌN trên phần chỉnh và XÁC NHẬN trên phần kiểm tra trong 107 phép so. Kiểm định SPA chỉ tính
tới số chiến lược đưa vào nó (8 hoặc 16), không tính tới 107 phép so đó, nên giá trị p ở đây lạc quan hơn thực tế. Phép này là mô tả, không chọn gì.
Chỉ đọc tệp nến; không nối MT5.

    python -X utf8 cong-cu/spa_phieu.py
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from arch.bootstrap import SPA

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import gia, hoc, phieu, phuong_phap as PP  # noqa: E402

TUAN = 7 * 24 * 3600 * 10 ** 9
LAN, KHOI = 10000, 4


def _nap(ten: str):
    spec = importlib.util.spec_from_file_location(ten, GOC / 'cong-cu' / f'{ten}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def theo_tuan(df: pd.DataFrame) -> pd.Series:
    """Tổng R theo tuần (chỉ số = số thứ tự tuần tính từ 1970) của các lệnh đã khớp."""
    k = df[df['khop']]
    return k.groupby(k['t_ra'] // TUAN)['r'].sum()


def p_spa(x: np.ndarray, hat: int = 20261124) -> dict:
    """Ba giá trị p của SPA cho bảng x (tuần × chiến lược), chuẩn so sánh là 0. arch làm việc với mất mát, nên mất mát của chiến lược là −lãi."""
    s = SPA(np.zeros(len(x)), -x, block_size=KHOI, reps=LAN, bootstrap='stationary', studentize=True, seed=hat)
    s.compute()
    return {k: float(s.pvalues[e]) for k, e in (('duoi', 'lower'), ('nhat_quan', 'consistent'), ('tren', 'upper'))}


if __name__ == '__main__':
    DV = _nap('diem_vao')
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    t0 = time.time()
    m1 = hoc._m1_dai(g, 2015)
    fr = hoc._khung(m1, g)
    D = DV.du_lieu(m1, DV.nap_spread(g, m1.index, float(g.get('spread', 0.17))), gia.tin_usd(g)[0] if g.get('lich_tin') else [])
    cot = {}
    for ma in PP.DS:
        ct = phieu.CONG_THUC[ma]
        th = DV.tin_hieu(ma, fr['M15'], fr['H1'])
        bc = DV.boi_canh(D, th, fr['M15'], fr['H4'])
        bo = _nap('hop_luu').bo_loc(ma, th, fr, bc, ct['loc'], DV)          # mọi bộ lọc trên phiếu, kể cả L6 và hợp lưu
        cot[f'phiếu {ma}'] = theo_tuan(DV.chay(D, th, ma, giu=~bo, vao=ct['vao'], sl=ct['sl'], tp=ct['tp']))
        cot[f'gốc {ma}'] = theo_tuan(DV.chay(D, th, ma))
    bang = pd.DataFrame(cot)
    bang = bang.reindex(range(int(bang.index.min()), int(bang.index.max()) + 1)).fillna(0.0)
    nam = pd.to_datetime(bang.index.to_numpy() * TUAN, utc=True).year
    print(f'{len(bang)} tuần · {bang.shape[1]} chuỗi · {LAN:,} lần lấy mẫu lại, khối trung bình {KHOI} tuần · nạp và chấm {time.time() - t0:.0f} giây', flush=True)
    kq = {}
    ph = [c for c in bang.columns if c.startswith('phiếu')]
    for ten_q, chon in (('Phần chỉnh 2015–2021', nam < DV.CAT_NAM), ('Phần kiểm tra 2022 trở đi', nam >= DV.CAT_NAM), ('Cả quãng', np.ones(len(bang), bool))):
        x = bang[chon]
        print(f'\n{ten_q} ({len(x)} tuần)')
        for ten_t, cs in (('Tám công thức trên phiếu', ph), ('Mười sáu: thêm tám luật gốc', list(bang.columns))):
            a = x[cs].to_numpy(dtype=float)
            tb = a.mean(0) / np.where(a.std(0) > 0, a.std(0), np.inf)
            tot = cs[int(np.argmax(tb))]
            p = p_spa(a)
            kq[f'{ten_q} · {ten_t}'] = {'tot': tot, 'tong_r': round(float(x[tot].sum()), 1), 'so_duong': int((a.sum(0) > 0).sum()), **{k: round(v, 4) for k, v in p.items()}}
            print(f'  {ten_t}: {int((a.sum(0) > 0).sum())}/{len(cs)} có tổng dương · tốt nhất "{tot}" tổng {x[tot].sum():+.1f}R · '
                  f'p dưới {p["duoi"]:.3f} · p nhất quán {p["nhat_quan"]:.3f} · p trên {p["tren"]:.3f}'.replace('.', ','))
    (GOC / 'out').mkdir(exist_ok=True)
    (GOC / 'out' / 'spa-phieu.json').write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding='utf-8')
    print('\nNhắc lại: các công thức này đã được chọn và xác nhận qua 107 phép so mà kiểm định này không tính tới, nên giá trị p ở phần kiểm tra lạc quan hơn thực tế.')
