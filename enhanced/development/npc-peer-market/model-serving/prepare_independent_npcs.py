"""Independent NPC warehouse; public listings reserve units away from NPC trades."""
from pathlib import Path
P=Path(__file__).resolve().parent;n=(P/'npc_exchange.py').read_text('utf8')
n=n.replace('Finite NPC wallets, owned card lots, listings and actual peer settlement.','Independent NPC inventory, reserved public offers, virtual income and actual peer settlement.')
n=n.replace('MAX_ASSETS=192\nMAX_PER_AGENT=12\n','MAX_VISIBLE_LISTINGS=192\nINTERNAL_BURN_FRACTION=.0025\n')
a=n.index('    def human_purchase(');b=n.index('    def status(',a)
n=n[:a]+'''    @staticmethod
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
        sources=[r for r in self.market.featured_rows(st,stamp,limit=50) if r['grade']<=10]
        if not sources:
            cards=self.market.candidates()
            if cards:
                sources=[dict(spid=cards[int(self.market.unit(f'{seed}:internal-card:{step}:{i}')*len(cards))%len(cards)],grade=(1,2,3,5,7,8,9,10)[int(self.market.unit(f'{seed}:internal-grade:{step}:{i}')*8)%8]) for i in range(BUY_PER_TICK)]
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
            if asset.get('listing') is not None or stamp<asset['acquired_at']+LIST_DELAY:continue
            owner=w['agents'][asset['owner']];q=self.market.quote(asset['spid'],asset['grade'],st)
            age=min(.20,(stamp-asset['acquired_at'])/3600*.12);ask=max(.6,min(1.4,self._preference(owner,asset,stamp,seed)-.06-age))
            asset['listed_at']=stamp;asset['listing']={'spid':asset['spid'],'grade':asset['grade'],'expandme':'player','price':max(1,int(q*ask)),'count':1,'_market_npc_lot':key};listed+=1

''' + n[b:]
needle="        return m['npc_exchange']"
replacement="""        w=m['npc_exchange']
        if w.get('version',1)<2:
            w['version']=2;w['historical_public_source_buys']=w.get('source_buys',0)
            w['internal_source_buys']=0;w['consumed_cards']=0;w['simulated_income']=0
            for asset in w['assets'].values():asset.setdefault('quantity',1)
        return w"""
assert n.count(needle)==1;n=n.replace(needle,replacement)
n=n.replace("counts[asset['owner']]+=1","counts[asset['owner']]+=self.quantity(asset)")
n=n.replace("agents=len(w['agents']),owned_cards=len(w['assets']),listed_cards=len(self.listings(st,stamp)),","agents=len(w['agents']),owned_cards=sum(self.quantity(a) for a in w['assets'].values()),inventory_lots=len(w['assets']),listed_cards=len(self.listings(st,stamp)),inventory_cap=None,per_agent_inventory_cap=None,public_listing_cap=MAX_VISIBLE_LISTINGS,public_pool_purchases_since_v2=0,internal_source_buys=w.get('internal_source_buys',0),consumed_cards=w.get('consumed_cards',0),simulated_income=w.get('simulated_income',0),")
compile(n,'npc_exchange.py','exec');(P/'npc_exchange.py').write_bytes(n.encode('utf8'));print('Prepared independent unlimited NPC inventory, reserved public offers, and simulated consumption')
