"""Theo dõi tiến cứu riêng cho cấu hình Harry SMC đã khóa, đọc MT5 và chấm mô phỏng."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
from bisect import bisect_left
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event

import numpy as np
import pandas as pd

from . import da_ma, duong, gia, local_runtime, luu_ben, smc_harry as H, smc_harry_loc as L, song
from . import tin_hieu_ngan as T, tin_hieu_tien_cuu as S

THU_MUC = 'harry-smc-loc-tien-cuu'
TEP_TT = 'trang-thai.json'
MAU_M30 = 100
DON_VI_LOT_XAU = 100.


def ma_phien(lock: dict) -> str:
    sha = hashlib.sha256(json.dumps(lock, sort_keys=True).encode()).hexdigest()[:12]
    return f'{L.PHIEN}:{sha}/{S.PHIEN_BAN_CHAM}'


def muc_theo_tick(row, dong, now, tick, vet, *, dich_r, buoc, digits, stops):
    ms = H._tick_ms(tick)
    if ms < S._ms(dong) or not -5 <= now.timestamp() - ms / 1000 <= H.TUOI_TICK:
        return 'gia_cu', {}
    if vet is None:
        return 'thieu_tick', {}
    times, bids = vet
    path = bids[(times >= S._ms(dong)) & (times <= ms)]
    if not len(path):
        return 'thieu_tick', {}
    if np.abs(path - row.close).max() > .25 * row.atr:
        return 'gia_di_xa', {}
    return T.muc_gia(row, float(tick.bid), float(tick.ask), buoc, digits, dich_r=dich_r, spread_atr=L.SPREAD_ATR, stops=stops)


def so_m30(out: Path, broker: str, ma: str, tag: str) -> dict:
    """Tách mẫu đã chấm được giá và chi phí. Tính thêm kịch bản chi phí tăng."""
    stats = {'so': 0, 'mau_toi_thieu': MAU_M30, 'thang_pct': None, 'r_rong_moi_lenh': None,
             'r_stress_moi_lenh': None, 'pf': None, 'qua_cong': False}
    if not broker or not S.tep(out).is_file():
        return stats
    with closing(S._db(out)) as db:
        rows = db.execute('''SELECT r_rong, ABS(vao-sl) FROM tin_hieu
            WHERE may_chu=? AND ma=? AND phien=? AND tf='M30' AND r_rong IS NOT NULL ORDER BY nen_ms''', (broker, ma, tag)).fetchall()
    if not rows:
        return stats
    r, risk = np.asarray(rows, dtype=float).T
    fee = (L.PHI_STRESS_LOT - L.PHI_LOT) / DON_VI_LOT_XAU
    stress = float(np.mean(r - fee / risk))
    win = float(np.mean(r > 0) * 100)
    mean = float(r.mean())
    loss = float(-r[r < 0].sum())
    pf = float(r[r > 0].sum() / loss) if loss else None
    return {**stats, 'so': len(r), 'thang_pct': round(win, 2), 'r_rong_moi_lenh': round(mean, 6),
            'r_stress_moi_lenh': round(stress, 6), 'pf': round(pf, 3) if pf is not None else None,
            'qua_cong': bool(len(r) >= MAU_M30 and win > 70 and mean > 0 and stress > 0 and (pf is None or pf >= 1.1))}


def quet(cfg: dict, out: Path, lock: dict, *, now: datetime | None = None) -> dict:
    g = cfg['gia']
    ma = da_ma.ma_vang(cfg)
    tag = ma_phien(lock)
    ket = {'ma': ma, 'phien': tag, 'luc': (now or datetime.now(timezone.utc)).isoformat(), 'tick_ms': 0, 'ghi_moi': 0,
           'khung': {tf: {'loc': u['loc'], 'tp_r': u['tp_r'], 'tt': 'chua_noi'} for tf, u in lock['chon'].items()}, 'da_cham': []}
    mt5 = da_ma._mt5(g)
    if mt5 is None:
        return {**ket, 'ly_do': song.ly_do() or 'Không kết nối được MT5.'}
    with song._khoa:
        tick = mt5.symbol_info_tick(ma)
        account = mt5.account_info()
    now = now or datetime.now(timezone.utc)
    broker = str(getattr(account, 'server', '') or '')
    ms = H._tick_ms(tick)
    moc_khoa = datetime.fromisoformat(lock['utc_khoa'])
    tick_fresh = bool(ms and -5 <= now.timestamp() - ms / 1000 <= H.TUOI_TICK)
    ket.update(luc=now.isoformat(), tick_ms=ms, tick_moi=bool(tick_fresh and ms >= S._ms(moc_khoa)),
               m30=so_m30(out, broker, ma, tag))
    if broker:
        ket['da_cham'] = S.tong_hop(out, broker, ma, phien_rieng=tag)['ds']
    if not tick_fresh:
        for a in ket['khung'].values():
            a['tt'] = 'gia_cu'
        return ket
    if not broker or getattr(account, 'currency', '') != 'USD' or not ma.upper().startswith('XAUUSD'):
        return {**ket, 'ly_do': 'Cần mã XAUUSD và tài khoản báo giá chi phí bằng USD.'}
    ds = []
    active = {}
    for tf, a in ket['khung'].items():
        close = pd.Timestamp(now).floor(f'{T.KHUNG[tf]}min')
        a['nen_dong'] = close.isoformat()
        if close < moc_khoa:
            a['tt'] = 'truoc_khi_khoa'
        elif not 7 <= close.hour < 15:
            a['tt'] = 'ngoai_gio'
        elif now > close + timedelta(seconds=T.HAN_GIAY):
            a['tt'] = 'qua_han'
        else:
            active[tf] = close
    if active:
        with song._khoa:
            sym = mt5.symbol_info(ma)
            if not sym or not getattr(sym, 'visible', False) or getattr(sym, 'custom', False):
                return {**ket, 'ly_do': 'Mã chưa sẵn sàng trong Market Watch MT5.'}
            if float(getattr(sym, 'trade_contract_size', 0)) != DON_VI_LOT_XAU:
                return {**ket, 'ly_do': 'Cần hợp đồng XAUUSD 100 oz mỗi lot để so với chi phí đã khóa.'}
            raw = {tf: da_ma._nen(mt5, ma, tf, 440) for tf in ('H1', 'H4', *active)}
        fr = {tf: H.CT.da_dong(b, tf, now) for tf, b in raw.items()}
        if min(len(fr[tf]) for tf in ('H1', 'H4')) < 240:
            return {**ket, 'ly_do': 'Chưa đủ lịch sử H1/H4 đã đóng.'}
        context = H.boi_canh(fr)
        tin, cover = gia.tin_usd(g) if g.get('lich_tin') else ([], None)
        tin = sorted(tin)
        rong = timedelta(minutes=15)
        point = float(sym.point)
        buoc = float(getattr(sym, 'trade_tick_size', 0) or point)
        gia_tick = float(getattr(sym, 'trade_tick_value_loss', 0) or 0)
        if not all(math.isfinite(x) and x > 0 for x in (point, buoc, gia_tick)):
            return {**ket, 'ly_do': 'Thiếu bước giá hoặc giá trị tick để chấm chi phí.'}
        stops = max(0, int(getattr(sym, 'trade_stops_level', 0) or 0)) * point
        vet, da_doc = None, False
        for tf, close in active.items():
            a, b = ket['khung'][tf], fr[tf]
            if len(b) < 240 or b.index[-1] + timedelta(minutes=T.KHUNG[tf]) != close:
                a['tt'] = 'thieu_nen'
                continue
            checks = (bisect_left(tin, ref - rong) for ref in (close, now))
            if any(j < len(tin) and tin[j] <= ref + rong for j, ref in zip(checks, (close, now), strict=True)):
                a['tt'] = 'tin_manh'
                continue
            d = L.loc(L.ung_vien(fr, tf, context), a['loc'])
            if d.empty or d.index[-1] != b.index[-1]:
                a['tt'] = 'chua_xac_nhan'
                continue
            if not da_doc:
                vet = H._vet_tick(mt5, ma, now, ms)
                da_doc = True
            row = d.iloc[-1]
            a['tt'], levels = muc_theo_tick(row, close, now, tick, vet, dich_r=a['tp_r'], buoc=buoc, digits=int(sym.digits), stops=stops)
            if a['tt'] == 'dat':
                ds.append({**levels, 'tf': tf, 'loai': str(row.loai), 'huong': 'MUA' if row.phia > 0 else 'BÁN',
                           'trang_thai': 'dat', 'dong': close.isoformat(), 'het': (close + timedelta(seconds=T.HAN_GIAY)).isoformat()})
        if ds:
            snapshot = {'nguon': 'mt5', 'phien_ban': T.PHIEN_BAN, 'may_chu': broker, 'ma': ma, 'luc': now.isoformat(),
                        'tick_ms': ms, 'bid': float(tick.bid), 'ask': float(tick.ask), 'buoc_gia': buoc, 'gia_tick': gia_tick,
                        'tien_tk': 'USD', 'lich_tin': bool(cover and cover >= now), 'ds': ds}
            phi = float((cfg.get('hoc') or {}).get('hoa_hong_lot', 0) or 0)
            ket['ghi_moi'] = S.ghi(out, snapshot, phi, now, phien_rieng=tag)
    if S.cap_nhat(out, mt5, broker, now):
        ket['m30'] = so_m30(out, broker, ma, tag)
    ket['da_cham'] = S.tong_hop(out, broker, ma, phien_rieng=tag)['ds']
    return ket


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cau-hinh', type=Path, default=duong.goc_du_lieu() / 'cau-hinh.json')
    ap.add_argument('--mot-luot', action='store_true')
    args = ap.parse_args()
    read = lambda: json.loads(args.cau_hinh.read_text(encoding='utf-8'))
    base = Path(read().get('thu_muc_ra', 'out'))
    base = base if base.is_absolute() else duong.goc_du_lieu() / base
    out = base / THU_MUC
    lock = L.nap_khoa(base)
    handle = local_runtime.InstanceLock(out / TEP_TT).acquire()
    wait = Event()
    tag = ma_phien(lock)
    first_tick = None
    try:
        saved = json.loads((out / TEP_TT).read_text(encoding='utf-8'))
        if saved.get('phien') == tag:
            first_tick = saved.get('tick_moi_dau_tien_ms')
    except (OSError, ValueError):
        pass
    print(f'Harry SMC {tag} · {out}', flush=True)
    try:
        while True:
            try:
                status = quet(read(), out, lock)
            except (AttributeError, KeyError, OSError, RuntimeError, ValueError, sqlite3.Error) as e:
                status = {'luc': datetime.now(timezone.utc).isoformat(), 'phien': tag, 'ly_do': str(e)}
            if first_tick is None and status.get('tick_moi'):
                first_tick = status['tick_ms']
            status['tick_moi_dau_tien_ms'] = first_tick
            luu_ben.ghi_json(out / TEP_TT, status)
            if args.mot_luot:
                print(json.dumps(status, ensure_ascii=False), flush=True)
                return
            wait.wait(5)
    except KeyboardInterrupt:
        pass
    finally:
        handle.release()


if __name__ == '__main__':
    main()
