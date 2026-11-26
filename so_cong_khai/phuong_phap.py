"""Các phương pháp phân tích tùy chọn, viết thành quy tắc máy rõ ràng để vừa tìm được điểm vào trên biểu đồ lúc này, vừa chạy lại
được trên dữ liệu quá khứ bằng đúng quy tắc đó:

  pha_vo   Phá vỡ đỉnh/đáy (breakout, breakdown): nến M15 đóng vượt đỉnh hoặc thủng đáy 8 giờ với thân nến đủ lớn.
  ict      ICT, quét thanh khoản rồi để lại khoảng trống giá: giá quét qua đáy/đỉnh 5 giờ rồi đóng ngược lại, sau đó bật mạnh để lại
           một khoảng trống giá (FVG); vào bằng lệnh chờ ở giữa khoảng trống đó.
  ema_hoi  Hồi về EMA theo xu hướng: H1 và M15 cùng chiều, nến M15 chạm EMA20 rồi đóng trở lại theo xu hướng.

Mọi khoảng cách tính theo ATR14 của khung M15, không theo số tuyệt đối, nên quy tắc dùng được cho mọi mã. Dừng lỗ đặt theo cấu trúc
của từng phương pháp; chốt lời ở 2R (TP1 ở 1R chỉ để tham khảo). Đây là các phương pháp phổ biến được viết lại cho máy đọc được,
KHÔNG phải luật trong sổ của chủ dự án và chưa từng được chạy bóng. Bằng chứng duy nhất là phần chạy lại trong hoc.py.

Hàm thuần: chỉ nhận bảng nến, không đọc tệp, không nối MT5, không đặt lệnh."""
from __future__ import annotations

import re
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

DS = {
    'pha_vo': {'ten': 'Phá vỡ đỉnh/đáy', 'ngan': 'Phá vỡ', 'truong_phai': 'Breakout, breakdown', 'kieu': 'nến M15 vừa đóng, vào theo giá thị trường',
               'mo_ta': 'Nến M15 đóng vượt đỉnh (hoặc thủng đáy) của 8 giờ trước đó, thân nến ít nhất 0,5 ATR. Dừng lỗ cách giá vào 1,5 ATR.',
               'khong': 'Nến M15 vừa đóng không vượt đỉnh hay thủng đáy 8 giờ với thân nến đủ lớn.'},
    'ict': {'ten': 'ICT/SMC: quét thanh khoản và khoảng trống giá', 'ngan': 'ICT/SMC', 'chip': 'ict', 'truong_phai': 'SMC và ICT', 'kieu': 'lệnh chờ ở giữa khoảng trống giá', 'cho': True,
            'mo_ta': 'Giá quét qua đáy (hoặc đỉnh) 5 giờ rồi đóng ngược lại, sau đó bật mạnh để lại khoảng trống giá (FVG). Vào bằng lệnh chờ ở giữa '
                     'khoảng trống, dừng lỗ ngay sau điểm quét, lệnh chờ sống 4 giờ.',
            'khong': 'Trong 4 giờ qua không có lần quét đáy/đỉnh 5 giờ nào kèm khoảng trống giá.'},
    'ict_fvg': {'ten': 'ICT/SMC: hồi về khoảng trống giá sau khi phá cấu trúc', 'ngan': 'ICT/SMC', 'chip': 'ict', 'truong_phai': 'SMC và ICT', 'kieu': 'lệnh chờ ở giữa khoảng trống giá', 'cho': True,
                'mo_ta': 'H1 có xu hướng; một nhịp bật mạnh theo xu hướng đóng vượt đỉnh (thủng đáy) 5 giờ và để lại khoảng trống giá. Vào bằng lệnh chờ ở giữa khoảng trống, '
                         'dừng lỗ sau điểm bắt đầu nhịp bật, lệnh chờ sống 4 giờ.',
                'khong': 'Trong 4 giờ qua không có nhịp phá cấu trúc nào theo xu hướng H1 để lại khoảng trống giá, hoặc giá đã hồi về lấp rồi.'},
    'elliott': {'ten': 'Sóng Elliott: vào sóng 3 sau khi sóng 2 hồi xong', 'ngan': 'Elliott', 'truong_phai': 'Sóng Elliott', 'kieu': 'vào theo giá thị trường khi nến đóng vượt cuối sóng 1',
                'mo_ta': 'Đỉnh và đáy lấy theo zigzag (mỗi lần đảo chiều ít nhất 2 ATR). Sóng 1 dài ít nhất 3 ATR; sóng 2 hồi 38,2–78,6% của sóng 1 và không vượt điểm bắt đầu sóng 1. '
                         'Vào khi nến M15 đóng vượt cuối sóng 1 (xác nhận sóng 3), dừng lỗ ngay sau cuối sóng 2. Mục tiêu lý thuyết: sóng 3 bằng 1,618 lần sóng 1.',
                'khong': 'Chưa có cặp sóng 1–2 hợp lệ vừa được nến M15 xác nhận.'},
    'wyckoff': {'ten': 'Wyckoff: spring và upthrust', 'ngan': 'Wyckoff', 'truong_phai': 'Wyckoff', 'kieu': 'nến M15 vừa đóng, vào theo giá thị trường',
                'mo_ta': 'Giá đi ngang 12 giờ trong một vùng rộng 2–8 ATR; một nến đâm thủng biên dưới (hoặc trên) của vùng rồi đóng trở lại bên trong. '
                         'Dừng lỗ ngay sau mũi đâm. Kho nến không có khối lượng, nên phần xác nhận bằng khối lượng của Wyckoff KHÔNG có ở đây.',
                'khong': 'Giá không đi ngang đủ lâu trong một vùng hẹp, hoặc nến M15 vừa đóng không đâm thủng biên vùng rồi đóng trở lại.'},
    'price_action': {'ten': 'Price Action: pin bar và nhấn chìm theo xu hướng', 'ngan': 'Price Action', 'truong_phai': 'Price Action', 'kieu': 'nến M15 vừa đóng, vào theo giá thị trường',
                     'mo_ta': 'Xu hướng H1 rõ (EMA20 so với EMA50); nến M15 tạo đáy (đỉnh) mới của 2 giờ rồi thành pin bar hoặc nến nhấn chìm theo xu hướng. '
                              'Dừng lỗ ngay sau đuôi nến.',
                     'khong': 'H1 chưa có xu hướng, hoặc nến M15 vừa đóng không phải pin bar hay nến nhấn chìm tại đáy/đỉnh 2 giờ.'},
    'fib': {'ten': 'Fibonacci: hồi 61,8% sau nhịp đẩy', 'ngan': 'Fibonacci', 'truong_phai': 'Sóng Elliott và Fibonacci', 'kieu': 'lệnh chờ ở mức hồi 61,8%', 'cho': True,
            'mo_ta': 'Một nhịp đẩy ít nhất 4 ATR trong 6 giờ vừa kết thúc (đỉnh hoặc đáy đã được 3 nến xác nhận). Vào bằng lệnh chờ ở mức hồi 61,8% của nhịp đó, '
                     'dừng lỗ ngay sau điểm đầu nhịp, lệnh chờ sống 4 giờ. Đây chỉ là phần Fibonacci; việc đếm sóng Elliott không viết được thành quy tắc máy '
                     'nhất quán nên KHÔNG có ở đây.',
            'khong': 'Trong 4 giờ qua không có nhịp đẩy đủ lớn nào vừa kết thúc, hoặc giá đã hồi về mức 61,8% rồi.'},
    'ema_hoi': {'ten': 'Hồi về EMA theo xu hướng', 'ngan': 'Hồi về EMA', 'truong_phai': 'Theo xu hướng', 'kieu': 'nến M15 vừa đóng, vào theo giá thị trường',
                'mo_ta': 'EMA20 và EMA50 cùng chiều trên cả H1 và M15; nến M15 chạm EMA20 rồi đóng trở lại theo xu hướng. Dừng lỗ sau đáy (đỉnh) của nhịp hồi.',
                'khong': 'H1 và M15 chưa cùng chiều, hoặc nến M15 vừa đóng không chạm EMA20 rồi đóng trở lại theo xu hướng.'},
}
N_PHA = 32                # số nến M15 của quãng đỉnh/đáy bị phá (8 giờ)
THAN_ATR = 0.5            # thân nến phá vỡ ít nhất chừng này ATR
SL_PHA_ATR = 1.5
N_QUET = 20               # số nến M15 của quãng đáy/đỉnh bị quét (5 giờ)
QUET_TRONG = 7            # điểm quét phải nằm trong chừng này nến trước khi khoảng trống giá hình thành
FVG_ATR = 0.1             # khoảng trống giá rộng ít nhất chừng này ATR
# Hai công tắc chuẩn hóa theo sách; luật và cổng ghi trước khi đo ở cong-cu/CHUAN_HOA_DANG_KY.md, kết quả đo bằng cong-cu/chuan_hoa.py.
# Đo ngày 24/11/2026 trên vàng 2015–2026. Thay đổi 1 (FVG_NEN_GIUA) là sửa định nghĩa nên được BẬT: bỏ 102 tín hiệu ở mỗi phương pháp ICT,
# R trung bình mỗi lệnh gần như không đổi (ict −0,095 → −0,093; ict_fvg −0,151 → −0,150). Thay đổi 2 (ICT_HOP_LUU) KHÔNG qua cổng nên để TẮT:
# còn 284 và 577 lệnh trong 11 năm (nửa KIỂM 91 và 172, dưới mức 200), và R trung bình kém hơn (ict −0,217; ict_fvg −0,226).
FVG_NEN_GIUA = True       # True: khoảng trống giá chỉ tính khi nến giữa là nến đẩy cùng chiều (định nghĩa chuẩn của ICT)
ICT_HOP_LUU = False       # True: lệnh ICT đòi đủ các điều kiện hợp lưu: thuận xu hướng H1, cấu trúc M15 cùng chiều, giá vào ở nửa có lợi của biên độ 24 giờ
CHO_NEN = 16              # lệnh chờ của ICT sống chừng này nến M15 (4 giờ)
DEM_ATR = 0.1             # dừng lỗ lùi sau điểm quét
HOI_DEM_ATR = 0.3         # dừng lỗ lùi sau nhịp hồi
RUI_RO_ATR = (0.5, 3.0)   # khoảng dừng lỗ ngoài khoảng này thì bỏ tín hiệu
TP_R = 2.0                # chốt lời dùng khi chạy lại
GIU_PHUT = 1440           # giữ tối đa 24 giờ
PHI = 0.18                # hoa hồng và trượt giá mỗi lệnh (USD/oz), như bộ kiểm luật ba khung của dự án
TRE_PHUT = 5              # quá chừng này phút sau khi nến đóng thì tín hiệu vào theo giá thị trường không còn hiệu lực
N_VUNG = 48               # Wyckoff: số nến M15 của vùng đi ngang (12 giờ)
VUNG_ATR = (2.0, 8.0)     # Wyckoff: vùng đi ngang rộng trong khoảng này (tính theo ATR)
N_PA = 8                  # Price Action: mẫu nến phải nằm ở đáy/đỉnh của chừng này nến (2 giờ)
N_NHIP = 24               # Fibonacci: nhịp đẩy nằm trong chừng này nến (6 giờ)
NHIP_ATR = 4.0            # Fibonacci: nhịp đẩy dài ít nhất chừng này ATR
FIB = 0.618


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    hi, lo, pc = df['high'].astype(float), df['low'].astype(float), df['close'].astype(float).shift(1)
    return pd.concat([hi - lo, (hi - pc).abs(), (lo - pc).abs()], axis=1).max(axis=1).rolling(n).mean()


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.astype(float).ewm(span=n, adjust=False, min_periods=n).mean()


def _chieu_h1(h1: pd.DataFrame, dong: pd.DatetimeIndex) -> np.ndarray:
    """Chiều EMA20 so với EMA50 của nến H1 ĐÃ ĐÓNG gần nhất tại mỗi thời điểm trong `dong` (+1, −1 hoặc 0)."""
    d = np.sign(_ema(h1['close'], 20) - _ema(h1['close'], 50)).fillna(0.0)
    d.index = d.index + timedelta(hours=1)                         # thời điểm nến H1 đóng
    return d.reindex(dong, method='ffill').fillna(0.0).to_numpy()


def _khoang_trong(on, hn, ln, cn, an) -> tuple[np.ndarray, np.ndarray]:
    """(tăng, giảm) tại mỗi nến i, coi i là nến thứ ba: khoảng trống giá tăng khi đáy nến i cao hơn đỉnh nến i−2 ít nhất FVG_ATR lần ATR;
    giảm thì ngược lại. FVG_NEN_GIUA bật thì nến giữa (i−1) còn phải cùng chiều: đóng trên mở với khoảng trống tăng, đóng dưới mở với giảm."""
    with np.errstate(invalid='ignore'):
        len_ = (ln > np.roll(hn, 2)) & ((ln - np.roll(hn, 2)) >= FVG_ATR * an)
        xuong = (hn < np.roll(ln, 2)) & ((np.roll(ln, 2) - hn) >= FVG_ATR * an)
    if FVG_NEN_GIUA:
        len_ = len_ & (np.roll(cn, 1) > np.roll(on, 1))
        xuong = xuong & (np.roll(cn, 1) < np.roll(on, 1))
    return len_, xuong


def _pha_cau_truc(h, l, c) -> tuple[list[tuple], np.ndarray]:
    """Các lần phá cấu trúc trên một chuỗi nến: nến ĐÓNG vượt đỉnh (hoặc thủng đáy) gần nhất đã được xác nhận. Một đỉnh/đáy được xác nhận khi
    K_SWING nến mỗi bên không cao/thấp hơn nó, và chỉ dùng được sau khi đủ K_SWING nến phía sau đã đóng, nên không nhìn trước. Cùng chiều cấu
    trúc đang có là BOS, ngược chiều là CHoCH. Trả (danh sách (vị trí đỉnh/đáy bị phá, vị trí nến phá, mức giá, chiều +1/−1, loại), mảng chiều
    của lần phá gần nhất tính tới từng nến: +1, −1, hoặc 0 khi chưa có lần nào)."""
    n, sw = len(c), []
    for i in range(K_SWING, n - K_SWING):
        if h[i] >= h[i - K_SWING:i + K_SWING + 1].max():
            sw.append((i, 'H', h[i]))
        if l[i] <= l[i - K_SWING:i + K_SWING + 1].min():
            sw.append((i, 'L', l[i]))
    ds, chieu, xu, dinh, day, k = [], np.zeros(n), 0, None, None, 0
    for i in range(n):
        while k < len(sw) and sw[k][0] + K_SWING <= i:             # đỉnh/đáy chỉ dùng được sau khi đã đủ nến xác nhận
            if sw[k][1] == 'H':
                dinh = sw[k]
            else:
                day = sw[k]
            k += 1
        if dinh is not None and c[i] > dinh[2]:
            ds.append((dinh[0], i, dinh[2], 1, 'CHoCH' if xu < 0 else 'BOS'))
            xu, dinh = 1, None
        elif day is not None and c[i] < day[2]:
            ds.append((day[0], i, day[2], -1, 'CHoCH' if xu > 0 else 'BOS'))
            xu, day = -1, None
        chieu[i] = xu
    return ds, chieu


def quet(ma: str, m15: pd.DataFrame, h1: pd.DataFrame) -> list[dict]:
    """Mọi tín hiệu của phương pháp `ma` trên chuỗi nến M15 đã đóng (chỉ số là giờ mở nến), cũ trước mới sau. Mỗi tín hiệu:
    {'i': vị trí nến, 't': giờ nến đóng, 'huong', 'kieu': 'thi_truong' | 'gioi_han', 'vao', 'sl', 'atr', 'ly_do'}."""
    if ma not in DS:
        raise ValueError(f'phương pháp không có: {ma}')
    if len(m15) < 80:
        return []
    o, h, l, c = (m15[k].astype(float) for k in ('open', 'high', 'low', 'close'))
    A = _atr(m15)
    dong = m15.index + timedelta(minutes=15)
    on, hn, ln, cn, an = o.to_numpy(), h.to_numpy(), l.to_numpy(), c.to_numpy(), A.to_numpy()
    out: list[dict] = []

    def them(i, huong, kieu, vao, sl, ly_do, vung=None, mt=None, mt_ten='', song=None):
        rui = abs(vao - sl)
        if not np.isfinite(an[i]) or an[i] <= 0 or not (RUI_RO_ATR[0] * an[i] <= rui <= RUI_RO_ATR[1] * an[i]):
            return
        out.append({'i': int(i), 't': dong[i], 'huong': huong, 'kieu': kieu, 'vao': float(vao), 'sl': float(sl), 'atr': float(an[i]), 'ly_do': ly_do,
                    'vung': sorted(float(v) for v in vung) if vung is not None else None,
                    'muc_tieu': float(mt) if mt is not None and np.isfinite(mt) else None, 'muc_tieu_ten': mt_ten, 'song': song})

    hop_luu = None                                                  # hợp lưu ICT: chỉ dựng khi công tắc bật và phương pháp là ICT
    if ICT_HOP_LUU and ma in ('ict', 'ict_fvg'):
        xu_h1, xu_ct = _chieu_h1(h1, dong), _pha_cau_truc(hn, ln, cn)[1]
        can_bang = ((h.rolling(N_BIEN).max() + l.rolling(N_BIEN).min()) / 2).to_numpy()       # mức 50% của biên độ 24 giờ, tính tới nến đang xét

        def hop_luu(i, mua, vao):
            d = 1 if mua else -1
            return bool(xu_h1[i] * d > 0 and xu_ct[i] * d > 0 and ((vao < can_bang[i]) if mua else (vao > can_bang[i])))

    if ma == 'pha_vo':
        dinh, day = h.rolling(N_PHA).max().shift(1).to_numpy(), l.rolling(N_PHA).min().shift(1).to_numpy()
        than = np.abs(cn - on)
        with np.errstate(invalid='ignore'):
            len_ = (cn > dinh) & (than >= THAN_ATR * an)
            xuong = (cn < day) & (than >= THAN_ATR * an)
        for i in np.flatnonzero(len_ | xuong):
            if len_[i]:
                them(i, 'MUA', 'thi_truong', cn[i], cn[i] - SL_PHA_ATR * an[i], f'Nến M15 đóng vượt đỉnh 8 giờ {dinh[i]:.7g} với thân nến {than[i] / an[i]:.1f} ATR.',
                     mt=dinh[i] + (dinh[i] - day[i]), mt_ten='đo biên độ: chiều cao vùng 8 giờ tính từ đỉnh vừa bị phá')
            else:
                them(i, 'BAN', 'thi_truong', cn[i], cn[i] + SL_PHA_ATR * an[i], f'Nến M15 đóng thủng đáy 8 giờ {day[i]:.7g} với thân nến {than[i] / an[i]:.1f} ATR.',
                     mt=day[i] - (dinh[i] - day[i]), mt_ten='đo biên độ: chiều cao vùng 8 giờ tính từ đáy vừa bị phá')
    elif ma == 'ict':
        day_truoc, dinh_truoc = l.rolling(N_QUET).min().shift(1), h.rolling(N_QUET).max().shift(1)
        with np.errstate(invalid='ignore'):
            quet_day = ((l < day_truoc) & (c > day_truoc)).astype(float)          # quét đáy rồi đóng trở lại phía trên
            quet_dinh = ((h > dinh_truoc) & (c < dinh_truoc)).astype(float)
            co_qd = quet_day.rolling(QUET_TRONG).max().shift(2).to_numpy() > 0     # có điểm quét trong các nến i−8 … i−2
            co_qD = quet_dinh.rolling(QUET_TRONG).max().shift(2).to_numpy() > 0
            trong_len, trong_xuong = _khoang_trong(on, hn, ln, cn, an)      # khoảng trống giá tăng: đáy nến i trên đỉnh nến i−2
        day_quet, dinh_quet = l.rolling(QUET_TRONG + 2).min().to_numpy(), h.rolling(QUET_TRONG + 2).max().to_numpy()
        cao_q, thap_q = h.rolling(N_QUET).max().to_numpy(), l.rolling(N_QUET).min().to_numpy()      # thanh khoản đối diện: đỉnh/đáy 5 giờ tính tới nến tín hiệu
        for i in np.flatnonzero((trong_len & co_qd) | (trong_xuong & co_qD)):
            if i < N_QUET + QUET_TRONG + 2:
                continue
            mua_ = bool(trong_len[i] and co_qd[i])
            if hop_luu is not None and not hop_luu(i, mua_, (ln[i] + hn[i - 2]) / 2 if mua_ else (hn[i] + ln[i - 2]) / 2):
                continue
            if trong_len[i] and co_qd[i]:
                them(i, 'MUA', 'gioi_han', (ln[i] + hn[i - 2]) / 2, day_quet[i] - DEM_ATR * an[i],
                     f'Giá quét đáy 5 giờ rồi bật lên, để lại khoảng trống giá {hn[i - 2]:.7g}–{ln[i]:.7g}.', (hn[i - 2], ln[i]),
                     mt=cao_q[i], mt_ten='thanh khoản đối diện: đỉnh 5 giờ (BSL)')
            else:
                them(i, 'BAN', 'gioi_han', (hn[i] + ln[i - 2]) / 2, dinh_quet[i] + DEM_ATR * an[i],
                     f'Giá quét đỉnh 5 giờ rồi rơi xuống, để lại khoảng trống giá {hn[i]:.7g}–{ln[i - 2]:.7g}.', (hn[i], ln[i - 2]),
                     mt=thap_q[i], mt_ten='thanh khoản đối diện: đáy 5 giờ (SSL)')
    elif ma == 'ict_fvg':
        xu = _chieu_h1(h1, dong)
        day20, dinh20 = l.rolling(N_QUET).min().shift(3).to_numpy(), h.rolling(N_QUET).max().shift(3).to_numpy()     # đáy/đỉnh 5 giờ TRƯỚC nhịp bật ba nến
        with np.errstate(invalid='ignore'):
            trong_len, trong_xuong = _khoang_trong(on, hn, ln, cn, an)
            pha_len = (xu > 0) & trong_len & (np.maximum(cn, np.roll(cn, 1)) > dinh20)
            pha_xuong = (xu < 0) & trong_xuong & (np.minimum(cn, np.roll(cn, 1)) < day20)
        for i in np.flatnonzero(pha_len | pha_xuong):
            if i < N_QUET + 6:
                continue
            mua_ = bool(pha_len[i])
            if hop_luu is not None and not hop_luu(i, mua_, (ln[i] + hn[i - 2]) / 2 if mua_ else (hn[i] + ln[i - 2]) / 2):
                continue
            if pha_len[i]:
                them(i, 'MUA', 'gioi_han', (ln[i] + hn[i - 2]) / 2, min(ln[i - 2], ln[i - 1]) - DEM_ATR * an[i],
                     f'H1 đang tăng; nhịp bật đóng vượt đỉnh 5 giờ {dinh20[i]:.7g} và để lại khoảng trống giá {hn[i - 2]:.7g}–{ln[i]:.7g}.', (hn[i - 2], ln[i]),
                     mt=max(hn[i], hn[i - 1]), mt_ten='đỉnh của nhịp bật: mục tiêu đầu tiên khi xu hướng tiếp diễn')
            else:
                them(i, 'BAN', 'gioi_han', (hn[i] + ln[i - 2]) / 2, max(hn[i - 2], hn[i - 1]) + DEM_ATR * an[i],
                     f'H1 đang giảm; nhịp bật đóng thủng đáy 5 giờ {day20[i]:.7g} và để lại khoảng trống giá {hn[i]:.7g}–{ln[i - 2]:.7g}.', (hn[i], ln[i - 2]),
                     mt=min(ln[i], ln[i - 1]), mt_ten='đáy của nhịp bật: mục tiêu đầu tiên khi xu hướng tiếp diễn')
    elif ma == 'wyckoff':
        tren, duoi = h.rolling(N_VUNG).max().shift(1).to_numpy(), l.rolling(N_VUNG).min().shift(1).to_numpy()
        with np.errstate(invalid='ignore'):
            ngang = ((tren - duoi) >= VUNG_ATR[0] * an) & ((tren - duoi) <= VUNG_ATR[1] * an)
            spring = ngang & (ln < duoi - DEM_ATR * an) & (cn > duoi) & (cn > on)
            upthrust = ngang & (hn > tren + DEM_ATR * an) & (cn < tren) & (cn < on)
        for i in np.flatnonzero(spring | upthrust):
            if spring[i]:
                them(i, 'MUA', 'thi_truong', cn[i], ln[i] - 2 * DEM_ATR * an[i], f'Giá đi ngang 12 giờ trong {duoi[i]:.7g}–{tren[i]:.7g}; nến M15 đâm thủng biên dưới rồi đóng trở lại (spring).',
                     mt=tren[i], mt_ten='biên trên của vùng đi ngang 12 giờ')
            else:
                them(i, 'BAN', 'thi_truong', cn[i], hn[i] + 2 * DEM_ATR * an[i], f'Giá đi ngang 12 giờ trong {duoi[i]:.7g}–{tren[i]:.7g}; nến M15 đâm thủng biên trên rồi đóng trở lại (upthrust).',
                     mt=duoi[i], mt_ten='biên dưới của vùng đi ngang 12 giờ')
    elif ma == 'price_action':
        xu = _chieu_h1(h1, dong)
        than, bien = np.abs(cn - on), hn - ln
        o1, c1 = np.roll(on, 1), np.roll(cn, 1)
        day_moi, dinh_moi = ln <= l.rolling(N_PA).min().to_numpy(), hn >= h.rolling(N_PA).max().to_numpy()
        cao6, thap6 = h.rolling(N_NHIP).max().to_numpy(), l.rolling(N_NHIP).min().to_numpy()
        with np.errstate(invalid='ignore', divide='ignore'):
            pin_len = (bien >= 0.8 * an) & ((np.minimum(on, cn) - ln) >= 0.6 * bien) & (cn >= hn - bien / 3)
            pin_xuong = (bien >= 0.8 * an) & ((hn - np.maximum(on, cn)) >= 0.6 * bien) & (cn <= ln + bien / 3)
            nc_len = (cn > on) & (c1 < o1) & (cn >= o1) & (on <= c1) & (than >= 0.5 * an)
            nc_xuong = (cn < on) & (c1 > o1) & (cn <= o1) & (on >= c1) & (than >= 0.5 * an)
            len_ = (xu > 0) & day_moi & (pin_len | nc_len)
            xuong = (xu < 0) & dinh_moi & (pin_xuong | nc_xuong)
        for i in np.flatnonzero(len_ | xuong):
            if i < 60:
                continue
            if len_[i]:
                them(i, 'MUA', 'thi_truong', cn[i], ln[i] - 2 * DEM_ATR * an[i], f'H1 đang tăng; nến M15 tạo đáy 2 giờ rồi thành {"pin bar" if pin_len[i] else "nến nhấn chìm"} tăng.',
                     mt=cao6[i], mt_ten='kháng cự gần nhất: đỉnh 6 giờ')
            else:
                them(i, 'BAN', 'thi_truong', cn[i], hn[i] + 2 * DEM_ATR * an[i], f'H1 đang giảm; nến M15 tạo đỉnh 2 giờ rồi thành {"pin bar" if pin_xuong[i] else "nến nhấn chìm"} giảm.',
                     mt=thap6[i], mt_ten='hỗ trợ gần nhất: đáy 6 giờ')
    elif ma == 'fib':
        dinh3, day3 = h.shift(3).to_numpy(), l.shift(3).to_numpy()                 # đỉnh/đáy của nến cách đây 3 nến: đã có 3 nến bên phải xác nhận
        cao_nhip, thap_nhip = h.rolling(N_NHIP).max().shift(3).to_numpy(), l.rolling(N_NHIP).min().shift(3).to_numpy()
        with np.errstate(invalid='ignore'):
            xong_len = (dinh3 >= h.rolling(7).max().to_numpy()) & (dinh3 >= cao_nhip) & ((dinh3 - thap_nhip) >= NHIP_ATR * an)
            xong_xuong = (day3 <= l.rolling(7).min().to_numpy()) & (day3 <= thap_nhip) & ((cao_nhip - day3) >= NHIP_ATR * an)
        for i in np.flatnonzero(xong_len | xong_xuong):
            if i < N_NHIP + 6:
                continue
            if xong_len[i]:
                nhip = dinh3[i] - thap_nhip[i]
                them(i, 'MUA', 'gioi_han', dinh3[i] - FIB * nhip, thap_nhip[i] - DEM_ATR * an[i],
                     f'Nhịp tăng {thap_nhip[i]:.7g}–{dinh3[i]:.7g} vừa kết thúc; chờ mua ở mức hồi 61,8%.', (dinh3[i] - FIB * nhip, dinh3[i] - 0.5 * nhip),
                     mt=dinh3[i], mt_ten='đỉnh của nhịp đẩy (mức 0%)')
            else:
                nhip = cao_nhip[i] - day3[i]
                them(i, 'BAN', 'gioi_han', day3[i] + FIB * nhip, cao_nhip[i] + DEM_ATR * an[i],
                     f'Nhịp giảm {cao_nhip[i]:.7g}–{day3[i]:.7g} vừa kết thúc; chờ bán ở mức hồi 61,8%.', (day3[i] + 0.5 * nhip, day3[i] + FIB * nhip),
                     mt=day3[i], mt_ten='đáy của nhịp đẩy (mức 0%)')
    elif ma == 'elliott':
        piv = _zigzag(hn, ln, an)
        tg = m15.index.as_unit('ns').asi8 // 10 ** 9
        cur, j, da = [], 0, set()
        for i in range(len(hn)):
            while j < len(piv) and piv[j][3] <= i:                 # chỉ dùng đỉnh/đáy đã được xác nhận tính tới nến i
                cur.append(piv[j])
                j += 1
            if len(cur) < 3 or cur[-1][0] in da or not np.isfinite(an[i]):
                continue
            p0, p1, p2 = cur[-3:]
            huong, kq = _e_xet(p0, p1, p2, an[i])
            if huong is None:
                continue
            s1, hoi = kq
            mua = huong == 'MUA'
            if mua and (cn[i] <= p1[2] or ln[p2[0]:i + 1].min() < p2[2]):      # chưa đóng vượt cuối sóng 1, hoặc cuối sóng 2 đã bị thủng
                continue
            if not mua and (cn[i] >= p1[2] or hn[p2[0]:i + 1].max() > p2[2]):
                continue
            da.add(p2[0])
            d = 1 if mua else -1
            them(i, huong, 'thi_truong', cn[i], p2[2] - d * DEM_ATR * an[i],
                 f'Sóng 1 {"tăng" if mua else "giảm"} {p0[2]:.7g}–{p1[2]:.7g}, sóng 2 hồi {hoi * 100:.0f}% về {p2[2]:.7g}; nến M15 đóng '
                 f'{"vượt đỉnh" if mua else "thủng đáy"} sóng 1, xác nhận sóng 3.',
                 mt=p2[2] + d * E_MR * s1, mt_ten='sóng 3 bằng 1,618 lần sóng 1, tính từ cuối sóng 2',
                 song=[{'t': int(tg[q[0]]), 'gia': float(q[2]), 'nhan': str(k)} for k, q in enumerate((p0, p1, p2))])
    else:                                                          # ema_hoi
        e20, e50 = _ema(c, 20).to_numpy(), _ema(c, 50).to_numpy()
        xu = _chieu_h1(h1, dong)
        day2, dinh2 = np.minimum(ln, np.roll(ln, 1)), np.maximum(hn, np.roll(hn, 1))
        cao6, thap6 = h.rolling(N_NHIP).max().to_numpy(), l.rolling(N_NHIP).min().to_numpy()
        with np.errstate(invalid='ignore'):
            len_ = (xu > 0) & (e20 > e50) & (ln <= e20) & (cn > e20) & (cn > on)
            xuong = (xu < 0) & (e20 < e50) & (hn >= e20) & (cn < e20) & (cn < on)
        for i in np.flatnonzero(len_ | xuong):
            if i < 60:
                continue
            if len_[i]:
                them(i, 'MUA', 'thi_truong', cn[i], day2[i] - HOI_DEM_ATR * an[i], f'H1 và M15 đang tăng; nến M15 chạm EMA20 ({e20[i]:.7g}) rồi đóng tăng trở lại.',
                     mt=cao6[i], mt_ten='đỉnh 6 giờ gần nhất của xu hướng')
            else:
                them(i, 'BAN', 'thi_truong', cn[i], dinh2[i] + HOI_DEM_ATR * an[i], f'H1 và M15 đang giảm; nến M15 chạm EMA20 ({e20[i]:.7g}) rồi đóng giảm trở lại.',
                     mt=thap6[i], mt_ten='đáy 6 giờ gần nhất của xu hướng')
    return out


def cham(tin_hieu: list[dict], m1: pd.DataFrame, sp: float, phi: float = PHI, buoc: int = 1, he_so: float = 1.0,
         theo_muc_tieu: bool = False, tp_r: float | None = None) -> list[dict]:
    """Chấm từng tín hiệu bằng nến 1 phút (giá Bid; lệnh mua khớp và lệnh bán thoát theo Ask = Bid + `sp`). Mỗi lúc một lệnh.
    Vào theo giá thị trường: khớp ở giá mở nến 1 phút đầu tiên sau khi nến tín hiệu đóng. Lệnh chờ: khớp khi giá chạm mức chờ trong
    CHO_NEN nến, hủy nếu chạm dừng lỗ trước, và hủy khi tín hiệu kế tiếp trong danh sách đến mà lệnh chưa khớp (trang Biểu đồ cũng chỉ hiện
    tín hiệu mới nhất). Không có quy tắc hủy này thì phép chấm sẽ chọn lệnh nhờ biết trước lệnh chờ nào về sau sẽ khớp. Tín hiệu lệnh chờ mà giá
    (Bid) đã ở bên kia mức chờ ngay ở nến đầu tiên thì bỏ, như hien_tai() báo "tín hiệu đã qua". Thoát ở dừng lỗ, ở TP_R lần rủi ro, hoặc sau GIU_PHUT phút. Nến chạm cả hai thì tính dừng lỗ.
    Nến MỞ CỬA đã nằm ngoài dừng lỗ (nhảy giá sau cuối tuần, sau giờ nghỉ hằng ngày) thì thoát ở giá mở, tức lỗ hơn 1R, như lệnh dừng ngoài
    thực tế; mở cửa nhảy qua chốt lời thì vẫn chỉ tính ở mức chốt lời (không cộng phần nhảy có lợi).
    Trả [{'t', 'ra', 'huong', 'vao', 'usd', 'r', 'ket'}], usd là lãi lỗ mỗi lệnh ở 0,01 lot sau phí. Lệnh còn mở ở cuối dữ liệu thì không chấm.
    `buoc`: số phút của mỗi nến trong `m1` (mã khác vàng chấm bằng nến 5 phút). `he_so`: nhân chênh lệch giá để ra USD ở 0,01 lot
    (vàng là 1; mã khác lấy từ giá trị một bước giá của MT5). `theo_muc_tieu`: chốt lời ở mục tiêu lý thuyết của tín hiệu thay cho TP_R lần
    rủi ro; tín hiệu không có mục tiêu, hoặc mục tiêu nằm sai phía so với giá khớp, thì bỏ qua. `tp_r`: chốt lời ở chừng này lần rủi ro thay cho TP_R (dùng để đo cách chốt 1R)."""
    T = m1.index.as_unit('ns').asi8                                # ép về nano giây: bảng nến có thể lưu giờ theo giây hoặc micro giây
    O, H, L, C = (m1[k].to_numpy(dtype=float) for k in ('open', 'high', 'low', 'close'))
    n, phut, giu = len(T), 60 * 10 ** 9, max(1, GIU_PHUT // buoc)
    out, ban = [], None
    ds = sorted(tin_hieu, key=lambda s: s['t'])
    for so, s in enumerate(ds):
        t0 = pd.Timestamp(s['t']).value
        if ban is not None and t0 <= ban:
            continue
        j = int(np.searchsorted(T, t0, side='left'))
        if j >= n or T[j] - t0 > TRE_PHUT * phut:
            continue
        mua = s['huong'] == 'MUA'
        dau = 1.0 if mua else -1.0
        if s['kieu'] == 'thi_truong':
            vao, bat = (O[j] + sp if mua else O[j]), j
        else:
            if (O[j] <= s['vao']) if mua else (O[j] >= s['vao']):
                continue                                           # giá đã ở bên kia mức chờ lúc tín hiệu đến: trang Biểu đồ báo "tín hiệu đã qua"
            cuoi = min(n, int(np.searchsorted(T, t0 + CHO_NEN * 15 * phut, side='left')))
            if so + 1 < len(ds):                                   # tín hiệu kế tiếp đến: lệnh chờ này chưa khớp thì bị thay
                cuoi = min(cuoi, int(np.searchsorted(T, pd.Timestamp(ds[so + 1]['t']).value, side='left')))
            khop = (L[j:cuoi] + sp <= s['vao']) if mua else (H[j:cuoi] >= s['vao'])
            huy = (L[j:cuoi] <= s['sl']) if mua else (H[j:cuoi] + sp >= s['sl'])
            if not khop.any():
                continue
            k1 = int(np.argmax(khop))
            if huy.any() and int(np.argmax(huy)) < k1:
                continue                                           # chạm dừng lỗ trước khi kịp khớp: lệnh chờ bị hủy
            vao, bat = s['vao'], j + k1
        rui = (vao - s['sl']) * dau
        if rui <= 0:
            continue
        tp = vao + dau * (tp_r or TP_R) * rui
        if theo_muc_tieu:
            if s.get('muc_tieu') is None or (s['muc_tieu'] - vao) * dau <= 0:
                continue
            tp = s['muc_tieu']
        cuoi = min(n, bat + giu)
        if mua:
            cs, ct = L[bat:cuoi] <= s['sl'], H[bat:cuoi] >= tp
        else:
            cs, ct = H[bat:cuoi] + sp >= s['sl'], L[bat:cuoi] + sp <= tp
        if s['kieu'] != 'thi_truong' and len(ct):
            ct[0] = False                                          # nến khớp của lệnh chờ: chỉ xét phần đi ngược
        ks = int(np.argmax(cs)) if cs.any() else None
        kt = int(np.argmax(ct)) if ct.any() else None
        if ks is not None and (kt is None or ks <= kt):
            k, ra, ket = bat + ks, s['sl'], 'SL'
            if ks > 0:                                             # mở cửa đã nhảy qua dừng lỗ: khớp ở giá mở, không phải ở mức đã đặt
                ra = min(ra, O[k]) if mua else max(ra, O[k] + sp)
        elif kt is not None:
            k, ra, ket = bat + kt, tp, 'TP'
        elif bat + giu > n:
            break                                                  # lệnh còn mở tới hết dữ liệu: dừng, không chấm
        else:
            k = cuoi - 1
            ra, ket = (C[k] if mua else C[k] + sp), 'Hết giờ'
        usd = (ra - vao) * dau - phi
        out.append({'t': pd.Timestamp(T[bat], tz='UTC').isoformat(), 'ra': pd.Timestamp(T[k], tz='UTC').isoformat(), 'huong': s['huong'], 'vao': round(float(vao), 5),
                    'usd': round(float(usd * he_so), 2), 'r': round(float(usd / rui), 2), 'ket': ket})
        ban = T[k]
    return out


def hien_tai(ma: str, m15: pd.DataFrame, h1: pd.DataFrame, bid: float, ask: float, now: datetime) -> tuple[dict | None, str]:
    """Điểm vào của phương pháp `ma` ngay lúc này: (phương án, '') hoặc (None, lý do). Phương án: {'huong', 'vao', 'sl', 'tp': [1R, 2R],
    'vung': [thấp, cao] | None, 'ly_do', 'kieu', 'nen': giờ nến tín hiệu đóng, 'tre_phut', 'con_phut' (chỉ lệnh chờ)}."""
    m = m15.iloc[-400:]
    th = quet(ma, m, h1)
    n = len(m)
    if n < 80:
        return None, 'Chưa đủ nến M15 để xét.'
    if not DS[ma].get('cho'):
        s = next((x for x in reversed(th) if x['i'] == n - 1), None)
        if s is None:
            return None, DS[ma]['khong']
        mua = s['huong'] == 'MUA'
        vao = ask if mua else bid
        rui = (vao - s['sl']) * (1 if mua else -1)
        if not (RUI_RO_ATR[0] * 0.6 * s['atr'] <= rui <= RUI_RO_ATR[1] * 1.3 * s['atr']):
            return None, 'Có tín hiệu ở nến vừa đóng nhưng giá đã chạy xa: khoảng dừng lỗ tính từ giá hiện tại không còn hợp lý.'
        tre = max(0, int((now - s['t'].to_pydatetime()).total_seconds() // 60))
        return ({'huong': s['huong'], 'vao': vao, 'sl': s['sl'], 'tp': [vao + (1 if mua else -1) * k * rui for k in (1.0, TP_R)], 'vung': None,
                 'ly_do': s['ly_do'], 'kieu': DS[ma]['kieu'], 'nen': s['t'].isoformat(), 'tre_phut': tre, 'con_phut': None,
                 'muc_tieu': s.get('muc_tieu'), 'muc_tieu_ten': s.get('muc_tieu_ten', ''), 'song': s.get('song')}, '')
    s = next((x for x in reversed(th) if x['i'] >= n - CHO_NEN), None)
    if s is None:
        return None, DS[ma]['khong']
    mua, sau = s['huong'] == 'MUA', m.iloc[s['i'] + 1:]
    thap = min(float(sau['low'].min()), bid) if len(sau) else bid
    cao = max(float(sau['high'].max()), bid) if len(sau) else bid
    if (mua and thap <= s['sl']) or (not mua and cao >= s['sl']):
        return None, 'Tín hiệu gần nhất đã hỏng: giá đã chạm mức dừng lỗ trước khi khớp lệnh chờ.'
    if (mua and (thap <= s['vao'] or ask <= s['vao'])) or (not mua and cao >= s['vao']):
        return None, 'Tín hiệu gần nhất đã qua: giá đã quay về mức chờ rồi (lệnh chờ coi như đã khớp).'
    rui = abs(s['vao'] - s['sl'])
    con = CHO_NEN * 15 - int((now - s['t'].to_pydatetime()).total_seconds() // 60)
    if con <= 0:
        return None, 'Tín hiệu gần nhất đã quá 4 giờ mà giá chưa quay về mức chờ: lệnh chờ hết hạn.'
    d = 1 if mua else -1
    return ({'huong': s['huong'], 'vao': s['vao'], 'sl': s['sl'], 'tp': [s['vao'] + d * k * rui for k in (1.0, TP_R)], 'vung': s.get('vung'), 'ly_do': s['ly_do'],
             'kieu': DS[ma]['kieu'], 'nen': s['t'].isoformat(), 'tre_phut': 0, 'con_phut': con,
             'muc_tieu': s.get('muc_tieu'), 'muc_tieu_ten': s.get('muc_tieu_ten', ''), 'song': s.get('song')}, '')


def phuong_an(ma: str, m15: pd.DataFrame, h1: pd.DataFrame, bid: float, ask: float, now: datetime, chung: list, so_le: int = 2) -> dict:
    """Phương án của phương pháp `ma` cho bảng phân tích, cùng dạng với phương án của các luật. `chung`: các lý do khiến MỌI phương án
    lúc này chỉ còn để tham khảo (giá cũ, đang né tin)."""
    tt = DS[ma]
    r = lambda x: round(float(x), so_le)                           # noqa: E731
    pa, vi = hien_tai(ma, m15, h1, bid, ask, now)
    if pa is None:
        cho = elliott_cho(m15, so_le) if ma == 'elliott' else None      # đếm sóng đang hình thành, để vẽ và để nói rõ đang chờ gì
        vi = cho['chu'] if cho else vi
        return {'cho': cho, 'ma': ma, 'ten': tt['ten'], 'ten_ngan': tt['ngan'], 'chip': tt.get('chip', ma), 'truong_phai': tt['truong_phai'], 'kieu': tt['kieu'], 'co': False, 'vi_sao': vi, 'thong_ke': tt['mo_ta'],
                'nhom': 'pp', 'hieu_luc': False, 'vi_sao_het': []}
    ly = list(chung)
    if pa['con_phut'] is None and pa['tre_phut'] > TRE_PHUT:
        ly.append(f'Nến tín hiệu đã đóng {pa["tre_phut"]} phút trước; phương pháp này vào ngay sau khi nến đóng.')
    ghi = ['TP1 ở 1R để tham khảo; phần chạy lại bên dưới chốt toàn bộ ở 2R.']
    mt, rui, dau = None, abs(pa['vao'] - pa['sl']), (1 if pa['huong'] == 'MUA' else -1)
    if pa.get('muc_tieu') is not None and rui > 0 and (pa['muc_tieu'] - pa['vao']) * dau > 0:      # chỉ nhận mục tiêu nằm về phía có lãi
        mt = {'gia': r(pa['muc_tieu']), 'ten': pa.get('muc_tieu_ten', ''), 'r': round((pa['muc_tieu'] - pa['vao']) * dau / rui, 2)}
        ghi.append(f'Mục tiêu theo lý thuyết của phương pháp: {mt["ten"]}, cách điểm vào {str(mt["r"]).replace(".", ",")}R. Số đo khi chốt ở mức này nằm trong phần bằng chứng.')
    if pa['con_phut'] is not None:
        ghi.append(f'Lệnh chờ còn hiệu lực khoảng {pa["con_phut"]} phút; hủy nếu giá chạm dừng lỗ trước khi về mức chờ.')
    return {'ma': ma, 'ten': tt['ten'], 'ten_ngan': tt['ngan'], 'chip': tt.get('chip', ma), 'truong_phai': tt['truong_phai'], 'kieu': pa['kieu'], 'co': True, 'huong': pa['huong'], 'vao': r(pa['vao']), 'sl': r(pa['sl']), 'tp': [r(t) for t in pa['tp']],
            'vung': [r(v) for v in pa['vung']] if pa['vung'] else None, 'rui_ro_gia': r(abs(pa['vao'] - pa['sl'])), 'rr': [1.0, TP_R], 'ly_do': re.sub(r'(\d)\.(\d)', r'\1,\2', pa['ly_do']),
            'thong_ke': tt['mo_ta'], 'ghi_chu': ghi, 'nhom': 'pp', 'hieu_luc': not ly, 'vi_sao_het': ly, 'muc_tieu': mt, 'nen': pa.get('nen'), 'con_phut': pa.get('con_phut'),
            'song': [{'t': q['t'], 'gia': r(q['gia']), 'nhan': q['nhan']} for q in pa['song']] if pa.get('song') else None}


K_SWING = 3               # một đỉnh/đáy được xác nhận khi có chừng này nến hai bên thấp/cao hơn nó
N_BIEN = 96               # biên độ giao dịch để chia premium/discount: 24 giờ
_DAU_VN = str.maketrans(',.', '.,')   # 3,547.17 thành 3.547,17
ZZ_ATR = 2.0              # zigzag: giá đảo chiều ít nhất chừng này ATR thì đỉnh/đáy trước đó được xác nhận
E_S1_ATR = 3.0            # Elliott: sóng 1 dài ít nhất chừng này ATR
E_HOI = (0.382, 0.786)    # Elliott: sóng 2 hồi trong khoảng này của sóng 1
E_MR = 1.618              # Elliott: mục tiêu sóng 3 bằng chừng này lần sóng 1


def _zigzag(hn, ln, an) -> list[tuple]:
    """Đỉnh và đáy theo zigzag nhân quả: [(vị trí nến, 'H' | 'L', giá, vị trí nến xác nhận)]. Một đỉnh được xác nhận khi giá đã rơi ít nhất
    ZZ_ATR lần ATR từ nó (đáy thì ngược lại), nên tại nến i chỉ được dùng những điểm có vị trí xác nhận ≤ i."""
    piv, n = [], len(hn)
    k0 = next((i for i in range(n) if an[i] > 0), None)
    if k0 is None:
        return piv
    huong, hi, hi_i, lo, lo_i = 0, hn[k0], k0, ln[k0], k0
    for i in range(k0 + 1, n):
        a = an[i]
        if not a > 0:
            continue
        if huong >= 0 and hn[i] > hi:
            hi, hi_i = hn[i], i
        if huong <= 0 and ln[i] < lo:
            lo, lo_i = ln[i], i
        if huong >= 0 and i > hi_i and hi - ln[i] >= ZZ_ATR * a:
            piv.append((hi_i, 'H', float(hi), i))
            huong = -1
            k = hi_i + 1 + int(np.argmin(ln[hi_i + 1:i + 1]))
            lo, lo_i = ln[k], k
        elif huong <= 0 and i > lo_i and hn[i] - lo >= ZZ_ATR * a:
            piv.append((lo_i, 'L', float(lo), i))
            huong = 1
            k = lo_i + 1 + int(np.argmax(hn[lo_i + 1:i + 1]))
            hi, hi_i = hn[k], k
    return piv


def _e_xet(p0, p1, p2, a: float):
    """Ba điểm xoay liên tiếp có phải một cặp sóng 1–2 hợp lệ không: ('MUA' | 'BAN', (độ dài sóng 1, tỷ lệ hồi)) hoặc (None, lý do)."""
    len_ = p2[1] == 'L'
    s1 = (p1[2] - p0[2]) if len_ else (p0[2] - p1[2])
    if s1 <= 0:
        return None, 'ba điểm xoay gần nhất không tạo thành một nhịp đẩy'
    hoi = abs(p1[2] - p2[2]) / s1
    if s1 < E_S1_ATR * a:
        return None, f'sóng 1 chỉ dài {s1 / a:.1f} ATR, ngắn hơn mức tối thiểu {E_S1_ATR:g} ATR'.replace('.', ',')
    if hoi >= 1:
        return None, 'sóng 2 đã hồi quá điểm bắt đầu của sóng 1, phạm quy tắc Elliott'
    if not E_HOI[0] <= hoi <= E_HOI[1]:
        return None, f'sóng 2 hồi {hoi * 100:.0f}% của sóng 1, ngoài khoảng 38,2–78,6%'
    return ('MUA' if len_ else 'BAN'), (s1, hoi)


def elliott_cho(m15: pd.DataFrame, so_le: int = 2) -> dict:
    """Cách đếm sóng Elliott đang hình thành khi CHƯA có điểm vào: {'chu': lời mô tả, 'song': các điểm để vẽ, và khi cặp sóng 1–2 đã đủ thì thêm
    'huong', 'kich_hoat' (mức nến phải đóng vượt), 'sl', 'muc_tieu'}. Chỉ mô tả cấu trúc; không phải tín hiệu."""
    m = m15.iloc[-400:]
    if len(m) < 80:
        return {'chu': 'Chưa đủ nến M15 để đếm sóng.', 'song': []}
    hn, ln, cn = (m[k].to_numpy(dtype=float) for k in ('high', 'low', 'close'))
    an = _atr(m).to_numpy()
    tg = m.index.as_unit('ns').asi8 // 10 ** 9
    piv, a = _zigzag(hn, ln, an), float(an[-1])
    r = lambda x: round(float(x), so_le)                           # noqa: E731
    chu = lambda x: f'{float(x):,.{so_le}f}'.translate(_DAU_VN)    # noqa: E731
    diem = lambda q, k: {'t': int(tg[q[0]]), 'gia': r(q[2]), 'nhan': k}      # noqa: E731
    if len(piv) < 2 or not a > 0:
        return {'chu': 'Chưa có đủ đỉnh và đáy được xác nhận để đếm sóng (mỗi lần đảo chiều phải từ 2 ATR).', 'song': []}
    ly = 'chưa đủ ba điểm xoay'
    if len(piv) >= 3:
        p0, p1, p2 = piv[-3:]
        huong, kq = _e_xet(p0, p1, p2, a)
        if huong:
            mua, (s1, hoi) = huong == 'MUA', kq
            hong = (ln[p2[0]:].min() < p2[2]) if mua else (hn[p2[0]:].max() > p2[2])
            qua = bool((cn[p2[3]:] > p1[2]).any()) if mua else bool((cn[p2[3]:] < p1[2]).any())
            if not hong and not qua:
                d = 1 if mua else -1
                return {'huong': huong, 'song': [diem(p0, '0'), diem(p1, '1'), diem(p2, '2')], 'kich_hoat': r(p1[2]), 'sl': r(p2[2] - d * DEM_ATR * a),
                        'muc_tieu': r(p2[2] + d * E_MR * s1),
                        'chu': f'Sóng 1 {"tăng" if mua else "giảm"} {chu(p0[2])} – {chu(p1[2])}; sóng 2 hồi {hoi * 100:.0f}% về {chu(p2[2])} và đã được xác nhận. '
                               f'Chờ nến M15 đóng {"trên" if mua else "dưới"} {chu(p1[2])} để vào sóng 3: dừng lỗ {chu(p2[2] - d * DEM_ATR * a)}, '
                               f'mục tiêu sóng 3 {chu(p2[2] + d * E_MR * s1)}.'}
            ly = 'giá đã đi qua cuối sóng 2, cách đếm này hỏng' if hong else 'nến M15 đã đóng vượt cuối sóng 1 trước đó (tín hiệu đã qua)'
        else:
            ly = kq
    p0, p1 = piv[-2:]                                             # sóng 2 có thể đang hình thành sau một nhịp đẩy vừa xong
    s1, len_ = abs(p1[2] - p0[2]), p1[1] == 'H'
    if s1 >= E_S1_ATR * a:
        hoi = abs(p1[2] - (ln[p1[0]:].min() if len_ else hn[p1[0]:].max())) / s1
        if hoi < 1:
            return {'huong': 'MUA' if len_ else 'BAN', 'song': [diem(p0, '0'), diem(p1, '1')],
                    'chu': f'Sóng 1 {"tăng" if len_ else "giảm"} {chu(p0[2])} – {chu(p1[2])} ({f"{s1 / a:.1f}".replace(".", ",")} ATR) đã xong; sóng 2 đang hồi {hoi * 100:.0f}%. '
                           + f'Cần sóng 2 hồi 38,2–78,6%, được xác nhận (giá đảo chiều ít nhất 2 ATR), rồi nến M15 đóng {"trên" if len_ else "dưới"} {chu(p1[2])}.'}
    return {'chu': f'Chưa có cặp sóng 1–2 hợp lệ: {ly}.', 'song': [diem(q, '') for q in piv[-3:]]}


def ban_do_ict(m15: pd.DataFrame, h1: pd.DataFrame, bid: float, now: datetime, so_le: int = 2) -> dict:
    """Bản đồ ICT/SMC của 300 nến M15 gần nhất, để vẽ lên biểu đồ và để người xem tự thấy điều kiện nào đã có, điều kiện nào còn thiếu:
    thanh khoản phía trên/dưới, đỉnh đáy hôm trước, khoảng trống giá chưa lấp, các lần phá cấu trúc (BOS, CHoCH), các lần quét thanh khoản,
    mức 50% của biên độ 24 giờ (premium/discount), bảng điều kiện và kịch bản chờ. Chỉ mô tả cấu trúc giá; không phải tín hiệu."""
    m = m15.iloc[-300:]
    n = len(m)
    r = lambda x: round(float(x), so_le)                           # noqa: E731
    if n < 120:
        return {'du': False}
    o, h, l, c = (m[k].to_numpy(dtype=float) for k in ('open', 'high', 'low', 'close'))
    A = _atr(m).to_numpy()
    T = [int(t.timestamp()) for t in m.index]
    # --- phá cấu trúc: nến ĐÓNG vượt đỉnh (hoặc thủng đáy) gần nhất đã xác nhận. Cùng chiều cấu trúc đang có là BOS, ngược chiều là CHoCH.
    ct = [{'t0': T[a_], 't': T[b_], 'gia': r(muc), 'huong': 'tang' if d_ > 0 else 'giam', 'loai': loai} for a_, b_, muc, d_, loai in _pha_cau_truc(h, l, c)[0]]
    # --- khoảng trống giá chưa bị lấp hết
    fvg = []
    for i in range(2, n):
        if not np.isfinite(A[i]):
            continue
        if l[i] > h[i - 2] and l[i] - h[i - 2] >= FVG_ATR * A[i] and (not FVG_NEN_GIUA or c[i - 1] > o[i - 1]):
            sau = l[i + 1:].min() if i + 1 < n else np.inf
            if sau > h[i - 2]:                                     # giá chưa quay về lấp hết
                fvg.append({'t': T[i - 2], 'duoi': r(h[i - 2]), 'tren': r(l[i]), 'huong': 'tang', 'da_cham': bool(sau <= l[i])})
        elif h[i] < l[i - 2] and l[i - 2] - h[i] >= FVG_ATR * A[i] and (not FVG_NEN_GIUA or c[i - 1] < o[i - 1]):
            sau = h[i + 1:].max() if i + 1 < n else -np.inf
            if sau < l[i - 2]:
                fvg.append({'t': T[i - 2], 'duoi': r(h[i]), 'tren': r(l[i - 2]), 'huong': 'giam', 'da_cham': bool(sau >= h[i])})
    fvg = sorted(fvg, key=lambda z: abs((z['duoi'] + z['tren']) / 2 - bid))[:6]
    # --- các lần quét thanh khoản gần đây (cùng định nghĩa với phương pháp ict)
    hs, ls = pd.Series(h), pd.Series(l)
    dt, dd = hs.rolling(N_QUET).max().shift(1).to_numpy(), ls.rolling(N_QUET).min().shift(1).to_numpy()
    quet_ds = []
    for i in range(max(N_QUET + 1, n - 48), n):
        if l[i] < dd[i] and c[i] > dd[i]:
            quet_ds.append({'t': T[i], 'gia': r(l[i]), 'loai': 'day'})
        if h[i] > dt[i] and c[i] < dt[i]:
            quet_ds.append({'t': T[i], 'gia': r(h[i]), 'loai': 'dinh'})
    # --- thanh khoản, đỉnh đáy hôm trước, premium/discount
    bsl, ssl = float(h[-N_QUET:].max()), float(l[-N_QUET:].min())
    ngay = m.index.normalize()
    cac_ngay = ngay.unique()
    truoc = m[ngay == cac_ngay[-2]] if len(cac_ngay) >= 2 else None
    cao, thap = float(h[-N_BIEN:].max()), float(l[-N_BIEN:].min())
    cb = (cao + thap) / 2
    vi_tri = 'premium' if bid > cb else 'discount'
    xu_h1 = int(_chieu_h1(h1, m.index[-1:] + timedelta(minutes=15))[0])
    # --- bảng điều kiện. Chiều đang xét: chiều của điểm vào nếu đã có, không thì chiều xu hướng H1.
    chu = lambda x: f'{float(x):,.{so_le}f}'.translate(_DAU_VN)    # noqa: E731
    pa, _ = hien_tai('ict', m15, h1, bid, bid, now)
    pb, _ = hien_tai('ict_fvg', m15, h1, bid, bid, now)
    ke = pa or pb
    huong = ke['huong'] if ke else 'BAN' if xu_h1 < 0 else 'MUA' if xu_h1 > 0 else None
    ban = huong == 'BAN'
    ten_h = 'BÁN' if ban else 'MUA'
    gan = [q for q in quet_ds if q['t'] >= T[-QUET_TRONG - 2]]
    # điểm vào của mô hình quét thanh khoản sống tới 4 giờ, nên lần quét sinh ra nó có thể đã nằm ngoài 9 nến gần nhất
    quet_dung = [q for q in (quet_ds if pa else gan) if q['loai'] == ('dinh' if ban else 'day')] if huong else gan
    thuan = bool(huong) and xu_h1 != 0 and (xu_h1 < 0) == ban
    dk = [{'ten': 'Thuận xu hướng H1 (EMA20 so với EMA50)', 'dat': thuan,
           'chi_tiet': 'H1 chưa rõ xu hướng' if not xu_h1 else f'H1 đang {"giảm" if xu_h1 < 0 else "tăng"}' + ('' if thuan else f'; điểm vào {ten_h} đi ngược khung lớn')},
          {'ten': 'Cấu trúc M15 gần nhất cùng chiều', 'dat': (bool(ct) and (ct[-1]['huong'] == 'giam') == ban) if huong else None,
           'chi_tiet': (f'{ct[-1]["loai"]} {"giảm" if ct[-1]["huong"] == "giam" else "tăng"} tại {chu(ct[-1]["gia"])}' if ct else 'chưa có lần phá cấu trúc nào')},
          {'ten': 'Giá ở nửa có lợi của biên độ 24 giờ', 'dat': ((vi_tri == 'premium') == ban) if huong else None,
           'chi_tiet': f'đang ở {vi_tri}, mức 50% là {chu(cb)}; bán nên ở premium (nửa trên), mua nên ở discount (nửa dưới)'},
          {'ten': 'Quét thanh khoản rồi đóng ngược lại', 'dat': bool(quet_dung) or pa is not None,
           'chi_tiet': (f'đã quét {"đỉnh" if quet_dung[-1]["loai"] == "dinh" else "đáy"} tại {chu(quet_dung[-1]["gia"])}' if quet_dung else
                        'đã quét trước nhịp tạo khoảng trống giá' if pa else
                        f'chưa quét {"đỉnh" if ban else "đáy"} 5 giờ ({chu(bsl) if ban else chu(ssl)}) trong {QUET_TRONG + 2} nến M15 gần nhất' if huong else
                        f'chưa có lần quét nào trong {QUET_TRONG + 2} nến M15 gần nhất')},
          {'ten': 'Khoảng trống giá và điểm vào còn sống', 'dat': ke is not None,
           'chi_tiet': (f'có: {"quét thanh khoản" if pa else "phá cấu trúc"} rồi để lại khoảng trống giá, lệnh chờ {ten_h} tại {chu(ke["vao"])}' if ke else 'chưa có')}]
    cho = []
    if xu_h1:
        xb = xu_h1 < 0
        cho.append(f'Kịch bản {"BÁN" if xb else "MUA"} thuận xu hướng H1: chờ giá {"hồi lên quét đỉnh 5 giờ" if xb else "rơi xuống quét đáy 5 giờ"} '
                   f'{chu(bsl) if xb else chu(ssl)} rồi đóng {"trở lại bên dưới" if xb else "trở lại bên trên"} và để lại một khoảng trống giá '
                   f'{"giảm" if xb else "tăng"}. Khi đủ, trang ra lệnh chờ ở giữa khoảng trống đó, dừng lỗ ngay sau điểm quét.')
        cung = [z for z in fvg if z['huong'] == ('giam' if xb else 'tang') and ((z['duoi'] > bid) if xb else (z['tren'] < bid))]
        if cung:
            z = min(cung, key=lambda z: abs((z['duoi'] + z['tren']) / 2 - bid))
            cho.append(f'Vùng đáng theo dõi: khoảng trống giá {"giảm" if xb else "tăng"} chưa lấp {chu(z["duoi"])} – {chu(z["tren"])} '
                       f'({"phía trên" if xb else "phía dưới"} giá). Sách ICT coi đây là chỗ giá hay hồi về; trang chưa đo riêng kiểu vào lệnh ở vùng cũ.')
        cho.append(f'Kịch bản ngược xu hướng H1 ({"MUA" if xb else "BÁN"}): chỉ xét khi giá quét {"đáy" if xb else "đỉnh"} 5 giờ {chu(ssl) if xb else chu(bsl)} '
                   'rồi đảo chiều để lại khoảng trống giá; rủi ro cao hơn vì đi ngược khung lớn.')
    else:
        cho.append('H1 chưa có xu hướng rõ: ICT khuyên đứng ngoài cho tới khi một phía thanh khoản bị quét và cấu trúc đổi chiều.')
    return {'du': True, 'xu_h1': xu_h1, 'huong_xet': huong, 'bsl': r(bsl), 'ssl': r(ssl), 't_tk': T[-N_QUET], 't_bien': T[-N_BIEN],
            'dinh_hom_truoc': r(truoc['high'].max()) if truoc is not None and len(truoc) else None,
            'day_hom_truoc': r(truoc['low'].min()) if truoc is not None and len(truoc) else None, 'can_bang': r(cb), 'bien': [r(thap), r(cao)], 'vi_tri': vi_tri,
            'fvg': fvg, 'cau_truc': ct[-6:], 'quet': quet_ds[-6:], 'dieu_kien': dk, 'kich_ban': cho, 'co_lenh': ke is not None,
            'ghi_chu': 'Hai mô hình vào lệnh đã đo: "quét thanh khoản rồi khoảng trống giá" chỉ cần điều kiện 4 và 5; "hồi về khoảng trống giá sau khi phá cấu trúc" '
                       'cần điều kiện 1 và 5. Điều kiện 2 và 3 là phần hợp lưu theo sách ICT, chưa được đo riêng.'}
