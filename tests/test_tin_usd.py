# -*- coding: utf-8 -*-
"""gia.tin_usd: lịch tin USD chỉ được đọc lại khi tệp đổi (nút Phân tích và biểu đồ gọi nó liên tục), và kết quả phải đúng như hàm gốc trả."""
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from so_cong_khai import gia



def setUpModule():                                  # không để lịch mạng thật trên máy (du-lieu/lich-tin-mang.json) lọt vào bài kiểm tra này
    from so_cong_khai import gia as _g
    _g._LICH_MANG_THAT, _g.LICH_MANG = _g.LICH_MANG, Path(__file__).parent / 'khong-co-lich-mang.json'
    _g._MANG.clear()


def tearDownModule():
    from so_cong_khai import gia as _g
    _g.LICH_MANG = _g._LICH_MANG_THAT
    _g._MANG.clear()


class TinUsd(unittest.TestCase):
    def setUp(self):
        self.dem = 0
        self.goc_nap, self.goc_nho = gia._nap_ma, dict(gia._TIN)
        gia._TIN.clear()

        def doc(p):
            self.dem += 1
            if not Path(p).exists():
                return [], None
            moc = [datetime(2026, 11, int(x), 13, 30, tzinfo=timezone.utc) for x in Path(p).read_text(encoding='utf-8').split()]
            return moc, (max(moc) if moc else None)
        gia._nap_ma = lambda g: (None, None, None, SimpleNamespace(load_high_usd_news=doc))
        self.thu_muc = tempfile.TemporaryDirectory()
        self.tep = Path(self.thu_muc.name) / 'lich.csv'
        self.g = {'lich_tin': str(self.tep)}

    def tearDown(self):
        gia._nap_ma = self.goc_nap
        gia._TIN.clear()
        gia._TIN.update(self.goc_nho)
        self.thu_muc.cleanup()

    def test_doc_mot_lan_khi_tep_khong_doi(self):
        self.tep.write_text('5 12', encoding='utf-8')
        a = gia.tin_usd(self.g)
        b = gia.tin_usd(self.g)
        self.assertEqual(self.dem, 1)
        self.assertEqual(a, b)
        self.assertEqual([t.day for t in a[0]], [5, 12])
        self.assertEqual(a[1].day, 12)

    def test_doc_lai_khi_tep_doi(self):
        self.tep.write_text('5', encoding='utf-8')
        gia.tin_usd(self.g)
        self.tep.write_text('5 12 19', encoding='utf-8')
        st = self.tep.stat()
        os.utime(self.tep, ns=(st.st_atime_ns, st.st_mtime_ns + 2_000_000_000))    # chắc chắn giờ sửa tệp khác đi
        moc, phu = gia.tin_usd(self.g)
        self.assertEqual(self.dem, 2)
        self.assertEqual([t.day for t in moc], [5, 12, 19])
        self.assertEqual(phu.day, 19)

    def test_tep_chua_co_roi_xuat_hien(self):
        self.assertEqual(gia.tin_usd(self.g), ([], None))
        self.tep.write_text('7', encoding='utf-8')
        self.assertEqual([t.day for t in gia.tin_usd(self.g)[0]], [7])

    def test_nguoi_goi_sua_danh_sach_khong_lam_hong_ban_nho(self):
        self.tep.write_text('5 12', encoding='utf-8')
        gia.tin_usd(self.g)[0].clear()
        self.assertEqual(len(gia.tin_usd(self.g)[0]), 2)


if __name__ == '__main__':
    unittest.main()
