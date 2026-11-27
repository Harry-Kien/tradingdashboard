"""python -m so_cong_khai [--tuan 2026-W47] [--cau-hinh cau-hinh.json] [--ra out]

Đọc các sổ (chỉ đọc) rồi viết: index.html (sổ công khai), tong-ket-tuan-<mã tuần>.txt, so-cong-khai.json."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import canh_bao, doc_so, duong, gia, tai_khoan, tong_hop, trang, thuong_hieu

HERE = duong.goc_du_lieu()      # GỐC DỮ LIỆU (cau-hinh.json, du-lieu/, out/); tài nguyên của chương trình thì lấy qua duong.goc_chuong_trinh()


def thu(fn, *a):
    """Đọc một nguồn; lỗi thì trả về chuỗi lý do thay vì làm hỏng cả trang."""
    try:
        return fn(*a)
    except Exception as e:                                     # noqa: BLE001 - một sổ hỏng không được chặn các sổ khác
        return f'{type(e).__name__}: {e}'


def gom(cfg: dict, start=None, end=None) -> dict:
    d: dict = {'tai_khoan': [], 'loi': []}
    bot = thu(doc_so.doc_bot, cfg['bot_db']) if cfg.get('bot_db') else None
    if isinstance(bot, str):
        d['loi'].append(('Bot tín hiệu vàng', bot))
    elif bot is not None:
        d['bot'] = tong_hop.tom_bot(bot, start, end)
    for i, acc in enumerate(cfg.get('tai_khoan', [])):
        eas, errs = [], []
        for e in acc.get('ea', []):
            r = thu(doc_so.doc_ea, e['tep'], e.get('lech_gio_utc', 0))
            (errs if isinstance(r, str) else eas).append((e['ten'], r))
        from . import doi_chieu_mt5
        eas, bo_sung = doi_chieu_mt5.bo_sung(acc, eas)
        d['tai_khoan'].append({'id': f'tk-{i + 1}', 'ten': acc['ten'], 'loi': errs,
                               'bo_sung_mt5': bo_sung,
                               'tom': tong_hop.tom_tai_khoan(eas, start, end) if eas else None})
    for key, name, reader, summ in (('xu_huong', 'Luật xu hướng ba khung', doc_so.doc_bong_xu_huong, tong_hop.tom_xu_huong),
                                    ('dinh_day', 'Luật đỉnh/đáy', doc_so.doc_bong_dinh_day, tong_hop.tom_dinh_day)):
        if not cfg.get('bong_' + key):
            continue
        src = thu(reader, cfg['bong_' + key])
        if isinstance(src, str):
            d['loi'].append((name, src))
        else:
            d[key] = {**summ(src, start, end), 'chain_ok': src['chain_ok'], 'n_lines': src['n_lines'],
                      'n_candles': src.get('n_candles', 0)}
    return d


def gan_doi_chieu(cfg: dict, d: dict, now: datetime | None = None) -> dict:
    """Đối chiếu nhật ký EA với lịch sử MT5 (chỉ đọc) cho tài khoản mà MT5 đang nối; gắn kết quả vào từng tài khoản trong `d`."""
    for khai, acc in zip(cfg.get('tai_khoan', []), d.get('tai_khoan', [])):
        if acc.get('tom'):
            dc = thu(tai_khoan.doi_chieu, cfg, {e['ten'] for e in khai.get('ea', [])}, acc['tom'], now, 300, khai.get('so_cuoi'))
            acc['doi_chieu'] = dc if isinstance(dc, dict) else None
            if acc['doi_chieu'] is not None:
                acc['doi_chieu']['n_bo_sung_mt5'] = (acc.get('bo_sung_mt5') or {}).get('bo_sung', 0)
    return d


def _gon(o):
    """Bản để ghi JSON: bỏ đường vốn (dài) và đổi ngày giờ thành chuỗi."""
    if isinstance(o, dict):
        return {str(k): _gon(v) for k, v in o.items() if k != 'curve'}
    if isinstance(o, (list, tuple)):
        return [_gon(v) for v in o]
    return o.isoformat() if hasattr(o, 'isoformat') else o


def ban_nhap_threads(out: Path) -> list[dict]:
    """Các bản nháp bài Threads đã tạo trong out/threads (mới nhất trước), để hiện bản xem trước trên trang."""
    res = []
    for f in sorted((out / 'threads').glob('*.draft.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:4]:
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
            cap = out / 'threads' / Path(d['captionFile']).name
            res.append({'id': d['id'], 'approved': d.get('approved') is True, 'img': 'threads/' + Path(d['imageFile']).name,
                        'text': cap.read_text(encoding='utf-8').strip()})
        except (OSError, ValueError, KeyError):
            continue
    return res


def xay(cfg: dict, ma_tuan: str | None = None, ra: str | None = None, live: bool = False, now: datetime | None = None) -> dict:
    """Đọc sổ, dựng trang và bài tuần, ghi ba tệp vào thư mục ra. Trả về HTML và các phần đã tính."""
    out = Path(ra or cfg.get('thu_muc_ra', 'out'))
    out = out if out.is_absolute() else HERE / out
    out.mkdir(parents=True, exist_ok=True)
    now = now or datetime.now(timezone.utc)
    start, end = tong_hop.tuan_theo_ma(ma_tuan) if ma_tuan else tong_hop.tuan_chua(now)
    ma = f'{start.isocalendar()[0]}-W{start.isocalendar()[1]:02d}'
    tat_ca, tuan = gom(cfg), gom(cfg, start, end)
    if live:
        gan_doi_chieu(cfg, tat_ca, now)
    bai = trang.bai_tuan(thuong_hieu.TEN, start, tuan)
    khoi_tuan = {'start': start, 'bai': bai, 'threads': ban_nhap_threads(out)}
    hien_tai = {'lenh': thu(gia.lenh_dang_mo, cfg), 'canh_bao': thu(canh_bao.doc, out, 5), 'tin': thu(gia.tin_sap_toi, cfg, now, 5)}
    hien_tai = {k: (v if isinstance(v, list) else []) for k, v in hien_tai.items()}
    try:                                                                # lệnh nhật ký EA còn ghi mở nhưng MT5 đã xác nhận đóng (vi_the.py)
        from . import vi_the                                            # noqa: PLC0415
        hien_tai['da_dong_mt5'] = vi_the.tong_hop_nho(cfg)['da_dong_theo_mt5']
    except Exception:                                                   # noqa: BLE001
        hien_tai['da_dong_mt5'] = []
    html = trang.trang_html(thuong_hieu.TEN, now, tat_ca, khoi_tuan, live, hien_tai)
    (out / 'index.html').write_text(trang.trang_html(thuong_hieu.TEN, now, tat_ca, khoi_tuan, False, hien_tai), encoding='utf-8')
    (out / f'tong-ket-tuan-{ma}.txt').write_text(bai, encoding='utf-8')
    (out / 'so-cong-khai.json').write_text(json.dumps(_gon({'cap_nhat': now, 'tuan': ma, 'tat_ca': tat_ca, 'trong_tuan': tuan}),
                                                      ensure_ascii=False, indent=1), encoding='utf-8')
    return {'html': html, 'bai': bai, 'ma': ma, 'out': out, 'tat_ca': tat_ca}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='so_cong_khai', description=__doc__)
    ap.add_argument('--cau-hinh', default=str(HERE / 'cau-hinh.json'))
    ap.add_argument('--ra', default=None, help='thư mục ghi kết quả (mặc định: theo cấu hình)')
    ap.add_argument('--tuan', default=None, help='mã tuần ISO, ví dụ 2026-W47 (mặc định: tuần hiện tại, giờ Việt Nam)')
    a = ap.parse_args(argv)
    cfg = json.loads(Path(a.cau_hinh).read_text(encoding='utf-8'))
    r = xay(cfg, a.tuan, a.ra)
    sys.stdout.reconfigure(encoding='utf-8')
    print(r['bai'])
    print(f'\nĐã viết: {r["out"] / "index.html"}\n         {r["out"] / ("tong-ket-tuan-" + r["ma"] + ".txt")}')
    for name, err in r['tat_ca']['loi'] + [x for acc in r['tat_ca']['tai_khoan'] for x in acc['loi']]:
        print(f'CẢNH BÁO: {name} không đọc được: {err}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
