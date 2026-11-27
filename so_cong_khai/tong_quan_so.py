"""Ảnh chụp gọn các sổ cho Tổng quan: chỉ đọc, không xuất lại báo cáo hay đọc tài khoản MT5."""
from __future__ import annotations

import math
from datetime import datetime, timezone


def _so(value):
    return float(value) if isinstance(value, (int, float)) and math.isfinite(value) else None


def _gio(value):
    return value.astimezone(timezone.utc).isoformat() if isinstance(value, datetime) else None


def _tia(curve):
    """Giữ cực trị từng nhóm và hai đầu, tối đa khoảng 50 điểm; không gửi cả sổ ra trình duyệt."""
    values = [v for _, v in curve if _so(v) is not None]
    if len(values) <= 50:
        return values
    step = math.ceil((len(values) - 2) / 24)
    out = [values[0]]
    for offset in range(1, len(values) - 1, step):
        group = values[offset:min(offset + step, len(values) - 1)]
        low, high = min(range(len(group)), key=group.__getitem__), max(range(len(group)), key=group.__getitem__)
        out.extend(group[i] for i in sorted({low, high}))
    return out + [values[-1]]


def doc(cfg: dict, now: datetime | None = None) -> dict:
    from .__main__ import gom  # noqa: PLC0415 - dùng cùng phép tổng hợp với sổ cũ, tránh vòng nạp
    now = now or datetime.now(timezone.utc)
    data = gom(cfg)
    rows, errors = [], []
    for acc in data.get('tai_khoan', []):
        summary = acc.get('tom')
        if not summary:
            errors.append(acc['ten'])
            continue
        initial, current = summary.get('first_equity'), summary.get('last_equity')
        change = summary.get('equity_change')
        rows.append({'id': acc['id'], 'ten': acc['ten'], 'loai': 'demo', 'don_vi': 'USD',
                     'gia_tri': _so(current) if summary.get('curve') else None, 'thay_doi': _so(change) if summary.get('curve') else None,
                     'pct': _so(change / initial * 100) if initial and _so(change) is not None else None,
                     'n': summary.get('n', 0), 'mo': len(summary.get('opens') or []),
                     'bo_sung_mt5': (acc.get('bo_sung_mt5') or {}).get('bo_sung', 0),
                     'tia': _tia(summary.get('curve') or []), 'luc': _gio(summary.get('last_time')),
                     'thieu': bool(acc.get('loi') or summary.get('orphans')), 'href': '/so-cong-khai#' + acc['id']})
    bot = data.get('bot')
    if bot is not None:
        decided = bot.get('decided', 0)
        rows.append({'id': 'bot', 'ten': 'Bot tín hiệu vàng', 'loai': 'signal', 'don_vi': 'TP1',
                     'gia_tri': bot.get('tp1', 0), 'mau': decided, 'pct': bot.get('tp1', 0) / decided * 100 if decided else None,
                     'n': bot.get('closed', 0), 'mo': bot.get('open', 0), 'tia': [],
                     'luc': _gio(max((r['opened'] for r in bot.get('rows', [])), default=None)),
                     'thieu': False, 'href': '/so-cong-khai#bot'})
    for key, id_, name in [('xu_huong', 'xu-huong', 'Luật ba khung'), ('dinh_day', 'dinh-day', 'Luật đỉnh/đáy')]:
        item = data.get(key)
        if item is None:
            continue
        closed = item.get('closed', item.get('n', 0))
        rows.append({'id': id_, 'ten': name, 'loai': 'shadow', 'don_vi': 'R' if key == 'dinh_day' else 'win',
                     'gia_tri': _so(item.get('r')) if key == 'dinh_day' else item.get('win', 0),
                     'mau': closed, 'pct': item.get('win', 0) / closed * 100 if closed else None,
                     'n': closed, 'mo': max(0, item.get('n', 0) - closed), 'tia': [],
                     'luc': _gio(max((r['opened'] for r in item.get('rows', []) if r.get('opened')), default=None)),
                     'thieu': item.get('chain_ok') is False, 'href': '/so-cong-khai#' + id_})
    errors += [name for name, _ in data.get('loi', [])]
    return {'luc': now.isoformat(), 'so': rows, 'loi': errors, 'pham_vi': 'all', 'nguon': 'journal'}
