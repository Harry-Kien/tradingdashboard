"""Trang Tin tức & tâm lý (/tin-tuc): dải tâm lý tổng hợp (khẩu vị rủi ro, sợ hãi/tham lam crypto, đồng thuận kỹ thuật toàn thị trường,
đồng tiền mạnh/yếu, tin mạnh kế tiếp), dòng tin từ các nguồn RSS (tin_tuc.py) và vị thế của dòng tiền đầu cơ theo COT (tam_ly.py).
Giá và chỉ báo lấy từ bảng giá trực tiếp (JS_CHUNG của thi_truong_trang)."""
from __future__ import annotations

from html import escape

from . import thi_truong_trang as TTT
from . import trang

CSS = r"""
.tl-dai{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:16px 0 6px}
.tl-o{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:13px 15px;min-width:0}
.tl-o>span{display:block;font-size:12px;color:var(--mute)}.tl-o b{display:block;font-size:20px;font-weight:600;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tl-o small{display:block;font-size:12px;color:var(--ink2);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tl-bar{position:relative;height:8px;border-radius:4px;margin-top:8px;background:linear-gradient(90deg,var(--loss),#e0a100 30%,var(--track) 50%,color-mix(in srgb,var(--gain) 60%,var(--track)) 70%,var(--gain))}
.tl-bar i{position:absolute;top:-4px;width:4px;height:16px;border-radius:2px;background:var(--ink);transform:translateX(-50%);transition:left .4s}
.tl-hai{display:flex;height:8px;border-radius:4px;overflow:hidden;margin-top:8px;background:var(--track)}.tl-hai u{background:var(--gain)}.tl-hai s{background:var(--loss)}
.tl-g{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(360px,1fr);gap:16px;align-items:start;margin-top:14px}@media(max-width:1100px){.tl-g{grid-template-columns:1fr}}
.tn-tool{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 10px}
.tn-tool input[type=search]{min-height:36px;border:1px solid var(--line);border-radius:10px;background:var(--card2);color:var(--ink);padding:0 12px;font:inherit;font-size:13px;flex:1;min-width:180px}
#tn-nhan button{min-height:28px;padding:0 10px;font-size:12px}
.tn-moi{display:block;width:100%;margin:0 0 10px;min-height:34px;border-radius:10px;border:1px solid color-mix(in srgb,var(--series) 45%,transparent);background:color-mix(in srgb,var(--series) 12%,transparent);
color:var(--series);font:600 13px inherit;font-family:inherit;cursor:pointer}.tn-moi[hidden]{display:none}
.tn{display:grid;grid-template-columns:72px minmax(0,1fr);gap:4px 14px;padding:12px 4px;border-bottom:1px solid var(--line)}.tn:last-child{border:0}
.tn time{font-size:12px;color:var(--mute);line-height:1.35}.tn time b{display:block;color:var(--ink2);font-size:13px;font-weight:600}
.tn a{color:var(--ink);text-decoration:none;font-weight:600;font-size:14px;line-height:1.4}.tn a:hover{color:var(--series);text-decoration:underline}
.tn p{margin:4px 0 0;font-size:12.5px;color:var(--ink2);line-height:1.5}
.tn .the{display:flex;flex-wrap:wrap;gap:5px;margin-top:6px;align-items:center}
.tn .nguon{font-size:11px;color:var(--mute);font-weight:600}
.tn .nh{font-size:10.5px;font-weight:700;padding:2px 7px;border-radius:6px;background:var(--card2);border:1px solid var(--line);color:var(--ink2)}
.tn .nh.qt{background:color-mix(in srgb,var(--warn) 14%,transparent);border-color:transparent;color:var(--warn)}
.tn.moi a::before{content:"Mới";font-size:10px;font-weight:700;color:var(--btn-ink);background:var(--series);border-radius:5px;padding:1px 6px;margin-right:7px;vertical-align:2px}
.cot-n{margin:14px 0 4px;font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--series);font-weight:700}
.cot{display:grid;grid-template-columns:104px minmax(0,1fr) 112px;gap:4px 12px;align-items:center;padding:8px 2px;border-bottom:1px solid var(--line);font-size:13px}
.cot:last-child{border:0}.cot.cu{opacity:.45}
.cot b{font-size:13.5px}.cot b small{display:block;font-size:11px;color:var(--mute);font-weight:400;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cot .hg{position:relative;height:10px;border-radius:5px;background:linear-gradient(90deg,color-mix(in srgb,var(--loss) 55%,var(--track)),var(--track) 50%,color-mix(in srgb,var(--gain) 55%,var(--track)))}
.cot .hg i{position:absolute;top:-3px;width:4px;height:16px;border-radius:2px;background:var(--ink);transform:translateX(-50%)}
.cot .hg+small{display:flex;justify-content:space-between;font-size:11px;color:var(--mute);margin-top:3px}
.cot .so{text-align:right;font-variant-numeric:tabular-nums}.cot .so small{display:block;font-size:11px}
.cd{display:inline-block;font-size:10px;font-weight:700;padding:1px 6px;border-radius:5px;margin-left:6px;vertical-align:1px}
.cd.mua{background:color-mix(in srgb,var(--gain) 18%,transparent);color:var(--gain)}.cd.ban{background:color-mix(in srgb,var(--loss) 18%,transparent);color:var(--loss)}
.fng{display:grid;grid-template-columns:150px minmax(0,1fr);gap:14px;align-items:center}
.fng svg{width:100%;height:auto;display:block}.fng b{display:block;font-size:30px;line-height:1.1}.fng small{color:var(--mute);font-size:12px}
.tia2{width:100%;height:44px;display:block;margin-top:6px}.tia2 polyline{fill:none;stroke:var(--series);stroke-width:1.6}
@media(max-width:640px){.tl-dai{grid-template-columns:1fr 1fr;gap:8px}.tl-o{padding:10px 11px}.tl-o b{font-size:15px}.tl-o small{font-size:11px}
.tl-dai .tl-o:first-child{grid-column:1/-1}.cot{grid-template-columns:86px minmax(0,1fr) 92px;gap:4px 8px}.fng{grid-template-columns:110px minmax(0,1fr)}.tn{grid-template-columns:56px minmax(0,1fr);gap:4px 10px}}
"""

JS = r"""
(()=>{const T=TT,$=s=>document.querySelector(s),esc=T.esc,fmt=T.fmt,pct=T.pct,cls=T.cls;T.pill($('#song'));
const VN=ms=>new Date(ms).toLocaleTimeString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit'});
const truoc=ms=>{const p=Math.max(0,Math.round((Date.now()-ms)/60000));return p<1?'vừa xong':p<60?p+' phút trước':p<1440?Math.floor(p/60)+' giờ trước':Math.floor(p/1440)+' ngày trước'};
const dem=ms=>{const p=Math.max(0,Math.round(ms/60000)),g=Math.floor(p/60);return g?g+' giờ '+(p%60)+' phút':p+' phút'};
// ---- dải tâm lý tổng hợp (theo giá trực tiếp)
let FNG=null;
function dai(){if(!T.S)return;const o=(t,b,s,x='')=>`<div class="tl-o"><span>${t}</span><b>${b}</b>${x}${s?`<small>${s}</small>`:''}</div>`;let h='';
 const k=T.khauVi();if(k){const n=k.d>.25?['Ưa rủi ro','gain']:k.d<-.25?['Né rủi ro','loss']:['Trung tính',''];h+=o('Khẩu vị rủi ro hôm nay',`<span class="${n[1]}">${n[0]}</span>`,'chỉ số, AUDJPY, BTC so với vàng, JPY, CHF',`<div class="rr-bar"><i style="left:${(50+k.d*50).toFixed(1)}%"></i></div>`)}
 if(FNG)h+=o('Sợ hãi & tham lam (crypto)',`${FNG.gt} · ${esc(FNG.nhan)}`,`hôm qua ${FNG.truoc??'—'} · tuần trước ${FNG.tuan??'—'}`,`<div class="tl-bar"><i style="left:${FNG.gt}%"></i></div>`);
 const ds=[...T.by().values()].filter(x=>x.kt&&x.kt.H1),m=ds.filter(x=>x.kt.H1.d>.1).length,b=ds.filter(x=>x.kt.H1.d<-.1).length;
 if(ds.length)h+=o('Đồng thuận kỹ thuật H1',`<span class="gain">${Math.round(m/ds.length*100)}% mua</span> · <span class="loss">${Math.round(b/ds.length*100)}% bán</span>`,`${ds.length} mã, còn lại trung tính`,`<div class="tl-hai"><u style="width:${m/ds.length*100}%"></u><span style="flex:1"></span><s style="width:${b/ds.length*100}%"></s></div>`);
 const sm=T.sucManh('ngay').filter(a=>a.v!=null);if(sm.length)h+=o('Tiền tệ mạnh / yếu hôm nay',`<span class="gain">${sm[0].c}</span> · <span class="loss">${sm[sm.length-1].c}</span>`,`${pct(sm[0].v)} / ${pct(sm[sm.length-1].v)}`);
 const L=T.S.lich,now=Date.now(),tin=L&&L.ds?L.ds.filter(e=>e.muc>=3&&Date.parse(e.t)>now)[0]:null;
 h+=o('Tin mạnh kế tiếp',tin?`${esc(tin.tien)} · ${dem(Date.parse(tin.t)-now).replace(' phút','p').replace(' giờ','g')}`:'Không có trong 7 ngày',tin?esc(tin.ten)+' · lúc '+VN(Date.parse(tin.t)):'');
 $('#tl-dai').innerHTML=h}
// ---- tin tức
let NHAN=[],nhan='',q='',chiQT=false,TIN=[],cho=[],daXem=0;try{daXem=+localStorage.getItem('tn-xem')||0;nhan=localStorage.getItem('tn-nhan')||''}catch(e){}
const moc=daXem;
async function taiTin(dau){try{const r=await fetch('/api/tin-tuc?'+new URLSearchParams({nhan,q}),{cache:'no-store'});if(!r.ok)throw 0;const j=await r.json();NHAN=j.nhan||NHAN;
 if(!$('#tn-nhan').dataset.co){$('#tn-nhan').dataset.co=1;veNhan()}
 const cu=new Set(TIN.map(x=>x.id)),moi=j.ds.filter(x=>!cu.has(x.id));
 if(dau||!TIN.length){TIN=j.ds;cho=[];veTin()}else if(moi.length){cho=j.ds;$('#tn-moi').hidden=false;$('#tn-moi').textContent=`${moi.length} tin mới · bấm để hiện`}
 const ng=Object.values(j.nguon||{});$('#tn-ng').textContent=(j.tai_luc?'Cập nhật '+truoc(Date.parse(j.tai_luc))+' · ':'')+ng.filter(n=>!n.loi).length+'/'+(ng.length||'—')+' nguồn chạy'+(ng.some(n=>n.loi)?' · lỗi: '+ng.filter(n=>n.loi).map(n=>n.ten).join(', '):'');
 }catch(e){if(!TIN.length)$('#tn').innerHTML='<p class="small">Chưa đọc được tin. Webapp tải tin 5 phút một lần; lần đầu cần chờ vài giây sau khi khởi động.</p>'}}
function veNhan(){$('#tn-nhan').innerHTML=`<button type="button" data-n="" aria-pressed="${!nhan}">Tất cả</button>`+NHAN.map(n=>`<button type="button" data-n="${n.k}" aria-pressed="${n.k===nhan}">${esc(n.n)}</button>`).join('')}
function veTin(){const ten=Object.fromEntries(NHAN.map(n=>[n.k,n.n]));const ds=TIN.filter(x=>!chiQT||x.quan_trong);
 $('#tn').innerHTML=ds.map(x=>{const t=Date.parse(x.t);return`<article class="tn${t>moc&&moc?' moi':''}"><time><b>${VN(t)}</b>${truoc(t)}</time><div><a href="${esc(x.link)}" target="_blank" rel="noopener noreferrer">${esc(x.tieu_de)}</a>${x.tom_tat?`<p>${esc(x.tom_tat)}</p>`:''}
  <div class="the"><span class="nguon">${esc(x.nguon)}</span>${x.quan_trong?`<span class="nh qt">${x.loai==='ngan_hang'?'Ngân hàng trung ương':'Quan trọng'}</span>`:''}${(x.nhan||[]).map(k=>`<span class="nh">${esc(ten[k]||k)}</span>`).join('')}</div></div></article>`}).join('')
  ||'<p class="small">Không có tin nào khớp bộ lọc.</p>';
 try{localStorage.setItem('tn-xem',Date.now())}catch(e){}}
$('#tn-nhan').addEventListener('click',e=>{const b=e.target.closest('button[data-n]');if(!b)return;nhan=b.dataset.n;try{localStorage.setItem('tn-nhan',nhan)}catch(_){}veNhan();taiTin(1)});
let hq;$('#tn-tim').addEventListener('input',e=>{clearTimeout(hq);hq=setTimeout(()=>{q=e.target.value.trim();taiTin(1)},250)});
$('#tn-qt').addEventListener('change',e=>{chiQT=e.target.checked;veTin()});
$('#tn-moi').addEventListener('click',()=>{TIN=cho;cho=[];$('#tn-moi').hidden=true;veTin()});
// ---- tâm lý: COT và sợ hãi/tham lam
function kq(n){const a=Math.abs(n);return(n<0?'−':'+')+(a>=1e6?fmt(a/1e6,2)+'M':a>=1e3?fmt(a/1e3,1)+'K':fmt(a,0))}
async function taiTamLy(){try{const r=await fetch('/api/tam-ly',{cache:'no-store'});if(!r.ok)throw 0;const j=await r.json();FNG=j.fng;dai();
 if(j.fng){const f=j.fng,v=f.lich_su||[],lo=0,hi=100,w=300,h=44;const a=Math.PI*(1-f.gt/100),cx=60,cy=60,r0=46;
  $('#fng').innerHTML=`<div class="fng"><svg viewBox="0 0 120 70"><path d="M14 60A46 46 0 0 1 106 60" stroke="var(--track)" stroke-width="10" fill="none"/><path d="M14 60A46 46 0 0 1 106 60" stroke="url(#gfng)" stroke-width="10" fill="none"/>
   <defs><linearGradient id="gfng"><stop offset="0" stop-color="var(--loss)"/><stop offset=".5" stop-color="#e0a100"/><stop offset="1" stop-color="var(--gain)"/></linearGradient></defs>
   <line x1="${cx}" y1="${cy}" x2="${(cx+r0*Math.cos(a)).toFixed(1)}" y2="${(cy-r0*Math.sin(a)).toFixed(1)}" stroke="var(--ink)" stroke-width="3" stroke-linecap="round"/><circle cx="${cx}" cy="${cy}" r="4" fill="var(--ink)"/></svg>
   <div><b>${f.gt}</b><span>${esc(f.nhan)}</span><br><small>Hôm qua ${f.truoc??'—'} · tuần trước ${f.tuan??'—'} · 0 là sợ hãi tột độ, 100 là tham lam tột độ</small>
   ${v.length>1?`<svg class="tia2" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><polyline points="${v.map((x,i)=>(i/(v.length-1)*w).toFixed(1)+','+(h-2-(x-lo)/(hi-lo)*(h-4)).toFixed(1)).join(' ')}"/></svg><small>${v.length} ngày gần nhất</small>`:''}</div></div>`}
 else $('#fng').innerHTML='<p class="small">Chưa tải được chỉ số.</p>';
 const ds=j.cot||[];if(!ds.length){$('#cot').innerHTML='<p class="small">Đang tải báo cáo COT của CFTC (lần đầu khoảng 5–10 giây)…</p>';return}
 let h='';for(const g of Object.keys(j.nhom)){const v=ds.filter(x=>x.nhom===g);if(!v.length)continue;h+=`<div class="cot-n">${esc(j.nhom[g])}</div>`;
  h+=v.map(x=>{const nh=x.bao_cao==='tff'?'Quỹ đầu cơ (Leveraged Funds)':'Quỹ quản lý (Managed Money)',am=x.bao_cao==='tff'?'Quỹ đầu tư dài hạn':'Nhà sản xuất, người dùng';
   const tip=`${x.ten} · tuần chốt ${x.ngay}\n${nh}: ròng ${kq(x.rong)} hợp đồng (${x.pct_oi!=null?fmt(x.pct_oi,1)+'% hợp đồng mở':''}), đổi ${kq(x.doi)} so với tuần trước\n${am}: ròng ${kq(x.am_rong)}, đổi ${kq(x.am_doi)}\nThứ hạng ${fmt(x.hang,0)}/100 trong ${x.so_tuan} tuần`+(x.sym&&x.chieu<0?`\nHợp đồng là ${x.nhan}/USD: mua ${x.nhan} tương ứng BÁN ${x.sym}`:'');
   return`<div class="cot${x.cu?' cu':''}" title="${esc(tip)}"><b>${esc(x.nhan)}${x.cuc_doan?`<span class="cd ${x.cuc_doan}">${x.cuc_doan==='mua'?'Đỉnh 3 năm':'Đáy 3 năm'}</span>`:''}<small>${esc(x.ten)}${x.cu?' · số cũ '+x.ngay:''}</small></b>
    <div><div class="hg"><i style="left:${x.hang}%"></i></div><small><span>0</span><span>hạng ${fmt(x.hang,0)}/100</span><span>100</span></small></div>
    <div class="so"><b class="${cls(x.rong)}">${kq(x.rong)}</b><small class="${cls(x.doi)}">${x.doi>0?'▲':x.doi<0?'▼':''} ${kq(x.doi)} tuần qua</small></div></div>`}).join('')}
 const nd=ds.filter(x=>!x.cu).map(x=>x.ngay).sort().pop();
 $('#cot').innerHTML=h+`<p class="small">Số chốt ngày ${nd||'—'} (thứ Ba), CFTC công bố thứ Sáu nên đã cũ 3–10 ngày khi đọc. Vạch là vị thế ròng tuần này nằm ở đâu giữa mức bán ròng sâu nhất (0) và mua ròng nhiều nhất (100) của 3 năm. Với JPY, CHF, CAD: mua hợp đồng là mua đồng tiền đó, tức bán USDJPY, USDCHF, USDCAD. Đã đo trên vàng: vị thế đi theo giá, không báo trước được giá; đây là bối cảnh, không phải tín hiệu.</p>`}
 catch(e){$('#cot').innerHTML='<p class="small">Chưa đọc được dữ liệu tâm lý.</p>'}}
T.on(l=>{if(l==='anh')dai()});let lanDai=0;T.on(l=>{if(l==='gia'&&Date.now()-lanDai>2000){lanDai=Date.now();dai()}});
T.batDau(30);taiTin(1);taiTamLy();setInterval(()=>{if(document.visibilityState==='visible')taiTin(0)},60000);setInterval(()=>{if(document.visibilityState==='visible')taiTamLy()},15*60000);
setInterval(()=>{if(document.visibilityState==='visible'&&TIN.length&&!cho.length)document.querySelectorAll('.tn time').forEach((el,i)=>{const x=TIN.filter(y=>!chiQT||y.quan_trong)[i];if(x)el.innerHTML=`<b>${VN(Date.parse(x.t))}</b>${truoc(Date.parse(x.t))}`})},60000)})();
"""


def trang_tin_tuc(ten: str) -> str:
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Tin tức & tâm lý · {escape(ten)}</title><style>{trang.CSS}{TTT.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'tin-tuc', '<button id="theme" type="button">Nền tối</button>') + '<main class="rong">',
        '<div class="tt-top"><div><h1>Tin tức &amp; tâm lý thị trường</h1><p>Tin nhanh Forex, lãi suất, vàng, dầu, chỉ số và thông cáo của ngân hàng trung ương; '
        'vị thế của dòng tiền đầu cơ và tâm lý chung của thị trường, cập nhật theo giá trực tiếp.</p></div><span id="song" class="song-pill"><i></i>Đang nối…</span></div>',
        '<div class="tl-dai" id="tl-dai"></div>',
        '<div class="tl-g"><section class="tt-card" style="margin:0"><div class="tn-tool"><h2 style="margin:0">Tin mới</h2><span class="grow" style="flex:1"></span>'
        '<label style="display:flex;gap:6px;align-items:center;font-size:12.5px;color:var(--ink2)"><input type="checkbox" id="tn-qt"> Chỉ tin quan trọng</label></div>'
        '<div class="tn-tool"><div class="sg" id="tn-nhan"></div></div><div class="tn-tool"><input type="search" id="tn-tim" placeholder="Tìm trong tin: Fed, CPI, gold…" aria-label="Tìm trong tin"></div>'
        '<button type="button" class="tn-moi" id="tn-moi" hidden></button><div id="tn"><p class="small">Đang đọc tin…</p></div>'
        '<p class="small" id="tn-ng"></p><p class="small">Tiêu đề và tóm tắt ngắn lấy từ RSS của InvestingLive (ForexLive), CNBC, Fed, ECB, BoE, bằng tiếng Anh như bản gốc; '
        'bấm tiêu đề để đọc bài ở trang của nguồn. Nhãn đồng tiền gắn tự động theo từ khóa nên có thể sót hoặc thừa.</p></section>'
        '<div><section class="tt-card" style="margin:0"><h2>Sợ hãi &amp; tham lam (crypto)</h2><p class="sub">Chỉ số của alternative.me cho thị trường tiền mã hóa, tính mỗi ngày.</p><div id="fng"></div></section>'
        '<section class="tt-card"><h2>Dòng tiền đầu cơ (COT)</h2><p class="sub">Vị thế ròng của quỹ đầu cơ trên hợp đồng tương lai, theo báo cáo hằng tuần của CFTC. '
        'Thanh hạng: 0 là bán ròng sâu nhất, 100 là mua ròng nhiều nhất trong 3 năm. Rê chuột vào một dòng để xem chi tiết.</p><div id="cot"><p class="small">Đang đọc…</p></div></section></div></div>',
        '<p class="note" style="margin-top:22px"><b>Bối cảnh, không phải tín hiệu.</b> Tin tức, vị thế COT và các chỉ số tâm lý mô tả thị trường đang nghĩ gì; '
        'chưa chỉ số nào ở đây được kiểm chứng là báo trước được giá. Tỷ lệ lệnh mua/bán của nhà giao dịch nhỏ lẻ chưa có vì các nguồn công khai chặn tải tự động.</p>',
        '<footer>Nguồn: RSS của InvestingLive, CNBC, Federal Reserve, ECB, Bank of England (tải 5 phút một lần); báo cáo Commitments of Traders của CFTC '
        '(cftc.gov); Fear &amp; Greed Index của alternative.me. Webapp chỉ tải về, không gửi dữ liệu nào. ' + escape(trang.MIEN_TRU)
        + f'</footer></main><script>{trang.JS}</script><script>{TTT.JS_CHUNG}</script><script>{JS}</script></body></html>'])
