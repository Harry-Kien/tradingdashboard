# -*- coding: utf-8 -*-
"""Chuỗi dấu băm của nhật ký điểm vào: mỗi điểm vào mới mang dấu SHA-256 nối với dòng trước, nên sửa, xóa hay chèn một tín hiệu cũ đều lộ ra.
Kết quả về sau (tt, r, ra…) không nằm trong dấu vì chúng được chấm lại từ giá; phần được khóa là nội dung tín hiệu và giờ ghi."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from so_cong_khai import nhat_ky

T0 = datetime(2026, 6, 1, 10, 2, tzinfo=timezone.utc)


def _pa(ma, nen, **kw):
    p = {'ma': ma, 'ten': ma, 'nhom': 'pp', 'co': True, 'hieu_luc': True, 'huong': 'MUA', 'kieu': 'lệnh chờ', 'vao': 100.0, 'sl': 98.0, 'tp': [102.0, 104.0],
         'rr': [1.0, 2.0], 'nen': nen, 'con_phut': 240, 'ly_do': 'thử'}
    p.update(kw)
    return p


class ChuoiDau(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = {'nhat_ky': {'bat': True, 'tep': str(Path(self.tmp.name) / 'nk.json')}, 'gia': {'ma_vang': 'XAUUSDp'}}
        self.p = nhat_ky.tep(self.cfg)

    def tearDown(self):
        self.tmp.cleanup()

    def _ghi_ba(self):
        for k, ma in enumerate(('ict', 'fib', 'pha_vo')):
            nhat_ky.ghi(self.cfg, {'phuong_an': [], 'phuong_phap': [_pa(ma, f'2026-06-01T10:0{k}:00+00:00')], 'bid': 100.0, 'boi_canh': {}}, T0 + timedelta(minutes=k))
        return json.loads(self.p.read_text(encoding='utf-8'))

    def test_moi_dong_moi_co_dau_noi_chuoi(self):
        ds = self._ghi_ba()
        self.assertEqual([len(x['bam']) for x in ds], [64, 64, 64])
        self.assertIsNone(ds[0]['bam_truoc'])
        self.assertEqual([ds[1]['bam_truoc'], ds[2]['bam_truoc']], [ds[0]['bam'], ds[1]['bam']])
        kq = nhat_ky.kiem_chuoi(ds)
        self.assertEqual((kq['ok'], kq['so_dong'], kq['bam_cuoi']), (True, 3, ds[2]['bam']))

    def test_ket_qua_ve_sau_khong_lam_gay_chuoi(self):
        ds = self._ghi_ba()
        ds[0].update(tt='thua', r=-1.0, ra='2026-06-01T11:00:00+00:00', trung_voi=None)
        self.assertTrue(nhat_ky.kiem_chuoi(ds)['ok'])

    def test_sua_xoa_chen_deu_lo(self):
        ds = self._ghi_ba()
        sua = json.loads(json.dumps(ds))
        sua[1]['sl'] = 99.0                                            # dời dừng lỗ của một tín hiệu cũ cho đẹp
        self.assertEqual((nhat_ky.kiem_chuoi(sua)['ok'], nhat_ky.kiem_chuoi(sua)['hong_id']), (False, 2))
        xoa = [ds[0], ds[2]]                                           # xóa một tín hiệu thua
        self.assertFalse(nhat_ky.kiem_chuoi(xoa)['ok'])
        gio = json.loads(json.dumps(ds))
        gio[2]['luc'] = (T0 - timedelta(hours=1)).isoformat()          # lùi giờ ghi
        self.assertFalse(nhat_ky.kiem_chuoi(gio)['ok'])

    def test_dong_cu_chua_co_dau_va_luu_tru(self):
        cu = [{'id': 1, 'luc': T0.isoformat(), 'sym': 'XAUUSDp', 'ma': 'x', 'huong': 'MUA', 'vao': 1.0, 'sl': 0.5, 'tp': [2.0], 'tt': 'thua'}]
        self.p.parent.mkdir(parents=True, exist_ok=True)
        self.p.write_text(json.dumps(cu), encoding='utf-8')
        ds = self._ghi_ba()
        kq = nhat_ky.kiem_chuoi(ds)
        self.assertEqual((kq['ok'], kq['so_dong'], kq['chua_dau']), (True, 3, 1))      # dòng ghi trước khi có chuỗi: đếm riêng, không coi là hỏng
        self.assertIsNone(ds[1]['bam_truoc'])
        that = nhat_ky.TOI_DA
        nhat_ky.TOI_DA = 2
        try:
            nhat_ky.ghi(self.cfg, {'phuong_an': [], 'phuong_phap': [_pa('wyckoff', '2026-06-01T10:09:00+00:00')], 'bid': 100.0, 'boi_canh': {}},
                        T0 + timedelta(minutes=9))
        finally:
            nhat_ky.TOI_DA = that
        self.assertTrue(nhat_ky.kiem_chuoi_tep(self.p)['ok'])          # dòng chuyển sang tệp lưu trữ vẫn được nối chuỗi khi kiểm cả hai tệp
        self.assertEqual(nhat_ky.kiem_chuoi_tep(self.p)['so_dong'], 4)


if __name__ == '__main__':
    unittest.main()
