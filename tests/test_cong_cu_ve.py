# -*- coding: utf-8 -*-
"""Các lỗi công cụ vẽ phiên kiểm thử tìm ra ngày 26/11/2026 (Playwright ở 1440x900, 1366x768, 390x844 cảm ứng). Mỗi bài giữ một bản sửa."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import bieu_do  # noqa: E402

JS, CSS = bieu_do.JS, bieu_do.CSS


class CongCuVe(unittest.TestCase):
    def test_thanh_cong_cu_khong_tran(self):
        """Lỗi: ở 1440x900 thanh cao 553px trong khi biểu đồ 505px, các nút cuối bị che."""
        self.assertIn('.vetb{max-height:calc(100% - 38px);overflow-x:hidden;overflow-y:auto', CSS)

    def test_thuoc_do_dem_theo_chi_so_nen(self):
        """Lỗi: đo 10 nến M15 vắt qua cuối tuần ra "206 nến" (đếm theo giờ đồng hồ)."""
        self.assertIn("Math.round(Math.abs(ix(b.t)-ix(a.t)))+' nến · '", JS)
        self.assertNotIn('Math.abs(b.t-a.t)/dt', JS)

    def test_fib_thoi_gian_theo_chi_so_nen(self):
        """Lỗi: qua khoảng nghỉ cuối tuần các đường 6, 10, 16 dồn về một chỗ."""
        self.assertIn('ts.logicalToCoordinate(ia+u*f)', JS)
        self.assertNotIn('vx(h.a.t+u*f)', JS)

    def test_cam_ung_keo_hinh(self):
        """Lỗi: trên cảm ứng, kéo hình bị pointercancel, trang cuộn mà hình đứng yên và VE.keo không được xóa."""
        self.assertIn("for(const ev of['pointerup','pointercancel'])addEventListener(ev,()=>{if(VE.keo&&!VE.keo.moi)", JS)
        self.assertIn("LWE.style.touchAction=VE.chon?'none':''", JS)

    def test_vi_the_sl_khong_vuot_diem_vao(self):
        """Lỗi: kéo SL của lệnh MUA lên trên điểm vào thì nhãn thành BÁN mà TP vẫn ở trên."""
        self.assertIn("h[k.nut]=g[k.nut]>g.a.p?Math.max(v,h.a.p+e):Math.min(v,h.a.p-e)", JS)

    def test_bam_dup_trung_hinh_khong_nhay(self):
        self.assertIn("LWE.addEventListener('dblclick',e=>{if(window.MNP&&MNP.dbl&&MNP.dbl(e))return;lwNay()})", JS)

    def test_lam_lai(self):
        for must in ('function veLam()', "lam:['Làm lại (Ctrl+Y)'", "(k==='lam'&&!VE.lai.length)", 'VE.lai=[]}'):
            self.assertIn(must, JS)

    def test_delete_khong_xoa_hinh_khoa(self):
        self.assertIn("&&VE.chon&&!(VE.ds.find(x=>x.id===VE.chon)||{}).khoa){", JS)

    def test_nhan_fib_gon(self):
        """23,6% chứ không 23,60%."""
        self.assertNotIn("f2(f*100).replace(',00','')", JS)
        self.assertIn("vePct=f=>(+(f*100).toFixed(1))", JS)

    def test_muoi_hai_cong_cu_them(self):
        """26/11/2026: kênh/vòng/cung Fibonacci, quạt và hộp Gann, đo giá/thời gian/vùng, đường cong, đầu vai, ba đỉnh, tam giác mẫu hình.
        Mỗi công cụ phải có nút (VEC) và nhánh vẽ (veVe); tên loại khớp bộ lọc của máy chủ lưu hình."""
        import re                                                             # noqa: PLC0415
        for k in ('fibk', 'fibvong', 'fibcung', 'gannq', 'gannh', 'dogia', 'dotg', 'dovung', 'cong', 'dauvai', 'badinh', 'tamgm'):
            self.assertIn(k + ":['", JS, k)
            self.assertRegex(k, r'^[a-z0-9_]{1,20}$')
        for k in ('fibk', 'fibvong', 'gannq', 'gannh', 'dogia', 'cong'):
            self.assertIn(f"h.k==='{k}'", JS)
        self.assertIn('dauvai:7,badinh:7,tamgm:4', JS)
        self.assertTrue(re.search(r"\(c==='kenh'\|\|c==='fibk'\)\?\{id,k:c,a:q,b:\{\.\.\.q\},d:0\}", JS))

    def test_doi_ma_ve_lai_lop_phu(self):
        self.assertIn('dvVe();veDoc();veTb();lwPhu();history.replaceState', JS)


if __name__ == '__main__':
    unittest.main()
