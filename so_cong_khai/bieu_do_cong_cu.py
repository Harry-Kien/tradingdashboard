# -*- coding: utf-8 -*-
"""Thanh công cụ vẽ theo nhóm và các công cụ vẽ thêm cho trang Biểu đồ (27/11/2026).

Bố cục học theo giao diện công khai của TradingView (đo bằng REA trên trang biểu đồ: cột công cụ khoảng 52 px, nút khoảng 38 px,
bảng bung ra dòng 40 px, tiêu đề nhóm viết hoa, phím tắt bên phải). Mã viết riêng cho webapp này, không lấy mã của TradingView.

- Cột dọc: Con trỏ, rồi mỗi NHÓM một nút (Đường, Fibonacci và Gann, Mẫu hình, Dự báo và đo, Hình học, Chữ và chú thích, Biểu tượng,
  và nhóm Yêu thích khi đã gắn sao). Nút nhóm mang biểu tượng của công cụ dùng gần nhất trong nhóm; bấm là cầm công cụ đó,
  bấm mũi tên nhỏ bên phải (hoặc chuột phải, hoặc chạm trên điện thoại) thì mở bảng bung ra.
- Bảng bung ra: ô tìm công cụ (tìm cả không dấu), tiêu đề từng phần, biểu tượng to, tên đầy đủ, phím tắt, nút sao để đưa vào Yêu thích.
- window.VEX: các công cụ vẽ thêm. Mỗi công cụ khai tên, biểu tượng, lời chỉ dẫn, cách tạo (kéo hai điểm, bấm một điểm `tao:1`,
  nhiều điểm `n`, chấm thứ ba tự đặt `c`, gõ chữ `chu`) và hàm `ve` trả về các chấm kéo được và hàm bắt chuột, đúng như các công cụ
  có sẵn trong bieu_do.py (veVe). bieu_do.py chỉ gộp VEX vào VEC/NHIEU và gọi VEX[k].ve; mọi thứ còn lại nằm ở đây.
- Chữ và biểu tượng chỉ vẽ lên canvas (fillText), không đi vào HTML; biểu tượng lưu bằng số thứ tự trong danh sách BT.
"""
from __future__ import annotations

CSS = r"""
.vetb.nhom{grid-template-columns:40px;gap:2px;padding:4px}
.vetb.nhom button{width:40px;height:38px;border-radius:7px}
.vetb.nhom svg{width:24px;height:24px;stroke-width:1.25}
.vetb.nhom [data-l]{height:32px}.vetb.nhom [data-l] svg{width:20px;height:20px}
.vetb.nhom .mo{grid-column:1/-1}
.vetb.nhom .vnh{position:relative;display:block;width:40px;height:38px}
.vetb.nhom .vnh::after{content:'';position:absolute;right:3px;bottom:3px;border:3px solid transparent;border-right-color:currentColor;border-bottom-color:currentColor;color:var(--mute);opacity:.6;pointer-events:none}
.vetb.nhom .vnh-mo{position:absolute;right:0;top:0;width:12px;height:38px;padding:0;border-radius:0 7px 7px 0;opacity:0;color:var(--ink2)}
.vetb.nhom .vnh-mo svg{width:7px;height:12px;stroke-width:1.6}
.vetb.nhom .vnh:hover .vnh-mo,.vetb.nhom .vnh-mo:focus-visible,.vetb.nhom .vnh-mo[aria-expanded=true]{opacity:1;background:var(--bg)}
.vetb.nhom .vnh-mo[aria-expanded=true]{color:var(--series)}
.vetb.nhom i{margin:3px 4px}
@media(pointer:coarse){.vetb.nhom .vnh-mo{opacity:.5}}
@media(max-width:640px){.vetb.nhom{grid-template-columns:36px}.vetb.nhom button,.vetb.nhom .vnh{width:36px;height:34px}.vetb.nhom .vnh-mo{height:34px;width:11px}.vetb.nhom svg{width:22px;height:22px}.vetb.nhom [data-l]{height:30px}}
.vetb.nhom[data-thu]{grid-template-columns:36px}
.vpop{position:absolute;z-index:25;width:310px;max-width:calc(100% - 64px);box-sizing:border-box;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:10px;box-shadow:0 12px 32px rgba(16,24,40,.24);padding:6px 0 8px;overflow-y:auto;overscroll-behavior:contain;font:14px Tahoma,'Segoe UI',Arial,sans-serif}
.vp-tim{position:sticky;top:-6px;z-index:1;background:var(--card);padding:4px 10px 6px}
.vp-tim input{width:100%;box-sizing:border-box;height:34px;border:1px solid var(--line);border-radius:7px;padding:0 10px;background:var(--bg);color:var(--ink);font:inherit;font-size:13.5px}
.vp-tim input:focus{outline:2px solid var(--series);outline-offset:-1px}
.vp-dau{padding:10px 16px 4px;font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--mute)}
.vp-dong{display:flex;align-items:center;margin:0 6px;border-radius:7px}
.vp-dong:hover{background:var(--bg)}
.vp-mi{flex:1;min-width:0;display:flex;align-items:center;gap:12px;min-height:40px;padding:0 8px;border:0;background:none;color:inherit;font:inherit;text-align:left;cursor:pointer;border-radius:7px}
.vp-mi svg{width:26px;height:26px;flex:none}
.vp-mi span{flex:1;min-width:0}
.vp-mi kbd{font:12px Tahoma,'Segoe UI',Arial,sans-serif;color:var(--mute);background:none;border:0;padding:0;white-space:nowrap}
.vp-mi[aria-current=true]{background:var(--ink);color:var(--card)}
.vp-mi[aria-current=true] kbd{color:inherit;opacity:.75}
.vp-mi:focus-visible,.vp-sao:focus-visible,.vp-e:focus-visible{outline:2px solid var(--series);outline-offset:-2px}
.vp-sao{flex:none;width:32px;height:32px;border:0;border-radius:6px;background:none;color:var(--mute);cursor:pointer;font-size:17px;line-height:1;opacity:0}
.vp-dong:hover .vp-sao,.vp-sao:focus-visible,.vp-sao[aria-pressed=true]{opacity:1}
.vp-sao[aria-pressed=true]{color:#e9a000}
@media(pointer:coarse){.vp-sao{opacity:.55}.vp-mi kbd{display:none}}
.vp-bt{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;padding:4px 10px 6px}
.vp-e{height:38px;border:0;border-radius:7px;background:none;font-size:22px;line-height:1;cursor:pointer}
.vp-e:hover{background:var(--bg)}.vp-e[aria-pressed=true]{background:color-mix(in srgb,var(--series) 18%,transparent)}
.vp-trong{padding:12px 16px;color:var(--mute);font-size:13px}
@media(max-width:640px){.vpop{width:auto;left:52px!important;right:8px}}
html.anh .vpop{display:none!important}
"""

JS = r"""
(()=>{
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const BT=['😀','😢','😡','😱','👍','👎','👀','🚀','🔥','⭐','💰','💎','🎯','⚠️','✅','❌','⏰','📌','📈','📉','🐂','🐻','🔔','💡','❓','❗','⚡','🏁'];
const FONT='12.5px Tahoma,"Segoe UI",Arial,sans-serif';
// ---------- trợ giúp vẽ
const L2=(X,a,b,c,d)=>{X.beginPath();X.moveTo(a,b);X.lineTo(c,d);X.stroke()};
const ext=(x1,y1,x2,y2,L)=>{const dx=x2-x1,dy=y2-y1,h=Math.hypot(dx,dy);return h?[x1+dx/h*L,y1+dy/h*L]:[x2,y2]};
const g2=(C,xa,ya,xb,yb)=>({nut:[['a',xa,ya],['b',xb,yb]],trong:(x,yy)=>C.doan(xa,ya,xb,yb,x,yy)<=6});
const trongHop=(r,x,yy,m=4)=>!!r&&x>=r[0]-m&&x<=r[0]+r[2]+m&&yy>=r[1]-m&&yy<=r[1]+r[3]+m;
const pc=(C,h,k)=>{const q=h[k];if(!q)return null;const x=C.vx(q.t),y=C.y(q.p);return x==null||y==null?null:[x,y]};
const dauSo=(C,d)=>(d>=0?'+':'−')+C.fp(Math.abs(d));
const thayDoi=(C,a,b)=>{const d=b.p-a.p;return dauSo(C,d)+' ('+(d>=0?'+':'−')+C.f2(Math.abs(b.p/a.p-1)*100)+'%)'+(C.atr?' · '+C.f2(Math.abs(d)/C.atr)+' ATR':'')};
const soNen=(C,a,b)=>Math.round(Math.abs(C.ix(b.t)-C.ix(a.t)))+' nến · '+C.tg(b.t-a.t);
const muiTen=(X,x1,y1,x2,y2,L=11)=>{const g=Math.atan2(y2-y1,x2-x1);X.beginPath();X.moveTo(x2,y2);X.lineTo(x2-L*Math.cos(g-.42),y2-L*Math.sin(g-.42));X.lineTo(x2-L*Math.cos(g+.42),y2-L*Math.sin(g+.42));X.closePath();X.fill()};
const donVi=LW=>{try{return Math.abs(LW.nen.coordinateToPrice(0)-LW.nen.coordinateToPrice(40))||1}catch(e){return 1}};
const pip=(ps,x,y)=>{let r=false;for(let i=0,j=ps.length-1;i<ps.length;j=i++){const[xi,yi]=ps[i],[xj,yj]=ps[j];if((yi>y)!==(yj>y)&&x<(xj-xi)*(y-yi)/((yj-yi)||1e-9)+xi)r=!r}return r};
const rr=(X,x,y,w,h,r)=>{X.beginPath();X.moveTo(x+r,y);X.arcTo(x+w,y,x+w,y+h,r);X.arcTo(x+w,y+h,x,y+h,r);X.arcTo(x,y+h,x,y,r);X.arcTo(x,y,x+w,y,r);X.closePath()};
const dongChu=(X,t,maxW)=>{X.save();X.font=FONT;const w=String(t||'').split(/\s+/).filter(Boolean),r=[];let s='';for(const x of w){const th=s?s+' '+x:x;if(s&&X.measureText(th).width>maxW){r.push(s);s=x}else s=th}if(s)r.push(s);X.restore();return r.slice(0,6)};
// đo hộp chữ: (x,y) là góc trên trái, hoặc tâm ngang (giua) / mép dưới (duoi); giữ trong khung vẽ
const doHop=(C,ls,x,y,o={})=>{const X=C.X;X.save();X.font=FONT;const pad=o.pad==null?7:o.pad,w=Math.max(12,...ls.map(l=>X.measureText(l).width))+pad*2,h=ls.length*17+pad*2-3;X.restore();
 let x0=o.giua?x-w/2:x,y0=o.duoi?y-h:y;x0=Math.max(2,Math.min(x0,C.pw-w-2));y0=Math.max(2,Math.min(y0,C.ph-h-2));return[x0,y0,w,h,pad]};
const veHop=(C,ls,r,o)=>{const X=C.X,[x0,y0,w,h,pad]=r;X.save();X.setLineDash([]);X.globalAlpha=o.nenA==null?.95:o.nenA;X.fillStyle=o.nen;rr(X,x0,y0,w,h,6);X.fill();X.globalAlpha=1;
 if(o.vien){X.strokeStyle=o.vien;X.lineWidth=o.sel?2:1;rr(X,x0+.5,y0+.5,w-1,h-1,6);X.stroke()}X.font=FONT;X.fillStyle=o.mau;X.textAlign='left';X.textBaseline='alphabetic';ls.forEach((l,i)=>X.fillText(l,x0+pad,y0+pad+11+i*17));X.restore();return r};
const hopChu=(C,ls,x,y,o)=>veHop(C,ls,doHop(C,ls,x,y,o),o);
const rt=(C,p,a,b,c,d)=>{if(p.length<=Math.max(a,b,c,d))return'';const m=Math.abs(p[a].p-p[b].p);return m?C.f2(Math.abs(p[c].p-p[d].p)/m):''};
const neoTl=(X,ps,C,col,i,j,t)=>{if(!t||ps.length<=Math.max(i,j))return;X.save();X.setLineDash([4,3]);X.lineWidth=1;X.globalAlpha=.75;L2(X,ps[i][0],ps[i][1],ps[j][0],ps[j][1]);X.restore();C.chu(t,(ps[i][0]+ps[j][0])/2-10,(ps[i][1]+ps[j][1])/2,col)};
const keoDai=(X,p,q,xe)=>{const dx=q[0]-p[0];if(!dx)return;X.save();X.setLineDash([5,4]);X.lineWidth=1;X.globalAlpha=.8;L2(X,p[0],p[1],xe,p[1]+(q[1]-p[1])/dx*(xe-p[0]));X.restore()};
const tim=(cs,t)=>{let a=0,b=cs.length-1;if(b<0)return-1;while(a<b){const m=(a+b+1)>>1;if(cs[m][0]<=t)a=m;else b=m-1}return a};
// công cụ nhiều điểm: đường nối các điểm, nhãn từng điểm (bỏ điểm đang theo chuột), thêm phần vẽ riêng trước/sau
const nhieu=(nh,them={})=>function(h,C,sel,col){const X=C.X,ps=(h.pts||[]).map(q=>[C.vx(q.t),C.y(q.p)]);if(ps.length<2||ps.some(q=>q[0]==null||q[1]==null))return null;
 if(them.truoc)them.truoc(X,ps,h,C,col);X.beginPath();ps.forEach((q,i)=>i?X.lineTo(q[0],q[1]):X.moveTo(q[0],q[1]));X.stroke();if(them.sau)them.sau(X,ps,h,C,col);
 const dang=C.VE.tam===h;if(nh)ps.forEach((q,i)=>{if(nh[i]==null||(dang&&i===ps.length-1&&i>0))return;const nb=h.pts[i+1]||h.pts[i-1],tren=nb?h.pts[i].p>=nb.p:true;C.chu(nh[i],q[0]-3,tren?q[1]-8:q[1]+17,col)});
 return{nut:ps.map((q,i)=>['p'+i,q[0],q[1]]),trong:(x,yy)=>ps.some((q,i)=>i&&C.doan(ps[i-1][0],ps[i-1][1],q[0],q[1],x,yy)<=6)}};
const toTamGiac=(X,ps,col,ds)=>{X.save();X.globalAlpha=.08;X.fillStyle=col;for(const d of ds){if(d.some(i=>!ps[i]))continue;X.beginPath();d.forEach((i,j)=>j?X.lineTo(ps[i][0],ps[i][1]):X.moveTo(ps[i][0],ps[i][1]));X.closePath();X.fill()}X.restore()};
const cBa=h=>({t:h.b.t+Math.round((h.b.t-h.a.t)/2),p:h.b.p-(h.b.p-h.a.p)*.6});
// chĩa ba: gốc A (Andrews), nửa giá A–B (Schiff), giữa A–B cả giá và thời gian (Schiff cải tiến); 'trong' thêm hai đường giữa trung tuyến và răng
const chiaVe=kieu=>function(h,C,sel,col,xa,ya,xb,yb){const X=C.X,q=pc(C,h,'c');if(!q){L2(X,xa,ya,xb,yb);return g2(C,xa,ya,xb,yb)}const[xc,yc]=q;
 let ox=xa,oy=ya;if(kieu==='schiff')oy=(ya+yb)/2;else if(kieu==='schiffs'){ox=(xa+xb)/2;oy=(ya+yb)/2}
 const mx=(xb+xc)/2,my=(yb+yc)/2,dx=mx-ox,dy=my-oy,he=(dx||dy)?(C.pw+C.ph)*3/Math.hypot(dx,dy):0,ex=dx*he,ey=dy*he;
 X.save();X.globalAlpha=.06;X.fillStyle=col;X.beginPath();X.moveTo(xb,yb);X.lineTo(xb+ex,yb+ey);X.lineTo(xc+ex,yc+ey);X.lineTo(xc,yc);X.closePath();X.fill();X.restore();
 const ds=[[ox,oy,mx+ex,my+ey],[xb,yb,xb+ex,yb+ey],[xc,yc,xc+ex,yc+ey]];X.beginPath();for(const s of ds){X.moveTo(s[0],s[1]);X.lineTo(s[2],s[3])}X.stroke();
 if(kieu==='trong'){X.save();X.strokeStyle=C.P.mute;X.lineWidth=1;X.setLineDash(C.veNd(h));for(const[px,py]of[[(xb+mx)/2,(yb+my)/2],[(xc+mx)/2,(yc+my)/2]]){L2(X,px,py,px+ex,py+ey);ds.push([px,py,px+ex,py+ey])}X.restore()}
 X.save();X.setLineDash([3,3]);X.lineWidth=1;X.beginPath();X.moveTo(xb,yb);X.lineTo(xc,yc);if(ox!==xa||oy!==ya){X.moveTo(xa,ya);X.lineTo(xb,yb)}X.stroke();X.restore();
 return{nut:[['a',xa,ya],['b',xb,yb],['c',xc,yc]],trong:(x,yy)=>ds.some(s=>C.doan(s[0],s[1],s[2],s[3],x,yy)<=6)||C.doan(xb,yb,xc,yc,x,yy)<=6}};

const VEX={
 ttin:{ten:'Đường thông tin',d:'M3 14L13 4M3 14m-1.5 0a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0M13 4m-1.5 0a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0M10 11h7v5h-7z',goi:'Kéo từ điểm đầu tới điểm cuối; hộp bên cạnh ghi mức thay đổi giá, phần trăm, số nến, thời gian và góc',
  ve(h,C,sel,col,xa,ya,xb,yb){const X=C.X;L2(X,xa,ya,xb,yb);const goc=Math.round(Math.atan2(ya-yb,xb-xa)*180/Math.PI),
   r=hopChu(C,[thayDoi(C,h.a,h.b),soNen(C,h.a,h.b),'Góc '+goc+'°'],xb+12,yb-26,{nen:C.P.bg,mau:C.P.fg,vien:col,sel});
   return{nut:[['a',xa,ya],['b',xb,yb]],trong:(x,yy)=>C.doan(xa,ya,xb,yb,x,yy)<=6||trongHop(r,x,yy)}}},
 mrong:{ten:'Đường mở rộng',d:'M1 16L17 2M6.5 11.5m-1.4 0a1.4 1.4 0 1 0 2.8 0a1.4 1.4 0 1 0-2.8 0M11.5 6.5m-1.4 0a1.4 1.4 0 1 0 2.8 0a1.4 1.4 0 1 0-2.8 0',goi:'Kéo qua hai điểm; đường tự kéo dài về cả hai phía',
  ve(h,C,sel,col,xa,ya,xb,yb){const L=(C.pw+C.ph)*3,[x1,y1]=ext(xa,ya,xb,yb,L),[x0,y0]=ext(xb,yb,xa,ya,L);L2(C.X,x0,y0,x1,y1);return{nut:[['a',xa,ya],['b',xb,yb]],trong:(x,yy)=>C.doan(x0,y0,x1,y1,x,yy)<=6}}},
 goc:{ten:'Góc xu hướng',d:'M3 15L15 5M3 15h13M9 15a6 6 0 0 0-1.4-3.9',goi:'Kéo từ điểm gốc theo hướng xu hướng; số độ hiện cạnh cung',
  ve(h,C,sel,col,xa,ya,xb,yb){const X=C.X;L2(X,xa,ya,xb,yb);const s=xb>=xa?0:Math.PI,t=Math.atan2(yb-ya,xb-xa);let d=t-s;while(d>Math.PI)d-=2*Math.PI;while(d<=-Math.PI)d+=2*Math.PI;
   X.save();X.lineWidth=1;X.setLineDash([4,3]);L2(X,xa,ya,xa+(xb>=xa?70:-70),ya);X.setLineDash([]);X.beginPath();X.arc(xa,ya,34,s,t,d<0);X.stroke();X.restore();
   const deg=Math.round(-d*180/Math.PI);C.chu(deg+'°',xa+(xb>=xa?40:-66),ya+(deg>=0?-8:16),col);return g2(C,xa,ya,xb,yb)}},
 hoiquy:{ten:'Xu hướng hồi quy',d:'M2 12L16 5M2 15.5L16 8.5M2 8.5L16 1.5',goi:'Kéo từ nến đầu tới nến cuối; đường giữa là hồi quy tuyến tính của giá đóng cửa, hai biên cách 2 độ lệch chuẩn',
  ve(h,C,sel,col,xa,ya,xb,yb){const X=C.X,cs=C.cs,n=cs.length;let i0=Math.round(C.ix(h.a.t)),i1=Math.round(C.ix(h.b.t));if(i0>i1){const t=i0;i0=i1;i1=t}i0=Math.max(0,i0);i1=Math.min(n-1,i1);
   if(i1-i0<2){L2(X,xa,ya,xb,yb);return g2(C,xa,ya,xb,yb)}
   let sx=0,sy=0,sxy=0,sxx=0;const m=i1-i0+1;for(let i=i0;i<=i1;i++){const v=cs[i][4];sx+=i;sy+=v;sxy+=i*v;sxx+=i*i}const k=(m*sxy-sx*sy)/((m*sxx-sx*sx)||1),b0=(sy-k*sx)/m;
   let ss=0;for(let i=i0;i<=i1;i++){const r=cs[i][4]-(k*i+b0);ss+=r*r}const sd=2*Math.sqrt(ss/m),X0=C.ts.logicalToCoordinate(i0),X1=C.ts.logicalToCoordinate(i1),Y=(i,o)=>C.y(k*i+b0+o),
    ys=[Y(i0,0),Y(i1,0),Y(i0,sd),Y(i1,sd),Y(i0,-sd),Y(i1,-sd)];if(X0==null||X1==null||ys.some(v=>v==null))return null;
   X.save();X.globalAlpha=.07;X.fillStyle=col;X.beginPath();X.moveTo(X0,ys[2]);X.lineTo(X1,ys[3]);X.lineTo(X1,ys[5]);X.lineTo(X0,ys[4]);X.closePath();X.fill();X.restore();
   L2(X,X0,ys[0],X1,ys[1]);X.save();X.lineWidth=C.veLw(h,0);X.setLineDash([6,4]);L2(X,X0,ys[2],X1,ys[3]);L2(X,X0,ys[4],X1,ys[5]);X.restore();C.chu('±2σ',X1+4,ys[3]-4,col);
   return{nut:[['a',X0,ys[0]],['b',X1,ys[1]]],trong:(x,yy)=>[[0,1],[2,3],[4,5]].some(([p,q])=>C.doan(X0,ys[p],X1,ys[q],x,yy)<=6)}}},
 phang:{ten:'Mặt phẳng đỉnh/đáy',d:'M2 4h14M2 14L16 7',goi:'Kéo đường xu hướng; đường nằm ngang kéo lên xuống bằng chấm ở giữa',c:(h,LW)=>({t:h.b.t,p:h.b.p+((h.b.p-h.a.p)||donVi(LW))*.6}),
  ve(h,C,sel,col,xa,ya,xb,yb){const X=C.X,yc=h.c?C.y(h.c.p):null;if(yc==null){L2(X,xa,ya,xb,yb);return g2(C,xa,ya,xb,yb)}
   X.save();X.globalAlpha=.08;X.fillStyle=col;X.beginPath();X.moveTo(xa,ya);X.lineTo(xb,yb);X.lineTo(xb,yc);X.lineTo(xa,yc);X.closePath();X.fill();X.restore();
   X.beginPath();X.moveTo(xa,ya);X.lineTo(xb,yb);X.moveTo(xa,yc);X.lineTo(xb,yc);X.stroke();
   return{nut:[['a',xa,ya],['b',xb,yb],['c',(xa+xb)/2,yc]],trong:(x,yy)=>C.doan(xa,ya,xb,yb,x,yy)<=6||C.doan(xa,yc,xb,yc,x,yy)<=6}}},
 roirac:{ten:'Kênh rời rạc',d:'M2 4l14 4M2 14l14-4',goi:'Kéo đường thứ nhất; đường thứ hai dốc ngược lại, kéo chấm ở đầu để chỉnh',c:(h,LW)=>({t:h.a.t,p:h.a.p-((h.b.p-h.a.p)||donVi(LW))*.8}),
  ve(h,C,sel,col,xa,ya,xb,yb){const X=C.X,yc=h.c?C.y(h.c.p):null;if(yc==null){L2(X,xa,ya,xb,yb);return g2(C,xa,ya,xb,yb)}const y2=yc-(yb-ya);
   X.save();X.globalAlpha=.08;X.fillStyle=col;X.beginPath();X.moveTo(xa,ya);X.lineTo(xb,yb);X.lineTo(xb,y2);X.lineTo(xa,yc);X.closePath();X.fill();X.restore();
   X.beginPath();X.moveTo(xa,ya);X.lineTo(xb,yb);X.moveTo(xa,yc);X.lineTo(xb,y2);X.stroke();
   return{nut:[['a',xa,ya],['b',xb,yb],['c',xa,yc]],trong:(x,yy)=>C.doan(xa,ya,xb,yb,x,yy)<=6||C.doan(xa,yc,xb,y2,x,yy)<=6}}},
 schiff:{ten:'Schiff Pitchfork',d:'M2 12L16 4M5 16l11-8M5 10l7-7M2 12h3',goi:'Kéo từ điểm gốc A tới đỉnh hoặc đáy B; chấm C tự đặt. Gốc trung tuyến dời tới nửa khoảng giá A–B',c:cBa,ve:chiaVe('schiff')},
 schiffs:{ten:'Schiff Pitchfork cải tiến',d:'M4 12L16 4M6 16l10-8M4 9l7-6M2 14l2-2',goi:'Như Schiff, nhưng gốc trung tuyến nằm giữa A và B cả về giá lẫn thời gian',c:cBa,ve:chiaVe('schiffs')},
 chiatr:{ten:'Pitchfork có đường bên trong',d:'M2 14L16 4M5 16l11-8M2 10l8-8M3.5 12L15 4',goi:'Như Pitchfork Andrews, thêm hai đường nằm giữa trung tuyến và hai răng',c:cBa,ve:chiaVe('trong')},
 fibtgx:{ten:'Fibonacci thời gian theo xu hướng',d:'M2 15l4-9 4 5M10 2v14M13 2v14M16 2v14',goi:'Kéo theo nhịp từ A tới B; chấm C tự đặt. Các đường dọc tính từ C theo 0,382 / 0,618 / 1 / 1,618… lần độ dài nhịp',
  c:h=>({t:h.b.t+Math.round((h.b.t-h.a.t)/2),p:h.a.p}),
  ve(h,C,sel,col,xa,ya,xb,yb){const X=C.X,q=pc(C,h,'c');X.save();X.lineWidth=1;X.strokeStyle=C.P.mute;X.setLineDash([4,3]);X.beginPath();X.moveTo(xa,ya);X.lineTo(xb,yb);if(q)X.lineTo(q[0],q[1]);X.stroke();X.restore();
   if(!q)return g2(C,xa,ya,xb,yb);const ic=C.ix(h.c.t),u=C.ix(h.b.t)-C.ix(h.a.t),F=[0,.382,.5,.618,1,1.382,1.618,2,2.618,3,4.236],xs=[];
   X.save();X.setLineDash(C.veNd(h));for(const f of F){const xx=C.ts.logicalToCoordinate(ic+u*f);if(xx==null||xx<-2||xx>C.pw+2)continue;const Xv=Math.round(xx)+.5,dam=f===1||f===1.618;
    X.strokeStyle=dam?col:C.P.mute;X.lineWidth=C.veLw(h,dam);L2(X,Xv,0,Xv,C.ph);C.chu(String(f).replace('.',','),Xv+3,14,dam?col:C.P.mute);xs.push(Xv)}X.restore();
   return{nut:[['a',xa,ya],['b',xb,yb],['c',q[0],q[1]]],trong:(x,yy)=>xs.some(v=>Math.abs(x-v)<=4)||C.doan(xa,ya,xb,yb,x,yy)<=6}}},
 fibxoan:{ten:'Xoắn ốc Fibonacci',d:'M9 9a1.5 1.5 0 0 1 1.5 1.5a3 3 0 0 1-3 3a4.5 4.5 0 0 1-4.5-4.5a6 6 0 0 1 6-6a7.5 7.5 0 0 1 7.5 7.5',goi:'Kéo từ tâm ra điểm thứ hai; xoắn ốc vàng đi qua điểm đó',
  ve(h,C,sel,col,xa,ya,xb,yb){const X=C.X,r=Math.hypot(xb-xa,yb-ya)||1,a0=Math.atan2(yb-ya,xb-xa),F=1.6180339887,ps=[];
   for(let t=-6*Math.PI;t<=2.5*Math.PI;t+=.08){const q=r*Math.pow(F,t/(Math.PI/2));if(q>(C.pw+C.ph)*2)break;ps.push([xa+q*Math.cos(a0+t),ya+q*Math.sin(a0+t)])}
   X.beginPath();ps.forEach((p,i)=>i?X.lineTo(p[0],p[1]):X.moveTo(p[0],p[1]));X.stroke();X.save();X.setLineDash([4,3]);X.lineWidth=1;X.strokeStyle=C.P.mute;L2(X,xa,ya,xb,yb);X.restore();
   return{nut:[['a',xa,ya],['b',xb,yb]],trong:(x,yy)=>C.doan(xa,ya,xb,yb,x,yy)<=6||ps.some((p,i)=>i&&C.doan(ps[i-1][0],ps[i-1][1],p[0],p[1],x,yy)<=5)}}},
 gannv:{ten:'Hình vuông Gann',d:'M3 3h12v12H3zM3 15L15 3M3 3l12 12M3 9a6 6 0 0 1 6 6',goi:'Kéo từ một góc; hình luôn vuông trên màn hình, có lưới phần tư, hai đường chéo và các cung',
  ve(h,C,sel,col,xa,ya,xb,yb){const X=C.X,dx=xb-xa,dy=yb-ya,s=Math.max(Math.abs(dx),Math.abs(dy))||1,sx=dx<0?-1:1,sy=dy<0?-1:1,x1=xa+sx*s,y1=ya+sy*s,x0=Math.min(xa,x1),y0=Math.min(ya,y1);
   X.save();X.globalAlpha=.05;X.fillStyle=col;X.fillRect(x0,y0,s,s);X.restore();X.strokeRect(x0+.5,y0+.5,s,s);
   X.save();X.lineWidth=1;X.strokeStyle=C.P.mute;X.setLineDash(C.veNd(h));X.beginPath();for(const f of[.25,.5,.75]){X.moveTo(x0,y0+s*f);X.lineTo(x0+s,y0+s*f);X.moveTo(x0+s*f,y0);X.lineTo(x0+s*f,y0+s)}X.stroke();
   X.strokeStyle=col;X.setLineDash([]);X.beginPath();X.moveTo(xa,ya);X.lineTo(x1,y1);X.moveTo(xa,y1);X.lineTo(x1,ya);X.stroke();
   const g0=sx>0?0:Math.PI,g1=sy>0?Math.PI/2:-Math.PI/2;X.beginPath();for(const f of[.5,1]){X.moveTo(xa+sx*s*f,ya);X.arc(xa,ya,s*f,g0,g1,sx*sy<0)}X.stroke();X.restore();
   return{nut:[['a',xa,ya],['b',xb,yb]],trong:(x,yy)=>x>=x0-3&&x<=x0+s+3&&yy>=y0-3&&yy<=y0+s+3}}},
 abcd:{ten:'Mẫu hình ABCD',d:'M2 14l4-9 4 5 6-8',goi:'Bấm lần lượt 4 điểm A, B, C, D; tỷ lệ BC/AB và CD/BC tự hiện',n:4,
  ve:nhieu(['A','B','C','D'],{sau:(X,ps,h,C,col)=>{neoTl(X,ps,C,col,0,2,rt(C,h.pts,0,1,1,2));neoTl(X,ps,C,col,1,3,rt(C,h.pts,1,2,2,3))}})},
 cypher:{ten:'Mẫu hình Cypher',d:'M1 12l4-8 3 5 4-7 5 11M1 12l7-3',goi:'Bấm lần lượt 5 điểm X, A, B, C, D; tỷ lệ AB/XA, XC/XA và CD/XC tự hiện',n:5,
  ve:nhieu(['X','A','B','C','D'],{truoc:(X,ps,h,C,col)=>toTamGiac(X,ps,col,[[0,1,2],[2,3,4]]),
   sau:(X,ps,h,C,col)=>{neoTl(X,ps,C,col,0,2,rt(C,h.pts,0,1,1,2));neoTl(X,ps,C,col,1,3,rt(C,h.pts,0,1,0,3));neoTl(X,ps,C,col,2,4,rt(C,h.pts,0,3,3,4))}})},
 elltg:{ten:'Sóng tam giác Elliott (ABCDE)',d:'M1 4l3 10 3-7 3 5 3-3 3 2',goi:'Bấm lần lượt 6 điểm: gốc, A, B, C, D, E',n:6,
  ve:nhieu([null,'(A)','(B)','(C)','(D)','(E)'],{sau:(X,ps)=>{if(ps.length>=5){const xe=ps[ps.length-1][0]+30;keoDai(X,ps[1],ps[3],xe);keoDai(X,ps[2],ps[4],xe)}}})},
 ellwxy:{ten:'Sóng điều chỉnh kép Elliott (WXY)',d:'M2 4l5 9 4-5 5 7',goi:'Bấm lần lượt 4 điểm: gốc, W, X, Y',n:4,ve:nhieu([null,'(W)','(X)','(Y)'])},
 ellwxyxz:{ten:'Sóng điều chỉnh ba Elliott (WXYXZ)',d:'M1 4l3 8 3-4 3 6 3-4 4 6',goi:'Bấm lần lượt 6 điểm: gốc, W, X, Y, X, Z',n:6,ve:nhieu([null,'(W)','(X)','(Y)','(X)','(Z)'])},
 ellcheo:{ten:'Sóng chéo Elliott (nêm)',d:'M1 15l3-5 2 2 4-7 2 3 5-6M4 10L16 3M6 12l10-5',goi:'Bấm lần lượt 6 điểm: 0, 1, 2, 3, 4, 5; hai cạnh nêm tự kẻ',n:6,
  ve:nhieu(['0','1','2','3','4','5'],{sau:(X,ps)=>{if(ps.length>=5){const xe=ps[ps.length-1][0]+30;keoDai(X,ps[1],ps[3],xe);keoDai(X,ps[2],ps[4],xe)}}})},
 chuky:{ten:'Đường chu kỳ',d:'M3 2v14M8 2v14M13 2v14M3 9h10',goi:'Kéo từ nến đầu tới nến cuối của một chu kỳ; các đường dọc lặp lại cùng khoảng cách',
  ve(h,C,sel,col,xa,ya,xb){const X=C.X,ia=C.ix(h.a.t),u=C.ix(h.b.t)-ia,xs=[];let vr=null;try{vr=C.ts.getVisibleLogicalRange()}catch(e){}
   X.save();X.setLineDash(C.veNd(h));for(let k=0;k<400;k++){const l=ia+u*k;if(vr&&(l>vr.to+1||l<vr.from-1)&&k>1)break;const xx=C.ts.logicalToCoordinate(l);if(xx!=null){const Xv=Math.round(xx)+.5;X.strokeStyle=k<2?col:C.P.mute;X.lineWidth=C.veLw(h,k<2);L2(X,Xv,0,Xv,C.ph);xs.push(Xv)}if(Math.abs(u)<.5)break}X.restore();
   return{nut:[['a',xa,ya],['b',xb,ya]],trong:x=>xs.some(v=>Math.abs(x-v)<=4)}}},
 sin:{ten:'Đường hình sin',d:'M1 9c2-7 4-7 6 0s4 7 6 0 3-5 4-3',goi:'Kéo từ một đỉnh tới đáy kế tiếp; sóng lặp lại trên cả biểu đồ',
  ve(h,C,sel,col,xa,ya,xb,yb){const X=C.X,ia=C.ix(h.a.t),u=C.ix(h.b.t)-ia;if(Math.abs(u)<.5){L2(X,xa,ya,xb,yb);return g2(C,xa,ya,xb,yb)}const mid=(h.a.p+h.b.p)/2,amp=(h.a.p-h.b.p)/2,ps=[];
   for(let px=0;px<=C.pw;px+=3){const l=C.ts.coordinateToLogical(px);if(l==null)continue;const yy=C.y(mid+amp*Math.cos(Math.PI*(l-ia)/u));if(yy!=null)ps.push([px,yy])}
   X.beginPath();ps.forEach((p,i)=>i?X.lineTo(p[0],p[1]):X.moveTo(p[0],p[1]));X.stroke();
   return{nut:[['a',xa,ya],['b',xb,yb]],trong:(x,yy)=>ps.some((p,i)=>i&&C.doan(ps[i-1][0],ps[i-1][1],p[0],p[1],x,yy)<=5)}}},
 dubao:{ten:'Dự báo',d:'M3 14L14 4M14 4l-5 1M14 4l-1 5M3 14m-1.5 0a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0',goi:'Kéo từ giá hiện tại tới giá dự kiến; hộp ghi mức thay đổi, phần trăm và số nến',
  ve(h,C,sel,col,xa,ya,xb,yb){const X=C.X,d=h.b.p-h.a.p,mc=h.mau||(d>=0?C.P.tp:C.P.sl);X.save();X.strokeStyle=mc;X.fillStyle=mc;X.setLineDash([6,4]);L2(X,xa,ya,xb,yb);X.setLineDash([]);muiTen(X,xa,ya,xb,yb);X.restore();
   C.cham(xa,ya,mc);const r=hopChu(C,[thayDoi(C,h.a,h.b),soNen(C,h.a,h.b)],xb+12,yb+(d>=0?-46:10),{nen:mc,mau:'#fff',nenA:.92,vien:sel?C.P.fg:null,sel});
   return{nut:[['a',xa,ya],['b',xb,yb]],trong:(x,yy)=>C.doan(xa,ya,xb,yb,x,yy)<=6||trongHop(r,x,yy)}}},
 duongdi:{ten:'Lộ trình dự báo',d:'M2 15l4-6 4 3 5-8M15 4l-3.5.5M15 4l-.5 3.5',goi:'Bấm từng điểm của đường đi dự kiến; bấm đúp hoặc Enter để xong',n:99,
  ve:nhieu(null,{sau:(X,ps,h,C,col)=>{const n=ps.length;X.save();X.fillStyle=col;X.setLineDash([]);muiTen(X,ps[n-2][0],ps[n-2][1],ps[n-1][0],ps[n-1][1],12);X.restore()}})},
 mauthanh:{ten:'Mẫu thanh nến (sao chép)',d:'M4 3v12M3 6h2v5H3zM9 2v10M8 4h2v5H8zM14 6v10M13 8h2v5h-2z',goi:'Kéo chọn một đoạn nến; bản sao hiện ngay sau, kéo chấm để đặt bản sao vào chỗ khác',
  c:(h,LW,D)=>{const cs=(D&&D.candles)||[],i0=tim(cs,Math.min(h.a.t,h.b.t)),dt=(()=>{let m=Infinity;for(let i=Math.max(1,cs.length-30);i<cs.length;i++){const d=cs[i][0]-cs[i-1][0];if(d>0&&d<m)m=d}return m<Infinity?m:60})();return{t:Math.max(h.a.t,h.b.t)+Math.abs(h.b.t-h.a.t)+dt*2,p:i0>=0?cs[i0][1]:h.a.p}},
  ve(h,C,sel,col,xa,ya,xb,yb){const X=C.X,cs=C.cs,n=cs.length,q=pc(C,h,'c'),xs0=Math.min(xa,xb),xs1=Math.max(xa,xb),ys0=Math.min(ya,yb),ys1=Math.max(ya,yb);
   let i0=Math.max(0,Math.round(C.ix(Math.min(h.a.t,h.b.t)))),i1=Math.min(n-1,Math.round(C.ix(Math.max(h.a.t,h.b.t))));i1=Math.min(i1,i0+400);
   X.save();X.setLineDash([3,3]);X.lineWidth=1;X.strokeStyle=C.P.mute;X.strokeRect(xs0+.5,ys0+.5,xs1-xs0,ys1-ys0);X.restore();
   const nguon=(x,yy)=>x>=xs0-4&&x<=xs1+4&&yy>=ys0-4&&yy<=ys1+4;if(!q||i1<i0)return{nut:[['a',xa,ya],['b',xb,yb]],trong:nguon};
   const ic=C.ix(h.c.t),dp=h.c.p-cs[i0][1],x1=C.ts.logicalToCoordinate(ic),x2=C.ts.logicalToCoordinate(ic+1),bw=Math.max(1,(x1!=null&&x2!=null?Math.abs(x2-x1):6)*.6);let lo=1e9,hi=-1e9,L=1e9,R=-1e9;
   X.save();X.lineWidth=1;X.setLineDash([]);for(let i=i0;i<=i1;i++){const c=cs[i],xx=C.ts.logicalToCoordinate(ic+i-i0);if(xx==null)continue;const yo=C.y(c[1]+dp),yh=C.y(c[2]+dp),yl=C.y(c[3]+dp),yc=C.y(c[4]+dp);
    if(yo==null||yh==null||yl==null||yc==null)continue;const m=h.mau||(c[4]>=c[1]?C.P.tp:C.P.sl);X.strokeStyle=m;X.fillStyle=m;X.globalAlpha=.6;L2(X,xx,yh,xx,yl);X.globalAlpha=.42;X.fillRect(xx-bw/2,Math.min(yo,yc),bw,Math.max(1,Math.abs(yc-yo)));
    lo=Math.min(lo,yh);hi=Math.max(hi,yl);L=Math.min(L,xx-bw);R=Math.max(R,xx+bw)}X.restore();
   return{nut:[['a',xa,ya],['b',xb,yb],['c',q[0],q[1]]],trong:(x,yy)=>(x>=L-3&&x<=R+3&&yy>=lo-3&&yy<=hi+3)||nguon(x,yy)}}},
 binhh:{ten:'Hình bình hành',d:'M5 4h11l-3 10H2z',goi:'Kéo cạnh thứ nhất; đỉnh thứ ba tự đặt, kéo chấm để chỉnh',c:(h,LW)=>({t:h.b.t+Math.round((h.b.t-h.a.t)*.25),p:h.b.p-donVi(LW)}),
  ve(h,C,sel,col,xa,ya,xb,yb){const X=C.X,q=pc(C,h,'c');if(!q){L2(X,xa,ya,xb,yb);return g2(C,xa,ya,xb,yb)}const ps=[[xa,ya],[xb,yb],q,[xa+q[0]-xb,ya+q[1]-yb]];
   X.beginPath();ps.forEach((p,i)=>i?X.lineTo(p[0],p[1]):X.moveTo(p[0],p[1]));X.closePath();X.save();X.globalAlpha=.1;X.fillStyle=col;X.fill();X.restore();X.stroke();
   return{nut:[['a',xa,ya],['b',xb,yb],['c',q[0],q[1]]],trong:(x,yy)=>pip(ps,x,yy)||ps.some((p,i)=>C.doan(p[0],p[1],ps[(i+1)%4][0],ps[(i+1)%4][1],x,yy)<=6)}}},
 tron:{ten:'Hình tròn',d:'M9 9m-6.5 0a6.5 6.5 0 1 0 13 0a6.5 6.5 0 1 0-13 0M9 9h6.5',goi:'Kéo từ tâm ra mép',
  ve(h,C,sel,col,xa,ya,xb,yb){const X=C.X,r=Math.hypot(xb-xa,yb-ya)||1;X.beginPath();X.arc(xa,ya,r,0,7);X.save();X.globalAlpha=.08;X.fillStyle=col;X.fill();X.restore();X.stroke();
   return{nut:[['a',xa,ya],['b',xb,yb]],trong:(x,yy)=>Math.hypot(x-xa,yy-ya)<=r+5}}},
 dabut:{ten:'Bút dạ (tô sáng)',d:'M4 13l3-1 8-8-2-2-8 8zM3 16h12',goi:'Giữ chuột và tô lên vùng cần làm nổi',
  ve(h,C,sel,col){const X=C.X,ps=(h.pts||[]).map(q=>[C.vx(q.t),C.y(q.p)]).filter(q=>q[0]!=null&&q[1]!=null);if(ps.length<2)return null;
   X.save();X.globalAlpha=.3;X.lineWidth=14*((h.w||1.5)/1.5);X.lineCap='round';X.lineJoin='round';X.setLineDash([]);X.beginPath();ps.forEach((q,i)=>i?X.lineTo(q[0],q[1]):X.moveTo(q[0],q[1]));X.stroke();X.restore();
   return{nut:[],trong:(x,yy)=>ps.some((q,i)=>i&&C.doan(ps[i-1][0],ps[i-1][1],q[0],q[1],x,yy)<=9)}}},
 chuthich:{ten:'Chú thích có mũi tên',d:'M3 3h12v8H8l-4 4v-4H3z',goi:'Bấm vào điểm cần chỉ rồi gõ chữ; kéo hộp chữ đi chỗ khác, mũi tên vẫn chỉ vào điểm đó',chu:1,
  them:(q,m,toa)=>{const b=toa(m.x+46,m.y-64);return b?{b}:{}},
  ve(h,C,sel,col,xa,ya,xb,yb){const X=C.X;if(xb==null){xb=xa+46;yb=ya-64}const ls=dongChu(X,h.chu,220),r=doHop(C,ls,xb,yb),cx=r[0]+r[2]/2,cy=r[1]+r[3]/2,g=Math.atan2(ya-cy,xa-cx),w=Math.min(9,r[3]/3);
   X.save();X.fillStyle=col;X.setLineDash([]);X.beginPath();X.moveTo(cx+w*Math.cos(g+Math.PI/2),cy+w*Math.sin(g+Math.PI/2));X.lineTo(xa,ya);X.lineTo(cx+w*Math.cos(g-Math.PI/2),cy+w*Math.sin(g-Math.PI/2));X.closePath();X.fill();X.restore();
   veHop(C,ls,r,{nen:col,mau:'#fff',nenA:1,vien:sel?C.P.fg:null,sel});
   return{nut:[['a',xa,ya],['b',r[0],r[1]]],trong:(x,yy)=>trongHop(r,x,yy)||C.doan(xa,ya,cx,cy,x,yy)<=6}}},
 binhluan:{ten:'Bình luận',d:'M3 4h12v7H9l-4 3v-3H3zM6 7.5h6',goi:'Bấm vào chỗ cần bình luận rồi gõ chữ',chu:1,
  ve(h,C,sel,col,xa,ya){const X=C.X,ls=dongChu(X,h.chu,220),r=doHop(C,ls,xa+6,ya-14,{duoi:1});X.save();X.fillStyle=C.P.bg;X.strokeStyle=col;X.lineWidth=1;X.setLineDash([]);X.beginPath();
   X.moveTo(r[0]+8,r[1]+r[3]-1);X.lineTo(xa,ya);X.lineTo(r[0]+20,r[1]+r[3]-1);X.closePath();X.fill();X.stroke();X.restore();veHop(C,ls,r,{nen:C.P.bg,mau:C.P.fg,vien:col,sel,nenA:1});
   return{nut:[],trong:(x,yy)=>trongHop(r,x,yy)||Math.hypot(x-xa,yy-ya)<=6}}},
 ghim:{ten:'Ghim ghi chú',d:'M9 17v-7M9 6m-4 0a4 4 0 1 0 8 0a4 4 0 1 0-8 0',goi:'Bấm vào nến cần ghim rồi gõ ghi chú',chu:1,
  ve(h,C,sel,col,xa,ya){const X=C.X;X.save();X.setLineDash([]);X.strokeStyle=col;X.lineWidth=2;L2(X,xa,ya,xa,ya-15);X.fillStyle=col;X.beginPath();X.arc(xa,ya-22,8,0,7);X.fill();X.fillStyle='#fff';X.beginPath();X.arc(xa,ya-22,3,0,7);X.fill();X.restore();
   const ls=dongChu(X,h.chu,200),r=ls.length?hopChu(C,ls,xa+13,ya-24,{duoi:1,nen:C.P.bg,mau:C.P.fg,vien:col,sel}):null;
   return{nut:[],trong:(x,yy)=>Math.hypot(x-xa,yy-(ya-22))<=10||(Math.abs(x-xa)<=4&&yy<=ya+2&&yy>=ya-22)||trongHop(r,x,yy)}}},
 bienbao:{ten:'Biển chỉ dẫn',d:'M9 17V9M4 3h10v6H4z',goi:'Bấm vào nến rồi gõ chữ; biển dựng ngay trên điểm đó',chu:1,
  ve(h,C,sel,col,xa,ya){const X=C.X;X.save();X.setLineDash([]);X.strokeStyle=col;X.lineWidth=2;L2(X,xa,ya,xa,ya-40);X.fillStyle=col;X.beginPath();X.arc(xa,ya,3,0,7);X.fill();X.restore();
   const r=hopChu(C,dongChu(X,h.chu,200),xa,ya-40,{giua:1,duoi:1,nen:col,mau:'#fff',nenA:1,vien:sel?C.P.fg:null,sel});
   return{nut:[],trong:(x,yy)=>trongHop(r,x,yy)||(Math.abs(x-xa)<=4&&yy<=ya+3&&yy>=ya-40)}}},
 co:{ten:'Cắm cờ',d:'M5 16V2M5 3h9l-2.5 3.5L14 10H5',goi:'Bấm vào nến cần đánh dấu',tao:1,
  ve(h,C,sel,col,xa,ya){const X=C.X;X.save();X.setLineDash([]);X.strokeStyle=col;X.lineWidth=2;L2(X,xa,ya,xa,ya-28);X.fillStyle=col;X.beginPath();X.moveTo(xa,ya-28);X.lineTo(xa+19,ya-23);X.lineTo(xa,ya-17);X.closePath();X.fill();
   if(sel){X.lineWidth=1;X.setLineDash([3,3]);X.strokeRect(xa-4.5,ya-31.5,26,35)}X.restore();return{nut:[],trong:(x,yy)=>x>=xa-5&&x<=xa+21&&yy>=ya-31&&yy<=ya+3}}},
 ghichugia:{ten:'Ghi chú giá',d:'M2 15L9 8M9 5h7v6H9z',goi:'Kéo từ mức giá cần ghi tới chỗ đặt nhãn',
  ve(h,C,sel,col,xa,ya,xb,yb){const X=C.X;L2(X,xa,ya,xb,yb);C.cham(xa,ya,col);const r=hopChu(C,[C.fp(h.a.p)],xb+(xb>=xa?4:-4),yb-12,{nen:col,mau:'#fff',nenA:1,vien:sel?C.P.fg:null,sel});
   return{nut:[['a',xa,ya],['b',xb,yb]],trong:(x,yy)=>C.doan(xa,ya,xb,yb,x,yy)<=6||trongHop(r,x,yy)}}},
 bieu:{ten:'Biểu tượng',d:'M9 9m-7 0a7 7 0 1 0 14 0a7 7 0 1 0-14 0M6 11c1.6 2 4.4 2 6 0M6.5 7h.01M11.5 7h.01',goi:'Bấm vào biểu đồ để đặt biểu tượng đã chọn',tao:1,
  them:(q,m,toa,VE)=>({bt:Math.max(0,Math.min(BT.length-1,(VE&&VE.bt)|0))}),
  ve(h,C,sel,col,xa,ya){const X=C.X,e=BT[h.bt|0]||BT[0],s=26;X.save();X.setLineDash([]);X.globalAlpha=1;X.font=s+'px "Segoe UI Emoji","Apple Color Emoji","Noto Color Emoji",sans-serif';X.textAlign='center';X.textBaseline='middle';X.fillStyle=C.P.fg;X.fillText(e,xa,ya);
   if(sel){X.lineWidth=1;X.strokeStyle=col;X.setLineDash([3,3]);X.strokeRect(xa-s/2-3.5,ya-s/2-3.5,s+7,s+7)}X.restore();return{nut:[],trong:(x,yy)=>Math.abs(x-xa)<=s/2+4&&Math.abs(yy-ya)<=s/2+4}}}
};
// tên ngắn kiểu TradingView cho vài công cụ có sẵn (hiện ở bảng bung ra, chú thích nút và menu chuột phải)
const VETEN={xu:'Đường xu hướng',tia:'Tia',ngang:'Đường nằm ngang',tngang:'Tia nằm ngang',doc:'Đường thẳng đứng',cheo:'Đường chữ thập',chia:'Pitchfork (chĩa ba Andrews)',
 hop:'Hình chữ nhật',chu:'Văn bản',do:'Thước đo nhanh',vt:'Vị thế mua/bán (R:R)',fib:'Fibonacci thoái lui',dogia:'Đo khoảng giá',dotg:'Đo khoảng thời gian',dovung:'Đo vùng giá và thời gian'};
const NHOM=[
 {id:'duong',ten:'Đường, kênh và pitchfork',ds:['Đường',['xu','Alt + T'],['tia'],['ttin'],['mrong'],['goc'],['ngang','Alt + H'],['tngang','Alt + J'],['doc','Alt + V'],['cheo'],
  'Kênh',['kenh'],['hoiquy'],['phang'],['roirac'],'Pitchfork',['chia'],['schiff'],['schiffs'],['chiatr']]},
 {id:'fib',ten:'Fibonacci và Gann',ds:['Fibonacci',['fib','Alt + F'],['fibmr'],['fibk'],['fibtg'],['fibtgx'],['quat'],['fibvong'],['fibcung'],['fibxoan'],'Gann',['gannh'],['gannv'],['gannq']]},
 {id:'mau',ten:'Mẫu hình',ds:['Mẫu hình giá',['xabcd'],['cypher'],['abcd'],['dauvai'],['tamgm'],['badinh'],'Sóng Elliott',['elliott'],['abc'],['elltg'],['ellwxy'],['ellwxyxz'],['ellcheo'],'Chu kỳ thời gian',['chuky'],['sin']]},
 {id:'dubao',ten:'Dự báo và đo lường',ds:['Dự báo',['vt'],['dubao'],['duongdi'],['mauthanh'],'Đo lường',['do'],['dogia'],['dotg'],['dovung']]},
 {id:'hinh',ten:'Hình học',ds:['Bút vẽ',['but'],['dabut'],'Mũi tên',['mt'],['muilen'],['muixuong'],'Hình',['hop','Alt + Shift + R'],['elip'],['tron'],['tamg'],['binhh'],['cong'],['gap']]},
 {id:'chu',ten:'Chữ và chú thích',ds:['Chữ',['chu'],['chuthich'],['binhluan'],['ghim'],['bienbao'],'Đánh dấu',['nhan'],['ghichugia'],['co']]},
 {id:'bt',ten:'Biểu tượng',bt:1,ds:[['bieu']]}];
const docLS=(k,md)=>{try{const v=JSON.parse(localStorage.getItem(k)||'null');return v==null?md:v}catch(e){return md}},ghiLS=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}};
let CUOI=docLS('so-ve-nhom',{}),YT=docLS('so-ve-yt',[]),POP=null,MO='',CTX=null;if(!Array.isArray(YT))YT=[];if(!CUOI||typeof CUOI!=='object')CUOI={};
const boDau=s=>String(s).normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/đ/g,'d').replace(/Đ/g,'D').toLowerCase();
const cacNhom=VEC=>{const ds=YT.filter(k=>VEC[k]);return(ds.length?[{id:'yt',ten:'Yêu thích',ds:ds.map(k=>[k])}]:[]).concat(NHOM)};
const cungNhom=(g,VEC)=>g.ds.filter(r=>Array.isArray(r)&&VEC[r[0]]).map(r=>r[0]);
const SVG=(d,s)=>`<svg viewBox="0 0 18 18" width="${s}" height="${s}" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`;
const MUI='<svg viewBox="0 0 7 12" width="7" height="12" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1.5 2l4 4-4 4"/></svg>';
function dongPop(){if(POP){POP.remove();POP=null}const cu=MO;MO='';if(cu&&CTX){const b=CTX.VTB.querySelector(`.vnh-mo[data-nh="${cu}"]`);if(b)b.setAttribute('aria-expanded','false')}}
function dongMuc(k,ph,VE,VEC){const yt=YT.includes(k);return`<div class="vp-dong"><button type="button" class="vp-mi" role="menuitem" data-c="${esc(k)}" aria-current="${VE.cong===k}">${SVG(VEC[k][1],26)}<span>${esc(VEC[k][0])}</span>${ph?`<kbd>${esc(ph)}</kbd>`:''}</button>`
 +`<button type="button" class="vp-sao" data-sao="${esc(k)}" aria-pressed="${yt}" title="${yt?'Bỏ khỏi Yêu thích':'Thêm vào Yêu thích'}" aria-label="${yt?'Bỏ khỏi Yêu thích':'Thêm vào Yêu thích'}">${yt?'★':'☆'}</button></div>`}
function noiDung(g,loc){const{VE,VEC}=CTX;let s='';
 if(loc){const q=boDau(loc.trim()),ds=[];for(const n of NHOM)for(const r of n.ds)if(Array.isArray(r)&&VEC[r[0]]&&!ds.some(x=>x[0]===r[0])&&(boDau(VEC[r[0]][0]).includes(q)||boDau(n.ten).includes(q)))ds.push(r);
  return ds.length?ds.map(r=>dongMuc(r[0],r[1],VE,VEC)).join(''):'<div class="vp-trong">Không thấy công cụ nào khớp</div>'}
 if(g.bt){const cur=VE.bt|0;return'<div class="vp-dau">Biểu tượng</div><div class="vp-bt">'+BT.map((e,i)=>`<button type="button" class="vp-e" role="menuitem" data-bt="${i}" aria-pressed="${i===cur}" aria-label="${e}">${e}</button>`).join('')+'</div>'}
 for(const r of g.ds){if(typeof r==='string')s+=`<div class="vp-dau">${esc(r)}</div>`;else if(VEC[r[0]])s+=dongMuc(r[0],r[1],VE,VEC)}return s||'<div class="vp-trong">Chưa có công cụ nào</div>'}
function datViTri(o){if(!POP)return;const st=POP.parentNode,rs=st.getBoundingClientRect(),rv=CTX.VTB.getBoundingClientRect(),ra=o?o.getBoundingClientRect():rv;POP.style.left=Math.round(rv.right-rs.left+6)+'px';
 POP.style.maxHeight=Math.max(160,rs.height-12)+'px';const h=POP.offsetHeight;let t=Math.round(ra.top-rs.top-6);if(t+h>rs.height-6)t=Math.max(6,Math.round(rs.height-6-h));POP.style.top=t+'px'}
function veLaiPop(){if(!POP)return;const g=cacNhom(CTX.VEC).find(x=>x.id===MO);const ds=POP.querySelector('.vp-ds'),o=POP.querySelector('input');ds.innerHTML=noiDung(g||NHOM[0],o&&o.value)}
function moPop(gid,neo){const g=cacNhom(CTX.VEC).find(x=>x.id===gid);if(!g)return;dongPop();const st=CTX.VTB.parentNode;if(!st)return;MO=gid;
 POP=document.createElement('div');POP.className='vpop';POP.setAttribute('role','menu');POP.setAttribute('aria-label',g.ten);
 POP.innerHTML=(g.bt?'':'<div class="vp-tim"><input type="search" placeholder="Tìm công cụ vẽ" aria-label="Tìm công cụ vẽ" autocomplete="off"></div>')+'<div class="vp-ds"></div>';st.appendChild(POP);veLaiPop();datViTri(neo);
 const b=CTX.VTB.querySelector(`.vnh-mo[data-nh="${gid}"]`);if(b)b.setAttribute('aria-expanded','true');
 const o=POP.querySelector('input');if(o)o.addEventListener('input',()=>{veLaiPop();datViTri(neo)});
 POP.addEventListener('click',e=>{const t=e.target.closest('button');if(!t)return;e.stopPropagation();const{VE,VEC}=CTX;
  if(t.dataset.sao){const k=t.dataset.sao;YT=YT.includes(k)?YT.filter(x=>x!==k):YT.concat(k);ghiLS('so-ve-yt',YT);const giu=MO;CTX.veTb();MO=giu;
   if(MO==='yt'&&!YT.length){dongPop();return}const bb=CTX.VTB.querySelector(`.vnh-mo[data-nh="${MO}"]`);if(bb)bb.setAttribute('aria-expanded','true');veLaiPop();datViTri(CTX.VTB.querySelector(`.vnh[data-g="${MO}"]`));return}
  if(t.dataset.bt!=null){VE.bt=+t.dataset.bt;ghiLS('so-ve-bt',VE.bt);CUOI.bt='bieu';ghiLS('so-ve-nhom',CUOI);dongPop();CTX.veCong('bieu');return}
  const k=t.dataset.c;if(!k||!VEC[k])return;for(const n of cacNhom(VEC))if(n.id!=='yt'&&cungNhom(n,VEC).includes(k))CUOI[n.id]=k;if(MO==='yt')CUOI.yt=k;ghiLS('so-ve-nhom',CUOI);dongPop();CTX.veCong(k)});
 POP.addEventListener('keydown',e=>{const ds=[...POP.querySelectorAll('.vp-mi,.vp-e')],i=ds.indexOf(document.activeElement);
  if(e.key==='Escape'){e.preventDefault();e.stopPropagation();const gb=MO;dongPop();const bb=CTX.VTB.querySelector(`.vnh-mo[data-nh="${gb}"]`);if(bb)bb.focus()}
  else if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();e.stopPropagation();if(!ds.length)return;const j=e.key==='ArrowDown'?(i+1)%ds.length:(i<=0?ds.length-1:i-1);ds[j].focus()}
  else if(e.key==='ArrowLeft'||e.key==='ArrowRight'||e.key==='Home'||e.key==='End')e.stopPropagation()});
 const dau=POP.querySelector('.vp-mi[aria-current="true"],.vp-e[aria-pressed="true"]')||POP.querySelector('.vp-mi,.vp-e');if(dau)setTimeout(()=>{try{dau.focus({preventScroll:true})}catch(_){dau.focus()}},0)}
document.addEventListener('pointerdown',e=>{if(POP&&!POP.contains(e.target)&&!(e.target.closest&&e.target.closest('.vnh-mo')))dongPop()},true);
addEventListener('resize',()=>dongPop());
document.addEventListener('keydown',e=>{if(POP&&e.key==='Escape'&&!POP.contains(e.target)){e.preventDefault();e.stopPropagation();dongPop()}},true);   // Esc đóng bảng cả khi tiêu điểm đã rời bảng (vừa bấm sao)
// Alt+T đường xu hướng, Alt+F Fibonacci, Alt+Shift+R hình chữ nhật (Alt+H/J/V đặt ngay tại chuột: bieu_do_menu.py)
addEventListener('keydown',e=>{if(!e.altKey||e.ctrlKey||e.metaKey||/^(INPUT|TEXTAREA|SELECT)$/.test((e.target&&e.target.tagName)||''))return;const k=e.code==='KeyT'&&!e.shiftKey?'xu':e.code==='KeyF'&&!e.shiftKey?'fib':e.code==='KeyR'&&e.shiftKey?'hop':null;
 if(!k||!window.BDMN)return;const g=window.BDMN();if(!g||!g.LW)return;e.preventDefault();e.stopPropagation();g.veCong(k)});
window.VEX=VEX;window.VETEN=VETEN;window.VEBT=BT;
window.VNH={NHOM,
 html(VE,VEC,nut){if(VE.bt==null)VE.bt=docLS('so-ve-bt',0)|0;let s=nut('tro',VEC.tro,'c'),doi=0;
  for(const g of cacNhom(VEC)){const ks=cungNhom(g,VEC);if(!ks.length)continue;let k=ks.includes(VE.cong)?VE.cong:ks.includes(CUOI[g.id])?CUOI[g.id]:ks[0];if(ks.includes(VE.cong)&&CUOI[g.id]!==VE.cong&&g.id!=='yt'){CUOI[g.id]=VE.cong;doi=1}
   s+=`<span class="vnh" data-g="${g.id}">${nut(k,VEC[k],'c')}<button type="button" class="vnh-mo" data-nh="${g.id}" title="${esc(g.ten)}" aria-label="${esc(g.ten)}" aria-haspopup="menu" aria-expanded="${MO===g.id}">${MUI}</button></span>`}
  if(doi)ghiLS('so-ve-nhom',CUOI);return s},
 gan(VTB,ctx){CTX={VTB,...ctx};VTB.classList.add('nhom');
  VTB.querySelectorAll('.vnh-mo').forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();const gid=b.dataset.nh;if(MO===gid)dongPop();else moPop(gid,b.closest('.vnh'))}));
  VTB.querySelectorAll('.vnh').forEach(w=>{w.addEventListener('contextmenu',e=>{e.preventDefault();e.stopPropagation();moPop(w.dataset.g,w)});
   w.addEventListener('click',e=>{if(e.target.closest('.vnh-mo'))return;if(matchMedia('(pointer:coarse)').matches){e.stopPropagation();e.preventDefault();if(MO===w.dataset.g)dongPop();else moPop(w.dataset.g,w)}},true)});
  if(POP&&MO){const bb=VTB.querySelector(`.vnh-mo[data-nh="${MO}"]`);if(bb)bb.setAttribute('aria-expanded','true');else dongPop()}},
 dong:dongPop};
})();
"""
