"""Mô hình replay trên nến Bid với spread/trượt giá cố định do người dùng nhập."""

JS = r"""
window.CPPL=(()=>{
 const valid=v=>Number.isFinite(v)&&v>=0;
 function chiPhi(c={}){if(!c||typeof c!=='object'||Array.isArray(c))return null;const x={spread:c.spread??0,slip:c.slip??0,phi_r:c.phi_r??0};
  return valid(x.spread)&&valid(x.slip)&&valid(x.phi_r)&&x.spread<=1e8&&x.slip<=1e8&&x.phi_r<=100?x:null}
 function vao(bid,len,atr,sl,tp,c){const costs=chiPhi(c);if(!costs||!Number.isFinite(bid)||bid<=0||!Number.isFinite(atr)||atr<=0||!Number.isFinite(sl)||sl<.2||sl>1000||!Number.isFinite(tp)||tp<.5||tp>1000)return null;
  const rui=sl*atr,sign=len?1:-1,price=bid+(len?costs.spread:0)+sign*costs.slip;
  // SL phải ở phía hợp lệ của giá đóng vị thế ngay tại thời điểm vào.
  if(!Number.isFinite(rui)||rui<=costs.spread+costs.slip||price<=0)return null;
  const stop=price-sign*rui,target=price+sign*tp*rui;
  if(![stop,target].every(Number.isFinite)||stop<=0||target<=0)return null;
  return{len:!!len,vao:price,vao_bid:bid,rui,sl:stop,tp:target,chi_phi:{...costs},mo_hinh:'bid-ask-cost-v1'}}
 function dong(l,bid){const c=chiPhi(l.chi_phi),sign=l.len?1:-1;
  if(!c||!Number.isFinite(bid)||!Number.isFinite(l.rui)||l.rui<=0)return null;
  const ra=bid+(l.len?0:c.spread)-sign*c.slip,goc=(bid-l.vao_bid)*sign/l.rui,cost=(c.spread+2*c.slip)/l.rui+c.phi_r;
  return{ra,ra_bid:bid,r_goc:goc,chi_phi_r:cost,r_truoc_phi:(ra-l.vao)*sign/l.rui,r:goc-cost}}
 function kiem(l,c){const costs=chiPhi(l.chi_phi);if(!costs||!Array.isArray(c)||c.length<5||!c.every(Number.isFinite))return null;
  const sp=l.len?0:costs.spread,o=c[1]+sp,h=c[2]+sp,lo=c[3]+sp;let p,ly;
  if(l.len?o<=l.sl:o>=l.sl){p=o;ly='SL'}else if(l.len?o>=l.tp:o<=l.tp){p=o;ly='TP'}
  else if(l.len?lo<=l.sl:h>=l.sl){p=l.sl;ly='SL'}else if(l.len?h>=l.tp:lo<=l.tp){p=l.tp;ly='TP'}else return null;
  return{gia_bid:p-sp,ly}}
 return{chiPhi,vao,dong,kiem};
})();
"""
