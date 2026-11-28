"""Trang giới thiệu (index.html) của bản demo trên GitHub Pages / tên miền riêng: app làm gì, bấm thử demo, cài miễn phí. Hai bản viết sẵn
(tiếng Việt ở gốc, tiếng Anh ở en/), không qua bộ dịch tự động. Màu xanh than và đồng thau theo chủ đề vàng; đỏ/xanh chỉ dùng cho lời/lỗ như
trong app. Điểm nhấn duy nhất: thẻ kết luận "Không nên" giống trang Kiểm tra lệnh, số liệu giả lập hoàn toàn, không lấy từ tài khoản của chủ hệ thống."""
from __future__ import annotations

import sys
from html import escape
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import trang as _trang  # noqa: E402
from so_cong_khai.logo import LOGO_NHO  # noqa: E402
from so_cong_khai.thuong_hieu import TEN  # noqa: E402

KHO = 'https://github.com/Harry-Kien/tradingdashboard'

CHU = {
    'vi': {
        'title': f'{TEN} · Biết một lệnh mất bao nhiêu trước khi vào',
        'mo_ta': 'Bảng điều khiển giao dịch miễn phí chạy trên máy bạn, đọc dữ liệu thật từ MetaTrader 5: tính khối lượng theo % rủi ro, cảnh báo lệnh '
                 'phạm quy tắc và chỉ ra thói quen nào đang làm bạn mất tiền.',
        'doi': ('English', 'en/index.html'), 'cai': 'Cài miễn phí',
        'h1': 'Biết một lệnh sẽ mất bao nhiêu, trước khi bấm vào.',
        'sub': 'Bảng điều khiển miễn phí chạy trên máy bạn, đọc dữ liệu thật từ MetaTrader 5. App tính khối lượng theo % rủi ro, cảnh báo lệnh phạm '
               'quy tắc bạn đặt, và chỉ ra thói quen nào đang làm bạn mất tiền. App chỉ đọc, không bao giờ đặt lệnh.',
        'thu': 'Thử bản demo', 'yeu_cau': 'Chạy trên Windows có MetaTrader 5. Có tiếng Việt và tiếng Anh.',
        'the': {'nhan': 'Kiểm tra trước khi vào lệnh', 'lenh': 'MUA XAUUSD 0,01 lot, dừng lỗ cách 40 giá', 'kl': 'Không nên',
                'kl_noi': 'Lệnh này phạm quy tắc rủi ro bạn đặt.',
                'dong': [('xau', 'Rủi ro minh họa 5% vốn', 'Vốn mẫu 800 USD quá nhỏ cho dừng lỗ này; mức bạn đặt là 1%.'),
                         ('chu_y', 'Tin mạnh USD sau 14 phút', 'Core PCE ra lúc 20:30. Chờ tin ra xong rồi hãy vào.'),
                         ('tot', 'Có dừng lỗ, lời/lỗ 1:2', 'Cần thắng trên 33% số lệnh để hòa vốn.')],
                'chu_thich': 'Ví dụ giả lập hoàn toàn; không phải tài khoản hay kết quả của chủ hệ thống.'},
        'lop_h2': 'Ba lớp giữ tiền', 'lop_sub': 'Cả ba dùng chung một bộ quy tắc, bạn đặt một lần.',
        'lop': [('Trước khi giao dịch', 'Kế hoạch vốn và lệnh',
                 'Nhập vốn, chọn mức rủi ro. App chia ra số tiền được mất mỗi lệnh và mỗi ngày, gợi ý dừng lỗ theo đỉnh/đáy gần nhất và theo ATR, '
                 'tính ký quỹ và khoảng giá tới mức sàn đóng lệnh, rồi mô phỏng 2.000 chuỗi lệnh để cho biết khả năng mất một nửa tài khoản.',
                 ('Thử trong demo', 'ke-hoach.html')),
                ('Ngay trước khi vào lệnh', 'Kiểm tra trước khi vào lệnh',
                 'Mười ba quy tắc chấm bằng dữ liệu MT5 lúc đó: khối lượng, spread, tin mạnh sắp ra, lỗ trong ngày, tổng rủi ro đang mở, các mã '
                 'chạy cùng nhau, và lịch sử của chính bạn với kiểu lệnh này.', None),
                ('Sau khi đóng lệnh', 'Kỷ luật giao dịch',
                 'Chấm lại từng lệnh đã đóng, tách lãi lỗ của lệnh đúng quy tắc với lệnh phạm quy tắc, để thấy thói quen nào đang tốn tiền: '
                 'vào lại ngay sau lệnh thua, tăng khối lượng để gỡ, quên dừng lỗ.', ('Thử trong demo', 'ky-luat.html'))],
        'chi_co_ban_cai': 'Có trong bản cài trên máy',
        'canh_bao': 'Trong lúc giao dịch, dải cảnh báo trên mọi trang báo ngay khi bạn chạm giới hạn lỗ ngày, giữ lệnh không có dừng lỗ, '
                    'hay sắp có tin mạnh mà đang giữ lệnh.',
        'cung_h2': 'Cũng có trong app',
        'cung': [('Bảng giá trực tiếp', 'Gần 90 mã Forex, kim loại, dầu, chỉ số, tiền mã hóa; tín hiệu kỹ thuật 4 khung, sức mạnh tiền tệ, tương quan.',
                  'thi-truong.html'),
                 ('Phân tích hiệu suất', 'Đường vốn, lịch lãi lỗ, thắng thua theo mã, phiên, giờ, và nhận xét tự động.', 'hieu-suat.html'),
                 ('Tin tức và lịch kinh tế', 'Tin mạnh sắp ra của các đồng tiền bạn đang giao dịch.', None),
                 ('Biểu đồ nến theo từng tick', 'Kèm lệnh đang mở, dừng lỗ và chốt lời trên biểu đồ.', None),
                 ('Gia sư giao dịch', 'Hỏi đáp từng bước về kiến thức giao dịch, dùng khóa AI của chính bạn.', None),
                 ('Nhóm Telegram và sao lưu', 'Gửi tín hiệu, kết quả vào nhóm của bạn; sao lưu dữ liệu mỗi ngày.', None)],
        'xem_demo': 'Xem demo', 'anh_alt': 'Bảng giá trực tiếp trong app',
        'cai_h2': 'Cài trong ba bước',
        'cai_b': ['Mở MetaTrader 5 và đăng nhập một tài khoản demo.',
                  'Tải mã nguồn từ GitHub, giải nén, bấm đúp tệp BAT_DAU.bat. Máy chưa có Python thì tệp này hỏi rồi cài giúp.',
                  'Mở biểu tượng Harry Gold Research trên màn hình là dùng được.'],
        'tai': 'Tải từ GitHub',
        'tin_h2': 'Chỉ đọc, chạy trên máy bạn',
        'tin': 'App không đặt, sửa hay đóng lệnh nào. Mặc định chỉ đọc tài khoản demo, chạy trên máy bạn và không gửi số liệu tài khoản đi đâu. '
               'Mã nguồn công khai trên GitHub để ai cũng kiểm được.',
        'mien_tru': 'Không phải lời khuyên đầu tư. Giao dịch CFD và Forex có rủi ro mất vốn cao. Quản lý rủi ro tốt làm lệnh thua nhỏ lại, '
                    'chứ không làm lệnh thắng nhiều hơn.',
    },
    'en': {
        'title': f'{TEN} · Know what a trade can lose before you take it',
        'mo_ta': 'A free trading dashboard that runs on your computer and reads real data from MetaTrader 5: position sizing by % risk, a check '
                 'that blocks rule-breaking trades, and a review that shows which habits cost you money.',
        'doi': ('Tiếng Việt', '../index.html'), 'cai': 'Install free',
        'h1': 'Know what a trade can lose, before you click.',
        'sub': 'A free dashboard that runs on your computer and reads real data from MetaTrader 5. It sizes positions by % risk, flags trades that '
               'break the rules you set, and shows which habits are costing you money. It only reads; it never places a trade.',
        'thu': 'Try the demo', 'yeu_cau': 'Runs on Windows with MetaTrader 5. In English and Vietnamese.',
        'the': {'nhan': 'Pre-trade check', 'lenh': 'BUY XAUUSD 0.01 lots, stop 40 points away', 'kl': 'Avoid',
                'kl_noi': 'This trade breaks your risk rules.',
                'dong': [('xau', 'Illustrative risk: 5% of equity', 'A sample 800 USD account is too small for this stop; your limit is 1%.'),
                         ('chu_y', 'High-impact USD news in 14 min', 'Core PCE is out at 20:30. Wait until it is out.'),
                         ('tot', 'Stop loss set, reward/risk 1:2', 'You need over 33% winners to break even.')],
                'chu_thich': 'Entirely fictional example; not the owner’s account or results.'},
        'lop_h2': 'Three layers that protect your money', 'lop_sub': 'All three share one set of rules that you set once.',
        'lop': [('Before you trade', 'Money and trade plan',
                 'Enter your capital and pick a risk level. The app works out what you can lose per trade and per day, suggests a stop from the '
                 'nearest swing and from ATR, shows margin and the move to broker stop-out, and simulates 2,000 runs to show the chance of losing '
                 'half the account.', ('Try it in the demo', 'ke-hoach.html')),
                ('Right before you enter', 'Pre-trade check',
                 'Thirteen rules checked against live MT5 data: size, spread, upcoming high-impact news, today\'s loss, total open risk, correlated '
                 'symbols, and your own history with this kind of trade.', None),
                ('After the trade closes', 'Trading discipline',
                 'Re-checks every closed trade and splits the profit and loss of rule-following and rule-breaking trades, so you see which habits '
                 'cost money: jumping back in after a loss, sizing up to win it back, forgetting the stop.', ('Try it in the demo', 'ky-luat.html'))],
        'chi_co_ban_cai': 'In the installed app',
        'canh_bao': 'While you trade, a warning strip on every page tells you the moment you hit your daily loss limit, hold a trade without a stop, '
                    'or hold trades into high-impact news.',
        'cung_h2': 'Also in the app',
        'cung': [('Live price board', 'About 90 forex, metal, oil, index and crypto symbols; technical ratings on 4 timeframes, currency strength, '
                  'correlation.', 'thi-truong.html'),
                 ('Performance analytics', 'Equity curve, P/L calendar, wins and losses by symbol, session and hour, with automatic insights.',
                  'hieu-suat.html'),
                 ('News and economic calendar', 'Upcoming high-impact news for the currencies you trade.', None),
                 ('Tick-by-tick candle chart', 'With your open trades, stops and targets on the chart.', None),
                 ('Trading tutor', 'Step-by-step Q&A on trading concepts, using your own AI key.', None),
                 ('Telegram group and backups', 'Post signals and results to your group; back up your data every day.', None)],
        'xem_demo': 'See the demo', 'anh_alt': 'Live price board in the app',
        'cai_h2': 'Install in three steps',
        'cai_b': ['Open MetaTrader 5 and log in to a demo account.',
                  'Download the code from GitHub, unzip it and double-click BAT_DAU.bat. If Python is missing it asks, then installs it for you.',
                  'Open the Harry Gold Research icon on your desktop.'],
        'tai': 'Download from GitHub',
        'tin_h2': 'Read-only, on your computer',
        'tin': 'The app never places, changes or closes a trade. By default it only reads demo accounts, runs on your computer and sends your '
               'account data nowhere. The source code is public on GitHub so anyone can check it.',
        'mien_tru': 'Not investment advice. Trading CFDs and forex carries a high risk of losing money. Good risk management makes losing trades '
                    'smaller; it does not make winning trades more frequent.',
    },
}

CSS = r"""
:root{--nen:#0F1A24;--khoi:#172534;--vien:#24384C;--dong:#C9A227;--chu:#E8ECEF;--phu:#9AA8B5;--lo:#E5484D;--lai:#2FB57C;--vang:#E9A23B}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--nen);color:var(--chu);font:400 16px/1.6 "Be Vietnam Pro",system-ui,"Segoe UI",sans-serif}
a{color:inherit}a:focus-visible,button:focus-visible{outline:2px solid var(--dong);outline-offset:3px;border-radius:6px}
.khung{max-width:1120px;margin:0 auto;padding:0 20px}
header.dau{display:flex;align-items:center;gap:14px;padding:18px 0}
header.dau .ten{display:flex;align-items:center;gap:10px;text-decoration:none;font-weight:700;font-size:16px;margin-right:auto}
header.dau .ten img{width:44px;height:44px;border-radius:12px;background:#0b141c}
header.dau nav{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
header.dau nav a{text-decoration:none;color:var(--phu);font-size:14px;padding:8px 10px;border-radius:8px}header.dau nav a:hover{color:var(--chu)}
.nut{display:inline-flex;align-items:center;justify-content:center;min-height:46px;padding:0 20px;border-radius:12px;font-weight:600;font-size:15px;
 text-decoration:none;border:1px solid transparent}
.nut.chinh{background:var(--dong);color:#17130A}.nut.chinh:hover{background:#D8B23A}
.nut.phu{border-color:var(--vien);color:var(--chu)}.nut.phu:hover{border-color:var(--phu)}
header.dau .nut{min-height:38px;padding:0 14px;font-size:14px}
.mo{display:grid;grid-template-columns:minmax(0,1.08fr) minmax(0,.92fr);gap:48px;align-items:center;padding:56px 0 72px}
.mo h1{font-size:clamp(34px,5.2vw,58px);line-height:1.06;letter-spacing:-.025em;font-weight:700;margin:0;max-width:15ch}
.mo p.sub{font-size:18px;color:var(--phu);margin:22px 0 0;max-width:56ch}
.mo .hd{display:flex;flex-wrap:wrap;gap:12px;margin-top:30px}.mo small{display:block;color:var(--phu);font-size:13.5px;margin-top:14px}
.the{background:var(--khoi);border:1px solid var(--vien);border-radius:20px;padding:20px;box-shadow:0 30px 80px -30px rgba(0,0,0,.6)}
.the .nhan{font-size:13px;color:var(--phu)}.the .lenh{font-weight:600;font-size:16px;margin:2px 0 14px}
.kl{display:flex;gap:12px;align-items:center;border-radius:14px;padding:12px 14px;background:color-mix(in srgb,var(--lo) 12%,var(--khoi));
 border:1px solid color-mix(in srgb,var(--lo) 45%,var(--vien))}
.kl i{flex:none;width:36px;height:36px;border-radius:50%;background:var(--lo);color:#1d0707;display:grid;place-items:center;font-style:normal;font-weight:700}
.kl b{display:block;font-size:18px}.kl span{color:var(--phu);font-size:13.5px}
.the ul{list-style:none;margin:12px 0 0;padding:0;display:grid;gap:8px}
.the li{display:grid;grid-template-columns:24px minmax(0,1fr);gap:10px;padding:10px 12px;border-radius:12px;background:#132030}
.the li i{width:22px;height:22px;border-radius:7px;display:grid;place-items:center;font-style:normal;font-weight:700;font-size:12px}
.the li.xau i{background:color-mix(in srgb,var(--lo) 25%,transparent);color:var(--lo)}
.the li.chu_y i{background:color-mix(in srgb,var(--vang) 25%,transparent);color:var(--vang)}
.the li.tot i{background:color-mix(in srgb,var(--lai) 22%,transparent);color:var(--lai)}
.the li b{display:block;font-size:14.5px;font-weight:600}.the li span{color:var(--phu);font-size:13px;line-height:1.45}
.the figcaption{color:var(--phu);font-size:12.5px;margin-top:12px}
/* hiệu ứng chỉ trượt nhẹ và sáng viền, không làm mờ: tab nền, xem trước link hay trình duyệt dừng hiệu ứng vẫn thấy đủ ba dòng kết luận */
@media(prefers-reduced-motion:no-preference){.the li{animation:hien .5s ease-out backwards}
 .the li:nth-child(1){animation-delay:.3s}.the li:nth-child(2){animation-delay:.6s}.the li:nth-child(3){animation-delay:.9s}}
@keyframes hien{from{transform:translateX(-8px);box-shadow:inset 3px 0 0 var(--dong)}}
section.phan{padding:64px 0;border-top:1px solid var(--vien)}
section.phan h2{font-size:clamp(26px,3.2vw,36px);line-height:1.15;letter-spacing:-.015em;margin:0;font-weight:700}
section.phan p.sub{color:var(--phu);margin:10px 0 0;max-width:60ch}
ol.lop{list-style:none;counter-reset:b;margin:36px 0 0;padding:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:28px}
ol.lop>li{counter-increment:b;position:relative;padding-top:56px}
ol.lop>li::before{content:counter(b);position:absolute;top:0;left:0;font-size:44px;line-height:1;font-weight:700;color:var(--dong)}
ol.lop .khi{color:var(--phu);font-size:14px}ol.lop h3{font-size:20px;margin:2px 0 10px;line-height:1.3}
ol.lop p{margin:0;color:#C9D2DA;font-size:15px}ol.lop .lk{margin-top:14px;font-size:14px;font-weight:600}
ol.lop .lk a{color:var(--dong);text-underline-offset:3px}ol.lop .lk span{color:var(--phu);font-weight:500}
p.canh{margin:36px 0 0;padding:16px 18px;border-left:3px solid var(--lo);background:#132030;border-radius:0 12px 12px 0;max-width:80ch;color:#C9D2DA}
.cung{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:40px;margin-top:32px;align-items:start}
.cung dl{margin:0;display:grid;gap:18px}.cung dt{font-weight:600;font-size:16.5px}.cung dd{margin:4px 0 0;color:var(--phu);font-size:15px}
.cung dd a{color:var(--dong);font-weight:600;text-underline-offset:3px}
.cung img{width:100%;height:auto;border-radius:16px;border:1px solid var(--vien);display:block}
ol.cai{margin:28px 0 0;padding-left:1.4em;display:grid;gap:12px;max-width:68ch}ol.cai li{padding-left:6px}ol.cai li::marker{color:var(--dong);font-weight:700}
.cai-hd{margin-top:28px}
p.tin{max-width:68ch;color:#C9D2DA;margin:14px 0 0}
section.tin-k{display:grid;grid-template-columns:180px minmax(0,1fr);gap:32px;align-items:center}
section.tin-k img{width:180px;height:180px;border-radius:28px;border:1px solid var(--vien);display:block}
@media(max-width:560px){section.tin-k{grid-template-columns:minmax(0,1fr);gap:20px}section.tin-k img{width:140px;height:140px}}
footer{border-top:1px solid var(--vien);padding:28px 0 48px;color:var(--phu);font-size:13.5px}footer p{margin:0 0 8px;max-width:90ch}
@media(max-width:900px){.mo{grid-template-columns:minmax(0,1fr);gap:36px;padding:32px 0 56px}ol.lop{grid-template-columns:minmax(0,1fr);gap:36px}
 .cung{grid-template-columns:minmax(0,1fr)}}
@media(max-width:560px){header.dau nav a.an,header.dau .nut{display:none}header.dau .ten{font-size:15px}.mo p.sub{font-size:16.5px}
 .mo .hd{flex-direction:column}.mo .hd .nut,.cai-hd .nut{width:100%}}
"""


def trang(lang: str = 'vi') -> str:
    c = CHU[lang]
    goc = '' if lang == 'vi' else '../'
    phong = _trang._phong_css().replace('url(/tinh/phong/', f'url({goc}tinh/phong/')
    t = c['the']
    dong = ''.join(f'<li class="{m}"><i>{"✕" if m == "xau" else "!" if m == "chu_y" else "✓"}</i><div><b>{escape(a)}</b><span>{escape(b)}</span></div></li>'
                   for m, a, b in t['dong'])
    lop = ''.join(f'<li><div class="khi">{escape(khi)}</div><h3>{escape(ten)}</h3><p>{escape(noi)}</p><div class="lk">'
                  + (f'<a href="{lk[1]}">{escape(lk[0])}</a>' if lk else f'<span>{escape(c["chi_co_ban_cai"])}</span>') + '</div></li>'
                  for khi, ten, noi, lk in c['lop'])
    cung = ''.join(f'<div><dt>{escape(a)}</dt><dd>{escape(b)}' + (f' <a href="{lk}">{escape(c["xem_demo"])}</a>' if lk else '') + '</dd></div>'
                   for a, b, lk in c['cung'])
    cai = ''.join(f'<li>{escape(x)}</li>' for x in c['cai_b'])
    anh = f'{goc}demo-cover.svg'
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(c['title'])}</title><meta name="description" content="{escape(c['mo_ta'])}"><meta name="theme-color" content="#0F1A24">
<link rel="icon" type="image/webp" href="{LOGO_NHO}"><meta property="og:type" content="website"><meta property="og:title" content="{escape(c['title'])}">
<meta property="og:description" content="{escape(c['mo_ta'])}"><meta property="og:image" content="{goc}logo.png"><meta name="twitter:card" content="summary">
<style>{phong}{CSS}</style></head><body>
<div class="khung"><header class="dau"><a class="ten" href="index.html"><img src="{LOGO_NHO}" alt="" width="44" height="44">{escape(TEN)}</a>
<nav aria-label="{'Liên kết' if lang == 'vi' else 'Links'}"><a class="an" href="tong-quan.html">Demo</a><a href="{c['doi'][1]}" hreflang="{'en' if lang == 'vi' else 'vi'}">{c['doi'][0]}</a>
<a class="nut chinh" href="{KHO}#readme" rel="noopener">{escape(c['cai'])}</a></nav></header>
<main><section class="mo"><div><h1>{escape(c['h1'])}</h1><p class="sub">{escape(c['sub'])}</p>
<div class="hd"><a class="nut chinh" href="tong-quan.html">{escape(c['thu'])}</a><a class="nut phu" href="{KHO}#readme" rel="noopener">{escape(c['cai'])}</a></div>
<small>{escape(c['yeu_cau'])}</small></div>
<figure class="the" style="margin:0" aria-label="{escape(t['nhan'])}"><div class="nhan">{escape(t['nhan'])}</div><div class="lenh">{escape(t['lenh'])}</div>
<div class="kl"><i aria-hidden="true">✕</i><div><b>{escape(t['kl'])}</b><span>{escape(t['kl_noi'])}</span></div></div><ul>{dong}</ul>
<figcaption>{escape(t['chu_thich'])}</figcaption></figure></section>
<section class="phan"><h2>{escape(c['lop_h2'])}</h2><p class="sub">{escape(c['lop_sub'])}</p><ol class="lop">{lop}</ol>
<p class="canh">{escape(c['canh_bao'])}</p></section>
<section class="phan"><h2>{escape(c['cung_h2'])}</h2><div class="cung"><dl>{cung}</dl>
<a href="tong-quan.html"><img src="{anh}" alt="{escape(c['anh_alt'])}" loading="lazy" width="1440" height="900"></a></div></section>
<section class="phan"><h2>{escape(c['cai_h2'])}</h2><ol class="cai">{cai}</ol>
<div class="cai-hd"><a class="nut chinh" href="{KHO}#readme" rel="noopener">{escape(c['tai'])}</a></div></section>
<section class="phan tin-k"><img src="{goc}logo.png" alt="{escape(TEN)}" width="630" height="630" loading="lazy">
<div><h2>{escape(c['tin_h2'])}</h2><p class="tin">{escape(c['tin'])}</p></div></section></main>
<footer><p>{escape(c['mien_tru'])}</p><p>{escape(TEN)} · <a href="{KHO}" rel="noopener">GitHub</a></p></footer></div></body></html>"""
