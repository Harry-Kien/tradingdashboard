"""Các kiểu chart và hướng dẫn; chỉ thay cách hiển thị, giữ nguyên dữ liệu giá gốc."""

CSS = """
.ct-pick{display:inline-flex;align-items:center;gap:6px;max-width:100%}.ct-pick select{max-width:190px!important}.ct-pick button{min-width:32px}
.ct-note{font-size:14px;line-height:1.45;margin:6px 0;color:var(--ink2);overflow-wrap:anywhere}.ct-note[hidden]{display:none}
#ct-dialog{box-sizing:border-box;width:min(580px,calc(100vw - 24px));max-height:calc(100dvh - 24px);padding:0;border:1px solid var(--line);border-radius:14px;background:var(--card);color:var(--ink);overflow:auto;box-shadow:0 20px 80px #0008}
#ct-dialog::backdrop{background:#0009}#ct-dialog header{position:sticky;top:0;display:flex;gap:12px;align-items:center;justify-content:space-between;background:var(--card);padding:16px;border-bottom:1px solid var(--line)}
#ct-dialog h2{font-size:18px;margin:0}#ct-dialog .ct-body{display:grid;gap:14px;padding:16px;font-size:14px;line-height:1.6}#ct-dialog p{margin:0}#ct-dialog label{display:grid;gap:6px}
#ct-dialog select,#ct-dialog input{box-sizing:border-box;min-height:40px;max-width:100%;width:100%;font:inherit;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:7px;padding:8px}
#ct-dialog button{font:inherit;min-height:38px}#ct-dialog [hidden]{display:none!important}#ct-dialog .ct-baseline{border-top:1px solid var(--line);padding-top:14px;display:grid;gap:12px}#ct-message{color:var(--series)}#ct-error{color:var(--loss)}
.ct-raw-label{color:var(--series)}
"""

CORE_JS = r"""
const CTMath=(()=>{
 function heikin(cs){let ho=null,hc=null;return cs.map(r=>{const c=(r[1]+r[2]+r[3]+r[4])/4,o=ho===null?(r[1]+r[4])/2:(ho+hc)/2;ho=o;hc=c;return[r[0],o,Math.max(r[2],o,c),Math.min(r[3],o,c),c]})}
 const sig=r=>r?.slice(0,5).join('|');
 function cache(){let src=null,rows=[],tail=[];return{read(cs){let full=src!==cs||rows.length>cs.length||!rows.length||rows[0]?.[0]!==cs[0]?.[0];
   if(!full)for(const[i,s]of tail)if(i<rows.length-1&&sig(cs[i])!==s){full=true;break}
   if(full)rows=heikin(cs);else{const from=Math.max(0,rows.length-1);for(let i=from;i<cs.length;i++){const r=cs[i],p=rows[i-1],c=(r[1]+r[2]+r[3]+r[4])/4,o=p?(p[1]+p[4])/2:(r[1]+r[4])/2;rows[i]=[r[0],o,Math.max(r[2],o,c),Math.min(r[3],o,c),c]}}
   src=cs;tail=cs.slice(-4).map((r,j)=>[cs.length-Math.min(4,cs.length)+j,sig(r)]);return{rows,full}}}}
 function hollow(cs,i,up,down){const r=cs[i],prev=i?cs[i-1][4]:r[1],color=r[4]>=prev?up:down;return{time:r[0],open:r[1],high:r[2],low:r[3],close:r[4],color:r[4]>=r[1]?'rgba(0,0,0,0)':color,wickColor:color,borderColor:color}}
 function base(cs,mode,value){if(mode==='custom'&&typeof value==='number'&&Number.isFinite(value)&&value>0)return value;if(mode==='first')return cs[0]?.[4]??null;const a=cs.slice(-200);return a.length?a.reduce((s,r)=>s+r[4],0)/a.length:null}
 return{heikin,cache,hollow,base};
})();
"""

RENDER_JS = CORE_JS + r"""
const ctEn=document.documentElement?.lang==='en',ctT=(a,b)=>ctEn?b:a;
const KIEU={nen:ctT('Nến','Candles'),rong:ctT('Nến rỗng','Hollow candles'),ha:'Heikin Ashi',thanh:ctT('Thanh OHLC','OHLC bars'),hlc:ctT('Thanh HLC','HLC bars'),duong:ctT('Đường giá đóng','Close line'),bac:ctT('Đường bậc thang','Step line'),diem:ctT('Đường có điểm','Line with markers'),vung:ctT('Vùng','Area'),coso:ctT('Đường cơ sở','Baseline')};
const ctUser=window.HVD_CHU,ctKey='so-kieu-bd:'+(ctUser?'u_'+ctUser.id:'khach');let KBD='nen',ctSaved=true;
try{KBD=localStorage.getItem(ctKey)||((ctUser?.chu&&localStorage.getItem('so-kieu-bd'))||'nen');if(!KIEU[KBD])KBD='nen'}catch(e){ctSaved=false}
let PHU=null,ctChart=null,ctOriginal=null,PHUK='',ctContext='',ctBase={mode:'avg200',value:null},ctNote=null,ctSelect=null,ctDialog=null;
const ctHA=CTMath.cache(),heikin=CTMath.heikin;
function ctBaseKey(B){return ctKey+':base:'+encodeURIComponent(B.D.ma||'XAUUSD')+':'+(B.D.tf||'')}
function ctLoadBase(B){const key=ctBaseKey(B);if(key===ctContext)return;ctContext=key;ctBase={mode:'avg200',value:null};try{const x=JSON.parse(localStorage.getItem(key)||'null');if(x&&['avg200','first','custom'].includes(x.mode)&&Number.isFinite(x.value)&&x.value>0)ctBase=x;else if(x&&['avg200','first'].includes(x.mode))ctBase={mode:x.mode,value:null}}catch(e){}}
function ctMask(o){return KBD==='nen'?o:{...o,color:'rgba(0,0,0,0)',wickColor:'rgba(0,0,0,0)',borderColor:'rgba(0,0,0,0)'}}
function ctRemove(){if(PHU&&ctChart)try{ctChart.removeSeries(PHU)}catch(e){}PHU=null;PHUK=''}
function ctDescription(){return({nen:ctT('Nến OHLC gốc: thân thể hiện giá mở/đóng, râu thể hiện cao/thấp.','Original OHLC candles: bodies show open/close; wicks show high/low.'),rong:ctT('Thân rỗng khi đóng ≥ mở, thân đặc khi đóng < mở. Màu xanh/đỏ so với giá đóng nến trước.','Hollow when close ≥ open; filled when close < open. Color compares close with the previous close.'),ha:ctT('Heikin Ashi làm mượt bằng giá trung bình, không phải giá khớp lệnh. OHLC, CSV, chỉ báo và mô phỏng vẫn dùng nến gốc.','Heikin Ashi smooths average prices; these are not execution prices. OHLC, CSV, indicators and simulation still use original candles.'),thanh:ctT('Thanh OHLC: cao/thấp trên thanh dọc, mở ở bên trái, đóng ở bên phải.','OHLC bars: vertical high/low, open on the left, close on the right.'),hlc:ctT('Thanh HLC chỉ thể hiện cao, thấp và đóng; ẩn dấu giá mở cửa.','HLC bars show high, low and close, with the open tick hidden.'),duong:ctT('Nối giá đóng của mỗi nến để xem xu hướng gọn hơn.','Connects each candle close for a simpler trend view.'),bac:ctT('Giữ mức giá đóng tới nến tiếp theo, tạo đường bậc thang.','Holds each close until the next candle to create a step line.'),diem:ctT('Đường giá đóng có điểm đánh dấu từng nến; phóng to để đọc các điểm rõ hơn.','Close line with a marker for each candle; zoom in to separate markers.'),vung:ctT('Đường giá đóng với vùng tô bên dưới.','Close line with a filled area underneath.'),coso:ctT('Tô màu trên/dưới mức giá cơ sở đã chọn. Mốc tự động chỉ dùng nến đã tải hoặc đã phát.','Colors above/below the selected reference price. Automatic references use only loaded or revealed candles.')})[KBD]}
function ctPaint(B){if(ctSelect)ctSelect.value=KBD;if(ctNote){ctNote.hidden=!['ha','coso'].includes(KBD);ctNote.textContent=KBD==='ha'?ctDescription():KBD==='coso'&&B?.D?.candles?.length?ctT('Giá cơ sở: ','Baseline price: ')+CTMath.base(B.D.candles,ctBase.mode,ctBase.value).toLocaleString(ctEn?'en-US':'vi-VN',{maximumFractionDigits:8})+' · '+({avg200:ctT('trung bình tối đa 200 nến cuối','average of up to 200 latest candles'),first:ctT('giá đóng nến đầu đã tải','first loaded candle close'),custom:ctT('tự nhập cho mã/khung này','custom for this symbol/timeframe')})[ctBase.mode]:''}
 if(ctDialog?.open){ctDialog.querySelector('#ct-kind-detail').value=KBD;ctDialog.querySelector('#ct-desc').textContent=ctDescription();ctDialog.querySelector('.ct-baseline').hidden=KBD!=='coso';ctDialog.querySelector('#ct-message').textContent=ctSaved?'':ctT('Đang dùng cho phiên này; trình duyệt chưa cho phép lưu lựa chọn.','Applied for this session; browser storage is unavailable.')}}
function ctRender(B){const LW=B.LW,c=LW.chart,LWC=window.LightweightCharts,cs=B.D.candles,P=B.P||{},up=P.bull||'#26a69a',down=P.bear||'#ef5350',blue=P.series||'#2962ff';ctLoadBase(B);
 if(c!==ctChart||LW.nen!==ctOriginal){ctRemove();ctChart=c;ctOriginal=LW.nen}
 if(KBD!==PHUK){ctRemove();PHUK=KBD;const common={priceLineVisible:false,lastValueVisible:false,priceFormat:LW.nen.options().priceFormat};
  if(['ha','rong'].includes(KBD))PHU=c.addSeries(LWC.CandlestickSeries,common,0);
  else if(['thanh','hlc'].includes(KBD))PHU=c.addSeries(LWC.BarSeries,{...common,thinBars:false,openVisible:KBD!=='hlc'},0);
  else if(['duong','bac','diem'].includes(KBD))PHU=c.addSeries(LWC.LineSeries,{...common,lineWidth:2,lineType:KBD==='bac'?1:0,pointMarkersVisible:KBD==='diem',pointMarkersRadius:3},0);
  else if(KBD==='vung')PHU=c.addSeries(LWC.AreaSeries,{...common,lineWidth:2},0);
  else if(KBD==='coso')PHU=c.addSeries(LWC.BaselineSeries,{...common,lineWidth:2},0)}
 if(PHU){PHU.applyOptions({priceFormat:LW.nen.options().priceFormat});if(['ha','rong'].includes(KBD))PHU.applyOptions({upColor:up,downColor:down,wickUpColor:up,wickDownColor:down,borderUpColor:up,borderDownColor:down});
  else if(['thanh','hlc'].includes(KBD))PHU.applyOptions({upColor:up,downColor:down});
  else if(['duong','bac','diem'].includes(KBD))PHU.applyOptions({color:blue});
  else if(KBD==='vung')PHU.applyOptions({lineColor:blue,topColor:blue+'55',bottomColor:blue+'05'});
  else if(KBD==='coso')PHU.applyOptions({baseValue:{type:'price',price:CTMath.base(cs,ctBase.mode,ctBase.value)},topLineColor:up,bottomLineColor:down,topFillColor1:up+'44',topFillColor2:up+'08',bottomFillColor1:down+'08',bottomFillColor2:down+'44'});
  const ha=KBD==='ha'?ctHA.read(cs):null,ds=ha?ha.rows:cs,make=i=>{const r=ds[i];return KBD==='rong'?CTMath.hollow(cs,i,up,down):['ha','thanh','hlc'].includes(KBD)?{time:r[0],open:r[1],high:r[2],low:r[3],close:r[4]}:{time:r[0],value:r[4]}};
  CHART_RT.gui(PHU,cs.length,make,cs,!ha?.full)}
 ctPaint(B)}
function kieuVe(B){try{ctRender(B)}catch(e){ctRemove();KBD='nen';const P=B.P||{};B.LW.nen.applyOptions({upColor:P.bull||'#26a69a',downColor:P.bear||'#ef5350',wickUpColor:P.wick||'#26a69a',wickDownColor:P.wickDn||'#ef5350'});B.LW.nen.setData(B.D.candles.map(r=>({time:r[0],open:r[1],high:r[2],low:r[3],close:r[4]})));ctPaint(B);console.warn('Khôi phục nến gốc:',e)}}
function ctTick(){const B=window.BDCB?.();if(B?.LW&&B.D?.candles?.length)kieuVe(B)}
function ctChange(k){if(!KIEU[k])return;KBD=k;try{localStorage.setItem(ctKey,k);ctSaved=true}catch(e){ctSaved=false}window.BDPL?.ve();ctPaint(window.BDCB?.())}
addEventListener('chart-context-changing',()=>{ctRemove();ctContext='';if(ctDialog?.open)ctDialog.close();if(ctNote)ctNote.hidden=true});
"""

UI_JS = r"""
 const ch=document.createElement('div');ch.className='ct-pick';
 const lab=document.createElement('label');lab.className='sel cbcn-kieu';lab.title=ctT('Chọn kiểu biểu đồ','Choose chart type');
 const options=Object.entries(KIEU).map(([k,n])=>`<option value="${k}">${n}</option>`).join('');lab.innerHTML='<select id="ct-kind" aria-label="'+ctT('Dạng biểu đồ','Chart type')+'">'+options+'</select>';ctSelect=lab.querySelector('select');ctSelect.value=KBD;ctSelect.addEventListener('change',e=>ctChange(e.target.value));
 const help=document.createElement('button');help.type='button';help.className='ghost nho';help.id='ct-help';help.textContent='?';help.title=ctT('Giải thích & cài đặt kiểu biểu đồ','Chart type guide & settings');help.setAttribute('aria-label',help.title);help.setAttribute('aria-haspopup','dialog');ch.append(lab,help);nut.before(ch);
 ctNote=document.createElement('p');ctNote.className='ct-note';ctNote.hidden=true;ctNote.setAttribute('role','note');const stage=document.querySelector('.stage');stage?.before(ctNote);
 ctDialog=document.createElement('dialog');ctDialog.id='ct-dialog';ctDialog.setAttribute('aria-labelledby','ct-title');ctDialog.innerHTML=`<header><h2 id="ct-title">${ctT('Kiểu biểu đồ','Chart types')}</h2><button type="button" id="ct-close" class="ghost nho">${ctT('Đóng','Close')} ×</button></header><div class="ct-body"><label>${ctT('Chọn cách xem giá','Choose a price view')}<select id="ct-kind-detail">${options}</select></label><p id="ct-desc"></p><form class="ct-baseline"><label>${ctT('Mức cơ sở','Reference price')}<select id="ct-base-mode"><option value="avg200">${ctT('Trung bình 200 nến cuối','Average of last 200 candles')}</option><option value="first">${ctT('Giá đóng nến đầu đã tải','First loaded close')}</option><option value="custom">${ctT('Tự nhập giá','Custom price')}</option></select></label><label id="ct-custom-label" hidden>${ctT('Giá cơ sở cho mã/khung này','Reference for this symbol/timeframe')}<input id="ct-base-price" type="number" step="any" min="0" inputmode="decimal"></label><button type="submit" class="ghost nho">${ctT('Áp dụng mức cơ sở','Apply reference')}</button><p id="ct-error" role="alert"></p></form><p>${ctT('Đổi kiểu chỉ thay cách nhìn. Chỉ báo, mức vào/SL/TP, dữ liệu nến và lệnh luyện tập tính theo giá gốc. Lựa chọn được nhớ riêng cho tài khoản trên trình duyệt này.','Changing chart type changes the view. Indicators, entry/SL/TP, candle data and practice orders use original prices. Your choice is remembered for your account in this browser.')}</p><p id="ct-message" role="status" aria-live="polite"></p><button type="button" id="ct-reset" class="ghost nho">${ctT('Về nến tiêu chuẩn','Use standard candles')}</button></div>`;document.querySelector('#cp')?.append(ctDialog);
 function ctBaseControls(){ctDialog.querySelector('#ct-base-mode').value=ctBase.mode;ctDialog.querySelector('#ct-base-price').value=ctBase.value??'';ctDialog.querySelector('#ct-custom-label').hidden=ctBase.mode!=='custom';ctDialog.querySelector('#ct-error').textContent=''}
 help.onclick=()=>{if(document.querySelector('dialog[open]'))return;const B=window.BDCB?.();if(B?.D)ctLoadBase(B);ctBaseControls();ctDialog.showModal();ctPaint(B);ctDialog.querySelector('#ct-close').focus()};ctDialog.querySelector('#ct-close').onclick=()=>ctDialog.close();ctDialog.addEventListener('close',()=>help.focus());
 ctDialog.querySelector('#ct-kind-detail').onchange=e=>{ctChange(e.target.value);ctBaseControls()};ctDialog.querySelector('#ct-base-mode').onchange=e=>{ctDialog.querySelector('#ct-custom-label').hidden=e.target.value!=='custom'};
 ctDialog.querySelector('form').onsubmit=e=>{e.preventDefault();const B=window.BDCB?.(),mode=ctDialog.querySelector('#ct-base-mode').value,input=ctDialog.querySelector('#ct-base-price'),value=input.value.trim()===''?null:Number(input.value);if(!B?.D)return;
  if(mode==='custom'&&(!(value>0)||!Number.isFinite(value))){ctDialog.querySelector('#ct-error').textContent=ctT('Nhập giá cơ sở lớn hơn 0.','Enter a reference price greater than zero.');return}ctBase={mode,value:mode==='custom'?value:null};try{localStorage.setItem(ctBaseKey(B),JSON.stringify(ctBase));ctSaved=true}catch(er){ctSaved=false}ctDialog.querySelector('#ct-error').textContent='';ctTick();ctDialog.querySelector('#ct-message').textContent=ctSaved?ctT('Đã áp dụng và lưu cho mã/khung này.','Applied and saved for this symbol/timeframe.'):ctT('Đã áp dụng trong phiên này; chưa lưu được trên trình duyệt.','Applied for this session; browser storage is unavailable.')};
 ctDialog.querySelector('#ct-reset').onclick=()=>{ctChange('nen');ctDialog.close()};
 addEventListener('keydown',e=>{if(!ctDialog.open)return;e.stopImmediatePropagation();if(e.key==='Escape'){e.preventDefault();ctDialog.close()}else if(e.key==='Tab'){const es=[...ctDialog.querySelectorAll('button,select,input')].filter(x=>!x.disabled&&x.getClientRects().length),a=es[0],b=es.at(-1);if(e.shiftKey&&document.activeElement===a){e.preventDefault();b.focus()}else if(!e.shiftKey&&document.activeElement===b){e.preventDefault();a.focus()}}},true);
 ctSelect.disabled=!window.BDCB?.()?.LW;if(ctSelect.disabled)help.title=ctT('Thư viện biểu đồ chưa sẵn sàng; đang dùng nến dự phòng.','Chart library unavailable; using fallback candles.');ctPaint(window.BDCB?.());
"""
