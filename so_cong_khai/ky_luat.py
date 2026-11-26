"""Kỷ luật giao dịch: chấm lại các lệnh ĐÃ ĐÓNG trong MT5 theo cùng bộ quy tắc quản lý rủi ro của trang Kiểm tra trước khi vào lệnh,
rồi cho biết lệnh phạm quy tắc đã làm lãi lỗ khác đi bao nhiêu. CHỈ ĐỌC (account_info, history_deals_get, history_orders_get, symbol_info),
chỉ tài khoản DEMO như trang Tài khoản.

Mỗi lệnh (một vị thế MT5, ghép lần khớp mở và các lần khớp đóng theo position_id) được kiểm:
  khong_sl  lúc vào lệnh không có dừng lỗ (và không đóng bởi dừng lỗ)
  rui_ro    rủi ro tới dừng lỗ lớn hơn mức tối đa mỗi lệnh (% số dư lúc vào)
  gap       vào trong vài phút sau một lệnh thua
  tang_lot  khối lượng lớn hơn hẳn lệnh thua ngay trước (gỡ bằng cách tăng cược)
  qua_lo    vào lệnh khi lỗ đã chốt trong ngày (giờ Việt Nam) đã chạm giới hạn ngày
  qua_nhieu vượt số lệnh tối đa mỗi ngày
  tin       vào sát tin mạnh của đồng tiền liên quan (chỉ khi lịch tin phủ tới lúc đó)
`cham(gd, quy_tac, tin)` là hàm thuần nên kiểm thử được; `doc(cfg, ...)` đọc MT5 rồi gọi nó. Không đoán giá, không hứa lợi nhuận."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .kiem_lenh import QUY_TAC_MAC_DINH as _QT_KL

QUY_TAC_MAC_DINH = {
    'rui_ro_lenh_toi_da_pct': _QT_KL['rui_ro_lenh_toi_da_pct'],
    'lo_ngay_toi_da_pct': _QT_KL['lo_ngay_toi_da_pct'],
    'gap_sau_thua_phut': _QT_KL['gap_sau_thua_phut'],
    'tin_truoc_phut': _QT_KL['tin_truoc_phut'],
    'tin_sau_phut': _QT_KL['tin_sau_phut'],
    'tang_lot_he_so': 1.5,           # lot lớn hơn 1,5 lần lệnh thua ngay trước, trong vòng 60 phút
    'tang_lot_phut': 60,
    'so_lenh_ngay_toi_da': 10,       # 0 = không kiểm
}
QUY_TAC = ('khong_sl', 'rui_ro', 'gap', 'tang_lot', 'qua_lo', 'qua_nhieu', 'tin')


def _t(x) -> datetime:
    return x if isinstance(x, datetime) else datetime.fromisoformat(x)


def _r(x, d: int = 2):
    return None if x is None else round(float(x), d)


def cham(gd: list[dict], quy_tac: dict | None = None, tin: list[dict] | None = None, tin_tu: datetime | str | None = None) -> dict:
    """gd: các lệnh đã đóng, mỗi lệnh {id, ma, chieu 'MUA'|'BAN', mo, dong (ISO hoặc datetime), lot, vao, ra, sl (None nếu lúc vào không có),
    dong_boi_sl (bool), lai (lãi lỗ ròng), nguon, von_truoc (số dư ngay trước lúc vào), rui_ro_tien (None nếu không tính được),
    tien_lien_quan [mã tiền]}.
    tin: tin mạnh [{t, tien, ten}] (None = không có lịch: bỏ quy tắc tin). tin_tu: lịch tin phủ từ lúc này; lệnh vào trước đó không kiểm tin.
    Trả: tổng hợp (điểm kỷ luật, lãi lỗ nhóm đúng/phạm quy tắc), từng quy tắc, chuỗi thua, các ngày chạm giới hạn và danh sách lệnh kèm lỗi."""
    from .doc_so import VN                                                   # noqa: PLC0415
    q = {**QUY_TAC_MAC_DINH, **(quy_tac or {})}
    ds = sorted((dict(x, mo=_t(x['mo']), dong=_t(x['dong'])) for x in gd), key=lambda x: (x['mo'], str(x.get('id'))))
    theo_dong = sorted(ds, key=lambda x: x['dong'])
    tin_ds = None if tin is None else sorted(((_t(e['t']), e) for e in tin), key=lambda z: z[0])
    tin_tu = _t(tin_tu) if tin_tu else (tin_ds[0][0] if tin_ds else None)
    dem_ngay: dict = {}
    khong_kiem_tin = 0
    for x in ds:
        loi: list[dict] = []
        von = x.get('von_truoc')
        # 1. dừng lỗ lúc vào
        if x.get('sl') in (None, 0) and not x.get('dong_boi_sl'):
            loi.append({'k': 'khong_sl'})
        # 2. rủi ro mỗi lệnh
        rr = x.get('rui_ro_tien')
        if rr is not None and von and von > 0:
            pct = rr / von * 100
            x['rui_ro_pct'] = round(pct, 2)
            if pct > q['rui_ro_lenh_toi_da_pct'] + 1e-9:
                loi.append({'k': 'rui_ro', 'pct': round(pct, 2)})
        # 3–4. vào gấp / tăng khối lượng sau lệnh thua (lệnh thua đóng gần nhất trước lúc vào)
        truoc = None
        for y in theo_dong:
            if y['dong'] > x['mo']:
                break
            if y is not x:
                truoc = y
        if truoc is not None and (truoc.get('lai') or 0) < 0:
            phut = (x['mo'] - truoc['dong']).total_seconds() / 60
            if phut <= q['gap_sau_thua_phut']:
                loi.append({'k': 'gap', 'phut': round(phut)})
            if phut <= q['tang_lot_phut'] and truoc.get('lot') and x.get('lot') and x['lot'] > truoc['lot'] * q['tang_lot_he_so'] + 1e-9:
                loi.append({'k': 'tang_lot', 'lot_truoc': truoc['lot']})
        # 5. đã chạm giới hạn lỗ ngày (lỗ đã chốt trong ngày giờ VN, tới trước lúc vào)
        ngay = x['mo'].astimezone(VN).date()
        dau_ngay = datetime.combine(ngay, datetime.min.time(), tzinfo=VN)
        lo = sum(y.get('lai') or 0 for y in theo_dong if dau_ngay <= y['dong'] <= x['mo'] and y is not x)
        von_ngay = x.get('von_dau_ngay') or von
        if lo < 0 and von_ngay and -lo / von_ngay * 100 >= q['lo_ngay_toi_da_pct']:
            loi.append({'k': 'qua_lo', 'pct': round(-lo / von_ngay * 100, 2)})
        # 6. quá nhiều lệnh trong ngày
        dem_ngay[ngay] = dem_ngay.get(ngay, 0) + 1
        if q['so_lenh_ngay_toi_da'] and dem_ngay[ngay] > q['so_lenh_ngay_toi_da']:
            loi.append({'k': 'qua_nhieu', 'thu': dem_ngay[ngay]})
        # 7. vào sát tin mạnh
        if tin_ds is not None:
            if tin_tu is None or x['mo'] < tin_tu:
                khong_kiem_tin += 1
            else:
                lien = set(x.get('tien_lien_quan') or [])
                gan = [(t, e) for t, e in tin_ds if (not lien or e.get('tien') in lien)
                       and -timedelta(minutes=q['tin_sau_phut']) <= t - x['mo'] <= timedelta(minutes=q['tin_truoc_phut'])]
                if gan:
                    t, e = min(gan, key=lambda z: abs((z[0] - x['mo']).total_seconds()))
                    loi.append({'k': 'tin', 'phut': round((t - x['mo']).total_seconds() / 60), 'tien': e.get('tien', ''), 'ten': e.get('ten', '')})
        x['loi'] = loi

    n = len(ds)
    dat = [x for x in ds if not x['loi']]
    pham = [x for x in ds if x['loi']]
    lai = lambda xs: round(sum(x.get('lai') or 0 for x in xs), 2)                # noqa: E731
    thang = lambda xs: sum((x.get('lai') or 0) > 0 for x in xs)                  # noqa: E731
    nhom = lambda xs: {'n': len(xs), 'lai': lai(xs), 'thang': thang(xs), 'thua': sum((x.get('lai') or 0) < 0 for x in xs),   # noqa: E731
                       'ty_le_thang': round(thang(xs) / len(xs) * 100, 1) if xs else None,
                       'tb': round(lai(xs) / len(xs), 2) if xs else None}
    theo_qt = []
    for k in QUY_TAC:
        xs = [x for x in ds if any(l['k'] == k for l in x['loi'])]
        theo_qt.append({'k': k, **nhom(xs)})
    # chuỗi thua dài nhất và lệnh lỗ lớn nhất (theo thứ tự đóng)
    chuoi = dai = 0
    for x in theo_dong:
        chuoi = chuoi + 1 if (x.get('lai') or 0) < 0 else 0
        dai = max(dai, chuoi)
    lo_nhat = min(ds, key=lambda x: x.get('lai') or 0) if ds else None
    # các ngày lỗ chạm giới hạn
    ngay_lai: dict = {}
    for x in theo_dong:
        k = x['dong'].astimezone(VN).date().isoformat()
        ngay_lai.setdefault(k, {'lai': 0.0, 'von': x.get('von_dau_ngay') or x.get('von_truoc')})
        ngay_lai[k]['lai'] += x.get('lai') or 0
    ngay_cham = sorted(k for k, v in ngay_lai.items() if v['lai'] < 0 and v['von'] and -v['lai'] / v['von'] * 100 >= q['lo_ngay_toi_da_pct'])
    lenh = [{'id': x.get('id'), 'ma': x['ma'], 'chieu': x['chieu'], 'mo': x['mo'].isoformat(), 'dong': x['dong'].isoformat(), 'lot': x.get('lot'),
             'vao': x.get('vao'), 'ra': x.get('ra'), 'sl': x.get('sl'), 'lai': x.get('lai'), 'nguon': x.get('nguon'), 'rui_ro_pct': x.get('rui_ro_pct'),
             'loi': x['loi']} for x in reversed(ds)]
    rr_ds = [x['rui_ro_pct'] for x in ds if x.get('rui_ro_pct') is not None]
    return {'n': n, 'diem': round(len(dat) / n * 100) if n else None, 'tong': nhom(ds), 'dat': nhom(dat), 'pham': nhom(pham),
            'rui_ro_tb_pct': round(sum(rr_ds) / len(rr_ds), 2) if rr_ds else None, 'rui_ro_max_pct': max(rr_ds) if rr_ds else None,
            'quy_tac': theo_qt, 'chuoi_thua_dai_nhat': dai,
            'lo_lon_nhat': ({'lai': lo_nhat.get('lai'), 'ma': lo_nhat['ma'], 'dong': lo_nhat['dong'].isoformat(),
                             'pct': round(-lo_nhat['lai'] / lo_nhat['von_truoc'] * 100, 2) if lo_nhat.get('von_truoc') and (lo_nhat.get('lai') or 0) < 0 else None}
                            if lo_nhat is not None and (lo_nhat.get('lai') or 0) < 0 else None),
            'ngay_cham_gioi_han': ngay_cham, 'khong_kiem_tin': khong_kiem_tin if tin_ds is not None else None,
            'co_lich_tin': tin_ds is not None, 'quy_tac_dung': q, 'lenh': lenh}


# --------------------------------------------------------------------------- đọc MT5 (chỉ đọc)
def ghep_lenh(deals, orders, ky_hieu: dict, tien_tk: str, so_du_hien: float, tu: datetime) -> list[dict]:
    """Ghép lần khớp mở/đóng thành từng lệnh đã đóng (vị thế đóng sau `tu`). `ky_hieu`: {ma: symbol_info}. Số dư trước mỗi lệnh dựng ngược từ số dư
    hiện tại trừ đi mọi thay đổi số dư (khớp lệnh, nạp, rút, phí) trong khoảng đã đọc."""
    from .kiem_lenh import _tien_lien_quan                                    # noqa: PLC0415
    from .doc_so import VN                                                   # noqa: PLC0415
    deals = sorted(deals, key=lambda x: (int(x.time), int(getattr(x, 'time_msc', 0) or 0)))
    tien = lambda x: float(x.profit) + float(x.commission or 0) + float(x.swap or 0) + float(getattr(x, 'fee', 0.0) or 0.0)   # noqa: E731
    so_du = so_du_hien - sum(tien(x) for x in deals)
    sl_lenh = {int(o.ticket): float(o.sl or 0) for o in orders}
    vt: dict = {}
    so_du_dau = so_du
    so_du_luc: list[tuple[datetime, float]] = []                            # (lúc khớp, số dư ngay SAU lần khớp đó)
    for x in deals:
        t = datetime.fromtimestamp(int(x.time), timezone.utc)
        so_du += tien(x)
        so_du_luc.append((t, so_du))
        if int(x.type) not in (0, 1):
            continue
        pid = int(getattr(x, 'position_id', 0) or 0)
        if not pid:
            continue
        v = vt.setdefault(pid, {'vao': [], 'ra': []})
        (v['vao'] if int(x.entry) == 0 else v['ra']).append((t, x))

    def so_du_truoc(t: datetime) -> float:
        """Số dư ngay trước thời điểm t: sau mọi lần khớp xảy ra TRƯỚC t (lần khớp mở của chính lệnh lúc t không tính)."""
        kq = so_du_dau
        for tt, sd in so_du_luc:
            if tt >= t:
                break
            kq = sd
        return kq

    out = []
    for pid, v in vt.items():
        if not v['vao'] or not v['ra']:
            continue
        t_mo, d0 = v['vao'][0]
        t_dong, dc = v['ra'][-1]
        if t_dong < tu:
            continue
        lot_vao = sum(float(x.volume) for _, x in v['vao'])
        lot_ra = sum(float(x.volume) for _, x in v['ra'])
        if lot_ra + 1e-9 < lot_vao:                                         # còn mở một phần: chưa tính
            continue
        mua = int(d0.type) == 0
        s = ky_hieu.get(d0.symbol)
        d = int(getattr(s, 'digits', 2)) if s is not None and getattr(s, 'digits', None) is not None else 2
        sl = sl_lenh.get(int(getattr(d0, 'order', 0) or 0)) or None
        vao = sum(float(x.price) * float(x.volume) for _, x in v['vao']) / lot_vao   # vào nhiều lần: giá vào trung bình theo khối lượng
        rr = None
        if sl and s is not None:
            tv, ts = float(getattr(s, 'trade_tick_value', 0) or 0), float(getattr(s, 'trade_tick_size', 0) or 0)
            gt1 = tv / ts if tv > 0 and ts > 0 else (float(s.trade_contract_size) if getattr(s, 'currency_profit', None) == tien_tk else None)
            kc = (vao - sl) if mua else (sl - vao)
            if gt1 and kc > 0:
                rr = kc * gt1 * lot_vao
            elif kc <= 0:
                rr = 0.0                                                    # dừng lỗ đã ở phía có lãi: không rủi ro
        ra = sum(float(x.price) * float(x.volume) for _, x in v['ra']) / lot_ra
        lai = sum(tien(x) for _, x in v['vao'] + v['ra'])
        von = so_du_truoc(t_mo)
        dau_ngay = datetime.combine(t_mo.astimezone(VN).date(), datetime.min.time(), tzinfo=VN)
        dt = {'cap': None, 'tien_goc': getattr(s, 'currency_base', None), 'tien_lai': getattr(s, 'currency_profit', None)} if s else {}
        out.append({'id': pid, 'ma': d0.symbol, 'chieu': 'MUA' if mua else 'BAN', 'mo': t_mo.isoformat(), 'dong': t_dong.isoformat(),
                    'lot': round(lot_vao, 2), 'vao': round(vao, d), 'ra': round(ra, d), 'sl': round(sl, d) if sl else None,
                    'dong_boi_sl': int(getattr(dc, 'reason', -1)) == 4, 'lai': round(lai, 2), 'magic': int(d0.magic),
                    'von_truoc': _r(von), 'von_dau_ngay': _r(so_du_truoc(dau_ngay)), 'rui_ro_tien': _r(rr),
                    'tien_lien_quan': _tien_lien_quan(dt, d0.symbol) if dt else ['USD']})
    return out


def doc(cfg: dict, now: datetime | None = None, ngay: int = 30, nguon: str | None = None, quy_tac: dict | None = None) -> dict:
    """Đọc lệnh đã đóng trong `ngay` ngày gần nhất rồi chấm. `nguon`: chỉ chấm lệnh của một nguồn ('Đặt tay', 'EA E'…), None = tất cả.
    Không nối được MT5 hoặc không phải tài khoản demo: {'san_sang': False, 'ly_do': ...}."""
    from . import song, tai_khoan, thi_truong                                # noqa: PLC0415
    from .__main__ import HERE                                               # noqa: PLC0415
    now = now or datetime.now(timezone.utc)
    tu = now - timedelta(days=ngay)
    mt5 = tai_khoan._mt5(cfg['gia'])
    if mt5 is None:
        return {'san_sang': False, 'ly_do': song.ly_do() or 'chưa nối được MT5'}
    with song._khoa:
        a = mt5.account_info()
        if a is None:
            return {'san_sang': False, 'ly_do': 'MT5 không trả thông tin tài khoản'}
        if int(getattr(a, 'trade_mode', -1)) != int(getattr(mt5, 'ACCOUNT_TRADE_MODE_DEMO', 0)):
            return {'san_sang': False, 'ly_do': 'Tài khoản đang nối không phải tài khoản demo. Trang này chỉ đọc tài khoản demo.'}
        doc_tu = tu - timedelta(days=30)                                     # đọc lùi thêm để có lần khớp mở của lệnh giữ qua mốc
        deals = list(mt5.history_deals_get(doc_tu, now + timedelta(days=1)) or [])
        orders = list(mt5.history_orders_get(doc_tu, now + timedelta(days=1)) or [])
        ky_hieu = {m: mt5.symbol_info(m) for m in {x.symbol for x in deals if x.symbol}}
        tien_tk, so_du = a.currency, float(a.balance)
    gd = ghep_lenh(deals, orders, ky_hieu, tien_tk, so_du, tu)
    for x in gd:
        x['nguon'] = tai_khoan._ea(cfg, x.pop('magic'))
    cac_nguon = sorted({x['nguon'] for x in gd})
    if nguon:
        gd = [x for x in gd if x['nguon'] == nguon]
    tin, tin_tu, ly_do_tin = None, None, None
    try:
        lich = thi_truong.lich_tong(cfg, HERE, now, lui_gio=(ngay + 1) * 24, toi_ngay=0)
        ds = [e for e in lich.get('ds', []) if e.get('muc') == 3]
        if ds:
            # lịch phủ từ sự kiện sớm nhất có trong lịch (mọi mức), không phải từ tin mạnh đầu tiên: lệnh vào ngay trước tin mạnh đầu tiên vẫn được kiểm
            tin, tin_tu = ds, min(e['t'] for e in lich['ds'])
        else:
            ly_do_tin = 'lịch tin không có tin mạnh nào trong khoảng này'
    except Exception as e:                                                   # noqa: BLE001
        ly_do_tin = f'{type(e).__name__}: {e}'
    kq = cham(gd, {**(cfg.get('kiem_lenh') or {}), **(quy_tac or {})}, tin, tin_tu)
    return {'san_sang': True, 'luc': now.isoformat(), 'ngay': ngay, 'tien': tien_tk, 'nguon': nguon, 'cac_nguon': cac_nguon,
            'ly_do_tin': ly_do_tin, **kq}
