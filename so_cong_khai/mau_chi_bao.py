# -*- coding: utf-8 -*-
"""Đồng bộ "Mẫu của tôi" và chỉ báo yêu thích của bảng Chỉ báo (bieu_do_chi_bao.py) lên máy chủ (26/11/2026), để mọi trình duyệt, máy tính và
điện thoại mở cùng webapp có cùng mẫu. Bộ chỉ báo đang bật (S.ds) vẫn theo từng máy, vì màn hình điện thoại và máy tính thường cần khác nhau.

Lưu ở du-lieu/mau-chi-bao.json: {'mau': {tên: [chỉ báo…]}, 'sao': [mã chỉ báo…], 'ban': số phiên bản, 'luc': giờ lưu}. Bản còn mẫu gần nhất được giữ ở
mau-chi-bao.truoc.json. Dữ liệu này đi vào HTML của bảng chỉ báo trên mọi máy, nên chỉ nhận đúng định dạng: tên mẫu không có ký tự HTML, mã chỉ báo
chữ thường, giá trị là số hữu hạn, chữ ngắn hoặc mã màu."""
from __future__ import annotations

import json
import math
import re
import threading
import time
from pathlib import Path

from . import luu_ben, telegram_nhom

TOI_DA_MAU = 50
TOI_DA_BYTE = 120_000
_khoa = threading.Lock()
_KHONG_CO = object()


class KhoLoi(ValueError):
    """Kho hỏng phải được phục hồi, không thay bằng kho rỗng."""


class XungDot(ValueError):
    def __init__(self, hien_tai):
        super().__init__('Mẫu chỉ báo đã thay đổi ở nơi khác.')
        self.hien_tai = hien_tai


def _tep(goc: Path | None = None, truoc: bool = False, chu: str | None = None) -> Path:
    d = telegram_nhom._tep('x').parent if goc is None else goc / 'du-lieu'
    if chu is not None:
        if not isinstance(chu, str) or not re.fullmatch(r'[0-9a-f]{32}', chu):
            raise ValueError('chủ kho không hợp lệ')
        d = d / 'chi-bao-nguoi-dung' / chu
    return d / ('mau-chi-bao.truoc.json' if truoc else 'mau-chi-bao.json')


def doc(goc: Path | None = None, chu: str | None = None) -> dict:
    p = _tep(goc, chu=chu)
    try:
        x = json.loads(p.read_text(encoding='utf-8'))
        if not isinstance(x, dict) or type(x.get('ban')) is not int or x['ban'] < 1:
            raise ValueError('sai cấu trúc kho')
        mau, sao = kiem(x.get('mau'), x.get('sao'))
        return {'mau': mau, 'sao': sao, 'ban': x['ban'], 'luc': x.get('luc')}
    except FileNotFoundError:
        return {'mau': {}, 'sao': [], 'ban': None, 'luc': None}
    except (OSError, ValueError, TypeError, OverflowError, RecursionError) as e:
        raise KhoLoi('Không đọc được kho mẫu chỉ báo. Giữ nguyên tệp và phục hồi bản sao lưu.') from e


_MA = re.compile(r'[a-z0-9_]{1,30}')
_KHOA = re.compile(r'[A-Za-z0-9_]{1,30}')
_TEN = re.compile(r'[^<>"&\'`\\]{1,40}')
_CHU = re.compile(r'[A-Za-z0-9_.#%+\- ]{0,40}')


def _gia_tri(v, sau: int = 0):
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        if abs(v) > 1e12 or not math.isfinite(v):                           # số nguyên quá lớn: math.isfinite ném OverflowError (lỗi 500)
            raise ValueError('số không hợp lệ')
        return v
    if isinstance(v, str):
        if not _CHU.fullmatch(v):
            raise ValueError('chữ không hợp lệ')
        return v
    if isinstance(v, dict) and sau < 2:
        return {_ten_ts(k): _gia_tri(x, sau + 1) for k, x in v.items()}
    if isinstance(v, list) and sau < 2 and len(v) <= 20:
        return [_gia_tri(x, sau + 1) for x in v]
    raise ValueError('giá trị không hợp lệ')


def _ten_ts(k) -> str:
    if not isinstance(k, str) or not _KHOA.fullmatch(k):
        raise ValueError('tên thông số không hợp lệ')
    return k


def kiem(mau, sao) -> tuple[dict, list]:
    """Chuẩn hóa và kiểm dữ liệu gửi lên; sai thì ValueError."""
    if not isinstance(mau, dict) or len(mau) > TOI_DA_MAU:
        raise ValueError('danh sách mẫu không hợp lệ')
    ra = {}
    for ten, ds in mau.items():
        if not isinstance(ten, str) or not _TEN.fullmatch(ten) or not ten.strip():
            raise ValueError('tên mẫu không hợp lệ')
        if not isinstance(ds, list) or len(ds) > 60:                       # thư viện có 41 chỉ báo; chừa chỗ cho nhiều bản cùng loại
            raise ValueError('mẫu không hợp lệ')
        mot = []
        for x in ds:
            if not isinstance(x, dict) or not isinstance(x.get('k'), str) or not _MA.fullmatch(x['k']):
                raise ValueError('chỉ báo trong mẫu không hợp lệ')
            mot.append({_ten_ts(k): _gia_tri(v) for k, v in x.items()})
        ra[ten] = mot
    if not isinstance(sao, list) or len(sao) > 100 or not all(isinstance(k, str) and _MA.fullmatch(k) for k in sao):
        raise ValueError('danh sách yêu thích không hợp lệ')
    if len(json.dumps({'mau': ra, 'sao': sao}, ensure_ascii=False).encode('utf-8')) > TOI_DA_BYTE:
        raise ValueError('mẫu quá lớn')
    return ra, list(sao)


def luu(mau, sao, goc: Path | None = None, now: float | None = None, *, chu: str | None = None, ban_co_so=_KHONG_CO) -> dict:
    mau, sao = kiem(mau, sao)
    with _khoa:
        cu = doc(goc, chu)
        if ban_co_so is not _KHONG_CO and ban_co_so != cu['ban']:
            raise XungDot(cu)
        x = {'mau': mau, 'sao': sao, 'ban': (cu['ban'] or 0) + 1, 'luc': time.time() if now is None else now}
        p = _tep(goc, chu=chu)
        p.parent.mkdir(parents=True, exist_ok=True)
        if cu['mau'] or cu['sao']:                                            # giữ bản còn dữ liệu; bản rỗng không đè lên nó
            luu_ben.ghi_json(_tep(goc, truoc=True, chu=chu), cu)
        luu_ben.ghi_json(p, x)
    return {'ban': x['ban'], 'luc': x['luc']}


# --------------------------------------------------------------------------- lớp đồng bộ trên trang Biểu đồ
# Theo dõi phần {mau, sao} trong localStorage 'so-cbcn1' (bảng Chỉ báo ghi sau mỗi thay đổi); khác bản đã đồng bộ thì đẩy lên (gom 0,8 giây).
# Lúc mở trang và mỗi 10 giây hỏi máy chủ; bản mới hơn (máy khác vừa lưu mẫu) thì nạp qua CBCN.dongBo, giữ nguyên bộ đang bật của máy này.
from .mau_chi_bao_dong_bo import JS  # noqa: E402, F401
