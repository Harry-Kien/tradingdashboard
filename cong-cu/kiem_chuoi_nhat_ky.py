# -*- coding: utf-8 -*-
"""Kiểm chuỗi dấu băm của nhật ký điểm vào (so_cong_khai.nhat_ky): mọi điểm vào ghi từ đêm 25/11/2026 mang dấu SHA-256 nối với dòng trước, nên
sửa, xóa hay chèn một tín hiệu cũ đều làm gãy chuỗi. In trạng thái và dấu mới nhất. Muốn chứng minh với người ngoài rằng hồ sơ không bị sửa về
sau, chủ dự án có thể tự công bố dấu mới nhất ở một nơi có ghi giờ (ví dụ một bài đăng); công cụ này không gửi gì ra ngoài.

    python -X utf8 cong-cu/kiem_chuoi_nhat_ky.py
"""
import json
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import nhat_ky  # noqa: E402

if __name__ == '__main__':
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    p = nhat_ky.tep(cfg)
    kq = nhat_ky.kiem_chuoi_tep(p)
    if kq['ok']:
        print(f"TỔNG: chuỗi nguyên vẹn · {kq['so_dong']} điểm vào có dấu · {kq['chua_dau']} dòng ghi trước khi có chuỗi · dấu mới nhất {kq['bam_cuoi'] or '(chưa có)'}")
    else:
        print(f"TỔNG: CHUỖI GÃY ở dòng {kq['hong_id']} · {kq['so_dong']} dòng đầu còn nguyên · dấu cuối còn đúng {kq['bam_cuoi']}")
    sys.exit(0 if kq['ok'] else 1)
