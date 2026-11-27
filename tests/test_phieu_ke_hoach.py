# -*- coding: utf-8 -*-
"""Phiếu kế hoạch dùng chung (so_cong_khai.phieu_ke_hoach) và API /api/phieu: giữ nguyên dữ liệu qua các màn, phiên bản không ghi đè,
kết quả kiểm cũ thành "cần kiểm lại" khi đổi giá, chấm mô phỏng không dùng nến tương lai, bấm lặp không ghi trùng."""
import base64
import http.client
import json
from http_owner import owner_cookie
import shutil
import subprocess
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from so_cong_khai import kiem_lenh_trang, ke_hoach_trang, nhat_ky_trang, phieu_ke_hoach as PK, web

NOW = datetime(2026, 11, 27, 8, 0, tzinfo=timezone.utc)
MAU = {'ma': 'XAUUSDp', 'chieu': 'BAN', 'vao': 3560.5, 'sl': 3580.5, 'tp': [3555.5, 3540.0], 'khung': 'M15',
       'phuong_phap': {'ma': 'harrison', 'ten': 'Harrison 3 Khung', 'phien_ban_quy_tac': 'harrison-3khung-research-1', 'kiem_chung': 'Nghiên cứu — chưa đạt cổng'},
       'nen_tin_hieu': '2026-11-27T07:45:00+00:00', 'luc_phan_tich': '2026-11-27T07:45:10+00:00', 'snapshot_id': 'phan-tich@2026-11-27T07:45:10+00:00',
       'ky_thuat': 'con_hieu_luc', 'nguon_gia': 'mt5'}
NODE = shutil.which('node')
JPEG = b'\xff\xd8\xff\xe0' + b'\x00' * 64


class LoiPhieu(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_giu_nguyen_va_khong_dien_mac_dinh(self):
        p = PK.tao(self.d, MAU, NOW)
        self.assertEqual((p['chieu'], p['vao'], p['sl'], p['tp'], p['phien_ban']), ('BAN', 3560.5, 3580.5, [3555.5, 3540.0], 1))
        self.assertEqual(p['phuong_phap']['phien_ban_quy_tac'], 'harrison-3khung-research-1')
        self.assertEqual(p['rui_ro']['trang_thai'], 'chua_kiem')
        p2 = PK.tao(self.d, {**MAU, 'sl': None, 'tp': []}, NOW)                  # thiếu SL/TP: để trống, không tự điền
        self.assertEqual((p2['sl'], p2['tp']), (None, []))
        for xau in ({**MAU, 'chieu': ''}, {**MAU, 'sl': 3550}, {**MAU, 'tp': [3570]}, {**MAU, 'vao': -1}, {**MAU, 'ma': ''}):
            with self.assertRaises(ValueError):
                PK.tao(self.d, xau, NOW)

    def test_phien_ban_va_can_kiem_lai(self):
        p = PK.tao(self.d, MAU, NOW)
        k = PK.gan_kiem(self.d, p['id'], {'ket_luan': 'dat', 'lot': 0.01, 'rui_ro_tien': 2.0, 'muc': [{'muc': 'tot', 'vi': {'tieu': 'SL hợp lý'}}]}, NOW)
        self.assertEqual((k['phien_ban'], k['rui_ro']['trang_thai'], k['rui_ro']['dau_lenh']), (2, 'dat', p['dau_lenh']))
        s = PK.sua_lenh(self.d, p['id'], {'vao': 3561.0}, NOW + timedelta(minutes=1))
        self.assertEqual((s['phien_ban'], s['thay_doi'], s['rui_ro']['trang_thai']), (3, ['vao'], 'can_kiem_lai'))
        self.assertEqual(PK.doc(self.d, p['id'], 1)['vao'], 3560.5)                  # bản cũ vẫn đọc lại được
        self.assertEqual(PK.doc(self.d, p['id'])['cac_ban'], [1, 2, 3])
        with self.assertRaises(ValueError):
            PK.sua_lenh(self.d, p['id'], {'vao': 3561.0})                            # không có gì đổi
        with self.assertRaises(ValueError):
            PK.gan_kiem(self.d, p['id'], {'ket_luan': 'thang_chac'})

    def test_bam_lap_khong_ghi_trung(self):
        p = PK.tao(self.d, MAU, NOW)
        PK.bat_dau_theo_doi(self.d, p['id'], NOW)
        with self.assertRaises(ValueError):
            PK.bat_dau_theo_doi(self.d, p['id'], NOW)
        with self.assertRaises(ValueError):
            PK.dung_ngoai(self.d, p['id'])
        q = PK.tao(self.d, MAU, NOW)
        PK.dung_ngoai(self.d, q['id'], 'tin mạnh sắp ra', NOW)
        with self.assertRaises(ValueError):
            PK.bat_dau_theo_doi(self.d, q['id'], NOW)
        self.assertEqual(len(PK.danh_sach(self.d)), 2)

    def test_ghi_chu_la_lop_them(self):
        p = PK.tao(self.d, MAU, NOW)
        g = PK.ghi_chu(self.d, p['id'], 'vào sớm hơn kế hoạch', ['vào sớm'], 'review_sau', NOW, tuan_thu='lech')
        self.assertEqual({k: g[k] for k in ('vao', 'sl', 'tp', 'chieu')}, {k: p[k] for k in ('vao', 'sl', 'tp', 'chieu')})
        self.assertEqual((g['tuan_thu'], g['ghi_chu_nd'][0]['tag']), ('lech', ['vào sớm']))
        for xau in (('', []), ):
            with self.assertRaises(ValueError):
                PK.ghi_chu(self.d, p['id'], *xau)

    def test_dong_hong_khong_mat_du_lieu(self):
        p = PK.tao(self.d, MAU, NOW)
        with open(self.d / 'ke-hoach' / 'phieu.jsonl', 'a', encoding='utf-8') as f:
            f.write('{"id": "KH-hong", "phien_b')                                      # dòng ghi dở
        self.assertEqual(PK.doc(self.d, p['id'])['vao'], 3560.5)
        q = PK.tao(self.d, MAU, NOW)                                                   # ghi tiếp được sau dòng hỏng
        self.assertIsNotNone(PK.doc(self.d, q['id']))

    def test_anh(self):
        p = PK.tao(self.d, MAU, NOW)
        for xau in ('data:text/html;base64,PGI+', 'data:image/jpeg;base64,!!!', 'data:image/jpeg;base64,' + base64.b64encode(b'GIF89a').decode()):
            with self.assertRaises(ValueError):
                PK.luu_anh(self.d, p['id'], xau)
        a = PK.luu_anh(self.d, p['id'], 'data:image/jpeg;base64,' + base64.b64encode(JPEG).decode())
        self.assertEqual(PK.duong_anh(self.d, a['anh']).read_bytes(), JPEG)
        self.assertIsNone(PK.duong_anh(self.d, '../cau-hinh.json'))
        with self.assertRaises(ValueError):
            PK.luu_anh(self.d, p['id'], 'data:image/jpeg;base64,' + base64.b64encode(JPEG).decode())

    def test_cham_khong_dung_nen_tuong_lai(self):
        p = {**PK.chuan_hoa(MAU), 'theo_doi': {'tu': NOW.isoformat()}}
        t0 = int(NOW.timestamp())
        truoc = [[t0 - 300, 3560, 3600, 3530, 3560]]                                   # nến trước lúc theo dõi chạm cả SL lẫn TP: không tính
        self.assertEqual(PK.cham_mo_phong(p, truoc + [[t0, 3561, 3562, 3559, 3560]])['trang_thai'], 'dang_mo')
        self.assertEqual(PK.cham_mo_phong(p, truoc + [[t0, 3561, 3562, 3559, 3560], [t0 + 300, 3560, 3561, 3555, 3556]])['trang_thai'], 'tp')
        cung = PK.cham_mo_phong(p, truoc + [[t0, 3560, 3581, 3550, 3560]])           # một nến chạm cả SL và TP: SL trước
        self.assertEqual((cung['trang_thai'], cung['r']), ('sl', -1.0))
        self.assertEqual(PK.cham_mo_phong(p, [[t0, 3570, 3572, 3565, 3566]])['trang_thai'], 'chua_khop')
        self.assertEqual(PK.cham_mo_phong(p, [[t0 + 3600, 3561, 3562, 3559, 3560]])['trang_thai'], 'chua_xac_dinh')   # thiếu đoạn đầu
        self.assertEqual(PK.cham_mo_phong(p, truoc)['trang_thai'], 'chua_xac_dinh')
        self.assertEqual(PK.cham_mo_phong(PK.chuan_hoa(MAU), truoc)['trang_thai'], 'khong_theo_doi')


class ApiPhieu(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.p = self.d / 'cau-hinh.json'
        self.p.write_text(json.dumps({'gia': {'ma_nguon': [], 'mt5': {'bat': False}}, 'ai': {'bat': False}, 'thu_muc_ra': str(self.d / 'out')}), encoding='utf-8')
        self.srv = web.tao_may_chu(str(self.p), port=0)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.cookie = owner_cookie(self.p.parent)
        self.port = self.srv.server_address[1]

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()

    def goi(self, phuong, duong, than=None, rieng=True):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=30)
        b = json.dumps(than).encode() if than is not None else b''
        h = {'Content-Type': 'application/json', 'Content-Length': str(len(b)), 'Cookie': self.cookie}
        if rieng:
            h['X-So-Cong-Khai'] = '1'
        c.request(phuong, duong, body=b, headers=h)
        r = c.getresponse()
        return r.status, r.read()

    def test_luong_phieu(self):
        ma, b = self.goi('POST', '/api/phieu', {'viec': 'tao', 'phieu': MAU})
        self.assertEqual(ma, 200, b)
        id_ = json.loads(b)['phieu']['id']
        ma, b = self.goi('GET', f'/api/phieu?id={id_}')
        p = json.loads(b)
        self.assertEqual((p['vao'], p['sl'], p['tp'], p['phuong_phap']['ma'], p['cham']['trang_thai']), (3560.5, 3580.5, [3555.5, 3540.0], 'harrison', 'khong_theo_doi'))
        self.assertEqual(self.goi('POST', '/api/phieu', {'viec': 'theo_doi', 'id': id_})[0], 200)
        self.assertEqual(self.goi('POST', '/api/phieu', {'viec': 'theo_doi', 'id': id_})[0], 400)          # bấm lặp
        self.assertEqual(self.goi('POST', '/api/phieu', {'viec': 'tao', 'phieu': {**MAU, 'sl': 1}})[0], 400)
        self.assertNotEqual(self.goi('POST', '/api/phieu', {'viec': 'tao', 'phieu': MAU}, rieng=False)[0], 200)   # thiếu tiêu đề riêng của trang
        self.assertEqual(self.goi('GET', '/api/phieu?id=KH-khong-co-dau')[0], 404)
        self.assertEqual(self.goi('GET', '/api/phieu?id=../../x')[0], 404)
        ds = json.loads(self.goi('GET', '/api/phieu/ds')[1])['ds']
        self.assertEqual([x['id'] for x in ds], [id_])                                  # yêu cầu thiếu tiêu đề riêng không tạo phiếu


@unittest.skipUnless(NODE, 'không có Node')
class CuPhapTrang(unittest.TestCase):
    def test_js_hop_le(self):
        import re
        for ten, h in (('ke_hoach', ke_hoach_trang.trang_ke_hoach('T')), ('kiem_lenh', kiem_lenh_trang.trang_kiem_lenh('T')), ('nhat_ky', nhat_ky_trang.trang_nhat_ky('T'))):
            with tempfile.TemporaryDirectory() as d:
                for i, s in enumerate(re.findall(r'<script>(.*?)</script>', h, re.S)):
                    f = Path(d) / f'{ten}{i}.js'
                    f.write_text(s, encoding='utf-8')
                    r = subprocess.run([NODE, '--check', str(f)], capture_output=True, text=True, encoding='utf-8')
                    self.assertEqual(r.returncode, 0, f'{ten} #{i}: {r.stderr[-800:]}')
            self.assertIn('PKJ', h)


if __name__ == '__main__':
    unittest.main()
