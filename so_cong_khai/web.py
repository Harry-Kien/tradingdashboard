"""Webapp chạy trên máy: python -m so_cong_khai.web [--port 8769]

Mỗi lần mở hoặc tải lại trang, máy chủ đọc lại các sổ (chỉ đọc) và dựng trang mới, nên số liệu luôn là số hiện tại.
Chỉ nghe ở 127.0.0.1: máy khác trong mạng không vào được. Không đặt lệnh, không gửi dữ liệu nào của bạn ra ngoài.
Tự gọi ra mạng ở đúng hai chỗ, đều chỉ tải về và chỉ khi cấu hình bật: tệp COT công khai của cftc.gov (cot.py) và tệp lịch tin kinh tế
tuần này của ForexFactory (lich_mang.py). Trang Tin tức & tâm lý còn tải tiêu đề RSS (tin_tuc.py), báo cáo COT của CFTC và chỉ số
sợ hãi/tham lam của alternative.me (tam_ly.py); cũng chỉ tải về."""
from __future__ import annotations

import argparse
import json
import re
import socket
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import bieu_do, canh_bao, cot, da_ma, gia, hoc, hoc_ma, kiem_chung, kien_thuc, nen_cu, nhat_ky, nhat_ky_trang, phan_tich, song, suc_khoe, tai_khoan, thuong_hieu
from . import cong_cu, dich, hoc_giao_dich, lich_mang, tam_ly, thi_truong, thi_truong_trang, tin_tuc, tin_tuc_trang, trang
from . import do_lai
from . import canh_bao_ve, hinh_ve, kiem_tin_hieu, kiem_tin_hieu_trang, mau_chi_bao
from . import cai_dat, giam_sat, hieu_suat, hieu_suat_trang, ke_hoach, ke_hoach_trang, kiem_lenh, kiem_lenh_trang, ky_luat, ky_luat_trang, nhieu_tai_khoan, sao_luu, telegram_nhom, tin_phan_ung
from . import duong, vo_app
from . import bao_mat_http, tai_khoan_chart
from . import ai_chart, ai_providers, ai_store, ai_evidence
from . import mcp_access
from . import luong_gia
from . import tin_hieu_ngan, tin_hieu_tien_cuu
from . import loi_nghiep_vu, phieu_ke_hoach
from .__main__ import HERE, xay
from . import tong_quan, khong_gian, local_runtime


def _so(s: str) -> float:
    """Số từ tham số đường dẫn: float('inf'), float('nan') và '1e999' cũng parse được nhưng làm hỏng phép tính phía sau (500 hoặc NaN trong JSON),
    nên báo ValueError (400) như số sai cú pháp."""
    x = float(s)
    if x != x or x in (float('inf'), float('-inf')):
        raise ValueError(f'số không hợp lệ: {s}')
    return x

LOAI = {'.png': 'image/png', '.txt': 'text/plain; charset=utf-8', '.json': 'application/json; charset=utf-8'}


def _out(cfg: dict) -> Path:
    base = Path(cfg.get('thu_muc_ra', 'out'))
    return base if base.is_absolute() else HERE / base


def _cham_phieu(cfg: dict, p: dict) -> dict:
    """Kết quả mô phỏng của phiếu đang theo dõi, chấm trên nến M5 đã đóng (bỏ nến đang chạy). Lỗi dữ liệu thì 'chua_xac_dinh'."""
    if not p.get('theo_doi'):
        return {'trang_thai': 'khong_theo_doi'}
    try:
        ma_phieu = str(p.get('ma') or da_ma.ma_vang(cfg))
        d = gia.goi(cfg, 'M5', 1500) if ma_phieu == da_ma.ma_vang(cfg) else da_ma.goi(cfg, ma_phieu, 'M5', 1500)
        cs = d.get('candles') or []
        live = d.get('live')
        if isinstance(live, int) and 0 <= live < len(cs):
            cs = cs[:live]
        return phieu_ke_hoach.cham_mo_phong(p, cs, 300)
    except gia.ChuaCoGia:
        return {'trang_thai': 'chua_xac_dinh', 'ly_do': 'chưa có dữ liệu nến (MT5 chưa nối, kho nến trống)'}
    except Exception as e:                                                    # noqa: BLE001
        return {'trang_thai': 'chua_xac_dinh', 'ly_do': f'không đọc được nến: {type(e).__name__}'}


def tao_vong_canh(cau_hinh: str):
    """Vòng canh cảnh báo theo cấu hình; None nếu mục canh_bao.bat là false."""
    cb = json.loads(Path(cau_hinh).read_text(encoding='utf-8')).get('canh_bao') or {}
    if not cb.get('bat', True):
        return None
    return canh_bao.VongCanh(lambda: json.loads(Path(cau_hinh).read_text(encoding='utf-8')), _out, cb.get('giay', 15))


NHIP_TICK = 0.008       # chu kỳ lấy mẫu mục tiêu; không phải cam kết độ trễ từ sàn tới màn hình
NHIP_QUYEN_LUONG = 5.0


class _MayChuDocQuyen(ThreadingHTTPServer):
    """Máy chủ giữ cổng ĐỘC QUYỀN. Mặc định http.server bật SO_REUSEADDR, mà trên Windows tùy chọn đó cho tiến trình thứ hai mở cùng cổng:
    hai webapp cùng chạy thì vòng Telegram, nhật ký, cảnh báo đều chạy đôi (gửi tin trùng). Ở đây bản thứ hai báo lỗi ngay lúc mở cổng,
    trước khi vòng nền nào khởi động (main mở cổng trước rồi mới bật các vòng)."""
    allow_reuse_address = False
    daemon_threads = True
    request_queue_size = 128  # đợt mở nhiều chart/SSE không nghẽn backlog TCP mặc định chỉ 5

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):                # Windows
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def server_close(self):
        if hasattr(self, 'luong_gia'):
            self.luong_gia.dong()
        super().server_close()
        if hasattr(self, 'instance_lock'):
            self.instance_lock.release()


def tao_may_chu(cau_hinh: str, host: str = '127.0.0.1', port: int = local_runtime.PORT, vong=None, bang=None, ghi_thieu: bool = False,
                tien_cuu_vong=None) -> ThreadingHTTPServer:
    """`ghi_thieu`: ghi các đoạn chưa dịch gặp lúc chạy vào so_cong_khai/dich/ (chỉ máy chủ thật bật; bài kiểm không ghi)."""
    """`bang`: bảng giá trực tiếp (thi_truong.BangGia) cho trang Thị trường, Công cụ và luồng /api/thi-truong/luong; None thì các trang đó báo đang tắt."""
    if host not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('Bản cài cá nhân chỉ nghe trên loopback. Website công khai dùng bản demo tĩnh.')
    TAT = {'tat': True, 'san_sang': False, 'ly_do': 'phần Thị trường đang tắt trong cấu hình (thi_truong.bat)', 'ds': [], 'lop': thi_truong.LOP,
           'tien_te': thi_truong.TIEN_TE, 'tai_khoan': {}, 'tuong_quan': None}

    class H(BaseHTTPRequestHandler):
        def _quyen(self, path, method):
            self._nguoi = None
            if any(self.headers.get(k) is not None for k in ('Forwarded', 'X-Forwarded-For', 'X-Forwarded-Host', 'X-Forwarded-Proto')):
                self._gui(403, LOAI['.json'], b'{"ok":false,"ly_do":"Local installation does not accept reverse proxies"}', dich_noi_dung=False)
                return False
            root = Path(cau_hinh).resolve().parent
            try:
                self._nguoi = khong_gian.nguoi(self.headers.get('Cookie'), root)
                if path == '/api/khong-gian' and method == 'GET':
                    body = {'mo_hinh': 'ca_nhan_cuc_bo', 'nguoi': self._nguoi, 'can_tao_chu': not tai_khoan_chart._doc(root)['nguoi']}
                    self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False).encode(), dich_noi_dung=False)
                    return False
                if khong_gian.cong_khai(path, method) or path == '/api/mcp/tool' and method == 'GET':
                    return True
                if method == 'GET' and path.startswith('/tinh/'):
                    self._gui(404, 'text/plain; charset=utf-8', b'Unknown static asset')
                    return False
                if self._nguoi and self._nguoi.get('chu'):
                    tab = self.headers.get('X-Chart-Owner')
                    if tab and tab != self._nguoi['id']:
                        raise tai_khoan_chart.LoiTaiKhoan(409, 'Tài khoản đã thay đổi. Tải lại trang.')
                    return True
                if self._nguoi and path in khong_gian.SCOPED:
                    return True  # các handler này tiếp tục kiểm UID của phiên, không nhận UID từ khách
                code = 403 if self._nguoi else 401
                if method == 'GET' and not path.startswith(('/api/', '/threads/', '/telegram/anh/')):
                    body = khong_gian.trang_vao(not tai_khoan_chart._doc(root)['nguoi'], bool(self._nguoi)).encode()
                    self._gui(200, 'text/html; charset=utf-8', body)
                else:
                    self._gui(code, LOAI['.json'], json.dumps({'ok': False, 'ly_do': 'Đăng nhập tài khoản chủ trên máy này để truy cập dữ liệu MT5 riêng.'}, ensure_ascii=False).encode())
                return False
            except tai_khoan_chart.LoiTaiKhoan as e:
                self._gui(e.ma, LOAI['.json'], json.dumps({'ok': False, 'ly_do': str(e)}, ensure_ascii=False).encode())
                return False

        def _ai_user(self, owner=False):
            root = Path(cau_hinh).resolve().parent
            u = tai_khoan_chart.hien_tai(self.headers.get('Cookie'), root)
            if not u:
                raise ai_store.StoreError('Đăng nhập tài khoản biểu đồ trước khi sử dụng AI.', 401)
            if owner and not u['chu']:
                raise ai_store.StoreError('Chỉ chủ tài khoản được cấu hình dịch vụ AI.', 403)
            tab_owner = self.headers.get('X-Chart-Owner')
            if tab_owner and tab_owner != u['id']:
                raise ai_store.StoreError('Tài khoản đã thay đổi. Tải lại trang trước khi hỏi AI.', 409)
            return u

        def setup(self):
            super().setup()
            self.connection.settimeout(bao_mat_http.HAN_DOC)

        def _luong_bang(self) -> None:
            """Luồng Server-Sent Events của bảng giá mọi mã (trang Thị trường, Công cụ): giữ kết nối mở và ghi mỗi khi có tick mới."""
            if bang is None:
                return self._gui(503, 'text/plain; charset=utf-8', TAT['ly_do'].encode('utf-8'))
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-HGR-Build', self.server.local_build)
            self._tieu_de_bao_ve()
            self.end_headers()

            def gui(b: bytes) -> None:
                self.wfile.write(b)
                self.wfile.flush()
            try:
                bang.luong(gui)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                pass                                                # trình duyệt đã đóng trang


        def _gui(self, ma: int, loai: str, body: bytes, nho: int = 0, *, tieu_de=None, dich_noi_dung=True) -> None:
            q = self.path.partition('?')[2]
            lang = dich.ngon_ngu(self.headers.get('Cookie'), q)
            if dich_noi_dung and lang != 'vi' and not nho and (loai.startswith('text/html') or loai.startswith('application/json')):   # không dịch nội dung bản vẽ riêng
                body = dich.dich_phan_hoi(body, loai, lang, dich.THIEU)
                if ghi_thieu:
                    dich.ghi_thieu(lang)
            user = getattr(self, '_nguoi', None)
            if loai.startswith('text/html') and user:
                body = body.replace(b'<script>', khong_gian.phien_script(user).encode() + b'<script>', 1)
            self.send_response(ma)
            self.send_header('Content-Type', loai)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', f'public, max-age={nho}, immutable' if nho else 'no-store')       # chỉ tệp tĩnh không đổi mới được trình duyệt nhớ
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-HGR-Build', self.server.local_build)
            self._tieu_de_bao_ve()
            for k, v in (tieu_de or {}).items():
                self.send_header(k, v)
            if 'lang=' in q:                                                 # ?lang=en / ?lang=vi: nhớ lựa chọn cho các lần sau
                self.send_header('Set-Cookie', f'lang={lang}; Path=/; Max-Age=31536000; SameSite=Lax')
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError):
                pass  # tab đã đóng/đổi trang: không gửi tiếp phản hồi 500 trên kết nối đã mất

        def _day_tick(self, g: dict, tf: str, ma: str | None) -> None:
            hub = self.server.luong_gia
            try:
                with hub.dang_ky(g, tf, ma) as kenh:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
                    self.send_header('Cache-Control', 'no-store, no-transform')
                    self.send_header('X-Accel-Buffering', 'no')
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self._tieu_de_bao_ve()
                    self.end_headers()
                    self.wfile.write(b'retry: 1000\n\n')
                    phien_ban, het = 0, time.monotonic() + 600
                    xem_lai_quyen = time.monotonic() + NHIP_QUYEN_LUONG
                    while (tin := hub.doi(kenh, phien_ban, het)) is not None:
                        if time.monotonic() >= xem_lai_quyen:
                            self._ai_user(owner=True)
                            xem_lai_quyen = time.monotonic() + NHIP_QUYEN_LUONG
                        phien_ban, goi = tin
                        self.wfile.write(goi)
            except luong_gia.QuaTai:
                self._gui(503, 'text/plain; charset=utf-8', 'Đang có nhiều kết nối giá. Thử tải lại biểu đồ.'.encode(), tieu_de={'Retry-After': '5'})
            except (OSError, ai_store.StoreError, tai_khoan_chart.LoiTaiKhoan):
                pass  # tab đã đóng, mất mạng, đọc quá chậm hoặc phiên đã hết quyền

        def do_GET(self):  # noqa: N802 - tên do http.server quy định
            if not self._host_ok():                                        # DNS rebinding: trang lạ không được đọc số liệu
                return self._gui(403, 'text/plain; charset=utf-8', 'Chỉ mở được webapp bằng địa chỉ 127.0.0.1 hoặc localhost.'.encode('utf-8'))
            url = urlparse(self.path)
            path = unquote(url.path)
            if not self._quyen(path, 'GET'):
                return
            if path == '/api/phien-ban':
                body = {'san_pham': thuong_hieu.TEN, 'build': self.server.local_build, 'cong': self.server.server_port,
                        'che_do': self.server.runtime_mode, 'chi_doc_mt5': True}
                if tien_cuu_vong is not None:
                    body['theo_doi_tick'] = {'dang_chay': tien_cuu_vong.is_alive() and not tien_cuu_vong.dung.is_set(),
                                             'lan_quet': tien_cuu_vong.luc_quet, 'co_du_lieu': bool(tien_cuu_vong.trang_thai),
                                             'loi': bool(tien_cuu_vong.loi)}
                return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False).encode(), dich_noi_dung=False)
            if path == '/api/mcp/tool':
                try:
                    config = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    root = Path(cau_hinh).resolve().parent
                    if not mcp_access.authorize(config, root, self.headers.get('Authorization', '')):
                        return self._gui(403, LOAI['.json'], b'{"ok":false,"error":"MCP disabled or unauthorized"}', dich_noi_dung=False)
                    q = parse_qs(url.query)
                    if len(url.query) > 4096:
                        raise ValueError('Tham số MCP quá dài.')
                    args = json.loads(q.get('arguments', ['{}'])[0])
                    result = mcp_access.route(root, config, q.get('tool', [''])[0], args)
                    if isinstance(result, bytes):
                        return self._gui(200, 'image/png', result, dich_noi_dung=False)
                    if isinstance(result, dict):
                        return self._gui(200, LOAI['.json'], json.dumps(result, ensure_ascii=False, allow_nan=False).encode('utf-8'), dich_noi_dung=False)
                    url = urlparse(result)
                    path = url.path
                except (ValueError, OSError, ImportError):
                    return self._gui(400, LOAI['.json'], b'{"ok":false,"error":"Invalid or expired MCP snapshot; check local configuration and data"}', dich_noi_dung=False)
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
                if path == '/kiem-tin-hieu':                                    # kiểm chứng tín hiệu của các nhóm Telegram
                    return self._gui(200, 'text/html; charset=utf-8', kiem_tin_hieu_trang.trang_kiem_tin_hieu(thuong_hieu.TEN).encode('utf-8'))
                if path == '/api/kiem-lenh':                                # kiểm tra trước khi vào lệnh: chỉ đọc MT5, không đặt lệnh
                    q = parse_qs(url.query)
                    lay = lambda k: (q.get(k, [''])[0] or '').strip().replace(',', '.')   # noqa: E731
                    try:
                        chieu = lay('chieu').upper()
                        if chieu not in ('MUA', 'BAN') or not lay('ma'):
                            raise ValueError('cần ma và chieu=MUA|BAN')
                        so = lambda k: _so(lay(k)) if lay(k) else None      # noqa: E731
                        lenh = {'ma': lay('ma'), 'chieu': chieu, 'vao': _so(lay('vao')), 'sl': so('sl'), 'tp': so('tp'), 'rui_ro_pct': so('rui_ro')}
                        if lenh['rui_ro_pct'] is not None and not 0 < lenh['rui_ro_pct'] <= 100:
                            raise ValueError('rui_ro phải trong (0, 100]')
                        if lenh['vao'] <= 0 or any(lenh[k] is not None and lenh[k] < 0 for k in ('sl', 'tp')):
                            raise ValueError('giá vào phải dương, dừng lỗ và chốt lời không âm')
                        cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                        qt = {k[2:]: v for k in ('q_rui_ro_lenh_toi_da_pct', 'q_lo_ngay_toi_da_pct', 'q_tong_rui_ro_toi_da_pct')
                              if (v := so(k)) is not None and 0 < v <= 100}
                        if qt:
                            cfg['kiem_lenh'] = {**(cfg.get('kiem_lenh') or {}), **qt}
                        body = kiem_lenh.kiem(cfg, bang, lenh)
                    except ValueError as e:
                        return self._gui(400, 'text/plain; charset=utf-8', f'Yêu cầu không hợp lệ: {e}'.encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False, default=str).encode('utf-8'))
                if path == '/api/vi-the':                                  # đối chiếu vị thế MT5 / nhật ký EA / bot (vi_the.py), chỉ đọc
                    from . import vi_the                                     # noqa: PLC0415
                    body = vi_the.tong_hop_nho(json.loads(Path(cau_hinh).read_text(encoding='utf-8')))
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False, default=str).encode('utf-8'))
                if path == '/api/harrison/tien-cuu':                       # sổ tiến cứu riêng của Harrison (harrison_tien_cuu.py), chỉ đọc
                    from . import harrison_tien_cuu as HT                    # noqa: PLC0415
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    kh = HT.khoa_phien_ban()
                    dau, ds = HT.doc(_out(cfg), kh)
                    body = {'tom_tat': HT.tom_tat(_out(cfg), kh), 'dau': dau, 'ds': ds[-50:][::-1]}
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False, default=str).encode('utf-8'))
                if path.startswith('/api/loi/'):                            # lõi nghiệp vụ chỉ đọc (loi_nghiep_vu.py), dùng cho MCP và kiểm tra
                    q = parse_qs(url.query)
                    lay = lambda k: (q.get(k, [''])[0] or '').strip()[:60]     # noqa: E731
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    try:
                        if path == '/api/loi/chup':
                            tf = lay('tf') or 'M15'
                            if tf not in gia.KHUNG:
                                raise ValueError('khung không hợp lệ')
                            body = loi_nghiep_vu.chup(cfg, lay('ma'), tf, thu_muc=_out(cfg))
                        elif path == '/api/loi/anh-chup':
                            body = loi_nghiep_vu.lay(lay('id'), _out(cfg))
                        elif path == '/api/loi/dieu-kien':
                            sn = loi_nghiep_vu.lay(lay('sn'), _out(cfg))
                            body = loi_nghiep_vu.dieu_kien(sn, lay('pp')) if sn else None
                        elif path == '/api/loi/bang-chung':
                            body = loi_nghiep_vu.bang_chung_phuong_phap(lay('pp'))
                        elif path == '/api/loi/review':
                            body = loi_nghiep_vu.tong_ket_review(_out(cfg))
                        else:
                            body = None
                    except gia.ChuaCoGia as e:
                        return self._gui(503, 'text/plain; charset=utf-8', f'Chưa có giá: {e}'.encode('utf-8'))
                    except ValueError as e:
                        return self._gui(400, 'text/plain; charset=utf-8', f'Yêu cầu không hợp lệ: {e}'.encode('utf-8'))
                    if body is None:
                        return self._gui(404, 'text/plain; charset=utf-8', 'Không có (ảnh chụp đã hết hạn hoặc sai id).'.encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False, default=str).encode('utf-8'))
                if path == '/api/phieu/anh':                               # ảnh chart lúc quyết định của một phiếu
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    p = phieu_ke_hoach.duong_anh(_out(cfg), (parse_qs(url.query).get('f', [''])[0] or '').strip())
                    if p is None:
                        return self._gui(404, 'text/plain; charset=utf-8', 'Không có ảnh này.'.encode('utf-8'))
                    return self._gui(200, 'image/jpeg' if p.suffix == '.jpg' else 'image/png', p.read_bytes())
                if path in ('/api/phieu', '/api/phieu/ds'):                # phiếu kế hoạch dùng chung (phieu_ke_hoach.py): chỉ đọc
                    q = parse_qs(url.query)
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    if path == '/api/phieu/ds':
                        ds = phieu_ke_hoach.danh_sach(_out(cfg))
                        for p in ds[:30]:                                    # chấm mô phỏng cho các phiếu đang theo dõi gần nhất
                            if p.get('theo_doi'):
                                p['cham'] = _cham_phieu(cfg, p)
                        body = {'ds': ds}
                    else:
                        id_ = (q.get('id', [''])[0] or '').strip()
                        v = (q.get('v', [''])[0] or '').strip()
                        p = phieu_ke_hoach.doc(_out(cfg), id_, int(v) if v.isdigit() else None) if re.fullmatch(r'KH-[0-9A-Za-z-]{6,40}', id_) else None
                        if p is None:
                            return self._gui(404, 'text/plain; charset=utf-8', 'Không có phiếu này.'.encode('utf-8'))
                        body = {**p, 'cham': _cham_phieu(cfg, p)}
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False, default=str).encode('utf-8'))
                if path == '/api/giam-sat':                                 # dải cảnh báo rủi ro trên mọi trang: chỉ đọc MT5
                    q = parse_qs(url.query)
                    try:
                        qt = {}
                        for k in ('q_rui_ro_lenh_toi_da_pct', 'q_lo_ngay_toi_da_pct', 'q_tong_rui_ro_toi_da_pct'):
                            s = (q.get(k, [''])[0] or '').strip().replace(',', '.')
                            if s and 0 < (v := _so(s)) <= 100:
                                qt[k[2:]] = v
                        cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                        body = giam_sat.doc(cfg, bang, qt)
                    except ValueError as e:
                        return self._gui(400, 'text/plain; charset=utf-8', f'Yêu cầu không hợp lệ: {e}'.encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False, default=str).encode('utf-8'))
                if path == '/ke-hoach':
                    return self._gui(200, 'text/html; charset=utf-8', ke_hoach_trang.trang_ke_hoach(thuong_hieu.TEN).encode('utf-8'))
                if path == '/api/ke-hoach/nen':                             # dữ liệu thô cho bản demo tĩnh (cong-cu/xuat_demo.py)
                    q = parse_qs(url.query)
                    try:
                        body = ke_hoach.du_lieu_tho(bang, (q.get('ma', [''])[0] or '').strip(), (q.get('khung', ['H1'])[0] or 'H1').strip())
                    except ValueError as e:
                        return self._gui(400, 'text/plain; charset=utf-8', f'Yêu cầu không hợp lệ: {e}'.encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False).encode('utf-8'))
                if path == '/api/ke-hoach':                                 # kế hoạch vốn và lệnh: chỉ đọc MT5, không đặt lệnh
                    q = parse_qs(url.query)
                    lay = lambda k: (q.get(k, [''])[0] or '').strip().replace(',', '.')   # noqa: E731
                    try:
                        chieu, khung, muc = lay('chieu').upper(), lay('khung') or 'H1', lay('muc') or 'can_bang'
                        if chieu not in ('MUA', 'BAN') or not lay('ma'):
                            raise ValueError('cần ma và chieu=MUA|BAN')
                        if khung not in ke_hoach.KHUNG or (muc not in ke_hoach.MUC_RUI_RO and muc != 'tu_dat'):
                            raise ValueError('khung hoặc mức rủi ro không hợp lệ')
                        so = lambda k: _so(lay(k)) if lay(k) else None      # noqa: E731
                        von, vao, sl, rr_tu = so('von'), so('vao'), so('sl'), so('rui_ro')
                        thang, rr = so('thang'), so('rr')
                        if (von is not None and von <= 0) or (vao is not None and vao <= 0) or (sl is not None and sl <= 0):
                            raise ValueError('vốn, giá vào và dừng lỗ phải dương')
                        if muc == 'tu_dat' and (rr_tu is None or not 0 < rr_tu <= 100):
                            raise ValueError('rui_ro phải trong (0, 100]')
                        if (thang is not None and not 0 <= thang <= 100) or (rr is not None and not 0 < rr <= 20):
                            raise ValueError('thang phải trong [0, 100], rr trong (0, 20]')
                        cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                        body = ke_hoach.lap(cfg, bang, lay('ma'), chieu, khung, vao, sl, von, muc, rr_tu if muc == 'tu_dat' else None,
                                            50.0 if thang is None else thang, 2.0 if rr is None else rr)
                    except ValueError as e:
                        return self._gui(400, 'text/plain; charset=utf-8', f'Yêu cầu không hợp lệ: {e}'.encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False, default=str).encode('utf-8'))
                if path == '/renko':                                        # Renko và Điểm & Hình: biểu đồ chỉ theo giá (renko_trang.py)
                    from . import renko_trang                               # noqa: PLC0415
                    return self._gui(200, 'text/html; charset=utf-8', renko_trang.trang_renko(thuong_hieu.TEN).encode('utf-8'))
                if path == '/da-khung':                                     # 2 hoặc 4 biểu đồ một mã, nhiều khung, con trỏ đồng bộ (da_khung_trang.py)
                    from . import da_khung_trang                            # noqa: PLC0415
                    return self._gui(200, 'text/html; charset=utf-8', da_khung_trang.trang_da_khung(thuong_hieu.TEN).encode('utf-8'))
                if path == '/bat-dau':                                      # hướng dẫn người mới: 5 bước tự kiểm (bat_dau_trang.py)
                    from . import bat_dau_trang                             # noqa: PLC0415
                    return self._gui(200, 'text/html; charset=utf-8', bat_dau_trang.trang_bat_dau(thuong_hieu.TEN).encode('utf-8'))
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
                        for k, hop_le in (('q_rui_ro_lenh_toi_da_pct', lambda v: 0 < v <= 100), ('q_lo_ngay_toi_da_pct', lambda v: 0 < v <= 100),
                                          ('q_so_lenh_ngay_toi_da', lambda v: 0 <= v <= 1000 and v == int(v))):   # số lệnh: số nguyên, 0 = không kiểm
                            if lay(k):
                                v = _so(lay(k))
                                if hop_le(v):
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
                        body = bang.tinh(lay('ma'), lay('loai'), _so(lay('lot')), _so(lay('vao')), _so(lay('ra')) if lay('ra') else None)
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
                    try:
                        self._ai_user(owner=True)
                    except ai_store.StoreError as e:
                        return self._gui(e.status, LOAI['.json'], json.dumps({'ok': False, 'chan': [str(e)], 'thong_bao': str(e)}, ensure_ascii=False).encode('utf-8'))
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(cai_dat.doc(cfg), ensure_ascii=False, default=str).encode('utf-8'))
                if path == '/api/mcp/admin':
                    try:
                        self._ai_user(owner=True)
                        cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                        body = mcp_access.configs(cfg, Path(cau_hinh), self.server.server_port)
                        return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False).encode('utf-8'), dich_noi_dung=False)
                    except ai_store.StoreError as e:
                        return self._gui(e.status, LOAI['.json'], json.dumps({'ok': False, 'chan': [str(e)]}, ensure_ascii=False).encode('utf-8'))
                if path == '/api/app':                                     # vỏ app: phiên bản, thư mục dữ liệu, bản mới (vo_app.py)
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(vo_app.trang_thai(cfg), ensure_ascii=False).encode('utf-8'))
                if path == '/api/tin-toi':                                 # tin USD mạnh sắp ra kèm số đo phản ứng của giá vàng
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(tin_phan_ung.tin_toi(cfg), ensure_ascii=False).encode('utf-8'))
                if path == '/cac-tai-khoan':                               # mọi tài khoản MT5 đã nối, demo và tiền thật (chỉ đọc)
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, 'text/html; charset=utf-8', nhieu_tai_khoan.trang_cac_tai_khoan(thuong_hieu.TEN).encode('utf-8'))
                if path == '/telegram':                                    # nhóm Telegram cố định: tín hiệu, kết quả, tin sắp ra
                    return self._gui(200, 'text/html; charset=utf-8', telegram_nhom.trang_telegram(thuong_hieu.TEN).encode('utf-8'))
                if path == '/api/do-lai':                                  # kiểm trên dữ liệu mới: kết luận theo luật đã đăng ký
                    from . import phuong_phap as _PP                           # noqa: PLC0415
                    tm = do_lai.tom_tat(ten_ma={v['ten']: k for k, v in _PP.DS.items()})
                    return self._gui(200, LOAI['.json'], json.dumps(tm, ensure_ascii=False).encode('utf-8'))
                if path.startswith('/telegram/anh/'):                      # ảnh biểu đồ kèm tin (xem trước ở trang /telegram)
                    ten = unquote(path[len('/telegram/anh/'):])
                    f = telegram_nhom.thu_muc_anh() / ten
                    if re.fullmatch(r'lenh-\d+\.png', ten) and f.is_file():
                        return self._gui(200, LOAI['.png'], f.read_bytes())
                    return self._gui(404, 'text/plain; charset=utf-8', 'Không có ảnh này.'.encode('utf-8'))
                if path == '/api/telegram':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(telegram_nhom.xem(cfg), ensure_ascii=False, default=str).encode('utf-8'))
                if path == '/sao-luu':                                     # sao lưu toàn bộ hệ thống mỗi ngày
                    return self._gui(200, 'text/html; charset=utf-8', sao_luu.trang_sao_luu(thuong_hieu.TEN).encode('utf-8'))
                if path == '/api/sao-luu':
                    return self._gui(200, LOAI['.json'], json.dumps(sao_luu.xem(), ensure_ascii=False, default=str).encode('utf-8'))
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
                    f = duong.goc_chuong_trinh() / 'tinh' / 'phong' / ten
                    if re.fullmatch(r'be-vietnam-pro-(400|500|600|700)-(vietnamese|latin-ext|latin)\.woff2', ten) and f.is_file():
                        return self._gui(200, 'font/woff2', f.read_bytes(), nho=30 * 86400)
                    return self._gui(404, 'text/plain; charset=utf-8', 'Không có tệp phông này.'.encode('utf-8'))
                if path == '/tinh/lightweight-charts.js':                    # thư viện biểu đồ, phục vụ từ máy (không gọi ra mạng lúc chạy)
                    f = duong.goc_chuong_trinh() / 'tinh' / 'lightweight-charts-5.3.0' / 'lightweight-charts.standalone.production.js'
                    if f.is_file():
                        return self._gui(200, 'text/javascript; charset=utf-8', f.read_bytes())
                    return self._gui(404, 'text/plain; charset=utf-8', 'Chưa có tệp thư viện biểu đồ; trang dùng lớp vẽ dự phòng.'.encode('utf-8'))
                if path == '/tinh/chi-bao-worker.js':
                    from . import bieu_do_chi_bao  # noqa: PLC0415
                    return self._gui(200, 'text/javascript; charset=utf-8', bieu_do_chi_bao.WORKER_JS.encode('utf-8'), dich_noi_dung=False)
                if path == '/bieu-do':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    nguoi = tai_khoan_chart.hien_tai(self.headers.get('Cookie'), Path(cau_hinh).resolve().parent)
                    cfg_chart = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    return self._gui(200, 'text/html; charset=utf-8', bieu_do.trang_bieu_do(thuong_hieu.TEN, nguoi, da_ma.ma_vang(cfg_chart) if nguoi and nguoi.get('chu') else 'XAUUSD').encode('utf-8'))
                if path == '/api/gia':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    q = parse_qs(url.query)
                    try:
                        ma = (q.get('ma', [''])[0] or '').strip()
                        if q.get('gon', [''])[0] == '1':
                            from . import da_khung_gia  # noqa: PLC0415
                            data = da_khung_gia.goi(cfg, ma, q.get('tf', ['M15'])[0], int(q.get('n', ['400'])[0]))
                        elif ma and ma != da_ma.ma_vang(cfg):
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
                    if tf not in song.SO_NEN and tf not in song.KHUNG_XEM:
                        return self._gui(400, 'text/plain; charset=utf-8', f'Yêu cầu không hợp lệ: khung {tf}'.encode('utf-8'))
                    ma = (q.get('ma', [''])[0] or '').strip()
                    if len(ma) > 64 or any(not c.isprintable() for c in ma):
                        return self._gui(400, 'text/plain; charset=utf-8', 'Mã không hợp lệ.'.encode())
                    return self._day_tick(cfg.get('gia') or {}, tf, None if not ma or ma == da_ma.ma_vang(cfg) else ma)
                if path == '/api/song/tinh-trang':
                    data = self.server.luong_gia.thong_ke()
                    return self._gui(200, LOAI['.json'], json.dumps(data).encode(), dich_noi_dung=False)
                if path == '/api/so-lenh':                                 # độ sâu thị trường: sổ lệnh sàn gửi về MT5, chỉ đọc (do_sau.py)
                    from . import do_sau                                    # noqa: PLC0415
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    ma = (parse_qs(url.query).get('ma', [''])[0] or '').strip()
                    if not re.fullmatch(r'[A-Za-z0-9._#-]{0,24}', ma):
                        return self._gui(400, 'text/plain; charset=utf-8', 'Yêu cầu không hợp lệ.'.encode('utf-8'))
                    kq = do_sau.doc(cfg.get('gia') or {}, None if not ma or ma == da_ma.ma_vang(cfg) else ma)
                    return self._gui(200, LOAI['.json'], json.dumps(kq, ensure_ascii=False).encode('utf-8'))
                if path == '/api/khoi-luong':                              # tick volume của nến cũ (tới 60.000 nến MT5 còn giữ), cho chỉ báo khối lượng
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    q = parse_qs(url.query)
                    tf, ma = q.get('tf', ['M15'])[0], (q.get('ma', [''])[0] or '').strip()
                    if (tf not in song.SO_NEN and tf not in song.KHUNG_XEM) or not re.fullmatch(r'[A-Za-z0-9._#-]{0,24}', ma):
                        return self._gui(400, 'text/plain; charset=utf-8', 'Yêu cầu không hợp lệ.'.encode('utf-8'))
                    try:
                        n = max(100, min(int(q.get('n', ['30000'])[0]), 60000))
                    except ValueError:
                        n = 30000
                    if song.khung_song(cfg.get('gia') or {}) is None:
                        kl, ly = None, song.ly_do() or 'chưa nối MT5'
                    else:
                        kl, ly = song.khoi_luong(tf, None if not ma or ma == da_ma.ma_vang(cfg) else ma, n), None
                    t = sorted(kl) if kl else []
                    return self._gui(200, LOAI['.json'], json.dumps({'tf': tf, 'ma': ma, 't': t, 'v': [kl[x] for x in t], 'ly_do': ly}, ensure_ascii=False).encode('utf-8'))
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
                    q = parse_qs(url.query)
                    ma = (q.get('ma', [''])[0] or '').strip()
                    tf = q.get('tf', ['M15'])[0]
                    try:
                        if tf in ('M5', 'M30'):
                            data = phan_tich.ngan(cfg, ma, tf)
                        else:
                            data = da_ma.phan_tich(cfg, ma) if ma and ma != da_ma.ma_vang(cfg) else phan_tich.phan_tich(cfg)
                            data['khung_phan_tich'] = 'M15'
                        try:                                                   # ghi điểm vào còn hiệu lực vào nhật ký (nếu cấu hình bật)
                            if not data.get('quy_trinh_ngan'):
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
                    gon = parse_qs(url.query).get('gon', [''])[0] == '1'           # ô chọn mã chỉ cần tên: không tính xu hướng của từng mã
                    return self._gui(200, LOAI['.json'], json.dumps(da_ma.ten_ma(cfg) if gon else da_ma.danh_sach(cfg), ensure_ascii=False).encode('utf-8'))
                if path == '/api/ma/danh-muc':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    try:
                        self._ai_user(owner=True)
                        data = da_ma.ten_ma(cfg, toan_bo=True)
                    except ai_store.StoreError as e:
                        return self._gui(e.status, LOAI['.json'], json.dumps({'ly_do': str(e)}, ensure_ascii=False).encode(), dich_noi_dung=False)
                    return self._gui(200, LOAI['.json'], json.dumps(data, ensure_ascii=False).encode(), dich_noi_dung=False)
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
                if path == '/api/tin-hieu-ngan':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    ma = parse_qs(url.query).get('ma', [''])[0].strip()
                    try:
                        data = tin_hieu_ngan.doc(cfg, ma)
                        data['canh_bao'] = canh_bao.ngan_han(data)
                    except ValueError as e:
                        return self._gui(400, LOAI['.json'], json.dumps({'ly_do': str(e)}, ensure_ascii=False).encode())
                    cb = cfg.get('canh_bao') or {}
                    try:
                        tien_cuu = tin_hieu_tien_cuu.tong_hop(_out(cfg), data.get('may_chu', ''), data['ma'])
                        data['tien_cuu'] = {**tien_cuu, 'ma_theo_doi': data['ma'] in tin_hieu_tien_cuu.ma_theo_doi(cfg),
                                            'bat': bool(cb.get('tien_cuu', True) and cb.get('ngan_han', True)),
                                            'dang_chay': any(t and t.is_alive() and not t.dung.is_set() for t in (vong, tien_cuu_vong)),
                                            'loi_vong': bool(tien_cuu_vong and tien_cuu_vong.loi),
                                            'nghien_cuu': tin_hieu_tien_cuu.tong_hop_nghien_cuu(_out(cfg), data.get('may_chu', ''), data['ma'])
                                            if data['ma'] == da_ma.ma_vang(cfg) else [],
                                            'lan_quet': tien_cuu_vong.trang_thai.get(data['ma']) if tien_cuu_vong else None}
                    except sqlite3.Error:
                        data['tien_cuu'] = {'ly_do': 'Chưa đọc được sổ tiến cứu.'}
                    for k in ('tien_tk', 'buoc_gia', 'gia_tick', 'bid', 'ask', 'tick_ms'):
                        data.pop(k, None)
                    return self._gui(200, LOAI['.json'], json.dumps(data, ensure_ascii=False).encode())
                if path == '/api/canh-bao':
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    tt = vong.trang_thai() if vong is not None else {'dang_chay': False, 'ly_do': 'Cảnh báo đang tắt trong cấu hình.'}
                    body = {'ds': canh_bao.doc(_out(cfg), 30), **tt}
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False).encode('utf-8'))
                if path == '/api/mau-chi-bao':                                  # mẫu chỉ báo và chỉ báo yêu thích, lưu trên máy chủ
                    root = Path(cau_hinh).resolve().parent
                    u = tai_khoan_chart.hien_tai(self.headers.get('Cookie'), root)
                    if not u:
                        return self._gui(401, LOAI['.json'], b'{"ok":false,"dang_nhap":false}')
                    if self.headers.get('X-Chart-Owner') != u['id']:
                        return self._gui(409, LOAI['.json'], b'{"ok":false,"doi_tai_khoan":true}')
                    return self._gui(200, LOAI['.json'], json.dumps({'chu': u['id'], **mau_chi_bao.doc(root, u['id'])}, ensure_ascii=False).encode('utf-8'), dich_noi_dung=False)
                if path in ('/api/tai-khoan-chart', '/api/hinh-ve', '/api/hinh-ve/lich-su'):
                    root = Path(cau_hinh).resolve().parent
                    try:
                        nguoi = tai_khoan_chart.hien_tai(self.headers.get('Cookie'), root)
                        if path == '/api/tai-khoan-chart':
                            body = {'nguoi': nguoi}
                        else:
                            if not nguoi:
                                return self._gui(401, LOAI['.json'], b'{"ok":false,"dang_nhap":false}')
                            if self.headers.get('X-Chart-Owner') != nguoi['id']:
                                return self._gui(409, LOAI['.json'], b'{"ok":false,"doi_tai_khoan":true}')
                            ma = (parse_qs(url.query).get('ma', [''])[0] or '').strip()
                            body = ({'ds': hinh_ve.lich_su(ma, root, nguoi['id'])} if path.endswith('/lich-su') else hinh_ve.doc(ma, root, nguoi['id']))
                            body['chu'] = nguoi['id']
                        return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False).encode('utf-8'), dich_noi_dung=False)
                    except (tai_khoan_chart.LoiTaiKhoan, hinh_ve.KhoLoi, ValueError) as e:
                        return self._gui(getattr(e, 'ma', 503 if isinstance(e, hinh_ve.KhoLoi) else 400), LOAI['.json'],
                                         json.dumps({'ok': False, 'ly_do': str(e)}, ensure_ascii=False).encode('utf-8'))
                if path == '/api/canh-bao-ve':                                  # cảnh báo trên đường vẽ: đang chờ, đã báo, Telegram riêng
                    root = Path(cau_hinh).resolve().parent
                    u = tai_khoan_chart.hien_tai(self.headers.get('Cookie'), root)
                    if not u:
                        return self._gui(401, LOAI['.json'], b'{"ok":false,"dang_nhap":false}')
                    if self.headers.get('X-Chart-Owner') != u['id']:
                        return self._gui(409, LOAI['.json'], b'{"ok":false,"doi_tai_khoan":true}')
                    q = parse_qs(url.query)
                    store = root if u['chu'] else canh_bao_ve.kho_rieng(u['id'], root)
                    body = {'chu': u['id'], **canh_bao_ve.trang_thai(q['ma'][0].strip() if 'ma' in q else None, store)}
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False).encode('utf-8'), dich_noi_dung=False)
                if path == '/api/gia-su':                                      # gia sư giao dịch: lượt còn lại, ngân sách, danh sách chủ đề
                    try:
                        self._ai_user(owner=True)
                    except ai_store.StoreError as e:
                        return self._gui(e.status, LOAI['.json'], json.dumps({'ok': False, 'chan': [str(e)], 'thong_bao': str(e)}, ensure_ascii=False).encode('utf-8'))
                    from . import gia_su                                       # noqa: PLC0415
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    pq = parse_qs(url.query)
                    if pq.get('phien'):                                        # học tiếp: hội thoại đã lưu của một buổi
                        b = gia_su.doc_buoi(pq['phien'][0])
                        return self._gui(200 if b else 404, LOAI['.json'], json.dumps(b or {'ok': False}, ensure_ascii=False).encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(gia_su.trang_thai(cfg, _out(cfg)), ensure_ascii=False).encode('utf-8'))
                if path in ('/api/ai-platform/status', '/api/ai-platform/admin', '/api/ai', '/api/ai-chi-bao'):
                    root = Path(cau_hinh).resolve().parent
                    try:
                        if path.endswith('/admin'):
                            self._ai_user(owner=True)
                            st = ai_store.admin(root)
                            with tai_khoan_chart._khoa:
                                st['users'] = [tai_khoan_chart._cong_khai(u) for u in tai_khoan_chart._doc(root)['nguoi'].values()]
                        else:
                            u = tai_khoan_chart.hien_tai(self.headers.get('Cookie'), root)
                            st = ai_store.status(root, u)
                        return self._gui(200, LOAI['.json'], json.dumps(st, ensure_ascii=False).encode('utf-8'), dich_noi_dung=False)
                    except (ai_store.StoreError, ai_providers.ProviderError) as e:
                        return self._gui(getattr(e, 'status', 400), LOAI['.json'], json.dumps({'ok': False, 'chan': [str(e)]}, ensure_ascii=False).encode('utf-8'))
                if path == '/api/tong-quan/so':
                    from . import tong_quan_so  # noqa: PLC0415 - chỉ đọc sổ, không dựng hoặc ghi báo cáo
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    body = tong_quan_so.doc(cfg)
                    return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8'))
                if path in ('/', '/index.html'):
                    return self._gui(200, 'text/html; charset=utf-8', tong_quan.trang_tong_quan(thuong_hieu.TEN).encode('utf-8'))
                if path in ('/so-cong-khai', '/api/so.json'):
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
            return bao_mat_http.host_hop_le(self.headers, self.server.server_port)

        def _cung_may(self) -> bool:
            return bao_mat_http.cung_nguon(self.headers, self.server.server_port)

        def do_POST(self):  # noqa: N802
            # Ba việc được phép qua POST: hỏi AI, thêm/bỏ/đọc lại tài khoản đã nối, và lưu cài đặt. Mọi lệnh đều phải đến từ chính trang
            # của webapp trên máy này (tiêu đề riêng, Host, Origin): trang web khác không gửi hộ được, kể cả qua DNS rebinding.
            if not self._cung_may():
                bao_mat_http.bo_than_con_lai(self)
                return self._gui(403, LOAI['.json'], json.dumps({'ok': False, 'thong_bao': 'Chỉ trang của webapp trên chính máy này mới được gửi lệnh.'},
                                                                ensure_ascii=False).encode('utf-8'))
            try:
                path = unquote(urlparse(self.path).path)
                if not self._quyen(path, 'POST'):
                    bao_mat_http.bo_than_con_lai(self)
                    return
                gioi_han = {
                    '/api/ai-platform/analyze': 1_600_000, '/api/ai-platform/settings': 16000, '/api/ai-platform/key': 8192,
                    '/api/cai-dat': 8192, '/api/app': 4096, '/api/ai-chi-bao': 65536,
                    '/api/cac-tai-khoan': 4096, '/api/kiem-tin-hieu': kiem_tin_hieu.TOI_DA_CHU * 4 + 4000,
                    '/api/mau-chi-bao': mau_chi_bao.TOI_DA_BYTE + 4000,
                    '/api/hinh-ve': hinh_ve.TOI_DA_BYTE + 2000, '/api/canh-bao-ve': 8192,
                    '/api/telegram': 8192, '/api/sao-luu': 4096, '/api/gia-su': 16384, '/api/phieu': phieu_ke_hoach.TOI_DA_ANH * 4 // 3 + 4096, '/api/ai-giai-thich': 4096,
                }
                yc = bao_mat_http.doc_json(self, gioi_han.get(path, 8192))
                if path == '/api/mcp/config':
                    try:
                        self._ai_user(owner=True)
                        if set(yc) - {'enabled', 'port', 'rotate'} or type(yc.get('enabled')) is not bool or type(yc.get('port')) is not int or not 1 <= yc['port'] <= 65535:
                            raise ValueError('Cấu hình MCP không hợp lệ.')
                        if 'rotate' in yc and type(yc['rotate']) is not bool:
                            raise ValueError('Lựa chọn tạo lại khóa không hợp lệ.')
                        root = Path(cau_hinh).resolve().parent
                        with ai_store.db(root):
                            if yc['enabled']:
                                mcp_access.token(root, create=True, rotate=yc.get('rotate', False))
                            cai_dat.ghi(Path(cau_hinh), {'mcp.bat': yc['enabled'], 'mcp.cong': yc['port']})
                        return self._gui(200, LOAI['.json'], b'{"ok":true}', dich_noi_dung=False)
                    except (ValueError, ai_store.StoreError) as e:
                        return self._gui(getattr(e, 'status', 400), LOAI['.json'], json.dumps({'ok': False, 'chan': [str(e)]}, ensure_ascii=False).encode('utf-8'))
                if path.startswith('/api/ai-platform/') or path in ('/api/ai', '/api/ai-chi-bao'):
                    root = Path(cau_hinh).resolve().parent
                    try:
                        owner = path in ('/api/ai-platform/settings', '/api/ai-platform/key', '/api/ai-platform/grant', '/api/ai-platform/check')
                        u = self._ai_user(owner=owner)
                        if path == '/api/ai-platform/settings':
                            ai_store.save(root, yc.get('settings'))
                            kq = {'ok': True}
                        elif path == '/api/ai-platform/check':
                            kq = ai_providers.check(root, ai_store.settings(root))
                        elif path == '/api/ai-platform/key':
                            with ai_store.db(root):
                                ai_providers.save_key(root, yc.get('provider'), yc.get('key'))
                            kq = {'ok': True}
                        elif path == '/api/ai-platform/grant':
                            with tai_khoan_chart._khoa:
                                if not isinstance(yc.get('uid'), str) or yc['uid'] not in tai_khoan_chart._doc(root)['nguoi']:
                                    raise ai_store.StoreError('Không tìm thấy tài khoản.')
                            ai_store.grant(root, yc.get('uid'), yc.get('plan'), yc.get('expires'))
                            kq = {'ok': True}
                        elif path in ('/api/ai-platform/analyze', '/api/ai', '/api/ai-chi-bao'):
                            cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                            kq = ai_chart.analyze(root, cfg, u, yc)
                        elif path == '/api/ai-platform/local':
                            from . import ai_local  # noqa: PLC0415
                            u = self._ai_user(owner=True)
                            cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                            kq = ai_local.analyze(root, cfg, u, yc)
                        else:
                            raise ai_store.StoreError('Không có API này.', 404)
                        return self._gui(200, LOAI['.json'], json.dumps(kq, ensure_ascii=False).encode('utf-8'), dich_noi_dung=False)
                    except (ai_store.StoreError, ai_providers.ProviderError) as e:
                        return self._gui(getattr(e, 'status', 400), LOAI['.json'], json.dumps({'ok': False, 'chan': [str(e)]}, ensure_ascii=False).encode('utf-8'), dich_noi_dung=False)
                if path == '/api/tai-khoan-chart':
                    root = Path(cau_hinh).resolve().parent
                    try:
                        viec = yc.get('viec')
                        headers = {}
                        if viec in ('dang_ky', 'dang_nhap'):
                            u, token = tai_khoan_chart.vao(yc.get('ten'), yc.get('mat_khau'), viec == 'dang_ky', root)
                            headers['Set-Cookie'] = tai_khoan_chart.cookie_header(token)
                            body = {'ok': True, 'nguoi': u}
                        elif viec == 'dang_xuat':
                            current = tai_khoan_chart.hien_tai(self.headers.get('Cookie'), root)
                            tab = self.headers.get('X-Chart-Owner')
                            if tab and current and tab != current['id']:
                                raise tai_khoan_chart.LoiTaiKhoan(409, 'Tài khoản đã thay đổi. Tải lại trang.')
                            tai_khoan_chart.ra(self.headers.get('Cookie'), root)
                            headers['Set-Cookie'] = tai_khoan_chart.cookie_header()
                            body = {'ok': True}
                        elif viec == 'nhap_cu':
                            u = tai_khoan_chart.hien_tai(self.headers.get('Cookie'), root)
                            if not u or not u['chu']:
                                raise tai_khoan_chart.LoiTaiKhoan(403, 'Chỉ tài khoản chủ đầu tiên được nhập kho bản vẽ cũ.')
                            cfg_chart = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                            body = {'ok': True, **hinh_ve.nhap_cu(u['id'], da_ma.ma_vang(cfg_chart), root), 'so_mau': 0}
                            old_templates = mau_chi_bao.doc(root)
                            if mau_chi_bao.doc(root, u['id'])['ban'] is None and old_templates['ban'] is not None:
                                mau_chi_bao.luu(old_templates['mau'], old_templates['sao'], root, chu=u['id'])
                                body['so_mau'] = len(old_templates['mau'])
                        else:
                            raise ValueError('Yêu cầu tài khoản không hợp lệ.')
                        return self._gui(200, LOAI['.json'], json.dumps(body, ensure_ascii=False).encode('utf-8'), tieu_de=headers, dich_noi_dung=False)
                    except (tai_khoan_chart.LoiTaiKhoan, ValueError, OSError) as e:
                        return self._gui(getattr(e, 'ma', 400), LOAI['.json'], json.dumps({'ok': False, 'ly_do': str(e)}, ensure_ascii=False).encode('utf-8'))
                if urlparse(self.path).path == '/api/cai-dat':
                    try:
                        self._ai_user(owner=True)
                    except ai_store.StoreError as e:
                        return self._gui(e.status, LOAI['.json'], json.dumps({'ok': False, 'chan': [str(e)], 'thong_bao': str(e)}, ensure_ascii=False).encode('utf-8'))
                    if not self._cung_may():
                        return self._gui(403, LOAI['.json'], json.dumps({'ok': False, 'thong_bao': 'Chỉ trang Cài đặt trên chính máy này mới được lưu.'},
                                                                        ensure_ascii=False).encode('utf-8'))
                    try:
                        if yc.get('viec') == 'noi_lai':
                            cai_dat.noi_lai(json.loads(Path(cau_hinh).read_text(encoding='utf-8')).get('gia') or {})
                            kq = {'ok': True, 'thong_bao': 'Đang nối lại MT5…'}
                        elif yc.get('viec') == 'luu':
                            kq = cai_dat.ghi(Path(cau_hinh), yc.get('gia_tri'))
                        elif yc.get('viec') == 'them_ma':
                            cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                            cai_dat.them_ma(cfg, yc.get('ma'))
                            kq = {'ok': True, 'thong_bao': 'Đã thêm mã vào Market Watch.'}
                        else:
                            raise ValueError('yêu cầu không hợp lệ')
                    except ValueError as e:
                        return self._gui(400, LOAI['.json'], json.dumps({'ok': False, 'thong_bao': f'Chưa lưu: {e}'}, ensure_ascii=False).encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps(kq, ensure_ascii=False).encode('utf-8'))
                if urlparse(self.path).path == '/api/app':                 # việc của vỏ app: hiện cửa sổ, mở thư mục dữ liệu, kiểm và tải bản mới
                    if not self._cung_may():
                        return self._gui(403, LOAI['.json'], json.dumps({'ok': False, 'thong_bao': 'Chỉ trang của webapp trên chính máy này mới được gửi lệnh.'},
                                                                        ensure_ascii=False).encode('utf-8'))
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    ma, kq = vo_app.lam(str((yc if isinstance(yc, dict) else {}).get('viec') or ''), cfg)
                    return self._gui(ma, LOAI['.json'], json.dumps(kq, ensure_ascii=False).encode('utf-8'))
                if path == '/api/ai-giai-thich':
                    try:
                        u = self._ai_user()
                        cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                        def doc_phieu(ident):
                            p = phieu_ke_hoach.doc(_out(cfg), ident)
                            return {**p, 'cham': _cham_phieu(cfg, p)} if p else None
                        kq = ai_evidence.analyze(Path(cau_hinh).resolve().parent, cfg, _out(cfg), u, yc, phieu_fn=doc_phieu)
                        return self._gui(200, LOAI['.json'], json.dumps(kq, ensure_ascii=False, default=str).encode('utf-8'), dich_noi_dung=False)
                    except (ai_store.StoreError, ai_providers.ProviderError) as e:
                        return self._gui(getattr(e, 'status', 400), LOAI['.json'], json.dumps({'ok': False, 'chan': [str(e)]}, ensure_ascii=False).encode('utf-8'))
                if path == '/api/phieu' and self.headers.get('X-So-Cong-Khai') == '1':   # lập, sửa, kiểm, theo dõi phiếu kế hoạch; không đặt lệnh
                    yc = yc if isinstance(yc, dict) else {}
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    viec, out = str(yc.get('viec') or ''), _out(cfg)
                    try:
                        if viec == 'tao':
                            kq = phieu_ke_hoach.tao(out, yc.get('phieu') or {})
                        elif viec == 'sua':
                            kq = phieu_ke_hoach.sua_lenh(out, str(yc.get('id') or ''), yc.get('phieu') or {})
                        elif viec == 'kiem':                                # kiểm bằng chính số trong phiếu, máy chủ tính, không nhận kết quả từ trang
                            p = phieu_ke_hoach.doc(out, str(yc.get('id') or ''))
                            if p is None:
                                raise KeyError('phiếu')
                            lenh = {'ma': p['ma'], 'chieu': p['chieu'], 'vao': p['vao'], 'sl': p['sl'], 'tp': (p['tp'] or [None])[0], 'rui_ro_pct': p['rui_ro_pct']}
                            kq = phieu_ke_hoach.gan_kiem(out, p['id'], kiem_lenh.kiem(cfg, bang, lenh))
                        elif viec == 'theo_doi':
                            kq = phieu_ke_hoach.bat_dau_theo_doi(out, str(yc.get('id') or ''))
                        elif viec == 'dung_ngoai':
                            kq = phieu_ke_hoach.dung_ngoai(out, str(yc.get('id') or ''), str(yc.get('ly_do') or ''))
                        elif viec == 'ghi_chu':
                            kq = phieu_ke_hoach.ghi_chu(out, str(yc.get('id') or ''), str(yc.get('noi_dung') or ''),
                                                        yc.get('tag') if isinstance(yc.get('tag'), list) else [], str(yc.get('loai') or 'ghi_chu'),
                                                        tuan_thu=str(yc.get('tuan_thu') or ''))
                        elif viec == 'anh':
                            kq = phieu_ke_hoach.luu_anh(out, str(yc.get('id') or ''), str(yc.get('anh') or ''))
                        else:
                            raise ValueError('việc không hợp lệ')
                    except KeyError:
                        return self._gui(404, LOAI['.json'], json.dumps({'ok': False, 'thong_bao': 'Không có phiếu này.'}, ensure_ascii=False).encode('utf-8'))
                    except ValueError as e:
                        return self._gui(400, LOAI['.json'], json.dumps({'ok': False, 'thong_bao': str(e)}, ensure_ascii=False).encode('utf-8'))
                    return self._gui(200, LOAI['.json'], json.dumps({'ok': True, 'phieu': kq}, ensure_ascii=False, default=str).encode('utf-8'))
                if urlparse(self.path).path == '/api/cac-tai-khoan' and self.headers.get('X-So-Cong-Khai') == '1':
                    viec = yc.get('viec')
                    if viec == 'them':
                        ok, nhan = nhieu_tai_khoan.them(str(yc.get('duong', '')), str(yc.get('ten', '')))
                        if ok:
                            nhieu_tai_khoan.doc_lai_ngay()
                    elif viec == 'xoa':
                        ident = yc.get('id')
                        if isinstance(ident, bool) or not isinstance(ident, int) or ident <= 0:
                            raise bao_mat_http.YeuCauLoi(400, 'Mã tài khoản phải là số nguyên dương.')
                        ok, nhan = nhieu_tai_khoan.xoa(ident)
                    elif viec == 'doc_lai':
                        nhieu_tai_khoan.doc_lai_ngay()
                        ok, nhan = True, 'Đang đọc lại mọi tài khoản; trang tự cập nhật sau ít giây.'
                    else:
                        ok, nhan = False, 'Yêu cầu không hợp lệ.'
                    return self._gui(200 if ok else 400, LOAI['.json'], json.dumps({'ok': ok, 'ly_do': nhan}, ensure_ascii=False).encode('utf-8'))
                if urlparse(self.path).path == '/api/kiem-tin-hieu' and self.headers.get('X-So-Cong-Khai') == '1':   # dò tín hiệu dán vào trên giá thật
                    yc = yc if isinstance(yc, dict) else {}
                    try:
                        mg, cho, giu = float(yc.get('mui_gio', 7)), float(yc.get('cho_gio', 4)), float(yc.get('giu_ngay', 5))
                        if not (-12 <= mg <= 14 and 0 < cho <= 72 and 0 < giu <= 30):
                            raise ValueError('tùy chọn ngoài khoảng cho phép')
                        ma0 = str(yc.get('ma_mac_dinh') or 'XAUUSD')
                        if not re.fullmatch(r'[A-Z0-9]{3,10}', ma0):
                            raise ValueError('mã mặc định không hợp lệ')
                        cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                        kq = kiem_tin_hieu.kiem(cfg, str(yc.get('van_ban') or ''), mg, cho, giu, bool(yc.get('ve_hoa_von')), ma0)
                    except (ValueError, TypeError) as e:
                        kq = {'ok': False, 'ly_do': f'Chưa kiểm được: {e}.', 'ds': [], 'loi': []}
                    return self._gui(200, LOAI['.json'], json.dumps(kq, ensure_ascii=False, default=str).encode('utf-8'))
                if urlparse(self.path).path == '/api/mau-chi-bao' and self.headers.get('X-So-Cong-Khai') == '1':   # lưu mẫu chỉ báo và yêu thích
                    try:
                        root = Path(cau_hinh).resolve().parent
                        u = tai_khoan_chart.hien_tai(self.headers.get('Cookie'), root)
                        if not u:
                            return self._gui(401, LOAI['.json'], b'{"ok":false,"dang_nhap":false}')
                        if self.headers.get('X-Chart-Owner') != u['id']:
                            return self._gui(409, LOAI['.json'], b'{"ok":false,"doi_tai_khoan":true}')
                        if not isinstance(yc, dict) or 'ban_co_so' not in yc or (yc['ban_co_so'] is not None and (type(yc['ban_co_so']) is not int or yc['ban_co_so'] < 1)):
                            raise ValueError('thiếu hoặc sai phiên bản mẫu cơ sở')
                        kq = {'ok': True, 'chu': u['id'], **mau_chi_bao.luu(yc.get('mau'), yc.get('sao'), root, chu=u['id'], ban_co_so=yc['ban_co_so'])}
                    except mau_chi_bao.XungDot as e:
                        return self._gui(409, LOAI['.json'], json.dumps({'ok': False, 'xung_dot': True, 'chu': u['id'], **e.hien_tai}, ensure_ascii=False).encode('utf-8'), dich_noi_dung=False)
                    except (ValueError, AttributeError) as e:
                        kq = {'ok': False, 'ly_do': f'Chưa lưu: {e}.'}
                    return self._gui(200 if kq['ok'] else 400, LOAI['.json'], json.dumps(kq, ensure_ascii=False).encode('utf-8'), dich_noi_dung=False)
                if urlparse(self.path).path == '/api/hinh-ve' and self.headers.get('X-So-Cong-Khai') == '1':   # lưu hình vẽ của một mã
                    try:
                        root = Path(cau_hinh).resolve().parent
                        u = tai_khoan_chart.hien_tai(self.headers.get('Cookie'), root)
                        if not u:
                            return self._gui(401, LOAI['.json'], b'{"ok":false,"dang_nhap":false}')
                        if self.headers.get('X-Chart-Owner') != u['id']:
                            return self._gui(409, LOAI['.json'], b'{"ok":false,"doi_tai_khoan":true}')
                        if 'ban_co_so' not in yc or (yc['ban_co_so'] is not None and (type(yc['ban_co_so']) is not int or yc['ban_co_so'] < 1)):
                            raise ValueError('thiếu hoặc sai phiên bản cơ sở')
                        ma = str(yc.get('ma', ''))
                        if yc.get('viec') == 'khoi_phuc':
                            if type(yc.get('ban')) is not int:
                                raise ValueError('sai phiên bản phục hồi')
                            data = hinh_ve.khoi_phuc(ma, yc['ban'], yc['ban_co_so'], root, u['id'])
                        else:
                            data = {'ds': yc.get('ds'), **hinh_ve.luu(ma, yc.get('ds'), root, chu=u['id'], ban_co_so=yc['ban_co_so'])}
                        kq = {'ok': True, 'chu': u['id'], **data}
                    except hinh_ve.XungDot as e:
                        return self._gui(409, LOAI['.json'], json.dumps({'ok': False, 'xung_dot': True, **e.hien_tai}, ensure_ascii=False).encode('utf-8'), dich_noi_dung=False)
                    except hinh_ve.KhoLoi as e:
                        return self._gui(503, LOAI['.json'], json.dumps({'ok': False, 'ly_do': str(e)}, ensure_ascii=False).encode('utf-8'))
                    except (ValueError, AttributeError) as e:
                        kq = {'ok': False, 'ly_do': f'Chưa lưu: {e}.'}
                    return self._gui(200 if kq['ok'] else 400, LOAI['.json'], json.dumps(kq, ensure_ascii=False).encode('utf-8'), dich_noi_dung=False)
                if urlparse(self.path).path == '/api/canh-bao-ve' and self.headers.get('X-So-Cong-Khai') == '1':   # đặt, xóa cảnh báo trên đường vẽ; nối Telegram riêng
                    root = Path(cau_hinh).resolve().parent
                    u = tai_khoan_chart.hien_tai(self.headers.get('Cookie'), root)
                    if not u:
                        return self._gui(401, LOAI['.json'], b'{"ok":false,"dang_nhap":false}')
                    if self.headers.get('X-Chart-Owner') != u['id']:
                        return self._gui(409, LOAI['.json'], b'{"ok":false,"doi_tai_khoan":true}')
                    store = root if u['chu'] else canh_bao_ve.kho_rieng(u['id'], root)
                    yc = yc if isinstance(yc, dict) else {}
                    viec, kq = yc.get('viec'), {}
                    if viec == 'them':
                        ok, nhan, a = canh_bao_ve.them(yc, store)
                        kq = {'canh_bao': a}
                    elif viec == 'xoa':
                        ok = canh_bao_ve.xoa(str(yc.get('id', '')), store)
                        nhan = 'Đã xóa cảnh báo.' if ok else 'Không thấy cảnh báo này.'
                    elif viec == 'xoa_ma':
                        so = canh_bao_ve.xoa_ma(str(yc.get('ma', '')), store)
                        ok, nhan = True, f'Đã xóa {so} cảnh báo.'
                    elif viec == 'tao_ma_noi':
                        ok, nhan, kq = True, 'Gửi mã trong chat riêng với bot rồi bấm Kiểm tra.', canh_bao_ve.tao_ma_noi(store)
                    elif viec == 'kiem_ma_noi':
                        ok, nhan = canh_bao_ve.kiem_ma_noi(store)
                    elif viec == 'bo_chat':
                        canh_bao_ve.bo_chat(store)
                        ok, nhan = True, 'Đã ngắt Telegram riêng; cảnh báo chỉ còn báo trong trang.'
                    else:
                        ok, nhan = False, 'Yêu cầu không hợp lệ.'
                    return self._gui(200 if ok else 400, LOAI['.json'], json.dumps({'ok': ok, 'chu': u['id'], 'ly_do': nhan, **kq}, ensure_ascii=False).encode('utf-8'), dich_noi_dung=False)
                if urlparse(self.path).path == '/api/do-lai' and self.headers.get('X-So-Cong-Khai') == '1':     # nút "Đo lại ngay"
                    bd = do_lai.chay_nen()
                    return self._gui(200, LOAI['.json'], json.dumps({'ok': bd, 'ly_do': 'Đang đo lại ở nền, khoảng một phút.' if bd else ('Đang đo rồi.' if do_lai.TT['dang'] else 'Máy này không có công cụ đo lại.')}, ensure_ascii=False).encode('utf-8'))
                if urlparse(self.path).path == '/api/telegram' and self.headers.get('X-So-Cong-Khai') == '1':
                    viec, ds = yc.get('viec'), None
                    if viec == 'luu':
                        ok, nhan = telegram_nhom.luu_cai(yc)
                    elif viec == 'che_do':
                        ok, nhan = telegram_nhom.doi_che_do(str(yc.get('che_do', '')))
                    elif viec == 'thu':
                        c = telegram_nhom.cai()
                        if c['che_do'] != 'gui':
                            ok, nhan = False, 'Chỉ gửi tin thử khi đang ở chế độ Gửi thật.'
                        else:
                            kq = telegram_nhom.gui('🔔 Tin thử từ webapp: nhóm đã nối. Từ giờ tín hiệu, kết quả từng lệnh, tin USD mạnh sắp ra và tổng kết '
                                                   'ngày sẽ được gửi vào đây.\n<i>' + telegram_nhom.MIEN + '</i>', 'thu', c)
                            ok, nhan = kq['ok'], ('Đã gửi tin thử; mở nhóm để xem.' if kq['ok'] else f'Chưa gửi được: {kq["loi"]}')
                    elif viec == 'phan_tich':                                   # đăng (hoặc soạn xem trước) một bài phân tích vàng ngay
                        kq = telegram_nhom.dang_phan_tich(json.loads(Path(cau_hinh).read_text(encoding='utf-8')))
                        ok, nhan = kq['ok'], kq['ly_do']
                    elif viec == 'tim_nhom':
                        ok, ds = telegram_nhom.tim_nhom()
                        nhan, ds = (None, ds) if ok else (ds, None)
                    else:
                        ok, nhan = False, 'Yêu cầu không hợp lệ.'
                    return self._gui(200 if ok else 400, LOAI['.json'], json.dumps({'ok': ok, 'ly_do': nhan, 'ds': ds}, ensure_ascii=False).encode('utf-8'))
                if urlparse(self.path).path == '/api/sao-luu' and self.headers.get('X-So-Cong-Khai') == '1':
                    if yc.get('viec') == 'chay':
                        ok = sao_luu.chay_nen()
                        nhan = 'Đang sao lưu; xong sau vài giây.' if ok else 'Đang có một lần sao lưu chạy.'
                    elif yc.get('viec') == 'dat_noi':
                        ok, nhan = sao_luu.dat_noi(str(yc.get('noi', '')))
                        if ok:
                            sao_luu.chay_nen()
                            nhan += ' Đang tạo bản đầu tiên ở đó.'
                    else:
                        ok, nhan = False, 'Yêu cầu không hợp lệ.'
                    return self._gui(200 if ok else 400, LOAI['.json'], json.dumps({'ok': ok, 'ly_do': nhan}, ensure_ascii=False).encode('utf-8'))
                if urlparse(self.path).path == '/api/gia-su' and self.headers.get('X-So-Cong-Khai') == '1':   # một lượt của buổi học
                    try:
                        self._ai_user(owner=True)
                    except ai_store.StoreError as e:
                        return self._gui(e.status, LOAI['.json'], json.dumps({'ok': False, 'chan': [str(e)], 'thong_bao': str(e)}, ensure_ascii=False).encode('utf-8'))
                    from . import gia_su                                       # noqa: PLC0415
                    cfg = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
                    lang_gs = dich.ngon_ngu(self.headers.get('Cookie'))
                    if not yc.get('luong'):
                        kq = gia_su.hoi(cfg, _out(cfg), yc.get('phien'), str(yc.get('chu_de') or ''), str(yc.get('cau') or ''), lang=lang_gs)
                        return self._gui(200 if kq['ok'] else 400, LOAI['.json'], json.dumps(kq, ensure_ascii=False, default=str).encode('utf-8'))
                    self.send_response(200)                                    # luồng: chữ của gia sư hiện dần, sự kiện cuối là kết quả đầy đủ
                    self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self._tieu_de_bao_ve()
                    self.end_headers()
                    con = {'mo': True}

                    def day(obj: dict) -> None:
                        if not con['mo']:
                            return
                        try:
                            self.wfile.write(('data: ' + json.dumps(obj, ensure_ascii=False, default=str) + '\n\n').encode('utf-8'))
                            self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                            con['mo'] = False                                  # trang đã đóng: gia sư vẫn viết xong và lưu buổi học
                    kq = gia_su.hoi(cfg, _out(cfg), yc.get('phien'), str(yc.get('chu_de') or ''), str(yc.get('cau') or ''), lang=lang_gs,
                                    khi_chu=lambda t: day({'chu': t}))
                    day({'xong': True, **kq})
                    return
                return self._gui(404, 'text/plain; charset=utf-8', 'Không có trang này.'.encode('utf-8'))
            except bao_mat_http.YeuCauLoi as e:
                bao_mat_http.bo_than_con_lai(self)
                self._gui(e.ma, LOAI['.json'], json.dumps({'ok': False, 'ly_do': str(e)}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:                                  # noqa: BLE001
                self._gui(500, 'text/plain; charset=utf-8', f'Lỗi khi hỏi AI: {type(e).__name__}: {e}'.encode('utf-8'))

        def log_message(self, *a):                                  # im lặng: không in mỗi lượt tải trang
            pass

    server = _MayChuDocQuyen((host, port), H)
    server.local_build = local_runtime.build_id()
    server.runtime_mode = 'preview'
    server.luong_gia = luong_gia.LuongGia(lambda g, tf, ma: song.tick(g, tf, ma), nhip=NHIP_TICK)
    return server


def khoi_dong(cau_hinh: str, port: int = local_runtime.PORT) -> ThreadingHTTPServer:
    """Mở cổng rồi bật mọi vòng nền (Telegram, nhật ký, sao lưu, cảnh báo, bảng giá…) và làm nóng phần phân tích; trả máy chủ CHƯA phục vụ.
    Dùng chung cho dòng lệnh (main) và vỏ app (app.py): nơi gọi tự chạy serve_forever. Ở đây không đổi luồng xuất chuẩn, không in gì và không
    giữ máy thức, vì vỏ app chạy không có cửa sổ dòng lệnh. Cổng mở TRƯỚC mọi vòng nền: bản thứ hai chết ở bước mở cổng (xem _MayChuDocQuyen)."""
    instance = local_runtime.InstanceLock(cau_hinh).acquire()
    try:
        vong = tao_vong_canh(cau_hinh)
        bang = thi_truong.bang(lambda: json.loads(Path(cau_hinh).read_text(encoding='utf-8')))
        srv = tao_may_chu(cau_hinh, port=port, vong=vong, bang=bang, ghi_thieu=True)
    except BaseException:
        instance.release()
        raise
    srv.instance_lock = instance
    srv.runtime_mode = 'full'
    if vong is not None:
        vong.start()
    nhieu_tai_khoan.VONG = nhieu_tai_khoan.VongTaiKhoan()                # đọc các tài khoản đã nối (mỗi cái một tiến trình riêng, chỉ đọc)
    nhieu_tai_khoan.VONG.start()
    from . import doi_chieu_mt5
    doi_chieu_mt5.VongDoiChieu(lambda: json.loads(Path(cau_hinh).read_text(encoding='utf-8')), cau_hinh).start()
    telegram_nhom.VongTelegram(lambda: json.loads(Path(cau_hinh).read_text(encoding='utf-8')), dia_chi=f'http://127.0.0.1:{port}').start()   # nhóm Telegram (mặc định chỉ xem trước)
    lay_gia = canh_bao_ve.lay_tu_mt5(lambda: json.loads(Path(cau_hinh).read_text(encoding='utf-8')))   # đọc thẳng nến và Bid từ MT5 (nhẹ)
    canh_bao_ve.VONG = canh_bao_ve.VongCanhVe(lay_gia, goc=Path(cau_hinh).resolve().parent)  # kiểm đúng kho của cấu hình đang mở
    canh_bao_ve.VONG.start()
    sao_luu.VongSaoLuu().start()                                     # mỗi ngày một bản sao toàn bộ hệ thống
    do_lai.VongDoLai().start()                                       # đo lại trên dữ liệu mới, mỗi tháng một lần
    if bang is not None:                                           # bảng giá trực tiếp cho trang Thị trường và Công cụ
        bang.start()
    nk = (json.loads(Path(cau_hinh).read_text(encoding='utf-8')).get('nhat_ky') or {})
    if nk.get('bat'):                                              # vòng nền ghi điểm vào, kể cả khi không ai mở trang
        nhat_ky.VongGhi(lambda: json.loads(Path(cau_hinh).read_text(encoding='utf-8')), nk.get('giay', 60)).start()
    if (json.loads(Path(cau_hinh).read_text(encoding='utf-8')).get('lich_mang') or {}).get('bat', True):   # lịch tin nhiều đồng tiền từ mạng (chỉ để hiển thị)
        lich_mang.VongLich(lambda: json.loads(Path(cau_hinh).read_text(encoding='utf-8')), HERE).start()
    cfg0 = json.loads(Path(cau_hinh).read_text(encoding='utf-8'))
    if (cfg0.get('tin_tuc') or {}).get('bat', True):                       # tin tức RSS, 5 phút một lần
        tin_tuc.VongTin(lambda: json.loads(Path(cau_hinh).read_text(encoding='utf-8')), HERE).start()
    if (cfg0.get('tam_ly') or {}).get('bat', True):                        # COT của CFTC và chỉ số sợ hãi/tham lam
        tam_ly.VongTamLy(lambda: json.loads(Path(cau_hinh).read_text(encoding='utf-8')), HERE).start()
    def lam_nong():                                                # lần phân tích đầu phải nạp mã luật và thư viện (khoảng 3 giây): làm trước, để lần bấm đầu của người dùng không phải chờ
        try:
            phan_tich.phan_tich(json.loads(Path(cau_hinh).read_text(encoding='utf-8')))
        except Exception:                                          # noqa: BLE001 - làm nóng hỏng thì lần bấm đầu chậm như cũ, không hơn
            pass
    threading.Thread(target=lam_nong, name='lam-nong', daemon=True).start()
    return srv


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='so_cong_khai.web', description=__doc__)
    ap.add_argument('--cau-hinh', default=str(HERE / 'cau-hinh.json'))
    ap.add_argument('--port', type=int, default=local_runtime.PORT)
    a = ap.parse_args(argv)
    mau = duong.goc_chuong_trinh() / 'cau-hinh.mau.json'
    if not Path(a.cau_hinh).exists() and mau.exists():               # lần chạy đầu của bản chia sẻ: tạo cấu hình từ bản mẫu
        Path(a.cau_hinh).write_text(mau.read_text(encoding='utf-8'), encoding='utf-8')
    srv = khoi_dong(a.cau_hinh, a.port)                              # mở cổng (bản thứ hai chết ở đây) rồi bật mọi vòng nền
    sys.stdout.reconfigure(encoding='utf-8')
    print(f'Sổ công khai đang chạy tại http://127.0.0.1:{srv.server_address[1]}  (nhấn Ctrl+C để dừng)', flush=True)
    cfg0 = json.loads(Path(a.cau_hinh).read_text(encoding='utf-8'))
    if cfg0.get('giu_may_thuc'):                                   # máy không tự ngủ trong lúc webapp chạy (luồng chính sống suốt đời webapp)
        from . import giu_thuc                                     # noqa: PLC0415
        print('Giữ máy thức: ' + ('đã bật' if giu_thuc.bat() else f'không bật được ({giu_thuc.TT["loi"]})'), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
