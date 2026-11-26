"""Sửa nhãn giờ của nến vàng nhiều năm (tệp xuất MT5 `XAUUSDp_M1.csv` của EA Promax) về đúng giờ UTC, lúc nạp; tệp gốc không bị sửa.

Phát hiện ngày 25/11/2026 (đo bằng hai cách độc lập: phút giá giật mạnh nhất quanh hàng trăm tin Mỹ ra lúc 8:30 giờ New York và quyết định lãi suất
của Fed, so với giờ ra tin trong lịch; và hình dạng biến động theo phút trong ngày của từng tuần so với quãng đã đúng giờ):
- tới hết tuần 11/02/2024: nhãn giờ SỚM hơn giờ thật 1 giờ khi châu Âu đang ở giờ mùa đông (từ Chủ nhật cuối tháng 10 tới Chủ nhật cuối tháng 3),
  đúng khi châu Âu ở giờ mùa hè. Tức là nguồn đã lấy giờ máy chủ của sàn (UTC+2 mùa đông, UTC+3 mùa hè theo lịch châu Âu) trừ đi 3 giờ cố định;
- từ tuần 18/02/2024 tới hết tuần 19/05/2024: nhãn giờ TRỄ hơn giờ thật 1 giờ;
- từ tuần 20/05/2024: đúng.
Cả ba ranh giới rơi vào cuối tuần (thị trường đóng cửa), nên sửa không làm chồng hay mất nến. Giá không đổi; chỉ nhãn giờ đổi.
Hệ quả trước khi sửa: các phần dựa vào giờ trong ngày (né tin, bộ lọc tin, khung giờ hoạt động của luật, phiên, nến H1/H4 cắt theo giờ) đã được kiểm
thử lệch 1 giờ trong các mùa đông 2015–2024 và trong quãng 02–05/2024."""
from __future__ import annotations

import pandas as pd

MOC_A = pd.Timestamp('2024-02-18', tz='UTC')        # hết đoạn "sớm 1 giờ vào mùa đông châu Âu"
MOC_B = pd.Timestamp('2024-05-20', tz='UTC')        # hết đoạn "trễ 1 giờ"
PHIEN_BAN = 1


def _chu_nhat_cuoi(nam: int, thang: int) -> pd.Timestamp:
    cuoi = pd.Timestamp(year=nam, month=thang, day=31 if thang in (3, 10) else 30, tz='UTC')
    return cuoi - pd.Timedelta(days=(cuoi.day_of_week + 1) % 7)


def mua_he_chau_au(t: pd.DatetimeIndex) -> pd.Series:
    """True nếu châu Âu đang ở giờ mùa hè (từ 01:00 UTC Chủ nhật cuối tháng 3 tới 01:00 UTC Chủ nhật cuối tháng 10)."""
    nam = sorted(set(t.year))
    bd = {y: _chu_nhat_cuoi(y, 3) + pd.Timedelta(hours=1) for y in nam}
    kt = {y: _chu_nhat_cuoi(y, 10) + pd.Timedelta(hours=1) for y in nam}
    y = t.year
    return pd.Series((t >= pd.DatetimeIndex([bd[v] for v in y])) & (t < pd.DatetimeIndex([kt[v] for v in y])), index=t)


def gio_that(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Nhãn giờ đúng UTC cho chỉ số nến (UTC) của tệp vàng nhiều năm."""
    if not len(idx):
        return idx
    lech = pd.Series(0, index=idx, dtype='int64')
    a = idx < MOC_A
    if a.any():
        dong = ~mua_he_chau_au(idx[a]).to_numpy()
        v = lech.to_numpy().copy()
        v[a.nonzero()[0][dong]] = 1                                          # sớm 1 giờ: cộng 1 giờ
        lech = pd.Series(v, index=idx)
    b = (idx >= MOC_A) & (idx < MOC_B)
    if b.any():
        v = lech.to_numpy().copy()
        v[b] = -1                                                            # trễ 1 giờ: trừ 1 giờ
        lech = pd.Series(v, index=idx)
    return idx + pd.to_timedelta(lech.to_numpy(), unit='h')
