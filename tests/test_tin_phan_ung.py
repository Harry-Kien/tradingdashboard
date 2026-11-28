# -*- coding: utf-8 -*-
"""Tin sắp ra kèm số đo phản ứng giá (so_cong_khai.tin_phan_ung): ghép đúng theo tên tin, ưu tiên số từ 2024, báo chiều không đoán được."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from so_cong_khai import gia, tin_phan_ung as TP


class TinToi(unittest.TestCase):
    def test_ghep_so_do(self):
        with tempfile.TemporaryDirectory() as d:
            tep = Path(d) / 'p.json'
            tep.write_text(json.dumps({'loai': [{'ten': 'Nonfarm Payrolls', 'n': 138, 'd15_tv': 5.6, 'd15_p90': 19.5, 'gan_day_d15_tv': 9.1, 'gan_day_d15_p90': 30.2,
                                                 'qua10_15': 29.7}], 'quy_tac': {'b': {'kiem': [1555, 799, 51.4]}}, 'chon': 'b', 'qua_cong': False}), encoding='utf-8')
            that = gia.tin_sap_toi
            gia.tin_sap_toi = lambda cfg, now, n: [{'luc': '2026-12-04T13:30:00+00:00', 'ten': 'Nonfarm Payrolls'}, {'luc': '2026-12-04T15:00:00+00:00', 'ten': 'Lạ'}]
            try:
                kq = TP.tin_toi({}, datetime(2026, 12, 4, 12, 0, tzinfo=timezone.utc), 2, tep)
            finally:
                gia.tin_sap_toi = that
        self.assertEqual(kq['ds'][0], {'luc': '2026-12-04T13:30:00+00:00', 'ten': 'Nonfarm Payrolls', 'con_phut': 90, 'n': 138, 'd15_tv': 9.1, 'd15_p90': 30.2,
                                       'qua10_15': 29.7})
        self.assertIsNone(kq['ds'][1]['d15_tv'])
        self.assertEqual(kq['doan_chieu'], {'qua_cong': False, 'ty_le_kiem': 51.4})


if __name__ == '__main__':
    unittest.main()
