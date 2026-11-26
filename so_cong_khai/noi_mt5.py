"""Nối MT5 độc lập, CHỈ ĐỌC, cho máy không có mã EA Promax (bản chia sẻ cho người khác).

Giữ đúng các chốt an toàn của hàm nối trong EA Promax (tools.ai_signal_loop._attach):
- không bao giờ tự mở MT5: chỉ nối khi đã thấy đúng một MT5 đang chạy ở đường dẫn đó và cửa sổ chính của nó đang hiện, nhìn hai lần
  cách nhau vài giây; nếu thư viện vẫn lỡ tự mở một MT5 khác thì ngắt và đóng cái vừa mở;
- mặc định chỉ nhận tài khoản DEMO (`gia.mt5.chi_demo`, mặc định true);
- sau khi nối chỉ đọc giá, nến, thông số mã; mô-đun không có lời gọi đặt lệnh nào.

Thêm hai việc mà bản chia sẻ cần:
- tự tìm MT5 đang mở khi cấu hình không ghi đường dẫn (`gia.mt5.terminal` để trống), tự tìm mã vàng của sàn (XAUUSD, XAUUSDm, GOLD...);
- tự đo độ lệch giờ máy chủ của sàn so với UTC (nhiều sàn chạy UTC+2/+3) rồi đổi mọi giờ nến và tick về UTC qua lớp bọc `LechGio`,
  để biểu đồ, luật và lịch tin không bị lệch vài tiếng."""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

LOP_CUA_SO = 'MetaQuotes::MetaTrader'
CHO_GIAY = 3.0
_LIET_KE = ("Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe' OR Name='metatester64.exe'\" | "
            "ForEach-Object { \"$($_.Name)|$($_.ProcessId)|$($_.ExecutablePath)\" }")
CHUA_MO = 'Chưa thấy MT5 nào đang mở. Hãy mở MT5, đăng nhập tài khoản demo, rồi tải lại trang.'
DANG_DOI = ('MT5 đang khởi động hoặc đang tắt (chưa thấy cửa sổ chính); chưa nối, để thư viện MT5 không tự mở thêm một MT5 khác.')
VUA_DOI = 'MT5 vừa đổi tiến trình trong lúc kiểm tra; chưa nối, sẽ thử lại.'
TU_MO = ('Trong lúc nối, thư viện MT5 đã tự mở thêm một MT5 khác; đã ngắt và đóng bản vừa mở. Hãy để MT5 mở sẵn và đăng nhập rồi thử lại.')


def _powershell() -> str:
    """Đường dẫn đầy đủ tới powershell.exe của Windows (không gọi tên trơn: Windows tìm cả thư mục hiện hành trước, Ruff S607)."""
    p = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'
    return str(p) if p.is_file() else 'powershell'


# ---- tiến trình và cửa sổ (chỉ liệt kê, không nối vào MT5)
def tien_trinh() -> list[tuple[str, int, str]] | None:
    """(tên tệp chạy, PID, đường dẫn) của mọi terminal64 và metatester64 đang chạy; None nếu không đọc được."""
    try:
        r = subprocess.run([_powershell(), '-NoProfile', '-Command', _LIET_KE], capture_output=True, text=True, timeout=30,   # noqa: S603 - lệnh và tham số cố định, PID ép int, chữ ổ đã kiểm A–Z
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if r.returncode != 0:
            return None
        out = []
        for line in r.stdout.splitlines():
            p = line.strip().split('|', 2)
            if len(p) == 3 and p[1].isdigit():
                out.append((p[0].lower(), int(p[1]), p[2]))
        return out
    except Exception:                                                        # noqa: BLE001
        return None


def cung_duong(a: str, b: str) -> bool:
    return bool(a) and bool(b) and str(Path(a)).casefold() == str(Path(b)).casefold()


def co_cua_so(pid: int) -> bool:
    """MT5 còn cửa sổ chính đang hiện hay không (liệt kê cửa sổ Win32, không gửi gì cho MT5). Không xác định được thì coi là không."""
    try:
        import ctypes                                                        # noqa: PLC0415
        from ctypes import wintypes                                          # noqa: PLC0415
        user32 = ctypes.WinDLL('user32')
    except Exception:                                                        # noqa: BLE001
        return False
    thay = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def moi(hwnd, _):
        chu = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(chu))
        if chu.value == pid and user32.IsWindowVisible(hwnd):
            ten = ctypes.create_unicode_buffer(128)
            user32.GetClassNameW(hwnd, ten, 128)
            if ten.value.startswith(LOP_CUA_SO):
                thay.append(hwnd)
                return False
        return True
    user32.EnumWindows(moi, 0)
    return bool(thay)


def _dong(pid: int) -> None:
    """Yêu cầu một MT5 đóng êm (CloseMainWindow). Chỉ dùng cho MT5 do thư viện vừa tự mở."""
    try:
        subprocess.run([_powershell(), '-NoProfile', '-Command',   # noqa: S603 - lệnh và tham số cố định, PID ép int, chữ ổ đã kiểm A–Z
                        f'$p = Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue; $t = (Get-Date).AddSeconds(40); '
                        'while ($p -and -not $p.HasExited -and (Get-Date) -lt $t) { $p.Refresh(); $p.CloseMainWindow() | Out-Null; Start-Sleep -Seconds 2 }'],
                       capture_output=True, text=True, timeout=60, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except Exception:                                                        # noqa: BLE001
        pass


def chon_terminal(chi_dinh: str | None, procs: list | None) -> tuple[str | None, tuple[int, ...] | None, str | None]:
    """(đường dẫn terminal, các PID của nó, lý do không chọn được). Không ghi đường dẫn thì nhận MT5 duy nhất đang mở."""
    if procs is None:
        return None, None, 'Không đọc được danh sách tiến trình của Windows để tìm MT5.'
    terms = [(pid, path) for ten, pid, path in procs if ten == 'terminal64.exe']
    testers = [path for ten, pid, path in procs if ten == 'metatester64.exe']
    if any(not path for _, path in terms):
        return None, None, 'Có MT5 đang chạy mà không đọc được đường dẫn (thường do chạy bằng quyền quản trị); hãy ghi gia.mt5.terminal.'
    if chi_dinh:
        mine = tuple(sorted(pid for pid, path in terms if cung_duong(path, chi_dinh)))
        if not mine:
            return None, None, 'MT5 đã chọn trong Cài đặt chưa mở. Hãy mở MT5 đó và đăng nhập, hoặc chọn MT5 khác ở trang Cài đặt (/cai-dat).'
        duong = chi_dinh
    else:
        cac = sorted({str(Path(path)).casefold(): path for _, path in terms}.values())
        if not cac:
            return None, None, CHUA_MO
        if len(cac) > 1:
            return None, None, f'Máy đang mở {len(cac)} MT5. Chọn MT5 muốn dùng ở trang Cài đặt (/cai-dat).'
        duong = cac[0]
        mine = tuple(sorted(pid for pid, path in terms if cung_duong(path, duong)))
    if any(not path or cung_duong(str(Path(path).parent), str(Path(duong).parent)) for path in testers):
        return None, None, 'MT5 này đang chạy Strategy Tester; chờ chạy xong rồi thử lại.'
    return duong, mine, None


def noi(mt5, cfgm: dict, procs_fn=tien_trinh, window_fn=co_cua_so, sleep=time.sleep, dong_fn=_dong) -> tuple[str | None, str | None]:
    """Nối vào MT5 đang mở. Trả (đường dẫn terminal, None) khi đã nối, hoặc (None, lý do) khi không nối (lúc đó đã ngắt)."""
    duong, pids, ly_do = chon_terminal((cfgm.get('terminal') or '').strip() or None, procs_fn())
    if ly_do:
        return None, ly_do
    if not all(window_fn(p) for p in pids):
        return None, DANG_DOI
    sleep(CHO_GIAY)                                                          # MT5 vừa bấm đóng vẫn còn cửa sổ thêm một hai giây
    _, pids2, ly_do = chon_terminal(duong, procs_fn())
    if ly_do or pids2 != pids:
        return None, ly_do or VUA_DOI
    if not all(window_fn(p) for p in pids):
        return None, DANG_DOI
    ok = mt5.initialize(path=duong)
    _, pids3, _ = chon_terminal(duong, procs_fn())
    if pids3 != pids:                                                        # thư viện đã tự mở một MT5 khác: không dùng, đóng cái vừa mở
        mt5.shutdown()
        for pid in set(pids3 or ()) - set(pids):
            dong_fn(pid)
        return None, TU_MO
    if not ok:
        err = mt5.last_error()
        if isinstance(err, tuple) and err and err[0] == -6:
            return None, f'MT5 đang mở nhưng chưa đăng nhập được tài khoản ({err[1]}); hãy đăng nhập trong MT5.'
        return None, f'Không kết nối được MT5: {err}'
    info, acc = mt5.terminal_info(), mt5.account_info()
    why = None
    if info is None or acc is None:
        why = 'MT5 chưa trả thông tin tài khoản; hãy đăng nhập trong MT5.'
    elif cfgm.get('chi_demo', True) and getattr(acc, 'trade_mode', None) != 0:
        why = ('Tài khoản đang đăng nhập trong MT5 không phải tài khoản DEMO; webapp mặc định chỉ đọc tài khoản demo. '
               'Muốn đọc giá từ tài khoản khác thì tắt "Chỉ đọc tài khoản demo" ở trang Cài đặt (/cai-dat); webapp vẫn chỉ đọc, không đặt lệnh.')
    elif not getattr(info, 'connected', False):
        why = 'MT5 chưa kết nối máy chủ của sàn.'
    if why:
        mt5.shutdown()
        return None, why
    return duong, None


# ---- mã vàng và giờ của sàn
def tim_ma_vang(mt5, chi_dinh: str | None = None) -> str | None:
    """Mã vàng giao ngay theo đô la Mỹ của sàn: theo cấu hình nếu có, không thì XAUUSD kèm hậu tố của sàn (XAUUSDm, XAUUSD.r...), rồi GOLD."""
    ds = mt5.symbols_get() or []
    ten = {s.name: s for s in ds}
    if chi_dinh and chi_dinh in ten:
        return chi_dinh
    ung = [s for s in ds if s.name.upper().startswith('XAUUSD')] or [s for s in ds if s.name.upper().startswith('GOLD')]
    if not ung:
        return None
    ung.sort(key=lambda s: (not getattr(s, 'visible', False), len(s.name), s.name))
    return ung[0].name


def do_lech(mt5, ma: str | None = None, now: float | None = None) -> int | None:
    """Giờ máy chủ của sàn trừ giờ UTC, tính bằng giây và làm tròn tới nửa giờ. Đo bằng tick mới nhất của mọi mã đang hiện
    (mã tiền mã hóa có giá cả cuối tuần). None nếu không có tick nào đủ mới để đo (thị trường nghỉ hết)."""
    now = time.time() if now is None else now
    ten = ([ma] if ma else []) + [s.name for s in (mt5.symbols_get() or []) if getattr(s, 'visible', False)]
    moi = None
    for t in ten[:150]:
        tk = mt5.symbol_info_tick(t)
        if tk is not None and tk.time and (moi is None or tk.time > moi):
            moi = int(tk.time)
    if moi is None:
        return None
    d = moi - now
    lech = round(d / 1800) * 1800
    if abs(lech) > 14 * 3600 or abs(d - lech) > 600:                         # tick cũ hơn 10 phút: không đo được
        return None
    return int(lech)


def lech_gio(mt5, cfgm: dict, ma: str | None, luu: Path | None) -> tuple[int, str]:
    """(độ lệch giây, nguồn). Thứ tự: cấu hình gia.mt5.lech_gio_san (giờ) > đo được > lần đo trước đã lưu > 0."""
    if cfgm.get('lech_gio_san') not in (None, ''):
        return int(round(float(cfgm['lech_gio_san']) * 3600)), 'theo cấu hình'
    acc = mt5.account_info()
    may_chu = getattr(acc, 'server', '') or ''
    da_luu = {}
    if luu is not None and luu.exists():
        try:
            da_luu = json.loads(luu.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            da_luu = {}
    d = do_lech(mt5, ma)
    if d is not None:
        if luu is not None and da_luu.get(may_chu) != d:
            try:
                luu.parent.mkdir(parents=True, exist_ok=True)
                luu.write_text(json.dumps({**da_luu, may_chu: d}, ensure_ascii=False), encoding='utf-8')
            except OSError:
                pass
        return d, 'đo từ tick'
    if may_chu in da_luu:
        return int(da_luu[may_chu]), 'lần đo trước'
    return 0, 'chưa đo được (thị trường đang nghỉ), tạm coi là UTC'


class _TickUTC:
    """Tick của MT5 với giờ đã đổi về UTC; các trường khác đọc thẳng từ tick gốc."""
    __slots__ = ('_t', 'time', 'time_msc')

    def __init__(self, t, lech: int):
        self._t, self.time, self.time_msc = t, int(t.time) - lech, int(t.time_msc) - lech * 1000

    def __getattr__(self, k):
        return getattr(self._t, k)


_GIO = ('time', 'time_update', 'time_setup', 'time_done', 'time_expiration')


class _BanUTC:
    """Lệnh, lệnh chờ, giao dịch của MT5 với mọi trường giờ đã đổi về UTC (giây và mili giây); 0 nghĩa là "không có" nên giữ 0."""
    __slots__ = ('_x', '_lech')

    def __init__(self, x, lech: int):
        self._x, self._lech = x, lech

    def __getattr__(self, k):
        v = getattr(self._x, k)
        if k in _GIO and v:
            return int(v) - self._lech
        if k.endswith('_msc') and k[:-4] in _GIO and v:
            return int(v) - self._lech * 1000
        return v

    def _asdict(self) -> dict:
        return {k: getattr(self, k) for k in self._x._asdict()}


def _cong(dt, lech: int):
    if isinstance(dt, datetime):
        return dt + timedelta(seconds=lech)
    if isinstance(dt, (int, float)):
        return dt + lech
    return dt


class LechGio:
    """Bọc thư viện MetaTrader5: mọi giờ nến và tick đọc ra đã đổi từ giờ máy chủ của sàn về UTC, mọi giờ truyền vào được đổi ngược lại.
    Các hàm khác đi thẳng tới thư viện. Độ lệch 0 thì không đổi gì."""

    def __init__(self, mt5, lech: int = 0):
        self._m, self.lech = mt5, int(lech)

    def __getattr__(self, k):
        return getattr(self._m, k)

    def _r(self, r, msc: bool = False):
        if r is None or not self.lech or len(r) == 0:
            return r
        r = r.copy()
        r['time'] -= self.lech
        if msc and 'time_msc' in (r.dtype.names or ()):
            r['time_msc'] -= self.lech * 1000
        return r

    def copy_rates_from_pos(self, *a, **k):
        return self._r(self._m.copy_rates_from_pos(*a, **k))

    def copy_rates_from(self, sym, tf, tu, n):
        return self._r(self._m.copy_rates_from(sym, tf, _cong(tu, self.lech), n))

    def copy_rates_range(self, sym, tf, a, b):
        return self._r(self._m.copy_rates_range(sym, tf, _cong(a, self.lech), _cong(b, self.lech)))

    def copy_ticks_from(self, sym, tu, n, flags):
        return self._r(self._m.copy_ticks_from(sym, _cong(tu, self.lech), n, flags), True)

    def copy_ticks_range(self, sym, a, b, flags):
        return self._r(self._m.copy_ticks_range(sym, _cong(a, self.lech), _cong(b, self.lech), flags), True)

    def symbol_info_tick(self, sym):
        t = self._m.symbol_info_tick(sym)
        return t if t is None or not self.lech else _TickUTC(t, self.lech)

    def _ban(self, ds):
        return ds if ds is None or not self.lech else tuple(_BanUTC(x, self.lech) for x in ds)

    def _lich_su(self, ham, a, k):
        a = tuple(_cong(x, self.lech) for x in a)                            # khoảng ngày truyền vào: UTC → giờ máy chủ của sàn
        k = {n: (_cong(v, self.lech) if n in ('date_from', 'date_to') else v) for n, v in k.items()}
        return self._ban(ham(*a, **k))

    def history_deals_get(self, *a, **k):
        return self._lich_su(self._m.history_deals_get, a, k)

    def history_orders_get(self, *a, **k):
        return self._lich_su(self._m.history_orders_get, a, k)

    def positions_get(self, *a, **k):
        return self._ban(self._m.positions_get(*a, **k))

    def orders_get(self, *a, **k):
        return self._ban(self._m.orders_get(*a, **k))


# ---- hàm đọc cho song.khung_song (cùng dạng với deps của EA Promax)
class Doc:
    """get_bars(tf, n): nến ĐÃ ĐÓNG (bỏ nến đang chạy) dạng DataFrame time(UTC)/open/high/low/close; get_tick(): (bid, ask, giờ UTC)."""

    def __init__(self, mt5, ma: str):
        self.mt5, self.ma = mt5, ma

    def get_bars(self, tf: str, n: int):
        r = self.mt5.copy_rates_from_pos(self.ma, getattr(self.mt5, 'TIMEFRAME_' + tf), 1, n)
        if r is None or len(r) == 0:
            return None
        df = pd.DataFrame(r)
        df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
        return df[['time', 'open', 'high', 'low', 'close']]

    def get_tick(self):
        t = self.mt5.symbol_info_tick(self.ma)
        if t is None or not t.bid or not t.ask:
            return None
        return float(t.bid), float(t.ask), datetime.fromtimestamp(t.time, timezone.utc)
