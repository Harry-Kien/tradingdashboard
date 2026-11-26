"""Cách giữ lệnh "sau khi chạm TP1, dời dừng lỗ về giá vào" cho tín hiệu luật bot (chủ dự án chọn ngày 25/11/2026).

Không có phép tính mới: số đo đọc từ out/diem-vao-bot.json do cong-cu/diem_vao_bot.py ghi, bản TLB (thang sáu mức, sau phần chốt đầu dời dừng lỗ
về giá vào) so với bản TL (thang sáu mức, dừng lỗ giữ nguyên), ở phần kiểm (từ năm cat_nam). Bản TLB KHÔNG qua cổng chọn (lời mỗi lệnh thấp hơn),
nên nó chỉ là một gợi ý kèm đủ cả hai mặt: tỷ lệ thắng cao hơn và sụt giảm nhỏ hơn, đổi lại lời mỗi lệnh thấp hơn. Chỉ đọc tệp."""
from __future__ import annotations

import json
from pathlib import Path

from .__main__ import HERE

_nho: dict = {}


def _so(x: float, le: int = 1) -> str:
    s = f'{abs(float(x)):,.{le}f}'.replace(',', '_').replace('.', ',').replace('_', '.')
    return ('−' if float(x) < 0 else '') + s


def _r(x: float) -> str:
    return ('+' if x > 0 else '') + _so(x, 2) + 'R'


def so_do(tep: Path | None = None) -> dict | None:
    """{'tu', 'n', 'thang', 'r', 'dd', 'thang_goc', 'r_goc', 'dd_goc'} của phần kiểm, hoặc None khi chưa có tệp đo hay tệp thiếu số."""
    tep = tep or HERE / 'out' / 'diem-vao-bot.json'
    try:
        key = (str(tep), tep.stat().st_mtime_ns)
        if _nho.get('key') != key:
            d = json.loads(tep.read_text(encoding='utf-8'))
            b = d['D2']['bang']
            hv, goc = b['TLB']['kiem'], b['TL']['kiem']
            _nho.update(key=key, kq={'tu': int(d.get('cat_nam') or 2022), 'n': int(hv['n']), 'thang': float(hv['thang']), 'r': float(hv['r_tb']),
                                     'dd': float(hv['dd']), 'thang_goc': float(goc['thang']), 'r_goc': float(goc['r_tb']), 'dd_goc': float(goc['dd'])})
        return _nho['kq']
    except (OSError, ValueError, KeyError, TypeError):
        return None


def cau(sd: dict | None = None) -> str:
    """Một câu đủ hai mặt để hiện cạnh tín hiệu; chuỗi rỗng khi chưa có số đo."""
    sd = sd if sd is not None else so_do()
    if not sd:
        return ''
    return (f'Giữ lệnh an toàn hơn: sau khi chạm TP1, dời dừng lỗ về giá vào. Đo trên {_so(sd["n"], 0)} lệnh từ {sd["tu"]}: thắng {_so(sd["thang"])}% '
            f'thay vì {_so(sd["thang_goc"])}%, sụt giảm lớn nhất {_so(sd["dd"])}R thay vì {_so(sd["dd_goc"])}R; đổi lại lời mỗi lệnh {_r(sd["r"])} '
            f'thay vì {_r(sd["r_goc"])}.')
