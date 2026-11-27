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

import html
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import luu_ben, telegram_nhom

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


@dataclass(frozen=True)
class KhoRieng:
    thu_muc: Path
    chu: str


def kho_rieng(chu: str, goc: Path | None = None) -> KhoRieng:
    if not isinstance(chu, str) or not re.fullmatch(r'[0-9a-f]{32}', chu):
        raise ValueError('tài khoản cảnh báo không hợp lệ')
    data = telegram_nhom._tep(TEP).parent if goc is None else goc / 'du-lieu'
    return KhoRieng(data / 'canh-bao-nguoi-dung' / chu, chu)


def cac_kho(goc: Path | None = None) -> list:
    data = telegram_nhom._tep(TEP).parent if goc is None else goc / 'du-lieu'
    folder = data / 'canh-bao-nguoi-dung'
    return [KhoRieng(p, p.name) for p in folder.iterdir() if p.is_dir() and re.fullmatch(r'[0-9a-f]{32}', p.name)] if folder.exists() else []


# --------------------------------------------------------------------------- tệp
def _tep(ten: str, goc: Path | None = None) -> Path:
    if isinstance(goc, KhoRieng):
        return goc.thu_muc / ten
    return telegram_nhom._tep(ten) if goc is None else goc / 'du-lieu' / ten


def doc(goc: Path | None = None) -> dict:
    try:
        x = json.loads(_tep(TEP, goc).read_text(encoding='utf-8'))
    except FileNotFoundError:
        x = {}
    if not isinstance(x, dict) or not isinstance(x.get('ds', []), list) or not isinstance(x.get('da_bao', []), list):
        raise ValueError('Kho cảnh báo hỏng; cần phục hồi bản sao lưu.')
    return {'ds': [a for a in x.get('ds', []) if isinstance(a, dict)], 'da_bao': [b for b in x.get('da_bao', []) if isinstance(b, dict)]}


def _ghi(x: dict, goc: Path | None = None) -> None:
    p = _tep(TEP, goc)
    p.parent.mkdir(parents=True, exist_ok=True)
    luu_ben.ghi_json(p, x)


def cai(goc: Path | None = None) -> dict:
    try:
        x = json.loads(_tep(TEP_CAI, goc).read_text(encoding='utf-8'))
    except FileNotFoundError:
        x = {}
    if not isinstance(x, dict):
        raise ValueError('Kho kết nối cảnh báo hỏng; cần phục hồi bản sao lưu.')
    return {'chat_rieng': '', 'ten_chat': '', **x}


def _ghi_cai(c: dict, goc: Path | None = None) -> None:
    p = _tep(TEP_CAI, goc)
    p.parent.mkdir(parents=True, exist_ok=True)
    luu_ben.ghi_json(p, c)


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
    a = {'id': f'cbv{int(now * 1000):x}_{secrets.token_hex(8)}', 'ma': ma, 'ten': str(yc.get('ten') or ma or 'XAUUSD')[:40], 'tf': tf, 'loai': loai, 'dk': dk,
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
    dong = [f'🔔 <b>{html.escape(a["ten"])} {a["tf"]}</b>: {mo_ta} {TEN_LOAI[a["loai"]]}',   # tin Telegram kiểu HTML: tên có & hay < thì Telegram từ chối
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


def tao_ma_noi(goc=None, now=None) -> dict:
    now = time.time() if now is None else now
    code = 'hgr_' + secrets.token_urlsafe(18)
    with _khoa:
        c = cai(goc)
        c['noi_hash'] = hashlib.sha256(code.encode()).hexdigest()
        c['noi_tao'], c['noi_het'] = now, now + 600
        _ghi_cai(c, goc)
    return {'lenh': '/start ' + code, 'het': now + 600}


def kiem_ma_noi(goc=None, goi=None, now=None) -> tuple[bool, str]:
    now = time.time() if now is None else now
    c = cai(goc)
    digest = c.get('noi_hash')
    if not digest or now > c.get('noi_het', 0):
        return False, 'Mã nối đã hết hạn. Tạo mã mới rồi gửi riêng cho bot.'
    token = telegram_nhom.token()
    if not token:
        return False, 'Chưa cấu hình bot Telegram trên máy chủ.'
    r = (goi or telegram_nhom._goi)(token, 'getUpdates', {'limit': 100, 'allowed_updates': ['message']})
    if not r.get('ok'):
        return False, 'Chưa kiểm tra được tin nhắn của bot. Thử lại sau.'
    for update in r.get('result') or []:
        msg = update.get('message') or {}
        chat, sender = msg.get('chat') or {}, msg.get('from') or {}
        match = re.fullmatch(r'/start(?:@[A-Za-z0-9_]+)? (hgr_[A-Za-z0-9_-]{24})', msg.get('text') or '')
        if not match or chat.get('type') != 'private' or sender.get('id') != chat.get('id') or msg.get('forward_origin') or msg.get('forward_from'):
            continue
        if not int(c.get('noi_tao', now)) <= msg.get('date', 0) <= min(now + 5, c['noi_het']):
            continue
        if not hmac.compare_digest(hashlib.sha256(match[1].encode()).hexdigest(), digest) or not _chat_hop_le(str(chat.get('id')), goc):
            continue
        with _khoa:
            latest = cai(goc)
            if latest.get('noi_hash') != digest:
                return False, 'Mã nối đã được thay hoặc sử dụng. Tạo mã mới.'
            latest.update(chat_rieng=str(chat['id']), ten_chat=str(chat.get('first_name') or chat.get('username') or '')[:80])
            for key in ('noi_hash', 'noi_tao', 'noi_het'):
                latest.pop(key, None)
            _ghi_cai(latest, goc)
        return True, 'Đã xác nhận và nối Telegram riêng của tài khoản này.'
    return False, 'Chưa thấy mã nối trong chat riêng. Gửi đúng lệnh cho bot rồi kiểm tra lại.'


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
        tu = min((d[0] for a in cac for d in a.get('diem') or []), default=None)   # mốc cũ nhất của các hình: lấy nến phủ tới mốc đó
        try:
            dl = lay(ma, tf, tu)
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
        # Đứng ở nến cuối: thị trường đóng cửa (cuối tuần, giờ nghỉ) hay chưa có tick mới thì không có nến mới, đường xu hướng không được
        # "chạy" tiếp theo đồng hồ, kẻo giá đứng yên mà đường tự vượt qua giá rồi báo sai. Tối đa một nến sau nến cuối (liền mạch khi nến mới mở).
        luc_gia = dl.get('luc_gia')                                          # giờ của tick mới nhất (UTC): đường tính tại lúc có giá cuối cùng
        t_ref = min(now, luc_gia) if isinstance(luc_gia, (int, float)) and luc_gia > 0 else now
        x_nay = min(chi_so(times, t_ref, dt), float(len(times)))
        for a in cac:
            m_nay = muc(a, x_nay, times, dt)
            cu = nho.get(a['id'])
            if cu is None and isinstance(a.get('gia_cuoi'), (int, float)) and a.get('muc_cuoi'):
                cu = (a['gia_cuoi'], a['muc_cuoi'])                          # cảnh báo lặp sau khi khởi động lại: so từ lần báo trước, không báo lại
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
                a['gia_cuoi'], a['muc_cuoi'] = bid, m_nay
            else:
                bo.add(a['id'])
    if moi or het:
        with _khoa:
            x = doc(goc)                                                     # đọc lại: trang có thể vừa thêm hay xóa trong lúc kiểm
            sua = {a['id']: a for a in ds}
            x['ds'] = [{**a, **{k: sua[a['id']][k] for k in ('lan_cuoi', 'so_lan', 'gia_cuoi', 'muc_cuoi') if a['id'] in sua and k in sua[a['id']]}}
                       for a in x['ds'] if a.get('id') not in bo and a.get('het', now + 1) > now]
            x['da_bao'] = (x['da_bao'] + moi)[-GIU_DA_BAO:]
            _ghi(x, goc)
    return moi


class VongCanhVe(threading.Thread):
    """Kiểm mọi cảnh báo trên đường vẽ mỗi `giay` giây, chạy suốt khi webapp chạy."""

    def __init__(self, lay, giay: float = 5, goc=None):
        super().__init__(name='canh-bao-ve', daemon=True)
        self.lay, self.giay, self.nho = lay, giay, {}
        self.goc = goc
        self.tt = {'luc': None, 'loi': None, 'so_cho': 0}

    def mot_vong(self) -> None:
        """Một vòng: kiểm mọi cảnh báo, rồi chuyển từng lần báo mới cho các hàm trong KHI_BAO."""
        try:
            moi, errors, waiting = [], [], 0
            for store in [self.goc, *cac_kho(self.goc)]:
                try:
                    hits = mot_luot(self.lay, goc=store, nho=self.nho)
                    if not isinstance(store, KhoRieng):
                        moi.extend(hits)  # thông báo desktop chung chỉ dành cho kho chủ máy; kho riêng báo qua phiên web/Telegram riêng
                    waiting += len(doc(store)['ds'])
                except Exception as e:  # noqa: BLE001 - một kho hỏng không chặn cảnh báo của người khác
                    errors.append(type(e).__name__)
            self.tt.update(luc=time.time(), loi='; '.join(errors) or None, so_cho=waiting)
        except Exception as e:                                               # noqa: BLE001  vòng nền không được chết
            self.tt['loi'] = f'{type(e).__name__}: {e}'
            return
        for b in moi:
            for f in list(KHI_BAO):
                try:
                    f(b)
                except Exception:                                            # noqa: BLE001  móc của vỏ app hỏng không chặn móc khác, không làm vòng chết
                    pass

    def run(self) -> None:
        while True:
            self.mot_vong()
            time.sleep(self.giay)


def lay_tu_mt5(nap_cfg, so_nen: int = 600):
    """Hàm lấy giá cho vòng kiểm: đọc thẳng nến của khung (kể cả nến đang chạy) và giá Bid từ MT5, qua phiên nối an toàn của webapp (chỉ đọc,
    chỉ demo). Không dùng gia.goi / da_ma.goi như /api/gia: hai hàm đó dựng cả trang biểu đồ (mọi chỉ báo, phương pháp), đo được 0,1–15 giây mỗi
    lần, trong khi vòng kiểm chỉ cần nến và Bid (đọc thẳng dưới 1 mili giây). `ma` rỗng là mã vàng của cấu hình."""
    def lay(ma: str, tf: str, tu: float | None = None) -> dict:
        """`tu`: mốc cũ nhất của các hình đang kiểm. Mốc cũ hơn `so_nen` nến thì lấy nến từ mốc đó (tối đa một năm), để số thứ tự nến giữa
        hai mốc khớp với biểu đồ (biểu đồ có nến từ đầu năm); đếm theo đồng hồ thì tính cả cuối tuần, đường lệch hàng chục giá."""
        from datetime import datetime, timezone                             # noqa: PLC0415
        from . import da_ma                                                 # noqa: PLC0415 - nạp chậm; bài kiểm thay da_ma._mt5
        if tf not in GIAY_KHUNG:
            raise ValueError(f'khung {tf} không hợp lệ')
        cfg = nap_cfg()
        mt5 = da_ma._mt5(cfg.get('gia') or {})
        if mt5 is None:
            raise RuntimeError('chưa nối MT5')
        sym = ma or da_ma.ma_vang(cfg)
        khung = getattr(mt5, 'TIMEFRAME_' + tf)
        bay_gio = time.time()
        if tu is not None and tu < bay_gio - so_nen * GIAY_KHUNG[tf]:
            # giờ CÓ múi giờ UTC: thư viện MT5 hiểu giờ không múi giờ là giờ máy tính (lệch 7 tiếng ở Việt Nam)
            tu = max(tu - 5 * GIAY_KHUNG[tf], bay_gio - 366 * 86400)
            r = mt5.copy_rates_range(sym, khung, datetime.fromtimestamp(tu, timezone.utc), datetime.fromtimestamp(bay_gio + 60, timezone.utc))
        else:
            r = mt5.copy_rates_from_pos(sym, khung, 0, so_nen)
        tk = mt5.symbol_info_tick(sym)
        if r is None or len(r) == 0 or tk is None or not getattr(tk, 'bid', 0):
            raise RuntimeError(f'MT5 không trả giá của {sym}')
        info = mt5.symbol_info(sym)
        return {'candles': [[int(x['time']), float(x['open']), float(x['high']), float(x['low']), float(x['close'])] for x in r],
                'bid': float(tk.bid), 'luc_gia': int(getattr(tk, 'time', 0) or 0), 'so_le': int(getattr(info, 'digits', 2) if info is not None else 2)}
    return lay


VONG: VongCanhVe | None = None
# Móc cho mỗi lần báo mới: hàm f(b) nhận đúng dict mot_luot trả (ma, tf, gia, mo_ta…). Vỏ app (app.py) gắn thông báo Windows vào đây;
# webapp chạy từ dòng lệnh để trống. Gọi trong luồng của vòng kiểm nên hàm móc phải nhanh; ném lỗi thì bị bỏ qua.
KHI_BAO: list = []


def trang_thai(ma: str | None = None, goc=None) -> dict:
    x = doc(goc)
    c = cai(goc)
    ds = x['ds'] if ma is None else [a for a in x['ds'] if a.get('ma', '') == ma]
    return {'ds': ds, 'da_bao': x['da_bao'][-20:], 'telegram': {'co_bot': bool(telegram_nhom.token()), 'noi': bool(c.get('chat_rieng')),
            'ten': c.get('ten_chat', '')}, 'vong': ({**VONG.tt, 'so_cho': len(x['ds'])} if VONG else {'luc': None, 'loi': 'vòng kiểm chưa chạy', 'so_cho': len(x['ds'])})}


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
(()=>{const G=window.BDMN;if(!G)return;const $=s=>document.querySelector(s),U=window.HVD_CHU,H={'Content-Type':'application/json','X-So-Cong-Khai':'1',...(U?{'X-Chart-Owner':U.id}:{})};
let TT=null,dau=true,huy=null;const biet=new Set(),CH=[];
const LOAI={ngang:'ngang',tngang:'tngang',xu:'duong',tia:'duong',mt:'duong',kenh:'kenh',hop:'hop'};
const TENL={ngang:'đường ngang',tngang:'tia ngang',duong:'đường xu hướng',kenh:'kênh song song',hop:'hộp giá'};
const DKL={ngang:['cat','cat_len','cat_xuong'],tngang:['cat','cat_len','cat_xuong'],duong:['cat','cat_len','cat_xuong'],kenh:['ra','vao','cat'],hop:['vao','ra']};
const DKT={cat:'Giá cắt (lên hoặc xuống)',cat_len:'Giá cắt lên',cat_xuong:'Giá cắt xuống',vao:'Giá đi vào',ra:'Giá đi ra ngoài'};
const GK={M1:60,M2:120,M3:180,M5:300,M10:600,M15:900,M30:1800,H1:3600,H2:7200,H3:10800,H4:14400,D1:86400,W1:604800};   // độ dài khung danh nghĩa, như máy chủ (GIAY_KHUNG)
const DKK={cat:'cắt',cat_len:'cắt lên',cat_xuong:'cắt xuống',vao:'đi vào',ra:'đi ra'};
const gs=v=>Number(v).toLocaleString('vi-VN',{maximumFractionDigits:v<20?5:2});
const gio=s=>new Date(s*1000).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'});
async function goi(du){if(window.PHAT_LAI&&du.viec==='them')return{ok:false,ly_do:'Thoát phát lại để đặt cảnh báo giá trực tiếp.'};if(U===null){if(window.HVD_UI)HVD_UI.account();return{ok:false,ly_do:'Đăng nhập để dùng cảnh báo riêng.'}}const r=await fetch('/api/canh-bao-ve',{method:'POST',headers:H,body:JSON.stringify(du)});return r.json()}
// --- ô dưới biểu đồ
let P=$('#cbv');if(!P){const ch=$('.duoi .cum')||$('.duoi');if(!ch)return;P=document.createElement('aside');P.className='panel side cbv-p';P.id='cbv';P.setAttribute('aria-label','Cảnh báo trên đường vẽ');ch.appendChild(P)}
function hinhChon(){const g=G(),id=g.VE&&g.VE.chon;const h=id&&(g.VE.ds||[]).find(x=>x.id===id);return h&&LOAI[h.k]?h:null}
function oVe(){if(U===null){P.innerHTML='<h3>Cảnh báo trên đường vẽ</h3><p>Đăng nhập để dùng cảnh báo riêng.</p><button type="button" class="ghost" id="cbv-login">Đăng nhập</button>';return}const g=G(),ds=(TT&&TT.ds)||[],tg=(TT&&TT.telegram)||{},hc=hinhChon(),v=(TT&&TT.vong)||{};
 let s='<h3>Cảnh báo trên đường vẽ</h3><p class="why">Máy chủ của webapp kiểm giá mỗi 5 giây, kể cả khi bạn đóng trang. Chọn một đường, kênh hoặc hộp đã vẽ rồi đặt cảnh báo.</p>';
 s+=`<div class="cbv-hang"><button type="button" class="ictb" id="cbv-dat"${hc?'':' disabled'}>${hc?'🔔 Đặt cảnh báo cho '+TENL[LOAI[hc.k]]+' đang chọn':'🔔 Chọn một hình đã vẽ để đặt cảnh báo'}</button></div>`;
 const conHinh=new Set((g.VE&&g.VE.ds||[]).map(h=>h.id));                                    // cảnh báo gắn hình đã bị xóa: vẫn chạy theo đường cũ, ghi rõ để người dùng quyết
 if(ds.length)s+=ds.map(a=>`<div class="cbv-d"><span><b>${DKK[a.dk]} ${TENL[a.loai]}</b> · ${g.esc(a.ten)} ${a.tf}${a.lap?' · lặp lại':''}${a.hinh&&!conHinh.has(a.hinh)?' · <i>hình đã xóa</i>':''}</span><button type="button" class="cbv-x" data-x="${a.id}" title="Xóa cảnh báo" aria-label="Xóa cảnh báo">✕</button>${a.ghi_chu?'<small>'+g.esc(a.ghi_chu)+'</small>':''}</div>`).join('');
 else s+='<p class="why">Mã này chưa có cảnh báo nào.</p>';
 s+='<div class="cbv-tg">'+(tg.noi?`Telegram riêng: đã nối${tg.ten?' ('+g.esc(tg.ten)+')':''}. <button type="button" class="lk" id="cbv-bo">Ngắt</button>`:
  tg.co_bot?'Telegram riêng: chưa nối, nên cảnh báo chỉ báo trong trang. <button type="button" class="lk" id="cbv-noi">Nối Telegram riêng</button>':
  'Telegram: chưa có bot. Đặt mã bot ở trang <a href="/telegram">Nhóm Telegram</a> để nhận cảnh báo khi đóng trình duyệt; máy chủ webapp cần tiếp tục chạy.')+'</div>';
 if(v.loi&&!String(v.loi).startsWith('vòng kiểm chưa'))s+=`<p class="why">Vòng kiểm đang lỗi: ${g.esc(v.loi)}</p>`;
 const cu=((TT&&TT.da_bao)||[]).slice(-5).reverse();
 if(cu.length)s+='<div class="cbv-cu"><b>Đã báo gần đây</b>'+cu.map(b=>`<div>${gio(b.luc)} · ${g.esc(b.ten)} ${b.tf}: ${g.esc(b.mo_ta)} ${TENL[b.loai]} · giá ${gs(b.gia)}${b.telegram?' · đã gửi Telegram':''}</div>`).join('')+'</div>';
 P.innerHTML=s}
P.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;
 if(b.id==='cbv-login'){if(window.HVD_UI)HVD_UI.account()}else if(b.id==='cbv-dat'){const h=hinhChon();if(h)mo(h.id)}
 else if(b.dataset.x){await goi({viec:'xoa',id:b.dataset.x});tai()}
 else if(b.id==='cbv-noi')noiTg();
 else if(b.id==='cbv-bo'){await goi({viec:'bo_chat'});tai()}});
// --- hộp đặt cảnh báo
function dong(){const n=$('.cbv-nen');if(n)n.remove()}
function mo(id){if(U===null){if(window.HVD_UI)HVD_UI.account();return}const g=G(),h=(g.VE.ds||[]).find(x=>x.id===id);if(!h)return;const loai=LOAI[h.k];if(!loai){g.toast({tieu_de:'Hình này không đặt cảnh báo được',noi_dung:'Dùng đường ngang, tia ngang, đường xu hướng, tia, kênh hoặc hộp.'});return}
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
async function noiTg(){let j;try{j=await goi({viec:'tao_ma_noi'})}catch(e){return}if(!j.ok)return;dong();const n=document.createElement('div');n.className='cbv-nen';
 n.innerHTML='<div class="cbv-hop" role="dialog" aria-modal="true" aria-label="Nối Telegram riêng"><h3>Nối Telegram riêng</h3><p>Gửi lệnh dưới đây cho bot đã cấu hình, trong chat riêng của bạn. Mã dùng một lần, hết hạn sau 10 phút.</p><p><code></code></p><p class="loi"></p><div class="nut"><button type="button" data-close>Đóng</button><button type="button" data-check>Kiểm tra</button></div></div>';
 n.querySelector('code').textContent=j.lenh;document.body.appendChild(n);n.querySelector('[data-close]').onclick=()=>n.remove();n.addEventListener('click',e=>{if(e.target===n)n.remove()});n.addEventListener('keydown',e=>{if(e.key==='Escape')n.remove()});
 n.querySelector('[data-check]').onclick=async e=>{e.currentTarget.disabled=true;try{const r=await goi({viec:'kiem_ma_noi'});n.querySelector('.loi').textContent=r.ly_do||'';if(r.ok){n.remove();tai()}}catch(err){n.querySelector('.loi').textContent='Chưa kiểm tra được. Thử lại sau.'}finally{const b=n.querySelector('[data-check]');if(b)b.disabled=false}}}
// --- chuông trên các đường đang có cảnh báo (cùng khung), cập nhật mỗi lần biểu đồ vẽ lại
function chiSo(cs,t,dt){const n=cs.length;if(!n)return 0;if(t>cs[n-1][0])return n-1+(t-cs[n-1][0])/dt;if(t<cs[0][0])return(t-cs[0][0])/dt;let a=0,b=n-1;while(a<b){const m=(a+b+1)>>1;if(cs[m][0]<=t)a=m;else b=m-1}return a}
function chuong(){const g=G();for(const c of CH.splice(0))c.remove();if(!TT||!g.LW||!g.D||window.PHAT_LAI)return;const st=$('.stage'),lw=$('#lw');if(!st||!lw)return;
 const cs=g.D.candles||[],n=cs.length;if(!n)return;const dt=GK[g.tf]||(n>1?cs[n-1][0]-cs[n-2][0]:900),ts=g.LW.chart.timeScale(),r=lw.getBoundingClientRect(),rs=st.getBoundingClientRect();
 let pw=r.width;try{pw-=g.LW.chart.priceScale('right').width()}catch(e){}
 const vr=ts.getVisibleLogicalRange();if(!vr)return;const x=Math.min(n-1,Math.floor(vr.to)-1);
 for(const a of TT.ds||[]){if(a.loai!=='ngang'&&a.loai!=='hop'&&a.tf!==g.tf)continue;const d=a.diem;let m;
  if(a.loai==='ngang'||a.loai==='tngang')m=[d[0][1]];else if(a.loai==='hop')m=[d[0][1],d[1][1]];
  else{const xa=chiSo(cs,d[0][0],dt),xb=chiSo(cs,d[1][0],dt),p=xa===xb?d[0][1]:d[0][1]+(d[1][1]-d[0][1])*(x-xa)/(xb-xa);m=a.loai==='kenh'?[p,p+a.lech]:[p]}
  const X=ts.logicalToCoordinate(x);if(X==null)continue;
  for(const v of m){const Y=g.LW.nen.priceToCoordinate(v);if(Y==null||Y<0||Y>r.height)continue;const e=document.createElement('div');e.className='cbv-chuong';
   e.textContent='🔔 '+DKK[a.dk];e.style.left=Math.min(pw-30,Math.max(30,X))+(r.left-rs.left)+'px';e.style.top=Y+(r.top-rs.top)+'px';st.appendChild(e);CH.push(e)}}}
// --- tải trạng thái, báo khi máy chủ vừa báo
async function tai(){if(U===null){oVe();return}const g=G(),maYeuCau=g.ma;try{const r=await fetch('/api/canh-bao-ve?ma='+encodeURIComponent(g.ma||''),{cache:'no-store',headers:H});if(!r.ok)return;const j=await r.json();if(G().ma!==maYeuCau||(U&&j.chu!==U.id))return;TT=j}catch(e){return}
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
