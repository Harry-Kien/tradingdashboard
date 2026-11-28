from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from so_cong_khai import cau_truc_live as L
from so_cong_khai.doc_so import VN

BASE = datetime(2026, 11, 28, 0, 59, 55, tzinfo=VN).astimezone(timezone.utc)
CFG_GUI = {'che_do': 'gui', 'chat': '@fixture'}
DEST = L.nhom_ma(CFG_GUI)
Z = {'id': 'z1', 'loai': 'iFVG', 'chieu': 1, 'duoi': 100., 'tren': 102., 'vo_hieu': 99.8,
     'tu': int((BASE - timedelta(hours=2)).timestamp())}


def moc(s):
    return int((BASE + timedelta(seconds=s)).timestamp() * 1000)


def snap(s=0, bid=105., ask=105.2, *, ma='BTCUSDTp', dx=(), huy=False, tuoi=True, z=None):
    t = BASE + timedelta(seconds=s)
    h1 = int(t.replace(minute=0, second=0, microsecond=0).timestamp())
    data = {**(z or Z), 'xac_nhan': list(dx)}
    return {'ma': ma, 'feed': 'demo', 'tick_ms': moc(s), 'luc': t.isoformat(), 'bid': bid, 'ask': ask, 'gia_moi': tuoi,
            'h1': 1, 'h4': -1, 'so_le': 2, 'trang_thai': 'lech_khung', 'bang_chung': 'mock',
            'nen_h1_dong': h1, 'nen': [[h1 - 3600, 102., 105., 98., 99. if huy else 104.]],
            'vung': [] if huy else [data]}


def tien(st, s, ticks=(), **kw):
    return L.tien(st, snap(s, **kw), ticks, 'gui', DEST)


def test_lich_utc_7_vang_tuan_btc_cuoi_tuan():
    sat = datetime(2026, 11, 28, 0, 0, tzinfo=VN)
    sun = sat + timedelta(days=1)
    mon = sat + timedelta(days=2)
    cfg = {'gia': {'ma_vang': 'XAUUSDp'}}
    with patch.object(L.da_ma, '_mt5', return_value=object()), patch.object(L.da_ma, '_hien', return_value={'BTCUSDTp': object()}):
        assert L.ma_cho(cfg, sat - timedelta(seconds=1)) == 'XAUUSDp'
        assert L.ma_cho(cfg, sat.astimezone(timezone.utc)) == 'BTCUSDTp'
        assert L.ma_cho(cfg, sun) == 'BTCUSDTp'
        assert L.ma_cho(cfg, mon) == 'XAUUSDp'


def test_phat_hien_ask_cham_giua_hai_lan_quet_va_khong_lap():
    st, e = tien({}, 0)
    assert not e
    # Tick đầu Bid nằm trong vùng, Ask ngoài. Tick sau Ask thực sự chạm rồi giá bật lại.
    st, e = tien(st, 3, [(moc(1), 101.9, 102.2), (moc(2), 101.8, 101.99), (moc(3), 105., 105.2)])
    assert [(a['loai'], a['ms'], a['gia']) for a in e] == [('cham', moc(2), 101.99)]
    assert 'Ask chạm' in L.van_ban(e[0])
    st, e = tien(st, 4, [(moc(3), 101.8, 101.99), (moc(4), 101.4, 101.8)])
    assert not e


def test_moi_khung_chi_bao_khi_nen_dong_sau_cu_cham():
    st, _ = tien({}, 0)
    st, _ = tien(st, 2, [(moc(2), 101.1, 101.5)])
    dx = [
        {'tf': 'M5', 'tt': 'xac_nhan', 'luc': moc(1) // 1000, 'moc': 103.},
        {'tf': 'M15', 'tt': 'xac_nhan', 'luc': moc(5) // 1000, 'moc': 103.},
        {'tf': 'M30', 'tt': 'qua_xac_nhan', 'luc': moc(5) // 1000, 'moc': 103.},
    ]
    st, e = tien(st, 6, dx=dx)
    assert [(a['loai'], a['tf']) for a in e] == [('xac_nhan', 'M15')]
    assert 'đứng ngoài' in L.van_ban(e[0])
    _, e = tien(st, 7, dx=dx)
    assert not e


def test_bao_vo_hieu_h1_du_vung_da_roi_danh_sach_va_giu_ban_tin_cu(tmp_path):
    L.tao(tmp_path)
    assert L.luu(tmp_path, snap(), [], 'gui', DEST) == 0
    assert L.luu(tmp_path, snap(2), [(moc(2), 101., 101.5)], 'gui', DEST) == 1
    assert L.luu(tmp_path, snap(6, huy=True), [], 'gui', DEST) == 1
    kq = L.doc(tmp_path)
    assert {e['loai']: e['tt'] for e in kq['su_kien']} == {'cham': 'het_han', 'vo_hieu': 'cho'}
    assert L.luu(tmp_path, snap(7, huy=True), [], 'gui', DEST) == 0


def test_khoi_dong_dang_o_trong_vung_va_ket_noi_lai_khong_bao_hoi_cuu():
    st, e = tien({}, 0, bid=101., ask=101.2)
    assert not e
    st, e = tien(st, 2, [(moc(1), 101.9, 102.), (moc(2), 101.8, 101.9)], bid=101.8, ask=101.9)
    assert not e
    st, e = tien(st, 55, [(moc(55), 101., 101.2)], bid=101., ask=101.2)
    assert not e
    st, e = tien(st, 59, [(moc(57), 103., 103.2), (moc(58), 101., 101.2)])
    assert len(e) == 1 and e[0]['ms'] == moc(58)


def test_doan_tick_thieu_khong_day_moc_de_luot_sau_doc_bu():
    st, _ = tien({}, 0)
    st, e = tien(st, 2, None)
    assert st['tick_ms'] == moc(0) and not e and st['loi']
    _, e = tien(st, 4, [(moc(1), 101., 101.2), (moc(4), 105., 105.2)])
    assert len(e) == 1 and e[0]['ms'] == moc(1)


def test_doc_bu_khong_bo_cu_cham_khi_luot_loi_co_gia_dang_trong_vung():
    st, _ = tien({}, 0)
    st, ev = tien(st, 2, None, bid=101., ask=101.2)
    assert not ev and st['vung'][Z['id']]['ngoai']
    _, ev = tien(st, 4, [(moc(1), 101., 101.2), (moc(3), 105., 105.2)])
    assert [(a['loai'], a['ms']) for a in ev] == [('cham', moc(1))]


def test_tick_moi_trung_mili_giay_voi_moc_cu_van_ghi_nhan_duoc():
    st, _ = tien({}, 0)
    st, ev = tien(st, 2, [(moc(0),105.,105.2), (moc(2),105.3,105.5)])
    assert not ev
    st, ev = tien(st, 3, [(moc(2),105.3,105.5), (moc(2),101.,101.2), (moc(3),105.,105.2)])
    assert [(a['loai'], a['ms']) for a in ev] == [('cham', moc(2))]
    _, ev = tien(st, 4, [(moc(3),105.,105.2), (moc(4),101.,101.2)])
    assert not ev


def test_gui_dong_thoi_cung_su_kien_chi_giam_mat_mot_lan(tmp_path):
    L.tao(tmp_path)
    L.luu(tmp_path, snap(), [], 'gui', DEST)
    L.luu(tmp_path, snap(2), [(moc(1), 101., 101.2)], 'gui', DEST)
    call = Mock(return_value={'ok': True, 'result': {'message_id': 82}})
    with ThreadPoolExecutor(max_workers=2) as ex:
        rs = list(ex.map(lambda _: L.gui_mot(tmp_path, CFG_GUI, 'fake', call, BASE + timedelta(seconds=2)), range(2)))
    assert sum(rs) == 1
    assert call.call_count == 1
    assert L.doc(tmp_path)['su_kien'][0]['tt'] == 'da_gui'
