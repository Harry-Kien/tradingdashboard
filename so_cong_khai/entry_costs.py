"""Read-only fee calibration; observed costs stay distinct from assumptions."""
from datetime import timedelta
import math
import time

_cache={}


def account_scope(account):
    import hashlib
    text=f'{getattr(account,"server","")}|{getattr(account,"login","")}'
    return hashlib.sha256(text.encode()).hexdigest() if account else ''


def estimate(cfg,data,now):
    """Never treats absent commission history as evidence of zero commission."""
    from . import da_ma,song
    scope=data.get('account_scope','');symbol=data['ma'];key=(scope,symbol)
    fallback={'commission_price':.18,'commission_source':'assumed_0.18_per_price_unit',
              'commission_positions':0,'slippage_price':.05,'slippage_source':'assumed',
              'spread_source':'observed_bid_ask','fully_verified':False}
    if not scope:
        return fallback
    cached=_cache.get(key)
    if cached and time.monotonic()-cached[0]<3600:
        return cached[1].copy()
    result=fallback.copy()
    try:
        mt=da_ma._mt5(cfg.get('gia') or {})
        with song._khoa:
            account=mt.account_info() if mt and hasattr(mt,'account_info') else None
            if account_scope(account)!=scope or getattr(account,'currency','')!='USD':
                return fallback
            info=mt.symbol_info(symbol)
            tick_value=float(getattr(info,'trade_tick_value_loss',0) or 0)
            step=float(getattr(info,'trade_tick_size',0) or 0)
            deals=mt.history_deals_get(now-timedelta(days=90),now) if hasattr(mt,'history_deals_get') else None
        groups={}
        for deal in deals or []:
            if getattr(deal,'symbol','')!=symbol or getattr(deal,'type',-1) not in (0,1):
                continue
            groups.setdefault(getattr(deal,'position_id',0),[]).append(deal)
        costs=[]
        for ident,rows in groups.items():
            if not ident or any(getattr(d,'entry',-1) not in (0,1) for d in rows):
                continue
            incoming=sum(float(d.volume) for d in rows if d.entry==0)
            outgoing=sum(float(d.volume) for d in rows if d.entry==1)
            charges=[float(getattr(d,'commission',float('nan')))+float(getattr(d,'fee',0)) for d in rows]
            if incoming>0 and abs(incoming-outgoing)<1e-7 and all(math.isfinite(c) for c in charges):
                costs.append(max(0.,-sum(charges))/incoming)
        if len(costs)>=10 and tick_value>0 and step>0:
            # Volume-weighted fees would hide the variability: retain observed range.
            costs.sort();median=costs[len(costs)//2]
            result.update(commission_price=median*step/tick_value,commission_source='observed_closed_positions_90d',
                          commission_positions=len(costs),commission_per_lot_range=[costs[0],costs[-1]])
    except (AttributeError,TypeError,ValueError,RuntimeError,OverflowError):
        pass
    _cache[key]=(time.monotonic(),result.copy())
    return result
