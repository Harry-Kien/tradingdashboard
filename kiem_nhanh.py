"""Kiểm nhanh bản chia sẻ (chạy trên GitHub Actions mỗi lần đẩy mã, chạy được cả trên máy): python -X utf8 kiem_nhanh.py

Không cần MetaTrader 5: bật webapp với cấu hình mẫu trên một cổng tạm, mở mọi trang ở hai ngôn ngữ và vài API, rồi kiểm:
- không trang nào lỗi máy chủ (5xx), các trang chính trả 200;
- tên hiển thị cố định "Harry · Gold Research" có trên mọi trang, logo có trong thanh điều hướng;
- bản tiếng Anh có <html lang="en">;
- Host lạ bị chặn (chống DNS rebinding) và có tiêu đề chống nhúng khung;
- khách chưa đăng nhập không đọc được API dữ liệu MT5 (401); các trang được mở bằng tài khoản chủ tạo trong thư mục tạm.
Thoát mã 0 khi đạt, 1 khi có lỗi."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))

TRANG = ['/', '/thi-truong', '/tin-tuc', '/bieu-do', '/cong-cu', '/hoc-giao-dich', '/kien-thuc', '/hieu-suat', '/cai-dat', '/cac-tai-khoan',
         '/nhat-ky', '/tai-khoan', '/kiem-lenh', '/ke-hoach', '/ky-luat', '/telegram', '/sao-luu', '/da-khung', '/bat-dau', '/kiem-tin-hieu']
API = ['/api/thi-truong', '/api/tin-tuc', '/api/tam-ly', '/api/hieu-suat?ngay=90&mau=1', '/api/hieu-suat.csv?ngay=90&mau=1', '/api/gia-su',
       '/api/telegram', '/api/canh-bao-ve', '/api/hinh-ve?ma=XAU', '/api/mau-chi-bao']
TEN = 'Harry · Gold Research'
PHIEN = ''                                                             # cookie phiên của tài khoản chủ tạm


def goi(u: str, host: str | None = None, lang: str = 'vi', khach: bool = False) -> tuple[int, str, dict]:
    ck = f'lang={lang}' + ('' if khach or not PHIEN else '; ' + PHIEN)
    rq = urllib.request.Request(u, headers={'Cookie': ck, **({'Host': host} if host else {})})  # noqa: S310 - chỉ gọi webapp tạm trên 127.0.0.1
    try:
        with urllib.request.urlopen(rq, timeout=60) as r:  # noqa: S310 - chỉ gọi webapp tạm trên 127.0.0.1
            return r.status, r.read().decode('utf-8', 'replace'), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace'), dict(e.headers)


def main() -> int:
    global PHIEN
    from so_cong_khai import tai_khoan_chart, thuong_hieu, trang, web    # noqa: PLC0415
    loi: list[str] = []
    if thuong_hieu.TEN != TEN:
        loi.append(f'tên hiển thị bị đổi: {thuong_hieu.TEN!r}')
    with tempfile.TemporaryDirectory() as d:
        ch = Path(d) / 'cau-hinh.json'
        shutil.copy(GOC / 'cau-hinh.mau.json', ch)
        cfg = json.loads(ch.read_text(encoding='utf-8'))
        cfg['ten'] = 'Ten Gia Mao'                                        # thử đổi tên qua cấu hình: phải không có tác dụng
        ch.write_text(json.dumps(cfg, ensure_ascii=False), encoding='utf-8')
        _, token = tai_khoan_chart.vao('kiem-nhanh-chu', 'chi-de-kiem-nhanh-12345', True, d)   # tài khoản chủ chỉ có trong thư mục tạm
        PHIEN = tai_khoan_chart.cookie_header(token).split(';')[0]
        srv = web.tao_may_chu(str(ch), port=0)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        u = f'http://127.0.0.1:{srv.server_address[1]}'
        try:
            for lang in ('vi', 'en'):
                for p in TRANG:
                    ma, body, _ = goi(u + p, lang=lang)
                    dong = f'{lang} {p:16s} {ma}'
                    if ma >= 500 or (ma != 200 and p in ('/', '/thi-truong', '/hieu-suat', '/cong-cu', '/hoc-giao-dich', '/tin-tuc')):
                        loi.append(dong)
                    elif ma == 200:
                        if TEN not in body or 'Ten Gia Mao' in body:
                            loi.append(f'{dong}: thiếu tên cố định hoặc tên bị đổi')
                        if 'nv-mk"><img' not in body:
                            loi.append(f'{dong}: thiếu logo')
                        if lang == 'en' and '<html lang="en"' not in body:
                            loi.append(f'{dong}: bản tiếng Anh không đặt lang="en"')
                    print(dong)
            for p in API:
                ma, _, _ = goi(u + p)
                print(f'   {p:34s} {ma}')
                if ma >= 500:
                    loi.append(f'{p} {ma}')
            ma, _, _ = goi(u + '/api/thi-truong', khach=True)
            if ma != 401:
                loi.append(f'khách chưa đăng nhập đọc được API dữ liệu MT5 (trả {ma})')
            ma, _, _ = goi(u + '/api/thi-truong', host='evil.example')
            if ma != 403:
                loi.append(f'Host lạ không bị chặn (trả {ma})')
            _, _, h = goi(u + '/hieu-suat')
            if h.get('X-Frame-Options') != 'DENY':
                loi.append('thiếu X-Frame-Options: DENY')
        finally:
            srv.shutdown()
            srv.server_close()
            if hasattr(trang, 'MIEN_TRU_GOC'):
                trang.MIEN_TRU = trang.MIEN_TRU_GOC
    if loi:
        print('\nLỖI:')
        for x in loi:
            print('  -', x)
        return 1
    print('\nĐẠT: mọi trang và API kiểm nhanh đều ổn.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
