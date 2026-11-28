"""Đo nguyên luật ba khung; không tối ưu, không nối MT5 hoặc gọi AI."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from so_cong_khai import gia, hoc  # noqa: E402

OUT = ROOT / 'out' / 'ba-khung-20261127'
MINUTE = 60_000_000_000


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def simulate(m1, decisions, news, spread, *, fee=0.18, gaps=False, swap=None, news_slip=0.0):
    t = m1.index.as_unit('ns').asi8
    o, hi, lo = (m1[c].to_numpy(dtype=float) for c in ('open', 'high', 'low'))
    sp = np.full(len(t), spread) if np.isscalar(spread) else np.asarray(spread)
    trades, busy, pending = [], -1, None
    for when, side in decisions:
        signal = pd.Timestamp(when).value
        if signal <= busy or news.covers(when):
            continue
        j = int(t.searchsorted(signal))
        if j >= len(t) or t[j] - signal > 5 * MINUTE:
            continue
        buy = side == 'MUA'
        direction = 1 if buy else -1
        entry = round(float(o[j] + (sp[j] if buy else 0)), 2)
        sl, tp = round(entry - direction * 20, 2), round(entry + direction * 5, 2)
        found = None
        for size in (240, 2880, 43200, None):
            end = len(t) if size is None else min(len(t), j + size)
            hs = lo[j:end] <= sl if buy else hi[j:end] + sp[j:end] >= sl
            ht = hi[j:end] >= tp if buy else lo[j:end] + sp[j:end] <= tp
            both = hs | ht
            if both.any():
                rel = int(both.argmax())
                k = j + rel
                exit_open = float(o[k] + (0 if buy else sp[k]))
                stop = bool(hs[rel])
                if gaps:
                    if (exit_open <= sl) if buy else (exit_open >= sl):
                        stop = True
                    elif (exit_open >= tp) if buy else (exit_open <= tp):
                        stop = False
                price = (min(sl, exit_open) if buy else max(sl, exit_open)) if stop and gaps else sl if stop else tp
                found = (k, float(price), 'SL' if stop else 'TP', bool(hs[rel] and ht[rel]))
                break
            if end == len(t):
                break
        if found is None:
            pending = {'signal': pd.Timestamp(signal, tz='UTC').isoformat(), 'side': side, 'entry': entry, 'sl': sl, 'tp': tp}
            break
        k, price, reason, ambiguous = found
        overnight = 0.0
        if swap is not None:
            overnight = entry * swap.QUA_DEM[buy] * swap.so_dem(int(t[j]), int(t[k]))
        slip = news_slip if reason == 'SL' and news.covers(pd.Timestamp(t[k]).to_pydatetime()) else 0.0
        gross = (price - entry) * direction
        net = gross - fee - slip + overnight
        trades.append({'signal': pd.Timestamp(signal, tz='UTC').isoformat(), 'entry_time': pd.Timestamp(t[j], tz='UTC').isoformat(),
                       'exit_time': pd.Timestamp(t[k], tz='UTC').isoformat(), 'year': pd.Timestamp(signal).year, 'side': side,
                       'entry': entry, 'sl': sl, 'tp': tp, 'exit': price, 'reason': reason, 'gross_usd_001': gross,
                       'net_usd_001': net, 'fee': fee, 'news_slip': slip, 'swap': overnight, 'entry_spread': float(sp[j]),
                       'exit_spread': float(sp[k]), 'ambiguous_m1': ambiguous, 'hold_hours': float((t[k] - t[j]) / (60 * MINUTE))})
        busy = int(t[k])
    return pd.DataFrame(trades), pending


def summary(df):
    x = df['net_usd_001'].to_numpy(dtype=float)
    eq = np.r_[0.0, x.cumsum()]
    loss_streak = longest = 0
    for u in x:
        loss_streak = loss_streak + 1 if u <= 0 else 0
        longest = max(longest, loss_streak)
    wins, losses = x[x > 0], x[x < 0]
    return {'trades': len(x), 'wins': int((x > 0).sum()), 'win_pct': round(float((x > 0).mean() * 100), 2),
            'net_usd_001': round(float(x.sum()), 2), 'expectancy_usd_001': round(float(x.mean()), 4),
            'expectancy_r': round(float(x.mean() / 20), 5),
            'profit_factor': round(float(wins.sum() / -losses.sum()), 4) if len(losses) else None,
            'closed_drawdown_usd_001': round(float((np.maximum.accumulate(eq) - eq).max()), 2),
            'longest_losing_streak': longest, 'average_win': round(float(wins.mean()), 4) if len(wins) else None,
            'average_loss': round(float(-losses.mean()), 4) if len(losses) else None,
            'max_holding_hours': round(float(df['hold_hours'].max()), 2), 'ambiguous_m1': int(df['ambiguous_m1'].sum())}


def confidence(df, start, end):
    """Moving-block bootstrap: 4 tuần liên tiếp, 5.000 lần, tỷ số tổng lãi/tổng số lệnh."""
    weekly = df.assign(t=pd.to_datetime(df['exit_time'], utc=True)).set_index('t')['net_usd_001'].resample('W-SUN').agg(['sum', 'count'])
    all_weeks = pd.date_range(pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize() + pd.Timedelta(days=7), freq='W-SUN')
    weekly = weekly.reindex(all_weeks, fill_value=0)
    values = weekly[['sum', 'count']].to_numpy()
    rng = np.random.default_rng(20261127)
    samples = []
    blocks = (len(values) + 3) // 4
    for _ in range(5000):
        begins = rng.integers(0, len(values) - 3, size=blocks)
        indices = (begins[:, None] + np.arange(4)).ravel()[:len(values)]
        sums = values[indices].sum(axis=0)
        if sums[1]:
            samples.append(sums[0] / sums[1])
    return {'method': 'moving-block bootstrap, 4 weeks, 5000 draws, seed 20261127',
            'expectancy_ci95_usd_001': [round(float(v), 4) for v in np.percentile(samples, [2.5, 97.5])]}


def self_check(news):
    idx = pd.date_range('2000-01-03T12:00Z', periods=2, freq='min')
    decisions = [(idx[0].tz_localize(None), 'MUA')]
    df = pd.DataFrame({'open': [100., 75.], 'high': [101., 76.], 'low': [99., 74.]}, index=idx)
    a, _ = simulate(df, decisions, news, 0, fee=0, gaps=False)
    b, _ = simulate(df, decisions, news, 0, fee=0, gaps=True)
    assert a['net_usd_001'].iloc[0] == -20 and b['net_usd_001'].iloc[0] == -25
    df.loc[idx[1], ['open', 'high', 'low']] = [100., 106., 79.]
    c, _ = simulate(df, decisions, news, 0, fee=0, gaps=True)
    assert c['net_usd_001'].iloc[0] == -20
    df.loc[idx[1], ['open', 'high', 'low']] = [106., 107., 79.]
    d, _ = simulate(df, decisions, news, 0, fee=0, gaps=True)
    assert d['net_usd_001'].iloc[0] == 5
    df.loc[idx[1], ['open', 'high', 'low']] = [100., 101., 94.]
    e, _ = simulate(df, [(idx[0].tz_localize(None), 'BAN')], news, 0.17, fee=0, gaps=True)
    assert e['net_usd_001'].iloc[0] == 5


def main():
    started = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((ROOT / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    gia._nap_ma(g)
    from ai import rule_trend as RT
    from tools import ai_trend_history as TH, ai_trend_news as TN
    spec = importlib.util.spec_from_file_location('harrison_costs', ROOT / 'cong-cu/diem_vao.py')
    dv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dv)
    files = [Path(RT.__file__), Path(TH.__file__), Path(TN.__file__), ROOT / 'so_cong_khai/sua_gio.py', Path(__file__)]
    source_hashes = {str(p): digest(p) for p in files}
    plan = {'registered_at_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'unchanged three-timeframe rule; no parameter search',
            'rule_id': RT.MODEL, 'ema': [RT.EMA_FAST, RT.EMA_SLOW], 'lookback': RT.BARS, 'min_bars': RT.MIN_BARS,
            'tp': RT.TP_USD, 'sl': RT.SL_USD, 'utc_window_minutes': RT.WINDOW_MINUTES,
            'one_position': True, 'news_exclusion_minutes': 15, 'range': '2015 through latest complete available M1',
            'units': 'USD at fixed 0.01 standard gold lot = 1 oz; no compounding or margin simulation',
            'source_sha256': source_hashes,
            'scenarios': ['original fixed spread 0.17 + fee 0.18', 'fixed spread with adverse stop gap fills',
                          'historical per-M1 spread, gap fills, current-rate swap estimate, news exit slip 0.25',
                          'same historical-cost scenario with extra round-trip cost 0.25'],
            'not_independent_holdout': 'historical data already examined by this project; year splits are descriptive, not a fresh holdout'}
    (OUT / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    assert (RT.TP_USD, RT.SL_USD, RT.EMA_FAST, RT.EMA_SLOW) == (5, 20, 20, 50)
    self_check(TN.Windows([]))
    print('Đã chốt cách đo và qua kiểm khớp giả lập; đang nạp kho M1...', flush=True)
    m1 = hoc._m1_dai(g, 2015)
    fr = hoc._khung(m1, g)
    print(f'{len(m1):,} nến M1: {m1.index[0]} → {m1.index[-1]}; đang lấy quyết định nguyên luật...', flush=True)
    def naive(df):
        d = df.reset_index(names='time')
        d['time'] = d['time'].dt.tz_localize(None)
        return d
    frames = {tf: naive(fr[tf]) for tf in ('D1', 'H4', 'H1', 'M15')}
    decisions = TH.decisions(frames, m1.index[0].tz_localize(None), (m1.index[-1] + pd.Timedelta(minutes=1)).tz_localize(None))
    events, _ = gia.tin_usd(g)
    news = TN.Windows([pd.Timestamp(t).tz_convert('UTC').tz_localize(None) for t in events])
    spreads = dv.nap_spread(g, m1.index, 0.17)
    print(f'{len(decisions):,} quyết định; {len(events):,} mốc tin; đang chấm và đối chiếu bản gốc...', flush=True)
    reference = TN.simulate(decisions, naive(m1), news, skip_news=True, news_costs=False)
    original, pending = simulate(m1, decisions, news, 0.17)
    assert len(reference) == len(original), (len(reference), len(original))
    differences = []
    for a, b in zip(reference, original.to_dict('records')):
        if abs(a['usd'] - b['net_usd_001']) > 1e-7 or pd.Timestamp(a['t_exit']).value != pd.Timestamp(b['exit_time']).value:
            differences.append(str(a['t']))
    assert not differences, differences[:5]
    scenarios = {'original': (original, pending)}
    scenarios['fixed_gap'] = simulate(m1, decisions, news, 0.17, gaps=True)
    scenarios['historical_costs'] = simulate(m1, decisions, news, spreads, gaps=True, swap=dv, news_slip=0.25)
    scenarios['historical_stress'] = simulate(m1, decisions, news, spreads, fee=0.43, gaps=True, swap=dv, news_slip=0.25)
    result = {'plan': plan, 'run_at_utc': datetime.now(timezone.utc).isoformat(), 'data_start': m1.index[0].isoformat(),
              'data_end': m1.index[-1].isoformat(), 'm1_bars': len(m1), 'raw_signals': len(decisions),
              'news_first': min(events).isoformat() if events else None, 'news_last': max(events).isoformat() if events else None,
              'reference_comparison': {'trades': len(original), 'unexplained_differences': len(differences)}, 'scenarios': {}}
    lines = ['BACKTEST NGUYÊN LUẬT XU HƯỚNG BA KHUNG — 27/11/2026',
             f'Dữ liệu M1: {result["data_start"]} → {result["data_end"]}; {len(m1):,} nến.',
             'Đơn vị USD ở 0,01 lot vàng tiêu chuẩn (1 oz), khối lượng cố định; không tính lãi kép.',
             'Lệnh được phân năm theo thời điểm tín hiệu. 2026 là năm chưa đủ. DD là sụt lãi lỗ đã đóng, chưa gồm lỗ treo.',
             f'Đối chiếu bản gốc: {len(original):,} lệnh, 0 khác biệt chưa giải thích.',
             'Không tối ưu tham số. Dữ liệu quá khứ đã được dự án xem trước đây, không phải ngoài mẫu độc lập.']
    for name, (df, open_trade) in scenarios.items():
        df.to_csv(OUT / f'{name}-trades.csv', index=False)
        groups = {'all': df, '2015_2021': df[df['year'] < 2022], '2022_2026': df[df['year'] >= 2022],
                  '2016_2022': df[(df['year'] >= 2016) & (df['year'] <= 2022)], '2023_2026': df[df['year'] >= 2023]}
        totals = {k: summary(v) for k, v in groups.items() if len(v)}
        totals['all'].update(confidence(df, m1.index[0], m1.index[-1]))
        yearly = {str(int(y)): summary(z) for y, z in df.groupby('year')}
        sides = {side: summary(z) for side, z in df.groupby('side')}
        result['scenarios'][name] = {'totals': totals, 'yearly': yearly, 'sides': sides, 'pending': open_trade}
        lines.extend(['', name, 'Năm | Lệnh | Thắng % | Lãi ròng USD | PF | DD đã đóng USD'])
        lines.extend(f'{y} | {s["trades"]} | {s["win_pct"]:.2f} | {s["net_usd_001"]:+.2f} | {s["profit_factor"]} | {s["closed_drawdown_usd_001"]:.2f}' for y, s in yearly.items())
        for period, s in totals.items():
            lines.append(f'{period}: {s["trades"]} lệnh; thắng {s["win_pct"]:.2f}%; tổng {s["net_usd_001"]:+.2f}; mỗi lệnh {s["expectancy_usd_001"]:+.4f}; PF {s["profit_factor"]}; DD {s["closed_drawdown_usd_001"]}; thua liền {s["longest_losing_streak"]}')
        lines.append('95% CI kỳ vọng/lệnh: ' + str(totals['all']['expectancy_ci95_usd_001']))
        print(name, json.dumps(totals['all'], ensure_ascii=False), flush=True)
    assert all(digest(p) == h for p, h in source_hashes.items()), 'Mã nguồn thay đổi trong lúc đo; cần kiểm tra lại.'
    result['elapsed_seconds'] = round(time.perf_counter() - started, 2)
    (OUT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / 'report.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Xong sau {result["elapsed_seconds"]} giây: {OUT}', flush=True)


if __name__ == '__main__':
    main()
