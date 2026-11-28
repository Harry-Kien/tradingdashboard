# -*- coding: utf-8 -*-
"""Sửa nhãn giờ nến vàng nhiều năm (so_cong_khai.sua_gio): mùa đông châu Âu trước 18/02/2024 cộng 1 giờ, 18/02–19/05/2024 trừ 1 giờ, về sau giữ nguyên."""
import unittest

import pandas as pd

from so_cong_khai import sua_gio


def _t(*s):
    return pd.DatetimeIndex([pd.Timestamp(x, tz='UTC') for x in s])


class SuaGio(unittest.TestCase):
    def test_ba_doan(self):
        vao = _t('2023-01-10 12:30', '2023-07-10 12:30', '2024-03-08 14:30', '2024-06-07 12:30', '2026-11-06 13:30')
        ra = _t('2023-01-10 13:30', '2023-07-10 12:30', '2024-03-08 13:30', '2024-06-07 12:30', '2026-11-06 13:30')
        self.assertTrue(sua_gio.gio_that(vao).equals(ra))

    def test_doi_gio_chau_au(self):
        # 2023: châu Âu sang giờ hè 26/03, về giờ đông 29/10 (Chủ nhật cuối tháng)
        vao = _t('2023-03-24 12:00', '2023-03-27 12:00', '2023-10-27 12:00', '2023-10-30 12:00')
        self.assertEqual([x.strftime('%m-%d %H:%M') for x in sua_gio.gio_that(vao)], ['03-24 13:00', '03-27 12:00', '10-27 12:00', '10-30 13:00'])

    def test_khong_chong_nen_o_ranh_gioi(self):
        idx = pd.date_range('2015-01-01', '2026-11-20', freq='1min', tz='UTC')
        idx = idx[idx.day_of_week < 5]                                       # bỏ cuối tuần như thị trường thật
        moi = sua_gio.gio_that(idx)
        self.assertTrue(moi.is_unique)
        self.assertTrue(moi.is_monotonic_increasing)

    def test_rong(self):
        self.assertEqual(len(sua_gio.gio_that(pd.DatetimeIndex([], tz='UTC'))), 0)


if __name__ == '__main__':
    unittest.main()
