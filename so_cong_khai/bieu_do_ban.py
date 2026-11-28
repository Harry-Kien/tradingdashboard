"""Bố cục "bàn giao dịch" cho trang Biểu đồ (/bieu-do, 27/11/2026): trên máy tính trang kín cả chiều ngang lẫn chiều cao và không cuộn.

Chỉ có hiệu lực khi cửa sổ rộng từ 981px và cao từ 600px (MOC). Ngoài mốc đó trang giữ nguyên bố cục cũ (điện thoại, máy tính bảng).
- Vùng trái: khung biểu đồ lấp hết chỗ; vùng nến co giãn theo cửa sổ (thấp nhất 320px, 200px khi cửa sổ thấp hơn 760px).
- Dòng "mã · nguồn giá" (.stamp) được dời xuống hàng nhỏ dưới nến (.ban-chan), cạnh dòng ghi công thư viện; thẻ điểm vào (#dv) cao tối đa 200px.
- Bảng phải (.col, 350px): cuộn riêng, gập/mở bằng nút #phai-btn; ghi chú "Đọc trước" và chân trang được dời xuống cuối bảng.
- Thẻ điểm vào có mũi tên thu gọn và cửa sổ đọc lớn trên mọi cỡ màn hình; giữ nguyên DOM, bộ lọc và cập nhật giá khi mở rộng.
- Ngăn dưới (.duoi): mọi ô dưới biểu đồ (AI, COT, Làm tiếp, và các ô mô-đun khác chèn lúc chạy như #cbv, #dsau) thành một dải thẻ, mặc định gập.
- Nút Toàn màn hình (lớp .max của #cp) không đổi: mọi luật ở đây đều viết cho .chartp:not(.max).

Khung HTML của trang và JS chính không bị sửa: mô-đun này chỉ thêm CSS đứng cuối <style> và một đoạn JS đứng cuối trang, đoạn JS chỉ quan sát DOM
(matchMedia, MutationObserver) chứ không gọi hàm nào của JS chính. Nhờ vậy phiên khác sửa bieu_do.JS không làm hỏng bố cục, và gỡ bố cục này chỉ cần
bỏ hai chỗ nạp trong bieu_do.trang_bieu_do.
Cách bố trí là kiểu chung của các bàn giao dịch; không dùng mã, hình hay biểu tượng của sản phẩm nào khác."""
from __future__ import annotations

MOC = '@media(min-width:981px) and (min-height:600px)'

CSS = r"""
#phai-btn,#dv-btn,.ngan-tab{display:none}
#dv-head{display:flex;align-items:center;gap:8px;padding:8px 0 2px;min-width:0}
#dv-head[hidden]{display:none}#dv-head strong{font-size:14px}#dv-head small{font-size:12px;color:var(--mute)}
#dv-head .dv-actions{margin-left:auto;display:flex;gap:6px;flex:none}
:root #dv-head button{display:inline-flex;align-items:center;justify-content:center;gap:6px;min-height:36px;padding:5px 10px;font-size:13px}
#dv-head svg,#dv-reader svg{flex:none}#dv-head button:focus-visible,#dv-reader button:focus-visible{outline:2px solid var(--series);outline-offset:2px}
:root .chartp.dv-an>#dv{display:none}:root .chartp.max.gon #dv-head{display:none}
:root.dv-reading{overflow:hidden}
#dv-reader{inset:0;margin:auto;padding:0;width:min(1180px,calc(100vw - 40px));height:min(730px,calc(100dvh - 48px));max-width:none;max-height:none;box-sizing:border-box;
 color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:0 24px 90px #0008}
#dv-reader[open]{display:flex;flex-direction:column}#dv-reader::backdrop{background:#000b;backdrop-filter:blur(3px)}
.dv-reader-head{display:flex;align-items:center;gap:12px;flex:none;padding:16px 20px;border-bottom:1px solid var(--line)}
.dv-reader-head h2{margin:0;font-size:21px;letter-spacing:-.025em}.dv-reader-head p{margin:4px 0 0;color:var(--ink2);font-size:12px;font-variant-numeric:tabular-nums}
.dv-reader-head p[data-live=true]{color:var(--gain)}
.dv-reader-head button{margin-left:auto;flex:none;display:inline-flex;align-items:center;gap:7px;min-height:40px}
.dv-reader-work{display:grid;grid-template-columns:315px minmax(0,1fr);flex:1;min-height:0}
.dv-reader-menu{display:flex;flex-direction:column;min-height:0;min-width:0;border-right:1px solid var(--line);background:var(--card2,var(--bg))}
.dv-reader-tools{display:grid;grid-template-columns:minmax(0,1fr) 108px;padding:12px;gap:8px;border-bottom:1px solid var(--line)}
.dv-reader-tools input,.dv-reader-tools select{font:inherit;font-size:13px;min-width:0;min-height:38px;padding:6px 9px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink)}
.dv-reader-tools input:focus-visible,.dv-reader-tools select:focus-visible{outline:2px solid var(--series);outline-offset:1px}
.dv-reader-count{grid-column:1/-1;color:var(--ink2);font-size:11.5px;line-height:1.4;margin:0}
.dv-reader-list{overflow:auto;min-height:0;padding:8px;overscroll-behavior:contain;scrollbar-gutter:stable}
.dv-reader-list h3{margin:12px 8px 4px;color:var(--mute);font-size:11px;font-weight:600}
.dv-reader-list .dv-row{width:100%;display:grid;grid-template-columns:8px minmax(0,1fr) auto;grid-template-rows:auto auto;gap:4px 8px;padding:8px 9px;margin:2px 0;text-align:left;color:var(--ink);background:none;border:1px solid transparent;border-radius:8px;font:inherit;cursor:pointer;min-height:42px}
.dv-row strong{font-size:12px;line-height:1.35;font-weight:600}.dv-row small{grid-column:2/-1;font-size:11px;color:var(--muted,var(--mute));line-height:1.3}
.dv-row i{width:7px;height:7px;margin-top:5px;border-radius:100%;background:var(--mute)}.dv-row[data-state=ready] i{background:var(--gain)}.dv-row[data-state=review] i{background:var(--warn)}.dv-row[data-state=data] i{background:none;border:1px solid var(--mute)}
.dv-reader-list .dv-row:hover{background:var(--bg)}.dv-reader-list .dv-row[aria-current=true]{background:color-mix(in srgb,var(--series) 10%,var(--card));border-color:color-mix(in srgb,var(--series) 34%,var(--line))}
.dv-tf{font-size:10px;font-weight:650;line-height:1.4;align-self:start;color:var(--ink2);background:var(--line);border:1px solid var(--line);border-radius:5px;padding:1px 5px;white-space:nowrap}
.dv-reader-list .dv-empty{font-size:13px;color:var(--muted,var(--mute));margin:10px}
.dv-reader-body{min-width:0;min-height:0;overflow:auto;overscroll-behavior:contain;padding:16px 20px;scrollbar-gutter:stable;background:var(--bg)}
:root #dv-reader #dv{display:block;max-height:none;overflow:visible;margin:0}
:root #dv-reader .ppt{gap:6px;margin-bottom:12px;justify-content:flex-end}:root #dv-reader .ppx{display:none}
:root #dv-reader .pl{gap:14px;padding-top:14px}:root #dv-reader .plh{gap:8px 12px}:root #dv-reader .plh b{font-size:17px}
:root #dv-reader .pl-wait .plh{padding-bottom:8px;border-bottom:1px solid var(--line)}
:root #dv-reader .plh small{flex-basis:100%;font-size:14px;line-height:1.5}
:root #dv-reader .plg{grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}
:root #dv-reader .plg div{padding:12px;gap:5px;border-radius:10px}:root #dv-reader .plg b{font-size:23px}
:root #dv-reader .plg small,:root #dv-reader .plg i{font-size:14px;white-space:normal;line-height:1.5;overflow-wrap:anywhere}
:root #dv-reader .plg i,:root #dv-reader .plh small{display:block}
:root #dv-reader .pl>.why{display:block}:root #dv-reader .why,:root #dv-reader .plct{font-size:16px;line-height:1.7;max-width:90ch}
:root #dv-reader .plct>summary{font-size:14px;min-height:36px}:root #dv-reader .pln button{min-height:40px;font-size:14px}
@media(max-width:720px){.dv-reader-work{grid-template-columns:minmax(0,1fr);grid-template-rows:minmax(136px,39%) minmax(0,1fr)}
 .dv-reader-menu{border-right:0;border-bottom:1px solid var(--line)}.dv-reader-tools{padding:8px}.dv-reader-list .dv-row{min-height:43px}
 #dv-head small{display:none}:root #dv-head button{min-height:44px;padding:5px 9px}#dv-head strong{font-size:13px}
 #dv-reader{width:calc(100vw - 16px);height:calc(100dvh - 16px);border-radius:12px}.dv-reader-head{padding:12px;gap:8px}.dv-reader-head h2{font-size:17px}
 .dv-reader-head p{font-size:11px}.dv-reader-body{padding:10px}:root #dv-reader .plg{grid-template-columns:repeat(2,minmax(0,1fr))}
 :root #dv-reader .plg div{padding:10px}:root #dv-reader .plg b{font-size:21px}:root #dv-reader .ppt .kl{margin-left:0}}
@media(min-width:981px) and (min-height:600px){
:root body{height:100vh;height:100dvh;display:flex;flex-direction:column;overflow:hidden}
:root .nv{flex:none}:root .nv-in{max-width:none}
:root .gsr{flex:none;max-width:none;margin:6px 10px 0;padding:0}
:root main{flex:1 1 0;min-height:0;max-width:none;width:auto;margin:0;padding:8px 10px;display:flex;flex-direction:column;box-sizing:border-box}
:root main>.top{position:absolute;width:1px;height:1px;margin:-1px;padding:0;border:0;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
:root main>#doc-truoc,:root main>footer{display:none}
:root .desk{flex:1 1 0;min-height:0;margin:0;gap:10px;grid-template-columns:minmax(0,1fr) 350px;grid-template-rows:minmax(0,1fr);align-items:stretch}
:root .desk.an-phai{grid-template-columns:minmax(0,1fr)}:root .desk.an-phai>.col{display:none}
:root .trai{display:flex;flex-direction:column;gap:8px;min-height:0}
:root .chartp:not(.max){flex:1 1 0;min-height:0;display:flex;flex-direction:column;overflow:auto;padding:8px 10px}
:root .chartp:not(.max)>*{flex:none}
:root .chartp:not(.max)>.tools{margin-bottom:6px}
:root .chartp:not(.max)>.bott{margin-bottom:6px;padding:4px 10px}
:root .chartp:not(.max)>.stage{flex:1 1 0;min-height:320px;display:flex}
:root .chartp:not(.max) #lw,:root .chartp:not(.max) #cv{flex:1 1 0;min-width:0;width:0;height:auto}
:root .chartp:not(.max)>#dv{max-height:min(20vh,170px);overflow:auto;margin-top:6px}:root .chartp.dv-an:not(.max)>#dv{display:none}
:root #dv-btn{display:inline-flex;align-items:center;min-height:22px;padding:0 8px;font-size:11.5px}:root #dv-btn[hidden]{display:none}
:root #dv-btn[aria-pressed=true]{border-color:var(--series);color:var(--series);background:color-mix(in srgb,var(--series) 12%,transparent)}
:root .chartp:not(.max)>.ban-chan{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 14px;margin-top:6px}
:root .chartp.max>.ban-chan{display:none}:root .ban-chan>.hint{margin:0}:root .ban-chan>details[open]{flex-basis:100%}
:root .ban-chan>.stamp{flex:1 1 0;min-width:0;margin-left:auto;font-size:12px;line-height:1.5;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
:root .ban-chan>.stamp br{display:none}:root .ban-chan>.stamp #ma-nhan::after{content:" · "}
:root #phai-btn{display:inline-flex;align-items:center;justify-content:center;position:relative;width:36px;padding:0}
:root #phai-btn[aria-pressed=true]{border-color:var(--series);color:var(--series);background:color-mix(in srgb,var(--series) 12%,transparent)}
:root #phai-moi{position:absolute;top:-6px;right:-6px;min-width:17px;height:17px;padding:0 4px;border-radius:99px;background:var(--loss);color:#fff;font-size:10.5px;line-height:17px;text-align:center}
:root #phai-btn[aria-pressed=true] #phai-moi,:root #phai-moi[hidden]{display:none}:root .chartp.max #phai-btn{display:none}
:root .desk>.col{position:static;max-height:none;min-height:0;overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;gap:10px;padding-right:2px}
:root .col>#his{font-size:12px;line-height:1.4;color:var(--mute)}:root .col>#his:empty{display:none}:root .col>#doc-truoc{margin:0}:root .col>footer{margin:0;padding-top:10px;font-size:12px}
:root .duoi{display:block;flex:none;min-width:0}:root .duoi .cum{display:contents}
:root .duoi .panel{display:none;border-top:0;border-radius:0 0 12px 12px}
:root .duoi .panel.mo:not([hidden]){display:block;height:clamp(140px,38vh,360px);overflow:auto;overscroll-behavior:contain}
:root .ngan-tab{display:flex;gap:4px;padding:4px;border:1px solid var(--line);border-radius:10px;background:var(--card);overflow-x:auto;scrollbar-width:none}
:root .ngan-tab[hidden]{display:none}:root .duoi.dang-mo .ngan-tab{border-radius:10px 10px 0 0}
:root .ngan-tab button{flex:none;border:0;background:none;color:var(--ink2);font:inherit;font-size:12.5px;font-weight:600;padding:6px 12px;border-radius:7px;cursor:pointer;white-space:nowrap}
:root .ngan-tab button:hover{color:var(--ink)}
:root .ngan-tab button[aria-selected=true]{background:color-mix(in srgb,var(--series) 16%,transparent);color:var(--ink)}
:root .ngan-tab button:focus-visible{outline:2px solid var(--series);outline-offset:1px}
:root .ngan-tab .ngan-mui{margin-left:auto;color:var(--mute)}
:root .ngan-tab .ngan-mui{min-width:40px;min-height:32px;font-size:15px}
}
@media(min-width:981px) and (min-height:600px) and (max-height:759px){:root .chartp:not(.max)>.stage{min-height:200px}}
@media(min-width:981px) and (min-height:600px) and (max-width:1560px){:root .chartp:not(.max) #fs-btn{font-size:0;gap:0;width:40px;padding:0;justify-content:center}
:root .chartp:not(.max)>.tools{gap:6px 8px}:root .chartp:not(.max) .tools .sel select{max-width:136px}:root .ban-chan>.stamp #ma-nhan{display:none}}
"""

JS = r"""
(()=>{const $=s=>document.querySelector(s),mq=matchMedia('(min-width:981px) and (min-height:600px)');
const desk=$('.desk'),col=$('.desk>.col'),duoi=$('.duoi'),cp=$('#cp'),fs=$('#fs-btn');if(!desk||!col||!duoi||!cp||!fs)return;
const doc=k=>{try{return localStorage.getItem(k)}catch(e){return null}},ghi=(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}};
// hai dòng nhỏ dưới nến (cách dùng, ghi công thư viện) vào một hàng
const hs=[...cp.children].filter(e=>e.classList.contains('hint'));
if(hs.length){const c=document.createElement('div');c.className='ban-chan';hs[0].before(c);hs.forEach(h=>c.appendChild(h))}
// vào mốc: dời dòng nguồn giá xuống hàng nhỏ dưới nến, "Đọc trước" và chân trang xuống cuối bảng phải; ra khỏi mốc: trả về đúng chỗ cũ
// (dòng "nến có từ ngày…" #his cũng xuống cuối bảng phải, để hàng nhỏ dưới nến vừa một dòng trên màn laptop)
const DOI=[[$('.top .stamp'),()=>$('.ban-chan')||$('.tools.t2')],[$('#his'),()=>col],[$('#doc-truoc'),()=>col],[$('main>footer'),()=>col]].map(([el,dich])=>({el,dich,nha:null}));
const dat=on=>{for(const d of DOI){if(!d.el)continue;
 if(on&&!d.nha){const toi=d.dich();if(!toi)continue;d.nha={cha:d.el.parentNode,sau:d.el.nextSibling};toi.appendChild(d.el)}
 else if(!on&&d.nha){const{cha,sau}=d.nha;d.nha=null;if(cha)cha.insertBefore(d.el,sau&&sau.parentNode===cha?sau:null)}}};
dat(mq.matches);mq.addEventListener('change',e=>dat(e.matches));
// nút gập bảng phải
const pb=document.createElement('button'),pm=document.createElement('b');
pb.type='button';pb.className='ghost';pb.id='phai-btn';pb.title='Ẩn hoặc hiện bảng bên phải';pb.setAttribute('aria-label','Bảng phải');
pb.innerHTML='<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/></svg>';
pm.id='phai-moi';pm.hidden=true;pb.append(pm);fs.before(pb);
const phai=(mo,nho)=>{desk.classList.toggle('an-phai',!mo);pb.setAttribute('aria-pressed',String(mo));if(nho)ghi('so-ban-phai',mo?'1':'0');
 if(mo&&col.dataset.tab==='cb'&&!pm.hidden){const t=col.querySelector('.ctab button[data-t=cb]');if(t)t.click()}};   // mở bảng đúng thẻ Cảnh báo: coi như đã xem, xóa số đếm
phai(doc('so-ban-phai')!=='0',0);pb.addEventListener('click',()=>phai(desk.classList.contains('an-phai'),1));
// thao tác ghi kết quả vào bảng phải lúc bảng đang gập: tự mở (không ghi nhớ, lần sau mở trang vẫn theo lựa chọn của người dùng)
// sau khi mở, cuộn bảng tới chỗ vừa có kết quả (lệnh cuộn của JS chính chạy lúc bảng còn ẩn nên không có tác dụng)
const moPhai=toi=>{if(!(mq.matches&&!cp.classList.contains('max')&&desk.classList.contains('an-phai')))return;phai(true,0);
 requestAnimationFrame(()=>{const e=toi&&toi();if(e&&e.scrollIntoView)e.scrollIntoView({block:'nearest'})})};
const pt=$('#pt'),toiPt=()=>pt,toiThe=()=>col.querySelector('.tabp[data-t="'+col.dataset.tab+'"]');
if(pt)new MutationObserver(()=>{if(!pt.hidden)moPhai(toiPt)}).observe(pt,{attributes:true,attributeFilter:['hidden']});
new MutationObserver(()=>moPhai(toiThe)).observe(col,{attributes:true,attributeFilter:['data-tab']});   // kể cả ghi lại cùng thẻ (menu chuột phải → Tính lot đang chọn sẵn)
// thoát Toàn màn hình: JS chính trả #pt về bảng phải; bảng đang gập thì mở ra để phân tích vừa đọc không biến mất
let laMax=cp.classList.contains('max');new MutationObserver(()=>{const m=cp.classList.contains('max');if(laMax&&!m&&pt&&!pt.hidden)moPhai(toiPt);laMax=m}).observe(cp,{attributes:true,attributeFilter:['class']});
document.addEventListener('click',e=>{if(e.target&&e.target.closest&&e.target.closest('#pt-btn,.dvm'))moPhai(toiPt)});
// Dùng chính DOM của thẻ trong cửa sổ đọc lớn: bộ lọc, giá trực tiếp và mọi listener vẫn hoạt động, không sao chép số liệu.
const dv=$('#dv');if(dv){
 const icon=path=>'<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="'+path+'"/></svg>';
 const head=document.createElement('div');head.id='dv-head';head.setAttribute('role','group');head.setAttribute('aria-label','Thẻ điểm vào');
 const title=document.createElement('strong');title.textContent='Thẻ điểm vào';const hint=document.createElement('small');hint.textContent='Xem nhanh';
 const actions=document.createElement('div');actions.className='dv-actions';
 const expand=document.createElement('button');expand.type='button';expand.id='dv-expand';expand.className='ghost nho';
 expand.innerHTML=icon('M14 4h6v6M20 4l-7 7M10 20H4v-6M4 20l7-7');const label=document.createElement('span');label.textContent='Mở rộng';expand.append(label);
 expand.setAttribute('aria-haspopup','dialog');expand.setAttribute('aria-controls','dv-reader');expand.setAttribute('aria-expanded','false');expand.title='Mở rộng thẻ điểm vào';
 const db=document.createElement('button');db.type='button';db.id='dv-btn';db.className='ghost nho';db.title='Ẩn hoặc hiện thẻ điểm vào dưới biểu đồ';db.setAttribute('aria-controls','dv');
 actions.append(expand,db);head.append(title,hint,actions);dv.before(head);const anchor=document.createComment('entry-card-home');dv.after(anchor);
 const reader=document.createElement('dialog');reader.id='dv-reader';reader.setAttribute('aria-labelledby','dv-reader-title');
 const rh=document.createElement('header');rh.className='dv-reader-head';const rhText=document.createElement('div');
 const rt=document.createElement('h2');rt.id='dv-reader-title';rt.textContent='Thẻ điểm vào';const desc=document.createElement('p');rhText.append(rt,desc);
 const close=document.createElement('button');close.type='button';close.className='ghost';close.title='Thu nhỏ về biểu đồ';
 close.innerHTML=icon('M20 10h-6V4M14 10l7-7M4 14h6v6M10 14l-7 7');const cl=document.createElement('span');cl.textContent='Thu nhỏ';close.append(cl);
 const shell=document.createElement('div');shell.className='dv-reader-work';const menu=document.createElement('aside');menu.className='dv-reader-menu';menu.setAttribute('aria-label','Danh mục phương pháp');
 menu.innerHTML='<div class="dv-reader-tools"><input type="search" aria-label="Tìm phương pháp" placeholder="Tìm phương pháp"><select aria-label="Lọc theo khung"><option value="">Mọi khung</option><option>M5</option><option>M15</option><option>M30</option></select><p class="dv-reader-count" aria-live="polite"></p></div><div class="dv-reader-list"></div>';
 const search=menu.querySelector('input'),frames=menu.querySelector('select'),list=menu.querySelector('.dv-reader-list'),count=menu.querySelector('.dv-reader-count');
 const body=document.createElement('div');body.className='dv-reader-body';rh.append(rhText,close);shell.append(menu,body);reader.append(rh,shell);cp.append(reader);
 const labels={he_thong:'Hệ thống Harry',phuong_phap:'Phương pháp M15',da_khung:'Bộ quét đa khung',nghien_cuu:'Nghiên cứu Harry'};
 const state={ready:'Giá đạt điều kiện',review:'Quan sát',wait:'Chờ thiết lập',data:'Thiếu dữ liệu'};
 const bn=s=>String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d');
 let menuDau='';
 function drawMenu(){if(!reader.open)return;const payload=window.ENTRY_CHOOSER?.data();if(!payload)return;
  const {rows,all,ma,tf,source,live}=payload,meta=[ma,tf,live?'Giá MT5 mới':source==='mt5'?'Chờ tick MT5 mới':source==='kho'?'Kho nến':'Chưa có dữ liệu'].filter(Boolean).join(' · ');
  if(desc.textContent!==meta){desc.textContent=meta;desc.dataset.live=String(live)}
  const q=bn(search.value).trim(),frame=frames.value,found=rows.filter(x=>(!frame||x.tf?.split('/').includes(frame))&&(!q||bn([x.name,labels[x.group],x.tf].join(' ')).includes(q)));
  const signature=JSON.stringify([found,all,q,frame,rows.length]);if(signature===menuDau)return;menuDau=signature;
  const scroll=list.scrollTop,focus=list.contains(document.activeElement)?document.activeElement.dataset.pick:null;
  const btn=(id,title,khung,full,kind,selected)=>{const b=document.createElement('button');b.type='button';b.className='dv-row';b.dataset.pick=id;b.dataset.state=kind;b.setAttribute('aria-current',String(selected));b.setAttribute('aria-controls','dv');
   const dot=document.createElement('i');dot.setAttribute('aria-hidden','true');const name=document.createElement('strong');name.textContent=title;
   const tag=document.createElement('span');tag.className='dv-tf';tag.textContent=khung;const detail=document.createElement('small');detail.textContent=full;b.append(dot,name,tag,detail);if(!khung)tag.hidden=true;return b};
  const els=[btn('','Tất cả phương pháp','','','',all)];
  for(const [key,label] of Object.entries(labels)){const group=found.filter(x=>x.group===key);if(!group.length)continue;
   const heading=document.createElement('h3');heading.textContent=label;els.push(heading);
   for(const x of group)els.push(btn(x.id,x.name,x.tf||'',state[x.state]||state.wait,x.state,x.selected))}
  if(!found.length){const empty=document.createElement('p');empty.className='dv-empty';empty.textContent='Không tìm thấy phương pháp.';els.push(empty)}
  list.replaceChildren(...els);list.scrollTop=scroll;count.textContent=found.length===rows.length?`${rows.length} mục phân tích`:`${found.length}/${rows.length} mục phân tích`;
  if(focus!==null)els.find(x=>x.dataset.pick===focus)?.focus({preventScroll:true})
 }
 search.addEventListener('input',drawMenu);frames.addEventListener('change',drawMenu);
 list.addEventListener('click',e=>{const b=e.target.closest?.('.dv-row');if(b){window.ENTRY_CHOOSER?.choose(b.dataset.pick);body.scrollTop=0;drawMenu()}});
 setInterval(drawMenu,1000);
 const dvDat=(hien,nho)=>{cp.classList.toggle('dv-an',!hien);db.setAttribute('aria-pressed',String(hien));db.setAttribute('aria-expanded',String(hien));
  db.innerHTML=icon(hien?'M6 14l6-6 6 6':'M6 10l6 6 6-6');const text=document.createElement('span');text.textContent=hien?'Thu gọn':'Hiện thẻ';db.append(text);if(nho)ghi('so-ban-dv',hien?'1':'0')};
 dvDat(doc('so-ban-dv')!=='0',0);db.addEventListener('click',()=>dvDat(cp.classList.contains('dv-an'),1));
 const focusable=scope=>[...scope.querySelectorAll('button,a[href],input,select,textarea,summary,[tabindex]')].filter(e=>!e.disabled&&e.tabIndex>=0&&e.getClientRects().length);
 let returnFocus=null,inlineScroll=0,cardFocus=null;
 const restore=()=>{anchor.before(dv);dv.scrollTop=inlineScroll;document.documentElement.classList.remove('dv-reading');expand.setAttribute('aria-expanded','false');
  cardFocus=null;if(returnFocus?.isConnected&&!head.hidden)returnFocus.focus({preventScroll:true});returnFocus=null};
 const closeReader=()=>{if(reader.open)reader.close();restore()};
 const keepMethodVisible=()=>{if(!reader.open)return;const tabs=dv.querySelector('.ppt'),selected=tabs?.contains(document.activeElement)?document.activeElement:tabs?.querySelector('[aria-selected="true"]');
  if(tabs&&selected&&tabs.scrollWidth>tabs.clientWidth){const t=tabs.getBoundingClientRect(),s=selected.getBoundingClientRect();
   if(s.left<t.left||s.right>t.right)tabs.scrollLeft+=s.left-t.left-(tabs.clientWidth-s.width)/2}};
 reader.addEventListener('focusin',e=>{const el=e.target;if(!dv.contains(el)){cardFocus=null;return}
  cardFocus={node:el,tag:el.tagName,attrs:['id','data-k','data-ma','data-i'].filter(a=>el.hasAttribute(a)).map(a=>[a,el.getAttribute(a)]),classes:el.className,index:focusable(dv).indexOf(el)}});
 new MutationObserver(()=>{if(reader.open)requestAnimationFrame(()=>{if(!reader.open)return;
  if(cardFocus&&!cardFocus.node.isConnected&&(document.activeElement===document.body||document.activeElement===reader)){
   const all=focusable(dv),same=all.filter(el=>el.tagName===cardFocus.tag&&el.className===cardFocus.classes&&cardFocus.attrs.every(([a,v])=>el.getAttribute(a)===v));
   const next=same.length===1?same[0]:all[cardFocus.index]||same[0]||close;next.focus({preventScroll:true})}
  keepMethodVisible()})}).observe(dv,{childList:true});
 expand.addEventListener('click',()=>{if(reader.open||dv.hidden)return;returnFocus=document.activeElement;inlineScroll=dv.scrollTop;body.append(dv);
  try{reader.showModal()}catch(e){restore();return}document.documentElement.classList.add('dv-reading');expand.setAttribute('aria-expanded','true');
  drawMenu();keepMethodVisible();search.focus({preventScroll:true})});
 close.addEventListener('click',closeReader);reader.addEventListener('close',()=>{if(!reader.open)restore()});
 reader.addEventListener('cancel',e=>{e.preventDefault();closeReader()});
 reader.addEventListener('keydown',e=>{e.stopPropagation();if(e.key!=='Tab')return;
  const all=focusable(reader),first=all[0]||close,last=all.at(-1)||close;
  if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}
  else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}});
 reader.addEventListener('click',e=>{if(e.target.closest?.('.dvm,.dvv'))closeReader()});
 const dvSoi=()=>{head.hidden=dv.hidden;if(dv.hidden&&reader.open)closeReader()};dvSoi();
 new MutationObserver(dvSoi).observe(dv,{attributes:true,attributeFilter:['hidden']})}
// cảnh báo mới không tự mở bảng: chỉ hiện chấm đỏ kèm số trên nút. Đọc SỐ đếm của #cb-moi chứ không đọc `hidden` của nó: JS chính luôn ẩn #cb-moi
// khi thẻ Cảnh báo đang chọn (mặc định), kể cả lúc bảng đang gập; CSS đã ẩn chấm khi bảng mở.
const cm=$('#cb-moi');if(cm){const soi=()=>{const n=+cm.textContent||0;pm.hidden=!n;pm.textContent=n};soi();new MutationObserver(soi).observe(cm,{attributes:true,childList:true,characterData:true,subtree:true})}
// ngăn dưới: mỗi ô trong .duoi là một thẻ; ô do mô-đun khác chèn sau cũng tự có thẻ, ô đang ẩn thì không
const NHAN={ai:'AI phân tích',cot:'COT',lt:'Làm tiếp',cbv:'Cảnh báo đường vẽ',dsau:'Độ sâu'};
const tab=document.createElement('div');tab.className='ngan-tab';tab.setAttribute('role','tablist');tab.setAttribute('aria-label','Các ô dưới biểu đồ');duoi.prepend(tab);
let mo=doc('so-ban-ngan')||'',cuoi=mo,stt=0;
const cacO=()=>[...duoi.querySelectorAll('aside.panel')].map(o=>{if(!o.id)o.id='ngan-o'+(++stt);return o});
const anO=o=>o.hidden||(o.id==='ai'&&document.body.hasAttribute('data-khac'));   // body[data-khac] (mã khác vàng) ẩn #ai bằng CSS
// chỉ dựng lại dải thẻ khi danh sách ô hoặc thẻ đang mở đổi thật (COT ghi lại `hidden` mỗi lần vẽ); dựng lại thì giữ tiêu điểm bàn phím
let ky='';
const ve=()=>{const os=cacO(),hien=os.filter(o=>!anO(o)),dang=hien.some(o=>o.id===mo);
 for(const o of os)o.classList.toggle('mo',dang&&o.id===mo);
 const k=hien.map(o=>o.id).join(',')+'|'+(dang?mo:'');if(k===ky)return;ky=k;
 const f=document.activeElement,fo=f&&tab.contains(f)?(f.dataset.o||'mui'):null;tab.textContent='';
 for(const o of hien){const b=document.createElement('button');b.type='button';b.setAttribute('role','tab');b.dataset.o=o.id;b.setAttribute('aria-selected',String(dang&&o.id===mo));
  b.textContent=NHAN[o.id]||o.getAttribute('aria-label')||o.id;tab.appendChild(b)}
 if(hien.length){const m=document.createElement('button');m.type='button';m.className='ngan-mui';m.textContent=dang?'▼':'▲';m.setAttribute('aria-label','Mở hoặc gập ngăn dưới');m.title='Mở hoặc gập ngăn dưới';
  m.setAttribute('aria-expanded',String(dang));tab.appendChild(m)}
 tab.hidden=!hien.length;duoi.classList.toggle('dang-mo',dang);
 if(fo){const b=fo==='mui'?tab.querySelector('.ngan-mui'):tab.querySelector('button[data-o="'+fo+'"]');if(b)b.focus()}};
// phím ← → chuyển giữa các thẻ
tab.addEventListener('keydown',e=>{if(e.key!=='ArrowLeft'&&e.key!=='ArrowRight')return;const bs=[...tab.querySelectorAll('button')],i=bs.indexOf(document.activeElement);if(i<0)return;
 e.preventDefault();bs[(i+(e.key==='ArrowRight'?1:bs.length-1))%bs.length].focus()});
const chon=id=>{mo=id;if(id)cuoi=id;ghi('so-ban-ngan',mo);ve()};
tab.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
 if(b.dataset.o)return chon(mo===b.dataset.o&&duoi.classList.contains('dang-mo')?'':b.dataset.o);
 if(duoi.classList.contains('dang-mo'))return chon('');
 const hien=cacO().filter(o=>!anO(o));chon((hien.find(o=>o.id===cuoi)||hien[0]||{id:''}).id)});
const laO=n=>n&&n.nodeType===1&&n.matches&&n.matches('aside.panel');
new MutationObserver(ms=>{if(ms.some(m=>m.type==='childList'?[...m.addedNodes,...m.removedNodes].some(laO):laO(m.target)))ve()})
 .observe(duoi,{childList:true,subtree:true,attributes:true,attributeFilter:['hidden']});
new MutationObserver(ve).observe(document.body,{attributes:true,attributeFilter:['data-khac']});
// thẻ đã nhớ mà ô đó chưa có lúc mở trang (COT, Độ sâu, Cảnh báo đường vẽ chèn sau vài giây): không tự bung ra khi ô xuất hiện, để biểu đồ
// không co lại dưới con trỏ; nút ▲ vẫn mở đúng thẻ đã nhớ
ve();if(mo&&!cacO().some(o=>o.id===mo&&!anO(o))){mo='';ve()}})();
"""
