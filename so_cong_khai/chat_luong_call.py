"""Điều kiện dữ liệu và mức giá để một phương án được tự ghi thành tín hiệu.

Không đưa ra xác suất thắng và không tối ưu TP/SL. Các điều kiện giá trực tiếp,
độ mới 60 giây và spread tối đa 5% SL theo cùng giới hạn của bot riêng.
"""
from __future__ import annotations

import math
from datetime import datetime

PHIEN_BAN = 1
TOI_DA_CU_GIAY = 60
TOI_DA_SPREAD_R = 0.05


def kiem(pa: dict, fr: dict, now: datetime) -> list[str]:
    ly = []
    if fr.get('nguon') != 'mt5':
        ly.append('Chỉ tự gọi lệnh khi có giá MT5 trực tiếp; kho nến dùng để tham khảo.')
    try:
        bid, ask = float(fr['bid']), float(fr['ask'])
        if not (math.isfinite(bid) and math.isfinite(ask) and 0 < bid <= ask):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return ly + ['Báo giá Bid/Ask thiếu hoặc không hợp lệ.']
    try:
        age = (now - fr['het']).total_seconds()
        if not math.isfinite(age) or age > TOI_DA_CU_GIAY:
            ly.append('Báo giá trực tiếp đã cũ quá 60 giây; chờ giá mới.')
        elif age < -5:
            ly.append('Giờ báo giá ở tương lai quá 5 giây; cần đồng bộ đồng hồ.')
    except (KeyError, TypeError, AttributeError):
        ly.append('Không xác định được độ mới của báo giá.')
    try:
        side = {'MUA': 1, 'BAN': -1}[pa['huong']]
        entry, sl = float(pa['vao']), float(pa['sl'])
        tps = [float(t) for t in pa['tp']]
        risk = (entry - sl) * side
        if not all(math.isfinite(v) and v > 0 for v in [entry, sl, *tps]) or risk <= 0 or not tps:
            raise ValueError
        if any((t - entry) * side <= 0 for t in tps):
            raise ValueError
        if ask - bid > TOI_DA_SPREAD_R * risk:
            ly.append('Spread lớn hơn 5% khoảng dừng lỗ; chờ spread hẹp lại.')
    except (KeyError, TypeError, ValueError):
        ly.append('Chiều lệnh hoặc thứ tự giá vào, SL, TP không hợp lệ.')
    return ly
