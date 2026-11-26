"""Tin tức thị trường: gom tiêu đề từ các nguồn RSS công khai, gắn nhãn đồng tiền / tài sản liên quan, lưu 7 ngày.

Nguồn mặc định (đổi trong `tin_tuc.nguon` của cau-hinh.json):
- InvestingLive (tên mới của ForexLive): tin nhanh Forex, lãi suất, vàng, dầu, chỉ số, cập nhật liên tục trong phiên.
- CNBC, mục tiền tệ.
- Thông cáo của Fed, ECB, BoE (Ngân hàng Anh).
FXStreet, Investing.com chặn tải tự động nên không dùng; FXEmpire bị bỏ vì lẫn bài quảng cáo sàn và nội dung do AI viết.

Chỉ lưu tiêu đề, đường dẫn, giờ đăng và một đoạn tóm tắt ngắn (tối đa 240 ký tự) do nguồn cung cấp; bấm tiêu đề để đọc bài gốc ở trang của nguồn.
Chỉ tải về, không gửi dữ liệu nào. Tải hỏng ở một nguồn thì giữ tin cũ của nguồn đó, các nguồn khác vẫn chạy. Tắt: `"tin_tuc": {"bat": false}`."""
from __future__ import annotations

import html
import json
import os
import re
import threading
import time
import urllib.request
from defusedxml import ElementTree as DET
from defusedxml.common import DefusedXmlException
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

NGUON = [
    {'id': 'investinglive', 'ten': 'InvestingLive (ForexLive)', 'url': 'https://investinglive.com/feed/news', 'loai': 'tin'},
    {'id': 'cnbc', 'ten': 'CNBC · Tiền tệ', 'url': 'https://www.cnbc.com/id/15839069/device/rss/rss.html', 'loai': 'tin'},
    {'id': 'fed', 'ten': 'Fed', 'url': 'https://www.federalreserve.gov/feeds/press_all.xml', 'loai': 'ngan_hang', 'nhan': ['USD']},
    {'id': 'ecb', 'ten': 'ECB', 'url': 'https://www.ecb.europa.eu/rss/press.html', 'loai': 'ngan_hang', 'nhan': ['EUR']},
    {'id': 'boe', 'ten': 'BoE', 'url': 'https://www.bankofengland.co.uk/rss/news', 'loai': 'ngan_hang', 'nhan': ['GBP']},
]
GIU_NGAY = 7
TOI_DA = 400
# Nhãn: (mã nhãn, tên hiện, mẫu tìm trong tiêu đề + tóm tắt, không phân biệt hoa thường)
NHAN = [
    ('USD', 'USD', r'\b(dollar|greenback|dxy|fed|fomc|powell|u\.?s\.? (cpi|pce|gdp|jobs|payrolls|treasur\w*|yields?|economy)|non-?farm|nfp|treasur(y|ies))\b|usd'),
    ('EUR', 'EUR', r'\b(euro(zone|pean central bank|-area)?|ecb|lagarde|german\w*|bund|eur|france|french|ital\w*|spain|spanish|belgi\w*|dutch|netherlands|austria\w*)\b'),
    ('GBP', 'GBP', r'\b(pound|sterling|cable|boe|bank of england|bailey|uk|britain|british|gbp)\b'),
    ('JPY', 'JPY', r'\b(yen|boj|bank of japan|ueda|japan\w*|jgb|jpy)\b'),
    ('CHF', 'CHF', r'\b(franc|snb|swiss|chf)\b'),
    ('CAD', 'CAD', r'\b(loonie|boc|bank of canada|macklem|canad\w*|cad)\b'),
    ('AUD', 'AUD', r'\b(aussie|rba|reserve bank of australia|australia\w*|aud)\b'),
    ('NZD', 'NZD', r'\b(kiwi|rbnz|new zealand|nzd)\b'),
    ('CNY', 'CNY', r'\b(yuan|renminbi|pboc|china|chinese|cnh|cny)\b'),
    ('XAU', 'Vàng', r'\b(gold|bullion|xau)\b'),
    ('XAG', 'Bạc', r'\b(silver|xag)\b'),
    ('OIL', 'Dầu', r'\b(oil|crude|brent|wti|opec\+?)\b'),
    ('IDX', 'Chứng khoán', r'\b(stocks?|equit(y|ies)|s&p|nasdaq|dow|nikkei|dax|ftse|wall street)\b'),
    ('CRYPTO', 'Crypto', r'\b(bitcoin|btc|crypto\w*|ether(eum)?|eth)\b'),
]
_MAU = [(k, n, re.compile(m, re.I)) for k, n, m in NHAN]
QUAN_TRONG = re.compile(r'\b(breaking|rate decision|raises rates|cuts rates|hikes|holds rates|surprise|intervention|non-?farm|cpi|fomc|emergency)\b', re.I)
_khoa = threading.Lock()
_tt: dict = {'nguon': {}, 'nho': None}


_MY = re.compile(r'\b(US|U\.S\.|America\w*|Wall Street)(?![A-Za-z])')            # phân biệt hoa thường: "US" là nước Mỹ, "us" là đại từ


def gan_nhan(chu: str, them: list[str] | None = None) -> list[str]:
    """Các nhãn đồng tiền / tài sản xuất hiện trong đoạn chữ (cộng nhãn cố định của nguồn, ví dụ Fed → USD)."""
    co = {k for k, _, m in _MAU if m.search(chu or '')} | set(them or [])
    if _MY.search(chu or ''):
        co.add('USD')
    return [k for k, _, _ in NHAN if k in co]


def _sach(s: str | None, toi_da: int = 240) -> str:
    s = re.sub(r'<[^>]+>', ' ', html.unescape(s or ''))
    s = re.sub(r'\s+([.,;:!?])', r'\1', re.sub(r'\s+', ' ', s)).strip()
    return s if len(s) <= toi_da else s[:toi_da - 1].rsplit(' ', 1)[0] + '…'


def _phan_tich_xml(body: bytes):
    """RSS từ mạng: luôn chặn DTD/ENTITY, kể cả UTF-16 hay khai báo sau prolog dài."""
    try:
        return DET.fromstring(body, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except DefusedXmlException as e:
        raise ValueError('tệp RSS có khai báo DOCTYPE/ENTITY: từ chối') from e


def doc_rss(body: bytes, nguon: dict) -> list[dict]:
    """RSS 2.0 → [{id, t (ISO UTC), tieu_de, tom_tat, link, nguon, loai, nhan, quan_trong}]. Bỏ mục thiếu tiêu đề, đường dẫn hay giờ."""
    root = _phan_tich_xml(body)
    out = []
    for it in root.iter('item'):
        tieu = _sach(it.findtext('title'), 300)
        link = (it.findtext('link') or it.findtext('guid') or '').strip()
        ngay = (it.findtext('pubDate') or '').strip()
        if not tieu or not link.startswith(('http://', 'https://')) or not ngay:
            continue
        try:
            t = parsedate_to_datetime(ngay).astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
        tom = _sach(it.findtext('description'))
        if tom == tieu:
            tom = ''
        chu = f'{tieu} {tom}'
        out.append({'id': link, 't': t.isoformat(), 'tieu_de': tieu, 'tom_tat': tom, 'link': link, 'nguon': nguon['ten'], 'ma_nguon': nguon['id'],
                    'loai': nguon.get('loai', 'tin'), 'nhan': gan_nhan(chu, nguon.get('nhan')),'quan_trong': bool(QUAN_TRONG.search(tieu)) or nguon.get('loai') == 'ngan_hang'})
    return out


def gop(cu: list[dict], moi: list[dict], now: datetime | None = None) -> list[dict]:
    """Gộp theo đường dẫn (bản mới thay bản cũ), bỏ tin cũ hơn GIU_NGAY ngày, giữ tối đa TOI_DA tin mới nhất."""
    now = now or datetime.now(timezone.utc)
    moc = (now - timedelta(days=GIU_NGAY)).isoformat()
    theo = {x['id']: x for x in cu if x.get('t', '') >= moc}
    for x in moi:
        if x['t'] >= moc:
            theo[x['id']] = x
    return sorted(theo.values(), key=lambda x: x['t'], reverse=True)[:TOI_DA]


def _tai_url(url: str, cho: float = 20.0) -> bytes:
    rq = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; so-cong-khai/1.0)', 'Accept': 'application/rss+xml, application/xml, text/xml'})   # noqa: S310 - địa chỉ https cố định, chỉ tải về
    with urllib.request.urlopen(rq, timeout=cho) as r:                       # noqa: S310 - địa chỉ https cố định trong cấu hình, chỉ tải về
        return r.read(3_000_000)


def _tep(cfg: dict, goc: Path) -> Path:
    p = Path(os.path.expandvars((cfg.get('tin_tuc') or {}).get('tep', 'du-lieu/tin-tuc.json')))
    return p if p.is_absolute() else goc / p


def doc(cfg: dict, goc: Path) -> dict:
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


def tai(cfg: dict, goc: Path, tai_url=_tai_url, now: datetime | None = None) -> dict:
    """Tải mọi nguồn một lượt, gộp và lưu. Nguồn hỏng chỉ ghi lỗi của nó."""
    now = now or datetime.now(timezone.utc)
    nguon = (cfg.get('tin_tuc') or {}).get('nguon') or NGUON
    moi = []
    for n in nguon:
        tt = _tt['nguon'].setdefault(n['id'], {'ten': n['ten']})
        try:
            ds = doc_rss(tai_url(n['url']), n)
            moi += ds
            tt.update(luc=now.isoformat(), loi=None, so=len(ds))
        except Exception as e:                                               # noqa: BLE001 - một nguồn hỏng không chặn nguồn khác
            tt.update(loi=f'{type(e).__name__}: {e}'[:200], thu_luc=now.isoformat())
    with _khoa:
        ds = gop(doc(cfg, goc).get('ds', []), moi, now)
        f = _tep(cfg, goc)
        f.parent.mkdir(parents=True, exist_ok=True)
        tam = f.with_suffix('.tmp')
        tam.write_text(json.dumps({'tai_luc': now.isoformat(), 'ds': ds}, ensure_ascii=False), encoding='utf-8')
        tam.replace(f)
    return trang_thai()


def trang_thai() -> dict:
    return {'nguon': {k: dict(v) for k, v in _tt['nguon'].items()}}


def lay(cfg: dict, goc: Path, nhan: str = '', q: str = '', so: int = 120) -> dict:
    """Tin cho trang: lọc theo nhãn và chữ (không dấu, không phân biệt hoa thường)."""
    d = doc(cfg, goc)
    ds = d.get('ds', [])
    if nhan:
        ds = [x for x in ds if nhan in x.get('nhan', [])]
    if q:
        ql = q.lower()
        ds = [x for x in ds if ql in (x['tieu_de'] + ' ' + x.get('tom_tat', '')).lower()]
    return {'tai_luc': d.get('tai_luc'), 'ds': ds[:max(1, min(int(so), TOI_DA))], 'tong': len(d.get('ds', [])),
            'nhan': [{'k': k, 'n': n} for k, n, _ in NHAN], **trang_thai()}


class VongTin(threading.Thread):
    """Luồng nền: tải lại mọi nguồn mỗi `tin_tuc.phut` phút (mặc định 5)."""

    def __init__(self, lay_cfg, goc: Path):
        super().__init__(name='tin-tuc', daemon=True)
        self._lay_cfg, self._goc = lay_cfg, goc

    def run(self) -> None:
        lan = 0.0
        while True:
            try:
                cfg = self._lay_cfg()
                tt = cfg.get('tin_tuc') or {}
                if tt.get('bat', True) and time.monotonic() - lan >= max(2.0, float(tt.get('phut', 5))) * 60:
                    lan = time.monotonic()
                    tai(cfg, self._goc)
            except Exception:                                                # noqa: BLE001
                pass
            time.sleep(20)
