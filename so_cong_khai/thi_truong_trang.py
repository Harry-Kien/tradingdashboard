"""Trang Thị trường (/thi-truong): bảng giá trực tiếp mọi mã Forex và CFD, sức mạnh tiền tệ, bản đồ nhiệt, tương quan, phiên giao dịch,
lịch tin và thông số hợp đồng. Giá đẩy về qua luồng SSE /api/thi-truong/luong (xem thi_truong.py); thông số và mốc giá qua /api/thi-truong.

JS_CHUNG là phần dùng chung với trang Công cụ và trang Học giao dịch: nạp bảng, nối luồng giá, các hàm định dạng và tính thay đổi."""
from __future__ import annotations

from html import escape

from . import trang

# --------------------------------------------------------------------------- kiểu dáng dùng chung cho ba trang mới
CSS = r"""
main.rong{max-width:1560px}
.tt-top{display:flex;justify-content:space-between;align-items:flex-end;gap:12px 24px;flex-wrap:wrap;padding-bottom:12px;border-bottom:1px solid var(--line)}
.tt-top h1{margin:0}.tt-top p{margin:6px 0 0;color:var(--ink2);max-width:760px}
.song-pill{display:inline-flex;align-items:center;gap:8px;font-size:12.5px;color:var(--ink2);background:var(--card);border:1px solid var(--line);border-radius:999px;padding:6px 12px;white-space:nowrap}
.song-pill i{width:8px;height:8px;border-radius:50%;background:var(--mute);flex:none}
.song-pill.ok i{background:var(--gain);box-shadow:0 0 0 0 color-mix(in srgb,var(--gain) 60%,transparent);animation:nhip 1.8s infinite}
.song-pill.loi i{background:var(--loss)}.song-pill b{color:var(--ink);font-weight:600}
.tt-moi{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px;margin:12px 0 0;padding:12px 16px;border-radius:14px;border:1px solid color-mix(in srgb,var(--series) 45%,var(--line));background:color-mix(in srgb,var(--series) 8%,var(--card));font-size:14px}.tt-moi[hidden]{display:none}.tt-moi span{color:var(--ink2);flex:1 1 260px}.tt-moi a{display:inline-flex;align-items:center;min-height:34px;padding:0 14px;border-radius:10px;background:var(--series);color:var(--btn-ink);font-weight:700;text-decoration:none}.tt-moi button{min-height:34px;padding:0 12px;border-radius:10px;border:1px solid var(--line);background:none;color:var(--ink2);font:inherit;cursor:pointer}
.song-pill.loi{white-space:normal;max-width:100%;min-width:0;border-radius:12px;overflow-wrap:anywhere}  /* lý do lỗi dài (MT5 tắt) không đẩy trang rộng 2169px trên điện thoại */
@keyframes nhip{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--gain) 55%,transparent)}70%{box-shadow:0 0 0 7px transparent}100%{box-shadow:0 0 0 0 transparent}}
.tt-hero{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:16px 0 4px}
.tt-hero>div{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;min-width:0}
.tt-hero>div>span{display:block;font-size:12px;color:var(--mute)}.tt-hero b{display:block;font-size:20px;line-height:1.3;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tt-hero small{display:block;font-size:12px;color:var(--ink2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tt-hero .breadth{display:flex;height:6px;border-radius:3px;overflow:hidden;margin-top:7px;background:var(--track)}.tt-hero .breadth u{background:var(--gain)}.tt-hero .breadth s{background:var(--loss)}
.sg{display:inline-flex;flex-wrap:wrap;gap:4px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:4px}
.sg button{min-height:32px;padding:0 13px;border:0;border-radius:8px;background:none;color:var(--ink2);font:600 12.5px/1 inherit;font-family:inherit;cursor:pointer;white-space:nowrap}
.sg button:hover{color:var(--ink);background:color-mix(in srgb,var(--ink) 6%,transparent)}
.sg button[aria-pressed=true],.sg button[aria-selected=true]{background:color-mix(in srgb,var(--series) 16%,transparent);color:var(--series);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--series) 45%,transparent)}
.sg button small{font-weight:500;opacity:.7;margin-left:4px}
.tt-tabs{position:sticky;top:var(--nv-h,56px);z-index:4;margin:18px 0 0;padding:8px 0;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)}
.tt-tabs .sg{display:flex;overflow-x:auto;flex-wrap:nowrap;scrollbar-width:none}
.tt-tool{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;margin:12px 0}
.tt-tool .grow{flex:1}
.tt-tool input[type=search],.cc input,.cc select,.tt-tool select{min-height:36px;border:1px solid var(--line);border-radius:10px;background:var(--card2);color:var(--ink);padding:0 12px;font:inherit;font-size:13px}
.tt-tool input[type=search]{min-width:220px}
.tt-p[hidden]{display:none}
.tt-card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-top:14px}
.tt-card h2{margin:0 0 4px}.tt-card>.sub{margin:0 0 12px;font-size:12.5px;color:var(--ink2)}
.tt-wrap{overflow:auto;border:1px solid var(--line);border-radius:12px;max-height:calc(100vh - 210px)}
.tt-wrap table{font-size:13px}
.tt-wrap thead th{position:sticky;top:0;z-index:2;background:var(--card2);cursor:default}
.tt-wrap th[data-k]{cursor:pointer;user-select:none}.tt-wrap th[data-k]:hover{color:var(--ink)}
.tt-wrap th[aria-sort=ascending]::after{content:" ▲";font-size:9px}.tt-wrap th[aria-sort=descending]::after{content:" ▼";font-size:9px}
.tt-wrap td,.tt-wrap th{padding:7px 10px}
.bg td.ma a{color:var(--ink);text-decoration:none;font-weight:700;letter-spacing:.01em}.bg td.ma a:hover{color:var(--series)}
.bg td.ma small{display:block;font-size:11.5px;color:var(--mute);max-width:230px;overflow:hidden;text-overflow:ellipsis}
.bg tr.nhom th{position:static;background:var(--bg);color:var(--series);font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;padding:10px 10px 6px;text-align:left}
.bg td.gia{font-weight:600;font-size:13.5px;border-radius:6px;transition:background-color .6s,color .6s}
.bg td.gia.up{background:color-mix(in srgb,var(--gain) 13%,transparent);color:var(--gain);transition:none}
.bg td.gia.dn{background:color-mix(in srgb,var(--loss) 13%,transparent);color:var(--loss);transition:none}
.bg td.ask{color:var(--ink2)}
.bg .sao{border:0;background:none;color:var(--mute);font-size:15px;cursor:pointer;padding:2px 4px;line-height:1;opacity:.5}
.bg .sao[aria-pressed=true]{color:#f5c518;opacity:1}.bg .sao:hover{opacity:1}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--gain);margin-right:6px;vertical-align:1px}.dot.nghi{background:var(--mute)}
.rg{min-width:130px}.rgb{position:relative;height:6px;border-radius:3px;background:linear-gradient(90deg,color-mix(in srgb,var(--loss) 55%,var(--track)),var(--track) 50%,color-mix(in srgb,var(--gain) 55%,var(--track)))}
.rgb i{position:absolute;top:-3px;width:3px;height:12px;border-radius:2px;background:var(--ink);transform:translateX(-50%)}
.rg small{display:flex;justify-content:space-between;font-size:11px;color:var(--mute);margin-top:3px}
.tia{width:110px;height:28px;display:block}.tia polyline{fill:none;stroke-width:1.5;stroke-linejoin:round}.tia.gain polyline{stroke:var(--gain)}.tia.loss polyline{stroke:var(--loss)}
.bg .hd a{font-size:12px;color:var(--ink2);text-decoration:none;border:1px solid var(--line);border-radius:8px;padding:4px 8px;margin-left:4px;white-space:nowrap}.bg .hd a:hover{color:var(--series);border-color:var(--series)}
.sm-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);gap:16px}@media(max-width:900px){.sm-grid{grid-template-columns:1fr}}
.sm-r{display:grid;grid-template-columns:46px minmax(0,1fr) 74px;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid var(--line)}.sm-r:last-child{border:0}
.sm-r b{font-size:14px}.sm-r em{font-style:normal;text-align:right;font-weight:600}.sm-r small{grid-column:2/4;font-size:11.5px;color:var(--mute);margin-top:-4px}
.sm-t{position:relative;height:14px;background:var(--track);border-radius:4px}.sm-t i{position:absolute;left:50%;top:-3px;bottom:-3px;width:1px;background:var(--mute)}
.sm-t span{position:absolute;top:0;bottom:0;border-radius:4px;transition:all .4s}
.sm-t span.gain{background:var(--gain)}.sm-t span.loss{background:var(--loss)}
.mx{border-collapse:separate;border-spacing:3px;width:100%;font-size:12px}.mx th{background:none!important;color:var(--ink2);font-weight:600;text-align:center;padding:4px}
.mx td{text-align:center;border-radius:6px;padding:8px 2px;font-weight:600;border:0;color:var(--ink)}.mx td.cheo{background:var(--track)}
.goi-y{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;font-size:13px;padding:10px 12px;border:1px dashed var(--line);border-radius:10px;margin-top:12px;color:var(--ink2)}
.goi-y b{color:var(--ink)}
.hm-nhom{margin-top:14px}.hm-nhom h3{margin:0 0 8px}
.hm-g{display:grid;grid-template-columns:repeat(auto-fill,minmax(118px,1fr));gap:6px}
.hm{display:block;border-radius:10px;padding:9px 10px;text-decoration:none;color:var(--ink);border:1px solid color-mix(in srgb,var(--line) 60%,transparent);min-height:66px;transition:transform .12s}
.hm:hover{transform:translateY(-1px);border-color:var(--ink2)}.hm b{display:block;font-size:13px}.hm em{display:block;font-style:normal;font-weight:700;font-size:15px}.hm small{display:block;font-size:11px;color:var(--ink2)}
.tq td,.tq th{text-align:center;padding:6px 4px!important;font-size:12px}.tq td{font-weight:600;min-width:46px}.tq th.hang{text-align:right!important;position:sticky;left:0;background:var(--card2);z-index:1}
.legend-bar{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--mute);margin-top:10px}.legend-bar span{flex:0 0 220px;height:8px;border-radius:4px;background:linear-gradient(90deg,var(--loss),var(--track),var(--gain))}
.ss{position:relative;margin-top:8px}
.ss-r{display:grid;grid-template-columns:150px minmax(0,1fr);gap:12px;align-items:center;padding:6px 0}
.ss-r>div:first-child b{display:block;font-size:13.5px}.ss-r>div:first-child small{font-size:11.5px;color:var(--mute)}
.ss-t{position:relative;height:26px;background:var(--track);border-radius:6px;overflow:hidden}
.ss-t span{position:absolute;top:0;bottom:0;border-radius:6px;background:color-mix(in srgb,var(--series) 30%,transparent);border:1px solid color-mix(in srgb,var(--series) 55%,transparent)}
.ss-t span.mo{background:color-mix(in srgb,var(--series) 55%,transparent)}
.ss-gio{display:grid;grid-template-columns:150px minmax(0,1fr);gap:12px;font-size:11px;color:var(--mute)}.ss-gio div:last-child{position:relative;height:16px}.ss-gio u{position:absolute;text-decoration:none;transform:translateX(-50%)}
.ss-now{position:absolute;top:0;bottom:16px;width:2px;background:var(--loss);z-index:2;pointer-events:none}.ss-now::after{content:attr(data-t);position:absolute;top:-18px;left:50%;transform:translateX(-50%);font-size:11px;font-weight:700;color:var(--loss);white-space:nowrap}
.ss-st{font-size:12px;font-weight:600}.ss-st.mo{color:var(--gain)}.ss-st.dong{color:var(--mute)}
.cal-ngay{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--series);font-weight:700;margin:14px 0 4px}
.cal-r{display:grid;grid-template-columns:62px 104px 60px 44px minmax(0,1fr) auto;gap:10px;align-items:center;padding:7px 4px;border-bottom:1px solid var(--line);font-size:13px}
.cal-r .so{font-size:12px;color:var(--ink2);white-space:nowrap;display:flex;gap:12px}.cal-r .so em{font-style:normal;color:var(--mute);margin-right:3px}
.badge.le{background:color-mix(in srgb,var(--warn) 14%,transparent);color:var(--warn);border-color:transparent}
#cal-tien button{min-height:28px;padding:0 10px;font-size:12px}
.cal-r.qua{opacity:.5}.cal-r.sap{background:color-mix(in srgb,var(--warn) 10%,transparent);border-radius:8px}
.cal-r .dg{font-size:11.5px;color:var(--mute)}
.imp{display:inline-flex;gap:2px}.imp i{width:7px;height:7px;border-radius:50%;background:var(--track)}.imp.m3 i{background:var(--loss)}.imp.m2 i:nth-child(-n+2){background:#e0a100}
.badge{display:inline-block;font-size:11px;font-weight:700;padding:2px 7px;border-radius:6px;background:var(--card2);border:1px solid var(--line);color:var(--ink)}
.spec td small{display:block;color:var(--mute);font-size:11px}
.off{color:var(--mute);text-decoration:line-through}
.sm-grid>*,.kt-g>*{min-width:0}
@media(max-width:760px){.tt-hero b a{display:inline-block;padding:3px 0}.bg .sao{padding:6px 7px;font-size:16px}}
@media(max-width:760px){.tt-tool input[type=search]{min-width:0;flex:1 1 100%}.tt-hero b{font-size:16px}.tt-hero b span{font-size:12px!important}.bg .rg,.bg .tia-c,.bg .c1,.bg .cw,.bg .ask{display:none}
.cal-r{grid-template-columns:52px 1fr 60px 40px;row-gap:2px}.cal-r .dg{grid-column:2}.cal-r .ten,.cal-r .so{grid-column:1/5}
.ss-r,.ss-gio{grid-template-columns:96px minmax(0,1fr)}}
/* tín hiệu kỹ thuật */
.kb{display:inline-block;min-width:76px;text-align:center;font-size:11.5px;font-weight:700;padding:4px 8px;border-radius:7px;white-space:nowrap;border:1px solid transparent}
.kb-mm{background:color-mix(in srgb,var(--gain) 26%,transparent);color:var(--gain);border-color:color-mix(in srgb,var(--gain) 45%,transparent)}
.kb-m{background:color-mix(in srgb,var(--gain) 11%,transparent);color:var(--gain)}
.kb-t{background:var(--card2);color:var(--mute);border-color:var(--line)}
.kb-b{background:color-mix(in srgb,var(--loss) 11%,transparent);color:var(--loss)}
.kb-bm{background:color-mix(in srgb,var(--loss) 26%,transparent);color:var(--loss);border-color:color-mix(in srgb,var(--loss) 45%,transparent)}
.kt-g{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(340px,1fr);gap:14px;align-items:start}@media(max-width:1060px){.kt-g{grid-template-columns:1fr}}
.kt-g .tt-wrap{max-height:calc(100vh - 220px)}
.kt tr[data-ma]{cursor:pointer}.kt tr.chon td{background:color-mix(in srgb,var(--series) 9%,transparent)}
.kt td.ma b{display:block}.kt td.ma small{color:var(--mute);font-size:11.5px}
.dt{display:inline-flex;gap:2px}.dt i{width:8px;height:14px;border-radius:2px;background:var(--track)}.dt i.m{background:var(--gain)}.dt i.b{background:var(--loss)}
.kt-ct{position:sticky;top:calc(var(--nv-h,56px) + 64px)}
.kt-hd{display:flex;justify-content:space-between;gap:10px;align-items:flex-start;flex-wrap:wrap}.kt-hd h2{font-size:18px}.kt-hd .lk a{font-size:12px;margin-left:6px}
.gauge3{display:grid;grid-template-columns:1.3fr 1fr 1fr;gap:6px;margin:10px 0 6px;text-align:center}
.gauge3 svg{width:100%;height:auto;display:block}.gauge3 b{display:block;font-size:14px;margin-top:-4px}.gauge3 small{display:block;font-size:11px;color:var(--mute)}
.gauge3 .lon b{font-size:17px}
.kt-bang{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px}@media(max-width:520px){.kt-bang{grid-template-columns:1fr}}
.kt-bang table{font-size:12px}.kt-bang td,.kt-bang th{padding:5px 8px!important}
.kt-bang h4{margin:0 0 6px;font-size:12px;color:var(--ink2);font-weight:600}
.p1{color:var(--gain);font-weight:600}.p-1{color:var(--loss);font-weight:600}.p0{color:var(--mute)}
/* biến động theo giờ */
.bd-cot{display:flex;align-items:flex-end;gap:3px;height:190px;padding:8px 0 0;border-bottom:1px solid var(--line)}
.bd-cot div{flex:1;position:relative;border-radius:4px 4px 0 0;background:color-mix(in srgb,var(--series) 38%,var(--card2));min-height:2px;transition:height .3s}
.bd-cot div.nay{background:var(--series)}.bd-cot div:hover{filter:brightness(1.25)}
.bd-cot div span{position:absolute;bottom:100%;left:50%;transform:translateX(-50%);font-size:10px;color:var(--mute);white-space:nowrap;margin-bottom:2px}
.bd-gio{display:flex;gap:3px;font-size:10.5px;color:var(--mute);margin-top:4px}.bd-gio span{flex:1;text-align:center}
.bd-thu{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-top:10px}
.bd-thu div{background:var(--card2);border:1px solid var(--line);border-radius:10px;padding:10px;text-align:center}.bd-thu b{display:block;font-size:16px}.bd-thu small{font-size:11.5px;color:var(--mute)}
.bd-thu div.max{border-color:var(--series)}
@media(max-width:760px){.bd-thu{gap:4px}.bd-thu div{padding:8px 3px;min-width:0}.bd-thu b{font-size:13px}.bd-thu small{font-size:10px;display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
/* cảnh báo giá */
.bg .hd button.chuong{border:1px solid var(--line);background:none;border-radius:8px;padding:3px 7px;cursor:pointer;color:var(--ink2);font-size:12px}
.bg .hd button.chuong.co{color:#f5c518;border-color:color-mix(in srgb,#f5c518 50%,var(--line))}
.cb-pop{position:fixed;z-index:40;width:290px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;box-shadow:0 20px 50px -12px rgba(0,0,0,.5)}
.cb-pop[hidden]{display:none}.cb-pop h4{margin:0 0 8px;font-size:14px}
.cb-pop label{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--mute);margin-bottom:8px}
.cb-pop input{min-height:36px;border:1px solid var(--line);border-radius:10px;background:var(--card2);color:var(--ink);padding:0 10px;font:inherit}
.cb-pop .hang{display:flex;gap:8px;justify-content:flex-end;margin-top:4px}
.cb-ds{margin-top:10px}.cb-r{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:8px 10px;border-bottom:1px solid var(--line);font-size:13px}
.cb-r:last-child{border:0}.cb-r small{display:block;color:var(--mute);font-size:11.5px}.cb-r.da{opacity:.55}
.cb-r button{border:1px solid var(--line);background:none;color:var(--ink2);border-radius:8px;padding:3px 8px;cursor:pointer;font-size:12px}
.toasts{position:fixed;right:16px;bottom:16px;z-index:70;display:flex;flex-direction:column;gap:8px;max-width:340px}
.toast{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--series);border-radius:12px;padding:11px 14px;box-shadow:0 14px 40px -10px rgba(0,0,0,.5);font-size:13px;animation:vao .2s}
.toast b{display:block;margin-bottom:2px}@keyframes vao{from{opacity:0;transform:translateY(8px)}}
.rr-bar{position:relative;height:8px;border-radius:4px;margin-top:8px;background:linear-gradient(90deg,var(--loss),var(--track) 50%,var(--gain))}
.rr-bar i{position:absolute;top:-4px;width:4px;height:16px;border-radius:2px;background:var(--ink);transform:translateX(-50%);transition:left .4s}
"""

# --------------------------------------------------------------------------- phần JS dùng chung (TT)
JS_CHUNG = r"""
window.TT=(()=>{const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const NF={},fmt=(v,d)=>{if(v==null||!isFinite(v))return'—';d=Math.max(0,Math.min(8,d??2));return(NF[d]||(NF[d]=new Intl.NumberFormat('vi-VN',{minimumFractionDigits:d,maximumFractionDigits:d}))).format(v)};
const pct=(v,d=2)=>v==null||!isFinite(v)?'—':(v>0?'+':v<0?'−':'')+fmt(Math.abs(v),d)+'%',cls=v=>v>0?'gain':v<0?'loss':'';
const CHINH=['USD','EUR','GBP','JPY','CHF','CAD','AUD','NZD'],LOPS=['fx_chinh','fx_cheo','fx_ngoai_lai','kim_loai','nang_luong','chi_so','crypto','khac'];
const KY={'1h':'1 giờ','4h':'4 giờ','ngay':'Hôm nay','tuan':'Tuần này','thang':'Tháng này'};
let S=null,by=new Map(),subs=[],lan=0,lanTai=0,es=null,tt={ok:false,ly:'đang nối với webapp…'};
const phat=(l,d)=>{for(const f of subs)try{f(l,d)}catch(e){console.error(e)}};
const doi=(x,k)=>{const q=x&&x.q,r=x&&x.ref&&x.ref[k];return q&&r?(q[0]/r-1)*100:null};
const maxT=()=>{let m=0;for(const x of by.values())if(x.q&&x.q[2]>m)m=x.q[2];return m};
const nghi=x=>!x.q||maxT()-x.q[2]>5*60000;
const spread=x=>{if(!x.q)return null;const s=x.q[1]-x.q[0];return x.pip?{v:s/x.pip,dv:'pip',d:1}:{v:s/x.diem,dv:'điểm',d:0}};
const spTxt=x=>{const s=spread(x);return s?fmt(s.v,s.d)+' '+s.dv:'—'};
const bien=x=>{const h=x.hom_nay;if(!h||!x.q)return null;const b=x.q[0],lo=Math.min(h.thap,b),hi=Math.max(h.cao,b),r=hi-lo;return{lo,hi,vt:r>0?(b-lo)/r:.5,adr:x.adr?r/x.adr*100:null}};
function sucManh(k){const s={},n={};for(const c of CHINH){s[c]=0;n[c]=0}
 for(const x of by.values()){if(!x.cap)continue;const[a,b]=x.cap;if(!(a in s&&b in s))continue;const v=doi(x,k);if(v==null)continue;s[a]+=v;n[a]++;s[b]-=v;n[b]++}
 return CHINH.map(c=>({c,v:n[c]?s[c]/n[c]:null,n:n[c]})).sort((p,q)=>(q.v??-1e9)-(p.v??-1e9))}
function capTien(a,b){for(const x of by.values()){if(!x.cap)continue;if(x.cap[0]===a&&x.cap[1]===b)return{x,dao:false};if(x.cap[0]===b&&x.cap[1]===a)return{x,dao:true}}return null}
async function tai(){const r=await fetch('/api/thi-truong',{cache:'no-store'});if(!r.ok)throw new Error(await r.text());const j=await r.json(),cu=by;S=j;by=new Map();
 for(const x of j.ds){const o=cu.get(x.ma);if(o&&o.q&&(!x.q||o.q[2]>x.q[2]))x.q=o.q;by.set(x.ma,x)}tt={ok:j.san_sang,ly:j.ly_do};if(!lan&&j.san_sang)lan=Date.now();phat('anh');return j}
// Luồng giá DÙNG CHUNG cho mọi tab của webapp. Trình duyệt chỉ cho mỗi máy chủ 6 kết nối cùng lúc; nếu mỗi tab Thị trường/Công cụ giữ
// một luồng thì mở tới tab thứ 7 là cả webapp treo (đo ngày 25/11/2026: tab thứ 7 chờ hơn 5 phút không tải được trang). Nên chỉ một tab
// "trưởng" (giữ khóa Web Locks) mở ĐÚNG MỘT kết nối và chuyển từng gói giá cho các tab khác qua BroadcastChannel, kể cả tab đang ẩn
// (cảnh báo giá vẫn chạy). Tab trưởng đóng thì khóa nhả và một tab khác tự lên thay. Trình duyệt thiếu hai API này: mỗi tab tự mở luồng.
function nhanGia(j){const ds=[];let la=0;for(const m in j.q){const x=by.get(m);if(!x){la++;continue}x.q0=x.q;x.q=j.q[m];ds.push(m)}
 if(la&&Date.now()-lanTai>3000){lanTai=Date.now();tai().catch(()=>{})}                  // có mã bảng chưa biết (bộ máy vừa sẵn sàng, hoặc sàn thêm mã): nạp lại bảng
 if(ds.length)lan=Date.now();tt={ok:j.s,ly:j.ly};phat('gia',ds)}
function moLuong(bc){es=new EventSource('/api/thi-truong/luong');
 es.addEventListener('gia',e=>{let j;try{j=JSON.parse(e.data)}catch(_){return}nhanGia(j);if(bc)bc.postMessage({t:'gia',j})});
 es.onerror=()=>{tt={ok:false,ly:'mất kết nối với webapp, đang nối lại…'};phat('trang_thai');if(bc)bc.postMessage({t:'loi'})}}
function noi(){if(es)return;if(!window.EventSource){setInterval(()=>tai().catch(()=>{}),3000);return}
 if(!window.BroadcastChannel||!(navigator.locks&&navigator.locks.request)){moLuong(null);return}
 es=-1;const bc=new BroadcastChannel('so-cong-khai-gia');
 bc.onmessage=e=>{const m=e.data||{};if(m.t==='gia')nhanGia(m.j);else if(m.t==='loi'){tt={ok:false,ly:'mất kết nối với webapp, đang nối lại…'};phat('trang_thai')}};
 navigator.locks.request('so-cong-khai-luong-gia',()=>new Promise(()=>moLuong(bc)))}                    // giữ khóa tới khi tab đóng
function batDau(moiGiay=30){const lam=()=>tai().catch(e=>{tt={ok:false,ly:'không đọc được bảng giá: '+e.message};phat('trang_thai')});
 const p=lam();noi();setInterval(()=>{if(document.visibilityState==='visible')lam()},moiGiay*1000);return p}
function pill(el){const ve=()=>{if(!el)return;const n=[...by.values()].filter(x=>x.q).length,giay=lan?Math.round((Date.now()-lan)/1000):null;
 el.className='song-pill '+(tt.ok?'ok':'loi');
 el.innerHTML=tt.ok?`<i></i><b>Trực tiếp</b> · ${n} mã · ${giay==null?'chờ giá':giay<3?'vừa cập nhật':giay<90?'cập nhật '+giay+' giây trước':'thị trường đang tĩnh'}`:`<i></i><b>Chưa có giá trực tiếp</b> · ${esc(tt.ly||'')}`};
 subs.push(ve);setInterval(ve,1000);ve()}
const gioVN=ms=>new Date(ms).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',second:'2-digit',day:'2-digit',month:'2-digit'});
const tia=(a,b,w=110,h=28)=>{const v=(a||[]).concat(b!=null?[b]:[]).filter(x=>x!=null);if(v.length<2)return'';const lo=Math.min(...v),hi=Math.max(...v),sp=(hi-lo)||1;
 return `<svg class="tia ${v[v.length-1]>=v[0]?'gain':'loss'}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true"><polyline points="${v.map((x,i)=>(i/(v.length-1)*w).toFixed(1)+','+(h-3-(x-lo)/sp*(h-6)).toFixed(1)).join(' ')}"/></svg>`};
const tenMa=x=>x.biet_danh?x.biet_danh+' · '+x.ten:x.ten;
const nhomOpt=(chon)=>{const g={};for(const x of by.values())(g[x.lop]=g[x.lop]||[]).push(x);
 return LOPS.filter(l=>g[l]).map(l=>`<optgroup label="${esc(S.lop[l])}">`+g[l].sort((a,b)=>a.goc.localeCompare(b.goc)).map(x=>`<option value="${esc(x.ma)}"${x.ma===chon?' selected':''}>${esc(x.goc)}${x.biet_danh?' · '+esc(x.biet_danh):''}</option>`).join('')+'</optgroup>').join('')};
// ---- nhãn tổng hợp kỹ thuật (cùng ngưỡng với thi_truong.nhan_kt)
const nhan=x=>x==null?'—':x>.5?'Mua mạnh':x>.1?'Mua':x>=-.1?'Trung tính':x>=-.5?'Bán':'Bán mạnh';
const kbc=x=>x==null?'kb-t':x>.5?'kb-mm':x>.1?'kb-m':x>=-.1?'kb-t':x>=-.5?'kb-b':'kb-bm';
const kb=x=>`<span class="kb ${kbc(x)}">${nhan(x)}</span>`;
// ---- khẩu vị rủi ro: thay đổi hôm nay của rổ tài sản rủi ro (chỉ số, AUDJPY, NZDJPY, BTC) trừ rổ trú ẩn (vàng, CHF, JPY),
//      mỗi mã chia cho biên độ trung bình ngày của chính nó để so được với nhau. Điểm −1..1. Chỉ mô tả, không dự báo.
const RR={len:['US500','USTEC','US30','GER30','JAPAN','AUS200','AUDJPY','NZDJPY','BTCUSDT']};
function khauVi(){const theo={};for(const x of by.values())theo[x.goc]=x;const v=[];
 const lay=(g,dau)=>{const x=theo[g];if(!x||!x.q||!x.ref||!x.ref.ngay||!x.adr)return;const ch=(x.q[0]-x.ref.ngay)/x.adr;if(isFinite(ch))v.push(Math.max(-2,Math.min(2,ch))*dau)};
 RR.len.forEach(g=>lay(g,1));lay('XAUUSD',-1);lay('USDJPY',1);lay('USDCHF',1);
 if(v.length<4)return null;const d=v.reduce((a,b)=>a+b,0)/v.length/1.2;return{d:Math.max(-1,Math.min(1,d)),n:v.length}}
// ---- thông báo nổi và âm thanh
let khay=null;function toast(t,nd){if(!khay){khay=document.createElement('div');khay.className='toasts';khay.setAttribute('aria-live','polite');document.body.appendChild(khay)}
 const e=document.createElement('div');e.className='toast';e.innerHTML=`<b>${esc(t)}</b>${esc(nd||'')}`;khay.appendChild(e);setTimeout(()=>e.remove(),9000)}
function bip(){try{const A=window.AudioContext||window.webkitAudioContext,a=new A(),o=a.createOscillator(),g=a.createGain();o.frequency.value=880;g.gain.value=.08;o.connect(g);g.connect(a.destination);o.start();
 g.gain.exponentialRampToValueAtTime(.0001,a.currentTime+.35);o.stop(a.currentTime+.36)}catch(e){}}
// ---- cảnh báo giá: lưu trong trình duyệt; kiểm ở mỗi tick khi có trang Thị trường hoặc Công cụ đang mở
const CB={ds(){try{return JSON.parse(localStorage.getItem('tt-canh')||'[]')}catch(e){return[]}},luu(a){try{localStorage.setItem('tt-canh',JSON.stringify(a))}catch(e){}phat('canh')},
 them(ma,muc,ghi){const x=by.get(ma);if(!x||!x.q||!(muc>0))return null;const a=CB.ds(),c={id:Date.now().toString(36),ma,goc:x.goc,muc,huong:muc>=x.q[0]?'tren':'duoi',ghi:ghi||'',luc:Date.now(),da:null};
  a.push(c);CB.luu(a);if(window.Notification&&Notification.permission==='default')try{Notification.requestPermission()}catch(e){}return c},
 xoa(id){CB.luu(CB.ds().filter(c=>c.id!==id))},xoaDa(){CB.luu(CB.ds().filter(c=>!c.da))}};
subs.push((l,ds)=>{if(l!=='gia'||!ds||!ds.length)return;const a=CB.ds();let doi=0;
 for(const c of a){if(c.da||!ds.includes(c.ma))continue;const x=by.get(c.ma);if(!x||!x.q)continue;const b=x.q[0];
  if((c.huong==='tren'&&b>=c.muc)||(c.huong==='duoi'&&b<=c.muc)){c.da=Date.now();doi=1;const t=`${c.goc} ${c.huong==='tren'?'lên tới':'xuống tới'} ${fmt(c.muc,x.so_le)}`,nd=`Giá lúc này ${fmt(b,x.so_le)}.${c.ghi?' '+c.ghi:''}`;
   toast(t,nd);bip();if(window.Notification&&Notification.permission==='granted')try{new Notification(t,{body:nd,tag:'tt-'+c.id})}catch(e){}}}
 if(doi)CB.luu(a)});
return{esc,fmt,pct,cls,CHINH,LOPS,KY,doi,maxT,nghi,spread,spTxt,bien,sucManh,capTien,tai,noi,batDau,pill,gioVN,tia,tenMa,nhomOpt,nhan,kbc,kb,khauVi,toast,CB,
 on:f=>subs.push(f),by:()=>by,get S(){return S},get tt(){return tt}}})();
"""

# --------------------------------------------------------------------------- trang Thị trường
JS = r"""
(()=>{const T=TT,$=s=>document.querySelector(s),esc=T.esc,fmt=T.fmt,pct=T.pct,cls=T.cls;
let tab=(location.hash||'').slice(1),loc='tat',tim='',sx={k:'',d:-1},ky='ngay',kyHm='ngay',calCao=false,spLoc='tat',spTim='';
let sao=new Set();try{sao=new Set(JSON.parse(localStorage.getItem('tt-sao')||'[]'))}catch(e){}
try{const k=localStorage.getItem('tt-ky');if(k)ky=kyHm=k}catch(e){}
const TABS=['bang-gia','ky-thuat','suc-manh','ban-do-nhiet','tuong-quan','bien-dong','phien','thong-so'];if(!TABS.includes(tab))tab='bang-gia';
const luuSao=()=>{try{localStorage.setItem('tt-sao',JSON.stringify([...sao]))}catch(e){}};
T.pill($('#song'));
// ---- thẻ
function moTab(t){tab=t;document.querySelectorAll('#tt-tabs button').forEach(b=>b.setAttribute('aria-selected',b.dataset.t===t));
 document.querySelectorAll('.tt-p').forEach(p=>p.hidden=p.dataset.p!==t);try{history.replaceState(null,'','#'+t)}catch(e){}ve(1)}
$('#tt-tabs').addEventListener('click',e=>{const b=e.target.closest('button[data-t]');if(b)moTab(b.dataset.t)});
addEventListener('hashchange',()=>{const t=location.hash.slice(1);if(TABS.includes(t)&&t!==tab)moTab(t)});
// ---- tổng quan nhanh
function hero(){const ds=[...T.by().values()].filter(x=>x.q&&x.ref),ch=ds.map(x=>({x,v:T.doi(x,'ngay')})).filter(a=>a.v!=null);
 const len=ch.filter(a=>a.v>0).length,xuong=ch.filter(a=>a.v<0).length,sm=T.sucManh('ngay').filter(a=>a.v!=null);
 const top=ch.slice().sort((a,b)=>b.v-a.v),vol=ds.map(x=>({x,b:T.bien(x)})).filter(a=>a.b&&a.b.adr!=null).sort((a,b)=>b.b.adr-a.b.adr);
 const o=(t,b,s)=>`<div><span>${t}</span><b>${b}</b><small>${s}</small></div>`;const ma=a=>a?`<a href="/bieu-do?ma=${encodeURIComponent(a.x.ma)}" style="color:inherit;text-decoration:none">${esc(a.x.goc)}</a>`:'—';
 $('#tt-hero').innerHTML=o('Độ rộng thị trường hôm nay',`<span class="gain">${len}</span> tăng · <span class="loss">${xuong}</span> giảm`,`<div class="breadth"><u style="width:${ch.length?len/ch.length*100:0}%"></u><span style="flex:1"></span><s style="width:${ch.length?xuong/ch.length*100:0}%"></s></div>`)
 +o('Tiền tệ mạnh nhất',sm.length?`${sm[0].c} <span class="gain" style="font-size:14px">${pct(sm[0].v)}</span>`:'—',sm.length?'yếu nhất: '+sm[sm.length-1].c+' '+pct(sm[sm.length-1].v):'')
 +o('Tăng mạnh nhất',top.length?`${ma(top[0])} <span class="gain" style="font-size:14px">${pct(top[0].v)}</span>`:'—',top.length?esc(T.tenMa(top[0].x)):'')
 +o('Giảm mạnh nhất',top.length?`${ma(top[top.length-1])} <span class="loss" style="font-size:14px">${pct(top[top.length-1].v)}</span>`:'—',top.length?esc(T.tenMa(top[top.length-1].x)):'')
 +(()=>{const k=T.khauVi();if(!k)return o('Khẩu vị rủi ro','—','chưa đủ dữ liệu');const n=k.d>.25?['Ưa rủi ro','gain']:k.d<-.25?['Né rủi ro','loss']:['Trung tính',''];
   return `<div title="Chỉ số, AUDJPY, NZDJPY, BTC so với vàng, JPY, CHF hôm nay (${k.n} mã, quy theo biên độ ngày của từng mã). Chỉ mô tả, không dự báo."><span>Khẩu vị rủi ro hôm nay</span><b class="${n[1]}">${n[0]}</b><div class="rr-bar"><i style="left:${(50+k.d*50).toFixed(1)}%"></i></div></div>`})()
 +o('Phiên đang mở',PH.dangMo().join(' + ')||'Không phiên chính nào',PH.ghiChu())}
// ---- bảng giá
const O=new Map();
function locDs(){const q=tim.trim().toLowerCase();return[...T.by().values()].filter(x=>(loc==='tat'||(loc==='sao'?sao.has(x.ma):x.lop===loc))&&(!q||(x.ma+' '+x.goc+' '+x.ten+' '+(x.biet_danh||'')).toLowerCase().includes(q)))}
function khoa(x,k){switch(k){case'ten':return x.goc;case'1h':return T.doi(x,'1h');case'ngay':return T.doi(x,'ngay');case'tuan':return T.doi(x,'tuan');
 case'spread':return x.q?(x.q[1]-x.q[0])/x.q[0]:null;case'adr':{const b=T.bien(x);return b&&b.adr}}return null}
function chips(){const dem={tat:T.by().size,sao:[...T.by().keys()].filter(m=>sao.has(m)).length};for(const x of T.by().values())dem[x.lop]=(dem[x.lop]||0)+1;
 const ds=[['tat','Tất cả'],['sao','★ Theo dõi']].concat(T.LOPS.filter(l=>dem[l]).map(l=>[l,T.S.lop[l]]));
 $('#bg-loc').innerHTML=ds.map(([k,n])=>`<button type="button" data-l="${k}" aria-pressed="${k===loc}">${esc(n)}<small>${dem[k]||0}</small></button>`).join('')}
function dongHtml(x){const b=T.bien(x),n=T.nghi(x);return`<tr data-ma="${esc(x.ma)}"><td><button type="button" class="sao" aria-pressed="${sao.has(x.ma)}" title="Thêm vào danh sách theo dõi">★</button></td>
 <td class="ma"><span class="dot${n?' nghi':''}" title="${n?'Không có giá mới hơn 5 phút: thị trường của mã này đang nghỉ':'Đang có giá'}"></span><a href="/bieu-do?ma=${encodeURIComponent(x.ma)}">${esc(x.goc)}</a><small>${esc(T.tenMa(x))}</small></td>
 <td class="r gia">${x.q?fmt(x.q[0],x.so_le):'—'}</td><td class="r ask">${x.q?fmt(x.q[1],x.so_le):'—'}</td><td class="r sp">${T.spTxt(x)}</td>
 <td class="r c1"></td><td class="r cd"></td><td class="r cw"></td>
 <td class="rg">${b?`<div class="rgb"><i style="left:${(b.vt*100).toFixed(1)}%"></i></div><small><span>${fmt(b.lo,x.so_le)}</span><span>${b.adr!=null?fmt(b.adr,0)+'% ADR':''}</span><span>${fmt(b.hi,x.so_le)}</span></small>`:''}</td>
 <td class="tia-c">${T.tia(x.tia,x.q&&x.q[0])}</td><td class="hd"><button type="button" class="chuong${coCB.has(x.ma)?' co':''}" title="Đặt cảnh báo giá" aria-label="Đặt cảnh báo giá ${esc(x.goc)}">🔔</button><a href="/cong-cu?ma=${encodeURIComponent(x.ma)}">Tính</a></td></tr>`}
function oCap(x,o,nhay){if(!o)return;const q=x.q;if(q){o.gia.textContent=fmt(q[0],x.so_le);o.ask.textContent=fmt(q[1],x.so_le);o.sp.textContent=T.spTxt(x);
  if(nhay&&x.q0&&x.q0[0]!==q[0]){o.gia.classList.remove('up','dn');void o.gia.offsetWidth;o.gia.classList.add(q[0]>x.q0[0]?'up':'dn');clearTimeout(o.tm);o.tm=setTimeout(()=>o.gia.classList.remove('up','dn'),450)}}
 for(const[k,el]of[['1h',o.c1],['ngay',o.cd],['tuan',o.cw]]){const v=T.doi(x,k);el.textContent=pct(v);el.className='r '+el.dataset.c+' '+cls(v)}
 const b=T.bien(x);if(b&&o.rgi)o.rgi.style.left=(b.vt*100).toFixed(1)+'%';const n=T.nghi(x);o.dot.classList.toggle('nghi',n)}
function bangGia(){chips();const ds=locDs(),body=$('#bg-body');O.clear();
 document.querySelectorAll('#bg th[data-k]').forEach(th=>th.setAttribute('aria-sort',th.dataset.k===sx.k?(sx.d>0?'ascending':'descending'):'none'));
 let h='';if(sx.k){ds.sort((a,b)=>{const p=khoa(a,sx.k),q=khoa(b,sx.k);if(p==null)return 1;if(q==null)return-1;return(typeof p==='string'?p.localeCompare(q):p-q)*sx.d});h=ds.map(dongHtml).join('')}
 else{for(const l of T.LOPS){const g=ds.filter(x=>x.lop===l).sort((a,b)=>a.goc.localeCompare(b.goc));if(!g.length)continue;h+=`<tr class="nhom"><th colspan="11">${esc(T.S.lop[l])} · ${g.length} mã</th></tr>`+g.map(dongHtml).join('')}}
 body.innerHTML=h||`<tr><td colspan="11" class="small" style="padding:18px">${loc==='sao'?'Chưa có mã nào trong danh sách theo dõi: bấm ★ ở đầu dòng để thêm.':'Không có mã nào khớp.'}</td></tr>`;
 body.querySelectorAll('tr[data-ma]').forEach(tr=>{const td=tr.children,o={gia:td[2],ask:td[3],sp:td[4],c1:td[5],cd:td[6],cw:td[7],rgi:td[8].querySelector('i'),dot:td[1].querySelector('.dot')};
  o.c1.dataset.c='c1';o.cd.dataset.c='cd';o.cw.dataset.c='cw';O.set(tr.dataset.ma,o);oCap(T.by().get(tr.dataset.ma),o,0)})}
$('#bg-loc').addEventListener('click',e=>{const b=e.target.closest('button[data-l]');if(!b)return;loc=b.dataset.l;bangGia()});
$('#bg-tim').addEventListener('input',e=>{tim=e.target.value;bangGia()});
$('#bg thead').addEventListener('click',e=>{const th=e.target.closest('th[data-k]');if(!th)return;const k=th.dataset.k;sx=sx.k===k?(sx.d<0?{k,d:1}:{k:'',d:-1}):{k,d:k==='ten'?1:-1};bangGia()});
// ---- cảnh báo giá
let coCB=new Set();const capCB=()=>{const ds=T.CB.ds(),con=ds.filter(c=>!c.da);coCB=new Set(con.map(c=>c.ma));$('#cb-n').textContent=con.length;
 document.querySelectorAll('#bg-body tr[data-ma]').forEach(tr=>{const b=tr.querySelector('.chuong');if(b)b.classList.toggle('co',coCB.has(tr.dataset.ma))});
 const el=$('#cb-ds');if(!el)return;el.innerHTML=ds.length?ds.slice().sort((a,b)=>(!!a.da-!!b.da)||b.luc-a.luc).map(c=>{const x=T.by().get(c.ma),d=x?x.so_le:5;
  return`<div class="cb-r${c.da?' da':''}"><span><b>${esc(c.goc)}</b> ${c.huong==='tren'?'lên tới':'xuống tới'} <b>${fmt(c.muc,d)}</b><small>${c.da?'Đã báo lúc '+T.gioVN(c.da):'Đang chờ · giá hiện tại '+(x&&x.q?fmt(x.q[0],d):'—')}${c.ghi?' · '+esc(c.ghi):''}</small></span><button type="button" data-xoa="${c.id}">Xóa</button></div>`}).join('')
  +(ds.some(c=>c.da)?'<p class="small"><button type="button" class="ghost nho" id="cb-xoa-da">Xóa các cảnh báo đã báo</button></p>':''):'<p class="small">Chưa có cảnh báo nào. Bấm 🔔 ở cuối một dòng trong bảng giá để đặt.</p>'};
const POP=$('#cb-pop');let popMa=null;
function moPop(ma,nut){const x=T.by().get(ma);if(!x||!x.q)return;popMa=ma;$('#cb-ten').textContent='Cảnh báo giá '+x.goc;const ip=$('#cb-muc');ip.value=x.q[0].toFixed(x.so_le);ip.step=x.diem;$('#cb-ghi').value='';
 $('#cb-hien').textContent='Giá hiện tại '+fmt(x.q[0],x.so_le)+'. Trang báo khi giá Bid chạm mức bạn nhập (lên hoặc xuống tùy mức đó nằm trên hay dưới giá hiện tại).';
 POP.hidden=false;const r=nut.getBoundingClientRect();POP.style.left=Math.max(8,Math.min(innerWidth-300,r.right-290))+'px';POP.style.top=Math.min(innerHeight-POP.offsetHeight-8,r.bottom+6)+'px';ip.focus();ip.select()}
$('#cb-luu').addEventListener('click',()=>{const v=parseFloat(String($('#cb-muc').value).replace(',','.'));const c=T.CB.them(popMa,v,$('#cb-ghi').value.trim());
 if(c){POP.hidden=true;T.toast('Đã đặt cảnh báo',`${c.goc} ${c.huong==='tren'?'lên tới':'xuống tới'} ${$('#cb-muc').value}. Trang Thị trường hoặc Công cụ phải đang mở để nhận báo.`)}});
$('#cb-huy').addEventListener('click',()=>{POP.hidden=true});
$('#cb-muc').addEventListener('keydown',e=>{if(e.key==='Enter')$('#cb-luu').click();if(e.key==='Escape')POP.hidden=true});
document.addEventListener('click',e=>{if(!POP.hidden&&!e.target.closest('#cb-pop')&&!e.target.closest('.chuong'))POP.hidden=true});
$('#cb-mo').addEventListener('click',()=>{const p=$('#cb-panel');p.hidden=!p.hidden;$('#cb-mo').setAttribute('aria-expanded',!p.hidden);capCB()});
$('#cb-panel').addEventListener('click',e=>{const b=e.target.closest('[data-xoa]');if(b){T.CB.xoa(b.dataset.xoa);return}if(e.target.closest('#cb-xoa-da'))T.CB.xoaDa()});
T.on(l=>{if(l==='canh')capCB()});
$('#bg-body').addEventListener('click',e=>{const c=e.target.closest('.chuong');if(c){e.stopPropagation();moPop(c.closest('tr').dataset.ma,c);return}});
$('#bg-body').addEventListener('click',e=>{const b=e.target.closest('.sao');if(!b)return;const m=b.closest('tr').dataset.ma;sao.has(m)?sao.delete(m):sao.add(m);luuSao();b.setAttribute('aria-pressed',sao.has(m));if(loc==='sao')bangGia();else chips()});
// ---- sức mạnh tiền tệ
function sucManh(){const sm=T.sucManh(ky),mx=Math.max(.05,...sm.map(a=>Math.abs(a.v||0)));
 $('#sm-ky').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.k===ky));
 $('#sm-bar').innerHTML=sm.map(a=>{const w=a.v==null?0:Math.abs(a.v)/mx*50,inf=T.S.tien_te[a.c]||{};return`<div class="sm-r"><b>${a.c}</b><div class="sm-t"><i></i><span class="${cls(a.v)}" style="${a.v>=0?'left:50%':'left:'+(50-w)+'%'};width:${w}%"></span></div><em class="${cls(a.v)}">${pct(a.v)}</em><small>${esc(inf.ten||'')} · ${esc(inf.nh||'')} · ${a.n} cặp</small></div>`}).join('');
 let h='<table class="mx"><thead><tr><th></th>'+T.CHINH.map(c=>`<th>${c}</th>`).join('')+'</tr></thead><tbody>';
 const mxv=[];for(const a of T.CHINH)for(const b of T.CHINH){if(a===b)continue;const p=T.capTien(a,b);if(p){const v=T.doi(p.x,ky);if(v!=null)mxv.push(Math.abs(v))}}const cap=Math.max(.05,...mxv);
 for(const a of T.CHINH){h+=`<tr><th>${a}</th>`;for(const b of T.CHINH){if(a===b){h+='<td class="cheo"></td>';continue}const p=T.capTien(a,b);let v=p?T.doi(p.x,ky):null;if(v!=null&&p.dao)v=-v;
  const m=v==null?0:Math.min(1,Math.abs(v)/cap)*70;h+=`<td title="${a}/${b}: ${pct(v)}${p&&p.dao?' (đảo từ '+p.x.goc+')':''}" style="background:color-mix(in srgb,var(--${v>=0?'gain':'loss'}) ${m.toFixed(0)}%,var(--card2))">${v==null?'—':pct(v,2).replace('%','')}</td>`}h+='</tr>'}
 $('#sm-mx').innerHTML=h+'</tbody></table>';
 const co=sm.filter(a=>a.v!=null);if(co.length>1){const m=co[0],y=co[co.length-1],p=T.capTien(m.c,y.c);
  $('#sm-goi').innerHTML=`<span>Mạnh nhất <b class="gain">${m.c}</b> · yếu nhất <b class="loss">${y.c}</b> (${esc(T.KY[ky].toLowerCase())})</span>`+(p?`<span>Cặp ghép hai đồng: <a href="/bieu-do?ma=${encodeURIComponent(p.x.ma)}"><b>${esc(p.x.goc)}</b></a> ${pct((p.dao?-1:1)*T.doi(p.x,ky))} theo chiều ${m.c}/${y.c}</span>`:'')+'<span class="small" style="margin:0">Chỉ mô tả chuyển động đã xảy ra, không phải tín hiệu vào lệnh.</span>'}}
$('#sm-ky').addEventListener('click',e=>{const b=e.target.closest('button[data-k]');if(!b)return;ky=b.dataset.k;try{localStorage.setItem('tt-ky',ky)}catch(_){}sucManh()});
// ---- bản đồ nhiệt
function banDo(){$('#hm-ky').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.k===kyHm));
 const ds=[...T.by().values()],v=ds.map(x=>Math.abs(T.doi(x,kyHm)||0)).sort((a,b)=>a-b),cap=Math.max(.1,v[Math.floor(v.length*.9)]||.1);let h='';
 for(const l of T.LOPS){const g=ds.filter(x=>x.lop===l).map(x=>({x,v:T.doi(x,kyHm)})).sort((a,b)=>(b.v??-1e9)-(a.v??-1e9));if(!g.length)continue;
  h+=`<div class="hm-nhom"><h3>${esc(T.S.lop[l])}</h3><div class="hm-g">`+g.map(({x,v})=>{const m=v==null?0:Math.min(1,Math.abs(v)/cap)*75;
   return`<a class="hm" href="/bieu-do?ma=${encodeURIComponent(x.ma)}" title="${esc(T.tenMa(x))}" style="background:color-mix(in srgb,var(--${v>=0?'gain':'loss'}) ${m.toFixed(0)}%,var(--card2))"><b>${esc(x.goc)}</b><em>${pct(v)}</em><small>${x.q?fmt(x.q[0],x.so_le):'—'}</small></a>`}).join('')+'</div></div>'}
 $('#hm').innerHTML=h}
$('#hm-ky').addEventListener('click',e=>{const b=e.target.closest('button[data-k]');if(!b)return;kyHm=b.dataset.k;banDo()});
// ---- tương quan
function tuongQuan(){const q=T.S&&T.S.tuong_quan,el=$('#tq');if(!q){el.innerHTML='<p class="small">Đang tính tương quan (lần đầu cần đọc 240 nến H1 của từng mã)…</p>';return}
 if(q.loi){el.innerHTML=`<p class="small">Chưa tính được: ${esc(q.loi)}</p>`;return}
 let h='<div class="tt-wrap" style="max-height:none"><table class="tq"><thead><tr><th></th>'+q.goc.map(g=>`<th>${esc(g)}</th>`).join('')+'</tr></thead><tbody>';
 q.ma_tran.forEach((r,i)=>{h+=`<tr><th class="hang">${esc(q.goc[i])}</th>`+r.map((v,j)=>{if(i===j)return'<td style="background:var(--track)">1</td>';const m=v==null?0:Math.abs(v)*80;
  const nx=v==null?'':Math.abs(v)>=.7?(v>0?'đi cùng chiều mạnh':'đi ngược chiều mạnh'):Math.abs(v)>=.4?(v>0?'cùng chiều vừa':'ngược chiều vừa'):'gần như độc lập';
  return`<td title="${esc(q.goc[i])} và ${esc(q.goc[j])}: ${v==null?'—':fmt(v,2)} · ${nx}" style="background:color-mix(in srgb,var(--${v>=0?'gain':'loss'}) ${m.toFixed(0)}%,var(--card2))">${v==null?'—':fmt(v,2)}</td>`}).join('')+'</tr>'});
 el.innerHTML=h+`</tbody></table></div><div class="legend-bar">−1 ngược chiều<span></span>+1 cùng chiều</div><p class="small">Tương quan Pearson của lợi suất từng giờ trên ${q.so_nen} nến ${esc(q.khung)} gần nhất (chỉ những giờ mọi mã cùng có giá), tính lúc ${T.gioVN(Date.parse(q.luc))}. Dùng để tránh mở nhiều lệnh thực chất là một (ví dụ mua EURUSD và mua GBPUSD cùng lúc) và để thấy mã nào đi ngược nhau. Tương quan thay đổi theo thời gian.</p>`}
// ---- phiên giao dịch (múi giờ thật của từng thành phố, tự tính giờ mùa hè)
const PH=(()=>{const DS=[{k:'Sydney',tz:'Australia/Sydney',a:7,b:16,m:'AUD, NZD'},{k:'Tokyo',tz:'Asia/Tokyo',a:9,b:18,m:'JPY, AUD, NZD'},{k:'London',tz:'Europe/London',a:8,b:17,m:'EUR, GBP, CHF, vàng, DAX'},{k:'New York',tz:'America/New_York',a:8,b:17,m:'USD, CAD, dầu, chỉ số Mỹ'}];
 const F={};const lech=(tz,ms)=>{const f=F[tz]||(F[tz]=new Intl.DateTimeFormat('en-US',{timeZone:tz,hourCycle:'h23',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}));
  const p={};for(const x of f.formatToParts(ms))p[x.type]=x.value;return Date.UTC(+p.year,+p.month-1,+p.day,+p.hour%24,+p.minute,+p.second)-Math.floor(ms/1000)*1000};
 const moc=(tz,y,m,d,h)=>{let g=Date.UTC(y,m,d,h);g-=lech(tz,g);return g-(lech(tz,g)-lech(tz,g+0))};
 const ngayTz=(tz,ms)=>{const p={};for(const x of new Intl.DateTimeFormat('en-US',{timeZone:tz,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(ms))p[x.type]=x.value;return[+p.year,+p.month-1,+p.day]};
 const khoang=(s,ms)=>{const out=[];for(const dd of[-1,0,1]){const[y,m,d]=ngayTz(s.tz,ms+dd*864e5);const a=moc(s.tz,y,m,d,s.a),b=moc(s.tz,y,m,d,s.b);const wd=new Date(Date.UTC(y,m,d)).getUTCDay();if(wd===0||wd===6)continue;out.push([a,b])}return out};
 const cuoiTuan=ms=>{const[y,m,d]=ngayTz('America/New_York',ms),wd=new Date(Date.UTC(y,m,d)).getUTCDay(),h=+new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',hourCycle:'h23',hour:'2-digit'}).format(ms);
  return wd===6||(wd===5&&h>=17)||(wd===0&&h<17)};
 const dangMo=(ms=Date.now())=>cuoiTuan(ms)?[]:DS.filter(s=>khoang(s,ms).some(([a,b])=>ms>=a&&ms<b)).map(s=>s.k);
 const ghiChu=(ms=Date.now())=>{if(cuoiTuan(ms))return'Forex nghỉ cuối tuần (crypto vẫn chạy)';const m=dangMo(ms);return m.includes('London')&&m.includes('New York')?'Giao thoa London–New York: thanh khoản cao nhất ngày':m.length?'':'Khoảng lặng giữa các phiên'};
 return{DS,khoang,dangMo,ghiChu,cuoiTuan}})();
const dem=ms=>{const p=Math.max(0,Math.round(ms/60000)),g=Math.floor(p/60);return g?g+' giờ '+(p%60)+' phút':p+' phút'};
function phien(){const now=Date.now(),vn=new Date(now+7*36e5),d0=Date.UTC(vn.getUTCFullYear(),vn.getUTCMonth(),vn.getUTCDate())-7*36e5,d1=d0+864e5,pos=t=>((t-d0)/864e5*100);
 let h='<div class="ss">';const cuoi=PH.cuoiTuan(now);
 for(const s of PH.DS){const ks=PH.khoang(s,now),mo=!cuoi&&ks.some(([a,b])=>now>=a&&now<b),ke=ks.filter(([a])=>a>now).sort((p,q)=>p[0]-q[0])[0],dong=ks.find(([a,b])=>now>=a&&now<b);
  const bars=ks.map(([a,b])=>[Math.max(a,d0),Math.min(b,d1),a<=now&&now<b]).filter(([a,b])=>b>a).map(([a,b,m])=>`<span class="${m&&!cuoi?'mo':''}" style="left:${pos(a)}%;width:${pos(b)-pos(a)}%"></span>`).join('');
  h+=`<div class="ss-r"><div><b>${s.k}</b><small><span class="ss-st ${mo?'mo':'dong'}">${mo?'Đang mở':'Đóng'}</span> · ${mo&&dong?'đóng sau '+dem(dong[1]-now):ke&&!cuoi?'mở sau '+dem(ke[0]-now):'cuối tuần'}</small></div><div class="ss-t" title="${esc(s.m)}">${bars}</div></div>`}
 h+=`<div class="ss-gio"><div></div><div>${[0,3,6,9,12,15,18,21,24].map(g=>`<u style="left:${g/24*100}%">${String(g).padStart(2,'0')}h</u>`).join('')}</div></div>`;
 const nowP=pos(now);h+=`</div>`;$('#ss').innerHTML=h;const ss=$('#ss .ss'),w=ss.querySelector('.ss-t');
 if(w){const r0=ss.getBoundingClientRect(),r1=w.getBoundingClientRect(),x=r1.left-r0.left+r1.width*nowP/100;const n=document.createElement('div');n.className='ss-now';n.style.left=x+'px';n.dataset.t=new Date(now).toLocaleTimeString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit'});ss.appendChild(n)}
 $('#ss-ghi').innerHTML=(cuoi?'<b>Thị trường Forex đang nghỉ cuối tuần</b> (mở lại 17:00 Chủ nhật giờ New York). Các mã crypto CFD vẫn giao dịch. ':'<b>'+(PH.dangMo(now).join(' + ')||'Chưa phiên chính nào mở')+'</b>. '+PH.ghiChu(now)+' ')+'Giờ trên trục là giờ Việt Nam. Giờ mở cửa lấy theo giờ làm việc địa phương của từng trung tâm (tự đổi theo giờ mùa hè).'}
let calTien=new Set(),calMuc=2;try{calTien=new Set(JSON.parse(localStorage.getItem('tt-cal-tien')||'[]'));calMuc=+(localStorage.getItem('tt-cal-muc')??2)}catch(e){}
function lich(){const L=T.S&&T.S.lich,el=$('#cal');if(!L)return;if(!L.co){el.innerHTML=`<p class="small">Chưa có lịch tin: ${esc(L.ly_do)}.</p>`;return}
 $('#cal-loc').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',+b.dataset.m===calMuc));
 const tienCo=(L.tien_te||[]).filter(Boolean);$('#cal-tien').innerHTML=`<button type="button" data-t="" aria-pressed="${!calTien.size}">Mọi đồng tiền</button>`+tienCo.map(c=>`<button type="button" data-t="${esc(c)}" aria-pressed="${calTien.has(c)}">${esc(c)}</button>`).join('');
 const now=Date.now(),ds=L.ds.filter(e=>(e.muc>=calMuc||(e.muc===0&&calMuc<=1))&&(!calTien.size||calTien.has(e.tien))),M=L.mang||{};
 let h=L.sap_het?`<p class="note"><b>Lịch tin sắp hết:</b> lịch chỉ phủ tới ${T.gioVN(Date.parse(L.phu_toi))}${M.loi?' và chưa tải được lịch từ mạng ('+esc(M.loi)+')':''}. Mở MT5 có EA xuất lịch để tệp lịch USD được cập nhật; phần né tin của các luật dùng tệp đó.</p>`:'';
 if(M.bat&&M.loi&&!L.sap_het)h+=`<p class="small">Lần tải lịch từ mạng gần nhất bị lỗi (${esc(M.loi)}); đang dùng bản đã lưu, sẽ thử lại sau 15 phút.</p>`;
 let ng='';for(const e of ds){const t=Date.parse(e.t),n=new Date(t).toLocaleDateString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',weekday:'long',day:'2-digit',month:'2-digit'});
  if(n!==ng){h+=`<div class="cal-ngay">${esc(n)}</div>`;ng=n}const qua=t<now,sap=!qua&&t-now<3600000,le=e.muc===0;
  h+=`<div class="cal-r${qua?' qua':''}${sap?' sap':''}"><b>${new Date(t).toLocaleTimeString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit'})}</b><span class="dg">${qua?'đã qua':'sau '+dem(t-now)}</span>`
   +(le?'<span class="badge le">Nghỉ lễ</span>':`<span class="imp m${e.muc}" title="Mức ảnh hưởng ${['','thấp','vừa','cao'][e.muc]}"><i></i><i></i><i></i></span>`)
   +`<span class="badge">${esc(e.tien)}</span><span class="ten">${esc(e.ten)}</span><span class="so">${e.du_bao?`<em>Dự báo</em> ${esc(e.du_bao)}`:''}${e.truoc?`<em>Trước</em> ${esc(e.truoc)}`:''}</span></div>`}
 const nguon=M.so?`lịch tuần này của ForexFactory, tải từ mạng mỗi giờ (lần gần nhất ${M.lan_tai?T.gioVN(Date.parse(M.lan_tai)):'chưa có'}; lịch tuần sau xuất hiện từ Chủ nhật)`+(L.ds.some(e=>e.nguon==='ea')?', cộng tin USD từ tệp lịch MT5 của EA cho phần sau đó':''):'lịch kinh tế MT5 do EA xuất ra (chỉ USD)'+(M.bat?'; lịch nhiều đồng tiền từ mạng chưa tải được'+(M.loi?' ('+esc(M.loi)+')':''):'');
 el.innerHTML=h+(ds.length?'':'<p class="small">Không có sự kiện nào khớp bộ lọc.</p>')+`<p class="small">Nguồn: ${nguon}. Giờ là giờ Việt Nam. Tin mức cao thường làm spread giãn và giá trượt; nhiều người đứng ngoài vài phút trước và sau tin USD mức cao.</p>`}
$('#cal-loc').addEventListener('click',e=>{const b=e.target.closest('button[data-m]');if(!b)return;calMuc=+b.dataset.m;try{localStorage.setItem('tt-cal-muc',calMuc)}catch(_){}lich()});
$('#cal-tien').addEventListener('click',e=>{const b=e.target.closest('button[data-t]');if(!b)return;const c=b.dataset.t;if(!c)calTien.clear();else calTien.has(c)?calTien.delete(c):calTien.add(c);
 try{localStorage.setItem('tt-cal-tien',JSON.stringify([...calTien]))}catch(_){}lich()});
// ---- thông số hợp đồng
function thongSo(){const tk=T.S.tai_khoan||{},tien=tk.tien||'USD',q=spTim.trim().toLowerCase();
 const dem={};for(const x of T.by().values())dem[x.lop]=(dem[x.lop]||0)+1;
 $('#sp-loc').innerHTML=[['tat','Tất cả']].concat(T.LOPS.filter(l=>dem[l]).map(l=>[l,T.S.lop[l]])).map(([k,n])=>`<button type="button" data-l="${k}" aria-pressed="${k===spLoc}">${esc(n)}</button>`).join('');
 const ds=[...T.by().values()].filter(x=>(spLoc==='tat'||x.lop===spLoc)&&(!q||(x.ma+' '+x.goc+' '+x.ten).toLowerCase().includes(q))).sort((a,b)=>T.LOPS.indexOf(a.lop)-T.LOPS.indexOf(b.lop)||a.goc.localeCompare(b.goc));
 const swapTat=ds.some(x=>x.swap&&!x.swap.bat);
 $('#sp-body').innerHTML=ds.map(x=>{const gt=x.q&&x.gt1?x.gt1*x.q[0]:null,db=gt&&x.ky_quy_1lot?gt/x.ky_quy_1lot:null,sw=x.swap||{};
  return`<tr><td class="ma"><b>${esc(x.goc)}</b><small>${esc(x.ten)}</small></td><td>${esc(T.S.lop[x.lop])}<small>${esc(x.kieu_tinh)}</small></td>
  <td class="r">${fmt(x.co_hd,x.co_hd%1?2:0)}<small>${esc(x.tien_goc||'')}</small></td><td class="r">${x.so_le}<small>${x.pip?'1 pip = '+fmt(x.pip,Math.max(0,x.so_le-1)):'1 điểm = '+fmt(x.diem,x.so_le)}</small></td>
  <td class="r">${x.pip?fmt(x.gt_pip,2):fmt(x.gt_diem,x.gt_diem<.1?4:2)} ${esc(tien)}<small>mỗi ${x.pip?'pip':'điểm'} · 1 lot</small></td><td class="r">${fmt(x.gt1,2)} ${esc(tien)}<small>mỗi 1,0 giá · 1 lot</small></td>
  <td class="r">${fmt(gt,0)}<small>giá trị 1 lot</small></td><td class="r">${fmt(x.ky_quy_1lot,2)}<small>${db?'đòn bẩy ≈ 1:'+fmt(db,0):''}</small></td>
  <td class="r">${fmt(x.lot_min,x.lot_min<.01?3:2)} / ${fmt(x.lot_buoc,x.lot_buoc<.01?3:2)}<small>tối đa ${fmt(x.lot_max,0)}</small></td>
  <td class="r ${sw.bat?'':'off'}">${fmt(sw.dai,2)} / ${fmt(sw.ngan,2)}<small>${esc(sw.kieu||'')} · x3 ${esc(sw.ngay_3||'')}</small></td><td class="r">${x.muc_dung||0}<small>điểm</small></td></tr>`}).join('');
 $('#sp-ghi').innerHTML=`Tài khoản ${esc(tk.san||'')} · tiền ${esc(tien)} · đòn bẩy tài khoản 1:${tk.don_bay||'—'}${tk.goi_ky_quy!=null?' · gọi ký quỹ ở mức ký quỹ '+fmt(tk.goi_ky_quy,0)+'%':''}${tk.dung_lenh?' · dừng lệnh ở '+fmt(tk.dung_lenh,0)+'%':''}. Ký quỹ 1 lot do MT5 tính (order_calc_margin) theo giá hiện tại; "đòn bẩy ≈" là giá trị 1 lot chia ký quỹ, nên chỉ số, dầu và crypto có thể khác đòn bẩy của tài khoản.`
  +(swapTat?' <b>Phí qua đêm (swap):</b> sàn đang để chế độ swap "Tắt" cho các mã gạch ngang, nghĩa là tài khoản này không bị tính swap; các con số là mức niêm yết (mua / bán) để tham khảo.':'')}
$('#sp-loc').addEventListener('click',e=>{const b=e.target.closest('button[data-l]');if(!b)return;spLoc=b.dataset.l;thongSo()});
$('#sp-tim').addEventListener('input',e=>{spTim=e.target.value;thongSo()});
// ---- tín hiệu kỹ thuật và bộ lọc mã
let ktLoc='tat',ktDk='tat',ktTim='',ktMa=null,ktTf='H1',ktCT=null,ktLan=0;const KF=['M15','H1','H4','D1'];
const dongThuan=x=>{const k=x.kt||{};let m=0,b=0;for(const f of KF){const d=k[f]&&k[f].d;if(d>.1)m++;else if(d<-.1)b++}return{m,b}};
function kyThuat(){const dem={};for(const x of T.by().values())dem[x.lop]=(dem[x.lop]||0)+1;
 $('#kt-loc').innerHTML=[['tat','Tất cả']].concat(T.LOPS.filter(l=>dem[l]).map(l=>[l,T.S.lop[l]])).map(([k,n])=>`<button type="button" data-l="${k}" aria-pressed="${k===ktLoc}">${esc(n)}</button>`).join('');
 const q=ktTim.trim().toLowerCase();let ds=[...T.by().values()].filter(x=>x.kt&&(ktLoc==='tat'||x.lop===ktLoc)&&(!q||(x.goc+' '+x.ten+' '+(x.biet_danh||'')).toLowerCase().includes(q)));
 const h1=x=>(x.kt.H1||{});
 const LOC={tat:()=>true,mua:x=>dongThuan(x).m>=3,ban:x=>dongThuan(x).b>=3,qmua:x=>h1(x).rsi>=70,qban:x=>h1(x).rsi<=30,xh:x=>h1(x).adx>=25,ngang:x=>h1(x).adx<18};
 ds=ds.filter(LOC[ktDk]||LOC.tat).sort((a,b)=>{const p=dongThuan(a),r=dongThuan(b);return Math.max(r.m,r.b)-Math.max(p.m,p.b)||Math.abs((b.kt.H1||{}).d||0)-Math.abs((a.kt.H1||{}).d||0)});
 $('#kt-n').textContent=ds.length+' mã';
 $('#kt-body').innerHTML=ds.map(x=>{const t=dongThuan(x),k=x.kt,r=h1(x);return`<tr data-ma="${esc(x.ma)}"${x.ma===ktMa?' class="chon"':''}><td class="ma"><b>${esc(x.goc)}</b><small>${esc(x.biet_danh||T.S.lop[x.lop])}</small></td>`
  +KF.map(f=>`<td>${T.kb(k[f]?k[f].d:null)}</td>`).join('')
  +`<td><span class="dt" title="${t.m} khung mua, ${t.b} khung bán">${KF.map((f,i)=>`<i class="${i<t.m?'m':i<t.m+t.b?'b':''}"></i>`).join('')}</span></td><td class="r ${r.rsi>=70?'loss':r.rsi<=30?'gain':''}">${fmt(r.rsi,1)}</td><td class="r">${fmt(r.adx,1)}</td></tr>`}).join('')
  ||'<tr><td colspan="8" class="small" style="padding:18px">'+([...T.by().values()].some(x=>x.kt)?'Không có mã nào khớp bộ lọc.':'Đang tính chỉ báo (lần đầu mất khoảng 10–30 giây sau khi webapp khởi động)…')+'</td></tr>';
 if(!ktMa&&ds.length){ktMa=ds[0].ma;ktTai()}else if(ktMa&&Date.now()-ktLan>30000)ktTai()}
const vong=(d,w=120)=>{const a=Math.PI*(1-((d??0)+1)/2),r=w*.4,cx=w/2,cy=w*.5,x=cx+r*Math.cos(a),y=cy-r*Math.sin(a),arc=(a0,a1,c)=>{const p=t=>[cx+r*Math.cos(Math.PI*(1-t)),cy-r*Math.sin(Math.PI*(1-t))],[x0,y0]=p(a0),[x1,y1]=p(a1);return`<path d="M${x0.toFixed(1)} ${y0.toFixed(1)}A${r} ${r} 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)}" stroke="${c}" stroke-width="${w*.07}" fill="none"/>`};
 return`<svg viewBox="0 0 ${w} ${w*.6}">${arc(0,.25,'var(--loss)')}${arc(.25,.45,'color-mix(in srgb,var(--loss) 45%,var(--track))')}${arc(.45,.55,'var(--track)')}${arc(.55,.75,'color-mix(in srgb,var(--gain) 45%,var(--track))')}${arc(.75,1,'var(--gain)')}
 <line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="var(--ink)" stroke-width="${w*.025}" stroke-linecap="round"/><circle cx="${cx}" cy="${cy}" r="${w*.035}" fill="var(--ink)"/></svg>`};
async function ktTai(){if(!ktMa)return;const m=ktMa;ktLan=Date.now();try{const r=await fetch('/api/thi-truong/ky-thuat?ma='+encodeURIComponent(m),{cache:'no-store'});if(!r.ok)throw new Error(await r.text());const j=await r.json();if(m===ktMa){ktCT=j;ktVe()}}
 catch(e){$('#kt-ct').innerHTML=`<p class="small">Không tính được: ${esc(e.message)}</p>`}}
function ktVe(){const j=ktCT,el=$('#kt-ct');if(!j)return;const x=T.by().get(j.ma),k=j.khung[ktTf];
 let h=`<div class="kt-hd"><div><h2>${esc(j.goc)}</h2><span class="small" style="margin:0">${esc(x?T.tenMa(x):'')}</span></div><div class="lk"><a class="ghost nho" href="/bieu-do?ma=${encodeURIComponent(j.ma)}">Biểu đồ</a><a class="ghost nho" href="/cong-cu?ma=${encodeURIComponent(j.ma)}">Tính khối lượng</a></div></div>`
  +`<div class="sg" id="kt-tf" style="margin-top:10px">${KF.map(f=>`<button type="button" data-f="${f}" aria-pressed="${f===ktTf}">${f}</button>`).join('')}</div>`;
 if(!k){el.innerHTML=h+'<p class="small">Chưa đủ nến cho khung này.</p>';return}
 h+=`<div class="gauge3"><div class="lon">${vong(k.d,140)}<b class="${T.cls(k.d)}">${esc(k.nhan)}</b><small>Tổng hợp</small></div><div>${vong(k.m)}<b class="${T.cls(k.m)}">${esc(k.nhan_ma)}</b><small>Đường trung bình · ${k.dem_ma.mua} mua / ${k.dem_ma.ban} bán</small></div><div>${vong(k.o)}<b class="${T.cls(k.o)}">${esc(k.nhan_dd)}</b><small>Dao động · ${k.dem_dd.mua} mua / ${k.dem_dd.ban} bán / ${k.dem_dd.trung} trung tính</small></div></div>`;
 const pv=p=>p>0?'<span class="p1">Mua</span>':p<0?'<span class="p-1">Bán</span>':'<span class="p0">Trung tính</span>',d=j.so_le;
 h+=`<div class="kt-bang"><div><h4>Chỉ báo dao động</h4><table><tbody>${k.dd.map(r=>`<tr><td>${esc(r.ten)}</td><td class="r">${fmt(r.gt,Math.abs(r.gt)<1?Math.min(6,d):2)}</td><td class="r">${pv(r.p)}</td></tr>`).join('')}</tbody></table></div>
  <div><h4>Đường trung bình (giá ${fmt(k.gia,d)})</h4><table><tbody>${k.ma.map(r=>`<tr><td>${esc(r.ten)}</td><td class="r">${fmt(r.gt,d)}</td><td class="r">${pv(r.p)}</td></tr>`).join('')}</tbody></table></div></div>
  <p class="small">Tính lúc ${T.gioVN(Date.parse(j.luc))}, gồm cả nến ${ktTf} đang chạy. Luật như bảng Technical Ratings của TradingView: dao động chỉ báo mua khi ở vùng quá bán và đang quay lên, nên phần lớn là trung tính. Đây là tóm tắt trạng thái chỉ báo, chưa được kiểm chứng là có lợi thế; các luật đơn giản đo trong sổ của bạn phần lớn không có lãi.</p>`;
 el.innerHTML=h;el.querySelector('#kt-tf').addEventListener('click',e=>{const b=e.target.closest('button[data-f]');if(b){ktTf=b.dataset.f;ktVe()}})}
$('#kt-loc').addEventListener('click',e=>{const b=e.target.closest('button[data-l]');if(!b)return;ktLoc=b.dataset.l;kyThuat()});
$('#kt-dk').addEventListener('change',e=>{ktDk=e.target.value;kyThuat()});
$('#kt-tim').addEventListener('input',e=>{ktTim=e.target.value;kyThuat()});
$('#kt-body').addEventListener('click',e=>{const tr=e.target.closest('tr[data-ma]');if(!tr)return;ktMa=tr.dataset.ma;document.querySelectorAll('#kt-body tr').forEach(r=>r.classList.toggle('chon',r===tr));
 $('#kt-ct').innerHTML='<p class="small">Đang tính…</p>';ktTai();if(innerWidth<1060)$('#kt-ct').scrollIntoView({behavior:'smooth',block:'start'})});
// ---- biến động theo giờ
let bdMa=null,bdKq=null;
async function bienDong(){const s=$('#bd-ma');if(!s.options.length||s.dataset.n!=String(T.by().size)){if(!bdMa){const e=[...T.by().values()].find(x=>x.goc==='XAUUSD')||[...T.by().values()][0];bdMa=e&&e.ma}s.innerHTML=T.nhomOpt(bdMa);s.dataset.n=T.by().size}
 if(!bdMa)return;if(bdKq&&bdKq.ma===bdMa){bdVe();return}$('#bd').innerHTML='<p class="small">Đang đọc 720 nến H1…</p>';
 try{const r=await fetch('/api/thi-truong/bien-dong?ma='+encodeURIComponent(bdMa),{cache:'no-store'});if(!r.ok)throw new Error(await r.text());bdKq=await r.json();bdVe()}catch(e){$('#bd').innerHTML=`<p class="small">Không đọc được: ${esc(e.message)}</p>`}}
function bdVe(){const j=bdKq,x=T.by().get(j.ma);if(!x)return;const u=x.pip?{k:x.pip,n:'pip',d:1}:{k:1,n:'đơn vị giá',d:x.so_le>3?x.so_le:2},v=j.gio.map(g=>g.tb==null?0:g.tb/u.k),mx=Math.max(...v)||1;
 const gioNay=new Date(Date.now()+7*36e5).getUTCHours(),top=v.map((y,i)=>[y,i]).sort((a,b)=>b[0]-a[0]).slice(0,3).map(a=>String(a[1]).padStart(2,'0')+'h');
 const TH=['Thứ Hai','Thứ Ba','Thứ Tư','Thứ Năm','Thứ Sáu','Thứ Bảy','Chủ nhật'],thu=j.thu.filter(t=>t.t<5),mt=Math.max(...thu.map(t=>t.tb));
 $('#bd').innerHTML=`<p class="sub" style="margin:0 0 8px">Biên độ trung bình (cao − thấp) của mỗi nến 1 giờ, tính bằng ${u.n}, trên ${j.so_nen} nến H1 (${T.gioVN(j.tu*1000).slice(-5)} → ${T.gioVN(j.den*1000).slice(-5)}). Giờ chạy mạnh nhất: <b>${top.join(', ')}</b> (giờ Việt Nam). Cột sáng là giờ hiện tại.</p>
  <div class="bd-cot">${v.map((y,i)=>`<div class="${i===gioNay?'nay':''}" style="height:${(y/mx*100).toFixed(1)}%" title="${String(i).padStart(2,'0')}:00–${String(i).padStart(2,'0')}:59 giờ VN: trung bình ${fmt(y,u.d)} ${u.n}">${y===mx?`<span>${fmt(y,u.d)}</span>`:''}</div>`).join('')}</div>
  <div class="bd-gio">${v.map((y,i)=>`<span>${i%3===0?String(i).padStart(2,'0'):''}</span>`).join('')}</div>
  <h3>Biên độ trung bình theo thứ</h3><div class="bd-thu">${thu.map(t=>`<div class="${t.tb===mt?'max':''}"><small>${TH[t.t]}</small><b>${fmt(t.tb/u.k,u.d)}</b><small>${u.n}</small></div>`).join('')}</div>
  <p class="small">Dùng để chọn giờ giao dịch: scalping và phá vỡ cần giờ chạy mạnh; giao dịch vùng hợp giờ yên. Biên độ của cả ngày tính theo ngày giờ Việt Nam. Số đo quá khứ ${Math.round(j.so_nen/24)} ngày gần nhất, có thể đổi khi thị trường đổi trạng thái.</p>`}
$('#bd-ma').addEventListener('change',e=>{bdMa=e.target.value;bdKq=null;bienDong()});
// ---- vẽ
let lanVe=0,choVe=0;
function ve(day){if(!T.S)return;hero();capCB();if(tab==='bang-gia'){if(day||!O.size)bangGia()}else if(tab==='ky-thuat'){if(day)kyThuat()}else if(tab==='suc-manh')sucManh();else if(tab==='ban-do-nhiet')banDo();else if(tab==='tuong-quan')tuongQuan();
 else if(tab==='bien-dong'){if(day)bienDong()}else if(tab==='phien'){phien();lich()}else if(tab==='thong-so')thongSo();lanVe=Date.now()}
T.on((loai,ds)=>{if(loai==='anh'){ve(1);return}if(loai!=='gia')return;
 if(tab==='bang-gia')for(const m of ds)oCap(T.by().get(m),O.get(m),1);
 if(Date.now()-lanVe>1000){if(tab==='bang-gia')hero();else ve(0)}else if(!choVe){choVe=setTimeout(()=>{choVe=0;if(tab!=='bang-gia')ve(0);else hero()},1000)}});
setInterval(()=>{if(tab==='phien'&&document.visibilityState==='visible'){phien();lich()}if(tab==='bang-gia')for(const[m,o]of O)o.dot.classList.toggle('nghi',T.nghi(T.by().get(m)))},30000);
addEventListener('resize',()=>{if(tab==='phien')phien()});
moTab(tab);T.batDau(30).then(()=>moTab(tab)).catch(()=>{})})();
"""


def trang_thi_truong(ten: str) -> str:
    tab = ''.join(f'<button type="button" role="tab" data-t="{k}">{n}</button>' for k, n in (
        ('bang-gia', 'Bảng giá'), ('ky-thuat', 'Tín hiệu kỹ thuật'), ('suc-manh', 'Sức mạnh tiền tệ'), ('ban-do-nhiet', 'Bản đồ nhiệt'),
        ('tuong-quan', 'Tương quan'), ('bien-dong', 'Biến động theo giờ'), ('phien', 'Phiên & lịch tin'), ('thong-so', 'Thông số hợp đồng')))
    ky = ''.join(f'<button type="button" data-k="{k}">{n}</button>' for k, n in (('1h', '1 giờ'), ('4h', '4 giờ'), ('ngay', 'Hôm nay'), ('tuan', 'Tuần'), ('thang', 'Tháng')))
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Thị trường · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'thi-truong', '<button id="theme" type="button">Nền tối</button>') + '<main class="rong">',
        '<div class="tt-top"><div><h1>Thị trường Forex &amp; CFD</h1><p>Giá trực tiếp của mọi cặp tiền, kim loại, năng lượng, chỉ số và tiền mã hóa mà sàn cung cấp, '
        'đẩy về trình duyệt ngay khi có tick mới.</p></div><span id="song" class="song-pill"><i></i>Đang nối…</span></div>',
        '<div class="tt-moi" id="tt-moi" hidden><b>Lần đầu dùng webapp?</b><span>Năm bước để nối MT5, xem tài khoản của bạn và dùng biểu đồ, '
        'mỗi bước tự kiểm trên máy này.</span><a href="/bat-dau">Xem 5 bước bắt đầu</a><button type="button" id="tt-moi-an">Ẩn</button></div>'
        '<script>(()=>{const b=document.getElementById("tt-moi");let da=1;try{da=localStorage.getItem("so-bat-dau")}catch(e){}if(!da)b.hidden=false;'
        'document.getElementById("tt-moi-an").addEventListener("click",()=>{b.hidden=true;try{localStorage.setItem("so-bat-dau","1")}catch(e){}})})()</script>',
        '<div class="tt-hero" id="tt-hero"></div>',
        f'<nav class="tt-tabs" aria-label="Các phần"><div class="sg" id="tt-tabs" role="tablist">{tab}</div></nav>',
        # bảng giá
        '<section class="tt-p" data-p="bang-gia"><div class="tt-tool"><div class="sg" id="bg-loc"></div><span class="grow"></span>'
        '<button type="button" class="ghost" id="cb-mo" aria-expanded="false">🔔 Cảnh báo giá <b id="cb-n">0</b></button>'
        '<input type="search" id="bg-tim" placeholder="Tìm mã: EURUSD, vàng, Nasdaq…" aria-label="Tìm mã"></div>'
        '<div class="tt-card" id="cb-panel" hidden style="margin:0 0 12px"><h2>Cảnh báo giá</h2><p class="sub">Trang báo bằng thông báo nổi, tiếng bíp và thông báo của '
        'máy (nếu bạn cho phép) khi giá Bid chạm mức đặt. Cảnh báo lưu trong trình duyệt này và chỉ chạy khi trang Thị trường hoặc Công cụ đang mở.</p><div class="cb-ds" id="cb-ds"></div></div>'
        '<div class="cb-pop" id="cb-pop" hidden role="dialog" aria-label="Đặt cảnh báo giá"><h4 id="cb-ten">Cảnh báo giá</h4><p class="small" id="cb-hien" style="margin:0 0 8px"></p>'
        '<label>Mức giá<input id="cb-muc" type="number" inputmode="decimal" step="any"></label><label>Ghi chú (không bắt buộc)<input id="cb-ghi" type="text" maxlength="80" '
        'placeholder="Ví dụ: chạm kháng cự tuần"></label><div class="hang"><button type="button" class="ghost" id="cb-huy">Hủy</button>'
        '<button type="button" class="act" id="cb-luu">Đặt cảnh báo</button></div></div>'
        '<div class="tt-wrap"><table class="bg" id="bg"><thead><tr><th></th><th data-k="ten">Mã</th><th class="r">Bid</th><th class="r ask">Ask</th>'
        '<th class="r" data-k="spread">Spread</th><th class="r c1" data-k="1h">1 giờ</th><th class="r" data-k="ngay">Hôm nay</th><th class="r cw" data-k="tuan">Tuần</th>'
        '<th class="rg" data-k="adr">Biên độ hôm nay</th><th class="tia-c">4 giờ qua</th><th></th></tr></thead><tbody id="bg-body">'
        '<tr><td colspan="11" class="small" style="padding:18px">Đang đọc bảng giá…</td></tr></tbody></table></div>'
        '<p class="small">"Hôm nay" so với giá đóng cửa của ngày giao dịch trước, "Tuần" so với giá mở cửa đầu tuần, "1 giờ" so với giá cách đây khoảng 60 phút. '
        'Biên độ hôm nay: vạch là giá hiện tại giữa đáy và đỉnh trong ngày; "% ADR" là biên độ hôm nay so với biên độ trung bình 14 ngày (trên 100% là ngày biến động mạnh). '
        'Spread của Forex tính bằng pip, của CFD tính bằng điểm giá nhỏ nhất. Bấm tên mã để mở biểu đồ, ★ để theo dõi, "Tính" để mở công cụ tính khối lượng.</p></section>',
        # tín hiệu kỹ thuật
        '<section class="tt-p" data-p="ky-thuat" hidden><div class="tt-tool"><div class="sg" id="kt-loc"></div><span class="grow"></span>'
        '<select id="kt-dk" aria-label="Lọc"><option value="tat">Mọi mã</option><option value="mua">Đồng thuận mua (≥ 3/4 khung)</option>'
        '<option value="ban">Đồng thuận bán (≥ 3/4 khung)</option><option value="qmua">RSI H1 quá mua (≥ 70)</option><option value="qban">RSI H1 quá bán (≤ 30)</option>'
        '<option value="xh">Đang có xu hướng (ADX H1 ≥ 25)</option><option value="ngang">Đi ngang (ADX H1 &lt; 18)</option></select>'
        '<input type="search" id="kt-tim" placeholder="Tìm mã…" aria-label="Tìm mã"><span class="small" id="kt-n" style="margin:0"></span></div>'
        '<div class="kt-g"><div class="tt-wrap"><table class="kt"><thead><tr><th>Mã</th><th>M15</th><th>H1</th><th>H4</th><th>D1</th><th>Đồng thuận</th>'
        '<th class="r">RSI H1</th><th class="r">ADX H1</th></tr></thead><tbody id="kt-body"></tbody></table></div>'
        '<div class="tt-card kt-ct" id="kt-ct" style="margin:0"><p class="small">Chọn một mã để xem chi tiết.</p></div></div>'
        '<p class="small">Mỗi ô tổng hợp 12 đường trung bình và 7 chỉ báo dao động trên khung đó (như bảng Technical Ratings của TradingView), tính lại mỗi phút. '
        '"Đồng thuận" đếm số khung cùng nghiêng mua (xanh) hoặc bán (đỏ). Bấm một dòng để xem từng chỉ báo.</p></section>',
        # sức mạnh tiền tệ
        f'<section class="tt-p" data-p="suc-manh" hidden><div class="tt-tool"><div class="sg" id="sm-ky">{ky}</div></div><div class="sm-grid">'
        '<div class="tt-card"><h2>Sức mạnh 8 đồng tiền chính</h2><p class="sub">Trung bình thay đổi của mỗi đồng tiền so với 7 đồng còn lại, tính lại theo từng tick trên 28 cặp.</p><div id="sm-bar"></div></div>'
        '<div class="tt-card"><h2>Ma trận thay đổi theo cặp</h2><p class="sub">Hàng là đồng tiền gốc, cột là đồng tiền định giá: ô xanh nghĩa là đồng ở hàng mạnh lên so với đồng ở cột.</p><div id="sm-mx" style="overflow-x:auto"></div></div>'
        '</div><div class="goi-y" id="sm-goi"></div></section>',
        f'<section class="tt-p" data-p="ban-do-nhiet" hidden><div class="tt-tool"><div class="sg" id="hm-ky">{ky}</div><span class="small" style="margin:0">Màu đậm là thay đổi lớn so với các mã còn lại; bấm ô để mở biểu đồ.</span></div><div id="hm"></div></section>',
        '<section class="tt-p" data-p="tuong-quan" hidden><div class="tt-card"><h2>Tương quan giữa các mã</h2><p class="sub">+1: luôn đi cùng chiều; −1: luôn ngược chiều; quanh 0: không liên quan.</p><div id="tq"></div></div></section>',
        '<section class="tt-p" data-p="bien-dong" hidden><div class="tt-card"><div class="tt-tool" style="margin:0 0 4px"><h2 style="margin:0">Biến động theo giờ trong ngày</h2>'
        '<span class="grow"></span><select id="bd-ma" aria-label="Chọn mã"></select></div><div id="bd"></div></div></section>',
        '<section class="tt-p" data-p="phien" hidden><div class="tt-card"><h2>Phiên giao dịch hôm nay</h2><p class="sub" id="ss-ghi"></p><div id="ss"></div></div>'
        '<div class="tt-card"><div class="tt-tool" style="margin:0 0 6px"><h2 style="margin:0">Lịch tin kinh tế</h2><span class="grow"></span><div class="sg" id="cal-loc">'
        '<button type="button" data-m="1">Mọi mức</button><button type="button" data-m="2">Vừa và cao</button><button type="button" data-m="3">Chỉ tin mạnh</button></div></div>'
        '<div class="sg" id="cal-tien" style="margin:0 0 8px"></div><div id="cal"><p class="small">Đang đọc lịch…</p></div></div></section>',
        '<section class="tt-p" data-p="thong-so" hidden><div class="tt-tool"><div class="sg" id="sp-loc"></div><span class="grow"></span><input type="search" id="sp-tim" placeholder="Tìm mã…" aria-label="Tìm mã"></div>'
        '<div class="tt-wrap"><table class="spec"><thead><tr><th>Mã</th><th>Loại</th><th class="r">Kích thước hợp đồng</th><th class="r">Số lẻ</th><th class="r">Giá trị pip / điểm</th>'
        '<th class="r">Giá trị 1,0 giá</th><th class="r">Giá trị danh nghĩa</th><th class="r">Ký quỹ 1 lot</th><th class="r">Lot nhỏ nhất / bước</th><th class="r">Swap mua / bán</th><th class="r">Mức dừng tối thiểu</th></tr></thead>'
        '<tbody id="sp-body"></tbody></table></div><p class="small" id="sp-ghi"></p></section>',
        '<p class="note" style="margin-top:22px"><b>Chỉ đọc giá.</b> Trang lấy giá từ MT5 demo đang mở trên máy này và không đặt lệnh. CFD và Forex là sản phẩm có đòn bẩy, '
        'rủi ro cao: phần lớn tài khoản cá nhân giao dịch CFD bị lỗ. Không phải lời khuyên đầu tư.</p>',
        '<footer>Giá: tick của MT5, đọc liên tục (mặc định 20 lần mỗi giây) và đẩy về trình duyệt qua Server-Sent Events ngay khi có giá mới. Thông số hợp đồng, ký quỹ và các mốc giá đọc lại 30 giây một lần; '
        'tương quan 10 phút một lần. ' + escape(trang.MIEN_TRU) + f'</footer></main><script>{trang.JS}</script><script>{JS_CHUNG}</script><script>{JS}</script></body></html>'])
