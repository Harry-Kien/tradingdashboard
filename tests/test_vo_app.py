# -*- coding: utf-8 -*-
"""Cầu nối giữa máy chủ và vỏ app (so_cong_khai/vo_app.py): trạng thái cho giao diện và các việc máy chủ làm hộ vỏ app
(hiện cửa sổ, mở thư mục dữ liệu, kiểm và tải bản mới). Không bài nào gọi ra mạng hay chạm cổng 8765: hàm dò cổng, hàm mở thư mục,
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
            self.assertFalse(vo_app.trang_thai({}, do_cong=lambda c: True)['ban_cu_8765'])

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
