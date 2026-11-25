"""Trang Cài đặt: chỉnh cấu hình của webapp ngay trên web thay vì sửa cau-hinh.json.

Chỉ sửa được một danh sách mục cố định (TRUONG), mỗi mục có kiểu và giới hạn riêng; mục lạ bị từ chối. Ghi theo kiểu ghi tệp tạm rồi
thay (không bao giờ để cau-hinh.json dở dang), giữ bản trước ở cau-hinh.json.bak. Đổi MT5 chính, mã vàng, chế độ chỉ demo hay giờ sàn
thì ngắt phiên MT5 để lượt sau nối lại ngay theo cấu hình mới (vẫn qua mọi chốt an toàn: không tự mở MT5, chỉ đọc).
Máy chủ chỉ nhận lệnh ghi khi yêu cầu đến từ chính máy này (xem web.py: tiêu đề X-So-Cong-Khai, Host và Origin)."""
from __future__ import annotations

import json
import os
import re
import threading
from html import escape
from pathlib import Path

from . import gia, nhieu_tai_khoan, song, trang

_khoa = threading.Lock()

# khóa (dạng a.b.c) → (kiểu, mặc định[, nhỏ nhất, lớn nhất])
TRUONG: dict = {
    'gia.mt5.terminal': ('duong_mt5', ''),
    'gia.ma_vang': ('ma', ''),
    'gia.mt5.chi_demo': ('bat', True),
    'gia.mt5.lech_gio_san': ('lech', None),
    'thi_truong.bat': ('bat', True),
    'thi_truong.chu_ky_giay': ('so', 0.05, 0.02, 2.0),
    'tin_tuc.bat': ('bat', True),
    'lich_mang.bat': ('bat', True),
    'cot.bat': ('bat', True),
    'nhat_ky.bat': ('bat', False),
    'canh_bao.bat': ('bat', False),
}
BO_QUA = {'ten'}                                   # tên hiển thị là tên thương hiệu cố định (thuong_hieu.TEN): gửi lên thì bỏ qua
KHOA_MT5 = {'gia.mt5.terminal', 'gia.ma_vang', 'gia.mt5.chi_demo', 'gia.mt5.lech_gio_san'}
LOAI_TK = {0: 'DEMO', 1: 'THI ĐẤU', 2: 'TIỀN THẬT'}


def _lay(cfg: dict, khoa: str, md=None):
    o = cfg
    for k in khoa.split('.'):
        if not isinstance(o, dict) or k not in o:
            return md
        o = o[k]
    return o


def _dat(cfg: dict, khoa: str, v) -> None:
    *dau, cuoi = khoa.split('.')
    o = cfg
    for k in dau:
        if not isinstance(o.get(k), dict):
            o[k] = {}
        o = o[k]
    o[cuoi] = v


def kiem(khoa: str, v):
    """Giá trị đã kiểm của một mục, hoặc ValueError kèm lý do đọc được."""
    if khoa not in TRUONG:
        raise ValueError(f'không sửa được mục "{khoa}"')
    kieu = TRUONG[khoa][0]
    if kieu == 'bat':
        if not isinstance(v, bool):
            raise ValueError(f'{khoa}: phải là bật hoặc tắt')
        return v
    if kieu == 'chu':
        v = str(v).strip()
        if len(v) > 60 or re.search(r'[\x00-\x1f<>]', v):
            raise ValueError('Tên hiển thị dài tối đa 60 ký tự, không có ký tự < >')
        return v
    if kieu == 'ma':
        v = str(v or '').strip()
        if v and not re.fullmatch(r'[A-Za-z0-9._#+\-]{1,32}', v):
            raise ValueError('Mã vàng chỉ gồm chữ, số và . _ # + -, tối đa 32 ký tự')
        return v
    if kieu == 'duong_mt5':
        v = str(v or '').strip().strip('"')
        if not v:
            return ''
        if Path(v).name.casefold() != 'terminal64.exe' or not os.path.isfile(v):
            raise ValueError('Đường dẫn MT5 phải là tệp terminal64.exe có thật trên máy này')
        return v
    if kieu == 'lech':
        if v is None or v == '':
            return None
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not -14 <= v <= 14 or round(v * 2) != v * 2:
            raise ValueError('Giờ sàn lệch UTC phải từ −14 tới +14, bước nửa giờ (để trống là tự đo)')
        return float(v) if v % 1 else int(v)
    if kieu == 'so':
        lo, hi = TRUONG[khoa][2], TRUONG[khoa][3]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
            raise ValueError(f'{khoa}: phải từ {lo} tới {hi}')
        return float(v)
    raise ValueError(f'không rõ kiểu của mục "{khoa}"')                    # pragma: no cover


def doc(cfg: dict) -> dict:
    """Giá trị hiện tại của mọi mục sửa được, kèm tình trạng kết nối, các MT5 đang mở và các mã vàng của sàn để chọn."""
    g = cfg.get('gia') or {}
    out = {'gia_tri': {k: _lay(cfg, k, t[1]) for k, t in TRUONG.items()}, 'mt5_dang_mo': nhieu_tai_khoan.mt5_dang_mo(lam_moi=True),
           'chia_se': gia.ban_chia_se(g), 'ket_noi': {'co': False, 'ly_do': song.ly_do(), **song.thong_tin(), 'tai_khoan': None}, 'ma_vang_goi_y': []}
    m = song._tt.get('mt5')
    if m is not None and song.ly_do() is None:
        try:
            with song._khoa:
                acc, syms = m.account_info(), m.symbols_get() or ()
            if acc is not None:
                out['ket_noi'].update(co=True, tai_khoan={'loai': LOAI_TK.get(int(getattr(acc, 'trade_mode', -1)), 'không rõ'),
                                                          'so': '•••' + str(getattr(acc, 'login', ''))[-3:], 'may_chu': getattr(acc, 'server', ''),
                                                          'tien': getattr(acc, 'currency', '')})
            out['ma_vang_goi_y'] = sorted({s.name for s in syms if s.name.upper().startswith(('XAUUSD', 'GOLD'))})[:40]
        except Exception:                                                  # noqa: BLE001 - mất kết nối giữa chừng: chỉ thiếu phần tài khoản
            pass
    return out


def _lam_moi_bang() -> None:
    """Đổi MT5 chính có thể đổi cả sàn: bảng giá Thị trường quên danh sách mã cũ để đọc lại từ MT5 mới."""
    from . import thi_truong                                               # noqa: PLC0415
    b = thi_truong._BANG.get('b')
    if b is None:
        return
    with b._dk:
        b.dac_ta, b.gia, b.doi, b.moc, b.kt = {}, {}, {}, {}, {}
        b._luc.update(dac_ta=0.0, moc=0.0, tq=0.0, kt=0.0)


def noi_lai(g: dict | None = None, doi_san: bool = False) -> None:
    """Ngắt phiên MT5 rồi nối lại NGAY ở nền theo cấu hình `g` (không chờ vòng đọc tới lượt; vẫn qua mọi chốt an toàn của song.py)."""
    song.ngat()
    song._tt['thu'] = 0.0
    if doi_san:
        _lam_moi_bang()
    if g is not None:
        threading.Thread(target=lambda: song.khung_song(g), name='noi-lai-mt5', daemon=True).start()


def ghi(p: Path, gia_tri: dict) -> dict:
    """Kiểm rồi ghi các mục đổi. Trả {'ok', 'doi': [khóa], 'noi_lai': bool, 'thong_bao'}; mục sai thì ValueError, không ghi gì."""
    if not isinstance(gia_tri, dict) or not gia_tri:
        raise ValueError('không có mục nào để lưu')
    gia_tri = {k: v for k, v in gia_tri.items() if k not in BO_QUA}
    if not gia_tri:
        return {'ok': True, 'doi': [], 'noi_lai': False, 'thong_bao': 'Không có gì thay đổi.'}
    moi = {k: kiem(k, v) for k, v in gia_tri.items()}                     # kiểm hết trước, sai một mục là không ghi mục nào
    with _khoa:
        goc = p.read_text(encoding='utf-8')
        cfg = json.loads(goc)
        doi = sorted(k for k, v in moi.items() if _lay(cfg, k, TRUONG[k][1]) != v)
        if not doi:
            return {'ok': True, 'doi': [], 'noi_lai': False, 'thong_bao': 'Không có gì thay đổi.'}
        cu_terminal = _lay(cfg, 'gia.mt5.terminal', '')
        for k in doi:
            _dat(cfg, k, moi[k])
        p.with_name(p.name + '.bak').write_text(goc, encoding='utf-8')
        tam = p.with_name(p.name + '.tam')
        tam.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(tam, p)
    can = bool(KHOA_MT5 & set(doi))
    if can:
        noi_lai(cfg.get('gia') or {}, doi_san=_lay(cfg, 'gia.mt5.terminal', '') != cu_terminal)
    return {'ok': True, 'doi': doi, 'noi_lai': can,
            'thong_bao': f'Đã lưu {len(doi)} mục.' + (' Đang nối lại MT5 theo cấu hình mới…' if can else '')}


# --------------------------------------------------------------------------- trang
CSS = """
.cd{display:grid;gap:16px;margin-top:16px}.cd .card{margin-top:0}
.cd h2{margin:0 0 4px;font-size:18px}.cd .sub{margin:0 0 12px}
.hang{display:grid;grid-template-columns:minmax(180px,260px) 1fr;gap:6px 18px;align-items:center;padding:10px 0;border-top:1px solid var(--line)}
.hang:first-of-type{border-top:0}.hang>label{font-weight:600}.hang small{display:block;color:var(--mute);font-weight:400;font-size:12.5px;margin-top:2px}
.hang input[type=text],.hang input[type=number],.hang select{width:100%;max-width:560px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:inherit}
.hang input[type=checkbox]{width:24px;height:24px;accent-color:var(--series);cursor:pointer}
.tt{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:center;font-size:14px}.tt b.ok{color:var(--gain)}.tt b.loi{color:var(--loss)}
.luu{position:sticky;bottom:0;display:flex;gap:12px;align-items:center;padding:12px 0;background:var(--bg);z-index:5}
.luu button{padding:10px 18px;border-radius:9px;border:0;background:var(--series);color:var(--btn-ink);font-weight:700;cursor:pointer;min-height:40px}
.luu button:disabled{opacity:.6;cursor:progress}.luu .kq{font-size:14px}.luu .kq.loi{color:var(--loss)}.luu .kq.ok{color:var(--gain)}
button.phu{padding:7px 12px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer;min-height:34px}
@media(max-width:640px){.hang{grid-template-columns:1fr}}
"""

JS = r"""(()=>{const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));let S=null;
const HDR={'Content-Type':'application/json','X-So-Cong-Khai':'1'};
async function tai(){try{const r=await fetch('/api/cai-dat',{cache:'no-store'});S=await r.json();ve()}catch(e){$('#cd').innerHTML='<p class="note">Không đọc được cài đặt: '+esc(e.message)+'</p>'}}
function ttVe(){const k=S.ket_noi||{},t=k.tai_khoan;let h='';
 if(k.co&&t)h=`<b class="ok">Đang nối</b><span>Tài khoản ${esc(t.so)} · ${esc(t.loai)} · ${esc(t.may_chu)} · ${esc(t.tien)}</span><span>Mã vàng: <b>${esc(k.ma||'—')}</b></span><span>Giờ sàn lệch UTC ${k.lech_gio>0?'+':''}${esc(k.lech_gio)} giờ (${esc(k.lech_nguon||'')})</span>`;
 else h=`<b class="loi">Chưa nối được</b><span>${esc(k.ly_do||'đang nối…')}</span>`;
 $('#tt').innerHTML=h}
function ve(){const v=S.gia_tri,mo=S.mt5_dang_mo||[],tu=v['gia.mt5.terminal']||'';
 const optMt5=['<option value="">Tự tìm MT5 đang mở (khi máy chỉ mở một MT5)</option>'].concat(mo.map(p=>`<option value="${esc(p)}"${p.toLowerCase()===tu.toLowerCase()?' selected':''}>${esc(p)}</option>`));
 if(tu&&!mo.some(p=>p.toLowerCase()===tu.toLowerCase()))optMt5.push(`<option value="${esc(tu)}" selected>${esc(tu)} (chưa mở)</option>`);
 const goi=S.ma_vang_goi_y||[],mv=v['gia.ma_vang']||'';
 const optMa=['<option value="">Tự tìm (XAUUSD kèm hậu tố của sàn, hoặc GOLD)</option>'].concat(goi.map(m=>`<option${m===mv?' selected':''}>${esc(m)}</option>`));
 if(mv&&!goi.includes(mv))optMa.push(`<option selected>${esc(mv)}</option>`);
 const cb=(k,nhan,ghi)=>`<div class="hang"><label for="${k}">${nhan}${ghi?`<small>${ghi}</small>`:''}</label><div><input type="checkbox" id="${k}" data-k="${k}"${v[k]?' checked':''}></div></div>`;
 const lech=v['gia.mt5.lech_gio_san'];
 $('#cd').innerHTML=`
<section class="card"><h2>Kết nối MT5</h2><p class="sub">MT5 dùng cho biểu đồ, bảng giá và phân tích. Webapp chỉ nối vào MT5 bạn đã mở và đăng nhập, không bao giờ tự mở MT5, không hỏi hay lưu mật khẩu, không đặt lệnh. Muốn xem cùng lúc nhiều tài khoản thì dùng trang <a href="/cac-tai-khoan">Các tài khoản đã nối</a>.</p>
 <div class="tt" id="tt"></div>
 <div class="hang"><label for="mt5">MT5 chính<small>các MT5 đang mở trên máy này</small></label><div><select id="mt5" data-k="gia.mt5.terminal">${optMt5.join('')}</select> <button type="button" class="phu" id="quet">Tìm lại</button></div></div>
 ${cb('gia.mt5.chi_demo','Chỉ đọc tài khoản demo','Tắt để đọc giá từ tài khoản tiền thật. Webapp vẫn chỉ đọc, không đặt lệnh.')}
 <div class="hang"><label for="ma">Mã vàng<small>${S.chia_se?'tên mã vàng trên sàn của bạn':'máy này dùng mã vàng theo cấu hình EA Promax'}</small></label><div><select id="ma" data-k="gia.ma_vang"${S.chia_se?'':' disabled'}>${optMa.join('')}</select></div></div>
 <div class="hang"><label for="lech">Giờ máy chủ của sàn<small>để trống là tự đo từ tick; chỉ ghi khi giờ trên biểu đồ bị lệch</small></label><div><input type="number" id="lech" data-k="gia.mt5.lech_gio_san" step="0.5" min="-14" max="14" placeholder="tự đo" value="${lech??''}" style="max-width:140px"> giờ so với UTC</div></div>
 <div class="hang"><label></label><div><button type="button" class="phu" id="noi">Nối lại MT5 ngay</button></div></div>
</section>
<section class="card"><h2>Bảng giá và dữ liệu</h2><p class="sub">Các mục dưới đây là những chỗ duy nhất webapp gọi ra Internet (tin tức, lịch kinh tế, COT).</p>
 ${cb('thi_truong.bat','Bảng giá Thị trường','Đọc giá mọi mã trong MT5 cho trang Thị trường và Công cụ. Cần khởi động lại webapp khi bật/tắt.')}
 <div class="hang"><label for="ck">Nhịp đọc bảng giá<small>giây giữa hai lượt đọc; nhỏ hơn là nhanh hơn</small></label><div><input type="number" id="ck" data-k="thi_truong.chu_ky_giay" step="0.01" min="0.02" max="2" value="${v['thi_truong.chu_ky_giay']}" style="max-width:140px"> giây</div></div>
 ${cb('tin_tuc.bat','Tin tức','Tin thị trường từ các nguồn RSS công khai.')}
 ${cb('lich_mang.bat','Lịch kinh tế từ Internet')}
 ${cb('cot.bat','Vị thế COT của CFTC','Tải báo cáo công khai mỗi tuần từ cftc.gov.')}
</section>
<section class="card"><h2>Cá nhân</h2>
 ${cb('nhat_ky.bat','Nhật ký điểm vào','Tự ghi mọi điểm vào của các phương pháp, rồi chấm bằng giá thật.')}
 ${cb('canh_bao.bat','Vòng canh cảnh báo','Báo khi luật có tín hiệu mới. Cần khởi động lại webapp khi bật/tắt.')}
</section>
<div class="luu"><button type="button" id="luu">Lưu cài đặt</button><span class="kq" id="kq"></span></div>`;
 ttVe();
 $('#luu').onclick=luu;$('#noi').onclick=async()=>{if(await gui({viec:'noi_lai'},'Đang nối lại MT5…'))cho()};$('#quet').onclick=tai}
function layGT(){const o={};for(const e of document.querySelectorAll('[data-k]')){if(e.disabled)continue;const k=e.dataset.k;let v;
  if(e.type==='checkbox')v=e.checked;else if(e.type==='number')v=e.value===''?null:Number(e.value);else v=e.value;
  if(JSON.stringify(v)!==JSON.stringify(S.gia_tri[k]))o[k]=v}return o}
async function gui(yc,dang){const kq=$('#kq'),b=$('#luu');b.disabled=true;kq.className='kq';kq.textContent=dang;
 try{const r=await fetch('/api/cai-dat',{method:'POST',headers:HDR,body:JSON.stringify(yc)});const j=await r.json().catch(()=>({thong_bao:'Máy chủ trả lỗi '+r.status}));
  kq.className='kq '+(r.ok?'ok':'loi');kq.textContent=j.thong_bao||j.loi||'';return r.ok?j:null}catch(e){kq.className='kq loi';kq.textContent='Không gửi được: '+e.message;return null}finally{b.disabled=false}}
async function luu(){const o=layGT();if(!Object.keys(o).length){$('#kq').className='kq';$('#kq').textContent='Không có gì thay đổi.';return}
 const j=await gui({viec:'luu',gia_tri:o},'Đang lưu…');if(j){Object.assign(S.gia_tri,o);if(j.noi_lai)cho()}}
// sau khi đổi phần MT5: hỏi trạng thái 2 giây một lần (tối đa 40 giây) tới khi nối xong hoặc có lý do cụ thể
async function cho(){$('#tt').innerHTML='<b>Đang nối lại…</b><span>webapp đang kiểm MT5 theo cấu hình mới</span>';const t0=Date.now();
 while(Date.now()-t0<40000){await new Promise(r=>setTimeout(r,2000));try{const j=await(await fetch('/api/cai-dat',{cache:'no-store'})).json();
  const k=j.ket_noi||{};if(k.co||(k.ly_do&&k.ly_do!=='đã ngắt')){S.ket_noi=k;S.ma_vang_goi_y=j.ma_vang_goi_y;S.mt5_dang_mo=j.mt5_dang_mo;ve();return}}catch(e){}}tai()}
tai();setInterval(()=>{if(document.visibilityState==='visible')fetch('/api/cai-dat',{cache:'no-store'}).then(r=>r.json()).then(j=>{S.ket_noi=j.ket_noi;ttVe()}).catch(()=>{})},10000)})();"""


def trang_cai_dat(ten: str) -> str:
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Cài đặt · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'cai-dat', '<button id="theme" type="button">Nền tối</button>') + '<main>',
        '<div class="top"><div><h1>Cài đặt</h1></div><div class="stamp">lưu vào cau-hinh.json trên máy này<br>bản trước giữ ở cau-hinh.json.bak</div></div>',
        '<div class="cd" id="cd"><p class="small">Đang đọc cài đặt…</p></div>',
        f'<footer>{escape(trang.MIEN_TRU)}</footer></main><script>{trang.JS}</script><script>{JS}</script></body></html>'])
