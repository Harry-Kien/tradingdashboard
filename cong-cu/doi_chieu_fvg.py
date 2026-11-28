# -*- coding: utf-8 -*-
"""Đối chiếu phần nhận diện KHOẢNG TRỐNG GIÁ (FVG) của webapp với một thư viện độc lập: smartmoneyconcepts
(github.com/joshyattridge/smartmoneyconcepts, bản 0.0.27, cài ngày 24/11/2026).

Khoảng trống giá là viên gạch chung của hai trong tám phương pháp (ict, ict_fvg) và của bản đồ ICT/SMC trên trang Biểu đồ. Nếu webapp nhận
diện sai thì cả điểm vào lẫn hình vẽ đều sai theo. Ba tầng:
1. Định nghĩa thô trên toàn bộ nến M15: khoảng trống khi đáy nến thứ ba cao hơn đỉnh nến thứ nhất (chiều tăng; chiều giảm ngược lại) và nến
   giữa cùng chiều (đóng cao hơn mở với chiều tăng). Trước ngày 24/11/2026 webapp không đòi điều kiện nến giữa nên lệch thư viện khoảng 1%
   (733 khoảng trống, 204 tín hiệu); từ khi bật phuong_phap.FVG_NEN_GIUA hai bên phải trùng hẳn. Tắt công tắc đó thì phần webapp có mà thư
   viện không có phải đúng là các nến giữa không cùng chiều (đếm riêng).
2. Tín hiệu thật của hai phương pháp ict và ict_fvg (so_cong_khai.phuong_phap.quet): vùng khoảng trống của từng tín hiệu phải nằm trong danh
   sách của thư viện, đúng chiều và đúng hai mép.
3. Bản đồ ICT (so_cong_khai.phuong_phap.ban_do_ict) tại các thời điểm lấy mẫu cách đều: mỗi khoảng trống "chưa lấp" mà webapp vẽ phải có ở thư
   viện, và nhãn "giá đã chạm vào vùng" phải trùng với chỉ số lấp (MitigatedIndex) của thư viện.

Cái KHÔNG đối chiếu được bằng thư viện này: phá cấu trúc (BOS, CHoCH), khối lệnh và thanh khoản. Thư viện định nghĩa chúng khác hẳn webapp
(đỉnh/đáy xét lệch một nến và bỏ đỉnh liền nhau; BOS theo mẫu bốn đỉnh đáy; thanh khoản là cụm đỉnh gần nhau), nên chỗ lệch sẽ là khác định
nghĩa chứ không phải lỗi tính. Chỉ đọc tệp nến; không nối MT5. Thoát với mã 1 nếu có chỗ lệch chưa giải thích được.

    python -X utf8 cong-cu/doi_chieu_fvg.py [năm bắt đầu, mặc định 2015]
"""
import contextlib
import io
import json
import sys
import time
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import hoc, phuong_phap as PP  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):                       # thư viện in một dòng quảng cáo lúc nạp
    from smartmoneyconcepts import smc                                 # noqa: E402

KHUC, CACH_MAU = 5000, 500


def fvg_thu_vien(m15: pd.DataFrame) -> dict:
    """{vị trí nến giữa: (chiều +1/−1, mép dưới, mép trên)} theo smartmoneyconcepts, chạy từng khúc chồng nhau 2 nến để không sót ở chỗ nối."""
    ra, n = {}, len(m15)
    for a in range(0, n, KHUC):
        b = min(n, a + KHUC + 2)
        x = m15.iloc[a:b][['open', 'high', 'low', 'close']].reset_index(drop=True)
        f = smc.fvg(x)
        for j in np.flatnonzero(f['FVG'].notna().to_numpy()):
            if 0 < j < len(x) - 1:
                ra[a + int(j)] = (int(f['FVG'].iloc[j]), float(f['Bottom'].iloc[j]), float(f['Top'].iloc[j]))
    return ra


if __name__ == '__main__':
    tu_nam = int(sys.argv[1]) if len(sys.argv) > 1 else 2015
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    t0 = time.time()
    fr = hoc._khung(hoc._m1_dai(g, tu_nam), g)
    m15, h1 = fr['M15'], fr['H1']
    o, h, l, c = (m15[k].to_numpy(dtype=float) for k in ('open', 'high', 'low', 'close'))
    n = len(m15)
    print(f'Vàng từ {tu_nam}: {n:,} nến M15 · nạp {time.time() - t0:.0f} giây', flush=True)

    # ---- tầng 1: định nghĩa thô ----
    t0 = time.time()
    tv = fvg_thu_vien(m15)
    wa = {}
    for i in range(2, n):
        if l[i] > h[i - 2] and (not PP.FVG_NEN_GIUA or c[i - 1] > o[i - 1]):
            wa[i - 1] = (1, h[i - 2], l[i])
        elif h[i] < l[i - 2] and (not PP.FVG_NEN_GIUA or c[i - 1] < o[i - 1]):
            wa[i - 1] = (-1, h[i], l[i - 2])
    chung = [j for j in tv if j in wa]
    lech_mep = [j for j in chung if tv[j][0] != wa[j][0] or abs(tv[j][1] - wa[j][1]) > 1e-9 or abs(tv[j][2] - wa[j][2]) > 1e-9]
    chi_tv = [j for j in tv if j not in wa]
    chi_wa = [j for j in wa if j not in tv]
    nguoc = [j for j in chi_wa if (c[j] <= o[j]) if wa[j][0] == 1] + [j for j in chi_wa if (c[j] >= o[j]) if wa[j][0] == -1]
    la1 = len(chi_wa) - len(nguoc)
    print(f'Tầng 1 · định nghĩa thô: webapp {len(wa):,} khoảng trống · thư viện {len(tv):,} · cả hai có {len(chung):,}, lệch mép {len(lech_mep)} · '
          f'chỉ thư viện có {len(chi_tv)} · chỉ webapp có {len(chi_wa):,}, trong đó {len(nguoc):,} do nến giữa không cùng chiều (thư viện đòi thêm điều này) '
          f'và {la1} chưa giải thích được · {time.time() - t0:.0f} giây', flush=True)

    # ---- tầng 2: tín hiệu của hai phương pháp ----
    t0 = time.time()
    khac2, dong2, tong2 = 0, [], [0, 0]
    for ma in ('ict', 'ict_fvg'):
        th = PP.quet(ma, m15, h1)
        khop = dn = la = 0
        for s in th:
            j, chieu = s['i'] - 1, 1 if s['huong'] == 'MUA' else -1
            x = tv.get(j)
            if x is not None and x[0] == chieu and abs(x[1] - s['vung'][0]) < 1e-9 and abs(x[2] - s['vung'][1]) < 1e-9:
                khop += 1
            elif x is None and ((c[j] <= o[j]) if chieu == 1 else (c[j] >= o[j])) and wa.get(j, (0,))[0] == chieu:
                dn += 1
            else:
                la += 1
        khac2 += la
        tong2[0] += khop
        tong2[1] += len(th)
        dong2.append(f'{ma}: {len(th):,} tín hiệu, {khop:,} có trong thư viện với đúng chiều và hai mép, {dn} nến giữa không cùng chiều, {la} chưa giải thích được')
    print('Tầng 2 · tín hiệu thật · ' + ' · '.join(dong2) + f' · {time.time() - t0:.0f} giây', flush=True)

    # ---- tầng 3: bản đồ ICT tại các thời điểm lấy mẫu ----
    t0 = time.time()
    so_mau = so_vung = khop3 = dn3 = 0
    la3 = []
    for e in range(900, n, CACH_MAU):
        m = m15.iloc[e - 600:e]
        luc = m.index[-1] + timedelta(minutes=15)
        bd = PP.ban_do_ict(m, h1[h1.index <= luc].iloc[-400:], float(m['close'].iloc[-1]), luc.to_pydatetime())
        if not bd.get('du'):
            continue
        so_mau += 1
        w = m.iloc[-300:][['open', 'high', 'low', 'close']].reset_index(drop=True)
        f = smc.fvg(w)
        T = [int(t.timestamp()) for t in m.index[-300:]]
        vt = {t: k for k, t in enumerate(T)}
        for z in bd['fvg']:
            so_vung += 1
            j = vt[z['t']] + 1                                          # webapp ghi giờ của nến thứ nhất; thư viện đánh dấu ở nến giữa
            chieu = 1 if z['huong'] == 'tang' else -1
            if pd.isna(f['FVG'].iloc[j]):
                giua = w.iloc[j]
                if (giua['close'] <= giua['open']) if chieu == 1 else (giua['close'] >= giua['open']):
                    dn3 += 1
                else:
                    la3.append((luc, z, 'thư viện không có'))
                continue
            cham_tv = float(f['MitigatedIndex'].iloc[j]) > 0
            if (int(f['FVG'].iloc[j]) == chieu and abs(round(float(f['Bottom'].iloc[j]), 2) - z['duoi']) < 1e-9
                    and abs(round(float(f['Top'].iloc[j]), 2) - z['tren']) < 1e-9 and cham_tv == z['da_cham']):
                khop3 += 1
            else:
                la3.append((luc, z, f'thư viện: chiều {int(f["FVG"].iloc[j])}, {float(f["Bottom"].iloc[j])}–{float(f["Top"].iloc[j])}, đã chạm {cham_tv}'))
    print(f'Tầng 3 · bản đồ ICT tại {so_mau:,} thời điểm (cách nhau {CACH_MAU} nến): {so_vung:,} khoảng trống chưa lấp được vẽ · {khop3:,} trùng chiều, hai mép và '
          f'nhãn "đã chạm" · {dn3} nến giữa không cùng chiều · {len(la3)} chưa giải thích được · {time.time() - t0:.0f} giây')
    for luc, z, vi in la3[:5]:
        print(f'     {luc:%d/%m/%Y %H:%M} UTC · webapp {z} · {vi}')

    khac = len(lech_mep) + len(chi_tv) + la1 + khac2 + len(la3)
    print(f'\nTỔNG: khoảng trống giá · định nghĩa thô {len(chung):,} trùng hai mép · tín hiệu ict và ict_fvg {tong2[0]:,}/{tong2[1]:,} có trong thư viện · '
          f'bản đồ ICT {khop3:,}/{so_vung:,} trùng · khác định nghĩa (nến giữa không cùng chiều) {len(nguoc):,} + {tong2[1] - tong2[0] - khac2} + {dn3}')
    print(f'Khác chưa giải thích được: {khac}')
    sys.exit(1 if khac else 0)
