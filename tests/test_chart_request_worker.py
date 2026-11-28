"""Run the production request gate, chart loader and worker math in Node."""
import unittest

from so_cong_khai import bieu_do, bieu_do_chi_bao, chart_realtime
from test_bieu_do_chi_bao import VO
from test_chart_pro import node


class ChartRequests(unittest.TestCase):
    def test_queued_stream_callback_cannot_reenter_after_A_B_A(self):
        start = bieu_do.JS.index('function sgDong(')
        end = bieu_do.JS.index('// hẹn vẽ:', start)
        result = node(chart_realtime.JS + '''
let ES=null,esKhoa='',SG=null,LECH=null,sgMS=0,ma='A',tf='M15',esLoi=0;
const D={nguon:'mt5'},document={visibilityState:'visible'},sgK=()=>ma+'|'+tf,srcVe=()=>{},sgHen=()=>{},seen=[];
const sgAp=x=>{seen.push(x.bid);return true},ptTheoTick=()=>seen.push('plan'),aiTheoGia=()=>{};
window.EventSource=class{constructor(url){this.url=url}close(){this.closed=true}};
''' + bieu_do.JS[start:end] + '''
sgMo();const old=ES.onmessage;ma='B';sgMo();ma='A';sgMo();
old({data:JSON.stringify({ms:Date.now(),bid:99,ask:100})});
ES.onmessage({data:JSON.stringify({ms:Date.now()+1,bid:10,ask:11})});
console.log(JSON.stringify(seen));
''')
        self.assertEqual(result, [10, 'plan'])

    def test_request_generation_rejects_A_B_A_and_same_key_overlap(self):
        result = node(chart_realtime.JS + '''
const gate=CHART_RT.latest(),a1=gate.begin('A'),b=gate.begin('B'),a2=gate.begin('A');
const before=[gate.current(a1),gate.current(b),gate.current(a2),a1.signal.aborted,b.signal.aborted];
const a3=gate.begin('A');gate.cancel();console.log(JSON.stringify({before,last:gate.current(a3),aborted:a3.signal.aborted}));
''')
        self.assertEqual(result, {'before': [False, False, True, True, True], 'last': False, 'aborted': True})

    def test_real_loader_does_not_apply_late_response_or_clear_new_loading_state(self):
        start = bieu_do.JS.index('const loadGate=')
        end = bieu_do.JS.index('function apD(', start)
        code = bieu_do.JS[start:end]
        result = node(chart_realtime.JS + '''
window.dispatchEvent=()=>{};
let tf='M15',ma='A',D=null,ANH=false,SG=null,CBS=null,sgMS=0,sgVe=0,LECH=null,mouse=null,drag=null,sgNap=0,view={},LW=null;
const defN=()=>100;
const document={body:{}},stage={dataset:{},setAttribute(){},removeAttribute(){}},err={textContent:''},$=s=>s==='#err'?err:stage,LWO=null;
const sgK=()=>ma+'|'+tf,sgDong=()=>{},NHO=new Map(),NHO_DANG=new Map(),NHO_HAN=999999,giaU=(t,m)=>m+'|'+t;
const applied=[],waiting=[],apD=(j)=>applied.push(j.value),luuGhi=()=>{},nhoGhi=()=>{};
const napSom=(u,cu,signal)=>new Promise(resolve=>waiting.push({u,signal,resolve}));
''' + code + '''
(async()=>{const first=load();ma='B';chartSwitch();const second=load();ma='A';chartSwitch();const third=load();
 waiting[2].resolve({ok:true,text:async()=>JSON.stringify({value:'new-A'})});await third;
 stage.dataset.doi='new-state';waiting[0].resolve({ok:true,text:async()=>JSON.stringify({value:'old-A'})});await first;
 waiting[1].resolve({ok:true,text:async()=>JSON.stringify({value:'old-B'})});await second;
 console.log(JSON.stringify({applied,state:stage.dataset.doi,aborted:waiting.map(x=>x.signal.aborted)}))})();
''')
        self.assertEqual(result['applied'], ['new-A'])
        self.assertEqual(result['state'], 'new-state')
        self.assertEqual(result['aborted'], [True, True, False])

    def test_worker_uses_exact_indicator_formulas_for_full_and_tail_output(self):
        result = node(VO + bieu_do_chi_bao.JS + '''
const bars=Array.from({length:260},(_,i)=>[100000+i*900,100+Math.sin(i*.2),102+Math.sin(i*.2),98+Math.sin(i*.2),100+Math.cos(i*.2)]),
 vol=Object.fromEntries(bars.map((r,i)=>[r[0],100+i%37])),specs=Object.entries(CBCN.LIB).map(([k,v])=>({id:k,k,p:Object.fromEntries(v.ts.map(x=>[x[0],x[2]]))}));
let message;globalThis.self={postMessage:x=>message=x};
''' + bieu_do_chi_bao.WORKER_JS + '''
const H=bars.map(r=>r[2]),L=bars.map(r=>r[3]),C=bars.map(r=>r[4]),O=bars.map(r=>r[1]),V=bars.map(r=>vol[r[0]]),T=bars.map(r=>r[0]);
self.onmessage({data:{id:1,cs:bars,vol,specs,from:0}});const full=message;
self.onmessage({data:{id:2,cs:bars,vol,specs,from:258}});const tail=message;
const mismatches=[];for(const x of specs){const expected=CBCN.LIB[x.k].tinh(H,L,C,O,x.p,V,T),a=full.items.find(i=>i.id===x.id),b=tail.items.find(i=>i.id===x.id);
 if(a.error||b.error){mismatches.push(x.k+':error');continue}expected.forEach((out,j)=>{const start=['zz','frac','rsipk'].includes(x.k)?0:258;
 if(JSON.stringify(a.out[j].values)!==JSON.stringify(out[1])||JSON.stringify(b.out[j].values)!==JSON.stringify(out[1].slice(start)))mismatches.push(x.k+':'+j)})}
console.log(JSON.stringify({count:specs.length,mismatches,tail:tail.items.find(x=>x.id==='ema').out[0].values.length}));
''')
        self.assertGreater(result['count'], 40)
        self.assertEqual(result['mismatches'], [])
        self.assertEqual(result['tail'], 2)


if __name__ == '__main__':
    unittest.main()
