"""Lõi nghiệp vụ dùng chung cho giao diện, API, AI giải thích và MCP (27/11/2026). Mọi phép tính giá, lot, RR, rủi ro và thống kê nằm ở đây
hoặc ở các mô-đun nó gọi; AI chỉ đọc kết quả, không tự tính.

- `chup`: ảnh chụp thị trường có cấu trúc cho đúng mã, khung và thời điểm, có `id` (SN-…) tính từ nội dung. Tách nến đã đóng với nến đang
  chạy. Mỗi sự kiện là một bằng chứng có `id` (E…) để câu trả lời dẫn chiếu. Ảnh chụp được giữ lại (bộ nhớ + out/ai/anh-chup) để mọi lần
  đọc trong một phân tích dùng cùng một thời điểm, không trộn.
- `dieu_kien`: điều kiện của một phương pháp trong ảnh chụp.
- `ke_hoach_rui_ro`: kiểm rủi ro một phiếu kế hoạch (kiem_lenh.kiem).
- `bang_chung_phuong_phap`: mô tả thống kê, phiên bản, phạm vi của phương pháp (báo cáo đóng băng như Harrison ghi rõ là đóng băng).
- `tong_ket_review`: thống kê sổ phiếu: kết quả mô phỏng tách khỏi việc làm đúng kế hoạch.
Không có hàm nào đặt, sửa hay đóng lệnh."""
from __future__ import annotations

import hashlib
import json
import math
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

CHI_BAO = (('ema20', 'EMA20'), ('ema50', 'EMA50'), ('ema200', 'EMA200'), ('rsi', 'RSI14'), ('atr14', 'ATR14'), ('macd', 'MACD'), ('macd_tin', 'MACD tín hiệu'),
           ('stoch_k', 'Stochastic %K'), ('stoch_d', 'Stochastic %D'), ('st', 'SuperTrend'), ('bb_tren', 'Bollinger trên'), ('bb_duoi', 'Bollinger dưới'))
_NHO: OrderedDict = OrderedDict()
_khoa = threading.Lock()
TOI_DA_NHO = 60


def _so(x, d: int = 5):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return round(x, d) if math.isfinite(x) else None


def _cuoi(a, n: int):
    """Giá trị tại chỉ số n (nến đã đóng cuối) của một mảng chỉ báo; None nếu thiếu."""
    if not isinstance(a, list) or n < 0 or n >= len(a):
        return None
    return _so(a[n])


def chup(cfg: dict, ma: str = '', tf: str = 'M15', now: datetime | None = None, goi=None, phan_tich_fn=None, thu_muc: Path | None = None) -> dict:
    """Ảnh chụp có cấu trúc. `goi`, `phan_tich_fn` để bài kiểm thay bằng dữ liệu giả."""
    from . import da_ma, gia, phan_tich                                 # noqa: PLC0415 - nạp chậm, tránh vòng nạp
    now = now or datetime.now(timezone.utc)
    vang = not ma or ma == da_ma.ma_vang(cfg)
    D = (goi or (lambda: gia.goi(cfg, tf, 300) if vang else da_ma.goi(cfg, ma, tf, 300)))()
    PT = (phan_tich_fn or (lambda: phan_tich.phan_tich(cfg) if vang else da_ma.phan_tich(cfg, ma)))() if tf else {}
    cs = D.get('candles') or []
    live = D.get('live')
    n_dong = live if isinstance(live, int) and 0 <= live < len(cs) else len(cs)
    dong, chay = cs[:n_dong], (cs[live] if isinstance(live, int) and 0 <= live < len(cs) else None)
    bc, thieu = [], []

    def them(id_, loai, mo_ta, gia_tri):
        bc.append({'id': id_, 'loai': loai, 'mo_ta': mo_ta, 'gia_tri': gia_tri})
    them('E_GIA', 'gia', 'Giá trực tiếp lúc chụp', {'bid': _so(D.get('bid')), 'ask': _so(D.get('ask')), 'nguon': D.get('nguon')})
    if D.get('nguon') != 'mt5':
        thieu.append('Không có giá trực tiếp từ MT5; số liệu lấy từ kho nến' + (f' ({D.get("ly_do_khong_song")})' if D.get('ly_do_khong_song') else ''))
    for k, r in enumerate(dong[-5:][::-1]):
        them(f'E_NEN_{k + 1}', 'nen_da_dong', f'Nến {tf} đã đóng thứ {k + 1} tính từ nến gần nhất',
             {'mo_luc': datetime.fromtimestamp(int(r[0]), timezone.utc).isoformat(), 'mo': _so(r[1]), 'cao': _so(r[2]), 'thap': _so(r[3]), 'dong': _so(r[4])})
    if chay:
        them('E_NEN_CHAY', 'nen_dang_chay', f'Nến {tf} đang chạy (chưa đóng, còn thay đổi)',
             {'mo_luc': datetime.fromtimestamp(int(chay[0]), timezone.utc).isoformat(), 'mo': _so(chay[1]), 'cao': _so(chay[2]), 'thap': _so(chay[3]), 'gia': _so(chay[4])})
    if dong:
        w = dong[-50:]
        them('E_BIEN_50', 'bien', f'Cao nhất và thấp nhất của {len(w)} nến {tf} đã đóng gần nhất', {'cao': _so(max(r[2] for r in w)), 'thap': _so(min(r[3] for r in w))})
    else:
        thieu.append('Chưa có nến đã đóng')
    i = n_dong - 1
    for k, ten in CHI_BAO:
        v = _cuoi(D.get(k), i)
        if v is None:
            if k in D:
                thieu.append(f'{ten} chưa đủ nến để tính')
            continue
        gt = {'gia_tri': v}
        if k == 'st':
            gt['chieu'] = 'tăng' if (_cuoi(D.get('st_chieu'), i) or 0) > 0 else 'giảm'
        them('E_CB_' + k.upper(), 'chi_bao', f'{ten} trên nến {tf} đã đóng gần nhất', gt)
    pps = []
    for p in list(PT.get('phuong_phap') or []) + list(PT.get('phuong_an') or []):
        ma_pp = str(p.get('ma') or '')
        if not ma_pp:
            continue
        hv = p.get('harrison') or {}
        g = {'co': bool(p.get('co')), 'hieu_luc': bool(p.get('hieu_luc')), 'huong': p.get('huong'), 'vao': _so(p.get('vao')), 'sl': _so(p.get('sl')),
             'tp': [_so(x) for x in (p.get('tp') or [])], 'nen_tin_hieu': p.get('nen'), 'vi_sao': p.get('vi_sao'), 'vi_sao_het': list(p.get('vi_sao_het') or [])[:6],
             'phien_ban': hv.get('version'), 'muc_kiem_chung': hv.get('status') or 'thống kê lịch sử của phương pháp, xem bảng chứng phương pháp'}
        id_ = 'E_PP_' + ma_pp.replace(':', '_').upper()
        them(id_, 'phuong_phap', f'Kết quả phương pháp {p.get("ten_ngan") or p.get("ten") or ma_pp}', g)
        for j, ck in enumerate(hv.get('checks') or []):
            them(f'{id_}_DK{j + 1}', 'dieu_kien', f'Điều kiện: {ck.get("ten")}', {'dat': bool(ck.get('dat'))})
        pps.append({'ma': ma_pp, 'ten': p.get('ten_ngan') or p.get('ten'), 'id': id_})
    if not pps and tf:
        thieu.append('Không có kết quả phương pháp cho mã/khung này')
    than = {'ma': ma or 'XAUUSD', 'tf': tf, 'luc': now.isoformat(), 'luc_phan_tich': PT.get('luc'), 'nguon': D.get('nguon'),
            'so_nen_da_dong': len(dong), 'co_nen_dang_chay': bool(chay), 'bang_chung': bc, 'phuong_phap': pps, 'thieu': thieu}
    sn = {'id': 'SN-' + hashlib.sha256(json.dumps(than, sort_keys=True, ensure_ascii=False, default=str).encode('utf-8')).hexdigest()[:14], **than}
    luu(sn, thu_muc)
    return sn


def luu(sn: dict, thu_muc: Path | None = None) -> None:
    with _khoa:
        _NHO[sn['id']] = sn
        _NHO.move_to_end(sn['id'])
        while len(_NHO) > TOI_DA_NHO:
            _NHO.popitem(last=False)
    if thu_muc:
        try:
            p = Path(thu_muc) / 'ai' / 'anh-chup'
            p.mkdir(parents=True, exist_ok=True)
            (p / f'{sn["id"]}.json').write_text(json.dumps(sn, ensure_ascii=False), encoding='utf-8')
        except OSError:
            pass


def lay(id_: str, thu_muc: Path | None = None) -> dict | None:
    """Ảnh chụp đã chốt theo id (bộ nhớ trước, đĩa sau). Không có thì None, không tự chụp lại."""
    import re                                                          # noqa: PLC0415
    if not re.fullmatch(r'SN-[0-9a-f]{14}', id_ or ''):
        return None
    with _khoa:
        if id_ in _NHO:
            return _NHO[id_]
    if thu_muc:
        p = Path(thu_muc) / 'ai' / 'anh-chup' / f'{id_}.json'
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding='utf-8'))
            except ValueError:
                return None
    return None


def tuoi_giay(sn: dict, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    return (now - datetime.fromisoformat(sn['luc'])).total_seconds()


def dieu_kien(sn: dict, ma_pp: str) -> dict | None:
    """Điều kiện và kết quả của một phương pháp trong ảnh chụp (không tính lại)."""
    p = next((x for x in sn.get('phuong_phap') or [] if x['ma'] == ma_pp), None)
    if not p:
        return None
    ds = [b for b in sn['bang_chung'] if b['id'] == p['id'] or b['id'].startswith(p['id'] + '_DK')]
    return {'snapshot_id': sn['id'], 'phuong_phap': p, 'bang_chung': ds}


def bang_chung_phuong_phap(ma_pp: str) -> dict:
    """Thống kê đã ghi của phương pháp, kèm phiên bản và loại báo cáo. Harrison: báo cáo nghiên cứu đóng băng, không tự tính lại theo cài đặt."""
    out = {'ma': ma_pp, 'loai': 'chua_ro', 'ghi_chu': []}
    if ma_pp == 'harrison':
        from . import harrison                                         # noqa: PLC0415
        r = harrison.load_report()
        out.update(loai='bao_cao_dong_bang', phien_ban=harrison.VERSION, chon=r.get('selected'), qua_cong=bool(r.get('gate_passed')),
                   ly_do_chua_dat=r.get('gate_reasons') or r.get('reasons'), pham_vi='XAUUSD · M15 · TP 5 / SL 20 giá',
                   ghi_chu=['Báo cáo đóng băng ngày 27/11/2026; không tự tính lại khi đổi chi phí trong Cài đặt.',
                            'Chọn bộ lọc trên 2015–2019, kiểm hồi cứu 2020–2026; không phải ngoài mẫu độc lập.'])
        return out
    try:
        from . import phuong_phap                                      # noqa: PLC0415
        tt = (getattr(phuong_phap, 'DS', {}) or {}).get(ma_pp) or {}
        if tt:
            out.update(loai='thong_ke_lich_su', mo_ta=tt.get('mo_ta'), ten=tt.get('ten'))
    except Exception:                                                  # noqa: BLE001
        pass
    return out


def ke_hoach_rui_ro(cfg: dict, bang, phieu: dict) -> dict:
    """Kiểm rủi ro đúng các số của phiếu (mã nghiệp vụ tính, không phải AI)."""
    from . import kiem_lenh                                            # noqa: PLC0415
    return kiem_lenh.kiem(cfg, bang, {'ma': phieu['ma'], 'chieu': phieu['chieu'], 'vao': phieu['vao'], 'sl': phieu['sl'],
                                      'tp': (phieu.get('tp') or [None])[0], 'rui_ro_pct': phieu.get('rui_ro_pct')})


def tong_ket_review(thu_muc: Path) -> dict:
    """Thống kê sổ phiếu: số phiếu, quyết định, kết quả mô phỏng đã có và mức làm đúng kế hoạch, đếm riêng từng thứ."""
    from . import phieu_ke_hoach                                       # noqa: PLC0415
    ds = phieu_ke_hoach.danh_sach(thu_muc, 10000)
    dem = lambda f: {k: sum(1 for p in ds if f(p) == k) for k in sorted({f(p) for p in ds} - {None})}   # noqa: E731
    return {'so_phieu': len(ds), 'quyet_dinh': dem(lambda p: (p.get('quyet_dinh') or {}).get('loai')),
            'kiem_rui_ro': dem(lambda p: (p.get('rui_ro') or {}).get('trang_thai')), 'tuan_thu': dem(lambda p: p.get('tuan_thu')),
            'ghi_chu': 'Kết quả mô phỏng xem ở từng phiếu; đây không phải thống kê hiệu suất đã kiểm chứng.'}
