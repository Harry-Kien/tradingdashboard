"""Trang Renko và Điểm & Hình (/renko, 26/11/2026): hai kiểu biểu đồ chỉ theo GIÁ, bỏ thời gian.

- Renko: mỗi viên gạch là một bước giá cố định (cỡ ô); giá đi đủ một ô theo chiều cũ thì thêm gạch, đi ngược đủ hai ô thì đổi chiều.
- Điểm & Hình (Point & Figure): cột X khi giá lên, cột O khi giá xuống; đổi cột khi giá đi ngược đủ số ô đảo chiều (mặc định 3).
Cả hai tính trên giá ĐÓNG của nến đã đóng (lấy từ /api/gia, tới 1.500 nến), cỡ ô mặc định bằng ATR14 của khung đang chọn hoặc tự nhập.
Vì không theo trục thời gian đều nên là trang xem riêng, không ghép vào biểu đồ nến (hình vẽ và chỉ báo ở đó bám theo thời gian).
Chỉ đọc: không đặt lệnh. Vẽ bằng canvas của trình duyệt, không dùng thư viện ngoài."""
from __future__ import annotations

from html import escape

from . import trang

CSS = r"""
main.rong{max-width:none;padding-left:16px;padding-right:16px}
.rk-top h1{margin:0}.rk-top p{margin:4px 0 0;color:var(--ink2);max-width:860px;font-size:14px;line-height:1.5}
.rk-thanh{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:14px 0 10px}
.rk-thanh select,.rk-thanh input{min-height:36px;border-radius:10px;border:1px solid var(--line);background:var(--card2);color:var(--ink);padding:0 10px;font:600 13px/1 inherit;font-family:inherit}
.rk-thanh input{width:110px}.rk-thanh label{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--ink2);font-weight:600}
.rk-seg{display:inline-flex;gap:3px;background:var(--card2);border:1px solid var(--line);border-radius:11px;padding:3px}
.rk-seg button{min-height:30px;padding:0 12px;border:0;border-radius:8px;background:none;color:var(--ink2);font:700 13px/1 inherit;font-family:inherit;cursor:pointer}
.rk-seg button[aria-pressed=true]{background:color-mix(in srgb,var(--series) 18%,transparent);color:var(--ink)}
.rk-tt{font-size:13px;color:var(--ink2);margin:0 0 8px;min-height:20px;font-variant-numeric:tabular-nums}.rk-tt b{color:var(--ink)}
.rk-khung{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}
#rk-cv{display:block;width:100%;height:calc(100vh - 330px);min-height:380px;cursor:grab;touch-action:none}
.rk-ghi{margin:12px 0 0;color:var(--ink2);font-size:12.5px;line-height:1.55}
"""

JS = r"""
(()=>{const $=s=>document.querySelector(s),C=$('#rk-cv');if(!C)return;const X=C.getContext('2d');
const ST={ma:'',tf:'M15',kieu:'renko',o:'',dao:3};try{Object.assign(ST,JSON.parse(localStorage.getItem('so-rk2')||'{}'))}catch(e){}
const U=new URLSearchParams(location.search);if(U.get('ma'))ST.ma=U.get('ma');
const luu=()=>{try{localStorage.setItem('so-rk2',JSON.stringify(ST))}catch(e){}};
const css=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let D=null,dg=2,B=0,COT=[],lui=0,keo=null,lan=0;
const fp=v=>Number(v).toLocaleString('vi-VN',{minimumFractionDigits:dg,maximumFractionDigits:dg});
const soLe=cs=>{let m=0;for(const c of cs.slice(-60))for(const v of c.slice(1,5)){const s=String(v),i=s.indexOf('.');if(i>=0)m=Math.max(m,s.length-i-1)}return Math.min(m,5)};
const gio=t=>new Date(t*1000).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
// Renko: gạch [đáy, đỉnh, chiều, giờ]; đổi chiều khi giá đóng đi ngược đủ 2 ô tính từ mép gạch cuối
function renko(cs,b){const ra=[];let moc=Math.round(cs[0][4]/b)*b,ch=0;
 for(const c of cs){const g=c[4];for(;;){if(ch>=0&&g>=moc+b){ra.push([moc,moc+b,1,c[0]]);moc+=b;ch=1}else if(ch<=0&&g<=moc-b){ra.push([moc-b,moc,-1,c[0]]);moc-=b;ch=-1}
   else if(ch>0&&g<=moc-2*b){moc-=b;ra.push([moc-b,moc,-1,c[0]]);moc-=b;ch=-1}else if(ch<0&&g>=moc+2*b){moc+=b;ra.push([moc,moc+b,1,c[0]]);moc+=b;ch=1}else break}}return ra}
// Điểm & Hình: cột [đáy, đỉnh, chiều (1 = X, -1 = O), giờ bắt đầu]; đổi cột khi giá đi ngược đủ `dao` ô
function diemHinh(cs,b,dao){const ra=[];let col=null;const san=g=>Math.floor(g/b+1e-9)*b,tran=g=>Math.ceil(g/b-1e-9)*b;   // chỉ tính ô giá đã đi trọn
 for(const c of cs){const g=c[4];if(!col){col=[san(g),san(g)+b,1,c[0]];ra.push(col);continue}
  if(col[2]>0){if(g>=col[1]+b)col[1]=san(g);else if(g<=col[1]-(dao+1)*b){col=[tran(g),col[1]-b,-1,c[0]];ra.push(col)}}      // cột O bắt đầu thấp hơn đỉnh cột X một ô
  else{if(g<=col[0]-b)col[0]=tran(g);else if(g>=col[0]+(dao+1)*b){col=[col[0]+b,san(g),1,c[0]];ra.push(col)}}}return ra}
function tinh(){if(!D)return;const cs=D.candles,atr=(()=>{const a=D.atr14||[];for(let i=a.length-1;i>=0;i--)if(a[i]!=null)return a[i];return null})();
 const tay=parseFloat(String(ST.o).replace(',','.'));B=tay>0?tay:(atr||((cs[cs.length-1][4])*.001));const buoc=Math.pow(10,-dg);B=Math.max(buoc,Math.round(B/buoc)*buoc);
 COT=ST.kieu==='renko'?renko(cs,B):diemHinh(cs,B,Math.max(1,Math.min(5,+ST.dao||3)));
 const c=cs[cs.length-1],k=COT[COT.length-1];
 $('#rk-tt').innerHTML=`<b>${esc(D.ma||ST.ma||'XAUUSD')}</b> · ${ST.tf} · cỡ ô <b>${fp(B)}</b>${tay>0?'':' (ATR14)'} · ${COT.length} ${ST.kieu==='renko'?'viên gạch':'cột'} từ ${cs.length} nến · giá đóng gần nhất <b>${fp(c[4])}</b>`
  +(k?` · ${ST.kieu==='renko'?'gạch':'cột'} cuối ${k[2]>0?'<b style="color:var(--gain)">tăng</b>':'<b style="color:var(--loss)">giảm</b>'} từ ${gio(k[3])}`:'');ve()}
function ve(){const d=window.devicePixelRatio||1,W=C.clientWidth,H=C.clientHeight;if(C.width!==Math.round(W*d)||C.height!==Math.round(H*d)){C.width=Math.round(W*d);C.height=Math.round(H*d)}
 X.setTransform(d,0,0,d,0,0);X.fillStyle=css('--card')||'#111';X.fillRect(0,0,W,H);if(!COT.length){X.fillStyle=css('--ink2')||'#999';X.font='13px sans-serif';X.fillText('Chưa đủ dữ liệu để dựng biểu đồ.',16,28);return}
 const pw=W-74,ph=H-26,cw=ST.kieu==='renko'?12:16,so=Math.max(5,Math.floor(pw/cw));lui=Math.max(0,Math.min(lui,Math.max(0,COT.length-so)));
 const b1=COT.length-lui,b0=Math.max(0,b1-so),xem=COT.slice(b0,b1);let lo=Infinity,hi=-Infinity;for(const k of xem){lo=Math.min(lo,k[0]);hi=Math.max(hi,k[1])}lo-=B;hi+=B;
 const y=g=>4+(hi-g)/(hi-lo)*(ph-8),len=css('--gain')||'#17935b',xuong=css('--loss')||'#e5532d',muc=css('--ink2')||'#999',vien=css('--line')||'#333';
 X.font='11px Tahoma,"Segoe UI",Arial,sans-serif';X.textBaseline='middle';X.strokeStyle=vien;X.lineWidth=1;
 const nb=Math.max(1,Math.ceil((hi-lo)/B/12));for(let g=Math.ceil(lo/B)*B,i=0;g<=hi;g+=B,i++){if(i%nb)continue;const Y=Math.round(y(g))+.5;X.globalAlpha=.35;X.beginPath();X.moveTo(0,Y);X.lineTo(pw,Y);X.stroke();X.globalAlpha=1;X.fillStyle=muc;X.fillText(fp(g),pw+6,Y)}
 xem.forEach((k,i)=>{const x=pw-(xem.length-i)*cw,mau=k[2]>0?len:xuong;
  if(ST.kieu==='renko'){X.fillStyle=mau;const ya=y(k[1]),yb=y(k[0]);X.fillRect(x+1,ya,cw-2,Math.max(1,yb-ya-1))}
  else{X.strokeStyle=mau;X.lineWidth=1.6;const h1=Math.abs(y(k[0])-y(k[0]+B));for(let g=k[0];g<k[1]-B/2;g+=B){const ya=y(g+B),m=Math.min(cw,h1)/2-2,cx=x+cw/2,cy=ya+h1/2;X.beginPath();
    if(k[2]>0){X.moveTo(cx-m,cy-m);X.lineTo(cx+m,cy+m);X.moveTo(cx+m,cy-m);X.lineTo(cx-m,cy+m)}else X.arc(cx,cy,Math.max(1.5,m),0,7);X.stroke()}}});
 const c=D.candles[D.candles.length-1][4],Yc=Math.round(y(c))+.5;if(Yc>0&&Yc<ph){X.setLineDash([4,3]);X.strokeStyle=muc;X.lineWidth=1;X.beginPath();X.moveTo(0,Yc);X.lineTo(pw,Yc);X.stroke();X.setLineDash([]);
  const t=fp(c),tw=X.measureText(t).width+10;X.fillStyle=css('--ink')||'#eee';X.fillRect(pw+2,Yc-9,tw,18);X.fillStyle=css('--card')||'#111';X.fillText(t,pw+7,Yc)}
 X.fillStyle=muc;X.textBaseline='alphabetic';const moc=Math.max(1,Math.floor(xem.length/6));xem.forEach((k,i)=>{if(i%moc===0)X.fillText(gio(k[3]),Math.max(2,pw-(xem.length-i)*cw),H-8)})}
async function tai(){const n=++lan,ma=ST.ma,tf=ST.tf;
 try{const r=await fetch('/api/gia?tf='+tf+'&n=1500'+(ma?'&ma='+encodeURIComponent(ma):''),{cache:'no-store'});const t=await r.text();if(!r.ok)throw new Error(t);const j=JSON.parse(t);
  if(n!==lan)return;if(!j.candles||j.candles.length<20)throw new Error('chưa đủ nến');D=j;dg=j.so_le!=null?j.so_le:soLe(j.candles);tinh()}
 catch(e){if(n===lan){COT=[];$('#rk-tt').textContent='Chưa tải được: '+e.message;ve()}}}
document.querySelectorAll('#rk-kieu button').forEach(b=>{b.setAttribute('aria-pressed',String(b.dataset.v===ST.kieu));b.addEventListener('click',()=>{ST.kieu=b.dataset.v;luu();lui=0;
 document.querySelectorAll('#rk-kieu button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));$('#rk-dao-o').hidden=ST.kieu!=='pf';tinh()})});
$('#rk-dao-o').hidden=ST.kieu!=='pf';
const TF=$('#rk-tf');TF.value=ST.tf;TF.addEventListener('change',()=>{ST.tf=TF.value;luu();lui=0;tai()});
const O=$('#rk-o');O.value=ST.o;O.addEventListener('input',()=>{ST.o=O.value.trim();luu();lui=0;tinh()});
const DA=$('#rk-dao');DA.value=ST.dao;DA.addEventListener('change',()=>{ST.dao=+DA.value;luu();lui=0;tinh()});
const MA=$('#rk-ma');fetch('/api/ma',{cache:'no-store'}).then(r=>r.json()).then(j=>{if(!j.san_sang||!j.ds.length)return;
 MA.innerHTML=j.ds.map(s=>`<option value="${s.la_vang?'':esc(s.ma)}">${esc(s.ma)} · ${esc(s.ten)}</option>`).join('');MA.value=[...MA.options].some(o=>o.value===ST.ma)?ST.ma:''}).catch(()=>{});
MA.addEventListener('change',()=>{ST.ma=MA.value;luu();lui=0;tai()});
C.addEventListener('pointerdown',e=>{keo={x:e.clientX,l:lui};C.style.cursor='grabbing';try{C.setPointerCapture(e.pointerId)}catch(_){}});
C.addEventListener('pointermove',e=>{if(!keo)return;lui=keo.l+Math.round((e.clientX-keo.x)/(ST.kieu==='renko'?12:16));ve()});
for(const ev of['pointerup','pointercancel'])C.addEventListener(ev,()=>{keo=null;C.style.cursor='grab'});
C.addEventListener('wheel',e=>{e.preventDefault();lui+=e.deltaY>0?-4:4;ve()},{passive:false});C.addEventListener('dblclick',()=>{lui=0;ve()});
addEventListener('resize',ve);new MutationObserver(ve).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
setInterval(()=>{if(document.visibilityState==='visible'&&!keo)tai()},15000);window.RK={renko,diemHinh,get COT(){return COT},get B(){return B}};tai()})();
"""


def trang_renko(ten: str) -> str:
    tfs = ''.join(f'<option>{t}</option>' for t in ('M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'))
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Renko và Điểm &amp; Hình · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'renko', '<button id="theme" type="button">Nền tối</button>') + '<main class="rong">',
        '<div class="rk-top"><h1>Renko và Điểm &amp; Hình</h1><p>Hai kiểu biểu đồ chỉ theo giá, bỏ thời gian: giá phải đi đủ một ô mới có gạch hay dấu mới, '
        'nên nhiễu nhỏ biến mất và xu hướng, vùng đảo chiều hiện rõ hơn. Tính trên giá đóng của nến đã đóng trong MT5 của bạn.</p></div>',
        '<div class="rk-thanh"><select id="rk-ma" aria-label="Mã"><option value="">XAUUSD</option></select>'
        f'<select id="rk-tf" aria-label="Khung thời gian của nến nguồn">{tfs}</select>'
        '<div class="rk-seg" id="rk-kieu" role="group" aria-label="Kiểu biểu đồ"><button type="button" data-v="renko">Renko</button>'
        '<button type="button" data-v="pf">Điểm &amp; Hình</button></div>'
        '<label>Cỡ ô <input id="rk-o" inputmode="decimal" autocomplete="off" placeholder="ATR14" aria-label="Cỡ ô theo giá, để trống là ATR14"></label>'
        '<label id="rk-dao-o">Số ô đảo chiều <select id="rk-dao"><option>1</option><option>2</option><option selected>3</option><option>4</option><option>5</option></select></label></div>',
        '<p class="rk-tt" id="rk-tt" aria-live="polite">Đang tải nến…</p>',
        '<div class="rk-khung"><canvas id="rk-cv" role="img" aria-label="Biểu đồ Renko hoặc Điểm và Hình"></canvas></div>',
        '<p class="rk-ghi">Kéo ngang hoặc lăn chuột để xem phần cũ hơn, bấm đúp để về mới nhất. Cỡ ô để trống thì lấy ATR14 của khung đang chọn. '
        'Renko đổi chiều khi giá đóng đi ngược đủ hai ô; Điểm &amp; Hình đổi cột khi đi ngược đủ số ô đảo chiều. Giờ ghi dưới mỗi cột là lúc cột đó bắt đầu. '
        'Đây là cách vẽ lại giá đã qua, không phải tín hiệu vào lệnh.</p>',
        '<footer>' + escape(trang.mien_tru()) + f'</footer></main><script>{trang.JS}</script><script>{JS}</script></body></html>'])
