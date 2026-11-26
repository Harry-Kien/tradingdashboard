# -*- coding: utf-8 -*-
"""Sao lưu toàn bộ hệ thống: mỗi ngày một tệp nén chứa mã, cấu hình, nhật ký và kết quả đo, cất ở nơi chủ dự án chọn.

Vì sao cần: nhật ký điểm vào, sổ của bot, cấu hình, kết quả đo và chính mã của webapp chỉ nằm trong một thư mục. Hỏng ổ, xóa nhầm hay một lần sửa
hỏng là mất. Vòng nền (VongSaoLuu) tạo một bản nén khi bản mới nhất đã cũ hơn CACH_GIO giờ, đọc lại để chắc tệp nén không hỏng, giữ GIU bản mới
nhất. Không chép tệp có tên giống khóa hay mật khẩu (.env, token, secret, .key, credential), không chép bộ nhớ tạm và ảnh chụp kiểm giao diện.

Nơi cất mặc định là thư mục Tài liệu của người dùng. Thư mục đó thường cùng ổ cứng với dự án (ổ C và ổ D có thể là hai phần của một ổ), nên trang
Sao lưu gợi ý chọn USB hoặc thư mục Google Drive. Chọn Google Drive nghĩa là tệp nén được tải lên tài khoản Google của chính người dùng; webapp
chỉ ghi vào nơi đã chọn, không tự chọn thay.
"""
from __future__ import annotations

import json
import shutil
import string
import os
import subprocess
import threading
import time
import zipfile
from datetime import datetime
from html import escape
from pathlib import Path

from . import trang
from .__main__ import HERE

GIU = 14                                        # số bản giữ lại
CACH_GIO = 24                                   # tạo bản mới khi bản mới nhất cũ hơn chừng này giờ
TIEN_TO = 'so-cong-khai-'
BO_THU_MUC = {'__pycache__', '.pytest_cache', '.git', 'kiem-giao-dien', 'dist', 'node_modules', '.venv', 'venv'}
BO_DUOI = {'.pyc', '.pkl', '.parquet', '.feather', '.zip', '.tmp', '.log', '.mp4'}
ANH = {'.png', '.jpg', '.jpeg', '.webp'}         # ảnh chụp trong out/ thì bỏ; logo, ảnh tĩnh của trang thì giữ
BO_TEN = ('.env', 'token', 'secret', 'credential', 'mat-khau', 'mat_khau', 'password')
BO_DUOI_KHOA = {'.key', '.pem', '.pfx', '.p12'}
TOI_DA = 50 * 1024 * 1024                        # bỏ tệp lớn hơn 50 MB
_khoa = threading.Lock()
TT: dict = {'dang_chay': False}


def tep_cai(goc: Path = HERE) -> Path:
    return goc / 'du-lieu' / 'sao-luu.json'


def noi_mac_dinh() -> Path:
    return Path.home() / 'Documents' / 'HarryGoldResearch-sao-luu'


def doc_cai(goc: Path = HERE) -> dict:
    try:
        d = json.loads(tep_cai(goc).read_text(encoding='utf-8'))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _ghi_cai(d: dict, goc: Path = HERE) -> None:
    p = tep_cai(goc)
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_suffix('.tmp')
    tam.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
    tam.replace(p)


def noi(goc: Path = HERE) -> Path:
    n = doc_cai(goc).get('noi')
    return Path(n) if n else noi_mac_dinh()


def _trong(a: Path, b: Path) -> bool:
    try:
        a.resolve().relative_to(b.resolve())
        return True
    except ValueError:
        return False


def dat_noi(duong: str, goc: Path = HERE) -> tuple[bool, str]:
    """Đổi nơi cất. Nơi đó phải là đường dẫn đầy đủ, nằm ngoài thư mục dự án và ghi được."""
    duong = (duong or '').strip().strip('"')
    if not duong:
        return False, 'Chưa nhập thư mục.'
    p = Path(duong)
    if not p.is_absolute():
        return False, 'Cần đường dẫn đầy đủ, ví dụ E:\\SaoLuu.'
    if _trong(p, goc):
        return False, 'Nơi cất phải nằm ngoài thư mục dự án, nếu không bản sao sẽ mất cùng dự án.'
    if not Path(p.anchor).exists():
        return False, f'Không thấy ổ {p.anchor}. Nếu là USB, hãy cắm vào rồi thử lại.'
    try:
        p.mkdir(parents=True, exist_ok=True)
        thu = p / '.thu-ghi'
        thu.write_text('ok', encoding='utf-8')
        thu.unlink()
    except OSError as e:
        return False, f'Không ghi được vào thư mục này: {e.strerror or e}.'
    d = doc_cai(goc)
    d['noi'] = str(p)
    _ghi_cai(d, goc)
    return True, f'Từ giờ bản sao được cất ở {p}.'


def nen_chep(p: Path, goc: Path) -> bool:
    """Tệp này có được đưa vào bản sao không."""
    phan = p.relative_to(goc).parts
    if any(x in BO_THU_MUC for x in phan[:-1]):
        return False
    ten = p.name.lower()
    if p.suffix.lower() in BO_DUOI or p.suffix.lower() in BO_DUOI_KHOA:
        return False
    if phan[0] == 'out' and p.suffix.lower() in ANH:
        return False
    if any(t in ten for t in BO_TEN):
        return False
    try:
        return p.stat().st_size <= TOI_DA
    except OSError:
        return False


def danh_sach_tep(goc: Path = HERE) -> list[Path]:
    ds = []
    for p in sorted(goc.rglob('*')):
        if p.is_file() and nen_chep(p, goc):
            ds.append(p)
    return ds


def cac_ban(dich: Path) -> list[Path]:
    try:
        return sorted(dich.glob(f'{TIEN_TO}*.zip'), key=lambda x: x.name, reverse=True)
    except OSError:
        return []


def tao(goc: Path = HERE, dich: Path | None = None, now: datetime | None = None, giu: int = GIU) -> dict:
    """Tạo một bản nén, đọc lại để kiểm, rồi bỏ các bản cũ quá GIU. Trả về trạng thái (ok, tep, so_tep, kich_thuoc hoặc loi)."""
    now = now or datetime.now()
    dich = dich or noi(goc)
    with _khoa:
        TT['dang_chay'] = True
        try:
            dich.mkdir(parents=True, exist_ok=True)
            ten = f'{TIEN_TO}{now:%Y%m%d-%H%M%S}.zip'
            tam = dich / (ten + '.dang-ghi')
            ds = danh_sach_tep(goc)
            with zipfile.ZipFile(tam, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
                for p in ds:
                    try:
                        z.write(p, p.relative_to(goc).as_posix())
                    except OSError:                              # tệp đang bị chương trình khác giữ: bỏ qua, lần sau chép
                        continue
                z.writestr('DOC_TOI.txt', 'Bản sao lưu của webapp so-cong-khai, tạo lúc ' + now.strftime('%d/%m/%Y %H:%M') + '.\r\n'
                           'Khôi phục: giải nén vào một thư mục mới, kiểm tra, rồi chép các tệp cần lấy lại vào thư mục dự án.\r\n'
                           'Bản sao không chứa tệp có tên giống khóa hay mật khẩu, bộ nhớ tạm và ảnh chụp.\r\n')
            with zipfile.ZipFile(tam) as z:
                hong = z.testzip()
                so = len(z.namelist()) - 1
            if hong:
                tam.unlink(missing_ok=True)
                raise OSError(f'tệp nén hỏng ở {hong}')
            dung = dich / ten
            tam.replace(dung)
            for cu in cac_ban(dich)[giu:]:
                cu.unlink(missing_ok=True)
            kq = {'ok': True, 'luc': now.isoformat(timespec='seconds'), 'tep': str(dung), 'so_tep': so, 'kich_thuoc': dung.stat().st_size}
        except OSError as e:
            kq = {'ok': False, 'luc': now.isoformat(timespec='seconds'), 'loi': f'{e.strerror or e}' + (f' ({e.filename})' if getattr(e, 'filename', None) else '')}
        finally:
            TT['dang_chay'] = False
        d = doc_cai(goc)
        d['lan_cuoi'] = kq
        _ghi_cai(d, goc)
        return kq


def tuoi_gio(dich: Path, now: float | None = None) -> float | None:
    """Bản mới nhất đã bao nhiêu giờ; None nếu chưa có bản nào."""
    ds = cac_ban(dich)
    if not ds:
        return None
    try:
        return ((now or time.time()) - ds[0].stat().st_mtime) / 3600
    except OSError:
        return None


_o_cung: dict = {}

def _powershell() -> str:
    """Đường dẫn đầy đủ tới powershell.exe của Windows (không gọi tên trơn: Windows tìm cả thư mục hiện hành trước, Ruff S607)."""
    p = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'
    return str(p) if p.is_file() else 'powershell'


def o_vat_ly(chu: str) -> int | None:
    """Số thứ tự ổ cứng vật lý của một chữ ổ (Windows); None nếu không biết (ổ mạng, Google Drive, máy khác Windows)."""
    chu = (chu or '').rstrip(':\\/').upper()[:1]
    if not ('A' <= chu <= 'Z'):                                              # chỉ chữ ổ A–Z mới đưa vào lệnh PowerShell
        return None
    if chu not in _o_cung:
        try:
            r = subprocess.run([_powershell(), '-NoProfile', '-Command', f'(Get-Partition -DriveLetter {chu} -ErrorAction Stop).DiskNumber'],   # noqa: S603 - lệnh và tham số cố định, PID ép int, chữ ổ đã kiểm A–Z
                               capture_output=True, text=True, timeout=15, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            _o_cung[chu] = int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip().isdigit() else None
        except (OSError, ValueError, subprocess.SubprocessError):
            _o_cung[chu] = None
    return _o_cung[chu]


def cung_o_cung(a: Path, b: Path) -> bool | None:
    """Hai đường dẫn có nằm trên cùng một ổ cứng vật lý không; None nếu không biết."""
    da, db = a.drive[:1].upper(), b.drive[:1].upper()
    if not da or not db:
        return None
    if da == db:
        return True
    x, y = o_vat_ly(da), o_vat_ly(db)
    if x is None or y is None:
        return None
    return x == y


def goi_y(goc: Path = HERE) -> list[dict]:
    """Các nơi cất có thể chọn: thư mục mặc định, thư mục Google Drive đang gắn, và các ổ khác (USB, ổ thứ hai)."""
    ds = [{'duong': str(noi_mac_dinh()), 'nhan': 'Thư mục Tài liệu (mặc định)', 'loai': 'may'}]
    for c in string.ascii_uppercase[2:]:
        o = Path(f'{c}:\\')
        try:
            if not o.exists():
                continue
            con = shutil.disk_usage(o).free
        except OSError:
            continue
        if (o / 'My Drive').is_dir():
            ds.append({'duong': str(o / 'My Drive' / 'HarryGoldResearch-sao-luu'), 'nhan': 'Google Drive, tải lên tài khoản Google của bạn',
                       'loai': 'google', 'con_trong': con, 'day': con < 200 * 1024 * 1024})
        elif o.drive.upper() != goc.drive.upper():
            cung = cung_o_cung(o, goc)
            ds.append({'duong': str(o / 'HarryGoldResearch-sao-luu'), 'nhan': 'Ổ khác, cùng ổ cứng với dự án' if cung else 'Ổ cứng khác' if cung is False else 'Ổ khác',
                       'loai': 'cung' if cung else 'khac' if cung is False else 'khong-ro', 'con_trong': con, 'day': con < 200 * 1024 * 1024})
    return ds


def xem(goc: Path = HERE, co_goi_y: bool = True) -> dict:
    dich = noi(goc)
    ban = []
    for p in cac_ban(dich):
        try:
            st = p.stat()
        except OSError:
            continue
        ban.append({'ten': p.name, 'kich_thuoc': st.st_size, 'luc': datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds')})
    return {'noi': str(dich), 'mac_dinh': not doc_cai(goc).get('noi'), 'google': 'my drive' in str(dich).lower(),
            'cung_o_cung': cung_o_cung(dich, goc), 'ban': ban, 'tuoi_gio': tuoi_gio(dich), 'lan_cuoi': doc_cai(goc).get('lan_cuoi'),
            'dang_chay': TT['dang_chay'], 'giu': GIU, 'cach_gio': CACH_GIO, 'goi_y': goi_y(goc) if co_goi_y else []}


def chay_nen(goc: Path = HERE) -> bool:
    """Tạo một bản ở luồng riêng (nút Sao lưu ngay). False nếu đang có lần sao lưu khác."""
    if TT['dang_chay']:
        return False
    threading.Thread(target=tao, args=(goc,), daemon=True, name='sao-luu-ngay').start()
    return True


class VongSaoLuu(threading.Thread):
    """Vòng nền: hai phút sau khi webapp mở, rồi mỗi 30 phút, tạo bản mới nếu bản mới nhất đã cũ hơn CACH_GIO giờ."""

    def __init__(self, goc: Path = HERE, dau: float = 120, cach: float = 1800):
        super().__init__(daemon=True, name='sao-luu')
        self.goc, self.dau, self.cach = goc, dau, cach

    def run(self) -> None:
        time.sleep(self.dau)
        while True:
            try:
                t = tuoi_gio(noi(self.goc))
                if t is None or t >= CACH_GIO:
                    tao(self.goc)
            except Exception:                                     # noqa: BLE001  vòng nền không được chết
                pass
            time.sleep(self.cach)


def muc_suc_khoe(goc: Path = HERE) -> dict:
    """Một dòng cho trang Tình trạng hệ thống."""
    ten, lam = 'Sao lưu toàn bộ', 'Mở trang Sao lưu (/sao-luu) để sao lưu ngay hoặc đổi nơi cất.'
    x = xem(goc, co_goi_y=False)
    lc = x.get('lan_cuoi') or {}
    if lc and not lc.get('ok'):
        return {'ten': ten, 'muc': 'chu_y', 'chi_tiet': f'Lần sao lưu gần nhất lỗi: {lc.get("loi")}.', 'lam': lam}
    t = x['tuoi_gio']
    if t is None:
        return {'ten': ten, 'muc': 'chu_y', 'chi_tiet': 'Chưa có bản sao nào. Webapp tự tạo bản đầu khoảng hai phút sau khi mở.', 'lam': lam}
    gan = f'Bản mới nhất cách đây {t:.0f} giờ, đang giữ {len(x["ban"])} bản.'
    if t > CACH_GIO + 12:
        return {'ten': ten, 'muc': 'chu_y', 'chi_tiet': gan + ' Bản sao đã cũ.', 'lam': lam}
    if x['cung_o_cung']:
        return {'ten': ten, 'muc': 'chu_y', 'chi_tiet': gan + ' Nơi cất nằm cùng ổ cứng với dự án: hỏng ổ là mất cả hai.',  # câu tách riêng để dịch được
                'lam': 'Chọn USB hoặc thư mục Google Drive ở trang Sao lưu.'}
    return {'ten': ten, 'muc': 'tot', 'chi_tiet': gan}


CSS = """
.sl{display:grid;gap:14px;margin-top:14px;grid-template-columns:minmax(0,1fr)}.sl>*{min-width:0}.sl table{width:100%;table-layout:fixed}.sl td,.sl th{white-space:normal;padding:8px}.sl th:first-child{width:38%}.sl th:nth-child(2){width:18%}.sl .card{padding:14px;display:grid;gap:10px}
.sl .tt{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.sl .tt b{font-size:16px}.sl .tt .x{margin-left:auto}
.sl .dot{width:10px;height:10px;border-radius:50%;background:var(--gain);flex:none}.sl .dot.chu_y{background:var(--warn)}
.sl code{font-size:12.5px;word-break:break-all}.sl table{font-size:13px}.sl td,.sl th{font-variant-numeric:tabular-nums}
.sl .gy{display:grid;gap:6px}.sl .gy button{text-align:left;justify-content:flex-start;min-height:38px;white-space:normal}
.sl .gy small{color:var(--mute)}.sl .tu{display:flex;gap:8px;flex-wrap:wrap}.sl .tu input{flex:1 1 240px;min-width:0;min-height:36px;padding:0 10px}
.sl .bao{min-height:1.2em;font-size:13px}
"""

JS = r"""
(()=>{const $=s=>document.querySelector(s),e=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const mb=b=>b>=1073741824?(b/1073741824).toFixed(1).replace('.',',')+' GB':b>=1048576?(b/1048576).toFixed(1).replace('.',',')+' MB':Math.max(1,Math.round(b/1024))+' KB';
const gio=s=>{const d=new Date(s);return d.toLocaleString('vi-VN',{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit',year:'numeric'})};
const gui=(o)=>fetch('/api/sao-luu',{method:'POST',headers:{'Content-Type':'application/json','X-So-Cong-Khai':'1'},body:JSON.stringify(o)}).then(r=>r.json());
let doiCho=0;
const ve=j=>{const t=j.tuoi_gio,lc=j.lan_cuoi||{},loi=lc.ok===false,cu=t==null||t>j.cach_gio+12,cung=j.cung_o_cung===true;
 const chu=loi||cu||cung;
 let tt=t==null?'Chưa có bản sao nào.':`Bản mới nhất cách đây ${t<1?'chưa tới 1 giờ':Math.round(t)+' giờ'}.`;
 if(loi)tt+=` Lần gần nhất lỗi: ${e(lc.loi)}.`;
 let h=`<section class="card"><div class="tt"><span class="dot ${chu?'chu_y':''}"></span><b>${e(tt)}</b>
 <button type="button" class="x" id="ngay" ${j.dang_chay?'disabled':''}>${j.dang_chay?'Đang sao lưu…':'Sao lưu ngay'}</button></div>
 <div class="small">Nơi cất: <code>${e(j.noi)}</code>${j.google?' · <b>Google Drive</b>: tệp được tải lên tài khoản Google của bạn':''}</div>
 ${cung?'<p class="note" style="margin:0"><b>Nơi cất đang cùng ổ cứng với dự án.</b> Xóa nhầm hay sửa hỏng thì lấy lại được, nhưng hỏng ổ cứng là mất cả hai. Chọn USB hoặc Google Drive bên dưới.</p>':''}
 <div class="small">Tự sao lưu mỗi ${j.cach_gio} giờ khi webapp đang mở, giữ ${j.giu} bản mới nhất, đọc lại mỗi bản để chắc tệp nén không hỏng.</div></section>`;
 h+='<section class="card"><b>Các bản đang giữ</b>'+(j.ban.length?'<table><thead><tr><th>Lúc tạo</th><th>Cỡ</th><th>Tệp</th></tr></thead><tbody>'+
  j.ban.map(b=>`<tr><td>${gio(b.luc)}</td><td>${mb(b.kich_thuoc)}</td><td><code>${e(b.ten)}</code></td></tr>`).join('')+'</tbody></table>':'<p class="small">Chưa có.</p>')+
  (lc.ok?`<div class="small">Lần gần nhất: ${lc.so_tep} tệp, ${mb(lc.kich_thuoc)}.</div>`:'')+'</section>';
 h+='<section class="card"><b>Đổi nơi cất</b><div class="gy">'+j.goi_y.map(g=>`<button type="button" class="ghost" data-d="${e(g.duong)}" ${g.duong===j.noi||g.day?'disabled':''}>${e(g.nhan)}${g.day?' · đã đầy':g.con_trong!=null?' · còn trống '+mb(g.con_trong):''}<br><small>${e(g.duong)}</small></button>`).join('')+
  `</div><div class="tu"><input id="tu-noi" placeholder="Hoặc gõ thư mục khác, ví dụ E:\\SaoLuu" aria-label="Thư mục cất bản sao"><button type="button" id="tu-dat">Dùng thư mục này</button></div>
  <div class="small">Chọn Google Drive nghĩa là bản sao (mã, cấu hình, nhật ký, kết quả đo; không có mật khẩu hay khóa) được tải lên tài khoản Google của bạn.</div>
  <div class="bao" id="bao" role="status"></div></section>`;
 h+=`<section class="card"><b>Khôi phục khi cần</b><ol class="small" style="margin:0;padding-left:18px"><li>Mở thư mục nơi cất, chọn bản trước lúc hỏng.</li>
 <li>Giải nén vào một thư mục mới (chuột phải, Extract All), đừng giải nén đè lên dự án.</li><li>Kiểm tra, rồi chép các tệp cần lấy lại (ví dụ <code>du-lieu\\nhat-ky-diem-vao.json</code>) vào thư mục dự án và mở lại webapp.</li></ol></section>`;
 $('#sl').innerHTML=h;
 $('#ngay').onclick=()=>gui({viec:'chay'}).then(r=>{$('#bao')&&($('#bao').textContent=r.ly_do||'');doiCho=1;setTimeout(nap,1500)});
 document.querySelectorAll('.gy button').forEach(b=>b.onclick=()=>dat(b.dataset.d));
 $('#tu-dat').onclick=()=>dat($('#tu-noi').value);
 if(j.dang_chay||doiCho){doiCho=j.dang_chay?1:0;if(j.dang_chay)setTimeout(nap,1500)}};
const dat=d=>{if(String(d).toLowerCase().includes('my drive')&&!confirm('Bản sao sẽ được tải lên Google Drive của bạn. Tiếp tục?'))return;
 gui({viec:'dat_noi',noi:d}).then(r=>{nap().then(()=>{$('#bao').textContent=r.ly_do||''})})};
const nap=()=>fetch('/api/sao-luu',{cache:'no-store'}).then(r=>r.json()).then(ve).catch(()=>{$('#sl').innerHTML='<p class="small">Không đọc được trạng thái sao lưu.</p>'});
nap();})();
"""


def trang_sao_luu(ten: str) -> str:
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Sao lưu · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'sao-luu', '<button id="theme" type="button">Nền tối</button>') + '<main>',
        '<div class="top"><div><h1>Sao lưu</h1></div><div class="stamp">mã, cấu hình, nhật ký và kết quả đo<br>mỗi ngày một bản</div></div>',
        '<p class="note">Nhật ký điểm vào, sổ của bot, cấu hình và kết quả đo chỉ có trên máy này. Webapp tự nén toàn bộ thành một tệp mỗi ngày và cất ở nơi '
        'bạn chọn. Bản sao không chứa tệp có tên giống khóa hay mật khẩu, bộ nhớ tạm và ảnh chụp.</p>',
        '<div class="sl" id="sl"><p class="small">Đang đọc…</p></div>',
        f'<footer>{escape(trang.MIEN_TRU)}</footer></main><script>{trang.JS}</script><script>{JS}</script></body></html>'])
