"""Tin USD mức cao sắp ra kèm số đo phản ứng của giá vàng với đúng loại tin đó (out/phan-ung-tin.json, do cong-cu/phan_ung_tin.py ghi).

Số đo nói giá THƯỜNG chạy bao xa sau tin, không nói chạy chiều nào: trên 3.994 lần ra tin 2015–11/2026, không quy tắc đoán chiều nào vượt mức tung
đồng xu (48,6–51,4% ở phần kiểm tra). Chỉ đọc tệp; không gọi mạng."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import gia
from .__main__ import HERE

_nho: dict = {}


# Tên tin trong lịch ForexFactory (lịch mạng, dùng khi tệp lịch của EA hết hạn) → tên trong lịch MT5 mà số đo phản ứng giá dùng
TEN_FF = {**gia.FF_MT5, 'Fed Chair Powell Speaks': 'Fed Chair Powell Speech',
          'Flash Manufacturing PMI': 'S&P Global Manufacturing PMI', 'Flash Services PMI': 'S&P Global Services PMI'}


def thong_ke(tep: Path | None = None) -> dict | None:
    tep = tep or HERE / 'out' / 'phan-ung-tin.json'
    try:
        key = (str(tep), tep.stat().st_mtime_ns)
        if _nho.get('key') != key:
            _nho.update(key=key, kq=json.loads(tep.read_text(encoding='utf-8')))
        return _nho['kq']
    except (OSError, ValueError):
        return None


def tin_toi(cfg: dict, now: datetime | None = None, n: int = 3, tep: Path | None = None) -> dict:
    """{'ds': [{'luc', 'ten', 'con_phut', 'n', 'd15_tv', 'd15_p90', 'qua10_15'}], 'doan_chieu': {...}} cho `n` tin sắp ra."""
    now = now or datetime.now(timezone.utc)
    tk = thong_ke(tep) or {}
    theo = {z['ten']: z for z in tk.get('loai', [])}
    ds = []
    for x in gia.tin_sap_toi(cfg, now, n):
        z = theo.get(x['ten']) or theo.get(TEN_FF.get(x['ten'], '')) or {}
        luc = datetime.fromisoformat(x['luc'])
        ds.append({'luc': x['luc'], 'ten': x['ten'], 'con_phut': int((luc - now).total_seconds() // 60), 'n': z.get('n'),
                   'd15_tv': z.get('gan_day_d15_tv') or z.get('d15_tv'), 'd15_p90': z.get('gan_day_d15_p90') or z.get('d15_p90'),   # số từ 2024 (mức giá gần với hiện nay)
                   'qua10_15': z.get('qua10_15')})
    qt = tk.get('quy_tac', {}).get(tk.get('chon') or '', {})
    return {'ds': ds, 'doan_chieu': {'qua_cong': bool(tk.get('qua_cong')), 'ty_le_kiem': (qt.get('kiem') or [None, None, None])[2]} if tk else None}
