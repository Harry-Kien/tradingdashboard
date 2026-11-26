"""Lịch tin kinh tế nhiều đồng tiền, tải từ mạng (tệp lịch công khai theo tuần của ForexFactory, qua nfs.faireconomy.media).

Vì sao: tệp lịch mà EA xuất từ MT5 chỉ có tin USD. Tệp tuần này của ForexFactory có các đồng tiền lớn (USD, EUR, GBP, JPY, AUD, CAD, NZD, CHF, CNY),
mức ảnh hưởng (High/Medium/Low/Holiday), số dự báo và số kỳ trước; không có số thực tế.

Cách làm: một luồng nền tải tệp mỗi giờ (`lich_mang.gio`), chỉ tải về, không gửi dữ liệu nào, không kèm thông tin của chủ máy. Tải hỏng (mất mạng,
bị giới hạn số lần) thì giữ dữ liệu cũ và thử lại sau 15 phút. Nguồn chỉ có tuần hiện tại, nên mỗi lần tải được gộp vào `du-lieu/lich-tin-mang.json`
(giữ 60 ngày) để vẫn còn lịch của tuần trước khi sang tuần mới.

Phần này CHỈ dùng để hiển thị trên trang Thị trường. Phần né tin của các luật, cảnh báo trước tin và phân tích điểm vào vẫn dùng tệp lịch USD của EA
(gia.tin_usd), không đổi. Tắt bằng `"lich_mang": {"bat": false}` trong cau-hinh.json."""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

URL = 'https://nfs.faireconomy.media/ff_calendar_thisweek.json'
MUC = {'High': 3, 'Medium': 2, 'Low': 1, 'Holiday': 0}
GIU_NGAY = 60
_khoa = threading.Lock()
_tt: dict = {'lan_tai': None, 'loi': None, 'thu_sau': 0.0, 'nho': None}


def _tep(cfg: dict, goc: Path) -> Path:
    p = Path(os.path.expandvars((cfg.get('lich_mang') or {}).get('tep', 'du-lieu/lich-tin-mang.json')))
    return p if p.is_absolute() else goc / p


def chuan_hoa(ds: list) -> list[dict]:
    """Dòng của nguồn → dạng của webapp: {t (ISO UTC), tien, muc 0–3, ten, du_bao, truoc}. Bỏ dòng hỏng."""
    out = []
    for x in ds or []:
        try:
            t = datetime.fromisoformat(str(x['date'])).astimezone(timezone.utc)
            out.append({'t': t.isoformat(), 'tien': str(x.get('country', '')).strip().upper(), 'muc': MUC.get(str(x.get('impact', '')).strip(), 1),
                        'ten': str(x.get('title', '')).strip(), 'du_bao': str(x.get('forecast') or '').strip(), 'truoc': str(x.get('previous') or '').strip()})
        except (KeyError, ValueError, TypeError):
            continue
    return out


def gop(cu: list[dict], moi: list[dict], now: datetime | None = None) -> list[dict]:
    """Gộp lần tải mới vào dữ liệu đã lưu: dòng cùng (giờ, đồng tiền, tên) lấy bản mới; bỏ dòng cũ hơn GIU_NGAY ngày."""
    now = now or datetime.now(timezone.utc)
    moc = (now - timedelta(days=GIU_NGAY)).isoformat()
    theo = {(e['t'], e['tien'], e['ten']): e for e in cu if e.get('t', '') >= moc}
    for e in moi:
        theo[(e['t'], e['tien'], e['ten'])] = e
    return sorted(theo.values(), key=lambda e: (e['t'], -e['muc'], e['tien']))


def _tai_url(url: str, cho: float = 20.0) -> list:
    rq = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; so-cong-khai/1.0)', 'Accept': 'application/json'})   # noqa: S310 - địa chỉ https cố định, chỉ tải về
    with urllib.request.urlopen(rq, timeout=cho) as r:                       # noqa: S310 - địa chỉ cố định https, chỉ tải về
        body = r.read(2_000_000)
    try:
        d = json.loads(body.decode('utf-8'))
    except ValueError as e:
        raise RuntimeError('nguồn không trả JSON (có thể đang giới hạn số lần tải)') from e
    if not isinstance(d, list):
        raise RuntimeError('dữ liệu lịch không đúng dạng')
    return d


def tai(cfg: dict, goc: Path, tai_url=_tai_url, now: datetime | None = None) -> dict:
    """Tải một lần, gộp và lưu. Trả trạng thái. Lỗi thì giữ dữ liệu cũ."""
    lm = cfg.get('lich_mang') or {}
    f = _tep(cfg, goc)
    now = now or datetime.now(timezone.utc)
    with _khoa:
        try:
            moi = chuan_hoa(tai_url(lm.get('url', URL)))
            if not moi:
                raise RuntimeError('lịch tải về không có sự kiện nào')
            cu = doc(cfg, goc).get('ds', [])
            ds = gop(cu, moi, now)
            f.parent.mkdir(parents=True, exist_ok=True)
            tam = f.with_suffix('.tmp')
            tam.write_text(json.dumps({'nguon': 'ForexFactory (nfs.faireconomy.media)', 'tai_luc': now.isoformat(), 'ds': ds}, ensure_ascii=False), encoding='utf-8')
            tam.replace(f)
            _tt.update(lan_tai=now.isoformat(), loi=None, nho=None)
        except Exception as e:                                               # noqa: BLE001 - mất mạng hay nguồn đổi dạng không được làm hỏng webapp
            _tt.update(loi=f'{type(e).__name__}: {e}', thu_sau=time.monotonic() + 15 * 60)
    return trang_thai()


def doc(cfg: dict, goc: Path) -> dict:
    """Dữ liệu đã lưu (nhớ theo giờ sửa tệp)."""
    f = _tep(cfg, goc)
    try:
        st = f.stat()
    except OSError:
        return {'ds': []}
    key = (st.st_mtime_ns, st.st_size)
    if _tt['nho'] and _tt['nho'][0] == key:
        return _tt['nho'][1]
    try:
        d = json.loads(f.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'ds': []}
    _tt['nho'] = (key, d)
    return d


def trang_thai() -> dict:
    return {'lan_tai': _tt['lan_tai'], 'loi': _tt['loi']}


class VongLich(threading.Thread):
    """Luồng nền: tải khi dữ liệu đã cũ hơn `lich_mang.gio` giờ (mặc định 1), thử lại sau 15 phút nếu hỏng."""

    def __init__(self, lay_cfg, goc: Path):
        super().__init__(name='lich-mang', daemon=True)
        self._lay_cfg, self._goc = lay_cfg, goc

    def run(self) -> None:
        while True:
            try:
                cfg = self._lay_cfg()
                lm = cfg.get('lich_mang') or {}
                if lm.get('bat', True) and time.monotonic() >= _tt['thu_sau']:
                    d = doc(cfg, self._goc)
                    cu = d.get('tai_luc')
                    tuoi = (datetime.now(timezone.utc) - datetime.fromisoformat(cu)).total_seconds() if cu else 1e9
                    if tuoi >= float(lm.get('gio', 1)) * 3600:
                        tai(cfg, self._goc)
                    elif _tt['lan_tai'] is None:
                        _tt['lan_tai'] = cu
            except Exception as e:                                           # noqa: BLE001
                _tt['loi'] = f'{type(e).__name__}: {e}'
            time.sleep(60)
