"""Trang Nhiều biểu đồ (/da-khung, 26/11/2026): 2, 4 hoặc 1+3 biểu đồ trên một màn hình. Mỗi ô chọn mã và khung riêng (ví dụ XAUUSD, EURUSD,
US30, BTC cùng lúc), hoặc bật Đồng bộ mã để xem một mã ở nhiều khung (mặc định M5, M15, H1, H4). Đồng bộ con trỏ và đồng bộ thời gian giữa các ô,
dòng tóm tắt xu hướng EMA20/EMA50 của từng ô, bấm đúp một ô để mở ô đó ở trang Biểu đồ.

Thời gian thực mà không ngốn kết nối: trình duyệt chỉ cho mỗi máy chủ khoảng 6 kết nối, nên trang KHÔNG mở luồng riêng mà dùng luồng giá dùng chung
của webapp (window.TT trong thi_truong_trang.JS_CHUNG: một tab giữ đúng một kết nối /api/thi-truong/luong cho mọi mã và chuyển giá cho các tab khác).
Mỗi gói giá cập nhật nến đang chạy của các ô có mã đó; khi một ô sang nến mới thì tải lại ô đó từ /api/gia cho khớp MT5, và cứ mỗi phút tải lại mọi ô.
Chỉ đọc: không đặt lệnh."""
from __future__ import annotations

from html import escape

from . import thi_truong_trang, trang

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
"""

JS = r"""
(()=>{const $=s=>document.querySelector(s),LWC=window.LightweightCharts,G=$('#dk-luoi'),TT=window.TT;if(!G)return;
if(!LWC){G.innerHTML='<p class="dk-cho">Không nạp được thư viện biểu đồ.</p>';return}
const TFS={M1:60,M5:300,M15:900,M30:1800,H1:3600,H4:14400,D1:86400},TFK=Object.keys(TFS),tz={timeZone:'Asia/Ho_Chi_Minh'},SO={'2':2,'4':4,'1+3':4};
const ST={bo:'4',o:[],dongMa:1,dongKhung:0,dongTro:1,dongTg:0};
try{const c=JSON.parse(localStorage.getItem('so-dk')||'{}');Object.assign(ST,c);if(c.tf&&!c.o)ST.o=c.tf.map(tf=>({ma:c.ma||'',tf}))}catch(e){}
const MAC=['M5','M15','H1','H4'];for(let i=0;i<4;i++)ST.o[i]=Object.assign({ma:'',tf:MAC[i]},ST.o[i]||{});if(!SO[ST.bo])ST.bo='4';
const U=new URLSearchParams(location.search);if(U.get('ma')){for(const c of ST.o)c.ma=U.get('ma');ST.dongMa=1}
const luu=()=>{try{localStorage.setItem('so-dk',JSON.stringify({bo:ST.bo,o:ST.o,dongMa:ST.dongMa,dongKhung:ST.dongKhung,dongTro:ST.dongTro,dongTg:ST.dongTg}))}catch(e){}};
const css=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let DS=[],VANG='',dongBo=false,ve=0;const O=[];
const soLe=cs=>{let m=0;for(const c of cs.slice(-60))for(const v of c.slice(1,5)){const s=String(v),i=s.indexOf('.');if(i>=0)m=Math.max(m,s.length-i-1)}return Math.min(m,5)};
const fpO=(o,v)=>v==null?'—':Number(v).toLocaleString('vi-VN',{minimumFractionDigits:o.dg,maximumFractionDigits:o.dg});
const mau=()=>({bg:css('--card')||'#111',ink:css('--ink2')||'#999',vien:css('--line')||'#333',len:css('--gain')||'#17935b',xuong:css('--loss')||'#e5532d'});
const gio=(t,ngay)=>new Date(t*1000).toLocaleString('vi-VN',{...tz,day:'2-digit',month:'2-digit',...(ngay?{year:'numeric'}:{hour:'2-digit',minute:'2-digit'})});
const timNen=(cs,t)=>{let a=0,b=cs.length-1;if(b<0||t<cs[0][0])return -1;while(a<b){const m=(a+b+1)>>1;if(cs[m][0]<=t)a=m;else b=m-1}return a};
const maThat=m=>m||VANG;                                                    // ô để trống mã = mã vàng của sàn
const nenLW=c=>({time:c[0],open:c[1],high:c[2],low:c[3],close:c[4]});
const optMa=chon=>{const nh={};for(const s of DS)(nh[s.nhom]=nh[s.nhom]||[]).push(s);const ds=Object.keys(nh).map(n=>`<optgroup label="${esc(n)}">`+nh[n].map(s=>`<option value="${esc(s.ma)}"${s.ma===chon?' selected':''}>${esc(s.ma)}</option>`).join('')+'</optgroup>').join('');
 return ds||`<option value="${esc(chon)}">${esc(chon||'XAUUSD')}</option>`};
// --- một ô biểu đồ
function taoO(i){const el=document.createElement('section'),c=ST.o[i];el.className='dk-o';el.dataset.i=i;
 el.innerHTML=`<header><select class="dk-ma" aria-label="Mã">${optMa(maThat(c.ma))}</select><select class="dk-tf" aria-label="Khung thời gian">${TFK.map(k=>`<option${k===c.tf?' selected':''}>${k}</option>`).join('')}</select>`
  +'<span class="dk-xu"></span><b class="dk-gia">—</b><span class="dk-bd"></span><a class="dk-mo" href="/bieu-do" title="Mở biểu đồ đầy đủ. Bấm đúp vào biểu đồ cũng mở được" aria-label="Mở biểu đồ đầy đủ"><span>Mở biểu đồ đầy đủ</span></a></header><div class="dk-c"></div>';
 G.appendChild(el);const M=mau(),o={i,el,cs:[],e20:null,e50:null,ban:0,dg:2,get ma(){return maThat(ST.o[i].ma)},get tf(){return ST.o[i].tf}};
 o.chart=LWC.createChart(el.querySelector('.dk-c'),{autoSize:true,layout:{background:{type:'solid',color:M.bg},textColor:M.ink,attributionLogo:false},
  grid:{vertLines:{color:'rgba(128,128,128,.1)'},horzLines:{color:'rgba(128,128,128,.1)'}},rightPriceScale:{borderColor:M.vien,scaleMargins:{top:.08,bottom:.06}},
  timeScale:{borderColor:M.vien,timeVisible:true,secondsVisible:false,rightOffset:4,
   tickMarkFormatter:(t,l)=>{const d=new Date(t*1000);return l===0?d.toLocaleDateString('vi-VN',{...tz,year:'numeric'}):l===1?d.toLocaleDateString('vi-VN',{...tz,month:'2-digit',year:'numeric'}):l===2?d.toLocaleDateString('vi-VN',{...tz,day:'2-digit',month:'2-digit'}):d.toLocaleTimeString('vi-VN',{...tz,hour:'2-digit',minute:'2-digit'})}},
  crosshair:{mode:0},localization:{locale:'vi-VN',priceFormatter:p=>fpO(o,p),timeFormatter:t=>gio(t,o.tf==='D1')}});
 o.nen=o.chart.addSeries(LWC.CandlestickSeries,{upColor:M.len,downColor:M.xuong,wickUpColor:M.len,wickDownColor:M.xuong,borderVisible:false});
 o.l20=o.chart.addSeries(LWC.LineSeries,{color:'#4da3ff',lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
 o.l50=o.chart.addSeries(LWC.LineSeries,{color:'#ffb020',lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
 el.querySelector('.dk-ma').addEventListener('change',e=>{const v=e.target.value;for(const k of(ST.dongMa?O:[o])){ST.o[k.i].ma=v;k.el.querySelector('.dk-ma').value=v;tai(k,1)}luu()});
 el.querySelector('.dk-tf').addEventListener('change',e=>{const v=e.target.value;for(const k of(ST.dongKhung?O:[o])){ST.o[k.i].tf=v;k.el.querySelector('.dk-tf').value=v;tai(k,1)}luu()});
 el.querySelector('.dk-c').addEventListener('dblclick',()=>{location.href=o.el.querySelector('.dk-mo').href});
 // con trỏ đồng bộ: rê chuột ở một ô thì các ô khác chỉ vào nến chứa cùng thời điểm (cùng mức giá nếu cùng mã)
 o.chart.subscribeCrosshairMove(p=>{if(!ST.dongTro||dongBo)return;dongBo=true;try{for(const k of O){if(k===o||!k.cs.length)continue;
  if(!p||p.time==null||!p.point){k.chart.clearCrosshairPosition();continue}const j=timNen(k.cs,p.time);if(j<0){k.chart.clearCrosshairPosition();continue}
  const gia=k.ma===o.ma?o.nen.coordinateToPrice(p.point.y):k.cs[j][4];if(gia!=null)k.chart.setCrosshairPosition(gia,k.cs[j][0],k.nen)}}finally{dongBo=false}});
 // đồng bộ thời gian: kéo hoặc phóng một ô thì các ô khác hiện cùng khoảng thời gian
 o.chart.timeScale().subscribeVisibleTimeRangeChange(r=>{if(!ST.dongTg||dongBo||!r)return;dongBo=true;try{for(const k of O)if(k!==o&&k.cs.length)try{k.chart.timeScale().setVisibleRange(r)}catch(e){}}finally{dongBo=false}});
 return o}
async function tai(o,dau){const ma=o.ma,tf=o.tf,lan=++o.ban;if(!ma){o.el.querySelector('.dk-bd').textContent='Chưa có danh sách mã từ MT5';return}
 try{const r=await fetch('/api/gia?tf='+tf+'&n=400&ma='+encodeURIComponent(ma),{cache:'no-store'});const t=await r.text();if(!r.ok)throw new Error(t);const j=JSON.parse(t);
  if(lan!==o.ban||tf!==o.tf||ma!==o.ma)return;const cs=(j.candles||[]).map(c=>c.slice());if(!cs.length)throw new Error(j.ly_do_khong_song||'chưa có nến');
  const x=TT&&TT.by().get(ma);o.dg=x&&x.so_le!=null?x.so_le:soLe(cs);o.cs=cs;o.nen.setData(cs.map(nenLW));
  const dl=k=>cs.map((c,n)=>j[k]&&j[k][n]!=null?{time:c[0],value:j[k][n]}:{time:c[0]});o.l20.setData(dl('ema20'));o.l50.setData(dl('ema50'));
  const cuoi=k=>{const a=j[k]||[];for(let n=a.length-1;n>=0;n--)if(a[n]!=null)return a[n];return null};o.e20=cuoi('ema20');o.e50=cuoi('ema50');
  o.chart.applyOptions({timeScale:{timeVisible:tf!=='D1'}});if(dau)o.chart.timeScale().setVisibleLogicalRange({from:cs.length-(tf==='D1'?120:100),to:cs.length+4});
  o.el.querySelector('.dk-mo').href='/bieu-do'+(ma===VANG?'':'?ma='+encodeURIComponent(ma));dau_(o)}
 catch(e){o.el.querySelector('.dk-bd').textContent='Chưa tải được: '+e.message}}
// đầu ô: giá, thay đổi của nến đang chạy, xu hướng EMA20/EMA50
function dau_(o){const c=o.cs[o.cs.length-1];if(!c)return;const h=o.el.querySelector('header'),xu=h.querySelector('.dk-xu'),len=o.e20!=null&&o.e50!=null?o.e20>=o.e50:null;
 h.querySelector('.dk-gia').textContent=fpO(o,c[4]);const d=c[4]-c[1];h.querySelector('.dk-bd').textContent=(d>=0?'+':'−')+fpO(o,Math.abs(d))+' · '+gio(c[0],o.tf==='D1');
 xu.className='dk-xu '+(len==null?'':len?'len':'xuong');xu.textContent=len==null?'':len?'▲ Tăng':'▼ Giảm';tom()}
function tom(){const ds=O.filter(o=>o.e20!=null&&o.e50!=null),n=ds.filter(o=>o.e20>=o.e50).length,el=$('#dk-tom');if(!el)return;if(!ds.length){el.innerHTML='';return}
 const motMa=ds.every(o=>o.ma===ds[0].ma);
 el.innerHTML='<span>Xu hướng EMA20/EMA50:</span>'+ds.map(o=>`<span class="chip ${o.e20>=o.e50?'len':'xuong'}">${motMa?'':esc(o.ma)+' '}${o.tf} ${o.e20>=o.e50?'▲':'▼'}</span>`).join('')
  +`<span><b>${n}/${ds.length}</b> ô tăng · <b>${ds.length-n}/${ds.length}</b> ô giảm</span>`
  +(motMa?(n===ds.length?'<span class="chip len">Các khung đồng thuận tăng</span>':n===0?'<span class="chip xuong">Các khung đồng thuận giảm</span>':'<span class="chip">Các khung chưa cùng chiều</span>'):'')}
// --- giá trực tiếp từ luồng dùng chung: cập nhật nến đang chạy; sang nến mới thì tải lại ô đó để nến vừa đóng và EMA khớp MT5
function apGia(dsMa){const by=TT.by();for(const o of O){if(!dsMa.includes(o.ma))continue;const x=by.get(o.ma);if(!x||!x.q||!o.cs.length)continue;
  const b=x.q[0],ts=Math.floor(x.q[2]/1000),cs=o.cs,last=cs[cs.length-1],st=TFS[o.tf];if(!isFinite(b)||!isFinite(ts))continue;
  if(ts>=last[0]+st){cs.push([last[0]+st*Math.floor((ts-last[0])/st),b,b,b,b]);setTimeout(()=>tai(o),1500)}
  else if(ts>=last[0]){last[2]=Math.max(last[2],b);last[3]=Math.min(last[3],b);last[4]=b}else continue;o.can=1}
 if(!ve){ve=1;requestAnimationFrame(()=>{ve=0;for(const o of O)if(o.can){o.can=0;try{o.nen.update(nenLW(o.cs[o.cs.length-1]))}catch(e){}dau_(o)}})}}
function trangThai(){const el=$('#dk-song');if(!el||!TT)return;const t=TT.tt;el.className='dk-song '+(t.ok?'ok':'loi');el.querySelector('span').textContent=t.ok?'Trực tiếp theo từng tick':'Chưa có giá trực tiếp: '+(t.ly||'')}
// --- dựng lưới
function dung(){for(const o of O)try{o.chart.remove()}catch(e){}O.length=0;G.innerHTML='';G.dataset.bo=ST.bo;for(let i=0;i<SO[ST.bo];i++)O.push(taoO(i));
 O.forEach((o,i)=>setTimeout(()=>tai(o,1),i*120))}
document.querySelectorAll('#dk-bo button').forEach(b=>{b.setAttribute('aria-pressed',String(b.dataset.v===ST.bo));b.addEventListener('click',()=>{ST.bo=b.dataset.v;luu();
 document.querySelectorAll('#dk-bo button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));dung()})});
for(const[id,k]of[['dk-dma','dongMa'],['dk-dkh','dongKhung'],['dk-dtro','dongTro'],['dk-dtg','dongTg']]){const b=$('#'+id);if(!b)continue;b.setAttribute('aria-pressed',String(!!ST[k]));
 b.addEventListener('click',()=>{ST[k]=ST[k]?0:1;luu();b.setAttribute('aria-pressed',String(!!ST[k]));
  if(k==='dongMa'&&ST[k]&&O[0]){const v=O[0].ma;for(const o of O.slice(1)){ST.o[o.i].ma=v;o.el.querySelector('.dk-ma').value=v;tai(o,1)}}
  if(k==='dongTro'&&!ST[k])for(const o of O)o.chart.clearCrosshairPosition()})}
setInterval(()=>{if(document.visibilityState==='visible')O.forEach((o,i)=>setTimeout(()=>tai(o),i*400))},60000);   // mỗi phút đồng bộ lại với MT5
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')O.forEach(o=>tai(o))});
new MutationObserver(()=>{const M=mau();for(const o of O){o.chart.applyOptions({layout:{background:{type:'solid',color:M.bg},textColor:M.ink},rightPriceScale:{borderColor:M.vien},timeScale:{borderColor:M.vien}});
 o.nen.applyOptions({upColor:M.len,downColor:M.xuong,wickUpColor:M.len,wickDownColor:M.xuong})}}).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
if(TT){TT.on((l,ds)=>{if(l==='gia'&&ds)apGia(ds);trangThai()});TT.batDau(60)}
fetch('/api/ma',{cache:'no-store'}).then(r=>r.json()).then(j=>{DS=(j.ds||[]);const v=DS.find(s=>s.la_vang);VANG=v?v.ma:(DS[0]||{}).ma||'';
 for(const c of ST.o)if(c.ma&&!DS.some(s=>s.ma===c.ma))c.ma='';dung()}).catch(()=>{dung()});
window.DK={O,ST}})();
"""


def trang_da_khung(ten: str) -> str:
    bo = ''.join(f'<button type="button" data-v="{v}">{t}</button>' for v, t in (('2', '2 biểu đồ'), ('4', '4 biểu đồ'), ('1+3', '1 lớn + 3 nhỏ')))
    dong = ''.join(f'<button type="button" id="{i}">{t}</button>' for i, t in (('dk-dma', 'Đồng bộ mã'), ('dk-dkh', 'Đồng bộ khung'),
                                                                            ('dk-dtro', 'Đồng bộ con trỏ'), ('dk-dtg', 'Đồng bộ thời gian')))
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Nhiều biểu đồ · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'da-khung', '<button id="theme" type="button">Nền tối</button>') + '<main class="rong">',
        '<div class="dk-top"><div><h1>Nhiều biểu đồ</h1><p>Hai, bốn hoặc một lớn ba nhỏ trên một màn hình, chạy theo từng tick. Mỗi ô chọn mã và khung riêng; '
        'bật Đồng bộ mã để xem một mã ở nhiều khung. Rê chuột ở một ô thì các ô khác chỉ vào cùng thời điểm; bấm đúp một ô để mở ô đó ở trang Biểu đồ.</p></div>'
        '<span id="dk-song" class="dk-song"><i></i><span>Đang nối…</span></span></div>',
        f'<div class="dk-thanh"><div class="dk-seg" id="dk-bo" role="group" aria-label="Bố cục">{bo}</div>'
        f'<div class="dk-seg" role="group" aria-label="Đồng bộ">{dong}</div></div>',
        '<div class="dk-tom" id="dk-tom" aria-live="polite"></div>',
        '<div class="dk-luoi" id="dk-luoi" data-bo="4"></div>',
        '<p class="dk-ghi">Xu hướng ở đây chỉ so EMA20 với EMA50 trên nến của từng ô, để nhìn nhanh các ô có cùng chiều không; đây là mô tả, không phải '
        'tín hiệu vào lệnh. Biểu đồ vẽ bằng <a href="https://www.tradingview.com/lightweight-charts/" target="_blank" rel="noopener">TradingView Lightweight Charts™</a>. '
        'Copyright (c) 2026 TradingView, Inc.</p>',
        '<footer>' + escape(trang.mien_tru()) + '</footer></main>'
        f'<script src="/tinh/lightweight-charts.js"></script><script>{trang.JS}</script><script>{thi_truong_trang.JS_CHUNG}</script><script>{JS}</script></body></html>'])
