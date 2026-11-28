"""Cảnh báo trên đường vẽ (canh_bao_ve.py): hình học theo số thứ tự nến, điều kiện cắt/vào/ra, kiểm đầu vào, vòng kiểm, Telegram chỉ chat riêng."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from so_cong_khai import canh_bao_ve as cbv

T0 = 1_795_000_000 - 1_795_000_000 % 900          # mốc tròn 15 phút
TIMES = [T0 + i * 900 for i in range(10)]


class HinhHocTest(unittest.TestCase):
    def test_chi_so_nhu_trang_bieu_do(self):
        self.assertEqual(cbv.chi_so(TIMES, TIMES[3], 900), 3.0)
        self.assertEqual(cbv.chi_so(TIMES, TIMES[3] + 400, 900), 3.0)          # trong nến 3
        self.assertEqual(cbv.chi_so(TIMES, TIMES[-1] + 1800, 900), 11.0)       # sau nến cuối: ngoại suy
        self.assertEqual(cbv.chi_so(TIMES, TIMES[0] - 900, 900), -1.0)

    def test_duong_theo_so_thu_tu_nen_qua_khoang_nghi(self):
        """Cuối tuần: nến 5 cách nến 4 hai ngày. Đường đi qua nến 0 và nến 4 vẫn tăng đều theo số nến, không theo thời gian."""
        times = TIMES[:5] + [TIMES[4] + 2 * 86400 + i * 900 for i in range(1, 6)]
        a = {'loai': 'duong', 'diem': [[times[0], 100.0], [times[4], 104.0]]}
        self.assertAlmostEqual(cbv.muc(a, 6, times, 900)[0], 106.0)

    def test_kenh_va_hop(self):
        k = {'loai': 'kenh', 'diem': [[TIMES[0], 100.0], [TIMES[2], 102.0]], 'lech': -3.0}
        self.assertEqual(cbv.muc(k, 4, TIMES, 900), [101.0, 104.0])
        h = {'loai': 'hop', 'diem': [[TIMES[0], 110.0], [TIMES[2], 105.0]]}
        self.assertEqual(cbv.muc(h, 9, TIMES, 900), [105.0, 110.0])


class DieuKienTest(unittest.TestCase):
    def test_cat(self):
        a = {'dk': 'cat_len'}
        self.assertEqual(cbv.kiem(a, 99, 101, [100], [100]), 'giá cắt lên')
        self.assertIsNone(cbv.kiem(a, 101, 99, [100], [100]))
        self.assertIsNone(cbv.kiem(a, 101, 102, [100], [100]))                  # đã ở trên từ trước: không báo
        self.assertEqual(cbv.kiem({'dk': 'cat'}, 101, 99, [100], [100]), 'giá cắt xuống')
        self.assertEqual(cbv.kiem({'dk': 'cat_len'}, 99, 100, [100], [100]), 'giá cắt lên')   # chạm đúng mức là đã cắt

    def test_duong_doc_di_qua_gia_dung_yen(self):
        """Giá đứng yên nhưng đường xu hướng đi lên vượt qua giá: giá cắt xuống đường."""
        self.assertEqual(cbv.kiem({'dk': 'cat'}, 100, 100, [99.5], [100.5]), 'giá cắt xuống')

    def test_vung(self):
        self.assertEqual(cbv.kiem({'dk': 'vao'}, 95, 101, [100, 105], [100, 105]), 'giá đi vào')
        self.assertEqual(cbv.kiem({'dk': 'ra'}, 101, 106, [100, 105], [100, 105]), 'giá thoát lên trên')
        self.assertEqual(cbv.kiem({'dk': 'ra'}, 101, 99, [100, 105], [100, 105]), 'giá thoát xuống dưới')
        self.assertIsNone(cbv.kiem({'dk': 'ra'}, 101, 104, [100, 105], [100, 105]))
        self.assertEqual(cbv.kiem({'dk': 'cat'}, 104, 106, [100, 105], [100, 105]), 'giá cắt cạnh trên')


class DauVaoTest(unittest.TestCase):
    def ok(self, **k):
        yc = {'loai': 'duong', 'tf': 'M15', 'dk': 'cat', 'ma': 'EURUSDp', 'diem': [[TIMES[0], 1.1], [TIMES[2], 1.2]], 'gia_tao': 1.15, **k}
        return cbv.chuan(yc, now=TIMES[-1])

    def test_hop_le(self):
        a = self.ok()
        self.assertEqual((a['loai'], a['tf'], a['dk'], a['ma']), ('duong', 'M15', 'cat', 'EURUSDp'))

    def test_tu_choi(self):
        for k in ({'loai': 'doc'}, {'tf': 'M2'}, {'dk': 'vao'}, {'ma': 'a/../b'}, {'diem': [[TIMES[0], 1.1]]},
                  {'diem': [[TIMES[0], float('nan')], [TIMES[1], 1]]}, {'diem': [[1, 1.1], [2, 1.2]]}, {'diem': [[TIMES[0], -1], [TIMES[1], 1]]}):
            with self.subTest(k=k), self.assertRaises((ValueError, TypeError)):
                self.ok(**k)
        with self.assertRaises(ValueError):
            self.ok(loai='kenh', dk='ra', lech=0)


class VongTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.goc = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_bao_mot_lan_khi_gia_cat(self):
        now = TIMES[-1] + 100
        ok, _, a = cbv.them({'loai': 'ngang', 'tf': 'M15', 'dk': 'cat_len', 'diem': [[TIMES[0], 100.0]], 'gia_tao': 99.0}, self.goc, now - 50)
        self.assertTrue(ok)
        gia = {'v': 99.5}
        lay = lambda ma, tf, tu=None: {'candles': [[t, 1, 1, 1, 1] for t in TIMES], 'bid': gia['v'], 'so_le': 2}   # noqa: E731
        nho = {}
        self.assertEqual(cbv.mot_luot(lay, self.goc, now, nho=nho), [])
        gia['v'] = 100.4
        moi = cbv.mot_luot(lay, self.goc, now + 5, nho=nho)
        self.assertEqual(len(moi), 1)
        self.assertEqual(moi[0]['mo_ta'], 'giá cắt lên')
        self.assertFalse(moi[0]['telegram'])                                    # chưa nối Telegram riêng: không gửi đi đâu
        x = cbv.doc(self.goc)
        self.assertEqual(x['ds'], [])                                           # báo một lần rồi bỏ
        self.assertEqual(x['da_bao'][-1]['id'], a['id'])

    def test_lap_lai_cach_10_phut(self):
        now = TIMES[-1]
        cbv.them({'loai': 'ngang', 'tf': 'M15', 'dk': 'cat', 'diem': [[TIMES[0], 100.0]], 'gia_tao': 99.0, 'lap': True}, self.goc, now)
        gia = {'v': 101}
        lay = lambda ma, tf, tu=None: {'candles': [[t, 1, 1, 1, 1] for t in TIMES], 'bid': gia['v']}   # noqa: E731
        nho = {}
        self.assertEqual(len(cbv.mot_luot(lay, self.goc, now + 1, nho=nho)), 1)
        gia['v'] = 99
        self.assertEqual(cbv.mot_luot(lay, self.goc, now + 60, nho=nho), [])        # cắt lại sau 1 phút: chưa báo
        gia['v'] = 101
        self.assertEqual(len(cbv.mot_luot(lay, self.goc, now + 700, nho=nho)), 1)
        self.assertEqual(len(cbv.doc(self.goc)['ds']), 1)

    def test_thi_truong_dong_cua_duong_khong_chay_theo_dong_ho(self):
        """Lỗi đã gặp: không có nến mới (cuối tuần) mà đường xu hướng vẫn đi lên theo đồng hồ, vượt giá đứng yên và báo sai."""
        now = TIMES[-1] + 60
        cbv.them({'loai': 'duong', 'tf': 'M15', 'dk': 'cat', 'diem': [[TIMES[0], 3490.0], [TIMES[-1], 3499.0]], 'gia_tao': 3500.0}, self.goc, now)
        lay = lambda ma, tf, tu=None: {'candles': [[t, 1, 1, 1, 1] for t in TIMES], 'bid': 3500.0, 'luc_gia': now}   # noqa: E731  tick cuối đứng yên
        nho = {}
        for phut in (1, 27, 60 * 24):                                             # 27 phút, rồi một ngày sau nến cuối: giá không đổi
            self.assertEqual(cbv.mot_luot(lay, self.goc, now + phut * 60, nho=nho), [], phut)

    def test_lap_lai_khong_bao_lai_sau_khi_khoi_dong_lai(self):
        now = TIMES[-1]
        cbv.them({'loai': 'ngang', 'tf': 'M15', 'dk': 'cat', 'diem': [[TIMES[0], 100.0]], 'gia_tao': 99.0, 'lap': True}, self.goc, now)
        lay = lambda ma, tf, tu=None: {'candles': [[t, 1, 1, 1, 1] for t in TIMES], 'bid': 101}   # noqa: E731
        self.assertEqual(len(cbv.mot_luot(lay, self.goc, now + 1, nho={})), 1)
        self.assertEqual(cbv.mot_luot(lay, self.goc, now + 700, nho={}), [])      # nho rỗng = webapp vừa khởi động lại; giá vẫn ở trên, không cắt mới

    def test_ten_trong_tin_telegram_duoc_thoat(self):
        a = {'ten': 'A&B<x>', 'tf': 'M15', 'loai': 'ngang', 'ghi_chu': ''}
        self.assertIn('A&amp;B&lt;x&gt;', cbv.soan(a, 'giá cắt lên', 1.5, [1.4], 2, TIMES[0]))

    def test_mat_gia_khong_lam_hong_vong(self):
        cbv.them({'loai': 'ngang', 'tf': 'M15', 'dk': 'cat', 'diem': [[TIMES[0], 100.0]]}, self.goc, TIMES[-1])

        def lay(ma, tf, tu=None):
            raise RuntimeError('MT5 đang tắt')
        self.assertEqual(cbv.mot_luot(lay, self.goc, TIMES[-1] + 5), [])
        self.assertEqual(len(cbv.doc(self.goc)['ds']), 1)

    def test_diem_moc_duoc_goi_va_loi_khong_lam_chet_vong(self):
        """KHI_BAO: vỏ app gắn thông báo Windows vào đây. Một hàm móc ném lỗi không được chặn các hàm sau, cũng không làm vòng báo lỗi."""
        b = {'ma': 'XAUUSD', 'tf': 'M15', 'gia': 2650.0}
        nhan = []

        def hong(x):
            raise RuntimeError('móc hỏng')
        vong = cbv.VongCanhVe(lambda ma, tf, tu=None: {})
        with (mock.patch.object(cbv, 'KHI_BAO', [hong, nhan.append]), mock.patch.object(cbv, 'mot_luot', lambda *a, **k: [b]),
              mock.patch.object(cbv, 'doc', return_value={'ds': [], 'da_bao': []})):          # không đọc tệp cảnh báo thật
            vong.mot_vong()
        self.assertEqual(nhan, [b])
        self.assertIsNone(vong.tt['loi'])


class TelegramRiengTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.goc = Path(self.tmp.name)
        self.p = [mock.patch.object(cbv.telegram_nhom, 'token', return_value='123456:' + 'A' * 35),
                  mock.patch.object(cbv.telegram_nhom, 'cai', return_value={'chat': '-1001234567890'})]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()
        self.tmp.cleanup()

    def test_khong_nhan_nhom_hay_kenh(self):
        for chat in ('-1001234567890', '-12345', 'abc', ''):
            ok, _ = cbv.chon_chat(chat, goc=self.goc, goi=lambda *a, **k: {'ok': True})
            self.assertFalse(ok, chat)
        self.assertEqual(cbv.cai(self.goc)['chat_rieng'], '')

    def test_gui_dung_chat_rieng(self):
        da_goi = []
        goi = lambda tk, lenh, du=None, timeout=15: (da_goi.append((lenh, du)), {'ok': True})[1]   # noqa: E731
        ok, _ = cbv.chon_chat('987654321', 'Harry', self.goc, goi)
        self.assertTrue(ok)
        self.assertEqual(da_goi[-1][1]['chat_id'], '987654321')
        kq = cbv.gui_rieng('thử', self.goc, goi)
        self.assertTrue(kq['ok'])
        self.assertTrue(all(du['chat_id'] == '987654321' for _, du in da_goi))

    def test_tim_chat_chi_lay_chat_rieng(self):
        upd = {'ok': True, 'result': [{'message': {'chat': {'id': 987654321, 'type': 'private', 'first_name': 'Harry'}}},
                                      {'message': {'chat': {'id': -100123, 'type': 'supergroup', 'title': 'Nhóm'}}}]}
        ok, ds = cbv.tim_chat(lambda tk, lenh, du=None, timeout=15: upd)
        self.assertTrue(ok)
        self.assertEqual([x['id'] for x in ds], ['987654321'])


class LayGiaTest(unittest.TestCase):
    """27/11/2026: vòng kiểm đọc thẳng nến và Bid từ MT5; gia.goi/da_ma.goi dựng cả trang biểu đồ, đo được tới 15 giây mỗi lần."""

    class MT5:
        TIMEFRAME_M15 = 15

        def __init__(self):
            self.hoi = []

        def copy_rates_from_pos(self, sym, tf, vi_tri, n):
            self.hoi.append((sym, tf, vi_tri, n))
            return [{'time': TIMES[i], 'open': 1, 'high': 2, 'low': 0.5, 'close': 1.5} for i in range(3)]

        def symbol_info_tick(self, sym):
            return type('T', (), {'bid': 3570.25})()

        def symbol_info(self, sym):
            return type('I', (), {'digits': 2})()

    def test_doc_thang_mt5(self):
        m = self.MT5()
        with mock.patch('so_cong_khai.da_ma._mt5', return_value=m), mock.patch('so_cong_khai.da_ma.ma_vang', return_value='XAUUSDp'):
            d = cbv.lay_tu_mt5(lambda: {'gia': {}})('', 'M15')
            self.assertEqual(m.hoi[0], ('XAUUSDp', 15, 0, 600))                 # mã rỗng = mã vàng; vị trí 0 gồm cả nến đang chạy
            self.assertEqual((d['bid'], d['so_le'], d['candles'][0][0]), (3570.25, 2, TIMES[0]))
            with self.assertRaises(ValueError):
                cbv.lay_tu_mt5(lambda: {})('', 'M7')
        with mock.patch('so_cong_khai.da_ma._mt5', return_value=None), self.assertRaises(RuntimeError):
            cbv.lay_tu_mt5(lambda: {})('EURUSDp', 'M15')

    def test_moc_cu_lay_nen_tu_moc(self):
        """Mốc hình cũ hơn 600 nến: lấy nến từ mốc (giờ UTC có múi giờ), để số thứ tự nến khớp biểu đồ."""
        import time as _t
        from datetime import timezone as _tz
        m = self.MT5()
        m.khoang = []
        m.copy_rates_range = lambda sym, tf, a, b: (m.khoang.append((a, b)), [{'time': TIMES[0], 'open': 1, 'high': 2, 'low': .5, 'close': 1}])[1]
        with mock.patch('so_cong_khai.da_ma._mt5', return_value=m), mock.patch('so_cong_khai.da_ma.ma_vang', return_value='XAUUSDp'):
            cbv.lay_tu_mt5(lambda: {})('', 'M15', _t.time() - 20 * 86400)
        a, _ = m.khoang[0]
        self.assertIs(a.tzinfo, _tz.utc)
        self.assertEqual(m.hoi, [])                                               # không dùng 600 nến gần nhất


class TrangTest(unittest.TestCase):
    def test_trang_bieu_do_co_phan_canh_bao(self):
        from so_cong_khai import bieu_do
        h = bieu_do.trang_bieu_do('Harry')
        self.assertIn('window.CBV={mo,tai,themGia,xoa,', h)
        self.assertLess(h.index('window.MNP'), h.index('window.CBV='))           # nạp sau menu chuột phải, bọc MNP.ve để vẽ chuông
        self.assertIn('.cbv-chuong{', h)
        self.assertIn("if(!TT||!g.LW||!g.D||window.PHAT_LAI)return", canh_bao_ve_js())


def canh_bao_ve_js():
    return cbv.JS


if __name__ == '__main__':
    unittest.main()
