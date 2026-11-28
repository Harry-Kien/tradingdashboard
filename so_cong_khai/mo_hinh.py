"""Điểm mô hình (thử nghiệm): một mô hình hồi quy logistic học từ mọi tín hiệu của tám phương pháp trên vàng từ 2015, để XẾP HẠNG một điểm vào
so với các tín hiệu trong quá khứ (0–100; càng cao thì trong quá khứ nhóm đó càng hay chạm 2R trước dừng lỗ).

Mức đã kiểm được (cong-cu/huan_luyen.py; học 2015–2021, kiểm trên 2022–2026 là quãng mô hình chưa thấy): nhóm 10% điểm cao nhất tốt hơn mặt
bằng chung khoảng 0,1R mỗi lệnh ở cả năm năm, nhưng tính chung nhóm đó mới quanh hòa vốn. Vì vậy đây là một con số để tham khảo và để nhật ký
điểm vào kiểm chứng bằng giá thật, KHÔNG phải tín hiệu vào lệnh. Mô hình chỉ học trên vàng nên chỉ chấm điểm cho vàng.

Từ 27/11/2026, kiem_cuon_chieu() là phép đánh giá ưu tiên: chỉ học quá khứ, bỏ 4 ngày nhãn sát phần kiểm, rồi kiểm phần kế tiếp.
Đo trên 69.959 tín hiệu: nhóm điểm cao nhất trung bình −0,038R, có lãi 2/6 phần, AUC 0,519. Chưa đủ bằng chứng để tự gọi lệnh bằng mô hình.

Để đối chiếu, kiem_cheo() kiểm chéo 6 phần theo thời gian, bỏ khỏi phần học các tín hiệu có kết quả chồng lên phần kiểm và
một vùng cấm sau nó (purged CV). Phép này có học dữ liệu sau phần kiểm, không mô phỏng triển khai theo thời gian. Đo ngày 25/11/2026 trên 69.902 tín hiệu: nhóm 10% cao nhất tốt hơn mặt bằng ở 6/6 phần (−0,02R so với
−0,15R mỗi lệnh) nhưng chỉ có lãi ở 1/6 phần, AUC 0,524; không loại chồng lấn thì gần như y hệt, tức mô hình không ăn nhờ rò rỉ.

Huấn luyện cần scikit-learn (đã có sẵn trên máy); chấm điểm lúc chạy chỉ cần numpy. Chỉ đọc tệp nến; không nối MT5, không đặt lệnh.
"""
from __future__ import annotations

import importlib.util
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import gia, hoc, phuong_phap as PP
from .__main__ import HERE

PHIEN_BAN = 11                     # 11: kiểm cuốn chiếu chỉ học quá khứ; 10: purged CV
NGUONG = 90                # điểm từ mức này trở lên là "nhóm 10% cao nhất" đã được kiểm ngoài mẫu
TPS = (0.25, 0.5, 1.0, 1.5, 2.0, 3.0)       # các mức chốt lời được đo, tính theo bội số của khoản rủi ro
HOC_TOI = 2021             # phép kiểm ngoài mẫu: mô hình chỉ học tới hết năm này, rồi được chấm trên các năm sau
DAC = ['rui_atr', 'bien_do', 'gio_sin', 'gio_cos', 'thu', 'thuan_h1', 'thuan_d1', 'cach_ema50', 'rsi', 'vi_tri_24h', 'di_4h', 'than_nen', 'bien_nen', 'cho', 'dt_cung', 'dt_nguoc']
CV_K = 6                   # số phần của phép kiểm chéo theo thời gian
H_NHAN = pd.Timedelta(days=4)  # kết quả một tín hiệu biết được sau tối đa 4 giờ chờ khớp + 1.440 nến 1 phút (qua cuối tuần thì dài hơn 1 ngày)
CAM_TY_LE = 0.01           # vùng cấm sau phần kiểm: 1% độ dài dữ liệu (ít nhất H_NHAN), vì đặc trưng dùng cửa sổ quá khứ dài (EMA200 D1, 24 giờ)
_khoa = threading.Lock()
_tt: dict = {'key': None, 'kq': None, 'dang': False, 'loi': None}


def cot() -> list[str]:
    return DAC + [f'pp_{m}' for m in PP.DS]


def bang_nen(m15: pd.DataFrame) -> pd.DataFrame:
    """Đặc trưng của từng nến M15, chỉ dùng nến đó trở về trước (không nhìn tương lai)."""
    c, atr = m15['close'], PP._atr(m15)
    f = pd.DataFrame(index=m15.index)
    f['atr'] = atr
    f['cach_ema50'] = (c - c.ewm(span=50, adjust=False, min_periods=50).mean()) / atr
    f['rsi'] = gia.rsi_wilder(c) - 50
    cao, thap = m15['high'].rolling(96).max(), m15['low'].rolling(96).min()
    f['vi_tri_24h'] = (c - thap) / (cao - thap) - 0.5
    f['di_4h'] = (c - c.shift(16)) / atr
    f['than_nen'] = (c - m15['open']) / atr
    f['bien_nen'] = (m15['high'] - m15['low']) / atr
    return f


def _xu_d1(d1: pd.DataFrame) -> pd.Series:
    return np.sign(d1['close'] - d1['close'].ewm(span=200, adjust=False, min_periods=200).mean()).shift(1)       # D1 hôm trước: giá so với EMA200


def _bang(f: pd.DataFrame, h1: pd.DataFrame, d1: pd.DataFrame, t: pd.DatetimeIndex, dau: np.ndarray, rui: np.ndarray, ma: str) -> pd.DataFrame:
    """Bảng đặc trưng cho các tín hiệu đóng nến lúc `t` (chiều `dau` = ±1, rủi ro `rui` theo giá) của phương pháp `ma`.
    Đặc trưng có chiều được nhân với chiều lệnh: dương nghĩa là thuận chiều lệnh."""
    x = f.reindex(t - pd.Timedelta(minutes=15))                    # nến tín hiệu mở trước giờ đóng 15 phút
    ti = hoc.ty_le_bien_do(h1).dropna()
    k = ti.index.searchsorted(t - pd.Timedelta(hours=1), side='right') - 1
    xd = np.nan_to_num(_xu_d1(d1).reindex(t.normalize(), method='ffill').to_numpy(dtype=float))
    gio = t.hour + t.minute / 60
    out = pd.DataFrame({
        'rui_atr': rui / x['atr'].to_numpy(), 'bien_do': [float(ti.iloc[i]) if i >= 0 else np.nan for i in k],
        'gio_sin': np.sin(gio / 24 * 2 * np.pi), 'gio_cos': np.cos(gio / 24 * 2 * np.pi), 'thu': t.day_of_week.astype(float),
        'thuan_h1': PP._chieu_h1(h1, t) * dau, 'thuan_d1': xd * dau,
        'cach_ema50': x['cach_ema50'].to_numpy() * dau, 'rsi': x['rsi'].to_numpy() * dau, 'vi_tri_24h': x['vi_tri_24h'].to_numpy() * dau,
        'di_4h': x['di_4h'].to_numpy() * dau, 'than_nen': x['than_nen'].to_numpy() * dau, 'bien_nen': x['bien_nen'].to_numpy(),
        'cho': float(bool(PP.DS[ma].get('cho')))})
    for m in PP.DS:
        out[f'pp_{m}'] = float(m == ma)
    return out


def du_lieu(cfg: dict, tu_nam: int = 2015, *, include_risk: bool = False) -> pd.DataFrame:
    """Mọi tín hiệu của tám phương pháp trên vàng từ `tu_nam`, kèm đặc trưng và kết quả khi chốt ở 1R, 2R (mỗi tín hiệu chấm độc lập)."""
    spec = importlib.util.spec_from_file_location('nghien_cuu', HERE / 'cong-cu' / 'nghien_cuu.py')      # dùng chung phép chấm với phần nghiên cứu
    nc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nc)
    g = cfg['gia']
    m1 = hoc._m1_dai(g, tu_nam)
    fr = hoc._khung(m1, g)
    T = m1.index.as_unit('ns').asi8
    O, H, L, C = (m1[k].to_numpy(dtype=float) for k in ('open', 'high', 'low', 'close'))
    f, parts, moi = bang_nen(fr['M15']), [], []
    for ma in PP.DS:
        th = PP.quet(ma, fr['M15'], fr['H1'])
        moi.append(pd.DataFrame({'t': pd.DatetimeIndex([s['t'] for s in th]), 'ma': ma, 'huong': [s['huong'] for s in th]}))
        df = nc.cham_doc_lap(th, T, O, H, L, C, float(g.get('spread', 0.17)), PP.PHI)
        if not len(df):
            continue
        t = pd.DatetimeIndex(df['t'])
        b = _bang(f, fr['H1'], fr['D1'], t, np.where(df['huong'] == 'MUA', 1.0, -1.0), df['rui'].to_numpy(), ma)
        b.insert(0, 't', df['t'].to_numpy())
        b.insert(1, 'ma', ma)
        b.insert(2, 'nam', t.year)
        b.insert(3, 'huong', df['huong'].to_numpy())
        if include_risk:
            b['risk_price'] = df['rui'].to_numpy()
        for k in TPS:
            b[f'r{k:g}'] = df[f'r{k:g}'].to_numpy()
        parts.append(b)
    # Đồng thuận đếm trên MỌI tín hiệu (kể cả lệnh chờ về sau không khớp), đúng như dac_trung() đếm lúc chạy thật. Trước 23/11/2026 nó chỉ đếm
    # tín hiệu có kết quả, tức là dùng thông tin tương lai (lệnh chờ kia về sau có khớp không) và làm mô hình trông có lãi trong khi không có.
    return them_dong_thuan(pd.concat(parts, ignore_index=True), nguon=pd.concat(moi, ignore_index=True)).replace([np.inf, -np.inf], np.nan).dropna(subset=DAC)


DT_PHUT = 120              # cửa sổ đồng thuận: tín hiệu của phương pháp khác trong chừng này phút trước đó


def them_dong_thuan(d: pd.DataFrame, nguon: pd.DataFrame | None = None) -> pd.DataFrame:
    """Thêm hai cột cho mỗi tín hiệu: 'dt_cung' và 'dt_nguoc' = số phương pháp KHÁC có tín hiệu cùng chiều / ngược chiều trong DT_PHUT phút
    tính tới đúng lúc tín hiệu (không nhìn tương lai). `nguon`: bảng tín hiệu để đếm (cột t, ma, huong); mặc định là chính `d`. Khi `d` chỉ gồm
    tín hiệu đã có kết quả thì PHẢI đưa `nguon` là mọi tín hiệu, nếu không phép đếm sẽ ngầm biết lệnh chờ nào về sau khớp."""
    d = d.copy()
    ng = d if nguon is None else nguon
    t = pd.DatetimeIndex(d['t']).as_unit('ns').asi8
    tn, ma_n, mua_n = pd.DatetimeIndex(ng['t']).as_unit('ns').asi8, ng['ma'].to_numpy(), (ng['huong'] == 'MUA').to_numpy()
    w = DT_PHUT * 60 * 10 ** 9
    cung, nguoc = np.zeros(len(d)), np.zeros(len(d))
    mua = (d['huong'] == 'MUA').to_numpy()
    for ma in pd.unique(ma_n):
        khac = (d['ma'] != ma).to_numpy()
        for h in (True, False):
            arr = np.sort(tn[(ma_n == ma) & (mua_n == h)])
            co = (np.searchsorted(arr, t, side='right') - np.searchsorted(arr, t - w, side='right')) > 0
            cung += co & khac & (mua == h)
            nguoc += co & khac & (mua != h)
    d['dt_cung'], d['dt_nguoc'] = cung, nguoc
    return d


def _hoc(d: pd.DataFrame):
    from sklearn.linear_model import LogisticRegression                       # noqa: PLC0415 - chỉ cần khi huấn luyện
    from sklearn.preprocessing import StandardScaler                          # noqa: PLC0415
    X = d[cot()].to_numpy(dtype=float)
    sc = StandardScaler().fit(X)
    lr = LogisticRegression(C=0.5, max_iter=500).fit(sc.transform(X), (d['r2'] > 0).astype(int))
    return sc.mean_, np.where(sc.scale_ == 0, 1.0, sc.scale_), lr.coef_[0], float(lr.intercept_[0])


def _p(X: np.ndarray, tb, lech, he_so, chan) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-(((X - tb) / lech) @ he_so + chan)))


def auc(y: np.ndarray, p: np.ndarray) -> float | None:
    """Diện tích dưới đường ROC (0,5 là đoán bừa, 1 là xếp đúng hoàn toàn), tính bằng hạng (Mann–Whitney), không cần thư viện ngoài."""
    y = np.asarray(y, dtype=bool)
    n1, n0 = int(y.sum()), int((~y).sum())
    if not n1 or not n0:
        return None
    h = pd.Series(np.asarray(p, dtype=float)).rank().to_numpy()
    return float((h[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def kiem_cheo(d: pd.DataFrame, k: int = CV_K, loc: bool = True, hoc_fn=None) -> dict:
    """Kiểm chéo k phần theo thời gian (López de Prado, Advances in Financial Machine Learning, 2018, chương 7).
    Mỗi lượt lấy một quãng liền làm phần kiểm, học trên phần còn lại. `loc=True`: bỏ khỏi phần học (1) mọi tín hiệu có kết quả chồng lên quãng
    kiểm (giờ tín hiệu trong [đầu − H_NHAN, cuối]) và (2) vùng cấm ngay sau quãng kiểm; `loc=False` là kiểm chéo thường, để so mức rò rỉ.
    Mỗi lượt đo: AUC, và nhóm 10% điểm cao nhất (ngưỡng lấy từ phần học) so với mọi tín hiệu của phần kiểm, chốt ở 2R."""
    hoc_fn = hoc_fn or _hoc
    d = d.sort_values('t', kind='stable').reset_index(drop=True)
    t = pd.DatetimeIndex(d['t'])
    X, r2 = d[cot()].to_numpy(dtype=float), d['r2'].to_numpy(dtype=float)
    cam = max(H_NHAN, (t[-1] - t[0]) * CAM_TY_LE)
    bien = np.array_split(np.arange(len(d)), k)
    gap = []
    for idx in bien:
        a, b = t[idx[0]], t[idx[-1]]
        kiem = np.zeros(len(d), dtype=bool)
        kiem[idx] = True
        hoc_ = ~kiem
        if loc:
            hoc_ &= ~((t >= a - H_NHAN) & (t <= b)) & ~((t > b) & (t <= b + cam))
        th = hoc_fn(d[hoc_])
        p_k, p_h = _p(X[kiem], *th), _p(X[hoc_], *th)
        top = p_k >= np.quantile(p_h, 0.9)
        rk = r2[kiem]
        a_ = auc(rk > 0, p_k)
        gap.append({'tu': a.date().isoformat(), 'den': b.date().isoformat(), 'n_hoc': int(hoc_.sum()), 'n_bo': int((~kiem).sum() - hoc_.sum()),
                    'n': int(kiem.sum()), 'auc': None if a_ is None else round(a_, 3), 'r_tb': round(float(rk.mean()), 3),
                    'n_top': int(top.sum()), 'top_r_tb': round(float(rk[top].mean()), 3) if top.any() else None,
                    'top_ty_le': round(float((rk[top] > 0).mean() * 100), 1) if top.any() else None})
    co = [g for g in gap if g['top_r_tb'] is not None]
    nt = sum(g['n_top'] for g in co)
    return {'k': k, 'loc': loc, 'ngay_chong': H_NHAN.days, 'ngay_cam': round(cam.total_seconds() / 86400, 1), 'gap': gap,
            'auc_tb': round(float(np.mean([g['auc'] for g in gap if g['auc'] is not None])), 3),
            'top_r_tb': round(sum(g['top_r_tb'] * g['n_top'] for g in co) / nt, 3) if nt else None,
            'r_tb': round(float(r2.mean()), 3), 'so_phan_hon': sum(g['top_r_tb'] > g['r_tb'] for g in co),
            'so_phan_lai': sum(g['top_r_tb'] > 0 for g in co)}


def kiem_cuon_chieu(d: pd.DataFrame, k: int = CV_K, hoc_fn=None) -> dict:
    """Học trên quá khứ rồi kiểm quãng kế tiếp; bỏ nhãn chưa chắc đã biết tại đầu quãng kiểm.

    Khối đầu chỉ dùng học. Cùng thời điểm luôn nằm cùng phía, chuẩn hóa và ngưỡng top10 chỉ lấy từ phần học.
    Khác purged CV ở trên: tuyệt đối không dùng dữ liệu sau quãng kiểm để học.
    """
    if k < 2:
        raise ValueError('Cần ít nhất hai phần kiểm.')
    hoc_fn = hoc_fn or _hoc
    d = d.sort_values('t', kind='stable').reset_index(drop=True)
    t = pd.DatetimeIndex(d['t'])
    gap, bo = [], []
    for idx in np.array_split(np.arange(len(d)), k + 1)[1:]:
        if not len(idx):
            continue
        a, b = t[idx[0]], t[idx[-1]]
        # Dùng mốc thời gian để mọi tín hiệu đồng thời không bị chia qua hai tập.
        kiem = (t >= a) & (t <= b)
        if gap and a <= pd.Timestamp(gap[-1]['den_luc']):
            kiem &= t > pd.Timestamp(gap[-1]['den_luc'])
        hoc_ = t < a - H_NHAN
        dh, dk = d[hoc_], d[kiem]
        if len(dh) < 30 or len(dk) == 0 or (dh['r2'] > 0).nunique() < 2:
            bo.append(a.isoformat())
            continue
        th = hoc_fn(dh)
        ph = _p(dh[cot()].to_numpy(dtype=float), *th)
        pk = _p(dk[cot()].to_numpy(dtype=float), *th)
        rk = dk['r2'].to_numpy(dtype=float)
        top = pk >= np.quantile(ph, 0.9)
        ac = auc(rk > 0, pk)
        gap.append({'tu': pd.Timestamp(dk['t'].min()).date().isoformat(), 'tu_luc': pd.Timestamp(dk['t'].min()).isoformat(), 'den': b.date().isoformat(),
                    'den_luc': b.isoformat(), 'hoc_den': pd.Timestamp(dh['t'].max()).isoformat(),
                    'n_hoc': len(dh), 'n': len(dk), 'auc': None if ac is None else round(ac, 3),
                    'r_tb': round(float(rk.mean()), 3), 'n_top': int(top.sum()),
                    'top_r_tb': round(float(rk[top].mean()), 3) if top.any() else None})
    co = [g for g in gap if g['top_r_tb'] is not None]
    nt, n = sum(g['n_top'] for g in co), sum(g['n'] for g in gap)
    acs = [g['auc'] for g in gap if g['auc'] is not None]
    return {'k': k, 'chi_hoc_qua_khu': True, 'ngay_chong': H_NHAN.days, 'gap': gap, 'bo_qua': bo,
            'auc_tb': round(float(np.mean(acs)), 3) if acs else None,
            'r_tb': round(sum(g['r_tb'] * g['n'] for g in gap) / n, 3) if n else None,
            'top_r_tb': round(sum(g['top_r_tb'] * g['n_top'] for g in co) / nt, 3) if nt else None,
            'so_phan_hon': sum(g['top_r_tb'] > g['r_tb'] for g in co), 'so_phan_lai': sum(g['top_r_tb'] > 0 for g in co)}


def huan(cfg: dict) -> dict:
    """Huấn luyện và tự kiểm ngoài mẫu. Trả tham số mô hình (dạng số thuần, lưu được thành JSON) cùng kết quả kiểm."""
    d = du_lieu(cfg)
    ngoai = d[d['nam'] > HOC_TOI]
    hoc_ = d[(d['nam'] <= HOC_TOI) & (pd.to_datetime(d['t']) < pd.Timestamp(ngoai['t'].min()) - H_NHAN)]
    th = _hoc(hoc_)
    p_ngoai = _p(ngoai[cot()].to_numpy(dtype=float), *th)
    chon = ngoai[p_ngoai >= np.quantile(_p(hoc_[cot()].to_numpy(dtype=float), *th), 0.9)]          # ngưỡng lấy từ quãng học
    so = lambda x: {'n': int(len(x)), 'ty_le': round(float((x['r2'] > 0).mean() * 100), 1), 'r_tb': round(float(x['r2'].mean()), 3)}      # noqa: E731
    thang = lambda x: [[k, int(len(x)), round(float((x[f'r{k:g}'] > 0).mean() * 100), 1), round(float(x[f'r{k:g}'].mean()), 3)] for k in TPS]      # noqa: E731
    theo_nam = [[int(n), int(len(x)), round(float(x['r2'].mean()), 3), round(float(ngoai[ngoai['nam'] == n]['r2'].mean()), 3)] for n, x in chon.groupby('nam')]
    # bậc thang chốt lời: cùng các điểm vào đó, chốt ở mỗi mức thì thắng bao nhiêu phần trăm và trung bình mấy R
    bac = {ma: {h: [[k, int(len(x)), round(float((x[f'r{k:g}'] > 0).mean() * 100), 1), round(float(x[f'r{k:g}'].mean()), 3)] for k in TPS]
                for h, x in g.groupby('huong') if len(x) >= 30} for ma, g in d.groupby('ma')}
    nhom = lambda x: [int(len(x)), round(float((x['r2'] > 0).mean() * 100), 1), round(float(x['r2'].mean()), 3)]      # noqa: E731
    dong_thuan = {'cung': [nhom(d[d['dt_cung'] == 0]), nhom(d[d['dt_cung'] == 1]), nhom(d[d['dt_cung'] >= 2])],
                  'nguoc': [nhom(d[d['dt_nguoc'] == 0]), nhom(d[d['dt_nguoc'] >= 1])], 'phut': DT_PHUT}
    cv = {'loc': kiem_cheo(d, loc=True), 'thuong': kiem_cheo(d, loc=False), 'cuon_chieu': kiem_cuon_chieu(d)}
    tb, lech, he_so, chan = _hoc(d)                                # mô hình dùng thật: học trên toàn bộ dữ liệu
    p = _p(d[cot()].to_numpy(dtype=float), tb, lech, he_so, chan)
    return {'phien_ban': PHIEN_BAN, 'tinh_luc': datetime.now(timezone.utc).isoformat(), 'n': int(len(d)), 'tu_nam': int(d['nam'].min()), 'cot': cot(),
            'tb': tb.tolist(), 'lech': lech.tolist(), 'he_so': he_so.tolist(), 'chan': chan, 'phan_vi': np.quantile(p, np.linspace(0, 1, 101)).tolist(),
            'ngoai_mau': {'hoc_toi': HOC_TOI, 'tu': HOC_TOI + 1, 'den': int(d['nam'].max()), 'tat_ca': so(ngoai), 'top10': so(chon),
                          'bac': {'tat_ca': thang(ngoai), 'top10': thang(chon)}, 'theo_nam': theo_nam}, 'bac_thang': bac, 'nguong': NGUONG, 'dong_thuan': dong_thuan,
            'kiem_cheo': cv}


def diem(mh: dict, x: dict) -> dict | None:
    """Điểm của một điểm vào có đặc trưng `x`: {'p': xác suất mô hình, 'hang': xếp hạng 0–100 so với các tín hiệu quá khứ}."""
    v = np.array([float(x.get(k, 0.0)) for k in mh['cot']], dtype=float)
    if not np.isfinite(v).all():
        return None
    p = float(_p(v[None, :], np.array(mh['tb']), np.array(mh['lech']), np.array(mh['he_so']), mh['chan'])[0])
    return {'p': round(p, 3), 'hang': int(np.clip(np.searchsorted(mh['phan_vi'], p, side='right') - 1, 0, 100))}


def tin_hieu_gan(fr: dict) -> dict:
    """Tín hiệu gần đây của mọi phương pháp ({mã: [(giờ nến đóng, chiều)]}), để đếm đồng thuận cho một phương án đang có."""
    m15 = fr['M15'].iloc[-400:]
    return {m: [(pd.Timestamp(s['t']), s['huong']) for s in PP.quet(m, m15, fr['H1'])] for m in PP.DS}


def dac_trung(fr: dict, pa: dict, th: dict | None = None) -> dict | None:
    """Đặc trưng của một phương án đang có (cần 'nen': giờ nến tín hiệu đóng), tính đúng như lúc huấn luyện."""
    if not (pa.get('co') and pa.get('nen')) or pa.get('ma') not in PP.DS:
        return None
    t = pd.DatetimeIndex([pd.Timestamp(pa['nen'])])
    b = _bang(bang_nen(fr['M15'].iloc[-600:]), fr['H1'], fr['D1'], t, np.array([1.0 if pa['huong'] == 'MUA' else -1.0]),
              np.array([abs(float(pa['vao']) - float(pa['sl']))]), pa['ma'])
    x = {k: float(v) for k, v in b.iloc[0].items()}
    th = th if th is not None else tin_hieu_gan(fr)
    t1, t0 = t[0], t[0] - pd.Timedelta(minutes=DT_PHUT)
    gan = {m: {h for tt, h in ds if t0 < tt <= t1} for m, ds in th.items() if m != pa['ma']}
    x['dt_cung'] = float(sum(pa['huong'] in v for v in gan.values()))
    x['dt_nguoc'] = float(sum(any(h != pa['huong'] for h in v) for v in gan.values()))
    return x


def _tep(cfg: dict) -> Path:
    base = Path(cfg.get('thu_muc_ra', 'out'))
    return (base if base.is_absolute() else HERE / base) / 'mo-hinh.json'


def lay(cfg: dict, cho: bool = False) -> dict | None:
    """Mô hình của hôm nay nếu đã có (bộ nhớ hoặc out/mo-hinh.json); chưa có thì huấn luyện ở nền và trả None. Tắt trong cấu hình thì luôn None."""
    if not (cfg.get('mo_hinh') or {}).get('bat'):
        return None
    key = json.dumps([PHIEN_BAN, datetime.now(timezone.utc).date().isoformat()])
    with _khoa:
        if _tt['key'] == key and _tt['kq'] is not None:
            return _tt['kq']
        if _tt['key'] != key:
            _tt.update(key=key, kq=None, loi=None)
            try:
                luu = json.loads(_tep(cfg).read_text(encoding='utf-8'))
                if luu.get('key') == key:
                    _tt['kq'] = luu['kq']
                    return _tt['kq']
            except (OSError, ValueError, KeyError):
                pass
        if _tt['loi'] or _tt['dang']:
            return None
        _tt['dang'] = True

    def lam():
        try:
            kq = huan(cfg)
            with _khoa:
                if _tt['key'] == key:
                    _tt['kq'] = kq
            _tep(cfg).parent.mkdir(parents=True, exist_ok=True)
            _tep(cfg).write_text(json.dumps({'key': key, 'kq': kq}, ensure_ascii=False), encoding='utf-8')
        except Exception as e:                                                 # noqa: BLE001
            with _khoa:
                _tt['loi'] = f'{type(e).__name__}: {e}'
        finally:
            with _khoa:
                _tt['dang'] = False

    if cho:
        lam()
        return _tt['kq']
    threading.Thread(target=lam, name='mo-hinh', daemon=True).start()
    return None


def gan(cfg: dict, fr: dict, plans: list[dict]) -> dict | None:
    """Gắn 'mo_hinh': {'p', 'hang'} vào từng phương án đang có điểm vào. Trả phần tóm tắt để trang hiển thị, hoặc None nếu mô hình chưa sẵn."""
    mh = lay(cfg)
    if mh is None:
        return {'san_sang': False, 'loi': _tt.get('loi')} if (cfg.get('mo_hinh') or {}).get('bat') else None
    th = None
    for pa in plans:
        try:
            if th is None and pa.get('co') and pa.get('nen'):
                th = tin_hieu_gan(fr)
            x = dac_trung(fr, pa, th)
            pa['mo_hinh'] = diem(mh, x) if x else None
            pa['dong_thuan'] = {'cung': int(x['dt_cung']), 'nguoc': int(x['dt_nguoc'])} if x else None
        except Exception:                                                      # noqa: BLE001 - thiếu đặc trưng thì bỏ điểm, không làm hỏng phương án
            pa['mo_hinh'] = None
    return {'san_sang': True, 'n': mh['n'], 'tu_nam': mh['tu_nam'], 'ngoai_mau': mh['ngoai_mau'], 'bac_thang': mh.get('bac_thang') or {}, 'nguong': mh.get('nguong', NGUONG), 'dong_thuan': mh.get('dong_thuan'),
            'kiem_cheo': mh.get('kiem_cheo')}


if __name__ == '__main__':                                                     # python -X utf8 -m so_cong_khai.mo_hinh
    cfg_ = json.loads((HERE / 'cau-hinh.json').read_text(encoding='utf-8'))
    kq_ = huan(cfg_)
    print(kq_['n'], 'tín hiệu từ', kq_['tu_nam'], '· kiểm ngoài mẫu:', kq_['ngoai_mau'])
    print('hệ số:', ', '.join(f'{k} {v:+.3f}' for k, v in sorted(zip(kq_['cot'], kq_['he_so']), key=lambda z: -abs(z[1]))[:10]))
