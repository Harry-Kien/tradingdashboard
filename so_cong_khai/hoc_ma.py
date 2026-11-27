"""Đo các phương pháp tùy chọn trên dữ liệu của chính một mã ngoài vàng (BTC, EURUSD, ...).

Cùng quy tắc và cùng cách thống kê với hoc.py (chia 70% học, 30% kiểm; theo chiều, phiên, biên độ), nhưng dữ liệu là nến 5 phút của năm
đang xem đọc từ MT5 demo đang mở. Khác với phần đo trên vàng ở ba chỗ, và cả ba đều được ghi vào kết quả để trang nói rõ:

- MT5 chỉ giữ chừng 100.000 nến mỗi khung, nên nến 1 phút chỉ có khoảng 69 ngày. Vì vậy lệnh được chấm bằng nến 5 phút: thô hơn nến 1 phút,
  và khi một nến chạm cả dừng lỗ lẫn chốt lời thì vẫn tính dừng lỗ.
- Spread lấy trung vị của chính dữ liệu (cột spread của MT5). Phí hoa hồng của sàn không có trong dữ liệu: trừ theo mức người dùng ghi trong
  Cài đặt (USD mỗi lot, cả mở và đóng); chưa ghi thì chưa trừ.
- Lãi lỗ quy ra USD ở 0,01 lot theo giá trị một bước giá mà MT5 đang báo cho mã đó.

Chỉ đọc nến của mã đang hiện trong Market Watch; không chọn mã, không đặt lệnh.
"""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from . import da_ma, gia, hoc, phuong_phap, song, duong

PHIEN_BAN = 5                                   # 5: lãi lỗ theo tháng; 4: mô phỏng lại chuỗi lệnh; 3: trừ hoa hồng theo Cài đặt; 2: thêm điểm khớp quá khứ (PBO, DSR)
TOI_DA_M5 = 99_999         # MT5 từ chối lời đọc từ 100.000 nến trở lên
BUOC = 5                   # số phút của nến dùng để chấm lệnh
_khoa = threading.Lock()
_tt: dict = {}             # mã -> {'key', 'kq', 'dang', 'loi', 'bat_dau'}


def _doc(cfg: dict, ma: str, now: datetime) -> tuple[pd.DataFrame, float, float, object]:
    """(nến 5 phút đã đóng từ đầu năm, spread trung vị theo giá, hệ số quy ra USD ở 0,01 lot hoặc None, thông tin mã)."""
    mt5 = da_ma._mt5(cfg['gia'])
    if mt5 is None:
        raise ValueError(f'chưa có giá trực tiếp từ MT5 ({song.ly_do() or "chưa nối"})')
    tu = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    n = max(1000, min(TOI_DA_M5, int((now - tu).total_seconds() // (BUOC * 60)) + 5))
    with song._khoa:
        hien = da_ma._hien(mt5)
        if ma not in hien:
            raise ValueError(f'mã {ma} không có trong Market Watch của MT5')
        s = hien[ma]
        r = None
        while r is None or len(r) == 0:
            r = mt5.copy_rates_from_pos(ma, mt5.TIMEFRAME_M5, 1, n)
            if r is None or len(r) == 0:
                if n <= 2000:
                    raise RuntimeError(f'MT5 không trả nến M5 của {ma}')
                n //= 2
    df = pd.DataFrame(r)
    df.index = pd.to_datetime(df['time'], unit='s', utc=True)
    df = df[df.index >= tu]
    diem = float(getattr(s, 'point', 0) or 10.0 ** -int(s.digits))
    sp = float(df['spread'].median()) * diem if 'spread' in df else 0.0
    if sp <= 0:                                                    # dữ liệu không ghi spread: dùng spread MT5 đang báo
        sp = float(getattr(s, 'spread', 0) or 0) * diem
    tv, ts = float(getattr(s, 'trade_tick_value', 0) or 0), float(getattr(s, 'trade_tick_size', 0) or 0)
    he_so = tv / ts * 0.01 if tv > 0 and ts > 0 else None
    return df[['open', 'high', 'low', 'close']].astype(float), sp, he_so, s


def chay(cfg: dict, ma: str, now: datetime | None = None) -> dict:
    """Chạy lại mọi phương pháp tùy chọn trên nến của mã `ma` từ đầu năm. Cùng dạng kết quả với hoc.chay()."""
    now = now or datetime.now(timezone.utc)
    m5, sp, he_so, s = _doc(cfg, ma, now)
    hh = hoc.hoa_hong(cfg) if he_so else 0.0                       # không quy được ra USD thì không trừ được hoa hồng tính bằng USD
    phi = hh / 100 / he_so if hh else 0.0                          # hoa hồng ở 0,01 lot, đổi ra đơn vị giá: cham() nhân lại với he_so
    if len(m5) < 3000:
        raise ValueError(f'MT5 chỉ có {len(m5)} nến M5 của {ma} trong năm nay, chưa đủ để đo')
    d = int(s.digits)
    het = m5.index[-1] + timedelta(minutes=BUOC)
    fr = {}
    for tf, rule, phut in (('M15', '15min', 15), ('H1', '1h', 60)):
        b = m5.resample(rule, origin='epoch', label='left', closed='left').agg(gia._OHLC).dropna()
        fr[tf] = b[b.index + timedelta(minutes=phut) <= het]
    tu = m5.index[0]
    cat = tu + (het - tu) * hoc.TY_LE_HOC
    ti = hoc.ty_le_bien_do(fr['H1'])
    vn = lambda x: f'{x:,.{d}f}'.translate(str.maketrans(',.', '.,'))          # noqa: E731
    out: dict = {'phien_ban': PHIEN_BAN, 'ma': ma, 'tinh_luc': now.isoformat(), 'tu_nam': now.year, 'luat': {}, 'loi': [],
                 'tu': tu.isoformat(), 'den': het.isoformat(), 'cat': cat.isoformat(), 'so_ngay': int((het - tu).days), 'spread': round(sp, d), 'hoa_hong_lot': hh,
                 'gia_dau': round(float(m5['open'].iloc[0]), d), 'gia_cuoi': round(float(m5['close'].iloc[-1]), d), 'so_nen': len(m5),
                 'don_vi': 'USD ở 0,01 lot' if he_so else 'đơn vị giá',
                 'ghi_chu': f'Đo trên chính {ma}, nến 5 phút đọc từ MT5 demo. Lệnh chấm bằng nến 5 phút (thô hơn nến 1 phút dùng cho vàng; nến chạm cả '
                            f'dừng lỗ lẫn chốt lời thì tính dừng lỗ). Đã trừ spread {vn(sp)}; ' + (f'đã trừ hoa hồng {hoc._vn(hh)} USD mỗi lot. ' if hh else 'phí hoa hồng của sàn chưa được trừ (ghi trong Cài đặt để trừ). ') + 'Chưa đầy một năm dữ liệu, '
                            'nên nửa kiểm chỉ dài khoảng ba tháng.'}
    lenh_pp: dict = {}
    for pp in phuong_phap.DS:
        try:
            th = phuong_phap.quet(pp, fr['M15'], fr['H1'])
            ls = phuong_phap.cham(th, m5, sp, phi=phi, buoc=BUOC, he_so=he_so or 1.0)
            ls2 = phuong_phap.cham(th, m5, sp, phi=phi, buoc=BUOC, he_so=he_so or 1.0, theo_muc_tieu=True)
            ls1 = phuong_phap.cham(th, m5, sp, phi=phi, buoc=BUOC, he_so=he_so or 1.0, tp_r=1.0)
            lenh_pp.update({pp: ls, f'{pp}·1R': ls1, f'{pp}·mục tiêu': ls2})
            out['luat'][pp] = {'cach': f'Chạy lại đúng quy tắc của phương pháp trên nến 5 phút của {ma}: mỗi lúc một lệnh, chốt ở {phuong_phap.TP_R:g}R, '
                                       f'giữ tối đa {phuong_phap.GIU_PHUT // 60} giờ, đã trừ spread, '
                                       + (f'đã trừ hoa hồng {hoc._vn(hh)} USD mỗi lot.' if hh else 'chưa trừ phí hoa hồng.'),
                               'tat_ca': hoc._so(ls), 'theo': hoc.thong_ke(ls, ti, cat),
                               'theo_muc_tieu': {'tat_ca': hoc._so(ls2), **{k: v for k, v in hoc.thong_ke(ls2, ti, cat).items() if '|' not in k}},
                               'r1': {'tat_ca': hoc._so(ls1), **{k: v for k, v in hoc.thong_ke(ls1, ti, cat).items() if '|' not in k}}}
            hoc._them_mo_phong(out['luat'][pp], ls, 'thang')                # chưa đầy một năm dữ liệu: xét theo tháng
        except Exception as e:                                             # noqa: BLE001 - một phương pháp hỏng không chặn phương pháp khác
            out['loi'].append(f'{pp}: {type(e).__name__}: {e}')
    try:                                                                   # điểm khớp quá khứ (dữ liệu ngắn: tính theo tuần)
        from . import qua_khop                                             # noqa: PLC0415
        out['qua_khop'] = qua_khop.danh_gia(lenh_pp)
    except Exception as e:                                                 # noqa: BLE001
        out['loi'].append(f'Điểm khớp quá khứ: {type(e).__name__}: {e}')
    return out


def _tep(out: Path, ma: str) -> Path:
    return Path(out) / f'hoc-{re.sub(r"[^A-Za-z0-9_.-]", "_", ma)}.json'


def lay(cfg: dict, out: Path, ma: str, cho: bool = False, now: datetime | None = None) -> dict:
    """Kết quả của mã `ma` nếu đã có cho hôm nay (bộ nhớ hoặc out/hoc-<mã>.json); chưa có thì tính ở nền và trả {'san_sang': False}."""
    now = now or datetime.now(timezone.utc)
    key = json.dumps([PHIEN_BAN, hoc.PHIEN_BAN, ma, now.date().isoformat(), hoc.hoa_hong(cfg)])
    with _khoa:
        tt = _tt.setdefault(ma, {'key': None, 'kq': None, 'dang': False, 'loi': None, 'bat_dau': None})
        if tt['key'] == key and tt['kq'] is not None:
            return {'san_sang': True, **tt['kq']}
        if tt['key'] != key:
            tt.update(key=key, kq=None, loi=None)
            try:
                saved = json.loads(_tep(out, ma).read_text(encoding='utf-8'))
                if saved.get('key') == key:
                    tt['kq'] = saved['kq']
                    return {'san_sang': True, **tt['kq']}
            except (OSError, ValueError, KeyError):
                pass
        if tt['loi']:
            return {'san_sang': False, 'dang_tinh': False, 'loi': [tt['loi']]}
        start = not tt['dang']
        if start:
            tt.update(dang=True, bat_dau=datetime.now(timezone.utc))

    def lam():
        try:
            kq = chay(cfg, ma, now)
            with _khoa:
                if tt['key'] == key:
                    tt['kq'] = kq
            try:
                Path(out).mkdir(parents=True, exist_ok=True)
                _tep(out, ma).write_text(json.dumps({'key': key, 'kq': kq}, ensure_ascii=False), encoding='utf-8')
            except OSError:
                pass
        except Exception as e:                                             # noqa: BLE001
            with _khoa:
                tt['loi'] = f'{type(e).__name__}: {e}'
        finally:
            with _khoa:
                tt['dang'] = False

    if cho:
        if start:
            lam()
        with _khoa:
            return {'san_sang': True, **tt['kq']} if tt['kq'] is not None else {'san_sang': False, 'dang_tinh': tt['dang'], 'loi': [tt['loi']] if tt['loi'] else []}
    if start:
        threading.Thread(target=lam, name=f'hoc-{ma}', daemon=True).start()
    return {'san_sang': False, 'dang_tinh': True, 'da_giay': int((datetime.now(timezone.utc) - tt['bat_dau']).total_seconds())}


if __name__ == '__main__':                                                 # python -X utf8 -m so_cong_khai.hoc_ma BTCUSDTp
    import sys
    cfg_ = json.loads((duong.goc_du_lieu() / 'cau-hinh.json').read_text(encoding='utf-8'))
    kq_ = chay(cfg_, sys.argv[1] if len(sys.argv) > 1 else 'BTCUSDTp')
    print(kq_['ma'], kq_['tu'][:10], '→', kq_['den'][:10], 'cắt', kq_['cat'][:10], '·', kq_['so_nen'], 'nến M5 · spread', kq_['spread'], '·', kq_['don_vi'], kq_['loi'])
    for pp_, r_ in kq_['luat'].items():
        print(f'\n{pp_}: tất cả {r_["tat_ca"]}')
        for k_, s_ in sorted(r_['theo'].items()):
            if k_.count('|') <= 1:
                print(f'  {k_:<16} n={s_["n"]:>4} lãi {s_["ty_le"]:>5}% tb {s_["usd_tb"]:>+7.2f} | học n={s_["hoc"]["n"]} tb {s_["hoc"].get("usd_tb", 0):+.2f} '
                      f'| kiểm n={s_["kiem"]["n"]} tb {s_["kiem"].get("usd_tb", 0):+.2f} | {s_["nhan_xet"]}')
