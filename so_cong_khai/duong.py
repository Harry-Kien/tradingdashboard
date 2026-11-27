"""Nơi chương trình và dữ liệu của người dùng nằm. Không nhập mô-đun nào khác của gói (để ai cũng nhập được, không vòng).

Hai gốc khác nhau:
- gốc chương trình: tài nguyên đi kèm bản cài (tinh/, cau-hinh.mau.json, dich/...), chỉ đọc;
- gốc dữ liệu: cau-hinh.json, du-lieu/, out/ của người dùng, ghi được.
Chạy từ mã nguồn thì hai gốc là một (thư mục dự án) nên mọi thứ y như trước. Bản đóng gói thì dữ liệu để ở %LOCALAPPDATA%
để cập nhật hay gỡ chương trình không làm mất dữ liệu; biến môi trường HGR_DU_LIEU luôn được ưu tiên (dùng cho bài kiểm và máy thử)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

DONG_GOI: bool = bool(getattr(sys, 'frozen', False))      # True khi chạy từ bản đóng gói (PyInstaller)
TEN_THU_MUC = 'HarryGoldResearch'


def goc_chuong_trinh() -> Path:
    """Thư mục chứa tài nguyên của chương trình (chỉ đọc)."""
    if DONG_GOI:
        return Path(sys._MEIPASS)                          # type: ignore[attr-defined]  # noqa: SLF001 - PyInstaller đặt thuộc tính này
    return Path(__file__).resolve().parent.parent


def goc_du_lieu() -> Path:
    r"""Thư mục dữ liệu của người dùng: HGR_DU_LIEU nếu có; bản đóng gói thì %LOCALAPPDATA%\HarryGoldResearch; mã nguồn thì thư mục dự án."""
    rieng = os.environ.get('HGR_DU_LIEU')
    if rieng:
        return Path(rieng)
    if DONG_GOI:
        goc = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
        return Path(goc) / TEN_THU_MUC
    return goc_chuong_trinh()


def chuan_bi() -> Path:
    """Tạo gốc dữ liệu cùng du-lieu/ và out/ nếu chưa có; chưa có cau-hinh.json thì chép từ bản mẫu. Không ghi đè tệp đã có.
    Trả về đường dẫn cau-hinh.json."""
    goc = goc_du_lieu()
    for ten in ('du-lieu', 'out'):
        (goc / ten).mkdir(parents=True, exist_ok=True)
    cau_hinh = goc / 'cau-hinh.json'
    mau = goc_chuong_trinh() / 'cau-hinh.mau.json'
    if not cau_hinh.exists() and mau.is_file():
        cau_hinh.write_text(mau.read_text(encoding='utf-8'), encoding='utf-8')
    return cau_hinh


def lenh_mo_dun(mo_dun: str, *tham_so: str) -> list[str]:
    """Lệnh chạy một mô-đun của gói trong tiến trình riêng. Bản đóng gói không có `python -m`, nên dùng cờ --mo-dun của chính tệp chạy."""
    if DONG_GOI:
        return [sys.executable, '--mo-dun', mo_dun, *tham_so]
    return [sys.executable, '-X', 'utf8', '-m', mo_dun, *tham_so]
