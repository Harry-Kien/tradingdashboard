# -*- coding: utf-8 -*-
"""Nghiên cứu trên toàn bộ nến vàng 1 phút (từ 2015): chạy lại mọi phương pháp tùy chọn, đo tỷ lệ thắng ở nhiều mức chốt lời, và tìm bộ lọc
cải tiến theo đúng kỷ luật chia ba quãng: TÌM trên 2015–2021, KIỂM trên 2022–2024, THI trên 2025–2026 (quãng thi chỉ được nhìn một lần, sau khi
đã chốt lựa chọn). Chỉ đọc tệp nến; không nối MT5, không đặt lệnh.

    python -X utf8 cong-cu/nghien_cuu.py            # tính lại từ đầu (vài phút) và lưu out/nghien-cuu.pkl
    python -X utf8 cong-cu/nghien_cuu.py --nho      # dùng lại kết quả đã lưu, chỉ in bảng

Khác với phần chạy lại của webapp ở một chỗ: mỗi tín hiệu được chấm ĐỘC LẬP (không bỏ tín hiệu rơi vào lúc lệnh trước còn mở), để một bộ lọc
chỉ là một phép chọn dòng. Lãi lỗ tính theo R (bội số của khoản rủi ro), đã trừ spread và phí của cấu hình.
"""
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import hoc, phuong_phap as PP  # noqa: E402

TPS = (0.25, 0.5, 1.0, 1.5, 2.0, 3.0)
QUANG = (('tim', 2015, 2021), ('kiem', 2022, 2024), ('thi', 2025, 2026))
TOI_THIEU = 150             # một bộ lọc phải còn ít nhất chừng này tín hiệu ở quãng tìm mới được xét
TEP = GOC / 'out' / 'nghien-cuu.pkl'


def cham_doc_lap(th, T, O, H, L, C, sp, phi):
    """Mỗi tín hiệu một dòng: (giờ, hướng, rủi ro, R ở từng mức trong TPS). Cùng quy tắc khớp và thoát với phuong_phap.cham(),
    kể cả việc thoát ở giá mở khi nến mở cửa nhảy qua dừng lỗ và việc bỏ lệnh chờ đã bị giá vượt lúc tín hiệu đến. Khác cham() ở một chỗ:
    mỗi tín hiệu được cả 4 giờ để khớp, không bị tín hiệu kế tiếp hủy."""
    n, phut, rows = len(T), 60 * 10 ** 9, []
    for s in th:
        t0 = pd.Timestamp(s['t']).value
        j = int(np.searchsorted(T, t0, side='left'))
        if j >= n or T[j] - t0 > PP.TRE_PHUT * phut:
            continue
        mua = s['huong'] == 'MUA'
        dau = 1.0 if mua else -1.0
        cho = s['kieu'] != 'thi_truong'
        if not cho:
            vao, bat = (O[j] + sp if mua else O[j]), j
        else:
            if (O[j] <= s['vao']) if mua else (O[j] >= s['vao']):
                continue                                           # giá đã ở bên kia mức chờ lúc tín hiệu đến: tín hiệu đã qua
            cuoi = min(n, int(np.searchsorted(T, t0 + PP.CHO_NEN * 15 * phut, side='left')))
            khop = (L[j:cuoi] + sp <= s['vao']) if mua else (H[j:cuoi] >= s['vao'])
            huy = (L[j:cuoi] <= s['sl']) if mua else (H[j:cuoi] + sp >= s['sl'])
            if not khop.any():
                continue
            k1 = int(np.argmax(khop))
            if huy.any() and int(np.argmax(huy)) < k1:
                continue
            vao, bat = s['vao'], j + k1
        rui = (vao - s['sl']) * dau
        if rui <= 0 or bat + PP.GIU_PHUT > n:
            continue
        cuoi = bat + PP.GIU_PHUT
        hi, lo = H[bat:cuoi], L[bat:cuoi]
        cs = (lo <= s['sl']) if mua else (hi + sp >= s['sl'])
        ks = int(np.argmax(cs)) if cs.any() else None
        r_sl = -1.0
        if ks:                                                     # mở cửa đã nhảy qua dừng lỗ: thoát ở giá mở, lỗ hơn 1R
            ra_sl = min(s['sl'], O[bat + ks]) if mua else max(s['sl'], O[bat + ks] + sp)
            r_sl = (ra_sl - vao) * dau / rui
        dich = (hi if mua else -(lo + sp)).copy()                  # quãng đi có lợi; lệnh chờ không tính nến khớp
        if cho:
            dich[0] = -np.inf
        cm = np.maximum.accumulate(dich)
        ra_cuoi = (C[cuoi - 1] if mua else C[cuoi - 1] + sp)
        out = []
        for k in TPS:
            tp = vao + dau * k * rui
            kt = int(np.searchsorted(cm, tp if mua else -tp, side='left'))
            kt = kt if kt < len(cm) else None
            if ks is not None and (kt is None or ks <= kt):
                r = r_sl
            elif kt is not None:
                r = k
            else:
                r = (ra_cuoi - vao) * dau / rui
            out.append(r - phi / rui)
        rows.append((pd.Timestamp(s['t']), s['huong'], rui, *out))
    return pd.DataFrame(rows, columns=['t', 'huong', 'rui'] + [f'r{k:g}' for k in TPS])


def tinh():
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    t0 = time.time()
    m1 = hoc._m1_dai(g, 2015)
    fr = hoc._khung(m1, g)
    print(f'nến 1 phút: {len(m1):,} dòng, {m1.index[0].date()} → {m1.index[-1].date()} ({time.time() - t0:.0f} giây)', flush=True)
    T = m1.index.as_unit('ns').asi8
    O, H, L, C = (m1[k].to_numpy(dtype=float) for k in ('open', 'high', 'low', 'close'))
    sp, phi = float(g.get('spread', 0.17)), PP.PHI
    h1, d1 = fr['H1'], fr['D1']
    ti = hoc.ty_le_bien_do(h1).dropna()
    xu_d1 = np.sign(d1['close'] - d1['close'].ewm(span=200, adjust=False, min_periods=200).mean()).shift(1)      # D1 hôm trước: giá so với EMA200
    kq = {}
    for ma in PP.DS:
        t1 = time.time()
        th = PP.quet(ma, fr['M15'], h1)
        df = cham_doc_lap(th, T, O, H, L, C, sp, phi)
        dau = np.where(df['huong'] == 'MUA', 1, -1)
        ch = PP._chieu_h1(h1, pd.DatetimeIndex(df['t']))
        df['thuan_h1'] = np.where(ch == 0, 'khong_ro', np.where(ch * dau > 0, 'thuan', 'nguoc'))
        ngay = pd.DatetimeIndex(df['t']).normalize()
        xd = xu_d1.reindex(ngay, method='ffill').to_numpy()
        df['thuan_d1'] = np.where(~np.isfinite(xd) | (xd == 0), 'khong_ro', np.where(xd * dau > 0, 'thuan', 'nguoc'))
        df['phien'] = [hoc.phien(t) for t in df['t']]
        k = ti.index.searchsorted(pd.DatetimeIndex(df['t']) - pd.Timedelta(hours=1), side='right') - 1
        df['bien_do'] = [hoc.muc(float(ti.iloc[i])) if i >= 0 else None for i in k]
        df['nam'] = pd.DatetimeIndex(df['t']).year
        kq[ma] = df
        print(f'{ma}: {len(th)} tín hiệu, {len(df)} lệnh chấm được ({time.time() - t1:.0f} giây)', flush=True)
    TEP.parent.mkdir(parents=True, exist_ok=True)
    TEP.write_bytes(pickle.dumps(kq))
    return kq


def so(df, cot):
    if not len(df):
        return 0, float('nan'), float('nan')
    v = df[cot].to_numpy()
    return len(v), float((v > 0).mean() * 100), float(v.mean())


def bang(kq):
    print('\n=== 1. TỶ LỆ THẮNG VÀ LÃI LỖ THEO MỨC CHỐT LỜI, 2015–2026 (thắng % · trung bình R mỗi lệnh) ===')
    print(f'{"phương pháp":<14}{"lệnh":>7}  ' + '  '.join(f'{"chốt " + format(k, "g") + "R":>15}' for k in TPS))
    for ma, df in kq.items():
        print(f'{ma:<14}{len(df):>7}  ' + '  '.join(f'{so(df, f"r{k:g}")[1]:>6.1f}% {so(df, f"r{k:g}")[2]:>+6.3f}R' for k in TPS))
    print('\n=== 2. TRUNG BÌNH R MỖI LỆNH THEO NĂM, CHỐT Ở 2R (số lệnh trong ngoặc) ===')
    nam = sorted({int(n) for df in kq.values() for n in df['nam'].unique()})
    print(f'{"":<14}' + ''.join(f'{n:>11}' for n in nam))
    for ma, df in kq.items():
        o = []
        for n in nam:
            c, _, tb = so(df[df['nam'] == n], 'r2')
            o.append(f'{tb:>+6.2f}({c:>3})' if c else f'{"-":>11}')
        print(f'{ma:<14}' + ''.join(o))
    print('\n=== 3. TÌM BỘ LỌC TRÊN 2015–2021, KIỂM TRÊN 2022–2024, THI TRÊN 2025–2026 ===')
    print('Mỗi phương pháp, mỗi mức chốt: bộ lọc có trung bình R cao nhất ở quãng TÌM (ít nhất 150 lệnh), rồi xem nó ra sao ở hai quãng sau.')
    dac = ('thuan_h1', 'thuan_d1', 'phien', 'bien_do', 'huong')
    chon = []
    for ma, df in kq.items():
        q = {ten: df[(df['nam'] >= a) & (df['nam'] <= b)] for ten, a, b in QUANG}
        for cot in ('r1', 'r2'):
            ung = [((), q['tim'])]
            for i, a in enumerate(dac):
                for va in q['tim'][a].dropna().unique():
                    ung.append((((a, va),), q['tim'][q['tim'][a] == va]))
                    for b in dac[i + 1:]:
                        for vb in q['tim'][b].dropna().unique():
                            ung.append((((a, va), (b, vb)), q['tim'][(q['tim'][a] == va) & (q['tim'][b] == vb)]))
            ung = [(loc, d) for loc, d in ung if len(d) >= TOI_THIEU]
            for tieu_chi, khoa in (('R cao nhất', lambda x: so(x[1], cot)[2]), ('thắng nhiều nhất', lambda x: so(x[1], cot)[1])):
                loc, d = max(ung, key=khoa)

                def ap(x, loc=loc):
                    for a, v in loc:
                        x = x[x[a] == v]
                    return x
                goc = [so(q[t], cot) for t in ('tim', 'kiem', 'thi')]
                sau = [so(ap(q[t]), cot) for t in ('tim', 'kiem', 'thi')]
                chon.append((ma, cot, tieu_chi, loc, len(ung), goc, sau))
                ten_loc = ' + '.join(f'{a}={v}' for a, v in loc) or '(không lọc)'
                print(f'\n{ma} · chốt {cot[1:]}R · chọn theo {tieu_chi} trong {len(ung)} bộ lọc: {ten_loc}')
                for t, g0, s0 in zip(('TÌM 2015–2021', 'KIỂM 2022–2024', 'THI 2025–2026'), goc, sau):
                    print(f'   {t:<15} không lọc: n={g0[0]:>5} thắng {g0[1]:>5.1f}% {g0[2]:>+6.3f}R   |   có lọc: n={s0[0]:>5} thắng {s0[1]:>5.1f}% {s0[2]:>+6.3f}R')
    print('\n=== 4. TỔNG KẾT: bộ lọc chọn theo "R cao nhất" có giữ được không ===')
    giu = 0
    for ma, cot, tc, loc, n_ung, goc, sau in chon:
        if tc != 'R cao nhất':
            continue
        ok = sau[1][0] >= 50 and sau[2][0] >= 30 and sau[1][2] > max(0, goc[1][2]) and sau[2][2] > max(0, goc[2][2])
        giu += ok
        print(f'{ma:<14} chốt {cot[1:]}R: TÌM {sau[0][2]:+.3f}R → KIỂM {sau[1][2]:+.3f}R (n={sau[1][0]}) → THI {sau[2][2]:+.3f}R (n={sau[2][0]})  {"GIỮ ĐƯỢC" if ok else "không giữ"}')
    print(f'\nSố bộ lọc vừa có lãi vừa hơn bản không lọc ở cả quãng KIỂM lẫn quãng THI: {giu}/{sum(c[2] == "R cao nhất" for c in chon)}')
    print('\n=== 5. MUỐN THẮNG 85–90% THÌ PHẢI CHỐT Ở ĐÂU ===')
    for ma, df in kq.items():
        dong = [f'{k:g}R: {so(df, f"r{k:g}")[1]:.1f}%' for k in TPS]
        print(f'{ma:<14} ' + ' · '.join(dong) + f'   → hòa vốn ở 0,25R cần thắng trên 80%; thực tế trung bình {so(df, "r0.25")[2]:+.3f}R mỗi lệnh')


if __name__ == '__main__':
    kq_ = pickle.loads(TEP.read_bytes()) if '--nho' in sys.argv and TEP.exists() else tinh()
    bang(kq_)
