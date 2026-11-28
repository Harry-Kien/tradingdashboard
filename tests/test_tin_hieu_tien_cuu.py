"""Tiến cứu: ghi lần đầu, chấm bằng đúng phía quote và bảo toàn sổ qua SQLite."""
import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from http_owner import owner_urlopen
from so_cong_khai import canh_bao, sao_luu, tin_hieu_ngan as T, tin_hieu_tien_cuu as S, web


NEN = datetime(2026, 11, 27, 10, tzinfo=timezone.utc)
NOW = NEN + timedelta(seconds=5)


def _goi(huong='MUA', may_chu='A', tf='M5', tien='USD'):
    mua = huong == 'MUA'
    vao = 100.10 if mua else 100.00
    return {'nguon': 'mt5', 'may_chu': may_chu, 'ma': 'XAUUSDp', 'phien_ban': T.PHIEN_BAN, 'luc': NOW.isoformat(),
            'tick_ms': S._ms(NOW), 'bid': 100.00, 'ask': 100.10, 'buoc_gia': .01, 'gia_tick': 1, 'tien_tk': tien,
            'lich_tin': True,
            'ds': [{'tf': tf, 'loai': 'pha_vo', 'huong': huong, 'trang_thai': 'dat', 'vao': vao,
                    'sl': vao - 1 if mua else vao + 1, 'tp': vao + 1.5 if mua else vao - 1.5,
                    'dong': NEN.isoformat(), 'het': (NEN + timedelta(seconds=120)).isoformat()}]}


class TienCuuTest(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        self.out = self.root / 'out'

    def rows(self):
        with closing(S._db(self.out)) as db:
            return [dict(r) for r in db.execute('SELECT * FROM tin_hieu ORDER BY id')]

    def test_ghi_mot_lan_va_co_lap_broker_khung(self):
        p = _goi()
        with ThreadPoolExecutor(max_workers=6) as ex:
            ds = list(ex.map(lambda _: S.ghi(self.out, p, 7, NOW), range(6)))
        self.assertEqual(sum(ds), 1)
        p['ds'][0]['tp'] = 103.5
        self.assertEqual(S.ghi(self.out, p, 0, NOW), 0)
        self.assertEqual(S.ghi(self.out, _goi(tf='M30'), 0, NOW), 1)
        self.assertEqual(S.ghi(self.out, _goi(may_chu='B'), 0, NOW), 1)
        self.assertEqual([r['tp'] for r in self.rows()], [101.6, 101.6, 101.6])
        self.assertEqual(len(S.tong_hop(self.out, 'A', 'XAUUSDp')['ds']), 2)
        self.assertEqual(len(S.tong_hop(self.out, 'B', 'XAUUSDp')['ds']), 1)

    def test_bo_mau_cu_khong_ghi_hoi_cuu(self):
        p = _goi()
        self.assertEqual(S.ghi(self.out, p, 0, NOW + timedelta(minutes=3)), 0)
        p['tick_ms'] -= 10_000
        self.assertEqual(S.ghi(self.out, p, 0, NOW), 0)
        self.assertFalse(S.tep(self.out).exists())

    def test_stop_ban_dung_ask_va_khong_tru_spread_lan_hai(self):
        self.assertEqual(S.ghi(self.out, _goi('BÁN'), 7, NOW), 1)
        moc = S._ms(NOW)
        # Tick chỉ thấy trước lúc ghi và nến có Bid vẫn dưới SL nhưng Ask đã vượt.
        ticks = [(moc - 1, 102.00, 102.20), (moc + 4000, 100.97, 101.18)]
        s = self.rows()[0]
        moc_ra, tt, _, ra, r = S.cham_mot(s, ticks, moc + 5000)
        self.assertEqual((moc_ra, tt, ra), (moc + 4000, 'sl', 101.18))
        self.assertAlmostEqual(r, -1.26)  # lỗ 1,18 + hoa hồng 0,07 + trượt 0,01

    def test_gap_khong_lay_tp_sau_do_va_het_gio_cham_theo_quote(self):
        self.assertEqual(S.ghi(self.out, _goi(), 0, NOW), 1)
        s = self.rows()[0]
        n = s['moc_ms'] + S.KHOANG_TRONG_MS + 1
        self.assertEqual(S.cham_mot(s, [(n, 105, 105.12)], n)[1], 'thieu_tick')
        s['moc_ms'] = s['han_ms'] - 1000
        x = S.cham_mot(s, [(s['han_ms'] + 10, 100.40, 100.50)], s['han_ms'] + 100)
        self.assertEqual(x[1], 'het_gio')
        self.assertAlmostEqual(x[-1], .29)

    def test_ket_noi_loi_giu_dang_cho_va_tiep_tu_moc_cu(self):
        S.ghi(self.out, _goi(), 0, NOW)
        S.ghi(self.out, _goi(may_chu='B'), 0, NOW)
        t0 = S._ms(NOW)
        with patch.object(S, '_doc_tick', return_value=None):
            self.assertEqual(S.cap_nhat(self.out, object(), 'A', NOW + timedelta(seconds=20)), 0)
        with patch.object(S, '_doc_tick', return_value=[(t0 + 1000, 100.20, 100.25)]) as doc:
            self.assertEqual(S.cap_nhat(self.out, object(), 'A', NOW + timedelta(seconds=20)), 1)
            self.assertEqual(doc.call_args.args[3], t0)
        with patch.object(S, '_doc_tick', return_value=[(t0 + 19000, 101.80, 101.90)]) as doc:
            self.assertEqual(S.cap_nhat(self.out, object(), 'A', NOW + timedelta(seconds=25)), 1)
            self.assertEqual(doc.call_args.args[3], t0 + 1000)
        self.assertEqual([r['tt'] for r in self.rows()], ['tp', 'cho'])
        self.assertAlmostEqual(S.tong_hop(self.out, 'A', 'XAUUSDp')['ds'][0]['r_moi'], 1.49)

    def test_thieu_phi_khong_vao_mau_va_sao_luu_doc_duoc(self):
        S.ghi(self.out, _goi(tien='EUR'), 7, NOW)
        with patch.object(S, '_doc_tick', return_value=[(S._ms(NOW) + 3000, 101.80, 101.90)]):
            S.cap_nhat(self.out, object(), 'A', NOW + timedelta(seconds=12))
        a = S.tong_hop(self.out, 'A', 'XAUUSDp')['ds'][0]
        self.assertEqual((a['thieu_phi'], a['da_cham'], a['thang_pct']), (1, 0, None))
        another = tempfile.TemporaryDirectory()
        self.addCleanup(another.cleanup)
        k = sao_luu.tao(self.root, Path(another.name))
        self.assertTrue(k['ok'], k)
        with zipfile.ZipFile(k['tep']) as z:
            raw = z.read('out/' + S.TEN_TEP)
        with closing(sqlite3.connect(':memory:')) as db:
            db.deserialize(raw)
            self.assertEqual(db.execute('SELECT tt FROM tin_hieu').fetchone()[0], 'tp')

    def test_api_chi_chu_doc_ket_qua_va_get_khong_ghi(self):
        S.ghi(self.out, _goi(), 0, NOW)
        config = self.root / 'config.json'
        config.write_text(json.dumps({'thu_muc_ra': str(self.out), 'gia': {'ma_vang': 'XAUUSDp'}}), encoding='utf-8')
        p = _goi()
        p['so_le'] = 2
        with patch.object(T, 'doc', return_value=p), web.tao_may_chu(str(config), port=0) as srv:
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            url = f'http://127.0.0.1:{srv.server_port}/api/tin-hieu-ngan'
            try:
                with self.assertRaises(urllib.error.HTTPError) as e:
                    urllib.request.urlopen(url, timeout=5).close()
                self.assertEqual(e.exception.code, 401)
                e.exception.close()
                with owner_urlopen(url, root=self.root, timeout=5) as r:
                    kq = json.load(r)
                self.assertEqual(kq['tien_cuu']['ds'][0]['cho'], 1)
                self.assertNotIn('tien_tk', kq)
                self.assertEqual(len(self.rows()), 1)
            finally:
                srv.shutdown()
                t.join()

    def test_vong_canh_ghi_khi_khong_co_trinh_duyet(self):
        cfg = {'gia': {'ma_vang': 'XAUUSDp'}, 'canh_bao': {'tien_cuu': True}}
        p = _goi()
        p['so_le'] = 2
        p['account_scope'] = 'test-owner-scope'
        p['ds'][0]['atr'] = 1.
        p['account_scope'] = 'test-owner-scope'
        p['ds'][0]['atr'] = 1.
        worker = canh_bao.VongCanh(lambda: cfg, lambda _: self.out)
        with (patch.object(canh_bao.song, 'khung_song', return_value={'nguon': 'mt5'}),
              patch.object(canh_bao.gia, 'luat', return_value={}), patch.object(T, 'doc', return_value=p),
              patch('so_cong_khai.entry_costs.estimate', return_value={'commission_price':.18,'slippage_price':.05})):
            self.assertEqual(len(worker.mot_vong(NOW)), 1)
            self.assertEqual(worker.mot_vong(NOW), [])
        self.assertEqual(S.tong_hop(self.out, 'A', 'XAUUSDp')['ds'][0]['cho'], 1)


if __name__ == '__main__':
    unittest.main()
