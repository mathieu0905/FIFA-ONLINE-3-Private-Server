"""Finite NPC wallets, owned card lots, listings and actual peer settlement.
Runs only inside Market.tick's state transaction. No client requests drive simulation.
"""
import math
from pathlib import Path
from npc_attribute_value import AttributeValueModel

AGENTS=32
INITIAL_WALLET=10**15
MAX_ASSETS=192
MAX_PER_AGENT=12
BUY_PER_TICK=3
TRADE_PER_TICK=6
HOLD_SECONDS=60
LIST_DELAY=30
FEE_RATE=.01

class NpcExchange:
    def __init__(self, market, model_path=None):
        self.market=market
        self.model=AttributeValueModel(model_path or Path(market.h.HERE)/'gamedata/npc_attribute_value.json')
        self._profiles={}
        self._factors={}

    def profile(self, spid):
        if spid not in self._profiles:
            fields=self.model.model['features']
            with self.market.h.closing(self.market.h._db()) as db:
                row=db.execute('SELECT '+','.join(fields)+' FROM players WHERE spid=?',(spid,)).fetchone()
            if row is None:raise ValueError('NPC card missing from database')
            self._profiles[spid]=dict(zip(fields,row))
        return self._profiles[spid]

    def base_value(self,spid):
        if spid not in self._factors:
            # Pure attribute estimate in the installed EP denomination. No OVR,
            # identity, season or historical-card lookup is used by the model.
            self._factors[spid]=max(1,self.model.predict(self.profile(spid))//1000)
        return self._factors[spid]

    def reference_value(self,spid,grade):
        # The other owner controls the enhancement curve. We replace only +1.
        graded=self.market.reference(spid,grade)
        if graded<=0:return 0
        anchor=max(1,self.market.reference(spid,1))
        return max(1,self.base_value(spid)*graded//anchor)

    def world(self,st,stamp):
        m=st['market_simulation']
        if 'npc_exchange' not in m:
            m['npc_exchange']={'version':1,'created_at':stamp,'last_step':int(stamp//15)-1,
                'serial':0,'agents':[{'id':i,'wallet':INITIAL_WALLET,'style':i%4} for i in range(AGENTS)],
                'assets':{},'supplier_wallet':0,'fees':0,'source_buys':0,'peer_trades':0,
                'human_buys':0,'history':[]}
        return m['npc_exchange']

    def listings(self,st,stamp,spid=None):
        w=st.get('market_simulation',{}).get('npc_exchange',{})
        return [a['listing'] for a in w.get('assets',{}).values()
            if 'listing' in a and a['listing']['count']>0
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

    def human_purchase(self,st,row,stamp):
        key=row.get('_market_npc_lot')
        if key is None:return
        w=st['market_simulation']['npc_exchange'];asset=w['assets'].get(key)
        if asset is None or asset.get('listing') is not row:raise ValueError('Stale NPC listing')
        price=row['price'];fee=price//100
        w['agents'][asset['owner']]['wallet']+=price-fee;w['fees']+=fee;w['human_buys']+=1
        self._history(w,dict(kind='npc_to_player',asset=key,spid=asset['spid'],grade=asset['grade'],seller=asset['owner'],price=price,at=stamp))
        del w['assets'][key]

    def advance(self,st,stamp):
        w=self.world(st,stamp);step=int(stamp//15)
        if step<=w['last_step']:return
        # No offline burst or replay; successful state save commits this step once.
        w['last_step']=step;seed=st['market_simulation']['seed'];counts=self._counts(w)
        sources=self.market.featured_rows(st,stamp,limit=50)
        sources=[r for r in sources if r['grade']<=10]
        if sources:
            offset=int(self.market.unit(f'{seed}:source:{step}')*len(sources))
            bought=0
            for i in range(len(sources)):
                if bought>=BUY_PER_TICK or len(w['assets'])>=MAX_ASSETS:break
                sample=sources[(offset+i)%len(sources)]
                # Actual book row, never a synthetic source or a second copy of a lot.
                row=next((r for r in self.market.book(st,sample['spid'],stamp)['rows']
                          if r['grade']==sample['grade'] and r['count']>0),None)
                if row is None:continue
                asset={'spid':row['spid'],'grade':row['grade']}
                eligible=[a for a in w['agents'] if counts[a['id']]<MAX_PER_AGENT and a['wallet']>=row['price']]
                if not eligible:break
                buyer=max(eligible,key=lambda a:self._preference(a,asset,stamp,seed)+.1*self.market.unit(f'{seed}:buyer:{step}:{i}:{a["id"]}'))
                row['count']-=1;buyer['wallet']-=row['price'];w['supplier_wallet']+=row['price']
                w['serial']+=1;key=str(w['serial'])
                asset.update(owner=buyer['id'],acquired_at=stamp,cost=row['price'],created_at=stamp)
                w['assets'][key]=asset;counts[buyer['id']]+=1;w['source_buys']+=1;bought+=1
                self._history(w,dict(kind='supply_to_npc',asset=key,spid=asset['spid'],grade=asset['grade'],buyer=buyer['id'],price=row['price'],at=stamp))
        # Every offer references one owned lot. Once listed, its price is frozen;
        # only expiry/relisting changes the asking price.
        for key,asset in w['assets'].items():
            listing=asset.get('listing')
            if listing is not None and stamp>=asset['listed_at']+300:
                del asset['listing'];listing=None
            if listing is None and stamp>=asset['acquired_at']+LIST_DELAY:
                owner=w['agents'][asset['owner']];q=self.market.quote(asset['spid'],asset['grade'],st)
                age=min(.20,(stamp-asset['acquired_at'])/3600*.12)
                ask=max(.6,min(1.4,self._preference(owner,asset,stamp,seed)-.06-age))
                price=max(1,int(q*ask));asset['listed_at']=stamp
                asset['listing']={'spid':asset['spid'],'grade':asset['grade'],'expandme':'player','price':price,'count':1,'_market_npc_lot':key}
        traded=0
        ordered=sorted(w['assets'],key=lambda key:self.market.unit(f'{seed}:match:{step}:{key}'))
        for key in ordered:
            if traded>=TRADE_PER_TICK:break
            asset=w['assets'][key];row=asset.get('listing')
            if row is None or stamp<asset['acquired_at']+HOLD_SECONDS or stamp<asset['listed_at']+15:continue
            q=self.market.quote(asset['spid'],asset['grade'],st)
            candidates=[a for a in w['agents'] if a['id']!=asset['owner'] and counts[a['id']]<MAX_PER_AGENT and a['wallet']>=row['price']
                        and q*self._preference(a,asset,stamp,seed)>=row['price']]
            if not candidates:continue
            buyer=max(candidates,key=lambda a:self._preference(a,asset,stamp,seed))
            seller=w['agents'][asset['owner']];price=row['price'];fee=price//100
            buyer['wallet']-=price;seller['wallet']+=price-fee;w['fees']+=fee
            counts[seller['id']]-=1;counts[buyer['id']]+=1
            event=dict(kind='npc_peer',asset=key,spid=asset['spid'],grade=asset['grade'],buyer=buyer['id'],seller=seller['id'],price=price,at=stamp)
            self._history(w,event);w['peer_trades']+=1;traded+=1
            # Feed only completed, funded, cross-owner trades to the existing
            # volume/time gate and bounded quote movement rules.
            self.market.record(st,{'_id':f'npc:{key}:{step}','spid':asset['spid'],'grade':asset['grade'],'price':price,
                '_market_owner':'npc:'+str(seller['id']),'_market_player':{},'_market_kind':'npc_peer',
                '_market_buyer':buyer['id'],'_market_seller':seller['id']},stamp)
            asset.update(owner=buyer['id'],acquired_at=stamp,cost=price)
            del asset['listing']

    def status(self,st,stamp):
        w=st.get('market_simulation',{}).get('npc_exchange')
        if not w:return {'initialized':False}
        return dict(initialized=True,agents=len(w['agents']),owned_cards=len(w['assets']),listed_cards=len(self.listings(st,stamp)),
            source_buys=w['source_buys'],peer_trades=w['peer_trades'],human_buys=w['human_buys'],fees=w['fees'],
            wallet_total=sum(a['wallet'] for a in w['agents']),supplier_wallet=w['supplier_wallet'],last_step=w['last_step'],
            trades_last_5_minutes=sum(e['kind']=='npc_peer' and e['at']>=stamp-300 for e in w['history']),
            recent_trades=w['history'][-25:],model='height_weight_33_abilities_only; historical EP /1000; external grade multiplier unchanged')


def install(hc):
    """Compose after the installed grade-price adapter, before starting workers."""
    if getattr(hc,'_npc_exchange_value_installed',False):return hc.market_engine.exchange
    engine=hc.market_engine
    engine.reference=hc.player_value_price
    hc.player_value_price=engine.exchange.reference_value
    hc._npc_exchange_value_installed=True
    return engine.exchange
