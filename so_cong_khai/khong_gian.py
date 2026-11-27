"""Ranh giới dữ liệu của bản cài cá nhân trên máy, không phải dịch vụ SaaS."""
import json
import re
from . import tai_khoan_chart, trang

AUTH = '/api/tai-khoan-chart'
SCOPED = {'/api/hinh-ve', '/api/hinh-ve/lich-su', '/api/mau-chi-bao', '/api/canh-bao-ve'}


def nguoi(cookie, root):
    # Đọc cả khi chưa có cookie: kho hỏng phải đóng quyền, không coi là máy mới.
    tai_khoan_chart._doc(root)
    return tai_khoan_chart.hien_tai(cookie, root)


def cong_khai(path, method):
    if path in (AUTH, '/api/khong-gian'):
        return True
    return method == 'GET' and (path in ('/bieu-do', '/api/phien-ban', '/api/ai-platform/status', '/tinh/lightweight-charts.js', '/tinh/chi-bao-worker.js') or re.fullmatch(r'/tinh/phong/be-vietnam-pro-(400|500|600|700)-(vietnamese|latin-ext|latin)\.woff2', path) is not None)


def trang_vao(first=False, reader=False):
    title = 'Tạo không gian riêng trên máy này' if first else 'Mở không gian giao dịch của bạn'
    note = ('Tài khoản đầu tiên quản lý dữ liệu MT5 của bản cài này. Mỗi khách hàng cài ứng dụng trên máy và kết nối MT5 của chính mình.'
            if first else 'Đăng nhập tài khoản chủ để xem tài khoản MT5, nhật ký và cấu hình trên máy này.')
    if reader:
        note = 'Tài khoản này chỉ có kho biểu đồ riêng. Dữ liệu MT5 trên máy thuộc tài khoản chủ. Để dùng MT5 của bạn, hãy cài ứng dụng trên máy riêng.'
    return f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Không gian riêng · Harry Gold Research</title>{trang.KHOI_TAO_NEN}
<style>{trang.CSS}main.entry{{max-width:560px;margin:8vh auto;padding:26px}}.entry form{{display:grid;gap:14px}}.entry label{{display:grid;gap:7px}}.entry input,.entry button{{font:inherit;min-height:44px;border:1px solid var(--line);border-radius:8px;padding:10px;background:var(--card);color:var(--ink)}}.entry button{{cursor:pointer;background:var(--series);color:var(--btn-ink);font-weight:700}}.entry p{{line-height:1.65;color:var(--ink2)}}.entry a{{color:var(--series)}}.entry h1{{font-size:28px}}.entry #result{{color:var(--warn)}}</style></head><body><main class="entry"><p>HARRY GOLD RESEARCH · KHÔNG GIAN CÁ NHÂN</p><h1>{title}</h1><p>{note}</p>
<form id="entry"><label>Tên đăng nhập<input name="ten" autocomplete="username" required minlength="3" maxlength="40" pattern="[A-Za-z0-9_.-]{{3,40}}"></label><label>Mật khẩu<input name="mat_khau" type="password" autocomplete="{'new-password' if first else 'current-password'}" required minlength="12" maxlength="128"></label><button>{'Tạo tài khoản chủ' if first else 'Đăng nhập'}</button><p id="result" role="status"></p></form>
<p>Website công khai chỉ dùng dữ liệu minh họa. Ứng dụng trên máy đọc dữ liệu MT5 và không đặt lệnh.</p>{'<a href="/bieu-do">Mở kho biểu đồ của tôi →</a>' if reader else ''}
<script>document.getElementById('entry').addEventListener('submit',async e=>{{e.preventDefault();const f=e.target,b=f.querySelector('button'),o=document.getElementById('result');b.disabled=true;o.textContent='Đang kiểm tra…';try{{const r=await fetch('/api/tai-khoan-chart',{{method:'POST',headers:{{'Content-Type':'application/json','X-So-Cong-Khai':'1'}},body:JSON.stringify({{...Object.fromEntries(new FormData(f)),viec:{json.dumps('dang_ky' if first else 'dang_nhap')}}})}}),j=await r.json();if(!r.ok||!j.ok)throw Error(j.ly_do||'Không đăng nhập được.');location.replace('/')}}catch(x){{o.textContent=x.message}}finally{{b.disabled=false}}}})</script></main></body></html>'''


def phien_script(user):
    uid = json.dumps(user['id'])
    return f'''<script>window.HGR_USER={uid};window.hgrKey=k=>'hgr:'+window.HGR_USER+':'+k;
(()=>{{const original=window.fetch.bind(window);window.fetch=(input,options)=>{{const u=new URL(input instanceof Request?input.url:input,location.href);if(u.origin===location.origin&&u.pathname.startsWith('/api/')){{const h=new Headers(options?.headers||(input instanceof Request?input.headers:undefined));if(!h.has('X-Chart-Owner'))h.set('X-Chart-Owner',window.HGR_USER);options={{...options,headers:h}}}}return original(input,options)}};
let busy=false;async function check(){{if(busy)return;busy=true;try{{const r=await fetch('/api/khong-gian',{{cache:'no-store'}}),j=await r.json();if(!r.ok||j.nguoi?.id!==window.HGR_USER||j.nguoi?.chu!=={json.dumps(bool(user.get('chu')))}){{document.body?.replaceChildren();location.replace('/')}}else if(document.body&&!document.hidden)document.body.style.visibility=''}}catch(e){{document.body?.replaceChildren();location.replace('/')}}finally{{busy=false}}}}addEventListener('pageshow',e=>{{if(e.persisted){{if(document.body)document.body.style.visibility='hidden';check()}}}});document.addEventListener('visibilitychange',()=>{{if(document.hidden){{if(document.body)document.body.style.visibility='hidden'}}else check()}});setInterval(check,10000)}})();</script>'''
