import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from so_cong_khai import diem_vao_rt, smc_harry as H


def test_fvg_repo_chi_xuat_hien_sau_nen_thu_ba_va_giu_qua_mep_khoi():
    idx = pd.date_range('2026-01-01', periods=1030, freq='h', tz='UTC')
    prices = 100 + np.arange(len(idx)) * .7
    h1 = pd.DataFrame({'open': prices, 'high': prices + .5, 'low': prices - .15, 'close': prices + .47}, index=idx)
    zones = H.fvg_repo(h1)
    assert set(zones) == set(range(2, len(h1)))
    assert H.fvg_repo(h1.iloc[:1026]) == {i: z for i, z in zones.items() if i < 1026}
    states = list(H.CT.phat_vung(h1, zones))
    t, book, _ = states[1026]
    side, low, high = zones[1026]
    new = H.CT.Vung(low, high, side, t)
    assert t == int((idx[1026] + pd.Timedelta(hours=1)).timestamp())
    assert new in book and new not in states[1025][1]


@pytest.mark.skipif(not shutil.which('node'), reason='máy không có Node.js')
@pytest.mark.parametrize('side', [1, -1])
def test_gia_harry_song_khop_may_chu_va_xoa_muc_khi_gia_di_xa(side):
    now = datetime(2026, 11, 27, 11, 15, 10, tzinfo=timezone.utc)
    dong = now - timedelta(seconds=10)
    r = SimpleNamespace(phia=side, close=100., atr=4., day=97.5, dinh=102.5, loai='FVG', duoi=98., tren=99., moc=100.)
    p = H.the('harry_smc', 'M15', 'Harry SMC')
    tick = SimpleNamespace(time_msc=int(now.timestamp() * 1000), bid=100., ask=100.25)
    vet = (np.array([tick.time_msc]), np.array([tick.bid]))
    opts = {'buoc': .25, 'so_le': 2, 'stops': 0., 'gan_tin': False, 'vet': vet}
    p = H.muc_live(p, r, dong, now, tick, **opts)
    assert p['hieu_luc'] and p['quan_sat']
    card = H.the('harry_smc', 'M15', 'Harry SMC')
    assert not H.muc_live(card, r, dong, now, tick, **dict(opts, stops=9.))['hieu_luc']
    probe = r"""
const assert=require('node:assert/strict');
const latch=new Map();
const run=(bid,ask,ms=t,now=t,cache=new Map())=>window.ENTRY_RT.xem(p,{bid,ask,ms,ma:'XAUUSDp'},now,4,2,cache);
const live=run(100,100.25);
assert.deepEqual([live.rt,live.vao,live.sl,live.tp,live.rr],['san_sang',p.vao,p.sl,p.tp,p.rr]);
const far=run(101.5,101.75,t,t,latch);
assert.deepEqual([far.rt,far.vao,far.sl,far.tp],['bo_lo',null,null,[]]);
assert.equal(run(100,100.25,t+1,t+1,latch).rt,'bo_lo');
assert.equal(run(100,100.5).rt,'spread');
assert.equal(run(100,100.25,t-16000).rt,'gia_cu');
assert.equal(run(100,100.25,t+120000,t+120000).rt,'het_han');
"""
    check = subprocess.run(['node', '-e', 'const window={};\n' + diem_vao_rt.JS +
                            f'const p={json.dumps(p)},t={tick.time_msc};\n' + probe],
                           capture_output=True, text=True, encoding='utf-8', timeout=10, check=False)
    assert check.returncode == 0, check.stderr


def test_tai_lai_chart_khong_khoi_phuc_diem_vao_sau_khi_gia_di_xa():
    now = datetime(2026, 11, 27, 11, 15, 10, tzinfo=timezone.utc)
    start = now - timedelta(seconds=10)
    end = int(now.timestamp() * 1000)
    r = SimpleNamespace(phia=1, close=3647.59, atr=4., day=3645., dinh=3650., loai='FVG', duoi=3645., tren=3646., moc=3647.)
    tick = SimpleNamespace(time_msc=end, bid=3647.59, ask=3647.76)
    p = H.the('harry_smc', 'M15', 'Harry SMC')
    opts = {'buoc': .01, 'so_le': 2, 'stops': 0., 'gan_tin': False}
    assert not H.muc_live(p, r, start, now, tick, vet=None, **opts)['co']
    assert not H.muc_live(p, r, start, now, tick, vet=(np.array([end - 11_000]), np.array([3647.60])), **opts)['co']
    vet = (np.array([end - 3000, end]), np.array([3676.47, tick.bid]))
    kq = H.muc_live(p, r, start, now, tick, vet=vet, **opts)
    assert not kq['co'] and 'Đã bỏ lỡ' in kq['vi_sao']
    vet = (np.array([end - 11_000, end]), vet[1])
    assert H.muc_live(p, r, start, now, tick, vet=vet, **opts)['hieu_luc']
