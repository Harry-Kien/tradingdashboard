"""Bốn bộ lọc Harrison, đăng ký ở HARRISON_DANG_KY_20261127.md; không tối ưu thêm."""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from so_cong_khai import gia, harrison, hoc  # noqa: E402

OUT = ROOT / 'out/harrison-cai-tien-20261127'
CUTOFF = pd.Timestamp('2026-11-26T16:17:00Z')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    started = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    bt = module('harrison_backtest_base', ROOT / 'cong-cu/backtest_ba_khung_20261127.py')
    costs = module('harrison_backtest_costs', ROOT / 'cong-cu/diem_vao.py')
    plan = ROOT / 'HARRISON_DANG_KY_20261127.md'
    hashes = {str(p.relative_to(ROOT)): bt.digest(p) for p in (plan, Path(harrison.__file__), Path(__file__))}
    (OUT / 'registration.json').write_text(json.dumps({'before_measurement_utc': datetime.now(timezone.utc).isoformat(),
                                                    'cutoff': CUTOFF.isoformat(), 'sha256': hashes}, indent=2), encoding='utf-8')
    g = json.loads((ROOT / 'cau-hinh.json').read_text(encoding='utf-8'))['gia']
    gia._nap_ma(g)
    from tools import ai_trend_history as th, ai_trend_news as tn
    print('Nạp dữ liệu và dựng nến đã đóng; giữ nguyên TP 5 / SL 20...', flush=True)
    m1 = hoc._m1_dai(g, 2015)
    m1 = m1[m1.index <= CUTOFF]
    fr = hoc._khung(m1, g)
    def naive(df):
        d = df.reset_index(names='time')
        d['time'] = d['time'].dt.tz_localize(None)
        return d
    decisions = th.decisions({tf: naive(fr[tf]) for tf in ('D1', 'H4', 'H1', 'M15')},
                             m1.index[0].tz_localize(None), (m1.index[-1] + pd.Timedelta(minutes=1)).tz_localize(None))
    table = harrison.indicators(fr)
    spreads = costs.nap_spread(g, m1.index, .17)
    times = m1.index.as_unit('ns').asi8
    candidates = {k: [] for k in harrison.CANDIDATES}
    for when, side in decisions:
        f = harrison.features(table, when)
        assert f.get('base') and f.get('side') == side, f'Tín hiệu không trùng luật gốc: {when}'
        j = int(times.searchsorted(pd.Timestamp(when).value))
        if j >= len(times) or times[j] - pd.Timestamp(when).value > 5 * bt.MINUTE:
            continue
        for key in candidates:
            if harrison.allowed(f, key, float(spreads[j])):
                candidates[key].append((when, side))
    news_times, _ = gia.tin_usd(g)
    news = tn.Windows([pd.Timestamp(t).tz_convert('UTC').tz_localize(None) for t in news_times])
    result = {'version': harrison.VERSION, 'run_at': datetime.now(timezone.utc).isoformat(),
              'data_start': m1.index[0].isoformat(), 'data_end': m1.index[-1].isoformat(),
              'original_decisions': len(decisions), 'original_signal_mismatches': 0,
              'selection_period': '2015–2019', 'validation_period': '2020–2022', 'confirmation_period': '2023–2026',
              'independent_holdout': False, 'rule': {'tp': 5, 'sl': 20, 'scope': 'XAUUSD M15'}, 'candidates': {}}
    dfs = {}
    for key, decs in {'original': decisions, **candidates}.items():
        d, pending = bt.simulate(m1, decs, news, spreads, gaps=True, swap=costs, news_slip=.25)
        dfs[key] = d
        periods = {'train': d[d.year <= 2019], 'validation': d[(d.year >= 2020) & (d.year <= 2022)], 'confirmation': d[d.year >= 2023], 'all': d}
        stats = {k: bt.summary(v) if len(v) else {'trades': 0, 'expectancy_usd_001': None, 'net_usd_001': 0, 'win_pct': None,
                                                'profit_factor': None, 'closed_drawdown_usd_001': None} for k, v in periods.items()}
        stress = {}
        for k, z in periods.items():
            if len(z):
                z = z.copy()
                z['net_usd_001'] -= .25
                stress[k] = bt.summary(z)
        result['candidates'][key] = {'name': harrison.CANDIDATES.get(key, 'Luật gốc'), 'signal_count': len(decs),
                                     'stats': stats, 'stress': stress, 'yearly': {str(y): bt.summary(z) for y, z in d.groupby('year')}, 'pending': pending}
        d.to_csv(OUT / f'{key}-trades.csv', index=False)
        print(key, json.dumps(stats, ensure_ascii=False), flush=True)
    selectable = [k for k in candidates if result['candidates'][k]['stats']['train']['trades'] >= 200]
    if not selectable:
        raise RuntimeError('Không ứng viên nào đủ 200 lệnh để chọn; cần ghi thiếu mẫu, không chọn theo phần kiểm.')
    selected = max(selectable, key=lambda k: result['candidates'][k]['stats']['train']['expectancy_usd_001'])
    chosen = result['candidates'][selected]
    ci = bt.confidence(dfs[selected], m1.index[0], m1.index[-1])
    chosen['confidence'] = ci
    base = result['candidates']['original']['stats']
    a, v, c = (chosen['stats'][k] for k in ('train', 'validation', 'confirmation'))
    years_positive = sum(s['net_usd_001'] > 0 for s in chosen['yearly'].values())
    gates = [
        ('Phần chọn có lãi và kỳ vọng hơn gốc', a['net_usd_001'] > 0 and a['expectancy_usd_001'] > base['train']['expectancy_usd_001']),
        ('2020–2022: đủ 100 lệnh, kỳ vọng dương và hơn gốc, PF ≥ 1,05', v['trades'] >= 100 and v['expectancy_usd_001'] > max(0, base['validation']['expectancy_usd_001']) and v['profit_factor'] >= 1.05),
        ('2023–2026: đủ 200 lệnh, kỳ vọng hơn gốc, PF ≥ 1,10', c['trades'] >= 200 and c['expectancy_usd_001'] > base['confirmation']['expectancy_usd_001'] and c['profit_factor'] >= 1.10),
        ('2023–2026: tỷ lệ thắng hơn gốc ít nhất 0,5 điểm phần trăm', c['trades'] > 0 and c['win_pct'] >= base['confirmation']['win_pct'] + .5),
        ('2023–2026: sụt giảm đã đóng không lớn hơn gốc', c['trades'] > 0 and c['closed_drawdown_usd_001'] <= base['confirmation']['closed_drawdown_usd_001']),
        ('Ít nhất 7/12 năm có lãi', years_positive >= 7),
        ('Cận dưới khoảng tin cậy 95% của kỳ vọng lớn hơn 0', ci['expectancy_ci95_usd_001'][0] > 0),
        ('Cộng 0,25 USD/lệnh vẫn dương ở cả hai đoạn kiểm', all(chosen['stress'].get(k, {}).get('net_usd_001', 0) > 0 for k in ('validation', 'confirmation'))),
    ]
    result.update(selected=selected, selected_name=harrison.CANDIDATES[selected], gate_passed=all(ok for _, ok in gates),
                  gates=[{'name': name, 'passed': bool(ok)} for name, ok in gates], years_positive=years_positive,
                  future_start='2026-11-27T00:00:00+00:00', source_sha256=hashes,
                  limitations=['Toàn bộ giá quá khứ đã từng được xem trong dự án; không phải kiểm ngoài mẫu độc lập.',
                               'Spread M1 không tái tạo tick thật; swap dùng mức hiện tại cho quá khứ.',
                               '0,01 lot chuẩn = 1 oz; DD đã đóng, chưa gồm lỗ treo hoặc margin call.'])
    assert all(bt.digest(ROOT / p) == h for p, h in hashes.items()), 'Mã nghiên cứu đổi trong lúc chạy.'
    result['seconds'] = round(time.perf_counter() - started, 2)
    (OUT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['HARRISON 3 KHUNG — NGHIÊN CỨU CẢI TIẾN 27/11/2026',
             'Chọn duy nhất trên 2015–2019; không đổi lựa chọn theo phần sau. TP 5, SL 20 giữ nguyên.',
             'Đơn vị USD/0,01 lot tiêu chuẩn; không lãi kép. Mỗi lúc một lệnh. Chi phí lịch sử mô phỏng.',
             f'Đối chiếu {len(decisions)} tín hiệu nguyên luật: 0 khác biệt.',
             f'Chọn {selected}: {harrison.CANDIDATES[selected]}; qua cổng: {result["gate_passed"]}.',
             '', 'Bản | Giai đoạn | Lệnh | Thắng % | USD/lệnh | Tổng USD | PF | DD USD']
    for key, r in result['candidates'].items():
        for period, s in r['stats'].items():
            lines.append(f'{key} | {period} | {s["trades"]} | {s["win_pct"]} | {s["expectancy_usd_001"]} | {s["net_usd_001"]} | {s["profit_factor"]} | {s["closed_drawdown_usd_001"]}')
    lines += ['', 'CỔNG ÁP DỤNG'] + [('ĐẠT ' if ok else 'CHƯA ĐẠT ') + name for name, ok in gates]
    lines += ['', 'Khoảng tin cậy 95% kỳ vọng của bản được chọn: ' + str(ci['expectancy_ci95_usd_001'])] + result['limitations']
    (OUT / 'report.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('CHỌN', selected, 'QUA CỔNG', result['gate_passed'], json.dumps(result['gates'], ensure_ascii=False), flush=True)
    print(f'Xong {result["seconds"]} giây: {OUT}', flush=True)


if __name__ == '__main__':
    main()
