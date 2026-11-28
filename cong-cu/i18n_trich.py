"""Trích mọi đoạn tiếng Việt mà webapp đang hiển thị (trang HTML, chuỗi trong mã JS, dữ liệu /api), so với từ điển dịch, và ghi các đoạn còn thiếu.

    python -X utf8 cong-cu/i18n_trich.py [--goc http://127.0.0.1:8765] [--lang en]

Webapp phải đang chạy (để có dữ liệu thật của MT5, lịch, tin…). Đọc ở chế độ tiếng Việt, chạy đúng bộ dịch của so_cong_khai/dich.py với từ điển hiện có,
rồi ghi `so_cong_khai/dich/thieu_<lang>.json`: danh sách khóa chưa có bản dịch (số đã thay bằng {0}, {1}…), xếp theo trang xuất hiện đầu tiên.
Chỉ đọc webapp; không sửa từ điển."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import dich  # noqa: E402

TRANG = ['/', '/thi-truong', '/tin-tuc', '/bieu-do', '/bieu-do?ma=EURUSDp', '/cong-cu', '/nhat-ky', '/tai-khoan', '/hoc-giao-dich', '/kien-thuc', '/hieu-suat', '/cai-dat', '/cac-tai-khoan', '/kiem-lenh', '/ke-hoach', '/ky-luat', '/sao-luu', '/telegram', '/bat-dau', '/da-khung', '/kiem-tin-hieu']
API = ['/api/thi-truong', '/api/thi-truong/ma', '/api/thi-truong/ky-thuat?ma=EURUSDp', '/api/thi-truong/bien-dong?ma=XAUUSDp', '/api/tin-tuc', '/api/tam-ly',
       '/api/phan-tich', '/api/phan-tich?ma=EURUSDp', '/api/gia?tf=M15&n=60', '/api/gia?tf=M15&n=60&ma=EURUSDp', '/api/tai-khoan', '/api/nhat-ky',
       '/api/tinh-trang', '/api/canh-bao', '/api/ma', '/api/cot', '/api/kiem-chung', '/api/hoc', '/api/hoc?ma=BTCUSDTp', '/api/ai', '/api/gia-su', '/api/hieu-suat?ngay=0', '/api/hieu-suat?ngay=0&mau=1', '/api/cai-dat', '/api/cac-tai-khoan', '/api/sao-luu', '/api/telegram', '/api/kiem-lenh?ma=XAUUSDp&chieu=MUA&vao=3500&sl=3490&tp=3520&rui_ro=1', '/api/ky-luat?ngay=90', '/api/ke-hoach?ma=XAUUSDp&chieu=MUA']


def lay(url: str) -> tuple[bytes, str]:
    rq = urllib.request.Request(url, headers={'Cookie': 'lang=vi'})
    with urllib.request.urlopen(rq, timeout=180) as r:
        return r.read(), r.headers.get('Content-Type', '')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--goc', default='http://127.0.0.1:8765')
    ap.add_argument('--lang', default='en')
    a = ap.parse_args(argv)
    d = dict(dich.tu_dien(a.lang))
    theo_trang: dict = {}
    tong = set()
    for p in TRANG + API:
        try:
            body, loai = lay(a.goc + p)
        except Exception as e:                                               # noqa: BLE001
            print(f'  bỏ qua {p}: {e}')
            continue
        thu: set = set()
        dich.dich_phan_hoi(body, loai, a.lang if d else 'en', thu) if d else _thu_rong(body, loai, thu)
        moi = sorted(thu - tong)
        tong |= thu
        theo_trang[p] = moi
        print(f'{p:45s} {len(thu):5d} đoạn thiếu, {len(moi):5d} mới')
    ra = dich.THU_MUC / f'thieu_{a.lang}.json'
    ra.parent.mkdir(parents=True, exist_ok=True)
    ra.write_text(json.dumps(theo_trang, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'Tổng {len(tong)} đoạn chưa dịch → {ra}')
    return 0


def _thu_rong(body: bytes, loai: str, thu: set) -> None:
    """Chưa có từ điển: chạy bộ dịch với từ điển rỗng chỉ để thu khóa."""
    d = {'__rong__': '-'}
    if loai.startswith('text/html'):
        dich.dich_html(body.decode('utf-8'), d, thu)
    elif loai.startswith('application/json'):
        dich.dich_json(json.loads(body.decode('utf-8')), d, thu)


if __name__ == '__main__':
    raise SystemExit(main())
