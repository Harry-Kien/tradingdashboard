# -*- coding: utf-8 -*-
"""Đối chiếu vị thế đang mở (so_cong_khai.vi_the): MT5 là nguồn chính; nhật ký EA thiếu dòng đóng không được hiện như lệnh đang mở;
nhiều tài khoản không lấy nhầm vị thế của nhau. Dùng MT5 giả, không nối MT5 thật."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace as N

from so_cong_khai import gia, tai_khoan, trang, vi_the

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
MO = NOW - timedelta(hours=12)                                                     # 00:00 UTC 26/11: EA M mở BÁN 0,05 ở 3445,62
T = int(NOW.timestamp())


def nhat_ky(thu_muc: Path, ten: str, dong: list[str]) -> str:
    p = thu_muc / f'{ten}.csv'
    p.write_text('time_server,event,equity,detail\n' + '\n'.join(dong) + '\n', encoding='utf-8')
    return str(p)


def dong_vao(t: datetime, ben: str, lot: float, gia_: float, sl: float, tp: float = 0) -> str:
    return f'{t:%Y.%m.%d %H:%M:%S},{ben},1000,lots={lot} price={gia_} sl={sl} tp={tp}'


class MT5Gia:
    ACCOUNT_TRADE_MODE_DEMO = 0

    def __init__(self, login=12345678, mo=(), deals=()):
        self.login, self.mo, self.deals, self.goi = login, list(mo), list(deals), []

    def __getattr__(self, ten):
        raise AssertionError(f'mô-đun gọi hàm MT5 không được phép: {ten}')

    def account_info(self):
        self.goi.append('account_info')
        return N(login=self.login, trade_mode=0)

    def positions_get(self):
        self.goi.append('positions_get')
        return tuple(self.mo)

    def history_deals_get(self, a, b):
        self.goi.append('history_deals_get')
        return tuple(self.deals)


def vt(ve, ben, lot, gia_, t, magic, sl=0.0, tp=0.0, ma='XAUUSDp'):
    return N(ticket=ve, symbol=ma, type=0 if ben == 'BUY' else 1, volume=lot, price_open=gia_, sl=sl, tp=tp, time=int(t.timestamp()), magic=magic)


def deal(vt_id, loai, vao_ra, lot, gia_, t, magic, lai=0.0, ma='XAUUSDp'):
    return N(position_id=vt_id, symbol=ma, type=loai, entry=vao_ra, volume=lot, price=gia_, time=int(t.timestamp()), magic=magic,
             profit=lai, commission=0.0, swap=0.0, fee=0.0, comment='')


class ViThe(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.d = Path(self.tam.name)
        self.that = tai_khoan._mt5
        self.mt5 = None
        tai_khoan._mt5 = lambda g: self.mt5

    def tearDown(self):
        tai_khoan._mt5 = self.that
        self.tam.cleanup()

    def cfg(self, tai_khoan_=None):
        ea_m = nhat_ky(self.d, 'ea_m', ['2026.11.25 23:00:00,init,1000,version=v3', dong_vao(MO, 'sell', 0.05, 3445.62, 3520.53)])
        return {'gia': {}, 'mt5_xem': {'magic': {'777': 'EA M', '888': 'EA E'}},
                'tai_khoan': tai_khoan_ or [{'ten': 'Demo 100', 'ea': [{'ten': 'EA M', 'tep': ea_m, 'lech_gio_utc': 0}]}]}

    def test_mt5_xac_nhan_dong_khi_nhat_ky_thieu_dong(self):
        """Lỗi rà soát 27/11: nhật ký EA M còn lệnh BÁN 0,05 nhưng MT5 đã đóng lúc 00:54 ở 3520,80."""
        dong = MO + timedelta(minutes=54)
        self.mt5 = MT5Gia(deals=[deal(91, 1, 0, 0.05, 3445.62, MO + timedelta(seconds=2), 777), deal(91, 0, 1, 0.05, 3520.80, dong, 777, lai=-375.9)])
        r = vi_the.tong_hop(self.cfg(), NOW)
        self.assertEqual(r['ds'], [])                                                   # không còn ở danh sách lệnh đang mở
        self.assertEqual(len(r['da_dong_theo_mt5']), 1)
        x = r['da_dong_theo_mt5'][0]
        self.assertEqual((x['ten'], x['gia_dong'], x['ve'], x['dong']), ('EA M', 3520.8, 91, dong.isoformat()))
        self.assertEqual(r['mt5']['tai_khoan'], 'Demo 100')
        self.assertEqual(set(self.mt5.goi), {'account_info', 'positions_get', 'history_deals_get'})   # chỉ hàm đọc

    def test_mt5_con_mo_thi_dung_so_lieu_mt5(self):
        self.mt5 = MT5Gia(mo=[vt(91, 'SELL', 0.05, 3445.60, MO + timedelta(seconds=3), 777, sl=3500.0)])
        r = vi_the.tong_hop(self.cfg(), NOW)
        self.assertEqual(len(r['ds']), 1)
        o = r['ds'][0]
        self.assertEqual((o['nguon'], o['xac_minh'], o['ve'], o['sl'], o['so_tk']), ('mt5', True, 91, 3500.0, '•••678'))   # SL hiện tại của MT5, không phải của nhật ký

    def test_chua_noi_mt5_thi_ghi_chua_xac_minh(self):
        self.mt5 = None
        r = vi_the.tong_hop(self.cfg(), NOW)
        o = r['ds'][0]
        self.assertEqual((o['nguon'], o['xac_minh']), ('nhat_ky_ea', False))
        self.assertIn('chưa nối được MT5', o['ly_do'])
        self.assertTrue(o['luc_nguon'].startswith('2026-11-26T00:00'))                   # giờ dòng cuối của nhật ký

    def test_dung_tai_khoan_nhung_mt5_khong_co_gi_khop(self):
        self.mt5 = MT5Gia(deals=[deal(5, 0, 0, 0.01, 3400.0, MO - timedelta(days=2), 777), deal(5, 1, 1, 0.01, 3410.0, MO - timedelta(days=2, hours=-1), 777)])
        o = vi_the.tong_hop(self.cfg(), NOW)['ds'][0]
        self.assertEqual((o['nguon'], o['xac_minh']), ('nhat_ky_ea', False))
        self.assertIn('không có vị thế mở hay đã đóng khớp', o['ly_do'])

    def test_nhieu_tai_khoan_khong_lay_nham(self):
        """Tài khoản B (EA E) đang nối và có vị thế giống hệt lệnh nhật ký của tài khoản A (EA M): không được ghép chéo."""
        ea_e = nhat_ky(self.d, 'ea_e', ['2026.11.25 23:00:00,init,1000,version=v1'])
        cfg = self.cfg()
        cfg['tai_khoan'].append({'ten': 'Demo B', 'ea': [{'ten': 'EA E', 'tep': ea_e, 'lech_gio_utc': 0}]})
        self.mt5 = MT5Gia(login=55555220, mo=[vt(300, 'SELL', 0.05, 3445.62, MO, 888)])
        r = vi_the.tong_hop(cfg, NOW)
        m = [o for o in r['ds'] if o['ten'] == 'EA M']
        e = [o for o in r['ds'] if o['ten'] == 'EA E']
        self.assertEqual((m[0]['nguon'], m[0]['xac_minh']), ('nhat_ky_ea', False))
        self.assertIn('tài khoản khác', m[0]['ly_do'])
        self.assertEqual((e[0]['nguon'], e[0]['tai_khoan'], e[0]['ve']), ('mt5', 'Demo B', 300))
        self.assertEqual(r['mt5']['tai_khoan'], 'Demo B')

    def test_so_cuoi_khai_ro(self):
        cfg = self.cfg()
        cfg['tai_khoan'][0]['so_cuoi'] = '999'                                             # khai số khác số đang nối
        self.mt5 = MT5Gia(mo=[vt(91, 'SELL', 0.05, 3445.60, MO, 777)])
        o = [x for x in vi_the.tong_hop(cfg, NOW)['ds'] if x['ten'] == 'EA M' and x['nguon'] == 'nhat_ky_ea']
        self.assertEqual(len(o), 1)                                                       # không xác minh bằng tài khoản không đúng số
        cfg['tai_khoan'][0]['so_cuoi'] = '678'
        r = vi_the.tong_hop(cfg, NOW)
        self.assertEqual([(x['nguon'], x['ve']) for x in r['ds']], [('mt5', 91)])

    def test_mot_so_ve_chi_ghep_mot_lan(self):
        ea_m2 = nhat_ky(self.d, 'ea_m2', [dong_vao(MO, 'sell', 0.05, 3445.62, 3520.53)])
        cfg = self.cfg()
        cfg['tai_khoan'][0]['ea'].append({'ten': 'EA M', 'tep': ea_m2, 'lech_gio_utc': 0})
        self.mt5 = MT5Gia(mo=[vt(91, 'SELL', 0.05, 3445.62, MO, 777)])
        r = vi_the.tong_hop(cfg, NOW)
        self.assertEqual(sorted((o['nguon'], o.get('ve')) for o in r['ds']), [('mt5', 91), ('nhat_ky_ea', None)])

    def test_vi_the_ma_khac_va_trang(self):
        self.mt5 = MT5Gia(mo=[vt(91, 'SELL', 0.05, 3445.60, MO, 777), vt(92, 'BUY', 0.1, 158.0, MO, 0, ma='USDJPYp')])
        cfg = self.cfg()
        gia._lenh_nho.update(luc=0.0, key=None, ds=[])
        vi_the._nho.update(luc=0.0, key=None, kq=None)
        ds = gia.lenh_dang_mo(cfg)
        self.assertEqual(sorted(o['ma'] for o in ds), ['USDJPYp', 'XAUUSDp'])          # Tổng quan thấy mọi vị thế MT5
        self.assertEqual([o['ma'] for o in ds if not o.get('ma') or 'XAU' in o['ma'].upper()], ['XAUUSDp'])   # biểu đồ vàng lọc đúng mã
        h = trang._khoi_hien_tai({'lenh': [ds[0], {**ds[0], 'xac_minh': False, 'nguon': 'nhat_ky_ea', 'ly_do': 'chưa nối được MT5 để xác minh',
                                                   'luc_nguon': MO.isoformat(), 'so_tk': None}]})
        self.assertIn('theo nhật ký, chưa xác minh', h)
        self.assertIn('chưa nối được MT5 để xác minh', h)
        self.assertIn('MT5 •••678', h)

    def test_loi_nhat_ky_khong_lam_hong(self):
        cfg = self.cfg([{'ten': 'Hỏng', 'ea': [{'ten': 'EA X', 'tep': str(self.d / 'khong-co.csv')}]}])
        self.mt5 = MT5Gia()
        self.assertEqual(vi_the.tong_hop(cfg, NOW)['ds'], [])


if __name__ == '__main__':
    unittest.main()
