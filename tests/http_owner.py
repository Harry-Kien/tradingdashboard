"""Client fixture: functional HTTP tests send a real owner session cookie.

No server bypass. Authorization tests use their own explicit anonymous/customer clients.
"""
import urllib.request
from pathlib import Path
from so_cong_khai import tai_khoan_chart

_cookies = {}


def owner_cookie(root):
    root = Path(root).resolve()
    if root not in _cookies:
        _, token = tai_khoan_chart.vao('fixture-owner', 'fixture-only-password-12345', True, root)
        _cookies[root] = tai_khoan_chart.cookie_header(token).split(';')[0]
    return _cookies[root]


def owner_urlopen(url, *args, root, **kwargs):
    request = urllib.request.Request(url) if isinstance(url, str) else url
    current = request.get_header('Cookie', '')
    request.add_header('Cookie', current + ('; ' if current else '') + owner_cookie(root))
    return urllib.request.urlopen(request, *args, **kwargs)
