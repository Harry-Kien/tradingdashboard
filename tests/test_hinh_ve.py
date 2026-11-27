"""Lưu hình vẽ trên máy chủ (hinh_ve.py): đọc, ghi, phiên bản, kiểm đầu vào, chặn đường dẫn lạ; trang Biểu đồ có lớp đồng bộ."""
import tempfile
import unittest
from pathlib import Path

from so_cong_khai import hinh_ve


class HinhVeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.goc = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_doc_ghi_va_phien_ban(self):
        self.assertEqual(hinh_ve.doc('XAU', self.goc), {'ds': [], 'ban': None, 'luc': None})
        ds = [{'id': 'a1', 'k': 'xu', 'a': {'t': 1, 'p': 2}, 'b': {'t': 3, 'p': 4}}]
        self.assertEqual(hinh_ve.luu('XAU', ds, self.goc, now=10)['ban'], 1)
        self.assertEqual(hinh_ve.luu('XAU', ds + [{'id': 'b2', 'k': 'ngang', 'a': {'t': 1, 'p': 5}}], self.goc, now=11)['ban'], 2)
        x = hinh_ve.doc('XAU', self.goc)
        self.assertEqual((x['ban'], len(x['ds']), x['luc']), (2, 2, 11))
        self.assertEqual(hinh_ve.doc('EURUSDp', self.goc)['ban'], None)           # mỗi mã một tệp

    def test_giu_ban_con_hinh_gan_nhat(self):
        """Lỡ xóa hết (hay kịch bản thử xóa bộ nhớ trình duyệt): bản còn hình gần nhất nằm ở <mã>.truoc.json; ghi bản rỗng lần nữa không đè lên nó."""
        ds = [{'id': f'h{i}', 'k': 'ngang', 'a': {'t': 1, 'p': i}} for i in range(6)]
        hinh_ve.luu('XAU', ds, self.goc)
        hinh_ve.luu('XAU', [], self.goc)
        hinh_ve.luu('XAU', [], self.goc)
        import json
        truoc = json.loads((self.goc / 'du-lieu' / 'hinh-ve' / 'XAU.truoc.json').read_text(encoding='utf-8'))
        self.assertEqual(len(truoc['ds']), 6)
        self.assertTrue("!sent.length&&n0>=5&&!daHoi&&!confirm(" in hinh_ve.JS)
        self.assertIn('const daHoi=window.HVD_DA_HOI===true;window.HVD_DA_HOI=false;', hinh_ve.JS)   # cờ dùng một lần

    def test_tu_choi(self):
        for ma in ('', '..', 'a/b', '..\\x', 'x' * 41):
            with self.subTest(ma=ma), self.assertRaises(ValueError):
                hinh_ve.luu(ma, [], self.goc)
        for ds in ({'id': 'a'}, [1], [{'k': 'xu'}], [{'id': 'a', 'k': 'xu'}] * (hinh_ve.TOI_DA_HINH + 1),
                   [{'id': 'a', 'k': '<img src=x onerror=alert(1)>'}], [{'id': '"><script>', 'k': 'xu'}],         # chặn chèn HTML (stored XSS)
                   [{'id': 'a', 'k': 'xu', 'mau': 'red;background:url(x)'}],
                   [{'id': 'a', 'k': 'chu', 'chu': 'x' * (hinh_ve.TOI_DA_BYTE + 10)}]):
            with self.assertRaises(ValueError):
                hinh_ve.luu('XAU', ds, self.goc)
        self.assertFalse((self.goc / 'du-lieu' / 'hinh-ve' / 'XAU.json').exists())

    def test_trang_co_lop_dong_bo(self):
        from so_cong_khai import bieu_do
        h = bieu_do.trang_bieu_do('Harry')
        self.assertIn('window.HVD=', h)
        self.assertIn("'so-ve:'+(g.ma||'XAU')", hinh_ve.JS)                      # cùng khóa với công cụ vẽ (veKhoa)
        self.assertIn("veKhoa=()=>(window.PHAT_LAI?'so-ve-luyen:':'')", bieu_do.JS)  # nháp replay có khóa riêng
        self.assertTrue("g.VE.keo||g.VE.tam||document.querySelector('.venhap,.mnp,.cbv-nen')" in hinh_ve.JS)
        self.assertTrue('window.HVD_MERGE=merge' in hinh_ve.JS)
        self.assertTrue('ban_co_so:' in hinh_ve.JS)
        self.assertTrue('s.timer&&s.sig===sig' in hinh_ve.JS)                  # cùng nội dung không hẹn lại vô hạn


NODE_KHUNG = r"""
const ls={},goi=[],hen=[];let lapLai=[];
globalThis.localStorage={getItem:k=>k in ls?ls[k]:null,setItem:(k,v)=>{ls[k]=String(v)}};
globalThis.setInterval=f=>{lapLai.push(f)};globalThis.setTimeout=(f)=>{hen.push(f);return hen.length};globalThis.clearTimeout=()=>{};
globalThis.addEventListener=()=>{};globalThis.document={visibilityState:'visible',querySelector:()=>null};globalThis.confirm=()=>false;
const VE={ds:[],keo:null,tam:null};
globalThis.window=globalThis;window.BDMN=()=>({ma:'',VE,veTb(){},lwPhu(){}});
const MAY={ds:SERVER,ban:3};
globalThis.fetch=async(u,o)=>{goi.push([u,o&&o.method,o&&o.body]);if(o&&o.method==='POST'){const b=JSON.parse(o.body);MAY.ds=b.ds;MAY.ban++;return{ok:true,json:async()=>({ok:true,ban:MAY.ban})}}
 return{ok:true,json:async()=>({ds:MAY.ds,ban:MAY.ban})}};
ls['so-ve:XAU']=JSON.stringify(LOCAL);if(SNAPV!==null)ls['so-ve-dong:XAU']=JSON.stringify(SNAPV);
const cho=()=>new Promise(r=>setImmediate(r));
(async()=>{JS_HVD
 for(let i=0;i<3;i++){for(const f of lapLai)f();await cho();await cho();for(const f of hen.splice(0))f();await cho();await cho()}
 console.log(JSON.stringify({local:JSON.parse(ls['so-ve:XAU']),may:MAY.ds,post:goi.filter(x=>x[1]==='POST').length}))})();
"""


@unittest.skipUnless(__import__('shutil').which('node'), 'máy không có Node.js')
class DongBoJsTest(unittest.TestCase):
    """27/11/2026: lớp đồng bộ không được nạp đè nét vẽ chưa gửi (tải lại trang ngay sau khi vẽ, hay lần gửi trước bị hỏng)."""

    def chay(self, local, server, snap):
        import json
        import subprocess
        import tempfile
        js = (NODE_KHUNG.replace('SERVER', json.dumps(server)).replace('LOCAL', json.dumps(local)).replace('SNAPV', json.dumps(snap))
              .replace('JS_HVD', hinh_ve.JS))
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(js)
        r = subprocess.run(['node', f.name], capture_output=True, text=True, encoding='utf-8', timeout=60)
        Path(f.name).unlink()
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    A, B = {'id': 'a', 'k': 'ngang'}, {'id': 'b', 'k': 'xu'}

    def test_net_ve_chua_gui_duoc_giu_va_gui_len(self):
        kq = self.chay([self.A, self.B], [self.A], [self.A])            # đã đồng bộ [A], vẽ thêm B rồi tải lại trước khi kịp gửi
        self.assertEqual((kq['local'], kq['may'], kq['post']), ([self.A, self.B], [self.A, self.B], 1))

    def test_ban_moi_tu_may_khac_van_duoc_nap(self):
        kq = self.chay([self.A], [self.A, self.B], [self.A])            # máy này không sửa gì; máy khác vừa thêm B
        self.assertEqual((kq['local'], kq['post']), ([self.A, self.B], 0))


if __name__ == '__main__':
    unittest.main()
