# -*- coding: utf-8 -*-
"""Lịch mạng vá chỗ hổng khi tệp lịch USD của EA hết hạn (gia.tin_mang_usd, gia.tin_usd, gia.tin_sap_toi) và ghép tên tin ForexFactory với số đo."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from so_cong_khai import gia, tin_phan_ung as TP

U = timezone.utc


def _mang(p: Path) -> None:
    p.write_text(json.dumps({'ds': [
        {'t': '2026-11-25T13:30:00+00:00', 'tien': 'USD', 'muc': 3, 'ten': 'Core PCE Price Index m/m'},
        {'t': '2026-12-04T13:30:00+00:00', 'tien': 'USD', 'muc': 3, 'ten': 'Non-Farm Employment Change'},
        {'t': '2026-12-04T15:00:00+00:00', 'tien': 'USD', 'muc': 2, 'ten': 'Vừa'},
        {'t': '2026-12-05T09:00:00+00:00', 'tien': 'EUR', 'muc': 3, 'ten': 'Tin EUR'}]}), encoding='utf-8')


class LichMang(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.goc = Path(self.d.name)
        self.mang = self.goc / 'lich-tin-mang.json'
        _mang(self.mang)
        self.cu = gia.LICH_MANG
        gia.LICH_MANG = self.mang
        gia._MANG.clear()

    def tearDown(self):
        gia.LICH_MANG = self.cu
        gia._MANG.clear()
        gia._nho_tin.clear()
        self.d.cleanup()

    def test_chi_lay_usd_muc_cao_sau_moc(self):
        tin, het = gia.tin_mang_usd(datetime(2026, 11, 26, tzinfo=U))
        self.assertEqual(tin, [(datetime(2026, 12, 4, 13, 30, tzinfo=U), 'Non-Farm Employment Change')])
        self.assertEqual(het, datetime(2026, 12, 5, 9, tzinfo=U))

    def test_tin_usd_bu_khi_tep_ea_het(self):
        ea = self.goc / 'ea.csv'
        ea.write_text('x', encoding='utf-8')
        st = ea.stat()
        phu = datetime(2026, 11, 26, 2, tzinfo=U)
        gia._TIN.update(key=(str(ea), st.st_mtime_ns, st.st_size), kq=([datetime(2026, 11, 25, 13, 30, tzinfo=U)], phu))
        try:
            news, het = gia.tin_usd({'lich_tin': str(ea)})
        finally:
            gia._TIN.clear()
        self.assertEqual(news, [datetime(2026, 11, 25, 13, 30, tzinfo=U), datetime(2026, 12, 4, 13, 30, tzinfo=U)])   # không lấy trùng tin 25/11
        self.assertEqual(het, datetime(2026, 12, 5, 9, tzinfo=U))
        self.assertEqual(gia.NGUON_TIN['ea_phu'], phu)

    def test_tin_sap_toi_noi_tiep(self):
        ea = self.goc / 'ea.csv'
        ea.write_text('time,currency,importance,event\n2026.11.25 13:30,USD,3,Core PCE Price Index m/m\n', encoding='utf-8')
        ds = gia.tin_sap_toi({'gia': {'lich_tin': str(ea)}}, datetime(2026, 11, 25, 12, tzinfo=U), 5)
        self.assertEqual([x['ten'] for x in ds], ['Core PCE Price Index m/m', 'Non-Farm Employment Change'])

    def test_ten_forexfactory_ghep_so_do(self):
        tep = self.goc / 'p.json'
        tep.write_text(json.dumps({'loai': [{'ten': 'Nonfarm Payrolls', 'n': 138, 'd15_tv': 5.6, 'd15_p90': 19.5}]}), encoding='utf-8')
        that = gia.tin_sap_toi
        gia.tin_sap_toi = lambda cfg, now, n: [{'luc': '2026-12-04T13:30:00+00:00', 'ten': 'Non-Farm Employment Change'}]
        try:
            kq = TP.tin_toi({}, datetime(2026, 12, 4, 13, tzinfo=U), 1, tep)
        finally:
            gia.tin_sap_toi = that
        self.assertEqual(kq['ds'][0]['d15_tv'], 5.6)


class MucTheoMT5(unittest.TestCase):
    """ForexFactory xếp nhiều tin MT5 coi là mạnh vào mức thấp; lịch mạng phải né đúng các tin MT5 né."""

    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.goc = Path(self.d.name)
        gia._CAO.clear()

    def tearDown(self):
        gia._CAO.clear()
        self.d.cleanup()

    def test_nang_muc_theo_mt5(self):
        mang = self.goc / 'm.json'
        mang.write_text(json.dumps({'ds': [
            {'t': '2026-11-25T13:30:00+00:00', 'tien': 'USD', 'muc': 1, 'ten': 'Unemployment Claims'},
            {'t': '2026-11-25T15:30:00+00:00', 'tien': 'USD', 'muc': 1, 'ten': 'Crude Oil Inventories'},
            {'t': '2026-11-23T14:45:00+00:00', 'tien': 'USD', 'muc': 2, 'ten': 'Flash Manufacturing PMI'},
            {'t': '2026-11-25T13:30:00+00:00', 'tien': 'USD', 'muc': 1, 'ten': 'Personal Income m/m'},
            {'t': '2026-12-01T15:00:00+00:00', 'tien': 'USD', 'muc': 2, 'ten': 'Fed Chair Warsh Speaks'},
            {'t': '2026-12-02T15:00:00+00:00', 'tien': 'EUR', 'muc': 1, 'ten': 'Unemployment Claims'}]}), encoding='utf-8')
        gia._MANG.clear()
        try:
            tin, _ = gia.tin_mang_usd(None, mang, gia.CAO_MT5_SAN)
            chi_ff, _ = gia.tin_mang_usd(None, mang, frozenset())
        finally:
            gia._MANG.clear()
        self.assertEqual([ten for _, ten in tin], ['Unemployment Claims', 'Crude Oil Inventories', 'Fed Chair Warsh Speaks'])
        self.assertEqual(chi_ff, [])

    def test_hoc_tu_tep_ea(self):
        ea = self.goc / 'ea.csv'
        ea.write_text('\n'.join([
            'time,currency,importance,event,country',
            '2023.01.05 13:30,USD,3,B,US',
            '2023.02.05 13:30,USD,3,B,US',
            '2025.03.05 13:30,USD,3,A,US',
            '2025.04.05 13:30,USD,3,A,US',
            '2025.05.05 13:30,USD,1,B,US',
            '2025.06.05 13:30,USD,1,B,US',
            '2025.07.05 13:30,USD,3,C,US',
            '2025.08.05 13:30,EUR,3,D,EU',
            '2025.09.05 13:30,EUR,3,D,EU',
            '2026.11.25 13:30,USD,3,A,US',
        ]) + '\n', encoding='utf-8')
        self.assertEqual(gia.ten_cao_mt5(str(ea)), frozenset({'A'}))   # B chỉ mạnh hơn 2 năm trước, C mới một lần, D không phải USD
        self.assertEqual(gia.ten_cao_mt5(str(self.goc / 'khong-co.csv')), gia.CAO_MT5_SAN)
        rong = self.goc / 'rong.csv'
        rong.write_text('x', encoding='utf-8')
        self.assertEqual(gia.ten_cao_mt5(str(rong)), gia.CAO_MT5_SAN)



class CuoiTuan(unittest.TestCase):
    def test_cho_lich_tuan_moi(self):
        from so_cong_khai import suc_khoe as SK
        phu = datetime(2026, 11, 27, 20, 30, tzinfo=U)                              # tin cuối tuần: tối thứ Sáu
        self.assertTrue(SK.cho_tuan_moi(phu, datetime(2026, 11, 28, 10, tzinfo=U)))   # thứ Bảy: chờ, không phải lỗi
        self.assertTrue(SK.cho_tuan_moi(phu, datetime(2026, 11, 30, 5, 59, tzinfo=U)))
        self.assertFalse(SK.cho_tuan_moi(phu, datetime(2026, 11, 30, 6, 0, tzinfo=U)))  # 13 giờ thứ Hai giờ Việt Nam: lỗi thật
        self.assertFalse(SK.cho_tuan_moi(datetime(2026, 11, 25, 13, 30, tzinfo=U), datetime(2026, 11, 26, tzinfo=U)))  # hết giữa tuần: lỗi thật


if __name__ == '__main__':
    unittest.main()
