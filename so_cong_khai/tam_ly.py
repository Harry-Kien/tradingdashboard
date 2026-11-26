"""Tâm lý thị trường từ nguồn công khai, cập nhật ở luồng nền.

1. Vị thế của dòng tiền đầu cơ trên hợp đồng tương lai, theo báo cáo Commitments of Traders của CFTC (cftc.gov, công bố thứ Sáu, số chốt thứ Ba):
   - báo cáo Traders in Financial Futures (TFF) cho 8 đồng tiền, USD index, chỉ số Mỹ và Nhật, Bitcoin và Ether của CME: nhóm "Leveraged Funds"
     (quỹ đầu cơ, CTA) và nhóm "Asset Manager" (quỹ đầu tư dài hạn);
   - báo cáo tách nhóm (Disaggregated) cho vàng, bạc, dầu WTI, đồng: nhóm "Managed Money".
   Mỗi mã có vị thế ròng (mua − bán), thay đổi so với tuần trước, ròng so với hợp đồng mở, và thứ hạng trong 3 năm (0 = bán ròng nhiều nhất,
   100 = mua ròng nhiều nhất trong 156 tuần). Lần đầu tải các tệp năm (từ 3 năm trước, khoảng 0,7 MB và 1–3 MB mỗi năm), về sau chỉ tải tệp tuần.
2. Chỉ số Sợ hãi & Tham lam của thị trường crypto (alternative.me), 0–100, mỗi ngày một số.

Nhà giao dịch nhỏ lẻ (tỷ lệ lệnh mua/bán ở các sàn) không có ở đây: các nguồn công khai (Myfxbook, IG, OANDA) chặn tải tự động hoặc đòi tài khoản.
Đã đo trên vàng (kiem_cot.py): vị thế COT đi theo giá, không báo trước được giá; đây là bối cảnh, không phải tín hiệu vào lệnh.
Chỉ tải về, không gửi dữ liệu nào. Tắt: `"tam_ly": {"bat": false}`."""
from __future__ import annotations

import csv
import io
import json
import os
import threading
import time
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

URL = {
    'tff_tuan': 'https://www.cftc.gov/dea/newcot/FinFutWk.txt',
    'tff_nam': 'https://www.cftc.gov/files/dea/history/fut_fin_txt_{nam}.zip',
    'dis_tuan': 'https://www.cftc.gov/dea/newcot/f_disagg.txt',
    'dis_nam': 'https://www.cftc.gov/files/dea/history/fut_disagg_txt_{nam}.zip',
    'fng': 'https://api.alternative.me/fng/?limit=60',
}
# mã hợp đồng CFTC: (nhãn, tên, nhóm, báo cáo, mã giao dịch tương ứng ở sàn, chiều: +1 nếu mua hợp đồng = mua mã đó)
HD = {
    '099741': ('EUR', 'Euro', 'tien', 'tff', 'EURUSD', 1), '096742': ('GBP', 'Bảng Anh', 'tien', 'tff', 'GBPUSD', 1),
    '097741': ('JPY', 'Yên Nhật', 'tien', 'tff', 'USDJPY', -1), '092741': ('CHF', 'Franc Thụy Sĩ', 'tien', 'tff', 'USDCHF', -1),
    '090741': ('CAD', 'Đô la Canada', 'tien', 'tff', 'USDCAD', -1), '232741': ('AUD', 'Đô la Úc', 'tien', 'tff', 'AUDUSD', 1),
    '112741': ('NZD', 'Đô la New Zealand', 'tien', 'tff', 'NZDUSD', 1), '095741': ('MXN', 'Peso Mexico', 'tien', 'tff', '', 1),
    '098662': ('USD', 'USD index (ICE)', 'tien', 'tff', '', 1),
    '13874A': ('US500', 'S&P 500 E-mini', 'chi_so', 'tff', 'US500', 1), '209742': ('USTEC', 'Nasdaq 100 mini', 'chi_so', 'tff', 'USTEC', 1),
    '124603': ('US30', 'Dow Jones ($5)', 'chi_so', 'tff', 'US30', 1), '240741': ('JAPAN', 'Nikkei 225', 'chi_so', 'tff', 'JAPAN', 1),
    '133741': ('BTC', 'Bitcoin (CME)', 'crypto', 'tff', 'BTCUSDT', 1), '146021': ('ETH', 'Ether (CME)', 'crypto', 'tff', 'ETHUSDT', 1),
    '088691': ('XAU', 'Vàng (COMEX)', 'hang_hoa', 'dis', 'XAUUSD', 1), '084691': ('XAG', 'Bạc (COMEX)', 'hang_hoa', 'dis', 'XAGUSD', 1),
    '067651': ('WTI', 'Dầu WTI (NYMEX)', 'hang_hoa', 'dis', 'CRUDE', 1), '085692': ('COPPER', 'Đồng (COMEX)', 'hang_hoa', 'dis', '', 1),
}
NHOM = {'tien': 'Tiền tệ', 'chi_so': 'Chỉ số', 'crypto': 'Crypto', 'hang_hoa': 'Hàng hóa'}
# cột trong tệp CFTC (đếm từ 0): hợp đồng mở, nhóm đầu cơ mua/bán, nhóm thứ hai mua/bán
COT_TFF = {'oi': 7, 'dc_mua': 14, 'dc_ban': 15, 'am_mua': 11, 'am_ban': 12}
COT_DIS = {'oi': 7, 'dc_mua': 13, 'dc_ban': 14, 'am_mua': 8, 'am_ban': 9}       # Managed Money; nhóm thứ hai = nhà sản xuất/người dùng
CUA_SO = 156
SO_NAM = 3
_khoa = threading.Lock()
_tt: dict = {'loi': {}, 'nho': None}


def doc_dong(van: str, bao_cao: str) -> list[dict]:
    """Các dòng của những hợp đồng trong HD từ một tệp CFTC dạng chữ (có hoặc không có dòng tiêu đề)."""
    c = COT_TFF if bao_cao == 'tff' else COT_DIS
    out = []
    for r in csv.reader(io.StringIO(van)):
        if len(r) < 20:
            continue
        ma = r[3].strip()
        if ma not in HD or HD[ma][3] != bao_cao:
            continue
        try:
            x = {'ma': ma, 'ngay': r[2].strip()[:10], **{k: int(float(r[i])) for k, i in c.items()}}
        except ValueError:
            continue
        out.append(x)
    return out


def doc_zip(b: bytes, bao_cao: str) -> list[dict]:
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        return [x for n in z.namelist() for x in doc_dong(z.read(n).decode('latin-1'), bao_cao)]


def gop(cu: list[dict], moi: list[dict]) -> list[dict]:
    theo = {(x['ma'], x['ngay']): x for x in cu}
    for x in moi:
        theo[(x['ma'], x['ngay'])] = x
    return sorted(theo.values(), key=lambda x: (x['ma'], x['ngay']))


def tom_tat(ds: list[dict]) -> list[dict]:
    """Mỗi hợp đồng một dòng: vị thế ròng tuần gần nhất, thay đổi, % hợp đồng mở, thứ hạng 3 năm, 52 tuần gần nhất để vẽ."""
    theo: dict = {}
    for x in ds:
        theo.setdefault(x['ma'], []).append(x)
    out = []
    for ma, v in theo.items():
        v = sorted(v, key=lambda x: x['ngay'])[-CUA_SO:]
        if len(v) < 2:
            continue
        rong = [x['dc_mua'] - x['dc_ban'] for x in v]
        am = [x['am_mua'] - x['am_ban'] for x in v]
        cuoi, truoc = rong[-1], rong[-2]
        lo, hi = min(rong), max(rong)
        hang = round((cuoi - lo) / (hi - lo) * 100, 1) if hi > lo else 50.0
        nh, ten, nhom, bc, sym, chieu = HD[ma]
        out.append({'ma': ma, 'nhan': nh, 'ten': ten, 'nhom': nhom, 'bao_cao': bc, 'sym': sym, 'chieu': chieu, 'ngay': v[-1]['ngay'],
                    'rong': cuoi, 'doi': cuoi - truoc, 'oi': v[-1]['oi'], 'pct_oi': round(cuoi / v[-1]['oi'] * 100, 1) if v[-1]['oi'] else None,
                    'hang': hang, 'so_tuan': len(v), 'am_rong': am[-1], 'am_doi': am[-1] - am[-2], 'lich_su': rong[-52:],
                    'cuc_doan': 'mua' if hang >= 90 else 'ban' if hang <= 10 else None})
    moi_nhat = max((x['ngay'] for x in out), default='')
    for x in out:                                                            # hợp đồng CFTC đã ngừng báo cáo (ví dụ Nikkei từ 3/2026): đánh dấu số cũ
        x['cu'] = bool(moi_nhat) and (datetime.fromisoformat(moi_nhat) - datetime.fromisoformat(x['ngay'])).days > 21
    thu_tu = list(HD)
    return sorted(out, key=lambda x: thu_tu.index(x['ma']))


def _tai(url: str, cho: float = 60.0, toi_da: int = 40_000_000) -> bytes:
    rq = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; so-cong-khai/1.0)'})   # noqa: S310 - địa chỉ https cố định, chỉ tải về
    with urllib.request.urlopen(rq, timeout=cho) as r:                       # noqa: S310 - địa chỉ https cố định, chỉ tải về
        b = r.read(toi_da + 1)
    if len(b) > toi_da:
        raise RuntimeError('tệp lớn bất thường, không nhận')
    return b


def _tep(cfg: dict, goc: Path) -> Path:
    p = Path(os.path.expandvars((cfg.get('tam_ly') or {}).get('tep', 'du-lieu/tam-ly.json')))
    return p if p.is_absolute() else goc / p


def doc(cfg: dict, goc: Path) -> dict:
    f = _tep(cfg, goc)
    try:
        st = f.stat()
    except OSError:
        return {}
    key = (st.st_mtime_ns, st.st_size)
    if _tt['nho'] and _tt['nho'][0] == key:
        return _tt['nho'][1]
    try:
        d = json.loads(f.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    _tt['nho'] = (key, d)
    return d


def _luu(cfg: dict, goc: Path, d: dict) -> None:
    f = _tep(cfg, goc)
    f.parent.mkdir(parents=True, exist_ok=True)
    tam = f.with_suffix('.tmp')
    tam.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
    tam.replace(f)


def cap_nhat(cfg: dict, goc: Path, tai=_tai, now: datetime | None = None) -> dict:
    """Một lượt cập nhật: tệp năm còn thiếu (lần đầu), tệp tuần (mỗi 6 giờ), chỉ số sợ hãi/tham lam (mỗi 6 giờ). Lỗi nguồn nào ghi riêng nguồn đó."""
    now = now or datetime.now(timezone.utc)
    with _khoa:
        d = dict(doc(cfg, goc))
        ds = d.get('cot', [])
        da_nam = set(d.get('da_nam', []))
        nam_luc = d.get('nam_luc')
        lam_moi = not nam_luc or now - datetime.fromisoformat(nam_luc) >= timedelta(days=7)    # tệp năm hiện tại: tải lại mỗi tuần để lấp tuần bị lỡ
        for bc in ('tff', 'dis'):
            for y in range(now.year - SO_NAM, now.year + 1):
                k = f'{bc}{y}'
                if k in da_nam and (y < now.year or not lam_moi):
                    continue
                try:
                    ds = gop(ds, doc_zip(tai(URL[f'{bc}_nam'].format(nam=y)), bc))
                    da_nam.add(k)
                    _tt['loi'].pop(k, None)
                except Exception as e:                                       # noqa: BLE001
                    _tt['loi'][k] = f'{type(e).__name__}: {e}'[:200]
        if lam_moi and all(f'{bc}{now.year}' in da_nam for bc in ('tff', 'dis')):
            d['nam_luc'] = now.isoformat()
        cu = d.get('tuan_luc')
        if not cu or now - datetime.fromisoformat(cu) >= timedelta(hours=6):
            ok = True
            for bc in ('tff', 'dis'):
                try:
                    ds = gop(ds, doc_dong(tai(URL[f'{bc}_tuan']).decode('latin-1'), bc))
                    _tt['loi'].pop(bc, None)
                except Exception as e:                                       # noqa: BLE001
                    _tt['loi'][bc] = f'{type(e).__name__}: {e}'[:200]
                    ok = False
            if ok:
                d['tuan_luc'] = now.isoformat()
        moc = (now - timedelta(weeks=CUA_SO + 8)).date().isoformat()
        d['cot'] = [x for x in ds if x['ngay'] >= moc]
        d['da_nam'] = sorted(da_nam)
        cu = d.get('fng_luc')
        if not cu or now - datetime.fromisoformat(cu) >= timedelta(hours=6):
            try:
                j = json.loads(tai(URL['fng'], 30, 1_000_000).decode('utf-8'))
                d['fng'] = [{'gt': int(x['value']), 'nhan': x.get('value_classification', ''), 't': int(x['timestamp'])} for x in j.get('data', [])]
                d['fng_luc'] = now.isoformat()
                _tt['loi'].pop('fng', None)
            except Exception as e:                                           # noqa: BLE001
                _tt['loi']['fng'] = f'{type(e).__name__}: {e}'[:200]
        _luu(cfg, goc, d)
    return lay(cfg, goc)


FNG_VI = {'Extreme Fear': 'Sợ hãi tột độ', 'Fear': 'Sợ hãi', 'Neutral': 'Trung tính', 'Greed': 'Tham lam', 'Extreme Greed': 'Tham lam tột độ'}


def lay(cfg: dict, goc: Path) -> dict:
    d = doc(cfg, goc)
    fng = d.get('fng') or []
    return {'cot': tom_tat(d.get('cot', [])), 'nhom': NHOM, 'tuan_luc': d.get('tuan_luc'),
            'fng': ({'gt': fng[0]['gt'], 'nhan': FNG_VI.get(fng[0]['nhan'], fng[0]['nhan']), 't': fng[0]['t'],
                     'truoc': fng[1]['gt'] if len(fng) > 1 else None, 'tuan': fng[7]['gt'] if len(fng) > 7 else None,
                     'lich_su': [x['gt'] for x in reversed(fng[:60])]} if fng else None),
            'fng_luc': d.get('fng_luc'), 'loi': dict(_tt['loi'])}


class VongTamLy(threading.Thread):
    """Luồng nền: kiểm mỗi 30 phút, tải khi đến hạn (xem cap_nhat)."""

    def __init__(self, lay_cfg, goc: Path):
        super().__init__(name='tam-ly', daemon=True)
        self._lay_cfg, self._goc = lay_cfg, goc

    def run(self) -> None:
        while True:
            try:
                cfg = self._lay_cfg()
                if (cfg.get('tam_ly') or {}).get('bat', True):
                    cap_nhat(cfg, self._goc)
            except Exception as e:                                           # noqa: BLE001
                _tt['loi']['vong'] = f'{type(e).__name__}: {e}'[:200]
            time.sleep(30 * 60)
