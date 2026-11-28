"""Shared prices, scope, no research broadcasts and honest prospective outcomes."""
import copy
from contextlib import closing
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from so_cong_khai import canh_bao,entry_costs,entry_feed,entry_plans as P,diem_vao_rt
from test_chart_pro import node

NOW=datetime(2026,11,28,5,0,10,tzinfo=timezone.utc)


def snapshot(now=NOW):
    closed=now.replace(second=0,microsecond=0)
    return {'ma':'XAUUSDp','account_scope':'scope-a','may_chu':'demo','nguon':'mt5','phien_ban':'ngan-topdown-v1',
            'luc':now.isoformat(),'tick_ms':int(now.timestamp()*1000),'bid':100.,'ask':100.1,'so_le':2,'buoc_gia':.01,
            'ds':[{'tf':'M30','trang_thai':'dat','loai':'hoi_ema','huong':'MUA','vao':100.1,'sl':99.,'tp':101.75,'rr':1.5,
                   'dong':closed.isoformat(),'het':(closed+timedelta(seconds=120)).isoformat(),'atr':1.,'moc':100.,'day':99.2,'dinh':100.5}]}


class SharedPlans(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.out=Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()

    def test_first_prices_survive_refresh_restart_and_alert_path(self):
        a=snapshot();P.apply(self.out,a,now=NOW)
        b=snapshot();b['ask']=100.12;b['ds'][0].update(vao=100.12,tp=102.)
        P.apply(self.out,b,now=NOW)
        self.assertEqual(a['ds'][0]['plan_id'],b['ds'][0]['plan_id'])
        self.assertEqual((b['ds'][0]['vao'],b['ds'][0]['sl'],b['ds'][0]['tp']),(100.1,99.,101.75))
        b['shared_plan_version']=P.VERSION
        alerts=canh_bao.ngan_han(b)
        self.assertEqual(alerts[0]['plan_ids'],[a['ds'][0]['plan_id']])
        self.assertEqual(alerts[0]['tin_hieu'][0]['tp'],101.75)
        self.assertEqual(len(canh_bao.ghi_moi(self.out,alerts,NOW)),1)
        self.assertEqual(canh_bao.ghi_moi(self.out,alerts,NOW),[])
        with closing(sqlite3.connect(self.out/P.DB)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM plans').fetchone()[0],1)

    def test_two_accounts_and_strategy_versions_never_merge(self):
        d=snapshot();r=d['ds'][0]
        a=P.register(self.out,d,r,strategy='v1',now=NOW)
        b=P.register(self.out,{**d,'account_scope':'scope-b'},r,strategy='v1',now=NOW)
        c=P.register(self.out,d,r,strategy='v2',now=NOW)
        self.assertEqual(len({p['id'] for p in (a,b,c)}),3)
        self.assertEqual(len(P.summary(self.out,'scope-a','XAUUSDp')['rows']),2)

    def test_overlapping_group_never_rebroadcasts_an_existing_plan(self):
        data=snapshot();P.apply(self.out,data,now=NOW);data['shared_plan_version']=P.VERSION
        first=canh_bao.ngan_han(data)
        self.assertEqual(len(canh_bao.ghi_moi(self.out,first,NOW)),1)
        second=copy.deepcopy(data['ds'][0]);second.update(tf='M15',plan_id='EP-second')
        data['ds'].append(second)
        alerts=canh_bao.ghi_moi(self.out,canh_bao.ngan_han(data),NOW)
        self.assertEqual(len(alerts),1)
        self.assertEqual(alerts[0]['plan_ids'],['EP-second'])
        self.assertEqual([r['tf'] for r in alerts[0]['tin_hieu']],['M15'])
        self.assertEqual(canh_bao.ghi_moi(self.out,canh_bao.ngan_han(data),NOW),[])

    def test_stale_future_nan_or_missing_account_is_not_registered(self):
        for change in ('stale','future','nan','scope'):
            d=snapshot();r=d['ds'][0]
            if change=='stale': d['tick_ms']-=31_000
            elif change=='future': d['tick_ms']+=6_000
            elif change=='nan':r['atr']=float('nan')
            else:d.pop('account_scope')
            self.assertIsNone(P.register(self.out,d,r,strategy='v1',now=NOW),change)

    def test_failed_plan_storage_removes_actionable_prices(self):
        d=snapshot()
        with patch.object(entry_feed.T,'doc',return_value=d),patch.object(entry_costs,'estimate',return_value={}),patch.object(P,'apply',side_effect=sqlite3.OperationalError('locked')):
            result=entry_feed.doc({},'XAUUSDp',NOW,out=self.out)
        self.assertEqual(result['ds'][0]['trang_thai'],'ke_hoach_loi')
        self.assertNotIn('vao',result['ds'][0])
        self.assertEqual(canh_bao.ngan_han(result),[])

    def test_research_has_own_ledger_and_never_becomes_alert(self):
        d=snapshot();r=d['ds'][0]
        p=P.register(self.out,d,r,strategy='research1',channel='research',hold_minutes=1080,now=NOW)
        self.assertEqual(p['hold_minutes'],1080)
        d['ds']=[{**r,'channel':'research','plan_id':p['id']}];d['shared_plan_version']=P.VERSION
        self.assertEqual(canh_bao.ngan_han(d),[])
        self.assertFalse(P.summary(self.out,'scope-a','XAUUSDp')['promotion_allowed'])

    def test_busy_research_does_not_inflate_entry_count(self):
        d=snapshot();P.register(self.out,d,d['ds'][0],strategy='research',channel='research',now=NOW)
        later=NOW+timedelta(minutes=30);d=snapshot(later)
        P.register(self.out,d,d['ds'][0],strategy='research',channel='research',now=later)
        row=P.summary(self.out,'scope-a','XAUUSDp')['rows'][0]
        self.assertEqual((row['plans'],row['open'],row['blocked']),(2,1,1))

    def test_tick_costs_are_modeled_not_verified_and_gap_is_unknown(self):
        d=snapshot();p=P.register(self.out,d,d['ds'][0],strategy='research',now=NOW)
        with closing(P.connect(self.out)) as db:
            track=dict(db.execute('SELECT * FROM tracking').fetchone())
        at=int(NOW.timestamp()*1000)
        answer=P.score(p,track,[(at+1_000,102.,102.1)],at+2_000)
        self.assertEqual(answer['state'],'tp')
        self.assertIsNotNone(answer['model_net_r']);self.assertIsNone(answer['verified_net_r'])
        answer=P.score(p,track,[(at+121_000,102.,102.1)],at+122_000)
        self.assertEqual(answer['state'],'unknown_gap');self.assertNotIn('model_net_r',answer)

    def test_time_exit_and_overnight_cost_missing_are_not_fake_net_profit(self):
        d=snapshot();p=P.register(self.out,d,d['ds'][0],strategy='research',now=NOW)
        track={'last_ms':p['captured_ms'],'fill':100.15,'risk':1.15,'cost_body':json.dumps({'commission_price':.18,'slippage_price':.05})}
        p['hold_minutes']=0
        answer=P.score(p,track,[(track['last_ms']+1_000,100.5,100.6)],track['last_ms']+2_000)
        self.assertEqual(answer['state'],'time')
        p['captured_ms']-=86_400_000
        answer=P.score(p,track,[(track['last_ms']+1_000,100.5,100.6)],track['last_ms']+2_000)
        self.assertIsNone(answer['model_net_r'])

    def test_js_locked_plan_keeps_entry_stop_and_target_on_live_quote(self):
        plan={'co':True,'hieu_luc':True,'quan_sat':True,'plan_id':'EP-1','plan_locked':True,'huong':'MUA',
              'vao':100.,'sl':99.,'tp':[101.5],'rr':[1.5],'ma':'ngan:M30:hoi_ema',
              'thuc_thi':{'loai':'tt','tu':NOW.isoformat(),'het':(NOW+timedelta(seconds=120)).isoformat(),
                          'moc':100.,'ngan':{'day':98.,'dinh':101.,'buoc':.01}}}
        q={'ms':int(NOW.timestamp()*1000),'bid':100.03,'ask':100.1,'ma':'XAUUSDp'}
        code='globalThis.window=globalThis;'+diem_vao_rt.JS+'\nconsole.log(JSON.stringify(ENTRY_RT.xem('+json.dumps(plan)+','+json.dumps(q)+','+str(q['ms'])+',1,2,new Map())));'
        result=node(code)
        self.assertEqual((result['vao'],result['sl'],result['tp']),(100.,99.,[101.5]))
        self.assertTrue(result['hieu_luc'])
        plan['thuc_thi']['stops'] = 1.10
        blocked = node('globalThis.window=globalThis;'+diem_vao_rt.JS+'\nconsole.log(JSON.stringify(ENTRY_RT.xem('+
                       json.dumps(plan)+','+json.dumps(q)+','+str(q['ms'])+',1,2,new Map())));')
        self.assertFalse(blocked['hieu_luc'])
        self.assertEqual(blocked['rt'], 'sai_muc')
        self.assertEqual((blocked['vao'], blocked['sl'], blocked['tp']), (100., 99., [101.5]))

    def test_chart_and_alert_feed_request_same_context_scanner(self):
        d=snapshot();d['ds']=[]
        with patch.object(entry_feed.T,'doc',return_value=d) as reader:
            entry_feed.doc({},'XAUUSDp',khung='M30',out=self.out)
        self.assertEqual(reader.call_args.kwargs,{'khung':'M30','topdown':True})


class ActualCosts(unittest.TestCase):
    def test_missing_history_stays_assumed_and_matching_positions_calibrate(self):
        entry_costs._cache.clear()
        account=SimpleNamespace(server='demo',login=12,currency='USD')
        scope=entry_costs.account_scope(account)
        deals=[]
        for i in range(10):
            for way in (0,1):
                deals.append(SimpleNamespace(symbol='XAUUSDp',type=0,entry=way,position_id=i+1,volume=1.,commission=-3.,fee=0.))
        mt=SimpleNamespace(account_info=lambda:account,symbol_info=lambda s:SimpleNamespace(trade_tick_value_loss=1.,trade_tick_size=.01),history_deals_get=lambda *a:deals)
        with patch.object(entry_feed.T.da_ma,'_mt5',return_value=mt):
            result=entry_costs.estimate({'gia':{}},{'ma':'XAUUSDp','account_scope':scope},NOW)
        self.assertAlmostEqual(result['commission_price'],.06)
        self.assertEqual(result['commission_positions'],10)
        self.assertFalse(result['fully_verified'])
        self.assertEqual(entry_costs.estimate({}, {'ma':'XAUUSDp'},NOW)['commission_price'],.18)


if __name__=='__main__':unittest.main()
