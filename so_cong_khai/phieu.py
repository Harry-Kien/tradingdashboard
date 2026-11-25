"""Phiếu vào lệnh cho tám phương pháp tùy chọn: với tín hiệu gần nhất của một phương pháp, nêu loại lệnh và giá vào, dừng lỗ, hai mức chốt, thời
hạn, điều kiện hủy, các điều kiện bối cảnh đạt/chưa đạt, và số đo lịch sử của ĐÚNG công thức đó.

Công thức của từng phương pháp (CONG_THUC) là kết quả đo ngày 24/11/2026 bằng cong-cu/diem_vao.py trên vàng 2015–11/2026: biến thể được chọn trên
phần chỉnh 2015–2021 và chỉ được nhận khi qua cổng trên phần kiểm tra 2022–2026 (luật và cổng ghi trước ở cong-cu/CHUAN_HOA_DANG_KY.md). 107 phép
so đã được làm, nên một số biến thể qua cổng có thể chỉ nhờ may; và sau khi áp dụng, lãi kỳ vọng của mọi phương pháp vẫn âm hoặc quanh 0. Phiếu ghi
đúng số đo đó. Phiếu KHÔNG thay luật gốc của phương pháp: phương án gốc, nhật ký điểm vào và các phép đối chiếu vẫn theo luật gốc.

Các hàm muc_cho và muc_sl ở đây cũng là hàm mà cong-cu/diem_vao.py dùng để đo, nên mức giá trên phiếu trùng với mức đã đo. Trạng thái lúc sống (đang
chờ, đã khớp, đã hủy) xét trên nến M15 đã đóng và giá hiện tại, thô hơn phép đo (đi bằng nến 1 phút). Hàm thuần: không đọc MT5, không đặt lệnh.
Đây là kết quả của một công thức đã đo, không phải lời khuyên đầu tư."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from . import phuong_phap as PP

THI_TRUONG = ('pha_vo', 'elliott', 'wyckoff', 'price_action', 'ema_hoi')       # các phương pháp mà luật gốc vào ngay khi nến tín hiệu đóng
NGAY_DO = '24/11/2026'
# Công thức đã qua cổng. vao: kiểu vào; sl: cách đặt dừng lỗ; tp: cách chốt (T0 = chốt hết ở 2R); loc: các bộ lọc bối cảnh được giữ.
CONG_THUC = {
    'pha_vo': {'vao': 'V2', 'sl': 'S3', 'tp': 'T0', 'loc': ('L4',)},
    'ict': {'vao': 'V3', 'sl': 'S2', 'tp': 'T0', 'loc': ('L2', 'L4')},
    'ict_fvg': {'vao': 'V3', 'sl': 'S0', 'tp': 'T0', 'loc': ('L2', 'L4')},
    'elliott': {'vao': 'V0', 'sl': 'S2', 'tp': 'T0', 'loc': ()},
    'wyckoff': {'vao': 'V2', 'sl': 'S1', 'tp': 'T0', 'loc': ('L4',)},
    'price_action': {'vao': 'V2', 'sl': 'S3', 'tp': 'T0', 'loc': ('L1',)},
    'fib': {'vao': 'V1', 'sl': 'S0', 'tp': 'T0', 'loc': ('L2',)},
    'ema_hoi': {'vao': 'V2', 'sl': 'S3', 'tp': 'T0', 'loc': ()},
}
TEN_LOAI = {'tt': 'Vào ngay theo giá thị trường', 'gh': 'Lệnh chờ giới hạn', 'dung': 'Lệnh chờ dừng'}
TEN_SL = {'S0': 'mức của phương pháp', 'S1': 'cách giá vào 1,5 ATR', 'S2': 'mức của phương pháp lùi thêm đúng spread', 'S3': 'mức của phương pháp lùi thêm 0,5 ATR'}
TEN_LOC = {'L1': 'Không nằm trong 60 phút quanh tin USD mức cao', 'L2': 'Spread không quá 2 lần mức thường',
           'L3': 'Còn ít nhất 1R trước đỉnh/đáy 24 giờ', 'L4': 'Thuận xu hướng H4 (EMA20 so với EMA50)'}
_nho: dict = {}


def nhom(ma: str) -> str:
    return 'tt' if (ma in THI_TRUONG or ma == 'bot') else 'fib' if ma == 'fib' else 'ict'      # 'bot': luật bot tín hiệu, chỉ dùng khi đo


def muc_cho(s: dict, ma: str, vao: str):
    """(loại, mức giá) của lệnh ứng với kiểu vào: 'tt' vào ngay, 'gh' chờ giới hạn, 'dung' chờ dừng, 'xn' xác nhận nến M5 (mức = mức phải chạm trước,
    hoặc None). `s` là tín hiệu của phuong_phap.quet, có thêm đỉnh và đáy nến tín hiệu ('nen_h', 'nen_l')."""
    mua = s['huong'] == 'MUA'
    g = nhom(ma)
    if g == 'tt':
        if vao == 'V0':
            return 'tt', None
        if vao == 'V1':
            return 'gh', (s['nen_h'] + s['nen_l']) / 2
        if vao == 'V2':
            return 'dung', s['nen_h'] if mua else s['nen_l']
        return 'xn', None
    if vao == 'V3':
        return 'tt', None
    if g == 'ict':
        gan, xa = (max(s['vung']), min(s['vung'])) if mua else (min(s['vung']), max(s['vung']))
        return {'V0': ('gh', s['vao']), 'V1': ('gh', gan), 'V2': ('gh', xa), 'V4': ('xn', gan)}[vao]
    m618 = s['vao']                                                # fib: vùng = [mức 61,8%, mức 50%]
    m50 = max(s['vung']) if mua else min(s['vung'])
    nhip = abs(m50 - m618) / (PP.FIB - 0.5)
    m786 = m618 - (0.786 - PP.FIB) * nhip if mua else m618 + (0.786 - PP.FIB) * nhip
    return {'V0': ('gh', m618), 'V1': ('gh', m50), 'V2': ('gh', m786), 'V4': ('xn', m50)}[vao]


def muc_sl(s: dict, ma: str, sl: str, gia_khop: float, spread_luc: float) -> float:
    """Mức dừng lỗ theo cách `sl`. S1 tính từ giá khớp (riêng Phá vỡ: sau đỉnh/đáy nến tín hiệu); S2 và S3 lùi mức gốc ra xa giá."""
    dau = 1.0 if s['huong'] == 'MUA' else -1.0
    if sl == 'S1':
        if ma == 'pha_vo':
            return (s['nen_l'] - PP.DEM_ATR * s['atr']) if dau > 0 else (s['nen_h'] + PP.DEM_ATR * s['atr'])
        return gia_khop - dau * PP.SL_PHA_ATR * s['atr']
    if sl == 'S2':
        return s['sl'] - dau * spread_luc
    if sl == 'S3':
        return s['sl'] - dau * 0.5 * s['atr']
    return s['sl']


def so_do(ma: str, tep: Path | None = None) -> dict | None:
    """{'goc': …, 'phieu': …, 'so_phep_so': …} đọc từ out/diem-vao.json (do cong-cu/diem_vao.py ghi); chưa có tệp thì None. Nhớ theo giờ sửa tệp."""
    tep = tep or Path(__file__).resolve().parent.parent / 'out' / 'diem-vao.json'
    try:
        key = (str(tep), tep.stat().st_mtime_ns)
        if _nho.get('key') != key:
            _nho.update(key=key, kq=json.loads(tep.read_text(encoding='utf-8')))
        x = _nho['kq']['pp'][ma]
        return {'goc': x['A']['moi'], 'phieu': x['cuoi'], 'so_phep_so': _nho['kq'].get('so_phep_so'), 'cat_nam': _nho['kq'].get('cat_nam')}
    except (OSError, ValueError, KeyError):
        return None


BOT_KHOANG = (10.0, 35.0)        # khoảng rủi ro (giá) được nhận khi đo điểm vào của luật bot (cong-cu/diem_vao_bot.py)


def so_do_bot(tep: Path | None = None) -> dict | None:
    """{'goc': bản hiện tại của bot, 'phieu': bản cuối theo cổng} đọc từ out/diem-vao-bot.json (cong-cu/diem_vao_bot.py); chưa có tệp thì None."""
    tep = tep or Path(__file__).resolve().parent.parent / 'out' / 'diem-vao-bot.json'
    try:
        key = ('bot', str(tep), tep.stat().st_mtime_ns)
        if _nho.get('key_bot') != key:
            _nho.update(key_bot=key, kq_bot=json.loads(tep.read_text(encoding='utf-8')))
        x = _nho['kq_bot']
        return {'goc': x['A']['moi'], 'phieu': x['cuoi'], 'so_phep_so': x.get('so_phep_so'), 'cat_nam': x.get('cat_nam'), 'ap_dung': x.get('ap_dung')}
    except (OSError, ValueError, KeyError):
        return None


BOT_MAC_DINH = {'vao': 'V2', 'sl': 'S0', 'tp': 'TL'}       # công thức khi chưa có tệp số đo
BOT_TEN_VAO = {'V0': 'vào ngay khi nến tín hiệu đóng (như bot)', 'V1': 'chờ hồi về giữa nến tín hiệu',
               'V2': 'chờ giá phá đỉnh/đáy nến tín hiệu rồi mới vào (bỏ được các tín hiệu hỏng ngay)'}
BOT_TEN_SL = {'S0': '', 'S2': 'dừng lỗ lùi thêm đúng spread', 'S3': 'dừng lỗ lùi thêm 3 giá'}
BOT_TEN_TP = {'TL': 'thang sáu mức chốt như bot, tính lại từ giá vào của phiếu', 'TLB': 'thang sáu mức chốt, tính lại từ giá vào của phiếu',
              'T0': 'chốt hết ở 2R', 'T1': 'chốt hết ở 1R'}


def lap_bot(pa: dict, nen: datetime, nen_h: float, nen_l: float, khung: str, bid: float, ask: float, now: datetime, tp_r, so_le: int = 2,
            ct: dict | None = None) -> dict | None:
    """Phiếu cho luật bot (chỉ phương án 'bot:nen', là kiểu lệnh đã được đo). Công thức `ct` mặc định lấy từ lần đo gần nhất của cong-cu/diem_vao_bot.py
    (mục 'ap_dung' của out/diem-vao-bot.json), nên khi bot đổi và được đo lại thì phiếu tự đổi theo. Kiểu vào: V0 vào ngay, V1 chờ hồi về giữa nến tín
    hiệu, V2 chờ phá đỉnh/đáy nến tín hiệu (V3 xác nhận nến M5 chưa làm được lúc sống: không ra phiếu). Dừng lỗ: S0 mức bot, S2 lùi thêm spread, S3
    lùi thêm 3 giá. Chốt: TL/TLB thang `tp_r`, T0 chốt hết ở 2R, T1 ở 1R; mọi mức tính lại từ giá vào của phiếu. Nhật ký chấm phiếu theo mức chốt
    đầu ('i_chinh' = 0), như lệnh gốc của bot. `nen`: giờ nến tín hiệu đóng. Hàm thuần: không đặt lệnh."""
    if pa.get('ma') != 'bot:nen' or not pa.get('co') or pa.get('sl') is None:
        return None
    sd = so_do_bot()
    ct = dict(ct or (sd or {}).get('ap_dung') or BOT_MAC_DINH)
    if ct.get('vao') not in BOT_TEN_VAO:
        return None
    r = lambda x: round(float(x), so_le)                           # noqa: E731
    mua = pa['huong'] == 'MUA'
    dau = 1.0 if mua else -1.0
    sp = max(0.0, ask - bid)
    sl = float(pa['sl']) - dau * {'S2': sp, 'S3': 3.0}.get(ct.get('sl'), 0.0)
    loai = {'V0': 'tt', 'V1': 'gh', 'V2': 'dung'}[ct['vao']]
    muc = (ask if mua else bid) if loai == 'tt' else (nen_h + nen_l) / 2 if loai == 'gh' else (nen_h if mua else nen_l)
    tuoi = max(0.0, (now - nen).total_seconds() / 60)
    con = int(PP.CHO_NEN * 15 - tuoi)
    tt = 'con_hieu_luc'
    if not pa.get('hieu_luc'):
        tt = 'qua_tre'
    elif loai == 'dung' and ((ask >= muc) if mua else (bid <= muc)):
        tt = 'da_khop'
    elif loai == 'gh' and ((ask <= muc) if mua else (bid >= muc)):
        tt = 'da_khop'
    elif loai != 'tt' and ((bid <= sl) if mua else (ask >= sl)):
        tt = 'da_huy'
    elif loai != 'tt' and con <= 0:
        tt = 'het_han'
    rui = (muc - sl) * dau
    if tt == 'con_hieu_luc' and not (BOT_KHOANG[0] <= rui <= BOT_KHOANG[1]):
        tt = 'rui_ro'
    if rui <= 0:
        return None
    muc_tp = list(tp_r) if ct.get('tp') in ('TL', 'TLB') else [2.0] if ct.get('tp') == 'T0' else [1.0]
    khac = [BOT_TEN_VAO[ct['vao']]] + ([BOT_TEN_SL[ct['sl']]] if BOT_TEN_SL.get(ct.get('sl')) else []) + [BOT_TEN_TP.get(ct.get('tp'), '')]
    huy = {'tt': 'Vào ngay khi nến tín hiệu vừa đóng, như bot; quá hạn của bot thì bỏ.',
           'gh': 'Hủy nếu giá chạm dừng lỗ trước khi khớp, hoặc sau 4 giờ chưa khớp.',
           'dung': 'Hủy nếu giá chạm dừng lỗ trước khi lệnh được kích hoạt, hoặc sau 4 giờ chưa kích hoạt.'}[loai]
    return {'ma': 'bot', 'ten': 'Luật bot tín hiệu', 'huong': pa['huong'], 'loai': loai, 'ten_loai': TEN_LOAI[loai], 'trang_thai': tt, 'vao': r(muc), 'sl': r(sl),
            'tp': [r(muc + dau * x * rui) for x in muc_tp], 'rr': muc_tp, 'rui_ro_gia': r(rui), 'vung': None,
            'con_phut': con if (tt == 'con_hieu_luc' and loai != 'tt') else None, 'tuoi_phut': int(tuoi), 'vao_luc': 'hien_tai', 'ket_cuc': None, 'khung': khung,
            'i_chinh': 0, 'nen': nen.isoformat(), 'huy': huy, 'ly_do': pa.get('ly_do', ''), 'khac_luat_goc': [x for x in khac if x],
            'dieu_kien': [], 'loc_hong': [], 'cong_thuc': {'vao': ct['vao'], 'sl': ct.get('sl', 'S0'), 'tp': ct.get('tp', 'TL'), 'loc': list(ct.get('loc') or [])},
            'so_do': sd, 'ngay_do': NGAY_DO}


def dieu_kien(s: dict, m15: pd.DataFrame, h4: pd.DataFrame, tin: list, spread: float, spread_thuong: float) -> dict:
    """{'L1'…'L4': True nếu điều kiện ĐẠT (tín hiệu không bị bộ lọc đó bỏ)}. L2 lúc sống so spread hiện tại với mức thường của cấu hình (phép đo
    dùng trung vị 1.440 nến 1 phút trước đó)."""
    mua = s['huong'] == 'MUA'
    t = pd.Timestamp(s['t'])
    gan = any(abs((t - pd.Timestamp(x)).total_seconds()) <= 3600 for x in tin) if tin else False
    doan = m15.iloc[max(0, s['i'] - PP.N_BIEN + 1):s['i'] + 1]
    cho = (float(doan['high'].max()) - s['vao']) if mua else (s['vao'] - float(doan['low'].min()))
    d4 = np.sign(PP._ema(h4['close'], 20) - PP._ema(h4['close'], 50)).fillna(0.0)
    d4.index = d4.index + timedelta(hours=4)
    truoc = d4[d4.index <= t]
    xu4 = float(truoc.iloc[-1]) if len(truoc) else 0.0
    return {'L1': not gan, 'L2': not (spread > 2 * spread_thuong), 'L3': not (cho < abs(s['vao'] - s['sl'])), 'L4': not (xu4 * (1 if mua else -1) < 0)}


def lap(ma: str, m15: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame, bid: float, ask: float, now: datetime, tin: list, spread_thuong: float,
        so_le: int = 2) -> dict | None:
    """Phiếu vào lệnh của tín hiệu gần nhất (trong 4 giờ) của phương pháp `ma`, hoặc None khi không có tín hiệu nào. Trường 'trang_thai':
    'con_hieu_luc' (đặt được lúc này), 'bi_loc' (bộ lọc đã qua cổng loại tín hiệu), 'da_khop', 'da_huy', 'het_han', 'qua_tre', 'da_qua', 'rui_ro'.
    'vao_luc': 'hien_tai' (giá vào là giá lúc này) hoặc 'tin_hieu' (phiếu vào ngay đã quá hạn: giá vào là giá lúc tín hiệu đến, chỉ để xem lại);
    khi đó 'ket_cuc' là 'sl', 'tp' (đã chạm dừng lỗ hoặc chốt 2R từ lúc ấy, xét trên nến M15) hoặc None. Dừng lỗ luôn ở phía thua của giá vào."""
    m = m15.iloc[-400:]
    n = len(m)
    if n < 80 or ma not in CONG_THUC:
        return None
    ct = CONG_THUC[ma]
    h, l = m['high'].to_numpy(dtype=float), m['low'].to_numpy(dtype=float)
    s = next((dict(x, nen_h=float(h[x['i']]), nen_l=float(l[x['i']])) for x in reversed(PP.quet(ma, m, h1)) if x['i'] >= n - PP.CHO_NEN), None)
    if s is None:
        return None
    r = lambda x: round(float(x), so_le)                           # noqa: E731
    mua = s['huong'] == 'MUA'
    dau = 1.0 if mua else -1.0
    sp = max(0.0, ask - bid)
    loai, muc = muc_cho(s, ma, ct['vao'])
    tuoi = max(0.0, (now - s['t'].to_pydatetime()).total_seconds() / 60)
    han = PP.CHO_NEN * 15
    sau = m.iloc[s['i'] + 1:]
    tt, gia_vao, con, vao_luc, ket = 'con_hieu_luc', None, None, 'hien_tai', None
    if loai == 'tt':
        gia_vao = ask if mua else bid
        if s['i'] != n - 1 or tuoi > PP.TRE_PHUT:
            tt = 'qua_tre'
        elif (gia_vao - muc_sl(s, ma, ct['sl'], gia_vao, sp)) * dau <= 0:
            tt = 'rui_ro'                                             # tín hiệu còn mới nhưng giá đã ở bên kia dừng lỗ
        if tt != 'con_hieu_luc':
            # Giá hiện tại không còn là giá vào của tín hiệu này. Lấy giá mà phép đo đã vào: giá mở nến ngay sau nến tín hiệu (mua thì cộng spread).
            # Nếu vẫn lấy giá hiện tại thì khi giá đã chạy qua dừng lỗ, dừng lỗ sẽ nằm sai phía và hai mức chốt bị lật ngược.
            mo = float(sau['open'].iloc[0]) if len(sau) else float(m['close'].iloc[s['i']])
            gia_vao, vao_luc = mo + (sp if mua else 0.0), 'tin_hieu'
    else:
        gia_vao, con = muc, int(han - tuoi)
        sl_truoc = muc_sl(s, ma, ct['sl'], muc, sp)
        mo_dau = float(sau['open'].iloc[0]) if len(sau) else bid
        if loai == 'gh' and ((mo_dau <= muc) if mua else (mo_dau >= muc)):
            tt = 'da_qua'
        else:
            nen = [(float(a), float(b)) for a, b in zip(sau['high'], sau['low'])] + [(bid, bid)]     # nến đã đóng sau tín hiệu, rồi tới giá hiện tại
            for cao, thap in nen:
                if loai == 'gh':
                    khop = (thap + sp <= muc) if mua else (cao >= muc)
                else:
                    khop = (cao + sp >= muc) if mua else (thap <= muc)
                if khop:
                    tt = 'da_khop'
                    break
                if (thap <= sl_truoc) if mua else (cao + sp >= sl_truoc):
                    tt = 'da_huy'
                    break
            if tt == 'con_hieu_luc' and con <= 0:
                tt = 'het_han'
    sl = muc_sl(s, ma, ct['sl'], gia_vao, sp)
    rui = (gia_vao - sl) * dau
    if rui <= 0:
        return None                                                    # không dựng được phiếu có dừng lỗ đúng phía (phép đo cũng bỏ tín hiệu như vậy)
    if vao_luc == 'tin_hieu':                                          # phiếu chỉ để xem lại: từ lúc tín hiệu đến nay giá đã chạm mức nào trước
        tp2 = gia_vao + dau * PP.TP_R * rui
        for cao, thap in [(float(a), float(b)) for a, b in zip(sau['high'], sau['low'])] + [(bid, bid)]:
            if (thap <= sl) if mua else (cao + sp >= sl):              # cùng một nến chạm cả hai mức thì tính là dừng lỗ
                ket = 'sl'
                break
            if (cao >= tp2) if mua else (thap + sp <= tp2):
                ket = 'tp'
                break
    lo, hi =(PP.RUI_RO_ATR[0] * (0.6 if loai == 'tt' else 1.0), PP.RUI_RO_ATR[1] * (1.3 if loai == 'tt' else 1.0))    # vào ngay: nới như phương án gốc, vì giá đã chạy từ lúc nến đóng
    if tt == 'con_hieu_luc' and not (rui > 0 and lo * s['atr'] <= rui <= hi * s['atr']):
        tt = 'rui_ro'
    dk = dieu_kien(s, m, h4, tin, sp, spread_thuong)
    hong = [k for k in ct['loc'] if not dk[k]]
    if tt == 'con_hieu_luc' and hong:
        tt = 'bi_loc'
    goc_loai = 'tt' if ma in THI_TRUONG else 'gh'
    khac = []
    if loai != goc_loai or (loai == 'gh' and abs(muc - s['vao']) > 1e-9):
        khac.append({'tt': 'vào ngay khi nến tín hiệu đóng thay cho lệnh chờ ở giữa vùng (lệnh chờ bỏ lỡ nhiều lệnh thắng mạnh)',
                     'dung': 'chờ giá phá đỉnh/đáy nến tín hiệu rồi mới vào (bỏ được các tín hiệu hỏng ngay)',
                     'gh': 'lệnh chờ ở mức hồi 50% thay cho 61,8%' if ma == 'fib' else 'đổi mức chờ'}[loai])
    if ct['sl'] != 'S0':
        khac.append('dừng lỗ: ' + TEN_SL[ct['sl']])
    if ct['loc']:
        khac.append('thêm bộ lọc: ' + '; '.join(TEN_LOC[k].lower() for k in ct['loc']))
    huy = {'tt': 'Vào ngay sau khi nến tín hiệu đóng; quá ' + str(PP.TRE_PHUT) + ' phút thì bỏ.',
           'gh': 'Hủy nếu giá chạm dừng lỗ trước khi khớp, hoặc sau 4 giờ chưa khớp.',
           'dung': 'Hủy nếu giá chạm dừng lỗ trước khi lệnh được kích hoạt, hoặc sau 4 giờ chưa kích hoạt.'}[loai]
    return {'ma': ma, 'ten': PP.DS[ma]['ten'], 'huong': s['huong'], 'loai': loai, 'ten_loai': TEN_LOAI[loai], 'trang_thai': tt, 'vao': r(gia_vao), 'sl': r(sl),
            'tp': [r(gia_vao + dau * rui), r(gia_vao + dau * PP.TP_R * rui)], 'rr': [1.0, PP.TP_R], 'rui_ro_gia': r(abs(rui)), 'vung': [r(v) for v in s['vung']] if s.get('vung') else None,
            'con_phut': con if tt == 'con_hieu_luc' else None, 'tuoi_phut': int(tuoi), 'vao_luc': vao_luc, 'ket_cuc': ket, 'huy': huy, 'nen': s['t'].isoformat(), 'ly_do': s['ly_do'],
            'dieu_kien': [{'ma': k, 'ten': TEN_LOC[k], 'dat': bool(dk[k]), 'bat_buoc': k in ct['loc']} for k in ('L1', 'L2', 'L3', 'L4')],
            'loc_hong': [TEN_LOC[k] for k in hong], 'khac_luat_goc': khac, 'cong_thuc': dict(ct, loc=list(ct['loc'])), 'so_do': so_do(ma), 'ngay_do': NGAY_DO}
