"""Bộ chọn chỉ báo kiểu TradingView cho trang Biểu đồ (chủ dự án yêu cầu ngày 26/11/2026).

Nút "Thêm chỉ báo" mở hộp chọn: ô tìm, nhóm (xu hướng, dao động, biến động), yêu thích, danh sách đang dùng với chỉnh tham số, màu, ẩn hiện;
thêm được nhiều bản cùng loại (EMA 9, EMA 21, EMA 200…); lưu mẫu cá nhân. Mọi lựa chọn lưu trong trình duyệt của người dùng (localStorage).

Các chỉ báo ở đây tính ngay trong trình duyệt trên đúng chuỗi nến biểu đồ đang vẽ (D.candles, kể cả phần nến cũ đã ghép), nên không lệch chỗ
khi ghép thêm nến cũ. Công thức theo chuẩn TradingView và khớp với phía máy chủ (gia.rsi_wilder, chi_bao_them: EMA kiểu pandas adjust=False,
RMA Wilder, Bollinger độ lệch chuẩn tổng thể, Stochastic chậm, SuperTrend); tests/test_bieu_do_chi_bao.py đối chiếu số với pandas.
Tab "Có sẵn" bật tắt các chỉ báo hệ thống tính ở máy chủ (nút chip cũ), không tính lại. Nến không có khối lượng nên chưa có VWAP, OBV, Volume.
Trang Biểu đồ cần hai móc: window.BDCB (trả LW, D, bảng màu) và gọi CBCN.ve() cuối lwDraw."""

CSS = r"""
.cbcn-mo{display:inline-flex;align-items:center;gap:6px}.cbcn-mo svg{width:16px;height:16px}
.cbcn-nen{position:fixed;inset:0;z-index:80;background:rgba(0,0,0,.45);display:grid;place-items:start center;padding:6vh 12px 12px}
.cbcn-nen[hidden]{display:none}
.cbcn{width:min(760px,100%);max-height:86vh;display:grid;grid-template-rows:auto auto auto minmax(0,1fr);background:var(--card);color:var(--ink);
border:1px solid var(--line);border-radius:14px;box-shadow:0 18px 48px rgba(0,0,0,.35);overflow:hidden}
.cbcn header{display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid var(--line)}.cbcn header b{font-size:16px;flex:1}
.cbcn .tim{padding:10px 14px 6px}.cbcn .tim input{width:100%;box-sizing:border-box;min-height:38px;padding:0 12px;font:inherit}
.cbcn .tab{display:flex;gap:6px;flex-wrap:wrap;padding:4px 14px 10px;border-bottom:1px solid var(--line)}
.cbcn .tab button{min-height:30px;font-size:12.5px;padding:0 10px}.cbcn .tab button[aria-pressed=true]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.cbcn .ds{overflow:auto;padding:6px 8px 12px}
.cbcn .h{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:4px 10px;align-items:center;padding:8px 8px;border-radius:10px}
.cbcn .h:hover{background:var(--card2)}.cbcn .h b{font-size:13.5px;font-weight:600}.cbcn .h small{grid-column:2;color:var(--mute);font-size:12px}
.cbcn .sao{background:none;border:0;cursor:pointer;font-size:17px;line-height:1;color:var(--mute);padding:2px 4px;min-height:0}.cbcn .sao[aria-pressed=true]{color:#f5b301}
.cbcn .them{min-height:30px;font-size:12.5px}
.cbcn .dg{display:grid;grid-template-columns:auto minmax(0,1fr) auto auto auto;gap:6px 8px;align-items:center;padding:8px;border:1px solid var(--line);border-radius:10px;margin:6px 4px}
.cbcn .dg input[type=color]{width:28px;height:28px;padding:0;border:0;background:none;cursor:pointer}
.cbcn .dg .ts{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:8px 12px}.cbcn .dg .ts label{display:flex;gap:6px;align-items:center;font-size:12.5px;color:var(--ink2)}
.cbcn .dg .ts input{width:72px;min-height:30px;padding:0 8px}.cbcn .dg button{min-height:30px;font-size:12.5px;padding:0 9px}.cbcn .dg.an{opacity:.55}
.cbcn .rong{color:var(--mute);font-size:13px;padding:14px}.cbcn .mau{display:flex;gap:8px;flex-wrap:wrap;align-items:center;padding:8px 6px}
.cbcn .mau input{min-height:32px;padding:0 10px;flex:1 1 180px}.cbcn .nhom{font-size:11.5px;color:var(--mute);padding:10px 8px 2px;font-weight:600}
@media(max-width:560px){.cbcn-nen{padding:0}.cbcn{max-height:100vh;height:100%;border-radius:0}.cbcn .dg{grid-template-columns:auto minmax(0,1fr) auto auto}.cbcn .dg .xoa{grid-column:4}}
"""

JS = r"""
window.CBCN=(()=>{const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
// ---------------------------------------------------------------- phép tính (mảng cùng độ dài nến; null ở chỗ chưa đủ nến)
const N=a=>a.length,nul=n=>new Array(n).fill(null);
function ewm(x,al,minp){const o=nul(N(x));let e=null,dem=0;for(let i=0;i<N(x);i++){const v=x[i];if(v==null){if(e!==null&&dem>=minp)o[i]=null;continue}
 e=e===null?v:al*v+(1-al)*e;dem++;if(dem>=minp)o[i]=e}return o}                       // như pandas ewm(adjust=False, min_periods): mồi bằng giá trị đầu
const ema=(x,n)=>ewm(x,2/(n+1),n),rma=(x,n)=>ewm(x,1/n,n);
function roll(x,n,f){const o=nul(N(x));for(let i=n-1;i<N(x);i++){let ok=true;const w=[];for(let j=i-n+1;j<=i;j++){if(x[j]==null){ok=false;break}w.push(x[j])}if(ok)o[i]=f(w)}return o}
const sma=(x,n)=>{const o=nul(N(x));let s=0,dem=0;for(let i=0;i<N(x);i++){if(x[i]==null){s=0;dem=0;continue}s+=x[i];dem++;if(dem>n){s-=x[i-n];dem=n}if(dem===n)o[i]=s/n}return o};
const wma=(x,n)=>roll(x,n,w=>{let s=0,t=0;w.forEach((v,j)=>{s+=v*(j+1);t+=j+1});return s/t}),
 sd=(x,n)=>roll(x,n,w=>{const m=w.reduce((a,b)=>a+b,0)/n;return Math.sqrt(w.reduce((a,b)=>a+(b-m)*(b-m),0)/n)}),
 hh=(x,n)=>roll(x,n,w=>Math.max(...w)),ll=(x,n)=>roll(x,n,w=>Math.min(...w)),
 hop=(a,b,f)=>a.map((v,i)=>v==null||b[i]==null?null:f(v,b[i])),dich=(x,k)=>x.map((_,i)=>i-k>=0&&i-k<N(x)?x[i-k]:null);
function tr(H,L,C){return H.map((h,i)=>i===0?h-L[0]:Math.max(h-L[i],Math.abs(h-C[i-1]),Math.abs(L[i]-C[i-1])))}
const atr=(H,L,C,n)=>rma(tr(H,L,C),n);
function rsi(C,n){const up=nul(N(C)),dn=nul(N(C));for(let i=1;i<N(C);i++){const d=C[i]-C[i-1];up[i]=Math.max(d,0);dn[i]=Math.max(-d,0)}
 const u=rma(up,n),d=rma(dn,n);return u.map((v,i)=>v==null||d[i]==null?null:d[i]===0?100:100-100/(1+v/d[i]))}
function stoch(H,L,C,n,k,d){const a=hh(H,n),b=ll(L,n),tho=C.map((c,i)=>a[i]==null||a[i]===b[i]?null:100*(c-b[i])/(a[i]-b[i])),kk=sma(tho,k);return[kk,sma(kk,d)]}
function supertrend(H,L,C,n,m){const a=atr(H,L,C,n),o=nul(N(C)),ch=nul(N(C));let tr0=null,du0=null,c0=null;
 for(let i=0;i<N(C);i++){if(a[i]==null)continue;const g=(H[i]+L[i])/2,t=g+m*a[i],u=g-m*a[i];let t1,u1,c1;
  if(tr0===null){t1=t;u1=u;c1=1}else{t1=(t<tr0||C[i-1]>tr0)?t:tr0;u1=(u>du0||C[i-1]<du0)?u:du0;c1=c0<0?(C[i]>t1?1:-1):(C[i]<u1?-1:1)}
  tr0=t1;du0=u1;c0=c1;ch[i]=c1;o[i]=c1>0?u1:t1}return[o,ch]}
function psar(H,L,buoc,toi){const o=nul(N(H));if(N(H)<2)return o;let tang=H[1]>=H[0],sar=tang?L[0]:H[0],ep=tang?H[0]:L[0],af=buoc;
 for(let i=1;i<N(H);i++){sar=sar+af*(ep-sar);if(tang){sar=Math.min(sar,L[i-1],i>1?L[i-2]:L[i-1]);if(L[i]<sar){tang=false;sar=ep;ep=L[i];af=buoc}else if(H[i]>ep){ep=H[i];af=Math.min(af+buoc,toi)}}
  else{sar=Math.max(sar,H[i-1],i>1?H[i-2]:H[i-1]);if(H[i]>sar){tang=true;sar=ep;ep=H[i];af=buoc}else if(L[i]<ep){ep=L[i];af=Math.min(af+buoc,toi)}}o[i]=sar}return o}
function adx(H,L,C,n){const pdm=nul(N(H)),mdm=nul(N(H));for(let i=1;i<N(H);i++){const u=H[i]-H[i-1],d=L[i-1]-L[i];pdm[i]=u>d&&u>0?u:0;mdm[i]=d>u&&d>0?d:0}
 const t=rma(tr(H,L,C).map((v,i)=>i===0?null:v),n),p=rma(pdm,n),m=rma(mdm,n),pdi=hop(p,t,(a,b)=>b?100*a/b:null),mdi=hop(m,t,(a,b)=>b?100*a/b:null),
  dx=hop(pdi,mdi,(a,b)=>a+b?100*Math.abs(a-b)/(a+b):0);return[rma(dx,n),pdi,mdi]}
function cci(H,L,C,n){const tp=H.map((h,i)=>(h+L[i]+C[i])/3),m=sma(tp,n),md=roll(tp,n,w=>{const a=w.reduce((x,y)=>x+y,0)/n;return w.reduce((x,y)=>x+Math.abs(y-a),0)/n});
 return tp.map((v,i)=>m[i]==null||!md[i]?null:(v-m[i])/(.015*md[i]))}
function aroon(H,L,n){const up=nul(N(H)),dn=nul(N(H));for(let i=n;i<N(H);i++){let a=i-n,b=i-n;for(let j=i-n;j<=i;j++){if(H[j]>=H[a])a=j;if(L[j]<=L[b])b=j}
 up[i]=100*(n-(i-a))/n;dn[i]=100*(n-(i-b))/n}return[up,dn]}
// ---------------------------------------------------------------- thư viện: k → {ten, nhom, khung:'gia'|'rieng', ts:[[khóa,nhãn,mặc định,bước]], mo, tinh(H,L,C,O,p) → [[tên,mảng,kiểu?]], muc?}
// ---------------------------------------------------------------- chỉ báo cộng đồng: công thức công khai, viết lại từ mô tả gốc (không chép mã)
const tong=(x,n)=>roll(x,n,w=>w.reduce((a,b)=>a+b,0));
function linreg(x,n){return roll(x,n,w=>{let sx=0,sy=0,sxy=0,sxx=0;w.forEach((v,j)=>{sx+=j;sy+=v;sxy+=j*v;sxx+=j*j});const b=(n*sxy-sx*sy)/(n*sxx-sx*sx||1),a=(sy-b*sx)/n;return a+b*(n-1)})}
const cat=(a,b,i)=>a[i-1]!=null&&b[i-1]!=null&&a[i]!=null&&b[i]!=null&&((a[i-1]<=b[i-1]&&a[i]>b[i])||(a[i-1]>=b[i-1]&&a[i]<b[i]));   // a cắt b ở nến i (hai chiều)
function squeeze(H,L,C,n,k,kc){const m=sma(C,n),d=sd(C,n),r=sma(tr(H,L,C),n),dt=hop(hh(H,n),ll(L,n),(a,b)=>(a+b)/2),val=linreg(C.map((c,i)=>dt[i]==null||m[i]==null?null:c-(dt[i]+m[i])/2),n),
 on=C.map((_,i)=>m[i]==null||d[i]==null||r[i]==null?null:(m[i]-k*d[i]>m[i]-kc*r[i]&&m[i]+k*d[i]<m[i]+kc*r[i])?0:null);return[val,on]}
function wavetrend(H,L,C,n1,n2){const ap=H.map((h,i)=>(h+L[i]+C[i])/3),esa=ema(ap,n1),d=ema(ap.map((v,i)=>esa[i]==null?null:Math.abs(v-esa[i])),n1),
 ci=ap.map((v,i)=>esa[i]==null||!d[i]?null:(v-esa[i])/(.015*d[i])),w1=ema(ci,n2),w2=sma(w1,4),mk=[];
 for(let i=1;i<C.length;i++)if(cat(w1,w2,i)){if(w1[i]>w2[i]&&w1[i]<-53)mk.push({i,len:1});else if(w1[i]<w2[i]&&w1[i]>53)mk.push({i,len:0})}return[w1,w2,mk]}
function utbot(H,L,C,a,n){const x=atr(H,L,C,n),st=nul(C.length),mk=[];let p=0;
 for(let i=0;i<C.length;i++){if(x[i]==null){continue}const nl=a*x[i],c=C[i],c1=i?C[i-1]:c;
  const v=c>p&&c1>p?Math.max(p,c-nl):c<p&&c1<p?Math.min(p,c+nl):c>p?c-nl:c+nl;if(st[i-1]!=null){if(c1<=st[i-1]&&c>v)mk.push({i,len:1});else if(c1>=st[i-1]&&c<v)mk.push({i,len:0})}st[i]=v;p=v}return[st,mk]}
function chandelier(H,L,C,n,k){const a=atr(H,L,C,n),hc=hh(C,n),lc=ll(C,n),lo=nul(C.length),sh=nul(C.length),dir=nul(C.length),mk=[];let L0=null,S0=null,d0=1;
 for(let i=0;i<C.length;i++){if(a[i]==null||hc[i]==null)continue;let l=hc[i]-k*a[i],s2=lc[i]+k*a[i];const lp=L0??l,sp=S0??s2;
  if(i&&C[i-1]>lp)l=Math.max(l,lp);if(i&&C[i-1]<sp)s2=Math.min(s2,sp);const d=C[i]>sp?1:C[i]<lp?-1:d0;if(d!==d0&&L0!=null)mk.push({i,len:d>0?1:0});
  lo[i]=d>0?l:null;sh[i]=d<0?s2:null;L0=l;S0=s2;d0=d;dir[i]=d}return[lo,sh,mk]}
function qqe(C,n,sf,q){const r=rsi(C,n),rm=ema(r,sf),ar=rm.map((v,i)=>i&&v!=null&&rm[i-1]!=null?Math.abs(rm[i-1]-v):null),wp=n*2-1,dar=ema(ema(ar,wp),wp).map(v=>v==null?null:v*q),
 lb=nul(C.length),sb=nul(C.length),tl=nul(C.length);let tr0=1;
 for(let i=0;i<C.length;i++){if(rm[i]==null||dar[i]==null)continue;const nl=rm[i]-dar[i],ns=rm[i]+dar[i],l1=lb[i-1],s1=sb[i-1],r1=rm[i-1];
  lb[i]=l1!=null&&r1>l1&&rm[i]>l1?Math.max(l1,nl):nl;sb[i]=s1!=null&&r1<s1&&rm[i]<s1?Math.min(s1,ns):ns;
  if(s1!=null&&((r1<=s1&&rm[i]>s1)||(r1>=s1&&rm[i]<s1)))tr0=1;else if(l1!=null&&((r1<=l1&&rm[i]>l1)||(r1>=l1&&rm[i]<l1)))tr0=-1;tl[i]=tr0===1?lb[i]:sb[i]}return[rm,tl]}
function fisher(H,L,n){const g=H.map((h,i)=>(h+L[i])/2),a=hh(g,n),b=ll(g,n),f=nul(g.length),t=nul(g.length);let v=0,f0=0;
 for(let i=0;i<g.length;i++){if(a[i]==null)continue;v=.66*((g[i]-b[i])/((a[i]-b[i])||1e-9)-.5)+.67*v;v=Math.max(-.999,Math.min(.999,v));const x=.5*Math.log((1+v)/(1-v))+.5*f0;t[i]=f0;f[i]=x;f0=x}return[f,t]}
function alma(x,n,off,sig){const m=off*(n-1),sg=n/sig,w=[...Array(n)].map((_,i)=>Math.exp(-((i-m)**2)/(2*sg*sg))),tw=w.reduce((a,b)=>a+b,0);return roll(x,n,v=>v.reduce((a,b,i)=>a+b*w[i],0)/tw)}
function kama(C,n,f,sl){const o=nul(C.length),fs=2/(f+1),ss=2/(sl+1);let k=null;for(let i=n;i<C.length;i++){let vo=0;for(let j=i-n+1;j<=i;j++)vo+=Math.abs(C[j]-C[j-1]);
 const er=vo?Math.abs(C[i]-C[i-n])/vo:0,sc=(er*(fs-ss)+ss)**2;k=k===null?C[i]:k+sc*(C[i]-k);o[i]=k}return o}
function mcginley(C,n){const o=nul(C.length),e=ema(C,n);let m=null;for(let i=0;i<C.length;i++){if(m===null){if(e[i]!=null)m=e[i];o[i]=m;continue}m=m+(C[i]-m)/(n*Math.pow(C[i]/m,4));o[i]=m}return o}
// khối lượng đột biến: rel = tick volume ÷ trung bình 20 nến đã đóng ngay trước; đột biến khi rel ≥ k và thân ≥ 50% biên độ; chiều theo thân nến
function kldb(H,L,C,O,V,n,k,xu){V=V||[];const e=ema(C,50),r=nul(C.length),mk=[],pt=nul(C.length);
 for(let i=n;i<C.length;i++){if(V[i]==null)continue;let s=0,ok=1;for(let j=i-n;j<i;j++){if(V[j]==null){ok=0;break}s+=V[j]}if(!ok||!s)continue;
  const x=V[i]/(s/n),len=C[i]>O[i]?1:C[i]<O[i]?0:-1;r[i]=len===0?-x:x;const bd=H[i]-L[i];
  if(x>=k&&len>=0&&bd>0&&Math.abs(C[i]-O[i])>=.5*bd&&(!xu||(e[i]!=null&&(len?C[i]>e[i]:C[i]<e[i])))){mk.push({i,len});pt[i]=len?L[i]:H[i]}}return[r,mk,pt]}
const L_=(t,a,k)=>[t,a,k||'duong'];
const LIB={
 sma:{ten:'Trung bình động đơn (SMA)',nhom:'xu',khung:'gia',ts:[['n','Chu kỳ',20,1]],mo:'Giá đóng trung bình của n nến.',tinh:(H,L,C,O,p)=>[L_('SMA '+p.n,sma(C,p.n))]},
 ema:{ten:'Trung bình động hàm mũ (EMA)',nhom:'xu',khung:'gia',ts:[['n','Chu kỳ',9,1]],mo:'Trung bình nghiêng về nến gần; hay dùng 9, 21, 50, 200.',tinh:(H,L,C,O,p)=>[L_('EMA '+p.n,ema(C,p.n))]},
 wma:{ten:'Trung bình động có trọng số (WMA)',nhom:'xu',khung:'gia',ts:[['n','Chu kỳ',20,1]],mo:'Nến gần có trọng số lớn hơn theo bậc 1, 2, 3…',tinh:(H,L,C,O,p)=>[L_('WMA '+p.n,wma(C,p.n))]},
 hma:{ten:'Trung bình động Hull (HMA)',nhom:'xu',khung:'gia',ts:[['n','Chu kỳ',21,1]],mo:'Mượt và ít trễ: WMA của (2·WMA n/2 − WMA n).',
  tinh:(H,L,C,O,p)=>{const a=wma(C,Math.max(1,Math.floor(p.n/2))),b=wma(C,p.n);return[L_('HMA '+p.n,wma(hop(a,b,(x,y)=>2*x-y),Math.max(1,Math.round(Math.sqrt(p.n)))))]}},
 dema:{ten:'EMA kép (DEMA)',nhom:'xu',khung:'gia',ts:[['n','Chu kỳ',20,1]],mo:'2·EMA − EMA của EMA, bám giá nhanh hơn EMA.',tinh:(H,L,C,O,p)=>{const e=ema(C,p.n);return[L_('DEMA '+p.n,hop(e,ema(e,p.n),(a,b)=>2*a-b))]}},
 bb:{ten:'Dải Bollinger',nhom:'bien',khung:'gia',ts:[['n','Chu kỳ',20,1],['k','Độ lệch chuẩn',2,.1]],mo:'SMA ± k lần độ lệch chuẩn; dải hẹp lại thường báo sắp có nhịp mạnh.',
  tinh:(H,L,C,O,p)=>{const m=sma(C,p.n),s=sd(C,p.n);return[L_('BB giữa',m),L_('BB trên',hop(m,s,(a,b)=>a+p.k*b)),L_('BB dưới',hop(m,s,(a,b)=>a-p.k*b))]}},
 kc:{ten:'Kênh Keltner',nhom:'bien',khung:'gia',ts:[['n','Chu kỳ EMA',20,1],['k','Hệ số ATR',2,.1],['a','Chu kỳ ATR',10,1]],mo:'EMA ± k lần ATR.',
  tinh:(H,L,C,O,p)=>{const m=ema(C,p.n),a=atr(H,L,C,p.a);return[L_('KC giữa',m),L_('KC trên',hop(m,a,(x,y)=>x+p.k*y)),L_('KC dưới',hop(m,a,(x,y)=>x-p.k*y))]}},
 dc:{ten:'Kênh Donchian',nhom:'bien',khung:'gia',ts:[['n','Chu kỳ',20,1]],mo:'Đỉnh cao nhất và đáy thấp nhất của n nến; nền của chiến lược phá vỡ Turtle.',
  tinh:(H,L,C,O,p)=>{const a=hh(H,p.n),b=ll(L,p.n);return[L_('DC trên',a),L_('DC giữa',hop(a,b,(x,y)=>(x+y)/2)),L_('DC dưới',b)]}},
 env:{ten:'Đường bao (Envelopes)',nhom:'bien',khung:'gia',ts:[['n','Chu kỳ',20,1],['pt','Phần trăm',.5,.1]],mo:'SMA ± một tỷ lệ phần trăm cố định.',
  tinh:(H,L,C,O,p)=>{const m=sma(C,p.n);return[L_('Env giữa',m),L_('Env trên',m.map(v=>v==null?null:v*(1+p.pt/100))),L_('Env dưới',m.map(v=>v==null?null:v*(1-p.pt/100)))]}},
 psar:{ten:'Parabolic SAR',nhom:'xu',khung:'gia',ts:[['b','Bước',.02,.01],['t','Tối đa',.2,.01]],mo:'Chấm đi theo xu hướng, đổi phía khi giá cắt qua; hay dùng làm dừng lỗ dời.',
  tinh:(H,L,C,O,p)=>[L_('SAR',psar(H,L,p.b,p.t),'cham')]},
 st:{ten:'SuperTrend',nhom:'xu',khung:'gia',ts:[['n','Chu kỳ ATR',10,1],['k','Hệ số',3,.1]],mo:'Đường dưới giá khi xu hướng tăng, trên giá khi giảm (ATR Wilder).',
  tinh:(H,L,C,O,p)=>{const[o,ch]=supertrend(H,L,C,p.n,p.k);return[L_('ST tăng',o.map((v,i)=>ch[i]>0?v:null),'tang'),L_('ST giảm',o.map((v,i)=>ch[i]<0?v:null),'giam')]}},
 rsi:{ten:'RSI (sức mạnh tương đối)',nhom:'dao',khung:'rieng',ts:[['n','Chu kỳ',14,1]],muc:[70,30],mo:'Trên 70 là mua nhiều, dưới 30 là bán nhiều (kiểu Wilder như MT5).',
  tinh:(H,L,C,O,p)=>[L_('RSI '+p.n,rsi(C,p.n))]},
 srsi:{ten:'Stochastic RSI',nhom:'dao',khung:'rieng',ts:[['n','Chu kỳ RSI',14,1],['s','Chu kỳ Stoch',14,1],['k','Làm trơn K',3,1],['d','Làm trơn D',3,1]],muc:[80,20],
  mo:'Stochastic tính trên RSI, nhạy hơn RSI.',tinh:(H,L,C,O,p)=>{const r=rsi(C,p.n),[k,d]=stoch(r,r,r,p.s,p.k,p.d);return[L_('K',k),L_('D',d)]}},
 stoch:{ten:'Stochastic',nhom:'dao',khung:'rieng',ts:[['n','%K',14,1],['k','Làm trơn K',3,1],['d','%D',3,1]],muc:[80,20],mo:'Vị trí giá đóng trong biên đỉnh–đáy n nến.',
  tinh:(H,L,C,O,p)=>{const[k,d]=stoch(H,L,C,p.n,p.k,p.d);return[L_('%K',k),L_('%D',d)]}},
 macd:{ten:'MACD',nhom:'dao',khung:'rieng',ts:[['f','Nhanh',12,1],['s','Chậm',26,1],['t','Tín hiệu',9,1]],mo:'EMA nhanh − EMA chậm, đường tín hiệu và cột chênh lệch.',
  tinh:(H,L,C,O,p)=>{const m=hop(ema(C,p.f),ema(C,p.s),(a,b)=>a-b),s=ema(m,p.t);return[L_('Cột',hop(m,s,(a,b)=>a-b),'cot'),L_('MACD',m),L_('Tín hiệu',s)]}},
 cci:{ten:'CCI (chỉ số kênh hàng hóa)',nhom:'dao',khung:'rieng',ts:[['n','Chu kỳ',20,1]],muc:[100,-100],mo:'Độ lệch của giá điển hình so với trung bình.',tinh:(H,L,C,O,p)=>[L_('CCI '+p.n,cci(H,L,C,p.n))]},
 willr:{ten:'Williams %R',nhom:'dao',khung:'rieng',ts:[['n','Chu kỳ',14,1]],muc:[-20,-80],mo:'Như Stochastic nhưng thang 0 tới −100.',
  tinh:(H,L,C,O,p)=>{const a=hh(H,p.n),b=ll(L,p.n);return[L_('%R '+p.n,C.map((c,i)=>a[i]==null||a[i]===b[i]?null:-100*(a[i]-c)/(a[i]-b[i])))]}},
 adx:{ten:'ADX / DMI (độ mạnh xu hướng)',nhom:'xu',khung:'rieng',ts:[['n','Chu kỳ',14,1]],muc:[25],mo:'ADX trên 25 thường là có xu hướng; +DI và −DI cho chiều.',
  tinh:(H,L,C,O,p)=>{const[a,pd,md]=adx(H,L,C,p.n);return[L_('ADX',a),L_('+DI',pd),L_('−DI',md)]}},
 aroon:{ten:'Aroon',nhom:'xu',khung:'rieng',ts:[['n','Chu kỳ',25,1]],muc:[70,30],mo:'Bao lâu từ đỉnh, đáy gần nhất trong n nến.',tinh:(H,L,C,O,p)=>{const[u,d]=aroon(H,L,p.n);return[L_('Aroon lên',u),L_('Aroon xuống',d)]}},
 atr:{ten:'ATR (biên độ thật trung bình)',nhom:'bien',khung:'rieng',ts:[['n','Chu kỳ',14,1]],mo:'Biên độ trung bình mỗi nến, kiểu Wilder; dùng đặt dừng lỗ theo biến động.',tinh:(H,L,C,O,p)=>[L_('ATR '+p.n,atr(H,L,C,p.n))]},
 mom:{ten:'Momentum (động lượng)',nhom:'dao',khung:'rieng',ts:[['n','Chu kỳ',10,1]],muc:[0],mo:'Giá đóng hiện tại − giá đóng n nến trước.',tinh:(H,L,C,O,p)=>[L_('MOM '+p.n,C.map((c,i)=>i<p.n?null:c-C[i-p.n]))]},
 roc:{ten:'ROC (tốc độ thay đổi %)',nhom:'dao',khung:'rieng',ts:[['n','Chu kỳ',10,1]],muc:[0],mo:'Phần trăm thay đổi so với n nến trước.',tinh:(H,L,C,O,p)=>[L_('ROC '+p.n,C.map((c,i)=>i<p.n||!C[i-p.n]?null:100*(c/C[i-p.n]-1)))]},
 ao:{ten:'Awesome Oscillator',nhom:'dao',khung:'rieng',ts:[['f','Nhanh',5,1],['s','Chậm',34,1]],muc:[0],mo:'SMA 5 − SMA 34 của giá giữa nến (Bill Williams).',
  tinh:(H,L,C,O,p)=>{const g=H.map((h,i)=>(h+L[i])/2);return[L_('AO',hop(sma(g,p.f),sma(g,p.s),(a,b)=>a-b),'cot')]}},
 bbw:{ten:'Độ rộng dải Bollinger (%)',nhom:'bien',khung:'rieng',ts:[['n','Chu kỳ',20,1],['k','Độ lệch chuẩn',2,.1]],mo:'(Dải trên − dải dưới) / dải giữa; thấp kỷ lục là lúc nén chặt.',
  tinh:(H,L,C,O,p)=>{const m=sma(C,p.n),s=sd(C,p.n);return[L_('BBW',hop(m,s,(a,b)=>a?100*2*p.k*b/a:null))]}},
 sqz:{ten:'Squeeze Momentum (TTM, kiểu LazyBear)',nhom:'cd',khung:'rieng',ts:[['n','Chu kỳ',20,1],['k','Độ lệch chuẩn BB',2,.1],['kc','Hệ số Keltner',1.5,.1]],muc:[0],
  mo:'Cột động lượng (hồi quy tuyến tính); chấm ở 0 là lúc Bollinger nằm trong Keltner, giá đang nén chờ bung.',
  tinh:(H,L,C,O,p)=>{const[v,on]=squeeze(H,L,C,p.n,p.k,p.kc);return[L_('SQZ',v,'cot'),L_('Đang nén',on,'cham')]}},
 wt:{ten:'WaveTrend (kiểu LazyBear)',nhom:'cd',khung:'rieng',ts:[['a','Kênh',10,1],['b','Trung bình',21,1]],muc:[60,-60],
  mo:'Dao động nổi tiếng; mũi tên khi WT1 cắt WT2 ở vùng quá bán (dưới −53) hoặc quá mua (trên 53).',
  tinh:(H,L,C,O,p)=>{const[a,b,mk]=wavetrend(H,L,C,p.a,p.b);return[[...L_('WT1',a),mk],L_('WT2',b)]}},
 ut:{ten:'UT Bot (dừng lỗ dời theo ATR)',nhom:'cd',khung:'gia',ts:[['a','Hệ số',1,.1],['n','Chu kỳ ATR',10,1]],
  mo:'Đường dừng lỗ dời theo ATR; mũi tên khi giá đóng cắt qua đường (tín hiệu mua bán của bản cộng đồng phổ biến).',
  tinh:(H,L,C,O,p)=>{const[st,mk]=utbot(H,L,C,p.a,p.n);return[[...L_('UT Bot',st),mk]]}},
 ce:{ten:'Chandelier Exit',nhom:'cd',khung:'gia',ts:[['n','Chu kỳ',22,1],['k','Hệ số ATR',3,.1]],
  mo:'Dừng lỗ dời theo đỉnh/đáy giá đóng ± ATR (Chuck LeBeau); đổi phía là đổi xu hướng, có mũi tên.',
  tinh:(H,L,C,O,p)=>{const[lo,sh,mk]=chandelier(H,L,C,p.n,p.k);return[[...L_('CE mua',lo,'tang'),mk],L_('CE bán',sh,'giam')]}},
 qqe:{ten:'QQE',nhom:'cd',khung:'rieng',ts:[['n','Chu kỳ RSI',14,1],['sf','Làm trơn',5,1],['q','Hệ số',4.238,.1]],muc:[50],
  mo:'RSI làm trơn kèm đường bám kiểu ATR trên RSI; cắt nhau gần mức 50 thường dùng lọc xu hướng.',tinh:(H,L,C,O,p)=>{const[a,b]=qqe(C,p.n,p.sf,p.q);return[L_('QQE',a),L_('Đường bám',b)]}},
 fisher:{ten:'Fisher Transform (Ehlers)',nhom:'dao',khung:'rieng',ts:[['n','Chu kỳ',9,1]],muc:[0],mo:'Đổi giá về phân phối gần chuẩn; đỉnh đáy sắc nét, cắt đường trễ là đổi nhịp.',
  tinh:(H,L,C,O,p)=>{const[f,t]=fisher(H,L,p.n);return[L_('Fisher',f),L_('Trễ',t)]}},
 vortex:{ten:'Vortex',nhom:'xu',khung:'rieng',ts:[['n','Chu kỳ',14,1]],mo:'VI+ trên VI− là xu hướng tăng và ngược lại.',
  tinh:(H,L,C,O,p)=>{const t=tong(tr(H,L,C),p.n),vp=tong(H.map((h,i)=>i?Math.abs(h-L[i-1]):null),p.n),vm=tong(L.map((l,i)=>i?Math.abs(l-H[i-1]):null),p.n);
   return[L_('VI+',hop(vp,t,(a,b)=>b?a/b:null)),L_('VI−',hop(vm,t,(a,b)=>b?a/b:null))]}},
 chop:{ten:'Choppiness Index',nhom:'bien',khung:'rieng',ts:[['n','Chu kỳ',14,1]],muc:[61.8,38.2],mo:'Trên 61,8 là thị trường đi ngang, dưới 38,2 là đang có xu hướng.',
  tinh:(H,L,C,O,p)=>{const t=tong(tr(H,L,C),p.n),a=hh(H,p.n),b=ll(L,p.n);return[L_('CHOP',t.map((v,i)=>v==null||a[i]==null||a[i]===b[i]?null:100*Math.log10(v/(a[i]-b[i]))/Math.log10(p.n)))]}},
 kama:{ten:'KAMA (Kaufman thích nghi)',nhom:'xu',khung:'gia',ts:[['n','Chu kỳ',10,1],['f','Nhanh',2,1],['s','Chậm',30,1]],mo:'Trung bình tự chậm lại khi đi ngang, nhanh lên khi có xu hướng.',
  tinh:(H,L,C,O,p)=>[L_('KAMA',kama(C,p.n,p.f,p.s))]},
 alma:{ten:'ALMA (Arnaud Legoux)',nhom:'xu',khung:'gia',ts:[['n','Chu kỳ',9,1],['o','Độ lệch',.85,.01],['g','Sigma',6,.1]],mo:'Trung bình trọng số Gauss: mượt và ít trễ.',
  tinh:(H,L,C,O,p)=>[L_('ALMA',alma(C,p.n,p.o,p.g))]},
 mcg:{ten:'McGinley Dynamic',nhom:'xu',khung:'gia',ts:[['n','Chu kỳ',14,1]],mo:'Đường trung bình tự điều chỉnh tốc độ theo giá, ít bị kéo lệch khi giá giật.',tinh:(H,L,C,O,p)=>[L_('McGinley',mcginley(C,p.n))]},
 lsma:{ten:'Hồi quy tuyến tính (LSMA)',nhom:'xu',khung:'gia',ts:[['n','Chu kỳ',25,1]],mo:'Điểm cuối của đường hồi quy bình phương nhỏ nhất trên n nến.',tinh:(H,L,C,O,p)=>[L_('LSMA',linreg(C,p.n))]},
 trix:{ten:'TRIX',nhom:'dao',khung:'rieng',ts:[['n','Chu kỳ',18,1]],muc:[0],mo:'Độ thay đổi của EMA ba lần (log giá), lọc nhiễu mạnh.',
  tinh:(H,L,C,O,p)=>{const e=ema(ema(ema(C.map(Math.log),p.n),p.n),p.n);return[L_('TRIX',e.map((v,i)=>i&&v!=null&&e[i-1]!=null?1e4*(v-e[i-1]):null))]}},
 uo:{ten:'Ultimate Oscillator',nhom:'dao',khung:'rieng',ts:[['a','Ngắn',7,1],['b','Vừa',14,1],['c','Dài',28,1]],muc:[70,30],mo:'Áp lực mua trên ba khoảng thời gian (Larry Williams).',
  tinh:(H,L,C,O,p)=>{const bp=C.map((c,i)=>i?c-Math.min(L[i],C[i-1]):null),t=C.map((c,i)=>i?Math.max(H[i],C[i-1])-Math.min(L[i],C[i-1]):null),
   av=n=>hop(tong(bp,n),tong(t,n),(a,b)=>b?a/b:null),a=av(p.a),b=av(p.b),c=av(p.c);return[L_('UO',a.map((v,i)=>v==null||b[i]==null||c[i]==null?null:100*(4*v+2*b[i]+c[i])/7))]}},
 elder:{ten:'Elder Ray (sức bò, sức gấu)',nhom:'dao',khung:'rieng',ts:[['n','Chu kỳ EMA',13,1]],muc:[0],mo:'Đỉnh − EMA (sức bên mua) và đáy − EMA (sức bên bán).',
  tinh:(H,L,C,O,p)=>{const e=ema(C,p.n);return[L_('Sức mua',hop(H,e,(a,b)=>a-b),'cot'),L_('Sức bán',hop(L,e,(a,b)=>a-b),'cot')]}},
 kld:{ten:'Khối lượng đột biến (tick volume MT5)',nhom:'cd',khung:'rieng',ts:[['n','Số nến làm nền',20,1],['k','Ngưỡng (số lần trung bình)',2,.1],['xu','Chỉ báo thuận EMA50 (1 có, 0 không)',1,1]],
  mo:'Cột là tick volume chia trung bình 20 nến trước (dương: nến tăng, âm: nến giảm); mũi tên khi gấp từ 2 lần, thân nến từ 50% và thuận EMA50. Vàng CFD không có khối lượng thật: tick volume là số lần giá đổi, đo độ sôi động chứ không phải lệnh của cá mập. Chỉ có khi đang nối MT5 trực tiếp.',
  tinh:(H,L,C,O,p,V)=>{const[r,mk]=kldb(H,L,C,O,V,p.n,p.k,p.xu);return[[...L_('KL',r,'cot'),mk]]}},
 kldg:{ten:'Khối lượng đột biến: dấu trên nến',nhom:'cd',khung:'gia',ts:[['n','Số nến làm nền',20,1],['k','Ngưỡng (số lần trung bình)',2,.1],['xu','Chỉ báo thuận EMA50 (1 có, 0 không)',1,1]],
  mo:'Cùng định nghĩa với "Khối lượng đột biến", nhưng vẽ mũi tên ngay dưới hoặc trên cây nến đột biến. Chỉ có khi đang nối MT5 trực tiếp.',
  tinh:(H,L,C,O,p,V)=>{const[,mk,pt]=kldb(H,L,C,O,V,p.n,p.k,p.xu);return[[...L_('KL đột biến',pt,'cham'),mk]]}},};
const NHOM={xu:'Xu hướng',dao:'Dao động',bien:'Biến động',cd:'Cộng đồng nổi tiếng'},MAUS=['#2962ff','#ff6d00','#e91e63','#00897b','#8e24aa','#fbc02d','#43a047','#6d4c41','#00acc1','#f4511e'];
// ---------------------------------------------------------------- trạng thái cá nhân (lưu trong trình duyệt)
let S={ds:[],sao:['ema','rsi','macd','bb'],mau:{}};try{Object.assign(S,JSON.parse(localStorage.getItem('so-cbcn1')||'{}'))}catch(e){}
S.ds=(S.ds||[]).filter(x=>x&&LIB[x.k]);const luu=()=>{try{localStorage.setItem('so-cbcn1',JSON.stringify(S))}catch(e){}};
const macDinh=k=>Object.fromEntries(LIB[k].ts.map(t=>[t[0],t[2]])),moiId=()=>Math.random().toString(36).slice(2,9);
function them(k,p){const n=S.ds.length;S.ds.push({id:moiId(),k,p:{...macDinh(k),...(p||{})},mau:MAUS[n%MAUS.length],an:false});luu();doi()}
// ---------------------------------------------------------------- vẽ lên biểu đồ (Lightweight Charts)
let SER=[],KH='',TINH=0,khoaDL='';
function goSach(c){for(const s of SER)try{c.removeSeries(s.s)}catch(e){}SER=[]}
// ---------------------------------------------------------------- dạng biểu đồ: nến, nến rỗng, Heikin Ashi, thanh OHLC, đường, vùng, đường cơ sở.
// Chuỗi nến gốc (LW.nen) giữ nguyên để các đường giá, hình vẽ và lệnh vẫn bám đúng; với dạng khác, nến gốc trong suốt và một chuỗi phủ vẽ dạng mới.
const KIEU={nen:'Nến',rong:'Nến rỗng',ha:'Heikin Ashi',thanh:'Thanh OHLC',duong:'Đường giá đóng',vung:'Vùng',coso:'Đường cơ sở'};
let KBD='nen',PHU=null,PHUK='',GOC=null,khoaKieu='';try{KBD=localStorage.getItem('so-kieu-bd')||'nen';if(!KIEU[KBD])KBD='nen'}catch(e){}
function heikin(cs){let ho=null,hc=null;return cs.map(r=>{const c=(r[1]+r[2]+r[3]+r[4])/4,o=ho===null?(r[1]+r[4])/2:(ho+hc)/2;ho=o;hc=c;return[r[0],o,Math.max(r[2],o,c),Math.min(r[3],o,c),c]})}
function kieuVe(B){const LW=B.LW,c=LW.chart,LWC=window.LightweightCharts,P=B.P||{},tr='rgba(0,0,0,0)',o=LW.nen.options();
 if(o.downColor!==tr&&o.upColor!==tr)GOC={upColor:o.upColor,downColor:o.downColor,wickUpColor:o.wickUpColor,wickDownColor:o.wickDownColor,borderUpColor:o.borderUpColor,borderDownColor:o.borderDownColor};
 if(KBD!==PHUK){if(PHU)try{c.removeSeries(PHU)}catch(e){}PHU=null;PHUK=KBD;khoaKieu='';const an={priceLineVisible:false,lastValueVisible:false};
  if(KBD==='ha')PHU=c.addSeries(LWC.CandlestickSeries,an,0);else if(KBD==='thanh')PHU=c.addSeries(LWC.BarSeries,{...an,thinBars:false},0);
  else if(KBD==='duong')PHU=c.addSeries(LWC.LineSeries,{...an,lineWidth:2},0);else if(KBD==='vung')PHU=c.addSeries(LWC.AreaSeries,{...an,lineWidth:2},0);
  else if(KBD==='coso')PHU=c.addSeries(LWC.BaselineSeries,{...an,lineWidth:2},0);
  if(KBD==='nen'&&GOC)LW.nen.applyOptions(GOC)}
 if(KBD==='nen')return;
 if(KBD==='rong'){LW.nen.applyOptions({upColor:tr});return}                       // nến tăng chỉ còn viền, như kiểu "Hollow candles"
 LW.nen.applyOptions({upColor:tr,downColor:tr,wickUpColor:tr,wickDownColor:tr,borderUpColor:tr,borderDownColor:tr});
 const len=(GOC&&GOC.upColor)||P.bull||'#26a69a',xuong=(GOC&&GOC.downColor)||P.bear||'#ef5350',xanh='#2962ff';
 if(KBD==='ha')PHU.applyOptions({upColor:len,downColor:xuong,wickUpColor:len,wickDownColor:xuong,borderUpColor:len,borderDownColor:xuong});
 else if(KBD==='thanh')PHU.applyOptions({upColor:len,downColor:xuong});else if(KBD==='duong')PHU.applyOptions({color:xanh});
 else if(KBD==='vung')PHU.applyOptions({lineColor:xanh,topColor:'rgba(41,98,255,.35)',bottomColor:'rgba(41,98,255,.02)'});
 const cs=B.D.candles,k=KBD+'|'+cs.length+'|'+cs[0][0]+'|'+cs[cs.length-1][4];if(k===khoaKieu)return;khoaKieu=k;
 if(KBD==='coso'){const n=Math.min(200,cs.length),tb=cs.slice(-n).reduce((s,r)=>s+r[4],0)/n;       // mốc: giá đóng trung bình 200 nến gần nhất
  PHU.applyOptions({baseValue:{type:'price',price:tb},topLineColor:len,bottomLineColor:xuong,topFillColor1:'rgba(38,166,154,.28)',topFillColor2:'rgba(38,166,154,.03)',
   bottomFillColor1:'rgba(239,83,80,.03)',bottomFillColor2:'rgba(239,83,80,.28)'})}
 const ds=KBD==='ha'?heikin(cs):cs;
 PHU.setData(KBD==='ha'||KBD==='thanh'?ds.map(r=>({time:r[0],open:r[1],high:r[2],low:r[3],close:r[4]})):cs.map(r=>({time:r[0],value:r[4]})))}
const MOC=[];
function ve(){const B=window.BDCB&&window.BDCB();if(!B||!B.LW||!B.D||!B.D.candles||!B.D.candles.length)return;const LW=B.LW,c=LW.chart,LWC=window.LightweightCharts,P=B.P||{};
 try{kieuVe(B)}catch(e){console.warn('Dạng biểu đồ:',e)}
 for(const f of MOC)try{f(B)}catch(e){console.warn('Công cụ biểu đồ:',e)}           // bieu_do_them.py: nền phiên, hồ sơ khối lượng, thang giá, so sánh mã
 const bat=S.ds.filter(x=>!x.an),coBan=1+String(LW.khDao||'').split(',').filter(Boolean).length,
  kh=coBan+'|'+(LW.khDao||'')+'|'+bat.map(x=>x.id+x.k+JSON.stringify(x.p)+x.mau).join(';'),
  mat=SER.some(s=>{try{return!c.panes().some(pa=>pa.getSeries().includes(s.s))}catch(e){return true}});
 if(kh!==KH||mat){goSach(c);try{for(let i=c.panes().length-1;i>=coBan;i--)c.removePane(i)}catch(e){}KH=kh;khoaDL='';let pn=coBan;
  for(const x of bat){const d=LIB[x.k],cs=d.khung==='rieng'?pn++:0,mau=[x.mau,'#ff6d00','#26a69a','#ef5350'];
   d.tinh([0],[0],[0],[0],x.p).forEach(([ten,,kieu],j)=>{const m=kieu==='tang'?'#26a69a':kieu==='giam'?'#ef5350':j===0?x.mau:mau[j%4],
     o={color:m,lineWidth:j===0?2:1,priceLineVisible:false,lastValueVisible:d.khung==='rieng'||j===0,title:d.khung==='rieng'?'':ten,crosshairMarkerVisible:kieu!=='cham'};
    let s;if(kieu==='cot')s=c.addSeries(LWC.HistogramSeries,{priceLineVisible:false,lastValueVisible:false},cs);
    else s=c.addSeries(LWC.LineSeries,kieu==='cham'?{...o,lineVisible:false,pointMarkersVisible:true,pointMarkersRadius:1.6}:o,cs);
    SER.push({s,id:x.id,j,kieu,mau:m,mk:null});
    if(j===0&&d.muc)for(const v of d.muc)try{s.createPriceLine({price:v,color:P.mute||'#888',lineWidth:1,lineStyle:1,axisLabelVisible:true,title:''})}catch(e){}})}
  try{c.panes().forEach((pa,i)=>{if(i>=coBan)pa.setStretchFactor(.22)})}catch(e){}}
 const cs=B.D.candles,k=cs.length+'|'+cs[0][0]+'|'+cs[cs.length-1][4]+'|'+KH,now=Date.now();
 if(k===khoaDL||(now-TINH<800&&khoaDL.split('|')[0]==String(cs.length)))return;khoaDL=k;TINH=now;
 const H=cs.map(r=>r[2]),Lo=cs.map(r=>r[3]),C=cs.map(r=>r[4]),O=cs.map(r=>r[1]),VM=B.D.vol||{},V=cs.map(r=>VM[r[0]]);          // V: tick volume của MT5 theo giờ mở nến (không có khi dùng kho nến)
 for(const x of bat){const out=LIB[x.k].tinh(H,Lo,C,O,x.p,V);for(const it of SER.filter(s=>s.id===x.id)){const a=out[it.j]&&out[it.j][1];if(!a)continue;
  it.s.setData(cs.map((r,i)=>a[i]==null||!isFinite(a[i])?{time:r[0]}:{time:r[0],value:a[i],...(it.kieu==='cot'?{color:a[i]>=0?'rgba(38,166,154,.6)':'rgba(239,83,80,.6)'}:{})}));
  const mk=out[it.j][3];if(mk&&LWC.createSeriesMarkers){if(!it.mk)it.mk=LWC.createSeriesMarkers(it.s,[]);                  // mũi tên mua bán của chỉ báo (300 dấu gần nhất)
   it.mk.setMarkers(mk.filter(m=>m.i<cs.length).slice(-300).map(m=>({time:cs[m.i][0],position:m.len?'belowBar':'aboveBar',color:m.len?'#26a69a':'#ef5350',shape:m.len?'arrowUp':'arrowDown'})))}}}}
function doi(){KH+='*';ve();veDs()}
// số cuối (nến đã đóng) của các chỉ báo đang bật, mũi tên gần nhất và 60 nến, cho nút "AI đọc chỉ báo"
function tomTat(){const B=window.BDCB&&window.BDCB(),r={tf:'',ma:'XAUUSD',chi_bao:[],nen:[],lang:(document.documentElement.lang||'vi').slice(0,2)};if(!B||!B.D||!B.D.candles)return r;
 const D=B.D,cs=D.candles,n=D.live!=null&&D.live>=0&&D.live<cs.length?D.live:cs.length,c2=cs.slice(0,n),VM=D.vol||{};r.tf=D.tf||'';r.ma=D.khac_vang?D.ma:'XAUUSD';
 const H=c2.map(x=>x[2]),Lo=c2.map(x=>x[3]),C=c2.map(x=>x[4]),O=c2.map(x=>x[1]),V=c2.map(x=>VM[x[0]]),so=v=>v==null||!isFinite(v)?null:+(+v).toPrecision(6);
 for(const x of S.ds.filter(v=>!v.an&&LIB[v.k])){let out;try{out=LIB[x.k].tinh(H,Lo,C,O,x.p,V)}catch(e){continue}const gt={},dau=[];
  for(const o of out){gt[o[0]]=[so(o[1][n-1]),so(o[1][n-2])];if(o[3])for(const m of o[3].filter(m=>m.i<n).slice(-3))dau.push({len:m.len,cach:n-1-m.i})}
  r.chi_bao.push({ten:LIB[x.k].ten,tham_so:x.p,gia_tri:gt,dau})}
 r.nen=c2.slice(-60).map(x=>x.slice(0,5));return r}
// ---------------------------------------------------------------- hộp chọn
const NEN=document.createElement('div');NEN.className='cbcn-nen';NEN.hidden=true;
NEN.innerHTML='<div class="cbcn" role="dialog" aria-modal="true" aria-label="Chỉ báo"><header><b>Chỉ báo</b><button type="button" class="ghost" data-dong>Đóng</button></header>'
 +'<div class="tim"><input type="search" placeholder="Tìm chỉ báo: EMA, RSI, MACD, Bollinger…" aria-label="Tìm chỉ báo"></div>'
 +'<div class="tab" role="group" aria-label="Nhóm chỉ báo"></div><div class="ds"></div></div>';
document.body.appendChild(NEN);let TAB='tat';const DS=NEN.querySelector('.ds'),TIM=NEN.querySelector('.tim input');
const TABS=[['tat','Tất cả'],['sao','Yêu thích'],['dung','Đang dùng'],['xu','Xu hướng'],['dao','Dao động'],['bien','Biến động'],['cd','Cộng đồng nổi tiếng'],['co_san','Có sẵn của hệ thống'],['mau','Mẫu của tôi']];
function veTab(){NEN.querySelector('.tab').innerHTML=TABS.map(([k,n])=>`<button type="button" class="ghost" data-tab="${k}" aria-pressed="${TAB===k}">${n}${k==='dung'&&S.ds.length?' ('+S.ds.length+')':''}</button>`).join('')}
function hangLib(k){const d=LIB[k],sao=S.sao.includes(k),dem=S.ds.filter(x=>x.k===k).length;
 return`<div class="h"><button type="button" class="sao" data-sao="${k}" aria-pressed="${sao}" aria-label="Yêu thích" title="Yêu thích">${sao?'★':'☆'}</button>`
 +`<b>${esc(d.ten)}</b><button type="button" class="them" data-them="${k}">Thêm${dem?' ('+dem+')':''}</button><small>${esc(NHOM[d.nhom])} · ${d.khung==='gia'?'trên biểu đồ giá':'khung riêng'} · ${esc(d.mo)}</small></div>`}
function hangDung(x){const d=LIB[x.k];return`<div class="dg${x.an?' an':''}" data-id="${x.id}"><input type="color" value="${x.mau}" data-mau aria-label="Màu">`
 +`<b>${esc(d.ten)}</b><button type="button" class="ghost" data-an>${x.an?'Hiện':'Ẩn'}</button><button type="button" class="ghost" data-chep>Nhân bản</button><button type="button" class="ghost xoa" data-xoa>Xóa</button>`
 +`<div class="ts">${d.ts.map(([k,n,,b])=>`<label>${esc(n)}<input type="number" step="${b}" min="${b}" data-ts="${k}" value="${x.p[k]}"></label>`).join('')}</div></div>`}
function veDs(){if(NEN.hidden)return;veTab();const q=TIM.value.trim().toLowerCase(),khop=k=>!q||(k+' '+LIB[k].ten+' '+LIB[k].mo).toLowerCase().includes(q);let h='';
 if(TAB==='dung')h=S.ds.length?S.ds.map(hangDung).join(''):'<p class="rong">Chưa dùng chỉ báo nào. Chọn ở tab Tất cả.</p>';
 else if(TAB==='co_san'){const ch=[...document.querySelectorAll('.chips .chip[data-k]')].filter(b=>!q||b.textContent.toLowerCase().includes(q));
  h='<p class="rong">Các chỉ báo hệ thống tính ở máy chủ (gồm vùng giá, lệnh, giờ tin). Bấm để bật hoặc tắt.</p>'+ch.map(b=>`<div class="h"><span></span><b>${esc(b.textContent)}</b>`
   +`<button type="button" class="them" data-chip="${esc(b.dataset.k)}">${b.getAttribute('aria-pressed')==='true'?'Đang bật · Tắt':'Bật'}</button></div>`).join('')}
 else if(TAB==='mau'){const ten=Object.keys(S.mau||{});h='<div class="mau"><input type="text" maxlength="40" placeholder="Tên mẫu, ví dụ: Lướt sóng M5" data-ten-mau><button type="button" data-luu-mau>Lưu bộ đang dùng</button></div>'
  +(ten.length?ten.map(t=>`<div class="h"><span></span><b>${esc(t)}</b><span><button type="button" class="them" data-ap="${esc(t)}">Áp dụng</button> <button type="button" class="ghost them" data-bo-mau="${esc(t)}">Xóa</button></span>`
   +`<small>${S.mau[t].map(x=>esc(LIB[x.k]?LIB[x.k].ten.split(' (')[0]+' '+Object.values(x.p).join('/'):'')).join(' · ')}</small></div>`).join(''):'<p class="rong">Chưa có mẫu nào. Bật các chỉ báo bạn hay dùng rồi lưu thành mẫu.</p>')}
 else{const ds=Object.keys(LIB).filter(k=>(TAB==='tat'||(TAB==='sao'?S.sao.includes(k):LIB[k].nhom===TAB))&&khop(k));
  h=ds.length?ds.map(hangLib).join(''):'<p class="rong">'+(TAB==='sao'?'Bấm ☆ để thêm chỉ báo vào Yêu thích.':'Không có chỉ báo khớp.')+'</p>'}
 DS.innerHTML=h}
NEN.addEventListener('click',e=>{const t=e.target;if(t===NEN||t.closest('[data-dong]')){dong();return}
 const b=t.closest('button');if(!b)return;const dg=t.closest('.dg'),x=dg&&S.ds.find(v=>v.id===dg.dataset.id);
 if(b.dataset.tab){TAB=b.dataset.tab;veDs()}
 else if(b.dataset.sao){const k=b.dataset.sao;S.sao=S.sao.includes(k)?S.sao.filter(v=>v!==k):[...S.sao,k];luu();veDs()}
 else if(b.dataset.them)them(b.dataset.them);
 else if(b.dataset.chip){const c=document.querySelector(`.chips .chip[data-k="${b.dataset.chip}"]`);if(c)c.click();veDs()}
 else if(x&&b.hasAttribute('data-an')){x.an=!x.an;luu();doi()}
 else if(x&&b.hasAttribute('data-xoa')){S.ds=S.ds.filter(v=>v!==x);luu();doi()}
 else if(x&&b.hasAttribute('data-chep'))them(x.k,x.p);
 else if(b.hasAttribute('data-luu-mau')){const i=NEN.querySelector('[data-ten-mau]'),ten=(i.value||'').trim();if(!ten||!S.ds.length)return;S.mau={...(S.mau||{}),[ten]:S.ds.map(v=>({k:v.k,p:v.p,mau:v.mau}))};luu();veDs()}
 else if(b.dataset.ap){S.ds=(S.mau[b.dataset.ap]||[]).filter(v=>LIB[v.k]).map(v=>({id:moiId(),k:v.k,p:{...macDinh(v.k),...v.p},mau:v.mau,an:false}));luu();TAB='dung';doi()}
 else if(b.dataset.boMau){delete S.mau[b.dataset.boMau];luu();veDs()}});
NEN.addEventListener('change',e=>{const t=e.target,dg=t.closest('.dg'),x=dg&&S.ds.find(v=>v.id===dg.dataset.id);if(!x)return;
 if(t.hasAttribute('data-mau'))x.mau=t.value;else if(t.dataset.ts){const v=parseFloat(t.value);if(isFinite(v)&&v>0){x.p[t.dataset.ts]=Math.min(v,1000)}else t.value=x.p[t.dataset.ts]}luu();doi()});
TIM.addEventListener('input',()=>{if(TAB==='dung'||TAB==='mau')TAB='tat';veDs()});
function mo(){NEN.hidden=false;TIM.value='';veDs();setTimeout(()=>TIM.focus(),30)}function dong(){NEN.hidden=true;nut&&nut.focus()}
addEventListener('keydown',e=>{if(!NEN.hidden&&e.key==='Escape'){e.stopPropagation();dong();return}
 if(e.key==='/'&&NEN.hidden&&!/INPUT|TEXTAREA|SELECT/.test((document.activeElement||{}).tagName||'')&&!e.ctrlKey&&!e.metaKey){e.preventDefault();mo()}},true);
// nút trên thanh công cụ của biểu đồ
let nut=null;const t2=document.querySelector('.tools.t2');if(t2){nut=document.createElement('button');nut.type='button';nut.className='ghost nho cbcn-mo';nut.title='Thêm chỉ báo (phím /)';
 nut.innerHTML='<svg viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M2 14l4-5 3 3 6-8M12 4h3v3"/></svg><span>Thêm chỉ báo</span>';
 nut.addEventListener('click',mo);const tuy=t2.querySelector('details.tuy');if(tuy)tuy.after(nut);else t2.appendChild(nut);
 const ch=document.createElement('label');ch.className='sel cbcn-kieu';ch.title='Dạng biểu đồ';
 ch.innerHTML='<select aria-label="Dạng biểu đồ">'+Object.entries(KIEU).map(([k,n])=>`<option value="${k}"${k===KBD?' selected':''}>${n}</option>`).join('')+'</select>';
 ch.querySelector('select').addEventListener('change',e=>{KBD=e.target.value;try{localStorage.setItem('so-kieu-bd',KBD)}catch(_){}ve()});nut.before(ch)}
return{ve,mo,LIB,KIEU,moc:MOC,tomTat,_tinh:{ema,sma,rma,rsi,stoch,atr,supertrend,psar,adx,cci,aroon,wma,sd,heikin,kldb,linreg,squeeze,wavetrend,utbot,chandelier,qqe,fisher,alma,kama,mcginley}}})();
"""

from . import bieu_do_them as _them  # noqa: E402 - công cụ thêm chạy ngay sau bộ chọn chỉ báo, cùng thẻ script

from . import bieu_do_phat_lai as _pl  # noqa: E402 - phát lại nến, chạy sau công cụ thêm

CSS += _them.CSS + _pl.CSS
JS += _them.JS + _pl.JS
