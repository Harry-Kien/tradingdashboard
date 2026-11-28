"""Cầu nối giữa máy chủ web và vỏ app Windows (app.py): trạng thái cho giao diện, các việc máy chủ làm hộ vỏ app, và ba mảnh giao diện.

Vỏ app mở webapp trong một cửa sổ riêng; giao diện vẫn là các trang web sẵn có, nên mọi việc của vỏ (hiện cửa sổ, mở thư mục dữ liệu,
kiểm và tải bản mới) đi qua /api/app: GET đọc trạng thái, POST {"viec": ...} làm việc (chỉ nhận từ chính trang của webapp trên máy này,
xem web.py: _cung_may). Mô-đun này không nhập app.py hay pywebview: app.py gán hàm và cổng vào VO, chạy từ mã nguồn thì VO để trống và mọi
việc của vỏ thành không làm gì. Kiểm và tải bản mới chỉ chạy ở bản đóng gói (cap_nhat.py tự chặn khi chạy từ mã nguồn)."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from . import cap_nhat, duong
from .phien_ban import PHIEN_BAN

# Cổng của webapp chạy riêng, ngoài app (R14): 8769 là webapp chạy từ mã nguồn (local_runtime.PORT, các tệp .bat), 8765 là bản zip cũ.
# App không bao giờ dùng hai cổng này (dải của app là 8790 tới 8800, xem app.UU_TIEN); có webapp trả lời ở đó thì máy đang chạy một bản riêng.
CONG_WEBAPP_RIENG = (8769, 8765)
VO: dict = {'hien': None, 'thoat': None, 'cong': None}   # app.py gán: hien() đưa cửa sổ lên trước, thoat() đóng app, cong = cổng app đang dùng
_nho_cong: dict = {}                                 # cổng → (lúc dò, kết quả): mỗi trang mở đều hỏi /api/app, không dò cổng cũ mỗi lần


def _hoi_get(url: str) -> tuple[int, bytes]:
    """GET một địa chỉ trên chính máy này (không qua proxy, hạn 1 giây): (mã HTTP, thân). Mã lỗi HTTP cũng trả về, không ném."""
    mo = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with mo.open(url, timeout=1) as r:                                   # noqa: S310 - địa chỉ http://127.0.0.1 cố định, chỉ đọc
            return r.status, r.read(4096)
    except urllib.error.HTTPError as e:
        return e.code, b''


def _co_webapp(cong: int, hoi=None) -> bool:
    """Có một webapp đang trả lời ở `cong` không (chỉ đọc, mỗi lần hỏi hạn 1 giây; nhớ kết quả 60 giây). Bản zip cũ trả 200 ở /api/tinh-trang.
    Webapp mới khóa /api/tinh-trang sau đăng nhập (401/403) nhưng /api/phien-ban thì công khai và có khóa `san_pham`: chỉ khi bị khóa mới
    hỏi tiếp chỗ đó, để chương trình lạ trả 401 không bị nhận nhầm là webapp. `hoi(url) -> (mã, thân)`: thay lời gọi mạng khi kiểm thử."""
    luc, kq = _nho_cong.get(cong, (0.0, False))
    if time.monotonic() - luc < 60:
        return kq
    hoi = hoi or _hoi_get
    goc = f'http://127.0.0.1:{int(cong)}'
    try:
        ma, _ = hoi(goc + '/api/tinh-trang')
        kq = ma == 200
        if ma in (401, 403):
            ma, than = hoi(goc + '/api/phien-ban')
            d = json.loads(than.decode('utf-8')) if ma == 200 else None
            kq = isinstance(d, dict) and 'san_pham' in d
    except (OSError, ValueError):
        kq = False
    _nho_cong[cong] = (time.monotonic(), kq)
    return kq


def trang_thai(cfg: dict, do_cong=None) -> dict:
    """Trạng thái cho giao diện (GET /api/app). `cap_nhat.ban_moi` là chuỗi phiên bản (không phải cả kê khai: địa chỉ tải và mã băm không
    ra tới trang). `ban_cu_8765` (giữ tên khóa cũ): đang chạy trong app và một cổng của CONG_WEBAPP_RIENG khác cổng của app có webapp trả
    lời, tức máy này còn chạy một webapp riêng (từ mã nguồn hay bản zip) với thư mục dữ liệu khác; `cong_webapp_rieng` là cổng đó (int) hoặc None."""
    tt = cap_nhat.trang_thai()
    bm = tt['ban_moi'] if isinstance(tt['ban_moi'], dict) else None
    cau = cfg.get('cap_nhat') if isinstance(cfg, dict) else None
    cong = VO['cong']
    rieng = None
    if cong is not None:                                                     # chạy từ mã nguồn (VO trống) thì không dò
        do = do_cong or _co_webapp
        rieng = next((c for c in CONG_WEBAPP_RIENG if c != cong and do(c)), None)
    return {'dong_goi': bool(duong.DONG_GOI), 'phien_ban': PHIEN_BAN, 'thu_muc_du_lieu': str(duong.goc_du_lieu()), 'cong': cong,
            'ban_cu_8765': rieng is not None, 'cong_webapp_rieng': rieng,
            'cap_nhat': {'bat': not (isinstance(cau, dict) and cau.get('bat') is False),    # không có mục cap_nhat thì coi như bật (như cap_nhat.kiem)
                         'ban_moi': str(bm['phien_ban']) if bm else None, 'ghi_chu': str(bm.get('ghi_chu') or '') if bm else '',
                         'lan_kiem': tt['lan_kiem'], 'loi': tt['loi'], 'dang_tai': bool(tt['dang_tai'])}}


def lam(viec: str, cfg: dict, mo=None, chay=None) -> tuple[int, dict]:
    """Một việc của POST /api/app. Trả (mã HTTP, thân JSON). `mo`, `chay`: hàm mở thư mục và hàm chạy bộ cài (mặc định os.startfile)."""
    if viec == 'hien':                                                       # lần mở thứ hai của app: đưa cửa sổ đang chạy lên trước
        if VO['hien']:
            VO['hien']()
        return 200, {'ok': True}
    if viec == 'mo_thu_muc':
        try:
            (mo or os.startfile)(str(duong.goc_du_lieu()))                   # Windows Explorer mở thư mục dữ liệu
        except OSError as e:
            return 500, {'loi': f'Không mở được thư mục dữ liệu: {e}'}
        return 200, {'ok': True}
    if viec == 'kiem_ngay':                                                  # nút "Kiểm ngay": bỏ qua hạn một ngày một lần
        cap_nhat.kiem(cfg, ep=True)
        return 200, trang_thai(cfg)
    if viec == 'tai_cap_nhat':
        if not duong.DONG_GOI:
            return 409, {'loi': 'Bản chạy từ mã nguồn không tự cập nhật.'}
        if not cap_nhat.trang_thai()['ban_moi']:
            return 409, {'loi': 'Chưa có bản mới để tải.'}
        ok, ly_do, bo_cai = cap_nhat.tai_bo_cai()                            # tải và so SHA-256; không khớp thì cap_nhat đã xóa tệp
        if not ok or bo_cai is None:
            return 409, {'loi': ly_do or 'Chưa có bản mới để tải.'}
        try:
            (chay or os.startfile)(str(bo_cai))                              # bộ cài đã kiểm mã băm; nó tự đóng app cũ nếu còn chạy
        except OSError as e:
            return 500, {'loi': f'Không chạy được bộ cài: {e}'}
        if VO['thoat']:                                                      # đóng app để bộ cài thay được tệp chương trình
            VO['thoat']()
        return 200, {'ok': True}
    return 400, {'loi': 'Việc không hỗ trợ.'}


# --------------------------------------------------------------------------- giao diện
# Mọi chữ tiếng Việt đứng trọn trong một chuỗi (hoặc một mảnh trước số) để bộ dịch (dich.py) đổi được sang tiếng Anh; thêm chữ mới thì thêm
# bản dịch vào so_cong_khai/dich/en.json. Lệnh ghi gửi tiêu đề X-So-Cong-Khai như cai_dat.JS.

# Khối "Ứng dụng" của trang Cài đặt, đặt ngay sau <div id="cd"> (nằm ngoài #cd vì cai_dat.JS vẽ lại toàn bộ #cd). Ô tự kiểm mang
# data-k="cap_nhat.bat" nên nút "Lưu cài đặt" sẵn có lưu luôn nó; ô bị khóa (layGT bỏ qua) cho tới khi đọc xong /api/app, để không lưu nhầm
# giá trị mặc định. Phần bản mới chỉ hiện ở bản đóng gói: chạy từ mã nguồn thì app không tự kiểm.
KHOI_CAI_DAT = f"""<div class="cd" id="cd-app"><style>#cd-app [hidden]{{display:none!important}}#cd-app .hang>div{{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px}}
#cd-app code{{font-size:12.5px;word-break:break-all;color:var(--ink2)}}#app-kq{{margin:8px 0 0}}#app-kq:empty{{display:none}}#app-kq.loi{{color:var(--loss)}}</style>
<section class="card"><h2>Ứng dụng</h2>
 <div class="hang"><label>Phiên bản {PHIEN_BAN}</label><div><span id="app-ban" hidden></span><button type="button" class="phu" id="app-kiem" hidden>Kiểm ngay</button></div></div>
 <div class="hang"><label>Thư mục dữ liệu</label><div><code id="app-thu-muc"></code><button type="button" class="phu" id="app-mo">Mở thư mục dữ liệu</button></div></div>
 <div class="hang" id="app-tu-kiem" hidden><label for="cap_nhat.bat">Tự kiểm bản mới mỗi ngày</label><div><input type="checkbox" id="cap_nhat.bat" data-k="cap_nhat.bat" disabled></div></div>
 <p class="small" id="app-kq" aria-live="polite"></p>
</section></div>
<script>(()=>{{const $=i=>document.getElementById(i),HDR={{'Content-Type':'application/json','X-So-Cong-Khai':'1'}};
const bao=(t,loi)=>{{const k=$('app-kq');k.textContent=t||'';k.className='small'+(loi?' loi':'')}};
function ve(j){{const c=j.cap_nhat||{{}};$('app-thu-muc').textContent=j.thu_muc_du_lieu||'';if(!j.dong_goi)return;
 const b=$('app-ban');b.textContent=c.ban_moi?'Có bản '+c.ban_moi+'.':'Đang dùng bản mới nhất.';b.hidden=false;$('app-kiem').hidden=false;
 const o=$('cap_nhat.bat');if(o.disabled){{o.checked=!!c.bat;o.disabled=false}}$('app-tu-kiem').hidden=false;if(c.loi)bao(c.loi,true)}}
async function gui(viec){{const r=await fetch('/api/app',{{method:'POST',headers:HDR,body:JSON.stringify({{viec}})}});const j=await r.json().catch(()=>({{}}));
 if(!r.ok)throw new Error(j.loi||j.thong_bao||('HTTP '+r.status));return j}}
fetch('/api/app',{{cache:'no-store'}}).then(r=>r.ok?r.json():null).then(j=>{{if(j)ve(j)}}).catch(()=>{{}});
$('app-mo').onclick=()=>{{bao('');gui('mo_thu_muc').catch(e=>bao('Không gửi được: '+e.message,true))}};
$('app-kiem').onclick=async()=>{{const b=$('app-kiem');b.disabled=true;bao('Đang kiểm…');
 try{{const j=await gui('kiem_ngay');bao('');ve(j)}}catch(e){{bao('Không gửi được: '+e.message,true)}}finally{{b.disabled=false}}}}}})();</script>"""

# Dải báo bản mới, nối vào cuối trang.JS nên chạy ở mọi trang (kể cả trang tĩnh của sổ công khai, nơi /api/app không có: lỗi thì im lặng).
# Một lần hỏi /api/app; chỉ hiện khi là bản đóng gói và có bản mới. Không bao giờ ném lỗi ra ngoài.
JS_DAI_BAO = r"""
(()=>{try{const M=document.querySelector('main');if(!M||!window.fetch)return;
fetch('/api/app',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(j=>{const c=j&&j.dong_goi&&j.cap_nhat;if(!c||!c.ban_moi||document.getElementById('app-dai'))return;
 const d=document.createElement('div'),t=document.createElement('b'),b=document.createElement('button'),k=document.createElement('span');
 d.id='app-dai';d.className='note';d.setAttribute('role','status');d.style.cssText='display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px';
 t.textContent='Có bản mới '+c.ban_moi+'.';b.type='button';b.className='go';b.textContent='Tải bản mới';
 const dang=()=>{b.disabled=true;k.textContent='Đang tải bản mới…'};if(c.dang_tai)dang();
 b.addEventListener('click',()=>{if(!confirm('App sẽ đóng để cài bản mới. Tiếp tục?'))return;dang();
  fetch('/api/app',{method:'POST',headers:{'Content-Type':'application/json','X-So-Cong-Khai':'1'},body:JSON.stringify({viec:'tai_cap_nhat'})})
  .then(r=>r.json().catch(()=>({})).then(x=>{if(!r.ok){k.textContent=x.loi||x.thong_bao||('HTTP '+r.status);b.disabled=false}}))
  .catch(e=>{k.textContent='Không gửi được: '+e.message;b.disabled=false})});
 d.append(t,b,k);M.prepend(d)}).catch(()=>{})}catch(e){}})();
"""

# Dòng báo trên trang Bắt đầu khi máy còn chạy một webapp riêng (cổng 8769 hay 8765, xem CONG_WEBAPP_RIENG): app dùng thư mục dữ liệu riêng
# nên người dùng sẽ thấy app "trống". Câu đứng trọn trong MỘT chuỗi với số 8765 để bộ dịch tra được mục "…ở cổng {0}…" của en.json (số được
# đặt lại nguyên văn vào bản dịch); rồi mới thay 8765 bằng cổng thật mà /api/app báo, ở cả hai ngôn ngữ.
JS_BAT_DAU = r"""
(()=>{try{fetch('/api/app',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(j=>{if(!j||!j.ban_cu_8765)return;const o=document.querySelector('.bd-top');if(!o)return;
 const p=document.createElement('p');p.className='note';p.style.marginTop='12px';
 p.textContent='Máy này đang chạy một webapp bản cũ ở cổng 8765. App dùng thư mục dữ liệu riêng nên chưa thấy hình vẽ và nhật ký cũ của bạn; xem mục "Chuyển từ bản zip" trong hướng dẫn.'.replace('8765',String(j.cong_webapp_rieng||8765));
 o.appendChild(p)}).catch(()=>{})}catch(e){}})();
"""
