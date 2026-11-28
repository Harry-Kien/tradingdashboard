"""Authenticated MCP over real HTTP, actual stdio process, snapshot/image consistency."""
import io
import json
import os
import subprocess
import sys
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet

from so_cong_khai import ai_chart, loi_nghiep_vu, mcp_access, mcp_may_chu as M
import test_chart_auth_http as auth_http
from test_ai_platform import market


class Protocol(unittest.TestCase):
    def test_rejects_nonfinite_bad_types_and_malformed_messages(self):
        for value in (float('inf'), float('nan'), True, '123'):
            self.assertIsNotNone(M.validate_arguments('kiem_rui_ro', {'ma': 'XAUUSD', 'chieu': 'MUA', 'vao': value}))
        for request in ([], {'id': True, 'method': 'ping'}, {'id': 1, 'method': 'tools/call', 'params': []}):
            self.assertIn('error', M.xu_ly(request, ''))
        self.assertTrue(M.xu_ly({'id': 1, 'method': 'tools/call', 'params': {'name': 'doc_realtime', 'arguments': []}}, 'http://127.0.0.1:8766')['result']['isError'])

    def test_exact_loopback_only_without_network_on_invalid_url(self):
        for url in ('http://127.0.0.1:80@evil.test', 'http://127.0.0.1:80/else', 'http://127.0.0.1:80?target=x', 'https://127.0.0.1:80', 'http://localhost:80'):
            def fail(*a, **k):
                raise AssertionError('Should not open a connection')
            self.assertTrue(M.goi_cong_cu('danh_sach_phieu', {}, url, fail)['isError'])

    def test_prompts_resources_and_negotiation(self):
        result = M.xu_ly({'id': 1, 'method': 'initialize', 'params': {'protocolVersion': 'unknown'}}, '')['result']
        self.assertEqual(result['protocolVersion'], M.PHIEN_BAN_GIAO_THUC)
        self.assertIn('prompts', result['capabilities'])
        result = M.xu_ly({'id': 2, 'method': 'prompts/get', 'params': {'name': M.PROMPT_NAME}}, '')['result']
        self.assertIn('snapshot_id', result['messages'][0]['content']['text'])
        self.assertIn('error', M.xu_ly({'id': 3, 'method': 'resources/read', 'params': {'uri': 'file:///secret'}}, ''))
        self.assertIn('resources', M.xu_ly({'id': 4, 'method': 'resources/list'}, '')['result'])

    def test_redirect_and_error_never_expose_private_body(self):
        with self.assertRaises(ValueError):
            M.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.test')
        import urllib.error
        def error(*a, **k):
            raise urllib.error.HTTPError('http://127.0.0.1:8766', 403, 'x', {}, io.BytesIO(b'PRIVATE CREDENTIAL'))
        result = M.goi_cong_cu('danh_sach_phieu', {}, 'http://127.0.0.1:8766', error)
        self.assertNotIn('PRIVATE', json.dumps(result))


class LiveHTTP(unittest.TestCase):
    setUp = auth_http.ChartHTTP.setUp
    tearDown = auth_http.ChartHTTP.tearDown
    start = auth_http.ChartHTTP.start
    stop = auth_http.ChartHTTP.stop
    req = auth_http.ChartHTTP.req
    signup = auth_http.ChartHTTP.signup

    def enable(self):
        self.signup(self.a, 'mcp_owner')
        key = Fernet.generate_key().decode()
        self.env = patch.dict(os.environ, {'HGR_AI_MASTER_KEY': key})
        self.env.start()
        self.addCleanup(self.env.stop)
        status, body, _ = self.req(self.a, '/api/mcp/config', {'enabled': True, 'port': self.server.server_port})
        self.assertEqual(status, 200, body)
        return mcp_access.token(self.root)

    def snap(self, *args):
        s = market()
        s['captured_at'] = s['quote_at'] = time.time()
        s['frames']['M15']['close'] = 101
        return s

    def test_owner_control_secret_redaction_and_revocation(self):
        self.assertEqual(self.req(self.a, '/api/mcp/admin')[0], 401)
        secret = self.enable()
        self.signup(self.b, 'mcp_customer')
        self.assertEqual(self.req(self.b, '/api/mcp/admin')[0], 403)
        self.assertEqual(self.req(self.b, '/api/mcp/config', {'enabled': False, 'port': self.server.server_port})[0], 403)
        self.assertNotIn(secret, json.dumps(self.req(self.a, '/api/mcp/admin')[1]))
        self.assertTrue(M.goi_cong_cu('phan_tich_realtime', {}, self.base)['isError'])
        self.assertEqual(self.req(self.a, '/api/mcp/config', {'enabled': True, 'port': self.server.server_port, 'rotate': True})[0], 200)
        self.assertTrue(M.goi_cong_cu('phan_tich_realtime', {}, self.base, access_token=secret)['isError'])
        current = mcp_access.token(self.root)
        self.assertNotEqual(secret, current)
        self.req(self.a, '/api/mcp/config', {'enabled': False, 'port': self.server.server_port})
        self.assertTrue(M.goi_cong_cu('phan_tich_realtime', {}, self.base, access_token=current)['isError'])

    def test_pinned_snapshot_image_and_expiry(self):
        secret = self.enable()
        with patch.object(ai_chart, 'snapshot', side_effect=self.snap):
            result = M.goi_cong_cu('phan_tich_realtime', {'ma': 'XAUUSD', 'tf': 'M15'}, self.base, access_token=secret)
        self.assertFalse(result['isError'], result)
        snap = result['structuredContent']
        self.assertEqual(snap['regime'], 'aligned_up')
        ident = snap['snapshot_id']
        reread = M.goi_cong_cu('doc_realtime', {'snapshot_id': ident}, self.base, access_token=secret)
        self.assertEqual(reread['structuredContent'], snap)
        png = M.goi_cong_cu('anh_realtime', {'snapshot_id': ident}, self.base, access_token=secret)
        self.assertEqual(png['content'][1]['type'], 'image')
        self.assertEqual(png['content'][1]['mimeType'], 'image/png')
        path = self.root / 'out' / 'mcp' / (ident + '.json')
        data = json.loads(path.read_text(encoding='utf-8'))
        data['expires_at'] = time.time() - 1
        path.write_text(json.dumps(data), encoding='utf-8')
        self.assertTrue(M.goi_cong_cu('doc_realtime', {'snapshot_id': ident}, self.base, access_token=secret)['isError'])
        self.assertTrue(M.goi_cong_cu('anh_realtime', {'snapshot_id': '../secret'}, self.base, access_token=secret)['isError'])

    def test_legacy_evidence_snapshot_cannot_be_read_after_expiry(self):
        secret = self.enable()
        snap = {'id': 'SN-' + 'a' * 14, 'luc': (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()}
        loi_nghiep_vu.luu(snap, self.root / 'out')
        r = M.goi_cong_cu('doc_anh_chup', {'snapshot_id': snap['id']}, self.base, access_token=secret)
        self.assertTrue(r['isError'])

    def test_real_stdio_process_discovers_tools_without_provider_api(self):
        self.enable()
        messages = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-11-25'}},
                    {'jsonrpc': '2.0', 'method': 'notifications/initialized'}, {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'}]
        command = [sys.executable, '-X', 'utf8', str(Path(M.__file__).with_name('mcp_boot.py')), '--cau-hinh', str(self.cfg), '--port', str(self.server.server_port)]
        proc = subprocess.run(command, input='\n'.join(map(json.dumps, messages)) + '\n', capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        output = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual([x['id'] for x in output], [1, 2])
        self.assertIn('anh_realtime', {t['name'] for t in output[1]['result']['tools']})


if __name__ == '__main__':
    unittest.main()
