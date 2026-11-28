"""Bài kiểm cho phiên bản và kiểm cập nhật: so sánh số phiên bản, đọc kê khai (hỏng thì bỏ qua), chỉ kiểm khi chạy bản đóng gói, bật trong
cấu hình và mỗi ngày một lần, tải bộ cài có kiểm mã băm. Mọi phép tải đều tiêm qua tham số `tai`, mọi tệp ghi vào thư mục tạm: không
gọi mạng thật, không chạm dữ liệu thật."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import cap_nhat, duong, phien_ban  # noqa: E402

HOP_LE = {'phien_ban': '1.0.1', 'tai': 'https://example.org/a.exe', 'sha256': 'a' * 64, 'ghi_chu': 'sửa lỗi'}
CFG = {'cap_nhat': {'bat': True}}


def _ke_khai(**them) -> bytes:
    return json.dumps({**HOP_LE, **them}).encode()


class PhienBanTest(unittest.TestCase):
    def test_so_sanh(self):
        self.assertTrue(phien_ban.moi_hon('1.0.10', '1.0.9'))
        self.assertTrue(phien_ban.moi_hon('2.0.0', '1.9.9'))
        self.assertFalse(phien_ban.moi_hon('1.0.0', '1.0.0'))
        self.assertFalse(phien_ban.moi_hon('1.0', '0.9.0'))
        self.assertFalse(phien_ban.moi_hon('v9.9.9', '1.0.0'))

    def test_phien_ban_dau(self):
        self.assertEqual(phien_ban.PHIEN_BAN, '1.0.0')


class KeKhaiTest(unittest.TestCase):
    def test_hop_le(self):
        k = cap_nhat.doc_ke_khai(json.dumps({**HOP_LE, 'sha256': 'A' * 64}).encode())
        self.assertEqual(k['sha256'], 'a' * 64)
        self.assertIsNone(k['ke_khai_moi'])

    def test_ke_khai_hong_thi_bo_qua(self):
        for sai in (b'khong phai json', b'[]', b'{}',
                    json.dumps({**HOP_LE, 'tai': 'http://example.org/a.exe'}).encode(),
                    json.dumps({**HOP_LE, 'sha256': 'abc'}).encode(),
                    json.dumps({**HOP_LE, 'phien_ban': 'moi-nhat'}).encode(),
                    b' ' * 70000):
            self.assertIsNone(cap_nhat.doc_ke_khai(sai))

    def test_ke_khai_moi_khong_https_thi_bo(self):
        k = cap_nhat.doc_ke_khai(json.dumps({**HOP_LE, 'ke_khai_moi': 'http://x.example/k.json'}).encode())
        self.assertIsNone(k['ke_khai_moi'])

    def test_ghi_chu_cat_con_500_ky_tu(self):
        k = cap_nhat.doc_ke_khai(_ke_khai(ghi_chu='x' * 900))
        self.assertEqual(len(k['ghi_chu']), 500)

    def test_nen_kiem(self):
        self.assertTrue(cap_nhat.nen_kiem(1000.0, None))
        self.assertFalse(cap_nhat.nen_kiem(1000.0 + 86399, 1000.0))
        self.assertTrue(cap_nhat.nen_kiem(1000.0 + 86400, 1000.0))


class KiemTest(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.goc = Path(td.name)
        p = mock.patch.object(duong, 'DONG_GOI', True)
        p.start()
        self.addCleanup(p.stop)

    def _tai(self, noi_dung=None, loi=None):
        """Máy tải giả: ghi lại các địa chỉ đã được gọi."""
        goi = []

        def tai(dia_chi):
            goi.append(dia_chi)
            if loi is not None:
                raise loi
            return noi_dung
        tai.goi = goi
        return tai

    def test_ma_nguon_thi_khong_goi_mang(self):
        tai = self._tai(_ke_khai())
        with mock.patch.object(duong, 'DONG_GOI', False):
            cap_nhat.kiem(CFG, self.goc, now=1000.0, tai=tai)
        self.assertEqual(tai.goi, [])

    def test_tat_trong_cau_hinh_thi_khong_goi_mang(self):
        tai = self._tai(_ke_khai())
        cap_nhat.kiem({'cap_nhat': {'bat': False}}, self.goc, now=1000.0, tai=tai)
        self.assertEqual(tai.goi, [])

    def test_kiem_ngay_van_kiem_khi_da_tat_tu_kiem(self):
        """Ô tắt chỉ tắt việc TỰ kiểm mỗi ngày; bấm "Kiểm ngay" (ep=True) là người dùng tự hỏi nên vẫn kiểm. Chạy từ mã nguồn thì không bao giờ."""
        tat = {'cap_nhat': {'bat': False}}
        tai = self._tai(_ke_khai())
        cap_nhat.kiem(tat, self.goc, now=1000.0, tai=tai, ep=True)
        self.assertEqual(tai.goi, [cap_nhat.KE_KHAI])
        tai = self._tai(_ke_khai())
        cap_nhat.kiem(tat, self.goc, now=1000.0 + 2 * 86400, tai=tai, ep=False)
        self.assertEqual(tai.goi, [])
        tai = self._tai(_ke_khai())
        with mock.patch.object(duong, 'DONG_GOI', False):
            cap_nhat.kiem(tat, self.goc, now=1000.0 + 4 * 86400, tai=tai, ep=True)
        self.assertEqual(tai.goi, [])

    def test_khong_co_muc_cap_nhat_thi_coi_la_bat(self):
        tai = self._tai(_ke_khai())
        cap_nhat.kiem({}, self.goc, now=1000.0, tai=tai)
        self.assertEqual(tai.goi, [cap_nhat.KE_KHAI])

    def test_mot_lan_moi_ngay(self):
        tai = self._tai(_ke_khai())
        cap_nhat.kiem(CFG, self.goc, now=1000.0, tai=tai)
        cap_nhat.kiem(CFG, self.goc, now=1000.0 + 3600, tai=tai)
        self.assertEqual(len(tai.goi), 1)

    def test_ep_thi_kiem_lai_ngay(self):
        tai = self._tai(_ke_khai())
        cap_nhat.kiem(CFG, self.goc, now=1000.0, tai=tai)
        cap_nhat.kiem(CFG, self.goc, now=1000.0 + 3600, tai=tai, ep=True)
        self.assertEqual(len(tai.goi), 2)

    def test_co_ban_moi(self):
        cap_nhat.kiem(CFG, self.goc, now=1000.0, tai=self._tai(_ke_khai()))
        tt = cap_nhat.trang_thai(self.goc)
        self.assertEqual(tt['ban_moi']['phien_ban'], '1.0.1')
        self.assertEqual(tt['lan_kiem'], 1000.0)
        self.assertIsNone(tt['loi'])

    def test_phien_ban_lui_thi_khong_bao(self):
        cap_nhat.kiem(CFG, self.goc, now=1000.0, tai=self._tai(_ke_khai(phien_ban='0.9.0')))
        self.assertIsNone(cap_nhat.trang_thai(self.goc)['ban_moi'])

    def test_doi_dia_chi_ke_khai(self):
        moi = 'https://khac.example/ban-moi.json'
        cap_nhat.kiem(CFG, self.goc, now=1000.0, tai=self._tai(_ke_khai(ke_khai_moi=moi)))
        self.assertEqual(cap_nhat.trang_thai(self.goc)['dia_chi'], moi)
        tai = self._tai(_ke_khai())
        cap_nhat.kiem(CFG, self.goc, now=1000.0 + 86400, tai=tai)
        self.assertEqual(tai.goi, [moi])

    def test_loi_mang_khong_nem(self):
        tt = cap_nhat.kiem(CFG, self.goc, now=1000.0, tai=self._tai(loi=OSError('mất mạng')))
        self.assertTrue(tt['loi'])
        self.assertTrue(cap_nhat.trang_thai(self.goc)['loi'])

    def test_ke_khai_hong_ghi_loi_khong_nem(self):
        tt = cap_nhat.kiem(CFG, self.goc, now=1000.0, tai=self._tai(b'khong phai json'))
        self.assertTrue(tt['loi'])
        self.assertIsNone(tt['ban_moi'])

    def test_trang_thai_mac_dinh(self):
        self.assertEqual(cap_nhat.trang_thai(self.goc),
                         {'dia_chi': cap_nhat.KE_KHAI, 'lan_kiem': None, 'ban_moi': None, 'loi': None, 'dang_tai': False})

    def test_tep_trang_thai_hong_thi_dung_mac_dinh(self):
        (self.goc / 'du-lieu').mkdir()
        (self.goc / 'du-lieu' / 'cap-nhat.json').write_text('{hong', encoding='utf-8')
        self.assertIsNone(cap_nhat.trang_thai(self.goc)['lan_kiem'])


class TaiTest(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.goc = Path(td.name)
        p = mock.patch.object(duong, 'DONG_GOI', True)
        p.start()
        self.addCleanup(p.stop)

    def _co_ban_moi(self, noi_dung: bytes, sha256: str | None = None):
        sha256 = sha256 or hashlib.sha256(noi_dung).hexdigest()
        cap_nhat.kiem(CFG, self.goc, now=1000.0, tai=lambda _dc: _ke_khai(sha256=sha256))

    @staticmethod
    def _tai_gia(noi_dung: bytes):
        def tai(_dia_chi, dich, _toi_da):
            dich.write_bytes(noi_dung)
        return tai

    def test_khop_ma_bam(self):
        nd = b'x' * 1000
        self._co_ban_moi(nd)
        ok, loi, p = cap_nhat.tai_bo_cai(self.goc, tai=self._tai_gia(nd))
        self.assertEqual((ok, loi), (True, ''))
        self.assertTrue(p.is_file())
        self.assertEqual(p.parent, self.goc / 'cap-nhat')
        self.assertEqual(p.name, 'HarryGoldResearch-Setup-1.0.1.exe')
        self.assertFalse(cap_nhat.trang_thai(self.goc)['dang_tai'])

    def test_khong_khop_thi_xoa(self):
        nd = b'x' * 1000
        self._co_ban_moi(nd, sha256='b' * 64)
        kq = cap_nhat.tai_bo_cai(self.goc, tai=self._tai_gia(nd))
        self.assertEqual(kq, (False, 'Tệp tải về không khớp mã kiểm. Đã xóa.', None))
        self.assertEqual(list((self.goc / 'cap-nhat').glob('*.exe')), [])
        self.assertFalse(cap_nhat.trang_thai(self.goc)['dang_tai'])

    def test_dang_tai_la_true_trong_luc_tai(self):
        nd = b'x' * 10
        self._co_ban_moi(nd)
        thay = []

        def tai(_dia_chi, dich, _toi_da):
            thay.append(cap_nhat.trang_thai(self.goc)['dang_tai'])
            dich.write_bytes(nd)
        cap_nhat.tai_bo_cai(self.goc, tai=tai)
        self.assertEqual(thay, [True])

    def test_loi_khi_tai_thi_dang_tai_ve_false(self):
        self._co_ban_moi(b'x')

        def tai(_dia_chi, dich, _toi_da):
            dich.write_bytes(b'do dang')
            raise OSError('đứt mạng')
        ok, loi, p = cap_nhat.tai_bo_cai(self.goc, tai=tai)
        self.assertFalse(ok)
        self.assertTrue(loi)
        self.assertIsNone(p)
        self.assertFalse(cap_nhat.trang_thai(self.goc)['dang_tai'])
        self.assertEqual(list((self.goc / 'cap-nhat').glob('*')), [])

    def test_chua_co_ban_moi(self):
        ok, loi, p = cap_nhat.tai_bo_cai(self.goc, tai=self._tai_gia(b'x'))
        self.assertFalse(ok)
        self.assertTrue(loi)
        self.assertIsNone(p)

    def test_truyen_gioi_han_300_mb(self):
        nd = b'x'
        self._co_ban_moi(nd)
        thay = []

        def tai(_dia_chi, dich, toi_da):
            thay.append(toi_da)
            dich.write_bytes(nd)
        cap_nhat.tai_bo_cai(self.goc, tai=tai)
        self.assertEqual(thay, [300 * 1024 * 1024])


    def _tep_cuoi(self):
        return self.goc / 'cap-nhat' / 'HarryGoldResearch-Setup-1.0.1.exe'

    def test_tai_vao_part_roi_moi_doi_ten(self):
        nd = b'x' * 100
        self._co_ban_moi(nd)
        cuoi, thay = self._tep_cuoi(), []

        def tai(_dia_chi, dich, _toi_da):
            dich.write_bytes(nd)
            thay.append((cuoi.exists(), dich.name.endswith('.part'), dich.exists()))
        ok, _, p = cap_nhat.tai_bo_cai(self.goc, tai=tai)
        self.assertEqual(thay, [(False, True, True)])
        self.assertTrue(ok)
        self.assertEqual(sorted(x.name for x in (self.goc / 'cap-nhat').iterdir()), [cuoi.name])
        self.assertEqual(p, cuoi)

    def test_khong_khop_thi_khong_con_tep_nao(self):
        self._co_ban_moi(b'x', sha256='b' * 64)
        cap_nhat.tai_bo_cai(self.goc, tai=self._tai_gia(b'x'))
        self.assertEqual(list((self.goc / 'cap-nhat').iterdir()), [])

    def test_loi_giua_chung_khong_con_tep_nao(self):
        self._co_ban_moi(b'x')

        def tai(_dia_chi, dich, _toi_da):
            dich.write_bytes(b'do dang')
            raise OSError('đứt mạng')
        cap_nhat.tai_bo_cai(self.goc, tai=tai)
        self.assertEqual(list((self.goc / 'cap-nhat').iterdir()), [])
        self.assertFalse(cap_nhat.trang_thai(self.goc)['dang_tai'])

    def test_tai_dong_thoi_thi_lan_hai_bi_tu_choi(self):
        nd = b'x' * 50
        self._co_ban_moi(nd)
        ket_qua = []

        def tai(_dia_chi, dich, _toi_da):
            ket_qua.append(cap_nhat.tai_bo_cai(self.goc, tai=self._tai_gia(b'khac')))      # lần hai chạy lúc lần một đang tải
            self.assertTrue(cap_nhat.trang_thai(self.goc)['dang_tai'])
            dich.write_bytes(nd)
        ok, _, p = cap_nhat.tai_bo_cai(self.goc, tai=tai)
        self.assertEqual(ket_qua, [(False, 'Đang tải bản mới, vui lòng chờ.', None)])
        self.assertTrue(ok)
        self.assertEqual(p.read_bytes(), nd)

    def test_tep_cu_chua_kiem_o_ten_cuoi_bi_xoa_khi_tai_hong(self):
        self._co_ban_moi(b'x')
        cuoi = self._tep_cuoi()
        cuoi.parent.mkdir(parents=True)
        cuoi.write_bytes(b'chua kiem tra')

        def tai(_dia_chi, _dich, _toi_da):
            raise OSError('mất mạng')
        cap_nhat.tai_bo_cai(self.goc, tai=tai)
        self.assertFalse(cuoi.exists())

    def test_dang_tai_trong_tep_cu_bi_bo_qua_va_khong_ghi_xuong_tep(self):
        nd = b'x' * 10
        self._co_ban_moi(nd)
        tep = self.goc / 'du-lieu' / 'cap-nhat.json'
        d = json.loads(tep.read_text(encoding='utf-8'))
        d['dang_tai'] = True
        tep.write_text(json.dumps(d), encoding='utf-8')
        self.assertFalse(cap_nhat.trang_thai(self.goc)['dang_tai'])
        cap_nhat.tai_bo_cai(self.goc, tai=self._tai_gia(nd))
        cap_nhat.kiem(CFG, self.goc, now=1000.0 + 5, tai=lambda _dc: _ke_khai(), ep=True)     # ghi lại tệp trạng thái
        self.assertNotIn('dang_tai', json.loads(tep.read_text(encoding='utf-8')))


class LanKiemLaTest(unittest.TestCase):
    """`lan_kiem` trong tệp trạng thái là dữ liệu không tin được: sai kiểu hay ở tương lai thì vẫn kiểm, không ném."""

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.goc = Path(td.name)
        p = mock.patch.object(duong, 'DONG_GOI', True)
        p.start()
        self.addCleanup(p.stop)

    def _kiem_voi(self, lan_kiem, now=1_000_000.0):
        (self.goc / 'du-lieu').mkdir()
        (self.goc / 'du-lieu' / 'cap-nhat.json').write_text(json.dumps({'lan_kiem': lan_kiem}), encoding='utf-8')
        goi = []

        def tai(dia_chi):
            goi.append(dia_chi)
            return _ke_khai()
        cap_nhat.kiem(CFG, self.goc, now=now, tai=tai)
        return goi

    def test_chuoi_thi_van_kiem(self):
        self.assertEqual(len(self._kiem_voi('hôm qua')), 1)

    def test_bool_thi_van_kiem(self):
        self.assertEqual(len(self._kiem_voi(True)), 1)

    def test_tuong_lai_thi_van_kiem(self):
        self.assertEqual(len(self._kiem_voi(1_000_000.0 + 86400)), 1)


class MacDinhTest(unittest.TestCase):
    """Hai hàm tải mặc định từ chối mọi địa chỉ không phải https trước khi mở kết nối."""

    def test_tai_ke_khai_khong_https(self):
        with mock.patch('urllib.request.urlopen') as m, self.assertRaises(ValueError):
            cap_nhat._tai_ke_khai('http://example.org/k.json')
        m.assert_not_called()

    def test_tai_tep_khong_https(self):
        with tempfile.TemporaryDirectory() as td, mock.patch('urllib.request.urlopen') as m, self.assertRaises(ValueError):
            cap_nhat._tai_tep('file:///c:/windows/win.ini', Path(td) / 'a.exe', 1000)
        m.assert_not_called()


if __name__ == '__main__':
    unittest.main()
