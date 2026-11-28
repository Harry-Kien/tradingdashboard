"""Bộ chọn chỉ báo kiểu TradingView cho trang Biểu đồ (chủ dự án yêu cầu ngày 26/11/2026).

Nút "Thêm chỉ báo" mở hộp chọn: ô tìm, nhóm (xu hướng, dao động, biến động), yêu thích, danh sách đang dùng với chỉnh tham số, màu, ẩn hiện;
thêm được nhiều bản cùng loại (EMA 9, EMA 21, EMA 200…); lưu mẫu cá nhân. Mọi lựa chọn lưu trong trình duyệt của người dùng (localStorage).

Các chỉ báo ở đây tính ngay trong trình duyệt trên đúng chuỗi nến biểu đồ đang vẽ (D.candles, kể cả phần nến cũ đã ghép), nên không lệch chỗ
khi ghép thêm nến cũ. Công thức theo chuẩn TradingView và khớp với phía máy chủ (gia.rsi_wilder, chi_bao_them: EMA kiểu pandas adjust=False,
RMA Wilder, Bollinger độ lệch chuẩn tổng thể, Stochastic chậm, SuperTrend); tests/test_bieu_do_chi_bao.py đối chiếu số với pandas.
Tab "Có sẵn" bật tắt các chỉ báo hệ thống tính ở máy chủ (nút chip cũ), không tính lại. Nhóm "Khối lượng" (VWAP, OBV, MFI, CMF, A/D…) dùng tick volume
của MT5 (D.vol), chỉ có khi đang nối MT5 trực tiếp; tinh() nhận thêm V (tick volume) và T (giờ mở nến, giây UTC) cho VWAP và mức ngày trước.
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
// ---------------------------------------------------------------- 27/11/2026: các chỉ báo phổ biến còn thiếu (công thức công khai, viết lại từ định nghĩa gốc).
// V: tick volume MT5 (không có khi dùng kho nến); T: giờ mở nến (giây UTC). Thiếu V hoặc T thì chỉ báo cần chúng trả mảng rỗng, không vẽ gì.
const coV=(V,n)=>!!V&&V.length===n&&V.some(v=>v!=null),ngay=(T,gio)=>T.map(t=>Math.floor((t-gio*3600)/86400)),
 rocn=(C,n)=>C.map((c,i)=>i<n||!C[i-n]?null:100*(c/C[i-n]-1));
function swma(x){return x.map((v,i)=>i<3||v==null||x[i-1]==null||x[i-2]==null||x[i-3]==null?null:(x[i-3]+2*x[i-2]+2*x[i-1]+v)/6)}
function vwapf(H,L,C,V,T,gio,k){const n=C.length,m=nul(n),a=nul(n),b=nul(n);if(!coV(V,n)||!T||T.length!==n)return[m,a,b];const d=ngay(T,gio);let sv=0,s1=0,s2=0;
 for(let i=0;i<n;i++){if(i&&d[i]!==d[i-1]){sv=0;s1=0;s2=0}const w=V[i];if(w==null)continue;const tp=(H[i]+L[i]+C[i])/3;sv+=w;s1+=tp*w;s2+=tp*tp*w;if(!sv)continue;
  const g=s1/sv;m[i]=g;if(k>0){const s=Math.sqrt(Math.max(0,s2/sv-g*g));a[i]=g+k*s;b[i]=g-k*s}}return[m,a,b]}
function obvf(C,V){const n=C.length,o=nul(n);if(!coV(V,n))return o;let s=null;
 for(let i=0;i<n;i++){if(V[i]==null)continue;s=s===null?0:s+(C[i]>C[i-1]?V[i]:C[i]<C[i-1]?-V[i]:0);o[i]=s}return o}
const mfv=(H,L,C,V)=>C.map((c,i)=>V[i]==null?null:(H[i]===L[i]?0:((c-L[i])-(H[i]-c))/(H[i]-L[i]))*V[i]);   // khối lượng dòng tiền (Chaikin)
function mfif(H,L,C,V,n){const N0=C.length;if(!coV(V,N0))return nul(N0);const tp=H.map((h,i)=>(h+L[i]+C[i])/3),up=nul(N0),dn=nul(N0);
 for(let i=1;i<N0;i++){if(V[i]==null)continue;const f=tp[i]*V[i];up[i]=tp[i]>tp[i-1]?f:0;dn[i]=tp[i]<tp[i-1]?f:0}const a=tong(up,n),b=tong(dn,n);
 return a.map((v,i)=>v==null||b[i]==null?null:b[i]===0?100:100-100/(1+v/b[i]))}
function stcf(C,f,s,cl,fac){const m=hop(ema(C,f),ema(C,s),(a,b)=>a-b),n=C.length,o=nul(n),pfs=nul(n),lm=ll(m,cl),hm=hh(m,cl);let f1=0,pf=null,f2=0,pff=null;
 for(let i=0;i<n;i++){if(lm[i]==null)continue;const r=hm[i]-lm[i];f1=r>0?(m[i]-lm[i])/r*100:f1;pf=pf===null?f1:pf+fac*(f1-pf);pfs[i]=pf;
  let a=Infinity,b=-Infinity,ok=i>=cl-1;for(let j=i-cl+1;ok&&j<=i;j++){if(pfs[j]==null){ok=false;break}a=Math.min(a,pfs[j]);b=Math.max(b,pfs[j])}if(!ok)continue;
  f2=b-a>0?(pf-a)/(b-a)*100:f2;pff=pff===null?f2:pff+fac*(f2-pff);o[i]=pff}return o}
function crsif(C,a,b,c){const n=C.length,st=nul(n);let k=0;if(n)st[0]=0;for(let i=1;i<n;i++){k=C[i]>C[i-1]?(k>0?k+1:1):C[i]<C[i-1]?(k<0?k-1:-1):0;st[i]=k}
 const r1=rsi(C,a),r2=rsi(st,b),rc=rocn(C,1),o=nul(n);
 for(let i=c+1;i<n;i++){if(r1[i]==null||r2[i]==null)continue;let d=0;for(let j=i-c;j<i;j++)if(rc[j]<=rc[i])d++;o[i]=(r1[i]+r2[i]+100*d/c)/3}return o}   // hạng phần trăm trên c nến trước
function pkRsi(H,L,C,n,lb,rb){const r=rsi(C,n),N0=C.length,mk=[];let pl=null,ph=null;                                  // phân kỳ thường giữa giá và RSI tại các đáy, đỉnh của RSI
 for(let i=lb+rb;i<N0;i++){const p=i-rb;if(r[p]==null)continue;let lo=true,hi=true;
  for(let j=p-lb;j<=p+rb;j++){if(j===p)continue;if(r[j]==null){lo=false;hi=false;break}if(r[j]<=r[p])lo=false;if(r[j]>=r[p])hi=false}
  if(lo){if(pl&&p-pl[0]>=5&&p-pl[0]<=60&&r[p]>pl[1]&&L[p]<pl[2])mk.push({i:p,len:1});pl=[p,r[p],L[p]]}
  if(hi){if(ph&&p-ph[0]>=5&&p-ph[0]<=60&&r[p]<ph[1]&&H[p]>ph[2])mk.push({i:p,len:0});ph=[p,r[p],H[p]]}}return[r,mk]}
function zigzag(H,L,pt){const n=H.length,o=nul(n),P=[];if(n<2)return[o,P];let dir=0,hi=0,lo=0,ei=0,ev=0;const q=pt/100;
 for(let i=0;i<n;i++){
  if(dir===0){if(H[i]>H[hi])hi=i;if(L[i]<L[lo])lo=i;
   if(hi>lo&&H[hi]>=L[lo]*(1+q)){P.push([lo,L[lo]]);dir=1;ei=hi;ev=H[hi]}else if(lo>hi&&L[lo]<=H[hi]*(1-q)){P.push([hi,H[hi]]);dir=-1;ei=lo;ev=L[lo]}continue}
  if(dir===1){if(H[i]>ev){ei=i;ev=H[i]}else if(L[i]<=ev*(1-q)){P.push([ei,ev]);dir=-1;ei=i;ev=L[i]}}
  else{if(L[i]<ev){ei=i;ev=L[i]}else if(H[i]>=ev*(1+q)){P.push([ei,ev]);dir=1;ei=i;ev=H[i]}}}
 if(dir)P.push([ei,ev]);                                                                // chân cuối còn tạm, có thể đổi khi có nến mới
 for(let k=1;k<P.length;k++){const[a,va]=P[k-1],[b,vb]=P[k];for(let i=a;i<=b;i++)o[i]=b===a?vb:va+(vb-va)*(i-a)/(b-a)}return[o,P]}
function fractal(H,L,n){const N0=H.length,pt=nul(N0),mk=[];for(let i=n;i<N0-n;i++){let up=true,dn=true;
 for(let j=i-n;j<=i+n;j++){if(j===i)continue;if(H[j]>=H[i])up=false;if(L[j]<=L[i])dn=false}if(up){mk.push({i,len:0});pt[i]=H[i]}if(dn){mk.push({i,len:1});pt[i]=L[i]}}return[pt,mk]}
function pdhl(H,L,C,T,gio){const n=H.length,a=nul(n),b=nul(n),c=nul(n);if(!T||T.length!==n)return[a,b,c];const d=ngay(T,gio);let ch=null,cl=null,cc=null,ph=null,pl=null,pc=null;
 for(let i=0;i<n;i++){if(i&&d[i]!==d[i-1]){ph=ch;pl=cl;pc=cc;ch=null;cl=null}ch=ch===null?H[i]:Math.max(ch,H[i]);cl=cl===null?L[i]:Math.min(cl,L[i]);cc=C[i];a[i]=ph;b[i]=pl;c[i]=pc}return[a,b,c]}
// ---------------------------------------------------------------- 28/11/2026: Pivot Points nhiều kiểu, trung bình động khung lớn, Auto Fibonacci (công thức công khai)
function ky(T,gio,k){return T.map(t=>{const s=t-gio*3600;if(k===2)return Math.floor((s+3*86400)/604800);if(k===3){const d=new Date(s*1000);return d.getUTCFullYear()*12+d.getUTCMonth()}return Math.floor(s/86400)})}   // 1 ngày, 2 tuần (từ thứ Hai), 3 tháng
function mucPivot(h,l,c,kieu){const r=h-l;let p=(h+l+c)/3;                                  // trả [P, R1, R2, R3, S1, S2, S3]
 if(kieu===2)return[p,p+.382*r,p+.618*r,p+r,p-.382*r,p-.618*r,p-r];
 if(kieu===3)return[p,c+r*1.1/12,c+r*1.1/6,c+r*1.1/4,c-r*1.1/12,c-r*1.1/6,c-r*1.1/4];
 if(kieu===4)p=(h+l+2*c)/4;
 return[p,2*p-l,p+r,h+2*(p-l),2*p-h,p-r,l-2*(h-p)]}
function pivots(H,L,C,T,gio,kieu,k){const n=H.length,o=[...Array(7)].map(()=>nul(n));if(!T||T.length!==n)return o;const d=ky(T,gio,k);let ch=null,cl=null,cc=null,M=null;
 for(let i=0;i<n;i++){if(i&&d[i]!==d[i-1]){M=mucPivot(ch,cl,cc,kieu);ch=null;cl=null}ch=ch===null?H[i]:Math.max(ch,H[i]);cl=cl===null?L[i]:Math.min(cl,L[i]);cc=C[i];
  if(M)for(let j=0;j<7;j++)o[j][i]=M[j]}return o}
// trung bình động của khung lớn hơn: nến khung lớn đã đóng + giá đóng hiện tại của nến khung lớn đang chạy (không nhìn trước, nến cũ không bị vẽ lại)
function maKhung(C,T,phut,gio,n,loai){const N0=C.length,o=nul(N0);if(!T||T.length!==N0||!(phut>0)||!(n>=1))return o;const s=phut*60,al=2/(n+1),dong=[];let e=null,dem=0,sum=0,b0=null,cuoi=null;
 for(let i=0;i<N0;i++){const b=Math.floor((T[i]-gio*3600)/s);if(b0!==null&&b!==b0){const x=cuoi;dem++;e=e===null?x:al*x+(1-al)*e;dong.push(x);sum+=x;if(dong.length>n-1)sum-=dong.shift()}
  b0=b;cuoi=C[i];if(dem+1<n)continue;o[i]=loai===2?(sum+C[i])/n:e===null?C[i]:al*C[i]+(1-al)*e}return o}
const tenKhung=p=>p%1440===0?'D'+p/1440:p%60===0?'H'+p/60:'M'+p;
const FIB=[0,.236,.382,.5,.618,.786,1];
function autoFib(H,L,pt){const n=H.length,[,P]=zigzag(H,L,pt),o=FIB.map(()=>nul(n));if(P.length<2)return o;const[a,va]=P[P.length-2],[,vb]=P[P.length-1];
 FIB.forEach((r,j)=>{const v=vb-(vb-va)*r;for(let i=a;i<n;i++)o[j][i]=v});return o}
const L_=(t,a,k)=>[t,a,k||'duong'];
const KLM='Vàng CFD dùng tick volume (số lần giá đổi trong nến), không phải khối lượng hợp đồng thật. Chỉ có khi đang nối MT5 trực tiếp.';
const LIB={
 zscore:{ten:'Z-score giá đóng',nhom:'dao',khung:'rieng',ts:[['n','Chu kỳ',20,1]],muc:[-2,0,2],mo:'(Giá đóng − SMA) / độ lệch chuẩn tổng thể; đo khoảng cách với trung bình. Chuỗi phẳng trả 0. Không tự xác nhận đảo chiều.',
  tinh:(H,L,C,O,p)=>{const m=sma(C,p.n),s=sd(C,p.n);return[L_('Z-score',C.map((c,i)=>m[i]==null||s[i]==null?null:s[i]===0?0:(c-m[i])/s[i]))]}},
 er:{ten:'Hiệu suất xu hướng (Efficiency Ratio)',nhom:'xu',khung:'rieng',ts:[['n','Chu kỳ',10,1]],muc:[0,1],mo:'Khoảng dịch chuyển tuyệt đối sau n nến / tổng biến động tuyệt đối từng bước, từ 0 tới 1. Cao là giá đi thẳng hơn; không dự báo hướng đi.',
  tinh:(H,L,C,O,p)=>{const d=C.map((c,i)=>i?Math.abs(c-C[i-1]):null),v=sma(d,p.n);return[L_('ER',C.map((c,i)=>i<p.n||v[i]==null?null:v[i]===0?0:Math.abs(c-C[i-p.n])/(v[i]*p.n)))]}},
 natr:{ten:'ATR chuẩn hóa (NATR, %)',nhom:'bien',khung:'rieng',ts:[['n','Chu kỳ',14,1]],mo:'100 × ATR Wilder / giá đóng; so sánh mức biến động tương đối giữa các mã. Không phải xác suất thắng.',
  tinh:(H,L,C,O,p)=>[L_('NATR %',atr(H,L,C,p.n).map((v,i)=>v==null||C[i]===0?null:100*v/Math.abs(C[i])))]},
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
 kld:{ten:'Khối lượng đột biến (tick volume MT5)',nhom:'cd',khung:'rieng',ts:[['n','Số nến làm nền',20,1],['k','Ngưỡng (số lần trung bình)',2,.1],['xu','Chỉ báo thuận EMA50 (1 có, 0 không)',1,1,0]],
  mo:'Cột là tick volume chia trung bình 20 nến trước (dương: nến tăng, âm: nến giảm); mũi tên khi gấp từ 2 lần, thân nến từ 50% và thuận EMA50. Vàng CFD không có khối lượng thật: tick volume là số lần giá đổi, đo độ sôi động chứ không phải lệnh của cá mập. Đo trên vàng 2026 (M5, M15, H1): nến có mũi tên KHÔNG đi tiếp tốt hơn nến thường, nên đừng dùng làm tín hiệu vào lệnh. Chỉ có khi đang nối MT5 trực tiếp.',
  tinh:(H,L,C,O,p,V)=>{const[r,mk]=kldb(H,L,C,O,V,p.n,p.k,p.xu);return[[...L_('KL',r,'cot'),mk]]}},
 kldg:{ten:'Khối lượng đột biến: dấu trên nến',nhom:'cd',khung:'gia',ts:[['n','Số nến làm nền',20,1],['k','Ngưỡng (số lần trung bình)',2,.1],['xu','Chỉ báo thuận EMA50 (1 có, 0 không)',1,1,0]],
  mo:'Cùng định nghĩa với "Khối lượng đột biến", nhưng vẽ mũi tên ngay dưới hoặc trên cây nến đột biến. Chỉ có khi đang nối MT5 trực tiếp.',
  tinh:(H,L,C,O,p,V)=>{const[,mk,pt]=kldb(H,L,C,O,V,p.n,p.k,p.xu);return[[...L_('KL đột biến',pt,'cham'),mk]]}},
 // ---- trung bình động và xu hướng
 smma:{ten:'Trung bình động làm trơn (SMMA, RMA)',nhom:'xu',khung:'gia',ts:[['n','Chu kỳ',14,1]],mo:'Trung bình kiểu Wilder (hệ số 1/n), mượt và chậm hơn EMA; là đường nền của RSI, ATR.',tinh:(H,L,C,O,p)=>[L_('SMMA '+p.n,rma(C,p.n))]},
 tema:{ten:'EMA ba lần (TEMA)',nhom:'xu',khung:'gia',ts:[['n','Chu kỳ',20,1]],mo:'3·EMA − 3·EMA(EMA) + EMA(EMA(EMA)), giảm độ trễ nhiều hơn DEMA.',
  tinh:(H,L,C,O,p)=>{const a=ema(C,p.n),b=ema(a,p.n),c=ema(b,p.n);return[L_('TEMA '+p.n,a.map((v,i)=>v==null||b[i]==null||c[i]==null?null:3*v-3*b[i]+c[i]))]}},
 zlema:{ten:'EMA không độ trễ (ZLEMA)',nhom:'xu',khung:'gia',ts:[['n','Chu kỳ',20,1]],mo:'EMA của (giá + (giá − giá cách (n−1)/2 nến)), bù phần trễ của EMA.',
  tinh:(H,L,C,O,p)=>{const g=Math.floor((p.n-1)/2);return[L_('ZLEMA '+p.n,ema(C.map((c,i)=>i<g?null:2*c-C[i-g]),p.n))]}},
 emac:{ten:'Giao cắt hai đường EMA',nhom:'xu',khung:'gia',ts:[['f','EMA nhanh',9,1],['s','EMA chậm',21,1]],mo:'Hai EMA kèm mũi tên khi đường nhanh cắt đường chậm. Mũi tên trễ theo bản chất đường trung bình; trong vùng đi ngang sẽ cắt qua lại nhiều lần.',
  tinh:(H,L,C,O,p)=>{const a=ema(C,p.f),b=ema(C,p.s),mk=[];for(let i=1;i<C.length;i++)if(cat(a,b,i))mk.push({i,len:a[i]>b[i]?1:0});return[[...L_('EMA '+p.f,a),mk],L_('EMA '+p.s,b)]}},
 alli:{ten:'Williams Alligator (cá sấu)',nhom:'xu',khung:'gia',ts:[['a','Hàm',13,1],['b','Răng',8,1],['c','Môi',5,1]],
  mo:'Ba đường SMMA của giá giữa (cao+thấp)/2, dời sang phải 8, 5, 3 nến. Ba đường quấn nhau là "cá sấu ngủ" (đi ngang); tách ra theo thứ tự là có xu hướng.',
  tinh:(H,L,C,O,p)=>{const g=H.map((h,i)=>(h+L[i])/2);return[L_('Hàm',dich(rma(g,p.a),8)),L_('Răng',dich(rma(g,p.b),5)),L_('Môi',dich(rma(g,p.c),3))]}},
 zz:{ten:'ZigZag (nối đỉnh đáy)',nhom:'xu',khung:'gia',ts:[['pt','Độ đảo chiều tối thiểu (%)',.5,.05,.05]],
  mo:'Nối các đỉnh, đáy khi giá đảo chiều từ mức % đã chọn; dùng đọc cấu trúc sóng, kẻ Fibonacci. Chân cuối cùng còn thay đổi khi có nến mới, nên không dùng làm tín hiệu.',
  tinh:(H,L,C,O,p)=>[L_('ZigZag',zigzag(H,L,p.pt)[0])]},
 frac:{ten:'Williams Fractals (đỉnh đáy fractal)',nhom:'xu',khung:'gia',ts:[['n','Số nến mỗi bên',2,1]],
  mo:'Đỉnh cao hơn n nến hai bên (mũi tên xuống) và đáy thấp hơn n nến hai bên (mũi tên lên). Chỉ xác nhận sau n nến kế tiếp, nên mũi tên hiện trễ n nến.',
  tinh:(H,L,C,O,p)=>{const[pt,mk]=fractal(H,L,p.n);return[[...L_('Fractal',pt,'cham'),mk]]}},
 pdhl:{ten:'Đỉnh, đáy, đóng cửa ngày trước',nhom:'xu',khung:'gia',ts:[['gio','Giờ bắt đầu ngày (giờ UTC)',0,1,0]],
  mo:'Mức cao, thấp và giá đóng của ngày giao dịch trước, vẽ dạng bậc thang cho cả ngày hiện tại; hay được dùng làm vùng hỗ trợ, kháng cự trong ngày. Dùng trên khung dưới D1.',
  tinh:(H,L,C,O,p,V,T)=>{const[a,b,c]=pdhl(H,L,C,T,p.gio);return[L_('Đỉnh ngày trước',a,'bac'),L_('Đáy ngày trước',b,'bac'),L_('Đóng ngày trước',c,'bac')]}},
 piv:{ten:'Pivot Points (cổ điển, Fibonacci, Camarilla, Woodie)',nhom:'xu',khung:'gia',ts:[['kieu','Kiểu: 1 cổ điển, 2 Fibonacci, 3 Camarilla, 4 Woodie',1,1,1,4],['ky','Kỳ: 1 ngày, 2 tuần, 3 tháng',1,1,1,3],['gio','Giờ bắt đầu ngày (giờ UTC)',0,1,0,23]],
  mo:'Mức P, R1–R3, S1–S3 tính từ cao, thấp, đóng của kỳ trước (ngày, tuần hoặc tháng), vẽ bậc thang cho cả kỳ hiện tại. Hay dùng làm vùng phản ứng giá; không tự báo mua bán.',
  tinh:(H,L,C,O,p,V,T)=>{const kieu=Math.min(4,Math.max(1,Math.round(p.kieu))),k=Math.min(3,Math.max(1,Math.round(p.ky))),o=pivots(H,L,C,T,p.gio,kieu,k);
   return['P','R1','R2','R3','S1','S2','S3'].map((t,j)=>L_(t,o[j],'bac'))}},
 mtf:{ten:'Trung bình động khung lớn (MTF)',nhom:'xu',khung:'gia',ts:[['phut','Khung lớn (phút: 60 là H1, 240 là H4, 1440 là D1)',240,1,1,10080],['n','Chu kỳ',50,1],['loai','Loại: 1 EMA, 2 SMA',1,1,1,2],['gio','Giờ bắt đầu ngày (giờ UTC)',0,1,0,23]],
  mo:'EMA hoặc SMA tính trên nến của khung lớn hơn rồi vẽ lên khung đang xem, ví dụ EMA 50 H4 trên biểu đồ M15. Nến khung lớn đang chạy dùng giá hiện tại, nên giá trị cũ không bị vẽ lại.',
  tinh:(H,L,C,O,p,V,T)=>{const loai=Math.round(p.loai)===2?2:1;return[L_((loai===2?'SMA ':'EMA ')+p.n+' '+tenKhung(p.phut),maKhung(C,T,p.phut,p.gio,p.n,loai))]}},
 afib:{ten:'Auto Fibonacci (theo sóng ZigZag gần nhất)',nhom:'xu',khung:'gia',ts:[['pt','Độ đảo chiều tối thiểu (%)',.5,.05,.05]],
  mo:'Tự kẻ các mức Fibonacci 0; 23,6; 38,2; 50; 61,8; 78,6; 100% trên sóng ZigZag gần nhất. Sóng cuối còn tạm nên các mức đổi theo khi giá tạo đỉnh, đáy mới.',
  tinh:(H,L,C,O,p)=>{const o=autoFib(H,L,p.pt);return FIB.map((r,j)=>L_('Fib '+(r*100).toFixed(1).replace('.0',''),o[j],'bac'))}},
 // ---- khối lượng (tick volume MT5)
 vol:{ten:'Khối lượng (tick volume)',nhom:'kl',khung:'rieng',ts:[['n','Trung bình',20,1]],mo:'Cột khối lượng mỗi nến (xanh: nến tăng, đỏ: nến giảm) kèm đường trung bình. '+KLM,
  tinh:(H,L,C,O,p,V)=>{const v=coV(V,C.length)?V.map(x=>x==null?null:+x):nul(C.length);return[L_('KL',v,'kl'),L_('TB '+p.n,sma(v,p.n))]}},
 vwap:{ten:'VWAP (giá trung bình theo khối lượng trong ngày)',nhom:'kl',khung:'gia',ts:[['gio','Giờ bắt đầu ngày (giờ UTC)',0,1,0],['k','Dải độ lệch chuẩn (0 là tắt)',1,.5,0]],
  mo:'Giá điển hình (cao+thấp+đóng)/3 bình quân theo khối lượng từ đầu mỗi ngày; giá trên VWAP là bên mua đang trội trong ngày. '+KLM,
  tinh:(H,L,C,O,p,V,T)=>{const[m,a,b]=vwapf(H,L,C,V,T,p.gio,p.k);return[L_('VWAP',m),L_('VWAP trên',a),L_('VWAP dưới',b)]}},
 vwma:{ten:'Trung bình động theo khối lượng (VWMA)',nhom:'kl',khung:'gia',ts:[['n','Chu kỳ',20,1]],mo:'Trung bình giá đóng có trọng số là khối lượng của n nến. '+KLM,
  tinh:(H,L,C,O,p,V)=>{if(!coV(V,C.length))return[L_('VWMA '+p.n,nul(C.length))];const x=C.map((c,i)=>V[i]==null?null:c*V[i]);return[L_('VWMA '+p.n,hop(tong(x,p.n),tong(V.map(v=>v==null?null:+v),p.n),(a,b)=>b?a/b:null))]}},
 obv:{ten:'OBV (khối lượng cân bằng)',nhom:'kl',khung:'rieng',ts:[],mo:'Cộng khối lượng khi giá đóng tăng, trừ khi giảm; so độ dốc OBV với giá để thấy dòng tiền. '+KLM,tinh:(H,L,C,O,p,V)=>[L_('OBV',obvf(C,V))]},
 mfi:{ten:'MFI (chỉ số dòng tiền)',nhom:'kl',khung:'rieng',ts:[['n','Chu kỳ',14,1]],muc:[80,20],mo:'Giống RSI nhưng có tính khối lượng; trên 80 là mua quá mức, dưới 20 là bán quá mức. '+KLM,
  tinh:(H,L,C,O,p,V)=>[L_('MFI '+p.n,mfif(H,L,C,V,p.n))]},
 cmf:{ten:'Chaikin Money Flow (CMF)',nhom:'kl',khung:'rieng',ts:[['n','Chu kỳ',20,1]],muc:[0],mo:'Tổng khối lượng dòng tiền chia tổng khối lượng n nến; dương là áp lực mua, âm là áp lực bán. '+KLM,
  tinh:(H,L,C,O,p,V)=>{if(!coV(V,C.length))return[L_('CMF',nul(C.length))];return[L_('CMF',hop(tong(mfv(H,L,C,V),p.n),tong(V.map(v=>v==null?null:+v),p.n),(a,b)=>b?a/b:null))]}},
 efi:{ten:'Elder Force Index (EFI)',nhom:'kl',khung:'rieng',ts:[['n','Chu kỳ',13,1]],muc:[0],mo:'EMA của (giá đóng − giá đóng trước) × khối lượng; dương là lực mua trội, âm là lực bán trội. '+KLM,
  tinh:(H,L,C,O,p,V)=>{if(!coV(V,C.length))return[L_('EFI',nul(C.length))];return[L_('EFI '+p.n,ema(C.map((c,i)=>i&&V[i]!=null?(c-C[i-1])*V[i]:null),p.n))]}},
 ad:{ten:'Tích lũy, phân phối (A/D)',nhom:'kl',khung:'rieng',ts:[],mo:'Cộng dồn khối lượng dòng tiền Chaikin; A/D đi lên khi giá thường đóng gần đỉnh nến. '+KLM,
  tinh:(H,L,C,O,p,V)=>{if(!coV(V,C.length))return[L_('A/D',nul(C.length))];let s=0;return[L_('A/D',mfv(H,L,C,V).map(v=>v==null?null:(s+=v)))]}},
 // ---- dao động
 ppo:{ten:'PPO (dao động giá theo %)',nhom:'dao',khung:'rieng',ts:[['f','Nhanh',12,1],['s','Chậm',26,1],['t','Tín hiệu',9,1]],muc:[0],mo:'Như MACD nhưng tính theo % của EMA chậm, so được giữa các mức giá, các mã khác nhau.',
  tinh:(H,L,C,O,p)=>{const m=hop(ema(C,p.f),ema(C,p.s),(a,b)=>b?100*(a-b)/b:null),s=ema(m,p.t);return[L_('Cột',hop(m,s,(a,b)=>a-b),'cot'),L_('PPO',m),L_('Tín hiệu',s)]}},
 tsi:{ten:'TSI (chỉ số sức mạnh thật)',nhom:'dao',khung:'rieng',ts:[['r','Làm trơn dài',25,1],['s','Làm trơn ngắn',13,1],['g','Tín hiệu',13,1]],muc:[0],mo:'Động lượng làm trơn hai lần (William Blau); cắt đường tín hiệu hoặc mức 0 cho biết đổi chiều động lượng.',
  tinh:(H,L,C,O,p)=>{const d=C.map((c,i)=>i?c-C[i-1]:null),a=ema(ema(d,p.r),p.s),b=ema(ema(d.map(v=>v==null?null:Math.abs(v)),p.r),p.s),t=hop(a,b,(x,y)=>y?100*x/y:null);return[L_('TSI',t),L_('Tín hiệu',ema(t,p.g))]}},
 smi:{ten:'Stochastic Momentum Index (SMI)',nhom:'dao',khung:'rieng',ts:[['n','Chu kỳ',10,1],['a','Làm trơn 1',3,1],['b','Làm trơn 2',3,1],['g','Tín hiệu',10,1]],muc:[40,-40],
  mo:'Vị trí giá đóng so với điểm giữa của biên cao, thấp n nến, làm trơn hai lần; ít nhiễu hơn Stochastic.',
  tinh:(H,L,C,O,p)=>{const a=hh(H,p.n),b=ll(L,p.n),m=C.map((c,i)=>a[i]==null?null:c-(a[i]+b[i])/2),r=hop(a,b,(x,y)=>x-y),u=ema(ema(m,p.a),p.b),d=ema(ema(r,p.a),p.b),s=hop(u,d,(x,y)=>y?200*x/y:null);return[L_('SMI',s),L_('Tín hiệu',ema(s,p.g))]}},
 cmo:{ten:'Chande Momentum Oscillator (CMO)',nhom:'dao',khung:'rieng',ts:[['n','Chu kỳ',9,1]],muc:[50,-50],mo:'(Tổng nhịp tăng − tổng nhịp giảm) / tổng cả hai trong n nến, từ −100 đến 100.',
  tinh:(H,L,C,O,p)=>{const d=C.map((c,i)=>i?c-C[i-1]:null),u=tong(d.map(v=>v==null?null:Math.max(v,0)),p.n),x=tong(d.map(v=>v==null?null:Math.max(-v,0)),p.n);return[L_('CMO '+p.n,hop(u,x,(a,b)=>a+b?100*(a-b)/(a+b):0))]}},
 crsi:{ten:'Connors RSI',nhom:'dao',khung:'rieng',ts:[['a','RSI giá',3,1],['b','RSI chuỗi tăng giảm',2,1],['c','Hạng phần trăm',100,1]],muc:[90,10],
  mo:'Trung bình của RSI 3 kỳ, RSI của số nến tăng hoặc giảm liên tiếp, và hạng phần trăm của mức thay đổi hôm nay; dùng tìm nhịp quá đà ngắn hạn.',tinh:(H,L,C,O,p)=>[L_('CRSI',crsif(C,p.a,p.b,p.c))]},
 rvi:{ten:'Relative Vigor Index (RVI)',nhom:'dao',khung:'rieng',ts:[['n','Chu kỳ',10,1]],muc:[0],mo:'So giá đóng với giá mở trong biên độ nến: xu hướng tăng thì nến thường đóng cao hơn mở.',
  tinh:(H,L,C,O,p)=>{const r=hop(tong(swma(C.map((c,i)=>c-O[i])),p.n),tong(swma(H.map((h,i)=>h-L[i])),p.n),(a,b)=>b?a/b:null);return[L_('RVI',r),L_('Tín hiệu',swma(r))]}},
 bop:{ten:'Balance of Power (BOP)',nhom:'dao',khung:'rieng',ts:[['n','Làm trơn (1 là không)',14,1]],muc:[0],mo:'(Đóng − mở) / (cao − thấp): bên nào kiểm soát nến; làm trơn bằng trung bình n nến.',
  tinh:(H,L,C,O,p)=>[L_('BOP',sma(C.map((c,i)=>H[i]===L[i]?0:(c-O[i])/(H[i]-L[i])),p.n))]},
 dpo:{ten:'Detrended Price Oscillator (DPO)',nhom:'dao',khung:'rieng',ts:[['n','Chu kỳ',21,1]],muc:[0],mo:'Giá trừ đường trung bình đã lùi n/2+1 nến; bỏ xu hướng để thấy chu kỳ ngắn.',
  tinh:(H,L,C,O,p)=>{const m=sma(C,p.n),k=Math.floor(p.n/2)+1;return[L_('DPO',C.map((c,i)=>i<k||m[i-k]==null?null:c-m[i-k]))]}},
 kst:{ten:'Know Sure Thing (KST)',nhom:'dao',khung:'rieng',ts:[['g','Tín hiệu',9,1]],muc:[0],mo:'Tổng có trọng số của bốn ROC (10, 15, 20, 30) đã làm trơn (Martin Pring); đo động lượng nhiều chu kỳ.',
  tinh:(H,L,C,O,p)=>{const a=sma(rocn(C,10),10),b=sma(rocn(C,15),10),c=sma(rocn(C,20),10),d=sma(rocn(C,30),15),k=a.map((v,i)=>v==null||b[i]==null||c[i]==null||d[i]==null?null:v+2*b[i]+3*c[i]+4*d[i]);return[L_('KST',k),L_('Tín hiệu',sma(k,p.g))]}},
 copp:{ten:'Coppock Curve',nhom:'dao',khung:'rieng',ts:[['n','WMA',10,1],['a','ROC dài',14,1],['b','ROC ngắn',11,1]],muc:[0],mo:'WMA của tổng hai ROC; vốn dùng trên khung tháng để tìm đáy dài hạn.',
  tinh:(H,L,C,O,p)=>[L_('Coppock',wma(hop(rocn(C,p.a),rocn(C,p.b),(x,y)=>x+y),p.n))]},
 stc:{ten:'Schaff Trend Cycle (STC)',nhom:'dao',khung:'rieng',ts:[['f','Nhanh',23,1],['s','Chậm',50,1],['c','Chu kỳ',10,1],['k','Hệ số làm trơn',.5,.05,.05]],muc:[75,25],
  mo:'MACD đưa qua Stochastic hai lần, từ 0 đến 100; đổi chiều nhanh hơn MACD, nhưng hay nằm sát 0 hoặc 100.',tinh:(H,L,C,O,p)=>[L_('STC',stcf(C,p.f,p.s,p.c,p.k))]},
 ac:{ten:'Accelerator Oscillator (AC)',nhom:'dao',khung:'rieng',ts:[],muc:[0],mo:'Awesome Oscillator trừ trung bình 5 nến của nó (Bill Williams): đo động lượng đang tăng tốc hay chậm lại.',
  tinh:(H,L,C,O,p)=>{const g=H.map((h,i)=>(h+L[i])/2),a=hop(sma(g,5),sma(g,34),(x,y)=>x-y);return[L_('AC',hop(a,sma(a,5),(x,y)=>x-y),'cot')]}},
 rsipk:{ten:'RSI kèm phân kỳ',nhom:'cd',khung:'rieng',ts:[['n','Chu kỳ RSI',14,1],['l','Số nến bên trái',5,1],['r','Số nến bên phải',5,1]],muc:[70,30],
  mo:'RSI và mũi tên phân kỳ thường: giá tạo đáy thấp hơn mà RSI tạo đáy cao hơn (lên), hoặc giá đỉnh cao hơn mà RSI đỉnh thấp hơn (xuống). Đáy, đỉnh chỉ xác nhận sau số nến bên phải, nên mũi tên hiện trễ. Phân kỳ có thể kéo dài nhiều lần trước khi giá đảo chiều.',
  tinh:(H,L,C,O,p)=>{const[r,mk]=pkRsi(H,L,C,p.n,p.l,p.r);return[[...L_('RSI '+p.n,r),mk]]}},
 // ---- biến động
 sdev:{ten:'Độ lệch chuẩn',nhom:'bien',khung:'rieng',ts:[['n','Chu kỳ',20,1]],mo:'Độ lệch chuẩn của giá đóng trong n nến (đơn vị giá); tăng khi giá dao động mạnh.',tinh:(H,L,C,O,p)=>[L_('StdDev '+p.n,sd(C,p.n))]},
 hv:{ten:'Biến động lịch sử (HV, % mỗi nến)',nhom:'bien',khung:'rieng',ts:[['n','Chu kỳ',20,1]],mo:'Độ lệch chuẩn của lợi suất log giữa hai nến liền nhau, tính theo % cho mỗi nến của khung đang xem.',
  tinh:(H,L,C,O,p)=>[L_('HV '+p.n,sd(C.map((c,i)=>i&&C[i-1]>0&&c>0?Math.log(c/C[i-1]):null),p.n).map(v=>v==null?null:100*v))]},
 mass:{ten:'Mass Index',nhom:'bien',khung:'rieng',ts:[['n','Tổng',25,1]],muc:[27,26.5],mo:'Đo biên độ nến phình rồi co (Donald Dorsey); vượt 27 rồi rơi dưới 26,5 là dấu hiệu "đảo chiều phình" cổ điển.',
  tinh:(H,L,C,O,p)=>{const e1=ema(H.map((h,i)=>h-L[i]),9),e2=ema(e1,9);return[L_('Mass',tong(hop(e1,e2,(a,b)=>b?a/b:null),p.n))]}},};
Object.assign(LIB,HGR_OSS_EXT.entries(L_));
const NHOM={xu:'Xu hướng',dao:'Dao động',bien:'Biến động',kl:'Khối lượng (tick volume)',cd:'Cộng đồng nổi tiếng'},MAUS=['#2962ff','#ff6d00','#e91e63','#00897b','#8e24aa','#fbc02d','#43a047','#6d4c41','#00acc1','#f4511e'];
// ---------------------------------------------------------------- trạng thái cá nhân (lưu trong trình duyệt)
const CBKEY=window.HVD_CB_KEY||'so-cbcn1';
let S={ds:[],sao:['ema','rsi','macd','bb'],mau:{}};try{Object.assign(S,JSON.parse(localStorage.getItem(CBKEY)||'{}'))}catch(e){}
S.ds=(Array.isArray(S.ds)?S.ds:[]).filter(x=>x&&LIB[x.k]);let cbLuuLoi=false;const luu=()=>{try{localStorage.setItem(CBKEY,JSON.stringify(S));cbLuuLoi=false;return true}catch(e){cbLuuLoi=true;return false}};
const macDinh=k=>Object.fromEntries(LIB[k].ts.map(t=>[t[0],t[2]])),moiId=()=>Math.random().toString(36).slice(2,9);
function them(k,p){const n=S.ds.length;S.ds.push({id:moiId(),k,p:{...macDinh(k),...(p||{})},mau:MAUS[n%MAUS.length],an:false});luu();doi()}
// ---------------------------------------------------------------- vẽ lên biểu đồ (Lightweight Charts)
let SER=[],KH='',TINH=0,khoaDL='',lastSource=null,tickTimer=0,tickCost=0;
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
 const cs=B.D.candles,k=KBD+'|'+cs.length+'|'+cs[0][0]+'|'+cs[cs.length-1].join(',');if(k===khoaKieu&&PHU._source===cs)return;khoaKieu=k;PHU._source=cs;
 if(KBD==='coso'){const n=Math.min(200,cs.length),tb=cs.slice(-n).reduce((s,r)=>s+r[4],0)/n;       // mốc: giá đóng trung bình 200 nến gần nhất
  PHU.applyOptions({baseValue:{type:'price',price:tb},topLineColor:len,bottomLineColor:xuong,topFillColor1:'rgba(38,166,154,.28)',topFillColor2:'rgba(38,166,154,.03)',
   bottomFillColor1:'rgba(239,83,80,.03)',bottomFillColor2:'rgba(239,83,80,.28)'})}
 const ds=KBD==='ha'?heikin(cs):cs;
 CHART_RT.gui(PHU,cs.length,i=>{const r=ds[i];return KBD==='ha'||KBD==='thanh'?{time:r[0],open:r[1],high:r[2],low:r[3],close:r[4]}:{time:r[0],value:r[4]}},cs)}
const MOC=[];
function ve(){const B=window.BDCB&&window.BDCB();if(!B||!B.LW||!B.D||!B.D.candles||!B.D.candles.length)return;const LW=B.LW,c=LW.chart,LWC=window.LightweightCharts,P=B.P||{};
 try{kieuVe(B)}catch(e){console.warn('Dạng biểu đồ:',e)}
 for(const f of MOC)try{f(B)}catch(e){console.warn('Công cụ biểu đồ:',e)}           // bieu_do_them.py: nền phiên, hồ sơ khối lượng, thang giá, so sánh mã
 const bat=S.ds.filter(x=>!x.an),coBan=1+String(LW.khDao||'').split(',').filter(Boolean).length,
  kh=coBan+'|'+(LW.khDao||'')+'|'+bat.map(x=>x.id+x.k+JSON.stringify(x.p)+x.mau).join(';'),
  mat=SER.some(s=>{try{return!c.panes().some(pa=>pa.getSeries().includes(s.s))}catch(e){return true}});
 if(kh!==KH||mat){workerBo();goSach(c);try{for(let i=c.panes().length-1;i>=coBan;i--)c.removePane(i)}catch(e){}KH=kh;khoaDL='';let pn=coBan;
  for(const x of bat){const d=LIB[x.k],cs=d.khung==='rieng'?pn++:0,mau=[x.mau,'#ff6d00','#26a69a','#ef5350'];
   d.tinh([0],[0],[0],[0],x.p).forEach(([ten,,kieu],j)=>{const m=kieu==='tang'?'#26a69a':kieu==='giam'?'#ef5350':j===0?x.mau:mau[j%4],
     o={color:m,lineWidth:j===0?2:1,priceLineVisible:false,lastValueVisible:d.khung==='rieng'||j===0,title:d.khung==='rieng'?'':ten,crosshairMarkerVisible:kieu!=='cham'};
    let s;if(kieu==='cot'||kieu==='kl')s=c.addSeries(LWC.HistogramSeries,{priceLineVisible:false,lastValueVisible:false},cs);
    else s=c.addSeries(LWC.LineSeries,kieu==='dau'?{...o,lineVisible:false,pointMarkersVisible:false,lastValueVisible:false,crosshairMarkerVisible:false,title:''}:kieu==='cham'?{...o,lineVisible:false,pointMarkersVisible:true,pointMarkersRadius:1.6}:kieu==='bac'?{...o,lineType:1,lineStyle:2}:o,cs);
    SER.push({s,id:x.id,j,kieu,mau:m,mk:null});
    if(j===0&&d.muc)for(const v of d.muc)try{s.createPriceLine({price:v,color:P.mute||'#888',lineWidth:1,lineStyle:1,axisLabelVisible:true,title:''})}catch(e){}})}
  try{c.panes().forEach((pa,i)=>{if(i>=coBan)pa.setStretchFactor(.22)})}catch(e){}}
 const cs=B.D.candles,last=cs[cs.length-1],k=cs.length+'|'+cs[0][0]+'|'+last.join(',')+'|'+(B.D.vol||{})[last[0]]+'|'+KH,now=Date.now();
 if(k===khoaDL&&lastSource===cs)return;khoaDL=k;lastSource=cs;TINH=now;if(!bat.length)return;
 if(!mayTinh(B,bat)){
  const H=cs.map(r=>r[2]),Lo=cs.map(r=>r[3]),C=cs.map(r=>r[4]),O=cs.map(r=>r[1]),VM=B.D.vol||{},V=cs.map(r=>VM[r[0]]),T=cs.map(r=>r[0]);
  const items=[];for(const x of bat)try{items.push({id:x.id,k:x.k,out:LIB[x.k].tinh(H,Lo,C,O,x.p,V,T).map(o=>({values:o[1],start:0,markers:o[3]}))})}catch(e){console.warn('Chỉ báo '+x.k+':',e)}
  nhanKetQua(items,cs,cs.length)}
}
function nhanKetQua(items,cs,n){const LWC=window.LightweightCharts;
 for(const item of items)for(const it of SER.filter(s=>s.id===item.id)){const out=item.out[it.j];if(!out)continue;
  CHART_RT.gui(it.s,n,i=>{const r=cs[i],v=out.values[i-out.start];return v==null||!isFinite(v)?{time:r[0]}:{time:r[0],value:v,...(it.kieu==='cot'?{color:v>=0?'rgba(38,166,154,.6)':'rgba(239,83,80,.6)'}:it.kieu==='kl'?{color:r[4]>=r[1]?'rgba(38,166,154,.6)':'rgba(239,83,80,.6)'}:{})}},cs,!['zz','frac','rsipk','afib'].includes(item.k));
  if(out.markers&&LWC.createSeriesMarkers){if(!it.mk)it.mk=LWC.createSeriesMarkers(it.s,[]);it.mk.setMarkers(out.markers.filter(m=>m.i>=0&&m.i<n).slice(-300).map(m=>({time:cs[m.i][0],position:m.len?'belowBar':'aboveBar',color:m.len?'#26a69a':'#ef5350',shape:m.len?'arrowUp':'arrowDown',...(m.text?{text:m.text}:{})})))}}
}
// Same formulas run off the UI thread. Only one job plus the newest dirty state is retained.
let worker=null,workerFailed=false,workerTask=null,workerSerial=0,workerDirty=false,workerDone=null,workerCost=null,workerApplied=null;
function workerBo(){if(worker){worker.onmessage=null;worker.onerror=null;worker.terminate()}worker=null;workerTask=null;workerDirty=false;workerDone=null}
function mayTinh(B,bat){if(workerFailed||!window.Worker)return false;
 const cs=B.D.candles,c=B.LW.chart,epoch=B.D._chart_epoch;
 if(workerTask&&(workerTask.source!==cs||workerTask.config!==KH||workerTask.epoch!==epoch||workerTask.chart!==c))workerBo();
 if(workerTask){workerDirty=true;return true}
 if(!worker){try{worker=new Worker('/tinh/chi-bao-worker.js');worker.onmessage=e=>{const task=workerTask,msg=e.data;if(!task||msg.id!==task.id)return;workerTask=null;
   const B2=window.BDCB&&BDCB();if(B2&&B2.D&&B2.LW&&B2.LW.chart===task.chart&&B2.D.candles===task.source&&B2.D._chart_epoch===task.epoch&&KH===task.config){
    nhanKetQua(msg.items,task.source,msg.n);workerCost=msg.cost_ms;workerApplied=performance.now();workerDone={source:task.source,n:msg.n,config:KH};}
   if(workerDirty){workerDirty=false;khoaDL='';tick()}};
  worker.onerror=()=>{workerBo();workerFailed=true;khoaDL='';tick()}}
 catch(e){workerFailed=true;return false}}
 const from=workerDone&&workerDone.source===cs&&workerDone.config===KH&&cs.length>=workerDone.n&&cs.length-workerDone.n<=2?Math.max(0,workerDone.n-1):0;
 workerTask={id:++workerSerial,source:cs,config:KH,epoch,chart:c};
 try{worker.postMessage({id:workerTask.id,cs,vol:B.D.vol||{},specs:bat.map(x=>({id:x.id,k:x.k,p:x.p})),from})}
 catch(e){workerBo();workerFailed=true;return false}return true}
function tinhTrang(){return{mode:worker?'worker':workerFailed?'fallback':'idle',waiting:!!workerTask,compute_ms:workerCost,age_ms:workerApplied==null?null:performance.now()-workerApplied}}
addEventListener('chart-context-changing',()=>{workerBo();clearTimeout(tickTimer);tickTimer=0;khoaDL='';lastSource=null});
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')workerBo();else{khoaDL='';tick()}});
// Chỉ gom cập nhật chỉ báo: nến/Bid/Ask vẫn vẽ ở khung hình kế tiếp. Tránh tính cả lịch sử ở mỗi tick.
function tick(){if(tickTimer)return;const wait=Math.max(0,Math.max(16,Math.min(500,tickCost*4))-(Date.now()-TINH));
 tickTimer=setTimeout(()=>{tickTimer=0;if(document.visibilityState==='hidden')return;const t=performance.now();try{ve()}catch(e){console.warn('Chỉ báo realtime:',e)}tickCost=performance.now()-t},wait)}
function doi(){clearTimeout(tickTimer);tickTimer=0;KH+='*';ve();veDs()}
// số cuối (nến đã đóng) của các chỉ báo đang bật, mũi tên gần nhất và 60 nến, cho nút "AI đọc chỉ báo"
function tomTat(){const B=window.BDCB&&window.BDCB(),r={tf:'',ma:'XAUUSD',chi_bao:[],nen:[],lang:(document.documentElement.lang||'vi').slice(0,2)};if(!B||!B.D||!B.D.candles)return r;
 const D=B.D,cs=D.candles,n=D.live!=null&&D.live>=0&&D.live<cs.length?D.live:cs.length,c2=cs.slice(0,n),VM=D.vol||{};r.tf=D.tf||'';r.ma=D.khac_vang?D.ma:'XAUUSD';
 const H=c2.map(x=>x[2]),Lo=c2.map(x=>x[3]),C=c2.map(x=>x[4]),O=c2.map(x=>x[1]),V=c2.map(x=>VM[x[0]]),T=c2.map(x=>x[0]),so=v=>v==null||!isFinite(v)?null:+(+v).toPrecision(6);
 for(const x of S.ds.filter(v=>!v.an&&LIB[v.k])){let out;try{out=LIB[x.k].tinh(H,Lo,C,O,x.p,V,T)}catch(e){continue}const gt={},dau=[];
  for(const o of out){if(o[2]!=='dau')gt[o[0]]=[so(o[1][n-1]),so(o[1][n-2])];if(o[3])for(const m of o[3].filter(m=>m.i<n).slice(-3))dau.push({len:m.len,cach:n-1-m.i,...(m.patterns?{mau:m.patterns}:{})})}
  r.chi_bao.push({ten:LIB[x.k].ten,tham_so:x.p,gia_tri:gt,dau})}
 r.nen=c2.slice(-60).map(x=>x.slice(0,5));return r}
// ---------------------------------------------------------------- hộp chọn
const NEN=document.createElement('div');NEN.className='cbcn-nen';NEN.hidden=true;
NEN.innerHTML='<div class="cbcn" role="dialog" aria-modal="true" aria-label="Chỉ báo"><header><b>Chỉ báo</b><button type="button" class="ghost" data-dong>Đóng</button></header>'
 +'<div class="tim"><input type="search" placeholder="Tìm chỉ báo: EMA, RSI, MACD, Bollinger…" aria-label="Tìm chỉ báo"></div>'
 +'<div class="tab" role="group" aria-label="Nhóm chỉ báo"></div><div class="ds"></div></div>';
document.body.appendChild(NEN);let TAB='tat';const DS=NEN.querySelector('.ds'),TIM=NEN.querySelector('.tim input');
const TABS=[['tat','Tất cả'],['sao','Yêu thích'],['dung','Đang dùng'],['oss','Mã nguồn mở'],['xu','Xu hướng'],['dao','Dao động'],['bien','Biến động'],['kl','Khối lượng'],['cd','Cộng đồng nổi tiếng'],['co_san','Có sẵn của hệ thống'],['mau','Mẫu của tôi']];
function veTab(){NEN.querySelector('.tab').innerHTML=TABS.map(([k,n])=>`<button type="button" class="ghost" data-tab="${k}" aria-pressed="${TAB===k}">${n}${k==='dung'&&S.ds.length?' ('+S.ds.length+')':''}</button>`).join('')}
function hangLib(k){const d=LIB[k],sao=S.sao.includes(k),dem=S.ds.filter(x=>x.k===k).length;
 return`<div class="h"><button type="button" class="sao" data-sao="${k}" aria-pressed="${sao}" aria-label="Yêu thích" title="Yêu thích">${sao?'★':'☆'}</button>`
 +`<b>${esc(d.ten)}</b><button type="button" class="them" data-them="${k}">Thêm${dem?' ('+dem+')':''}</button><small>${esc(NHOM[d.nhom])} · ${d.khung==='gia'?'trên biểu đồ giá':'khung riêng'} · ${esc(d.mo)}</small></div>`}
function hangDung(x){const d=LIB[x.k];return`<div class="dg${x.an?' an':''}" data-id="${x.id}"><input type="color" value="${x.mau}" data-mau aria-label="Màu">`
 +`<b>${esc(d.ten)}</b><button type="button" class="ghost" data-an>${x.an?'Hiện':'Ẩn'}</button><button type="button" class="ghost" data-chep>Nhân bản</button><button type="button" class="ghost xoa" data-xoa>Xóa</button>`
 +`<div class="ts">${d.ts.map(([k,n,,b,mn,mx])=>`<label>${esc(n)}<input type="number" step="${b}" min="${mn??b}" max="${mx??1000}" data-ts="${k}" value="${x.p[k]}"></label>`).join('')}</div></div>`}
function veDs(){if(NEN.hidden)return;veTab();const q=TIM.value.trim().toLowerCase(),khop=k=>!q||(k+' '+LIB[k].ten+' '+LIB[k].mo).toLowerCase().includes(q);let h='';
 if(TAB==='dung')h=S.ds.length?S.ds.map(hangDung).join(''):'<p class="rong">Chưa dùng chỉ báo nào. Chọn ở tab Tất cả.</p>';
 else if(TAB==='co_san'){const ch=[...document.querySelectorAll('.chips .chip[data-k]')].filter(b=>!q||b.textContent.toLowerCase().includes(q));
  h='<p class="rong">Các chỉ báo hệ thống tính ở máy chủ (gồm vùng giá, lệnh, giờ tin). Bấm để bật hoặc tắt.</p>'+ch.map(b=>`<div class="h"><span></span><b>${esc(b.textContent)}</b>`
   +`<button type="button" class="them" data-chip="${esc(b.dataset.k)}">${b.getAttribute('aria-pressed')==='true'?'Đang bật · Tắt':'Bật'}</button></div>`).join('')}
 else if(TAB==='mau'){const ten=Object.keys(S.mau||{});h='<div class="mau"><input type="text" maxlength="40" placeholder="Tên mẫu, ví dụ: Lướt sóng M5" data-ten-mau><button type="button" data-luu-mau>Lưu bộ đang dùng</button></div>'
  +(ten.length?ten.map(t=>`<div class="h"><span></span><b>${esc(t)}</b><span><button type="button" class="them" data-ap="${esc(t)}">Áp dụng</button> <button type="button" class="ghost them" data-bo-mau="${esc(t)}">Xóa</button></span>`
   +`<small>${S.mau[t].map(x=>esc(LIB[x.k]?LIB[x.k].ten.split(' (')[0]+' '+Object.values(x.p).join('/'):'')).join(' · ')}</small></div>`).join(''):'<p class="rong">Chưa có mẫu nào. Bật các chỉ báo bạn hay dùng rồi lưu thành mẫu.</p>')}
 else{const ds=Object.keys(LIB).filter(k=>(TAB==='tat'||(TAB==='sao'?S.sao.includes(k):TAB==='oss'?LIB[k].nguon==='oss':LIB[k].nhom===TAB))&&khop(k));
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
 if(t.hasAttribute('data-mau'))x.mau=t.value;else if(t.dataset.ts){const q=LIB[x.k].ts.find(r=>r[0]===t.dataset.ts)||[],mn=q[4]??0,nguyen=q[3]>=1;let v=parseFloat(t.value);   // bước 1 là chu kỳ: làm tròn số nguyên
 if(isFinite(v)&&v>=mn&&(v>0||mn===0)){if(nguyen)v=Math.max(mn,Math.round(v));x.p[t.dataset.ts]=Math.min(v,q[5]??1000);t.value=x.p[t.dataset.ts]}else t.value=x.p[t.dataset.ts]}luu();doi()});
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
return{cauHinh:()=>({mau:S.mau,sao:S.sao}),loiLuu:()=>cbLuuLoi,ve,tick,mo,LIB,KIEU,tinhTrang,moc:MOC,tomTat,dung:k=>S.ds.some(x=>x.k===k&&!x.an),tinhLai:()=>{khoaDL='';ve()},dongBo:x=>{if(x&&x.mau&&typeof x.mau==='object'&&!Array.isArray(x.mau))S.mau=x.mau;if(x&&Array.isArray(x.sao))S.sao=x.sao.filter(k=>LIB[k]);const ok=luu();if(!NEN.hidden)veDs();return ok},_tinh:{ema,sma,rma,rsi,stoch,atr,supertrend,psar,adx,cci,aroon,wma,sd,heikin,kldb,linreg,squeeze,wavetrend,utbot,chandelier,qqe,fisher,alma,kama,mcginley}}})();
"""

from . import chi_bao_nguon_mo as _oss  # noqa: E402

NGUON_MO_NOTICE = _oss.NOTICE_HTML

# Derive worker formulas from the exact same source tested against pandas; no approximation or second implementation.
WORKER_JS = _oss.JS + JS[JS.index('const N=a=>'):JS.index('// ---------------------------------------------------------------- trạng thái cá nhân')] + r"""
self.onmessage=e=>{const task=e.data,t0=performance.now(),cs=task.cs,
 H=cs.map(r=>r[2]),L=cs.map(r=>r[3]),C=cs.map(r=>r[4]),O=cs.map(r=>r[1]),V=cs.map(r=>task.vol[r[0]]),T=cs.map(r=>r[0]),items=[];
 for(const x of task.specs){if(!LIB[x.k])continue;try{const start=['zz','frac','rsipk'].includes(x.k)?0:task.from;
  const out=LIB[x.k].tinh(H,L,C,O,x.p,V,T).map(o=>({values:o[1].slice(start),start,markers:o[3]?o[3].slice(-300):null}));items.push({id:x.id,k:x.k,out})}catch(e){items.push({id:x.id,k:x.k,out:[],error:'indicator_failed'})}}
 self.postMessage({id:task.id,n:cs.length,items,cost_ms:performance.now()-t0})};
"""

from . import chart_realtime as _rt  # noqa: E402

JS = _oss.JS + _rt.JS + JS

from . import bieu_do_them as _them  # noqa: E402 - công cụ thêm chạy ngay sau bộ chọn chỉ báo, cùng thẻ script

from . import ai_giai_thich_js as _gt  # noqa: E402 - hộp AI giải thích có bằng chứng, gắn cạnh nút "AI đọc chỉ báo"

from . import bieu_do_phat_lai as _pl  # noqa: E402 - phát lại nến, chạy sau công cụ thêm

CSS += _them.CSS + _gt.CSS + _pl.CSS
JS += _them.JS + _gt.JS + _pl.JS
