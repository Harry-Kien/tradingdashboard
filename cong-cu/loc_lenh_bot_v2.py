# -*- coding: utf-8 -*-
"""Lọc lệnh luật bot bằng mô hình, bản 2: giữ nguyên bản 1 (cong-cu/loc_lenh_bot.py) và thêm 7 đặc trưng liên thị trường: bạc, tỷ lệ vàng/bạc, dầu
Brent, S&P 500, vị thế quỹ đầu cơ trong báo cáo COT. Cách đo và cổng ghi TRƯỚC ở cong-cu/CHUAN_HOA_DANG_KY.md (phần "bản 2").

Mọi đặc trưng chỉ dùng nến đã đóng (hoặc bản tin COT đã phát hành) trước lúc vào lệnh. Chỉ ĐO: bot không bị sửa. Chỉ đọc tệp; không nối MT5.
Kết quả ở out/loc-lenh-bot-v2.json và .txt.

    python -X utf8 cong-cu/loc_lenh_bot_v2.py
"""
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
THO = Path(os.environ.get('HGR_RAW_DATA', 'data/raw'))
MOI = ['bac_di_4h', 'vang_bac_cung', 'ty_le_vb_z', 'brent_di_1d', 'spx_di_5d', 'cot_mm_pct', 'cot_mm_doi']


def _nap(ten: str):
    spec = importlib.util.spec_from_file_location(ten, GOC / 'cong-cu' / f'{ten}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def doc_tho(ten: str) -> pd.Series:
    """Giá đóng của tệp MT5 xuất ra, chỉ số là giờ ĐÓNG nến (giờ mở + độ dài), cùng mốc giờ với nến vàng của webapp."""
    df = pd.read_csv(THO / f'{ten}.csv', sep='\t')
    t = pd.to_datetime(df['<DATE>'] + ' ' + df['<TIME>'], format='%Y.%m.%d %H:%M:%S').dt.tz_localize('UTC')
    dai = pd.Timedelta('1D') if ten.endswith('_D1') else pd.Timedelta('1h')
    return pd.Series(df['<CLOSE>'].to_numpy(dtype=float), index=t + dai).sort_index().loc[lambda s: ~s.index.duplicated()]


def truoc(s: pd.Series, t: pd.DatetimeIndex) -> np.ndarray:
    """Giá trị cuối cùng của `s` có chỉ số ≤ từng mốc trong `t` (NaN nếu chưa có)."""
    k = s.index.searchsorted(t, side='right') - 1
    v = np.where(k >= 0, s.to_numpy()[np.clip(k, 0, None)], np.nan)
    return v.astype(float)


def dac_trung_moi(t_vao: np.ndarray, mua: np.ndarray, vang_h1: pd.Series, cot: list) -> pd.DataFrame:
    """7 đặc trưng liên thị trường tại các mốc vào lệnh `t_vao` (ns, UTC); thiếu thì 0."""
    t = pd.DatetimeIndex(pd.to_datetime(t_vao, utc=True))
    dau = np.where(mua, 1.0, -1.0)
    bac = doc_tho('XAGUSDp_H1')
    brent = doc_tho('BRENTp_H1')
    spx = doc_tho('US500p_D1')
    di = lambda s, lui: (s / s.shift(lui) - 1) * 100                                    # noqa: E731 - đà theo số nến
    bac4, vang4 = truoc(di(bac, 4), t), truoc(di(vang_h1, 4), t)
    vb = (vang_h1.reindex(bac.index, method='ffill') / bac).resample('1D').last().dropna()
    vb.index = vb.index + pd.Timedelta('1D')                                            # giá trị của một ngày chỉ dùng được sau khi ngày đó hết
    vb_z = (vb - vb.rolling(60, min_periods=40).mean()) / vb.rolling(60, min_periods=40).std()
    F = pd.DataFrame({'bac_di_4h': dau * bac4, 'vang_bac_cung': (np.sign(bac4) == np.sign(vang4)).astype(float),
                      'ty_le_vb_z': dau * truoc(vb_z, t), 'brent_di_1d': dau * truoc(di(brent, 24), t), 'spx_di_5d': dau * truoc(di(spx, 5), t)})
    F.loc[np.isnan(bac4) | np.isnan(vang4), 'vang_bac_cung'] = 0.0
    c = pd.DataFrame(cot)
    c['luc'] = pd.to_datetime(c['ngay']).dt.tz_localize('UTC') + pd.Timedelta(days=4)  # thứ Ba chốt số → dùng từ 00:00 thứ Bảy
    c = c.sort_values('luc').set_index('luc')
    pct = (c['mm_mua'] - c['mm_ban']) / c['oi'] * 100
    F['cot_mm_pct'] = dau * truoc(pct, t)
    F['cot_mm_doi'] = dau * truoc(pct.diff(), t)
    return F[MOI].replace([np.inf, -np.inf], np.nan).fillna(0.0)


if __name__ == '__main__':
    LB = _nap('loc_lenh_bot')
    t0 = time.time()
    ctx = LB.nap(json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8')))
    L = LB.lenh_bot(ctx)
    m1 = ctx['m1']
    vang_h1 = m1['close'].resample('1h').last().dropna()
    vang_h1.index = vang_h1.index + pd.Timedelta('1h')                                 # chỉ số là giờ đóng nến, như doc_tho
    cot = json.loads((GOC / 'du-lieu' / 'cot-vang.json').read_text(encoding='utf-8'))['ds']
    mua = np.array([s['huong'] == 'MUA' for s in L['th']])
    Fm = dac_trung_moi(L['t_vao'], mua, vang_h1, cot)
    thieu = {k: int((Fm[k] == 0).sum()) for k in MOI}
    print(f"{len(L['r']):,} lệnh · số lệnh có đặc trưng mới bằng 0 (thiếu dữ liệu hoặc đúng 0): {thieu} · {time.time() - t0:.0f} giây", flush=True)
    L2 = dict(L, F=pd.concat([L['F'], Fm], axis=1))
    L2['X'] = L2['F'].to_numpy(dtype=float)
    KQ = LB.danh_gia(L2, 'loc-lenh-bot-v2', 'LỌC LỆNH LUẬT BOT BẰNG MÔ HÌNH, BẢN 2 (thêm bạc, Brent, S&P 500, COT)', t0)
    try:
        v1 = json.loads((GOC / 'out' / 'loc-lenh-bot.json').read_text(encoding='utf-8'))
        print('\nAUC so với bản 1 (cùng lệnh; chỉ để tham khảo, không dùng để chọn):')
        for k in KQ['bien_the']:
            a, b = v1['bien_the'][k], KQ['bien_the'][k]
            print(f"  {k:12s} ngoài mẫu phần học {a['auc_oof']} → {b['auc_oof']} · phần kiểm {a['auc_kiem']} → {b['auc_kiem']}".replace('.', ','))
    except (OSError, KeyError, ValueError):
        pass
