"""Học từ dữ liệu nhiều năm: chạy lại từng luật trên nến 1 phút của vàng từ năm `tu_nam` tới nay, rồi thống kê riêng cho từng
BỐI CẢNH (chiều lệnh, phiên giao dịch, biên độ), để khi bấm "Phân tích" trang trả lời được: những lần trước, trong bối cảnh
giống lúc này, luật này kết thúc ra sao.

"Học" ở đây là đếm và so sánh, không phải huấn luyện một mô hình: mỗi luật chỉ có vài trăm tới vài nghìn lệnh, quá ít để một
mô hình máy học không tự lừa mình. Để một bộ lọc bối cảnh không chỉ đẹp vì trùng hợp, dữ liệu được cắt theo thời gian thành nửa
"học" (70% đầu) và nửa "kiểm" (30% cuối); bối cảnh chỉ được coi là giữ được khi có lãi ở CẢ HAI nửa và mỗi nửa đủ 30 lệnh.

Cách chấm từng lệnh dùng nguyên bộ kiểm của dự án (xem kiem_chung.py). Chỉ đọc tệp giá; không nối MT5, không đặt lệnh, không gọi API.
Dự án đã nhìn thấy toàn bộ dữ liệu này khi chọn tham số, nên đây vẫn không phải kiểm ngoài mẫu độc lập."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from . import gia, kiem_chung, phuong_phap

PHIEN_BAN = 14
PHIEN = (('Á', 0, 7), ('Âu', 7, 12), ('Mỹ', 12, 20), ('cuối ngày', 20, 24))        # theo giờ UTC của lúc vào lệnh
MUC = (0.8, 1.25)                                  # ATR14 H1 so với trung vị 720 nến H1: dưới 0,8 là thấp, trên 1,25 là cao
TOI_THIEU = 30                                     # số lệnh ít nhất ở mỗi nửa để dám nhận xét
TY_LE_HOC = 0.7
_tt: dict = {'key': None, 'kq': None, 'dang': False, 'loi': None, 'bat_dau': None}
_khoa = threading.Lock()


def phien(t) -> str:
    h = pd.Timestamp(t).tz_convert('UTC').hour if pd.Timestamp(t).tzinfo else pd.Timestamp(t).hour
    return next(ten for ten, a, b in PHIEN if a <= h < b)


def ty_le_bien_do(h1: pd.DataFrame) -> pd.Series:
    """ATR14 của H1 chia cho trung vị của chính nó trong 720 nến H1 gần nhất (khoảng 30 ngày giao dịch)."""
    hi, lo, pc = h1['high'].astype(float), h1['low'].astype(float), h1['close'].astype(float).shift(1)
    tr = pd.concat([hi - lo, (hi - pc).abs(), (lo - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    return atr / atr.rolling(720, min_periods=240).median()


def muc(x) -> str | None:
    if x is None or x != x:
        return None
    return 'thấp' if x < MUC[0] else 'cao' if x > MUC[1] else 'vừa'


def boi_canh_luc(h1: pd.DataFrame, t: datetime) -> dict:
    """Bối cảnh của một thời điểm, cùng cách tính với lúc thống kê: phiên theo giờ UTC, biên độ theo nến H1 đã đóng gần nhất."""
    ti = ty_le_bien_do(h1).dropna()
    k = int(ti.index.searchsorted(pd.Timestamp(t) - timedelta(hours=1), side='right')) - 1
    x = float(ti.iloc[k]) if k >= 0 else None
    return {'phien': phien(t), 'bien_do': muc(x), 'bien_do_ty_le': round(x, 2) if x is not None else None}


# ---- dữ liệu dài -----------------------------------------------------------------------------------------------------
def _m1_dai(g: dict, tu_nam: int) -> pd.DataFrame:
    """Nến 1 phút từ tệp xuất của MT5 (nhiều năm) nối với kho nến của webapp cho phần mới hơn. Chỉ số là giờ mở nến, UTC."""
    goc = Path(os.path.expandvars(g.get('d1_goc') or 'khong-co')).with_name('XAUUSDp_M1.csv')
    parts = []
    if goc.exists():
        moc = f'{tu_nam}.01.01'
        for c in pd.read_csv(goc, sep='\t', usecols=[0, 1, 2, 3, 4, 5], names=['d', 't', 'open', 'high', 'low', 'close'], header=0, chunksize=750_000, dtype={'d': str, 't': str}):
            c = c[c['d'] >= moc]
            if len(c):
                c.index = pd.to_datetime(c['d'] + ' ' + c['t'], format='%Y.%m.%d %H:%M:%S', utc=True)
                parts.append(c[['open', 'high', 'low', 'close']].astype(float))
    cu = pd.concat(parts) if parts else None
    moi = kiem_chung._m1(g)
    if cu is None:
        return moi
    m1 = pd.concat([cu, moi[moi.index > cu.index[-1]]])
    return m1[~m1.index.duplicated(keep='last')].sort_index()


def _khung(m1: pd.DataFrame, g: dict) -> dict:
    """Các khung lớn hơn ghép từ nến 1 phút, chỉ nến đã đóng; D1 nối với tệp D1 nhiều năm để đủ lịch sử cho EMA200."""
    het = m1.index[-1] + timedelta(minutes=1)
    fr = {}
    for tf, rule in gia._QUY.items():
        b = m1.resample(rule, origin='epoch', label='left', closed='left').agg(gia._OHLC).dropna()
        fr[tf] = b[b.index + timedelta(minutes=gia.KHUNG[tf]) <= het]
    d1 = m1.resample('1D').agg(gia._OHLC).dropna()
    d1 = d1[(d1.index + timedelta(days=1) <= het) & (d1.index.day_of_week != 6)]
    goc = os.path.expandvars(g.get('d1_goc') or '')
    if goc and os.path.exists(goc):
        raw = pd.read_csv(goc, sep='\t')
        raw.columns = [c.strip('<>').lower() for c in raw.columns]
        t = pd.to_datetime(raw['date'] + ' ' + raw['time'] if 'time' in raw else raw['date'], format='mixed', utc=True)
        old = raw.assign(t=t).set_index('t')[['open', 'high', 'low', 'close']]
        d1 = pd.concat([old[old.index < d1.index[0]], d1])
    fr['D1'] = d1
    fr['het'] = het.to_pydatetime()
    return fr


# ---- thống kê theo bối cảnh ------------------------------------------------------------------------------------------
def _so(ls: list[dict]) -> dict:
    n = len(ls)
    if not n:
        return {'n': 0}
    usd = [x['usd'] for x in ls]
    return {'n': n, 'ty_le': round(sum(u > 0 for u in usd) / n * 100, 1), 'usd_tb': round(sum(usd) / n, 2), 'tong': round(sum(usd), 2)}


def nhan_xet(hoc: dict, kiem: dict) -> tuple[str, str]:
    if hoc['n'] < TOI_THIEU or kiem['n'] < TOI_THIEU:
        return 'chua_du', f'Chưa đủ mẫu: cần ít nhất {TOI_THIEU} lệnh ở mỗi nửa.'
    if hoc['usd_tb'] > 0 and kiem['usd_tb'] > 0:
        return 'giu', 'Có lãi ở cả nửa học và nửa kiểm.'
    if hoc['usd_tb'] <= 0 and kiem['usd_tb'] <= 0:
        return 'lo', 'Lỗ ở cả nửa học và nửa kiểm.'
    return 'khong_on', 'Không ổn định: một nửa có lãi, một nửa lỗ.'


def thong_ke(lenh: list[dict], ti: pd.Series, cat: datetime) -> dict:
    """{khóa bối cảnh: số đo}. Khóa: 'BAN', 'BAN|Mỹ', 'BAN|Mỹ|cao'. Mỗi số đo có cả giai đoạn và hai nửa học/kiểm (cắt tại `cat`)."""
    nhom: dict = {}
    ti = ti.dropna()
    for x in lenh:
        t = pd.Timestamp(x['t'])
        k = int(ti.index.searchsorted(t - timedelta(hours=1), side='right')) - 1
        bd = muc(float(ti.iloc[k])) if k >= 0 else None
        ph = phien(t)
        for khoa in (x['huong'], f'{x["huong"]}|{ph}') + ((f'{x["huong"]}|{ph}|{bd}',) if bd else ()):
            nhom.setdefault(khoa, []).append((t, x))
    out = {}
    for khoa, ds in nhom.items():
        hoc, kiem = _so([x for t, x in ds if t < cat]), _so([x for t, x in ds if t >= cat])
        ma, loi = nhan_xet(hoc, kiem)
        out[khoa] = {**_so([x for _, x in ds]), 'hoc': hoc, 'kiem': kiem, 'nhan_xet': ma, 'loi_nhan_xet': loi}
    return out


def quang_dai(lenh: list[dict], tu_nam: int) -> dict | None:
    """Số đo của một luật trên quãng dài, tách các năm TRƯỚC `tu_nam` (trước quãng mà webapp vẫn dùng để nhận xét, cũng là quãng dự án đã nhìn
    khi chọn tham số) khỏi các năm từ `tu_nam`. Trả None nếu không có lệnh nào trước `tu_nam`. 'theo_nam': [năm, số lệnh, % có lãi,
    USD mỗi lệnh, tổng]; 'truoc' có thêm số năm có tổng dương. Mỗi chiều có 'dat': các năm trước `tu_nam` có ít nhất TOI_THIEU lệnh chiều đó
    và trung bình có lãi; chế độ Kỷ luật và dòng 'Bằng chứng tốt nhất' trên trang đòi điều này."""
    co_nam = [(pd.Timestamp(x['t']).year, x) for x in lenh]
    truoc, sau = [x for n, x in co_nam if n < tu_nam], [x for n, x in co_nam if n >= tu_nam]
    if not truoc:
        return None
    theo_nam = []
    for nam in sorted({n for n, _ in co_nam}):
        s = _so([x for n, x in co_nam if n == nam])
        theo_nam.append([nam, s['n'], s['ty_le'], s['usd_tb'], s['tong']])
    cu = [r for r in theo_nam if r[0] < tu_nam]

    def chieu(h):
        t = _so([x for x in truoc if x['huong'] == h])
        return {'truoc': t, 'sau': _so([x for x in sau if x['huong'] == h]), 'dat': bool(t['n'] >= TOI_THIEU and t['usd_tb'] > 0)}
    return {'tu_nam': theo_nam[0][0], 'tat_ca': _so(lenh), 'sau': _so(sau), 'theo_nam': theo_nam,
            'truoc': {**_so(truoc), 'den_nam': tu_nam - 1, 'nam_lai': sum(r[4] > 0 for r in cu), 'so_nam': len(cu)},
            'theo': {h: chieu(h) for h in ('MUA', 'BAN')}}


def nho_truoc(base: Path | None, ma: str, khoa: list, fn) -> list[dict]:
    """Lệnh của một luật ở các năm TRƯỚC quãng chọn. Dữ liệu những năm đó không đổi nữa, nên chỉ tính một lần rồi nhớ ra tệp
    `hoc_truoc_<ma>.json`; tính lại khi `khoa` đổi (dữ liệu, chi phí hoặc mã của luật đổi). Chỉ giữ ba trường mà quang_dai() cần."""
    tep = base / f'hoc_truoc_{ma}.json' if base else None
    khoa = json.loads(json.dumps(khoa))
    if tep is not None:
        try:
            d = json.loads(tep.read_text(encoding='utf-8'))
            if d.get('khoa') == khoa:
                return d['lenh']
        except (OSError, ValueError, AttributeError, KeyError):
            pass
    lenh = [{'t': str(x['t']), 'huong': x['huong'], 'usd': float(x['usd'])} for x in fn()]
    if tep is not None:
        try:
            tep.parent.mkdir(parents=True, exist_ok=True)
            tep.write_text(json.dumps({'khoa': khoa, 'lenh': lenh}), encoding='utf-8')
        except OSError:
            pass                                                           # không ghi được thì lần sau tính lại
    return lenh


def _luc_sua(*ten: str) -> list:
    """Lúc sửa cuối của các tệp mã luật (của chủ dự án, chỉ đọc): mã đổi thì phần đã nhớ phải tính lại."""
    import importlib.util                                                  # noqa: PLC0415
    out = []
    for t in ten:
        try:
            out.append(os.path.getmtime(importlib.util.find_spec(t).origin))
        except Exception:                                                  # noqa: BLE001
            out.append(None)
    return out


def chay(cfg: dict) -> dict:
    """Chạy lại ba luật trên dữ liệu nhiều năm. Nặng (vài phút): gọi qua lay() để chạy nền và nhớ kết quả."""
    g = cfg['gia']
    tu_nam = int((cfg.get('hoc') or {}).get('tu_nam', 2024))
    out: dict = {'phien_ban': PHIEN_BAN, 'tinh_luc': datetime.now(timezone.utc).isoformat(), 'tu_nam': tu_nam, 'luat': {}, 'loi': []}
    gia._nap_ma(g)
    m1 = _m1_dai(g, tu_nam)
    fr = _khung(m1, g)
    sp = float(g.get('spread', 0.17))
    tu, den = m1.index[0], fr['het']
    cat = tu + (pd.Timestamp(den) - tu) * TY_LE_HOC
    out.update(tu=tu.isoformat(), den=den.isoformat(), cat=cat.isoformat(), so_ngay=int((pd.Timestamp(den) - tu).days), spread=sp,
               gia_dau=round(float(m1['open'].iloc[0]), 2), gia_cuoi=round(float(m1['close'].iloc[-1]), 2))
    tin: list = []
    tin_tat: list = []
    if g.get('lich_tin'):
        try:
            from ai import snapshot as SN                                  # noqa: PLC0415
            tin_tat, _ = SN.load_high_usd_news(Path(os.path.expandvars(g['lich_tin'])))
            tin = [t for t in tin_tat if tu - timedelta(days=1) <= t <= pd.Timestamp(den) + timedelta(days=1)]
        except Exception as e:                                             # noqa: BLE001
            out['loi'].append(f'Lịch tin: {type(e).__name__}: {e}')
    ti = ty_le_bien_do(fr['H1'])
    khung_bot = tuple((cfg.get('kiem_chung') or {}).get('khung_bot', ('M5', 'M15')))
    ls_luat: dict = {}
    for ma, fn in (('bot', lambda: kiem_chung._bot(g, m1, fr['D1'], sp, khung_bot)), ('ba_khung', lambda: kiem_chung._ba_khung(g, m1, fr, sp, tin)),
                   ('dinh_day', lambda: kiem_chung._dinh_day(g, m1, fr, sp, tin))):
        try:
            r = fn()
            ls = sorted(r.pop('lenh'), key=lambda x: x['t'])
            out['luat'][ma] = {'cach': r.get('cach', ''), 'tat_ca': _so(ls), 'theo': thong_ke(ls, ti, cat)}
            ls_luat[ma] = ls
        except Exception as e:                                             # noqa: BLE001 - một luật hỏng không chặn luật khác
            out['loi'].append(f'{ma}: {type(e).__name__}: {e}')
    # Các phương pháp tùy chọn dùng quãng dài hơn hẳn (mặc định từ 2015): ba năm gần đây vàng đi một chiều rất mạnh, và chỉ nhìn ba năm đó
    # làm vài phương pháp trông có lãi trong khi cả quãng dài thì không. Luật trong sổ của chủ dự án vẫn chạy trên quãng từ `tu_nam`.
    tu_pp = int((cfg.get('hoc') or {}).get('tu_nam_pp', 2015))
    m1p, frp, tip, tup, catp = m1, fr, ti, tu, cat
    if tu_pp < tu_nam:
        try:
            m1p = _m1_dai(g, tu_pp)
            frp = _khung(m1p, g)
            tip, tup = ty_le_bien_do(frp['H1']), m1p.index[0]
            catp = tup + (pd.Timestamp(den) - tup) * TY_LE_HOC
        except Exception as e:                                             # noqa: BLE001 - không đọc được quãng dài thì dùng quãng ngắn
            out['loi'].append(f'Dữ liệu từ {tu_pp}: {type(e).__name__}: {e}')
            m1p, frp, tip, tup, catp = m1, fr, ti, tu, cat
    # Luật trong sổ cũng chạy trên quãng dài, chỉ để NÊU: phần lãi của quãng từ `tu_nam` có giữ được ở các năm trước đó không. Nhận xét
    # 'giữ được' và nút Kỷ luật vẫn dùng quãng từ `tu_nam` như cũ. Mức chốt lời và dừng lỗ của các luật này là số giá cố định, nên các năm
    # giá vàng thấp hơn nhiều không phải phép kiểm giống hệt; trang ghi rõ điều đó.
    if tup < tu:
        tin_dai = [t for t in tin_tat if tup - timedelta(days=1) <= t <= pd.Timestamp(den) + timedelta(days=1)]
        for ma, fn in (('bot', lambda: kiem_chung._bot(g, m1p, frp['D1'], sp, khung_bot)), ('ba_khung', lambda: kiem_chung._ba_khung(g, m1p, frp, sp, tin_dai))):
            if ma not in out['luat']:
                continue
            try:
                d = quang_dai(sorted(fn().pop('lenh'), key=lambda x: x['t']), tu_nam)
                if d:
                    out['luat'][ma]['dai'] = d
            except Exception as e:                                         # noqa: BLE001 - thiếu phần này không chặn phần còn lại
                out['loi'].append(f'{ma} trên quãng dài: {type(e).__name__}: {e}')
        # Luật đỉnh/đáy chạy chậm hơn nhiều (quyết định ở từng nến M15), nên các năm trước `tu_nam` chỉ tính một lần rồi nhớ ra tệp, và
        # ghép với lệnh của quãng từ `tu_nam` đã tính ở trên. Luật này đặt dừng lỗ theo biên độ (ATR), nên các năm cũ so được với hiện nay.
        if 'dinh_day' in ls_luat:
            try:
                m1t = m1p[m1p.index < tu]
                tin_t = [t for t in tin_dai if t < tu + timedelta(days=1)]
                khoa = [PHIEN_BAN, tup.isoformat(), tu.isoformat(), len(m1t), sp, len(tin_t),
                        _luc_sua('ai.rule_fade', 'ai.scorer', 'ai.validator', 'ai.config', 'tinhieu.rules')]
                truoc = nho_truoc(Path(cfg.get('thu_muc_ra', 'out')), 'dinh_day', khoa,
                                  lambda: kiem_chung._dinh_day(g, m1t, _khung(m1t, g), sp, tin_t)['lenh'])
                d = quang_dai(sorted(truoc + ls_luat['dinh_day'], key=lambda x: str(x['t'])), tu_nam)
                if d:
                    out['luat']['dinh_day']['dai'] = d
            except Exception as e:                                         # noqa: BLE001
                out['loi'].append(f'dinh_day trên quãng dài: {type(e).__name__}: {e}')
    for ma, tt in phuong_phap.DS.items():
        try:
            th = phuong_phap.quet(ma, frp['M15'], frp['H1'])
            ls = phuong_phap.cham(th, m1p, sp)
            ls2 = phuong_phap.cham(th, m1p, sp, theo_muc_tieu=True)
            ls1 = phuong_phap.cham(th, m1p, sp, tp_r=1.0)
            out['luat'][ma] = {'cach': f'Chạy lại đúng quy tắc của phương pháp trên nến 1 phút: mỗi lúc một lệnh, chốt ở {phuong_phap.TP_R:g}R, '
                                       f'giữ tối đa {phuong_phap.GIU_PHUT // 60} giờ, phí {phuong_phap.PHI:g} mỗi lệnh.'.replace('0.18', '0,18'),
                               'tu': tup.isoformat(), 'cat': catp.isoformat(), 'den': pd.Timestamp(den).isoformat(),
                               'tat_ca': _so(ls), 'theo': thong_ke(ls, tip, catp),
                               'theo_muc_tieu': {'tat_ca': _so(ls2), **{k: v for k, v in thong_ke(ls2, tip, catp).items() if '|' not in k}},
                               'r1': {'tat_ca': _so(ls1), **{k: v for k, v in thong_ke(ls1, tip, catp).items() if '|' not in k}}}
        except Exception as e:                                             # noqa: BLE001
            out['loi'].append(f'{ma}: {type(e).__name__}: {e}')
    return out


# ---- nhớ kết quả và chạy nền -----------------------------------------------------------------------------------------
def _key(cfg: dict) -> str:
    g = cfg['gia']
    goc = Path(os.path.expandvars(g.get('d1_goc') or 'x')).with_name('XAUUSDp_M1.csv')
    return json.dumps([PHIEN_BAN, int((cfg.get('hoc') or {}).get('tu_nam', 2024)), os.path.getmtime(goc) if goc.exists() else None,
                       gia.khung(g)['het'].date().isoformat(), g.get('spread', 0.17)])


def _tep(out: Path) -> Path:
    return Path(out) / 'hoc.json'


def lay(cfg: dict, out: Path, cho: bool = False) -> dict:
    """Kết quả nếu đã có (bộ nhớ hoặc out/hoc.json của đúng dữ liệu hôm nay); chưa có thì tính ở nền và trả {'san_sang': False}."""
    if gia.chia_se_song(cfg['gia']):              # bản chia sẻ: học trên nến 5 phút lấy thẳng từ MT5, như mọi mã khác
        from . import da_ma, hoc_ma               # noqa: PLC0415
        return hoc_ma.lay(cfg, out, da_ma.ma_vang(cfg), cho)
    try:
        key = _key(cfg)
    except Exception as e:                                                 # noqa: BLE001
        return {'san_sang': False, 'dang_tinh': False, 'loi': [f'{type(e).__name__}: {e}']}
    with _khoa:
        if _tt['key'] == key and _tt['kq'] is not None:
            return {'san_sang': True, **_tt['kq']}
        if _tt['key'] != key:
            _tt.update(key=key, kq=None, loi=None)
            try:
                saved = json.loads(_tep(out).read_text(encoding='utf-8'))
                if saved.get('key') == key:
                    _tt['kq'] = saved['kq']
                    return {'san_sang': True, **_tt['kq']}
            except (OSError, ValueError, KeyError):
                pass
        if _tt['loi']:
            return {'san_sang': False, 'dang_tinh': False, 'loi': [_tt['loi']]}
        start = not _tt['dang']
        if start:
            _tt.update(dang=True, bat_dau=datetime.now(timezone.utc))

    def lam():
        try:
            kq = chay(cfg)
            with _khoa:
                if _tt['key'] == key:
                    _tt['kq'] = kq
            try:
                Path(out).mkdir(parents=True, exist_ok=True)
                _tep(out).write_text(json.dumps({'key': key, 'kq': kq}, ensure_ascii=False), encoding='utf-8')
            except OSError:
                pass
        except Exception as e:                                             # noqa: BLE001
            with _khoa:
                _tt['loi'] = f'{type(e).__name__}: {e}'
        finally:
            with _khoa:
                _tt['dang'] = False

    if cho:
        if start:
            lam()
        with _khoa:
            return {'san_sang': True, **_tt['kq']} if _tt['kq'] is not None else {'san_sang': False, 'dang_tinh': _tt['dang'], 'loi': [_tt['loi']] if _tt['loi'] else []}
    if start:
        threading.Thread(target=lam, name='hoc', daemon=True).start()
    return {'san_sang': False, 'dang_tinh': True, 'da_giay': int((datetime.now(timezone.utc) - _tt['bat_dau']).total_seconds())}


def main(argv=None) -> int:
    import sys                                                             # noqa: PLC0415
    import time                                                            # noqa: PLC0415
    here = Path(__file__).resolve().parent.parent
    cfg = json.loads((here / 'cau-hinh.json').read_text(encoding='utf-8'))
    t0 = time.time()
    kq = lay(cfg, here / cfg.get('thu_muc_ra', 'out'), cho=True)
    sys.stdout.reconfigure(encoding='utf-8')
    if not kq.get('san_sang'):
        print('Không tính được:', kq.get('loi'))
        return 1
    print(f'Dữ liệu {kq["tu"][:10]} tới {kq["den"][:10]} ({kq["so_ngay"]} ngày), cắt học/kiểm tại {kq["cat"][:10]}, tính trong {time.time() - t0:.0f} giây')
    for ma, r in kq['luat'].items():
        print(f'\n{ma}: tất cả {r["tat_ca"]}')
        for khoa in sorted(r['theo'], key=lambda k: (k.count("|"), k)):
            s = r['theo'][khoa]
            if khoa.count('|') < 2:
                print(f'  {khoa:16} n={s["n"]:5} lãi {s["ty_le"]:5}% tb {s["usd_tb"]:+7.2f} | học n={s["hoc"]["n"]} tb {s["hoc"].get("usd_tb", 0):+.2f} | kiểm n={s["kiem"]["n"]} tb {s["kiem"].get("usd_tb", 0):+.2f} | {s["nhan_xet"]}')
    for e in kq['loi']:
        print('LỖI:', e)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
