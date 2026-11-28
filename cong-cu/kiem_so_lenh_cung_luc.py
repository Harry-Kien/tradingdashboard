# -*- coding: utf-8 -*-
"""Số lệnh mở cùng lúc có làm đổi kết quả của nhóm điểm mô hình từ 90 không?

Phép này được viết ngày 23/11/2026 để tìm vì sao nhóm đó có lãi khi chấm riêng từng tín hiệu nhưng lỗ khi mô phỏng. Nó cho thấy số lệnh
cùng lúc KHÔNG phải nguyên nhân (một lệnh hay không giới hạn đều âm như nhau); nguyên nhân thật là rò rỉ ở đặc trưng đồng thuận lúc học,
đã sửa cùng ngày (xem README, mục Kiểm định thống kê).

Cuốn chiếu theo năm như cong-cu/kiem_mo_hinh.py (mỗi năm thi, mô hình chỉ học các năm trước). Mỗi tín hiệu được chọn được chấm riêng bằng đúng
phuong_phap.cham() (vào, dừng lỗ, chốt 2R, giữ tối đa 24 giờ, chi phí của cấu hình), rồi xếp lại theo số lệnh được phép mở CÙNG LÚC:
một lệnh, hai, ba, năm, không giới hạn. Một tín hiệu chỉ được nhận nếu lúc nó khớp còn chỗ trống. In lãi mỗi lệnh, tổng, sụt giảm lớn nhất
(tính theo R, cộng dồn theo lúc thoát) và số tháng có lãi cho từng mức, kèm so sánh lệnh được nhận với lệnh bị bỏ khi chỉ cho một lệnh.

Đây là phép CHẨN ĐOÁN, không phải đề xuất cách vào lệnh: mở nhiều lệnh cùng lúc là nhân rủi ro lên bấy nhiêu lần, vì các tín hiệu dồn cụm
thường thắng thua cùng nhau. Chỉ đọc tệp nến; không nối MT5.

    python -X utf8 cong-cu/kiem_so_lenh_cung_luc.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import hoc, mo_hinh as M, phuong_phap as PP  # noqa: E402

TU = 2019


def chon_cuon_chieu(cfg: dict):
    """(m1, [(tín hiệu, mã phương pháp)]) của các tín hiệu có điểm từ 90, mỗi năm chỉ học các năm trước. Cùng cách với kiem_mo_hinh.py."""
    g = cfg['gia']
    d = M.du_lieu(cfg)
    m1 = hoc._m1_dai(g, 2015)
    fr = hoc._khung(m1, g)
    f = M.bang_nen(fr['M15'])
    rows, sig = [], []
    for ma in PP.DS:
        th = PP.quet(ma, fr['M15'], fr['H1'])
        if not th:
            continue
        t = pd.DatetimeIndex([s['t'] for s in th])
        b = M._bang(f, fr['H1'], fr['D1'], t, np.array([1.0 if s['huong'] == 'MUA' else -1.0 for s in th]), np.array([abs(s['vao'] - s['sl']) for s in th]), ma)
        b.insert(0, 't', t)
        b.insert(1, 'ma', ma)
        b.insert(2, 'huong', [s['huong'] for s in th])
        rows.append(b)
        sig += [(s, ma) for s in th]
    a = M.them_dong_thuan(pd.concat(rows, ignore_index=True)).replace([np.inf, -np.inf], np.nan)
    a['nam'] = pd.DatetimeIndex(a['t']).year
    X, idx = M.cot(), []
    for nam in range(TU, int(a['nam'].max()) + 1):
        hoc_ = d[d['nam'] < nam]
        th_ = M._hoc(hoc_)
        nguong = np.quantile(M._p(hoc_[X].to_numpy(dtype=float), *th_), 0.9)
        q = a[a['nam'] == nam].dropna(subset=M.DAC)
        idx += list(q.index[M._p(q[X].to_numpy(dtype=float), *th_) >= nguong])
    return m1, [sig[i] for i in sorted(idx)], float(g.get('spread', 0.17))


def cham_rieng(m1: pd.DataFrame, chon: list, sp: float) -> pd.DataFrame:
    """Mỗi tín hiệu chấm một mình (lệnh chờ được đủ CHO_NEN nến để khớp). Cắt một đoạn nến quanh tín hiệu cho nhanh."""
    idx, rows = m1.index, []
    dai = PP.CHO_NEN * 15 + PP.GIU_PHUT + PP.TRE_PHUT + 30
    for s, ma in chon:
        j = int(idx.searchsorted(pd.Timestamp(s['t']), side='left'))
        if j + dai > len(idx):
            continue                                                # sát cuối dữ liệu: không đủ nến để chấm trọn
        r = PP.cham([s], m1.iloc[j:j + dai], sp)
        if r:
            rows.append({'t_th': pd.Timestamp(s['t']), 'ma': ma, 'kieu': s['kieu'], 'huong': s['huong'], 'vao': pd.Timestamp(r[0]['t']), 'ra': pd.Timestamp(r[0]['ra']),
                         'r': r[0]['r'], 'ket': r[0]['ket']})
    return pd.DataFrame(rows).sort_values(['vao', 't_th']).reset_index(drop=True)


def xep(d: pd.DataFrame, k: int | None) -> np.ndarray:
    """Đánh dấu lệnh được nhận khi chỉ cho `k` lệnh mở cùng lúc (None = không giới hạn). Xét theo thứ tự khớp."""
    if k is None:
        return np.ones(len(d), dtype=bool)
    nhan, mo = np.zeros(len(d), dtype=bool), []
    vao, ra = d['vao'].to_numpy(), d['ra'].to_numpy()
    for i in range(len(d)):
        mo = [x for x in mo if x >= vao[i]]                         # lệnh thoát đúng phút này vẫn tính là còn mở, như cham() (t0 <= ban thì bỏ)
        if len(mo) < k:
            nhan[i] = True
            mo.append(ra[i])
    return nhan


def tom(d: pd.DataFrame, ten: str) -> None:
    if not len(d):
        print(f'  {ten}: không có lệnh')
        return
    x = d.sort_values('ra')
    luy = x['r'].cumsum().to_numpy()
    sut = float((np.maximum.accumulate(np.maximum(luy, 0)) - luy).max())
    thang = x.groupby(pd.DatetimeIndex(x['ra']).tz_localize(None).to_period('M'))['r'].sum()
    print(f'  {ten}: {len(d):>5,} lệnh · thắng {(d["r"] > 0).mean() * 100:.1f}% · {d["r"].mean():+.3f}R mỗi lệnh · tổng {d["r"].sum():+7.1f}R · '
          f'sụt giảm lớn nhất {sut:5.1f}R · {int((thang > 0).sum())}/{len(thang)} tháng có lãi')


if __name__ == '__main__':
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    m1, chon, sp = chon_cuon_chieu(cfg)
    d = cham_rieng(m1, chon, sp)
    print(f'Cuốn chiếu {TU}–{d["vao"].dt.year.max()}: {len(chon):,} tín hiệu có điểm từ 90, {len(d):,} cái khớp lệnh khi chấm riêng · chốt 2R, chi phí của cấu hình')
    print('\n=== Theo số lệnh được mở cùng lúc ===')
    for k, ten in ((1, 'một lệnh      '), (2, 'hai lệnh      '), (3, 'ba lệnh       '), (5, 'năm lệnh      '), (None, 'không giới hạn')):
        tom(d[xep(d, k)], ten)
    mot = xep(d, 1)
    print('\n=== Khi chỉ cho một lệnh: lệnh được nhận so với lệnh bị bỏ vì đang có lệnh mở ===')
    tom(d[mot], 'được nhận')
    tom(d[~mot], 'bị bỏ   ')
    giu = (d['ra'] - d['vao']).dt.total_seconds() / 3600
    print(f'  Thời gian giữ trung bình: lệnh thắng {giu[d["r"] > 0].mean():.1f} giờ · lệnh thua {giu[d["r"] <= 0].mean():.1f} giờ')
    sau = d[mot].copy()
    sau['truoc_thua'] = (sau['r'].shift(1) <= 0)
    print(f'  Trong các lệnh được nhận: lệnh ngay sau một lệnh THUA {sau[sau["truoc_thua"]]["r"].mean():+.3f}R ({int(sau["truoc_thua"].sum())}) · '
          f'ngay sau một lệnh THẮNG {sau[~sau["truoc_thua"]]["r"].iloc[1:].mean():+.3f}R ({int((~sau["truoc_thua"]).sum()) - 1})')
    print('\n=== Theo phương pháp (chấm riêng, không giới hạn) → khi chỉ cho một lệnh ===')
    for ma, x in d.groupby('ma'):
        y = x[mot[x.index]]
        print(f'  {ma:<13} riêng: {len(x):>5,} lệnh {x["r"].mean():+.3f}R  →  một lệnh: {len(y):>5,} lệnh {y["r"].mean() if len(y) else float("nan"):+.3f}R')
