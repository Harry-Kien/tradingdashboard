"""Đo lại trên dữ liệu mới, tự động: chạy cong-cu/do_lai_du_lieu_moi.py theo lịch đã đăng ký ("khoảng mỗi tháng") và cho các trang đọc kết luận.

Cách đo và cách kết luận đã ghi TRƯỚC ở cong-cu/CHUAN_HOA_DANG_KY.md (phần "Đo lại trên dữ liệu mới"): các luật và công thức chốt ngày 24/11/2026 được
chạy lại nguyên trạng trên giá từ 25/11/2026, phần chưa phép đo nào nhìn thấy; dưới 30 lệnh là "chưa đủ lệnh", từ 30 lệnh kết luận theo khoảng tin cậy
90% của R mỗi lệnh. Tự chạy mỗi tháng một lần (lần đầu trong tháng mới), đúng nhịp đã ghi: đo dày hơn là nhìn nhiều lần vào cùng một phép kiểm, dễ gặp
kết luận may. Người dùng vẫn bấm "Đo lại ngay" được. Công cụ chạy ở một tiến trình riêng, ưu tiên thấp, để webapp không chậm. Chỉ đọc tệp nến và ghi
out/du-lieu-moi.json; không nối MT5, không đặt lệnh, không sửa luật nào. Bản chia sẻ không có công cụ và số đo gốc nên phần này tự tắt."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .__main__ import HERE

CONG_CU = 'cong-cu/do_lai_du_lieu_moi.py'
CAN = ('out/diem-vao.json', 'out/diem-vao-bot.json', 'out/loc-lenh-bot.json')      # số đo gốc mà công cụ cần
KET_QUA = 'out/du-lieu-moi.json'
HAN_GIAY = 30 * 60
TEN_KET = {'chua_du': 'chưa đủ lệnh', 'co_lai': 'vẫn có lãi', 'lo_ro': 'đang lỗ rõ', 'chua_ro': 'chưa phân định'}     # cùng mã với công cụ
TT: dict = {'dang': False, 'loi': None, 'bat_dau': None, 'xong': None}
_khoa = threading.Lock()


def co_the(goc: Path = HERE) -> bool:
    """Máy này có công cụ và các số đo gốc (bản của chủ dự án), nên đo lại được."""
    return (goc / CONG_CU).is_file() and all((goc / p).is_file() for p in CAN)


def doc(goc: Path = HERE) -> dict | None:
    try:
        return json.loads((goc / KET_QUA).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def den_han(kq: dict | None, now: datetime) -> bool:
    """Tới lịch đo: chưa đo lần nào, hoặc lần gần nhất thuộc một tháng trước tháng hiện tại."""
    if not kq or not kq.get('luc'):
        return True
    try:
        luc = datetime.fromisoformat(kq['luc'])
    except ValueError:
        return True
    return (luc.year, luc.month) < (now.year, now.month)


def chay(goc: Path = HERE, chay_lenh=subprocess.run) -> dict:
    """Chạy công cụ một lần (chặn tới khi xong). Trả {'ok', 'loi'}; ghi log ra out/du-lieu-moi.log."""
    if not _khoa.acquire(blocking=False):
        return {'ok': False, 'loi': 'đang đo'}
    TT.update(dang=True, loi=None, bat_dau=datetime.now(timezone.utc).isoformat(timespec='seconds'))
    try:
        if not co_the(goc):
            raise RuntimeError('máy này không có công cụ đo lại hoặc số đo gốc')
        co = getattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', 0) | getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        r = chay_lenh([sys.executable, '-X', 'utf8', str(goc / CONG_CU)], cwd=str(goc), capture_output=True, text=True, encoding='utf-8',
                      errors='replace', timeout=HAN_GIAY, creationflags=co)
        try:
            (goc / 'out' / 'du-lieu-moi.log').write_text((r.stdout or '') + '\n' + (r.stderr or ''), encoding='utf-8')
        except OSError:
            pass
        if r.returncode != 0:
            dong = [x for x in (r.stderr or r.stdout or '').strip().splitlines() if x.strip()]
            raise RuntimeError(f'công cụ dừng với mã {r.returncode}: {dong[-1][:200] if dong else "không rõ"}')
        TT['xong'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
        return {'ok': True, 'loi': None}
    except subprocess.TimeoutExpired:
        TT['loi'] = f'quá {HAN_GIAY // 60} phút chưa xong'
        return {'ok': False, 'loi': TT['loi']}
    except Exception as e:                                                       # noqa: BLE001
        TT['loi'] = f'{e}'
        return {'ok': False, 'loi': TT['loi']}
    finally:
        TT['dang'] = False
        _khoa.release()


def chay_nen(goc: Path = HERE) -> bool:
    """Bắt đầu đo ở nền (nút "Đo lại ngay"). False nếu đang đo hoặc máy không đo được."""
    if TT['dang'] or not co_the(goc):
        return False
    threading.Thread(target=chay, args=(goc,), daemon=True, name='do-lai-ngay').start()
    return True


def tom_tat(goc: Path = HERE, ten_ma: dict | None = None) -> dict:
    """Cho trang Biểu đồ: các mục đã đo (kèm mã phương pháp khi khớp tên), mốc dữ liệu, trạng thái chạy."""
    kq = doc(goc) or {}
    ten_ma = ten_ma or {}
    muc = []
    for x in kq.get('muc') or []:
        ma = ten_ma.get(x.get('ten')) if str(x.get('nhom', '')).startswith('Công thức phiếu') else ('bot' if str(x.get('ten', '')).startswith('Luật bot · bản hiện tại') else None)
        muc.append({**x, 'ma': ma, 'ket_ten': TEN_KET.get(x.get('ket'), x.get('ket'))})
    return {'co_the': co_the(goc), 'luc': kq.get('luc'), 'tu': kq.get('tu'), 'den': kq.get('den'), 'so_ngay': kq.get('so_ngay'), 'muc': muc,
            'dang': TT['dang'], 'loi': TT['loi']}


class VongDoLai(threading.Thread):
    """Vòng nền: năm phút sau khi webapp mở, rồi mỗi giờ, đo lại nếu đã sang tháng mới so với lần đo gần nhất."""

    def __init__(self, goc: Path = HERE, dau: float = 300, cach: float = 3600):
        super().__init__(daemon=True, name='do-lai')
        self.goc, self.dau, self.cach = goc, dau, cach

    def run(self) -> None:
        time.sleep(self.dau)
        while True:
            try:
                if co_the(self.goc) and den_han(doc(self.goc), datetime.now(timezone.utc)):
                    chay(self.goc)
            except Exception:                                                    # noqa: BLE001 - vòng nền không được chết
                pass
            time.sleep(self.cach)
