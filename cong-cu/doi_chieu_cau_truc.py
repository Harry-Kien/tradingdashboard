# -*- coding: utf-8 -*-
"""Đối chiếu độc lập phần CẤU TRÚC GIÁ của webapp: phá cấu trúc (BOS, CHoCH) và quét thanh khoản.

Phá cấu trúc là viên gạch của phương pháp ict_fvg và của bản đồ ICT trên trang Biểu đồ; quét thanh khoản là viên gạch của phương pháp ict và của
bản đồ. Thư viện smartmoneyconcepts định nghĩa hai thứ này khác hẳn webapp (xem cong-cu/doi_chieu_fvg.py), nên ở đây dựng lại ĐÚNG định nghĩa của
webapp bằng một cách tính khác, rồi so trên toàn bộ nến M15:

1. Phá cấu trúc: so_cong_khai.phuong_phap._pha_cau_truc (đi từng nến, giữ đỉnh/đáy gần nhất đã xác nhận) so với bản dựng lại ở đây (tìm đỉnh/đáy
   bằng cửa sổ trượt của numpy; với mỗi đỉnh/đáy, tìm nến đóng vượt đầu tiên trong quãng nó còn là đỉnh/đáy gần nhất; rồi xếp lại theo thời gian để
   gán BOS/CHoCH). Mọi lần phá (vị trí đỉnh/đáy, nến phá, mức giá, chiều, loại) và mảng chiều cấu trúc phải trùng hẳn.
2. Quét thanh khoản trên bản đồ ICT (so_cong_khai.phuong_phap.ban_do_ict, vẽ 6 lần gần nhất) tại các thời điểm lấy mẫu cách đều: danh sách phải trùng với một
   vòng lặp viết tay (đáy 5 giờ trước đó bị xuyên rồi nến đóng trở lại, và ngược lại với đỉnh).

Chỉ đọc tệp nến; không nối MT5. Thoát với mã 1 nếu có chỗ lệch.

    python -X utf8 cong-cu/doi_chieu_cau_truc.py [năm bắt đầu, mặc định 2015]
"""
import json
import sys
import time
from datetime import timedelta
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import hoc, phuong_phap as PP  # noqa: E402

CACH_MAU = 400


def dinh_day(x: np.ndarray, k: int, cao: bool) -> np.ndarray:
    """Vị trí các đỉnh (cao=True) hoặc đáy: giá tại đó bằng cực trị của cửa sổ k nến mỗi bên (hòa cũng tính)."""
    if len(x) < 2 * k + 1:
        return np.zeros(0, dtype=int)
    w = sliding_window_view(x, 2 * k + 1)
    cuc = w.max(axis=1) if cao else w.min(axis=1)
    return np.flatnonzero(x[k:len(x) - k] == cuc) + k


def pha_doc_lap(h: np.ndarray, l: np.ndarray, c: np.ndarray, k: int) -> tuple[list[tuple], np.ndarray]:
    """Bản dựng lại của _pha_cau_truc: cùng định nghĩa, khác cách tính."""
    n = len(c)
    ung = []                                                            # (chiều, vị trí đỉnh/đáy, mức, nến bắt đầu dùng được, nến hết làm "gần nhất")
    for d, vt, gia_ in ((1, dinh_day(h, k, True), h), (-1, dinh_day(l, k, False), l)):
        vt = vt[vt < n - k]
        for a, j in enumerate(vt):
            ung.append([d, int(j), float(gia_[j]), int(j) + k, int(vt[a + 1]) + k if a + 1 < len(vt) else n])

    def dau_tien(u, tu):
        d, _, muc, _, het = u
        doan = c[tu:het]
        hit = (doan > muc) if d > 0 else (doan < muc)
        return tu + int(np.argmax(hit)) if hit.any() else None

    pha = {}
    for u in ung:
        i = dau_tien(u, u[3])
        if i is not None:
            pha[(u[0], u[1])] = i
    # cùng một nến vừa phá đỉnh vừa thủng đáy: webapp xét đỉnh trước (elif), đáy còn nguyên và có thể bị thủng ở nến sau
    while True:
        theo_nen = {}
        for (d, j), i in pha.items():
            theo_nen.setdefault(i, []).append((d, j))
        dung = [(i, v) for i, v in theo_nen.items() if len({d for d, _ in v}) > 1]
        if not dung:
            break
        for i, v in dung:
            for d, j in v:
                if d < 0:
                    u = next(x for x in ung if x[0] == d and x[1] == j)
                    moi = dau_tien(u, i + 1)
                    if moi is None:
                        del pha[(d, j)]
                    else:
                        pha[(d, j)] = moi
    ds, xu = [], 0
    chieu = np.zeros(n)
    for (d, j), i in sorted(pha.items(), key=lambda kv: (kv[1], -kv[0][0])):
        muc = float(h[j] if d > 0 else l[j])
        ds.append((j, i, muc, d, 'CHoCH' if xu == -d else 'BOS'))
        xu = d
        chieu[i:] = d
    return ds, chieu


def quet_tay(h, l, c, n_quet: int, tu: int) -> list[tuple]:
    """Các lần quét từ nến `tu`: đáy thấp nhất của n_quet nến TRƯỚC bị xuyên rồi đóng trở lại phía trên (và ngược lại với đỉnh)."""
    ra = []
    for i in range(max(tu, n_quet + 1), len(c)):
        day, dinh = min(l[i - n_quet:i]), max(h[i - n_quet:i])
        if l[i] < day and c[i] > day:
            ra.append((i, 'day'))
        if h[i] > dinh and c[i] < dinh:
            ra.append((i, 'dinh'))
    return ra


if __name__ == '__main__':
    tu_nam = int(sys.argv[1]) if len(sys.argv) > 1 else 2015
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    t0 = time.time()
    m1 = hoc._m1_dai(g, tu_nam)
    fr = hoc._khung(m1, g)
    m15, h1 = fr['M15'], fr['H1']
    h, l, c = (m15[x].to_numpy(dtype=float) for x in ('high', 'low', 'close'))
    print(f'M15 từ {tu_nam}: {len(m15):,} nến · nạp {time.time() - t0:.0f} giây', flush=True)
    lech = 0
    # 1. phá cấu trúc trên toàn bộ chuỗi
    a, ca = PP._pha_cau_truc(h, l, c)
    b, cb = pha_doc_lap(h, l, c, PP.K_SWING)
    sa, sb = set(a), set(b)
    khac_chieu = int((ca != cb).sum())
    lech += len(sa ^ sb) + khac_chieu
    dem = {k: sum(1 for x in a if x[4] == k) for k in ('BOS', 'CHoCH')}
    print(f'TỔNG: phá cấu trúc · webapp {len(a):,} lần (BOS {dem["BOS"]:,} · CHoCH {dem["CHoCH"]:,}) · bản dựng lại {len(b):,} lần · trùng {len(sa & sb):,} · '
          f'chỉ webapp có {len(sa - sb)} · chỉ bản dựng lại có {len(sb - sa)} · mảng chiều khác ở {khac_chieu} nến', flush=True)
    for x in sorted(sa ^ sb)[:5]:
        print('   ví dụ lệch:', x, 'webapp' if x in sa else 'bản dựng lại')
    # 2. quét thanh khoản trên bản đồ ICT, lấy mẫu cách đều
    mau, trung, tong = 0, 0, 0
    for e in range(400, len(m15), CACH_MAU):
        m = m15.iloc[:e]
        now = m.index[-1].to_pydatetime() + timedelta(minutes=15)
        bd = PP.ban_do_ict(m, h1[h1.index + timedelta(hours=1) <= now], float(m['close'].iloc[-1]), now)
        if not bd.get('du'):
            continue
        w = m.iloc[-300:]
        wh, wl, wc = (w[x].to_numpy(dtype=float) for x in ('high', 'low', 'close'))
        T = [int(t.timestamp()) for t in w.index]
        tay = [(T[i], loai, round(float(wl[i] if loai == 'day' else wh[i]), 2)) for i, loai in quet_tay(wh, wl, wc, PP.N_QUET, len(w) - 48)][-6:]   # bản đồ chỉ vẽ 6 lần gần nhất
        web = [(q['t'], q['loai'], q['gia']) for q in bd['quet']]
        mau += 1
        tong += max(len(tay), len(web))
        trung += sum(1 for x, y in zip(tay, web) if x == y) if len(tay) == len(web) else 0
        lech += 0 if tay == web else max(len(tay), len(web))
    print(f'TỔNG: quét thanh khoản trên bản đồ ICT · {mau:,} thời điểm lấy mẫu · {tong:,} lần quét · trùng {trung:,} · lệch {tong - trung}', flush=True)
    print(f'Khác chưa giải thích được: {lech}')
    print(f'Xong sau {time.time() - t0:.0f} giây.')
    sys.exit(1 if lech else 0)
