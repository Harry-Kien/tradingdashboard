"""Đo chỉ báo "Khối lượng đột biến" (tick volume của MT5) đúng cách đã ghi trước trong cong-cu/CHUAN_HOA_DANG_KY.md (mục ghi ngày 26/11/2026).

    python -X utf8 cong-cu/do_khoi_luong.py [--goc http://127.0.0.1:8765]

Đọc nến vàng M5, M15, H1 kèm tick volume qua webapp đang chạy (/api/gia, chỉ đọc; webapp phải đang nối MT5). Không tự nối MT5, không đặt lệnh.
Nến đột biến: tick volume ≥ 2 lần trung bình 20 nến đóng trước, thân ≥ 50% biên độ, thuận EMA50. Xét 4 nến sau: "đi tiếp" khi giá đóng nến thứ 4
vượt giá đóng nến đột biến theo đúng chiều. Mốc so sánh: nến thuận EMA50, thân ≥ 50%, khối lượng dưới 2 lần. Ghi out/khoi-luong-dot-bien.json."""
from __future__ import annotations

import argparse
import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
N_NEN, NGUONG, THAN, SAU = 20, 2.0, 0.5, 4


def doc(goc: str, tf: str) -> pd.DataFrame:
    with urllib.request.urlopen(f'{goc}/api/gia?tf={tf}&n=1500', timeout=300) as r:
        d = json.loads(r.read())
    if d.get('nguon') != 'mt5' or not d.get('vol'):
        raise SystemExit(f'{tf}: webapp chưa có tick volume (đang không nối MT5 trực tiếp).')
    b = pd.DataFrame(d['candles'], columns=['t', 'open', 'high', 'low', 'close'])
    b['vol'] = pd.to_numeric(b['t'].astype(str).map(d['vol']), errors='coerce')       # vol: {giờ mở nến: tick volume}
    return b


def doc_lon(goc: str, tf: str) -> tuple[pd.DataFrame, int]:
    """Mẫu lớn (đăng ký bổ sung 26/11/2026): nến từ /api/gia-cu ghép với tick volume từ /api/khoi-luong theo giờ mở nến. Trả (nến có volume, số nến bị bỏ)."""
    with urllib.request.urlopen(f'{goc}/api/gia-cu?tf={tf}', timeout=600) as r:
        d = json.loads(r.read())
    with urllib.request.urlopen(f'{goc}/api/khoi-luong?tf={tf}&n=60000', timeout=600) as r:
        k = json.loads(r.read())
    if not k.get('t'):
        raise SystemExit(f'{tf}: webapp chưa có tick volume ({k.get("ly_do")}).')
    b = pd.DataFrame(d['candles'], columns=['t', 'open', 'high', 'low', 'close'])
    b['vol'] = b['t'].map(dict(zip(k['t'], k['v'])))
    bo = int(b['vol'].isna().sum())
    return b.dropna(subset=['vol']).reset_index(drop=True), bo


def do(b: pd.DataFrame, den: int | None = None) -> dict:
    o, h, l, c, v = b['open'], b['high'], b['low'], b['close'], b['vol']
    rel = v / v.shift(1).rolling(N_NEN).mean()
    e50 = c.ewm(span=50, adjust=False, min_periods=50).mean()
    c0 = c.shift(1)
    tr = pd.concat([h - l, (h - c0).abs(), (l - c0).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    sg = np.sign(c - o)
    than = (c - o).abs() >= THAN * (h - l)
    thuan = ((sg > 0) & (c > e50)) | ((sg < 0) & (c < e50))
    tien = (c.shift(-SAU) - c) * sg / atr                                      # biến động 4 nến sau theo chiều nến, tính bằng ATR
    co = rel.notna() & than & thuan & tien.notna() & (h > l)
    if den is not None:
        co &= b['t'] < den                                                      # chỉ phần không trùng với lần đo trước
    nhom = {'dot_bien': co & (rel >= NGUONG), 'moc': co & (rel < NGUONG)}
    out = {}
    for k, m in nhom.items():
        x = tien[m]
        out[k] = {'so_lan': int(m.sum()), 'ty_le_di_tiep': round(float((x > 0).mean()), 3) if len(x) else None,
                  'bien_dong_tb_atr': round(float(x.mean()), 3) if len(x) else None}
    a, z = out['dot_bien'], out['moc']
    if a['so_lan'] and z['so_lan']:
        p1, p2, n1, n2 = a['ty_le_di_tiep'], z['ty_le_di_tiep'], a['so_lan'], z['so_lan']
        se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
        out['chenh'] = round(p1 - p2, 3)
        out['tin_cay_90'] = [round(p1 - p2 - 1.645 * se, 3), round(p1 - p2 + 1.645 * se, 3)]
        out['ket_luan'] = ('chưa đủ dữ liệu' if n1 < 30 else 'có lợi thế trên mẫu này' if out['tin_cay_90'][0] > 0 else 'chưa thấy lợi thế')
    else:
        out['ket_luan'] = 'chưa đủ dữ liệu'
    t = pd.to_datetime(b['t'], unit='s', utc=True)
    out['tu'], out['den'] = t.iloc[0].isoformat(), t.iloc[-1].isoformat()
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--goc', default='http://127.0.0.1:8765')
    ap.add_argument('--mau-lon', action='store_true', help='mẫu lớn theo đăng ký bổ sung: nến từ đầu năm ghép tick volume MT5 còn giữ')
    a = ap.parse_args(argv)
    if a.mau_lon:
        return mau_lon(a.goc)
    kq = {'luc': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'dinh_nghia': {'n': N_NEN, 'nguong': NGUONG, 'than': THAN, 'sau': SAU},
          'khung': {tf: do(doc(a.goc, tf)) for tf in ('M5', 'M15', 'H1')}}
    p = GOC / 'out' / 'khoi-luong-dot-bien.json'
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding='utf-8')
    for tf, r in kq['khung'].items():
        a_, z = r['dot_bien'], r['moc']
        print(f"{tf}: {r['tu'][:16]} → {r['den'][:16]} | đột biến {a_['so_lan']} lần, đi tiếp {a_['ty_le_di_tiep']}, TB {a_['bien_dong_tb_atr']} ATR"
              f" | mốc {z['so_lan']} lần, đi tiếp {z['ty_le_di_tiep']}, TB {z['bien_dong_tb_atr']} ATR | chênh {r.get('chenh')} {r.get('tin_cay_90')} → {r['ket_luan']}")
    return 0



def mau_lon(goc: str) -> int:
    cu = json.loads((GOC / 'out' / 'khoi-luong-dot-bien.json').read_text(encoding='utf-8'))['khung']     # lần đo đầu: mốc tách phần không trùng
    kq = {'luc': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'dinh_nghia': {'n': N_NEN, 'nguong': NGUONG, 'than': THAN, 'sau': SAU}, 'khung': {}}
    for tf in ('M5', 'M15', 'H1'):
        b, bo = doc_lon(goc, tf)
        den = int(pd.Timestamp(cu[tf]['tu']).timestamp())
        kq['khung'][tf] = {'so_nen': len(b), 'bo': bo, 'ca_mau': do(b), 'khong_trung': do(b, den), 'moc_tach': cu[tf]['tu']}
    p = GOC / 'out' / 'khoi-luong-dot-bien-mau-lon.json'
    p.write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding='utf-8')
    for tf, r in kq['khung'].items():
        for ten in ('khong_trung', 'ca_mau'):
            x = r[ten]
            a_, z = x['dot_bien'], x['moc']
            print(f"{tf} {ten:11} ({r['so_nen']} nến, bỏ {r['bo']}): đột biến {a_['so_lan']}, đi tiếp {a_['ty_le_di_tiep']}, TB {a_['bien_dong_tb_atr']} ATR"
                  f" | mốc {z['so_lan']}, đi tiếp {z['ty_le_di_tiep']}, TB {z['bien_dong_tb_atr']} ATR | chênh {x.get('chenh')} {x.get('tin_cay_90')} → {x['ket_luan']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
