"""Đối chiếu phương án đã phân tích với Bid/Ask hiện tại trong trình duyệt."""

import math
from datetime import datetime, timezone


def dat_gia(loai: str, huong: str, vao: float, sl: float, tp: float, bid: float, ask: float,
            atr: float | None = None, moc: float | None = None) -> bool:
    """Cổng khoảng cách cho nhật ký và phép đo. Giữ mức chờ và giá tham chiếu đã chốt."""
    try:
        if not all(math.isfinite(x) and x > 0 for x in (vao, sl, tp, bid, ask)) or bid > ask:
            return False
        dau = 1 if huong == 'MUA' else -1 if huong in ('BAN', 'BÁN') else 0
        px, ra = (ask, bid) if dau > 0 else (bid, ask)
        rui = (vao - sl) * dau
        if rui <= 0 or (tp - vao) * dau <= 0 or (ra - sl) * dau <= 0 or (tp - ra) * dau <= 0:
            return False
        xa = min(atr, rui) if atr and math.isfinite(atr) and atr > 0 else rui
        if loai == 'gh':
            return 0 < (px - vao) * dau <= xa
        if loai == 'dung':
            return 0 < (vao - px) * dau <= xa
        return abs(px - (moc if moc is not None else vao)) <= .25 * xa and ask - bid <= .15 * abs(px - sl)
    except (TypeError, ValueError):
        return False


def ghi_duoc(p: dict, pt: dict, now: datetime) -> bool:
    tt = p.get('thuc_thi')
    if not tt:
        return True  # dữ liệu luật cũ chưa có thông tin thực thi có cấu trúc
    try:
        gia_luc = (datetime.fromtimestamp(pt['tick_ms'] / 1000, timezone.utc) if 'tick_ms' in pt
                   else datetime.fromisoformat(pt['het']))
        if pt.get('nguon') != 'mt5' or not -5 <= (now - gia_luc).total_seconds() <= 15:
            return False
        if tt.get('het') and now > datetime.fromisoformat(tt['het']):
            return False
        return dat_gia(tt['loai'], p['huong'], p['vao'], p['sl'], p['tp'][-1], pt['bid'], pt['ask'],
                       tt.get('atr') or (pt.get('boi_canh') or {}).get('atr_m15'), tt.get('moc'))
    except (ValueError, KeyError, TypeError):
        return False


JS = r"""
window.ENTRY_RT=(()=>{
 const so=Number.isFinite;
 const quoteAge=15000;
 function xem(p,q,now,atr,soLe,ket){
  if(!p?.co)return p;
  const ext=p.thuc_thi||{},side=p.huong==='MUA'?1:p.huong==='BAN'||p.huong==='BÁN'?-1:0;
  const loai=ext.loai||((p.con_phut!=null)?'gh':'tt'),stop=loai==='dung',cho=loai==='gh'||stop;
  const tp=Array.isArray(p.tp)?p.tp:[],muc=p.vao,rui=Math.abs(muc-p.sl);
  const han=Date.parse(ext.het||''),den=Date.parse(ext.tu||p.nen||'');
  const id=[q?.ma||'',p.ma,side,loai,ext.tu||p.nen||'',cho?muc:''].join('|');
  const da=Number.isInteger(soLe)?Math.max(0,Math.min(12,soLe)):2;
  const doi=(rt,them={})=>({...p,...them,rt,loai_vao:loai,hieu_luc:rt==='san_sang'});
  if(!p.hieu_luc&&!(p.quan_sat&&ext.cho_tick))return doi('tham_khao');
  if(!side)return doi('sai_muc');
  if(so(han)&&now>han)return doi('het_han');
  if(ket?.has(id))return doi(ket.get(id));
  if(!q||!so(q.ms)||!so(q.bid)||!so(q.ask)||q.bid<=0||q.ask<q.bid||now-q.ms>quoteAge||q.ms-now>5000||(so(den)&&q.ms<den))return doi('gia_cu');
  const vao=side>0?q.ask:q.bid,ra=side>0?q.bid:q.ask,d=side*(vao-muc),kc=Math.abs(d);
  const A=so(atr)&&atr>0?atr:null;
  const voHieu=(tt)=>{if(ket&&(so(den)||cho))ket.set(id,tt);return doi(tt)};
  if(ext.ngan){
   const {day,dinh,buoc}=ext.ngan;
   if(!A||!so(ext.moc)||!so(day)||!so(dinh)||!so(buoc)||buoc<=0)return doi('sai_muc');
   if(Math.abs(q.bid-ext.moc)>.25*A)return doi('gia_di_xa');
   const sp=q.ask-q.bid;if(sp>.15*A)return doi('spread');
   const step=(x,len)=>Number(((len?Math.ceil(x/buoc-1e-8):Math.floor(x/buoc+1e-8))*buoc).toFixed(da));
   const mua=side>0,gia=step(vao,mua),sl=step(mua?Math.min(day-.12*A,gia-.65*A):Math.max(dinh+.12*A,gia+.65*A),!mua);
   const risk=Math.abs(gia-sl),dich=step(gia+side*1.5*risk,mua);
   if(Math.min(gia,sl,dich)<=0||risk<=0||risk>2.5*A||side*(ra-sl)<=0)return doi('sai_muc');
   if(sp>.15*risk)return doi('spread');
   return doi('san_sang',{vao:gia,sl,tp:[dich],rui_ro_gia:risk,rr:[Math.round(Math.abs(dich-gia)/risk*100)/100]});
  }
  if(!so(rui)||rui<=0||side*(muc-p.sl)<=0||!tp.length||tp.some(t=>!so(t)||side*(t-muc)<=0))return doi('sai_muc');
  if(side*(ra-p.sl)<=0)return voHieu('cham_sl');
  if(cho){
   if((stop&&d>=0)||(!stop&&d<=0))return voHieu('da_cham');
   if(side*(ra-tp.at(-1))>=0)return voHieu('cham_tp');
   return doi(kc>(A?Math.min(A,rui):rui)?'cho_xa':'cho_gia');
  }
  if(side*(ra-tp.at(-1))>=0)return voHieu('cham_tp');
  if(Math.abs(vao-(so(ext.moc)?ext.moc:muc))>(A?Math.min(.25*A,.25*rui):.25*rui)||side*(tp[0]-vao)<=0)return doi('gia_di_xa');
  if(q.ask-q.bid>.15* Math.abs(vao-p.sl))return doi('spread');
  const entry=Number(vao.toFixed(da));
  if(side*(entry-p.sl)<=0)return doi('sai_muc');
  const risk=Math.abs(entry-p.sl);
  const targets=ext.theo_r&&p.rr?.length===tp.length
     ?p.rr.map(r=>Number((entry+side*r*risk).toFixed(da))):tp;
  if(targets.some(t=>!so(t)||side*(t-entry)<=0))return doi('sai_muc');
  return doi('san_sang',{vao:entry,tp:targets,rui_ro_gia:risk,rr:targets.map(t=>Math.round(Math.abs(t-entry)/risk*100)/100)});
 }
 return{xem};
})();
"""
