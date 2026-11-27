"""Trang Nhiều biểu đồ (/da-khung, 26/11/2026): 2, 4 hoặc 1+3 biểu đồ trên một màn hình. Mỗi ô chọn mã và khung riêng (ví dụ XAUUSD, EURUSD,
US30, BTC cùng lúc), hoặc bật Đồng bộ mã để xem một mã ở nhiều khung (mặc định M5, M15, H1, H4). Đồng bộ con trỏ và đồng bộ thời gian giữa các ô,
dòng tóm tắt xu hướng EMA20/EMA50 của từng ô, bấm đúp một ô để mở ô đó ở trang Biểu đồ.

Thời gian thực mà không ngốn kết nối: trình duyệt chỉ cho mỗi máy chủ khoảng 6 kết nối, nên trang KHÔNG mở luồng riêng mà dùng luồng giá dùng chung
của webapp (window.TT trong thi_truong_trang.JS_CHUNG: một tab giữ đúng một kết nối /api/thi-truong/luong cho mọi mã và chuyển giá cho các tab khác).
Mỗi gói giá cập nhật nến đang chạy của các ô có mã đó; khi một ô sang nến mới thì tải lại ô đó từ /api/gia cho khớp MT5, và cứ mỗi phút tải lại mọi ô.
Chỉ đọc: không đặt lệnh."""
from __future__ import annotations

from html import escape

from . import da_khung_giao_dien, da_khung_realtime, thi_truong_trang, trang

CSS = r"""
main.rong{max-width:none;padding-left:16px;padding-right:16px}
.dk-top{display:flex;flex-wrap:wrap;align-items:flex-end;gap:10px 18px;justify-content:space-between}
.dk-top h1{margin:0}.dk-top p{margin:4px 0 0;color:var(--ink2);max-width:820px;font-size:14px;line-height:1.5}
.dk-thanh{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:14px 0 10px}
.dk-seg{display:inline-flex;gap:3px;background:var(--card2);border:1px solid var(--line);border-radius:11px;padding:3px;flex-wrap:wrap}
.dk-seg button{min-height:32px;padding:0 12px;border:0;border-radius:8px;background:none;color:var(--ink2);font:700 13px/1 inherit;font-family:inherit;cursor:pointer}
.dk-seg button[aria-pressed=true]{background:color-mix(in srgb,var(--series) 18%,transparent);color:var(--ink)}
.dk-seg button:focus-visible,.dk-o select:focus-visible{outline:2px solid var(--series);outline-offset:1px}
.dk-song{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;color:var(--ink2);border:1px solid var(--line);border-radius:999px;padding:5px 11px;background:var(--card)}
.dk-song i{width:8px;height:8px;border-radius:50%;background:var(--mute)}.dk-song.ok i{background:var(--gain)}.dk-song.loi i{background:var(--loss)}
.dk-tom{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;margin:0 0 10px;font-size:13px;color:var(--ink2);min-height:26px}
.dk-tom .chip{display:inline-flex;gap:5px;align-items:center;border:1px solid var(--line);border-radius:999px;padding:3px 10px;font-weight:700;color:var(--ink)}
.dk-tom .len{color:var(--gain)}.dk-tom .xuong{color:var(--loss)}.dk-tom b{color:var(--ink)}
.dk-luoi{display:grid;gap:10px;grid-template-columns:repeat(2,minmax(0,1fr))}
.dk-luoi[data-bo="1+3"]{grid-template-columns:minmax(0,2fr) minmax(0,1fr)}
.dk-luoi[data-bo="1+3"] .dk-o:first-child{grid-row:1/4}
.dk-o{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;min-width:0}
.dk-o header{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;padding:6px 10px;border-bottom:1px solid var(--line);font-size:13px;min-height:42px}
.dk-o header select{min-height:30px;border-radius:8px;border:1px solid var(--line);background:var(--card2);color:var(--ink);font:700 13px/1 inherit;font-family:inherit;padding:0 6px;max-width:160px}
.dk-o .dk-gia{font-variant-numeric:tabular-nums;font-size:14px}.dk-o .dk-bd{color:var(--ink2);font-variant-numeric:tabular-nums;font-size:12px}
.dk-o .len{color:var(--gain)}.dk-o .xuong{color:var(--loss)}.dk-o .dk-xu{font-weight:700;font-size:12.5px}
.dk-o .dk-mo{margin-left:auto;color:var(--ink2);text-decoration:none;font-size:12px;border:1px solid var(--line);border-radius:8px;padding:4px 8px;white-space:nowrap}
.dk-o .dk-mo:hover{color:var(--ink)}.dk-o .dk-mo::before{content:'↗ '}
.dk-o{container-type:inline-size}@container (max-width:640px){.dk-o .dk-mo span{display:none}.dk-o .dk-mo::before{content:'↗'}}   /* ô hẹp: chỉ còn mũi tên, đầu ô không xuống dòng */
.dk-c{position:relative;height:calc((100vh - 300px)/2);min-height:250px}
.dk-luoi[data-bo="2"] .dk-c{height:calc(100vh - 300px);min-height:360px}
.dk-luoi[data-bo="1+3"] .dk-o:first-child .dk-c{height:calc(100vh - 300px);min-height:420px}
.dk-luoi[data-bo="1+3"] .dk-o:not(:first-child) .dk-c{height:calc((100vh - 300px)/3 - 50px);min-height:170px}
.dk-cho{padding:20px;color:var(--ink2)}
.dk-ghi{margin:12px 0 0;color:var(--ink2);font-size:12.5px;line-height:1.55}
@media(max-width:900px){.dk-luoi,.dk-luoi[data-bo="1+3"]{grid-template-columns:1fr}.dk-luoi[data-bo="1+3"] .dk-o:first-child{grid-row:auto}
 .dk-c,.dk-luoi[data-bo] .dk-c,.dk-luoi[data-bo="1+3"] .dk-o .dk-c{height:300px;min-height:300px}}
/* Máy tính (27/11/2026): tiêu đề và hàng nút gộp một hàng, đoạn mô tả thu vào nút "i", lưới biểu đồ cao vừa phần còn lại của cửa sổ nên màn hình
   đầu là biểu đồ. --tru = mọi thứ phía trên lưới + lề dưới; lưới có chiều cao cố định, các hàng chia đều, vùng nến của mỗi ô lấp phần còn lại
   (đầu ô có xuống dòng ở ô hẹp cũng không làm lưới tràn màn hình). */
.dk-help{position:relative;flex:none}.dk-help summary{display:flex;align-items:center;justify-content:center;width:24px;height:24px;border:1px solid var(--line);border-radius:50%;color:var(--ink2);cursor:pointer;font-weight:700;list-style:none}.dk-help summary::-webkit-details-marker{display:none}.dk-help summary:focus-visible{outline:2px solid var(--series)}
.dk-help-content{position:absolute;z-index:12;left:0;top:32px;width:min(480px,calc(100vw - 55px));max-height:55vh;overflow:auto;padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--card);box-shadow:0 10px 30px #0005;font-size:13px;line-height:1.6}.dk-top .dk-help-content p{display:block;position:static;width:auto;max-width:none;margin:0 0 10px;padding:0;border:0;background:none;box-shadow:none;color:var(--ink2)}.dk-help-content p:last-child{margin-bottom:0}
.dk-notes{margin-top:12px;color:var(--ink2);font-size:12px;line-height:1.6}.dk-notes summary{cursor:pointer;padding:5px 0}.dk-notes p{margin:6px 0}.dk-notes .dk-ghi{margin:6px 0;font-size:12px}
@media(min-width:981px) and (min-height:600px){
main.rong{--tru:calc(var(--nv-h,56px) + 112px);display:grid;grid-template-columns:minmax(0,1fr) auto;column-gap:18px;align-items:center;padding-top:10px;padding-bottom:24px}
main.rong>*{grid-column:1/-1}main.rong>.dk-top{grid-column:1;min-width:0;flex-wrap:nowrap;align-items:center;justify-content:flex-start;gap:10px;position:relative}
main.rong>.dk-thanh{grid-column:2;margin:0;justify-content:flex-end;flex-wrap:nowrap}
.dk-top>div{display:flex;align-items:center;gap:8px;flex:none}.dk-song{min-width:0}.dk-song span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.dk-top h1{font-size:18px;white-space:nowrap}
.dk-tom{margin:8px 0}
.dk-luoi{height:calc(100dvh - var(--tru));min-height:420px;grid-auto-rows:minmax(0,1fr)}.dk-luoi .dk-o{min-height:0}
.dk-luoi .dk-c,.dk-luoi[data-bo] .dk-o .dk-c{height:auto;flex:1 1 0;min-height:0}
}
"""

CSS += da_khung_giao_dien.CSS

JS = da_khung_giao_dien.JS


def trang_da_khung(ten: str) -> str:
    bo = ''.join(f'<button type="button" data-v="{v}">{t}</button>' for v, t in (('2', '2 biểu đồ'), ('4', '4 biểu đồ'), ('1+3', '1 lớn + 3 nhỏ')))
    dong = ''.join(f'<button type="button" id="{i}" title="{ti}">{t}</button>' for i, t, ti in (
        ('dk-dma', 'Đồng bộ mã', 'Đổi mã ở một ô thì mọi ô đổi theo'), ('dk-dkh', 'Đồng bộ khung', 'Đổi khung ở một ô thì mọi ô đổi theo'),
        ('dk-dtro', 'Đồng bộ con trỏ', 'Rê chuột ở một ô: mọi ô hiện cùng thời điểm, cùng mức giá và bảng giá của nến tại đó'),
        ('dk-dtg', 'Liên kết thu phóng', 'Bật: kéo hoặc phóng to một ô thì các ô khác theo cùng khoảng thời gian. Tắt: mỗi ô thu phóng độc lập')))
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.KHOI_TAO_NEN}{trang.BIEU_TUONG}<title>Nhiều biểu đồ · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'da-khung', '<button id="theme" type="button">Nền tối</button>') + '<main class="rong">',
        '<div class="dk-top"><div><h1>Nhiều biểu đồ</h1><details class="dk-help"><summary aria-label="Hướng dẫn nhiều biểu đồ" title="Hướng dẫn nhiều biểu đồ">?</summary><div class="dk-help-content">'
        '<p>Chọn mã và khung riêng cho từng ô bằng Tách từng ô. Bật Đồng bộ mã hoặc Đồng bộ khung khi muốn các ô đổi cùng nhau.</p>'
        '<p>Giữ khung nhìn giúp nền lưới và trục đứng yên khi giá đổi. Bấm Hiện tại hoặc Giá ngoài vùng để về nến mới.</p>'
        '<p>Đồng bộ con trỏ: rê chuột ở một ô thì mọi ô hiện cùng thời điểm; góc trên mỗi ô ghi giá Mở, Cao, Thấp, Đóng của nến khung đó tại thời điểm ấy, và với ô cùng mã thì giá đang trỏ nằm trên đỉnh, dưới đáy hay trong nến. Bấm (không kéo) để ghim điểm: mọi ô có vạch dọc và đường giá ghim, bảng giữ nguyên và ghi quãng giá đã đi từ điểm ghim tới giá hiện tại; Về điểm ghim cuộn mọi ô tới đó, Bỏ ghim hoặc phím Esc để bỏ.</p>'
        '<p>Liên kết thu phóng: bật thì kéo hoặc phóng to một ô, các ô khác đi theo, mép phải cùng một thời điểm. Chọn kiểu bên cạnh nút: Cùng số nến (mặc định) để khung lớn cũng hiện ngần ấy nến nên vẫn thấy nhiều nến; Cùng khoảng thời gian để mọi ô xem đúng một quãng giờ; Chỉ cuộn theo nhau để mỗi ô giữ độ phóng riêng. Ô thiếu nến cũ bắt đầu ở nến đầu tiên của nó thay vì để trống, và trục giá tự co cho vừa nến. Tắt thì mỗi ô thu phóng riêng.</p>'
        '<p>Một tick là một lần MT5 cập nhật giá Bid/Ask. Trang hiển thị các thay đổi máy chủ nhận được, không bảo đảm nhận đủ mọi tick của sàn hoặc không có độ trễ.</p>'
        '</div></details></div>'
        '<span id="dk-song" class="dk-song"><i></i><span>Đang nối…</span></span></div>',
        f'<div class="dk-thanh"><div class="dk-seg" id="dk-bo" role="group" aria-label="Bố cục">{bo}</div>'
        f'<div class="dk-seg" role="group" aria-label="Đồng bộ">{dong}</div></div>',
        '<div class="dk-tom" id="dk-tom" aria-live="polite"></div>',
        '<div class="dk-luoi" id="dk-luoi" data-bo="4"></div>',
        '<details class="dk-notes"><summary>Nguồn dữ liệu và lưu ý</summary><p class="dk-ghi">Xu hướng ở đây chỉ so EMA20 với EMA50 trên nến của từng ô, để nhìn nhanh các ô có cùng chiều không; đây là mô tả, không phải '
        'tín hiệu vào lệnh. Biểu đồ vẽ bằng <a href="https://www.tradingview.com/lightweight-charts/" target="_blank" rel="noopener">TradingView Lightweight Charts™</a>. '
        'Copyright (c) 2026 TradingView, Inc.</p>',
        '<p>' + escape(trang.mien_tru()) + '</p></details></main>'
        f'<script src="/tinh/lightweight-charts.js"></script><script>{trang.JS}</script><script>{thi_truong_trang.JS_CHUNG}</script><script>{da_khung_realtime.JS}</script><script>{JS}</script></body></html>'])
