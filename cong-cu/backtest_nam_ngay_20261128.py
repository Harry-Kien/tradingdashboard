"""Frozen five-day evaluation of the selected release; no provider calls or orders."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sqlite3
import sys

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'out/nam-ngay-20261128'
SELECTED=PROGRAM=None
ai_chart=ai_local=ai_store=ai_timeframes=gia=hoc=sua_gio=scanner=None


def load_runtime():
    global ai_chart,ai_local,ai_store,ai_timeframes,gia,hoc,sua_gio,scanner,SELECTED,PROGRAM
    SELECTED=json.loads((ROOT/'du-lieu/local-release.json').read_text(encoding='utf-8'))
    PROGRAM=Path(SELECTED['program_root'])
    os.environ['HGR_DU_LIEU']=str(ROOT)
    sys.path[:0]=[str(PROGRAM)]
    from so_cong_khai import ai_chart, ai_local, ai_store, ai_timeframes, gia, hoc, sua_gio, tin_hieu_ngan as scanner  # noqa: PLC0415

TZ='Asia/Ho_Chi_Minh'
MINUTE=60_000_000_000
START=pd.Timestamp('2026-11-23',tz=TZ).tz_convert('UTC')
STOP=pd.Timestamp('2026-11-28',tz=TZ).tz_convert('UTC')
WARM=START-pd.Timedelta(days=7)
DAYS=[f'2026-11-{day:02d}' for day in range(23,28)]


def write(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def day(value):
    return pd.Timestamp(value).tz_convert(TZ).date().isoformat()


def simulate(m1,spreads,signals,*,stress=False,swap_fn=None):
    """Fixed targets; exits may be censored, never guessed beyond the archive."""
    times=m1.index.as_unit('ns').asi8
    op,high,low=(m1[k].to_numpy(float) for k in ('open','high','low'))
    sp=np.asarray(spreads)*(2 if stress else 1)
    slip=.05*(2 if stress else 1);fee=.18*(2 if stress else 1)
    trades=[];busy=-1;blocked=invalid=0
    for signal in sorted(signals,key=lambda s:s['at']):
        at=signal['at'];j=int(times.searchsorted(at))
        if at<=busy:
            blocked+=1;continue
        if j>=len(times) or times[j]-at>120*10**9:
            invalid+=1;continue
        sign=1 if signal['side']=='MUA' else -1
        entry=float(op[j]+(sp[j] if sign>0 else 0)+sign*slip)
        sl,target=float(signal['sl']),float(signal['tp'])
        risk=(entry-sl)*sign
        if risk<=0 or (target-entry)*sign<=0 or abs(entry-signal['entry'])>signal['atr']:
            invalid+=1;continue
        deadline=times[j]+int(signal.get('hold_minutes',1440))*MINUTE
        scheduled=int(times.searchsorted(deadline))
        limit=min(scheduled,len(times))
        hi=high[j:limit]+(sp[j:limit] if sign<0 else 0)
        lo=low[j:limit]+(sp[j:limit] if sign<0 else 0)
        stops=lo<=sl if sign>0 else hi>=sl
        profits=hi>=target if sign>0 else lo<=target
        hits=stops|profits;ambiguous=False
        price=None;reason='OPEN';k=None
        if hits.any():
            offset=int(hits.argmax());k=j+offset
            opened=op[k]+(sp[k] if sign<0 else 0)
            if (opened-sl)*sign<=0:
                price=float(opened-sign*slip);reason='SL_GAP'
            elif (opened-target)*sign>=0:
                price=target;reason='TP'
            elif stops[offset]:
                price=sl-sign*slip;reason='SL';ambiguous=bool(profits[offset])
            else:
                price=target;reason='TP'
        elif scheduled<len(times):
            k=scheduled;price=float(op[k]+(sp[k] if sign<0 else 0)-sign*slip);reason='TIME'
        swap=0.
        if k is not None and swap_fn:
            swap=entry*(-.000181 if sign>0 else .000066)*swap_fn(int(times[j]),int(times[k]))
        pnl=(price-entry)*sign-fee+swap if price is not None else None
        trade={**signal,'signal':pd.Timestamp(at,tz='UTC').isoformat(),'day_local':day(pd.Timestamp(at,tz='UTC')),
               'filled_at':pd.Timestamp(times[j],tz='UTC').isoformat(),'entry_fill':entry,'tp_fixed':target,'sl_fixed':sl,
               'risk_fill':risk,'exit_time':pd.Timestamp(times[k],tz='UTC').isoformat() if k is not None else None,
               'exit_fill':price,'reason':reason,'closed':k is not None,'r':pnl/risk if pnl is not None else None,
               'pnl_per_oz':pnl,'swap_estimate':swap,'fee_round_trip':fee,'ambiguous_m1':ambiguous}
        trades.append(trade)
        busy=int(times[k]) if k is not None else int(times[-1])+MINUTE
    return trades,{'blocked_by_open_position':blocked,'invalid_fill':invalid}


def stats(trades):
    closed=[t for t in trades if t['closed']]
    values=np.array([t['r'] for t in closed],float)
    wins=int((values>0).sum());losses=int((values<0).sum());flat=int((values==0).sum())
    eq=np.r_[0.,values.cumsum()]
    n=len(closed)
    # Wilson interval describes sample uncertainty; correlated signals weaken inference further.
    ci=None
    if n:
        p=wins/n;z=1.95996398454;den=1+z*z/n
        middle=(p+z*z/(2*n))/den
        half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
        ci=[(middle-half)*100,(middle+half)*100]
    return {'entered':len(trades),'closed':n,'open':len(trades)-n,'wins':wins,'losses':losses,'flat':flat,
            'win_pct':wins/n*100 if n else None,'win_ci95_wilson_pct':ci,'net_r':float(values.sum()),
            'mean_r':float(values.mean()) if n else None,
            'profit_factor_r':float(values[values>0].sum()/-values[values<0].sum()) if losses else None,
            'max_closed_drawdown_r':float((np.maximum.accumulate(eq)-eq).max())}


def merge(signals):
    groups={};priority={'M30':0,'M15':1,'M5':2}
    for signal in signals:
        groups.setdefault((signal['at'],signal['side']),[]).append(signal)
    result=[]
    for _,group in sorted(groups.items()):
        chosen=min(group,key=lambda s:priority[s['tf']])
        result.append({**chosen,'contributing_frames':','.join(sorted({s['tf'] for s in group},key=lambda tf:priority[tf]))})
    return result


def load_spreads(g,index):
    source=Path(os.path.expandvars(g['d1_goc'])).with_name('XAUUSDp_M1.csv')
    raw=pd.read_csv(source,sep='\t',usecols=[0,1,8],names=['d','t','spread'],header=0,dtype={'d':str,'t':str})
    time=pd.DatetimeIndex(pd.to_datetime(raw['d']+' '+raw['t'],format='%Y.%m.%d %H:%M:%S',utc=True))
    s=pd.Series(raw['spread'].to_numpy(float)*.01,index=sua_gio.gio_that(time))
    s=s[~s.index.duplicated(keep='last')].reindex(index)
    mask=(index>=START)&(index<STOP)
    coverage={'m1_in_test':int(mask.sum()),'historical_spread_m1':int(s.iloc[np.flatnonzero(mask)].notna().sum()),
              'fallback_m1':int(s.iloc[np.flatnonzero(mask)].isna().sum()),'fallback_price':float(g.get('spread',.17)),
              'spread_archive_last':str(time.max())}
    return s.fillna(float(g.get('spread',.17))).to_numpy(float),coverage


def run():
    load_runtime()
    OUT.mkdir(parents=True,exist_ok=True)
    cfg=json.loads((ROOT/'cau-hinh.json').read_text(encoding='utf-8'));g=cfg['gia']
    print('Loading frozen-release data for 23–27 Nov, UTC+7...',flush=True)
    m1=hoc._m1_dai(g,2024).iloc[:-1]
    assert m1.index.is_monotonic_increasing and not m1.index.has_duplicates
    assert np.isfinite(m1.to_numpy(float)).all() and (m1.to_numpy(float)>0).all()
    fr=hoc._khung(m1,g)
    fr={tf:pd.concat([bars[bars.index<WARM].tail(300),bars[bars.index>=WARM]])
        for tf,bars in fr.items() if isinstance(bars,pd.DataFrame)}
    spread,coverage=load_spreads(g,m1.index)
    recent_mask=m1.index>=WARM
    m1.loc[recent_mask].to_pickle(OUT/'input_m1.pkl')
    pd.to_pickle(fr,OUT/'input_frames.pkl')
    np.save(OUT/'input_spread.npy',spread[recent_mask])
    spec=importlib.util.spec_from_file_location('five_day_costs',ROOT/'cong-cu/diem_vao.py')
    costs=importlib.util.module_from_spec(spec);spec.loader.exec_module(costs)
    news,news_until=gia.tin_usd(g) if g.get('lich_tin') else ([],None)
    news_ns=np.array(sorted(pd.Timestamp(t).value for t in news),dtype=np.int64)
    def near_news(at):
        i=int(news_ns.searchsorted(at-15*MINUTE))
        return bool(i<len(news_ns) and news_ns[i]<=at+15*MINUTE)
    conf=dict(ai_store.DEFAULT)
    with sqlite3.connect((ROOT/'du-lieu/ai-platform.sqlite3').as_uri()+'?mode=ro',uri=True) as con:
        stored=con.execute('SELECT body FROM settings WHERE id=1').fetchone()
        if stored:
            conf['min_rr']=json.loads(stored[0]).get('min_rr',conf['min_rr'])
    mt=m1.index.as_unit('ns').asi8;bids=m1['open'].to_numpy(float)
    cache={}
    def flat(tf,at):
        key=(tf,int(fr[tf].index.searchsorted(pd.Timestamp(at,tz='UTC')-pd.Timedelta(minutes=gia.KHUNG[tf]),side='right')))
        if key not in cache:
            cache[key]=ai_chart._indicators(fr[tf].iloc[max(0,key[1]-240):key[1]]) if key[1] else {}
        return cache[key]
    signals={tf:[] for tf in ai_timeframes.ENTRY_FRAMES};free_counts={date:{tf:0 for tf in signals} for date in DAYS}
    exclusions={tf:{'news':0,'context':0,'quotes_or_cost':0} for tf in signals}
    audit=[]
    for tf in signals:
        d=scanner.dieu_kien(fr[tf],fr['H1'],tf)
        for opened,row in d.iterrows():
            at=int(opened.value+gia.KHUNG[tf]*MINUTE)
            if at<WARM.value or at>=STOP.value:
                continue
            j=int(mt.searchsorted(at))
            if j>=len(mt) or mt[j]-at>120*10**9:
                continue
            frames={higher:flat(higher,at) for higher in ai_timeframes.required(tf)}
            snapshot={'symbol':'XAUUSDp','timeframe':tf,'source':'historical M1','captured_at':at/10**9,'quote_at':int(mt[j])/10**9,
                      'bid':float(bids[j]),'ask':float(bids[j]+spread[j]),'spread':float(spread[j]),
                      'digits':2,'point':.01,'tick_size':.01,'stops_level_points':0,'frames':frames}
            ctx=ai_timeframes.assess(snapshot)
            local_date=day(pd.Timestamp(at,tz='UTC'))
            if at>=START.value and ctx['aligned']:
                end=int(fr[tf].index.searchsorted(opened,side='right'))
                bars=fr[tf].iloc[max(0,end-80):end]
                snapshot['candles']=[[int(t.timestamp()),*map(float,r)] for t,r in zip(bars.index,bars[['open','high','low','close']].to_numpy())]
                request={'ma':'XAUUSDp','tf':tf,'lang':'en','mode':'entry'}
                result=ai_local.read_snapshot(snapshot,conf,request,clock=lambda:at/10**9)
                free_counts[local_date][tf]+=int(bool(result['analysis']['scenarios']))
            if not row.phia:
                continue
            record={'tf':tf,'signal':pd.Timestamp(at,tz='UTC').isoformat(),'date':local_date,
                    'side':'MUA' if row.phia>0 else 'BAN','kind':str(row.loai),'context':ctx['status'],'status':'eligible'}
            if at>=START.value:
                audit.append(record)
            if not ctx['aligned'] or ctx['bias']!=row.phia:
                record['status']='context'
                if at>=START.value:
                    exclusions[tf]['context']+=1
                continue
            if near_news(at):
                record['status']='news'
                if at>=START.value:
                    exclusions[tf]['news']+=1
                continue
            status,levels=scanner.muc_gia(row,float(bids[j]),float(bids[j]+spread[j]),.01,2)
            if status!='dat':
                record['status']=status
                if at>=START.value:
                    exclusions[tf]['quotes_or_cost']+=1
                continue
            signals[tf].append({'at':at,'tf':tf,'side':'MUA' if row.phia>0 else 'BAN','kind':str(row.loai),
                                'entry':levels['vao'],'sl':levels['sl'],'tp':levels['tp'],'atr':float(row.atr)})
        print(json.dumps({'tf':tf,'five_day_signals':sum(s['at']>=START.value for s in signals[tf]),'exclusions':exclusions[tf]}),flush=True)
    combined=merge([s for values in signals.values() for s in values])
    report={'release':SELECTED,'period_days':DAYS,'timezone':TZ,'data_to_utc':m1.index[-1].isoformat(),
            'data_to_local':m1.index[-1].tz_convert(TZ).isoformat(),'coverage':coverage,
            'calendar_enabled':bool(g.get('lich_tin')),'calendar_covered_until':str(news_until),
            'calendar_events_in_period':int(((news_ns>=START.value)&(news_ns<STOP.value)).sum()),
            'free_reference_snapshots':free_counts,'native_exclusions':exclusions,'frames':{},'combined':{}}
    local_dates=np.array([d.isoformat() for d in m1.index.tz_convert(TZ).date])
    report['daily_input_bars']={date:int((local_dates==date).sum()) for date in DAYS}
    daily=[]
    all_sets={**signals,'combined':combined}
    for name,plans in all_sets.items():
        test_signals=[s for s in plans if START.value<=s['at']<STOP.value]
        result={}
        for scenario,stress in (('base',False),('stress',True)):
            trades,counts=simulate(m1,spread,plans,stress=stress,swap_fn=costs.so_dem)
            trades=[t for t in trades if START.value<=t['at']<STOP.value]
            result[scenario]={'summary':stats(trades),'execution_counts_including_warmup':counts}
            rows=[]
            for date in DAYS:
                summary=stats([t for t in trades if t['day_local']==date])
                row={'date':date,'scope':name,'scenario':scenario,
                     'new_signals':sum(day(pd.Timestamp(s['at'],tz='UTC'))==date for s in test_signals),**summary}
                rows.append(row);daily.append(row)
            result[scenario]['daily']=rows
            pd.DataFrame(trades).to_csv(OUT/(name+'__'+scenario+'__trades.csv'),index=False)
        result['new_signals']=len(test_signals)
        (report['combined'] if name=='combined' else report['frames']).update(result if name=='combined' else {name:result})
    pd.DataFrame(daily).to_csv(OUT/'daily.csv',index=False)
    pd.DataFrame(audit).to_csv(OUT/'signal_audit.csv',index=False)
    report['evidence_sources']={str(path.relative_to(PROGRAM)):hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in (PROGRAM/'so_cong_khai').glob('ai*.py')}
    report['evidence_sources']['tin_hieu_ngan.py']=hashlib.sha256((PROGRAM/'so_cong_khai/tin_hieu_ngan.py').read_bytes()).hexdigest()
    report['saved_input_sha256']={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest()
                                for name in ('input_m1.pkl','input_frames.pkl','input_spread.npy','PLAN.json')}
    report['claims']={'more_than_20_new_calls_every_day':all(row['new_signals']>20 for row in report['combined']['base']['daily']),
                      'more_than_20_entered_every_day':all(row['entered']>20 for row in report['combined']['base']['daily']),
                      'over_70pct_closed_sample':bool(report['combined']['base']['summary']['closed'] and report['combined']['base']['summary']['win_pct']>70),
                      'long_run_70pct_proven':False,'actual_messages_or_broker_trades_verified':False,'claude_api_backtested':False}
    write('results.json',report)
    print(json.dumps({'combined':report['combined'],'coverage':coverage,'claims':report['claims']},ensure_ascii=False),flush=True)


if __name__=='__main__':
    run()
