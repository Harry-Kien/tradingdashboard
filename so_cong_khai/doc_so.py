"""Đọc các sổ của hệ thống. CHỈ ĐỌC: không ghi vào sổ, không nối MT5, không gọi Telegram, không đọc token."""
from __future__ import annotations

import csv
import glob
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

VN = timezone(timedelta(hours=7))
EXIT_KINDS = ('SL', 'BE', 'TIME', 'CLOSE', 'DONE')        # cùng thứ tự với tinhieu/store.py


def mo_rong(path: str) -> str:
    """Thay biến môi trường (%USERPROFILE%) và, nếu có dấu *, chọn tệp mới nhất khớp mẫu."""
    p = os.path.expandvars(path)
    if '*' in p:
        found = sorted(glob.glob(p), key=os.path.getmtime)
        if not found:
            raise FileNotFoundError(f'không có tệp nào khớp {p}')
        p = found[-1]
    if not Path(p).exists():
        raise FileNotFoundError(f'không thấy {p}')
    return p


def _dt(text: str) -> datetime:
    d = datetime.fromisoformat(text)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def doc_bot(db_path: str) -> list[dict]:
    """Các lệnh ĐÃ ĐÁNH SỐ mà bài gốc đã lên nhóm, đúng định nghĩa của Store.calls() trong bot.
    Mở cơ sở dữ liệu ở chế độ chỉ đọc (mode=ro) nên không ảnh hưởng bot đang chạy."""
    p = Path(mo_rong(db_path))
    con = sqlite3.connect('file:' + quote(p.as_posix(), safe='/:') + '?mode=ro', uri=True)
    try:
        status = dict(con.execute('SELECT key, status FROM outbox'))
        out = []
        for sid, body, state in con.execute('SELECT id, body, state FROM signals ORDER BY opened, rowid'):
            b, st = json.loads(body), json.loads(state)
            if not b.get('call') or status.get(f'signal:{sid}') not in ('sent', 'dry'):
                continue
            kinds = {k.rsplit(':', 1)[1] for k in status if k.startswith(sid + ':')}
            closed = bool(st['closed'])
            out.append({'call': b['call'], 'id': sid, 'side': b['side'], 'opened': _dt(b['opened']),
                        'entry': float(b['entry']), 'sl': float(b['sl']), 'tps': [float(x) for x in b['tps']],
                        'n_tps': len(b['tps']), 'tps_hit': int(st['next_tp']), 'closed': closed,
                        'ladder': b.get('ladder', ''),
                        'exit': next((k for k in EXIT_KINDS if k in kinds), None) if closed else None})
        return sorted(out, key=lambda r: r['call'])
    finally:
        con.close()


def _kv(detail: str) -> dict:
    return dict(x.split('=', 1) for x in detail.split() if '=' in x)


def _f(text) -> float:
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


def doc_ea(csv_path: str, lech_gio_utc: float = 0) -> dict:
    """Nhật ký sự kiện của một EA. Đọc được hai dạng cột của dự án:
      - gọn (EA M):       time_server, event, equity, detail          ("lots=0.01 price=...", "trail pnl=11.44")
      - đầy đủ (E, I, BB): time_server, event, ..., reason, lots, sl, tp, ..., equity, ..., fill_price ("sl net=-80.39")
    Ghép mỗi dòng `closed` với lệnh vào gần nhất trước nó. Lệnh vào mà không có dòng đóng trước lệnh vào kế tiếp được
    giữ riêng trong `orphans`, không bị nuốt mất. `lech_gio_utc`: giờ máy chủ trừ giờ UTC (PrimeXBT: 0)."""
    tz = timezone(timedelta(hours=lech_gio_utc))
    trades, orphans, curve, deposits = [], [], [], []
    cur, version = None, ''
    with open(mo_rong(csv_path), encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        gon = 'detail' in (reader.fieldnames or [])
        for row in reader:
            t = datetime.strptime(row['time_server'], '%Y.%m.%d %H:%M:%S').replace(tzinfo=tz)
            ev, eq = row['event'], _f(row['equity'])
            text = (row.get('detail') if gon else row.get('reason')) or ''
            kv = _kv(text)
            if eq > 0:
                curve.append((t, eq))
            if ev == 'init':
                version = kv.get('version') or next((w for w in text.split() if w[:1] == 'v' and w[1:2].isdigit()), version)
            elif ev in ('buy', 'sell'):
                if cur is not None:
                    orphans.append(cur)
                if gon:
                    cur = {'side': ev.upper(), 'opened': t, 'lots': _f(kv.get('lots')), 'entry': _f(kv.get('price')),
                           'sl': _f(kv.get('sl')), 'tp': _f(kv.get('tp'))}
                else:
                    cur = {'side': ev.upper(), 'opened': t, 'lots': _f(row.get('lots')),
                           'entry': _f(row.get('fill_price')) or _f(row.get('req_price')),
                           'sl': _f(row.get('sl')), 'tp': _f(row.get('tp'))}
            elif ev == 'closed':
                words = [w for w in text.split() if '=' not in w]
                base = cur or {'side': '?', 'opened': None, 'lots': _f(row.get('lots')), 'entry': 0.0, 'sl': 0.0, 'tp': 0.0}
                trades.append({**base, 'closed_at': t, 'pnl': _f(kv.get('pnl', kv.get('net'))), 'reason': words[0] if words else '',
                               'equity': eq})
                cur = None
            elif ev == 'balance':
                deposits.append((t, _f(kv.get('deposit_or_withdrawal'))))
    return {'trades': trades, 'open': cur, 'orphans': orphans, 'curve': curve, 'deposits': deposits, 'version': version,
            'first_equity': curve[0][1] if curve else None, 'last_equity': curve[-1][1] if curve else None,
            'last_time': curve[-1][0] if curve else None}


def _jsonl(path: str) -> list[dict]:
    with open(mo_rong(path), encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def _chuoi_lien_tuc(recs: list[dict]) -> bool:
    """Mỗi dòng phải trỏ đúng mã của dòng trước. Đây là kiểm liên kết, không tính lại mã băm."""
    return all(recs[i].get('hash_truoc') == recs[i - 1].get('hash') for i in range(1, len(recs)))


def doc_bong_xu_huong(path: str) -> dict:
    """Sổ chạy bóng của luật xu hướng ba khung: tín hiệu và kết quả (USD ở 0,01 lot)."""
    recs = _jsonl(path)
    kq = {r['tin_hieu_stt']: r for r in recs if r.get('loai') == 'ket_qua'}
    rows = []
    for r in recs:
        if r.get('loai') != 'tin_hieu':
            continue
        k = kq.get(r['stt'])
        rows.append({'stt': r['stt'], 'opened': _dt(r['nen_dong_utc']), 'side': 'BUY' if r['huong'] == 'MUA' else 'SELL',
                     'entry': r['gia_vao'], 'sl': r['sl'], 'tp': r['tp'],
                     'result': k['ket_thuc'] if k else None, 'usd': k['usd'] if k else None,
                     'closed_at': _dt(k['t_dong']) if k and k.get('t_dong') else None})
    return {'rows': rows, 'chain_ok': _chuoi_lien_tuc(recs), 'n_lines': len(recs)}


def doc_bong_dinh_day(path: str) -> dict:
    """Sổ chạy bóng của luật đỉnh/đáy: mỗi kết quả đã đóng kèm hướng lấy từ dòng `goi` của nó."""
    recs = _jsonl(path)
    by_hash = {r.get('hash'): r for r in recs}
    rows = []
    for r in recs:
        if r.get('loai') != 'ket_qua' or r.get('trang_thai') != 'da_dong':
            continue
        side = '?'
        goi = by_hash.get(r.get('goi_hash'))
        if goi:
            try:
                side = {'MUA': 'BUY', 'BAN': 'SELL'}.get(json.loads(goi.get('tra_loi_goc') or '{}').get('hanh_dong'), '?')
            except (ValueError, AttributeError):
                side = '?'
        rows.append({'opened': _dt(r['t_khop']), 'closed_at': _dt(r['t_dong']), 'side': side, 'entry': r.get('gia_khop'),
                     'result': r['ket_thuc'], 'r': float(r['r'])})
    return {'rows': rows, 'chain_ok': _chuoi_lien_tuc(recs), 'n_lines': len(recs),
            'n_candles': sum(r.get('loai') == 'goi' for r in recs)}
