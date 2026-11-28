# -*- coding: utf-8 -*-
"""Nhóm Telegram (so_cong_khai.telegram_nhom), với Telegram GIẢ: không có lời gọi mạng nào.

Kiểm: lần đầu chỉ đặt mốc; tín hiệu mới đúng bộ lọc được đăng một lần; dòng trùng và dòng quá muộn không đăng; kết quả trả lời đúng tin gốc và
đếm cả lệnh thua; tin sắp ra nhắc một lần; tổng kết một lần mỗi ngày; xem trước không gọi mạng; mã bot không lọt ra thông báo lỗi."""
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from so_cong_khai import telegram_nhom as T

TK = '123456789:' + 'A' * 35
NOW = datetime(2026, 11, 26, 3, 0, tzinfo=timezone.utc)                       # 10:00 giờ Việt Nam


def _dong(i, ma='bot:nen', tt='dang_mo', r=None, phut=1, **k):
    return {'id': i, 'luc': (NOW - timedelta(minutes=phut)).isoformat(), 'sym': 'XAUUSDp', 'ma': ma, 'ten': 'Luật bot tín hiệu', 'nhom': 'luat',
            'huong': 'BAN', 'vao': 3528.12, 'sl': 3554.0, 'tp': [3515.0, 3502.0, 3489.0, 3476.0], 'rr': [0.51, 1.01, 1.51, 2.01], 'cho': False,
            'so_le': 2, 'tt': tt, 'r': r, 'ly_do': 'H1, H4, D1 cùng giảm.', 'phien': 'Á', 'bien_do': 'vừa', 'bam': 'ab' * 32, **k}


# Kết quả thật của nút Phân tích lúc 15:57 UTC ngày 25/11/2026 (rút gọn)
PT = {'bid': 3448.72, 'tuoi_phut': 0, 'canh_bao': [], 'dong_thuan': {'MUA': 0, 'BAN': 2, 'khong': 2},
      'phuong_an': [{'ma': 'bot:nen', 'co': False}, {'ma': 'bot:xu_huong', 'co': True, 'huong': 'BAN'}, {'ma': 'ba_khung', 'co': True, 'huong': 'BAN'},
                    {'ma': 'dinh_day', 'co': False}],
      'boi_canh': {'xu_huong': {'D1': -1, 'H4': -1, 'H1': -1, 'trend': -1}, 'atr_m15': 18.67, 'ho_tro': 3426.69, 'khang_cu': 3489.77,
                   'vung': {'tren': {'loai': 'Khoảng trống giá', 'duoi': 3455.62, 'tren': 3459.17}, 'duoi': None}, 'phien': 'Mỹ', 'bien_do': 'cao',
                   'bien_do_ty_le': 1.65, 'lien_thi_truong': {'usd_ngay_pct': 0.14, 'cap': ['EURUSDp', 'GBPUSDp', 'USDJPYp']}},
      'ict': {'bsl': 3532.75, 'ssl': 3426.69, 'dinh_hom_truoc': 3678.23, 'day_hom_truoc': 3546.61}}


class GiaTele:
    def __init__(self):
        self.goi, self.so = [], 100

    def __call__(self, tk, lenh, du):
        self.goi.append((lenh, du))
        self.so += 1
        return {'ok': True, 'result': {'message_id': self.so}}


class Vong(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.goc = Path(self.d.name)
        (self.goc / 'du-lieu').mkdir()
        (self.goc / 'du-lieu' / 'telegram-token.txt').write_text(TK, encoding='utf-8')
        self.ds = [_dong(1, phut=600, tt='thang', r=0.5)]
        self.tele = GiaTele()
        self.tin = {'ds': []}

    def tearDown(self):
        self.d.cleanup()

    def luot(self, now=NOW, lay_pt=None):
        return T.mot_luot({}, now, self.goc, doc_nk=lambda: self.ds, tin_toi=lambda c, n: self.tin, goi=self.tele, lay_pt=lay_pt)

    def bat_gui(self):
        self.assertTrue(T.luu_cai({'chat': '@nhom_vang', 'link_moi': 'https://t.me/+abcDEF123', 'tong_ket': False}, self.goc)[0])
        self.assertTrue(T.doi_che_do('gui', self.goc)[0])

    def test_lan_dau_chi_dat_moc_roi_dang_moi(self):
        self.bat_gui()
        self.assertEqual(self.luot()['tin_hieu'], 0)                        # dòng cũ: không đăng lại lịch sử
        self.ds += [_dong(2), _dong(3, ma='ict'), _dong(4, trung_voi=2), _dong(5, phut=90)]
        dem = self.luot()
        self.assertEqual(dem['tin_hieu'], 1)                                 # chỉ #2: #3 sai bộ lọc, #4 trùng, #5 quá muộn
        lenh, du = self.tele.goi[0]
        self.assertEqual((lenh, du['chat_id'], du['parse_mode']), ('sendMessage', '@nhom_vang', 'HTML'))
        for must in ('🔴 BÁN', 'XAUUSD', '#2', '3.528,12', '3.554,00', 'TP1 3.515,00', '(+1 mức nữa)', 'Chấm thắng khi chạm TP1 (0,51R)', 'abababab', 'Không phải lời khuyên'):
            self.assertIn(must, du['text'])
        self.assertEqual(self.luot()['tin_hieu'], 0)                         # không đăng hai lần

    def test_ket_qua_tra_loi_tin_goc_va_dem_ca_lenh_thua(self):
        self.bat_gui()
        self.luot()
        self.ds += [_dong(2), _dong(3)]
        self.luot()
        msg2 = self.tele.goi[0][1]
        self.ds[1].update(tt='thua', r=-1.0)
        self.ds[2].update(tt='thang', r=0.51)
        dem = self.luot()
        self.assertEqual(dem['ket_qua'], 2)
        kq = [du for l, du in self.tele.goi if '❌' in du['text']][0]
        self.assertEqual(kq['reply_parameters']['message_id'], 101)
        self.assertIn('−1,00R', kq['text'])
        cuoi = self.tele.goi[-1][1]['text']
        self.assertIn('2 lệnh xong · thắng 1 · thua 1 · tổng <b>−0,49R</b>', cuoi)
        self.assertEqual(self.luot()['ket_qua'], 0)
        self.assertIsNotNone(msg2)

    def test_khong_tu_dang_nhanh_theo_yeu_cau_va_diem_vao_cu(self):
        self.bat_gui()
        self.luot()
        self.ds += [_dong(2, ma='bot:xu_huong'), _dong(3, phut=4), _dong(4)]
        self.assertEqual(self.luot()['tin_hieu'], 1)
        self.assertIn('#4', self.tele.goi[0][1]['text'])
        self.assertNotIn('🛡', T.soan_tin_hieu(_dong(5, ma='bot:xu_huong'),
                         {'tu': 2022, 'thang': 67.2, 'thang_goc': 52.7, 'r': 0.14, 'r_goc': 0.18}))

    def test_van_bao_ket_qua_nhanh_cu_da_dang(self):
        self.bat_gui()
        self.luot()
        st = T.trang_thai(self.goc)
        st['tin_hieu']['2'] = {'msg': 88, 'bao': 'dang_mo', 'that': True}
        T._luu_tt(st, self.goc)
        self.ds.append(_dong(2, ma='bot:xu_huong', tt='thua', r=-1.0))
        self.assertEqual(self.luot()['ket_qua'], 1)
        self.assertIn('#2', self.tele.goi[0][1]['text'])

    def test_thanh_tich_tach_nhanh_cu_va_nhanh_cho_nen(self):
        st = {'tin_hieu': {'1': {'that': True}, '2': {'that': True}, '3': {'that': True}}}
        rows = [_dong(1, ma='bot:xu_huong', tt='thua', r=-1.),
                _dong(2, ma='bot:nen', tt='thang', r=.5), _dong(3, ma='bot:nen')]
        t = T.thanh_tich(st, rows)
        a, b = t['theo_nhanh']
        self.assertEqual((a['n'], a['ty_le'], a['tong_r']), (1, 100., .5))
        self.assertEqual((b['n'], b['ty_le'], b['tong_r']), (1, 0., -1.))
        self.assertEqual((t['n'], t['tong_r'], t['mo']), (2, -.5, 1))
        self.assertFalse(a['du_mau'])

    def test_tin_sap_ra_va_tong_ket(self):
        self.bat_gui()
        T.luu_cai({'tong_ket': True, 'gio_tong_ket': 22}, self.goc)
        self.tin = {'ds': [{'luc': '2026-11-26T03:10:00+00:00', 'ten': 'Nonfarm Payrolls', 'con_phut': 10, 'd15_tv': 9.1, 'd15_p90': 30.2},
                           {'luc': '2026-11-26T05:00:00+00:00', 'ten': 'Xa', 'con_phut': 120, 'd15_tv': None, 'd15_p90': None}]}
        dem = self.luot()
        self.assertEqual((dem['tin_tuc'], dem['tong_ket']), (1, 0))
        self.assertIn('10 phút nữa: Nonfarm Payrolls', self.tele.goi[0][1]['text'])
        self.assertIn('9,1 giá', self.tele.goi[0][1]['text'])
        self.assertEqual(self.luot()['tin_tuc'], 0)
        toi = NOW + timedelta(hours=12, minutes=5)                            # 22:05 giờ Việt Nam
        self.tin = {'ds': []}
        self.assertEqual(self.luot(toi)['tong_ket'], 1)
        self.assertIn('Tổng kết ngày 26/11/2026', self.tele.goi[-1][1]['text'])
        self.assertEqual(self.luot(toi + timedelta(minutes=30))['tong_ket'], 0)

    def test_xem_truoc_khong_goi_mang(self):
        self.luot()
        self.ds.append(_dong(2))
        self.assertEqual(self.luot()['tin_hieu'], 1)
        self.assertEqual(self.tele.goi, [])
        tin = json.loads((self.goc / 'du-lieu' / 'telegram-tin.json').read_text(encoding='utf-8'))
        self.assertEqual(tin[-1]['che_do'], 'xem_truoc')

    def test_phan_tich_dung_gio_mot_lan(self):
        self.bat_gui()
        self.assertTrue(T.luu_cai({'gio_phan_tich': '10, 19'}, self.goc)[0])            # NOW là 10:00 giờ Việt Nam
        self.tin = {'ds': [{'luc': '2026-11-26T13:30:00+00:00', 'ten': 'Nonfarm Payrolls', 'con_phut': 630, 'd15_tv': 9.1, 'd15_p90': 30.2}]}
        goi = []
        lay = lambda cfg: goi.append(1) or PT                                            # noqa: E731
        self.assertEqual(self.luot(lay_pt=lay)['phan_tich'], 1)
        van = [du['text'] for l, du in self.tele.goi if 'Phân tích vàng' in du['text']][0]
        for must in ('Phân tích vàng XAUUSD · 10:00 26/11/2026', 'Giá: <b>3.448,72</b> · phiên Mỹ', 'D1 🔴 giảm · H4 🔴 giảm · H1 🔴 giảm → ba khung cùng giảm',
                     'USD hôm nay</b>: tăng 0,14% (đo qua EURUSD, GBPUSD, USDJPY)', 'Kháng cự gần: <b>3.489,77</b>', 'Hỗ trợ gần: <b>3.426,69</b>',
                     'khoảng trống giá 3.455,62–3.459,17', 'Đỉnh / đáy hôm trước: 3.678,23 / 3.546,61', 'biên độ hôm nay cao (1,65 lần mức thường)',
                     '• Luật bot: chưa có tín hiệu (số đo dài nhất', '• Ba khung: BÁN (thắng nhiều', '• Đỉnh/đáy 8 giờ: chưa có tín hiệu (lỗ ở 2023–2025, chỉ để tham khảo)', '20:30 26/11 · Nonfarm Payrolls · 15 phút sau tin vàng thường chạy 9,1 giá', 'Không phải lời khuyên'):
            self.assertIn(must, van)
        self.assertEqual(self.luot(lay_pt=lay)['phan_tich'], 0)                           # một lần mỗi khe giờ
        self.assertEqual(len(goi), 1)

    def test_phan_tich_bo_qua_gia_cu_va_sai_gio(self):
        self.bat_gui()
        T.luu_cai({'gio_phan_tich': '10'}, self.goc)
        goi = []
        cu = dict(PT, tuoi_phut=300)                                                     # cuối tuần: giá cũ, không đăng
        self.assertEqual(self.luot(lay_pt=lambda cfg: goi.append(1) or cu)['phan_tich'], 0)
        self.assertEqual(self.luot(lay_pt=lambda cfg: goi.append(1) or cu)['phan_tich'], 0)
        self.assertEqual(len(goi), 1)                                                    # không thử lại mỗi 30 giây
        self.assertFalse(any('Phân tích vàng' in du['text'] for _, du in self.tele.goi))
        T.luu_cai({'gio_phan_tich': '8'}, self.goc)
        self.luot(NOW + timedelta(days=1), lay_pt=lambda cfg: goi.append(1) or PT)      # 10:00 ngày sau, không phải giờ đã chọn
        self.assertEqual(len(goi), 1)
        self.assertFalse(T.luu_cai({'gio_phan_tich': '25'}, self.goc)[0])
        self.assertFalse(T.luu_cai({'gio_phan_tich': '1,2,3,4,5'}, self.goc)[0])

    def test_lenh_xem_truoc_khong_lot_len_kenh(self):
        T.luu_cai({'chat': '@nhom_vang', 'tong_ket': False}, self.goc)
        self.luot()
        self.ds.append(_dong(2))
        self.assertEqual(self.luot()['tin_hieu'], 1)                         # #2 chỉ soạn lúc xem trước
        self.assertTrue(T.doi_che_do('gui', self.goc)[0])                   # lần đầu gửi thật: đặt lại mốc
        self.luot()
        self.ds[1].update(tt='thang', r=0.51)
        self.ds.append(_dong(3))
        dem = self.luot()
        self.assertEqual((dem['tin_hieu'], dem['ket_qua']), (1, 0))         # #3 mới thì đăng; #2 chưa từng lên kênh nên không báo kết quả
        self.assertEqual(len(self.tele.goi), 1)
        self.ds[-1].update(tt='thua', r=-1.0)
        self.assertEqual(self.luot()['ket_qua'], 1)
        self.assertIn('1 lệnh xong · thắng 0 · thua 1', self.tele.goi[-1][1]['text'])   # thành tích chỉ có lệnh đã lên kênh
        T.doi_che_do('xem_truoc', self.goc)
        T.doi_che_do('gui', self.goc)                                        # bật lại: không xóa thành tích công khai
        self.assertEqual(T.thanh_tich(T.trang_thai(self.goc), self.ds)['n'], 1)

    def test_tat(self):
        T.doi_che_do('tat', self.goc)
        self.ds.append(_dong(2))
        self.assertEqual(self.luot(), {'tin_hieu': 0, 'ket_qua': 0, 'tin_tuc': 0, 'phan_tich': 0, 'tong_ket': 0})


class CaiDat(unittest.TestCase):
    def test_kiem_dau_vao_va_ma_bot(self):
        with tempfile.TemporaryDirectory() as d:
            goc = Path(d)
            self.assertFalse(T.luu_cai({'chat': 'nhom vang'}, goc)[0])
            self.assertFalse(T.luu_cai({'link_moi': 'http://lua-dao.com'}, goc)[0])
            self.assertFalse(T.doi_che_do('gui', goc)[0])                     # chưa có mã nhóm
            self.assertTrue(T.luu_cai({'chat': '-1001234567890', 'ma': 'bot:, ba_khung'}, goc)[0])
            self.assertEqual(T.cai(goc)['ma'], ['bot:', 'ba_khung'])
            with mock.patch.dict(os.environ, {'HARRY_TELEGRAM_TOKEN': ''}):
                ok, ly_do = T.doi_che_do('gui', goc)                         # chưa có mã bot
                self.assertFalse(ok)
                self.assertIn('telegram-token.txt', ly_do)
                (goc / 'du-lieu' / 'telegram-token.txt').write_text('sai', encoding='utf-8')
                self.assertEqual(T.token(goc), '')

    def test_ma_bot_khong_lot_ra_loi(self):
        with tempfile.TemporaryDirectory() as d:
            goc = Path(d)
            (goc / 'du-lieu').mkdir()
            (goc / 'du-lieu' / 'telegram-token.txt').write_text(TK, encoding='utf-8')
            T.luu_cai({'chat': '@nhom_vang'}, goc)
            T.doi_che_do('gui', goc)
            kq = T.gui('x', 'thu', goc=goc, goi=lambda tk, l, du: {'ok': False, 'description': f'lỗi ở {tk}'})
            self.assertFalse(kq['ok'])
            self.assertNotIn(TK, kq['loi'])
            self.assertNotIn(TK, (goc / 'du-lieu' / 'telegram-tin.json').read_text(encoding='utf-8'))

    def test_kenh_mac_dinh(self):
        from so_cong_khai import thuong_hieu
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(T.link_moi({}, Path(d)), thuong_hieu.KENH_TELEGRAM)              # bản cài mới: vẫn dẫn tới kênh của chủ dự án
            self.assertEqual(T.link_moi({'nhom_telegram': 'https://t.me/khac'}, Path(d)), 'https://t.me/khac')
        self.assertIn(f'href="{thuong_hieu.KENH_TELEGRAM}"', __import__('so_cong_khai.trang', fromlist=['x']).thanh_dau('x', 'tong'))

    def test_goi_y_hoa_von_sau_tp1(self):
        from so_cong_khai import giu_lenh
        with tempfile.TemporaryDirectory() as d:
            tep = Path(d) / 'b.json'
            self.assertIsNone(giu_lenh.so_do(tep))
            tep.write_text(json.dumps({'cat_nam': 2022, 'D2': {'bang': {'TLB': {'kiem': {'n': 1850, 'thang': 67.2, 'r_tb': 0.1429, 'dd': 17.7}},
                                                                         'TL': {'kiem': {'n': 1850, 'thang': 52.7, 'r_tb': 0.1809, 'dd': 22.6}}}}}), encoding='utf-8')
            hv = giu_lenh.so_do(tep)
        self.assertEqual(giu_lenh.cau(hv), 'Giữ lệnh an toàn hơn: sau khi chạm TP1, dời dừng lỗ về giá vào. Đo trên 1.850 lệnh từ 2022: thắng 67,2% '
                                           'thay vì 52,7%, sụt giảm lớn nhất 17,7R thay vì 22,6R; đổi lại lời mỗi lệnh +0,14R thay vì +0,18R.')
        th = T.soan_tin_hieu(_dong(2), hv)
        self.assertIn('🛡 Gợi ý giữ lệnh: chạm TP1 thì dời dừng lỗ phần còn lại về giá vào 3.528,12. Đo từ 2022: thắng 67,2% thay vì 52,7%', th)
        self.assertIn('lời mỗi lệnh +0,14R thay vì +0,18R', th)
        self.assertNotIn('🛡', T.soan_tin_hieu(_dong(2, ma='ict'), hv))       # chỉ luật bot có số đo này
        self.assertNotIn('🛡', T.soan_tin_hieu(_dong(2)))                     # tắt gợi ý
        t = {'tu': None, 'n': 1, 'thang': 1, 'thua': 0, 'tong_r': 0.51, 'mo': 0}
        self.assertIn('🛡 Ai giữ phần còn lại: dời dừng lỗ về giá vào 3.528,12.', T.soan_ket_qua(_dong(2, tt='thang', r=0.51), t, hv))
        self.assertNotIn('🛡', T.soan_ket_qua(_dong(2, tt='thua', r=-1.0), t, hv))

    def test_loi_cu_xoa_khi_gui_lai_duoc(self):
        with tempfile.TemporaryDirectory() as d:
            goc = Path(d)
            (goc / 'du-lieu').mkdir()
            (goc / 'du-lieu' / 'telegram-token.txt').write_text(TK, encoding='utf-8')
            T.luu_cai({'chat': '@nhom_vang'}, goc)
            T.doi_che_do('gui', goc)
            T.gui('x', 'thu', goc=goc, goi=lambda tk, l, du: {'ok': False, 'description': 'URLError 10054'})
            self.assertIn('URLError 10054 (lúc ', T.TT.get('loi', ''))
            T.gui('x', 'thu', goc=goc, goi=lambda tk, l, du: {'ok': True, 'result': {'message_id': 7}})
            self.assertNotIn('loi', T.TT)

    def test_so(self):
        self.assertEqual((T.so(3528.12), T.so(-0.49), T.so(12345.6, 1)), ('3.528,12', '−0,49', '12.345,6'))

    def test_tim_nhom(self):
        with tempfile.TemporaryDirectory() as d:
            goc = Path(d)
            (goc / 'du-lieu').mkdir()
            (goc / 'du-lieu' / 'telegram-token.txt').write_text(TK, encoding='utf-8')
            ok, ds = T.tim_nhom(goc, goi=lambda tk, l, du: {'ok': True, 'result': [
                {'message': {'chat': {'id': -1001, 'title': 'Vàng', 'type': 'supergroup'}}}, {'message': {'chat': {'id': 5, 'type': 'private'}}}]})
            self.assertTrue(ok)
            self.assertEqual(ds, [{'id': '-1001', 'ten': 'Vàng', 'loai': 'supergroup'}])


if __name__ == '__main__':
    unittest.main()


class AnhBieuDo(unittest.TestCase):
    """Tin tín hiệu kèm ảnh biểu đồ (tùy chọn 'anh_bieu_do', mặc định tắt). Telegram giả, chụp ảnh giả: không mạng, không trình duyệt."""
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.goc = Path(self.d.name)
        (self.goc / 'du-lieu').mkdir()
        (self.goc / 'du-lieu' / 'telegram-token.txt').write_text(TK, encoding='utf-8')
        self.anh = self.goc / 'lenh-2.png'
        self.anh.write_bytes(b'\x89PNG\r\n\x1a\nGIA')
        self.tele = GiaTele()
        self.ds = [_dong(1, phut=600, tt='thang', r=0.5)]
        self.chup = []

    def tearDown(self):
        self.d.cleanup()

    def bat(self, anh=True):
        self.assertTrue(T.luu_cai({'chat': '@nhom_vang', 'tong_ket': False, 'anh_bieu_do': anh}, self.goc)[0])
        self.assertTrue(T.doi_che_do('gui', self.goc)[0])

    def luot(self):
        return T.mot_luot({}, NOW, self.goc, doc_nk=lambda: self.ds, tin_toi=lambda c, n: {'ds': []}, goi=self.tele,
                          chup=lambda r: self.chup.append(r['id']) or self.anh)

    def test_mac_dinh_tat_va_khong_chup(self):
        self.assertFalse(T.cai(self.goc)['anh_bieu_do'])
        self.bat(anh=False)
        self.luot()
        self.ds.append(_dong(2))
        self.luot()
        self.assertEqual(self.chup, [])
        self.assertEqual([g[0] for g in self.tele.goi], ['sendMessage'])

    def test_mot_tin_anh_co_chu_thich_va_ket_qua_tra_loi_dung_tin(self):
        self.bat()
        self.luot()
        self.ds.append(_dong(2))
        self.assertEqual(self.luot()['tin_hieu'], 1)
        self.assertEqual(self.chup, [2])                                     # chụp một lần cho tín hiệu mới
        lenh, du = self.tele.goi[-1]
        self.assertEqual((lenh, du['_anh'], du['parse_mode']), ('sendPhoto', str(self.anh), 'HTML'))
        self.assertIn('#2', du['caption'])
        self.assertIn('Không phải lời khuyên', du['caption'])                # dòng miễn trừ còn nguyên
        msg = self.tele.so
        st = T.trang_thai(self.goc)['tin_hieu']['2']
        self.assertEqual((st['msg'], st['that']), (msg, True))
        self.luot()
        self.assertEqual(self.chup, [2])                                     # không chụp lại tín hiệu đã đăng
        self.ds[-1] = _dong(2, tt='thang', r=0.51)
        self.luot()
        lenh, du = self.tele.goi[-1]
        self.assertEqual((lenh, du['reply_parameters']['message_id']), ('sendMessage', msg))
        tin = json.loads((self.goc / 'du-lieu' / 'telegram-tin.json').read_text(encoding='utf-8'))
        self.assertEqual(next(x for x in tin if x['loai'] == 'tin_hieu')['anh'], 'lenh-2.png')   # chỉ ghi tên tệp, không nhúng ảnh

    def test_chu_dai_thi_gui_anh_roi_gui_chu(self):
        self.bat()
        self.luot()
        self.ds.append(_dong(2, ly_do='x' * 1100))
        self.luot()
        (l1, d1), (l2, d2) = self.tele.goi[-2:]
        self.assertEqual((l1, l2), ('sendPhoto', 'sendMessage'))
        self.assertNotIn('caption', d1)
        self.assertIn('Không phải lời khuyên', d2['text'])
        self.assertEqual(T.trang_thai(self.goc)['tin_hieu']['2']['msg'], self.tele.so)   # mã tin là của tin chữ

    def test_gui_anh_loi_thi_van_gui_chu_va_che_ma_bot(self):
        self.bat()
        self.luot()
        goc_goi = self.tele

        def goi(tk, lenh, du):
            if lenh == 'sendPhoto':
                return {'ok': False, 'description': f'Bad Request: lỗi với {tk}'}
            return goc_goi(tk, lenh, du)
        self.tele = goi
        self.ds.append(_dong(2))
        self.assertEqual(self.luot()['tin_hieu'], 1)
        self.assertEqual(goc_goi.goi[-1][0], 'sendMessage')
        tin = json.loads((self.goc / 'du-lieu' / 'telegram-tin.json').read_text(encoding='utf-8'))
        x = next(x for x in tin if x['loai'] == 'tin_hieu')
        self.assertTrue(x['ok'])
        self.assertNotIn(TK, json.dumps(x, ensure_ascii=False))
        self.assertIn('Bad Request', x['loi_anh'])

    def test_khong_co_anh_thi_gui_chu(self):
        self.bat()
        self.luot()
        self.anh = None
        self.ds.append(_dong(2))
        self.luot()
        self.assertEqual(self.tele.goi[-1][0], 'sendMessage')

    def test_than_nhieu_phan(self):
        than, loai = T._nhieu_phan({'chat_id': '@nhom_vang', 'caption': 'Bán <b>vàng</b>', 'parse_mode': 'HTML', '_anh': str(self.anh)})
        ranh = loai.split('boundary=')[1]
        self.assertTrue(loai.startswith('multipart/form-data'))
        self.assertIn(b'name="photo"; filename="lenh-2.png"', than)
        self.assertIn(b'\x89PNG\r\n\x1a\nGIA', than)
        self.assertIn('Bán <b>vàng</b>'.encode('utf-8'), than)
        self.assertTrue(than.endswith(f'--{ranh}--\r\n'.encode()))
        self.assertNotIn(b'_anh', than)


class AnhLenh(unittest.TestCase):
    def test_duong_dan_va_khung_tu_ly_do(self):
        from so_cong_khai import anh_lenh                                    # noqa: PLC0415
        r = _dong(7, ly_do='Vào theo xu hướng; xu hướng H1, H4 và D1 cùng chiều. Khung M5.')
        self.assertEqual(anh_lenh.duong_dan('http://127.0.0.1:8765/', r), 'http://127.0.0.1:8765/bieu-do?anh=1&nk=7&ma=XAUUSDp&tf=M5')
        self.assertNotIn('tf=', anh_lenh.duong_dan('http://x', _dong(8, ly_do='không ghi khung')))

    def test_khong_co_playwright_thi_tra_none(self):
        from so_cong_khai import anh_lenh                                    # noqa: PLC0415
        with mock.patch.dict('sys.modules', {'playwright': None, 'playwright.sync_api': None}), tempfile.TemporaryDirectory() as d:
            self.assertIsNone(anh_lenh.chup('http://127.0.0.1:1', _dong(9), Path(d)))


class AnhKhongTrung(unittest.TestCase):
    """Lỗi tìm được khi rà soát (26/11/2026): chữ dài thì gửi ảnh rồi gửi chữ; chữ lỗi mạng thì lượt sau gửi lại cả hai, ảnh lên kênh hai lần.
    Và khi Telegram lỗi, mỗi 30 giây lại mở trình duyệt chụp lại cùng một ảnh."""
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.goc = Path(self.d.name)
        (self.goc / 'du-lieu').mkdir()
        (self.goc / 'du-lieu' / 'telegram-token.txt').write_text(TK, encoding='utf-8')
        self.anh = self.goc / 'lenh-2.png'
        self.anh.write_bytes(b'\x89PNG\r\n\x1a\nGIA')
        self.ds = [_dong(1, phut=600, tt='thang', r=0.5)]
        self.goi, self.chu_loi = [], True
        self.assertTrue(T.luu_cai({'chat': '@nhom_vang', 'tong_ket': False, 'anh_bieu_do': True}, self.goc)[0])
        self.assertTrue(T.doi_che_do('gui', self.goc)[0])

    def tearDown(self):
        self.d.cleanup()

    def tele(self, tk, lenh, du):
        self.goi.append(lenh)
        if lenh == 'sendMessage' and self.chu_loi:
            return {'ok': False, 'description': 'URLError 10054'}
        return {'ok': True, 'result': {'message_id': 500 + len(self.goi)}}

    def luot(self, chup):
        return T.mot_luot({}, NOW, self.goc, doc_nk=lambda: self.ds, tin_toi=lambda c, n: {'ds': []}, goi=self.tele, chup=chup)

    def test_chu_loi_thi_lan_sau_khong_gui_lai_anh(self):
        self.luot(lambda r: self.anh)
        self.ds.append(_dong(2, ly_do='x' * 1100))                          # chữ quá dài cho chú thích ảnh
        self.luot(lambda r: self.anh)
        self.assertEqual(self.goi, ['sendPhoto', 'sendMessage'])             # ảnh lên, chữ lỗi
        self.chu_loi = False
        self.assertEqual(self.luot(lambda r: self.anh)['tin_hieu'], 1)
        self.assertEqual(self.goi, ['sendPhoto', 'sendMessage', 'sendMessage'])   # lần thử lại chỉ gửi chữ
        self.assertEqual(self.goi.count('sendPhoto'), 1)

    def test_dung_lai_anh_da_chup(self):
        thu_muc = T.thu_muc_anh(self.goc)
        thu_muc.mkdir(parents=True, exist_ok=True)
        (thu_muc / 'lenh-7.png').write_bytes(b'\x89PNG')
        with mock.patch('so_cong_khai.anh_lenh.chup', side_effect=AssertionError('không được mở trình duyệt lần nữa')):
            self.assertEqual(T.chup_anh(_dong(7), self.goc), thu_muc / 'lenh-7.png')
