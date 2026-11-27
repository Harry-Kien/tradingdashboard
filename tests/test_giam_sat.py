"""Bài kiểm cho giám sát rủi ro (giam_sat.danh_gia là hàm thuần), đường dẫn /api/giam-sat và dải cảnh báo trên trang."""
from functools import partial
from http_owner import owner_urlopen
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import dich, giam_sat as G, trang, web  # noqa: E402

NOW = datetime(2026, 11, 26, 6, 0, tzinfo=timezone.utc)                         # 13:00 giờ VN


def TK(**k):
    return {'san_sang': True, 'von': 10000.0, 'tien': 'USD', 'rui_ro': {'tong': 100.0, 'khong_sl': 0}, 'lenh': [], 'theo_ngay': [], 'da_dong': [], **k}


def L(ma='XAUUSD', sl=3490.0, rui_ro=100.0, mo=NOW - timedelta(hours=1), huong='MUA'):
    return {'ma': ma, 'huong': huong, 'lot': 0.1, 'vao': 3500.0, 'sl': sl, 'mo': mo.isoformat(), 'nguon': 'Đặt tay', 'rui_ro': rui_ro}


def ids(ds):
    return [a['id'].split('-')[0] for a in ds]


class DanhGiaTest(unittest.TestCase):
    def test_tai_khoan_on(self):
        self.assertEqual(G.danh_gia(TK(lenh=[L()]), now=NOW), [])

    def test_lo_ngay_va_tong_rui_ro(self):
        ds = G.danh_gia(TK(theo_ngay=[{'ngay': '2026-11-26', 'lai': -320.0}]), now=NOW)   # 320 / (10.000 + 320) = 3,1% ≥ 3%
        self.assertEqual(ids(ds), ['ngay'])
        self.assertEqual(ds[0]['muc'], 'xau')
        self.assertEqual(G.danh_gia(TK(theo_ngay=[{'ngay': '2026-11-25', 'lai': -900.0}]), now=NOW), [])   # lỗ hôm qua không tính
        self.assertEqual(ids(G.danh_gia(TK(rui_ro={'tong': 700.0}), now=NOW)), ['tong'])
        self.assertEqual(G.danh_gia(TK(rui_ro={'tong': 700.0}), {'tong_rui_ro_toi_da_pct': 8}, now=NOW), [])

    def test_lenh_khong_sl_va_rui_ro_lon(self):
        ds = G.danh_gia(TK(lenh=[L(sl=None, rui_ro=None), L(ma='EURUSD', rui_ro=600.0)]), now=NOW)
        self.assertEqual(ids(ds), ['khong', 'lon'])                                    # đỏ trước vàng
        self.assertEqual([a['muc'] for a in ds], ['xau', 'chu_y'])
        self.assertIn('6,0%', ds[1]['vi']['tieu'])

    def test_vao_gap_sau_thua(self):
        mo = NOW - timedelta(minutes=30)
        tk = TK(lenh=[L(mo=mo)], da_dong=[{'luc': (mo - timedelta(minutes=5)).isoformat(), 'lai': -50.0}])
        self.assertEqual(ids(G.danh_gia(tk, now=NOW)), ['gap'])
        tk['da_dong'][0]['lai'] = 50.0                                                  # lệnh trước thắng: không cảnh báo
        self.assertEqual(G.danh_gia(tk, now=NOW), [])
        tk = TK(lenh=[L(mo=NOW - timedelta(hours=5))], da_dong=[{'luc': (NOW - timedelta(hours=5, minutes=5)).isoformat(), 'lai': -50.0}])
        self.assertEqual(G.danh_gia(tk, now=NOW), [])                                  # đã quá 2 giờ: thôi nhắc

    def test_tin_manh_cua_lenh_dang_giu(self):
        tin = [{'t': (NOW + timedelta(minutes=20)).isoformat(), 'tien': 'USD', 'ten': 'CPI m/m'}]
        ds = G.danh_gia(TK(lenh=[L()]), now=NOW, tin=tin)
        self.assertEqual(ids(ds), ['tin'])
        self.assertIn('XAUUSD', ds[0]['vi']['noi'])
        self.assertEqual(G.danh_gia(TK(lenh=[L(ma='EURJPY')]), now=NOW, tin=tin), [])     # EURJPY không dính USD
        self.assertEqual(ids(G.danh_gia(TK(lenh=[L(ma='EURJPY')]), now=NOW, tin=tin, tien_cua_ma={'EURJPY': ['USD']})), ['tin'])
        self.assertEqual(G.danh_gia(TK(), now=NOW, tin=tin), [])                         # không giữ lệnh: không báo

    def test_id_rieng_cho_tung_lenh_va_tung_tin(self):
        mo = NOW - timedelta(hours=1)
        hai = [{**L(sl=None, rui_ro=None, mo=mo), 've': 11}, {**L(sl=None, rui_ro=None, mo=mo), 've': 12}]   # cùng mã, cùng giây mở
        self.assertEqual(len({a['id'] for a in G.danh_gia(TK(lenh=hai), now=NOW)}), 2)
        khong_ve = [L(sl=None, rui_ro=None, mo=mo), L(sl=None, rui_ro=None, mo=mo)]
        self.assertEqual(len({a['id'] for a in G.danh_gia(TK(lenh=khong_ve), now=NOW)}), 2)
        t = (NOW + timedelta(minutes=20)).isoformat()
        tin = [{'t': t, 'tien': 'USD', 'ten': 'Non-Farm Payrolls'}, {'t': t, 'tien': 'USD', 'ten': 'Unemployment Rate'}]
        self.assertEqual(len({a['id'] for a in G.danh_gia(TK(lenh=[L()]), now=NOW, tin=tin)}), 2)

    def test_doan_tien_tu_ten_ma(self):
        self.assertEqual(G._doan_tien('EURUSDp'), ['EUR', 'USD'])
        self.assertEqual(G._doan_tien('XAUUSD'), ['USD'])
        self.assertEqual(G._doan_tien('US30Cash'), ['USD'])
        self.assertEqual(G._doan_tien('GER40'), ['USD'])

    def test_ban_tieng_anh_va_id_on_dinh(self):
        tin = [{'t': (NOW + timedelta(minutes=20)).isoformat(), 'tien': 'USD', 'ten': 'CPI m/m'}]
        mo = NOW - timedelta(minutes=30)
        tk = TK(lenh=[L(sl=None, rui_ro=None, mo=mo), L(ma='EURUSD', rui_ro=600.0, huong='BAN')], rui_ro={'tong': 900.0},
                theo_ngay=[{'ngay': '2026-11-26', 'lai': -400.0}], da_dong=[{'luc': (mo - timedelta(minutes=5)).isoformat(), 'lai': -50.0}])
        a, b = G.danh_gia(tk, now=NOW, tin=tin), G.danh_gia(tk, now=NOW, tin=tin)
        self.assertEqual(len(a), 6)
        self.assertEqual([x['id'] for x in a], [x['id'] for x in b])
        for x in a:
            self.assertIsNone(dich._VI.search(x['en']['tieu'] + ' ' + x['en']['noi']), x['en'])


class DaiCanhBaoTest(unittest.TestCase):
    def test_ten_rieng_va_an_han_khi_khong_co_canh_bao(self):
        k = trang.GIAM_SAT
        self.assertIn('.gsr[hidden]{display:none}', k)                                # display:grid không được đè thuộc tính hidden
        for cu in ('class="gs"', '.gs{', '.gs-m', 'gs-dai', 'data-gs='):                # lớp .gs là của phần gia sư (hoc_giao_dich.py)
            self.assertNotIn(cu, k.replace('gsr', '§'), cu)


class WebTest(unittest.TestCase):
    def test_duong_dan_va_dai_canh_bao(self):
        with tempfile.TemporaryDirectory() as d:
            ch = Path(d) / 'cau-hinh.json'
            ch.write_text(json.dumps({'gia': {}}), encoding='utf-8')
            srv = web.tao_may_chu(str(ch), port=0)
            open_owner = partial(owner_urlopen, root=ch.parent)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            u = f'http://127.0.0.1:{srv.server_address[1]}'
            try:
                j = json.loads(open_owner(u + '/api/giam-sat', timeout=60).read())
                self.assertEqual((j['san_sang'], j['ds']), (False, []))                   # không có MT5: báo rõ, không lỗi
                with self.assertRaises(urllib.error.HTTPError) as c:
                    open_owner(u + '/api/giam-sat?q_lo_ngay_toi_da_pct=nan', timeout=30)
                self.assertEqual(c.exception.code, 400)
                for p in ('/ke-hoach', '/thi-truong'):
                    self.assertIn('id="gsr-dai"', open_owner(u + p, timeout=60).read().decode('utf-8'))
            finally:
                srv.shutdown()
                srv.server_close()
                trang.MIEN_TRU = trang.MIEN_TRU_GOC


if __name__ == '__main__':
    unittest.main()
