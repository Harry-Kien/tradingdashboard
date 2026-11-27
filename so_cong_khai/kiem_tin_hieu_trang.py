"""Trang Kiểm chứng tín hiệu nhóm (/kiem-tin-hieu): dán các tin tín hiệu chép từ Telegram, trang dò lại từng tín hiệu trên nến 1 phút thật của MT5
(qua /api/kiem-tin-hieu, kiem_tin_hieu.py) và cho tỷ lệ thắng thật, lãi lỗ theo R. Chỉ đọc giá; đoạn dán không gửi ra ngoài máy."""
from __future__ import annotations

from html import escape

from . import trang

CSS = r"""
main.rong{max-width:1560px}
.kt-top h1{margin:0}.kt-top p{margin:6px 0 0;color:var(--ink2);max-width:820px}
.kt{display:grid;grid-template-columns:minmax(0,400px) minmax(0,1fr);gap:16px;margin-top:16px;align-items:start}
@media(max-width:940px){.kt{grid-template-columns:minmax(0,1fr)}}
.kt-card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kt-card h2{margin:0 0 8px;font-size:16px}
.kt-f{display:grid;gap:10px}.kt-f label{display:grid;gap:4px;font-size:13px;color:var(--ink2)}
.kt-f textarea{min-height:260px;resize:vertical;font:13px/1.5 ui-monospace,Consolas,monospace;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:10px}
.kt-f select,.kt-f input[type=number]{min-height:34px;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:0 8px}
.kt-2{display:grid;grid-template-columns:1fr 1fr;gap:10px}.kt-f .chk{display:flex;gap:8px;align-items:center;color:var(--ink)}
.kt-goi{font-size:12px;color:var(--mute);margin:0}
.kt-o{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:12px}
.kt-o div{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.kt-o small{display:block;color:var(--mute);font-size:12px}.kt-o b{font-size:22px;font-variant-numeric:tabular-nums}.kt-o i{font-style:normal;font-size:12px;color:var(--ink2)}
.kt-nx{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--series);border-radius:10px;padding:10px 14px;margin-bottom:12px;font-size:13.5px;line-height:1.55}
.kt-nx p{margin:4px 0}
.kt-bang{width:100%;border-collapse:collapse;font-size:12.5px;font-variant-numeric:tabular-nums}
.kt-bang th,.kt-bang td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
.kt-bang th{color:var(--mute);font-weight:600}.kt-wrap{overflow-x:auto}
.kt-bang small{display:block;color:var(--mute)}
.kt-t{display:inline-block;padding:2px 8px;border-radius:999px;font-weight:700;font-size:11.5px;white-space:nowrap}
.kt-t.tot{background:color-mix(in srgb,var(--gain,#17935b) 18%,transparent);color:var(--gain,#17935b)}
.kt-t.xau{background:color-mix(in srgb,var(--loss,#e5532d) 18%,transparent);color:var(--loss,#e5532d)}
.kt-t.ve{background:color-mix(in srgb,var(--mute) 20%,transparent);color:var(--ink2)}
.kt-loi{margin-top:12px;font-size:12.5px;color:var(--ink2)}.kt-loi li{margin:3px 0}
.kt-cho{color:var(--mute)}
"""

JS = r"""
(()=>{const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const KQ=$('#kt-kq'),f2=v=>v==null?'—':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:2}),fr=v=>v==null?'—':(v>0?'+':'')+f2(v)+'R',
 fg=v=>v==null?'—':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:v<20?5:2}),pc=v=>v==null?'—':f2(v)+'%';
const TT={het_tp:['Chạm hết TP','tot'],tp_roi_sl:['Chạm TP rồi về SL','ve'],hoa_von:['Chạm TP rồi hòa vốn','ve'],thua:['Chạm SL trước TP','xau'],
 dang_mo:['Chưa xong','ve'],khong_khop:['Không khớp','ve'],khong_du_lieu:['Không có dữ liệu','ve'],loi:['Lỗi','ve']};
const gio=s=>new Date(s).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'});
try{const v=localStorage.getItem('kt-dan');if(v)$('#kt-dan').value=v}catch(e){}
function nhanXet(t){const o=[];if(!t.xong){o.push('Chưa có tín hiệu nào chạy xong để chấm.');return o}
 if(t.tp1_cach_tb!=null&&t.tp1_cach_tb<0.7&&t.ty_le_tp1>=60)o.push(`TP1 chỉ cách giá vào trung bình <b>${f2(t.tp1_cach_tb)}R</b> (nhỏ hơn khoảng cách tới dừng lỗ), nên "chạm TP1" dễ: tỷ lệ chạm TP1 <b>${pc(t.ty_le_tp1)}</b> không nói được nhóm có lãi.`);
 if(t.r_tp1_tb!=null)o.push(`Nếu chốt hết ở TP1: trung bình <b>${fr(t.r_tp1_tb)}</b> mỗi lệnh (tổng ${fr(t.r_tp1_tong)} trên ${t.xong} lệnh). Nếu chia đều cho các TP: <b>${fr(t.r_chia_tb)}</b> mỗi lệnh.`);
 if(t.r_chia_tb!=null)o.push(t.r_chia_tb>0.1&&t.xong>=30?'Kết quả dương trên mẫu khá: đáng theo dõi thêm, nhưng quá khứ không bảo đảm tương lai.':t.r_chia_tb>0?'Dương nhẹ hoặc mẫu còn nhỏ: chưa đủ để kết luận nhóm có lợi thế.':'Âm: theo đúng các tín hiệu này thì đang mất tiền, dù tin "chạm TP" trông nhiều.');
 if(t.xong<30)o.push(`Mẫu mới có ${t.xong} lệnh chạy xong; cần ít nhất vài chục lệnh mới nói được điều gì chắc.`);
 if(t.khong_khop)o.push(`${t.khong_khop} tín hiệu không khớp (giá không về mức vào trong thời hạn chờ): nhóm thường vẫn đếm các tín hiệu này nếu giá chạy đúng hướng.`);return o}
function ve(d){if(!d.ok){KQ.innerHTML=`<p class="kt-cho">${esc(d.ly_do||'Chưa kiểm được.')}</p>`+loi(d.loi);return}
 const t=d.tong;if(!t.tin){KQ.innerHTML='<p class="kt-cho">Chưa đọc được tín hiệu nào trong đoạn dán.</p>'+loi(d.loi);return}
 let h=`<div class="kt-o"><div><small>Tín hiệu đọc được</small><b>${t.tin}</b><i>${t.khop} khớp · ${t.khong_khop} không khớp${t.khong_du_lieu?' · '+t.khong_du_lieu+' thiếu dữ liệu':''}</i></div>`
  +`<div><small>Chạm TP1</small><b>${pc(t.ty_le_tp1)}</b><i>${t.tp1}/${t.khop} lệnh khớp</i></div>`
  +`<div><small>Chạm SL trước mọi TP</small><b>${pc(t.ty_le_thua)}</b><i>${t.thua}/${t.xong} lệnh xong</i></div>`
  +`<div><small>Chạm hết các TP</small><b>${pc(t.ty_le_het_tp)}</b><i>${t.het_tp}/${t.xong} lệnh xong</i></div>`
  +`<div><small>Lãi lỗ mỗi lệnh (chia đều TP)</small><b>${fr(t.r_chia_tb)}</b><i>chốt hết ở TP1: ${fr(t.r_tp1_tb)}</i></div></div>`;
 h+='<div class="kt-nx">'+nhanXet(t).map(x=>`<p>${x}</p>`).join('')+'</div>';
 h+='<div class="kt-wrap"><table class="kt-bang"><thead><tr><th>Giờ gửi</th><th>Tín hiệu</th><th>Vào</th><th>SL / TP</th><th>Kết quả</th><th>R</th></tr></thead><tbody>';
 for(const x of d.ds){const k=x.kq||{},tt=TT[k.trang_thai]||[k.trang_thai,'ve'];
  h+=`<tr><td>${gio(x.gio)}</td><td><b>${x.chieu==='MUA'?'MUA':'BÁN'}</b> ${esc(x.ma_san||x.ma)}<small>${x.ngay?'vào ngay':'chờ '+(x.vung||[]).map(fg).join('–')}</small></td>`
   +`<td>${fg(k.vao)}</td><td>${fg(x.sl)}<small>${x.tp.map(fg).join(' · ')}</small></td>`
   +`<td><span class="kt-t ${tt[1]}">${esc(tt[0])}</span><small>${k.tp_cham?'chạm '+k.tp_cham+'/'+x.tp.length+' TP':''}${k.ghi_chu?(k.tp_cham?' · ':'')+esc(k.ghi_chu):''}</small></td>`
   +`<td>${fr(k.r_chia)}<small>TP1: ${fr(k.r_tp1)}</small></td></tr>`}
 KQ.innerHTML=h+'</tbody></table></div>'+loi(d.loi)}
function loi(ds){return ds&&ds.length?`<details class="kt-loi"><summary>${ds.length} đoạn có chữ BUY/SELL chưa đọc được</summary><ul>${ds.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></details>`:''}
async function kiem(){const dan=$('#kt-dan').value.trim();if(!dan){KQ.innerHTML='<p class="kt-cho">Dán các tin tín hiệu vào ô bên trái trước.</p>';return}
 try{localStorage.setItem('kt-dan',dan.slice(0,60000))}catch(e){}
 const b=$('#kt-nut');b.disabled=true;b.textContent='Đang dò trên giá thật…';KQ.innerHTML='<p class="kt-cho">Đang đọc tín hiệu và dò từng tín hiệu trên nến 1 phút của MT5…</p>';
 try{const r=await fetch('/api/kiem-tin-hieu',{method:'POST',headers:{'Content-Type':'application/json','X-So-Cong-Khai':'1'},body:JSON.stringify({van_ban:dan,
   mui_gio:+$('#kt-mg').value,cho_gio:+$('#kt-cho').value,giu_ngay:+$('#kt-giu').value,ve_hoa_von:$('#kt-hv').checked,ma_mac_dinh:$('#kt-ma').value})});
  ve(await r.json())}catch(e){KQ.innerHTML='<p class="kt-cho">Không gửi được tới webapp.</p>'}
 b.disabled=false;b.textContent='Kiểm chứng'}
$('#kt-nut').addEventListener('click',kiem)})();
"""

VI_DU = ('Gold VIP, [25.11.2026 14:05]\nXAUUSD SELL NOW 3540-3545\nSL 3552\nTP1 3535\nTP2 3530\n\n'
         'Gold VIP, [25.11.2026 16:30]\nGOLD BUY LIMIT 3500\nSL: 3492\nTP: 3505/3510/3520')


def trang_kiem_tin_hieu(ten: str) -> str:
    mg = ''.join(f'<option value="{v}"{" selected" if v == 7 else ""}>{n}</option>'
                 for v, n in ((7, 'Giờ Việt Nam (GMT+7)'), (0, 'GMT+0'), (2, 'GMT+2'), (3, 'GMT+3'), (8, 'GMT+8')))
    ma = ''.join(f'<option value="{m}">{m}</option>' for m in ('XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD', 'US30', 'NAS100'))
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.KHOI_TAO_NEN}{trang.BIEU_TUONG}<title>Kiểm chứng tín hiệu · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'kiem-tin-hieu', '<button id="theme" type="button">Nền tối</button>') + '<main class="rong">',
        '<div class="kt-top"><h1>Kiểm chứng tín hiệu nhóm</h1><p>Dán các tin tín hiệu chép từ nhóm Telegram (chọn nhiều tin, chuột phải, Copy). '
        'Trang dò lại từng tín hiệu trên nến 1 phút thật của MT5: giá chạm dừng lỗ hay chốt lời trước, rồi cho tỷ lệ thắng thật và lãi lỗ theo R, '
        'kể cả những tín hiệu nhóm không báo kết quả.</p></div>',
        '<div class="kt"><form class="kt-card kt-f" onsubmit="return false" aria-label="Tín hiệu cần kiểm"><h2>Tín hiệu</h2>',
        f'<label>Dán tin từ Telegram<textarea id="kt-dan" spellcheck="false" placeholder="{escape(VI_DU)}"></textarea></label>',
        '<p class="kt-goi">Mỗi tin cần dòng có giờ gửi (Telegram tự chép kèm khi bạn chọn nhiều tin), chữ BUY/SELL, SL và TP.</p>',
        f'<div class="kt-2"><label>Giờ trong tin theo<select id="kt-mg">{mg}</select></label><label>Mã khi tin không ghi<select id="kt-ma">{ma}</select></label></div>',
        '<div class="kt-2"><label>Lệnh chờ sống (giờ)<input type="number" id="kt-cho" min="0.25" max="72" step="0.25" value="4"></label>'
        '<label>Giữ lệnh tối đa (ngày)<input type="number" id="kt-giu" min="0.1" max="30" step="0.5" value="5"></label></div>',
        '<label class="chk"><input type="checkbox" id="kt-hv"> Dời dừng lỗ về giá vào sau khi chạm TP1</label>',
        '<button type="button" class="act" id="kt-nut">Kiểm chứng</button></form>',
        '<section id="kt-kq" aria-live="polite"><p class="kt-cho">Kết quả hiện ở đây.</p></section></div>',
        '<p class="note" style="margin-top:22px"><b>Cách chấm.</b> Tin có NOW/ngay: vào theo giá mở của phút ngay sau tin. Tin có giá vào: khớp khi giá chạm mức đó '
        '(vùng: chạm cạnh gần giá nhất) trong thời hạn chờ. Một nến chạm cả dừng lỗ và chốt lời thì tính dừng lỗ trước. R = khoảng giá vào tới dừng lỗ. '
        'Giá dò là giá Bid trên sàn của bạn, chưa trừ spread và phí, nên có thể lệch vài giá so với sàn của nhóm. Đoạn dán chỉ xử lý trên máy bạn.</p>',
        '<footer>' + escape(trang.MIEN_TRU) + f'</footer></main><script>{trang.JS}</script><script>{JS}</script></body></html>'])
