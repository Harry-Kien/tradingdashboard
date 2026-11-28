"""Bài kiểm cho so_cong_khai.app (vỏ app Windows): chỉ các hàm thuần và đường --mo-dun. Không nhập webview hay pystray (Python chính của máy
không có hai thư viện đó), không mở cửa sổ, không khởi động máy chủ hay vòng nền nào. Mọi thư mục ghi là thư mục tạm."""
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
import unittest.mock as mock
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import app  # noqa: E402


def _ba_cong_trong() -> int:
    """Một cổng p mà p, p+1, p+2 đều đang trống (để kiểm thứ tự thử cổng của chon_cong)."""
    for _ in range(100):
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            p = s.getsockname()[1]
        if p + 2 <= 65535 and all(app._trong(c) for c in (p, p + 1, p + 2)):
            return p
    raise unittest.SkipTest('không tìm được ba cổng trống liền nhau')


class AppTest(unittest.TestCase):
    def test_chuyen_dau_ra_khi_stdout_none(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.object(sys, 'stdout', None), mock.patch.object(sys, 'stderr', None):
            app.chuyen_dau_ra(Path(t))
            print('xin chào', flush=True)
            sys.stdout.flush()
            self.assertIn('xin chào', (Path(t) / 'app.log').read_text(encoding='utf-8'))
            sys.stdout.close()

    def test_chuyen_dau_ra_cat_tep_lon(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.object(sys, 'stdout', None), mock.patch.object(sys, 'stderr', None):
            log = Path(t) / 'app.log'
            log.write_bytes(b'x' * (3 * 1024 * 1024))
            app.chuyen_dau_ra(Path(t))
            sys.stdout.close()
            self.assertLess(log.stat().st_size, 1024 * 1024)

    def test_chuyen_dau_ra_giu_nguyen_khi_co_luong(self):
        with tempfile.TemporaryDirectory() as t:
            truoc = (sys.stdout, sys.stderr)
            app.chuyen_dau_ra(Path(t))
            self.assertEqual((sys.stdout, sys.stderr), truoc)
            self.assertFalse((Path(t) / 'app.log').exists())

    def test_chon_cong_khi_bi_chiem(self):
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            ban = s.getsockname()[1]
            c = app.chon_cong(ban)
            self.assertNotEqual(c, ban)
            self.assertGreater(c, 0)

    def test_chon_cong_khi_trong(self):
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            c = s.getsockname()[1]
        self.assertEqual(app.chon_cong(c), c)

    def test_ung_vien_theo_thu_tu_r7(self):
        self.assertEqual(app.ung_vien(8765), list(range(8765, 8776)))
        self.assertEqual(app.ung_vien(65534), [65534, 65535])

    def test_chon_cong_thu_cong_ke_tiep_r7(self):
        p = _ba_cong_trong()
        with socket.socket() as a, socket.socket() as b:
            a.bind(('127.0.0.1', p))
            b.bind(('127.0.0.1', p + 1))
            self.assertEqual(app.chon_cong(p), p + 2)

    def test_chon_cong_het_ung_vien_thi_he_thong_cap_r7(self):
        hoi = []
        with mock.patch.object(app, '_trong', side_effect=lambda c: hoi.append(c) or False):
            c = app.chon_cong(8765)
        self.assertEqual(hoi, list(range(8765, 8776)))
        self.assertNotIn(c, range(8765, 8776))
        self.assertGreater(c, 0)

    def test_tep_chay(self):
        self.assertEqual(app.tep_chay(Path('x')), Path('x') / 'du-lieu' / 'app-chay.json')

    def test_tep_chay_cu_thi_khoi_dong_moi(self):
        with tempfile.TemporaryDirectory() as t:
            g = Path(t)
            (g / 'du-lieu').mkdir()
            app.tep_chay(g).write_text('{"cong": 1, "pid": 999999}', encoding='utf-8')
            self.assertIsNone(app.ban_dang_chay(g, goi=mock.Mock(side_effect=OSError)))
            app.tep_chay(g).write_text('hỏng', encoding='utf-8')
            self.assertIsNone(app.ban_dang_chay(g, goi=mock.Mock(return_value=200)))

    def test_ban_dang_chay_tra_cong(self):
        with tempfile.TemporaryDirectory() as t:
            g = Path(t)
            (g / 'du-lieu').mkdir()
            app.tep_chay(g).write_text('{"cong": 51234}', encoding='utf-8')
            goi = mock.Mock(return_value=200)
            self.assertEqual(app.ban_dang_chay(g, goi=goi), 51234)
            goi.assert_called_once_with(51234)

    def test_ban_dang_chay_sai_dinh_dang_hay_khong_200(self):
        with tempfile.TemporaryDirectory() as t:
            g = Path(t)
            goi = mock.Mock(return_value=200)
            self.assertIsNone(app.ban_dang_chay(g, goi=goi))                       # chưa có tệp
            (g / 'du-lieu').mkdir()
            for sai in ('[1]', '{"cong": "51234"}', '{"cong": true}', '{"cong": 0}', '{"cong": 70000}', '{}'):
                app.tep_chay(g).write_text(sai, encoding='utf-8')
                self.assertIsNone(app.ban_dang_chay(g, goi=goi), sai)
            goi.assert_not_called()
            app.tep_chay(g).write_text('{"cong": 51234, "pid": 1}', encoding='utf-8')
            self.assertIsNone(app.ban_dang_chay(g, goi=mock.Mock(return_value=403)))

    def test_trang_dau(self):
        with tempfile.TemporaryDirectory() as t:
            g = Path(t)
            self.assertEqual(app.trang_dau(g), '/bat-dau')
            self.assertTrue((g / 'du-lieu' / 'app-da-mo.json').is_file())
            self.assertEqual(app.trang_dau(g), '/')

    def test_dich_mo(self):
        b = {'ma': 'XAUUSD.r', 'tf': 'M15', 'luc': 1000.0}
        self.assertEqual(app.dich_mo(b, 1300.0), '/bieu-do?ma=XAUUSD.r&tf=M15')
        self.assertEqual(app.dich_mo(b, 1700.0), '')
        self.assertEqual(app.dich_mo(None, 1300.0), '')
        self.assertEqual(app.dich_mo({'ma': 'A B&C', 'tf': 'H1', 'luc': 1000.0}, 1001.0), '/bieu-do?ma=A%20B%26C&tf=H1')

    def test_dich_mo_bien(self):
        b = {'ma': 'XAUUSD', 'tf': 'H1', 'luc': 1000.0}
        self.assertEqual(app.dich_mo(b, 1600.0), '/bieu-do?ma=XAUUSD&tf=H1')        # đúng 600 giây vẫn tính
        self.assertEqual(app.dich_mo({**b, 'luc': float('nan')}, 1001.0), '')
        self.assertEqual(app.dich_mo({**b, 'luc': None}, 1001.0), '')
        self.assertEqual(app.dich_mo({**b, 'ma': ''}, 1001.0), '')

    def test_co_webview2(self):
        cac_khoa = []

        def doc(goc, khoa):
            cac_khoa.append((goc, khoa))
            return '158.0.4370.33' if goc == 'HKCU' else None
        self.assertTrue(app.co_webview2(doc))
        self.assertIn(('HKLM', r'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'), cac_khoa)
        self.assertFalse(app.co_webview2(lambda goc, khoa: None))
        self.assertFalse(app.co_webview2(lambda goc, khoa: ''))
        self.assertFalse(app.co_webview2(lambda goc, khoa: '0.0.0.0'))
        self.assertFalse(app.co_webview2(mock.Mock(side_effect=OSError)))

    def test_doc_tu_thoat_r13(self):
        self.assertIsNone(app.doc_tu_thoat([]))
        self.assertEqual(app.doc_tu_thoat(['--tu-thoat', '45']), 45.0)
        self.assertEqual(app.doc_tu_thoat(['--tu-thoat', '0.5']), 0.5)
        for sai in (['--tu-thoat'], ['--tu-thoat', '0'], ['--tu-thoat', '-3'], ['--tu-thoat', 'abc'], ['--tu-thoat', 'nan'], ['--tu-thoat', 'inf']):
            with self.assertRaises(ValueError, msg=str(sai)):
                app.doc_tu_thoat(sai)

    def test_tu_thoat_sai_thi_tra_2_truoc_khi_dung_du_lieu(self):
        with mock.patch.object(app, 'chuyen_dau_ra') as cd, mock.patch.object(app.duong, 'chuan_bi') as cb:
            self.assertEqual(app.main(['--tu-thoat', '0']), 2)
        cd.assert_not_called()
        cb.assert_not_called()

    def test_mo_dun_la_bi_tu_choi(self):
        self.assertEqual(app.main(['--mo-dun', 'os']), 2)

    def test_mo_dun_chi_nhan_goi_so_cong_khai(self):
        with mock.patch.object(app.runpy, 'run_module') as chay, mock.patch.object(app, 'chuyen_dau_ra') as cd:
            for sai in ([], ['so_cong_khai'], ['so_cong_khai.'], ['so_cong_khaix.web'], ['so_cong_khai..web'], ['so_cong_khai.web/x'], ['../so_cong_khai.web']):
                self.assertEqual(app.main(['--mo-dun', *sai]), 2, sai)
        chay.assert_not_called()
        cd.assert_not_called()

    def test_mo_dun_chay_va_tra_ma_thoat(self):
        with mock.patch.object(sys, 'argv', ['cu']), mock.patch.object(app, 'chuyen_dau_ra') as cd, \
                mock.patch.object(app.duong, 'chuan_bi') as cb, mock.patch.object(app, '_lay_khoa') as kh:
            with mock.patch.object(app.runpy, 'run_module', return_value={}) as chay:
                self.assertEqual(app.main(['--mo-dun', 'so_cong_khai.cong_cu', 'a', '--b']), 0)
                chay.assert_called_once_with('so_cong_khai.cong_cu', run_name='__main__')
                self.assertEqual(sys.argv, ['so_cong_khai.cong_cu', 'a', '--b'])
            with mock.patch.object(app.runpy, 'run_module', side_effect=SystemExit(3)):
                self.assertEqual(app.main(['--mo-dun', 'so_cong_khai.cong_cu']), 3)
            with mock.patch.object(app.runpy, 'run_module', side_effect=SystemExit(None)):
                self.assertEqual(app.main(['--mo-dun', 'so_cong_khai.cong_cu']), 0)
        cd.assert_not_called()                               # chế độ thợ không đụng nhật ký, thư mục dữ liệu hay mutex
        cb.assert_not_called()
        kh.assert_not_called()

    def test_khong_nhap_thu_vien_giao_dien_o_dau_tep(self):
        nguon = (GOC / 'so_cong_khai' / 'app.py').read_text(encoding='utf-8')
        for dong in nguon.splitlines():
            if dong.startswith(('import ', 'from ')):
                self.assertNotIn('webview', dong)
                self.assertNotIn('pystray', dong)
                self.assertNotIn('PIL', dong)

    def test_chu_co_dinh(self):
        self.assertEqual(app.TEN_KHOA, 'HarryGoldResearch.App')
        self.assertEqual(app.CHU_KHONG_PHAN_HOI, 'Harry · Gold Research đang chạy nhưng không phản hồi. Hãy thoát nó ở khay hệ thống rồi mở lại.')
        self.assertEqual(app.CHU_BAO_KHAY, 'Harry · Gold Research vẫn chạy ở khay hệ thống để cảnh báo giá hoạt động. Bấm chuột phải vào biểu tượng để thoát.')
        self.assertEqual(app.chu_loi(Path('C:/x/app.log')), f'Không khởi động được. Chi tiết nằm trong {Path("C:/x/app.log")}')

    def test_tep_chay_ghi_doc_lai(self):
        with tempfile.TemporaryDirectory() as t:
            g = Path(t)
            app.ghi_tep_chay(g, 51234)
            d = json.loads(app.tep_chay(g).read_text(encoding='utf-8'))
            self.assertEqual(d['cong'], 51234)
            self.assertIsInstance(d['pid'], int)


class MoMayChuTest(unittest.TestCase):
    """Bước 4 và R7, R11: web.khoi_dong được thay bằng giả, không máy chủ hay vòng nền nào chạy."""

    def setUp(self):
        from so_cong_khai import web
        self.web = web
        p = mock.patch.object(sys, 'stdout', io.StringIO())
        p.start()
        self.addCleanup(p.stop)

    def test_bo_qua_cong_da_thay_ban(self):
        srv = mock.Mock(server_address=('127.0.0.1', 8771))
        with mock.patch.object(app, '_trong', side_effect=lambda c: c >= 8771), \
                mock.patch.object(self.web, 'khoi_dong', return_value=srv) as kd:
            self.assertEqual(app._mo_may_chu(Path('cau-hinh.json')), (srv, 8771))
        kd.assert_called_once_with('cau-hinh.json', 8771)

    def test_thua_cuoc_dua_gianh_cong_thi_thu_cong_ke_r11(self):
        srv = mock.Mock(server_address=('127.0.0.1', 8770))
        with mock.patch.object(app, '_trong', return_value=True), \
                mock.patch.object(self.web, 'khoi_dong', side_effect=[OSError('bận'), srv]) as kd:
            self.assertEqual(app._mo_may_chu(Path('c.json')), (srv, 8770))
        self.assertEqual([c.args[1] for c in kd.call_args_list], [8769, 8770])

    def test_het_ung_vien_thi_he_thong_cap(self):
        srv = mock.Mock(server_address=('127.0.0.1', 50001))
        with mock.patch.object(app, '_trong', return_value=False), mock.patch.object(app, '_cong_he_thong', return_value=50001), \
                mock.patch.object(self.web, 'khoi_dong', return_value=srv) as kd:
            self.assertEqual(app._mo_may_chu(Path('c.json')), (srv, 50001))
        kd.assert_called_once_with('c.json', 50001)

    def test_khong_cong_nao_dung_duoc_thi_nem(self):
        with mock.patch.object(app, '_trong', return_value=True), mock.patch.object(app, '_cong_he_thong', return_value=50001), \
                mock.patch.object(self.web, 'khoi_dong', side_effect=OSError('bận')) as kd:
            with self.assertRaises(OSError):
                app._mo_may_chu(Path('c.json'))
        self.assertEqual(kd.call_count, 11 + 3)


class MainTest(unittest.TestCase):
    """main với mọi bước nặng thay bằng giả: không mutex thật, không máy chủ, không hộp thoại. Gốc dữ liệu là thư mục tạm (HGR_DU_LIEU)."""

    def test_loi_khoi_dong_ghi_log_hop_thoai_tra_1(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(os.environ, {'HGR_DU_LIEU': t}), \
                mock.patch.object(app, '_lay_khoa', return_value=True), \
                mock.patch.object(app, '_mo_may_chu', side_effect=RuntimeError('hỏng thử')), \
                mock.patch.object(app, '_hop_thoai') as hop, \
                mock.patch.object(sys, 'stdout', io.StringIO()), mock.patch.object(sys, 'stderr', io.StringIO()):
            g = Path(t)
            (g / 'du-lieu').mkdir()
            app.tep_chay(g).write_text('{"cong": 8765, "pid": 1}', encoding='utf-8')     # tệp của một bản đã chết
            self.assertEqual(app.main([]), 1)
            hop.assert_called_once_with(app.chu_loi(g / 'app.log'))
            self.assertIn('RuntimeError: hỏng thử', (g / 'app.log').read_text(encoding='utf-8'))
            self.assertFalse(app.tep_chay(g).exists())                                   # giữ được mutex thì tệp chạy cũ là rác: xóa ngay

    def test_ban_khac_dang_chay_tra_0(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(os.environ, {'HGR_DU_LIEU': t}), \
                mock.patch.object(app, '_lay_khoa', return_value=False), \
                mock.patch.object(app, 'ban_dang_chay', return_value=51234) as bdc, \
                mock.patch.object(app, '_mo_may_chu') as mmc, mock.patch.object(app, '_hop_thoai') as hop, \
                mock.patch.object(sys, 'stdout', io.StringIO()):
            self.assertEqual(app.main([]), 0)
        bdc.assert_called_once_with(Path(t))
        mmc.assert_not_called()
        hop.assert_not_called()

    def test_ban_khac_khong_phan_hoi_thi_hop_thoai_tra_1(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(os.environ, {'HGR_DU_LIEU': t}), \
                mock.patch.object(app, '_lay_khoa', return_value=False), \
                mock.patch.object(app, 'ban_dang_chay', return_value=None), mock.patch.object(app, 'CHO_BAN_KHAC', 0.2), \
                mock.patch.object(app, '_mo_may_chu') as mmc, mock.patch.object(app, '_hop_thoai') as hop, \
                mock.patch.object(sys, 'stdout', io.StringIO()):
            self.assertEqual(app.main([]), 1)
        mmc.assert_not_called()
        hop.assert_called_once_with(app.CHU_KHONG_PHAN_HOI)


@unittest.skipUnless(sys.platform == 'win32', 'mutex Windows')
class KhoaTest(unittest.TestCase):
    """Mutex thật của Windows, dưới một tên riêng của bài kiểm (không phải TEN_KHOA: app thật hay bộ cài có thể đang dò tên đó)."""

    def test_ban_thu_hai_khong_lay_duoc_khoa(self):
        import ctypes
        ten = f'HarryGoldResearch.App.thu-{os.getpid()}'
        with mock.patch.object(app, 'TEN_KHOA', ten), mock.patch.dict(app._TT, {'khoa': None}):
            self.assertTrue(app._lay_khoa())
            try:
                ma = ('import sys; sys.path.insert(0, sys.argv[1]); from so_cong_khai import app; app.TEN_KHOA = sys.argv[2]; '
                      'print(app._lay_khoa())')
                r = subprocess.run([sys.executable, '-c', ma, str(GOC), ten], capture_output=True, text=True, timeout=60, check=False)  # noqa: S603 - chính Python này, mã cố định trong bài kiểm
                self.assertEqual(r.stdout.strip(), 'False', r.stderr)
            finally:
                ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(app._TT['khoa']))


class _CuaSoGia:
    """Cửa sổ pywebview giả: ghi lại các lời gọi; destroy đi qua `closing` như thật (R8)."""

    def __init__(self):
        self.goi: list = []
        self.events = mock.MagicMock()
        self.dong = None                                     # hàm của events.closing, gán trong bài kiểm

    def show(self):
        self.goi.append('show')

    def hide(self):
        self.goi.append('hide')

    def load_url(self, url):
        self.goi.append(('load_url', url))

    def destroy(self):
        self.goi.append(('destroy', self.dong() if self.dong else None))


class VoTest(unittest.TestCase):
    """Các hành vi của vỏ app với cửa sổ, khay và máy chủ giả: không mở cửa sổ, không nhập webview hay pystray."""

    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.g = Path(self._t.name)
        (self.g / 'du-lieu').mkdir()
        self.ch = self.g / 'cau-hinh.json'
        self.ch.write_text('{}', encoding='utf-8')
        self.srv = mock.Mock()
        self.vo = app._Vo(self.g, self.ch, self.srv, 50123)
        self.w = _CuaSoGia()
        self.vo.window, self.vo.icon = self.w, mock.Mock()
        self.w.dong = self.vo.khi_dong
        p = mock.patch.object(sys, 'stdout', io.StringIO())
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self._t.cleanup)

    def _cho(self, dk, han=3.0):
        het = time.monotonic() + han
        while not dk() and time.monotonic() < het:
            time.sleep(0.01)
        return dk()

    def test_dong_cua_so_an_xuong_khay_va_bao_mot_lan(self):
        self.assertIs(self.vo.khi_dong(), False)                                   # hủy đóng
        self.assertEqual(self.w.goi, ['hide'])
        self.assertTrue(self._cho(lambda: self.vo.icon.notify.called))
        self.vo.icon.notify.assert_called_once_with(app.CHU_BAO_KHAY, app.TEN)
        self.assertTrue((self.g / 'du-lieu' / 'app-da-bao-khay.json').is_file())
        self.assertIs(self.vo.khi_dong(), False)                                   # lần sau: vẫn ẩn, không báo lại
        time.sleep(0.1)
        self.vo.icon.notify.assert_called_once()

    def test_dong_khi_khong_co_khay_thi_cho_dong(self):
        self.vo.icon = None
        self.assertIs(self.vo.khi_dong(), True)
        self.assertEqual(self.w.goi, [])

    def test_thoat_bat_co_truoc_destroy_r8(self):
        app.ghi_tep_chay(self.g, 50123)
        self.vo.thoat()
        self.assertEqual(self.w.goi, [('destroy', True)])                         # closing trong destroy cho đóng, không ẩn
        self.assertFalse(app.tep_chay(self.g).exists())
        self.vo.icon.stop.assert_called_once()
        self.srv.shutdown.assert_called_once()
        self.assertTrue(self.vo.xong.is_set())
        self.vo.thoat()                                                            # gọi lần hai không làm lại
        self.srv.shutdown.assert_called_once()

    def test_thoat_nen_tra_ve_ngay_r12(self):
        da = threading.Event()
        self.vo.thoat = da.set
        t0 = time.monotonic()
        self.vo.thoat_nen()
        self.assertLess(time.monotonic() - t0, 0.1)
        self.assertFalse(da.is_set())
        self.assertTrue(da.wait(3))

    def test_hien_nen_khong_chan_r12(self):
        cho, xong = threading.Event(), threading.Event()
        self.vo.mo = lambda: (cho.wait(5), xong.set())
        t0 = time.monotonic()
        self.vo.hien_nen()
        self.assertLess(time.monotonic() - t0, 0.1)
        cho.set()
        self.assertTrue(xong.wait(3))

    def test_mo_toi_bieu_do_cua_canh_bao_roi_quen(self):
        self.vo.canh_bao = {'ma': 'XAUUSD', 'tf': 'M15', 'luc': time.time()}
        self.vo.mo()
        self.assertEqual(self.w.goi, ['show', ('load_url', 'http://127.0.0.1:50123/bieu-do?ma=XAUUSD&tf=M15')])
        self.assertIsNone(self.vo.canh_bao)
        self.vo.mo()
        self.assertEqual(self.w.goi[-1], 'show')

    def test_mo_o_che_do_trinh_duyet(self):
        self.vo.trinh_duyet, self.vo.window = True, None
        self.vo.canh_bao = {'ma': 'XAUUSD', 'tf': 'H1', 'luc': time.time()}
        with mock.patch.object(app.os, 'startfile', create=True) as sf:
            self.vo.mo()
            self.vo.mo()
        self.assertEqual([c.args[0] for c in sf.call_args_list], ['http://127.0.0.1:50123/bieu-do?ma=XAUUSD&tf=H1', 'http://127.0.0.1:50123/'])

    def test_khi_bao_hien_thong_bao_va_nho(self):
        b = {'ma': 'XAUUSD', 'ten': 'Vàng', 'tf': 'M15', 'mo_ta': 'Giá chạm đường xu hướng', 'gia': 2650.5, 'luc': 1000.0}
        self.vo.khi_bao(b)
        self.vo.icon.notify.assert_called_once_with('Giá chạm đường xu hướng · giá 2650.5', 'Vàng M15')
        self.assertIs(self.vo.canh_bao, b)


class GiaoDienTest(unittest.TestCase):
    """_chay_giao_dien với mô-đun webview GIẢ đặt vào sys.modules (không phải thư viện thật) và khay giả."""

    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.g = Path(self._t.name)
        self.ch = self.g / 'cau-hinh.json'
        self.ch.write_text('{}', encoding='utf-8')
        self.vo = app._Vo(self.g, self.ch, mock.Mock(), 50123)
        self.wv = types.ModuleType('webview')
        self.wv.settings = {'ALLOW_DOWNLOADS': False, 'OPEN_EXTERNAL_LINKS_IN_BROWSER': False}
        self.cua_so = mock.MagicMock()
        self.wv.create_window = mock.Mock(return_value=self.cua_so)
        from so_cong_khai import canh_bao_ve
        for p in (mock.patch.dict(sys.modules, {'webview': self.wv}), mock.patch.object(app, 'co_webview2', return_value=True),
                  mock.patch.object(app._Vo, '_kiem_cap_nhat'), mock.patch.object(canh_bao_ve, 'KHI_BAO', []),
                  mock.patch.object(sys, 'stdout', io.StringIO())):
            p.start()
            self.addCleanup(p.stop)
        self.khi_bao = canh_bao_ve.KHI_BAO

    def test_mo_cua_so_dung_tham_so_r6(self):
        self.wv.start = mock.Mock(side_effect=lambda **k: self.vo.thoat())              # người dùng bấm "Thoát" trong lúc cửa sổ mở
        with mock.patch.object(app, '_tao_khay', return_value=mock.Mock()):
            app._chay_giao_dien(self.vo, None)
        self.wv.create_window.assert_called_once_with(app.TEN, 'http://127.0.0.1:50123/bat-dau', width=1280, height=800, min_size=(900, 600))
        self.wv.start.assert_called_once_with(private_mode=False, storage_path=str(self.g / 'webview'))
        self.assertTrue(self.wv.settings['ALLOW_DOWNLOADS'])
        self.assertTrue(self.wv.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'])
        self.assertEqual(self.khi_bao, [self.vo.khi_bao])
        self.cua_so.destroy.assert_called_once()
        self.vo.srv.shutdown.assert_called_once()

    def test_cua_so_loi_khong_co_khay_thi_mo_trinh_duyet(self):
        self.wv.start = mock.Mock(side_effect=RuntimeError('WebView2 hỏng'))
        with mock.patch.object(app, '_tao_khay', return_value=None), mock.patch.object(app._Vo, '_mo_trinh_duyet') as td:
            app._chay_giao_dien(self.vo, 0.3)                                            # R13: tự thoát để bài kiểm kết thúc
        td.assert_called_once_with('/bat-dau')
        self.assertTrue(self.vo.trinh_duyet)
        self.vo.srv.shutdown.assert_called_once()

    def test_khong_co_webview2_thi_mo_trinh_duyet(self):
        self.wv.start = mock.Mock()
        with mock.patch.object(app, 'co_webview2', return_value=False), mock.patch.object(app, '_tao_khay', return_value=mock.Mock()), \
                mock.patch.object(app._Vo, '_mo_trinh_duyet') as td:
            app._chay_giao_dien(self.vo, 0.3)
        self.wv.create_window.assert_not_called()
        td.assert_called_once_with('/bat-dau')
        self.vo.srv.shutdown.assert_called_once()


if __name__ == '__main__':
    unittest.main()
