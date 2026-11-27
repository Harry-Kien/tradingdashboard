"""Trang Nhật ký: xem toàn bộ các điểm vào đã ghi, lọc theo mã, phương pháp và trạng thái. Số liệu lấy từ /api/nhat-ky, tự tải lại 30 giây một lần."""
from __future__ import annotations

from html import escape

from . import phieu_js, trang

CSS = """
.nkt{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;margin:18px 0 10px}
.nkt .seg{display:inline-flex;border:1px solid var(--line);border-radius:6px;overflow:hidden;background:var(--card)}
.nkt .seg button{min-height:32px;padding:0 12px;border:0;border-right:1px solid var(--line);background:none;color:var(--ink2);font:600 12.5px/1 Tahoma,"Segoe UI",Arial,sans-serif;cursor:pointer;transition:background-color .12s,color .12s}
.nkt .seg button:last-child{border-right:0}.nkt .seg button:hover:not([aria-pressed=true]){background:var(--bg);color:var(--ink)}
.nkt .seg button[aria-pressed=true]{background:var(--series);color:var(--btn-ink)}.nkt .seg button:focus-visible,.nkt select:focus-visible{outline:2px solid var(--series);outline-offset:1px}
.nkt select{min-height:32px;padding:0 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink);font:600 12.5px/1 Tahoma,"Segoe UI",Arial,sans-serif;max-width:320px}
.nkt .dem{margin-left:auto;color:var(--mute);font-size:13px}
.cham{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--line);vertical-align:1px}
.cham.song{background:var(--gain);animation:nhip 1.8s ease-out infinite}.cham.ok{background:var(--gain)}.cham.xau{background:var(--loss)}
@keyframes nhip{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--gain) 55%,transparent)}100%{box-shadow:0 0 0 7px transparent}}
@media(prefers-reduced-motion:reduce){.cham.song{animation:none}}
.huong{font-weight:700}.huong.up{color:var(--gain)}.huong.dn{color:var(--loss)}
td.tt{font-weight:700}td.pp{white-space:normal;min-width:190px;max-width:320px}
td a.xem{color:var(--series);font-weight:600;text-decoration:none;border:1px solid var(--series);border-radius:6px;padding:3px 9px;font-size:12.5px}
td a.xem:hover{background:color-mix(in srgb,var(--series) 9%,transparent)}
h2.nk{margin:26px 0 4px;font-size:16px}
main{max-width:1560px!important}.bar>div{max-width:1400px!important}td.pp{min-width:170px;max-width:260px}
details.gt{margin:18px 0 0;font-size:13.5px;color:var(--ink2)}details.gt summary{cursor:pointer;color:var(--series);font-weight:600;text-transform:none;letter-spacing:0;font-size:13.5px}
details.gt p{margin:8px 0 0;max-width:78ch}
"""

JS = r"""
(()=>{const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])),
 so=(v,d)=>v==null?'—':Number(v).toLocaleString('vi-VN',{minimumFractionDigits:d,maximumFractionDigits:d}),
 gio=t=>new Date(t).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}),
 rr=v=>v==null?'':(v>0?'+':v<0?'−':'')+so(Math.abs(v),2)+'R',mau=v=>v>0?'gain':v<0?'loss':'',
 TT={cho_khop:['Chờ khớp','song'],dang_mo:['Đang mở','song'],thang:['Thắng','ok'],thua:['Thua','xau'],het_gio:['Hết giờ',''],khong_khop:['Không khớp',''],huy:['Hủy trước khi khớp',''],thay:['Tín hiệu mới thay','']},
 NHOM={song:x=>x.tt==='cho_khop'||x.tt==='dang_mo',thang:x=>x.tt==='thang',thua:x=>x.tt==='thua',khac:x=>['het_gio','khong_khop','huy','thay'].includes(x.tt)};
let NK=null,loc={sym:'',tt:'',ma:''};try{Object.assign(loc,JSON.parse(sessionStorage.getItem('so-nk-loc')||'{}'))}catch(e){}
function ve(){const el=$('#nk-trang');if(!NK){el.innerHTML='<p class="small">Đang đọc nhật ký…</p>';return}
 if(!NK.bat){el.innerHTML='<p class="note">Nhật ký đang tắt trong cấu hình (mục nhat_ky.bat).</p>';return}
 const tat=NK.ds||[],syms=[...new Set(tat.map(x=>x.sym))].sort(),pps=[...new Map(tat.map(x=>[x.ma,x.ten])).entries()];
 if(loc.sym&&!syms.includes(loc.sym))loc.sym='';if(loc.ma&&!pps.some(p=>p[0]===loc.ma))loc.ma='';
 const coSo=tat.filter(x=>!x.trung_voi&&(!loc.sym||x.sym===loc.sym)&&(!loc.ma||x.ma===loc.ma)),ds=coSo.filter(x=>!loc.tt||NHOM[loc.tt](x)),
  trung=tat.filter(x=>x.trung_voi&&(!loc.sym||x.sym===loc.sym)&&(!loc.ma||x.ma===loc.ma)).length,dem=k=>coSo.filter(NHOM[k]).length,tongR=coSo.reduce((a,x)=>a+(x.r||0),0),xong=dem('thang')+dem('thua');
 let h='<div class="tiles">'+[['Điểm vào đã ghi',coSo.length,(loc.sym||'mọi mã')+(trung?' · không tính '+trung+' dòng ghi trùng':'')],['Còn sống',`<span class="cham ${dem('song')?'song':''}"></span> ${dem('song')}`,'đang chờ khớp hoặc đang mở'],
   ['Thắng · Thua',`<span class="gain">${dem('thang')}</span> · <span class="loss">${dem('thua')}</span>`,xong?'thắng '+so(dem('thang')/xong*100,1)+'% số lệnh đã xong':'chưa có lệnh nào xong'],
   ['Tổng R',`<span class="${mau(tongR)}">${rr(tongR)||'0,00R'}</span>`,'cộng mọi lệnh đã có kết quả']].map(([k,v,s])=>`<div class="tile"><span>${k}</span><b>${v}</b><small>${esc(s)}</small></div>`).join('')+'</div>';
 const ch=NK.chuoi||{};if(ch.ok!==undefined)h+=`<p class="small" title="Mỗi điểm vào mang dấu SHA-256 nối với dòng trước: sửa, xóa hay chèn một tín hiệu cũ đều làm gãy chuỗi. Kết quả về sau không nằm trong dấu vì được chấm lại từ giá.">`
  +(ch.ok?`Chuỗi dấu nguyên vẹn: ${ch.so_dong} điểm vào${ch.chua_dau?' (thêm '+ch.chua_dau+' dòng ghi trước khi có chuỗi)':''}${ch.bam_cuoi?' · dấu mới nhất <code>'+esc(ch.bam_cuoi.slice(0,16))+'…</code>':''}`
   :`<b class="loss">Chuỗi dấu gãy ở dòng ${esc(String(ch.hong_id||ch.loi||''))}: một điểm vào đã ghi bị sửa, xóa hoặc chèn.</b>`)+'</p>';
 const nut=(nhom,gt,ten)=>`<button type="button" data-n="${nhom}" data-v="${esc(gt)}" aria-pressed="${loc[nhom]===gt}">${esc(ten)}</button>`;
 h+='<div class="nkt"><div class="seg" role="group" aria-label="Mã">'+nut('sym','','Mọi mã')+syms.map(s=>nut('sym',s,s)).join('')+'</div>'
  +'<div class="seg" role="group" aria-label="Trạng thái">'+[['','Tất cả'],['song','Còn sống'],['thang','Thắng'],['thua','Thua'],['khac','Khác']].map(([v,t])=>nut('tt',v,t)).join('')+'</div>'
  +`<select id="nk-pp" aria-label="Phương pháp"><option value="">Mọi phương pháp</option>${pps.map(([m,t])=>`<option value="${esc(m)}"${loc.ma===m?' selected':''}>${esc(t)}</option>`).join('')}</select>`
  +`<span class="dem">${ds.length} dòng</span></div>`;
 h+=ds.length?'<div class="wrap"><table><thead><tr><th></th><th>Lúc ghi</th><th>Mã</th><th>Phương pháp</th><th>Chiều</th><th class="r">Vào</th><th class="r">Dừng lỗ</th><th class="r">Chốt lời</th><th>Trạng thái</th><th class="r">Kết quả</th><th class="r" title="Điểm mô hình (thử nghiệm), 0–100">Mô hình</th><th></th></tr></thead><tbody>'
   +ds.map(x=>{const[tt,lop]=TT[x.tt]||[x.tt,''],d=x.so_le==null?2:x.so_le,mua=x.huong==='MUA',duong='/bieu-do?'+(x.sym===NK.ma_vang?'':'ma='+encodeURIComponent(x.sym)+'&')+'nk='+x.id;
    return `<tr><td><span class="cham ${lop}" title="${tt}"></span></td><td>${gio(x.luc)}</td><td>${esc(x.sym)}</td><td class="pp">${esc(x.ten)}</td><td class="huong ${mua?'up':'dn'}">${mua?'▲ MUA':'▼ BÁN'}</td>`
     +`<td class="r">${so(x.vao,d)}</td><td class="r">${so(x.sl,d)}</td><td class="r">${so(x.tp[x.tp.length-1],d)}</td><td class="tt ${lop==='ok'?'gain':lop==='xau'?'loss':''}">${tt}${x.cham_tp1&&x.tt!=='thang'?' · đã chạm TP1':''}</td>`
     +`<td class="r ${mau(x.r)}">${rr(x.r)}</td><td class="r">${x.mo_hinh!=null?x.mo_hinh:''}</td><td><a class="xem" href="${duong}">Xem trên biểu đồ</a></td></tr>`}).join('')+'</tbody></table></div>'
  :'<p class="small">Không có dòng nào khớp bộ lọc. Điểm vào được ghi khi một luật hoặc một phương pháp có điểm vào còn hiệu lực.</p>';
 const tom=(NK.tom||[]).filter(t=>(!loc.sym||t.sym===loc.sym)&&(!loc.ma||t.ma===loc.ma));
 if(tom.length)h+='<h2 class="nk">Theo phương pháp</h2><div class="wrap"><table><thead><tr><th>Phương pháp</th><th>Mã</th><th class="r">Điểm vào</th><th class="r">Thắng</th><th class="r">Thua</th><th class="r">Không tính</th><th class="r">Còn sống</th><th class="r">Tổng R</th></tr></thead><tbody>'
   +tom.sort((a,b)=>b.tong_r-a.tong_r).map(t=>`<tr><td class="pp">${esc(t.ten)}</td><td>${esc(t.sym)}</td><td class="r">${t.n}</td><td class="r gain">${t.thang}</td><td class="r loss">${t.thua}</td><td class="r">${t.khac}</td><td class="r">${t.song}</td><td class="r ${mau(t.tong_r)}">${rr(t.tong_r)||'0,00R'}</td></tr>`).join('')+'</tbody></table></div>';
 const mh=NK.theo_mo_hinh||{};if(mh.cao||mh.thap)h+='<h2 class="nk">Theo điểm mô hình (thử nghiệm, chỉ vàng; chỉ tính điểm vào do bản mô hình hiện tại chấm)</h2><div class="wrap"><table><thead><tr><th>Nhóm</th><th class="r">Điểm vào</th><th class="r">Thắng</th><th class="r">Thua</th><th class="r">Không tính</th><th class="r">Còn sống</th><th class="r">Tổng R</th></tr></thead><tbody>'
   +[['cao','Điểm từ 90'],['thap','Điểm dưới 90']].filter(([k])=>mh[k]).map(([k,t])=>`<tr><td>${t}</td><td class="r">${mh[k].n}</td><td class="r gain">${mh[k].thang}</td><td class="r loss">${mh[k].thua}</td><td class="r">${mh[k].khac}</td><td class="r">${mh[k].song}</td><td class="r ${mau(mh[k].tong_r)}">${rr(mh[k].tong_r)||'0,00R'}</td></tr>`).join('')+'</tbody></table></div>';
 for(const e of NK.loi||[])h+=`<p class="note">${esc(e)}</p>`;
 el.innerHTML=h;$('#nk-luc').textContent='cập nhật lúc '+gio(NK.luc);
 const luu=()=>{try{sessionStorage.setItem('so-nk-loc',JSON.stringify(loc))}catch(e){}ve()};
 el.querySelectorAll('.seg button').forEach(b=>b.addEventListener('click',()=>{loc[b.dataset.n]=b.dataset.v;luu()}));
 $('#nk-pp').addEventListener('change',e=>{loc.ma=e.target.value;luu()})}
async function tai(){try{const r=await fetch('/api/nhat-ky',{cache:'no-store'});if(!r.ok)throw new Error(await r.text());NK=await r.json()}catch(e){NK=NK||{bat:true,ds:[],tom:[],loi:[]};NK.loi=['Không đọc được nhật ký: '+e.message]}ve()}
ve();tai();setInterval(()=>{if(document.visibilityState==='visible')tai()},30000)})();
"""


def trang_nhat_ky(ten: str) -> str:
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Nhật ký điểm vào · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'nhat-ky', '<button id="theme" type="button">Nền tối</button>') + '<main>',
        '<div class="top"><div><h1>Nhật ký điểm vào</h1></div><div class="stamp">ghi lúc điểm vào xuất hiện, chấm kết quả về sau<br><span id="nk-luc">đang đọc…</span></div></div>',
        '<div id="nk-trang"></div>',
        '<section class="card" id="phieu" style="margin-top:18px"><h2>Phiếu kế hoạch và quyết định của bạn</h2>'
        '<p class="sub">Phiếu lập từ phương án trên Biểu đồ: giữ nguyên mã, phương pháp, nến tín hiệu, giá vào, SL, TP qua Kế hoạch và Kiểm tra lệnh. '
        'Kết quả mô phỏng (chạm TP hay SL) và việc làm đúng kế hoạch là hai cột riêng. Dữ kiện của phiếu không bị sửa; ghi chú là lớp thêm.</p>'
        '<div class="pk-loc" style="display:flex;gap:8px;flex-wrap:wrap;margin:8px 0"><input id="pk-tim" placeholder="Lọc theo mã, phương pháp hoặc tag" '
        'style="min-height:34px;padding:0 10px;flex:1 1 220px"></div><div id="pk-ds"><p class="small">Đang đọc phiếu…</p></div></section>',
        '<details class="gt"><summary>Cách ghi và cách chấm</summary>'
        '<p>Mỗi khi một luật hoặc một phương pháp có điểm vào còn hiệu lực, máy chủ ghi lại ngay lúc đó. Mức giá chốt lúc ghi và không sửa lại. '
        'Mỗi mã, mỗi phương pháp, mỗi chiều chỉ có một dòng còn sống.</p>'
        '<p>Với tám phương pháp tùy chọn, nhật ký theo đúng thứ tự của phép chạy lại: mỗi lúc một lệnh cho mỗi phương pháp. Tín hiệu mới đến lúc lệnh chờ cũ '
        'chưa khớp thì dòng cũ đóng với trạng thái "Tín hiệu mới thay" (trang Biểu đồ lúc đó cũng chỉ còn hiện tín hiệu mới); tín hiệu đến lúc lệnh trước '
        'đã khớp và còn mở thì không ghi. Nhờ vậy số của nhật ký so được với số đo quá khứ.</p>'
        '<p>Kết quả được chấm bằng nến 5 phút: lệnh chờ có khớp trước khi hết hạn không, rồi chạm chốt lời hay dừng lỗ trước; giữ tối đa 24 giờ. Nến mở cửa đã nhảy qua dừng lỗ thì tính thoát ở giá mở, nên có dòng lỗ hơn 1R. '
        'Thắng tính ở 2R với phương pháp tùy chọn và ở TP1 với luật trong sổ. Một nến chạm cả dừng lỗ lẫn chốt lời thì tính dừng lỗ.</p>'
        '<p>Máy chủ ghi cả khi bạn không mở trang; máy chủ tắt thì không ghi. Đây là sổ theo dõi, không phải lệnh thật: nó không tính trượt giá và '
        'không biết bạn có kịp vào lệnh hay không.</p>'
        '<p>Cột Mô hình là điểm thử nghiệm 0–100 của mô hình học máy, chỉ có cho vàng, ghi lúc điểm vào xuất hiện. Nhật ký sẽ cho biết điểm cao có '
        'thật sự đi kèm kết quả tốt hơn không.</p></details>',
        '<footer>' + escape(trang.MIEN_TRU) + f'</footer></main><script>{trang.JS}</script><script>{JS}</script>'
        f'<script>{phieu_js.JS}</script><script>{JS_PHIEU}</script></body></html>'])


JS_PHIEU = r"""
(()=>{const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const so=v=>v==null?'—':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:5}),TT={dung:'Đúng kế hoạch',mot_phan:'Một phần',lech:'Lệch kế hoạch'};
let DS=[];
function ve(){const q=($('#pk-tim').value||'').trim().toLowerCase(),ds=DS.filter(p=>!q||[p.ma,(p.phuong_phap||{}).ten,...(p.ghi_chu_nd||[]).flatMap(g=>g.tag||[])].join(' ').toLowerCase().includes(q));
 if(!ds.length){$('#pk-ds').innerHTML='<p class="small">'+(DS.length?'Không có phiếu khớp bộ lọc.':'Chưa có phiếu nào. Trên trang Biểu đồ, chọn một phương án rồi bấm "Lập kế hoạch lệnh" hoặc "Kiểm tra lệnh trước khi vào".')+'</p>';return}
 $('#pk-ds').innerHTML='<div class="wrap"><table><thead><tr><th>Phiếu</th><th>Lập lúc</th><th>Mã · chiều</th><th class="r">Vào</th><th class="r">SL</th><th class="r">TP</th><th>Phương pháp</th><th>Kỹ thuật lúc lập</th><th>Kiểm rủi ro</th><th>Quyết định</th><th>Kết quả mô phỏng</th><th>Tuân thủ</th><th>Ghi chú</th></tr></thead><tbody>'
  +ds.map(p=>{const pp=p.phuong_phap||{},c=p.cham||{},qd=(p.quyet_dinh||{}).loai,g=(p.ghi_chu_nd||[]),q=new URLSearchParams({ma:p.ma,phieu:p.id});
   return`<tr><td><a href="/kiem-lenh?${q}">${esc(p.id)}</a><br><small>bản ${p.phien_ban}</small>${p.anh?` · <a href="/api/phieu/anh?f=${encodeURIComponent(p.anh)}" target="_blank" rel="noopener">ảnh</a>`:''}</td><td>${PKJ.gio(p.tao_luc)}</td>
    <td><a href="/bieu-do?ma=${encodeURIComponent(p.ma)}">${esc(p.ma)}</a> · ${p.chieu==='MUA'?'MUA':'BÁN'}</td><td class="r">${so(p.vao)}</td><td class="r">${so(p.sl)}</td><td class="r">${(p.tp||[]).map(so).join(' / ')||'—'}</td>
    <td>${esc(pp.ten||pp.ma||'')}${pp.phien_ban_quy_tac?'<br><small>'+esc(pp.phien_ban_quy_tac)+'</small>':''}</td><td>${(PKJ.KT[p.ky_thuat]||PKJ.KT.khong_ro)[1]}</td><td>${(PKJ.RR[(p.rui_ro||{}).trang_thai]||PKJ.RR.chua_kiem)[1]}</td>
    <td>${qd==='dung_ngoai'?'Đứng ngoài':qd==='vao_mo_phong'?'Theo dõi mô phỏng':'—'}</td><td>${p.theo_doi?esc(PKJ.KQ[c.trang_thai]||c.trang_thai||'—')+(c.r!=null?' · '+(c.r>0?'+':'')+so(c.r)+'R':''):'—'}</td>
    <td>${esc(TT[p.tuan_thu]||'—')}</td><td>${g.length?esc(g[g.length-1].noi_dung).slice(0,80)+(g.length>1?' <small>(+'+(g.length-1)+')</small>':''):'—'}</td></tr>`}).join('')+'</tbody></table></div>'
  +'<p class="small">Kết quả mô phỏng chấm trên nến M5 đã đóng sau lúc bấm theo dõi; một nến chạm cả SL và TP tính SL trước; thiếu nến thì ghi "Chưa xác định". Đây không phải lệnh thật.</p>'}
async function tai(){try{const r=await fetch('/api/phieu/ds',{cache:'no-store'});if(!r.ok)throw new Error(await r.text());DS=(await r.json()).ds||[];ve()}
 catch(e){$('#pk-ds').innerHTML='<p class="note">Không đọc được sổ phiếu: '+esc(e.message)+'. Dữ liệu cũ trên máy không bị ảnh hưởng.</p>'}}
$('#pk-tim').addEventListener('input',ve);tai();setInterval(tai,60000);})();
"""
