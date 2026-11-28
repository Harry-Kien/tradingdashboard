# -*- coding: utf-8 -*-
"""Đo lại trên dữ liệu mới, tự động (so_cong_khai/do_lai.py): lịch mỗi tháng, chạy công cụ ở tiến trình riêng (giả), tóm tắt cho trang Biểu đồ.
Và: công cụ đo lại giữ nguyên tám công thức chốt ngày 24/11/2026, theo dõi bản có L6 riêng (cong-cu/CHUAN_HOA_DANG_KY.md)."""
import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from so_cong_khai import do_lai, phieu

# công thức trên phiếu chốt ngày 24/11/2026 (trước bộ lọc L6): phép đo lại trên dữ liệu mới phải dùng đúng các công thức này
CHOT_24_11 = {'pha_vo': ('V2', 'S3', ('L4',)), 'ict': ('V3', 'S2', ('L2', 'L4')), 'ict_fvg': ('V3', 'S0', ('L2', 'L4')), 'elliott': ('V0', 'S2', ()),
              'wyckoff': ('V2', 'S1', ('L4',)), 'price_action': ('V2', 'S3', ('L1',)), 'fib': ('V1', 'S0', ('L2',)), 'ema_hoi': ('V2', 'S3', ())}


class Lich(unittest.TestCase):
    def test_moi_thang_mot_lan(self):
        now = datetime(2026, 12, 3, tzinfo=timezone.utc)
        self.assertTrue(do_lai.den_han(None, now))
        self.assertTrue(do_lai.den_han({'luc': '2026-11-26T05:00:00+00:00'}, now))            # tháng trước
        self.assertFalse(do_lai.den_han({'luc': '2026-12-01T05:00:00+00:00'}, now))           # đã đo trong tháng này
        self.assertTrue(do_lai.den_han({'luc': 'hỏng'}, now))


class Chay(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.goc = Path(self.d.name)
        (self.goc / 'cong-cu').mkdir()
        (self.goc / 'out').mkdir()
        (self.goc / do_lai.CONG_CU).write_text('# giả', encoding='utf-8')
        for p in do_lai.CAN:
            (self.goc / p).write_text('{}', encoding='utf-8')

    def tearDown(self):
        self.d.cleanup()

    def test_khong_co_cong_cu_thi_khong_chay(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(do_lai.co_the(Path(d)))
            self.assertFalse(do_lai.chay(Path(d), chay_lenh=lambda *a, **k: self.fail('không được gọi'))['ok'])

    def test_chay_tien_trinh_rieng_uu_tien_thap(self):
        goi = []

        def gia(lenh, **kw):
            goi.append((lenh, kw))
            return SimpleNamespace(returncode=0, stdout='Ghi out/du-lieu-moi.json', stderr='')
        kq = do_lai.chay(self.goc, chay_lenh=gia)
        self.assertTrue(kq['ok'])
        lenh, kw = goi[0]
        self.assertTrue(lenh[-1].endswith('do_lai_du_lieu_moi.py'))
        self.assertEqual((kw['cwd'], kw['timeout']), (str(self.goc), do_lai.HAN_GIAY))
        self.assertEqual(kw['creationflags'] & getattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', 0), getattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', 0))
        self.assertTrue((self.goc / 'out' / 'du-lieu-moi.log').exists())
        self.assertFalse(do_lai.TT['dang'])

    def test_cong_cu_loi_va_qua_han(self):
        kq = do_lai.chay(self.goc, chay_lenh=lambda *a, **k: SimpleNamespace(returncode=1, stdout='', stderr='Traceback\nKeyError: L6'))
        self.assertIn('KeyError: L6', kq['loi'])

        def lau(*a, **k):
            raise subprocess.TimeoutExpired('python', 1)
        self.assertIn('phút', do_lai.chay(self.goc, chay_lenh=lau)['loi'])
        self.assertFalse(do_lai.TT['dang'])

    def test_tom_tat_gan_ma_phuong_phap(self):
        (self.goc / do_lai.KET_QUA).write_text(json.dumps({'luc': '2026-11-26T05:00:00+00:00', 'so_ngay': 1, 'muc': [
            {'nhom': 'Công thức phiếu', 'ten': 'Phá vỡ đỉnh/đáy', 'n': 3, 'ket': 'chua_du'},
            {'nhom': 'Công thức phiếu có L6 (từ 26/11/2026)', 'ten': 'Phá vỡ đỉnh/đáy', 'n': 1, 'ket': 'chua_du'},
            {'nhom': 'Luật bot', 'ten': 'Luật bot · bản hiện tại (vào ngay)', 'n': 40, 'ket': 'co_lai'},
            {'nhom': 'Lọc lệnh bằng mô hình', 'ten': 'Cây tăng cường, giữ 30%', 'n': 5, 'ket': 'chua_du'}]}), encoding='utf-8')
        t = do_lai.tom_tat(self.goc, ten_ma={'Phá vỡ đỉnh/đáy': 'pha_vo'})
        self.assertTrue(t['co_the'])
        self.assertEqual([x['ma'] for x in t['muc']], ['pha_vo', 'pha_vo', 'bot', None])
        self.assertEqual([x['ket_ten'] for x in t['muc']], ['chưa đủ lệnh', 'chưa đủ lệnh', 'vẫn có lãi', 'chưa đủ lệnh'])


class CongThucChot(unittest.TestCase):
    def test_bo_l6_ra_thi_dung_cong_thuc_24_11(self):
        """Công cụ đo lại bỏ L6 khỏi công thức phiếu để đo đúng bản đã chốt; nếu ai đổi phiếu theo cách khác thì bài này báo."""
        for ma, (vao, sl, loc) in CHOT_24_11.items():
            ct = phieu.CONG_THUC[ma]
            self.assertEqual((ct['vao'], ct['sl'], tuple(k for k in ct['loc'] if k not in ('L6', 'H1', 'H2'))), (vao, sl, loc), ma)   # L6, hợp lưu thêm sau 24/11
        src = (Path(__file__).resolve().parent.parent / 'cong-cu' / 'do_lai_du_lieu_moi.py').read_text(encoding='utf-8')
        self.assertIn("loc = tuple(k for k in ct['loc'] if k not in ('L6', 'H1', 'H2'))", src)
        self.assertIn("MOC_L6 = '2026-11-26T00:00:00+00:00'", src)


if __name__ == '__main__':
    unittest.main()
