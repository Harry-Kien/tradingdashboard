"""Tiến độ làm quen lưu cục bộ: dữ liệu nối tự kiểm, thao tác học do người dùng xác nhận."""

CSS = r"""
.lq{padding:18px 20px;border:1px solid var(--line);border-radius:16px;background:var(--card);margin:18px 0 22px}
.lq [hidden]{display:none!important}.lq-head{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap}
.lq h2{font-size:17px;margin:0}.lq-count{font-size:12px;color:var(--series);font-weight:700;white-space:nowrap}.lq p{color:var(--ink2);font-size:12px;line-height:1.6;margin:8px 0 12px}
.lq-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.lq-step{border:1px solid var(--line);border-radius:10px;padding:12px;min-width:0}.lq-step[data-ok=true]{border-color:color-mix(in srgb,var(--series) 45%,var(--line))}
.lq-step b{font-size:12px;display:block;margin-bottom:6px}.lq-step small{display:block;color:var(--mute);font-size:11px;line-height:1.5;min-height:32px}.lq-step a{color:var(--series);font-size:12px;min-height:28px;display:inline-flex;align-items:center;margin-top:5px;text-decoration:none}.lq label{display:flex;gap:7px;align-items:flex-start;font-size:11.5px;color:var(--ink2);cursor:pointer;margin-top:6px;line-height:1.5}.lq input{accent-color:var(--series);flex:none;width:16px;height:16px;margin:1px 0}
.lq a:focus-visible,.lq input:focus-visible{outline:2px solid var(--series);outline-offset:3px}.lq progress{width:100%;height:5px;display:block;margin-top:14px;accent-color:var(--series)}.lq progress::-webkit-progress-bar{background:var(--track);border-radius:5px}.lq progress::-webkit-progress-value{background:var(--series);border-radius:5px}.lq .lq-save{color:var(--warn);margin-bottom:0}
@media(max-width:800px){.lq-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.lq{padding:16px}.lq-step{padding:10px}}
"""

JS = r"""
(()=>{const root=document.querySelector('[data-lq]');if(!root)return;
const KEY=window.hgrKey?window.hgrKey('so-lam-quen-v1'):'demo:so-lam-quen-v1',checks=[...root.querySelectorAll('[data-lq-confirm]')];let saved={},facts={mt5:null,account:null};
try{const x=JSON.parse(localStorage.getItem(KEY)||'{}');if(x&&typeof x==='object'&&!Array.isArray(x))saved=x}catch(e){}
const panel=root.closest('details');
function draw(){for(const name of ['mt5','account']){const el=root.querySelector('[data-lq-step="'+name+'"]'),ok=facts[name]===true;el.dataset.ok=String(ok);el.querySelector('small').textContent=facts[name]===null?'Chưa kiểm tra kết nối':ok?'Đã xác minh bằng dữ liệu hiện tại':'Chưa xác minh được; xem hướng dẫn bên dưới'}
checks.forEach(c=>{c.checked=saved[c.dataset.lqConfirm]===true;c.closest('.lq-step').dataset.ok=String(c.checked)});
const n=Number(facts.mt5===true)+Number(facts.account===true)+checks.filter(c=>c.checked).length;root.querySelector('progress').value=n;root.querySelector('.lq-count').textContent=n+' / 4';if(panel){const badge=panel.querySelector('[data-lq-badge]');if(badge)badge.textContent=n+' / 4'}root.querySelector('[data-lq-next]').textContent=n===4?'Bạn đã hoàn tất các bước làm quen. Các trạng thái kết nối vẫn được kiểm tra lại.':'Hai bước đầu tự kiểm từ dữ liệu; hai bước sau do bạn xác nhận đã thử. Các tính năng tùy chọn không bắt buộc.'}
checks.forEach(c=>c.addEventListener('change',()=>{saved={chart:root.querySelector('[data-lq-confirm="chart"]').checked,risk:root.querySelector('[data-lq-confirm="risk"]').checked};try{localStorage.setItem(KEY,JSON.stringify(saved))}catch(e){root.querySelector('.lq-save').hidden=false}draw()}));
addEventListener('lq-source',e=>{const d=e.detail||{};for(const key of ['mt5','account'])if(Object.hasOwn(d,key))facts[key]=typeof d[key]==='boolean'?d[key]:null;draw()});
addEventListener('storage',e=>{if(e.key!==KEY)return;try{const x=JSON.parse(e.newValue||'{}');saved=x&&typeof x==='object'&&!Array.isArray(x)?x:{}}catch(x){saved={}}draw()});draw();})();
"""


def khoi() -> str:
    return '''<section class="lq" data-lq aria-label="Tiến độ làm quen"><div class="lq-head"><h2>Bắt đầu vững vàng</h2><span class="lq-count" aria-live="polite">0 / 4</span></div>
<p data-lq-next>Hai bước đầu tự kiểm từ dữ liệu; hai bước sau do bạn xác nhận đã thử. Các tính năng tùy chọn không bắt buộc.</p>
<div class="lq-grid"><div class="lq-step" data-lq-step="mt5"><b>1. Kết nối giá MT5</b><small>Chưa kiểm tra kết nối</small><a href="/bat-dau#b-mt5">Kiểm tra kết nối →</a></div>
<div class="lq-step" data-lq-step="account"><b>2. Đọc tài khoản</b><small>Chưa kiểm tra kết nối</small><a href="/tai-khoan">Xem tài khoản →</a></div>
<div class="lq-step" data-lq-step="chart"><b>3. Làm quen biểu đồ</b><small>Tự xác nhận sau khi thử</small><a href="/bieu-do">Mở biểu đồ →</a><label><input type="checkbox" data-lq-confirm="chart">Tôi đã thử đổi mã và khung thời gian</label></div>
<div class="lq-step" data-lq-step="risk"><b>4. Thử kiểm tra lệnh</b><small>Tự xác nhận sau khi thử</small><a href="/kiem-lenh">Mở kiểm tra lệnh →</a><label><input type="checkbox" data-lq-confirm="risk">Tôi đã thử nhập lệnh và đọc kết quả kiểm tra</label></div></div>
<progress value="0" max="4" aria-label="Tiến độ làm quen"></progress><p class="lq-save" hidden>Trình duyệt chưa lưu được tiến độ. Bạn vẫn có thể tiếp tục sử dụng.</p>
<noscript><p>Bật JavaScript để tự kiểm kết nối. Các liên kết hướng dẫn vẫn dùng được.</p></noscript></section>'''
