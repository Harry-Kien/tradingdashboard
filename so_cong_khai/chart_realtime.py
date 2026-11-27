"""Cập nhật chuỗi theo đuôi và đo chi phí trình duyệt, không giả làm độ trễ sàn."""

JS = r"""
window.CHART_RT=window.CHART_RT||(()=>{
 const cache=new WeakMap(),samples=[];let received=null,last=null,dropped=0;
 function gui(s,n,item,source,tail=true){if(!n)return;const old=cache.get(s);
  const incremental=tail&&old&&old.source===source&&n>=old.n&&item(old.n-1).time===old.time;
  if(incremental){try{for(let i=old.n-1;i<n;i++)s.update(item(i))}catch(e){s.setData(Array.from({length:n},(_,i)=>item(i)))}}
  else s.setData(Array.from({length:n},(_,i)=>item(i)));
  cache.set(s,{source,n,time:item(n-1).time})}
 function hopLe(x,ms){return !!x&&Number.isFinite(x.ms)&&x.ms>=0&&x.ms>=ms&&Number.isFinite(x.bid)&&x.bid>0&&Number.isFinite(x.ask)&&x.ask>=x.bid&&
  (!x.nen||(Array.isArray(x.nen)&&x.nen.length===5&&x.nen.every(Number.isFinite)&&x.nen[0]>0&&x.nen[2]>=Math.max(x.nen[1],x.nen[4])&&x.nen[3]<=Math.min(x.nen[1],x.nen[4])&&x.nen[2]>=x.nen[3]))}
 function nhan(){const now=performance.now();if(received==null)received=now;last=now}
 function xong(){if(received==null)return;samples.push(Math.max(0,performance.now()-received));if(samples.length>120)samples.shift();received=null}
 function thongTin(){const sorted=samples.slice().sort((a,b)=>a-b);return{so_mau:samples.length,p95:sorted.length?sorted[Math.ceil(sorted.length*.95)-1]:null,
  gan_nhat:samples.length?samples[samples.length-1]:null,im_ms:last==null?null:Math.max(0,performance.now()-last),bo:dropped}}
 function latest(){let serial=0,active=null;return{
  begin(key){if(active)active.controller.abort();const controller=new AbortController();active={key,id:++serial,controller,signal:controller.signal};return active},
  current(ticket){return !!ticket&&active===ticket&&!ticket.signal.aborted},
  cancel(){if(active)active.controller.abort();active=null;serial++}}}
 return{gui,hopLe,nhan,xong,boTick:()=>dropped++,thongTin,latest};
})();
"""
