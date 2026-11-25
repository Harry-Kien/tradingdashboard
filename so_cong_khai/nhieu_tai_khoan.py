"""Các tài khoản đã nối: gom nhiều tài khoản MT5 (demo và tiền thật) vào một chỗ, CHỈ ĐỌC.

Mỗi tài khoản là một MT5 mà chủ dự án TỰ MỞ và TỰ ĐĂNG NHẬP trên máy này. Webapp chỉ ghi nhớ đường dẫn của MT5 đó (du-lieu/tai-khoan-noi.json: tên tự
đặt, đường dẫn, giờ thêm), không bao giờ hỏi, nhận hay lưu mật khẩu. Một vòng nền đọc từng tài khoản trong một tiến trình riêng
(so_cong_khai.doc_mot_tai_khoan, giữ mọi chốt an toàn của noi_mt5: không tự mở MT5, chỉ gọi hàm đọc), nên không đụng phiên MT5 chính của webapp.
Chỉ thêm được MT5 đang mở. Không có lời gọi đặt, sửa hay đóng lệnh nào. Chủ dự án đồng ý đọc cả tài khoản tiền thật ngày 25/11/2026.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from . import noi_mt5, trang
from .__main__ import HERE

GIAY = 120                                   # chu kỳ đọc lại mọi tài khoản
_khoa = threading.Lock()
_nho: dict = {}                              # id → kết quả đọc gần nhất
_mo: dict = {'luc': 0.0, 'ds': None}         # danh sách MT5 đang mở, nhớ 30 giây
TT: dict = {}


def tep() -> Path:
    return HERE / 'du-lieu' / 'tai-khoan-noi.json'


def doc_ds(p: Path | None = None) -> list[dict]:
    p = p or tep()
    try:
        ds = json.loads(p.read_text(encoding='utf-8'))
        return ds if isinstance(ds, list) else []
    except (OSError, ValueError):
        return []


def _luu(ds: list[dict], p: Path | None = None) -> None:
    p = p or tep()
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_suffix('.tmp')
    tam.write_text(json.dumps(ds, ensure_ascii=False, indent=1), encoding='utf-8')
    tam.replace(p)


def mt5_dang_mo(procs_fn=noi_mt5.tien_trinh, lam_moi: bool = False) -> list[str] | None:
    """Đường dẫn các MT5 (terminal64.exe) đang chạy, không trùng; None nếu không đọc được danh sách tiến trình."""
    if not lam_moi and _mo['ds'] is not None and time.time() - _mo['luc'] < 30:
        return _mo['ds']
    procs = procs_fn()
    ds = None if procs is None else sorted({str(Path(path)).casefold(): path for ten, _, path in procs if ten == 'terminal64.exe' and path}.values())
    _mo.update(luc=time.time(), ds=ds)
    return ds


def them(duong: str, ten: str, p: Path | None = None, procs_fn=noi_mt5.tien_trinh) -> tuple[bool, str]:
    """Thêm một MT5 ĐANG MỞ vào danh sách. Trả (được không, lời nhắn)."""
    duong = (duong or '').strip()
    ten = ' '.join((ten or '').split())[:40] or 'Tài khoản'
    mo = mt5_dang_mo(procs_fn, lam_moi=True)
    if mo is None:
        return False, 'Không đọc được danh sách chương trình đang chạy để kiểm MT5.'
    if not any(noi_mt5.cung_duong(duong, x) for x in mo):
        return False, 'Chỉ thêm được MT5 đang mở trên máy này. Hãy mở MT5 đó, đăng nhập tài khoản, rồi thử lại.'
    with _khoa:
        ds = doc_ds(p)
        if any(noi_mt5.cung_duong(duong, x.get('duong', '')) for x in ds):
            return False, 'MT5 này đã có trong danh sách.'
        ds.append({'id': max([x.get('id', 0) for x in ds] + [0]) + 1, 'ten': ten, 'duong': duong, 'them_luc': datetime.now(timezone.utc).isoformat()})
        _luu(ds, p)
    return True, f'Đã thêm "{ten}". Trang sẽ đọc tài khoản này trong ít phút.'


def xoa(id_: int, p: Path | None = None) -> tuple[bool, str]:
    with _khoa:
        ds = doc_ds(p)
        con = [x for x in ds if x.get('id') != int(id_)]
        if len(con) == len(ds):
            return False, 'Không thấy tài khoản này.'
        _luu(con, p)
        _nho.pop(int(id_), None)
    return True, 'Đã bỏ tài khoản khỏi danh sách (webapp chỉ quên đường dẫn; MT5 và tài khoản không bị đụng tới).'


def doc_mot(duong: str, ngay: int = 90, chay=subprocess.run) -> dict:
    """Đọc một tài khoản trong tiến trình riêng; trả kết quả JSON của so_cong_khai.doc_mot_tai_khoan."""
    try:
        r = chay([sys.executable, '-X', 'utf8', '-m', 'so_cong_khai.doc_mot_tai_khoan', duong, str(int(ngay))], cwd=str(HERE), capture_output=True,
                 text=True, encoding='utf-8', timeout=120, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        dong = [x for x in (r.stdout or '').splitlines() if x.strip().startswith('{')]
        if not dong:
            return {'ok': False, 'ly_do': 'Tiến trình đọc tài khoản không trả kết quả. ' + (r.stderr or '').strip()[-300:]}
        return json.loads(dong[-1])
    except subprocess.TimeoutExpired:
        return {'ok': False, 'ly_do': 'Đọc tài khoản quá 2 phút; MT5 có thể đang bận hoặc treo.'}
    except Exception as e:                                                   # noqa: BLE001
        return {'ok': False, 'ly_do': f'{type(e).__name__}: {e}'}


def cap_nhat(p: Path | None = None, chay=subprocess.run, ngay: int = 90) -> None:
    for x in doc_ds(p):
        kq = doc_mot(x['duong'], ngay, chay)
        kq['luc_doc'] = datetime.now(timezone.utc).isoformat()
        with _khoa:
            _nho[int(x['id'])] = kq


def xem(p: Path | None = None) -> dict:
    """Danh sách tài khoản kèm kết quả đọc gần nhất, tổng theo loại tiền, và các MT5 đang mở chưa thêm."""
    ds = doc_ds(p)
    with _khoa:
        tk = [dict(x, kq=_nho.get(int(x['id']))) for x in ds]
    tong: dict = {}
    for x in tk:
        k = x['kq']
        if not k or not k.get('ok'):
            continue
        t = tong.setdefault(k['tai_khoan']['tien'], {'von': 0.0, 'treo': 0.0, 'rui_ro': 0.0, 'lenh_mo': 0, 'so_tk': 0, 'that': 0, 'rong': 0.0})
        t['von'] += k.get('von') or 0.0
        t['treo'] += k.get('treo') or 0.0
        t['rui_ro'] += (k.get('rui_ro') or {}).get('tong') or 0.0
        t['lenh_mo'] += len(k.get('lenh_mo') or [])
        t['so_tk'] += 1
        t['that'] += bool(k['tai_khoan'].get('that'))
        t['rong'] += ((k.get('tong') or {}).get('rong') or 0.0)
    for t in tong.values():
        t.update({a: round(t[a], 2) for a in ('von', 'treo', 'rui_ro', 'rong')}, rui_ro_pct=round(t['rui_ro'] / t['von'] * 100, 2) if t['von'] > 0 else None)
    mo = mt5_dang_mo()
    chua = [d for d in (mo or []) if not any(noi_mt5.cung_duong(d, x['duong']) for x in ds)]
    return {'ds': tk, 'tong': tong, 'mt5_chua_them': chua, 'doc_duoc_tien_trinh': mo is not None, 'vong': dict(TT), 'chu_ky_giay': GIAY}


class VongTaiKhoan(threading.Thread):
    """Vòng nền: cứ GIAY giây đọc lại mọi tài khoản trong danh sách (mỗi cái một tiến trình riêng)."""

    def __init__(self, giay: int = GIAY):
        super().__init__(name='cac-tai-khoan', daemon=True)
        self.giay = giay
        self.ngay = threading.Event()

    def run(self) -> None:
        while True:
            try:
                if doc_ds():
                    cap_nhat()
                TT.update(luc=datetime.now(timezone.utc).isoformat(), loi=None)
            except Exception as e:                                           # noqa: BLE001 - vòng nền không được chết
                TT.update(loi=f'{type(e).__name__}: {e}')
            self.ngay.wait(self.giay)
            self.ngay.clear()


VONG: VongTaiKhoan | None = None


def doc_lai_ngay() -> None:
    if VONG is not None:
        VONG.ngay.set()


# ---- trang
CSS = """
.ctk{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;margin-top:14px}
.ctk .card{display:grid;gap:8px;padding:14px}.ctk .hd{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.ctk .hd b{font-size:15px}
.ctk .hd small{color:var(--mute);font-size:12px}.ctk .hd .x{margin-left:auto}
.loai{font-size:11px;font-weight:700;padding:2px 7px;border-radius:5px;border:1px solid var(--line);color:var(--ink2)}.loai.that{background:var(--loss);border-color:var(--loss);color:#fff}
.ctk .g3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.ctk .g3 div{display:grid;gap:1px;border:1px solid var(--line);border-radius:8px;padding:6px 8px;min-width:0}
.ctk .g3 small{font-size:11px;color:var(--mute)}.ctk .g3 b{font-size:14.5px;font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ctk .rr .tr{height:7px;border-radius:99px;background:var(--track);overflow:hidden}.ctk .rr .tr i{display:block;height:100%;background:var(--gain)}
.ctk .rr.vua .tr i{background:var(--warn)}.ctk .rr.cao .tr i{background:var(--loss)}.ctk .rr{display:grid;gap:4px;font-size:12.5px}
.ctk table{font-size:12.5px}.ctk .why{margin:0}.them{display:grid;gap:8px;margin-top:10px}.them .h{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.them code{font-size:12px;word-break:break-all}.them input{min-width:0;flex:1}
"""

JS = r"""
(()=>{const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
 f2=v=>v==null?'—':Number(v).toLocaleString('vi-VN',{minimumFractionDigits:2,maximumFractionDigits:2}),dau=v=>v==null?'—':(v>0?'+':v<0?'−':'')+f2(Math.abs(v)),
 mau=v=>v>0?'gain':v<0?'loss':'',muc=p=>p==null?'':p<2?'':p<5?' vua':' cao';let DL=null;
 async function gui(viec,them){const r=await fetch('/api/cac-tai-khoan',{method:'POST',headers:{'Content-Type':'application/json','X-So-Cong-Khai':'1'},body:JSON.stringify({viec,...them})});
  const j=await r.json().catch(()=>({ok:false,ly_do:'lỗi máy chủ'}));$('#tb').textContent=j.ly_do||'';await tai()}
 function the(x){const k=x.kq;let h=`<section class="card"><div class="hd"><b>${esc(x.ten)}</b>`;
  if(!k)return h+`<small>đang chờ lần đọc đầu…</small><button class="ghost nho x" data-xoa="${x.id}">Bỏ</button></div><p class="why">${esc(x.duong)}</p></section>`;
  if(!k.ok)return h+`<small>${esc(k.luc_doc?'đọc lúc '+new Date(k.luc_doc).toLocaleTimeString('vi-VN'):'')}</small><button class="ghost nho x" data-xoa="${x.id}">Bỏ</button></div><p class="why loss">${esc(k.ly_do)}</p><p class="why">${esc(x.duong)}</p></section>`;
  const t=k.tai_khoan,T=k.tong||{},R=k.rui_ro||{},tien=esc(t.tien);
  h+=`<span class="loai${t.that?' that':''}">${esc(t.loai)}</span><small>${esc(t.so)} · ${esc(t.may_chu)} · đòn bẩy 1:${t.don_bay||'?'}</small><button class="ghost nho x" data-xoa="${x.id}">Bỏ</button></div>`
   +`<div class="g3"><div><small>Vốn hiện có</small><b>${f2(k.von)}</b></div><div><small>Lãi lỗ treo</small><b class="${mau(k.treo)}">${dau(k.treo)}</b></div><div><small>Ký quỹ trống</small><b>${f2(k.ky_quy_con)}</b></div></div>`
   +`<div class="rr${muc(R.pct)}"><span>Đang chịu rủi ro: <b>${f2(R.tong)} ${tien}${R.pct!=null?' = '+String(R.pct).replace('.',',')+'% vốn':''}</b> · ${k.lenh_mo.length} lệnh mở</span><div class="tr"><i style="width:${Math.min(100,Math.max(2,R.pct||0))}%"></i></div>`
   +(R.khong_sl?`<span class="loss">${R.khong_sl} lệnh không có dừng lỗ: rủi ro không giới hạn.</span>`:'')+'</div>'
   +(T.n?`<div class="g3"><div><small>${k.so_ngay} ngày: thắng · thua</small><b><span class="gain">${T.thang}</span> · <span class="loss">${T.thua}</span></b></div><div><small>Lãi lỗ ròng</small><b class="${mau(T.rong)}">${dau(T.rong)}</b></div><div><small>Sụt vốn lớn nhất</small><b>${f2(T.dd_max)}${T.dd_pct!=null?' ('+String(T.dd_pct).replace('.',',')+'%)':''}</b></div></div>`
    +`<p class="why">Tỷ lệ thắng ${String(T.ty_le).replace('.',',')}% · hệ số lợi nhuận ${T.pf==null?'—':String(T.pf).replace('.',',')} · lệnh thắng trung bình ${dau(T.tb_thang)}, lệnh thua trung bình ${dau(T.tb_thua)} ${tien}</p>`
    :`<p class="why">Chưa có lệnh nào đóng trong ${k.so_ngay} ngày.</p>`)
   +((k.gan_day||[]).length?'<div class="wrap"><table><thead><tr><th>Đóng lúc</th><th>Mã</th><th>Chiều</th><th class="r">Lot</th><th class="r">Ròng</th><th>Nguồn</th></tr></thead><tbody>'
    +k.gan_day.slice(0,6).map(g=>`<tr><td>${esc(new Date(g.dong).toLocaleString('vi-VN',{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'}))}</td><td>${esc(g.ma)}</td><td>${g.chieu==='MUA'?'▲ MUA':'▼ BÁN'}</td><td class="r">${g.lot}</td><td class="r ${mau(g.rong)}">${dau(g.rong)}</td><td>${esc(g.nguon)}</td></tr>`).join('')+'</tbody></table></div>':'')
   +`<p class="why">Đọc lúc ${esc(new Date(k.luc_doc).toLocaleTimeString('vi-VN'))} · ${esc(x.duong)}</p></section>`;return h}
 function ve(){const el=$('#ctk');if(!DL){el.innerHTML='<p class="small">Đang đọc…</p>';return}
  let h='';const tg=Object.entries(DL.tong||{});
  if(tg.length)h+='<div class="tiles">'+tg.map(([tien,t])=>`<div class="tile"><span>Tổng ${t.so_tk} tài khoản (${esc(tien)})${t.that?' · '+t.that+' tiền thật':''}</span><b>${f2(t.von)}</b><small>lãi treo <span class="${mau(t.treo)}">${dau(t.treo)}</span> · đang chịu rủi ro ${f2(t.rui_ro)}${t.rui_ro_pct!=null?' ('+String(t.rui_ro_pct).replace('.',',')+'%)':''} · ${t.lenh_mo} lệnh mở</small></div>`).join('')+'</div>';
  h+=DL.ds.length?'<div class="ctk">'+DL.ds.map(the).join('')+'</div>':'<p class="note">Chưa có tài khoản nào. Mở MT5 của tài khoản muốn theo dõi, tự đăng nhập trong MT5, rồi bấm "Thêm" ở danh sách dưới đây.</p>';
  h+='<section class="card them"><h2>Thêm tài khoản</h2><p class="why">Chỉ thêm được MT5 đang mở trên máy này. Webapp không hỏi mật khẩu: bạn tự đăng nhập trong MT5. Muốn thêm tài khoản khác cùng sàn thì cài thêm một bản MT5 ở thư mục khác.</p>';
  h+=!DL.doc_duoc_tien_trinh?'<p class="why loss">Không đọc được danh sách chương trình đang chạy.</p>':DL.mt5_chua_them.length?DL.mt5_chua_them.map((d,i)=>`<div class="h"><code>${esc(d)}</code><input id="ten${i}" type="text" maxlength="40" placeholder="Tên gợi nhớ, ví dụ: Exness thật" aria-label="Tên gợi nhớ"><button class="act" data-them="${i}">Thêm</button></div>`).join(''):'<p class="why">Không có MT5 nào đang mở mà chưa thêm.</p>';
  h+='<p class="why" id="tb" role="status"></p></section>';el.innerHTML=h;
  el.querySelectorAll('[data-them]').forEach(b=>b.addEventListener('click',()=>{const i=+b.dataset.them;b.disabled=true;gui('them',{duong:DL.mt5_chua_them[i],ten:$('#ten'+i).value})}));
  el.querySelectorAll('[data-xoa]').forEach(b=>b.addEventListener('click',()=>{if(confirm('Bỏ tài khoản này khỏi danh sách? Webapp chỉ quên đường dẫn; MT5 và tài khoản không bị đụng tới.'))gui('xoa',{id:+b.dataset.xoa})}));
  $('#ctk-luc').textContent='cập nhật '+new Date().toLocaleTimeString('vi-VN')}
 async function tai(){try{DL=await (await fetch('/api/cac-tai-khoan',{cache:'no-store'})).json()}catch(e){}ve()}
 $('#doc-lai').addEventListener('click',()=>gui('doc_lai',{}));tai();setInterval(()=>{if(document.visibilityState==='visible')tai()},20000)})();
"""


def trang_cac_tai_khoan(ten: str) -> str:
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Các tài khoản · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'cac-tai-khoan', '<button id="theme" type="button">Nền tối</button>') + '<main>',
        '<div class="top"><div><h1>Các tài khoản đã nối</h1></div><div class="stamp">mọi MT5 bạn đã thêm, demo và tiền thật<br><span id="ctk-luc">đang đọc…</span> · '
        '<button type="button" class="ghost nho" id="doc-lai">Đọc lại ngay</button></div></div>',
        '<p class="note"><b>Chỉ đọc.</b> Trang đọc các MT5 bạn đã tự mở và tự đăng nhập trên máy này: vốn, lệnh đang mở, rủi ro nếu mọi dừng lỗ bị chạm, '
        'lệnh thắng thua và lãi lỗ 90 ngày. Trang không hỏi hay lưu mật khẩu, không tự mở MT5, không đặt, sửa hay đóng lệnh, và che số tài khoản. '
        'Mỗi tài khoản được đọc lại khoảng 2 phút một lần. Đây không phải lời khuyên đầu tư.</p>',
        '<div id="ctk"><p class="small">Đang đọc…</p></div>',
        f'<footer>{escape(trang.MIEN_TRU)}</footer></main><script>{trang.JS}</script><script>{JS}</script></body></html>'])
