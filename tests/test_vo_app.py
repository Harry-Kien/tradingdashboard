# -*- coding: utf-8 -*-
"""Cầu nối giữa máy chủ và vỏ app (so_cong_khai/vo_app.py): trạng thái cho giao diện và các việc máy chủ làm hộ vỏ app
(hiện cửa sổ, mở thư mục dữ liệu, kiểm và tải bản mới). Không bài nào gọi ra mạng hay chạm cổng 8765, 8769: hàm dò cổng, hàm mở thư mục,
hàm chạy bộ cài và phần tải của cap_nhat đều được thay bằng hàm giả."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import cap_nhat, duong, vo_app  # noqa: E402

BAN_MOI = {'phien_ban': '1.2.0', 'tai': 'https://vi-du.invalid/HarryGoldResearch-Setup-1.2.0.exe', 'sha256': 'a' * 64, 'ghi_chu': 'Sửa lỗi nhỏ.'}


def _tt(ban_moi=None) -> dict:
    """Trạng thái giả của cap_nhat.trang_thai()."""
    return {'dia_chi': cap_nhat.KE_KHAI, 'lan_kiem': 1_795_000_000.0, 'ban_moi': ban_moi, 'loi': None, 'dang_tai': False}


class TrangThaiTest(unittest.TestCase):
    def test_ma_nguon(self):
        t = vo_app.trang_thai({})
        self.assertEqual((t['dong_goi'], t['phien_ban'], t['ban_cu_8765']), (False, '1.0.0', False))

    def test_ban_cu_8765(self):
        with mock.patch.dict(vo_app.VO, {'cong': 51234}):
            self.assertTrue(vo_app.trang_thai({}, do_cong=lambda c: True)['ban_cu_8765'])
            self.assertFalse(vo_app.trang_thai({}, do_cong=lambda c: False)['ban_cu_8765'])
        with mock.patch.dict(vo_app.VO, {'cong': 8765}):
            t = vo_app.trang_thai({}, do_cong=lambda c: c == 8765)                 # chỉ chính app trả lời ở cổng của nó
            self.assertEqual((t['ban_cu_8765'], t['cong_webapp_rieng']), (False, None))

    def test_webapp_rieng_r14(self):
        self.assertEqual(vo_app.CONG_WEBAPP_RIENG, (8769, 8765))
        hoi = []
        with mock.patch.dict(vo_app.VO, {'cong': 8790}):
            t = vo_app.trang_thai({}, do_cong=lambda c: hoi.append(c) or c == 8769)     # webapp chạy từ mã nguồn ở 8769
            self.assertEqual((t['ban_cu_8765'], t['cong_webapp_rieng']), (True, 8769))
            self.assertEqual(hoi, [8769])
            t = vo_app.trang_thai({}, do_cong=lambda c: c == 8765)                 # chỉ có bản zip cũ ở 8765
            self.assertEqual((t['ban_cu_8765'], t['cong_webapp_rieng']), (True, 8765))
            t = vo_app.trang_thai({}, do_cong=lambda c: False)
            self.assertEqual((t['ban_cu_8765'], t['cong_webapp_rieng']), (False, None))
        hoi.clear()
        with mock.patch.dict(vo_app.VO, {'cong': 8769}):                           # app (vì lý do nào đó) đang ở 8769: bỏ qua cổng của chính nó
            t = vo_app.trang_thai({}, do_cong=lambda c: hoi.append(c) or True)
            self.assertEqual((t['ban_cu_8765'], t['cong_webapp_rieng']), (True, 8765))
            self.assertEqual(hoi, [8765])

    def test_ma_nguon_khong_do_cong(self):
        do = mock.Mock(return_value=True)
        with mock.patch.dict(vo_app.VO, {'cong': None}):
            t = vo_app.trang_thai({}, do_cong=do)
        self.assertEqual((t['ban_cu_8765'], t['cong_webapp_rieng']), (False, None))
        do.assert_not_called()


class CoWebappTest(unittest.TestCase):
    """Dò webapp chạy riêng bằng hàm hỏi giả (không gọi mạng). Webapp mới chặn /api/tinh-trang sau đăng nhập (401) nhưng /api/phien-ban công khai."""

    def setUp(self):
        p = mock.patch.dict(vo_app._nho_cong, clear=True)
        p.start()
        self.addCleanup(p.stop)

    def _hoi(self, tra):
        hoi = []

        def f(url):
            hoi.append(url.rsplit(':', 1)[1])
            return tra[url.split('/', 3)[3]]
        return hoi, f

    def test_ban_zip_cu_tra_loi_tinh_trang(self):
        hoi, f = self._hoi({'api/tinh-trang': (200, b'{}')})
        self.assertTrue(vo_app._co_webapp(8765, hoi=f))
        self.assertEqual(hoi, ['8765/api/tinh-trang'])                           # không hỏi thêm

    def test_webapp_moi_dang_nhap_thi_hoi_phien_ban(self):
        hoi, f = self._hoi({'api/tinh-trang': (401, b'{"ok": false}'), 'api/phien-ban': (200, '{"san_pham": "Harry · Gold Research"}'.encode())})
        self.assertTrue(vo_app._co_webapp(8769, hoi=f))
        self.assertEqual(hoi, ['8769/api/tinh-trang', '8769/api/phien-ban'])

    def test_khong_phai_webapp(self):
        _, f = self._hoi({'api/tinh-trang': (401, b''), 'api/phien-ban': (200, b'{"khac": 1}')})
        self.assertFalse(vo_app._co_webapp(8769, hoi=f))
        vo_app._nho_cong.clear()
        _, f = self._hoi({'api/tinh-trang': (404, b''), 'api/phien-ban': (200, '{"san_pham": "Harry · Gold Research"}'.encode())})
        self.assertFalse(vo_app._co_webapp(8769, hoi=f))                         # 404: không phải webapp bị khóa, không hỏi tiếp
        vo_app._nho_cong.clear()
        self.assertFalse(vo_app._co_webapp(8769, hoi=mock.Mock(side_effect=OSError)))


class BatDauTest(unittest.TestCase):
    """Dòng báo trên trang Bắt đầu hiện đúng cổng của webapp chạy riêng, ở cả tiếng Việt lẫn tiếng Anh (qua bộ dịch thật)."""

    def test_hien_dung_cong(self):
        self.assertIn(".replace('8765',String(j.cong_webapp_rieng||8765))", vo_app.JS_BAT_DAU)

    def test_ban_dich_tieng_anh_van_ap(self):
        from so_cong_khai import dich
        en = dich.dich_js(vo_app.JS_BAT_DAU, dich.tu_dien('en'))
        self.assertNotIn('Máy này đang chạy', en)
        self.assertIn("older webapp on port 8765.", en)
        self.assertIn(".replace('8765',String(j.cong_webapp_rieng||8765))", en)

    def test_ban_moi_la_chuoi_phien_ban(self):
        with mock.patch.object(cap_nhat, 'trang_thai', return_value=_tt(BAN_MOI)):
            c = vo_app.trang_thai({'cap_nhat': {'bat': False}})['cap_nhat']
        self.assertEqual(c, {'bat': False, 'ban_moi': '1.2.0', 'ghi_chu': 'Sửa lỗi nhỏ.', 'lan_kiem': 1_795_000_000.0, 'loi': None, 'dang_tai': False})
        with mock.patch.object(cap_nhat, 'trang_thai', return_value=_tt()):
            c = vo_app.trang_thai({})['cap_nhat']
        self.assertEqual((c['bat'], c['ban_moi'], c['ghi_chu']), (True, None, ''))            # không có mục cap_nhat thì coi như bật


class LamTest(unittest.TestCase):
    def test_viec_la(self):
        self.assertEqual(vo_app.lam('xoa_het', {}), (400, {'loi': 'Việc không hỗ trợ.'}))

    def test_hien_goi_vo(self):
        hien = mock.Mock()
        with mock.patch.dict(vo_app.VO, {'hien': hien}):
            self.assertEqual(vo_app.lam('hien', {}), (200, {'ok': True}))
        hien.assert_called_once_with()

    def test_mo_thu_muc(self):
        mo = mock.Mock()
        self.assertEqual(vo_app.lam('mo_thu_muc', {}, mo=mo)[0], 200)
        mo.assert_called_once_with(str(duong.goc_du_lieu()))

    def test_kiem_ngay_ep_kiem(self):
        """Nút "Kiểm ngay" phải truyền ep=True: cap_nhat.kiem chỉ bỏ qua ô tắt tự kiểm và hạn một ngày khi có ep."""
        tat = {'cap_nhat': {'bat': False}}
        with mock.patch.object(cap_nhat, 'kiem', return_value=_tt()) as kiem, mock.patch.object(cap_nhat, 'trang_thai', return_value=_tt()):
            ma, kq = vo_app.lam('kiem_ngay', tat)
        kiem.assert_called_once_with(tat, ep=True)
        self.assertEqual(ma, 200)
        self.assertIn('cap_nhat', kq)

    def test_tai_cap_nhat_ma_nguon_thi_tu_choi(self):
        chay = mock.Mock()
        with (mock.patch.object(duong, 'DONG_GOI', False), mock.patch.object(cap_nhat, 'trang_thai', return_value=_tt(BAN_MOI)),
              mock.patch.object(cap_nhat, 'tai_bo_cai') as tai):
            ma, _ = vo_app.lam('tai_cap_nhat', {}, chay=chay)
        self.assertEqual(ma, 409)
        chay.assert_not_called()
        tai.assert_not_called()

    def test_tai_cap_nhat_ma_bam_sai_thi_khong_chay(self):
        chay, thoat = mock.Mock(), mock.Mock()
        cau = 'Tệp tải về không khớp mã kiểm. Đã xóa.'
        with (mock.patch.object(duong, 'DONG_GOI', True), mock.patch.object(cap_nhat, 'trang_thai', return_value=_tt(BAN_MOI)),
              mock.patch.object(cap_nhat, 'tai_bo_cai', return_value=(False, cau, None)), mock.patch.dict(vo_app.VO, {'thoat': thoat})):
            self.assertEqual(vo_app.lam('tai_cap_nhat', {}, chay=chay), (409, {'loi': cau}))
        chay.assert_not_called()
        thoat.assert_not_called()

    def test_tai_cap_nhat_thanh_cong(self):
        thu_tu = mock.Mock()                                                    # một mock cha ghi lại thứ tự gọi của chay và thoat
        bo_cai = Path('C:/tam/HarryGoldResearch-Setup-1.2.0.exe')
        with (mock.patch.object(duong, 'DONG_GOI', True), mock.patch.object(cap_nhat, 'trang_thai', return_value=_tt(BAN_MOI)),
              mock.patch.object(cap_nhat, 'tai_bo_cai', return_value=(True, '', bo_cai)), mock.patch.dict(vo_app.VO, {'thoat': thu_tu.thoat})):
            ma, _ = vo_app.lam('tai_cap_nhat', {}, chay=thu_tu.chay)
        self.assertEqual(ma, 200)
        self.assertEqual(thu_tu.mock_calls, [mock.call.chay(str(bo_cai)), mock.call.thoat()])


if __name__ == '__main__':
    unittest.main()
