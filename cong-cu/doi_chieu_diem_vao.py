# -*- coding: utf-8 -*-
"""Đối chiếu phần CHỌN NẾN VÀO LỆNH của luật bot và luật đỉnh/đáy với một bản dựng lại độc lập.

Bốn phép đối chiếu với Backtesting.py chỉ kiểm phần thoát lệnh của hai luật này: danh sách lệnh lấy nguyên từ mã của dự án. Công cụ này kiểm
nửa còn lại: luật có chọn đúng nến, đúng chiều, đúng giá vào, dừng lỗ và chốt lời như lời mô tả của nó không.

Bản dựng lại viết từ lời mô tả luật, cố ý tính theo cách khác mã của dự án:
- nến các khung tự ghép từ nến 1 phút bằng numpy (không dùng resample của pandas);
- EMA, ATR tính bằng vòng lặp và cửa sổ cắt tường minh (không dùng ewm, rolling, shift, merge_asof);
- mỗi nến tín hiệu chỉ nhìn các nến có chỉ số nhỏ hơn hoặc bằng nó, và nến khung lớn nào đã đóng trước lúc quyết định. Viết như vậy thì nhìn
  trước tương lai là không thể xảy ra, nên nếu mã của dự án có nhìn trước thì hai bên sẽ lệch nhau.
Tham số (số nến, ngưỡng, bội số ATR…) đọc từ mã của dự án: phép này kiểm cách tính, không kiểm việc chọn tham số.

Trạng thái "đang có lệnh nào mở, hôm nay đã thua chiều nào" phụ thuộc lúc lệnh trước đóng. Phần đó lấy từ bộ chấm của dự án (đã đối chiếu
riêng với Backtesting.py), rồi bản dựng lại tự quyết ở từng nến: có vào không, vào ở đâu. Lệch ở nến nào thì đếm ở nến đó, sau đó đi tiếp
theo trạng thái của dự án để một chỗ lệch không kéo theo các chỗ sau.

Luật bot được so ba tầng:
1. nến tín hiệu và các mức dừng lỗ ứng viên (tinhieu.rules.scan);
2. lệnh được vào, theo đúng thứ tự xử lý của bộ kiểm trong dự án (tinhieu.backtest.simulate + tinhieu.levels.build);
3. lệnh được vào nếu xử lý theo đúng thứ tự thời gian. Bộ kiểm của dự án xếp tín hiệu theo giờ MỞ nến, nên một nến M15 (đóng lúc 10:15) được
   xét trước một nến M5 mở sau nó nhưng đóng sớm hơn (10:10). Tầng này đếm số quyết định sẽ khác đi; đó là đặc điểm của bộ kiểm, không phải
   chỗ lệch của bản dựng lại.
Luật đỉnh/đáy được so từng tín hiệu hợp lệ (ai.rule_fade.decide + ai.validator.validate + vòng chọn trong so_cong_khai.kiem_chung._dinh_day).

Chạy với đúng cấu hình webapp dùng (spread trong cau-hinh.json, lịch tin USD). Công cụ không sửa gì trong dự án của chủ dự án: chỉ bọc tạm vài
hàm trong bộ nhớ để ghi lại kết quả, rồi trả lại ngay. Chỉ đọc tệp nến; không nối MT5. Thoát với mã 1 nếu có chỗ lệch chưa giải thích được.

    python -X utf8 cong-cu/doi_chieu_diem_vao.py [năm bắt đầu, mặc định 2015]
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import gia, hoc, kiem_chung  # noqa: E402

SAT = 1e-7          # hai vế của một phép so sánh cách nhau dưới mức này thì coi là "đúng ngưỡng": sai số làm tròn có thể lật kết quả
NGAY = 86400


# ---- khối dựng chung, viết độc lập -----------------------------------------------------------------------------------------------------------
def giay(idx) -> np.ndarray:
    """Giờ mở nến tính bằng giây từ 1/1/1970 UTC."""
    return idx.tz_convert('UTC').tz_localize(None).values.astype('datetime64[s]').astype(np.int64)


def ghep(T, O, H, L, C, dai: int):
    """Ghép nến 1 phút thành nến dài `dai` giây: nến chứa mọi phút có cùng phần nguyên của T / dai."""
    khoa = T // dai
    dau = np.flatnonzero(np.r_[True, khoa[1:] != khoa[:-1]])
    cuoi = np.r_[dau[1:] - 1, len(T) - 1]
    return khoa[dau] * dai, O[dau], np.maximum.reduceat(H, dau), np.minimum.reduceat(L, dau), C[cuoi]


def atr_tb(H, L, C, n: int) -> np.ndarray:
    """Trung bình cộng của n biên độ thật gần nhất; nến đầu tiên lấy cao trừ thấp. Chưa đủ n nến thì NaN."""
    tr = H - L
    if len(H) > 1:
        tr = np.r_[tr[0], np.maximum(tr[1:], np.maximum(np.abs(H[1:] - C[:-1]), np.abs(L[1:] - C[:-1])))]
    out = np.full(len(H), np.nan)
    if len(H) >= n:
        out[n - 1:] = np.lib.stride_tricks.sliding_window_view(tr, n).mean(axis=1)
    return out


def ema(x, n: int) -> np.ndarray:
    """EMA đệ quy bắt đầu từ giá trị đầu tiên, hệ số 2 / (n + 1); n − 1 nến đầu để NaN."""
    a, e, out = 2.0 / (n + 1), float(x[0]), np.full(len(x), np.nan)
    for k in range(len(x)):
        if k:
            e += a * (float(x[k]) - e)
        if k >= n - 1:
            out[k] = e
    return out


def da_dong(dong_lon, gia_tri, luc) -> np.ndarray:
    """Giá trị của nến khung lớn ĐÃ ĐÓNG gần nhất tại mỗi thời điểm `luc` (đóng đúng lúc đó cũng tính); chưa có thì NaN."""
    k = np.searchsorted(dong_lon, luc, side='right') - 1
    return np.where(k >= 0, gia_tri[np.maximum(k, 0)], np.nan)


def nen_ngay(T, O, H, L, C, tep: str):
    """Nến ngày như webapp dùng: ghép từ nến 1 phút (bỏ Chủ nhật và ngày chưa trọn), phía trước nối bằng tệp nến ngày nhiều năm."""
    t, o, h, l, c = ghep(T, O, H, L, C, NGAY)
    giu = (t + NGAY <= T[-1] + 60) & ((t // NGAY + 3) % 7 != 6)            # 1/1/1970 là thứ Năm
    t, o, h, l, c = (x[giu] for x in (t, o, h, l, c))
    if tep and os.path.exists(tep):
        raw = pd.read_csv(tep, sep='\t')
        raw.columns = [x.strip('<>').lower() for x in raw.columns]
        tt = giay(pd.DatetimeIndex(pd.to_datetime(raw['date'] + ' ' + raw['time'] if 'time' in raw else raw['date'], format='mixed', utc=True)))
        cu = tt < t[0]
        t, o, h, l, c = (np.r_[raw[k].to_numpy(dtype=float)[cu] if k else tt[cu], x] for k, x in ((None, t), ('open', o), ('high', h), ('low', l), ('close', c)))
    return t.astype(np.int64), o, h, l, c


# ---- luật bot, dựng lại ----------------------------------------------------------------------------------------------------------------------
def bot_tin_hieu(tf: str, M, lon: dict, R) -> tuple[dict, set]:
    """{giờ mở nến tín hiệu: (mua?, [mức dừng lỗ ứng viên theo đỉnh/đáy], khoảng dừng lỗ dự phòng hoặc None, sát ngưỡng?)} và tập nến suýt được."""
    dai = int(pd.Timedelta(R.TIMEFRAMES[tf]).total_seconds())
    t, o, h, l, c = ghep(*M, dai)
    luc = t + dai                                                           # lúc nến tín hiệu đóng = lúc quyết định
    so_nen = lambda gio: gio * 3600 // dai
    atr = atr_tb(h, l, c, R.ATR_PERIOD)
    ba = [da_dong(lon[k][0], lon[k][1], luc) for k in ('H1', 'H4', 'D1')]
    # lọc xu hướng: từ đêm 24/11/2026 bot có hai công tắc (rules.TREND_D1, rules.SELL_NEEDS_D1): MUA cần H1 và H4 tăng (thêm D1 nếu TREND_D1),
    # BÁN cần H1 và H4 giảm (thêm D1 nếu TREND_D1 hoặc SELL_NEEDS_D1). Bản bot cũ không có hai công tắc này: coi như cả hai chiều cần D1.
    can_d1_mua = bool(getattr(R, 'TREND_D1', True))
    can_d1_ban = can_d1_mua or bool(getattr(R, 'SELL_NEEDS_D1', True))
    tang = (ba[0] > 0) & (ba[1] > 0) & ((ba[2] > 0) if can_d1_mua else True)
    giam = (ba[0] < 0) & (ba[1] < 0) & ((ba[2] < 0) if can_d1_ban else True)
    xh = np.where(tang, 1, np.where(giam, -1, 0))
    sat_xh = (np.abs(ba[0]) < SAT) | (np.abs(ba[1]) < SAT) | ((np.abs(ba[2]) < SAT) if (can_d1_mua or can_d1_ban) else False)
    atr_ng = da_dong(lon['D1'][0], lon['ATR_D1'], luc)
    lo, hi = R.SL_MIN - R.SL_SLACK, R.SL_MAX + R.SL_SLACK
    n_ngay = so_nen(24)
    ra, suyt = {}, set()
    for i in np.flatnonzero((xh != 0) | sat_xh):
        ti = int(t[i])
        sat = bool(sat_xh[i])
        if xh[i] == 0:
            suyt.add(ti)
            continue
        gio = ti % NGAY // 3600
        if not (R.SESSION_UTC[0] <= gio < R.SESSION_UTC[1]) or i < R.ATR_PERIOD - 1:
            continue
        mua = xh[i] > 0
        tich_cuc = R.DON_ACTIVE_UTC[0] <= gio < R.DON_ACTIVE_UTC[1]
        n = so_nen(R.DON_HOURS[tf] if tich_cuc else max(R.DON_HOURS[tf], R.DON_QUIET_HOURS))
        if i - n < 0:
            continue
        moc = h[i - n:i].max() if mua else l[i - n:i].min()                # đỉnh/đáy của n nến TRƯỚC nến tín hiệu
        pha = c[i] > moc if mua else c[i] < moc
        gan = abs(c[i] - moc) < SAT
        if not pha:
            if gan:
                suyt.add(ti)
            continue
        sat |= gan
        if R.EXT_MAX:                                                       # độ dãn so với đáy/đỉnh 24 giờ, chia ATR ngày đã đóng
            ad = atr_ng[i]
            if i - n_ngay + 1 < 0 or not np.isfinite(ad) or ad == 0:
                continue
            chay = (c[i] - l[i - n_ngay + 1:i + 1].min()) / ad if mua else (h[i - n_ngay + 1:i + 1].max() - c[i]) / ad
            gan = min(abs(chay - R.EXT_MIN), abs(chay - R.EXT_MAX)) < SAT
            if not (R.EXT_MIN < chay <= R.EXT_MAX):
                if gan:
                    suyt.add(ti)
                continue
            sat |= gan
        if R.BODY_MIN:                                                      # thân nến so với ATR của khung, tính tới nến trước
            if i - 1 < R.ATR_PERIOD - 1:
                continue
            than, a1 = abs(c[i] - o[i]), atr[i - 1]
            ty = than / a1 if a1 > 0 else (math.inf if than > 0 else math.nan)
            gan = abs(ty - R.BODY_MIN) < SAT
            if not ty >= R.BODY_MIN:
                if gan:
                    suyt.add(ti)
                continue
            sat |= gan
        ds, da_co, gan_nhat = [], set(), None
        for w in R.SR_WINDOWS:                                              # vùng hỗ trợ/kháng cự: w giờ gần nhất, tính cả nến tín hiệu
            nw = so_nen(w)
            if i - nw + 1 < 0:
                continue
            muc = l[i - nw + 1:i + 1].min() if mua else h[i - nw + 1:i + 1].max()
            sl = float(math.floor(muc - R.SL_PAD) if mua else math.ceil(muc + R.SL_PAD))
            kc = float(c[i] - sl if mua else sl - c[i])
            gan_nhat = kc if gan_nhat is None else gan_nhat
            if sl in da_co or not (lo <= kc <= hi):
                continue
            da_co.add(sl)
            ds.append(sl)
        du_phong = float(min(R.SL_MAX, max(R.SL_MIN, gan_nhat if gan_nhat is not None else R.SL_MIN))) if R.SL_FALLBACK else None
        ra[ti] = (bool(mua), ds, du_phong, sat)
    return ra, suyt


def bot_dung(mua: bool, ds: list, du_phong, gia_mo: float, sp: float, R, LV, tran_spread: float):
    """(giá vào, dừng lỗ, các mức chốt) của ứng viên đầu tiên dùng được, hoặc None. Mua khớp ở Ask = Bid + spread, bán khớp ở Bid."""
    dau = 1 if mua else -1
    vao = round(gia_mo + sp if mua else gia_mo, 2)
    for kieu, x in [('muc', s) for s in ds] + ([('kc', du_phong)] if du_phong is not None else []):
        if kieu == 'muc':
            sl = round(x, 2)
            if not (R.SL_MIN - 1e-9 <= dau * (vao - sl) <= R.SL_MAX + 1e-9):
                continue
        else:
            sl = float(math.floor(vao - x) if mua else math.ceil(vao + x))
        rr = abs(vao - sl)
        if sp > tran_spread * rr:
            continue
        goc, buoc, tps = math.floor(vao + 0.5), 0, []
        if LV.TP_R and rr > 0:                                              # thang theo R, số nguyên, mỗi mức xa hơn mức trước ít nhất 1 giá
            for m in LV.TP_R[:R.TP_COUNT]:
                buoc = max(buoc + 1, math.floor(m * rr + 0.5))
                tps.append(float(goc + dau * buoc))
        else:
            tps = [float(goc + dau * (LV.TP_FIRST + LV.TP_STEP * k)) for k in range(R.TP_COUNT)]
        return vao, sl, tuple(tps)
    return None


def bot_chon(nen: list, T, sp: float, cua_da: dict, dung, R, LV, BT, theo_thoi_gian: bool) -> dict:
    """Đi qua các nến tín hiệu, tự quyết từng nến có vào không; trạng thái lệnh mở lấy từ lệnh của dự án. Trả các bộ đếm và ví dụ lệch."""
    thu = sorted(nen, key=lambda x: (x['i'], x['thu_tu'])) if theo_thoi_gian else nen
    mo, ngay = [], {}                                                       # mo: (nến M1 được gọi lệnh mới, nến M1 đóng lệnh, khung)
    dem = {'khop': 0, 'cung_khong': 0, 'sat_nguong': 0, 'chi_du_an': [], 'chi_doc_lap': [], 'khac_gia': []}
    for x in thu:
        i, khung = x['i'], x['khung']
        if (i, khung) == dung:
            if not theo_thoi_gian:
                break                                                       # bộ kiểm của dự án dừng ở lệnh còn mở tới hết dữ liệu
            continue
        mo = [y for y in mo if y[1] >= i]
        vn = (int(T[i]) + 7 * 3600) // NGAY
        chan = (x['tre'] or len(mo) >= R.MAX_OPEN or any(y[2] == khung and y[0] >= i for y in mo) or ngay.get(vn, 0) >= R.MAX_PER_DAY)
        toi = None if chan else bot_dung(x['mua'], x['ds'], x['du_phong'], x['gia_mo'], sp, R, LV, BT.MAX_SPREAD_FRAC)
        p = cua_da.get((i, khung))
        if p is None and toi is None:
            dem['cung_khong'] += 1
        elif p is not None and toi is not None:
            giong = (p['mua'] == x['mua'] and abs(p['vao'] - toi[0]) < 1e-9 and abs(p['sl'] - toi[1]) < 1e-9 and len(p['tps']) == len(toi[2])
                     and all(abs(a - b) < 1e-9 for a, b in zip(p['tps'], toi[2])))
            if giong:
                dem['khop'] += 1
            elif x['sat']:
                dem['sat_nguong'] += 1
            else:
                dem['khac_gia'].append((int(T[i]), khung, (p['vao'], p['sl'], p['tps']), toi))
        elif x['sat']:
            dem['sat_nguong'] += 1
        else:
            dem['chi_du_an' if p is not None else 'chi_doc_lap'].append(
                (int(T[i]), khung, ', '.join(f'{y[2]} vào {gio(T[y[3]])}' for y in mo) or 'không có'))
        if p is not None:
            mo.append((p['duoc_goi'], p['dong'], khung, i))
            ngay[vn] = ngay.get(vn, 0) + 1
    return dem


def bot_dung_thu_tu(setups: list, mb: pd.DataFrame, R, LV, BT, TK) -> list[float]:
    """Chạy lại cả luật bot với tín hiệu xếp theo LÚC QUYẾT ĐỊNH (lúc nến tín hiệu đóng) thay vì giờ mở nến. Cùng các điều kiện chặn, cùng hàm
    dựng mức và cùng bộ theo dõi TP/SL của bot; chỉ khác thứ tự. Trả lãi lỗ từng lệnh (giá ở 0,01 lot, sau trượt giá của bộ kiểm)."""
    times = mb.index
    py = times.to_pydatetime()
    o, h, l, s_ = (mb[k].to_numpy(dtype=float) for k in ('open', 'high', 'low', 'spread'))
    T = giay(times)
    ra, mo, ngay = [], [], {}
    for x in sorted(setups, key=lambda x: (x.bar_time + pd.Timedelta(R.TIMEFRAMES[x.code]), x.bar_time)):
        den = x.bar_time + pd.Timedelta(R.TIMEFRAMES[x.code])
        i = int(times.searchsorted(den, side='left'))
        if i >= len(times):
            break
        mo = [y for y in mo if y[1] >= i]
        vn = (int(T[i]) + 7 * 3600) // NGAY
        if (times[i] - den > BT.MAX_ENTRY_DELAY or len(mo) >= R.MAX_OPEN or any(y[2] == x.code and y[0] >= i for y in mo)
                or ngay.get(vn, 0) >= R.MAX_PER_DAY):
            continue
        sig = LV.build(x, bid=o[i], ask=o[i] + s_[i], now=py[i], seq=1)
        if sig is None or s_[i] > BT.MAX_SPREAD_FRAC * sig.risk:
            continue
        st, ev, j, goi_lai = TK.new_state(sig), [], i, None
        while j < len(times) and not st.closed:
            ev += TK.on_bar(sig, st, py[j], o[j], h[j], l[j], s_[j])
            if goi_lai is None and st.next_tp >= R.REARM_AFTER_TP:
                goi_lai = j
            j += 1
        if not st.closed:
            break
        mo.append((j - 1 if goi_lai is None else goi_lai, j - 1, x.code))
        ngay[vn] = ngay.get(vn, 0) + 1
        ra.append(BT.result_r(sig, ev, BT.SLIP) * sig.risk)
    return ra


# ---- luật đỉnh/đáy, dựng lại -----------------------------------------------------------------------------------------------------------------
def dinh_day(M, sp: float, tin: np.ndarray, goi: dict, RF, C) -> dict:
    """Đi qua từng nến M15 đã đóng, tự quyết có tín hiệu hợp lệ không rồi so với lần gọi bộ chấm của dự án ở cùng nến."""
    T, O = M[0], M[1]
    het = T[-1] + 60
    t15, o15, h15, l15, c15 = (x for x in ghep(*M, 900))
    du = t15 + 900 <= het
    t15, o15, h15, l15, c15 = (x[du] for x in (t15, o15, h15, l15, c15))
    t30, _, h30, l30, c30 = ghep(*M, 1800)
    atr30, dong30 = atr_tb(h30, l30, c30, 14), t30 + 1800
    rong = C.NEWS_BLACKOUT_MIN * 60
    ne = set()                                                              # các giờ đóng nến M15 nằm trong vùng né tin
    for n in tin:
        k = math.ceil((n - rong) / 900)
        while k * 900 <= n + rong:
            ne.add(k * 900)
            k += 1
    ban, thua = None, {}
    dem = {'khop': 0, 'sat_nguong': 0, 'khong_hop_le': 0, 'chi_du_an': [], 'chi_doc_lap': [], 'khac_gia': [], 'tin_hieu': 0}
    for i in range(RF.LOOKBACK, len(t15)):
        td = int(t15[i]) + 900
        toi, sat = None, False
        j = int(np.searchsorted(T, td, side='left'))
        k = int(np.searchsorted(dong30, td, side='right')) - 1             # nến M30 đã đóng gần nhất
        if not (ban is not None and td <= ban) and j < len(T) and T[j] - td <= 300 and td not in ne and k >= 13:
            atr, bid = float(atr30[k]), float(O[j])
            ask = bid + sp
            if atr > 0:
                dinh, day = float(h15[i - RF.LOOKBACK:i].max()), float(l15[i - RF.LOOKBACK:i].min())
                o, h, l, c = float(o15[i]), float(h15[i]), float(l15[i]), float(c15[i])
                sat = min(abs(h - (dinh - RF.TOUCH_ATR * atr)), abs(l - (day + RF.TOUCH_ATR * atr))) < SAT
                huong = None
                if h >= dinh - RF.TOUCH_ATR * atr and c < o and c < dinh:
                    huong, dau, vao, sl = 'BAN', -1.0, bid, max(dinh, h) + RF.BUFFER_ATR * atr
                elif l <= day + RF.TOUCH_ATR * atr and c > o and c > day:
                    huong, dau, vao, sl = 'MUA', 1.0, ask, min(day, l) - RF.BUFFER_ATR * atr
                if huong is not None and huong not in thua.get(td // NGAY, ()):
                    rr = abs(vao - sl)
                    sat |= min(abs(rr - RF.SL_ATR_MIN * atr), abs(rr - RF.SL_ATR_MAX * atr)) < SAT
                    if RF.SL_ATR_MIN * atr <= rr <= RF.SL_ATR_MAX * atr:
                        tp = vao + dau * RF.TP_R * rr
                        sl2, tps = round(sl, 2), (round(tp, 2), round(tp + dau * RF.TP_STEP, 2), round(tp + dau * 2 * RF.TP_STEP, 2))
                        # bộ kiểm tra tín hiệu: giá khớp là Ask (mua) hoặc Bid (bán), dừng lỗ đúng phía và trong khoảng ATR, ba mức chốt xa dần
                        d = (vao - sl2) * dau
                        xa = [(x - vao) * dau for x in tps]
                        hop = (sl2 > 0 and all(x > 0 for x in tps) and abs(vao - (bid + ask) / 2) <= C.ENTRY_MAX_ATR * atr and d > 0
                               and C.SL_ATR_MIN * atr <= d <= C.SL_ATR_MAX * atr and 0 < xa[0] < xa[1] < xa[2]
                               and xa[0] >= C.TP1_MIN_R * d - 1e-9 and (ask - bid) <= C.SPREAD_MAX_FRAC_SL * d + 1e-9)
                        sat |= d > 0 and min(abs(d - C.SL_ATR_MIN * atr), abs(d - C.SL_ATR_MAX * atr), abs(xa[0] - C.TP1_MIN_R * d)) < SAT
                        if hop:
                            toi = (huong, vao, sl2, tps)
                        else:
                            dem['khong_hop_le'] += 1
        p = goi.get(td)
        if toi is not None:
            dem['tin_hieu'] += 1
        if p is not None and toi is not None:
            v = p[0]
            if (v.huong == toi[0] and abs(v.gia_tham_chieu - toi[1]) < 1e-9 and abs(v.sl - toi[2]) < 1e-9
                    and all(abs(a - b) < 1e-9 for a, b in zip((v.tp1, v.tp2, v.tp3), toi[3]))):
                dem['khop'] += 1
            elif sat:
                dem['sat_nguong'] += 1
            else:
                dem['khac_gia'].append((td, (v.huong, v.gia_tham_chieu, v.sl, v.tp1), toi))
        elif p is not None or toi is not None:
            if sat:
                dem['sat_nguong'] += 1
            else:
                dem['chi_du_an' if p is not None else 'chi_doc_lap'].append(td)
        if p is not None:                                                   # trạng thái đi tiếp lấy từ kết quả chấm của dự án
            o_ = p[1]
            if o_ is None:
                break                                                       # lệnh còn chạy tới hết dữ liệu: dự án dừng ở đây
            if o_.trang_thai == 'da_dong' and o_.r is not None:
                ban = int(pd.Timestamp(o_.t_dong).timestamp())
                if o_.r <= 0:
                    thua.setdefault(td // NGAY, set()).add(p[0].huong)
    return dem


def gio(x) -> str:
    return f'{pd.Timestamp(int(x), unit="s"):%d/%m/%Y %H:%M} UTC'


if __name__ == '__main__':
    tu_nam = int(sys.argv[1]) if len(sys.argv) > 1 else 2015
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    g = cfg['gia']
    gia._nap_ma(g)
    from ai import config as C, rule_fade as RF, scorer as SC, snapshot as SN       # noqa: E402 - mã của chủ dự án, chỉ đọc
    from tinhieu import backtest as BT, levels as LV, rules as R, tracker as TK     # noqa: E402

    if tuple(R.KINDS) != ('DON',) or R.PULLBACK > 0 or LV.BE_AFTER:
        print('Cấu hình luật bot đã đổi (kiểu vào khác DON, chờ giá hồi, hoặc dời dừng lỗ): bản dựng lại chưa viết cho cấu hình này.')
        sys.exit(1)
    t0 = time.time()
    sp = float(g.get('spread', 0.17))
    khung_bot = tuple((cfg.get('kiem_chung') or {}).get('khung_bot', ('M5', 'M15')))
    m1 = hoc._m1_dai(g, tu_nam)
    fr = hoc._khung(m1, g)
    tin, _ = SN.load_high_usd_news(Path(os.path.expandvars(g['lich_tin']))) if g.get('lich_tin') else ([], None)
    T = giay(m1.index)
    M = (T, *(m1[k].to_numpy(dtype=float) for k in ('open', 'high', 'low', 'close')))
    print(f'Vàng từ {tu_nam}: {len(m1):,} nến 1 phút · spread {sp:g} · {len(tin):,} mốc tin USD mức cao · nạp dữ liệu {time.time() - t0:.0f} giây', flush=True)

    # ---- nến ghép: bản dựng lại so với webapp ----
    lech_nen = 0
    for tf, dai in (('M15', 900), ('M30', 1800)):
        a = ghep(*M, dai)
        du = a[0] + dai <= T[-1] + 60
        b = fr[tf]
        if int(du.sum()) != len(b) or not np.array_equal(a[0][du], giay(b.index)) or any(
                not np.array_equal(x[du], b[k].to_numpy(dtype=float)) for x, k in zip(a[1:], ('open', 'high', 'low', 'close'))):
            lech_nen += 1
    D = nen_ngay(*M, os.path.expandvars(g.get('d1_goc') or ''))
    d1 = fr['D1']
    if len(D[0]) != len(d1) or not np.array_equal(D[0], giay(d1.index)) or any(
            not np.allclose(x, d1[k].to_numpy(dtype=float), rtol=0, atol=1e-9) for x, k in zip(D[1:], ('open', 'high', 'low', 'close'))):
        lech_nen += 1
    print(f'Nến ghép M15, M30 và nến ngày ({len(D[0]):,} ngày): {"trùng với webapp" if not lech_nen else f"{lech_nen} khung LỆCH"}', flush=True)

    # ---- luật bot: chạy mã của dự án, ghi lại tín hiệu, lệnh và mức đã dựng ----
    t1 = time.time()
    ghi_scan, ghi_build, ghi_sim = {}, {}, []
    goc_scan, goc_build, goc_sim = R.scan, LV.build, BT.simulate

    def scan(bars, h1, h4, d1_, tf='M5', kinds=None):
        out = goc_scan(bars, h1, h4, d1_, tf, kinds)
        ghi_scan[tf] = out
        return out

    def build(setup, bid, ask, now, seq):
        s = goc_build(setup, bid, ask, now, seq)
        if s is not None:
            ghi_build[(int(pd.Timestamp(now).timestamp()), s.code)] = s
        return s

    def simulate(setups, m1_, *a, **k):
        out = goc_sim(setups, m1_, *a, **k)
        ghi_sim.append(out)
        return out
    R.scan, LV.build, BT.simulate = scan, build, simulate
    try:
        kq_bot = kiem_chung._bot(g, m1, fr['D1'], sp, khung_bot)
    finally:
        R.scan, LV.build, BT.simulate = goc_scan, goc_build, goc_sim
    lenh_bot = ghi_sim[0]
    assert len(lenh_bot) == len(kq_bot['lenh'])
    print(f'Luật bot, mã của dự án: {sum(len(v) for v in ghi_scan.values()):,} ứng viên · {len(lenh_bot):,} lệnh · {time.time() - t1:.0f} giây', flush=True)

    t1 = time.time()
    th1, _, _, _, ch1 = ghep(*M, 3600)
    th4, _, _, _, ch4 = ghep(*M, 14400)
    e200 = ema(D[4], R.EMA_D1)
    e200[:R.D1_MIN_BARS] = np.nan
    lon = {'H1': (th1 + 3600, ema(ch1, R.EMA_FAST) - ema(ch1, R.EMA_SLOW)), 'H4': (th4 + 14400, ema(ch4, R.EMA_FAST) - ema(ch4, R.EMA_SLOW)),
           'D1': (D[0] + NGAY, D[4] - e200), 'ATR_D1': atr_tb(D[2], D[3], D[4], R.ATR_PERIOD)}
    tang1 = {'khop': 0, 'sat_nguong': 0, 'chi_du_an': [], 'chi_doc_lap': [], 'khac_ung_vien': []}
    nen_bot = []
    for so_khung, tf in enumerate(khung_bot):
        dai = int(pd.Timedelta(R.TIMEFRAMES[tf]).total_seconds())
        toi, suyt = bot_tin_hieu(tf, M, lon, R)
        da = {}
        for s in ghi_scan.get(tf, []):
            x = da.setdefault(int(s.bar_time.timestamp()), {'mua': s.side == 'BUY', 'ds': [], 'du_phong': None})
            if s.sl_fixed:
                x['du_phong'] = float(s.sl_fixed)
            else:
                x['ds'].append(float(s.sl_price))
        for tm in sorted(set(toi) | set(da)):
            a, b = toi.get(tm), da.get(tm)
            if a is not None and b is not None:
                giong = (a[0] == b['mua'] and a[1] == b['ds']
                         and (a[2] is None) == (b['du_phong'] is None) and (a[2] is None or abs(a[2] - b['du_phong']) < 1e-9))
                if giong:
                    tang1['khop'] += 1
                elif a[3]:
                    tang1['sat_nguong'] += 1
                else:
                    tang1['khac_ung_vien'].append((tm, tf, (b['mua'], b['ds'], b['du_phong']), a[:3]))
            elif (a is not None and a[3]) or (a is None and tm in suyt):
                tang1['sat_nguong'] += 1
            else:
                tang1['chi_du_an' if a is None else 'chi_doc_lap'].append((tm, tf))
            if b is None:
                continue                                                    # tầng 2 và 3 đi theo đúng các nến mà dự án đã xét
            i = int(np.searchsorted(T, tm + dai, side='left'))
            if i >= len(T):
                continue
            # tầng 2, 3 dùng ứng viên của BẢN DỰNG LẠI khi nó có; nến chỉ dự án có thì bản dựng lại coi như không có tín hiệu
            nen_bot.append({'khung': tf, 'bar': tm, 'so_khung': so_khung, 'i': i, 'tre': bool(T[i] - (tm + dai) > BT.MAX_ENTRY_DELAY.total_seconds()),
                            'mua': a[0] if a else b['mua'], 'ds': a[1] if a else [], 'du_phong': a[2] if a else None, 'co': a is not None,
                            'sat': bool(a[3]) if a else tm in suyt, 'gia_mo': float(M[1][i])})
    nen_bot.sort(key=lambda x: (x['bar'], x['so_khung']))                   # thứ tự xử lý của bộ kiểm trong dự án: theo giờ mở nến tín hiệu
    for n, x in enumerate(nen_bot):
        x['thu_tu'] = n
    cua_da = {}
    for x in lenh_bot:
        i = int(np.searchsorted(T, int(pd.Timestamp(x['entry_time']).timestamp()), side='left'))
        dong = int(np.searchsorted(T, int(pd.Timestamp(x['exit_time']).timestamp()), side='left'))
        s = ghi_build[(int(T[i]), x['tf'])]
        mua = s.side == 'BUY'
        cham = (M[2][i:dong + 1] >= s.tps[R.REARM_AFTER_TP - 1]) if mua else (M[3][i:dong + 1] + sp <= s.tps[R.REARM_AFTER_TP - 1])
        cua_da[(i, x['tf'])] = {'mua': mua, 'vao': float(s.entry), 'sl': float(s.sl), 'tps': tuple(float(y) for y in s.tps),
                                'duoc_goi': i + int(np.argmax(cham)) if cham.any() else dong, 'dong': dong}
    da_vao = {(int(T[i]), k) for i, k in cua_da}
    con_mo = [k for k in ghi_build if k not in da_vao]                      # lệnh đã dựng nhưng còn mở tới hết dữ liệu: dự án dừng ở đó
    dung = (int(np.searchsorted(T, min(con_mo)[0], side='left')), min(con_mo)[1]) if con_mo else None

    for x in nen_bot:
        if not x['co']:
            x['tre'] = True                                                 # bản dựng lại không có tín hiệu ở nến này: không vào
    tang2 = bot_chon(nen_bot, T, sp, cua_da, dung, R, LV, BT, theo_thoi_gian=False)
    tang3 = bot_chon(nen_bot, T, sp, cua_da, dung, R, LV, BT, theo_thoi_gian=True)
    print(f'Luật bot, bản dựng lại: {time.time() - t1:.0f} giây')
    print(f'  Tầng 1 · nến tín hiệu: trùng cả chiều và các mức dừng lỗ ứng viên {tang1["khop"]:,} · chỉ dự án có {len(tang1["chi_du_an"])} · '
          f'chỉ bản dựng lại có {len(tang1["chi_doc_lap"])} · khác ứng viên {len(tang1["khac_ung_vien"])} · đúng ngưỡng (sai số làm tròn) {tang1["sat_nguong"]}')
    print(f'  Tầng 2 · lệnh, theo thứ tự xử lý của dự án: trùng giá vào, dừng lỗ và {R.TP_COUNT} mức chốt {tang2["khop"]:,}/{len(lenh_bot):,} · cùng không vào '
          f'{tang2["cung_khong"]:,} · chỉ dự án vào {len(tang2["chi_du_an"])} · chỉ bản dựng lại vào {len(tang2["chi_doc_lap"])} · khác giá {len(tang2["khac_gia"])} · '
          f'đúng ngưỡng {tang2["sat_nguong"]}')
    doi = len(tang3['chi_du_an']) + len(tang3['chi_doc_lap'])
    print(f'  Tầng 3 · nếu xử lý theo đúng thứ tự thời gian: {doi} quyết định sẽ khác ({len(tang3["chi_du_an"])} lệnh dự án đã vào sẽ bị chặn, '
          f'{len(tang3["chi_doc_lap"])} lệnh dự án bỏ sẽ được vào), trên {len(lenh_bot):,} lệnh')
    for ten, ds in (('chỉ dự án có nến tín hiệu', tang1['chi_du_an']), ('chỉ bản dựng lại có nến tín hiệu', tang1['chi_doc_lap']),
                    ('khác ứng viên', tang1['khac_ung_vien']), ('chỉ dự án vào lệnh', tang2['chi_du_an']), ('chỉ bản dựng lại vào lệnh', tang2['chi_doc_lap']),
                    ('khác giá', tang2['khac_gia']), ('tầng 3, dự án vào', tang3['chi_du_an']), ('tầng 3, dự án bỏ', tang3['chi_doc_lap'])):
        for x in ds[:4]:
            print(f'     {ten}: {gio(x[0])} {x[1]}' + (f' · dự án {x[2]} · dựng lại {x[3]}' if len(x) > 3 else f' · lệnh đang mở lúc xét: {x[2]}' if len(x) > 2 else ''))
    t1 = time.time()
    theo_tg = bot_dung_thu_tu([x for tf in khung_bot for x in ghi_scan.get(tf, [])], m1.assign(spread=sp), R, LV, BT, TK)
    tong_da, tong_tg = float(sum(x['usd'] for x in lenh_bot)), float(sum(theo_tg))
    print(f'  Chạy lại cả luật bot theo đúng thứ tự thời gian (cùng bộ theo dõi TP/SL của bot): {len(theo_tg):,} lệnh, tổng {tong_tg:+,.0f} giá · '
          f'theo thứ tự của bộ kiểm trong dự án: {len(lenh_bot):,} lệnh, tổng {tong_da:+,.0f} giá · {time.time() - t1:.0f} giây', flush=True)
    khac_bot = (len(tang1['chi_du_an']) + len(tang1['chi_doc_lap']) + len(tang1['khac_ung_vien'])
                + len(tang2['chi_du_an']) + len(tang2['chi_doc_lap']) + len(tang2['khac_gia']))

    # ---- luật đỉnh/đáy ----
    t1 = time.time()
    goi, goc_score = {}, SC.score

    def score(v, t, bars, now, news):
        o = goc_score(v, t, bars, now, news)
        goi[int(pd.Timestamp(t).timestamp())] = (v, o)
        return o
    SC.score = score
    try:
        kq_dd = kiem_chung._dinh_day(g, m1, fr, sp, tin)
    finally:
        SC.score = goc_score
    print(f'Luật đỉnh/đáy, mã của dự án: {len(goi):,} tín hiệu hợp lệ · {len(kq_dd["lenh"]):,} lệnh đã đóng · {kq_dd["khong_hop_le"]:,} tín hiệu bị bộ kiểm tra loại · '
          f'{time.time() - t1:.0f} giây', flush=True)
    t1 = time.time()
    dd = dinh_day(M, sp, np.array(sorted(pd.Timestamp(x).timestamp() for x in tin), dtype=float), goi, RF, C)
    lech_loai = dd['khong_hop_le'] != kq_dd['khong_hop_le']
    print(f'Luật đỉnh/đáy, bản dựng lại: {dd["tin_hieu"]:,} tín hiệu hợp lệ · {time.time() - t1:.0f} giây')
    print(f'  Trùng chiều, giá khớp, dừng lỗ và ba mức chốt: {dd["khop"]:,}/{len(goi):,} · chỉ dự án có {len(dd["chi_du_an"])} · chỉ bản dựng lại có '
          f'{len(dd["chi_doc_lap"])} · khác giá {len(dd["khac_gia"])} · đúng ngưỡng (sai số làm tròn) {dd["sat_nguong"]} · tín hiệu bị loại: dự án '
          f'{kq_dd["khong_hop_le"]:,}, bản dựng lại {dd["khong_hop_le"]:,}')
    for ten, ds in (('chỉ dự án có', dd['chi_du_an']), ('chỉ bản dựng lại có', dd['chi_doc_lap'])):
        for x in ds[:4]:
            print(f'     {ten}: nến M15 đóng {gio(x)}')
    for x in dd['khac_gia'][:4]:
        print(f'     khác giá: nến M15 đóng {gio(x[0])} · dự án {x[1]} · dựng lại {x[2]}')
    khac_dd = len(dd['chi_du_an']) + len(dd['chi_doc_lap']) + len(dd['khac_gia']) + int(lech_loai)

    khac = khac_bot + khac_dd + lech_nen
    print(f'\nTỔNG: luật bot {tang1["khop"]:,} nến tín hiệu trùng, {tang2["khop"]:,}/{len(lenh_bot):,} lệnh trùng · luật đỉnh/đáy {dd["khop"]:,}/{len(goi):,} tín hiệu trùng · '
          f'đúng ngưỡng {tang1["sat_nguong"] + tang2["sat_nguong"] + dd["sat_nguong"]} · thứ tự xử lý đổi {doi} quyết định của luật bot')
    print(f'Khác chưa giải thích được: {khac}')
    sys.exit(1 if khac else 0)
