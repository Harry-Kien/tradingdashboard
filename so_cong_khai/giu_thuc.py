"""Giữ máy không tự ngủ trong lúc webapp chạy (chủ dự án chọn ngày 26/11/2026).

Kênh Telegram, nhật ký điểm vào, đối chiếu tài khoản và sao lưu chỉ chạy khi máy thức. Đêm 26/11/2026 máy ngủ từ 00:48 tới 11:16 nên bài phân tích
8 giờ không được đăng. Mô-đun này gọi SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED) của Windows từ luồng chính của webapp: máy không tự
ngủ, màn hình vẫn tự tắt được. Tiến trình webapp kết thúc thì Windows tự bỏ yêu cầu này. Không đổi cài đặt nguồn điện của máy; gập máy hay bấm Sleep
thì máy vẫn ngủ. Bật bằng khóa "giu_may_thuc": true trong cau-hinh.json (bản mẫu để false)."""
from __future__ import annotations

import sys

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
TT: dict = {'thu': False, 'bat': False, 'loi': None}


def bat(goi=None) -> bool:
    """Gọi từ luồng sống suốt đời webapp (luồng chính, trước serve_forever). `goi`: thay hàm Windows khi kiểm thử."""
    TT['thu'] = True
    if goi is None:
        if sys.platform != 'win32':
            TT.update(bat=False, loi='chỉ làm được trên Windows')
            return False
        import ctypes                                                          # noqa: PLC0415
        goi = ctypes.windll.kernel32.SetThreadExecutionState
    try:
        kq = goi(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    except Exception as e:                                                     # noqa: BLE001
        TT.update(bat=False, loi=type(e).__name__)
        return False
    TT.update(bat=bool(kq), loi=None if kq else 'Windows không nhận yêu cầu')
    return bool(kq)


def muc_suc_khoe(cfg: dict) -> dict | None:
    """Mục cho trang Tình trạng; None khi không chạy trong webapp (chưa từng thử bật) và cấu hình không bật."""
    ten = 'Giữ máy thức'
    if not cfg.get('giu_may_thuc'):
        return {'ten': ten, 'muc': 'tot', 'chi_tiet': 'Đang tắt: máy ngủ thì kênh Telegram, nhật ký điểm vào và sao lưu dừng theo.',
                'lam': 'Muốn chạy suốt đêm thì đặt "giu_may_thuc": true trong cau-hinh.json rồi chạy lại webapp.'}
    if not TT['thu']:
        return None
    if TT['bat']:
        return {'ten': ten, 'muc': 'tot', 'chi_tiet': 'Máy không tự ngủ trong lúc webapp chạy; màn hình vẫn tự tắt. Tắt webapp thì máy ngủ lại bình thường.', 'lam': ''}
    return {'ten': ten, 'muc': 'chu_y', 'chi_tiet': f'Chưa giữ được máy thức: {TT["loi"]}.',
            'lam': 'Vào Settings → System → Power & battery, đặt máy không ngủ khi cắm sạc.'}
