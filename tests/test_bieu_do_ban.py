# -*- coding: utf-8 -*-
"""Bố cục "bàn giao dịch" của trang Biểu đồ (27/11/2026): trên máy tính trang kín cả màn hình và không cuộn, bảng phải gập được, các ô dưới biểu đồ
thành một ngăn gập. Toàn bộ CSS và JS nằm ở so_cong_khai/bieu_do_ban.py; ngoài mốc 981×600 trang giữ bố cục cũ.
Bài kiểm ở đây chỉ soát phần dựng trang (không cần trình duyệt); đo thật bằng cong-cu/kiem_giao_dien.py."""
import json
import re
import sys
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
from so_cong_khai import (bieu_do, bieu_do_ban, do_sau, hieu_suat_trang, ke_hoach_trang, kiem_lenh_trang, kiem_tin_hieu_trang, ky_luat_trang,  # noqa: E402
                          nhat_ky_trang, thi_truong_trang, trang)

MOC = '@media(min-width:981px) and (min-height:600px)'


class BanGiaoDich(unittest.TestCase):
    def setUp(self):
        self.h = bieu_do.trang_bieu_do('Harry')

    def test_trang_co_khoi_ban(self):
        for s in (MOC, 'so-ban-phai', 'so-ban-ngan', 'so-ban-dv', 'ngan-tab', 'phai-btn', 'dv-btn'):
            self.assertIn(s, self.h)

    def test_khoi_ban_nam_cuoi_style(self):
        """CSS bàn giao dịch phải đứng sau mọi khối CSS khác của trang thì mới thắng luật cũ."""
        self.assertGreater(self.h.index(bieu_do_ban.CSS), self.h.index(do_sau.CSS))
        self.assertLess(self.h.index(bieu_do_ban.CSS), self.h.index('</style></head>'))

    def test_js_ban_nam_sau_js_chinh(self):
        self.assertGreater(self.h.index(bieu_do_ban.JS), self.h.index(bieu_do.JS))

    def test_khong_dung_ham_rieng_cua_js_chinh(self):
        """Mô-đun chỉ quan sát DOM, để phiên khác sửa JS chính không làm hỏng bố cục."""
        self.assertNotIn('BDMN', bieu_do_ban.JS)

    def test_nen_co_muc_toi_thieu(self):
        self.assertRegex(bieu_do_ban.CSS, r'\.stage\{[^}]*min-height:320px')
        self.assertRegex(bieu_do_ban.CSS, r'\.stage\{[^}]*min-height:200px')

    def test_ngoai_moc_khong_doi_gi(self):
        """Mọi luật bố cục nằm trong mốc; ngoài mốc chỉ có luật ẩn nút và dải thẻ mới."""
        ngoai = re.sub(r'@media\([^{]*\)\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}', '', bieu_do_ban.CSS)
        self.assertNotIn('.desk', ngoai)
        self.assertNotIn('.stage', ngoai)
        self.assertNotIn('main', ngoai)
        self.assertIn('#phai-btn', ngoai)

    def test_luu_tru_bi_chan_van_chay(self):
        """Mọi lần đụng localStorage đều nằm trong try."""
        for m in re.finditer(r'localStorage', bieu_do_ban.JS):
            self.assertIn('try{', bieu_do_ban.JS[max(0, m.start() - 12):m.start()])

    def test_cham_canh_bao_theo_so_dem(self):
        """Lỗi soát mã 27/11: #cb-moi luôn `hidden` khi thẻ Cảnh báo đang chọn (mặc định), nên chấm trên nút Bảng phải phải theo SỐ đếm."""
        self.assertIn('pm.hidden=!n', bieu_do_ban.JS)
        self.assertNotIn('pm.hidden=cm.hidden', bieu_do_ban.JS)

    def test_the_ai_an_o_ma_khac_vang(self):
        """body[data-khac] ẩn #ai bằng CSS (luật id thắng ngăn dưới): thẻ AI không được hiện khi đang xem mã khác vàng."""
        self.assertIn("o.id==='ai'&&document.body.hasAttribute('data-khac')", bieu_do_ban.JS)
        self.assertIn("attributeFilter:['data-khac']", bieu_do_ban.JS)

    def test_toan_man_hinh_an_nut_bang_phai(self):
        self.assertIn(':root .chartp.max #phai-btn{display:none}', bieu_do_ban.CSS)

    def test_doi_the_cung_gia_tri_van_mo_bang(self):
        """Menu chuột phải đưa SL sang Tính lot khi thẻ Tính lot đã chọn sẵn: vẫn phải mở bảng."""
        self.assertNotIn('m.oldValue!==col.dataset.tab', bieu_do_ban.JS)

    def test_thoat_toan_man_hinh_khong_giau_phan_tich(self):
        self.assertIn("attributeFilter:['class']", bieu_do_ban.JS)

    def test_dai_the_giu_tieu_diem_va_khong_dung_lai_thua(self):
        """Soát mã 27/11: dựng lại dải thẻ mỗi lần COT ghi `hidden` làm mất tiêu điểm bàn phím; thẻ nhớ của ô chèn sau không tự bung."""
        self.assertIn('if(k===ky)return;', bieu_do_ban.JS)
        self.assertIn('if(b)b.focus()', bieu_do_ban.JS)
        self.assertIn("e.key!=='ArrowLeft'", bieu_do_ban.JS)
        self.assertIn("ve();if(mo&&!cacO().some(o=>o.id===mo&&!anO(o))){mo='';ve()}", bieu_do_ban.JS)

    def test_tu_mo_bang_thi_cuon_toi_ket_qua(self):
        self.assertIn("scrollIntoView({block:'nearest'})", bieu_do_ban.JS)

    def test_nhan_moi_da_dich(self):
        d = json.loads((GOC / 'so_cong_khai' / 'dich' / 'en.json').read_text(encoding='utf-8'))
        for s in ('Bảng phải', 'AI phân tích', 'Làm tiếp', 'Cảnh báo đường vẽ', 'Độ sâu', 'Ẩn hoặc hiện bảng bên phải', 'Các ô dưới biểu đồ',
                  'Mở hoặc gập ngăn dưới', 'Thẻ điểm vào', 'Ẩn hoặc hiện thẻ điểm vào dưới biểu đồ'):
            self.assertIn(s, d)
            self.assertIn("'" + s + "'", bieu_do_ban.JS)      # đứng riêng một chuỗi thì bộ dịch mới thay được


class HaiTrangBieuDoKia(unittest.TestCase):
    """Nhiều biểu đồ và Renko: trên máy tính đầu trang gọn một hàng, biểu đồ cao theo cửa sổ (100dvh), đoạn mô tả thu vào nút "i"."""

    def test_da_khung(self):
        from so_cong_khai import da_khung_trang                        # noqa: PLC0415
        h = da_khung_trang.trang_da_khung('Harry')
        self.assertIn(MOC, da_khung_trang.CSS)
        self.assertRegex(da_khung_trang.CSS.split(MOC)[1], r'\.dk-luoi\{height:calc\(100dvh')
        self.assertRegex(h, r'<span class="dk-i" tabindex="0"[^>]*aria-describedby="dk-gt">i</span><p id="dk-gt">')   # trình đọc màn hình đọc được mô tả

    def test_renko(self):
        from so_cong_khai import renko_trang                           # noqa: PLC0415
        h = renko_trang.trang_renko('Harry')
        self.assertIn(MOC, renko_trang.CSS)
        self.assertRegex(renko_trang.CSS.split(MOC)[1], r'#rk-cv\{height:calc\(100dvh')
        self.assertRegex(h, r'<span class="rk-i" tabindex="0"[^>]*aria-describedby="rk-gt">i</span><p id="rk-gt">')


class ChieuRongChung(unittest.TestCase):
    def test_chieu_rong_chung(self):
        self.assertIn('main{max-width:1560px}', trang.CSS)
        self.assertIn('.nv-in{max-width:1560px', trang.CSS)
        self.assertIn('main .note,main p.why,main p.sub{max-width:100ch}', trang.CSS)       # trang rộng hơn nhưng dòng chữ không dài quá ~100 ký tự
        self.assertNotIn('main{max-width:1520px}', bieu_do.CSS)
        self.assertNotRegex(trang.CSS, r'(?:\.bar>div|\.subnav>div|\.gsr)\{max-width:(?:1240|1520)px')
        for m in (nhat_ky_trang, thi_truong_trang, hieu_suat_trang, ke_hoach_trang, kiem_lenh_trang, kiem_tin_hieu_trang, ky_luat_trang):
            self.assertRegex(m.CSS, r'main(?:\.rong)?\{max-width:1560px', m.__name__)


if __name__ == '__main__':
    unittest.main()
