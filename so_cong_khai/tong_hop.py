"""Tính số tổng hợp từ các sổ đã đọc. Chỉ đếm và cộng; không suy diễn."""
from __future__ import annotations

from datetime import datetime, timedelta

from .doc_so import VN

DU_LENH = 30          # dưới chừng này lệnh đã đóng thì chưa đủ để nhận xét (cùng ngưỡng với bot)


def tuan_chua(now: datetime) -> tuple[datetime, datetime]:
    """Tuần (thứ Hai 00:00 đến hết Chủ nhật, giờ Việt Nam) chứa thời điểm `now`."""
    local = now.astimezone(VN)
    start = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=7)


def tuan_theo_ma(code: str) -> tuple[datetime, datetime]:
    """'2026-W47' -> khoảng thời gian của tuần ISO đó theo giờ Việt Nam."""
    year, week = code.upper().split('-W')
    start = datetime.fromisocalendar(int(year), int(week), 1).replace(tzinfo=VN)
    return start, start + timedelta(days=7)


def _trong(t, start, end) -> bool:
    return t is not None and (start is None or start <= t) and (end is None or t < end)


def tom_bot(calls: list[dict], start=None, end=None) -> dict:
    """Lệnh gọi của bot có giờ MỞ trong khoảng. "Đã ngã ngũ" với TP1: đã chạm TP1 hoặc đã đóng (như bot tự đếm)."""
    rows = [r for r in calls if _trong(r['opened'], start, end)]
    closed = [r for r in rows if r['closed']]
    decided = [r for r in rows if r['closed'] or r['tps_hit'] >= 1]
    most = max((r['n_tps'] for r in rows), default=0)
    return {'rows': rows, 'n': len(rows), 'closed': len(closed), 'open': len(rows) - len(closed), 'decided': len(decided),
            'tp1': sum(r['tps_hit'] >= 1 for r in decided),
            'sl0': sum(r['closed'] and r['exit'] == 'SL' and r['tps_hit'] == 0 for r in decided),
            'full': sum(r['tps_hit'] == r['n_tps'] for r in rows),
            'levels': [sum(r['tps_hit'] >= k for r in rows) for k in range(1, most + 1)],
            'enough': len(closed) >= DU_LENH}


def sut_von(curve: list[tuple[datetime, float]]) -> tuple[float, float]:
    """Mức sụt lớn nhất từ đỉnh trên đường vốn: (USD, tỷ lệ so với đỉnh)."""
    peak, worst, worst_pct = None, 0.0, 0.0
    for _, eq in curve:
        peak = eq if peak is None or eq > peak else peak
        if peak - eq > worst:
            worst, worst_pct = peak - eq, (peak - eq) / peak if peak else 0.0
    return worst, worst_pct


def tom_tai_khoan(eas: list[tuple[str, dict]], start=None, end=None) -> dict:
    """Một tài khoản demo có một hoặc nhiều EA (`eas`: [(tên, kết quả doc_ea)]). Lệnh tính theo giờ ĐÓNG trong khoảng.
    Chỉ số rủi ro (sụt vốn, hệ số hồi phục) tính trên đường vốn của cả tài khoản, nên chỉ có nghĩa khi không lọc tuần."""
    rows = sorted(({**t, 'ea': name} for name, ea in eas for t in ea['trades'] if _trong(t['closed_at'], start, end)),
                  key=lambda t: t['closed_at'])
    pnl_all = sum(t['pnl'] for _, ea in eas for t in ea['trades'])
    curve = sorted((p for _, ea in eas for p in ea['curve']), key=lambda p: p[0])
    # Nạp/rút tiền làm đường vốn nhảy mà không phải do lệnh: chỉ số rủi ro chỉ tính từ lần nạp/rút gần nhất trở đi.
    deposits = sorted(d for _, ea in eas for d in ea['deposits'])
    cut, before = (deposits[-1][0], None) if deposits else (None, None)
    if cut is not None:
        old = [p for p in curve if p[0] < cut]
        if old:
            before = {'first': old[0][1], 'min': min(v for _, v in old), 'max': max(v for _, v in old), 'from': old[0][0]}
        curve = [p for p in curve if p[0] >= cut]
    gp = sum(t['pnl'] for t in rows if t['pnl'] > 0)
    gl = sum(t['pnl'] for t in rows if t['pnl'] < 0)
    holds = [(t['closed_at'] - t['opened']).total_seconds() / 3600 for t in rows if t['opened']]
    dd, dd_pct = sut_von(curve)
    days = max((curve[-1][0] - curve[0][0]).total_seconds() / 86400, 1) if curve else 1
    daily: dict = {}
    for t in rows:
        d = t['closed_at'].astimezone(VN).date()
        daily[d] = daily.get(d, 0.0) + t['pnl']
    first_eq, last_eq = (curve[0][1], curve[-1][1]) if curve else (0.0, 0.0)
    buys, sells = [t for t in rows if t['side'] == 'BUY'], [t for t in rows if t['side'] == 'SELL']
    return {
        'rows': rows, 'n': len(rows), 'win': sum(t['pnl'] > 0 for t in rows), 'loss': sum(t['pnl'] < 0 for t in rows),
        'pnl': gp + gl, 'gross_profit': gp, 'gross_loss': gl, 'pnl_all': pnl_all,
        'profit_factor': gp / abs(gl) if gl else None,
        'recovery': (gp + gl) / dd if dd > 0 else None,
        'max_dd': dd, 'max_dd_pct': dd_pct,
        'per_week': len(rows) / (days / 7), 'avg_hold_h': sum(holds) / len(holds) if holds else None,
        'best': max((t['pnl'] for t in rows), default=None), 'worst': min((t['pnl'] for t in rows), default=None),
        'buy': (len(buys), sum(t['pnl'] for t in buys)), 'sell': (len(sells), sum(t['pnl'] for t in sells)),
        'daily': sorted(daily.items()), 'curve': curve,
        'first_equity': first_eq, 'last_equity': last_eq, 'equity_change': last_eq - first_eq,
        'unexplained': (last_eq - first_eq) - pnl_all,
        'opens': [{**ea['open'], 'ea': name} for name, ea in eas if ea['open']],
        'orphans': [{**o, 'ea': name} for name, ea in eas for o in ea['orphans'] if _trong(o['opened'], start, end)],
        'deposits': deposits, 'curve_from': cut, 'before': before,
        'last_time': curve[-1][0] if curve else None,
        'per_ea': [{'ten': name, 'version': ea['version'], 'closed': len(ea['trades']), 'open': 1 if ea['open'] else 0,
                    'orphans': len(ea['orphans']), 'pnl': sum(t['pnl'] for t in ea['trades']),
                    'entries': len(ea['trades']) + len(ea['orphans']) + (1 if ea['open'] else 0)} for name, ea in eas],
    }


def tom_xu_huong(sx: dict, start=None, end=None) -> dict:
    rows = [r for r in sx['rows'] if _trong(r['opened'], start, end)]
    done = [r for r in rows if r['result']]
    cum, curve = 0.0, []
    for r in sorted(done, key=lambda r: r['closed_at'] or r['opened']):
        cum += r['usd']
        curve.append((r['closed_at'] or r['opened'], cum))
    return {'rows': rows, 'n': len(rows), 'closed': len(done), 'win': sum(r['usd'] > 0 for r in done),
            'loss': sum(r['usd'] <= 0 for r in done), 'usd': sum(r['usd'] for r in done), 'curve': curve}


def tom_dinh_day(sd: dict, start=None, end=None) -> dict:
    rows = [r for r in sd['rows'] if _trong(r['opened'], start, end)]
    return {'rows': rows, 'n': len(rows), 'win': sum(r['r'] > 0 for r in rows), 'loss': sum(r['r'] <= 0 for r in rows),
            'r': sum(r['r'] for r in rows)}
