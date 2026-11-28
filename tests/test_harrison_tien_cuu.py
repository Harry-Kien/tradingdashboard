# -*- coding: utf-8 -*-
"""Sổ tiến cứu Harrison (so_cong_khai.harrison_tien_cuu): ghi trước kết quả, không trộn phiên bản, không dùng nến trước lúc ghi,
chấm đúng định nghĩa thực thi (TP 5 / SL 20, SL trước, nhảy giá, không giới hạn thời gian), thiếu dữ liệu là chưa xác định."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from so_cong_khai import harrison_tien_cuu as HT

NOW = datetime(2026, 11, 25, 10, 0, 30, tzinfo=timezone.utc)                      # thứ Tư
KH = HT.khoa_phien_ban({'version': 'harrison-3khung-research-1', 'selected': 'A', 'gate_passed': False})
PP = {'ma': 'harrison', 'co': True, 'huong': 'MUA', 'vao': 3555.0, 'sl': 3535.0, 'tp': [3560.0], 'nen': '2026-11-25T10:00:00+00:00'}
T = int(NOW.timestamp())


def nen(i, o, h, lo, c=None, t0=T):
    return [t0 + 300 * i, o, h, lo, c if c is not None else o]


class TienCuu(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_ghi_mot_lan_va_mot_lenh(self):
        a = HT.ghi_tin_hieu(self.out, PP, 3554.8, 3555.0, NOW, KH)
        self.assertEqual((a['vao'], a['sl'], a['tp'], a['spread']), (3555.0, 3535.0, 3560.0, 0.2))
        self.assertIsNone(HT.ghi_tin_hieu(self.out, PP, 3554.8, 3555.0, NOW, KH))                 # trùng nến
        self.assertIsNone(HT.ghi_tin_hieu(self.out, {**PP, 'nen': '2026-11-25T10:15:00+00:00'}, 1, 2, NOW + timedelta(minutes=15), KH))   # còn lệnh mở
        self.assertIsNone(HT.ghi_tin_hieu(self.out, {**PP, 'co': False}, 1, 2, NOW, KH))
        self.assertIsNone(HT.ghi_tin_hieu(self.out, PP, 1, 2, NOW + timedelta(minutes=6), HT.khoa_phien_ban({'selected': 'B'})))   # quá hạn 5 phút
        dau, ds = HT.doc(self.out, KH)
        self.assertEqual((dau['khoa'], dau['tp'], dau['sl'], len(ds)), (KH['khoa'], 5.0, 20.0, 1))

    def test_phien_ban_khac_tep_khac(self):
        HT.ghi_tin_hieu(self.out, PP, 3554.8, 3555.0, NOW, KH)
        kh2 = HT.khoa_phien_ban({'version': 'harrison-3khung-research-1', 'selected': 'B', 'gate_passed': True})
        self.assertNotEqual(KH['khoa'], kh2['khoa'])
        self.assertEqual(HT.doc(self.out, kh2), (None, []))
        self.assertIsNotNone(HT.ghi_tin_hieu(self.out, PP, 3554.8, 3555.0, NOW, kh2))             # không bị chặn bởi lệnh của phiên bản khác
        self.assertEqual(HT.tom_tat(self.out, KH)['so_tin_hieu'], 1)

    def test_cham(self):
        t = HT.ghi_tin_hieu(self.out, PP, 3554.8, 3555.0, NOW, KH)
        truoc = [nen(-3, 3555, 3600, 3500)]                                                        # trước lúc ghi: không được dùng
        self.assertEqual(HT.cham_mot(t, truoc + [nen(0, 3556, 3557, 3554)])['trang_thai'], 'chua_xac_dinh')
        tp = HT.cham_mot(t, truoc + [nen(0, 3556, 3557, 3554), nen(1, 3557, 3561, 3556)])
        self.assertEqual((tp['trang_thai'], tp['loi_gia'], tp['loi_gia_rong'], tp['r']), ('tp', 5.0, round(5 - 0.2 - 0.18, 3), 0.25))
        self.assertEqual(HT.cham_mot(t, [nen(0, 3556, 3561, 3530)])['trang_thai'], 'sl')            # chạm cả hai: SL trước
        self.assertEqual(HT.cham_mot(t, [nen(0, 3562, 3563, 3530)])['trang_thai'], 'tp_nhay')       # mở đã qua TP
        g = HT.cham_mot(t, [nen(0, 3556, 3557, 3554), nen(1, 3530, 3531, 3525)])                    # mở nhảy qua SL: thoát ở giá mở
        self.assertEqual((g['trang_thai'], g['gia_ra'], g['loi_gia']), ('sl_nhay', 3530, -25.0))
        lau = HT.cham_mot(t, [nen(i, 3556, 3557, 3554) for i in range(300)] + [nen(300, 3557, 3561, 3556)])   # 25 giờ sau vẫn tính: không giới hạn giữ lệnh
        self.assertEqual(lau['trang_thai'], 'tp')
        trong = HT.cham_mot(t, [nen(0, 3556, 3557, 3554), nen(20, 3556, 3557, 3554)])               # hở 100 phút giữa tuần
        self.assertEqual((trong['trang_thai'], len(trong['khoang_mat_du_lieu'])), ('chua_xac_dinh', 1))
        self.assertIn('khoảng trống', trong['ly_do'])

    def test_cham_ghi_so_va_tom_tat(self):
        HT.ghi_tin_hieu(self.out, PP, 3554.8, 3555.0, NOW, KH)
        self.assertEqual(HT.cham(self.out, [nen(0, 3556, 3557, 3554)], NOW, KH), [])               # chưa xác định: không ghi kết quả cuối
        moi = HT.cham(self.out, [nen(0, 3556, 3557, 3554), nen(1, 3557, 3561, 3556)], NOW, KH)
        self.assertEqual(len(moi), 1)
        self.assertEqual(HT.cham(self.out, [nen(1, 3557, 3561, 3556)], NOW, KH), [])               # không chấm lại
        s = HT.tom_tat(self.out, KH)
        self.assertEqual((s['so_tin_hieu'], s['da_co_ket_qua'], s['thang'], s['thua']), (1, 1, 1, 0))
        self.assertIn('chưa nói được gì về lợi thế', s['ghi_chu'])
        self.assertIn('chưa qua cổng', s['ghi_chu'])
        self.assertIsNotNone(HT.ghi_tin_hieu(self.out, {**PP, 'nen': '2026-11-25T11:00:00+00:00'}, 1, 2, NOW + timedelta(hours=1), KH))   # lệnh trước đã xong


if __name__ == '__main__':
    unittest.main()
