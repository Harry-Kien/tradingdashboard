# -*- coding: utf-8 -*-
"""Kiểm tra toàn bộ hệ thống bằng một lệnh: trả lời "hệ thống còn chuẩn không?" bằng kết quả đo được, không bằng cảm giác.

Chạy lần lượt và báo ĐẠT / KHÔNG ĐẠT cho từng mục:
1. Bài kiểm tra tự động (tests/).
2. Tín hiệu trang sống thấy có trùng với phép chạy lại không (cong-cu/kiem_song_chay_lai.py).
3. Phép chấm tám phương pháp so với Backtesting.py (cong-cu/doi_chieu_backtesting.py, từ 2025).
4. Bộ chấm luật ba khung so với Backtesting.py (cong-cu/doi_chieu_ba_khung.py, từ 2015).
5. Bộ chấm luật bot so với Backtesting.py (cong-cu/doi_chieu_bot.py, từ 2015).
6. Bộ chấm luật đỉnh/đáy so với Backtesting.py (cong-cu/doi_chieu_dinh_day.py, từ 2015).
7. Phần chọn nến vào lệnh của luật bot và luật đỉnh/đáy so với một bản dựng lại độc lập (cong-cu/doi_chieu_diem_vao.py, từ 2015).
8. Phần nhận diện khoảng trống giá của webapp so với thư viện smartmoneyconcepts (cong-cu/doi_chieu_fvg.py, từ 2015).
9. Công cụ đo lại trên dữ liệu mới tự đối chiếu: với mốc 01/01/2022 phải ra đúng số phần kiểm đã ghi (cong-cu/do_lai_du_lieu_moi.py --doi-chieu).
10. Phá cấu trúc (BOS, CHoCH) và quét thanh khoản của webapp so với bản dựng lại độc lập (cong-cu/doi_chieu_cau_truc.py, từ 2015).
11. Webapp đang chạy và tự kiểm của nó không báo lỗi (http://127.0.0.1:8765/api/tinh-trang); webapp tắt thì mục này báo rõ là không kiểm được.

"ĐẠT" nghĩa là phép tính và phép đo của hệ thống đúng như thiết kế. Nó KHÔNG nói gì về việc các phương pháp có lãi hay không; phần đó xem trang
Kiến thức. Nên chạy lại sau mỗi lần sửa mã của webapp, của EA Promax hoặc của bot tín hiệu. Mất khoảng 10–13 phút. Chỉ đọc; không nối MT5,
không đặt lệnh. Kết quả cũng được ghi vào out/kiem-tra-toan-bo.txt. Thoát với mã 1 nếu có mục không đạt.

    python -X utf8 cong-cu/kiem_tra_toan_bo.py        (hoặc bấm đúp KIEM_TRA_TOAN_BO.bat)
"""
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
PY = [sys.executable, '-X', 'utf8', '-W', 'ignore']
MUC = [
    ('Bài kiểm tra tự động', PY + ['-m', 'unittest', 'discover', '-s', 'tests'], 900),
    ('Tín hiệu lúc sống trùng với phép chạy lại', PY + ['cong-cu/kiem_song_chay_lai.py'], 1800),
    ('Phép chấm tám phương pháp so với Backtesting.py (từ 2025)', PY + ['cong-cu/doi_chieu_backtesting.py', '2025'], 1800),
    ('Bộ chấm luật ba khung so với Backtesting.py (từ 2015)', PY + ['cong-cu/doi_chieu_ba_khung.py', '2015'], 1800),
    ('Bộ chấm luật bot so với Backtesting.py (từ 2015)', PY + ['cong-cu/doi_chieu_bot.py', '2015'], 1800),
    ('Bộ chấm luật đỉnh/đáy so với Backtesting.py (từ 2015)', PY + ['cong-cu/doi_chieu_dinh_day.py', '2015'], 1800),
    ('Chọn nến vào lệnh của luật bot và luật đỉnh/đáy so với bản dựng lại độc lập (từ 2015)', PY + ['cong-cu/doi_chieu_diem_vao.py', '2015'], 1800),
    ('Khoảng trống giá của webapp so với thư viện smartmoneyconcepts (từ 2015)', PY + ['cong-cu/doi_chieu_fvg.py', '2015'], 900),
    ('Công cụ đo lại trên dữ liệu mới ra đúng số phần kiểm đã ghi (mốc 01/01/2022)', PY + ['cong-cu/do_lai_du_lieu_moi.py', '--doi-chieu'], 900),
    ('Phá cấu trúc và quét thanh khoản so với bản dựng lại độc lập (từ 2015)', PY + ['cong-cu/doi_chieu_cau_truc.py', '2015'], 900),
]


def chay(lenh: list, han: int) -> tuple[bool, str]:
    """(đạt?, dòng tóm tắt). Đạt khi tiến trình thoát với mã 0."""
    try:
        r = subprocess.run(lenh, cwd=GOC, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=han)
    except subprocess.TimeoutExpired:
        return False, f'quá {han // 60} phút chưa xong'
    dong = [x.strip() for x in (r.stdout + '\n' + r.stderr).splitlines() if x.strip() and 'bar/s' not in x]
    chon = [x for x in dong if x.startswith(('Ran ', 'OK', 'FAILED', 'Khác chưa giải thích', 'Lệnh so được', 'Cùng nến vào', 'TỔNG:', 'TỔNG LỆNH'))]
    return r.returncode == 0, ' · '.join((chon or dong[-2:])[-3:])[:260]


def webapp() -> tuple[bool | None, str]:
    try:
        with urllib.request.urlopen('http://127.0.0.1:8765/api/tinh-trang', timeout=20) as r:
            muc = json.loads(r.read().decode('utf-8'))['muc']
    except Exception as e:                                             # noqa: BLE001 - webapp tắt không phải là lỗi của phép kiểm
        return None, f'không hỏi được webapp ({type(e).__name__}); mở webapp rồi chạy lại nếu muốn kiểm mục này'
    dem = {k: sum(x['muc'] == k for x in muc) for k in ('tot', 'chu_y', 'loi')}
    khac = [x['ten'] for x in muc if x['muc'] not in ('tot', 'chu_y')]
    return not khac, f'{dem["tot"]} mục tốt, {dem["chu_y"]} cần chú ý, {len(khac)} lỗi' + (': ' + '; '.join(khac) if khac else '')


if __name__ == '__main__':
    out = [f'KIỂM TRA TOÀN BỘ · bắt đầu {datetime.now():%H:%M ngày %d/%m/%Y}', '']
    print(out[0], flush=True)
    hong = 0
    for so, (ten, lenh, han) in enumerate(MUC, 1):
        t0 = time.time()
        print(f'{so}. {ten} … ', end='', flush=True)
        dat, tom = chay(lenh, han)
        hong += not dat
        d = f'{so}. {"ĐẠT      " if dat else "KHÔNG ĐẠT"} · {ten} ({time.time() - t0:.0f} giây)\n      {tom}'
        print('ĐẠT' if dat else 'KHÔNG ĐẠT', flush=True)
        out.append(d)
    dat, tom = webapp()
    hong += dat is False
    out.append(f'{len(MUC) + 1}. {"ĐẠT      " if dat else "CHƯA KIỂM" if dat is None else "KHÔNG ĐẠT"} · Webapp đang chạy và tự kiểm không báo lỗi\n      {tom}')
    out += ['', ('KẾT QUẢ: mọi mục đều đạt. Phép tính và phép đo của hệ thống đúng như thiết kế.' if not hong else f'KẾT QUẢ: {hong} mục KHÔNG ĐẠT. Xem dòng tương ứng ở trên.'),
            'Lưu ý: "đạt" không có nghĩa các phương pháp có lãi. Số đo lãi lỗ và các kiểm định thống kê nằm ở trang Kiến thức của webapp.']
    van = '\n'.join(out)
    print('\n' + van)
    try:
        (GOC / 'out').mkdir(exist_ok=True)
        (GOC / 'out' / 'kiem-tra-toan-bo.txt').write_text(van + '\n', encoding='utf-8')
    except OSError:
        pass
    sys.exit(1 if hong else 0)
