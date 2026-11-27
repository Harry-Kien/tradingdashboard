"""Phiếu kế hoạch dùng chung giữa Biểu đồ, Kế hoạch, Kiểm tra lệnh, theo dõi mô phỏng và Nhật ký (27/11/2026).

Một phiếu có `id` cố định và nhiều `phien_ban`. Mỗi lần đổi (sửa giá, gắn kết quả kiểm, bắt đầu theo dõi, ghi kết quả) là một dòng mới
ghi thêm vào out/ke-hoach/phieu.jsonl; dòng cũ không bao giờ bị sửa, nên bản kế hoạch cũ luôn đọc lại được để đối chiếu.

Ba trạng thái tách riêng, không cái nào suy ra cái nào:
- `ky_thuat`: điều kiện kỹ thuật của phương pháp lúc lập phiếu (còn hiệu lực, đã qua, chưa cập nhật…), lấy từ trang Biểu đồ.
- `rui_ro`: kết quả kiểm quản lý rủi ro (chưa kiểm, đạt, cân nhắc, không nên, cần kiểm lại khi giá vào, SL, TP, chiều, mã hoặc
  tham số đổi so với lúc kiểm).
- `kiem_chung`: mức kiểm chứng của phương pháp (ví dụ nghiên cứu, theo dõi tiến cứu); qua bộ kiểm rủi ro KHÔNG có nghĩa phương pháp có
  lợi thế hay lệnh sẽ thắng.

Theo dõi mô phỏng chỉ dùng nến đã đóng SAU lúc bắt đầu theo dõi; một nến chạm cả SL và TP thì tính SL trước. Không đặt lệnh nào."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path

PHIEN_BAN_DINH_DANG = 1
CHIEU = ('MUA', 'BAN')
KY_THUAT = ('con_hieu_luc', 'het_hieu_luc', 'chua_cap_nhat', 'tk_dung', 'tham_khao', 'khong_ro')
RUI_RO = ('chua_kiem', 'dat', 'can_nhac', 'khong_nen', 'can_kiem_lai')
_khoa = threading.Lock()


def _tep(thu_muc: Path) -> Path:
    return Path(thu_muc) / 'ke-hoach' / 'phieu.jsonl'


def _so(x, ten: str, duong: bool = True) -> float | None:
    if x is None or x == '':
        return None
    try:
        v = float(str(x).replace(',', '.'))
    except ValueError as e:
        raise ValueError(f'{ten} không phải số') from e
    if v != v or v in (float('inf'), float('-inf')) or (duong and v <= 0):
        raise ValueError(f'{ten} phải là số dương')
    return v


def dau_lenh(p: dict) -> str:
    """Dấu của phần quyết định kết quả kiểm: đổi bất kỳ trường nào thì kết quả kiểm cũ không còn đúng."""
    g = {k: p.get(k) for k in ('ma', 'chieu', 'vao', 'sl', 'tp', 'tai_khoan', 'rui_ro_pct')}
    return hashlib.sha256(json.dumps(g, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:16]


def chuan_hoa(d: dict) -> dict:
    """Kiểm và chuẩn hóa dữ liệu phiếu do trang gửi lên. Không tự điền giá trị mặc định cho chiều, SL hay TP: thiếu là lỗi hoặc để trống."""
    ma = str(d.get('ma') or '').strip()
    if not ma or len(ma) > 40:
        raise ValueError('cần mã giao dịch')
    chieu = str(d.get('chieu') or '').upper().replace('BÁN', 'BAN').replace('BUY', 'MUA').replace('SELL', 'BAN')
    if chieu not in CHIEU:
        raise ValueError('chiều phải là MUA hoặc BAN')
    vao, sl = _so(d.get('vao'), 'giá vào'), _so(d.get('sl'), 'dừng lỗ')
    if vao is None:
        raise ValueError('cần giá vào')
    tp = [_so(x, 'chốt lời') for x in (d.get('tp') or [])][:5]
    tp = [x for x in tp if x is not None]
    if sl is not None and ((chieu == 'MUA' and sl >= vao) or (chieu == 'BAN' and sl <= vao)):
        raise ValueError('dừng lỗ nằm sai phía so với giá vào')
    if any((chieu == 'MUA' and x <= vao) or (chieu == 'BAN' and x >= vao) for x in tp):
        raise ValueError('chốt lời nằm sai phía so với giá vào')
    rr = _so(d.get('rui_ro_pct'), 'rủi ro %')
    if rr is not None and rr > 100:
        raise ValueError('rủi ro % phải không quá 100')
    pp = d.get('phuong_phap') or {}
    kt = str(d.get('ky_thuat') or 'khong_ro')
    s = lambda k, n=200: (str(d.get(k))[:n] if d.get(k) not in (None, '') else None)   # noqa: E731
    return {'ma': ma, 'chieu': chieu, 'vao': vao, 'sl': sl, 'tp': tp, 'rui_ro_pct': rr,
            'tai_khoan': s('tai_khoan', 40) or 'mo_phong', 'khung': s('khung', 8) or 'M15',
            'phuong_phap': {'ma': str(pp.get('ma') or '')[:40], 'ten': str(pp.get('ten') or '')[:120], 'phien_ban_quy_tac': str(pp.get('phien_ban_quy_tac') or '')[:40],
                            'kiem_chung': str(pp.get('kiem_chung') or 'chua_ro')[:40]},
            'nen_tin_hieu': s('nen_tin_hieu', 40), 'luc_phan_tich': s('luc_phan_tich', 40), 'snapshot_id': s('snapshot_id', 80),
            'dieu_kien_vo_hieu': s('dieu_kien_vo_hieu', 400), 'chi_phi': {k: _so((d.get('chi_phi') or {}).get(k), k, duong=False)
                                                                       for k in ('spread', 'hoa_hong') if (d.get('chi_phi') or {}).get(k) not in (None, '')},
            'ky_thuat': kt if kt in KY_THUAT else 'khong_ro', 'nguon_gia': s('nguon_gia', 20), 'ghi_chu': s('ghi_chu', 500)}


def _doc_tat(thu_muc: Path) -> list[dict]:
    p = _tep(thu_muc)
    if not p.exists():
        return []
    ds = []
    with open(p, encoding='utf-8') as f:
        for dong in f:
            dong = dong.strip()
            if not dong:
                continue
            try:
                ds.append(json.loads(dong))
            except ValueError:
                continue                                          # dòng hỏng (ghi dở) không làm mất các phiếu khác
    return ds


def _ghi(thu_muc: Path, ban: dict) -> None:
    p = _tep(thu_muc)
    p.parent.mkdir(parents=True, exist_ok=True)
    dau = ''
    if p.exists() and p.stat().st_size:                                # dòng cuối ghi dở (mất điện, tắt máy): bắt đầu dòng mới, không dính vào nó
        with open(p, 'rb') as f:
            f.seek(-1, os.SEEK_END)
            dau = '' if f.read(1) == b'\n' else '\n'
    with open(p, 'a', encoding='utf-8') as f:
        f.write(dau + json.dumps(ban, ensure_ascii=False, sort_keys=True) + '\n')
        f.flush()
        os.fsync(f.fileno())


def doc(thu_muc: Path, id_: str, phien_ban: int | None = None) -> dict | None:
    """Bản mới nhất (hoặc đúng `phien_ban`) của phiếu, kèm `cac_ban` (số phiên bản đã có) và `can_kiem_lai` tính lại."""
    ds = [x for x in _doc_tat(thu_muc) if x.get('id') == id_]
    if not ds:
        return None
    ban = next((x for x in ds if x.get('phien_ban') == phien_ban), None) if phien_ban else ds[-1]
    if ban is None:
        return None
    return {**ban, 'cac_ban': [x['phien_ban'] for x in ds], 'moi_nhat': ds[-1]['phien_ban']}


def danh_sach(thu_muc: Path, n: int = 50) -> list[dict]:
    """Bản mới nhất của từng phiếu, mới trước."""
    moi: dict = {}
    for x in _doc_tat(thu_muc):
        moi[x['id']] = x
    return sorted(moi.values(), key=lambda x: x.get('sua_luc') or '', reverse=True)[:n]


def tao(thu_muc: Path, d: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    p = chuan_hoa(d)
    ban = {**p, 'dinh_dang': PHIEN_BAN_DINH_DANG, 'id': f'KH-{now:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}', 'phien_ban': 1,
           'tao_luc': now.isoformat(), 'sua_luc': now.isoformat(), 'thay_doi': [], 'dau_lenh': dau_lenh(p),
           'rui_ro': {'trang_thai': 'chua_kiem'}, 'theo_doi': None, 'ket_qua': None}
    with _khoa:
        _ghi(thu_muc, ban)
    return ban


def _ban_moi(thu_muc: Path, id_: str, sua, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    with _khoa:
        cu = doc(thu_muc, id_)
        if cu is None:
            raise KeyError(id_)
        cu = {k: v for k, v in cu.items() if k not in ('cac_ban', 'moi_nhat')}
        moi = sua(json.loads(json.dumps(cu)))
        moi.update(phien_ban=cu['phien_ban'] + 1, sua_luc=now.isoformat())
        _ghi(thu_muc, moi)
    return moi


def sua_lenh(thu_muc: Path, id_: str, d: dict, now: datetime | None = None) -> dict:
    """Người dùng đổi giá/chiều/SL/TP: phiên bản mới, ghi rõ trường nào đổi; kết quả kiểm cũ thành "cần kiểm lại"."""
    def f(p):
        moi = chuan_hoa({**p, **d, 'phuong_phap': p['phuong_phap']})
        doi = [k for k in ('ma', 'chieu', 'vao', 'sl', 'tp', 'rui_ro_pct', 'tai_khoan', 'khung') if moi[k] != p.get(k)]
        if not doi:
            raise ValueError('không có gì thay đổi')
        p.update(moi)
        p['thay_doi'] = doi
        p['dau_lenh'] = dau_lenh(p)
        if p['rui_ro']['trang_thai'] != 'chua_kiem':
            p['rui_ro'] = {**p['rui_ro'], 'trang_thai': 'can_kiem_lai', 'ly_do': 'đã đổi ' + ', '.join(doi) + ' sau lần kiểm'}
        return p
    return _ban_moi(thu_muc, id_, f, now)


def gan_kiem(thu_muc: Path, id_: str, kq: dict, now: datetime | None = None) -> dict:
    """Gắn kết quả của kiem_lenh.kiem (do máy chủ tính, không nhận số từ trang) vào phiếu, kèm dấu của lệnh lúc kiểm."""
    now = now or datetime.now(timezone.utc)
    kl = kq.get('ket_luan')
    if kl not in ('dat', 'can_nhac', 'khong_nen'):
        raise ValueError('kết quả kiểm không hợp lệ')

    def f(p):
        p['thay_doi'] = ['rui_ro']
        p['rui_ro'] = {'trang_thai': kl, 'luc': now.isoformat(), 'dau_lenh': p['dau_lenh'], 'lot': kq.get('lot'), 'rui_ro_tien': kq.get('rui_ro_tien'),
                       'rr': kq.get('rr'), 'tong_rui_ro_pct': kq.get('tong_rui_ro_pct'), 'tien': kq.get('tien'), 'thieu': list(kq.get('thieu') or [])[:10],
                       'muc': [{'muc': m.get('muc'), 'tieu': (m.get('vi') or {}).get('tieu')} for m in (kq.get('muc') or [])][:20],
                       'ghi_chu': 'Qua bộ kiểm rủi ro không có nghĩa phương pháp có lợi thế hay lệnh sẽ thắng.'}
        return p
    return _ban_moi(thu_muc, id_, f, now)


def bat_dau_theo_doi(thu_muc: Path, id_: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)

    def f(p):
        if p.get('theo_doi'):
            raise ValueError('phiếu này đã đang theo dõi')                 # bấm lặp không tạo hai lần theo dõi
        if (p.get('quyet_dinh') or {}).get('loai') == 'dung_ngoai':
            raise ValueError('phiếu này đã ghi quyết định đứng ngoài')
        if p.get('sl') is None or not p.get('tp'):
            raise ValueError('cần cả dừng lỗ và ít nhất một chốt lời để theo dõi mô phỏng')
        p['thay_doi'] = ['theo_doi']
        p['theo_doi'] = {'tu': now.isoformat(), 'loai': 'mo_phong', 'ghi_chu': 'Mô phỏng trên nến đã đóng sau lúc bấm, không đặt lệnh thật.'}
        p['quyet_dinh'] = {'loai': 'vao_mo_phong', 'luc': now.isoformat()}
        return p
    return _ban_moi(thu_muc, id_, f, now)


def dung_ngoai(thu_muc: Path, id_: str, ly_do: str = '', now: datetime | None = None) -> dict:
    """Ghi quyết định đứng ngoài (không theo dõi). Cũng là một quyết định cần review sau, nên được lưu như vào lệnh."""
    now = now or datetime.now(timezone.utc)

    def f(p):
        if p.get('theo_doi'):
            raise ValueError('phiếu này đã đang theo dõi mô phỏng')
        if (p.get('quyet_dinh') or {}).get('loai') == 'dung_ngoai':
            raise ValueError('đã ghi đứng ngoài')
        p['thay_doi'] = ['quyet_dinh']
        p['quyet_dinh'] = {'loai': 'dung_ngoai', 'luc': now.isoformat(), 'ly_do': str(ly_do or '')[:500]}
        return p
    return _ban_moi(thu_muc, id_, f, now)


TUAN_THU = ('', 'dung', 'mot_phan', 'lech')


def ghi_chu(thu_muc: Path, id_: str, noi_dung: str, tag=None, loai: str = 'ghi_chu', now: datetime | None = None, tuan_thu: str = '') -> dict:
    """Ghi chú và tag cá nhân: lớp bổ sung, không đổi dữ kiện của phiếu. `loai`: ghi_chu | review_truoc | review_sau.
    `tuan_thu` (review sau): có làm đúng kế hoạch không — tách khỏi kết quả lãi lỗ, vì làm đúng vẫn có thể thua và ngược lại."""
    now = now or datetime.now(timezone.utc)
    noi_dung = str(noi_dung or '').strip()[:1000]
    tag = [str(t).strip()[:30] for t in (tag or []) if str(t).strip()][:8]
    if not noi_dung and not tag and not tuan_thu:
        raise ValueError('ghi chú trống')
    if loai not in ('ghi_chu', 'review_truoc', 'review_sau'):
        raise ValueError('loại ghi chú không hợp lệ')
    if tuan_thu not in TUAN_THU:
        raise ValueError('mức tuân thủ không hợp lệ')

    def f(p):
        p['thay_doi'] = ['ghi_chu']
        p['ghi_chu_nd'] = list(p.get('ghi_chu_nd') or []) + [{'luc': now.isoformat(), 'loai': loai, 'noi_dung': noi_dung, 'tag': tag, 'tuan_thu': tuan_thu}]
        if tuan_thu:
            p['tuan_thu'] = tuan_thu
        return p
    return _ban_moi(thu_muc, id_, f, now)


TOI_DA_ANH = 600_000


def luu_anh(thu_muc: Path, id_: str, du_lieu_url: str, now: datetime | None = None) -> dict:
    """Ảnh chart lúc quyết định (data URL JPEG/PNG do trang Biểu đồ chụp). Lưu tệp riêng, phiếu chỉ giữ tên tệp."""
    import base64                                                       # noqa: PLC0415
    s = str(du_lieu_url or '')
    for dau, duoi in (('data:image/jpeg;base64,', 'jpg'), ('data:image/png;base64,', 'png')):
        if s.startswith(dau):
            break
    else:
        raise ValueError('ảnh phải là JPEG hoặc PNG')
    try:
        b = base64.b64decode(s[len(dau):], validate=True)
    except ValueError as e:
        raise ValueError('ảnh không đọc được') from e
    if not b or len(b) > TOI_DA_ANH or not (b[:3] == b'\xff\xd8\xff' or b[:8] == b'\x89PNG\r\n\x1a\n'):
        raise ValueError('ảnh rỗng, quá lớn hoặc sai định dạng')

    def f(p):
        if p.get('anh'):
            raise ValueError('phiếu đã có ảnh lúc quyết định')
        ten = f'{p["id"]}-b{p["phien_ban"] + 1}.{duoi}'
        thu = Path(thu_muc) / 'ke-hoach' / 'anh'
        thu.mkdir(parents=True, exist_ok=True)
        (thu / ten).write_bytes(b)
        p['thay_doi'] = ['anh']
        p['anh'] = ten
        return p
    return _ban_moi(thu_muc, id_, f, now)


def duong_anh(thu_muc: Path, ten: str) -> Path | None:
    import re                                                           # noqa: PLC0415
    if not re.fullmatch(r'KH-[0-9A-Za-z-]{6,40}-b\d{1,4}\.(jpg|png)', ten or ''):
        return None
    p = Path(thu_muc) / 'ke-hoach' / 'anh' / ten
    return p if p.is_file() else None


def cham_mo_phong(p: dict, nen: list[list], buoc: int = 300) -> dict:
    """Chấm phiếu đang theo dõi trên nến [giây, mở, cao, thấp, đóng] ĐÃ ĐÓNG (nến có giờ mở từ lúc bắt đầu theo dõi trở đi; `buoc`: giây mỗi nến).
    Vào ở giá vào của phiếu khi nến chạm giá đó lần đầu; sau đó SL trước TP nếu cùng nến. Thiếu nến thì 'chua_xac_dinh'."""
    if not p.get('theo_doi'):
        return {'trang_thai': 'khong_theo_doi'}
    t0 = datetime.fromisoformat(p['theo_doi']['tu']).timestamp()
    ds = [r for r in nen if r[0] >= t0]
    if not ds:
        return {'trang_thai': 'chua_xac_dinh', 'ly_do': 'chưa có nến đã đóng nào sau lúc bắt đầu theo dõi'}
    if nen and nen[0][0] > t0 + buoc:
        return {'trang_thai': 'chua_xac_dinh', 'ly_do': 'dữ liệu nến đang có bắt đầu sau lúc theo dõi, thiếu đoạn đầu'}
    mua, vao, sl, tp = p['chieu'] == 'MUA', p['vao'], p['sl'], p['tp'][0]
    da_vao = None
    for r in ds:
        _, o, h, lo, c = r[:5]
        if da_vao is None:
            if lo <= vao <= h:
                da_vao = r[0]
            else:
                continue
        cham_sl = lo <= sl if mua else h >= sl
        cham_tp = h >= tp if mua else lo <= tp
        if cham_sl:
            return {'trang_thai': 'sl', 'luc': datetime.fromtimestamp(r[0], timezone.utc).isoformat(), 'r': -1.0, 'vao_luc': datetime.fromtimestamp(da_vao, timezone.utc).isoformat()}
        if cham_tp:
            r_ = abs(tp - vao) / abs(vao - sl)
            return {'trang_thai': 'tp', 'luc': datetime.fromtimestamp(r[0], timezone.utc).isoformat(), 'r': round(r_, 3), 'vao_luc': datetime.fromtimestamp(da_vao, timezone.utc).isoformat()}
    return {'trang_thai': 'dang_mo' if da_vao else 'chua_khop', 'nen_cuoi': datetime.fromtimestamp(ds[-1][0], timezone.utc).isoformat(),
            'ghi_chu': 'Chưa chạm SL hoặc TP trên nến đã đóng.' if da_vao else 'Giá chưa chạm mức vào.'}
