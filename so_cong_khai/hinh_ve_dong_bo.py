"""Đồng bộ bản vẽ theo tài khoản, CAS và ghép ba phía theo id hình."""
JS = r"""
(()=>{
const eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b),copy=v=>JSON.parse(JSON.stringify(v));
function merge(base,local,remote,choice){const B=new Map(base.map(h=>[h.id,h])),L=new Map(local.map(h=>[h.id,h])),R=new Map(remote.map(h=>[h.id,h])),ids=[...new Set([...R.keys(),...L.keys(),...B.keys()])],ds=[],conflicts=[];
 for(const id of ids){const b=B.get(id),l=L.get(id),r=R.get(id),lc=!eq(l,b),rc=!eq(r,b);let v;
  if(!lc)v=r;else if(!rc||eq(l,r))v=l;else{conflicts.push(id);v=choice==='remote'?r:l;if(choice==='both'){v=r;if(l){const q=copy(l);q.id='ban_'+Date.now().toString(36)+Math.random().toString(36).slice(2,12);ds.push(q)}}}
  if(v)ds.push(copy(v))}return{ds,conflicts}}
window.HVD_MERGE=merge;
const G=window.BDMN;if(!G)return;const U=window.HVD_CHU,S=new Map();let stopped=false;
const khoa=g=>g.veKhoa?g.veKhoa():window.HVD_KHOA?HVD_KHOA(g.ma):'so-ve:'+(g.ma||'XAU'),maCua=g=>window.HVD_MA?HVD_MA(g.ma):g.ma||'XAU',META=k=>'so-ve-dong:'+k.slice(6);
const ls=k=>{try{return localStorage.getItem(k)}catch(e){return null}},parse=(s,d)=>{try{const v=JSON.parse(s);return v==null?d:v}catch(e){return d}};
const headers=()=>({'Content-Type':'application/json','X-So-Cong-Khai':'1',...(U?{'X-Chart-Owner':U.id}:{})});
function state(g){const k=khoa(g);if(!S.has(k)){let m=parse(ls(META(k)),{});if(Array.isArray(m))m={base:m};S.set(k,{k,ma:maCua(g),base:Array.isArray(m.base)?m.base:[],ban:m.ban??null,ready:false,sending:false,reading:false,next:0,delay:1000,lastRead:0,conflicts:[],status:'loading',text:'Đang khôi phục bản vẽ…'})}return S.get(k)}
function active(s){const g=G();return g&&khoa(g)===s.k?g:null}
function busy(s){const g=active(s);return !!(g&&(g.VE.keo||g.VE.tam||document.querySelector('.venhap,.mnp,.cbv-nen')))}
function local(s){const g=active(s);if(g&&g.veKhoa&&Array.isArray(g.VE.ds))return copy(g.VE.ds);if(s.localError&&s.draft)return copy(s.draft);return parse(ls(s.k),s.draft||[])}
function setStatus(s,status,text){s.status=status;s.text=text;paint()}
function paint(){const g=G();if(!g||!window.HVD_UI)return;if(window.HVD_KHOI_PHUC){HVD_UI.paint('restoring','Đang khôi phục bản vẽ… Tạm khóa chỉnh sửa.');return}if(window.PHAT_LAI){HVD_UI.paint('replay','Luyện tập: bản vẽ tạm, kho thật được giữ riêng');return}if(U===null){HVD_UI.paint('guest','Đăng nhập để lưu bản vẽ riêng');return}const s=state(g);HVD_UI.paint(s.status,s.text)}
function meta(s){try{localStorage.setItem(META(s.k),JSON.stringify({base:s.base,ban:s.ban}));return true}catch(e){s.localError=true;return false}}
function apply(s,ds){s.draft=copy(ds);const raw=JSON.stringify(ds);try{localStorage.setItem(s.k,raw);s.localError=false}catch(e){s.localError=true}
 const g=active(s);if(g&&!busy(s)&&!eq(g.VE.ds,ds)){g.VE.ds=copy(ds);g.VE.goc=raw;g.VE.chon=null;g.VE.cu=[];g.VE.lai=[];g.veTb();g.lwPhu()}}
function fail(s,j){if(j&&(j.doi_tai_khoan||j.dang_nhap===false)){stopped=true;setStatus(s,'error','Phiên đăng nhập đã đổi hoặc hết hạn. Tải lại trang để tiếp tục.');return}
 s.next=Date.now()+s.delay;s.delay=Math.min(30000,s.delay*2);setStatus(s,'error',(s.localError?'Chưa lưu: bộ nhớ trình duyệt không khả dụng. Giữ trang này mở.':'Chưa đồng bộ · bản nháp còn trên máy này')+(j&&j.ly_do?' · '+j.ly_do:''))}
function accept(s,j){if(busy(s))return false;const now=local(s),m=merge(s.base,now,j.ds||[]);s.remote=j;s.ready=true;s.conflicts=m.conflicts;apply(s,m.ds);
 if(m.conflicts.length){setStatus(s,'conflict','Có xung đột · bấm để chọn bản cần giữ');return false}
 if(eq(m.ds,j.ds||[])){s.base=copy(j.ds||[]);s.ban=j.ban;meta(s);setStatus(s,'saved','Đã lưu trên máy chủ')}else setStatus(s,'pending','Có thay đổi chưa đồng bộ');return true}
async function pull(s){if(stopped||U===null||s.reading||s.sending)return;s.reading=true;s.lastRead=Date.now();try{const r=await fetch('/api/hinh-ve?ma='+encodeURIComponent(s.ma),{cache:'no-store',headers:headers()}),j=await r.json();if(!r.ok){fail(s,j);return}if(U&&j.chu!==U.id){fail(s,{doi_tai_khoan:true});return}accept(s,j)}catch(e){fail(s)}finally{s.reading=false}}
async function flush(s,keep){if(stopped||U===null||s.restoring)return false;if(s.sending||busy(s))return false;if(!s.ready)await pull(s);if(!s.ready||s.conflicts.length)return false;
 const sent=local(s);if(eq(sent,s.base)){if(s.status!=='conflict')setStatus(s,'saved','Đã lưu trên máy chủ');return true}
 let n0=s.base.length;const daHoi=window.HVD_DA_HOI===true;window.HVD_DA_HOI=false;
 if(!sent.length&&n0>=5&&!daHoi&&!confirm('Xóa toàn bộ '+n0+' hình vẽ của mã này trên máy chủ? Bản cũ vẫn còn trong lịch sử.')){apply(s,s.base);return false}
 const body=JSON.stringify({ma:s.ma,ds:sent,ban_co_so:s.remote?s.remote.ban:s.ban});if(keep&&new TextEncoder().encode(body).length>60000)return false;
 s.sending=true;setStatus(s,'saving','Đang lưu…');try{const r=await fetch('/api/hinh-ve',{method:'POST',headers:headers(),keepalive:!!keep,body}),j=await r.json();
  if(r.status===409&&j.xung_dot){accept(s,j);return false}if(!r.ok||!j.ok){fail(s,j);return false}if(U&&j.chu!==U.id){fail(s,{doi_tai_khoan:true});return false}
  s.base=copy(sent);s.ban=j.ban;s.remote={ds:copy(sent),ban:j.ban};s.delay=1000;s.next=0;meta(s);setStatus(s,eq(local(s),sent)?'saved':'pending',eq(local(s),sent)?'Đã lưu trên máy chủ':'Có thay đổi chưa đồng bộ');return eq(local(s),sent)
 }catch(e){fail(s);return false}finally{s.sending=false}}
function doi(){if(window.PHAT_LAI){paint();return}const g=G();if(!g)return;const s=state(g);s.draft=copy(g.VE.ds);s.localError=!!g.VE.luuLoi;if(U===null){paint();return}setStatus(s,'pending','Có thay đổi chưa đồng bộ');schedule(s)}
function schedule(s){const sig=JSON.stringify(local(s));if(s.timer&&s.sig===sig)return;clearTimeout(s.timer);s.sig=sig;s.timer=setTimeout(()=>{s.timer=null;if(Date.now()>=s.next)flush(s)},350)}
function tick(){const g=G();if(!g)return;if(window.PHAT_LAI||window.HVD_KHOI_PHUC){paint();return}const s=state(g);if(U===null){paint();return}for(const q of S.values()){if(stopped||q.conflicts.length)continue;if(!q.ready){if(!q.reading&&Date.now()>=q.next&&Date.now()-q.lastRead>2500)pull(q).then(()=>{if(q.ready&&!eq(local(q),q.base))schedule(q)});}else if(!q.sending&&Date.now()>=q.next&&!eq(local(q),q.base))schedule(q)}paint()}
async function gui(){if(window.PHAT_LAI)return false;if(U===null){if(window.HVD_UI)HVD_UI.account();return false}const g=G();if(g)state(g);let ok=true;for(const s of S.values()){clearTimeout(s.timer);s.timer=null;s.next=0;ok=(await flush(s))&&ok}return ok}
function xungDot(){const s=state(G());if(s.conflicts.length&&window.HVD_UI)HVD_UI.conflict(s.conflicts.length)}
function giaiQuyet(choice){if(!['local','remote','both'].includes(choice))return;const s=state(G());if(!s.remote||!s.conflicts.length)return;
 const m=merge(s.base,local(s),s.remote.ds||[],choice);s.base=copy(s.remote.ds||[]);s.ban=s.remote.ban;s.conflicts=[];meta(s);apply(s,m.ds);setStatus(s,'pending','Có thay đổi chưa đồng bộ');schedule(s)}
async function lichSu(){if(window.PHAT_LAI)throw Error('Thoát phát lại để mở kho bản vẽ thật.');const s=state(G()),r=await fetch('/api/hinh-ve/lich-su?ma='+encodeURIComponent(s.ma),{headers:headers(),cache:'no-store'}),j=await r.json();if(!r.ok)throw Error(j.ly_do||'Cần đăng nhập lại để đọc lịch sử.');return j.ds}
async function khoiPhuc(ban){if(window.PHAT_LAI||window.HVD_KHOI_PHUC)throw Error('Thoát phát lại hoặc chờ khôi phục hoàn tất.');const s=state(G());if(s.reading||s.sending)throw Error('Đang đồng bộ. Hãy thử khôi phục lại sau.');window.HVD_KHOI_PHUC=true;paint();
 try{if(!await gui())throw Error('Cần đồng bộ hoặc xử lý xung đột trước khi phục hồi.');await pull(s);if(!active(s)||busy(s)||s.conflicts.length||!eq(local(s),s.base)||s.status==='error')throw Error('Đang sửa chart hoặc có xung đột.');
 s.restoring=true;const snapshot=local(s),r=await fetch('/api/hinh-ve',{method:'POST',headers:headers(),body:JSON.stringify({viec:'khoi_phuc',ma:s.ma,ban,ban_co_so:s.remote.ban})}),j=await r.json();
 if(!r.ok||!j.ok){if(j.xung_dot)accept(s,j);else fail(s,j);throw Error(j.ly_do||'Chart đã thay đổi. Kiểm tra lại trước khi phục hồi.')}
 if(U&&j.chu!==U.id){fail(s,{doi_tai_khoan:true});throw Error('Phiên đăng nhập đã đổi hoặc hết hạn. Tải lại trang để tiếp tục.')}
 if(!Array.isArray(j.ds))throw Error('Phản hồi khôi phục không hợp lệ.');
 if(!eq(local(s),snapshot)){s.base=snapshot;accept(s,j);throw Error('Chart đã sửa trong lúc khôi phục. Bản nháp được giữ để xử lý xung đột.')}
 s.base=copy(j.ds);s.ban=j.ban;s.remote=j;s.conflicts=[];meta(s);apply(s,j.ds);setStatus(s,'saved','Đã khôi phục và lưu trên máy chủ')
 }finally{s.restoring=false;window.HVD_KHOI_PHUC=false;paint()}}
async function nhapTam(){const s=state(G());if(!await gui())throw Error('Chưa đồng bộ được chart hiện tại.');const ds=parse(ls('so-ve:khach:'+s.ma),[]);if(!ds.length)throw Error('Không có bản nháp cho mã đang xem.');const ids=new Set(local(s).map(h=>h.id)),next=local(s);for(const h of ds){const q=copy(h);if(ids.has(q.id))q.id='nhap_'+Date.now().toString(36)+Math.random().toString(36).slice(2,10);next.push(q);ids.add(q.id)}apply(s,next);await flush(s)}
async function digest(v){const a=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(v));return Array.from(new Uint8Array(a),b=>b.toString(16).padStart(2,'0')).join('')}
async function nhapCuLocal(){if(!U||!U.chu)throw Error('Chỉ tài khoản chủ đầu tiên được nhập kho bản vẽ cũ.');if(!await gui())throw Error('Chưa đồng bộ được chart hiện tại.');
 const keys=[];for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(/^so-ve:[A-Za-z0-9._#+-]{1,40}$/.test(k))keys.push(k)}let count=0;
 for(const k of keys){const raw=ls(k),ds=parse(raw,[]);if(!Array.isArray(ds)||!ds.length)continue;const mark='hvd-nhap-cu:'+U.id+':'+k,hash=await digest(raw);if(ls(mark)===hash)continue;
  const s=state({ma:window.HVD_MA?HVD_MA(k.slice(6)==='XAU'?'':k.slice(6)):k.slice(6)});await pull(s);if(!s.ready||s.conflicts.length)throw Error('Cần đồng bộ hoặc xử lý xung đột trước khi phục hồi.');
  const next=local(s),seen=new Map(next.map(h=>[h.id,h]));for(const h of ds){if(eq(seen.get(h.id),h))continue;const q=copy(h);if(seen.has(q.id))q.id='cu_'+(await digest(JSON.stringify(q))).slice(0,28);if(seen.has(q.id))continue;next.push(q);seen.set(q.id,q);count++}
  apply(s,next);if(!await flush(s))throw Error('Chưa đồng bộ được chart hiện tại.');try{localStorage.setItem(mark,hash)}catch(e){}
 }return count}
setInterval(tick,400);setInterval(()=>{const g=G();if(g&&document.visibilityState==='visible'&&!window.PHAT_LAI&&!window.HVD_KHOI_PHUC)pull(state(g))},8000);
addEventListener('online',()=>{if(window.HVD_KHOI_PHUC)return;for(const s of S.values()){s.next=0;if(!s.ready)pull(s);else schedule(s)}});
addEventListener('pagehide',()=>{const g=G();if(g&&g.veLuu&&!g.VE.tam)g.veLuu(1);for(const s of S.values()){clearTimeout(s.timer);s.timer=null;flush(s,true)}});
addEventListener('beforeunload',e=>{if([...S.values()].some(s=>s.localError&&!eq(local(s),s.base))){e.preventDefault();e.returnValue=''}});
function truocLuyen(){const g=G();if(g.veLuu)g.veLuu(1);const s=state(g);s.draft=copy(g.VE.ds);s.localError=!!g.VE.luuLoi;return s.k}
function sauLuyen(k,fallback){const s=S.get(k);return s?{ds:copy(local(s)),luuLoi:!!s.localError}:{ds:copy(fallback),luuLoi:false}}
window.HVD={doi,gui,paint,truocLuyen,sauLuyen,nap:async()=>{if(window.PHAT_LAI)return false;const s=state(G());await pull(s);if(!eq(local(s),s.base))return flush(s)},xungDot,giaiQuyet,lichSu,khoiPhuc,nhapTam,nhapCuLocal};tick();
})();
"""
