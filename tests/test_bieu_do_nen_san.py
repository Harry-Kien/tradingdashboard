# -*- coding: utf-8 -*-
"""Nến có sẵn khi mở trang Biểu đồ (26/11/2026). Lỗi đã gặp: trang chỉ gọi /api/gia sau khi trình duyệt đọc xong toàn bộ trang (khoảng 150 ms),
rồi chờ máy chủ tính (50 tới 400 ms; lúc webapp vừa khởi động lại, đang nối MT5, là khoảng 10 giây), nên lần mở nào cũng thấy
"Đang tải dữ liệu nến…". Sửa: đầu trang gọi nến ngay từ dòng đầu, và bản nến của lần xem trước được vẽ tạm khi máy chủ chưa kịp trả."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import bieu_do  # noqa: E402

CHAY = r"""
const goi=[];let luu=null;
globalThis.window=globalThis;
globalThis.location={search:process.argv[3]||''};
globalThis.localStorage={getItem:k=>k==='so-ma'?(process.argv[4]||null):null};
globalThis.fetch=(u,o)=>{goi.push([u,o&&o.cache]);return Promise.resolve({ok:true})};
globalThis.caches={open:n=>Promise.resolve({match:u=>{luu=[n,u];return Promise.resolve({headers:{get:()=>'1700000000000'},json:()=>Promise.resolve({tf:'M15',candles:[]})})}})};
require(process.argv[2]);
setTimeout(async()=>{const o=globalThis.BDNAP,j=o&&o.luu?await o.luu:null;console.log(JSON.stringify({goi,luu,u:o&&o.u,xong:o&&o.xong,luc:j&&j._luc,coLuu:!!(o&&o.luu)}))},20);
"""


class NenCoSan(unittest.TestCase):
    def test_dau_trang_goi_nen_truoc_khi_doc_trang(self):
        h = bieu_do.trang_bieu_do('Harry')
        self.assertLess(h.index('window.BDNAP='), h.index('<style>'))            # chạy trước khi trình duyệt đọc CSS và 400 KB mã của trang
        self.assertLess(h.index('window.BDNAP='), h.index('</head>'))

    def test_load_dung_lan_goi_som_va_luu_ban_nen(self):
        js = bieu_do.JS
        self.assertIn("r=await napSom(u,cu,ticket.signal);if(!r.ok)throw new Error(await r.text());if(cu())return;luuGhi(u,r);txt=await r.text();if(cu())return;nhoGhi(u,txt)}", js)
        self.assertIn("if(!o||o.u!==u){if(o?.ctl)o.ctl.abort();return fetch(u,{cache:'no-store',signal})}", js)   # đổi mã/khung, hoặc địa chỉ không khớp: gọi như cũ
        self.assertIn("if(!tam){hisTai()", js)   # bản mới về thì bỏ nhãn "nến lưu"

    def test_nen_luu_khong_mang_gia_va_lenh_cu(self):
        """Bản lưu chỉ để vẽ nến đã đóng: không giá bid/ask, không lệnh đang mở, không luật, không nến đang chạy, không mở luồng tick."""
        js = bieu_do.JS
        self.assertIn("j.nguon='luu';j.luat=null;j.lenh=[];j.bid=j.ask=null;delete j.dang_chay;", js)
        self.assertIn('if(D||ANH||!j||', js)                                     # ảnh gửi Telegram không bao giờ chụp nến cũ
        self.assertIn("D&&D.nguon==='luu'?3000:60000", js)                       # đang vẽ nến lưu thì thử lại sau 3 giây, không chờ 60 giây

    def test_chu_dang_tai_hien_cham(self):
        h = bieu_do.trang_bieu_do('Harry')
        self.assertIn('.stage[data-tai]::after{animation:tai-hien', h)           # tải nhanh thì không nháy chữ "Đang tải dữ liệu nến…"
        self.assertIn('.stage[data-luu]::before{content:attr(data-luu)', h)

    @unittest.skipUnless(shutil.which('node'), 'máy không có Node.js')
    def test_dia_chi_goi_som_khop_voi_load(self):
        """Đoạn đầu trang phải dựng đúng địa chỉ mà load() dựng (cùng mã, cùng khung), nếu không lần gọi sớm bị bỏ phí."""
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'nap.js').write_text(bieu_do.NAP_SOM, encoding='utf-8')
            (Path(d) / 'chay.js').write_text(CHAY, encoding='utf-8')

            def chay(search='', ma=''):
                r = subprocess.run(['node', str(Path(d) / 'chay.js'), str(Path(d) / 'nap.js'), search, ma], capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(r.returncode, 0, r.stderr[:400])
                return json.loads(r.stdout)
            a = chay()
            self.assertEqual(a['goi'], [['/api/gia?tf=M15&n=900', 'no-store']])
            self.assertEqual(a['luu'], ['so-nen', '/api/gia?tf=M15&n=900'])
            self.assertEqual((a['u'], a['xong'], a['luc']), ('/api/gia?tf=M15&n=900', 1, 1700000000000))
            self.assertEqual(chay('', 'BTCUSD')['u'], '/api/gia?tf=M15&n=900&ma=BTCUSD')           # mã đang xem lần trước
            self.assertEqual(chay('?ma=EUR%2FUSD', 'BTCUSD')['u'], '/api/gia?tf=M15&n=900&ma=EUR%2FUSD')   # ?ma= thắng mã đã nhớ
            b = chay('?anh=1&tf=H1')
            self.assertEqual(b['u'], '/api/gia?tf=H1&n=900')                     # chế độ ảnh: đúng khung, không đọc bản lưu
            self.assertFalse(b['coLuu'])
            self.assertEqual(chay('?anh=1&tf=XYZ')['u'], '/api/gia?tf=M15&n=900')
        self.assertRegex(bieu_do.JS, re.escape("function giaU(k,m){return '/api/gia?tf='+k+'&n=900'+(m?'&ma='+encodeURIComponent(m):'')}"))
        self.assertIn('const u=giaU(t0,m0);', bieu_do.JS)                       # load() dùng cùng địa chỉ (27/11/2026: tách ra để nạp trước khung khác)


CHAY_CON = r"""
%s
const Y=new Date().getUTCFullYear(),now=Math.floor(Date.now()/1000),c=[];for(let i=0;i<900;i++)c.push([now-(900-i)*900,1,1,1,1]);
const moc=c[260][0]*1000,ra={
 moi_luu:hisCon({nam:Y,_luc:Date.now()-3600e3},c),          // lưu cách đây 1 giờ
 qua_cu:hisCon({nam:Y,_luc:moc-1000},c),                    // lưu TRƯỚC nến thứ 260 của phần đang chạy: sẽ hở nến hoặc thiếu đoạn khởi động chỉ báo
 vua_du:hisCon({nam:Y,_luc:moc},c),
 nam_cu:hisCon({nam:Y-1,_luc:Date.now()},c),
 khong_nam:hisCon({_luc:Date.now()},c),
 vua_goi_may_chu:hisCon({nam:Y-1,_luc:0,_nap:Date.now()},c), // vừa gọi máy chủ xong thì luôn nhận, kẻo gọi lại mãi 4 MB mỗi 5 giây
 it_nen:hisCon({nam:Y,_luc:Date.now()},c.slice(0,60))};
console.log(JSON.stringify(ra));
"""


class NenCuLuu(unittest.TestCase):
    """Nến từ đầu năm (4 MB mỗi khung) không tải lại mỗi lần mở trang: đọc bản lưu trong trình duyệt, chỉ gọi máy chủ khi bản lưu quá cũ.
    Lỗi đã đo (26/11/2026): /api/gia đứng riêng 0,06 giây, chạy cùng /api/gia-cu hoặc /api/ma thì 0,34 tới 0,85 giây, có lần 4 giây."""

    def test_doc_ban_luu_truoc_khi_goi_may_chu(self):
        js = bieu_do.JS
        self.assertIn("let j=await hisLuu(u);if(j&&!(key===hisKhoa()&&D&&D.candles.length&&hisCon(j,D.candles)))j=null;", js)
        self.assertIn("khoGhi('so-nen-cu',8,u,r);j=await r.json();j._luc=j._nap=Date.now()}", js)
        self.assertIn("if(!hisCon(h,D.candles)){HISM.delete(hisKhoa());return}", js)   # trang mở lâu: bản trong bộ nhớ quá cũ thì bỏ, hisTai nạp lại
        self.assertIn("const u='/api/gia-cu?tf='+tf+(ma?'&ma='+encodeURIComponent(ma):'');", js)

    def test_danh_sach_ma_tai_sau_nen(self):
        """/api/ma tính xu hướng của gần trăm mã (0,3 giây): gọi sau khi nến đã vẽ, không chạy cùng lúc với /api/gia."""
        js = bieu_do.JS
        self.assertIn("const MA=$('#ma'),maTai=()=>fetch('/api/ma?gon=1',{cache:'no-store'})", js)
        self.assertIn("load().then(()=>{maTai();ai();", js)
        # lỗi đã gặp khi sửa: ghi chú // chèn giữa dòng nuốt mất phần dựng danh sách, ô chọn mã chỉ còn một dòng mà node --check vẫn qua
        self.assertIn("if(!j.san_sang||!j.ds.length)return;const nh={};for(const s of j.ds)(nh[s.nhom]=nh[s.nhom]||[]).push(s);", js)

    @unittest.skipUnless(shutil.which('node'), 'máy không có Node.js')
    def test_ban_luu_con_dung_duoc(self):
        m = re.search(r'const hisCon=\(h,c\)=>[^\n;]+;', bieu_do.JS)
        self.assertIsNotNone(m)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'con.js').write_text(CHAY_CON % m.group(0), encoding='utf-8')
            r = subprocess.run(['node', str(Path(d) / 'con.js')], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(r.returncode, 0, r.stderr[:400])
        self.assertEqual(json.loads(r.stdout), {'moi_luu': True, 'qua_cu': False, 'vua_du': True, 'nam_cu': False, 'khong_nam': True,
                                                'vua_goi_may_chu': True, 'it_nen': True})


class TenMa(unittest.TestCase):
    """Ô chọn mã chỉ cần tên các mã: /api/ma?gon=1 đọc MT5 một lần (đo được 1 ms). Bản đầy đủ /api/ma tính xu hướng, ATR, RSI cho từng mã
    (88 mã: gần 0,5 giây), và trong lúc đó mọi yêu cầu khác của webapp chậm theo vì các luồng Python chia nhau một bộ xử lý."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_da_ma import MT5Gia                                        # noqa: PLC0415
        from so_cong_khai import da_ma                                       # noqa: PLC0415
        self.da_ma, self.mt5, self.that = da_ma, MT5Gia(), da_ma._mt5
        da_ma._mt5 = lambda g: self.mt5
        da_ma._nho.clear()
        self.cfg = {'ten': 'Thử', 'gia': {'ma_vang': 'XAUUSDp'}}

    def tearDown(self):
        self.da_ma._mt5 = self.that
        self.da_ma._nho.clear()

    def test_chi_ten_khong_doc_nen(self):
        r = self.da_ma.ten_ma(self.cfg)
        self.assertTrue(r['san_sang'])
        self.assertEqual([x['ma'] for x in r['ds']], ['XAUUSDp', 'EURUSDp', 'BTCUSDTp'])     # cùng thứ tự với bản đầy đủ; mã không hiện thì không có
        self.assertEqual(r['ds'][1], {'ma': 'EURUSDp', 'ten': 'Euro vs US Dollar', 'nhom': 'Ngoại hối', 'so_le': 5, 'la_vang': False})
        self.assertEqual(self.mt5.goi, [])                                                    # không đọc cây nến nào

    def test_chua_noi_mt5(self):
        self.da_ma._mt5 = lambda g: None
        r = self.da_ma.ten_ma({'gia': {}})
        self.assertEqual((r['san_sang'], r['ds']), (False, []))
        self.assertTrue(r['ly_do'])

    def test_qua_may_chu(self):
        import threading                                                     # noqa: PLC0415
        import urllib.request                                                # noqa: PLC0415
        from so_cong_khai import tai_khoan_chart, web                         # noqa: PLC0415
        with tempfile.TemporaryDirectory() as tmp:
            cfgp = Path(tmp) / 'c.json'
            cfgp.write_text(json.dumps({**self.cfg, 'thu_muc_ra': str(Path(tmp) / 'out')}), encoding='utf-8')
            _, token = tai_khoan_chart.vao('chart-http-test', 'chart-test-password-1234', True, Path(tmp))
            srv = web.tao_may_chu(str(cfgp), port=0)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                request = urllib.request.Request(f'http://127.0.0.1:{srv.server_address[1]}/api/ma?gon=1',
                                                 headers={'Cookie': tai_khoan_chart.cookie_header(token).split(';')[0]})
                with urllib.request.urlopen(request, timeout=30) as r:
                    j = json.loads(r.read())
            finally:
                srv.shutdown()
                srv.server_close()
        self.assertEqual([x['ma'] for x in j['ds']], ['XAUUSDp', 'EURUSDp', 'BTCUSDTp'])
        self.assertNotIn('xu_huong', j['ds'][0])
        self.assertEqual(self.mt5.goi, [])

    def test_cac_o_chon_ma_dung_ban_gon(self):
        from so_cong_khai import bieu_do_them, da_khung_trang                # noqa: PLC0415
        self.assertIn("maTai=()=>fetch('/api/ma?gon=1',{cache:'no-store'})", bieu_do.JS)
        self.assertIn("fetch('/api/ma?gon=1',{cache:'no-store'})", da_khung_trang.trang_da_khung('Harry'))
        self.assertIn("fetch('/api/ma?gon=1',{cache:'no-store'})", bieu_do_them.JS)


if __name__ == '__main__':
    unittest.main()
