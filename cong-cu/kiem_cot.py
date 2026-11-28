# -*- coding: utf-8 -*-
"""Vị thế COT của quỹ đầu cơ trên vàng tương lai có báo trước được giá vàng tuần sau không?

Câu hỏi đặt TRƯỚC khi nhìn số (không thêm bớt sau khi thấy kết quả), bốn phép so:
  A. Thứ hạng vị thế mua ròng của quỹ trong 156 tuần trước đó: nhóm cao (từ 80% trở lên) so với nhóm thấp (từ 20% trở xuống),
     lợi suất 1 tuần và 4 tuần sau khi báo cáo công bố.
  B. Tuần đó quỹ mua thêm so với quỹ bán bớt (thay đổi vị thế ròng so với tuần trước), lợi suất 1 tuần và 4 tuần sau.
Vì thử bốn phép, ngưỡng có ý nghĩa là p < 0,05 / 4 = 0,0125 (Bonferroni).

Cách tính để không nhìn trước tương lai:
- Báo cáo chốt thứ Ba, công bố thứ Sáu. Coi như chỉ dùng được từ phiên đầu tiên SAU ngày chốt + 3 ngày: vào ở giá mở cửa phiên đó,
  ra ở giá đóng cửa sau 5 phiên (1 tuần) hoặc 20 phiên (4 tuần). Tuần CFTC công bố trễ vì nghỉ lễ thì phép này hơi lạc quan.
- Thứ hạng chỉ dùng các tuần đã có tới lúc đó.
- Các tuần nối nhau không độc lập (nhất là lợi suất 4 tuần chồng lên nhau), nên sai số tính bằng stationary bootstrap
  (Politis và Romano, 1994; khối trung bình 4 tuần cho phép 1 tuần, 8 tuần cho phép 4 tuần), 10.000 lần, hạt giống cố định.

Kèm một dòng mô tả (không phải dự báo): trong cùng tuần chốt, quỹ mua thêm thì giá đã tăng hay giảm.

Chỉ đọc du-lieu/cot-vang.json và tệp nến ngày; không gọi mạng, không nối MT5.

    python -X utf8 cong-cu/kiem_cot.py
"""
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kiem_dinh_thong_ke import chi_so_khoi  # noqa: E402
from so_cong_khai import cot, kiem_chung  # noqa: E402

LAN = 10000


def gia_ngay(g: dict) -> pd.DataFrame:
    """Nến ngày: tệp xuất của MT5, nối thêm phần mới hơn từ kho nến 1 phút."""
    d = pd.read_csv(os.path.expandvars(g['d1_goc']), sep='\t', usecols=[0, 2, 5], names=['d', 'open', 'close'], header=0, dtype={'d': str})
    d.index = pd.to_datetime(d['d'], format='%Y.%m.%d')
    d = d[['open', 'close']].astype(float)
    try:
        m1 = kiem_chung._m1(g)
        m1.index = m1.index.tz_localize(None)
        moi = m1.resample('1D').agg({'open': 'first', 'close': 'last'}).dropna()
        d = pd.concat([d, moi[moi.index > d.index[-1]]])
    except Exception as e:                                                 # noqa: BLE001 - thiếu kho nến thì dùng riêng tệp ngày
        print(f'(không nối được kho nến 1 phút: {type(e).__name__})')
    return d[d.index.day_of_week < 5]


def bang(ds: list[dict], d1: pd.DataFrame) -> pd.DataFrame:
    """Mỗi báo cáo một hàng: thứ hạng, thay đổi vị thế, lợi suất 1 và 4 tuần sau công bố (%), lợi suất trong tuần chốt (%)."""
    ng, op, cl = d1.index.values, d1['open'].to_numpy(), d1['close'].to_numpy()
    r = [cot.rong(x) for x in ds]
    hang = []
    for i, x in enumerate(ds):
        if i < cot.CUA_SO:
            continue
        cs = r[i - cot.CUA_SO + 1:i + 1]
        j = int(np.searchsorted(ng, np.datetime64(date.fromisoformat(x['ngay']) + timedelta(days=3)), side='right'))    # phiên đầu tiên sau ngày công bố
        k0 = int(np.searchsorted(ng, np.datetime64(date.fromisoformat(ds[i - 1]['ngay'])), side='right')) - 1         # phiên chốt của tuần trước
        k1 = int(np.searchsorted(ng, np.datetime64(date.fromisoformat(x['ngay'])), side='right')) - 1                 # phiên chốt của tuần này
        hang.append({'ngay': x['ngay'], 'hang': 100 * sum(c <= r[i] for c in cs) / len(cs), 'doi': r[i] - r[i - 1],
                     'r1': 100 * (cl[j + 4] / op[j] - 1) if j + 4 < len(cl) else np.nan,
                     'r4': 100 * (cl[j + 19] / op[j] - 1) if j + 19 < len(cl) else np.nan,
                     'r0': 100 * (cl[k1] / cl[k0] - 1) if k0 >= 0 and k1 > k0 else np.nan})
    return pd.DataFrame(hang)


def so(t: pd.DataFrame, cot_r: str, a: pd.Series, b: pd.Series, khoi: int, rng) -> dict:
    """Trung bình nhóm a trừ trung bình nhóm b của cột lợi suất, kèm khoảng tin cậy 95% và p hai phía (bootstrap theo khối trên cả dãy tuần)."""
    ok = t[cot_r].notna().to_numpy()
    y, a, b = t[cot_r].to_numpy()[ok], a.to_numpy()[ok], b.to_numpy()[ok]
    idx = chi_so_khoi(len(y), LAN, khoi, rng)
    def hieu(yy, aa, bb):
        return (yy * aa).sum(-1) / np.maximum(aa.sum(-1), 1) - (yy * bb).sum(-1) / np.maximum(bb.sum(-1), 1)
    goc = float(hieu(y, a, b))
    bs = hieu(y[idx], a[idx], b[idx])
    return {'n_a': int(a.sum()), 'n_b': int(b.sum()), 'tb_a': float(y[a].mean()), 'tb_b': float(y[b].mean()), 'hieu': goc,
            'ci': [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], 'p': float((np.abs(bs - bs.mean()) >= abs(goc)).mean())}


if __name__ == '__main__':
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    ds = cot._doc(cot.tep(cfg))['ds']
    if len(ds) < cot.CUA_SO + 100:
        sys.exit('Chưa đủ dữ liệu COT trong du-lieu/cot-vang.json; mở webapp một lần để nó tải về.')
    t = bang(ds, gia_ngay(cfg['gia']))
    rng = np.random.default_rng(20261123)
    f = lambda x: f'{x:+.2f}'.replace('.', ',')                                                    # noqa: E731
    print(f'COT vàng COMEX: {len(ds)} tuần từ {ds[0]["ngay"]} tới {ds[-1]["ngay"]}. Xét được {t["r1"].notna().sum()} tuần (từ {t["ngay"].iloc[0]}), sau khi dành {cot.CUA_SO} tuần đầu để xếp hạng.')
    print(f'Lợi suất trung bình của vàng trong quãng này, không điều kiện gì: 1 tuần {f(t["r1"].mean())}% · 4 tuần {f(t["r4"].mean())}%')
    kq = {}
    for ten, a, b, nhan in (('A', t['hang'] >= 80, t['hang'] <= 20, ('quỹ mua ròng ở nhóm cao (≥80%)', 'quỹ mua ròng ở nhóm thấp (≤20%)')),
                            ('B', t['doi'] > 0, t['doi'] < 0, ('quỹ mua thêm trong tuần', 'quỹ bán bớt trong tuần'))):
        for cot_r, khoi, ky in (('r1', 4, '1 tuần sau'), ('r4', 8, '4 tuần sau')):
            k = so(t, cot_r, a, b, khoi, rng)
            kq[f'{ten}_{cot_r}'] = k
            print(f'{ten} · {ky}: {nhan[0]} {k["n_a"]} tuần, tb {f(k["tb_a"])}% · {nhan[1]} {k["n_b"]} tuần, tb {f(k["tb_b"])}% · '
                  f'hiệu {f(k["hieu"])} điểm % · khoảng tin cậy 95% [{f(k["ci"][0])}; {f(k["ci"][1])}] · p = {k["p"]:.3f}'.replace('p = 0.', 'p = 0,'))
    nho = min(k['p'] for k in kq.values())
    print(f'p nhỏ nhất trong bốn phép: {f"{nho:.3f}".replace(".", ",")}; ngưỡng sau khi tính tới bốn phép thử: 0,0125 → ' + ('CÓ phép vượt ngưỡng.' if nho < 0.0125 else 'KHÔNG phép nào vượt ngưỡng.'))
    cung = t.dropna(subset=['r0'])
    print(f'Mô tả, không phải dự báo: trong chính tuần chốt, tương quan hạng (Spearman) giữa thay đổi vị thế của quỹ và lợi suất vàng tuần đó = '
          f'{cung["doi"].corr(cung["r0"], method="spearman"):+.2f}; quỹ mua thêm ở {100 * ((cung["doi"] > 0) & (cung["r0"] > 0)).sum() / max((cung["r0"] > 0).sum(), 1):.0f}% số tuần giá tăng '
          f'và ở {100 * ((cung["doi"] > 0) & (cung["r0"] < 0)).sum() / max((cung["r0"] < 0).sum(), 1):.0f}% số tuần giá giảm.')
    (GOC / 'out').mkdir(exist_ok=True)
    (GOC / 'out' / 'kiem-cot.json').write_text(json.dumps({'tuan': int(t['r1'].notna().sum()), 'tu': t['ngay'].iloc[0], 'toi': ds[-1]['ngay'], 'kq': kq}, ensure_ascii=False, indent=1), encoding='utf-8')
