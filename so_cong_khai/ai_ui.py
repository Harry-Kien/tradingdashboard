"""Owner console and chart AI dialog. No secrets in HTML, storage or responses."""

CSS = r'''
.aip-back{position:fixed;inset:0;background:#0009;z-index:1800;display:grid;place-items:center;padding:16px}.aip-back[hidden]{display:none}
.aip-dialog{width:min(960px,100%);max-height:92dvh;overflow:auto;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:14px;box-shadow:0 20px 80px #0008}
.aip-head{position:sticky;top:0;background:var(--card);padding:14px 18px;display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--line);z-index:1}.aip-head b{flex:1}.aip-body{padding:18px;display:grid;gap:14px}
.aip-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}.aip-dialog button,.aip-admin button{font:inherit;cursor:pointer;border-radius:7px;border:1px solid var(--line);padding:8px 12px;background:var(--bg);color:var(--ink)}
.aip-dialog button:disabled,.aip-admin button:disabled{opacity:.5;cursor:default}.aip-dialog .primary,.aip-admin .primary{background:var(--series);color:var(--btn-ink);font-weight:700}
.aip-dialog textarea,.aip-admin textarea,.aip-admin input,.aip-admin select,.aip-dialog select{font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:7px;padding:8px;max-width:100%;box-sizing:border-box}
.aip-dialog textarea,.aip-admin textarea{width:100%;resize:vertical}.aip-muted{color:var(--mute);font-size:12px;line-height:1.6}.aip-warn{color:var(--warn,#e7ae46)}
.aip-result{line-height:1.65;overflow-wrap:anywhere}.aip-result h3{font-size:15px;margin:14px 0 6px}.aip-result p{white-space:pre-wrap;margin:6px 0}.aip-result ul{padding-left:20px}
.aip-scenario{padding:12px;border:1px solid var(--line);border-radius:9px;margin:10px 0}.aip-levels{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;font-variant-numeric:tabular-nums}.aip-levels small{display:block;color:var(--mute)}
.aip-admin{padding:18px;margin-top:16px;border:1px solid var(--line);border-radius:12px;background:var(--card)}.aip-admin h2{margin-top:0}.aip-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}.aip-grid label{display:grid;gap:5px;font-size:13px}.aip-admin details{margin:14px 0}.aip-admin summary{cursor:pointer}.aip-admin input[type=checkbox]{width:20px;height:20px}
.aip-table{overflow:auto}.aip-table table{width:100%;font-size:12px;border-collapse:collapse}.aip-table td,.aip-table th{padding:8px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
.aip-context{border:1px solid var(--line);border-radius:9px;padding:12px;margin:12px 0}.aip-context-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-top:8px}.aip-context-grid>div{padding:8px;background:var(--bg);border-radius:6px}.aip-context-grid small{display:block;color:var(--mute);font-size:11px}.aip-context-grid b{display:block;font-size:13px}
@media(max-width:640px){.aip-back{padding:6px}.aip-dialog{max-height:96dvh}.aip-body{padding:12px}.aip-grid{grid-template-columns:1fr}}
'''

COMMON = r'''
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');
async function api(path,body,owner){const headers={'X-So-Cong-Khai':'1','Content-Type':'application/json'};if(owner)headers['X-Chart-Owner']=owner;
 const r=await fetch('/api/ai-platform/'+path,{method:body?'POST':'GET',headers,body:body?JSON.stringify(body):undefined,cache:'no-store'});
 const j=await r.json();if(!r.ok||j.ok===false)throw new Error((j.chan||['Máy chủ chưa xử lý được yêu cầu.']).join(' '));return j}
'''

CHART_JS = r'''(()=>{
''' + COMMON + r'''
const back=document.createElement('div');back.className='aip-back';back.hidden=true;
back.innerHTML='<section class="aip-dialog" role="dialog" aria-modal="true" aria-label="AI phân tích biểu đồ"><header class="aip-head"><b>AI · Forex / CFD / Crypto</b><button data-close type="button">Đóng</button></header><div class="aip-body"></div></section>';
document.body.append(back);const box=back.querySelector('.aip-body');let result=null,context=null,busy=false,previousFocus=null,identity=null,ageTimer=0;
const chart=()=>window.BDMN?.(),symbol=g=>g?.tkMa?.()||g?.ma||g?.D?.ma||'',id=()=>crypto.randomUUID().replaceAll('-','');
function stopAge(){clearTimeout(ageTimer);ageTimer=0}
function close(){back.hidden=true;stopAge();previousFocus?.focus()}
back.querySelector('[data-close]').onclick=close;back.addEventListener('click',e=>{if(e.target===back)close()});
back.addEventListener('keydown',e=>{if(e.key==='Escape')close();if(e.key==='Tab'){const a=[...back.querySelectorAll('button,textarea,select,input,a[href]')].filter(x=>!x.disabled&&!x.hidden&&x.offsetParent!==null);if(!a.length)return;const first=a[0],last=a.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}}});
function expired(r){const g=chart();if(r.expired||Date.now()/1000>=r.expires_at||symbol(g)!==r.ma||g?.tf!==r.tf||r._chart_epoch!==g?.D?._chart_epoch||!!window.PHAT_LAI)return true;
 const bid=g?.D?.bid,ask=g?.D?.ask;if(!Number.isFinite(bid)||!Number.isFinite(ask))return true;
 if(r.reference_atr>0&&Math.abs(bid-r.bid)>r.reference_atr*.5)return true;
 return r.analysis.scenarios.some(s=>s.side==='MUA'?(bid<=s.sl||bid>=s.tp[0]):(ask>=s.sl||ask<=s.tp[0]))}
function renderContext(r){const c=r.topdown;if(!c?.rows)return'';const roles={entry:'Khung xác nhận',bridge:'Khung nối',trend:'Xu hướng lớn',macro:'Bối cảnh dài hạn'},states={missing:'Thiếu nến hợp lệ ở khung lớn',macro_conflict:'D1 chưa xác nhận cùng phía EMA200',higher_conflict:'Các khung lớn đang mâu thuẫn',wait_entry:'Chờ khung vào xác nhận theo xu hướng lớn',aligned:'Bối cảnh cùng chiều · Vẫn cần điều kiện vào'};
 const locale=document.documentElement.lang==='en'?'en-GB':'vi-VN',stamp=t=>new Intl.DateTimeFormat(locale,{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(t*1000));
 return '<section class="aip-context"><b>Đối chiếu khung lớn</b><p class="aip-muted">'+esc(c.required.join(' → '))+' · UTC+7</p><p class="'+(c.aligned?'':'aip-warn')+'">'+esc(states[c.status]||c.status)+'</p><div class="aip-context-grid">'+c.rows.map(row=>'<div><small>'+esc(roles[row.role]||row.role)+'</small><b>'+esc(row.timeframe)+' · '+(row.direction>0?'▲':row.direction<0?'▼':'—')+'</b><small>'+esc(row.valid&&Number.isFinite(row.closed_at)?stamp(row.closed_at):'Chưa có nến đóng hợp lệ')+'</small></div>').join('')+'</div><small class="aip-muted">Đồng thuận là điều kiện kỹ thuật, không phải xác suất thắng.</small></section>'}
function renderResult(r){const d=r.analysis,locale=document.documentElement.lang==='en'?'en-GB':'vi-VN',digits=Number.isInteger(r.digits)?Math.max(0,Math.min(8,r.digits)):5,number=(v,n=digits)=>new Intl.NumberFormat(locale,{maximumFractionDigits:n}).format(v),price=v=>number(v),list=(title,a)=>a.length?'<h3>'+title+'</h3><ul>'+a.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>':'';
 const stamp=new Intl.DateTimeFormat(locale,{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).format(new Date(r.snapshot_at*1000))+' · UTC+7';
 return '<div class="aip-result"><p class="aip-muted">'+esc(r.ma+' · '+r.tf+' · '+r.provider+' / '+r.model)+' · '+esc(stamp)+' · '+(r.vision_used?'Có đọc ảnh':'Dữ liệu số')+'</p>'
 +(r.engine==='rules'?'<p class="aip-muted">Miễn phí · Quy tắc cố định, chưa phải mô hình đã huấn luyện · Không gửi dữ liệu tới nhà cung cấp AI.</p>':'<p class="aip-muted">Mô hình nền của nhà cung cấp · Không phải mô hình được fine-tune riêng trên hệ thống này.</p>')
 +renderContext(r)
 +(r.checks?.length?'<div class="aip-grid">'+r.checks.map(c=>'<div><b>'+esc(c.label)+'</b><br><span class="'+(c.passed?'':'aip-warn')+'">'+(c.passed?'Đạt điều kiện':'Chưa đạt')+'</span></div>').join('')+'</div>':'')
 +'<p class="aip-warn" data-age></p><h3>Bức tranh chung</h3><p>'+esc(d.summary)+'</p><p>'+esc(d.trend)+'</p>'+list('Đồng thuận',d.agreement)+list('Mâu thuẫn',d.conflicts)
 +d.scenarios.map((s,i)=>'<article class="aip-scenario"><b>'+esc(s.side==='MUA'?'Kịch bản MUA có điều kiện':'Kịch bản BÁN có điều kiện')+'</b><div class="aip-levels">'+[['Entry',s.entry],['SL',s.sl],...s.tp.map((p,j)=>['TP'+(j+1)+' · '+s.rr[j]+'R',p])].map(([k,v])=>'<div><small>'+esc(k)+'</small><b>'+esc(price(v))+'</b></div>').join('')+'</div><p>'+esc(s.reason)+'</p><p><b>Điều kiện máy chủ: </b>'+esc(s.condition)+'</p><p><b>Xác nhận AI: </b>'+esc(s.trigger)+'</p><p><b>Vô hiệu: </b>'+esc(s.invalidation)+'</p><p class="aip-muted">'+esc(s.execution_note)+'</p><button type="button" data-draw="'+i+'">Vẽ mức tham chiếu lên biểu đồ</button></article>').join('')
 +(!d.scenarios.length&&r.engine!=='rules'?'<p class="aip-warn">ĐỨNG NGOÀI · Chưa có kịch bản đủ điều kiện.</p>':'')+list('Cần theo dõi',d.watch)+(d.answer?'<h3>Trả lời câu hỏi</h3><p>'+esc(d.answer)+'</p>':'')
 +(r.evidence?.length?'<details><summary>Chỉ báo dùng làm căn cứ</summary><div class="aip-table"><table><thead><tr>'+['Khung','Giá đóng','EMA20','EMA50','EMA200','RSI14','ATR14 · SMA'].map(x=>'<th>'+x+'</th>').join('')+'</tr></thead><tbody>'+r.evidence.map(f=>'<tr><th>'+esc(f.timeframe)+'</th>'+['close','ema20','ema50','ema200','rsi14','atr14_sma'].map(k=>'<td>'+(f[k]==null?'—':esc(number(f[k],k==='rsi14'?2:digits)))+'</td>').join('')+'</tr>').join('')+'</tbody></table></div><p class="aip-muted">MT5 · Nến đã đóng · '+esc(r.snapshot_sha.slice(0,12))+'</p></details>':'')
 +'<p class="aip-muted">'+esc(r.mien_tru)+' Mức giá tham chiếu do máy chủ tính từ OHLC/ATR. Chưa xác minh tin kinh tế trong lượt này.</p></div>'}
function tick(){stopAge();if(!result||back.hidden)return;const el=box.querySelector('[data-age]');if(!el)return;const old=expired(result);el.textContent=old?'Ảnh chụp đã hết hiệu lực hoặc biểu đồ đã đổi. Hỏi lại để cập nhật; không dùng các mức này như tín hiệu hiện tại.':'Ảnh chụp tại thời điểm hỏi · còn '+Math.max(0,Math.ceil(result.expires_at-Date.now()/1000))+' giây. Không tự gọi API liên tục.';
 for(const b of box.querySelectorAll('[data-draw]'))b.disabled=old;ageTimer=setTimeout(tick,1000)}
async function show(mode='indicators'){
 if(busy){back.hidden=false;return}stopAge();previousFocus=document.activeElement;back.hidden=false;box.innerHTML='<p>Đang kiểm tra dữ liệu và hạn mức…</p>';result=null;
 try{const st=await api('status'),u=await(await fetch('/api/tai-khoan-chart',{cache:'no-store'})).json(),g=chart();identity=u.nguoi?.id||null;
  const a=st.account;context={ma:symbol(g),tf:g?.tf,mode,epoch:g?.D?._chart_epoch};
  box.innerHTML='<p class="aip-muted">'+esc(context.ma+' · '+context.tf)+'<br>'+esc(a?(a.plan==='owner'?'Chủ tài khoản':a.plan+' · còn '+a.remaining+'/'+a.limit+' lượt AI API'):'Cần đăng nhập tại nút Tài khoản chart trên biểu đồ')+'</p>'
   +'<label>Cách phân tích <select data-engine><option value="rules">Miễn phí · Bộ quy tắc đa khung</option><option value="llm">AI API · Đọc chỉ báo, ảnh và câu hỏi</option></select></label>'
   +'<p data-local-note class="aip-muted">Đọc EMA20/50/200, RSI14 và ATR14 từ nến đã đóng trên MT5. Không cần API key, không trừ lượt AI. Chỉ hiện kịch bản khi đủ điều kiện; chưa có bằng chứng lợi nhuận.</p>'
   +(!st.owner?'<p class="aip-warn">Dữ liệu MT5 trên máy thuộc tài khoản chủ. Dùng bản cài riêng để phân tích dữ liệu của bạn.</p>':'')
   +'<div data-cloud hidden><p class="aip-muted">'+esc(st.provider+' / '+st.model)+'</p><label>Chế độ <select data-mode><option value="indicators">AI đọc chỉ báo</option><option value="explain">AI giải thích</option><option value="entry">Entry / SL / TP</option></select></label>'
   +'<label>Câu hỏi về biểu đồ<textarea rows="3" maxlength="1500" data-question placeholder="Ví dụ: Các khung có đồng thuận không? Điều kiện nào làm kịch bản mất hiệu lực?"></textarea></label>'
   +'<label><input type="checkbox" data-vision '+(!st.vision?'disabled':'')+'> Kèm ảnh biểu đồ đang xem '+(!st.vision?'(model chưa bật đọc ảnh)':'')+'</label>'
   +'<p class="aip-muted">Gửi nến và chỉ báo đa khung từ MT5, các chỉ báo đang bật và câu hỏi tới nhà cung cấp AI đã chọn. Ảnh chỉ gửi khi bạn bật tùy chọn. Một lần bấm dùng một lượt; lỗi phân tích được hoàn lượt.</p>'
   +st.chan.map(x=>'<p class="aip-warn">'+esc(x)+'</p>').join('')+'</div><div class="aip-row"><button type="button" class="primary" data-ask '+(!identity?'disabled':'')+'>Phân tích miễn phí</button>'+(st.owner?'<a href="/cai-dat#ai-admin">Cấu hình AI</a>':'')+'</div>'
   +'<div role="status" aria-live="polite" data-message></div><div data-result></div><details><summary>Gói sử dụng</summary>'+Object.values(st.plans).map(p=>'<p>'+esc(p.label)+' · '+p.questions+' lượt/tháng · '+new Intl.NumberFormat('vi-VN').format(p.price_vnd)+' đ</p>').join('')+'<p class="aip-muted">Liên hệ chủ tài khoản để đăng ký và kích hoạt gói. Thanh toán tự động chưa được kết nối.</p></details>';
  box.querySelector('[data-mode]').value=mode;
  const engine=box.querySelector('[data-engine]'),syncEngine=()=>{const free=engine.value==='rules';box.querySelector('[data-cloud]').hidden=free;box.querySelector('[data-local-note]').hidden=!free;
   box.querySelector('[data-question]').disabled=free;const vision=box.querySelector('[data-vision]');vision.disabled=free||!st.vision;if(free)vision.checked=false;
   const b=box.querySelector('[data-ask]');b.disabled=busy||!identity||!st.owner||(!free&&st.chan.length>0);b.textContent=free?'Phân tích miễn phí':'Phân tích bằng AI API'};
  engine.onchange=syncEngine;syncEngine();box.querySelector('[data-ask]').onclick=ask;engine.focus();
 }catch(e){box.innerHTML='<p class="aip-warn">'+esc(e.message)+'</p>'}}
async function ask(){if(busy)return;const g=chart(),message=box.querySelector('[data-message]'),button=box.querySelector('[data-ask]');
 if(!g?.D||symbol(g)!==context.ma||g?.tf!==context.tf||g.D._chart_epoch!==context.epoch||window.PHAT_LAI){message.textContent='Biểu đồ đã đổi hoặc đang phát lại. Đóng rồi mở lại bảng AI.';return}
 busy=true;button.disabled=true;box.querySelector('[data-engine]').disabled=true;result=null;box.querySelector('[data-result]').textContent='';message.textContent='Đang lấy giá mới và phân tích…';
 try{const free=box.querySelector('[data-engine]').value==='rules',body={...(free?{}:window.CBCN?.tomTat?.()||{}),...context,lang:document.documentElement.lang==='en'?'en':'vi',mode:box.querySelector('[data-mode]').value,request_id:id(),replay:!!window.PHAT_LAI};
  if(!free)body.question=box.querySelector('[data-question]').value;
  if(!free&&box.querySelector('[data-vision]').checked){const source=g.LW?.chart.takeScreenshot();if(!source)throw new Error('Chưa chụp được biểu đồ.');const canvas=document.createElement('canvas'),scale=Math.min(1,1600/source.width,1000/source.height);canvas.width=Math.round(source.width*scale);canvas.height=Math.round(source.height*scale);const x=canvas.getContext('2d');x.drawImage(source,0,0,canvas.width,canvas.height);
   const overlay=document.querySelector('#lwo');if(overlay?.width)x.drawImage(overlay,0,0,canvas.width,canvas.height);body.image=canvas.toDataURL('image/png')}
  const r=await api(free?'local':'analyze',body,identity),u=await(await fetch('/api/tai-khoan-chart',{cache:'no-store'})).json();
  if(u.nguoi?.id!==identity)throw new Error('Tài khoản đã thay đổi; kết quả đã được ẩn.');
  const current=chart();if(symbol(current)!==context.ma||current?.tf!==context.tf||current?.D?._chart_epoch!==context.epoch||window.PHAT_LAI)throw new Error('Biểu đồ đã đổi trong lúc phân tích; kết quả cũ được ẩn.');
  r._chart_epoch=context.epoch;result=r;box.querySelector('[data-result]').innerHTML=renderResult(r);message.textContent='Đã phân tích. '+(free?'Miễn phí, không trừ lượt AI.':r.account?.plan==='owner'?'':('Còn '+(r.account?.remaining??'—')+' lượt.'));
  box.querySelectorAll('[data-draw]').forEach(b=>b.onclick=()=>{if(expired(r))return;window.dispatchEvent(new CustomEvent('ai-chart-plan',{detail:{...r,selected:r.analysis.scenarios[+b.dataset.draw]}}));close()});tick();
 }catch(e){message.textContent=e.message;message.className='aip-warn'}finally{busy=false;const engine=box.querySelector('[data-engine]');engine.disabled=false;engine.onchange?.()}}
window.AI_CHART={open:show,context:renderContext};
document.addEventListener('visibilitychange',()=>{if(document.hidden){stopAge();result=null;const r=box.querySelector('[data-result]');if(r)r.textContent='Kết quả được ẩn khi rời trang. Mở lại bảng AI để lấy dữ liệu mới.'}});
})();'''

ADMIN_HTML = '<section class="aip-admin" id="ai-admin"><h2>AI · Nhà cung cấp và gói sử dụng</h2><div id="ai-owner-console"><p class="aip-muted">Đang kiểm tra quyền chủ tài khoản…</p></div></section>'

ADMIN_JS = r'''(()=>{
''' + COMMON + r'''
const host=document.getElementById('ai-owner-console');if(!host)return;let state=null;
const field=(key,label,type='number',step='1')=>'<label>'+label+'<input data-ai="'+key+'" type="'+type+'" step="'+step+'" value="'+esc(state.settings[key])+'"></label>';
async function load(){try{state=await api('admin');render()}catch(e){host.innerHTML='<p class="aip-muted">'+esc(e.message)+'</p><p>Đăng nhập bằng tài khoản chủ tại <a href="/bieu-do">Biểu đồ → Tài khoản chart</a>. Khách hàng chỉ xem gói và số lượt của mình.</p>'}}
function render(){const s=state.settings;host.innerHTML='<p class="aip-muted">Chỉ chủ tài khoản được thay đổi. Khóa API lưu mã hóa trên máy chủ, không trả về trình duyệt. Claude Code là công cụ lập trình; dịch vụ này dùng Claude API.</p><div class="aip-grid">'
 +'<label>Bật dịch vụ AI<input type="checkbox" data-ai="enabled" '+(s.enabled?'checked':'')+'></label><label>Nhà cung cấp<select data-ai="provider">'+Object.entries(state.providers).map(([k,p])=>'<option value="'+k+'" '+(s.provider===k?'selected':'')+'>'+esc(p.ten)+'</option>').join('')+'</select></label>'
 +'<label>Model sử dụng<select data-ai="model">'+s.approved_models.map(m=>'<option '+(s.model===m?'selected':'')+'>'+esc(m)+'</option>').join('')+'</select></label>'
 +'<label>Suy luận<select data-ai="effort">'+['high','medium','low'].map(m=>'<option '+(s.effort===m?'selected':'')+'>'+m+'</option>').join('')+'</select></label>'
 +'<label>Cho phép đọc ảnh<input type="checkbox" data-ai="vision" '+(s.vision?'checked':'')+'></label>'
 +field('free_questions','Lượt miễn phí trọn đời mỗi tài khoản mới')+field('daily_questions','Tối đa lượt/ngày mỗi tài khoản')+field('daily_budget_usd','Ngân sách tổng/ngày (USD)','number','0.1')+field('monthly_budget_usd','Ngân sách tổng/tháng UTC (USD)','number','0.1')
 +field('quote_max_age','Tuổi tick và hiệu lực ảnh chụp tối đa (giây)')+field('timeout','Thời gian chờ API (giây)')+field('max_tokens','Giới hạn token đầu ra, gồm suy luận')+field('min_rr','R:R tối thiểu của kịch bản','number','0.1')+'</div>'
 +'<details><summary>Model được duyệt, lời nhắc và dự toán chi phí</summary><p class="aip-muted">Các model gợi ý cần quyền API tương ứng. Thêm model mới sau khi tự đánh giá trên dữ liệu kiểm định. Không tự chuyển model khi lỗi. Đơn giá dưới đây dùng để giữ ngân sách và ước tính, không phải hóa đơn; nên đặt cao hơn đơn giá thực gồm cache và suy luận.</p>'
 +'<label>Model được duyệt (mỗi dòng một ID)<textarea data-models rows="4">'+esc(s.approved_models.join('\n'))+'</textarea></label><div class="aip-grid">'+field('input_usd_million','Dự toán USD / triệu token đầu vào','number','0.01')+field('output_usd_million','Dự toán USD / triệu token đầu ra','number','0.01')+'</div>'
 +'<label>Phong cách giải thích bổ sung<textarea data-note rows="3" maxlength="3000">'+esc(s.prompt_note)+'</textarea></label><p class="aip-muted">Lời nhắc nền vẫn yêu cầu dữ liệu thật, chỉ forex/CFD/crypto và kiểm giá bằng máy chủ.</p></details>'
 +'<details><summary>Gói và giá niêm yết</summary><p class="aip-muted">JSON: mã gói → label, questions (lượt/tháng UTC), price_vnd. Giá niêm yết chưa tạo giao dịch thanh toán.</p><textarea data-plans rows="8">'+esc(JSON.stringify(s.plans,null,2))+'</textarea></details>'
 +'<div class="aip-row"><button type="button" class="primary" data-save>Lưu cấu hình AI</button></div><hr>'
 +'<h3>Khóa API · '+esc(state.providers[s.provider].ten)+'</h3><p class="aip-muted" data-key-status>'+(state.keys[s.provider]?'Đã có khóa (không hiển thị giá trị).':'Chưa có khóa.')+' Có thể dùng biến môi trường '+esc(state.providers[s.provider].env)+'.</p><div class="aip-row"><input type="password" autocomplete="new-password" data-key placeholder="Dán khóa API mới" maxlength="4096" aria-label="Khóa API"><button type="button" data-save-key>Lưu khóa mã hóa</button><button type="button" data-clear-key>Xóa khóa đã lưu</button></div>'
 +'<p><button type="button" data-check>Kiểm tra kết nối / model (không sinh câu trả lời)</button></p>'
 +'<h3>Kích hoạt gói cho khách hàng</h3><p class="aip-muted">Chỉ cấp gói sau khi kiểm tra thanh toán bên ngoài. Gia hạn không đặt lại số lượt đã dùng trong tháng. Gói miễn phí tính tổng lượt trọn đời.</p><div class="aip-row"><select data-user aria-label="Khách hàng">'+state.users.filter(u=>!u.chu).map(u=>'<option value="'+u.id+'">'+esc(u.ten)+'</option>').join('')+'</select><select data-plan aria-label="Gói"><option value="free">Miễn phí / thu hồi gói</option>'+Object.entries(s.plans).map(([k,p])=>'<option value="'+k+'">'+esc(p.label)+'</option>').join('')+'</select><input type="date" data-expiry aria-label="Ngày hết hạn"><button type="button" data-grant>Cấp / thu hồi gói</button></div>'
 +'<details><summary>Sử dụng và gói đang cấp</summary><div class="aip-table"><table><thead><tr><th>Tài khoản</th><th>Lượt thành công</th><th>Dự toán / giữ ngân sách USD</th><th>Gói</th><th>Hết hạn</th></tr></thead><tbody>'+state.users.map(u=>{const use=state.usage.find(x=>x.uid===u.id),g=state.grants.find(x=>x.uid===u.id);return '<tr><td>'+esc(u.ten)+'</td><td>'+(use?.used||0)+'</td><td>'+(use?.reserved_usd||0)+'</td><td>'+esc(g?.plan||'free')+'</td><td>'+esc(g?new Date(g.expires*1000).toLocaleDateString():'—')+'</td></tr>'}).join('')+'</tbody></table></div></details><p role="status" aria-live="polite" data-admin-message></p>';
 host.querySelector('[data-ai="provider"]').onchange=e=>{const spec=state.providers[e.target.value],models=spec.models;host.querySelector('[data-models]').value=models.join('\n');host.querySelector('[data-ai="model"]').innerHTML=models.map(m=>'<option>'+esc(m)+'</option>').join('');host.querySelector('[data-key-status]').textContent='Lưu cấu hình trước khi nhập khóa cho nhà cung cấp mới.'};
 host.querySelector('[data-models]').oninput=e=>{const select=host.querySelector('[data-ai="model"]'),current=select.value;select.innerHTML=e.target.value.split(/\s+/).filter(Boolean).map(m=>'<option '+(m===current?'selected':'')+'>'+esc(m)+'</option>').join('')};
 host.querySelector('[data-save]').onclick=()=>run(async()=>{const value={...s};host.querySelectorAll('[data-ai]').forEach(e=>value[e.dataset.ai]=e.type==='checkbox'?e.checked:e.type==='number'?Number(e.value):e.value);value.approved_models=host.querySelector('[data-models]').value.split(/\s+/).filter(Boolean);value.prompt_note=host.querySelector('[data-note]').value;value.plans=JSON.parse(host.querySelector('[data-plans]').value);await api('settings',{settings:value});await load()});
 host.querySelector('[data-save-key]').onclick=()=>run(async()=>{if(host.querySelector('[data-ai="provider"]').value!==s.provider)throw new Error('Lưu nhà cung cấp trước khi nhập khóa.');const input=host.querySelector('[data-key]');if(!input.value)throw new Error('Chưa nhập khóa.');try{await api('key',{provider:s.provider,key:input.value})}finally{input.value=''}await load()});
 host.querySelector('[data-clear-key]').onclick=()=>run(async()=>{await api('key',{provider:s.provider,key:''});await load()});
 host.querySelector('[data-check]').onclick=()=>run(async()=>{const r=await api('check',{});host.querySelector('[data-admin-message]').dataset.detail=r.message+' Model API: '+r.models.join(', ')});
 host.querySelector('[data-grant]').onclick=()=>run(async()=>{const plan=host.querySelector('[data-plan]').value,v=host.querySelector('[data-expiry]').value;if(plan!=='free'&&!v)throw new Error('Chọn ngày hết hạn.');await api('grant',{uid:host.querySelector('[data-user]').value,plan,expires:v?Date.parse(v+'T23:59:59+07:00')/1000:0});await load()})}
async function run(fn){const buttons=[...host.querySelectorAll('button')],message=host.querySelector('[data-admin-message]');delete message.dataset.detail;buttons.forEach(x=>x.disabled=true);try{await fn();const m=host.querySelector('[data-admin-message]');m.textContent=m.dataset.detail||'Đã lưu.'}catch(e){host.querySelector('[data-admin-message]').textContent=e.message}finally{buttons.forEach(x=>x.disabled=false)}}
load();})();'''
