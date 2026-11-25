"""Trang Kiểm tra trước khi vào lệnh (/kiem-lenh): nhập lệnh dự định, trang tính khối lượng theo % rủi ro và chấm từng quy tắc quản lý rủi ro
bằng dữ liệu thật từ MT5 (qua /api/kiem-lenh, kiem_lenh.py). Chỉ đọc, không đặt lệnh."""
from __future__ import annotations

from html import escape

from . import trang

CSS = r"""
main.rong{max-width:1240px}
.kl-top h1{margin:0}.kl-top p{margin:6px 0 0;color:var(--ink2);max-width:780px}
.kl{display:grid;grid-template-columns:minmax(0,380px) minmax(0,1fr);gap:16px;margin-top:16px;align-items:start}
@media(max-width:900px){.kl{grid-template-columns:minmax(0,1fr)}}
.kl-card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px}
.kl-card h2{font-size:15px;margin:0 0 12px}
.kl-f{display:grid;gap:12px}.kl-f label{display:grid;gap:5px;font-size:12.5px;color:var(--ink2);font-weight:600}
.kl-f input,.kl-f select{min-height:40px;border-radius:10px;border:1px solid var(--line);background:var(--card2);color:var(--ink);padding:0 12px;font:600 14px/1 inherit;font-family:inherit;width:100%;box-sizing:border-box}
.kl-f input:focus,.kl-f select:focus{outline:2px solid color-mix(in srgb,var(--series) 60%,transparent);outline-offset:1px}
.kl-2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.kl-ch{display:grid;grid-template-columns:1fr 1fr;gap:6px;background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:4px}
.kl-ch button{min-height:38px;border:0;border-radius:9px;background:none;color:var(--ink2);font:700 13px/1 inherit;font-family:inherit;cursor:pointer}
.kl-ch button[aria-pressed=true][data-v=MUA]{background:color-mix(in srgb,var(--gain) 18%,transparent);color:var(--gain)}
.kl-ch button[aria-pressed=true][data-v=BAN]{background:color-mix(in srgb,var(--loss) 18%,transparent);color:var(--loss)}
.kl-gia{display:flex;gap:8px}.kl-gia input{flex:1}.kl-gia button{flex:none;min-height:40px;padding:0 12px;border-radius:10px;font:600 12px/1 inherit;font-family:inherit;cursor:pointer}
.kl-goi{font-size:12px;color:var(--ink2);margin:-4px 0 0}
details.kl-qt{margin-top:4px;border-top:1px solid var(--line);padding-top:10px}details.kl-qt summary{cursor:pointer;font-size:13px;font-weight:700;color:var(--ink)}
.kl-kq{display:grid;gap:14px}
.kl-kl{display:flex;align-items:center;gap:14px;border-radius:16px;padding:16px 18px;border:1px solid var(--line);background:var(--card)}
.kl-kl i{width:46px;height:46px;border-radius:50%;display:grid;place-items:center;font-style:normal;font-weight:800;font-size:22px;flex:none}
.kl-kl b{display:block;font-size:20px}.kl-kl span{color:var(--ink2);font-size:13px}
.kl-kl.dat{border-color:color-mix(in srgb,var(--gain) 50%,var(--line));background:color-mix(in srgb,var(--gain) 8%,var(--card))}.kl-kl.dat i{background:var(--gain);color:#08110a}
.kl-kl.can_nhac{border-color:color-mix(in srgb,var(--warn) 55%,var(--line));background:color-mix(in srgb,var(--warn) 8%,var(--card))}.kl-kl.can_nhac i{background:var(--warn);color:#161000}
.kl-kl.khong_nen{border-color:color-mix(in srgb,var(--loss) 55%,var(--line));background:color-mix(in srgb,var(--loss) 8%,var(--card))}.kl-kl.khong_nen i{background:var(--loss);color:#1a0606}
.kl-so{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}
.kl-so div{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px}
.kl-so small{display:block;color:var(--ink2);font-size:12px}.kl-so b{display:block;font-size:20px;margin-top:4px}
.kl-ds{display:grid;gap:8px}
.kl-m{display:grid;grid-template-columns:28px minmax(0,1fr);gap:10px;align-items:start;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px}
.kl-m i{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;font-style:normal;font-weight:800;font-size:13px}
.kl-m b{display:block;font-size:13.5px}.kl-m p{margin:3px 0 0;color:var(--ink2);font-size:12.5px;line-height:1.5}
.kl-m.xau i{background:color-mix(in srgb,var(--loss) 22%,transparent);color:var(--loss)}.kl-m.chu_y i{background:color-mix(in srgb,var(--warn) 22%,transparent);color:var(--warn)}
.kl-m.tot i{background:color-mix(in srgb,var(--gain) 20%,transparent);color:var(--gain)}.kl-m.tin i{background:color-mix(in srgb,var(--series) 16%,transparent);color:var(--series)}
.kl-thieu{font-size:12.5px;color:var(--warn)}
.kl-cho{color:var(--ink2);font-size:13.5px;padding:24px;text-align:center;border:1px dashed var(--line);border-radius:14px}
"""

JS = r"""
(()=>{const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const NF={},fmt=(v,d=2)=>v==null||!isFinite(v)?'—':(NF[d]||(NF[d]=new Intl.NumberFormat('vi-VN',{minimumFractionDigits:d,maximumFractionDigits:d}))).format(v);
const QT={q_rui_ro_lenh_toi_da_pct:2,q_lo_ngay_toi_da_pct:3,q_tong_rui_ro_toi_da_pct:6};
let DS=[],chieu='MUA',hen=null,lan=0,daSl=false;const LG=document.documentElement.lang==='en'?'en':'vi';
try{Object.assign(QT,JSON.parse(localStorage.getItem('kl-qt')||'{}'))}catch(e){}
for(const k in QT){const el=$('#'+k);if(el)el.value=QT[k]}
const so=el=>{const v=parseFloat(String(el.value).replace(',','.'));return isFinite(v)?v:null};
const giaMa=()=>DS.find(x=>x.ma===$('#kl-ma').value);
function datGia(){const x=giaMa();if(!x||!x.q)return;$('#kl-vao').value=(chieu==='MUA'?x.q[1]:x.q[0]).toFixed(x.so_le??5);goi()}
async function taiMa(){try{const r=await fetch('/api/thi-truong',{cache:'no-store'});const j=await r.json();DS=(j.ds||[]).filter(x=>x.q);
  const u=new URLSearchParams(location.search),chon=u.get('ma')||localStorage.getItem('kl-ma')||(DS.find(x=>/XAU/.test(x.ma))||DS[0]||{}).ma;
  $('#kl-ma').innerHTML=DS.map(x=>`<option value="${esc(x.ma)}"${x.ma===chon?' selected':''}>${esc(x.goc||x.ma)} · ${esc(x.ten||'')}</option>`).join('');
  if(u.get('chieu')==='BAN'){chieu='BAN'}boChieu();if(!$('#kl-vao').value)datGia()}
 catch(e){$('#kl-kq').innerHTML=`<p class="kl-cho">Không đọc được danh sách mã: ${esc(e.message)}</p>`}}
function boChieu(){document.querySelectorAll('#kl-ch button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.v===chieu))}
if(LG==='en')document.querySelectorAll('#kl-ch button').forEach(b=>{b.textContent=b.dataset.v==='MUA'?'BUY':'SELL'});
function goi(){clearTimeout(hen);hen=setTimeout(kiem,350)}
async function kiem(){const ma=$('#kl-ma').value,vao=so($('#kl-vao')),sl=so($('#kl-sl')),tp=so($('#kl-tp')),rr=so($('#kl-rr'));
 try{localStorage.setItem('kl-ma',ma)}catch(e){}
 if(!ma||vao==null){$('#kl-kq').innerHTML='<p class="kl-cho">Chọn mã và nhập giá vào để bắt đầu.</p>';return}
 if(sl==null&&!daSl){$('#kl-kq').innerHTML='<p class="kl-cho">Nhập mức dừng lỗ (SL) để tính khối lượng và kiểm lệnh.</p>';return}
 const q=new URLSearchParams({ma,chieu,vao});if(sl!=null)q.set('sl',sl);if(tp!=null)q.set('tp',tp);if(rr!=null)q.set('rui_ro',rr);
 for(const k in QT){const el=$('#'+k),v=el?so(el):null;if(v!=null){q.set(k,v);QT[k]=v}}try{localStorage.setItem('kl-qt',JSON.stringify(QT))}catch(e){}
 const n=++lan;$('#kl-kq').setAttribute('aria-busy','true');
 try{const r=await fetch('/api/kiem-lenh?'+q,{cache:'no-store'});const t=await r.text();if(n!==lan)return;if(!r.ok)throw new Error(t);ve(JSON.parse(t))}
 catch(e){if(n===lan)$('#kl-kq').innerHTML=`<p class="kl-cho">Không kiểm được: ${esc(e.message)}</p>`}
 finally{if(n===lan)$('#kl-kq').removeAttribute('aria-busy')}}
function ve(D){const t=D.tien||'';const icon={xau:'✕',chu_y:'!',tot:'✓',tin:'i'};
 const so4=[['Khối lượng gợi ý',D.lot!=null?fmt(D.lot,2)+' lot':'—'],['Mất nếu chạm dừng lỗ',D.rui_ro_tien!=null?fmt(D.rui_ro_tien)+' '+t:'—'],
  ['Lời/lỗ',D.rr!=null?'1:'+fmt(D.rr,2):'—'],['Cần thắng để hòa vốn',D.hoa_von_pct!=null?fmt(D.hoa_von_pct,0)+'%':'—'],['Tổng rủi ro đang mở',D.tong_rui_ro_pct!=null?fmt(D.tong_rui_ro_pct,1)+'% vốn':'—']];
 $('#kl-kq').innerHTML=`<div class="kl-kl ${D.ket_luan}" role="status"><i>${{dat:'✓',can_nhac:'!',khong_nen:'✕'}[D.ket_luan]}</i><div><b>${{dat:'Đạt',can_nhac:'Cân nhắc',khong_nen:'Không nên'}[D.ket_luan]}</b><span>${esc((D.ket_luan_chu||{})[LG]||(D.ket_luan_chu||{}).vi||'')}</span></div></div>
  <div class="kl-so">${so4.map(([a,b])=>`<div><small>${a}</small><b>${b}</b></div>`).join('')}</div>
  ${(D.thieu||[]).length?`<p class="kl-thieu">Chưa kiểm được hết: ${D.thieu.map(esc).join('; ')}.</p>`:''}
  <div class="kl-ds">${D.muc.map(m=>{const c=m[LG]||m.vi;return`<div class="kl-m ${m.muc}"><i>${icon[m.muc]}</i><div><b>${esc(c.tieu)}</b>${c.noi?`<p>${esc(c.noi)}</p>`:''}</div></div>`}).join('')}</div>`}
$('#kl-ch').addEventListener('click',e=>{const b=e.target.closest('button[data-v]');if(!b)return;chieu=b.dataset.v;boChieu();goi()});
$('#kl-ma').addEventListener('change',()=>{$('#kl-sl').value='';$('#kl-tp').value='';datGia()});
$('#kl-lay').addEventListener('click',datGia);
document.querySelectorAll('.kl-f input').forEach(el=>el.addEventListener('input',goi));$('#kl-sl').addEventListener('input',()=>{daSl=true});
taiMa().then(goi)})();
"""


def trang_kiem_lenh(ten: str) -> str:
    qt = ''.join(f'<label>{n}<input id="{k}" inputmode="decimal" autocomplete="off"></label>'
                 for k, n in (('q_rui_ro_lenh_toi_da_pct', 'Rủi ro tối đa mỗi lệnh (% vốn)'), ('q_lo_ngay_toi_da_pct', 'Giới hạn lỗ mỗi ngày (% vốn)'),
                              ('q_tong_rui_ro_toi_da_pct', 'Tổng rủi ro tối đa đang mở (% vốn)')))
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Kiểm tra lệnh · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'kiem-lenh', '<button id="theme" type="button">Nền tối</button>') + '<main class="rong">',
        '<div class="kl-top"><h1>Kiểm tra trước khi vào lệnh</h1><p>Nhập lệnh bạn định vào. Trang tính khối lượng đúng theo % rủi ro và kiểm từng quy tắc quản lý '
        'rủi ro bằng dữ liệu thật từ MT5 của bạn: dừng lỗ, lời/lỗ, biến động, spread, tin mạnh sắp ra, lỗ trong ngày, tổng rủi ro đang mở, '
        'các lệnh đi cùng một cược. Trang không đoán giá và không đặt lệnh.</p></div>',
        '<div class="kl"><form class="kl-card kl-f" onsubmit="return false" aria-label="Lệnh dự định"><h2>Lệnh dự định</h2>',
        '<label>Mã<select id="kl-ma"><option>Đang tải…</option></select></label>',
        '<div class="kl-ch" id="kl-ch" role="group" aria-label="Chiều"><button type="button" data-v="MUA" aria-pressed="true">MUA</button>'
        '<button type="button" data-v="BAN" aria-pressed="false">BÁN</button></div>',
        '<label>Giá vào<span class="kl-gia"><input id="kl-vao" inputmode="decimal" autocomplete="off">'
        '<button type="button" class="ghost" id="kl-lay">Giá hiện tại</button></span></label>',
        '<div class="kl-2"><label>Dừng lỗ (SL)<input id="kl-sl" inputmode="decimal" autocomplete="off"></label>'
        '<label>Chốt lời (TP)<input id="kl-tp" inputmode="decimal" autocomplete="off"></label></div>',
        '<label>Rủi ro lệnh này (% vốn)<input id="kl-rr" inputmode="decimal" autocomplete="off" value="1"></label>',
        '<p class="kl-goi">Khối lượng được tính để chạm dừng lỗ chỉ mất đúng % vốn này.</p>',
        f'<details class="kl-qt"><summary>Quy tắc của bạn</summary><div class="kl-f" style="margin-top:10px">{qt}</div></details></form>',
        '<section class="kl-kq" id="kl-kq" aria-live="polite"><p class="kl-cho">Đang tải giá…</p></section></div>',
        '<p class="note" style="margin-top:22px"><b>Chỉ đọc.</b> Trang dùng giá, tài khoản, lệnh đang mở và lịch tin từ MT5 trên máy bạn để kiểm quy tắc '
        'quản lý rủi ro. Đạt các quy tắc không có nghĩa lệnh sẽ thắng; không phải lời khuyên đầu tư.</p>',
        '<footer>' + escape(trang.mien_tru() if hasattr(trang, 'mien_tru') else trang.MIEN_TRU)
        + f'</footer></main><script>{trang.JS}</script><script>{JS}</script></body></html>'])
