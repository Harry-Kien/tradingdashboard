"""Trang Bắt đầu sử dụng (/bat-dau, 26/11/2026): cho người mới cài bản chia sẻ thấy ngay webapp đã nối MT5 chưa, đang đọc tài khoản nào,
và nên thử gì tiếp theo. Mọi bước tự kiểm bằng dữ liệu thật của chính webapp (/api/tinh-trang, /api/tai-khoan), không đoán.
Chỉ đọc: không đặt lệnh, không gửi gì ra ngoài."""
from __future__ import annotations

from html import escape

from . import lam_quen, trang, vo_app

CSS = r"""
main.rong{max-width:1080px}.bd-refresh{font:600 13px inherit;min-height:40px;padding:8px 14px;border:1px solid var(--line);border-radius:10px;color:var(--ink);background:var(--card2);cursor:pointer;margin-top:16px}.bd-refresh:disabled{opacity:.5;cursor:wait}.bd-refresh:focus-visible{outline:2px solid var(--series);outline-offset:3px}
.bd-top h1{margin:0}.bd-top p{margin:6px 0 0;color:var(--ink2);max-width:760px;line-height:1.55}
.bd-tom{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0 6px}
.bd-tom span{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:13px;font-weight:600;background:var(--card)}
.bd-ds{list-style:none;margin:14px 0 0;padding:0;display:grid;gap:12px;counter-reset:b}
.bd-ds>li{display:grid;grid-template-columns:38px 1fr;gap:14px;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px}
.bd-ds>li[data-tt=tot]{border-color:color-mix(in srgb,var(--gain) 45%,var(--line))}
.bd-ds>li[data-tt=can]{border-color:color-mix(in srgb,var(--warn) 55%,var(--line));background:color-mix(in srgb,var(--warn) 6%,var(--card))}
.bd-so{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;font-weight:800;font-size:15px;background:var(--card2);border:1px solid var(--line);color:var(--ink2)}
li[data-tt=tot] .bd-so{background:var(--gain);border-color:var(--gain);color:#06140c}
li[data-tt=can] .bd-so{background:var(--warn);border-color:var(--warn);color:#1d1400}
.bd-ds h2{font-size:16px;margin:4px 0 6px}.bd-ds p{margin:4px 0;color:var(--ink2);line-height:1.55;font-size:14px}
.bd-ds .bd-kq{margin:8px 0 2px;font-size:14px;color:var(--ink)}
.bd-ds .bd-kq b{font-variant-numeric:tabular-nums}
.bd-nut{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.bd-nut a{display:inline-flex;align-items:center;min-height:36px;padding:0 14px;border-radius:10px;border:1px solid var(--line);background:var(--card2);color:var(--ink);font-weight:700;font-size:13px;text-decoration:none}
.bd-nut a.chinh{background:var(--series);border-color:var(--series);color:var(--btn-ink)}
.bd-nut a:focus-visible{outline:2px solid var(--series);outline-offset:2px}
.bd-meo{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:8px;margin:10px 0 0;padding:0;list-style:none}
.bd-meo li{font-size:13px;color:var(--ink2);line-height:1.5;padding:8px 10px;border-radius:10px;background:var(--card2)}
.bd-meo kbd{font:11.5px ui-monospace,Consolas,monospace;border:1px solid var(--line);border-radius:4px;padding:1px 5px;color:var(--ink)}
.bd-can{margin:8px 0 0;padding-left:18px;font-size:13.5px;line-height:1.55;color:var(--ink2)}.bd-can b{color:var(--ink)}
@media(max-width:640px){.bd-ds>li{grid-template-columns:1fr;padding:14px}.bd-so{width:30px;height:30px}}
"""

JS = r"""
(()=>{const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const dat=(id,tt,kq)=>{const li=$('#'+id);if(!li)return;li.dataset.tt=tt;const o=li.querySelector('.bd-kq');if(o&&kq!=null)o.innerHTML=kq};
const so=v=>v==null?'—':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:2});
async function json(u){const c=new AbortController(),t=setTimeout(()=>c.abort(),12000);try{const r=await fetch(u,{cache:'no-store',signal:c.signal});if(!r.ok)throw new Error('HTTP '+r.status);return await r.json()}finally{clearTimeout(t)}}
let busy=false;
async function tai(){if(busy||document.hidden)return;busy=true;$('#bd-refresh').disabled=true;
const source=d=>dispatchEvent(new CustomEvent('lq-source',{detail:d}));
await Promise.allSettled([
(async()=>{try{const st=await json('/api/tinh-trang');if(!Array.isArray(st.muc)||!st.muc.length)throw Error();
 const TEN={gia:'Giá trực tiếp từ MT5',ai:'Hỏi AI',tg:'Nhóm Telegram',sl:'Sao lưu toàn bộ'};
 const ds=st.muc,gia=ds.find(m=>m.id==='mt5-price'),d=st.dem||{};
 $('#bd-tom').innerHTML=`<span>✓ ${d.tot||0} mục tốt</span><span>! ${d.chu_y||0} mục nên xem</span><span>✕ ${d.loi||0} lỗi</span>`;
 source({mt5:gia?.ket_noi===true});
 if(gia?.ket_noi===true)dat('b-mt5',gia.gia_moi===true?'tot':'can','<b>Đã nối MT5.</b> '+esc(gia.chi_tiet)+(gia.lam?' '+esc(gia.lam):''));
 else dat('b-mt5','can','<b>Chưa nối được MT5.</b> '+esc(gia?.chi_tiet||'')+(gia?.lam?' '+esc(gia.lam):''));
 const extra=[TEN.ai,TEN.tg,TEN.sl].map(name=>ds.find(m=>m.ten===name)).filter(Boolean);
 $('#b-them .bd-kq').innerHTML=extra.length?`<ul class="bd-can">${extra.map(m=>`<li><b>${esc(m.ten)}:</b> ${esc(m.chi_tiet)}</li>`).join('')}</ul>`:'';
 }catch(e){source({mt5:null});dat('b-mt5','can','Chưa đọc được trạng thái kết nối. Thử kiểm tra lại hoặc mở Cài đặt.');$('#bd-tom').textContent='Chưa tải đủ tình trạng hệ thống.'}})(),
(async()=>{try{const tk=await json('/api/tai-khoan');source({account:tk.san_sang===true});
 if(tk.san_sang===true)dat('b-tk','tot',`<b>${esc(tk.loai)}</b> · tài khoản ${esc(tk.so)} · ${esc(tk.may_chu)} · vốn <b>${so(tk.von)} ${esc(tk.tien)}</b> · đòn bẩy 1:${esc(tk.don_bay)} · ${(tk.lenh||[]).length} lệnh đang mở`);
 else dat('b-tk','can','<b>Chưa đọc được tài khoản.</b> '+esc(tk.ly_do||''))
 }catch(e){source({account:null});dat('b-tk','can','Chưa đọc được tài khoản. Thử cập nhật lại sau khi kiểm tra MT5.')}})()
]);busy=false;$('#bd-refresh').disabled=false}
$('#bd-refresh').addEventListener('click',tai);tai();setInterval(tai,15000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)tai()});
try{localStorage.setItem('so-bat-dau','1')}catch(e){}})();
"""


def trang_bat_dau(ten: str) -> str:
    buoc = [
        ('b-mt5', 'Nối MetaTrader 5', '<p>Mở MetaTrader 5 trên máy này và đăng nhập tài khoản của bạn. Webapp tự tìm MT5 và đọc giá theo từng tick. Máy mở '
         'nhiều MT5 thì chọn đúng MT5 ở trang Cài đặt.</p>', [('/cai-dat', 'Mở Cài đặt', 0)]),
        ('b-tk', 'Xem tài khoản của bạn', '<p>Webapp chỉ đọc tài khoản đang đăng nhập trong MT5: vốn, lệnh đang mở, lịch sử. Số tài khoản được che, '
         'dữ liệu này được đọc từ MT5 trên máy của bạn.</p>', [('/tai-khoan', 'Tài khoản MT5', 1), ('/cac-tai-khoan', 'Thêm tài khoản khác', 0)]),
        ('b-bd', 'Dùng biểu đồ', '<p>Nến cập nhật theo từng tick, đủ khung từ M1 tới D1, chỉ báo, công cụ vẽ và các phương pháp phân tích điểm vào. '
         'Hình vẽ, chỉ báo và cảnh báo giá được tổ chức riêng theo từng mã; xem trạng thái lưu và đồng bộ ngay trên biểu đồ.</p>'
         '<ul class="bd-meo"><li><b>Bấm chuột phải</b> vào biểu đồ (điện thoại: giữ ngón tay): chép giá, đặt cảnh báo, vẽ ngay, thử lệnh, tải ảnh.</li>'
         '<li><kbd>Alt</kbd>+<kbd>H</kbd> đường ngang, <kbd>Alt</kbd>+<kbd>V</kbd> đường dọc, <kbd>Alt</kbd>+<kbd>A</kbd> cảnh báo giá, '
         '<kbd>Alt</kbd>+<kbd>S</kbd> tải ảnh.</li><li><kbd>1</kbd>–<kbd>7</kbd> đổi khung, <kbd>F</kbd> toàn màn hình, <kbd>Ctrl</kbd>+<kbd>Z</kbd> / '
         '<kbd>Ctrl</kbd>+<kbd>Y</kbd> hoàn tác và làm lại hình vẽ.</li><li>Bấm đúp vào ghi chú để sửa chữ; bấm đúp chỗ trống để về nến mới nhất.</li></ul>',
         [('/bieu-do', 'Mở Biểu đồ', 1), ('/da-khung', 'Nhiều biểu đồ', 0), ('/thi-truong', 'Bảng giá trực tiếp', 0)]),
        ('b-cc', 'Kiểm tra trước khi vào lệnh', '<p>Trước mỗi lệnh: tính khối lượng theo % rủi ro, xem tin mạnh sắp ra, spread và lỗ trong ngày. Sau đó '
         'xem lại thói quen nào đang tốn tiền.</p>',
         [('/kiem-lenh', 'Kiểm tra lệnh', 1), ('/ke-hoach', 'Kế hoạch vốn', 0), ('/ky-luat', 'Kỷ luật giao dịch', 0), ('/hieu-suat', 'Phân tích hiệu suất', 0)]),
        ('b-them', 'Tính năng tùy chọn', '<p>Hỏi AI, nhóm Telegram và sao lưu là các tính năng tùy chọn. Xem trạng thái bên dưới và cấu hình khi cần.</p>',
         [('/telegram', 'Nhóm Telegram', 0), ('/sao-luu', 'Sao lưu', 0), ('/hoc-giao-dich', 'Học giao dịch', 0)]),
    ]
    li = ''.join(
        f'<li id="{i}" data-tt=""><span class="bd-so" aria-hidden="true">{n + 1}</span><div><h2>{t}</h2>{mo}<div class="bd-kq" aria-live="polite"></div>'
        '<div class="bd-nut">' + ''.join(f'<a href="{h}"{" class=chinh" if c else ""}>{x}</a>' for h, x, c in nut) + '</div></div></li>'
        for n, (i, t, mo, nut) in enumerate(buoc))
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.KHOI_TAO_NEN}{trang.BIEU_TUONG}<title>Bắt đầu sử dụng · {escape(ten)}</title><style>{trang.CSS}{CSS}{lam_quen.CSS}</style></head><body>',
        trang.thanh_dau(ten, 'bat-dau', '<button id="theme" type="button">Nền tối</button>') + '<main class="rong">',
        '<div class="bd-top"><h1>Bắt đầu sử dụng</h1><p>Năm bước để dùng webapp với tài khoản MT5 của chính bạn. Kết nối và tài khoản tự kiểm bằng dữ liệu thật '
        'trên máy này; bước thử công cụ do bạn tự xác nhận. Webapp chỉ đọc MT5, không bao giờ đặt lệnh.</p></div>',
        '<button type="button" class="bd-refresh" id="bd-refresh">Kiểm tra lại kết nối ↻</button>' + lam_quen.khoi(),
        '<div class="bd-tom" id="bd-tom" aria-live="polite"><span>Đang kiểm tình trạng…</span></div>',
        f'<ol class="bd-ds">{li}</ol>',
        '<footer>' + escape(trang.mien_tru()) + f'</footer></main><script>{trang.JS}</script><script>{lam_quen.JS}</script><script>{JS}</script>'
        f'<script>{vo_app.JS_BAT_DAU}</script></body></html>'])                # app: báo khi máy còn chạy webapp bản zip ở cổng 8765
