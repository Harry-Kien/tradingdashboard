"""Giá và chỉ báo cho trang biểu đồ. CHỈ ĐỌC tệp: không nối MT5, không ghi gì.

Nguồn giá là kho nến 1 phút mà hệ thống tự lưu (EA Promax\\reports\\ai-signals\\gia), ghép với tệp D1 dài hạn. Các khung
khác được gộp từ nến 1 phút, và chỉ giữ nến ĐÃ ĐÓNG. Chỉ báo và luật gọi thẳng các hàm thuần trong mã của chủ dự án
(tinhieu.rules, ai.rule_trend, ai.rule_fade, ai.snapshot); phần nào không nạp được thì báo lỗi riêng, biểu đồ vẫn lên."""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from . import doc_so, song

KHUNG ={'M5': 5, 'M15': 15, 'M30': 30, 'H1': 60, 'H4': 240, 'D1': 1440}
_QUY = {'M5': '5min', 'M15': '15min', 'M30': '30min', 'H1': '1h', 'H4': '4h'}
_OHLC = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}
_nho: dict = {}


def _p(path: str) -> str:
    return os.path.expandvars(path)


def _chu_ky(g: dict) -> tuple:
    files = sorted(glob.glob(os.path.join(_p(g['kho_m1']), 'XAUUSDp_M1_*.csv')))
    extra = [_p(g['d1_goc'])] if g.get('d1_goc') and os.path.exists(_p(g['d1_goc'])) else []
    return tuple((f, os.path.getmtime(f), os.path.getsize(f)) for f in files + extra)


def khung(g: dict) -> dict:
    """{'M5'..'D1': DataFrame open/high/low/close, chỉ số là giờ MỞ nến (UTC), chỉ nến đã đóng} + 'het' (thời điểm hết dữ liệu)."""
    key = _chu_ky(g)
    if _nho.get('key') == key:
        return _nho['fr']
    files = [f for f, _, _ in key if os.path.basename(f).startswith('XAUUSDp_M1_')]
    if not files:
        raise FileNotFoundError(f'không thấy tệp nến 1 phút trong {_p(g["kho_m1"])}')
    m1 = pd.concat([pd.read_csv(f, parse_dates=['time']) for f in files[-int(g.get('so_thang', 4)):]])
    m1 = m1.drop_duplicates('time').set_index('time').sort_index()[['open', 'high', 'low', 'close']]
    if m1.index.tz is None:
        m1.index = m1.index.tz_localize('UTC')
    het = m1.index[-1] + timedelta(minutes=1)                     # nến 1 phút cuối đóng lúc này
    fr = {}
    for tf, rule in _QUY.items():
        b = m1.resample(rule, origin='epoch', label='left', closed='left').agg(_OHLC).dropna()
        fr[tf] = b[b.index + timedelta(minutes=KHUNG[tf]) <= het]
    d1 = m1.resample('1D').agg(_OHLC).dropna()
    d1 = d1[(d1.index + timedelta(days=1) <= het) & (d1.index.day_of_week != 6)]
    if g.get('d1_goc') and os.path.exists(_p(g['d1_goc'])):       # lịch sử dài cho EMA200 D1
        raw = pd.read_csv(_p(g['d1_goc']), sep='\t')
        raw.columns = [c.strip('<>').lower() for c in raw.columns]
        t = pd.to_datetime(raw['date'] + ' ' + raw['time'] if 'time' in raw else raw['date'], format='mixed', utc=True)
        old = raw.assign(t=t).set_index('t')[['open', 'high', 'low', 'close']]
        d1 = pd.concat([old, d1[d1.index > old.index[-1]]])
    fr['D1'] = d1
    fr['het'] = het.to_pydatetime()
    fr['nguon'] = 'kho'
    _nho.update(key=key, fr=fr)
    return fr


class ChuaCoGia(RuntimeError):
    """Bản chia sẻ chưa nối được MT5 (và không có kho nến): không có giá để vẽ. Thông điệp là lý do đọc được cho người dùng."""


def can_gia(g: dict) -> None:
    """Bản chia sẻ không có kho nến: chưa nối được MT5 thì báo rõ lý do (máy mở nhiều MT5, MT5 chưa mở…) thay vì lỗi tìm tệp."""
    if ban_chia_se(g) and not g.get('kho_m1') and song.khung_song(g) is None:
        raise ChuaCoGia(song.ly_do() or 'chưa nối được MT5')


def ban_chia_se(g: dict) -> bool:
    """Máy không có mã EA Promax và bot tín hiệu của chủ dự án (bản chia sẻ cho người khác): không thư mục nào trong gia.ma_nguon tồn tại."""
    return not any(os.path.isdir(_p(p)) for p in g.get('ma_nguon', []))


def chia_se_song(g: dict) -> bool:
    """Bản chia sẻ VÀ đang có giá trực tiếp từ MT5: khi đó vàng đi chung đường với mọi mã khác (da_ma), dùng các phương pháp
    tùy chọn tính theo ATR thay cho luật riêng của chủ dự án. Không có MT5 thì giữ đường kho nến như cũ."""
    return ban_chia_se(g) and song.khung_song(g) is not None


def _nap_ma(g: dict):
    """Nạp mã của chủ dự án (hàm thuần). Trả về (tinhieu.rules, ai.rule_trend, ai.rule_fade, ai.snapshot).
    Bản chia sẻ không có mã đó: trả các chỉ báo chung trong chi_bao.py (cùng cách tính), không có luật vào lệnh."""
    for p in g.get('ma_nguon', []):
        if _p(p) not in sys.path:
            sys.path.insert(0, _p(p))
    try:
        from ai import rule_fade, rule_trend, snapshot       # noqa: PLC0415 - nạp muộn có chủ ý
        from tinhieu import rules                            # noqa: PLC0415
    except ImportError:
        if not ban_chia_se(g):                               # máy chủ dự án mà nạp hỏng: báo lỗi thật, không lặng lẽ đổi sang bản chung
            raise
        from . import chi_bao                                # noqa: PLC0415
        return chi_bao.R, chi_bao.RT, None, chi_bao.SN
    return rules, rule_trend, rule_fade, snapshot


_TIN: dict = {}
LICH_MANG = Path(__file__).resolve().parent.parent / 'du-lieu' / 'lich-tin-mang.json'   # lịch ForexFactory do lich_mang.py tải mỗi giờ
NGUON_TIN: dict = {}                                       # lần gọi gần nhất: tệp EA phủ tới đâu, lịch mạng bù bao nhiêu tin
_MANG: dict = {}
_CAO: dict = {}

# Tên tin trên ForexFactory → tên của CÙNG tin đó trong lịch MT5. Chỉ ghép cặp đúng một tin: PMI sơ bộ (Flash) không có trong lịch MT5 nên không ghép.
FF_MT5 = {'Non-Farm Employment Change': 'Nonfarm Payrolls', 'ADP Non-Farm Employment Change': 'ADP Nonfarm Employment Change',
          'Federal Funds Rate': 'Fed Interest Rate Decision', 'FOMC Press Conference': 'FOMC Press Conference',
          'Prelim GDP q/q': 'GDP q/q', 'Advance GDP q/q': 'GDP q/q', 'Final GDP q/q': 'GDP q/q',
          'ISM Services PMI': 'ISM Non-Manufacturing PMI', 'ISM Services Prices': 'ISM Non-Manufacturing Prices Paid',
          'ISM Manufacturing Prices': 'ISM Manufacturing Prices Paid', 'Unemployment Claims': 'Initial Jobless Claims',
          'CB Consumer Confidence': 'CB Consumer Confidence Index', 'Crude Oil Inventories': 'EIA Crude Oil Stocks Change',
          'Philly Fed Manufacturing Index': 'Philadelphia Fed Manufacturing Index', 'Chicago PMI': 'MNI Chicago Business Barometer',
          'Final Manufacturing PMI': 'S&P Global Manufacturing PMI', 'Final Services PMI': 'S&P Global Services PMI',
          '10-y Bond Auction': '10-Year Note Auction', '30-y Bond Auction': '30-Year Bond Auction'}
# Các tin MT5 xếp mức cao (importance 3) từ 25/11/2024 tới 25/11/2026, đọc từ tệp lịch của EA; dùng khi không đọc được tệp đó.
CAO_MT5_SAN = frozenset({
    '10-Year Note Auction',
    '30-Year Bond Auction',
    'ADP Nonfarm Employment Change',
    'Average Hourly Earnings m/m',
    'CB Consumer Confidence Index',
    'CPI',
    'CPI m/m',
    'CPI y/y',
    'Core CPI m/m',
    'Core CPI n.s.a. m/m',
    'Core PCE Price Index m/m',
    'Core PCE Price Index y/y',
    'Core Retail Sales m/m',
    'Durable Goods Orders m/m',
    'EIA Crude Oil Stocks Change',
    'Existing Home Sales',
    'FOMC Press Conference',
    'Fed Chair Powell Speech',
    'Fed Chair Powell Testimony',
    'Fed Interest Rate Decision',
    'GDP Sales q/q',
    'GDP q/q',
    'ISM Manufacturing PMI',
    'ISM Manufacturing Prices Paid',
    'ISM Non-Manufacturing PMI',
    'ISM Non-Manufacturing Prices Paid',
    'Initial Jobless Claims',
    'JOLTS Job Openings',
    'MNI Chicago Business Barometer',
    'New Home Sales',
    'Nonfarm Payrolls',
    'PPI m/m',
    'Philadelphia Fed Manufacturing Index',
    'Retail Sales m/m',
    'S&P Global Manufacturing PMI',
    'S&P Global Services PMI',
    'Unemployment Rate',
})


def ten_cao_mt5(path: str | None = None) -> frozenset:
    """Tên các tin USD mà MT5 xếp mức cao trong 2 năm cuối của tệp lịch EA (ít nhất 2 lần, và ít nhất một nửa số lần tin đó ra).

    MT5 xếp mức theo loại tin, gần như không đổi (2 năm tới 25/11/2026: 37 loại, loại nào cũng 100% số lần), nên học từ lịch sử của chính tệp
    là cách giữ cho lịch mạng né đúng những tin EA Promax né. Không đọc được tệp thì dùng danh sách CAO_MT5_SAN."""
    try:
        p = _p(path)
        key = (p, os.path.getmtime(p), os.path.getsize(p))
    except (OSError, TypeError):
        return CAO_MT5_SAN
    if _CAO.get('key') != key:
        import csv                                         # noqa: PLC0415
        rows = []
        try:
            with open(p, encoding='utf-8-sig', newline='') as f:
                for r in csv.DictReader(f):
                    if (r.get('currency') or '').strip().upper() == 'USD':
                        rows.append(((r.get('time') or '').strip(), (r.get('event') or '').strip(), (r.get('importance') or '').strip()))
        except (OSError, UnicodeDecodeError, csv.Error):
            rows = []
        ten = frozenset()
        if rows:
            cuoi = max(t for t, _, _ in rows)                  # giờ dạng 2026.11.25 13:30: so chuỗi là so thời gian
            moc = f'{int(cuoi[:4]) - 2}{cuoi[4:]}' if cuoi[:4].isdigit() else ''
            dem, cao = {}, {}
            for t, e, i in rows:
                if t >= moc and e:
                    dem[e] = dem.get(e, 0) + 1
                    cao[e] = cao.get(e, 0) + (i in ('3', '3.0'))
            ten = frozenset(e for e in dem if cao[e] >= 2 and 2 * cao[e] >= dem[e])
        _CAO.update(key=key, ten=ten or CAO_MT5_SAN)
    return _CAO['ten']


def la_tin_cao(ten: str, muc, cao: frozenset) -> bool:
    """Một tin USD trên lịch mạng có phải tin cần né không: ForexFactory xếp High, HOẶC đó là loại tin MT5 xếp mức cao."""
    try:
        if int(muc or 0) >= 3:
            return True
    except (TypeError, ValueError):
        pass
    if FF_MT5.get(ten, ten) in cao:
        return True
    m = re.fullmatch(r'Fed Chair \S+ (Speaks|Testifies)', ten or '')     # chủ tịch Fed đổi người thì tên tin đổi theo
    duoi = {'Speaks': ' Speech', 'Testifies': ' Testimony'}[m.group(1)] if m else ''
    return bool(m) and any(x.startswith('Fed Chair ') and x.endswith(duoi) for x in cao)


def tin_mang_usd(sau: datetime | None, p: Path | None = None, cao: frozenset | None = None) -> tuple[list[tuple[datetime, str]], datetime | None]:
    """Tin USD cần né trong lịch mạng, giờ SAU mốc `sau`; kèm mốc muộn nhất của lịch mạng.

    Dùng để vá chỗ hổng khi tệp lịch của EA hết hạn: lịch mạng tự tải mỗi giờ nên không cần ai xuất tay. ForexFactory chỉ xếp High cho ít tin hơn
    MT5 (tuần 23/11/2026: 2 so với 9), nên tin được tính là cần né khi ForexFactory xếp High HOẶC MT5 xếp loại tin đó mức cao (`cao`, mặc định là
    danh sách học lần gần nhất từ tệp EA). Tuần 23/11/2026, cách này cho đúng các mốc giờ MT5 né: 24/11 15:00, 25/11 13:30, 15:00 và 15:30 UTC."""
    p = p or LICH_MANG
    cao = cao if cao is not None else (_CAO.get('ten') or CAO_MT5_SAN)
    try:
        st = p.stat()
        key = (str(p), st.st_mtime_ns, st.st_size, cao)
    except OSError:
        return [], None
    if _MANG.get('key') != key:
        try:
            ds = json.loads(p.read_text(encoding='utf-8')).get('ds') or []
        except (OSError, ValueError, AttributeError):
            ds = []
        tin, het = [], None
        for x in ds:
            try:
                t = datetime.fromisoformat(x['t']).astimezone(timezone.utc)
            except (KeyError, TypeError, ValueError):
                continue
            het = t if het is None or t > het else het
            if x.get('tien') == 'USD' and la_tin_cao(str(x.get('ten') or ''), x.get('muc'), cao):
                tin.append((t, str(x.get('ten') or '')))
        _MANG.update(key=key, tin=sorted(tin), het=het)
    return [(t, ten) for t, ten in _MANG['tin'] if sau is None or t > sau], _MANG['het']


def tin_usd(g: dict) -> tuple[list, object]:
    """(các mốc tin USD mức cao, mốc sự kiện muộn nhất trong tệp), đúng như ai.snapshot.load_high_usd_news trả. Tệp lịch có hàng chục nghìn
    dòng mà nút Phân tích, biểu đồ và phần tự kiểm đều cần nó, nên kết quả được nhớ lại và chỉ đọc lại khi tệp đổi (giờ sửa hoặc cỡ tệp)."""
    p = Path(_p(g['lich_tin']))
    try:
        st = p.stat()
        key = (str(p), st.st_mtime_ns, st.st_size)
    except OSError:
        key = (str(p), None, None)
    if _TIN.get('key') != key:
        kq = _nap_ma(g)[3].load_high_usd_news(p)
        _TIN.update(key=key, kq=(list(kq[0]), kq[1]))
    news, covered = _TIN['kq']
    bu, het_mang = tin_mang_usd(covered, cao=ten_cao_mt5(g.get('lich_tin')))   # tệp EA hết hạn (hoặc thiếu): lịch mạng bù phần sau đó
    NGUON_TIN.update(ea_phu=covered, mang_phu=het_mang, so_bu=len(bu))
    if het_mang is not None and (covered is None or het_mang > covered):
        return sorted(list(news) + [t for t, _ in bu]), het_mang
    return list(news), covered


def _so(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if x != x else round(x, 2)


def _day(s: pd.Series) -> list:
    return [_so(v) for v in s.tolist()]


def _giay(t) -> int:
    return int(pd.Timestamp(t).timestamp())


def luat(fr: dict, g: dict, now: datetime) -> dict:
    """Các luật của chủ dự án đang nói gì trên nến đã đóng gần nhất. Mỗi mục tự bắt lỗi của mình."""
    het = fr['het']
    out: dict = {'het': het.isoformat(), 'tuoi_phut': max(0, int((now - het).total_seconds() // 60)), 'loi': []}
    try:
        R, RT, RF, SN = _nap_ma(g)
    except Exception as e:                                                    # noqa: BLE001
        out['loi'].append(f'Không nạp được mã chỉ báo của dự án: {type(e).__name__}: {e}')
        return out
    if RF is None:                                                            # bản chia sẻ: chỉ có chỉ báo chung, không có luật riêng
        out['chia_se'] = True
        out['loi'].append('Không nạp được mã chỉ báo của dự án: máy này không có các luật riêng của chủ dự án (bản chia sẻ).')
        return out
    m15, h1, h4, d1 = fr['M15'], fr['H1'].iloc[-300:], fr['H4'].iloc[-300:], fr['D1'].iloc[-900:]

    def thu(ten, fn):
        try:
            return fn()
        except Exception as e:                                                # noqa: BLE001
            out['loi'].append(f'{ten}: {type(e).__name__}: {e}')
            return None

    snap = thu('Ảnh chụp thị trường của bot', lambda: R.snapshot(m15.iloc[-320:], h1, h4, d1, 'M15'))
    if snap:
        out['bot'] = {k: (int(v) if k in ('H1', 'H4', 'D1', 'trend') else _so(v)) for k, v in snap.items()}
    setups = []
    for tf in ('M5', 'M15'):
        found = thu(f'Luật của bot trên {tf}', lambda tf=tf: R.candidates(fr[tf].iloc[-320:], h1, h4, d1, tf)) or []
        setups += [{'tf': tf, 'side': s.side, 'kind': s.kind, 'reason': s.reason, 'sl': _so(s.sl_price), 'level': _so(s.level),
                    'bar': pd.Timestamp(s.bar_time).isoformat()} for s in found]
    out['bot_tin_hieu'] = setups

    def cho():
        """Đỉnh và đáy của quãng mà nến KẾ TIẾP phải đóng vượt qua thì kiểu vào DON của bot mới có điều kiện (đúng cách tính trong scan)."""
        if 'DON' not in getattr(R, 'KINDS', ()):
            return []
        res = []
        for tf in ('M5', 'M15'):
            b = fr[tf]
            gio = int(R.don_hours(tf, int((b.index[-1] + pd.Timedelta(R.TIMEFRAMES[tf])).hour)))
            n_ = R.sr_bars(tf, gio)
            if len(b) >= n_:
                res.append({'tf': tf, 'gio': gio, 'dinh': _so(b['high'].iloc[-n_:].max()), 'day': _so(b['low'].iloc[-n_:].min())})
        return res
    out['bot_cho'] = thu('Mức bot đang chờ', cho) or []
    dirs = thu('Xu hướng ba khung', lambda: RT.directions(fr['D1']['close'], fr['H4']['close'], fr['H1']['close']))
    if dirs:
        last = m15.iloc[-1]
        close_t = (m15.index[-1] + timedelta(minutes=15)).to_pydatetime()
        out['ba_khung'] = {'huong': {k: int(v) for k, v in dirs.items()}, 'nen': m15.index[-1].isoformat(),
                           'quyet_dinh': thu('Luật ba khung', lambda: RT.decide(fr['D1']['close'], fr['H4']['close'], fr['H1']['close'],
                                                                                 float(last['open']), float(last['close']))),
                           'trong_gio': bool(thu('Khung giờ của luật ba khung', lambda: RT.in_window(close_t)))}

    def dinh_day():
        atr = float(R.atr_sma(fr['M30'], 14).iloc[-1])
        bid = float(fr.get('bid') or m15['close'].iloc[-1])
        s = RF.decide(m15.iloc[-200:], bid, float(fr.get('ask') or bid + float(g.get('spread', 0.17))), atr, False, None)
        d = s.model_dump() if hasattr(s, 'model_dump') else dict(vars(s))
        return {k: (_so(v) if isinstance(v, float) else v) for k, v in d.items()
                if k in ('hanh_dong', 'kieu_vao', 'gia_vao', 'sl', 'tp1', 'tp2', 'tp3', 'ly_do')}
    fade = thu('Luật đỉnh/đáy', dinh_day)
    if fade:
        out['dinh_day'] = {**fade, 'nen': m15.index[-1].isoformat()}

    def tin():
        news, covered = tin_usd(g)
        return {'sap_toi': [t.isoformat() for t in news if t > het][:4], 'phu_toi': covered.isoformat() if covered else None,
                'dang_ne': bool(SN.in_news_blackout(het, news)), 'tat_ca': news}
    news = thu('Lịch tin USD', tin) if g.get('lich_tin') else None
    if news:
        out['_tin'] = news.pop('tat_ca')
        out['tin'] = news
    return out


_lenh_nho: dict = {'luc': 0.0, 'key': None, 'ds': []}


def _con(t: datetime, now: datetime) -> str:
    m = max(0, int((t - now).total_seconds() // 60))
    return f'còn {m} phút' if m < 90 else f'còn {m // 60} giờ' if m < 48 * 60 else f'còn {m // 1440} ngày'


def tin_sap_toi(cfg: dict, now: datetime | None = None, n: int = 5) -> list[dict]:
    """Các tin USD mức cao sắp tới trong lịch (giờ trong tệp là UTC): [{'luc': ISO, 'ten': tên sự kiện}], gần trước xa sau."""
    path = (cfg.get('gia') or {}).get('lich_tin')
    now = now or datetime.now(timezone.utc)
    if not path or not os.path.exists(_p(path)):                 # không có tệp của EA: chỉ còn lịch mạng
        return [{'luc': t.isoformat(), 'ten': ten, 'con': _con(t, now)} for t, ten in tin_mang_usd(now, cao=ten_cao_mt5(path))[0]][:n] if path else []
    key = ('tin', _p(path), os.path.getmtime(_p(path)))
    if _nho_tin.get('key') != key:
        import csv                                         # noqa: PLC0415
        rows = []
        with open(_p(path), encoding='utf-8-sig', newline='') as f:
            for r in csv.DictReader(f):
                try:
                    if (r.get('currency') or '').strip().upper() != 'USD' or int(float(r.get('importance') or 0)) < 3:
                        continue
                    t = datetime.strptime(r['time'].strip(), '%Y.%m.%d %H:%M').replace(tzinfo=timezone.utc)
                except (ValueError, KeyError, AttributeError):
                    continue
                rows.append((t, (r.get('event') or '').strip()))
        rows.sort()
        _nho_tin.update(key=key, rows=rows)
    def con(t):
        return _con(t, now)
    rows = _nho_tin['rows']
    if rows:                                               # sau chỗ tệp EA còn phủ: lấy thêm từ lịch mạng
        rows = rows + tin_mang_usd(rows[-1][0], cao=ten_cao_mt5(path))[0]
    return [{'luc': t.isoformat(), 'ten': ten, 'con': con(t)} for t, ten in rows if t > now][:n]


_nho_tin: dict = {}


def lenh_dang_mo(cfg: dict) -> list[dict]:
    """Lệnh đang mở để vẽ lên biểu đồ: lệnh gọi còn mở của bot tín hiệu và vị thế còn mở của từng EA demo. Chỉ đọc sổ."""
    key = (cfg.get('bot_db'), json.dumps(cfg.get('tai_khoan', []), sort_keys=True))
    now = time.monotonic()
    if _lenh_nho['key'] == key and now - _lenh_nho['luc'] < 15:
        return _lenh_nho['ds']
    ds = []
    try:
        for r in doc_so.doc_bot(cfg['bot_db']) if cfg.get('bot_db') else []:
            if not r['closed']:
                ds.append({'nhan': f'Bot {r["call"]} {"MUA" if r["side"] == "BUY" else "BÁN"}', 'ten': f'Bot {r["call"]}', 'huong': r['side'], 'vao': _so(r['entry']),
                           'sl': _so(r['sl']), 'tp': [_so(x) for x in r['tps'][r['tps_hit']:]], 'loai': 'tin_hieu'})
    except Exception:                                                         # noqa: BLE001 - thiếu sổ bot thì bỏ qua phần này
        pass
    for acc in cfg.get('tai_khoan', []):
        for e in acc.get('ea', []):
            try:
                o = doc_so.doc_ea(e['tep'], e.get('lech_gio_utc', 0))['open']
            except Exception:                                                 # noqa: BLE001
                continue
            if o:
                # 'ten' và 'lot' riêng để trang ghép nhãn với chữ Mua/Bán của chính nó: bản tiếng Anh dịch được mà không cần khóa riêng cho từng tên EA
                ds.append({'nhan': f'{e["ten"]} {"MUA" if o["side"] == "BUY" else "BÁN"} {o["lots"]:g}', 'ten': e['ten'], 'lot': o['lots'],
                           'huong': o['side'], 'vao': _so(o['entry']),
                           'sl': _so(o['sl']) if o['sl'] else None, 'tp': [_so(o['tp'])] if o['tp'] else [], 'loai': 'demo'})
    _lenh_nho.update(luc=now, key=key, ds=ds)
    return ds


def rsi_wilder(close: pd.Series, n: int = 14) -> pd.Series:
    """RSI kiểu Wilder (làm trơn hệ số 1/n), cùng cách tính với RSI của MT5."""
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn)


def goi(cfg: dict, tf: str = 'M15', n: int = 600, now: datetime | None = None) -> dict:
    """Dữ liệu cho biểu đồ một khung: nến đã đóng, chỉ báo, vùng giá, giờ tin, và phần luật."""
    if tf not in KHUNG:
        raise ValueError(f'khung không hỗ trợ: {tf}')
    g = cfg['gia']
    can_gia(g)
    if chia_se_song(g):                           # bản chia sẻ: vàng dùng chung đường với mọi mã (không có luật riêng của chủ dự án)
        from . import da_ma                       # noqa: PLC0415 - da_ma nạp gia, tránh vòng nạp
        return da_ma.goi(cfg, da_ma.ma_vang(cfg), tf, n, now)
    now = now or datetime.now(timezone.utc)
    fr = song.khung_song(g) or khung(g)           # giá trực tiếp từ MT5 nếu bật và nối được, không thì kho nến 1 phút
    bars = fr[tf]
    n = max(50, min(int(n), 1500))
    close = bars['close']
    mid, sd = close.rolling(20).mean(), close.rolling(20).std(ddof=0)
    over = {'ema20': close.ewm(span=20, adjust=False, min_periods=20).mean(), 'ema50': close.ewm(span=50, adjust=False, min_periods=50).mean(),
            'bb_tren': mid + 2 * sd, 'bb_duoi': mid - 2 * sd, 'rsi': rsi_wilder(close)}
    view = bars.iloc[-n:]
    out = {'tf': tf, 'candles': [[_giay(t), _so(o), _so(h), _so(l), _so(c)] for t, o, h, l, c in
                                 zip(view.index, view['open'], view['high'], view['low'], view['close'])],
           **{k: _day(v.iloc[-n:]) for k, v in over.items()}, 'vung': [], 'tin': [],
           'nguon': fr['nguon'], 'bid': _so(fr.get('bid')), 'ask': _so(fr.get('ask')),
           'ly_do_khong_song': song.ly_do() if fr['nguon'] != 'mt5' else None, 'lenh': lenh_dang_mo(cfg)}
    dc = (fr.get('dang_chay') or {}).get(tf)
    if dc and out['candles'] and dc[0] > out['candles'][-1][0]:      # cây nến đang chạy: chỉ để vẽ
        out['dang_chay'] = [dc[0]] + [_so(v) for v in dc[1:]]
    rules = luat(fr, g, now)
    news = rules.pop('_tin', [])
    try:
        R, _, _, SN = _nap_ma(g)
        if tf in ('M5', 'M15', 'M30'):                          # hỗ trợ / kháng cự 2 giờ như bot dùng
            sup, res = R.levels_sr(bars, tf, 2)
            out['ho_tro'], out['khang_cu'] = _day(sup.iloc[-n:]), _day(res.iloc[-n:])
        if tf != 'D1':
            atr_h1 = float(R.atr_sma(fr['H1'], 14).iloc[-1])
            src = bars.iloc[-300:].reset_index(names='time')
            for loai, rows in (('fvg', SN.fvg_zones(src, 0.1 * atr_h1, 8)), ('ob', SN.order_blocks(src, 1.0 * atr_h1, 8))):
                out['vung'] += [{'loai': loai, 'huong': z['huong'], 't': _giay(pd.Timestamp(z['thoi_diem_utc'], tz='UTC')),
                                 'duoi': _so(z['duoi']), 'tren': _so(z['tren'])} for z in rows]
    except Exception as e:                                                    # noqa: BLE001
        rules['loi'].append(f'Vùng giá và hỗ trợ/kháng cự: {type(e).__name__}: {e}')
    if len(view):
        a, b = view.index[0].to_pydatetime(), fr['het'] + timedelta(days=3)
        out['tin'] = [_giay(t) for t in news if a <= t <= b]
    out['luat'] = rules
    return out
