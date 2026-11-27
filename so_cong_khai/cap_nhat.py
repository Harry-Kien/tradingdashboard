"""Kiểm và tải bản cập nhật của app (chỉ chạy ở bản đóng gói). Không có giao diện, không có đường dẫn web: chỉ logic.

Mỗi ngày tối đa một lần, app đọc một tệp kê khai nhỏ (JSON) ở địa chỉ https cố định. Có phiên bản mới hơn thì nhớ lại trong
du-lieu/cap-nhat.json để giao diện báo; người dùng bấm tải thì bộ cài về cap-nhat/ và phải khớp SHA-256 trong kê khai, không khớp là xóa.
App không tự chạy bộ cài. Chỉ nhận địa chỉ https (kể cả khi bị chuyển hướng); kê khai hỏng hay lỗi mạng chỉ ghi lỗi, không ném.
Ghi trạng thái theo kiểu tệp tạm rồi thay, như cai_dat.ghi."""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import urllib.request
from pathlib import Path

from . import duong
from .phien_ban import PHIEN_BAN, hop_le, moi_hon

KE_KHAI = 'https://harry-kien.github.io/tradingdashboard/app/ban-moi.json'
TOI_DA_KE_KHAI = 65536                              # byte: kê khai thật chỉ vài trăm byte, lớn hơn là bất thường
TOI_DA_BO_CAI = 300 * 1024 * 1024                   # byte
CHU_KY_GIAY = 86400
HAN_MANG = 10                                       # giây, cho tệp kê khai
MAC_DINH = {'dia_chi': KE_KHAI, 'lan_kiem': None, 'ban_moi': None, 'loi': None, 'dang_tai': False}
_SHA256 = re.compile(r'[0-9a-fA-F]{64}')

_khoa = threading.Lock()
_dang_tai = threading.Lock()                        # giữ suốt lúc tải bộ cài: vừa chặn tải đồng thời, vừa là nguồn của `dang_tai`


def _la_https(dia_chi) -> bool:
    return isinstance(dia_chi, str) and dia_chi.startswith('https://')


def doc_ke_khai(du_lieu: bytes) -> dict | None:
    """Kê khai đã kiểm {'phien_ban', 'tai', 'sha256', 'ghi_chu', 'ke_khai_moi'}, hoặc None nếu sai bất kỳ điều kiện nào."""
    if not isinstance(du_lieu, (bytes, bytearray)) or len(du_lieu) > TOI_DA_KE_KHAI:
        return None
    try:
        d = json.loads(bytes(du_lieu).decode('utf-8'))
    except ValueError:                                                     # gồm cả UnicodeDecodeError và JSONDecodeError
        return None
    if not isinstance(d, dict):
        return None
    pb, tai, sha, ghi_chu = d.get('phien_ban'), d.get('tai'), d.get('sha256'), d.get('ghi_chu', '')
    if not hop_le(pb) or not _la_https(tai) or not isinstance(sha, str) or not _SHA256.fullmatch(sha) or not isinstance(ghi_chu, str):
        return None
    moi = d.get('ke_khai_moi')
    return {'phien_ban': pb, 'tai': tai, 'sha256': sha.lower(), 'ghi_chu': ghi_chu[:500], 'ke_khai_moi': moi if _la_https(moi) else None}


def nen_kiem(now: float, lan_kiem: float | None) -> bool:
    """Chưa kiểm lần nào hoặc đã qua một ngày."""
    if lan_kiem is None or isinstance(lan_kiem, bool) or not isinstance(lan_kiem, (int, float)):
        return True                                                         # giá trị lạ trong tệp trạng thái: coi như chưa kiểm
    return lan_kiem > now or now - lan_kiem >= CHU_KY_GIAY                  # lần kiểm ở tương lai (đồng hồ từng sai) cũng không chặn


def _tep(goc: Path | None) -> Path:
    return (goc or duong.goc_du_lieu()) / 'du-lieu' / 'cap-nhat.json'


def trang_thai(goc: Path | None = None) -> dict:
    """Trạng thái đã lưu (mặc định nếu chưa có hoặc tệp hỏng). Bản mới đã bằng hay thấp hơn bản đang chạy (vừa cập nhật xong) thì bỏ."""
    tt = dict(MAC_DINH)
    tt['dang_tai'] = _dang_tai.locked()                                     # trạng thái của tiến trình này, không đọc từ tệp (chết giữa chừng không kẹt)
    try:
        d = json.loads(_tep(goc).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return tt
    if isinstance(d, dict):
        tt.update({k: d[k] for k in MAC_DINH if k in d and k != 'dang_tai'})
    lk = tt['lan_kiem']
    if isinstance(lk, bool) or not isinstance(lk, (int, float)) or lk != lk or lk in (float('inf'), float('-inf')):
        tt['lan_kiem'] = None
    bm = tt['ban_moi']
    if not isinstance(bm, dict) or not moi_hon(bm.get('phien_ban'), PHIEN_BAN):
        tt['ban_moi'] = None
    if not _la_https(tt['dia_chi']):
        tt['dia_chi'] = KE_KHAI
    return tt


def _ghi(goc: Path | None, **doi) -> dict:
    """Gộp `doi` vào trạng thái rồi ghi tệp tạm và thay (không bao giờ để tệp dở dang). Trả trạng thái mới."""
    with _khoa:
        tt = {**trang_thai(goc), **doi}
        tt.pop('dang_tai', None)                                            # chỉ là trạng thái tiến trình, không bao giờ ghi xuống tệp
        p = _tep(goc)
        p.parent.mkdir(parents=True, exist_ok=True)
        tam = p.with_name(p.name + '.tam')
        tam.write_text(json.dumps(tt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(tam, p)
    return tt


class _ChiHttps(urllib.request.HTTPRedirectHandler):
    """Không theo chuyển hướng sang địa chỉ không phải https."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _la_https(newurl):
            raise ValueError('chuyển hướng tới địa chỉ không phải https')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _mo(dia_chi: str, han: float):
    """Mở kết nối https (đã kiểm ở nơi gọi)."""
    rq = urllib.request.Request(dia_chi, headers={'User-Agent': 'HarryGoldResearch-capnhat/1'})   # noqa: S310 - địa chỉ đã kiểm là https, chỉ tải về
    return urllib.request.build_opener(_ChiHttps).open(rq, timeout=han)     # noqa: S310 - địa chỉ đã kiểm là https, chuyển hướng cũng chỉ https


def _tai_ke_khai(dia_chi: str) -> bytes:
    """Tải tệp kê khai (mặc định của `kiem`): chỉ https, hạn 10 giây, đọc không quá TOI_DA_KE_KHAI + 1 byte."""
    if not _la_https(dia_chi):
        raise ValueError('địa chỉ kê khai phải là https')
    with _mo(dia_chi, HAN_MANG) as r:
        return r.read(TOI_DA_KE_KHAI + 1)


def _tai_tep(dia_chi: str, dich: Path, toi_da: int) -> None:
    """Tải bộ cài về `dich` theo từng khúc (mặc định của `tai_bo_cai`): chỉ https; vượt `toi_da` byte thì ném lỗi."""
    if not _la_https(dia_chi):
        raise ValueError('địa chỉ tải phải là https')
    tong = 0
    with _mo(dia_chi, 30) as r, open(dich, 'wb') as f:
        while True:
            khuc = r.read(1024 * 1024)
            if not khuc:
                return
            tong += len(khuc)
            if tong > toi_da:
                raise ValueError(f'tệp lớn hơn {toi_da // (1024 * 1024)} MB')
            f.write(khuc)


def kiem(cfg: dict, goc: Path | None = None, now: float | None = None, tai=None, ep: bool = False) -> dict:
    """Kiểm kê khai nếu được phép. Trả trạng thái; không bao giờ ném.
    Chạy từ mã nguồn thì không bao giờ kiểm. Bản đóng gói: lượt tự kiểm (ep=False) chỉ chạy khi chưa tắt trong cấu hình (cap_nhat.bat)
    và đã qua một ngày. `ep=True` là nút "Kiểm ngay": người dùng tự hỏi nên bỏ qua cả hạn một ngày lẫn ô tắt (ô đó chỉ tắt việc TỰ kiểm)."""
    if not duong.DONG_GOI:
        return trang_thai(goc)
    cau = cfg.get('cap_nhat') if isinstance(cfg, dict) else None
    if not ep and isinstance(cau, dict) and cau.get('bat') is False:        # không có mục này thì coi như bật
        return trang_thai(goc)
    now = time.time() if now is None else now
    tt = trang_thai(goc)
    if not ep and not nen_kiem(now, tt['lan_kiem']):
        return tt
    tai = tai or _tai_ke_khai
    try:
        ke = doc_ke_khai(tai(tt['dia_chi']))
    except Exception as e:                                                  # noqa: BLE001 - mọi lỗi mạng chỉ ghi lại, lượt sau (hôm sau) thử lại
        return _ghi(goc, lan_kiem=now, loi=f'Không kiểm được bản mới: {type(e).__name__}: {e}'[:300])
    if ke is None:
        return _ghi(goc, lan_kiem=now, loi='Tệp kê khai bản mới không hợp lệ.')
    doi = {'lan_kiem': now, 'loi': None, 'ban_moi': None}
    if moi_hon(ke['phien_ban'], PHIEN_BAN):
        doi['ban_moi'] = {k: ke[k] for k in ('phien_ban', 'tai', 'sha256', 'ghi_chu')}
    if ke['ke_khai_moi']:
        doi['dia_chi'] = ke['ke_khai_moi']
    return _ghi(goc, **doi)


def tai_bo_cai(goc: Path | None = None, tai=None) -> tuple[bool, str, Path | None]:
    """Tải bộ cài của `ban_moi` vào <gốc dữ liệu>/cap-nhat/ rồi so SHA-256. Trả (thành công, lý do lỗi, đường dẫn).
    Tải vào <tên>.part; chỉ khi mã băm khớp mới đổi tên thành <tên>.exe, nên tên cuối chỉ có tệp đã kiểm trong chính lần gọi này (tệp
    cũ cùng tên bị xóa trước khi tải). Không khớp, lỗi hay quá lớn thì xóa .part. Đang có một lần tải khác thì trả lỗi ngay, không đụng tệp nào."""
    if not _dang_tai.acquire(blocking=False):
        return False, 'Đang tải bản mới, vui lòng chờ.', None
    try:
        bm = trang_thai(goc)['ban_moi']
        if not bm or not hop_le(bm.get('phien_ban')) or not _la_https(bm.get('tai')) or not _SHA256.fullmatch(str(bm.get('sha256'))):
            return False, 'Chưa có bản mới để tải.', None
        thu_muc = (goc or duong.goc_du_lieu()) / 'cap-nhat'
        dich = thu_muc / f'HarryGoldResearch-Setup-{bm["phien_ban"]}.exe'
        tam = dich.with_name(dich.name + '.part')
        tai = tai or _tai_tep
        try:
            thu_muc.mkdir(parents=True, exist_ok=True)
            dich.unlink(missing_ok=True)
            tam.unlink(missing_ok=True)
            tai(bm['tai'], tam, TOI_DA_BO_CAI)
            if tam.stat().st_size > TOI_DA_BO_CAI:
                raise ValueError('tệp quá lớn')
            bam = hashlib.sha256()
            with open(tam, 'rb') as f:
                for khuc in iter(lambda: f.read(1024 * 1024), b''):
                    bam.update(khuc)
            if bam.hexdigest() != bm['sha256'].lower():
                tam.unlink(missing_ok=True)
                return False, 'Tệp tải về không khớp mã kiểm. Đã xóa.', None
            os.replace(tam, dich)
            return True, '', dich
        except Exception as e:                                              # noqa: BLE001 - lỗi mạng hay đĩa: xóa tệp dở dang, báo lý do
            tam.unlink(missing_ok=True)
            return False, f'Không tải được bản cập nhật: {type(e).__name__}: {e}'[:300], None
    finally:
        _dang_tai.release()
