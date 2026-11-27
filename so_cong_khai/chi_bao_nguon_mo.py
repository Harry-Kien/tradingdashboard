"""Bộ chỉ báo MIT đã chọn và khóa commit; cùng mã chạy trên UI và worker."""
from pathlib import Path

THU_MUC = Path(__file__).resolve().parent.parent / 'tinh' / 'chi-bao-oss-1.0.0'
BUNDLE = (THU_MUC / 'indicators.js').read_text(encoding='utf-8')
NOTICE_HTML = ('<p>Chỉ báo bổ sung sử dụng <a href="https://github.com/cinar/indicatorts" target="_blank" rel="noopener">indicatorts</a> '
               '(Copyright © 2022–2026 The Indicator Authors) và <a href="https://github.com/anandanand84/technicalindicators" target="_blank" rel="noopener">technicalindicators</a> '
               '(Copyright © 2016 Anand Aravindan), giấy phép MIT. Mã nguồn, giấy phép và commit được giữ trong gói ứng dụng.</p>')

ADAPTER_JS = r"""
globalThis.HGR_OSS_EXT=(()=>{
 const F=HGR_OSS,finite=Number.isFinite,lim=(v,d,lo=1,hi=1000)=>finite(+v)?Math.max(lo,Math.min(hi,+v)):d,n=(v,d)=>Math.trunc(lim(v,d));
 function entries(L_){
  const make=(ten,nhom,khung,ts,mo,names,calc,warm=()=>0,volume=false,muc)=>({ten,nhom,khung,ts,mo,nguon:'oss',muc,
   tinh(H,L,C,O,p={},V){const size=C.length,wait=Math.max(0,Math.trunc(warm(p))),out=names.map(()=>Array(size).fill(null));
    const apply=(a,b)=>{if(b-a<=wait)return;const values=calc({H:H.slice(a,b),L:L.slice(a,b),C:C.slice(a,b),O:O.slice(a,b),V:V?V.slice(a,b):[],p});
     for(let j=0;j<out.length;j++)for(let i=wait;i<b-a;i++)if(finite(values[j]?.[i]))out[j][a+i]=values[j][i]};
    if(volume){let a=0;while(a<size){while(a<size&&(!finite(V?.[a])||V[a]<0))a++;let b=a;while(b<size&&finite(V?.[b])&&V[b]>=0)b++;if(b>a)apply(a,b);a=b+1}}
    else if(size>wait)apply(0,size);
    return names.map((s,j)=>L_(s[0],out[j],s[1]))}
  });
  const period=d=>[['n','Chu kỳ',d,1]],volNote=' Dùng tick volume MT5; không có dữ liệu khối lượng thì để trống.',w=p=>n(p.n,14)-1;
  const lib={
   oss_t3:make('Tillson T3','xu','gia',[...period(5),['a','Hệ số',.7,.05,0,1]],'Trung bình T3 làm trơn qua sáu EMA; hệ số từ 0 đến 1.',[['T3']],({C,p})=>[F.t3(C,{period:n(p.n,5),volumeFactor:lim(p.a,.7,0,1)})],p=>6*(n(p.n,5)-1)),
   oss_trima:make('Triangular MA (TRIMA)','xu','gia',period(20),'Trung bình tam giác, làm trơn giá đóng theo hai lớp SMA.',[['TRIMA']],({C,p})=>[F.trima(C,{period:n(p.n,20)})],p=>n(p.n,20)-1),
   oss_ab:make('Acceleration Bands','bien','gia',[...period(20),['k','Hệ số',4,.1,.1,20]],'Dải tăng tốc theo biên cao/thấp và SMA; không phải dự báo chắc chắn hướng giá.',[['AB upper'],['AB middle'],['AB lower']],({H,L,C,p})=>{const r=F.ab(H,L,C,{period:n(p.n,20),multiplier:lim(p.k,4,.1,20)});return[r.upper,r.middle,r.lower]},p=>n(p.n,20)-1),
   oss_apo:make('Absolute Price Oscillator (APO)','dao','rieng',[['f','Nhanh',12,1],['s','Chậm',26,1]],'Chênh lệch EMA nhanh và chậm, tính bằng đơn vị giá.',[['APO']],({C,p})=>[F.apo(C,{fast:n(p.f,12),slow:n(p.s,26)})],p=>Math.max(n(p.f,12),n(p.s,26))-1,false,[0]),
   oss_qstick:make('Qstick','dao','rieng',period(14),'SMA của giá đóng trừ giá mở; đo hướng và độ lớn thân nến.',[['Qstick']],({O,C,p})=>[F.qstick(O,C,{period:n(p.n,14)})],w,false,[0]),
   oss_slope:make('Độ dốc giá (Slope)','xu','rieng',period(14),'Chênh lệch giá đóng trong n nến chia cho n; không phải độ dốc hồi quy.',[['Slope']],({C,p})=>[F.slope(C,{period:n(p.n,14)})],p=>n(p.n,14),false,[0]),
   oss_cfo:make('Chande Forecast Oscillator (CFO)','dao','rieng',[['n','Chu kỳ',14,1,2]],'Độ lệch giá so với hồi quy trên cửa sổ trượt; chỉ dùng dữ liệu đến cây nến đang xét.',[['CFO']],({C,p})=>[F.mcfo(C,{period:Math.max(2,n(p.n,14))})],p=>Math.max(2,n(p.n,14))-1,false,[0]),
   oss_ui:make('Ulcer Index','bien','rieng',period(14),'Đo mức sụt giảm từ đỉnh giá đóng gần đây; số cao biểu thị rủi ro sụt giảm lớn hơn.',[['Ulcer Index']],({C,p})=>[F.ui(C,{period:n(p.n,14)})],p=>2*(n(p.n,14)-1)),
   oss_percentb:make('Bollinger %B','bien','rieng',period(20),'Vị trí giá trong dải Bollinger hai độ lệch chuẩn; 0 là dải dưới, 100 là dải trên.',[['%B']],({C,p})=>[F.percentB(C,{period:n(p.n,20)}).map(v=>v*100)],p=>n(p.n,20)-1,false,[0,100]),
   oss_po:make('Projection Oscillator','dao','rieng',[['n','Chu kỳ',14,1,2],['s','Làm trơn',3,1]],'Vị trí giá trong biên chiếu từ hồi quy cao/thấp của cửa sổ trượt.',[['PO'],['PO signal']],({H,L,C,p})=>{const r=F.po(H,L,C,{period:Math.max(2,n(p.n,14)),smooth:n(p.s,3)});return[r.poResult,r.spoResult]},p=>Math.max(2,n(p.n,14))-1,false,[20,80]),
   oss_ibs:make('Internal Bar Strength (IBS)','dao','rieng',[],'Vị trí giá đóng trong biên cao/thấp của chính nến, từ 0 đến 100.',[['IBS']],({H,L,C})=>[F.ibs(H,L,C).map(v=>100*v)],()=>0,false,[20,80]),
   oss_specialk:make('Pring Special K','dao','rieng',[],'Động lượng kết hợp 12 chu kỳ. Cần ít nhất 725 nến để có giá trị đầy đủ.',[['Special K']],({C})=>[F.specialK(C)],()=>724,false,[0]),
   oss_force:make('Force Index','kl','rieng',period(13),'EMA của biến động giá đóng nhân khối lượng.'+volNote,[['Force Index']],({C,V,p})=>[F.fi(C,V,{period:n(p.n,13)})],p=>n(p.n,13),true,[0]),
   oss_emv:make('Ease of Movement (EMV)','kl','rieng',period(14),'Độ dịch chuyển giá giữa nến so với khối lượng và biên nến.'+volNote,[['EMV']],({H,L,V,p})=>[F.emv(H,L,V,{period:n(p.n,14)})],w,true,[0]),
   oss_chaikin:make('Chaikin Oscillator','kl','rieng',[['f','Nhanh',3,1],['s','Chậm',10,1]],'Chênh lệch EMA nhanh và chậm của đường tích lũy/phân phối.'+volNote,[['Chaikin']],({H,L,C,V,p})=>[F.co(H,L,C,V,{fast:n(p.f,3),slow:n(p.s,10)}).coResult],p=>Math.max(n(p.f,3),n(p.s,10))-1,true,[0]),
   oss_pvo:make('Percentage Volume Oscillator (PVO)','kl','rieng',[['f','Nhanh',12,1],['s','Chậm',26,1],['g','Tín hiệu',9,1]],'Chênh lệch hai EMA khối lượng theo phần trăm, kèm tín hiệu và histogram.'+volNote,[['PVO'],['PVO signal'],['PVO histogram','cot']],({V,p})=>{const r=F.pvo(V,{fast:n(p.f,12),slow:n(p.s,26),signal:n(p.g,9)});return[r.pvoResult,r.signal,r.histogram]},p=>Math.max(n(p.f,12),n(p.s,26))+n(p.g,9)-2,true,[0]),
   oss_vpt:make('Volume Price Trend (VPT)','kl','rieng',[],'Cộng dồn khối lượng nhân tỷ lệ thay đổi giá đóng.'+volNote,[['VPT']],({C,V})=>[F.vpt(C,V)],()=>1,true),
   oss_nvi:make('Negative Volume Index (NVI)','kl','rieng',[['b','Giá trị gốc',1000,1,1,1e9]],'Chỉ tích lũy thay đổi giá khi khối lượng giảm so với nến trước.'+volNote,[['NVI']],({C,V,p})=>[F.nvi(C,V,{start:lim(p.b,1000,1,1e9)})],()=>1,true),
  };
  lib.oss_candles={ten:'Mẫu nến Nhật (27 mẫu)','nhom':'cd',khung:'gia',nguon:'oss',ts:[['n','Số nến quét gần nhất',500,50,50],['c','Chờ nến kế tiếp (1 có, 0 không)',1,1,0,1],['l','Hiện tên mẫu (1 có, 0 không)',0,1,0,1]],
   mo:'Nhận diện 27 mẫu nến theo quy tắc nguồn mở. Mặc định bỏ nến cuối và chỉ xác nhận sau khi có nến kế tiếp; mẫu nến không bảo đảm giá sẽ đảo chiều.',
   tinh(H,L,C,O,p={}){const size=C.length,marks=[[],[]],end=lim(p.c,1,0,1)>0?size-1:size,start=Math.max(0,end-Math.trunc(lim(p.n,500,50,1000)));
    for(let i=start;i<end;i++){const found=[[],[]];for(const x of F.candlePatterns){const k=x.detector.requiredCount,a=i-k+1;if(a<0)continue;
      const data={open:O.slice(a,i+1),high:H.slice(a,i+1),low:L.slice(a,i+1),close:C.slice(a,i+1)};
      if(data.open.some((v,j)=>!finite(v)||!finite(data.high[j])||!finite(data.low[j])||!finite(data.close[j])||data.high[j]<Math.max(v,data.close[j])||data.low[j]>Math.min(v,data.close[j])))continue;
      if(x.detector.hasPattern(data))found[x.len?0:1].push(x.name.replace(/Pattern$/,'').replace(/([a-z])([A-Z])/g,'$1 $2'))}
     for(let j=0;j<2;j++)if(found[j].length)marks[j].push({i,len:j===0,text:lim(p.l,0,0,1)>0?found[j].slice(0,2).join(' / '):'',patterns:found[j]})}
    return[[...L_('Mẫu nến tăng',L,'dau'),marks[0]],[...L_('Mẫu nến giảm',H,'dau'),marks[1]]]}
  };
  return lib;
 }
 return{entries,version:'1.0.0'};
})();
"""

JS = BUNDLE + '\n' + ADAPTER_JS
