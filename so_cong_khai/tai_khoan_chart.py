"""Tài khoản webapp cục bộ. Không phải tài khoản MT5.

Mật khẩu scrypt (N=2^17, r=8, p=1); phiên 256 bit qua cookie HttpOnly/SameSite,
chỉ lưu SHA256 của mã phiên. Tài khoản chủ truy cập dữ liệu MT5 trên máy;
các tài khoản khác chỉ truy cập kho biểu đồ riêng. Không mở máy chủ này ra mạng.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from contextlib import contextmanager
from http.cookies import CookieError, SimpleCookie
from pathlib import Path

from . import duong, luu_ben

COOKIE = 'hgr_chart_session'
HAN = 30 * 86400
_khoa = threading.RLock()
_thu: dict = {}


class LoiTaiKhoan(ValueError):
    def __init__(self, ma: int, ly_do: str):
        self.ma = ma
        super().__init__(ly_do)


def _tep(goc=None):
    return (Path(goc) if goc is not None else duong.goc_du_lieu()) / 'du-lieu' / 'tai-khoan-chart.json'


def _doc(goc=None):
    try:
        d = json.loads(_tep(goc).read_text(encoding='utf-8'))
        if not isinstance(d.get('nguoi'), dict) or not isinstance(d.get('phien'), dict):
            raise ValueError('sai cấu trúc')
        return d
    except FileNotFoundError:
        return {'nguoi': {}, 'phien': {}}
    except (OSError, ValueError, AttributeError) as e:
        raise LoiTaiKhoan(503, 'Không đọc được kho tài khoản. Cần phục hồi bản sao lưu; không tạo lại kho rỗng.') from e


def _bam(password, salt):
    return hashlib.scrypt(password.encode('utf-8'), salt=bytes.fromhex(salt), n=131072, r=8, p=1,
                          maxmem=256 * 1024 * 1024, dklen=32).hex()


def _cong_khai(u):
    return {k: u[k] for k in ('id', 'ten', 'chu')}


def _token(cookie):
    try:
        c = SimpleCookie()
        c.load(cookie or '')
        t = c[COOKIE].value if COOKIE in c else ''
        return t if re.fullmatch(r'[A-Za-z0-9_-]{43}', t) else ''
    except (ValueError, KeyError, CookieError):
        return ''


def hien_tai(cookie='', goc=None, now=None):
    token = _token(cookie)
    if not token:
        return None
    with _khoa:
        d = _doc(goc)
        phien = d['phien'].get(hashlib.sha256(token.encode()).hexdigest(), {})
        u = d['nguoi'].get(phien.get('uid'))
        return _cong_khai(u) if u and phien.get('het', 0) > (time.time() if now is None else now) else None


def vao(ten, mat_khau, tao=False, goc=None, now=None):
    now = time.time() if now is None else now
    if not isinstance(ten, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{3,40}', ten):
        raise LoiTaiKhoan(400, 'Tên đăng nhập cần 3–40 ký tự: chữ không dấu, số, dấu chấm, gạch ngang hoặc gạch dưới.')
    if not isinstance(mat_khau, str) or not 12 <= len(mat_khau) <= 128:
        raise LoiTaiKhoan(400, 'Mật khẩu cần từ 12 đến 128 ký tự.')
    key = (str(_tep(goc)), ten.lower())
    with _khoa:
        # Giới hạn cả theo tên và toàn bộ kho, tránh đổi tên để thử mật khẩu liên tục.
        for k, limit in ((key, 6), ((str(_tep(goc)), '*'), 30)):
            times = [t for t in _thu.get(k, []) if now - t < 300]
            if len(times) >= limit:
                raise LoiTaiKhoan(429, 'Đã thử nhiều lần. Hãy thử lại sau 5 phút.')
            _thu[k] = times + [now]
        d = _doc(goc)
        u = next((u for u in d['nguoi'].values() if u['ten'].lower() == ten.lower()), None)
        if tao:
            if u:
                raise LoiTaiKhoan(409, 'Tên đăng nhập đã được sử dụng.')
            if len(d['nguoi']) >= 1000:
                raise LoiTaiKhoan(429, 'Kho tài khoản đã đầy.')
            salt = secrets.token_hex(32)
            u = {'id': secrets.token_hex(16), 'ten': ten, 'chu': not d['nguoi'], 'salt': salt,
                 'hash': _bam(mat_khau, salt), 'tao': now, 'alg': 'scrypt-131072-8-1'}
            d['nguoi'][u['id']] = u
        else:
            salt = u['salt'] if u else '00' * 32
            result = _bam(mat_khau, salt)
            if not u or not hmac.compare_digest(result, u['hash']):
                raise LoiTaiKhoan(401, 'Tên đăng nhập hoặc mật khẩu không đúng.')
        _thu.pop(key, None)
        d['phien'] = {k: v for k, v in d['phien'].items() if v['het'] > now}
        own = sorted((k for k, v in d['phien'].items() if v['uid'] == u['id']), key=lambda k: d['phien'][k]['tao'])
        for k in own[:-9]:
            del d['phien'][k]
        token = secrets.token_urlsafe(32)
        d['phien'][hashlib.sha256(token.encode()).hexdigest()] = {'uid': u['id'], 'tao': now, 'het': now + HAN}
        luu_ben.ghi_json(_tep(goc), d)
        return _cong_khai(u), token


def ra(cookie, goc=None):
    token = _token(cookie)
    if token:
        with _khoa:
            d = _doc(goc)
            d['phien'].pop(hashlib.sha256(token.encode()).hexdigest(), None)
            luu_ben.ghi_json(_tep(goc), d)


def cookie_header(token=''):
    # Máy chủ chỉ HTTP loopback. Khi triển khai HTTPS cần thêm Secure và dùng dịch vụ xác thực phù hợp.
    return f'{COOKIE}={token}; Path=/; Max-Age={HAN if token else 0}; HttpOnly; SameSite=Strict'


@contextmanager
def phien_noi_bo(goc):
    """Phiên ngắn cho tác vụ chụp biểu đồ trong tiến trình chủ; không có API phát phiên này."""
    token = secrets.token_urlsafe(32)
    key = hashlib.sha256(token.encode()).hexdigest()
    with _khoa:
        data = _doc(goc)
        owner = next((u for u in data['nguoi'].values() if u.get('chu')), None)
        if owner:
            now = time.time()
            data['phien'][key] = {'uid': owner['id'], 'tao': now, 'het': now + 60}
            luu_ben.ghi_json(_tep(goc), data)
    try:
        yield token if owner else None
    finally:
        if owner:
            with _khoa:
                data = _doc(goc)
                data['phien'].pop(key, None)
                luu_ben.ghi_json(_tep(goc), data)
