"""Kiểm chức năng toàn bộ webapp như một người dùng thật (Playwright, trình duyệt Chromium không hiện cửa sổ).

    python -X utf8 cong-cu/kiem_chuc_nang.py [--goc http://127.0.0.1:8765] [--dien-thoai]

Webapp phải đang chạy và nối được MT5. Chỉ ĐỌC: không bấm Lưu ở trang Cài đặt, không thêm hay bỏ tài khoản, không hỏi AI.
Mỗi trang: bắt lỗi JS, lỗi tải (mã ≥ 400) và đo thời gian tới lúc nội dung chính hiện ra; rồi làm các thao tác chính của trang và kiểm
kết quả. In ĐẠT / LỖI từng mục và ghi out/kiem-chuc-nang.json. Thoát mã 1 nếu có mục lỗi."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
KQ: list[dict] = []


def ghi(muc: str, ok: bool, chi_tiet: str = '') -> None:
    KQ.append({'muc': muc, 'ok': ok, 'chi_tiet': chi_tiet})
    print(f'{"ĐẠT" if ok else "LỖI"}  {muc}' + (f'  ({chi_tiet})' if chi_tiet else ''), flush=True)


def cho(pg, js: str, giay: float = 20) -> float | None:
    """Chờ tới khi biểu thức JS đúng; trả số giây đã chờ, None nếu quá hạn."""
    t0 = time.monotonic()
    try:
        pg.wait_for_function(js, timeout=giay * 1000, polling=100)
        return round(time.monotonic() - t0, 2)
    except Exception:                                                        # noqa: BLE001
        return None


def mo(ctx, goc: str, duong: str, san_sang: str, ten: str, giay: float = 25):
    """Mở trang, chờ nội dung chính; ghi một mục 'tải' kèm thời gian. Trả (trang, danh sách lỗi JS, danh sách lỗi tải)."""
    pg = ctx.new_page()
    loi, tai = [], []
    pg.on('console', lambda m: loi.append(m.text[:160]) if m.type == 'error' and 'favicon' not in m.text else None)
    pg.on('pageerror', lambda e: loi.append('pageerror: ' + str(e)[:160]))
    pg.on('response', lambda r: tai.append(f'{r.status} {r.url.replace(goc, "")[:70]}') if r.status >= 400 and r.url.startswith(goc) else None)
    t0 = time.monotonic()
    pg.goto(goc + duong, wait_until='domcontentloaded', timeout=60000)
    g = cho(pg, san_sang, giay)
    ghi(f'{ten}: tải trang', g is not None, f'{round(time.monotonic() - t0, 2)} s tới khi có nội dung' if g is not None else f'quá {giay} s chưa có nội dung')
    return pg, loi, tai


def ket(pg, loi, tai, ten: str) -> None:
    ghi(f'{ten}: không lỗi JS', not loi, '; '.join(loi[:3]))
    ghi(f'{ten}: không lỗi tải', not tai, '; '.join(tai[:3]))
    pg.close()


def bieu_do(ctx, goc):
    T = 'Biểu đồ'
    pg, loi, tai = mo(ctx, goc, '/bieu-do?ma=XAUUSDp', "document.querySelector('#lw canvas') && !document.querySelector('.stage').dataset.tai", T)
    lg = "[...document.querySelectorAll('.stage div')].map(d=>d.textContent).find(t=>/, (M5|M15|M30|H1|H4|D1)/.test(t)&&t.length<400)||''"
    for tf in ('M5', 'H1', 'D1', 'M15'):
        pg.click(f'.seg.tf button[data-tf="{tf}"]')
        g = cho(pg, f"({lg}).includes(', {tf}')", 15)
        ghi(f'{T}: đổi khung {tf}', g is not None, f'{g} s' if g is not None else 'chú giải không đổi')
    src = pg.evaluate("document.querySelector('#src')?.textContent||''")
    ghi(f'{T}: dòng trạng thái giá', bool(re.search('từng tick|đang nghỉ|nối lại', src)), src[:80])
    if 'từng tick' in src:
        a = pg.evaluate(f"({lg}).match(/Đ ([\\d.,]+)/)?.[1]")
        g = cho(pg, f"(({lg}).match(/Đ ([\\d.,]+)/)?.[1]) !== {json.dumps(a)}", 20)
        ghi(f'{T}: giá chạy theo tick', g is not None, f'giá đổi sau {g} s' if g is not None else 'giá đứng yên 20 s')
    chips = pg.evaluate("[...document.querySelectorAll('.chip[data-k]')].map(b=>b.dataset.k)")
    sai = []
    for k in chips:
        try:
            pg.evaluate("document.querySelector('details.tuy').open=true")
            pg.click(f'.chip[data-k="{k}"]', timeout=3000)
            pg.click(f'.chip[data-k="{k}"]', timeout=3000)
        except Exception as e:                                               # noqa: BLE001
            sai.append(f'{k}: {str(e)[:60]}')
    pg.evaluate("document.querySelector('details.tuy').open=false")
    ghi(f'{T}: bật tắt {len(chips)} chỉ báo', not sai and len(chips) > 0, '; '.join(sai[:3]))
    pg.click('#pt-btn')
    g = cho(pg, "(()=>{const p=document.querySelector('aside.pt');return p&&!p.hidden&&p.textContent.length>200})()", 30)
    ghi(f'{T}: phân tích điểm vào', g is not None, f'{g} s' if g is not None else 'bảng phân tích không hiện')
    n = pg.evaluate("document.querySelectorAll('.blt tbody tr').length")
    ghi(f'{T}: bảng lệnh của mọi phương pháp', n >= 5, f'{n} dòng')
    pg.click('#fs-btn')
    vua = pg.evaluate("(()=>{const r=document.querySelector('#lw').getBoundingClientRect(),c=document.querySelector('.chartp');return r.bottom<=innerHeight+1&&c.scrollHeight<=c.clientHeight+1&&c.classList.contains('max')})()")
    ghi(f'{T}: toàn màn hình vừa khít', bool(vua))
    pg.click('#fs-btn')
    pg.select_option('#ma', 'EURUSDp') if pg.evaluate("[...document.querySelectorAll('#ma option')].some(o=>o.value==='EURUSDp')") else None
    g = cho(pg, f"({lg}).includes('EURUSD')", 20)
    ghi(f'{T}: đổi sang mã khác (EURUSD)', g is not None, f'{g} s' if g is not None else 'không đổi được mã')
    ket(pg, loi, tai, T)


def thi_truong(ctx, goc):
    T = 'Thị trường'
    pg, loi, tai = mo(ctx, goc, '/thi-truong#bang-gia', "document.querySelectorAll('#bg-body tr[data-ma]').length>20", T)
    ghi(f'{T}: trạng thái trực tiếp', 'Trực tiếp' in (pg.evaluate("document.querySelector('.song-pill')?.textContent||''")),
        pg.evaluate("document.querySelector('.song-pill')?.textContent||''")[:60])
    a = pg.evaluate("[...document.querySelectorAll('#bg-body td.gia')].map(t=>t.textContent).join('|')")
    g = cho(pg, f"[...document.querySelectorAll('#bg-body td.gia')].map(t=>t.textContent).join('|')!=={json.dumps(a)}", 15)
    ghi(f'{T}: bảng giá chạy', g is not None, f'giá đổi sau {g} s' if g is not None else 'không mã nào đổi giá trong 15 s')
    for tab, o in (('ky-thuat', '#kt-body tr'), ('suc-manh', '#sm-bar .sm-r'), ('ban-do-nhiet', '#hm *'), ('tuong-quan', '#tq table'),
                   ('bien-dong', '#bd *'), ('phien', '#ss .ss'), ('thong-so', '#sp-body tr')):
        pg.evaluate(f"location.hash='#{tab}'")
        g = cho(pg, f"document.querySelectorAll('{o}').length>0", 40)
        ghi(f'{T}: tab {tab}', g is not None, f'{g} s' if g is not None else 'không có nội dung')
    ket(pg, loi, tai, T)


def cong_cu(ctx, goc):
    T = 'Công cụ'
    pg, loi, tai = mo(ctx, goc, '/cong-cu?ma=XAUUSDp', "/\\d/.test(document.querySelector('#cc-bid')?.textContent||'')", T)
    bid = float(pg.evaluate("document.querySelector('#cc-bid').textContent").replace('.', '').replace(',', '.'))
    pg.fill('#von', '10000')
    pg.fill('#rr-sl', f'{bid - 15:.2f}')
    pg.dispatch_event('#rr-sl', 'input')
    g = cho(pg, "/\\d+,\\d+ lot/.test(document.querySelector('#rr-kq')?.textContent||'')", 10)
    ghi(f'{T}: tính khối lượng theo rủi ro', g is not None, (pg.evaluate("document.querySelector('#rr-kq').textContent") or '')[:70])
    g = cho(pg, "getComputedStyle(document.querySelector('#rr-mt5')).display!=='none'", 10)
    ghi(f'{T}: ký quỹ lấy từ MT5', g is not None)
    for o, ten in (('#pip-kq', 'giá trị pip'), ('#pv-kq', 'pivot'), ('#kq-kq', 'ký quỹ')):
        ghi(f'{T}: {ten}', bool(re.search(r'\d', pg.evaluate(f"document.querySelector('{o}')?.textContent||''"))))
    ket(pg, loi, tai, T)


def don_gian(ctx, goc, duong, san_sang, ten, giay=25):
    pg, loi, tai = mo(ctx, goc, duong, san_sang, ten, giay)
    ket(pg, loi, tai, ten)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--goc', default='http://127.0.0.1:8765')
    ap.add_argument('--dien-thoai', action='store_true', help='chạy ở cỡ điện thoại 390×844, cảm ứng')
    a = ap.parse_args(argv)
    from playwright.sync_api import sync_playwright                         # noqa: PLC0415
    t0 = time.monotonic()
    with sync_playwright() as p:
        b = p.chromium.launch()
        dt = a.dien_thoai
        ctx = b.new_context(viewport={'width': 390, 'height': 844} if dt else {'width': 1440, 'height': 900}, is_mobile=dt, has_touch=dt, locale='vi-VN')
        ctx.add_cookies([{'name': 'lang', 'value': 'vi', 'url': a.goc}])
        for f in (bieu_do, thi_truong, cong_cu):
            try:
                f(ctx, a.goc)
            except Exception as e:                                           # noqa: BLE001
                ghi(f'{f.__name__}: chạy hết kịch bản', False, f'{type(e).__name__}: {str(e)[:150]}')
        for duong, san_sang, ten in (
                ('/tin-tuc', "document.querySelector('#tn')?.children.length>0", 'Tin tức'),
                ('/hieu-suat', "(document.querySelector('#ds')?.textContent||'').length>50", 'Hiệu suất'),
                ('/cac-tai-khoan', "!/Đang đọc/.test(document.querySelector('#ctk')?.textContent||'Đang đọc')", 'Các tài khoản'),
                ('/tai-khoan', "/\\d/.test(document.querySelector('main')?.textContent||'')", 'Tài khoản MT5'),
                ('/nhat-ky', "(document.querySelector('main')?.textContent||'').length>300", 'Nhật ký điểm vào'),
                ('/cai-dat', "/Đang nối|Chưa nối/.test(document.querySelector('#tt')?.textContent||'')", 'Cài đặt'),
                ('/hoc-giao-dich', "document.querySelectorAll('section').length>2", 'Học giao dịch'),
                ('/kien-thuc', "document.querySelectorAll('article').length>20", 'Kiến thức'),
                ('/', "document.body.textContent.length>500", 'Tổng quan')):
            try:
                don_gian(ctx, a.goc, duong, san_sang, ten)
            except Exception as e:                                           # noqa: BLE001
                ghi(f'{ten}: tải trang', False, f'{type(e).__name__}: {str(e)[:150]}')
        b.close()
    loi = [k for k in KQ if not k['ok']]
    tep = 'kiem-chuc-nang-dien-thoai.json' if a.dien_thoai else 'kiem-chuc-nang.json'
    (GOC / 'out' / tep).write_text(json.dumps({'luc': time.strftime('%Y-%m-%d %H:%M'), 'kq': KQ}, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'\n{len(KQ) - len(loi)}/{len(KQ)} mục đạt trong {round(time.monotonic() - t0)} s. Chi tiết: out/{tep}')
    return 1 if loi else 0


if __name__ == '__main__':
    sys.exit(main())
