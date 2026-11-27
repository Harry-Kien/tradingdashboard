"""Bộ chuyển MCP tùy chọn (27/11/2026), MẶC ĐỊNH TẮT. Bật bằng "mcp": {"bat": true} trong cau-hinh.json, rồi cho MCP client chạy cục bộ:

    python -m so_cong_khai.mcp_may_chu --cau-hinh cau-hinh.json

- Chạy qua stdio (JSON-RPC 2.0, mỗi dòng một thông điệp). Không mở cổng mạng, không tạo tunnel.
- Mọi công cụ gọi lại API CHỈ ĐỌC của webapp đang chạy ở 127.0.0.1 (cùng lõi nghiệp vụ với giao diện: loi_nghiep_vu, phieu_ke_hoach,
  kiem_lenh, ke_hoach). Tiến trình này không tự nối MT5, nên không có phiên MT5 thứ hai.
- Không có công cụ đặt, sửa, đóng lệnh; không shell, không SQL, không đọc tệp tùy ý. Phạm vi tài khoản là đúng tài khoản demo mà webapp đang
  đọc (webapp từ chối tài khoản không phải demo).
- Chốt ảnh chụp: gọi `chot_anh_chup` một lần, rồi truyền `snapshot_id` cho các công cụ đọc khác, để mọi lần đọc trong một phân tích cùng một
  thời điểm. Ảnh chụp hết hạn thì công cụ báo lỗi, không tự chụp lại.
Chức năng AI chính của webapp không phụ thuộc bộ chuyển này."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PHIEN_BAN_GIAO_THUC = '2025-06-18'
_S = {'type': 'string'}
_N = {'type': 'number'}
CONG_CU = {
    'chot_anh_chup': ('Chụp và chốt trạng thái thị trường (mã, khung) thành một ảnh chụp có id và danh sách bằng chứng có id. Gọi trước các công cụ khác.',
                      {'ma': _S, 'tf': _S}, [], '/api/loi/chup', lambda a: {'ma': a.get('ma', ''), 'tf': a.get('tf', 'M15')}),
    'doc_anh_chup': ('Đọc lại đúng ảnh chụp đã chốt theo id.', {'snapshot_id': _S}, ['snapshot_id'], '/api/loi/anh-chup', lambda a: {'id': a['snapshot_id']}),
    'dieu_kien_phuong_phap': ('Điều kiện và kết quả của một phương pháp trong ảnh chụp đã chốt (không tính lại).', {'snapshot_id': _S, 'phuong_phap': _S},
                              ['snapshot_id', 'phuong_phap'], '/api/loi/dieu-kien', lambda a: {'sn': a['snapshot_id'], 'pp': a['phuong_phap']}),
    'bang_chung_phuong_phap': ('Thống kê đã ghi, phiên bản và loại báo cáo của một phương pháp (Harrison là báo cáo đóng băng).', {'phuong_phap': _S},
                               ['phuong_phap'], '/api/loi/bang-chung', lambda a: {'pp': a['phuong_phap']}),
    'kiem_rui_ro': ('Kiểm quản lý rủi ro một lệnh dự định (chỉ tính, không đặt lệnh). chieu: MUA hoặc BAN.',
                    {'ma': _S, 'chieu': _S, 'vao': _N, 'sl': _N, 'tp': _N, 'rui_ro_pct': _N}, ['ma', 'chieu', 'vao'], '/api/kiem-lenh',
                    lambda a: {k2: a[k] for k, k2 in (('ma', 'ma'), ('chieu', 'chieu'), ('vao', 'vao'), ('sl', 'sl'), ('tp', 'tp'), ('rui_ro_pct', 'rui_ro')) if a.get(k) is not None}),
    'tinh_ke_hoach': ('Tính kế hoạch vốn và lệnh: lot, SL/TP gợi ý, ký quỹ (chỉ tính). chieu: MUA hoặc BAN.',
                      {'ma': _S, 'chieu': _S, 'vao': _N, 'sl': _N, 'von': _N}, ['ma', 'chieu'], '/api/ke-hoach',
                      lambda a: {k: a[k] for k in ('ma', 'chieu', 'vao', 'sl', 'von') if a.get(k) is not None}),
    'doc_phieu': ('Đọc một phiếu kế hoạch (bản mới nhất) kèm kết quả mô phỏng.', {'id': _S}, ['id'], '/api/phieu', lambda a: {'id': a['id']}),
    'danh_sach_phieu': ('Danh sách phiếu kế hoạch gần nhất.', {}, [], '/api/phieu/ds', lambda a: {}),
    'tong_ket_review': ('Thống kê sổ phiếu: quyết định, kiểm rủi ro, mức làm đúng kế hoạch (đếm riêng, không phải hiệu suất đã kiểm chứng).', {}, [],
                        '/api/loi/review', lambda a: {}),
}


def danh_sach_cong_cu() -> list[dict]:
    return [{'name': k, 'description': v[0], 'inputSchema': {'type': 'object', 'properties': v[1], 'required': v[2], 'additionalProperties': False}}
            for k, v in CONG_CU.items()]


def goi_cong_cu(ten: str, doi: dict, goc: str, mo=urllib.request.urlopen) -> dict:
    """Gọi một công cụ: chỉ các tên trong CONG_CU, chỉ GET tới webapp cục bộ. Trả nội dung MCP."""
    if ten not in CONG_CU:
        return {'content': [{'type': 'text', 'text': f'Không có công cụ {ten}.'}], 'isError': True}
    _, tinh_chat, bat_buoc, duong, tham = CONG_CU[ten]
    doi = doi if isinstance(doi, dict) else {}
    thua = [k for k in doi if k not in tinh_chat]
    thieu = [k for k in bat_buoc if doi.get(k) in (None, '')]
    if thua or thieu:
        return {'content': [{'type': 'text', 'text': f'Tham số không hợp lệ: thừa {thua}, thiếu {thieu}.'}], 'isError': True}
    for k, v in doi.items():
        if tinh_chat[k] is _S and (not isinstance(v, str) or len(v) > 60) or tinh_chat[k] is _N and (isinstance(v, bool) or not isinstance(v, (int, float))):
            return {'content': [{'type': 'text', 'text': f'Tham số {k} sai kiểu.'}], 'isError': True}
    if not goc.startswith('http://127.0.0.1:'):
        return {'content': [{'type': 'text', 'text': 'Chỉ gọi webapp trên chính máy này.'}], 'isError': True}
    url = goc + duong + ('?' + urllib.parse.urlencode(tham(doi)) if tham(doi) else '')
    try:
        with mo(urllib.request.Request(url, headers={'Accept': 'application/json'}), timeout=60) as r:   # noqa: S310 - chỉ http://127.0.0.1, kiểm ở trên
            body = r.read().decode('utf-8')
        return {'content': [{'type': 'text', 'text': body}], 'isError': False}
    except urllib.error.HTTPError as e:
        return {'content': [{'type': 'text', 'text': f'Webapp trả {e.code}: {e.read().decode("utf-8", "replace")[:500]}'}], 'isError': True}
    except (urllib.error.URLError, OSError) as e:
        return {'content': [{'type': 'text', 'text': f'Không nối được webapp ở {goc}: {e}. Mở webapp trước.'}], 'isError': True}


def xu_ly(tin: dict, goc: str, mo=urllib.request.urlopen) -> dict | None:
    """Một thông điệp JSON-RPC → câu trả lời (None với thông báo không cần trả lời)."""
    id_, pp = tin.get('id'), tin.get('method')
    if id_ is None:
        return None
    if pp == 'initialize':
        kq = {'protocolVersion': (tin.get('params') or {}).get('protocolVersion') or PHIEN_BAN_GIAO_THUC, 'capabilities': {'tools': {}},
              'serverInfo': {'name': 'so-cong-khai-chi-doc', 'version': '1'}}
    elif pp == 'ping':
        kq = {}
    elif pp == 'tools/list':
        kq = {'tools': danh_sach_cong_cu()}
    elif pp == 'tools/call':
        p = tin.get('params') or {}
        kq = goi_cong_cu(str(p.get('name') or ''), p.get('arguments') or {}, goc, mo)
    else:
        return {'jsonrpc': '2.0', 'id': id_, 'error': {'code': -32601, 'message': f'không hỗ trợ {pp}'}}
    return {'jsonrpc': '2.0', 'id': id_, 'result': kq}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='so_cong_khai.mcp_may_chu', description=__doc__)
    ap.add_argument('--cau-hinh', default='cau-hinh.json')
    a = ap.parse_args(argv)
    try:
        cfg = json.loads(Path(a.cau_hinh).read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        print(f'Không đọc được cấu hình: {e}', file=sys.stderr)
        return 2
    m = cfg.get('mcp') or {}
    if not m.get('bat'):
        print('Bộ chuyển MCP đang tắt. Bật bằng "mcp": {"bat": true} trong cau-hinh.json.', file=sys.stderr)
        return 1
    cong = int(m.get('cong', 8765))
    goc = f'http://127.0.0.1:{cong}'                                     # chỉ máy này; không nhận địa chỉ khác
    for dong in sys.stdin:
        dong = dong.strip()
        if not dong:
            continue
        try:
            tin = json.loads(dong)
            tl = xu_ly(tin, goc) if isinstance(tin, dict) else {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32600, 'message': 'yêu cầu không hợp lệ'}}
        except ValueError:
            tl = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'JSON hỏng'}}
        if tl is not None:
            sys.stdout.write(json.dumps(tl, ensure_ascii=False) + '\n')
            sys.stdout.flush()
    return 0


if __name__ == '__main__':
    sys.exit(main())
