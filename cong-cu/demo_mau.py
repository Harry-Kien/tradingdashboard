"""Dữ liệu demo công khai hoàn toàn giả lập; không đọc cấu hình, API hay MT5."""
import math
from datetime import timedelta


def cover():
    """Minh họa SVG dựng từ dữ liệu mẫu, không chụp tài khoản riêng."""
    panels = ''.join(f'<rect x="{45+i*345}" y="150" width="330" height="135" rx="14" fill="#141610" stroke="#2b3025"/><text x="{65+i*345}" y="185" fill="#adb4a4" font-size="17">{label}</text><text x="{65+i*345}" y="245" fill="#edf0e8" font-size="34" font-weight="700">{value}</text>'
                     for i, (label, value) in enumerate([('Sample equity · USD', '10,000.00'), ('Floating P/L · USD', '0.00'), ('Open positions', '0'), ('Stop-loss risk', '0.00%')]))
    lines = ''.join(f'<path d="M 490 {400+i*65} H 1370" stroke="#2b3025"/><text x="510" y="{438+i*65}" fill="#c3c9ba" font-size="20">{label}</text><text x="1190" y="{438+i*65}" fill="{color}" font-size="23">{value}</text>'
                    for i, (label, value, color) in enumerate([('Sample account · 10,000 USD', '+240.00', '#68de73'), ('Sample account · 50,000 USD', '-350.00', '#f57970'), ('Sample signals · TP1', '18 / 30', '#c3c9ba'), ('Shadow research · sample', '20 / 36', '#c3c9ba')]))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="900" viewBox="0 0 1440 900"><rect width="1440" height="900" rx="18" fill="#090b08"/><g font-family="Arial,sans-serif"><text x="45" y="55" fill="#a3ff12" font-size="15" letter-spacing="2">HARRY GOLD RESEARCH · SYNTHETIC DEMO</text><text x="45" y="108" fill="#edf0e8" font-size="35" font-weight="700">Your trading session at a glance</text>{panels}<rect x="45" y="315" width="1350" height="390" rx="14" fill="#10120e" stroke="#2b3025"/><text x="68" y="365" fill="#c3c9ba" font-size="20">XAUUSD · SAMPLE</text><text x="68" y="425" fill="#edf0e8" font-size="44">2,400.00</text><polyline points="70,590 100,560 130,580 160,550 190,555 220,520 250,530 280,480 310,495 345,460 375,470 410,440" fill="none" stroke="#a3ff12" stroke-width="3"/><text x="490" y="365" fill="#edf0e8" font-size="24" font-weight="700">Journals and research</text>{lines}<rect x="45" y="735" width="660" height="110" rx="14" fill="#141610" stroke="#2b3025"/><rect x="725" y="735" width="670" height="110" rx="14" fill="#141610" stroke="#2b3025"/><text x="68" y="780" fill="#edf0e8" font-size="22">Plan · Check risk · Review results</text><text x="748" y="780" fill="#edf0e8" font-size="22">Your MT5 data stays in your local app</text><text x="68" y="820" fill="#929b88" font-size="17">Entirely fictional data, for interface demonstration only.</text></g></svg>'''


def tao(now):
    stamp = now.isoformat()
    rows = []
    for i, (ma, price, digits, step, group) in enumerate([
        ('XAUUSD', 2400.0, 2, 1.2, 'kim_loai'), ('EURUSD', 1.08000, 5, .00015, 'forex'),
        ('GBPUSD', 1.26000, 5, .00018, 'forex'), ('USDJPY', 150.0, 3, .02, 'forex'),
        ('AUDUSD', .66000, 5, .00012, 'forex'), ('BTCUSD', 60000.0, 2, 45.0, 'crypto')]):
        curve = [round(price + step * (math.sin(n * .35 + i) + n / 20 - 2), digits) for n in range(40)]
        price = curve[-1]
        atr = step * 4
        rows.append({'ma': ma, 'goc': ma, 'ten': ma + ' · SAMPLE', 'lop': group, 'so_le': digits,
                     'diem': 10 ** -digits, 'gt1': 100 if ma == 'XAUUSD' else 100000 if group == 'forex' else 1,
                     'lot_min': .01, 'lot_buoc': .01, 'lot_max': 10, 'co_hd': 100, 'ky_quy_1lot': 1000,
                     'muc_dung': 0, 'q': [price, round(price + step * .2, digits), int(now.timestamp() * 1000)],
                     'tia': curve, 'ref': {'ngay': curve[0]}, 'hom_nay': {'thap': min(curve), 'cao': max(curve)},
                     'kt': {k: {'d': 1 if i % 2 == 0 else -1, 'atr': atr, 'm': 8, 'b': 3, 't': 8}
                            for k in ('M15', 'H1', 'H4', 'D1')}, 'adr': atr * 3})
    market = {'san_sang': True, 'mau': True, 'luc': stamp, 'ds': rows,
              'lop': {'forex': 'Forex', 'kim_loai': 'Kim loại', 'crypto': 'Crypto'}, 'tien_te': {},
              'tai_khoan': {'san': 'SAMPLE', 'tien': 'USD'}, 'tuong_quan': None,
              'lich': {'co': True, 'ds': [{'ten': 'Sự kiện minh họa · SAMPLE', 'tien': 'USD', 'muc': 3,
                                         't': (now + timedelta(hours=3)).isoformat()}]}}
    books = []
    for i, (name, kind, value, unit, count, n) in enumerate([
        ('Tài khoản mẫu 10.000 USD', 'demo', 10240, 'USD', 0, 42),
        ('Tài khoản mẫu 50.000 USD', 'demo', 49650, 'USD', 0, 38),
        ('Tín hiệu minh họa', 'signal', 18, 'TP1', 30, 30),
        ('Nghiên cứu ba khung', 'shadow', 20, 'win', 36, 36),
        ('Nghiên cứu đỉnh/đáy', 'shadow', -1.2, 'R', 25, 25)]):
        change = 240 if i == 0 else -350
        initial = value - change
        books.append({'id': 'sample-' + str(i), 'ten': name, 'loai': kind, 'gia_tri': value, 'don_vi': unit,
                      'n': n, 'mo': 0, 'mau': count, 'thay_doi': change if kind == 'demo' else None,
                      'pct': change / initial * 100 if kind == 'demo' else 60 if i == 2 else 55.6 if i == 3 else 40,
                      'tia': [initial + (value - initial) * n / 24 + math.sin(n) * 25 for n in range(25)],
                      'luc': stamp, 'thieu': False})
    account = {'mau': True, 'san_sang': True, 'luc': stamp, 'so': 'SAMPLE', 'loai': 'MINH HỌA', 'tien': 'USD',
               'von': 10000, 'treo': 0, 'lenh': [], 'cho': [], 'rui_ro': {'pct': 0}}
    overview = {'account': account, 'ledger': {'mau': True, 'luc': stamp, 'so': books, 'loi': []},
                'activity': {'mau': True, 'ds': [{'tieu_de': 'Đã hoàn tất kế hoạch minh họa',
                             'noi_dung': 'Dữ liệu giả lập để trải nghiệm giao diện; không phải tín hiệu giao dịch.', 'luc': stamp}]},
                'risk': {'mau': True, 'san_sang': True, 'ds': []},
                'health': {'mau': True, 'muc': [{'id': 'demo', 'ten': 'Bản minh họa', 'muc': 'tot',
                           'chi_tiet': 'Dữ liệu giả lập, không kết nối tài khoản MT5.'}]}}
    plans = {}
    for x in rows:
        for tf in ('M15', 'H1', 'H4'):
            atr = x['kt'][tf]['atr']
            plans[x['ma'], tf] = {'ma': x['ma'], 'khung': tf, 'dac_ta': x, 'bid': x['q'][0], 'ask': x['q'][1],
                                  'atr': atr, 'cao': [v + atr for v in x['tia']], 'thap': [v - atr for v in x['tia']]}
    # Dùng cùng phép tính với app trên chuỗi nến giả lập; không chụp chỉ báo từ MT5.
    import numpy as np
    from so_cong_khai import thi_truong
    details, volatility, returns = {}, {}, []
    times = np.array([int(now.timestamp()) - (719 - n) * 3600 for n in range(720)])
    for i, x in enumerate(rows):
        atr = x['kt']['H1']['atr']
        close = np.array([x['q'][0] + atr * (math.sin(n * .12 + i) + n / 720 - 1) for n in range(720)])
        high, low = close + atr / 2, close - atr / 2
        full = thi_truong.ky_thuat(close, high, low, close, chi_tiet=True)
        details[x['ma']] = {'ma': x['ma'], 'goc': x['goc'], 'so_le': x['so_le'], 'luc': stamp,
                            'mau': True, 'khung': {tf: full for tf in ('M15', 'H1', 'H4', 'D1')}}
        volatility[x['ma']] = {'ma': x['ma'], 'goc': x['goc'], 'so_nen': 720, 'tu': int(times[0]),
                               'den': int(times[-1]), 'mau': True, **thi_truong.bien_dong_theo_gio(times, high, low)}
        returns.append(np.diff(close) / close[:-1])
    market['tuong_quan'] = {'ma': [x['ma'] for x in rows], 'goc': [x['goc'] for x in rows],
                           'ma_tran': np.corrcoef(returns).round(2).tolist(), 'so_nen': 719,
                           'khung': 'H1', 'luc': stamp, 'mau': True}
    return {'tt': market, 'kt': details, 'bd': volatility, 'luc': now}, plans, overview
