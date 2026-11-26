# -*- coding: utf-8 -*-
"""Nhóm Telegram cố định: webapp tự báo tín hiệu, kết quả từng lệnh, tin mạnh sắp ra và tổng kết ngày vào MỘT nhóm hoặc kênh của chủ dự án.

Người xem chỉ cần bấm đường mời (link_moi) để vào nhóm. Nguồn tin là nhật ký điểm vào của webapp (chỉ đọc) và lịch tin USD đã đo phản ứng giá.

Ba chế độ (du-lieu/telegram.json, đổi ở trang /telegram):
  'xem_truoc' (mặc định): soạn tin như thật nhưng KHÔNG gửi đi đâu; tin nằm ở trang /telegram để xem trước.
  'gui': gửi thật qua Telegram Bot API vào đúng một nhóm (chat). Chỉ chủ dự án bật, bằng nút trên trang của chính máy này.
  'tat': không soạn gì.
Mã bot (token) do chủ dự án tự đặt: biến môi trường HARRY_TELEGRAM_TOKEN hoặc tệp du-lieu/telegram-token.txt. Webapp chỉ đọc mã đó lúc gửi,
không bao giờ hiện, ghi ra nhật ký hay đưa vào bản sao lưu (tên tệp có chữ "token" nên sao_luu bỏ qua), và che nó khỏi mọi thông báo lỗi.

Nguyên tắc nội dung: báo MỌI lệnh đã đăng, kể cả lệnh thua; mỗi tín hiệu kèm dấu băm của dòng nhật ký (kiểm được, không sửa ngược được); không
hứa lãi, không nói tỷ lệ thắng chưa đo; mỗi tin có câu "không phải lời khuyên đầu tư". Lần đầu chạy chỉ đặt mốc, không đăng lại lịch sử.

Ảnh biểu đồ (tùy chọn 'anh_bieu_do', mặc định tắt): tin tín hiệu kèm ảnh chụp chính trang Biểu đồ của webapp với vùng vào, dừng lỗ, chốt lời của
đúng lệnh đó (so_cong_khai/anh_lenh.py). Ảnh không có lệnh hay số liệu của tài khoản. Không chụp được thì gửi chữ như cũ.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from . import giu_lenh, nhat_ky, thuong_hieu, trang
from .__main__ import HERE
from .doc_so import VN

API = 'https://api.telegram.org/bot{token}/{lenh}'
GIAY = 30                                    # chu kỳ của vòng nền
CACH_GUI = 1.5                               # giây giữa hai tin (Telegram giới hạn khoảng 20 tin/phút cho một nhóm)
TOI_DA_TRE = 30                              # tín hiệu ghi cách đây quá chừng này phút (webapp vừa tắt) thì không đăng nữa
GIU_TIN = 400                                # số tin giữ trong nhật ký gửi
MAC_DINH = {'che_do': 'xem_truoc', 'chat': '', 'link_moi': '', 'ten_nhom': '', 'tin_hieu': True, 'ma': ['bot:'], 'ket_qua': True,
            'tin_tuc': True, 'nhac_truoc_phut': 15, 'tong_ket': True, 'gio_tong_ket': 22, 'phan_tich': True, 'gio_phan_tich': [8, 19],
            'hoa_von_tp1': True, 'anh_bieu_do': False}
DIA_CHI = 'http://127.0.0.1:8765'             # địa chỉ của chính webapp, để chụp ảnh biểu đồ (web.py đặt theo cổng đang chạy)
CHU_THICH_TOI_DA = 1024                        # Telegram: chú thích ảnh tối đa 1.024 ký tự (sau khi bỏ thẻ HTML)
CHE_DO = ('xem_truoc', 'gui', 'tat')
MIEN = 'Không phải lời khuyên đầu tư. Bạn tự quyết và tự chịu rủi ro.'
_khoa = threading.Lock()
TT: dict = {}


# --------------------------------------------------------------------------- tệp
def _tep(ten: str, goc: Path = HERE) -> Path:
    return goc / 'du-lieu' / ten


def _doc_json(p: Path, mac_dinh):
    try:
        x = json.loads(p.read_text(encoding='utf-8'))
        return x if isinstance(x, type(mac_dinh)) else mac_dinh
    except (OSError, ValueError):
        return mac_dinh


def _ghi_json(p: Path, x) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_suffix('.tmp')
    tam.write_text(json.dumps(x, ensure_ascii=False, indent=1), encoding='utf-8')
    tam.replace(p)


def cai(goc: Path = HERE) -> dict:
    return {**MAC_DINH, **_doc_json(_tep('telegram.json', goc), {})}


def trang_thai(goc: Path = HERE) -> dict:
    return _doc_json(_tep('telegram-trang-thai.json', goc), {})


def _luu_tt(st: dict, goc: Path = HERE) -> None:
    _ghi_json(_tep('telegram-trang-thai.json', goc), st)


def token(goc: Path = HERE) -> str:
    """Mã bot do chủ dự án tự đặt. Không in, không trả ra ngoài mô-đun này."""
    t = os.environ.get('HARRY_TELEGRAM_TOKEN', '').strip()
    if not t:
        try:
            t = _tep('telegram-token.txt', goc).read_text(encoding='utf-8').strip()
        except OSError:
            t = ''
    return t if re.fullmatch(r'\d{5,}:[A-Za-z0-9_-]{30,}', t) else ''


def _che(s: str, tk: str) -> str:
    return s.replace(tk, '•••') if tk else s


def luu_cai(moi: dict, goc: Path = HERE) -> tuple[bool, str]:
    """Kiểm rồi lưu phần cài đặt người dùng gửi lên. Đổi chế độ dùng doi_che_do."""
    c = cai(goc)
    chat = str(moi.get('chat', c['chat']) or '').strip()
    if chat and not re.fullmatch(r'@[A-Za-z][A-Za-z0-9_]{3,}|-?\d{5,}', chat):
        return False, 'Mã nhóm phải có dạng @ten_nhom hoặc một số như -1001234567890.'
    link = str(moi.get('link_moi', c['link_moi']) or '').strip()
    if link and not re.fullmatch(r'https://t\.me/[A-Za-z0-9_+/-]{3,}', link):
        return False, 'Đường mời phải bắt đầu bằng https://t.me/ (lấy trong phần mời thành viên của nhóm).'
    ma = moi.get('ma', c['ma'])
    ma = [str(x).strip() for x in (ma.split(',') if isinstance(ma, str) else ma) if str(x).strip()][:12]
    try:
        truoc, gio = int(moi.get('nhac_truoc_phut', c['nhac_truoc_phut'])), int(moi.get('gio_tong_ket', c['gio_tong_ket']))
    except (TypeError, ValueError):
        return False, 'Số phút và giờ phải là số.'
    if not (5 <= truoc <= 120 and 0 <= gio <= 23):
        return False, 'Nhắc trước 5–120 phút; giờ tổng kết 0–23.'
    try:
        gio_pt = _gio_ds(moi.get('gio_phan_tich', c['gio_phan_tich']))
    except (TypeError, ValueError):
        return False, 'Giờ đăng phân tích: tối đa 4 giờ từ 0 tới 23, cách nhau dấu phẩy (ví dụ 8, 19).'
    c.update(chat=chat, link_moi=link, ten_nhom=str(moi.get('ten_nhom', c['ten_nhom']) or '').strip()[:60], ma=ma, nhac_truoc_phut=truoc, gio_tong_ket=gio,
             gio_phan_tich=gio_pt, **{k: bool(moi.get(k, c[k])) for k in ('tin_hieu', 'ket_qua', 'tin_tuc', 'tong_ket', 'phan_tich', 'hoa_von_tp1', 'anh_bieu_do')})
    if c['che_do'] == 'gui' and not c['chat']:
        c['che_do'] = 'xem_truoc'
    _ghi_json(_tep('telegram.json', goc), c)
    return True, 'Đã lưu.'


def doi_che_do(che_do: str, goc: Path = HERE) -> tuple[bool, str]:
    if che_do not in CHE_DO:
        return False, 'Chế độ không hợp lệ.'
    c = cai(goc)
    if che_do == 'gui':
        if not c['chat']:
            return False, 'Chưa có mã nhóm. Lưu mã nhóm trước.'
        if not token(goc):
            return False, 'Chưa có mã bot. Đặt mã bot vào du-lieu\\telegram-token.txt (xem hướng dẫn trên trang) rồi thử lại.'
    if che_do == 'gui':
        with _khoa:
            st = trang_thai(goc)
            if not st.get('gui_tu'):                          # lần đầu gửi thật: bỏ mọi thứ soạn lúc xem trước, thành tích tính từ đây
                for k in ('moc_id', 'bat_dau', 'tin_hieu'):
                    st.pop(k, None)
                st['gui_tu'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
                _luu_tt(st, goc)
    c['che_do'] = che_do
    _ghi_json(_tep('telegram.json', goc), c)
    return True, {'gui': 'Đã bật gửi thật vào nhóm.', 'xem_truoc': 'Đã chuyển về xem trước: không gửi gì đi.', 'tat': 'Đã tắt.'}[che_do]


# --------------------------------------------------------------------------- gửi
def _nhieu_phan(du: dict) -> tuple[bytes, str]:
    """Thân multipart/form-data cho sendPhoto: các trường của `du` và tệp ảnh ở du['_anh'] (trường 'photo')."""
    ranh = f'----harry{os.urandom(8).hex()}'
    phan = []
    for k, v in du.items():
        if k == '_anh':
            continue
        v = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
        phan.append(f'--{ranh}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode('utf-8'))
    anh = Path(du['_anh'])
    phan.append(f'--{ranh}\r\nContent-Disposition: form-data; name="photo"; filename="{anh.name}"\r\nContent-Type: image/png\r\n\r\n'.encode('utf-8')
                + anh.read_bytes() + b'\r\n')
    phan.append(f'--{ranh}--\r\n'.encode('utf-8'))
    return b''.join(phan), f'multipart/form-data; boundary={ranh}'


def _goi(tk: str, lenh: str, du: dict | None = None, timeout: float = 15) -> dict:
    if du and du.get('_anh'):                                   # sendPhoto kèm tệp ảnh
        try:
            than, loai = _nhieu_phan(du)
        except OSError as e:
            return {'ok': False, 'description': f'không đọc được ảnh: {type(e).__name__}'}
        req = urllib.request.Request(API.format(token=tk, lenh=lenh), data=than, headers={'Content-Type': loai}, method='POST')
        timeout = max(timeout, 30)
    else:
        req = urllib.request.Request(API.format(token=tk, lenh=lenh), data=json.dumps(du or {}).encode('utf-8'),
                                     headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode('utf-8'))
        except ValueError:
            return {'ok': False, 'description': f'HTTP {e.code}'}
    except (urllib.error.URLError, OSError, ValueError) as e:
        return {'ok': False, 'description': _che(f'{type(e).__name__}: {e}', tk)}


def _ghi_tin(muc: dict, goc: Path = HERE) -> None:
    p = _tep('telegram-tin.json', goc)
    ds = _doc_json(p, [])
    ds.append(muc)
    _ghi_json(p, ds[-GIU_TIN:])


def _chu(van_ban: str) -> str:
    """Phần chữ người xem thấy (bỏ thẻ HTML, trả lại ký tự đã mã hóa): Telegram đếm giới hạn chú thích trên phần này."""
    import html                                                  # noqa: PLC0415
    return html.unescape(re.sub(r'<[^>]+>', '', van_ban))


def gui(van_ban: str, loai: str, c: dict | None = None, tra_loi: int | None = None, goc: Path = HERE, goi=_goi, anh: Path | None = None) -> dict:
    """Gửi (hoặc chỉ soạn, ở chế độ xem trước) một tin. Trả {'ok', 'msg', 'loi', 'that'}; mọi tin đều được ghi vào du-lieu/telegram-tin.json.
    `anh`: tệp ảnh kèm theo. Chữ vừa chú thích ảnh thì gửi một tin ảnh có chú thích; dài hơn thì gửi ảnh trước rồi gửi chữ (mã tin là của tin chữ,
    để tin kết quả trả lời đúng tin có nội dung). Gửi ảnh lỗi thì vẫn gửi chữ như cũ."""
    c = c or cai(goc)
    kq = {'ok': True, 'msg': None, 'loi': None, 'that': False}
    if c['che_do'] == 'gui':
        tk = token(goc)
        if not tk or not c['chat']:
            kq.update(ok=False, loi='thiếu mã bot hoặc mã nhóm')
        else:
            r = None
            if anh is not None:
                vua = len(_chu(van_ban)) <= CHU_THICH_TOI_DA
                da = {'chat_id': c['chat'], '_anh': str(anh)}
                if vua:
                    da.update(caption=van_ban, parse_mode='HTML')
                ra = goi(tk, 'sendPhoto', da)
                if not ra.get('ok'):
                    kq['loi_anh'] = _che(str(ra.get('description') or 'lỗi không rõ'), tk)
                else:
                    kq['anh_da_gui'] = True                      # ảnh đã lên kênh: lần thử lại (nếu tin chữ lỗi) không gửi ảnh nữa
                if ra.get('ok') and vua:
                    r = ra                                       # một tin ảnh có đủ nội dung
            if r is None:
                du = {'chat_id': c['chat'], 'text': van_ban, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
                if tra_loi:
                    du['reply_parameters'] = {'message_id': tra_loi, 'allow_sending_without_reply': True}
                r = goi(tk, 'sendMessage', du)
            if r.get('ok'):
                kq.update(msg=(r.get('result') or {}).get('message_id'), that=True)
            else:
                kq.update(ok=False, loi=_che(str(r.get('description') or 'lỗi không rõ'), tk))
            time.sleep(CACH_GUI if goi is _goi else 0)
    _ghi_tin({'luc': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'loai': loai, 'che_do': c['che_do'], 'van_ban': van_ban,
              'ok': kq['ok'], 'loi': kq['loi'], **({'anh': Path(anh).name} if anh is not None else {}),
              **({'loi_anh': kq['loi_anh']} if kq.get('loi_anh') else {})}, goc)
    if not kq['ok']:
        TT['loi'] = f'{kq["loi"]} (lúc {datetime.now(VN):%H:%M %d/%m})'
    elif kq['that']:
        TT.pop('loi', None)                                      # gửi lại được rồi: lỗi cũ không còn đúng nữa
    return kq


def tim_nhom(goc: Path = HERE, goi=_goi) -> tuple[bool, list | str]:
    """Các nhóm, kênh mà bot đã thấy gần đây (cần thêm bot vào nhóm và gửi một tin trong nhóm trước)."""
    tk = token(goc)
    if not tk:
        return False, 'Chưa có mã bot.'
    r = goi(tk, 'getUpdates', {'limit': 100, 'allowed_updates': ['message', 'channel_post', 'my_chat_member']})
    if not r.get('ok'):
        return False, _che(str(r.get('description') or 'lỗi không rõ'), tk)
    thay = {}
    for u in r.get('result') or []:
        for k in ('message', 'channel_post', 'my_chat_member'):
            ch = (u.get(k) or {}).get('chat') or {}
            if ch.get('type') in ('group', 'supergroup', 'channel') and ch.get('id'):
                thay[ch['id']] = {'id': str(ch['id']), 'ten': ch.get('title') or '', 'loai': ch['type']}
    return True, list(thay.values())


# --------------------------------------------------------------------------- soạn tin
def so(x, le: int = 2) -> str:
    """Số kiểu Việt Nam: 3528.12 → 3.528,12."""
    if x is None:
        return '—'
    s = f'{abs(float(x)):,.{le}f}'.replace(',', '_').replace('.', ',').replace('_', '.')
    return ('−' if float(x) < 0 else '') + s


def _r(x) -> str:
    return ('+' if x > 0 else '') + so(x, 2) + 'R'


def _gio(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone(VN).strftime('%H:%M %d/%m')


def _sym(s: str) -> str:
    return re.sub(r'p$', '', s or '')


def soan_tin_hieu(r: dict, hv: dict | None = None) -> str:
    le = int(r.get('so_le') or 2)
    mua = r['huong'] == 'MUA'
    tps = list(r.get('tp') or [])
    i = r.get('i_chinh')
    i = int(i) if i is not None else (len(tps) - 1 if r.get('nhom') in ('pp', 'phieu') else 0)
    rr = r.get('rr') or []
    vao = f'{so(r["vao"], le)} · vào ngay' if not r.get('cho') else (
        f'{so(r["vao"], le)} · lệnh chờ ' + ('dừng' if r.get('loai') == 'dung' else 'giới hạn') + (f', hết hạn {_gio(r["het_han"])}' if r.get('het_han') else ''))
    dong = [f'{"🟢 MUA" if mua else "🔴 BÁN"} <b>{escape(_sym(r["sym"]))}</b> · {escape(r.get("ten") or r["ma"])} (#{r["id"]})',
            f'Vào: <b>{vao}</b>',
            f'Dừng lỗ: <b>{so(r["sl"], le)}</b> ({so(abs(float(r["vao"]) - float(r["sl"])), le)} giá)',
            'Chốt lời: ' + ' · '.join(f'TP{k + 1} {so(t, le)}' for k, t in enumerate(tps[:3])) + (f' (+{len(tps) - 3} mức nữa)' if len(tps) > 3 else '')]
    if tps:
        dong.append(f'Chấm thắng khi chạm TP{i + 1}' + (f' ({so(rr[i], 2)}R)' if len(rr) > i and rr[i] is not None else '') + '; chạm dừng lỗ trước là thua.')
    if r.get('ly_do'):
        dong.append(f'Lý do: {escape(str(r["ly_do"]))}')
    if r.get('phien') or r.get('bien_do'):
        dong.append(' · '.join(x for x in (f'Phiên {r["phien"]}' if r.get('phien') else '', f'biên độ {r["bien_do"]}' if r.get('bien_do') else '') if x))
    if hv and _la_bot(r) and tps:
        dong.append(f'🛡 Gợi ý giữ lệnh: chạm TP1 thì dời dừng lỗ phần còn lại về giá vào {so(r["vao"], le)}. Đo từ {hv["tu"]}: thắng '
                    f'{so(hv["thang"], 1)}% thay vì {so(hv["thang_goc"], 1)}%, sụt giảm nhỏ hơn; đổi lại lời mỗi lệnh {_r(hv["r"])} thay vì {_r(hv["r_goc"])}.')
    if r.get('bam'):
        dong.append(f'Dấu sổ: <code>{r["bam"][:16]}</code> (dòng đã ghi không sửa được)')
    dong.append(f'<i>{MIEN}</i>')
    return '\n'.join(dong)


def _la_bot(r: dict) -> bool:
    return str(r.get('ma') or '').startswith('bot:')


KET = {'thang': '✅ chạm chốt lời', 'thua': '❌ chạm dừng lỗ', 'het_gio': '⏱ hết giờ giữ lệnh', 'khong_khop': '⚪ lệnh chờ không khớp, hết hạn',
       'huy': '⚪ hủy: giá chạm dừng lỗ trước khi khớp', 'thay': '⚪ bị thay bằng điểm vào mới'}
XONG = tuple(KET)


def _da_dang(st: dict) -> set[int]:
    """Các tín hiệu đã đăng. Từ khi gửi thật lần đầu (gui_tu), chỉ tính tín hiệu đã THẬT SỰ lên nhóm: thành tích công khai không lẫn lệnh xem trước."""
    return {int(k) for k, v in (st.get('tin_hieu') or {}).items() if not v.get('bo_qua') and (v.get('that') or not st.get('gui_tu'))}


def thanh_tich(st: dict, ds: list[dict]) -> dict:
    """Số liệu của riêng các lệnh ĐÃ ĐĂNG vào nhóm: bao nhiêu lệnh đã xong, thắng, thua, tổng R."""
    da = _da_dang(st)
    xong = [r for r in ds if r['id'] in da and r.get('r') is not None and r['tt'] in ('thang', 'thua', 'het_gio')]
    return {'tu': st.get('bat_dau'), 'n': len(xong), 'thang': sum(r['r'] > 0 for r in xong), 'thua': sum(r['r'] <= 0 for r in xong),
            'tong_r': round(sum(r['r'] for r in xong), 2), 'mo': sum(1 for r in ds if r['id'] in da and r['tt'] in nhat_ky.SONG)}


def _dong_thanh_tich(t: dict) -> str:
    if not t['n']:
        return 'Chưa có lệnh nào của nhóm đóng xong.'
    tu = datetime.fromisoformat(t['tu']).astimezone(VN).strftime('%d/%m/%Y') if t.get('tu') else ''
    return f'Mọi lệnh đã đăng từ {tu}: {t["n"]} lệnh xong · thắng {t["thang"]} · thua {t["thua"]} · tổng <b>{_r(t["tong_r"])}</b>'


def soan_ket_qua(r: dict, t: dict, hv: dict | None = None) -> str:
    dau = f'{KET.get(r["tt"], r["tt"])} · #{r["id"]} {"MUA" if r["huong"] == "MUA" else "BÁN"} {escape(_sym(r["sym"]))}'
    if r.get('r') is not None:
        dau += f': <b>{_r(r["r"])}</b>'
    if hv and _la_bot(r) and r['tt'] == 'thang' and r.get('vao') is not None:
        dau += f'\n🛡 Ai giữ phần còn lại: dời dừng lỗ về giá vào {so(r["vao"], int(r.get("so_le") or 2))}.'
    return dau + '\n' + _dong_thanh_tich(t) + '\nMọi lệnh đều được báo kết quả, kể cả lệnh thua.'


def soan_tin_tuc(x: dict) -> str:
    dong = [f'📰 <b>{x["con_phut"]} phút nữa: {escape(x["ten"])}</b> ({_gio(x["luc"])} giờ Việt Nam)']
    if x.get('d15_tv') is not None:
        dong.append(f'Từ 2024, 15 phút sau tin này vàng thường chạy khoảng {so(x["d15_tv"], 1)} giá'
                    + (f'; 10% số lần trên {so(x["d15_p90"], 1)} giá.' if x.get('d15_p90') is not None else '.'))
    dong.append('Chiều giá sau tin không đoán trước được (đo trên tin 2015–2026). Giá có thể giật mạnh cả hai chiều, chênh lệch mua bán thường giãn rộng.')
    dong.append(f'<i>{MIEN}</i>')
    return '\n'.join(dong)


def soan_tong_ket(ngay: datetime, ds: list[dict], st: dict, t: dict) -> str:
    da = _da_dang(st)
    hom = [r for r in ds if r['id'] in da and datetime.fromisoformat(r['luc']).astimezone(VN).date() == ngay.date()]
    xong = [r for r in hom if r.get('r') is not None and r['tt'] in ('thang', 'thua', 'het_gio')]
    dong = [f'📊 <b>Tổng kết ngày {ngay:%d/%m/%Y}</b>']
    if not hom:
        dong.append('Hôm nay không có tín hiệu nào đủ điều kiện. Không vào lệnh cũng là một quyết định.')
    else:
        dong.append(f'Tín hiệu hôm nay: {len(hom)} · đã xong {len(xong)} (thắng {sum(r["r"] > 0 for r in xong)}, thua {sum(r["r"] <= 0 for r in xong)}'
                    + (f', tổng {_r(round(sum(r["r"] for r in xong), 2))}' if xong else '') + f') · còn mở hoặc chờ {sum(r["tt"] in nhat_ky.SONG for r in hom)}')
    dong.append(_dong_thanh_tich(t))
    dong.append(f'<i>Kết quả đã qua không bảo đảm kết quả sau này. {MIEN}</i>')
    return '\n'.join(dong)


XU = {1: '🟢 tăng', -1: '🔴 giảm', 0: '⚪ ngang'}
PT_CU_PHUT = 30                              # giá cũ hơn chừng này (thị trường nghỉ, MT5 mất kết nối) thì không đăng bài phân tích


def _gio_ds(x) -> list[int]:
    """'8, 19' hoặc [8, 19] → [8, 19]; giờ 0–23, tối đa 4 giờ, không trùng."""
    ds = x.replace(';', ',').split(',') if isinstance(x, str) else list(x or [])
    out = sorted({int(str(v).strip()) for v in ds if str(v).strip() != ''})
    if any(not 0 <= v <= 23 for v in out) or len(out) > 4:
        raise ValueError
    return out


LUAT_PT = (('bot', 'Luật bot', 'số đo dài nhất, có lãi ở phần kiểm 2022–2026'),       # (gốc mã, tên, độ tin) theo phan_tich.THONG_KE
           ('ba_khung', 'Ba khung', 'thắng nhiều nhưng cần thắng trên 80% mới hòa vốn, lời rất mỏng'),
           ('dinh_day', 'Đỉnh/đáy 8 giờ', 'lỗ ở 2023–2025, chỉ để tham khảo'))


def soan_phan_tich(pt: dict, tin_ds: list[dict], now: datetime) -> str | None:
    """Bài phân tích vàng từ kết quả của nút Phân tích (phan_tich.phan_tich). None khi giá cũ hoặc thiếu bối cảnh: không đăng bài trên giá cũ."""
    bc = pt.get('boi_canh') or {}
    if not bc or pt.get('bid') is None or pt.get('tuoi_phut') is None or pt['tuoi_phut'] > PT_CU_PHUT:
        return None
    vn = now.astimezone(VN)
    dong = [f'📈 <b>Phân tích vàng XAUUSD · {vn:%H:%M %d/%m/%Y}</b> (giờ Việt Nam)',
            f'Giá: <b>{so(pt["bid"])}</b>' + (f' · phiên {escape(str(bc["phien"]))}' if bc.get('phien') else '')]
    xu = bc.get('xu_huong') or {}
    khung = [k for k in ('D1', 'H4', 'H1') if k in xu]
    if khung:
        cung = {xu[k] for k in khung}
        ket = (' → ba khung cùng ' + ('tăng' if 1 in cung else 'giảm')) if len(cung) == 1 and 0 not in cung and len(khung) == 3 else ' → các khung chưa cùng chiều'
        dong.append('<b>Xu hướng</b>: ' + ' · '.join(f'{k} {XU.get(xu[k], "—")}' for k in khung) + ket)
    lt = bc.get('lien_thi_truong') or {}
    if lt.get('usd_ngay_pct') is not None:
        u = float(lt['usd_ngay_pct'])
        dong.append(f'<b>USD hôm nay</b>: {"tăng" if u > 0 else "giảm" if u < 0 else "đứng"} {so(abs(u))}% (đo qua {", ".join(escape(_sym(c)) for c in lt.get("cap") or [])}). '
                    'Vàng thường đi ngược USD.')
    vung = []
    if bc.get('khang_cu') is not None:
        vung.append(f'Kháng cự gần: <b>{so(bc["khang_cu"])}</b>')
    if bc.get('ho_tro') is not None:
        vung.append(f'Hỗ trợ gần: <b>{so(bc["ho_tro"])}</b>')
    for k, ten in (('tren', 'phía trên'), ('duoi', 'phía dưới')):
        z = (bc.get('vung') or {}).get(k)
        if z:
            vung.append(f'Vùng {ten}: {escape(str(z["loai"]).lower())} {so(z["duoi"])}–{so(z["tren"])}')
    ict = pt.get('ict') or {}
    if ict.get('dinh_hom_truoc') is not None and ict.get('day_hom_truoc') is not None:
        vung.append(f'Đỉnh / đáy hôm trước: {so(ict["dinh_hom_truoc"])} / {so(ict["day_hom_truoc"])}')
    if ict.get('bsl') is not None and ict.get('ssl') is not None:
        vung.append(f'Thanh khoản phía trên {so(ict["bsl"])} · phía dưới {so(ict["ssl"])}')
    if vung:
        dong.append('<b>Vùng giá đáng chú ý</b>\n' + '\n'.join('• ' + v for v in vung))
    if bc.get('atr_m15') is not None:
        dong.append(f'<b>Biến động</b>: một nến M15 chạy trung bình {so(bc["atr_m15"], 1)} giá'
                    + (f'; biên độ hôm nay {escape(str(bc["bien_do"]))} ({so(bc["bien_do_ty_le"])} lần mức thường)' if bc.get('bien_do') and bc.get('bien_do_ty_le') else '')
                    + '.')
    luat = []                                                    # từng luật một, kèm độ tin của nó: không gộp luật đang lỗ vào một con số "đồng thuận"
    for goc_ma, ten, tin in LUAT_PT:
        pa = [p for p in pt.get('phuong_an') or [] if str(p.get('ma') or '').split(':')[0] == goc_ma]
        if pa:
            h = sorted({p['huong'] for p in pa if p.get('co') and p.get('huong') in ('MUA', 'BAN')})
            luat.append(f'{ten}: {" / ".join("MUA" if x == "MUA" else "BÁN" for x in h) if h else "chưa có tín hiệu"} ({tin})')
    if luat:
        dong.append('<b>Các luật của hệ thống lúc này</b>\n' + '\n'.join('• ' + x for x in luat)
                    + '\nLệnh có điểm vào được đăng riêng khi luật bot ra tín hiệu.')
    toi = [x for x in tin_ds if x.get('con_phut') is not None and 0 < x['con_phut'] <= 24 * 60]
    if toi:
        dong.append('📰 <b>Tin USD mạnh trong 24 giờ tới</b>\n' + '\n'.join(
            f'• {_gio(x["luc"])} · {escape(x["ten"])}' + (f' · 15 phút sau tin vàng thường chạy {so(x["d15_tv"], 1)} giá' if x.get('d15_tv') is not None else '')
            for x in toi))
    else:
        dong.append('📰 Không có tin USD mạnh trong 24 giờ tới.')
    for cb in (pt.get('canh_bao') or [])[:2]:
        dong.append(f'⚠️ {escape(str(cb))}')
    dong.append(f'<i>Mô tả trạng thái thị trường theo các luật của hệ thống; không luật nào đoán chắc chiều giá. {MIEN}</i>')
    return '\n'.join(dong)


def dang_phan_tich(cfg: dict, now: datetime | None = None, goc: Path = HERE, c: dict | None = None, lay_pt=None, tin_toi=None, goi=_goi) -> dict:
    """Soạn và đăng (hoặc chỉ soạn, ở chế độ xem trước) một bài phân tích ngay. Trả {'ok', 'ly_do'}."""
    now = now or datetime.now(timezone.utc)
    c = c or cai(goc)
    try:
        if lay_pt is None:
            from . import phan_tich as PT                       # noqa: PLC0415 - nạp muộn: nặng, và chỉ cần khi tới giờ đăng
            lay_pt = PT.phan_tich
        pt = lay_pt(cfg)
    except Exception as e:                                       # noqa: BLE001
        return {'ok': False, 'ly_do': f'Không phân tích được: {type(e).__name__}.'}
    try:
        ds_tin = (tin_toi(cfg, now) if tin_toi else _tin_toi(cfg, now)).get('ds') or []
    except Exception:                                            # noqa: BLE001
        ds_tin = []
    van_ban = soan_phan_tich(pt, ds_tin, now)
    if van_ban is None:
        return {'ok': False, 'ly_do': 'Giá đang cũ (thị trường nghỉ hoặc MT5 chưa nối), không đăng bài phân tích trên giá cũ.'}
    kq = gui(van_ban, 'phan_tich', c, goc=goc, goi=goi)
    return {'ok': kq['ok'], 'ly_do': ('Đã gửi bài phân tích; mở kênh để xem.' if kq['that'] else 'Đã soạn bài phân tích (xem trước, chưa gửi).') if kq['ok']
            else f'Chưa gửi được: {kq["loi"]}'}


# --------------------------------------------------------------------------- vòng nền
def _hop(r: dict, c: dict) -> bool:
    return any(r.get('ma', '').startswith(m) for m in c['ma']) and not r.get('trung_voi')


def thu_muc_anh(goc: Path = HERE) -> Path:
    return _tep('anh-lenh', goc)


def chup_anh(r: dict, goc: Path = HERE) -> Path | None:
    """Ảnh biểu đồ của lệnh `r` (một lần cho mỗi tín hiệu; lỗi hay quá hạn thì None để gửi chữ)."""
    try:
        from . import anh_lenh                                   # noqa: PLC0415
        co = thu_muc_anh(goc) / f'lenh-{int(r["id"])}.png'
        if co.is_file() and co.stat().st_size > 0:                # đã chụp ở lượt trước (gửi lỗi): dùng lại, không mở trình duyệt lần nữa
            return co
        return anh_lenh.chup(DIA_CHI, r, thu_muc_anh(goc))
    except Exception:                                            # noqa: BLE001 - ảnh hỏng không chặn tin
        return None


def mot_luot(cfg: dict, now: datetime | None = None, goc: Path = HERE, doc_nk=None, tin_toi=None, goi=_goi, lay_pt=None, chup=None) -> dict:
    """Một lượt: đăng tín hiệu mới, kết quả lệnh đã đóng, tin sắp ra, bài phân tích, tổng kết ngày. Trả số tin đã soạn theo loại."""
    now = now or datetime.now(timezone.utc)
    chup = chup or (lambda r: chup_anh(r, goc))
    c = cai(goc)
    dem = {'tin_hieu': 0, 'ket_qua': 0, 'tin_tuc': 0, 'phan_tich': 0, 'tong_ket': 0}
    if c['che_do'] == 'tat':
        return dem
    with _khoa:
        st = trang_thai(goc)
        ds = doc_nk() if doc_nk else nhat_ky.danh_dau_trung(_doc_json(nhat_ky.tep(cfg), []))
        if 'moc_id' not in st:                                   # lần đầu: đặt mốc, không đăng lại lịch sử
            st.update(moc_id=max([r['id'] for r in ds] or [0]), bat_dau=st.get('gui_tu') or now.isoformat(timespec='seconds'), tin_hieu={},
                      tin=st.get('tin') or [])
        th = st.setdefault('tin_hieu', {})
        hv = giu_lenh.so_do() if c.get('hoa_von_tp1') else None
        if c['tin_hieu']:
            for r in ds:
                if r['id'] <= st['moc_id'] or str(r['id']) in th or not _hop(r, c):
                    continue
                if (now - datetime.fromisoformat(r['luc'])).total_seconds() > TOI_DA_TRE * 60 or r['tt'] in XONG:
                    th[str(r['id'])] = {'msg': None, 'bo_qua': True, 'bao': r['tt']}   # webapp vừa tắt lâu: không đăng muộn
                    continue
                # Lỗi đã gặp (rà soát 26/11/2026): chữ quá dài thì gửi ảnh trước rồi chữ; chữ lỗi mạng thì 30 giây sau gửi lại cả hai và ảnh bị đăng
                # trùng. Nhớ các tín hiệu đã lên ảnh để lần thử lại chỉ gửi chữ.
                da_anh = st.setdefault('da_anh', [])
                kq = gui(soan_tin_hieu(r, hv), 'tin_hieu', c, goc=goc, goi=goi,
                         anh=chup(r) if c.get('anh_bieu_do') and r['id'] not in da_anh else None)
                if kq.get('anh_da_gui') and not kq['ok'] and r['id'] not in da_anh:
                    da_anh.append(r['id'])
                    st['da_anh'] = da_anh[-200:]
                if kq['ok']:
                    th[str(r['id'])] = {'msg': kq['msg'], 'bao': r['tt'], 'that': kq['that']}
                    dem['tin_hieu'] += 1
        if c['ket_qua']:
            hien = {k: v for k, v in th.items() if not v.get('bo_qua')}
            for r in ds:
                v = hien.get(str(r['id']))
                if v is None or r['tt'] not in XONG or v.get('bao') in XONG:
                    continue
                if c['che_do'] == 'gui' and not v.get('that'):       # tín hiệu chỉ soạn lúc xem trước: người xem chưa thấy, không báo kết quả
                    v['bao'] = r['tt']
                    continue
                v['bao'] = r['tt']                              # đánh dấu trước để không tính hai lần trong thành tích
                kq = gui(soan_ket_qua(r, thanh_tich(st, ds), hv), 'ket_qua', c, tra_loi=v.get('msg'), goc=goc, goi=goi)
                if kq['ok']:
                    dem['ket_qua'] += 1
                else:
                    v['bao'] = 'loi'
        if c['tin_tuc']:
            try:
                ds_tin = (tin_toi(cfg, now) if tin_toi else _tin_toi(cfg, now)).get('ds') or []
            except Exception:                                    # noqa: BLE001 - lịch hỏng không chặn phần khác
                ds_tin = []
            da = st.setdefault('tin', [])
            for x in ds_tin:
                khoa = f'{x["luc"]}|{x["ten"]}'
                if 0 < x['con_phut'] <= c['nhac_truoc_phut'] and khoa not in da:
                    if gui(soan_tin_tuc(x), 'tin_tuc', c, goc=goc, goi=goi)['ok']:
                        da.append(khoa)
                        dem['tin_tuc'] += 1
            st['tin'] = da[-200:]
        vn = now.astimezone(VN)
        khe = f'{vn:%Y-%m-%d} {vn.hour:02d}'                  # mỗi giờ đã chọn đăng một lần; webapp bật muộn quá giờ đó thì bỏ, không đăng bài cũ
        da_pt = st.setdefault('phan_tich', [])
        if c.get('phan_tich') and vn.hour in (c.get('gio_phan_tich') or []) and khe not in da_pt:
            da_pt.append(khe)                                  # thử một lần mỗi khe (thị trường nghỉ thì bỏ qua, không thử lại mỗi 30 giây)
            if dang_phan_tich(cfg, now, goc, c, lay_pt=lay_pt, tin_toi=tin_toi, goi=goi)['ok']:
                dem['phan_tich'] += 1
            st['phan_tich'] = da_pt[-40:]
        if c['tong_ket'] and vn.hour >= c['gio_tong_ket'] and st.get('tong_ket') != vn.strftime('%Y-%m-%d'):
            if gui(soan_tong_ket(vn, ds, st, thanh_tich(st, ds)), 'tong_ket', c, goc=goc, goi=goi)['ok']:
                st['tong_ket'] = vn.strftime('%Y-%m-%d')
                dem['tong_ket'] += 1
        st['luot_cuoi'] = now.isoformat(timespec='seconds')
        _luu_tt(st, goc)
    return dem


def _tin_toi(cfg: dict, now: datetime) -> dict:
    from . import tin_phan_ung                                   # noqa: PLC0415
    return tin_phan_ung.tin_toi(cfg, now, 5)


class VongTelegram(threading.Thread):
    def __init__(self, doc_cfg, goc: Path = HERE, dia_chi: str | None = None):
        super().__init__(daemon=True, name='telegram')
        self.doc_cfg, self.goc = doc_cfg, goc
        if dia_chi:
            global DIA_CHI                                       # noqa: PLW0603
            DIA_CHI = dia_chi

    def run(self) -> None:
        time.sleep(20)
        while True:
            try:
                TT['dem'] = mot_luot(self.doc_cfg(), goc=self.goc)
                TT['loi_vong'] = None
            except Exception as e:                               # noqa: BLE001 - vòng nền không được chết
                TT['loi_vong'] = f'{type(e).__name__}: {_che(str(e), token(self.goc))}'
            time.sleep(GIAY)


def xem(cfg: dict | None = None, goc: Path = HERE) -> dict:
    c, st = cai(goc), trang_thai(goc)
    try:
        ds = nhat_ky.danh_dau_trung(_doc_json(nhat_ky.tep(cfg or {}), []))
    except Exception:                                            # noqa: BLE001
        ds = []
    tin = _doc_json(_tep('telegram-tin.json', goc), [])
    return {'cai': c, 'co_token': bool(token(goc)), 'thanh_tich': thanh_tich(st, ds), 'luot_cuoi': st.get('luot_cuoi'), 'bat_dau': st.get('bat_dau'),
            'loi': TT.get('loi') or TT.get('loi_vong'), 'tin': list(reversed(tin[-40:]))}


def link_moi(cfg: dict | None = None, goc: Path = HERE) -> str:
    """Đường mời vào nhóm để hiện trên webapp: từ trang /telegram, hoặc khóa 'nhom_telegram' trong cấu hình (bản chia sẻ)."""
    return cai(goc).get('link_moi') or str((cfg or {}).get('nhom_telegram') or '') or thuong_hieu.KENH_TELEGRAM


def muc_suc_khoe(goc: Path = HERE) -> dict:
    c = cai(goc)
    ten = 'Nhóm Telegram'
    if c['che_do'] == 'tat':
        return {'ten': ten, 'muc': 'tot', 'chi_tiet': 'Đang tắt.', 'lam': ''}
    if c['che_do'] == 'xem_truoc':
        return {'ten': ten, 'muc': 'tot', 'chi_tiet': 'Chế độ xem trước: tin được soạn ở trang /telegram, chưa gửi đi đâu.', 'lam': ''}
    loi = TT.get('loi') or TT.get('loi_vong')
    if loi or not token(goc):
        return {'ten': ten, 'muc': 'chu_y', 'chi_tiet': f'Gửi lỗi: {loi}.' if loi else 'Thiếu mã bot.', 'lam': 'Mở trang /telegram để xem và gửi tin thử.'}
    return {'ten': ten, 'muc': 'tot', 'chi_tiet': f'Đang gửi vào {c.get("ten_nhom") or c["chat"]}.', 'lam': ''}


# --------------------------------------------------------------------------- trang
CSS = """
.tg{display:grid;gap:14px;margin-top:14px;grid-template-columns:minmax(0,1fr)}.tg>*{min-width:0}.tg code{word-break:break-all}.tg .card{padding:14px;display:grid;gap:10px}
.tg .vao{display:flex;gap:14px;align-items:center;flex-wrap:wrap}.tg .vao a.nut{display:inline-flex;align-items:center;gap:8px;padding:10px 16px;border-radius:10px;
background:#2aabee;color:#fff;font-weight:700;text-decoration:none}.tg .vao a.nut:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.tg .cd{display:flex;gap:6px;flex-wrap:wrap}.tg .cd button[aria-pressed=true]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.tg form{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}.tg label{display:grid;gap:4px;font-size:13px}
.tg label.ck{display:flex;gap:8px;align-items:center}.tg input[type=text],.tg input[type=number]{min-height:36px;padding:0 10px;min-width:0}
.tg .so{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px}.tg .so div{border:1px solid var(--line);border-radius:8px;padding:8px 10px;display:grid;gap:2px}
.tg .so small{color:var(--mute);font-size:11.5px}.tg .so b{font-size:17px;font-variant-numeric:tabular-nums}
.tg .tin{display:grid;gap:8px;max-height:640px;overflow:auto}.tg .tin article{border:1px solid var(--line);border-radius:10px;padding:10px 12px;white-space:pre-wrap;
font-size:13.5px;line-height:1.5;background:var(--card2,transparent)}.tg .tin header{font-size:11.5px;color:var(--mute);margin-bottom:4px}
.tg .tin article.loi{border-color:var(--loss)}.tg .bao{min-height:1.2em;font-size:13px}.tg ol{margin:0;padding-left:18px;display:grid;gap:4px}
"""

JS = r"""
(()=>{const $=s=>document.querySelector(s),e=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const gui=o=>fetch('/api/telegram',{method:'POST',headers:{'Content-Type':'application/json','X-So-Cong-Khai':'1'},body:JSON.stringify(o)}).then(r=>r.json());
const sr=x=>(x>0?'+':'')+String(x.toFixed(2)).replace('.',',')+'R';
const tg=s=>e(s).replace(/&lt;(\/?)(b|i|code)&gt;/g,'<$1$2>');
const LOAI={tin_hieu:'Tín hiệu',ket_qua:'Kết quả',tin_tuc:'Tin sắp ra',phan_tich:'Phân tích',tong_ket:'Tổng kết',thu:'Tin thử'};
const bao=t=>{const b=$('#bao');if(b)b.textContent=t||''};
const ve=j=>{const c=j.cai,t=j.thanh_tich;
 $('#tg-vao').innerHTML=c.link_moi?`<div class="vao"><a class="nut" href="${e(c.link_moi)}" target="_blank" rel="noopener">Tham gia nhóm Telegram${c.ten_nhom?' · '+e(c.ten_nhom):''}</a>
  <code>${e(c.link_moi)}</code></div><div class="small">Gửi đường này cho người dùng; ai bấm vào cũng vào được nhóm để nhận tín hiệu, kết quả và tin sắp ra.</div>`
  :'<div class="small">Chưa có đường mời. Khi tạo xong nhóm, dán đường mời (https://t.me/...) vào ô bên dưới; nút "Tham gia nhóm" sẽ hiện ở đây.</div>';
 $('#tg-cd').innerHTML=[['xem_truoc','Xem trước (không gửi)'],['gui','Gửi thật vào nhóm'],['tat','Tắt']].map(([k,n])=>`<button type="button" class="ghost" data-cd="${k}" aria-pressed="${c.che_do===k}">${n}</button>`).join('')+
  (c.che_do==='gui'?'<button type="button" id="thu">Gửi tin thử</button>':'')+'<button type="button" class="ghost" id="pt">Đăng bài phân tích ngay</button>';
 $('#tg-tt').innerHTML=`Mã bot: <b>${j.co_token?'đã đặt':'chưa đặt'}</b> · Mã nhóm: <b>${e(c.chat)||'chưa có'}</b>${j.luot_cuoi?' · lượt gần nhất '+new Date(j.luot_cuoi).toLocaleTimeString('vi-VN'):''}`+
  (j.loi?`<br><span style="color:var(--loss)">Lỗi gần nhất: ${e(j.loi)}</span>`:'');
 $('#tg-so').innerHTML=`<div><small>Lệnh đã đăng, đã xong</small><b>${t.n}</b></div><div><small>Thắng / thua</small><b>${t.thang} / ${t.thua}</b></div>
  <div><small>Tổng</small><b>${t.n?sr(t.tong_r):'—'}</b></div><div><small>Còn mở hoặc chờ</small><b>${t.mo}</b></div>`;
 const f=$('#tg-f');if(!f.dataset.da){f.dataset.da=1;for(const k of ['chat','link_moi','ten_nhom','nhac_truoc_phut','gio_tong_ket'])f[k].value=c[k];f.ma.value=(c.ma||[]).join(', ');
  f.gio_phan_tich.value=(c.gio_phan_tich||[]).join(', ');for(const k of ['tin_hieu','ket_qua','tin_tuc','phan_tich','tong_ket','hoa_von_tp1','anh_bieu_do'])f[k].checked=!!c[k]}
 $('#tg-tin').innerHTML=j.tin.length?j.tin.map(m=>`<article class="${m.ok?'':'loi'}"><header>${LOAI[m.loai]||e(m.loai)} · ${new Date(m.luc).toLocaleString('vi-VN')} · ${m.che_do==='gui'?(m.ok?'đã gửi':'gửi lỗi: '+e(m.loi)):'xem trước, chưa gửi'}</header>${m.anh?`<a href="/telegram/anh/${encodeURIComponent(m.anh)}" target="_blank" rel="noopener"><img src="/telegram/anh/${encodeURIComponent(m.anh)}" alt="Ảnh biểu đồ kèm tin" loading="lazy" style="width:100%;max-width:640px;border-radius:8px;display:block;margin:4px 0 8px"></a>`:''}${m.loi_anh?`<div class="small" style="color:var(--loss)">Không gửi được ảnh (đã gửi chữ): ${e(m.loi_anh)}</div>`:''}${tg(m.van_ban)}</article>`).join('')
  :'<p class="small">Chưa có tin nào. Tin xuất hiện khi có tín hiệu mới, khi một lệnh đóng, 15 phút trước tin mạnh, vào giờ đăng phân tích và giờ tổng kết.</p>';
 document.querySelectorAll('[data-cd]').forEach(b=>b.onclick=()=>{const k=b.dataset.cd;
  if(k==='gui'&&!confirm('Từ giờ webapp sẽ tự gửi tín hiệu, kết quả, tin sắp ra, bài phân tích và tổng kết vào nhóm Telegram đã lưu. Bật gửi thật?'))return;
  gui({viec:'che_do',che_do:k}).then(r=>{bao(r.ly_do);nap()})});
 const th=$('#thu');if(th)th.onclick=()=>gui({viec:'thu'}).then(r=>{bao(r.ly_do);nap()});
 const pt=$('#pt');if(pt)pt.onclick=()=>{if(c.che_do==='gui'&&!confirm('Gửi ngay một bài phân tích vàng vào kênh?'))return;pt.disabled=true;bao('Đang phân tích…');gui({viec:'phan_tich'}).then(r=>{bao(r.ly_do);nap()}).finally(()=>{pt.disabled=false})}};
$('#tg-f').addEventListener('submit',ev=>{ev.preventDefault();const f=ev.target,o={viec:'luu'};
 for(const k of ['chat','link_moi','ten_nhom','ma','nhac_truoc_phut','gio_tong_ket','gio_phan_tich'])o[k]=f[k].value;for(const k of ['tin_hieu','ket_qua','tin_tuc','phan_tich','tong_ket','hoa_von_tp1','anh_bieu_do'])o[k]=f[k].checked;
 gui(o).then(r=>{bao(r.ly_do);f.dataset.da='';nap()})});
$('#tim').onclick=()=>gui({viec:'tim_nhom'}).then(r=>{if(!r.ok){bao(r.ly_do);return}
 $('#tim-kq').innerHTML=r.ds.length?r.ds.map(x=>`<button type="button" class="ghost" data-id="${e(x.id)}">${e(x.ten)} · ${e(x.loai)} · ${e(x.id)}</button>`).join(' ')
  :'Bot chưa thấy nhóm nào. Thêm bot vào nhóm, gửi một tin bất kỳ trong nhóm, rồi bấm lại.';
 document.querySelectorAll('#tim-kq [data-id]').forEach(b=>b.onclick=()=>{$('#tg-f').chat.value=b.dataset.id;bao('Đã điền mã nhóm; bấm Lưu.')})});
const nap=()=>fetch('/api/telegram',{cache:'no-store'}).then(r=>r.json()).then(ve).catch(()=>bao('Không đọc được trạng thái.'));
nap();setInterval(nap,30000);})();
"""


def trang_telegram(ten: str) -> str:
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Nhóm Telegram · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'telegram', '<button id="theme" type="button">Nền tối</button>') + '<main>',
        '<div class="top"><div><h1>Nhóm Telegram</h1></div><div class="stamp">tín hiệu, kết quả, tin sắp ra<br>tự gửi vào một nhóm cố định</div></div>',
        '<div class="tg">',
        '<section class="card" id="tg-vao"></section>',
        '<section class="card"><b>Thành tích của chính nhóm</b><div class="so" id="tg-so"></div>'
        '<div class="small">Chỉ tính các lệnh đã đăng vào nhóm, từ lúc bật. Mọi lệnh đều được báo kết quả, kể cả lệnh thua; mỗi tín hiệu kèm dấu của dòng nhật ký '
        'nên không ai sửa ngược được. Đây là cách cho người xem thấy hệ thống làm việc thật, thay cho lời hứa.</div></section>',
        '<section class="card"><b>Chế độ</b><div class="cd" id="tg-cd"></div><div class="small" id="tg-tt"></div><div class="bao" id="bao" role="status"></div></section>',
        '<section class="card"><b>Cài đặt nhóm</b><form id="tg-f">'
        '<label>Mã nhóm (chat)<input type="text" name="chat" placeholder="@ten_nhom hoặc -100…" autocomplete="off"></label>'
        '<label>Đường mời cho người dùng<input type="text" name="link_moi" placeholder="https://t.me/+…" autocomplete="off"></label>'
        '<label>Tên nhóm hiển thị<input type="text" name="ten_nhom" maxlength="60" autocomplete="off"></label>'
        '<label>Đăng tín hiệu của (mã bắt đầu bằng, cách nhau dấu phẩy)<input type="text" name="ma" placeholder="bot:" autocomplete="off"></label>'
        '<label>Nhắc trước tin mạnh (phút)<input type="number" name="nhac_truoc_phut" min="5" max="120"></label>'
        '<label>Giờ tổng kết ngày (giờ Việt Nam)<input type="number" name="gio_tong_ket" min="0" max="23"></label>'
        '<label>Giờ đăng phân tích vàng (giờ Việt Nam, cách nhau dấu phẩy)<input type="text" name="gio_phan_tich" placeholder="8, 19" autocomplete="off"></label>'
        '<label class="ck"><input type="checkbox" name="tin_hieu"> Tín hiệu mới</label><label class="ck"><input type="checkbox" name="ket_qua"> Kết quả từng lệnh</label>'
        '<label class="ck"><input type="checkbox" name="tin_tuc"> Tin USD mạnh sắp ra</label><label class="ck"><input type="checkbox" name="phan_tich"> Bài phân tích vàng</label>'
        '<label class="ck"><input type="checkbox" name="tong_ket"> Tổng kết cuối ngày</label>'
        '<label class="ck"><input type="checkbox" name="hoa_von_tp1"> Gợi ý dời dừng lỗ về giá vào sau TP1 (tín hiệu luật bot)</label>'
        '<label class="ck"><input type="checkbox" name="anh_bieu_do"> Kèm ảnh biểu đồ của lệnh (vùng vào, dừng lỗ, chốt lời; không có số liệu tài khoản)</label>'
        '<div><button type="submit">Lưu</button></div></form>'
        '<div class="small">Mặc định chỉ đăng tín hiệu của luật bot (mã bắt đầu bằng <code>bot:</code>), luật có số đo dài nhất trong hệ thống. '
        'Các phương pháp khác chưa qua cổng kiểm; thêm chúng vào nhóm nghĩa là đăng tín hiệu chưa được chứng minh.</div></section>',
        '<section class="card"><b>Nối nhóm lần đầu</b><ol class="small">'
        '<li>Trong Telegram, mở <b>@BotFather</b>, gõ <code>/newbot</code>, đặt tên; BotFather trả về một mã bot.</li>'
        '<li>Tự tạo tệp <code>du-lieu\\telegram-token.txt</code> trong thư mục webapp và dán mã bot vào đó (hoặc đặt biến môi trường HARRY_TELEGRAM_TOKEN). '
        'Webapp không hiện mã này ở đâu và không đưa nó vào bản sao lưu.</li>'
        '<li>Thêm bot vào nhóm, cho bot quyền quản trị (gửi tin). Với kênh, thêm bot làm quản trị viên của kênh.</li>'
        '<li>Gửi một tin bất kỳ trong nhóm, rồi bấm <button type="button" class="ghost nho" id="tim">Tìm nhóm của bot</button> để điền mã nhóm. Nhóm công khai có thể gõ thẳng @tên.</li>'
        '<li>Dán đường mời, bấm Lưu, chọn <b>Gửi thật vào nhóm</b>, rồi bấm <b>Gửi tin thử</b>.</li></ol><div class="small" id="tim-kq"></div>'
        '<p class="note" style="margin:0">Đăng tín hiệu giao dịch cho nhiều người có thể thuộc diện bị quản lý tùy nơi; ở Việt Nam, CFD và Forex với nhà môi giới nước ngoài '
        'chưa được cấp phép cho cá nhân. Nên hỏi luật sư trước khi mở nhóm công khai hoặc thu phí.</p></section>',
        '<section class="card"><b>Các tin gần đây</b><div class="tin" id="tg-tin"></div></section>',
        '</div>',
        f'<footer>{escape(trang.MIEN_TRU)}</footer></main><script>{trang.JS}</script><script>{JS}</script></body></html>'])
