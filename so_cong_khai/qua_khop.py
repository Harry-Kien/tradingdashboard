"""Điểm "khớp quá khứ": kết quả kiểm lại quá khứ đẹp vì phương pháp có lợi thế thật, hay vì đã thử nhiều cấu hình rồi chọn cái may mắn nhất.

Hai phép đo, theo hai bài báo:
- PBO (Probability of Backtest Overfitting), đo bằng CSCV — Bailey, Borwein, López de Prado, Zhu, "The Probability of Backtest Overfitting",
  Journal of Computational Finance (2017), https://papers.ssrn.com/abstract=2326253. Chia chuỗi thời gian thành S khối; với mọi cách lấy
  S/2 khối làm phần "chọn" và phần còn lại làm phần "kiểm", lấy cấu hình tốt nhất ở phần chọn rồi xem nó đứng hạng mấy ở phần kiểm.
  PBO là tỷ lệ số lần cấu hình được chọn rơi xuống nửa dưới ở phần kiểm. PBO gần 0,5 trở lên: chọn theo kiểm lại quá khứ không hơn bốc thăm.
- DSR (Deflated Sharpe Ratio) — Bailey, López de Prado, "The Deflated Sharpe Ratio", Journal of Portfolio Management 40(5), 2014,
  https://papers.ssrn.com/abstract=2460551. Xác suất chỉ số Sharpe thật lớn hơn mức Sharpe cao nhất mà N cấu hình KHÔNG có lợi thế nào vẫn
  đạt được do may, có tính độ lệch và độ nhọn của phân phối lãi lỗ. DSR cao (ví dụ ≥ 95%) mới là dấu hiệu lợi thế thật.

Chỉ dùng numpy và thư viện chuẩn (statistics.NormalDist), không cần scipy. Đầu vào là danh sách lệnh của từng cấu hình
[{'t': giờ đóng/mở lệnh, 'usd': lãi lỗ}], được gộp thành lãi lỗ theo tháng (hoặc theo tuần khi dữ liệu ngắn)."""
from __future__ import annotations

import itertools
import math
from statistics import NormalDist

import numpy as np
import pandas as pd

_N = NormalDist()
EULER = 0.5772156649015329


def ma_tran(lenh: dict[str, list[dict]], tan_suat: str = 'ME') -> pd.DataFrame:
    """Bảng lãi lỗ theo kỳ: hàng là kỳ (tháng 'ME' hoặc tuần 'W'), cột là cấu hình. Kỳ không có lệnh tính 0."""
    cot = {}
    for ten, ls in lenh.items():
        if not ls:
            continue
        s = pd.Series([float(x['usd']) for x in ls], index=pd.to_datetime([str(x['t']) for x in ls], utc=True, format='mixed'))
        cot[ten] = s.groupby(pd.Grouper(freq=tan_suat)).sum()
    if not cot:
        return pd.DataFrame()
    return pd.DataFrame(cot).fillna(0.0).sort_index()


def _sharpe(x: np.ndarray, truc: int = 0) -> np.ndarray:
    m, sd = x.mean(axis=truc), x.std(axis=truc, ddof=1)
    return np.where(sd > 0, m / np.where(sd > 0, sd, 1), np.sign(m) * 1e6)


def pbo(M: pd.DataFrame | np.ndarray, S: int = 16) -> dict:
    """PBO bằng CSCV. M: T kỳ × N cấu hình. Thước đo hiệu quả là Sharpe theo kỳ. Trả {'pbo', 'lo_khi_kiem', 'so_to_hop', 'S', 'N', 'T', 'logit_tb'}."""
    X = np.asarray(M, dtype=float)
    T, N = X.shape
    if N < 2 or S < 2 or S % 2 or T < 2 * S:
        raise ValueError(f'không đủ dữ liệu cho CSCV: {T} kỳ, {N} cấu hình, S={S}')
    X = X[T - (T // S) * S:]                                                    # bỏ phần dư ở ĐẦU để giữ dữ liệu gần nhất
    khoi = np.split(X, S)
    lam, lo = [], 0
    for chon in itertools.combinations(range(S), S // 2):
        bo = [i for i in range(S) if i not in chon]
        A, B = np.vstack([khoi[i] for i in chon]), np.vstack([khoi[i] for i in bo])
        sa, sb = _sharpe(A), _sharpe(B)
        n = int(np.argmax(sa))
        hang = 1 + int((sb < sb[n]).sum()) + 0.5 * int((sb == sb[n]).sum() - 1)       # hạng của cấu hình được chọn ở phần kiểm (1 = tệ nhất)
        w = hang / (N + 1)
        lam.append(math.log(w / (1 - w)))
        lo += sb[n] < 0
    lam = np.array(lam)
    return {'pbo': float((lam <= 0).mean()), 'lo_khi_kiem': float(lo / len(lam)), 'so_to_hop': len(lam), 'S': S, 'N': N, 'T': int(len(X)),
            'logit_tb': float(lam.mean())}


def sr0(v_sr: float, n: int) -> float:
    """Sharpe cao nhất kỳ vọng do may trong n cấu hình không có lợi thế (Bailey & López de Prado 2014, công thức của DSR)."""
    if n <= 1 or v_sr <= 0:
        return 0.0
    return math.sqrt(v_sr) * ((1 - EULER) * _N.inv_cdf(1 - 1 / n) + EULER * _N.inv_cdf(1 - 1 / (n * math.e)))


def psr(sr: float, ngung: float, t: int, lech: float, nhon: float) -> float:
    """Xác suất Sharpe thật > ngưỡng (Probabilistic Sharpe Ratio). sr, ngưỡng theo kỳ; nhon là độ nhọn thô (phân phối chuẩn = 3)."""
    mau = 1 - lech * sr + (nhon - 1) / 4 * sr * sr
    if t < 3 or mau <= 0:
        return float('nan')
    return _N.cdf((sr - ngung) * math.sqrt(t - 1) / math.sqrt(mau))


def dsr(M: pd.DataFrame, n_thu: int | None = None) -> dict:
    """DSR của từng cột. n_thu: số cấu hình đã thử (mặc định = số cột). Mỗi cột chỉ tính trên các kỳ từ lệnh đầu tới lệnh cuối của nó."""
    sr, chi = {}, {}
    for c in M.columns:
        s = M[c]
        nz = s.to_numpy().nonzero()[0]
        if len(nz) < 2:
            continue
        x = s.iloc[nz[0]:nz[-1] + 1].to_numpy()
        if len(x) < 6 or x.std(ddof=1) == 0:
            continue
        sr[c] = float(x.mean() / x.std(ddof=1))
        d = x - x.mean()
        m2 = (d ** 2).mean()
        chi[c] = (len(x), float((d ** 3).mean() / m2 ** 1.5), float((d ** 4).mean() / m2 ** 2))
    n = n_thu or len(sr)
    v = float(np.var(list(sr.values()), ddof=1)) if len(sr) > 1 else 0.0
    nguong = sr0(v, n)
    out = {}
    for c, s in sr.items():
        t, lech, nhon = chi[c]
        so = lambda v: None if v != v else round(v, 4)                       # noqa: E731 - NaN không ghi được ra JSON
        out[c] = {'dsr': so(psr(s, nguong, t, lech, nhon)), 'psr': so(psr(s, 0.0, t, lech, nhon)), 'sr': round(s, 4), 'so_ky': t}
    return {'cot': out, 'sr0': nguong, 'n_thu': n, 'v_sr': v}


def danh_gia(lenh_chon: dict[str, list[dict]], lenh_them: dict[str, list[dict]] | None = None) -> dict:
    """Điểm khớp quá khứ cho một lần "học". lenh_chon: các cấu hình cùng quãng dữ liệu, cạnh tranh để được chọn (dùng cho PBO).
    lenh_them: cấu hình khác quãng (luật riêng) — chỉ tính DSR, nhưng vẫn đếm vào số lần thử. Tự chọn kỳ tháng hay tuần theo độ dài dữ liệu."""
    lenh_them = lenh_them or {}
    for ts in ('ME', 'W'):
        M = ma_tran(lenh_chon, ts)
        if len(M) >= 64 or ts == 'W':
            break
    out: dict = {'ky': 'tháng' if ts == 'ME' else 'tuần', 'so_cau_hinh': len(lenh_chon) + len(lenh_them)}
    S = 16 if len(M) >= 64 else 8 if len(M) >= 32 else 0
    try:
        out['pbo'] = pbo(M, S) if S else None
        if not S:
            out['ly_do_pbo'] = f'chỉ có {len(M)} {out["ky"]} dữ liệu, cần ít nhất 32 để đo'
    except ValueError as e:
        out['pbo'], out['ly_do_pbo'] = None, str(e)
    tat_ca = {**lenh_chon, **lenh_them}
    out['dsr'] = dsr(ma_tran(tat_ca, ts), n_thu=out['so_cau_hinh'])
    return out
