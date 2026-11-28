# -*- coding: utf-8 -*-
"""Phép thử vào lệnh trễ: nếu người dùng thấy tín hiệu rồi mới đặt lệnh sau 1, 5 hoặc 15 phút thì kết quả đổi thế nào?

Mỗi phương pháp được chạy lại trên vàng từ 2015 bằng đúng phuong_phap.cham() (mỗi lúc một lệnh, chốt 2R, chi phí của cấu hình), với giờ tín hiệu
lùi lại chừng đó phút. Mức dừng lỗ giữ nguyên như tín hiệu gốc:
- lệnh theo giá thị trường: vào ở giá mở nến 1 phút đầu tiên sau quãng trễ; khoản rủi ro (và mức chốt 2R) tính từ giá vào mới đó;
- lệnh chờ: đặt trễ. Trong quãng trễ giá đã chạm mức chờ thì coi như lỡ ("tín hiệu đã qua") và không vào.
Hạn chờ khớp của lệnh chờ cũng lùi theo cùng số phút (tối đa 15 trên 240 phút), sai khác nhỏ.
Dòng cuối là nhóm điểm mô hình từ 90, chọn cuốn chiếu theo năm như cong-cu/kiem_mo_hinh.py (chỉ 2019 trở đi).
Một lợi thế thật phải chịu được vài phút trễ; kết quả đổi dấu khi trễ vài phút thì không dùng được ngoài đời. Chỉ đọc tệp nến; không nối MT5.

    python -X utf8 cong-cu/kiem_vao_tre.py
"""
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import phuong_phap as PP  # noqa: E402

TRE = (0, 1, 5, 15)


def lui(th: list[dict], phut: int) -> list[dict]:
    return [dict(s, t=pd.Timestamp(s['t']) + pd.Timedelta(minutes=phut)) for s in th]


def dong(ten: str, th: list[dict], m1: pd.DataFrame, sp: float) -> None:
    o = []
    for phut in TRE:
        ls = PP.cham(lui(th, phut), m1, sp)
        n = len(ls)
        o.append(f'{n:>5,} lệnh {sum(x["r"] > 0 for x in ls) / max(n, 1) * 100:4.1f}% {sum(x["r"] for x in ls) / max(n, 1):+.3f}R' if n else '    không có lệnh    ')
    print(f'  {ten:<26}' + ' | '.join(o), flush=True)


if __name__ == '__main__':
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    spec = importlib.util.spec_from_file_location('kslcl', GOC / 'cong-cu' / 'kiem_so_lenh_cung_luc.py')
    k = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(k)
    m1, chon, sp = k.chon_cuon_chieu(cfg)                              # nến 1 phút từ 2015 và các tín hiệu có điểm từ 90
    from so_cong_khai import hoc                                       # noqa: E402
    fr = hoc._khung(m1, cfg['gia'])
    print('Vàng từ 2015, chốt 2R, mỗi lúc một lệnh, chi phí của cấu hình. Mỗi ô: số lệnh · tỷ lệ thắng · R mỗi lệnh.')
    print(f'  {"":<26}' + ' | '.join(f'{"vào ngay" if p == 0 else f"trễ {p} phút":^26}' for p in TRE))
    for ma, tt in PP.DS.items():
        dong(f'{ma} ({"lệnh chờ" if tt.get("cho") else "thị trường"})', PP.quet(ma, fr['M15'], fr['H1']), m1, sp)
    dong('điểm mô hình từ 90 (2019+)', [s for s, _ in chon], m1, sp)
