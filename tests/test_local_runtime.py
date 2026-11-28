"""Cổng chuẩn, nhận diện bản đang chạy và khóa chống chạy đôi tác vụ nền."""
import json
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from so_cong_khai import local_runtime as R, web


class LocalRuntime(unittest.TestCase):
    def test_default_port(self):
        self.assertEqual(R.PORT, 8769)

    def test_os_lock_prevents_a_second_process_and_releases(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / 'config.json'
            lock = R.InstanceLock(config).acquire()
            code = ('import sys;from so_cong_khai.local_runtime import InstanceLock;'
                    'lock=InstanceLock(sys.argv[1]).acquire();lock.release()')
            try:
                result = subprocess.run([sys.executable, '-X', 'utf8', '-c', code, str(config)], capture_output=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
            finally:
                lock.release()
            result = subprocess.run([sys.executable, '-X', 'utf8', '-c', code, str(config)], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0)

    def test_start_failure_releases_lock_before_any_worker_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / 'config.json'
            config.write_text('{}')
            with patch.object(web, 'tao_vong_canh', return_value=None), patch.object(web.thi_truong, 'bang', return_value=None), \
                    patch.object(web, 'tao_may_chu', side_effect=OSError('port occupied')), \
                    patch.object(web.telegram_nhom, 'VongTelegram') as messages:
                with self.assertRaises(OSError):
                    web.khoi_dong(str(config), port=0)
                messages.assert_not_called()
            lock = R.InstanceLock(config).acquire()
            lock.release()

    def test_build_endpoint_is_public_and_does_not_expose_config(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / 'config.json'
            config.write_text('{"private_canary":"OWNER_SECRET"}')
            server = web.tao_may_chu(str(config), port=0)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/phien-ban', timeout=5) as response:
                    raw = response.read()
                    body = json.loads(raw)
                    self.assertEqual(response.headers['X-HGR-Build'], body['build'])
                    self.assertEqual(body['cong'], server.server_port)
                    self.assertEqual(body['che_do'], 'preview')
                    self.assertTrue(body['chi_doc_mt5'])
                    self.assertNotIn(b'OWNER_SECRET', raw)
                    self.assertNotIn(str(config).encode(), raw)
            finally:
                server.shutdown()
                server.server_close()
