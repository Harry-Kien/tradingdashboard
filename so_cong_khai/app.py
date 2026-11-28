"""Vỏ app Windows của Harry · Gold Research: mở webapp trong một cửa sổ riêng (WebView2 qua pywebview), có biểu tượng ở khay hệ thống
(pystray) và thông báo Windows cho cảnh báo giá. Bản đóng gói chạy tệp này; chạy từ mã nguồn vẫn dùng BAT_DAU.bat / so_cong_khai.web như cũ.

Một máy chỉ chạy một bản app: mutex TEN_KHOA (bộ cài cũng dò đúng tên này để biết app đang mở). Lần mở thứ hai không dựng máy chủ thứ hai
mà nhờ bản đang chạy hiện cửa sổ lên (sự kiện có tên TEN_SU_KIEN_HIEN, chờ xác nhận ở TEN_SU_KIEN_DA_HIEN; R15) rồi thoát.
Đóng cửa sổ chỉ ẩn xuống khay: vòng cảnh báo giá, Telegram, nhật ký vẫn chạy; muốn tắt hẳn thì bấm "Thoát" ở khay.

`webview`, `pystray` và `PIL` chỉ được nhập bên trong hàm: bài kiểm và bản zip chạy bằng Python không có các thư viện đó. Mọi hàm thuần
(chọn cổng, đọc tệp chạy, trang đầu, đích khi mở) tách riêng để kiểm được mà không mở cửa sổ. Chế độ thợ `--mo-dun` chạy trước mọi thứ
khác (không đụng thư mục dữ liệu, nhật ký, mutex, thư viện giao diện): bản đóng gói không có `python -m`, xem duong.lenh_mo_dun."""
from __future__ import annotations

import json
import math
import os
import re
import runpy
import socket
import sys
import threading
import time
import traceback
import urllib.parse
from pathlib import Path

from . import duong
from .thuong_hieu import TEN

TEN_KHOA = 'HarryGoldResearch.App'                 # tên mutex Windows; kịch bản bộ cài (Nhiệm vụ 6) dùng đúng chuỗi này
# Kênh "lần mở thứ hai nhờ bản đầu hiện cửa sổ" (R15): hai sự kiện có tên, tự đặt lại. Trước đây là POST /api/app {"viec": "hien"} tới cổng
# trong app-chay.json, nhưng máy chủ giờ khóa mọi yêu cầu không có cookie đăng nhập (khong_gian.py) nên lời gọi đó bị 401; không nới cổng
# đăng nhập cho việc này. Sự kiện Windows chỉ tiến trình cùng phiên đăng nhập Windows mở được, không đi qua mạng.
TEN_SU_KIEN_HIEN = 'HarryGoldResearch.App.Hien'     # bản thứ hai bật: "hiện cửa sổ đi"
TEN_SU_KIEN_DA_HIEN = 'HarryGoldResearch.App.DaHien'   # bản đầu bật sau khi đã làm "Mở": xác nhận cho bản thứ hai
# Cổng ưu tiên; localStorage của trang gắn theo cổng nên cổng phải ổn định giữa các lần mở. Dải riêng của app (R14): 8790 tới 8800. Không bao giờ
# dùng 8769 (webapp chạy từ mã nguồn: các tệp .bat coi "cổng 8769 trả lời" là webapp đã chạy) hay 8765 (bản zip cũ).
UU_TIEN = 8790
SO_CONG_KE = 10                                     # bận thì thử thêm 10 cổng liền sau rồi mới lấy cổng do hệ điều hành cấp (R7)
TOI_DA_LOG = 2 * 1024 * 1024                        # app.log lớn hơn thì cắt bỏ trước khi mở
HAN_DICH_MO = 600                                   # giây: bấm "Mở" trong 10 phút sau một cảnh báo thì vào thẳng biểu đồ của mã đó
CHO_BAN_KHAC = 5.0                                  # giây chờ bản đang chạy trả lời trước khi báo "không phản hồi"
_KHOA_WV2 = r'Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
# Theo tài liệu Microsoft "Distribute your app and the WebView2 Runtime" (mục Detect if a WebView2 Runtime is already installed):
# đọc giá trị pv (REG_SZ) ở khóa máy (Windows 64 bit: WOW6432Node; 32 bit: không có) và khóa người dùng; có ít nhất một bản khác rỗng,
# khác 0.0.0.0 là đã cài.
NOI_WEBVIEW2 = (('HKLM', 'SOFTWARE\\WOW6432Node\\' + _KHOA_WV2), ('HKLM', 'SOFTWARE\\' + _KHOA_WV2), ('HKCU', 'Software\\' + _KHOA_WV2))
_MO_DUN = re.compile(r'so_cong_khai(?:\.[A-Za-z_][A-Za-z0-9_]*)+')

# Chữ cố định của hộp thoại và thông báo Windows (không phải trang web nên không qua bộ dịch).
CHU_KHONG_PHAN_HOI = f'{TEN} đang chạy nhưng không phản hồi. Hãy thoát nó ở khay hệ thống rồi mở lại.'
CHU_BAO_KHAY = f'{TEN} vẫn chạy ở khay hệ thống để cảnh báo giá hoạt động. Bấm chuột phải vào biểu tượng để thoát.'

_TT: dict = {'khoa': None, 'log': None}            # tay cầm mutex (giữ suốt đời tiến trình) và tệp app.log đang mở


def chu_loi(log: Path) -> str:
    return f'Không khởi động được. Chi tiết nằm trong {log}'


def _bao(chu: str) -> None:
    """Một dòng nhật ký của vỏ app (ra app.log khi chạy không có cửa sổ dòng lệnh). Không bao giờ ném."""
    try:
        print(f'{time.strftime("%Y-%m-%d %H:%M:%S")} [app] {chu}', flush=True)
    except Exception:                                                          # noqa: BLE001 - ghi nhật ký hỏng không được làm hỏng app
        pass


# --------------------------------------------------------------------------- hàm thuần
def chuyen_dau_ra(goc: Path) -> None:
    """Bản đóng gói chạy không có cửa sổ dòng lệnh thì sys.stdout/sys.stderr là None: print im lặng, còn sys.stdout.write hay
    traceback thì ném lỗi. Khi đó gán cả hai vào goc/app.log (UTF-8, ghi nối, đẩy ra từng dòng). Tệp lớn hơn 2 MB thì cắt bỏ trước khi mở."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    goc.mkdir(parents=True, exist_ok=True)
    tep = goc / 'app.log'
    try:
        if tep.stat().st_size > TOI_DA_LOG:
            tep.write_bytes(b'')
    except OSError:
        pass
    f = open(tep, 'a', encoding='utf-8', errors='backslashreplace', buffering=1)   # noqa: SIM115 - mở suốt đời tiến trình
    sys.stdout = sys.stderr = f
    _TT['log'] = f


def ung_vien(uu_tien: int = UU_TIEN) -> list[int]:
    """Thứ tự thử cổng (R7): uu_tien, rồi uu_tien+1 tới uu_tien+10 (không vượt 65535)."""
    return [c for c in range(uu_tien, uu_tien + SO_CONG_KE + 1) if c <= 65535]


def _trong(cong: int) -> bool:
    """Gắn thử 127.0.0.1:cong theo kiểu độc quyền như máy chủ thật (web._MayChuDocQuyen); gắn được là cổng trống."""
    with socket.socket() as s:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):                            # Windows
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            s.bind(('127.0.0.1', cong))
        except OSError:
            return False
    return True


def _cong_he_thong() -> int:
    """Một cổng trống do hệ điều hành cấp."""
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def chon_cong(uu_tien: int = UU_TIEN) -> int:
    """Cổng trống đầu tiên theo thứ tự của ung_vien; tất cả bận thì lấy cổng do hệ điều hành cấp. Chỉ dò: máy chủ thật vẫn có thể thua
    cuộc đua giành cổng, nên main thử web.khoi_dong lần lượt từng cổng (R11)."""
    for c in ung_vien(uu_tien):
        if _trong(c):
            return c
    return _cong_he_thong()


def tep_chay(goc: Path) -> Path:
    """Tệp {'cong', 'pid'} của bản app đang chạy: cổng cho vo_app và Nhiệm vụ 6, pid để lần mở thứ hai nhường quyền lên trước (_cho_len_truoc)."""
    return goc / 'du-lieu' / 'app-chay.json'


def ghi_tep_chay(goc: Path, cong: int) -> None:
    """Ghi tệp chạy theo kiểu tệp tạm rồi thay (lần mở thứ hai không bao giờ đọc phải tệp dở dang)."""
    p = tep_chay(goc)
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_name(p.name + '.tam')
    tam.write_text(json.dumps({'cong': int(cong), 'pid': os.getpid()}), encoding='utf-8')
    os.replace(tam, p)


def _doc_tep_chay(goc: Path) -> dict | None:
    """{'cong': int, 'pid': int | None} hoặc None khi chưa có tệp, tệp hỏng hay sai định dạng."""
    try:
        d = json.loads(tep_chay(goc).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict):
        return None
    cong, pid = d.get('cong'), d.get('pid')
    if isinstance(cong, bool) or not isinstance(cong, int) or not 0 < cong <= 65535:
        return None
    return {'cong': cong, 'pid': pid if isinstance(pid, int) and not isinstance(pid, bool) and pid > 0 else None}


def trang_dau(goc: Path) -> str:
    """Lần mở đầu tiên vào trang Bắt đầu (rồi đánh dấu bằng du-lieu/app-da-mo.json), các lần sau vào trang chủ."""
    p = goc / 'du-lieu' / 'app-da-mo.json'
    if p.exists():
        return '/'
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({'luc': time.time()}), encoding='utf-8')
    except OSError:
        pass
    return '/bat-dau'


def dich_mo(canh_bao: dict | None, now: float) -> str:
    """Đích của "Mở": cảnh báo gần nhất báo trong vòng 600 giây trước `now` thì vào biểu đồ của mã và khung đó, ngược lại ''.
    pystray không báo lại lần bấm vào thông báo (Nhiệm vụ 1 câu 3), nên đây là cách thay: thấy thông báo rồi mở app thì vào đúng chỗ."""
    if not isinstance(canh_bao, dict):
        return ''
    ma, tf, luc = canh_bao.get('ma'), canh_bao.get('tf'), canh_bao.get('luc')
    if not isinstance(ma, str) or not ma or not isinstance(tf, str) or not tf:
        return ''
    if isinstance(luc, bool) or not isinstance(luc, (int, float)) or not 0 <= now - luc <= HAN_DICH_MO:   # NaN cũng rơi vào đây
        return ''
    return f'/bieu-do?ma={urllib.parse.quote(ma, safe="")}&tf={urllib.parse.quote(tf, safe="")}'


def _doc_khoa_dang_ky(goc: str, khoa: str) -> str | None:
    """Giá trị pv của một khóa đăng ký (None khi không có khóa hay không phải Windows)."""
    try:
        import winreg                                                          # noqa: PLC0415 - chỉ có trên Windows
    except ImportError:
        return None
    hive = winreg.HKEY_LOCAL_MACHINE if goc == 'HKLM' else winreg.HKEY_CURRENT_USER
    try:
        with winreg.OpenKey(hive, khoa) as k:
            gt, _ = winreg.QueryValueEx(k, 'pv')
    except OSError:
        return None
    return gt if isinstance(gt, str) else None


def co_webview2(doc_khoa=None) -> bool:
    """WebView2 Runtime đã cài chưa (xem NOI_WEBVIEW2). `doc_khoa(goc, khoa) -> str | None`: thay việc đọc khóa đăng ký khi kiểm thử."""
    doc = doc_khoa or _doc_khoa_dang_ky
    for goc, khoa in NOI_WEBVIEW2:
        try:
            pv = doc(goc, khoa)
        except Exception:                                                      # noqa: BLE001 - đọc khóa hỏng thì coi như không có khóa đó
            continue
        if isinstance(pv, str) and pv.strip() and pv.strip() != '0.0.0.0':  # noqa: S104 - phiên bản WebView2 trong registry, không phải địa chỉ bind
            return True
    return False


def doc_tu_thoat(argv: list[str]) -> float | None:
    """Tham số `--tu-thoat <giây>` (R13): số thực dương; không có thì None, sai thì ValueError."""
    if '--tu-thoat' not in argv:
        return None
    i = argv.index('--tu-thoat')
    if i + 1 >= len(argv):
        raise ValueError('--tu-thoat cần số giây')
    g = float(argv[i + 1])
    if not math.isfinite(g) or g <= 0:
        raise ValueError('--tu-thoat cần số giây dương')
    return g


# --------------------------------------------------------------------------- Windows
def _lay_khoa() -> bool:
    """Lấy mutex TEN_KHOA. True khi tiến trình này là bản duy nhất (giữ tay cầm tới khi tiến trình kết thúc, Windows tự nhả kể cả khi
    tiến trình bị giết, nên tệp chạy cũ của một bản đã chết không chặn lần mở sau)."""
    if sys.platform != 'win32':
        return True
    import ctypes                                                              # noqa: PLC0415
    from ctypes import wintypes                                                # noqa: PLC0415
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    k32.CreateMutexW.restype = ctypes.c_void_p
    k32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, ctypes.c_wchar_p]   # BOOL của Win32 là int 4 byte, không phải c_bool
    h = k32.CreateMutexW(None, False, TEN_KHOA)
    loi = ctypes.get_last_error()
    if not h:                                                                  # không mở được (thường là mutex của phiên khác): coi như đã có bản chạy
        return False
    if loi == 183:                                                             # ERROR_ALREADY_EXISTS
        k32.CloseHandle(ctypes.c_void_p(h))
        return False
    _TT['khoa'] = h
    return True


WAIT_OBJECT_0, WAIT_TIMEOUT = 0, 0x102                 # mã trả của WaitForSingleObject


def _k32():
    """kernel32 với kiểu tham số đúng cho các hàm sự kiện (HANDLE là con trỏ: để mặc định int thì tay cầm 64 bit bị cắt)."""
    import ctypes                                                              # noqa: PLC0415
    from ctypes import wintypes                                                # noqa: PLC0415
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreateEventW.restype = wintypes.HANDLE
    k.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
    for ten in ('SetEvent', 'ResetEvent', 'CloseHandle'):
        f = getattr(k, ten)
        f.restype, f.argtypes = wintypes.BOOL, [wintypes.HANDLE]
    k.WaitForSingleObject.restype = wintypes.DWORD
    k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    return k


def _su_kien(k, ten: str):
    """Mở sự kiện có tên `ten`, chưa có thì tạo: kiểu TỰ ĐẶT LẠI (mỗi tín hiệu đánh thức đúng một lần chờ rồi tự tắt), lúc tạo chưa bật.
    Tay cầm, hoặc None khi không mở được."""
    return k.CreateEventW(None, False, False, ten) or None


def bao_ban_dang_chay(cho: float) -> bool:
    """Lần mở thứ hai (R15): bật TEN_SU_KIEN_HIEN rồi chờ tới `cho` giây để bản đầu bật TEN_SU_KIEN_DA_HIEN. True khi bản đầu đã làm "Mở".
    Trước khi bật thì xóa một xác nhận cũ có thể còn treo (bản đầu từng trả lời một lần mở đã bỏ chờ), để không nhận nhầm. Sự kiện tự đặt lại giữ
    tín hiệu tới khi có người chờ: lần mở thứ hai đến lúc bản đầu chưa kịp dựng luồng chờ vẫn được trả lời, miễn là trong hạn `cho`."""
    if sys.platform != 'win32':
        return False
    k = _k32()
    hien, da = _su_kien(k, TEN_SU_KIEN_HIEN), _su_kien(k, TEN_SU_KIEN_DA_HIEN)
    try:
        if not hien or not da:
            return False
        k.ResetEvent(da)
        k.SetEvent(hien)
        return k.WaitForSingleObject(da, max(0, int(cho * 1000))) == WAIT_OBJECT_0
    finally:
        for h in (hien, da):
            if h:
                k.CloseHandle(h)


def _cho_su_kien_hien(vo, buoc: float = 0.5) -> None:
    """Luồng nền của bản đầu (R15): chờ TEN_SU_KIEN_HIEN; mỗi lần nó bật thì làm đúng hành động "Mở" của mục khay (vo.mo, gọi ngay trong
    luồng này vì đây không phải luồng HTTP hay luồng giao diện), rồi bật TEN_SU_KIEN_DA_HIEN. Chờ từng `buoc` giây một để thấy app thoát mà dừng.
    "Mở" trước khi có cửa sổ là an toàn (mo() bỏ qua, cửa sổ sẽ tự hiện); khi "Thoát" đã bắt đầu thì không làm gì, không xác nhận, và dừng."""
    if sys.platform != 'win32':
        return
    k = _k32()
    hien, da = _su_kien(k, TEN_SU_KIEN_HIEN), _su_kien(k, TEN_SU_KIEN_DA_HIEN)
    try:
        if not hien or not da:
            _bao('không tạo được sự kiện hiện cửa sổ: lần mở thứ hai sẽ báo "không phản hồi"')
            return
        while not vo.xong.is_set() and not vo.dang_thoat:
            r = k.WaitForSingleObject(hien, int(buoc * 1000))
            if r == WAIT_TIMEOUT:
                continue
            if r != WAIT_OBJECT_0:
                _bao(f'chờ sự kiện hiện cửa sổ lỗi (mã {r}): dừng luồng chờ')
                return
            if vo.dang_thoat:
                _bao('nhận sự kiện hiện cửa sổ khi app đang thoát: bỏ qua')
                return
            _bao('nhận sự kiện hiện cửa sổ từ lần mở thứ hai')
            try:
                vo.mo()
            except Exception:                                                  # noqa: BLE001 - luồng chờ không được chết vì một lần "Mở" hỏng
                _bao('mở cửa sổ lỗi:\n' + traceback.format_exc())
            k.SetEvent(da)
    finally:
        for h in (hien, da):
            if h:
                k.CloseHandle(h)


def _cho_len_truoc(goc: Path) -> None:
    """Lần mở thứ hai vừa được người dùng bấm nên có quyền đưa cửa sổ lên trước; nhường quyền đó cho bản đang chạy (Windows chặn tiến
    trình nền tự giành tiêu điểm), để cửa sổ kia thật sự lên trước chứ không chỉ nháy ở thanh tác vụ."""
    d = _doc_tep_chay(goc)
    if sys.platform != 'win32' or not d or not d['pid']:
        return
    try:
        import ctypes                                                          # noqa: PLC0415
        ctypes.windll.user32.AllowSetForegroundWindow(int(d['pid']))
    except Exception:                                                          # noqa: BLE001 - chỉ là tiện ích
        pass


def _hop_thoai(chu: str) -> None:
    """Hộp thoại lỗi của Windows (chặn tới khi người dùng bấm OK). Ghi cả vào nhật ký."""
    _bao(f'hộp thoại: {chu}')
    if sys.platform != 'win32':
        return
    try:
        import ctypes                                                          # noqa: PLC0415
        ctypes.windll.user32.MessageBoxW(None, chu, TEN, 0x10 | 0x10000)      # MB_ICONERROR | MB_SETFOREGROUND
    except Exception:                                                          # noqa: BLE001
        pass


def _ghi_loi(goc: Path, vet: str) -> None:
    """Ghi vết lỗi vào app.log (và ra stderr nếu stderr là cửa sổ dòng lệnh chứ không phải chính app.log)."""
    if sys.stderr is not None:
        try:
            sys.stderr.write(vet)
            sys.stderr.flush()
        except Exception:                                                      # noqa: BLE001
            pass
    if sys.stderr is not _TT['log']:
        try:
            goc.mkdir(parents=True, exist_ok=True)
            with open(goc / 'app.log', 'a', encoding='utf-8', errors='backslashreplace') as f:
                f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} [app] lỗi khởi động\n{vet}')
        except OSError:
            pass


# --------------------------------------------------------------------------- chế độ thợ
def _chay_mo_dun(con: list[str]) -> int:
    """`--mo-dun <mô-đun> [tham số...]`: chạy một mô-đun của gói như `python -m` (bản đóng gói không có python -m). Chỉ nhận mô-đun trong
    gói so_cong_khai; khác thì trả 2."""
    if not con or not _MO_DUN.fullmatch(con[0]):
        return 2
    mo_dun = con[0]
    sys.argv = [mo_dun, *con[1:]]
    try:
        runpy.run_module(mo_dun, run_name='__main__')
    except SystemExit as e:
        if e.code is None:
            return 0
        if isinstance(e.code, int):
            return e.code
        print(e.code, file=sys.stderr)
        return 1
    return 0


# --------------------------------------------------------------------------- vỏ app
class _Vo:
    """Trạng thái một lần chạy app: máy chủ, cửa sổ, khay, cảnh báo gần nhất và cờ "đang thoát"."""

    def __init__(self, goc: Path, cau_hinh: Path, srv, cong: int):
        self.goc, self.cau_hinh, self.srv, self.cong = goc, cau_hinh, srv, cong
        self.goc_url = f'http://127.0.0.1:{cong}'
        self.window = None                  # cửa sổ pywebview; None khi chạy bằng trình duyệt (bước 12)
        self.icon = None                    # biểu tượng khay pystray; None khi không có thư viện
        self.trinh_duyet = False
        self.dang_thoat = False
        self.khoa = threading.Lock()
        self.xong = threading.Event()       # đặt khi "Thoát" làm xong
        self.canh_bao = None                # cảnh báo gần nhất (dict của canh_bao_ve.mot_luot)
        self.thu_nho = self.phong_to = False
        self.da_kiem = False

    def cfg(self) -> dict:
        try:
            d = json.loads(self.cau_hinh.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {}
        return d if isinstance(d, dict) else {}

    def _mo_trinh_duyet(self, duong_dan: str) -> None:
        try:
            os.startfile(self.goc_url + duong_dan)                             # noqa: S606 - địa chỉ http://127.0.0.1 của chính app, mở bằng trình duyệt mặc định
        except OSError as e:
            _bao(f'không mở được trình duyệt: {e}')

    def _thong_bao(self, chu: str, tieu_de: str) -> None:
        if self.icon is None:
            _bao(f'không có khay nên không hiện thông báo: {tieu_de} | {chu}')
            return
        try:
            self.icon.notify(chu, tieu_de)
            _bao(f'đã gọi thông báo Windows: {tieu_de} | {chu}')
        except Exception as e:                                                 # noqa: BLE001 - thông báo hỏng không làm hỏng app
            _bao(f'thông báo Windows lỗi: {type(e).__name__}: {e}')

    # bước 9: móc của canh_bao_ve (gọi trong luồng của vòng kiểm: phải nhanh)
    def khi_bao(self, b: dict) -> None:
        self.canh_bao = b
        self._thong_bao(f"{b.get('mo_ta', '')} · giá {b.get('gia', '')}", f"{b.get('ten', '')} {b.get('tf', '')}")

    # bước 10: "Mở"
    def mo(self) -> None:
        if not self.trinh_duyet and self.window is None:
            # Lệnh đến khi cửa sổ chưa dựng xong (lần mở thứ hai ngay sau lần đầu, nhập webview mất vài giây): cửa sổ sắp tự hiện, đừng mở thêm
            # một thẻ trình duyệt. Giữ cảnh báo gần nhất cho lần "Mở" sau.
            _bao('nhận lệnh hiện cửa sổ khi cửa sổ chưa dựng xong: bỏ qua, cửa sổ sẽ tự hiện')
            return
        dich = dich_mo(self.canh_bao, time.time())
        try:
            if self.trinh_duyet or self.window is None:
                self._mo_trinh_duyet(dich or '/')
            else:
                self.window.show()                                             # winforms: Show() rồi Activate()
                if self.thu_nho:
                    if self.phong_to:
                        self.window.maximize()
                    else:
                        self.window.restore()
                if dich:
                    self.window.load_url(self.goc_url + dich)
            _bao('mở cửa sổ' + (f', tới {dich}' if dich else ''))
        except Exception:                                                      # noqa: BLE001
            _bao('mở cửa sổ lỗi:\n' + traceback.format_exc())
        if dich:
            self.canh_bao = None

    def hien_nen(self) -> None:
        """VO['hien'] và mục khay "Mở": trả về ngay, việc giao diện làm ở luồng khác (R12; window.show chờ cửa sổ hiện tới 20 giây)."""
        _bao('nhận lệnh hiện cửa sổ')
        threading.Thread(target=self.mo, name='app-hien', daemon=True).start()

    # bước 11: "Thoát"
    def thoat(self) -> None:
        with self.khoa:
            if self.dang_thoat:
                return
            self.dang_thoat = True                                             # bật TRƯỚC window.destroy(): destroy cũng đi qua `closing` (R8)
        _bao('thoát')
        try:
            tep_chay(self.goc).unlink(missing_ok=True)
        except OSError as e:
            _bao(f'không xóa được tệp chạy: {e}')
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:                                                  # noqa: BLE001
                _bao('tắt khay lỗi:\n' + traceback.format_exc())
        if self.window is not None and not self.trinh_duyet:
            try:
                self.window.destroy()
            except Exception:                                                  # noqa: BLE001
                _bao('đóng cửa sổ lỗi:\n' + traceback.format_exc())
        try:
            self.srv.shutdown()
        except Exception:                                                      # noqa: BLE001
            _bao('dừng máy chủ lỗi:\n' + traceback.format_exc())
        self.xong.set()

    def thoat_nen(self, cho: float = 0.5) -> None:
        """VO['thoat']: được gọi giữa một yêu cầu HTTP, trước khi phản hồi đi. Trả về ngay; thoát ở luồng khác sau `cho` giây (R12)."""
        t = threading.Timer(cho, self.thoat)
        t.daemon = True
        t.start()

    def thoat_khay(self) -> None:
        """Mục khay "Thoát" (chạy trong luồng của pystray: không tự dừng khay từ chính luồng đó)."""
        threading.Thread(target=self.thoat, name='app-thoat', daemon=True).start()

    # bước 8: đóng cửa sổ → ẩn xuống khay (chạy đồng bộ trên luồng giao diện; trả False là hủy đóng)
    def khi_dong(self):
        if self.dang_thoat or self.icon is None:                               # đang thoát thật, hoặc không có khay để mở lại: cho đóng
            return True
        try:
            self.window.hide()
        except Exception:                                                      # noqa: BLE001
            _bao('ẩn cửa sổ lỗi:\n' + traceback.format_exc())
        _bao('đóng cửa sổ: ẩn xuống khay')
        p = self.goc / 'du-lieu' / 'app-da-bao-khay.json'
        if not p.exists():
            threading.Thread(target=self._thong_bao, args=(CHU_BAO_KHAY, TEN), daemon=True).start()
            try:
                p.write_text(json.dumps({'luc': time.time()}), encoding='utf-8')
            except OSError:
                pass
        return False

    def khi_thu_nho(self) -> None:
        self.thu_nho = True

    def khi_phong_to(self) -> None:
        self.thu_nho, self.phong_to = False, True

    def khi_tro_lai(self) -> None:
        self.thu_nho = self.phong_to = False

    # bước 13: kiểm bản mới một lần, sau khi cửa sổ (hoặc trình duyệt) đã hiện
    def khi_hien(self) -> None:
        if self.da_kiem:
            return
        self.da_kiem = True
        _bao('cửa sổ đã hiện')
        threading.Thread(target=self._kiem_cap_nhat, name='app-cap-nhat', daemon=True).start()

    def _kiem_cap_nhat(self) -> None:
        try:
            from . import cap_nhat                                             # noqa: PLC0415
            tt = cap_nhat.kiem(self.cfg())
            _bao(f'kiểm bản mới: lần kiểm {tt.get("lan_kiem")}, lỗi {tt.get("loi")}')
        except Exception:                                                      # noqa: BLE001 - kiểm bản mới không bao giờ được làm hỏng app
            _bao('kiểm bản mới lỗi:\n' + traceback.format_exc())


def _tao_khay(vo: _Vo):
    """Biểu tượng khay với hai mục "Mở" (mặc định: bấm chuột trái một lần, R8) và "Thoát"; chạy vòng tin nhắn riêng (run_detached,
    phải gọi trước webview.start). Không có pystray hay Pillow thì None."""
    try:
        import pystray                                                         # noqa: PLC0415
        from PIL import Image                                                  # noqa: PLC0415
    except ImportError as e:
        _bao(f'không có khay hệ thống ({e})')
        return None
    try:
        anh = Image.open(duong.goc_chuong_trinh() / 'tinh' / 'logo.ico')
        anh.load()
    except OSError:
        anh = Image.new('RGB', (64, 64), (201, 162, 39))
    menu = pystray.Menu(pystray.MenuItem('Mở', vo.hien_nen, default=True), pystray.MenuItem('Thoát', vo.thoat_khay))
    icon = pystray.Icon('HarryGoldResearch', anh, TEN, menu)
    icon.run_detached()
    return icon


def _mo_may_chu(cau_hinh: Path):
    """Bước 4 (R7, R11): chọn cổng như chon_cong (cổng của ung_vien đã thấy bận thì bỏ qua, khỏi dựng vòng canh và bảng giá vô ích), rồi
    web.khoi_dong. Nó vẫn có thể ném OSError khi thua cuộc đua giành cổng với tiến trình khác (máy chủ mở cổng độc quyền trước mọi vòng nền,
    nên chưa có gì chạy): khi đó thử cổng kế tiếp theo đúng thứ tự, hết ung_vien thì tối đa ba cổng do hệ điều hành cấp.
    Trả (máy chủ chưa phục vụ, cổng)."""
    from . import web                                                          # noqa: PLC0415 - nhập nặng, và chỉ sau khi đã chắc không phải chế độ thợ
    loi = None
    for c in [*ung_vien(UU_TIEN), None, None, None]:
        if c is not None and not _trong(c):
            continue
        cong = c if c is not None else _cong_he_thong()
        try:
            srv = web.khoi_dong(str(cau_hinh), cong)
        except OSError as e:
            loi = e
            _bao(f'cổng {cong} không dùng được ({type(e).__name__}: {e}); thử cổng kế tiếp')
            continue
        return srv, srv.server_address[1]
    raise OSError(f'không mở được cổng nào: {loi}')


def _chay_giao_dien(vo: _Vo, tu_thoat: float | None) -> None:
    """Bước 5 tới 13. Chạy trên luồng chính (pywebview bắt buộc) và chỉ trả về khi app thoát."""
    from . import canh_bao_ve                                                  # noqa: PLC0415
    if vo.cfg().get('giu_may_thuc'):                                           # bước 5: luồng chính sống suốt đời app
        from . import giu_thuc                                                 # noqa: PLC0415
        _bao('giữ máy thức: ' + ('đã bật' if giu_thuc.bat() else f'không bật được ({giu_thuc.TT["loi"]})'))
    vo.icon = _tao_khay(vo)                                                    # bước 6
    canh_bao_ve.KHI_BAO.append(vo.khi_bao)                                     # bước 9
    if tu_thoat:                                                               # R13: tự đi đúng đường của mục "Thoát"
        t = threading.Timer(tu_thoat, vo.thoat)
        t.daemon = True
        t.start()
        _bao(f'sẽ tự thoát sau {tu_thoat:g} giây')
    # Khay, máy chủ và hẹn giờ --tu-thoat đều đã chạy từ đây, mà nhập webview (pythonnet) có thể mất vài giây ở bản đóng gói: "Thoát" có thể đến
    # TRƯỚC khi có cửa sổ. Khi đó thoat() không có cửa sổ để đóng; nếu vẫn mở cửa sổ thì nó gắn với máy chủ đã chết, không còn khay, và tiến
    # trình không bao giờ tự kết thúc. Nên: kiểm cờ đang thoát trước mỗi bước, và gán vo.window DƯỚI CÙNG khóa với thoat(), để hoặc thoat()
    # thấy cửa sổ và đóng nó (destroy chờ cửa sổ hiện), hoặc ở đây thấy cờ và không start.
    url = vo.goc_url + trang_dau(vo.goc)
    if vo.dang_thoat:
        _bao('đã nhận lệnh thoát trước khi mở cửa sổ')
    elif co_webview2():                                                        # bước 7
        try:
            import webview                                                     # noqa: PLC0415
            webview.settings['ALLOW_DOWNLOADS'] = True                         # nút tải ảnh biểu đồ: hiện hộp lưu tệp
            webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True          # chỉ áp cho liên kết mở cửa sổ mới (target="_blank", window.open)
            w = webview.create_window(TEN, url, width=1280, height=800, min_size=(900, 600))
            w.events.closing += vo.khi_dong
            w.events.shown += vo.khi_hien
            w.events.minimized += vo.khi_thu_nho
            w.events.maximized += vo.khi_phong_to
            w.events.restored += vo.khi_tro_lai
            with vo.khoa:
                mo_cua_so = not vo.dang_thoat
                if mo_cua_so:
                    vo.window = w
            if mo_cua_so:
                _bao(f'mở cửa sổ ở {url}')
                # private_mode=False: mặc định True xóa localStorage (cài đặt giao diện của các trang) mỗi lần mở (R6)
                webview.start(private_mode=False, storage_path=str(vo.goc / 'webview'))
            else:
                _bao('đã nhận lệnh thoát trong lúc dựng cửa sổ: không mở cửa sổ')
        except Exception:                                                      # noqa: BLE001 - bước 12: cửa sổ hỏng thì dùng trình duyệt
            _bao('mở cửa sổ lỗi, chuyển sang trình duyệt:\n' + traceback.format_exc())
            vo.window = None                                                   # cửa sổ đã tạo nhưng không chạy được: đừng coi là "người dùng đã đóng"
    else:
        _bao('máy không có WebView2 Runtime: dùng trình duyệt mặc định')
    if vo.window is not None and vo.icon is None and not vo.dang_thoat:       # cửa sổ đã đóng mà không có khay để mở lại: thoát
        vo.thoat()
    else:
        with vo.khoa:                                                          # bước 12: trình duyệt mặc định, app vẫn chạy ở khay
            dung_trinh_duyet = not vo.dang_thoat
            if dung_trinh_duyet:
                vo.trinh_duyet, vo.window = True, None
        if dung_trinh_duyet:
            vo._mo_trinh_duyet(url[len(vo.goc_url):])
            vo.khi_hien()
            if vo.icon is None:
                _bao('không có khay hệ thống: app chạy tới khi tiến trình bị dừng')
    vo.xong.wait()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == '--mo-dun':                                         # bước 1: trước mọi thứ khác
        return _chay_mo_dun(argv[1:])
    try:
        tu_thoat = doc_tu_thoat(argv)
    except ValueError:
        return 2
    goc = duong.goc_du_lieu()
    srv = None
    try:                                                                       # bước 2 tới 4; lỗi thì bước 14
        chuyen_dau_ra(goc)                                                     # trước chuan_bi để lỗi của nó cũng vào app.log
        cau_hinh = duong.chuan_bi()
        _bao(f'khởi động, pid {os.getpid()}, dữ liệu ở {goc}')
        if not _lay_khoa():                                                    # bước 3
            _bao('đã có một bản app khác đang chạy: báo nó hiện cửa sổ (sự kiện Windows)')
            _cho_len_truoc(goc)
            if bao_ban_dang_chay(CHO_BAN_KHAC):                               # R15: không qua HTTP (cổng đăng nhập trả 401)
                _bao('bản đang chạy đã hiện cửa sổ; thoát')
                return 0
            _hop_thoai(CHU_KHONG_PHAN_HOI)
            return 1
        # Đã giữ mutex thì tệp chạy còn sót là của một bản đã chết (bị giết, mất điện). Xóa ngay, để vo_app, bộ cài và lần mở thứ hai (lấy pid
        # để nhường quyền lên trước) không đọc phải cổng và pid cũ trong lúc bản này còn dựng máy chủ.
        tep_chay(goc).unlink(missing_ok=True)
        srv, cong = _mo_may_chu(cau_hinh)                                      # bước 4
        vo = _Vo(goc, cau_hinh, srv, cong)
        from . import vo_app                                                   # noqa: PLC0415
        vo_app.VO.update(hien=vo.hien_nen, thoat=vo.thoat_nen, cong=cong)
        # R15: lần mở thứ hai báo bằng sự kiện có tên; luồng này làm "Mở" rồi xác nhận, và tự dừng khi app thoát.
        threading.Thread(target=_cho_su_kien_hien, args=(vo,), name='app-su-kien-hien', daemon=True).start()
        threading.Thread(target=srv.serve_forever, name='may-chu', daemon=True).start()
        ghi_tep_chay(goc, cong)
        _bao(f'máy chủ chạy ở cổng {cong}')
    except Exception:                                                          # noqa: BLE001 - bước 14
        _ghi_loi(goc, traceback.format_exc())
        if srv is not None:
            try:
                srv.server_close()
            except Exception:                                                  # noqa: BLE001
                pass
        _hop_thoai(chu_loi(goc / 'app.log'))
        return 1
    _chay_giao_dien(vo, tu_thoat)
    try:
        srv.server_close()
    except Exception:                                                          # noqa: BLE001
        pass
    _bao('đã thoát')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
