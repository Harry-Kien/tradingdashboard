"""Bản JavaScript của ke_hoach.py (ke_hoach_von, mo_phong, goi_y_muc, tinh_lenh, lap) cho trang demo tĩnh trên GitHub Pages: trang demo không có máy
chủ Python, nên tính kế hoạch ngay trong trình duyệt từ dữ liệu thô đã chụp (ke_hoach.du_lieu_tho). Giữ khớp từng dòng với ke_hoach.py;
tests/test_ke_hoach_js.py chạy cả hai bản trên cùng đầu vào bằng Node.js và so kết quả (mô phỏng dùng bộ sinh số ngẫu nhiên khác nên so theo sai số)."""

JS_TINH = r"""
const KH=(()=>{
const MUC={an_toan:{lenh:.5,ngay:1.5,mo:2},can_bang:{lenh:1,ngay:3,mo:4},manh:{lenh:2,ngay:5,mo:6}},KHUNG=['M15','H1','H4'];
const R=(x,d)=>Number(x.toFixed(d));                 // như round() của Python: làm tròn đúng giá trị nhị phân của số
const loi=s=>{throw new Error(s)};
function chuoi(r,mat){r=Math.min(Math.max(r,1e-9),99.999)/100;return Math.max(1,Math.ceil(Math.log(1-mat/100)/Math.log(1-r)))}
function von(v,muc,rr){if(!v||v<=0)loi('vốn phải lớn hơn 0');let m=Object.assign({},MUC[muc]||MUC.can_bang);
 if(rr!=null){if(!(rr>0&&rr<=100))loi('rủi ro mỗi lệnh phải trong (0, 100]');m={lenh:rr,ngay:Math.min(100,rr*3),mo:Math.min(100,rr*4)};muc='tu_dat'}
 return{von:R(v,2),muc,rui_ro_pct:m.lenh,lo_ngay_pct:m.ngay,tong_mo_pct:m.mo,rui_ro_tien:R(v*m.lenh/100,2),lo_ngay_tien:R(v*m.ngay/100,2),tong_mo_tien:R(v*m.mo/100,2),
  so_lenh_cung_luc:Math.max(1,Math.floor(m.mo/m.lenh+1e-9)),so_lenh_thua_ngay:Math.max(1,Math.floor(m.ngay/m.lenh+1e-9)),thua_lien_mat_20:chuoi(m.lenh,20),thua_lien_mat_50:chuoi(m.lenh,50)}}
function rng(a){return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function moPhong(rr,thang,rrr,n=100,lan=2000,seed=7){if(!(rr>0&&rr<100)||!(thang>=0&&thang<=100)||!(rrr>0))loi('tham số mô phỏng không hợp lệ');
 const ng=rng(seed),r=rr/100,p=thang/100,cuoi=[],sm=[];let s20=0,s50=0;
 for(let i=0;i<lan;i++){let v=1,d=1,s=0;for(let j=0;j<n;j++){v*=ng()<p?1+r*rrr:1-r;if(v>d)d=v;s=Math.max(s,1-v/d)}cuoi.push(v);sm.push(s);s20+=s>=.2;s50+=s>=.5}
 cuoi.sort((a,b)=>a-b);sm.sort((a,b)=>a-b);const pt=(xs,q)=>xs[Math.min(xs.length-1,Math.floor(q*xs.length))];
 return{so_lenh:n,lan,ky_vong_r:R(p*rrr-(1-p),3),hoa_von_pct:R(100/(1+rrr),1),trung_vi_pct:R((pt(cuoi,.5)-1)*100,1),xau_5_pct:R((pt(cuoi,.05)-1)*100,1),
  tot_5_pct:R((pt(cuoi,.95)-1)*100,1),xs_sut_20:R(s20/lan*100,1),xs_sut_50:R(s50/lan*100,1),sut_trung_vi_pct:R(pt(sm,.5)*100,1)}}
function dinhDay(cao,thap,k=2){const dinh=[],day=[];for(let i=k;i<cao.length-k;i++){const c=cao.slice(i-k,i+k+1),t=thap.slice(i-k,i+k+1);
 if(cao[i]===Math.max(...c))dinh.push(cao[i]);if(thap[i]===Math.min(...t))day.push(thap[i])}return[dinh,day]}
function goiY(chieu,vao,cao,thap,atr,spread,so_le,toiThieu){if(chieu!=='MUA'&&chieu!=='BAN')loi('chieu phải là MUA hoặc BAN');
 const mua=chieu==='MUA',dau=mua?1:-1,[dinh,day]=dinhDay(cao,thap),dem=(spread||0)+(atr?.1*atr:0),sl={};
 const phia=(mua?day:dinh).slice().reverse().filter(p=>mua?p<vao:p>vao);
 if(phia.length){const g=phia[0]-dau*dem;sl.cau_truc={gia:R(g,so_le),kc:R(Math.abs(vao-g),so_le+1)}}
 if(atr){const g=vao-dau*1.5*atr;sl.bien_dong={gia:R(g,so_le),kc:R(1.5*atr,so_le+1)}}
 for(const v of Object.values(sl)){v.atr=atr?R(v.kc/atr,2):null;v.qua_sat=!!(toiThieu&&v.kc<toiThieu)}
 let chon=null;if(sl.cau_truc&&(!atr||(sl.cau_truc.atr>=.5&&sl.cau_truc.atr<=3)))chon='cau_truc';else if(sl.bien_dong)chon='bien_dong';else if(Object.keys(sl).length)chon=Object.keys(sl)[0];
 const tp=[];if(chon){const kc=sl[chon].kc;for(const r of[1,2,3])tp.push({k:r+'R',gia:R(vao+dau*r*kc,so_le),r});
  const truoc=(mua?dinh:day).slice().reverse().filter(p=>mua?p>vao:p<vao);if(truoc.length){const g=truoc[0];tp.push({k:'cau_truc',gia:R(g,so_le),r:R(Math.abs(g-vao)/kc,2)})}}
 return{chieu,vao,atr,sl,chon,tp}}
function lenh(v,rr,vao,sl,tps,gt1,lmin=.01,lbuoc=.01,lmax=100,kq1=null,dung=null){const kc=Math.abs(vao-sl);if(!(kc>0)||!(gt1>0)||!(v>0))loi('cần giá vào khác dừng lỗ, giá trị bước giá và vốn dương');
 const mt=v*rr/100,lt=mt/(kc*gt1);let lot=Math.min(lmax,Math.floor(lt/lbuoc+1e-9)*lbuoc);const duoi=lot<lmin;if(duoi)lot=lmin;lot=R(lot,4);const mat=kc*gt1*lot;
 const o={lot_tinh:R(lt,4),lot,duoi_lot_min:duoi,rui_ro_muc_tieu:R(mt,2),rui_ro_tien:R(mat,2),rui_ro_that_pct:R(mat/v*100,2),tp:[]};
 for(const g of tps||[])o.tp.push({gia:g,lai_tien:R(Math.abs(g-vao)*gt1*lot,2),r:R(Math.abs(g-vao)/kc,2)});
 if(kq1){const kq=kq1*lot;Object.assign(o,{ky_quy:R(kq,2),ky_quy_pct:R(kq/v*100,2),muc_ky_quy:kq?R(v/kq*100,0):null});
  if(dung!=null&&kq){const con=v-kq*dung/100;o.kc_dung_lenh=con>0?R(con/(gt1*lot),6):0;o.dung_lenh_truoc_sl=o.kc_dung_lenh<kc}}
 return o}
function lap(raw,p,tk){const{chieu,khung='H1',muc='can_bang',thang=50,rr=2}=p;let{vao=null,sl=null,von:v=null}=p;
 if(!KHUNG.includes(khung))loi('khung phải là M15, H1 hoặc H4');const dt=raw.dac_ta||{};
 let nguon='nhap';if(v==null){v=tk.von;nguon='mt5'}const kh=von(v,muc,muc==='tu_dat'?p.rui_ro:null);let mp=moPhong(kh.rui_ro_pct,thang,rr);
 const bid=raw.bid,ask=raw.ask;if(vao==null){if(bid==null)loi('chưa có giá trực tiếp của mã này, hãy nhập giá vào');vao=chieu==='MUA'?ask:bid}
 const spread=bid!=null?ask-bid:0,so_le=dt.so_le||2,thieu=[];if(!raw.cao.length)thieu.push('chưa đọc được nến từ MT5');if(!raw.atr)thieu.push('chưa có ATR của khung này');
 const m=goiY(chieu,+vao,raw.cao,raw.thap,raw.atr,spread,so_le,(dt.muc_dung||0)*(dt.diem||0));
 const sd=sl!=null?sl:(m.chon?m.sl[m.chon].gia:null);let L=null;
 if(sd!=null){if((chieu==='MUA'&&sd>=vao)||(chieu==='BAN'&&sd<=vao))loi('dừng lỗ nằm sai phía giá vào');const kc=Math.abs(vao-sd),dau=chieu==='MUA'?1:-1;
  const tps=[1,2,3].map(k=>R(vao+dau*k*kc,so_le));for(const t of m.tp)if(t.k==='cau_truc')tps.push(t.gia);
  if(dt.gt1){L=lenh(kh.von,kh.rui_ro_pct,+vao,+sd,tps,+dt.gt1,+(dt.lot_min||.01),+(dt.lot_buoc||.01),+(dt.lot_max||100),dt.ky_quy_1lot,tk.dung_lenh);L.sl=sd;
   if(L.duoi_lot_min&&L.rui_ro_that_pct>kh.rui_ro_pct){const r=Math.min(L.rui_ro_that_pct,99);mp=Object.assign(moPhong(r,thang,rr),{theo_rui_ro_that:r});
    L.thua_lien_mat_20=chuoi(r,20);L.thua_lien_mat_50=chuoi(r,50)}}else thieu.push('chưa có giá trị bước giá của mã này')}
 return{ma:raw.ma,goc:dt.goc||raw.ma,chieu,khung,vao:+vao,bid,ask,so_le,tien:tk.tien||'USD',nguon_von:nguon,don_bay:tk.don_bay,dung_lenh_pct:tk.dung_lenh,
  lot_min:dt.lot_min,von:kh,mo_phong:mp,muc:m,lenh:L,thieu}}
return{von,moPhong,goiY,lenh,lap,chuoi}})();
"""
