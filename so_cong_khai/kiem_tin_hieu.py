# -*- coding: utf-8 -*-
"""Kiểm chứng tín hiệu của các nhóm Telegram (26/11/2026): dán các tin tín hiệu (chép từ Telegram), webapp dò lại từng tín hiệu trên nến 1 phút
thật của MT5 xem giá chạm dừng lỗ hay chốt lời trước, rồi tính tỷ lệ thắng thật và lãi lỗ theo R.

Vì sao cần: nhiều nhóm trông "báo chuẩn" nhờ cách trình bày (TP1 đặt rất gần rồi báo "đã chạm TP1", nhiều mức TP, không nhắc lệnh thua, dời
dừng lỗ sau khi giá chạy, đếm pip mà không tính rủi ro). Ở đây mọi tín hiệu đọc được đều được chấm theo cùng một cách, kể cả tín hiệu nhóm không
báo kết quả.

Cách chấm (ghi rõ trên trang):
- Giờ của tin là giờ đọc được trong đoạn dán (dòng kiểu "Tên nhóm, [25.11.2026 14:05]" hoặc "25/11 14:05"), theo múi giờ người dùng chọn.
- Tin có chữ NOW / ngay / market / CMP: vào theo giá mở của phút ngay sau tin. Tin có giá vào (một mức hay một vùng): khớp khi giá chạm mức đó
  (vùng: chạm cạnh gần giá nhất) trong thời hạn chờ; quá hạn là "không khớp".
- Sau khi khớp, dò từng nến 1 phút: chạm dừng lỗ là thua; chạm lần lượt các mức chốt lời. Một nến chạm cả dừng lỗ và mức chốt lời thì tính dừng lỗ
  trước (thận trọng, như các phép đo khác của webapp). Tùy chọn: dời dừng lỗ về giá vào sau khi chạm TP1.
- Lãi lỗ theo R (R = khoảng giá vào tới dừng lỗ): "chốt hết ở TP1" và "chia đều cho các TP". Chưa trừ spread, phí; giá dò là giá Bid của sàn bạn.
Chỉ đọc giá; không gửi gì ra ngoài, không đặt lệnh."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

TOI_DA_TIN = 200
TOI_DA_CHU = 60_000
CHIEU = {'BUY': 'MUA', 'LONG': 'MUA', 'MUA': 'MUA', 'SELL': 'BAN', 'SHORT': 'BAN', 'BAN': 'BAN', 'BÁN': 'BAN'}
BI_DANH = {'GOLD': 'XAUUSD', 'XAU': 'XAUUSD', 'VANG': 'XAUUSD', 'VÀNG': 'XAUUSD', 'SILVER': 'XAGUSD', 'BAC': 'XAGUSD', 'XAG': 'XAGUSD',
           'DOW': 'US30', 'DJ30': 'US30', 'NASDAQ': 'NAS100', 'US100': 'NAS100', 'USTEC': 'NAS100', 'NAS': 'NAS100', 'SPX': 'US500', 'SP500': 'US500',
           'BTC': 'BTCUSD', 'BITCOIN': 'BTCUSD', 'ETH': 'ETHUSD', 'OIL': 'USOIL', 'WTI': 'USOIL', 'DAX': 'GER40', 'GER30': 'GER40'}
_GIO = [  # (mẫu, thứ tự nhóm: ngày, tháng, năm, giờ, phút)
    (re.compile(r'\[?\s*(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})[\s,T]+(\d{1,2})[:h](\d{2})(?::\d{2})?\s*\]?'), (1, 2, 3, 4, 5)),
    (re.compile(r'\b(\d{1,2})[:h](\d{2})(?::\d{2})?\s*,?\s*(?:ngày\s*)?(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?\b'), (3, 4, 5, 1, 2)),
    (re.compile(r'\b(\d{1,2})[./-](\d{1,2})\s+(\d{1,2})[:h](\d{2})\b'), (1, 2, None, 3, 4)),
]
_SO = r'\d[\d.,]*\d|\d'
_TU_CHIEU = re.compile(r'(?<![A-Za-z])(BUY|SELL|LONG|SHORT|MUA|BÁN|BAN)(?![A-Za-z])', re.I)
_TU_SL = re.compile(r'(?:\bS\s*/?\s*L\b|STOP\s*LOSS|CẮT\s*LỖ|CAT\s*LO|DỪNG\s*LỖ|DUNG\s*LO)\s*[:=@-]?\s*(' + _SO + ')', re.I)
_TU_TP = re.compile(r'(?:\bT\s*/?\s*P\s*\d?\b|TAKE\s*PROFIT\s*\d?|CHỐT\s*LỜI\s*\d?|CHOT\s*LOI\s*\d?)\s*[:=@-]?\s*((?:(?:' + _SO + r')\s*[/|,;]?\s*)+)', re.I)
_NGAY = re.compile(r'\b(NOW|MARKET|CMP|NGAY|HIỆN\s*TẠI|THỊ\s*TRƯỜNG)\b', re.I)


def so(s: str) -> float | None:
    """Đọc số giá kiểu '3,540.5', '3.540,5', '1.0850', '3540'."""
    s = s.strip().rstrip('.,')
    if not s:
        return None
    if ',' in s and '.' in s:
        s = s.replace(',', '') if s.rfind('.') > s.rfind(',') else s.replace('.', '').replace(',', '.')
    elif ',' in s:
        dau = s.split(',')
        s = s.replace(',', '') if all(len(x) == 3 for x in dau[1:]) else s.replace(',', '.')
    elif s.count('.') > 1:
        s = s.replace('.', '')
    try:
        v = float(s)
    except ValueError:
        return None
    return v if v > 0 else None


def _ma(dong: str) -> str | None:
    for tu in re.findall(r'[A-Za-zÀ-ỹ0-9#]{2,12}', dong):
        t = tu.upper().replace('#', '')
        if t in BI_DANH:
            return BI_DANH[t]
        if re.fullmatch(r'(XAU|XAG|EUR|GBP|USD|AUD|NZD|CAD|CHF|JPY|BTC|ETH)[A-Z]{3}[A-Z]?', t):
            return t[:6]
        if re.fullmatch(r'(US30|US500|NAS100|GER40|UK100|JP225|USOIL|UKOIL)', t):
            return t
    return None


def _gio(dong: str, nam_mac_dinh: int) -> datetime | None:
    for mau, th in _GIO:
        m = mau.search(dong)
        if not m:
            continue
        g = [m.group(i) if i else None for i in th]
        try:
            nam = int(g[2]) if g[2] else nam_mac_dinh
            nam = nam + 2000 if nam < 100 else nam
            return datetime(nam, int(g[1]), int(g[0]), int(g[3]), int(g[4]))
        except (ValueError, TypeError):
            continue
    return None


def doc_tin(van_ban: str, mui_gio: float = 7, nam: int | None = None, ma_mac_dinh: str = 'XAUUSD') -> tuple[list[dict], list[str]]:
    """Tách đoạn dán thành các tín hiệu. Trả (tín hiệu, các đoạn có chữ BUY/SELL mà không đọc được, kèm lý do)."""
    nam = nam or datetime.now(timezone.utc).year
    tz = timezone(timedelta(hours=mui_gio))
    dong = [d.strip() for d in van_ban[:TOI_DA_CHU].replace('\r', '').split('\n')]
    khoi, cur, gio_cu = [], None, None
    for d in dong:
        g = _gio(d, nam)
        con_lai = _GIO[0][0].sub('', d).strip(' ,:-') if g else d
        if g:
            gio_cu = g
        if _TU_CHIEU.search(con_lai) and (cur is None or cur['chieu_co'] or g):
            cur = {'dong': [], 'gio': gio_cu, 'chieu_co': False}
            khoi.append(cur)
        elif g and cur is not None and cur['dong']:
            cur = None                                                       # tin mới (có dòng giờ) chưa có chiều: để dòng sau mở khối
        if cur is None:
            continue
        if con_lai:
            cur['dong'].append(con_lai)
            if _TU_CHIEU.search(con_lai):
                cur['chieu_co'] = True
    ra, loi = [], []
    for k in khoi[:TOI_DA_TIN]:
        x, ly_do = _mot_tin(k['dong'], ma_mac_dinh)
        tom = ' / '.join(k['dong'])[:160]
        if ly_do:
            loi.append(f'{tom} → {ly_do}')
            continue
        if k['gio'] is None:
            loi.append(f'{tom} → không thấy giờ gửi tin (chép cả dòng tên nhóm và giờ, ví dụ "Nhóm, [25.11.2026 14:05]")')
            continue
        x['gio'] = k['gio'].replace(tzinfo=tz).astimezone(timezone.utc)
        x['nguyen_van'] = tom
        ra.append(x)
    return ra, loi


def _mot_tin(dong: list[str], ma_mac_dinh: str) -> tuple[dict, str | None]:
    chu = '\n'.join(dong)
    m = _TU_CHIEU.search(chu)
    if not m:
        return {}, 'không thấy BUY/SELL'
    chieu = CHIEU[m.group(1).upper()]
    dau = chu[:m.start()].rsplit('\n', 1)[-1] + chu[m.start():].split('\n', 1)[0]  # dòng có chữ BUY/SELL
    loai = 'cho' if re.search(r'\b(LIMIT|STOP|CHỜ|CHO)\b', dau, re.I) else ''
    ngay = bool(_NGAY.search(dau)) and not loai
    sau = dau[dau.upper().find(m.group(1).upper()) + len(m.group(1)):]
    sau = re.split(r'\b(?:S\s*/?\s*L|T\s*/?\s*P|STOP\s*LOSS|TAKE)\b', sau, maxsplit=1, flags=re.I)[0]
    gia_vao = [v for v in (so(t) for t in re.findall(_SO, re.sub(r'\b(?:US30|US500|NAS100|GER40|UK100|JP225)\b', '', sau))) if v]
    if not gia_vao:                                                         # "BUY GOLD" xuống dòng "Entry: 3540"
        e = re.search(r'(?:ENTRY|VÀO|VAO|GIÁ\s*VÀO|@)\s*[:=]?\s*(' + _SO + r')(?:\s*[-–~]\s*(' + _SO + '))?', chu, re.I)
        if e:
            gia_vao = [v for v in (so(e.group(1)), so(e.group(2) or '')) if v]
    sl = [so(x) for x in _TU_SL.findall(chu)]
    sl = [v for v in sl if v]
    tp = []
    for nhom in _TU_TP.findall(chu):
        tp += [v for v in (so(t) for t in re.findall(_SO, nhom)) if v]
    if not sl:
        return {}, 'không thấy dừng lỗ (SL)'
    if not tp:
        return {}, 'không thấy chốt lời (TP)'
    x = {'chieu': chieu, 'ma': _ma(chu) or ma_mac_dinh, 'sl': sl[0], 'tp': [], 'ngay': ngay or not gia_vao,
         'vung': sorted(gia_vao[:2]) if gia_vao else None}
    mua = chieu == 'MUA'
    for v in tp:                                                            # bỏ số lạ (như "TP1" bị đọc thành 1) và giữ đúng chiều
        if (v > x['sl']) == mua and v not in x['tp']:
            x['tp'].append(v)
    x['tp'] = sorted(x['tp'], reverse=not mua)
    if not x['tp']:
        return {}, 'các mức chốt lời nằm sai phía so với dừng lỗ'
    if x['vung']:
        lo, hi = x['vung'][0], x['vung'][-1]
        if (mua and not (x['sl'] < lo and x['tp'][0] > hi)) or (not mua and not (x['sl'] > hi and x['tp'][0] < lo)):
            return {}, 'giá vào, dừng lỗ và chốt lời không đúng thứ tự'
    return x, None


def cham(x: dict, nen: list[tuple], cho_gio: float = 4, ve_hoa_von: bool = False) -> dict:
    """Dò một tín hiệu trên nến 1 phút (t, open, high, low, close; t là giây UTC, tăng dần, từ lúc gửi tin trở đi)."""
    mua = x['chieu'] == 'MUA'
    t0 = x['gio'].timestamp()
    kq = {'trang_thai': 'khong_du_lieu', 'vao': None, 'luc_vao': None, 'tp_cham': 0, 'r_tp1': None, 'r_chia': None, 'luc_xong': None, 'ghi_chu': ''}
    nen = [n for n in nen if n[0] + 60 > t0]
    if not nen:
        return kq
    if nen[0][0] - t0 > 900:                                                 # lịch sử hở ngay sau giờ gửi tin: không chấm trên khoảng sai
        kq['ghi_chu'] = 'lịch sử nến 1 phút của sàn bị hở ngay sau giờ gửi tin'
        return kq
    i, vao = 0, None
    giua = nen[0][0] < t0                                                    # tin gửi giữa một phút: phần đầu phút đó đã qua trước tin
    if x['ngay']:
        vao = nen[0][4] if giua else nen[0][1]                               # giá mở của phút ngay sau tin (tin giữa phút: giá đóng phút đó)
        i = 1 if giua else 0
        kq['ghi_chu'] = 'vào theo giá thị trường lúc gửi tin'
    else:
        lo, hi = x['vung'][0], x['vung'][-1]
        p0 = nen[0][4] if giua else nen[0][1]
        muc = hi if p0 > hi else lo if p0 < lo else p0                       # cạnh vùng gần giá nhất; giá đã trong vùng thì vào ngay
        if lo <= p0 <= hi:
            vao, i = p0, (1 if giua else 0)
        else:
            han = t0 + cho_gio * 3600
            for j in range(1 if giua else 0, len(nen)):
                n = nen[j]
                if n[0] > han:
                    break
                if n[3] <= muc <= n[2]:
                    vao, i = muc, j
                    break
            if vao is None:
                kq['trang_thai'] = 'khong_khop'
                return kq
    if i >= len(nen):
        return kq
    kq['vao'], kq['luc_vao'] = vao, nen[i][0]
    rui = abs(vao - x['sl'])
    if rui <= 0:
        kq['trang_thai'] = 'loi'
        return kq
    sl = x['sl']
    tps = x['tp']
    for n in nen[i:]:
        cham_sl = n[3] <= sl if mua else n[2] >= sl
        if cham_sl:
            kq.update(trang_thai='thua' if kq['tp_cham'] == 0 else ('hoa_von' if sl == vao else 'tp_roi_sl'), luc_xong=n[0])
            break
        while kq['tp_cham'] < len(tps) and ((n[2] >= tps[kq['tp_cham']]) if mua else (n[3] <= tps[kq['tp_cham']])):
            kq['tp_cham'] += 1
            if kq['tp_cham'] == 1 and ve_hoa_von:
                sl = vao
        if kq['tp_cham'] == len(tps):
            kq.update(trang_thai='het_tp', luc_xong=n[0])
            break
    else:
        kq['trang_thai'] = 'dang_mo'
    r = [abs(t - vao) / rui for t in tps]
    kq['r_cac_tp'] = [round(v, 2) for v in r]
    if kq['trang_thai'] != 'dang_mo' or kq['tp_cham']:
        kq['r_tp1'] = round(r[0] if kq['tp_cham'] else -1.0, 3)
    if kq['trang_thai'] != 'dang_mo':
        phan = [r[j] if j < kq['tp_cham'] else (0.0 if kq['trang_thai'] == 'hoa_von' else -1.0) for j in range(len(tps))]
        kq['r_chia'] = round(sum(phan) / len(phan), 3)
    return kq


def tong_hop(ds: list[dict]) -> dict:
    khop = [x for x in ds if x['kq']['trang_thai'] not in ('khong_khop', 'khong_du_lieu', 'loi')]
    xong = [x for x in khop if x['kq']['trang_thai'] != 'dang_mo']
    n = len(xong)
    tp1 = sum(1 for x in khop if x['kq']['tp_cham'] >= 1)
    thua = sum(1 for x in xong if x['kq']['trang_thai'] == 'thua')
    het = sum(1 for x in xong if x['kq']['trang_thai'] == 'het_tp')
    r1 = [x['kq']['r_tp1'] for x in xong if x['kq']['r_tp1'] is not None]
    rc = [x['kq']['r_chia'] for x in xong if x['kq']['r_chia'] is not None]
    kc = [x['kq']['r_cac_tp'][0] for x in khop if x['kq'].get('r_cac_tp')]
    pc = lambda a, b: round(100 * a / b, 1) if b else None                   # noqa: E731
    return {'tin': len(ds), 'khop': len(khop), 'khong_khop': sum(1 for x in ds if x['kq']['trang_thai'] == 'khong_khop'),
            'khong_du_lieu': sum(1 for x in ds if x['kq']['trang_thai'] in ('khong_du_lieu', 'loi')), 'xong': n,
            'dang_mo': len(khop) - n, 'tp1': tp1, 'ty_le_tp1': pc(tp1, len(khop)), 'thua': thua, 'ty_le_thua': pc(thua, n), 'het_tp': het,
            'ty_le_het_tp': pc(het, n), 'r_tp1_tb': round(sum(r1) / len(r1), 3) if r1 else None, 'r_tp1_tong': round(sum(r1), 2) if r1 else None,
            'r_chia_tb': round(sum(rc) / len(rc), 3) if rc else None, 'r_chia_tong': round(sum(rc), 2) if rc else None,
            'tp1_cach_tb': round(sum(kc) / len(kc), 2) if kc else None}


# --------------------------------------------------------------------------- nối MT5
def _chuan(t: str) -> str:
    return re.sub(r'[^A-Z0-9]', '', t.upper())


def tim_ma(ma: str, hien: list[str]) -> str | None:
    """Mã của sàn ứng với tên trong tin (XAUUSD → XAUUSDp, NAS100 → USTEC…)."""
    goc = _chuan(ma)
    cung = [h for h in hien if _chuan(h) == goc] or [h for h in hien if _chuan(h).startswith(goc)]
    if not cung and goc == 'NAS100':
        cung = [h for h in hien if _chuan(h).startswith(('USTEC', 'US100', 'NDX'))]
    return min(cung, key=len) if cung else None


def kiem(cfg: dict, van_ban: str, mui_gio: float = 7, cho_gio: float = 4, giu_ngay: float = 5, ve_hoa_von: bool = False,
         ma_mac_dinh: str = 'XAUUSD', mt5=None, now: datetime | None = None) -> dict:
    from . import da_ma                                                     # noqa: PLC0415 - nạp chậm: bài kiểm thay MT5 giả
    now = now or datetime.now(timezone.utc)
    tin, loi = doc_tin(van_ban, mui_gio, now.year, ma_mac_dinh)
    if mt5 is None:
        mt5 = da_ma._mt5(cfg.get('gia') or {})
    if mt5 is None:
        return {'ok': False, 'ly_do': 'Chưa nối được MT5 (mở MT5 demo rồi thử lại).', 'ds': [], 'loi': loi}
    hien = list(da_ma._hien(mt5))
    nho: dict = {}
    for x in tin:
        x['ma_san'] = tim_ma(x['ma'], hien)
        if not x['ma_san']:
            x['kq'] = {'trang_thai': 'khong_du_lieu', 'tp_cham': 0, 'ghi_chu': f'{x["ma"]} không có trong Market Watch của MT5'}
            continue
        tu = x['gio'] - timedelta(minutes=1)
        den = min(now, x['gio'] + timedelta(days=giu_ngay))
        k = (x['ma_san'], int(tu.timestamp()) // 3600, int(den.timestamp()) // 3600)
        if k not in nho:
            # Phải truyền giờ CÓ múi giờ UTC: thư viện MT5 hiểu giờ không kèm múi giờ là giờ của máy tính (GMT+7 ở Việt Nam), lệch 7 tiếng.
            r = mt5.copy_rates_range(x['ma_san'], mt5.TIMEFRAME_M1, tu, den)
            nho[k] = [(int(n['time']), float(n['open']), float(n['high']), float(n['low']), float(n['close'])) for n in (r if r is not None else [])]
        x['kq'] = cham(x, nho[k], cho_gio, ve_hoa_von)
        if x['kq']['trang_thai'] == 'khong_du_lieu' and not x['kq'].get('ghi_chu'):
            x['kq']['ghi_chu'] = ('tin gửi sau thời điểm hiện tại' if x['gio'] > now
                                  else 'MT5 không trả nến 1 phút cho khoảng này (tin cũ hơn lịch sử của sàn, hoặc thị trường đóng cửa)')
    ds = [{'gio': x['gio'].isoformat(), 'ma': x['ma'], 'ma_san': x.get('ma_san'), 'chieu': x['chieu'], 'vung': x['vung'], 'ngay': x['ngay'],
           'sl': x['sl'], 'tp': x['tp'], 'kq': x['kq'], 'nguyen_van': x['nguyen_van']} for x in tin]
    return {'ok': True, 'ds': ds, 'loi': loi, 'tong': tong_hop(ds), 'cai': {'mui_gio': mui_gio, 'cho_gio': cho_gio, 'giu_ngay': giu_ngay,
            've_hoa_von': ve_hoa_von}}
