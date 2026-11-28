"""Kiểm giao diện tự động bằng Playwright (thư viện mã nguồn mở của Microsoft, https://github.com/microsoft/playwright-python).

    python -X utf8 cong-cu/kiem_giao_dien.py [--goc http://127.0.0.1:8765] [--trang /thi-truong] [--khong-anh]

Mở từng trang (và từng thẻ của trang Thị trường) ở 2 ngôn ngữ (vi, en) × 2 cỡ màn hình (máy tính 1440×900, điện thoại 390×844), chờ trang chạy
JS và nhận giá, rồi soát:
- lỗi JS (console error, pageerror) và lỗi tải (HTTP ≥ 400) của chính webapp;
- tràn ngang cả trang (cuộn ngang) và phần tử lọt ra ngoài mép màn hình mà không nằm trong khung cuộn;
- thanh điều hướng giữ đúng một hàng (cao ≤ 64 px);
- trên điện thoại: nút và liên kết bấm được nhỏ hơn 24 px;
- ở tiếng Anh: chữ tiếng Việt còn sót trên màn hình (đếm dòng, in tối đa 8 mẫu).
Ảnh chụp cả trang lưu ở out/kiem-giao-dien/, báo cáo ở out/kiem-giao-dien.json và .txt. Chỉ đọc webapp; không bấm nút đặt hay gửi gì."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
TRANG = ['/', '/thi-truong#bang-gia', '/thi-truong#ky-thuat', '/thi-truong#suc-manh', '/thi-truong#ban-do-nhiet', '/thi-truong#tuong-quan',
         '/thi-truong#bien-dong', '/thi-truong#phien', '/thi-truong#thong-so', '/tin-tuc', '/bieu-do', '/cong-cu?ma=EURUSDp', '/nhat-ky', '/tai-khoan',
         '/hoc-giao-dich', '/kien-thuc', '/hieu-suat', '/cai-dat', '/cac-tai-khoan', '/kiem-lenh', '/ke-hoach', '/ky-luat', '/bat-dau', '/da-khung', '/kiem-tin-hieu', '/renko']
CO = {'may-tinh': {'width': 1440, 'height': 900}, 'dien-thoai': {'width': 390, 'height': 844},
      'man-lon': {'width': 1920, 'height': 1080}}       # 27/11/2026: màn lớn, để soát bố cục kín màn hình của trang Biểu đồ và chiều rộng 1560px
_VI = re.compile(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', re.I)

DO = r"""() => {
 const W = innerWidth, de = document.documentElement, ra = [];
 const cuon = el => { for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) { const s = getComputedStyle(p);
   if (/(auto|scroll|hidden)/.test(s.overflowX) || s.position === 'fixed') return true } return false };
 for (const el of document.body.querySelectorAll('*')) {
   const r = el.getBoundingClientRect(), s = getComputedStyle(el);
   if (!r.width || !r.height || s.visibility === 'hidden' || s.display === 'none' || s.position === 'fixed') continue;
   if ((r.right > W + 1 || r.left < -1) && !cuon(el)) ra.push((el.tagName + '.' + [...el.classList].join('.')).slice(0, 60) + ' ' + Math.round(r.left) + '→' + Math.round(r.right)) }
 const nho = [];
 if (W < 600) for (const el of document.querySelectorAll('a[href],button,select,input:not([type=hidden])')) {
   const r = el.getBoundingClientRect(), s = getComputedStyle(el);
   if (!r.width || s.visibility === 'hidden' || s.display === 'none' || el.closest('[hidden]')) continue;
   if (el.closest('p, footer, .tn, label') || (el.tagName === 'A' && s.display === 'inline' && el.closest('td') === null)) continue;   // liên kết trong đoạn văn: ngoại lệ "inline" của WCAG 2.5.8
   if ((r.height < 24 || r.width < 24) && el.offsetParent) nho.push((el.tagName + ' ' + (el.textContent || el.getAttribute('aria-label') || '').trim()).slice(0, 40) + ' ' + Math.round(r.width) + '×' + Math.round(r.height)) }
 const nv = document.querySelector('.nv-in');
 return { cuon_ngang: de.scrollWidth > de.clientWidth + 1, rong: de.scrollWidth, tran: ra.slice(0, 12), so_tran: ra.length, nho: nho.slice(0, 10), so_nho: nho.length,
          nv_cao: nv ? Math.round(nv.getBoundingClientRect().height) : null, lang: de.lang, chu: document.body.innerText }
}"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--goc', default='http://127.0.0.1:8765')
    ap.add_argument('--trang', action='append')
    ap.add_argument('--khong-anh', action='store_true')
    ap.add_argument('--co', action='append', choices=list(CO), help='chỉ soát cỡ màn này (lặp lại được); bỏ trống là mọi cỡ')
    ap.add_argument('--ngon-ngu', action='append', choices=['vi', 'en'], help='chỉ soát ngôn ngữ này; bỏ trống là cả hai')
    ap.add_argument('--cho', type=float, default=5.0, help='giây chờ sau khi mở trang')
    a = ap.parse_args(argv)
    from playwright.sync_api import sync_playwright                         # noqa: PLC0415
    ra = GOC / 'out' / 'kiem-giao-dien'
    ra.mkdir(parents=True, exist_ok=True)
    kq, dong = [], []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for lang in a.ngon_ngu or ('vi', 'en'):
            for co, vp in CO.items():
                if a.co and co not in a.co:
                    continue
                ctx = b.new_context(viewport=vp, device_scale_factor=1, is_mobile=co == 'dien-thoai', has_touch=co == 'dien-thoai', locale='en-US' if lang == 'en' else 'vi-VN')
                ctx.add_cookies([{'name': 'lang', 'value': lang, 'url': a.goc}])
                for t in a.trang or TRANG:
                    pg = ctx.new_page()
                    loi, tai = [], []
                    pg.on('console', lambda m, loi=loi: loi.append(m.text[:200]) if m.type == 'error' else None)
                    pg.on('pageerror', lambda e, loi=loi: loi.append('pageerror: ' + str(e)[:200]))
                    pg.on('response', lambda r, tai=tai: tai.append(f'{r.status} {r.url[-80:]}') if r.status >= 400 and a.goc in r.url else None)
                    t0 = time.monotonic()
                    try:
                        pg.goto(a.goc + t, wait_until='domcontentloaded', timeout=90000)
                        pg.wait_for_timeout(a.cho * 1000)
                        d = pg.evaluate(DO)
                    except Exception as e:                                   # noqa: BLE001
                        kq.append({'trang': t, 'lang': lang, 'co': co, 'loi_mo': str(e)[:300]})
                        dong.append(f'KHÔNG MỞ ĐƯỢC  {lang} {co:10s} {t}: {e}')
                        pg.close()
                        continue
                    sot = [x.strip() for x in d.pop('chu').splitlines()
                           if _VI.search(x.replace('López', '').replace('Tele dự báo', ''))] if lang == 'en' else []   # tên riêng giữ nguyên
                    ten = re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-') or 'tong-quan'
                    if not a.khong_anh:
                        pg.screenshot(path=str(ra / f'{ten}_{lang}_{co}.png'), full_page=True)
                    loi_js = [x for x in loi if 'ERR_CONNECTION' not in x and 'favicon' not in x]
                    van_de = []
                    if loi_js:
                        van_de.append(f'{len(loi_js)} lỗi JS')
                    if tai:
                        van_de.append(f'{len(tai)} lỗi tải')
                    if d['cuon_ngang']:
                        van_de.append(f'cuộn ngang (rộng {d["rong"]} px)')
                    if d['so_tran']:
                        van_de.append(f'{d["so_tran"]} phần tử tràn mép')
                    if d['nv_cao'] and d['nv_cao'] > 64:
                        van_de.append(f'thanh điều hướng cao {d["nv_cao"]} px')
                    if d['so_nho']:
                        van_de.append(f'{d["so_nho"]} nút < 24 px')
                    if sot:
                        van_de.append(f'{len(sot)} dòng còn tiếng Việt')
                    kq.append({'trang': t, 'lang': lang, 'co': co, 'giay': round(time.monotonic() - t0, 1), 'van_de': van_de, 'loi_js': loi_js[:8],
                               'loi_tai': tai[:8], 'tran': d['tran'], 'nho': d['nho'], 'sot': sot[:8], 'so_sot': len(sot), 'html_lang': d['lang']})
                    dong.append(f'{"ĐẠT " if not van_de else "XEM "} {lang} {co:10s} {t:24s} ' + ('; '.join(van_de) or 'không có vấn đề'))
                    print(dong[-1], flush=True)
                    pg.close()
                ctx.close()
        b.close()
    (GOC / 'out' / 'kiem-giao-dien.json').write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding='utf-8')
    dat = sum(1 for x in kq if not x.get('van_de') and not x.get('loi_mo'))
    tom = f'{dat}/{len(kq)} lượt không có vấn đề. Chi tiết: out/kiem-giao-dien.json; ảnh: out/kiem-giao-dien/.'
    (GOC / 'out' / 'kiem-giao-dien.txt').write_text('\n'.join(dong + ['', tom]), encoding='utf-8')
    print(tom)
    return 0 if dat == len(kq) else 1


if __name__ == '__main__':
    sys.exit(main())
