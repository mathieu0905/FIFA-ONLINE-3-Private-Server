from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
n=(S/'npc_exchange.py').read_text('utf8');market=(S/'market_simulation.py').read_text('utf8')
baseline={name:hashlib.sha256((S/name).read_bytes()).hexdigest() for name in ('npc_exchange.py','market_simulation.py')}
n=n.replace('from npc_attribute_value import AttributeValueModel','from market_price_store import MarketPriceStore, MAX_PRICE')
a=n.index('    def __init__(self, market, model_path=None):');b=n.index('    def world(',a)
n=n[:a]+'''    def __init__(self, market, model_path=None):
        self.market=market
        path=getattr(market.h,'MARKET_PRICE_DB_PATH',Path(market.h.HERE)/'gamedata/npc-market-prices.sqlite')
        self.price_store=MarketPriceStore(path)
        self._profiles={}

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
        if st is not None:
            basis=st.get('market_simulation',{}).get('quotes',{}).get(str(int(spid)),{}).get('basis_price')
            if basis is not None:return max(1,round(basis))
        return self.price_store.current(spid)

    def reference_value(self,spid,grade,st=None):
        base=self.base_value(spid,st)
        if base<=0:return 0
        graded=self.market.reference(spid,grade)
        if graded<=0:return 0
        anchor=max(1,self.market.reference(spid,1))
        # Inherit the existing grade curve and its display ceiling.
        return min(MAX_PRICE,max(1,base*graded//anchor))

''' + n[b:]
n=n.replace("if not w:return {'initialized':False}","if not w:return {'initialized':False,'price_store':self.price_store.status()}")
n=n.replace("recent_trades=w['history'][-25:],model='height_weight_33_abilities_only; historical EP /1000; external grade multiplier unchanged')","recent_trades=w['history'][-25:],model='one_time_neural_seed_then_trade_driven_database',price_store=self.price_store.status())")
needle='    hc._npc_exchange_value_installed=True'
insert='''    import admin,logging,sys
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
        if params.get('spid') is not None:
            spid=admin.as_int(params['spid'],1,2**31-1,'spid');grade=admin.as_int(params.get('grade',1),1,hc.MAX_GRADE,'grade')
            out.update(spid=spid,grade=grade,initial_price=store.initial(spid),current_price=store.current(spid),value=hc.player_value_price(spid,grade))
        return out
    admin.READ_ONLY.add('market_price_store');admin.API['market_price_store']=price_status
    hc.market_reference_price=hc.player_value_price
'''
assert n.count(needle)==1;n=n.replace(needle,insert+needle)

old="""        factor = st.get('market_simulation', {}).get('quotes', {}).get(str(int(spid)), {}).get('factor', 1.0)
        return min((2**53-1)//3, max(1, int(self.exchange.reference_value(int(spid), int(grade)) * min(1.6, max(.6, factor)))))"""
new="""        # Current database/state price only. No valuation model or seed anchor.
        return min((2**53-1)//3, max(1, self.exchange.reference_value(int(spid),int(grade),st)))"""
assert old in market;market=market.replace(old,new)
market=market.replace("'reference_policy':'attribute-only +1 value; independent external grade multiplier; actual NPC/player trades move quotes'","'reference_policy':'one-time model seed; persistent trade-only current prices; inherited grade multiplier'")
needle="            return self._known_cards[spid]"
assert market.count(needle)==1;market=market.replace(needle,"            return self._known_cards[spid] and self.exchange.price_store.current(spid)>0")
needle="            cards = list(self.h.market_spids() & present)"
assert needle in market;market=market.replace(needle,"            cards = [s for s in self.h.market_spids() & present if self.exchange.price_store.current(s)>0]")
needle="        m.setdefault('created_at', now())"
insert='''
        pending_events=m.setdefault('price_events',[])
        # Only remove already committed events; never write an uncommitted
        # state transaction to the price DB from prepare()/read operations.
        m['price_events']=[e for e in pending_events if not self.exchange.price_store.applied(e['event_id'])]
        if m.get('price_store_version')!=1:
            for spid,q in m.get('quotes',{}).items():
                before=self.exchange.price_store.basis(spid)
                if before<=0:continue
                factor=min(1.6,max(.6,q.get('factor',1.)))
                basis=min(5_600_000_000_000_000,max(1.,before*factor))
                if basis!=before:
                    m['price_events'].append(dict(event_id='seed-migration:'+self.exchange.price_store.meta['seed_revision']+':'+spid,spid=int(spid),before=before,after=basis,at=now(),reason='legacy_market_movement',evidence={'legacy_factor':factor}))
                q['basis_price']=basis
                q['prior_model_pending']=q.get('pending',[]);q['pending']=[]
                q['movement']=min(math.log(1.02),q.get('movement',0.))
            m['price_store_version']=1
'''
assert market.count(needle)==1;market=market.replace(needle,needle+insert)
old="'ratio': offer['price'] / max(1, self.exchange.reference_value(offer['spid'], offer['grade']))"
assert old in market;market=market.replace(old,"'ratio': offer['price'] / max(1, self.exchange.reference_value(offer['spid'], offer['grade'],st))")
market=market.replace("pending.append({'ratio': entry['ratio'], 'at': stamp})","pending.append({'ratio': entry['ratio'], 'at': stamp, 'id':entry['id'], 'kind':entry['kind'], 'price':entry['price'], 'grade':entry['grade']})")
old="""        factor = quote['factor']; delta = max(-.005, min(.005, (target - factor) * .1))
        budget = max(0, .02 - quote['movement']); delta = max(-budget, min(budget, delta))
        value = min(1.6, max(.6, factor + delta))
        quote.update(factor=value, movement=quote['movement'] + abs(value-factor), pending=[])"""
new="""        before=quote.get('basis_price',self.exchange.price_store.basis(spid))
        if before<=0:return
        delta=max(-math.log(1.005),min(math.log(1.005),math.log(max(1e-12,target))*.1))
        budget=max(0.,math.log(1.02)-quote['movement']);delta=max(-budget,min(budget,delta))
        value=min(5_600_000_000_000_000,max(1.,before*math.exp(delta)))
        if value!=before:
            st['market_simulation'].setdefault('price_events',[]).append(dict(
                event_id='trade-price:'+str(entry['id']),spid=int(spid),before=before,after=value,at=stamp,
                reason='funded_trade_volume',evidence={'sales':list(pending),'median_ratio':target}))
        quote.update(basis_price=value,movement=quote['movement']+abs(math.log(value/before)),pending=[])"""
assert old in market;market=market.replace(old,new)
for name,raw in [('npc_exchange.py',n),('market_simulation.py',market)]:compile(raw,name,'exec');(P/name).write_bytes(raw.encode('utf8'))
(P/'source-baseline.json').write_text(json.dumps(baseline,indent=2),'utf8')
print('Prepared one-time seed / persistent trade-driven market patches')
