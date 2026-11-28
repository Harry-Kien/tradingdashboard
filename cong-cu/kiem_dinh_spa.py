# -*- coding: utf-8 -*-
"""Kiểm định SPA (Hansen, 2005) và Reality Check (White, 2000) trên toàn bộ tập luật và phương pháp của webapp.

Câu hỏi: sau khi tính tới việc đã nhìn RẤT NHIỀU luật, chiều và bối cảnh cùng lúc, có cái nào có lãi thật (kỳ vọng lớn hơn 0), hay cái tốt nhất
cũng chỉ là cái may nhất? Chuẩn so sánh là "không vào lệnh" (lãi 0).

Cách làm: mỗi chiến lược là một chuỗi lãi lỗ theo tuần (USD ở 0,01 lot, sau chi phí; tuần không có lệnh tính 0) trên vàng 2015–2026. Lấy mẫu lại
kiểu stationary bootstrap (khối trung bình 4 tuần), dùng CHUNG chỉ số tuần cho mọi chiến lược để giữ nguyên việc chúng thắng thua cùng nhau.
Thống kê là giá trị lớn nhất của (lãi trung bình / sai số chuẩn) trên cả tập. In ba giá trị p của SPA (dưới, nhất quán, trên; giá trị "trên"
tương ứng Reality Check) và, để đối chiếu, giá trị p "ngây thơ" của riêng chiến lược tốt nhất nếu coi như chỉ thử một mình nó.

Hai tập: (1) 11 luật và phương pháp, cả hai chiều gộp và từng chiều: 33 chiến lược; (2) thêm từng chiều trong từng phiên: 121 chiến lược.
Giới hạn: tham số của luật bot và luật ba khung đã được chọn khi nhìn 2024–2026; kiểm định này không tính được phần chọn lựa đó.
Chỉ đọc tệp nến; không nối MT5. Hạt giống cố định.

    python -X utf8 cong-cu/kiem_dinh_spa.py
"""
import importlib.util
import json
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import gia, hoc, kiem_chung, phuong_phap as PP  # noqa: E402

LAN, KHOI = 10000, 4


def spa(d: np.ndarray, idx: np.ndarray) -> dict:
    """d: (số tuần × số chiến lược). idx: (số lần × số tuần) chỉ số lấy mẫu lại. Trả thống kê và ba giá trị p."""
    n = d.shape[0]
    tb = d.mean(0)
    tb_b = np.stack([d[i].mean(0) for i in idx])                      # (số lần × số chiến lược)
    om = np.sqrt(n) * tb_b.std(0)
    om = np.where(om > 0, om, np.inf)
    t = max(0.0, float((np.sqrt(n) * tb / om).max()))
    nguong = -np.sqrt(om ** 2 / n * 2 * np.log(np.log(n)))
    out = {'t': t, 'tot': int(np.argmax(np.sqrt(n) * tb / om))}
    for ten, g in (('duoi', np.maximum(tb, 0)), ('nhat_quan', np.where(tb >= nguong, tb, 0.0)), ('tren', tb)):
        tb_sao = np.maximum(0.0, (np.sqrt(n) * (tb_b - g) / om).max(1))
        out[ten] = float((tb_sao > t).mean())
    k = out['tot']
    out['ngay_tho'] = float(((tb_b[:, k] - tb[k]) >= tb[k]).mean())    # p một phía của riêng chiến lược tốt nhất, coi như chỉ thử mình nó
    return out


def moi_lenh(cfg: dict) -> dict:
    """{mã luật: [{'t', 'huong', 'usd'}]} trên vàng từ 2015, đúng các phép chấm mà webapp dùng."""
    g = cfg['gia']
    gia._nap_ma(g)
    m1 = hoc._m1_dai(g, 2015)
    fr = hoc._khung(m1, g)
    sp = float(g.get('spread', 0.17))
    tin = []
    if g.get('lich_tin'):
        from ai import snapshot as SN                                  # noqa: PLC0415 - mã của chủ dự án, chỉ đọc
        tin, _ = SN.load_high_usd_news(Path(os.path.expandvars(g['lich_tin'])))
        tin = [t for t in tin if m1.index[0] - timedelta(days=1) <= t <= m1.index[-1] + timedelta(days=1)]
    khung_bot = tuple((cfg.get('kiem_chung') or {}).get('khung_bot', ('M5', 'M15')))
    out = {}
    for ma, fn in (('bot', lambda: kiem_chung._bot(g, m1, fr['D1'], sp, khung_bot)), ('ba_khung', lambda: kiem_chung._ba_khung(g, m1, fr, sp, tin)),
                   ('dinh_day', lambda: kiem_chung._dinh_day(g, m1, fr, sp, tin))):
        t0 = time.time()
        out[ma] = [{'t': x['t'], 'huong': x['huong'], 'usd': float(x['usd'])} for x in fn()['lenh']]
        print(f'  {ma}: {len(out[ma]):,} lệnh ({time.time() - t0:.0f} giây)', flush=True)
    for ma in PP.DS:
        out[ma] = [{'t': x['t'], 'huong': x['huong'], 'usd': float(x['usd'])} for x in PP.cham(PP.quet(ma, fr['M15'], fr['H1']), m1, sp)]
        print(f'  {ma}: {len(out[ma]):,} lệnh', flush=True)
    return out


def bang_tuan(lenh: dict) -> tuple[pd.DataFrame, list[str]]:
    """(bảng lãi lỗ theo tuần của mọi chiến lược, tên các cột thuộc tập 1). Tuần không có lệnh tính 0."""
    rows = []
    for ma, ls in lenh.items():
        for x in ls:
            t = pd.Timestamp(x['t'])
            t = t.tz_convert('UTC') if t.tzinfo else t.tz_localize('UTC')
            rows.append((ma, x['huong'], hoc.phien(t), t.tz_localize(None).to_period('W'), x['usd']))
    a = pd.DataFrame(rows, columns=['ma', 'huong', 'phien', 'tuan', 'usd'])
    tuan = pd.period_range(a['tuan'].min(), a['tuan'].max(), freq='W')
    cot = {}
    for ma, x in a.groupby('ma'):
        cot[f'{ma}'] = x.groupby('tuan')['usd'].sum()
        for h, y in x.groupby('huong'):
            cot[f'{ma} {h}'] = y.groupby('tuan')['usd'].sum()
    tap1 = list(cot)
    for (ma, h, ph), y in a.groupby(['ma', 'huong', 'phien']):
        cot[f'{ma} {h} phiên {ph}'] = y.groupby('tuan')['usd'].sum()
    return pd.DataFrame(cot).reindex(tuan).fillna(0.0), tap1


if __name__ == '__main__':
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    spec = importlib.util.spec_from_file_location('kdtk', GOC / 'cong-cu' / 'kiem_dinh_thong_ke.py')
    kd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kd)
    print('Chạy lại 11 luật và phương pháp trên vàng từ 2015:')
    lenh = moi_lenh(cfg)
    d, tap1 = bang_tuan(lenh)
    tuan, cot = d.index, list(d.columns)
    so_lenh = sum(len(v) for v in lenh.values())
    try:                                                              # để cong-cu/doi_chieu_spa.py dùng lại mà không phải chạy lại mọi luật
        (GOC / 'out').mkdir(exist_ok=True)
        d.assign(tuan=[str(x) for x in tuan]).to_csv(GOC / 'out' / 'spa-bang-tuan.csv', index=False)
        (GOC / 'out' / 'spa-tap-1.json').write_text(json.dumps(tap1, ensure_ascii=False), encoding='utf-8')
    except OSError:
        pass
    idx = kd.chi_so_khoi(len(d), LAN, KHOI, np.random.default_rng(20261123))
    print(f'\n{so_lenh:,} lệnh · {len(d)} tuần ({tuan[0]} tới {tuan[-1]}) · {LAN:,} lần lấy mẫu lại, khối trung bình {KHOI} tuần')
    for ten, cs in (('1. Luật và phương pháp, gộp và từng chiều', tap1), ('2. Thêm từng chiều trong từng phiên', list(cot))):
        x = d[cs].to_numpy()
        r = spa(x, idx)
        tot = cs[r['tot']]
        duong = int((x.mean(0) > 0).sum())
        print(f'\n=== {ten}: {len(cs)} chiến lược, {duong} cái có tổng dương ===')
        print(f'  Tốt nhất theo (lãi trung bình / sai số chuẩn): "{tot}" · {d[tot].sum():+.0f} USD cả quãng ở 0,01 lot · {d[tot].mean():+.2f} USD mỗi tuần')
        print(f'  Nếu coi như chỉ thử một mình nó: p = {r["ngay_tho"]:.3f}')
        print(f'  SPA trên cả tập: p dưới = {r["duoi"]:.3f} · p nhất quán = {r["nhat_quan"]:.3f} · p trên (Reality Check) = {r["tren"]:.3f}')
        xep = sorted(cs, key=lambda c: -d[c].mean() / (d[c].std() or np.inf))[:5]
        print('  Năm cái đứng đầu: ' + ' · '.join(f'{c} ({d[c].sum():+.0f})' for c in xep))
