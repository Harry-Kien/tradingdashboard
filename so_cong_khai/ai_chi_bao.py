"""AI đọc các chỉ báo người dùng đang bật trên trang Biểu đồ (yêu cầu của chủ dự án, 26/11/2026).

Trang gửi lên số cuối của từng chỉ báo đang bật (giá trị nến đã đóng gần nhất và nến trước đó), các mũi tên mua bán gần nhất và 60 nến đã đóng.
Claude (claude-opus-5-5) đọc lại: bức tranh chung, chỉ báo nào đồng thuận hay mâu thuẫn, các kịch bản vào lệnh CÓ ĐIỀU KIỆN kèm mức vô hiệu,
và điều cần chú ý. Chỉ dùng số được gửi lên; không hứa tỷ lệ thắng.

Dùng chung chốt chặn với nút "Hỏi AI" (ai_hoi.trang_thai): cấu hình ai.bat, ai.moi_ngay, ai.ngan_sach_usd, phải có khóa API và giá trực tiếp.
Mỗi lượt ghi vào cùng sổ out/ai-hoi.jsonl (loai = "doc_chi_bao"), nên số lượt và tiền tính chung. Không đặt lệnh, không phải lời khuyên đầu tư."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from . import ai_hoi, gia, gia_su

LOAI = 'doc_chi_bao'
KHUNG = tuple(gia.KHUNG)                                  # mọi khung của biểu đồ, kể cả khung chỉ để xem (M2…MN1)
TOI_DA_CB, TOI_DA_NEN = 25, 80
MIEN_TRU = {'vi': 'Đây là cách đọc của một mô hình AI trên các chỉ báo bạn chọn, chưa được kiểm chứng bằng số liệu, không phải lời khuyên đầu tư. Trang này không đặt lệnh.',
            'en': 'This is an AI model reading the indicators you chose. It has not been validated with data and is not investment advice. This page never places orders.'}

HE_THONG = """You read technical indicators for a retail trader who looks at a chart of {ma} on the {tf} timeframe.
The trader turned these indicators on themselves. You get, for each one, its value on the last CLOSED candle and on the candle before it,
plus its most recent buy/sell arrows (how many candles ago). You also get the last closed candles (time UTC, open, high, low, close).

Write in {ngon_ngu}, plain words, at most 380 words, with these short sections:
1. The overall picture: trend, momentum, volatility, using only the numbers given.
2. Where the indicators agree and where they conflict. Name the indicators.
3. Conditional entry scenarios (one for each direction that makes sense, or say "stand aside" if the picture is mixed): what must happen first
   (for example a close above a level), a reference stop beyond a level taken from the data, and what invalidates the scenario.
   Use price levels that come from the candles or indicator values given; never invent numbers.
4. What to watch: anything that could make these readings unreliable (low sample, ranging market, tick volume is not real volume, news).

Rules: never promise or estimate a win rate or profit. Do not tell the trader to buy or sell now; describe conditions only.
These indicators have not been validated on this market, so say so briefly if the trader seems to rely on one of them alone.
Do not add a disclaimer at the end; the page adds one."""


def _so(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def lam_sach(body: dict) -> dict:
    """Kiểm tra và cắt gọn dữ liệu trang gửi lên. Sai dạng thì ValueError."""
    tf = str(body.get('tf') or '')
    if tf not in KHUNG:
        raise ValueError('khung không hợp lệ')
    ma = str(body.get('ma') or 'XAUUSD')[:24]
    cb = []
    for x in (body.get('chi_bao') or [])[:TOI_DA_CB]:
        if not isinstance(x, dict):
            continue
        gt = {str(k)[:30]: [_so(a) for a in (v if isinstance(v, list) else [v])][:2] for k, v in list((x.get('gia_tri') or {}).items())[:6]}
        dau = [{'chieu': 'MUA' if d.get('len') else 'BAN', 'cach_nen': int(d.get('cach') or 0)} for d in (x.get('dau') or [])[:4] if isinstance(d, dict)]
        tham = {str(k)[:12]: _so(v) for k, v in list((x.get('tham_so') or {}).items())[:6]}
        cb.append({'ten': str(x.get('ten') or '')[:80], 'tham_so': tham, 'gia_tri': gt, 'dau_gan': dau})
    if not cb:
        raise ValueError('chưa bật chỉ báo nào')
    nen = []
    for r in (body.get('nen') or [])[-TOI_DA_NEN:]:
        if isinstance(r, list) and len(r) >= 5 and all(_so(v) is not None for v in r[:5]):
            nen.append([int(r[0])] + [_so(v) for v in r[1:5]])
    if len(nen) < 20:
        raise ValueError('thiếu nến')
    return {'tf': tf, 'ma': ma, 'chi_bao': cb, 'nen': nen, 'lang': 'en' if body.get('lang') == 'en' else 'vi'}


def _noi_dung(d: dict) -> str:
    dong = ['time_utc,open,high,low,close'] + [
        f"{datetime.fromtimestamp(r[0], timezone.utc):%Y-%m-%d %H:%M},{r[1]},{r[2]},{r[3]},{r[4]}" for r in d['nen']]
    return ('Indicators (value on last closed candle, value one candle before):\n' + json.dumps(d['chi_bao'], ensure_ascii=False)
            + '\n\nLast closed candles:\n' + '\n'.join(dong))


def hoi(cfg: dict, out: Path, body: dict, client=None, now: datetime | None = None) -> dict:
    """Một lượt AI đọc chỉ báo. `client` chỉ để bài kiểm thay bằng Claude giả."""
    now = now or datetime.now(timezone.utc)
    try:
        d = lam_sach(body)
    except ValueError as e:
        return {'ok': False, 'chan': [f'Dữ liệu chưa đủ: {e}.']}
    st = ai_hoi.trang_thai(cfg, out, now)
    chan = [c for c in st['chan'] if client is None or 'khóa API' not in c]
    if chan:
        return {'ok': False, 'chan': chan}
    try:
        if client is None:
            import anthropic                                       # noqa: PLC0415 - chỉ nạp khi người dùng bấm
            client = anthropic.Anthropic(max_retries=2, timeout=120.0)
        r = client.beta.messages.create(
            model=gia_su.MODEL, max_tokens=1800, output_config={'effort': 'medium'}, betas=['server-side-fallback-2026-07-01'], fallbacks='default',
            system=HE_THONG.format(ma=d['ma'], tf=d['tf'], ngon_ngu='English' if d['lang'] == 'en' else 'Vietnamese'),
            messages=[{'role': 'user', 'content': _noi_dung(d)}])
    except Exception as e:                                         # noqa: BLE001 - lỗi mạng, khóa sai: báo, không làm hỏng webapp
        return {'ok': False, 'chan': [gia_su._loi(e).replace('gia sư', 'AI')]}
    phi = gia_su._phi(getattr(r, 'usage', None))
    chu = '\n\n'.join(b.text for b in r.content if getattr(b, 'type', '') == 'text').strip()
    if r.stop_reason == 'refusal' or not chu:
        chu = ''
    rec = {'luc': now.isoformat(), 'loai': LOAI, 'model': getattr(r, 'model', gia_su.MODEL), 'chi_phi_usd': phi, 'tf': d['tf'], 'ma': d['ma'],
           'chi_bao': [x['ten'] for x in d['chi_bao']], 'dung': getattr(r, 'stop_reason', None)}
    out.mkdir(parents=True, exist_ok=True)
    with (out / 'ai-hoi.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    if not chu:
        return {'ok': False, 'chan': ['Mô hình không trả lời lượt này; thử lại sau.'], 'chi_phi_usd': phi}
    if r.stop_reason == 'max_tokens':
        chu += '\n\n(Câu trả lời bị cắt vì quá dài.)' if d['lang'] == 'vi' else '\n\n(The answer was cut because it was too long.)'
    return {'ok': True, 'tra_loi': chu, 'mien_tru': MIEN_TRU[d['lang']], 'chi_phi_usd': phi, 'trang_thai': ai_hoi.trang_thai(cfg, out, now)}
