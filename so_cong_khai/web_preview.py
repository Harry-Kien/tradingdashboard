"""Run the updated web/market feed alongside an existing app, without message schedulers.

This preview never starts khoi_dong(), Telegram, drawing notification or journal workers.
The existing app may keep those workers running on port 8765. Both use the same
owner settings and account store. This is loopback only, not a hosting entry point.
"""
import argparse
import json
from pathlib import Path

from . import duong, thi_truong, tin_hieu_tien_cuu, web


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8769)
    parser.add_argument('--cau-hinh', default=str(duong.goc_du_lieu() / 'cau-hinh.json'))
    parser.add_argument('--tien-cuu', action='store_true', help='Ghi và chấm tín hiệu quan sát bằng dữ liệu MT5.')
    args = parser.parse_args()
    read = lambda: json.loads(Path(args.cau_hinh).read_text(encoding='utf-8'))
    feed = thi_truong.bang(read)
    tien_cuu = tin_hieu_tien_cuu.VongTienCuu(read, web._out) if args.tien_cuu else None
    server = web.tao_may_chu(args.cau_hinh, port=args.port, bang=feed, tien_cuu_vong=tien_cuu)
    if feed:
        feed.start()
    if tien_cuu:
        tien_cuu.start()
    print(f'AI preview http://127.0.0.1:{server.server_port}; message schedulers are not started.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if tien_cuu:
            tien_cuu.dung.set()
        server.server_close()


if __name__ == '__main__':
    main()
