"""Thu thập báo giá một lần cho mỗi mã/khung đang xem, chia sẻ cho các kết nối."""
from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from math import isfinite
from threading import Condition, Thread
from typing import Callable


_LOG = logging.getLogger(__name__)
_THIEU = b'event: nguon-gia\ndata: {"trang_thai":"khong_co_du_lieu"}\n\n'
_GIU = b': giu\n\n'
Khoa = tuple[str | None, str]
DocGia = Callable[[dict, str, str | None], dict | None]


class QuaTai(RuntimeError):
    """Máy chủ đã đạt giới hạn luồng giá hoặc đang dừng."""


@dataclass
class _Kenh:
    cau_hinh: dict
    so_xem: int = 0
    doc_lai_luc: float = 0
    phien_ban: int = 0
    goi: bytes | None = None
    ms: int = -1
    nen: int = -1


def _so(x) -> bool:
    return type(x) in (int, float) and isfinite(x)


def _dong_goi(x: dict | None, ms_cu: int, nen_cu: int) -> tuple[bytes, int, int] | None:
    if not isinstance(x, dict):
        return None
    ms, bid, ask = (x.get(k) for k in ('ms', 'bid', 'ask'))
    if type(ms) is not int or ms < max(0, ms_cu) or not (_so(bid) and _so(ask) and 0 < bid <= ask):
        return None
    nen, vol = x.get('nen'), x.get('vol')
    t = nen_cu
    goi = {'ms': ms, 'bid': bid, 'ask': ask}
    if nen is not None:
        if not isinstance(nen, (tuple, list)) or len(nen) != 5 or not all(_so(v) for v in nen):
            return None
        t, mo, cao, thap, dong = nen
        if type(t) is not int or t < max(1, nen_cu) or not thap <= min(mo, dong) <= max(mo, dong) <= cao:
            return None
        goi['nen'] = nen
    if _so(vol) and vol >= 0:
        goi['vol'] = vol
    return b'data: ' + json.dumps(goi, separators=(',', ':')).encode('utf-8') + b'\n\n', ms, t


class LuongGia:
    """Một vòng đọc dùng chung trong mỗi máy chủ. Người xem chậm chỉ nhận trạng thái mới nhất."""

    def __init__(self, doc: DocGia, *, nhip: float = 0.008, giu: float = 5.0,
                 toi_da_kenh: int = 128, toi_da_xem: int = 256):
        self._doc = doc
        self._nhip, self._giu = nhip, giu
        self._toi_da_kenh, self._toi_da_xem = toi_da_kenh, toi_da_xem
        self._cho = Condition()
        self._kenh: dict[Khoa, _Kenh] = {}
        self._luong: Thread | None = None
        self._dong = False
        self._so_xem = self._so_doc = self._so_goi = 0

    @contextmanager
    def dang_ky(self, g: dict, tf: str, ma: str | None):
        khoa = ma, tf
        with self._cho:
            k = self._kenh.get(khoa)
            if self._dong or self._so_xem >= self._toi_da_xem or (k is None and len(self._kenh) >= self._toi_da_kenh):
                raise QuaTai
            if k is None:
                k = self._kenh[khoa] = _Kenh(g)
            k.so_xem += 1
            self._so_xem += 1
            if self._luong is None:
                self._luong = Thread(target=self._chay, name='thu-thap-gia-chart', daemon=True)
                self._luong.start()
            self._cho.notify_all()
        try:
            yield k
        finally:
            with self._cho:
                k.so_xem -= 1
                self._so_xem -= 1
                if not k.so_xem:
                    del self._kenh[khoa]
                self._cho.notify_all()

    def doi(self, k: _Kenh, cu: int, het_luc: float) -> tuple[int, bytes] | None:
        """Chờ có giá mới hoặc đến giờ kiểm tra kết nối. Không giữ khóa khi ghi mạng."""
        with self._cho:
            han = min(het_luc, time.monotonic() + self._giu)
            self._cho.wait_for(lambda: self._dong or k.phien_ban != cu, timeout=max(0, han - time.monotonic()))
            if self._dong or time.monotonic() >= het_luc:
                return None
            if k.phien_ban != cu and k.goi is not None:
                return k.phien_ban, k.goi
            return cu, _GIU

    def thong_ke(self) -> dict:
        with self._cho:
            return {'kenh': len(self._kenh), 'dang_xem': self._so_xem, 'lan_doc': self._so_doc,
                    'lan_phat': self._so_goi, 'kenh_thieu_du_lieu': sum(k.goi == _THIEU for k in self._kenh.values())}

    def dong(self) -> None:
        with self._cho:
            self._dong = True
            self._cho.notify_all()

    def _chay(self) -> None:
        while True:
            with self._cho:
                while not self._dong and not self._kenh:
                    self._cho.wait()
                if self._dong:
                    return
                khoa, k = min(self._kenh.items(), key=lambda p: p[1].doc_lai_luc)
                bat_dau = time.monotonic()
                con = k.doc_lai_luc - bat_dau
                if con > 0:
                    self._cho.wait(con)
                    continue
            ma, tf = khoa
            try:
                x = _dong_goi(self._doc(k.cau_hinh, tf, ma), k.ms, k.nen)
            except Exception:  # nguồn lỗi vẫn để các kênh khác tiếp tục chạy
                if k.goi != _THIEU:
                    _LOG.exception('Lỗi đọc nguồn giá chart')
                x = None
            with self._cho:
                self._so_doc += 1
                if self._kenh.get(khoa) is not k or self._dong:
                    continue
                k.doc_lai_luc = max(bat_dau + self._nhip, time.monotonic()) if x else time.monotonic() + 1
                if x:
                    goi, k.ms, k.nen = x
                else:
                    goi = _THIEU
                if goi != k.goi:
                    k.goi = goi
                    k.phien_ban += 1
                    self._so_goi += 1
                    self._cho.notify_all()
