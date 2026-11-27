# -*- coding: utf-8 -*-
"""Bản vẽ lưu bền theo tài khoản và mã trên máy chủ webapp (27/11/2026).

HTTP lấy người dùng từ phiên đăng nhập, không lấy từ tham số người xem gửi. Kho mới nằm trong
du-lieu/hinh-ve/nguoi-dung/<id>/<mã>.json; giữ 20 phiên bản, ghi nguyên tử và kiểm phiên bản cơ sở.
Kho cũ ở du-lieu/hinh-ve/<mã>.json giữ nguyên để chủ máy nhập sau khi đăng ký tài khoản đầu tiên.
Trình duyệt giữ nháp và mốc đồng bộ riêng theo người dùng; ghép thay đổi khác hình và dừng khi cùng
hình bị sửa khác nhau. Không coi ghi đè cuối cùng là cách xử lý xung đột. Cùng máy chủ mới dùng chung dữ liệu.
Bản sao lưu hiện có bao gồm du-lieu; không thay thế sao lưu ở ổ độc lập."""
from __future__ import annotations

import json
import hashlib
import math
import re
import secrets
import threading
import time
from pathlib import Path

from . import luu_ben, telegram_nhom

TOI_DA_HINH = 1000
TOI_DA_BYTE = 400_000
GIU_PHIEN_BAN = 20
_khoa = threading.RLock()
_BO_QUA = object()


class XungDot(ValueError):
    def __init__(self, hien_tai):
        self.hien_tai = hien_tai
        super().__init__('Chart đã thay đổi ở tab hoặc thiết bị khác.')


class KhoLoi(ValueError):
    pass


def _thu_muc(goc: Path | None = None) -> Path:
    return (telegram_nhom._tep('x').parent if goc is None else goc / 'du-lieu') / 'hinh-ve'


def ma_hop_le(ma: str) -> bool:
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{s}{i}' for s in ('COM', 'LPT') for i in range(1, 10)}
    return (bool(re.fullmatch(r'[A-Za-z0-9._#+\-]{1,40}', ma or '')) and ma not in ('.', '..')
            and ma.split('.')[0].upper() not in reserved and not ma.endswith(('.truoc', '.lich-su')))


def _tep(ma: str, goc: Path | None = None, chu: str = '') -> Path:
    if not ma_hop_le(ma):
        raise ValueError('mã không hợp lệ')
    root = _thu_muc(goc)
    if chu:
        if not re.fullmatch(r'[a-f0-9]{32}', chu):
            raise ValueError('người dùng không hợp lệ')
        root = root / 'nguoi-dung' / chu
    return root / f'{ma}.json'


def _doc_tep(p: Path) -> dict:
    x = json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(x, dict) or not isinstance(x.get('ban'), int) or x['ban'] < 1:
        raise ValueError('sai phiên bản')
    _kiem_ds(x.get('ds'))
    return {'ds': x['ds'], 'ban': x['ban'], 'luc': x.get('luc')}


def doc(ma: str, goc: Path | None = None, chu: str = '') -> dict:
    """{'ds', 'ban', 'luc'}; mã chưa có hình trên máy chủ thì ban là None."""
    p = _tep(ma, goc, chu)
    try:
        return _doc_tep(p)
    except (OSError, ValueError, TypeError, RecursionError):
        candidates = sorted(p.with_suffix('.lich-su').glob('*.json'), reverse=True) if p.with_suffix('.lich-su').exists() else []
        candidates.append(p.with_suffix('.truoc.json'))
        for f in candidates:
            try:
                return {**_doc_tep(f), 'phuc_hoi': True}
            except (OSError, ValueError, TypeError, RecursionError):
                continue
        if p.exists():
            raise KhoLoi('Kho bản vẽ bị hỏng; giữ nguyên tệp để phục hồi, không ghi đè bằng bản rỗng.') from None
        return {'ds': [], 'ban': None, 'luc': None}


def _kiem_ds(ds) -> list:
    if not isinstance(ds, list):
        raise ValueError('dữ liệu hình vẽ không hợp lệ')
    if len(ds) > TOI_DA_HINH:
        raise ValueError(f'quá {TOI_DA_HINH} hình trên một mã')
    ids = set()
    def kiem(v, depth=0):
        if depth > 16:
            raise ValueError('hình vẽ lồng quá sâu')
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError('tọa độ phải là số hữu hạn')
        if isinstance(v, dict):
            for x in v.values():
                kiem(x, depth + 1)
        elif isinstance(v, list):
            for x in v:
                kiem(x, depth + 1)
    for h in ds:
        if not isinstance(h, dict) or not isinstance(h.get('id'), str) or not isinstance(h.get('k'), str):
            raise ValueError('hình vẽ thiếu mã hoặc loại')
        # Hình vẽ giờ được nạp về mọi máy: mã, loại và màu đi vào HTML/CSS của trang (menu chuột phải, thanh công cụ), nên chỉ nhận đúng
        # định dạng, kẻo một bản lưu có chèn thẻ HTML chạy được mã trên mọi trình duyệt mở trang (stored XSS).
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', h['id']) or not re.fullmatch(r'[a-z0-9_]{1,20}', h['k']):
            raise ValueError('mã hoặc loại hình vẽ không hợp lệ')
        if h['id'] in ids:
            raise ValueError('mã hình vẽ bị trùng')
        ids.add(h['id'])
        kiem(h)
        for point in [h.get('a'), *[h[k] for k in ('b', 'c') if k in h], *(h.get('pts') or [])]:
            if not isinstance(point, dict) or any(type(point.get(k)) not in (int, float) or not math.isfinite(point[k]) or abs(point[k]) > 1e15 for k in ('t', 'p')):
                raise ValueError('điểm vẽ cần thời gian và giá hữu hạn')
        if h.get('mau') not in (None, '') and not (isinstance(h['mau'], str) and re.fullmatch(r'#[0-9A-Fa-f]{3,8}', h['mau'])):
            raise ValueError('màu hình vẽ không hợp lệ')
    if len(json.dumps(ds, ensure_ascii=False, allow_nan=False).encode('utf-8')) > TOI_DA_BYTE:
        raise ValueError('hình vẽ quá lớn')
    return ds


def luu(ma: str, ds, goc: Path | None = None, now: float | None = None, *, chu: str = '', ban_co_so=_BO_QUA) -> dict:
    """Ghi bản mới; trả {'ban', 'luc'}. Sai thì ValueError."""
    ds = _kiem_ds(ds)
    p = _tep(ma, goc, chu)
    with _khoa:
        cu = doc(ma, goc, chu)
        if ban_co_so is not _BO_QUA and (ban_co_so != cu['ban'] or isinstance(ban_co_so, bool)):
            raise XungDot(cu)
        if cu['ban'] is not None and cu['ds'] == ds:
            if cu.get('phuc_hoi'):
                luu_ben.ghi_json(p, {k: cu[k] for k in ('ds', 'ban', 'luc')})
            return {'ban': cu['ban'], 'luc': cu['luc']}
        x = {'ds': ds, 'ban': (cu['ban'] or 0) + 1, 'luc': time.time() if now is None else now}
        p.parent.mkdir(parents=True, exist_ok=True)
        if cu['ds']:                                                         # giữ bản CÒN HÌNH gần nhất (bản rỗng không đè lên nó): lỡ xóa thì khôi phục được
            luu_ben.ghi_json(p.with_suffix('.truoc.json'), cu)
        history = p.with_suffix('.lich-su')
        if cu['ban'] and not any(history.glob(f'{cu["ban"]:010d}-*.json')):
            luu_ben.ghi_json(history / f'{cu["ban"]:010d}-{secrets.token_hex(4)}.json', cu)
        luu_ben.ghi_json(p, x)
        luu_ben.ghi_json(history / f'{x["ban"]:010d}-{secrets.token_hex(4)}.json', x)
        for f in sorted(history.glob('*.json'), reverse=True)[GIU_PHIEN_BAN:]:
            f.unlink(missing_ok=True)
    return {'ban': x['ban'], 'luc': x['luc']}


def lich_su(ma: str, goc=None, chu='') -> list[dict]:
    p = _tep(ma, goc, chu)
    found = {}
    for f in list(p.with_suffix('.lich-su').glob('*.json')) + [p.with_suffix('.truoc.json'), p]:
        try:
            x = _doc_tep(f)
            found[x['ban']] = {'ban': x['ban'], 'luc': x['luc'], 'so_hinh': len(x['ds'])}
        except (OSError, ValueError, TypeError):
            continue
    return sorted(found.values(), key=lambda x: x['ban'], reverse=True)[:GIU_PHIEN_BAN]


def khoi_phuc(ma: str, ban: int, ban_co_so, goc=None, chu='') -> dict:
    p = _tep(ma, goc, chu)
    with _khoa:
        for f in list(p.with_suffix('.lich-su').glob('*.json')) + [p.with_suffix('.truoc.json')]:
            try:
                x = _doc_tep(f)
            except (OSError, ValueError, TypeError):
                continue
            if x['ban'] == ban:
                luu(ma, x['ds'], goc, chu=chu, ban_co_so=ban_co_so)
                return doc(ma, goc, chu)
    raise ValueError('không tìm thấy phiên bản cần phục hồi')


def nhap_cu(chu: str, ma_vang: str, goc=None) -> dict:
    """Chỉ web handler của tài khoản chủ được gọi. Không xóa hay ghi đè kho cũ."""
    count, errors = 0, []
    with _khoa:
        for p in _thu_muc(goc).glob('*.json'):
            if not ma_hop_le(p.stem) or p.stem.endswith('.truoc'):
                continue
            try:
                old = _doc_tep(p)['ds']
                ma = ma_vang if p.stem == 'XAU' else p.stem
                current = doc(ma, goc, chu)
                ds, seen = list(current['ds']), {h['id']: h for h in current['ds']}
                for h in old:
                    if h['id'] not in seen:
                        ds.append(h)
                    elif h != seen[h['id']]:
                        copied = 'nhap_' + hashlib.sha256(json.dumps(h, sort_keys=True).encode()).hexdigest()[:24]
                        if copied not in seen:
                            ds.append({**h, 'id': copied})
                luu(ma, ds, goc, chu=chu, ban_co_so=current['ban'])
                count += len(ds) - len(current['ds'])
            except (ValueError, OSError) as e:
                errors.append({'ma': p.stem, 'ly_do': str(e)})
    return {'so_hinh': count, 'loi': errors}


# Lớp đồng bộ tách riêng để kiểm tra ghép xung đột độc lập.
from .hinh_ve_dong_bo import JS  # noqa: E402, F401
