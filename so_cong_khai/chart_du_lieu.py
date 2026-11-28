"""Đọc/xuất nến và điều hướng lịch sử đã tải; không đọc tài khoản, không gọi MT5.

Trục thời gian có thể chứa điểm của series khác: luôn đổi timestamp bằng
timeToIndex, không dùng vị trí trong mảng nến làm logical index.
"""

CSS = """
#cd-dialog{box-sizing:border-box;width:min(700px,calc(100vw - 24px));max-height:calc(100dvh - 24px);padding:0;border:1px solid var(--line);border-radius:14px;background:var(--card);color:var(--ink);overflow:auto;box-shadow:0 20px 80px #0008}
#cd-dialog::backdrop{background:#0009}#cd-dialog *{box-sizing:border-box}
#cd-dialog .cd-head{position:sticky;top:0;background:var(--card);z-index:1;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px 20px;border-bottom:1px solid var(--line)}
#cd-dialog h2{font-size:18px;margin:0}#cd-dialog .cd-body{padding:16px 20px;display:grid;gap:16px}
#cd-dialog .cd-row{display:flex;align-items:center;flex-wrap:wrap;gap:8px}#cd-dialog button,#cd-dialog select,#cd-dialog input{font:inherit;min-height:38px;max-width:100%}
#cd-dialog select,#cd-dialog input{background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:7px;padding:7px 9px;color-scheme:inherit}
#cd-dialog label{display:grid;gap:6px;font-size:13px;color:var(--ink2)}#cd-dialog label.cd-check{display:flex;align-items:center;gap:8px}#cd-dialog input[type=checkbox]{min-height:18px;width:18px;flex:none}
#cd-dialog .cd-tabs{display:flex;gap:8px}#cd-dialog .cd-tabs [aria-selected=true]{border-color:var(--series);color:var(--series)}
#cd-dialog [hidden]{display:none!important}#cd-dialog .cd-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
#cd-dialog .cd-cell{min-width:0;border:1px solid var(--line);border-radius:9px;padding:12px;display:grid;gap:5px}#cd-dialog .cd-cell dt{font-size:12px;color:var(--mute)}#cd-dialog .cd-cell dd{font-size:19px;font-weight:650;font-variant-numeric:tabular-nums;margin:0;overflow-wrap:anywhere}
#cd-dialog dl{margin:0}#cd-dialog .cd-note,#cd-dialog .cd-status{font-size:12px;line-height:1.6;color:var(--ink2);margin:0;overflow-wrap:anywhere}
#cd-dialog .cd-status{min-height:20px;color:var(--series)}#cd-dialog .cd-status[data-error=true]{color:var(--loss)}#cd-dialog .cd-divider{border-top:1px solid var(--line);padding-top:14px;display:grid;gap:10px}
#cd-dialog .cd-date{flex:1;min-width:180px}#cd-dialog button:focus-visible,#cd-dialog input:focus-visible,#cd-dialog select:focus-visible{outline:2px solid var(--series);outline-offset:2px}
@media(max-width:480px){#cd-dialog .cd-body{padding:14px}#cd-dialog .cd-head{padding:14px}#cd-dialog .cd-cell dd{font-size:17px}}
"""

CORE_JS = r"""
const CandleData=(()=>{
 const finite=x=>typeof x==='number'&&Number.isFinite(x);
 const valid=c=>Array.isArray(c)&&c.length>=5&&c.slice(0,5).every(finite)&&c[0]>=0&&c[2]>=Math.max(c[1],c[3],c[4])&&c[3]<=Math.min(c[1],c[4]);
 function lower(cs,t){let a=0,b=cs.length;while(a<b){const m=(a+b)>>1;if(cs[m][0]<t)a=m+1;else b=m}return a}
 function nearest(cs,t){if(!cs.length||!finite(t)||t<cs[0][0]||t>cs[cs.length-1][0])return -1;const i=lower(cs,t);return i>0&&t-cs[i-1][0]<=cs[i][0]-t?i-1:i}
 function parse(s,offset){if(![0,420].includes(offset))return null;const m=/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(s);if(!m)return null;
  const [y,mo,d,h,mi,se]=m.slice(1).map(x=>+(x||0));if(y<1970||y>9999)return null;const x=new Date(Date.UTC(y,mo-1,d,h,mi,se));
  if(x.getUTCFullYear()!==y||x.getUTCMonth()!==mo-1||x.getUTCDate()!==d||x.getUTCHours()!==h||x.getUTCMinutes()!==mi||x.getUTCSeconds()!==se)return null;return x.getTime()/1000-offset*60}
 const local=(t,offset)=>new Date((t+offset*60)*1000).toISOString().slice(0,19);
 function cutoff(t,k){if(k==='all')return -Infinity;const n=+k.slice(0,-1),unit=k.slice(-1);if(unit==='d')return t-n*86400;
  const x=new Date(t*1000),day=x.getUTCDate();x.setUTCDate(1);x.setUTCMonth(x.getUTCMonth()-(unit==='y'?n*12:n));
  const end=new Date(Date.UTC(x.getUTCFullYear(),x.getUTCMonth()+1,0)).getUTCDate();x.setUTCDate(Math.min(day,end));return x.getTime()/1000}
 function mapped(ts,t){const n=ts.timeToIndex(t,false);return finite(n)?n:null}
 function centered(ts,t){const i=mapped(ts,t);if(i===null)return null;const old=ts.getVisibleLogicalRange(),w=old&&finite(old.from)&&finite(old.to)?Math.max(20,old.to-old.from):100;return{from:i-w/2,to:i+w/2}}
 function span(ts,cs,start,end){const a=mapped(ts,cs[start][0]),b=mapped(ts,cs[end][0]);return a===null||b===null?null:{from:a-1,to:Math.max(a+1,b+1)}}
 function cell(v){let s=String(v??'');if(typeof v==='string'&&/^[\s]*[=+\-@]/.test(s))s="'"+s;return (/[",\r\n]/).test(s)?'"'+s.replace(/"/g,'""')+'"':s}
 function csv(D,symbol,tf,scope,ts,forming){const cs=D.candles||[],range=scope==='visible'?ts?.getVisibleLogicalRange():null;if(scope==='visible'&&!range)throw Error('visible');
  const rows=[['time_utc','symbol','timeframe','open','high','low','close','tick_volume','status']],live=Number.isInteger(D.live)?D.live:-1;let skipped=0;
  for(let i=0;i<cs.length;i++){const c=cs[i];if(!valid(c)){skipped++;continue}if(i===live&&!forming)continue;
   if(range){const ix=mapped(ts,c[0]);if(ix===null||ix<range.from||ix>range.to)continue}
   const v=D.vol?.[c[0]],volume=finite(v)&&v>=0?v:'';rows.push([new Date(c[0]*1000).toISOString(),symbol,tf,c[1],c[2],c[3],c[4],volume,i===live?'forming':'closed'])}
  return{text:'\uFEFF'+rows.map(r=>r.map(cell).join(',')).join('\r\n')+'\r\n',count:rows.length-1,skipped}}
 return{valid,lower,nearest,parse,local,cutoff,mapped,centered,span,csv};
})();
"""

JS = r"""(()=>{'use strict';
""" + CORE_JS + r"""
const cp=document.getElementById('cp'),tools=cp?.querySelector('.tools.t2');if(!cp||!tools)return;
const en=document.documentElement.lang==='en',T=(vi,eng)=>en?eng:vi,$=s=>dialog.querySelector(s),BD=()=>window.BDMN?.();
const button=document.createElement('button');button.type='button';button.id='cd-open';button.className='ghost nho';button.textContent=T('Dữ liệu','Data');button.title=T('Đọc/xuất nến · Đến ngày (Alt+G)','Candle data/export · Go to date (Alt+G)');button.setAttribute('aria-haspopup','dialog');tools.append(button);
const dialog=document.createElement('dialog');dialog.id='cd-dialog';dialog.setAttribute('aria-labelledby','cd-title');
dialog.innerHTML=`<header class="cd-head"><h2 id="cd-title">${T('Dữ liệu & điều hướng','Data & navigation')}</h2><button type="button" class="ghost nho" id="cd-close">${T('Đóng','Close')} ×</button></header>
<div class="cd-body"><div class="cd-tabs" role="tablist" aria-label="${T('Tiện ích nến','Candle utilities')}"><button type="button" class="ghost nho" role="tab" id="cd-data-tab" aria-controls="cd-data" aria-selected="true">${T('Dữ liệu nến','Candle data')}</button><button type="button" class="ghost nho" role="tab" id="cd-nav-tab" aria-controls="cd-nav" aria-selected="false" tabindex="-1">${T('Điều hướng','Navigate')}</button></div>
<p id="cd-context" class="cd-note"></p><label>${T('Múi giờ hiển thị','Display timezone')}<select id="cd-zone"><option value="420">${T('Việt Nam (UTC+7)','Vietnam (UTC+7)')}</option><option value="0">UTC</option></select></label>
<section id="cd-data" role="tabpanel" aria-labelledby="cd-data-tab"><div class="cd-row"><button type="button" class="ghost nho" id="cd-prev" aria-label="${T('Nến trước','Previous candle')}">←</button><button type="button" class="ghost nho" id="cd-next" aria-label="${T('Nến tiếp','Next candle')}">→</button><button type="button" class="ghost nho" id="cd-latest">${T('Theo nến mới nhất','Follow latest candle')}</button></div>
<p id="cd-time" class="cd-note"></p><dl class="cd-grid">${[['open',T('Mở cửa','Open')],['high',T('Cao nhất','High')],['low',T('Thấp nhất','Low')],['close',T('Đóng / giá cuối','Close / last')],['body',T('Thân nến (C − O)','Candle body (C − O)')],['range',T('Biên độ (H − L)','Range (H − L)')],['volume',T('Tick volume','Tick volume')],['state',T('Trạng thái nến','Candle status')]].map(([k,v])=>`<div class="cd-cell"><dt>${v}</dt><dd id="cd-value-${k}">—</dd></div>`).join('')}</dl>
<div class="cd-divider"><p class="cd-note">${T('Di chuột trên biểu đồ rồi mở cửa sổ để đọc nến đó. Tick volume là số lần giá thay đổi, không phải khối lượng khớp lệnh.','Hover over the chart, then open this window to read that candle. Tick volume counts price updates, not traded volume.')}</p><div class="cd-row"><label>${T('Phạm vi xuất CSV','CSV export scope')}<select id="cd-scope"><option value="visible">${T('Đoạn đang xem','Visible candles')}</option><option value="loaded">${T('Toàn bộ nến đã tải','All loaded candles')}</option></select></label><button type="button" class="ghost nho" id="cd-export">${T('Tải CSV','Download CSV')}</button></div><label class="cd-check"><input type="checkbox" id="cd-forming">${T('Bao gồm nến chưa đóng (có đánh dấu)','Include the forming candle (labelled)')}</label><p class="cd-note">${T('CSV chỉ chứa dữ liệu nến, giờ UTC và tick volume nếu có. Trong phát lại chỉ xuất nến đã được mở tới thời điểm hiện tại.','CSV contains candle data, UTC timestamps and tick volume where available. Replay exports only candles revealed so far.')}</p></div></section>
<section id="cd-nav" role="tabpanel" aria-labelledby="cd-nav-tab" hidden><form id="cd-form" class="cd-row"><label class="cd-date">${T('Đến ngày & giờ','Go to date & time')}<input id="cd-date" type="datetime-local" step="1" required></label><button class="ghost nho" type="submit">${T('Đến nến','Go to candle')}</button></form><div class="cd-divider"><p class="cd-note">${T('Xem nhanh tính từ nến cuối đã tải','Quick range ending at the last loaded candle')}</p><div class="cd-row" id="cd-ranges">${[['1d','1D'],['5d','5D'],['1m','1M'],['3m','3M'],['6m','6M'],['1y','1Y'],['all',T('Tất cả','All')]].map(([k,v])=>`<button type="button" class="ghost nho" data-range="${k}">${v}</button>`).join('')}</div><p class="cd-note">${T('D = ngày, M = tháng, Y = năm. Ngày nghỉ sẽ chọn nến gần nhất. Chỉ điều hướng trong lịch sử đã tải; chọn khung lớn hơn để xem xa hơn.','D = days, M = months, Y = years. Market gaps select the nearest candle. Navigation is limited to loaded history; use a higher timeframe for a longer history.')}</p></div></section>
<p class="cd-note" id="cd-bounds"></p><p class="cd-status" id="cd-status" role="status" aria-live="polite"></p></div>`;
cp.append(dialog);
let chart=null,picked=null,follow=true,queued=false,lastContext='',restore=button;
const say=(s,error=false)=>{$('#cd-status').textContent=s;$('#cd-status').dataset.error=String(error)};
const num=x=>typeof x==='number'&&Number.isFinite(x)?x.toLocaleString(en?'en-US':'vi-VN',{maximumFractionDigits:8}):'—';
const offset=()=>+$('#cd-zone').value;
const stamp=t=>CandleData.local(t,offset()).replace('T',' ')+' '+(offset()?'UTC+7':'UTC');
function current(){const B=BD();return B?.D?.candles?.length&&B.LW?.chart?B:null}
function index(B){const cs=B.D.candles;if(follow||picked===null)return cs.length-1;const i=CandleData.nearest(cs,picked);return i<0?cs.length-1:i}
function tab(nav,focus=false){for(const [id,on]of [['nav',nav],['data',!nav]]){const b=$('#cd-'+id+'-tab');b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;$('#cd-'+id).hidden=!on}if(focus)$('#cd-'+(nav?'nav':'data')+'-tab').focus()}
function render(){if(!dialog.open)return;const B=current(),ok=!!B;dialog.querySelectorAll('#cd-prev,#cd-next,#cd-latest,#cd-export,#cd-form button,#cd-ranges button').forEach(b=>b.disabled=!ok);
 if(!B){$('#cd-context').textContent=T('Chưa có dữ liệu nến. Chờ tải biểu đồ.','No candle data yet. Wait for the chart to load.');$('#cd-bounds').textContent='';$('#cd-time').textContent='';dialog.querySelectorAll('dd').forEach(e=>e.textContent='—');return}
 const D=B.D,cs=D.candles,i=index(B),c=cs[i],symbol=B.ma||D.ma||'XAUUSD',tf=D.tf||B.tf||'';
 $('#cd-context').textContent=symbol+' · '+tf+' · '+(D.nguon==='mt5'?T('Nguồn MT5 · chỉ đọc','MT5 source · read only'):T('Kho nến của hệ thống','System candle store'))+(window.BDPL?.chan?T(' · PHÁT LẠI',' · REPLAY'):'');
 $('#cd-bounds').textContent=T('Đã tải: ','Loaded: ')+stamp(cs[0][0])+' → '+stamp(cs[cs.length-1][0])+' · '+num(cs.length)+T(' nến',' candles');
 $('#cd-time').textContent=stamp(c[0])+' · '+(follow?T('Theo nến mới nhất','Following latest'):T('Nến đã chọn','Selected candle'));
 $('#cd-prev').disabled=i===0;$('#cd-next').disabled=i===cs.length-1;
 for(const [k,j]of [['open',1],['high',2],['low',3],['close',4]])$('#cd-value-'+k).textContent=num(c[j]);
 const body=c[4]-c[1];$('#cd-value-body').textContent=num(body)+(c[1]?' ('+num(body/c[1]*100)+'%)':'');$('#cd-value-range').textContent=num(c[2]-c[3]);
 const v=D.vol?.[c[0]];$('#cd-value-volume').textContent=typeof v==='number'&&v>=0?num(v):T('Chưa có','Unavailable');$('#cd-value-state').textContent=D.live===i?T('Chưa đóng','Forming'):T('Đã đóng','Closed');
}
function schedule(){if(queued||!dialog.open)return;queued=true;requestAnimationFrame(()=>{queued=false;render()})}
function cursor(p){if(typeof p.time==='number'){const B=current();if(B&&CandleData.nearest(B.D.candles,p.time)>=0){picked=p.time;follow=false;schedule()}}}
function attach(B){if(!B?.LW?.chart)return;if(chart!==B.LW.chart){if(chart)chart.unsubscribeCrosshairMove(cursor);chart=B.LW.chart;chart.subscribeCrosshairMove(cursor)}const key=(B.D._chart_epoch??'')+'|'+(B.D.ma||'')+'|'+(B.D.tf||'');if(key!==lastContext){lastContext=key;picked=null;follow=true}schedule()}
if(window.CBCN)CBCN.moc.push(attach);const initial=current();if(initial)attach(initial);
function open(nav=false){if(document.querySelector('dialog[open]')&&!dialog.open)return;restore=document.activeElement||button;if(!dialog.open)dialog.showModal();say('');tab(nav);render();const B=current();if(B){const c=B.D.candles[index(B)];$('#cd-date').value=CandleData.local(c[0],offset())}$(nav?'#cd-date':'#cd-close').focus()}
function close(){if(dialog.open)dialog.close()}
button.onclick=()=>open();$('#cd-close').onclick=close;dialog.addEventListener('close',()=>{if(restore?.isConnected)restore.focus()});
$('#cd-data-tab').onclick=()=>tab(false);$('#cd-nav-tab').onclick=()=>tab(true);
$('#cd-zone').onchange=()=>{const B=current();if(B)$('#cd-date').value=CandleData.local(B.D.candles[index(B)][0],offset());render()};
$('#cd-prev').onclick=()=>step(-1);$('#cd-next').onclick=()=>step(1);function step(n){const B=current();if(!B)return;picked=B.D.candles[Math.max(0,Math.min(B.D.candles.length-1,index(B)+n))][0];follow=false;render()}
$('#cd-latest').onclick=()=>{follow=true;picked=null;render()};
function navigate(range,message){const B=current();if(!B||!range){say(T('Chưa định vị được nến trên trục thời gian.','Cannot locate this candle on the time axis.'),true);return}B.LW.chart.timeScale().setVisibleLogicalRange(range);say(message);close();B.toast?.(message)}
$('#cd-form').onsubmit=e=>{e.preventDefault();const B=current();if(!B)return;const t=CandleData.parse($('#cd-date').value,offset());if(t===null){say(T('Ngày giờ không hợp lệ.','Invalid date or time.'),true);return}
 const cs=B.D.candles,i=CandleData.nearest(cs,t);if(i<0){say(T('Ngày này nằm ngoài lịch sử đã tải. Hãy chọn trong khoảng bên dưới hoặc đổi khung.','This date is outside loaded history. Choose within the range below or change timeframe.'),true);return}
 picked=cs[i][0];follow=false;navigate(CandleData.centered(B.LW.chart.timeScale(),picked),T('Đã đến nến ','Moved to candle ')+stamp(picked)+(picked!==t?T(' · gần nhất với giờ đã chọn',' · nearest to selected time'):''))};
$('#cd-ranges').onclick=e=>{const k=e.target.closest('button[data-range]')?.dataset.range,B=current();if(!k||!B)return;const cs=B.D.candles,last=cs.length-1,t=CandleData.cutoff(cs[last][0],k),a=Math.min(last,CandleData.lower(cs,t));const partial=t<cs[0][0]&&k!=='all';
 navigate(CandleData.span(B.LW.chart.timeScale(),cs,a,last),partial?T('Đã hiển thị phần lịch sử hiện có; chưa đủ khoảng đã chọn.','Showing available history; the selected range is not fully loaded.'):T('Đã đổi khoảng thời gian.','Time range updated.'))};
$('#cd-export').onclick=()=>{const B=current();if(!B)return;try{const symbol=B.ma||B.D.ma||'XAUUSD',tf=B.D.tf||B.tf||'',out=CandleData.csv(B.D,symbol,tf,$('#cd-scope').value,B.LW.chart.timeScale(),$('#cd-forming').checked);
 if(!out.count){say(T('Không có nến phù hợp để xuất trong phạm vi đã chọn.','No matching candles to export in the selected range.'),true);return}
 const url=URL.createObjectURL(new Blob([out.text],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=('candles_'+symbol+'_'+tf+'_'+$('#cd-scope').value).replace(/[^a-zA-Z0-9_.-]/g,'_')+'.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
 say(T('Đã xuất ','Exported ')+num(out.count)+T(' nến · giờ UTC',' candles · UTC')+(out.skipped?T(' · bỏ qua dòng dữ liệu không hợp lệ: ',' · invalid rows skipped: ')+out.skipped:''))
 }catch(e){say(T('Không xuất được CSV. Hãy chờ biểu đồ tải xong rồi thử lại.','CSV export failed. Wait for the chart to load and try again.'),true)}};
// Capture trước các hotkey của chart; Tab vẫn giữ trong cửa sổ, Enter vẫn gửi form.
document.addEventListener('keydown',e=>{if(dialog.open){e.stopImmediatePropagation();if(e.key==='Escape'){e.preventDefault();close()}else if(e.target.closest('.cd-tabs')&&['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();tab(e.key==='End'||(e.key!=='Home'&&$('#cd-nav').hidden),true)}else if(e.key==='Tab'){const els=[...dialog.querySelectorAll('button,input,select')].filter(x=>!x.disabled&&x.tabIndex>=0&&x.getClientRects().length),a=els[0],b=els.at(-1);if(e.shiftKey&&document.activeElement===a){e.preventDefault();b.focus()}else if(!e.shiftKey&&document.activeElement===b){e.preventDefault();a.focus()}}return}
 if(e.altKey&&!e.ctrlKey&&!e.metaKey&&e.code==='KeyG'&&!e.target.closest('input,textarea,select,[contenteditable=true]')&&!document.querySelector('dialog[open]')){e.preventDefault();e.stopImmediatePropagation();open(true)}},true);
addEventListener('chart-context-changing',()=>{picked=null;follow=true;lastContext='';say('');close()});
})();
"""
