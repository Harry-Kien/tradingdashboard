"""Kiểm hồi quy SSE thật, đọc dùng chung, mất nguồn, nối lại và đóng máy chủ."""
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from so_cong_khai import luong_gia, tai_khoan_chart, web


def _doc_sse(r):
    frame = {}
    while line := r.readline():
        if line == b'\n' and 'data' in frame:
            return frame.get('event', 'message'), json.loads(frame['data'])
        for key in (b'event', b'data'):
            if line.startswith(key + b': '):
                frame[key.decode()] = line[len(key) + 2:].strip().decode()
    raise EOFError('Luồng kết thúc trước khi có gói dữ liệu')


def _may_chu(tmp_path, doc, **opts):
    cfg = tmp_path / 'config.json'
    cfg.write_text('{}')
    srv = web.tao_may_chu(str(cfg), port=0)
    srv.luong_gia.dong()
    srv.luong_gia = luong_gia.LuongGia(doc, giu=0.05, **opts)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    _, token = tai_khoan_chart.vao('owner_test', 'test-password-for-feed', True, tmp_path)
    cookie = tai_khoan_chart.cookie_header(token).split(';', 1)[0]

    def mo(query=''):
        url = f'http://127.0.0.1:{srv.server_port}/api/song{query}'
        return urllib.request.urlopen(urllib.request.Request(url, headers={'Cookie': cookie}), timeout=6)

    return srv, thread, mo, cookie


def _gia(ms, gia_bid=10):
    return {'ms': ms, 'bid': gia_bid, 'ask': gia_bid + 1, 'nen': [60, gia_bid, gia_bid, gia_bid, gia_bid]}


class SharedFeed(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_nhieu_trinh_duyet_cung_ma_chi_doc_mot_lan(self):
        san_sang = threading.Event()
        calls = []

        def doc(g, tf, ma):
            calls.append((ma, tf))
            if not san_sang.wait(5):
                return None
            return _gia(10 if ma == 'EURUSD' else 20)

        srv, thread, mo, _ = _may_chu(self.root, doc, nhip=0.2, toi_da_xem=9)
        try:
            with ThreadPoolExecutor(max_workers=9) as pool, ExitStack() as streams:
                def mo_ma(ma):
                    return mo(f'?ma={ma}&tf=M15')
                rs = [streams.enter_context(f.result()) for f in
                      [pool.submit(mo_ma, 'EURUSD') for _ in range(8)] + [pool.submit(mo_ma, 'XAUUSD')]]
                assert srv.luong_gia.thong_ke()['dang_xem'] == 9
                assert srv.luong_gia.thong_ke()['kenh'] == 2
                try:
                    mo_ma('EURUSD').close()
                    raise AssertionError('Luồng vượt giới hạn vẫn được mở')
                except urllib.error.HTTPError as e:
                    assert e.code == 503
                    assert e.headers['Retry-After'] == '5'
                    e.close()
                san_sang.set()
                assert [_doc_sse(r) for r in rs] == [('message', _gia(10))] * 8 + [('message', _gia(20))]
                assert set(calls) == {('EURUSD', 'M15'), ('XAUUSD', 'M15')}
                assert len(calls) <= 4, calls
                # Đóng máy chủ phải đánh thức ngay cả các kết nối đang chờ dữ liệu tiếp.
                srv.shutdown()
                srv.server_close()
                assert all(not r.read().strip().replace(b': giu', b'').strip() for r in rs)
        finally:
            san_sang.set()
            srv.shutdown()
            srv.server_close()
            thread.join()


    def test_nguon_lui_thoi_gian_hoac_mat_gia_tu_khoi_phuc(self):
        payload = {'value': _gia(100)}
        srv, thread, mo, _ = _may_chu(self.root, lambda *args: payload['value'], nhip=0.02)
        try:
            with mo() as r:
                assert _doc_sse(r) == ('message', _gia(100))
                payload['value'] = _gia(99)  # mẫu cũ phải bị chặn ở máy chủ
                assert _doc_sse(r) == ('nguon-gia', {'trang_thai': 'khong_co_du_lieu'})
                payload['value'] = _gia(100)  # nguồn trở lại với chính quote hợp lệ trước đó
                assert _doc_sse(r) == ('message', _gia(100))
                payload['value'] = None
                assert _doc_sse(r)[0] == 'nguon-gia'
                payload['value'] = _gia(101, 12)
                assert _doc_sse(r) == ('message', _gia(101, 12))
            den = time.monotonic() + 2
            while srv.luong_gia.thong_ke()['dang_xem'] and time.monotonic() < den:
                time.sleep(0.02)
            assert srv.luong_gia.thong_ke()['kenh'] == 0
        finally:
            srv.shutdown()
            srv.server_close()
            thread.join()


    def test_gia_hong_khong_loi_ra_json(self):
        for x in (_gia(1, float('inf')), _gia(1, float('nan')), _gia(True), {**_gia(1), 'ask': 9},
                  {**_gia(1), 'nen': [60, 10, 9, 8, 10]}, {**_gia(1), 'nen': [59, 10, 10, 10, 10]}):
            assert luong_gia._dong_goi(x, 0, 60) is None


    def test_may_chu_mac_dinh_dung_bo_doc_mt5(self):
        cfg = self.root / 'config.json'
        cfg.write_text('{}')
        with patch.object(web.song, 'tick', return_value=_gia(42)) as tick:
            with web.tao_may_chu(str(cfg), port=0) as srv:
                with srv.luong_gia.dang_ky({}, 'H1', 'USDJPY') as k:
                    assert b'"ms":42' in srv.luong_gia.doi(k, 0, time.monotonic() + 3)[1]
                tick.assert_any_call({}, 'H1', 'USDJPY')

    def test_dang_xuat_dong_luong_dang_xem(self):
        with patch.object(web, 'NHIP_QUYEN_LUONG', 0.05):
            srv, thread, mo, cookie = _may_chu(self.root, lambda *args: _gia(1))
            try:
                with mo() as r:
                    assert _doc_sse(r) == ('message', _gia(1))
                    tai_khoan_chart.ra(cookie, self.root)
                    assert b'data:' not in r.read()
                with self.assertRaises(urllib.error.HTTPError) as loi:
                    mo().close()
                assert loi.exception.code == 401
                loi.exception.close()
            finally:
                srv.shutdown()
                srv.server_close()
                thread.join()
