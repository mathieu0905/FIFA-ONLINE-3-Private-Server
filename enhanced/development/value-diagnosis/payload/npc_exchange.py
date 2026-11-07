"""Independent NPC inventory, reserved public offers, virtual income and actual peer settlement.
Runs only inside Market.tick's state transaction. No client requests drive simulation.
"""
import math
from pathlib import Path
from market_price_store import MarketPriceStore, MAX_PRICE
from ability_value import AbilityPriceBook

AGENTS=32
INITIAL_WALLET=10**15
MAX_VISIBLE_LISTINGS=192
INTERNAL_BURN_FRACTION=.0025
BUY_PER_TICK=3
TRADE_PER_TICK=6
HOLD_SECONDS=60
LIST_DELAY=30
FEE_RATE=.01

class NpcExchange:
    def __init__(self, market, model_path=None):
        self.market=market
        path=getattr(market.h,'MARKET_PRICE_DB_PATH',Path(market.h.HERE)/'gamedata/npc-market-prices.sqlite')
        self.price_store=MarketPriceStore(path)
        self._profiles={}
        self.ability_prices=AbilityPriceBook(market.h)

    def profile(self,spid):
        # Attributes are NPC preferences only; they never recalculate the price.
        if spid not in self._profiles:
            fields=('acceleration','sprintspeed','agility','ballcontrol','dribbling','shortpassing',
                    'strength','headingaccuracy','jumping','standingtackle','interceptions','stamina')
            with self.market.h.closing(self.market.h._db()) as db:
                row=db.execute('SELECT '+','.join(fields)+' FROM players WHERE spid=?',(spid,)).fetchone()
            if row is None:raise ValueError('NPC card missing from database')
            self._profiles[spid]=dict(zip(fields,row))
        return self._profiles[spid]

    def base_value(self,spid,st=None):
        initial=self.price_store.initial(spid)
        if initial<=0:return 0
        basis=self.price_store.basis(spid)
        if st is not None:
            basis=st.get('market_simulation',{}).get('quotes',{}).get(str(int(spid)),{}).get('basis_price',basis)
        return self.ability_prices.current(spid,basis,initial)

    def reference_value(self,spid,grade,st=None):
        base=self.base_value(spid,st)
        if base<=0:return 0
        return self.ability_prices.graded(base,grade)

    def world(self,st,stamp):
        m=st['market_simulation']
        if 'npc_exchange' not in m:
            m['npc_exchange']={'version':1,'created_at':stamp,'last_step':int(stamp//15)-1,
                'serial':0,'agents':[{'id':i,'wallet':INITIAL_WALLET,'style':i%4} for i in range(AGENTS)],
                'assets':{},'supplier_wallet':0,'fees':0,'source_buys':0,'peer_trades':0,
                'human_buys':0,'history':[]}
        w=m['npc_exchange']
        if w.get('version',1)<2:
            w['version']=2;w['historical_public_source_buys']=w.get('source_buys',0)
            w['internal_source_buys']=0;w['consumed_cards']=0;w['simulated_income']=0
            for asset in w['assets'].values():asset.setdefault('quantity',1)
        return w

    def listings(self,st,stamp,spid=None):
        w=st.get('market_simulation',{}).get('npc_exchange',{})
        return [a['listing'] for a in w.get('assets',{}).values()
            if 'listing' in a and a['listing']['count']>0 and self.market.npc_supply_allowed(a['spid'],a['grade'])
            and (spid is None or a['spid']==int(spid))]

    def _counts(self,w):
        counts={i:0 for i in range(AGENTS)}
        for a in w['assets'].values():counts[a['owner']]+=1
        return counts

    def _preference(self,agent,asset,stamp,seed):
        p=self.profile(asset['spid'])
        fields=(('acceleration','sprintspeed','agility'),('ballcontrol','dribbling','shortpassing'),
                ('strength','headingaccuracy','jumping'),('standingtackle','interceptions','stamina'))[agent['style']]
        quality=sum(p[f] for f in fields)/len(fields)
        utility=max(.82,min(1.22,1+(quality-75)/180))
        mood=.90+.24*self.market.unit(f'{seed}:interest:{int(stamp//180)}:{agent["id"]}:{asset["spid"]}')
        return utility*mood

    def _history(self,w,event):
        w['history'].append(event);w['history']=w['history'][-300:]

    @staticmethod
    def quantity(asset):return int(asset.get('quantity',1))

    def available(self,asset):
        return self.quantity(asset)-(1 if asset.get('listing') is not None else 0)

    def _put(self,w,spid,grade,owner,price,stamp):
        for key,asset in w['assets'].items():
            if (asset['spid'],asset['grade'],asset['owner'])==(spid,grade,owner):
                asset['quantity']=self.quantity(asset)+1
                return key
        w['serial']+=1;key=str(w['serial'])
        w['assets'][key]=dict(spid=spid,grade=grade,owner=owner,quantity=1,cost=price,
            acquired_at=stamp,created_at=stamp)
        return key

    def _take(self,w,key,public=False):
        asset=w['assets'][key]
        if public:
            if asset.get('listing') is None:raise ValueError('Missing reserved public unit')
            del asset['listing']
        elif self.available(asset)<=0:raise ValueError('Publicly reserved stock cannot be taken by NPCs')
        count=self.quantity(asset)-1
        if count:asset['quantity']=count
        else:del w['assets'][key]

    def human_purchase(self,st,row,stamp):
        key=row.get('_market_npc_lot')
        if key is None:return
        w=st['market_simulation']['npc_exchange'];asset=w['assets'].get(key)
        if asset is None or asset.get('listing') is not row:raise ValueError('Stale NPC listing')
        price=row['price'];fee=price//100
        w['agents'][asset['owner']]['wallet']+=price-fee;w['fees']+=fee;w['human_buys']+=1
        self._history(w,dict(kind='npc_to_player',asset=key,spid=asset['spid'],grade=asset['grade'],seller=asset['owner'],price=price,at=stamp))
        self._take(w,key,public=True)

    def _burn(self,w,stamp,seed,step):
        total=sum(max(0,self.available(a)) for a in w['assets'].values())
        if total<=0:return
        expected=max(1. if total>=10 else 0.,total*INTERNAL_BURN_FRACTION)
        amount=min(total,50,int(expected)+(self.market.unit(f'{seed}:burn-count:{step}')<expected-int(expected)))
        if amount<=0:return
        keys=sorted(w['assets'],key=lambda k:self.market.unit(f'{seed}:burn-order:{step}:{k}'));details=[];left=amount
        for key in keys:
            asset=w['assets'].get(key)
            if asset is None:continue
            count=min(left,max(0,self.available(asset)))
            if not count:continue
            details.append(dict(spid=asset['spid'],grade=asset['grade'],owner=asset['owner'],quantity=count))
            remaining=self.quantity(asset)-count
            if remaining:asset['quantity']=remaining
            else:del w['assets'][key]
            left-=count
            if not left:break
        used=amount-left;w['consumed_cards']+=used
        reason='simulated_enhancement_failure' if self.market.unit(f'{seed}:burn-kind:{step}')<.5 else 'simulated_combination_material'
        self._history(w,dict(kind='npc_consumption',reason=reason,quantity=used,details=details,at=stamp))

    def advance(self,st,stamp):
        w=self.world(st,stamp);step=int(stamp//15)
        if step<=w['last_step']:return
        w['last_step']=step;seed=st['market_simulation']['seed']
        # Public rows provide card variety only. No public row is removed or
        # decremented; inventory comes from an independent simulated supplier.
        sources=[r for r in self.market.featured_rows(st,stamp,limit=50) if r['grade']<=10 and self.market.npc_supply_allowed(r['spid'],r['grade'])]
        if not sources:
            cards=self.market.candidates()
            if cards:
                sources=[dict(spid=cards[int(self.market.unit(f'{seed}:internal-card:{step}:{i}')*len(cards))%len(cards)],grade=(1,2,3,5,7,8,9,10)[int(self.market.unit(f'{seed}:internal-grade:{step}:{i}')*8)%8]) for i in range(BUY_PER_TICK)]
        sources=[r for r in sources if self.market.npc_supply_allowed(r['spid'],r['grade'])]
        if sources:
            offset=int(self.market.unit(f'{seed}:source:{step}')*len(sources))
            for i in range(BUY_PER_TICK):
                sample=sources[(offset+i)%len(sources)];asset={'spid':sample['spid'],'grade':sample['grade']}
                price=self.market.quote(asset['spid'],asset['grade'],st)
                buyer=max(w['agents'],key=lambda a:self._preference(a,asset,stamp,seed)+.1*self.market.unit(f'{seed}:buyer:{step}:{i}:{a["id"]}'))
                if buyer['wallet']<price:
                    income=price-buyer['wallet']+INITIAL_WALLET;buyer['wallet']+=income;w['simulated_income']+=income
                    self._history(w,dict(kind='npc_external_income',buyer=buyer['id'],amount=income,at=stamp))
                buyer['wallet']-=price;w['supplier_wallet']+=price
                key=self._put(w,asset['spid'],asset['grade'],buyer['id'],price,stamp)
                w['source_buys']+=1;w['internal_source_buys']+=1
                self._history(w,dict(kind='internal_supply_to_npc',asset=key,spid=asset['spid'],grade=asset['grade'],buyer=buyer['id'],price=price,quantity=1,at=stamp))
        # Reserved offers are frozen until normal expiry/player purchase. NPC
        # peer trades and consumption use only the unreserved internal units.
        traded=0;ordered=sorted(w['assets'],key=lambda k:self.market.unit(f'{seed}:match:{step}:{k}'))
        for key in ordered:
            if traded>=TRADE_PER_TICK:break
            asset=w['assets'].get(key)
            if asset is None or self.available(asset)<=0 or stamp<asset['acquired_at']+HOLD_SECONDS:continue
            q=self.market.quote(asset['spid'],asset['grade'],st);seller=w['agents'][asset['owner']]
            age=min(.20,(stamp-asset['acquired_at'])/3600*.12)
            ask=max(.6,min(1.4,self._preference(seller,asset,stamp,seed)-.06-age));price=max(1,int(q*ask))
            candidates=[a for a in w['agents'] if a['id']!=seller['id'] and a['wallet']>=price and q*self._preference(a,asset,stamp,seed)>=price]
            if not candidates:continue
            buyer=max(candidates,key=lambda a:self._preference(a,asset,stamp,seed));fee=price//100
            buyer['wallet']-=price;seller['wallet']+=price-fee;w['fees']+=fee
            spid,grade=asset['spid'],asset['grade'];self._take(w,key);target=self._put(w,spid,grade,buyer['id'],price,stamp)
            self._history(w,dict(kind='npc_peer',asset=key,target_asset=target,spid=spid,grade=grade,buyer=buyer['id'],seller=seller['id'],price=price,at=stamp))
            w['peer_trades']+=1;traded+=1
            self.market.record(st,{'_id':f'npc:{key}:{step}','spid':spid,'grade':grade,'price':price,
                '_market_owner':'npc:'+str(seller['id']),'_market_player':{},'_market_kind':'npc_peer',
                '_market_buyer':buyer['id'],'_market_seller':seller['id']},stamp)
        self._burn(w,stamp,seed,step)
        for asset in w['assets'].values():
            if asset.get('listing') is not None and stamp>=asset['listed_at']+300:del asset['listing']
        listed=sum(a.get('listing') is not None for a in w['assets'].values())
        candidates=sorted(w['assets'],key=lambda k:self.market.unit(f'{seed}:public-rotation:{int(stamp//300)}:{k}'))
        for key in candidates:
            if listed>=MAX_VISIBLE_LISTINGS:break
            asset=w['assets'][key]
            if not self.market.npc_supply_allowed(asset['spid'],asset['grade']):continue
            if asset.get('listing') is not None or stamp<asset['acquired_at']+LIST_DELAY:continue
            owner=w['agents'][asset['owner']];q=self.market.quote(asset['spid'],asset['grade'],st)
            age=min(.20,(stamp-asset['acquired_at'])/3600*.12);ask=max(.6,min(1.4,self._preference(owner,asset,stamp,seed)-.06-age))
            asset['listed_at']=stamp;asset['listing']={'spid':asset['spid'],'grade':asset['grade'],'expandme':'player','price':max(1,int(q*ask)),'count':1,'_market_npc_lot':key};listed+=1

    def status(self,st,stamp):
        w=st.get('market_simulation',{}).get('npc_exchange')
        if not w:return {'initialized':False,'price_store':self.price_store.status()}
        return dict(initialized=True,agents=len(w['agents']),owned_cards=sum(self.quantity(a) for a in w['assets'].values()),inventory_lots=len(w['assets']),listed_cards=len(self.listings(st,stamp)),inventory_cap=None,per_agent_inventory_cap=None,public_listing_cap=MAX_VISIBLE_LISTINGS,public_pool_purchases_since_v2=0,internal_source_buys=w.get('internal_source_buys',0),consumed_cards=w.get('consumed_cards',0),simulated_income=w.get('simulated_income',0),
            source_buys=w['source_buys'],peer_trades=w['peer_trades'],human_buys=w['human_buys'],fees=w['fees'],
            wallet_total=sum(a['wallet'] for a in w['agents']),supplier_wallet=w['supplier_wallet'],last_step=w['last_step'],
            trades_last_5_minutes=sum(e['kind']=='npc_peer' and e['at']>=stamp-300 for e in w['history']),
            recent_trades=w['history'][-25:],model='role_ability_value_v1_with_bounded_trade_movement',price_store=self.price_store.status())


def install(hc):
    """Compose after the installed grade-price adapter, before starting workers."""
    if getattr(hc,'_npc_exchange_value_installed',False):return hc.market_engine.exchange
    engine=hc.market_engine
    engine.reference=hc.player_value_price
    hc.player_value_price=engine.exchange.reference_value
    import admin,logging,sys
    old_save=hc._save
    def save(st):
        # Commit manager/card transactions first. A crash before the DB commit
        # leaves a persisted replay queue, never an uncommitted price movement.
        result=old_save(st)
        pending=st.get('market_simulation',{}).get('price_events',[])
        try:
            engine.exchange.price_store.flush(pending)
            if pending:st['market_simulation']['price_events']=[]
        except Exception:
            logging.getLogger(__name__).exception('Committed market price events await retry')
        return result
    hc._save=save
    engine.exchange.price_store.flush(hc._state().get('market_simulation',{}).get('price_events',[]))
    def price_status(params):
        store=engine.exchange.price_store;out=store.status()
        out['runtime_model_modules']=[name for name in ('npc_attribute_value','expanded_value_model') if name in sys.modules]
        out['runtime_model_loaded']=bool(out['runtime_model_modules'])
        out['active_valuation_policy']='ability-value-v1'
        out['historical_basis_unit']='immutable old seed EP; not the active displayed price'
        if params.get('spid') is not None:
            spid=admin.as_int(params['spid'],1,2**31-1,'spid');grade=admin.as_int(params.get('grade',1),1,hc.MAX_GRADE,'grade')
            out.update(spid=spid,grade=grade,initial_price=store.initial(spid),
                legacy_current_basis=store.current(spid),current_price=engine.exchange.base_value(spid),
                value=hc.player_value_price(spid,grade),ability=engine.exchange.ability_prices.explain(spid),
                market_factor=engine.exchange.ability_prices.policy.market_factor(store.basis(spid),store.initial(spid)))
        return out
    admin.READ_ONLY.add('market_price_store');admin.API['market_price_store']=price_status
    hc.market_reference_price=hc.player_value_price
    hc._npc_exchange_value_installed=True
    return engine.exchange
