"""Phân tích hiệu suất giao dịch từ lịch sử lệnh trong MT5 (CHỈ ĐỌC): ghép các lần khớp thành từng lệnh, tính chỉ số, đường vốn, sụt vốn,
lịch lãi/lỗ theo ngày, bảng theo mã / phiên / thứ / giờ / thời gian giữ / nguồn, và nhận xét bằng lời có ngưỡng đủ mẫu.

Nguồn: history_deals_get và history_orders_get của MT5 (hai hàm đọc); rủi ro ban đầu của mỗi lệnh lấy từ dừng lỗ đặt lúc mở lệnh và quy ra tiền
bằng order_calc_profit (hàm tính thuần, không gửi lệnh). Mặc định chỉ đọc tài khoản demo (`gia.mt5.chi_demo`, như lớp nối MT5). Số tài khoản được che.

`mau=True` trả dữ liệu MINH HỌA (lệnh giả lập, cố định theo hạt giống) để người mới xem trước trang khi chưa có lịch sử; trang ghi rõ điều đó."""
from __future__ import annotations

import csv
import io
import math
import random
from datetime import datetime, timedelta, timezone

from . import song

VN = timezone(timedelta(hours=7))
PHIEN = (('Á', 0, 7), ('Âu', 7, 12), ('Mỹ', 12, 20), ('Cuối ngày', 20, 24))       # theo giờ UTC lúc mở lệnh, cùng cách chia với hoc.py
THU = ('Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ nhật')
GIU = ((0, 15, '< 15 phút'), (15, 60, '15–60 phút'), (60, 240, '1–4 giờ'), (240, 1440, '4–24 giờ'), (1440, 10 ** 9, '> 1 ngày'))
DU_MAU = 10                                                                    # nhóm có ít lệnh hơn thì không đưa ra nhận xét
_nho: dict = {}


def _r(x, d: int = 2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if x != x or math.isinf(x) else round(x, d)


# --------------------------------------------------------------------------- ghép lần khớp thành lệnh
def ghep_lenh(deals, orders=(), ten_nguon=lambda m: 'Đặt tay' if not m else f'EA {m}', rui_ro=None) -> tuple[list[dict], list[dict]]:
    """Lần khớp MT5 → (lệnh đã đóng hết, thay đổi số dư). Mỗi lệnh gom theo position_id: chiều và giờ mở theo lần khớp VÀO đầu tiên, giá vào/ra
    bình quân theo khối lượng, lãi ròng = lãi + hoa hồng + swap + phí của mọi lần khớp. Vị thế còn mở (khối lượng ra < vào) bị bỏ.
    `rui_ro(ma, chieu, lot, vao, sl)` trả số tiền mất nếu chạm SL (để tính R); None thì không tính R."""
    sl_cua = {int(o.ticket): float(o.sl or 0) for o in orders}
    tp_cua = {int(o.ticket): float(o.tp or 0) for o in orders}
    so_du, theo = [], {}
    for x in sorted(deals, key=lambda x: (x.time_msc if getattr(x, 'time_msc', 0) else x.time * 1000)):
        if int(x.type) not in (0, 1):
            so_du.append({'t': datetime.fromtimestamp(int(x.time), timezone.utc).isoformat(), 'tien': _r(x.profit), 'loai': int(x.type), 'ghi': x.comment or ''})
            continue
        theo.setdefault(int(x.position_id), []).append(x)
    lenh = []
    for pid, ds in theo.items():
        vao = [x for x in ds if int(x.entry) == 0]
        ra = [x for x in ds if int(x.entry) in (1, 2, 3)]
        if not vao or not ra:
            continue
        v_vao, v_ra = sum(float(x.volume) for x in vao), sum(float(x.volume) for x in ra)
        if v_ra + 1e-9 < v_vao:
            continue                                                        # còn mở một phần
        dau = vao[0]
        mua = int(dau.type) == 0
        gia_vao = sum(float(x.price) * float(x.volume) for x in vao) / v_vao
        gia_ra = sum(float(x.price) * float(x.volume) for x in ra) / v_ra
        lai = sum(float(x.profit) for x in ds)
        phi = sum(float(x.commission) + float(getattr(x, 'fee', 0) or 0) for x in ds)
        swap = sum(float(x.swap) for x in ds)
        rong = lai + phi + swap
        mo = datetime.fromtimestamp(int(dau.time), timezone.utc)
        dong = datetime.fromtimestamp(int(ra[-1].time), timezone.utc)
        sl = sl_cua.get(int(dau.order), 0.0)
        r_tien = None
        if sl and rui_ro is not None:
            try:
                r_tien = rui_ro(dau.symbol, 'mua' if mua else 'ban', v_vao, gia_vao, sl)
            except Exception:                                               # noqa: BLE001
                r_tien = None
        lenh.append({'id': pid, 'ma': dau.symbol, 'chieu': 'MUA' if mua else 'BAN', 'lot': _r(v_vao, 3), 'vao': gia_vao, 'ra': gia_ra,
                     'mo': mo.isoformat(), 'dong': dong.isoformat(), 'phut': round((dong - mo).total_seconds() / 60, 1),
                     'lai': _r(lai), 'phi': _r(phi), 'swap': _r(swap), 'rong': _r(rong), 'sl': sl or None, 'tp': tp_cua.get(int(dau.order)) or None,
                     'r': _r(rong / r_tien, 2) if r_tien and r_tien > 0 else None, 'rui_ro': _r(r_tien), 'nguon': ten_nguon(int(dau.magic)),
                     'magic': int(dau.magic)})
    lenh.sort(key=lambda x: x['dong'])
    return lenh, so_du


# --------------------------------------------------------------------------- chỉ số
def _nhom_so(ds: list[dict]) -> dict:
    """Chỉ số cho một nhóm lệnh."""
    v = [x['rong'] for x in ds]
    n = len(v)
    thang = [x for x in v if x > 0]
    thua = [x for x in v if x < 0]
    lg, lo = sum(thang), -sum(thua)
    rr = [x['r'] for x in ds if x.get('r') is not None]
    return {'n': n, 'thang': len(thang), 'thua': len(thua), 'ty_le': _r(len(thang) / n * 100, 1) if n else None, 'rong': _r(sum(v)),
            'tb': _r(sum(v) / n) if n else None, 'pf': _r(lg / lo, 2) if lo > 0 else (None if not lg else float('inf')),
            'tb_thang': _r(lg / len(thang)) if thang else None, 'tb_thua': _r(-lo / len(thua)) if thua else None,
            'r_tb': _r(sum(rr) / len(rr), 2) if rr else None, 'n_r': len(rr)}


def _pf_json(x):
    return 'inf' if x == float('inf') else x


def phan_tich(lenh: list[dict], so_du_dau: float | None = None, tien: str = 'USD') -> dict:
    """Mọi chỉ số, đường vốn, lịch theo ngày, các bảng phân nhóm và nhận xét cho danh sách lệnh (cũ trước)."""
    tong = _nhom_so(lenh)
    tong['pf'] = _pf_json(tong['pf'])
    phi = sum(x['phi'] or 0 for x in lenh)
    swap = sum(x['swap'] or 0 for x in lenh)
    lai_gop = sum(x['lai'] for x in lenh if x['lai'] > 0)
    # đường vốn và sụt vốn (theo lệnh đã đóng)
    goc = so_du_dau if so_du_dau and so_du_dau > 0 else None
    cong, dinh, dd_max, dd_pct, duong = 0.0, 0.0, 0.0, 0.0, []
    for x in lenh:
        cong += x['rong']
        dinh = max(dinh, cong)
        dd = dinh - cong
        if dd > dd_max:
            dd_max = dd
            dd_pct = dd / (goc + dinh) * 100 if goc else 0.0
        duong.append({'t': x['dong'], 'v': _r(cong), 'dd': _r(-dd)})
    # chuỗi thắng/thua
    cur, best = {'t': 0, 'l': 0}, {'t': 0, 'l': 0}
    for x in lenh:
        if not x['rong']:                                                    # hòa vốn: không thắng, không thua, giữ nguyên chuỗi
            continue
        k = 't' if x['rong'] > 0 else 'l'
        cur[k] += 1
        cur['l' if k == 't' else 't'] = 0
        best[k] = max(best[k], cur[k])
    # theo ngày (giờ Việt Nam)
    ngay: dict = {}
    for x in lenh:
        k = datetime.fromisoformat(x['dong']).astimezone(VN).date().isoformat()
        o = ngay.setdefault(k, {'ngay': k, 'rong': 0.0, 'n': 0})
        o['rong'] += x['rong']
        o['n'] += 1
    for o in ngay.values():
        o['rong'] = _r(o['rong'])
    # phân nhóm
    def theo(ham, thu_tu=None):
        g: dict = {}
        for x in lenh:
            g.setdefault(ham(x), []).append(x)
        ks = thu_tu if thu_tu else sorted(g, key=lambda k: -len(g[k]))
        return [{'k': k, 'k_en': NHOM_EN.get(k, k) if isinstance(k, str) else k, **{a: _pf_json(b) for a, b in _nhom_so(g[k]).items()}} for k in ks if k in g]

    def phien(x):
        h = datetime.fromisoformat(x['mo']).hour
        return next(p for p, a, b in PHIEN if a <= h < b)

    def giu(x):
        return next(t for a, b, t in GIU if a <= x['phut'] < b)
    bang = {
        'ma': theo(lambda x: x['ma']),
        'chieu': theo(lambda x: x['chieu'], ['MUA', 'BAN']),
        'phien': theo(phien, [p for p, _, _ in PHIEN]),
        'thu': theo(lambda x: THU[datetime.fromisoformat(x['mo']).astimezone(VN).weekday()], list(THU)),
        'gio': theo(lambda x: datetime.fromisoformat(x['mo']).astimezone(VN).hour, list(range(24))),
        'giu': theo(giu, [t for _, _, t in GIU]),
        'nguon': theo(lambda x: x['nguon']),
    }
    phut_thang = [x['phut'] for x in lenh if x['rong'] > 0]
    phut_thua = [x['phut'] for x in lenh if x['rong'] < 0]
    out = {'tong': {**tong, 'phi': _r(phi), 'swap': _r(swap), 'lai_gop': _r(lai_gop), 'dd_max': _r(dd_max), 'dd_pct': _r(dd_pct, 1) if goc else None,
                    'chuoi_thang': best['t'], 'chuoi_thua': best['l'], 'giu_tb': _r(sum(x['phut'] for x in lenh) / len(lenh), 1) if lenh else None,
                    'giu_thang': _r(sum(phut_thang) / len(phut_thang), 1) if phut_thang else None,
                    'giu_thua': _r(sum(phut_thua) / len(phut_thua), 1) if phut_thua else None,
                    'tot_nhat': max(lenh, key=lambda x: x['rong']) if lenh else None, 'te_nhat': min(lenh, key=lambda x: x['rong']) if lenh else None,
                    'khong_sl': sum(1 for x in lenh if not x.get('sl')), 'so_du_dau': _r(goc), 'tien': tien},
           'duong_von': duong, 'ngay': sorted(ngay.values(), key=lambda o: o['ngay']), 'bang': bang}
    out['nhan_xet'] = nhan_xet(lenh, out)
    return out


# --------------------------------------------------------------------------- nhận xét (song ngữ)
def _vn(x: float, so: int) -> str:
    """Số thập phân kiểu Việt Nam (dấu phẩy) cho câu nhận xét tiếng Việt."""
    return f'{x:.{so}f}'.replace('.', ',')


def _fmt(x: float, tien: str, en: bool = False) -> str:
    """Số tiền: kiểu Việt Nam (1.706,52) hoặc kiểu Anh (1,706.52)."""
    s = f'{abs(x):,.2f}'
    if not en:
        s = s.replace(',', '§').replace('.', ',').replace('§', '.')
    return f'{"+" if x > 0 else "−" if x < 0 else ""}{s} {tien}'


NHOM_EN = {'Á': 'Asia', 'Âu': 'Europe', 'Mỹ': 'US', 'Cuối ngày': 'Late US', 'Thứ Hai': 'Monday', 'Thứ Ba': 'Tuesday', 'Thứ Tư': 'Wednesday',
           'Thứ Năm': 'Thursday', 'Thứ Sáu': 'Friday', 'Thứ Bảy': 'Saturday', 'Chủ nhật': 'Sunday', '< 15 phút': '< 15 min', '15–60 phút': '15–60 min',
           '1–4 giờ': '1–4 h', '4–24 giờ': '4–24 h', '> 1 ngày': '> 1 day', 'Đặt tay': 'Manual', 'EA mẫu': 'Sample EA', 'MUA': 'BUY', 'BAN': 'SELL'}


def nhan_xet(lenh: list[dict], kq: dict) -> list[dict]:
    """Các nhận xét bằng lời, mỗi cái có sẵn bản tiếng Việt và tiếng Anh ({'muc', 'vi': {tieu, noi}, 'en': {tieu, noi}}): câu chứa tên mã, phiên,
    khung giờ thay đổi theo dữ liệu nên không dịch được bằng từ điển. Mỗi nhận xét chỉ đưa ra khi nhóm liên quan có ít nhất DU_MAU lệnh."""
    t = kq['tong']
    tien = t['tien']
    n = t['n']
    out = []

    def F(x):
        return _fmt(x, tien)

    def E(x):
        return _fmt(x, tien, True)

    def G(k):
        return NHOM_EN.get(k, k)

    def them(muc, vi, en):
        out.append({'muc': muc, 'vi': {'tieu': vi[0], 'noi': vi[1]}, 'en': {'tieu': en[0], 'noi': en[1]}})
    if n == 0:
        them('tin', ('Chưa có lệnh đã đóng', 'Trong khoảng này chưa có lệnh nào đóng hết. Chọn khoảng dài hơn hoặc xem dữ liệu minh họa.'),
             ('No closed trades yet', 'No trade was fully closed in this period. Pick a longer period or view the sample data.'))
        return out
    if n < 30:
        them('tin', (f'Mới có {n} lệnh', 'Dưới 30 lệnh thì tỷ lệ thắng và lãi trung bình còn dao động mạnh do may rủi; các nhận xét dưới đây chỉ để tham khảo.'),
             (f'Only {n} trades', 'Below 30 trades, win rate and average profit still swing a lot by chance; treat the notes below as indicative only.'))
    if t['tb_thang'] and t['tb_thua']:
        payoff = t['tb_thang'] / -t['tb_thua']
        can = 1 / (1 + payoff) * 100
        muc = 'tot' if t['ty_le'] > can + 3 else 'xau' if t['ty_le'] < can - 3 else 'chu_y'
        them(muc, (f'Thắng {t["ty_le"]:.0f}%, cần {can:.0f}% để hòa vốn',
                   f'Lệnh thắng trung bình {F(t["tb_thang"])}, lệnh thua trung bình {F(t["tb_thua"])} (tỷ lệ lời/lỗ {_vn(payoff, 2)}). '
                   f'Với tỷ lệ đó bạn cần thắng hơn {can:.0f}% số lệnh mới có lãi; hiện tại là {t["ty_le"]:.0f}% trên {n} lệnh.'),
             (f'Winning {t["ty_le"]:.0f}%, {can:.0f}% needed to break even',
              f'Average win {E(t["tb_thang"])}, average loss {E(t["tb_thua"])} (payoff ratio {payoff:.2f}). '
              f'With that ratio you need to win more than {can:.0f}% of trades to be profitable; you are at {t["ty_le"]:.0f}% over {n} trades.'))
    if t['giu_thang'] and t['giu_thua'] and t['thang'] >= DU_MAU and t['thua'] >= DU_MAU and t['giu_thua'] > 1.5 * t['giu_thang']:
        k = t['giu_thua'] / t['giu_thang']
        them('xau', ('Giữ lệnh thua lâu hơn lệnh thắng',
                     f'Lệnh thua được giữ trung bình {t["giu_thua"]:.0f} phút, gấp {_vn(k, 1)} lần lệnh thắng ({t["giu_thang"]:.0f} phút). '
                     'Đây là dấu hiệu quen thuộc của "chốt lời sớm, gồng lỗ"; đặt dừng lỗ và chốt lời từ lúc vào lệnh giúp tránh việc này.'),
             ('Losers are held longer than winners',
              f'Losing trades are held {t["giu_thua"]:.0f} minutes on average, {k:.1f}× as long as winners ({t["giu_thang"]:.0f} minutes). '
              'This is the classic “cut winners early, let losers run” pattern; setting stop loss and take profit at entry helps avoid it.'))
    for ten, nvi, nen in (('ma', 'Mã', 'Symbol'), ('phien', 'Phiên', 'Session'), ('thu', 'Ngày', 'Day'), ('giu', 'Thời gian giữ', 'Holding time')):
        g = [x for x in kq['bang'][ten] if x['n'] >= DU_MAU]
        if len(g) < 2:
            continue
        te = min(g, key=lambda x: x['rong'])
        tot = max(g, key=lambda x: x['rong'])
        if te['rong'] < 0 and te['rong'] < -0.15 * abs(t['rong'] or 1) and te is not tot:
            them('xau', (f'{nvi} kéo kết quả xuống: {te["k"]}',
                         f'{te["n"]} lệnh, thắng {te["ty_le"]:.0f}%, tổng {F(te["rong"])}. Nhóm tốt nhất là {tot["k"]}: {tot["n"]} lệnh, tổng {F(tot["rong"])}.'),
                 (f'{nen} dragging results down: {G(te["k"])}',
                  f'{te["n"]} trades, {te["ty_le"]:.0f}% won, total {E(te["rong"])}. The best group is {G(tot["k"])}: {tot["n"]} trades, total {E(tot["rong"])}.'))
    if t['lai_gop'] and (t['phi'] or t['swap']):
        ty = -((t['phi'] or 0) + min(t['swap'] or 0, 0)) / t['lai_gop'] * 100
        if ty >= 10:
            them('chu_y', (f'Phí và swap ăn {ty:.0f}% lãi gộp',
                           f'Hoa hồng và phí {F(t["phi"] or 0)}, swap {F(t["swap"] or 0)} so với lãi gộp {F(t["lai_gop"])}. '
                           'Giảm số lệnh nhỏ, tránh giữ qua đêm khi swap âm, hoặc chọn tài khoản phí thấp hơn.'),
                 (f'Fees and swap eat {ty:.0f}% of gross profit',
                  f'Commission and fees {E(t["phi"] or 0)}, swap {E(t["swap"] or 0)} against gross profit {E(t["lai_gop"])}. '
                  'Take fewer small trades, avoid holding overnight when swap is negative, or choose a lower-cost account.'))
    if t['khong_sl'] and n >= DU_MAU and t['khong_sl'] / n >= 0.2:
        pc = t['khong_sl'] / n * 100
        them('xau', (f'{t["khong_sl"]} lệnh ({pc:.0f}%) mở không có dừng lỗ',
                     'Lệnh không có dừng lỗ là nguồn chính của các khoản lỗ lớn bất ngờ. Công cụ "Khối lượng theo rủi ro" tính khối lượng từ dừng lỗ.'),
             (f'{t["khong_sl"]} trades ({pc:.0f}%) opened without a stop loss',
              'Trades without a stop loss are the main source of large unexpected losses. The “Position size by risk” tool sizes trades from the stop.'))
    tra = []
    for a, b in zip(lenh, lenh[1:]):
        if a['rong'] < 0 and (datetime.fromisoformat(b['mo']) - datetime.fromisoformat(a['dong'])) <= timedelta(minutes=15) and b['lot'] > a['lot'] * 1.2:
            tra.append(b)
    if len(tra) >= 3:
        rong = sum(x['rong'] for x in tra)
        them('xau' if rong < 0 else 'chu_y',
             (f'{len(tra)} lệnh tăng khối lượng ngay sau lệnh thua',
              f'Mở trong 15 phút sau một lệnh thua với khối lượng lớn hơn; tổng các lệnh này {F(rong)}. '
              'Nếu đây không phải kế hoạch có sẵn (như gấp thếp có kiểm soát), hãy đặt giới hạn lỗ trong ngày.'),
             (f'{len(tra)} trades sized up right after a loss',
              f'Opened within 15 minutes of a losing trade with a larger volume; these trades total {E(rong)}. '
              'Unless this is a planned approach (such as a controlled martingale), set a daily loss limit.'))
    if t['chuoi_thua'] >= 5:
        them('chu_y', (f'Chuỗi thua dài nhất: {t["chuoi_thua"]} lệnh',
                       'Chuỗi thua dài là bình thường ngay cả với phương pháp có lãi; khối lượng mỗi lệnh nên đủ nhỏ để chịu được chuỗi gấp đôi như vậy.'),
             (f'Longest losing streak: {t["chuoi_thua"]} trades',
              'Long losing streaks happen even with profitable methods; size each trade small enough to survive a streak twice as long.'))
    if n >= 30 and t['pf'] not in (None, 'inf'):
        if t['pf'] >= 1.3:
            them('tot', (f'Hệ số lợi nhuận {_vn(t["pf"], 2)} trên {n} lệnh', 'Lãi gộp lớn hơn rõ lỗ gộp. Kết quả quá khứ không bảo đảm tương lai; tiếp tục ghi sổ để kiểm.'),
                 (f'Profit factor {t["pf"]:.2f} over {n} trades', 'Gross profit clearly exceeds gross loss. Past results do not guarantee the future; keep logging to verify.'))
        elif t['pf'] < 1:
            them('xau', (f'Hệ số lợi nhuận {_vn(t["pf"], 2)}: đang lỗ', f'Lỗ gộp lớn hơn lãi gộp trên {n} lệnh. Xem các nhóm kéo kết quả xuống ở trên trước khi tăng khối lượng.'),
                 (f'Profit factor {t["pf"]:.2f}: losing', f'Gross loss exceeds gross profit over {n} trades. Review the groups dragging results down above before sizing up.'))
    thu_tu = {'tin': 0, 'xau': 1, 'chu_y': 2, 'tot': 3}                      # lời nhắc "chưa đủ mẫu" đứng đầu để đọc các nhận xét sau với tâm thế đúng
    return sorted(out, key=lambda x: thu_tu[x['muc']])


# --------------------------------------------------------------------------- dữ liệu
def mau(so: int = 260, hat: int = 7, now: datetime | None = None) -> tuple[list[dict], float]:
    """Lệnh MINH HỌA (giả lập, cố định theo hạt giống): vài mã Forex và vàng, có lợi thế nhỏ, vài thói quen xấu để phần nhận xét có việc để nói."""
    rnd = random.Random(hat)
    now = (now or datetime.now(timezone.utc)).replace(second=0, microsecond=0)
    ma = [('EURUSD', 0.0001, 1.09, 10), ('GBPUSD', 0.0001, 1.31, 10), ('USDJPY', 0.01, 159.0, 6.3), ('XAUUSD', 0.1, 3600.0, 10)]
    t = now - timedelta(days=240)
    lenh = []
    for i in range(so):
        t += timedelta(minutes=rnd.randint(40, 1400))
        if t.weekday() >= 5:
            t += timedelta(days=7 - t.weekday())
        if t >= now - timedelta(hours=2):                                    # không sinh lệnh ở tương lai (kiểm sau khi đã dời giờ)
            break
        sym, pip, gia, gt_pip = rnd.choice(ma)
        mua = rnd.random() < 0.55
        lot = rnd.choice([0.05, 0.1, 0.1, 0.2])
        sl_pip = rnd.randint(15, 40)
        a_phien = t.hour < 7                                                  # phiên Á: kém hơn để nhận xét có ví dụ
        p_thang = 0.42 if a_phien else 0.5
        thang = rnd.random() < p_thang
        pip_kq = sl_pip * (rnd.uniform(1.2, 2.2) if thang else -rnd.uniform(0.6, 1.05))
        phut = rnd.uniform(10, 300) if thang else rnd.uniform(20, 700)
        if rnd.random() < 0.1:
            sl_pip_dat = None
        else:
            sl_pip_dat = sl_pip
        rong = pip_kq * gt_pip * lot
        vao = gia * (1 + rnd.uniform(-0.01, 0.01))
        dong = min(t + timedelta(minutes=phut), now - timedelta(minutes=1))
        phut = (dong - t).total_seconds() / 60
        r_tien = sl_pip * gt_pip * lot if sl_pip_dat else None
        lenh.append({'id': 1000 + i, 'ma': sym, 'chieu': 'MUA' if mua else 'BAN', 'lot': lot, 'vao': round(vao, 5),
                     'ra': round(vao + (pip_kq * pip if mua else -pip_kq * pip), 5), 'mo': t.isoformat(), 'dong': dong.isoformat(), 'phut': round(phut, 1),
                     'lai': _r(rong + 0.7 * lot * 10), 'phi': _r(-0.7 * lot * 10), 'swap': _r(-0.3 * lot * 10 if phut > 600 else 0.0),
                     'rong': _r(rong + (-0.3 * lot * 10 if phut > 600 else 0.0)),
                     'sl': (vao - sl_pip * pip if mua else vao + sl_pip * pip) if sl_pip_dat else None, 'tp': None,
                     'r': _r(rong / r_tien, 2) if r_tien else None, 'rui_ro': _r(r_tien), 'nguon': 'Đặt tay' if rnd.random() < 0.6 else 'EA mẫu', 'magic': 0})
        t = dong
    lenh.sort(key=lambda x: x['dong'])
    return lenh, 5000.0


def von_dau(so_du: float, lenh: list[dict], nap: list[dict]) -> float:
    """Số dư ngay trước lệnh đầu tiên trong khoảng: số dư hiện tại trừ lãi ròng của các lệnh và trừ các lần nạp/rút xảy ra SAU lúc mở lệnh đầu tiên
    (nạp/rút trước đó đã là vốn ban đầu)."""
    if not lenh:
        return so_du - sum(x['tien'] or 0 for x in nap)
    dau = min(x['mo'] for x in lenh)
    return so_du - sum(x['rong'] for x in lenh) - sum(x['tien'] or 0 for x in nap if x['t'] > dau)


def doc(cfg: dict, ngay: int = 90, now: datetime | None = None) -> dict:
    """Lệnh đã đóng trong `ngay` ngày gần nhất (0 = mọi lịch sử) từ MT5 đang nối. Không nối được hoặc tài khoản không được phép thì trả lý do."""
    from . import tai_khoan                                                  # noqa: PLC0415
    g = cfg['gia']
    now = now or datetime.now(timezone.utc)
    mt5 = tai_khoan._mt5(g)
    if mt5 is None:
        return {'san_sang': False, 'ly_do': song.ly_do() or 'chưa nối được MT5'}
    chi_demo = (g.get('mt5') or {}).get('chi_demo', True)
    tu = now - timedelta(days=ngay) if ngay else datetime(2000, 1, 1, tzinfo=timezone.utc)
    with song._khoa:
        a = mt5.account_info()
        if a is None:
            return {'san_sang': False, 'ly_do': 'MT5 không trả thông tin tài khoản'}
        demo = int(getattr(a, 'trade_mode', -1)) == int(getattr(mt5, 'ACCOUNT_TRADE_MODE_DEMO', 0))
        if chi_demo and not demo:
            return {'san_sang': False, 'ly_do': 'Tài khoản đang nối không phải demo. Muốn phân tích tài khoản khác thì đặt gia.mt5.chi_demo = false '
                    '(trang vẫn chỉ đọc lịch sử, không đặt lệnh).'}
        deals = list(mt5.history_deals_get(tu, now + timedelta(days=1)) or [])
        orders = list(mt5.history_orders_get(tu, now + timedelta(days=1)) or [])
        so_du = float(a.balance)
        tien = a.currency
        so = str(a.login)
        may_chu = a.server

    def rui_ro(ma, chieu, lot, vao, sl):
        with song._khoa:
            kieu = mt5.ORDER_TYPE_BUY if chieu == 'mua' else mt5.ORDER_TYPE_SELL
            v = mt5.order_calc_profit(kieu, ma, float(lot), float(vao), float(sl))
        return -float(v) if v is not None and v < 0 else None
    lenh, nap = ghep_lenh(deals, orders, lambda m: tai_khoan._ea(cfg, m), rui_ro)
    dau = von_dau(so_du, lenh, nap)
    return {'san_sang': True, 'mau': False, 'tai_khoan': {'so': '•••' + so[-3:], 'may_chu': may_chu, 'demo': demo, 'tien': tien, 'so_du': _r(so_du)},
            'lenh': lenh, 'so_du_dau': dau, 'nap_rut': nap}


def lay(cfg: dict, ngay: int = 90, ma: str = '', chieu: str = '', nguon: str = '', dung_mau: bool = False, now: datetime | None = None) -> dict:
    """Dữ liệu cho trang: đọc MT5 (hoặc dữ liệu minh họa), lọc, rồi phân tích. Nhớ 20 giây theo khoảng thời gian."""
    import time                                                              # noqa: PLC0415
    k = ('mau' if dung_mau else 'mt5', ngay)
    cu = _nho.get(k)
    if cu and time.monotonic() - cu[0] < 20:
        goc = cu[1]
    else:
        if dung_mau:
            ds, dau = mau(now=now)
            if ngay:
                moc = (datetime.fromisoformat(ds[-1]['dong']) - timedelta(days=ngay)).isoformat()
                truoc = [x for x in ds if x['dong'] < moc]
                ds = [x for x in ds if x['dong'] >= moc]
                dau += sum(x['rong'] for x in truoc)
            goc = {'san_sang': True, 'mau': True, 'tai_khoan': {'so': 'MINH HỌA', 'may_chu': '', 'demo': True, 'tien': 'USD', 'so_du': None},
                   'lenh': ds, 'so_du_dau': dau, 'nap_rut': []}
        else:
            goc = doc(cfg, ngay, now)
        if goc.get('san_sang'):
            _nho[k] = (time.monotonic(), goc)
    if not goc.get('san_sang'):
        return goc
    tat_ca = goc['lenh']
    ds = [x for x in tat_ca if (not ma or x['ma'] == ma) and (not chieu or x['chieu'] == chieu)
          and (not nguon or nguon in (x['nguon'], NHOM_EN.get(x['nguon'])))]                  # trang tiếng Anh gửi tên nguồn đã dịch ("Manual")
    kq = phan_tich(ds, goc['so_du_dau'], goc['tai_khoan']['tien'])
    return {**{k: v for k, v in goc.items() if k != 'lenh'}, **kq, 'lenh': ds[::-1], 'ngay_xem': ngay,
            'loc': {'ma': sorted({x['ma'] for x in tat_ca}), 'nguon': sorted({x['nguon'] for x in tat_ca})}}


def csv_lenh(lenh: list[dict]) -> str:
    """Danh sách lệnh dạng CSV (UTF-8 có BOM để Excel đọc đúng tiếng Việt)."""
    f = io.StringIO()
    w = csv.writer(f)
    cot = ['id', 'ma', 'chieu', 'lot', 'vao', 'ra', 'mo', 'dong', 'phut', 'lai', 'phi', 'swap', 'rong', 'sl', 'tp', 'r', 'nguon']
    w.writerow(cot)
    for x in lenh:
        w.writerow([x.get(c) for c in cot])
    return '﻿' + f.getvalue()
