"""Bài kiểm cho phần vị thế COT của vàng tương lai: đọc tệp của CFTC, gộp theo tuần, tóm tắt, và không bao giờ gọi mạng khi chưa bật.

Mọi bài ở đây dùng hàm tải giả; không bài nào được chạm tới cftc.gov."""
import io
import json
import sys
import tempfile
import unittest
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import bieu_do, cot, suc_khoe  # noqa: E402

DAU = ('"Market_and_Exchange_Names","As_of_Date_In_Form_YYMMDD","Report_Date_as_YYYY-MM-DD","CFTC_Contract_Market_Code","CFTC_Market_Code",'
       '"CFTC_Region_Code","CFTC_Commodity_Code","Open_Interest_All","Prod_Merc_Positions_Long_All","Prod_Merc_Positions_Short_All",'
       '"Swap_Positions_Long_All","Swap__Positions_Short_All","Swap__Positions_Spread_All","M_Money_Positions_Long_All",'
       '"M_Money_Positions_Short_All","M_Money_Positions_Spread_All","Other_Rept_Positions_Long_All","Other_Rept_Positions_Short_All"')


def dong(ngay: str, mm_mua: int, mm_ban: int, ma: str = '088691', ten: str = 'GOLD - COMMODITY EXCHANGE INC.', oi: int = 400000) -> str:
    return f'"{ten}",{ngay[2:4]}{ngay[5:7]}{ngay[8:]},{ngay},{ma},CMX,NYC,88,{oi}, 20000, 25000, 21000, 210000, 9000, {mm_mua}, {mm_ban}, 30000, 60000, 15000'


def tuan(n: int, cuoi: date = date(2026, 11, 17)) -> list[str]:
    """n ngày thứ Ba liên tiếp, kết thúc ở `cuoi`."""
    return [(cuoi - timedelta(days=7 * i)).isoformat() for i in range(n - 1, -1, -1)]


def nen_zip(van: str) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('f_year.txt', van)
    return b.getvalue()


class TaiGia:
    """Hàm tải giả: ghi lại địa chỉ được hỏi, trả tệp năm và tệp tuần dựng sẵn."""

    def __init__(self, nam: dict, tuan_moi: str, hong: bool = False):
        self.nam, self.tuan_moi, self.hong, self.goi = nam, tuan_moi, hong, []

    def __call__(self, url: str) -> bytes:
        self.goi.append(url)
        if self.hong:
            raise OSError('mất mạng')
        if url == cot.URL_TUAN:
            return self.tuan_moi.encode('latin-1')
        for y, van in self.nam.items():
            if url == cot.URL_NAM.format(nam=y):
                return nen_zip(van)
        raise OSError(f'404 {url}')


class CotTest(unittest.TestCase):
    def setUp(self):
        cot._tt.update(dang=False, loi=None)
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.cfg = {'cot': {'bat': True, 'tep': str(self.d / 'cot-vang.json'), 'tu_nam': 2025}}
        self.now = datetime(2026, 11, 23, 6, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.tmp.cleanup()

    def test_doc_tep_co_tieu_de_va_tep_tuan_khong_tieu_de(self):
        van = '\n'.join([DAU, dong('2026-11-10', 120000, 20000), dong('2026-11-10', 5, 6, ma='084691', ten='SILVER - COMMODITY EXCHANGE INC.'),
                         dong('2026-11-17', 121994, 19052, oi=407834)])
        ds = cot.doc_van(van)
        self.assertEqual([x['ngay'] for x in ds], ['2026-11-10', '2026-11-17'])                       # chỉ dòng vàng COMEX
        self.assertEqual((ds[1]['oi'], ds[1]['mm_mua'], ds[1]['mm_ban'], ds[1]['sw_mua'], ds[1]['sw_ban'], ds[1]['pm_mua'], ds[1]['pm_ban']),
                         (407834, 121994, 19052, 21000, 210000, 20000, 25000))
        self.assertEqual(cot.doc_van(dong('2026-11-17', 121994, 19052))[0]['mm_mua'], 121994)           # tệp tuần: không có dòng tiêu đề
        self.assertEqual(cot.doc_van('rác,không,phải,csv\n\n'), [])

    def test_gop_theo_ngay_ban_moi_thay_ban_cu(self):
        cu = cot.doc_van('\n'.join(dong(n, 100, 50) for n in ('2026-11-03', '2026-11-10')))
        moi = cot.doc_van('\n'.join(dong(n, 200, 50) for n in ('2026-11-17', '2026-11-10')))
        ds = cot.gop(cu, moi)
        self.assertEqual([(x['ngay'], x['mm_mua']) for x in ds], [('2026-11-03', 100), ('2026-11-10', 200), ('2026-11-17', 200)])

    def test_tom_tat_tuan_moi_nhat(self):
        ng = tuan(200)
        ds = cot.doc_van('\n'.join(dong(n, 100000 + 100 * i, 20000) for i, n in enumerate(ng)))         # mua ròng tăng đều mỗi tuần
        t = cot.tom(ds, now=self.now)
        self.assertEqual(t['ngay'], '2026-11-17')
        self.assertEqual(t['quy_rong'], 100000 + 19900 - 20000)
        self.assertEqual(t['quy_doi'], 100)
        self.assertEqual(t['hang'], 100)                                                               # cao nhất trong 156 tuần gần nhất
        self.assertEqual(t['hang_tuan'], cot.CUA_SO)
        self.assertEqual(t['nh_rong'], 21000 - 210000)
        self.assertEqual(t['sx_rong'], 20000 - 25000)
        self.assertEqual(t['tuoi_ngay'], 6)
        self.assertEqual(len(t['chuoi']), 52)
        self.assertIsNone(cot.tom([], now=self.now))
        ngan = cot.tom(ds[-10:], now=self.now)                                                          # chưa đủ lịch sử thì không xếp hạng
        self.assertIsNone(ngan['hang'])

    def test_khi_nao_can_tai(self):
        ds = cot.doc_van(dong('2026-11-17', 1, 1))
        co = lambda now, thu=None: cot.can_tai(ds, thu, now)                                           # noqa: E731
        self.assertTrue(cot.can_tai([], None, self.now))                                               # chưa có gì
        self.assertFalse(cot.can_tai([], self.now - timedelta(hours=1), self.now))                      # vừa thử xong thì chờ
        self.assertFalse(co(datetime(2026, 11, 26, tzinfo=timezone.utc)))                               # báo cáo kế chưa tới hạn công bố
        self.assertTrue(co(datetime(2026, 11, 27, 21, 0, tzinfo=timezone.utc)))                         # thứ Sáu kế, sau giờ công bố
        self.assertFalse(co(datetime(2026, 11, 27, 21, 0, tzinfo=timezone.utc), datetime(2026, 11, 27, 20, 40, tzinfo=timezone.utc)))

    def test_lan_dau_tai_cac_nam_roi_tep_tuan_va_luu_lai(self):
        ng = tuan(60)
        nam = {y: '\n'.join([DAU] + [dong(n, 100000, 20000) for n in ng[:-1] if n.startswith(str(y))]) for y in (2025, 2026)}
        tai = TaiGia(nam, dong(ng[-1], 121994, 19052))
        kq = cot.cap_nhat(self.cfg, now=self.now, tai=tai)
        self.assertEqual(tai.goi, [cot.URL_NAM.format(nam=2025), cot.URL_NAM.format(nam=2026), cot.URL_TUAN])
        self.assertEqual(len(kq['ds']), 60)
        luu = json.loads((self.d / 'cot-vang.json').read_text(encoding='utf-8'))
        self.assertEqual(luu['ds'][-1]['mm_mua'], 121994)
        r = cot.lay(self.cfg, now=self.now, tai=tai, cho=True)                                          # dữ liệu còn mới: không tải lại
        self.assertEqual(len(tai.goi), 3)
        self.assertTrue(r['san_sang'])
        self.assertEqual(r['tom']['ngay'], ng[-1])

    def test_tuan_sau_chi_tai_tep_tuan_va_lap_cho_trong(self):
        ng = tuan(60, cuoi=date(2026, 11, 3))
        (self.d / 'cot-vang.json').write_text(json.dumps({'thu_luc': None, 'ds': cot.doc_van('\n'.join(dong(n, 100000, 20000) for n in ng))}), encoding='utf-8')
        tai = TaiGia({}, dong('2026-11-10', 110000, 20000))
        kq = cot.cap_nhat(self.cfg, now=self.now, tai=tai)
        self.assertEqual(tai.goi, [cot.URL_TUAN])                                                       # liền tuần: chỉ một tệp nhỏ
        self.assertEqual(kq['ds'][-1]['ngay'], '2026-11-10')
        tai = TaiGia({2026: '\n'.join([DAU, dong('2026-11-17', 115000, 20000)])}, dong('2026-11-24', 120000, 20000))
        kq = cot.cap_nhat(self.cfg, now=self.now + timedelta(days=7), tai=tai)                          # webapp tắt một tuần: lấy tệp năm để lấp
        self.assertEqual(tai.goi, [cot.URL_TUAN, cot.URL_NAM.format(nam=2026)])
        self.assertEqual([x['ngay'] for x in kq['ds'][-3:]], ['2026-11-10', '2026-11-17', '2026-11-24'])

    def test_tai_hong_thi_giu_du_lieu_cu_va_bao_loi(self):
        cu = cot.doc_van('\n'.join(dong(n, 100000, 20000) for n in tuan(5, cuoi=date(2026, 10, 6))))
        (self.d / 'cot-vang.json').write_text(json.dumps({'thu_luc': None, 'ds': cu}), encoding='utf-8')
        r = cot.lay(self.cfg, now=self.now, tai=TaiGia({}, '', hong=True), cho=True)
        self.assertTrue(r['san_sang'])
        self.assertEqual(r['tom']['ngay'], '2026-10-06')
        self.assertIn('mất mạng', r['loi'])
        luu = json.loads((self.d / 'cot-vang.json').read_text(encoding='utf-8'))
        self.assertEqual(len(luu['ds']), 5)                                                             # không mất dòng nào
        self.assertIsNotNone(luu['thu_luc'])                                                            # nhớ lần thử để không gọi dồn dập
        tai = TaiGia({}, '', hong=True)
        cot.lay(self.cfg, now=self.now + timedelta(hours=1), tai=tai, cho=True)
        self.assertEqual(tai.goi, [])

    def test_chua_bat_thi_khong_bao_gio_goi_mang(self):
        tai = TaiGia({}, '')
        for cfg in ({}, {'cot': {'bat': False, 'tep': str(self.d / 'x.json')}}):
            self.assertEqual(cot.lay(cfg, now=self.now, tai=tai, cho=True), {'bat': False})
        self.assertEqual(tai.goi, [])

    def test_tinh_trang_he_thong_co_muc_cot(self):
        cu = cot.doc_van('\n'.join(dong(n, 100000, 20000) for n in tuan(5, cuoi=date(2026, 10, 6))))
        (self.d / 'cot-vang.json').write_text(json.dumps({'thu_luc': self.now.isoformat(), 'ds': cu}), encoding='utf-8')
        m = suc_khoe.muc_cot(self.cfg, self.now)
        self.assertEqual((m['ten'], m['muc']), ('Vị thế COT (CFTC)', 'chu_y'))                          # báo cáo cũ hơn ba tuần
        self.assertIn('06/10', m['chi_tiet'])
        moi = cot.doc_van('\n'.join(dong(n, 100000, 20000) for n in tuan(5)))
        (self.d / 'cot-vang.json').write_text(json.dumps({'thu_luc': self.now.isoformat(), 'ds': moi}), encoding='utf-8')
        self.assertEqual(suc_khoe.muc_cot(self.cfg, self.now)['muc'], 'tot')
        self.assertIsNone(suc_khoe.muc_cot({}, self.now))

    def test_trang_bieu_do_co_khung_cot_va_noi_ro_gioi_han(self):
        html = bieu_do.trang_bieu_do('Thử')
        for must in ('id="cot"', "fetch('/api/cot'", 'Vị thế lớn trên vàng tương lai', 'chốt thứ Ba, công bố thứ Sáu', 'không phải khối lượng trên sàn'):
            self.assertIn(must, html)


if __name__ == '__main__':
    unittest.main()
