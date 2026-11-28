import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from so_cong_khai import diem_vao_rt, tin_hieu_ngan


def test_nhat_ky_chi_ghi_muc_cho_gan_khi_gia_con_moi():
    now = datetime(2026, 11, 27, 11, 14, 11, tzinfo=timezone.utc)
    p = {'huong': 'MUA', 'vao': 3647.59, 'sl': 3623.48, 'tp': [3671.71, 3695.82],
         'thuc_thi': {'loai': 'gh', 'atr': 7.58, 'het': (now + timedelta(hours=1)).isoformat()}}
    q = {'nguon': 'mt5', 'het': now.isoformat(), 'bid': 3676.47, 'ask': 3676.64}
    assert not diem_vao_rt.ghi_duoc(p, q, now)
    near = dict(q, bid=3651.8, ask=3652)
    assert diem_vao_rt.ghi_duoc(p, near, now)
    assert not diem_vao_rt.ghi_duoc(p, near, now + timedelta(seconds=16))
    assert not diem_vao_rt.ghi_duoc(p, dict(near, nguon='kho'), now)
    assert not diem_vao_rt.ghi_duoc(p, dict(near, tick_ms=None), now)
    assert not diem_vao_rt.ghi_duoc(p, dict(q, bid=3647.40, ask=3647.59), now)


@pytest.mark.skipif(not shutil.which('node'), reason='máy không có Node.js')
def test_tick_dung_phia_khong_doi_muc_cho_va_tinh_lai_phuong_an_thi_truong():
    quotes = [[100, 100.25], [100.25, 100.5], [101.5, 101.75], [100, 101]]
    results = [tin_hieu_ngan.muc_gia(SimpleNamespace(phia=1, close=100, atr=4, day=98, dinh=103),
                                    bid, ask, .25, 2) for bid, ask in quotes]
    test = r"""
const assert=require('node:assert/strict'),t=Date.parse('2026-11-27T11:14:11Z');
const fib={ma:'fib',huong:'MUA',co:true,hieu_luc:true,vao:3647.59,sl:3623.48,tp:[3671.71,3695.82],rr:[1,2],
           thuc_thi:{loai:'gh',tu:new Date(t-60000).toISOString(),het:new Date(t+3600000).toISOString()}};
const q=(bid,ask,ms=t,ma='XAUUSDp')=>({bid,ask,ms,ma});
const latch=new Map(),x=(p,g,now=t,k=latch)=>window.ENTRY_RT.xem(p,g,now,7.58,2,k);
const far=x(fib,q(3676.47,3676.64));
assert.equal(far.rt,'cho_xa');assert.equal(far.hieu_luc,false);
assert.deepEqual([far.vao,far.sl,far.tp],[fib.vao,fib.sl,fib.tp]);
assert.equal(x(fib,q(3647.50,3647.66)).rt,'cho_gia'); // Bid ở dưới, Ask còn ở trên mức lệnh mua.
assert.equal(x(fib,q(3647.40,3647.59)).rt,'da_cham');
assert.equal(x(fib,q(3650,3650.17)).rt,'da_cham');
assert.equal(x(fib,q(3650,3650.17,t,'OTHER')).rt,'cho_gia');
assert.equal(x(fib,q(3650,3650.17),t+3600001).rt,'het_han');
assert.equal(x(fib,q(3650,3650.17,t-15001),t,new Map()).rt,'gia_cu');
assert.equal(x(fib,q(3695.82,3695.99),t,new Map()).rt,'cham_tp');
const sell={...fib,huong:'BAN',ma:'ict',vao:101,sl:110,tp:[92,83]};
assert.equal(x(sell,q(100.9,101.1)).rt,'cho_gia');
assert.equal(x(sell,q(101,101.2)).rt,'da_cham');
const tt={...fib,ma:'breakout',vao:100,sl:95,tp:[105,110],thuc_thi:{...fib.thuc_thi,loai:'tt',moc:100,theo_r:true}};
const live=x(tt,q(100.3,100.5));
assert.deepEqual([live.rt,live.vao,live.sl,live.tp],['san_sang',100.5,95,[106,111.5]]);
assert.equal(x(tt,q(102,102.2)).rt,'gia_di_xa');
assert.equal(x(tt,q(99.9,100.8)).rt,'spread');
const short={...tt,vao:100.25,sl:97.5,tp:[104.5],rr:[1.5],thuc_thi:{...tt.thuc_thi,ngan:{day:98,dinh:103,buoc:.25}}};
const actual=quotes.map(([bid,ask])=>window.ENTRY_RT.xem(short,q(bid,ask),t,4,2,new Map()));
for(let i=0;i<actual.length;i++){
 const [state,out]=results[i],a=actual[i];
 assert.equal(a.rt,state==='dat'?'san_sang':state);
 if(state==='dat')assert.deepEqual([a.vao,a.sl,a.tp[0],a.rr[0]],[out.vao,out.sl,out.tp,out.rr]);
}
const warm={...short,quan_sat:true,hieu_luc:false,vao:null,sl:null,tp:[],thuc_thi:{...short.thuc_thi,cho_tick:true}};
assert.equal(window.ENTRY_RT.xem(warm,null,t,4,2,new Map()).rt,'gia_cu');
assert.deepEqual(window.ENTRY_RT.xem(warm,q(100,100.25),t,4,2,new Map()).tp,[results[0][1].tp]);
"""
    proc = subprocess.run(['node', '-e', 'const window={};\n' + diem_vao_rt.JS +
                           f'const quotes={json.dumps(quotes)},results={json.dumps(results)};\n' + test],
                          capture_output=True, text=True, encoding='utf-8', timeout=10, check=False)
    assert proc.returncode == 0, proc.stderr
