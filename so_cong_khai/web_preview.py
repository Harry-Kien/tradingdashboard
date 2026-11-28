"""Run the updated web/market feed alongside an existing app.

This preview never starts khoi_dong(), the general Telegram scheduler, or drawing and journal workers.
The dedicated structure watcher is opt-in and honors the owner-configured Telegram mode.
The existing app may keep those workers running on port 8765. Both use the same
owner settings and account store. This is loopback only, not a hosting entry point.
"""
import argparse
import json
from pathlib import Path

from . import cau_truc_live, duong, thi_truong, tin_hieu_tien_cuu, web


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8769)
    parser.add_argument('--cau-hinh', default=str(duong.goc_du_lieu() / 'cau-hinh.json'))
    parser.add_argument('--tien-cuu', action='store_true', help='Ghi và chấm tín hiệu quan sát bằng dữ liệu MT5.')
    parser.add_argument('--cau-truc-live', action='store_true', help='Bật riêng bộ theo dõi cảnh báo cấu trúc MT5 theo cấu hình Telegram.')
    args = parser.parse_args()
    read = lambda: json.loads(Path(args.cau_hinh).read_text(encoding='utf-8'))
    feed = thi_truong.bang(read)
    tien_cuu = tin_hieu_tien_cuu.VongTienCuu(read, web._out) if args.tien_cuu else None
    cau_truc = cau_truc_live.Vong(read, web._out, gui_that=True) if args.cau_truc_live else None
    server = web.tao_may_chu(args.cau_hinh, port=args.port, bang=feed, tien_cuu_vong=tien_cuu)
    if feed:
        feed.start()
    if tien_cuu:
        tien_cuu.start()
    if cau_truc:
        cau_truc.start()
    print(f'AI preview http://127.0.0.1:{server.server_port}; structure watcher {"on" if cau_truc else "off"}.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if tien_cuu:
            tien_cuu.dung.set()
        if cau_truc:
            cau_truc.dung.set()
        server.server_close()


if __name__ == '__main__':
    main()
