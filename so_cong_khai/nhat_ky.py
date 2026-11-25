"""Nhật ký điểm vào: sổ ghi tiến của các điểm vào mà hệ thống đã nêu.

Mỗi khi một phương án CÒN HIỆU LỰC xuất hiện (luật trong sổ hoặc phương pháp tùy chọn), nhật ký ghi lại đúng lúc đó: mã, phương pháp, chiều,
giá vào, dừng lỗ, các mức chốt lời, bối cảnh. Mức giá được chốt lúc ghi và không sửa lại nữa. Về sau mỗi dòng được theo dõi bằng nến 5 phút:
lệnh chờ có khớp không, rồi chạm chốt lời hay dừng lỗ trước. Vì ghi trước khi biết kết quả, đây là bằng chứng không thể chỉnh cho đẹp.

Quy tắc chấm (giống phần chạy lại): giá Bid; lệnh MUA khớp và lệnh BÁN thoát theo Ask = Bid + spread; một nến chạm cả dừng lỗ lẫn chốt lời
thì tính dừng lỗ; giữ tối đa 24 giờ. Mức chốt lời dùng để chấm thắng/thua: mức xa nhất (2R) với phương pháp tùy chọn, mức đầu tiên với
luật trong sổ. Chỉ ghi và đọc tệp trong máy; không đặt lệnh.

Phương pháp tùy chọn theo đúng thứ tự của phép chạy lại (phuong_phap.cham): mỗi (mã, phương pháp) mỗi lúc một lệnh. Tín hiệu mới đến lúc
lệnh chờ cũ chưa khớp thì dòng cũ đóng với trạng thái 'thay' (trang Biểu đồ cũng chỉ còn hiện tín hiệu mới); tín hiệu đến lúc lệnh trước đã
khớp và còn mở thì không ghi. Luật trong sổ của chủ dự án giữ cách ghi riêng theo từng chiều.

Từ ngày 24/11/2026 nhật ký ghi thêm PHIẾU VÀO LỆNH (so_cong_khai/phieu.py) của mỗi phương pháp tùy chọn như một dòng riêng, mã 'phieu:<phương pháp>',
nhóm 'phieu', cùng quy tắc mỗi lúc một lệnh. Dòng của luật gốc vẫn được ghi như cũ, nên hai cách vào lệnh được giá thật chấm song song. Phiếu có
ba loại lệnh ('loai'): 'tt' vào ngay, 'gh' chờ giới hạn, 'dung' chờ dừng (khớp khi Ask vượt mức với lệnh mua, Bid thủng mức với lệnh bán). Giới hạn:
lệnh chờ dừng được chấm ở đúng mức đã ghi, kể cả khi nến mở cửa nhảy qua mức đó (thực tế sẽ khớp xấu hơn một chút).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from . import da_ma, gia, phuong_phap, song
from .__main__ import HERE

SONG = ('cho_khop', 'dang_mo')            # hai trạng thái "còn sống"
TOI_DA = 10000                             # số dòng giữ trong tệp chính; dòng cũ hơn chuyển sang tệp lưu trữ, không xóa
SAO_LUU_GIU = 30                           # số bản sao lưu hằng ngày giữ lại
_khoa = threading.Lock()
# Chuỗi dấu (từ đêm 25/11/2026): mỗi điểm vào mới mang 'bam' = SHA-256 của dấu dòng trước nối với nội dung tín hiệu lúc ghi. Sửa, xóa hay chèn
# một tín hiệu cũ đều làm gãy chuỗi. Kết quả về sau (tt, r, ra, khop…) không nằm trong dấu vì được chấm lại từ giá.
KHOA_DAU = ('id', 'luc', 'sym', 'ma', 'nhom', 'huong', 'loai', 'kieu', 'vao', 'sl', 'tp', 'nen', 'het_han')
TT: dict = {}                               # trạng thái vòng ghi nền, để phần tự kiểm tra của webapp đọc


def tep(cfg: dict) -> Path:
    nk = cfg.get('nhat_ky') or {}
    if nk.get('tep'):
        return Path(os.path.expandvars(nk['tep']))
    base = Path(cfg.get('thu_muc_ra', 'out'))
    base = base if base.is_absolute() else HERE / base
    return base.parent / 'du-lieu' / 'nhat-ky-diem-vao.json'


class NhatKyKhongDocDuoc(RuntimeError):
    """Tệp nhật ký có đó nhưng lúc này không đọc được (đang bị chương trình khác khóa…). Bên gọi bỏ lượt này; KHÔNG được coi như rỗng."""


def _doc(p: Path) -> list[dict]:
    """Đọc nhật ký. Chưa có tệp: rỗng. Không đọc được: báo lỗi để không ai ghi đè. Tệp hỏng: giữ một bản `<tên>.hong-<giờ sửa>.json` rồi lấy
    bản sao lưu hằng ngày gần nhất còn đọc được (không có thì rỗng; bản hỏng vẫn còn đó)."""
    if not p.exists():
        return []
    try:
        van = p.read_text(encoding='utf-8')
    except OSError as e:
        raise NhatKyKhongDocDuoc(f'Không đọc được tệp nhật ký lúc này ({type(e).__name__}: {e}); bỏ lượt này, không ghi đè.') from e
    try:
        ds = json.loads(van)
        if isinstance(ds, list):
            return ds
    except ValueError:
        pass
    try:
        hong = p.with_name(f'{p.stem}.hong-{datetime.fromtimestamp(p.stat().st_mtime):%Y%m%d-%H%M%S}.json')
        if not hong.exists():
            shutil.copy2(p, hong)
        TT['su_co'] = f'Tệp nhật ký bị hỏng; đã giữ bản hỏng ở {hong.name} và lấy lại từ bản sao lưu gần nhất.'
    except OSError:
        pass
    for b in sorted((p.parent / 'sao-luu').glob(f'{p.stem}-*.json'), reverse=True):
        try:
            ds = json.loads(b.read_text(encoding='utf-8'))
            if isinstance(ds, list):
                return ds
        except (OSError, ValueError):
            continue
    return []


def _sao_luu(p: Path) -> None:
    """Trước lần ghi đầu tiên của mỗi ngày: chép tệp đang có sang sao-luu/<tên>-YYYYMMDD.json. Giữ SAO_LUU_GIU bản mới nhất."""
    try:
        if not p.exists():
            return
        thu_muc = p.parent / 'sao-luu'
        dich = thu_muc / f'{p.stem}-{datetime.now():%Y%m%d}.json'
        if dich.exists():
            return
        json.loads(p.read_text(encoding='utf-8'))                    # không sao lưu một tệp đang hỏng đè lên chuỗi bản tốt
        thu_muc.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dich)
        for cu in sorted(thu_muc.glob(f'{p.stem}-*.json'), reverse=True)[SAO_LUU_GIU:]:
            cu.unlink()
    except (OSError, ValueError):
        pass                                                          # sao lưu hỏng không được chặn việc ghi nhật ký


def _luu(p: Path, ds: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    _sao_luu(p)
    if len(ds) > TOI_DA:                                              # dòng cũ nhất chuyển sang tệp lưu trữ (mỗi dòng một JSON), không bao giờ xóa
        with (p.parent / f'{p.stem}-luu-tru.jsonl').open('a', encoding='utf-8') as f:
            f.writelines(json.dumps(x, ensure_ascii=False) + '\n' for x in ds[:-TOI_DA])
    tam = p.with_suffix('.tmp')
    tam.write_text(json.dumps(ds[-TOI_DA:], ensure_ascii=False), encoding='utf-8')
    tam.replace(p)                                                # thay tệp một bước: không bao giờ để lại tệp ghi dở


def _dau(truoc: str | None, rec: dict) -> str:
    noi = json.dumps({k: rec.get(k) for k in KHOA_DAU}, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(((truoc or '') + '|' + noi).encode('utf-8')).hexdigest()


def kiem_chuoi(ds: list[dict]) -> dict:
    """Kiểm chuỗi dấu theo thứ tự các dòng. Dòng không có dấu đứng TRƯỚC dòng có dấu đầu tiên là dòng ghi trước khi có chuỗi (đếm riêng); dòng
    không có dấu chen vào sau đó, hoặc dấu không khớp, là chuỗi hỏng. Trả {'ok', 'so_dong', 'chua_dau', 'bam_cuoi', 'hong_id'}."""
    truoc, so, chua, bat_dau = None, 0, 0, False
    for x in ds:
        if not x.get('bam'):
            if bat_dau:
                return {'ok': False, 'so_dong': so, 'chua_dau': chua, 'bam_cuoi': truoc, 'hong_id': x.get('id')}
            chua += 1
            continue
        bat_dau = True
        if x.get('bam_truoc') != truoc or _dau(truoc, x) != x['bam']:
            return {'ok': False, 'so_dong': so, 'chua_dau': chua, 'bam_cuoi': truoc, 'hong_id': x.get('id')}
        truoc, so = x['bam'], so + 1
    return {'ok': True, 'so_dong': so, 'chua_dau': chua, 'bam_cuoi': truoc, 'hong_id': None}


def kiem_chuoi_tep(p: Path) -> dict:
    """Kiểm chuỗi trên cả tệp lưu trữ (dòng cũ đã chuyển ra) và tệp chính, đúng thứ tự."""
    ds = []
    luu = p.parent / f'{p.stem}-luu-tru.jsonl'
    if luu.exists():
        ds += [json.loads(d) for d in luu.read_text(encoding='utf-8').splitlines() if d.strip()]
    if p.exists():
        ds += json.loads(p.read_text(encoding='utf-8'))
    return kiem_chuoi(ds)


def _mh_ban() -> int:
    from . import mo_hinh                                                 # noqa: PLC0415 - nạp muộn để tránh vòng nạp
    return mo_hinh.PHIEN_BAN


TRUNG_PHUT = 30                    # hai phương án cùng một luật, cùng chiều, cùng giá vào và dừng lỗ, cách nhau dưới chừng này phút: là một lệnh


def _goc(ma: str) -> str | None:
    """Tên luật của một phương án nhiều nhánh ('bot:nen' → 'bot'); None nếu không phải (phương pháp tùy chọn, phiếu)."""
    return ma.split(':', 1)[0] if ':' in ma and not ma.startswith('phieu:') else None


def _cung_lenh(a: dict, b: dict) -> bool:
    """Hai dòng là CÙNG một lệnh của hai phương án khác nhau của một luật."""
    g = _goc(a['ma'])
    return (g is not None and a['ma'] != b['ma'] and _goc(b['ma']) == g and a['sym'] == b['sym'] and a['huong'] == b['huong']
            and abs(float(a['vao']) - float(b['vao'])) < 1e-9 and abs(float(a['sl']) - float(b['sl'])) < 1e-9
            and abs((datetime.fromisoformat(a['luc']) - datetime.fromisoformat(b['luc'])).total_seconds()) < TRUNG_PHUT * 60)


def danh_dau_trung(ds: list[dict]) -> list[dict]:
    """Gắn 'trung_voi' (id dòng gốc) cho dòng là cùng một lệnh với một dòng ghi trước nó (hai phương án của cùng một luật). Không xóa dòng nào."""
    for i, x in enumerate(ds):
        x.pop('trung_voi', None)
        if _goc(x.get('ma', '')):
            y = next((y for y in ds[:i] if not y.get('trung_voi') and _cung_lenh(x, y)), None)
            if y is not None:
                x['trung_voi'] = y['id']
    return ds


def ghi(cfg: dict, pt: dict, now: datetime | None = None) -> list[dict]:
    """Ghi các phương án còn hiệu lực trong kết quả phân tích `pt` mà nhật ký chưa có. Trả các dòng vừa ghi.
    Mỗi (mã, phương pháp, chiều) chỉ có một dòng còn sống; tín hiệu của cùng một nến không ghi hai lần. Với phương pháp tùy chọn, tín hiệu
    của một nến mới hơn thay lệnh chờ cũ chưa khớp, và bị bỏ nếu lệnh trước (chiều nào cũng vậy) đã khớp và còn mở."""
    if not (cfg.get('nhat_ky') or {}).get('bat'):
        return []
    now = now or datetime.now(timezone.utc)
    sym = pt.get('ma') or da_ma.ma_vang(cfg)
    bc = pt.get('boi_canh') or {}
    moi = []
    with _khoa:
        p = tep(cfg)
        ds = _doc(p)
        phieu = []                                                 # phiếu còn hiệu lực của từng phương pháp, đưa về cùng dạng với một phương án
        for x in list(pt.get('phuong_an') or []) + list(pt.get('phuong_phap') or []):     # phiếu của luật bot nằm ở phương án 'bot:nen'
            f = x.get('phieu')
            if f and f.get('trang_thai') == 'con_hieu_luc':
                phieu.append({'ma': 'phieu:' + f['ma'], 'ten': 'Phiếu · ' + f.get('ten', f['ma']), 'nhom': 'phieu', 'co': True, 'hieu_luc': True, 'huong': f['huong'],
                              'kieu': f.get('ten_loai', ''), 'loai': f.get('loai'), 'vao': f['vao'], 'sl': f['sl'], 'tp': f['tp'], 'rr': f.get('rr'),
                              'nen': f.get('nen'), 'con_phut': f.get('con_phut'), 'ly_do': f.get('ly_do', ''), 'i_chinh': f.get('i_chinh')})
        for pa in list(pt.get('phuong_an') or []) + list(pt.get('phuong_phap') or []) + phieu:
            if not (pa.get('co') and pa.get('hieu_luc')) or pa.get('sl') is None or not pa.get('tp'):
                continue
            cung = [x for x in ds if x['sym'] == sym and x['ma'] == pa['ma'] and x['huong'] == pa['huong']]
            if pa.get('nhom') in ('pp', 'phieu') and pa.get('nen') and not any(x.get('nen') == pa['nen'] for x in cung):
                nen_moi = datetime.fromisoformat(pa['nen'])
                truoc = [x for x in ds if x['sym'] == sym and x['ma'] == pa['ma'] and x['tt'] in SONG and x.get('nen')
                         and datetime.fromisoformat(x['nen']) < nen_moi]
                if any(x['tt'] == 'dang_mo' for x in truoc):
                    continue                                       # lệnh trước của phương pháp này đã khớp và còn mở: mỗi lúc một lệnh
                for x in truoc:                                    # lệnh chờ cũ chưa khớp: tín hiệu mới thay nó
                    x.update(tt='thay', ra=now.isoformat(), thay_boi=(ds[-1]['id'] + 1) if ds else 1)
            if any(x['tt'] in SONG for x in cung):
                continue                                           # điểm vào trước của phương pháp này còn sống
            if pa.get('nen') and any(x.get('nen') == pa['nen'] for x in cung):
                continue                                           # tín hiệu của nến này đã ghi rồi
            if not pa.get('nen') and any((now - datetime.fromisoformat(x['luc'])) < timedelta(minutes=30) for x in cung):
                continue                                           # luật trong sổ không báo nến tín hiệu: không ghi lại trong 30 phút
            if any(_cung_lenh({'ma': pa['ma'], 'sym': sym, 'huong': pa['huong'], 'vao': pa['vao'], 'sl': pa['sl'], 'luc': now.isoformat()}, x) for x in ds):
                continue                                           # phương án khác của cùng luật đã ghi đúng lệnh này: không đếm đôi
            cho = pa.get('con_phut') is not None
            rec = {'id': (ds[-1]['id'] + 1) if ds else 1, 'luc': now.isoformat(), 'sym': sym, 'ma': pa['ma'], 'ten': pa.get('ten', pa['ma']),
                   'nhom': pa.get('nhom') or 'luat', 'huong': pa['huong'], 'kieu': pa.get('kieu', ''), 'vao': pa['vao'], 'sl': pa['sl'],
                   'tp': list(pa['tp']), 'rr': list(pa.get('rr') or []), 'muc_tieu': (pa.get('muc_tieu') or {}).get('gia'), 'nen': pa.get('nen'),
                   'cho': cho, 'loai': pa.get('loai'), 'i_chinh': pa.get('i_chinh'), 'het_han': (now + timedelta(minutes=int(pa['con_phut']))).isoformat() if cho else None,
                   'so_le': pt.get('so_le', 2), 'gia': pt.get('bid'), 'phien': bc.get('phien'), 'bien_do': bc.get('bien_do'), 'ly_do': pa.get('ly_do', ''), 'mo_hinh': (pa.get('mo_hinh') or {}).get('hang'),
                   'mh_ban': _mh_ban() if (pa.get('mo_hinh') or {}).get('hang') is not None else None,
                   'tt': 'cho_khop' if cho else 'dang_mo', 'khop': None if cho else now.isoformat(), 'ra': None, 'r': None, 'cham_tp1': None}
            rec['bam_truoc'] = next((x['bam'] for x in reversed(ds) if x.get('bam')), None)
            rec['bam'] = _dau(rec['bam_truoc'], rec)
            ds.append(rec)
            moi.append(rec)
        if moi:
            _luu(p, ds)
    return moi


def cap_nhat(rec: dict, bars: pd.DataFrame, sp: float) -> bool:
    """Theo dõi một dòng còn sống bằng nến 5 phút đã đóng (`bars`, chỉ số là giờ mở nến). Đổi `rec` tại chỗ; trả True nếu có đổi."""
    if rec['tt'] not in SONG or bars is None or not len(bars):
        return False
    luc = pd.Timestamp(rec['luc'])
    b = bars[bars.index >= luc.ceil('5min')]                      # chỉ dùng nến mở SAU lúc ghi
    if not len(b):
        return False
    mua = rec['huong'] == 'MUA'
    dau = 1.0 if mua else -1.0
    vao, sl, tps = float(rec['vao']), float(rec['sl']), [float(t) for t in rec['tp']]
    rui = (vao - sl) * dau
    if rui <= 0:
        rec.update(tt='huy', ra=luc.isoformat())
        return True
    i_chinh = len(tps) - 1 if rec.get('nhom') in ('pp', 'phieu') else 0       # mức chốt lời dùng để chấm thắng/thua
    if rec.get('i_chinh') is not None:                              # phiếu của luật bot: chấm theo TP1 như lệnh gốc của bot
        i_chinh = int(rec['i_chinh'])
    chinh = tps[i_chinh]
    r_chinh = (rec.get('rr') or [])[i_chinh] if len(rec.get('rr') or []) > i_chinh else (chinh - vao) * dau / rui
    T = b.index
    H, L, C = (b[k].to_numpy(dtype=float) for k in ('high', 'low', 'close'))
    O = b['open'].to_numpy(dtype=float) if 'open' in b.columns else None
    truoc = (rec['tt'], rec.get('cham_tp1'))
    dong = lambda k: (T[k] + pd.Timedelta(minutes=5)).isoformat()                # noqa: E731 - giờ nến k đóng
    k0 = 0
    if rec['tt'] == 'cho_khop':
        het = pd.Timestamp(rec['het_han'])
        k0 = None
        for k in range(len(T)):
            if T[k] >= het:
                rec.update(tt='khong_khop', ra=het.isoformat())
                break
            if rec.get('loai') == 'dung':                          # lệnh chờ dừng: khớp khi giá đi TIẾP qua mức
                khop = (H[k] + sp >= vao) if mua else (L[k] <= vao)
            else:                                                  # lệnh chờ giới hạn: khớp khi giá quay VỀ mức
                khop = (L[k] + sp <= vao) if mua else (H[k] >= vao)
            thung = (L[k] <= sl) if mua else (H[k] + sp >= sl)
            if thung and not khop:
                rec.update(tt='huy', ra=dong(k))                   # chạm dừng lỗ trước khi kịp khớp: lệnh chờ bị hủy
                break
            if khop:
                rec.update(tt='dang_mo', khop=dong(k))
                if thung:                                          # cùng một nến vừa khớp vừa thủng dừng lỗ
                    rec.update(tt='thua', ra=dong(k), r=-1.0)
                k0 = k + 1
                break
        if k0 is None or rec['tt'] != 'dang_mo':
            return (rec['tt'], rec.get('cham_tp1')) != truoc
    else:
        khop = pd.Timestamp(rec['khop'])
        k0 = int(T.searchsorted(khop.ceil('5min'), side='left')) if rec.get('cho') else 0
    het_gio = pd.Timestamp(rec['khop']) + pd.Timedelta(minutes=phuong_phap.GIU_PHUT)
    for k in range(k0, len(T)):
        if T[k] >= het_gio:
            ra = C[k - 1] if k > 0 else vao
            rec.update(tt='het_gio', ra=het_gio.isoformat(), r=round(((ra if mua else ra + sp) - vao) * dau / rui, 2))
            break
        if (L[k] <= sl) if mua else (H[k] + sp >= sl):
            gia_ra = sl
            if k > 0 and O is not None:                            # nến mở cửa đã nhảy qua dừng lỗ: thoát ở giá mở, lỗ hơn 1R
                gia_ra = min(sl, O[k]) if mua else max(sl, O[k] + sp)
            rec.update(tt='thua', ra=dong(k), r=round((gia_ra - vao) * dau / rui, 2))
            break
        if rec.get('cham_tp1') is None and ((H[k] >= tps[0]) if mua else (L[k] + sp <= tps[0])):
            rec['cham_tp1'] = dong(k)
        if (H[k] >= chinh) if mua else (L[k] + sp <= chinh):
            rec.update(tt='thang', ra=dong(k), r=round(float(r_chinh), 2))
            break
    return (rec['tt'], rec.get('cham_tp1')) != truoc


def _nen_m5(cfg: dict, sym: str, tu: datetime, now: datetime):
    """(nến 5 phút đã đóng từ `tu`, spread theo giá). MT5 đang mở thì đọc từ MT5 (chỉ đọc nến); vàng còn có kho nến của webapp."""
    g = cfg['gia']
    mt5 = da_ma._mt5(g)
    if mt5 is not None:
        n = max(300, min(40_000, int((now - tu).total_seconds() // 300) + 20))
        with song._khoa:
            if sym in da_ma._hien(mt5):
                bars = da_ma._nen(mt5, sym, 'M5', n)
                tick = mt5.symbol_info_tick(sym)
                sp = float(tick.ask - tick.bid) if tick and tick.ask and tick.bid else 0.0
                return bars, max(sp, 0.0)
    if sym == da_ma.ma_vang(cfg):
        return gia.khung(g)['M5'], float(g.get('spread', 0.17))
    return None, 0.0


def xem(cfg: dict, now: datetime | None = None, nen=None) -> dict:
    """Nhật ký sau khi đã cập nhật các dòng còn sống: {'ds': mới nhất trước, 'tom': tổng kết theo mã và phương pháp}."""
    now = now or datetime.now(timezone.utc)
    nen = nen or (lambda sym, tu: _nen_m5(cfg, sym, tu, now))
    loi = []
    with _khoa:
        p = tep(cfg)
        ds = _doc(p)
        doi = False
        for sym in sorted({x['sym'] for x in ds if x['tt'] in SONG}):
            song_ds = [x for x in ds if x['sym'] == sym and x['tt'] in SONG]
            try:
                bars, sp = nen(sym, min(datetime.fromisoformat(x['luc']) for x in song_ds))
            except Exception as e:                                             # noqa: BLE001 - không đọc được nến thì để nguyên, lần sau chấm
                loi.append(f'{sym}: {type(e).__name__}: {e}')
                continue
            for x in song_ds:
                doi = cap_nhat(x, bars, sp) or doi
        if doi:
            _luu(p, ds)
    danh_dau_trung(ds)                                            # dòng trùng ghi trước bản sửa 24/11/2026: giữ trong tệp, không đếm
    tom: dict = {}
    for x in ds:
        if x.get('trung_voi'):
            continue
        t = tom.setdefault((x['sym'], x['ma']), {'sym': x['sym'], 'ma': x['ma'], 'ten': x['ten'], 'n': 0, 'song': 0, 'thang': 0, 'thua': 0, 'khac': 0, 'tong_r': 0.0})
        t['n'] += 1
        t['song'] += x['tt'] in SONG
        t['thang'] += x['tt'] == 'thang'
        t['thua'] += x['tt'] == 'thua'
        t['khac'] += x['tt'] in ('het_gio', 'khong_khop', 'huy', 'thay')
        t['tong_r'] = round(t['tong_r'] + (x.get('r') or 0.0), 2)
    nhom: dict = {}                                               # theo nhóm điểm mô hình: để giá thật trả lời điểm cao có tốt hơn không
    ban = _mh_ban()                                               # chỉ tính dòng do bản mô hình HIỆN TẠI chấm: bản trước 23/11/2026 học trên đặc trưng rò rỉ
    for x in ds:
        if x.get('trung_voi') or x.get('mo_hinh') is None or x.get('mh_ban') != ban:
            continue
        t = nhom.setdefault('cao' if x['mo_hinh'] >= 90 else 'thap', {'n': 0, 'song': 0, 'thang': 0, 'thua': 0, 'khac': 0, 'tong_r': 0.0})
        t['n'] += 1
        t['song'] += x['tt'] in SONG
        t['thang'] += x['tt'] == 'thang'
        t['thua'] += x['tt'] == 'thua'
        t['khac'] += x['tt'] in ('het_gio', 'khong_khop', 'huy', 'thay')
        t['tong_r'] = round(t['tong_r'] + (x.get('r') or 0.0), 2)
    try:
        chuoi = kiem_chuoi_tep(p)
    except (OSError, ValueError) as e:
        chuoi = {'ok': False, 'loi': f'{type(e).__name__}: {e}'}
    return {'bat': bool((cfg.get('nhat_ky') or {}).get('bat')), 'ma_vang': da_ma.ma_vang(cfg), 'theo_mo_hinh': nhom, 'luc': now.isoformat(), 'chuoi': chuoi, 'ds': ds[::-1][:300], 'tom': list(tom.values()), 'loi': loi}


class VongGhi(threading.Thread):
    """Vòng nền của máy chủ: cứ `giay` giây chấm các dòng còn sống, rồi chạy phần phân tích cho vàng và các mã trong cấu hình và ghi điểm vào
    mới, để nhật ký không phụ thuộc vào việc có ai đang mở trang hay không. Phải chấm trước khi ghi: một dòng đã xong mà chưa được chấm thì
    vẫn bị coi là còn sống và chặn điểm vào mới của cùng phương pháp."""

    def __init__(self, doc_cfg, giay: int = 60):
        super().__init__(name='nhat-ky', daemon=True)
        self.doc_cfg, self.giay, self.dung = doc_cfg, max(20, int(giay)), threading.Event()
        self.tt = TT
        TT.update(lan=0, luc=None, loi=None, da_ghi=0, bat_dau=datetime.now(timezone.utc).isoformat())

    def mot_lan(self) -> None:
        from . import phan_tich                                               # noqa: PLC0415 - nạp muộn để tránh vòng nạp
        cfg = self.doc_cfg()
        nk = cfg.get('nhat_ky') or {}
        if not nk.get('bat'):
            return
        loi = []
        try:
            loi += list(xem(cfg).get('loi') or [])
        except Exception as e:                                                 # noqa: BLE001 - chấm hỏng thì vẫn ghi điểm vào mới
            loi.append(f'chấm dòng còn sống: {type(e).__name__}: {e}')
        for ma in [''] + [m for m in nk.get('ma', []) if m and m != da_ma.ma_vang(cfg)]:
            try:
                pt = da_ma.phan_tich(cfg, ma) if ma else phan_tich.phan_tich(cfg)
                self.tt['da_ghi'] += len(ghi(cfg, pt))
            except Exception as e:                                             # noqa: BLE001 - một mã hỏng không chặn mã khác
                loi.append(f'{ma or "vàng"}: {type(e).__name__}: {e}')
        if self.tt.get('su_co'):
            loi.append(self.tt.pop('su_co'))
        self.tt.update(lan=self.tt['lan'] + 1, luc=datetime.now(timezone.utc).isoformat(), loi='; '.join(loi) or None)

    def run(self) -> None:
        time.sleep(5)
        while not self.dung.is_set():
            try:
                self.mot_lan()
            except Exception as e:                                             # noqa: BLE001
                self.tt['loi'] = f'{type(e).__name__}: {e}'
            self.dung.wait(self.giay)
