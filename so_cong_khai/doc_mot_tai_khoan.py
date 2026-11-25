"""Đọc MỘT tài khoản MT5 đang mở ở một đường dẫn, CHỈ ĐỌC, rồi ngắt.

Chạy như một tiến trình riêng (`python -m so_cong_khai.doc_mot_tai_khoan <đường dẫn terminal64.exe> [số ngày]`) để không đụng phiên MT5 chính mà
webapp đang dùng cho giá trực tiếp. In ra đúng một dòng JSON.

Chốt an toàn (giữ nguyên của so_cong_khai.noi_mt5.noi):
- không bao giờ tự mở MT5: chỉ nối khi thấy đúng một MT5 đang chạy ở đường dẫn đó và cửa sổ chính của nó đang hiện; nếu thư viện lỡ tự mở một MT5
  khác thì ngắt và đóng cái vừa mở;
- không nhập, không đọc, không lưu mật khẩu: tài khoản phải được chủ dự án tự đăng nhập sẵn trong MT5 đó;
- chỉ gọi các hàm đọc (account_info, positions_get, history_deals_get, history_orders_get) và hàm tính thuần order_calc_profit; không có lời gọi
  đặt, sửa hay đóng lệnh nào;
- đọc được cả tài khoản tiền thật (chủ dự án đồng ý ngày 25/11/2026: "Cả tài khoản thật"), vẫn chỉ đọc; số tài khoản được che, chỉ để ba chữ số cuối,
  tên chủ tài khoản không được đọc ra.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone

from . import hieu_suat as HS, noi_mt5

LOAI = {0: 'DEMO', 1: 'THI ĐẤU', 2: 'TIỀN THẬT'}


def _r(x, d: int = 2):
    try:
        return round(float(x), d)
    except (TypeError, ValueError):
        return None


def doc_tu(mt5, duong: str, ngay: int = 90, now: datetime | None = None, procs_fn=noi_mt5.tien_trinh, window_fn=noi_mt5.co_cua_so,
           sleep=time.sleep) -> dict:
    """Nối (an toàn) vào MT5 ở `duong`, đọc tài khoản, lệnh đang mở và lịch sử `ngay` ngày, tính thắng thua và lãi lỗ, rồi ngắt."""
    now = now or datetime.now(timezone.utc)
    d, ly_do = noi_mt5.noi(mt5, {'terminal': duong, 'chi_demo': False}, procs_fn, window_fn, sleep)
    if ly_do:
        return {'ok': False, 'ly_do': ly_do}
    try:
        a = mt5.account_info()
        if a is None:
            return {'ok': False, 'ly_do': 'MT5 không trả thông tin tài khoản; hãy đăng nhập trong MT5.'}
        mode = int(getattr(a, 'trade_mode', -1))
        buy = getattr(mt5, 'ORDER_TYPE_BUY', 0)
        sell = getattr(mt5, 'ORDER_TYPE_SELL', 1)

        def lo_neu_cham(ma, mua, lot, vao, sl):
            v = mt5.order_calc_profit(buy if mua else sell, ma, float(lot), float(vao), float(sl))
            return -float(v) if v is not None and v < 0 else (0.0 if v is not None else None)
        lenh_mo, rui, khong_sl, khong_tinh = [], 0.0, 0, 0
        for p in mt5.positions_get() or []:
            mua = int(p.type) == 0
            rr = None
            if p.sl:
                try:
                    rr = lo_neu_cham(p.symbol, mua, p.volume, p.price_open, p.sl)
                except Exception:                                            # noqa: BLE001
                    rr = None
                if rr is None:
                    khong_tinh += 1
                else:
                    rui += rr
            else:
                khong_sl += 1
            lenh_mo.append({'ma': p.symbol, 'huong': 'MUA' if mua else 'BAN', 'lot': _r(p.volume, 3), 'vao': _r(p.price_open, 5), 'sl': _r(p.sl, 5) or None,
                            'tp': _r(p.tp, 5) or None, 'lai': _r(p.profit), 'rui_ro': _r(rr)})
        tu = now - timedelta(days=ngay)
        deals = list(mt5.history_deals_get(tu, now + timedelta(days=1)) or [])
        orders = list(mt5.history_orders_get(tu, now + timedelta(days=1)) or [])

        def rui_ro(ma, chieu, lot, vao, sl):
            v = mt5.order_calc_profit(buy if chieu == 'mua' else sell, ma, float(lot), float(vao), float(sl))
            return -float(v) if v is not None and v < 0 else None
        lenh, nap = HS.ghep_lenh(deals, orders, lambda m: 'Đặt tay' if not m else f'EA {m}', rui_ro)
        so_du, von = float(a.balance), float(a.equity)
        kq = HS.phan_tich(lenh, HS.von_dau(so_du, lenh, nap), a.currency) if lenh else None
        return {'ok': True, 'luc': now.isoformat(), 'so_ngay': ngay,
                'tai_khoan': {'so': '•••' + str(a.login)[-3:], 'may_chu': a.server, 'loai': LOAI.get(mode, 'KHÁC'), 'that': mode == 2, 'tien': a.currency,
                              'don_bay': int(getattr(a, 'leverage', 0) or 0)},
                'so_du': _r(so_du), 'von': _r(von), 'treo': _r(a.profit), 'ky_quy': _r(a.margin), 'ky_quy_con': _r(a.margin_free),
                'muc_ky_quy': _r(a.margin_level, 1) if a.margin else None, 'lenh_mo': lenh_mo,
                'rui_ro': {'tong': _r(rui), 'pct': _r(rui / von * 100, 2) if von > 0 else None, 'khong_sl': khong_sl, 'khong_tinh': khong_tinh},
                'tong': (kq or {}).get('tong'), 'ngay': (kq or {}).get('ngay', [])[-30:],
                'gan_day': [{k: x.get(k) for k in ('ma', 'chieu', 'lot', 'vao', 'ra', 'dong', 'rong', 'r', 'nguon')} for x in lenh[-10:]][::-1]}
    finally:
        mt5.shutdown()


if __name__ == '__main__':
    import MetaTrader5 as _mt5                                               # noqa: N813 - chỉ nạp khi chạy thật, bài kiểm dùng MT5 giả
    duong_ = sys.argv[1] if len(sys.argv) > 1 else ''
    ngay_ = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    try:
        kq_ = doc_tu(_mt5, duong_, ngay_) if duong_ else {'ok': False, 'ly_do': 'thiếu đường dẫn MT5'}
    except Exception as e:                                                   # noqa: BLE001
        kq_ = {'ok': False, 'ly_do': f'{type(e).__name__}: {e}'}
    print(json.dumps(kq_, ensure_ascii=False, default=str))
