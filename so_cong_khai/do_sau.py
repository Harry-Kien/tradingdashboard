"""Độ sâu thị trường (sổ lệnh) của mã đang xem trên trang Biểu đồ (26/11/2026).

Đọc sổ lệnh mà SÀN của người dùng gửi về MT5 (market_book_get), chỉ đọc: đăng ký nhận sổ lệnh của mã, không đặt lệnh nào. Đây là sổ lệnh của riêng
sàn đó, không phải của cả thị trường (vàng và forex không có sàn tập trung). Sàn không gửi sổ lệnh, hoặc không gửi khối lượng, thì trang nói rõ,
không bịa số. Trang hỏi /api/so-lenh mỗi giây, và chỉ khi ô này đang nằm trong màn hình."""
from __future__ import annotations

import time

from . import song

TOI_DA_MA = 6              # số mã giữ đăng ký sổ lệnh cùng lúc; quá thì nhả mã cũ nhất
SO_MUC = 10                # số mức giá mỗi bên trả về trang
_dk: dict[str, float] = {}


def doc(g: dict, ma: str | None = None) -> dict:
    """Sổ lệnh của một mã: {'san_sang', 'ma', 'so_le', 'ban': [[giá, khối lượng]…] (gần giá nhất trước), 'mua': […], 'co_kl'}."""
    if song.khung_song(g) is None:
        return {'san_sang': False, 'ly_do': f'Chưa có giá trực tiếp từ MT5 ({song.ly_do() or "chưa nối"}).'}
    with song._khoa:
        mt5 = song._tt.get('mt5')
        if mt5 is None:
            return {'san_sang': False, 'ly_do': 'Chưa nối MT5.'}
        goc = getattr(mt5, 'mt5', mt5)                           # lớp bọc đổi giờ giữ mô-đun MT5 thật
        sym = ma or song._tt.get('sym')
        try:
            moi = sym not in _dk
            if moi:
                if not goc.market_book_add(sym):
                    return {'san_sang': False, 'ma': sym, 'ly_do': 'Sàn của bạn không gửi sổ lệnh cho mã này.'}
                while len(_dk) >= TOI_DA_MA:
                    cu = min(_dk, key=_dk.get)
                    _dk.pop(cu)
                    try:
                        goc.market_book_release(cu)
                    except Exception:                            # noqa: BLE001, S110 - nhả đăng ký hỏng thì bỏ qua
                        pass
            _dk[sym] = time.monotonic()
            b = goc.market_book_get(sym)
            tt = goc.symbol_info(sym)
        except Exception as e:                                   # noqa: BLE001
            return {'san_sang': False, 'ma': sym, 'ly_do': f'Không đọc được sổ lệnh: {type(e).__name__}'}
    d = int(getattr(tt, 'digits', 2) or 2)
    if not b:
        return {'san_sang': False, 'ma': sym, 'dang_cho': moi, 'ly_do': 'Đang chờ sàn gửi sổ lệnh…' if moi else 'Sàn của bạn không gửi sổ lệnh cho mã này.'}
    ban = sorted(([round(float(x.price), d), float(getattr(x, 'volume_dbl', 0) or x.volume)] for x in b if int(x.type) == 1), key=lambda r: r[0])
    mua = sorted(([round(float(x.price), d), float(getattr(x, 'volume_dbl', 0) or x.volume)] for x in b if int(x.type) == 2), key=lambda r: -r[0])
    return {'san_sang': True, 'ma': sym, 'so_le': d, 'ban': ban[:SO_MUC], 'mua': mua[:SO_MUC], 'co_kl': any(r[1] > 0 for r in ban + mua)}


CSS = r"""
.dsau h3{margin:0 0 4px}.dsau .why{margin:2px 0 8px}
.dsau-b{display:grid;gap:1px;font-variant-numeric:tabular-nums;font-size:12.5px}
.dsau-h{display:grid;grid-template-columns:1fr 1fr;position:relative;padding:2px 8px;border-radius:4px;overflow:hidden}
.dsau-h i{position:absolute;top:0;bottom:0;right:0;opacity:.2;pointer-events:none}
.dsau-h.ban i{background:var(--loss)}.dsau-h.mua i{background:var(--gain)}
.dsau-h span{position:relative}.dsau-h span:last-child{text-align:right;color:var(--ink2)}
.dsau-h.ban span:first-child{color:var(--loss)}.dsau-h.mua span:first-child{color:var(--gain)}
.dsau-g{display:flex;justify-content:space-between;padding:5px 8px;margin:3px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);font-size:12px;color:var(--ink2)}
.dsau-g b{color:var(--ink)}
.dsau-cb{display:flex;height:8px;border-radius:999px;overflow:hidden;margin:8px 0 4px;background:var(--card2)}
.dsau-cb i:first-child{background:var(--gain)}.dsau-cb i:last-child{background:var(--loss)}
.dsau-ct{display:flex;justify-content:space-between;font-size:12px;color:var(--ink2)}
"""

JS = r"""
(()=>{const G=window.BDMN;if(!G)return;const ch=document.querySelector('.duoi .cum')||document.querySelector('.duoi');if(!ch)return;
const P=document.createElement('aside');P.className='panel side dsau';P.id='dsau';P.setAttribute('aria-label','Độ sâu thị trường');ch.appendChild(P);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const gon=v=>v>=1e6?(v/1e6).toLocaleString('vi-VN',{maximumFractionDigits:1})+'M':v>=1e3?(v/1e3).toLocaleString('vi-VN',{maximumFractionDigits:1})+'K':v.toLocaleString('vi-VN',{maximumFractionDigits:2});
let thay=false,dang=false;
function ve(j){const dau='<h3>Độ sâu thị trường</h3>';
 if(!j||!j.san_sang){P.innerHTML=dau+`<p class="why">${esc((j&&j.ly_do)||'Chưa đọc được sổ lệnh.')}</p>`;return}
 const fp=v=>Number(v).toLocaleString('vi-VN',{minimumFractionDigits:j.so_le,maximumFractionDigits:j.so_le}),ban=j.ban||[],mua=j.mua||[],mx=Math.max(1,...ban.map(r=>r[1]),...mua.map(r=>r[1]));
 const hang=(r,l)=>`<div class="dsau-h ${l}"><i style="width:${j.co_kl?Math.round(r[1]/mx*100):0}%"></i><span>${fp(r[0])}</span><span>${j.co_kl?gon(r[1]):'—'}</span></div>`;
 const tb=mua.reduce((s,r)=>s+r[1],0),ts=ban.reduce((s,r)=>s+r[1],0),tong=tb+ts,ask=ban[0]&&ban[0][0],bid=mua[0]&&mua[0][0];
 let s=dau+`<p class="why">Sổ lệnh sàn của bạn gửi về MT5 cho ${esc(j.ma)}: ${ban.length} mức bán, ${mua.length} mức mua gần giá nhất. Đây là sổ lệnh của riêng sàn này, không phải của cả thị trường.</p>`;
 s+='<div class="dsau-b">'+ban.slice().reverse().map(r=>hang(r,'ban')).join('')
  +`<div class="dsau-g"><span>Chênh mua bán</span><b>${ask!=null&&bid!=null?fp(ask-bid):'—'}</b></div>`+mua.map(r=>hang(r,'mua')).join('')+'</div>';
 if(j.co_kl&&tong>0)s+=`<div class="dsau-cb"><i style="width:${Math.round(tb/tong*100)}%"></i><i style="width:${100-Math.round(tb/tong*100)}%"></i></div>`
  +`<div class="dsau-ct"><span>Chờ mua ${gon(tb)} (${Math.round(tb/tong*100)}%)</span><span>Chờ bán ${gon(ts)} (${100-Math.round(tb/tong*100)}%)</span></div>`
  +'<p class="why">Khối lượng chờ nghiêng về một bên chỉ mô tả sổ lệnh lúc này, không phải tín hiệu vào lệnh.</p>';
 else if(!j.co_kl)s+='<p class="why">Sàn không gửi khối lượng cho mã này, nên chỉ có các mức giá.</p>';
 P.innerHTML=s}
async function tai(){if(dang||!thay||document.visibilityState!=='visible'||window.PHAT_LAI)return;dang=true;const ma=G().ma||'';
 try{const r=await fetch('/api/so-lenh'+(ma?'?ma='+encodeURIComponent(ma):''),{cache:'no-store'});const j=await r.json();if((G().ma||'')===ma)ve(j)}catch(e){ve({san_sang:false,ly_do:'Không gọi được webapp.'})}dang=false}
ve({san_sang:false,ly_do:'Kéo tới đây thì bảng bắt đầu đọc sổ lệnh.'});
if(window.IntersectionObserver)new IntersectionObserver(es=>{thay=es.some(e=>e.isIntersecting);if(thay)tai()}).observe(P);else thay=true;
setInterval(tai,1000)})();
"""
