# -*- coding: utf-8 -*-
"""Đo các bản chuẩn hóa theo sách của hai phương pháp ICT, theo đúng luật và cổng đã ghi trước ở cong-cu/CHUAN_HOA_DANG_KY.md.

Ba bản cho mỗi phương pháp (ict, ict_fvg), đo trên vàng từ 2015 bằng đúng phép chấm của webapp (phuong_phap.quet + phuong_phap.cham):
  B0  bản trước ngày 24/11/2026 (không xét nến giữa, không đòi hợp lưu);
  B1  thay đổi 1: khoảng trống giá chỉ tính khi nến giữa cùng chiều (FVG_NEN_GIUA);
  B2  thay đổi 1 + thay đổi 2: đòi đủ các điều kiện hợp lưu ICT (ICT_HOP_LUU).
Thay đổi 1 là sửa định nghĩa, không có cổng lãi lỗ. Thay đổi 2 qua cổng khi mỗi nửa (HỌC trước 1/5/2023, KIỂM từ 1/5/2023) còn ít nhất 200 lệnh
VÀ R trung bình mỗi lệnh của B2 cao hơn B1 ở cả hai nửa. Công cụ chỉ đo và in kết luận theo cổng; nó không tự đổi công tắc trong mã.
Hai công tắc bị đổi tạm trong bộ nhớ của tiến trình này và được trả lại ngay. Chỉ đọc tệp nến; không nối MT5. Kết quả ghi ở out/chuan-hoa.json.

    python -X utf8 cong-cu/chuan_hoa.py
"""
import json
import sys
import time
from pathlib import Path

import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import hoc, phuong_phap as PP  # noqa: E402

MOC = pd.Timestamp('2023-05-01', tz='UTC')
TOI_THIEU = 200
BAN = (('B0', False, False), ('B1', True, False), ('B2', True, True))


def so_do(ls: list[dict]) -> dict:
    n = len(ls)
    if not n:
        return {'n': 0, 'thang': None, 'r_tb': None, 'tong_r': 0.0}
    r = [x['r'] for x in ls]
    return {'n': n, 'thang': round(sum(x > 0 for x in r) / n * 100, 1), 'r_tb': round(sum(r) / n, 4), 'tong_r': round(sum(r), 1)}


def do(ma: str, m15, h1, m1, sp: float) -> dict:
    """{bản: {'tin_hieu', 'ca', 'hoc', 'kiem'}} cho phương pháp `ma`. Trả lại hai công tắc về giá trị cũ dù có lỗi."""
    cu = PP.FVG_NEN_GIUA, PP.ICT_HOP_LUU
    out = {}
    try:
        for ten, giua, hl in BAN:
            PP.FVG_NEN_GIUA, PP.ICT_HOP_LUU = giua, hl
            th = PP.quet(ma, m15, h1)
            ls = PP.cham(th, m1, sp)
            truoc = [x for x in ls if pd.Timestamp(x['t']) < MOC]
            sau = [x for x in ls if pd.Timestamp(x['t']) >= MOC]
            out[ten] = {'tin_hieu': len(th), 'ca': so_do(ls), 'hoc': so_do(truoc), 'kiem': so_do(sau)}
    finally:
        PP.FVG_NEN_GIUA, PP.ICT_HOP_LUU = cu
    return out


def qua_cong(b1: dict, b2: dict) -> tuple[bool, str]:
    """Cổng của thay đổi 2: đủ lệnh ở mỗi nửa và R trung bình cao hơn ở cả hai nửa."""
    if b2['hoc']['n'] < TOI_THIEU or b2['kiem']['n'] < TOI_THIEU:
        return False, f'không đủ lệnh (HỌC {b2["hoc"]["n"]}, KIỂM {b2["kiem"]["n"]}; cần ít nhất {TOI_THIEU} mỗi nửa)'
    hon = [b2[k]['r_tb'] > b1[k]['r_tb'] for k in ('hoc', 'kiem')]
    if all(hon):
        return True, 'R trung bình cao hơn ở cả hai nửa và đủ lệnh'
    return False, 'R trung bình không cao hơn ở ' + ' và '.join(t for t, h in zip(('nửa HỌC', 'nửa KIỂM'), hon) if not h)


if __name__ == '__main__':
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    t0 = time.time()
    m1 = hoc._m1_dai(g, 2015)
    fr = hoc._khung(m1, g)
    sp = float(g.get('spread', 0.17))
    print(f'Vàng từ 2015: {len(fr["M15"]):,} nến M15 · spread {sp:g} · phí {PP.PHI:g} · chốt {PP.TP_R:g}R · mốc chia hai nửa {MOC:%d/%m/%Y} · nạp {time.time() - t0:.0f} giây', flush=True)
    kq, so = {}, lambda x: '—' if x is None else f'{x:+.3f}'.replace('.', ',')      # noqa: E731
    for ma in ('ict', 'ict_fvg'):
        t0 = time.time()
        kq[ma] = do(ma, fr['M15'], fr['H1'], m1, sp)
        print(f'\n{PP.DS[ma]["ten"]} ({ma}) · {time.time() - t0:.0f} giây')
        print('  bản · tín hiệu · lệnh · thắng · R mỗi lệnh · tổng R │ HỌC: lệnh, thắng, R mỗi lệnh │ KIỂM: lệnh, thắng, R mỗi lệnh')
        for ten, _, _ in BAN:
            x = kq[ma][ten]
            print(f'  {ten} · {x["tin_hieu"]:>6,} · {x["ca"]["n"]:>5,} · {x["ca"]["thang"]}% · {so(x["ca"]["r_tb"])} · {x["ca"]["tong_r"]:+.1f} │ '
                  f'{x["hoc"]["n"]:,}, {x["hoc"]["thang"]}%, {so(x["hoc"]["r_tb"])} │ {x["kiem"]["n"]:,}, {x["kiem"]["thang"]}%, {so(x["kiem"]["r_tb"])}')
        dat, vi = qua_cong(kq[ma]['B1'], kq[ma]['B2'])
        kq[ma]['cong_2'] = {'qua': dat, 'vi': vi}
        print(f'  Thay đổi 1 (định nghĩa khoảng trống giá): áp dụng theo bản đăng ký, không có cổng lãi lỗ. Bỏ {kq[ma]["B0"]["tin_hieu"] - kq[ma]["B1"]["tin_hieu"]:,} tín hiệu.')
        print(f'  Thay đổi 2 (đủ điều kiện hợp lưu): {"QUA CỔNG" if dat else "KHÔNG QUA CỔNG"}: {vi}.')
    (GOC / 'out').mkdir(exist_ok=True)
    (GOC / 'out' / 'chuan-hoa.json').write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding='utf-8')
