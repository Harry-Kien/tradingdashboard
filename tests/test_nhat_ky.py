"""Bài kiểm cho nhật ký điểm vào: chỉ ghi phương án còn hiệu lực, không ghi trùng, mức giá chốt lúc ghi, và phần theo dõi xử đúng từng
trường hợp (lệnh chờ khớp rồi thắng, thua, không khớp, bị hủy, hết giờ; nến chạm cả hai thì tính dừng lỗ)."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import bieu_do, nhat_ky, nhat_ky_trang, trang  # noqa: E402

T0 = datetime(2026, 6, 1, 10, 2, tzinfo=timezone.utc)


def _pa(**kw):
    p = {'ma': 'ict', 'ten': 'ICT thử', 'nhom': 'pp', 'co': True, 'hieu_luc': True, 'huong': 'MUA', 'kieu': 'lệnh chờ', 'vao': 100.0, 'sl': 98.0,
         'tp': [102.0, 104.0], 'rr': [1.0, 2.0], 'nen': '2026-06-01T10:00:00+00:00', 'con_phut': 240, 'ly_do': 'thử'}
    p.update(kw)
    return p


def _m5(gia, bat_dau=None):
    """Nến 5 phút từ `bat_dau` (mặc định 10:05); `gia`: danh sách (đỉnh, đáy, đóng)."""
    idx = pd.date_range(bat_dau or datetime(2026, 6, 1, 10, 5, tzinfo=timezone.utc), periods=len(gia), freq='5min')
    return pd.DataFrame([(c, h, l, c) for h, l, c in gia], columns=['open', 'high', 'low', 'close'], index=idx)


class NhatKyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = {'nhat_ky': {'bat': True, 'tep': str(Path(self.tmp.name) / 'nk.json')}, 'gia': {'ma_vang': 'XAUUSDp'}}

    def tearDown(self):
        self.tmp.cleanup()

    def _ghi(self, *pas, now=T0, **pt):
        return nhat_ky.ghi(self.cfg, {'phuong_an': [], 'phuong_phap': list(pas), 'bid': 101.0, 'boi_canh': {'phien': 'Âu', 'bien_do': 'vừa'}, **pt}, now)

    # ---- nhật ký là bằng chứng chạy thật duy nhất của hệ thống: không được mất dòng nào -------------------------------------
    def test_tep_hong_duoc_giu_lai_va_lay_ban_sao_luu(self):
        p = nhat_ky.tep(self.cfg)
        self._ghi(_pa())
        tot = p.read_text(encoding='utf-8')
        sl = p.parent / 'sao-luu'
        sl.mkdir()
        (sl / f'{p.stem}-20260531.json').write_text(tot, encoding='utf-8')
        p.write_text('{"ghi dở', encoding='utf-8')                                                      # mất điện giữa chừng, đĩa lỗi…
        ds = nhat_ky._doc(p)
        self.assertEqual([x['id'] for x in ds], [1])                                                    # lấy lại từ bản sao lưu gần nhất
        hong = list(p.parent.glob(f'{p.stem}.hong-*.json'))
        self.assertEqual([h.read_text(encoding='utf-8') for h in hong], ['{"ghi dở'])                   # bản hỏng được giữ lại để xem
        nhat_ky._doc(p)
        self.assertEqual(len(list(p.parent.glob(f'{p.stem}.hong-*.json'))), 1)                          # đọc lại nhiều lần không sinh thêm bản

    def test_khong_doc_duoc_tep_thi_khong_ghi_de(self):
        p = nhat_ky.tep(self.cfg)
        self._ghi(_pa())
        truoc = p.read_text(encoding='utf-8')
        that = Path.read_text

        def khoa(self_, *a, **k):                                                                       # tệp đang bị chương trình khác khóa
            if self_ == p:
                raise PermissionError('đang bị khóa')
            return that(self_, *a, **k)
        Path.read_text = khoa
        try:
            with self.assertRaises(nhat_ky.NhatKyKhongDocDuoc):
                self._ghi(_pa(ma='fib', nen='2026-06-01T10:15:00+00:00'), now=T0 + timedelta(minutes=15))
        finally:
            Path.read_text = that
        self.assertEqual(p.read_text(encoding='utf-8'), truoc)                                          # trước đây: coi như nhật ký rỗng rồi ghi đè, mất hết

    def test_sao_luu_mot_ban_moi_ngay(self):
        p = nhat_ky.tep(self.cfg)
        self._ghi(_pa())                                                                                # lần ghi đầu: chưa có tệp nên chưa có gì để sao lưu
        sl = p.parent / 'sao-luu'
        self.assertEqual(list(sl.glob('*.json')) if sl.exists() else [], [])
        truoc = p.read_text(encoding='utf-8')
        self._ghi(_pa(ma='fib'), now=T0 + timedelta(minutes=1))
        self._ghi(_pa(ma='pha_vo'), now=T0 + timedelta(minutes=2))
        ban = list(sl.glob(f'{p.stem}-*.json'))
        self.assertEqual(len(ban), 1)                                                                   # một bản mỗi ngày, là tệp TRƯỚC lần ghi đầu của ngày
        self.assertEqual(ban[0].read_text(encoding='utf-8'), truoc)

    def test_dong_cu_duoc_luu_tru_khong_bi_xoa(self):
        p, that = nhat_ky.tep(self.cfg), nhat_ky.TOI_DA
        nhat_ky.TOI_DA = 3
        try:
            nhat_ky._luu(p, [{'id': i, 'tt': 'thua'} for i in range(1, 6)])
        finally:
            nhat_ky.TOI_DA = that
        self.assertEqual([x['id'] for x in json.loads(p.read_text(encoding='utf-8'))], [3, 4, 5])
        luu = [json.loads(d) for d in (p.parent / f'{p.stem}-luu-tru.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual([x['id'] for x in luu], [1, 2])                                                # trước đây hai dòng này bị bỏ hẳn
        self.assertGreaterEqual(that, 10000)

    def test_nhom_diem_mo_hinh_chi_tinh_ban_mo_hinh_hien_tai(self):
        from so_cong_khai import mo_hinh
        moi = self._ghi(_pa(mo_hinh={'hang': 95}))
        self.assertEqual(moi[0]['mh_ban'], mo_hinh.PHIEN_BAN)
        p = nhat_ky.tep(self.cfg)
        ds = json.loads(p.read_text(encoding='utf-8'))
        ds.append({**ds[0], 'id': 2, 'ma': 'fib', 'mo_hinh': 99, 'mh_ban': mo_hinh.PHIEN_BAN - 1, 'tt': 'thang', 'r': 2.0})      # điểm do bản mô hình cũ (còn rò rỉ) chấm
        p.write_text(json.dumps(ds), encoding='utf-8')
        r = nhat_ky.xem(self.cfg, T0 + timedelta(minutes=1), nen=lambda sym, tu: (_m5([(101, 100.5, 100.8)]), 0.0))
        self.assertEqual(r['theo_mo_hinh']['cao']['n'], 1)                                              # chỉ dòng của bản hiện tại

    def test_chi_ghi_phuong_an_con_hieu_luc_va_khong_ghi_trung(self):
        self.assertEqual(self._ghi(_pa(hieu_luc=False), _pa(co=False)), [])
        moi = self._ghi(_pa())
        self.assertEqual([(x['id'], x['sym'], x['tt'], x['vao'], x['phien']) for x in moi], [(1, 'XAUUSDp', 'cho_khop', 100.0, 'Âu')])
        self.assertEqual(moi[0]['het_han'], (T0 + timedelta(minutes=240)).isoformat())
        self.assertEqual(self._ghi(_pa(vao=100.5), now=T0 + timedelta(minutes=5)), [])        # điểm vào trước còn sống: không ghi thêm
        self.assertEqual(len(self._ghi(_pa(huong='BAN', sl=102.0, tp=[98.0, 96.0]))), 1)      # chiều khác là dòng khác
        self.assertEqual(len(self._ghi(_pa(), ma='BTCUSDTp')), 1)                             # mã khác là dòng khác
        tat = dict(self.cfg, nhat_ky={'bat': False, 'tep': self.cfg['nhat_ky']['tep']})
        self.assertEqual(nhat_ky.ghi(tat, {'phuong_phap': [_pa(ma='fib')]}, T0), [])          # tắt trong cấu hình thì không ghi

    def test_hai_phuong_an_cua_luat_bot_cung_mot_lenh_chi_ghi_mot_dong(self):
        """Lỗi ngày 24/11/2026: luật bot có hai phương án ('bot:nen', 'bot:xu_huong'); khi cả hai ra đúng một lệnh, nhật ký ghi hai dòng nên đếm đôi."""
        bot = dict(nhom='luat', nen=None, con_phut=None, huong='BAN', vao=3602.59, sl=3631.0, tp=[3589.0, 3518.0])
        moi = nhat_ky.ghi(self.cfg, {'phuong_an': [_pa(ma='bot:nen', **bot), _pa(ma='bot:xu_huong', **bot)], 'phuong_phap': [], 'bid': 3602.59}, T0)
        self.assertEqual([x['ma'] for x in moi], ['bot:nen'])
        sau = nhat_ky.ghi(self.cfg, {'phuong_an': [_pa(ma='bot:xu_huong', **bot)], 'phuong_phap': [], 'bid': 3602.59}, T0 + timedelta(minutes=1))
        self.assertEqual(sau, [])                                                     # lần quét sau cũng không ghi phương án kia
        khac = nhat_ky.ghi(self.cfg, {'phuong_an': [_pa(ma='bot:xu_huong', **dict(bot, vao=3590.0, sl=3620.0))], 'phuong_phap': [], 'bid': 3590.0},
                           T0 + timedelta(minutes=2))
        self.assertEqual([x['ma'] for x in khac], ['bot:xu_huong'])                   # lệnh khác thật (giá khác) thì vẫn ghi

    def test_dong_trung_cu_khong_bi_xoa_nhung_khong_tinh(self):
        p = nhat_ky.tep(self.cfg)
        goc = {'luc': T0.isoformat(), 'sym': 'XAUUSDp', 'ten': 'Luật bot tín hiệu', 'nhom': 'luat', 'huong': 'BAN', 'vao': 3602.59, 'sl': 3631.0, 'tp': [3589.0, 3518.0],
               'nen': None, 'tt': 'thang', 'r': 0.48}
        p.write_text(json.dumps([dict(goc, id=1, ma='bot:nen'), dict(goc, id=2, ma='bot:xu_huong'), dict(goc, id=3, ma='bot:xu_huong', vao=3590.0, tt='thua', r=-1.0)]),
                     encoding='utf-8')
        r = nhat_ky.xem(self.cfg, T0 + timedelta(hours=1), nen=lambda sym, tu: (_m5([(101, 100.5, 100.8)]), 0.0))
        self.assertEqual(sorted((x['id'], x.get('trung_voi')) for x in r['ds']), [(1, None), (2, 1), (3, None)])
        tom = {t['ma']: (t['n'], t['thang'], t['thua'], t['tong_r']) for t in r['tom']}
        self.assertEqual(tom, {'bot:nen': (1, 1, 0, 0.48), 'bot:xu_huong': (1, 0, 1, -1.0)})
        self.assertEqual(len(json.loads(p.read_text(encoding='utf-8'))), 3)           # không xóa dòng nào trong tệp
        self.assertIn('trung_voi', nhat_ky_trang.trang_nhat_ky('Harry') if hasattr(nhat_ky_trang, 'trang_nhat_ky') else nhat_ky_trang.JS)

    def test_tin_hieu_cua_cung_mot_nen_khong_ghi_lai_sau_khi_xong(self):
        self._ghi(_pa())
        kq = nhat_ky.xem(self.cfg, T0 + timedelta(hours=1), nen=lambda sym, tu: (_m5([(100.6, 99.9, 100.2), (100.3, 97.5, 97.8)]), 0.0))
        self.assertEqual(kq['ds'][0]['tt'], 'thua')
        self.assertEqual(self._ghi(_pa(), now=T0 + timedelta(hours=1)), [])                   # vẫn là nến tín hiệu cũ
        self.assertEqual(len(self._ghi(_pa(nen='2026-06-01T11:00:00+00:00'), now=T0 + timedelta(hours=1))), 1)

    def _mot(self, gia, sp=0.0, **kw):
        self._ghi(_pa(**kw))
        return nhat_ky.xem(self.cfg, T0 + timedelta(days=3), nen=lambda sym, tu: (_m5(gia), sp))['ds'][0]

    def test_lenh_cho_khop_roi_thang(self):
        x = self._mot([(101.0, 100.4, 100.8), (100.9, 99.8, 100.5), (102.5, 100.4, 102.2), (104.2, 102.0, 104.0)])
        self.assertEqual((x['tt'], x['r'], x['khop'][11:16], x['ra'][11:16], x['cham_tp1'][11:16]), ('thang', 2.0, '10:15', '10:25', '10:20'))

    def test_khop_va_thung_dung_lo_cung_nen_thi_thua(self):
        x = self._mot([(101.0, 100.4, 100.8), (100.5, 97.9, 98.2)])
        self.assertEqual((x['tt'], x['r']), ('thua', -1.0))

    def test_nen_cham_ca_hai_thi_tinh_dung_lo(self):
        x = self._mot([(100.2, 99.9, 100.0), (104.5, 97.8, 100.0)])
        self.assertEqual(x['tt'], 'thua')

    def test_khong_khop_va_chua_co_ket_qua(self):
        x = self._mot([(101.5, 100.6, 101.0)] * 60)                                           # 5 giờ giá đứng trên mức chờ
        self.assertEqual((x['tt'], x['r']), ('khong_khop', None))
        nhat_ky._luu(nhat_ky.tep(self.cfg), [])
        y = self._mot([(101.5, 100.6, 101.0)] * 10)                                           # mới 50 phút: vẫn chờ
        self.assertEqual(y['tt'], 'cho_khop')

    def test_lenh_ban_tinh_theo_ask(self):
        ban = dict(huong='BAN', sl=102.0, tp=[98.0, 96.0])
        x = self._mot([(100.1, 99.5, 99.8), (99.9, 96.1, 96.3)], sp=0.2, **ban)               # Ask thấp nhất 96,3: chưa tới 96
        self.assertEqual((x['tt'], x['cham_tp1'] is not None), ('dang_mo', True))
        nhat_ky._luu(nhat_ky.tep(self.cfg), [])
        y = self._mot([(100.1, 99.5, 99.8), (99.9, 95.7, 96.0)], sp=0.2, **ban)
        self.assertEqual((y['tt'], y['r']), ('thang', 2.0))

    def test_vao_theo_gia_thi_truong_va_het_gio(self):
        x = self._mot([(100.4, 99.8, 100.2)] * 300, con_phut=None, nen=None, ma='bot:nen', nhom='luat', tp=[101.0])
        self.assertEqual((x['tt'], x['r'], x['khop']), ('het_gio', 0.1, T0.isoformat()))
        tom = nhat_ky.xem(self.cfg, T0 + timedelta(days=3), nen=lambda s, t: (None, 0.0))['tom'][0]
        self.assertEqual((tom['n'], tom['khac'], tom['tong_r'], tom['song']), (1, 1, 0.1, 0))

    def test_gia_mo_nhay_qua_dung_lo_thi_lo_hon_1r(self):
        def nen(gia):                                                                         # (mở, đỉnh, đáy, đóng)
            idx = pd.date_range(datetime(2026, 6, 1, 10, 5, tzinfo=timezone.utc), periods=len(gia), freq='5min')
            return pd.DataFrame(gia, columns=['open', 'high', 'low', 'close'], index=idx)
        luat = dict(con_phut=None, nen=None, ma='bot:nen', nhom='luat', tp=[101.0])            # vào 100 theo giá thị trường, SL 98
        self._ghi(_pa(**luat))
        x = nhat_ky.xem(self.cfg, T0 + timedelta(days=3), nen=lambda s, t: (nen([(100.2, 100.4, 99.8, 100.2), (97.0, 97.2, 96.8, 97.0)]), 0.0))['ds'][0]
        self.assertEqual((x['tt'], x['r']), ('thua', -1.5))                                   # nến mở ở 97, dưới SL: thoát ở giá mở
        nhat_ky._luu(nhat_ky.tep(self.cfg), [])
        self._ghi(_pa(**luat))
        y = nhat_ky.xem(self.cfg, T0 + timedelta(days=3), nen=lambda s, t: (nen([(100.2, 100.4, 99.8, 100.2), (99.0, 99.1, 97.5, 97.6)]), 0.0))['ds'][0]
        self.assertEqual((y['tt'], y['r']), ('thua', -1.0))                                   # chạm SL trong lúc chạy: lỗ đúng 1R
        nhat_ky._luu(nhat_ky.tep(self.cfg), [])
        self._ghi(_pa(**luat))
        z = nhat_ky.xem(self.cfg, T0 + timedelta(days=3), nen=lambda s, t: (nen([(97.0, 97.2, 96.8, 97.0)]), 0.0))['ds'][0]
        self.assertEqual((z['tt'], z['r']), ('thua', -1.0))                                   # nến đầu tiên sau lúc ghi: không có nến trước để biết là nhảy giá

    def test_luat_trong_so_thang_o_tp1_va_tep_khong_bi_ghi_do(self):
        x = self._mot([(100.4, 99.8, 100.2), (101.2, 100.1, 101.0)], con_phut=None, nen=None, ma='bot:nen', nhom='luat', tp=[101.0, 102.0, 103.0], rr=[0.5, 1.0, 1.5])
        self.assertEqual((x['tt'], x['r']), ('thang', 0.5))
        self.assertEqual(json.loads(Path(self.cfg['nhat_ky']['tep']).read_text(encoding='utf-8'))[0]['tt'], 'thang')
        self.assertFalse(Path(self.cfg['nhat_ky']['tep']).with_suffix('.tmp').exists())

    def test_thong_ke_theo_diem_mo_hinh(self):
        self._ghi(_pa(mo_hinh={'p': 0.4, 'hang': 95}))
        self._ghi(_pa(ma='fib', mo_hinh={'p': 0.3, 'hang': 40}), _pa(ma='pha_vo'))
        kq = nhat_ky.xem(self.cfg, T0 + timedelta(hours=1), nen=lambda sym, tu: (_m5([(100.6, 99.9, 100.2), (100.3, 97.5, 97.8)]), 0.0))
        self.assertEqual([x['mo_hinh'] for x in kq['ds']][::-1], [95, 40, None])               # điểm được chốt lúc ghi; không có điểm thì để trống
        self.assertEqual((kq['theo_mo_hinh']['cao']['n'], kq['theo_mo_hinh']['cao']['thua'], kq['theo_mo_hinh']['thap']['n']), (1, 1, 1))

    def _tep(self):
        return json.loads(Path(self.cfg['nhat_ky']['tep']).read_text(encoding='utf-8'))

    def test_tin_hieu_moi_thay_lenh_cho_cu_nhu_phep_chay_lai(self):
        n2, n3 = '2026-06-01T10:30:00+00:00', '2026-06-01T11:00:00+00:00'
        self._ghi(_pa())                                                                      # A: chờ mua 100, tín hiệu của nến 10:00
        ban = dict(huong='BAN', vao=101.5, sl=103.5, tp=[99.5, 97.5])
        moi = self._ghi(_pa(nen=n2, **ban), now=T0 + timedelta(minutes=30))                   # B: tín hiệu mới của cùng phương pháp, A chưa khớp
        self.assertEqual([(x['id'], x['tt']) for x in moi], [(2, 'cho_khop')])
        a = self._tep()[0]
        self.assertEqual((a['tt'], a['thay_boi'], a['ra'], a['r']), ('thay', 2, (T0 + timedelta(minutes=30)).isoformat(), None))
        # B khớp (giá lên 101,6) và còn mở; A dù giá có về 100 cũng không sống lại
        kq = nhat_ky.xem(self.cfg, T0 + timedelta(minutes=50), nen=lambda s, t: (_m5([(101.6, 101.0, 101.2), (101.3, 99.8, 100.0)], datetime(2026, 6, 1, 10, 35, tzinfo=timezone.utc)), 0.0))
        self.assertEqual([(x['id'], x['tt']) for x in kq['ds']], [(2, 'dang_mo'), (1, 'thay')])
        self.assertEqual([(t['n'], t['song'], t['khac']) for t in kq['tom']], [(2, 1, 1)])
        # tín hiệu thứ ba đến lúc B còn mở: không ghi, kể cả khi khác chiều với B (mỗi lúc một lệnh, như phép chạy lại)
        self.assertEqual(self._ghi(_pa(nen=n3), now=T0 + timedelta(minutes=60)), [])
        self.assertEqual(self._ghi(_pa(nen=n3, **ban), now=T0 + timedelta(minutes=60)), [])
        self.assertEqual(len(self._tep()), 2)

    def test_luat_trong_so_van_ghi_rieng_tung_chieu(self):
        luat = dict(con_phut=None, nen=None, ma='bot:nen', nhom='luat', tp=[101.0])
        self._ghi(_pa(**luat))
        moi = self._ghi(_pa(**dict(luat, huong='BAN', sl=102.0, tp=[99.0])), now=T0 + timedelta(minutes=40))
        self.assertEqual(len(moi), 1)                                                         # luật của chủ dự án: giữ cách ghi cũ
        self.assertEqual([x['tt'] for x in self._tep()], ['dang_mo', 'dang_mo'])

    def test_vong_ghi_cap_nhat_dong_con_song_truoc_khi_ghi(self):
        from unittest import mock
        goi = []
        with mock.patch.object(nhat_ky, 'xem', side_effect=lambda cfg, *a, **k: goi.append('xem') or {'loi': []}), \
                mock.patch.object(nhat_ky, 'ghi', side_effect=lambda cfg, pt, *a, **k: goi.append('ghi') or []), \
                mock.patch('so_cong_khai.phan_tich.phan_tich', return_value={}):
            nhat_ky.VongGhi(lambda: self.cfg).mot_lan()
        self.assertEqual(goi, ['xem', 'ghi'])                                                 # không ai mở trang thì dòng còn sống vẫn phải được chấm
        with mock.patch.object(nhat_ky, 'xem', side_effect=RuntimeError('mất MT5')), \
                mock.patch.object(nhat_ky, 'ghi', side_effect=lambda cfg, pt, *a, **k: goi.append('ghi') or []), \
                mock.patch('so_cong_khai.phan_tich.phan_tich', return_value={}):
            v = nhat_ky.VongGhi(lambda: self.cfg)
            v.mot_lan()
        self.assertEqual(goi[-1], 'ghi')                                                      # chấm hỏng thì vẫn ghi điểm vào mới
        self.assertIn('mất MT5', v.tt['loi'])

    def test_trang_va_ma_nguon(self):
        html = bieu_do.trang_bieu_do('Thử')
        for must in ('id="nk"', '/api/nhat-ky', 'Nhật ký điểm vào', 'href="/nhat-ky"', "get('nk')"):
            self.assertIn(must, html)
        rieng = nhat_ky_trang.trang_nhat_ky('Thử')
        for must in ('/api/nhat-ky', 'Mức giá chốt lúc ghi và không sửa lại', 'không phải lệnh thật', 'Xem trên biểu đồ', 'Theo phương pháp', 'aria-current="page">Nhật ký'):
            self.assertIn(must, rieng)
        self.assertIn('href="/nhat-ky"', trang.thanh_dau('Thử', 'tong'))                 # mọi trang đều có lối sang Nhật ký
        src = Path(nhat_ky.__file__).read_text(encoding='utf-8')
        for banned in ('order_send', 'order_check', 'TRADE_ACTION', 'symbol_select', 'positions_get'):
            self.assertNotIn(banned, src)


if __name__ == '__main__':
    unittest.main()
