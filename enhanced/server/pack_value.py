"""Expected pack value and explicitly ordered cash discounts.

Player values use the same displayed EP valuation as player cards, not the old
unscaled shop anchor. Choice packs use the best selectable value; a package is
the sum of its contents. All issued odds stay in the original pack definitions.
"""
import functools, math
from decimal import Decimal, ROUND_CEILING

FACTORS={'ordinary':1.0,'chain':0.65,'once':0.45}

def triangular_ep_value(bounds):
    lo,hi=map(int,bounds)
    if lo<0 or hi<lo:raise ValueError('Invalid EP lottery bounds')
    if lo==hi:return float(lo)
    # Sum survival probabilities at rounding thresholds in constant time.
    den=(hi-lo)**2;first=lo//10000+1;last=(hi+5000)//10000
    if last<first:return float(lo)
    threshold=first*10000-5000
    survival=den if threshold<=lo else max(0,hi-threshold)**2
    total=lo*den+(first*10000-lo)*survival
    a,b=first+1,last
    if b>=a:
        n=b-a+1;sumk=(a+b)*n//2
        sumk2=b*(b+1)*(2*b+1)//6-(a-1)*a*(2*a-1)//6
        H=hi+5000
        total+=10000*(n*H*H-20000*H*sumk+100000000*sumk2)
    return total/den

class ValueModel:
    def __init__(self,h,points_per_ep):
        if not math.isfinite(points_per_ep) or points_per_ep<=0:raise ValueError('Invalid value conversion')
        self.h=h;self.points_per_ep=points_per_ep
    @functools.lru_cache(maxsize=None)
    def card(self,spid,grade):return self.h.player_value_price(spid,grade)
    @functools.lru_cache(maxsize=None)
    def value(self,itemid,trail=()):
        h=self.h
        if itemid in trail:raise ValueError('Cyclic package')
        trail=trail+(itemid,)
        if itemid in h.PACKS:
            pool=[(int(s),float(w)) for s,w in h.pack_pool(itemid) if w>0]
            grades=[(int(g),float(w)) for g,w in h.pack_grades(itemid) if w>0]
            if not pool or not grades:return 0.0
            gw=math.fsum(w for _,w in grades);pw=math.fsum(w for _,w in pool)
            values=[(math.fsum(self.card(s,g)*w for g,w in grades)/gw,weight) for s,weight in pool]
            data=getattr(h,'product_packs',{});definition={**data.get('risk_packs',{}),**data.get('strength_packs',{})}.get(str(itemid),{})
            catalogue=getattr(h,'pack_catalogue',{})
            if not definition:definition=catalogue.get('items',{}).get(str(itemid),{})
            if definition.get('mode')=='choice':return max(v for v,_ in values)
            return math.fsum(v*w for v,w in values)/pw
        if itemid in h.PACKAGES:
            return math.fsum(n*self.value(i,trail) for i,n in h.PACKAGES[itemid][2])
        if itemid in h.MONTHLY:
            _,_,days,now,daily,_=h.MONTHLY[itemid]
            return math.fsum(n*self.value(i,trail) for i,n in now)+days*math.fsum(n*self.value(i,trail) for i,n in daily)
        # Utility items have no player-card resale value. Keep their ordinary point
        # anchor explicit rather than inventing an EP resale price for experience.
        if itemid==h.EP_ITEM:return 1.0
        if itemid==h.ES_ITEM:return .02/self.points_per_ep
        if itemid in getattr(h,'ITEMS',{}):
            _,_,kind,effect,_=h.ITEMS[itemid]
            if kind=='EP_LOTTERY':return triangular_ep_value(effect['ep'])
            if kind=='ITEM_LOTTERY':
                prizes=effect.get('prizes') or []
                total=math.fsum(w for w,_ in prizes)
                if total<=0:return 0.0
                return math.fsum(w*(self.value(prize,trail) if isinstance(prize,int) else prize[1]) for w,prize in prizes)/total
        return h.cash_product_price(itemid)/self.points_per_ep
    def quote(self,itemid,kind='ordinary'):
        if kind not in FACTORS:raise ValueError('Unknown discount tier')
        value=self.value(itemid)
        if value<=0:return 0
        # Decimal prevents exact boundary quotes such as 123500 gaining a point
        # from a binary floating-point tail before ceiling.
        base=Decimal(str(value))*Decimal(str(self.points_per_ep))
        ceiling=lambda factor:int((base*Decimal(str(factor))).to_integral_value(rounding=ROUND_CEILING))
        standard=max(3,ceiling(1))
        chain=min(standard-1,max(2,ceiling(FACTORS['chain'])))
        once=min(chain-1,max(1,ceiling(FACTORS['once'])))
        return {'ordinary':standard,'chain':chain,'once':once}[kind]
    def describe(self,itemid):
        value=self.value(itemid)
        return dict(expected_ep=value,standard_points=value*self.points_per_ep,
                    quotes={kind:self.quote(itemid,kind) for kind in FACTORS})
