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
.rk-nut{min-height:36px;padding:0 12px;border-radius:10px;border:1px solid var(--line);background:var(--card2);color:var(--ink);font:600 13px/1 inherit;font-family:inherit;cursor:pointer}
.rk-nut[aria-pressed=true]{background:var(--series);color:var(--btn-ink);border-color:var(--series)}.rk-nut:focus-visible{outline:2px solid var(--series);outline-offset:1px}
.rk-tt i{display:inline-block;width:9px;height:9px;border-radius:50%;margin:0 4px 0 2px;vertical-align:0}
#rk-cv.ve{cursor:crosshair}
/* Máy tính (27/11/2026): tiêu đề và hàng nút gộp một hàng, đoạn mô tả thu vào nút "i", khung vẽ cao vừa phần còn lại của cửa sổ. */
.rk-i{display:none}
@media(min-width:981px) and (min-height:600px){
main.rong{display:grid;grid-template-columns:auto minmax(0,1fr);column-gap:18px;align-items:center;padding-top:10px;padding-bottom:24px}
main.rong>*{grid-column:1/-1}main.rong>.rk-top{grid-column:1;display:flex;align-items:center;gap:8px;position:relative}
main.rong>.rk-thanh{grid-column:2;margin:0;justify-content:flex-end;flex-wrap:nowrap;min-width:0;overflow-x:auto;scrollbar-width:none}   /* luôn một hàng: chiều cao khung vẽ tính theo một hàng */
main.rong>.rk-thanh>*{flex:none}#rk-ma{max-width:200px}
.rk-top h1{font-size:18px;white-space:nowrap}
.rk-i{display:inline-flex;align-items:center;justify-content:center;flex:none;width:22px;height:22px;border-radius:50%;border:1px solid var(--line);color:var(--ink2);font:italic 700 12px/1 Georgia,serif;cursor:pointer}
.rk-i:focus-visible{outline:2px solid var(--series);outline-offset:1px}
.rk-top p{display:none;position:absolute;left:0;top:calc(100% + 6px);z-index:8;width:min(520px,80vw);max-width:none;margin:0;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card);box-shadow:0 10px 30px rgba(0,0,0,.35)}
.rk-i:hover+p,.rk-i:focus+p{display:block}
.rk-tt{margin:8px 0}
#rk-cv{height:calc(100dvh - var(--nv-h,56px) - 112px);min-height:300px}
}
"""

JS = r"""
(()=>{const $=s=>document.querySelector(s),C=$('#rk-cv');if(!C)return;const X=C.getContext('2d');
const ST={ma:'',tf:'M15',kieu:'renko',o:'',dao:3,tb:10};try{Object.assign(ST,JSON.parse(localStorage.getItem('so-rk2')||'{}'))}catch(e){}
const U=new URLSearchParams(location.search);if(U.get('ma'))ST.ma=U.get('ma');
const luu=()=>{try{localStorage.setItem('so-rk2',JSON.stringify(ST))}catch(e){}};
const css=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let D=null,dg=2,B=0,COT=[],lui=0,keo=null,lan=0,VG=null,VEL=[],veDang=null,cheDo=0;
const cau=(s,o)=>s.replace(/%([a-z])/g,(m,k)=>o[k]==null?m:o[k]);   // câu trọn vẹn để bản tiếng Anh dịch nguyên câu, giá trị chèn sau
// đường xu hướng người dùng vẽ: mỗi đầu gắn theo giờ bắt đầu của cột (và thứ tự trong các cột cùng giờ) cùng giá, nên vẫn đúng chỗ khi có nến mới hay đổi cỡ ô
const veKhoa=()=>'so-rk-ve:'+(ST.ma||'XAU')+':'+ST.tf,veDoc=()=>{try{VEL=JSON.parse(localStorage.getItem(veKhoa())||'[]')}catch(e){VEL=[]}if(!Array.isArray(VEL))VEL=[]},veLuu=()=>{try{localStorage.setItem(veKhoa(),JSON.stringify(VEL.slice(-50)))}catch(e){}};
const neo=i=>{const j=Math.max(0,Math.min(COT.length-1,Math.round(i))),t=COT[j][3];let a=j;while(a>0&&COT[a-1][3]===t)a--;return{t,n:j-a}};
const viTriNeo=q=>{let a=-1;for(let i=0;i<COT.length;i++){if(COT[i][3]===q.t){a=i;break}if(COT[i][3]>q.t)break;a=i}if(a<0)return null;if(COT[a][3]===q.t){let b=a;while(b+1<COT.length&&COT[b+1][3]===q.t&&b-a<q.n)b++;return b}return a};
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
 const c=cs[cs.length-1],k=COT[COT.length-1],rk=ST.kieu==='renko';
 const cuoi=!k?'':rk?(k[2]>0?'Gạch cuối tăng, bắt đầu lúc %t':'Gạch cuối giảm, bắt đầu lúc %t'):(k[2]>0?'Cột cuối là cột X (tăng), bắt đầu lúc %t':'Cột cuối là cột O (giảm), bắt đầu lúc %t');
 $('#rk-tt').innerHTML=`<b>${esc(D.ma||ST.ma||'XAUUSD')}</b> · ${ST.tf} · `+cau(tay>0?'Cỡ ô: %o':'Cỡ ô: %o (ATR14)',{o:`<b>${fp(B)}</b>`})+' · '
  +cau(rk?'%n viên gạch dựng từ %c nến':'%n cột dựng từ %c nến',{n:COT.length,c:cs.length})+' · '+cau('Giá đóng gần nhất: %g',{g:`<b>${fp(c[4])}</b>`})
  +(k?' · '+`<i style="background:var(${k[2]>0?'--gain':'--loss'})"></i>`+cau(cuoi,{t:gio(k[3])}):'');ve()}
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
 VG={b0,b1,cw,pw,ph,lo,hi};const xi=i=>pw-(b1-i)*cw+cw/2;
 const tb=+ST.tb||0;if(tb>1&&COT.length>=tb){const v=COT.map(k=>ST.kieu==='renko'?(k[2]>0?k[1]:k[0]):(k[0]+k[1])/2),mau=css('--warn')||'#e0a100';let s=0,dau=1,cuoiX=null,cuoiY=null;   // đường trung bình của giá đóng từng viên gạch (giữa cột với Điểm & Hình)
  X.strokeStyle=mau;X.lineWidth=1.8;X.beginPath();for(let i=0;i<v.length;i++){s+=v[i];if(i>=tb)s-=v[i-tb];if(i<tb-1||i<b0-1||i>=b1)continue;const xx=xi(i),yy=y(s/tb);if(dau){X.moveTo(xx,yy);dau=0}else X.lineTo(xx,yy);cuoiX=xx;cuoiY=yy}X.stroke();
  if(cuoiX!=null){X.fillStyle=mau;X.textBaseline='middle';X.fillText('TB'+tb,Math.min(cuoiX+6,pw-30),cuoiY-10)}}
 const mauVe=css('--series')||'#2f6fed';X.lineCap='round';for(const L of veDang?[...VEL,veDang]:VEL){const ia=L.ia!=null?L.ia:viTriNeo(L.a),ib=L.ib!=null?L.ib:viTriNeo(L.b);if(ia==null||ib==null)continue;
  const x1=xi(ia),y1=y(L.a.p),x2=xi(ib),y2=y(L.b.p);X.strokeStyle=mauVe;X.lineWidth=2;X.beginPath();X.moveTo(x1,y1);X.lineTo(x2,y2);X.stroke();
  if(x2!==x1){const k=(y2-y1)/(x2-x1),xe=x2>x1?pw:0;X.setLineDash([5,4]);X.lineWidth=1;X.beginPath();X.moveTo(x2,y2);X.lineTo(xe,y2+k*(xe-x2));X.stroke();X.setLineDash([])}
  X.fillStyle=mauVe;for(const[xx,yy]of[[x1,y1],[x2,y2]]){X.beginPath();X.arc(xx,yy,3,0,7);X.fill()}}X.lineCap='butt';X.textBaseline='middle';
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
const TF=$('#rk-tf');TF.value=ST.tf;TF.addEventListener('change',()=>{ST.tf=TF.value;luu();lui=0;veDoc();tai()});
const TB=$('#rk-tb');TB.value=String(ST.tb||0);TB.addEventListener('change',()=>{ST.tb=+TB.value;luu();ve()});veDoc();
const O=$('#rk-o');O.value=ST.o;O.addEventListener('input',()=>{ST.o=O.value.trim();luu();lui=0;tinh()});
const DA=$('#rk-dao');DA.value=ST.dao;DA.addEventListener('change',()=>{ST.dao=+DA.value;luu();lui=0;tinh()});
const MA=$('#rk-ma');fetch('/api/ma',{cache:'no-store'}).then(r=>r.json()).then(j=>{if(!j.san_sang||!j.ds.length)return;
 MA.innerHTML=j.ds.map(s=>`<option value="${s.la_vang?'':esc(s.ma)}">${esc(s.ma)} · ${esc(s.ten)}</option>`).join('');MA.value=[...MA.options].some(o=>o.value===ST.ma)?ST.ma:''}).catch(()=>{});
MA.addEventListener('change',()=>{ST.ma=MA.value;luu();lui=0;veDoc();tai()});
const toaDo=e=>{if(!VG)return null;const r=C.getBoundingClientRect(),x=e.clientX-r.left,yy=e.clientY-r.top;if(x>VG.pw||x<0)return null;const i=Math.round(VG.b1-(VG.pw-x)/VG.cw-.5);if(i<0||i>=COT.length)return null;
 return{i,p:VG.hi-(yy-4)/(VG.ph-8)*(VG.hi-VG.lo)}};
const VEN=$('#rk-ve'),datVe=on=>{cheDo=on?1:0;VEN.setAttribute('aria-pressed',String(!!on));C.classList.toggle('ve',!!on);veDang=null;ve()};VEN.addEventListener('click',()=>datVe(!cheDo));
$('#rk-xoa').addEventListener('click',()=>{if(!VEL.length)return;if(confirm('Xóa tất cả đường đã vẽ trên biểu đồ Renko này?')){VEL=[];veLuu();ve()}});
addEventListener('keydown',e=>{if(/^(INPUT|TEXTAREA|SELECT)$/.test((e.target&&e.target.tagName)||''))return;if(e.key==='Escape'&&cheDo)datVe(0);else if((e.ctrlKey||e.metaKey)&&(e.key==='z'||e.key==='Z')&&VEL.length){e.preventDefault();VEL.pop();veLuu();ve()}});
C.addEventListener('pointerdown',e=>{if(cheDo){const q=toaDo(e);if(!q)return;veDang={ia:q.i,ib:q.i,a:{p:q.p},b:{p:q.p}};try{C.setPointerCapture(e.pointerId)}catch(_){}ve();return}keo={x:e.clientX,l:lui};C.style.cursor='grabbing';try{C.setPointerCapture(e.pointerId)}catch(_){}});
C.addEventListener('pointermove',e=>{if(veDang){const q=toaDo(e);if(q){veDang.ib=q.i;veDang.b={p:q.p};ve()}return}if(!keo)return;lui=keo.l+Math.round((e.clientX-keo.x)/(ST.kieu==='renko'?12:16));ve()});
for(const ev of['pointerup','pointercancel'])C.addEventListener(ev,()=>{if(veDang){const L=veDang;veDang=null;if(ev==='pointerup'&&(L.ia!==L.ib||Math.abs(L.a.p-L.b.p)>B/4)){VEL.push({a:{...neo(L.ia),p:L.a.p},b:{...neo(L.ib),p:L.b.p}});veLuu()}ve();return}
 keo=null;C.style.cursor=''});
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
        '<div class="rk-top"><h1>Renko và Điểm &amp; Hình</h1><span class="rk-i" tabindex="0" aria-label="Giới thiệu trang" aria-describedby="rk-gt">i</span><p id="rk-gt">Hai kiểu biểu đồ chỉ theo giá, bỏ thời gian: giá phải đi đủ một ô mới có gạch hay dấu mới, '
        'nên nhiễu nhỏ biến mất và xu hướng, vùng đảo chiều hiện rõ hơn. Tính trên giá đóng của nến đã đóng trong MT5 của bạn.</p></div>',
        '<div class="rk-thanh"><select id="rk-ma" aria-label="Mã"><option value="">XAUUSD</option></select>'
        f'<select id="rk-tf" aria-label="Khung thời gian của nến nguồn">{tfs}</select>'
        '<div class="rk-seg" id="rk-kieu" role="group" aria-label="Kiểu biểu đồ"><button type="button" data-v="renko">Renko</button>'
        '<button type="button" data-v="pf">Điểm &amp; Hình</button></div>'
        '<label>Cỡ ô <input id="rk-o" inputmode="decimal" autocomplete="off" placeholder="ATR14" aria-label="Cỡ ô theo giá, để trống là ATR14"></label>'
        '<label id="rk-dao-o">Số ô đảo chiều <select id="rk-dao"><option>1</option><option>2</option><option selected>3</option><option>4</option><option>5</option></select></label>'
        '<label>Trung bình <select id="rk-tb" aria-label="Đường trung bình theo số viên gạch hoặc số cột"><option value="0">Tắt</option><option>10</option><option>20</option><option>50</option></select></label>'
        '<button type="button" class="rk-nut" id="rk-ve" aria-pressed="false">Vẽ đường xu hướng</button><button type="button" class="rk-nut" id="rk-xoa">Xóa đường vẽ</button></div>',
        '<p class="rk-tt" id="rk-tt" aria-live="polite">Đang tải nến…</p>',
        '<div class="rk-khung"><canvas id="rk-cv" role="img" aria-label="Biểu đồ Renko hoặc Điểm và Hình"></canvas></div>',
        '<p class="rk-ghi">Kéo ngang hoặc lăn chuột để xem phần cũ hơn, bấm đúp để về mới nhất. Cỡ ô để trống thì lấy ATR14 của khung đang chọn. '
        'Renko đổi chiều khi giá đóng đi ngược đủ hai ô; Điểm &amp; Hình đổi cột khi đi ngược đủ số ô đảo chiều. Giờ ghi dưới mỗi cột là lúc cột đó bắt đầu. '
        'Bấm "Vẽ đường xu hướng" rồi kéo trên biểu đồ để kẻ đường (Esc để thôi, Ctrl+Z bỏ đường vừa vẽ); đường được nhớ theo mã và khung. '
        'Đường trung bình tính trên giá đóng của từng viên gạch (với Điểm &amp; Hình là giữa cột). Đây là cách vẽ lại giá đã qua, không phải tín hiệu vào lệnh.</p>',
        '<footer>' + escape(trang.mien_tru()) + f'</footer></main><script>{trang.JS}</script><script>{JS}</script></body></html>'])
