"""Tình trạng hệ thống: soát từng nguồn dữ liệu và từng bộ phận của webapp, để chuyện hỏng âm thầm (lịch tin hết hạn, kho nến đứng,
nhật ký EA ngừng ghi, sổ đứt chuỗi, MT5 mất nối) tự hiện ra thay vì chỉ được phát hiện khi số liệu đã sai.

Mỗi mục có một mức: 'tot', 'chu_y' (vẫn chạy nhưng nên xem) hoặc 'loi' (một phần của trang đang thiếu hoặc sai), kèm việc nên làm.
Mốc để biết một nguồn có "đứng" hay không là thời điểm giá gần nhất (giá trực tiếp từ MT5, không có thì kho nến), nên cuối tuần
không báo nhầm. Chỉ đọc; không sửa gì."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import ai_hoi, gia, hoc, kiem_chung, song
from .doc_so import VN

CHAM_EA_GIO = 6            # nhật ký EA cũ hơn giá gần nhất chừng này giờ thì coi là đứng
CHAM_KHO_PHUT = 120        # kho nến chậm hơn giá trực tiếp chừng này phút thì coi là đứng
LICH_CON_NGAY = 7          # lịch tin còn phủ ít hơn chừng này ngày thì nhắc
COT_CU_NGAY = 17           # báo cáo COT mới nhất cũ hơn chừng này ngày thì nhắc (bình thường tối đa khoảng 11 ngày)


def _gio(t: datetime | None) -> str:
    return t.astimezone(VN).strftime('%H:%M ngày %d/%m') if t else 'chưa có'


def _khoang(giay: float) -> str:
    m = int(abs(giay) // 60)
    return f'{m} phút' if m < 90 else f'{m // 60} giờ' if m < 48 * 60 else f'{m // 1440} ngày'


def muc_cot(cfg: dict, now: datetime) -> dict | None:
    """Mục tình trạng của phần vị thế COT; None nếu phần này chưa bật trong cấu hình. Gọi mục này cũng là lúc webapp xét có cần tải báo cáo mới."""
    from . import cot                                                      # noqa: PLC0415 - nạp muộn, mô-đun này không bắt buộc
    r = cot.lay(cfg, now)
    if not r.get('bat'):
        return None
    ten, t, loi = 'Vị thế COT (CFTC)', r.get('tom'), r.get('loi')
    lam = 'Webapp tự thử lại sau vài giờ. Nếu kéo dài: kiểm tra mạng, hoặc CFTC đang chậm công bố (ngày lễ ở Mỹ).'
    if not t:
        return {'ten': ten, 'muc': 'chu_y', 'chi_tiet': 'Đang tải lần đầu từ cftc.gov.' if r.get('dang_tai') and not loi else f'Chưa có dữ liệu. {loi or ""}'.strip(), 'lam': lam}
    ngay = f'{t["ngay"][8:]}/{t["ngay"][5:7]}'
    if t['tuoi_ngay'] > COT_CU_NGAY:
        return {'ten': ten, 'muc': 'chu_y', 'chi_tiet': f'Báo cáo mới nhất chốt ngày {ngay}, đã {t["tuoi_ngay"]} ngày.' + (f' Lần tải gần nhất lỗi: {loi}' if loi else ''), 'lam': lam}
    return {'ten': ten, 'muc': 'tot', 'chi_tiet': f'Báo cáo mới nhất chốt ngày {ngay}; đang giữ {r["tuan"]} tuần.' + (f' Lần tải gần nhất lỗi: {loi}' if loi else ''), 'lam': ''}


def kiem(cfg: dict, out: Path, d: dict | None = None, vong: dict | None = None, now: datetime | None = None) -> dict:
    """`d`: kết quả gom() toàn bộ sổ (None thì tự gom). `vong`: trạng thái vòng canh cảnh báo. Trả {'muc': [...], 'dem': {...}}."""
    now = now or datetime.now(timezone.utc)
    g = cfg.get('gia') or {}
    muc: list[dict] = []

    def them(ten: str, cap: str, chi_tiet: str, lam: str = '') -> None:
        muc.append({'ten': ten, 'muc': cap, 'chi_tiet': chi_tiet, 'lam': lam})

    # ---- giá: MT5 trực tiếp và kho nến
    fr_song = fr_kho = None
    try:
        fr_song = song.khung_song(g)
    except Exception as e:                                                 # noqa: BLE001
        them('Giá trực tiếp từ MT5', 'loi', f'{type(e).__name__}: {e}')
    chia_se = gia.ban_chia_se(g)
    if g.get('kho_m1') or not chia_se:                                     # bản chia sẻ không cần kho nến: mọi nến lấy thẳng từ MT5
        try:
            fr_kho = gia.khung(g)
        except Exception as e:                                             # noqa: BLE001
            them('Kho nến 1 phút', 'loi', f'Không đọc được: {type(e).__name__}: {e}', 'Kiểm tra đường dẫn gia.kho_m1 trong cau-hinh.json.')
    if fr_song is not None:
        tt = song.thong_tin()
        san = (f' Mã vàng {tt["ma"]}; giờ máy chủ của sàn lệch UTC {tt["lech_gio"]:+g} giờ ({tt["lech_nguon"]}), mọi giờ trên trang đã đổi về UTC.'
               if tt.get('ma') else '')
        them('Giá trực tiếp từ MT5', 'tot', f'Đang nối MT5. Giá gần nhất lúc {_gio(fr_song["het"])}, cách đây {_khoang((now - fr_song["het"]).total_seconds())}.' + san)
    elif not any(m['ten'] == 'Giá trực tiếp từ MT5' for m in muc):
        bat = (g.get('mt5') or {}).get('bat')
        them('Giá trực tiếp từ MT5', 'chu_y' if bat else 'tot', (f'Chưa nối được: {song.ly_do()}.' if bat else 'Đang tắt trong cấu hình; trang dùng kho nến.'),
             'Mở MT5 demo ở đường dẫn đã khai rồi chờ một phút. Khi chưa nối, trang dùng kho nến và các mã ngoài vàng không đọc được.' if bat else '')
    moc = fr_song['het'] if fr_song is not None else (fr_kho['het'] if fr_kho is not None else None)       # thời điểm giá gần nhất
    if fr_kho is not None:
        cham = (fr_song['het'] - fr_kho['het']).total_seconds() / 60 if fr_song is not None else 0
        if cham > CHAM_KHO_PHUT:
            them('Kho nến 1 phút', 'chu_y', f'Nến cuối lúc {_gio(fr_kho["het"])}, chậm hơn giá trực tiếp {_khoang(cham * 60)}.',
                 'Kho nến do vòng chạy bóng của EA Promax ghi mỗi giờ; vòng đó có thể đang tắt. Kiểm chứng lịch sử sẽ thiếu phần mới nhất.')
        else:
            them('Kho nến 1 phút', 'tot', f'Nến cuối lúc {_gio(fr_kho["het"])}.')

    # ---- mã luật của dự án
    try:
        if gia._nap_ma(g)[2] is None:
            them('Luật vào lệnh', 'tot', 'Bản chia sẻ: không có luật riêng của ai; biểu đồ, chỉ báo và các phương pháp tùy chọn tính theo ATR chạy trên dữ liệu MT5 của bạn.')
        else:
            them('Mã luật của dự án', 'tot', 'Nạp được các luật của bot, luật ba khung, luật đỉnh/đáy.')
    except Exception as e:                                                 # noqa: BLE001
        them('Mã luật của dự án', 'loi', f'Không nạp được: {type(e).__name__}: {e}', 'Kiểm tra gia.ma_nguon trong cau-hinh.json. Thiếu phần này thì không có phân tích và cảnh báo.')

    # ---- các sổ
    if d is None:
        from .__main__ import gan_doi_chieu, gom                           # noqa: PLC0415 - nạp muộn, tránh vòng nạp
        d = gan_doi_chieu(cfg, gom(cfg), now)
    for ten, err in d.get('loi', []):
        them(ten, 'loi', f'Không đọc được sổ: {err}', 'Kiểm tra đường dẫn của sổ này trong cau-hinh.json.')
    for acc in d.get('tai_khoan', []):
        for ten, err in acc.get('loi', []):
            them(f'Nhật ký {ten}', 'loi', f'Không đọc được: {err}', 'Kiểm tra đường dẫn tệp nhật ký của EA này trong cau-hinh.json.')
        e = acc.get('tom')
        if not e:
            continue
        cuoi = e.get('last_time')
        if cuoi and moc and (moc - cuoi) > timedelta(hours=CHAM_EA_GIO):
            them(f'Nhật ký EA: {acc["ten"]}', 'chu_y', f'Sự kiện cuối lúc {_gio(cuoi)}, trước giá gần nhất {_khoang((moc - cuoi).total_seconds())}.',
                 'EA hoặc MT5 của tài khoản này có thể đã tắt. Số liệu trên trang dừng ở thời điểm đó.')
        else:
            them(f'Nhật ký EA: {acc["ten"]}', 'tot', f'Sự kiện cuối lúc {_gio(cuoi)}.')
        if e.get('orphans'):
            dc = acc.get('doi_chieu')
            if dc and dc.get('khop'):
                them(f'Đối chiếu MT5: {acc["ten"]}', 'chu_y', f'Nhật ký của EA thiếu dòng đóng của {len(e["orphans"])} lệnh; lịch sử MT5 có đủ và vốn đã khớp.',
                     'Lỗi nằm ở phần ghi nhật ký của EA; nên xem lại trong dự án EA Promax.')
            else:
                them(f'Đối chiếu: {acc["ten"]}', 'chu_y', f'{len(e["orphans"])} lệnh vào không có dòng đóng trong nhật ký, chưa đối chiếu được với MT5.',
                     'Tài khoản này nằm ở MT5 khác với MT5 webapp đang nối, hoặc MT5 chưa mở.')
    b = d.get('bot')
    if b is not None:
        cuoi = max((r['opened'] for r in b['rows']), default=None)
        them('Sổ của bot tín hiệu', 'tot', f'{b["n"]} lệnh đã gọi, lệnh gần nhất lúc {_gio(cuoi)}.')
    for khoa, ten in (('xu_huong', 'Sổ chạy bóng luật ba khung'), ('dinh_day', 'Sổ chạy bóng luật đỉnh/đáy')):
        x = d.get(khoa)
        if x is None:
            continue
        if not x.get('chain_ok', True):
            them(ten, 'loi', f'Chuỗi liên kết của sổ bị đứt ({x.get("n_lines")} dòng): có dòng đã bị sửa hoặc mất.', 'Không dùng số liệu của sổ này cho tới khi tìm ra dòng hỏng.')
        else:
            them(ten, 'tot', f'{x.get("n_lines")} dòng, chuỗi liên kết liền mạch.')

    # ---- lịch tin
    if g.get('lich_tin'):
        try:
            from ai import snapshot as SN                                  # noqa: PLC0415
            tin, phu = gia.tin_usd(g)
            if phu is None:
                them('Lịch tin USD', 'loi', 'Không đọc được tệp lịch tin.', 'Thiếu lịch tin thì trang không biết lúc nào cần né tin.')
            else:
                con = (phu - now).total_seconds() / 86400
                toi = sum(1 for t in tin if t > now)
                if con < 0:
                    them('Lịch tin USD', 'loi', f'Lịch đã hết từ {_gio(phu)}. Trang đang không biết tin nào sắp ra.',
                         'Xuất lại tệp lịch từ MT5 theo hướng dẫn của dự án EA Promax. Cho tới lúc đó, phần "né tin" và cảnh báo trước tin không hoạt động.')
                elif con < LICH_CON_NGAY:
                    them('Lịch tin USD', 'chu_y', f'Lịch chỉ còn phủ tới {_gio(phu)} (còn {con:.0f} ngày), {toi} tin USD mức cao sắp tới.',
                         'Xuất lại tệp lịch từ MT5 trước ngày đó, nếu không phần "né tin" sẽ lặng lẽ ngừng hoạt động.')
                else:
                    them('Lịch tin USD', 'tot', f'Lịch phủ tới {_gio(phu)}, {toi} tin USD mức cao sắp tới.')
        except Exception as e:                                             # noqa: BLE001
            them('Lịch tin USD', 'loi', f'{type(e).__name__}: {e}')

    # ---- vị thế COT của vàng tương lai
    try:
        m = muc_cot(cfg, now)
        if m:
            muc.append(m)
    except Exception as e:                                                 # noqa: BLE001
        them('Vị thế COT (CFTC)', 'chu_y', f'{type(e).__name__}: {e}')

    # ---- các bộ phận của webapp
    if vong is not None:
        if vong.get('dang_chay') and not vong.get('ly_do'):
            them('Vòng canh cảnh báo', 'tot', 'Đang chạy.')
        else:
            them('Vòng canh cảnh báo', 'chu_y', vong.get('ly_do') or 'Chưa chạy.', 'Cảnh báo chỉ đầy đủ khi webapp đang mở và MT5 demo đang nối.')
    try:
        st = ai_hoi.trang_thai(cfg, out, now)
        if st['chan']:
            them('Hỏi AI', 'chu_y', 'Nút Hỏi AI đang khóa: ' + ' '.join(st['chan']), 'Không ảnh hưởng tới phần phân tích theo luật.')
        else:
            tien = f'{st["da_tieu_usd"]:.2f}/{st["ngan_sach_usd"]:.2f}'.replace('.', ',')
            them('Hỏi AI', 'tot', f'Sẵn sàng. Hôm nay đã hỏi {st["hom_nay"]}/{st["moi_ngay"]} lượt, đã dùng {tien} USD.')
    except Exception as e:                                                 # noqa: BLE001
        them('Hỏi AI', 'chu_y', f'{type(e).__name__}: {e}')
    for ten, mo, tep in (('Kiểm chứng 4 tháng', kiem_chung, kiem_chung._tep(out)), ('Dữ liệu nhiều năm', hoc, hoc._tep(out))):
        if chia_se:                                                        # bản chia sẻ: hai phần này đo luật riêng trên kho nến nhiều năm
            if mo is kiem_chung:
                continue
            them(ten, 'tot', 'Bản chia sẻ: phần học chạy trên nến 5 phút của từng mã lấy thẳng từ MT5, khi bạn bấm Phân tích điểm vào.')
            continue
        tt = mo._tt
        if tt.get('loi'):
            them(ten, 'loi', f'Lần tính gần nhất bị lỗi: {tt["loi"]}', 'Khởi động lại webapp để tính lại.')
        elif tt.get('dang'):
            them(ten, 'tot', 'Đang tính ở nền.')
        elif tt.get('kq') is not None or tep.exists():
            luc = datetime.fromtimestamp(tep.stat().st_mtime, timezone.utc) if tep.exists() else None
            them(ten, 'tot', f'Đã có kết quả, tính lúc {_gio(luc)}.' if luc else 'Đã có kết quả.')
        else:
            them(ten, 'tot', 'Chưa tính; sẽ tính khi bạn bấm Phân tích điểm vào.')
    # ---- hai bộ phận chạy nền: nhật ký điểm vào và mô hình
    try:
        from . import mo_hinh, nhat_ky                                         # noqa: PLC0415 - nạp muộn, hai mô-đun này không bắt buộc
        if (cfg.get('nhat_ky') or {}).get('bat'):
            tt, n = nhat_ky.TT, len(nhat_ky._doc(nhat_ky.tep(cfg)))
            if tt.get('loi'):
                them('Nhật ký điểm vào', 'chu_y', f'Vòng ghi gặp lỗi ở lần gần nhất: {tt["loi"]}', 'Kiểm tra MT5 còn mở không; vòng ghi tự thử lại mỗi phút.')
            elif tt.get('luc'):
                them('Nhật ký điểm vào', 'tot', f'Vòng ghi đang chạy, lần gần nhất lúc {_gio(datetime.fromisoformat(tt["luc"]))}; đã ghi {n} điểm vào.')
            elif tt.get('bat_dau'):
                them('Nhật ký điểm vào', 'tot', f'Vòng ghi vừa khởi động; đã ghi {n} điểm vào.')
            else:
                them('Nhật ký điểm vào', 'chu_y', f'Vòng ghi nền không chạy trong tiến trình này; đã ghi {n} điểm vào.', 'Chạy webapp bằng CHAY_WEBAPP.bat để nhật ký ghi cả khi không mở trang.')
            ch = nhat_ky.kiem_chuoi_tep(nhat_ky.tep(cfg))                    # chuỗi dấu băm: bằng chứng không ai sửa tín hiệu cũ
            if ch['ok']:
                them('Chuỗi dấu nhật ký', 'tot', f"{ch['so_dong']} điểm vào nối chuỗi nguyên vẹn" + (f" (thêm {ch['chua_dau']} dòng ghi trước khi có chuỗi)" if ch['chua_dau'] else '')
                     + (f"; dấu mới nhất {ch['bam_cuoi'][:16]}…" if ch['bam_cuoi'] else '') + '.')
            else:
                them('Chuỗi dấu nhật ký', 'loi', f"Chuỗi gãy ở dòng {ch.get('hong_id')}: một điểm vào đã ghi bị sửa, xóa hoặc chèn.",
                     'Xem bản sao lưu trong du-lieu/sao-luu để biết dòng nào bị đổi; chạy python -X utf8 cong-cu/kiem_chuoi_nhat_ky.py.')
        elif 'nhat_ky' in cfg:
            them('Nhật ký điểm vào', 'chu_y', 'Đang tắt trong cấu hình.', 'Đặt "nhat_ky": {"bat": true} trong cau-hinh.json nếu muốn ghi lại các điểm vào.')
        if (cfg.get('mo_hinh') or {}).get('bat'):
            mt, tep_mh = mo_hinh._tt, mo_hinh._tep(cfg)
            if mt.get('loi'):
                them('Mô hình chấm điểm', 'chu_y', f'Lần huấn luyện gần nhất bị lỗi: {mt["loi"]}', 'Khởi động lại webapp để huấn luyện lại; thiếu scikit-learn thì mô hình không chạy được.')
            elif mt.get('dang'):
                them('Mô hình chấm điểm', 'tot', 'Đang huấn luyện ở nền.')
            elif mt.get('kq') is not None or tep_mh.exists():
                them('Mô hình chấm điểm', 'tot', f'Đã huấn luyện, tệp lưu lúc {_gio(datetime.fromtimestamp(tep_mh.stat().st_mtime, timezone.utc))}.' if tep_mh.exists() else 'Đã huấn luyện.')
            else:
                them('Mô hình chấm điểm', 'tot', 'Chưa huấn luyện; sẽ huấn luyện khi trang vàng chạy phân tích lần đầu trong ngày.')
    except Exception as e:                                                     # noqa: BLE001 - phần tự kiểm tra không được tự làm hỏng mình
        them('Nhật ký và mô hình', 'chu_y', f'Không đọc được trạng thái: {type(e).__name__}: {e}', '')
    try:                                                                       # đo lại trên dữ liệu mới: nhắc khi lâu chưa chạy hoặc có luật đang lỗ rõ
        tep = Path(__file__).resolve().parent.parent / 'out' / 'du-lieu-moi.json'
        if tep.exists():
            kq = json.loads(tep.read_text(encoding='utf-8'))
            tuoi = (now - datetime.fromisoformat(kq['luc'])).days
            xau = [x['ten'] for x in kq.get('muc', []) if x.get('ket') == 'lo_ro' or x.get('kem_ky_vong')]
            if xau:
                them('Đo lại trên dữ liệu mới', 'chu_y', f'{len(xau)} luật đang lỗ rõ hoặc kém kỳ vọng rõ trên giá mới: ' + '; '.join(xau[:4]) + '.',
                     'Xem bảng ở trang Kiến thức. Đừng chỉnh luật theo số này; muốn đổi thì ghi mục đăng ký mới trước.')
            elif tuoi > 35:
                them('Đo lại trên dữ liệu mới', 'chu_y', f'Đã {tuoi} ngày chưa đo lại.', 'Chạy DO_LAI_DU_LIEU_MOI.bat (khoảng 1 phút).')
            else:
                them('Đo lại trên dữ liệu mới', 'tot', f"Đo lần gần nhất {tuoi} ngày trước, trên {kq.get('so_ngay', 0)} ngày giá mới.")
        else:
            them('Đo lại trên dữ liệu mới', 'chu_y', 'Chưa chạy lần nào.', 'Chạy DO_LAI_DU_LIEU_MOI.bat khoảng mỗi tháng.')
    except Exception as e:                                                     # noqa: BLE001
        them('Đo lại trên dữ liệu mới', 'chu_y', f'Không đọc được kết quả: {type(e).__name__}: {e}')
    dem = {k: sum(m['muc'] == k for m in muc) for k in ('tot', 'chu_y', 'loi')}
    muc.sort(key=lambda m: {'loi': 0, 'chu_y': 1, 'tot': 2}[m['muc']])
    return {'luc': now.isoformat(), 'dem': dem, 'muc': muc}
