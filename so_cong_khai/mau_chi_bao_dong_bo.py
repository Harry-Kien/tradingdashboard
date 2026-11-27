"""Đồng bộ mẫu có CAS và ghép ba phía; không ghi đè sửa đổi từ tab khác."""

JS = r"""
(()=>{const cp=x=>JSON.parse(JSON.stringify(x)),eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b),empty=()=>({mau:{},sao:[]});
function merge(base,local,remote,choice){const mau={},conflicts=[],B=base.mau||{},L=local.mau||{},R=remote.mau||{},names=[...new Set([...Object.keys(R),...Object.keys(L),...Object.keys(B)])];
 for(const name of names){const b=B[name],l=L[name],r=R[name],lc=!eq(l,b),rc=!eq(r,b);let value;
  if(!lc)value=r;else if(!rc||eq(l,r))value=l;else{conflicts.push(name);value=choice==='remote'?r:l;
   if(choice==='both'&&l!==undefined&&r!==undefined){value=r;let i=1,n;do{const suffix=' ('+i+')';i++;n=name.slice(0,40-suffix.length)+suffix}while(names.includes(n)||n in mau);mau[n]=cp(l)}}
  if(value!==undefined)mau[name]=cp(value)}
 const b=new Set(base.sao||[]),l=new Set(local.sao||[]),r=new Set(remote.sao||[]),sao=[];
 for(const k of new Set([...r,...l,...b]))if(l.has(k)!==b.has(k)?l.has(k):r.has(k))sao.push(k);
 return{mau,sao,conflicts}}
window.MCB_MERGE=merge;
const U=window.HVD_CHU;if(U===null)return;
const K=window.HVD_CB_KEY||'so-cbcn1',SN=K+'-dong',META=K+'-meta-v2',H={'Content-Type':'application/json','X-So-Cong-Khai':'1',...(U?{'X-Chart-Owner':U.id}:{})};
const read=k=>{try{return localStorage.getItem(k)}catch(e){return null}},parse=(x,f)=>{try{return JSON.parse(x)||f}catch(e){return f}},shape=x=>({mau:x.mau||{},sao:x.sao||[]});
const doc=()=>shape(window.CBCN&&CBCN.cauHinh?CBCN.cauHinh():parse(read(K),empty())),old=parse(read(META),null);let BASE=old?old.base:parse(read(SN),empty()),BAN=old?old.ban:null,ready=false,sending=false,reading=false,stopped=false,conflict=null,state='loading',message='Đang đồng bộ mẫu chỉ báo…';
function paint(){if(window.HVD_UI&&HVD_UI.mauPaint){const bad=window.CBCN&&CBCN.loiLuu&&CBCN.loiLuu();HVD_UI.mauPaint(bad?'error':state,bad?'Không lưu được nháp mẫu trên trình duyệt. Giữ trang mở tới khi đồng bộ.':message)}}
function status(s,t){state=s;message=t;paint()}
function meta(){try{localStorage.setItem(META,JSON.stringify({base:BASE,ban:BAN}));localStorage.setItem(SN,JSON.stringify(BASE))}catch(e){status('error','Chưa lưu được mốc đồng bộ mẫu trên trình duyệt.')}}
function ap(x){if(window.CBCN&&CBCN.dongBo){if(CBCN.dongBo(x)===false)return false}else{const raw=parse(read(K),{});try{localStorage.setItem(K,JSON.stringify({...raw,...shape(x)}))}catch(e){status('error','Chưa lưu được mẫu trên trình duyệt.');return false}}return true}
function fail(r,j){if(r&&(r.status===401||j.doi_tai_khoan)){stopped=true;status('error','Phiên tài khoản đã đổi. Tải lại trang để đồng bộ mẫu.')}else status('error',j&&j.ly_do||'Chưa đồng bộ mẫu; bản nháp vẫn còn trên trình duyệt.')}
function accept(j,wasEmpty){const remote=shape(j),local=doc(),m=wasEmpty&&read(K)==null?{...remote,conflicts:[]}:merge(BASE,local,remote);
 if(m.conflicts.length){conflict={remote,ban:j.ban,names:m.conflicts};status('conflict','Mẫu chỉ báo có sửa đổi khác nhau · bấm để xử lý');return false}
 if(!ap(m)&&!(window.CBCN&&CBCN.cauHinh))return false;BASE=remote;BAN=j.ban;ready=true;meta();status(eq(doc(),BASE)?'saved':'pending',eq(doc(),BASE)?'Mẫu chỉ báo đã đồng bộ':'Mẫu chỉ báo đang chờ lưu');return true}
async function nap(){if(stopped||reading||sending||conflict)return false;reading=true;const wasEmpty=read(K)==null;
 try{const r=await fetch('/api/mau-chi-bao',{cache:'no-store',headers:H}),j=await r.json();if(!r.ok){fail(r,j);return false}if(U&&j.chu!==U.id){fail(r,{doi_tai_khoan:true});return false}
  if(document.querySelector('.cbcn-nen:not([hidden]) input:focus'))return false;return accept(j,wasEmpty)}catch(e){fail(null,{})}finally{reading=false}return false}
async function gui(keep){if(stopped||sending||conflict)return false;if(!ready&&!await nap())return false;const sent=cp(doc());if(eq(sent,BASE)){status('saved','Mẫu chỉ báo đã đồng bộ');return true}
 const n0=Object.keys(BASE.mau||{}).length;if(!Object.keys(sent.mau).length&&n0>=3&&!confirm('Xóa toàn bộ '+n0+' mẫu chỉ báo của tài khoản này?')){ap(BASE);return false}
 sending=true;status('pending','Đang lưu mẫu chỉ báo…');try{const r=await fetch('/api/mau-chi-bao',{method:'POST',headers:H,keepalive:!!keep,body:JSON.stringify({...sent,ban_co_so:BAN})}),j=await r.json();
  if(r.status===409&&j.xung_dot){ready=false;accept(j,false);return false}if(!r.ok||!j.ok){fail(r,j);return false}if(U&&j.chu!==U.id){fail(r,{doi_tai_khoan:true});return false}
  BASE=sent;BAN=j.ban;meta();status(eq(doc(),BASE)?'saved':'pending',eq(doc(),BASE)?'Mẫu chỉ báo đã đồng bộ':'Mẫu chỉ báo còn thay đổi chưa gửi');return true
 }catch(e){fail(null,{})}finally{sending=false}return false}
function resolve(choice){if(!conflict||!['local','remote','both'].includes(choice))return;const c=conflict,m=merge(BASE,doc(),c.remote,choice);if(!ap(m))return;BASE=c.remote;BAN=c.ban;conflict=null;ready=true;meta();gui()}
function showConflict(){if(conflict&&window.HVD_UI&&HVD_UI.mauConflict)HVD_UI.mauConflict(conflict.names)}
setInterval(()=>{paint();if(!stopped&&!conflict&&!reading&&!sending&&ready&&!eq(doc(),BASE)&&!window.PHAT_LAI)gui()},1000);
setInterval(()=>{if(document.visibilityState==='visible'&&!window.PHAT_LAI)nap()},10000);
addEventListener('online',()=>gui());addEventListener('pagehide',()=>{if(ready&&!eq(doc(),BASE))gui(true)});
addEventListener('beforeunload',e=>{if(window.CBCN&&CBCN.loiLuu&&CBCN.loiLuu()&&!eq(doc(),BASE)){e.preventDefault();e.returnValue=''}});
window.MCB={nap,gui,resolve,showConflict,paint};nap();
})();
"""
