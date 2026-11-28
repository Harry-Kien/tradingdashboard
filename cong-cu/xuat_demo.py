"""Xuất website tĩnh bằng dữ liệu giả lập, độc lập API/MT5/cấu hình riêng.
Chạy: python -X utf8 cong-cu/xuat_demo.py [thư_mục_ra].
Xuất vào thư mục mới rồi thay bản cũ; không giữ lại ảnh chụp hay dữ liệu cũ.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape, unescape
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import (dich, hieu_suat, hieu_suat_trang, ke_hoach, ke_hoach_js, ke_hoach_trang, ky_luat, ky_luat_trang,  # noqa: E402
                          thi_truong_trang, thuong_hieu, tong_quan)
from so_cong_khai.doc_so import VN  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demo_mau
import gioi_thieu  # noqa: E402  (trang giới thiệu index.html, cùng thư mục cong-cu)

KHO = 'https://github.com/Harry-Kien/tradingdashboard'
TRANG_WEB = 'https://harry-kien.github.io/tradingdashboard/'
TEN = thuong_hieu.TEN
NGAY = (7, 30, 90, 365, 0)
CHIEU = ('', 'MUA', 'BAN')
TRANG_DEMO = {'/': 'tong-quan.html', '/tong-quan': 'tong-quan.html', '/hieu-suat': 'hieu-suat.html', '/thi-truong': 'thi-truong.html', '/ke-hoach': 'ke-hoach.html',
              '/ky-luat': 'ky-luat.html'}                                      # đường dẫn webapp → tệp demo; index.html là trang giới thiệu
TEP_KL = {'': 'all', 'Đặt tay': 'dat-tay', 'EA mẫu': 'ea-mau', 'Manual': 'dat-tay', 'Sample EA': 'ea-mau'}   # nguồn lệnh (Việt/Anh) → tên tệp Kỷ luật
VON_MAU = 10000.0                                                              # vốn mẫu của trang Kế hoạch khi người xem để trống ô vốn
TK_CHUNG = {'tien': 'USD', 'don_bay': 100, 'goi_ky_quy': 50.0, 'dung_lenh': 0.0, 'san': ''}   # thay thông số tài khoản thật

CSS_DEMO = """<style>#hs-mau,#hs-csv,#hs-ma,#hs-nguon{display:none!important}
.demo-bang{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;justify-content:space-between;margin:0 0 16px;padding:12px 16px;border-radius:14px;
border:1px solid color-mix(in srgb,var(--series) 40%,var(--line));background:color-mix(in srgb,var(--series) 8%,var(--card))}
.demo-bang p{margin:0;font-size:13.5px;color:var(--ink2);flex:1 1 320px}.demo-bang b{color:var(--ink)}
.demo-bang a{display:inline-flex;align-items:center;min-height:36px;padding:0 14px;border-radius:10px;background:var(--series);color:#0b0d09;font-weight:700;font-size:13px;text-decoration:none}
</style>"""


def js_chup(luc: datetime) -> str:
    """Ô trạng thái giá ("Trực tiếp · cập nhật x giây trước") luôn ghi đúng là ảnh chụp: viết lại ngay mỗi lần trang vẽ ô đó."""
    t = luc.astimezone(VN)
    nc = f'<i></i><b>Ảnh chụp</b> · giá lúc {t:%H:%M} {t:%d/%m/%Y} (giờ Việt Nam)'
    return ('<script>(()=>{const NC=' + json.dumps(nc, ensure_ascii=False) + ',gan=el=>{if(el.__nc!==undefined&&el.innerHTML===el.__nc)return;'
            'el.className="song-pill";el.innerHTML=NC;el.__nc=el.innerHTML};'
            'new MutationObserver(()=>document.querySelectorAll(".song-pill").forEach(gan)).observe(document.documentElement,{childList:true,subtree:true,characterData:true})})();</script>')


def js_demo(doi_ngon_ngu: str) -> str:
    """Chặn fetch /api/... sang tệp JSON dựng sẵn, thay luồng giá trực tiếp bằng luồng rỗng, liên kết tới trang có trong demo thì mở trong demo,
    trang khác mở kho mã nguồn; nút EN/VI chuyển giữa hai bản."""
    return ('<script>(()=>{try{localStorage.setItem("hs-loc",JSON.stringify(Object.assign(JSON.parse(localStorage.getItem("hs-loc")||"{}"),'
            '{ma:"",nguon:"",mau:true})))}catch(e){}'
            f'const KHO={json.dumps(KHO)},TRANG={json.dumps(TRANG_DEMO)},_f=window.fetch.bind(window);'
            'const tep=u=>{const[p,q0]=u.split("?"),q=new URLSearchParams(q0||"");'
            'if(p==="/api/hieu-suat")return"du-lieu/hs-"+(q.get("ngay")||"90")+"-"+(q.get("chieu")||"all")+".json";'
            'if(p==="/api/thi-truong")return"du-lieu/tt.json";'
            'const OV={"/api/tai-khoan":"account","/api/tong-quan/so":"ledger","/api/canh-bao":"activity","/api/giam-sat":"risk","/api/tinh-trang":"health"};if(OV[p])return"du-lieu/overview/"+OV[p]+".json";'
            f'if(p==="/api/ky-luat"){{const KL={json.dumps(TEP_KL, ensure_ascii=False)};'
            'return"du-lieu/kl/"+(["7","30","90"].includes(q.get("ngay"))?q.get("ngay"):"30")+"-"+(KL[q.get("nguon")||""]||"all")+".json"}'
            'if(p==="/api/thi-truong/ky-thuat")return"du-lieu/kt/"+encodeURIComponent(q.get("ma")||"")+".json";'
            'if(p==="/api/thi-truong/bien-dong")return"du-lieu/bd/"+encodeURIComponent(q.get("ma")||"")+".json";return null};'
            # trang Kế hoạch: tính ngay trong trình duyệt (KH của ke_hoach_js) từ dữ liệu thô đã chụp cho mã và khung
            'const keHoach=async u=>{const q=new URLSearchParams(u.split("?")[1]||""),ma=q.get("ma")||"",kh=q.get("khung")||"H1",so=k=>q.get(k)!=null&&q.get(k)!==""?+q.get(k):null;'
            'try{const r=await _f("du-lieu/kh/"+encodeURIComponent(ma)+"-"+kh+".json");if(!r.ok)throw new Error("Bản demo không có mã này");const raw=await r.json();'
            'const tk=await _f("du-lieu/kh/tk.json").then(x=>x.json());'
            'const p={chieu:q.get("chieu"),khung:kh,muc:q.get("muc")||"can_bang",rui_ro:so("rui_ro"),von:so("von"),vao:so("vao"),sl:so("sl"),thang:so("thang")??50,rr:so("rr")??2};'
            # cùng điều kiện như /api/ke-hoach của máy chủ: số phải hữu hạn, vốn/giá dương, tỷ lệ thắng 0–100, R:R tối đa 20
            'for(const k of["von","vao","sl","rui_ro","thang","rr"])if(p[k]!=null&&!isFinite(p[k]))throw new Error("số không hợp lệ");'
            'if([p.von,p.vao,p.sl].some(x=>x!=null&&x<=0))throw new Error("vốn, giá vào và dừng lỗ phải dương");'
            'if(p.thang<0||p.thang>100||!(p.rr>0&&p.rr<=20))throw new Error("thang phải trong [0, 100], rr trong (0, 20]");'
            'const d=KH.lap(raw,p,tk);if(p.von==null)d.nguon_von="mau";return new Response(JSON.stringify(d),{headers:{"Content-Type":"application/json"}})}'
            'catch(e){return new Response("Yêu cầu không hợp lệ: "+e.message,{status:400})}};'
            'window.fetch=(u,o)=>{if(typeof u==="string"&&u.startsWith("/api/ke-hoach?")&&typeof KH!=="undefined")return keHoach(u);'
            'if(typeof u==="string"&&u.startsWith("/api/")){const t=tep(u);'
            'return t?_f(t):Promise.resolve(new Response(JSON.stringify({loi:"Bản demo không có mục này"}),{status:404,headers:{"Content-Type":"application/json"}}))}'
            'return _f(u,o)};'
            'window.EventSource=class{constructor(u){this.url=u;this.readyState=1}close(){this.readyState=2}addEventListener(){}removeEventListener(){}};'
            f'document.addEventListener("click",e=>{{if(e.target.closest("#nv-lang")){{e.preventDefault();e.stopImmediatePropagation();location.href={json.dumps(doi_ngon_ngu)};return}}'
            'const a=e.target.closest("a[href^=\'/\']");if(!a||a.hasAttribute("download"))return;e.preventDefault();e.stopImmediatePropagation();'
            'const h=a.getAttribute("href"),p=h.split(/[?#]/)[0],m=h.match(/#.*/);'
            'if(TRANG[p])location.href=TRANG[p]+(m?m[0]:"");else window.open(KHO+"#readme","_blank","noopener")},true)})();</script>')


def bang_demo(loai: str, luc: datetime | None = None) -> str:
    if loai == 'tong-quan':
        noi = '<b>Bản demo · Dữ liệu giả lập hoàn toàn.</b> Trải nghiệm tổng quan, lọc sổ và công cụ. Không kết nối MT5, không phải dữ liệu hay kết quả của chủ hệ thống.'
    elif loai == 'ky-luat':
        noi = ('<b>Bản demo trực tuyến</b> với lệnh minh họa có cài sẵn vài thói quen xấu thường gặp (vào lại ngay sau lệnh thua với khối lượng lớn hơn, '
               'đặt rủi ro quá lớn, quên dừng lỗ), chấm theo quy tắc mặc định: rủi ro tối đa 2% mỗi lệnh, lỗ ngày 3%, tối đa 10 lệnh mỗi ngày. '
               'Bản cài trên máy chấm lại lệnh thật của bạn trong MT5, theo đúng quy tắc bạn đặt.')
    elif loai == 'ke-hoach':
        t = luc.astimezone(VN) if luc else None
        chup = f' Giá và nến chụp lúc {t:%H:%M} ngày {t:%d/%m/%Y} (giờ Việt Nam).' if t else ''
        von = f'{VON_MAU:,.0f}'.replace(',', '.')
        noi = (f'<b>Bản demo trực tuyến</b>: để trống ô vốn thì dùng vốn mẫu {von} USD, hoặc nhập vốn của bạn.{chup} '
               'Bản cài trên máy dùng vốn, giá và nến trực tiếp từ MT5 của bạn, và có thêm trang Kiểm tra trước khi vào lệnh.')
    elif loai == 'thi-truong':
        t = luc.astimezone(VN) if luc else None
        chup = f' Giá chụp lúc {t:%H:%M} ngày {t:%d/%m/%Y} (giờ Việt Nam), không cập nhật trực tiếp.' if t else ''
        noi = (f'<b>Bản demo trực tuyến</b>.{chup} Bản cài trên máy nhận giá theo từng tick từ MT5 của bạn, '
               'có thêm biểu đồ, tin tức, công cụ tính và phân tích lệnh thật của bạn.')
    else:
        noi = ('<b>Bản demo trực tuyến</b> với 260 lệnh minh họa. Bản cài trên máy đọc lịch sử lệnh thật từ MT5 của bạn '
               'và có thêm bảng giá trực tiếp, tín hiệu kỹ thuật, tin tức, biểu đồ và công cụ tính.')
    return f'<div class="demo-bang"><p>{noi}</p><a href="{KHO}#readme" target="_blank" rel="noopener">Cài miễn phí trên GitHub</a></div>'


def the_meta(lang: str, loai: str) -> str:
    if loai == 'tong-quan':
        tieu = 'Tổng quan phiên giao dịch · demo' if lang == 'vi' else 'Your trading overview · demo'
        mo = ('Trải nghiệm tổng quan, bảng giá, sổ nghiên cứu và công cụ quản lý rủi ro bằng dữ liệu giả lập hoàn toàn.' if lang == 'vi'
              else 'Explore the overview, markets, research journals and risk planning tools with entirely synthetic data.')
        anh = TRANG_WEB + 'logo.png'
    elif loai == 'ky-luat':
        tieu = 'Kỷ luật giao dịch · demo' if lang == 'vi' else 'Trading discipline · demo'
        mo = ('Chấm lại từng lệnh đã đóng: lệnh đúng quy tắc và lệnh phạm quy tắc lãi lỗ khác nhau bao nhiêu, thói quen nào đang tốn tiền.' if lang == 'vi'
              else 'Re-checks every closed trade: how rule-following and rule-breaking trades differ in profit, and which habits cost money.')
        anh = TRANG_WEB + 'logo.png'
    elif loai == 'ke-hoach':
        tieu = 'Kế hoạch vốn và lệnh · demo' if lang == 'vi' else 'Money and trade plan · demo'
        mo = ('Nhập vốn và thử tính khối lượng, dừng lỗ, chốt lời, ký quỹ và rủi ro trên giá và nến minh họa.' if lang == 'vi'
              else 'Enter your capital and explore position sizing, stop loss, take profit, margin and risk using sample prices and candles.')
        anh = TRANG_WEB + 'logo.png'
    elif loai == 'thi-truong':
        tieu = 'Bảng giá Forex & CFD · demo' if lang == 'vi' else 'Forex & CFD market board · demo'
        mo = ('Bảng giá, tín hiệu kỹ thuật 19 chỉ báo × 4 khung, sức mạnh tiền tệ, tương quan, lịch tin — từ MT5 của bạn.' if lang == 'vi'
              else 'Price board, technical ratings (19 indicators × 4 timeframes), currency strength, correlation and calendar — from your MT5.')
        anh = TRANG_WEB + 'logo.png'
    else:
        tieu = 'Phân tích hiệu suất giao dịch · demo' if lang == 'vi' else 'Trading performance analytics · demo'
        mo = ('Bạn thắng, thua ở đâu: chỉ số, đường vốn, lịch lãi/lỗ, nhận xét tự động từ lịch sử MT5.' if lang == 'vi'
              else 'Where you win and lose: stats, equity curve, P/L calendar and automatic insights from your MT5 history.')
        anh = TRANG_WEB + 'logo.png'
    return (f'<meta name="description" content="{escape(mo)}"><meta property="og:type" content="website">'
            f'<meta property="og:title" content="{escape(tieu)}"><meta property="og:description" content="{escape(mo)}">'
            f'<meta property="og:image" content="{anh}"><meta name="twitter:card" content="summary_large_image">')


KHO_MAY = GOC.parent / 'tradingdashboard'                                       # bản sao kho công khai trên máy (nếu có)


def _cong_khai() -> tuple[set[str], bool] | None:
    """Các trang (đường dẫn) và nút kênh Telegram đã có trong kho công khai trên máy; None nếu máy không có bản sao kho."""
    w, t = KHO_MAY / 'so_cong_khai' / 'web.py', KHO_MAY / 'so_cong_khai' / 'thuong_hieu.py'
    if not w.exists():
        return None
    duong = set(re.findall(r"'(/[a-z0-9][a-z0-9\-/.]*)'", w.read_text(encoding='utf-8')))          # mọi đường dẫn web.py nhắc tới
    return duong, t.exists() and 'KENH_TELEGRAM' in t.read_text(encoding='utf-8')


def loc_cong_khai(html: str) -> str:
    """Bỏ khỏi thanh điều hướng và ô tìm nhanh các trang chưa có ở bản công khai (đang làm dở trên máy), và nút kênh Telegram nếu kho chưa có:
    demo chỉ giới thiệu đúng những gì người tải về nhận được."""
    ck = _cong_khai()
    if ck is None:
        return html
    duong, co_kenh = ck
    an = lambda h: h.startswith('/') and h != '/' and h.split('#')[0].split('?')[0] not in duong   # noqa: E731
    html = re.sub(r'<a class="nv-[id]" href="([^"]+)"[^>]*>.*?</a>', lambda m: '' if an(m.group(1)) else m.group(0), html, flags=re.S)

    def _tim(m):
        try:
            ds = json.loads(unescape(m.group(1)))
        except ValueError:
            return m.group(0)
        return 'data-tim="' + escape(json.dumps([x for x in ds if not an(x.get('h', ''))], ensure_ascii=False), quote=True) + '"'
    html = re.sub(r'data-tim="([^"]*)"', _tim, html)
    if not co_kenh:
        html = re.sub(r'<a class="nv-tg"[^>]*>.*?</a>', '', html, flags=re.S)
    return html


def trang(lang: str, loai: str = 'hieu-suat', luc: datetime | None = None) -> str:
    goc = '' if lang == 'vi' else '../'
    tep = TRANG_DEMO['/' + loai]
    if loai == 'ky-luat':
        # demo chấm theo quy tắc mặc định (dữ liệu dựng sẵn): ẩn ô sửa quy tắc để người xem không tưởng là đổi được
        html = ky_luat_trang.trang_ky_luat(TEN).replace('</head>', '<style>details.ky-qt{display:none!important}</style></head>', 1)
    elif loai == 'ke-hoach':
        html = ke_hoach_trang.trang_ke_hoach(TEN).replace('Vốn (để trống: lấy vốn từ MT5)', 'Vốn (để trống: vốn mẫu 10.000 USD)').replace(
            'placeholder="Lấy từ MT5"', 'placeholder="10.000"')
        html = html.replace('<script>', f'<script>{ke_hoach_js.JS_TINH}</script><script>', 1)
    elif loai == 'tong-quan':
        html = tong_quan.trang_tong_quan(TEN).replace('<button type="button" class="tq-btn" id="tq-logout">Đăng xuất</button>', '<button type="button" id="tq-logout" hidden disabled></button>')
    else:
        html = thi_truong_trang.trang_thi_truong(TEN) if loai == 'thi-truong' else hieu_suat_trang.trang_hieu_suat(TEN)
    if loai == 'tong-quan':
        html = html.replace("a.href='/kiem-lenh'", "a.href='/ke-hoach'").replace('href="/kiem-lenh"', 'href="/ke-hoach"')
        html = html.replace('Kiểm tra trước khi vào lệnh →', 'Thử lập kế hoạch vốn →')
        html = html.replace("'/bieu-do?ma='", "'/thi-truong?ma='").replace('href="/bieu-do', 'href="/thi-truong')
        html = html.replace('Mở biểu đồ & phân tích →', 'Khám phá bảng giá →')
        html = re.sub(r'<div class="tq-tool" data-tool="(?:check|learn)">.*?</button></div>', '', html, flags=re.S)
        html = html.replace('href="/so-cong-khai', 'href="/hieu-suat').replace('href="/bat-dau', f'href="{KHO}#readme')
        html = html.replace('<a href="/so-cong-khai#${encodeURIComponent(r.id)}">', '<a href="/hieu-suat">')
        html = html.replace('Biểu đồ & phân tích', 'Thị trường & bảng giá').replace('Chỉ báo, hình vẽ, cảnh báo giá', 'Theo dõi giá, sức mạnh và biến động')
        html = html.replace('Các mục vừa kiểm tra đang hoạt động', 'Trạng thái minh họa · không kiểm tra MT5')
    html = loc_cong_khai(html).replace('url(/tinh/phong/', f'url({goc}tinh/phong/')
    i = html.index('<main')
    j = html.index('>', i) + 1
    html = html[:j] + bang_demo(loai, luc) + html[j:]
    html = html.replace('</head>', CSS_DEMO + '</head>', 1)
    sau = f'en/{tep}' if lang == 'vi' else f'../{tep}'
    i = html.index('<script>')
    html = html[:i] + js_demo(sau) + (js_chup(luc) if loai == 'thi-truong' and luc else '') + html[i:]
    if lang != 'vi':
        html = dich.dich_phan_hoi(html.encode('utf-8'), 'text/html', lang).decode('utf-8')
        if loai == 'ke-hoach':                                               # số vốn mẫu viết kiểu tiếng Anh
            html = html.replace('10.000 USD', '10,000 USD').replace('placeholder="10.000"', 'placeholder="10,000"')
    html = html.replace('Giá MT5', 'Giá minh họa').replace('Giá chưa mới', 'Ảnh minh họa').replace('Tài khoản đang nối trong MT5', 'Tài khoản giả lập').replace('Tự cập nhật mỗi 30 giây khi mở trang', 'Dữ liệu giả lập cố định').replace('Bản demo trực tuyến</b>.', 'Bản demo trực tuyến</b> · Dữ liệu giả lập hoàn toàn.').replace('Giá và nến chụp lúc', 'Giá và nến giả lập lúc').replace('Giá chụp lúc', 'Giá giả lập lúc')
    html = html.replace('</title>', '</title>' + the_meta(lang, loai), 1)
    chu = re.sub(r'<(script|style)\b.*?</\1>', '', html, flags=re.S)                # chỉ soát chữ người xem thấy, bỏ mã JS/CSS
    con = set(re.findall(r'[À-ỹ]{2,}', chu)) if lang != 'vi' else set()
    if con:
        print(f'  chú ý: {loai} bản {lang} còn {len(con)} từ có dấu tiếng Việt (ví dụ {sorted(con)[:5]})')
    return html


def _lay(goc: str, p: str, timeout: int = 60):
    rq = urllib.request.Request(goc + p, headers={'Cookie': 'lang=vi'})
    with urllib.request.urlopen(rq, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def chup_thi_truong(goc: str) -> dict | None:
    """Ảnh chụp dữ liệu trang Thị trường từ webapp đang chạy; None nếu không lấy được. Bỏ tên sàn và thông số tài khoản."""
    try:
        tt = _lay(goc, '/api/thi-truong')
    except Exception as e:                                                   # noqa: BLE001
        print(f'  bỏ qua trang Thị trường: không đọc được {goc} ({e})')
        return None
    if not tt.get('san_sang') or not tt.get('ds'):
        print('  bỏ qua trang Thị trường: webapp chưa có bảng giá (chưa nối MT5?)')
        return None
    tt['tai_khoan'] = dict(TK_CHUNG, tien=(tt.get('tai_khoan') or {}).get('tien') or 'USD')
    kt, bd = {}, {}
    for x in tt['ds']:
        ma = x['ma']
        for kho, p in ((kt, '/api/thi-truong/ky-thuat'), (bd, '/api/thi-truong/bien-dong')):
            try:
                kho[ma] = _lay(goc, f'{p}?ma={urllib.parse.quote(ma)}')
            except Exception:                                                # noqa: BLE001
                pass
    return {'tt': tt, 'kt': kt, 'bd': bd, 'luc': datetime.fromisoformat(tt['luc']) if tt.get('luc') else datetime.now(timezone.utc)}


def chup_ke_hoach(goc: str, tt: dict) -> dict:
    """Dữ liệu thô của trang Kế hoạch (thông số mã, giá, ATR, đỉnh/đáy nến) cho mọi mã có giá trong ảnh chụp Thị trường × ba khung."""
    out = {}
    for x in tt.get('ds') or []:
        if not x.get('q'):
            continue
        for kh in ke_hoach.KHUNG:
            try:
                out[(x['ma'], kh)] = _lay(goc, f'/api/ke-hoach/nen?ma={urllib.parse.quote(x["ma"])}&khung={kh}')
            except Exception:                                                # noqa: BLE001
                pass
    return out


def ky_luat_demo(now: datetime) -> dict:
    """Kết quả trang Kỷ luật cho 260 lệnh minh họa của hieu_suat.mau() (cùng dữ liệu với trang Hiệu suất của demo), theo quy tắc mặc định:
    {(số ngày, tên tệp nguồn): câu trả lời như /api/ky-luat}. Số dư trước mỗi lệnh dựng từ vốn đầu và lãi lỗ các lệnh đã đóng trước đó."""
    import random                                                            # noqa: PLC0415
    ds, dau = hieu_suat.mau(now=now)
    # cài thêm (theo hạt giống cố định) hai thói quen xấu thường gặp để trang có việc để chỉ ra: vào lại 5–10 phút sau lệnh thua với khối lượng
    # gấp 2,5 lần (thường thua tiếp), và vài lệnh đặt rủi ro gấp 5 lần bình thường
    rnd = random.Random(11)
    ds = sorted((dict(x) for x in ds), key=lambda x: x['mo'])
    for i in range(1, len(ds)):
        x, truoc = ds[i], ds[i - 1]
        he_so = 1.0
        if truoc['rong'] < 0 and rnd.random() < 0.3:
            giu = datetime.fromisoformat(x['dong']) - datetime.fromisoformat(x['mo'])
            mo = datetime.fromisoformat(truoc['dong']) + timedelta(minutes=rnd.randint(5, 10))
            if mo + giu < now:
                x['mo'], x['dong'] = mo.isoformat(), (mo + giu).isoformat()
                he_so = 2.5
                if x['rong'] > 0 and rnd.random() < 0.5:                     # vào để gỡ thì hay thua tiếp
                    x['rong'] = -x['rong'] * 0.8
        elif rnd.random() < 0.06:
            he_so = 5.0
        if he_so != 1.0:
            x['lot'] = round(x['lot'] * he_so, 2)
            x['rong'] = round(x['rong'] * he_so, 2)
            x['rui_ro'] = round(x['rui_ro'] * he_so, 2) if x['rui_ro'] else None
    dong = sorted(ds, key=lambda x: x['dong'])

    def so_du_truoc(t: str) -> float:
        return round(dau + sum(x['rong'] for x in dong if x['dong'] < t), 2)
    gd = []
    for x in ds:
        mo = datetime.fromisoformat(x['mo'])
        dau_ngay = datetime.combine(mo.astimezone(VN).date(), datetime.min.time(), tzinfo=VN).astimezone(timezone.utc).isoformat()
        gd.append({'id': x['id'], 'ma': x['ma'], 'chieu': x['chieu'], 'mo': x['mo'], 'dong': x['dong'], 'lot': x['lot'], 'vao': x['vao'], 'ra': x['ra'],
                   'sl': x['sl'], 'dong_boi_sl': False, 'lai': x['rong'], 'nguon': x['nguon'], 'von_truoc': so_du_truoc(x['mo']),
                   'von_dau_ngay': so_du_truoc(dau_ngay), 'rui_ro_tien': x['rui_ro'], 'tien_lien_quan': [x['ma'][:3], x['ma'][3:6]]})
    cac_nguon = sorted({x['nguon'] for x in gd})
    out = {}
    for ngay in (7, 30, 90):
        moc = (now - timedelta(days=ngay)).isoformat()
        for nguon in ('', *cac_nguon):
            con = [x for x in gd if x['dong'] >= moc and (not nguon or x['nguon'] == nguon)]          # tên tiếng Anh map qua TEP_KL trong lớp chặn
            out[(ngay, TEP_KL[nguon])] = {'san_sang': True, 'luc': now.isoformat(), 'ngay': ngay, 'tien': 'USD', 'nguon': nguon or None,
                                          'cac_nguon': cac_nguon, 'ly_do_tin': None, **ky_luat.cham(con)}
    return out


def _ghi(p: Path, o) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


def _build(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    goc_web = ''
    if '--goc' in argv:
        raise ValueError('Bản xuất công khai chỉ nhận dữ liệu giả lập; không đọc máy chủ cá nhân.')
    ra = Path(argv[0]) if argv else GOC / 'out' / 'demo'
    ra.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    cfg = {'gia': {}}
    hieu_suat._nho.clear()
    chup, kh, overview = demo_mau.tao(now)
    kl = ky_luat_demo(now)
    for lang, thu in (('vi', ra), ('en', ra / 'en')):
        (thu / 'du-lieu').mkdir(parents=True, exist_ok=True)
        d = dich.tu_dien(lang) if lang != 'vi' else None
        dj = (lambda o: dich.dich_json(o, d)) if d else (lambda o: o)
        for n in NGAY:
            for c in CHIEU:
                _ghi(thu / 'du-lieu' / f'hs-{n}-{c or "all"}.json', dj(hieu_suat.lay(cfg, n, '', c, '', dung_mau=True, now=now)))
        for key, value in overview.items():
            _ghi(thu / 'du-lieu' / 'overview' / (key + '.json'), dj(value))
        (thu / 'tong-quan.html').write_text(trang(lang, 'tong-quan'), encoding='utf-8')
        (thu / 'hieu-suat.html').write_text(trang(lang), encoding='utf-8')
        (thu / 'index.html').write_text(gioi_thieu.trang(lang), encoding='utf-8')            # trang giới thiệu (gốc của tên miền)
        for (ngay, tep), o in kl.items():
            _ghi(thu / 'du-lieu' / 'kl' / f'{ngay}-{tep}.json', dj(o))
        (thu / 'ky-luat.html').write_text(trang(lang, 'ky-luat'), encoding='utf-8')
        if chup:
            _ghi(thu / 'du-lieu' / 'tt.json', dj(chup['tt']))
            for ma, o in chup['kt'].items():
                _ghi(thu / 'du-lieu' / 'kt' / f'{ma}.json', dj(o))
            for ma, o in chup['bd'].items():
                _ghi(thu / 'du-lieu' / 'bd' / f'{ma}.json', dj(o))
            (thu / 'thi-truong.html').write_text(trang(lang, 'thi-truong', chup['luc']), encoding='utf-8')
        if kh:
            for (ma, k), o in kh.items():
                _ghi(thu / 'du-lieu' / 'kh' / f'{ma}-{k}.json', o)
            _ghi(thu / 'du-lieu' / 'kh' / 'tk.json', {'tien': 'USD', 'don_bay': 100, 'dung_lenh': 50.0, 'von': VON_MAU})
            (thu / 'ke-hoach.html').write_text(trang(lang, 'ke-hoach', chup['luc']), encoding='utf-8')
    phong = ra / 'tinh' / 'phong'
    phong.mkdir(parents=True, exist_ok=True)
    for f in (GOC / 'tinh' / 'phong').glob('*.woff2'):
        shutil.copy2(f, phong / f.name)
    (ra / 'demo-cover.svg').write_text(demo_mau.cover(), encoding='utf-8')
    logo = KHO_MAY / 'docs' / 'logo.png'
    if logo.is_file():
        shutil.copy2(logo, ra / 'logo.png')
    _ghi(ra / 'privacy-manifest.json', {'schema': 1, 'data_source': 'synthetic_only', 'live_api': False, 'mt5': False, 'owner_data': False})
    (ra / '.nojekyll').write_text('', encoding='utf-8')
    tong = sum(f.stat().st_size for f in ra.rglob('*') if f.is_file())
    print(f'Đã xuất demo vào {ra} ({tong / 1e6:.1f} MB){"" if chup else " — chưa có trang Thị trường"}. '
          f'Mở {ra / "index.html"} qua một máy chủ tĩnh, ví dụ: python -m http.server -d "{ra}"')
    return 0


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1 or any(x.startswith('--') for x in args):
        raise ValueError('Chỉ nhận thư mục xuất; bản công khai không đọc API cá nhân.')
    raw_target = Path(args[0]) if args else GOC / 'out' / 'demo'
    if raw_target.is_symlink() or getattr(raw_target, 'is_junction', lambda: False)():
        raise ValueError('Không xuất qua liên kết thư mục.')
    target = raw_target.resolve()
    if target in (GOC.resolve(), GOC.parent.resolve(), KHO_MAY.resolve(), Path(target.anchor)) or target.is_symlink():
        raise ValueError('Thư mục xuất không hợp lệ.')
    if target.exists() and any(target.iterdir()) and not (target / '.nojekyll').is_file():
        raise ValueError('Thư mục có dữ liệu chưa được nhận diện là bản xuất demo; hãy chọn thư mục trống.')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='demo-staging-', dir=target.parent) as staging:
        _build([staging])
        # The only directory removed is the verified output above; replacement never merges stale files.
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(staging, target)
    print(f'Website giả lập đã sẵn sàng: {target}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
