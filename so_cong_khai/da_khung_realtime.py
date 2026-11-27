"""Ghép nến đang chạy, EMA theo tick và hàng đợi tải lịch sử dùng chung."""
from . import da_khung_vendor

JS = da_khung_vendor.JS + r'''
window.DKRT=(()=>{
 const TF={M1:60,M2:120,M3:180,M5:300,M10:600,M15:900,M30:1800,H1:3600,H2:7200,H3:10800,H4:14400,D1:86400,W1:604800,MN1:0};
 const finite=v=>typeof v==='number'&&Number.isFinite(v),quote=q=>Array.isArray(q)&&q.length>=3&&q.slice(0,3).every(finite)&&q[0]>0&&q[1]>=q[0]&&q[2]>0&&Number.isFinite(new Date(q[2]).getTime());
 const candle=c=>Array.isArray(c)&&c.length>=5&&c.slice(0,5).every(finite)&&c[0]>0&&Number.isInteger(c[0])&&Number.isFinite(new Date(c[0]*1000).getTime())&&c.slice(1,5).every(v=>v>0)&&c[2]>=Math.max(c[1],c[4])&&c[3]<=Math.min(c[1],c[4]);
 function next(t,tf){if(tf==='MN1'){const d=new Date(t*1000);return Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+1,1,d.getUTCHours(),d.getUTCMinutes(),d.getUTCSeconds())/1000}return t+TF[tf]}
 function bucket(t,start,tf){if(tf==='MN1'){const d=new Date(t*1000),s=new Date(start*1000),a=Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),1,s.getUTCHours(),s.getUTCMinutes(),s.getUTCSeconds())/1000;return a<=t?a:Date.UTC(d.getUTCFullYear(),d.getUTCMonth()-1,1,s.getUTCHours(),s.getUTCMinutes(),s.getUTCSeconds())/1000}return start+Math.floor((t-start)/TF[tf])*TF[tf]}
 function ema(s,n){const key='e'+n,a=s[key],i=s.cs.length-1;if(i<0)return null;const prev=i?a[i-1]:null;
  let v;if(finite(prev))v=prev+(s.cs[i][4]-prev)*2/(n+1);else{v=s.cs[0][4];for(let j=1;j<=i;j++)v+=(s.cs[j][4]-v)*2/(n+1)}a[i]=i>=n-1?v:null;return a[i]}
 function snapshot(j,tf){if(!Object.hasOwn(TF,tf)||!Array.isArray(j.candles)||!j.candles.length)throw Error('Chưa có nến cho khung này.');if(j.tf&&j.tf!==tf)throw Error('Nến trả về không đúng khung đã chọn.');
  const cs=j.candles.map(c=>c.slice(0,5));for(let i=0;i<cs.length;i++)if(!candle(cs[i])||(i&&cs[i][0]<=cs[i-1][0]))throw Error('Dữ liệu nến không hợp lệ.');
  const s={cs,tf,e20:cs.map((_,i)=>finite(j.ema20?.[i])?j.ema20[i]:null),e50:cs.map((_,i)=>finite(j.ema50?.[i])?j.ema50[i]:null),lastMs:finite(j.tick_ms)?j.tick_ms:0,src:j.nguon||'luu',provisional:false};
  if(j.dang_chay){if(!candle(j.dang_chay))throw Error('Nến đang chạy không hợp lệ.');const c=j.dang_chay.slice(0,5),last=cs.at(-1);if(c[0]>last[0])cs.push(c);else if(c[0]===last[0])cs[cs.length-1]=c;ema(s,20);ema(s,50)}
  else if(!finite(s.e20.at(-1))||!finite(s.e50.at(-1))){ema(s,20);ema(s,50)}return s}
 function tick(s,q){if(!quote(q)||q[2]<s.lastMs)return false;const t=Math.floor(q[2]/1000),b=q[0],last=s.cs.at(-1);if(t<last[0])return false;
  let fresh=false;if(t>=next(last[0],s.tf)){s.cs.push([bucket(t,last[0],s.tf),b,b,b,b]);s.provisional=true;fresh=true}
  else{last[2]=Math.max(last[2],b);last[3]=Math.min(last[3],b);last[4]=b}
  s.lastMs=q[2];ema(s,20);ema(s,50);if(s.cs.length>600){const n=s.cs.length-600;s.cs.splice(0,n);s.e20.splice(0,n);s.e50.splice(0,n)}return{fresh}}
 function merge(s,old){if(!old||old.tf!==s.tf)return s;const newer=old.lastMs>s.lastMs,first=s.cs[0][0],prefix=old.cs.filter(c=>c[0]<first);
  if(prefix.length){s.cs=prefix.map(c=>c.slice()).concat(s.cs);s.e20=old.e20.slice(0,prefix.length).concat(s.e20);s.e50=old.e50.slice(0,prefix.length).concat(s.e50)}
  for(const c of old.cs){const last=s.cs.at(-1);if(c[0]<last[0])continue;if(c[0]===last[0]){last[2]=Math.max(last[2],c[2]);last[3]=Math.min(last[3],c[3]);if(newer)last[4]=c[4]}
   else if(newer){s.cs.push(c.slice());s.provisional=true}ema(s,20);ema(s,50)}if(newer)s.lastMs=old.lastMs;if(s.cs.length>600){const n=s.cs.length-600;s.cs.splice(0,n);s.e20.splice(0,n);s.e50.splice(0,n)}return s}
 // Một mã/khung đang tải chỉ dùng một GET, tối đa 3 GET lịch sử cùng lúc.
 const flights=new Map(),queue=[],cache=new window.DKQuickLRU({maxSize:12,maxAge:30000});let active=0;
 function pump(){while(active<3&&queue.length){const job=queue.shift();active++;const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),15000);
   fetch(job.url,{cache:'no-store',signal:ctl.signal}).then(async r=>{if(!r.ok)throw Error((await r.text()).slice(0,240));return r.json()}).then(j=>{snapshot(j,job.tf);cache.set(job.key,j);job.resolve(j)},job.reject).catch(job.reject).finally(()=>{clearTimeout(timer);active--;flights.delete(job.key);pump()})}}
 function load(ma,tf){const key=ma+'|'+tf;if(flights.has(key))return flights.get(key);let resolve,reject;const p=new Promise((a,b)=>{resolve=a;reject=b});flights.set(key,p);queue.push({key,tf,url:'/api/gia?gon=1&tf='+encodeURIComponent(tf)+'&n=400&ma='+encodeURIComponent(ma),resolve,reject});pump();return p}
 function peek(ma,tf){return cache.get(ma+'|'+tf)}
 // Neo theo thời gian của một nến, giữ cả phần lẻ và khoảng trống bên phải khi lịch sử đổi độ dài.
 function view(cs,r){if(!cs.length||!r||!finite(r.from)||!finite(r.to))return null;const i=Math.max(0,Math.min(cs.length-1,Math.floor(r.from)));return{...r,i,t:cs[i][0],last:cs.at(-1)[0],n:cs.length}}
 function rebase(cs,v,follow=false){if(!v||!cs.length)return null;const i=cs.findIndex(c=>c[0]===v.t);if(i<0)return null;const end=cs.findIndex(c=>c[0]===v.last),advance=follow&&end>=0?cs.length-1-end:0,delta=i-v.i+advance;return{from:v.from+delta,to:v.to+delta}}
 return{TF,quote,candle,next,snapshot,tick,merge,load,view,rebase,peek};
})();
'''
