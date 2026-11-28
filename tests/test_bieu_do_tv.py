# -*- coding: utf-8 -*-
"""Các phần biểu đồ theo kiểu TradingView (28/11/2026): khối lượng ở đáy biểu đồ chính, hàng khoảng thời gian, mức thay đổi trên dòng OHLC."""
import unittest

from so_cong_khai import bieu_do, bieu_do_them


class BieuDoTV(unittest.TestCase):
    def test_khoi_luong_day(self):
        js = bieu_do_them.JS
        self.assertIn("let ON={phien:0,hoso:0,thang:0,ss:'',kl:1};", js)                  # bật sẵn như TradingView
        self.assertIn("if(!ON.kl||CBCN.dung('vol')||!v||!cs||!cs.length){if(KLS)klBo(c);return}", js)   # không vẽ trùng chỉ báo Khối lượng; không có tick volume thì gỡ
        self.assertIn("priceScaleId:'kl-day'", js)
        self.assertIn("scaleMargins:{top:.82,bottom:0},visible:false", js)                    # thang riêng ẩn, không làm lệch thang giá
        self.assertIn('data-k="kl"', js)
        self.assertIn('klBo(B.LW.chart)', js.split("addEventListener('chart-context-changing'", 1)[1].split('\n', 1)[0])

    def test_hang_khoang_thoi_gian(self):
        js = bieu_do_them.JS
        kg = js.split('const KG=[', 1)[1].split('];', 1)[0]
        self.assertEqual(kg.count("['"), 8)
        for nhan, tf in (('1 ngày', 'M5'), ('5 ngày', 'M15'), ('1 tháng', 'H1'), ('3 tháng', 'H4'), ('YTD', 'D1'), ('1 năm', 'D1')):
            self.assertRegex(kg, rf"\['{nhan}','[^']+',\d+,'{tf}'\]")
        self.assertIn("['Tất cả','Xem toàn bộ nến đã tải của khung đang xem',-1,null]", kg)
        self.assertIn("document.querySelector('#cp>.ban-chan')", js)                         # nằm trong hàng ghi công dưới biểu đồ
        self.assertIn('.kg-hang button', bieu_do_them.CSS)

    def test_thay_doi_tren_dong_ohlc(self):
        html = bieu_do.JS if hasattr(bieu_do, 'JS') else ''
        nguon = html or open(bieu_do.__file__, encoding='utf-8').read()
        self.assertIn("const d=c[4]-cs[k-1][4],p=d/cs[k-1][4]*100", nguon)
        self.assertIn("LWE.clientWidth>=420", nguon)                                          # màn hẹp bỏ để dòng giá không xuống ba dòng


if __name__ == '__main__':
    unittest.main()
