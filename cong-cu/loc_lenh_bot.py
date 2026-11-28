# -*- coding: utf-8 -*-
"""Lọc lệnh luật bot bằng mô hình (meta-labeling, López de Prado 2018). Cách đo, bốn biến thể và cổng ghi TRƯỚC ở cong-cu/CHUAN_HOA_DANG_KY.md
(phần "Lọc lệnh luật bot bằng mô hình").

Mô hình không đoán chiều giá: nó học từ đặc trưng lúc vào xem lệnh nào của luật bot nên bỏ. Chọn biến thể trên 2015–2021 bằng kiểm định chéo
có tách khoảng (purged k-fold + embargo); kiểm một lần trên 2022–11/2026 và so với lọc ngẫu nhiên cùng số lệnh. Chỉ ĐO: bot Telegram và EA không bị
sửa; mã của bot chỉ bị bọc tạm trong bộ nhớ (như cong-cu/diem_vao_bot.py). Chỉ đọc tệp nến; không nối MT5. Kết quả ở out/loc-lenh-bot.json và .txt.

    python -X utf8 cong-cu/loc_lenh_bot.py
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))

NGAY = 24 * 3600 * 10 ** 9
EMBARGO = NGAY                    # nới 1 ngày mỗi bên khi bỏ lệnh chồng lấn khỏi phần học
SO_KHOI = 5
GIU = (0.5, 0.3)                  # giữ 50% hoặc 30% lệnh có xác suất thắng dự báo cao nhất
TOI_THIEU = 100
LAN_NGAU_NHIEN = 2000
CAT_NAM = 2022


def _nap(ten: str):
    spec = importlib.util.spec_from_file_location(ten, GOC / 'cong-cu' / f'{ten}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---- các hàm lõi (có bài kiểm ở tests/test_loc_lenh_bot.py) ----
def khoi_tach(t_vao: np.ndarray, t_ra: np.ndarray, so_khoi: int = SO_KHOI, embargo: int = EMBARGO) -> list[tuple[np.ndarray, np.ndarray]]:
    """Kiểm định chéo có tách khoảng: chia các lệnh (đã xếp theo giờ vào) thành `so_khoi` khối liên tiếp. Với mỗi khối kiểm, phần học là mọi lệnh
    khác mà khoảng [vào, ra] KHÔNG chạm khoảng [vào đầu − embargo, ra cuối + embargo] của khối kiểm. Trả [(chỉ số học, chỉ số kiểm)]."""
    n = len(t_vao)
    assert np.all(np.diff(t_vao) >= 0), 'lệnh phải xếp theo giờ vào'
    ra = []
    for k in np.array_split(np.arange(n), so_khoi):
        a, b = t_vao[k].min() - embargo, t_ra[k].max() + embargo
        cham = (t_ra >= a) & (t_vao <= b)
        hoc = np.where(~cham)[0]
        ra.append((hoc, k))
    return ra


def nguong(p: np.ndarray, giu: float) -> float:
    """Ngưỡng xác suất để giữ phần `giu` lệnh có xác suất cao nhất."""
    return float(np.quantile(p, 1 - giu))


def p_ngau_nhien(r: np.ndarray, so_giu: int, r_mo_hinh: float, lan: int = LAN_NGAU_NHIEN, hat: int = 0) -> float:
    """Tỷ lệ lần (trong `lan` lần chọn ngẫu nhiên `so_giu` lệnh từ `r`) mà R mỗi lệnh từ mức `r_mo_hinh` trở lên."""
    g = np.random.default_rng(hat)
    tb = np.array([r[g.choice(len(r), so_giu, replace=False)].mean() for _ in range(lan)])
    return float((tb >= r_mo_hinh - 1e-12).mean())


def so_do(r: np.ndarray) -> dict:
    if not len(r):
        return {'n': 0, 'thang': None, 'r_tb': None, 'tong': 0.0, 'dd': 0.0}
    luy = np.r_[0.0, np.cumsum(r)]
    return {'n': int(len(r)), 'thang': round(float((r > 0).mean() * 100), 1), 'r_tb': round(float(r.mean()), 4), 'tong': round(float(r.sum()), 1),
            'dd': round(float((np.maximum.accumulate(luy) - luy).max()), 1)}


def mo_hinh(ten: str):
    from sklearn.ensemble import HistGradientBoostingClassifier       # noqa: PLC0415
    from sklearn.linear_model import LogisticRegression                # noqa: PLC0415
    from sklearn.pipeline import make_pipeline                         # noqa: PLC0415
    from sklearn.preprocessing import StandardScaler                   # noqa: PLC0415
    if ten == 'logistic':
        return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=50, l2_regularization=1.0,
                                          early_stopping=False, random_state=0)


# ---- đặc trưng lúc vào ----
def dac_trung(th: list, ket: list, D: dict, m15: pd.DataFrame, MH, DV) -> pd.DataFrame:
    """Một dòng cho mỗi lệnh: đặc trưng chỉ dùng nến M15 đã đóng trước giờ vào (th[i]['i'] là nến M15 cuối cùng đã đóng) và thông tin có lúc vào."""
    f = MH.bang_nen(m15)
    atr_tb = f['atr'].rolling(480, min_periods=100).mean()
    rows = []
    for s, x in zip(th, ket):
        i, dau = s['i'], (1.0 if s['huong'] == 'MUA' else -1.0)
        t = pd.Timestamp(s['t'])
        j = int(np.searchsorted(D['T'], t.value, side='left'))
        atr = float(f['atr'].iloc[i])
        gio = t.hour + t.minute / 60
        tv = D['S_tv'][j] if j < len(D['S_tv']) else np.nan
        rows.append({'cach_ema50': dau * f['cach_ema50'].iloc[i], 'rsi': dau * f['rsi'].iloc[i], 'vi_tri_24h': dau * f['vi_tri_24h'].iloc[i],
                     'di_4h': dau * f['di_4h'].iloc[i], 'than_nen': dau * f['than_nen'].iloc[i], 'bien_nen': f['bien_nen'].iloc[i],
                     'atr_so_tb': atr / atr_tb.iloc[i] if atr_tb.iloc[i] > 0 else np.nan, 'rui_atr': abs(s['vao'] - s['sl']) / atr if atr > 0 else np.nan,
                     'gio_sin': np.sin(2 * np.pi * gio / 24), 'gio_cos': np.cos(2 * np.pi * gio / 24), 'thu': t.day_of_week,
                     'm5': 1.0 if s.get('khung') == 'M5' else 0.0, 'mua': dau, 'spread_so_tv': (D['S'][j] / tv) if (j < len(D['S']) and tv and np.isfinite(tv)) else np.nan,
                     'gan_tin': 1.0 if DV.gan_tin(D, t.value, 60 * DV.PHUT) else 0.0})
    return pd.DataFrame(rows)


def oof(ten: str, X: np.ndarray, y: np.ndarray, khoi: list) -> np.ndarray:
    """Xác suất thắng dự báo ngoài mẫu cho từng lệnh của phần học (mỗi lệnh được dự báo bởi mô hình không học nó và không học lệnh chồng lấn)."""
    p = np.full(len(y), np.nan)
    for hoc, kiem in khoi:
        m = mo_hinh(ten).fit(X[hoc], y[hoc])
        p[kiem] = m.predict_proba(X[kiem])[:, 1]
    return p


def nap(cfg: dict, den: str | None = None) -> dict:
    """Nạp mọi thứ phép đo cần: nến 1 phút từ 2015, các khung, mảng mô phỏng, và các mô-đun đo. Chỉ đọc tệp nến; không nối MT5."""
    DV, DB = _nap('diem_vao'), _nap('diem_vao_bot')
    from so_cong_khai import gia, hoc, mo_hinh as MH                  # noqa: PLC0415
    g = cfg['gia']
    gia._nap_ma(g)
    m1 = hoc._m1_dai(g, 2015)
    if den:                                                             # cắt nến tới mốc cuối của một lần đo cũ (phép tự đối chiếu)
        m1 = m1[m1.index <= pd.Timestamp(den)]
    fr = hoc._khung(m1, g)
    sp0 = float(g.get('spread', 0.17))
    D = DV.du_lieu(m1, DV.nap_spread(g, m1.index, sp0), gia.tin_usd(g)[0] if g.get('lich_tin') else [])
    return {'cfg': cfg, 'g': g, 'm1': m1, 'fr': fr, 'sp0': sp0, 'D': D, 'DV': DV, 'DB': DB, 'MH': MH}


def lenh_bot(ctx: dict) -> dict:
    """Lệnh của luật bot (bộ kiểm của bot, mã của bot chỉ bị bọc tạm), chấm bằng phép mô phỏng chung (vào ngay, thang sáu mức), xếp theo giờ vào,
    kèm đặc trưng lúc vào. Lệnh thiếu đặc trưng bị bỏ. 'th_all': mọi tín hiệu trước khi chấm (để chấm thêm biến thể khác)."""
    DV, DB, D, fr = ctx['DV'], ctx['DB'], ctx['D'], ctx['fr']
    from tinhieu import levels as LV                                    # noqa: PLC0415 - mã của chủ dự án, chỉ đọc
    khung = tuple((ctx['cfg'].get('kiem_chung') or {}).get('khung_bot', ('M5', 'M15')))
    lenh, sig = DB.lenh_cua_bot(ctx['g'], ctx['m1'], fr['D1'], ctx['sp0'], khung)
    th_all = DB.thanh_tin_hieu(lenh, sig, D, fr['M15'], LV.TP_R)
    th, ket = [], []
    for s in th_all:
        x = DV.mo_phong(D, s, 'bot', tp='TL')
        if x['khop']:
            th.append(s)
            ket.append(x)
    thu_tu = np.argsort([x['t_vao'] for x in ket], kind='stable')
    th, ket = [th[k] for k in thu_tu], [ket[k] for k in thu_tu]
    r = np.array([x['r'] for x in ket])
    t_vao, t_ra = np.array([x['t_vao'] for x in ket], dtype=np.int64), np.array([x['t_ra'] for x in ket], dtype=np.int64)
    F = dac_trung(th, ket, D, fr['M15'], ctx['MH'], DV)
    tot = F.notna().all(axis=1).to_numpy()
    return {'th_all': th_all, 'n_khop': len(th), 'n_thieu': int((~tot).sum()), 'th': [x for x, k in zip(th, tot) if k], 'F': F[tot].reset_index(drop=True),
            'X': F[tot].to_numpy(dtype=float), 'r': r[tot], 'y': (r[tot] > 0).astype(int), 't_vao': t_vao[tot], 't_ra': t_ra[tot],
            'nam': np.array([pd.Timestamp(x, unit='ns').year for x in t_vao[tot]]), 'den': ctx['m1'].index[-1].isoformat()}


def huan_luyen(L: dict) -> dict:
    """Bốn biến thể đã đăng ký, học trên phần trước năm CAT_NAM: {'logistic_50': {'mo_hinh', 'nguong', 'p_oof', 'giu_oof'}, …}."""
    hoc_m = L['nam'] < CAT_NAM
    khoi = khoi_tach(L['t_vao'][hoc_m], L['t_ra'][hoc_m])
    Xh, yh = L['X'][hoc_m], L['y'][hoc_m]
    ra = {}
    for ten in ('logistic', 'cay'):
        p_oof = oof(ten, Xh, yh, khoi)
        m = mo_hinh(ten).fit(Xh, yh)
        for giu in GIU:
            ng = nguong(p_oof, giu)
            ra[f'{ten}_{int(giu * 100)}'] = {'mo_hinh': m, 'nguong': ng, 'p_oof': p_oof, 'giu_oof': p_oof >= ng}
    return {'khoi': khoi, 'bien_the': ra}


def danh_gia(L: dict, ten_tep: str = 'loc-lenh-bot', tieu_de: str = 'LỌC LỆNH LUẬT BOT BẰNG MÔ HÌNH (meta-labeling)', t0: float | None = None) -> dict:
    """Chọn biến thể trên phần học, kiểm cổng trên phần kiểm, in và ghi out/<ten_tep>.json và .txt. Dùng chung cho các bộ đặc trưng khác nhau."""
    t0 = t0 or time.time()
    F, r, y, t_vao, t_ra, nam = L['F'], L['r'], L['y'], L['t_vao'], L['t_ra'], L['nam']
    X = F.to_numpy(dtype=float)
    hoc_m, kiem_m = nam < CAT_NAM, nam >= CAT_NAM
    KQ: dict = {'den': L.get('den'), 'dac_trung': list(F.columns), 'n_hoc': int(hoc_m.sum()), 'n_kiem': int(kiem_m.sum()),
                'khong_loc': {'hoc': so_do(r[hoc_m]), 'kiem': so_do(r[kiem_m])}, 'bien_the': {}}
    H = huan_luyen(L)
    khoi = H['khoi']
    KQ['khoi'] = [{'hoc': int(len(a)), 'kiem': int(len(b))} for a, b in khoi]
    Xh, yh, rh = X[hoc_m], y[hoc_m], r[hoc_m]
    Xk, rk = X[kiem_m], r[kiem_m]
    from sklearn.metrics import roc_auc_score                          # noqa: E402
    for k, v in H['bien_the'].items():
        ten, giu, p_oof, m, ng = k.split('_')[0], int(k.split('_')[1]) / 100, v['p_oof'], v['mo_hinh'], v['nguong']
        p_k = m.predict_proba(Xk)[:, 1]
        if True:
            a, b = p_oof >= ng, p_k >= ng
            KQ['bien_the'][f'{ten}_{int(giu * 100)}'] = {'nguong': round(ng, 4), 'auc_oof': round(float(roc_auc_score(yh, p_oof)), 3),
                                                       'auc_kiem': round(float(roc_auc_score(y[kiem_m], p_k)), 3),
                                                       'hoc_oof': so_do(rh[a]), 'kiem': so_do(rk[b]), '_giu_kiem': b.tolist()}
    hop = {k: v for k, v in KQ['bien_the'].items() if v['hoc_oof']['n'] >= TOI_THIEU}
    chon = max(hop, key=lambda k: hop[k]['hoc_oof']['r_tb']) if hop else None
    KQ['chon'] = chon
    if chon:
        v = KQ['bien_the'][chon]
        giu_k = np.array(v['_giu_kiem'])
        p = p_ngau_nhien(rk, int(giu_k.sum()), v['kiem']['r_tb']) if v['kiem']['n'] else 1.0
        kl = KQ['khong_loc']['kiem']
        dat = {'du_lenh': v['kiem']['n'] >= TOI_THIEU, 'r_cao_hon': bool(v['kiem']['n'] and v['kiem']['r_tb'] > kl['r_tb']),
               'thang_cao_hon': bool(v['kiem']['n'] and v['kiem']['thang'] > kl['thang']), 'hon_ngau_nhien': p < 0.05}
        KQ['cong'] = {'p_ngau_nhien': round(p, 4), **dat, 'qua': all(dat.values())}
        KQ['theo_nam'] = {str(yy): {'khong_loc': so_do(rk[nam[kiem_m] == yy]), 'loc': so_do(rk[(nam[kiem_m] == yy) & giu_k])} for yy in sorted(set(nam[kiem_m]))}
    for v in KQ['bien_the'].values():
        v.pop('_giu_kiem')
    dong = lambda x: '—' if not x['n'] else f"{x['n']:5d} lệnh · thắng {x['thang']:5.1f}% · {x['r_tb']:+.3f}R · tổng {x['tong']:+7.1f}R · sụt {x['dd']:5.1f}R"   # noqa: E731
    chu = [f"{tieu_de} · học 2015–2021: {KQ['n_hoc']:,} lệnh · kiểm 2022–2026: {KQ['n_kiem']:,} lệnh",
           f"Khối kiểm định chéo (lệnh học / lệnh kiểm): {[(k['hoc'], k['kiem']) for k in KQ['khoi']]}",
           f"Không lọc   · học: {dong(KQ['khong_loc']['hoc'])}", f"Không lọc   · kiểm: {dong(KQ['khong_loc']['kiem'])}", '']
    for k, v in KQ['bien_the'].items():
        chu.append(f"{k:12s}{' ← chọn' if k == chon else ''}\n   học (ngoài mẫu, AUC {v['auc_oof']}): {dong(v['hoc_oof'])}\n   kiểm (AUC {v['auc_kiem']}):              {dong(v['kiem'])}")
    if chon:
        c = KQ['cong']
        chu.append(f"\nCỔNG ({chon}): đủ {TOI_THIEU} lệnh {c['du_lenh']} · R cao hơn {c['r_cao_hon']} · thắng cao hơn {c['thang_cao_hon']} · "
                   f"hơn lọc ngẫu nhiên {c['hon_ngau_nhien']} (p = {c['p_ngau_nhien']}) → {'QUA CỔNG' if c['qua'] else 'KHÔNG QUA CỔNG'}")
        chu.append('Theo năm (phần kiểm): không lọc | sau lọc')
        for yy, v in KQ['theo_nam'].items():
            chu.append(f"  {yy}: {dong(v['khong_loc'])} | {dong(v['loc'])}")
    else:
        chu.append('\nKhông biến thể nào giữ đủ 100 lệnh trên phần học.')
    txt = '\n'.join(chu).replace('.', ',').replace('cong-cu/loc_lenh_bot,py', 'cong-cu/loc_lenh_bot.py')
    print(txt)
    (GOC / 'out').mkdir(exist_ok=True)
    (GOC / 'out' / f'{ten_tep}.json').write_text(json.dumps(KQ, ensure_ascii=False, indent=1), encoding='utf-8')
    (GOC / 'out' / f'{ten_tep}.txt').write_text(txt + '\n', encoding='utf-8')
    print(f'\nGhi out/{ten_tep}.json và .txt · {time.time() - t0:.0f} giây')
    return KQ


if __name__ == '__main__':
    t0 = time.time()
    ctx = nap(json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8')))
    L = lenh_bot(ctx)
    print(f"{L['n_khop']:,} lệnh khớp · {L['n_thieu']} lệnh thiếu đặc trưng (bỏ) · {time.time() - t0:.0f} giây", flush=True)
    danh_gia(L, t0=t0)
