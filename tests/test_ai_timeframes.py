"""Closed-bar causality, shared M5/M15/M30 context and manual scanner boundaries."""
import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from so_cong_khai import ai_chart, ai_local, ai_store, ai_timeframes as context, ai_ui, phan_tich, tin_hieu_ngan as scanner
from test_ai_platform import market, NOW
from test_chart_pro import node
from test_tin_hieu_ngan import _nen, NOW as SCAN_NOW
import test_chart_auth_http as auth_http


def snapshot(tf='M15'):
    result=market();result['timeframe']=tf
    return result


class Context(unittest.TestCase):
    def test_required_frames_and_both_sides(self):
        expected={'M5':('M5','M15','H1','H4','D1'),'M15':('M15','M30','H1','H4','D1'),'M30':('M30','H1','H4','D1')}
        for tf,needed in expected.items():
            with self.subTest(tf=tf):
                self.assertEqual(context.required(tf),needed)
                result=context.assess(snapshot(tf))
                self.assertTrue(result['aligned'])
                self.assertEqual(result['bias'],1)
                bearish=snapshot(tf)
                for frame in bearish['frames'].values():
                    frame.update(close=90.,ema20=95.,ema50=96.,ema200=100.)
                self.assertEqual(context.assess(bearish)['bias'],-1)

    def test_missing_future_stale_bridge_or_conflicting_macro_stands_aside(self):
        for tf in context.ENTRY_FRAMES:
            for cause in ('missing','future','stale','opposite','macro'):
                snap=snapshot(tf);bridge=context.BRIDGE[tf]
                if cause=='missing':
                    del snap['frames'][bridge]
                elif cause=='future':
                    snap['frames'][bridge]['last_closed_candle_open_at']=NOW
                elif cause=='stale':
                    snap['frames'][bridge]['last_closed_candle_open_at']=NOW-999999
                elif cause=='opposite':
                    snap['frames'][bridge].update(close=95.,ema20=98.,ema50=99.)
                else:
                    snap['frames']['D1']['ema200']=200.
                with self.subTest(tf=tf,cause=cause):
                    self.assertFalse(context.assess(snap)['aligned'])
                    self.assertEqual(context.filter_candidates(snap,ai_chart.candidates(snap,ai_store.DEFAULT)),[])
                    request={'ma':'XAUUSD','tf':tf,'lang':'en','mode':'entry'}
                    result=ai_local.read_snapshot(snap,ai_store.DEFAULT,request,clock=lambda:NOW)
                    self.assertEqual(result['analysis']['scenarios'],[])

    def test_api_and_free_reader_share_same_context_and_direction(self):
        for tf in context.ENTRY_FRAMES:
            snap=snapshot(tf)
            req={'ma':'XAUUSD','tf':tf,'lang':'vi','mode':'entry'}
            result=ai_local.read_snapshot(snap,ai_store.DEFAULT,req,clock=lambda:NOW)
            self.assertEqual(result['topdown'],context.assess(snap))
            self.assertTrue(result['analysis']['scenarios'])
            self.assertTrue(all(choice['side']=='MUA' for choice in context.filter_candidates(snap,ai_chart.candidates(snap,ai_store.DEFAULT))))
            self.assertFalse(result['topdown']['profitability_proven'])
            json.dumps(result,allow_nan=False)

    def test_raw_frame_reader_never_uses_running_higher_bars(self):
        frames={tf:_nen(minutes) for tf,minutes in {'M5':5,'M15':15,'M30':30,'H1':60,'H4':240,'D1':1440}.items()}
        at=SCAN_NOW.timestamp()
        first=context.from_frames(frames,'M5',at)
        future=copy.deepcopy(frames)
        for tf,bars in future.items():
            future[tf]=pd.concat([bars,pd.DataFrame([[1.,99999.,.01,1.]],columns=bars.columns,index=[SCAN_NOW])])
        self.assertTrue(first['aligned'])
        self.assertEqual(first,context.from_frames(future,'M5',at))

    def test_manual_topdown_blocks_setup_without_changing_legacy_scanner(self):
        frames={tf:_nen(minutes) for tf,minutes in {'M5':5,'M15':15,'M30':30,'H1':60,'H4':240,'D1':1440}.items()}
        frames['H4']=_nen(240,-1)
        tick=SimpleNamespace(bid=float(frames['M5'].close.iloc[-1]),ask=float(frames['M5'].close.iloc[-1])+.02,time_msc=int(SCAN_NOW.timestamp()*1000))
        symbol=SimpleNamespace(visible=True,trade_calc_mode=4,trade_tick_size=.01,point=.01,digits=2)
        mt=SimpleNamespace(symbol_info=lambda ma:symbol,symbol_info_tick=lambda ma:tick)
        def bars(mt,ma,tf,n):
            return frames[tf].tail(n)
        legacy=scanner.quet(frames,SCAN_NOW,tick,buoc_gia=.01,so_le=2)
        self.assertTrue(all(row['trang_thai']=='dat' for row in legacy))
        with patch.object(scanner.da_ma,'_mt5',return_value=mt),patch.object(scanner.da_ma,'_nen',side_effect=bars):
            result=scanner.doc({'gia':{}},'XAUUSD',SCAN_NOW,topdown=True)
        self.assertTrue(all(row['trang_thai']=='khung_lon' for row in result['ds']))
        self.assertTrue(all('vao' not in row and 'tp' not in row for row in result['ds']))

    def test_manual_m15_analysis_requests_context(self):
        data={'ma':'XAUUSD','luc':'2026-11-28','ds':[{'tf':'M15','trang_thai':'khung_lon','topdown':context.assess(snapshot())}]}
        with patch.object(scanner,'doc',return_value=data) as call:
            result=phan_tich.ngan({},'XAUUSD','M15')
        self.assertEqual(call.call_args.kwargs,{'khung':'M15','topdown':True})
        self.assertEqual(result['boi_canh']['topdown']['entry_timeframe'],'M15')
        self.assertEqual(result['con_hieu_luc'],0)

    def test_manual_reference_levels_respect_broker_minimum_stop(self):
        frames={tf:_nen(minutes) for tf,minutes in {'M5':5,'M15':15,'M30':30,'H1':60,'H4':240,'D1':1440}.items()}
        tick=SimpleNamespace(bid=float(frames['M5'].close.iloc[-1]),ask=float(frames['M5'].close.iloc[-1])+.02,time_msc=int(SCAN_NOW.timestamp()*1000))
        symbol=SimpleNamespace(visible=True,trade_calc_mode=4,trade_tick_size=.01,point=.01,digits=2,trade_stops_level=100000)
        mt=SimpleNamespace(symbol_info=lambda ma:symbol,symbol_info_tick=lambda ma:tick)
        with patch.object(scanner.da_ma,'_mt5',return_value=mt),patch.object(scanner.da_ma,'_nen',side_effect=lambda mt,ma,tf,n:frames[tf].tail(n)):
            result=scanner.doc({'gia':{}},'XAUUSD',SCAN_NOW,topdown=True)
        self.assertEqual(result['phien_ban'],'ngan-topdown-v1')
        self.assertTrue(all(row['trang_thai']=='muc_gia' for row in result['ds']))
        self.assertTrue(all('tp' not in row for row in result['ds']))

    def test_context_ui_escapes_symbolic_values_and_shows_closed_times(self):
        start=ai_ui.CHART_JS.index('function renderContext(')
        end=ai_ui.CHART_JS.index('function renderResult(',start)
        ctx=context.assess(snapshot('M5'))
        ctx['rows'][0]['timeframe']='<img src=x onerror=alert(1)>'
        code="const document={documentElement:{lang:'vi'}},esc=s=>String(s??'').replace(/[&<>\"']/g,c=>'&#'+c.charCodeAt(0)+';');\n"
        html=node(code+ai_ui.CHART_JS[start:end]+'console.log(JSON.stringify(renderContext({topdown:'+json.dumps(ctx)+'})));')
        self.assertIn('UTC+7',html)
        self.assertIn('Khung nối',html)
        self.assertIn('không phải xác suất thắng',html)
        self.assertNotIn('<img',html)
        self.assertIn('&#60;img',html)


class ContextHTTP(unittest.TestCase):
    setUp,tearDown,start,stop=auth_http.ChartHTTP.setUp,auth_http.ChartHTTP.tearDown,auth_http.ChartHTTP.start,auth_http.ChartHTTP.stop
    req,signup=auth_http.ChartHTTP.req,auth_http.ChartHTTP.signup

    def test_three_manual_frames_route_to_same_observation_contract(self):
        owner=self.signup(self.a,'topdown_owner')
        for tf in context.ENTRY_FRAMES:
            data={'khung_phan_tich':tf,'quy_trinh_ngan':True,'phuong_phap':[],'phuong_an':[]}
            with self.subTest(tf=tf),patch.object(phan_tich,'ngan',return_value=data) as reader:
                status,result,_=self.req(self.a,f'/api/phan-tich?tf={tf}&ma=XAUUSD&topdown=1',None,owner)
                self.assertEqual(status,200,result)
                self.assertEqual(result['khung_phan_tich'],tf)
                self.assertEqual(reader.call_args.args[1:],('XAUUSD',tf))


if __name__=='__main__':
    unittest.main()
