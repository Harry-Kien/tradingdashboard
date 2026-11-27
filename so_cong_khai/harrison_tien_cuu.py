"""Sổ tiến cứu riêng của Harrison 3 Khung (27/11/2026). Không gộp với nhật ký luật gốc, không đổi tham số, không ghi hồi cứu.

- Mỗi phiên bản đóng băng (VERSION + bộ lọc được chọn + SHA-256 của báo cáo nghiên cứu) có một tệp riêng
  out/harrison/tien-cuu-<khóa>.jsonl; dòng đầu là cấu hình đóng băng. Báo cáo đổi thì sang tệp mới, không trộn kết quả.
- Tín hiệu chỉ được ghi khi `analyze` báo đạt điều kiện kỹ thuật, ghi ngay lúc đó (`luc_ghi`), trước khi có bất kỳ nến nào sau nó, nên
  không thể là ghi hồi cứu. Tín hiệu có nến tín hiệu cũ hơn 5 phút so với lúc ghi bị bỏ (như quy tắc quá hạn vào lệnh).
- Mỗi lúc một lệnh: còn lệnh chưa có kết quả thì tín hiệu mới bị bỏ và đếm riêng.
- Chấm đúng định nghĩa thực thi của nghiên cứu: vào ở giá ghi lúc tín hiệu (ask khi MUA, bid khi BÁN), TP 5, SL 20 giá, KHÔNG giới hạn
  thời gian giữ; nến mở cửa đã qua SL thì thoát ở giá mở; một nến chạm cả SL và TP tính SL trước, trừ khi giá mở đã qua TP. Chỉ dùng nến
  ĐÃ ĐÓNG có giờ mở từ lúc ghi trở đi. Thiếu nến (khoảng trống quá `KHOANG_TRONG` phút ngoài cuối tuần) thì ghi khoảng mất dữ liệu; chưa
  chạm mức nào mà dữ liệu có khoảng trống thì kết quả là "chưa xác định".
- Ghi spread lúc vào và giả định phí của báo cáo (0,18 giá mỗi lệnh, 0,25 khi thoát SL sát tin); lãi lỗ ròng trừ cả hai.
Harrison chưa qua cổng kiểm chứng vẫn được quan sát ở đây như ứng viên nghiên cứu; sổ này không nâng nó thành phương pháp đã chứng minh."""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from . import harrison

PHI_GIA = 0.18
KHOANG_TRONG = 20
_khoa = threading.Lock()


def khoa_phien_ban(report: dict | None = None) -> dict:
    r = harrison.load_report() if report is None else report
    sha = hashlib.sha256(json.dumps(r, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    chon = r.get('selected', 'A') if r.get('selected') in harrison.CANDIDATES else 'A'
    return {'version': harrison.VERSION, 'chon': chon, 'bao_cao_sha256': sha, 'tp': harrison.TP, 'sl': harrison.SL, 'phi_gia': PHI_GIA,
            'qua_cong': bool(r.get('gate_passed')), 'khoa': f'{harrison.VERSION}-{chon}-{sha[:10]}'}


def _tep(out: Path, kh: dict) -> Path:
    return Path(out) / 'harrison' / f'tien-cuu-{kh["khoa"]}.jsonl'


def doc(out: Path, kh: dict | None = None) -> tuple[dict | None, list[dict]]:
    kh = kh or khoa_phien_ban()
    p = _tep(out, kh)
    if not p.exists():
        return None, []
    dau, ds = None, []
    for dong in p.read_text(encoding='utf-8').splitlines():
        try:
            x = json.loads(dong)
        except ValueError:
            continue
        if x.get('loai') == 'dau':
            dau = x
        elif x.get('loai') == 'tin_hieu':
            ds.append(x)
        elif x.get('loai') == 'ket_qua':
            for t in ds:
                if t['id'] == x['id']:
                    t['ket_qua'] = x
    return dau, ds


def _ghi(out: Path, kh: dict, ban: dict) -> None:
    p = _tep(out, kh)
    p.parent.mkdir(parents=True, exist_ok=True)
    moi = not p.exists()
    with open(p, 'a', encoding='utf-8') as f:
        if moi:
            f.write(json.dumps({'loai': 'dau', 'tao_luc': ban.get('luc_ghi') or ban.get('cham_luc'), **kh}, ensure_ascii=False) + '\n')
        f.write(json.dumps(ban, ensure_ascii=False, default=str) + '\n')


def ghi_tin_hieu(out: Path, pp: dict, bid: float | None, ask: float | None, now: datetime | None = None, kh: dict | None = None) -> dict | None:
    """Ghi một tín hiệu Harrison đang đạt điều kiện kỹ thuật. Trả bản ghi, hoặc None nếu không ghi (không đạt, trùng, quá hạn, đang có lệnh)."""
    now = now or datetime.now(timezone.utc)
    kh = kh or khoa_phien_ban()
    if not pp or pp.get('ma') != 'harrison' or not pp.get('co') or pp.get('vao') is None:
        return None
    nen = datetime.fromisoformat(str(pp.get('nen')))
    if (now - nen).total_seconds() > 300:
        return None                                                     # quá hạn vào lệnh 5 phút: không ghi muộn
    id_ = f'{kh["khoa"]}@{nen.isoformat()}'
    with _khoa:
        _, ds = doc(out, kh)
        if any(t['id'] == id_ for t in ds):
            return None                                                 # trùng: hỏi lại nhiều lần trong cùng nến
        if any(not (t.get('ket_qua') or {}).get('dong') for t in ds):
            return None                                                 # mỗi lúc một lệnh: lệnh trước chưa chạm TP/SL
        ban = {'loai': 'tin_hieu', 'id': id_, 'luc_ghi': now.isoformat(), 'nen_tin_hieu': nen.isoformat(), 'huong': pp['huong'], 'vao': float(pp['vao']),
               'sl': float(pp['sl']), 'tp': float((pp.get('tp') or [None])[0]), 'spread': round(float(ask) - float(bid), 3) if bid is not None and ask is not None else None,
               'dat_cong': kh['qua_cong'], 'ghi_chu': 'Ghi lúc tín hiệu xuất hiện, trước mọi nến sau nó.'}
        _ghi(out, kh, ban)
    return ban


def cham_mot(t: dict, nen: list[list], now: datetime | None = None) -> dict:
    """Chấm một tín hiệu trên nến M1 hoặc M5 [giây, mở, cao, thấp, đóng] đã đóng."""
    t0 = datetime.fromisoformat(t['luc_ghi']).timestamp()
    ds = sorted((r for r in nen if r[0] >= t0 - 1e-9), key=lambda r: r[0])
    mua, vao, sl, tp = t['huong'] == 'MUA', t['vao'], t['sl'], t['tp']
    trong, truoc = [], t0
    for r in ds:
        d = datetime.fromtimestamp(r[0], timezone.utc)
        if r[0] - truoc > KHOANG_TRONG * 60 and not (d.weekday() in (0, 6) and r[0] - truoc < 3.5 * 86400):   # bỏ qua nghỉ cuối tuần
            trong.append([datetime.fromtimestamp(truoc, timezone.utc).isoformat(), d.isoformat()])
        truoc = r[0]
        _, o, h, lo, _c = r[:5]
        qua_tp_mo = (o >= tp) if mua else (o <= tp)
        qua_sl_mo = (o <= sl) if mua else (o >= sl)
        if qua_sl_mo:
            ra, ly = o, 'sl_nhay'
        elif qua_tp_mo:
            ra, ly = o, 'tp_nhay'
        elif (lo <= sl) if mua else (h >= sl):
            ra, ly = sl, 'sl'
        elif (h >= tp) if mua else (lo <= tp):
            ra, ly = tp, 'tp'
        else:
            continue
        gia = (ra - vao) if mua else (vao - ra)
        phi = (t.get('spread') or 0) + PHI_GIA
        return {'loai': 'ket_qua', 'id': t['id'], 'trang_thai': ly, 'dong': d.isoformat(), 'gia_ra': round(ra, 3), 'loi_gia': round(gia, 3),
                'loi_gia_rong': round(gia - phi, 3), 'r': round(gia / harrison.SL, 4), 'khoang_mat_du_lieu': trong,
                'do_chac': 'chac' if not trong else 'co_khoang_trong'}
    return {'loai': 'ket_qua', 'id': t['id'], 'trang_thai': 'chua_xac_dinh', 'dong': None, 'khoang_mat_du_lieu': trong,
            'ly_do': ('dữ liệu có khoảng trống, chưa đủ để kết luận' if trong else 'chưa chạm TP hoặc SL trên nến đã đóng'),
            'nen_cuoi': datetime.fromtimestamp(ds[-1][0], timezone.utc).isoformat() if ds else None}


def cham(out: Path, nen: list[list], now: datetime | None = None, kh: dict | None = None) -> list[dict]:
    """Chấm các tín hiệu chưa có kết quả cuối; chỉ ghi khi đã chạm TP hoặc SL (kết quả chưa xác định không ghi, để lần sau chấm tiếp)."""
    kh = kh or khoa_phien_ban()
    moi = []
    with _khoa:
        _, ds = doc(out, kh)
        for t in ds:
            if t.get('ket_qua') and t['ket_qua'].get('dong'):
                continue
            kq = cham_mot(t, nen, now)
            if kq.get('dong'):
                _ghi(out, kh, {**kq, 'cham_luc': (now or datetime.now(timezone.utc)).isoformat()})
                moi.append(kq)
    return moi


def tom_tat(out: Path, kh: dict | None = None) -> dict:
    """Thống kê tiến cứu của đúng phiên bản đóng băng hiện hành. Ít lệnh thì chỉ nêu số, không kết luận."""
    kh = kh or khoa_phien_ban()
    dau, ds = doc(out, kh)
    xong = [t for t in ds if (t.get('ket_qua') or {}).get('dong')]
    thang = [t for t in xong if t['ket_qua']['loi_gia'] > 0]
    return {'phien_ban': kh, 'bat_dau': dau and dau.get('tao_luc'), 'so_tin_hieu': len(ds), 'da_co_ket_qua': len(xong), 'chua_xac_dinh': len(ds) - len(xong),
            'thang': len(thang), 'thua': len(xong) - len(thang), 'loi_gia_rong': round(sum(t['ket_qua']['loi_gia_rong'] for t in xong), 3),
            'co_khoang_trong': sum(1 for t in xong if t['ket_qua']['khoang_mat_du_lieu']),
            'ghi_chu': ('Dưới 30 lệnh có kết quả: chưa nói được gì về lợi thế.' if len(xong) < 30 else 'Tiến cứu, không phải bằng chứng đã kiểm chứng đầy đủ.')
            + (' Ứng viên chưa qua cổng kiểm chứng nghiên cứu.' if not kh['qua_cong'] else '')}
