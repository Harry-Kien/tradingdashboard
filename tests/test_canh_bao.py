"""Bài kiểm cho phần cảnh báo: phát hiện trên nến vừa đóng, không báo lại, không báo trên nến cũ."""
from functools import partial
from http_owner import owner_urlopen
import json
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from so_cong_khai import bieu_do, canh_bao, gia, song, web  # noqa: E402
from test_gia import _kho  # noqa: E402

NEN = datetime(2026, 11, 20, 16, 30, tzinfo=timezone.utc)              # nến M15 mở 16:30, đóng 16:45
NOW = NEN + timedelta(minutes=16)


def _luat(**kw):
    base = {'bot_tin_hieu': [], 'ba_khung': {'quyet_dinh': None, 'trong_gio': True, 'nen': NEN.isoformat()},
            'dinh_day': {'hanh_dong': 'DUNG_NGOAI', 'nen': NEN.isoformat()}, 'tin': {'sap_toi': []}}
    base.update(kw)
    return base


class CanhBaoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / 'out'

    def tearDown(self):
        self.tmp.cleanup()

    def test_khong_co_gi_thi_khong_bao(self):
        self.assertEqual(canh_bao.tim(_luat(), NOW), [])

    def test_luat_bot_tren_nen_vua_dong(self):
        s = {'tf': 'M5', 'side': 'SELL', 'kind': 'DON', 'reason': 'Phá đáy 4 giờ.', 'sl': 3569.0, 'level': 3550.0,
             'bar': (NOW - timedelta(minutes=6)).isoformat()}
        a = canh_bao.tim(_luat(bot_tin_hieu=[s]), NOW)
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]['tieu_de'], 'Luật bot: BÁN trên M5')
        self.assertIn('SL theo luật 3.569,00', a[0]['noi_dung'])
        self.assertIn('chưa luật nào được chứng minh có lãi', a[0]['noi_dung'])

    def test_nen_cu_thi_khong_bao(self):
        s = {'tf': 'M15', 'side': 'BUY', 'kind': 'DON', 'reason': '', 'sl': 1.0, 'level': 1.0, 'bar': (NOW - timedelta(minutes=70)).isoformat()}
        self.assertEqual(canh_bao.tim(_luat(bot_tin_hieu=[s]), NOW), [])
        cu = _luat(ba_khung={'quyet_dinh': 'BAN', 'trong_gio': True, 'nen': (NOW - timedelta(hours=2)).isoformat()})
        self.assertEqual(canh_bao.tim(cu, NOW), [])

    def test_ba_khung_va_dinh_day(self):
        L = _luat(ba_khung={'quyet_dinh': 'BAN', 'trong_gio': True, 'nen': NEN.isoformat()},
                  dinh_day={'hanh_dong': 'MUA', 'nen': NEN.isoformat(), 'ly_do': 'Chạm đáy 8 giờ.', 'gia_vao': 3540.5, 'sl': 3530.0, 'tp1': 3556.25})
        a = canh_bao.tim(L, NOW)
        self.assertEqual([x['tieu_de'] for x in a], ['Luật ba khung: BÁN', 'Luật đỉnh/đáy: MUA'])
        self.assertIn('Giá vào 3.540,50, SL 3.530,00, TP 3.556,25', a[1]['noi_dung'])
        ngoai = _luat(ba_khung={'quyet_dinh': 'BAN', 'trong_gio': False, 'nen': NEN.isoformat()})
        self.assertEqual(canh_bao.tim(ngoai, NOW), [])                        # ngoài khung giờ của luật thì không báo

    def test_dang_ne_tin_thi_khong_bao_luat(self):
        s = {'tf': 'M5', 'side': 'SELL', 'kind': 'DON', 'reason': '', 'sl': 3569.0, 'level': 3550.0, 'bar': (NOW - timedelta(minutes=6)).isoformat()}
        L = _luat(bot_tin_hieu=[s], ba_khung={'quyet_dinh': 'BAN', 'trong_gio': True, 'nen': NEN.isoformat()},
                  dinh_day={'hanh_dong': 'MUA', 'nen': NEN.isoformat(), 'gia_vao': 1.0, 'sl': 1.0, 'tp1': 1.0}, tin={'sap_toi': [], 'dang_ne': True})
        self.assertEqual(canh_bao.tim(L, NOW), [])                            # bot và các luật không vào lệnh quanh tin: không báo
        L['tin']['dang_ne'] = False
        self.assertEqual(len(canh_bao.tim(L, NOW)), 3)

    def test_tin_sap_ra(self):
        gan, xa, qua = NOW + timedelta(minutes=25), NOW + timedelta(hours=3), NOW - timedelta(minutes=5)
        a = canh_bao.tim(_luat(tin={'sap_toi': [qua.isoformat(), gan.isoformat(), xa.isoformat()]}), NOW)
        self.assertEqual([x['khoa'] for x in a], [f'tin|{gan.isoformat()}'])
        self.assertIn(f'{gan.astimezone(canh_bao.VN):%H:%M}', a[0]['noi_dung'])

    def test_ghi_mot_lan_va_danh_so(self):
        a = [{'khoa': 'k1', 'tieu_de': 'A', 'noi_dung': 'x'}, {'khoa': 'k2', 'tieu_de': 'B', 'noi_dung': 'y'}]
        self.assertEqual([r['id'] for r in canh_bao.ghi_moi(self.out, a, NOW)], [1, 2])
        self.assertEqual(canh_bao.ghi_moi(self.out, a, NOW), [])               # cùng khóa: không báo lại
        new = canh_bao.ghi_moi(self.out, a + [{'khoa': 'k3', 'tieu_de': 'C', 'noi_dung': 'z'}], NOW)
        self.assertEqual([(r['id'], r['khoa']) for r in new], [(3, 'k3')])
        self.assertEqual([r['id'] for r in canh_bao.doc(self.out)], [3, 2, 1])   # mới nhất đứng trước
        self.assertEqual(canh_bao.doc(self.out / 'khong-co'), [])

    def test_vong_canh_va_api(self):
        gia._nho.clear()
        song._tt.update(deps=None, mt5=None, fr=None, thu=0.0, luc=0.0)
        d = Path(self.tmp.name)
        start = datetime(2026, 11, 16, tzinfo=timezone.utc)
        _kho(d, start, 2 * 1440)
        cfg = {'ten': 'Thử', 'thu_muc_ra': str(self.out), 'gia': {'kho_m1': str(d), 'ma_nguon': [], 'so_thang': 4}, 'canh_bao': {'bat': True, 'giay': 5}}
        cfgp = d / 'c.json'
        cfgp.write_text(json.dumps(cfg), encoding='utf-8')
        vong = web.tao_vong_canh(str(cfgp))
        self.assertEqual(vong.mot_vong(start + timedelta(days=2, minutes=3)), [])     # sổ giả không có luật nào ra tín hiệu
        self.assertEqual((vong.nguon, vong.loi), ('kho', None))
        self.assertFalse(vong.trang_thai()['dang_chay'])                               # chưa start
        canh_bao.ghi_moi(self.out, [{'khoa': 'k1', 'tieu_de': 'Luật bot: BÁN trên M5', 'noi_dung': 'thử'}], NOW)
        srv = web.tao_may_chu(str(cfgp), port=0, vong=vong)
        open_owner = partial(owner_urlopen, root=cfgp.parent)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            with open_owner(f'http://127.0.0.1:{srv.server_address[1]}/api/canh-bao', timeout=10) as r:
                j = json.loads(r.read())
        finally:
            srv.shutdown()
            srv.server_close()
            gia._nho.clear()
        self.assertEqual((len(j['ds']), j['ds'][0]['tieu_de'], j['dang_chay']), (1, 'Luật bot: BÁN trên M5', False))
        cfg['canh_bao']['bat'] = False
        cfgp.write_text(json.dumps(cfg), encoding='utf-8')
        self.assertIsNone(web.tao_vong_canh(str(cfgp)))

    def test_trang_co_o_canh_bao_va_khong_gui_di_dau(self):
        html = bieu_do.trang_bieu_do('Thử')
        for must in ('id="cb"', '/api/canh-bao', 'Thông báo trên máy', 'Âm thanh'):
            self.assertIn(must, html)
        src = (Path(canh_bao.__file__)).read_text(encoding='utf-8')
        for banned in ('order_send', 'sendMessage', 'api.telegram.org', 'requests.post', 'urlopen'):
            self.assertNotIn(banned, src)


if __name__ == '__main__':
    unittest.main()
