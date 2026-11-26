"""AI phân tích điểm vào lệnh theo yêu cầu, dùng đúng bộ máy của dự án EA Promax:
ai.snapshot (ảnh chụp thị trường) -> ai.analyst (hỏi Claude, lời nhắc v3) -> ai.validator (kiểm tra câu trả lời).

Chỉ chạy khi người dùng bấm nút. Mỗi lượt hỏi tốn tiền API của chủ dự án, nên có ba chốt chặn: phải có giá trực tiếp còn
mới, không quá số lượt mỗi ngày, và không quá ngân sách riêng của webapp. Mọi lượt hỏi được ghi vào sổ out/ai-hoi.jsonl.
Mô-đun này không đặt lệnh. Kết quả là ý kiến của một mô hình, không phải lời khuyên đầu tư."""
from __future__ import annotations

import json
import threading
from functools import wraps
import os
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import song
from .doc_so import VN

SO_NEN = {'M5': 300, 'M15': 500, 'M30': 300, 'H1': 1000, 'H4': 1000, 'D1': 60}       # như BARS_TO_FETCH của vòng chạy bóng
GIA_MOI_GIAY = 120
UOC_TINH_USD = 0.08                                                                       # theo VAN_HANH_NHANH.md của dự án


_luot_hoi = threading.Lock()


def gioi_han_dong_thoi(fn):
    """Giữ chốt từ kiểm hạn mức tới ghi chi phí: hai tab không tiêu cùng một lượt còn lại."""
    @wraps(fn)
    def goi(*args, **kwargs):
        if not _luot_hoi.acquire(blocking=False):
            ly_do = 'Đang có một lượt AI xử lý; chờ xong rồi gửi tiếp.'
            return {'ok': False, 'chan': [ly_do], 'ly_do': ly_do}
        try:
            return fn(*args, **kwargs)
        finally:
            _luot_hoi.release()
    return goi


def _so(out: Path) -> Path:
    return out / 'ai-hoi.jsonl'


def doc_so(out: Path) -> list[dict]:
    p = _so(out)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]


def co_khoa() -> bool:
    """Chỉ kiểm tra CÓ khóa hay không; không đọc giá trị của khóa."""
    return bool(os.environ.get('ANTHROPIC_API_KEY')) or (Path.home() / '.config' / 'anthropic').exists()


def trang_thai(cfg: dict, out: Path, now: datetime | None = None) -> dict:
    a = cfg.get('ai') or {}
    now = now or datetime.now(timezone.utc)
    recs = doc_so(out)
    today = now.astimezone(VN).date()
    hom_nay = sum(datetime.fromisoformat(r['luc']).astimezone(VN).date() == today for r in recs)
    da_tieu = sum(float(r.get('chi_phi_usd') or 0) for r in recs)
    toi_da, ngan_sach = int(a.get('moi_ngay', 5)), float(a.get('ngan_sach_usd', 5))
    chan = []
    if not a.get('bat'):
        chan.append('Phần AI đang tắt trong cấu hình.')
    if not co_khoa():
        chan.append('Chưa có khóa API của Anthropic trên máy này (đặt biến ANTHROPIC_API_KEY như hướng dẫn trong HUONG_DAN.md, mục Tính năng tùy chọn).')
    if song.ly_do() is not None:
        chan.append(f'Chưa có giá trực tiếp từ MT5: {song.ly_do()}.')
    if hom_nay >= toi_da:
        chan.append(f'Đã hỏi đủ {toi_da} lượt hôm nay.')
    if da_tieu + UOC_TINH_USD > ngan_sach:
        chan.append(f'Đã chạm ngân sách {ngan_sach:.2f} USD của webapp.')
    return {'hom_nay': hom_nay, 'moi_ngay': toi_da, 'da_tieu_usd': round(da_tieu, 4), 'ngan_sach_usd': ngan_sach,
            'uoc_tinh_usd': UOC_TINH_USD, 'chan': chan, 'gan_day': [r for r in recs if r.get('loai') != 'doc_chi_bao'][-5:][::-1]}   # lượt "AI đọc chỉ báo" tính chung lượt và tiền, không hiện ở đây


def _dict(o) -> dict:
    if o is None:
        return {}
    if hasattr(o, 'model_dump'):
        return o.model_dump()
    if is_dataclass(o):
        return asdict(o)
    return dict(o)


@gioi_han_dong_thoi
def hoi(cfg: dict, out: Path, analyze=None, now: datetime | None = None, khung_song=None) -> dict:
    """Một lượt hỏi AI. `analyze` và `khung_song` chỉ để bài kiểm thay thế; mặc định là hàm thật của dự án."""
    g = cfg['gia']
    now = now or datetime.now(timezone.utc)
    fr = (khung_song or song.khung_song)(g)
    st = trang_thai(cfg, out, now)
    chan = [c for c in st['chan'] if analyze is None or 'khóa API' not in c]
    if fr is None or fr.get('nguon') != 'mt5':
        chan = chan or ['Chưa có giá trực tiếp từ MT5.']
    elif 'bid' not in fr or (now - fr['het']).total_seconds() > GIA_MOI_GIAY:
        chan.append('Giá từ MT5 đã cũ hơn 2 phút (thị trường nghỉ hoặc MT5 mất kết nối): không hỏi AI trên giá cũ.')
    if fr is not None and fr.get('nguon') == 'mt5':
        chan = [c for c in chan if 'Chưa có giá trực tiếp' not in c]
    if chan:
        return {'ok': False, 'chan': chan}
    for p in g.get('ma_nguon', []):
        if os.path.expandvars(p) not in sys.path:
            sys.path.insert(0, os.path.expandvars(p))
    from ai import analyst, snapshot as SN, validator as V          # noqa: PLC0415
    bars = {tf: fr[tf].iloc[-n:].reset_index() for tf, n in SO_NEN.items()}
    news = SN.load_high_usd_news(Path(os.path.expandvars(g['lich_tin'])))[0] if g.get('lich_tin') else None
    snap = SN.build_swing_snapshot(bars, fr['bid'], fr['ask'], news, now, None)
    res = (analyze or analyst.analyze)(SN.render_swing(snap))
    rec = {'luc': now.isoformat(), 'loai': res.kind, 'model': getattr(res, 'model_served', None), 'chi_phi_usd': getattr(res, 'cost_usd', None),
           'bid': fr['bid'], 'ask': fr['ask'], 'anh_chup_sha': SN.snapshot_sha(snap), 'loi': getattr(res, 'error', None)}
    if res.kind == 'signal' and res.signal is not None:
        atr = snap.get('atr_thuoc_do') or float((fr['M30']['high'] - fr['M30']['low']).iloc[-14:].mean())
        v = V.validate(res.signal, V.Market(fr['bid'], fr['ask'], float(atr), float(fr['M15']['close'].iloc[-1])))
        rec['tin_hieu'] = _dict(res.signal)
        rec['kiem_tra'] = {k: (list(x) if isinstance(x, tuple) else x) for k, x in _dict(v).items()}
    out.mkdir(parents=True, exist_ok=True)
    with _so(out).open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + '\n')
    return {'ok': True, 'ket_qua': rec, 'het_han': (now + timedelta(minutes=int((rec.get('tin_hieu') or {}).get('hieu_luc_phut') or 0))).isoformat()}
