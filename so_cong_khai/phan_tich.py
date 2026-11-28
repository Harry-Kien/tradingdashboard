"""Phân tích điểm vào, SL, TP khi người dùng bấm "Phân tích" trên biểu đồ.

Không có công thức mới nào ở đây: mỗi phương án gọi thẳng hàm trong mã của chủ dự án và trả đúng mức giá mà luật đó sẽ dùng
nếu ra lệnh lúc này:
  - luật bot (nến tín hiệu):   tinhieu.rules.evaluate  + tinhieu.levels.build
  - luật bot (theo xu hướng):  tinhieu.rules.on_demand + tinhieu.levels.build   (như lệnh `python -m tinhieu now`)
  - luật xu hướng ba khung:    ai.rule_trend.decide    + ai.rule_trend.levels
  - luật đỉnh/đáy 8 giờ:       ai.rule_fade.decide
Kèm theo là bối cảnh (xu hướng, vùng giá gần nhất, tin sắp tới) và số đo của chính từng luật. Chỉ đọc giá, không đặt lệnh.
Đây là kết quả của các luật, không phải lời khuyên đầu tư."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from . import ai_timeframes, chat_luong_call, gia, giu_lenh, harrison, phieu, phuong_phap, song, tin_hieu_ngan

THONG_KE = {
    'bot:xu_huong': 'Nhánh theo yêu cầu chưa có kiểm định riêng. Số đo của bot chờ nến phá vỡ không áp dụng cho nhánh này. Chỉ tham khảo, không tự ghi lệnh hay phát tín hiệu Telegram.',
    'bot': 'MUA cần H1 và H4 cùng tăng, BÁN cần H1, H4 và D1 cùng giảm (từ đêm 24/11/2026); tối đa 6 lệnh mở cùng lúc (từ sáng 25/11/2026, trước là 3). Bot tự đo 2024–26: 1.249 lệnh, +4,38 giá mỗi lệnh, sụt giảm 621 giá; phần tăng chủ yếu do nhiều lệnh cùng chiều mở chồng lên nhau. Webapp đo độc lập với chi phí thật, trên nến đã sửa lệch giờ (3.522 lệnh): −0,002R mỗi lệnh ở 2015–2021, +0,174R ở 2022–2026. Vàng tăng gần suốt 2015–2026 nên phép đo ưu ái lệnh MUA, và cấu hình chọn khi đã nhìn dữ liệu nên con số lạc quan.',
    'ba_khung': 'Kiểm bản né tin 2023–10/2026: 2.610 lệnh, thắng 81,8%, hòa vốn cần 80,7%. 2016–2022 lỗ nhẹ. Đang đo, cần 300 lệnh mới kết luận.',
    'dinh_day': 'Khi kiểm lại có lãi mỏng năm 2026 nhưng lỗ cả 2023–2025. Sổ chạy bóng mới có vài lệnh.',
}
HUONG = {'BUY': 'MUA', 'SELL': 'BAN', 'MUA': 'MUA', 'BAN': 'BAN'}


def _r(x):
    return gia._so(x)


def _phuong_an(ma: str, ten: str, kieu: str, huong: str, vao: float, sl: float, tps: list, ly_do: str, vung=None, ghi_chu=None) -> dict:
    rui_ro = abs(vao - sl)
    return {'ma': ma, 'ten': ten, 'kieu': kieu, 'co': True, 'huong': HUONG[huong], 'vao': _r(vao), 'sl': _r(sl), 'tp': [_r(t) for t in tps],
            'vung': [_r(vung[0]), _r(vung[1])] if vung else None, 'rui_ro_gia': _r(rui_ro),
            'rr': [_r(abs(t - vao) / rui_ro) if rui_ro else None for t in tps], 'ly_do': ly_do, 'thong_ke': THONG_KE.get(ma, THONG_KE[ma.split(':')[0]]),
            'ghi_chu': ghi_chu or []}


def _khong(ma: str, ten: str, kieu: str, vi_sao: str) -> dict:
    return {'ma': ma, 'ten': ten, 'kieu': kieu, 'co': False, 'vi_sao': vi_sao, 'thong_ke': THONG_KE.get(ma, THONG_KE[ma.split(':')[0]])}


def ngan(cfg: dict, ma: str, tf: str) -> dict:
    """Kịch bản quan sát theo đúng khung đang được yêu cầu."""
    from . import entry_feed

    return ngan_tu_du_lieu(entry_feed.doc(cfg, ma, khung=tf), tf)


def ngan_tu_du_lieu(data: dict, tf: str) -> dict:
    """Dựng hai thẻ của một khung từ cùng ảnh chụp Bid/Ask và nến đã đóng."""
    a = next((r for r in data['ds'] if r['tf'] == tf), {})
    trang_thai = a.get('trang_thai')
    if trang_thai == 'dat' and not (a.get('plan_locked') and a.get('plan_id') and a.get('plan_hash')):
        trang_thai = 'ke_hoach_loi'
    co = trang_thai == 'dat'
    trang_thai_them = {'ke_hoach_loi': 'Chưa khóa được kế hoạch giá. Đang chờ lượt kiểm tra tiếp theo.'}
    p = []
    for loai, chip in (('pha_vo', 'pha_vo'), ('hoi_ema', 'ema_hoi')):
        co_loai = co and a.get('loai') == loai
        row = {'ma': f'ngan:{tf}:{loai}', 'ten': tin_hieu_ngan.LOAI[loai] + f' · {tf}', 'chip': chip, 'nhom': 'pp', 'khung': tf,
               'co': co_loai, 'hieu_luc': co and co_loai, 'quan_sat': True,
               'kieu': f'Quan sát nến {tf} đã đóng', 'thong_ke': 'Bộ quét ngắn hạn đang được theo dõi tiến cứu.'}
        row['thong_ke'] = 'Bộ quét nến và bối cảnh đa khung đang được kiểm định riêng; không coi là phương pháp đã chứng minh lợi nhuận.'
        row['ly_do'] = 'Mẫu nến đã đóng; chỉ quan sát khi khung nối, H1/H4 và D1 cùng chiều.'
        if co_loai:
            row.update(plan_id=a['plan_id'], plan_hash=a.get('plan_hash'), plan_locked=True)
            row['kieu'] += ' · Kế hoạch ' + a['plan_id'][-6:] + ' · Giá đã khóa'
            row.update(huong='BAN' if a['huong'] == 'BÁN' else a['huong'], vao=a.get('vao'), sl=a.get('sl'),
                       tp=[a['tp']], rr=[a['rr']], rui_ro_gia=abs(a['vao'] - a['sl']), nen=a['dong'],
                       thuc_thi={'loai': 'tt', 'tu': a['dong'], 'het': a['het'], 'atr': a['atr'], 'moc': a['moc'],
                                  'stops': data.get('minimum_stop', 0.)})
        else:
            row['vi_sao'] = data.get('ly_do') or (
                tin_hieu_ngan.TRANG_THAI.get(trang_thai, trang_thai_them.get(trang_thai, 'Chưa có dữ liệu.')) if a.get('loai') in (None, loai)
                else 'Nến này không xác nhận phương pháp.')
            if not a or trang_thai in ('thieu_nen', 'gia_cu', 'ke_hoach_loi'):
                row['thieu_du_lieu'] = True
        p.append(row)
    return {**{k: data[k] for k in ('ma', 'luc', 'nguon', 'bid', 'ask', 'tick_ms', 'so_le') if k in data},
            'het': datetime.fromtimestamp(data['tick_ms'] / 1000, timezone.utc).isoformat() if data.get('tick_ms') else None,
            'khung_phan_tich': tf, 'quy_trinh_ngan': True, 'phuong_an': [], 'phuong_phap': p, 'con_hieu_luc': int(co),
            'boi_canh': {'topdown': a.get('topdown'), 'atr_khung': a.get('atr')}, 'canh_bao': [], 'loi': [], 'ms': {}}


def gop_da_khung(cfg: dict, ma: str, data: dict) -> dict:
    """Chế độ "Tất cả" của bảng phân tích (28/11/2026): các phương pháp M15 cộng bộ quét đa khung M5/M15/M30, mỗi khung một thẻ riêng.
    Gọi SAU khi đã ghi nhật ký, để bộ quét (còn đang kiểm định tiến cứu) không lẫn vào sổ tín hiệu của các phương pháp."""
    for k in ('M5', 'M15', 'M30'):
        try:
            rows = ngan(cfg, ma, k)['phuong_phap']
        except Exception:                                                 # noqa: BLE001 - bộ quét lỗi không làm mất phần phương pháp
            continue
        for r in rows:
            r['chip'], r['ten_ngan'] = f'da_khung_{k}', f'Đa khung · {k}'
            data.setdefault('phuong_phap', []).append(r)
    return data


def phan_tich(cfg: dict, now: datetime | None = None) -> dict:
    g = cfg['gia']
    gia.can_gia(g)
    if gia.chia_se_song(g):                       # bản chia sẻ: các phương pháp tùy chọn theo ATR, như mọi mã khác
        from . import da_ma                       # noqa: PLC0415
        return da_ma.phan_tich(cfg, da_ma.ma_vang(cfg), now)
    now = now or datetime.now(timezone.utc)
    t_dau = time.perf_counter()
    fr = song.khung_song(g) or gia.khung(g)
    ms = {'Lấy nến và giá': round((time.perf_counter() - t_dau) * 1000)}
    het = fr['het']
    tuoi = max(0, int((now - het).total_seconds() // 60))
    m5, m15, m30 = fr['M5'], fr['M15'], fr['M30']
    h1, h4, d1 = fr['H1'].iloc[-300:], fr['H4'].iloc[-300:], fr['D1'].iloc[-900:]
    bid = float(fr.get('bid') or m5['close'].iloc[-1])
    ask = float(fr.get('ask') or bid + float(g.get('spread', 0.17)))
    out: dict = {'luc': now.isoformat(), 'het': het.isoformat(), 'tuoi_phut': tuoi, 'nguon': fr.get('nguon', 'kho'), 'bid': _r(bid), 'ask': _r(ask),
                 'tick_ms': int(het.timestamp() * 1000) if fr.get('nguon') == 'mt5' and fr.get('bid') and fr.get('ask') else None,
                 'phuong_an': [], 'canh_bao': [], 'loi': [], 'ms': ms}
    # Bối cảnh đa khung không phụ thuộc luật riêng của chủ dự án: bản cài mới (không có mã luật) vẫn có, không bịa tín hiệu.
    out['boi_canh'] = {'topdown': ai_timeframes.from_frames(fr, 'M15', now.timestamp()), 'spread': _r(ask - bid)}
    if tuoi > 20:
        out['canh_bao'].append(f'Giá đã cũ {tuoi} phút (thị trường nghỉ, MT5 mất kết nối, hoặc đang dùng kho nến). Các mức dưới đây tính trên giá cũ, không dùng để vào lệnh.')
    try:
        R, RT, RF, SN = gia._nap_ma(g)
        from tinhieu import levels as LV                                       # noqa: PLC0415
    except Exception as e:                                                     # noqa: BLE001
        out['loi'].append(f'Không nạp được mã luật của dự án: {type(e).__name__}: {e}')
        return out
    han_bot, han_m15 = 3.0, 5.0                                                # phút; lấy đúng hạn trong mã của dự án nếu nạp được
    try:
        from tinhieu import backtest as BT                                     # noqa: PLC0415
        han_bot = BT.MAX_ENTRY_DELAY.total_seconds() / 60
    except Exception:                                                          # noqa: BLE001
        pass
    try:
        from tools import ai_trend_history as TH                               # noqa: PLC0415
        han_m15 = TH.MAX_ENTRY_LAG.total_seconds() / 60
    except Exception:                                                          # noqa: BLE001
        pass

    def han(p, index, phut, gioi_han, vi):
        """Nến tín hiệu đóng quá hạn thì phương án chỉ còn để tham khảo: luật thật không vào lệnh muộn như vậy."""
        dong = index[-1].to_pydatetime() + timedelta(minutes=phut)
        qua = (now - dong).total_seconds() / 60
        if p.get('co'):
            p['thuc_thi'] = {'loai': 'tt', 'tu': dong.isoformat(), 'het': (dong + timedelta(minutes=gioi_han)).isoformat()}
        if p.get('co') and qua > gioi_han:
            p.setdefault('_ly', []).append(f'Nến tín hiệu đã đóng {int(qua)} phút trước; {vi}.')
        return p

    def thu(ten, fn):
        t0 = time.perf_counter()
        try:
            return fn()
        except Exception as e:                                                 # noqa: BLE001
            out['loi'].append(f'{ten}: {type(e).__name__}: {e}')
            return None
        finally:                                                               # thời gian từng bước, để thấy bước nào chậm
            ms[ten] = ms.get(ten, 0) + round((time.perf_counter() - t0) * 1000)

    # ---- bối cảnh
    snap = thu('Bối cảnh', lambda: R.snapshot(m15.iloc[-320:], h1, h4, d1, 'M15')) or {}
    bc = {'xu_huong': {k: int(snap[k]) for k in ('D1', 'H4', 'H1', 'trend') if k in snap}, 'atr_m15': _r(snap.get('atr')),
          'ho_tro': _r(snap.get('support')), 'khang_cu': _r(snap.get('resistance')), 'spread': _r(ask - bid)}
    bc['topdown'] = ai_timeframes.from_frames(fr, 'M15', now.timestamp())

    def vung_gan():
        atr_h1 = float(R.atr_sma(fr['H1'], 14).iloc[-1])
        src = m15.iloc[-300:].reset_index(names='time')
        zs = [dict(z, loai='Khoảng trống giá') for z in SN.fvg_zones(src, 0.1 * atr_h1, 8)] + \
             [dict(z, loai='Khối lệnh') for z in SN.order_blocks(src, 1.0 * atr_h1, 8)]
        tren = min((z for z in zs if z['duoi'] > bid), key=lambda z: z['duoi'], default=None)
        duoi = max((z for z in zs if z['tren'] < bid), key=lambda z: z['tren'], default=None)
        return {k: ({'loai': z['loai'], 'duoi': _r(z['duoi']), 'tren': _r(z['tren'])} if z else None) for k, z in (('tren', tren), ('duoi', duoi))}
    bc['vung'] = thu('Vùng giá gần nhất', vung_gan) or {}

    def tin():
        news, _ = gia.tin_usd(g)
        nxt = next((t for t in news if t > het), None)
        return {'sap_toi': nxt.isoformat() if nxt else None, 'con_phut': int((nxt - het).total_seconds() // 60) if nxt else None,
                'dang_ne': bool(SN.in_news_blackout(het, news))}
    bc['tin'] = (thu('Lịch tin USD', tin) if g.get('lich_tin') else None) or {}
    if bc['tin'].get('dang_ne'):
        out['canh_bao'].append('Đang trong 15 phút quanh một tin USD mạnh: bot và các luật của bạn không vào lệnh lúc này.')
    elif bc['tin'].get('con_phut') is not None and bc['tin']['con_phut'] <= 60:
        out['canh_bao'].append(f'Còn {bc["tin"]["con_phut"]} phút nữa có tin USD mạnh.')
    from . import hoc                                                          # noqa: PLC0415 - nạp muộn, tránh vòng nạp
    bc.update(thu('Bối cảnh phiên và biên độ', lambda: hoc.boi_canh_luc(fr['H1'], het)) or {})
    def lien_thi_truong():
        from . import da_ma                                                    # noqa: PLC0415
        ds = da_ma.danh_sach(cfg, now)
        if not ds.get('san_sang'):
            return None
        m = {x['ma'][:6]: x for x in ds['ds'] if 'loi' not in x and x.get('doi_ngay') is not None}
        co = [(m[k], d) for k, d in (('EURUSD', -1), ('GBPUSD', -1), ('USDJPY', 1)) if k in m]
        if len(co) < 2:
            return None
        xu = {tf: sum(d * x['xu_huong'][tf] for x, d in co) for tf in ('D1', 'H4', 'H1')}
        return {'usd_ngay_pct': _r(sum(d * x['doi_ngay'] for x, d in co) / len(co)), 'usd_xu_huong': {tf: (v > 0) - (v < 0) for tf, v in xu.items()},
                'so_cap': len(co), 'cap': [x['ma'] for x, _ in co]}
    bc['lien_thi_truong'] = thu('Liên thị trường', lien_thi_truong)
    out['boi_canh'] = bc

    # ---- phương án của từng luật
    def tu_setup(ma, kieu, setup, tf):
        sig = LV.build(setup, bid, ask, now, 1)
        if sig is None:
            return _khong(ma, 'Luật bot tín hiệu', kieu, f'Luật có điều kiện trên {tf} nhưng dừng lỗ theo vùng hỗ trợ/kháng cự nằm ngoài khoảng {R.SL_MIN:g}–{R.SL_MAX:g} giá, nên luật không ra lệnh.')
        return _phuong_an(ma, 'Luật bot tín hiệu', kieu, sig.side, sig.entry, sig.sl, list(sig.tps), f'{sig.reason} Khung {tf}.'.strip(),
                          vung=(sig.zone_low, sig.zone_high), ghi_chu=['Thang TP theo R: ' + ' · '.join(f'{x:g}R'.replace('.', ',') for x in LV.TP_R) + '.' if LV.TP_R else 'Thang TP cố định.',
                                                                       'Bot giữ lệnh tối đa 24 giờ.'] + ([giu_lenh.cau()] if ma == 'bot:nen' and giu_lenh.cau() else []))

    xu_luat = R.trend_rule_text() if hasattr(R, 'trend_rule_text') else 'H1, H4 và D1 phải cùng chiều'      # lọc xu hướng của bot đang chạy

    def bot_nen():
        for tf in ('M5', 'M15'):
            for s in R.candidates(fr[tf].iloc[-320:], h1, h4, d1, tf):
                pa = tu_setup('bot:nen', 'nến tín hiệu vừa đóng', s, tf)
                if not pa['co']:
                    continue                            # như bot riêng: thử vùng SL tiếp theo, không bỏ cả nến vì vùng đầu không khớp
                pa = han(pa, fr[tf].index, 5 if tf == 'M5' else 15, han_bot,
                         f'bot bỏ tín hiệu khi nến đã đóng quá {han_bot:g} phút')
                pa.update(nen=s.bar_time.isoformat(), khung=tf)
                ly_gia = chat_luong_call.kiem(pa, fr, now)
                pa.setdefault('_ly', []).extend(ly_gia)
                pa['chat_luong_call'] = {'phien_ban': chat_luong_call.PHIEN_BAN, 'gia_dat': not ly_gia, 'ly_do': ly_gia}
                try:                                                   # phiếu: chờ phá đỉnh/đáy nến tín hiệu (kiểu vào đã qua cổng, cong-cu/diem_vao_bot.py)
                    k = fr[tf]
                    nen_dong = (k.index[-1] + timedelta(minutes=5 if tf == 'M5' else 15)).to_pydatetime()
                    pa['phieu'] = phieu.lap_bot(pa, nen_dong, float(k['high'].iloc[-1]), float(k['low'].iloc[-1]), tf, bid, ask, now,
                                                LV.TP_R or (0.5, 1.0, 1.5, 2.0, 2.5, 3.0))
                except Exception:                                      # noqa: BLE001 - phiếu hỏng không được làm hỏng phương án gốc
                    pass
                return pa
        return _khong('bot:nen', 'Luật bot tín hiệu', 'nến tín hiệu vừa đóng',
                      f'Nến M5 và M15 vừa đóng không phá đỉnh hay đáy của quãng trước đó theo xu hướng ({xu_luat}), hoặc bị bộ lọc độ dãn, thân nến loại.')

    def bot_xu_huong():
        s = R.on_demand(m5.iloc[-320:], h1, h4, d1, 'M5')
        if s is None:
            return _khong('bot:xu_huong', 'Luật bot tín hiệu', 'theo xu hướng, không chờ nến',
                          f'Xu hướng chưa đủ điều kiện ({xu_luat}), hoặc không có vùng hỗ trợ/kháng cự cho dừng lỗ trong khoảng cho phép.')
        p = tu_setup('bot:xu_huong', 'theo xu hướng, không chờ nến', s, 'M5')
        if p['co']:
            p['_ly'] = ['Nhánh theo yêu cầu chưa được kiểm định riêng; chỉ tham khảo, không tự phát tín hiệu.']
        return p

    def ba_khung():
        last = m15.iloc[-1]
        q = RT.decide(fr['D1']['close'], fr['H4']['close'], fr['H1']['close'], float(last['open']), float(last['close']))
        trong = bool(RT.in_window((m15.index[-1] + timedelta(minutes=15)).to_pydatetime()))
        if q not in ('MUA', 'BAN'):
            return _khong('ba_khung', 'Luật xu hướng ba khung', 'nến M15 vừa đóng', 'D1, H4, H1 chưa cùng chiều, hoặc nến M15 vừa đóng không hồi ngược xu hướng.')
        vao, sl, tp = RT.levels(q, bid, ask)
        p = _phuong_an('ba_khung', 'Luật xu hướng ba khung', 'nến M15 vừa đóng', q, vao, sl, [tp],
                       'D1, H4, H1 cùng chiều và nến M15 vừa đóng hồi ngược chiều đó.',
                       ghi_chu=[f'Chốt {RT.TP_USD:g} USD, dừng {RT.SL_USD:g} USD ở 0,01 lot: một lệnh thua xóa {RT.SL_USD / RT.TP_USD:g} lệnh thắng.'])
        if not trong:
            p['_ly'] = ['Nến vừa đóng nằm ngoài khung giờ của luật (14:00–03:00 giờ Việt Nam, thứ Hai tới thứ Sáu).']
        return han(p, m15.index, 15, han_m15, 'luật chỉ vào ngay sau khi nến M15 đóng')

    def dinh_day():
        atr = float(R.atr_sma(m30, 14).iloc[-1])
        s = RF.decide(m15.iloc[-200:], bid, ask, atr, False, None)
        d = s.model_dump() if hasattr(s, 'model_dump') else dict(vars(s))
        if d.get('hanh_dong') not in ('MUA', 'BAN'):
            return _khong('dinh_day', 'Luật đỉnh/đáy 8 giờ', 'nến M15 vừa đóng', d.get('ly_do') or 'Nến vừa đóng không từ chối đỉnh hay đáy 8 giờ.')
        tps = [d[k] for k in ('tp1', 'tp2', 'tp3') if d.get(k) is not None]
        p = _phuong_an('dinh_day', 'Luật đỉnh/đáy 8 giờ', 'nến M15 vừa đóng', d['hanh_dong'], float(d['gia_vao']), float(d['sl']), sorted(set(tps), key=tps.index),
                       d.get('ly_do') or '', ghi_chu=['Dừng lỗ lùi 0,5 lần ATR sau đỉnh hoặc đáy; chốt hết ở 1,5R; giữ tối đa 8 giờ.'])
        return han(p, m15.index, 15, han_m15, 'luật chỉ vào ngay sau khi nến M15 đóng')

    for ten, fn in (('Luật bot (nến tín hiệu)', bot_nen), ('Luật bot (theo xu hướng)', bot_xu_huong), ('Luật ba khung', ba_khung), ('Luật đỉnh/đáy', dinh_day)):
        p = thu(ten, fn)
        if p:
            out['phuong_an'].append(p)
    chung = []                                                                 # lý do áp cho mọi luật
    if tuoi > 20:
        chung.append(f'Giá đã cũ {tuoi} phút.')
    if bc['tin'].get('dang_ne'):
        chung.append('Đang trong 15 phút quanh một tin USD mạnh.')
    for p in out['phuong_an']:
        ly = (chung + p.pop('_ly', [])) if p['co'] else []
        p['hieu_luc'] = bool(p['co']) and not ly
        p['vi_sao_het'] = ly
        f = p.get('phieu')
        ly_phieu = chung + (p.get('chat_luong_call') or {}).get('ly_do', [])
        if f and ly_phieu and f.get('trang_thai') == 'con_hieu_luc':
            f['trang_thai'] = 'bi_loc'
            f['loc_hong'] = list(dict.fromkeys(list(f.get('loc_hong') or []) + ly_phieu))
    out['con_hieu_luc'] = sum(p['hieu_luc'] for p in out['phuong_an'])
    # ---- các phương pháp tùy chọn (không phải luật trong sổ): cùng dạng phương án, để riêng một danh sách
    out['phuong_phap'] = []
    tin_gan = []                                                               # tin USD mức cao trong 6 giờ quanh lúc này: đủ cho mọi tín hiệu còn sống
    if g.get('lich_tin'):
        tin_gan = thu('Lịch tin USD', lambda: [t for t in gia.tin_usd(g)[0] if abs((t - het).total_seconds()) <= 6 * 3600]) or []
    for ma in phuong_phap.DS:
        p = thu(phuong_phap.DS[ma]['ten'], lambda ma=ma: phuong_phap.phuong_an(ma, m15, fr['H1'], bid, ask, now, chung))
        if p:
            # phiếu vào lệnh theo công thức đã đo (so_cong_khai/phieu.py); không thay phương án gốc ở trên
            p['phieu'] = thu('Phiếu vào lệnh', lambda ma=ma: phieu.lap(ma, m15, fr['H1'], fr['H4'], bid, ask, now, tin_gan, float(g.get('spread', 0.17)), d1=fr.get('D1')))
            if p['phieu'] and chung and p['phieu']['trang_thai'] == 'con_hieu_luc':
                p['phieu']['trang_thai'], p['phieu']['loc_hong'] = 'bi_loc', list(chung)      # giá cũ hoặc đang né tin: mọi phương án chỉ để tham khảo
            out['phuong_phap'].append(p)
    def cham_mo_hinh():                                            # điểm mô hình (thử nghiệm) cho từng phương án đang có điểm vào
        from . import mo_hinh                                      # noqa: PLC0415 - nạp muộn: mô hình tắt thì không cần tới
        return mo_hinh.gan(cfg, fr, out['phuong_phap'])
    out['mo_hinh'] = thu('Điểm mô hình', cham_mo_hinh)
    out['ict'] = thu('Bản đồ ICT', lambda: phuong_phap.ban_do_ict(m15, fr['H1'], bid, now))
    hp = thu('Harrison 3 Khung', lambda: harrison.analyze(fr, bid, ask, now, chung))
    if hp:
        out['phuong_phap'].append(hp)
    co = [p for p in out['phuong_an'] if p['co']]
    ms['Tổng'] = round((time.perf_counter() - t_dau) * 1000)
    out['dong_thuan'] = {'MUA': sum(p['huong'] == 'MUA' for p in co), 'BAN': sum(p['huong'] == 'BAN' for p in co), 'khong': len(out['phuong_an']) - len(co)}
    return out
