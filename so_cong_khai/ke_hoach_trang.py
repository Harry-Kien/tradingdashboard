"""Trang Kế hoạch vốn và lệnh (/ke-hoach): nhập vốn và mức rủi ro → phân bổ vốn, mô phỏng xác suất sụt vốn; chọn mã, chiều, phong cách → gợi ý
dừng lỗ, chốt lời, khối lượng, ký quỹ và khoảng tới mức sàn đóng lệnh (qua /api/ke-hoach, ke_hoach.py). Chỉ đọc, không đặt lệnh."""
from __future__ import annotations

from html import escape

from . import trang

CSS = r"""
main.rong{max-width:1560px}
.kh-top h1{margin:0}.kh-top p{margin:6px 0 0;color:var(--ink2);max-width:820px}
.kh{display:grid;grid-template-columns:minmax(0,370px) minmax(0,1fr);gap:16px;margin-top:16px;align-items:start}
@media(max-width:920px){.kh{grid-template-columns:minmax(0,1fr)}}
.kh-card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;min-width:0}
.kh-card h2{font-size:15px;margin:0 0 12px}.kh-card h2 small{font-weight:500;color:var(--ink2);font-size:12px;margin-left:6px}
.kh-f{display:grid;gap:12px}.kh-f label{display:grid;gap:5px;font-size:12.5px;color:var(--ink2);font-weight:600}.kh-f label[hidden]{display:none}
.kh-f input,.kh-f select{min-height:40px;border-radius:10px;border:1px solid var(--line);background:var(--card2);color:var(--ink);padding:0 12px;font:600 14px/1 inherit;font-family:inherit;width:100%;box-sizing:border-box}
.kh-2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.kh-seg{display:grid;gap:4px;background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:4px}
.kh-seg.c2{grid-template-columns:1fr 1fr}.kh-seg.c3{grid-template-columns:1fr 1fr 1fr}.kh-seg.c4{grid-template-columns:repeat(4,1fr)}
.kh-seg button{min-height:38px;border:0;border-radius:9px;background:none;color:var(--ink2);font:700 12.5px/1.15 inherit;font-family:inherit;cursor:pointer;padding:4px 2px}
.kh-seg button small{display:block;font-weight:600;font-size:11px;opacity:.8;margin-top:2px}
.kh-seg button[aria-pressed=true]{background:color-mix(in srgb,var(--series) 18%,transparent);color:var(--ink)}
.kh-seg button[aria-pressed=true][data-v=MUA]{background:color-mix(in srgb,var(--gain) 18%,transparent);color:var(--gain)}
.kh-seg button[aria-pressed=true][data-v=BAN]{background:color-mix(in srgb,var(--loss) 18%,transparent);color:var(--loss)}
.kh-gia{display:flex;gap:8px}.kh-gia input{flex:1}.kh-gia button{flex:none;min-height:40px;padding:0 12px;border-radius:10px;font:600 12px/1 inherit;font-family:inherit;cursor:pointer}
.kh-goi{font-size:12px;color:var(--ink2);margin:-4px 0 0}
details.kh-mp{border-top:1px solid var(--line);padding-top:10px}details.kh-mp summary{cursor:pointer;font-size:13px;font-weight:700}
.kh-kq{display:grid;gap:14px}
.kh-kl{display:flex;align-items:center;gap:14px;border-radius:16px;padding:14px 18px;border:1px solid var(--line);background:var(--card)}
.kh-kl i{width:42px;height:42px;border-radius:50%;display:grid;place-items:center;font-style:normal;font-weight:800;font-size:20px;flex:none}
.kh-kl b{display:block;font-size:18px}.kh-kl span{color:var(--ink2);font-size:13px}
.kh-kl.tot{border-color:color-mix(in srgb,var(--gain) 50%,var(--line));background:color-mix(in srgb,var(--gain) 8%,var(--card))}.kh-kl.tot i{background:var(--gain);color:#08110a}
.kh-kl.chu_y{border-color:color-mix(in srgb,var(--warn) 55%,var(--line));background:color-mix(in srgb,var(--warn) 8%,var(--card))}.kh-kl.chu_y i{background:var(--warn);color:#161000}
.kh-kl.xau{border-color:color-mix(in srgb,var(--loss) 55%,var(--line));background:color-mix(in srgb,var(--loss) 8%,var(--card))}.kh-kl.xau i{background:var(--loss);color:#1a0606}
.kh-so{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
@media(max-width:700px){.kh-so{grid-template-columns:repeat(2,minmax(0,1fr))}}
.kh-so div{background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:10px 12px;min-width:0}
.kh-so small{display:block;color:var(--ink2);font-size:11.5px}.kh-so b{display:block;font-size:19px;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kh-so b em{font-style:normal;font-size:12px;color:var(--ink2);font-weight:600}.kh-so div>span{display:block;color:var(--ink2);font-size:11.5px;margin-top:2px}
.kh-bang{overflow-x:auto}.kh-bang table{width:100%;border-collapse:collapse;font-size:13px}
.kh-bang th{color:var(--ink2);font-weight:600;text-align:left;font-size:12px;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
.kh-bang td{padding:8px;border-bottom:1px solid var(--line);vertical-align:middle}.kh-bang td.so{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.kh-bang tr:last-child td{border-bottom:0}.kh-bang td p{margin:2px 0 0;color:var(--ink2);font-size:11.5px}
.kh-bang tr.chon td{background:color-mix(in srgb,var(--series) 9%,transparent)}
.kh-bang button{min-height:30px;padding:0 10px;border-radius:8px;font:600 12px/1 inherit;font-family:inherit;cursor:pointer}
.kh-ds{display:grid;gap:8px;margin:0;padding:0;list-style:none}
.kh-ds li{display:grid;grid-template-columns:24px minmax(0,1fr);gap:8px;align-items:start;font-size:13px;line-height:1.5}
.kh-ds li i{width:22px;height:22px;border-radius:7px;display:grid;place-items:center;font-style:normal;font-weight:800;font-size:12px}
.kh-ds li.xau i{background:color-mix(in srgb,var(--loss) 22%,transparent);color:var(--loss)}.kh-ds li.chu_y i{background:color-mix(in srgb,var(--warn) 22%,transparent);color:var(--warn)}
.kh-ds li.tot i{background:color-mix(in srgb,var(--gain) 20%,transparent);color:var(--gain)}
.kh-hd{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.kh-hd a.btn{display:inline-flex;align-items:center;min-height:40px;padding:0 16px;border-radius:10px;font-weight:700;font-size:13.5px;text-decoration:none;
 background:color-mix(in srgb,var(--series) 22%,transparent);color:var(--ink);border:1px solid color-mix(in srgb,var(--series) 45%,var(--line))}
.kh-ghi{font-size:12px;color:var(--ink2);margin:0}
.kh-lai{color:var(--gain)}.kh-lo{color:var(--loss)}
.kh-cho{color:var(--ink2);font-size:13.5px;padding:24px;text-align:center;border:1px dashed var(--line);border-radius:14px}
"""

JS = r"""
(()=>{const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const LG=document.documentElement.lang==='en'?'en':'vi',LOC=LG==='en'?'en-US':'vi-VN';
const NF={},fmt=(v,d=2)=>v==null||!isFinite(v)?'—':(NF[d]||(NF[d]=new Intl.NumberFormat(LOC,{minimumFractionDigits:d,maximumFractionDigits:d}))).format(v);
const tien=(v,t,dau)=>v==null?'—':`<span class="${dau&&v>0?'kh-lai':dau&&v<0?'kh-lo':''}">${dau&&v>0?'+':''}${fmt(v)}</span> <em>${esc(t)}</em>`;
const pc=v=>v==null?'—':`<span class="${v>0?'kh-lai':v<0?'kh-lo':''}">${v>0?'+':''}${fmt(v,1)}%</span>`;
let ST={muc:'can_bang',chieu:'MUA',khung:'H1',thang:50,rr:2},DS=[],hen=null,lan=0,slTay=false,D=null;
try{Object.assign(ST,JSON.parse(localStorage.getItem('kh')||'{}'))}catch(e){}
const so=el=>{const v=parseFloat(String(el.value).replace(',','.'));return isFinite(v)?v:null};
function bo(){document.querySelectorAll('[data-nhom]').forEach(g=>g.querySelectorAll('button[data-v]').forEach(b=>b.setAttribute('aria-pressed',String(String(ST[g.dataset.nhom])===b.dataset.v))));
 $('#kh-rr-tu').closest('label').hidden=ST.muc!=='tu_dat'}
if(LG==='en')document.querySelectorAll('[data-nhom=chieu] button').forEach(b=>{b.textContent=b.dataset.v==='MUA'?'BUY':'SELL'});
$('#kh-thang').value=ST.thang;$('#kh-rrr').value=ST.rr;if(ST.von)$('#kh-von').value=ST.von;if(ST.rui_ro)$('#kh-rr-tu').value=ST.rui_ro;
async function taiMa(){try{const r=await fetch('/api/thi-truong',{cache:'no-store'});const j=await r.json();DS=(j.ds||[]).filter(x=>x.q);
  const u=new URLSearchParams(location.search),chon=u.get('ma')||ST.ma||(DS.find(x=>/XAU/.test(x.ma))||DS[0]||{}).ma;
  $('#kh-ma').innerHTML=DS.map(x=>`<option value="${esc(x.ma)}"${x.ma===chon?' selected':''}>${esc(x.goc||x.ma)} · ${esc(x.ten||'')}</option>`).join('')}
 catch(e){$('#kh-kq').innerHTML=`<p class="kh-cho">Không đọc được danh sách mã: ${esc(e.message)}</p>`}}
function goi(){clearTimeout(hen);hen=setTimeout(tai,350)}
async function tai(){const ma=$('#kh-ma').value;if(!ma)return;ST.ma=ma;
 const q=new URLSearchParams({ma,chieu:ST.chieu,khung:ST.khung,muc:ST.muc});const von=so($('#kh-von')),vao=so($('#kh-vao')),sl=so($('#kh-sl'));
 ST.von=von;if(von!=null)q.set('von',von);if(vao!=null)q.set('vao',vao);if(sl!=null&&slTay)q.set('sl',sl);
 if(ST.muc==='tu_dat'){const r=so($('#kh-rr-tu'));ST.rui_ro=r;if(r!=null)q.set('rui_ro',r)}
 const th=so($('#kh-thang')),rr=so($('#kh-rrr'));if(th!=null){q.set('thang',th);ST.thang=th}if(rr!=null){q.set('rr',rr);ST.rr=rr}
 try{localStorage.setItem('kh',JSON.stringify(ST))}catch(e){}
 const n=++lan;$('#kh-kq').setAttribute('aria-busy','true');
 try{const r=await fetch('/api/ke-hoach?'+q,{cache:'no-store'});const t=await r.text();if(n!==lan)return;if(!r.ok)throw new Error(t);D=JSON.parse(t);ve()}
 catch(e){if(n===lan)$('#kh-kq').innerHTML=`<p class="kh-cho">Chưa lập được kế hoạch: ${esc(e.message)}</p>`}
 finally{if(n===lan)$('#kh-kq').removeAttribute('aria-busy')}}
function ve(){const t=D.tien||'',V=D.von,L=D.lenh,M=D.muc,P=D.mo_phong,dl=D.so_le??2;
 if($('#kh-vao').value==='')$('#kh-vao').placeholder=fmt(D.vao,dl);
 if(!slTay){$('#kh-sl').value='';$('#kh-sl').placeholder=L?fmt(L.sl,dl):''}
 const canh=[];let muc='tot';const xau=(s)=>{canh.push(['xau',s]);muc='xau'},chu=(s)=>{canh.push(['chu_y',s]);if(muc==='tot')muc='chu_y'};
 if(L&&L.dung_lenh_truoc_sl)xau(`Sàn sẽ đóng lệnh (stop out) trước khi giá chạm dừng lỗ: giá chỉ cần chạy ngược ${fmt(L.kc_dung_lenh,dl)} là tài khoản bị đóng lệnh.`);
 if(L&&L.duoi_lot_min)xau(`Vốn quá nhỏ cho dừng lỗ này: khối lượng tính ra chỉ ${fmt(L.lot_tinh,3)} lot, dưới mức tối thiểu ${fmt(D.lot_min,2)} lot. Vào ${fmt(L.lot,2)} lot thì rủi ro thật là ${fmt(L.rui_ro_that_pct,1)}% vốn.${L.thua_lien_mat_50?` Thua liền ${L.thua_lien_mat_50} lệnh là mất một nửa vốn.`:''}`);
 if(V.rui_ro_pct>2)(V.rui_ro_pct>5?xau:chu)(`Rủi ro ${fmt(V.rui_ro_pct,1)}% mỗi lệnh: thua liền ${V.thua_lien_mat_50} lệnh là mất một nửa vốn.`);
 if(L&&L.ky_quy_pct>30)chu(`Ký quỹ dùng ${fmt(L.ky_quy_pct,0)}% vốn: còn ít chỗ cho lệnh khác và cho giá chạy ngược.`);
 if(M.chon&&M.sl[M.chon]&&M.sl[M.chon].qua_sat)chu('Dừng lỗ gần hơn khoảng cách tối thiểu sàn cho phép.');
 if(P.ky_vong_r<=0)xau(`Với tỷ lệ thắng ${fmt(ST.thang,0)}% và lời/lỗ 1:${fmt(ST.rr,1)}, kỳ vọng mỗi lệnh là âm: về lâu dài sẽ lỗ dù quản lý vốn tốt. Cần thắng trên ${fmt(P.hoa_von_pct,0)}% số lệnh mới hòa vốn.`);
 if(P.xs_sut_50>=5)xau(`Mô phỏng: ${fmt(P.xs_sut_50,0)}% khả năng có lúc mất một nửa tài khoản trong ${P.so_lenh} lệnh.`);
 else if(P.xs_sut_20>=25)chu(`Mô phỏng: ${fmt(P.xs_sut_20,0)}% khả năng có lúc sụt 20% vốn trong ${P.so_lenh} lệnh.`);
 if(!canh.length)canh.push(['tot','Không thấy rủi ro cháy tài khoản với kế hoạch này. Kết quả từng lệnh vẫn có thể thắng hoặc thua.']);
 const KL={tot:['✓','Kế hoạch an toàn'],chu_y:['!','Cần xem lại'],xau:['✕','Nguy cơ cháy tài khoản']}[muc];
 const MUCV={an_toan:'An toàn',can_bang:'Cân bằng',manh:'Mạnh',tu_dat:'Tự đặt'}[V.muc]||V.muc;
 const von=`<section class="kh-card"><h2>Phân bổ vốn<small>${D.nguon_von==='mt5'?'vốn lấy từ MT5':D.nguon_von==='mau'?'vốn mẫu của bản demo':'vốn bạn nhập'} · ${esc(MUCV)}</small></h2><div class="kh-so">
  <div><small>Vốn</small><b>${tien(V.von,t)}</b></div>
  <div><small>Rủi ro mỗi lệnh</small><b>${tien(V.rui_ro_tien,t)}</b><span>${fmt(V.rui_ro_pct,1)}% vốn</span></div>
  <div><small>Dừng giao dịch khi lỗ trong ngày</small><b>${tien(V.lo_ngay_tien,t)}</b><span>${V.so_lenh_thua_ngay} lệnh thua</span></div>
  <div><small>Tổng rủi ro được mở</small><b>${tien(V.tong_mo_tien,t)}</b><span>tối đa ${V.so_lenh_cung_luc} lệnh cùng lúc</span></div></div>
  <p class="kh-ghi" style="margin-top:10px">Với mức này, phải thua liền ${V.thua_lien_mat_20} lệnh mới mất 20% vốn và ${V.thua_lien_mat_50} lệnh mới mất một nửa.</p></section>`;
 let lenh='';
 if(L){const sl=Object.entries(M.sl).map(([k,s])=>`<tr class="${Math.abs(s.gia-L.sl)<1e-9?'chon':''}"><td><b>${k==='cau_truc'?'Theo cấu trúc giá':'Theo biến động'}</b><p>${k==='cau_truc'?(D.chieu==='MUA'?'Sau đáy gần nhất, lùi thêm spread':'Sau đỉnh gần nhất, lùi thêm spread'):'1,5 lần ATR '+esc(D.khung)}</p></td>
   <td class="so">${fmt(s.gia,dl)}</td><td class="so">${s.atr!=null?fmt(s.atr,1)+' ATR':'—'}</td><td><button type="button" class="ghost" data-sl="${s.gia}">Dùng</button></td></tr>`).join('');
  const tp=L.tp.map((x,i)=>`<tr><td><b>${i<3?(i+1)+'R':'Đỉnh/đáy gần nhất'}</b>${i===3?'<p>Vùng giá từng quay đầu</p>':''}</td><td class="so">${fmt(x.gia,dl)}</td><td class="so">1:${fmt(x.r,1)}</td><td class="so">${tien(x.lai_tien,t,1)}</td></tr>`).join('');
  const tp2=L.tp[1]?L.tp[1].gia:'';
  const link=new URLSearchParams({ma:D.ma,chieu:D.chieu,vao:D.vao,sl:L.sl,rui_ro:V.rui_ro_pct});if(tp2)link.set('tp',tp2);
  lenh=`<section class="kh-card"><h2>Dừng lỗ, chốt lời và khối lượng<small>${esc(D.goc)} · <span style="text-transform:uppercase">${D.chieu==='MUA'?'Mua':'Bán'}</span> · vào ${fmt(D.vao,dl)}</small></h2>
  <div class="kh-so"><div><small>Khối lượng</small><b>${fmt(L.lot,2)} <em>lot</em></b><span>${L.duoi_lot_min?'mức tối thiểu của sàn':'làm tròn xuống theo bước lot'}</span></div>
   <div><small>Mất nếu chạm dừng lỗ</small><b>${tien(-L.rui_ro_tien,t,1)}</b><span>${fmt(L.rui_ro_that_pct,2)}% vốn</span></div>
   <div><small>Ký quỹ cần</small><b>${L.ky_quy!=null?tien(L.ky_quy,t):'—'}</b><span>${L.ky_quy_pct!=null?fmt(L.ky_quy_pct,1)+'% vốn':''}</span></div>
   <div><small>Giá chạy ngược tới mức sàn đóng lệnh</small><b>${L.kc_dung_lenh!=null?fmt(L.kc_dung_lenh,dl):'—'}</b><span>${L.kc_dung_lenh!=null?'dừng lỗ cách '+fmt(Math.abs(D.vao-L.sl),dl)+' · chỉ tính lệnh này':'sàn tính mức đóng lệnh bằng tiền'}</span></div></div>
  <h3 style="font-size:13.5px;margin:16px 0 6px">Dừng lỗ gợi ý</h3><div class="kh-bang"><table><thead><tr><th>Cách đặt</th><th>Giá</th><th>Khoảng</th><th></th></tr></thead><tbody>${sl||'<tr><td colspan="4">Chưa đủ dữ liệu nến để gợi ý.</td></tr>'}</tbody></table></div>
  <h3 style="font-size:13.5px;margin:16px 0 6px">Chốt lời</h3><div class="kh-bang"><table><thead><tr><th>Mức</th><th>Giá</th><th>Lời/lỗ</th><th>Lời nếu chạm</th></tr></thead><tbody>${tp}</tbody></table></div>
  <div class="kh-hd" style="margin-top:14px"><a class="btn" href="/kiem-lenh?${link}">Kiểm tra lệnh này trước khi vào</a><span class="kh-ghi">Trang kiểm tra xem thêm tin mạnh, spread, lỗ trong ngày và các lệnh đang mở.</span></div></section>`}
 else lenh=`<section class="kh-card"><p class="kh-cho">Chưa đủ dữ liệu để gợi ý dừng lỗ. Hãy nhập mức dừng lỗ.</p></section>`;
 const mp=`<section class="kh-card"><h2>Mô phỏng ${P.so_lenh} lệnh<small>${P.theo_rui_ro_that?'theo rủi ro thật '+fmt(P.theo_rui_ro_that,1)+'% mỗi lệnh · ':''}${fmt(P.lan,0)} lần · thắng ${fmt(ST.thang,0)}% · lời/lỗ 1:${fmt(ST.rr,1)}</small></h2><div class="kh-so">
  <div><small>Kết quả thường gặp (trung vị)</small><b>${pc(P.trung_vi_pct)}</b><span>vốn sau ${P.so_lenh} lệnh</span></div>
  <div><small>5% trường hợp xấu nhất</small><b>${pc(P.xau_5_pct)}</b><span>hoặc tệ hơn</span></div>
  <div><small>Khả năng sụt 20%</small><b>${fmt(P.xs_sut_20,1)}%</b><span>sụt trung vị ${fmt(P.sut_trung_vi_pct,1)}%</span></div>
  <div><small>Khả năng mất một nửa</small><b>${fmt(P.xs_sut_50,1)}%</b><span>kỳ vọng ${fmt(P.ky_vong_r,2)}R mỗi lệnh</span></div></div>
  <p class="kh-ghi" style="margin-top:10px">Mỗi lần mô phỏng xáo ngẫu nhiên thứ tự thắng thua theo tỷ lệ thắng bạn nhập. Đây là phép thử rủi ro của cách quản lý vốn, không phải dự báo lợi nhuận.</p></section>`;
 $('#kh-kq').innerHTML=`<div class="kh-kl ${muc}" role="status"><i>${KL[0]}</i><div><b>${KL[1]}</b><span>${muc==='tot'?'Rủi ro mỗi lệnh và ký quỹ trong mức an toàn.':'Xem các điểm bên dưới.'}</span></div></div>
  <section class="kh-card"><ul class="kh-ds">${canh.map(([m,s])=>`<li class="${m}"><i>${{xau:'✕',chu_y:'!',tot:'✓'}[m]}</i><span>${s}</span></li>`).join('')}</ul></section>
  ${lenh}${von}${mp}${(D.thieu||[]).length?`<p class="kh-ghi">Chưa đủ dữ liệu: ${D.thieu.map(esc).join('; ')}.</p>`:''}`}
document.addEventListener('click',e=>{const b=e.target.closest('[data-nhom] button[data-v]');if(b){const g=b.closest('[data-nhom]').dataset.nhom;ST[g]=b.dataset.v;if(g!=='muc'){slTay=false;$('#kh-sl').value=''}
  if(g==='chieu'){$('#kh-vao').value=''}bo();goi();return}
 const s=e.target.closest('button[data-sl]');if(s){$('#kh-sl').value=s.dataset.sl;slTay=true;goi()}});
$('#kh-ma').addEventListener('change',()=>{$('#kh-vao').value='';$('#kh-sl').value='';slTay=false;goi()});
$('#kh-lay').addEventListener('click',()=>{$('#kh-vao').value='';goi()});
$('#kh-sl').addEventListener('input',()=>{slTay=$('#kh-sl').value.trim()!=='';goi()});
['#kh-von','#kh-vao','#kh-rr-tu','#kh-thang','#kh-rrr'].forEach(s=>$(s).addEventListener('input',goi));
bo();taiMa().then(tai)})();
"""


def _nhom(ten: str, cot: int, ds: list[tuple[str, str, str]], nhan: str) -> str:
    nut = ''.join(f'<button type="button" data-v="{v}" aria-pressed="false">{a}{f"<small>{b}</small>" if b else ""}</button>' for v, a, b in ds)
    return f'<div class="kh-seg c{cot}" data-nhom="{ten}" role="group" aria-label="{nhan}">{nut}</div>'


def trang_ke_hoach(ten: str) -> str:
    muc = _nhom('muc', 4, [('an_toan', 'An toàn', '0,5%'), ('can_bang', 'Cân bằng', '1%'), ('manh', 'Mạnh', '2%'), ('tu_dat', 'Tự đặt', '% riêng')], 'Mức rủi ro')
    chieu = _nhom('chieu', 2, [('MUA', 'MUA', ''), ('BAN', 'BÁN', '')], 'Chiều')
    khung = _nhom('khung', 3, [('M15', 'Lướt sóng', 'M15'), ('H1', 'Trong ngày', 'H1'), ('H4', 'Dài hơn', 'H4')], 'Phong cách')
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Kế hoạch vốn · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'ke-hoach', '<button id="theme" type="button">Nền tối</button>') + '<main class="rong">',
        '<div class="kh-top"><h1>Kế hoạch vốn và lệnh</h1><p>Nhập vốn và chọn mức rủi ro: trang chia vốn thành rủi ro mỗi lệnh, giới hạn lỗ ngày, tổng rủi ro '
        'được mở, rồi mô phỏng hàng nghìn chuỗi lệnh để cho biết khả năng sụt vốn. Chọn mã và chiều: trang gợi ý dừng lỗ theo đỉnh/đáy gần nhất và theo '
        'biến động, chốt lời theo bội số R, tính khối lượng, ký quỹ và khoảng giá tới mức sàn đóng lệnh, để một lệnh không thể làm cháy tài khoản.</p></div>',
        '<div class="kh"><form class="kh-card kh-f" onsubmit="return false" aria-label="Kế hoạch"><h2>Vốn và mức rủi ro</h2>',
        '<label>Vốn (để trống: lấy vốn từ MT5)<input id="kh-von" inputmode="decimal" autocomplete="off" placeholder="Lấy từ MT5"></label>',
        muc, '<label hidden>Rủi ro mỗi lệnh (% vốn)<input id="kh-rr-tu" inputmode="decimal" autocomplete="off" value="1"></label>',
        '<h2 style="margin:8px 0 0">Lệnh</h2><label>Mã<select id="kh-ma"><option>Đang tải…</option></select></label>', chieu, khung,
        '<label>Giá vào (để trống: giá hiện tại)<span class="kh-gia"><input id="kh-vao" inputmode="decimal" autocomplete="off">'
        '<button type="button" class="ghost" id="kh-lay">Giá hiện tại</button></span></label>',
        '<label>Dừng lỗ (để trống: dùng mức gợi ý)<input id="kh-sl" inputmode="decimal" autocomplete="off"></label>',
        '<details class="kh-mp"><summary>Mô phỏng: tỷ lệ thắng và lời/lỗ của bạn</summary><div class="kh-2" style="margin-top:10px">'
        '<label>Tỷ lệ thắng (%)<input id="kh-thang" inputmode="decimal" autocomplete="off"></label>'
        '<label>Lời/lỗ trung bình (R)<input id="kh-rrr" inputmode="decimal" autocomplete="off"></label></div></details></form>',
        '<section class="kh-kq" id="kh-kq" aria-live="polite"><p class="kh-cho">Đang lập kế hoạch…</p></section></div>',
        '<p class="note" style="margin-top:22px"><b>Chỉ đọc.</b> Giá, nến, ATR, thông số mã, ký quỹ (MT5 tính) và mức sàn đóng lệnh lấy từ MT5 trên máy bạn. '
        'Các mức dừng lỗ, chốt lời là gợi ý quản lý rủi ro dựa trên dữ liệu hiện tại, không phải dự báo giá; đạt kế hoạch không bảo đảm lệnh thắng; '
        'không phải lời khuyên đầu tư.</p>',
        '<footer>' + escape(trang.mien_tru() if hasattr(trang, 'mien_tru') else trang.MIEN_TRU)
        + f'</footer></main><script>{trang.JS}</script><script>{JS}</script></body></html>'])
