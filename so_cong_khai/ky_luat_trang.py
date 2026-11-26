"""Trang Kỷ luật giao dịch (/ky-luat): chấm lại các lệnh đã đóng trong MT5 theo quy tắc quản lý rủi ro của bạn và cho biết lệnh phạm quy tắc đã
làm lãi lỗ khác đi bao nhiêu (qua /api/ky-luat, ky_luat.py). Chỉ đọc, chỉ tài khoản demo. Quy tắc dùng chung với trang Kiểm tra trước khi vào
lệnh (lưu trên trình duyệt ở khóa kl-qt)."""
from __future__ import annotations

from html import escape

from . import trang

CSS = r"""
main.rong{max-width:1240px}
.ky-top h1{margin:0}.ky-top p{margin:6px 0 0;color:var(--ink2);max-width:820px}
.ky-loc{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:16px 0 4px}
.ky-seg{display:inline-flex;gap:4px;background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:4px}
.ky-seg button{min-height:34px;padding:0 14px;border:0;border-radius:9px;background:none;color:var(--ink2);font:700 13px/1 inherit;font-family:inherit;cursor:pointer}
.ky-seg button[aria-pressed=true]{background:color-mix(in srgb,var(--series) 18%,transparent);color:var(--ink)}
.ky-loc select{min-height:42px;border-radius:10px;border:1px solid var(--line);background:var(--card2);color:var(--ink);padding:0 12px;font:600 13px/1 inherit;font-family:inherit;max-width:100%}
details.ky-qt{border:1px solid var(--line);border-radius:12px;padding:8px 12px;background:var(--card)}
details.ky-qt summary{cursor:pointer;font-size:13px;font-weight:700;min-height:26px;display:flex;align-items:center}
.ky-qt-f{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(190px,100%),1fr));gap:10px;margin-top:10px}
@media(max-width:640px){details.ky-qt{flex:1 1 100%;min-width:0}}   /* lỗi đã gặp: trên điện thoại ô quy tắc tràn mép phải (210→400px) */
.ky-qt-f label{display:grid;gap:5px;font-size:12.5px;color:var(--ink2);font-weight:600}
.ky-qt-f input{min-height:38px;border-radius:10px;border:1px solid var(--line);background:var(--card2);color:var(--ink);padding:0 10px;font:600 14px/1 inherit;font-family:inherit;width:100%;box-sizing:border-box}
.ky-kq{display:grid;gap:14px;margin-top:14px}
.ky-so{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
@media(max-width:640px){.ky-so{grid-template-columns:repeat(2,minmax(0,1fr))}}
.ky-so div{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px}
.ky-so small{display:block;color:var(--ink2);font-size:12px}.ky-so b{display:block;font-size:22px;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ky-so b em{font-style:normal;font-size:13px;color:var(--ink2);font-weight:600}.ky-so div>span{display:block;color:var(--ink2);font-size:12px;margin-top:2px}
.ky-diem b{font-size:30px}
.ky-y{border-radius:16px;padding:14px 18px;border:1px solid var(--line);background:var(--card);font-size:14.5px;line-height:1.55}
.ky-y.xau{border-color:color-mix(in srgb,var(--loss) 50%,var(--line));background:color-mix(in srgb,var(--loss) 7%,var(--card))}
.ky-y.chu_y{border-color:color-mix(in srgb,var(--warn) 50%,var(--line));background:color-mix(in srgb,var(--warn) 7%,var(--card))}
.ky-y.tot{border-color:color-mix(in srgb,var(--gain) 45%,var(--line));background:color-mix(in srgb,var(--gain) 7%,var(--card))}
.ky-card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;min-width:0}
.ky-card h2{font-size:15px;margin:0 0 10px}
.ky-bang{overflow-x:auto}.ky-bang table{width:100%;border-collapse:collapse;font-size:13px}
.ky-bang th{color:var(--ink2);font-weight:600;text-align:left;font-size:12px;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
.ky-bang td{padding:8px;border-bottom:1px solid var(--line);vertical-align:top}.ky-bang td.so{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.ky-bang tr:last-child td{border-bottom:0}.ky-bang td p{margin:2px 0 0;color:var(--ink2);font-size:12px;line-height:1.45}
.ky-chip{display:inline-flex;align-items:center;gap:4px;border-radius:999px;padding:2px 9px;font-size:11.5px;font-weight:700;margin:2px 4px 2px 0;
 background:color-mix(in srgb,var(--loss) 14%,transparent);color:var(--loss);white-space:nowrap}
.ky-chip.chu_y{background:color-mix(in srgb,var(--warn) 16%,transparent);color:var(--warn)}
.ky-kq em{font-style:normal}.ky-lai{color:var(--gain)}.ky-lo{color:var(--loss)}
.ky-cho{color:var(--ink2);font-size:13.5px;padding:24px;text-align:center;border:1px dashed var(--line);border-radius:14px}
.ky-ghi{font-size:12.5px;color:var(--ink2);margin:0}
"""

JS = r"""
(()=>{const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const LG=document.documentElement.lang==='en'?'en':'vi',LOC=LG==='en'?'en-US':'vi-VN';
const NF={},fmt=(v,d=2)=>v==null||!isFinite(v)?'—':(NF[d]||(NF[d]=new Intl.NumberFormat(LOC,{minimumFractionDigits:d,maximumFractionDigits:d}))).format(v);
const DTF=new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Ho_Chi_Minh'});
const ngayGio=s=>{const p={};DTF.formatToParts(new Date(s)).forEach(x=>p[x.type]=x.value);return`${p.day}/${p.month} ${p.hour}:${p.minute}`};
const QT={q_rui_ro_lenh_toi_da_pct:2,q_lo_ngay_toi_da_pct:3,q_so_lenh_ngay_toi_da:10};
let ST={ngay:30,nguon:''},hen=null,lan=0;
try{Object.assign(QT,JSON.parse(localStorage.getItem('kl-qt')||'{}'))}catch(e){}
try{Object.assign(ST,JSON.parse(localStorage.getItem('kyl')||'{}'))}catch(e){}
for(const k in QT){const el=$('#'+k);if(el)el.value=QT[k]}
const so=el=>{const v=parseFloat(String(el.value).replace(',','.'));return isFinite(v)?v:null};
const tien=(v,t)=>v==null?'—':`<span class="${v>0?'ky-lai':v<0?'ky-lo':''}">${v>0?'+':''}${fmt(v)}</span> <em>${esc(t)}</em>`;
const TEN={khong_sl:'Không có dừng lỗ lúc vào',rui_ro:'Rủi ro vượt mức mỗi lệnh',gap:'Vào gấp sau lệnh thua',tang_lot:'Tăng khối lượng sau lệnh thua',
 qua_lo:'Vào lệnh khi đã chạm giới hạn lỗ ngày',qua_nhieu:'Quá số lệnh mỗi ngày',tin:'Vào sát tin mạnh'};
const GIAI={khong_sl:'Lệnh không có dừng lỗ có thể lỗ không giới hạn.',rui_ro:'Một lệnh lỗ lớn xóa nhiều lệnh thắng.',gap:'Vào lại ngay sau khi thua thường là muốn gỡ, không phải theo kế hoạch.',
 tang_lot:'Tăng cược để gỡ làm lệnh thua tiếp theo nặng hơn hẳn.',qua_lo:'Đã đến mức dừng của ngày mà vẫn vào thêm.',qua_nhieu:'Vào nhiều lệnh trong ngày thường là giao dịch theo cảm xúc.',
 tin:'Quanh tin mạnh giá giật mạnh và spread giãn.'};
const CHIP={khong_sl:'Không dừng lỗ',rui_ro:'Rủi ro cao',gap:'Vào gấp sau thua',tang_lot:'Tăng lot sau thua',qua_lo:'Đã chạm lỗ ngày',qua_nhieu:'Quá số lệnh ngày',tin:'Sát tin'};
function chip(l){let x='';if(l.k==='rui_ro'&&l.pct!=null)x=' '+fmt(l.pct,1)+'%';else if(l.k==='gap'&&l.phut!=null)x=' '+fmt(l.phut,0)+"'";else if(l.k==='tin')x=' '+esc(l.tien||'');
 return`<span class="ky-chip${['qua_nhieu','tin'].includes(l.k)?' chu_y':''}" title="${esc(TEN[l.k]||l.k)}${l.k==='tin'&&l.ten?': '+esc(l.ten):''}">${esc(CHIP[l.k]||l.k)}${x}</span>`}
function boLoc(){document.querySelectorAll('#ky-ngay button').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.v===+ST.ngay)))}
function goi(){clearTimeout(hen);hen=setTimeout(tai,250)}
async function tai(){const q=new URLSearchParams({ngay:ST.ngay});if(ST.nguon)q.set('nguon',ST.nguon);
 for(const k in QT){const el=$('#'+k),v=el?so(el):null;if(v!=null){q.set(k,v);QT[k]=v}}
 try{localStorage.setItem('kl-qt',JSON.stringify(QT));localStorage.setItem('kyl',JSON.stringify(ST))}catch(e){}
 const n=++lan;$('#ky-kq').setAttribute('aria-busy','true');
 try{const r=await fetch('/api/ky-luat?'+q,{cache:'no-store'});const t=await r.text();if(n!==lan)return;if(!r.ok)throw new Error(t);ve(JSON.parse(t))}
 catch(e){if(n===lan)$('#ky-kq').innerHTML=`<p class="ky-cho">Không đọc được lịch sử lệnh: ${esc(e.message)}</p>`}
 finally{if(n===lan)$('#ky-kq').removeAttribute('aria-busy')}}
function nguon(D){const s=$('#ky-nguon'),ds=D.cac_nguon||[];if(ST.nguon&&!ds.includes(ST.nguon)){ST.nguon='';goi()}
 s.innerHTML=`<option value="">Mọi nguồn lệnh</option>`+ds.map(x=>`<option value="${esc(x)}"${x===ST.nguon?' selected':''}>${esc(x)}</option>`).join('')}
function ve(D){if(!D.san_sang){$('#ky-kq').innerHTML=`<p class="ky-cho">Chưa đọc được tài khoản: ${esc(D.ly_do||'')}</p>`;return}
 nguon(D);const t=D.tien||'';
 if(!D.n){$('#ky-kq').innerHTML=`<p class="ky-cho">Chưa có lệnh nào đóng trong khoảng này.</p>`;return}
 const P=D.pham,A=D.dat,T=D.tong;let y,cls;
 if(!P.n){cls='tot';y='Mọi lệnh trong khoảng này đều đúng quy tắc của bạn. Giữ nguyên cách làm này.'}
 else if(P.lai<0){cls='xau';y=`Các lệnh phạm quy tắc đã lấy đi <span class="ky-lo">${fmt(-P.lai)}</span> <em>${esc(t)}</em>. Chỉ tính các lệnh đúng quy tắc, kết quả là ${tien(A.lai,t)} thay vì ${tien(T.lai,t)}.`}
 else{cls='chu_y';y=`Các lệnh phạm quy tắc lần này vẫn có lãi (${tien(P.lai,t)}), nhưng đó là may mắn chứ không phải lợi thế: rủi ro đã cao hơn mức bạn đặt.`}
 const gh=(D.quy_tac_dung||{}).rui_ro_lenh_toi_da_pct||2;
 if(D.rui_ro_tb_pct!=null&&D.rui_ro_tb_pct>gh*2){const r=Math.min(D.rui_ro_tb_pct,99)/100,k=Math.max(1,Math.ceil(Math.log(.5)/Math.log(1-r)));cls='xau';
  y+=k===1?` Mỗi lệnh đang đặt trung bình ${fmt(D.rui_ro_tb_pct,1)}% số dư: chỉ một lệnh thua là mất hơn nửa tài khoản.`
   :` Mỗi lệnh đang đặt trung bình ${fmt(D.rui_ro_tb_pct,1)}% số dư: chỉ cần thua liền ${k} lệnh là mất một nửa tài khoản.`}
 const ll=D.lo_lon_nhat;
 const the=[[`<div class="ky-diem"><small>Điểm kỷ luật</small><b>${fmt(D.diem,0)}%</b><span>${A.n}/${D.n} lệnh đúng mọi quy tắc</span></div>`],
  [`<div><small>Lệnh đúng quy tắc</small><b>${tien(A.lai,t)}</b><span>${A.n} lệnh · thắng ${fmt(A.ty_le_thang,0)}%</span></div>`],
  [`<div><small>Lệnh phạm quy tắc</small><b>${tien(P.lai,t)}</b><span>${P.n} lệnh · thắng ${fmt(P.ty_le_thang,0)}%</span></div>`],
  [`<div><small>Rủi ro trung bình mỗi lệnh</small><b>${D.rui_ro_tb_pct!=null?fmt(D.rui_ro_tb_pct,1)+'%':'—'}</b><span>${D.rui_ro_max_pct!=null?'cao nhất '+fmt(D.rui_ro_max_pct,1)+'% số dư':'Chưa tính được (thiếu dừng lỗ)'}</span></div>`],
  [`<div><small>Chuỗi thua dài nhất</small><b>${D.chuoi_thua_dai_nhat}</b><span>lệnh thua liền nhau</span></div>`],
  [`<div><small>Lệnh lỗ lớn nhất</small><b>${ll?tien(ll.lai,t):'—'}</b><span>${ll&&ll.pct!=null?fmt(ll.pct,1)+'% số dư lúc vào':'Không có lệnh lỗ'}</span></div>`]];
 const qt=D.quy_tac.filter(r=>r.n).sort((a,b)=>a.lai-b.lai);
 const bang=qt.length?`<div class="ky-bang"><table><thead><tr><th>Quy tắc</th><th>Lệnh phạm</th><th>Thắng / thua</th><th>Lãi lỗ</th></tr></thead><tbody>${qt.map(r=>
  `<tr><td><b>${esc(TEN[r.k]||r.k)}</b><p>${esc(GIAI[r.k]||'')}</p></td><td class="so">${r.n}</td><td class="so">${r.thang} / ${r.thua}</td><td class="so">${tien(r.lai,t)}</td></tr>`).join('')}</tbody></table></div>`
  :'<p class="ky-ghi">Không quy tắc nào bị phạm.</p>';
 const ds=D.lenh.filter(x=>x.loi.length).slice(0,60);
 const lenh=ds.length?`<div class="ky-bang"><table><thead><tr><th>Lúc vào</th><th>Mã</th><th>Chiều</th><th>Lot</th><th>Lãi lỗ</th><th>Nguồn</th><th>Lỗi</th></tr></thead><tbody>${ds.map(x=>
  `<tr><td class="so">${ngayGio(x.mo)}</td><td>${esc(x.ma)}</td><td>${x.chieu==='MUA'?'MUA':'BÁN'}</td><td class="so">${fmt(x.lot,2)}</td><td class="so">${tien(x.lai,t)}</td><td>${esc(x.nguon||'')}</td><td>${x.loi.map(chip).join('')}</td></tr>`).join('')}</tbody></table></div>`
  :'<p class="ky-ghi">Không có lệnh nào phạm quy tắc.</p>';
 const ghi=[];if(D.ngay_cham_gioi_han&&D.ngay_cham_gioi_han.length)ghi.push(`Số ngày lỗ chạm giới hạn ngày: ${D.ngay_cham_gioi_han.length}.`);
 if(!D.co_lich_tin)ghi.push('Chưa kiểm quy tắc tin mạnh vì không có lịch tin cho khoảng này.');else if(D.khong_kiem_tin)ghi.push(`${D.khong_kiem_tin} lệnh vào trước khi lịch tin có dữ liệu nên chưa kiểm quy tắc tin mạnh.`);
 $('#ky-kq').innerHTML=`<div class="ky-y ${cls}" role="status">${y}</div><div class="ky-so">${the.join('')}</div>
  <section class="ky-card"><h2>Từng quy tắc</h2>${bang}</section>
  <section class="ky-card"><h2>Lệnh phạm quy tắc</h2>${lenh}</section>${ghi.length?`<p class="ky-ghi">${ghi.join(' ')}</p>`:''}`;
 if(LG==='en')document.querySelectorAll('#ky-kq td').forEach(td=>{if(td.textContent==='MUA')td.textContent='BUY';else if(td.textContent==='BÁN')td.textContent='SELL'})}
$('#ky-ngay').addEventListener('click',e=>{const b=e.target.closest('button[data-v]');if(!b)return;ST.ngay=+b.dataset.v;boLoc();goi()});
$('#ky-nguon').addEventListener('change',e=>{ST.nguon=e.target.value;goi()});
document.querySelectorAll('.ky-qt-f input').forEach(el=>el.addEventListener('input',goi));
boLoc();tai()})();
"""


def trang_ky_luat(ten: str) -> str:
    qt = ''.join(f'<label>{n}<input id="{k}" inputmode="decimal" autocomplete="off"></label>'
                 for k, n in (('q_rui_ro_lenh_toi_da_pct', 'Rủi ro tối đa mỗi lệnh (% vốn)'), ('q_lo_ngay_toi_da_pct', 'Giới hạn lỗ mỗi ngày (% vốn)'),
                              ('q_so_lenh_ngay_toi_da', 'Số lệnh tối đa mỗi ngày (0 = không kiểm)')))
    ngay = ''.join(f'<button type="button" data-v="{n}" aria-pressed="false">{n} ngày</button>' for n in (7, 30, 90))
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Kỷ luật giao dịch · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'ky-luat', '<button id="theme" type="button">Nền tối</button>') + '<main class="rong">',
        '<div class="ky-top"><h1>Kỷ luật giao dịch</h1><p>Trang chấm lại từng lệnh đã đóng trong MT5 theo quy tắc quản lý rủi ro của bạn: có dừng lỗ không, rủi ro '
        'bao nhiêu % số dư, có vào gấp hay tăng khối lượng sau lệnh thua, có vào thêm khi đã chạm giới hạn lỗ ngày, có vào sát tin mạnh. Rồi tách lãi lỗ '
        'của lệnh đúng quy tắc và lệnh phạm quy tắc để bạn thấy thói quen nào đang tốn tiền.</p></div>',
        f'<div class="ky-loc"><div class="ky-seg" id="ky-ngay" role="group" aria-label="Khoảng thời gian">{ngay}</div>'
        '<select id="ky-nguon" aria-label="Nguồn lệnh"><option value="">Mọi nguồn lệnh</option></select>'
        f'<details class="ky-qt"><summary>Quy tắc của bạn</summary><div class="ky-qt-f">{qt}</div></details></div>',
        '<section class="ky-kq" id="ky-kq" aria-live="polite"><p class="ky-cho">Đang đọc lịch sử lệnh…</p></section>',
        '<p class="note" style="margin-top:22px"><b>Chỉ đọc.</b> Dừng lỗ được lấy từ lệnh lúc vào; dừng lỗ thêm hoặc sửa sau khi vào không có trong lịch sử '
        'MT5, nên lệnh đặt dừng lỗ muộn vẫn bị tính là không có dừng lỗ (trừ khi lệnh đóng bởi dừng lỗ). % rủi ro tính trên số dư ngay trước lúc vào. '
        'Quy tắc dùng chung với trang <a href="/kiem-lenh">Kiểm tra trước khi vào lệnh</a>: kiểm ở đó trước lệnh tiếp theo để không lặp lại các lỗi này. '
        'Đúng quy tắc không bảo đảm lệnh thắng; không phải lời khuyên đầu tư.</p>',
        '<footer>' + escape(trang.mien_tru() if hasattr(trang, 'mien_tru') else trang.MIEN_TRU)
        + f'</footer></main><script>{trang.JS}</script><script>{JS}</script></body></html>'])
