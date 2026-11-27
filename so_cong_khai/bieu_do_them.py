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
function vePhien(t){const B=BD();if(!ON.phien||!B||!B.LW||!B.D||!B.D.candles)return;const tf=B.D.tf||'';if(['H4','D1','W1','MN1'].includes(tf))return;   // từ H4 trở lên: một nến dài hơn một phiên
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
let SS=null,ssKhoa='',ssLuc=0,ssDL=null,ssVe='',ssES=null,ssESKey='',ssMS=0,ssTick=null,ssFrame=0,ssSource=null;const ssGate=CHART_RT.latest();let ssTask=null;
const ssKey=B=>(B.D._chart_context||B.D.ma||'')+'|'+(B.D._chart_epoch||0)+'|'+ON.ss+'|'+(B.D.tf||'M15');
function ssDong(){if(ssES){ssES.onmessage=ssES.onerror=null;ssES.close()}ssES=null;ssESKey='';ssTick=null;ssMS=0}
function ssBo(c){ssGate.cancel();ssTask=null;ssDong();if(SS){try{c.removeSeries(SS)}catch(e){}SS=null}ssKhoa='';ssDL=null;ssVe='';ssSource=null;try{c.applyOptions({leftPriceScale:{visible:false}})}catch(e){}}
function ssAp(j,x){if(!x.nen||!j?.candles?.length)return;const cs=j.candles,last=cs.at(-1),r=x.nen;if(r[0]===last[0])cs[cs.length-1]=r.slice();else if(r[0]>last[0])cs.push(r.slice());j.bid=x.bid;j.ask=x.ask}
function ssHen(){if(ssFrame)return;ssFrame=requestAnimationFrame(()=>{ssFrame=0;const B=BD();if(B?.D)ssNap(B)})}
function ssMo(B,key){if(!window.EventSource||B.D.nguon!=='mt5'||document.visibilityState!=='visible'||window.PHAT_LAI)return;
 if(ssES&&ssESKey===key)return;ssDong();ssESKey=key;const es=new EventSource('/api/song?tf='+encodeURIComponent(B.D.tf||'M15')+'&ma='+encodeURIComponent(ON.ss));ssES=es;
 es.onmessage=e=>{if(ssES!==es||ssESKey!==key)return;const now=BD();if(!now?.D||ssKey(now)!==key)return;let x;try{x=JSON.parse(e.data)}catch(e){return}if(!CHART_RT.hopLe(x,ssMS))return;ssMS=x.ms;ssTick=x;if(ssDL)ssAp(ssDL,x);ssHen()}}
async function ssNap(B){if(!B?.D||!B.LW)return;const c=B.LW.chart,tf=B.D.tf||'M15',k=ssKey(B);
 if(window.PHAT_LAI){if(SS||ssES||ssTask)ssBo(c);return}
 if(!ON.ss||(B.D.ma===ON.ss)){if(SS||ssES||ssTask)ssBo(c);return}
 if(k!==ssKhoa){ssBo(c);ssKhoa=k;ssLuc=0}
 if(!ssTask&&(Date.now()-ssLuc>=(ssES?60000:10000)||!ssDL)){
  const task=ssGate.begin(k);ssTask=task;ssLuc=Date.now();
  try{const r=await fetch('/api/gia?tf='+tf+'&n=1500&ma='+encodeURIComponent(ON.ss),{cache:'no-store',signal:task.signal});if(!r.ok)throw new Error(await r.text());const j=await r.json();
   const B2=BD();if(!ssGate.current(task)||!B2?.D||ssKey(B2)!==k)return;ssDL=j;if(ssTick)ssAp(j,ssTick);B=B2;ssVe='';ssMo(B,k)}
  catch(e){if(ssGate.current(task)&&e.name!=='AbortError')console.warn('So sánh mã:',e);return}
  finally{if(ssTask===task)ssTask=null}}
 const j=ssDL;if(!j||ssKey(B)!==ssKhoa)return;ssMo(B,k);
 const last=B.D.candles.at(-1),other=j.candles.at(-1),kv=k+'|'+B.D.candles.length+'|'+last.join(',')+'|'+j.candles.length+'|'+other.join(',');
 if(kv===ssVe&&SS)return;ssVe=kv;
 const cs=B.D.candles,co=new Set(cs.map(x=>x[0])),m=new Map(j.candles.filter(x=>co.has(x[0])).map(x=>[x[0],x[4]]));if(!m.size)return;
 const chung=cs.filter(x=>m.has(x[0])).slice(-101);let tq=null;
 if(chung.length>30){const a=[],b=[];for(let i=1;i<chung.length;i++){a.push(Math.log(chung[i][4]/chung[i-1][4]));b.push(Math.log(m.get(chung[i][0])/m.get(chung[i-1][0])))}
  const mu=x=>x.reduce((p,q)=>p+q,0)/x.length,ma=mu(a),mb=mu(b);let sab=0,saa=0,sbb=0;a.forEach((v,i)=>{sab+=(v-ma)*(b[i]-mb);saa+=(v-ma)**2;sbb+=(b[i]-mb)**2});tq=sab/Math.sqrt(saa*sbb)}
 if(!SS){SS=c.addSeries(LightweightCharts.LineSeries,{priceScaleId:'left',color:'#4f8cff',lineWidth:1.5,priceLineVisible:false,crosshairMarkerVisible:false},0);
  c.applyOptions({leftPriceScale:{visible:true,borderVisible:false}})}
 const ds=[...m].sort((p,q)=>p[0]-q[0]),goc=ds[0][1];                 // % thay đổi so với nến chung đầu tiên, như "So sánh" của TradingView
 SS.applyOptions({title:ON.ss+' %'+(tq!=null&&isFinite(tq)?' · tương quan '+tq.toFixed(2):'')});
 if(!ssSource||ssSource.main!==cs||ssSource.compare!==j.candles||ssSource.first!==ds[0][0])ssSource={main:cs,compare:j.candles,first:ds[0][0]};
 CHART_RT.gui(SS,ds.length,i=>({time:ds[i][0],value:(ds[i][1]/goc-1)*100}),ssSource)}
// ---------------------------------------------------------------- tick volume của nến cũ: tải một lần mỗi mã và khung (tới 30.000 nến MT5 còn giữ), ghép theo giờ nến
const KLM=new Map();let klDang='';
async function napKL(B){if(!(ON.hoso||CBCN.dung('kld')||CBCN.dung('kldg'))||!B.D||B.D.nguon!=='mt5')return;const ma=B.D.khac_vang?B.D.ma:'',tf=B.D.tf||'',k=ma+'|'+tf,c=KLM.get(k);
 if(c&&c.m){const v=B.D.vol||(B.D.vol={});if(B.D._kl!==k){for(const[t,x]of c.m)if(v[t]==null)v[t]=x;B.D._kl=k;const F=window.CBPL&&CBPL.PL.on&&CBPL.PL.F;if(F){F._kl=k;F.vol=v}CBCN.tinhLai();capNhat()}return}
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
sm.addEventListener('change',()=>{const B=BD();if(B?.LW)ssBo(B.LW.chart);ON.ss=sm.value;luu();ve()});
addEventListener('chart-context-changing',()=>{const B=BD();if(B?.LW)ssBo(B.LW.chart)});
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')ssDong()});
const pop=dt.querySelector('.pop');dt.addEventListener('toggle',()=>{if(!dt.open)return;const dl=v=>{pop.style.setProperty('left',v,'important');pop.style.setProperty('right','auto','important')};dl('0px');const r=pop.getBoundingClientRect(),o=dt.getBoundingClientRect(),mx=document.documentElement.clientWidth-12;if(r.right>mx)dl(Math.max(12-o.left,mx-r.right)+'px')});   // dời sang trái cho vừa màn hình hẹp
let dsNap=0;dt.addEventListener('toggle',async()=>{if(!dt.open||dsNap)return;dsNap=1;try{const j=await(await fetch('/api/ma?gon=1',{cache:'no-store'})).json(),B=BD(),hien=B&&B.D&&B.D.khac_vang?B.D.ma:'';
 sm.innerHTML='<option value="">Không so sánh</option>'+(j.ds||[]).filter(x=>x.ma!==hien).map(x=>`<option value="${esc(x.ma)}">${esc(x.ma)}</option>`).join('');sm.value=ON.ss||''}
 catch(e){dsNap=0}});
if(ON.ss){const o=document.createElement('option');o.value=ON.ss;o.textContent=ON.ss;sm.append(o);sm.value=ON.ss}
addEventListener('click',e=>{if(dt.open&&!dt.contains(e.target))dt.open=false});
// ---------------------------------------------------------------- AI biểu đồ dùng chung
for(const [mode,label] of [['indicators','AI đọc chỉ báo'],['explain','AI giải thích']]){
 const button=document.createElement('button');button.type='button';button.className='ghost nho';button.textContent=label;
 button.addEventListener('click',()=>window.AI_CHART?.open(mode));dt.after(button)}
window.CBTH={ON,phien,PRIM,ssNap}})();
"""
