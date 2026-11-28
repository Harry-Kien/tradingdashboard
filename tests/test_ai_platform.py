"""Real SQL/HTTP boundaries, mocked billable providers and deterministic market data."""
import copy
import io
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
from cryptography.fernet import Fernet

from so_cong_khai import ai_chart, ai_providers as providers, ai_store, song
import test_chart_auth_http as auth_http

NOW = 1795759200.0
USER = {'id': 'a' * 32, 'ten': 'client', 'chu': False}


def market(*args):
    cs = [[int(NOW - 900 * (80 - i)), 100.0, 102.0, 98.0, 101.0] for i in range(80)]
    return {'symbol': 'XAUUSD', 'timeframe': 'M15', 'source': 'MT5', 'captured_at': NOW, 'quote_at': NOW,
            'bid': 101.0, 'ask': 101.05, 'spread': .05, 'digits': 2, 'point': .01, 'news': 'not_available',
            'candles': cs, 'frames': {tf: {'close':101., 'atr14_sma': 2., 'ema20':100., 'ema50':99., 'ema200':90.,
                                        'rsi14':55., 'bars':240, 'high20':102., 'low20':98.,
                                        'last_closed_candle_open_at':int(NOW-seconds)}
                                    for tf,seconds in (('M5',300),('M15',900),('M30',1800),('H1',3600),('H4',14400),('D1',86400))}, 'running_candle': None}


def answer(options=None):
    scenarios = [] if not options else [{'id': options[0]['id'], 'reason': 'Cấu trúc đã xác minh.',
                                          'trigger': 'Chờ nến đóng xác nhận.', 'invalidation': 'Hủy khi cấu trúc mất hiệu lực.'}]
    return {'summary': 'Thị trường cần xác nhận.', 'trend': 'H1/H4 chưa đồng thuận.', 'agreement': ['EMA tăng.'],
            'conflicts': ['Chưa có tin kinh tế.'], 'scenarios': scenarios, 'watch': ['Spread và biến động.'], 'answer': 'Chờ xác nhận.'}


def provider(*args):
    payload = json.loads(args[3])
    return {'text': json.dumps(answer(payload['CANDIDATES'])), 'complete': True, 'model': 'test-model', 'input_tokens': 100, 'output_tokens': 200}


class Platform(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {'HGR_AI_MASTER_KEY': Fernet.generate_key().decode(), 'ANTHROPIC_API_KEY': 'test-key-never-billed'})
        self.env.start()
        self.cfg = copy.deepcopy(ai_store.DEFAULT)
        self.cfg.update(enabled=True, free_questions=1, daily_budget_usd=20)
        ai_store.save(self.root, self.cfg)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def body(self):
        return {'ma': 'XAUUSD', 'tf': 'M15', 'mode': 'entry', 'request_id': ai_store.new_id()}

    def analyze(self, body=None, fn=provider, snap=market, now=NOW):
        return ai_chart.analyze(self.root, {}, USER, body or self.body(), provider_fn=fn, snapshot_fn=snap, clock=lambda: now)

    def test_grounded_levels_idempotency_and_account_isolation(self):
        body = self.body()
        body.update(provider='evil', uid='b' * 32, plan='premium', settings={'free_questions': 1000})
        mock = unittest.mock.Mock(side_effect=provider)
        r = self.analyze(body, fn=mock)
        self.assertTrue(r['ok'], r)
        self.assertEqual(len(r['analysis']['scenarios']), 1)
        scenario = r['analysis']['scenarios'][0]
        self.assertEqual(scenario['entry'], ai_chart.candidates(market(), self.cfg)[0]['entry'])
        self.assertGreaterEqual(scenario['rr'][0], self.cfg['min_rr'])
        self.assertEqual(r['account']['remaining'], 0)
        self.assertEqual(mock.call_args[0][1]['provider'], 'anthropic')
        again = self.analyze(body, fn=mock)
        self.assertEqual(again['snapshot_sha'], r['snapshot_sha'])
        self.assertEqual(mock.call_count, 1)
        other = ai_store.status(self.root, {**USER, 'id': 'b' * 32}, NOW)
        self.assertEqual(other['account']['remaining'], 1)
        with self.assertRaises(ai_store.StoreError):
            self.analyze(now=NOW + 10)

    def test_api_cannot_offer_entry_when_higher_frame_conflicts(self):
        def conflicting(*args):
            snap=market()
            snap['frames']['H4'].update(close=95.,ema20=98.,ema50=99.)
            return snap
        result=self.analyze(snap=conflicting)
        self.assertTrue(result['ok'])
        self.assertEqual(result['analysis']['scenarios'],[])
        self.assertEqual(result['topdown']['status'],'higher_conflict')

    def test_last_free_question_is_atomic_across_connections(self):
        barrier = threading.Barrier(2)
        def run(_):
            barrier.wait()
            try:
                ai_store.reserve(self.root, USER, ai_store.new_id(), .1, NOW)
                return 'reserved'
            except ai_store.StoreError:
                return 'blocked'
        with ThreadPoolExecutor(2) as pool:
            self.assertCountEqual(list(pool.map(run, range(2))), ['reserved', 'blocked'])

    def test_crash_refunds_question_without_releasing_unknown_api_cost(self):
        ident = ai_store.new_id()
        ai_store.reserve(self.root, USER, ident, .5, NOW)
        self.assertEqual(ai_store.status(self.root, USER, NOW + 181)['account']['remaining'], 1)
        cached, _ = ai_store.reserve(self.root, USER, ident, .5, NOW + 182)
        self.assertFalse(cached['ok'])
        self.assertEqual(ai_store.admin(self.root)['usage'][0]['reserved_usd'], .5)

    def test_bad_output_refunds_question_but_tracks_billed_cost(self):
        def invalid(*args):
            d = answer()
            d['scenarios'] = [{'id': 'invented', 'entry': 999999}]
            return {'text': json.dumps(d), 'complete': True, 'model': 'test', 'input_tokens': 100, 'output_tokens': 100}
        r = self.analyze(fn=invalid)
        self.assertFalse(r['ok'])
        self.assertEqual(ai_store.status(self.root, USER, NOW)['account']['remaining'], 1)
        admin = ai_store.admin(self.root)
        self.assertGreater(admin['usage'][0]['reserved_usd'], 0)
        self.assertEqual(admin['usage'][0]['used'], 0)
        self.assertTrue(self.analyze(now=NOW + 10)['ok'])

    def test_stale_after_inference_is_marked_and_no_second_api_call(self):
        r = self.analyze(now=NOW + 90)
        self.assertTrue(r['expired'])
        self.assertLess(r['expires_at'], NOW + 90)

    def test_budget_is_reserved_before_external_call(self):
        self.cfg['daily_budget_usd'] = .1
        ai_store.save(self.root, self.cfg)
        mock = unittest.mock.Mock(side_effect=provider)
        with self.assertRaisesRegex(ai_store.StoreError, 'Ngân sách'):
            self.analyze(fn=mock)
        mock.assert_not_called()

    def test_timeout_keeps_conservative_budget_and_refunds_free_turn(self):
        def error(*a):
            raise providers.ProviderError('API hết thời gian.')
        r = self.analyze(fn=error)
        self.assertFalse(r['ok'])
        self.assertEqual(r['account']['remaining'], 1)
        self.assertGreater(ai_store.admin(self.root)['usage'][0]['reserved_usd'], .1)

    def test_paid_plan_expiry_and_restart_do_not_reset_usage(self):
        self.assertTrue(self.analyze()['ok'])
        ai_store.grant(self.root, USER['id'], 'pro', NOW + 60)
        s = ai_store.status(self.root, USER, NOW + 10)['account']
        self.assertEqual((s['plan'], s['remaining']), ('pro', 199))
        self.assertEqual(ai_store.status(self.root, USER, NOW + 61)['account']['remaining'], 0)
        ai_store.grant(self.root, USER['id'], 'pro', NOW + 500)
        self.assertEqual(ai_store.status(self.root, USER, NOW + 100)['account']['remaining'], 199)

    def test_consistent_backup_retains_allowance_and_settings(self):
        self.assertTrue(self.analyze()['ok'])
        raw = ai_store.backup_bytes(self.root / 'du-lieu' / 'ai-platform.sqlite3')
        con = sqlite3.connect(':memory:')
        try:
            con.deserialize(raw)
            self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(con.execute('SELECT SUM(counted) FROM requests').fetchone()[0], 1)
        finally:
            con.close()

    def test_encrypted_key_roundtrip_and_corrupt_master_fails_closed(self):
        providers.save_key(self.root, 'openai', 'never-print-this-secret')
        raw = (self.root / 'du-lieu' / 'ai-openai-secret.json').read_text()
        self.assertNotIn('never-print', raw)
        self.assertEqual(providers.key(self.root, 'openai'), 'never-print-this-secret')
        self.assertNotIn('never-print', json.dumps(ai_store.admin(self.root)))
        with patch.dict(os.environ, {'HGR_AI_MASTER_KEY': Fernet.generate_key().decode()}), self.assertRaises(providers.ProviderError):
            providers.key(self.root, 'openai')
        providers.save_key(self.root, 'openai', '')
        self.assertFalse((self.root / 'du-lieu' / 'ai-openai-secret.json').exists())

    def test_reject_bad_settings_and_unapproved_model(self):
        for changes in ({'model': 'unknown'}, {'free_questions': -1}, {'daily_budget_usd': float('nan')},
                        {'max_tokens': 4096.5}, {'vision': 1}, {'provider': 'http://localhost'}):
            with self.subTest(changes=changes), self.assertRaises(ai_store.StoreError):
                ai_store.save(self.root, {**self.cfg, **changes})

    def test_provider_request_protocols_and_secret_error_redaction(self):
        for name in providers.CATALOG:
            with self.subTest(provider=name), patch.dict(os.environ, {providers.CATALOG[name]['env']: 'secret-for-test'}):
                cfg = {**self.cfg, 'provider': name, 'model': 'owner-approved'}
                if name == 'openai':
                    reply = {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': '{}'}]}]}
                elif name == 'anthropic':
                    reply = {'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': '{}'}]}
                else:
                    reply = {'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}]}
                ctx = unittest.mock.MagicMock()
                ctx.__enter__.return_value.read.return_value = json.dumps(reply).encode()
                opener = SimpleNamespace(open=unittest.mock.Mock(return_value=ctx))
                with patch('urllib.request.build_opener', return_value=opener):
                    result = providers.call(self.root, cfg, 'Return JSON', 'json data', None)
                self.assertTrue(result['complete'])
                req = opener.open.call_args[0][0]
                body = json.loads(req.data)
                self.assertEqual(body['model'], 'owner-approved')
                self.assertEqual(req.full_url, providers.CATALOG[name]['url'])
                if name == 'openai':
                    self.assertFalse(body['store'])
        err = urllib.error.HTTPError('https://example.test/key=SECRET', 401, 'SECRET', {}, io.BytesIO(b'SECRET'))
        with patch('urllib.request.build_opener', return_value=SimpleNamespace(open=unittest.mock.Mock(side_effect=err))):
            with self.assertRaises(providers.ProviderError) as caught:
                providers.call(self.root, self.cfg, 'json', 'data')
        self.assertNotIn('SECRET', str(caught.exception))

    def test_image_validation_and_disallowed_image_model(self):
        for value in ('https://localhost/secret', 'data:image/svg+xml;base64,PHN2Zz4=', 'data:image/png;base64,not!base64'):
            with self.assertRaises(ai_store.StoreError):
                ai_chart.image_data(value)
        self.cfg['vision'] = False
        ai_store.save(self.root, self.cfg)
        with self.assertRaises(ai_store.StoreError):
            self.analyze({**self.body(), 'image': 'data:image/png;base64,' + 'A' * 100})

    def test_live_snapshot_rejects_stale_tick_and_actual_stocks(self):
        tick = {'ms': int(NOW * 1000), 'bid': 101, 'ask': 101.05}
        with patch.object(song, 'tick', return_value=tick), patch('so_cong_khai.ai_chart.time.time', return_value=NOW):
            with patch.dict(song._tt, {'mt5': SimpleNamespace(symbol_info=lambda _: SimpleNamespace(trade_calc_mode=32))}):
                with self.assertRaisesRegex(ai_store.StoreError, 'forex'):
                    ai_chart.snapshot({}, 'AAPL', 'M15', 30)
        with patch.object(song, 'tick', return_value={**tick, 'ms': int((NOW - 90) * 1000)}), patch('so_cong_khai.ai_chart.time.time', return_value=NOW):
            with self.assertRaisesRegex(ai_store.StoreError, 'cũ'):
                ai_chart.snapshot({}, 'XAUUSD', 'M15', 30)

    def test_trusted_candles_and_multiframe_symbol_match(self):
        tick = {'ms': int(NOW * 1000), 'bid': 101, 'ask': 101.05}
        def bars(mt5, ma, tf, n):
            self.assertEqual(ma, 'EURUSD.r')
            from so_cong_khai import gia
            period = pd.Timedelta(minutes=gia.KHUNG[tf])
            idx = pd.date_range(end=pd.Timestamp(NOW, unit='s', tz='UTC') - period, periods=240, freq=period)
            return pd.DataFrame({'open': 100., 'high': 102., 'low': 98., 'close': 101.}, index=idx)
        symbol = SimpleNamespace(trade_calc_mode=0, digits=5, point=.00001)
        with patch.object(song, 'tick', return_value=tick), patch('so_cong_khai.ai_chart.time.time', return_value=NOW), patch.dict(song._tt, {'mt5': SimpleNamespace(symbol_info=lambda _: symbol)}), patch.object(da_ma_module(), '_nen', side_effect=bars):
            snap = ai_chart.snapshot({}, 'EURUSD.r', 'M15', 30)
        self.assertEqual(snap['symbol'], 'EURUSD.r')
        self.assertEqual(set(snap['frames']), {'M15', 'M30', 'H1', 'H4', 'D1'})


def da_ma_module():
    from so_cong_khai import da_ma
    return da_ma


class PlatformHTTP(unittest.TestCase):
    # Reuse only the real HTTP/session harness.
    setUp = auth_http.ChartHTTP.setUp
    tearDown = auth_http.ChartHTTP.tearDown
    start = auth_http.ChartHTTP.start
    stop = auth_http.ChartHTTP.stop
    req = auth_http.ChartHTTP.req
    signup = auth_http.ChartHTTP.signup

    def test_ai_owner_and_customer_permissions(self):
        self.assertEqual(self.req(self.a, '/api/ai-platform/admin')[0], 401)
        self.assertEqual(self.req(self.a, '/api/ai-platform/analyze', {})[0], 401)
        owner = self.signup(self.a, 'ai_owner')
        client = self.signup(self.b, 'ai_client')
        self.assertEqual(self.req(self.b, '/api/ai-platform/admin')[0], 403)
        for path, data in (('settings', {'settings': ai_store.DEFAULT}), ('key', {'provider': 'openai', 'key': 'fake-key-not-used'}),
                           ('grant', {'uid': client, 'plan': 'premium', 'expires': NOW + 99999999})):
            self.assertEqual(self.req(self.b, '/api/ai-platform/' + path, data)[0], 403)
        self.assertEqual(self.req(self.a, '/api/ai-platform/settings', {'settings': copy.deepcopy(ai_store.DEFAULT)}, owner)[0], 200)
        self.assertEqual(self.req(self.a, '/api/ai-platform/settings', {'settings': copy.deepcopy(ai_store.DEFAULT)}, client)[0], 409)
        for path in ('/api/ai', '/api/ai-chi-bao', '/api/gia-su'):
            self.assertIn(self.req(self.b, path, {})[0], (400, 403))
        self.assertEqual(self.req(self.b, '/api/cai-dat', {'viec': 'luu', 'gia_tri': {'tin_tuc.bat': False}})[0], 403)
        grant = {'uid': client, 'plan': 'pro', 'expires': NOW + 99999999}
        self.assertEqual(self.req(self.a, '/api/ai-platform/grant', grant)[0], 200)
        st = self.req(self.b, '/api/ai-platform/status')[1]
        self.assertEqual(st['account']['plan'], 'pro')
        self.assertNotIn('settings', st)
        self.assertNotIn('keys', st)


if __name__ == '__main__':
    unittest.main()
