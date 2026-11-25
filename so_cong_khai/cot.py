"""Vị thế của các nhóm lớn trên vàng tương lai COMEX, theo báo cáo Commitments of Traders (COT) của CFTC.

Đây là thứ gần nhất với "khối lượng cá mập" mà có nguồn chính thức và miễn phí. Giới hạn cần nhớ:
- Số liệu chốt thứ Ba, công bố thứ Sáu (khoảng 20:30 UTC): lúc đọc được thì đã cũ 3 tới 10 ngày.
- Là vàng TƯƠNG LAI ở COMEX, không phải khối lượng trên sàn forex/CFD đang giao dịch.
- Cho biết ai đang giữ bao nhiêu hợp đồng, không cho biết họ sắp làm gì.

Phần này là chỗ duy nhất của webapp tự gọi ra mạng mà không cần bấm: nó TẢI VỀ tệp công khai của cftc.gov (tệp tuần khoảng 0,5 MB;
lần đầu thêm mỗi năm một tệp nén khoảng 2 MB) và không gửi đi dữ liệu nào. Chỉ chạy khi cau-hinh.json có "cot": {"bat": true}.
Tải hỏng thì giữ dữ liệu cũ và thử lại sau THU_LAI_GIO giờ."""
from __future__ import annotations

import csv
import io
import json
import threading
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

MA_VANG = '088691'                                             # mã hợp đồng vàng COMEX trong báo cáo của CFTC
URL_TUAN = 'https://www.cftc.gov/dea/newcot/f_disagg.txt'      # báo cáo tuần mới nhất (bản tách nhóm, chỉ hợp đồng tương lai)
URL_NAM = 'https://www.cftc.gov/files/dea/history/fut_disagg_txt_{nam}.zip'
TU_NAM = 2015                                                  # lịch sử lấy từ năm này, khớp với dữ liệu giá nhiều năm của webapp
CUA_SO = 156                                                   # số tuần (3 năm) dùng để xếp hạng vị thế của quỹ
THU_LAI_GIO = 6                                                # tải hỏng hoặc CFTC chậm công bố: thử lại sau chừng này giờ
CONG_BO = timedelta(days=10, hours=20, minutes=30)             # báo cáo kế tiếp ra sau ngày chốt của báo cáo đang có chừng này
TOI_DA_BYTE = 60_000_000                                       # tệp lớn hơn mức này thì không nhận
COT = {'oi': 7, 'pm_mua': 8, 'pm_ban': 9, 'sw_mua': 10, 'sw_ban': 11, 'mm_mua': 13, 'mm_ban': 14, 'kh_mua': 16, 'kh_ban': 17}

_tt: dict = {'dang': False, 'loi': None}
_khoa = threading.Lock()


def _tai(url: str) -> bytes:
    rq = urllib.request.Request(url, headers={'User-Agent': 'so-cong-khai/1'})
    with urllib.request.urlopen(rq, timeout=60) as r:                      # noqa: S310 - địa chỉ là hằng số https ở trên
        b = r.read(TOI_DA_BYTE + 1)
    if len(b) > TOI_DA_BYTE:
        raise ValueError('tệp lớn bất thường, không nhận')
    return b


def doc_van(van: str, ma: str = MA_VANG) -> list[dict]:
    """Các dòng của một hợp đồng trong tệp COT (có hoặc không có dòng tiêu đề), xếp theo ngày chốt. Dòng không đọc được thì bỏ qua."""
    ds = {}
    for r in csv.reader(io.StringIO(van)):
        if len(r) <= max(COT.values()) or r[3].strip() != ma:
            continue
        try:
            x = {'ngay': date.fromisoformat(r[2].strip()).isoformat(), **{k: int(float(r[i])) for k, i in COT.items()}}
        except ValueError:
            continue
        ds[x['ngay']] = x
    return [ds[k] for k in sorted(ds)]


def doc_zip(b: bytes, ma: str = MA_VANG) -> list[dict]:
    """Đọc tệp nén theo năm ngay trong bộ nhớ (không giải nén ra đĩa)."""
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        tv = next((i for i in z.infolist() if i.filename.lower().endswith('.txt')), None)
        if tv is None or tv.file_size > 4 * TOI_DA_BYTE:
            raise ValueError('tệp nén không có tệp văn bản như mong đợi')
        return doc_van(z.read(tv).decode('latin-1'), ma)


def gop(cu: list[dict], moi: list[dict]) -> list[dict]:
    """Gộp theo ngày chốt; cùng ngày thì bản mới thay bản cũ (CFTC đôi khi sửa số)."""
    ds = {x['ngay']: x for x in cu}
    ds.update({x['ngay']: x for x in moi})
    return [ds[k] for k in sorted(ds)]


def rong(x: dict) -> int:
    """Vị thế mua ròng của nhóm quỹ đầu cơ (managed money), tính bằng hợp đồng."""
    return x['mm_mua'] - x['mm_ban']


def tom(ds: list[dict], now: datetime | None = None) -> dict | None:
    """Tóm tắt tuần mới nhất: vị thế ròng từng nhóm, thay đổi so với tuần trước, và thứ hạng của quỹ trong CUA_SO tuần gần nhất."""
    if not ds:
        return None
    now = now or datetime.now(timezone.utc)
    x, tr = ds[-1], (ds[-2] if len(ds) > 1 else None)
    r = rong(x)
    cs = [rong(y) for y in ds[-CUA_SO:]]
    return {'ngay': x['ngay'], 'tuoi_ngay': (now.date() - date.fromisoformat(x['ngay'])).days, 'oi': x['oi'],
            'quy_mua': x['mm_mua'], 'quy_ban': x['mm_ban'], 'quy_rong': r, 'quy_doi': r - rong(tr) if tr else None,
            'quy_ty_le': round(100 * r / x['oi'], 1) if x['oi'] else None,
            'hang': round(100 * sum(c <= r for c in cs) / len(cs)) if len(cs) >= CUA_SO else None, 'hang_tuan': CUA_SO,
            'nh_rong': x['sw_mua'] - x['sw_ban'], 'sx_rong': x['pm_mua'] - x['pm_ban'], 'kh_rong': x['kh_mua'] - x['kh_ban'],
            'chuoi': [[y['ngay'], rong(y)] for y in ds[-52:]]}


def _gio(s) -> datetime | None:
    try:
        return datetime.fromisoformat(s) if s else None
    except (TypeError, ValueError):
        return None


def can_tai(ds: list[dict], thu_luc: datetime | None, now: datetime) -> bool:
    """Có nên gọi CFTC lúc này không: chưa có dữ liệu, hoặc báo cáo kế tiếp đã tới giờ công bố; và lần thử trước đã cách THU_LAI_GIO giờ."""
    if thu_luc is not None and now - thu_luc < timedelta(hours=THU_LAI_GIO):
        return False
    if not ds:
        return True
    return now >= datetime.fromisoformat(ds[-1]['ngay']).replace(tzinfo=timezone.utc) + CONG_BO


def tep(cfg: dict) -> Path:
    t = (cfg.get('cot') or {}).get('tep')
    return Path(t) if t else Path(__file__).resolve().parent.parent / 'du-lieu' / 'cot-vang.json'


def _doc(p: Path) -> dict:
    try:
        d = json.loads(p.read_text(encoding='utf-8'))
        return d if isinstance(d, dict) and isinstance(d.get('ds'), list) else {'ds': []}
    except (OSError, ValueError):
        return {'ds': []}


def _luu(p: Path, d: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_suffix('.tmp')
    tam.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
    tam.replace(p)


def cap_nhat(cfg: dict, now: datetime | None = None, tai=None) -> dict:
    """Tải ngay (không xét can_tai) rồi lưu. Lần đầu: mỗi năm một tệp nén rồi tệp tuần. Về sau: chỉ tệp tuần; nếu hở tuần thì lấy thêm tệp năm.
    Tải hỏng: giữ nguyên dữ liệu cũ, ghi lại lỗi và giờ thử. Trả nội dung vừa lưu."""
    now = now or datetime.now(timezone.utc)
    tai = tai or _tai
    p = tep(cfg)
    d = _doc(p)
    ds, loi = d['ds'], None
    try:
        da_lay_nam = not ds
        if da_lay_nam:
            for y in range(int((cfg.get('cot') or {}).get('tu_nam', TU_NAM)), now.year + 1):
                ds = gop(ds, doc_zip(tai(URL_NAM.format(nam=y))))
        cuoi_cu = ds[-1]['ngay'] if ds else None
        moi = doc_van(tai(URL_TUAN).decode('latin-1'))
        if not moi:
            raise ValueError('tệp tuần của CFTC không có dòng vàng COMEX')
        ds = gop(ds, moi)
        if not da_lay_nam and cuoi_cu and (date.fromisoformat(moi[-1]['ngay']) - date.fromisoformat(cuoi_cu)).days > 9:
            for y in range(int(cuoi_cu[:4]), int(moi[-1]['ngay'][:4]) + 1):                # webapp đã tắt hơn một tuần: lấp chỗ hở
                ds = gop(ds, doc_zip(tai(URL_NAM.format(nam=y))))
    except Exception as e:                                                 # noqa: BLE001 - mạng hỏng không được làm mất dữ liệu đang có
        loi = f'{type(e).__name__}: {e}'
    d = {'thu_luc': now.isoformat(), 'tai_luc': d.get('tai_luc') if loi else now.isoformat(), 'loi': loi, 'ds': ds}
    try:
        _luu(p, d)
    except OSError as e:
        d['loi'] = loi or f'Không lưu được tệp COT: {e}'
    return d


def lay(cfg: dict, now: datetime | None = None, tai=None, cho: bool = False) -> dict:
    """Dữ liệu đang có trên đĩa, kèm tóm tắt. Tới hạn thì tải ở nền (cho=True: tải xong mới trả). Chưa bật trong cấu hình: {'bat': False}."""
    if not (cfg.get('cot') or {}).get('bat'):
        return {'bat': False}
    now = now or datetime.now(timezone.utc)
    d = _doc(tep(cfg))
    if can_tai(d['ds'], _gio(d.get('thu_luc')), now):
        with _khoa:
            start = not _tt['dang']
            if start:
                _tt['dang'] = True

        def lam():
            try:
                cap_nhat(cfg, now, tai)
            finally:
                with _khoa:
                    _tt['dang'] = False

        if start and cho:
            lam()
            d = _doc(tep(cfg))
        elif start:
            threading.Thread(target=lam, name='cot', daemon=True).start()
    return {'bat': True, 'san_sang': bool(d['ds']), 'dang_tai': _tt['dang'], 'loi': d.get('loi'), 'tai_luc': d.get('tai_luc'),
            'tom': tom(d['ds'], now), 'tuan': len(d['ds']), 'tu': d['ds'][0]['ngay'] if d['ds'] else None}
