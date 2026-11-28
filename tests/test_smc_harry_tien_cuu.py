import json
from contextlib import closing
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

from so_cong_khai import smc_harry_loc as L, smc_harry_tien_cuu as F, tin_hieu_tien_cuu as S


def test_khoa_kiem_nguon_va_khung(tmp_path):
    lock = {'phien': L.PHIEN, 'nguon': L.dau_nguon(), 'chon': {'M5': {'loc': 'cau_truc', 'tp_r': .85}}}
    p = tmp_path / L.TEP_KHOA
    p.write_text(json.dumps(lock), encoding='utf-8')
    assert L.nap_khoa(tmp_path) == lock
    lock['chon']['M5']['tp_r'] = .99
    p.write_text(json.dumps(lock), encoding='utf-8')
    with pytest.raises(ValueError, match='ngoài tập ứng viên'):
        L.nap_khoa(tmp_path)


def test_tien_cuu_giu_muc_gia_dau_va_cho_nen_sau_khi_khoa(tmp_path, monkeypatch):
    dong = pd.Timestamp('2026-11-30T08:00:00Z')
    now = dong + timedelta(seconds=10)
    ms = S._ms(now)
    frame = lambda tf: pd.DataFrame({'open': 100., 'high': 101., 'low': 99., 'close': 100.},
                                    index=pd.date_range(end=dong - pd.Timedelta(minutes=F.H.CT.KHUNG[tf]),
                                                        periods=300, freq=f'{F.H.CT.KHUNG[tf]}min'))
    params = {'loc': 'cau_truc', 'tp_r': .85}
    lock = {'utc_khoa': (dong - timedelta(days=1)).isoformat(), 'chon': {'M5': params}}
    cfg = {'gia': {'ma_vang': 'XAUUSDp'}}
    tick = NS(time_msc=ms, bid=100., ask=100.1)
    account = NS(server='TEST', currency='USD')
    symbol = NS(visible=True, point=.01, digits=2, trade_tick_value_loss=1., trade_contract_size=100.)
    mock = NS(symbol_info_tick=lambda _: tick, symbol_info=lambda _: symbol, account_info=lambda: account)
    monkeypatch.setattr(F.da_ma, '_mt5', lambda _: mock)
    monkeypatch.setattr(F.da_ma, '_nen', lambda _mt, _ma, tf, _n: frame(tf))
    monkeypatch.setattr(F.H, 'boi_canh', lambda _: ())
    monkeypatch.setattr(F.H, '_vet_tick', lambda *_: (np.array([ms]), np.array([100.])))
    monkeypatch.setattr(F.S, 'cap_nhat', lambda *_: None)
    feature = pd.DataFrame([{'close': 100., 'atr': 4., 'phia': 1, 'loai': 'FVG', 'day': 98., 'dinh': 101.,
                             'cau_truc': True, 'rut_chan': False, 'manh': True}], index=[frame('M5').index[-1]])
    monkeypatch.setattr(L, 'ung_vien', lambda *_: feature)
    first = F.quet(cfg, tmp_path, lock, now=now)
    assert first['ghi_moi'] == 1 and first['da_cham'][0]['cho'] == 1
    tick.ask = 100.12
    second = F.quet(cfg, tmp_path, lock, now=now)
    assert second['ghi_moi'] == 0
    with closing(S._db(tmp_path)) as conn:
        row = conn.execute('SELECT vao, phi_gia FROM tin_hieu').fetchone()
    assert row['vao'] == 100.1
    assert row['phi_gia'] == pytest.approx(.27)  # Cộng .01 trượt giá ở bước chấm.
    later = {**lock, 'utc_khoa': (dong + timedelta(seconds=1)).isoformat()}
    assert F.quet(cfg, tmp_path, later, now=now)['khung']['M5']['tt'] == 'truoc_khi_khoa'


def test_muc_theo_tick_bo_diem_vao_neu_gia_da_di_xa():
    dong = datetime(2026, 11, 30, 8, tzinfo=timezone.utc)
    now = dong + timedelta(seconds=10)
    ms = S._ms(now)
    tick = NS(time_msc=ms, bid=100., ask=100.1)
    row = NS(close=100., atr=4., phia=1, day=98., dinh=101.)
    opts = {'dich_r': .85, 'buoc': .01, 'digits': 2, 'stops': 0}
    assert F.muc_theo_tick(row, dong, now, tick, None, **opts)[0] == 'thieu_tick'
    vet = (np.array([ms - 1_000, ms]), np.array([103., 100.]))
    assert F.muc_theo_tick(row, dong, now, tick, vet, **opts)[0] == 'gia_di_xa'


def test_m30_tinh_sau_chi_phi_stress_va_giu_cong_du_mau(tmp_path):
    dong = datetime(2026, 11, 30, 8, tzinfo=timezone.utc)
    now = dong + timedelta(seconds=10)
    tag = 'harry-test'
    snap = {'nguon': 'mt5', 'phien_ban': F.T.PHIEN_BAN, 'may_chu': 'TEST', 'ma': 'XAUUSDp', 'luc': now.isoformat(),
            'tick_ms': S._ms(now), 'bid': 100., 'ask': 100.1, 'buoc_gia': .01, 'gia_tick': 1., 'tien_tk': 'USD',
            'lich_tin': True, 'ds': [{'tf': 'M30', 'loai': 'FVG', 'huong': 'MUA', 'trang_thai': 'dat', 'vao': 100.1,
                                     'sl': 99.1, 'tp': 100.65, 'dong': dong.isoformat(), 'het': now.isoformat()}]}
    assert S.ghi(tmp_path, snap, 0., now, phien_rieng=tag) == 1
    with closing(S._db(tmp_path, viet=True)) as db, db:
        db.execute("UPDATE tin_hieu SET tt='tp', r_rong=.20")
    result = F.so_m30(tmp_path, 'TEST', 'XAUUSDp', tag)
    assert result['so'] == 1 and result['thang_pct'] == 100
    assert result['r_rong_moi_lenh'] == .20 and result['r_stress_moi_lenh'] == -.05
    assert not result['qua_cong']
