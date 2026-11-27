"""Vị thế đang mở: một nguồn sự thật cho biểu đồ, Tổng quan và mọi nơi vẽ "lệnh đang mở" (27/11/2026).

Ba loại nguồn, không trộn lẫn:
- `mt5`: vị thế MT5 trả về cho tài khoản đang nối. Đây là nguồn chính, đã xác minh.
- `nhat_ky_ea`: lệnh vào ghi trong nhật ký sự kiện của EA mà chưa có dòng đóng. Nhật ký có thể cũ hoặc thiếu dòng đóng, nên phải
  đối chiếu với MT5 trước khi coi là còn mở.
- `bot`: lệnh gọi còn mở của bot tín hiệu. Đây là tín hiệu, không phải vị thế của tài khoản nào.

Đối chiếu nhật ký EA với MT5 (nhật ký không ghi số vé): cùng chiều, khối lượng lệch dưới 0,0051 lot, giờ mở lệch tối đa 5 phút, và
giá vào lệch tối đa 0,05% (khi nhật ký có giá). Một bản ghi MT5 chỉ ghép với một lệnh nhật ký.
- Khớp một vị thế MT5 còn mở: dùng số liệu MT5 (SL, TP, số vé đang có), nhãn EA từ nhật ký.
- Khớp một vị thế MT5 đã đóng trong lịch sử: lệnh đã đóng, KHÔNG hiện như lệnh đang mở; ghi lại giờ và giá đóng.
- MT5 đang nối đúng tài khoản của EA nhưng không có gì khớp: không coi là đang mở đã xác minh; hiện "theo nhật ký, chưa xác minh" kèm lý do.
- MT5 chưa nối, hoặc đang nối tài khoản khác: "theo nhật ký, chưa xác minh" kèm giờ dòng cuối của nhật ký.

Nhận ra tài khoản: khai `so_cuoi` (ba số cuối số tài khoản) cho từng tài khoản trong cau-hinh.json thì dùng đúng số đó; không khai thì
chỉ coi MT5 đang nối là của tài khoản này khi MT5 có vị thế hoặc giao dịch mang magic của chính các EA trong tài khoản. Không bao giờ
lấy vị thế của tài khoản này gán cho tài khoản khác. Mô-đun chỉ gọi hàm đọc của MT5 (account_info, positions_get, history_deals_get)."""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone

from . import doc_so, song, tai_khoan

LECH_GIAY = 300
LECH_GIA = 0.0005


def _r(x, d: int = 2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if x != x else round(x, d)


def _gio(t: int) -> datetime:
    return datetime.fromtimestamp(int(t), timezone.utc)


def anh_mt5(cfg: dict, now: datetime | None = None, ngay: int = 21) -> dict | None:
    """Ảnh chụp chỉ đọc của tài khoản MT5 đang nối: vị thế đang mở và các vị thế đã đóng trong `ngay` ngày (ghép theo position_id).
    None khi chưa nối được MT5 hoặc tài khoản không phải demo."""
    now = now or datetime.now(timezone.utc)
    mt5 = tai_khoan._mt5(cfg['gia'])
    if mt5 is None:
        return None
    with song._khoa:
        a = mt5.account_info()
        if a is None or int(getattr(a, 'trade_mode', -1)) != int(getattr(mt5, 'ACCOUNT_TRADE_MODE_DEMO', 0)):
            return None
        pos = mt5.positions_get()
        deals = mt5.history_deals_get(now - timedelta(days=ngay), now + timedelta(days=1))
        if pos is None or deals is None:
            return None
        current = mt5.account_info()
        if current is None or current.login != a.login or current.trade_mode != a.trade_mode:
            return None
    so = str(a.login)
    mo = [{'ve': int(getattr(p, 'ticket', 0) or 0), 'ma': p.symbol, 'huong': 'BUY' if int(p.type) == 0 else 'SELL', 'lot': _r(p.volume, 3),
           'vao': _r(p.price_open, 5), 'sl': _r(p.sl, 5) if p.sl else None, 'tp': _r(p.tp, 5) if p.tp else None, 'mo': _gio(p.time),
           'nguon': tai_khoan._ea(cfg, int(p.magic)), 'magic': int(p.magic)} for p in pos]
    theo_vt: dict = {}
    dong_le = []                                                    # lần khớp đóng không có position_id (MT5 cũ hoặc dữ liệu giả)
    for x in sorted(deals, key=lambda x: x.time):
        if int(x.type) not in (0, 1):
            continue
        vt = int(getattr(x, 'position_id', 0) or 0)
        rec = {'luc': _gio(x.time), 'gia': _r(x.price, 5), 'lot': _r(x.volume, 3), 'ma': x.symbol, 'nguon': tai_khoan._ea(cfg, int(x.magic)),
               'magic': int(x.magic), 'lai': _r(float(x.profit) + float(x.commission) + float(x.swap) + float(getattr(x, 'fee', 0.0) or 0.0))}
        if int(x.entry) == 0:
            rec['huong'] = 'BUY' if int(x.type) == 0 else 'SELL'
            if vt:
                theo_vt.setdefault(vt, {})['vao'] = rec
        else:
            rec['huong'] = 'SELL' if int(x.type) == 0 else 'BUY'     # khớp BÁN để đóng là đóng một vị thế MUA
            if vt:
                theo_vt.setdefault(vt, {}).setdefault('ra', []).append(rec)
            else:
                dong_le.append(rec)
    dang_mo = {m['ve'] for m in mo}
    da_dong = []
    for vt, r in theo_vt.items():
        if vt in dang_mo or not r.get('ra'):
            continue
        v, ra = r.get('vao'), r['ra'][-1]
        da_dong.append({'ve': vt, 'ma': ra['ma'], 'huong': ra['huong'], 'lot': (v or ra)['lot'], 'vao': v['gia'] if v else None, 'mo': v['luc'] if v else None,
                        'dong': ra['luc'], 'gia_dong': ra['gia'], 'lai': _r(sum(x['lai'] or 0 for x in r['ra'])), 'nguon': ra['nguon'], 'magic': ra['magic']})
    for ra in dong_le:
        da_dong.append({'ve': 0, 'ma': ra['ma'], 'huong': ra['huong'], 'lot': ra['lot'], 'vao': None, 'mo': None, 'dong': ra['luc'], 'gia_dong': ra['gia'],
                        'lai': ra['lai'], 'nguon': ra['nguon'], 'magic': ra['magic']})
    return {'so': '•••' + so[-3:], 'so_day_du': so, 'luc': now, 'mo': mo, 'da_dong': da_dong}


def la_tai_khoan(khai: dict, anh: dict | None) -> bool:
    """MT5 đang nối có phải tài khoản `khai` (một mục trong cfg['tai_khoan']) không."""
    if not anh:
        return False
    pin = khai.get('mt5_doi_chieu') or {}
    if pin.get('so'):
        return str(pin['so']) == anh['so_day_du']
    so_cuoi = str(khai.get('so_cuoi') or '').strip()
    if so_cuoi:
        return anh['so_day_du'].endswith(so_cuoi)
    ten = {e['ten'] for e in khai.get('ea', [])}
    return any(x['nguon'] in ten for x in anh['mo'] + anh['da_dong'])


def _khop(o: dict, x: dict) -> bool:
    if o.get('ma') and o['ma'] != x.get('ma'):
        return False
    if x['huong'] != o['side'] or abs(float(x['lot'] or 0) - float(o['lots'] or 0)) >= 0.0051:
        return False
    if not o.get('opened'):
        return False
    if x.get('mo') is not None:
        if abs((x['mo'] - o['opened']).total_seconds()) > LECH_GIAY:
            return False
    else:                                                         # chỉ có giờ đóng không đủ xác minh đây là cùng vị thế
        return False
    if o.get('entry') and x.get('vao'):
        return abs(float(x['vao']) - float(o['entry'])) <= max(0.01, LECH_GIA * float(o['entry']))
    return True


def doi_chieu_ea(o: dict, ten_ea: str, anh: dict | None, dung_tk: bool, da_dung: set) -> dict:
    """Trạng thái một lệnh vào còn mở theo nhật ký EA. `da_dung`: số vé MT5 đã ghép với lệnh khác (không ghép hai lần)."""
    if anh and dung_tk:
        ung = [x for x in anh['mo'] if x['nguon'] in (ten_ea, 'Đặt tay') or x['nguon'].startswith('EA (magic')]
        for x in sorted(ung, key=lambda x: abs((x['mo'] - o['opened']).total_seconds()) if o.get('opened') else 0):
            if x['ve'] not in da_dung and x['nguon'] == ten_ea and _khop(o, x):
                da_dung.add(x['ve'])
                return {'trang_thai': 'xac_minh', 'mt5': x}
        for x in sorted(anh['da_dong'], key=lambda x: x['dong']):
            if ('d', x['ve'], x['dong']) not in da_dung and x['nguon'] == ten_ea and _khop(o, x):
                da_dung.add(('d', x['ve'], x['dong']))
                return {'trang_thai': 'da_dong', 'mt5': x}
        return {'trang_thai': 'chua_xac_minh', 'ly_do': 'MT5 đang nối đúng tài khoản nhưng không có vị thế mở hay đã đóng khớp với lệnh này'}
    if anh is None:
        return {'trang_thai': 'chua_xac_minh', 'ly_do': 'chưa nối được MT5 để xác minh'}
    return {'trang_thai': 'chua_xac_minh', 'ly_do': 'MT5 đang nối một tài khoản khác'}


def _so(x):
    return _r(x, 5)


def tong_hop(cfg: dict, now: datetime | None = None, anh=...) -> dict:
    """Danh sách vị thế để vẽ và hiển thị, kèm danh sách lệnh nhật ký đã được MT5 xác nhận đóng. `anh` để bài kiểm truyền vào."""
    now = now or datetime.now(timezone.utc)
    if anh is ...:
        try:
            anh = anh_mt5(cfg, now)
        except Exception:                                                     # noqa: BLE001 - lỗi MT5 không làm mất phần còn lại
            anh = None
    ds, da_dong, tk_noi = [], [], None
    da_dung: set = set()
    ve_cua_ea: set = set()
    anh_chinh = anh
    for khai in cfg.get('tai_khoan', []):
        if khai.get('mt5_doi_chieu') and not la_tai_khoan(khai, anh_chinh):
            from . import doi_chieu_mt5
            anh = doi_chieu_mt5.anh_vi_the(khai, now)
        else:
            anh = anh_chinh
        da_dung = set()
        dung = la_tai_khoan(khai, anh)
        if dung and anh is anh_chinh:
            tk_noi = khai.get('ten')
        for e in khai.get('ea', []):
            try:
                ea = doc_so.doc_ea(e['tep'], e.get('lech_gio_utc', 0))
            except Exception:                                                 # noqa: BLE001 - thiếu tệp nhật ký thì bỏ qua EA này
                continue
            o = ea['open']
            if not o:
                continue
            luc_nk = ea['last_time'].astimezone(timezone.utc).isoformat() if ea.get('last_time') else None
            dc = doi_chieu_ea(o, e['ten'], anh, dung, da_dung)
            chung = {'ten': e['ten'], 'tai_khoan': khai.get('ten'), 'huong': o['side'], 'lot': o['lots'], 'ma': o.get('ma')}
            if dc['trang_thai'] == 'xac_minh':
                x = dc['mt5']
                if anh is anh_chinh:
                    ve_cua_ea.add(x['ve'])
                ds.append({**chung, 'nhan': f'{e["ten"]} {"MUA" if x["huong"] == "BUY" else "BÁN"} {x["lot"]:g}', 'lot': x['lot'], 'vao': _so(x['vao']),
                           'sl': x['sl'], 'tp': [x['tp']] if x['tp'] else [], 'loai': 'demo', 'nguon': 'mt5', 'xac_minh': True, 've': x['ve'],
                           'ma': x['ma'], 'luc_nguon': anh['luc'].isoformat(), 'so_tk': anh['so']})
            elif dc['trang_thai'] == 'da_dong':
                x = dc['mt5']
                da_dong.append({**chung, 'vao': _so(o['entry']), 'mo': o['opened'].isoformat() if o.get('opened') else None, 'dong': x['dong'].isoformat(),
                                'gia_dong': x['gia_dong'], 'lai': x['lai'], 've': x['ve'], 'ma': x['ma'], 'so_tk': anh['so'],
                                'ly_do': 'nhật ký EA thiếu dòng đóng; lịch sử MT5 cho thấy vị thế đã đóng'})
            else:
                ds.append({**chung, 'nhan': f'{e["ten"]} {"MUA" if o["side"] == "BUY" else "BÁN"} {o["lots"]:g}', 'vao': _so(o['entry']),
                           'sl': _so(o['sl']) if o['sl'] else None, 'tp': [_so(o['tp'])] if o['tp'] else [], 'loai': 'demo', 'nguon': 'nhat_ky_ea',
                           'xac_minh': False, 'luc_nguon': luc_nk, 'ly_do': dc['ly_do'],
                           'mo': o['opened'].isoformat() if o.get('opened') else None})
    anh = anh_chinh
    if anh:                                                                    # vị thế MT5 khác của tài khoản đang nối (đặt tay, EA khác)
        for x in anh['mo']:
            if x['ve'] in ve_cua_ea:
                continue
            ds.append({'ten': x['nguon'], 'tai_khoan': tk_noi, 'huong': x['huong'], 'lot': x['lot'],
                       'nhan': f'{x["nguon"]} {"MUA" if x["huong"] == "BUY" else "BÁN"} {x["lot"]:g}', 'vao': _so(x['vao']), 'sl': x['sl'],
                       'tp': [x['tp']] if x['tp'] else [], 'loai': 'mt5', 'nguon': 'mt5', 'xac_minh': True, 've': x['ve'], 'ma': x['ma'],
                       'luc_nguon': anh['luc'].isoformat(), 'so_tk': anh['so']})
    return {'luc': now.isoformat(), 'mt5': {'noi': anh is not None, 'so': anh['so'] if anh else None, 'tai_khoan': tk_noi},
            'ds': ds, 'da_dong_theo_mt5': da_dong}


_nho = {'luc': 0.0, 'key': None, 'kq': None}


def tong_hop_nho(cfg: dict, giay: float = 10) -> dict:
    """tong_hop có nhớ ngắn hạn: biểu đồ hỏi mỗi vài giây, MT5 chỉ bị đọc tối đa một lần mỗi `giay` giây."""
    key = json.dumps([cfg.get('tai_khoan', []), cfg.get('gia', {}), (cfg.get('mt5_xem') or {}).get('magic')], sort_keys=True, default=str)
    now = time.monotonic()
    if _nho['key'] == key and now - _nho['luc'] < giay and _nho['kq'] is not None:
        return _nho['kq']
    kq = tong_hop(cfg)
    _nho.update(luc=now, key=key, kq=kq)
    return kq
