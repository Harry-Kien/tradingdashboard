"""Panel trạng thái cảnh báo cấu trúc, dùng chung trên Biểu đồ và Telegram."""

HTML = ('<details class="live-cau-truc"><summary>Theo dõi FVG/iFVG trên MT5</summary>'
        '<div data-cau-truc-live>Đang chờ bộ theo dõi…</div></details>')

CSS = """
.live-cau-truc{font-size:12.5px;line-height:1.55;color:var(--ink2);padding:10px 12px}
.live-cau-truc summary{cursor:pointer;color:var(--ink);font-weight:700}
.live-cau-truc p{margin:6px 0}
.live-cau-truc .ct-vung{border-top:1px solid var(--line);padding:7px 0;overflow-wrap:anywhere}
.live-cau-truc .ct-tf{display:flex;gap:5px;flex-wrap:wrap;margin-top:4px}
.live-cau-truc .ct-tf b{border:1px solid var(--line);border-radius:5px;padding:1px 5px;font-size:11px}
.live-cau-truc .ct-dat{color:var(--gain)}.live-cau-truc .ct-cu{color:var(--loss)}
"""

JS = r"""
(()=>{const root=document.querySelector('[data-cau-truc-live]');if(!root)return;
const box=root.closest('details'),esc=x=>String(x??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const ten={cham:'Chạm vùng',xac_nhan:'Xác nhận',vo_hieu:'Vô hiệu'},state={cho:'Đang chờ gửi',da_gui:'Đã gửi',xem:'Xem trước',
 het_han:'Hết hạn',loi_gui:'Lỗi gửi',khong_ro:'Chưa xác minh được việc gửi',dang_gui:'Đang gửi'};
const dir={1:'tăng',0:'trung tính','-1':'giảm'},fmtDate=v=>new Date(v).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour12:false});
let busy=false,data=null;
function render(){const d=data;if(!d)return;
 const fresh=d.luc_tick&&Date.now()-d.luc_tick>=-5000&&Date.now()-d.luc_tick<=30000&&!d.loi;
 const status=!d.bat?'Chưa bật theo dõi':fresh?d.mode==='gui'?'Đang theo dõi · gửi Telegram':'Đang theo dõi · xem trước':
   d.loi||'Đang chờ tick MT5 mới';
 const nf=new Intl.NumberFormat('vi-VN',{maximumFractionDigits:Math.max(0,Math.min(8,d.so_le??2))}),p=v=>nf.format(v);
 let h='<p'+(fresh?'':' class="ct-cu"')+'><b>'+esc(d.ma||'')+'</b> · '+esc(status)+'</p>';
 if(d.luc_tick)h+='<p>Tick MT5 '+esc(fmtDate(d.luc_tick))+' · H1 '+esc(dir[d.h1])+' · H4 '+esc(dir[d.h4])+'</p>';
 if(fresh&&Number.isFinite(d.bid)&&Number.isFinite(d.ask))h+='<p>Bid '+esc(p(d.bid))+' · Ask '+esc(p(d.ask))+'</p>';
 if(fresh&&d.trang_thai==='lech_khung')h+='<p><b>Đứng ngoài · H1/H4 chưa đồng thuận</b></p>';
 const zs=d.vung||[];
 if(d.ma&&fresh&&!zs.length)h+='<p>Chưa có vùng H1 trong phạm vi theo dõi.</p>';
 for(const z of zs){const flags=['M5','M15','M30'].map(k=>'<b'+(z.tf?.[k]?' class="ct-dat"':'')+'>'+k+
  (z.tf?.[k]?' xác nhận':z.cham?' chờ':'')+'</b>').join('');
  h+='<div class="ct-vung"><strong>'+esc(z.loai_vung)+' '+esc(p(z.duoi))+'–'+esc(p(z.tren))+
   '</strong><br>'+ (z.huy?'Đã vô hiệu':z.cham?'Đã chạm · '+esc(fmtDate(z.cham)):'Chờ giá chạm')+
   ' · vô hiệu H1 '+esc(p(z.vo_hieu))+'<div class="ct-tf">'+flags+'</div></div>';
 }
 for(const e of (d.su_kien||[]).slice(0,5)){
  h+='<div class="ct-vung"><b>'+esc(ten[e.loai])+' '+esc(e.tf||'')+' · '+esc(e.ma)+'</b><br>'+
   esc(fmtDate(e.ms))+' · '+esc(state[e.tt]||'')+(e.loi?' · '+esc(e.loi):'')+'</div>';
 }
 if(root.innerHTML!==h)root.innerHTML=h;
}
async function doc(){if(busy||!box.open||document.visibilityState==='hidden')return;busy=true;
 try{const r=await fetch('/api/cau-truc-live',{cache:'no-store'});if(!r.ok)throw Error();data=await r.json();render()}
 catch(_){root.textContent='Chưa đọc được trạng thái theo dõi.'}finally{busy=false}}
box.addEventListener('toggle',doc);setInterval(()=>{if(box.open){render();doc()}},5000);doc();})();
"""
