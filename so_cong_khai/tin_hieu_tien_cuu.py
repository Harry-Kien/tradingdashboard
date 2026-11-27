"""Lưu tín hiệu quan sát tại thời điểm phát sinh và chấm bằng tick Bid/Ask MT5."""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from . import da_ma, song, tin_hieu_ngan as T


PHIEN_BAN_CHAM = 'tick-1'
TEN_TEP = 'tin-hieu-tien-cuu.sqlite3'
HET_NEN = 12
KHOANG_TRONG_MS = 120_000
CHO_DU_LIEU_MS = 24 * 60 * 60_000
CUA_SO_MS = 180_000
CHO_TICK_MS = 2_000
UNG_VIEN_TEP = Path(__file__).resolve().parents[1] / 'tinh' / 'bo-loc-ngan-tien-cuu.json'
PHI_MO_PHONG_XAU_MOI_LOT = 28.  # Khứ hồi USD trên 1 lot, tương ứng 0,28 USD trên 0,01 lot.
KHOA_GHI = threading.Lock()
SCHEMA = '''
BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS tin_hieu (
    id INTEGER PRIMARY KEY,
    may_chu TEXT NOT NULL, ma TEXT NOT NULL, phien TEXT NOT NULL, tf TEXT NOT NULL,
    nen_ms INTEGER NOT NULL, luc_ms INTEGER NOT NULL, tick_ms INTEGER NOT NULL,
    han_ms INTEGER NOT NULL, moc_ms INTEGER NOT NULL,
    loai TEXT NOT NULL, huong TEXT NOT NULL, vao REAL NOT NULL, sl REAL NOT NULL, tp REAL NOT NULL,
    spread REAL NOT NULL, buoc REAL NOT NULL, phi_gia REAL, lich_tin INTEGER NOT NULL,
    tt TEXT NOT NULL DEFAULT 'cho', ra_ms INTEGER, ra REAL, r_rong REAL,
    UNIQUE(may_chu, ma, phien, tf, nen_ms)
);
CREATE INDEX IF NOT EXISTS tien_cuu_cho ON tin_hieu(may_chu, ma, moc_ms) WHERE tt = 'cho';
COMMIT;
'''


def tep(out: Path) -> Path:
    return out / TEN_TEP


def phien(ung_vien: str | None = None) -> str:
    dau = f'{T.PHIEN_NGHIEN_CUU}:{ung_vien}' if ung_vien else T.PHIEN_BAN
    return f'{dau}/{PHIEN_BAN_CHAM}'


@lru_cache(maxsize=1)
def cau_hinh_nghien_cuu() -> dict[str, str]:
    """Chỉ mở theo dõi trên bộ mã nguồn và danh sách ứng viên đã khóa."""
    try:
        c = json.loads(UNG_VIEN_TEP.read_text(encoding='utf-8'))
        dau = hashlib.sha256(Path(T.__file__).read_bytes()).hexdigest()
        if c['version'] == T.PHIEN_NGHIEN_CUU and c['source_sha256'] == dau:
            return {tf: u for tf, u in c['ung_vien'].items() if tf in T.KHUNG and u in T.UNG_VIEN}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return {}


def _ms(x: datetime) -> int:
    return int(x.timestamp() * 1000)


def _dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, timezone.utc)


def _db(out: Path, viet: bool = False) -> sqlite3.Connection:
    p = tep(out)
    if viet:
        p.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(p, timeout=60)
        try:
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name='tien_cuu_cho'").fetchone() is None:
                db.executescript(SCHEMA)
        except sqlite3.Error:
            db.close()
            raise
    else:
        db = sqlite3.connect(p.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    return db


def ma_theo_doi(cfg: dict) -> list[str]:
    cb = cfg.get('canh_bao') or {}
    return list(dict.fromkeys([da_ma.ma_vang(cfg), *str(cb.get('ma_ngan_han') or '').split()]))[:9]


def ghi(out: Path, kq: dict, hoa_hong_usd: float, now: datetime | None = None, *, ung_vien: str | None = None) -> int:
    """Chỉ nhận ảnh chụp mới từ MT5. Ghi lần đầu và giữ nguyên mức giá ban đầu."""
    if kq.get('nguon') != 'mt5' or kq.get('phien_ban') != T.PHIEN_BAN or not kq.get('may_chu') or not any(x['trang_thai'] == 'dat' for x in kq['ds']):
        return 0
    now = now or datetime.now(timezone.utc)
    luc, da_doc, tick = _ms(now), _ms(datetime.fromisoformat(kq['luc'])), kq['tick_ms']
    if not 0 <= luc - da_doc <= T.TUOI_GIA * 1000 or not -5_000 <= luc - tick <= T.TUOI_GIA * 1000:
        return 0
    bid, ask, buoc = kq['bid'], kq['ask'], kq['buoc_gia']
    if not all(math.isfinite(v) for v in (bid, ask, buoc)) or not 0 < bid <= ask or buoc <= 0:
        return 0
    gia_tick = kq.get('gia_tick', 0)
    phi = 0.0 if hoa_hong_usd == 0 else None
    if hoa_hong_usd > 0 and kq.get('tien_tk') == 'USD' and math.isfinite(gia_tick) and gia_tick > 0:
        phi = hoa_hong_usd * buoc / gia_tick
    if ung_vien:
        if ung_vien not in T.UNG_VIEN:
            return 0
        if kq.get('tien_tk') == 'USD' and math.isfinite(gia_tick) and gia_tick > 0 and phi is not None:
            phi = max(phi, PHI_MO_PHONG_XAU_MOI_LOT * buoc / gia_tick - buoc)
        else:
            phi = None
    rows = []
    for a in kq['ds']:
        if a['trang_thai'] != 'dat':
            continue
        dong, het = (_ms(datetime.fromisoformat(a[k])) for k in ('dong', 'het'))
        vao, sl, tp = (a[k] for k in ('vao', 'sl', 'tp'))
        huong = a['huong']
        if not (all(math.isfinite(v) and v > 0 for v in (vao, sl, tp)) and
                ((huong == 'MUA' and sl < vao < tp) or (huong == 'BÁN' and tp < vao < sl))):
            continue
        if not dong <= luc <= min(het, dong + T.HAN_GIAY * 1000) or tick < dong:
            continue
        han = dong + HET_NEN * T.KHUNG[a['tf']] * 60_000
        rows.append((kq['may_chu'], kq['ma'], phien(ung_vien), a['tf'], dong, luc, tick, han, max(luc, tick),
                     a['loai'], huong, vao, sl, tp, ask - bid, buoc, phi, bool(kq['lich_tin'])))
    if not rows:
        return 0
    with KHOA_GHI, closing(_db(out, viet=True)) as db, db:
        # Ứng viên mô phỏng một vị thế đồng thời cho mỗi mã và khung, như trong hồi cứu.
        return db.executemany('''INSERT OR IGNORE INTO tin_hieu(
            may_chu, ma, phien, tf, nen_ms, luc_ms, tick_ms, han_ms, moc_ms, loai, huong, vao, sl, tp, spread, buoc, phi_gia, lich_tin
        ) SELECT ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,? WHERE ?=0 OR NOT EXISTS (
            SELECT 1 FROM tin_hieu WHERE may_chu=? AND ma=? AND phien=? AND tf=? AND tt='cho')''',
                              [(*r, int(bool(ung_vien)), *r[:4]) for r in rows]).rowcount


def cham_mot(s, ds, den_ms: int) -> tuple:
    """Trả mốc đọc và kết quả. Một khoảng thiếu giá làm kết quả không thể xác minh."""
    moc = s['moc_ms']
    mua = s['huong'] == 'MUA'
    dau = 1 if mua else -1
    for ms, bid, ask in ds:
        if ms <= s['moc_ms'] or ms > den_ms or not (math.isfinite(bid) and math.isfinite(ask) and 0 < bid <= ask):
            continue
        if ms - moc > KHOANG_TRONG_MS:
            return moc, 'thieu_tick', None, None, None
        moc = ms
        gia = bid if mua else ask
        if ms >= s['han_ms']:
            tt, ra = 'het_gio', gia
        elif dau * (gia - s['sl']) <= 0:
            tt, ra = 'sl', gia
        elif dau * (gia - s['tp']) >= 0:
            tt, ra = 'tp', s['tp']
        else:
            continue
        # Bid/Ask đã bao gồm spread. Trừ một bước giá trượt giả định và hoa hồng nếu biết.
        r = None if s['phi_gia'] is None else ((ra - s['vao']) * dau - s['buoc'] - s['phi_gia']) / abs(s['vao'] - s['sl'])
        return moc, tt, ms, ra, round(r, 6) if r is not None else None
    tt = 'thieu_tick' if den_ms - moc > KHOANG_TRONG_MS else 'cho'
    return moc, tt, None, None, None


def _doc_tick(mt5, may_chu: str, ma: str, tu: int, den: int) -> list[tuple] | None:
    with song._khoa:
        if mt5 is not song._tt.get('mt5'):
            return None
        if getattr(mt5.account_info(), 'server', '') != may_chu:
            return None
        rows = mt5.copy_ticks_range(ma, _dt(tu // 1000 * 1000), _dt((den // 1000 + 1) * 1000), mt5.COPY_TICKS_INFO)
    if rows is None:
        return None
    ds = [(int(r['time_msc']), float(r['bid']), float(r['ask'])) for r in rows]
    ds.sort(key=lambda r: r[0])  # giữ thứ tự gốc khi nhiều tick trùng mili giây
    return ds


def cap_nhat(out: Path, mt5, may_chu: str, now: datetime | None = None) -> int:
    """Đọc một đoạn tick có giới hạn cho từng mã đang chờ, lưu tiến độ để nối lại."""
    if mt5 is None or not may_chu or not tep(out).is_file():
        return 0
    luc = _ms(now or datetime.now(timezone.utc))
    with closing(_db(out)) as db:
        ds = db.execute("SELECT * FROM tin_hieu WHERE may_chu=? AND tt='cho' ORDER BY moc_ms", (may_chu,)).fetchall()
    nhom: dict[str, list] = {}
    thay = []
    for s in ds:
        if luc - s['han_ms'] > CHO_DU_LIEU_MS:
            thay.append((s['moc_ms'], 'thieu_tick', None, None, None, s['id'], s['moc_ms']))
        else:
            nhom.setdefault(s['ma'], []).append(s)
    for ma, rows in nhom.items():
        tu = rows[0]['moc_ms']
        den = min(luc - CHO_TICK_MS, tu + CUA_SO_MS)
        if den <= tu:
            continue
        ticks = _doc_tick(mt5, may_chu, ma, tu, den)
        if ticks is None:
            continue
        for s in rows:
            kq = cham_mot(s, ticks, den)
            if kq[:2] != (s['moc_ms'], 'cho'):
                thay.append((*kq, s['id'], s['moc_ms']))
    if not thay:
        return 0
    with KHOA_GHI, closing(_db(out, viet=True)) as db, db:
        return db.executemany('''UPDATE tin_hieu SET moc_ms=?, tt=?, ra_ms=?, ra=?, r_rong=?
            WHERE id=? AND moc_ms=? AND tt='cho' ''', thay).rowcount


def tong_hop(out: Path, may_chu: str, ma: str, *, ung_vien: str | None = None) -> dict:
    kq = {'ma': ma, 'may_chu': may_chu, 'phien': phien(ung_vien), 'ds': []}
    if not may_chu or not tep(out).is_file():
        return kq
    sql = '''SELECT tf, loai, COUNT(*) AS so, SUM(tt='cho') AS cho, SUM(tt='thieu_tick') AS thieu_tick,
             SUM(tt IN ('tp','sl','het_gio') AND r_rong IS NULL) AS thieu_phi,
             COUNT(r_rong) AS da_cham, SUM(CASE WHEN r_rong>0 THEN 1 ELSE 0 END) AS thang, AVG(r_rong) AS r_moi
             FROM tin_hieu WHERE may_chu=? AND ma=? AND phien=? GROUP BY tf, loai'''
    with closing(_db(out)) as db:
        rows = db.execute(sql, (may_chu, ma, phien(ung_vien)))
        for r in rows:
            a = dict(r)
            n = a['da_cham']
            if n:
                a['r_moi'] = round(a['r_moi'], 4)
            a['thang_pct'] = round(a['thang'] / n * 100, 1) if n else None
            kq['ds'].append(a)
    kq['ds'].sort(key=lambda a: (T.KHUNG.get(a['tf'], 0), a['loai']))
    return kq


def tong_hop_nghien_cuu(out: Path, may_chu: str, ma: str) -> list[dict]:
    bang = {u: tong_hop(out, may_chu, ma, ung_vien=u)['ds'] for u in set(cau_hinh_nghien_cuu().values())}
    return [{'tf': tf, 'ung_vien': u, 'rr': T.UNG_VIEN[u][1], 'ds': [x for x in bang[u] if x['tf'] == tf]}
            for tf, u in cau_hinh_nghien_cuu().items()]


def ghi_cau_hinh(out: Path, cfg: dict, kq: dict, now: datetime | None = None) -> int:
    return ghi(out, kq, float((cfg.get('hoc') or {}).get('hoa_hong_lot', 0)), now)


def ghi_nghien_cuu(out: Path, cfg: dict, kq: dict) -> int:
    hoa_hong = float((cfg.get('hoc') or {}).get('hoa_hong_lot', 0))
    return sum(ghi(out, {**kq, 'ds': [a]}, hoa_hong, ung_vien=a['ung_vien']) for a in kq.get('nghien_cuu', []))


def chuyen(out: Path, now: datetime | None = None) -> int:
    if not tep(out).is_file():
        return 0
    with song._khoa:
        mt5 = song._tt.get('mt5')
        tk = mt5.account_info() if mt5 is not None and hasattr(mt5, 'account_info') else None
    return cap_nhat(out, mt5, str(getattr(tk, 'server', '') or ''), now)


class VongTienCuu(threading.Thread):
    """Dùng cho bản xem thử: ghi sổ tiến cứu, không mở các vòng nền khác."""

    def __init__(self, nap, thu_muc):
        super().__init__(name='tien-cuu-m5-m15-m30', daemon=True)
        self.nap, self.thu_muc = nap, thu_muc
        self.dung = threading.Event()
        self.loi = None
        self.luc_quet = None
        self.trang_thai = {}

    def run(self):
        while not self.dung.is_set():
            try:
                cfg = self.nap()
                ca = cfg.get('canh_bao') or {}
                if ca.get('tien_cuu', True) and ca.get('ngan_han', True):
                    out = self.thu_muc(cfg)
                    loi = []
                    for ma in ma_theo_doi(cfg):
                        if self.dung.is_set():
                            return
                        try:
                            ung_vien = cau_hinh_nghien_cuu() if ma == da_ma.ma_vang(cfg) else None
                            kq = T.doc(cfg, ma, ung_vien=ung_vien) if ung_vien else T.doc(cfg, ma)
                            ghi_cau_hinh(out, cfg, kq)
                            ghi_nghien_cuu(out, cfg, kq)
                            if kq.get('nguon') == 'mt5' and kq.get('tick_ms'):
                                self.trang_thai[ma] = {'luc': kq['luc'], 'tick_ms': kq['tick_ms'],
                                                      'nghien_cuu': {a['tf']: a['trang_thai'] for a in kq.get('nghien_cuu', [])}}
                            else:
                                self.trang_thai.pop(ma, None)
                                loi.append(f'{ma}: Chưa có tick MT5')
                        except (OSError, ValueError, RuntimeError, sqlite3.Error) as e:
                            loi.append(f'{ma}: {e}')
                    chuyen(out)
                    self.luc_quet = datetime.now(timezone.utc).isoformat()
                    self.loi = '; '.join(loi) or None
            except (OSError, ValueError, RuntimeError, sqlite3.Error) as e:
                self.loi = str(e)
            self.dung.wait(5 if datetime.now(timezone.utc).minute % 5 < 2 else 15)
