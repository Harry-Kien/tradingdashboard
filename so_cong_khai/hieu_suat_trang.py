"""Trang Phân tích hiệu suất (/hieu-suat): chỉ số, đường vốn và sụt vốn, lịch lãi/lỗ theo ngày, nhận xét tự động, bảng phân nhóm, danh sách lệnh.
Dữ liệu từ /api/hieu-suat (hieu_suat.py), xuất CSV ở /api/hieu-suat.csv."""
from __future__ import annotations

from html import escape

from . import thuong_hieu, trang

CSS = r"""
main.rong{max-width:1320px}
.hs-top{display:flex;justify-content:space-between;align-items:flex-end;gap:12px 24px;flex-wrap:wrap;padding-bottom:12px;border-bottom:1px solid var(--line)}
.hs-top h1{margin:0}.hs-top p{margin:6px 0 0;color:var(--ink2);max-width:760px}
.hs-tk{display:inline-flex;align-items:center;gap:8px;font-size:12.5px;color:var(--ink2);background:var(--card);border:1px solid var(--line);border-radius:999px;padding:6px 12px}
.hs-tk b{color:var(--ink)}.hs-tk.mau{border-color:color-mix(in srgb,var(--warn) 55%,var(--line));color:var(--warn)}
.hs-loc{display:flex;flex-wrap:wrap;gap:8px 10px;align-items:center;margin:14px 0 4px;position:sticky;top:var(--nv-h,56px);z-index:4;padding:8px 0;
background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)}
.hs-loc .sg{display:inline-flex;flex-wrap:wrap;gap:4px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:4px}
.hs-loc .sg button{min-height:32px;padding:0 12px;border:0;border-radius:8px;background:none;color:var(--ink2);font:600 12.5px/1 inherit;font-family:inherit;cursor:pointer}
.hs-loc .sg button:hover{color:var(--ink);background:color-mix(in srgb,var(--ink) 6%,transparent)}
.hs-loc .sg button[aria-pressed=true]{background:color-mix(in srgb,var(--series) 16%,transparent);color:var(--series);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--series) 45%,transparent)}
.hs-loc select{min-height:40px;border:1px solid var(--line);border-radius:10px;background:var(--card2);color:var(--ink);padding:0 10px;font:inherit;font-size:13px}
.hs-loc .grow{flex:1}
.hs-loc a.ghost,.hs-loc button.ghost{text-decoration:none}
.hs-kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:14px 0}
.hs-k{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;position:relative;overflow:hidden}
.hs-k::after{content:"";position:absolute;inset:auto -30% -60% auto;width:160px;height:160px;border-radius:50%;background:radial-gradient(color-mix(in srgb,var(--series) 18%,transparent),transparent 70%);pointer-events:none}
.hs-k span{display:block;font-size:12px;color:var(--mute)}.hs-k b{display:block;font-size:28px;line-height:1.2;font-weight:700;letter-spacing:-.02em;margin-top:4px}
.hs-k small{display:block;font-size:12px;color:var(--ink2);margin-top:4px}
.hs-k .vong{position:absolute;right:14px;top:14px;width:54px;height:54px}
.vong circle{fill:none;stroke-width:6}.vong .nen{stroke:var(--track)}.vong .gt{stroke:var(--gain);stroke-linecap:round;transform:rotate(-90deg);transform-origin:50% 50%;transition:stroke-dashoffset 1s cubic-bezier(.2,.7,.2,1)}
.hs-card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;margin-top:14px}
.hs-card h2{margin:0 0 4px}.hs-card>.sub{margin:0 0 12px;font-size:12.5px;color:var(--ink2)}
.hs-g2{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr);gap:14px}@media(max-width:1000px){.hs-g2{grid-template-columns:1fr}}
.hs-g2>.hs-card{margin-top:0}
.dv{position:relative}.dv svg{display:block;width:100%;height:auto}
.dv .tip{position:absolute;pointer-events:none;background:var(--card2);border:1px solid var(--line);border-radius:10px;padding:7px 10px;font-size:12px;white-space:nowrap;box-shadow:0 10px 30px -10px rgba(0,0,0,.5);display:none}
.dv .duong{fill:none;stroke:var(--series);stroke-width:2.2;stroke-linejoin:round}
.dv .ve{stroke-dasharray:var(--dai);stroke-dashoffset:var(--dai);animation:ve 1.4s cubic-bezier(.3,.6,.2,1) forwards}
@keyframes ve{to{stroke-dashoffset:0}}
.dv text{font-size:10.5px;fill:var(--mute)}
.lich{display:flex;gap:14px;overflow-x:auto;padding-bottom:6px}
.lich .thang{flex:none}.lich .thang>b{display:block;font-size:12px;color:var(--ink2);margin-bottom:6px;font-weight:600}
.lich .o{display:grid;grid-template-columns:repeat(7,16px);gap:3px}.lich .o i{width:16px;height:16px;border-radius:4px;background:var(--track);display:block}
.lich .o i.trong{background:transparent}.lich .o i[data-v]{cursor:default}
.lich-chu{display:flex;align-items:center;gap:8px;font-size:11.5px;color:var(--mute);margin-top:8px}.lich-chu span{width:160px;height:8px;border-radius:4px;background:linear-gradient(90deg,var(--loss),var(--track),var(--gain))}
.nx{display:grid;gap:8px}
.nx div{display:grid;grid-template-columns:28px minmax(0,1fr);gap:4px 10px;padding:11px 12px;border-radius:12px;background:var(--card2);border:1px solid var(--line)}
.nx i{grid-row:1/3;width:28px;height:28px;border-radius:8px;display:grid;place-items:center;font-style:normal;font-weight:800;font-size:14px}
.nx .xau i{background:color-mix(in srgb,var(--loss) 18%,transparent);color:var(--loss)}.nx .chu_y i{background:color-mix(in srgb,var(--warn) 18%,transparent);color:var(--warn)}
.nx .tot i{background:color-mix(in srgb,var(--gain) 18%,transparent);color:var(--gain)}.nx .tin i{background:color-mix(in srgb,var(--series) 14%,transparent);color:var(--series)}
.nx b{font-size:13.5px}.nx p{margin:0;font-size:12.5px;color:var(--ink2);line-height:1.5}
.pn-tab{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:10px}
.pn-tab button{min-height:32px;padding:0 12px;border:1px solid var(--line);border-radius:999px;background:var(--card2);color:var(--ink2);font:600 12.5px/1 inherit;font-family:inherit;cursor:pointer}
.pn-tab button[aria-pressed=true]{color:var(--series);border-color:color-mix(in srgb,var(--series) 55%,var(--line));background:color-mix(in srgb,var(--series) 12%,transparent)}
.pn{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr);gap:16px}@media(max-width:900px){.pn{grid-template-columns:1fr}}
.cot-n{display:grid;grid-template-columns:96px minmax(0,1fr) 92px;gap:8px;align-items:center;font-size:12.5px;padding:4px 0}
.cot-n .t{position:relative;height:16px}.cot-n .t i{position:absolute;top:0;bottom:0;border-radius:4px;transition:all .5s}.cot-n .t u{position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;background:var(--mute)}
.cot-n em{font-style:normal;text-align:right;font-weight:600}
.hs-wrap{overflow:auto;border:1px solid var(--line);border-radius:12px;max-height:520px}
.hs-wrap table{font-size:12.5px}.hs-wrap th{position:sticky;top:0;background:var(--card2);z-index:1}.hs-wrap th[data-k]{cursor:pointer}
.hs-wrap td,.hs-wrap th{padding:7px 10px}
.trang-so{display:flex;gap:6px;align-items:center;justify-content:flex-end;margin-top:8px;font-size:12.5px;color:var(--ink2)}
.hien{animation:hien .55s cubic-bezier(.2,.7,.2,1) both}
@keyframes hien{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@media(prefers-reduced-motion:reduce){.hien{animation:none}.dv .ve{animation:none;stroke-dashoffset:0}.vong .gt{transition:none}}
.hs-the{width:min(880px,94vw);max-width:none;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:16px;padding:16px 18px;box-shadow:0 30px 80px rgba(0,0,0,.45)}
.hs-the::backdrop{background:rgba(0,0,0,.62);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px)}
.hs-the[open]{animation:the-vao .28s cubic-bezier(.2,.7,.2,1)}
@keyframes the-vao{from{opacity:0;transform:translateY(14px) scale(.98)}to{opacity:1;transform:none}}
.the-dau{display:flex;justify-content:space-between;align-items:center;gap:10px}.the-dau b{font-size:16px}
.hs-the canvas{display:block;width:100%;height:auto;aspect-ratio:1200/630;margin:12px 0;border-radius:12px;border:1px solid var(--line);background:#090a08}
.the-chon{display:flex;gap:8px;align-items:flex-start;font-size:13px;color:var(--ink2);cursor:pointer}.the-chon input{margin-top:2px}
.the-nut{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:12px}
.the-nut button{min-height:38px;padding:0 16px;border-radius:10px;font:600 13px/1 inherit;font-family:inherit;cursor:pointer}
.the-nut .chinh{background:var(--series);color:#0b0d09;border:0}.the-nut .chinh:hover{filter:brightness(1.08)}
#hs-chia{background:color-mix(in srgb,var(--series) 14%,transparent);color:var(--series);border-color:color-mix(in srgb,var(--series) 45%,transparent)}
@media(prefers-reduced-motion:reduce){.hs-the[open]{animation:none}}
@media(max-width:640px){.hs-k b{font-size:22px}.cot-n{grid-template-columns:74px minmax(0,1fr) 78px}.hs-loc{position:static}}
"""

JS = r"""
(()=>{const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const NF={},fmt=(v,d=2)=>v==null||!isFinite(v)?'—':(NF[d]||(NF[d]=new Intl.NumberFormat('vi-VN',{minimumFractionDigits:d,maximumFractionDigits:d}))).format(v);
const tien=(v,t)=>v==null?'—':(v>0?'+':v<0?'−':'')+fmt(Math.abs(v))+' '+(t||'');
const cls=v=>v>0?'gain':v<0?'loss':'';const giam=matchMedia('(prefers-reduced-motion: reduce)').matches,LG=document.documentElement.lang==='en'?'en':'vi';
const gio=p=>p==null?'—':p<60?fmt(p,0)+' phút':p<1440?fmt(p/60,1)+' giờ':fmt(p/1440,1)+' ngày';
const ngayVN=t=>new Date(t).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',year:'2-digit',hour:'2-digit',minute:'2-digit'});
const ngayNgan=t=>new Date(t).toLocaleDateString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',year:'numeric'});
let st={ngay:90,ma:'',chieu:'',nguon:'',mau:false},D=null,tab='ma',sx={k:'dong',d:-1},trangSo=0;
try{const s=JSON.parse(localStorage.getItem('hs-loc')||'{}');Object.assign(st,s)}catch(e){}
const luu=()=>{try{localStorage.setItem('hs-loc',JSON.stringify(st))}catch(e){}};
function dem(el,den,fn){if(giam||!isFinite(den)){el.textContent=fn(den);return}const t0=performance.now(),d=800;
 const b=t=>{const k=Math.min(1,(t-t0)/d),e=1-Math.pow(1-k,3);el.textContent=fn(den*e);if(k<1)requestAnimationFrame(b)};requestAnimationFrame(b)}
let lan=0;
async function tai(){const so=++lan;$('#hs-noi').setAttribute('aria-busy','true');
 try{const r=await fetch('/api/hieu-suat?'+new URLSearchParams({ngay:st.ngay,ma:st.ma,chieu:st.chieu,nguon:st.nguon,mau:st.mau?1:0}),{cache:'no-store'});
  if(!r.ok)throw new Error(await r.text());const j=await r.json();if(so!==lan)return;D=j;ve()}
 catch(e){if(so!==lan)return;$('#hs-noi').innerHTML=`<div class="hs-card"><p class="note">Không đọc được lịch sử lệnh: ${esc(e.message)}</p></div>`}
 $('#hs-noi').removeAttribute('aria-busy')}
function boLoc(){document.querySelectorAll('#hs-ngay button').forEach(b=>b.setAttribute('aria-pressed',+b.dataset.v===st.ngay));
 document.querySelectorAll('#hs-chieu button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.v===st.chieu));
 $('#hs-mau').setAttribute('aria-pressed',st.mau);$('#hs-mau').textContent=st.mau?'Đang xem dữ liệu minh họa':'Xem dữ liệu minh họa';
 if(D&&D.loc){$('#hs-ma').innerHTML='<option value="">Mọi mã</option>'+D.loc.ma.map(m=>`<option${m===st.ma?' selected':''}>${esc(m)}</option>`).join('');
  $('#hs-nguon').innerHTML='<option value="">Mọi nguồn</option>'+D.loc.nguon.map(m=>`<option${m===st.nguon?' selected':''}>${esc(m)}</option>`).join('')}
 $('#hs-csv').href='/api/hieu-suat.csv?'+new URLSearchParams({ngay:st.ngay,ma:st.ma,chieu:st.chieu,nguon:st.nguon,mau:st.mau?1:0})}
function ve(){boLoc();const el=$('#hs-noi');
 if(!D.san_sang){el.innerHTML=`<div class="hs-card"><h2>Chưa đọc được lịch sử lệnh</h2><p class="sub">${esc(D.ly_do||'')}</p><p class="small">Bấm "Xem dữ liệu minh họa" để xem trước trang với lệnh giả lập.</p></div>`;$('#hs-tk').innerHTML='';return}
 const tk=D.tai_khoan||{},T=D.tong,t=tk.tien||'USD';
 $('#hs-tk').className='hs-tk'+(D.mau?' mau':'');$('#hs-tk').innerHTML=D.mau?'<b>Dữ liệu minh họa</b> · lệnh giả lập, không phải kết quả thật':`Tài khoản <b>${esc(tk.so)}</b> · ${tk.demo?'demo':'thật'} · ${esc(tk.may_chu||'')}`;
 const pf=T.pf==='inf'?'∞':fmt(T.pf,2),tl=T.ty_le||0;
 let h=`<div class="hs-kpi">
  <div class="hs-k hien"><span>Lãi ròng</span><b class="${cls(T.rong)}" data-dem="${T.rong??0}" data-kieu="tien">—</b><small>lãi gộp ${tien(T.lai_gop,t)} · phí ${tien(T.phi,t)} · swap ${tien(T.swap,t)}</small></div>
  <div class="hs-k hien"><span>Tỷ lệ thắng</span><b data-dem="${tl}" data-kieu="pct">—</b><small>Lệnh thắng ${T.thang} · lệnh thua ${T.thua}</small>
   <svg class="vong" viewBox="0 0 60 60"><circle class="nen" cx="30" cy="30" r="24"/><circle class="gt" cx="30" cy="30" r="24" stroke-dasharray="150.8" stroke-dashoffset="150.8" data-p="${tl}"/></svg></div>
  <div class="hs-k hien"><span>Hệ số lợi nhuận</span><b class="${T.pf==='inf'||T.pf>1?'gain':T.pf!=null&&T.pf<1?'loss':''}">${pf}</b><small>lãi gộp chia lỗ gộp; trên 1 là có lãi</small></div>
  <div class="hs-k hien"><span>Kỳ vọng mỗi lệnh</span><b class="${cls(T.tb)}">${tien(T.tb,t)}</b><small>${T.r_tb!=null?'trung bình '+(T.r_tb>0?'+':'')+fmt(T.r_tb,2)+'R trên '+T.n_r+' lệnh có SL':'chưa tính được R (lệnh không có SL)'}</small></div>
  <div class="hs-k hien"><span>Sụt vốn lớn nhất</span><b class="${T.dd_max>0?'loss':''}">${T.dd_max?'−'+fmt(T.dd_max)+' '+t:'—'}</b><small>${T.dd_pct!=null?fmt(T.dd_pct,1)+'% vốn lúc đỉnh':''} · chuỗi thua dài nhất ${T.chuoi_thua}</small></div>
  <div class="hs-k hien"><span>Số lệnh</span><b data-dem="${T.n}" data-kieu="so">—</b><small>giữ trung bình ${gio(T.giu_tb)} · chuỗi thắng dài nhất ${T.chuoi_thang}</small></div></div>`;
 h+=`<div class="hs-g2"><div class="hs-card hien"><h2>Đường vốn</h2><p class="sub">Lãi ròng cộng dồn theo lệnh đã đóng (xanh) và mức sụt so với đỉnh trước đó (đỏ). Rê chuột để xem từng lệnh.</p><div class="dv" id="dv"></div></div>
  <div class="hs-card hien"><h2>Nhận xét</h2><p class="sub">Tự động từ lịch sử của bạn; chỉ nêu khi nhóm có đủ lệnh.</p><div class="nx">${(D.nhan_xet||[]).map(n=>{const c=n[LG]||n.vi||n;return`<div class="${n.muc}"><i>${{xau:'!',chu_y:'?',tot:'✓',tin:'i'}[n.muc]}</i><b>${esc(c.tieu)}</b><p>${esc(c.noi)}</p></div>`}).join('')}</div></div></div>`;
 h+=`<div class="hs-card hien"><h2>Lịch lãi/lỗ theo ngày</h2><p class="sub">Mỗi ô là một ngày (giờ Việt Nam): xanh là ngày có lãi, đỏ là ngày lỗ, đậm theo số tiền.</p><div class="lich" id="lich"></div><div class="lich-chu">lỗ<span></span>lãi</div></div>`;
 h+=`<div class="hs-card hien"><h2>Phân tích theo nhóm</h2><p class="sub">Lãi ròng của từng nhóm (thanh) và chỉ số chi tiết (bảng).</p><div class="pn-tab" id="pn-tab">${[['ma','Mã'],['chieu','Chiều'],['phien','Phiên'],['thu','Thứ'],['gio','Giờ mở lệnh'],['giu','Thời gian giữ'],['nguon','Nguồn']].map(([k,n])=>`<button type="button" data-k="${k}" aria-pressed="${k===tab}">${n}</button>`).join('')}</div><div id="pn"></div></div>`;
 h+=`<div class="hs-card hien"><h2>Danh sách lệnh</h2><p class="sub">${D.lenh.length} lệnh đã đóng hết trong khoảng đã chọn. Bấm tiêu đề cột để sắp xếp.</p><div class="hs-wrap"><table><thead><tr>${[['dong','Đóng lúc'],['ma','Mã'],['chieu','Chiều'],['lot','Lot'],['vao','Giá vào'],['ra','Giá ra'],['phut','Giữ'],['rong','Lãi ròng'],['r','R'],['nguon','Nguồn']].map(([k,n])=>`<th data-k="${k}"${['lot','vao','ra','phut','rong','r'].includes(k)?' class="r"':''}>${n}</th>`).join('')}</tr></thead><tbody id="ds"></tbody></table></div><div class="trang-so" id="trang-so"></div></div>`;
 el.innerHTML=h;
 el.querySelectorAll('[data-dem]').forEach(b=>{const k=b.dataset.kieu,v=+b.dataset.dem;dem(b,v,x=>k==='tien'?tien(x,t):k==='pct'?fmt(x,1)+'%':fmt(Math.round(x),0))});
 const g=el.querySelector('.vong .gt');if(g)requestAnimationFrame(()=>requestAnimationFrame(()=>{g.style.strokeDashoffset=150.8*(1-(+g.dataset.p)/100)}));
 veDuong();veLich();veNhom();veDs();
 el.querySelectorAll('.hien').forEach((x,i)=>{x.style.animationDelay=Math.min(i,8)*55+'ms'});         // hiện dần lần lượt; luôn kết thúc ở trạng thái hiện
 el.querySelector('#pn-tab').addEventListener('click',e=>{const b=e.target.closest('button[data-k]');if(!b)return;tab=b.dataset.k;el.querySelectorAll('#pn-tab button').forEach(x=>x.setAttribute('aria-pressed',x===b));veNhom()});
 el.querySelector('thead').addEventListener('click',e=>{const th=e.target.closest('th[data-k]');if(!th)return;sx=sx.k===th.dataset.k?{k:sx.k,d:-sx.d}:{k:th.dataset.k,d:-1};trangSo=0;veDs()})}
function veDuong(){const box=$('#dv'),v=D.duong_von;if(!v.length){box.innerHTML='<p class="small">Chưa có lệnh.</p>';return}
 const W=760,H=260,P={l:52,r:10,t:12,b:24},hd=70,tt=H-hd-P.b,ys=v.map(p=>p.v).concat([0]),lo=Math.min(...ys),hi=Math.max(...ys),sp=(hi-lo)||1,dmin=Math.min(...v.map(p=>p.dd),-1e-9);
 const X=i=>P.l+(v.length<2?0:i/(v.length-1))*(W-P.l-P.r),Y=x=>P.t+(hi-x)/sp*(tt-P.t),Yd=x=>tt+18+(x/dmin)*(hd-24);
 const pts=v.map((p,i)=>[X(i),Y(p.v)]),duong=pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)).join(''),
  vung=duong+`L${X(v.length-1).toFixed(1)} ${Y(Math.max(lo,0)).toFixed(1)}L${X(0).toFixed(1)} ${Y(Math.max(lo,0)).toFixed(1)}Z`,
  dd=v.map((p,i)=>(i?'L':'M')+X(i).toFixed(1)+' '+Yd(p.dd).toFixed(1)).join('')+`L${X(v.length-1).toFixed(1)} ${(tt+18).toFixed(1)}L${X(0).toFixed(1)} ${(tt+18).toFixed(1)}Z`;
 const tk=[lo,(lo+hi)/2,hi].map(x=>`<text x="${P.l-6}" y="${Y(x)+3}" text-anchor="end">${fmt(x,0)}</text><line x1="${P.l}" x2="${W-P.r}" y1="${Y(x)}" y2="${Y(x)}" stroke="var(--gridc)"/>`).join('');
 let dai=0;for(let i=1;i<pts.length;i++)dai+=Math.hypot(pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1]);
 box.innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Đường vốn"><defs><linearGradient id="gv" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--series)" stop-opacity=".35"/><stop offset="1" stop-color="var(--series)" stop-opacity="0"/></linearGradient></defs>
  ${tk}<line x1="${P.l}" x2="${W-P.r}" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--mute)" stroke-dasharray="3 3"/><path d="${vung}" fill="url(#gv)"/><path class="duong ve" style="--dai:${Math.ceil(dai)}" d="${duong}"/>
  <path d="${dd}" fill="color-mix(in srgb,var(--loss) 35%,transparent)" stroke="var(--loss)" stroke-width="1"/><text x="${P.l+4}" y="${tt+12}">sụt</text>
  <line id="dv-x" y1="${P.t}" y2="${H-P.b}" stroke="var(--mute)" stroke-dasharray="3 3" visibility="hidden"/><circle id="dv-o" r="4.5" fill="var(--series)" stroke="var(--card)" stroke-width="2" visibility="hidden"/>
  <text x="${P.l}" y="${H-6}">${ngayNgan(v[0].t)}</text><text x="${W-P.r}" y="${H-6}" text-anchor="end">${ngayNgan(v[v.length-1].t)}</text></svg><div class="tip" id="dv-tip"></div>`;
 const svg=box.querySelector('svg'),tip=box.querySelector('#dv-tip'),lx=svg.querySelector('#dv-x'),o=svg.querySelector('#dv-o'),ds=D.lenh.slice().reverse();
 svg.addEventListener('mousemove',e=>{const r=svg.getBoundingClientRect(),x=(e.clientX-r.left)/r.width*W;let i=Math.round((x-P.l)/(W-P.l-P.r)*(v.length-1));i=Math.max(0,Math.min(v.length-1,i));
  const p=v[i],l=ds[i]||{};lx.setAttribute('x1',X(i));lx.setAttribute('x2',X(i));lx.setAttribute('visibility','visible');o.setAttribute('cx',X(i));o.setAttribute('cy',Y(p.v));o.setAttribute('visibility','visible');
  tip.style.display='block';tip.innerHTML=`<b>Lệnh ${i+1}: ${esc(l.ma||'')} ${l.chieu==='MUA'?'MUA':'BÁN'}</b><br>${ngayVN(p.t)} · <span class="${cls(l.rong)}">${tien(l.rong,D.tong.tien)}</span><br>Cộng dồn ${tien(p.v,D.tong.tien)} · sụt ${fmt(-p.dd)}`;
  const px=(X(i)/W)*r.width;tip.style.left=Math.min(r.width-tip.offsetWidth-4,Math.max(0,px+12))+'px';tip.style.top='8px'});
 svg.addEventListener('mouseleave',()=>{tip.style.display='none';lx.setAttribute('visibility','hidden');o.setAttribute('visibility','hidden')})}
function veLich(){const box=$('#lich'),ds=D.ngay;if(!ds.length){box.innerHTML='<p class="small">Chưa có ngày nào có lệnh đóng.</p>';return}
 const m=new Map(ds.map(o=>[o.ngay,o])),cap=Math.max(...ds.map(o=>Math.abs(o.rong)))||1,dau=new Date(ds[0].ngay+'T00:00:00Z'),cuoi=new Date(ds[ds.length-1].ngay+'T00:00:00Z');
 let h='',c=new Date(Date.UTC(dau.getUTCFullYear(),dau.getUTCMonth(),1));
 while(c<=cuoi){const y=c.getUTCFullYear(),mo=c.getUTCMonth(),so=new Date(Date.UTC(y,mo+1,0)).getUTCDate(),lech=(new Date(Date.UTC(y,mo,1)).getUTCDay()+6)%7;
  let o='';for(let i=0;i<lech;i++)o+='<i class="trong"></i>';
  for(let d=1;d<=so;d++){const k=`${y}-${String(mo+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`,x=m.get(k);
   if(!x){o+='<i></i>';continue}const a=Math.min(1,Math.abs(x.rong)/cap)*80+15,ti=k+': '+tien(x.rong,D.tong.tien)+' · '+x.n+' lệnh';
   o+=`<i data-v title="${esc(ti)}" style="background:color-mix(in srgb,var(--${x.rong>=0?'gain':'loss'}) ${a.toFixed(0)}%,var(--track))"></i>`}
  h+=`<div class="thang"><b>${String(mo+1).padStart(2,'0')}/${y}</b><div class="o">${o}</div></div>`;c=new Date(Date.UTC(y,mo+1,1))}
 box.innerHTML=h;box.scrollLeft=box.scrollWidth}
function veNhom(){const ds=(D.bang[tab]||[]).filter(x=>x.n),box=$('#pn');if(!ds.length){box.innerHTML='<p class="small">Không có dữ liệu.</p>';return}
 const cap=Math.max(...ds.map(x=>Math.abs(x.rong)))||1,ten=x=>tab==='gio'?String(x.k).padStart(2,'0')+':00':tab==='chieu'?(x.k==='MUA'?'MUA':'BÁN'):(LG==='en'&&x.k_en!=null?x.k_en:x.k);
 box.innerHTML='<div class="pn"><div>'+ds.map(x=>{const w=Math.abs(x.rong)/cap*50;return`<div class="cot-n"><span>${esc(ten(x))}</span><div class="t"><u></u><i style="${x.rong>=0?'left:50%':'left:'+(50-w)+'%'};width:${w}%;background:var(--${x.rong>=0?'gain':'loss'})"></i></div><em class="${cls(x.rong)}">${tien(x.rong,'')}</em></div>`}).join('')
  +'</div><div class="hs-wrap" style="max-height:none"><table><thead><tr><th>Nhóm</th><th class="r">Lệnh</th><th class="r">Thắng</th><th class="r">Hệ số LN</th><th class="r">TB/lệnh</th><th class="r">R bình quân</th></tr></thead><tbody>'
  +ds.map(x=>`<tr><td>${esc(ten(x))}</td><td class="r">${x.n}</td><td class="r">${fmt(x.ty_le,0)}%</td><td class="r">${x.pf==='inf'?'∞':fmt(x.pf,2)}</td><td class="r ${cls(x.tb)}">${tien(x.tb,'')}</td><td class="r">${x.r_tb!=null?fmt(x.r_tb,2):'—'}</td></tr>`).join('')+'</tbody></table></div></div>'}
function veDs(){const ds=D.lenh.slice().sort((a,b)=>{const p=a[sx.k],q=b[sx.k];if(p==null)return 1;if(q==null)return-1;return(typeof p==='string'?p.localeCompare(q):p-q)*sx.d}),N=25,tong=Math.ceil(ds.length/N)||1;
 trangSo=Math.min(trangSo,tong-1);document.querySelectorAll('#hs-noi th[data-k]').forEach(th=>th.setAttribute('aria-sort',th.dataset.k===sx.k?(sx.d>0?'ascending':'descending'):'none'));
 $('#ds').innerHTML=ds.slice(trangSo*N,trangSo*N+N).map(x=>{const d=x.vao>100?2:x.vao>10?3:5;return`<tr><td>${ngayVN(x.dong)}</td><td><b>${esc(x.ma)}</b></td><td class="${x.chieu==='MUA'?'gain':'loss'}">${x.chieu==='MUA'?'MUA':'BÁN'}</td>
  <td class="r">${fmt(x.lot,2)}</td><td class="r">${fmt(x.vao,d)}</td><td class="r">${fmt(x.ra,d)}</td><td class="r">${gio(x.phut)}</td><td class="r ${cls(x.rong)}"><b>${tien(x.rong,'')}</b></td>
  <td class="r ${cls(x.r)}">${x.r!=null?(x.r>0?'+':'')+fmt(x.r,2):'—'}</td><td>${esc(x.nguon)}</td></tr>`}).join('')||'<tr><td colspan="10" class="small">Không có lệnh.</td></tr>';
 $('#trang-so').innerHTML=tong>1?`<button type="button" class="ghost nho" data-p="-1"${trangSo?'':' disabled'}>‹ Trước</button><span>Trang ${trangSo+1}/${tong}</span><button type="button" class="ghost nho" data-p="1"${trangSo<tong-1?'':' disabled'}>Sau ›</button>`:'';
 $('#trang-so').onclick=e=>{const b=e.target.closest('button[data-p]');if(!b)return;trangSo+= +b.dataset.p;veDs()}}
$('#hs-ngay').addEventListener('click',e=>{const b=e.target.closest('button[data-v]');if(!b)return;st.ngay=+b.dataset.v;luu();tai()});
$('#hs-chieu').addEventListener('click',e=>{const b=e.target.closest('button[data-v]');if(!b)return;st.chieu=b.dataset.v;luu();tai()});
$('#hs-ma').addEventListener('change',e=>{st.ma=e.target.value;luu();tai()});$('#hs-nguon').addEventListener('change',e=>{st.nguon=e.target.value;luu();tai()});
$('#hs-mau').addEventListener('click',()=>{st.mau=!st.mau;st.ma='';st.nguon='';luu();tai()});
const CC={bg:'#090a08',card:'#12150f',line:'#262b21',ink:'#f3f5ee',ink2:'#a4aa9a',series:'#8dff08',gain:'#5fe36a',loss:'#ff6b63'};
const KY={7:'7 ngày',30:'30 ngày',90:'90 ngày',365:'1 năm',0:'Toàn bộ lịch sử'};
const hop=(c,x,y,w,h,r)=>{c.beginPath();if(c.roundRect)c.roundRect(x,y,w,h,r);else c.rect(x,y,w,h)};
const vua=(c,s,dam,co,w)=>{const F='"Be Vietnam Pro","Segoe UI",Arial,sans-serif';do{c.font=dam+' '+co+'px '+F}while(c.measureText(s).width>w&&(co-=2)>16)};
const coDan=(c,s,w)=>{if(c.measureText(s).width<=w)return s;while(s.length>1&&c.measureText(s+'…').width>w)s=s.slice(0,-1);return s+'…'};
async function veThe(cv,coTien){
 const c=cv.getContext('2d'),W=1200,H=630,T=D.tong,tk=D.tai_khoan||{},t=tk.tien||'USD',F='"Be Vietnam Pro","Segoe UI",Arial,sans-serif',v=D.duong_von||[];
 try{await Promise.all(['800 40px','700 20px','500 20px'].map(f=>document.fonts.load(f+' "Be Vietnam Pro"')))}catch(e){}
 cv.width=W;cv.height=H;c.textBaseline='alphabetic';
 c.fillStyle=CC.bg;c.fillRect(0,0,W,H);
 const gl=c.createRadialGradient(W*.82,40,10,W*.82,40,560);gl.addColorStop(0,'rgba(141,255,8,.16)');gl.addColorStop(1,'rgba(141,255,8,0)');c.fillStyle=gl;c.fillRect(0,0,W,H);
 c.strokeStyle='rgba(255,255,255,.035)';c.lineWidth=1;for(let x=0;x<W;x+=40){c.beginPath();c.moveTo(x+.5,0);c.lineTo(x+.5,H);c.stroke()}
 if(D.mau){c.save();c.translate(W/2,H/2);c.rotate(-.18);c.font='800 150px '+F;c.fillStyle='rgba(255,255,255,.045)';c.textAlign='center';c.fillText('MINH HỌA',0,50);c.restore()}
 const lg=document.querySelector('.nv-mk img');
 if(lg&&lg.complete&&lg.naturalWidth){c.save();hop(c,52,40,54,54,13);c.clip();c.drawImage(lg,52,40,54,54);c.restore();hop(c,52,40,54,54,13);c.strokeStyle='rgba(141,255,8,.45)';c.lineWidth=1.5;c.stroke()}
 else{hop(c,56,46,42,42,11);c.fillStyle=CC.series;c.fill();
  c.strokeStyle=CC.bg;c.lineWidth=4;c.lineCap='round';c.lineJoin='round';c.beginPath();c.moveTo(66,76);c.lineTo(75,66);c.lineTo(81,72);c.lineTo(89,60);c.stroke()}
 c.fillStyle=CC.ink;c.font='700 21px '+F;c.fillText(coDan(c,$('#hs-the').dataset.ten||'',420),120,75);
 const nhan=D.mau?'Dữ liệu minh họa':tk.demo?'Tài khoản demo':'Tài khoản thật';c.font='700 16px '+F;const nw=c.measureText(nhan).width+30;
 hop(c,W-56-nw,48,nw,38,19);c.fillStyle=D.mau?'rgba(255,196,0,.12)':'rgba(141,255,8,.1)';c.fill();c.strokeStyle=D.mau?'rgba(255,196,0,.55)':'rgba(141,255,8,.45)';c.lineWidth=1.5;c.stroke();
 c.fillStyle=D.mau?'#ffd34d':CC.series;c.fillText(nhan,W-56-nw+15,73);
 c.fillStyle=CC.ink;c.font='800 46px '+F;c.fillText('Hiệu suất giao dịch',56,158);
 let phu=KY[st.ngay]||'';if(v.length)phu+=' · '+ngayNgan(v[0].t)+' – '+ngayNgan(v[v.length-1].t);
 if(st.ma)phu+=' · '+st.ma;if(st.chieu)phu+=' · '+(st.chieu==='MUA'?'chỉ lệnh mua':'chỉ lệnh bán');
 c.fillStyle=CC.ink2;c.font='500 21px '+F;c.fillText(coDan(c,phu,540),56,196);
 const pct=T.so_du_dau>0&&T.rong!=null?T.rong/T.so_du_dau*100:null,dau=x=>x>0?'+':x<0?'−':'';
 const lon=coTien?tien(T.rong,t):pct!=null?dau(pct)+fmt(Math.abs(pct),1)+'%':'—';
 c.fillStyle=(T.rong||0)>=0?CC.gain:CC.loss;vua(c,lon,800,88,560);c.fillText(lon,52,300);
 c.fillStyle=CC.ink2;c.font='500 20px '+F;
 c.fillText(coTien?(pct!=null?dau(pct)+fmt(Math.abs(pct),1)+'% trên vốn đầu kỳ':'lãi ròng'):pct!=null?'lợi nhuận trên vốn đầu kỳ':'chưa tính được % (không rõ vốn đầu kỳ)',56,340);
 const X0=640,X1=W-56,Y0=126,Y1=392;
 if(v.length>1){const ys=v.map(p=>p.v).concat([0]),lo=Math.min(...ys),hi=Math.max(...ys),sp=(hi-lo)||1,X=i=>X0+i/(v.length-1)*(X1-X0),Y=x=>Y1-(x-lo)/sp*(Y1-Y0);
  c.setLineDash([5,6]);c.strokeStyle='rgba(255,255,255,.18)';c.lineWidth=1.5;c.beginPath();c.moveTo(X0,Y(0));c.lineTo(X1,Y(0));c.stroke();c.setLineDash([]);
  const g=c.createLinearGradient(0,Y0,0,Y1);g.addColorStop(0,'rgba(141,255,8,.32)');g.addColorStop(1,'rgba(141,255,8,0)');
  c.beginPath();v.forEach((p,i)=>i?c.lineTo(X(i),Y(p.v)):c.moveTo(X(i),Y(p.v)));c.lineTo(X(v.length-1),Y1);c.lineTo(X0,Y1);c.closePath();c.fillStyle=g;c.fill();
  c.beginPath();v.forEach((p,i)=>i?c.lineTo(X(i),Y(p.v)):c.moveTo(X(i),Y(p.v)));c.strokeStyle=CC.series;c.lineWidth=4;c.shadowColor='rgba(141,255,8,.55)';c.shadowBlur=14;c.stroke();c.shadowBlur=0;
  const ex=X(v.length-1),ey=Y(v[v.length-1].v);c.beginPath();c.arc(ex,ey,7,0,7);c.fillStyle=CC.series;c.fill();c.lineWidth=3;c.strokeStyle=CC.bg;c.stroke()}
 const o=[['Tỷ lệ thắng',fmt(T.ty_le||0,1)+'%',null],['Hệ số lợi nhuận',T.pf==='inf'?'∞':fmt(T.pf,2),T.pf==='inf'||T.pf>1?CC.gain:T.pf!=null&&T.pf<1?CC.loss:null],
  ['Sụt vốn lớn nhất',coTien?(T.dd_max?'−'+fmt(T.dd_max)+' '+t:'—'):(T.dd_pct!=null?'−'+fmt(T.dd_pct,1)+'%':'—'),T.dd_max>0?CC.loss:null],['Số lệnh',fmt(T.n||0,0),null]];
 const bw=(W-112-3*16)/4;o.forEach(([n,g,mau],i)=>{const x=56+i*(bw+16);hop(c,x,428,bw,118,16);c.fillStyle=CC.card;c.fill();c.strokeStyle=CC.line;c.lineWidth=1.5;c.stroke();
  c.fillStyle=CC.ink2;c.font='600 17px '+F;c.fillText(coDan(c,n,bw-40),x+20,462);c.fillStyle=mau||CC.ink;vua(c,g,800,38,bw-40);c.fillText(coDan(c,g,bw-40),x+20,520)});
 c.fillStyle='rgba(164,170,154,.85)';c.font='500 14px '+F;c.fillText(coDan(c,'Kết quả quá khứ không bảo đảm kết quả tương lai · không phải lời khuyên đầu tư',620),56,596);
 c.textAlign='right';const web=$('#hs-the').dataset.web||'';c.fillText(ngayNgan(Date.now()),W-56,web?574:596);if(web){c.fillStyle=CC.series;c.font='700 16px '+F;c.fillText(web,W-56,598)}c.textAlign='left'}
const theDlg=$('#hs-the'),theCv=$('#the-cv'),theTt=$('#the-tt');
const veLai=()=>veThe(theCv,$('#the-tien').checked).catch(e=>{theTt.textContent=e.message});
const blob=()=>new Promise((ok,loi)=>theCv.toBlob(b=>b?ok(b):loi(new Error('Không tạo được ảnh')),'image/png'));
$('#hs-chia').addEventListener('click',()=>{if(!D||!D.san_sang||!D.tong||!D.tong.n){alert('Chưa có lệnh đã đóng để tạo ảnh.');return}
 theTt.textContent='';if(theDlg.showModal)theDlg.showModal();else theDlg.setAttribute('open','');veLai()});
$('#the-dong').addEventListener('click',()=>theDlg.close?theDlg.close():theDlg.removeAttribute('open'));
theDlg.addEventListener('click',e=>{if(e.target===theDlg)theDlg.close()});
$('#the-tien').addEventListener('change',veLai);
$('#the-tai').addEventListener('click',async()=>{try{const b=await blob(),u=URL.createObjectURL(b),a=document.createElement('a');
 a.href=u;a.download='hieu-suat-'+new Date().toISOString().slice(0,10)+'.png';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),4000);theTt.textContent='Đã tải ảnh.'}catch(e){theTt.textContent=e.message}});
$('#the-chep').addEventListener('click',async()=>{try{if(!navigator.clipboard||!window.ClipboardItem)throw new Error('Trình duyệt này không cho sao chép ảnh; hãy dùng nút tải ảnh.');
 await navigator.clipboard.write([new ClipboardItem({'image/png':blob()})]);theTt.textContent='Đã sao chép ảnh, dán vào bài đăng hoặc tin nhắn.'}catch(e){theTt.textContent=e.message||'Không sao chép được.'}});
boLoc();tai();setInterval(()=>{if(document.visibilityState==='visible'&&!st.mau)tai()},60000)})();
"""


def trang_hieu_suat(ten: str) -> str:
    ngay = ''.join(f'<button type="button" data-v="{v}">{n}</button>' for v, n in ((7, '7 ngày'), (30, '30 ngày'), (90, '90 ngày'), (365, '1 năm'), (0, 'Tất cả')))
    chieu = ''.join(f'<button type="button" data-v="{v}">{n}</button>' for v, n in (('', 'Cả hai chiều'), ('MUA', 'Mua'), ('BAN', 'Bán')))
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Phân tích hiệu suất · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'hieu-suat', '<button id="theme" type="button">Nền tối</button>') + '<main class="rong">',
        '<div class="hs-top"><div><h1>Phân tích hiệu suất giao dịch</h1><p>Đọc lịch sử lệnh trong MT5 của bạn và cho biết bạn thắng, thua ở đâu: '
        'chỉ số chính, đường vốn, lịch lãi/lỗ, nhận xét tự động và phân tích theo mã, phiên, giờ, thời gian giữ lệnh.</p></div><span class="hs-tk" id="hs-tk"></span></div>',
        f'<div class="hs-loc"><div class="sg" id="hs-ngay">{ngay}</div><div class="sg" id="hs-chieu">{chieu}</div>'
        '<select id="hs-ma" aria-label="Lọc theo mã"><option value="">Mọi mã</option></select><select id="hs-nguon" aria-label="Lọc theo nguồn"><option value="">Mọi nguồn</option></select>'
        '<span class="grow"></span><button type="button" class="ghost" id="hs-mau" aria-pressed="false">Xem dữ liệu minh họa</button>'
        '<a class="ghost" id="hs-csv" href="/api/hieu-suat.csv" download>Xuất CSV</a>'
        '<button type="button" class="ghost" id="hs-chia">Ảnh chia sẻ</button></div>',
        '<div id="hs-noi"><p class="small">Đang đọc lịch sử lệnh từ MT5…</p></div>',
        '<dialog class="hs-the" id="hs-the" aria-labelledby="the-tieu" data-ten="' + escape(ten) + '" data-web="' + escape(thuong_hieu.WEB) + '"><div class="the-dau"><b id="the-tieu">Ảnh chia sẻ kết quả</b>'
        '<button type="button" class="ghost nho" id="the-dong" aria-label="Đóng">✕</button></div><canvas id="the-cv" width="1200" height="630" role="img" aria-label="Ảnh tóm tắt hiệu suất"></canvas>'
        '<label class="the-chon"><input type="checkbox" id="the-tien"><span>Hiện số tiền. Mặc định ảnh chỉ hiện %, không lộ quy mô tài khoản.</span></label>'
        '<div class="the-nut"><button type="button" class="chinh" id="the-tai">Tải ảnh PNG</button><button type="button" class="ghost" id="the-chep">Sao chép ảnh</button>'
        '<span class="small" id="the-tt" role="status"></span></div><p class="small" style="margin:10px 0 0">Ảnh được vẽ ngay trên máy bạn, không tải lên đâu cả.</p></dialog>',
        '<p class="note" style="margin-top:22px"><b>Chỉ đọc.</b> Trang đọc lịch sử lệnh đã đóng trong MT5 (mặc định chỉ tài khoản demo) và không đặt, sửa hay đóng lệnh. '
        'Kết quả quá khứ không bảo đảm kết quả tương lai; không phải lời khuyên đầu tư.</p>',
        '<footer><span>Lệnh được ghép từ các lần khớp cùng mã vị thế (position); lãi ròng gồm lãi, hoa hồng, phí và swap. R là lãi ròng chia số tiền mất nếu chạm '
        'dừng lỗ đặt lúc mở lệnh (MT5 tính, order_calc_profit).</span> ' + escape(trang.mien_tru() if hasattr(trang, 'mien_tru') else trang.MIEN_TRU)
        + f'</footer></main><script>{trang.JS}</script><script>{JS}</script></body></html>'])
