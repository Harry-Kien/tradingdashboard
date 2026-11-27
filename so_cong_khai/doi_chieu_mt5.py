"""Bằng chứng MT5 chỉ đọc, tách tiến trình; bổ sung dòng đóng thiếu mà không sửa CSV EA.

Chỉ áp dụng khi đã khai chính xác terminal, số DEMO và máy chủ. Không xuất số đầy đủ ra API.
Vị thế có nhiều lần vào/đóng hoặc đảo chiều được giữ để xem xét, không tự ghép.
Nguồn đóng MT5 được hiển thị cùng giờ nhật ký khi EA ghi nhận muộn.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import doc_so, duong, noi_mt5, tai_khoan

CHU_KY = 120
HAN = 360


def _pin(khai):
    p = khai.get('mt5_doi_chieu') or {}
    if not p.get('terminal') or not str(p.get('so', '')).isdigit() or not p.get('may_chu'):
        return None
    return p


def _key(khai):
    return hashlib.sha256(json.dumps(_pin(khai), sort_keys=True).encode()).hexdigest()


def _tep(khai):
    return duong.goc_du_lieu() / 'du-lieu' / 'doi-chieu-mt5' / (_key(khai) + '.json')


def _dt(t):
    v = datetime.fromisoformat(t)
    if v.tzinfo is None:
        raise ValueError('Thiếu múi giờ')
    return v.astimezone(timezone.utc)


def _gio(t):
    return datetime.fromtimestamp(int(t), timezone.utc).isoformat()


def _hop_le(d):
    if not isinstance(d, dict) or d.get('ok') is not True:
        return False
    try:
        _dt(d['luc'])
        for field in ('da_dong', 'mo', 'su_kien'):
            if not isinstance(d[field], list):
                return False
        seen = set()
        for x in d['da_dong'] + d['mo']:
            if not isinstance(x['ve'], int) or x['ve'] <= 0 or x['ve'] in seen:
                return False
            seen.add(x['ve'])
            if not x['ma'] or not x['ea'] or x['side'] not in ('BUY', 'SELL'):
                return False
            if not all(math.isfinite(float(x[k])) for k in ('lots', 'entry', 'pnl')) or x['lots'] <= 0 or x['entry'] <= 0:
                return False
            opened = _dt(x['opened'])
            if x in d['da_dong'] and _dt(x['closed_at']) < opened:
                return False
        for x in d['su_kien']:
            _dt(x['luc'])
            if not isinstance(x['ea'], str):
                return False
        return isinstance(d['so'], str) and d['so'].startswith('•••')
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def doc(khai, now=None, lich_su=False):
    """Chỉ tin ảnh của đúng danh tính đã ghim và chưa quá hạn; mất kết nối không dùng ảnh cũ làm số liệu hiện tại."""
    if not _pin(khai):
        return None
    try:
        d = json.loads(_tep(khai).read_text(encoding='utf-8'))
        age = ((now or datetime.now(timezone.utc)) - _dt(d['luc'])).total_seconds()
        if (_hop_le(d) and d.get('danh_tinh') == _key(khai) and age >= -10
                and (lich_su or (age <= HAN and not d.get('loi_doc_cuoi')))):
            return d
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return None


def _khop(o, x):
    try:
        return (o.get('ma') == x['ma'] and o['side'] == x['side']
                and abs(float(o['lots']) - x['lots']) < 0.000001
                and abs((_dt(x['opened']) - o['opened']).total_seconds()) <= 60
                and abs(float(o['entry']) - x['entry']) <= 0.011
                and all(math.isfinite(float(x[k])) for k in ('lots', 'entry', 'pnl')))
    except (KeyError, TypeError, ValueError):
        return False


def bo_sung(khai, eas, now=None, anh=...):
    """Ghép một đối một bằng giờ vào, mã, hướng, lot, giá vào, EA và position_id. Trả bản sao và thông tin nguồn."""
    now = now or datetime.now(timezone.utc)
    d = doc(khai, now, lich_su=True) if anh is ... else anh
    fresh = bool(d and _hop_le(d) and -10 <= (now - _dt(d['luc'])).total_seconds() <= HAN and not d.get('loi_doc_cuoi'))
    meta = {'san_sang': fresh, 'bo_sung': 0, 'chinh_gio': 0, 'xac_minh': False}
    if not d or not _hop_le(d):
        meta['san_sang'] = False
        return eas, meta
    out = copy.deepcopy(eas)
    used = set()
    day_du = True
    for ten, ea in out:
        closed = [x for x in d['da_dong'] if x['ea'] == ten]
        # Các dòng đóng sẵn cũng phải khớp MT5 trước khi xác nhận toàn bộ sổ.
        for r in ea['trades']:
            xs = [x for x in closed if x['ve'] not in used and _khop(r, x)
                  and abs(x['pnl'] - float(r['pnl'])) <= .05]
            if len(xs) == 1:
                x = xs[0]
                used.add(x['ve'])
                # EA có thể chỉ phát hiện lệnh đã đóng khi được mở lại nhiều giờ/ngày sau đó.
                if abs((_dt(x['closed_at']) - r['closed_at']).total_seconds()) > 60:
                    r.update(closed_at_nhat_ky=r['closed_at'], closed_at=_dt(x['closed_at']), nguon_dong='MT5', ve_mt5=x['ve'])
                    meta['chinh_gio'] += 1
            else:
                day_du = False
        for r in list(ea['orphans']) + ([ea['open']] if ea['open'] else []):
            xs = [x for x in closed if x['ve'] not in used and _khop(r, x)]
            if len(xs) == 1:
                x = xs[0]
                used.add(x['ve'])
                ea['trades'].append({**r, 'closed_at': _dt(x['closed_at']), 'pnl': x['pnl'],
                                     'reason': 'MT5', 'equity': None, 'nguon_dong': 'MT5', 've_mt5': x['ve']})
                if r is ea['open']:
                    ea['open'] = None
                else:
                    ea['orphans'].remove(r)
                meta['bo_sung'] += 1
            elif r is ea['open']:
                ps = [x for x in d['mo'] if x['ea'] == ten and _khop(r, x)]
                if len(ps) != 1:
                    day_du = False
            else:
                day_du = False
        if ea['last_time'] and any(x['ea'] == ten and _dt(x['luc']) > ea['last_time'] for x in d['su_kien']):
            day_du = False
    # Giao dịch MT5 chưa ghép được vẫn phải cảnh báo, kể cả tổng vốn tình cờ trùng nhau.
    names = {ten for ten, _ in eas}
    if names.intersection(d.get('khong_ho_tro', [])):
        day_du = False
    if any(x['ea'] in names and x['ve'] not in used for x in d['da_dong']):
        day_du = False
    meta.update(xac_minh=day_du and fresh, luc=d['luc'], so=d['so'], lenh_mo=len(d['mo']) if fresh else None)
    return out, meta


def chup(mt5, cfg, khai, now=None):
    """Worker dùng phiên MT5 riêng; tuyệt đối không đặt, sửa, đóng lệnh hoặc đăng nhập."""
    now = now or datetime.now(timezone.utc)
    p = _pin(khai)
    if not p:
        return {'ok': False, 'ly_do': 'Chưa ghim danh tính tài khoản đối chiếu.'}
    _, why = noi_mt5.noi(mt5, {'terminal': p['terminal'], 'chi_demo': True})
    if why:
        return {'ok': False, 'ly_do': why}
    try:
        a, t = mt5.account_info(), mt5.terminal_info()
        if (a is None or t is None or not t.connected or str(a.login) != str(p['so']) or a.server != p['may_chu']
                or int(a.trade_mode) != int(getattr(mt5, 'ACCOUNT_TRADE_MODE_DEMO', 0))):
            return {'ok': False, 'ly_do': 'Danh tính DEMO hoặc máy chủ không khớp cấu hình; từ chối đối chiếu.'}
        entries = []
        for e in khai.get('ea', []):
            path = doc_so.mo_rong(e['tep'])
            if not Path(path).name.endswith('_' + str(a.login) + '_events.csv'):
                return {'ok': False, 'ly_do': 'Nhật ký không thuộc số tài khoản đã ghim.'}
            ea = doc_so.doc_ea(path, e.get('lech_gio_utc', 0))
            entries += [r['opened'] for r in ea['trades'] + ea['orphans'] + ([ea['open']] if ea['open'] else []) if r['opened']]
        since = min(entries) - timedelta(days=1) if entries else now - timedelta(days=90)
        pos, deals = mt5.positions_get(), mt5.history_deals_get(since, now + timedelta(days=1))
        current = mt5.account_info()
        if (pos is None or deals is None or current is None or current.login != a.login or current.server != a.server
                or current.trade_mode != a.trade_mode):
            return {'ok': False, 'ly_do': 'Dữ liệu chưa đầy đủ hoặc tài khoản đổi trong lúc đọc.'}
        groups, events = {}, []
        for x in deals:
            if int(x.type) not in (0, 1):
                continue
            ea = tai_khoan._ea(cfg, int(x.magic))
            events.append({'ea': ea, 'luc': _gio(x.time)})
            groups.setdefault(int(x.position_id), []).append(x)
        live = {int(getattr(x, 'identifier', x.ticket)) for x in pos}
        done, unsupported = [], set()
        for ve, xs in groups.items():
            ins = [x for x in xs if int(x.entry) == 0]
            outs = [x for x in xs if int(x.entry) == 1]
            # Unambiguous complete round trips only. Partial closes, pyramiding and reversals remain visible as unresolved.
            if ve in live:
                continue
            if not ve or len(ins) != 1 or len(outs) != 1 or len(xs) != 2:
                unsupported.update(tai_khoan._ea(cfg, int(x.magic)) for x in xs)
                continue
            v, r = ins[0], outs[0]
            if abs(float(v.volume) - float(r.volume)) > .000001 or v.magic != r.magic or v.symbol != r.symbol or v.type == r.type:
                unsupported.add(tai_khoan._ea(cfg, int(v.magic)))
                continue
            done.append({'ve': ve, 'ma': v.symbol, 'side': 'BUY' if int(v.type) == 0 else 'SELL', 'lots': float(v.volume),
                         'entry': float(v.price), 'exit': float(r.price), 'opened': _gio(v.time), 'closed_at': _gio(r.time),
                         'pnl': round(sum(float(x.profit) + float(x.commission) + float(x.swap) + float(getattr(x, 'fee', 0)) for x in xs), 2),
                         'ea': tai_khoan._ea(cfg, int(v.magic))})
        mo = [{'ve': int(x.ticket), 'ma': x.symbol, 'side': 'BUY' if int(x.type) == 0 else 'SELL', 'lots': float(x.volume),
               'entry': float(x.price_open), 'opened': _gio(x.time), 'pnl': float(x.profit), 'ea': tai_khoan._ea(cfg, int(x.magic)),
               'sl': float(x.sl) or None, 'tp': float(x.tp) or None, 'magic': int(x.magic)} for x in pos]
        return {'ok': True, 'luc': now.isoformat(), 'danh_tinh': _key(khai), 'so': '•••' + str(a.login)[-3:],
                'da_dong': done, 'mo': mo, 'su_kien': events, 'khong_ho_tro': sorted(unsupported), 'so_du': round(float(a.balance), 2)}
    finally:
        mt5.shutdown()


def anh_vi_the(khai, now=None):
    d = doc(khai, now)
    if not d:
        return None
    def row(x):
        return {'ve': x['ve'], 'ma': x['ma'], 'huong': x['side'], 'lot': x['lots'], 'vao': x['entry'],
                'mo': _dt(x['opened']), 'nguon': x['ea'], 'sl': x.get('sl'), 'tp': x.get('tp'), 'magic': x.get('magic', 0)}
    return {'so': d['so'], 'so_day_du': str(_pin(khai)['so']), 'luc': _dt(d['luc']), 'mo': [row(x) for x in d['mo']],
            'da_dong': [{**row(x), 'dong': _dt(x['closed_at']), 'gia_dong': x.get('exit'), 'lai': x['pnl']} for x in d['da_dong']]}


def cap_nhat(cfg, config_path):
    for i, khai in enumerate(cfg.get('tai_khoan', [])):
        if not _pin(khai):
            continue
        try:
            r = subprocess.run(duong.lenh_mo_dun('so_cong_khai.doi_chieu_mt5', str(config_path), str(i)),  # noqa: S603 - fixed Python module and argument vector, no shell
                               cwd=duong.goc_chuong_trinh(), capture_output=True, text=True, encoding='utf-8', timeout=75,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=False)
            d = json.loads(r.stdout.strip())
        except (OSError, ValueError, subprocess.TimeoutExpired):
            d = {'ok': False, 'ly_do': 'Không đọc được tiến trình đối chiếu MT5.'}
        path = _tep(khai)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not d.get('ok'):
            previous = doc(khai, lich_su=True)
            if previous:
                d = {**previous, 'loi_doc_cuoi': d.get('ly_do', 'Không đọc được MT5'),
                     'lan_thu': datetime.now(timezone.utc).isoformat()}
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
        temp.replace(path)


class VongDoiChieu(threading.Thread):
    def __init__(self, doc_cfg, config_path):
        super().__init__(name='doi-chieu-mt5', daemon=True)
        self.doc_cfg, self.config_path = doc_cfg, config_path

    def run(self):
        while True:
            try:
                cap_nhat(self.doc_cfg(), self.config_path)
            except Exception:  # một lần đọc lỗi không giết vòng nền; ảnh tự hết hạn sau HAN
                pass
            threading.Event().wait(CHU_KY)


if __name__ == '__main__':
    import MetaTrader5 as mt5
    try:
        cfg = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
        result = chup(mt5, cfg, cfg['tai_khoan'][int(sys.argv[2])])
    except Exception as exc:
        result = {'ok': False, 'ly_do': type(exc).__name__}
    print(json.dumps(result, ensure_ascii=False))
