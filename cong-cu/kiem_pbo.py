# -*- coding: utf-8 -*-
"""Xác suất khớp quá mức của phép kiểm thử (PBO) theo Bailey, Borwein, López de Prado và Zhu (2015), bằng kiểm định chéo đối xứng tổ hợp (CSCV).

Câu hỏi: nếu chọn chiến lược tốt nhất trên một phần lịch sử, thì trên phần còn lại nó có còn tốt không, hay chỉ là may? Cách đo ghi TRƯỚC ở
cong-cu/CHUAN_HOA_DANG_KY.md (phần "PBO"). Dữ liệu: bảng lãi lỗ theo tuần của cong-cu/kiem_dinh_spa.py (out/spa-bang-tuan.csv). Chỉ đọc tệp.

    python -X utf8 cong-cu/kiem_pbo.py
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
SO_KHOI = 16


def chi_so(x: np.ndarray) -> np.ndarray:
    """Tỷ số lãi trung bình / độ lệch chuẩn của từng cột (cột không biến động thì 0)."""
    sd = x.std(axis=0, ddof=1)
    tb = x.mean(axis=0)
    return np.where(sd > 0, tb / np.where(sd > 0, sd, 1.0), 0.0)


def pbo(M: np.ndarray, so_khoi: int = SO_KHOI) -> dict:
    """M: (số tuần × số chiến lược). Trả PBO, tỷ lệ chiến lược được chọn lỗ ngoài mẫu, thứ hạng tương đối trung vị ngoài mẫu, số cách chia."""
    T, N = M.shape
    khoi = np.array_split(np.arange(T), so_khoi)
    tong = np.array([M[k].sum(axis=0) for k in khoi])                       # tổng theo khối, để tính nhanh trung bình
    binh = np.array([(M[k] ** 2).sum(axis=0) for k in khoi])
    dem = np.array([len(k) for k in khoi])
    lam, lo, hang = [], [], []
    for trong in itertools.combinations(range(so_khoi), so_khoi // 2):
        a = np.zeros(so_khoi, bool)
        a[list(trong)] = True
        out = []
        for m in (a, ~a):
            n = dem[m].sum()
            tb = tong[m].sum(axis=0) / n
            var = (binh[m].sum(axis=0) - n * tb ** 2) / (n - 1)
            sd = np.sqrt(np.clip(var, 0, None))
            out.append(np.where(sd > 1e-12, tb / np.where(sd > 1e-12, sd, 1.0), 0.0))
        is_, oos = out
        j = int(np.argmax(is_))
        w = (np.sum(oos < oos[j]) + 0.5 * (np.sum(oos == oos[j]) - 1) + 1) / (N + 1)  # thứ hạng tương đối ngoài mẫu, trong (0, 1)
        lam.append(np.log(w / (1 - w)))
        hang.append(w)
        n_oos = dem[~a].sum()
        lo.append(tong[~a].sum(axis=0)[j] / n_oos <= 0)
    lam = np.array(lam)
    return {'pbo': round(float((lam <= 0).mean()), 4), 'lo_ngoai_mau': round(float(np.mean(lo)), 4), 'hang_trung_vi': round(float(np.median(hang)), 3),
            'so_cach': int(len(lam)), 'so_tuan': int(T), 'so_chien_luoc': int(N)}


if __name__ == '__main__':
    bang = pd.read_csv(GOC / 'out' / 'spa-bang-tuan.csv')
    bang = bang.drop(columns=[c for c in bang.columns if c.lower().startswith(('unnamed', 'tuan', 'week'))], errors='ignore')
    tap1 = json.loads((GOC / 'out' / 'spa-tap-1.json').read_text(encoding='utf-8'))
    KQ = {}
    for ten, cot in (('tap_1', [c for c in tap1 if c in bang.columns]), ('toan_bo', list(bang.columns))):
        KQ[ten] = pbo(bang[cot].to_numpy(dtype=float))
    doc = lambda p: 'ít dấu hiệu khớp quá mức' if p < 0.2 else 'đáng ngờ' if p < 0.5 else 'chọn theo quá khứ không hơn chọn bừa'   # noqa: E731
    chu = ['XÁC SUẤT KHỚP QUÁ MỨC (PBO, kiểm định chéo đối xứng tổ hợp, 16 khối)']
    for ten, nhan in (('tap_1', 'Tập 1 (luật và phương pháp, gộp và từng chiều)'), ('toan_bo', 'Toàn bộ (thêm từng chiều trong từng phiên)')):
        x = KQ[ten]
        chu.append(f"{nhan}: {x['so_chien_luoc']} chiến lược · {x['so_tuan']} tuần · {x['so_cach']:,} cách chia · PBO = {x['pbo']:.3f} ({doc(x['pbo'])}) · "
                   f"chiến lược tốt nhất trong mẫu lỗ ngoài mẫu ở {x['lo_ngoai_mau'] * 100:.1f}% số cách · thứ hạng ngoài mẫu trung vị {x['hang_trung_vi']:.2f} (0,5 là giữa)")
    txt = '\n'.join(chu).replace('.', ',').replace(',py', '.py')
    print(txt)
    (GOC / 'out' / 'pbo.json').write_text(json.dumps(KQ, ensure_ascii=False, indent=1), encoding='utf-8')
    (GOC / 'out' / 'pbo.txt').write_text(txt + '\n', encoding='utf-8')
    sys.exit(0)
