# -*- coding: utf-8 -*-
"""Menu chuột phải của trang Biểu đồ (26/11/2026). Chỉ chạy trong trình duyệt, chỉ đọc: không đặt lệnh, không gọi MT5.

Bấm chuột phải (hoặc giữ ngón tay trên điện thoại) vào biểu đồ:
- chỗ trống: giá và giờ tại con trỏ, khoảng cách tới giá hiện tại (giá, %, ATR, USD cho 0,01 lot vàng); sao chép giá; đặt cảnh báo giá;
  vẽ ngay tại mức đó (ngang, tia ngang, dọc, chữ thập, nhãn giá); thử lệnh với dừng lỗ tại mức đó (vẽ vị thế R:R 1:2, tính lot,
  mở trang Kiểm tra lệnh); thông tin nến dưới con trỏ (mở, cao, thấp, đóng, biên độ theo ATR, % thân nến); về nến mới nhất; ẩn/hiện
  hình vẽ; biểu đồ trống; tải hoặc chép ảnh biểu đồ; toàn màn hình; xóa hết hình vẽ.
- trên một hình đã vẽ: sao chép giá, đặt cảnh báo tại đường đó, nhân bản, khóa vị trí, ẩn riêng hình đó, đưa lên trên/xuống dưới,
  đổi màu, độ dày, kiểu nét, xóa.
Phím tắt khi con trỏ ở trên biểu đồ: Alt+H đường ngang, Alt+J tia ngang, Alt+V đường dọc, Alt+A cảnh báo, Alt+C chép giá,
Alt+R về nến mới nhất, Alt+S tải ảnh.

Cảnh báo giá lưu trong trình duyệt theo từng mã và chỉ báo khi trang Biểu đồ của mã đó đang mở (nói rõ trong danh sách cảnh báo).
Đọc biểu đồ qua window.BDMN do bieu_do.py cung cấp; bieu_do.py gọi window.MNP.ve() sau mỗi lần vẽ lại."""
import json

from .thuong_hieu import TEN

CSS = r"""
.mnp{position:fixed;z-index:80;min-width:260px;max-width:min(340px,calc(100vw - 16px));max-height:calc(100vh - 16px);overflow:auto;background:var(--card);color:var(--ink);
 border:1px solid var(--line);border-radius:10px;box-shadow:0 12px 32px rgba(0,0,0,.3);padding:5px;font-size:13px;line-height:1.3}
.mnp .dau{padding:6px 10px 7px}
.mnp .dau b{display:block;font-size:14.5px;font-variant-numeric:tabular-nums}
.mnp .dau small{display:block;color:var(--ink2);font-size:11.5px;margin-top:2px;font-variant-numeric:tabular-nums}
.mnp button.mi{display:flex;align-items:center;gap:10px;width:100%;border:0;background:none;color:inherit;font:inherit;text-align:left;padding:6px 10px;border-radius:6px;cursor:pointer;min-height:32px}
.mnp button.mi:hover,.mnp button.mi:focus-visible{background:color-mix(in srgb,var(--series) 15%,transparent);outline:none}
.mnp button.mi[disabled]{opacity:.42;cursor:default;background:none}
.mnp .mi svg{flex:none;color:var(--ink2)}.mnp .mi span{flex:1}
.mnp .mi kbd{font:11px ui-monospace,Consolas,monospace;color:var(--ink2);border:1px solid var(--line);border-radius:4px;padding:1px 5px;white-space:nowrap}
.mnp .mi.xau,.mnp .mi.xau svg{color:var(--loss)}
.mnp hr{border:0;border-top:1px solid var(--line);margin:4px 6px}
.mnp .nhom{padding:6px 10px 3px;font-size:11px;font-weight:600;letter-spacing:.03em;color:var(--ink2)}
.mnp .nen{display:grid;grid-template-columns:auto 1fr auto 1fr;gap:3px 10px;padding:2px 10px 6px;font-size:12px;font-variant-numeric:tabular-nums}
.mnp .nen span{color:var(--ink2)}.mnp .nen b{font-weight:600}
.mnp .mau{display:flex;flex-wrap:wrap;gap:7px;padding:4px 10px 6px}
.mnp .mau button{width:22px;height:22px;border-radius:50%;border:2px solid var(--line);padding:0;cursor:pointer}
.mnp .mau button[aria-pressed=true]{outline:2px solid var(--ink);outline-offset:2px}
.mnp .hang{display:flex;gap:4px;padding:2px 10px 5px}
.mnp .hang button{flex:1;min-height:28px;border:1px solid var(--line);background:none;color:inherit;border-radius:6px;cursor:pointer;font:inherit;font-size:12px}
.mnp .hang button[aria-pressed=true]{border-color:var(--series);background:color-mix(in srgb,var(--series) 15%,transparent)}
.mnp-bao{position:absolute;left:50%;bottom:44px;transform:translate(-50%,8px);z-index:6;background:var(--ink);color:var(--card);padding:7px 12px;border-radius:8px;font-size:12.5px;
 opacity:0;pointer-events:none;transition:opacity .18s,transform .18s;max-width:calc(100% - 24px)}
.mnp-bao.hien{opacity:.94;transform:translate(-50%,0)}
@media (pointer:coarse){.mnp button.mi{min-height:42px}.mnp .mau button{width:28px;height:28px}}
@media (prefers-reduced-motion:reduce){.mnp-bao{transition:none}}
"""

JS = r"""
(()=>{const G=window.BDMN,$=s=>document.querySelector(s),LWE=$('#lw'),ST=$('.stage');
if(!G||!LWE||!ST||document.documentElement.classList.contains('anh'))return;
const TEN=__TEN__,MAU=['','#e5532d','#17935b','#d99a00','#2f6fed','#6250d6','#e040fb','#00a3a3','#8d9286','#ffffff','#1b1f24'];
const IC={chep:'M6 6h8v9H6zM4 12V3h8',bao:'M9 2.5a4 4 0 0 0-4 4V10l-1.5 2.5h11L13 10V6.5a4 4 0 0 0-4-4zM7.5 14.5a1.6 1.6 0 0 0 3 0',ngang:'M2 9h14',
 tngang:'M6 9h10M6 9m-1.7 0a1.7 1.7 0 1 0 3.4 0a1.7 1.7 0 1 0-3.4 0',doc:'M9 2v14',cheo:'M9 2v14M2 9h14',nhan:'M3 15l3-4h9V5H6v6',vt:'M3 3h12v6H3zM3 9h12v6H3z',
 lot:'M3 15h12M5 15V9M9 15V5M13 15V7',kiem:'M3 9.5l3.5 3.5L15 4.5',cho:'M9 3v9M5 8l4 4 4-4M3 15h12',nay:'M4 9h9M10 5l4 4-4 4M15 3v12',
 mat:'M2 9s2.8-5 7-5 7 5 7 5-2.8 5-7 5-7-5-7-5zM9 9m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0',xoa:'M4 6h10M7 6V4h4v2M5.5 6l.7 9h5.6l.7-9',trong:'M3 3h12v12H3z',
 anh:'M2.5 5.5h3l1.5-2h4l1.5 2h3v9h-13zM9 10m-2.6 0a2.6 2.6 0 1 0 5.2 0a2.6 2.6 0 1 0-5.2 0',fs:'M3 7V3h4M11 3h4v4M15 11v4h-4M7 15H3v-4',nban:'M6 6h9v9H6zM3 12V3h9',
 khoa:'M5 8h8v7H5zM6.5 8V6a2.5 2.5 0 0 1 5 0v2',mo:'M5 8h8v7H5zM6.5 8V6a2.5 2.5 0 0 1 5 0',an:'M3 3l12 12M7.5 5.2A7 7 0 0 1 9 5c4.2 0 7 4 7 4a12 12 0 0 1-2.1 2.4M5 6.5C3.2 7.7 2 9 2 9s2.8 5 7 5a6.6 6.6 0 0 0 3-.7',
 len:'M9 15V4M5 8l4-4 4 4',xuong:'M9 3v11M5 10l4 4 4-4'};
const svg=k=>`<svg viewBox="0 0 18 18" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${IC[k]||''}"/></svg>`;
const mi=(k,ic,chu,o={})=>`<button type="button" class="mi${o.xau?' xau':''}" role="menuitem" data-k="${k}"${o.v!=null?` data-v="${o.v}"`:''}${o.tat?' disabled':''}>${svg(ic)}<span>${chu}</span>${o.phim?`<kbd>${o.phim}</kbd>`:''}</button>`;
const nhom=t=>`<div class="nhom" role="presentation">${t}</div>`,hr='<hr>';
let MN=null,chuot=null,lpLuc=0,ctxLuc=0,dRef=null,kRef='',PL=[],plNen=null,lp=null;
const giaNay=g=>{const D=g.D;if(!D)return null;if(D.bid!=null&&isFinite(D.bid))return +D.bid;const c=D.candles;return c&&c.length?c[c.length-1][4]:null};   // giá bid đang chạy
const atrNay=g=>{const a=g.D&&g.D.atr14;if(!a)return null;for(let i=a.length-1;i>=0;i--)if(a[i]!=null)return a[i];return null};
const so=(g,p)=>Number(p).toFixed(g.dg);                                  // số trơn để chép và gửi qua địa chỉ trang
const buoc=g=>{const c=g.D.candles,n=c.length;return n>1?c[n-1][0]-c[n-2][0]:900};
const caoKhung=g=>{try{return g.LW.chart.panes()[0].getHeight()}catch(e){return LWE.clientHeight}};
const toaGia=(g,m)=>m&&m.y>=0&&m.y<=caoKhung(g)?g.veToa(m.x,m.y):null;    // chỉ khung giá chính: khung MACD, RSI… không đổi ra giá được
const kyMa=g=>g.ma||'XAU';
// --- thông báo ngắn ở chân biểu đồ
function ping(t){let b=ST.querySelector('.mnp-bao');if(!b){b=document.createElement('div');b.className='mnp-bao';b.setAttribute('role','status');ST.appendChild(b)}
 b.textContent=t;b.classList.add('hien');clearTimeout(ping.h);ping.h=setTimeout(()=>b.classList.remove('hien'),1900)}
function chepCu(t,ok){const a=document.createElement('textarea');a.value=t;a.style.position='fixed';a.style.opacity='0';document.body.appendChild(a);a.select();
 try{document.execCommand('copy');ok()}catch(e){ping('Trình duyệt không cho chép')}a.remove()}
function chep(t){const ok=()=>ping('Đã chép: '+t);if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(t).then(ok,()=>chepCu(t,ok));else chepCu(t,ok)}
// --- khung menu: tự né mép màn hình, đi bằng phím mũi tên, Esc để đóng, bấm ra ngoài để đóng
function dong(){if(!MN)return;MN.remove();MN=null;removeEventListener('pointerdown',ngoai,true)}
function ngoai(e){if(MN&&!MN.contains(e.target))dong()}
function mo(x,y,html,lam){dong();MN=document.createElement('div');MN.className='mnp';MN.setAttribute('role','menu');MN.setAttribute('aria-label','Menu biểu đồ');MN.innerHTML=html;
 (document.fullscreenElement||document.body).appendChild(MN);
 const r=MN.getBoundingClientRect(),W=document.documentElement.clientWidth,H=innerHeight;
 MN.style.left=Math.max(8,Math.min(x,W-r.width-8))+'px';MN.style.top=Math.max(8,y+r.height>H-8?y-r.height:y)+'px';
 MN.addEventListener('click',e=>{const b=e.target.closest('button[data-k]');if(!b||b.disabled)return;e.stopPropagation();const k=b.dataset.k,v=b.dataset.v;dong();
  try{lam(k,v)}catch(er){console.warn('Menu biểu đồ:',er)}});
 MN.addEventListener('keydown',e=>{const ds=[...MN.querySelectorAll('button:not([disabled])')],i=ds.indexOf(document.activeElement);
  if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();const j=e.key==='ArrowDown'?(i+1)%ds.length:(i-1+ds.length)%ds.length;if(ds[j])ds[j].focus()}
  else if(e.key==='Escape'){e.preventDefault();dong()}else if(e.key==='Tab')e.preventDefault()});
 MN.addEventListener('contextmenu',e=>e.preventDefault());
 const f=MN.querySelector('button.mi:not([disabled])');if(f)f.focus({preventScroll:true});
 setTimeout(()=>addEventListener('pointerdown',ngoai,true),0)}
for(const ev of['resize','blur'])addEventListener(ev,dong);
addEventListener('scroll',e=>{if(MN&&!MN.contains(e.target))dong()},true);
addEventListener('wheel',e=>{if(MN&&!MN.contains(e.target))dong()},{capture:true,passive:true});
addEventListener('keydown',e=>{if(e.key==='Escape'&&MN)dong()});
// --- vẽ nhanh tại con trỏ, thử lệnh (chỉ tính, không đặt lệnh)
function veMoi(k,q){const g=G(),id=g.moiId();g.VE.ds.push({id,k,a:{t:q.t,p:q.p}});g.xong(id)}
function veVt(p){const g=G(),cur=giaNay(g),cs=g.D.candles;if(cur==null||p===cur)return;const t=cs[cs.length-1][0],id=g.moiId();
 g.VE.ds.push({id,k:'vt',a:{t,p:cur},b:{t:t+buoc(g)*24,p:cur},sl:p,tp:cur+(cur-p)*2});g.xong(id)}
function tinhLot(p){const g=G(),cur=giaNay(g);if(cur==null)return;const sl=Math.round(Math.abs(cur-p)*100)/100;g.rk.sl=sl;const el=$('#rk-sl');if(el)el.value=sl;
 g.rkLuu();g.rkDraw();g.ctabDat('rk');const o=$('#rko')||$('#rk');if(o)o.scrollIntoView({block:'nearest',behavior:'smooth'});ping('Đã đặt khoảng dừng lỗ '+g.fp(sl)+' vào ô Tính lot')}
function kiemLenh(p,cho){const g=G(),cur=giaNay(g);if(cur==null)return;const q=new URLSearchParams({ma:g.tkMa(),chieu:p<cur?'MUA':'BAN'});
 if(cho)q.set('vao',so(g,p));else{q.set('vao',so(g,cur));q.set('sl',so(g,p))}window.open('/kiem-lenh?'+q,'_blank','noopener')}
// --- cảnh báo giá: lưu trong trình duyệt theo mã, đường nét đứt màu cam trên biểu đồ, báo bằng khung nổi, tiếng và thông báo hệ thống
const BK=g=>'so-bao:'+kyMa(g);
const baoDoc=g=>{try{return JSON.parse(localStorage.getItem(BK(g))||'[]')}catch(e){return[]}};
const baoGhi=(g,ds)=>{try{localStorage.setItem(BK(g),JSON.stringify(ds))}catch(e){}baoVe()};
// có hệ thống cảnh báo của máy chủ (canh_bao_ve.py, window.CBV: kiểm mỗi 5 giây kể cả khi đóng trang, gửi được Telegram riêng) thì dùng nó;
// cảnh báo cũ còn trong trình duyệt được chuyển sang máy chủ một lần rồi xóa
const CBV=()=>window.CBV&&typeof window.CBV.themGia==='function'?window.CBV:null;
const baoDs=g=>{const c=CBV();return c?c.ds().filter(a=>a.loai==='ngang').map(a=>({id:a.id,p:a.diem[0][1],len:a.dk!=='cat_xuong',may:1})):baoDoc(g)};
const daChuyen=new Set();
function chuyenBao(g){const c=CBV(),k=BK(g);if(!c||daChuyen.has(k))return;daChuyen.add(k);const cu=baoDoc(g);if(!cu.length)return;
 Promise.all(cu.map(a=>c.themGia(a.p,'Chuyển từ trình duyệt').catch(()=>({ok:false})))).then(kq=>{if(kq.every(x=>x.ok))try{localStorage.removeItem(k)}catch(e){}setTimeout(baoVe,800)})}
function baoThem(p){const g=G(),cur=giaNay(g);if(cur==null||!isFinite(p))return;const c=CBV();
 if(c){c.themGia(+so(g,p)).then(kq=>{ping(kq.ok?kq.ly_do||('Đã đặt cảnh báo khi giá chạm '+g.fp(p)):kq.ly_do||'Chưa đặt được cảnh báo');setTimeout(baoVe,800)},()=>ping('Chưa đặt được cảnh báo'));return}
 const ds=baoDoc(g),v=+so(g,p);
 if(ds.some(a=>a.p===v)){ping('Đã có cảnh báo ở mức này');return}
 ds.push({id:g.moiId(),p:v,len:v>=cur,luc:Date.now()});baoGhi(g,ds);ping('Đã đặt cảnh báo khi giá chạm '+g.fp(v));
 if(window.Notification&&Notification.permission==='default')try{Notification.requestPermission()}catch(e){}}
function baoVe(){const g=G();if(!g.LW||!g.LW.nen)return;const nen=g.LW.nen;if(plNen!==nen){PL=[];plNen=nen}for(const l of PL)try{nen.removePriceLine(l)}catch(e){}
 PL=baoDs(g).map(a=>nen.createPriceLine({price:a.p,color:'#f5a623',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'🔔'}))}
setInterval(()=>{const g=G();if(CBV()||window.PHAT_LAI||!g.D||g.D!==dRef||kyMa(g)!==kRef)return;   // có cảnh báo máy chủ thì máy chủ kiểm   // đang phát lại nến cũ (bieu_do_phat_lai.py): không so giá cũ với cảnh báoconst ds=baoDoc(g);if(!ds.length)return;const cur=giaNay(g);if(cur==null)return;   // chỉ so với giá của đúng mã đang hiện
 const no=ds.filter(a=>a.len?cur>=a.p:cur<=a.p);if(!no.length)return;baoGhi(g,ds.filter(a=>!no.includes(a)));
 for(const a of no){const tieu='Giá chạm '+g.fp(a.p),nd=g.tkMa()+' · '+g.fp(cur);g.toast({tieu_de:tieu,noi_dung:nd});g.beep();
  if(window.Notification&&Notification.permission==='granted')try{new Notification(tieu,{body:nd,tag:'so-bao-'+a.id})}catch(e){}}},1000);
function menuBao(){const g=G(),c=CBV(),ds=baoDs(g),r=LWE.getBoundingClientRect();if(!ds.length)return;
 let s=`<div class="dau"><b>Cảnh báo giá</b><small>${g.esc(g.tkMa())}</small><small>${c?'Máy chủ kiểm mỗi 5 giây, kể cả khi bạn đóng trang':'Chỉ báo khi trang Biểu đồ của mã này đang mở'}</small></div>`;
 s+=ds.map(a=>mi('xbao','xoa','Xóa cảnh báo '+g.fp(a.p)+(a.len?' ↑':' ↓'),{v:a.id})).join('')+hr+mi('xbaohet','xoa','Xóa tất cả cảnh báo',{xau:1});
 mo(r.left+r.width/2-140,r.top+40,s,k=>{if(k==='xbaohet'){if(c)Promise.all(ds.map(a=>c.xoa(a.id))).then(()=>setTimeout(baoVe,500));else baoGhi(g,[])}});
 if(MN)MN.addEventListener('click',e=>{const b=e.target.closest('button[data-k=xbao]');if(!b)return;if(c)c.xoa(b.dataset.v).then(()=>setTimeout(baoVe,500));else baoGhi(g,baoDoc(g).filter(a=>a.id!==b.dataset.v))},true)}
// --- ảnh biểu đồ: nến, chỉ báo, hình vẽ, kèm dòng mã · khung · giờ và tên thương hiệu
function veAnh(){const g=G();if(!g.LW)return null;let c;try{c=g.LW.chart.takeScreenshot()}catch(e){return null}if(!c||!c.width)return null;
 const o=$('#lwo'),d=c.width/(LWE.clientWidth||c.width),dau=Math.round(26*d),k=document.createElement('canvas');k.width=c.width;k.height=c.height+dau;
 const x=k.getContext('2d'),P=g.P;x.fillStyle=P.bg;x.fillRect(0,0,k.width,k.height);x.drawImage(c,0,dau);
 if(o&&o.width&&o.height)x.drawImage(o,0,0,o.width,o.height,0,dau,c.width,c.width*o.height/o.width);
 x.fillStyle=P.fg;x.font=Math.round(12*d)+'px Tahoma,"Segoe UI",Arial,sans-serif';x.textBaseline='middle';x.textAlign='left';
 x.fillText(g.tkMa()+' · '+g.tf+' · '+g.vnN(Date.now()/1000),10*d,dau/2);x.textAlign='right';x.fillText(TEN,k.width-10*d,dau/2);return k}
function taiAnh(){const k=veAnh(),g=G();if(!k){ping('Chưa chụp được biểu đồ');return}const n=new Date(),p=v=>String(v).padStart(2,'0');
 k.toBlob(b=>{if(!b)return;const a=document.createElement('a');a.href=URL.createObjectURL(b);
  a.download=g.tkMa()+'-'+g.tf+'-'+n.getFullYear()+p(n.getMonth()+1)+p(n.getDate())+'-'+p(n.getHours())+p(n.getMinutes())+'.png';
  document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),5000);ping('Đã tải ảnh biểu đồ')},'image/png')}
function chepAnh(){const k=veAnh();if(!k){ping('Chưa chụp được biểu đồ');return}
 try{navigator.clipboard.write([new ClipboardItem({'image/png':new Promise(r=>k.toBlob(r,'image/png'))})]).then(()=>ping('Đã chép ảnh biểu đồ'),()=>ping('Trình duyệt không cho chép ảnh'))}
 catch(e){ping('Trình duyệt không cho chép ảnh')}}
// --- menu khi bấm vào chỗ trống của biểu đồ
function menuBieuDo(cx,cy,m){const g=G(),D=g.D;if(!D||!D.candles||!D.candles.length)return;
 const q=toaGia(g,m),cur=giaNay(g),atr=atrNay(g),vang=!D.khac_vang,cs=D.candles,n=cs.length;
 let li=null;try{li=g.LW.chart.timeScale().coordinateToLogical(m.x)}catch(e){}const i=li==null?-1:Math.round(li),c=i>=0&&i<n?cs[i]:null;
 let h='';
 if(q){const p=q.p,d=cur==null?null:p-cur,dau=v=>v>=0?'+':'−';
  h+=`<div class="dau"><b>${g.fp(p)}</b><small>${g.vnN(q.t)}</small>`+(d==null||!cur?'':`<small>Cách giá hiện tại ${dau(d)}${g.fp(Math.abs(d))} (${dau(d)}${g.f2(Math.abs(d/cur*100))}%)${atr?' · '+g.f2(Math.abs(d)/atr)+' ATR':''}${vang?' · '+g.f2(.01)+' lot ≈ '+g.f2(Math.abs(d))+' USD':''}</small>`)+'</div>';
  h+=mi('chep','chep','Sao chép giá',{phim:'Alt+C',v:so(g,p)})+mi('bao','bao','Đặt cảnh báo khi giá chạm mức này',{phim:'Alt+A',v:so(g,p)});
  h+=hr+nhom('Vẽ tại mức này')+mi('ve','ngang','Đường ngang',{phim:'Alt+H',v:'ngang'})+mi('ve','tngang','Tia ngang',{phim:'Alt+J',v:'tngang'})
   +mi('ve','doc','Đường dọc',{phim:'Alt+V',v:'doc'})+mi('ve','cheo','Đường chữ thập',{v:'cheo'})+mi('ve','nhan','Nhãn giá',{v:'nhan'});
  if(cur!=null&&p!==cur){const mua=p<cur;
   h+=hr+nhom('Thử lệnh: chỉ tính, không đặt lệnh')+mi('vt','vt',mua?'Vẽ vị thế MUA, dừng lỗ tại mức này':'Vẽ vị thế BÁN, dừng lỗ tại mức này')
    +(vang?mi('lot','lot','Tính lot với dừng lỗ tại mức này'):'')
    +mi('kiem','kiem',mua?'Kiểm tra lệnh MUA, dừng lỗ tại mức này':'Kiểm tra lệnh BÁN, dừng lỗ tại mức này')
    +mi('cho','cho',mua?'Kiểm tra lệnh chờ MUA tại mức này':'Kiểm tra lệnh chờ BÁN tại mức này')}}
 if(c){const[t,o,hi,lo,cl]=c,bd=hi-lo,than=bd?Math.abs(cl-o)/bd*100:0;
  h+=(h?hr:'')+nhom('Nến lúc '+g.vnN(t))+`<div class="nen"><span>Mở</span><b>${g.fp(o)}</b><span>Cao</span><b>${g.fp(hi)}</b><span>Thấp</span><b>${g.fp(lo)}</b><span>Đóng</span><b>${g.fp(cl)}</b>`
   +`<span>Biên độ</span><b>${g.fp(bd)}${atr?' · '+g.f2(bd/atr)+' ATR':''}</b><span>Thân nến</span><b>${g.f2(than)}%</b></div>`+mi('chepnen','chep','Sao chép giá mở, cao, thấp, đóng')}
 const VE=g.VE,soAn=VE.ds.filter(x=>x.an).length,soBao=baoDs(g).length,coAnh=!!(window.ClipboardItem&&navigator.clipboard&&navigator.clipboard.write);
 h+=(h?hr:'')+mi('nay','nay','Về nến mới nhất',{phim:'Alt+R'})
  +mi('an','mat',VE.an?'Hiện các hình đã vẽ':'Ẩn các hình đã vẽ',{tat:!VE.ds.length})
  +(soAn?mi('hienan','mat','Hiện lại hình đã ẩn riêng'+' · '+soAn):'')
  +mi('trong','trong',g.TRONG?'Tắt biểu đồ trống':'Biểu đồ trống: ẩn lớp của hệ thống')
  +(soBao?mi('dsbao','bao','Cảnh báo giá đang đặt'+' · '+soBao):'')
  +mi('anh','anh','Tải ảnh biểu đồ (PNG)',{phim:'Alt+S'})+(coAnh?mi('chepanh','chep','Sao chép ảnh biểu đồ'):'')
  +mi('fs','fs','Toàn màn hình',{phim:'F'})
  +hr+mi('xoahet','xoa','Xóa tất cả hình vẽ của mã này',{xau:1,tat:!VE.ds.length});
 mo(cx,cy,h,(k,v)=>lamBieuDo(k,v,q,c))}
function lamBieuDo(k,v,q,c){const g=G(),VE=g.VE;
 if(k==='chep')chep(v);else if(k==='bao')baoThem(+v);else if(k==='ve'&&q)veMoi(v,q);
 else if(k==='vt'&&q)veVt(q.p);else if(k==='lot'&&q)tinhLot(q.p);else if(k==='kiem'&&q)kiemLenh(q.p,false);else if(k==='cho'&&q)kiemLenh(q.p,true);
 else if(k==='chepnen'&&c)chep(c.slice(1,5).map(x=>so(g,x)).join('\t'));
 else if(k==='nay')g.lwNay();else if(k==='an'){VE.an=!VE.an;g.veTb();g.lwPhu()}
 else if(k==='hienan'){for(const x of VE.ds)delete x.an;g.veLuu();g.veTb();g.lwPhu()}
 else if(k==='trong')g.datTrong(!g.TRONG);else if(k==='dsbao')menuBao();else if(k==='anh')taiAnh();else if(k==='chepanh')chepAnh();
 else if(k==='fs'){const b=$('#fs-btn');if(b)b.click()}
 else if(k==='xoahet'&&VE.ds.length&&confirm('Xóa tất cả '+VE.ds.length+' hình đã vẽ trên '+g.tkMa()+'? Bấm Hoàn tác nếu đổi ý.')){window.HVD_DA_HOI=true;VE.ds=[];VE.chon=null;g.veLuu();g.veTb();g.lwPhu()}}   // đã hỏi: lớp đồng bộ hình (hinh_ve.py) không hỏi lần hai
// --- menu khi bấm vào một hình đã vẽ
function menuHinh(cx,cy,id){const g=G(),h=g.VE.ds.find(x=>x.id===id);if(!h)return;const ten=(g.VEC[h.k]||[h.k])[0],coGia=/^(ngang|tngang|nhan|cheo)$/.test(h.k),w=h.w||1.5,net=h.net||'';
 let s=`<div class="dau"><b>${ten}</b>`+(coGia?`<small>${g.fp(h.a.p)}</small>`:'')+(h.khoa?'<small>Đã khóa vị trí</small>':'')+'</div>';
 const coCbv=CBV()&&/^(ngang|tngang|xu|tia|mt|kenh|hop)$/.test(h.k);                    // hình có điều kiện cắt, vào, ra: hộp chọn của máy chủ
 if(coGia)s+=mi('chep','chep','Sao chép giá',{v:so(g,h.a.p)})+(coCbv?'':mi('bao','bao','Đặt cảnh báo tại đường này',{v:so(g,h.a.p)}));
 if(coCbv)s+=mi('cbv','bao','Cảnh báo khi giá cắt hình này…');
 if(coGia||coCbv)s+=hr;
 if(h.k==='chu')s+=mi('suachu','nhan','Sửa chữ');
 s+=mi('nban','nban','Nhân bản')+mi('khoa',h.khoa?'mo':'khoa',h.khoa?'Mở khóa vị trí':'Khóa vị trí')+mi('an1','an','Ẩn hình này')
  +mi('tren','len','Đưa lên trên cùng')+mi('duoi','xuong','Đưa xuống dưới cùng');
 s+=hr+nhom('Màu')+'<div class="mau">'+MAU.map(c=>`<button type="button" data-k="mau" data-v="${c}" title="${c||'Màu mặc định'}" aria-label="${c||'Màu mặc định'}" aria-pressed="${(h.mau||'')===c}" style="background:${c||'var(--series)'}"></button>`).join('')+'</div>';
 s+=nhom('Nét')+'<div class="hang">'+[[1,'Mảnh'],[1.5,'Vừa'],[2.5,'Đậm'],[3.5,'Rất đậm']].map(([v,t])=>`<button type="button" data-k="w" data-v="${v}" aria-pressed="${w===v}">${t}</button>`).join('')+'</div>'
  +'<div class="hang">'+[['','Liền'],['gach','Gạch'],['cham','Chấm']].map(([v,t])=>`<button type="button" data-k="net" data-v="${v}" aria-pressed="${net===v}">${t}</button>`).join('')+'</div>';
 s+=hr+mi('xoa','xoa','Xóa',{xau:1,phim:'Del'});
 mo(cx,cy,s,(k,v)=>lamHinh(k,v,id))}
function lamHinh(k,v,id){const g=G(),VE=g.VE,i=VE.ds.findIndex(x=>x.id===id),h=VE.ds[i];if(!h)return;
 if(k==='chep'){chep(v);return}if(k==='bao'){baoThem(+v);return}if(k==='xoa'){VE.chon=id;g.veXoa();return}if(k==='suachu'){suaChu(id);return}if(k==='cbv'){const c=CBV();if(c)c.mo(id);return}
 if(k==='nban'){const n=JSON.parse(JSON.stringify(h)),d=buoc(g)*5,dc=pt=>pt&&{...pt,t:pt.t+d};n.id=g.moiId();delete n.khoa;n.a=dc(n.a);if(n.b)n.b=dc(n.b);if(n.c)n.c=dc(n.c);if(n.pts)n.pts=n.pts.map(dc);
  VE.ds.push(n);VE.chon=n.id}
 else if(k==='khoa'){if(h.khoa)delete h.khoa;else h.khoa=1}
 else if(k==='an1'){h.an=1;VE.chon=null;ping('Đã ẩn hình. Bấm chuột phải vào biểu đồ để hiện lại')}
 else if(k==='tren'){VE.ds.splice(i,1);VE.ds.push(h)}else if(k==='duoi'){VE.ds.splice(i,1);VE.ds.unshift(h)}
 else if(k==='mau'){if(v)h.mau=v;else delete h.mau}else if(k==='w')h.w=+v;else if(k==='net'){if(v)h.net=v;else delete h.net}
 g.veLuu();g.veTb();g.lwPhu()}
// --- sửa chữ của ghi chú ngay trên biểu đồ (bấm đúp vào ghi chú, hoặc menu → Sửa chữ)
function suaChu(id){const g=G(),h=g.VE.ds.find(x=>x.id===id);if(!h||h.k!=='chu')return;let x=null,y=null;try{x=g.LW.chart.timeScale().timeToCoordinate(h.a.t);y=g.LW.nen.priceToCoordinate(h.a.p)}catch(e){}
 const o=document.createElement('input');o.className='venhap';o.maxLength=80;o.value=h.chu||'';o.style.left=Math.max(4,Math.min(x==null?LWE.clientWidth/2:x,LWE.clientWidth-230))+'px';
 o.style.top=Math.max(4,(y==null?60:y)-14)+'px';ST.appendChild(o);setTimeout(()=>{o.focus();o.select()},0);
 let da=0;const xong=luu=>{if(da)return;da=1;const v=o.value.trim();o.remove();if(luu&&v&&v!==h.chu){h.chu=v;g.veLuu();g.lwPhu()}};
 o.addEventListener('keydown',e=>{e.stopPropagation();if(e.key==='Enter')xong(1);else if(e.key==='Escape')xong(0)});o.addEventListener('blur',()=>xong(1))}
// bấm đúp trúng hình: ghi chú thì sửa chữ, hình khác thì mở menu của hình (bieu_do.py gọi trước khi nhảy về nến mới nhất)
function dbl(e){const g=G();if(!g.LW||!g.D||g.VE.an||g.VE.cong!=='tro')return false;const r=LWE.getBoundingClientRect(),h=g.veTrung(e.clientX-r.left,e.clientY-r.top);if(!h)return false;
 const s=g.VE.ds.find(x=>x.id===h.id);if(s&&s.k==='chu')suaChu(h.id);else menuHinh(e.clientX,e.clientY,h.id);return true}
// --- mở menu: chuột phải trên máy tính, giữ ngón tay trên điện thoại; đang cầm công cụ vẽ thì chuột phải là thôi công cụ (như TradingView)
function moMenu(cx,cy){const g=G();if(!g.LW||!g.D)return;if(g.VE.cong!=='tro'){g.veCong('tro');return}
 const r=LWE.getBoundingClientRect(),m={x:cx-r.left,y:cy-r.top};if(m.x<0||m.y<0||m.x>r.width||m.y>r.height)return;
 const h=!g.VE.an&&g.veTrung(m.x,m.y);if(h){g.VE.chon=h.id;g.veTb();g.lwPhu();menuHinh(cx,cy,h.id)}else menuBieuDo(cx,cy,m)}
ST.addEventListener('contextmenu',e=>{const g=G();if(!g.LW||!g.D||e.target.closest('.vetb,.venhap,input,textarea,a,button'))return;const r=LWE.getBoundingClientRect();
 if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)return;e.preventDefault();e.stopPropagation();
 if(Date.now()-lpLuc<900)return;ctxLuc=Date.now();moMenu(e.clientX,e.clientY)},true);       // Android giữ ngón tay cũng phát contextmenu: chỉ mở một menu
LWE.addEventListener('pointerdown',e=>{if(e.pointerType!=='touch')return;const x=e.clientX,y=e.clientY;if(lp)clearTimeout(lp.t);
 lp={x,y,t:setTimeout(()=>{lp=null;if(Date.now()-ctxLuc<900)return;lpLuc=Date.now();moMenu(x,y)},600)}},true);
addEventListener('pointermove',e=>{if(lp&&Math.hypot(e.clientX-lp.x,e.clientY-lp.y)>10){clearTimeout(lp.t);lp=null}},true);
for(const ev of['pointerup','pointercancel'])addEventListener(ev,()=>{if(lp){clearTimeout(lp.t);lp=null}},true);
LWE.addEventListener('pointermove',e=>{const r=LWE.getBoundingClientRect();chuot={x:e.clientX-r.left,y:e.clientY-r.top}});LWE.addEventListener('pointerleave',()=>{chuot=null});
addEventListener('keydown',e=>{if(!e.altKey||e.ctrlKey||e.metaKey||e.shiftKey||/^(INPUT|TEXTAREA|SELECT)$/.test((e.target&&e.target.tagName)||''))return;const g=G();if(!g.LW||!g.D)return;
 const q=toaGia(g,chuot),c=e.code;let ok=1;
 if(c==='KeyH'&&q)veMoi('ngang',q);else if(c==='KeyJ'&&q)veMoi('tngang',q);else if(c==='KeyV'&&q)veMoi('doc',q);
 else if(c==='KeyA'){const p=q?q.p:giaNay(g);if(p!=null)baoThem(p)}else if(c==='KeyC'&&q)chep(so(g,q.p));else if(c==='KeyR')g.lwNay();else if(c==='KeyS')taiAnh();else ok=0;
 if(ok){e.preventDefault();e.stopPropagation()}});
window.MNP={ve(){if(window.PHAT_LAI)return;const g=G();dRef=g.D;kRef=kyMa(g);chuyenBao(g);baoVe()},dbl};
if(G().D)window.MNP.ve()})();
""".replace('__TEN__', json.dumps(TEN, ensure_ascii=False))
