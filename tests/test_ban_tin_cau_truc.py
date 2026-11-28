from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd

from so_cong_khai import ban_tin_cau_truc as C, telegram_nhom as T


MOC = datetime(2026, 11, 27, 13, 0, 10, tzinfo=timezone.utc)


def nen(tf):
    phut = C.KHUNG[tf]
    het = pd.Timestamp(MOC).floor(f'{phut}min')
    idx = pd.date_range(end=het - timedelta(minutes=phut), periods=160, freq=f'{phut}min')
    p = 100 + np.arange(len(idx)) * .7
    return pd.DataFrame({'open': p, 'high': p + .50, 'low': p - .15, 'close': p + .47}, index=idx)


def test_ifvg_chi_dao_vai_sau_nen_dong_xuyen():
    b = nen('H1')
    _, ds, _ = list(C.phat_vung(b))[-1]
    v = ds[-1]
    tren = v.tren
    t = b.index[-1] + timedelta(hours=1)
    b.loc[t] = (tren, tren + .25, v.duoi - 1., v.duoi + .1)
    assert v in list(C.phat_vung(b))[-1][1]  # râu nến qua vùng, thân đóng vẫn ở trong
    b.loc[t, 'close'] = v.duoi - .9
    ms, sau, _ = list(C.phat_vung(b))[-1]
    assert C.Vung(v.duoi, v.tren, -1, ms, 'iFVG') in sau


def test_ban_tin_khong_dung_nen_tuong_lai_va_anh_co_bang_chung():
    fr = {tf: nen(tf) for tf in C.KHUNG}
    px = float(fr['H1'].iloc[-1].close)
    q = (px, px + .05, int(MOC.timestamp() * 1000))
    a = C.lap('XAUUSDp', fr, *q, MOC, 2)
    assert a['gia_moi'] and len(a['vung']) == 1  # các khoảng trống chồng lên nhau chỉ hiện một lần
    assert all([k['tf'] for k in v['xac_nhan']] == ['M5', 'M15', 'M30'] for v in a['vung'])
    for tf, b in fr.items():
        b.loc[b.index[-1] + timedelta(minutes=C.KHUNG[tf])] = [800., 901., 700., 820.]
    assert C.lap('XAUUSDp', fr, *q, MOC, 2) == a
    assert C.anh_png(a).startswith(b'\x89PNG\r\n\x1a\n')
    s = C.van_ban(a)
    assert all(k in s for k in ('UTC+7', a['bang_chung'], 'Vô hiệu nếu H1 đóng', 'M5', 'M15', 'M30'))
    assert C.lap('XAUUSDp', fr, *q, MOC + timedelta(seconds=31), 2)['trang_thai'] == 'gia_cu'


def test_xac_nhan_phai_den_sau_cham_va_gia_con_gan():
    b = nen('M5').iloc[-32:].copy()
    b.iloc[-3] = [210, 211, 209, 210.5]
    sec = int(b.index[-3].timestamp())
    v = C.Vung(209.6, 209.9, 1, sec)
    with patch.object(C.phuong_phap, '_pha_cau_truc', return_value=([(15, 28, 210., 1, 'CHoCH')], None)):
        assert C.xac_nhan(b, 'M5', v, 210.1, 1.0)['tt'] == 'cho_xac_nhan'
    with patch.object(C.phuong_phap, '_pha_cau_truc', return_value=([(15, 30, 210., 1, 'CHoCH')], None)):
        assert C.xac_nhan(b, 'M5', v, 210.1, 1.0)['tt'] == 'xac_nhan'
        assert C.xac_nhan(b, 'M5', v, 211., 1.0)['tt'] == 'qua_xac_nhan'


def test_telegram_xem_truoc_khong_doc_token_va_giu_gia_cu_ngoai_luong_gui(tmp_path):
    stub = {'ma': 'ETHUSDTp', 'gia_moi': False}
    with (patch.object(C, 'doc', return_value=stub), patch.object(C, 'anh_png', return_value=b'PNG'),
          patch.object(C, 'van_ban', return_value='bản nháp'), patch.object(T, 'token', side_effect=AssertionError('token'))):
        assert T.xem_truoc_cau_truc({}, 'ETHUSDTp') == {'ok': True, 'ma': 'ETHUSDTp', 'van_ban': 'bản nháp', 'anh': 'UE5H'}
        gui = Mock()
        assert not T.dang_phan_tich({}, MOC, tmp_path, {'che_do': 'gui'}, goi=gui)['ok']
        gui.assert_not_called()


def test_cua_kiem_gia_truoc_khi_gui():
    s = {'tt': 'dang_mo', 'huong': 'MUA', 'vao': 120, 'sl': 116, 'tp': [125], 'atr': 2}
    ms = int(MOC.timestamp() * 1000)
    assert T._dat_luc_gui(s, (119.95, 120.12, ms), MOC)
    assert not T._dat_luc_gui(s, (119.95, 120.12, ms - 16_000), MOC)
    assert not T._dat_luc_gui(s, (121.7, 121.9, ms), MOC)
    p = dict(s, cho=True, tt='cho_khop')
    assert T._dat_luc_gui(p, (120.30, 120.5, ms), MOC)
    assert not T._dat_luc_gui(p, (119.8, 120., ms), MOC)


def test_vong_telegram_cho_gia_moi_va_in_dau_gia_truoc_khi_gui(tmp_path):
    r = {'id': 1, 'sym': 'XAUUSDp', 'ma': 'bot:nen', 'luc': MOC.isoformat(), 'tt': 'dang_mo',
         'huong': 'MUA', 'vao': 120, 'sl': 116, 'tp': [125], 'atr': 2}
    c = {**T.MAC_DINH, 'che_do': 'gui', 'tin_tuc': False, 'phan_tich': False, 'tong_ket': False, 'ket_qua': False,
         'hoa_von_tp1': False}
    s = {'moc_id': 0}
    m = int(MOC.timestamp() * 1000)
    with (patch.object(T, 'cai', return_value=c), patch.object(T, 'trang_thai', return_value=s),
          patch.object(T, 'gui', return_value={'ok': True, 'msg': 17, 'that': True}) as gui):
        assert T.mot_luot({}, MOC, tmp_path, doc_nk=lambda: [r], kiem_gia=lambda _: (121.4, 121.6, m))['tin_hieu'] == 0
        gui.assert_not_called()
        assert s['chan_gia'] == 1
        assert T.mot_luot({}, MOC, tmp_path, doc_nk=lambda: [r], kiem_gia=lambda _: (119.9, 120.1, m))['tin_hieu'] == 1
        assert 'Đối chiếu MT5' in gui.call_args.args[0]
