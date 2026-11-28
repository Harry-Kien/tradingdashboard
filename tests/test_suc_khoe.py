"""Bài kiểm cho phần Tình trạng hệ thống: mỗi kiểu hỏng âm thầm phải hiện ra đúng mức, và cuối tuần không báo nhầm."""
from functools import partial
from http_owner import owner_urlopen
import json
import os
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from so_cong_khai import gia, hoc, kiem_chung, song, suc_khoe, trang, web  # noqa: E402
from test_gia import MA_THAT, _kho  # noqa: E402

CO_MA = all(os.path.isdir(p) for p in MA_THAT)



def setUpModule():                                  # không để lịch mạng thật trên máy (du-lieu/lich-tin-mang.json) lọt vào bài kiểm tra này
    from so_cong_khai import gia as _g
    _g._LICH_MANG_THAT, _g.LICH_MANG = _g.LICH_MANG, Path(__file__).parent / 'khong-co-lich-mang.json'
    _g._MANG.clear()


def tearDownModule():
    from so_cong_khai import gia as _g
    _g.LICH_MANG = _g._LICH_MANG_THAT
    _g._MANG.clear()


class SucKhoeTest(unittest.TestCase):
    def setUp(self):
        gia._nho.clear()
        song._tt.update(deps=None, mt5=None, fr=None, thu=0.0, luc=0.0)
        for m in (kiem_chung, hoc):
            m._tt.update(key=None, kq=None, dang=False, loi=None, bat_dau=None)
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.start = datetime(2026, 11, 9, tzinfo=timezone.utc)
        _kho(self.d, self.start, 10 * 1440)
        self.het = self.start + timedelta(days=10)                             # kho nến dừng ở đây: đó là "giá gần nhất"
        self.out = self.d / 'out'
        self.cfg = {'ten': 'Thử', 'thu_muc_ra': str(self.out), 'gia': {'kho_m1': str(self.d), 'ma_nguon': MA_THAT, 'so_thang': 4}}

    def tearDown(self):
        gia._nho.clear()
        self.tmp.cleanup()

    def _so(self, **kw):
        acc = {'id': 'tk-1', 'ten': 'Demo thử', 'loi': [], 'tom': {'last_time': self.het - timedelta(hours=1), 'orphans': []}}
        return {'tai_khoan': [acc], 'loi': [], **kw}

    def _muc(self, r, ten):
        return next(m for m in r['muc'] if m['ten'].startswith(ten))

    def test_moi_thu_binh_thuong_va_cuoi_tuan_khong_bao_nham(self):
        r = suc_khoe.kiem(self.cfg, self.out, self._so(), now=self.het + timedelta(days=2))          # hai ngày sau khi thị trường nghỉ
        self.assertEqual(self._muc(r, 'Nhật ký EA')['muc'], 'tot')                                    # nhật ký chỉ cũ so với đồng hồ, không cũ so với giá
        self.assertEqual(self._muc(r, 'Kho nến')['muc'], 'tot')
        self.assertEqual(self._muc(r, 'Giá trực tiếp')['muc'], 'tot')                                 # đang tắt trong cấu hình: không phải lỗi
        self.assertEqual(r['dem']['loi'], 0 if CO_MA else 1)
        self.assertEqual(sum(r['dem'].values()), len(r['muc']))
        json.dumps(r)

    def test_nhat_ky_ea_dung_va_so_khong_doc_duoc(self):
        d = self._so(loi=[('Bot tín hiệu vàng', 'OperationalError: unable to open database file')])
        d['tai_khoan'][0]['tom']['last_time'] = self.het - timedelta(hours=30)
        d['tai_khoan'][0]['loi'] = [('EA X', 'FileNotFoundError')]
        r = suc_khoe.kiem(self.cfg, self.out, d, now=self.het + timedelta(hours=1))
        ea = self._muc(r, 'Nhật ký EA: Demo thử')
        self.assertEqual(ea['muc'], 'chu_y')
        self.assertIn('trước giá gần nhất 30 giờ', ea['chi_tiet'])
        self.assertEqual(self._muc(r, 'Bot tín hiệu vàng')['muc'], 'loi')
        self.assertEqual(self._muc(r, 'Nhật ký EA X')['muc'], 'loi')
        self.assertEqual([m['muc'] for m in r['muc']][:2], ['loi', 'loi'])                            # mục hỏng xếp lên đầu

    def test_so_dut_chuoi_va_lenh_thieu_dong_dong(self):
        d = self._so(xu_huong={'chain_ok': False, 'n_lines': 72}, dinh_day={'chain_ok': True, 'n_lines': 9})
        d['tai_khoan'][0]['tom']['orphans'] = [{'side': 'SELL'}]
        r = suc_khoe.kiem(self.cfg, self.out, d, now=self.het)
        self.assertEqual(self._muc(r, 'Sổ chạy bóng luật ba khung')['muc'], 'loi')
        self.assertEqual(self._muc(r, 'Sổ chạy bóng luật đỉnh/đáy')['muc'], 'tot')
        self.assertIn('chưa đối chiếu được', self._muc(r, 'Đối chiếu')['chi_tiet'])
        d['tai_khoan'][0]['doi_chieu'] = {'khop': True}
        r = suc_khoe.kiem(self.cfg, self.out, d, now=self.het)
        self.assertIn('vốn đã khớp', self._muc(r, 'Đối chiếu MT5')['chi_tiet'])

    def test_gia_tat_khong_phai_ket_noi_thanh_cong(self):
        with patch.object(song, 'khung_song', return_value=None):
            result = suc_khoe.kiem(self.cfg, self.out, self._so(), now=self.het)
        price = self._muc(result, 'Giá trực tiếp')
        self.assertEqual(price['id'], 'mt5-price')
        self.assertEqual(price['muc'], 'tot')  # tắt chủ động không phải lỗi hệ thống
        self.assertFalse(price['ket_noi'])
        self.assertFalse(price['gia_moi'])

    def test_co_phien_mt5_nhung_gia_cu_khong_bao_la_gia_moi(self):
        with patch.object(song, 'khung_song', return_value={'het': self.het}), patch.object(song, 'thong_tin', return_value={}):
            result = suc_khoe.kiem(self.cfg, self.out, self._so(), now=self.het + timedelta(minutes=30))
        price = self._muc(result, 'Giá trực tiếp')
        self.assertTrue(price['ket_noi'])
        self.assertFalse(price['gia_moi'])
        self.assertEqual(price['muc'], 'chu_y')
        with patch.object(song, 'khung_song', return_value={'het': self.het}), patch.object(song, 'thong_tin', return_value={}):
            result = suc_khoe.kiem(self.cfg, self.out, self._so(), now=self.het + timedelta(seconds=10))
        self.assertTrue(self._muc(result, 'Giá trực tiếp')['gia_moi'])

    def test_nhat_ky_cu_khong_ket_luan_ea_da_tat(self):
        data = self._so()
        data['tai_khoan'][0]['tom']['last_time'] = self.het - timedelta(hours=30)
        result = suc_khoe.kiem(self.cfg, self.out, data, now=self.het)
        item = self._muc(result, 'Nhật ký EA')
        self.assertIn('không phải tín hiệu EA còn chạy', item['lam'])
        self.assertNotIn('EA hoặc MT5 của tài khoản này có thể đã tắt', item['lam'])

    @unittest.skipUnless(CO_MA, 'không có mã của dự án trên máy này')
    def test_lich_tin_sap_het_va_da_het(self):
        f = self.d / 'lich.csv'
        f.write_text('time,currency,importance,event,country\n2026.11.18 13:30,USD,3,A,US\n2026.11.25 19:00,USD,3,B,US\n', encoding='utf-8')
        cfg = {**self.cfg, 'gia': {**self.cfg['gia'], 'lich_tin': str(f)}}
        cap = lambda now: self._muc(suc_khoe.kiem(cfg, self.out, self._so(), now=now), 'Lịch tin USD')    # noqa: E731
        self.assertEqual(cap(datetime(2026, 11, 10, tzinfo=timezone.utc))['muc'], 'tot')
        sap = cap(datetime(2026, 11, 21, 15, tzinfo=timezone.utc))
        self.assertEqual(sap['muc'], 'chu_y')
        self.assertIn('còn 4 ngày', sap['chi_tiet'])
        het = cap(datetime(2026, 11, 27, tzinfo=timezone.utc))
        self.assertEqual(het['muc'], 'loi')
        self.assertIn('không hoạt động', het['lam'])

    def test_vong_canh_va_viec_tinh_nen(self):
        hoc._tt['loi'] = 'RuntimeError: hỏng thử'
        r = suc_khoe.kiem(self.cfg, self.out, self._so(), vong={'dang_chay': False, 'ly_do': 'Vòng canh chưa chạy.'}, now=self.het)
        self.assertEqual(self._muc(r, 'Vòng canh')['muc'], 'chu_y')
        self.assertEqual(self._muc(r, 'Dữ liệu nhiều năm')['muc'], 'loi')
        self.assertEqual(self._muc(r, 'Kiểm chứng 4 tháng')['muc'], 'tot')
        r = suc_khoe.kiem(self.cfg, self.out, self._so(), vong={'dang_chay': True, 'ly_do': None}, now=self.het)
        self.assertEqual(self._muc(r, 'Vòng canh')['muc'], 'tot')

    def test_qua_may_chu_va_trang(self):
        cfgp = self.d / 'c.json'
        cfgp.write_text(json.dumps({**self.cfg, 'tai_khoan': []}), encoding='utf-8')
        srv = web.tao_may_chu(str(cfgp), port=0)
        open_owner = partial(owner_urlopen, root=cfgp.parent)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            with open_owner(f'http://127.0.0.1:{srv.server_address[1]}/api/tinh-trang', timeout=30) as r:
                j = json.loads(r.read())
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertEqual(set(j), {'luc', 'dem', 'muc'})
        self.assertIn('id="tt-he-thong"', trang._KHOI_TINH_TRANG)
        self.assertIn('/api/tinh-trang', trang.JS)
        src = Path(suc_khoe.__file__).read_text(encoding='utf-8')
        for banned in ('order_send', 'positions_get', 'MetaTrader5', 'unlink', 'write_text'):
            self.assertNotIn(banned, src)


if __name__ == '__main__':
    unittest.main()
