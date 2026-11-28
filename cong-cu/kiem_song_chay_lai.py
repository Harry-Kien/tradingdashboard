# -*- coding: utf-8 -*-
"""Kiểm: tín hiệu mà trang sống thấy có trùng với tín hiệu của phép chạy lại không.

Trang sống gọi phuong_phap.quet() trên 400 nến M15 gần nhất (H1: 1.000 nến MT5 trả về); phép chạy lại gọi quet() một lần trên toàn bộ lịch sử.
Nếu hai cách cho tín hiệu khác nhau thì số đo quá khứ không nói về những gì trang thật sự hiện. Phép kiểm này cắt chuỗi nến ở nhiều thời điểm,
chỉ đưa cho quet() phần nến TRƯỚC điểm cắt (đúng như lúc sống), rồi so với tín hiệu của lần chạy trên toàn bộ lịch sử: phải cùng nến, cùng
chiều, cùng mức vào và cùng dừng lỗ. Vì lần chạy cắt không có nến tương lai, hai bên trùng nhau cũng có nghĩa quet() không nhìn trước.

Điểm cắt: tới 600 nến có tín hiệu của mỗi phương pháp (lấy ngẫu nhiên, hạt giống cố định) cộng 600 nến bất kỳ, từ năm đã cho.
Chỉ đọc tệp nến; không nối MT5. Thoát với mã 1 nếu có chỗ lệch.

    python -X utf8 cong-cu/kiem_song_chay_lai.py [năm bắt đầu, mặc định 2025]
"""
import json
import sys
import time
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import hoc, phuong_phap as PP  # noqa: E402

CUA_M15, CUA_H1 = 400, 1000        # số nến trang sống đưa cho quet(): hien_tai() lấy 400 nến M15, song.SO_NEN lấy 1.000 nến H1


def khoa(s):
    return (pd.Timestamp(s['t']).value, s['huong'], round(s['vao'], 3), round(s['sl'], 3))


def so_sanh(ma, m15, h1, cat):
    """Với mỗi điểm cắt c (số nến M15 đã đóng lúc đó): tín hiệu quet() thấy khi chỉ có nến trước c, so với tín hiệu của lần chạy toàn bộ.
    Trả (số điểm cắt có tín hiệu và trùng, [(giờ, tín hiệu chạy lại, tín hiệu lúc sống)] các chỗ lệch)."""
    xa = PP.CHO_NEN if PP.DS[ma].get('cho') else 1                 # hien_tai() nhìn lại chừng này nến
    theo_i = {}
    for s in PP.quet(ma, m15, h1):
        theo_i.setdefault(s['i'], []).append(s)
    h1_dong = (h1.index + timedelta(hours=1)).as_unit('ns').asi8
    dung, lech = 0, []
    for c in cat:
        w = m15.iloc[max(0, c - CUA_M15):c]
        k = int(np.searchsorted(h1_dong, (w.index[-1] + timedelta(minutes=15)).value, side='right'))        # chỉ nến H1 đã đóng lúc đó
        song = {khoa(s) for s in PP.quet(ma, w, h1.iloc[max(0, k - CUA_H1):k]) if s['i'] >= len(w) - xa}
        day = {khoa(s) for i in range(c - xa, c) for s in theo_i.get(i, [])}
        if song == day:
            dung += bool(day)
        else:
            lech.append((w.index[-1], sorted(x[1:] for x in day), sorted(x[1:] for x in song)))
    return dung, lech, sorted(theo_i)


if __name__ == '__main__':
    tu_nam = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    g = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))['gia']
    fr = hoc._khung(hoc._m1_dai(g, tu_nam - 1), g)                 # thêm một năm phía trước để lần chạy toàn bộ có lịch sử dài hơn cửa sổ sống
    m15, h1 = fr['M15'], fr['H1']
    tu = max(CUA_M15, int(np.searchsorted(m15.index, pd.Timestamp(f'{tu_nam}-01-01', tz='UTC'))))
    rng = np.random.default_rng(7)
    print(f'Vàng: {len(m15):,} nến M15, {len(h1):,} nến H1 · điểm cắt từ {m15.index[tu].date()} tới {m15.index[-1].date()} · cửa sổ sống {CUA_M15} nến M15, {CUA_H1} nến H1')
    tong_lech = 0
    for ma in PP.DS:
        t1 = time.time()
        co = [i for i in sorted({s['i'] for s in PP.quet(ma, m15, h1)}) if i >= tu]
        cat = sorted({int(i) + 1 for i in (rng.choice(co, size=min(600, len(co)), replace=False) if co else [])} | {int(x) for x in rng.integers(tu, len(m15), size=600)})
        dung, lech, _ = so_sanh(ma, m15, h1, cat)
        tong_lech += len(lech)
        print(f'{ma}: {len(cat)} điểm cắt · có tín hiệu và trùng {dung} · lệch {len(lech)} · {time.time() - t1:.0f} giây')
        for t, a, b in lech[:3]:
            print(f'   lệch tại nến {t}: chạy lại {a} · lúc sống {b}')
    print(f'\nTỔNG: {tong_lech} chỗ lệch')
    sys.exit(1 if tong_lech else 0)
