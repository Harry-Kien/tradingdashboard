"""Tạo bài Threads từ sổ của bot tín hiệu, ở dạng BẢN NHÁP CHƯA DUYỆT.

    python -m so_cong_khai.threads --loai ngay [--ngay 2026-11-20]
    python -m so_cong_khai.threads --loai tuan [--tuan 2026-W47]
    python -m so_cong_khai.threads --loai tuan --dua-vao-hang-cho

Mặc định chỉ viết bản xem trước vào out/threads/. Với --dua-vao-hang-cho, bản nháp được chép vào hàng chờ của Thread Auto
với approved = false. Thread Auto chỉ đăng bài có approved = true, nên chương trình này không bao giờ tự làm một bài lên mạng:
người duyệt phải tự đổi approved thành true."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import doc_so, tong_hop, thuong_hieu, duong
from .doc_so import VN

GIOI_HAN = 500                      # Thread Auto từ chối chú thích dài hơn 500 ký tự
THANG = {'en': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']}

CHU = {
    'en': {
        'ngay': 'Gold signal bot · log for {d}', 'tuan': 'Gold signal bot · week {w} ({a}–{b})',
        'nhan': '(signals from my own rule-based bot, not trades)',
        'dem': 'Calls: {n} · closed {c} · open {o}', 'tp1': 'Reached TP1: {k} of {m} decided', 'sl0': 'Stopped before any TP: {k} of {m}',
        'du': 'Reached all {t} TPs: {k}', 'khong': 'No calls in this period.',
        'mot_chieu': 'All {n} calls were {s} in a one-way market, so this says little about the rule itself.',
        'it': 'Under 30 closed calls: too few to judge.',
        'ket': 'Every call is logged, including the stops. Not financial advice.', 'the': '#XAUUSD #Forex',
        'BUY': 'BUY', 'SELL': 'SELL', 'mo': 'open, {k}/{t} TP', 'full': 'all {t} TPs', 'sl': 'stopped out', 'tpsl': 'TP{k}, then stop',
        'tay': 'closed by hand', 'han': '{k}/{t} TP, time exit', 'them': '+{k} more in the log',
        'k_tieu_de': 'SIGNAL LOG', 'k_phu': 'Signals from a rule-based bot. No orders placed. Not an account statement.',
        'k_goi': 'CALLS', 'k_tp1': 'REACHED TP1', 'k_sl0': 'STOPPED BEFORE ANY TP', 'k_cua': 'of {m}', 'k_muc': 'CALLS REACHING EACH TARGET',
        'k_ds': 'CALLS', 'k_chan': 'Source: the bot\'s own ledger, read-only. Every call is listed, including the stops. Not financial advice.',
    },
    'vi': {
        'ngay': 'Bot tín hiệu vàng · sổ ngày {d}', 'tuan': 'Bot tín hiệu vàng · tuần {w} ({a}–{b})',
        'nhan': '(tín hiệu từ bot theo luật của tôi, không phải lệnh thật)',
        'dem': 'Lệnh gọi: {n} · đã đóng {c} · còn mở {o}', 'tp1': 'Chạm TP1: {k}/{m} lệnh đã ngã ngũ', 'sl0': 'Chạm SL khi chưa có TP: {k}/{m}',
        'du': 'Đạt đủ {t} TP: {k}', 'khong': 'Không có lệnh gọi nào trong quãng này.',
        'mot_chieu': 'Cả {n} lệnh đều là {s} trong lúc giá chạy một chiều, nên chưa nói được gì về luật.',
        'it': 'Dưới 30 lệnh đã đóng: chưa đủ để nhận xét.',
        'ket': 'Mọi lệnh đều được ghi, kể cả lệnh chạm SL. Không phải lời khuyên đầu tư.', 'the': '#XAUUSD #Forex',
        'BUY': 'MUA', 'SELL': 'BÁN', 'mo': 'đang mở, {k}/{t} TP', 'full': 'đủ {t} TP', 'sl': 'chạm SL', 'tpsl': 'TP{k} rồi chạm SL',
        'tay': 'đóng tay', 'han': '{k}/{t} TP, hết hạn giữ', 'them': '+{k} lệnh nữa trong sổ',
        'k_tieu_de': 'SỔ TÍN HIỆU', 'k_phu': 'Tín hiệu từ bot theo luật. Không đặt lệnh. Không phải sao kê tài khoản.',
        'k_goi': 'LỆNH GỌI', 'k_tp1': 'CHẠM TP1', 'k_sl0': 'CHẠM SL KHI CHƯA CÓ TP', 'k_cua': 'trên {m}', 'k_muc': 'SỐ LỆNH TỚI TỪNG MỨC',
        'k_ds': 'CÁC LỆNH', 'k_chan': 'Nguồn: sổ của chính bot, chỉ đọc. Mọi lệnh đều có trong sổ, kể cả lệnh chạm SL. Không phải lời khuyên đầu tư.',
    },
}


def _ngay(d, lang: str) -> str:
    return f'{d.day} {THANG["en"][d.month - 1][:3]}' if lang == 'en' else f'{d:%d/%m}'


def ket_qua(r: dict, lang: str) -> str:
    c, k, t = CHU[lang], r['tps_hit'], r['n_tps']
    if not r['closed']:
        return c['mo'].format(k=k, t=t)
    if k == t:
        return c['full'].format(t=t)
    if r['exit'] == 'SL':
        return c['tpsl'].format(k=k) if k else c['sl']
    if r['exit'] == 'CLOSE':
        return c['tay']
    return c['han'].format(k=k, t=t)


def _dong_lenh(r: dict, lang: str) -> str:
    # Không viết "#22": Threads sẽ biến nó thành thẻ chủ đề.
    return f'{r["call"]} · {CHU[lang][r["side"]]} {r["entry"]:.0f} · {ket_qua(r, lang)}'


def chu_bai(loai: str, b: dict, start: datetime, lang: str = 'en', so_lenh: int = 6) -> str:
    """Chú thích của bài, tối đa 500 ký tự. Bớt dần danh sách lệnh nếu quá dài; phần nhãn và miễn trừ luôn được giữ."""
    c = CHU[lang]
    end = start + timedelta(days=6)
    head = (c['ngay'].format(d=_ngay(start, lang)) if loai == 'ngay'
            else c['tuan'].format(w=start.isocalendar()[1], a=_ngay(start, lang), b=_ngay(end, lang)))
    body = [head, c['nhan'], '']
    if not b['n']:
        return '\n'.join(body + [c['khong'], '', c['ket'], c['the']])
    body.append(c['dem'].format(n=b['n'], c=b['closed'], o=b['open']))
    if b['decided']:
        body += [c['tp1'].format(k=b['tp1'], m=b['decided']), c['sl0'].format(k=b['sl0'], m=b['decided'])]
    if b['levels']:
        body.append(c['du'].format(t=len(b['levels']), k=b['full']))
    notes = []
    sides = {r['side'] for r in b['rows']}
    if len(sides) == 1 and b['n'] >= 3:
        notes.append(c['mot_chieu'].format(n=b['n'], s=c[sides.pop()]))
    if not b['enough']:
        notes.append(c['it'])
    tail = ['', c['ket'], c['the']]
    rows = list(reversed(b['rows']))
    for keep in range(min(so_lenh, len(rows)) if loai == 'ngay' else 0, -1, -1):
        lst = [_dong_lenh(r, lang) for r in rows[:keep]]
        if keep and keep < len(rows):
            lst.append(c['them'].format(k=len(rows) - keep))
        text = '\n'.join(body + ([''] + lst if lst else []) + ([''] + notes if notes else []) + tail)
        if len(text) <= GIOI_HAN:
            return text
    text = '\n'.join(body + ([''] + notes if notes else []) + tail)
    return text if len(text) <= GIOI_HAN else '\n'.join(body + tail)


# ------------------------------------------------------------------ ảnh thẻ 1080×1350
NEN, MUC, MUC2, VANG, KE, XANH, RANH = '#f4f1e8', '#17191c', '#52514e', '#8a6d1f', '#d9d3c2', '#2a78d6', '#e8e3d6'


def _font(ten: str, co: int):
    from PIL import ImageFont
    for f in (ten, 'arial.ttf'):
        try:
            return ImageFont.truetype(os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', f), co)
        except OSError:
            continue
    return ImageFont.load_default()


def _xuong_dong(draw, text: str, font, rong: int) -> list[str]:
    lines, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if draw.textlength(t, font=font) <= rong:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur] if cur else lines


def anh_the(path: Path, loai: str, b: dict, start: datetime, lang: str, ten: str, tai_khoan: str) -> Path:
    """Ảnh thẻ dọc 4:5 theo bộ nhận diện (nền ngà, chữ than, nhấn vàng trầm). Ghi rõ là sổ tín hiệu, không phải sao kê."""
    from PIL import Image, ImageDraw
    c = CHU[lang]
    W, H, M = 1080, 1350, 80
    im = Image.new('RGB', (W, H), NEN)
    d = ImageDraw.Draw(im)
    serif_b = 'cambriab.ttf'
    f_nhan, f_h1, f_phu = _font('seguisb.ttf', 26), _font(serif_b, 84), _font('segoeui.ttf', 30)
    f_so, f_nho, f_dong, f_chan = _font(serif_b, 92), _font('seguisb.ttf', 22), _font('segoeui.ttf', 32), _font('segoeui.ttf', 24)
    end = start + timedelta(days=6)

    d.text((M, 78), f'{ten.upper()}  ·  {c["k_tieu_de"]}', font=f_nhan, fill=VANG)
    d.line((M, 124, W - M, 124), fill=MUC, width=4)
    tieu_de = (f'{start.day} {THANG["en"][start.month - 1]} {start.year}' if lang == 'en' else f'Ngày {start:%d/%m/%Y}') if loai == 'ngay' else \
              (f'Week {start.isocalendar()[1]}' if lang == 'en' else f'Tuần {start.isocalendar()[1]}')
    d.text((M, 150), tieu_de, font=f_h1, fill=MUC)
    y = 256
    if loai == 'tuan':
        d.text((M, y), f'{_ngay(start, lang)} – {_ngay(end, lang)} {end.year}', font=f_phu, fill=MUC2)
        y += 46
    for line in _xuong_dong(d, c['k_phu'], f_phu, W - 2 * M):
        d.text((M, y), line, font=f_phu, fill=MUC2)
        y += 40

    y += 34
    cot = (W - 2 * M) // 3
    o = [(c['k_goi'], str(b['n']), f'{b["closed"]} closed · {b["open"]} open' if lang == 'en' else f'đã đóng {b["closed"]} · mở {b["open"]}'),
         (c['k_tp1'], str(b['tp1']), c['k_cua'].format(m=b['decided'])), (c['k_sl0'], str(b['sl0']), c['k_cua'].format(m=b['decided']))]
    d.line((M, y, W - M, y), fill=KE, width=2)
    for i, (nhan, gia_tri, phu) in enumerate(o):
        x = M + i * cot
        if i:
            d.line((x - 14, y + 22, x - 14, y + 200), fill=KE, width=2)
        d.text((x, y + 26), nhan, font=f_nho, fill=MUC2)
        d.text((x, y + 58), gia_tri, font=f_so, fill=MUC)
        d.text((x, y + 164), phu, font=f_chan, fill=MUC2)
    y += 224
    d.line((M, y, W - M, y), fill=KE, width=2)
    y += 40

    if loai == 'tuan' and b['levels'] and b['n']:
        d.text((M, y), c['k_muc'], font=f_nho, fill=MUC2)
        y += 48
        for i, n in enumerate(b['levels']):
            d.text((M, y + 2), f'TP{i + 1}', font=f_dong, fill=MUC2)
            x0, x1 = M + 96, W - M - 130
            d.rounded_rectangle((x0, y + 8, x1, y + 38), radius=6, fill=RANH)
            if n:
                d.rounded_rectangle((x0, y + 8, x0 + max(12, (x1 - x0) * n / b['n']), y + 38), radius=6, fill=XANH)
            d.text((W - M, y + 2), f'{n}/{b["n"]}', font=f_dong, fill=MUC, anchor='ra')
            y += 62
    else:
        d.text((M, y), c['k_ds'], font=f_nho, fill=MUC2)
        y += 48
        rows = list(reversed(b['rows']))
        for r in rows[:8]:
            d.text((M, y), str(r['call']), font=f_dong, fill=MUC2)
            d.text((M + 90, y), f'{c[r["side"]]}  {r["entry"]:.0f}', font=f_dong, fill=MUC)
            d.text((W - M, y), ket_qua(r, lang), font=f_dong, fill=MUC, anchor='ra')
            d.line((M, y + 50, W - M, y + 50), fill=RANH, width=2)
            y += 62
        if len(rows) > 8:
            d.text((M, y), c['them'].format(k=len(rows) - 8), font=f_chan, fill=MUC2)
        if not rows:
            d.text((M, y), c['khong'], font=f_dong, fill=MUC2)

    yc = H - 170
    d.line((M, yc, W - M, yc), fill=MUC, width=2)
    yy = yc + 22
    for line in _xuong_dong(d, c['k_chan'], f_chan, W - 2 * M):
        d.text((M, yy), line, font=f_chan, fill=MUC2)
        yy += 32
    if tai_khoan:
        d.text((W - M, H - 62), '@' + tai_khoan, font=f_nho, fill=VANG, anchor='ra')
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, 'PNG')
    return path


# ------------------------------------------------------------------ bản nháp và hàng chờ
def tao_ban_nhap(cfg: dict, loai: str, start: datetime, end: datetime, out: Path, now: datetime) -> dict:
    t = cfg['threads']
    lang = t.get('ngon_ngu', 'en')
    b = tong_hop.tom_bot(doc_so.doc_bot(cfg['bot_db']), start, end)
    ma = f'{start:%Y%m%d}' if loai == 'ngay' else f'{start.isocalendar()[0]}w{start.isocalendar()[1]:02d}'
    did = f'{t["kenh"]}-botlog-{loai}-{ma}'
    out.mkdir(parents=True, exist_ok=True)
    text = chu_bai(loai, b, start, lang)
    (out / f'{did}.caption.txt').write_text(text, encoding='utf-8')
    anh_the(out / f'{did}.image.png', loai, b, start, lang, thuong_hieu.TEN, t.get('tai_khoan', ''))
    draft = {'id': did, 'channel': t['kenh'], 'account': t['tai_khoan'], 'approved': False,
             'notBefore': now.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
             'expiresAt': (now + timedelta(hours=t.get('het_han_gio', 24))).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
             'captionFile': f'data/out/{did}.caption.txt', 'imageFile': f'data/out/{did}.image.png', 'topic': t.get('chu_de', 'Forex'),
             'source': 'bot-ledger', 'note': 'Tạo bởi so-cong-khai từ sổ của bot tín hiệu (chỉ đọc). Chưa duyệt: đổi approved thành true để cho đăng.'}
    (out / f'{did}.draft.json').write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'draft': draft, 'text': text, 'so_ky_tu': len(text), 'tom': b}


def dua_vao_hang_cho(draft: dict, out: Path, thu_muc: Path) -> str:
    """Chép chú thích và ảnh vào data/out của Thread Auto rồi thêm bản nháp (approved = false) vào editorial-queue.json.
    Từ chối khi Thread Auto đang giữ khóa thao tác, khi mã bài đã có trong hàng chờ, hoặc khi bản nháp không ở trạng thái chưa duyệt."""
    data = thu_muc / 'data'
    queue_file = data / 'editorial-queue.json'
    if draft.get('approved') is not False:
        raise ValueError('bản nháp phải có approved = false; việc duyệt là của người')
    if (data / 'operation-lock.json').exists():
        raise RuntimeError('Thread Auto đang chạy một thao tác (có operation-lock.json); thử lại sau')
    queue = json.loads(queue_file.read_text(encoding='utf-8'))
    if not isinstance(queue, list):
        raise ValueError('editorial-queue.json không phải một danh sách')
    if any(d.get('id') == draft['id'] for d in queue):
        raise ValueError(f'hàng chờ đã có bài {draft["id"]}')
    for key in ('captionFile', 'imageFile'):
        src = out / Path(draft[key]).name
        shutil.copyfile(src, thu_muc / draft[key])
    shutil.copyfile(queue_file, out / f'editorial-queue.truoc-{draft["id"]}.json')        # bản sao trước khi sửa
    tmp = queue_file.with_suffix('.json.tmp-so-cong-khai')
    tmp.write_text(json.dumps(queue + [draft], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, queue_file)
    return str(queue_file)


def main(argv=None) -> int:
    here = duong.goc_du_lieu()
    ap = argparse.ArgumentParser(prog='so_cong_khai.threads', description=__doc__)
    ap.add_argument('--cau-hinh', default=str(here / 'cau-hinh.json'))
    ap.add_argument('--loai', choices=('ngay', 'tuan'), default='tuan')
    ap.add_argument('--ngay', default=None, help='YYYY-MM-DD theo giờ Việt Nam (mặc định: hôm qua)')
    ap.add_argument('--tuan', default=None, help='mã tuần ISO, ví dụ 2026-W47 (mặc định: tuần hiện tại)')
    ap.add_argument('--dua-vao-hang-cho', action='store_true', help='chép bản nháp CHƯA DUYỆT vào hàng chờ của Thread Auto')
    a = ap.parse_args(argv)
    cfg = json.loads(Path(a.cau_hinh).read_text(encoding='utf-8'))
    now = datetime.now(timezone.utc)
    if a.loai == 'ngay':
        day = datetime.strptime(a.ngay, '%Y-%m-%d').replace(tzinfo=VN) if a.ngay else \
            (now.astimezone(VN) - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        start, end = day, day + timedelta(days=1)
    else:
        start, end = tong_hop.tuan_theo_ma(a.tuan) if a.tuan else tong_hop.tuan_chua(now)
    out = Path(cfg.get('thu_muc_ra', 'out'))
    out = (out if out.is_absolute() else here / out) / 'threads'
    r = tao_ban_nhap(cfg, a.loai, start, end, out, now)
    sys.stdout.reconfigure(encoding='utf-8')
    print(r['text'])
    print(f'\n({r["so_ky_tu"]}/{GIOI_HAN} ký tự) Bản xem trước: {out / (r["draft"]["id"] + ".image.png")}')
    if a.dua_vao_hang_cho:
        q = dua_vao_hang_cho(r['draft'], out, Path(cfg['threads']['thu_muc']))
        print(f'Đã thêm bản nháp CHƯA DUYỆT {r["draft"]["id"]} vào {q}. Thread Auto sẽ không đăng cho tới khi approved = true.')
    else:
        print('Chưa đụng tới Thread Auto. Thêm --dua-vao-hang-cho để đặt bản nháp (chưa duyệt) vào hàng chờ.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
