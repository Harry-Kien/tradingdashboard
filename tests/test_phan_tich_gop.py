"""Chế độ "Tất cả" của bảng phân tích (28/11/2026): phương pháp M15 cộng bộ quét đa khung M5/M15/M30, mỗi khung một thẻ.
Lỗi người dùng gặp: chế độ mặc định chỉ đa khung nên ICT/SMC, Elliott, Wyckoff, Price Action, Fibonacci, Harrison biến mất khỏi bảng."""
import unittest
from unittest.mock import patch

from so_cong_khai import bieu_do, entry_feed, nhat_ky, phan_tich, phuong_phap, smc_harry

import test_chart_auth_http as auth_http


def _ngan(cfg, ma, tf):
    return {'quy_trinh_ngan': True, 'phuong_phap': [{'ma': f'ngan:{tf}:pha_vo', 'ten': f'Phá vỡ · {tf}', 'chip': 'pha_vo', 'co': False},
                                                    {'ma': f'ngan:{tf}:hoi_ema', 'ten': f'Hồi về EMA · {tf}', 'chip': 'ema_hoi', 'co': False}]}


class GopTest(unittest.TestCase):
    def test_moi_khung_mot_the_khong_trung_chip_phuong_phap(self):
        data = {'phuong_phap': [{'ma': 'ict', 'chip': 'ict', 'co': True}, {'ma': 'pha_vo', 'chip': 'pha_vo', 'co': False}]}
        with patch.object(phan_tich, 'ngan', side_effect=_ngan):
            phan_tich.gop_da_khung({}, 'XAUUSD', data)
        chips = [p['chip'] for p in data['phuong_phap']]
        self.assertEqual(chips[:2], ['ict', 'pha_vo'])                       # phương pháp giữ nguyên, đứng trước
        self.assertEqual(chips[2:], ['da_khung_M5'] * 2 + ['da_khung_M15'] * 2 + ['da_khung_M30'] * 2)
        self.assertEqual(data['phuong_phap'][2]['ten_ngan'], 'Đa khung · M5')

    def test_bo_quet_loi_khong_mat_phuong_phap(self):
        data = {'phuong_phap': [{'ma': 'ict', 'chip': 'ict', 'co': True}]}
        with patch.object(phan_tich, 'ngan', side_effect=RuntimeError('MT5')):
            phan_tich.gop_da_khung({}, '', data)
        self.assertEqual(len(data['phuong_phap']), 1)

    def test_trang_mac_dinh_tat_ca(self):
        self.assertIn("'/api/phan-tich?danh_muc=1&tf='", bieu_do.JS)
        self.assertIn('epoch0===chartEpoch&&tf0===tf', bieu_do.JS)


class GopHTTP(unittest.TestCase):
    setUp, tearDown, start, stop = auth_http.ChartHTTP.setUp, auth_http.ChartHTTP.tearDown, auth_http.ChartHTTP.start, auth_http.ChartHTTP.stop
    req, signup = auth_http.ChartHTTP.req, auth_http.ChartHTTP.signup

    def test_gop_o_moi_khung_va_ghi_nhat_ky_truoc_khi_gop(self):
        owner = self.signup(self.a, 'gop_owner')
        ghi = []
        for tf in ('M5', 'M15', 'M30'):
            goc = {'phuong_phap': [{'ma': 'ict', 'chip': 'ict', 'co': True}], 'phuong_an': []}
            with self.subTest(tf=tf), patch.object(phan_tich, 'phan_tich', return_value=goc), patch.object(phan_tich, 'ngan', side_effect=_ngan), \
                    patch.object(nhat_ky, 'ghi', side_effect=lambda cfg, d: ghi.append(len(d['phuong_phap']))):
                status, result, _ = self.req(self.a, f'/api/phan-tich?tf={tf}&gop=1', None, owner)
                self.assertEqual(status, 200, result)
                self.assertEqual(result['khung_phan_tich'], 'M15')
                rows = result['phuong_phap']
                self.assertEqual([p['chip'] for p in rows[:7]], ['ict', 'da_khung_M5', 'da_khung_M5',
                                                                 'da_khung_M15', 'da_khung_M15', 'da_khung_M30', 'da_khung_M30'])
                self.assertEqual({p['ma'] for p in rows[7:]}, {f'{chip}:{k}' for chip in ('harry_smc', 'harry_xu_huong')
                                                               for k in ('M5', 'M15', 'M30')})
                self.assertEqual([p['khung'] for p in rows[7:9]], [tf, tf])
                self.assertTrue(all(p['quan_sat'] for p in rows[7:]))
        self.assertEqual(ghi, [1, 1, 1])                                         # nhật ký chỉ thấy phương pháp, không thấy bộ quét

    def test_danh_muc_giu_du_nhom_khi_thieu_du_lieu(self):
        owner = self.signup(self.a, 'reader_owner')
        goc = {'phuong_phap': [{'ma': 'ict', 'chip': 'ict', 'ten': 'ICT/SMC', 'co': False}], 'phuong_an': []}
        snapshot = {'ds': [{'tf': tf, 'trang_thai': 'gia_cu', 'loai': 'pha_vo'} for tf in ('M5', 'M15', 'M30')]}
        with (patch.object(phan_tich, 'phan_tich', return_value=goc), patch.object(entry_feed, 'doc', return_value=snapshot) as read,
              patch.object(smc_harry, 'doc', side_effect=RuntimeError('MT5')), patch.object(nhat_ky, 'ghi') as journal):
            status, result, _ = self.req(self.a, '/api/phan-tich?tf=M30&danh_muc=1', None, owner)
        self.assertEqual(status, 200, result)
        self.assertEqual(result['khung_bieu_do'], 'M30')
        self.assertEqual(result['khung_phan_tich'], 'M15')
        self.assertTrue(result['danh_muc_day_du'])
        rows = result['phuong_phap']
        self.assertEqual(len(rows), len(phuong_phap.DS) + 1 + 12)
        self.assertEqual(len(set(p['ma'] for p in rows)), len(rows))
        self.assertEqual({p['nhom_doc'] for p in rows}, {'phuong_phap', 'da_khung', 'nghien_cuu'})
        self.assertEqual(len(result['phuong_an']), 4)
        self.assertTrue(all(p['thieu_du_lieu'] and not p['hieu_luc'] for p in rows if p['nhom_doc'] == 'nghien_cuu'))
        self.assertEqual([p['khung'] for p in rows if p['nhom_doc'] == 'da_khung'], ['M30', 'M30', 'M5', 'M5', 'M15', 'M15'])
        self.assertTrue(all(not p['co'] and 'vao' not in p for p in rows if p['nhom_doc'] == 'da_khung'))
        read.assert_called_once()
        journal.assert_not_called()

    def test_bo_quet_chi_hien_muc_da_khoa(self):
        a = {'tf': 'M30', 'trang_thai': 'dat', 'loai': 'pha_vo', 'huong': 'MUA', 'vao': 100., 'sl': 99., 'tp': 102.,
             'rr': 2., 'dong': '2026-11-28T08:00:00+00:00', 'het': '2026-11-28T08:02:00+00:00', 'atr': 2., 'moc': 100.}
        r = phan_tich.ngan_tu_du_lieu({'ds': [a]}, 'M30')
        self.assertEqual(r['con_hieu_luc'], 0)
        self.assertNotIn('vao', r['phuong_phap'][0])
        a.update(plan_id='plan-123456', plan_hash='abc', plan_locked=True)
        r = phan_tich.ngan_tu_du_lieu({'ds': [a], 'minimum_stop': .25}, 'M30')
        p = r['phuong_phap'][0]
        self.assertEqual(r['con_hieu_luc'], 1)
        self.assertEqual((p['vao'], p['sl'], p['tp'], p['plan_locked']), (100., 99., [102.], True))
        self.assertEqual(p['thuc_thi']['stops'], .25)
        self.assertNotIn('cho_tick', p['thuc_thi'])


if __name__ == '__main__':
    unittest.main()
