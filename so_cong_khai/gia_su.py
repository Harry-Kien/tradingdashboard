"""Gia sư giao dịch trên trang /hoc-giao-dich (chủ dự án chọn ngày 26/11/2026).

Dạy một chủ đề của trang Học giao dịch bằng cách hỏi từng câu, theo kỹ năng socratic-tutor của Jane Street (giấy phép MIT, chép nguyên văn ở
so_cong_khai/ky_nang_jane_street/): kiểm tra trình độ, bản đồ kỹ năng mức 0–5, sai thì hỏi hẹp lại chứ không đọc đáp án, ôn lại bất ngờ,
bài kiểm tra cuối. Phần thêm của webapp: nói theo ngôn ngữ của trang (tiếng Việt hoặc tiếng Anh), nội dung chủ đề lấy từ trang Học giao dịch,
không đưa tín hiệu, không dự báo giá, không lời khuyên đầu tư, không hứa tỷ lệ thắng.

Mỗi câu trả lời gọi Claude bằng khóa API của chủ máy, nên có hai chốt chặn: số lượt mỗi ngày và ngân sách riêng (khóa "gia_su" trong
cau-hinh.json). Sổ chi phí out/gia-su.jsonl chỉ ghi chủ đề, số token và tiền. Mỗi buổi học lưu ở du-lieu/gia-su/<mã buổi>.json (hội thoại,
tiến độ) để học tiếp được sau khi tắt webapp; giữ 30 buổi gần nhất. Mô-đun này không đọc giá và không đặt lệnh."""
from __future__ import annotations

import json
import re
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path

from . import giu_lenh
from . import hoc_giao_dich as HG
from .__main__ import HERE
from .doc_so import VN

MODEL = 'claude-opus-5-5'
GIA = {'in': 4.0, 'out': 20.0, 'ghi_dem': 5.0, 'doc_dem': 0.2}     # USD mỗi triệu token của Claude Opus 5.5 (ghi bộ đệm 1,25 lần giá vào)
UOC_TINH_USD = 0.05                                               # ước một lượt, để chặn trước khi vượt ngân sách
MAC_DINH = {'bat': True, 'luot_moi_ngay': 80, 'ngan_sach_usd': 3.0}
MAX_CAU = 1500                                                    # ký tự mỗi câu người học gửi
MAX_LUOT_PHIEN = 120                                              # lượt mỗi buổi học
GIU_BUOI = 30                                                     # số buổi giữ trên đĩa
THU_MUC = Path(__file__).resolve().parent / 'ky_nang_jane_street'
PHIEN: dict = {}
_khoa = threading.Lock()
_MA = re.compile(r'[A-Za-z0-9_-]{8,40}')

QUY_TAC = """Bạn là gia sư giao dịch của webapp "Harry · Gold Research". Bạn dạy theo đúng kỹ năng socratic-tutor ở dưới (của Jane Street, giấy phép MIT).

Điều chỉnh cho webapp này (ưu tiên hơn kỹ năng khi có chỗ khác nhau):
- Viết đúng ngôn ngữ ghi ở khối "Buổi học" phía dưới, câu ngắn, giọng thẳng thắn. Khi viết tiếng Việt, số theo kiểu Việt Nam: 3.528,12; 0,5R; 52,7%.
- Người học đã bấm "Bắt đầu học" cho đúng một chủ đề, nên ý định học đã rõ: vào thẳng phần kiểm tra trình độ, không hỏi lại có muốn học không.
- Mỗi tin nhắn kết thúc bằng ĐÚNG MỘT câu hỏi, chỉ có một dấu chấm hỏi trong cả tin nhắn. Không gộp hai ý vào một câu hỏi ("bao nhiêu… và vì sao…");
  phần "vì sao" để dành cho tin nhắn sau. Sau câu hỏi không viết thêm gì.
- Bản đồ kỹ năng đặt trong khối ``` để thẳng hàng, dùng ký tự █ và ░ cho thanh tiến độ, tên kỹ năng viết theo ngôn ngữ của buổi học. Đưa bản đồ
  ra khi xong phần kiểm tra trình độ, mỗi khi một mức thay đổi, và khi người học xin xem tiến độ.
- Người học có thể gõ lệnh bằng tiếng Việt hoặc tiếng Anh: "xem tiến độ"/"show progress", "khó hơn"/"harder", "dễ hơn"/"easier",
  "nói luôn đáp án"/"just tell me". Buổi học được webapp tự lưu, nên không cần lệnh lưu hay tiếp tục.
- Chỉ dạy kiến thức. Không đưa tín hiệu mua bán, không dự báo giá của bất kỳ mã nào, không nói nên vào lệnh nào, không đưa lời khuyên đầu tư cá nhân.
  Nếu người học hỏi những điều đó, nói ngắn rằng gia sư không làm việc này (tín hiệu và phân tích nằm ở trang Biểu đồ và kênh Telegram, kèm số đo),
  rồi quay lại bài.
- Không hứa tỷ lệ thắng hay lợi nhuận. Khi nói về hiệu quả của một cách giao dịch, nói rõ đó là số đo quá khứ, và dùng các sự thật đo được dưới đây.
- Bài tập thực hành dùng số giả định do bạn đặt ra (vốn, giá vào, dừng lỗ…), và chấm đúng con số người học tính ra.

Sự thật đo được trên dữ liệu vàng của chính hệ thống này (2015–11/2026), dùng khi liên quan:
- Tỷ lệ thắng cao không có nghĩa là có lãi: muốn thắng trên 70–75% phải chốt lời rất gần, và khi đó phí cùng chênh lệch giá ăn hết phần lời
  (chốt ở 0,25R: 4/12 năm thắng từ 75% nhưng chỉ 4/12 năm có lãi).
- Đoán chiều giá vàng quanh giờ ra tin Mỹ đúng khoảng 50%, ngang tung đồng xu (gần 4.000 lần ra tin).
- Thứ quyết định sống sót là rủi ro mỗi lệnh và kỳ vọng mỗi lệnh (R), không phải tỷ lệ thắng.
{giu_lenh}
---
"""
NGON_NGU = {'vi': 'tiếng Việt', 'en': 'English (viết toàn bộ bằng tiếng Anh, kể cả bản đồ kỹ năng; số theo kiểu tiếng Anh: 3,528.12)'}


def _ky_nang() -> str:
    try:
        s = (THU_MUC / 'SKILL.md').read_text(encoding='utf-8')
    except OSError:
        return ''
    if s.startswith('---'):                                        # bỏ phần đầu YAML: tên và mô tả chỉ dùng để chọn kỹ năng, không phải lời dạy
        s = s.split('---', 2)[2]
    return s.strip()


def chu_de() -> list[dict]:
    """Các chủ đề lấy từ trang Học giao dịch: {'id', 'ten', 'nhom'}."""
    ds = [{'id': 'co_ban', 'ten': 'Khái niệm cốt lõi (CFD, spread, lot, pip, đòn bẩy, ký quỹ, swap)', 'nhom': 'Nền tảng'},
          {'id': 'lenh', 'ten': 'Các loại lệnh trong MT5', 'nhom': 'Nền tảng'},
          {'id': 'rui_ro', 'ten': 'Quản lý rủi ro và tính khối lượng lệnh', 'nhom': 'Nền tảng'},
          {'id': 'ky_vong', 'ten': 'Tỷ lệ thắng, R:R, kỳ vọng và kiểm chứng một phương pháp', 'nhom': 'Nền tảng'}]
    ds += [{'id': p['id'], 'ten': p['ten'], 'nhom': 'Phong cách giao dịch'} for p in HG.PHONG_CACH]
    return ds


def _ten(cd: str) -> str:
    return next((x['ten'] for x in chu_de() if x['id'] == cd), cd)


def noi_dung(cd: str) -> str:
    """Nội dung của chủ đề, lấy nguyên từ trang Học giao dịch, để gia sư dạy đúng những gì webapp đang dạy."""
    if cd == 'co_ban':
        return '\n'.join(f'- {t}: {n}' for t, n in HG.KHAI_NIEM)
    if cd == 'lenh':
        return '\n'.join(f'- {x[0]}: {x[1]} {x[2]}' for x in HG.LENH)
    if cd == 'rui_ro':
        return ('\n'.join(f'- {t}: {n}' for t, n in HG.QUY_TAC)
                + '\n- Công cụ của webapp: trang Công cụ tính khối lượng lệnh từ vốn, % rủi ro và khoảng dừng lỗ; trang Kỷ luật có giới hạn lỗ trong ngày.')
    if cd == 'ky_vong':
        return ('- Kỳ vọng mỗi lệnh = tỷ lệ thắng × lãi trung bình − tỷ lệ thua × lỗ trung bình (tính bằng R, R là số tiền mất nếu chạm dừng lỗ).\n'
                '- Tỷ lệ thắng hòa vốn của mức chốt k·R (chưa tính phí) là 1 / (1 + k): chốt 0,25R cần thắng 80%, 0,5R cần 66,7%, 1R cần 50%, 2R cần 33,3%.\n'
                '- Kiểm chứng: chia dữ liệu thành phần học và phần kiểm, chọn cách làm trên phần học rồi chỉ xác nhận trên phần kiểm; thử càng nhiều cách thì '
                'càng dễ gặp kết quả đẹp do may (webapp có PBO, Deflated Sharpe, kiểm định SPA để trừ hao điều này).\n'
                '- Số đo quá khứ không bảo đảm kết quả sau này; chỉ dữ liệu mới (sau ngày chọn luật) mới là phép thử thật.')
    p = next((x for x in HG.PHONG_CACH if x['id'] == cd), None)
    if p is None:
        return ''
    return (f'- {p["ten"]}: {p["mo_ta"]}\n- Khung: {p["khung"]}; giữ lệnh: {p["giu"]}; hợp với: {p["hop"]}\n'
            + ''.join(f'- Cách làm: {c}\n' for c in p['cach']) + f'- Lỗi hay gặp: {p["loi"]}'
            + ('\n- Cảnh báo: phong cách rủi ro rất cao, dạy để người học hiểu vì sao nó nguy hiểm.' if p.get('canh_bao') else ''))


def he_thong(cd: str, lang: str = 'vi') -> list[dict]:
    """Lời nhắc hệ thống: khối chung (quy tắc + kỹ năng, giống nhau cho mọi buổi) rồi khối buổi học (chủ đề, ngôn ngữ). Bộ đệm đặt ở khối cuối."""
    hv = giu_lenh.cau()
    chung = QUY_TAC.format(giu_lenh=f'- {hv}' if hv else '') + '\n' + _ky_nang()
    return [{'type': 'text', 'text': chung},
            {'type': 'text', 'text': f'Buổi học\nNgôn ngữ: {NGON_NGU.get(lang, NGON_NGU["vi"])}\nChủ đề: {_ten(cd)}\n'
                                     f'Nội dung webapp đang dạy cho chủ đề này (dạy bám theo, được mở rộng khi cần):\n{noi_dung(cd)}',
             'cache_control': {'type': 'ephemeral'}}]


# --------------------------------------------------------------------------- giới hạn và sổ chi phí
def cai(cfg: dict) -> dict:
    return {**MAC_DINH, **(cfg.get('gia_su') or {})}


def _so(out: Path) -> Path:
    return out / 'gia-su.jsonl'


def doc_so(out: Path) -> list[dict]:
    try:
        return [json.loads(x) for x in _so(out).read_text(encoding='utf-8').splitlines() if x.strip()]
    except (OSError, ValueError):
        return []


def co_khoa() -> bool:
    """Chỉ kiểm tra CÓ khóa hay không, như nút Hỏi AI; không đọc giá trị của khóa."""
    from . import ai_hoi                                           # noqa: PLC0415
    return ai_hoi.co_khoa()


def trang_thai(cfg: dict, out: Path, now: datetime | None = None, goc: Path = HERE) -> dict:
    a, now = cai(cfg), now or datetime.now(timezone.utc)
    recs = doc_so(out)
    hom = [r for r in recs if datetime.fromisoformat(r['luc']).astimezone(VN).date() == now.astimezone(VN).date()]
    da_tieu = round(sum(float(r.get('usd') or 0) for r in recs), 4)
    chan = []
    if not a['bat']:
        chan.append('Gia sư đang tắt trong cấu hình (khóa "gia_su").')
    if not co_khoa():
        chan.append('Chưa có khóa API của Anthropic trên máy này (đặt biến ANTHROPIC_API_KEY như hướng dẫn trong HUONG_DAN.md, mục Tính năng tùy chọn).')
    if len(hom) >= int(a['luot_moi_ngay']):
        chan.append(f'Đã dùng đủ {int(a["luot_moi_ngay"])} lượt hôm nay.')
    if da_tieu + UOC_TINH_USD > float(a['ngan_sach_usd']):
        chan.append(f'Đã chạm ngân sách {float(a["ngan_sach_usd"]):.2f} USD của gia sư.')
    return {'hom_nay': len(hom), 'moi_ngay': int(a['luot_moi_ngay']), 'da_tieu_usd': da_tieu, 'ngan_sach_usd': float(a['ngan_sach_usd']),
            'chan': chan, 'chu_de': chu_de(), 'mo_hinh': MODEL, 'buoi': buoi_gan_day(goc)}


def _phi(u) -> float:
    g = lambda k: float(getattr(u, k, 0) or 0)                     # noqa: E731
    return round((g('input_tokens') * GIA['in'] + g('output_tokens') * GIA['out'] + g('cache_creation_input_tokens') * GIA['ghi_dem']
                  + g('cache_read_input_tokens') * GIA['doc_dem']) / 1e6, 5)


def _ghi(out: Path, rec: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with _so(out).open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')


# --------------------------------------------------------------------------- buổi học trên đĩa
def _tm(goc: Path) -> Path:
    return goc / 'du-lieu' / 'gia-su'


def _luu(goc: Path, pid: str, s: dict) -> None:
    tm = _tm(goc)
    tm.mkdir(parents=True, exist_ok=True)
    tam = tm / f'{pid}.tmp'
    tam.write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')
    tam.replace(tm / f'{pid}.json')
    ds = sorted(tm.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in ds[GIU_BUOI:]:                                        # chỉ giữ các buổi gần nhất
        p.unlink(missing_ok=True)


def _doc(goc: Path, pid: str | None) -> dict | None:
    if not pid or not _MA.fullmatch(pid):
        return None
    if pid in PHIEN:
        return PHIEN[pid]
    try:
        s = json.loads((_tm(goc) / f'{pid}.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    PHIEN[pid] = s
    return s


def _ban_do(hien: list[dict]) -> str | None:
    """Bản đồ kỹ năng gần nhất gia sư đã đưa ra (khối ``` có thanh █/░), để danh sách buổi học hiện tiến độ."""
    for m in reversed(hien):
        if m.get('ai'):
            for khoi in reversed(re.findall(r'```[a-z]*\n?(.*?)```', m.get('chu_gs', ''), re.S)):
                if '█' in khoi or '░' in khoi:
                    return khoi.strip('\n')
    return None


def buoi_gan_day(goc: Path = HERE, n: int = 10) -> list[dict]:
    tm = _tm(goc)
    out = []
    for p in sorted(tm.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:n] if tm.exists() else []:
        try:
            s = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        out.append({'phien': p.stem, 'chu_de': s['chu_de'], 'ten': _ten(s['chu_de']), 'luc': s.get('luc'), 'luot': s.get('luot', 0),
                    'usd': round(float(s.get('usd') or 0), 4), 'lang': s.get('lang', 'vi'), 'ban_do': _ban_do(s.get('hien') or [])})
    return out


def doc_buoi(pid: str, goc: Path = HERE) -> dict | None:
    """Hội thoại để vẽ lại trên trang khi học tiếp: {'phien', 'chu_de', 'hien': [{'ai', 'chu_gs'}], 'luot', 'usd'}."""
    with _khoa:
        s = _doc(goc, pid)
    if s is None:
        return None
    return {'phien': pid, 'chu_de': s['chu_de'], 'ten': _ten(s['chu_de']), 'hien': s.get('hien') or [], 'luot': s.get('luot', 0), 'usd': s.get('usd', 0)}


def _khoi(b) -> dict:
    """Một khối trả lời của Claude thành dict để lưu và gửi lại NGUYÊN VẸN ở lượt sau (khối suy nghĩ phải giữ đúng như nhận)."""
    if hasattr(b, 'model_dump'):
        return b.model_dump(mode='json', exclude_none=True)
    return {k: v for k, v in vars(b).items() if v is not None}


# --------------------------------------------------------------------------- hỏi
def hoi(cfg: dict, out: Path, phien: str | None, cd: str, cau: str, client=None, now: datetime | None = None, lang: str = 'vi',
        goc: Path = HERE, khi_chu=None) -> dict:
    """Một lượt của buổi học. Không có `phien` (hoặc phiên khác chủ đề) là buổi mới, `cau` rỗng nghĩa là bắt đầu.
    Trả {'ok', 'phien', 'tra_loi' | 'ly_do', 'chi_phi_usd', 'trang_thai'}. `khi_chu(đoạn)`: nhận chữ dần trong lúc gia sư viết (luồng)."""
    now = now or datetime.now(timezone.utc)
    lang = lang if lang in NGON_NGU else 'vi'
    if cd not in {x['id'] for x in chu_de()}:
        return {'ok': False, 'ly_do': 'Chủ đề không có trong danh sách.'}
    cau = (cau or '').strip()
    if len(cau) > MAX_CAU:
        return {'ok': False, 'ly_do': f'Câu trả lời dài quá {MAX_CAU} ký tự; viết gọn lại.'}
    st = trang_thai(cfg, out, now, goc)
    if st['chan']:
        return {'ok': False, 'ly_do': ' '.join(st['chan']), 'trang_thai': st}
    with _khoa:
        s = _doc(goc, phien)
        if s is None or s['chu_de'] != cd:
            phien, s = secrets.token_urlsafe(12), {'chu_de': cd, 'lang': lang, 'tao': now.isoformat(timespec='seconds'), 'msgs': [], 'hien': [],
                                                   'luot': 0, 'usd': 0.0}
            PHIEN[phien] = s
        if s['luot'] >= MAX_LUOT_PHIEN:
            return {'ok': False, 'phien': phien, 'ly_do': f'Buổi học đã đủ {MAX_LUOT_PHIEN} lượt; bắt đầu buổi mới cho chủ đề này.'}
        tu_dong = not cau                                          # lời mở đầu do webapp viết, không hiện như câu của người học
        if not cau:
            if s['msgs']:
                return {'ok': False, 'phien': phien, 'ly_do': 'Viết câu trả lời trước khi gửi.'}
            cau = (f'Teach me "{_ten(cd)}" until I master it.' if s.get('lang') == 'en' else f'Hãy dạy tôi chủ đề "{_ten(cd)}" tới mức thành thạo.')
        cu = list(s['msgs'])
    gui = cu + [{'role': 'user', 'content': [{'type': 'text', 'text': cau, 'cache_control': {'type': 'ephemeral'}}]}]   # bộ đệm cả hội thoại cũ
    try:
        if client is None:
            import anthropic                                       # noqa: PLC0415 - chỉ nạp khi có người dùng gia sư
            client = anthropic.Anthropic(max_retries=2, timeout=120.0)
        kw = dict(model=MODEL, max_tokens=4000, system=he_thong(cd, s.get('lang', 'vi')), messages=gui, output_config={'effort': 'medium'},
                  betas=['server-side-fallback-2026-07-01'], fallbacks='default')   # bị từ chối vì phân loại an toàn thì máy chủ tự chạy lại ở mô hình dự phòng
        if khi_chu is None:
            r = client.beta.messages.create(**kw)
        else:
            with client.beta.messages.stream(**kw) as luong:
                for doan in luong.text_stream:
                    khi_chu(doan)
                r = luong.get_final_message()
    except Exception as e:                                         # noqa: BLE001 - lỗi mạng, khóa sai, hết hạn mức: báo, không làm hỏng webapp
        return {'ok': False, 'phien': phien, 'ly_do': _loi(e)}
    phi = _phi(getattr(r, 'usage', None))
    _ghi(out, {'luc': now.isoformat(timespec='seconds'), 'chu_de': cd, 'mo_hinh': getattr(r, 'model', MODEL), 'dung': getattr(r, 'stop_reason', None),
               'vao': getattr(r.usage, 'input_tokens', None), 'ra': getattr(r.usage, 'output_tokens', None),
               'doc_dem': getattr(r.usage, 'cache_read_input_tokens', None), 'usd': phi})
    if r.stop_reason == 'refusal':
        with _khoa:
            s['usd'] = round(float(s.get('usd') or 0) + phi, 5)
        return {'ok': False, 'phien': phien, 'ly_do': 'Mô hình không trả lời câu này. Thử diễn đạt khác, hoặc bắt đầu buổi mới.', 'chi_phi_usd': phi}
    chu = '\n\n'.join(b.text for b in r.content if getattr(b, 'type', '') == 'text').strip()
    if r.stop_reason == 'max_tokens':
        chu += '\n\n(Câu trả lời bị cắt vì quá dài.)'
    chu = chu or '(Gia sư không trả lời bằng chữ; gửi lại câu trả lời.)'
    with _khoa:
        s['msgs'] = cu + [{'role': 'user', 'content': cau}, {'role': 'assistant', 'content': [_khoi(b) for b in r.content]}]
        if not tu_dong:
            s['hien'].append({'ai': False, 'chu_gs': cau})
        s['hien'].append({'ai': True, 'chu_gs': chu})
        s['luot'] += 1
        s['usd'] = round(float(s.get('usd') or 0) + phi, 5)
        s['luc'] = now.isoformat(timespec='seconds')
        _luu(goc, phien, s)
    return {'ok': True, 'phien': phien, 'tra_loi': chu, 'chi_phi_usd': phi, 'usd_buoi': s['usd'], 'trang_thai': trang_thai(cfg, out, now, goc)}


def _loi(e: Exception) -> str:
    ten = type(e).__name__
    if ten == 'AuthenticationError':
        return 'Khóa API của Anthropic không hợp lệ.'
    if ten == 'PermissionDeniedError':
        return 'Khóa API không có quyền dùng mô hình này.'
    if ten == 'RateLimitError':
        return 'Anthropic đang giới hạn số lượt; thử lại sau ít phút.'
    if ten in ('APIConnectionError', 'APITimeoutError'):
        return 'Không nối được tới Anthropic (mạng); thử lại sau.'
    if ten == 'BadRequestError':
        return 'Anthropic từ chối yêu cầu (dữ liệu không hợp lệ); bắt đầu buổi mới.'
    if ten == 'ModuleNotFoundError':
        return 'Chưa cài thư viện anthropic (python -m pip install anthropic).'
    return f'Lỗi khi hỏi gia sư: {ten}.'
