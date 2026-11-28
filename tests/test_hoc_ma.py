"""Bài kiểm cho phần đo phương pháp trên mã khác vàng: dùng MT5 giả, kiểm dạng kết quả, phép chấm bằng nến 5 phút, hệ số quy ra USD,
việc nhớ kết quả, và rằng mã nguồn không có lời gọi chọn mã hay đặt lệnh."""
import json
import os
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from so_cong_khai import bieu_do, da_ma, hoc_ma, phuong_phap as PP  # noqa: E402
from test_da_ma import HET, MT5Gia  # noqa: E402
from test_gia import MA_THAT  # noqa: E402


class MT5CoGia(MT5Gia):
    """Như MT5 giả, thêm các trường mà phần đo dùng để tính spread và quy ra USD."""

    def symbols_get(self):
        return [SimpleNamespace(**vars(s), point=10.0 ** -s.digits, spread=20, trade_tick_value=0.1, trade_tick_size=10.0 ** -s.digits)
                for s in super().symbols_get()]


@unittest.skipUnless(all(os.path.isdir(p) for p in MA_THAT), 'không có mã của dự án trên máy này')
class HocMaTest(unittest.TestCase):
    def setUp(self):
        self.that, self.chay = da_ma._mt5, hoc_ma.chay
        self.mt5 = MT5CoGia()
        da_ma._mt5 = lambda g: self.mt5
        hoc_ma._tt.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = {'ten': 'Thử', 'gia': {'ma_nguon': MA_THAT, 'ma_vang': 'XAUUSDp'}}

    def tearDown(self):
        da_ma._mt5, hoc_ma.chay = self.that, self.chay
        hoc_ma._tt.clear()
        self.tmp.cleanup()

    def test_chay_tren_nen_5_phut_cua_ma(self):
        kq = hoc_ma.chay(self.cfg, 'BTCUSDTp', HET)
        self.assertEqual((kq['ma'], kq['loi'], kq['don_vi'], kq['tu_nam']), ('BTCUSDTp', [], 'USD ở 0,01 lot', 2026))
        self.assertEqual(set(kq['luat']), set(PP.DS))
        self.assertEqual(kq['spread'], 2.0)                                          # 20 điểm × 0,1
        self.assertTrue(kq['tu'] < kq['cat'] < kq['den'])
        self.assertIn('phí hoa hồng của sàn chưa được trừ', kq['ghi_chu'])
        for ma, r in kq['luat'].items():
            self.assertEqual(sum(s['n'] for k, s in r['theo'].items() if '|' not in k), r['tat_ca']['n'], ma)
            self.assertIn('tat_ca', r['r1'])                                             # có cả số đo khi chốt ở 1R và ở mục tiêu lý thuyết
            self.assertIn('tat_ca', r['theo_muc_tieu'])
            self.assertEqual('mo_phong' in r['tat_ca'], r['tat_ca']['n'] >= 30, ma)                  # mô phỏng chuỗi lệnh khi đủ 30 lệnh
            if r['tat_ca']['n']:
                self.assertEqual(r['tat_ca']['theo_ky']['ky'], 'thang', ma)                          # chưa đầy năm dữ liệu: xét theo tháng
            for k, s in r['theo'].items():
                self.assertEqual(s['hoc']['n'] + s['kiem']['n'], s['n'], (ma, k))
                self.assertIn(s['nhan_xet'], ('giu', 'lo', 'khong_on', 'chua_du'))
        self.assertEqual([g[1:3] for g in self.mt5.goi if g[0] == 'BTCUSDTp'], [(list(self.mt5.__dict__).index('TIMEFRAME_M5'), 1)])   # một lần đọc M5, nến đã đóng
        json.dumps(kq)

    def test_tru_hoa_hong_theo_cai_dat(self):
        """10 USD mỗi lot (cả mở và đóng) là 0,10 USD mỗi lệnh 0,01 lot; cùng tín hiệu, cùng lệnh, chỉ lãi lỗ giảm đúng chừng đó."""
        goc = hoc_ma.chay(self.cfg, 'BTCUSDTp', HET)
        co = hoc_ma.chay({**self.cfg, 'hoc': {'hoa_hong_lot': 10}}, 'BTCUSDTp', HET)
        self.assertEqual(co['hoa_hong_lot'], 10.0)
        self.assertIn('đã trừ hoa hồng 10 USD mỗi lot', co['ghi_chu'])
        for ma, r in goc['luat'].items():
            a, b = r['tat_ca'], co['luat'][ma]['tat_ca']
            self.assertEqual(a['n'], b['n'], ma)
            if a['n']:
                self.assertAlmostEqual((a['tong'] - b['tong']) / a['n'], 0.10, delta=0.006, msg=ma)

    def test_ma_khong_hien_va_khong_co_mt5(self):
        with self.assertRaises(ValueError):
            hoc_ma.chay(self.cfg, 'AUDUSDp', HET)
        da_ma._mt5 = lambda g: None
        r = hoc_ma.lay(self.cfg, Path(self.tmp.name), 'BTCUSDTp', cho=True, now=HET)
        self.assertFalse(r['san_sang'])
        self.assertIn('MT5', r['loi'][0])

    def test_nho_ket_qua_theo_ma_va_ngay(self):
        dem = []
        hoc_ma.chay = lambda cfg, ma, now=None: dem.append(ma) or {'ma': ma, 'luat': {}, 'loi': []}
        out = Path(self.tmp.name)
        a = hoc_ma.lay(self.cfg, out, 'BTCUSDTp', cho=True, now=HET)
        b = hoc_ma.lay(self.cfg, out, 'BTCUSDTp', now=HET)
        self.assertTrue(a['san_sang'] and b['san_sang'])
        hoc_ma._tt.clear()
        self.assertTrue(hoc_ma.lay(self.cfg, out, 'BTCUSDTp', now=HET)['san_sang'])      # đọc lại từ out/hoc-BTCUSDTp.json
        hoc_ma.lay(self.cfg, out, 'EURUSDp', cho=True, now=HET)
        hoc_ma.lay(self.cfg, out, 'BTCUSDTp', cho=True, now=HET + timedelta(days=1))     # sang ngày mới thì tính lại
        self.assertEqual(dem, ['BTCUSDTp', 'EURUSDp', 'BTCUSDTp'])

    def test_trang_va_ma_nguon(self):
        html = bieu_do.trang_bieu_do('Thử')
        for must in ("'/api/hoc'+(ma?'?ma='", 'Đo trên dữ liệu của chính mã này', 'đo trên dữ liệu của chính mã', 'Mục tiêu lý thuyết', 'Tất cả phương pháp',
                     'aria-label="Phương pháp phân tích"', 'Công cụ vẽ', 'Fibonacci thoái lui', 'so-ve:', 'Số đo quá khứ của phương án này là lỗ', 'prefers-reduced-motion', 'id="tk"', '/api/tai-khoan', 'không đặt, sửa hay đóng lệnh', 'Sóng Elliott', 'Kỷ luật: đứng ngoài', 'Bảng xếp hạng phương pháp theo số đo',
                     'Mũi tên', 'Kênh song song', 'Bút vẽ tự do', 'Hoàn tác (Ctrl+Z)', 'hòa vốn cần hơn ${s1.hoa_von!=null', 'hòa vốn cần ${pc(s.hoa_von)}', '${mpTxt(s)}${kyTxt(s)}', 'năm có lãi','Dòng 95% dưới ô chốt 2R', 'block bootstrap'):
            self.assertIn(must, html)
        self.assertNotIn('Chưa phương pháp nào được đo trên mã này', html)
        src = Path(hoc_ma.__file__).read_text(encoding='utf-8')
        for banned in ('order_send', 'order_check', 'TRADE_ACTION', 'symbol_select', 'positions_get'):
            self.assertNotIn(banned, src)


class ChamNenLonTest(unittest.TestCase):
    def test_cham_bang_nen_5_phut_va_he_so(self):
        t = pd.Timestamp('2026-06-04', tz='UTC')
        phang = [(1.1000, 1.1002, 1.0999, 1.1000)]
        m5 = pd.DataFrame(phang * 2 + [(1.1000, 1.1031, 1.0999, 1.1030)] + phang * 400, columns=['open', 'high', 'low', 'close'],
                          index=pd.date_range(t, periods=403, freq='5min'))
        mua = {'t': t, 'huong': 'MUA', 'kieu': 'thi_truong', 'vao': 1.1000, 'sl': 1.0990, 'atr': 0.001}
        r = PP.cham([mua], m5, 0.0, phi=0.0, buoc=5, he_so=1000.0)                    # 1 giá = 1.000 USD ở 0,01 lot
        self.assertEqual((r[0]['ket'], r[0]['usd'], r[0]['r']), ('TP', 2.0, 2.0))      # rủi ro 0,0010 → chốt ở 0,0020 = 2,00 USD, không bị làm tròn về 0
        self.assertEqual(r[0]['ra'], (t + pd.Timedelta(minutes=10)).isoformat())
        het = PP.cham([mua], pd.DataFrame(phang * 400, columns=['open', 'high', 'low', 'close'], index=pd.date_range(t, periods=400, freq='5min')), 0.0, phi=0.0, buoc=5)
        self.assertEqual(het[0]['ket'], 'Hết giờ')
        self.assertEqual(het[0]['ra'], (t + pd.Timedelta(minutes=5 * (PP.GIU_PHUT // 5 - 1))).isoformat())    # giữ 24 giờ tính theo nến 5 phút


if __name__ == '__main__':
    unittest.main()
