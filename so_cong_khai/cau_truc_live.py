"""Theo dõi FVG/iFVG từ MT5, lưu trạng thái và chống gửi lại mỗi mốc Telegram."""
from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

from . import ban_tin_cau_truc as C, da_ma, song, telegram_nhom as T
from .doc_so import VN

GIAY_QUET = 3
GAP_MS = 45_000
HAN_GUI_MS = 90_000
TEN = 'cau-truc-live.sqlite3'
NHAN = {'cham': 'Giá chạm vùng', 'xac_nhan': 'Xác nhận cấu trúc', 'vo_hieu': 'Kịch bản vô hiệu'}
SCHEMA = """
CREATE TABLE IF NOT EXISTS trang_thai(id INTEGER PRIMARY KEY CHECK(id=1), nd TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS su_kien(
    id TEXT PRIMARY KEY, moc_ms INTEGER NOT NULL, nd TEXT NOT NULL,
    tt TEXT NOT NULL, nhom_ma TEXT NOT NULL, msg INTEGER, loi TEXT
);
CREATE INDEX IF NOT EXISTS su_kien_cho ON su_kien(tt,moc_ms);
"""


def cuoi_tuan(now: datetime) -> bool:
    return now.astimezone(VN).weekday() >= 5


def ma_cho(cfg: dict, now: datetime, cau_hinh: str = '') -> str:
    if not cuoi_tuan(now):
        return da_ma.ma_vang(cfg)
    mt5 = da_ma._mt5(cfg['gia'])
    if mt5 is None:
        raise ValueError('Chưa có kết nối MT5.')
    with song._khoa:
        ds = da_ma._hien(mt5)
    uu_tien = (cau_hinh, 'BTCUSDTp', 'BTCUSDp', 'BTCUSDT', 'BTCUSD')
    ma = next((k for k in uu_tien if k in ds), '')
    if cau_hinh and cau_hinh not in ds:
        raise ValueError('Mã Bitcoin đã chọn chưa có trong Market Watch.')
    if not ma:
        ma = next((s for s in sorted(ds) if re.fullmatch(r'BTC(?:USDT|USD)[.\w-]{0,8}', s, re.I)), '')
    if not ma:
        raise ValueError('Không tìm thấy Bitcoin trong Market Watch.')
    return ma


def nhom_ma(c: dict) -> str:
    return hashlib.sha256(str(c.get('chat') or '').encode()).hexdigest()[:12]


def doc_tick(cfg: dict, snap: dict, tu_ms: int) -> list[tuple] | None:
    mt5 = da_ma._mt5(cfg['gia'])
    if mt5 is None:
        return None
    den = snap['tick_ms']
    tu = datetime.fromtimestamp(max(0, tu_ms - 1) / 1000, timezone.utc) - timedelta(seconds=1)
    het = datetime.fromtimestamp(den / 1000, timezone.utc) + timedelta(seconds=1)
    with song._khoa:
        tk = mt5.account_info()
        if hashlib.sha256(str(getattr(tk, 'server', '')).encode()).hexdigest()[:12] != snap['feed']:
            return None
        rows = mt5.copy_ticks_range(snap['ma'], tu, het, mt5.COPY_TICKS_INFO)
    if rows is None:
        return None
    ds = sorted(((int(r['time_msc']), float(r['bid']), float(r['ask'])) for r in rows if tu_ms <= int(r['time_msc']) <= den),
                key=lambda x: x[0])
    if den > tu_ms and not any(t > tu_ms for t, _, _ in ds):
        return None
    return ds


def _moc(snap: dict) -> int:
    return int(datetime.fromisoformat(snap['luc']).timestamp() * 1000)


def _tick_tiep(st: dict, ticks: list[tuple], tu: int) -> list[tuple]:
    """Đọc phần nối thêm của nhóm tick trùng mili giây với mốc cũ."""
    cung_ms = [(t, b, a) for t, b, a in ticks if t == tu]
    cu = [tuple(q) for q in st.get('vet_tick', [])]
    px = [(b, a) for _, b, a in cung_ms]
    if cu and st.get('vet_day_du'):
        moi = cung_ms[len(cu):] if px[:len(cu)] == cu else []
    else:
        moc = cu[-1] if cu else (st.get('bid'), st.get('ask'))
        i = next((j for j in range(len(px) - 1, -1, -1) if px[j] == moc), None)
        moi = cung_ms[i + 1:] if i is not None else []
    return moi + [(t, b, a) for t, b, a in ticks if t > tu]


def tien(st: dict, snap: dict, ticks, mode: str, dest: str) -> tuple[dict, list[dict]]:
    """Xử lý vùng một lần trên mỗi phiên vùng, giữ xác nhận cho từng khung và mốc đóng H1."""
    ma, feed, den = snap['ma'], snap['feed'], snap['tick_ms']
    now = _moc(snap)
    same = (st.get('ma'), st.get('feed'), st.get('mode'), st.get('dest')) == (ma, feed, mode, dest)
    tu = st.get('tick_ms', 0) if same else 0
    if same and (den < tu or (st.get('luc') and now < int(datetime.fromisoformat(st['luc']).timestamp() * 1000))):
        return st, []
    # Chỉ lấy giá hiện tại làm mốc mới khi đổi phiên theo dõi hoặc bị gián đoạn dài.
    # Lỗi đọc tick ngắn phải giữ cả mốc thời gian lẫn trạng thái trong/ngoài vùng để đọc bù.
    khoi_dong = not same or not tu or den - tu > GAP_MS
    lien = not khoi_dong and ticks is not None
    tick_moi = _tick_tiep(st, ticks, tu) if lien else []
    old = st.get('vung', {}) if same else {}
    ds = {z['id']: z for z in snap['vung']}
    vung = {k: {**u, 'tf': dict(u.get('tf') or {})} for k, u in old.items()
            if now // 1000 - u['tu'] <= C.SONG_GIO * 3600}
    out = []

    def them(k, loai, ms, **them_so):
        if -5000 <= now - ms <= HAN_GUI_MS:
            z = vung[k]
            out.append({'id': f'{feed}:{ma}:{k}:{loai}:{them_so.get("tf", "")}', 'ma': ma, 'loai': loai, 'ms': ms, 'vung_id': k,
                        **{x: z[x] for x in ('duoi', 'tren', 'chieu', 'loai_vung', 'vo_hieu')}, 'h1': snap['h1'],
                        'h4': snap['h4'], 'so_le': snap['so_le'], 'bang_chung': snap['bang_chung'], **them_so})

    if snap['gia_moi']:
        for k, z in ds.items():
            if k not in vung:
                px = snap['ask'] if z['chieu'] > 0 else snap['bid']
                vung[k] = {**{x: z[x] for x in ('duoi', 'tren', 'chieu', 'tu', 'vo_hieu')}, 'loai_vung': z['loai'],
                           'bat_dau': den, 'moc_h1': snap['nen_h1_dong'], 'ngoai': not z['duoi'] <= px <= z['tren'], 'tf': {}}
        for k, z in vung.items():
            if z.get('huy'):
                continue
            bar = next(((int(row[0] + 3600) * 1000, row[4]) for row in snap['nen']
                        if row[0] + 3600 > z['moc_h1'] and z['chieu'] * (row[4] - z['vo_hieu']) < 0), None)
            if bar:
                z['huy'] = bar[0]
                them(k, 'vo_hieu', bar[0], gia=bar[1])
                continue
            z['moc_h1'] = max(z['moc_h1'], snap['nen_h1_dong'])
            if khoi_dong and not z.get('cham'):
                px = snap['ask'] if z['chieu'] > 0 else snap['bid']
                z['ngoai'] = not z['duoi'] <= px <= z['tren']
            if lien and k in old and not z.get('cham'):
                for ms, bid, ask in tick_moi:
                    if ms < z['bat_dau'] or not (math.isfinite(ask) and 0 < bid <= ask):
                        continue
                    px = ask if z['chieu'] > 0 else bid
                    if z['duoi'] <= px <= z['tren'] and z['ngoai']:
                        z['cham'] = ms
                        them(k, 'cham', ms, gia=px, bid=bid, ask=ask)
                        break
                    z['ngoai'] = not z['duoi'] <= px <= z['tren']
            if z.get('cham') and k in ds:
                for a in ds[k]['xac_nhan']:
                    tf, ms = a['tf'], int(a.get('luc', 0)) * 1000
                    if a['tt'] == 'xac_nhan' and z['cham'] < ms <= den and tf not in z['tf']:
                        z['tf'][tf] = ms
                        them(k, 'xac_nhan', ms, tf=tf, gia=a['moc'])
    if len(vung) > 24:
        giu = sorted(vung, key=lambda k: (k in ds, vung[k]['bat_dau']), reverse=True)[:24]
        vung = {k: vung[k] for k in giu}
    doc_moi = den if khoi_dong or ticks is not None else tu
    vet = [[bid, ask] for ms, bid, ask in ticks or () if ms == doc_moi and math.isfinite(ask) and 0 < bid <= ask]
    du_vet = bool(vet)
    if not khoi_dong and doc_moi == tu and st.get('vet_tick'):
        cu = st['vet_tick']
        if not vet or (st.get('vet_day_du') and vet[:len(cu)] != cu):
            vet, du_vet = cu, bool(st.get('vet_day_du'))
    if not vet:
        vet = [[snap['bid'], snap['ask']]]
    result = {'ma': ma, 'feed': feed, 'tick_ms': doc_moi, 'luc_tick': den, 'luc': snap['luc'], 'mode': mode, 'dest': dest,
              'tick_luot': len(ticks or ()), 'loi': 'giá cũ' if not snap['gia_moi'] else 'không đọc được đoạn tick' if ticks is None else '',
              'trang_thai': snap['trang_thai'], 'h1': snap['h1'], 'h4': snap['h4'], 'so_le': snap['so_le'], 'vung': vung,
              'hien': list(ds), 'bang_chung': snap['bang_chung'], 'bid': snap['bid'], 'ask': snap['ask'],
              'vet_tick': vet, 'vet_day_du': du_vet}
    return result, sorted(out, key=lambda e: e['ms'])


def van_ban(ev: dict) -> str:
    tt = NHAN[ev['loai']]
    ma = escape(ev['ma'])
    gio = datetime.fromtimestamp(ev['ms'] / 1000, VN)
    fmt = lambda x: C.so(ev, x)  # noqa: E731
    khu = f'{ev["loai_vung"]} H1 {fmt(ev["duoi"])}–{fmt(ev["tren"])}'
    if ev['loai'] == 'vo_hieu':
        step = f'H1 đóng {fmt(ev["gia"])} qua mức vô hiệu {fmt(ev["vo_hieu"])}.'
    elif ev['loai'] == 'xac_nhan':
        step = f'{ev["tf"]} đã đóng và đổi cấu trúc tại {fmt(ev["gia"])} sau cú chạm.'
    else:
        px = 'Ask' if ev['chieu'] > 0 else 'Bid'
        step = f'{px} chạm vùng tại {fmt(ev["gia"])}. Chờ xác nhận ở M5, M15 hoặc M30.'
    lech = ev['h1'] * ev['h4'] < 0 or not ev['h1']
    canh = 'H1/H4 chưa đồng thuận · đứng ngoài.' if lech else 'Cảnh báo quan sát cấu trúc.'
    return f'<b>{tt} · {ma}</b>\n{khu}\n{step}\n{canh}\nMT5 {gio:%H:%M:%S %d/%m} UTC+7 · <code>{ev["bang_chung"]}</code>'


def _db(out: Path, *, write=False):
    p = out / TEN
    if not write:
        return sqlite3.connect(p.resolve().as_uri() + '?mode=ro', uri=True, timeout=3)
    out.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(p, timeout=15)


def tao(out: Path):
    with closing(_db(out, write=True)) as db:
        db.executescript('BEGIN IMMEDIATE;\n' + SCHEMA + '\nCOMMIT;')


def _st(db):
    r = db.execute('SELECT nd FROM trang_thai WHERE id=1').fetchone()
    return json.loads(r[0]) if r else {}


def doc(out: Path) -> dict:
    if not (out / TEN).is_file():
        return {'bat': False, 'su_kien': []}
    with closing(_db(out)) as db:
        st = _st(db)
        rs = db.execute('SELECT nd,tt,loi,msg FROM su_kien ORDER BY moc_ms DESC,rowid DESC LIMIT 12').fetchall()
    hien = {k: st[k] for k in ('ma', 'luc', 'luc_tick', 'mode', 'tick_luot', 'loi', 'trang_thai', 'h1', 'h4', 'so_le',
                                  'bang_chung', 'bid', 'ask') if k in st}
    return {**hien, 'bat': bool(hien) and hien.get('mode') != 'tat',
            'vung': [st['vung'][k] for k in st.get('hien', []) if k in st.get('vung', {})],
            'su_kien': [{**json.loads(nd), 'tt': tt, 'loi': loi, 'msg': msg} for nd, tt, loi, msg in rs]}


def luu(out: Path, snap: dict, ticks, mode: str, dest: str) -> int:
    with closing(_db(out, write=True)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        st, ds = tien(_st(db), snap, ticks, mode, dest)
        db.execute('INSERT OR REPLACE INTO trang_thai(id,nd) VALUES (1,?)', (json.dumps(st, ensure_ascii=False),))
        cho = 'cho' if mode == 'gui' else 'xem'
        n = db.executemany('INSERT OR IGNORE INTO su_kien(id,moc_ms,nd,tt,nhom_ma) VALUES (?,?,?,?,?)',
                           [(x['id'], x['ms'], json.dumps(x, ensure_ascii=False), cho, dest) for x in ds]).rowcount
        da_huy = [(st['ma'], k) for k, z in st['vung'].items() if z.get('huy')]
        db.executemany("""UPDATE su_kien SET tt='het_han' WHERE tt='cho' AND json_extract(nd,'$.loai')<>'vo_hieu'
                        AND json_extract(nd,'$.ma')=? AND json_extract(nd,'$.vung_id')=?""", da_huy)
        return n


def _loi(out: Path, ma: str, mode: str, txt: str):
    with closing(_db(out, write=True)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        st = _st(db)
        if ma and ma != st.get('ma'):
            st = {'ma': ma}
        st.update(loi=txt, mode=mode, luc=datetime.now(timezone.utc).isoformat())
        db.execute('INSERT OR REPLACE INTO trang_thai(id,nd) VALUES (1,?)', (json.dumps(st, ensure_ascii=False),))


def _nhan(out: Path, now: int, dest: str):
    vn = datetime.fromtimestamp(now / 1000, VN)
    moc_lich = vn.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=vn.weekday() % 5)
    con_han = max(now - HAN_GUI_MS, int(moc_lich.timestamp() * 1000))
    with closing(_db(out, write=True)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        db.execute("UPDATE su_kien SET tt='het_han' WHERE tt='cho' AND moc_ms<?", (con_han,))
        db.execute("UPDATE su_kien SET tt='khong_ro' WHERE tt='dang_gui' AND moc_ms<?", (now - 2 * HAN_GUI_MS,))
        st = _st(db)
        if (st.get('mode') != 'gui' or st.get('dest') != dest or st.get('loi') or
                not -5000 <= now - st.get('luc_tick', 0) <= C.TUOI_TICK * 1000):
            return None
        return db.execute("""UPDATE su_kien SET tt='dang_gui' WHERE id=(
            SELECT id FROM su_kien WHERE tt='cho' AND nhom_ma=? AND json_extract(nd,'$.ma')=?
            ORDER BY moc_ms,rowid LIMIT 1) RETURNING id,nd""", (dest, st.get('ma'))).fetchone()


def gui_mot(out: Path, c: dict, token: str, goi, now: datetime | None = None) -> bool:
    if c.get('che_do') != 'gui' or not (token and c.get('chat')):
        return False
    luc = int((now or datetime.now(timezone.utc)).timestamp() * 1000)
    hit = _nhan(out, luc, nhom_ma(c))
    if not hit:
        return False
    id_, nd = hit
    try:
        r = goi(token, 'sendMessage', {'chat_id': c['chat'], 'text': van_ban(json.loads(nd)), 'parse_mode': 'HTML',
                                      'disable_web_page_preview': True})
        tt = 'da_gui' if r.get('ok') else 'loi_gui'
        loi = None if r.get('ok') else T._che(str(r.get('description') or 'Telegram không xác nhận.'), token)[:160]
        msg = (r.get('result') or {}).get('message_id')
    except (OSError, TimeoutError, ValueError, TypeError):
        tt, loi, msg = 'khong_ro', 'Không xác nhận được kết quả gửi.', None
    with closing(_db(out, write=True)) as db, db:
        db.execute('UPDATE su_kien SET tt=?,msg=?,loi=? WHERE id=? AND tt=?', (tt, msg, loi, id_, 'dang_gui'))
    return True


class Vong(threading.Thread):
    def __init__(self, nap, thu_muc, *, gui_that=False):
        super().__init__(name='cau-truc-mt5', daemon=True)
        self.nap, self.thu_muc, self.gui_that = nap, thu_muc, gui_that
        self.dung = threading.Event()

    def _bat(self, c):
        return c.get('cau_truc_live', True) and c.get('che_do') != 'tat'

    def _gui(self):
        while not self.dung.wait(2):
            try:
                c = T.cai()
                if self._bat(c) and c['che_do'] == 'gui':
                    out = self.thu_muc(self.nap())
                    if (out / TEN).is_file():
                        gui_mot(out, c, T.token(), T._goi)
            except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
                continue

    def run(self):
        if self.gui_that:
            threading.Thread(target=self._gui, name='gui-cau-truc-telegram', daemon=True).start()
        while not self.dung.is_set():
            ma = ''
            mode = 'xem'
            try:
                cfg, c = self.nap(), T.cai()
                out = self.thu_muc(cfg)
                if not (out / TEN).is_file():
                    tao(out)
                mode = 'gui' if self.gui_that and c['che_do'] == 'gui' else 'xem'
                if not self._bat(c):
                    _loi(out, '', 'tat', 'Theo dõi đang tắt.')
                else:
                    dest = nhom_ma(c)
                    ma = ma_cho(cfg, datetime.now(timezone.utc), str(c.get('ma_bitcoin') or ''))
                    with closing(_db(out)) as db:
                        old = _st(db)
                    same = (old.get('ma'), old.get('mode'), old.get('dest')) == (ma, mode, dest)
                    ds = {k: z['cham'] for k, z in old.get('vung', {}).items() if same and z.get('cham') and not z.get('huy')}
                    snap = C.doc(cfg, ma, dang_theo_doi=ds)
                    tu = old.get('tick_ms', 0) if same and old.get('feed') == snap['feed'] else 0
                    tick = doc_tick(cfg, snap, tu) if snap['gia_moi'] and 0 < tu <= snap['tick_ms'] <= tu + GAP_MS else []
                    luu(out, snap, tick, mode, dest)
            except (OSError, ValueError, TypeError, KeyError, RuntimeError, sqlite3.Error):
                try:
                    _loi(self.thu_muc(self.nap()), ma, mode, 'Chưa xác minh được dữ liệu MT5.')
                except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
                    pass
            self.dung.wait(GIAY_QUET)
