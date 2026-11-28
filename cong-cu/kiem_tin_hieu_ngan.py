"""Đo bộ quét M5/M15/M30 trên kho XAUUSD; kết quả hồi cứu, không chọn lại tham số."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from so_cong_khai import gia, hoc, tin_hieu_ngan as T  # noqa: E402


def mo_phong(ds, m1, spread, news, phut: int, *, hoi_ema: bool) -> tuple[pd.DataFrame, int]:
    """Vào ở phút kế, mô phỏng riêng theo khung. Một vị thế mô phỏng đồng thời mỗi khung."""
    t = m1.index.as_unit('ns').asi8
    o, h, l, c = (m1[k].to_numpy() for k in ('open', 'high', 'low', 'close'))
    buoc = pd.Timedelta(minutes=1).value
    loc = ds['phia'].ne(0) & (True if hoi_ema else ds['loai'].eq('pha_vo'))
    rows = []
    rong = pd.Timedelta(minutes=15).value
    da_dong = -1
    for r in ds[loc].itertuples():
        dong = (r.Index + pd.Timedelta(minutes=phut)).value
        n = int(news.searchsorted(dong - rong))
        if dong <= da_dong or (n < len(news) and news[n] <= dong + rong):
            continue
        j = int(t.searchsorted(dong))
        if j >= len(t) or t[j] != dong:
            continue
        bid, ask = o[j], o[j] + spread[j]
        tt, x = T.muc_gia(r, bid, ask, .01, 2)
        if tt != 'dat':
            continue
        han = dong + 12 * phut * buoc
        k = min(int(t.searchsorted(han)), len(t))
        if k == len(t):
            break  # dữ liệu chưa đủ để chấm hết thời gian nắm giữ
        mua = r.phia > 0
        cao = h[j:k] if mua else h[j:k] + spread[j:k]
        thap = l[j:k] if mua else l[j:k] + spread[j:k]
        sl, tp, vao = (x[a] for a in ('sl', 'tp', 'vao'))
        cham_sl = thap <= sl if mua else cao >= sl
        cham_tp = cao >= tp if mua else thap <= tp
        dung = np.flatnonzero(cham_sl | cham_tp)
        if len(dung):
            i = dung[0]
            kq = j + i
            mo = o[kq] if mua else o[kq] + spread[kq]
            # Ưu tiên giá mở khi nhảy qua SL; nến chạm cả hai mức chấm SL.
            ra = (min(mo, sl) if mua else max(mo, sl)) if cham_sl[i] else tp
        else:
            kq = k - 1
            ra = c[kq] if mua else c[kq] + spread[kq]
        da_dong = t[kq]
        # XAUUSD 0,01 lot chuẩn = 1 oz. Phí 0,18 và trượt giá giả định 0,10 giá/lượt khứ hồi.
        net = (ra - vao) * r.phia - .18 - .10
        rows.append((r.Index.year, r.loai, net / abs(vao - sl)))
    return pd.DataFrame(rows, columns=['nam', 'loai', 'r']), int(loc.sum())


def tom(df):
    r = df['r']
    loi, lo = r[r > 0].sum(), r[r < 0].sum()
    von = np.r_[0., r.cumsum()]
    return {'so': len(r), 'thang_pct': round(float(r.gt(0).mean()) * 100, 2) if len(r) else None,
            'r_moi_lenh': round(float(r.mean()), 4) if len(r) else None,
            'pf': round(float(loi / -lo), 3) if lo else None, 'dd_r': round(float((np.maximum.accumulate(von) - von).max()), 2)}


def _huong_da_dong(b, gio, moc):
    z = T._ema(b['close'], 20) - T._ema(b['close'], 50)
    z.index += pd.Timedelta(hours=gio)
    return z.reindex(moc, method='ffill', tolerance=pd.Timedelta(hours=2 * gio)).to_numpy()


def phu(d, fr, phut, m1, spread, news):
    """Kiểm ba giả thuyết lọc riêng. Không dùng các kết quả này để chọn tham số live."""
    dong = d.index + pd.Timedelta(minutes=phut)
    h4 = _huong_da_dong(fr['H4'], 4, dong)
    d1 = _huong_da_dong(fr['D1'], 24, dong)
    cung_h4 = d['phia'] * h4 > 0
    cac_loc = {'cung_h4': cung_h4, 'cung_h4_va_d1': cung_h4 & (d['phia'] * d1 > 0),
               'cung_h4_trong_phien_07_19_utc': cung_h4 & (dong.hour >= 7) & (dong.hour < 19)}
    kq = {}
    for ten, hop in cac_loc.items():
        df, dem = mo_phong(d[hop], m1, spread, news, phut, hoi_ema=True)
        kq[ten] = {**tom(df), 'thiet_lap': dem,
                   'chia_quang': {f'{a}-{b}': tom(df[df['nam'].between(a, b)]) for a, b in ((2015, 2021), (2022, 2024), (2025, 2026))}}
    return kq


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tu-nam', type=int, default=2015)
    parser.add_argument('--ra', type=Path, default=ROOT / 'out' / 'tin-hieu-ngan.json')
    args = parser.parse_args()
    cfg = json.loads((ROOT / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    m1 = hoc._m1_dai(g, args.tu_nam)
    fr = hoc._khung(m1, g)
    # Dùng cùng hàm spread lịch sử và đánh giá lệnh của báo cáo chất lượng.
    from diem_vao import nap_spread

    spread = nap_spread(g, m1.index, float(g.get('spread', .17)))
    spread = np.where(np.isfinite(spread) & (spread > 0), spread, float(g.get('spread', .17)))
    tin, _ = gia.tin_usd(g) if g.get('lich_tin') else ([], None)
    news = np.array(sorted(pd.Timestamp(t).value for t in tin), dtype=np.int64)
    kq = {'phien_ban': T.PHIEN_BAN, 'ma': 'XAUUSD', 'm1': len(m1), 'tu': m1.index[0].isoformat(), 'den': m1.index[-1].isoformat(),
          'gia_dinh': {'so_tin': len(news), 'phi_001': .18, 'truot_gia_khu_hoi': .10, 'toi_da_so_nen_nam_giu': 12,
                       'spread_du_phong': float(g.get('spread', .17)), 'phan_doan_gia_su': 'Hồi cứu, các năm đã từng được dùng nghiên cứu trong dự án'},
          'khung': {}}
    for tf, phut in T.KHUNG.items():
        d = T.dieu_kien(fr[tf], fr['H1'], tf)
        a, sa = mo_phong(d, m1, spread, news, phut, hoi_ema=False)
        b, sb = mo_phong(d, m1, spread, news, phut, hoi_ema=True)
        kq['khung'][tf] = {'chi_pha_vo': {**tom(a), 'thiet_lap': sa}, 'ca_hai': {**tom(b), 'thiet_lap': sb},
                           'chia_quang': {f'{x}-{y}': tom(b[b['nam'].between(x, y)]) for x, y in ((2015, 2021), (2022, 2024), (2025, 2026))},
                           'tung_loai': {k: tom(b[b['loai'].eq(k)]) for k in T.LOAI},
                           'loc_khao_sat': phu(d, fr, phut, m1, spread, news)}
        print(tf, tom(b), [(k, z['r_moi_lenh']) for k, z in kq['khung'][tf]['loc_khao_sat'].items()], flush=True)
    args.ra.parent.mkdir(parents=True, exist_ok=True)
    args.ra.write_text(json.dumps(kq, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
