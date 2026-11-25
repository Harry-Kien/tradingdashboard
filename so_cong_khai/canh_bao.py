"""Cảnh báo khi một luật của chủ dự án ra tín hiệu trên nến VỪA ĐÓNG, hoặc 30 phút trước tin USD mạnh.

Cảnh báo chỉ hiện trong webapp (ô Cảnh báo, thông báo của trình duyệt, tiếng bíp). Mô-đun này không gửi tin nhắn đi đâu và
không đặt lệnh. Mỗi cảnh báo được ghi một lần vào sổ out/canh-bao.jsonl; cùng một nến và một luật thì không báo lại."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import gia, song
from .doc_so import VN

MOI_GIAY = 20 * 60            # nến đóng quá 20 phút thì coi là cũ, không báo (ví dụ khi chỉ có kho nến cập nhật mỗi giờ)
TRUOC_TIN_GIAY = 30 * 60
HUONG = {'BUY': 'MUA', 'SELL': 'BÁN', 'MUA': 'MUA', 'BAN': 'BÁN'}
GHI_CHU = 'Đây là tín hiệu của luật, chưa luật nào được chứng minh có lãi.'
_khoa_so = threading.Lock()


def _gia(x) -> str:
    return f'{x:,.2f}'.replace(',', '§').replace('.', ',').replace('§', '.') if isinstance(x, (int, float)) else '—'


def tim(luat: dict, now: datetime) -> list[dict]:
    """Từ kết quả gia.luat(), rút ra các cảnh báo ứng với nến vừa đóng. Hàm thuần: không đọc, không ghi."""
    res = []

    def vua_dong(nen_iso: str, phut: int) -> bool:
        dong = datetime.fromisoformat(nen_iso) + timedelta(minutes=phut)
        return 0 <= (now - dong).total_seconds() <= MOI_GIAY

    ne = bool((luat.get('tin') or {}).get('dang_ne'))        # trong 15 phút quanh tin USD mạnh, bot và các luật không vào lệnh: không báo
    for s in ([] if ne else luat.get('bot_tin_hieu') or []):
        if vua_dong(s['bar'], 5 if s['tf'] == 'M5' else 15):
            res.append({'khoa': f'bot|{s["tf"]}|{s["bar"]}|{s["side"]}', 'tieu_de': f'Luật bot: {HUONG.get(s["side"], s["side"])} trên {s["tf"]}',
                        'noi_dung': f'{s.get("reason") or ""} SL theo luật {_gia(s.get("sl"))}. {GHI_CHU}'.strip()})
    bk = luat.get('ba_khung') or {}
    if not ne and bk.get('quyet_dinh') in ('MUA', 'BAN') and bk.get('trong_gio') and bk.get('nen') and vua_dong(bk['nen'], 15):
        res.append({'khoa': f'ba_khung|{bk["nen"]}|{bk["quyet_dinh"]}', 'tieu_de': f'Luật ba khung: {HUONG[bk["quyet_dinh"]]}',
                    'noi_dung': f'D1, H4, H1 cùng chiều và nến M15 vừa đóng hồi ngược chiều đó. Luật cần thắng trên 80% số lệnh mới hòa vốn. {GHI_CHU}'})
    dd = luat.get('dinh_day') or {}
    if not ne and dd.get('hanh_dong') in ('MUA', 'BAN') and dd.get('nen') and vua_dong(dd['nen'], 15):
        res.append({'khoa': f'dinh_day|{dd["nen"]}|{dd["hanh_dong"]}', 'tieu_de': f'Luật đỉnh/đáy: {HUONG[dd["hanh_dong"]]}',
                    'noi_dung': f'{dd.get("ly_do") or ""} Giá vào {_gia(dd.get("gia_vao"))}, SL {_gia(dd.get("sl"))}, TP {_gia(dd.get("tp1"))}. {GHI_CHU}'.strip()})
    for t in (luat.get('tin') or {}).get('sap_toi') or []:
        dt = datetime.fromisoformat(t)
        if 0 < (dt - now).total_seconds() <= TRUOC_TIN_GIAY:
            res.append({'khoa': f'tin|{t}', 'tieu_de': 'Sắp có tin USD mạnh',
                        'noi_dung': f'Tin ra lúc {dt.astimezone(VN):%H:%M ngày %d/%m} (giờ Việt Nam). Bot và các luật của bạn né 15 phút trước và sau tin.'})
    return res


def _so(out: Path) -> Path:
    return out / 'canh-bao.jsonl'


def doc(out: Path, n: int = 30) -> list[dict]:
    """Các cảnh báo gần nhất, mới nhất đứng trước."""
    p = _so(out)
    if not p.exists():
        return []
    rows = [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
    return rows[-n:][::-1]


def ghi_moi(out: Path, alerts: list[dict], now: datetime) -> list[dict]:
    """Ghi các cảnh báo CHƯA có trong sổ (theo khóa) và trả về đúng các cảnh báo vừa ghi."""
    if not alerts:
        return []
    with _khoa_so:
        p = _so(out)
        old = [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()] if p.exists() else []
        seen = {r['khoa'] for r in old}
        nid = max((r['id'] for r in old), default=0)
        new = []
        for a in alerts:
            if a['khoa'] in seen:
                continue
            nid += 1
            seen.add(a['khoa'])
            new.append({'id': nid, 'luc': now.isoformat(), **a})
        if new:
            out.mkdir(parents=True, exist_ok=True)
            with p.open('a', encoding='utf-8') as f:
                f.write(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in new))
        return new


class VongCanh(threading.Thread):
    """Vòng canh chạy nền trong webapp: định kỳ tính lại các luật trên nến đã đóng và ghi cảnh báo mới. Chỉ đọc giá."""

    def __init__(self, nap_cau_hinh, out_fn, giay: float = 15):
        super().__init__(daemon=True, name='so-cong-khai-canh-bao')
        self.nap, self.out_fn, self.giay = nap_cau_hinh, out_fn, max(5.0, float(giay))
        self.dung = threading.Event()
        self.loi: str | None = None
        self.lan_cuoi: datetime | None = None
        self.nguon: str | None = None

    def mot_vong(self, now: datetime | None = None) -> list[dict]:
        cfg = self.nap()
        g = cfg['gia']
        now = now or datetime.now(timezone.utc)
        fr = song.khung_song(g) or gia.khung(g)
        new = ghi_moi(self.out_fn(cfg), tim(gia.luat(fr, g, now), now), now)
        self.lan_cuoi, self.nguon, self.loi = now, fr.get('nguon'), None
        return new

    def run(self) -> None:
        while not self.dung.is_set():
            try:
                self.mot_vong()
            except Exception as e:                                # noqa: BLE001 - một vòng hỏng không được làm chết vòng canh
                self.loi = f'{type(e).__name__}: {e}'
            self.dung.wait(self.giay)

    def trang_thai(self) -> dict:
        chay = self.is_alive() and not self.dung.is_set()
        ly_do = None
        if not chay:
            ly_do = 'Vòng canh chưa chạy.'
        elif self.loi:
            ly_do = f'Vòng canh gặp lỗi ở lượt gần nhất: {self.loi}'
        elif self.nguon != 'mt5':
            ly_do = 'Đang không có giá trực tiếp từ MT5, nên cảnh báo luật có thể trễ tới một giờ hoặc không báo.'
        return {'dang_chay': chay, 'ly_do': ly_do, 'lan_cuoi': self.lan_cuoi.isoformat() if self.lan_cuoi else None, 'nguon': self.nguon}
