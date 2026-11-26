# -*- coding: utf-8 -*-
"""Cảnh báo trên đường vẽ (26/11/2026): đặt cảnh báo lên một hình đã vẽ trên trang Biểu đồ (đường ngang, tia ngang, đường xu hướng, tia,
mũi tên, kênh song song, hộp); MÁY CHỦ của webapp kiểm giá mỗi vài giây nên vẫn báo khi đã đóng trang hay tắt trình duyệt.

Khớp đúng hình bạn thấy: công cụ vẽ đặt điểm theo số thứ tự nến của khung đang xem, nên đường xu hướng được tính theo số thứ tự nến của khung lúc
đặt cảnh báo (không theo thời gian thuần, kẻo lệch qua mỗi cuối tuần), kéo dài sang phải theo đúng độ dốc. Kênh: hai cạnh song song. Hộp: dải giá
giữa cạnh trên và cạnh dưới.

Điều kiện: đường (ngang, tia ngang, xu hướng): giá cắt (một chiều nào cũng được), cắt lên, cắt xuống. Kênh, hộp: giá đi vào, đi ra; kênh còn có
"cắt một cạnh". Chỉ báo khi giá thật sự đi qua sau lúc đặt (so giá lần kiểm trước với giá lần này), như TradingView; đặt xong không báo ngay.

Báo ở đâu: (1) trang Biểu đồ đang mở (khung nổi, tiếng, thông báo hệ thống); (2) Telegram RIÊNG: chat giữa bạn và bot, chỉ khi bạn tự nối
(nhắn /start cho bot rồi bấm Tìm). KHÔNG BAO GIỜ gửi vào nhóm hay kênh công khai của mô-đun telegram_nhom: chỉ nhận mã chat số dương (chat riêng)
và khác mã nhóm. Chỉ đọc giá; không đặt lệnh."""
from __future__ import annotations

import json
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import telegram_nhom

TEP = 'canh-bao-ve.json'
TEP_CAI = 'canh-bao-ve-cai.json'
GIAY_KHUNG = {'M1': 60, 'M5': 300, 'M15': 900, 'M30': 1800, 'H1': 3600, 'H4': 14400, 'D1': 86400}
LOAI = ('ngang', 'tngang', 'duong', 'kenh', 'hop')
DK = {'ngang': ('cat', 'cat_len', 'cat_xuong'), 'tngang': ('cat', 'cat_len', 'cat_xuong'), 'duong': ('cat', 'cat_len', 'cat_xuong'),
      'kenh': ('ra', 'vao', 'cat'), 'hop': ('vao', 'ra')}
TEN_LOAI = {'ngang': 'đường ngang', 'tngang': 'tia ngang', 'duong': 'đường xu hướng', 'kenh': 'kênh song song', 'hop': 'hộp giá'}
TEN_DK = {'cat': 'giá cắt', 'cat_len': 'giá cắt lên', 'cat_xuong': 'giá cắt xuống', 'vao': 'giá đi vào', 'ra': 'giá đi ra khỏi'}
TOI_DA = 200                    # số cảnh báo đang chờ tối đa
GIU_DA_BAO = 50                 # số lần báo gần nhất giữ lại để xem
LAP_CACH_GIAY = 600             # cảnh báo lặp lại: hai lần báo cách nhau ít nhất 10 phút
HAN_NGAY = 90                   # cảnh báo tự hết hạn sau 90 ngày
VN = timezone(timedelta(hours=7))
_khoa = threading.Lock()


# --------------------------------------------------------------------------- tệp
def _tep(ten: str, goc: Path | None = None) -> Path:
    return telegram_nhom._tep(ten) if goc is None else goc / 'du-lieu' / ten


def doc(goc: Path | None = None) -> dict:
    try:
        x = json.loads(_tep(TEP, goc).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        x = {}
    x = x if isinstance(x, dict) else {}
    return {'ds': [a for a in x.get('ds', []) if isinstance(a, dict)], 'da_bao': [b for b in x.get('da_bao', []) if isinstance(b, dict)]}


def _ghi(x: dict, goc: Path | None = None) -> None:
    p = _tep(TEP, goc)
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_suffix('.tmp')
    tam.write_text(json.dumps(x, ensure_ascii=False), encoding='utf-8')
    tam.replace(p)


def cai(goc: Path | None = None) -> dict:
    try:
        x = json.loads(_tep(TEP_CAI, goc).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        x = {}
    return {'chat_rieng': '', 'ten_chat': '', **(x if isinstance(x, dict) else {})}


def _ghi_cai(c: dict, goc: Path | None = None) -> None:
    p = _tep(TEP_CAI, goc)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(c, ensure_ascii=False), encoding='utf-8')


# --------------------------------------------------------------------------- hình học
def chi_so(times: list[int], t: float, dt: int) -> float:
    """Số thứ tự nến của thời điểm t, đúng như hàm vt của trang Biểu đồ: nến chứa t; sau nến cuối thì ngoại suy theo độ dài khung;
    trước nến đầu (hình vẽ cũ hơn dữ liệu đang có) cũng ngoại suy theo độ dài khung."""
    if not times:
        return 0.0
    if t > times[-1]:
        return len(times) - 1 + (t - times[-1]) / dt
    if t < times[0]:
        return (t - times[0]) / dt
    a, b = 0, len(times) - 1
    while a < b:
        m = (a + b + 1) >> 1
        if times[m] <= t:
            a = m
        else:
            b = m - 1
    return float(a)


def muc(a: dict, x: float, times: list[int], dt: int) -> list[float]:
    """Các mức giá của hình tại số thứ tự nến x: một mức cho đường, hai mức [dưới, trên] cho kênh và hộp."""
    d = a['diem']
    if a['loai'] in ('ngang', 'tngang'):
        return [d[0][1]]
    if a['loai'] == 'hop':
        return sorted([d[0][1], d[1][1]])
    xa, xb = chi_so(times, d[0][0], dt), chi_so(times, d[1][0], dt)
    p = d[0][1] if xa == xb else d[0][1] + (d[1][1] - d[0][1]) * (x - xa) / (xb - xa)
    if a['loai'] == 'duong':
        return [p]
    return sorted([p, p + a.get('lech', 0.0)])                                 # kênh: cạnh thứ hai lệch giá đều


def kiem(a: dict, truoc: float, nay: float, m_truoc: list[float], m_nay: list[float]) -> str | None:
    """Có báo không: trả câu mô tả nếu giá đã đi qua đúng điều kiện từ lần kiểm trước tới lần này, không thì None."""
    dk = a['dk']
    if len(m_nay) == 1:
        lt, ln = m_truoc[0], m_nay[0]
        len_ = truoc < lt and nay >= ln
        xuong = truoc > lt and nay <= ln
        if (dk == 'cat_len' and len_) or (dk == 'cat_xuong' and xuong) or (dk == 'cat' and (len_ or xuong)):
            return 'giá cắt lên' if len_ else 'giá cắt xuống'
        return None
    trong = lambda g, m: m[0] <= g <= m[1]                                      # noqa: E731
    t0, t1 = trong(truoc, m_truoc), trong(nay, m_nay)
    if dk == 'vao' and not t0 and t1:
        return 'giá đi vào'
    if dk == 'ra' and t0 and not t1:
        return 'giá thoát lên trên' if nay > m_nay[1] else 'giá thoát xuống dưới'
    if dk == 'cat':
        for i in (0, 1):
            if (truoc - m_truoc[i]) * (nay - m_nay[i]) < 0 or (truoc != m_truoc[i] and nay == m_nay[i]):
                return 'giá cắt cạnh ' + ('trên' if i else 'dưới')
    return None


# --------------------------------------------------------------------------- thêm, xóa
def _so(x) -> float:
    v = float(x)
    if v != v or v in (float('inf'), float('-inf')):
        raise ValueError('số không hợp lệ')
    return v


def chuan(yc: dict, now: float | None = None) -> dict:
    """Kiểm và chuẩn hóa một cảnh báo mới gửi từ trang. Sai thì ValueError kèm lý do."""
    now = time.time() if now is None else now
    loai = str(yc.get('loai', ''))
    if loai not in LOAI:
        raise ValueError('loại hình không đặt cảnh báo được')
    tf = str(yc.get('tf', 'M15'))
    if tf not in GIAY_KHUNG:
        raise ValueError('khung không hợp lệ')
    dk = str(yc.get('dk') or DK[loai][0])
    if dk not in DK[loai]:
        raise ValueError('điều kiện không hợp với loại hình')
    ma = str(yc.get('ma', '')).strip()
    if len(ma) > 40 or not re.fullmatch(r'[A-Za-z0-9._#+\-]*', ma):
        raise ValueError('mã không hợp lệ')
    so_diem = 1 if loai in ('ngang', 'tngang') else 2
    diem = yc.get('diem')
    if not isinstance(diem, list) or len(diem) < so_diem:
        raise ValueError('thiếu điểm của hình')
    diem = [[int(_so(d[0])), _so(d[1])] for d in diem[:so_diem]]
    if any(p <= 0 for _, p in diem) or any(not 946684800 <= t <= now + 400 * 86400 for t, _ in diem):
        raise ValueError('điểm của hình không hợp lệ')
    a = {'id': f'cbv{int(now * 1000):x}', 'ma': ma, 'ten': str(yc.get('ten') or ma or 'XAUUSD')[:40], 'tf': tf, 'loai': loai, 'dk': dk,
         'diem': diem, 'lech': _so(yc.get('lech', 0)) if loai == 'kenh' else 0.0, 'hinh': str(yc.get('hinh', ''))[:40],
         'ghi_chu': str(yc.get('ghi_chu', ''))[:200], 'lap': bool(yc.get('lap')), 'tao': now, 'het': now + HAN_NGAY * 86400,
         'gia_tao': _so(yc['gia_tao']) if yc.get('gia_tao') is not None else None, 'so_lan': 0}
    if loai == 'kenh' and a['lech'] == 0:
        raise ValueError('kênh chưa có độ rộng')
    return a


def them(yc: dict, goc: Path | None = None, now: float | None = None) -> tuple[bool, str, dict | None]:
    try:
        a = chuan(yc, now)
    except (ValueError, TypeError, KeyError, IndexError) as e:
        return False, f'Chưa đặt được: {e}.', None
    with _khoa:
        x = doc(goc)
        if len(x['ds']) >= TOI_DA:
            return False, f'Đã có {TOI_DA} cảnh báo đang chờ; xóa bớt rồi đặt tiếp.', None
        x['ds'].append(a)
        _ghi(x, goc)
    return True, f'Đã đặt cảnh báo: {TEN_DK[a["dk"]]} {TEN_LOAI[a["loai"]]} ({a["ten"]} {a["tf"]}).', a


def xoa(id_: str, goc: Path | None = None) -> bool:
    with _khoa:
        x = doc(goc)
        n = len(x['ds'])
        x['ds'] = [a for a in x['ds'] if a.get('id') != id_]
        _ghi(x, goc)
        return len(x['ds']) < n


def xoa_ma(ma: str, goc: Path | None = None) -> int:
    with _khoa:
        x = doc(goc)
        n = len(x['ds'])
        x['ds'] = [a for a in x['ds'] if a.get('ma') != ma]
        _ghi(x, goc)
        return n - len(x['ds'])


# --------------------------------------------------------------------------- báo
def _gia(x: float, le: int) -> str:
    s = f'{x:,.{le}f}'
    return s.replace(',', '§').replace('.', ',').replace('§', '.')


def soan(a: dict, mo_ta: str, gia_nay: float, m: list[float], le: int, luc: float) -> str:
    gio = datetime.fromtimestamp(luc, VN).strftime('%H:%M %d/%m')
    muc_s = ' – '.join(_gia(v, le) for v in m)
    dong = [f'🔔 <b>{a["ten"]} {a["tf"]}</b>: {mo_ta} {TEN_LOAI[a["loai"]]}',
            f'Giá {_gia(gia_nay, le)} · {"mức" if len(m) == 1 else "vùng"} {muc_s}', f'Lúc {gio} (giờ Việt Nam)']
    if a.get('ghi_chu'):
        dong.append('Ghi chú: ' + re.sub(r'[<>&]', '', a['ghi_chu']))
    dong.append('<i>Cảnh báo bạn tự đặt trên webapp. Không phải lời khuyên đầu tư.</i>')
    return '\n'.join(dong)


def _chat_hop_le(chat: str, goc: Path | None = None) -> bool:
    """Chỉ chat riêng (mã số dương) và không trùng nhóm/kênh công khai của telegram_nhom."""
    nhom = str(telegram_nhom.cai().get('chat', ''))
    return bool(re.fullmatch(r'[1-9]\d{3,15}', chat or '')) and chat != nhom


def gui_rieng(van_ban: str, goc: Path | None = None, goi=None) -> dict:
    c = cai(goc)
    chat = str(c.get('chat_rieng') or '')
    if not chat:
        return {'ok': False, 'loi': 'chưa nối Telegram riêng'}
    if not _chat_hop_le(chat, goc):
        return {'ok': False, 'loi': 'mã chat không phải chat riêng'}
    tk = telegram_nhom.token()
    if not tk:
        return {'ok': False, 'loi': 'chưa có mã bot'}
    r = (goi or telegram_nhom._goi)(tk, 'sendMessage', {'chat_id': chat, 'text': van_ban, 'parse_mode': 'HTML', 'disable_web_page_preview': True})
    return {'ok': bool(r.get('ok')), 'loi': None if r.get('ok') else telegram_nhom._che(str(r.get('description') or 'lỗi không rõ'), tk)}


def tim_chat(goi=None) -> tuple[bool, list | str]:
    """Các chat riêng đã nhắn cho bot gần đây (bạn mở bot, bấm Start hoặc gửi /start trước)."""
    tk = telegram_nhom.token()
    if not tk:
        return False, 'Chưa có mã bot. Đặt mã bot ở trang Nhóm Telegram trước.'
    g = goi or telegram_nhom._goi
    r = g(tk, 'getUpdates', {'limit': 100, 'allowed_updates': ['message']})
    if not r.get('ok'):
        return False, telegram_nhom._che(str(r.get('description') or 'lỗi không rõ'), tk)
    thay = {}
    for u in r.get('result') or []:
        ch = (u.get('message') or {}).get('chat') or {}
        if ch.get('type') == 'private' and ch.get('id'):
            ten = ' '.join(x for x in (ch.get('first_name'), ch.get('last_name')) if x) or ''
            thay[str(ch['id'])] = {'id': str(ch['id']), 'ten': (ten + (f' (@{ch["username"]})' if ch.get('username') else '')).strip()}
    if not thay:
        me = g(tk, 'getMe', {})
        ten_bot = ((me.get('result') or {}).get('username')) if me.get('ok') else None
        return False, ('Chưa thấy chat riêng nào. ' + (f'Mở t.me/{ten_bot}, ' if ten_bot else 'Mở bot của bạn trên Telegram, ')
                       + 'bấm Start (hoặc gửi /start), rồi bấm Tìm lại.')
    return True, list(thay.values())


def chon_chat(chat: str, ten: str = '', goc: Path | None = None, goi=None) -> tuple[bool, str]:
    chat = str(chat or '').strip()
    if not _chat_hop_le(chat, goc):
        return False, 'Chỉ nối được chat riêng giữa bạn và bot (không nhận nhóm hay kênh).'
    c = cai(goc)
    c.update(chat_rieng=chat, ten_chat=str(ten)[:80])
    _ghi_cai(c, goc)
    kq = gui_rieng('✅ Đã nối: cảnh báo trên đường vẽ của webapp sẽ báo vào đây, kể cả khi bạn đóng trang.', goc, goi)
    return True, 'Đã nối Telegram riêng.' + ('' if kq['ok'] else f' Tin thử chưa gửi được: {kq["loi"]}.')


def bo_chat(goc: Path | None = None) -> None:
    c = cai(goc)
    c.update(chat_rieng='', ten_chat='')
    _ghi_cai(c, goc)


# --------------------------------------------------------------------------- vòng kiểm
def mot_luot(lay, goc: Path | None = None, now: float | None = None, gui=None, nho: dict | None = None) -> list[dict]:
    """Một lượt kiểm mọi cảnh báo đang chờ. `lay(ma, tf)` trả dữ liệu giá như /api/gia (candles, dang_chay, bid, so_le) hoặc ném lỗi;
    `nho`: giá và mức của lần kiểm trước theo từng cảnh báo (vòng giữ giữa các lượt). Trả các lần báo mới."""
    now = time.time() if now is None else now
    nho = {} if nho is None else nho
    x = doc(goc)
    ds = [a for a in x['ds'] if a.get('het', now + 1) > now]
    het = len(ds) != len(x['ds'])
    nhom: dict[tuple, list] = {}
    for a in ds:
        nhom.setdefault((a.get('ma', ''), a.get('tf', 'M15')), []).append(a)
    moi, bo = [], set()
    for (ma, tf), cac in nhom.items():
        try:
            dl = lay(ma, tf)
        except Exception:                                                    # noqa: BLE001  mất giá một mã thì kiểm mã khác
            continue
        bid = dl.get('bid')
        cs = dl.get('candles') or []
        if not isinstance(bid, (int, float)) or not cs:
            continue
        times = [int(c[0]) for c in cs]
        if dl.get('dang_chay') and int(dl['dang_chay'][0]) > times[-1]:
            times.append(int(dl['dang_chay'][0]))
        dt = GIAY_KHUNG.get(tf, 900)
        le = dl.get('so_le') if isinstance(dl.get('so_le'), int) else 2
        x_nay = chi_so(times, now, dt)
        for a in cac:
            m_nay = muc(a, x_nay, times, dt)
            cu = nho.get(a['id'])
            if cu is None:                                                    # lần đầu: so với giá và mức lúc đặt
                g0 = a.get('gia_tao') if isinstance(a.get('gia_tao'), (int, float)) else bid
                cu = (g0, muc(a, chi_so(times, a['tao'], dt), times, dt))
            nho[a['id']] = (bid, m_nay)
            mo_ta = kiem(a, cu[0], bid, cu[1], m_nay)
            if not mo_ta or (a.get('lap') and now - a.get('lan_cuoi', 0) < LAP_CACH_GIAY):
                continue
            van_ban = soan(a, mo_ta, bid, m_nay, le, now)
            kq = (gui or gui_rieng)(van_ban, goc) if cai(goc).get('chat_rieng') else {'ok': False, 'loi': 'chưa nối Telegram riêng'}
            b = {'id': a['id'], 'luc': now, 'ma': ma, 'ten': a['ten'], 'tf': tf, 'loai': a['loai'], 'dk': a['dk'], 'mo_ta': mo_ta, 'gia': bid,
                 'muc': m_nay, 'ghi_chu': a.get('ghi_chu', ''), 'telegram': kq['ok'], 'loi_telegram': kq.get('loi'), 'hinh': a.get('hinh', '')}
            moi.append(b)
            if a.get('lap'):
                a['lan_cuoi'] = now
                a['so_lan'] = a.get('so_lan', 0) + 1
            else:
                bo.add(a['id'])
    if moi or het:
        with _khoa:
            x = doc(goc)                                                     # đọc lại: trang có thể vừa thêm hay xóa trong lúc kiểm
            sua = {a['id']: a for a in ds}
            x['ds'] = [{**a, **{k: sua[a['id']][k] for k in ('lan_cuoi', 'so_lan') if a['id'] in sua and k in sua[a['id']]}}
                       for a in x['ds'] if a.get('id') not in bo and a.get('het', now + 1) > now]
            x['da_bao'] = (x['da_bao'] + moi)[-GIU_DA_BAO:]
            _ghi(x, goc)
    return moi


class VongCanhVe(threading.Thread):
    """Kiểm mọi cảnh báo trên đường vẽ mỗi `giay` giây, chạy suốt khi webapp chạy."""

    def __init__(self, lay, giay: float = 5):
        super().__init__(name='canh-bao-ve', daemon=True)
        self.lay, self.giay, self.nho = lay, giay, {}
        self.tt = {'luc': None, 'loi': None, 'so_cho': 0}

    def run(self) -> None:
        while True:
            try:
                mot_luot(self.lay, nho=self.nho)
                self.tt.update(luc=time.time(), loi=None, so_cho=len(doc()['ds']))
            except Exception as e:                                           # noqa: BLE001  vòng nền không được chết
                self.tt['loi'] = f'{type(e).__name__}: {e}'
            time.sleep(self.giay)


VONG: VongCanhVe | None = None


def trang_thai(ma: str | None = None) -> dict:
    x = doc()
    c = cai()
    ds = x['ds'] if ma is None else [a for a in x['ds'] if a.get('ma', '') == ma]
    return {'ds': ds, 'da_bao': x['da_bao'][-20:], 'telegram': {'co_bot': bool(telegram_nhom.token()), 'noi': bool(c.get('chat_rieng')),
            'ten': c.get('ten_chat', '')}, 'vong': (VONG.tt if VONG else {'luc': None, 'loi': 'vòng kiểm chưa chạy', 'so_cho': len(x['ds'])})}


# --------------------------------------------------------------------------- phần trên trang Biểu đồ
CSS = r"""
.cbv-p .cbv-d{display:grid;grid-template-columns:1fr auto;gap:2px 8px;align-items:center;padding:8px 0;border-bottom:1px solid var(--line);font-size:12.5px}
.cbv-p .cbv-d:last-of-type{border-bottom:0}.cbv-p .cbv-d b{font-size:13px}.cbv-p .cbv-d small{grid-column:1/-1;color:var(--mute)}
.cbv-p .cbv-x{border:0;background:none;color:var(--mute);cursor:pointer;font-size:15px;line-height:1;padding:4px}.cbv-p .cbv-x:hover{color:var(--loss,#ff5a5f)}
.cbv-p .cbv-hang{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 4px}.cbv-p .cbv-tg{font-size:12.5px;color:var(--ink2);margin-top:8px}
.cbv-p .cbv-tg a,.cbv-p .cbv-tg button.lk{color:var(--series);background:none;border:0;padding:0;cursor:pointer;font:inherit;text-decoration:underline}
.cbv-p .cbv-tg button.lk{display:inline-flex;align-items:center;min-height:28px;padding:0 2px}
.cbv-p .cbv-cu{margin-top:8px;font-size:12px;color:var(--mute)}.cbv-p .cbv-cu div{padding:3px 0}
.cbv-chuong{position:absolute;z-index:4;transform:translate(-50%,-50%);pointer-events:none;font-size:12px;line-height:1;padding:3px 5px;border-radius:999px;
 background:#f5a623;color:#111;box-shadow:0 1px 4px rgba(0,0,0,.4);white-space:nowrap}
.cbv-nen{position:fixed;inset:0;z-index:60;background:rgba(0,0,0,.45);display:grid;place-items:center;padding:16px}
.cbv-hop{background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:12px;max-width:420px;width:100%;padding:16px 18px;box-shadow:0 10px 40px rgba(0,0,0,.45)}
.cbv-hop h3{margin:0 0 4px;font-size:16px}.cbv-hop p{margin:4px 0 10px;color:var(--ink2);font-size:13px;line-height:1.45}
.cbv-hop label.r{display:flex;gap:8px;align-items:center;padding:6px 0;font-size:13.5px;cursor:pointer}
.cbv-hop input[type=text]{width:100%;box-sizing:border-box;min-height:34px;margin-top:6px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink);padding:0 10px}
.cbv-hop .nut{display:flex;gap:8px;justify-content:flex-end;margin-top:14px}.cbv-hop .loi{color:#ff5a5f;font-size:12.5px;min-height:1em;margin-top:6px}
"""

JS = r"""
(()=>{const G=window.BDMN;if(!G)return;const $=s=>document.querySelector(s),H={'Content-Type':'application/json','X-So-Cong-Khai':'1'};
let TT=null,dau=true,huy=null;const biet=new Set(),CH=[];
const LOAI={ngang:'ngang',tngang:'tngang',xu:'duong',tia:'duong',mt:'duong',kenh:'kenh',hop:'hop'};
const TENL={ngang:'đường ngang',tngang:'tia ngang',duong:'đường xu hướng',kenh:'kênh song song',hop:'hộp giá'};
const DKL={ngang:['cat','cat_len','cat_xuong'],tngang:['cat','cat_len','cat_xuong'],duong:['cat','cat_len','cat_xuong'],kenh:['ra','vao','cat'],hop:['vao','ra']};
const DKT={cat:'Giá cắt (lên hoặc xuống)',cat_len:'Giá cắt lên',cat_xuong:'Giá cắt xuống',vao:'Giá đi vào',ra:'Giá đi ra ngoài'};
const DKK={cat:'cắt',cat_len:'cắt lên',cat_xuong:'cắt xuống',vao:'đi vào',ra:'đi ra'};
const gs=v=>Number(v).toLocaleString('vi-VN',{maximumFractionDigits:v<20?5:2});
const gio=s=>new Date(s*1000).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'});
async function goi(du){const r=await fetch('/api/canh-bao-ve',{method:'POST',headers:H,body:JSON.stringify(du)});return r.json()}
// --- ô dưới biểu đồ
let P=$('#cbv');if(!P){const ch=$('.duoi .cum')||$('.duoi');if(!ch)return;P=document.createElement('aside');P.className='panel side cbv-p';P.id='cbv';P.setAttribute('aria-label','Cảnh báo trên đường vẽ');ch.appendChild(P)}
function hinhChon(){const g=G(),id=g.VE&&g.VE.chon;const h=id&&(g.VE.ds||[]).find(x=>x.id===id);return h&&LOAI[h.k]?h:null}
function oVe(){const g=G(),ds=(TT&&TT.ds)||[],tg=(TT&&TT.telegram)||{},hc=hinhChon(),v=(TT&&TT.vong)||{};
 let s='<h3>Cảnh báo trên đường vẽ</h3><p class="why">Máy chủ của webapp kiểm giá mỗi 5 giây, kể cả khi bạn đóng trang. Chọn một đường, kênh hoặc hộp đã vẽ rồi đặt cảnh báo.</p>';
 s+=`<div class="cbv-hang"><button type="button" class="ictb" id="cbv-dat"${hc?'':' disabled'}>${hc?'🔔 Đặt cảnh báo cho '+TENL[LOAI[hc.k]]+' đang chọn':'🔔 Chọn một hình đã vẽ để đặt cảnh báo'}</button></div>`;
 if(ds.length)s+=ds.map(a=>`<div class="cbv-d"><span><b>${DKK[a.dk]} ${TENL[a.loai]}</b> · ${g.esc(a.ten)} ${a.tf}${a.lap?' · lặp lại':''}</span><button type="button" class="cbv-x" data-x="${a.id}" title="Xóa cảnh báo" aria-label="Xóa cảnh báo">✕</button>${a.ghi_chu?'<small>'+g.esc(a.ghi_chu)+'</small>':''}</div>`).join('');
 else s+='<p class="why">Mã này chưa có cảnh báo nào.</p>';
 s+='<div class="cbv-tg">'+(tg.noi?`Telegram riêng: đã nối${tg.ten?' ('+g.esc(tg.ten)+')':''}. <button type="button" class="lk" id="cbv-bo">Ngắt</button>`:
  tg.co_bot?'Telegram riêng: chưa nối, nên cảnh báo chỉ báo trong trang. <button type="button" class="lk" id="cbv-noi">Nối Telegram riêng</button>':
  'Telegram: chưa có bot. Đặt mã bot ở trang <a href="/telegram">Nhóm Telegram</a> để nhận cảnh báo cả khi tắt máy.')+'</div>';
 if(v.loi&&!String(v.loi).startsWith('vòng kiểm chưa'))s+=`<p class="why">Vòng kiểm đang lỗi: ${g.esc(v.loi)}</p>`;
 const cu=((TT&&TT.da_bao)||[]).slice(-5).reverse();
 if(cu.length)s+='<div class="cbv-cu"><b>Đã báo gần đây</b>'+cu.map(b=>`<div>${gio(b.luc)} · ${g.esc(b.ten)} ${b.tf}: ${g.esc(b.mo_ta)} ${TENL[b.loai]} · giá ${gs(b.gia)}${b.telegram?' · đã gửi Telegram':''}</div>`).join('')+'</div>';
 P.innerHTML=s}
P.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;
 if(b.id==='cbv-dat'){const h=hinhChon();if(h)mo(h.id)}
 else if(b.dataset.x){await goi({viec:'xoa',id:b.dataset.x});tai()}
 else if(b.id==='cbv-noi')noiTg();
 else if(b.id==='cbv-bo'){await goi({viec:'bo_chat'});tai()}});
// --- hộp đặt cảnh báo
function dong(){const n=$('.cbv-nen');if(n)n.remove()}
function mo(id){const g=G(),h=(g.VE.ds||[]).find(x=>x.id===id);if(!h)return;const loai=LOAI[h.k];if(!loai){g.toast({tieu_de:'Hình này không đặt cảnh báo được',noi_dung:'Dùng đường ngang, tia ngang, đường xu hướng, tia, kênh hoặc hộp.'});return}
 dong();const n=document.createElement('div');n.className='cbv-nen';
 n.innerHTML=`<div class="cbv-hop" role="dialog" aria-modal="true" aria-label="Đặt cảnh báo"><h3>🔔 Cảnh báo trên ${TENL[loai]}</h3>
  <p>${g.esc(g.tkMa())} · khung ${g.tf}. ${loai==='duong'?'Đường được tính kéo dài sang phải theo đúng độ dốc bạn vẽ, theo số nến của khung này. ':''}Chỉ báo khi giá đi qua sau lúc đặt, không báo ngay.</p>
  ${DKL[loai].map((k,i)=>`<label class="r"><input type="radio" name="cbv-dk" value="${k}"${i?'':' checked'}> ${DKT[k]}</label>`).join('')}
  <label class="r"><input type="checkbox" id="cbv-lap"> Lặp lại (mỗi lần cách nhau ít nhất 10 phút)</label>
  <input type="text" id="cbv-gc" maxlength="200" placeholder="Ghi chú (không bắt buộc), ví dụ: phá kênh thì canh bán">
  <div class="loi" id="cbv-loi"></div><div class="nut"><button type="button" class="ghost" id="cbv-huy">Hủy</button><button type="button" class="act" id="cbv-ok">Đặt cảnh báo</button></div></div>`;
 document.body.appendChild(n);n.addEventListener('click',e=>{if(e.target===n)dong()});$('#cbv-huy').onclick=dong;
 n.addEventListener('keydown',e=>{if(e.key==='Escape')dong()});$('#cbv-ok').focus();
 $('#cbv-ok').onclick=async()=>{const d=g.D||{},cs=d.candles||[],gia=d.bid!=null?d.bid:(cs.length?cs[cs.length-1][4]:null);
  const diem=loai==='ngang'||loai==='tngang'?[[h.a.t,h.a.p]]:[[h.a.t,h.a.p],[h.b.t,h.b.p]];
  const du={viec:'them',ma:g.ma||'',ten:g.tkMa(),tf:g.tf,loai,dk:(n.querySelector('input[name=cbv-dk]:checked')||{}).value,diem,lech:h.d||0,hinh:h.id,
   ghi_chu:$('#cbv-gc').value.trim(),lap:$('#cbv-lap').checked,gia_tao:gia};
  let kq;try{kq=await goi(du)}catch(e){kq={ok:false,ly_do:'Không gửi được tới webapp.'}}
  if(!kq.ok){$('#cbv-loi').textContent=kq.ly_do||'Chưa đặt được.';return}
  dong();g.toast({tieu_de:'🔔 '+kq.ly_do,noi_dung:'Máy chủ kiểm mỗi 5 giây, kể cả khi bạn đóng trang.'});
  if(window.Notification&&Notification.permission==='default')try{Notification.requestPermission()}catch(e){}tai()}}
// --- nối Telegram riêng
async function noiTg(){const g=G();let kq;try{kq=await goi({viec:'tim_chat'})}catch(e){return}
 if(!kq.ok){g.toast({tieu_de:'Nối Telegram riêng',noi_dung:kq.ly_do||'Chưa tìm được chat riêng.'});return}
 const ds=kq.ds||[];if(ds.length===1&&!confirm('Nối với chat riêng '+(ds[0].ten||ds[0].id)+'?'))return;
 let x=ds[0];if(ds.length>1){const i=prompt('Chọn chat riêng (gõ số):\n'+ds.map((c,i)=>(i+1)+'. '+(c.ten||c.id)).join('\n'),'1');x=ds[(+i||0)-1];if(!x)return}
 const r=await goi({viec:'chon_chat',id:x.id,ten:x.ten});g.toast({tieu_de:'Telegram riêng',noi_dung:r.ly_do||''});tai()}
// --- chuông trên các đường đang có cảnh báo (cùng khung), cập nhật mỗi lần biểu đồ vẽ lại
function chiSo(cs,t,dt){const n=cs.length;if(!n)return 0;if(t>cs[n-1][0])return n-1+(t-cs[n-1][0])/dt;if(t<cs[0][0])return(t-cs[0][0])/dt;let a=0,b=n-1;while(a<b){const m=(a+b+1)>>1;if(cs[m][0]<=t)a=m;else b=m-1}return a}
function chuong(){const g=G();for(const c of CH.splice(0))c.remove();if(!TT||!g.LW||!g.D||window.PHAT_LAI)return;const st=$('.stage'),lw=$('#lw');if(!st||!lw)return;
 const cs=g.D.candles||[],n=cs.length;if(!n)return;const dt=n>1?cs[n-1][0]-cs[n-2][0]:900,ts=g.LW.chart.timeScale(),r=lw.getBoundingClientRect(),rs=st.getBoundingClientRect();
 let pw=r.width;try{pw-=g.LW.chart.priceScale('right').width()}catch(e){}
 const vr=ts.getVisibleLogicalRange();if(!vr)return;const x=Math.min(n-1,Math.floor(vr.to)-1);
 for(const a of TT.ds||[]){if(a.loai!=='ngang'&&a.loai!=='hop'&&a.tf!==g.tf)continue;const d=a.diem;let m;
  if(a.loai==='ngang'||a.loai==='tngang')m=[d[0][1]];else if(a.loai==='hop')m=[d[0][1],d[1][1]];
  else{const xa=chiSo(cs,d[0][0],dt),xb=chiSo(cs,d[1][0],dt),p=xa===xb?d[0][1]:d[0][1]+(d[1][1]-d[0][1])*(x-xa)/(xb-xa);m=a.loai==='kenh'?[p,p+a.lech]:[p]}
  const X=ts.logicalToCoordinate(x);if(X==null)continue;
  for(const v of m){const Y=g.LW.nen.priceToCoordinate(v);if(Y==null||Y<0||Y>r.height)continue;const e=document.createElement('div');e.className='cbv-chuong';
   e.textContent='🔔 '+DKK[a.dk];e.style.left=Math.min(pw-30,Math.max(30,X))+(r.left-rs.left)+'px';e.style.top=Y+(r.top-rs.top)+'px';st.appendChild(e);CH.push(e)}}}
// --- tải trạng thái, báo khi máy chủ vừa báo
async function tai(){const g=G();try{const r=await fetch('/api/canh-bao-ve?ma='+encodeURIComponent(g.ma||''),{cache:'no-store'});if(!r.ok)return;TT=await r.json()}catch(e){return}
 for(const b of TT.da_bao||[]){const k=b.id+'@'+b.luc;if(biet.has(k))continue;biet.add(k);if(dau)continue;
  const tieu='🔔 '+b.ten+' '+b.tf+': '+b.mo_ta+' '+TENL[b.loai],nd='Giá '+gs(b.gia)+(b.ghi_chu?' · '+b.ghi_chu:'')+(b.telegram?' · đã gửi Telegram':'');
  g.toast({tieu_de:tieu,noi_dung:nd});g.beep();if(window.Notification&&Notification.permission==='granted')try{new Notification(tieu,{body:nd,tag:'cbv-'+k})}catch(e){}}
 dau=false;oVe();chuong()}
// cảnh báo một mức giá (menu chuột phải, Alt+A): đường ngang ở mức p, chiều theo giá hiện tại; trả kết quả của máy chủ
async function themGia(p,ghi_chu){const g=G(),d=g.D||{},cs=d.candles||[],cur=d.bid!=null?d.bid:(cs.length?cs[cs.length-1][4]:null);if(cur==null||!isFinite(p)||!cs.length)return{ok:false,ly_do:'Chưa có giá.'};
 const kq=await goi({viec:'them',ma:g.ma||'',ten:g.tkMa(),tf:g.tf,loai:'ngang',dk:p>=cur?'cat_len':'cat_xuong',diem:[[cs[cs.length-1][0],+p]],ghi_chu:ghi_chu||'',gia_tao:cur});
 if(kq.ok&&window.Notification&&Notification.permission==='default')try{Notification.requestPermission()}catch(e){}tai();return kq}
async function xoa(id){const kq=await goi({viec:'xoa',id});tai();return kq}
window.CBV={mo,tai,themGia,xoa,ds:()=>((TT&&TT.ds)||[])};
if(window.MNP&&typeof MNP.ve==='function'){const cu=MNP.ve;MNP.ve=function(){const kq=cu.apply(this,arguments);try{chuong()}catch(e){}return kq}}
let chonCu=null;setInterval(()=>{const g=G(),c=g.VE&&g.VE.chon;if(c!==chonCu){chonCu=c;oVe()}},400);   // nút "Đặt cảnh báo" theo hình đang chọn
let maCu=null;setInterval(()=>{const g=G();if(g.ma!==maCu){maCu=g.ma;tai()}},1000);
tai();setInterval(()=>{if(document.visibilityState==='visible')tai()},4000)})();
"""
