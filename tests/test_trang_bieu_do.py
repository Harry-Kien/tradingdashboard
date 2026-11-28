# -*- coding: utf-8 -*-
"""Trang biểu đồ không trôi khi mở (lỗi ngày 24/11/2026): phân tích tự chạy lúc mở trang không tự vẽ phương án lên biểu đồ (thang giá không bị kéo
giãn tới dừng lỗ và chốt lời), và thẻ tóm tắt điểm vào nằm DƯỚI vùng biểu đồ nên lúc nó hiện ra biểu đồ không bị đẩy xuống."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import bieu_do  # noqa: E402


class KhongTroi(unittest.TestCase):
    def test_mo_trang_chua_ve_phuong_an(self):
        self.assertRegex(bieu_do.JS, r'(?:^|[,;\s])planTat=1,ppChon=')       # chưa bấm thì chưa vẽ

    def test_the_tom_tat_nam_duoi_bieu_do(self):
        h = bieu_do.trang_bieu_do('Harry')
        self.assertLess(h.index('class="stage"'), h.index('id="dv"'))
        self.assertIsNone(re.search(r'id="dv"[^>]*>.*class="stage"', h, re.S))

    def test_toan_man_hinh_co_nut_an_phan_tren(self):
        h = bieu_do.trang_bieu_do('Harry')
        self.assertIn('id="gon-btn"', h)
        self.assertRegex(h, r'\.chartp\.max \.stage\{[^}]*min-height:\s*\d')   # phần trên dài cũng không ép biểu đồ còn vài pixel

    def test_toan_man_hinh_van_lan_chuot_thu_nho_duoc(self):
        """Lỗi đã gặp: ở Toàn màn hình Chrome không gửi sự kiện cuộn tới biểu đồ. Trình nghe thụ động ở window buộc gửi (kiểm thật: cong-cu/kiem_chuc_nang.py)."""
        self.assertIn("addEventListener('wheel',()=>{},{capture:true,passive:true})", bieu_do.trang_bieu_do('Harry'))

    def test_che_do_anh_khong_lo_tai_khoan(self):
        """Ảnh đăng lên kênh công khai: không vẽ lệnh của tài khoản và điểm vào của phương pháp khác; báo trình chụp khi đã vẽ xong."""
        h = bieu_do.trang_bieu_do('Harry')
        self.assertIn("const ANH=new URLSearchParams(location.search).get('anh')==='1'", h)
        self.assertIn('if(TK&&TK.san_sang&&on.lenh&&!ANH)', h)
        self.assertIn("if(PTR&&!ANH&&!gon){for(const q of ppNhom('tat')", h)
        self.assertIn("document.documentElement.dataset.anh=co?'san':'khong-thay'", h)

    def test_nhay_toi_lenh_khong_bi_keo_ve(self):
        """Lỗi đã gặp: lwToi đặt khung mới nhưng lwDraw đọc khung cũ (thư viện áp chậm một nhịp) rồi đặt ngược lại."""
        h = bieu_do.trang_bieu_do('Harry')
        self.assertIn('LW.cho={from:a-90,to:a+70}', h)
        self.assertIn('giu=moi?null:(LW.cho||ts.getVisibleLogicalRange())', h)
        self.assertIn('subscribeVisibleLogicalRangeChange(()=>{LW.cho=null;lwPhu()})', h)

    @unittest.skipUnless(__import__('shutil').which('node'), 'máy không có Node.js')
    def test_ma_js_hop_cu_phap_ca_hai_ngon_ngu(self):
        """Lỗi đã gặp (26/11/2026): chèn mã vào giữa một câu khai báo nhiều biến làm hỏng cú pháp, cả trang Biểu đồ không chạy mà mọi bài kiểm
        Python vẫn qua. Kiểm cú pháp mọi đoạn <script> của trang, bản tiếng Việt và bản đã dịch sang tiếng Anh, bằng `node --check`."""
        import subprocess                                                     # noqa: PLC0415
        import tempfile                                                       # noqa: PLC0415
        from so_cong_khai import dich                                         # noqa: PLC0415
        goc = bieu_do.trang_bieu_do('Harry')
        with tempfile.TemporaryDirectory() as d:
            for lang, h in (('vi', goc), ('en', dich.dich_html(goc, dich.tu_dien('en')))):
                for i, js in enumerate(re.findall(r'<script>(.*?)</script>', h, re.S)):
                    tep = Path(d) / f'{lang}{i}.js'
                    tep.write_text(js, encoding='utf-8')
                    r = subprocess.run(['node', '--check', str(tep)], capture_output=True, text=True, encoding='utf-8')
                    self.assertEqual(r.returncode, 0, f'{lang} đoạn {i}: {r.stderr[:400]}')

    def test_chi_bao_va_cong_cu_ve_them(self):
        """Bảy chỉ báo và ba công cụ vẽ thêm ngày 26/11/2026; chỉ báo nằm trong danh sách ghép với nến cũ (lỗi đã gặp: không có trong danh sách thì
        900 giá trị bị gán vào 900 nến CŨ NHẤT, đường chỉ báo nằm ngoài khung nhìn)."""
        h = bieu_do.trang_bieu_do('Harry')
        for k in ('ema200', 'st', 'ich', 'pv', 'macd', 'sto', 'atr'):
            self.assertIn(f'data-k="{k}"', h)
        for k in ('fibmr:[', 'chia:[', 'tngang:['):
            self.assertIn(k, h)
        ind = re.search(r"IND=\[([^\]]*)\]", h).group(1)
        for k in ('ema200', 'macd', 'macd_cot', 'stoch_k', 'atr14', 'st', 'st_chieu', 'ichi_span_a', 'ichi_chikou'):
            self.assertIn(f"'{k}'", ind)

    def test_nhan_canh_bao_3_khung_dich_duoc(self):
        from so_cong_khai import dich                                              # noqa: PLC0415
        self.assertIn("ba_khung:'3 TF'", dich.dich_html(bieu_do.trang_bieu_do('Harry'), dich.tu_dien('en')))


if __name__ == '__main__':
    unittest.main()


class CotPhai(unittest.TestCase):
    """Cột phải (25/11/2026): dải tài khoản cố định đứng đầu, thẻ chuyển giữa Cảnh báo · Lệnh · Nhật ký · Tính lot, cảnh báo gộp trùng."""

    def test_bo_cuc(self):
        h = bieu_do.trang_bieu_do('Harry')
        col = h[h.index('class="col"'):]
        self.assertLess(col.index('id="tkt"'), col.index('id="pt"'))
        self.assertLess(col.index('class="ctab"'), col.index('id="cb"'))
        for t in ('cb', 'tk', 'nk', 'rk'):
            self.assertIn(f'data-t="{t}" id="{t}"', col)
            self.assertIn(f'.col[data-tab={t}] .tabp:not([data-t={t}])', h)
        self.assertNotIn('class="panel side tabp" data-t="side"', col)        # tóm tắt luật vẫn luôn hiện

    def test_khong_trong_duoi_bieu_do(self):
        """26/11/2026: dưới biểu đồ từng trống ~1500 px vì cột phải dài hơn nhiều. AI, lối tắt, COT nằm dưới biểu đồ; cột phải dính màn hình và tự cuộn."""
        h = bieu_do.trang_bieu_do('Harry')
        trai, duoi, col = h.index('class="trai"'), h.index('class="duoi"'), h.index('class="col"')
        self.assertLess(trai, h.index('id="cp"'))
        self.assertLess(h.index('class="stage"'), duoi)
        for i in ('ai', 'lt', 'cot'):
            self.assertTrue(duoi < h.index(f'id="{i}"') < col, i)
        self.assertRegex(h, r'\.desk>\.col\{position:sticky;[^}]*overflow-y:auto')
        self.assertIn('.desk>.col>.tkt{top:0}', h)                           # dải tài khoản dính đỉnh cột chứ không lệch 64 px
        self.assertIn('.trai{display:contents}.duoi{order:1}', h)             # điện thoại: thứ tự cũ, AI và COT ở cuối
        self.assertIn("a.dataset.lt+'?ma='", h)                               # lối tắt mang theo mã đang xem

    def test_doi_khung_khong_troi(self):
        """26/11/2026: đổi khung lúc lần tải tự động đang chạy thì nến của khung cũ về muộn đè lên khung mới; biểu đồ giữ vùng nhìn theo số thứ tự
        nến của khung kia nên trôi về tháng 1, nến nằm ngoài khung hình. Phản hồi cũ phải bị bỏ, khóa vùng nhìn theo khung của dữ liệu, và đổi
        mã/khung thì thang giá tự co lại."""
        js = bieu_do.JS
        self.assertIn('const t0=tf,m0=ma,cu=()=>!loadGate.current(ticket)||t0!==tf||m0!==ma;', js)
        self.assertIn("const j=JSON.parse(txt);if(cu())return;if(window.BDPL&&BDPL.chan){xong();delete $('.stage').dataset.tai;return}", js)   # đang phát lại nến: bỏ kết quả về muộn
        self.assertIn('xong();apD(j,keep||daVe,0)', js)
        self.assertIn('function apD(j,keep,tam){D=j;', js)
        self.assertIn("catch(e){if(cu()||e.name==='AbortError')return;xong();$('#err')", js)
        self.assertIn("if(!cu())$('.stage').dataset.doi=daVe?'Đang cập nhật nến…':'Đang tải dữ liệu nến…'},350)", js)   # đổi mã lần đầu MT5 tải lịch sử vài giây: báo đang tải, không che nến
        self.assertIn('.stage[data-doi]::before{content:attr(data-doi);', bieu_do.trang_bieu_do('Harry'))   # chữ lấy từ JS nên bộ dịch dịch được
        self.assertIn("+'|'+(D.tf||tf),moi=key!==LW.key", js)
        self.assertIn('if(moi||LW.veMoi){LW.key=key;lwNay()}else if(xem)ts.setVisibleLogicalRange(xem)', js)

    def test_doi_khung_tuc_thi(self):
        """27/11/2026: người dùng bấm khung khác thì biểu đồ đứng ở khung cũ, nhãn "Đang tải" (máy chủ bận phân tích thì /api/gia có lúc 2–3 giây).
        Nến từng khung được nhớ bằng chữ JSON gốc (phần áp dữ liệu sửa D tại chỗ); rê chuột tới nút là nạp trước; sau lần tải đầu nạp ngầm các khung chính.
        Khung đã nhớ vẽ ngay, bản mới đè lên với keep để giữ chỗ đang xem; bản tạm không nạp lịch sử, tài khoản lần hai."""
        js = bieu_do.JS
        self.assertIn("if(!keep&&!ANH){const o=NHO.get(u);if(o&&Date.now()-o.luc<NHO_HAN){try{apD(JSON.parse(o.txt),0,1);daVe=true}catch(e){}}}", js)
        self.assertIn('let txt=NHO_DANG.has(u)?await NHO_DANG.get(u):null;if(cu())return;', js)            # lượt nạp trước đang chạy thì dùng luôn
        self.assertIn('txt=await r.text();if(cu())return;nhoGhi(u,txt)}', js)
        self.assertIn("if(!tam){hisTai();tkTai();setTimeout(napNgam,2500);if(!PTR_GOC)ptTai(1)}", js)
        self.assertIn("e.target.closest('.seg.tf button[data-tf]');if(b&&b.dataset.tf!==tf)napTruoc(b.dataset.tf)", js)
        self.assertIn('while(NHO.size>16)', js)                                                            # bộ nhớ có giới hạn

    @unittest.skipUnless(__import__('shutil').which('node'), 'máy không có Node.js')
    def test_the_diem_vao_ghi_gio_tin_hieu(self):
        """27/11/2026: lệnh chờ cách xa giá trông như phân tích cũ bị giữ lại; thẻ ghi tín hiệu lúc nào và lệnh chờ còn bao lâu."""
        import json
        import subprocess
        js = bieu_do.JS
        self.assertIn("<small>${esc(p.kieu||'')}</small>${plTg(p)}</div>", js)
        src = js[js.index('function plTg'):js.index('const PH_TT={')]
        chay = ("const esc=x=>String(x),vn=t=>new Date(t*1000).toISOString().slice(11,16);" + src +
                "const n=Date.UTC(2026,10,27,16,50);Date.now=()=>n;const iso=m=>new Date(n+m*60000).toISOString();"
                "console.log(JSON.stringify([plTg({loai_vao:'gh',thuc_thi:{tu:iso(-50),het:iso(190)}}),plTg({loai_vao:'tt',nen:iso(-3),thuc_thi:{het:iso(2)}}),"
                "plTg({loai_vao:'gh',thuc_thi:{tu:iso(-300),het:iso(-60)}}),plTg({})]))")
        r = subprocess.run(['node', '-e', chay], capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        a, b, c, d = json.loads(r.stdout)
        self.assertIn('Tín hiệu lúc 16:00 · còn 3 giờ 10 phút', a)
        self.assertIn('>Tín hiệu lúc 16:47</small>', b)                         # vào ngay: không đếm ngược
        self.assertIn('>Tín hiệu lúc 11:50</small>', c)                         # đã hết hạn: không ghi "còn"
        self.assertEqual(d, '')

    def test_doi_khung_ve_nen_moi_nhat(self):
        """Yêu cầu 27/11: đổi khung tự về nến mới nhất, bỏ tâm lịch sử và thang giá kéo tay."""
        js = bieu_do.JS
        self.assertIn("addEventListener('click',()=>{if(tf===b.dataset.tf)return;tf=b.dataset.tf;chartSwitch();", js)
        self.assertNotIn('lwTam', js)
        self.assertIn("if(AP)AP.addEventListener('click',()=>{lwNay();apVe()})", js)
        self.assertIn('title="Về nến mới nhất và tự co thang giá"', bieu_do.trang_bieu_do('Harry'))

    def test_keo_doc_bieu_do(self):
        """26/11/2026: giữ chuột kéo lên xuống trong vùng nến dời thang giá (như TradingView); chỉ chuột trái, chế độ chọn, không trúng hình vẽ,
        không trên trục giá; nút Tự co giá bật lại; về nến mới nhất đặt lại cả hai trục."""
        js = bieu_do.JS
        self.assertIn("e.button!==0||e.pointerType==='touch'||VE.cong!=='tro'||VE.keo)return", js)
        self.assertIn('LW.nen.priceScale().setVisibleRange({from:KD.v.from+d,to:KD.v.to+d})', js)
        self.assertIn('if(!KD.dang&&Math.abs(dy)<6)return', js)
        self.assertIn('id="tu-co" hidden', bieu_do.trang_bieu_do('Harry'))
        self.assertIn('try{LW.nen.priceScale().applyOptions({autoScale:true})}', js)

    def test_nhan_khung_chi_bao_phu(self):
        """27/11/2026: mỗi khung chỉ báo phụ (RSI, MACD, Stochastic, ATR) có nhãn tên, giá trị, nút "?" giải thích và nút "✕" ẩn khung đó."""
        js = bieu_do.JS
        for ten in ("rsi:['RSI 14'", "macd:['MACD 12 26 9'", "sto:['Stochastic 14 3'", "atr:['ATR 14'"):
            self.assertIn(ten, js)
        self.assertIn("const k=i?ks[i-1]:null", js)                                  # khung thứ i+1 ứng với chỉ báo thứ i của LW.khDao
        self.assertIn("if(b.dataset.an){const k=b.dataset.an;on[k]=0;mo='';luu();boVe();draw()", js)
        self.assertIn('if(window.KHN)requestAnimationFrame(', js)
        self.assertIn('@media(max-width:640px){.khn button{width:26px;height:26px}}', bieu_do.trang_bieu_do('Harry'))

    def test_nut_an_phan_tich(self):
        """26/11/2026: nút Ẩn phân tích ở hàng công cụ chính (thấy cả khi toàn màn hình thu gọn), phím B, nhãn trên biểu đồ khi đang ẩn;
        xin phân tích (nút, phím A, Vẽ lên biểu đồ) thì tự thoát biểu đồ trống."""
        h = bieu_do.trang_bieu_do('Harry')
        hang1 = h[h.index('<div class="tools">'):h.index('<div class="tools t2">')]
        self.assertIn('id="an-pt"', hang1)
        self.assertIn('id="trong-nhan"', h[h.index('class="stage"'):h.index('id="dv"')])
        js = bieu_do.JS
        self.assertIn("else if(k==='b'||k==='B')datTrong(!TRONG)", js)
        self.assertIn("closest('#pt-btn,.vph,button.ve[data-i],.dvv'))datTrong(false)", js)
        self.assertIn("a.setAttribute('aria-label',TRONG?'Hiện phân tích':'Ẩn phân tích')", js)

    def test_ma_js(self):
        js = bieu_do.JS
        for must in ('function tktVe', 'TK.rui_ro', 'so-ctab', 'cbNhom', 'MIEN', "x.phieu.ma===ma"):
            self.assertIn(must, js)
