"""Conservative M1 Bid/Ask replay for fixed experimental plans. No API calls."""
import numpy as np
import pandas as pd

MINUTE=60_000_000_000


def simulate(m1,spreads,plans,*,stress=False,swap_fn=None,news=None):
    t=m1.index.as_unit('ns').asi8
    o,h,l=(m1[k].to_numpy(float) for k in ('open','high','low'))
    sp=np.asarray(spreads)*(2 if stress else 1)
    slip=.05*(2 if stress else 1);fee=.18*(2 if stress else 1)
    penetration=.01*(2 if stress else 1)
    news=np.asarray(news if news is not None else [],dtype=np.int64)
    busy=-1;trades=[]
    counts={'blocked':0,'expired':0,'pending_unresolved':0,'cancelled_context':0,'cancelled_news':0,'invalid_start':0,'ambiguous_entry_minute':0}
    for p in sorted(plans,key=lambda x:(x['at'],{'M30':0,'M15':1,'M5':2}[x['tf']])):
        at=p['at'];j=int(t.searchsorted(at));sign=1 if p['side']=='MUA' else -1
        if at<=busy:
            counts['blocked']+=1;continue
        if j>=len(t) or t[j]-at>120*10**9:
            counts['invalid_start']+=1;continue
        entry_type=p['entry_type'];order=float(p['entry']);sl=float(p['sl']);tp=float(p['tp'])
        pending_end=at+p['wait_minutes']*MINUTE
        filled=None;fill=None;entry_at_open=False;cancel_at=None
        for i in range(j,min(int(t.searchsorted(pending_end)),len(t)) if entry_type!='market' else j+1):
            if entry_type!='market':
                if t[i]>=p.get('context_until',np.iinfo(np.int64).max):
                    counts['cancelled_context']+=1;cancel_at=int(t[i]);break
                n=int(news.searchsorted(int(t[i])-15*MINUTE))
                if n<len(news) and news[n]<=int(t[i])+15*MINUTE:
                    counts['cancelled_news']+=1;cancel_at=int(t[i]);break
            quote=o[i]+(sp[i] if sign>0 else 0)
            high=h[i]+(sp[i] if sign>0 else 0)
            low=l[i]+(sp[i] if sign>0 else 0)
            if entry_type=='market':
                fill=quote+sign*slip;entry_at_open=True
            elif entry_type=='stop':
                if (high>=order if sign>0 else low<=order):
                    fill=(max(quote,order) if sign>0 else min(quote,order))+sign*slip
                    entry_at_open=(quote-order)*sign>=0
            elif (low<=order-penetration if sign>0 else high>=order+penetration):
                # Require penetration; no favorable gap improvement or fill beyond a limit.
                fill=order;entry_at_open=(quote-order)*sign<=-penetration
            if fill is not None:
                filled=i;break
        if filled is None:
            if cancel_at is None:
                counts['pending_unresolved' if pending_end>int(t[-1])+MINUTE else 'expired']+=1
            # One pending order per symbol; cancellation frees the slot at that minute.
            busy=(cancel_at if cancel_at is not None else pending_end)-1
            continue
        i=filled;risk=(fill-sl)*sign
        # A gap through a fixed TP cannot be silently dropped as an invalid fill.
        deadline=int(t[i])+p['hold_minutes']*MINUTE
        scheduled=int(t.searchsorted(deadline));limit=min(scheduled,len(t))
        hi=h[i:limit]+(sp[i:limit] if sign<0 else 0)
        lo=l[i:limit]+(sp[i:limit] if sign<0 else 0)
        opens=o[i:limit]+(sp[i:limit] if sign<0 else 0)
        legs=[];exit_index=None;reason='OPEN';ambiguous=False;partial=False
        initial_risk=abs(order-sl)
        if risk<=0 or (tp-fill)*sign<=0:
            legs=[(i,1.,float(opens[0]-sign*slip))];exit_index=i;reason='GAP_LEVEL_INVALID'
            risk=initial_risk
        else:
            stops=lo<=sl if sign>0 else hi>=sl
            profits=hi>=tp if sign>0 else lo<=tp
            if not entry_at_open and len(profits):
                # Intrabar high/low may have occurred before the pending entry.
                profits[0]=False
                if (h[i]>=tp if sign>0 else l[i]+sp[i]<=tp):
                    counts['ambiguous_entry_minute']+=1
            split=p['exit_type']=='split_be'
            first_target=float(p['tp1']) if split else tp
            firsts=(hi>=first_target if sign>0 else lo<=first_target)
            if not entry_at_open and len(firsts):
                firsts[0]=False
            hits=stops|firsts
            if hits.any():
                k=int(hits.argmax());exit_index=i+k
                if stops[k]:
                    # An opening gap BEFORE an intrabar pending fill is not a
                    # possible exit after that fill. Assume SL next, at SL.
                    opened=sl if k==0 and not entry_at_open else opens[k]
                    price=(min(opened,sl) if sign>0 else max(opened,sl))-sign*slip
                    legs=[(exit_index,1.,float(price))];reason='SL';ambiguous=bool(firsts[k])
                elif not split:
                    legs=[(exit_index,1.,tp)];reason='TP'
                elif profits[k]:
                    legs=[(exit_index,.5,first_target),(exit_index,.5,tp)];reason='TP_SPLIT'
                else:
                    partial=True;legs=[(exit_index,.5,first_target)]
                    # Move the remaining stop to fill only from the NEXT minute.
                    start=k+1
                    be=(lo[start:]<=fill if sign>0 else hi[start:]>=fill)
                    final=profits[start:];second=be|final
                    if second.any():
                        off=start+int(second.argmax());exit_index=i+off
                        if be[off-start]:
                            price=(min(opens[off],fill) if sign>0 else max(opens[off],fill))-sign*slip
                            legs.append((exit_index,.5,float(price)));reason='SPLIT_BE'
                            ambiguous=bool(final[off-start])
                        else:
                            legs.append((exit_index,.5,tp));reason='TP_SPLIT'
                    else:
                        exit_index=None
            if exit_index is None and scheduled<len(t):
                price=o[scheduled]+(sp[scheduled] if sign<0 else 0)-sign*slip
                legs.append((scheduled,.5 if partial else 1.,float(price)))
                exit_index=scheduled;reason='TIME_SPLIT' if partial else 'TIME'
        closed=exit_index is not None
        pnl=sum(weight*(price-fill)*sign for _,weight,price in legs)-fee
        swap=0.
        if swap_fn:
            swap=sum(weight*fill*(-.000181 if sign>0 else .000066)*swap_fn(int(t[i]),int(t[k])) for k,weight,_ in legs)
        pnl+=swap
        stamp=lambda k:pd.Timestamp(t[k],tz='UTC').isoformat()
        trade={**p,'signal':pd.Timestamp(at,tz='UTC').isoformat(),'filled_at':stamp(i),'entry_fill':float(fill),
               'risk_fill':float(risk),'sl_fixed':sl,'tp_fixed':tp,'closed':closed,'reason':reason,
               'exit_time':stamp(exit_index) if closed else None,'r':float(pnl/risk) if closed else None,
               'pnl_per_oz':float(pnl) if closed else None,'fee_round_trip':fee,'swap_estimate':float(swap),
               'partial':partial,'ambiguous_m1':ambiguous,'entry_at_open':entry_at_open,
               'legs':[{'at':stamp(k),'fraction':weight,'price':price} for k,weight,price in legs]}
        trades.append(trade)
        busy=int(t[exit_index]) if closed else int(t[-1])+MINUTE
    return trades,counts
