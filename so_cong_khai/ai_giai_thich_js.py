"""Hộp "AI giải thích" trên trang Biểu đồ (ai_giai_thich.py qua /api/ai-giai-thich): chọn chế độ, gửi, hiện câu trả lời có cấu trúc với
từng quan sát kèm bằng chứng (bấm để xem số liệu nguồn trong ảnh chụp). Câu trả lời về sau khi người dùng đã đổi mã hoặc khung được giữ
cho đúng mã/khung cũ, ghi rõ, không đè lên chart mới. Không gọi AI theo tick; chỉ khi bấm."""

CSS = r"""
.aigt .noi{padding:12px 16px 16px;overflow:auto;font-size:13.5px;line-height:1.55}.aigt .noi p{margin:0 0 8px}.aigt .why{color:var(--mute);font-size:12.5px}
.aigt .cd{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 10px}.aigt .cd button[aria-pressed=true]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.aigt .kq h4{margin:12px 0 4px;font-size:13px}.aigt .kq li{margin:0 0 6px}.aigt .bc{display:inline-block;margin-left:4px;padding:0 6px;border:1px solid var(--line);border-radius:6px;font-size:11.5px;cursor:pointer;background:var(--card2);color:var(--ink2)}
.aigt .dat{color:var(--gain)}.aigt .chua_dat{color:var(--loss)}.aigt .khong_ro{color:var(--mute)}.aigt pre{white-space:pre-wrap;font-size:12px;background:var(--card2);padding:8px;border-radius:8px;margin:6px 0}
.aigt .cu{border-left:3px solid var(--warn,#f5b301);padding-left:10px}
"""

JS = r"""
(()=>{const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const BD=()=>window.BDCB&&BDCB(),maNay=()=>{const m=document.getElementById('ma');return m?(m.value||''):''},tfNay=()=>{const B=BD();return B&&B.D?B.D.tf:'M15'};
const CD=[['chart','Giải thích chart hiện tại'],['phuong_phap','Vì sao phương pháp đạt hoặc chưa đạt'],['rui_ro','Rủi ro của phiếu kế hoạch'],['review','Review quyết định của phiếu']];
let CHON='chart',KQ=null,DANG=0,UID=null;
const NE=document.createElement('div');NE.className='cbcn-nen aigt';NE.hidden=true;
NE.innerHTML='<div class="cbcn" role="dialog" aria-modal="true" aria-label="AI giải thích có bằng chứng" style="grid-template-rows:auto minmax(0,1fr)"><header><b>AI giải thích có bằng chứng</b><button type="button" class="ghost" data-dong>Đóng</button></header><div class="noi"></div></div>';
document.body.appendChild(NE);const NOI=NE.querySelector('.noi');
const ppNay=()=>{const P=window.BDPK&&BDPK(maNay());return P&&P.phuong_phap?P.phuong_phap.ma:''};
const phieuNay=()=>{try{return localStorage.getItem('so-phieu-cuoi')||''}catch(e){return''}};
function veKq(){if(!KQ)return'';const t=KQ.tra_loi||{},bc=Object.fromEntries((KQ.bang_chung||[]).map(b=>[b.id,b])),
  chip=ds=>(ds||[]).map(i=>`<button type="button" class="bc" data-bc="${esc(i)}" title="${esc((bc[i]||{}).mo_ta||'')}">${esc(i)}</button>`).join(''),
  doi=KQ.ma!==(maNay()||KQ.ma)||KQ.tf!==tfNay()||KQ.expired||Date.now()/1000>=KQ.expires_at;
 const TT={dat:'đạt',chua_dat:'chưa đạt',khong_ro:'không rõ'};
 return`<div class="kq ${doi?'cu':''}"><p class="why">Ảnh chụp ${esc(KQ.snapshot_id)} · ${esc(KQ.ma)} ${esc(KQ.tf)} · lúc ${new Date(KQ.luc).toLocaleTimeString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'})}${KQ.nho?' · kết quả đã có, không gọi lại':''} · chi phí ${(+KQ.chi_phi_usd||0).toFixed(3)} USD</p>
  <p class="why" data-evidence-age>${doi?'Ảnh chụp đã cũ hoặc biểu đồ đã đổi. Không dùng diễn giải này như tín hiệu hiện tại.':''}</p>
  ${t.tom_tat?`<p>${esc(t.tom_tat)}</p>`:''}
  ${(t.quan_sat||[]).length?'<h4>Quan sát</h4><ul>'+t.quan_sat.map(x=>`<li>${esc(x.noi_dung)}${chip(x.bang_chung)}</li>`).join('')+'</ul>':''}
  ${(t.dieu_kien||[]).length?'<h4>Điều kiện</h4><ul>'+t.dieu_kien.map(x=>`<li><b class="${x.trang_thai}">${TT[x.trang_thai]||''}</b> · ${esc(x.ten)}${chip(x.bang_chung)}</li>`).join('')+'</ul>':''}
  ${(t.kich_ban||[]).length?'<h4>Kịch bản có điều kiện</h4><ul>'+t.kich_ban.map(x=>`<li>${esc(x.dieu_kien)}<br><span class="why">Vô hiệu khi: ${esc(x.vo_hieu)}</span>${chip(x.bang_chung)}</li>`).join('')+'</ul>':''}
  ${(t.thieu_du_lieu||[]).length?'<h4>Dữ liệu thiếu</h4><ul>'+t.thieu_du_lieu.map(x=>`<li>${esc(x)}</li>`).join('')+'</ul>':''}
  ${(t.khong_chac_chan||[]).length?'<h4>Điểm chưa chắc chắn</h4><ul>'+t.khong_chac_chan.map(x=>`<li>${esc(x)}</li>`).join('')+'</ul>':''}
  ${(KQ.loi_kiem||[]).length?'<p class="why">Đã bỏ '+KQ.loi_kiem.length+' mục không qua kiểm: '+KQ.loi_kiem.map(esc).join('; ')+'</p>':''}
  <div id="aigt-bc"></div>
  <p class="why">AI chỉ giải thích các số do phần mềm tính; giá, lot, RR, rủi ro không do AI tính. Không có tỷ lệ thắng hay xác suất lợi nhuận nào ở đây. Không phải lời khuyên đầu tư.</p></div>`}
async function ve(){let st;try{st=await(await fetch('/api/ai-platform/status',{cache:'no-store'})).json();const u=await(await fetch('/api/tai-khoan-chart',{cache:'no-store'})).json();if(UID&&UID!==u.nguoi?.id)KQ=null;UID=u.nguoi?.id||null}catch(e){st={chan:['Không tải được trạng thái.']}}
 const pp=ppNay(),pk=phieuNay(),thieu=CHON==='phuong_phap'&&!pp?'Chọn một phương pháp trên biểu đồ trước.':(CHON==='rui_ro'||CHON==='review')&&!pk?'Chưa có phiếu: lập phiếu từ Biểu đồ (Lập kế hoạch lệnh) trước.':'';
 const chan=[...(st.chan||[]).filter(c=>!/giá trực tiếp/.test(c)),...(thieu?[thieu]:[])];
 NOI.innerHTML=`<p class="why">Máy chủ chụp lại thị trường (${esc(maNay()||'XAUUSD')} ${esc(tfNay())}), gán mã cho từng số liệu, rồi hỏi AI. Mỗi ý phải dẫn đúng mã số liệu; ý nào không dẫn được bị bỏ. ${esc(st.provider||'')} / ${esc(st.model||'')} · ${st.account?.plan==='owner'?'Chủ tài khoản':'Còn '+(st.account?.remaining??0)+' lượt'}. Phiếu cũ chỉ dành cho chủ hệ thống.</p>
  <div class="cd" role="group" aria-label="Chế độ">${CD.map(([k,n])=>`<button type="button" class="ghost" data-cd="${k}" aria-pressed="${CHON===k}">${n}</button>`).join('')}</div>
  <p>${CHON==='phuong_phap'?'Phương pháp: <b>'+esc(pp||'chưa chọn')+'</b>':CHON==='rui_ro'||CHON==='review'?'Phiếu: <b>'+esc(pk||'chưa có')+'</b>':''}</p>
  <button type="button" class="go" data-gui ${chan.length||DANG?'disabled':''}>${DANG?'Đang hỏi, chờ tối đa 90 giây…':'Gửi giải thích (1 lượt)'}</button>${chan.map(c=>`<p class="why">• ${esc(c)}</p>`).join('')}${veKq()}`;capTuoi()}
NOI.addEventListener('click',async e=>{const c=e.target.closest('[data-cd]');if(c){CHON=c.dataset.cd;ve();return}
 const b=e.target.closest('[data-bc]');if(b&&KQ){const x=(KQ.bang_chung||[]).find(v=>v.id===b.dataset.bc);const el=document.getElementById('aigt-bc');if(el&&x)el.innerHTML=`<p class="why"><b>${esc(x.id)}</b> · ${esc(x.mo_ta)}</p><pre>${esc(JSON.stringify(x.gia_tri,null,1))}</pre>`;return}
 if(!e.target.closest('[data-gui]')||DANG)return;const requestOwner=UID;DANG=1;ve();const yc={che_do:CHON,ma:maNay(),tf:tfNay(),phuong_phap:ppNay(),phieu:phieuNay(),lang:document.documentElement.lang==='en'?'en':'vi',request_id:crypto.randomUUID().replaceAll('-',''),replay:!!window.PHAT_LAI};
 try{const r=await fetch('/api/ai-giai-thich',{method:'POST',headers:{'X-So-Cong-Khai':'1','Content-Type':'application/json','X-Chart-Owner':requestOwner||''},body:JSON.stringify(yc)});if(!r.ok)throw new Error(await r.text());
  const j=await r.json(),u=await(await fetch('/api/tai-khoan-chart',{cache:'no-store'})).json();if(u.nguoi?.id!==requestOwner)throw new Error('Tài khoản đã thay đổi.');if(!j.ok)alert((j.chan||['Chưa giải thích được.']).join('\n'));else KQ={...j,ma:j.ma||yc.ma,tf:j.tf||yc.tf}}
 catch(er){alert('Không hỏi được AI: '+er.message)}finally{DANG=0;ve()}});
let tuoiTimer=0;function capTuoi(){clearTimeout(tuoiTimer);tuoiTimer=0;if(NE.hidden||!KQ)return;const p=NE.querySelector('[data-evidence-age]');if(p&&(KQ.expired||Date.now()/1000>=KQ.expires_at||KQ.ma!==(maNay()||KQ.ma)||KQ.tf!==tfNay()))p.textContent='Ảnh chụp đã cũ hoặc biểu đồ đã đổi. Không dùng diễn giải này như tín hiệu hiện tại.';tuoiTimer=setTimeout(capTuoi,1000)}
NE.addEventListener('click',e=>{if(e.target===NE||e.target.closest('[data-dong]'))NE.hidden=true});
addEventListener('keydown',e=>{if(!NE.hidden&&e.key==='Escape'){e.stopPropagation();NE.hidden=true}},true);
const moc=[...document.querySelectorAll('button')].find(x=>x.textContent==='AI đọc chỉ báo');
if(moc){const ab=document.createElement('button');ab.type='button';ab.className='ghost nho';ab.textContent='Bằng chứng / Phiếu';ab.title='AI giải thích chart, phương pháp hoặc phiếu, mỗi ý kèm số liệu nguồn';
 ab.addEventListener('click',()=>{NE.hidden=false;ve()});moc.after(ab)}})();
"""
