"""Đóng gói bản chia sẻ của webapp thành một tệp zip để gửi cho người khác: python -X utf8 cong-cu/dong_goi.py

Chỉ lấy đúng các tệp người nhận cần (mã webapp, thư viện biểu đồ và phông chữ đi kèm, cấu hình MẪU, tệp cài và chạy, hướng dẫn).
KHÔNG lấy: cau-hinh.json của bạn, du-lieu/, out/, pine/, cong-cu/, các báo cáo .md riêng, bài kiểm.
Trước khi ghi zip, chương trình quét mọi tệp chữ trong gói tìm thông tin riêng của máy này (mọi đường dẫn và tên tài khoản trong
cau-hinh.json của bạn, tên thư mục người dùng Windows); thấy là dừng và không tạo zip. Sau đó giải nén thử vào thư mục tạm,
biên dịch mọi tệp .py và nạp thử webapp với cấu hình mẫu.

Kết quả: dist/<tên>-<ngày>.zip trong thư mục so-cong-khai."""
from __future__ import annotations

import argparse
import json
import os
import py_compile
import re
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
LAY = ['cau-hinh.mau.json', 'requirements.txt', 'BAT_DAU.bat', 'CAI_DAT.bat', 'CHAY_WEBAPP.bat', 'HUONG_DAN.md', 'REALTIME_BIEU_DO.md']
THU_MUC = ['so_cong_khai', 'tinh']
BO_DUOI = {'.pyc', '.pyo'}
BO_TEP = {'logo-goc.webp', 'logo-chia-se.png'}                                # ảnh gốc và ảnh xem trước của logo: app dùng logo nhúng trong logo.py
CHU = {'.py', '.json', '.md', '.bat', '.txt', '.js', '.css', '.html'}


def danh_sach() -> list[tuple[Path, str]]:
    """(tệp nguồn, đường dẫn trong zip)."""
    out = []
    for ten in LAY:
        p = GOC / ten
        if not p.is_file():
            raise SystemExit(f'Thiếu tệp {ten}')
        out.append((p, ten))
    for d in THU_MUC:
        for p in sorted((GOC / d).rglob('*')):
            tam = any(x == '__pycache__' or x.startswith('_tam') for x in p.parts) or p.name.startswith('thieu_')   # tệp tạm khi làm song ngữ
            if p.is_file() and not tam and p.suffix not in BO_DUOI and p.name not in BO_TEP:
                out.append((p, p.relative_to(GOC).as_posix()))
    return out


def dau_rieng() -> list[str]:
    """Các chuỗi chỉ có trên máy này: mọi đường dẫn và tên tài khoản trong cau-hinh.json của bạn, và thư mục người dùng Windows."""
    dau = set()
    cfg_p = GOC / 'cau-hinh.json'
    if cfg_p.exists():
        def di(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == 'tai_khoan' and isinstance(v, str) and v:      # tên tài khoản mạng xã hội; "kenh" là tên thương hiệu, hiện công khai
                        dau.add(v)
                    di(v)
            elif isinstance(o, list):
                for v in o:
                    di(v)
            elif isinstance(o, str) and re.search(r'[A-Za-z]:\\|%[A-Z]+%', o):
                p = os.path.expandvars(o)
                for phan in (p, str(Path(p).parent)):
                    if len(phan) > 6 and phan not in ('C:\\', 'D:\\'):
                        dau.add(phan)
        di(json.loads(cfg_p.read_text(encoding='utf-8')))
    nha = os.path.expanduser('~')
    if nha and nha != '~':
        dau.add(nha)
    return sorted(dau, key=len, reverse=True)


def quet(tep: list[tuple[Path, str]], dau: list[str]) -> list[str]:
    thay = []
    for p, ten in tep:
        if p.suffix.lower() not in CHU:
            continue
        noi = p.read_text(encoding='utf-8', errors='replace').casefold()
        for d in dau:
            for bien in {d, d.replace('\\', '\\\\'), d.replace('\\', '/')}:
                if bien.casefold() in noi:
                    thay.append(f'{ten}: chứa "{d}"')
                    break
    return thay


def kien_thuc_chia_se(nguon: str) -> str:
    """kien_thuc.py cho gói: thay danh sách MUC bằng bản chỉ còn phần giải thích chung (kien_thuc.muc_chia_se), để mã nguồn trong gói
    không mang các mô tả luật riêng, ngưỡng và số đo nghiên cứu của bạn. Tệp gốc trên máy bạn giữ nguyên."""
    import pprint                                                            # noqa: PLC0415
    if str(GOC) not in sys.path:
        sys.path.insert(0, str(GOC))
    from so_cong_khai import kien_thuc                                       # noqa: PLC0415
    a, b = nguon.index('\nMUC = [') + 1, nguon.index('\nCSS = """')
    moi = '# Bản chia sẻ: chỉ phần giải thích chung.\nMUC = ' + pprint.pformat(kien_thuc.muc_chia_se(), width=150, sort_dicts=False) + '\n\n'
    return nguon[:a] + moi + nguon[b + 1:]


def loc_tu_dien(nguon: str, tep: list[tuple[Path, str]], kien_thuc_moi: str) -> str:
    """dich/en.json cho gói: chỉ giữ mục mà mã trong gói thật sự dùng. Từ điển được dịch từ bản đầy đủ nên có cả câu mô tả luật riêng và số đo
    nghiên cứu (khóa là nguyên văn tiếng Việt); một mục được giữ khi mọi đoạn chữ của khóa (cắt ở các ô {n}) đều có trong chuỗi chữ của các tệp .py
    trong gói (đọc bằng ast, nên chuỗi viết nối nhiều dòng vẫn được ghép lại)."""
    import ast                                                               # noqa: PLC0415
    import html as h                                                         # noqa: PLC0415
    kho = []
    for p, ten in tep:
        if p.suffix != '.py':
            continue
        src = kien_thuc_moi if ten == 'so_cong_khai/kien_thuc.py' else p.read_text(encoding='utf-8')
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                kho.append(n.value)
    van = re.sub(r'\s+', ' ', '\n'.join(kho))
    van = van + '\n' + h.unescape(van)
    d = json.loads(nguon)
    them = GOC / 'cong-cu' / 'dich_chia_se_them.json'                       # khóa đã thấy bản chia sẻ hiển thị (ghép nhiều mảnh nên bộ lọc trên bỏ sót)
    them = set(json.loads(them.read_text(encoding='utf-8'))) if them.exists() else set()
    giu = {}
    for k, v in d.items():
        if k.startswith('__') or k in them:
            giu[k] = v
            continue
        doan = [x.strip() for x in re.split(r'\{\d+\}', k) if len(x.strip()) >= 3]
        if all(x in van for x in doan):
            giu[k] = v
    return json.dumps(giu, ensure_ascii=False, indent=0)


def crlf(b: bytes) -> bytes:
    return b.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')


def kiem_goi(zp: Path) -> None:
    """Giải nén thử, biên dịch mọi tệp .py, rồi nạp webapp với cấu hình mẫu ở một tiến trình riêng (không mở cổng, không nối MT5)."""
    with tempfile.TemporaryDirectory() as t:
        with zipfile.ZipFile(zp) as z:
            z.extractall(t)
        goc = Path(t) / zp.stem
        for p in goc.rglob('*.py'):
            py_compile.compile(str(p), doraise=True)
        thu = ('import json,sys; sys.path.insert(0, "."); from so_cong_khai import web, gia; '
               'c = json.load(open("cau-hinh.mau.json", encoding="utf-8")); '
               'assert gia.ban_chia_se(c["gia"]), "cấu hình mẫu không ở chế độ chia sẻ"; '
               'web.tao_may_chu("cau-hinh.mau.json", port=0).server_close(); print("nap-duoc")')
        r = subprocess.run([sys.executable, '-X', 'utf8', '-I', '-c', thu.replace('sys.path.insert(0, ".")', f'sys.path.insert(0, {str(goc)!r})')],
                           cwd=goc, capture_output=True, text=True, encoding='utf-8', timeout=120)
        if r.returncode != 0 or 'nap-duoc' not in r.stdout:
            raise SystemExit('Gói không nạp được webapp:\n' + r.stdout + r.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description='Tạo gói webapp chia sẻ từ mã nguồn và cấu hình mẫu.')
    parser.add_argument('--hau-to', default='', help='Hậu tố riêng để giữ các bản xuất cùng ngày.')
    args = parser.parse_args()
    if args.hau_to and not re.fullmatch(r'[A-Za-z0-9-]{1,32}', args.hau_to):
        parser.error('Hậu tố chỉ gồm chữ, số và dấu gạch ngang (tối đa 32 ký tự).')
    tep = danh_sach()
    loi = quet(tep, dau_rieng())
    if loi:
        print('DỪNG: gói sẽ lộ thông tin riêng của máy này:')
        for x in loi:
            print('  -', x)
        return 1
    ten_co_dinh = re.search(r"^TEN = '([^']*)'", (GOC / 'so_cong_khai' / 'thuong_hieu.py').read_text(encoding='utf-8'), re.M)   # tên hiển thị cố định
    ten = re.sub(r'[^A-Za-z0-9]+', '-', (ten_co_dinh.group(1) if ten_co_dinh else 'webapp').split('·')[0]).strip('-') or 'webapp'
    ten = f'{ten}-Webapp-{datetime.now():%Y%m%d}'
    if args.hau_to:
        ten += f'-{args.hau_to}'
    dist = GOC / 'dist'
    dist.mkdir(exist_ok=True)
    zp = dist / f'{ten}.zip'
    kt_moi = kien_thuc_chia_se((GOC / 'so_cong_khai' / 'kien_thuc.py').read_text(encoding='utf-8'))
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p, trong in tep:
            b = p.read_bytes()
            if trong == 'so_cong_khai/kien_thuc.py':
                b = kt_moi.encode('utf-8')
            elif trong == 'so_cong_khai/dich/en.json':                       # bỏ bản dịch của câu chỉ có ở bản đầy đủ (luật riêng, số đo nghiên cứu)
                b = loc_tu_dien(b.decode('utf-8'), tep, kt_moi).encode('utf-8')
            z.writestr(f'{ten}/{trong}', crlf(b) if p.suffix.lower() == '.bat' else b)
    kiem_goi(zp)
    print(f'Đã tạo {zp}')
    print(f'{len(tep)} tệp, {zp.stat().st_size / 1e6:.1f} MB. Đã quét thông tin riêng, biên dịch và nạp thử webapp: đạt.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
