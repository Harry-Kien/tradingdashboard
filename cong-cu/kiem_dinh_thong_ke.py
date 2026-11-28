# -*- coding: utf-8 -*-
"""Kiểm định thống kê cho hai thứ webapp đang dùng để lọc điểm vào, theo cách các bài báo về dự báo tài chính đòi hỏi
(so với chuẩn đơn giản, sai số có tính tới phụ thuộc theo thời gian, và tính tới việc đã thử nhiều phương án):

1. ĐIỂM MÔ HÌNH (nhóm 10% điểm cao nhất). Cuốn chiếu theo năm như cong-cu/kiem_mo_hinh.py: mỗi năm thi, mô hình chỉ học các năm trước đó.
   Hỏi hai câu: (a) lãi mỗi lệnh của nhóm được chọn có khác 0 không; (b) có hơn "không lọc gì" không (chuẩn đơn giản).
   Các tín hiệu dồn cụm theo thời gian nên không coi từng lệnh là độc lập: gộp theo tuần rồi lấy mẫu lại kiểu stationary bootstrap
   (Politis và Romano, 1994; khối dài trung bình 4 tuần). In khoảng tin cậy 95% và giá trị p một phía.
2. NÚT KỶ LUẬT ("có lãi ở cả hai nửa"). Một bối cảnh không có lợi thế thật vẫn có khoảng 1/4 khả năng có lãi ở cả hai nửa chỉ nhờ may.
   Đếm trong số liệu đang dùng (out/hoc.json): bao nhiêu bối cảnh đủ mẫu, bao nhiêu cái "giữ", so với con số chờ đợi nếu tất cả chỉ là may.

Chỉ đọc tệp nến và out/hoc.json; không nối MT5. Số ngẫu nhiên cố định hạt giống để chạy lại ra cùng kết quả.

    python -X utf8 cong-cu/kiem_dinh_thong_ke.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import mo_hinh as M  # noqa: E402

TU, LAN, KHOI = 2019, 10000, 4          # năm thi đầu tiên · số lần lấy mẫu lại · độ dài khối trung bình (tuần)


def chi_so_khoi(n: int, lan: int, khoi: float, rng) -> np.ndarray:
    """Stationary bootstrap: mỗi hàng là một dãy chỉ số dài n, ghép từ các khối liên tiếp có độ dài ngẫu nhiên (trung bình `khoi`)."""
    moi = rng.random((lan, n)) < 1.0 / khoi
    moi[:, 0] = True
    dau = rng.integers(0, n, size=(lan, n))
    idx = np.empty((lan, n), dtype=np.int64)
    idx[:, 0] = dau[:, 0]
    for j in range(1, n):
        idx[:, j] = np.where(moi[:, j], dau[:, j], (idx[:, j - 1] + 1) % n)
    return idx


def kiem(tuan: pd.DataFrame, ten: str, rng) -> dict:
    """tuan: mỗi hàng một tuần, cột s_chon, n_chon, s_tat, n_tat (tổng R và số lệnh của nhóm được chọn và của mọi tín hiệu)."""
    a = tuan[['s_chon', 'n_chon', 's_tat', 'n_tat']].to_numpy(dtype=float)
    tb = lambda x: x[..., 0].sum(-1) / np.maximum(x[..., 1].sum(-1), 1)                        # noqa: E731 - lãi mỗi lệnh của nhóm được chọn
    hon = lambda x: tb(x) - x[..., 2].sum(-1) / np.maximum(x[..., 3].sum(-1), 1)               # noqa: E731 - hơn mức "không lọc"
    b = a[chi_so_khoi(len(a), LAN, KHOI, rng)]
    out = {}
    for nhan, f in (('so với 0', tb), ('so với không lọc', hon)):
        that, gia = float(f(a)), f(b)
        thap, cao = np.quantile(gia, [0.025, 0.975])
        p = float(((gia - that) >= that).mean())                                              # một phía, giả thuyết gốc: không lớn hơn 0
        out[nhan] = (that, float(thap), float(cao), p)
        print(f'  {ten} · {nhan}: {that:+.3f}R mỗi lệnh · khoảng tin cậy 95% [{thap:+.3f}; {cao:+.3f}] · p một phía = {p:.3f}')
    return out


def may_rui(cfg: dict) -> None:
    tep = GOC / cfg.get('thu_muc_ra', 'out') / 'hoc.json'
    if not tep.exists():
        print('  Chưa có out/hoc.json (mở webapp một lần để nó tính).')
        return
    d = json.loads(tep.read_text(encoding='utf-8'))
    d = d.get('kq', d)
    dem = {'giu': 0, 'lo': 0, 'khong_on': 0, 'chua_du': 0}
    rieng = {}
    for ma, r in d['luat'].items():
        for khoa, s in r['theo'].items():
            dem[s['nhan_xet']] += 1
            if s['nhan_xet'] != 'chua_du':
                rieng.setdefault(khoa.count('|'), []).append(s['nhan_xet'])
    du = dem['giu'] + dem['lo'] + dem['khong_on']
    print(f'  {len(d["luat"])} luật và phương pháp · {sum(dem.values())} bối cảnh (chiều, chiều+phiên, chiều+phiên+biên độ) · {du} cái đủ mẫu (mỗi nửa từ 30 lệnh)')
    print(f'  Trong {du} cái đủ mẫu: "có lãi cả hai nửa" {dem["giu"]} ({dem["giu"] / du * 100:.0f}%) · "lỗ cả hai nửa" {dem["lo"]} ({dem["lo"] / du * 100:.0f}%) · '
          f'"không ổn định" {dem["khong_on"]} ({dem["khong_on"] / du * 100:.0f}%)')
    print(f'  Nếu KHÔNG bối cảnh nào có lợi thế thật (lãi trung bình đúng bằng 0): chờ đợi khoảng {du * 0.25:.0f} cái "có lãi cả hai nửa" chỉ nhờ may (25%).')
    for cap, ten in ((0, 'chỉ theo chiều'), (1, 'chiều + phiên'), (2, 'chiều + phiên + biên độ')):
        x = rieng.get(cap, [])
        if x:
            print(f'     {ten}: {len(x)} đủ mẫu, {x.count("giu")} "có lãi cả hai nửa" ({x.count("giu") / len(x) * 100:.0f}%)')


if __name__ == '__main__':
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    rng = np.random.default_rng(20261123)
    d = M.du_lieu(cfg)
    X = M.cot()
    cac = []
    for nam in range(TU, int(d['nam'].max()) + 1):
        hoc_ = d[d['nam'] < nam]
        th_ = M._hoc(hoc_)                                              # chỉ học dữ liệu trước năm thi; ngưỡng cũng lấy từ quãng học
        nguong = np.quantile(M._p(hoc_[X].to_numpy(dtype=float), *th_), 0.9)
        thi = d[d['nam'] == nam].copy()
        thi['chon'] = M._p(thi[X].to_numpy(dtype=float), *th_) >= nguong
        cac.append(thi)
    a = pd.concat(cac, ignore_index=True)
    a['tuan'] = pd.DatetimeIndex(pd.to_datetime(a['t'], utc=True)).tz_localize(None).to_period('W')
    print(f'Cuốn chiếu {TU}–{int(a["nam"].max())}: {len(a):,} tín hiệu ngoài mẫu, {int(a["chon"].sum()):,} cái được chọn (điểm từ 90) · '
          f'{a["tuan"].nunique()} tuần · {LAN:,} lần lấy mẫu lại, khối trung bình {KHOI} tuần')
    print('\n=== 1. ĐIỂM MÔ HÌNH: nhóm 10% điểm cao nhất, mỗi tín hiệu chấm riêng ===')
    kq = {}
    for cot, ten in (('r2', 'Chốt ở 2R'), ('r1', 'Chốt ở 1R')):
        g = a.groupby('tuan')
        tuan = pd.DataFrame({'s_chon': a[cot].where(a['chon'], 0.0).groupby(a['tuan']).sum(), 'n_chon': a['chon'].groupby(a['tuan']).sum(),
                             's_tat': g[cot].sum(), 'n_tat': g[cot].size()})
        kq[cot] = kiem(tuan, ten, rng)
    so_thu = 16                                                         # cong-cu/huan_luyen.py đã thử 2 loại mô hình × 2 đích × 4 ngưỡng trước khi chọn cấu hình này
    p_min = min(v['so với không lọc'][3] for v in kq.values())
    print(f'  Lưu ý về thử nhiều phương án: trước khi chọn cấu hình này đã thử ít nhất {so_thu} cấu hình (2 loại mô hình × 2 đích × 4 ngưỡng). Hiệu chỉnh '
          f'Bonferroni: p phải dưới {0.05 / so_thu:.4f} mới coi là có ý nghĩa ở mức 5%; p nhỏ nhất ở trên là {p_min:.3f}.')
    print('\n=== 2. NÚT KỶ LUẬT: bao nhiêu bối cảnh "có lãi cả hai nửa" có thể chỉ là may ===')
    may_rui(cfg)
