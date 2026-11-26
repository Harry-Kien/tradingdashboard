"""Công cụ thêm cho trang Biểu đồ, cho ngang các phần hay dùng của TradingView (chủ dự án yêu cầu ngày 26/11/2026).

Menu "Công cụ" trên thanh biểu đồ:
- Tô nền phiên Á (Tokyo 9–18 giờ), Âu (London 8–17 giờ), Mỹ (New York 8–17 giờ), theo giờ địa phương nên tự theo giờ mùa hè. Chỉ ở khung H1 trở xuống.
- Hồ sơ khối lượng theo giá của đoạn đang xem (kiểu Volume Profile Visible Range), từ tick volume của MT5: cột xanh là nến tăng, đỏ là nến giảm,
  vàng là mức nhiều khối lượng nhất (POC), phần đậm là vùng chứa 70% khối lượng. Tick volume chỉ có khi nối MT5, cho các nến MT5 còn giữ (trang tải thêm tới 30.000 nến cũ qua /api/khoi-luong).
- Thang giá thường, logarit, phần trăm.
- So sánh với một mã khác trong Market Watch: % thay đổi trên thang trái (tính từ nến chung đầu tiên), kèm tương quan lợi suất 100 nến chung gần nhất.
Nút "AI đọc chỉ báo": gửi số cuối của các chỉ báo bạn đang bật cho Claude (chung lượt và ngân sách với Hỏi AI), hiện cách đọc kèm kịch bản có điều kiện.

Nền phiên và hồ sơ khối lượng vẽ bằng primitive của Lightweight Charts gắn vào chuỗi nến, nên có trong ảnh chụp biểu đồ. Chỉ đọc, không đặt lệnh.
Chạy sau bieu_do_chi_bao (dùng window.BDCB, CBCN.moc, CBCN.tomTat)."""

CSS = r"""
.cbcn-them{position:relative;margin:0}.cbcn-them summary{list-style:none;padding:0 10px}.cbcn-them summary::-webkit-details-marker{display:none}
.cbcn-them[open] summary{border-color:var(--series)}
@media (max-width:640px){.cbcn-them .pop{left:auto!important;right:0!important}}
.cbcn-them .pop{position:absolute;z-index:40;top:calc(100% + 6px);left:0;width:min(300px,calc(100vw - 24px));box-sizing:border-box;display:grid;gap:10px;padding:12px;background:var(--card);
border:1px solid var(--line);border-radius:12px;box-shadow:0 14px 36px rgba(0,0,0,.3);font-size:13px}
.cbcn-them .pop label{display:flex;gap:8px;align-items:center;color:var(--ink2)}.cbcn-them .pop select{flex:1;min-height:32px}
.cbcn-them .pop small{color:var(--mute);font-size:11.5px;line-height:1.4}
.aicb .noi{padding:12px 16px 16px;overflow:auto;font-size:13.5px;line-height:1.55}.aicb .noi p{margin:0 0 10px}
.aicb .noi .why{color:var(--mute);font-size:12.5px}.aicb .noi .tl{border-left:3px solid var(--series);padding-left:12px;margin:8px 0 12px}
"""

JS = r"""
(()=>{if(!window.CBCN||!window.LightweightCharts)return;const BD=()=>window.BDCB&&window.BDCB(),esc=s=>String(s??'').replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');
let ON={phien:0,hoso:0,thang:0,ss:''};try{ON={...ON,...JSON.parse(localStorage.getItem('so-cbcn-them')||'{}')}}catch(e){}
const luu=()=>{try{localStorage.setItem('so-cbcn-them',JSON.stringify(ON))}catch(e){}};
// ---------------------------------------------------------------- phiên giao dịch (giờ địa phương của từng thị trường, nhớ theo từng giờ)
const PH=[['Phiên Á','Asia/Tokyo',9,18,'79,140,255'],['Phiên Âu','Europe/London',8,17,'240,180,41'],['Phiên Mỹ','America/New_York',8,17,'232,107,216']],GIO={},
 FM=PH.map(p=>new Intl.DateTimeFormat('en-GB',{timeZone:p[1],hour:'numeric',hourCycle:'h23',weekday:'short'}));
function phien(t){const k=Math.floor(t/3600);if(GIO[k]!=null)return GIO[k];let m=0;
 PH.forEach((p,j)=>{const ps=FM[j].formatToParts(new Date(k*3600000)),h=+ps.find(x=>x.type==='hour').value,w=ps.find(x=>x.type==='weekday').value;
  if(w!=='Sat'&&w!=='Sun'&&h>=p[2]&&h<p[3])m|=1<<j});return GIO[k]=m}
function vePhien(t){const B=BD();if(!ON.phien||!B||!B.LW||!B.D||!B.D.candles)return;const tf=B.D.tf||'';if(tf==='H4'||tf==='D1')return;
 const cs=B.D.candles,ts=B.LW.chart.timeScale(),r=ts.getVisibleLogicalRange();if(!r||!cs.length)return;const bs=ts.options().barSpacing||6,
  i0=Math.max(0,Math.floor(r.from)-1),i1=Math.min(cs.length-1,Math.ceil(r.to)+1),bg=(getComputedStyle(document.body).backgroundColor.match(/\d+/g)||[0,0,0]).map(Number),toi=bg[0]+bg[1]+bg[2]<384;
 t.useMediaCoordinateSpace(({context:c,mediaSize:m})=>{c.save();c.font='11px Tahoma, Segoe UI, sans-serif';
  PH.forEach((p,j)=>{let a=null,x0=0;const dong=(x1)=>{c.fillStyle=`rgba(${p[4]},${toi?.075:.07})`;c.fillRect(x0,0,x1-x0,m.height);
    if(x1-x0>46){c.fillStyle=`rgba(${p[4]},.85)`;c.fillText(p[0],x0+4,m.height-6-j*13)}};
   for(let i=i0;i<=i1;i++){const x=ts.timeToCoordinate(cs[i][0]);if(x==null)continue;const co=phien(cs[i][0])&(1<<j);
    if(co&&a===null){a=i;x0=x-bs/2}else if(!co&&a!==null){dong(x-bs/2);a=null}}
   if(a!==null){const x=ts.timeToCoordinate(cs[i1][0]);if(x!=null)dong(x+bs/2)}});c.restore()})}
// ---------------------------------------------------------------- hồ sơ khối lượng theo giá của đoạn đang xem (tick volume)
function veHoSo(t){const B=BD();if(!ON.hoso||!B||!B.LW||!B.D||!B.D.candles)return;const cs=B.D.candles,VM=B.D.vol||{},ts=B.LW.chart.timeScale(),r=ts.getVisibleLogicalRange(),s=B.LW.nen;
 if(!r||!s)return;const i0=Math.max(0,Math.floor(r.from)),i1=Math.min(cs.length-1,Math.ceil(r.to));let lo=1e18,hi=-1e18,co=0;
 for(let i=i0;i<=i1;i++){const v=VM[cs[i][0]];if(v==null)continue;co++;lo=Math.min(lo,cs[i][3]);hi=Math.max(hi,cs[i][2])}
 t.useMediaCoordinateSpace(({context:c,mediaSize:m})=>{c.save();c.font='11px Tahoma, Segoe UI, sans-serif';
  if(co<5||!(hi>lo)){c.fillStyle='rgba(150,150,150,.9)';const s1='Hồ sơ khối lượng: đoạn này chưa có tick volume (chỉ có khi nối MT5, cho các nến MT5 còn giữ).';
   c.fillText(s1,Math.max(8,m.width-c.measureText(s1).width-10),m.height-10);c.restore();return}
  const R=32,b=(hi-lo)/R,up=new Float64Array(R),dn=new Float64Array(R);
  for(let i=i0;i<=i1;i++){const v=VM[cs[i][0]];if(v==null)continue;const a=Math.max(0,Math.min(R-1,Math.floor((cs[i][3]-lo)/b))),z=Math.max(0,Math.min(R-1,Math.floor((cs[i][2]-lo)/b))),
   phan=v/(z-a+1),tang=cs[i][4]>=cs[i][1];for(let k=a;k<=z;k++)(tang?up:dn)[k]+=phan}
  const tong=[...up].map((u,k)=>u+dn[k]),mx=Math.max(...tong),sum=tong.reduce((x,y)=>x+y,0);let poc=tong.indexOf(mx),va=new Set([poc]),dd=mx,lu=poc,ld=poc;
  while(dd<.7*sum&&(lu<R-1||ld>0)){const tr=lu<R-1?tong[lu+1]:-1,du=ld>0?tong[ld-1]:-1;if(tr>=du){lu++;dd+=tong[lu];va.add(lu)}else{ld--;dd+=tong[ld];va.add(ld)}}
  const W=m.width*.24;for(let k=0;k<R;k++){if(!tong[k])continue;const y1=s.priceToCoordinate(lo+(k+1)*b),y0=s.priceToCoordinate(lo+k*b);if(y1==null||y0==null)continue;
   const h=Math.max(1,Math.abs(y0-y1)-1),y=Math.min(y0,y1),wu=up[k]/mx*W,wd=dn[k]/mx*W,al=va.has(k)?.42:.2;
   c.fillStyle=`rgba(38,166,154,${al})`;c.fillRect(m.width-wu-wd,y,wu,h);c.fillStyle=`rgba(239,83,80,${al})`;c.fillRect(m.width-wd,y,wd,h);
   if(k===poc){c.strokeStyle='rgba(240,180,41,.95)';c.lineWidth=1;c.strokeRect(m.width-wu-wd+.5,y+.5,wu+wd-1,h-1);
    const gp=lo+(k+.5)*b,nh='POC '+gp.toFixed(gp>100?2:5);c.fillStyle='rgba(240,180,41,.95)';c.fillText(nh,m.width-wu-wd-c.measureText(nh).width-6,y+h/2+4)}}
  c.restore()})}
// primitive gắn vào chuỗi nến: nền phiên vẽ dưới nến, hồ sơ khối lượng vẽ trên
let GAN=null,YC=null;const PRIM={attached(p){YC=p.requestUpdate},detached(){YC=null},updateAllViews(){},
 paneViews(){return[{zOrder:()=>'bottom',renderer:()=>({draw:t=>{try{vePhien(t)}catch(e){}}})},{zOrder:()=>'top',renderer:()=>({draw:t=>{try{veHoSo(t)}catch(e){}}})}]}};
const capNhat=()=>{YC&&YC()};
// ---------------------------------------------------------------- so sánh với mã khác (thang trái) và tương quan lợi suất
let SS=null,ssKhoa='',ssLuc=0;
function ssBo(c){if(SS){try{c.removeSeries(SS)}catch(e){}SS=null}ssKhoa='';try{c.applyOptions({leftPriceScale:{visible:false}})}catch(e){}}
async function ssNap(B){const c=B.LW.chart,tf=B.D.tf||'M15',k=ON.ss+'|'+tf;if(!ON.ss||(B.D.khac_vang&&B.D.ma===ON.ss)){if(SS)ssBo(c);return}
 if(k===ssKhoa&&Date.now()-ssLuc<60000)return;ssKhoa=k;ssLuc=Date.now();
 let j;try{const r=await fetch('/api/gia?tf='+tf+'&n=1500&ma='+encodeURIComponent(ON.ss),{cache:'no-store'});if(!r.ok)throw new Error(await r.text());j=await r.json()}
 catch(e){console.warn('So sánh mã:',e);ssKhoa='';return}
 const cs=B.D.candles,co=new Set(cs.map(x=>x[0])),m=new Map(j.candles.filter(x=>co.has(x[0])).map(x=>[x[0],x[4]]));if(!m.size)return;
 const chung=cs.filter(x=>m.has(x[0])).slice(-101);let tq=null;
 if(chung.length>30){const a=[],b=[];for(let i=1;i<chung.length;i++){a.push(Math.log(chung[i][4]/chung[i-1][4]));b.push(Math.log(m.get(chung[i][0])/m.get(chung[i-1][0])))}
  const mu=x=>x.reduce((p,q)=>p+q,0)/x.length,ma=mu(a),mb=mu(b);let sab=0,saa=0,sbb=0;a.forEach((v,i)=>{sab+=(v-ma)*(b[i]-mb);saa+=(v-ma)**2;sbb+=(b[i]-mb)**2});tq=sab/Math.sqrt(saa*sbb)}
 if(!SS){SS=c.addSeries(LightweightCharts.LineSeries,{priceScaleId:'left',color:'#4f8cff',lineWidth:1.5,priceLineVisible:false,crosshairMarkerVisible:false},0);
  c.applyOptions({leftPriceScale:{visible:true,borderVisible:false}})}
 const ds=[...m].sort((p,q)=>p[0]-q[0]),goc=ds[0][1];                 // % thay đổi so với nến chung đầu tiên, như "So sánh" của TradingView
 SS.applyOptions({title:ON.ss+' %'+(tq!=null?' · tương quan '+tq.toFixed(2):'')});SS.setData(ds.map(([t,v])=>({time:t,value:(v/goc-1)*100})))}
// ---------------------------------------------------------------- tick volume của nến cũ: tải một lần mỗi mã và khung (tới 30.000 nến MT5 còn giữ), ghép theo giờ nến
const KLM=new Map();let klDang='';
async function napKL(B){if(!(ON.hoso||CBCN.dung('kld')||CBCN.dung('kldg'))||!B.D||B.D.nguon!=='mt5')return;const ma=B.D.khac_vang?B.D.ma:'',tf=B.D.tf||'',k=ma+'|'+tf,c=KLM.get(k);
 if(c&&c.m){const v=B.D.vol||(B.D.vol={});if(B.D._kl!==k){for(const[t,x]of c.m)if(v[t]==null)v[t]=x;B.D._kl=k;CBCN.tinhLai();capNhat()}return}
 if(klDang===k||(c&&Date.now()-c.luc<600000))return;klDang=k;
 try{const j=await(await fetch('/api/khoi-luong?tf='+tf+'&n=30000'+(ma?'&ma='+encodeURIComponent(ma):''),{cache:'no-store'})).json();
  KLM.set(k,{luc:Date.now(),m:j.t&&j.t.length?j.t.map((t,i)=>[t,j.v[i]]):null});while(KLM.size>6)KLM.delete(KLM.keys().next().value)}catch(e){KLM.set(k,{luc:Date.now(),m:null})}
 klDang='';const B2=BD();if(B2)napKL(B2)}
// ---------------------------------------------------------------- móc vào mỗi lần vẽ biểu đồ
let mau=null;
CBCN.moc.push(B=>{const s=B.LW.nen;if(s&&GAN!==s){try{if(GAN)GAN.detachPrimitive(PRIM)}catch(e){}try{s.attachPrimitive(PRIM);GAN=s}catch(e){console.warn('Primitive:',e)}}
 try{const ps=B.LW.chart.priceScale('right');if(ps.options().mode!==ON.thang)ps.applyOptions({mode:ON.thang})}catch(e){}
 const k=(B.D.khac_vang?B.D.ma:'')+'|'+(B.D.tf||'');if(mau!==k){if(mau!==null&&SS)ssBo(B.LW.chart);mau=k}ssNap(B);napKL(B);capNhat()});
// ---------------------------------------------------------------- menu Công cụ
const t2=document.querySelector('.tools.t2'),moc=document.querySelector('.cbcn-mo');if(!t2)return;
const dt=document.createElement('details');dt.className='cbcn-them';
dt.innerHTML='<summary class="ghost nho" title="Phiên giao dịch, hồ sơ khối lượng, thang giá, so sánh mã">Công cụ</summary><div class="pop">'
 +'<label><input type="checkbox" data-k="phien"> Tô nền phiên Á, Âu, Mỹ</label>'
 +'<label><input type="checkbox" data-k="hoso"> Hồ sơ khối lượng theo giá (đoạn đang xem)</label>'
 +'<small>Tính từ tick volume của MT5 (số lần giá đổi), không phải khối lượng giao dịch thật; chỉ có khi nối MT5, cho các nến MT5 còn giữ (tới 30.000 nến gần nhất).</small>'
 +'<label>Thang giá <select data-k="thang"><option value="0">Thường</option><option value="1">Logarit</option><option value="2">Phần trăm</option></select></label>'
 +'<label>So sánh với <select data-k="ss"><option value="">Không so sánh</option></select></label>'
 +'<small>Mã so sánh vẽ theo % thay đổi trên thang trái; số bên cạnh là tương quan lợi suất của 100 nến chung gần nhất (−1 đến 1).</small></div>';
(moc||t2.lastChild).after(dt);
const ve=()=>{const B=BD();if(window.CBCN)CBCN.ve();if(B&&B.LW){const s=B.LW.nen;if(s&&GAN!==s)CBCN.ve();if(B.D)ssNap(B)}capNhat()};
dt.querySelectorAll('input[type=checkbox]').forEach(i=>{i.checked=!!ON[i.dataset.k];i.addEventListener('change',()=>{ON[i.dataset.k]=i.checked?1:0;luu();ve();const B=BD();if(B)napKL(B)})});
const st=dt.querySelector('[data-k=thang]'),sm=dt.querySelector('[data-k=ss]');st.value=String(ON.thang||0);
st.addEventListener('change',()=>{ON.thang=+st.value;luu();const B=BD();try{B.LW.chart.priceScale('right').applyOptions({mode:ON.thang})}catch(e){}ve()});
sm.addEventListener('change',()=>{ON.ss=sm.value;luu();const B=BD();if(B&&B.LW&&!ON.ss)ssBo(B.LW.chart);ssKhoa='';ve()});
const pop=dt.querySelector('.pop');dt.addEventListener('toggle',()=>{if(!dt.open)return;const dl=v=>{pop.style.setProperty('left',v,'important');pop.style.setProperty('right','auto','important')};dl('0px');const r=pop.getBoundingClientRect(),o=dt.getBoundingClientRect(),mx=document.documentElement.clientWidth-12;if(r.right>mx)dl(Math.max(12-o.left,mx-r.right)+'px')});   // dời sang trái cho vừa màn hình hẹp
let dsNap=0;dt.addEventListener('toggle',async()=>{if(!dt.open||dsNap)return;dsNap=1;try{const j=await(await fetch('/api/ma',{cache:'no-store'})).json(),B=BD(),hien=B&&B.D&&B.D.khac_vang?B.D.ma:'';
 sm.innerHTML='<option value="">Không so sánh</option>'+(j.ds||[]).filter(x=>x.ma!==hien).map(x=>`<option value="${esc(x.ma)}">${esc(x.ma)}</option>`).join('');sm.value=ON.ss||''}
 catch(e){dsNap=0}});
if(ON.ss){const o=document.createElement('option');o.value=ON.ss;o.textContent=ON.ss;sm.append(o);sm.value=ON.ss}
addEventListener('click',e=>{if(dt.open&&!dt.contains(e.target))dt.open=false});
// ---------------------------------------------------------------- AI đọc chỉ báo
const NE=document.createElement('div');NE.className='cbcn-nen aicb';NE.hidden=true;
NE.innerHTML='<div class="cbcn" role="dialog" aria-modal="true" aria-label="AI đọc chỉ báo" style="grid-template-rows:auto minmax(0,1fr)"><header><b>AI đọc chỉ báo</b><button type="button" class="ghost" data-dong>Đóng</button></header><div class="noi"></div></div>';
document.body.appendChild(NE);const NOI=NE.querySelector('.noi');let KQ=null;
const dinhDang=s=>esc(s).replace(/\*\*([^*]+)\*\*/g,'<b>$1</b>').split(/\n{2,}/).map(p=>'<p>'+p.replace(/\n/g,'<br>')+'</p>').join('');
async function aiVe(){let st;try{st=await(await fetch('/api/ai-chi-bao',{cache:'no-store'})).json()}catch(e){NOI.innerHTML='<p class="why">Không tải được trạng thái.</p>';return}
 const tt=CBCN.tomTat(),B=BD();let h='<p class="why">Gửi số cuối (nến đã đóng) của các chỉ báo bạn đang bật, các mũi tên mua bán gần nhất và 60 nến gần nhất cho Claude. Claude chỉ ra chỉ báo nào đồng thuận, chỗ nào mâu thuẫn, và các kịch bản vào lệnh có điều kiện. Dùng chung lượt và ngân sách với nút Hỏi AI.</p>'
  +`<p class="why">Hôm nay ${st.hom_nay}/${st.moi_ngay} lượt · đã dùng ${(+st.da_tieu_usd).toFixed(2)} / ${(+st.ngan_sach_usd).toFixed(2)} USD.</p>`;
 const chan=[...st.chan];if(!tt.chi_bao.length)chan.push('Chưa bật chỉ báo nào: bấm "Thêm chỉ báo" và chọn vài chỉ báo trước.');
 h+=`<p><b>Sẽ gửi ${tt.chi_bao.length} chỉ báo</b> (${esc(tt.chi_bao.map(x=>x.ten).join(', ')||'không có')}), khung ${esc(B&&B.D?B.D.tf:'')}.</p>`
  +`<button type="button" class="go" data-hoi ${chan.length?'disabled':''}>Đọc các chỉ báo đang bật (khoảng 0,05 USD)</button>`+chan.map(c=>`<p class="why">• ${esc(c)}</p>`).join('');
 if(KQ)h+=`<div class="tl">${dinhDang(KQ.tra_loi)}</div><p class="why">${esc(KQ.mien_tru)} Chi phí lượt này: ${(+KQ.chi_phi_usd||0).toFixed(3)} USD.</p>`;
 NOI.innerHTML=h;const b=NOI.querySelector('[data-hoi]');if(b)b.addEventListener('click',async()=>{if(!confirm('Một lượt AI đọc chỉ báo tốn khoảng 0,05 USD tiền API của bạn và tính vào lượt Hỏi AI hôm nay. Tiếp tục?'))return;
  b.disabled=true;b.textContent='Đang đọc, chờ tối đa 2 phút…';
  try{const r=await fetch('/api/ai-chi-bao',{method:'POST',headers:{'X-So-Cong-Khai':'1','Content-Type':'application/json'},body:JSON.stringify(CBCN.tomTat())});
   if(!r.ok)throw new Error(await r.text());const j=await r.json();if(!j.ok){alert(j.chan.join('\n'));await aiVe();return}KQ=j;await aiVe()}
  catch(e){alert('Không hỏi được AI: '+e.message);await aiVe()}})}
NE.addEventListener('click',e=>{if(e.target===NE||e.target.closest('[data-dong]'))NE.hidden=true});
addEventListener('keydown',e=>{if(!NE.hidden&&e.key==='Escape'){e.stopPropagation();NE.hidden=true}},true);
const ab=document.createElement('button');ab.type='button';ab.className='ghost nho';ab.textContent='AI đọc chỉ báo';ab.title='Claude đọc các chỉ báo bạn đang bật (chung lượt với Hỏi AI)';
ab.addEventListener('click',()=>{NE.hidden=false;aiVe()});dt.after(ab);
window.CBTH={ON,phien,PRIM,ssNap}})();
"""
