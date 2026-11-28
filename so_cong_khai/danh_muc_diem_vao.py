"""Danh mục của thẻ điểm vào. Giữ phương pháp trong danh sách khi đang chờ dữ liệu."""
from __future__ import annotations

from pathlib import Path

from . import da_ma, entry_feed, nhat_ky, phan_tich, phuong_phap, smc_harry, song, tin_hieu_ngan

LUAT = {'bot:nen': 'Bot Harry · Nến xác nhận', 'bot:xu_huong': 'Bot Harry · Theo xu hướng',
        'ba_khung': 'Xu hướng ba khung', 'dinh_day': 'Đỉnh/đáy 8 giờ'}
NGAN = {'pha_vo': 'Phá vỡ', 'hoi_ema': 'Hồi về EMA'}
THIEU = 'Chưa đủ dữ liệu để phân tích phương pháp này.'


def _cho(ma, ten, nhom_doc, reason=THIEU, **more):
    return {'ma': ma, 'ten': ten, 'co': False, 'hieu_luc': False, 'vi_sao': reason, 'nhom_doc': nhom_doc, 'thieu_du_lieu': True, **more}


def gop(cfg: dict, ma: str, tf: str, data: dict, out: Path, *, ly_do: str = '', loi_base: bool = False) -> dict:
    """Dùng đúng khung của từng luật. Bộ quét kỹ thuật và phương pháp thử nghiệm luôn mang nhãn riêng."""
    base = {r['ma']: r for r in data.get('phuong_phap', [])}
    law = {r['ma']: r for r in data.get('phuong_an', [])}
    khac_vang = bool(data.get('khac_vang'))
    chia_se = bool(data.get('chia_se'))
    for key, name in LUAT.items():
        if key not in law:
            reason = 'Luật dùng dữ liệu dành riêng cho cấu hình vàng của Harry.' if khac_vang else (ly_do or THIEU)
            law[key] = _cho(key, name, 'he_thong', reason, khung='M15', quan_sat=True)
    for key, setup in phuong_phap.DS.items():
        if key not in base:
            base[key] = _cho(key, setup['ten'], 'phuong_phap', ly_do or THIEU, chip=setup.get('chip', key),
                             ten_ngan=setup['ngan'], nhom='pp', thong_ke=setup['mo_ta'], khung='M15')
    reason = 'Chỉ áp dụng trên XAUUSD.' if khac_vang and not chia_se else (ly_do or THIEU)
    if 'harrison' not in base:
        base['harrison'] = _cho('harrison', 'Harrison 3 Khung', 'phuong_phap', reason, chip='harrison', nhom='pp', khung='M15', quan_sat=True)
    for r in law.values():
        r.setdefault('khung', 'M5' if r['ma'] == 'bot:xu_huong' else 'M5/M15' if r['ma'] == 'bot:nen' else 'M15')
        r.setdefault('nhom_doc', 'he_thong')
        if r['ma'] in LUAT:
            r.setdefault('ten_doc', LUAT[r['ma']])
    for r in base.values():
        r.setdefault('khung', 'M15')
        r.setdefault('nhom_doc', 'phuong_phap')
    frames = tuple(dict.fromkeys((tf, *tin_hieu_ngan.KHUNG))) if tf in tin_hieu_ngan.KHUNG else tuple(tin_hieu_ngan.KHUNG)
    rows = list(base.values())
    snapshot = None
    if not loi_base:
        try:
            snapshot = entry_feed.doc(cfg, ma)
        except (AttributeError, OSError, RuntimeError, ValueError):
            pass
    for k in frames:
        short = phan_tich.ngan_tu_du_lieu(snapshot, k)['phuong_phap'] if snapshot is not None else []
        by_id = {r['ma']: r for r in short}
        for key, name in NGAN.items():
            code = f'ngan:{k}:{key}'
            r = by_id.get(code) or _cho(code, f'{name} · {k}', 'da_khung', ly_do or THIEU, nhom='pp', quan_sat=True)
            rows.append({**r, 'chip': f'da_khung_{k}', 'ten_ngan': f'Đa khung · {k}', 'khung': k, 'nhom_doc': 'da_khung'})
    try:
        trial = smc_harry.doc(cfg, ma, frames, out) if not loi_base else []
    except (AttributeError, ImportError, OSError, RuntimeError, ValueError):
        trial = []
    lookup = {r['ma']: r for r in trial}
    for k in frames:
        for key, name in smc_harry.TEN.items():
            card = lookup.get(f'{key}:{k}') or {**smc_harry.the(key, k, name), 'vi_sao': ly_do or THIEU, 'thieu_du_lieu': True}
            rows.append({**card, 'nhom_doc': 'nghien_cuu'})
    return {**data, 'phuong_an': list(law.values()), 'phuong_phap': rows, 'khung_bieu_do': tf, 'danh_muc_day_du': True}


def tao(cfg: dict, ma: str, tf: str, out: Path) -> dict:
    if tf not in song.SO_NEN and tf not in song.KHUNG_XEM:
        raise ValueError('Khung biểu đồ không hợp lệ.')
    default = da_ma.ma_vang(cfg)
    khac = bool(ma and ma != default)
    try:
        data = da_ma.phan_tich(cfg, ma) if khac else phan_tich.phan_tich(cfg)
    except (RuntimeError, ValueError) as e:
        if isinstance(e, ValueError) and not str(e).startswith('chưa có giá trực tiếp từ MT5'):
            raise
        return gop(cfg, ma, tf, {'ma': ma or default, 'nguon': 'khong', 'khac_vang': khac, 'khung_phan_tich': 'M15'},
                   out, ly_do='Chưa có đủ giá và nến từ MT5. Thẻ sẽ tự cập nhật khi dữ liệu có lại.', loi_base=True)
    data['khung_phan_tich'] = 'M15'
    if tf not in ('M5', 'M30'):
        try:
            nhat_ky.ghi(cfg, data)
        except Exception:  # noqa: BLE001 - Nhật ký hỏng không làm mất kết quả phân tích.
            pass
    return gop(cfg, ma, tf, data, out)
