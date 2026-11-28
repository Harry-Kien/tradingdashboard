# -*- coding: utf-8 -*-
"""Đối chiếu phép kiểm định SPA tự viết của webapp (cong-cu/kiem_dinh_spa.py) với một bản cài độc lập: thư viện arch (arch.bootstrap.SPA,
github.com/bashtage/arch, cài ngày 24/11/2026).

Vì sao cần: câu "chưa có luật nào có lãi thật sau khi tính tới việc đã thử rất nhiều luật" dựa trên phép SPA do dự án tự viết. Nếu phép đó viết
sai thì kết luận sai theo. arch là thư viện kinh tế lượng được dùng rộng rãi và có sẵn đúng phép kiểm định này.

Bốn phần:
A. Dữ liệu giả có đáp án biết trước, hạt giống cố định (vài giây): nhiễu thuần (không chiến lược nào có lãi thật → p phải lớn) và một chiến lược
   có lãi thật giữa nhiều chiến lược nhiễu (p phải rất nhỏ). Hai bản phải cho p gần nhau (lệch không quá 0,05 hoặc cùng dưới 0,01).
C. Tỷ lệ báo động giả trên dữ liệu giả (khoảng một phút): 200 bộ dữ liệu KHÔNG có lãi thật, đếm số lần mỗi bản kêu "có lãi" ở mức 5%. Phép kiểm
   định đúng thì kêu khoảng 5%. Các tuần độc lập nhau: cả hai bản phải nằm trong 2–9%. Tuần này phụ thuộc tuần trước (tự tương quan 0,5): in ra
   để biết, không tính đạt hay hỏng.
B. Bảng lãi lỗ theo tuần thật của webapp (out/spa-bang-tuan.csv do kiem_dinh_spa.py ghi; chưa có thì công cụ tự chạy lại mọi luật, mất vài phút):
   hai tập chiến lược như trong kiem_dinh_spa.py, in giá trị p của cả hai bản.
D. Hiệu chuẩn trên dữ liệu có hình dạng thật (khoảng hai phút): lấy chính bảng tuần thật, trừ đi lãi trung bình của từng chiến lược để mọi chiến
   lược có lãi thật bằng 0 (giữ nguyên các tuần lãi lỗ lớn bất thường và việc các chiến lược thắng thua cùng nhau), xáo lại theo khối thành 300
   bộ dữ liệu, rồi đếm số lần mỗi bản kêu "có lãi". Bản nào kêu gần đúng mức danh nghĩa hơn thì giá trị p của bản đó đáng đọc hơn.

Hai bản cài không cho con số giống hệt:
- dãy số ngẫu nhiên khác nhau;
- bản tự viết làm đúng như bài báo gốc của Hansen (2005): chia cho MỘT sai số chuẩn tính trên dữ liệu gốc, dùng cho mọi lần lấy mẫu lại; arch 9
  tính lại sai số chuẩn trong từng lần lấy mẫu (kiểu bootstrap-t), cách này chịu được dữ liệu lệch và có vài tuần rất lớn tốt hơn.

Phát hiện ngày 24/11/2026 (các con số ở trang Kiến thức và README):
- trên dữ liệu giả các tuần độc lập, hai bản tương đương (báo động giả 4,5% và 4,0%);
- trên dữ liệu giả có tự tương quan 0,5, bản tự viết kêu nhầm 23%, arch 8%;
- trên dữ liệu có hình dạng thật (phần D), bản tự viết quá THẬN TRỌNG (kêu 2,0% ở mức 5%), arch đúng mức (4,7%). Tức là giá trị p của bản tự
  viết trên bảng thật lớn hơn mức đúng khoảng hai lần; nên đọc số của arch;
- vì vậy ở tập 1 (33 chiến lược) hai bản KHÁC kết luận: tự viết p = 0,081, arch p = 0,025. Ở tập 2 (119 chiến lược) cả hai đều không có ý nghĩa.
Công cụ chỉ thoát với mã 1 khi phần A hoặc phần C (các tuần độc lập) hỏng, tức là khi một trong hai bản cài tính sai. Hai bản khác kết luận trên
dữ liệu thật là một KẾT QUẢ để đọc, không phải lỗi của công cụ. Chỉ đọc; không nối MT5. Thêm --nhanh để bỏ phần C và D.

    python -X utf8 cong-cu/doi_chieu_spa.py
"""
import importlib.util
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
NGUONG, LAN, KHOI = 0.05, 10000, 4
TEN = (('duoi', 'lower', 'p dưới'), ('nhat_quan', 'consistent', 'p nhất quán'), ('tren', 'upper', 'p trên'))


def _nap(ten: str):
    spec = importlib.util.spec_from_file_location(ten, GOC / 'cong-cu' / f'{ten}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def hai_ban(d: np.ndarray, lan: int = LAN, khoi: int = KHOI, hat: int = 20261124) -> tuple[dict, dict]:
    """(ba giá trị p của bản tự viết, ba giá trị p của arch) cho bảng d (số kỳ × số chiến lược), chuẩn so sánh là lãi 0."""
    from arch.bootstrap import SPA                                     # noqa: PLC0415 - thư viện ngoài, chỉ cần khi chạy phép này
    sp, kd = _nap('kiem_dinh_spa'), _nap('kiem_dinh_thong_ke')
    a = sp.spa(d, kd.chi_so_khoi(len(d), lan, khoi, np.random.default_rng(hat)))
    # arch làm việc với "mất mát": mất mát của chuẩn so sánh là 0, của chiến lược là −lãi, nên chênh lệch mất mát chính là lãi.
    b = SPA(np.zeros(len(d)), -d, block_size=khoi, reps=lan, bootstrap='stationary', studentize=True, seed=hat + 1)
    b.compute()
    pv = b.pvalues
    return {k: float(a[k]) for k, _, _ in TEN}, {k: float(pv[e]) for k, e, _ in TEN}


def dat(a: dict, b: dict) -> bool:
    gan = all(abs(a[k] - b[k]) <= NGUONG or max(a[k], b[k]) < 0.01 for k, _, _ in TEN)
    return gan and all((a[k] < 0.05) == (b[k] < 0.05) or abs(a[k] - b[k]) <= 0.02 for k, _, _ in TEN)


def du_lieu_gia() -> list[tuple[str, np.ndarray, str]]:
    rng = np.random.default_rng(7)
    n, k = 600, 40
    nhieu = rng.normal(0, 10, (n, k))
    co_lai = nhieu.copy()
    co_lai[:, 0] += 2.5                                                 # một chiến lược có lãi thật: trung bình bằng 0,25 độ lệch chuẩn mỗi tuần
    return [('Nhiễu thuần, 40 chiến lược', nhieu, 'lon'), ('Một chiến lược có lãi thật giữa 39 chiến lược nhiễu', co_lai, 'nho')]


def bao_dong_gia(phi: float, so_bo: int = 200, lan: int = 1000, n: int = 600, k: int = 40) -> tuple[float, float]:
    """Tỷ lệ kêu "có lãi" ở mức 5% (p nhất quán) của (bản tự viết, arch) trên `so_bo` bộ dữ liệu không có lãi thật, tự tương quan `phi`."""
    from arch.bootstrap import SPA                                     # noqa: PLC0415
    sp, kd = _nap('kiem_dinh_spa'), _nap('kiem_dinh_thong_ke')
    rng = np.random.default_rng(100 + int(phi * 10))
    pa, pb = [], []
    for _ in range(so_bo):
        e = rng.normal(0, 10, (n, k))
        d = np.empty_like(e)
        d[0] = e[0]
        for i in range(1, n):
            d[i] = phi * d[i - 1] + e[i]
        pa.append(sp.spa(d, kd.chi_so_khoi(n, lan, KHOI, rng))['nhat_quan'])
        b = SPA(np.zeros(n), -d, block_size=KHOI, reps=lan, bootstrap='stationary', studentize=True, seed=int(rng.integers(1, 2**31 - 1)))
        b.compute()
        pb.append(float(b.pvalues['consistent']))
    return float(np.mean(np.array(pa) < 0.05)), float(np.mean(np.array(pb) < 0.05))


def hieu_chuan(x: np.ndarray, so_bo: int = 300, lan: int = 1000) -> tuple[tuple, tuple]:
    """((tỷ lệ kêu ở mức 5%, ở mức 10%) của bản tự viết, của arch) trên `so_bo` bộ dữ liệu dựng từ bảng thật x đã trừ lãi trung bình từng cột."""
    from arch.bootstrap import SPA                                     # noqa: PLC0415
    sp, kd = _nap('kiem_dinh_spa'), _nap('kiem_dinh_thong_ke')
    x0 = x - x.mean(0)
    n = len(x0)
    rng = np.random.default_rng(2026112401)
    the_gioi = kd.chi_so_khoi(n, so_bo, KHOI, rng)
    pa, pb = [], []
    for m in range(so_bo):
        d = x0[the_gioi[m]]
        pa.append(sp.spa(d, kd.chi_so_khoi(n, lan, KHOI, rng))['nhat_quan'])
        b = SPA(np.zeros(n), -d, block_size=KHOI, reps=lan, bootstrap='stationary', studentize=True, seed=int(rng.integers(1, 2**31 - 1)))
        b.compute()
        pb.append(float(b.pvalues['consistent']))
    pa, pb = np.array(pa), np.array(pb)
    return (float((pa < 0.05).mean()), float((pa < 0.10).mean())), (float((pb < 0.05).mean()), float((pb < 0.10).mean()))


def in_dong(ten: str, a: dict, b: dict) -> bool:
    ok = dat(a, b)
    print(f'  {"ĐẠT      " if ok else "KHÔNG ĐẠT"} · {ten}')
    print('      ' + ' · '.join(f'{nhan}: tự viết {a[k]:.3f}, arch {b[k]:.3f}'.replace('.', ',') for k, _, nhan in TEN))
    return ok


if __name__ == '__main__':
    hong = 0
    t0 = time.time()
    print('A. Dữ liệu giả có đáp án biết trước (600 tuần, 10.000 lần lấy mẫu lại, khối trung bình 4 tuần)')
    for ten, d, mong in du_lieu_gia():
        a, b = hai_ban(d)
        ok = in_dong(ten, a, b)
        dung = all((x['nhat_quan'] < 0.01) if mong == 'nho' else (x['nhat_quan'] > 0.10) for x in (a, b))
        if not dung:
            print(f'      KHÔNG ĐẠT: đáp án mong đợi là p {"rất nhỏ" if mong == "nho" else "lớn"}')
        hong += not (ok and dung)
    print(f'  ({time.time() - t0:.0f} giây)')

    if '--nhanh' not in sys.argv:
        t0 = time.time()
        print()
        print('C. Tỷ lệ báo động giả ở mức 5% trên 200 bộ dữ liệu giả không có lãi thật (đúng thì khoảng 5%)')
        a0, b0 = bao_dong_gia(0.0)
        ok = 0.02 <= a0 <= 0.09 and 0.02 <= b0 <= 0.09
        hong += not ok
        print(f'  {"ĐẠT      " if ok else "KHÔNG ĐẠT"} · Các tuần độc lập nhau: tự viết {a0 * 100:.1f}%, arch {b0 * 100:.1f}%'.replace('.', ','))
        a5, b5 = bao_dong_gia(0.5)
        print(f'  GIỚI HẠN  · Tuần này phụ thuộc tuần trước (tự tương quan 0,5): tự viết {a5 * 100:.1f}%, arch {b5 * 100:.1f}%'.replace('.', ','))
        print('      Khi lãi lỗ theo tuần có tự tương quan, giá trị p của bản tự viết quá nhỏ (dễ kêu "có lãi" nhầm); nên đọc số của arch.')
        print(f'  ({time.time() - t0:.0f} giây)')

    tep = GOC / 'out' / 'spa-bang-tuan.csv'
    if tep.exists():
        bang = pd.read_csv(tep)
        tap1 = json.loads((GOC / 'out' / 'spa-tap-1.json').read_text(encoding='utf-8'))
        dau = bang.pop('tuan').str[:10].to_numpy()
        nguon = f'bảng ghi lúc {datetime.fromtimestamp(tep.stat().st_mtime):%H:%M ngày %d/%m/%Y}'
    else:
        print()
        print('Chưa có out/spa-bang-tuan.csv: chạy lại 11 luật và phương pháp trên vàng từ 2015 (vài phút)…', flush=True)
        sp = _nap('kiem_dinh_spa')
        bang, tap1 = sp.bang_tuan(sp.moi_lenh(json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))))
        dau = np.array([str(t)[:10] for t in bang.index])
        bang = bang.reset_index(drop=True)
        nguon = 'vừa chạy lại'
    print()
    print(f'B. Bảng lãi lỗ theo tuần thật của webapp: {len(bang)} tuần, {bang.shape[1]} chiến lược ({nguon})')
    x = bang.to_numpy(dtype=float)
    x = x[:, x.std(0) > 0]
    ac = np.array([np.corrcoef(x[:-1, j], x[1:, j])[0, 1] for j in range(x.shape[1])])
    print(f'  Tự tương quan giữa tuần này và tuần trước của {len(ac)} chuỗi lãi lỗ: trung vị {np.median(ac):+.2f}, lớn nhất {ac.max():+.2f}, '
          f'{int((ac > 0.2).sum())} chuỗi trên +0,20'.replace('.', ','))
    t0 = time.time()
    khac_kl, tom, tom_gd = 0, [], []
    for ten, cs in ((f'Tập 1 · luật và phương pháp, gộp và từng chiều: {len(tap1)} chiến lược', tap1),
                    (f'Tập 2 · thêm từng chiều trong từng phiên: {bang.shape[1]} chiến lược', list(bang.columns))):
        a, b = hai_ban(bang[cs].to_numpy(dtype=float))
        cung = (a['nhat_quan'] < 0.05) == (b['nhat_quan'] < 0.05)
        khac_kl += not cung
        tom.append((len(cs), a['nhat_quan'], b['nhat_quan']))
        print(f'  {ten}')
        print('      ' + ' · '.join(f'{nhan}: tự viết {a[k]:.3f}, arch {b[k]:.3f}'.replace('.', ',') for k, _, nhan in TEN))
        print(f'      Ở mức 5% (p nhất quán): tự viết {"có" if a["nhat_quan"] < 0.05 else "không"} ý nghĩa, arch {"có" if b["nhat_quan"] < 0.05 else "không"} ý nghĩa'
              f' → {"hai bản cùng kết luận" if cung else "HAI BẢN KHÁC KẾT LUẬN"}')
    # Tham số của luật bot và luật ba khung được chọn khi nhìn 2024–2026, nên tách riêng quãng đó ra khỏi các năm trước nó.
    print('  Tập 1 tách theo giai đoạn (mốc 1/1/2024 là lúc bắt đầu quãng mà tham số luật bot và luật ba khung được chọn):')
    for nhan, chon in (('2015–2023', dau < '2024-01-01'), ('2024–2026', dau >= '2024-01-01')):
        xs = bang.loc[chon, tap1].to_numpy(dtype=float)
        a, b = hai_ban(xs)
        tom_gd.append((nhan, a['nhat_quan'], b['nhat_quan']))
        print(f'      {nhan} ({len(xs)} tuần, {int((xs.sum(0) > 0).sum())}/{xs.shape[1]} chiến lược có tổng dương): p nhất quán tự viết {a["nhat_quan"]:.3f}, arch {b["nhat_quan"]:.3f}'.replace('.', ','))
    print(f'  ({time.time() - t0:.0f} giây)')

    if '--nhanh' not in sys.argv:
        t0 = time.time()
        print()
        print('D. Hiệu chuẩn: 300 bộ dữ liệu dựng từ bảng thật của tập 1 sau khi ép mọi chiến lược về lãi thật bằng 0 (đúng thì kêu khoảng 5% ở mức 5%)')
        ha, hb = hieu_chuan(bang[tap1].to_numpy(dtype=float))
        print(f'  Kêu "có lãi" nhầm ở mức 5% / 10% (p nhất quán): tự viết {ha[0] * 100:.1f}% / {ha[1] * 100:.1f}% · arch {hb[0] * 100:.1f}% / {hb[1] * 100:.1f}%'.replace('.', ','))
        gan = 'arch' if abs(hb[0] - 0.05) < abs(ha[0] - 0.05) else 'tự viết'
        print(f'  Bản gần mức danh nghĩa hơn: {gan}. Nên đọc giá trị p của bản đó trên dữ liệu thật.')
        print(f'  ({time.time() - t0:.0f} giây)')

    print()
    print('TỔNG: ' + ' · '.join(f'{n} chiến lược: p nhất quán tự viết {pa:.3f}, arch {pb:.3f}'.replace('.', ',') for n, pa, pb in tom)
          + ' · ' + ' · '.join(f'tập 1 riêng {g}: {pa:.3f} và {pb:.3f}'.replace('.', ',') for g, pa, pb in tom_gd)
          + f' · hai bản khác kết luận ở mức 5% trong {khac_kl} tập')
    print(f'Phép so cho thấy một bản cài tính sai: {hong}')
    sys.exit(1 if hong else 0)
