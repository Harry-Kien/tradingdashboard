"""Webapp chạy trên máy: python -m so_cong_khai.web [--port 8765]

Mỗi lần mở hoặc tải lại trang, máy chủ đọc lại các sổ (chỉ đọc) và dựng trang mới, nên số liệu luôn là số hiện tại.
Chỉ nghe ở 127.0.0.1: máy khác trong mạng không vào được. Không đặt lệnh, không gửi dữ liệu nào của bạn ra ngoài.
Tự gọi ra mạng ở đúng hai chỗ, đều chỉ tải về và chỉ khi cấu hình bật: tệp COT công khai của cftc.gov (cot.py) và tệp lịch tin kinh tế
tuần này của ForexFactory (lich_mang.py). Trang Tin tức & tâm lý còn tải tiêu đề RSS (tin_tuc.py), báo cáo COT của CFTC và chỉ số
sợ hãi/tham lam của alternative.me (tam_ly.py); cũng chỉ tải về."""
from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import ai_hoi, bieu_do, canh_bao, cot, da_ma, gia, hoc, hoc_ma, kiem_chung, kien_thuc, nen_cu, nhat_ky, nhat_ky_trang, phan_tich, song, suc_khoe, tai_khoan, thuong_hieu
from . import cong_cu, dich, hoc_giao_dich, lich_mang, tam_ly, thi_truong, thi_truong_trang, tin_tuc, tin_tuc_trang, trang
from . import cai_dat, hieu_suat, hieu_suat_trang, kiem_lenh, kiem_lenh_trang, ky_luat, ky_luat_trang, nhieu_tai_khoan, tin_phan_ung
from .__main__ import HERE, xay

LOAI = {'.png': 'image/png', '.txt': 'text/plain; charset=utf-8', '.json': 'application/json; charset=utf-8'}


def _out(cfg: dict) -> Path:
    base = Path(cfg.get('thu_muc_ra', 'out'))
    return base if base.is_absolute() else HERE / base


def tao_vong_canh(cau_hinh: str):
    """Vòng canh cảnh báo theo cấu hình; None nếu mục canh_bao.bat là false."""
    cb = json.loads(Path(cau_hinh).read_text(encoding='utf-8')).get('canh_bao') or {}
    if not cb.get('bat', True):
        return None
    return canh_bao.VongCanh(lambda: json.loads(Path(cau_hinh).read_text(encoding='utf-8')), _out, cb.get('giay', 15))


def tao_may_chu(cau_hinh: str, host: str = '127.0.0.1', port: int = 8765, vong=None, bang=None, ghi_thieu: bool = False) -> ThreadingHTTPServer:
    """`ghi_thieu`: ghi các đoạn chưa dịch gặp lúc chạy vào so_cong_khai/dich/ (chỉ máy chủ thật bật; bài kiểm không ghi)."""
    """`bang`: bảng giá trực tiếp (thi_truong.BangGia) cho trang Thị trường, Công cụ và luồng /api/thi-truong/luong; None thì các trang đó báo đang tắt."""
    TAT = {'san_sang': False, 'ly_do': 'phần Thị trường đang tắt trong cấu hình (thi_truong.bat)', 'ds': [], 'lop': thi_truong.LOP,
           'tien_te': thi_truong.TIEN_TE, 'tai_khoan': {}, 'tuong_quan': None}

    class H(BaseHTTPRequestHandler):
        def _luong_bang(self) -> None:
            """Luồng Server-Sent Events của bảng giá mọi mã (trang Thị trường, Công cụ): giữ kết nối mở và ghi mỗi khi có tick mới."""
            if bang is None:
                return self._gui(503, 'text/plain; charset=utf-8', TAT['ly_do'].encode('utf-8'))
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self._tieu_de_bao_ve()
            self.end_headers()

            def gui(b: bytes) -> None:
                self.wfile.write(b)
                self.wfile.flush()
            try:
                bang.luong(gui)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                pass                                                # trình duyệt đã đóng trang


        def _gui(self, ma: int, loai: str, body: bytes, nho: int = 0) -> None:
            q = urlparse(self.path).query
            lang = dich.ngon_ngu(self.headers.get('Cookie'), q)
            if lang != 'vi' and not nho and (loai.startswith('text/html') or loai.startswith('application/json')):   # song ngữ: dịch ngay trước khi gửi
                body = dich.dich_phan_hoi(body, loai, lang, dich.THIEU)
                if ghi_thieu:
                    dich.ghi_thieu(lang)
            self.send_response(ma)
            self.send_header('Content-Type', loai)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', f'public, max-age={nho}, immutable' if nho else 'no-store')       # chỉ tệp tĩnh không đổi mới được trình duyệt nhớ
            self.send_header('X-Content-Type-Options', 'nosniff')
            self._tieu_de_bao_ve()
            if 'lang=' in q:                                                 # ?lang=en / ?lang=vi: nhớ lựa chọn cho các lần sau
                self.send_header('Set-Cookie', f'lang={lang}; Path=/; Max-Age=31536000; SameSite=Lax')
            self.end_headers()
            self.wfile.write(body)

        def _day_tick(self, g: dict, tf: str, ma: str | None) -> None:
            """Luồng đẩy giá (Server-Sent Events): hỏi MT5 mỗi 25 ms và đẩy ngay khi có tick mới, để nến đang chạy trên trang đi cùng nhịp với MT5.
            Mỗi luồng tự đóng sau 10 phút; trình duyệt tự nối lại sau 1 giây, nên không còn luồng nào treo khi tab đã đóng."""
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self._tieu_de_bao_ve()
            self.end_headers()
            try:
                self.wfile.write(b'retry: 1000\n\n')
                cu, lan, het = None, time.monotonic(), time.monotonic() + 600
                while time.monotonic() < het:
                    x = song.tick(g, tf, ma)
                    now = time.monotonic()
                    if x is not None and (x['ms'], x['bid'], x['ask'], x.get('nen')) != cu:
                        cu = (x['ms'], x['bid'], x['ask'], x.get('nen'))
                        self.wfile.write(b'data: ' + json.dumps(x, separators=(',', ':')).encode('utf-8') + b'\n\n')
                        lan = now
                    elif now - lan > 15:                                  # dòng giữ nối khi chợ đứng, để biết sớm tab đã đóng
                        self.wfile.write(b': giu\n\n')
                        lan = now
                    time.sleep(0.025 if x is not None else 1.0)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass                                                      # tab đã đóng hoặc đổi khung: thôi đẩy

        def do_GET(self):  # noqa: N802 - tên do http.server quy định
            if not self._host_ok():                                        # DNS rebinding: trang lạ không được đọc số liệu
                return self._gui(403, 'text/plain; charset=utf-8', 'Chỉ mở được webapp bằng địa chỉ 127.0.0.1 hoặc localhost.'.encode('utf-8'))
            url = urlparse(self.path)
            path = unquote(url.path)
            try:                                                           # bản chia sẻ chưa khai sổ riêng: câu miễn trừ và trang Kiến thức chung
                c0 = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                cs = gia.ban_chia_se(c0.get('gia') or {}) and not c0.get('tai_khoan') and not c0.get('bot_db')
            except (OSError, ValueError):
                cs = False
            trang.chia_se_luot(cs)                                         # chỉ cho luồng của lượt này, không lây sang lượt khác
            try:
                if path == '/api/thi-truong/luong':
                    return self._luong_bang()
                if path in ('/thi-truong', '/cong-cu', '/hoc-giao-dich'):
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    f = {'/thi-truong': thi_truong_trang.trang_thi_truong, '/cong-cu': cong_cu.trang_cong_cu, '/hoc-giao-dich': hoc_giao_dich.trang_hoc}[path]
                    return self._gui(200, 'text/html; charset=utf-8', f(thuong_hieu.TEN).encode('utf-8'))
                if path == '/api/thi-truong':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    body = bang.anh_chup() if bang is not None else dict(TAT)
                    try:
                        body['lich'] = thi_truong.lich_tong(cfg, HERE)
                    except Exception as e:                                 # noqa: BLE001 - lịch hỏng không làm hỏng bảng giá
                        body['lich'] = {'co': False, 'ly_do': f'{type(e).__name__}: {e}', 'ds': []}
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False).encode('utf-8'))
                if path == '/hieu-suat':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, 'text/html; charset=utf-8', hieu_suat_trang.trang_hieu_suat(thuong_hieu.TEN).encode('utf-8'))
                if path in ('/api/hieu-suat', '/api/hieu-suat.csv'):                # phân tích hiệu suất từ lịch sử lệnh MT5 (chỉ đọc)
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    q = parse_qs(url.query)
                    lay_q = lambda k, md='': (q.get(k, [md])[0] or md).strip()[:40]   # noqa: E731
                    try:
                        ngay = max(0, min(int(lay_q('ngay', '90')), 3650))
                    except ValueError:
                        return self._gui(400, 'text/plain; charset=utf-8', 'Yêu cầu không hợp lệ: ngay'.encode('utf-8'))
                    body = hieu_suat.lay(cfg, ngay, lay_q('ma'), lay_q('chieu'), lay_q('nguon'), lay_q('mau') == '1')
                    if path.endswith('.csv'):
                        csv_b = hieu_suat.csv_lenh(body.get('lenh', [])[::-1]).encode('utf-8')
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/csv; charset=utf-8')
                        self.send_header('Content-Disposition', 'attachment; filename="lich-su-lenh.csv"')
                        self.send_header('Content-Length', str(len(csv_b)))
                        self.send_header('Cache-Control', 'no-store')
                        self.send_header('X-Content-Type-Options', 'nosniff')
                        self._tieu_de_bao_ve()
                        self.end_headers()
                        self.wfile.write(csv_b)
                        return None
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False, default=str).encode('utf-8'))
                if path == '/tin-tuc':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, 'text/html; charset=utf-8', tin_tuc_trang.trang_tin_tuc(thuong_hieu.TEN).encode('utf-8'))
                if path == '/api/tin-tuc':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    q = parse_qs(url.query)
                    body = tin_tuc.lay(cfg, HERE, (q.get('nhan', [''])[0] or '').strip()[:10], (q.get('q', [''])[0] or '').strip()[:80])
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False).encode('utf-8'))
                if path == '/api/tam-ly':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(tam_ly.lay(cfg, HERE), ensure_ascii=False).encode('utf-8'))
                if path == '/api/thi-truong/ma':                          # danh sách gọn cho ô tìm nhanh (Ctrl+K) ở mọi trang
                    ds = [{k: x.get(k) for k in ('ma', 'goc', 'ten', 'biet_danh', 'lop')} for x in (bang.anh_chup()['ds'] if bang is not None else [])]
                    return self._gui(200, LOAI['.json'], json.dumps({'ds': ds, 'lop': thi_truong.LOP}, ensure_ascii=False).encode('utf-8'))
                if path in ('/api/thi-truong/ky-thuat', '/api/thi-truong/bien-dong'):
                    ma = (parse_qs(url.query).get('ma', [''])[0] or '').strip()
                    try:
                        if bang is None:
                            raise ValueError(TAT['ly_do'])
                        body = bang.chi_tiet_ky_thuat(ma) if path.endswith('ky-thuat') else bang.bien_dong(ma)
                    except ValueError as e:
                        return self._gui(400, 'text/plain; charset=utf-8', f'Yêu cầu không hợp lệ: {e}'.encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False).encode('utf-8'))
                if path == '/kiem-lenh':
                    return self._gui(200, 'text/html; charset=utf-8', kiem_lenh_trang.trang_kiem_lenh(thuong_hieu.TEN).encode('utf-8'))
                if path == '/api/kiem-lenh':                                # kiểm tra trước khi vào lệnh: chỉ đọc MT5, không đặt lệnh
                    q = parse_qs(url.query)
                    lay = lambda k: (q.get(k, [''])[0] or '').strip().replace(',', '.')   # noqa: E731
                    try:
                        chieu = lay('chieu').upper()
                        if chieu not in ('MUA', 'BAN') or not lay('ma'):
                            raise ValueError('cần ma và chieu=MUA|BAN')
                        so = lambda k: float(lay(k)) if lay(k) else None    # noqa: E731
                        lenh = {'ma': lay('ma'), 'chieu': chieu, 'vao': float(lay('vao')), 'sl': so('sl'), 'tp': so('tp'), 'rui_ro_pct': so('rui_ro')}
                        if lenh['rui_ro_pct'] is not None and not 0 < lenh['rui_ro_pct'] <= 100:
                            raise ValueError('rui_ro phải trong (0, 100]')
                        cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                        qt = {k[2:]: v for k in ('q_rui_ro_lenh_toi_da_pct', 'q_lo_ngay_toi_da_pct', 'q_tong_rui_ro_toi_da_pct')
                              if (v := so(k)) is not None and 0 < v <= 100}
                        if qt:
                            cfg['kiem_lenh'] = {**(cfg.get('kiem_lenh') or {}), **qt}
                        body = kiem_lenh.kiem(cfg, bang, lenh)
                    except ValueError as e:
                        return self._gui(400, 'text/plain; charset=utf-8', f'Yêu cầu không hợp lệ: {e}'.encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False, default=str).encode('utf-8'))
                if path == '/ky-luat':
                    return self._gui(200, 'text/html; charset=utf-8', ky_luat_trang.trang_ky_luat(thuong_hieu.TEN).encode('utf-8'))
                if path == '/api/ky-luat':                                  # chấm lại lệnh đã đóng theo quy tắc rủi ro: chỉ đọc MT5
                    q = parse_qs(url.query)
                    lay = lambda k: (q.get(k, [''])[0] or '').strip().replace(',', '.')   # noqa: E731
                    try:
                        ngay = int(lay('ngay') or 30)
                        if not 1 <= ngay <= 365:
                            raise ValueError('ngay phải từ 1 tới 365')
                        nguon = (q.get('nguon', [''])[0] or '').strip()[:80] or None
                        qt = {}
                        for k, lo, hi in (('q_rui_ro_lenh_toi_da_pct', 0, 100), ('q_lo_ngay_toi_da_pct', 0, 100), ('q_so_lenh_ngay_toi_da', -1, 1000)):
                            if lay(k):
                                v = float(lay(k))
                                if lo < v <= hi:
                                    qt[k[2:]] = v
                        cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                        body = ky_luat.doc(cfg, ngay=ngay, nguon=nguon, quy_tac=qt)
                    except ValueError as e:
                        return self._gui(400, 'text/plain; charset=utf-8', f'Yêu cầu không hợp lệ: {e}'.encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False, default=str).encode('utf-8'))
                if path == '/api/tinh':
                    q = parse_qs(url.query)
                    try:
                        if bang is None:
                            raise ValueError(TAT['ly_do'])
                        lay = lambda k: (q.get(k, [''])[0] or '').strip()   # noqa: E731
                        body = bang.tinh(lay('ma'), lay('loai'), float(lay('lot')), float(lay('vao')), float(lay('ra')) if lay('ra') else None)
                    except ValueError as e:
                        return self._gui(400, 'text/plain; charset=utf-8', f'Yêu cầu không hợp lệ: {e}'.encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False).encode('utf-8'))
                if path == '/kien-thuc':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, 'text/html; charset=utf-8', kien_thuc.trang_kien_thuc(thuong_hieu.TEN, cs).encode('utf-8'))
                if path == '/nhat-ky':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, 'text/html; charset=utf-8', nhat_ky_trang.trang_nhat_ky(thuong_hieu.TEN).encode('utf-8'))
                if path == '/cai-dat':                                     # chỉnh cấu hình ngay trên web
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, 'text/html; charset=utf-8', cai_dat.trang_cai_dat(thuong_hieu.TEN).encode('utf-8'))
                if path == '/api/cai-dat':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(cai_dat.doc(cfg), ensure_ascii=False, default=str).encode('utf-8'))
                if path == '/api/tin-toi':                                 # tin USD mạnh sắp ra kèm số đo phản ứng của giá vàng
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(tin_phan_ung.tin_toi(cfg), ensure_ascii=False).encode('utf-8'))
                if path == '/cac-tai-khoan':                               # mọi tài khoản MT5 đã nối, demo và tiền thật (chỉ đọc)
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, 'text/html; charset=utf-8', nhieu_tai_khoan.trang_cac_tai_khoan(thuong_hieu.TEN).encode('utf-8'))
                if path == '/api/cac-tai-khoan':
                    return self._gui(200, LOAI['.json'], json.dumps(nhieu_tai_khoan.xem(), ensure_ascii=False, default=str).encode('utf-8'))
                if path == '/tai-khoan':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, 'text/html; charset=utf-8', tai_khoan.trang_tai_khoan(thuong_hieu.TEN).encode('utf-8'))
                if path == '/api/tai-khoan':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(tai_khoan.doc(cfg), ensure_ascii=False).encode('utf-8'))
                if path.startswith('/tinh/phong/'):                          # phông chữ, phục vụ từ máy; chỉ nhận đúng các tên tệp đã biết
                    ten = path.rsplit('/', 1)[1]
                    f = HERE / 'tinh' / 'phong' / ten
                    if re.fullmatch(r'be-vietnam-pro-(400|500|600|700)-(vietnamese|latin-ext|latin)\.woff2', ten) and f.is_file():
                        return self._gui(200, 'font/woff2', f.read_bytes(), nho=30 * 86400)
                    return self._gui(404, 'text/plain; charset=utf-8', 'Không có tệp phông này.'.encode('utf-8'))
                if path == '/tinh/lightweight-charts.js':                    # thư viện biểu đồ, phục vụ từ máy (không gọi ra mạng lúc chạy)
                    f = HERE / 'tinh' / 'lightweight-charts-5.3.0' / 'lightweight-charts.standalone.production.js'
                    if f.is_file():
                        return self._gui(200, 'text/javascript; charset=utf-8', f.read_bytes())
                    return self._gui(404, 'text/plain; charset=utf-8', 'Chưa có tệp thư viện biểu đồ; trang dùng lớp vẽ dự phòng.'.encode('utf-8'))
                if path == '/bieu-do':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, 'text/html; charset=utf-8', bieu_do.trang_bieu_do(thuong_hieu.TEN).encode('utf-8'))
                if path == '/api/gia':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    q = parse_qs(url.query)
                    try:
                        ma = (q.get('ma', [''])[0] or '').strip()
                        if ma and ma != da_ma.ma_vang(cfg):
                            data = da_ma.goi(cfg, ma, q.get('tf', ['M15'])[0], int(q.get('n', ['600'])[0]))
                        else:
                            data = gia.goi(cfg, q.get('tf', ['M15'])[0], int(q.get('n', ['600'])[0]))
                    except gia.ChuaCoGia as e:
                        return self._gui(503, 'text/plain; charset=utf-8', f'Chưa có giá trực tiếp: {e}'.encode('utf-8'))
                    except (ValueError, KeyError) as e:
                        return self._gui(400, 'text/plain; charset=utf-8', f'Yêu cầu không hợp lệ: {e}'.encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(data, ensure_ascii=False).encode('utf-8'))
                if path == '/api/song':                                     # luồng đẩy tick và nến đang chạy, theo từng tick của MT5
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    q = parse_qs(url.query)
                    tf = q.get('tf', ['M15'])[0]
                    if tf not in song.SO_NEN:
                        return self._gui(400, 'text/plain; charset=utf-8', f'Yêu cầu không hợp lệ: khung {tf}'.encode('utf-8'))
                    ma = (q.get('ma', [''])[0] or '').strip()
                    return self._day_tick(cfg.get('gia') or {}, tf, None if not ma or ma == da_ma.ma_vang(cfg) else ma)
                if path == '/api/gia-cu':                                   # nến lùi về đầu năm, nạp một lần cho mỗi mã và khung
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    q = parse_qs(url.query)
                    try:
                        data = nen_cu.goi(cfg, (q.get('ma', [''])[0] or '').strip(), q.get('tf', ['M15'])[0])
                    except (ValueError, KeyError, RuntimeError, FileNotFoundError) as e:
                        return self._gui(400, 'text/plain; charset=utf-8', f'Không nạp được nến cũ: {e}'.encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(data, ensure_ascii=False).encode('utf-8'))
                if path == '/api/phan-tich':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    ma = (parse_qs(url.query).get('ma', [''])[0] or '').strip()
                    try:
                        data = da_ma.phan_tich(cfg, ma) if ma and ma != da_ma.ma_vang(cfg) else phan_tich.phan_tich(cfg)
                        try:                                                   # ghi điểm vào còn hiệu lực vào nhật ký (nếu cấu hình bật)
                            nhat_ky.ghi(cfg, data)
                        except Exception:                                      # noqa: BLE001 - nhật ký hỏng không được làm hỏng phần phân tích
                            pass
                    except gia.ChuaCoGia as e:
                        return self._gui(503, 'text/plain; charset=utf-8', f'Chưa có giá trực tiếp: {e}'.encode('utf-8'))
                    except ValueError as e:
                        return self._gui(400, 'text/plain; charset=utf-8', f'Yêu cầu không hợp lệ: {e}'.encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(data, ensure_ascii=False).encode('utf-8'))
                if path == '/api/nhat-ky':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(nhat_ky.xem(cfg), ensure_ascii=False).encode('utf-8'))
                if path == '/api/cot':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(cot.lay(cfg), ensure_ascii=False).encode('utf-8'))
                if path == '/api/ma':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(da_ma.danh_sach(cfg), ensure_ascii=False).encode('utf-8'))
                if path == '/api/kiem-chung':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(kiem_chung.lay(cfg, _out(cfg)), ensure_ascii=False).encode('utf-8'))
                if path == '/api/hoc':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    ma = (parse_qs(url.query).get('ma', [''])[0] or '').strip()
                    body = hoc_ma.lay(cfg, _out(cfg), ma) if ma and ma != da_ma.ma_vang(cfg) else hoc.lay(cfg, _out(cfg))
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False).encode('utf-8'))
                if path == '/api/tinh-trang':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    tt = vong.trang_thai() if vong is not None else {'dang_chay': False, 'ly_do': 'Cảnh báo đang tắt trong cấu hình.'}
                    body = suc_khoe.kiem(cfg, _out(cfg), vong=tt)
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False).encode('utf-8'))
                if path == '/api/canh-bao':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    tt = vong.trang_thai() if vong is not None else {'dang_chay': False, 'ly_do': 'Cảnh báo đang tắt trong cấu hình.'}
                    body = {'ds': canh_bao.doc(_out(cfg), 30), **tt}
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False).encode('utf-8'))
                if path == '/api/ai':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    st = ai_hoi.trang_thai(cfg, _out(cfg))
                    return self._gui(200, LOAI['.json'], json.dumps(st, ensure_ascii=False, default=str).encode('utf-8'))
                if path in ('/', '/index.html'):                               # bản chia sẻ chưa khai sổ riêng nào: trang tổng quan là Thị trường
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    if gia.ban_chia_se(cfg.get('gia') or {}) and not cfg.get('tai_khoan') and not cfg.get('bot_db'):
                        self.send_response(302)
                        self.send_header('Location', '/thi-truong')
                        self.send_header('Content-Length', '0')
                        self.send_header('X-Content-Type-Options', 'nosniff')
                        self._tieu_de_bao_ve()
                        self.end_headers()
                        return
                if path in ('/', '/index.html', '/api/so.json'):
                    r = xay(json.loads(Path(cau_hinh).read_text(encoding='utf-8')), live=True)
                    if path == '/api/so.json':
                        return self._gui(200, LOAI['.json'], (r['out'] / 'so-cong-khai.json').read_bytes())
                    return self._gui(200, 'text/html; charset=utf-8', r['html'].encode('utf-8'))
                if path.startswith('/threads/'):
                    name = path[len('/threads/'):]
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    base = Path(cfg.get('thu_muc_ra', 'out'))
                    f = (base if base.is_absolute() else HERE / base) / 'threads' / name
                    # chỉ tên tệp trần, đúng đuôi cho phép: không cho đi ra ngoài thư mục threads
                    if name == Path(name).name and f.suffix in ('.png', '.txt') and f.is_file():
                        return self._gui(200, LOAI[f.suffix], f.read_bytes())
                self._gui(404, 'text/plain; charset=utf-8', 'Không có trang này.'.encode('utf-8'))
            except Exception as e:                                  # noqa: BLE001 - báo lỗi ra trang thay vì làm chết máy chủ
                self._gui(500, 'text/plain; charset=utf-8', f'Lỗi khi dựng trang: {type(e).__name__}: {e}'.encode('utf-8'))

        def _tieu_de_bao_ve(self) -> None:
            """Cấm trang khác nhúng webapp vào khung (chống lừa bấm), không gửi địa chỉ trang khi bấm link ra ngoài, không cho trang khác nạp tài nguyên."""
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Content-Security-Policy', "frame-ancestors 'none'")
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Cross-Origin-Resource-Policy', 'same-origin')

        def _host_ok(self) -> bool:
            """Tiêu đề Host là chính máy này. Chặn DNS rebinding: trang lạ đổi tên miền của nó trỏ về 127.0.0.1 rồi đọc số liệu tài khoản như cùng nguồn;
            khi đó Host là tên miền lạ nên bị từ chối."""
            h = (self.headers.get('Host') or '').strip().lower()
            h = h[1:h.index(']')] if h.startswith('[') and ']' in h else h.rsplit(':', 1)[0] if h.count(':') == 1 else h
            return h in ('127.0.0.1', 'localhost', '::1')

        def _cung_may(self) -> bool:
            """Yêu cầu ghi đến từ chính trang của webapp trên máy này: có tiêu đề riêng (trang lạ không gửi được nếu không qua CORS),
            Host là máy này (chặn DNS rebinding), và Origin (nếu có) cũng là máy này."""
            may = ('127.0.0.1', 'localhost', '::1')
            goc = self.headers.get('Origin')
            return (self.headers.get('X-So-Cong-Khai') == '1' and self._host_ok()
                    and (not goc or (urlparse(goc).hostname or '').lower() in may))

        def do_POST(self):  # noqa: N802
            # Ba việc được phép qua POST: hỏi AI, thêm/bỏ/đọc lại tài khoản đã nối, và lưu cài đặt. Mọi lệnh đều phải đến từ chính trang
            # của webapp trên máy này (tiêu đề riêng, Host, Origin): trang web khác không gửi hộ được, kể cả qua DNS rebinding.
            if not self._cung_may():
                return self._gui(403, LOAI['.json'], json.dumps({'ok': False, 'thong_bao': 'Chỉ trang của webapp trên chính máy này mới được gửi lệnh.'},
                                                                ensure_ascii=False).encode('utf-8'))
            try:
                if urlparse(self.path).path == '/api/cai-dat':
                    if not self._cung_may():
                        return self._gui(403, LOAI['.json'], json.dumps({'ok': False, 'thong_bao': 'Chỉ trang Cài đặt trên chính máy này mới được lưu.'},
                                                                        ensure_ascii=False).encode('utf-8'))
                    n = min(int(self.headers.get('Content-Length') or 0), 8192)
                    yc = json.loads(self.rfile.read(n).decode('utf-8') or '{}') if n else {}
                    try:
                        if yc.get('viec') == 'noi_lai':
                            cai_dat.noi_lai(json.loads(Path(cau_hinh).read_text(encoding='utf-8')).get('gia') or {})
                            kq = {'ok': True, 'thong_bao': 'Đang nối lại MT5…'}
                        elif yc.get('viec') == 'luu':
                            kq = cai_dat.ghi(Path(cau_hinh), yc.get('gia_tri'))
                        else:
                            raise ValueError('yêu cầu không hợp lệ')
                    except ValueError as e:
                        return self._gui(400, LOAI['.json'], json.dumps({'ok': False, 'thong_bao': f'Chưa lưu: {e}'}, ensure_ascii=False).encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(kq, ensure_ascii=False).encode('utf-8'))
                if urlparse(self.path).path == '/api/cac-tai-khoan' and self.headers.get('X-So-Cong-Khai') == '1':
                    n = min(int(self.headers.get('Content-Length') or 0), 4096)
                    yc = json.loads(self.rfile.read(n).decode('utf-8') or '{}') if n else {}
                    viec = yc.get('viec')
                    if viec == 'them':
                        ok, nhan = nhieu_tai_khoan.them(str(yc.get('duong', '')), str(yc.get('ten', '')))
                        if ok:
                            nhieu_tai_khoan.doc_lai_ngay()
                    elif viec == 'xoa':
                        ok, nhan = nhieu_tai_khoan.xoa(int(yc.get('id', 0)))
                    elif viec == 'doc_lai':
                        nhieu_tai_khoan.doc_lai_ngay()
                        ok, nhan = True, 'Đang đọc lại mọi tài khoản; trang tự cập nhật sau ít giây.'
                    else:
                        ok, nhan = False, 'Yêu cầu không hợp lệ.'
                    return self._gui(200 if ok else 400, LOAI['.json'], json.dumps({'ok': ok, 'ly_do': nhan}, ensure_ascii=False).encode('utf-8'))
                if urlparse(self.path).path != '/api/ai' or self.headers.get('X-So-Cong-Khai') != '1':
                    return self._gui(404, 'text/plain; charset=utf-8', 'Không có trang này.'.encode('utf-8'))
                cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                r = ai_hoi.hoi(cfg, _out(cfg))
                self._gui(200, LOAI['.json'], json.dumps(r, ensure_ascii=False, default=str).encode('utf-8'))
            except Exception as e:                                  # noqa: BLE001
                self._gui(500, 'text/plain; charset=utf-8', f'Lỗi khi hỏi AI: {type(e).__name__}: {e}'.encode('utf-8'))

        def log_message(self, *a):                                  # im lặng: không in mỗi lượt tải trang
            pass

    return ThreadingHTTPServer((host, port), H)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='so_cong_khai.web', description=__doc__)
    ap.add_argument('--cau-hinh', default=str(HERE / 'cau-hinh.json'))
    ap.add_argument('--port', type=int, default=8765)
    a = ap.parse_args(argv)
    mau = HERE / 'cau-hinh.mau.json'
    if not Path(a.cau_hinh).exists() and mau.exists():               # lần chạy đầu của bản chia sẻ: tạo cấu hình từ bản mẫu
        Path(a.cau_hinh).write_text(mau.read_text(encoding='utf-8'), encoding='utf-8')
    vong = tao_vong_canh(a.cau_hinh)
    bang = thi_truong.bang(lambda: json.loads(Path(a.cau_hinh).read_text(encoding='utf-8')))
    srv = tao_may_chu(a.cau_hinh, port=a.port, vong=vong, bang=bang, ghi_thieu=True)
    if vong is not None:
        vong.start()
    nhieu_tai_khoan.VONG = nhieu_tai_khoan.VongTaiKhoan()                # đọc các tài khoản đã nối (mỗi cái một tiến trình riêng, chỉ đọc)
    nhieu_tai_khoan.VONG.start()
    if bang is not None:                                           # bảng giá trực tiếp cho trang Thị trường và Công cụ
        bang.start()
    nk = (json.loads(Path(a.cau_hinh).read_text(encoding='utf-8')).get('nhat_ky') or {})
    if nk.get('bat'):                                              # vòng nền ghi điểm vào, kể cả khi không ai mở trang
        nhat_ky.VongGhi(lambda: json.loads(Path(a.cau_hinh).read_text(encoding='utf-8')), nk.get('giay', 60)).start()
    if (json.loads(Path(a.cau_hinh).read_text(encoding='utf-8')).get('lich_mang') or {}).get('bat', True):   # lịch tin nhiều đồng tiền từ mạng (chỉ để hiển thị)
        lich_mang.VongLich(lambda: json.loads(Path(a.cau_hinh).read_text(encoding='utf-8')), HERE).start()
    cfg0 = json.loads(Path(a.cau_hinh).read_text(encoding='utf-8'))
    if (cfg0.get('tin_tuc') or {}).get('bat', True):                       # tin tức RSS, 5 phút một lần
        tin_tuc.VongTin(lambda: json.loads(Path(a.cau_hinh).read_text(encoding='utf-8')), HERE).start()
    if (cfg0.get('tam_ly') or {}).get('bat', True):                        # COT của CFTC và chỉ số sợ hãi/tham lam
        tam_ly.VongTamLy(lambda: json.loads(Path(a.cau_hinh).read_text(encoding='utf-8')), HERE).start()
    def lam_nong():                                                # lần phân tích đầu phải nạp mã luật và thư viện (khoảng 3 giây): làm trước, để lần bấm đầu của người dùng không phải chờ
        try:
            phan_tich.phan_tich(json.loads(Path(a.cau_hinh).read_text(encoding='utf-8')))
        except Exception:                                          # noqa: BLE001 - làm nóng hỏng thì lần bấm đầu chậm như cũ, không hơn
            pass
    threading.Thread(target=lam_nong, name='lam-nong', daemon=True).start()
    sys.stdout.reconfigure(encoding='utf-8')
    print(f'Sổ công khai đang chạy tại http://127.0.0.1:{srv.server_address[1]}  (nhấn Ctrl+C để dừng)', flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
