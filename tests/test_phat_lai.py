# -*- coding: utf-8 -*-
"""Phát lại nến (so_cong_khai.bieu_do_phat_lai): trang có đủ móc chặn tải lại và luồng giá; phần giao dịch thử tính đúng R trên chuỗi nến giả.
Phần logic chạy bằng Node với DOM giả tối thiểu; không có Node thì bỏ qua phần đó."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from so_cong_khai import bieu_do, bieu_do_chi_bao, bieu_do_phat_lai

NODE = shutil.which('node')


class MocTrang(unittest.TestCase):
    def test_moc_va_chan(self):
        h = bieu_do.trang_bieu_do('Thử')
        self.assertIn('window.BDPL={chan:false,get D(){return chartReady()?D:null},set D(v){D=v}', h)
        for ham in ('async function load(keep){', 'function sgAp(x){', 'function sgMo(){', 'function hisGhep(){', 'function ptTai(tu){'):
            self.assertIn(ham + 'if(window.BDPL&&BDPL.chan)return', h, ham)
        self.assertIn(bieu_do_phat_lai.JS.strip()[:80], h)                   # phát lại nạp cùng trang, sau bộ chọn chỉ báo
        self.assertIn('window.PHAT_LAI=true', bieu_do_phat_lai.JS)
        js = bieu_do.JS                                                             # 26/11/2026: chú thích từng nuốt mất mã phía sau trên cùng dòng
        i = js.index('if(ma0===ma&&epoch0===chartEpoch&&')                          # điều kiện còn thêm topdown0/nguon0 (28/11/2026)
        self.assertRegex(js[i:i + 400], r'\n\s*PTR_GOC=j;')                  # câu lệnh lưu kết quả phải nằm trên dòng riêng, không nằm sau //
        for dong in js.splitlines():
            if 'BDPL.chan' in dong and '//' in dong:
                self.assertNotRegex(dong.split('//', 1)[1], r'[;{}]\s*\w+\s*=', dong[:120])   # không còn câu lệnh nằm sau chú thích
        self.assertIn('window.PHAT_LAI=false', bieu_do_phat_lai.JS)
        self.assertTrue(bieu_do_chi_bao.JS.endswith(bieu_do_phat_lai.JS))
        for cam in ('fetch(', 'order_send'):
            self.assertNotIn(cam, bieu_do_phat_lai.JS)                          # không gọi máy chủ, không đặt lệnh


VO = r"""
const noop=()=>{},el=()=>new Proxy({dataset:{},style:{},hidden:true,nextElementSibling:null,classList:{toggle:noop,add:noop,remove:noop},parentNode:null},{get:(t,k)=>k in t?t[k]:(k==='querySelector'?()=>el():k==='querySelectorAll'?()=>[]:noop),set:(t,k,v)=>{t[k]=v;return true}});
globalThis.window=globalThis;globalThis.document={createElement:el,querySelector:()=>el(),querySelectorAll:()=>[],body:el(),addEventListener:noop,documentElement:{clientWidth:1200}};
globalThis.addEventListener=noop;globalThis.localStorage={getItem:()=>null,setItem:noop};globalThis.alert=noop;globalThis.matchMedia=()=>({matches:false});
globalThis.LightweightCharts={createSeriesMarkers:()=>({setMarkers:noop,detach:noop})};
const cs=JSON.parse(require('fs').readFileSync(process.argv[2],'utf8'));let D={candles:cs,tf:'M15',live:-1,so_le:2,ema20:cs.map(r=>r[4]),ask:4000,pivot:{P:1},ichi_sau:[[1,2,3]],luat:{bot_cho:[1]}},ve=0,tai=0;
globalThis.BDPL={chan:false,get D(){return D},set D(v){D=v},IND:()=>['ema20'],ve:()=>{ve++},tai:()=>{tai++},dong:noop,trong:noop,TRONG:false};
const series={createPriceLine:()=>({}),removePriceLine:noop},chart={timeScale:()=>({getVisibleLogicalRange:()=>null,setVisibleLogicalRange:noop}),subscribeClick:noop};
globalThis.BDCB=()=>({LW:{nen:series,chart},D,P:{}});
globalThis.CBCN={moc:[],_tinh:{atr:(H,L,C,n)=>C.map(()=>10)}};
"""


@unittest.skipUnless(NODE, 'không có Node')
class GiaoDichThu(unittest.TestCase):
    def test_cat_va_ket_qua(self):
        cs = [[1767225600 + 900 * i, 4000.0, 4005.0, 3995.0, 4000.0] for i in range(400)]
        cs[201] = [cs[201][0], 4000.0, 4031.0, 3996.0, 4030.0]                 # nến 201 chạm TP của lệnh mua (vào 4000, ATR 10, SL 1,5 ATR, TP 2R = 4030)
        cs[301] = [cs[301][0], 4000.0, 4016.0, 3984.0, 4000.0]                 # nến 301 chạm cả SL và TP của lệnh bán: tính SL trước
        cs[351] = [cs[351][0], 3970.0, 3972.0, 3960.0, 3965.0]                 # nến 351 mở nhảy qua SL (3985) của lệnh mua: khớp ở giá mở 3970 = −2R
        js = VO + bieu_do_phat_lai.JS + r"""
const P=CBPL;P.batDau(200);const a=BDPL.D;
const r={on:P.PL.on,chan:BDPL.chan,co:window.PHAT_LAI,n:a.candles.length,cuoi:a.candles[a.candles.length-1][0],ema:a.ema20.length,ask:a.ask,pivot:a.pivot,may:a.ichi_sau.length,luat:a.luat};
P.vao(1);const l=P.PL.lenh;r.lenh=[l.vao,l.sl,l.tp];P.tien();r.sau=P.PL.ds.map(x=>[x.ly,+x.r.toFixed(4)]);
const k0=P.PL.k;P.lui();r.lui_chan=P.PL.k===k0;                                       // không lùi qua lệnh đã biết kết quả
P.batDau(300);P.vao(0);P.tien();r.sau2=P.PL.ds.map(x=>[x.ly,+x.r.toFixed(4)]);
P.batDau(350);P.vao(1);P.tien();r.gap=P.PL.ds.map(x=>[x.ly,+x.r.toFixed(4)]).slice(-1);
P.thoat(true);r.ra={on:P.PL.on,chan:BDPL.chan,co:window.PHAT_LAI,n:BDPL.D.candles.length,tai};
process.stdout.write(JSON.stringify(r));"""
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'cs.json').write_text(json.dumps(cs), encoding='utf-8')
            (Path(d) / 't.js').write_text(js, encoding='utf-8')
            p = subprocess.run([NODE, str(Path(d) / 't.js'), str(Path(d) / 'cs.json')], capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr[-2000:])
        r = json.loads(p.stdout)
        self.assertEqual((r['on'], r['chan'], r['co']), (1, True, True))
        self.assertEqual((r['n'], r['cuoi'], r['ema']), (201, cs[200][0], 201))     # chỉ nến tới điểm đang phát
        self.assertEqual((r['ask'], r['pivot'], r['may'], r['luat']), (None, None, 0, None))   # không lộ giá, mây chiếu tới, mức bot hiện tại
        self.assertTrue(r['lui_chan'])
        self.assertEqual(r['gap'], [['SL', -2.0]])
        self.assertEqual(r['lenh'], [4000, 3985, 4030])
        self.assertEqual(r['sau'], [['TP', 2.0]])
        self.assertEqual(r['sau2'], [['TP', 2.0], ['SL', -1.0]])
        self.assertEqual(r['ra'], {'on': 0, 'chan': False, 'co': False, 'n': 400, 'tai': 1})


if __name__ == '__main__':
    unittest.main()
