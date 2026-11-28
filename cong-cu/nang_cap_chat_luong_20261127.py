"""Đo ba bộ lọc đã đăng ký; không gửi Telegram, không nối MT5, không đặt lệnh."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'cong-cu' / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def stats(df):
    if not len(df):
        return {'n': 0, 'thang': None, 'r_tb': None, 'tong': 0, 'dd': 0}
    x = df.sort_values('t_ra', kind='stable')['r'].to_numpy()
    eq = np.r_[0.0, np.cumsum(x)]
    return {'n': len(x), 'thang': round(float((x > 0).mean() * 100), 2), 'r_tb': round(float(x.mean()), 5),
            'tong': round(float(x.sum()), 3), 'dd': round(float((np.maximum.accumulate(eq) - eq).max()), 3),
            'cham_tp': round(float((df['ket'] == 'TP').mean() * 100), 2),
            'het_gio': round(float((df['ket'] == 'Hết giờ').mean() * 100), 2)}


def partitions(df):
    y = pd.to_datetime(df['t'], utc=True).dt.year
    return {name: stats(df[(y >= a) & (y <= b)]) for name, a, b in
            (('chon', 2015, 2021), ('xac_nhan_1', 2022, 2024), ('xac_nhan_2', 2025, 2026))}


def improves(v, base, minimum):
    return (v['n'] >= minimum and v['r_tb'] > 0 and v['r_tb'] > base['r_tb']
            and v['thang'] > base['thang'] and v['cham_tp'] > base['cham_tp'] and v['dd'] <= base['dd'])


def main():
    start = time.monotonic()
    cfg = json.loads((ROOT / 'cau-hinh.json').read_text(encoding='utf-8'))
    LB = load('loc_lenh_bot')
    ctx = LB.nap(cfg)
    from tinhieu import backtest as BT, levels as LV, quality as Q, rules as R
    from so_cong_khai import gia
    raw_scan, raw_sim = R.scan, BT.simulate
    news = np.array([pd.Timestamp(t).value for t in gia.tin_usd(cfg['gia'])[0]], dtype=np.int64)
    news.sort()
    window = pd.Timedelta(minutes=15).value
    out = {'luc': datetime.now(timezone.utc).isoformat(), 'du_lieu_den': ctx['m1'].index[-1].isoformat(),
           'dang_ky_sha256': hashlib.sha256((ROOT / 'docs/DANG_KY_NANG_CAP_CHAT_LUONG_20261127.md').read_bytes()).hexdigest(),
           'bien_the': {}, 'so_tin_usd': len(news),
           'gioi_han': 'Lịch sử đã từng nghiên cứu; xác nhận theo thời gian chưa phải kiểm tiến cứu độc lập.'}
    keep = []

    def simulate(setups, mb, *args, **kw):
        return raw_sim(setups, mb.assign(spread=ctx['D']['S']), *args, **kw)

    BT.simulate = simulate
    try:
        for mode in Q.MODES:
            def scan(bars, h1, h4, d1, tf='M5', kinds=None):
                buy, sell = Q.masks(bars, mode)
                sets = raw_scan(bars, h1, h4, d1, tf, kinds)
                ret = []
                for s in sets:
                    if not (buy if s.side == 'BUY' else sell).loc[s.bar_time]:
                        continue
                    due = (s.bar_time + pd.Timedelta(R.TIMEFRAMES[s.code])).value
                    if np.searchsorted(news, due + window, side='right') > np.searchsorted(news, due - window, side='left'):
                        continue
                    ret.append(s)
                return ret

            R.scan = scan
            trades, sigs = ctx['DB'].lenh_cua_bot(ctx['g'], ctx['m1'], ctx['fr']['D1'], ctx['sp0'], ('M5', 'M15'))
            signals = {(pd.Timestamp(t['entry_time']), t['tf']): s for t, s in zip(trades, sigs)}
            th = ctx['DB'].thanh_tin_hieu(trades, sigs, ctx['D'], ctx['fr']['M15'], LV.TP_R)
            rows = {'tp1': [], 'sau_muc': []}
            for s in th:
                s['muc_tieu'] = signals[(s['t'], s['khung'])].tps[0]
                for name, tp in (('tp1', 'T2'), ('sau_muc', 'TL')):
                    x = ctx['DV'].mo_phong(ctx['D'], s, 'bot', tp=tp)
                    if x['khop']:
                        row = {'t': s['t'].isoformat(), 't_ra': x['t_ra'], 'r': x['r'], 'ket': x['ket'], 'huong': s['huong'], 'khung': s['khung']}
                        rows[name].append(row)
                        keep.append({'bien_the': mode, 'cach_chot': name, **row})
            out['bien_the'][mode] = {name: partitions(pd.DataFrame(values)) for name, values in rows.items()}
            print(json.dumps({'bien_the': mode, **out['bien_the'][mode]}, ensure_ascii=False), flush=True)
    finally:
        R.scan, BT.simulate = raw_scan, raw_sim
    variants = out['bien_the']
    base = variants['tat']
    eligible = [name for name in Q.MODES[1:] if improves(variants[name]['tp1']['chon'], base['tp1']['chon'], 200)]
    chosen = max(eligible, key=lambda name: variants[name]['tp1']['chon']['r_tb']) if eligible else None
    checks = {}
    if chosen:
        for part in ('xac_nhan_1', 'xac_nhan_2'):
            v, b = variants[chosen], base
            checks[part] = improves(v['tp1'][part], b['tp1'][part], 100)
            checks[part + '_sau_muc'] = (v['sau_muc'][part]['r_tb'] >= b['sau_muc'][part]['r_tb']
                                          and v['sau_muc'][part]['dd'] <= b['sau_muc'][part]['dd'])
    out.update(chon=chosen, cong=checks, duoc_ap_dung=bool(chosen and all(checks.values())), giay=round(time.monotonic() - start, 1))
    (ROOT / 'out/nang-cap-chat-luong-20261127.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    pd.DataFrame(keep).to_csv(ROOT / 'out/nang-cap-chat-luong-20261127-lenh.csv', index=False)
    print(json.dumps({k: out[k] for k in ('chon', 'cong', 'duoc_ap_dung', 'giay')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
