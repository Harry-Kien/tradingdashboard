"""Giám sát rủi ro theo thời gian thực: mọi trang hỏi /api/giam-sat mỗi 30 giây, và hiện dải cảnh báo ngay dưới thanh điều hướng khi tài khoản
đang phạm quy tắc quản lý rủi ro của người dùng (cùng bộ quy tắc với Kiểm tra trước khi vào lệnh):
  ngay     lỗ đã chốt hôm nay (giờ VN) chạm giới hạn lỗ ngày                        đỏ
  khong_sl lệnh đang mở không có dừng lỗ                                            đỏ
  tong     tổng rủi ro mọi lệnh đang mở vượt mức                                    đỏ
  lon      một lệnh đang mở rủi ro vượt mức mỗi lệnh                                vàng
  gap      lệnh vừa mở trong 15 phút sau một lệnh thua                              vàng
  tin      sắp có tin mạnh (30 phút) của đồng tiền liên quan tới lệnh đang mở        vàng
CHỈ ĐỌC (tai_khoan.doc, lịch tin); không đặt, sửa hay đóng lệnh. `danh_gia` là hàm thuần; `doc` gom dữ liệu thật và nhớ 10 giây.
Mỗi cảnh báo có `id` ổn định để trang cho người dùng tắt riêng từng cái trong ngày."""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone

from .kiem_lenh import QUY_TAC_MAC_DINH, _so, _tien_lien_quan

_nho: dict = {}
_khoa = threading.Lock()


def _t(x) -> datetime:
    return x if isinstance(x, datetime) else datetime.fromisoformat(x)


def danh_gia(tk: dict, quy_tac: dict | None = None, now: datetime | None = None, tin: list[dict] | None = None,
             tien_cua_ma: dict | None = None) -> list[dict]:
    """tk: kết quả tai_khoan.doc (von, tien, rui_ro{tong,pct,khong_sl}, lenh[{ma,huong,lot,vao,sl,mo,nguon,rui_ro}], theo_ngay, da_dong).
    tin: tin mạnh [{t, tien, ten}]; tien_cua_ma: {ma: [mã tiền liên quan]} (thiếu thì đoán từ tên mã). Trả danh sách cảnh báo, nặng trước."""
    from .doc_so import VN                                                   # noqa: PLC0415
    q = {**QUY_TAC_MAC_DINH, **(quy_tac or {})}
    now = now or datetime.now(timezone.utc)
    von, tien = tk.get('von') or 0, tk.get('tien', 'USD')
    out: list[dict] = []

    def them(id_, muc, vi, en):
        out.append({'id': id_, 'muc': muc, 'vi': {'tieu': vi[0], 'noi': vi[1]}, 'en': {'tieu': en[0], 'noi': en[1]}})
    V, E = (lambda x, d=1: _so(x, d)), (lambda x, d=1: _so(x, d, True))
    hom_nay = now.astimezone(VN).date().isoformat()
    lenh = tk.get('lenh') or []

    # 1. lỗ hôm nay
    lo = next((x['lai'] for x in tk.get('theo_ngay') or [] if x.get('ngay') == hom_nay), 0) or 0
    if von > 0 and lo < 0:
        pct = -lo / (von - lo) * 100                                         # so với vốn đầu ngày (vốn hiện tại cộng lại phần đã lỗ)
        if pct >= q['lo_ngay_toi_da_pct']:
            them(f'ngay-{hom_nay}', 'xau', (f'Hôm nay đã lỗ {V(pct)}% vốn ({V(lo, 2)} {tien}): chạm giới hạn {V(q["lo_ngay_toi_da_pct"])}%',
                                             'Dừng giao dịch tới hết ngày. Vào thêm lệnh lúc đang lỗ là lúc dễ phá kỷ luật nhất.'),
                 (f'Down {E(pct)}% today ({E(lo, 2)} {tien}): daily limit of {E(q["lo_ngay_toi_da_pct"])}% reached',
                  'Stop trading for the rest of the day. Adding trades while down is when discipline breaks most easily.'))
    # 2, 4. từng lệnh đang mở
    for x in lenh:
        nhan = f'{x["ma"]} {"MUA" if x.get("huong") == "MUA" else "BÁN"} {x.get("lot")} lot'
        nhan_en = f'{x["ma"]} {"BUY" if x.get("huong") == "MUA" else "SELL"} {x.get("lot")} lots'
        khoa = f'{x["ma"]}-{x.get("mo")}'
        if not x.get('sl'):
            them(f'khong-sl-{khoa}', 'xau', (f'Lệnh {nhan} không có dừng lỗ', 'Rủi ro không giới hạn: một cú giật giá có thể xóa nhiều tuần lãi. Đặt dừng lỗ ngay trong MT5.'),
                 (f'{nhan_en} has no stop loss', 'Unlimited risk: one spike can wipe out weeks of profit. Set a stop loss in MT5 now.'))
        elif von > 0 and x.get('rui_ro') is not None and x['rui_ro'] / von * 100 > q['rui_ro_lenh_toi_da_pct']:
            pct = x['rui_ro'] / von * 100
            them(f'lon-{khoa}', 'chu_y', (f'Lệnh {nhan} rủi ro {V(pct)}% vốn, trên mức {V(q["rui_ro_lenh_toi_da_pct"])}% bạn đặt',
                                            f'Chạm dừng lỗ là mất {V(x["rui_ro"], 2)} {tien}. Cân nhắc giảm khối lượng hoặc dời dừng lỗ gần hơn ở lệnh sau.'),
                 (f'{nhan_en} risks {E(pct)}% of equity, above your {E(q["rui_ro_lenh_toi_da_pct"])}% limit',
                  f'Hitting the stop loses {E(x["rui_ro"], 2)} {tien}. Consider a smaller size or a closer stop next time.'))
    # 3. tổng rủi ro
    rr = tk.get('rui_ro') or {}
    if von > 0 and rr.get('tong') is not None and rr['tong'] / von * 100 > q['tong_rui_ro_toi_da_pct']:
        pct = rr['tong'] / von * 100
        them('tong', 'xau', (f'Tổng rủi ro đang mở {V(pct)}% vốn, trên mức {V(q["tong_rui_ro_toi_da_pct"])}%',
                             f'Mọi lệnh cùng chạm dừng lỗ thì mất {V(rr["tong"], 2)} {tien}. Không mở thêm lệnh cho tới khi tổng rủi ro giảm.'),
             (f'Total open risk is {E(pct)}% of equity, above {E(q["tong_rui_ro_toi_da_pct"])}%',
              f'If every stop is hit you lose {E(rr["tong"], 2)} {tien}. Do not open more trades until it comes down.'))
    # 5. vào gấp sau lệnh thua
    thua = [_t(d['luc']) for d in tk.get('da_dong') or [] if (d.get('lai') or 0) < 0]
    for x in lenh:
        if not x.get('mo'):
            continue
        mo = _t(x['mo'])
        truoc = [t for t in thua if t <= mo]
        if truoc and mo - max(truoc) <= timedelta(minutes=q['gap_sau_thua_phut']) and now - mo <= timedelta(hours=2):
            phut = round((mo - max(truoc)).total_seconds() / 60)
            them(f'gap-{x["ma"]}-{x["mo"]}', 'chu_y', (f'Lệnh {x["ma"]} mở {phut} phút sau một lệnh thua',
                                                      'Vào lại ngay sau khi thua thường là muốn gỡ, không theo kế hoạch. Kiểm lại lý do vào lệnh này.'),
                 (f'{x["ma"]} trade opened {phut} min after a loss', 'Jumping back in right after a loss is usually about winning it back, not the plan. Re-check why you took it.'))
    # 6. tin mạnh sắp ra khi đang giữ lệnh
    if tin and lenh:
        lien: dict[str, list[str]] = {}
        for x in lenh:
            for c in (tien_cua_ma or {}).get(x['ma']) or _doan_tien(x['ma']):
                lien.setdefault(c, []).append(x['ma'])
        for e in tin:
            t = _t(e['t'])
            if timedelta(0) <= t - now <= timedelta(minutes=q['tin_truoc_phut']) and e.get('tien') in lien:
                phut = round((t - now).total_seconds() / 60)
                ds = ', '.join(sorted(set(lien[e['tien']])))
                them(f'tin-{e["t"]}-{e["tien"]}', 'chu_y', (f'Tin mạnh {e["tien"]} sau {phut} phút: {e.get("ten", "")}',
                                                           f'Đang giữ lệnh {ds}. Quanh tin giá có thể giật qua dừng lỗ và spread giãn.'),
                     (f'High-impact {e["tien"]} news in {phut} min: {e.get("ten", "")}',
                      f'You hold {ds}. Around the news price can jump through stops and spreads widen.'))
    thu_tu = {'xau': 0, 'chu_y': 1}
    out.sort(key=lambda a: thu_tu[a['muc']])
    return out


def _doan_tien(ma: str) -> list[str]:
    """Mã tiền đoán từ tên mã khi không có thông số: 6 chữ đầu là cặp tiền (EURUSDp → EUR, USD); còn lại (vàng, chỉ số…) theo USD."""
    g = ''.join(ch for ch in ma.upper() if ch.isalpha())[:6]
    if len(g) == 6:
        return [g[:3], g[3:]]
    return ['USD']


def doc(cfg: dict, bang=None, quy_tac: dict | None = None, now: datetime | None = None) -> dict:
    """Cảnh báo cho tài khoản đang nối. Nhớ 10 giây theo bộ quy tắc (mọi tab cùng hỏi mỗi 30 giây)."""
    from . import tai_khoan, thi_truong                                       # noqa: PLC0415
    from .__main__ import HERE                                               # noqa: PLC0415
    q = {**(cfg.get('kiem_lenh') or {}), **(quy_tac or {})}
    k = tuple(sorted(q.items()))
    with _khoa:
        cu = _nho.get(k)
        if cu and time.monotonic() - cu[0] < 10:
            return cu[1]
    now = now or datetime.now(timezone.utc)
    try:
        tk = tai_khoan.doc(cfg, now=now, ngay=2)
    except Exception as e:                                                   # noqa: BLE001
        tk = {'san_sang': False, 'ly_do': str(e)}
    if not tk.get('san_sang'):
        kq = {'san_sang': False, 'ly_do': tk.get('ly_do'), 'ds': []}
    else:
        tin = None
        try:
            tin = [e for e in thi_truong.lich_tong(cfg, HERE, now, lui_gio=1, toi_ngay=1).get('ds', []) if e.get('muc') == 3]
        except Exception:                                                    # noqa: BLE001
            pass
        tien_cua_ma = {}
        if bang is not None:
            with bang._dk:
                for x in tk.get('lenh') or []:
                    dt = bang.dac_ta.get(x['ma'])
                    if dt:
                        tien_cua_ma[x['ma']] = _tien_lien_quan(dt, x['ma'])
        kq = {'san_sang': True, 'luc': now.isoformat(), 'ds': danh_gia(tk, q, now, tin, tien_cua_ma)}
    with _khoa:
        _nho[k] = (time.monotonic(), kq)
    return kq
