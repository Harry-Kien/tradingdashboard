# -*- coding: utf-8 -*-
"""Đo điểm vào lệnh của tám phương pháp: độ đi ngược/đi thuận, các kiểu vào, cách đặt dừng lỗ, cách chốt lời, bộ lọc bối cảnh và điểm chất lượng.

Mọi biến thể và cổng chấp nhận đã ghi TRƯỚC khi đo ở cong-cu/CHUAN_HOA_DANG_KY.md (phần "Điểm vào lệnh"); tệp này chỉ làm đúng những gì ghi ở đó.
Chia dữ liệu: phần CHỈNH 2015–2021 (chọn biến thể), phần KIỂM TRA 2022 trở đi (chỉ để xác nhận).

Phép mô phỏng ở đây khác phuong_phap.cham() của webapp ở ba chỗ, có chủ ý:
- spread lấy theo TỪNG nến 1 phút (cột spread của tệp nến nhiều năm), không phải một số cố định;
- thêm trượt giá lúc tin và phí qua đêm;
- mỗi tín hiệu được chấm RIÊNG, để mọi biến thể được so trên cùng một bộ tín hiệu và lệnh chờ không khớp vẫn có "kết quả nếu vào ngay".
Mua khớp ở Ask, bán khớp ở Bid; dừng lỗ và chốt lời cùng một nến 1 phút thì tính thua; chỉ dùng nến đã đóng. Chỉ đọc tệp nến; không nối MT5, không
đặt lệnh, không sửa luật nào trong webapp. Kết quả ghi ở out/diem-vao.json; bảng in ra màn hình.

    python -X utf8 cong-cu/diem_vao.py
"""
import json
import os
import sys
import time
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import gia, hoc, phuong_phap as PP  # noqa: E402
from so_cong_khai.diem_vao_rt import dat_gia  # noqa: E402
from so_cong_khai.phieu import THI_TRUONG, muc_cho, muc_sl, nhom  # noqa: E402 - cùng hàm với phiếu vào lệnh của webapp

PHUT = 60 * 10 ** 9
CAT_NAM = 2022                       # phần chỉnh: trước năm này; phần kiểm tra: từ năm này
TOI_THIEU = 100
PHI = PP.PHI                         # phí và trượt giá thường mỗi lệnh
TRUOT_TIN = 0.25                     # cộng thêm cho mỗi lần khớp kiểu thị trường trong 15 phút quanh tin USD mức cao
QUANH_TIN = 15 * PHUT
QUA_DEM = {True: -0.0181 / 100, False: 0.0066 / 100}        # mua / bán, phần giá trị lệnh mỗi đêm (mức phí hiện tại của sàn)
HE_SO_DEM = (1, 1, 3, 1, 1, 0, 0)    # theo thứ của ngày vừa kết thúc; thứ Hai là chỉ số 0
ATHENS = ZoneInfo('Europe/Athens')
KIEU_VAO = {**{m: ('V0', 'V1', 'V2', 'V3') for m in THI_TRUONG}, 'ict': ('V0', 'V1', 'V2', 'V3', 'V4'), 'ict_fvg': ('V0', 'V1', 'V2', 'V3', 'V4'),
            'fib': ('V0', 'V1', 'V2', 'V3', 'V4')}
TEN_VAO = {'tt': {'V0': 'vào ngay (hiện tại)', 'V1': 'chờ hồi về giữa nến tín hiệu', 'V2': 'chờ phá đỉnh/đáy nến tín hiệu', 'V3': 'xác nhận nến M5'},
           'ict': {'V0': 'giữa khoảng trống (hiện tại)', 'V1': 'mép gần', 'V2': 'mép xa', 'V3': 'vào ngay', 'V4': 'xác nhận nến M5 trong vùng'},
           'fib': {'V0': 'mức 61,8% (hiện tại)', 'V1': 'mức 50%', 'V2': 'mức 78,6%', 'V3': 'vào ngay', 'V4': 'xác nhận nến M5 sau mức 50%'}}
TEN_SL = {'S0': 'mức của phương pháp (hiện tại)', 'S1': 'theo ATR (riêng Phá vỡ: theo cấu trúc)', 'S2': 'thêm đệm spread', 'S3': 'nới thêm 0,5 ATR'}
TEN_TP = {'T0': 'chốt hết ở 2R (hiện tại)', 'T1': 'chốt hết ở 1R', 'T2': 'mục tiêu lý thuyết', 'T3': 'nửa ở 1R, dời về hòa vốn, nửa ở 2R'}
TEN_LOC = {'L1': 'bỏ khi trong 60 phút quanh tin', 'L2': 'bỏ khi spread trên 2 lần trung vị', 'L3': 'bỏ khi chưa tới 1R đã gặp đỉnh/đáy 24 giờ',
           'L4': 'bỏ khi ngược xu hướng H4'}


# ---- dữ liệu ----------------------------------------------------------------------------------------------------------------------------------
def nap_spread(g: dict, idx: pd.DatetimeIndex, mac_dinh: float) -> np.ndarray:
    """Spread (USD) của từng nến 1 phút trong `idx`: cột spread của tệp nến nhiều năm (đơn vị điểm, 1 điểm = 0,01); nến không có thì dùng `mac_dinh`."""
    goc = Path(os.path.expandvars(g.get('d1_goc') or 'khong-co')).with_name('XAUUSDp_M1.csv')
    if not goc.exists():
        return np.full(len(idx), mac_dinh)
    c = pd.read_csv(goc, sep='\t', usecols=[0, 1, 8], names=['d', 't', 'sp'], header=0, dtype={'d': str, 't': str})
    s = pd.Series(c['sp'].to_numpy(dtype=float) * 0.01, index=pd.to_datetime(c['d'] + ' ' + c['t'], format='%Y.%m.%d %H:%M:%S', utc=True))
    from so_cong_khai import sua_gio                                         # noqa: PLC0415
    s.index = sua_gio.gio_that(s.index)                                      # cùng cách sửa giờ như nến (hoc._m1_dai)
    s = s[~s.index.duplicated(keep='last')]
    return s.reindex(idx).fillna(mac_dinh).to_numpy(dtype=float)


def du_lieu(m1: pd.DataFrame, spread: np.ndarray, tin: list) -> dict:
    """Gói mảng dùng cho phép mô phỏng. `m1`: nến 1 phút giá Bid, chỉ số là giờ mở nến (UTC). `tin`: các mốc tin USD mức cao."""
    m5 = m1.resample('5min', origin='epoch', label='left', closed='left').agg({'open': 'first', 'close': 'last'}).dropna()
    return {'T': m1.index.as_unit('ns').asi8, 'O': m1['open'].to_numpy(dtype=float), 'H': m1['high'].to_numpy(dtype=float),
            'L': m1['low'].to_numpy(dtype=float), 'C': m1['close'].to_numpy(dtype=float), 'S': np.asarray(spread, dtype=float),
            'tin': np.array(sorted(pd.Timestamp(t).value for t in tin), dtype=np.int64),
            'T5': m5.index.as_unit('ns').asi8, 'O5': m5['open'].to_numpy(dtype=float), 'C5': m5['close'].to_numpy(dtype=float),
            # trung vị spread của 1.440 nến 1 phút TRƯỚC mỗi nến (không tính chính nó)
            'S_tv': pd.Series(np.asarray(spread, dtype=float)).rolling(1440, min_periods=300).median().shift(1).to_numpy()}


def gan_tin(D: dict, t: int, rong: int = QUANH_TIN) -> bool:
    tin = D['tin']
    k = int(np.searchsorted(tin, t - rong, side='left'))
    return k < len(tin) and tin[k] <= t + rong


def so_dem(t_vao: int, t_ra: int) -> int:
    """Tổng hệ số qua đêm của các mốc 00:00 giờ Athens nằm trong (lúc vào, lúc ra]; hệ số là của ngày vừa kết thúc."""
    ngay = 1440 * PHUT                                               # Athens đi trước UTC 2 hoặc 3 giờ: cùng ngày ở cả hai độ lệch thì chắc chắn không qua đêm
    if (t_vao + 120 * PHUT) // ngay == (t_ra + 120 * PHUT) // ngay and (t_vao + 180 * PHUT) // ngay == (t_ra + 180 * PHUT) // ngay:
        return 0
    a = pd.Timestamp(t_vao, tz='UTC').tz_convert(ATHENS).date()
    b = pd.Timestamp(t_ra, tz='UTC').tz_convert(ATHENS).date()
    return sum(HE_SO_DEM[(a + timedelta(days=k)).weekday()] for k in range((b - a).days))


# ---- một lệnh ---------------------------------------------------------------------------------------------------------------------------------
def mo_phong(D: dict, s: dict, ma: str, vao: str = 'V0', sl: str = 'S0', tp: str = 'T0', chi_phi_cu: float | None = None,
             khong_tp: bool = False, cong_gia: bool = False) -> dict:
    """Chấm một tín hiệu theo một bộ (kiểu vào, dừng lỗ, chốt lời). Trả {'khop': False, 'vi': …} hoặc
    {'khop': True, 't_vao', 't_ra', 'gia', 'rui', 'r', 'ket', 'mae', 'mfe'} (r, mae, mfe tính bằng R; r đã trừ chi phí).
    `chi_phi_cu`: nếu đưa một số thì dùng spread cố định đó và chỉ trừ PHI (cách tính cũ của webapp), để có mốc so sánh."""
    T, O, H, L, C = D['T'], D['O'], D['H'], D['L'], D['C']
    S = D['S'] if chi_phi_cu is None else None
    sp = (lambda k: S[k]) if S is not None else (lambda k: chi_phi_cu)          # noqa: E731
    n, t0 = len(T), pd.Timestamp(s['t']).value
    j = int(np.searchsorted(T, t0, side='left'))
    if j >= n or T[j] - t0 > PP.TRE_PHUT * PHUT:
        return {'khop': False, 'vi': 'thieu_nen'}
    mua = s['huong'] == 'MUA'
    dau = 1.0 if mua else -1.0
    loai, muc = muc_cho(s, ma, vao)
    han = int(np.searchsorted(T, t0 + (60 if (loai == 'xn' and nhom(ma) == 'tt') else PP.CHO_NEN * 15) * PHUT, side='left'))
    sl_truoc = muc_sl(s, ma, sl, muc if muc is not None else s['vao'], sp(j))   # mức dừng lỗ dùng để hủy lệnh chờ trước khi khớp

    def spr(a, b):                                                    # spread của các nến a…b−1
        return S[a:b] if S is not None else chi_phi_cu

    def cham_sl(a, b, muc_dung):
        return (L[a:b] <= muc_dung) if mua else (H[a:b] + spr(a, b) >= muc_dung)

    cho = loai != 'tt'
    thi_truong = loai in ('tt', 'dung', 'xn')
    if cong_gia and loai == 'tt':
        moc = s['vao']
        muc_tp_goc = moc + PP.TP_R * (moc - sl_truoc)
        if not dat_gia(loai, s['huong'], moc, sl_truoc, muc_tp_goc, O[j], O[j] + sp(j), s['atr'], moc):
            return {'khop': False, 'vi': 'cong_gia'}
    if loai == 'tt':
        bat, gia_khop = j, (O[j] + sp(j) if mua else O[j])
    elif loai in ('gh', 'dung'):
        if loai == 'gh' and cong_gia:
            # Ghi nhận mức chờ khi một giá mở M1 quan sát được còn ở phía trước mức vào và nằm trong ngưỡng.
            # Nếu đã chạm trước đó thì bỏ. Nếu chạm đích và entry cùng một phút, ưu tiên bỏ vì thiếu thứ tự tick.
            vao_mo = O[j:han] + spr(j, han) if mua else O[j:han]
            rui_goc = abs(muc - sl_truoc)
            kc = (vao_mo - muc) * dau
            hop = np.flatnonzero((kc > 0) & (kc <= min(s['atr'], rui_goc)))
            cham = (L[j:han] + spr(j, han) <= muc) if mua else (H[j:han] >= muc)
            dich = muc + dau * PP.TP_R * rui_goc
            het = (H[j:han] >= dich) if mua else (L[j:han] + spr(j, han) <= dich)
            if not len(hop) or not len(kc) or kc[0] <= 0 or cham[:hop[0]].any():
                return {'khop': False, 'vi': 'cong_gia'}
            if not cham.any():
                return {'khop': False, 'vi': 'khong_khop'}
            k1 = int(np.argmax(cham))
            if het[:k1 + 1].any():
                return {'khop': False, 'vi': 'cham_tp_truoc'}
            khop = cham
        elif loai == 'gh':
            if (O[j] <= muc) if mua else (O[j] >= muc):
                return {'khop': False, 'vi': 'da_qua'}                # giá đã ở bên kia mức chờ lúc tín hiệu đến
            khop = (L[j:han] + spr(j, han) <= muc) if mua else (H[j:han] >= muc)
        else:
            khop = (H[j:han] + spr(j, han) >= muc) if mua else (L[j:han] <= muc)
        if not khop.any():
            return {'khop': False, 'vi': 'khong_khop'}
        k1 = int(np.argmax(khop))
        huy = cham_sl(j, j + k1, sl_truoc)
        if huy.any():
            return {'khop': False, 'vi': 'cham_sl_truoc'}
        bat = j + k1
        if loai == 'gh':
            gia_khop = muc
        else:                                                         # lệnh chờ dừng: nến mở cửa đã vượt mức thì khớp ở giá mở, xấu hơn
            gia_khop = max(muc, O[bat] + sp(bat)) if mua else min(muc, O[bat])
    else:                                                             # xác nhận bằng nến M5
        dau_cho = j
        if muc is not None:                                           # phải chạm mức trước đã
            cham = (L[j:han] + spr(j, han) <= muc) if mua else (H[j:han] >= muc)
            if not cham.any():
                return {'khop': False, 'vi': 'khong_khop'}
            dau_cho = j + int(np.argmax(cham))
        T5, O5, C5 = D['T5'], D['O5'], D['C5']
        a = int(np.searchsorted(T5, T[dau_cho], side='left'))         # nến M5 đầu tiên mở từ lúc bắt đầu chờ
        b = int(np.searchsorted(T5, (T[han - 1] if han > 0 else t0) - 4 * PHUT, side='right'))
        ok = (C5[a:b] > O5[a:b]) if mua else (C5[a:b] < O5[a:b])
        if not ok.any():
            return {'khop': False, 'vi': 'khong_khop'}
        t_xn = T5[a + int(np.argmax(ok))] + 5 * PHUT                  # lúc nến M5 xác nhận đóng
        bat = int(np.searchsorted(T, t_xn, side='left'))
        if bat >= n or bat >= han + 5:
            return {'khop': False, 'vi': 'khong_khop'}
        if cham_sl(j, bat, sl_truoc).any():
            return {'khop': False, 'vi': 'cham_sl_truoc'}
        gia_khop = O[bat] + sp(bat) if mua else O[bat]
    muc_dung = muc_sl(s, ma, sl, gia_khop, sp(j))
    rui = (gia_khop - muc_dung) * dau
    lo_r, hi_r = s['rui_khoang'] if s.get('rui_khoang') else (PP.RUI_RO_ATR[0] * s['atr'], PP.RUI_RO_ATR[1] * s['atr'])     # luật bot: khoảng tuyệt đối tính bằng giá
    if not np.isfinite(rui) or rui <= 0 or not (lo_r <= rui <= hi_r):
        return {'khop': False, 'vi': 'rui_ro'}
    if tp == 'T2' and not khong_tp:
        if s.get('muc_tieu') is None or (s['muc_tieu'] - gia_khop) * dau <= 0:
            return {'khop': False, 'vi': 'khong_muc_tieu'}
        muc_tp = s['muc_tieu']
    else:
        boi = float(tp[1:]) if tp.startswith('R') else 1.0 if tp in ('T1', 'T3') else PP.TP_R      # 'R0.5': chốt hết ở 0,5R (chỉ dùng khi đo)
        muc_tp = gia_khop + dau * boi * rui
    cuoi = min(n, bat + PP.GIU_PHUT)
    if bat + PP.GIU_PHUT > n:
        return {'khop': False, 'vi': 'het_du_lieu'}
    nguoc = L[bat:cuoi] if mua else H[bat:cuoi] + spr(bat, cuoi)      # giá bên thoát lệnh, phía đi ngược
    thuan = H[bat:cuoi] if mua else L[bat:cuoi] + spr(bat, cuoi)      # giá bên thoát lệnh, phía đi thuận

    def ra_sl(k, muc_):                                               # giá thoát khi chạm dừng ở nến k (tính từ bat): mở cửa đã vượt thì thoát ở giá mở
        if k == 0:
            return muc_
        mo = O[bat + k] if mua else O[bat + k] + sp(bat + k)
        return min(muc_, mo) if mua else max(muc_, mo)

    cs = (nguoc <= muc_dung) if mua else (nguoc >= muc_dung)
    ct = np.zeros(len(cs), bool) if khong_tp else ((thuan >= muc_tp) if mua else (thuan <= muc_tp))
    if cho and len(ct):
        ct[0] = False                                                 # nến khớp của lệnh chờ: chỉ xét phần đi ngược
    if tp in ('TL', 'TLB') and not khong_tp:                         # thang nhiều mức chốt, các phần bằng nhau (luật bot)
        k_cuoi = len(cs) - 1
        phan = thang(mua, nguoc, thuan, cho, gia_khop, rui, muc_dung, s['thang'], tp == 'TLB', ra_sl,
                     C[bat + k_cuoi] if mua else C[bat + k_cuoi] + sp(bat + k_cuoi))
    else:
        ks = int(np.argmax(cs)) if cs.any() else None
        kt = int(np.argmax(ct)) if ct.any() else None
        phan = []                                                         # [(tỷ trọng, giá ra, kiểu, nến)]
        if ks is not None and (kt is None or ks <= kt):
            phan.append((1.0, ra_sl(ks, muc_dung), 'SL', ks))
        elif kt is None:
            k = len(cs) - 1
            phan.append((1.0, C[bat + k] if mua else C[bat + k] + sp(bat + k), 'Hết giờ', k))
        elif tp != 'T3' or khong_tp:
            phan.append((1.0, muc_tp, 'TP', kt))
        else:                                                             # nửa ở 1R; từ nến kế tiếp dừng lỗ của nửa còn lại về giá vào; nửa còn lại ở 2R
            phan.append((0.5, muc_tp, 'TP', kt))
            muc2 = gia_khop + dau * PP.TP_R * rui
            c2 = (thuan[kt:] >= muc2) if mua else (thuan[kt:] <= muc2)
            s2 = (nguoc[kt + 1:] <= gia_khop) if mua else (nguoc[kt + 1:] >= gia_khop)
            k2 = kt + int(np.argmax(c2)) if c2.any() else None
            kb = kt + 1 + int(np.argmax(s2)) if s2.any() else None
            if kb is not None and (k2 is None or kb <= k2):
                phan.append((0.5, ra_sl(kb, gia_khop), 'Hòa vốn', kb))
            elif k2 is not None:
                phan.append((0.5, muc2, 'TP2', k2))
            else:
                k = len(cs) - 1
                phan.append((0.5, C[bat + k] if mua else C[bat + k] + sp(bat + k), 'Hết giờ', k))
    k_ra = max(p[3] for p in phan)
    lai = sum(w * (ra - gia_khop) * dau for w, ra, _, _ in phan)
    phi = PHI
    if chi_phi_cu is None:
        if thi_truong and gan_tin(D, int(T[bat])):
            phi += TRUOT_TIN
        for w, _, kieu, k in phan:
            if kieu in ('SL', 'Hòa vốn', 'Hết giờ') and gan_tin(D, int(T[bat + k])):
                phi += w * TRUOT_TIN
        dem = so_dem(int(T[bat]), int(T[bat + k_ra]))
        if dem:
            phi -= gia_khop * QUA_DEM[mua] * dem                      # mua: phí dương (bị trừ); bán: được cộng một khoản nhỏ
    doan_n, doan_t = nguoc[:k_ra + 1], thuan[:k_ra + 1]
    mae = max(0.0, float((gia_khop - doan_n.min()) * dau if mua else (doan_n.max() - gia_khop))) / rui
    mfe = max(0.0, float((doan_t.max() - gia_khop) if mua else (gia_khop - doan_t.min()))) / rui
    return {'khop': True, 't_vao': int(T[bat]), 't_ra': int(T[bat + k_ra]), 'gia': float(gia_khop), 'rui': float(rui), 'r': float((lai - phi) / rui),
            'ket': phan[-1][2] if len(phan) > 1 else phan[0][2], 'mae': mae, 'mfe': mfe}


def thang(mua: bool, nguoc, thuan, cho: bool, gia_khop: float, rui: float, muc_dung: float, cac_muc, hoa_von: bool, ra_sl, gia_cuoi: float) -> list:
    """[(tỷ trọng, giá ra, kiểu, nến)] của một lệnh chia đều cho các mức chốt `cac_muc` (bội số R, tăng dần). Phần nào chưa chốt thì thoát ở dừng
    lỗ hoặc lúc hết giờ. Dừng lỗ và một mức chốt cùng trong một nến thì tính dừng lỗ. `hoa_von`: sau khi mức đầu chốt, dừng lỗ của phần còn lại dời
    về giá vào, có hiệu lực từ nến kế tiếp."""
    dau = 1.0 if mua else -1.0
    w, phan, dung, da = 1.0 / len(cac_muc), [], muc_dung, 0
    cs = (nguoc <= dung) if mua else (nguoc >= dung)
    ks = int(np.argmax(cs)) if cs.any() else None
    for m in cac_muc:
        muc = gia_khop + dau * m * rui
        c = (thuan >= muc) if mua else (thuan <= muc)
        if cho and len(c):
            c[0] = False                                              # nến khớp của lệnh chờ: chỉ xét phần đi ngược
        kt = int(np.argmax(c)) if c.any() else None
        if kt is None or (ks is not None and ks <= kt):
            break
        phan.append((w, muc, 'TP', kt))
        da += 1
        if hoa_von and da == 1:
            s2 = (nguoc[kt + 1:] <= gia_khop) if mua else (nguoc[kt + 1:] >= gia_khop)
            ks, dung = (kt + 1 + int(np.argmax(s2)) if s2.any() else None), gia_khop
    con = len(cac_muc) - da
    if con:
        if ks is not None:
            phan.append((w * con, ra_sl(ks, dung), 'Hòa vốn' if (hoa_von and da) else 'SL', ks))
        else:
            phan.append((w * con, gia_cuoi, 'Hết giờ', len(nguoc) - 1))
    return phan


# ---- cả bộ tín hiệu ---------------------------------------------------------------------------------------------------------------------------
def tin_hieu(ma: str, m15: pd.DataFrame, h1: pd.DataFrame) -> list[dict]:
    """Tín hiệu của webapp (phuong_phap.quet), kèm đỉnh và đáy của nến tín hiệu."""
    h, l = m15['high'].to_numpy(dtype=float), m15['low'].to_numpy(dtype=float)
    return [dict(s, nen_h=float(h[s['i']]), nen_l=float(l[s['i']])) for s in PP.quet(ma, m15, h1)]


def chay(D: dict, th: list, ma: str, giu=None, **kw) -> pd.DataFrame:
    """Một dòng cho mỗi tín hiệu (trừ tín hiệu thiếu nến): năm, có khớp không, vì sao không, r, mae, mfe, giờ ra. `giu`: mảng bool chọn tín hiệu."""
    rows = []
    for so, s in enumerate(th):
        if giu is not None and not giu[so]:
            continue
        x = mo_phong(D, s, ma, **kw)
        if not x['khop'] and x['vi'] in ('thieu_nen', 'het_du_lieu'):
            continue
        rows.append({'so': so, 'nam': pd.Timestamp(s['t']).year, 'khop': x['khop'], 'vi': x.get('vi', ''), 'r': x.get('r', np.nan),
                     'mae': x.get('mae', np.nan), 'mfe': x.get('mfe', np.nan), 't_ra': x.get('t_ra', 0), 'ket': x.get('ket', '')})
    return pd.DataFrame(rows, columns=['so', 'nam', 'khop', 'vi', 'r', 'mae', 'mfe', 't_ra', 'ket'])


def so_do(df: pd.DataFrame) -> dict:
    """Số đo của một nhóm dòng: số tín hiệu, tỷ lệ khớp, số lệnh, tỷ lệ thắng, R mỗi lệnh, tổng R, hệ số lợi nhuận, sụt giảm lớn nhất (R)."""
    k = df[df['khop']].sort_values('t_ra')
    n = len(k)
    if not n:
        return {'tin_hieu': int(len(df)), 'khop_pct': 0.0, 'n': 0, 'thang': None, 'r_tb': None, 'tong': 0.0, 'pf': None, 'dd': 0.0}
    r = k['r'].to_numpy()
    lai, lo = r[r > 0].sum(), -r[r < 0].sum()
    luy = np.cumsum(r)
    return {'tin_hieu': int(len(df)), 'khop_pct': round(n / len(df) * 100, 1), 'n': int(n), 'thang': round(float((r > 0).mean() * 100), 1),
            'r_tb': round(float(r.mean()), 4), 'tong': round(float(r.sum()), 1), 'pf': round(float(lai / lo), 3) if lo > 0 else None,
            'dd': round(float((np.maximum.accumulate(np.r_[0.0, luy]) - np.r_[0.0, luy]).max()), 1)}


def hai_phan(df: pd.DataFrame) -> dict:
    return {'chinh': so_do(df[df['nam'] < CAT_NAM]), 'kiem': so_do(df[df['nam'] >= CAT_NAM])}


def cong(cu: dict, moi: dict) -> tuple[bool, str]:
    """Cổng chung: `moi` (đã được chọn trên phần chỉnh) phải có ≥ 100 lệnh ở phần kiểm tra, R mỗi lệnh cao hơn và tổng R không thấp hơn `cu`."""
    a, b = cu['kiem'], moi['kiem']
    if b['n'] < TOI_THIEU:
        return False, f'mẫu nhỏ, chưa đủ tin ({b["n"]} lệnh ở phần kiểm tra)'
    if b['r_tb'] <= a['r_tb']:
        return False, 'R mỗi lệnh ở phần kiểm tra không cao hơn bản hiện tại'
    if b['tong'] < a['tong']:
        return False, 'tổng R ở phần kiểm tra thấp hơn bản hiện tại'
    return True, 'R mỗi lệnh cao hơn và tổng R không thấp hơn ở phần kiểm tra'


def chon(bang: dict, goc: str) -> tuple[str, bool, str]:
    """(bản được giữ, có đổi không, lý do). `bang`: {tên bản: hai_phan()}. Chọn trên phần chỉnh theo R mỗi lệnh; khác bản gốc thì phải qua cổng."""
    co = {k: v for k, v in bang.items() if v['chinh']['n'] >= TOI_THIEU and v['chinh']['r_tb'] is not None}
    if goc not in co:
        return goc, False, 'bản hiện tại không đủ lệnh ở phần chỉnh để so'
    tot = max(co, key=lambda k: co[k]['chinh']['r_tb'])
    if tot == goc:
        return goc, False, 'bản hiện tại tốt nhất trên phần chỉnh'
    dat, vi = cong(bang[goc], bang[tot])
    return (tot, True, vi) if dat else (goc, False, f'{tot} tốt nhất trên phần chỉnh nhưng không qua cổng: {vi}')


def dong(ten: str, x: dict) -> str:
    def nua(v):
        if not v['n']:
            return f'{v["tin_hieu"]:>6,} · {v["khop_pct"]:>5}% · {0:>5} ·    —   ·    —    ·     —   ·   —   ·    —'
        return (f'{v["tin_hieu"]:>6,} · {v["khop_pct"]:>5}% · {v["n"]:>5,} · {v["thang"]:>5}% · {v["r_tb"]:+.3f} · {v["tong"]:+8.1f} · '
                f'{v["pf"] if v["pf"] is not None else "—":>5} · {v["dd"]:>6.1f}')
    return f'  {ten:<44} │ {nua(x["chinh"])} │ {nua(x["kiem"])}'.replace('.', ',')


DAU_BANG = ('  bản' + ' ' * 41 + '│ CHỈNH 2015–2021: tín hiệu · khớp · lệnh · thắng · R/lệnh · tổng R · PF · sụt giảm │ KIỂM TRA 2022–: tín hiệu · khớp · lệnh · thắng · '
            'R/lệnh · tổng R · PF · sụt giảm')


# ---- bối cảnh ---------------------------------------------------------------------------------------------------------------------------------
def boi_canh(D: dict, th: list, m15: pd.DataFrame, h4: pd.DataFrame) -> dict:
    """{'L1'…'L4': mảng bool, True = tín hiệu BỊ bộ lọc đó bỏ}. Chỉ dùng dữ liệu có trước lúc tín hiệu."""
    T, S = D['T'], D['S']
    h, l = m15['high'].to_numpy(dtype=float), m15['low'].to_numpy(dtype=float)
    cao = pd.Series(h).rolling(PP.N_BIEN).max().to_numpy()
    thap = pd.Series(l).rolling(PP.N_BIEN).min().to_numpy()
    d4 = np.sign(PP._ema(h4['close'], 20) - PP._ema(h4['close'], 50)).fillna(0.0)
    d4.index = d4.index + timedelta(hours=4)
    luc = pd.DatetimeIndex([pd.Timestamp(s['t']) for s in th])
    xu4 = d4.reindex(luc, method='ffill').fillna(0.0).to_numpy() if len(th) else np.array([])
    tv = D['S_tv']
    ra = {k: np.zeros(len(th), bool) for k in ('L1', 'L2', 'L3', 'L4')}
    for so, s in enumerate(th):
        t0 = pd.Timestamp(s['t']).value
        j = int(np.searchsorted(T, t0, side='left'))
        mua = s['huong'] == 'MUA'
        ra['L1'][so] = gan_tin(D, t0, 60 * PHUT)
        if 0 < j < len(T):
            ra['L2'][so] = bool(np.isfinite(tv[j]) and S[j - 1] > 2 * tv[j])        # spread của nến 1 phút vừa đóng trước lúc tín hiệu
        rui = abs(s['vao'] - s['sl'])
        cho = (cao[s['i']] - s['vao']) if mua else (s['vao'] - thap[s['i']])
        ra['L3'][so] = bool(np.isfinite(cho) and cho < rui)
        ra['L4'][so] = bool(xu4[so] * (1 if mua else -1) < 0)
    return ra


if __name__ == '__main__':
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    t0 = time.time()
    m1 = hoc._m1_dai(g, 2015)
    fr = hoc._khung(m1, g)
    sp0 = float(g.get('spread', 0.17))
    S = nap_spread(g, m1.index, sp0)
    tin = gia.tin_usd(g)[0] if g.get('lich_tin') else []
    D = du_lieu(m1, S, tin)
    nam = m1.index.year.to_numpy()
    print(f'Vàng từ 2015: {len(m1):,} nến 1 phút · {len(tin):,} mốc tin · spread theo nến, trung vị từng năm: '
          + ' '.join(f'{y}:{np.median(S[nam == y]):.2f}' for y in sorted(set(nam.tolist()))).replace('.', ',') + f' · nạp {time.time() - t0:.0f} giây', flush=True)
    KQ: dict = {'cat_nam': CAT_NAM, 'pp': {}, 'so_phep_so': 0, 'ap_dung': {}, 'den': m1.index[-1].isoformat()}      # den: nến cuối đã dùng
    gop_diem = []
    for ma in PP.DS:
        t1 = time.time()
        th = tin_hieu(ma, fr['M15'], fr['H1'])
        G = nhom(ma)
        kq = KQ['pp'][ma] = {'ten': PP.DS[ma]['ten'], 'tin_hieu': len(th)}
        print(f'\n══════ {PP.DS[ma]["ten"]} ({ma}) · {len(th):,} tín hiệu ══════')
        # A. mốc: chi phí cũ so với chi phí mới, cùng bản hiện tại
        cu, moi = chay(D, th, ma, chi_phi_cu=sp0), chay(D, th, ma)
        kq['A'] = {'cu': hai_phan(cu), 'moi': hai_phan(moi)}
        print('A. Mốc: bản hiện tại, chi phí cũ so với chi phí mới\n' + DAU_BANG)
        print(dong('chi phí cũ (spread 0,17 cố định + phí 0,18)', kq['A']['cu']))
        print(dong('chi phí mới (spread từng nến, tin, qua đêm)', kq['A']['moi']))
        # B. đi ngược, đi thuận
        k = moi[moi['khop']]
        kh = chay(D, th, ma, khong_tp=True)
        kh = kh[kh['khop']]
        pv = lambda x, q: round(float(np.quantile(x, q)), 2) if len(x) else None      # noqa: E731
        thang, thua = k[k['ket'] == 'TP'], k[k['ket'] == 'SL']
        kq['B'] = {'n_thang': int(len(thang)), 'n_thua': int(len(thua)),
                   'mae_thang': [pv(thang['mae'], q) for q in (0.5, 0.75, 0.9)], 'mfe_thua': [pv(thua['mfe'], q) for q in (0.5, 0.75, 0.9)],
                   'thua_tung_dat_1r': round(float((thua['mfe'] >= 1).mean() * 100), 1) if len(thua) else None,
                   'thang_di_nguoc_duoi_nua_r': round(float((thang['mae'] < 0.5).mean() * 100), 1) if len(thang) else None,
                   'khong_tp_mfe': [pv(kh['mfe'], q) for q in (0.5, 0.75, 0.9)],
                   'khong_tp_dat': {str(x): round(float((kh['mfe'] >= x).mean() * 100), 1) for x in (1, 2, 3)} if len(kh) else {}}
        b = kq['B']
        print(f'B. Đi ngược, đi thuận (R; trung vị / phân vị 75 / phân vị 90)\n'
              f'  Lệnh THẮNG ({b["n_thang"]:,}): đi ngược tối đa {b["mae_thang"]} · {b["thang_di_nguoc_duoi_nua_r"]}% lệnh thắng chưa từng đi ngược quá 0,5R\n'
              f'  Lệnh THUA ({b["n_thua"]:,}): đi thuận tối đa trước khi thua {b["mfe_thua"]} · {b["thua_tung_dat_1r"]}% lệnh thua đã từng lãi từ 1R\n'
              f'  Không đặt chốt lời (giữ tới dừng lỗ hoặc 24 giờ): đi thuận tối đa {b["khong_tp_mfe"]} · tỷ lệ từng đạt 1R / 2R / 3R: {b["khong_tp_dat"]}')
        # C. kiểu vào
        bang = {'V0': kq['A']['moi']}
        run = {'V0': moi}
        for v in KIEU_VAO[ma][1:]:
            run[v] = chay(D, th, ma, vao=v)
            bang[v] = hai_phan(run[v])
        KQ['so_phep_so'] += len(bang) - 1
        giu_v, doi, vi = chon(bang, 'V0')
        kq['C'] = {'bang': bang, 'giu': giu_v, 'doi': doi, 'vi': vi, 'lo': {}}
        print('C. Kiểu vào\n' + DAU_BANG)
        for v in bang:
            print(dong(f'{v} {TEN_VAO[G][v]}', bang[v]))
        ngay = run['V0' if G == 'tt' else 'V3'].set_index('so')        # kết quả nếu vào ngay, để xem lệnh chờ bỏ lỡ lệnh loại nào
        for v in bang:
            if v == ('V0' if G == 'tt' else 'V3'):
                continue
            x = run[v].set_index('so')
            lo = ngay.reindex(x.index[~x['khop'].to_numpy()])
            lo = lo[lo['khop'] == True]                                # noqa: E712
            co = ngay.reindex(x.index[x['khop'].to_numpy()])
            co = co[co['khop'] == True]                                # noqa: E712
            if len(lo) and len(co):
                kq['C']['lo'][v] = {'n_lo': int(len(lo)), 'r_lo': round(float(lo['r'].mean()), 3), 'n_khop': int(len(co)), 'r_khop': round(float(co['r'].mean()), 3)}
                print(f'     {v}: nếu vào ngay, {len(lo):,} tín hiệu KHÔNG khớp cho {lo["r"].mean():+.3f}R mỗi lệnh; {len(co):,} tín hiệu có khớp cho {co["r"].mean():+.3f}R'.replace('.', ','))
        print(f'  → giữ {giu_v}: {vi}')
        # D1. dừng lỗ
        bang = {'S0': bang[giu_v]}
        for v in ('S1', 'S2', 'S3'):
            bang[v] = hai_phan(chay(D, th, ma, vao=giu_v, sl=v))
        KQ['so_phep_so'] += 3
        giu_s, doi, vi = chon(bang, 'S0')
        kq['D1'] = {'bang': bang, 'giu': giu_s, 'doi': doi, 'vi': vi}
        print('D1. Dừng lỗ\n' + DAU_BANG)
        for v in bang:
            print(dong(f'{v} {TEN_SL[v]}', bang[v]))
        print(f'  → giữ {giu_s}: {vi}')
        # D2. chốt lời
        bang = {'T0': bang[giu_s]}
        for v in ('T1', 'T2', 'T3'):
            bang[v] = hai_phan(chay(D, th, ma, vao=giu_v, sl=giu_s, tp=v))
        KQ['so_phep_so'] += 3
        giu_t, doi, vi = chon(bang, 'T0')
        kq['D2'] = {'bang': bang, 'giu': giu_t, 'doi': doi, 'vi': vi}
        print('D2. Chốt lời\n' + DAU_BANG)
        for v in bang:
            print(dong(f'{v} {TEN_TP[v]}', bang[v]))
        print(f'  → giữ {giu_t}: {vi}')
        # E. bối cảnh
        bc = boi_canh(D, th, fr['M15'], fr['H4'])
        nen = chay(D, th, ma, vao=giu_v, sl=giu_s, tp=giu_t)
        bang = {'không lọc': hai_phan(nen)}
        giu_l = []
        print('E. Bối cảnh (mỗi bộ lọc xét riêng)\n' + DAU_BANG)
        print(dong('không lọc', bang['không lọc']))
        for v in ('L1', 'L2', 'L3', 'L4'):
            con = nen[~bc[v][nen['so'].to_numpy()]]
            bang[v] = hai_phan(con)
            KQ['so_phep_so'] += 1
            tot_chinh = bang[v]['chinh']['n'] >= TOI_THIEU and bang[v]['chinh']['r_tb'] > bang['không lọc']['chinh']['r_tb']
            dat, vi = cong(bang['không lọc'], bang[v]) if tot_chinh else (False, 'không cải thiện trên phần chỉnh')
            if dat:
                giu_l.append(v)
            bo = int(bc[v][nen['so'].to_numpy()].sum())
            print(dong(f'{v} {TEN_LOC[v]} (bỏ {bo:,})', bang[v]) + f'\n     → {"GIỮ" if dat else "không giữ"}: {vi}')
        kq['E'] = {'bang': bang, 'giu': giu_l}
        bo = np.zeros(len(th), bool)                               # bản cuối: gộp mọi bộ lọc được giữ (chỉ để báo số, không phải một phép chọn nữa)
        for v in giu_l:
            bo |= bc[v]
        kq['cuoi'] = hai_phan(nen[~bo[nen['so'].to_numpy()]])
        print('Bản cuối theo cổng (' + ', '.join([giu_v, giu_s, giu_t] + giu_l) + ')\n' + dong('bản hiện tại của webapp', kq['A']['moi']) + '\n' + dong('bản cuối', kq['cuoi']))
        KQ['ap_dung'][ma] = {'vao': giu_v, 'sl': giu_s, 'tp': giu_t, 'loc': giu_l}
        diem = 4 - sum(bc[v][nen['so'].to_numpy()].astype(int) for v in ('L1', 'L2', 'L3', 'L4'))
        gop_diem.append(nen.assign(diem=diem, ma=ma))
        print(f'  ({time.time() - t1:.0f} giây)', flush=True)
    # F. điểm chất lượng, gộp tám phương pháp
    tat = pd.concat(gop_diem)
    tat = tat[tat['khop']]
    print('\n══════ F. Điểm chất lượng = số điều kiện bối cảnh đạt (0–4), gộp tám phương pháp ══════')
    F = {}
    for ten, phan in (('chinh', tat[tat['nam'] < CAT_NAM]), ('kiem', tat[tat['nam'] >= CAT_NAM])):
        F[ten] = {str(d): {'n': int((phan['diem'] == d).sum()), 'r_tb': round(float(phan.loc[phan['diem'] == d, 'r'].mean()), 4) if (phan['diem'] == d).any() else None}
                  for d in (4, 3, 2)}
        thap = phan[phan['diem'] <= 1]
        F[ten]['0-1'] = {'n': int(len(thap)), 'r_tb': round(float(thap['r'].mean()), 4) if len(thap) else None}
        print(f'  {"CHỈNH" if ten == "chinh" else "KIỂM TRA"}: ' + ' · '.join(f'điểm {d}: {v["n"]:,} lệnh, {v["r_tb"]:+.3f}R' if v['r_tb'] is not None else f'điểm {d}: 0 lệnh'
                                                                           for d, v in F[ten].items()).replace('.', ','))
    k = F['kiem']
    du = all(k[d]['n'] >= TOI_THIEU for d in ('4', '3', '2', '0-1'))
    tang = du and k['4']['r_tb'] > k['3']['r_tb'] > k['2']['r_tb'] > k['0-1']['r_tb']
    KQ['F'] = {'bang': F, 'dat': bool(tang), 'vi': 'R mỗi lệnh tăng dần theo điểm trên phần kiểm tra' if tang else
               ('có nhóm điểm dưới 100 lệnh ở phần kiểm tra' if not du else 'R mỗi lệnh KHÔNG tăng dần theo điểm trên phần kiểm tra')}
    print(f'  → {"HIỆN điểm số" if tang else "KHÔNG hiện điểm số, chỉ hiện từng điều kiện đạt/chưa đạt"}: {KQ["F"]["vi"]}')
    print(f'\nTổng số phép so đã làm (không kể bản hiện tại): {KQ["so_phep_so"]}')
    print('Áp dụng theo cổng: ' + json.dumps(KQ['ap_dung'], ensure_ascii=False))
    (GOC / 'out').mkdir(exist_ok=True)
    (GOC / 'out' / 'diem-vao.json').write_text(json.dumps(KQ, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'Xong sau {time.time() - t0:.0f} giây. Kết quả: out/diem-vao.json')
