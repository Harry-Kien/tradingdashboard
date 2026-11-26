"""Phát lại nến (Bar Replay) có giao dịch thử, cho trang Biểu đồ (chủ dự án yêu cầu ngày 26/11/2026).

Bấm "Phát lại", chọn một cây nến trên biểu đồ (hoặc nhập ngày giờ, hoặc lùi nhanh 100/500 nến), rồi cho nến chạy từng cây: tiến, lùi, tự chạy 1–10
nến mỗi giây. Phần bên phải nến đang phát bị giấu hẳn: biểu đồ chỉ nhận nến tới đó, các lớp phân tích của hệ thống (tính trên giá hiện tại) tắt
như chế độ Biểu đồ trống, giá Bid/Ask và pivot hiện tại không vẽ, luồng giá trực tiếp và vòng tải lại tạm dừng. Chỉ báo bạn tự bật vẫn tính,
nhưng chỉ trên nến đã phát (không nhìn trước).

Giao dịch thử: Mua hoặc Bán ở giá đóng của nến đang phát; dừng lỗ = hệ số × ATR14, chốt lời = số R. Mỗi nến mới, nếu chạm cả dừng lỗ và chốt
lời trong cùng một nến thì tính dừng lỗ trước (cách tính thận trọng). Chưa trừ spread và phí. Kết quả từng phiên luyện lưu trong trình duyệt.
Phím khi đang phát: Shift+→ tiến, Shift+← lùi, Space chạy/dừng, Shift+B mua, Shift+S bán, Shift+C đóng lệnh, Esc thoát.

Cần móc window.BDPL của bieu_do.py (đọc/ghi D, chặn load, sgAp, sgMo, hisGhep, ptTai khi BDPL.chan). Đặt window.PHAT_LAI để menu chuột phải
không kiểm cảnh báo giá trên nến cũ. Chỉ chạy trong trình duyệt; không gọi máy chủ, không đặt lệnh."""

CSS = r"""
.pl-thanh{position:absolute;z-index:30;left:50%;transform:translateX(-50%);top:8px;max-width:calc(100% - 24px);display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;
padding:6px 8px;width:max-content;max-width:min(860px,calc(100% - 24px));box-sizing:border-box;background:var(--card);border:1px solid var(--series);border-radius:12px;box-shadow:0 10px 28px rgba(0,0,0,.35);font-size:12.5px}
.pl-thanh[hidden]{display:none}.pl-thanh button{min-height:28px;padding:0 9px;font-size:12.5px;width:auto;flex:0 0 auto;margin:0}.pl-thanh select,.pl-thanh input{min-height:28px;font-size:12.5px}
.pl-thanh input[type=number]{width:54px;padding:0 6px}.pl-thanh input[type=datetime-local]{padding:0 6px}
.pl-thanh .tt{color:var(--ink2);font-variant-numeric:tabular-nums}.pl-thanh .tt b{color:var(--ink)}.pl-thanh .sep{width:1px;align-self:stretch;background:var(--line)}
.pl-thanh .mua{color:#26a69a;border-color:#26a69a}.pl-thanh .ban{color:#ef5350;border-color:#ef5350}.pl-thanh .goi{color:var(--mute);font-size:11.5px;flex-basis:100%}.pl-thanh.ngoai{position:static;transform:none;width:auto;max-width:100%;margin:8px 0;box-shadow:none}.pl-thanh .i{cursor:help;color:var(--mute);border:1px solid var(--line);border-radius:50%;width:18px;height:18px;display:inline-grid;place-items:center;font-size:11px}
"""

JS = r"""
(()=>{const BP=window.BDPL;if(!BP||!window.LightweightCharts||!window.CBCN)return;const BD=()=>window.BDCB&&window.BDCB(),LWC=window.LightweightCharts;
const st=document.querySelector('.stage'),t2=document.querySelector('.tools.t2');if(!st||!t2)return;
let CH={sl:1.5,tp:2,toc:2,so:[]};try{CH={...CH,...JSON.parse(localStorage.getItem('so-phat-lai')||'{}')}}catch(e){}
const luuCH=()=>{try{localStorage.setItem('so-phat-lai',JSON.stringify(CH))}catch(e){}};
const PL={on:0,chon:0,F:null,s0:0,k:0,kMax:0,hen:0,trong:false,lenh:null,ds:[],dau:null,duong:[]};
const gio=t=>new Date(t*1000).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
const r2=v=>(v>=0?'+':'')+v.toFixed(2)+'R';
// ---------------------------------------------------------------- thanh điều khiển
const TH=document.createElement('div');TH.className='pl-thanh';TH.hidden=true;TH.setAttribute('role','toolbar');TH.setAttribute('aria-label','Phát lại nến');st.appendChild(TH);
function choThanh(){const hep=matchMedia('(max-width:640px)').matches&&!document.querySelector('.max .stage, .stage:fullscreen');TH.classList.toggle('ngoai',hep);   // màn hình hẹp: thanh nằm dưới biểu đồ, không che nến
 if(hep&&TH.parentNode===st)st.after(TH);else if(!hep&&TH.parentNode!==st)st.appendChild(TH)}
function veThanh(){choThanh();if(PL.chon){TH.innerHTML='<b>Phát lại nến:</b> bấm vào một cây nến trên biểu đồ để bắt đầu từ đó, hoặc '
  +'<button type="button" class="ghost" data-lui="100">Lùi 100 nến</button><button type="button" class="ghost" data-lui="500">Lùi 500 nến</button>'
  +'<input type="datetime-local" data-ngay aria-label="Ngày giờ bắt đầu"><button type="button" class="ghost" data-di>Đi tới</button><button type="button" class="ghost" data-thoi>Thôi</button>'
  +(CH.so.length?`<span class="goi">Phiên luyện gần nhất: ${CH.so[0].so} lệnh, thắng ${CH.so[0].thang}, tổng ${r2(CH.so[0].tong_r)} (${esc(CH.so[0].tf)}, ${gio(CH.so[0].tu)}).</span>`:'');return}
 const F=PL.F,c=F.candles[PL.k],l=PL.lenh,ds=PL.ds,th=ds.filter(x=>x.r>0).length,tong=ds.reduce((a,x)=>a+x.r,0);
 TH.innerHTML=`<button type="button" class="ghost" data-lui1 title="Lùi 1 nến (Shift+←)" ${PL.k<=PL.s0+30||l?'disabled':''}>◀</button>`
  +`<button type="button" class="go" data-choi title="Chạy hoặc dừng (Space)">${PL.hen?'Dừng':'Chạy'}</button>`
  +`<button type="button" class="ghost" data-tien title="Tiến 1 nến (Shift+→)">▶</button>`
  +`<select data-toc aria-label="Tốc độ">${[1,2,5,10].map(v=>`<option value="${v}"${v===CH.toc?' selected':''}>${v} nến/giây</option>`).join('')}</select><span class="sep"></span>`
  +(l?`<span class="tt">${l.len?'MUA':'BÁN'} ${fpx(l.vao)} · SL ${fpx(l.sl)} · TP ${fpx(l.tp)} · <b>${r2(((c[4]-l.vao)*(l.len?1:-1))/l.rui)}</b></span><button type="button" class="ghost" data-dong>Đóng lệnh</button>`
   :`<button type="button" class="ghost mua" data-mua title="Shift+B">Mua</button><button type="button" class="ghost ban" data-ban title="Shift+S">Bán</button>`
    +`<label class="tt">SL <input type="number" data-sl min="0.2" step="0.1" value="${CH.sl}"> ATR</label><label class="tt">TP <input type="number" data-tp min="0.5" step="0.5" value="${CH.tp}"> R</label>`)
  +`<span class="sep"></span><span class="tt">${gio(c[0])} · còn ${(PL.kMax-PL.k).toLocaleString('vi-VN')} nến · <b>${ds.length}</b> lệnh, thắng ${th}, tổng <b>${r2(tong)}</b></span>`
  +`<button type="button" class="ghost" data-chon>Chọn lại</button><button type="button" class="ghost" data-thoat title="Esc">Thoát</button>`
  +`<span class="i" tabindex="0" title="Giá vào là giá đóng của nến đang phát, chưa trừ spread và phí. Nến chạm cả SL và TP thì tính SL trước. Các ô bên phải trang vẫn là số hiện tại. Phím: Shift+→ tiến, Shift+← lùi, Space chạy/dừng, Shift+B mua, Shift+S bán, Shift+C đóng lệnh, Esc thoát.">i</span>`}
const fpx=v=>{const B=BD(),d=B&&B.D&&B.D.so_le!=null?B.D.so_le:2;return(+v).toFixed(d)};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');
// ---------------------------------------------------------------- cắt dữ liệu tới nến đang phát
function cat(){const F=PL.F,a=PL.s0,b=PL.k+1,D2={...F,candles:F.candles.slice(a,b),live:-1,dang_chay:null,ask:null,bid:null,pivot:null,lenh:[],vung:[],tin:[]};
 for(const n of BP.IND())if(Array.isArray(F[n]))D2[n]=F[n].slice(a,b);
 delete D2.ichi_chikou;return D2}                                     // Chikou là giá đóng của 26 nến SAU: bỏ hẳn khi phát lại
function ve(theo){const B=BD();BP.D=cat();BP.ve();const c=B&&B.LW&&B.LW.chart;if(c&&theo){const ts=c.timeScale(),r=ts.getVisibleLogicalRange(),n=PL.k-PL.s0;
  if(!r||r.to<n-1||r.to>n+12){const w=r?Math.max(40,Math.min(400,r.to-r.from)):120;ts.setVisibleLogicalRange({from:n+6-w,to:n+6})}}
 veLenh();veThanh()}
function atr(){const F=PL.F,a=Math.max(0,PL.k-300),cs=F.candles.slice(a,PL.k+1),x=CBCN._tinh.atr(cs.map(r=>r[2]),cs.map(r=>r[3]),cs.map(r=>r[4]),14);return x[x.length-1]}
// ---------------------------------------------------------------- giao dịch thử
function veLenh(){const B=BD();if(!B||!B.LW||!B.LW.nen)return;const s=B.LW.nen;for(const d of PL.duong)try{s.removePriceLine(d)}catch(e){}PL.duong=[];
 const l=PL.lenh;if(l)for(const[g,m,t]of[[l.vao,'#9e9e9e','Vào thử'],[l.sl,'#ef5350','SL thử'],[l.tp,'#26a69a','TP thử']])PL.duong.push(s.createPriceLine({price:g,color:m,lineWidth:1,lineStyle:2,axisLabelVisible:true,title:t}));
 try{if(!PL.dau||PL.dauS!==s){PL.dau=LWC.createSeriesMarkers(s,[]);PL.dauS=s}
  const mk=[];for(const x of PL.ds.concat(l?[l]:[])){if(x.tv>=PL.F.candles[PL.s0][0]&&x.tv<=PL.F.candles[PL.k][0])mk.push({time:x.tv,position:x.len?'belowBar':'aboveBar',color:x.len?'#26a69a':'#ef5350',shape:x.len?'arrowUp':'arrowDown',text:x.len?'Mua':'Bán'});
   if(x.tr!=null&&x.tr<=PL.F.candles[PL.k][0])mk.push({time:x.tr,position:'inBar',color:x.r>0?'#26a69a':'#ef5350',shape:'circle',text:r2(x.r)})}
  PL.dau.setMarkers(mk.sort((p,q)=>p.time-q.time))}catch(e){}}
function vao(len){if(!PL.on||PL.lenh)return;const c=PL.F.candles[PL.k],a=atr();if(!(a>0))return;const rui=CH.sl*a,vg=c[4];
 PL.lenh={len,vao:vg,rui,sl:len?vg-rui:vg+rui,tp:len?vg+CH.tp*rui:vg-CH.tp*rui,tv:c[0]};ve(0)}
function dong(gia,t,ly){const l=PL.lenh;if(!l)return;l.ra=gia;l.tr=t;l.ly=ly;l.r=((gia-l.vao)*(l.len?1:-1))/l.rui;PL.ds.push(l);PL.lenh=null}
function kiem(){const l=PL.lenh;if(!l)return;const c=PL.F.candles[PL.k];
 const chamSL=l.len?c[3]<=l.sl:c[2]>=l.sl,chamTP=l.len?c[2]>=l.tp:c[3]<=l.tp;if(chamSL)dong(l.sl,c[0],'SL');else if(chamTP)dong(l.tp,c[0],'TP')}
// ---------------------------------------------------------------- chạy, tiến, lùi
function tien(){if(PL.k>=PL.kMax){dung();alert('Đã tới nến mới nhất. Bấm Thoát để về giá trực tiếp.');return}PL.k++;kiem();ve(1)}
function lui(){if(PL.lenh||PL.k<=PL.s0+30)return;PL.k--;ve(1)}
function dung(){if(PL.hen){clearInterval(PL.hen);PL.hen=0}veThanh()}
function choi(){if(PL.hen){dung();return}PL.hen=setInterval(tien,1000/CH.toc);veThanh()}
// ---------------------------------------------------------------- vào, ra chế độ phát lại
function batDau(i){const B=BD();if(!B||!B.D)return;const F=PL.on?PL.F:B.D,n=F.candles.length,kMax=F.live!=null&&F.live>=0?F.live-1:n-1;
 i=Math.max(60,Math.min(kMax-1,i));if(!PL.on){PL.F=F;PL.trong=BP.TRONG;window.PHAT_LAI=true;BP.chan=true;BP.dong();BP.trong(true);PL.on=1;PL.ds=[];PL.lenh=null}
 PL.chon=0;dung();PL.kMax=kMax;PL.k=i;PL.s0=Math.max(0,i-2500);ve(1);const c=BD().LW.chart,m=PL.k-PL.s0;c.timeScale().setVisibleLogicalRange({from:m-110,to:m+12});nut.setAttribute('aria-pressed','true')}
function chon(){if(PL.on){dung();if(PL.lenh){const c=PL.F.candles[PL.k];dong(c[4],c[0],'Chọn lại')}veLenh()}PL.chon=1;TH.hidden=false;veThanh()}
function thoat(tai){dung();const B=BD();if(PL.on){if(PL.lenh){const c=PL.F.candles[PL.k];dong(c[4],c[0],'Thoát')}
  if(PL.ds.length){const tong=PL.ds.reduce((a,x)=>a+x.r,0);CH.so=[{luc:Date.now(),tf:(PL.F.tf||''),ma:PL.F.khac_vang?PL.F.ma:'XAUUSD',tu:PL.ds[0].tv,so:PL.ds.length,
    thang:PL.ds.filter(x=>x.r>0).length,tong_r:+tong.toFixed(2)},...CH.so].slice(0,50);luuCH()}
  try{if(B&&B.LW&&B.LW.nen)for(const d of PL.duong)B.LW.nen.removePriceLine(d)}catch(e){}PL.duong=[];try{if(PL.dau)PL.dau.detach()}catch(e){}PL.dau=null;
  BP.chan=false;window.PHAT_LAI=false;BP.D=PL.F;PL.on=0;PL.F=null;BP.trong(PL.trong);BP.ve();if(tai)BP.tai(1)}
 PL.chon=0;TH.hidden=true;nut.setAttribute('aria-pressed','false')}
// ---------------------------------------------------------------- sự kiện
TH.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const B=BD();
 if(b.dataset.lui){const n=B.D.candles.length,kMax=B.D.live>=0?B.D.live-1:n-1;batDau(kMax-(+b.dataset.lui))}
 else if(b.hasAttribute('data-di')){const v=TH.querySelector('[data-ngay]').value;if(!v)return;const t=Date.parse(v)/1000,cs=(PL.F||B.D).candles;let a=0,z=cs.length-1;
  while(a<z){const m=(a+z+1)>>1;if(cs[m][0]<=t)a=m;else z=m-1}batDau(a)}
 else if(b.hasAttribute('data-thoi'))thoat(false);else if(b.hasAttribute('data-thoat'))thoat(true);else if(b.hasAttribute('data-chon'))chon();
 else if(b.hasAttribute('data-choi'))choi();else if(b.hasAttribute('data-tien'))tien();else if(b.hasAttribute('data-lui1'))lui();
 else if(b.hasAttribute('data-mua'))vao(1);else if(b.hasAttribute('data-ban'))vao(0);else if(b.hasAttribute('data-dong')){const c=PL.F.candles[PL.k];dong(c[4],c[0],'Tay');ve(0)}});
TH.addEventListener('change',e=>{const t=e.target;if(t.dataset.toc!=null&&t.matches('[data-toc]')){CH.toc=+t.value;luuCH();if(PL.hen){dung();choi()}}
 else if(t.matches('[data-sl]')){const v=+t.value;if(v>=.2)CH.sl=v;luuCH()}else if(t.matches('[data-tp]')){const v=+t.value;if(v>=.5)CH.tp=v;luuCH()}});
let gan=null;const ganClick=()=>{const B=BD();if(!B||!B.LW||gan===B.LW.chart)return;gan=B.LW.chart;
 gan.subscribeClick(p=>{if(!PL.chon||!p||p.time==null)return;const cs=(PL.F||BD().D).candles;let a=0,z=cs.length-1;while(a<z){const m=(a+z+1)>>1;if(cs[m][0]<=p.time)a=m;else z=m-1}batDau(a)})};
CBCN.moc.push(()=>ganClick());
document.addEventListener('click',e=>{if((PL.on||PL.chon)&&e.target.closest&&e.target.closest('.seg.tf button'))thoat(false)},true);   // đổi khung: thoát phát lại trước, trang tự tải khung mới
addEventListener('keydown',e=>{if(!PL.on&&!PL.chon)return;if(/^(INPUT|TEXTAREA|SELECT)$/.test((e.target&&e.target.tagName)||'')&&e.key!=='Escape')return;let ok=1;
 if(e.key==='Escape')thoat(PL.on?true:false);else if(!PL.on)ok=0;
 else if(e.shiftKey&&e.key==='ArrowRight')tien();else if(e.shiftKey&&e.key==='ArrowLeft')lui();else if(e.key===' '&&!e.ctrlKey)choi();
 else if(e.shiftKey&&(e.key==='B'||e.key==='b'))vao(1);else if(e.shiftKey&&(e.key==='S'||e.key==='s'))vao(0);
 else if(e.shiftKey&&(e.key==='C'||e.key==='c')){if(PL.lenh){const c=PL.F.candles[PL.k];dong(c[4],c[0],'Tay');ve(0)}}else ok=0;
 if(ok){e.preventDefault();e.stopPropagation()}},true);
document.addEventListener('visibilitychange',()=>{if(document.visibilityState!=='visible'&&PL.hen)dung()});
const nut=document.createElement('button');nut.type='button';nut.className='ghost nho';nut.textContent='Phát lại';nut.setAttribute('aria-pressed','false');
nut.title='Phát lại nến từ một thời điểm trong quá khứ và luyện vào lệnh thử (như Bar Replay của TradingView)';
nut.addEventListener('click',()=>{if(PL.on||PL.chon)thoat(PL.on?true:false);else chon()});
const sau=document.querySelector('.cbcn-them')||document.querySelector('.cbcn-mo');(sau?sau.nextElementSibling||sau:t2.lastChild).after(nut);
window.CBPL={PL,batDau,tien,lui,vao,dong,thoat,kiem,cat}})();
"""
