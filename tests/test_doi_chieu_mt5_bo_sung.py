"""Không ghép nhầm tài khoản/lệnh và không thay đổi nhật ký gốc khi bổ sung MT5."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

from so_cong_khai import doi_chieu_mt5 as d, telegram_nhom as tg


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 27, 12, tzinfo=timezone.utc)
        self.t = self.now - timedelta(days=3)
        self.k = {'mt5_doi_chieu': {'terminal': 'demo.exe', 'so': '123456', 'may_chu': 'Demo'}}
        self.entry = {'side': 'SELL', 'opened': self.t, 'lots': .02, 'entry': 3700., 'ma': 'XAUUSD', 'sl': 3750., 'tp': 3600.}
        self.ea = {'trades': [], 'open': dict(self.entry), 'orphans': [], 'last_time': self.now - timedelta(hours=9)}
        self.deal = {'ve': 2345, 'ma': 'XAUUSD', 'side': 'SELL', 'lots': .02, 'entry': 3700., 'pnl': -100.,
                     'opened': (self.t - timedelta(seconds=22)).isoformat(), 'closed_at': (self.t + timedelta(hours=1)).isoformat(), 'ea': 'EA M'}
        self.snap = {'ok': True, 'luc': self.now.isoformat(), 'danh_tinh': d._key(self.k), 'so': '•••456',
                     'da_dong': [self.deal], 'mo': [], 'su_kien': [], 'khong_ho_tro': []}

    def reconcile(self, snap=None, ea=None):
        return d.bo_sung(self.k, [('EA M', ea or self.ea)], self.now, anh=snap or self.snap)

    def test_missing_close_preserves_original_and_negative_result(self):
        original = copy.deepcopy(self.ea)
        eas, meta = self.reconcile()
        self.assertEqual(self.ea, original)
        self.assertIsNone(eas[0][1]['open'])
        self.assertEqual(eas[0][1]['trades'][0]['pnl'], -100)
        self.assertEqual(eas[0][1]['trades'][0]['nguon_dong'], 'MT5')
        self.assertEqual(meta['bo_sung'], 1)
        self.assertTrue(meta['xac_minh'])

    def test_delayed_close_uses_actual_time_and_retains_log_time(self):
        ea = copy.deepcopy(self.ea)
        ea['open'] = None
        ea['trades'] = [{**self.entry, 'pnl': -100., 'closed_at': self.t + timedelta(days=1)}]
        eas, meta = self.reconcile(ea=ea)
        r = eas[0][1]['trades'][0]
        self.assertEqual(r['closed_at'], d._dt(self.deal['closed_at']))
        self.assertEqual(r['closed_at_nhat_ky'], self.t + timedelta(days=1))
        self.assertEqual(meta['chinh_gio'], 1)
        self.assertTrue(meta['xac_minh'])

    def test_different_symbol_ea_side_volume_price_or_time_cannot_match(self):
        for field, value in [('ma', 'EURUSD'), ('ea', 'EA X'), ('side', 'BUY'), ('lots', .021), ('entry', 3701.),
                             ('opened', (self.t - timedelta(minutes=2)).isoformat())]:
            with self.subTest(field=field):
                s = copy.deepcopy(self.snap); s['da_dong'][0][field] = value
                eas, meta = self.reconcile(s)
                self.assertEqual(meta['bo_sung'], 0)
                self.assertFalse(meta['xac_minh'])
                self.assertIsNotNone(eas[0][1]['open'])

    def test_ambiguous_duplicates_never_pick_one(self):
        s = copy.deepcopy(self.snap)
        s['da_dong'].append({**self.deal, 've': 2346})
        _, meta = self.reconcile(s)
        self.assertFalse(meta['xac_minh'])
        self.assertEqual(meta['bo_sung'], 0)

    def test_fee_mismatch_unlogged_activity_and_complex_closes_stay_unverified(self):
        ea = copy.deepcopy(self.ea);ea['open'] = None
        ea['trades'] = [{**self.entry, 'pnl': -101., 'closed_at': d._dt(self.deal['closed_at'])}]
        self.assertFalse(self.reconcile(ea=ea)[1]['xac_minh'])
        for more in ({'khong_ho_tro': ['EA M']}, {'su_kien': [{'ea': 'EA M', 'luc': self.now.isoformat()}]}):
            self.assertFalse(self.reconcile({**self.snap, **more})[1]['xac_minh'])

    def test_fresh_cache_requires_exact_identity_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(d.duong, 'goc_du_lieu', return_value=Path(tmp)):
            path = d._tep(self.k);path.parent.mkdir(parents=True)
            def write(s):path.write_text(json.dumps(s), encoding='utf-8')
            write(self.snap)
            self.assertIsNotNone(d.doc(self.k, self.now))
            for bad in ({'danh_tinh': 'other'}, {'luc': (self.now-timedelta(seconds=d.HAN+1)).isoformat()},
                        {'luc': (self.now+timedelta(minutes=1)).isoformat()}, {'ok': False}, {'mo': None}):
                write({**self.snap, **bad});self.assertIsNone(d.doc(self.k, self.now))
            path.write_text('{', encoding='utf-8');self.assertIsNone(d.doc(self.k, self.now))

    def test_malformed_or_nonfinite_proof_never_breaks_report(self):
        for value in (float('nan'), float('inf'), None):
            s = copy.deepcopy(self.snap);s['da_dong'][0]['pnl'] = value
            self.assertFalse(self.reconcile(s)[1]['san_sang'])

    def test_one_position_cannot_close_two_journal_entries(self):
        ea = copy.deepcopy(self.ea);ea['orphans'] = [dict(self.entry)]
        _, meta = self.reconcile(ea=ea)
        self.assertEqual(meta['bo_sung'], 1)
        self.assertFalse(meta['xac_minh'])

    def test_live_position_is_verified_without_inventing_close(self):
        s = copy.deepcopy(self.snap);s['mo'] = [s['da_dong'].pop()]
        eas, meta = self.reconcile(s)
        self.assertTrue(meta['xac_minh'])
        self.assertEqual(eas[0][1]['trades'], [])
        self.assertIsNotNone(eas[0][1]['open'])

    def test_historical_evidence_survives_disconnect_but_is_not_live_verification(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(d.duong, 'goc_du_lieu', return_value=Path(tmp)):
            path = d._tep(self.k);path.parent.mkdir(parents=True)
            path.write_text(json.dumps({**self.snap, 'loi_doc_cuoi': 'offline'}), encoding='utf-8')
            self.assertIsNone(d.doc(self.k, self.now))
            self.assertIsNotNone(d.doc(self.k, self.now, lich_su=True))
            eas, meta = d.bo_sung(self.k, [('EA M', self.ea)], self.now)
            self.assertEqual(meta['bo_sung'], 1)
            self.assertFalse(meta['san_sang'])
            self.assertFalse(meta['xac_minh'])


class WorkerTests(unittest.TestCase):
    def test_refuses_account_change_and_incomplete_reads_and_includes_entry_fees(self):
        now = datetime(2026, 11, 27, 12, tzinfo=timezone.utc)
        a = NS(login=123456, server='Demo', trade_mode=0, balance=100)
        v = NS(type=1, entry=0, magic=7, position_id=11, time=int((now-timedelta(hours=2)).timestamp()),
               symbol='XAUUSD', volume=.01, price=3700, profit=0, commission=-.1, swap=0, fee=0)
        r = NS(**{**vars(v), 'type': 0, 'entry': 1, 'time': int((now-timedelta(hours=1)).timestamp()),
                  'price': 3710, 'profit': -10, 'commission': -.1, 'swap': -.2})
        class Fake:
            ACCOUNT_TRADE_MODE_DEMO = 0
            def __init__(self):self.accounts=[a,a];self.pos=[];self.deals=[v,r];self.closed=False
            def account_info(self):return self.accounts.pop(0)
            def terminal_info(self):return NS(connected=True)
            def positions_get(self):return self.pos
            def history_deals_get(self,*args):return self.deals
            def shutdown(self):self.closed=True
        with tempfile.TemporaryDirectory() as tmp, patch.object(d.noi_mt5, 'noi', return_value=(True, '')):
            p=Path(tmp)/'EAPromax_M_XAUUSD_7_123456_events.csv'
            p.write_text('time_server,event,equity,detail\n2026.11.27 09:00:00,init,100,version=v1\n',encoding='utf-8')
            k={'mt5_doi_chieu': {'terminal':'demo.exe','so':'123456','may_chu':'Demo'},'ea':[{'ten':'EA M','tep':str(p)}]}
            cfg={'mt5_xem':{'magic':{'7':'EA M'}}}
            f=Fake();out=d.chup(f,cfg,k,now)
            self.assertTrue(out['ok']);self.assertAlmostEqual(out['da_dong'][0]['pnl'],-10.4)
            self.assertNotIn('123456',json.dumps(out))
            self.assertTrue(f.closed)
            f=Fake();f.accounts=[a,NS(login=999,server='Demo',trade_mode=0)]
            self.assertFalse(d.chup(f,cfg,k,now)['ok']);self.assertTrue(f.closed)
            f=Fake();f.pos=None;self.assertFalse(d.chup(f,cfg,k,now)['ok'])
            f=Fake();f.accounts=[NS(**{**vars(a),'trade_mode':2})]
            self.assertFalse(d.chup(f,cfg,k,now)['ok'])
            f=Fake();f.deals=[v,r,NS(**{**vars(r),'entry':1})]
            out=d.chup(f,cfg,k,now);self.assertEqual(out['da_dong'],[]);self.assertEqual(out['khong_ho_tro'],['EA M'])


class TransportTests(unittest.TestCase):
    def test_restart_does_not_hide_last_failed_delivery(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(tg.TT, {}, clear=True), patch.object(tg, 'token', return_value='secret'):
            root=Path(tmp);(root/'du-lieu').mkdir()
            (root/'du-lieu/telegram.json').write_text(json.dumps({'che_do':'gui','chat':'-10012345'}),encoding='utf-8')
            (root/'du-lieu/telegram-tin.json').write_text(json.dumps([{'che_do':'gui','ok':False,'loi':'disconnected'}]),encoding='utf-8')
            self.assertEqual(tg.muc_suc_khoe(root)['muc'],'chu_y')
    def test_form_unicode_and_nested_json_with_no_secret_in_error(self):
        import urllib.error
        import urllib.parse
        calls = []
        def fake(req, timeout):
            calls.append(req)
            raise urllib.error.URLError('token-abc was disconnected')
        with patch.object(tg.urllib.request, 'urlopen', side_effect=fake):
            r = tg._goi('token-abc', 'sendMessage', {'text': 'Kiểm tra ✓', 'chat_id': '-10001',
                       'disable_web_page_preview': True, 'reply_parameters': {'message_id': 7}})
        self.assertFalse(r['ok']);self.assertNotIn('token-abc', r['description'])
        self.assertEqual(len(calls), 1)  # no blind resend after an ambiguous network failure
        req = calls[0]
        self.assertIn('application/x-www-form-urlencoded', req.headers['Content-type'])
        body = urllib.parse.parse_qs(req.data.decode())
        self.assertEqual(body['text'], ['Kiểm tra ✓'])
        self.assertEqual(body['disable_web_page_preview'], ['true'])
        self.assertEqual(json.loads(body['reply_parameters'][0]), {'message_id': 7})


if __name__ == '__main__':
    unittest.main()
