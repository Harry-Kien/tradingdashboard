"""Kiểm chứng lịch sử cho nút "Phân tích": chạy lại từng luật trên kho nến 1 phút để biết những lần trước luật ra lệnh
thì kết thúc thế nào.

Không tự chế cách chấm. Mỗi luật dùng đúng bộ kiểm của chủ dự án:
  - luật bot:         tinhieu.rules.scan + tinhieu.backtest.simulate (đúng bộ theo dõi TP/SL của bot, trượt giá 0,25)
  - luật ba khung:    tools.ai_trend_history.decisions + tools.ai_trend_news.simulate (bản né tin, phí 0,35 USD/oz)
  - luật đỉnh/đáy:    ai.rule_fade.decide + ai.validator.validate + ai.scorer.score (bộ chấm của sổ chạy bóng)
Kho nến không có cột spread nên dùng một spread cố định (cau-hinh.json: gia.spread).

Chỉ đọc tệp giá. Không nối MT5, không đặt lệnh, không gọi API. Kết quả là kiểm trên giá quá khứ của một quãng ngắn mà
dự án đã nhìn thấy, không phải lời hứa lợi nhuận."""
from __future__ import annotations

import bisect
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from . import gia

HUONG = {'BUY': 'MUA', 'SELL': 'BAN', 'MUA': 'MUA', 'BAN': 'BAN'}
PHIEN_BAN = 2                                  # đổi cách tính thì tăng số này để bỏ kết quả đã lưu (2: sửa lệch giờ 25/11/2026)
_tt: dict = {'key': None, 'kq': None, 'dang': False, 'loi': None, 'bat_dau': None}
_khoa = threading.Lock()


def _m1(g: dict) -> pd.DataFrame:
    """Nến 1 phút của kho (chỉ số UTC), đúng các tệp mà gia.khung dùng."""
    files = [f for f, _, _ in gia._chu_ky(g) if os.path.basename(f).startswith('XAUUSDp_M1_')]
    if not files:
        raise FileNotFoundError('không thấy tệp nến 1 phút trong kho')
    m1 = pd.concat([pd.read_csv(f, parse_dates=['time']) for f in files[-int(g.get('so_thang', 4)):]])
    m1 = m1.drop_duplicates('time').set_index('time').sort_index()[['open', 'high', 'low', 'close']].astype(float)
    if m1.index.tz is None:
        m1.index = m1.index.tz_localize('UTC')
    return m1


def _iso(t) -> str:
    t = pd.Timestamp(t)
    return (t.tz_localize('UTC') if t.tzinfo is None else t.tz_convert('UTC')).isoformat()


def _vn(x: float) -> str:
    return f'{x:g}'.replace('.', ',')


def _lenh(t, ra, huong, vao, usd, ket, **them) -> dict:
    return {'t': _iso(t), 'ra': _iso(ra), 'huong': HUONG[huong], 'vao': round(float(vao), 2), 'usd': round(float(usd), 2), 'ket': ket, **them}


# ---- từng luật -------------------------------------------------------------------------------------------------------
def _bot(g: dict, m1: pd.DataFrame, d1: pd.DataFrame, sp: float, khung_bot) -> dict:
    from tinhieu import backtest as BT, rules as R                         # noqa: PLC0415
    mb = m1.assign(spread=sp)
    h1, h4 = BT.resample(mb, '1h'), BT.resample(mb, '4h')
    setups = []
    for tf in khung_bot:
        setups += R.scan(BT.resample(mb, R.TIMEFRAMES[tf]), h1, h4, d1, tf)
    lenh = [_lenh(t['entry_time'], t['exit_time'], t['side'], t['entry'], t['usd'], t['exit'], tp_dat=int(t['tps_hit']), n_tp=int(t['n_tps']),
                  rui_ro=round(float(t['risk']), 2), khung=t['tf']) for t in BT.simulate(setups, mb)]
    return {'lenh': lenh, 'cach': f'Chạy lại bằng tinhieu.backtest (khung {", ".join(khung_bot)}): vào ở giá mở nến 1 phút sau nến tín hiệu, '
                                  f'chia đều cho {R.TP_COUNT} TP, giữ tối đa {R.HOLD_MINUTES // 60} giờ, trượt giá {_vn(BT.SLIP)} mỗi lần khớp.'}


def _ba_khung(g: dict, m1: pd.DataFrame, fr: dict, sp: float, tin: list) -> dict:
    from ai import rule_trend as RT                                        # noqa: PLC0415
    from tools import ai_trend_history as TH, ai_trend_news as TN          # noqa: PLC0415

    def tran(df):                                                          # bộ kiểm của dự án dùng giờ UTC không múi
        out = df.reset_index(names='time')
        out['time'] = out['time'].dt.tz_localize(None)
        return out
    frames = {tf: tran(fr[tf]) for tf in ('D1', 'H4', 'H1', 'M15')}
    mn = tran(m1)
    decs = TH.decisions(frames, mn['time'].iloc[0], mn['time'].iloc[-1] + pd.Timedelta(minutes=1))
    cua = TN.Windows([pd.Timestamp(t).tz_convert('UTC').tz_localize(None) for t in tin])
    old = TH.SPREAD
    TH.SPREAD = sp                                                         # TN.simulate đọc spread từ đây
    try:
        trades = TN.simulate(decs, mn, cua, skip_news=bool(tin), news_costs=False)
    finally:
        TH.SPREAD = old
    lenh = [_lenh(t['t'], t['t_exit'], t['side'], t['entry'], t['usd'], 'TP' if t['usd'] > 0 else 'SL') for t in trades]
    hoa = (RT.SL_USD + TH.EXTRA) / (RT.TP_USD + RT.SL_USD) * 100
    return {'lenh': lenh, 'hoa_von': round(hoa, 1),
            'cach': f'Chạy lại bằng tools.ai_trend_history và ai_trend_news: mỗi lúc một lệnh, chốt {RT.TP_USD:g}, dừng {RT.SL_USD:g}, '
                    f'{"bỏ tín hiệu trong 15 phút quanh tin USD mạnh, " if tin else ""}phí thêm {_vn(TH.EXTRA)} mỗi lệnh.'}


def _dinh_day(g: dict, m1: pd.DataFrame, fr: dict, sp: float, tin: list) -> dict:
    from ai import config as C, rule_fade as RF, scorer as SC, snapshot as SN, validator as VA   # noqa: PLC0415, F401 - SN: nạp để chắc mã của EA đủ bộ
    from ai.schema import Market                                           # noqa: PLC0415
    from tinhieu import rules as R                                         # noqa: PLC0415
    m15 = fr['M15']
    atr30 = R.atr_sma(fr['M30'], 14).dropna()
    idx = m1.index
    mo = m1['open'].to_numpy()
    cot = m1.assign(spread=sp).reset_index(names='time')
    dai = C.MAX_HOLD_HOURS * 60 + 30
    lenh, ban, chan, khong_hop_le = [], None, {}, 0
    moc = sorted(pd.Timestamp(t).timestamp() for t in tin)
    rong = C.NEWS_BLACKOUT_MIN * 60

    def ne(t) -> bool:
        x = t.timestamp()
        k = bisect.bisect_left(moc, x - rong)
        return k < len(moc) and moc[k] <= x + rong
    for i in range(RF.LOOKBACK, len(m15)):
        t_dong = m15.index[i] + timedelta(minutes=15)
        if ban is not None and t_dong <= ban:
            continue
        j = int(idx.searchsorted(t_dong, side='left'))
        if j >= len(idx) or idx[j] - t_dong > timedelta(minutes=5):
            continue
        py = t_dong.to_pydatetime()
        if moc and ne(t_dong):
            continue
        k = int(atr30.index.searchsorted(t_dong - timedelta(minutes=30), side='right')) - 1
        if k < 0:
            continue
        atr, bid = float(atr30.iloc[k]), float(mo[j])
        sig = RF.decide(m15.iloc[max(0, i - RF.LOOKBACK - 4):i + 1], bid, bid + sp, atr, False, chan.get(py.date()))
        if sig.hanh_dong not in ('MUA', 'BAN'):
            continue
        v = VA.validate(sig, Market(bid, bid + sp, atr, float(m15['close'].iloc[i])))
        if v.trang_thai != 'hop_le':
            khong_hop_le += 1
            continue
        part = cot.iloc[j:j + dai]
        o = SC.score(v, py, part, part['time'].iloc[-1].to_pydatetime() + timedelta(days=1), tin)
        if o is None:
            break                                                          # lệnh còn chạy tới hết dữ liệu: dừng, không chấm
        if o.trang_thai != 'da_dong' or o.r is None:
            continue
        d = abs(o.gia_khop - v.sl)
        lenh.append(_lenh(o.t_khop, o.t_dong, v.huong, o.gia_khop, o.r * d, {'sl': 'SL', 'tp3': 'TP', 'hoa_von': 'Hòa vốn', 'het_gio': 'Hết giờ',
                                                                           'thu_sau': 'Thứ Sáu'}.get(o.ket_thuc, str(o.ket_thuc)),
                          r=round(float(o.r), 2), rui_ro=round(d, 2)))
        ban = pd.Timestamp(o.t_dong)
        if o.r <= 0:
            chan.setdefault(py.date(), set()).add(v.huong)
    return {'lenh': lenh, 'khong_hop_le': khong_hop_le,
            'cach': f'Chạy lại bằng ai.rule_fade và chấm bằng ai.scorer như sổ chạy bóng: mỗi lúc một lệnh, né tin, chốt ở 1,5R, '
                    f'giữ tối đa {C.MAX_HOLD_HOURS} giờ, hôm nào đã thua một chiều thì không vào lại chiều đó.'}


# ---- tóm tắt ---------------------------------------------------------------------------------------------------------
def tom(lenh: list[dict], huong: str | None = None) -> dict:
    """Số đo của một nhóm lệnh (cả hai chiều, hoặc một chiều). usd là lãi lỗ mỗi lệnh ở 0,01 lot (= số giá) sau chi phí."""
    ls = [x for x in lenh if huong is None or x['huong'] == huong]
    n = len(ls)
    if not n:
        return {'n': 0}
    usd = [x['usd'] for x in ls]
    lai, lo = sum(u for u in usd if u > 0), -sum(u for u in usd if u < 0)
    chuoi = dai = 0
    for u in usd:
        chuoi = chuoi + 1 if u <= 0 else 0
        dai = max(dai, chuoi)
    out = {'n': n, 'thang': sum(u > 0 for u in usd), 'ty_le': round(sum(u > 0 for u in usd) / n * 100, 1), 'usd_tb': round(sum(usd) / n, 2),
           'tong': round(sum(usd), 2), 'pf': round(lai / lo, 2) if lo > 0 else None, 'chuoi_thua': dai,
           'gan_day': [{k: x[k] for k in ('t', 'huong', 'vao', 'ket', 'usd')} for x in ls[-5:]][::-1]}
    if 'tp_dat' in ls[0]:
        out['tp1'] = round(sum(x['tp_dat'] >= 1 for x in ls) / n * 100, 1)
        out['tp2'] = round(sum(x['tp_dat'] >= 2 for x in ls) / n * 100, 1)
        out['sl_tron'] = round(sum(x['ket'] == 'SL' and x['tp_dat'] == 0 for x in ls) / n * 100, 1)
    return out


def chay(cfg: dict) -> dict:
    """Chạy lại cả ba luật trên kho nến. Nặng (vài chục giây): gọi qua lay() để chạy nền và nhớ kết quả."""
    g = cfg['gia']
    out: dict = {'phien_ban': PHIEN_BAN, 'tinh_luc': datetime.now(timezone.utc).isoformat(), 'luat': {}, 'loi': []}
    gia._nap_ma(g)
    fr, m1 = gia.khung(g), _m1(g)
    sp = float(g.get('spread', 0.17))
    dau, cuoi = float(m1['open'].iloc[0]), float(m1['close'].iloc[-1])
    out.update(tu=m1.index[0].isoformat(), den=fr['het'].isoformat(), so_ngay=int((fr['het'] - m1.index[0]).days), spread=sp,
               gia_dau=round(dau, 2), gia_cuoi=round(cuoi, 2), doi_pct=round((cuoi / dau - 1) * 100, 1))
    tin: list = []
    if g.get('lich_tin'):
        try:
            from ai import snapshot as SN                                  # noqa: PLC0415
            tin, _ = SN.load_high_usd_news(Path(os.path.expandvars(g['lich_tin'])))
        except Exception as e:                                             # noqa: BLE001
            out['loi'].append(f'Lịch tin: {type(e).__name__}: {e}')
    out['co_lich_tin'] = bool(tin)
    khung_bot = tuple((cfg.get('kiem_chung') or {}).get('khung_bot', ('M5', 'M15')))
    for ma, fn in (('bot', lambda: _bot(g, m1, fr['D1'], sp, khung_bot)), ('ba_khung', lambda: _ba_khung(g, m1, fr, sp, tin)),
                   ('dinh_day', lambda: _dinh_day(g, m1, fr, sp, tin))):
        try:
            r = fn()
            ls = sorted(r.pop('lenh'), key=lambda x: x['t'])               # theo giờ vào lệnh, cũ trước mới sau
            out['luat'][ma] = {**r, 'tat_ca': tom(ls), 'MUA': tom(ls, 'MUA'), 'BAN': tom(ls, 'BAN'),
                               'diem': [[int(pd.Timestamp(x['t']).timestamp()), 1 if x['huong'] == 'MUA' else -1, x['vao'], x['usd']] for x in ls]}
        except Exception as e:                                             # noqa: BLE001 - một luật hỏng không chặn luật khác
            out['loi'].append(f'{ma}: {type(e).__name__}: {e}')
    return out


# ---- nhớ kết quả và chạy nền -----------------------------------------------------------------------------------------
def _key(cfg: dict) -> str:
    g = cfg['gia']
    files = [os.path.basename(f) for f, _, _ in gia._chu_ky(g)]
    return json.dumps([PHIEN_BAN, files, gia.khung(g)['het'].date().isoformat(), g.get('spread', 0.17), g.get('so_thang', 4)])


def _tep(out: Path) -> Path:
    return Path(out) / 'kiem-chung.json'


def lay(cfg: dict, out: Path, cho: bool = False) -> dict:
    """Kết quả kiểm chứng nếu đã có (trong bộ nhớ hoặc tệp out/kiem-chung.json của đúng kho nến hôm nay); chưa có thì bắt
    đầu tính ở nền và trả {'san_sang': False}. cho=True: tính xong mới trả (dùng trong bài kiểm và dòng lệnh)."""
    if gia.ban_chia_se(cfg['gia']):
        return {'san_sang': False, 'dang_tinh': False, 'chia_se': True, 'loi': [],
                'ly_do': 'Kiểm chứng đo các luật riêng của chủ dự án trên kho nến nhiều năm; bản chia sẻ không có phần này.'}
    try:
        key = _key(cfg)
    except Exception as e:                                                 # noqa: BLE001
        return {'san_sang': False, 'dang_tinh': False, 'loi': [f'{type(e).__name__}: {e}']}
    with _khoa:
        if _tt['key'] == key and _tt['kq'] is not None:
            return {'san_sang': True, **_tt['kq']}
        if _tt['key'] != key:
            _tt.update(key=key, kq=None, loi=None)
            try:
                saved = json.loads(_tep(out).read_text(encoding='utf-8'))
                if saved.get('key') == key:
                    _tt['kq'] = saved['kq']
                    return {'san_sang': True, **_tt['kq']}
            except (OSError, ValueError, KeyError):
                pass
        if _tt['loi']:
            return {'san_sang': False, 'dang_tinh': False, 'loi': [_tt['loi']]}
        start = not _tt['dang']
        if start:
            _tt.update(dang=True, bat_dau=datetime.now(timezone.utc))

    def lam():
        try:
            kq = chay(cfg)
            with _khoa:
                if _tt['key'] == key:
                    _tt['kq'] = kq
            try:
                Path(out).mkdir(parents=True, exist_ok=True)
                _tep(out).write_text(json.dumps({'key': key, 'kq': kq}, ensure_ascii=False), encoding='utf-8')
            except OSError:
                pass
        except Exception as e:                                             # noqa: BLE001
            with _khoa:
                _tt['loi'] = f'{type(e).__name__}: {e}'
        finally:
            with _khoa:
                _tt['dang'] = False

    if cho:
        if start:
            lam()
        with _khoa:
            return {'san_sang': True, **_tt['kq']} if _tt['kq'] is not None else {'san_sang': False, 'dang_tinh': _tt['dang'], 'loi': [_tt['loi']] if _tt['loi'] else []}
    if start:
        threading.Thread(target=lam, name='kiem-chung', daemon=True).start()
    return {'san_sang': False, 'dang_tinh': True, 'da_giay': int((datetime.now(timezone.utc) - _tt['bat_dau']).total_seconds())}


def main(argv=None) -> int:
    import sys                                                             # noqa: PLC0415
    import time                                                            # noqa: PLC0415
    here = Path(__file__).resolve().parent.parent
    cfg = json.loads((here / 'cau-hinh.json').read_text(encoding='utf-8'))
    t0 = time.time()
    kq = chay(cfg)
    sys.stdout.reconfigure(encoding='utf-8')
    print(f'Kho nến {kq["tu"][:10]} tới {kq["den"][:10]} ({kq["so_ngay"]} ngày), spread {kq["spread"]}, tính trong {time.time() - t0:.0f} giây')
    for ma, r in kq['luat'].items():
        print(f'\n{ma}: {r["cach"]}')
        for ten in ('tat_ca', 'MUA', 'BAN'):
            print(f'  {ten}: ' + json.dumps({k: v for k, v in r[ten].items() if k != 'gan_day'}, ensure_ascii=False))
    for e in kq['loi']:
        print('LỖI:', e)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
