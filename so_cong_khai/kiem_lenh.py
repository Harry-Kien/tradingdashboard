"""Kiểm tra trước khi vào lệnh: chấm một lệnh dự định theo các quy tắc quản lý rủi ro, bằng dữ liệu thật từ MT5 của người dùng. CHỈ ĐỌC.

Không đoán giá đi đâu và không hứa lợi nhuận. Trang chỉ trả lời: lệnh này có phạm những lỗi làm mất tiền hay gặp không
(không dừng lỗ, rủi ro quá lớn, dừng lỗ quá sát so với biến động, spread đang giãn, sắp có tin mạnh, đã chạm giới hạn lỗ ngày,
vào gấp ngay sau lệnh thua, dồn rủi ro vào các mã đi cùng chiều, đi ngược xu hướng khung lớn).

`cham(lenh, du_lieu, quy_tac)` là hàm thuần (không gọi MT5) nên kiểm thử được; `thu_thap(...)` gom dữ liệu thật rồi gọi nó."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

QUY_TAC_MAC_DINH = {
    'rui_ro_lenh_pct': 1.0,          # rủi ro gợi ý mỗi lệnh (% vốn)
    'rui_ro_lenh_toi_da_pct': 2.0,   # trên mức này: cân nhắc; trên gấp 2,5 lần: không nên
    'lo_ngay_toi_da_pct': 3.0,       # lỗ đã chốt trong ngày (giờ Việt Nam) chạm mức này: dừng giao dịch hôm nay
    'tong_rui_ro_toi_da_pct': 6.0,   # tổng rủi ro mọi lệnh đang mở + lệnh này
    'rr_toi_thieu': 1.0,             # lời/lỗ dưới mức này cần tỷ lệ thắng rất cao
    'sl_atr_toi_thieu': 0.5,         # dừng lỗ ngắn hơn 0,5 ATR M15: dễ bị nhiễu quét
    'spread_gian_lan': 2.0,          # spread hiện tại so với spread thường (trung vị)
    'spread_tren_sl_pct': 20.0,      # spread ăn quá 20% khoảng dừng lỗ
    'tin_truoc_phut': 30,            # tin mạnh trong 30 phút tới
    'tin_sau_phut': 15,              # hoặc vừa ra trong 15 phút
    'gap_sau_thua_phut': 15,         # vào lệnh trong 15 phút sau một lệnh thua
    'tuong_quan_cao': 0.7,           # |tương quan| từ mức này coi là cùng một cược
}
THU_TU = {'xau': 0, 'chu_y': 1, 'tot': 2, 'tin': 3}


def _so(x: float, d: int = 2, en: bool = False) -> str:
    s = f'{x:,.{d}f}'
    return s if en else s.replace(',', '§').replace('.', ',').replace('§', '.')


def cham(lenh: dict, du: dict, quy_tac: dict | None = None) -> dict:
    """lenh: {ma, chieu 'MUA'|'BAN', vao, sl, tp?, rui_ro_pct?}.
    du (dữ liệu đã thu thập, khóa nào thiếu thì bỏ qua mục đó):
      von, tien, gia_tri_1_gia_1_lot (tiền lời/lỗ khi giá đi 1,0 với 1 lot), lot_min, lot_buoc, lot_max,
      bid, ask, spread_thuong, atr_m15, tin [{t, tien, ten}], tien_lien_quan [mã tiền], now,
      lo_hom_nay (lãi lỗ đã chốt hôm nay, âm là lỗ), thua_gan_nhat {dong, lot} | None,
      rui_ro_dang_mo (tiền mất nếu mọi dừng lỗ đang mở bị chạm), vi_the [{ma, chieu}], tuong_quan {ma: hệ số với mã này},
      ky_thuat {H1: điểm -1..1, H4: ...}.
    Trả về: khối lượng gợi ý, tiền rủi ro, R:R, tỷ lệ thắng hòa vốn, danh sách mục kiểm và kết luận.
    Mỗi mục có sẵn hai ngôn ngữ {'vi': {tieu, noi}, 'en': {tieu, noi}} (tên tin, tiền tệ, mã chen vào câu nên không dịch theo từ điển được)."""
    q = {**QUY_TAC_MAC_DINH, **(quy_tac or {})}
    muc: list[dict] = []

    def them(k, m, vi, en):
        muc.append({'k': k, 'muc': m, 'vi': {'tieu': vi[0], 'noi': vi[1] if len(vi) > 1 else ''},
                    'en': {'tieu': en[0], 'noi': en[1] if len(en) > 1 else ''}})

    def V(x, d=2):
        return _so(x, d)

    def E(x, d=2):
        return _so(x, d, True)

    mua = lenh['chieu'] == 'MUA'
    cv, ce = ('MUA', 'BUY') if mua else ('BÁN', 'SELL')
    vao, sl, tp = float(lenh['vao']), lenh.get('sl'), lenh.get('tp')
    rr_pct = float(lenh.get('rui_ro_pct') or q['rui_ro_lenh_pct'])
    von, tien = du.get('von'), du.get('tien', 'USD')
    kq = {'ma': lenh['ma'], 'chieu': lenh['chieu'], 'vao': vao, 'sl': sl, 'tp': tp, 'rui_ro_pct': rr_pct, 'tien': tien}

    # 1. dừng lỗ
    if sl in (None, '', 0):
        them('sl', 'xau', ('Lệnh không có dừng lỗ', 'Không có dừng lỗ thì rủi ro không giới hạn: một lệnh có thể xóa nhiều tuần lãi. Đặt dừng lỗ trước khi tính khối lượng.'),
             ('No stop loss', 'Without a stop loss the risk is unlimited: one trade can wipe out weeks of profit. Set a stop loss before sizing the trade.'))
        return _ket(kq, muc)
    sl = float(sl)
    kc = (vao - sl) if mua else (sl - vao)
    if kc <= 0:
        them('sl', 'xau', ('Dừng lỗ nằm sai phía', f'Lệnh {cv} cần dừng lỗ {"dưới" if mua else "trên"} giá vào.'),
             ('Stop loss on the wrong side', f'A {ce} trade needs its stop loss {"below" if mua else "above"} the entry price.'))
        return _ket(kq, muc)
    kq['kc_sl'] = kc

    # 2. khối lượng theo % rủi ro
    gt = du.get('gia_tri_1_gia_1_lot')
    if von and gt:
        tien_rr = von * rr_pct / 100
        lot = tien_rr / (kc * gt)
        buoc, lmin, lmax = du.get('lot_buoc') or 0.01, du.get('lot_min') or 0.01, du.get('lot_max') or 100.0
        lot_lam_tron = min(max(0.0, (int(lot / buoc + 1e-9)) * buoc), lmax)   # chặn ở lot tối đa của sàn; tiền rủi ro tính theo đúng lot này
        kq.update(lot_tinh=round(lot, 4), lot=round(lot_lam_tron, 4), rui_ro_tien=round(kc * gt * lot_lam_tron, 2), rui_ro_muc_tieu=round(tien_rr, 2))
        if lot_lam_tron < lmin:
            that = kc * gt * lmin
            kq.update(lot=lmin, rui_ro_tien=round(that, 2), duoi_lot_min=True)   # số thật nếu vẫn vào ở mức tối thiểu của sàn
            them('lot', 'xau',
                 ('Dừng lỗ quá xa so với vốn', f'Với {V(rr_pct, 1)}% rủi ro ({V(tien_rr)} {tien}) khối lượng chỉ {V(lot, 3)} lot, nhỏ hơn mức tối thiểu {V(lmin)} lot '
                  f'của sàn. Vào {V(lmin)} lot thì rủi ro thật là {V(that)} {tien} ({V(that / von * 100, 1)}% vốn).'),
                 ('Stop too far for this balance', f'At {E(rr_pct, 1)}% risk ({E(tien_rr)} {tien}) the size is only {E(lot, 3)} lots, below the broker minimum of '
                  f'{E(lmin)} lots. At {E(lmin)} lots the real risk is {E(that)} {tien} ({E(that / von * 100, 1)}% of equity).'))
        else:
            r = kq['rui_ro_tien']
            them('lot', 'tin', (f'Khối lượng gợi ý: {V(kq["lot"])} lot', f'Mất {V(r)} {tien} ({V(r / von * 100)}% vốn) nếu chạm dừng lỗ.'),
                 (f'Suggested size: {E(kq["lot"])} lots', f'You lose {E(r)} {tien} ({E(r / von * 100)}% of equity) if the stop is hit.'))
    # 3. rủi ro mỗi lệnh
    mat5 = 100 - 100 * (1 - min(rr_pct, 100) / 100) ** 5
    if rr_pct > q['rui_ro_lenh_toi_da_pct'] * 2.5:
        them('rui_ro', 'xau', (f'Rủi ro {V(rr_pct, 1)}% vốn cho một lệnh là quá lớn',
                               f'Thua 5 lệnh liền (chuyện bình thường) là mất khoảng {V(mat5, 0)}% vốn. Mức thường dùng là 0,5–2%.'),
             (f'{E(rr_pct, 1)}% of equity on one trade is too much', f'Five losses in a row (normal) would cost about {E(mat5, 0)}% of equity. Common practice is 0.5–2%.'))
    elif rr_pct > q['rui_ro_lenh_toi_da_pct']:
        them('rui_ro', 'chu_y', (f'Rủi ro {V(rr_pct, 1)}% vốn cao hơn mức bạn đặt ({V(q["rui_ro_lenh_toi_da_pct"], 1)}%)',
                                 f'Thua 5 lệnh liền là mất khoảng {V(mat5, 0)}% vốn.'),
             (f'{E(rr_pct, 1)}% risk is above your limit ({E(q["rui_ro_lenh_toi_da_pct"], 1)}%)', f'Five losses in a row would cost about {E(mat5, 0)}% of equity.'))
    else:
        them('rui_ro', 'tot', (f'Rủi ro {V(rr_pct, 1)}% vốn mỗi lệnh', 'Nằm trong mức bạn đặt.'), (f'{E(rr_pct, 1)}% of equity at risk', 'Within your limit.'))

    # 4. lời/lỗ
    if tp not in (None, '', 0):
        tp = float(tp)
        lai = (tp - vao) if mua else (vao - tp)
        if lai <= 0:
            them('rr', 'xau', ('Chốt lời nằm sai phía', f'Lệnh {cv} cần chốt lời {"trên" if mua else "dưới"} giá vào.'),
                 ('Take profit on the wrong side', f'A {ce} trade needs its take profit {"above" if mua else "below"} the entry price.'))
        else:
            r = lai / kc
            hv = 100 / (1 + r)
            kq.update(rr=round(r, 2), hoa_von_pct=round(hv, 1))
            if r < q['rr_toi_thieu']:
                them('rr', 'chu_y', (f'Lời/lỗ 1:{V(r)}, cần thắng trên {V(hv, 0)}% số lệnh mới hòa vốn',
                                     'Chốt lời gần hơn dừng lỗ thì phải thắng rất thường xuyên; một lệnh thua ăn mất nhiều lệnh thắng.'),
                     (f'Reward/risk 1:{E(r)}, you need over {E(hv, 0)}% winners to break even',
                      'A target closer than the stop means you must win very often; one loss eats several wins.'))
            else:
                them('rr', 'tot', (f'Lời/lỗ 1:{V(r)}', f'Cần thắng trên {V(hv, 0)}% số lệnh để hòa vốn (chưa tính phí).'),
                     (f'Reward/risk 1:{E(r)}', f'You need over {E(hv, 0)}% winners to break even (before costs).'))
    else:
        them('rr', 'chu_y', ('Chưa có mức chốt lời', 'Không tính được lời/lỗ và tỷ lệ thắng cần có. Đặt mức chốt lời hoặc quy tắc thoát lệnh trước khi vào.'),
             ('No take profit yet', 'Reward/risk and the win rate you need cannot be calculated. Set a target or an exit rule before entering.'))

    # 5. dừng lỗ so với biến động
    atr = du.get('atr_m15')
    if atr:
        k = kc / atr
        kq['sl_atr'] = round(k, 2)
        if k < q['sl_atr_toi_thieu']:
            them('atr', 'chu_y', (f'Dừng lỗ chỉ {V(k)} lần ATR M15', 'Ngắn hơn một nhịp dao động bình thường của 15 phút: dễ bị quét rồi giá mới chạy đúng hướng.'),
                 (f'Stop is only {E(k)}× the M15 ATR', 'Shorter than a normal 15-minute swing: easy to get stopped out before price moves your way.'))
        else:
            them('atr', 'tot', (f'Dừng lỗ {V(k)} lần ATR M15', 'Rộng hơn nhiễu thông thường của khung 15 phút.'),
                 (f'Stop is {E(k)}× the M15 ATR', 'Wider than normal 15-minute noise.'))

    # 6. spread
    bid, ask = du.get('bid'), du.get('ask')
    if bid and ask:
        sp = ask - bid
        thuong = du.get('spread_thuong')
        ty = sp / kc * 100
        if thuong and sp > thuong * q['spread_gian_lan']:
            them('spread', 'chu_y', (f'Spread đang giãn gấp {V(sp / thuong, 1)} lần bình thường',
                                     'Thường gặp quanh tin, đầu phiên Á hoặc lúc thanh khoản mỏng. Chờ spread về bình thường sẽ rẻ hơn.'),
                 (f'Spread is {E(sp / thuong, 1)}× wider than normal', 'Common around news, the Asian open or thin liquidity. Waiting for a normal spread is cheaper.'))
        elif ty > q['spread_tren_sl_pct']:
            them('spread', 'chu_y', (f'Spread ăn {V(ty, 0)}% khoảng dừng lỗ', 'Phí vào lệnh lớn so với dừng lỗ: kết quả dài hạn bị kéo xuống rõ.'),
                 (f'Spread eats {E(ty, 0)}% of the stop distance', 'Entry cost is large relative to the stop: long-run results are dragged down noticeably.'))
        else:
            them('spread', 'tot', (f'Spread {V(ty, 1)}% khoảng dừng lỗ', 'Chi phí vào lệnh hợp lý.'),
                 (f'Spread is {E(ty, 1)}% of the stop distance', 'Reasonable entry cost.'))

    # 7. tin mạnh
    now = du.get('now') or datetime.now(timezone.utc)
    lien = set(du.get('tien_lien_quan') or [])
    if du.get('tin') is not None:
        gan = []
        for e in du['tin']:
            t = e['t'] if isinstance(e['t'], datetime) else datetime.fromisoformat(e['t'])
            if lien and e.get('tien') not in lien:
                continue
            if -timedelta(minutes=q['tin_sau_phut']) <= t - now <= timedelta(minutes=q['tin_truoc_phut']):
                gan.append((t, e))
        if gan:
            t, e = min(gan, key=lambda x: abs((x[0] - now).total_seconds()))
            phut = round((t - now).total_seconds() / 60)
            kv = f'sau {phut} phút nữa' if phut > 0 else ('đang ra' if phut == 0 else f'vừa ra {-phut} phút trước')
            ke = f'in {phut} min' if phut > 0 else ('out now' if phut == 0 else f'released {-phut} min ago')
            ten, tt = e.get('ten', ''), e.get('tien', '')
            them('tin', 'xau', (f'Tin mạnh {tt} {kv}: {ten}', 'Quanh tin mạnh giá có thể giật qua dừng lỗ và spread giãn; chiều giá sau tin không đoán trước được. Chờ tin ra xong.'),
                 (f'High-impact {tt} news {ke}: {ten}', 'Around major news price can jump through stops and spreads widen; direction after the news cannot be predicted. Wait until it is out.'))
        else:
            them('tin', 'tot', (f'Không có tin mạnh trong {q["tin_truoc_phut"]} phút tới', 'Theo lịch kinh tế của các đồng tiền liên quan.'),
                 (f'No high-impact news in the next {q["tin_truoc_phut"]} minutes', 'Per the economic calendar of the related currencies.'))

    # 8. lỗ trong ngày
    if von and du.get('lo_hom_nay') is not None:
        lo = du['lo_hom_nay']
        pct = -lo / von * 100 if lo < 0 else 0.0
        gh = q['lo_ngay_toi_da_pct']
        if pct >= gh:
            them('ngay', 'xau', (f'Hôm nay đã lỗ {V(pct, 1)}% vốn, chạm giới hạn {V(gh, 1)}%', 'Dừng giao dịch tới hết ngày. Vào thêm lệnh lúc đang lỗ là lúc dễ phá kỷ luật nhất.'),
                 (f'Down {E(pct, 1)}% today, daily limit of {E(gh, 1)}% reached', 'Stop trading for the rest of the day. Adding trades while down is when discipline breaks most easily.'))
        elif lo < 0:
            them('ngay', 'tot', (f'Hôm nay đang lỗ {V(pct, 1)}% vốn', f'Còn cách giới hạn ngày {V(gh - pct, 1)}% vốn.'),
                 (f'Down {E(pct, 1)}% today', f'{E(gh - pct, 1)}% of equity left before the daily limit.'))
        else:
            them('ngay', 'tot', ('Chưa chạm giới hạn lỗ ngày',), ('Daily loss limit not reached',))

    # 9. vào gấp sau lệnh thua
    tg = du.get('thua_gan_nhat')
    if tg:
        dong = tg['dong'] if isinstance(tg['dong'], datetime) else datetime.fromisoformat(tg['dong'])
        phut = (now - dong).total_seconds() / 60
        if 0 <= phut <= q['gap_sau_thua_phut']:
            them('gap', 'chu_y', (f'Lệnh thua vừa đóng {V(phut, 0)} phút trước',
                                  'Vào lệnh ngay sau khi thua (nhất là với khối lượng lớn hơn) là thói quen "gỡ" hay làm thua nặng. Nghỉ vài phút rồi kiểm lại.'),
                 (f'A losing trade closed {E(phut, 0)} min ago',
                  'Jumping back in right after a loss (especially with a bigger size) is the "revenge trading" habit behind many big losses. Take a few minutes, then check again.'))

    # 10. tổng rủi ro đang mở
    if von and du.get('rui_ro_dang_mo') is not None and kq.get('rui_ro_tien') is not None:
        tong = du['rui_ro_dang_mo'] + kq['rui_ro_tien']
        pct = tong / von * 100
        kq['tong_rui_ro_pct'] = round(pct, 2)
        gh = q['tong_rui_ro_toi_da_pct']
        if pct > gh:
            them('tong', 'xau', (f'Tổng rủi ro sẽ là {V(pct, 1)}% vốn', f'Cả lệnh đang mở và lệnh này cùng chạm dừng lỗ thì mất {V(tong)} {tien}, quá mức {V(gh, 1)}% bạn đặt.'),
                 (f'Total risk would be {E(pct, 1)}% of equity', f'If all open trades and this one hit their stops you lose {E(tong)} {tien}, above your {E(gh, 1)}% limit.'))
        elif du.get('mo_chua_tinh'):
            n = du['mo_chua_tinh']
            them('tong', 'chu_y', (f'Tổng rủi ro sau lệnh này: ít nhất {V(pct, 1)}% vốn',
                                   f'{n} lệnh đang mở không có dừng lỗ (hoặc tính bằng đồng tiền khác) chưa cộng vào tổng: rủi ro thật cao hơn con số này.'),
                 (f'Total risk after this trade: at least {E(pct, 1)}% of equity',
                  f'{n} open trade(s) without a stop loss (or in another currency) are not included: the real risk is higher than this.'))
        else:
            them('tong', 'tot', (f'Tổng rủi ro sau lệnh này: {V(pct, 1)}% vốn',), (f'Total risk after this trade: {E(pct, 1)}% of equity',))

    # 11. dồn cược vào mã tương quan
    tq, cung = du.get('tuong_quan') or {}, []
    for v in du.get('vi_the') or []:
        h = 1.0 if v['ma'] == lenh['ma'] else tq.get(v['ma'])
        if h is None or abs(h) < q['tuong_quan_cao']:
            continue
        if (v['chieu'] == lenh['chieu']) == (h > 0):
            cung.append(v['ma'])
    if cung:
        ds = ', '.join(sorted(set(cung)))
        them('tq', 'chu_y', (f'Đã có lệnh đi cùng một cược: {ds}',
                             'Các mã này thường chạy cùng nhau, nên nhiều lệnh cùng chiều giống một lệnh lớn: rủi ro thật cao hơn từng lệnh cộng lại trông có vẻ.'),
             (f'Already holding the same bet: {ds}', 'These symbols usually move together, so several same-direction trades act like one big trade: the real risk is higher than it looks.'))

    # 12. xu hướng khung lớn
    kt = du.get('ky_thuat') or {}
    nguoc = [k for k in ('H1', 'H4') if kt.get(k) is not None and ((kt[k] < -0.5) if mua else (kt[k] > 0.5))]
    if len(nguoc) == 2:
        them('kt', 'chu_y', ('Đi ngược tín hiệu kỹ thuật mạnh ở H1 và H4',
                             'Đồng thuận chỉ báo ở cả hai khung đang nghiêng mạnh về chiều ngược lại. Không phải lý do cấm, nhưng nên có lý do rõ ràng.'),
             ('Against strong technical signals on H1 and H4', 'Indicator consensus on both timeframes leans strongly the other way. Not a ban, but have a clear reason.'))
    elif kt:
        them('kt', 'tin', ('Không đi ngược tín hiệu kỹ thuật mạnh ở khung lớn', 'Tín hiệu kỹ thuật mô tả hiện trạng, không dự báo giá.'),
             ('Not against strong higher-timeframe signals', 'Technical signals describe the current state; they do not forecast price.'))
    # 13. lịch sử của chính người dùng với kiểu lệnh này
    m = cham_lich_su(du.get('lich_su'), lenh['ma'], lenh['chieu'], now, du.get('tien', 'USD'))
    if m:
        muc.append(m)
    return _ket(kq, muc)


DU_MAU = 10                          # nhóm ít lệnh hơn thì không kết luận
NGAY_LICH_SU = 180


def _phien(t: datetime) -> str:
    from .hieu_suat import PHIEN                                             # noqa: PLC0415
    h = t.astimezone(timezone.utc).hour
    return next(p for p, a, b in PHIEN if a <= h < b)


def cham_lich_su(ls: list[dict] | None, ma: str, chieu: str, now: datetime, tien: str = 'USD') -> dict | None:
    """So lệnh định vào với lệnh ĐÃ ĐÓNG của chính người dùng (hieu_suat: mỗi lệnh {ma, chieu, mo, rong, r}): chọn nhóm cụ thể nhất có từ DU_MAU
    lệnh trở lên — cùng mã + chiều + phiên lúc này, rồi cùng mã + chiều, rồi cùng mã — và cho biết nhóm đó đang thắng hay thua.
    Kỳ vọng âm (lãi ròng trung bình mỗi lệnh < 0): 'chu_y'; dương: 'tot'; chưa đủ lệnh: 'tin'. None nếu không có dữ liệu lịch sử."""
    from .hieu_suat import NHOM_EN                                           # noqa: PLC0415
    if ls is None:
        return None
    ph = _phien(now)
    cv, ce = ('MUA', 'BUY') if chieu == 'MUA' else ('BÁN', 'SELL')
    nhom = [
        ([x for x in ls if x['ma'] == ma and x['chieu'] == chieu and _phien(datetime.fromisoformat(x['mo'])) == ph],
         f'lệnh {cv} {ma} vào phiên {ph}', f'{ce} {ma} trades in the {NHOM_EN.get(ph, ph)} session'),
        ([x for x in ls if x['ma'] == ma and x['chieu'] == chieu], f'lệnh {cv} {ma}', f'{ce} {ma} trades'),
        ([x for x in ls if x['ma'] == ma], f'lệnh {ma}', f'{ma} trades'),
    ]
    chon = next((g for g in nhom if len(g[0]) >= DU_MAU), None)
    if chon is None:
        n = len(nhom[1][0])
        return {'k': 'lich_su', 'muc': 'tin',
                'vi': {'tieu': f'Chưa đủ lịch sử để so: {n} {nhom[1][1]} trong {NGAY_LICH_SU} ngày',
                       'noi': f'Cần từ {DU_MAU} lệnh đã đóng trở lên mới đánh giá được kiểu lệnh này của bạn đang thắng hay thua.'},
                'en': {'tieu': f'Not enough history to compare: {n} {nhom[1][2]} in {NGAY_LICH_SU} days',
                       'noi': f'At least {DU_MAU} closed trades are needed to tell whether this kind of trade is working for you.'}}
    g, ten_vi, ten_en = chon
    n = len(g)
    thang = sum(1 for x in g if (x.get('rong') or 0) > 0)
    tong = sum(x.get('rong') or 0 for x in g)
    rs = [x['r'] for x in g if x.get('r') is not None]
    r_tb = sum(rs) / len(rs) if rs else None
    tl = thang / n * 100
    V, E = (lambda x, d=2: _so(x, d)), (lambda x, d=2: _so(x, d, True))
    dau = lambda x, f: ('+' if x > 0 else '') + f(x)                         # noqa: E731
    r_vi = f', trung bình {dau(r_tb, lambda v: V(v))}R mỗi lệnh' if r_tb is not None else ''
    r_en = f', {dau(r_tb, lambda v: E(v))}R per trade on average' if r_tb is not None else ''
    so_vi = f'{n} {ten_vi} của bạn trong {NGAY_LICH_SU} ngày: thắng {V(tl, 0)}%, tổng {dau(tong, V)} {tien}{r_vi}.'
    so_en = f'Your {n} {ten_en} in the last {NGAY_LICH_SU} days: {E(tl, 0)}% winners, total {dau(tong, E)} {tien}{r_en}.'
    if chon is nhom[2]:
        # chưa đủ lệnh cùng chiều: chỉ cho xem kết quả chung của mã, không kết luận về chiều này (có thể toàn lệnh chiều ngược lại)
        n1 = len(nhom[1][0])
        return {'k': 'lich_su', 'muc': 'tin',
                'vi': {'tieu': f'Chưa có đủ {nhom[1][1]} để so ({n1} lệnh)', 'noi': f'Kết quả chung với mã này: {so_vi}'},
                'en': {'tieu': f'Not enough {nhom[1][2]} to compare ({n1})', 'noi': f'Overall with this symbol: {so_en}'}}
    if tong < 0:
        return {'k': 'lich_su', 'muc': 'chu_y',
                'vi': {'tieu': f'Kiểu lệnh này đang làm bạn lỗ: {so_vi}',
                       'noi': 'Bỏ bớt kiểu lệnh đang thua là cách thực tế nhất để nâng tỷ lệ thắng. Xem lại lý do vào, hoặc chờ điều kiện bạn hay thắng hơn.'},
                'en': {'tieu': f'This kind of trade is losing you money: {so_en}',
                       'noi': 'Cutting the kind of trades that lose is the most practical way to raise your win rate. Review your entry reason or wait for conditions that work better for you.'}}
    tot_nhat = max((x.get('rong') or 0) for x in g)
    if tong <= 0 or tong - tot_nhat <= 0:
        # hòa vốn, hoặc lãi chỉ nhờ một lệnh thắng lớn (bỏ lệnh đó thì không còn lãi): chưa đủ cơ sở để nói kiểu lệnh này tốt
        return {'k': 'lich_su', 'muc': 'tin',
                'vi': {'tieu': f'Kiểu lệnh này chưa cho thấy lợi thế rõ: {so_vi}',
                       'noi': 'Lãi lỗ quanh mức hòa vốn, hoặc chỉ nhờ một lệnh thắng lớn. Cần thêm lệnh mới biết kiểu lệnh này có hợp với bạn không.'},
                'en': {'tieu': f'No clear edge in this kind of trade yet: {so_en}',
                       'noi': 'Results are near breakeven or rely on one big winner. More trades are needed to tell whether this kind of trade suits you.'}}
    return {'k': 'lich_su', 'muc': 'tot',
            'vi': {'tieu': f'Kiểu lệnh bạn đang làm tốt: {so_vi}', 'noi': 'Kết quả quá khứ không bảo đảm lệnh này thắng; vẫn giữ đúng mức rủi ro.'},
            'en': {'tieu': f'A kind of trade that works for you: {so_en}', 'noi': 'Past results do not guarantee this trade wins; keep your risk level.'}}


def _ket(kq: dict, muc: list[dict]) -> dict:
    muc.sort(key=lambda m: THU_TU[m['muc']])
    co = {m['muc'] for m in muc}
    if 'xau' in co:
        kl, vi, en = 'khong_nen', 'Lệnh này phạm quy tắc quản lý rủi ro bạn đặt (xem mục đỏ bên dưới).', 'This trade breaks your risk rules (see the red items below).'
    elif 'chu_y' in co:
        kl, vi, en = 'can_nhac', 'Có điểm cần xem lại trước khi vào (mục vàng bên dưới).', 'Some points need a second look before entering (yellow items below).'
    else:
        kl, vi, en = 'dat', 'Đạt các quy tắc quản lý rủi ro. Kết quả lệnh vẫn có thể thắng hoặc thua.', 'Passes your risk rules. The trade can still win or lose.'
    return {**kq, 'muc': muc, 'ket_luan': kl, 'ket_luan_chu': {'vi': vi, 'en': en}}


def _tien_lien_quan(dt: dict, ma: str) -> list[str]:
    """Các đồng tiền mà tin của chúng làm mã này chạy: hai đồng của cặp tiền; với vàng, chỉ số, dầu… là đồng tiền định giá (thường USD)."""
    cap = dt.get('cap')
    if cap:
        return [c for c in cap if c]
    return [c for c in {dt.get('tien_goc'), dt.get('tien_lai')} if c and len(c) == 3 and c.isalpha() and c.isupper()] or ['USD']


def thu_thap(cfg: dict, bang, lenh: dict, now: datetime | None = None) -> dict:
    """Gom dữ liệu thật cho `cham`: tài khoản, lệnh đang mở và lãi lỗ hôm nay (tai_khoan.doc, chỉ đọc), giá, spread, ATR, tín hiệu kỹ thuật
    và tương quan (bảng giá), tin mạnh (lịch). Thiếu phần nào thì bỏ qua mục tương ứng. Trả {'du': ..., 'thieu': [lý do]}."""
    from . import tai_khoan, thi_truong                                       # noqa: PLC0415
    from .__main__ import HERE                                               # noqa: PLC0415
    from .doc_so import VN                                                   # noqa: PLC0415
    now = now or datetime.now(timezone.utc)
    ma = lenh['ma']
    du: dict = {'now': now}
    thieu: list[str] = []
    if bang is not None:
        with bang._dk:
            dt = dict(bang.dac_ta.get(ma) or {})
            g = list(bang.gia.get(ma) or [])
            kt = {tf: dict(v) for tf, v in ((bang.kt or {}).get(ma) or {}).items()}
            tq = bang.tuong_quan if isinstance(getattr(bang, 'tuong_quan', None), dict) else None
        if not dt:
            raise ValueError(f'không có mã {ma} trong bảng giá')
        du.update(gia_tri_1_gia_1_lot=dt.get('gt1'), lot_min=dt.get('lot_min'), lot_buoc=dt.get('lot_buoc'), lot_max=dt.get('lot_max'),
                  so_le=dt.get('so_le'), tien_lien_quan=_tien_lien_quan(dt, ma))
        if len(g) >= 2 and g[0] and g[1]:
            du.update(bid=g[0], ask=g[1])
        else:
            thieu.append('chưa có giá trực tiếp của mã này')
        if kt.get('M15', {}).get('atr'):
            du['atr_m15'] = kt['M15']['atr']
        du['ky_thuat'] = {tf: kt[tf]['d'] for tf in ('H1', 'H4') if kt.get(tf, {}).get('d') is not None}
        if tq and tq.get('ma') and ma in tq['ma']:
            i = tq['ma'].index(ma)
            du['tuong_quan'] = {m: tq['ma_tran'][i][j] for j, m in enumerate(tq['ma']) if j != i and tq['ma_tran'][i][j] is not None}
    else:
        thieu.append('bảng giá chưa chạy')
    try:
        tk = tai_khoan.doc(cfg, now=now, ngay=2)
    except Exception as e:                                                   # noqa: BLE001
        tk = {'san_sang': False, 'ly_do': str(e)}
    if tk.get('san_sang'):
        hom_nay = now.astimezone(VN).date().isoformat()
        rr_mo = tk.get('rui_ro') or {}
        du.update(von=tk.get('von'), tien=tk.get('tien', 'USD'), rui_ro_dang_mo=rr_mo.get('tong', 0.0),
                  mo_chua_tinh=int(rr_mo.get('khong_sl') or 0) + int(rr_mo.get('khong_tinh') or 0),
                  vi_the=[{'ma': x['ma'], 'chieu': x['huong']} for x in tk.get('lenh', [])],
                  lo_hom_nay=next((x['lai'] for x in tk.get('theo_ngay', []) if x['ngay'] == hom_nay), 0.0))
        dd = tk.get('da_dong') or []
        if dd and (dd[0].get('lai') or 0) < 0:
            du['thua_gan_nhat'] = {'dong': dd[0]['luc'], 'lot': dd[0].get('lot')}
    else:
        thieu.append('chưa đọc được tài khoản: ' + str(tk.get('ly_do') or ''))
    try:                                                                     # lệnh đã đóng của chính người dùng (trang Hiệu suất nhớ 20 giây)
        from . import hieu_suat                                              # noqa: PLC0415
        hs = hieu_suat.lay(cfg, NGAY_LICH_SU, now=now)
        if hs.get('san_sang'):
            du['lich_su'] = hs.get('lenh') or []
    except Exception:                                                        # noqa: BLE001 - thiếu lịch sử thì bỏ mục này
        pass
    try:
        lich = thi_truong.lich_tong(cfg, HERE, now)
        du['tin'] = [e for e in lich.get('ds', []) if e.get('muc') == 3]
    except Exception as e:                                                   # noqa: BLE001
        thieu.append(f'chưa đọc được lịch tin: {e}')
    return {'du': du, 'thieu': thieu}


def kiem(cfg: dict, bang, lenh: dict, now: datetime | None = None) -> dict:
    """Thu thập rồi chấm. Quy tắc người dùng đặt ở cfg['kiem_lenh'] (ghi đè QUY_TAC_MAC_DINH)."""
    tt = thu_thap(cfg, bang, lenh, now)
    kq = cham(lenh, tt['du'], cfg.get('kiem_lenh'))
    kq['thieu'] = tt['thieu']
    du = tt['du']
    kq['gia'] = {'bid': du.get('bid'), 'ask': du.get('ask'), 'so_le': du.get('so_le')}
    kq['quy_tac'] = {**QUY_TAC_MAC_DINH, **(cfg.get('kiem_lenh') or {})}
    return kq
