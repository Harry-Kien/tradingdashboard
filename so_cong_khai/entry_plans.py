"""Immutable plan ledger shared by chart and alerts; prospective paper results only."""
from contextlib import closing
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3

VERSION='shared-entry-plan-v1'
DB='entry-plans.sqlite3'
SCHEMA='''
CREATE TABLE IF NOT EXISTS plans(
 id TEXT PRIMARY KEY, scope TEXT NOT NULL, server TEXT NOT NULL, symbol TEXT NOT NULL,
 strategy TEXT NOT NULL, tf TEXT NOT NULL, candle_ms INTEGER NOT NULL, captured_ms INTEGER NOT NULL,
 channel TEXT NOT NULL, body TEXT NOT NULL,
 UNIQUE(scope,symbol,strategy,tf,candle_ms));
CREATE TABLE IF NOT EXISTS tracking(
 plan_id TEXT PRIMARY KEY REFERENCES plans(id), state TEXT NOT NULL, last_ms INTEGER NOT NULL,
 fill REAL NOT NULL, risk REAL NOT NULL, exit_ms INTEGER, exit REAL, gross_r REAL, model_net_r REAL,
 verified_net_r REAL, cost_body TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS open_tracking ON tracking(state,last_ms);
'''


def out_dir(cfg):
    from . import duong
    p=Path(cfg.get('thu_muc_ra','out'))
    return p if p.is_absolute() else duong.goc_du_lieu()/p


def connect(out):
    p=Path(out)/DB;p.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(p,timeout=10)
    db.row_factory=sqlite3.Row
    db.executescript(SCHEMA)
    return db


def register(out,data,row,*,strategy,channel='observation',costs=None,hold_minutes=None,now=None):
    """First fresh snapshot wins; a later quote can never rewrite its levels."""
    now=now or datetime.now(timezone.utc);ms=int(now.timestamp()*1000)
    try:
        closed=int(datetime.fromisoformat(row['dong']).timestamp()*1000)
        expiry=int(datetime.fromisoformat(row['het']).timestamp()*1000)
        captured=int(datetime.fromisoformat(data['luc']).timestamp()*1000)
        tick=int(data['tick_ms']);entry,sl,tp=(float(row[k]) for k in ('vao','sl','tp'))
        bid,ask=float(data['bid']),float(data['ask']);atr=float(row['atr'])
        side=1 if row['huong']=='MUA' else -1 if row['huong'] in ('BAN','BÁN') else 0
        scope=data.get('account_scope')
        if (data.get('nguon')!='mt5' or row.get('trang_thai')!='dat' or not scope or not side
            or not closed<=captured<=ms<=min(expiry,closed+120_000) or not closed<=tick<=ms+5_000
            or ms-tick>30_000 or ms-captured>30_000 or row.get('tf') not in ('M5','M15','M30')
            or not all(math.isfinite(v) and v>0 for v in (entry,sl,tp,bid,ask,atr))
            or ask<bid or (entry-sl)*side<=0 or (tp-entry)*side<=0):
            return None
    except (KeyError,ValueError,TypeError,OverflowError):
        return None
    if channel not in ('observation','research'):
        raise ValueError('Unknown plan channel')
    key=[scope,data['ma'],strategy,row['tf'],closed]
    ident='EP-'+hashlib.sha256(json.dumps(key,separators=(',',':')).encode()).hexdigest()[:24]
    costs=costs or {'commission_price':.18,'commission_source':'assumed','slippage_price':.05,'slippage_source':'assumed','fully_verified':False}
    body={'id':ident,'version':VERSION,'strategy':strategy,'symbol':data['ma'],'tf':row['tf'],
          'candle_ms':closed,'captured_ms':captured,'tick_ms':tick,'expires_ms':min(expiry,closed+120_000),
          'side':'MUA' if side>0 else 'BAN','entry':entry,'sl':sl,'tp':tp,'atr':float(row['atr']),
          'kind':row['loai'],'bid':bid,'ask':ask,'spread':ask-bid,'channel':channel,'profitability_proven':False,
          'hold_minutes':hold_minutes or 12*{'M5':5,'M15':15,'M30':30}[row['tf']], 'costs':costs}
    body['content_sha256']=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    with closing(connect(out)) as db,db:
        db.execute('BEGIN IMMEDIATE')
        inserted=db.execute('INSERT OR IGNORE INTO plans VALUES(?,?,?,?,?,?,?,?,?,?)',
                           (ident,scope,data.get('may_chu',''),data['ma'],strategy,row['tf'],closed,captured,channel,json.dumps(body,ensure_ascii=False))).rowcount
        saved=json.loads(db.execute('SELECT body FROM plans WHERE id=?',(ident,)).fetchone()[0])
        if saved['side']!=body['side']:
            raise ValueError('Closed-candle direction changed within a locked plan')
        if inserted:
            busy=db.execute('''SELECT 1 FROM tracking t JOIN plans p ON p.id=t.plan_id
                WHERE t.state='open' AND p.scope=? AND p.symbol=? AND p.strategy=? AND p.tf=?''',
                            (scope,data['ma'],strategy,row['tf'])).fetchone()
            slip=float(costs['slippage_price']);fill=(ask if side>0 else bid)+side*slip;risk=(fill-sl)*side
            state='blocked' if busy else 'open'
            if risk<=0 or (tp-fill)*side<=0:
                state='invalid_fill'
            db.execute('INSERT INTO tracking(plan_id,state,last_ms,fill,risk,cost_body) VALUES(?,?,?,?,?,?)',
                       (ident,state,tick,fill,max(risk,1e-12),json.dumps(costs)))
        return saved


def apply(out,data,*,costs=None,now=None):
    """Only observation plans enter the normal ds consumed by chart/alerts."""
    for row in data.get('ds',[]):
        if row.get('trang_thai')!='dat':
            continue
        from . import entry_feed
        plan=register(out,data,row,strategy=data['phien_ban']+'-'+entry_feed.research_version().rsplit('-',1)[-1],costs=costs,now=now)
        if plan is None:
            row['trang_thai']='ke_hoach_loi'
            for k in ('vao','sl','tp','rr'):
                row.pop(k,None)
            continue
        sign=1 if plan['side']=='MUA' else -1
        risk=(plan['entry']-plan['sl'])*sign
        row.update(vao=plan['entry'],sl=plan['sl'],tp=plan['tp'],rr=round((plan['tp']-plan['entry'])*sign/risk,2),
                   plan_id=plan['id'],plan_hash=plan['content_sha256'],plan_locked=True)
        quote=data['ask'] if sign>0 else data['bid'];exit_quote=data['bid'] if sign>0 else data['ask']
        minimum=max(0.,float(data.get('minimum_stop',0)))
        if (abs(quote-plan['entry'])>.25*min(plan['atr'],risk) or data['ask']-data['bid']>.15*min(plan['atr'],risk) or (exit_quote-plan['sl'])*sign<=0
            or (plan['tp']-exit_quote)*sign<=0 or (exit_quote-plan['sl'])*sign<minimum or (plan['tp']-exit_quote)*sign<minimum):
            row['trang_thai']='gia_di_xa'
            for k in ('vao','sl','tp','rr'):
                row.pop(k,None)
    return data


def score(plan,track,ticks,until_ms):
    """Real Bid/Ask observations; modeled execution costs are explicitly estimated."""
    last=track['last_ms'];sign=1 if plan['side']=='MUA' else -1
    deadline=plan['captured_ms']+plan['hold_minutes']*60_000
    costs=json.loads(track['cost_body']);slip=float(costs['slippage_price']);fee=float(costs['commission_price'])
    for ms,bid,ask in ticks:
        if ms<=last or ms>until_ms or not all(math.isfinite(x) for x in (bid,ask)) or not 0<bid<=ask:
            continue
        if ms-last>120_000:
            return {'state':'unknown_gap','last_ms':last}
        last=ms;quote=bid if sign>0 else ask
        state='time' if ms>=deadline else 'sl' if (quote-plan['sl'])*sign<=0 else 'tp' if (quote-plan['tp'])*sign>=0 else None
        if not state:
            continue
        price=plan['tp'] if state=='tp' else quote-sign*slip
        gross=(price-track['fill'])*sign
        # No historical swap schedule: overnight results cannot be net-verified.
        start=datetime.fromtimestamp(plan['captured_ms']/1000,timezone.utc)
        end=datetime.fromtimestamp(ms/1000,timezone.utc)
        # Conservative day boundary: exact broker rollover not supplied here.
        from zoneinfo import ZoneInfo
        broker_zone=ZoneInfo('Europe/Athens')
        overnight=start.date()!=end.date() or start.astimezone(broker_zone).date()!=end.astimezone(broker_zone).date()
        net=None if overnight else (gross-fee)/track['risk']
        return {'state':state,'last_ms':last,'exit_ms':ms,'exit':price,'gross_r':gross/track['risk'],
                'model_net_r':net,'verified_net_r':None,'overnight_cost_unknown':overnight}
    return {'state':'unknown_gap' if until_ms-last>120_000 else 'open','last_ms':last}


def advance(out,mt5,account,now=None):
    from . import entry_costs,song
    if not (Path(out)/DB).is_file() or not account:
        return 0
    now=now or datetime.now(timezone.utc);end=int(now.timestamp()*1000)-2_000
    scope=entry_costs.account_scope(account);count=0
    with closing(connect(out)) as db:
        rows=db.execute('''SELECT t.*,p.body,p.server,p.symbol FROM tracking t JOIN plans p ON p.id=t.plan_id
            WHERE t.state='open' AND p.scope=? ORDER BY last_ms LIMIT 64''',(scope,)).fetchall()
        for row in rows:
            until=min(end,row['last_ms']+180_000)
            if until<=row['last_ms']:
                continue
            with song._khoa:
                current=mt5.account_info() if mt5 and hasattr(mt5,'account_info') else None
                if entry_costs.account_scope(current)!=scope:
                    return count
                if mt5 is not song._tt.get('mt5'):
                    continue
                raw=mt5.copy_ticks_range(row['symbol'],datetime.fromtimestamp(row['last_ms']//1000,timezone.utc),
                                        datetime.fromtimestamp(until//1000+1,timezone.utc),mt5.COPY_TICKS_INFO)
                ticks=None if raw is None else sorted([(int(t['time_msc']),float(t['bid']),float(t['ask'])) for t in raw],key=lambda t:t[0])
            if ticks is None:
                continue
            result=score(json.loads(row['body']),row,ticks,until)
            with db:
                count+=db.execute('''UPDATE tracking SET state=?,last_ms=?,exit_ms=?,exit=?,gross_r=?,model_net_r=?,verified_net_r=?
                    WHERE plan_id=? AND state='open' AND last_ms=?''',
                    (result['state'],result['last_ms'],result.get('exit_ms'),result.get('exit'),result.get('gross_r'),
                     result.get('model_net_r'),None,row['plan_id'],row['last_ms'])).rowcount
    return count


def summary(out,scope,symbol):
    result={'version':VERSION,'promotion_allowed':False,'profitability_proven':False,'rows':[],
            'note':'Spread quan sát từ tick; phí đối chiếu lịch sử nếu đủ mẫu. Trượt giá là giả định; chưa phải lợi nhuận khớp lệnh thật.'}
    if not scope or not (Path(out)/DB).is_file():
        return result
    with closing(connect(out)) as db:
        result['rows']=[dict(r) for r in db.execute('''SELECT p.channel,p.strategy,p.tf,COUNT(*) plans,
            SUM(t.state='open') open,SUM(t.state='blocked') blocked,SUM(t.state='unknown_gap') unknown_gap,
            SUM(t.state IN ('tp','sl','time')) closed,COUNT(t.model_net_r) modeled_net_count,
            AVG(t.model_net_r) modeled_mean_r,COUNT(t.verified_net_r) verified_net_count,
            MIN(p.captured_ms) first_observed_ms,MAX(p.captured_ms) last_observed_ms
            FROM plans p JOIN tracking t ON p.id=t.plan_id WHERE p.scope=? AND p.symbol=?
            GROUP BY p.channel,p.strategy,p.tf''',(scope,symbol))]
    return result
