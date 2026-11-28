# -*- coding: utf-8 -*-
"""Đợt 0 của đề xuất "AI phân tích chart có dẫn chứng": nhãn "còn hiệu lực"/"đặt được lúc này" chỉ hiện khi phân tích còn mới VÀ tài khoản
không đang dừng. Chạy đúng khối mã của trang Biểu đồ trong Node với DOM giả; không có Node thì bỏ qua phần đó."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from so_cong_khai import bieu_do, trang

NODE = shutil.which('node')
VO = r"""
const noop=()=>{},el=()=>({className:'',textContent:'',hidden:true,setAttribute:noop,before:noop,after:noop});
globalThis.document={createElement:el,querySelector:s=>s==='#pt-source-mode'?null:el(),getElementById:()=>el(),addEventListener:noop,head:{insertAdjacentHTML:noop}};
const $=s=>document.querySelector(s);
globalThis.window=globalThis;globalThis.addEventListener=noop;globalThis.setInterval=noop;globalThis.matchMedia=()=>({matches:false});
let PTR=null,plan=null,tf='H4',ve=0;const PTB={hidden:true},ptVe=noop,dvVe=()=>{ve++},draw=noop;
"""


def _khoi() -> str:
    js = bieu_do.JS
    a = js.index('// --- Đợt 0:')
    return js[a:js.index('let ptDang=0,ptCho=0,ptLan=0;', a)]


class MaTrang(unittest.TestCase):
    def test_moc(self):
        js = bieu_do.JS
        self.assertIn('PTR_GOC=j;j._nhan=Date.now();ptLoi=0;ptApDung();', js)
        self.assertIn('catch(e){if(epoch0===chartEpoch){ptLoi++;ptDoi();', js)
        self.assertIn('AbortSignal.timeout(20000)', js)                       # phân tích treo không giữ ptDang mãi
        self.assertEqual(js.count("tk_dung:['xau','Đủ điều kiện kỹ thuật · tài khoản đang dừng']"), 2)
        self.assertIn("dispatchEvent(new Event('gsr'))", trang.GIAM_SAT)       # băng giám sát báo trạng thái cho trang Biểu đồ
        self.assertNotIn('rk.sl*100', js)                                     # tab Tính lot không còn hằng số 100 ounce
        self.assertIn("fetch('/api/thi-truong'", js)


@unittest.skipUnless(NODE, 'không có Node')
class NhanTrangThai(unittest.TestCase):
    def chay(self, kich_ban: str) -> dict:
        js = VO + _khoi() + r"""
const mau=()=>({luc:new Date().toISOString(),het:new Date().toISOString(),nguon:'mt5',con_hieu_luc:1,
  phuong_phap:[{ma:'fib',co:true,hieu_luc:true,vi_sao_het:[],phieu:{ma:'fib',trang_thai:'con_hieu_luc'}},{ma:'ict',co:false,hieu_luc:false}],
  phuong_an:[{ma:'bot:nen',co:true,hieu_luc:true}]});
const nap=()=>{PTR_GOC=mau();PTR_GOC._nhan=Date.now();ptLoi=0;window.GSR=null;ptApDung()};
const tom=()=>({tt:ptTT,hl:PTR.phuong_phap[0].hieu_luc,phieu:PTR.phuong_phap[0].phieu.trang_thai,bot:PTR.phuong_an[0].hieu_luc,dem:PTR.con_hieu_luc,
  ly:(PTR.phuong_phap[0].vi_sao_het||[])[0]||'',goc:PTR===PTR_GOC,khung:PTK.textContent});
const r={};""" + kich_ban + "\nprocess.stdout.write(JSON.stringify(r));"
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 't.js').write_text(js, encoding='utf-8')
            p = subprocess.run([NODE, str(Path(d) / 't.js')], capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr[-2000:])
        return json.loads(p.stdout)

    def test_moi_thi_giu_nguyen(self):
        r = self.chay("nap();ptKhung();r.a=tom();")['a']
        self.assertEqual((r['tt'], r['hl'], r['phieu'], r['goc']), ('', True, 'con_hieu_luc', True))
        self.assertIn('bạn đang xem H4', r['khung'])                           # khung xem khác M15 thì luôn ghi rõ

    def test_loi_hai_lan_thi_ha_nhan(self):
        r = self.chay("nap();ptLoi=1;ptDoi();r.mot=tom();ptLoi=2;ptDoi();r.hai=tom();r.ve=ve;")
        self.assertEqual((r['mot']['tt'], r['mot']['hl']), ('', True))         # một lần lỗi lẻ chưa hạ
        h = r['hai']
        self.assertEqual((h['tt'], h['hl'], h['phieu'], h['bot'], h['dem']), ('cu', False, 'chua_cap_nhat', False, 0))
        self.assertIn('Chưa cập nhật được phân tích', h['ly'])
        self.assertIn('Chưa cập nhật được', h['khung'])
        self.assertEqual(r['ve'], 1)                                          # vẽ lại đúng một lần khi trạng thái đổi

    def test_qua_han_thi_ha_nhan(self):
        r = self.chay("nap();PTR_GOC._nhan=Date.now()-46e3;ptDoi();r.a=tom();")['a']
        self.assertEqual((r['tt'], r['hl']), ('cu', False))

    def test_tai_khoan_dung(self):
        r = self.chay("nap();window.GSR={ds:[{id:'ngay-2026-11-27',muc:'xau'}]};ptDoi();r.a=tom();"
                      "window.GSR={ds:[{id:'khong-sl-1',muc:'xau'}]};ptDoi();r.b=tom();")
        a = r['a']
        self.assertEqual((a['tt'], a['hl'], a['phieu']), ('dung', False, 'tk_dung'))
        self.assertIn('Tài khoản đang dừng', a['ly'])
        self.assertEqual((r['b']['tt'], r['b']['hl']), ('', True))             # cảnh báo khác không phải lệnh dừng giao dịch


if __name__ == '__main__':
    unittest.main()
