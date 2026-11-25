"""Song ngữ Việt / Anh cho webapp.

Giao diện được viết bằng tiếng Việt. Khi người xem chọn tiếng Anh (cookie `lang=en`, đặt bằng nút VI/EN trên thanh điều hướng hoặc `?lang=en`),
máy chủ dịch câu trả lời ngay trước khi gửi: trang HTML (chữ hiển thị, thuộc tính title/placeholder/aria-label, chuỗi trong mã JS chạy trên trang)
và dữ liệu JSON của các /api. Bản dịch tra từ từ điển `so_cong_khai/dich/en.json` theo TỪNG ĐOẠN TRỌN VẸN (không thay một phần câu), số trong
đoạn được thay bằng ô {0}, {1}… nên "Giá cũ 25 phút" và "Giá cũ 3 phút" dùng chung một mục "Giá cũ {0} phút".

An toàn cho mã: chuỗi JS chỉ được dịch khi cả chuỗi là một mục trong từ điển; chuỗi đứng trong phép so sánh (===, !==, startsWith, includes, case…)
không bao giờ bị dịch để không đổi hành vi; dấu nháy trong bản dịch được thoát đúng kiểu chuỗi. Đoạn chưa có trong từ điển giữ nguyên tiếng Việt;
`cong-cu/i18n_trich.py` liệt kê các đoạn còn thiếu, `cong-cu/kiem_giao_dien.py` đo phần còn sót trên từng trang."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

THU_MUC = Path(__file__).resolve().parent / 'dich'
NGON_NGU = ('vi', 'en')
_VI = re.compile(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', re.I)
_VI_KHONG_DAU = {'Mua', 'Tin', 'Theo', 'Sau', 'Xem', 'Gon', 'Tim', 'Ban'}       # nhãn tiếng Việt không có dấu thường gặp
# số đứng riêng, lấy trọn ("0,12R" → "{0}R"); "M15", "EMA20", "US30" là tên, giữ nguyên; mã băm hex (≥ 10 ký tự, có cả số lẫn chữ) cũng thành ô {n}
_SO = re.compile(r'(?<![A-Za-z0-9_.,])(?:(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{10,}(?![0-9A-Za-z])|\d+(?:[.,]\d+)*(?!\d))')
_KHOANG = re.compile(r'\s+')
THUOC_TINH = ('title', 'placeholder', 'aria-label', 'alt', 'data-tip', 'content', 'label')
_tu: dict = {}


# --------------------------------------------------------------------------- từ điển
def tu_dien(lang: str) -> dict:
    """Từ điển của một ngôn ngữ (nhớ theo giờ sửa tệp)."""
    f = THU_MUC / f'{lang}.json'
    try:
        st = f.stat()
    except OSError:
        return {}
    key = (st.st_mtime_ns, st.st_size)
    cu = _tu.get(lang)
    if cu and cu[0] == key:
        return cu[1]
    try:
        d = {k: v for k, v in json.loads(f.read_text(encoding='utf-8')).items() if isinstance(v, str) and v.strip()}
    except (OSError, ValueError):
        d = {}
    _tu[lang] = (key, d)
    return d


_TU_KHONG_DAU = re.compile(r'(?<![A-Za-z])(mua|theo|sau|xem|khi|vao|nao|cho)(?![A-Za-z])', re.I)   # từ tiếng Việt không dấu hay gặp


_DINH_DANH = re.compile(r'[#.]?[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)+|[#.][A-Za-z0-9_-]+|[A-Z0-9_]+')   # tên trong mã: #pl-vao, tn-xem, cho_khop, MUA


def la_tieng_viet(s: str) -> bool:
    s = s.strip()
    if not s:
        return False
    if _VI.search(s):
        return True
    if s in _VI_KHONG_DAU:
        return True
    if _DINH_DANH.fullmatch(s) or not re.search(r'\s', s):                  # không dấu, không khoảng trắng: giá trị/định danh trong mã ('mua', 'ban', a|b|MUA)
        return False
    return bool(_TU_KHONG_DAU.search(s))


def khoa(s: str) -> tuple[str, list[str]]:
    """Đoạn chữ → (khóa tra từ điển, các số đã rút ra). Khoảng trắng gộp lại, số thay bằng {0}, {1}…"""
    so: list[str] = []

    def _o(m):
        so.append(m.group(0))
        return '{%d}' % (len(so) - 1)
    return _SO.sub(_o, _KHOANG.sub(' ', s.strip())), so


def dich_doan(s: str, d: dict, thu: set | None = None) -> str:
    """Dịch một đoạn trọn vẹn, giữ khoảng trắng ở hai đầu. Không có trong từ điển thì trả nguyên (và ghi vào `thu` nếu là tiếng Việt)."""
    if not la_tieng_viet(s):
        return s
    k, so = khoa(s)
    v = d.get(k)
    if v is None:
        if thu is not None:
            thu.add(k)
        return s
    try:
        v = re.sub(r'\{(\d+)\}', lambda m: so[int(m.group(1))], v)
    except IndexError:
        return s
    dau = s[:len(s) - len(s.lstrip())]
    cuoi = s[len(s.rstrip()):]
    return dau + v + cuoi


# --------------------------------------------------------------------------- HTML
_THE = re.compile(r'<!--.*?-->|<(script|style)\b[^>]*>.*?</\1\s*>|<[^>]+>', re.S | re.I)
_TT = re.compile(r'''(\s)([a-zA-Z_:][-a-zA-Z0-9_:.]*)(\s*=\s*)("[^"]*"|'[^']*')''')


def _dich_the(the: str, d: dict, thu: set | None) -> str:
    def _o(m):
        ten, gt = m.group(2).lower(), m.group(4)
        q, noi = gt[0], gt[1:-1]
        if ten == 'data-tim':                                                # JSON danh sách trang cho ô tìm nhanh
            try:
                j = json.loads(html.unescape(noi))
                return m.group(1) + m.group(2) + m.group(3) + q + html.escape(json.dumps(dich_json(j, d, thu), ensure_ascii=False), quote=True) + q
            except ValueError:
                return m.group(0)
        if ten not in THUOC_TINH or not la_tieng_viet(html.unescape(noi)):
            return m.group(0)
        moi = dich_doan(html.unescape(noi), d, thu)
        return m.group(1) + m.group(2) + m.group(3) + q + html.escape(moi, quote=True) + q
    return _TT.sub(_o, the)


def dich_html(s: str, d: dict, thu: set | None = None, trong_js: bool = False) -> str:
    """Dịch một trang hoặc một mảnh HTML: chữ giữa các thẻ, thuộc tính hiển thị, mã trong <script>. `trong_js`: mảnh nằm trong chuỗi JS
    (không unescape/escape thực thể, vì mã đó tự nối chuỗi)."""
    if trong_js:                                                             # mảnh bị cắt giữa thẻ bởi ${…}: phần đầu/cuối là thẻ dở dang
        a = s.find('>')
        if a >= 0 and '<' not in s[:a]:
            return _dich_the(' ' + s[:a + 1], d, thu)[1:] + dich_html(s[a + 1:], d, thu, True)
        b = s.rfind('<')
        if b >= 0 and '>' not in s[b:]:
            return dich_html(s[:b], d, thu, True) + _dich_the(s[b:], d, thu)
    out, i = [], 0
    for m in _THE.finditer(s):
        out.append(_dich_chu(s[i:m.start()], d, thu, trong_js))
        t = m.group(0)
        if t.startswith('<!--'):
            out.append(t)
        elif m.group(1) and m.group(1).lower() == 'script':
            a = t.index('>') + 1
            b = t.lower().rindex('</script')
            mo = t[:a]
            if 'application/json' in mo.lower():                             # dữ liệu nhúng dạng JSON
                try:
                    out.append(mo + json.dumps(dich_json(json.loads(t[a:b]), d, thu), ensure_ascii=False).replace('</', '<\\/') + t[b:])
                except ValueError:
                    out.append(t)
            else:
                out.append(mo + dich_js(t[a:b], d, thu) + t[b:])
        elif m.group(1):                                                     # <style>
            out.append(t)
        else:
            out.append(_dich_the(t, d, thu))
        i = m.end()
    out.append(_dich_chu(s[i:], d, thu, trong_js))
    return ''.join(out)


def _dich_chu(t: str, d: dict, thu: set | None, trong_js: bool) -> str:
    if not t.strip() or not la_tieng_viet(html.unescape(t) if not trong_js else t):
        return t
    if trong_js:
        return dich_doan(t, d, thu)
    moi = dich_doan(html.unescape(t), d, thu)
    return t if moi == html.unescape(t) else html.escape(moi, quote=False)


# --------------------------------------------------------------------------- JS
_TRUOC_REGEX = set('(,=:[!&|?{};+-*%<>~^')
_SO_SANH_TRUOC = re.compile(r'(===|!==|==|!=|\bcase|startsWith\(|endsWith\(|includes\(|indexOf\(|lastIndexOf\(|\bin)\s*$')
_SO_SANH_SAU = re.compile(r'^\s*(===|!==|==|!=)')


def _dich_chuoi_js(noi: str, ngoac: str, d: dict, thu: set | None) -> str:
    """Nội dung một chuỗi JS (chưa giải mã thoát). Có thẻ HTML thì dịch như mảnh HTML, không thì dịch cả chuỗi."""
    if not la_tieng_viet(noi):
        return noi
    if '<' in noi or '>' in noi:
        moi = dich_html(noi, d, thu, trong_js=True)
    else:
        moi = dich_doan(noi, d, thu)
    if moi == noi:
        return noi
    if ngoac == '`':
        return moi.replace('`', '\\`').replace('${', '\\${')
    return re.sub(r'(?<!\\)' + re.escape(ngoac), '\\' + ngoac, moi)


def dich_js(s: str, d: dict, thu: set | None = None) -> str:
    """Duyệt mã JS: chú thích, regex, chuỗi '…' "…" và chuỗi mẫu `…${…}…` (lồng nhau). Chỉ đổi nội dung chuỗi."""
    out: list[str] = []
    i, n = 0, len(s)
    truoc = ''                                                              # ký tự có nghĩa gần nhất trước vị trí hiện tại

    def doc_mau(i: int, giu: bool = False) -> int:
        """Đọc chuỗi mẫu bắt đầu ở s[i] == '`'; ghi ra out; trả vị trí sau dấu ` đóng. `giu`: chuỗi trong phép so sánh, không dịch."""
        tinh = (lambda x: x) if giu else (lambda x: _dich_chuoi_js(x, '`', d, thu))  # noqa: E731
        out.append('`')
        i += 1
        phan = i
        while i < n:
            c = s[i]
            if c == '\\':
                i += 2
                continue
            if c == '`':
                out.append(tinh(s[phan:i]))
                out.append('`')
                return i + 1
            if c == '$' and i + 1 < n and s[i + 1] == '{':
                out.append(tinh(s[phan:i]))
                out.append('${')
                i = doc_bieu_thuc(i + 2)
                phan = i
                continue
            i += 1
        out.append(s[phan:])
        return n

    def doc_bieu_thuc(i: int) -> int:
        """Đọc biểu thức trong ${…} tới dấu } khớp; trả vị trí sau dấu }."""
        nonlocal truoc
        sau = 0
        while i < n:
            c = s[i]
            if c == '}' and sau == 0:
                out.append('}')
                return i + 1
            if c == '{':
                sau += 1
            elif c == '}':
                sau -= 1
            j = buoc(i)
            if j is None:
                out.append(c)
                if not c.isspace():
                    truoc = c
                i += 1
            else:
                i = j
        return n

    def buoc(i: int):
        """Nếu s[i] mở đầu chú thích, regex hay chuỗi: ghi ra out, trả vị trí kế tiếp; không thì None."""
        nonlocal truoc
        c = s[i]
        if c == '/' and i + 1 < n and s[i + 1] == '/':
            j = s.find('\n', i)
            j = n if j < 0 else j
            out.append(s[i:j])
            return j
        if c == '/' and i + 1 < n and s[i + 1] == '*':
            j = s.find('*/', i + 2)
            j = n if j < 0 else j + 2
            out.append(s[i:j])
            return j
        if c == '/' and (truoc == '' or truoc in _TRUOC_REGEX):
            j, lop = i + 1, False
            while j < n and s[j] != '\n':
                if s[j] == '\\':
                    j += 2
                    continue
                if s[j] == '[':
                    lop = True
                elif s[j] == ']':
                    lop = False
                elif s[j] == '/' and not lop:
                    j += 1
                    while j < n and s[j].isalpha():
                        j += 1
                    out.append(s[i:j])
                    truoc = 'r'
                    return j
                j += 1
            return None
        if c in '\'"':
            j = i + 1
            while j < n and s[j] != c and s[j] != '\n':
                j += 2 if s[j] == '\\' else 1
            noi = s[i + 1:j]
            so_sanh = bool(_SO_SANH_TRUOC.search(''.join(out[-24:])[-24:])) or bool(_SO_SANH_SAU.match(s[j + 1:j + 8]))
            if noi == 'vi-VN' and d.get('__locale__'):
                noi_moi = d['__locale__']
            else:
                noi_moi = noi if so_sanh else _dich_chuoi_js(noi, c, d, thu)
            out.append(c + noi_moi + c)
            truoc = c
            return j + 1
        if c == '`':
            moc = len(out)
            j = doc_mau(i, giu=bool(_SO_SANH_TRUOC.search(''.join(out[-24:])[-24:])))
            if _SO_SANH_SAU.match(s[j:j + 7]):                              # mẫu đứng trước phép so sánh: chép nguyên văn
                del out[moc:]
                out.append(s[i:j])
            truoc = '`'
            return j
        return None

    while i < n:
        j = buoc(i)
        if j is None:
            c = s[i]
            out.append(c)
            if not c.isspace():
                truoc = c if not (c.isalnum() or c in '_$)].') else 'a'
                if c in ')]':
                    truoc = ')'
            i += 1
        else:
            i = j
    return ''.join(out)


# --------------------------------------------------------------------------- JSON
_KHOA_GIU = {'link', 'url', 'id', 'ma', 'goc', 'sym', 'ma_nguon', 'k', 'h', 'h2', 'i', 'lop', 'huong', 'nguon_id'}       # mã, đường dẫn: không dịch


def dich_json(x, d: dict, thu: set | None = None, khoa_cha: str = ''):
    """Dịch giá trị chuỗi trong dữ liệu JSON (không dịch tên khóa, đường dẫn hay mã)."""
    if isinstance(x, dict):
        return {k: (v if k in _KHOA_GIU and isinstance(v, str) else dich_json(v, d, thu, k)) for k, v in x.items()}
    if isinstance(x, list):
        return [dich_json(v, d, thu, khoa_cha) for v in x]
    if isinstance(x, str) and la_tieng_viet(x):
        if '<' in x and '>' in x:
            return dich_html(x, d, thu, trong_js=True)
        return dich_doan(x, d, thu)
    return x


# --------------------------------------------------------------------------- dùng ở máy chủ
def dich_phan_hoi(body: bytes, loai: str, lang: str, thu: set | None = None) -> bytes:
    """Dịch câu trả lời HTML/JSON sang `lang`. Tiếng Việt (gốc) hoặc ngôn ngữ chưa có từ điển: trả nguyên."""
    if lang == 'vi' or lang not in NGON_NGU:
        return body
    d = tu_dien(lang)
    if not d:
        return body
    try:
        if loai.startswith('text/html'):
            s = body.decode('utf-8')
            s = re.sub(r'<html lang="vi"', f'<html lang="{lang}"', s, count=1)
            return dich_html(s, d, thu).encode('utf-8')
        if loai.startswith('application/json'):
            return json.dumps(dich_json(json.loads(body.decode('utf-8')), d, thu), ensure_ascii=False).encode('utf-8')
    except (ValueError, UnicodeDecodeError):
        return body
    return body


THIEU: set = set()                                                         # đoạn tiếng Việt chưa có bản dịch, gặp lúc chạy
_luu_thieu = {'n': 0, 'luc': 0.0}


def ghi_thieu(lang: str = 'en', moi_giay: float = 60.0) -> None:
    """Ghi các đoạn chưa dịch gặp lúc chạy vào dich/thieu_<lang>_khi_chay.json (gộp với lần trước), tối đa mỗi `moi_giay` giây một lần."""
    import time                                                              # noqa: PLC0415
    if len(THIEU) == _luu_thieu['n'] or time.monotonic() - _luu_thieu['luc'] < moi_giay:
        return
    f = THU_MUC / f'thieu_{lang}_khi_chay.json'
    try:
        cu = set(json.loads(f.read_text(encoding='utf-8'))) if f.exists() else set()
        ds = sorted((cu | THIEU) - set(tu_dien(lang)))
        f.write_text(json.dumps(ds, ensure_ascii=False, indent=0), encoding='utf-8')
    except (OSError, ValueError):
        return
    _luu_thieu.update(n=len(THIEU), luc=time.monotonic())


def ngon_ngu(cookie: str | None, query: str | None = None) -> str:
    """Ngôn ngữ của lượt hỏi: ?lang=… thắng cookie `lang`; mặc định tiếng Việt."""
    m = re.search(r'(?:^|&)lang=(vi|en)(?:&|$)', query or '')
    if m:
        return m.group(1)
    m = re.search(r'(?:^|;\s*)lang=(vi|en)\b', cookie or '')
    return m.group(1) if m else 'vi'
