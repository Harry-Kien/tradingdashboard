"""Ảnh biểu đồ của một lệnh trong nhật ký, để đăng kèm tin tín hiệu ở nhóm Telegram.

Chụp chính trang Biểu đồ của webapp ở chế độ ảnh (/bieu-do?anh=1&nk=<id>&ma=<mã>&tf=<khung>): chỉ còn biểu đồ nến, vùng vào lệnh, dừng lỗ, chốt lời
của đúng dòng nhật ký đó, và nhãn thương hiệu cố định. Trình duyệt chạy ẩn (Playwright, Chromium); máy không cài Playwright hoặc trang không vẽ được
lệnh thì trả None, và tin được gửi bằng chữ như cũ. Có thời hạn ngắn để vòng nền Telegram không bị treo. Chỉ đọc trang của chính máy này."""
from __future__ import annotations

import re
import time
from pathlib import Path
from urllib.parse import urlencode

RONG, CAO = 1280, 720            # khung ảnh (điểm ảnh CSS); ảnh thật gấp đôi cho nét
HAN_GIAY = 20                    # quá thời hạn thì bỏ ảnh
GIU_ANH = 200                    # số ảnh giữ trong thư mục, cũ hơn thì xóa
KHUNG = ('M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1')


def duong_dan(dia_chi: str, r: dict) -> str:
    """Đường tới trang Biểu đồ ở chế độ ảnh cho dòng nhật ký `r`."""
    q = {'anh': 1, 'nk': int(r['id'])}
    if r.get('sym'):
        q['ma'] = r['sym']
    tf = str(r.get('khung') or r.get('tf') or '')
    if tf not in KHUNG:                                           # nhật ký ghi khung trong lý do ("… Khung M5.")
        m = re.search(r'\bKhung (M1|M5|M15|M30|H1|H4|D1)\b', str(r.get('ly_do') or ''))
        tf = m.group(1) if m else ''
    if tf in KHUNG:
        q['tf'] = tf
    return dia_chi.rstrip('/') + '/bieu-do?' + urlencode(q)


def _don(thu_muc: Path) -> None:
    anh = sorted(thu_muc.glob('lenh-*.png'), key=lambda p: p.stat().st_mtime)
    for p in anh[:-GIU_ANH]:
        try:
            p.unlink()
        except OSError:
            pass


def chup(dia_chi: str, r: dict, thu_muc: Path, han: float = HAN_GIAY) -> Path | None:
    """Chụp ảnh lệnh `r` (một dòng nhật ký) thành thu_muc/lenh-<id>.png. Trả đường tệp, hoặc None khi không chụp được trong `han` giây."""
    try:
        from playwright.sync_api import sync_playwright          # noqa: PLC0415 - không bắt buộc: bản chia sẻ có thể không cài
    except ImportError:
        return None
    thu_muc.mkdir(parents=True, exist_ok=True)
    tep = thu_muc / f'lenh-{int(r["id"])}.png'
    bat_dau = time.monotonic()
    try:
        con = lambda: max(1.0, han - (time.monotonic() - bat_dau)) * 1000      # noqa: E731 - một hạn chung cho cả lần chụp, không phải cho từng bước
        with sync_playwright() as p:
            b = p.chromium.launch(timeout=con())
            try:
                pg = b.new_page(viewport={'width': RONG, 'height': CAO}, device_scale_factor=2)
                pg.goto(duong_dan(dia_chi, r), timeout=con())
                pg.wait_for_function('document.documentElement.dataset.anh', timeout=con())
                if pg.evaluate('document.documentElement.dataset.anh') != 'san':
                    return None                                   # trang không thấy lệnh này (khác mã, hoặc dòng đã bị xóa)
                pg.screenshot(path=str(tep), timeout=con())
            finally:
                b.close()
    except Exception:                                             # noqa: BLE001 - mọi lỗi chụp đều quay về gửi chữ
        return None
    _don(thu_muc)
    return tep if tep.exists() and tep.stat().st_size > 0 else None
