"""Dựng lại so_cong_khai/logo.py (logo nhúng sẵn dạng data URI) từ ảnh logo gốc tinh/logo.webp:

    python -X utf8 cong-cu/tao_logo.py [ảnh_mới] [--le 0] [--nho x0,y0,x1,y1]

Có `ảnh_mới` thì cắt phần giữa (mặc định bỏ 8,5% viền quanh mép; `--le 0` để giữ nguyên ảnh), bo góc, ghi đè tinh/logo.webp (512 px)
và tinh/logo-chia-se.png (ảnh xem trước khi chia sẻ link) rồi dựng lại logo.py. `--nho` cắt thêm một vùng cận (tỷ lệ theo ảnh gốc) làm
tinh/logo-nho.webp cho các cỡ nhỏ: logo.py và tinh/logo.ico lấy từ bản này. Logo hiện tại (26/11/2026):
    python -X utf8 cong-cu/tao_logo.py <ảnh chân dung> --le 0 --nho 0.2,0,0.8,0.6
Logo được nhúng thẳng vào trang nên chạy được ở mọi nơi (webapp, gói chia sẻ, bản demo tĩnh) mà không cần thêm đường dẫn máy chủ."""
from __future__ import annotations

import base64
import io
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

GOC = Path(__file__).resolve().parent.parent
NGUON = GOC / 'tinh' / 'logo.webp'
RA = GOC / 'so_cong_khai' / 'logo.py'


def bo_goc(im: Image.Image, r: float = 0.22) -> Image.Image:
    n = im.size[0]
    m = Image.new('L', (n * 4, n * 4), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, n * 4 - 1, n * 4 - 1), radius=int(n * 4 * r), fill=255)
    out = im.convert('RGBA')
    out.putalpha(m.resize((n, n), Image.LANCZOS))
    return out


NHO = GOC / 'tinh' / 'logo-nho.webp'                                         # bản cắt cận cho cỡ nhỏ (thanh menu, tab, lối tắt), nếu có
CHIA_SE = GOC / 'tinh' / 'logo-chia-se.png'                                   # ảnh đầy đủ, không bo góc: ảnh xem trước khi chia sẻ link (og:image)


def tu_anh_moi(p: Path, le_ty: float = 0.085, nho: tuple[float, float, float, float] | None = None) -> None:
    """le_ty: tỷ lệ cắt bỏ quanh mép (logo cũ có viền sương trắng: 0,085; ảnh không có viền: 0). nho: vùng (x0, y0, x1, y1) theo tỷ lệ
    của ảnh gốc để cắt bản cận cho cỡ nhỏ: ảnh nhiều chi tiết thu về 16–36 px sẽ không còn nhận ra, nên cỡ nhỏ dùng vùng quan trọng nhất."""
    im = Image.open(p).convert('RGB')
    n = min(im.size)
    le = round(n * le_ty)
    x0, y0 = (im.size[0] - n) // 2, (im.size[1] - n) // 2
    lech = round(n * 0.009) if le else 0
    vuong = im.crop((x0 + le, y0 + le - lech, x0 + n - le, y0 + n - le - lech)).resize((1024, 1024), Image.LANCZOS)
    bo_goc(vuong).resize((512, 512), Image.LANCZOS).save(NGUON, 'WEBP', quality=90, method=6)
    vuong.resize((630, 630), Image.LANCZOS).save(CHIA_SE, 'PNG', optimize=True)
    if nho:
        w, h = im.size
        c = im.crop((round(nho[0] * w), round(nho[1] * h), round(nho[2] * w), round(nho[3] * h)))
        bo_goc(c.resize((1024, 1024), Image.LANCZOS)).resize((512, 512), Image.LANCZOS).save(NHO, 'WEBP', quality=90, method=6)
    elif NHO.exists():
        NHO.unlink()


def data_uri(im: Image.Image, n: int) -> str:
    x = im.resize((n, n), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=2))
    buf = io.BytesIO()
    x.save(buf, 'WEBP', quality=88, method=6)
    return 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    le, nho = 0.085, None
    if '--le' in argv:
        k = argv.index('--le')
        le = float(argv[k + 1])
        del argv[k:k + 2]
    if '--nho' in argv:
        k = argv.index('--nho')
        nho = tuple(float(x) for x in argv[k + 1].split(','))
        del argv[k:k + 2]
    if argv:
        tu_anh_moi(Path(argv[0]), le, nho)
    im = Image.open(NHO if NHO.exists() else NGUON).convert('RGBA')
    im.save(GOC / 'tinh' / 'logo.ico', sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64)])   # biểu tượng lối tắt Windows
    nho = data_uri(im, 72)
    RA.write_text('"""Logo của webapp, nhúng sẵn dạng data URI (tạo bởi cong-cu/tao_logo.py từ tinh/logo.webp; đừng sửa tay)."""\n\n'
                  f'LOGO_NHO = {nho!r}   # 72 px: thanh điều hướng (hiện 36 px), biểu tượng tab, ảnh chia sẻ\n', encoding='utf-8')
    print(f'Đã ghi {RA} ({RA.stat().st_size / 1024:.1f} KB)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
