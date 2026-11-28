"""Bài kiểm cho điểm mô hình: phép chấm điểm thuần số, đặc trưng tính được trên nến dựng tay và không nhìn tương lai, mặc định tắt khi cấu
hình không bật, và mã nguồn không có lời gọi đặt lệnh."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import bieu_do, mo_hinh, phuong_phap as PP  # noqa: E402

T0 = datetime(2026, 3, 2, tzinfo=timezone.utc)


def _khung(n=700):
    idx = pd.date_range(T0, periods=n, freq='15min')
    c = 100 + np.cumsum(np.sin(np.arange(n) / 7.0)) * 0.2
    m15 = pd.DataFrame({'open': np.roll(c, 1), 'high': c + 0.4, 'low': c - 0.4, 'close': c}, index=idx)
    m15.iloc[0, 0] = c[0]
    agg = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}
    return {'M15': m15, 'H1': m15.resample('1h').agg(agg).dropna(), 'D1': m15.resample('1D').agg(agg).dropna()}


class MoHinhTest(unittest.TestCase):
    def setUp(self):
        self.mh = {'cot': mo_hinh.cot(), 'tb': [0.0] * len(mo_hinh.cot()), 'lech': [1.0] * len(mo_hinh.cot()), 'he_so': [0.0] * len(mo_hinh.cot()), 'chan': 0.0,
                   'phan_vi': np.linspace(0.3, 0.7, 101).tolist()}
        self.mh['he_so'][self.mh['cot'].index('rsi')] = 1.0

    def test_cham_diem(self):
        x = dict.fromkeys(mo_hinh.cot(), 0.0)
        self.assertEqual(mo_hinh.diem(self.mh, x), {'p': 0.5, 'hang': 50})
        cao, thap = mo_hinh.diem(self.mh, {**x, 'rsi': 5.0}), mo_hinh.diem(self.mh, {**x, 'rsi': -5.0})
        self.assertEqual((cao['hang'], thap['hang']), (100, 0))                          # ngoài khoảng đã thấy thì chặn ở 0 và 100
        self.assertGreater(mo_hinh.diem(self.mh, {**x, 'rsi': 0.2})['p'], 0.5)
        self.assertIsNone(mo_hinh.diem(self.mh, {**x, 'rsi': float('nan')}))               # thiếu đặc trưng thì không chấm

    def test_dac_trung_khong_nhin_tuong_lai(self):
        fr = _khung()
        nen = (fr['M15'].index[650] + timedelta(minutes=15)).isoformat()
        pa = {'co': True, 'ma': 'ict', 'huong': 'MUA', 'vao': 100.0, 'sl': 99.0, 'nen': nen}
        x = mo_hinh.dac_trung(fr, pa)
        self.assertEqual(set(x), set(mo_hinh.cot()))
        self.assertEqual((x['pp_ict'], x['pp_fib'], x['cho']), (1.0, 0.0, 1.0))
        sau = {k: v.copy() for k, v in fr.items()}
        sau['M15'].iloc[651:, :] *= 3                                                      # đổi mọi nến SAU nến tín hiệu
        y = mo_hinh.dac_trung({**sau, 'H1': fr['H1'], 'D1': fr['D1']}, pa)
        for k in ('rui_atr', 'cach_ema50', 'rsi', 'vi_tri_24h', 'di_4h', 'than_nen', 'bien_nen'):
            self.assertAlmostEqual(x[k], y[k], places=9, msg=k)
        ban = mo_hinh.dac_trung(fr, {**pa, 'huong': 'BAN', 'sl': 101.0})
        self.assertAlmostEqual(ban['rsi'], -x['rsi'], places=9)                            # đặc trưng có chiều đổi dấu theo chiều lệnh
        self.assertIsNone(mo_hinh.dac_trung(fr, {**pa, 'nen': None}))
        self.assertIsNone(mo_hinh.dac_trung(fr, {**pa, 'ma': 'bot:nen'}))                  # luật trong sổ không có trong mô hình

    def test_mac_dinh_tat_va_gan_diem(self):
        fr = _khung(1400)                                                                  # đủ 240 nến H1 để tính được biên độ
        self.assertIsNone(mo_hinh.lay({'gia': {}}))                                        # cấu hình không bật thì không huấn luyện, không đọc tệp
        self.assertIsNone(mo_hinh.gan({'gia': {}}, fr, [{'co': True}]))
        that = mo_hinh.lay
        mo_hinh.lay = lambda cfg, cho=False: {**self.mh, 'n': 10, 'tu_nam': 2015, 'ngoai_mau': {}}
        try:
            pa = {'co': True, 'ma': 'ict', 'huong': 'MUA', 'vao': 100.0, 'sl': 99.0, 'nen': (fr['M15'].index[1350] + timedelta(minutes=15)).isoformat()}
            ngan = {**pa, 'nen': (_khung()['M15'].index[650] + timedelta(minutes=15)).isoformat()}
            self.assertIsNone(mo_hinh.diem(self.mh, mo_hinh.dac_trung(_khung(), ngan)))     # chưa đủ nến H1 để tính biên độ thì không chấm điểm
            khong = {'co': False, 'ma': 'fib'}
            tom = mo_hinh.gan({'mo_hinh': {'bat': True}}, fr, [pa, khong])
        finally:
            mo_hinh.lay = that
        self.assertTrue(tom['san_sang'])
        self.assertIn(pa['mo_hinh']['hang'], range(101))
        self.assertIsNone(khong['mo_hinh'])

    def test_dem_dong_thuan(self):
        t = pd.Timestamp('2026-06-01 10:00', tz='UTC')
        d = pd.DataFrame({'t': [t, t + pd.Timedelta(minutes=30), t + pd.Timedelta(minutes=60), t + pd.Timedelta(minutes=200), t + pd.Timedelta(minutes=60)],
                          'ma': ['ict', 'fib', 'pha_vo', 'ict', 'ict'], 'huong': ['MUA', 'MUA', 'BAN', 'MUA', 'MUA']})
        r = mo_hinh.them_dong_thuan(d)
        self.assertEqual(r['dt_cung'].tolist(), [0, 1, 0, 0, 1])           # fib thấy ict trước đó 30 phút; ict lúc 11:00 thấy fib; tín hiệu sau 200 phút thì không
        self.assertEqual(r['dt_nguoc'].tolist(), [0, 0, 2, 0, 1])          # pha_vo BÁN thấy ict và fib MUA; ict lúc 11:00 thấy pha_vo BÁN cùng lúc
        self.assertEqual(r['dt_cung'].iloc[0], 0)                          # không nhìn tín hiệu đến SAU

    def test_dong_thuan_dem_tren_moi_tin_hieu_khong_chi_tin_hieu_da_khop(self):
        # Lỗi rò rỉ đã gặp (23/11/2026): lúc học, đồng thuận chỉ đếm các tín hiệu VỀ SAU có khớp lệnh. Việc một lệnh chờ có khớp hay không là
        # thông tin tương lai, nên mô hình trông có lãi (+0,087R) trong khi đếm đúng như lúc chạy thật thì không (−0,017R).
        t = pd.Timestamp('2026-06-01 10:00', tz='UTC')
        da_khop = pd.DataFrame({'t': [t + pd.Timedelta(minutes=30)], 'ma': ['fib'], 'huong': ['MUA']})
        moi = pd.DataFrame({'t': [t, t + pd.Timedelta(minutes=10), t + pd.Timedelta(minutes=30), t + pd.Timedelta(minutes=45)],
                            'ma': ['ict', 'pha_vo', 'fib', 'elliott'], 'huong': ['MUA', 'BAN', 'MUA', 'MUA']})        # ict và pha_vo có tín hiệu nhưng không khớp
        r = mo_hinh.them_dong_thuan(da_khop, nguon=moi)
        self.assertEqual((r['dt_cung'].tolist(), r['dt_nguoc'].tolist()), ([1], [1]))                  # thấy ict (cùng) và pha_vo (ngược); không thấy elliott đến sau
        self.assertEqual(mo_hinh.them_dong_thuan(da_khop)['dt_cung'].tolist(), [0])
        src = Path(mo_hinh.__file__).read_text(encoding='utf-8')
        self.assertIn('nguon=pd.concat(moi', src)                                                      # du_lieu() phải đếm trên mọi tín hiệu

    def test_trang_va_ma_nguon(self):
        self.assertEqual(len(mo_hinh.cot()), len(mo_hinh.DAC) + len(PP.DS))
        html = bieu_do.trang_bieu_do('Thử')
        for must in ('Điểm mô hình', 'thử nghiệm', 'mới quanh hòa vốn', 'chưa phải tín hiệu', 'Tỷ lệ thắng theo mức chốt', 'Cần để hòa vốn', 'vẫn lỗ khi chấm riêng từng tín hiệu', 'không phải lý do để tin điểm vào hơn'):
            self.assertIn(must, html)
        self.assertNotIn('Đồng thuận nhiều: thận trọng', html)                                          # nhãn này dựa trên số đo bị rò rỉ, đã bỏ
        src = Path(mo_hinh.__file__).read_text(encoding='utf-8')
        for banned in ('order_send', 'order_check', 'TRADE_ACTION', 'symbol_select', 'positions_get', 'MetaTrader5'):
            self.assertNotIn(banned, src)


if __name__ == '__main__':
    unittest.main()


def _du_lieu_gia(n=3000, loi=0.0, seed=0):
    """Bảng tín hiệu giả: mỗi 2 giờ một tín hiệu; r2 = +2 hoặc −1, xác suất thắng tăng theo cột 'rsi' với độ mạnh `loi` (0 là không có quan hệ)."""
    rng = np.random.default_rng(seed)
    d = pd.DataFrame(rng.normal(0, 1, (n, len(mo_hinh.cot()))), columns=mo_hinh.cot())
    d.insert(0, 't', pd.date_range('2015-01-01', periods=n, freq='2h', tz='UTC'))
    p = 1 / (1 + np.exp(-(np.log(0.5) + loi * d['rsi'])))
    d['r2'] = np.where(rng.random(n) < p, 2.0, -1.0)
    return d


class KiemCheoTest(unittest.TestCase):
    def test_cuon_chieu_chi_hoc_qua_khu_va_khong_tach_tin_dong_thoi(self):
        d = _du_lieu_gia(n=900, loi=1.2)
        d.loc[149:151, 't'] = d.loc[150, 't']
        calls = []

        def hoc(dh):
            calls.append(dh.copy())
            return mo_hinh._hoc(dh)

        kq = mo_hinh.kiem_cuon_chieu(d, k=5, hoc_fn=hoc)
        self.assertTrue(kq['chi_hoc_qua_khu'])
        seen = set()
        for dh, g in zip(calls, kq['gap']):
            a, b = pd.Timestamp(g['tu_luc']), pd.Timestamp(g['den_luc'])
            self.assertLess(dh['t'].max(), a - mo_hinh.H_NHAN)
            ids = set(d.index[(d['t'] >= a) & (d['t'] <= b)])
            self.assertGreater(g['n'], 0)
            self.assertEqual(g['n'], len(ids))
            self.assertFalse(ids & seen)
            seen |= ids
        self.assertEqual(len(calls), 5)

    def test_cuon_chieu_tuong_lai_khong_doi_ket_qua_qua_khu(self):
        d = _du_lieu_gia(n=1800, loi=1.2)
        a = mo_hinh.kiem_cuon_chieu(d, k=5)
        d.loc[1500:, 'rsi'] = 999
        d.loc[1500:, 'r2'] = -10
        b = mo_hinh.kiem_cuon_chieu(d, k=5)
        self.assertEqual(a['gap'][:-1], b['gap'][:-1])
        self.assertIsNone(mo_hinh.kiem_cuon_chieu(d.iloc[:0])['auc_tb'])

    def test_auc_dung_dinh_nghia(self):
        rng = np.random.default_rng(1)
        y, p = rng.random(300) < 0.4, rng.normal(0, 1, 300)
        p[::7] = 0.0                                                                          # có điểm trùng: tính nửa
        dung = np.mean([(a > b) + 0.5 * (a == b) for a in p[y] for b in p[~y]])
        self.assertAlmostEqual(mo_hinh.auc(y, p), dung, places=12)
        self.assertIsNone(mo_hinh.auc(np.ones(5, bool), np.arange(5.0)))

    def test_loai_chong_lan_va_vung_cam(self):
        d = _du_lieu_gia()
        kq, thuong = mo_hinh.kiem_cheo(d, k=6, loc=True), mo_hinh.kiem_cheo(d, k=6, loc=False)
        t = pd.DatetimeIndex(d['t'])
        cam = max(mo_hinh.H_NHAN, (t[-1] - t[0]) * mo_hinh.CAM_TY_LE)
        for j, idx in enumerate(np.array_split(np.arange(len(d)), 6)):
            a, b = t[idx[0]], t[idx[-1]]
            truoc = int(((t >= a - mo_hinh.H_NHAN) & (t < a)).sum())                              # kết quả chồng lên đầu quãng kiểm
            sau = int(((t > b) & (t <= b + cam)).sum())                                           # vùng cấm sau quãng kiểm
            g = kq['gap'][j]
            self.assertEqual((g['n'], g['n_bo'], g['n_hoc']), (len(idx), truoc + sau, len(d) - len(idx) - truoc - sau), j)
            self.assertEqual((thuong['gap'][j]['n_bo'], thuong['gap'][j]['n_hoc']), (0, len(d) - len(idx)))
        self.assertEqual(kq['gap'][0]['n_bo'], int(((t > t[499]) & (t <= t[499] + cam)).sum()))   # phần đầu: chỉ có vùng cấm phía sau
        self.assertEqual(kq['gap'][-1]['n_bo'], int(((t >= t[2500] - mo_hinh.H_NHAN) & (t < t[2500])).sum()))
        self.assertEqual(kq['ngay_chong'], 4)

    def test_phan_biet_co_va_khong_co_quan_he(self):
        co = mo_hinh.kiem_cheo(_du_lieu_gia(loi=1.2, seed=2))
        khong = mo_hinh.kiem_cheo(_du_lieu_gia(loi=0.0, seed=3))
        self.assertGreater(co['auc_tb'], 0.65)
        self.assertGreater(co['top_r_tb'], co['r_tb'] + 0.3)
        self.assertEqual(co['so_phan_hon'], 6)
        self.assertLess(abs(khong['auc_tb'] - 0.5), 0.04)
