"""Shared subscription/quota path for the existing evidence-based explanations."""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from so_cong_khai import ai_evidence, ai_store
from test_ai_platform import market, USER, NOW
from test_ai_giai_thich import du_lieu, PT, tra_loi, LN


class EvidencePlatform(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'fake-for-test'})
        self.env.start()
        cfg = copy.deepcopy(ai_store.DEFAULT)
        cfg.update(enabled=True, free_questions=1)
        ai_store.save(self.root, cfg)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def evidence(self, cfg, ma, tf, now, **kw):
        return LN.chup({'gia': {}}, ma, tf, now, goi=lambda: du_lieu(), phan_tich_fn=lambda: PT)

    def call(self, body, fn=None):
        def coherent_market(*args):
            snapshot = market()
            snapshot.update(bid=du_lieu()['bid'], ask=du_lieu()['ask'])
            return snapshot
        return ai_evidence.analyze(self.root, {'gia': {}}, self.root, USER, body, snapshot_fn=coherent_market,
                                   evidence_fn=self.evidence, provider_fn=fn or self.provider, clock=lambda: NOW)

    def provider(self, *args):
        return {'text': json.dumps(tra_loi()), 'complete': True, 'model': 'owner-selected-model', 'input_tokens': 100, 'output_tokens': 200}

    def test_evidence_ids_preserved_with_shared_free_allowance(self):
        body = {'ma': 'XAUUSD', 'tf': 'M15', 'che_do': 'chart', 'request_id': ai_store.new_id()}
        fn = Mock(side_effect=self.provider)
        r = self.call(body, fn)
        self.assertTrue(r['ok'], r)
        self.assertEqual(r['tra_loi']['quan_sat'][0]['bang_chung'], ['E_CB_RSI'])
        self.assertEqual(r['account']['remaining'], 0)
        self.assertEqual(self.call(body, fn), r)
        self.assertEqual(fn.call_count, 1)
        self.assertEqual(ai_store.status(self.root, USER, NOW)['account']['remaining'], 0)

    def test_customer_cannot_read_legacy_owner_plan(self):
        with self.assertRaises(ai_store.StoreError) as e:
            self.call({'ma': 'XAUUSD', 'tf': 'M15', 'che_do': 'review', 'phieu': 'KH-abcdefghi', 'request_id': ai_store.new_id()})
        self.assertEqual(e.exception.status, 403)

    def test_mismatched_quote_is_rejected_before_any_paid_call(self):
        provider = Mock(side_effect=AssertionError('No paid call'))
        with self.assertRaisesRegex(ai_store.StoreError, 'lệch'):
            ai_evidence.analyze(self.root, {'gia':{}}, self.root, USER,
                                {'ma':'XAUUSD','tf':'M15','che_do':'chart','request_id':ai_store.new_id()},
                                snapshot_fn=market, evidence_fn=self.evidence, provider_fn=provider, clock=lambda:NOW)
        provider.assert_not_called()

    def test_invalid_evidence_and_model_json_refund_allowance(self):
        def bad(*args):
            return {'text': json.dumps(tra_loi(tom_tat='Bịa 99999', quan_sat=[])), 'complete': True, 'model': 'test', 'input_tokens': 100, 'output_tokens': 200}
        r = self.call({'ma': 'XAUUSD', 'tf': 'M15', 'che_do': 'chart', 'request_id': ai_store.new_id()}, bad)
        self.assertFalse(r['ok'])
        self.assertEqual(r['account']['remaining'], 1)


if __name__ == '__main__':
    unittest.main()
