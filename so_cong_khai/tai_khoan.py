"""Xem tài khoản MT5 đang nối, CHỈ ĐỌC: số dư, vốn, ký quỹ, lệnh đang mở, lệnh chờ, lịch sử khớp lệnh và rủi ro nếu mọi SL bị chạm.

Dùng chung phiên nối an toàn của song.py: chỉ nối vào MT5 đang mở ở đường dẫn đã khai, không tự mở MT5, không nhập mật khẩu.
Mô-đun chỉ gọi các hàm đọc của MT5 (account_info, positions_get, orders_get, history_deals_get, symbol_info) và không có lời gọi
đặt, sửa hay đóng lệnh nào. Chỉ đọc tài khoản DEMO: gặp tài khoản khác thì từ chối và nói rõ. Số tài khoản được che, chỉ để lại
ba chữ số cuối; tên chủ tài khoản không được đọc ra trang."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape

from . import da_ma, song, trang
from .doc_so import VN

EA_THEO_MAGIC = {20261026: 'EA E', 20261028: 'EA I', 20261030: 'EA BB'}
LOAI_TIEN = {2: 'Nạp hoặc rút', 3: 'Tín dụng', 4: 'Phí', 5: 'Điều chỉnh', 6: 'Thưởng'}
LOAI_CHO = {2: 'MUA giới hạn', 3: 'BÁN giới hạn', 4: 'MUA dừng', 5: 'BÁN dừng', 6: 'MUA dừng giới hạn', 7: 'BÁN dừng giới hạn'}


def _mt5(g: dict):
    """Phiên MT5 đang nối (None nếu chưa nối được). Bài kiểm thay hàm này bằng một MT5 giả."""
    return da_ma._mt5(g)


def _r(x, d: int = 2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if x != x else round(x, d)


def _ea(cfg: dict, magic: int) -> str:
    ten = {int(k): v for k, v in ((cfg.get('mt5_xem') or {}).get('magic') or {}).items()}
    return ten.get(magic) or EA_THEO_MAGIC.get(magic) or ('Đặt tay' if not magic else f'EA (magic {magic})')


def _gio(t) -> str:
    return datetime.fromtimestamp(int(t), timezone.utc).isoformat()


def doc(cfg: dict, now: datetime | None = None, ngay: int = 30) -> dict:
    """Ảnh chụp tài khoản lúc này. Không nối được, hoặc tài khoản không phải demo, thì trả {'san_sang': False, 'ly_do': ...}."""
    g = cfg['gia']
    now = now or datetime.now(timezone.utc)
    mt5 = _mt5(g)
    if mt5 is None:
        return {'san_sang': False, 'ly_do': song.ly_do() or 'chưa nối được MT5'}
    with song._khoa:
        a = mt5.account_info()
        if a is None:
            return {'san_sang': False, 'ly_do': 'MT5 không trả thông tin tài khoản'}
        if int(getattr(a, 'trade_mode', -1)) != int(getattr(mt5, 'ACCOUNT_TRADE_MODE_DEMO', 0)):
            return {'san_sang': False, 'ly_do': 'Tài khoản đang nối không phải tài khoản demo. Trang này chỉ đọc tài khoản demo.'}
        so = str(a.login)
        out = {'san_sang': True, 'luc': now.isoformat(), 'loai': 'DEMO', 'so': '•••' + so[-3:], 'may_chu': a.server, 'tien': a.currency, 'don_bay': int(a.leverage),
               'so_du': _r(a.balance), 'von': _r(a.equity), 'treo': _r(a.profit), 'ky_quy': _r(a.margin), 'ky_quy_con': _r(a.margin_free),
               'muc_ky_quy': _r(a.margin_level, 1) if a.margin else None, 'lenh': [], 'cho': [], 'da_dong': [], 'nap_rut': [], 'theo_ngay': []}
        tt_ma: dict = {}

        def ma(ten):
            if ten not in tt_ma:
                tt_ma[ten] = mt5.symbol_info(ten)
            return tt_ma[ten]

        rui_ro, khong_sl, khong_tinh = 0.0, 0, 0
        for p in mt5.positions_get() or []:
            s = ma(p.symbol)
            d = int(s.digits) if s else 2
            mua = int(p.type) == 0
            rr = None
            if p.sl:
                if s and s.currency_profit == a.currency:
                    rr = abs(float(p.price_open) - float(p.sl)) * float(p.volume) * float(s.trade_contract_size)
                    # SL đã kéo qua giá vào (khóa lãi) thì chạm SL không lỗ
                    if (mua and p.sl >= p.price_open) or (not mua and p.sl <= p.price_open):
                        rr = 0.0
                    rui_ro += rr
                else:
                    khong_tinh += 1
            else:
                khong_sl += 1
            out['lenh'].append({'ma': p.symbol, 'huong': 'MUA' if mua else 'BAN', 'lot': _r(p.volume), 'vao': _r(p.price_open, d), 'gia': _r(p.price_current, d),
                                'sl': _r(p.sl, d) if p.sl else None, 'tp': _r(p.tp, d) if p.tp else None, 'lai': _r(p.profit), 'swap': _r(p.swap), 'so_le': d,
                                'mo': _gio(p.time), 'nguon': _ea(cfg, int(p.magic)), 'rui_ro': _r(rr) if rr is not None else None,
                                've': int(getattr(p, 'ticket', 0) or 0)})              # số vé: phân biệt các lệnh cùng mã mở cùng giây
        out['rui_ro'] = {'tong': _r(rui_ro), 'pct': _r(rui_ro / a.equity * 100, 2) if a.equity else None, 'khong_sl': khong_sl, 'khong_tinh': khong_tinh}
        for o in mt5.orders_get() or []:
            s = ma(o.symbol)
            d = int(s.digits) if s else 2
            out['cho'].append({'ma': o.symbol, 'loai': LOAI_CHO.get(int(o.type), f'kiểu {int(o.type)}'), 'lot': _r(o.volume_current), 'gia': _r(o.price_open, d),
                               'sl': _r(o.sl, d) if o.sl else None, 'tp': _r(o.tp, d) if o.tp else None, 'dat': _gio(o.time_setup), 'nguon': _ea(cfg, int(o.magic)), 'so_le': d})
        deals = mt5.history_deals_get(now - timedelta(days=ngay), now + timedelta(days=1)) or []
    ngay_vn: dict = {}
    for x in sorted(deals, key=lambda x: x.time):
        t = datetime.fromtimestamp(int(x.time), timezone.utc)
        if int(x.type) not in (0, 1):                              # không phải khớp lệnh: nạp, rút, điều chỉnh số dư, phí…
            out['nap_rut'].append({'luc': t.isoformat(), 'loai': LOAI_TIEN.get(int(x.type), f'Kiểu {int(x.type)}'), 'tien': _r(x.profit), 'ghi_chu': x.comment or ''})
            continue
        if int(x.entry) == 0:                                      # chỉ tính lần khớp ĐÓNG vị thế; lần khớp mở chưa có lãi lỗ
            continue
        rong = float(x.profit) + float(x.commission) + float(x.swap) + float(getattr(x, 'fee', 0.0) or 0.0)
        s = tt_ma.get(x.symbol)
        d = int(s.digits) if s else 2
        # lần khớp đóng có chiều ngược với vị thế: khớp BÁN là đóng một lệnh MUA
        out['da_dong'].append({'luc': t.isoformat(), 'ma': x.symbol, 'huong': 'MUA' if int(x.type) == 1 else 'BAN', 'lot': _r(x.volume), 'gia': _r(x.price, d),
                               'lai': _r(rong), 'nguon': _ea(cfg, int(x.magic)), 'so_le': d})
        k = t.astimezone(VN).date().isoformat()
        ngay_vn[k] = ngay_vn.get(k, 0.0) + rong
    dd = out['da_dong']
    lai = [x['lai'] for x in dd]
    out['tom'] = {'ngay': ngay, 'n': len(dd), 'thang': sum(v > 0 for v in lai), 'thua': sum(v < 0 for v in lai), 'tong': _r(sum(lai)),
                  'lai_gop': _r(sum(v for v in lai if v > 0)), 'lo_gop': _r(sum(v for v in lai if v < 0))}
    out['theo_ngay'] = [{'ngay': k, 'lai': _r(v)} for k, v in sorted(ngay_vn.items())]
    out['da_dong'] = dd[::-1][:60]                                  # mới nhất trước
    return out


def lich_su(cfg: dict, tu: datetime, now: datetime | None = None) -> dict | None:
    """Mọi lệnh đã đóng (cũ trước) và mọi thay đổi số dư từ `tu` tới nay, cùng lãi lỗ đang treo. None nếu chưa nối được MT5
    hoặc tài khoản đang nối không phải demo."""
    now = now or datetime.now(timezone.utc)
    mt5 = _mt5(cfg['gia'])
    if mt5 is None:
        return None
    with song._khoa:
        a = mt5.account_info()
        if a is None or int(getattr(a, 'trade_mode', -1)) != int(getattr(mt5, 'ACCOUNT_TRADE_MODE_DEMO', 0)):
            return None
        deals = mt5.history_deals_get(tu, now + timedelta(days=1)) or []
        treo = float(a.profit)
    out = {'da_dong': [], 'nap_rut': [], 'treo': _r(treo)}
    for x in sorted(deals, key=lambda x: x.time):
        t = datetime.fromtimestamp(int(x.time), timezone.utc)
        if int(x.type) not in (0, 1):
            out['nap_rut'].append({'luc': t.isoformat(), 'loai': LOAI_TIEN.get(int(x.type), f'Kiểu {int(x.type)}'), 'tien': _r(x.profit)})
        elif int(x.entry) != 0:
            rong = float(x.profit) + float(x.commission) + float(x.swap) + float(getattr(x, 'fee', 0.0) or 0.0)
            out['da_dong'].append({'luc': t.isoformat(), 'ma': x.symbol, 'huong': 'MUA' if int(x.type) == 1 else 'BAN', 'lot': _r(x.volume), 'gia': _r(x.price, 2),
                                   'lai': _r(rong), 'nguon': _ea(cfg, int(x.magic))})
    return out


def doi_chieu(cfg: dict, ten_ea: set, tom: dict, now: datetime | None = None, lech_giay: int = 300) -> dict | None:
    """So nhật ký sự kiện của các EA trong một tài khoản (`tom` của tong_hop.tom_tai_khoan) với lịch sử khớp lệnh của MT5.
    Ghép từng lệnh theo chiều, khối lượng và giờ đóng (lệch tối đa `lech_giay`). Trả None khi không đọc được MT5, hoặc khi MT5 đang nối
    không có lệnh nào của các EA này (tức là đang nối một tài khoản khác)."""
    now = now or datetime.now(timezone.utc)
    rows = list(tom.get('rows') or [])
    moc = [r['opened'] for r in rows + list(tom.get('orphans') or []) + list(tom.get('opens') or []) if r.get('opened')]
    dau = min(moc) if moc else now - timedelta(days=60)
    ls = lich_su(cfg, dau - timedelta(days=1), now)
    if ls is None:
        return None
    cua_ea = [x for x in ls['da_dong'] if x['nguon'] in ten_ea]
    if not cua_ea:
        return None
    con = list(cua_ea)
    cap, thieu_mt5 = [], []
    for r in sorted(rows, key=lambda r: r['closed_at']):
        huong = 'MUA' if r['side'] == 'BUY' else 'BAN'
        ung = [x for x in con if x['huong'] == huong and abs(x['lot'] - float(r['lots'])) < 0.0051
               and abs((datetime.fromisoformat(x['luc']) - r['closed_at']).total_seconds()) <= lech_giay]
        if ung:
            x = min(ung, key=lambda x: abs((datetime.fromisoformat(x['luc']) - r['closed_at']).total_seconds()))
            con.remove(x)
            cap.append((r, x))
        else:
            thieu_mt5.append({'luc': r['closed_at'].isoformat(), 'huong': huong, 'lot': _r(r['lots']), 'lai': _r(r['pnl'])})
    lech_cap = [{'luc': x['luc'], 'nhat_ky': _r(r['pnl']), 'mt5': x['lai']} for r, x in cap if abs(float(r['pnl']) - x['lai']) > 0.05]
    nap = sum(x['tien'] or 0.0 for x in ls['nap_rut'] if datetime.fromisoformat(x['luc']) >= dau)
    tong_mt5 = sum(x['lai'] for x in cua_ea)
    thay_doi = float(tom.get('equity_change') or 0.0)
    con_lech = thay_doi - (tong_mt5 + nap + (ls['treo'] or 0.0))
    return {'n_nhat_ky': len(rows), 'tong_nhat_ky': _r(sum(float(r['pnl']) for r in rows)), 'n_mt5': len(cua_ea), 'tong_mt5': _r(tong_mt5),
            'thang_mt5': sum(1 for x in cua_ea if (x['lai'] or 0) > 0), 'thua_mt5': sum(1 for x in cua_ea if (x['lai'] or 0) < 0),
            'so_cap': len(cap), 'lech_cap': lech_cap, 'thieu_nhat_ky': con, 'thieu_mt5': thieu_mt5, 'nap_rut': _r(nap), 'treo': ls['treo'],
            'von_thay_doi': _r(thay_doi), 'con_lech': _r(con_lech), 'khop': abs(con_lech) < 0.5, 'tu': dau.isoformat()}


CSS = """
.tk-top{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden;margin-top:16px}
.tk-top>div{background:var(--card);padding:12px 14px}.tk-top>div>span{display:block;color:var(--ink2);font-size:12.5px}
.tk-top b{display:block;font-size:20px;font-weight:700;line-height:1.3;font-variant-numeric:tabular-nums}.tk-top small{display:block;color:var(--mute);font-size:12px}
.tk-top .lon b{font-size:26px}
.ngay{display:grid;grid-template-columns:64px 1fr 86px;gap:4px 10px;align-items:center;font-size:12.5px;color:var(--ink2);font-variant-numeric:tabular-nums;max-width:720px}
.ngay i{display:block;height:12px;border-radius:3px;min-width:2px}.ngay i.gain{background:var(--gain)}.ngay i.loss{background:var(--loss)}.ngay b{text-align:right}
td.buy{color:var(--series);font-weight:700}td.sell{color:var(--loss);font-weight:700}
"""

JS = r"""
(()=>{const $=i=>document.getElementById(i),esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])),
so=(v,d=2)=>v==null?'—':Number(v).toLocaleString('vi-VN',{minimumFractionDigits:d,maximumFractionDigits:d}),dau=v=>v==null?'—':(v>0?'+':v<0?'−':'')+so(Math.abs(v)),
mau=v=>v>0?'gain':v<0?'loss':'',gio=s=>new Date(s).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}),
bang=(dau_,dong,trong)=>dong.length?'<div class="wrap"><table><thead><tr>'+dau_.map(h=>`<th class="${h[1]||''}">${h[0]}</th>`).join('')+'</tr></thead><tbody>'+dong.join('')+'</tbody></table></div>':`<p class="small">${trong}</p>`;
async function tai(){let j;try{const r=await fetch('/api/tai-khoan',{cache:'no-store'});if(!r.ok)throw 0;j=await r.json()}catch(e){$('tk').innerHTML='<p class="note">Không đọc được tài khoản lúc này. Trang sẽ thử lại.</p>';return}
 if(!j.san_sang){$('tk').innerHTML=`<p class="note"><b>Chưa đọc được tài khoản.</b> ${esc(j.ly_do||'')} Mở MT5 demo rồi chờ vài giây.</p>`;$('tk-luc').textContent='';return}
 const t=j.tien,r=j.rui_ro||{},m=j.tom||{};
 $('tk-luc').textContent='Cập nhật '+gio(j.luc)+' · 5 giây một lần';
 let h=`<div class="tk-top"><div class="lon"><span>Vốn hiện tại (${esc(t)})</span><b>${so(j.von)}</b><small>số dư ${so(j.so_du)}</small></div>`
  +`<div><span>Lãi lỗ đang treo</span><b class="${mau(j.treo)}">${dau(j.treo)}</b><small>${j.lenh.length} lệnh đang mở</small></div>`
  +`<div><span>Ký quỹ đã dùng</span><b>${so(j.ky_quy)}</b><small>còn trống ${so(j.ky_quy_con)}</small></div>`
  +`<div><span>Mức ký quỹ</span><b>${j.muc_ky_quy==null?'—':so(j.muc_ky_quy,1)+'%'}</b><small>đòn bẩy 1:${j.don_bay}</small></div>`
  +`<div><span>Tài khoản</span><b>${esc(j.so)}</b><small><span class="tag" style="margin:0">${esc(j.loai)}</span> ${esc(j.may_chu)}</small></div></div>`;
 if(j.lenh.length){h+='<section class="card"><h2>Rủi ro của các lệnh đang mở</h2>';h+=`<div class="tiles"><div class="tile"><span>Lỗ nếu mọi SL cùng bị chạm</span><b class="${r.tong>0?'loss':''}">${r.tong>0?'−':''}${so(r.tong)} ${esc(t)}</b><small>${r.pct==null?'':so(r.pct)+'% vốn hiện tại'}</small></div>`
   +`<div class="tile"><span>Lệnh không có SL</span><b class="${r.khong_sl?'loss':''}">${r.khong_sl}</b><small>${r.khong_sl?'lệnh không có SL thì mức lỗ không có giới hạn':'mọi lệnh đều có SL'}</small></div>`
   +`<div class="tile"><span>Lãi lỗ đang treo</span><b class="${mau(j.treo)}">${dau(j.treo)} ${esc(t)}</b><small>chưa chốt, còn thay đổi</small></div></div>`;
  if(r.khong_tinh)h+=`<p class="small">${r.khong_tinh} lệnh có đồng tiền lãi lỗ khác đồng tiền tài khoản nên chưa tính vào tổng rủi ro.</p>`;
  h+='<p class="small">Tính theo giá SL đang đặt, chưa kể trượt giá khi thị trường nhảy giá. Lệnh đã kéo SL qua giá vào thì tính rủi ro bằng 0.</p></section>'}
 h+='<section class="card"><h2>Lệnh đang mở ('+j.lenh.length+')</h2>'+bang([['Mã'],['Hướng'],['Lot','r'],['Giá vào','r'],['Giá hiện tại','r'],['SL','r'],['TP','r'],['Lãi lỗ','r'],['Rủi ro tới SL','r'],['Nguồn'],['Mở lúc']],
  j.lenh.map(p=>`<tr><td><a href="/bieu-do?ma=${encodeURIComponent(p.ma)}">${esc(p.ma)}</a></td><td class="${p.huong==='MUA'?'buy':'sell'}">${p.huong==='MUA'?'MUA':'BÁN'}</td><td class="r">${so(p.lot)}</td><td class="r">${so(p.vao,p.so_le)}</td><td class="r">${so(p.gia,p.so_le)}</td>
   <td class="r">${p.sl==null?'<span class="loss">không có</span>':so(p.sl,p.so_le)}</td><td class="r">${p.tp==null?'—':so(p.tp,p.so_le)}</td><td class="r"><b class="${mau(p.lai)}">${dau(p.lai)}</b></td><td class="r">${p.rui_ro==null?'—':so(p.rui_ro)}</td><td>${esc(p.nguon)}</td><td>${gio(p.mo)}</td></tr>`),'Không có lệnh nào đang mở.')+'</section>';
 if(j.cho.length)h+='<section class="card"><h2>Lệnh chờ ('+j.cho.length+')</h2>'+bang([['Mã'],['Kiểu'],['Lot','r'],['Giá đặt','r'],['SL','r'],['TP','r'],['Nguồn'],['Đặt lúc']],
  j.cho.map(o=>`<tr><td>${esc(o.ma)}</td><td>${esc(o.loai)}</td><td class="r">${so(o.lot)}</td><td class="r">${so(o.gia,o.so_le)}</td><td class="r">${o.sl==null?'—':so(o.sl,o.so_le)}</td><td class="r">${o.tp==null?'—':so(o.tp,o.so_le)}</td><td>${esc(o.nguon)}</td><td>${gio(o.dat)}</td></tr>`),'')+'</section>';
 h+=`<section class="card"><h2>${m.ngay} ngày gần nhất</h2><div class="tiles"><div class="tile"><span>Lãi lỗ đã chốt</span><b class="${mau(m.tong)}">${dau(m.tong)} ${esc(t)}</b><small>sau phí và phí qua đêm</small></div>`
  +`<div class="tile"><span>Lệnh đã đóng</span><b>${m.n}</b><small>thắng ${m.thang}, thua ${m.thua}</small></div>`
  +`<div class="tile"><span>Lãi gộp / lỗ gộp</span><b><span class="gain">${dau(m.lai_gop)}</span> / <span class="loss">${dau(m.lo_gop)}</span></b><small>${m.lo_gop?'hệ số lợi nhuận '+so(m.lai_gop/Math.abs(m.lo_gop)):'chưa có lệnh thua'}</small></div></div>`;
 if(m.n<30)h+=`<p class="note"><b>Mới có ${m.n} lệnh đã đóng.</b> Dưới 30 lệnh thì các con số này chưa nói được gì về lợi thế.</p>`;
 if(j.theo_ngay.length){const mx=Math.max(...j.theo_ngay.map(d=>Math.abs(d.lai)))||1;h+='<h3>Lãi lỗ đã chốt theo ngày (giờ Việt Nam)</h3><div class="ngay">'
   +j.theo_ngay.map(d=>`<span>${d.ngay.slice(8)}/${d.ngay.slice(5,7)}</span><span><i class="${mau(d.lai)}" style="width:${(Math.abs(d.lai)/mx*100).toFixed(1)}%"></i></span><b class="${mau(d.lai)}">${dau(d.lai)}</b>`).join('')+'</div>'}
 h+='<h3>Các lệnh đã đóng</h3>'+bang([['Đóng lúc'],['Mã'],['Hướng'],['Lot','r'],['Giá đóng','r'],['Lãi lỗ ròng','r'],['Nguồn']],
  j.da_dong.map(x=>`<tr><td>${gio(x.luc)}</td><td>${esc(x.ma)}</td><td class="${x.huong==='MUA'?'buy':'sell'}">${x.huong==='MUA'?'MUA':'BÁN'}</td><td class="r">${so(x.lot)}</td><td class="r">${so(x.gia,x.so_le)}</td><td class="r"><b class="${mau(x.lai)}">${dau(x.lai)}</b></td><td>${esc(x.nguon)}</td></tr>`),
  'Chưa có lệnh nào đóng trong quãng này.');
 if(j.nap_rut.length)h+='<h3>Nạp, rút và điều chỉnh số dư demo</h3>'+bang([['Lúc'],['Loại'],['Số tiền','r'],['Ghi chú']],j.nap_rut.map(x=>`<tr><td>${gio(x.luc)}</td><td>${esc(x.loai)}</td><td class="r">${dau(x.tien)}</td><td>${esc(x.ghi_chu)}</td></tr>`),'');
 $('tk').innerHTML=h+'</section>'}
tai();setInterval(()=>{if(document.visibilityState==='visible'&&!getSelection().toString())tai()},5000)})();
"""


def trang_tai_khoan(ten: str) -> str:
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Tài khoản MT5 · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'tai-khoan', '<button id="theme" type="button">Nền tối</button>') + '<main>',
        '<div class="top"><div><h1>Tài khoản MT5</h1></div><div class="stamp">tài khoản demo đang mở trong MT5<br><span id="tk-luc">đang đọc…</span></div></div>',
        '<p class="note"><b>Chỉ đọc.</b> Trang lấy số liệu từ MT5 demo đang mở trên máy này. Trang không đặt, sửa hay đóng lệnh, không lưu mật khẩu, '
        'và che số tài khoản. Đây là tiền demo, không phải tiền thật, và không phải lời khuyên đầu tư. '
        'Muốn xem nhiều tài khoản cùng lúc, kể cả tài khoản tiền thật (chỉ đọc): <a href="/cac-tai-khoan">Các tài khoản đã nối</a>.</p>',
        '<div id="tk"><p class="small">Đang đọc tài khoản từ MT5…</p></div>',
        '<footer>Số liệu đọc trực tiếp từ MT5 qua các hàm chỉ đọc. Lãi lỗ ròng của lệnh đã đóng gồm lãi lỗ, hoa hồng và phí qua đêm của lần khớp đóng lệnh. '
        + escape(trang.MIEN_TRU) + f'</footer></main><script>{trang.JS}</script><script>{JS}</script></body></html>'])
