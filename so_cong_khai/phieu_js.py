"""Đoạn JS dùng chung cho phiếu kế hoạch (phieu_ke_hoach.py) trên trang Kế hoạch, Kiểm tra lệnh và Nhật ký: tải phiếu, vẽ ba trạng thái
tách riêng (điều kiện kỹ thuật, kiểm rủi ro, mức kiểm chứng), báo chỗ người dùng đã đổi so với phiếu, gửi việc lên /api/phieu."""

JS = r"""
window.PKJ=(()=>{const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const KT={con_hieu_luc:['tot','Điều kiện kỹ thuật còn hiệu lực'],het_hieu_luc:['','Điều kiện kỹ thuật đã hết hiệu lực'],chua_cap_nhat:['xau','Phân tích chưa cập nhật được lúc lập phiếu'],
 tk_dung:['xau','Đủ điều kiện kỹ thuật · tài khoản đang dừng'],tham_khao:['','Chỉ để tham khảo'],khong_ro:['','Chưa rõ']};
const RR={chua_kiem:['','Chưa kiểm rủi ro'],dat:['tot','Đạt kiểm rủi ro'],can_nhac:['chu_y','Cân nhắc'],khong_nen:['xau','Không nên theo kiểm rủi ro'],can_kiem_lai:['chu_y','Cần kiểm lại']};
const KQ={tp:'Chạm chốt lời',sl:'Chạm dừng lỗ',dang_mo:'Đang mở trong mô phỏng',chua_khop:'Giá chưa chạm mức vào',chua_xac_dinh:'Chưa xác định',khong_theo_doi:'Chưa theo dõi'};
const gio=s=>s?new Date(s).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
const so=v=>v==null?'—':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:5});
async function tai(id){const r=await fetch('/api/phieu?id='+encodeURIComponent(id),{cache:'no-store'});const t=await r.text();if(!r.ok)throw new Error(t);
 try{localStorage.setItem('so-phieu-cuoi',id)}catch(e){}return JSON.parse(t)}                // phiếu gần nhất cho hộp "AI giải thích" (rủi ro, review)
async function gui(viec,o){const r=await fetch('/api/phieu',{method:'POST',headers:{'Content-Type':'application/json','X-So-Cong-Khai':'1'},body:JSON.stringify({viec,...o})});
 const j=await r.json().catch(()=>({ok:false,thong_bao:'Máy chủ không trả lời đúng.'}));if(!r.ok||!j.ok)throw new Error(j.thong_bao||('lỗi '+r.status));return j.phieu}
// cur: {ma,chieu,vao,sl,tp} người dùng đang nhập; trả danh sách trường đã đổi so với phiếu
function doi(p,cur){const d=[];if(!cur)return d;const g=(a,b)=>a!=null&&b!=null&&Math.abs(+a-+b)>1e-9;
 if(cur.chieu&&cur.chieu!==p.chieu)d.push('chiều');if(g(cur.vao,p.vao))d.push('giá vào');if(g(cur.sl,p.sl)||(cur.sl==null)!==(p.sl==null))d.push('dừng lỗ');
 if(cur.tp!==undefined&&g(cur.tp,(p.tp||[])[0]))d.push('chốt lời');return d}
function html(p,cur){const pp=p.phuong_phap||{},k=KT[p.ky_thuat]||KT.khong_ro,r=RR[(p.rui_ro||{}).trang_thai]||RR.chua_kiem,d=doi(p,cur),c=p.cham||{};
 return`<section class="kh-card kh-pk pkj" id="pk-${esc(p.id)}"><h2>Phiếu ${esc(p.id)} · bản ${p.phien_ban}${p.moi_nhat&&p.moi_nhat!==p.phien_ban?' (mới nhất: bản '+p.moi_nhat+')':''}
  <small>${esc(pp.ten||pp.ma||'')}${pp.phien_ban_quy_tac?' · '+esc(pp.phien_ban_quy_tac):''} · nến tín hiệu ${gio(p.nen_tin_hieu)} · phân tích lúc ${gio(p.luc_phan_tich)}</small></h2>
  <p class="pkj-l">${esc(p.ma)} · <b>${p.chieu==='MUA'?'MUA':'BÁN'}</b> · vào ${so(p.vao)} · SL ${so(p.sl)} · TP ${(p.tp||[]).map(so).join(' / ')||'—'}${p.rui_ro_pct?' · rủi ro '+so(p.rui_ro_pct)+'%':''} · ${esc(p.tai_khoan==='mo_phong'?'phạm vi mô phỏng':p.tai_khoan)}</p>
  <div class="kh-so"><div><small>Điều kiện kỹ thuật (lúc lập phiếu)</small><b class="pkj-${k[0]}">${k[1]}</b></div>
   <div><small>Kiểm quản lý rủi ro</small><b class="pkj-${r[0]}">${r[1]}</b>${(p.rui_ro||{}).ly_do?'<span>'+esc(p.rui_ro.ly_do)+'</span>':(p.rui_ro||{}).luc?'<span>lúc '+gio(p.rui_ro.luc)+'</span>':''}</div>
   <div><small>Mức kiểm chứng của phương pháp</small><b>${esc(pp.kiem_chung||'chưa rõ')}</b></div>
   <div><small>Theo dõi mô phỏng</small><b>${p.theo_doi?esc(KQ[c.trang_thai]||c.trang_thai||'—'):'Chưa theo dõi'}</b><span>${p.theo_doi?'từ '+gio(p.theo_doi.tu)+(c.r!=null?' · '+(c.r>0?'+':'')+so(c.r)+'R':'')+(c.ly_do?' · '+esc(c.ly_do):''):''}</span></div></div>
  ${d.length?`<p class="kh-doi pkj-doi">Bạn đã đổi ${d.join(', ')} so với phiếu. Kết quả trên trang là cho lệnh đã đổi; phiếu giữ nguyên cho tới khi bạn lưu bản mới.</p>`:''}
  ${p.dieu_kien_vo_hieu?`<p class="kh-ghi">Điểm vô hiệu: ${esc(p.dieu_kien_vo_hieu)}</p>`:''}
  <p class="kh-ghi">Ba trạng thái trên độc lập nhau: qua kiểm rủi ro không có nghĩa phương pháp có lợi thế hay lệnh sẽ thắng.</p></section>`}
const CSS='.pkj b.pkj-tot{color:var(--gain)}.pkj b.pkj-xau{color:var(--loss)}.pkj b.pkj-chu_y{color:var(--warn,#f5b301)}.pkj .pkj-l{margin:4px 0 10px;font-size:13.5px}'
 +'.pkj .kh-so{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}.pkj .kh-so small{display:block;color:var(--mute);font-size:12px}.pkj .kh-so span{display:block;font-size:12px;color:var(--ink2)}'
 +'.pkj .pkj-doi{color:var(--loss);font-weight:600;font-size:13px}.pkj-nut{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}';
document.head.insertAdjacentHTML('beforeend','<style>'+CSS+'</style>');
return{tai,gui,html,doi,KT,RR,KQ,gio}})();
"""
