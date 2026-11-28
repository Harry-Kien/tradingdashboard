"""One observation plan feed for chart and alerts; M30 research is never broadcast."""
from datetime import datetime,timezone
from functools import lru_cache
import hashlib
from pathlib import Path
import sqlite3

from . import entry_costs,entry_execution,entry_plans,tin_hieu_ngan as T

M30_CANDIDATE='ket_hop/market/swing5/rr1/36'


@lru_cache(maxsize=1)
def research_version():
    from . import ai_timeframes
    digest=hashlib.sha256()
    for module in (T,entry_execution,ai_timeframes):
        digest.update(Path(module.__file__).read_bytes())
    return 'm30-forward-v1-'+digest.hexdigest()[:16]


def prepare_m30(fr,data,now,minimum_stop=0.):
    """Frozen selected candidate, purely prospective; only for the tested gold symbol."""
    import pandas as pd
    from . import ai_timeframes
    b=fr.get('M30');h=fr.get('H1')
    if b is None or h is None:
        return []
    b=b[b.index+pd.Timedelta(minutes=30)<=now].tail(T.MAU)
    h=h[h.index+pd.Timedelta(hours=1)<=now].tail(T.MAU)
    if len(b)<200 or len(h)<200:
        return []
    closed=b.index[-1]+pd.Timedelta(minutes=30)
    if not 0<=(now-closed).total_seconds()<=T.HAN_GIAY or data['tick_ms']/1000<closed.timestamp() or not -5<=now.timestamp()-data['tick_ms']/1000<=30:
        return []
    d=T.dieu_kien(b,h,'M30');r=d.iloc[-1]
    sign=int(r.phia or r.hoi_sau or r.quet_nguoc)
    ctx=ai_timeframes.from_frames(fr,'M30',now.timestamp())
    if not sign or not ctx['aligned'] or ctx['bias']!=sign:
        return []
    row={k:float(r[k]) for k in ('atr','close','day','dinh')}
    row.update(phia=sign,high=float(b.high.iloc[-1]),low=float(b.low.iloc[-1]),low5=float(b.low.tail(5).min()),high5=float(b.high.tail(5).max()))
    p=entry_execution.plan(row,M30_CANDIDATE,data['bid'],data['ask'],30,step=data['buoc_gia'],digits=data['so_le'])
    quote=data['bid'] if sign>0 else data['ask']
    if not p or (quote-p['sl'])*sign<minimum_stop or (p['tp']-quote)*sign<minimum_stop:
        return []
    return [{'tf':'M30','trang_thai':'dat','loai':'m30_research','huong':'MUA' if sign>0 else 'BÁN',
             'vao':p['entry'],'sl':p['sl'],'tp':p['tp'],'atr':row['atr'],'dong':closed.isoformat(),
             'het':(closed+pd.Timedelta(seconds=120)).isoformat()}]


def doc(cfg,ma,now=None,*,khung=None,research=False,out=None):
    params={'topdown':True}
    if khung is not None:
        params['khung']=khung
    if research:
        params['research_m30']=True
    data=T.doc(cfg,ma,now,**params) if now is not None else T.doc(cfg,ma,**params)
    out=out if out is not None else entry_plans.out_dir(cfg)
    clock=now or datetime.now(timezone.utc)
    ready=any(row.get('trang_thai')=='dat' for row in data.get('ds',[])) or bool(data.get('m30_research'))
    if ready:
        costs=entry_costs.estimate(cfg,data,clock)
        try:
            entry_plans.apply(out,data,costs=costs,now=clock)
            for row in data.pop('m30_research',[]):
                entry_plans.register(out,data,row,strategy=research_version(),channel='research',costs=costs,
                                     hold_minutes=1080,now=clock)
        except (sqlite3.Error,OSError,ValueError) as error:
            data['plan_error']=type(error).__name__
            for row in data.get('ds',[]):
                row['trang_thai']='ke_hoach_loi'
                for key in ('vao','sl','tp','rr'):
                    row.pop(key,None)
    data.pop('m30_research',None)
    data['shared_plan_version']=entry_plans.VERSION
    return data


def update(cfg,out,now=None):
    from . import song
    with song._khoa:
        mt=song._tt.get('mt5')
        account=mt.account_info() if mt and hasattr(mt,'account_info') else None
    return entry_plans.advance(out,mt,account,now)
