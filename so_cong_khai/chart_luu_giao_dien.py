"""Giao diện tài khoản chart và trạng thái lưu; không để mã phiên trong JavaScript."""
import base64
import json


def boot(nguoi=None, ma_vang='XAUUSDp'):
    data = base64.b64encode(json.dumps({'nguoi': nguoi, 'vang': ma_vang}, ensure_ascii=True).encode()).decode()
    return """(()=>{const b=JSON.parse(atob('""" + data + """'));window.HVD_CHU=b.nguoi;
window.HVD_MA=m=>m||b.vang;window.HVD_KHOA=m=>'so-ve:'+(b.nguoi?'u_'+b.nguoi.id:'khach')+':'+HVD_MA(m);
window.HVD_CB_KEY='so-cbcn1:'+(b.nguoi?'u_'+b.nguoi.id:'khach');
try{if((!b.nguoi||b.nguoi.chu)&&!localStorage.getItem(HVD_CB_KEY)){const old=localStorage.getItem('so-cbcn1');if(old)localStorage.setItem(HVD_CB_KEY,old)}}catch(e){}
window.HVD_CHO_VE=()=>{if(b.nguoi)return true;if(window.HVD_UI)HVD_UI.account();return false};})();"""


CSS = r"""
.hv-save{display:flex;align-items:center;gap:7px;flex-wrap:wrap;padding:7px 0;color:var(--mute);font-size:12px}
.hv-save [role=status]{flex:1;min-width:100px}.hv-save [data-state=error],.hv-save [data-state=conflict]{color:var(--loss)}
.hv-save button{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--ink);padding:6px 10px;border-radius:7px;min-height:32px;cursor:pointer}
.hv-save .hv-account{max-width:100%;overflow-wrap:anywhere}
.hv-health{font-size:12px;color:var(--mute);margin:0 0 8px}.hv-health summary{cursor:pointer;color:var(--ink2)}.hv-health p{margin:5px 0;line-height:1.5;overflow-wrap:anywhere}
.hv-dialog{background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:12px;padding:20px;width:400px;max-width:calc(100vw - 36px);box-sizing:border-box;max-height:85vh;overflow:auto;box-shadow:0 18px 70px #0006}
.hv-dialog::backdrop{background:#0008}.hv-dialog h3{margin:0 0 12px;font-size:17px}.hv-dialog p{font-size:13px;line-height:1.5;color:var(--mute)}
.hv-dialog label{display:block;font-size:13px;margin:10px 0}.hv-dialog input{display:block;box-sizing:border-box;width:100%;margin-top:5px;padding:10px;border:1px solid var(--line);border-radius:7px;background:var(--bg);color:var(--ink);font:inherit}
.hv-dialog [hidden]{display:none!important}
.hv-dialog button{background:var(--card);color:var(--ink);border:1px solid var(--line);padding:9px 12px;border-radius:7px;cursor:pointer;font:inherit;margin:4px 5px 4px 0}
.hv-dialog button.primary{background:var(--series);color:#111;font-weight:700}.hv-dialog [role=alert]{font-size:13px;color:var(--loss);white-space:pre-wrap}
.hv-dialog .hv-revision{display:flex;gap:8px;align-items:center;border-bottom:1px solid var(--line);padding:5px 0;font-size:12px}.hv-revision span{flex:1}
html.anh .hv-save{display:none!important}@media(max-width:640px){.hv-save{gap:5px}.hv-save button{min-height:36px;padding:6px 8px}.hv-dialog{padding:16px}}
"""

JS = r"""
(()=>{const G=window.BDMN,st=document.querySelector('.stage');if(!G||!st||document.documentElement.classList.contains('anh'))return;
const U=window.HVD_CHU,esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const bar=document.createElement('div');bar.className='hv-save';bar.innerHTML='<button type="button" class="hv-account"></button><span role="status" aria-live="polite"></span><button type="button" class="hv-now">Lưu ngay</button><button type="button" class="hv-history">Lịch sử bản vẽ</button>';st.before(bar);
bar.querySelector('.hv-account').textContent=U?'Tài khoản chart: '+U.ten:'Đăng nhập để vẽ và lưu chart';
const badge=bar.querySelector('[role=status]');let dlg=null;
const templateStatus=document.createElement('button');templateStatus.type='button';templateStatus.className='hv-templates';templateStatus.hidden=!U;templateStatus.textContent='Mẫu chỉ báo';bar.appendChild(templateStatus);
templateStatus.onclick=()=>{if(!window.MCB)return;if(templateStatus.dataset.state==='conflict')MCB.showConflict();else MCB.gui()};
const health=document.createElement('details');health.className='hv-health';health.innerHTML='<summary>Chất lượng realtime</summary><p class="hv-health-data"></p><p>Đo thời gian JavaScript từ lúc nhận tick tới lúc cập nhật nến, gồm chờ khung hình; không phải độ trễ từ sàn hay thời gian màn hình hiển thị. Chỉ báo tùy chỉnh cập nhật có gom nhịp để giữ thao tác mượt. Nến đang chạy và chỉ báo của nến đó có thể đổi.</p>';bar.after(health);
function healthPaint(){if(!health.open)return;const b=G(),r=window.CHART_RT&&CHART_RT.thongTin(),el=health.querySelector('.hv-health-data');if(window.PHAT_LAI){el.textContent='Đang phát lại: không đo độ trễ giá trực tiếp.';return}if(!b.D||b.D.nguon!=='mt5'||!r||!r.so_mau){el.textContent='Chưa có mẫu tick trực tiếp để đo.';return}
 el.textContent='Nhận tick → cập nhật nến: '+r.gan_nhat.toFixed(1)+' ms · P95: '+r.p95.toFixed(1)+' ms / '+r.so_mau+' mẫu · Tick hợp lệ gần nhất: '+(r.im_ms/1000).toFixed(1)+' giây trước · Gói cũ hoặc không hợp lệ bỏ qua: '+r.bo;const q=window.CBCN?.tinhTrang?.();if(q)el.textContent+=' · Chỉ báo: '+(q.mode==='worker'?'Worker cục bộ':q.mode==='fallback'?'luồng dự phòng':'chờ')+(q.waiting?' · đang tính':'')+(q.compute_ms!=null?' · phép tính gần nhất '+q.compute_ms.toFixed(1)+' ms':'')}
health.addEventListener('toggle',healthPaint);setInterval(healthPaint,1000);
function dialog(title,html){if(dlg)dlg.close();const el=document.createElement('dialog');dlg=el;el.className='hv-dialog';el.setAttribute('aria-label',title);el.innerHTML='<h3>'+esc(title)+'</h3>'+html+'<div><button type="button" class="hv-close">Đóng</button></div>';document.body.appendChild(el);el.querySelector('.hv-close').onclick=()=>el.close();el.addEventListener('close',()=>{el.remove();if(dlg===el)dlg=null});el.showModal();return el}
async function accountPost(body){const r=await fetch('/api/tai-khoan-chart',{method:'POST',headers:{'Content-Type':'application/json','X-So-Cong-Khai':'1'},body:JSON.stringify(body)}),j=await r.json();if(!r.ok||!j.ok)throw Error(j.ly_do||'Chưa thực hiện được.');return j}
function broadcast(){try{localStorage.setItem('hvd-user-change',Date.now()+':'+Math.random())}catch(e){}location.reload()}
function account(){if(!U){if(dlg&&dlg.open)return;let create=false;const d=dialog('Tài khoản biểu đồ','<p>Xem chart và chỉ báo ngay. Đăng nhập để vẽ, chỉnh sửa và lưu bản vẽ riêng. Tài khoản này tách biệt tài khoản MT5.</p><form><label>Tên đăng nhập<input name="ten" autocomplete="username" minlength="3" maxlength="40" required></label><label>Mật khẩu<input name="pw" type="password" autocomplete="current-password" minlength="12" maxlength="128" required></label><label class="hv-confirm" hidden>Nhập lại mật khẩu<input name="confirm" type="password" autocomplete="new-password" maxlength="128"></label><p role="alert"></p><button class="primary" type="submit">Đăng nhập</button><button class="hv-mode" type="button">Tạo tài khoản</button></form>');
 const form=d.querySelector('form'),error=d.querySelector('[role=alert]'),submit=form.querySelector('[type=submit]');
 d.querySelector('.hv-mode').onclick=e=>{create=!create;submit.textContent=create?'Tạo tài khoản':'Đăng nhập';e.currentTarget.textContent=create?'Đã có tài khoản':'Tạo tài khoản';d.querySelector('.hv-confirm').hidden=!create;form.elements.confirm.required=create;form.elements.pw.autocomplete=create?'new-password':'current-password';error.textContent=''};
 form.onsubmit=async e=>{e.preventDefault();if(create&&form.elements.pw.value!==form.elements.confirm.value){error.textContent='Hai mật khẩu chưa khớp.';return}submit.disabled=true;error.textContent='';try{await accountPost({viec:create?'dang_ky':'dang_nhap',ten:form.elements.ten.value.trim(),mat_khau:form.elements.pw.value});form.reset();broadcast()}catch(err){error.textContent=err.message;submit.disabled=false}};
 }else{const d=dialog('Tài khoản biểu đồ','<p></p><p>Bản vẽ riêng được lưu trên máy chủ webapp này. Bản nháp mất mạng được giữ theo tài khoản trên trình duyệt hiện tại.</p><button type="button" class="hv-draft">Nhập bản nháp mã đang xem</button>'+(U.chu?'<button type="button" class="hv-legacy">Nhập kho bản vẽ cũ của máy này</button>':'')+'<button type="button" class="hv-logout">Đăng xuất</button><p role="alert"></p>');d.querySelector('p').textContent=U.ten;const note=d.querySelector('[role=alert]');
 d.querySelector('.hv-draft').onclick=async()=>{try{await HVD.nhapTam();note.textContent='Đã nhập bản nháp. Kiểm tra trạng thái lưu trên chart.'}catch(e){note.textContent=e.message}};
 const old=d.querySelector('.hv-legacy');if(old)old.onclick=async()=>{old.disabled=true;try{if(!await HVD.gui())throw Error('Chưa đồng bộ được chart hiện tại.');const j=await accountPost({viec:'nhap_cu'});await HVD.nap();const browserCount=await HVD.nhapCuLocal();note.textContent='Đã nhập '+(j.so_hinh+browserCount)+' hình; giữ nguyên kho cũ.'+(j.loi.length?' Có mã chưa nhập được: '+j.loi.map(x=>x.ma).join(', '):'');await HVD.nap()}catch(e){note.textContent=e.message}finally{old.disabled=false}};
 d.querySelector('.hv-logout').onclick=async()=>{try{const ok=await HVD.gui();if(!ok&&!confirm('Có bản nháp chưa đồng bộ. Đăng xuất vẫn giữ bản nháp theo tài khoản trên trình duyệt này để gửi lại sau. Tiếp tục?'))return;await accountPost({viec:'dang_xuat'});broadcast()}catch(e){note.textContent=e.message}}}}
async function history(){if(!U){account();return}try{const ds=await HVD.lichSu(),d=dialog('Lịch sử bản vẽ','<p>Khôi phục tạo một phiên bản mới, không xóa các phiên bản cũ.</p><div class="hv-revisions"></div><p role="alert"></p>'),list=d.querySelector('.hv-revisions');
 if(!ds.length)list.textContent='Chưa có phiên bản đã lưu.';for(const x of ds){const row=document.createElement('div');row.className='hv-revision';const text=document.createElement('span');text.textContent='#'+x.ban+' · '+x.so_hinh+' hình · '+new Date(x.luc*1000).toLocaleString(document.documentElement.lang==='en'?'en-US':'vi-VN');const b=document.createElement('button');b.textContent='Khôi phục';b.onclick=async()=>{if(!confirm('Khôi phục bản vẽ phiên bản '+x.ban+'? Bản hiện tại vẫn còn trong lịch sử.'))return;b.disabled=true;try{await HVD.khoiPhuc(x.ban);d.close()}catch(e){d.querySelector('[role=alert]').textContent=e.message;b.disabled=false}};row.append(text,b);list.append(row)}}catch(e){dialog('Chưa đọc được lịch sử','<p>'+esc(e.message)+'</p>')}}
bar.querySelector('.hv-account').onclick=account;bar.querySelector('.hv-now').onclick=()=>U?HVD.gui():account();bar.querySelector('.hv-history').onclick=history;
window.HVD_UI={paint(state,text){badge.dataset.state=state;badge.textContent=text;bar.querySelector('.hv-now').disabled=['replay','restoring'].includes(state);bar.querySelector('.hv-history').disabled=['replay','restoring'].includes(state)},account,
 mauPaint(state,text){templateStatus.dataset.state=state;templateStatus.textContent=text},
 mauConflict(names){const d=dialog('Mẫu chỉ báo thay đổi ở hai nơi','<p></p><button type="button" data-choice="both">Giữ cả hai bản</button><button type="button" data-choice="local">Giữ sửa đổi trên máy này</button><button type="button" data-choice="remote">Giữ sửa đổi trên máy chủ</button>');d.querySelector('p').textContent=names.join(', ');d.querySelectorAll('[data-choice]').forEach(b=>b.onclick=()=>{MCB.resolve(b.dataset.choice);d.close()})},
 conflict(count){const d=dialog('Bản vẽ thay đổi ở hai nơi','<p>Có '+count+' hình được sửa khác nhau. Bản nháp trên máy này vẫn được giữ. Chọn cách xử lý để tiếp tục lưu.</p><button type="button" data-choice="both">Giữ cả hai bản</button><button type="button" data-choice="local">Giữ sửa đổi trên máy này</button><button type="button" data-choice="remote">Giữ sửa đổi trên máy chủ</button>');d.querySelectorAll('[data-choice]').forEach(b=>b.onclick=()=>{HVD.giaiQuyet(b.dataset.choice);d.close()})}};
badge.onclick=()=>HVD.xungDot();if(window.HVD)HVD.paint();addEventListener('storage',e=>{if(e.key==='hvd-user-change')location.reload()});
})();
"""
