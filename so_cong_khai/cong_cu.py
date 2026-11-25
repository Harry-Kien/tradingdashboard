"""Trang Công cụ (/cong-cu): máy tính cho giao dịch Forex và CFD, dùng thông số hợp đồng và giá trực tiếp của sàn (thi_truong.py).

Khối lượng theo rủi ro, giá trị pip/điểm, lãi lỗ, ký quỹ và mức gọi ký quỹ, điểm xoay (pivot) bốn kiểu, Fibonacci, R:R và kỳ vọng,
sụt vốn và chuỗi thua. Phần tính ở trình duyệt; ký quỹ và lãi lỗ được hỏi thêm MT5 (/api/tinh, hai hàm tính thuần) để có số chính xác
kể cả khi phải quy đổi tiền. Trang không đặt lệnh."""
from __future__ import annotations

from html import escape

from . import thi_truong_trang as TTT
from . import trang

CSS = r"""
.cc-dau{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;margin:16px 0 4px;padding:12px 14px;background:var(--card);border:1px solid var(--line);border-radius:14px}
.cc-dau label{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--mute)}
.cc-dau select{min-width:240px}.cc-dau input{min-height:36px;border:1px solid var(--line);border-radius:10px;background:var(--card2);color:var(--ink);padding:0 12px;font:inherit}
@media(max-width:640px){.cc-dau select{min-width:0;width:100%}.cc-dau label{flex:1 1 100%}}.cc-q{display:flex;gap:18px;flex-wrap:wrap;align-items:baseline;margin-left:auto}
.cc-q span{font-size:12px;color:var(--mute)}.cc-q b{display:block;font-size:20px;font-weight:600}
.cc-g{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,430px),1fr));gap:14px;margin-top:14px}
.cc{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}
.cc h2{margin:0 0 2px;font-size:16px}.cc>p.sub{margin:0 0 12px;font-size:12.5px;color:var(--ink2)}
.cc .f{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}
.cc label{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--mute)}
.cc input,.cc select{width:100%}
.cc .sg{margin:0}.cc .hang{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px}
.cc .kq{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin-top:12px}
.cc .kq>div{background:var(--card2);padding:10px 12px}.cc .kq span{display:block;font-size:11.5px;color:var(--mute)}.cc .kq b{display:block;font-size:18px;font-weight:600;line-height:1.3}
.cc .kq .lon{grid-column:1/-1}.cc .kq .lon b{font-size:28px;color:var(--series)}
.cc .kq small{display:block;font-size:11.5px;color:var(--ink2)}
.cc .canh{font-size:12.5px;color:var(--warn);margin:10px 0 0}
.cc table{font-size:12.5px}.cc td,.cc th{padding:6px 10px}
.cc tr.gan td{background:color-mix(in srgb,var(--series) 12%,transparent)}
.cc tr.hien td{background:color-mix(in srgb,var(--loss) 14%,transparent);font-weight:600}
.cc .nho{font-size:11.5px;color:var(--mute);margin-top:8px}
.cc .lnk{font-size:12px;border:1px solid var(--line);background:var(--card2);color:var(--ink2);border-radius:8px;padding:5px 9px;cursor:pointer;font-family:inherit}
.cc .lnk:hover{color:var(--series);border-color:var(--series)}
.mt5tag[hidden]{display:none}.mt5tag{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.06em;color:var(--series);border:1px solid color-mix(in srgb,var(--series) 50%,transparent);border-radius:999px;padding:1px 6px;margin-left:6px;vertical-align:2px}
"""

JS = r"""
(()=>{const T=TT,$=s=>document.querySelector(s),esc=T.esc,fmt=T.fmt,pct=T.pct;
const sp=new URLSearchParams(location.search);let ma=sp.get('ma')||'';try{ma=ma||localStorage.getItem('cc-ma')||''}catch(e){}
const v=id=>{const x=parseFloat(String($('#'+id).value).replace(',','.'));return isFinite(x)?x:null},dat=(id,x)=>{const el=$('#'+id);if(el&&document.activeElement!==el)el.value=x};
const nho=id=>{const el=$('#'+id);try{const x=localStorage.getItem('cc-'+id);if(x!=null)el.value=x}catch(e){}el.addEventListener('input',()=>{try{localStorage.setItem('cc-'+id,el.value)}catch(e){}})};
['von','rr-pct','pip-lot','pl-lot','kq-lot','fb-w'].forEach(nho);
T.pill($('#song'));
const X=()=>T.by().get(ma),tien=()=>(T.S&&T.S.tai_khoan&&T.S.tai_khoan.tien)||'USD',d=()=>X()?X().so_le:5;
const don=x=>x.pip?{k:x.pip,n:'pip'}:{k:x.diem,n:'điểm'};
const gp=(p)=>fmt(p,d()),tn=(x,s)=>fmt(x,2)+' '+(s||tien());
const lamTron=(lot,x)=>{const b=x.lot_buoc||.01;return Math.floor(lot/b+1e-9)*b};
const chieu={rr:'mua',pl:'mua',kq:'mua',fb:'tang'};
document.querySelectorAll('.sg[data-ch]').forEach(g=>g.addEventListener('click',e=>{const b=e.target.closest('button[data-v]');if(!b)return;chieu[g.dataset.ch]=b.dataset.v;g.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));
 if(g.dataset.ch==='rr'&&$('#rr-song').checked)dat('rr-vao','');tinh()}));
let slKieu='gia';$('#rr-slk').addEventListener('click',e=>{const b=e.target.closest('button[data-v]');if(!b)return;slKieu=b.dataset.v;$('#rr-slk').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));$('#rr-sl').value='';tinh()});
let pvKieu='co';$('#pv-k').addEventListener('click',e=>{const b=e.target.closest('button[data-v]');if(!b)return;pvKieu=b.dataset.v;$('#pv-k').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));tinh()});
// ---- hỏi MT5 số chính xác (ký quỹ, lãi lỗ), gom lại để không gọi dồn
// Nhịp đều (throttle) chứ không chờ yên (debounce): giá chạy theo tick gọi hàm này liên tục, chờ yên thì không bao giờ hỏi được.
// Mỗi ô hỏi nhiều nhất một lần mỗi 350 ms, luôn với số mới nhất; câu trả lời của lượt cũ về muộn thì bỏ, để không đè số mới.
const MT={};let hen={},cho={},luot={};
function hoi(key,q,cb){cho[key]=[q,cb];if(hen[key])return;hen[key]=setTimeout(async()=>{hen[key]=0;const[q,cb]=cho[key],k=JSON.stringify(q),so=luot[key]=(luot[key]||0)+1;
 if(MT[k]){cb(MT[k]);return}
 try{const r=await fetch('/api/tinh?'+new URLSearchParams(q),{cache:'no-store'});if(!r.ok)throw 0;const j=await r.json();
  if(Object.keys(MT).length>300)for(const c in MT)delete MT[c];MT[k]=j;if(so===luot[key])cb(j)}catch(e){if(so===luot[key])cb(null)}},350)}
function gia(ch){const x=X();if(!x||!x.q)return null;return ch==='ban'?x.q[0]:x.q[1]}
function chonMa(){const x=X();if(!x)return;$('#cc-ma').value=ma;try{localStorage.setItem('cc-ma',ma)}catch(e){}
 try{history.replaceState(null,'','?ma='+encodeURIComponent(ma))}catch(e){}document.title='Công cụ · '+x.goc;
 ['rr-vao','rr-sl','pl-vao','pl-ra','kq-vao','fb-cao','fb-thap','rk-vao','rk-sl','rk-tp'].forEach(id=>{const el=$('#'+id);if(el)el.value=''});$('#rr-song').checked=true;rrMT=null;
 document.querySelectorAll('.dv').forEach(el=>el.textContent=don(x).n);tinh()}
$('#cc-ma').addEventListener('change',e=>{ma=e.target.value;chonMa()});
function dau(){const x=X();if(!x)return;const q=x.q;$('#cc-bid').textContent=q?gp(q[0]):'—';$('#cc-ask').textContent=q?gp(q[1]):'—';$('#cc-sp').textContent=T.spTxt(x);
 const c=T.doi(x,'ngay');$('#cc-doi').innerHTML=`<span class="${T.cls(c)}">${pct(c)}</span>`;$('#cc-ten').textContent=T.tenMa(x)}
// ---- 1. khối lượng theo rủi ro
let rrMT=null;
function khoiLuong(){const x=X();if(!x)return;const von=v('von'),p=v('rr-pct'),ch=chieu.rr,u=don(x);
 let vao=v('rr-vao');if($('#rr-song').checked||vao==null){vao=gia(ch);if(vao!=null)dat('rr-vao',vao.toFixed(x.so_le))}
 let sl=v('rr-sl');if(sl==null){$('#rr-kq').innerHTML='<div class="lon"><span>Khối lượng</span><b>—</b><small>Nhập dừng lỗ '+(slKieu==='gia'?'(mức giá)':'(khoảng cách, '+u.n+')')+' để tính.</small></div>';return}
 const kc=slKieu==='gia'?Math.abs(vao-sl):sl*u.k,giaSl=slKieu==='gia'?sl:(ch==='mua'?vao-kc:vao+kc);
 if(slKieu==='gia'&&((ch==='mua'&&sl>=vao)||(ch==='ban'&&sl<=vao))){$('#rr-kq').innerHTML=`<div class="lon"><span>Khối lượng</span><b>—</b><small>Dừng lỗ của lệnh ${ch==='mua'?'MUA phải thấp hơn':'BÁN phải cao hơn'} giá vào.</small></div>`;return}
 if(!von||!p||!kc||!x.gt1){return}
 const tienRui=von*p/100,moiLot=kc*x.gt1,lot0=tienRui/moiLot;let lot=Math.min(lamTron(lot0,x),x.lot_max||1e9),canh='';
 if(lot<(x.lot_min||.01)){canh=`Vốn và mức rủi ro này chưa đủ cho khối lượng nhỏ nhất (${fmt(x.lot_min,x.lot_min<.01?3:2)} lot): ở mức đó bạn mất ${tn(moiLot*x.lot_min)} (${pct(moiLot*x.lot_min/von*100).replace('+','')} vốn) nếu chạm dừng lỗ.`;lot=0}
 const thuc=lot*moiLot,dp=Math.max(0,(String(x.lot_buoc||.01).split('.')[1]||'').length),khoaMT=ma+'|'+ch+'|'+lot.toFixed(dp),cuMT=rrMT&&rrMT.k===khoaMT?rrMT:null;   // số MT5 gần nhất cho cùng mã, chiều, khối lượng (giá vào nhích theo tick)
 const tp=[1,2,3].map(r=>ch==='mua'?vao+kc*r:vao-kc*r);
 $('#rr-kq').innerHTML=`<div class="lon"><span>Khối lượng nên vào</span><b>${lot?fmt(lot,dp)+' lot':'—'}</b><small>${lot?'Lý thuyết '+fmt(lot0,4)+' lot, làm tròn xuống theo bước '+fmt(x.lot_buoc,dp)+' của sàn':''}</small></div>
  <div><span>Tiền rủi ro thực tế</span><b>${tn(thuc)}</b><small>${pct(thuc/von*100).replace('+','')} vốn</small></div>
  <div><span>Khoảng dừng lỗ</span><b>${fmt(kc/u.k,u.n==='pip'?1:0)} ${u.n}</b><small>dừng lỗ ở ${gp(giaSl)}</small></div>
  <div><span>Giá trị 1 ${u.n} ở khối lượng này</span><b>${tn(lot*x.gt1*u.k)}</b><small>${tn(x.gt1*u.k)} cho 1 lot</small></div>
  <div><span>Ký quỹ cần <i class="mt5tag" id="rr-mt5"${cuMT?'':' hidden'}>MT5</i></span><b id="rr-kqy">${cuMT?tn(cuMT.ky_quy):lot&&x.ky_quy_1lot?tn(x.ky_quy_1lot*lot):'—'}</b><small id="rr-kqp">${cuMT?pct(cuMT.ky_quy/von*100).replace('+','')+' vốn bị giữ làm ký quỹ':''}</small></div>
  <div><span>Chốt lời 1R · 2R · 3R</span><b style="font-size:14px">${tp.map(gp).join(' · ')}</b><small>lãi ${tn(thuc)} · ${tn(thuc*2)} · ${tn(thuc*3)}</small></div>`;
 $('#rr-canh').textContent=canh;$('#rr-canh').hidden=!canh;
 if(lot)hoi('rr',{ma,loai:ch,lot:lot.toFixed(dp),vao:vao.toFixed(x.so_le)},j=>{if(!j||j.ky_quy==null)return;rrMT={k:khoaMT,ky_quy:j.ky_quy};const e=$('#rr-kqy');if(!e)return;e.textContent=tn(j.ky_quy);$('#rr-mt5').hidden=false;$('#rr-kqp').textContent=pct(j.ky_quy/von*100).replace('+','')+' vốn bị giữ làm ký quỹ'})}
// ---- 2. giá trị pip / điểm
function giaTriPip(){const x=X();if(!x)return;const u=don(x),lot=v('pip-lot')||1,rows=[[.01,'0,01 lot (micro)'],[.1,'0,1 lot (mini)'],[1,'1 lot (chuẩn)']];if(![.01,.1,1].includes(lot))rows.push([lot,fmt(lot,2)+' lot (bạn nhập)']);
 $('#pip-kq').innerHTML='<table><thead><tr><th>Khối lượng</th><th class="r">1 '+u.n+'</th><th class="r">10 '+u.n+'</th><th class="r">Giá đi 1,0</th><th class="r">Giá đi 1%</th></tr></thead><tbody>'+
  rows.map(([l,n])=>`<tr><td>${n}</td><td class="r">${tn(l*x.gt1*u.k)}</td><td class="r">${tn(l*x.gt1*u.k*10)}</td><td class="r">${tn(l*x.gt1)}</td><td class="r">${x.q?tn(l*x.gt1*x.q[0]/100):'—'}</td></tr>`).join('')+'</tbody></table>'+
  `<p class="nho">1 ${u.n} = ${fmt(u.k,Math.max(0,x.so_le-(x.pip?1:0)))} giá · kích thước hợp đồng ${fmt(x.co_hd,x.co_hd%1?2:0)} ${esc(x.tien_goc||'')}. Giá trị quy ra ${tien()} theo tỷ giá hiện tại của MT5${x.tien_lai&&x.tien_lai!==tien()?' (tiền lãi lỗ của mã là '+esc(x.tien_lai)+')':''}.</p>`}
// ---- 3. lãi lỗ
function laiLo(){const x=X();if(!x)return;const ch=chieu.pl,lot=v('pl-lot')||1,u=don(x);let vao=v('pl-vao'),ra=v('pl-ra');
 if(vao==null&&x.q){vao=gia(ch);dat('pl-vao',vao.toFixed(x.so_le))}if(ra==null||vao==null){$('#pl-kq').innerHTML='<div class="lon"><span>Lãi / lỗ</span><b>—</b><small>Nhập giá đóng lệnh.</small></div>';return}
 const dif=(ch==='mua'?ra-vao:vao-ra),uoc=dif*x.gt1*lot,von=v('von');
 const ve=(lai,mt5)=>{$('#pl-kq').innerHTML=`<div class="lon"><span>Lãi / lỗ${mt5?' <i class="mt5tag">MT5</i>':' (ước tính)'}</span><b class="${T.cls(lai)}" style="color:var(--${lai>=0?'gain':'loss'})">${lai>=0?'+':'−'}${tn(Math.abs(lai))}</b><small>${von?pct(lai/von*100)+' vốn':''}</small></div>
  <div><span>Số ${u.n}</span><b>${dif>=0?'+':'−'}${fmt(Math.abs(dif)/u.k,u.n==='pip'?1:0)}</b></div><div><span>Thay đổi giá</span><b>${pct(dif/vao*100,3)}</b></div>`};
 ve(uoc,0);hoi('pl',{ma,loai:ch,lot,vao,ra},j=>{if(j&&j.lai!=null)ve(j.lai,1)})}
// ---- 4. ký quỹ và mức an toàn
function kyQuy(){const x=X();if(!x)return;const ch=chieu.kq,lot=v('kq-lot')||1,von=v('von'),tk=T.S.tai_khoan||{},u=don(x);let vao=v('kq-vao');
 if(vao==null&&x.q){vao=gia(ch);dat('kq-vao',vao.toFixed(x.so_le))}if(vao==null)return;
 const ve=(m,mt5)=>{const dn=x.gt1*vao*lot,call=tk.goi_ky_quy||50,so=tk.dung_lenh||0;
  const lv=m?von/m*100:null,chiu=m&&von?(von-call/100*m)/(x.gt1*lot):null,chiuSo=m&&von&&so?(von-so/100*m)/(x.gt1*lot):null;
  $('#kq-kq').innerHTML=`<div class="lon"><span>Ký quỹ cần${mt5?' <i class="mt5tag">MT5</i>':' (ước tính)'}</span><b>${m?tn(m):'—'}</b><small>${von&&m?pct(m/von*100).replace('+','')+' vốn bị giữ':''}</small></div>
   <div><span>Giá trị danh nghĩa</span><b>${tn(dn)}</b><small>đòn bẩy thực ${m?'1:'+fmt(dn/m,0):'—'}</small></div>
   <div><span>Mức ký quỹ lúc mở</span><b>${lv?fmt(lv,0)+'%':'—'}</b><small>vốn / ký quỹ</small></div>
   <div><span>Giá chạm gọi ký quỹ (${fmt(call,0)}%)</span><b>${chiu!=null&&chiu>0?gp(ch==='mua'?vao-chiu:vao+chiu):'—'}</b><small>${chiu!=null&&chiu>0?'giá đi ngược '+fmt(chiu/u.k,u.n==='pip'?0:0)+' '+u.n+' ('+fmt(chiu/vao*100,2)+'%)':'vốn không đủ'}</small></div>
   ${chiuSo!=null&&chiuSo>0?`<div><span>Giá bị đóng lệnh (${fmt(so,0)}%)</span><b>${gp(ch==='mua'?vao-chiuSo:vao+chiuSo)}</b></div>`:''}`};
 ve(x.ky_quy_1lot?x.ky_quy_1lot*lot:null,0);hoi('kq',{ma,loai:ch,lot,vao},j=>{if(j&&j.ky_quy!=null)ve(j.ky_quy,1)})}
// ---- 5. pivot
function pivot(){const x=X();if(!x)return;const q=x.hom_qua,el=$('#pv-kq');if(!q){el.innerHTML='<p class="small">Chưa có nến ngày trước của mã này.</p>';return}
 const H=q.cao,L=q.thap,C=q.dong,R=H-L;let lv;
 if(pvKieu==='co'){const P=(H+L+C)/3;lv={R3:H+2*(P-L),R2:P+R,R1:2*P-L,P,S1:2*P-H,S2:P-R,S3:L-2*(H-P)}}
 else if(pvKieu==='fib'){const P=(H+L+C)/3;lv={R3:P+R,R2:P+.618*R,R1:P+.382*R,P,S1:P-.382*R,S2:P-.618*R,S3:P-R}}
 else if(pvKieu==='cam'){const k=R*1.1;lv={R4:C+k/2,R3:C+k/4,R2:C+k/6,R1:C+k/12,P:(H+L+C)/3,S1:C-k/12,S2:C-k/6,S3:C-k/4,S4:C-k/2}}
 else{const P=(H+L+2*C)/4;lv={R3:H+2*(P-L),R2:P+R,R1:2*P-L,P,S1:2*P-H,S2:P-R,S3:L-2*(H-P)}}
 const b=x.q&&x.q[0],u=don(x),ds=Object.entries(lv);let gan=null;if(b!=null)for(const[k,p]of ds)if(gan==null||Math.abs(p-b)<Math.abs(lv[gan]-b))gan=k;
 let h='<table><thead><tr><th>Mức</th><th class="r">Giá</th><th class="r">Cách giá hiện tại</th></tr></thead><tbody>',chen=false;
 for(const[k,p]of ds){if(b!=null&&!chen&&b>p){h+=`<tr class="hien"><td>Giá hiện tại</td><td class="r">${gp(b)}</td><td></td></tr>`;chen=true}
  h+=`<tr class="${k===gan?'gan':''}"><td><b>${k==='P'?'P (trục)':k}</b></td><td class="r">${gp(p)}</td><td class="r">${b!=null?(p>=b?'+':'−')+fmt(Math.abs(p-b)/u.k,u.n==='pip'?1:0)+' '+u.n:''}</td></tr>`}
 if(b!=null&&!chen)h+=`<tr class="hien"><td>Giá hiện tại</td><td class="r">${gp(b)}</td><td></td></tr>`;
 el.innerHTML=h+`</tbody></table><p class="nho">Tính từ nến ngày trước của sàn: cao ${gp(H)}, thấp ${gp(L)}, đóng ${gp(C)}. Mức tô xanh là mức gần giá nhất. Pivot là mức tham chiếu nhiều người cùng nhìn, không phải điểm vào lệnh.</p>`}
// ---- 6. Fibonacci
function fibo(){const x=X();if(!x)return;let H=v('fb-cao'),L=v('fb-thap');const h=x.hom_nay;
 if(H==null&&h){H=Math.max(h.cao,x.q?x.q[0]:h.cao);dat('fb-cao',H.toFixed(x.so_le))}if(L==null&&h){L=Math.min(h.thap,x.q?x.q[0]:h.thap);dat('fb-thap',L.toFixed(x.so_le))}
 if(H==null||L==null||H<=L){$('#fb-kq').innerHTML='<p class="small">Nhập đỉnh cao hơn đáy.</p>';return}
 const R=H-L,tang=chieu.fb==='tang',b=x.q&&x.q[0],u=don(x);
 const hoi_=[0,.236,.382,.5,.618,.786,1].map(r=>[r,tang?H-R*r:L+R*r]),mo=[1.272,1.618,2.618].map(r=>[r,tang?L+R*r:H-R*r]);
 const dong=([r,p],loai)=>`<tr><td>${loai} ${fmt(r*100,1)}%</td><td class="r">${gp(p)}</td><td class="r">${b!=null?(p>=b?'+':'−')+fmt(Math.abs(p-b)/u.k,u.n==='pip'?1:0)+' '+u.n:''}</td></tr>`;
 $('#fb-kq').innerHTML='<table><thead><tr><th>Mức</th><th class="r">Giá</th><th class="r">Cách giá hiện tại</th></tr></thead><tbody>'+hoi_.map(a=>dong(a,'Hồi')).join('')+mo.map(a=>dong(a,'Mở rộng')).join('')+
  `</tbody></table><p class="nho">${tang?'Sóng tăng từ đáy lên đỉnh: mức hồi đo từ đỉnh xuống; mức mở rộng là mục tiêu phía trên đỉnh.':'Sóng giảm từ đỉnh xuống đáy: mức hồi đo từ đáy lên; mức mở rộng là mục tiêu phía dưới đáy.'} Mặc định lấy đỉnh và đáy hôm nay.</p>`}
// ---- 7. R:R và kỳ vọng
function rrKyVong(){const x=X();if(!x)return;let vao=v('rk-vao');if(vao==null&&x.q){vao=x.q[1];dat('rk-vao',vao.toFixed(x.so_le))}const sl=v('rk-sl'),tp=v('rk-tp'),w=(v('fb-w')??40)/100,u=don(x);
 if(vao==null||sl==null||tp==null||sl===vao){$('#rk-kq').innerHTML='<p class="small">Nhập giá vào, dừng lỗ và chốt lời.</p>';return}
 const rui=Math.abs(vao-sl),lai=Math.abs(tp-vao),rr=lai/rui,hv=1/(1+rr),kv=w*rr-(1-w),von=v('von'),p=v('rr-pct')||1;
 $('#rk-kq').innerHTML=`<div><span>Tỷ lệ lời : lỗ</span><b>1 : ${fmt(rr,2)}</b><small>${fmt(lai/u.k,u.n==='pip'?1:0)} / ${fmt(rui/u.k,u.n==='pip'?1:0)} ${u.n}</small></div>
  <div><span>Tỷ lệ thắng hòa vốn</span><b>${fmt(hv*100,1)}%</b><small>chưa tính spread, phí</small></div>
  <div><span>Kỳ vọng mỗi lệnh</span><b class="${T.cls(kv)}" style="color:var(--${kv>=0?'gain':'loss'})">${kv>=0?'+':'−'}${fmt(Math.abs(kv),2)}R</b><small>${von?'≈ '+(kv>=0?'+':'−')+tn(Math.abs(kv)*von*p/100)+' mỗi lệnh ở '+fmt(p,1)+'% rủi ro':''}</small></div>
  <div><span>Sau 100 lệnh như vậy</span><b>${kv>=0?'+':'−'}${fmt(Math.abs(kv)*100,0)}R</b><small>nếu tỷ lệ thắng thật là ${fmt(w*100,0)}%</small></div>`}
// ---- 8. sụt vốn và chuỗi thua
function chuoiThua(){const p=(v('rr-pct')||1)/100,w=(v('fb-w')??40)/100,n=Math.max(1,Math.round(v('ct-n')||5)),m=Math.max(n,Math.round(v('ct-m')||100));
 let a=new Array(n).fill(0);a[0]=1;for(let i=0;i<m;i++){const b=new Array(n).fill(0);let s=0;for(let k=0;k<n;k++){b[0]+=a[k]*w;if(k+1<n)b[k+1]+=a[k]*(1-w)}a=b}
 const khong=a.reduce((s,x)=>s+x,0),con=Math.pow(1-p,n);
 $('#ct-kq').innerHTML=`<div><span>Xác suất gặp ít nhất ${n} lệnh thua liên tiếp trong ${m} lệnh</span><b>${fmt((1-khong)*100,1)}%</b><small>với tỷ lệ thắng ${fmt(w*100,0)}%</small></div>
  <div><span>Sau ${n} lệnh thua liền, mỗi lệnh rủi ro ${fmt(p*100,1)}%</span><b>${fmt(con*100,1)}% vốn</b><small>cần lãi ${fmt((1/con-1)*100,1)}% để về lại</small></div>`;
 $('#ct-bang').innerHTML='<table><thead><tr><th>Sụt vốn</th>'+[10,20,30,40,50,60,75,90].map(x=>`<th class="r">${x}%</th>`).join('')+'</tr></thead><tbody><tr><td>Cần lãi để hồi</td>'+[10,20,30,40,50,60,75,90].map(x=>`<td class="r">${fmt((1/(1-x/100)-1)*100,0)}%</td>`).join('')+'</tr></tbody></table>'}
function tinh(){if(!X())return;dau();for(const f of[khoiLuong,giaTriPip,laiLo,kyQuy,pivot,fibo,rrKyVong,chuoiThua])try{f()}catch(e){console.error(e)}}
document.querySelectorAll('.cc input').forEach(el=>el.addEventListener('input',()=>{if(el.id==='rr-vao')$('#rr-song').checked=false;tinh()}));
$('#rr-song').addEventListener('change',()=>{if($('#rr-song').checked)dat('rr-vao','');tinh()});
$('#fb-hq').addEventListener('click',()=>{const x=X();if(x&&x.hom_qua){$('#fb-cao').value=x.hom_qua.cao.toFixed(x.so_le);$('#fb-thap').value=x.hom_qua.thap.toFixed(x.so_le);fibo()}});
$('#fb-hn').addEventListener('click',()=>{$('#fb-cao').value='';$('#fb-thap').value='';fibo()});
$('#pl-gia').addEventListener('click',()=>{const x=X();if(x&&x.q){$('#pl-vao').value=gia(chieu.pl).toFixed(x.so_le);laiLo()}});
// giá mới của mã đang chọn: vẽ ở khung hình kế tiếp (gộp các tick dồn trong một khung hình), hoặc sau 100 ms nếu trình duyệt đang hãm
// requestAnimationFrame (cửa sổ bị che). Không bỏ tick nào: tick cuối luôn được vẽ.
let choVe=0;function henSong(){if(choVe)return;choVe=1;const f=()=>{if(!choVe)return;choVe=0;dau();if($('#rr-song').checked)khoiLuong();pivot()};requestAnimationFrame(f);setTimeout(f,100)}
let daChon=0;T.on((l,ds)=>{if(l==='anh'){const s=$('#cc-ma');if(!s.options.length||s.dataset.n!=String(T.by().size)){s.innerHTML=T.nhomOpt(ma);s.dataset.n=T.by().size}
  if(!X()){const e=[...T.by().values()].find(x=>x.goc==='EURUSD')||[...T.by().values()][0];if(e){ma=e.ma;daChon=0}}if(!daChon&&X()){daChon=1;chonMa()}else tinh();return}
 if(l==='gia'&&ds.includes(ma))henSong()});
T.batDau(30)})();
"""


def _o(id_: str, nhan: str, mac_dinh: str = '', goi_y: str = '', kieu: str = 'number') -> str:
    return (f'<label>{nhan}<input id="{id_}" type="{kieu}" inputmode="decimal" step="any" value="{escape(mac_dinh)}"'
            + (f' placeholder="{escape(goi_y)}"' if goi_y else '') + '></label>')


def _sg(ten: str, ds: list[tuple[str, str]], mac_dinh: str, id_: str = '') -> str:
    return (f'<div class="sg"' + (f' data-ch="{ten}"' if ten else '') + (f' id="{id_}"' if id_ else '') + '>'
            + ''.join(f'<button type="button" data-v="{k}" aria-pressed="{"true" if k == mac_dinh else "false"}">{n}</button>' for k, n in ds) + '</div>')


def trang_cong_cu(ten: str) -> str:
    mb = [('mua', 'Mua'), ('ban', 'Bán')]
    the = [
        ('Khối lượng theo mức rủi ro', 'Nhập số tiền bạn chấp nhận mất nếu chạm dừng lỗ; trang tính số lot đúng với thông số hợp đồng của sàn.',
         f'<div class="hang">{_sg("rr", mb, "mua")}<label style="flex-direction:row;align-items:center;gap:6px;font-size:12.5px;color:var(--ink2)">'
         '<input type="checkbox" id="rr-song" checked style="width:auto"> Giá vào theo giá trực tiếp</label></div>'
         f'<div class="f">{_o("rr-pct", "Rủi ro mỗi lệnh (%)", "1")}{_o("rr-vao", "Giá vào")}'
         f'<label>Dừng lỗ theo {_sg("", [("gia", "Mức giá"), ("kc", "Khoảng cách")], "gia", "rr-slk")}<input id="rr-sl" type="number" inputmode="decimal" step="any" placeholder="Nhập dừng lỗ"></label></div>'
         '<div class="kq" id="rr-kq"></div><p class="canh" id="rr-canh" hidden></p>'),
        ('Giá trị pip và điểm', 'Một bước giá đáng bao nhiêu tiền ở từng khối lượng.',
         f'<div class="f">{_o("pip-lot", "Khối lượng của bạn (lot)", "0.5")}</div><div id="pip-kq" style="margin-top:12px;overflow-x:auto"></div>'),
        ('Lãi / lỗ của một lệnh', 'Số tiền lãi lỗ giữa giá vào và giá đóng; MT5 tính lại để có số chính xác kể cả khi phải quy đổi tiền.',
         f'<div class="hang">{_sg("pl", mb, "mua")}<button type="button" class="lnk" id="pl-gia">Lấy giá hiện tại</button></div>'
         f'<div class="f">{_o("pl-lot", "Khối lượng (lot)", "0.1")}{_o("pl-vao", "Giá vào")}{_o("pl-ra", "Giá đóng")}</div><div class="kq" id="pl-kq"></div>'),
        ('Ký quỹ và mức an toàn', 'Ký quỹ bị giữ khi mở lệnh, và giá phải đi ngược bao xa thì sàn gọi ký quỹ, nếu tài khoản chỉ có lệnh này.',
         f'<div class="hang">{_sg("kq", mb, "mua")}</div><div class="f">{_o("kq-lot", "Khối lượng (lot)", "0.1")}{_o("kq-vao", "Giá vào")}</div><div class="kq" id="kq-kq"></div>'),
        ('Điểm xoay (pivot) hôm nay', 'Các mức hỗ trợ và kháng cự tính từ đỉnh, đáy, giá đóng cửa của ngày trước.',
         f'<div class="hang">{_sg("", [("co", "Cổ điển"), ("fib", "Fibonacci"), ("cam", "Camarilla"), ("woo", "Woodie")], "co", "pv-k")}</div><div id="pv-kq" style="overflow-x:auto"></div>'),
        ('Fibonacci hồi và mở rộng', 'Các mức hồi 23,6–78,6% và mục tiêu mở rộng 127,2–261,8% của một sóng giá.',
         f'<div class="hang">{_sg("fb", [("tang", "Sóng tăng"), ("giam", "Sóng giảm")], "tang")}<button type="button" class="lnk" id="fb-hn">Đỉnh/đáy hôm nay</button>'
         '<button type="button" class="lnk" id="fb-hq">Đỉnh/đáy hôm qua</button></div>'
         f'<div class="f">{_o("fb-cao", "Đỉnh")}{_o("fb-thap", "Đáy")}</div><div id="fb-kq" style="margin-top:12px;overflow-x:auto"></div>'),
        ('Tỷ lệ lời/lỗ (R:R) và kỳ vọng', 'Một kế hoạch có lãi lâu dài khi tỷ lệ thắng thật cao hơn tỷ lệ thắng hòa vốn.',
         f'<div class="f">{_o("rk-vao", "Giá vào")}{_o("rk-sl", "Dừng lỗ")}{_o("rk-tp", "Chốt lời")}{_o("fb-w", "Tỷ lệ thắng ước tính (%)", "40")}</div><div class="kq" id="rk-kq"></div>'),
        ('Sụt vốn và chuỗi thua', 'Chuỗi thua dài xảy ra thường hơn người ta nghĩ; mức rủi ro mỗi lệnh quyết định bạn còn bao nhiêu vốn sau đó.',
         f'<div class="f">{_o("ct-n", "Số lệnh thua liên tiếp", "6")}{_o("ct-m", "Trong bao nhiêu lệnh", "100")}</div><div class="kq" id="ct-kq"></div>'
         '<div id="ct-bang" style="margin-top:12px;overflow-x:auto"></div><p class="nho">Dùng mức rủi ro (%) ở thẻ đầu và tỷ lệ thắng ở thẻ R:R.</p>'),
    ]
    cards = ''.join(f'<section class="cc"><h2>{t}</h2><p class="sub">{s}</p>{b}</section>' for t, s, b in the)
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Công cụ · {escape(ten)}</title><style>{trang.CSS}{TTT.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'cong-cu', '<button id="theme" type="button">Nền tối</button>') + '<main class="rong">',
        '<div class="tt-top"><div><h1>Công cụ giao dịch</h1><p>Tính khối lượng, rủi ro, ký quỹ và các mức giá cho bất kỳ cặp tiền hay CFD nào của sàn, '
        'theo thông số hợp đồng và giá trực tiếp.</p></div><span id="song" class="song-pill"><i></i>Đang nối…</span></div>',
        '<div class="cc-dau"><label>Mã<select id="cc-ma" aria-label="Chọn mã"></select></label>'
        f'<label>Vốn tài khoản<input id="von" type="number" inputmode="decimal" step="any" value="1000" style="width:140px"></label>'
        '<div class="cc-q"><div><span id="cc-ten">—</span></div><div><span>Bid</span><b id="cc-bid">—</b></div><div><span>Ask</span><b id="cc-ask">—</b></div>'
        '<div><span>Spread</span><b id="cc-sp">—</b></div><div><span>Hôm nay</span><b id="cc-doi">—</b></div></div></div>',
        f'<div class="cc-g">{cards}</div>',
        '<p class="note" style="margin-top:22px"><b>Công cụ tính, không phải lời khuyên.</b> Số liệu dựa trên thông số hợp đồng và giá của MT5 demo lúc này; '
        'tài khoản thật có thể khác về spread, hoa hồng, ký quỹ và trượt giá. Trang không đặt lệnh.</p>',
        '<footer>Ký quỹ và lãi lỗ có nhãn MT5 là số do MT5 tính (order_calc_margin, order_calc_profit); số còn lại tính ở trình duyệt từ giá trị một bước giá '
        'của sàn. ' + escape(trang.MIEN_TRU) + f'</footer></main><script>{trang.JS}</script><script>{TTT.JS_CHUNG}</script><script>{JS}</script></body></html>'])
