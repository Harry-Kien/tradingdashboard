"""Kiểm Host/Origin và đọc JSON có giới hạn cho máy chủ cục bộ."""
from __future__ import annotations

import json
import math
import re
from urllib.parse import urlsplit

HAN_DOC = 10  # giây: không để yêu cầu thiếu thân giữ luồng vô hạn


class YeuCauLoi(ValueError):
    def __init__(self, ma: int, ly_do: str):
        super().__init__(ly_do)
        self.ma = ma


def host_hop_le(headers, port: int) -> bool:
    hs = headers.get_all('Host', [])
    if len(hs) != 1:
        return False
    h = hs[0].lower()
    if not re.fullmatch(r'(127\.0\.0\.1|localhost|\[::1\])(?::[0-9]{1,5})?', h):
        return False
    try:
        return urlsplit('http://' + h).port in (None, port)
    except ValueError:
        return False


def cung_nguon(headers, port: int) -> bool:
    if headers.get_all('X-So-Cong-Khai', []) != ['1'] or not host_hop_le(headers, port):
        return False
    if headers.get('Sec-Fetch-Site') == 'cross-site':
        return False
    origins = headers.get_all('Origin', [])
    if not origins:  # công cụ cục bộ không gửi Origin; trình duyệt vẫn cần tiêu đề riêng
        return True
    if len(origins) != 1:
        return False
    try:
        o = urlsplit(origins[0])
        h = urlsplit('http://' + headers['Host'])
        return (o.scheme == 'http' and o.hostname == h.hostname and (o.port or 80) == port
                and not o.username and not o.password and not o.path and not o.query and not o.fragment)
    except ValueError:
        return False


def _hang_so_sai(s):
    raise ValueError('JSON không nhận NaN hay Infinity')


def _so_huu_han(s):
    v = float(s)
    if not math.isfinite(v):
        raise ValueError('số JSON vượt giới hạn')
    return v


def bo_than_con_lai(handler) -> None:
    """Đọc bỏ tối đa 64 KiB/50 ms trước khi từ chối: Windows có thể reset nếu đóng khi thân còn trong đệm."""
    cu = handler.connection.gettimeout()
    handler.connection.settimeout(0.05)
    try:
        handler.rfile.read(65536)
    except OSError:
        pass  # có thể đã hết hạn đọc trước đó; kết nối này sẽ đóng sau phản hồi
    finally:
        handler.connection.settimeout(cu)


def doc_json(handler, toi_da: int) -> dict:
    """Không cắt ngầm thân yêu cầu. Chỉ đọc sau khi kiểm độ dài, trả 4xx khi dữ liệu sai."""
    lengths = handler.headers.get_all('Content-Length', [])
    if handler.headers.get_all('Transfer-Encoding', []) or len(lengths) > 1:
        raise YeuCauLoi(400, 'Tiêu đề độ dài yêu cầu không hợp lệ.')
    s = lengths[0] if lengths else '0'
    if not re.fullmatch(r'[0-9]{1,10}', s):
        raise YeuCauLoi(400, 'Content-Length phải là số nguyên không âm.')
    n = int(s)
    if n > toi_da:
        raise YeuCauLoi(413, 'Dữ liệu gửi lên quá lớn; chia nhỏ rồi thử lại.')
    try:
        b = handler.rfile.read(n) if n else b''
    except TimeoutError as e:
        raise YeuCauLoi(408, 'Hết thời gian đọc yêu cầu.') from e
    if len(b) != n:
        raise YeuCauLoi(400, 'Thân yêu cầu chưa đầy đủ.')
    try:
        yc = json.loads(b.decode('utf-8') or '{}', parse_constant=_hang_so_sai, parse_float=_so_huu_han)
    except (ValueError, RecursionError) as e:
        raise YeuCauLoi(400, 'Dữ liệu phải là JSON UTF-8 hợp lệ với số hữu hạn.') from e
    if not isinstance(yc, dict):
        raise YeuCauLoi(400, 'Dữ liệu JSON phải là một đối tượng.')
    return yc
