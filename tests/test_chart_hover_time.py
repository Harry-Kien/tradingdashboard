"""Nhãn ngày giờ phải đúng nến và múi giờ, không nhảy về nến cuối khi giá cập nhật."""
import unittest

from so_cong_khai import bieu_do
from test_chart_pro import node
from test_da_khung_realtime import page


def clock_js():
    a = bieu_do.JS.index('const DTS=')
    b = bieu_do.JS.index('const esc=', a)
    return bieu_do.JS[a:b]


class HoverTime(unittest.TestCase):
    def test_gio_viet_nam_du_ngay_nam_ke_ca_giao_thua(self):
        r = node(clock_js() + """
const cases=['2026-11-27T16:59:00Z','2026-11-27T17:00:00Z','2026-12-31T17:05:00Z'];
console.log(JSON.stringify(cases.map(s=>gioNen(Date.parse(s)/1000))));
""")
        for text, date, time in zip(r, ('27/11/2026', '28/11/2026', '01/01/2027'), ('23:59', '00:00', '00:05'), strict=True):
            self.assertIn(date, text)
            self.assertIn(time, text)
            self.assertIn('UTC+7', text)

    def test_cac_khung_lon_khong_bo_gio_khoi_nhan_con_tro(self):
        r = page("""
const t=Date.parse('2026-11-27T00:00:00Z')/1000;
console.log(JSON.stringify(DK.O.map(o=>o.chart.opts.localization.timeFormatter(t))));
""", {'o': [{'tf': tf} for tf in ('M1', 'D1', 'W1', 'MN1')]})
        for text in r:
            self.assertIn('27/11/2026', text)
            self.assertIn('07:00', text)
            self.assertIn('UTC+7', text)
        self.assertIn('timeFormatter:t=>gioNen(t)', bieu_do.JS)

    def test_giu_ngay_gio_ohlc_cua_nen_dang_tro_khi_ve_lai(self):
        a = bieu_do.JS.index('function lwDoc(')
        b = bieu_do.JS.index('// Yêu cầu về hiện tại', a)
        r = node(clock_js() + """
const first=Date.parse('2026-11-26T00:00:00Z')/1000,last=first+86400;
let D={candles:[[first,10,12,9,11],[last,20,22,19,21]],live:1};
const LW={hov:true,hoverTime:first,idx:new Map([[first,0],[last,1]])},R={style:{},innerHTML:''},LWE={clientWidth:900},on={},tf='D1';
const pal=()=>({fg:'#fff'}),kieu='toi',fp=String,f2=String,esc=String;
""" + bieu_do.JS[a:b] + """
lwDoc(null);const before=R.innerHTML;D.candles[1][4]=999;lwDoc(null);const tick=R.innerHTML;
// Nạp thêm lịch sử làm thay đổi chỉ số của nến đang trỏ.
D.candles.unshift([first-86400,1,2,.5,1]);LW.idx.set(first,1);LW.idx.set(last,2);D.live=2;lwDoc(null);const history=R.innerHTML;
LW.hov=false;LW.hoverTime=null;lwDoc(null);const leave=R.innerHTML;
console.log(JSON.stringify({before,tick,history,leave}));
""")
        self.assertEqual(r['before'], r['tick'])
        self.assertEqual(r['before'], r['history'])
        self.assertIn('26/11/2026', r['tick'])
        self.assertIn('07:00', r['tick'])
        self.assertIn('UTC+7', r['tick'])
        self.assertIn('27/11/2026', r['leave'])
        self.assertIn('<b>999</b>', r['leave'])

    def test_canvas_du_phong_cung_co_nhan_gio_duoi_con_tro(self):
        js = bieu_do.JS
        self.assertIn('const text=gioNen(D.candles[k][0])', js)
        self.assertIn('Math.max(0,Math.min(xx-tw/2,W-PR-tw))', js)
        self.assertIn('mouse.x>=0&&mouse.x<W-PR&&mouse.y>=PT&&mouse.y<H-PB', js)


if __name__ == '__main__':
    unittest.main()
