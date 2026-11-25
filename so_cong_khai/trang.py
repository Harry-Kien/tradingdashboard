"""Dựng trang sổ công khai (một tệp HTML tự chứa, biểu đồ SVG vẽ sẵn) và bài tổng kết tuần dạng chữ."""
from __future__ import annotations

import json
import math
import sys
import threading
import types
from datetime import datetime, timedelta
from html import escape
from pathlib import Path

from .doc_so import VN

BIEU_TUONG = ('<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 32 32%27%3E'
              '%3Crect width=%2732%27 height=%2732%27 rx=%277%27 fill=%27%232f6fed%27/%3E%3Cpath d=%27M7 21l6-7 5 4 7-9%27 fill=%27none%27 stroke=%27%23fff%27 '
              'stroke-width=%273%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27/%3E%3C/svg%3E">')
MIEN_TRU_GOC = 'Đây là số liệu tín hiệu, tài khoản demo và chạy bóng, không phải kết quả tiền thật, lời hứa lợi nhuận hay lời khuyên đầu tư.'
# bản chia sẻ chưa khai sổ riêng (máy không có luật của chủ dự án): câu miễn trừ chung
MIEN_TRU_CHIA_SE = ('Đây là số liệu thị trường và kết quả đo lại trên dữ liệu quá khứ, không phải lời hứa lợi nhuận hay lời khuyên đầu tư. '
                    'Giao dịch CFD và Forex có rủi ro mất vốn cao.')
# Câu miễn trừ chọn RIÊNG cho từng luồng: máy chủ mở một luồng cho mỗi lượt yêu cầu và gọi chia_se_luot() ở đầu lượt, nên lượt này
# không đổi câu của lượt khác hay của bài kiểm chạy sau. `trang.MIEN_TRU` (đọc hoặc gán) vẫn dùng được như trước: xem _Mod ở cuối tệp.
_luong = threading.local()


def chia_se_luot(cs: bool) -> None:
    """Đặt câu miễn trừ cho luồng đang chạy: True là câu của bản chia sẻ, False là câu gốc."""
    _luong.cs = bool(cs)


def mien_tru() -> str:
    return MIEN_TRU_CHIA_SE if getattr(_luong, 'cs', False) else MIEN_TRU_GOC


# ------------------------------------------------------------------ định dạng
def so(x: float, n: int = 2, dau: bool = False) -> str:
    """Số kiểu Việt: dấu phẩy thập phân, dấu chấm ngăn nghìn."""
    s = f'{x:+,.{n}f}' if dau else f'{x:,.{n}f}'
    return s.replace(',', '§').replace('.', ',').replace('§', '.')


def gio(t: datetime | None) -> str:
    return t.astimezone(VN).strftime('%d/%m %H:%M') if t else '—'


def ket_qua_bot(r: dict) -> str:
    if not r['closed']:
        return f'đang mở, đã đạt {r["tps_hit"]}/{r["n_tps"]} TP'
    if r['tps_hit'] == r['n_tps']:
        return f'đạt đủ {r["n_tps"]} TP'
    if r['exit'] == 'SL':
        return f'đạt TP{r["tps_hit"]} rồi chạm SL' if r['tps_hit'] else 'chạm SL'
    if r['exit'] == 'CLOSE':
        return f'đạt TP{r["tps_hit"]} rồi đóng tay' if r['tps_hit'] else 'đóng tay khi chưa có TP'
    return f'đạt {r["tps_hit"]}/{r["n_tps"]} TP, đóng theo thời hạn'


def _ty_le(k: int, n: int) -> str:
    return f'{k}/{n} ({k / n:.0%})' if n else 'chưa có'


def _huong(side: str) -> str:
    return {'BUY': 'MUA', 'SELL': 'BÁN'}.get(side, side)


def _mau(x: float, text: str) -> str:
    return f'<span class="{"gain" if x > 0 else "loss" if x < 0 else ""}">{escape(text)}</span>'


def _giu(h: float | None) -> str:
    if h is None:
        return '—'
    return f'{so(h, 1)} giờ' if h < 48 else f'{so(h / 24, 1)} ngày'


# ------------------------------------------------------------------ bài tổng kết tuần
def bai_tuan(ten: str, start: datetime, d: dict) -> str:
    end = start + timedelta(days=6)
    lines = [f'TỔNG KẾT TUẦN {start.isocalendar()[1]} ({start:%d/%m}–{end:%d/%m/%Y}) · {ten}', '']
    b = d.get('bot')
    if b is not None:
        lines.append(f'Bot tín hiệu vàng (tín hiệu, không phải lệnh thật): gọi {b["n"]} lệnh, đã đóng {b["closed"]}, còn mở {b["open"]}.')
        if b['decided']:
            lines.append(f'  Chạm TP1: {_ty_le(b["tp1"], b["decided"])} · chạm SL khi chưa có TP: {_ty_le(b["sl0"], b["decided"])} · đủ mọi TP: {b["full"]}')
    for acc in d.get('tai_khoan', []):
        e = acc['tom']
        for name, err in acc['loi']:
            lines.append(f'{name}: không đọc được nhật ký ({err}).')
        if e is None:
            continue
        lines.append(f'{acc["ten"]} ({", ".join(p["ten"] for p in e["per_ea"])}, tài khoản DEMO): đóng {e["n"]} lệnh, thắng {e["win"]}, '
                     f'thua {e["loss"]}, tổng {so(e["pnl"], 2, True)} USD demo; đang mở {len(e["opens"])} lệnh.')
        if e['orphans']:
            lines.append(f'  Còn {len(e["orphans"])} lệnh vào không có dòng đóng trong nhật ký, chưa tính vào tổng trên.')
    x = d.get('xu_huong')
    if x is not None:
        lines.append(f'Luật xu hướng ba khung (chạy bóng, không đặt lệnh): {x["n"]} tín hiệu, đã đóng {x["closed"]}, '
                     f'thắng {x["win"]}, thua {x["loss"]}, tổng {so(x["usd"], 2, True)} USD ở 0,01 lot. Sổ có thể sót lệnh lúc máy tắt.')
    k = d.get('dinh_day')
    if k is not None:
        lines.append(f'Luật đỉnh/đáy (chạy bóng, không đặt lệnh): {k["n"]} lệnh giả định, thắng {k["win"]}, thua {k["loss"]}, tổng {so(k["r"], 2, True)}R.')
    for name, err in d.get('loi', []):
        lines.append(f'{name}: không đọc được sổ ({err}).')
    lines += ['', mien_tru()]
    return '\n'.join(lines)


# ------------------------------------------------------------------ biểu đồ SVG
def _buoc_dep(span: float, n: int = 4) -> float:
    raw = span / n if span > 0 else 1
    mag = 10 ** math.floor(math.log10(raw))
    return next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)


def svg_duong(points: list[tuple[datetime, float]], don_vi: str, nhan: str, so_le: int = 2, bac_thang: bool = False) -> str:
    """Biểu đồ đường một chuỗi: lưới mờ, đường 2px, chấm và nhãn ở điểm cuối, lớp rê chuột (crosshair + ô chú thích)."""
    if len(points) < 2:
        return '<p class="small">Chưa đủ điểm để vẽ.</p>'
    W, H, L, R, T, B = 760, 240, 62, 78, 14, 28
    t0, t1 = points[0][0].timestamp(), points[-1][0].timestamp()
    vals = [v for _, v in points]
    step = _buoc_dep(max(vals) - min(vals) or abs(vals[0]) or 1)
    lo, hi = math.floor(min(vals) / step) * step, math.ceil(max(vals) / step) * step
    if hi == lo:
        hi = lo + step
    X = lambda t: L + (t - t0) / ((t1 - t0) or 1) * (W - L - R)
    Y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    k = max(1, len(points) // 500)
    pts = points[::k] + ([points[-1]] if (len(points) - 1) % k else [])
    xy = [(X(t.timestamp()), Y(v)) for t, v in pts]
    if bac_thang:
        d = f'M{xy[0][0]:.1f},{xy[0][1]:.1f}' + ''.join(f'H{x:.1f}V{y:.1f}' for x, y in xy[1:])
    else:
        d = 'M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in xy)
    out = [f'<svg class="line" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(nhan)}" '
           f'data-pts="{escape(json.dumps([[round(x, 1), round(y, 1), gio(t), so(v, so_le) + " " + don_vi] for (x, y), (t, v) in zip(xy, pts)], ensure_ascii=False), quote=True)}">']
    v = lo
    while v <= hi + step / 1000:
        y = Y(v)
        out.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}"/>'
                   f'<text class="ax" x="{L - 8}" y="{y + 4:.1f}" text-anchor="end">{so(v, 0 if step >= 1 else 2)}</text>')
        v += step
    day = points[0][0].astimezone(VN).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    n_days = max(1, int((t1 - t0) // 86400))
    every = max(1, math.ceil(n_days / 7))
    i = 0
    while day.timestamp() < t1:
        if i % every == 0:
            x = X(day.timestamp())
            out.append(f'<line class="tick" x1="{x:.1f}" x2="{x:.1f}" y1="{H - B}" y2="{H - B + 4}"/>'
                       f'<text class="ax" x="{x:.1f}" y="{H - 8}" text-anchor="middle">{day:%d/%m}</text>')
        day += timedelta(days=1)
        i += 1
    ex, ey = xy[-1]
    out.append(f'<path class="area" d="{d}L{ex:.1f},{H - B}L{xy[0][0]:.1f},{H - B}Z"/><path class="ln" d="{d}"/>'
               f'<circle class="end" cx="{ex:.1f}" cy="{ey:.1f}" r="4.5"/>'
               f'<text class="endlab" x="{ex + 9:.1f}" y="{ey + 4:.1f}">{so(vals[-1], so_le)}</text>'
               f'<line class="cross" y1="{T}" y2="{H - B}" style="display:none"/><circle class="hov" r="4.5" style="display:none"/></svg>')
    return '<div class="chart">' + ''.join(out) + '</div>'


def _cot(x: float, w: float, y0: float, y1: float) -> str:
    """Cột bo tròn 4px ở đầu dữ liệu, chân vuông bám đường gốc."""
    r = min(4.0, abs(y1 - y0), w / 2)
    s = -1 if y1 < y0 else 1                 # -1: cột đi lên
    return (f'M{x:.1f},{y0:.1f}V{y1 - s * r:.1f}Q{x:.1f},{y1:.1f} {x + r:.1f},{y1:.1f}H{x + w - r:.1f}'
            f'Q{x + w:.1f},{y1:.1f} {x + w:.1f},{y1 - s * r:.1f}V{y0:.1f}Z')


def svg_cot_ngay(daily: list[tuple]) -> str:
    """Lãi lỗ đã đóng theo ngày: cột hai phía quanh đường 0. Chỉ gắn nhãn cho ngày lãi nhất và ngày lỗ nhất."""
    W, H, L, R, T, B = 760, 180, 62, 16, 18, 26
    vals = [v for _, v in daily]
    hi, lo = max(vals + [0]), min(vals + [0])
    step = _buoc_dep(hi - lo or 1, 3)
    hi, lo = math.ceil(hi / step) * step, math.floor(lo / step) * step
    Y = lambda v: T + (hi - v) / ((hi - lo) or 1) * (H - T - B)
    slot = (W - L - R) / len(daily)
    bw = min(46.0, slot * 0.6)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Lãi lỗ đã đóng theo ngày">']
    v = lo
    while v <= hi + step / 1000:
        out.append(f'<line class="{"zero" if abs(v) < step / 1000 else "grid"}" x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>'
                   f'<text class="ax" x="{L - 8}" y="{Y(v) + 4:.1f}" text-anchor="end">{so(v, 0)}</text>')
        v += step
    best, worst = max(vals), min(vals)
    for i, (day, val) in enumerate(daily):
        x = L + slot * i + (slot - bw) / 2
        tip = escape(f'<b>{so(val, 2, True)} USD demo</b><br>{day:%d/%m/%Y}', quote=True)
        out.append(f'<path class="bar {"gain" if val >= 0 else "loss"}" d="{_cot(x, bw, Y(0), Y(val))}" data-tip="{tip}"/>'
                   f'<text class="ax" x="{x + bw / 2:.1f}" y="{H - 8}" text-anchor="middle">{day:%d/%m}</text>')
        if (val == best and val > 0) or (val == worst and val < 0):
            out.append(f'<text class="val" x="{x + bw / 2:.1f}" y="{Y(val) + (-6 if val > 0 else 14):.1f}" text-anchor="middle">{so(val, 0, True)}</text>')
    return '<div class="chart">' + ''.join(out) + '</svg></div>'


def svg_donut(gp: float, gl: float) -> str:
    """Vành khuyên mảnh lãi gộp / lỗ gộp, tổng ở giữa; hai phần cách nhau một khe nhỏ, chú giải bằng chữ ở hai bên."""
    r, sw = 60, 9
    C = 2 * math.pi * r
    total = gp + abs(gl)
    seg = ''
    if total > 0:
        gap = 4 if gp > 0 and gl < 0 else 0
        a = gp / total * C
        tg = escape(f'<b>Lãi gộp {so(gp, 2, True)} USD</b><br>{gp / total:.0%} tổng lãi và lỗ', quote=True)
        tl = escape(f'<b>Lỗ gộp {so(gl, 2, True)} USD</b><br>{abs(gl) / total:.0%} tổng lãi và lỗ', quote=True)
        if gp > 0:
            seg += f'<circle class="dn gain" r="{r}" stroke-linecap="round" stroke-dasharray="{max(a - gap, 0.1):.1f} {C:.1f}" data-tip="{tg}"/>'
        if gl < 0:
            seg += (f'<circle class="dn loss" r="{r}" stroke-linecap="round" stroke-dasharray="{max(C - a - gap, 0.1):.1f} {C:.1f}" '
                    f'stroke-dashoffset="{-a:.1f}" data-tip="{tl}"/>')
    net = gp + gl
    return (f'<div class="donut"><div class="dleg"><i class="sw gain"></i>Lãi gộp<b>{so(gp, 2, True)}</b></div>'
            f'<svg viewBox="-80 -80 160 160" role="img" aria-label="Lãi gộp và lỗ gộp">'
            f'<circle class="dn track" r="{r}"/><g transform="rotate(-90)" stroke-width="{sw}">{seg}</g>'
            f'<text class="dnv" y="0" text-anchor="middle">{so(net, 2, True) if total else "—"}</text>'
            f'<text class="dnl" y="18" text-anchor="middle">Tổng</text></svg>'
            f'<div class="dleg r"><i class="sw loss"></i>Lỗ gộp<b>{so(gl, 2, True) if gl else "0,00"}</b></div></div>')




def _thuoc(nhan: str, gia_tri: str, ty_le: float | None, ghi_chu: str = '', dau: str = '0', cuoi: str = '', cao_tot: bool = False) -> str:
    """Một thanh đo: nhãn ở trên, thanh nền nhạt, ô giá trị đặt đúng vị trí trên thanh, hai đầu ghi mốc. Không có thang thì chỉ ghi số."""
    if ty_le is None:
        return (f'<div class="gauge"><div class="grow"><span>{escape(nhan)}</span><b>{escape(gia_tri)}</b></div>'
                + (f'<div class="mnote">{escape(ghi_chu)}</div>' if ghi_chu else '') + '</div>')
    x = max(0.0, min(1.0, ty_le)) * 100
    # ô giá trị không được tràn ra ngoài hai đầu thanh
    pos = 'left:0;transform:none' if x < 6 else 'left:auto;right:0;transform:none' if x > 94 else f'left:{x:.1f}%'
    return (f'<div class="gauge"><div class="grow"><span>{escape(nhan)}</span></div>'
            f'<div class="gtrack{" tot" if cao_tot else ""}"><i style="{pos}">{escape(gia_tri)}</i></div>'
            f'<div class="gends"><span>{escape(dau)}</span><span>{escape(cuoi)}</span></div>'
            + (f'<div class="mnote">{escape(ghi_chu)}</div>' if ghi_chu else '') + '</div>')




def _tiles(items: list[tuple[str, str, str]]) -> str:
    """[(nhãn, giá trị dạng HTML đã thoát, dòng phụ)]"""
    return '<div class="tiles">' + ''.join(
        f'<div class="tile"><span>{escape(k)}</span><b>{v}</b>' + (f'<small>{escape(s)}</small>' if s else '') + '</div>'
        for k, v, s in items) + '</div>'


def _table(head: list[str], rows: list[list[str]], right: set[int] = frozenset()) -> str:
    if not rows:
        return '<p class="small">Chưa có dòng nào.</p>'
    th = ''.join(f'<th class="{"r" if i in right else ""}">{escape(h)}</th>' for i, h in enumerate(head))
    body = ''.join('<tr>' + ''.join(f'<td class="{"r" if i in right else ""}">{c}</td>' for i, c in enumerate(row)) + '</tr>' for row in rows)
    return f'<div class="wrap"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def _gap(tieu_de: str, noi_dung: str, mo: bool = False) -> str:
    return f'<details{" open" if mo else ""}><summary>{escape(tieu_de)}</summary>{noi_dung}</details>'


# ------------------------------------------------------------------ từng khối của trang
def _dong_lenh(t: dict) -> str:
    """Một dòng lệnh kiểu sổ giao dịch: mã, hướng, lot, giá vào; bên phải là lãi lỗ và giờ đóng."""
    side = 'buy' if t['side'] == 'BUY' else 'sell'
    return (f'<div class="deal"><div><b>XAUUSD</b> <span class="{side}">{_huong(t["side"]).lower()} {so(t["lots"])}</span>'
            f'<small>{escape(t["ea"])} · vào {so(t["entry"])} · {escape(t["reason"] or "đóng")} · mở {gio(t["opened"])}</small></div>'
            f'<div class="r"><b>{_mau(t["pnl"], so(t["pnl"], 2, True))}</b><small>{gio(t["closed_at"])}</small></div></div>')


def _kv(k: str, v: str) -> str:
    return f'<div class="kvr"><span>{escape(k)}</span><b>{v}</b></div>'


def _doi_chieu_html(dc: dict) -> str:
    """Khối đối chiếu nhật ký của EA với lịch sử khớp lệnh trong MT5 (do tai_khoan.doi_chieu tính)."""
    h = ['<h3>Đối chiếu với lịch sử MT5</h3><div class="kvs">',
         _kv('Nhật ký của EA', f'{dc["n_nhat_ky"]} lệnh · ' + _mau(dc['tong_nhat_ky'], so(dc['tong_nhat_ky'], 2, True))),
         _kv('Lịch sử MT5', f'{dc["n_mt5"]} lệnh · ' + _mau(dc['tong_mt5'], so(dc['tong_mt5'], 2, True))),
         _kv('Số lệnh ghép được giữa hai nguồn', f'{dc["so_cap"]}')]
    if dc['nap_rut']:
        h.append(_kv('Nạp, rút, điều chỉnh trong quãng này', so(dc['nap_rut'], 2, True)))
    if dc['treo']:
        h.append(_kv('Lãi lỗ đang treo (theo MT5)', _mau(dc['treo'], so(dc['treo'], 2, True))))
    h += [_kv('Vốn thay đổi theo nhật ký của EA', so(dc['von_thay_doi'], 2, True)), _kv('Còn lệch sau khi đối chiếu', '0,00' if abs(dc['con_lech']) < 0.005 else so(dc['con_lech'], 2, True)), '</div>']
    if dc['thieu_nhat_ky']:
        h.append('<h3>Lệnh có trong MT5 nhưng nhật ký của EA không ghi dòng đóng</h3>' + _table(
            ['Đóng lúc (VN)', 'Hướng', 'Lot', 'Giá đóng', 'Lãi lỗ ròng'],
            [[gio(datetime.fromisoformat(x['luc'])), 'MUA' if x['huong'] == 'MUA' else 'BÁN', so(x['lot']), so(x['gia']), _mau(x['lai'], so(x['lai'], 2, True))]
             for x in dc['thieu_nhat_ky']], right={2, 3, 4}))
    if dc['thieu_mt5']:
        h.append('<h3>Lệnh có trong nhật ký của EA nhưng không thấy trong lịch sử MT5</h3>' + _table(
            ['Đóng lúc (VN)', 'Hướng', 'Lot', 'Lãi lỗ theo nhật ký'],
            [[gio(datetime.fromisoformat(x['luc'])), 'MUA' if x['huong'] == 'MUA' else 'BÁN', so(x['lot']), _mau(x['lai'], so(x['lai'], 2, True))] for x in dc['thieu_mt5']], right={2, 3}))
    if dc['lech_cap']:
        h.append(f'<p class="note">{len(dc["lech_cap"])} lệnh ghép được nhưng lãi lỗ hai nguồn lệch nhau quá 0,05 USD (thường do phí hoặc phí qua đêm mà nhật ký của EA không tính).</p>')
    if dc['khop']:
        h.append(f'<p class="note"><b>Đã khớp.</b> Vốn thay đổi {so(dc["von_thay_doi"], 2, True)} USD bằng tổng lãi lỗ {dc["n_mt5"]} lệnh trong lịch sử MT5'
                 + (', cộng nạp rút và lãi lỗ đang treo' if dc['nap_rut'] or dc['treo'] else '') + '. '
                 + (f'Nhật ký của EA thiếu dòng đóng của {len(dc["thieu_nhat_ky"])} lệnh; các chỉ số ở trang này tính theo nhật ký của EA nên chưa gồm lệnh đó.'
                    if dc['thieu_nhat_ky'] else 'Hai nguồn ghi cùng số lệnh.') + '</p>')
    else:
        h.append(f'<p class="note"><b>Còn lệch {so(dc["con_lech"], 2, True)} USD</b> mà cả nhật ký của EA lẫn lịch sử MT5 chưa giải thích được.</p>')
    return ''.join(h)


def _khoi_tai_khoan(acc: dict) -> str:
    e = acc['tom']
    out = [f'<section class="card" id="{escape(acc["id"])}"><h2>{escape(acc["ten"])} <span class="tag">DEMO</span></h2>']
    for name, err in acc['loi']:
        out.append(f'<p class="note">Không đọc được nhật ký của {escape(name)}: {escape(err)}.</p>')
    if e is None:
        return ''.join(out) + '</section>'
    names = ', '.join(p['ten'] + (f' {p["version"]}' if p['version'] else '') for p in e['per_ea'])
    out.append(f'<p class="sub">{escape(names)} · EA tự đặt lệnh trên tài khoản demo. Tiền demo, không phải tiền thật. Nhật ký đọc tới {gio(e["last_time"])} (giờ Việt Nam).</p>')
    out.append('<div class="tabs" role="tablist">' + ''.join(
        f'<button type="button" role="tab" aria-selected="{"true" if i == 0 else "false"}">{n}</button>'
        for i, n in enumerate(('Tổng quan', 'Lãi &amp; lỗ', 'Rủi ro', f'Lệnh ({e["n"]})'))) + '</div>')

    # --- Tổng quan
    pct = f' ({e["equity_change"] / e["first_equity"]:+.1%})'.replace('.', ',') if e['first_equity'] else ''
    pf0 = e['profit_factor']
    ben = ('<div class="accs rows"><div class="big"><span>Vốn demo hiện tại (USD)</span>'
           f'<b>{so(e["last_equity"])}</b><small>{_mau(e["equity_change"], so(e["equity_change"], 2, True) + pct)} từ đầu sổ {so(e["first_equity"])}</small></div>'
           + _kv('Lãi lỗ đã đóng (USD demo)', _mau(e['pnl'], so(e['pnl'], 2, True)))
           + _kv('Lệnh đã đóng', f'{e["n"]} · thắng {e["win"]}, thua {e["loss"]}')
           + (_kv('Theo lịch sử MT5', f'{acc["doi_chieu"]["n_mt5"]} lệnh · ' + _mau(acc['doi_chieu']['tong_mt5'], so(acc['doi_chieu']['tong_mt5'], 2, True)))
              if acc.get('doi_chieu') else '')
           + _kv('Tỷ lệ thắng', f'{e["win"] / e["n"]:.0%}' if e['n'] else '—')
           + _kv('Hệ số lợi nhuận', so(pf0) if pf0 is not None else '—')
           + _kv('Đang mở', f'{len(e["opens"])} lệnh' + (' · lãi lỗ đang treo' if e['opens'] else ''))
           + _kv('Sụt vốn lớn nhất', f'{e["max_dd_pct"]:.1%}'.replace('.', ',') + f' · {so(e["max_dd"])} USD') + '</div>')
    hinh = svg_duong(e['curve'], 'USD', 'Đường vốn demo của ' + acc['ten'])
    tq = [f'<div class="acc"><div><h3>Đường vốn demo (USD)</h3>{hinh}</div>{ben}</div>']
    if e['curve_from'] is not None:
        dep = e['deposits'][-1]
        txt = (f'Đường vốn và các chỉ số rủi ro tính từ lần nạp/rút tiền demo gần nhất ({so(dep[1], 2, True)} USD lúc {gio(dep[0])}), '
               'vì nạp/rút làm vốn nhảy mà không phải do lệnh.')
        if e['before']:
            b = e['before']
            txt += (f' Trước mốc đó, từ {gio(b["from"])}, vốn demo dao động trong khoảng {so(b["min"])}–{so(b["max"])} USD; '
                    'quãng này không nằm trong biểu đồ và chỉ số.')
        tq.append(f'<p class="note">{escape(txt)}</p>')
    if e['n'] < 30:
        tq.append(f'<p class="note"><b>Mới có {e["n"]} lệnh đã đóng.</b> Dưới 30 lệnh thì các chỉ số chưa nói được EA có lợi thế hay không, '
                  'nhất là khi giá vừa chạy một chiều.</p>')

    # --- Lãi & lỗ
    tron = '<h3>Lãi gộp và lỗ gộp (USD demo)</h3>' + svg_donut(e['gross_profit'], e['gross_loss'])
    ll = []
    bang = ('<div class="kvs">' + _kv('Vốn đầu sổ', so(e['first_equity'])) + _kv('Lãi gộp', _mau(e['gross_profit'], so(e['gross_profit'], 2, True)))
              + _kv('Lỗ gộp', _mau(e['gross_loss'], so(e['gross_loss'], 2, True) if e['gross_loss'] else '0,00'))
              + _kv('Lãi lỗ đã đóng', _mau(e['pnl'], so(e['pnl'], 2, True)))
              + _kv('Chưa chốt hoặc chưa đối chiếu', so(e['unexplained'], 2, True)) + _kv('Vốn hiện tại', so(e['last_equity'])) + '</div>')
    if len(e['daily']) >= 2:
        ll.append(f'<div class="acc"><div><h3>Lãi lỗ đã đóng theo ngày (USD demo)</h3>{svg_cot_ngay(e["daily"])}</div><div>{tron}{bang}</div></div>')
    else:
        ll.append(tron + bang)
    if e['orphans']:
        ds = '; '.join(f'{o["ea"]} {_huong(o["side"])} {so(o["lots"])} lot lúc {gio(o["opened"])}, giá vào {so(o["entry"])}, TP {so(o["tp"])}' for o in e['orphans'])
        ll.append(f'<p class="note"><b>{len(e["orphans"])} lệnh vào không có dòng đóng trong nhật ký</b> ({escape(ds)}). '
                  'Nhật ký của EA không ghi lệnh này đóng thế nào, nên lãi lỗ của nó không nằm trong bảng và các chỉ số ở đây.</p>')
    if acc.get('doi_chieu'):
        ll.append(_doi_chieu_html(acc['doi_chieu']))
    elif abs(e['unexplained']) > 0.5:
        why = []
        if e['opens']:
            why.append(f'lãi lỗ đang treo của {len(e["opens"])} lệnh còn mở (chưa chốt, còn thay đổi)')
        if e['orphans']:
            why.append('lệnh không có dòng đóng')
        if e['deposits']:
            why.append('nạp hoặc rút tiền demo')
        ll.append(f'<p class="note">Vốn demo thay đổi {so(e["equity_change"], 2, True)} USD nhưng tổng lãi lỗ các lệnh đã đóng là {so(e["pnl_all"], 2, True)} USD. '
                  f'Phần chênh {so(e["unexplained"], 2, True)} USD đến từ: {escape("; ".join(why) or "nguồn mà nhật ký không ghi")}. Trang này chưa tách được từng phần.</p>')

    # --- Rủi ro
    pf, rec = e['profit_factor'], e['recovery']
    rr = [_thuoc('Hệ số lợi nhuận (lãi gộp ÷ lỗ gộp)', so(pf) if pf is not None else 'chưa tính được', pf / 4 if pf is not None else None,
                 '' if pf is not None else ('Chưa có lệnh thua nào đã đóng.' if e['n'] else 'Chưa có lệnh nào đã đóng.'), '0', '4', True),
          _thuoc('Hệ số hồi phục (lãi ròng ÷ sụt vốn lớn nhất)', so(rec) if rec is not None else 'chưa tính được', rec / 7 if rec is not None else None, '', '0', '7', True),
          _thuoc('Sụt vốn lớn nhất so với đỉnh', f'{e["max_dd_pct"]:.1%}'.replace('.', ','), e['max_dd_pct'], '', '0%', '100%'),
          _thuoc('Tỷ lệ thắng', _ty_le(e['win'], e['n']), e['win'] / e['n'] if e['n'] else None, '', '0%', '100%', True),
          _thuoc('Số lệnh đã đóng mỗi tuần', so(e['per_week'], 1), None),
          _thuoc('Thời gian giữ lệnh trung bình', _giu(e['avg_hold_h']), None),
          _thuoc('Lệnh mua / lệnh bán đã đóng', f'{e["buy"][0]} ({so(e["buy"][1], 2, True)}) / {e["sell"][0]} ({so(e["sell"][1], 2, True)})', None),
          _thuoc('Lệnh lãi nhất / lỗ nhất', (f'{so(e["best"], 2, True)} / {so(e["worst"], 2, True)}' if e['n'] else '—'), None)]

    # --- Lệnh
    ln = []
    if e['opens']:
        ln.append('<h3>Lệnh đang mở</h3>' + _table(['EA', 'Mở (VN)', 'Hướng', 'Lot', 'Giá vào', 'SL', 'TP'],
                                                   [[escape(o['ea']), gio(o['opened']), _huong(o['side']), so(o['lots']), so(o['entry']), so(o['sl']) if o['sl'] else '—',
                                                     so(o['tp']) if o['tp'] else '—'] for o in e['opens']], right={3, 4, 5, 6}))
    if len(e['per_ea']) > 1:
        ln.append('<h3>Từng EA</h3>' + _table(['EA', 'Lệnh đã vào', 'Đã đóng', 'Đang mở', 'Lãi lỗ đã đóng (USD demo)'],
                                              [[escape(p['ten']), str(p['entries']), str(p['closed']), str(p['open']), _mau(p['pnl'], so(p['pnl'], 2, True))]
                                               for p in e['per_ea']], right={1, 2, 3, 4}))
    ln.append(f'<h3>Danh sách {e["n"]} lệnh đã đóng</h3>' + ('<div class="deals">' + ''.join(_dong_lenh(t) for t in reversed(e['rows'])) + '</div>'
                                                               if e['rows'] else '<p class="small">Chưa có lệnh nào đã đóng.</p>'))
    rr = ['<div class="gauges">' + ''.join(rr) + '</div>']
    for i, pane in enumerate((tq, ll, rr, ln)):
        out.append(f'<div class="pane" role="tabpanel"{"" if i == 0 else " hidden"}>' + ''.join(pane) + '</div>')
    return ''.join(out) + '</section>'




def _khoi_bot(b: dict) -> str:
    out = ['<section class="card" id="bot"><h2>Bot tín hiệu vàng trên Telegram <span class="tag">TÍN HIỆU</span></h2>'
           '<p class="sub">Bot tự gọi lệnh XAUUSD và tự báo từng TP, SL. Bot không đặt lệnh. Mọi lệnh đã lên kênh đều ở đây, kể cả lệnh chạm SL.</p>']
    out.append(_tiles([('Lệnh đã gọi', str(b['n']), f'đã đóng {b["closed"]}, còn mở {b["open"]}'),
                       ('Chạm TP1', _ty_le(b['tp1'], b['decided']), 'trên lệnh đã ngã ngũ'),
                       ('Chạm SL khi chưa có TP nào', _ty_le(b['sl0'], b['decided']), 'trên lệnh đã ngã ngũ'),
                       ('Đạt đủ mọi TP', str(b['full']), '')]))
    trai = []
    if b['levels'] and b['n']:
        tong = b['n']
        rows = ''
        for i, n in enumerate(b['levels']):
            tip = escape(f'<b>TP{i + 1}: {n}/{tong} lệnh</b><br>{n / tong:.0%} số lệnh đã gọi', quote=True)
            rows += (f'<div class="frow" data-tip="{tip}"><span>TP{i + 1}</span><div class="track"><div class="fill" style="width:{n / tong * 100:.1f}%"></div></div>'
                     f'<b>{n}/{tong}</b></div>')
        trai.append(f'<h3>Số lệnh tới từng mức chốt lời</h3><div class="funnel">{rows}</div>')
    if not b['enough']:
        trai.append(f'<p class="note"><b>Mới có {b["closed"]} lệnh đã đóng.</b> Dưới 30 lệnh thì chưa đủ để nhận xét luật tốt hay xấu.</p>')
    out.append('<div class="duo"><div>' + ''.join(trai) + '</div><div>' + _gap(f'Danh sách {b["n"]} lệnh đã gọi', _table(
        ['#', 'Giờ gọi (VN)', 'Hướng', 'Entry', 'SL', 'Kết quả'],
        [[str(r['call']), gio(r['opened']), _huong(r['side']), so(r['entry'], 0), so(r['sl'], 0), escape(ket_qua_bot(r))] for r in reversed(b['rows'])],
        right={3, 4}), mo=True) + '</div></div>')
    return ''.join(out) + '</section>'


def _khoi_bong(x: dict | None, k: dict | None) -> str:
    out = []
    if x is not None:
        out.append('<section class="card" id="xu-huong"><h2>Luật xu hướng ba khung <span class="tag">CHẠY BÓNG</span></h2>'
                   '<p class="sub">Luật máy ghi tín hiệu và tự chấm bằng giá thật: chốt 5 USD, dừng 20 USD ở 0,01 lot. Không đặt lệnh. Cần thắng trên 80% số lệnh mới hòa vốn.</p>')
        out.append(_tiles([('Tín hiệu đã ghi', str(x['n']), f'đã đóng {x["closed"]}'), ('Thắng / thua theo sổ', f'{x["win"]} / {x["loss"]}', _ty_le(x['win'], x['closed'])),
                           ('Tổng (USD ở 0,01 lot)', _mau(x['usd'], so(x['usd'], 2, True)), 'chưa tính trượt giá'),
                           ('Liên kết chuỗi của sổ', 'liền mạch' if x['chain_ok'] else 'CÓ CHỖ ĐỨT', f'{x["n_lines"]} dòng')]))
        out.append('<div class="duo ng"><div>')
        if len(x['curve']) >= 2:
            out.append('<h3>Tổng cộng dồn theo sổ (USD ở 0,01 lot)</h3>' + svg_duong(x['curve'], 'USD', 'Tổng cộng dồn của luật ba khung', bac_thang=True))
        out.append('<p class="note"><b>Sổ này chỉ ghi lúc máy tính bật</b> nên có thể sót lệnh, kể cả lệnh thua. Tỷ lệ thắng thật thấp hơn con số của sổ; '
                   'chưa đủ 300 tín hiệu thì chưa kết luận gì.</p>')
        out.append('</div><div>' + _gap(f'Danh sách {x["n"]} tín hiệu', _table(
            ['#', 'Nến đóng (VN)', 'Hướng', 'Giá vào', 'Kết quả', 'USD'],
            [[str(r['stt']), gio(r['opened']), _huong(r['side']), so(r['entry']),
              {'tp': 'chạm chốt lời', 'sl': 'chạm dừng lỗ', None: 'đang mở'}.get(r['result'], escape(str(r['result']))),
              _mau(r['usd'], so(r['usd'], 2, True)) if r['usd'] is not None else '—'] for r in reversed(x['rows'])], right={3, 5}), mo=True) + '</div></div></section>')
    if k is not None:
        out.append('<section class="card" id="dinh-day"><h2>Luật đỉnh/đáy <span class="tag">CHẠY BÓNG</span></h2>'
                   '<p class="sub">Luật máy bán ở đỉnh 8 giờ, mua ở đáy 8 giờ; chấm như lệnh giả định, tính theo R. Không đặt lệnh.</p>')
        out.append(_tiles([('Lệnh giả định đã đóng', str(k['n']), f'trên {k["n_candles"]} nến đã xét'), ('Thắng / thua', f'{k["win"]} / {k["loss"]}', ''),
                           ('Tổng R', _mau(k['r'], so(k['r'], 2, True)), 'vài lệnh là quá ít để nhận xét'),
                           ('Liên kết chuỗi của sổ', 'liền mạch' if k['chain_ok'] else 'CÓ CHỖ ĐỨT', f'{k["n_lines"]} dòng')]))
        out.append(_gap(f'Danh sách {k["n"]} lệnh giả định', _table(
            ['Khớp (VN)', 'Đóng (VN)', 'Hướng', 'Giá khớp', 'Kết quả', 'R'],
            [[gio(r['opened']), gio(r['closed_at']), _huong(r['side']), so(r['entry']) if r['entry'] else '—', escape(str(r['result'])),
              _mau(r['r'], so(r['r'], 2, True))] for r in reversed(k['rows'])], right={3, 5}), mo=True) + '</section>')
    return ''.join(out)


def _tia(points: list, w: int = 160, h: int = 40) -> str:
    """Đường vốn thu nhỏ cho thẻ tóm tắt: không trục, không nhãn, trục ngang theo thời gian."""
    pts = [(t.timestamp(), float(v)) for t, v in points]
    if len(pts) < 2:
        return ''
    if len(pts) > 160:
        k = len(pts) / 160
        pts = [pts[int(i * k)] for i in range(160)] + [pts[-1]]
    t0, t1 = pts[0][0], pts[-1][0]
    lo, hi = min(v for _, v in pts), max(v for _, v in pts)
    dx, dy = (t1 - t0) or 1.0, (hi - lo) or 1.0
    line = ' '.join(f'{(t - t0) / dx * w:.1f},{h - 3 - (v - lo) / dy * (h - 6):.1f}' for t, v in pts)
    return (f'<svg class="tia {"gain" if pts[-1][1] >= pts[0][1] else "loss"}" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true">'
            f'<polyline points="{line}"/></svg>')


def _thanh(ty_le: float, moc: float | None = None, nhan_moc: str = '') -> str:
    """Thanh tỷ lệ cho thẻ tóm tắt; `moc` là một vạch so sánh (ví dụ mức hòa vốn)."""
    vach = f'<u style="left:{moc * 100:.1f}%" title="{escape(nhan_moc)}"></u>' if moc is not None else ''
    return f'<div class="hbar"><span style="width:{max(0.0, min(1.0, ty_le)) * 100:.1f}%"></span>{vach}</div>'


CSS = """
:root{color-scheme:light;--bg:#f5f6f8;--card:#ffffff;--ink:#1b1f24;--ink2:#5d6673;--mute:#6f7887;--line:#e6e9ee;--gridc:#eef0f3;
--gold:#2e7d0e;--series:#2e7d0e;--gain:#17935b;--loss:#e5532d;--warn:#7a5a00;--warnbg:#fff8e1;--warnline:#f3e3a6;--track:#eef0f3;--meter:#1b1f24;--accent2:#0e9f6e;--btn-ink:#ffffff;--head:#12161b;--card2:#f5f6f8}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#090a08;--card:#111310;--ink:#e3e6dd;--ink2:#cdd1c6;--mute:#8d9286;--line:#23261f;--gridc:#1a1d17;
--gold:#8dff08;--series:#8dff08;--gain:#5fe36a;--loss:#ff6b63;--warn:#f2d94e;--warnbg:#1f1b08;--warnline:#4a3204;--track:#1d1f1b;--meter:#cdd1c6;--accent2:#08ffb5;--btn-ink:#0a0c06;--head:#f4f6f0;--card2:#181a16}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#090a08;--card:#111310;--ink:#e3e6dd;--ink2:#cdd1c6;--mute:#8d9286;--line:#23261f;--gridc:#1a1d17;
--gold:#8dff08;--series:#8dff08;--gain:#5fe36a;--loss:#ff6b63;--warn:#f2d94e;--warnbg:#1f1b08;--warnline:#4a3204;--track:#1d1f1b;--meter:#cdd1c6;--accent2:#08ffb5;--btn-ink:#0a0c06;--head:#f4f6f0;--card2:#181a16}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 "Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;-webkit-font-smoothing:antialiased}
main{max-width:1080px;margin:0 auto;padding:28px 16px 64px}
.top{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;border-bottom:2px solid var(--ink);padding-bottom:12px}
h1{font:600 34px/1.1 "Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;margin:0;letter-spacing:-.01em}
.brand{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);font-weight:700;margin:0 0 6px}
.stamp{color:var(--ink2);font-size:13px;text-align:right}
h2{font:600 22px/1.25 "Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;margin:0 0 4px}
h3{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink2);margin:26px 0 8px;font-weight:700}
.sub{color:var(--ink2);margin:0 0 14px;font-size:14px}.small{color:var(--mute);font-size:13px;margin:8px 0}
.note{background:var(--warnbg);color:var(--warn);border:1px solid var(--warnline);border-radius:8px;padding:10px 14px;margin:12px 0;font-size:14px}
.tag{display:inline-block;font:700 11px/1 system-ui,sans-serif;letter-spacing:.08em;border:1px solid var(--gold);color:var(--gold);border-radius:999px;padding:4px 9px;vertical-align:middle;margin-left:6px}
.hero{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px;margin:18px 0 6px}
.hero a{display:block;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;color:inherit;text-decoration:none}
.hero a:hover,.hero a:focus-visible{border-color:var(--gold);outline:none}
.hero .tag{margin:0}.hero h4{margin:10px 0 2px;font-size:14px;font-weight:600;color:var(--ink2)}
.hero b{display:block;font:600 30px/1.15 "Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;font-variant-numeric:tabular-nums}
.hero small{display:block;color:var(--ink2);font-size:13px}.hero em{display:block;font-style:normal;color:var(--mute);font-size:12.5px;margin-top:8px;border-top:1px solid var(--line);padding-top:8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px 22px 18px;margin-top:22px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.tile{background:var(--card);padding:12px 14px}.tile>span{display:block;color:var(--ink2);font-size:12.5px}
.tile b{display:block;font:600 24px/1.25 "Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;font-variant-numeric:tabular-nums}.tile small{display:block;color:var(--mute);font-size:12.5px}
.gain{color:var(--gain)}.loss{color:var(--loss)}
.grid2{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.25fr);gap:8px 32px}@media(max-width:760px){.grid2{grid-template-columns:1fr}}
.chart svg{display:block;width:100%;height:auto;overflow:visible}
svg text{font:11.5px system-ui,"Segoe UI",Arial,sans-serif;fill:var(--mute)}
.grid{stroke:var(--gridc);stroke-width:1}.zero{stroke:var(--mute);stroke-width:1}.tick{stroke:var(--mute)}
.ln{fill:none;stroke:var(--series);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}.area{fill:var(--series);opacity:.08}
.end,.hov{fill:var(--series);stroke:var(--card);stroke-width:2}.cross{stroke:var(--mute);stroke-width:1;stroke-dasharray:3 3}
svg text.endlab,svg text.val{fill:var(--ink);font-weight:600;font-size:12px}
.bar.gain,.sw.gain{fill:var(--gain);background:var(--gain)}.bar.loss,.sw.loss{fill:var(--loss);background:var(--loss)}.bar:hover,.dn:hover{opacity:.82}
.donut{display:flex;align-items:center;gap:22px;flex-wrap:wrap}.donut svg{width:176px;height:176px;flex:none}
.dn{fill:none}.dn.track{stroke:var(--track);stroke-width:15}.dn.gain{stroke:var(--gain)}.dn.loss{stroke:var(--loss)}
svg text.dnv{font:600 17px "Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;fill:var(--ink)}svg text.dnl{font-size:10.5px}
.legend{list-style:none;margin:0;padding:0;font-size:14px;color:var(--ink2)}.legend li{display:flex;align-items:center;gap:8px;margin:6px 0}
.legend b{margin-left:14px;color:var(--ink);font-variant-numeric:tabular-nums}.sw{width:11px;height:11px;border-radius:3px;display:inline-block}
.meter{padding:7px 0;border-bottom:1px solid var(--line)}.meter:last-child{border-bottom:0}
.mrow{display:flex;justify-content:space-between;gap:12px;font-size:14px;color:var(--ink2)}.mrow b{color:var(--ink);font-variant-numeric:tabular-nums;white-space:nowrap}
.track{height:6px;background:var(--track);border-radius:3px;margin-top:6px;overflow:hidden}.fill{height:100%;background:var(--meter);border-radius:3px}
.mnote{font-size:12.5px;color:var(--mute);margin-top:3px}
.funnel{display:grid;gap:7px;max-width:640px}.frow{display:grid;grid-template-columns:38px 1fr 58px;align-items:center;gap:10px;font-size:14px;color:var(--ink2)}
.frow .track{margin:0;height:14px;border-radius:4px}.frow .fill{background:var(--series);border-radius:0 4px 4px 0}.frow b{color:var(--ink);text-align:right;font-variant-numeric:tabular-nums}
details{margin-top:18px}summary{cursor:pointer;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink2);font-weight:700;padding:6px 0}
.wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin-top:6px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:14px}
th,td{padding:8px 12px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
th{font-size:12px;color:var(--ink2);font-weight:600;background:var(--bg)}tr:last-child td{border-bottom:0}td.r,th.r{text-align:right}
.tip{position:fixed;display:none;pointer-events:none;z-index:9;background:var(--ink);color:var(--card);font-size:12.5px;line-height:1.4;padding:7px 10px;border-radius:7px;max-width:280px;box-shadow:0 4px 14px rgba(0,0,0,.18)}
footer{margin-top:36px;color:var(--mute);font-size:13px;border-top:1px solid var(--line);padding-top:14px}
@media print{.tip{display:none!important}.card{break-inside:avoid}}
"""

JS = """
(()=>{const tip=document.createElement('div');tip.className='tip';document.body.appendChild(tip);
const show=(e,h)=>{tip.innerHTML=h;tip.style.display='block';const r=tip.getBoundingClientRect();let x=e.clientX+14,y=e.clientY+14;
if(x+r.width>innerWidth-8)x=e.clientX-r.width-14;if(y+r.height>innerHeight-8)y=e.clientY-r.height-14;tip.style.left=x+'px';tip.style.top=y+'px'};
const hide=()=>{tip.style.display='none'};
document.querySelectorAll('[data-tip]').forEach(el=>{el.addEventListener('mousemove',e=>show(e,el.dataset.tip));el.addEventListener('mouseleave',hide)});
document.querySelectorAll('svg.line').forEach(svg=>{const pts=JSON.parse(svg.dataset.pts),cross=svg.querySelector('.cross'),dot=svg.querySelector('.hov');
svg.addEventListener('mousemove',e=>{const b=svg.getBoundingClientRect(),x=(e.clientX-b.left)/b.width*svg.viewBox.baseVal.width;let best=pts[0];
for(const p of pts)if(Math.abs(p[0]-x)<Math.abs(best[0]-x))best=p;cross.setAttribute('x1',best[0]);cross.setAttribute('x2',best[0]);cross.style.display='';
dot.setAttribute('cx',best[0]);dot.setAttribute('cy',best[1]);dot.style.display='';show(e,'<b>'+best[3]+'</b><br>'+best[2])});
svg.addEventListener('mouseleave',()=>{cross.style.display='none';dot.style.display='none';hide()})})})();
"""


CSS += """
.bar{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line)}
.bar>div{max-width:1080px;margin:0 auto;padding:9px 16px;display:flex;align-items:center;gap:6px 18px;flex-wrap:wrap}
.bar strong{font:700 12px/1 system-ui,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);margin-right:auto}
.bar a{color:var(--ink2);text-decoration:none;font-size:13.5px;padding:4px 0}.bar a:hover,.bar a:focus-visible{color:var(--ink);outline:none;text-decoration:underline}
.bar button,.copy{font:600 12.5px system-ui,sans-serif;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 10px;cursor:pointer}
.bar button:hover,.copy:hover,.bar button:focus-visible,.copy:focus-visible{border-color:var(--gold);outline:none}
section[id],nav[id]{scroll-margin-top:64px}
.fresh{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden;margin:6px 0 0}
.fresh div{background:var(--card);padding:9px 14px;font-size:12.5px;color:var(--mute)}.fresh b{display:block;color:var(--ink2);font-weight:600;font-size:13px}
pre.bai{white-space:pre-wrap;word-break:break-word;font:14px/1.55 system-ui,"Segoe UI",Arial,sans-serif;background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:8px 0;color:var(--ink)}
.drafts{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:18px;margin-top:8px}
.draft img{width:100%;border:1px solid var(--line);border-radius:10px;display:block}.draft pre.bai{font-size:13px}
.state{display:inline-block;font:700 11px/1 system-ui,sans-serif;letter-spacing:.06em;color:var(--warn);background:var(--warnbg);border:1px solid var(--warnline);border-radius:999px;padding:4px 9px;margin:8px 0 0}
@media(max-width:640px){.bar>div{flex-wrap:nowrap;overflow-x:auto;white-space:nowrap;scrollbar-width:none}.bar strong{display:none}
.bar button{flex:none}.stamp{text-align:left}h1{font-size:28px}.card{padding:18px 14px 14px}}
"""

CSS += """
/* Kiểu dáng 24/11/2026: nền tối, điểm nhấn xanh chanh chuyển xanh ngọc, bo góc lớn. Màu lấy từ các biến ở đầu tệp nên nền sáng vẫn dùng được. */
h1,h2,h3{color:var(--head);font-weight:600;letter-spacing:-.01em}
.top{border-bottom:1px solid var(--line)}
.panel,.card{border-radius:14px}
.tile,.note,.deals,.hero a{border-radius:12px}
.act,.btnl{background:linear-gradient(324deg,var(--accent2) 0%,var(--series) 42%)!important;color:var(--btn-ink)!important;border-color:transparent!important;font-weight:600;border-radius:10px}
.act:hover,.btnl:hover{filter:brightness(1.07)}
.ghost,select,#theme,.copy,.bar button{border-radius:10px}
a{text-underline-offset:3px}
:focus-visible{outline:2px solid var(--series);outline-offset:2px}
::selection{background:color-mix(in srgb,var(--series) 32%,transparent)}
*{scrollbar-width:thin;scrollbar-color:var(--line) transparent}
:root[data-theme="dark"] .panel,:root[data-theme="dark"] .card{background-image:linear-gradient(rgba(255,255,255,.035),rgba(255,255,255,.012));border:1px solid var(--line)}
:root[data-theme="dark"] .bar{background:rgba(9,10,8,.84);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
:root[data-theme="dark"] .subnav{background:rgba(17,19,16,.9)}
:root[data-theme="dark"] .bar strong{background:linear-gradient(324deg,var(--accent2) 0%,var(--series) 60%);-webkit-background-clip:text;background-clip:text;color:transparent}
:root[data-theme="dark"] .seg button[aria-pressed=true],:root[data-theme="dark"] .seg button[aria-selected=true]{background:color-mix(in srgb,var(--series) 15%,transparent);color:var(--series);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--series) 45%,transparent)}
:root[data-theme="dark"] body{background-image:radial-gradient(900px 300px at 50% -140px,rgba(141,255,8,.075),transparent 70%);background-repeat:no-repeat}
:root[data-theme="dark"] .act,:root[data-theme="dark"] .btnl{box-shadow:0 0 0 1px rgba(141,255,8,.25),0 6px 22px -8px rgba(141,255,8,.45)}
:root[data-theme="dark"] .hl,:root[data-theme="dark"] .chip{border-radius:999px}
:root[data-theme="dark"] .hl.ok{background:color-mix(in srgb,var(--series) 14%,transparent);color:var(--series);border-color:color-mix(in srgb,var(--series) 40%,transparent)}
:root[data-theme="dark"] .note{background:var(--card2);border:1px solid var(--line)}
:root[data-theme="dark"] .tile,:root[data-theme="dark"] .pa,:root[data-theme="dark"] .pl{background:var(--card2);border-color:var(--line)}
:root[data-theme="dark"] .gain{color:var(--gain)}:root[data-theme="dark"] .loss{color:var(--loss)}
:root[data-theme="dark"] select,:root[data-theme="dark"] input,:root[data-theme="dark"] textarea{background:var(--card2);color:var(--ink);border-color:var(--line)}
"""

CSS += """
/* Tinh chỉnh 24/11/2026 (lượt hai). Mỗi luật có tiền tố :root để thắng các luật riêng của từng trang nạp sau tệp này.
   Hệ chữ: 13,5 px cho thân bài, 12 px cho chú thích, 16 px cho tiêu đề mục, 26 px cho tên trang; mọi con số dùng chữ số cùng bề ngang để thẳng cột.
   Mật độ: lưới 4 px; nút, ô chọn và ô nhập cùng cao 34 px, bo 10 px; thẻ bo 14 px, đệm 16 px. */
:root body{font-size:13.5px;line-height:1.5;font-variant-numeric:tabular-nums;text-rendering:optimizeLegibility}
:root h1{font-size:26px;line-height:1.15;letter-spacing:-.02em}
:root h2{font-size:16px;line-height:1.3;letter-spacing:-.01em}
:root h3{font-size:13.5px;line-height:1.35}
:root b,:root strong{font-weight:600}
:root .top{align-items:center;padding-bottom:10px}
:root .top .stamp{font-size:12px;line-height:1.5;color:var(--mute)}
:root .note{font-size:12.5px;line-height:1.5;color:var(--ink2);padding:9px 12px 9px 13px;border-left:3px solid var(--warn);border-radius:10px}
:root .panel{padding:14px 16px}
:root .tools{gap:8px;margin-bottom:12px}
:root .seg{border-radius:10px;box-shadow:none}
:root .seg button{min-height:34px;font-size:12.5px;padding:0 12px}
:root .seg.zo button{width:36px;padding:0}
:root .act,:root .ghost{min-height:36px;font-size:12.5px}
:root select{min-height:36px;font-size:12.5px}
:root .chip{min-height:30px}
:root .pa,:root .pl{border-radius:12px}
:root .pa .hd b{font-size:14px}
:root .why{line-height:1.55}
:root th{font-weight:500;color:var(--mute);font-size:12px}
:root tbody tr{transition:background-color .12s}
:root tbody tr:hover{background:color-mix(in srgb,var(--ink) 4%,transparent)}
:root button,:root select,:root summary,:root a{transition:background-color .12s,border-color .12s,color .12s,filter .12s,box-shadow .12s}
:root .ghost:hover,:root select:hover,:root #theme:hover{border-color:color-mix(in srgb,var(--ink) 30%,var(--line))}
:root .bar a.pri{font-weight:500}
:root .bar a.pri[aria-current=page]{font-weight:600}
@media(prefers-reduced-motion:reduce){:root *{transition:none!important;scroll-behavior:auto!important}}
@media(max-width:640px){
:root main{padding:14px 12px 56px}
:root h1{font-size:22px}
:root .note{font-size:12px;padding:8px 10px 8px 11px}
:root .panel{padding:12px}
:root .bar>div{-webkit-mask-image:linear-gradient(90deg,#000 84%,transparent);mask-image:linear-gradient(90deg,#000 84%,transparent);scrollbar-width:none}
:root .tools .sel{flex:1 1 0;min-width:0}
:root .tools .sel select{width:100%}
:root .tools .grow{display:none}
:root .tools .seg.zo,:root .tools #fs-btn{order:1}
:root .tools #fs-btn{font-size:0;gap:0;width:40px;padding:0;justify-content:center}
:root .tools .seg.tf{order:2;flex:1 1 100%}
:root .tools .seg.tf button{flex:1;padding:0}
:root .tools #pt-btn{order:3;flex:1 1 100%;justify-content:center;min-height:44px;font-size:14px}
:root .tools .seg.kieu{flex:1 1 100%}
:root .tools .seg.kieu button{flex:1;padding:0 6px}
:root .seg button,:root .ghost,:root select{min-height:38px}
}
"""


def _phong_css() -> str:
    """Khai báo @font-face cho phông Be Vietnam Pro đã tải về tinh/phong/ (xem tinh/NGUON.md). Trang lấy phông từ chính webapp, không gọi ra mạng;
    thiếu thư mục phông thì trả chuỗi rỗng và trang dùng phông có sẵn của máy."""
    try:
        ds = json.loads((Path(__file__).resolve().parent.parent / 'tinh' / 'phong' / 'phong.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return ''
    return ''.join(f'@font-face{{font-family:"Be Vietnam Pro";font-style:normal;font-weight:{x["dam"]};font-display:swap;'
                   f'src:url(/tinh/phong/{x["tep"]}) format("woff2");unicode-range:{x["khoang"]}}}' for x in ds)


CSS += _phong_css()

JS += """
(()=>{const r=document.documentElement,b=document.getElementById('theme');let s=null;try{s=localStorage.getItem('so-theme')}catch(e){}
if(s)r.dataset.theme=s;const cur=()=>r.dataset.theme||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
const lab=()=>{b.textContent=cur()==='dark'?'Nền sáng':'Nền tối'};lab();
b.addEventListener('click',()=>{const n=cur()==='dark'?'light':'dark';r.dataset.theme=n;try{localStorage.setItem('so-theme',n)}catch(e){}lab()});
document.querySelectorAll('.copy').forEach(c=>c.addEventListener('click',()=>{const el=document.getElementById(c.dataset.for),t=el.textContent;
const sel=()=>{const g=document.createRange();g.selectNodeContents(el);const x=getSelection();x.removeAllRanges();x.addRange(g);c.textContent='Đã chọn, nhấn Ctrl+C'};
if(navigator.clipboard&&window.isSecureContext)navigator.clipboard.writeText(t).then(()=>{c.textContent='Đã chép'},sel);else sel()}));
const f=document.getElementById('refresh');if(f){f.addEventListener('click',()=>{f.setAttribute('aria-busy','true');f.disabled=true;f.textContent='Đang tải…';location.reload()});
setInterval(()=>{if(document.visibilityState==='visible'&&!getSelection().toString())location.reload()},120000)}})();
"""

CSS += """
h1{font:700 27px/1.15 SANS;letter-spacing:-.01em}h2{font:700 18px/1.3 SANS}
h3{font-size:12px;letter-spacing:.04em;text-transform:none;color:var(--mute);font-weight:600;margin:22px 0 8px}
.top{border-bottom:1px solid var(--line)}.brand{color:var(--mute)}.bar strong{color:var(--ink);letter-spacing:.06em}
.tag{border-color:var(--line);color:var(--ink2);background:var(--bg);font-weight:600;letter-spacing:.04em}
.hero a{border-radius:14px;box-shadow:0 1px 2px rgba(16,24,40,.04)}.hero b{font:700 26px/1.2 SANS}
.card{border-radius:16px;box-shadow:0 1px 2px rgba(16,24,40,.04)}
.tile b{font:700 20px/1.3 SANS}.tiles{border-radius:12px}
.tabs{display:flex;gap:22px;border-bottom:1px solid var(--line);margin:4px 0 16px;overflow-x:auto;scrollbar-width:none}
.tabs button{font:500 14px SANS;color:var(--mute);background:none;border:0;border-bottom:2px solid transparent;padding:9px 0;cursor:pointer;white-space:nowrap}
.tabs button[aria-selected=true]{color:var(--ink);font-weight:700;border-bottom-color:var(--series)}
.tabs button:focus-visible{outline:2px solid var(--series);outline-offset:2px}
.bar button,.copy{border-radius:999px}.bar button:hover,.copy:hover{border-color:var(--series)}
.donut{display:grid;grid-template-columns:1fr auto 1fr;align-items:start;gap:10px;max-width:520px;margin:0 auto}
.donut svg{width:180px;height:180px}.dn.track{stroke-width:9}
.dleg{font-size:13px;color:var(--ink2);padding-top:6px}.dleg.r{text-align:right}.dleg b{display:block;color:var(--ink);font-size:15px;font-variant-numeric:tabular-nums}
.dleg .sw{border-radius:50%;width:8px;height:8px;margin-right:6px}
svg text.dnv{font:700 17px SANS;fill:var(--gain)}svg text.dnl{font-size:11px}
.gauge{padding:10px 0 8px;border-bottom:1px solid var(--line)}.gauge:last-child{border-bottom:0}
.grow{display:flex;justify-content:space-between;gap:12px;font-size:13.5px;color:var(--ink2)}.grow b{color:var(--ink);font-variant-numeric:tabular-nums;white-space:nowrap}
.gtrack{position:relative;height:12px;border-radius:3px;margin:14px 0 4px;background:linear-gradient(90deg,#e6f4ec,#fbf3d6 55%,#fde3d8)}
:root[data-theme="dark"] .gtrack{background:linear-gradient(90deg,#1d3a2d,#3a3420 55%,#43271f)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .gtrack{background:linear-gradient(90deg,#1d3a2d,#3a3420 55%,#43271f)}}
.gtrack i{position:absolute;top:-5px;transform:translateX(-50%);font:700 11px/1 SANS;font-style:normal;color:var(--card);background:var(--ink);border-radius:4px;padding:5px 6px;white-space:nowrap;font-variant-numeric:tabular-nums}
.gends{display:flex;justify-content:space-between;font-size:11.5px;color:var(--mute)}
.kvs{max-width:520px;margin:14px auto 0}.kvr{display:flex;justify-content:space-between;gap:12px;padding:6px 0;font-size:14px;color:var(--ink2)}
.kvr b{color:var(--ink);font-variant-numeric:tabular-nums}.kvr:last-child{border-top:1px solid var(--line);margin-top:4px;padding-top:9px}.kvr:last-child b{font-size:15px}
.deals{border:1px solid var(--line);border-radius:12px;overflow:hidden}
.deal{display:flex;justify-content:space-between;gap:14px;padding:10px 14px;border-bottom:1px solid var(--line);font-size:14px}.deal:last-child{border-bottom:0}
.deal b{font-weight:700}.deal small{display:block;color:var(--mute);font-size:12.5px;margin-top:2px}.deal .r{text-align:right;white-space:nowrap}
.deal .buy{color:var(--series);font-weight:600}.deal .sell{color:var(--loss);font-weight:600}
.frow .fill{background:var(--series)}.note{border-radius:12px}th{background:var(--bg)}
.bar strong{margin-right:10px}.bar .sec{margin-left:auto;display:flex;align-items:center;gap:6px 16px;flex-wrap:wrap}
.bar a.pri{font-weight:600;font-size:14px;padding:6px 0}.bar a[aria-current=page]{color:var(--ink);box-shadow:inset 0 -2px 0 var(--series);text-decoration:none}
@media(max-width:640px){.bar .sec{flex-wrap:nowrap;margin-left:8px}}
.subnav{border-top:1px solid var(--line);background:var(--card)}.subnav>div{max-width:1080px;margin:0 auto;padding:4px 16px;display:flex;gap:4px 22px;overflow-x:auto;white-space:nowrap;scrollbar-width:none}.subnav a{font-size:12.5px;padding:4px 0}:target{scroll-margin-top:104px}
:root *{font-family:"Be Vietnam Pro","Segoe UI",Tahoma,Verdana,Arial,sans-serif!important}
body{font-size:13px}h1{font-size:24px}h2{font-size:17px}.hero b{font-size:24px}.tile b{font-size:19px}
.card{border-radius:10px;padding:18px 18px 14px}.hero a,.tiles,.deals,.note{border-radius:8px}.bar button,.copy{border-radius:6px}
.cbr{padding:8px 0;border-bottom:1px solid var(--line);font-size:13px;color:var(--ink2)}.cbr:last-child{border-bottom:0}
.cbr b{display:block;color:var(--ink)}.cbr span{display:block;margin:2px 0}.cbr small{color:var(--mute);font-size:12px}
@media print{.pane[hidden]{display:block!important}.tabs{display:none}}
main{max-width:1240px}.bar>div,.subnav>div{max-width:1240px}
.hero{grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}.hero a{display:flex;flex-direction:column;padding:14px 16px 12px}
.hero .hd{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px}.hero .hd h4{margin:0;font-size:13px}
.hero b i{font-style:normal;font-size:14px;font-weight:600;color:var(--mute)}.hero small{font-size:12.5px;font-variant-numeric:tabular-nums}
.hero em{margin-top:auto;padding-top:9px}.hero .tia,.hero .hbar{margin-bottom:12px}
.tia{display:block;width:100%;height:40px;margin-top:10px}.tia polyline{fill:none;stroke-width:1.8;stroke-linejoin:round;vector-effect:non-scaling-stroke}
.tia.gain polyline{stroke:var(--gain)}.tia.loss polyline{stroke:var(--loss)}
.hbar{position:relative;height:6px;border-radius:3px;background:var(--track);margin-top:27px}.hbar>span{display:block;height:100%;border-radius:3px;background:var(--series)}
.hbar>u{position:absolute;top:-4px;width:2px;height:14px;background:var(--ink);text-decoration:none}
.now{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:4px 30px}.now.ba{grid-template-columns:minmax(0,1.25fr) minmax(0,.95fr) minmax(0,.95fr)}
.now h3{margin-top:14px}@media(max-width:980px){.now,.now.ba{grid-template-columns:1fr}}
.rows .kvr{border-bottom:1px solid var(--line);padding:7px 0;font-size:13px;margin:0}.rows .kvr:last-child{border-top:0;border-bottom:0;margin-top:0;padding-top:7px}
.rows .kvr:last-child b{font-size:inherit}
.btnl{display:inline-block;margin-top:12px;font-weight:600;font-size:12.5px;color:var(--btn-ink);background:var(--series);border-radius:6px;padding:7px 12px;text-decoration:none}
.btnl:hover,.btnl:focus-visible{filter:brightness(1.08);outline:none}
.acc{display:grid;grid-template-columns:minmax(0,2fr) minmax(250px,1fr);gap:6px 30px;align-items:start}.acc h3{margin-top:4px}
@media(max-width:860px){.acc{grid-template-columns:1fr}}
.accs .big{padding:2px 0 12px;border-bottom:1px solid var(--line)}.accs .big>span{display:block;color:var(--ink2);font-size:12.5px}.hero .tag{white-space:nowrap;flex:none}
.accs .big b{display:block;font-size:26px;font-weight:700;line-height:1.25;font-variant-numeric:tabular-nums}.accs .big small{font-size:12.5px;color:var(--mute);font-variant-numeric:tabular-nums}
@media(max-width:980px){.now,.now.ba{grid-template-columns:minmax(0,1fr)}}@media(max-width:860px){.acc{grid-template-columns:minmax(0,1fr)}}
@media(max-width:640px){.hero,.fresh{grid-template-columns:repeat(2,minmax(0,1fr))}.hero{gap:10px}.hero a{padding:12px 12px 10px}
.hero .hd{flex-direction:column-reverse;align-items:flex-start;gap:6px}.hero b{font-size:20px}.hero b i{font-size:12px}.hero small,.hero em{font-size:12px}
.fresh div{padding:8px 10px}main{padding:18px 12px 48px}}
.gauges{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 34px}@media(max-width:760px){.gauges{grid-template-columns:minmax(0,1fr)}}
.gtrack.tot{background:linear-gradient(90deg,#fde3d8,#fbf3d6 45%,#e6f4ec)}:root[data-theme="dark"] .gtrack.tot{background:linear-gradient(90deg,#43271f,#3a3420 45%,#1d3a2d)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .gtrack.tot{background:linear-gradient(90deg,#43271f,#3a3420 45%,#1d3a2d)}}
details .wrap{max-height:452px;overflow:auto}
summary{text-transform:none;letter-spacing:.02em;color:var(--mute);font-weight:600}
.note{background:var(--card);color:var(--ink2);border:1px solid var(--line);border-left:3px solid #d9a300;border-radius:6px;font-size:13px;padding:9px 14px}.note b{color:var(--ink)}
.board{display:grid;grid-template-columns:304px minmax(0,1fr);background:var(--card);border:1px solid var(--line);border-radius:10px;margin:16px 0 0;overflow:hidden;box-shadow:0 1px 2px rgba(16,24,40,.04)}
.board.mot{grid-template-columns:minmax(0,1fr)}
.gia{padding:16px 18px 16px;border-right:1px solid var(--line);display:flex;flex-direction:column}
.gh{display:flex;justify-content:space-between;align-items:baseline;gap:8px;font-size:12px;color:var(--mute)}.gh b{font-size:13px;color:var(--ink2);letter-spacing:.03em}
.gp{font-size:38px;font-weight:700;line-height:1.15;font-variant-numeric:tabular-nums;letter-spacing:-.015em;margin-top:2px}
.ga{font-size:12.5px;color:var(--ink2);font-variant-numeric:tabular-nums}
.gv{display:block;width:100%;height:64px;margin:12px 0 10px}.gv polyline{fill:none;stroke:var(--series);stroke-width:1.6;vector-effect:non-scaling-stroke;stroke-linejoin:round}
.gv polygon{fill:var(--series);opacity:.07}
.gxh{display:flex;gap:6px;flex-wrap:wrap}.xh{font-size:12px;font-weight:700;border:1px solid var(--line);border-radius:4px;padding:2px 8px;color:var(--ink2)}.xh.gain{color:var(--gain)}.xh.loss{color:var(--loss)}
.gia .rows{margin:8px 0 14px}.gia .rows .small{margin:6px 0 0;font-size:12px}.gia .btnl{margin-top:auto;align-self:flex-start}
.so{min-width:0}
.sr{display:grid;grid-template-columns:minmax(200px,1.9fr) minmax(104px,.9fr) minmax(104px,.9fr) minmax(104px,1fr) 62px minmax(104px,.85fr);align-items:center;gap:0 16px;
padding:11px 18px;border-bottom:1px solid var(--line);color:inherit;text-decoration:none;font-variant-numeric:tabular-nums;font-size:13px}
.sr:last-child{border-bottom:0}a.sr:hover,a.sr:focus-visible{background:var(--bg);outline:none}
.sr.hd{font-size:12px;color:var(--mute);padding:8px 18px;background:var(--bg)}
.sr>span{min-width:0}.sr .r{text-align:right}.sr .m{text-align:center}
.sr .ten b{font-size:13.5px;font-weight:700;margin-right:7px}.sr .ten .tag{margin:0;font-size:10px;padding:3px 7px;font-style:normal}
.sr small{display:block;font-size:12px;color:var(--mute);font-weight:400;margin-top:1px}
.sr .v{font-size:17px;font-weight:700}.sr .v i{font-style:normal;font-size:12px;font-weight:600;color:var(--mute)}.sr .c{font-weight:700}
.sr .z .tia{height:30px;margin:0}.sr .z .hbar{margin:0}.sr .f{color:var(--ink2)}
.tag.th{border-color:var(--series);color:var(--series);background:none}.tag.cb{border-style:dashed}
.now{grid-template-columns:minmax(0,1.3fr) minmax(0,1fr)}
.duo{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.45fr);gap:6px 32px;align-items:start;margin-top:8px}.duo.ng{grid-template-columns:minmax(0,1.45fr) minmax(0,1fr)}
.duo details{margin-top:14px}.duo .funnel{max-width:none}
@media(max-width:1000px){.board{grid-template-columns:minmax(0,1fr)}.gia{border-right:0;border-bottom:1px solid var(--line)}.gia .btnl{margin-top:4px}}
@media(max-width:860px){.duo,.duo.ng{grid-template-columns:minmax(0,1fr)}}
@media(max-width:760px){.sr{grid-template-columns:minmax(0,1fr) auto;grid-template-areas:"ten v" "f c";gap:4px 12px;padding:10px 14px}.sr.hd,.sr .z,.sr .m{display:none}
.sr .ten{grid-area:ten}.sr .v{grid-area:v;font-size:16px}.sr .c{grid-area:c}.sr .f{grid-area:f;font-size:12px;color:var(--mute)}.sr .f small,.sr .c small{display:inline;margin-left:5px}
.sr .ten b{display:block;margin:0 0 3px}.gp{font-size:32px}}details thead th{position:sticky;top:0;z-index:1}
""".replace('SANS', '\"Segoe UI\",Roboto,\"Helvetica Neue\",Arial,sans-serif')

JS += """
document.querySelectorAll('.tabs').forEach(t=>{const bs=[...t.querySelectorAll('button')],ps=[...t.parentElement.querySelectorAll(':scope>.pane')];
bs.forEach((b,i)=>b.addEventListener('click',()=>{bs.forEach((x,j)=>{x.setAttribute('aria-selected',j===i);ps[j].hidden=j!==i})}))});
"""


def _truoc(now: datetime, t: datetime | None) -> str:
    if t is None:
        return ''
    m = max(0, int((now - t).total_seconds() // 60))
    return f'{m} phút trước' if m < 90 else f'{m // 60} giờ trước' if m < 48 * 60 else f'{m // 1440} ngày trước'


def _bang_so(now: datetime, d: dict, live: bool = False) -> str:
    """Bảng đầu trang: mỗi sổ một dòng (con số chính, thay đổi, diễn biến, lệnh mở, dữ liệu đọc tới lúc nào). Khi webapp đang chạy
    thì bên trái có ô giá vàng, do trình duyệt tự đọc từ /api/gia và /api/phan-tich."""
    rows = []

    def dong(i, ten, tag, lop, phu, v, c, z, m, t):
        rows.append(f'<a class="sr" role="row" href="#{escape(i)}"><span class="ten"><b>{escape(ten)}</b><i class="tag{lop}">{tag}</i><small>{escape(phu)}</small></span>'
                    f'<span class="v r">{v}</span><span class="c r">{c}</span><span class="z">{z}</span><span class="m">{m}</span>'
                    f'<span class="f">{escape(gio(t)) if t else "chưa có dữ liệu"}<small>{escape(_truoc(now, t))}</small></span></a>')

    for acc in d.get('tai_khoan', []):
        e = acc['tom']
        if e is None:
            continue
        pct = f'{e["equity_change"] / e["first_equity"]:+.1%}'.replace('.', ',') if e['first_equity'] else ''
        dong(acc['id'], acc['ten'], 'DEMO', '', f'{e["n"]} lệnh đã đóng' + (' (chưa đủ 30 để nhận xét)' if e['n'] < 30 else '')
             + (f', {len(e["opens"])} lệnh mở có lãi lỗ đang treo' if e['opens'] else ''),
             f'{so(e["last_equity"])} <i>USD</i>', _mau(e['equity_change'], so(e['equity_change'], 2, True)) + f'<small>{pct} từ {so(e["first_equity"], 0)}</small>',
             _tia(e['curve'], 160, 30), str(len(e['opens'])), e['last_time'])
    b = d.get('bot')
    if b is not None:
        ty = b['tp1'] / b['decided'] if b['decided'] else 0.0
        dong('bot', 'Bot tín hiệu vàng', 'TÍN HIỆU', ' th', f'{b["sl0"]} lệnh chạm SL khi chưa có TP' + ('' if b['enough'] else ', dưới 30 lệnh đã đóng'),
             f'{b["tp1"]}<i>/{b["decided"]}</i>', (f'{ty:.0%}' if b['decided'] else '—') + '<small>lệnh chạm TP1</small>', _thanh(ty), str(b['open']),
             max((r['opened'] for r in b['rows']), default=None))
    x = d.get('xu_huong')
    if x is not None:
        ty = x['win'] / x['closed'] if x['closed'] else 0.0
        dong('xu-huong', 'Luật ba khung', 'CHẠY BÓNG', ' cb', 'Vạch đen là mức hòa vốn 80%. Sổ có thể sót lệnh lúc máy tắt.',
             f'{x["win"]}<i>/{x["closed"]}</i>', (f'{ty:.0%}' if x['closed'] else '—') + '<small>thắng theo sổ</small>',
             _thanh(ty, 0.8, 'hòa vốn cần thắng trên 80%'), str(x['n'] - x['closed']), max((r['opened'] for r in x['rows']), default=None))
    k = d.get('dinh_day')
    if k is not None:
        dong('dinh-day', 'Luật đỉnh/đáy', 'CHẠY BÓNG', ' cb', f'{k["n"]} lệnh giả định, quá ít để nhận xét',
             _mau(k['r'], so(k['r'], 2, True)) + ' <i>R</i>', f'{k["win"]}/{k["n"]}<small>lệnh thắng</small>', '', '—',
             max((r['opened'] for r in k['rows'] if r.get('opened')), default=None))
    gia = ('<aside class="gia" id="gia-vang"><div class="gh"><b>XAUUSD</b><span id="gv-nguon">đang đọc giá…</span></div>'
           '<div class="gp" id="gv-gia">—</div><div class="ga" id="gv-ask">&nbsp;</div>'
           '<svg class="gv" id="gv-hinh" viewBox="0 0 300 64" preserveAspectRatio="none" role="img" aria-label="Giá vàng qua 24 giờ giao dịch gần nhất"></svg>'
           '<div class="gxh" id="gv-xh"></div><div class="rows" id="gv-them"></div>'
           '<a class="btnl" href="/bieu-do">Mở biểu đồ và phân tích điểm vào</a></aside>') if live else ''
    head = ('<div class="sr hd" role="row"><span>Sổ</span><span class="r">Hiện tại</span><span class="r">Thay đổi</span><span>Diễn biến</span>'
            '<span class="m">Lệnh mở</span><span>Dữ liệu đọc tới</span></div>')
    return (f'<section class="board{"" if live else " mot"}" aria-label="Tình hình chung">{gia}<div class="so" role="table">{head}{"".join(rows)}</div></section>'
            + ('<a class="ttl" id="tt-dong" href="#tinh-trang" hidden></a>' if live else ''))


def _khoi_tuan(tuan: dict) -> str:
    out = [f'<section class="card" id="tuan"><h2>Tổng kết tuần {tuan["start"].isocalendar()[1]}</h2>'
           '<p class="sub">Bài chữ để bạn đọc lại rồi tự đăng lên Telegram hoặc Facebook. Chương trình không tự đăng gì.</p>'
           f'<pre class="bai" id="bai-tuan">{escape(tuan["bai"])}</pre><button class="copy" type="button" data-for="bai-tuan">Chép bài</button>']
    if tuan.get('threads'):
        out.append('<h3>Bản nháp bài Threads</h3><div class="drafts">')
        for i, t in enumerate(tuan['threads']):
            state = 'ĐÃ DUYỆT' if t['approved'] else 'CHƯA DUYỆT · CHƯA ĐĂNG'
            out.append(f'<div class="draft"><img src="{escape(t["img"])}" alt="Ảnh thẻ của bản nháp {escape(t["id"])}" loading="lazy">'
                       f'<span class="state">{state}</span>'
                       f'<pre class="bai" id="nhap-{i}">{escape(t["text"])}</pre>'
                       f'<button class="copy" type="button" data-for="nhap-{i}">Chép chú thích</button></div>')
        out.append('</div>')
    return ''.join(out) + '</section>'


def _khoi_hien_tai(h: dict, live: bool = False) -> str:
    """Việc đang diễn ra ngay lúc này: lệnh còn mở của bot và của các EA demo, thị trường (chỉ khi webapp đang chạy), cảnh báo gần nhất."""
    lenh, cb = h.get('lenh') or [], h.get('canh_bao') or []
    tin = h.get('tin')
    out = ['<section class="card" id="hien-tai"><h2>Đang diễn ra</h2>'
           '<p class="sub">Lệnh còn mở và cảnh báo gần nhất. Lệnh của bot là tín hiệu, lệnh của EA là trên tài khoản demo.</p>'
           f'<div class="now{" ba" if tin is not None else ""}">',
           f'<div><h3>Lệnh đang mở ({len(lenh)})</h3>']
    if lenh:
        out.append(_table(['Nguồn', 'Loại', 'Giá vào', 'SL', 'TP kế tiếp'],
                          [[escape(o['nhan']), 'demo' if o.get('loai') == 'demo' else 'tín hiệu', so(o['vao']) if o.get('vao') is not None else '—',
                            so(o['sl']) if o.get('sl') is not None else '—', so(o['tp'][0]) if o.get('tp') else '—'] for o in lenh], right={2, 3, 4}))
    else:
        out.append('<p class="small">Bot và các EA demo không có lệnh nào đang mở.</p>')
    out.append('</div>')
    if tin is not None:
        out.append(f'<div><h3>Tin USD mạnh sắp tới ({len(tin)})</h3>')
        if tin:
            out += [f'<div class="cbr"><b>{escape(a["ten"] or "Tin USD mức cao")}</b><small>{gio(datetime.fromisoformat(a["luc"]))} giờ Việt Nam, {escape(a["con"])}</small></div>'
                    for a in tin]
            out.append('<p class="small">Bot và các luật của bạn không vào lệnh trong 15 phút trước và sau mỗi tin.</p>')
        else:
            out.append('<p class="small">Lịch tin trên máy không còn tin USD mức cao nào sắp tới. Lịch do MT5 xuất ra; mở MT5 để cập nhật.</p>')
        out.append('</div>')
    out.append(f'<div><h3>Cảnh báo gần đây ({len(cb)})</h3>')
    if cb:
        out += [f'<div class="cbr"><b>{escape(a["tieu_de"])}</b><span>{escape(a["noi_dung"])}</span>'
                f'<small>{gio(datetime.fromisoformat(a["luc"]))}</small></div>' for a in cb]
    else:
        out.append('<p class="small">Chưa có cảnh báo nào. Cảnh báo xuất hiện khi một luật ra tín hiệu trên nến vừa đóng, hoặc 30 phút trước tin USD mạnh.</p>')
    return ''.join(out) + '</div></div></section>'


_KHOI_MA = ('<section class="card" id="ma-khac"><h2>Các mã CFD trong MT5 của bạn</h2>'
            '<p class="sub">Mọi mã đang hiện trong Market Watch của MT5 demo. Bấm vào một mã để mở biểu đồ. Phần này chỉ có bối cảnh '
            '(xu hướng, biên độ, RSI); các luật vào lệnh của bạn được viết và đo riêng cho vàng nên không áp cho mã khác.</p>'
            '<div id="ds-ma"><p class="small">Đang đọc giá từ MT5…</p></div></section>')


_KHOI_TINH_TRANG = ('<section class="card" id="tinh-trang"><h2>Tình trạng hệ thống</h2>'
                    '<p class="sub">Từng nguồn dữ liệu và từng bộ phận của webapp có đang chạy đúng không. Mục cần xem được xếp lên đầu.</p>'
                    '<div id="tt-he-thong"><p class="small">Đang soát…</p></div></section>')


_HINH = {
    'so': 'M4 5h16v14H4zM4 9h16M9 9v10', 'gia': 'M3 17l6-6 4 4 8-8M15 7h6v6', 'kt': 'M12 14l4-4M3.5 17a9 9 0 1 1 17 0',
    'sm': 'M5 20V10M10 20V4M15 20v-8M20 20v-5', 'nhiet': 'M3 3h8v8H3zM13 3h8v5h-8zM13 10h8v11h-8zM3 13h8v8H3z',
    'tq': 'M5 19L19 5M5 5h4v4H5zM15 15h4v4h-4z', 'song': 'M2 12c2-6 4-6 6 0s4 6 6 0 4-6 6 0', 'lich': 'M4 6h16v14H4zM4 10h16M9 3v4M15 3v4',
    'ts': 'M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01', 'nen': 'M7 4v16M17 4v16M5 8h4v8H5zM15 6h4v6h-4z',
    'tinh': 'M6 3h12v18H6zM9 7h6M9 11h.01M12 11h.01M15 11h.01M9 15h.01M12 15h.01M15 15h.01',
    'nk': 'M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3zM5 17a3 3 0 0 1 3-3h11', 'tk': 'M3 7h18v12H3zM3 7l3-3h12l3 3M16 13h2',
    'hoc': 'M2 9l10-5 10 5-10 5zM6 11v5c3 2 9 2 12 0v-5', 'kt2': 'M2 5c4-1 7 0 10 2 3-2 6-3 10-2v14c-4-1-7 0-10 2-3-2-6-3-10-2zM12 7v14',
    'tim': 'M11 11m-7 0a7 7 0 1 0 14 0a7 7 0 1 0-14 0M21 21l-5-5',
    'tin': 'M4 5h13v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2zM17 9h3v10a2 2 0 0 1-2 2M8 9h5M8 13h5M8 17h3',
    'hs': 'M3 3v18h18M7 15l3-4 3 2 5-7M18 6h2v2', 'menu': 'M4 6h16M4 12h16M4 18h16', 'xuong': 'M6 9l6 6 6-6',
}


def hinh(k: str, cls: str = 'ic') -> str:
    """Biểu tượng nét mảnh 24×24, màu theo màu chữ."""
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true"><path d="{_HINH[k]}"/></svg>')


# (khóa trang, tên, đường dẫn, mục con [(khóa, tên, đường dẫn, mô tả, biểu tượng)], biểu tượng)
MENU = [
    ('tong', 'Tổng quan', '/', None, 'so'),
    ('thi-truong', 'Thị trường', '/thi-truong', [
        ('thi-truong', 'Bảng giá trực tiếp', '/thi-truong#bang-gia', 'Forex, kim loại, năng lượng, chỉ số, crypto', 'gia'),
        ('thi-truong', 'Tín hiệu kỹ thuật', '/thi-truong#ky-thuat', '19 chỉ báo trên 4 khung, bộ lọc mã', 'kt'),
        ('thi-truong', 'Sức mạnh tiền tệ', '/thi-truong#suc-manh', '8 đồng tiền chính, ma trận 28 cặp', 'sm'),
        ('thi-truong', 'Bản đồ nhiệt', '/thi-truong#ban-do-nhiet', 'Mã nào đang tăng, giảm mạnh', 'nhiet'),
        ('thi-truong', 'Tương quan', '/thi-truong#tuong-quan', 'Mã nào đi cùng chiều, ngược chiều', 'tq'),
        ('thi-truong', 'Biến động theo giờ', '/thi-truong#bien-dong', 'Giờ nào, thứ nào giá chạy nhiều nhất', 'song'),
        ('thi-truong', 'Phiên & lịch tin', '/thi-truong#phien', 'Bốn phiên lớn, tin kinh tế sắp ra', 'lich'),
        ('thi-truong', 'Thông số hợp đồng', '/thi-truong#thong-so', 'Pip, ký quỹ, đòn bẩy, swap từng mã', 'ts')], 'gia'),
    ('tin-tuc', 'Tin tức', '/tin-tuc', None, 'tin'),
    ('bieu-do', 'Biểu đồ', '/bieu-do', None, 'nen'),
    ('cong-cu', 'Công cụ', '/cong-cu', None, 'tinh'),
    ('so', 'Sổ giao dịch', None, [
        ('hieu-suat', 'Phân tích hiệu suất', '/hieu-suat', 'Bạn thắng, thua ở đâu: chỉ số, đường vốn, nhận xét', 'hs'),
        ('nhat-ky', 'Nhật ký điểm vào', '/nhat-ky', 'Mọi điểm vào của các phương pháp, chấm bằng giá thật', 'nk'),
        ('tai-khoan', 'Tài khoản MT5', '/tai-khoan', 'Vốn, lệnh đang mở, lãi lỗ theo ngày', 'tk'),
        ('tong', 'Sổ công khai', '/', 'Kết quả bot, EA demo và chạy bóng', 'so')], 'nk'),
    ('hoc', 'Học', None, [
        ('hoc', 'Học giao dịch', '/hoc-giao-dich', 'CFD, Forex, loại lệnh, 16 phong cách', 'hoc'),
        ('kien-thuc', 'Kiến thức', '/kien-thuc', 'Giải thích từng chỉ báo và luật trong hệ thống', 'kt2')], 'hoc'),
]


def thanh_dau(ten: str, trang_hien: str, phai: str = '', muc: str = '') -> str:
    """Thanh đầu trang dùng chung cho mọi trang của webapp: logo, menu nhóm (thả xuống), ô tìm nhanh (Ctrl+K), nút phụ; trên điện thoại
    menu gập vào nút ☰. Mục đang xem được tô sáng. `muc`: thanh phụ (liên kết tới các phần trong trang)."""
    ten_a, _, ten_b = (ten or '').partition('·')
    logo = (f'<a class="nv-logo" href="/" aria-label="{escape(ten)} — Tổng quan"><span class="nv-mk">{hinh("gia")}</span>'
            f'<span class="nv-tn"><b>{escape(ten_a.strip() or ten)}</b>' + (f'<small>{escape(ten_b.strip())}</small>' if ten_b.strip() else '') + '</span></a>')
    chinh, ngan, tim = [], [], []
    for k, n, h, con, ic in MENU:
        if not con:
            on = k == trang_hien
            chinh.append(f'<a class="nv-a" href="{h}"' + (' aria-current="page"' if on else '') + f'>{escape(n)}</a>')
            ngan.append(f'<a class="nv-d" href="{h}"' + (' aria-current="page"' if on else '') + f'>{escape(n)}{hinh(ic)}</a>')
            tim.append({'t': n, 'h': h, 'm': '', 'i': ic})
            continue
        on = any(c[0] == trang_hien for c in con) and not (k == 'so' and trang_hien == 'tong')
        cur = lambda ck, ch: ck == trang_hien and '#' not in ch               # noqa: E731 - mục con là trang đang xem
        muc_con = ''.join(f'<a class="nv-i" href="{ch}"' + (' aria-current="page"' if cur(ck, ch) else '') + f'>{hinh(ci)}<span><b>{escape(cn)}</b><small>{escape(cm)}</small></span></a>'
                          for ck, cn, ch, cm, ci in con)
        chinh.append(f'<div class="nv-g{" rong" if len(con) > 4 else ""}"><button type="button" class="nv-a{" on" if on else ""}" aria-expanded="false" aria-haspopup="true">'
                     f'{escape(n)}{hinh("xuong", "ic nv-x")}</button><div class="nv-m">{muc_con}</div></div>')
        ngan.append(f'<p class="nv-dh">{escape(n)}</p>' + ''.join(f'<a class="nv-d" href="{ch}"' + (' aria-current="page"' if cur(ck, ch) else '') + f'>{escape(cn)}{hinh(ci)}</a>'
                                                               for ck, cn, ch, _, ci in con))
        tim += [{'t': cn, 'h': ch, 'm': cm, 'i': ci} for _, cn, ch, cm, ci in con]
    tim_js = escape(json.dumps(tim, ensure_ascii=False), quote=True)
    sub = f'<nav class="subnav" aria-label="Các phần của trang"><div>{muc}</div></nav>' if muc else ''
    return (f'<header class="nv" data-tim="{tim_js}"><div class="nv-in">{logo}<nav class="nv-chinh" aria-label="Điều hướng chính">{"".join(chinh)}</nav>'
            f'<div class="nv-phai"><button type="button" class="nv-tim-b" aria-label="Tìm mã hoặc trang (Ctrl+K)">{hinh("tim")}<span>Tìm mã, trang…</span><kbd>Ctrl K</kbd></button>'
            f'<button type="button" class="nv-lang" id="nv-lang" title="Đổi ngôn ngữ">EN</button>'
            f'{phai}<button type="button" class="nv-mb" aria-label="Mở menu" aria-expanded="false">{hinh("menu")}</button></div></div>{sub}'
            f'<nav class="nv-ngan" hidden aria-label="Menu">{"".join(ngan)}</nav></header>')


def trang_html(ten: str, now: datetime, d: dict, tuan: dict | None = None, live: bool = False, hien_tai: dict | None = None) -> str:
    """`d`: số tổng hợp TOÀN BỘ sổ (không lọc theo tuần). `tuan`: {'start', 'bai', 'threads': [...]} cho khối tổng kết tuần.
    `live`: trang do máy chủ cục bộ phục vụ (có nút làm mới và tự tải lại mỗi 2 phút)."""
    links = [(acc['id'], acc['ten'].replace('Tài khoản ', '').capitalize()) for acc in d.get('tai_khoan', []) if acc['tom']]
    links += [(i, n) for i, n, ok in (('bot', 'Bot tín hiệu', d.get('bot') is not None), ('xu-huong', 'Chạy bóng', d.get('xu_huong') is not None),
                                      ('tuan', 'Tuần này', tuan is not None)) if ok]
    if live:
        links.insert(0, ('ma-khac', 'Các mã CFD'))
        links.append(('tinh-trang', 'Tình trạng'))
    nav = ''.join(f'<a href="#{escape(i)}">{escape(n)}</a>' for i, n in links)
    out = [f'<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f'{BIEU_TUONG}<title>Sổ công khai · {escape(ten)}</title><style>{CSS}</style></head><body>',
           (thanh_dau(ten, 'tong', '<button id="refresh" type="button">Làm mới</button><button id="theme" type="button">Nền tối</button>', nav) if live
            else f'<header class="bar"><div><strong>{escape(ten)}</strong><span class="sec">{nav}<button id="theme" type="button">Nền tối</button></span></div></header>')
           + '<main>',
           '<div class="top"><div><h1>Sổ công khai</h1></div>'
           f'<div class="stamp">Cập nhật {now.astimezone(VN):%H:%M ngày %d/%m/%Y}<br>giờ Việt Nam' + (' · tự tải lại mỗi 2 phút' if live else '') + '</div></div>',
           '<p class="note"><b>Đọc trước:</b> mọi con số ở trang này là tín hiệu, tài khoản DEMO hoặc chạy bóng (không đặt lệnh). '
           'Không có tài khoản tiền thật nào ở đây. Số liệu demo và mô phỏng thường đẹp hơn giao dịch thật vì chưa tính đủ trượt giá và tâm lý. '
           'Không phải lời khuyên đầu tư.</p>',
           _bang_so(now, d, live)] + ([_khoi_hien_tai(hien_tai, live)] if hien_tai is not None else []) + ([_KHOI_MA] if live else [])
    out += [_khoi_tai_khoan(acc) for acc in d.get('tai_khoan', [])]
    if d.get('bot') is not None:
        out.append(_khoi_bot(d['bot']))
    out.append(_khoi_bong(d.get('xu_huong'), d.get('dinh_day')))
    if tuan is not None:
        out.append(_khoi_tuan(tuan))
    if live:
        out.append(_KHOI_TINH_TRANG)
    for name, err in d.get('loi', []):
        out.append(f'<section class="card"><h2>{escape(name)}</h2><p class="note">Không đọc được sổ: {escape(err)}.</p></section>')
    out.append('<footer>Trang này do một chương trình chỉ đọc dựng từ sổ gốc của hệ thống: cơ sở dữ liệu của bot, nhật ký sự kiện của từng EA '
               'và hai sổ chạy bóng. Chương trình không sửa sổ, không đặt lệnh, không chọn lọc dòng: sổ có gì thì trang có nấy. '
               'Sụt vốn tính trên đường vốn do EA ghi lại ở mỗi sự kiện, nên có thể bỏ sót dao động giữa hai lần ghi. '
               + escape(mien_tru()) + f'</footer></main><script>{JS}</script></body></html>')
    return '\n'.join(out)


JS += """
(()=>{const P=document.getElementById('gia-vang');if(!P)return;const $=i=>document.getElementById(i),
f2=v=>v==null?'—':Number(v).toLocaleString('vi-VN',{minimumFractionDigits:2,maximumFractionDigits:2}),kv=(k,v)=>`<div class="kvr"><span>${k}</span><b>${v}</b></div>`;
const gia=()=>fetch('/api/gia?tf=M15&n=96',{cache:'no-store'}).then(r=>{if(!r.ok)throw 0;return r.json()}).then(j=>{const cs=(j.candles||[]).slice(-96);if(cs.length<2)throw 0;
const bid=j.bid||cs[cs.length-1][4],v=cs.map(c=>c[4]).concat([bid]),d=(bid/v[0]-1)*100,lo=Math.min(...v),hi=Math.max(...v),sp=(hi-lo)||1;
$('gv-gia').textContent=f2(bid);
$('gv-ask').innerHTML=(j.ask?'Ask '+f2(j.ask)+', ':'')+`<span class="${d>0?'gain':d<0?'loss':''}">${(d>0?'+':d<0?'−':'')+f2(Math.abs(d))}%</span> qua 24 giờ giao dịch gần nhất`;
const pts=v.map((x,i)=>(i/(v.length-1)*300).toFixed(1)+','+(60-(x-lo)/sp*56).toFixed(1)).join(' ');
$('gv-hinh').innerHTML=`<polygon points="0,64 ${pts} 300,64"/><polyline points="${pts}"/>`;
$('gv-nguon').textContent=j.nguon==='mt5'?'giá từ MT5 demo':'giá từ kho nến'}).catch(()=>{$('gv-nguon').textContent='không đọc được giá'});
gia();setInterval(()=>{if(document.visibilityState==='visible')gia()},20000);
fetch('/api/phan-tich',{cache:'no-store'}).then(r=>{if(!r.ok)throw 0;return r.json()}).then(j=>{const b=j.boi_canh||{},x=b.xu_huong||{},pa=j.phuong_an||[],co=pa.filter(p=>p.co);
$('gv-xh').innerHTML=['D1','H4','H1'].map(k=>`<span class="xh ${x[k]>0?'gain':x[k]<0?'loss':''}">${k} ${x[k]>0?'▲ tăng':x[k]<0?'▼ giảm':'ngang'}</span>`).join('');
let h=kv('ATR14 (M15)',f2(b.atr_m15))+kv('Luật còn hiệu lực lúc này',(j.con_hieu_luc||0)+' / '+pa.length+(j.con_hieu_luc?' ('+[...new Set(pa.filter(p=>p.hieu_luc).map(p=>p.huong==='MUA'?'MUA':'BÁN'))].join(', ')+')':''));
const ghi=co.length>(j.con_hieu_luc||0)?`<p class="small">${co.length-(j.con_hieu_luc||0)} luật có điều kiện nhưng chỉ còn để tham khảo (giá cũ, ngoài khung giờ hoặc nến tín hiệu đã quá hạn).</p>`:'';
if(b.tin&&b.tin.sap_toi)h+=kv('Tin USD mạnh kế tiếp',new Date(b.tin.sap_toi).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}));
if(j.tuoi_phut>20)h+=`<p class="small">Giá cũ ${j.tuoi_phut>=120?Math.round(j.tuoi_phut/60)+' giờ':j.tuoi_phut+' phút'}: thị trường nghỉ hoặc MT5 không có giá mới.</p>`;
$('gv-them').innerHTML=h+ghi}).catch(()=>{})})();
"""


# ------------------------------------------------------------------ hệ nút dùng chung cho cả ba trang
def _bt(body: str) -> str:
    """Một biểu tượng nét mảnh 24x24 dạng url() để dùng làm mặt nạ; màu lấy theo màu chữ của nút."""
    svg = ("%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.2' stroke-linecap='round' "
           "stroke-linejoin='round'%3E" + body.replace('<', '%3C').replace('>', '%3E') + '%3C/svg%3E')
    return f'url("data:image/svg+xml,{svg}")'


BIEU_TUONG_NUT = {
    'lam-moi': "<path d='M21 12a9 9 0 1 1-3-6.7M21 4v5h-5'/>",
    'trang': "<path d='M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z'/>",
    'mat-troi': "<circle cx='12' cy='12' r='4'/><path d='M12 4V2M12 22v-2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4'/>",
    'mo-rong': "<path d='M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5'/>",
    'thu-lai': "<path d='M3 8h5V3M21 8h-5V3M3 16h5v5M21 16h-5v5'/>",
    'ngam': "<circle cx='12' cy='12' r='7'/><path d='M12 2v5M12 17v5M2 12h5M17 12h5'/>",
    'cong': "<path d='M12 5v14M5 12h14'/>",
    'tru': "<path d='M5 12h14'/>",
    'hien-tai': "<path d='M5 5l9 7-9 7zM19 5v14'/>",
    'chep': "<rect x='9' y='9' width='12' height='12' rx='2'/><path d='M5 15V5a2 2 0 0 1 2-2h10'/>",
    'bieu-do': "<path d='M3 3v18h18M7 15l4-5 4 3 5-7'/>",
    'dong': "<path d='M6 6l12 12M18 6 6 18'/>",
    'quay': "<path d='M21 12a9 9 0 1 1-6.2-8.6'/>",
}

CSS += ':root{' + ''.join(f'--i-{k}:{_bt(v)};' for k, v in BIEU_TUONG_NUT.items()) + '}' + """
.bar button,.copy,.btnl,.act,.ghost,.go{display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:32px;padding:0 13px;border-radius:6px;
font-size:12.5px;font-weight:600;line-height:1;cursor:pointer;white-space:nowrap;user-select:none;text-decoration:none;
transition:background-color .12s,border-color .12s,color .12s,filter .12s}
.bar button,.copy,.ghost{background:var(--card);color:var(--ink);border:1px solid var(--line);box-shadow:0 1px 0 rgba(16,24,40,.04)}
.bar button:hover,.copy:hover,.ghost:hover{border-color:var(--mute);background:var(--bg)}
.btnl,.act,.go{background:var(--series);color:var(--btn-ink);border:1px solid var(--series);font-weight:700;box-shadow:0 1px 0 rgba(16,24,40,.1)}
.btnl:hover,.act:hover:not(:disabled),.go:hover:not(:disabled){filter:brightness(1.08)}
.ghost.nho{min-height:28px;padding:0 10px;font-size:12px}
:is(.bar button,.copy,.btnl,.act,.ghost,.go):active:not(:disabled){transform:translateY(1px)}
:is(.bar button,.copy,.btnl,.act,.ghost,.go):focus-visible{outline:2px solid var(--series);outline-offset:2px;border-color:var(--series)}
:is(.bar button,.copy,.ghost):disabled{opacity:.55;cursor:not-allowed}
#refresh::before,#theme::before,#pt-btn::before,#fs-btn::before,.copy::before,.btnl::before,.pt .x::before,.zo button::before{content:"";width:14px;height:14px;flex:none;
background:currentColor;-webkit-mask:var(--i) center/contain no-repeat;mask:var(--i) center/contain no-repeat}
#refresh{--i:var(--i-lam-moi)}#theme{--i:var(--i-trang)}:root[data-theme="dark"] #theme{--i:var(--i-mat-troi)}
#pt-btn{--i:var(--i-ngam)}#fs-btn{--i:var(--i-mo-rong)}#fs-btn[aria-pressed=true]{--i:var(--i-thu-lai)}
.copy{--i:var(--i-chep)}.btnl{--i:var(--i-bieu-do)}.pt .x{--i:var(--i-dong)}
[aria-busy=true]::before{-webkit-mask-image:var(--i-quay)!important;mask-image:var(--i-quay)!important;animation:quay .8s linear infinite}
@keyframes quay{to{transform:rotate(360deg)}}
.tabs button:hover{color:var(--ink)}
@media(pointer:coarse){.bar button,.copy,.btnl,.act,.ghost,.go{min-height:38px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation-duration:.01s!important;scroll-behavior:auto!important}}
"""


CSS += """
#ds-ma td,#ds-ma th{padding:7px 12px}#ds-ma td a{font-weight:700;color:var(--ink);text-decoration:none}#ds-ma td a:hover{color:var(--series);text-decoration:underline}
#ds-ma td small{display:block;color:var(--mute);font-size:12px;font-weight:400}#ds-ma .tia{width:110px;height:26px;margin:0}#ds-ma .xh{margin-right:4px}
#ds-ma tr.vang td:first-child{box-shadow:inset 3px 0 0 var(--series)}
"""

JS += """
(()=>{const el=document.getElementById('ds-ma');if(!el)return;const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])),
so=(v,d)=>v==null?'—':Number(v).toLocaleString('vi-VN',{minimumFractionDigits:d,maximumFractionDigits:d}),
xh=(k,v)=>`<span class="xh ${v>0?'gain':v<0?'loss':''}">${k} ${v>0?'▲':v<0?'▼':'–'}</span>`,
tia=a=>{const v=(a||[]).filter(x=>x!=null);if(v.length<2)return'';const lo=Math.min(...v),hi=Math.max(...v),sp=(hi-lo)||1;
 return `<svg class="tia ${v[v.length-1]>=v[0]?'gain':'loss'}" viewBox="0 0 110 26" preserveAspectRatio="none" aria-hidden="true"><polyline points="${v.map((x,i)=>(i/(v.length-1)*110).toFixed(1)+','+(23-(x-lo)/sp*20).toFixed(1)).join(' ')}"/></svg>`};
fetch('/api/ma',{cache:'no-store'}).then(r=>{if(!r.ok)throw 0;return r.json()}).then(j=>{
 if(!j.san_sang){el.innerHTML=`<p class="small">Chưa đọc được các mã từ MT5: ${esc(j.ly_do||'chưa nối')}. Mở MT5 demo rồi bấm Làm mới.</p>`;return}
 let h='<div class="wrap"><table><thead><tr><th>Mã</th><th>Nhóm</th><th class="r">Giá</th><th class="r">So với hôm trước</th><th>Xu hướng</th><th class="r">ATR14 H1</th><th class="r">RSI14 H1</th><th>48 giờ gần nhất</th></tr></thead><tbody>';
 for(const s of j.ds){if(s.loi){h+=`<tr><td><b>${esc(s.ma)}</b><small>${esc(s.ten)}</small></td><td>${esc(s.nhom)}</td><td colspan="6" class="small">Không đọc được: ${esc(s.loi)}</td></tr>`;continue}
  const x=s.xu_huong||{},d=s.doi_ngay;h+=`<tr class="${s.la_vang?'vang':''}"><td><a href="/bieu-do${s.la_vang?'':'?ma='+encodeURIComponent(s.ma)}">${esc(s.ma)}</a><small>${esc(s.ten)}${s.tuoi_phut>60?' · giá cũ '+(s.tuoi_phut>=120?Math.round(s.tuoi_phut/60)+' giờ':s.tuoi_phut+' phút'):''}</small></td>
   <td>${esc(s.nhom)}</td><td class="r"><b>${so(s.bid,s.so_le)}</b></td><td class="r"><span class="${d>0?'gain':d<0?'loss':''}">${d==null?'—':(d>0?'+':d<0?'−':'')+so(Math.abs(d),2)+'%'}</span></td>
   <td>${xh('D1',x.D1)}${xh('H4',x.H4)}${xh('H1',x.H1)}</td><td class="r">${so(s.atr_h1,s.so_le)}<small>${so(s.atr_pct,2)}% giá</small></td><td class="r">${so(s.rsi_h1,1)}</td><td>${tia(s.tia)}</td></tr>`}
 el.innerHTML=h+'</tbody></table></div><p class="small">"So với hôm trước" là giá hiện tại so với giá đóng cửa của nến ngày gần nhất. Xu hướng là EMA20 so với EMA50 trên từng khung. Muốn thêm mã, thêm mã đó vào Market Watch trong MT5.</p>'})
.catch(()=>{el.innerHTML='<p class="small">Không đọc được danh sách mã lúc này.</p>'})})();
"""


CSS += """
.ttl{display:flex;flex-wrap:wrap;align-items:center;gap:6px 14px;margin:10px 0 0;padding:8px 14px;border:1px solid var(--line);border-radius:8px;background:var(--card);font-size:12.5px;
color:var(--ink2);text-decoration:none}.ttl[hidden]{display:none}.ttl:hover,.ttl:focus-visible{border-color:var(--mute);outline:none}.ttl b{color:var(--ink)}
.cham{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;vertical-align:0;background:var(--gain)}.cham.chu_y{background:#d9a300}.cham.loi{background:var(--loss)}
.ttm{display:grid;grid-template-columns:minmax(190px,280px) 1fr;gap:2px 22px;padding:10px 0;border-bottom:1px solid var(--line);font-size:13px}.ttm:last-child{border-bottom:0}
.ttm b{font-weight:700}.ttm span{color:var(--ink2)}.ttm small{display:block;color:var(--mute);font-size:12.5px;margin-top:2px}
@media(max-width:760px){.ttm{grid-template-columns:minmax(0,1fr)}}
"""

JS += """
(()=>{const el=document.getElementById('tt-he-thong');if(!el)return;const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])),
ten={tot:'tốt',chu_y:'cần xem',loi:'đang lỗi'};
fetch('/api/tinh-trang',{cache:'no-store'}).then(r=>{if(!r.ok)throw 0;return r.json()}).then(j=>{const d=j.dem||{},dong=document.getElementById('tt-dong');
 el.innerHTML=(j.muc||[]).map(m=>`<div class="ttm"><b><i class="cham ${m.muc}"></i>${esc(m.ten)}</b><span>${esc(m.chi_tiet)}${m.lam?`<small>${esc(m.lam)}</small>`:''}</span></div>`).join('')||'<p class="small">Chưa có mục nào.</p>';
 if(dong){const xau=(j.muc||[]).filter(m=>m.muc!=='tot');
  dong.innerHTML=`<b>Tình trạng hệ thống</b><span><i class="cham"></i>${d.tot||0} ${ten.tot}</span>`+(d.chu_y?`<span><i class="cham chu_y"></i>${d.chu_y} ${ten.chu_y}</span>`:'')+(d.loi?`<span><i class="cham loi"></i>${d.loi} ${ten.loi}</span>`:'')
   +(xau.length?`<span>${esc(xau.map(m=>m.ten).slice(0,3).join(', '))}${xau.length>3?'…':''}</span>`:'<span>Mọi nguồn dữ liệu đều đang chạy đúng.</span>');dong.hidden=false}})
.catch(()=>{el.innerHTML='<p class="small">Không soát được tình trạng lúc này.</p>'})})();
"""


# ------------------------------------------------------------------ thanh điều hướng (đổi ngày 24/11/2026, lượt ba)
# Một thanh cao 56 px cho mọi trang: logo, sáu mục (ba mục có menu thả xuống), ô tìm nhanh Ctrl+K, nút nền sáng/tối, nút ☰ trên màn hình hẹp.
CSS += r"""
:root{--nv-h:56px}
.nv{position:sticky;top:0;z-index:30;background:color-mix(in srgb,var(--bg) 86%,transparent);backdrop-filter:blur(14px) saturate(1.4);-webkit-backdrop-filter:blur(14px) saturate(1.4);border-bottom:1px solid var(--line)}
.nv-in{max-width:1520px;margin:0 auto;height:var(--nv-h);padding:0 20px;display:flex;align-items:center;gap:6px}
.nv .ic{width:18px;height:18px;flex:none}
.nv-logo{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink);margin-right:18px;flex:none}
.nv-mk{width:32px;height:32px;border-radius:9px;display:grid;place-items:center;color:var(--btn-ink);background:linear-gradient(324deg,var(--accent2) 0%,var(--series) 70%);
box-shadow:0 0 0 1px color-mix(in srgb,var(--series) 35%,transparent),0 6px 18px -8px var(--series)}
.nv-mk .ic{width:18px;height:18px;stroke-width:2.4}
.nv-tn{display:flex;flex-direction:column;line-height:1.1}.nv-tn b{font-size:14.5px;font-weight:700;letter-spacing:-.01em}
.nv-tn small{font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--mute);font-weight:600}
.nv-chinh{display:flex;align-items:center;gap:2px;height:100%}
.nv-a{position:relative;display:inline-flex;align-items:center;gap:4px;height:36px;padding:0 12px;border-radius:9px;border:0;background:none;color:var(--ink2);
font:500 13.5px/1 inherit;font-family:inherit;text-decoration:none;cursor:pointer;white-space:nowrap}
.nv-a:hover,.nv-g.mo>.nv-a{color:var(--ink);background:color-mix(in srgb,var(--ink) 6%,transparent)}
.nv-a[aria-current=page],.nv-a.on{color:var(--ink);font-weight:600}
.nv-a[aria-current=page]::after,.nv-a.on::after{content:"";position:absolute;left:12px;right:12px;bottom:-10px;height:2px;border-radius:2px;background:linear-gradient(90deg,var(--series),var(--accent2))}
.nv-x{width:14px!important;height:14px!important;opacity:.6;transition:transform .15s}.nv-g.mo .nv-x{transform:rotate(180deg)}
.nv-g{position:relative}
.nv-m{position:absolute;top:calc(100% + 10px);left:-8px;min-width:300px;padding:8px;background:var(--card);border:1px solid var(--line);border-radius:14px;
box-shadow:0 18px 50px -12px rgba(0,0,0,.45),0 2px 6px rgba(0,0,0,.12);display:grid;gap:2px;opacity:0;visibility:hidden;transform:translateY(-4px);transition:opacity .14s,transform .14s,visibility .14s}
.nv-g.rong .nv-m{grid-template-columns:1fr 1fr;min-width:560px}
.nv-g.mo .nv-m{opacity:1;visibility:visible;transform:none}
.nv-m::before{content:"";position:absolute;left:0;right:0;top:-12px;height:12px}
.nv-i{display:flex;gap:11px;align-items:flex-start;padding:9px 10px;border-radius:10px;color:var(--ink);text-decoration:none}
.nv-i:hover,.nv-i:focus-visible{background:color-mix(in srgb,var(--series) 10%,transparent);outline:none}
.nv-i .ic{margin-top:1px;padding:7px;width:32px!important;height:32px!important;border-radius:9px;background:var(--card2);border:1px solid var(--line);color:var(--series)}
.nv-i b{display:block;font-size:13.5px;font-weight:600}.nv-i small{display:block;font-size:12px;color:var(--mute);margin-top:2px;line-height:1.35}
.nv-phai{margin-left:auto;display:flex;align-items:center;gap:8px}
.nv-tim-b{display:inline-flex;align-items:center;gap:8px;height:36px;padding:0 8px 0 11px;min-width:210px;border-radius:10px;border:1px solid var(--line);background:var(--card2);
color:var(--mute);font:500 13px inherit;font-family:inherit;cursor:pointer}
.nv-tim-b span{flex:1;text-align:left}.nv-tim-b:hover{border-color:color-mix(in srgb,var(--ink) 25%,var(--line));color:var(--ink2)}
.nv kbd,.nv-tim kbd{font:600 10.5px/1 inherit;font-family:inherit;color:var(--mute);border:1px solid var(--line);border-bottom-width:2px;border-radius:5px;padding:3px 5px;background:var(--card)}
.nv-phai #theme,.nv-phai #refresh{height:36px;min-height:36px;width:36px;padding:0;font-size:0;gap:0;border-radius:10px;background:var(--card2);border:1px solid var(--line);color:var(--ink2);cursor:pointer;
display:inline-flex;align-items:center;justify-content:center;box-shadow:none}
.nv-phai #theme::before,.nv-phai #refresh::before{width:16px;height:16px}
.nv-phai #theme:hover,.nv-phai #refresh:hover{color:var(--ink);border-color:color-mix(in srgb,var(--ink) 25%,var(--line))}
.nv-lang{height:36px;min-width:40px;padding:0 9px;border-radius:10px;border:1px solid var(--line);background:var(--card2);color:var(--ink);font:700 12px/1 inherit;font-family:inherit;
letter-spacing:.06em;cursor:pointer}.nv-lang:hover{border-color:var(--series);color:var(--series)}
.nv-mb{display:none;height:36px;width:36px;border-radius:10px;border:1px solid var(--line);background:var(--card2);color:var(--ink);cursor:pointer;align-items:center;justify-content:center}
.nv-ngan{border-top:1px solid var(--line);padding:8px 12px 14px;max-height:calc(100vh - var(--nv-h));overflow:auto;background:var(--bg)}
.nv-ngan[hidden]{display:none}
.nv-dh{margin:12px 8px 4px;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--mute);font-weight:700}
.nv-d{display:flex;flex-direction:row-reverse;justify-content:flex-end;align-items:center;gap:12px;padding:11px 10px;border-radius:10px;color:var(--ink);text-decoration:none;font-size:14.5px}
.nv-d .ic{color:var(--series)}.nv-d[aria-current=page],.nv-d:hover{background:color-mix(in srgb,var(--series) 10%,transparent)}.nv-d[aria-current=page]{font-weight:600}
.nv-i[aria-current=page]{background:color-mix(in srgb,var(--series) 8%,transparent)}
html.nv-khoa{overflow:hidden}
.nv .subnav{border-top:1px solid var(--line);background:transparent}.nv .subnav>div{max-width:1520px;padding:0 20px}.nv .subnav a{display:inline-block;padding:8px 0;color:var(--mute);text-decoration:none}
.nv .subnav a:hover{color:var(--ink)}
.tt-tabs{top:var(--nv-h)}
@media(max-width:1180px){.nv-tim-b{min-width:0}.nv-tim-b span,.nv-tim-b kbd{display:none}.nv-tn small{display:none}.nv-logo{margin-right:8px}.nv-a{padding:0 9px}}
@media(max-width:960px){.nv-chinh{display:none}.nv-mb{display:inline-flex}.nv-in{padding:0 12px}.nv .subnav>div{padding:0 12px}}
@media(max-width:420px){.nv-tn b{font-size:13px}}
/* điện thoại: vùng bấm tối thiểu 24 px cho liên kết trong bảng và ô đánh dấu (WCAG 2.5.8) */
@media(max-width:640px){:root td a{display:inline-block;padding:4px 0;min-height:24px}
:root input[type=checkbox]{width:18px;height:18px;margin:3px}}
/* ô tìm nhanh */
.nv-tim{position:fixed;inset:0;z-index:60;background:rgba(5,6,4,.55);backdrop-filter:blur(3px);display:flex;justify-content:center;align-items:flex-start;padding:10vh 16px 16px}
.nv-tim[hidden]{display:none}
.nv-hop{width:min(640px,100%);background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:0 30px 80px -20px rgba(0,0,0,.6);overflow:hidden;display:flex;flex-direction:column;max-height:76vh}
.nv-o{display:flex;align-items:center;gap:10px;padding:0 14px;border-bottom:1px solid var(--line)}
.nv-o .ic{width:20px;height:20px;color:var(--mute)}
.nv-o input{flex:1;height:54px;border:0;background:none;color:var(--ink);font:500 16px inherit;font-family:inherit;outline:none}
.nv-kq{overflow:auto;padding:6px}
.nv-kq h6{margin:10px 10px 4px;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--mute)}
.nv-r{display:flex;align-items:center;gap:12px;padding:9px 10px;border-radius:10px;color:var(--ink);text-decoration:none;cursor:pointer}
.nv-r[aria-selected=true]{background:color-mix(in srgb,var(--series) 12%,transparent)}
.nv-r .ic{width:18px;height:18px;color:var(--series);flex:none}
.nv-r .nv-l{font-style:normal;font-size:10.5px;font-weight:700;color:var(--ink2);background:var(--card2);border:1px solid var(--line);border-radius:6px;padding:2px 6px;white-space:nowrap;min-width:92px;text-align:center}
.nv-r span{flex:1;min-width:0}.nv-r b{font-size:14px}.nv-r small{display:block;font-size:12px;color:var(--mute);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nv-r em{font-style:normal;font-size:11.5px;color:var(--mute);white-space:nowrap}
.nv-goi{display:flex;gap:14px;flex-wrap:wrap;padding:9px 14px;border-top:1px solid var(--line);font-size:11.5px;color:var(--mute)}
.nv-rong{padding:22px;text-align:center;color:var(--mute);font-size:13px}
@media(prefers-reduced-motion:reduce){.nv-m{transition:none}}
"""

JS += r"""
(()=>{const H=document.querySelector('header.nv');if(!H)return;
const gs=[...H.querySelectorAll('.nv-g')],dat=(g,m)=>{g.classList.toggle('mo',m);g.querySelector('button').setAttribute('aria-expanded',m)},dong=()=>gs.forEach(g=>dat(g,false));
const hover=matchMedia('(hover:hover) and (pointer:fine)').matches;
gs.forEach(g=>{const b=g.querySelector('button');let t;b.addEventListener('click',e=>{e.stopPropagation();const m=!g.classList.contains('mo');dong();dat(g,m)});
 if(hover){g.addEventListener('mouseenter',()=>{clearTimeout(t);gs.forEach(x=>x!==g&&dat(x,false));dat(g,true)});g.addEventListener('mouseleave',()=>{t=setTimeout(()=>dat(g,false),200)})}
 g.addEventListener('keydown',e=>{if(e.key==='Escape'){dat(g,false);b.focus()}});g.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>dat(g,false)))});
document.addEventListener('click',e=>{if(!e.target.closest('.nv-g'))dong()});
const mb=H.querySelector('.nv-mb'),ng=H.querySelector('.nv-ngan'),moNgan=m=>{ng.hidden=!m;mb.setAttribute('aria-expanded',m);document.documentElement.classList.toggle('nv-khoa',m)};
mb.addEventListener('click',()=>moNgan(ng.hidden));ng.addEventListener('click',e=>{if(e.target.closest('a'))moNgan(false)});
addEventListener('resize',()=>{if(innerWidth>960&&!ng.hidden)moNgan(false)});
// ---- ô tìm nhanh: Ctrl+K hoặc phím /
const TRANG=JSON.parse(H.dataset.tim||'[]'),IC={};H.querySelectorAll('.nv-i,.nv-d').forEach(a=>{const s=a.querySelector('svg');if(s)IC[a.getAttribute('href')]=s.outerHTML});
const bo=s=>String(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/đ/g,'d').replace(/Đ/g,'D').toLowerCase();
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let MA=null,LOP={},hop=null,ds=[],chon=0;
const napMa=()=>MA?Promise.resolve():fetch('/api/thi-truong/ma',{cache:'no-store'}).then(r=>r.json()).then(j=>{MA=j.ds||[];LOP=j.lop||{}}).catch(()=>{MA=[]});
function tao(){hop=document.createElement('div');hop.className='nv-tim';hop.hidden=true;hop.setAttribute('role','dialog');hop.setAttribute('aria-modal','true');hop.setAttribute('aria-label','Tìm nhanh');
 hop.innerHTML=`<div class="nv-hop"><div class="nv-o">${H.querySelector('.nv-tim-b svg').outerHTML}<input type="text" placeholder="Tìm mã (EURUSD, vàng, nasdaq…) hoặc trang (pivot, ký quỹ…)" aria-label="Tìm" autocomplete="off" spellcheck="false"><kbd>Esc</kbd></div><div class="nv-kq" role="listbox"></div><div class="nv-goi"><span>↑ ↓ chọn</span><span>Enter mở biểu đồ</span><span>Shift + Enter mở công cụ tính</span></div></div>`;
 document.body.appendChild(hop);const ip=hop.querySelector('input');hop.addEventListener('click',e=>{if(e.target===hop)dongTim()});
 ip.addEventListener('input',()=>{chon=0;ve(ip.value)});
 ip.addEventListener('keydown',e=>{if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();chon=(chon+(e.key==='ArrowDown'?1:-1)+ds.length)%Math.max(1,ds.length);danh()}
  else if(e.key==='Enter'){e.preventDefault();const x=ds[chon];if(x){dongTim();location.href=e.shiftKey&&x.h2?x.h2:x.h}}else if(e.key==='Escape'){e.preventDefault();dongTim()}})}
function danh(){hop.querySelectorAll('.nv-r').forEach((r,i)=>{r.setAttribute('aria-selected',i===chon);if(i===chon)r.scrollIntoView({block:'nearest'})})}
function ve(q){const k=bo(q).trim(),el=hop.querySelector('.nv-kq');ds=[];
 const tr=TRANG.filter(p=>!k||bo(p.t+' '+p.m).includes(k)).slice(0,k?6:9).map(p=>({h:p.h,html:`${IC[p.h]||''}<span><b>${esc(p.t)}</b>${p.m?`<small>${esc(p.m)}</small>`:''}</span><em>Trang</em>`}));
 let ma=[];if(MA&&k){ma=MA.map(x=>{const g=bo(x.goc),t=bo((x.biet_danh||'')+' '+x.ten+' '+x.ma);const d=g===k?0:g.startsWith(k)?1:g.includes(k)?2:t.includes(k)?3:9;return{x,d}}).filter(a=>a.d<9).sort((a,b)=>a.d-b.d||a.x.goc.localeCompare(b.x.goc)).slice(0,8)}
 const mm=ma.map(({x})=>({h:'/bieu-do?ma='+encodeURIComponent(x.ma),h2:'/cong-cu?ma='+encodeURIComponent(x.ma),html:`<i class="nv-l">${esc(LOP[x.lop]||x.lop)}</i><span><b>${esc(x.goc)}</b><small>${esc(x.biet_danh?x.biet_danh+' · '+x.ten:x.ten)}</small></span><em>Biểu đồ ↵</em>`}));
 ds=mm.concat(tr);let h='';if(mm.length)h+='<h6>Mã giao dịch</h6>'+mm.map((x,i)=>`<a class="nv-r" role="option" href="${x.h}" data-i="${i}">${x.html}</a>`).join('');
 if(tr.length)h+='<h6>Trang và công cụ</h6>'+tr.map((x,i)=>`<a class="nv-r" role="option" href="${x.h}" data-i="${i+mm.length}">${x.html}</a>`).join('');
 el.innerHTML=h||`<div class="nv-rong">${MA===null?'Đang nạp danh sách mã…':'Không thấy mã hay trang nào khớp “'+esc(q)+'”.'}</div>`;
 el.querySelectorAll('.nv-r').forEach(r=>{r.addEventListener('mousemove',()=>{const i=+r.dataset.i;if(i!==chon){chon=i;danh()}});r.addEventListener('click',()=>dongTim())});danh()}
function moTim(){if(!hop)tao();dong();if(!ng.hidden)moNgan(false);hop.hidden=false;document.documentElement.classList.add('nv-khoa');const ip=hop.querySelector('input');ip.value='';chon=0;ve('');ip.focus();napMa().then(()=>{if(!hop.hidden)ve(ip.value)})}
function dongTim(){if(hop){hop.hidden=true;document.documentElement.classList.remove('nv-khoa')}}
H.querySelector('.nv-tim-b').addEventListener('click',moTim);
// ---- chuyển ngôn ngữ: nhớ trong cookie `lang`, máy chủ dịch trang theo cookie
const LG=document.getElementById('nv-lang'),lgNay=document.documentElement.lang==='en'?'en':'vi';
if(LG){LG.textContent=lgNay==='en'?'VI':'EN';LG.setAttribute('aria-label',lgNay==='en'?'Chuyển sang tiếng Việt':'Switch to English');
 LG.addEventListener('click',()=>{const m=lgNay==='en'?'vi':'en';document.cookie='lang='+m+';path=/;max-age=31536000;samesite=lax';
  const u=new URL(location.href);u.searchParams.delete('lang');location.replace(u.pathname+u.search+u.hash)})}
addEventListener('keydown',e=>{const go=/^(INPUT|TEXTAREA|SELECT)$/.test((e.target&&e.target.tagName)||'')||(e.target&&e.target.isContentEditable);
 if((e.ctrlKey||e.metaKey)&&(e.key==='k'||e.key==='K')){e.preventDefault();hop&&!hop.hidden?dongTim():moTim()}else if(e.key==='/'&&!go&&!e.ctrlKey&&!e.metaKey){e.preventDefault();moTim()}})})();
"""


class _Mod(types.ModuleType):
    """`trang.MIEN_TRU` là câu miễn trừ của luồng đang chạy. Gán câu gốc (như các bài kiểm làm khi xong) là trả luồng về câu gốc."""

    @property
    def MIEN_TRU(self) -> str:                                            # noqa: N802 - giữ tên cũ cho các trang đang dùng
        return mien_tru()

    @MIEN_TRU.setter
    def MIEN_TRU(self, v: str) -> None:                                   # noqa: N802
        chia_se_luot(v == MIEN_TRU_CHIA_SE)


sys.modules[__name__].__class__ = _Mod
