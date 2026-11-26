"""Kế hoạch vốn và lệnh: người dùng nhập vốn (hoặc lấy vốn từ MT5) và mức rủi ro; trang tính số tiền rủi ro mỗi lệnh, giới hạn lỗ ngày, tổng rủi
ro được mở, mô phỏng hàng nghìn chuỗi lệnh để ra xác suất sụt vốn, rồi với một lệnh cụ thể gợi ý dừng lỗ theo cấu trúc giá (đỉnh/đáy gần nhất)
và theo biến động (ATR), chốt lời theo bội số R và theo đỉnh/đáy đối diện, kèm khối lượng, ký quỹ và khoảng giá tới mức sàn đóng lệnh (stop out).

CHỈ ĐỌC: giá, nến, thông số mã và tài khoản từ MT5 qua bảng giá; không đặt lệnh. Các mức là gợi ý quản lý rủi ro dựa trên dữ liệu hiện tại, không
phải dự báo giá. Các hàm `ke_hoach_von`, `mo_phong`, `goi_y_muc`, `tinh_lenh` là hàm thuần (kiểm thử được); `lap(cfg, bang, ...)` gom dữ liệu thật."""
from __future__ import annotations

import math
import random

MUC_RUI_RO = {                       # % vốn mỗi lệnh, lỗ tối đa mỗi ngày, tổng rủi ro được mở cùng lúc
    'an_toan': {'lenh': 0.5, 'ngay': 1.5, 'mo': 2.0},
    'can_bang': {'lenh': 1.0, 'ngay': 3.0, 'mo': 4.0},
    'manh': {'lenh': 2.0, 'ngay': 5.0, 'mo': 6.0},
}
KHUNG = ('M15', 'H1', 'H4')


def _lam_tron(x: float, d: int) -> float:
    return round(x, d)


def chuoi_thua_de_mat(rui_ro_pct: float, mat_pct: float) -> int:
    """Số lệnh thua liền (mỗi lệnh mất rui_ro_pct% số dư lúc đó) để vốn giảm mat_pct%."""
    r = min(max(rui_ro_pct, 1e-9), 99.999) / 100
    return max(1, math.ceil(math.log(1 - mat_pct / 100) / math.log(1 - r)))


def ke_hoach_von(von: float, muc: str = 'can_bang', rui_ro_pct: float | None = None) -> dict:
    """Phân bổ vốn theo một mức rủi ro (hoặc % tự đặt: lỗ ngày = 3 lần, tổng mở = 4 lần, như mức cân bằng)."""
    if not von or von <= 0:
        raise ValueError('vốn phải lớn hơn 0')
    m = dict(MUC_RUI_RO.get(muc) or MUC_RUI_RO['can_bang'])
    if rui_ro_pct is not None:
        if not 0 < rui_ro_pct <= 100:
            raise ValueError('rủi ro mỗi lệnh phải trong (0, 100]')
        m = {'lenh': rui_ro_pct, 'ngay': min(100.0, rui_ro_pct * 3), 'mo': min(100.0, rui_ro_pct * 4)}
        muc = 'tu_dat'
    return {'von': round(von, 2), 'muc': muc, 'rui_ro_pct': m['lenh'], 'lo_ngay_pct': m['ngay'], 'tong_mo_pct': m['mo'],
            'rui_ro_tien': round(von * m['lenh'] / 100, 2), 'lo_ngay_tien': round(von * m['ngay'] / 100, 2), 'tong_mo_tien': round(von * m['mo'] / 100, 2),
            'so_lenh_cung_luc': max(1, int(m['mo'] / m['lenh'] + 1e-9)), 'so_lenh_thua_ngay': max(1, int(m['ngay'] / m['lenh'] + 1e-9)),
            'thua_lien_mat_20': chuoi_thua_de_mat(m['lenh'], 20), 'thua_lien_mat_50': chuoi_thua_de_mat(m['lenh'], 50)}


def mo_phong(rui_ro_pct: float, ty_le_thang_pct: float, rr: float, so_lenh: int = 100, lan: int = 2000, seed: int = 7) -> dict:
    """Mô phỏng `lan` chuỗi `so_lenh` lệnh: mỗi lệnh rủi ro rui_ro_pct% số dư lúc đó, thắng với xác suất ty_le_thang (lời rr lần rủi ro), thua thì mất
    đúng phần rủi ro. Trả kết quả cuối (trung vị, 5% xấu nhất, 5% tốt nhất, % thay đổi vốn), xác suất có lúc sụt từ đỉnh ≥ 20% và ≥ 50%,
    và kỳ vọng mỗi lệnh tính bằng R."""
    if not 0 < rui_ro_pct < 100 or not 0 <= ty_le_thang_pct <= 100 or not rr > 0 or not 1 <= so_lenh <= 1000 or not 1 <= lan <= 20000:
        raise ValueError('tham số mô phỏng không hợp lệ')
    rng = random.Random(seed)
    r, p = rui_ro_pct / 100, ty_le_thang_pct / 100
    cuoi, sut20, sut50, sut_max = [], 0, 0, []
    for _ in range(lan):
        v = dinh = 1.0
        s = 0.0
        for _ in range(so_lenh):
            v *= (1 + r * rr) if rng.random() < p else (1 - r)
            dinh = max(dinh, v)
            s = max(s, 1 - v / dinh)
        cuoi.append(v)
        sut_max.append(s)
        sut20 += s >= 0.2
        sut50 += s >= 0.5
    cuoi.sort()
    sut_max.sort()
    pt = lambda xs, q: xs[min(len(xs) - 1, int(q * len(xs)))]                 # noqa: E731
    return {'so_lenh': so_lenh, 'lan': lan, 'ky_vong_r': round(p * rr - (1 - p), 3), 'hoa_von_pct': round(100 / (1 + rr), 1),
            'trung_vi_pct': round((pt(cuoi, 0.5) - 1) * 100, 1), 'xau_5_pct': round((pt(cuoi, 0.05) - 1) * 100, 1), 'tot_5_pct': round((pt(cuoi, 0.95) - 1) * 100, 1),
            'xs_sut_20': round(sut20 / lan * 100, 1), 'xs_sut_50': round(sut50 / lan * 100, 1), 'sut_trung_vi_pct': round(pt(sut_max, 0.5) * 100, 1)}


def _dinh_day(cao: list[float], thap: list[float], k: int = 2) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Đỉnh/đáy fractal: nến có đỉnh cao nhất (đáy thấp nhất) trong k nến mỗi bên. Trả (đỉnh, đáy), mỗi phần tử (vị trí, giá)."""
    dinh, day = [], []
    for i in range(k, len(cao) - k):
        if cao[i] == max(cao[i - k:i + k + 1]):
            dinh.append((i, cao[i]))
        if thap[i] == min(thap[i - k:i + k + 1]):
            day.append((i, thap[i]))
    return dinh, day


def goi_y_muc(chieu: str, vao: float, cao: list[float], thap: list[float], atr: float | None, spread: float = 0.0, so_le: int = 2,
              cach_toi_thieu: float = 0.0) -> dict:
    """Gợi ý dừng lỗ và chốt lời cho lệnh MUA/BÁN ở giá `vao`, từ nến đã đóng (cũ trước) và ATR của cùng khung.
    Dừng lỗ: 'cau_truc' = sau đáy (MUA) hoặc đỉnh (BÁN) fractal gần nhất phía bên kia giá vào, lùi thêm spread và 0,1 ATR; 'bien_dong' = 1,5 ATR.
    Gợi ý chọn phương án cấu trúc nếu nó cách giá vào từ 0,5 tới 3 ATR, không thì theo biến động.
    Chốt lời: 1R, 2R, 3R tính từ dừng lỗ được chọn, và 'cau_truc' = đỉnh (MUA) hoặc đáy (BÁN) fractal gần nhất phía trước giá vào nếu có."""
    if chieu not in ('MUA', 'BAN'):
        raise ValueError('chieu phải là MUA hoặc BAN')
    mua = chieu == 'MUA'
    dau = 1 if mua else -1
    dinh, day = _dinh_day(cao, thap)
    dem = (spread or 0) + (0.1 * atr if atr else 0)
    sl: dict = {}
    phia = [p for _, p in reversed(day if mua else dinh) if (p < vao if mua else p > vao)]
    if phia:
        g = phia[0] - dau * dem
        sl['cau_truc'] = {'gia': _lam_tron(g, so_le), 'kc': round(abs(vao - g), so_le + 1)}
    if atr:
        g = vao - dau * 1.5 * atr
        sl['bien_dong'] = {'gia': _lam_tron(g, so_le), 'kc': round(1.5 * atr, so_le + 1)}
    for v in sl.values():
        v['atr'] = round(v['kc'] / atr, 2) if atr else None
        v['qua_sat'] = bool(cach_toi_thieu and v['kc'] < cach_toi_thieu)
    chon = None
    if 'cau_truc' in sl and (not atr or 0.5 <= sl['cau_truc']['atr'] <= 3):
        chon = 'cau_truc'
    elif 'bien_dong' in sl:
        chon = 'bien_dong'
    elif sl:
        chon = next(iter(sl))
    tp: list[dict] = []
    if chon:
        kc = sl[chon]['kc']
        for r in (1, 2, 3):
            tp.append({'k': f'{r}R', 'gia': _lam_tron(vao + dau * r * kc, so_le), 'r': float(r)})
        truoc = [p for _, p in reversed(dinh if mua else day) if (p > vao if mua else p < vao)]
        if truoc:
            g = truoc[0]
            tp.append({'k': 'cau_truc', 'gia': _lam_tron(g, so_le), 'r': round(abs(g - vao) / kc, 2)})
    return {'chieu': chieu, 'vao': vao, 'atr': atr, 'sl': sl, 'chon': chon, 'tp': tp}


def tinh_lenh(von: float, rui_ro_pct: float, vao: float, sl: float, tp: list[float] | None, gt1: float, lot_min: float = 0.01, lot_buoc: float = 0.01,
              lot_max: float = 100.0, ky_quy_1lot: float | None = None, dung_lenh_pct: float | None = None) -> dict:
    """Khối lượng theo % rủi ro (làm tròn xuống theo bước lot), tiền mất ở dừng lỗ, tiền lời ở từng mức chốt, ký quỹ và khoảng giá tới mức sàn đóng
    lệnh (vốn còn lại = dung_lenh_pct% ký quỹ). Dưới lot tối thiểu: trả số thật nếu vẫn vào ở mức tối thiểu."""
    kc = abs(vao - sl)
    if kc <= 0 or not gt1 or gt1 <= 0 or von <= 0:
        raise ValueError('cần giá vào khác dừng lỗ, giá trị bước giá và vốn dương')
    muc_tieu = von * rui_ro_pct / 100
    lot_tinh = muc_tieu / (kc * gt1)
    lot = min(lot_max, int(lot_tinh / lot_buoc + 1e-9) * lot_buoc)
    duoi_min = lot < lot_min
    if duoi_min:
        lot = lot_min
    lot = round(lot, 4)
    mat = kc * gt1 * lot
    out = {'lot_tinh': round(lot_tinh, 4), 'lot': lot, 'duoi_lot_min': duoi_min, 'rui_ro_muc_tieu': round(muc_tieu, 2), 'rui_ro_tien': round(mat, 2),
           'rui_ro_that_pct': round(mat / von * 100, 2), 'tp': []}
    for g in tp or []:
        out['tp'].append({'gia': g, 'lai_tien': round(abs(g - vao) * gt1 * lot, 2), 'r': round(abs(g - vao) / kc, 2)})
    if ky_quy_1lot:
        kq = ky_quy_1lot * lot
        out.update(ky_quy=round(kq, 2), ky_quy_pct=round(kq / von * 100, 2), muc_ky_quy=round(von / kq * 100, 0) if kq else None)
        if dung_lenh_pct is not None and kq:
            con = von - kq * dung_lenh_pct / 100                          # tiền được phép lỗ trước khi sàn đóng lệnh
            out['kc_dung_lenh'] = round(con / (gt1 * lot), 6) if con > 0 else 0.0
            out['dung_lenh_truoc_sl'] = out['kc_dung_lenh'] < kc
    return out


# --------------------------------------------------------------------------- gom dữ liệu thật (chỉ đọc)
DAC_TA_CAN = ('goc', 'so_le', 'diem', 'gt1', 'lot_min', 'lot_buoc', 'lot_max', 'ky_quy_1lot', 'muc_dung')


def du_lieu_tho(bang, ma: str, khung: str) -> dict:
    """Dữ liệu đầu vào của `lap` cho một mã và khung (thông số mã, giá, ATR, đỉnh/đáy nến đã đóng), không tính gì. Dùng để xuất bản demo tĩnh:
    trang demo tính kế hoạch ngay trong trình duyệt từ dữ liệu này."""
    if khung not in KHUNG:
        raise ValueError('khung phải là M15, H1 hoặc H4')
    if bang is None:
        raise ValueError('bảng giá chưa chạy')
    with bang._dk:
        dt = dict(bang.dac_ta.get(ma) or {})
        q = list(bang.gia.get(ma) or [])
        atr = (((bang.kt or {}).get(ma) or {}).get(khung) or {}).get('atr')
    if not dt:
        raise ValueError(f'không có mã {ma} trong bảng giá')
    g, _ = bang._cfg()
    mt5 = bang._mt5_fn(g)
    r = bang._rates(mt5, ma, khung, 120) if mt5 is not None else None
    d = int(dt['so_le'] if dt.get('so_le') is not None else 2)
    return {'ma': ma, 'khung': khung, 'dac_ta': {k: dt.get(k) for k in DAC_TA_CAN}, 'bid': q[0] if len(q) >= 2 else None,
            'ask': q[1] if len(q) >= 2 else None, 'atr': atr,
            'cao': [round(float(x), d) for x in r['high'][:-1]] if r is not None else [], 'thap': [round(float(x), d) for x in r['low'][:-1]] if r is not None else []}
def lap(cfg: dict, bang, ma: str, chieu: str, khung: str = 'H1', vao: float | None = None, sl: float | None = None, von: float | None = None,
        muc: str = 'can_bang', rui_ro_pct: float | None = None, ty_le_thang: float = 50.0, rr: float = 2.0) -> dict:
    """Kế hoạch đầy đủ cho mã `ma`: vốn (tham số, không có thì vốn MT5), phân bổ, mô phỏng, gợi ý mức và tính lệnh cho dừng lỗ `sl`
    (không có thì dùng mức được gợi ý)."""
    from . import tai_khoan                                                  # noqa: PLC0415
    if khung not in KHUNG:
        raise ValueError('khung phải là M15, H1 hoặc H4')
    if bang is None:
        raise ValueError('bảng giá chưa chạy')
    with bang._dk:
        if not bang.dac_ta:
            raise ValueError('bảng giá đang nạp thông số mã từ MT5, thử lại sau vài giây')
        dt = dict(bang.dac_ta.get(ma) or {})
        q = list(bang.gia.get(ma) or [])
        kt = dict(((bang.kt or {}).get(ma) or {}).get(khung) or {})
        tk_san = dict(getattr(bang, 'tai_khoan', {}) or {})
    if not dt:
        raise ValueError(f'không có mã {ma} trong bảng giá')
    thieu: list[str] = []
    nguon_von = 'nhap'
    if von is None:
        try:
            tk = tai_khoan.doc(cfg, ngay=1)
        except Exception as e:                                               # noqa: BLE001
            tk = {'san_sang': False, 'ly_do': str(e)}
        if tk.get('san_sang') and tk.get('von'):
            von, nguon_von = float(tk['von']), 'mt5'
        else:
            raise ValueError('chưa đọc được vốn từ MT5, hãy nhập vốn')
    kh = ke_hoach_von(von, muc, rui_ro_pct)
    mp = mo_phong(kh['rui_ro_pct'], ty_le_thang, rr)
    bid, ask = (q[0], q[1]) if len(q) >= 2 and q[0] and q[1] else (None, None)
    if vao is None:
        if bid is None:
            raise ValueError('chưa có giá trực tiếp của mã này, hãy nhập giá vào')
        vao = ask if chieu == 'MUA' else bid
    spread = (ask - bid) if bid is not None else 0.0
    so_le = int(dt['so_le'] if dt.get('so_le') is not None else 2)        # mã không có chữ số lẻ (so_le = 0) giữ 0, không thành 2
    cao, thap = [], []
    try:
        g, _ = bang._cfg()
        mt5 = bang._mt5_fn(g)
        r = bang._rates(mt5, ma, khung, 120) if mt5 is not None else None
        if r is not None:
            cao, thap = [float(x) for x in r['high'][:-1]], [float(x) for x in r['low'][:-1]]   # bỏ nến đang chạy
        else:
            thieu.append('chưa đọc được nến từ MT5')
    except Exception as e:                                                   # noqa: BLE001
        thieu.append(f'chưa đọc được nến: {e}')
    atr = kt.get('atr')
    if not atr:
        thieu.append('chưa có ATR của khung này')
    diem = float(dt.get('diem') or 0)
    muc_gy = goi_y_muc(chieu, float(vao), cao, thap, atr, spread, so_le, (dt.get('muc_dung') or 0) * diem)
    sl_dung = sl if sl is not None else (muc_gy['sl'][muc_gy['chon']]['gia'] if muc_gy['chon'] else None)
    lenh = None
    if sl_dung is not None:
        if (chieu == 'MUA' and sl_dung >= vao) or (chieu == 'BAN' and sl_dung <= vao):
            raise ValueError('dừng lỗ nằm sai phía giá vào')
        kc = abs(vao - sl_dung)
        dau = 1 if chieu == 'MUA' else -1
        tps = [round(vao + dau * k * kc, so_le) for k in (1, 2, 3)]
        tps += [t['gia'] for t in muc_gy['tp'] if t['k'] == 'cau_truc']
        if dt.get('gt1'):
            lenh = tinh_lenh(kh['von'], kh['rui_ro_pct'], float(vao), float(sl_dung), tps, float(dt['gt1']), float(dt.get('lot_min') or 0.01),
                             float(dt.get('lot_buoc') or 0.01), float(dt.get('lot_max') or 100), dt.get('ky_quy_1lot'),
                             None if tk_san.get('dung_lenh_tien') else tk_san.get('dung_lenh'))   # sàn đặt mức đóng lệnh bằng tiền: không tính khoảng theo %
            lenh['sl'] = sl_dung
            if lenh['duoi_lot_min'] and lenh['rui_ro_that_pct'] > kh['rui_ro_pct']:
                # vốn nhỏ phải vào lot tối thiểu: rủi ro thật lớn hơn mức chọn, mô phỏng theo rủi ro thật để không vẽ ra bức tranh an toàn giả
                r_that = min(lenh['rui_ro_that_pct'], 99.0)
                mp = {**mo_phong(r_that, ty_le_thang, rr), 'theo_rui_ro_that': r_that}
                lenh.update(thua_lien_mat_20=chuoi_thua_de_mat(r_that, 20), thua_lien_mat_50=chuoi_thua_de_mat(r_that, 50))
        else:
            thieu.append('chưa có giá trị bước giá của mã này')
    return {'ma': ma, 'goc': dt.get('goc', ma), 'chieu': chieu, 'khung': khung, 'vao': float(vao), 'bid': bid, 'ask': ask, 'so_le': so_le,
            'tien': tk_san.get('tien', 'USD'), 'nguon_von': nguon_von, 'don_bay': tk_san.get('don_bay'), 'dung_lenh_pct': tk_san.get('dung_lenh'),
            'lot_min': dt.get('lot_min'), 'von': kh, 'mo_phong': mp, 'muc': muc_gy, 'lenh': lenh, 'thieu': thieu}
