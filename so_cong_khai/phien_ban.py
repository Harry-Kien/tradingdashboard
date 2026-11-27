"""Số phiên bản của app và cách so sánh. Không nhập mô-đun nào khác của gói (để ai cũng nhập được, không vòng).

Chỉ nhận dạng ba số cách nhau bằng dấu chấm (1.0.10); mọi chuỗi khác (1.0, v2.0.0, 1.0.0-beta) coi như không so được nên không bao giờ
được xem là "mới hơn", để một kê khai lạ không kéo người dùng tới bản cài không rõ nguồn gốc."""
from __future__ import annotations

import re

PHIEN_BAN = '1.0.0'

_DANG = re.compile(r'(\d+)\.(\d+)\.(\d+)')


def hop_le(s: str) -> bool:
    """Đúng dạng ba số \\d+.\\d+.\\d+ (cả chuỗi, không thừa ký tự)."""
    return isinstance(s, str) and _DANG.fullmatch(s) is not None


def moi_hon(a: str, b: str) -> bool:
    """`a` lớn hơn `b` khi so từng số (1.0.10 > 1.0.9, không so chuỗi). Chuỗi sai dạng thì False."""
    if not hop_le(a) or not hop_le(b):
        return False
    return tuple(map(int, a.split('.'))) > tuple(map(int, b.split('.')))
