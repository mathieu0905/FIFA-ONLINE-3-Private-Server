"""Temporary-data transaction, restart, grade and trade-discovery regression."""
from pathlib import Path
import copy,gzip,hashlib,json,sys,tempfile,types
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from market_price_store import MarketPriceStore,initialize,verify_seed,MAX_PRICE
from market_simulation import Market
from npc_exchange import NpcExchange
TMP=P/'tmp';TMP.mkdir(exist_ok=True)
checks=[]
def check(value,name):
 assert value,name;checks.append(name)
def seed(root,name='prices'):
 rows=[[101,100000],[102,200000]];p=root/(name+'.json.gz')
 data=dict(schema=1,price_region='kr',model_sha256='0'*64,seed_prices_sha256=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest(),rows=rows)
 with gzip.open(p,'wt',encoding='utf8') as f:json.dump(data,f)
 db=root/(name+'.sqlite');initialize(db,p,'unit-seed');return db,p
def market(db):
 m=Market.__new__(Market);m.h=types.SimpleNamespace(HERE=str(db.parent),MARKET_PRICE_DB_PATH=db,MAX_GRADE=20,_default_slot=lambda st:0)
 factors={1:1,8:1090,20:10000000};m.reference=lambda spid,g:100000*factors.get(g,1) if g else 0;m.exchange=NpcExchange(m);m.valid_card=lambda spid,g=True:m.exchange.price_store.current(spid)>0;return m
def state():return {'coaches':[{'slot':0,'_market_owner':'owner'}],'teams':{'0':{'players':[{'_id':'real-like-test-id','experience':123,'grade':8}]}},'balance':123456,'offers':[], 'market_simulation':dict(version=2,books={},rare_books={},buyers={},created_at=0,sales=[],quotes={},supply_version=3,player_price_divisor=1000,attribute_value_model_version=1,legacy_migrated=True,price_events=[],price_store_version=1)}
def sale(m,st,key,stamp,ratio=1.3,origin=None):
 price=round(m.exchange.reference_value(101,1,st)*ratio)
 offer=dict(_id=key,spid=101,grade=1,price=price,_market_owner='npc:0',_market_kind='npc_peer',_market_buyer=1,_market_seller=0,_market_player={} if origin is None else {'_market_origin':origin})
 m.record(st,offer,stamp)
with tempfile.TemporaryDirectory(prefix='market-store-',dir=TMP) as tmp:
 root=Path(tmp).resolve();assert root.is_relative_to(TMP.resolve());db,seedfile=seed(root);m=market(db);st=state();assets=copy.deepcopy({k:v for k,v in st.items() if k!='market_simulation'})
 sale(m,st,'a',0);sale(m,st,'b',900)
 check(m.exchange.price_store.current(101)==100000 and not st['market_simulation']['price_events'],'two trades cannot move prices')
 sale(m,st,'c',1900)
 check(m.exchange.price_store.current(101)==100000,'uncommitted state cannot move database price')
 check(round(st['market_simulation']['quotes']['101']['basis_price'])==100500,'funded volume gate stages a 0.5 percent move')
 committed=json.loads(json.dumps(st));m.exchange.price_store.close();m=market(db)
 check(m.exchange.price_store.current(101)==100000,'crash before price commit retains initial DB value')
 count=m.exchange.price_store.flush(committed['market_simulation']['price_events']);check(count==1 and m.exchange.price_store.current(101)==100500,'committed state events replay after restart')
 check(m.exchange.price_store.flush(committed['market_simulation']['price_events'])==0 and m.exchange.price_store.current(101)==100500,'replay is idempotent')
 check(m.exchange.reference_value(101,8)==100500*1090,'external enhancement multiplier unchanged')
 check(m.exchange.reference_value(101,20)<=MAX_PRICE,'existing display ceiling retained')
 check(m.exchange.reference_value(999,1)==0,'unknown unseeded card is not sold at a fabricated cheap price')
 st=committed
 for day in range(1,31):
  before=m.exchange.price_store.basis(101)
  for group in range(4):
   for j,offset in enumerate((0,900,1900)):sale(m,st,f'{day}-{group}-{j}',day*86400+group*2500+offset)
   m.exchange.price_store.flush(st['market_simulation']['price_events'])
  check(m.exchange.price_store.basis(101)<=before*1.02+1e-7,'daily upward movement is bounded '+str(day))
 check(m.exchange.price_store.current(101)>160000,'market can move beyond 1.6 times the original neural seed')
 before=m.exchange.price_store.current(101);events=len(m.exchange.price_store._events)
 good=dict(event_id='atomic-good',spid=101,before=m.exchange.price_store.basis(101),after=m.exchange.price_store.basis(101)*1.001,at=99999999,reason='funded_trade_volume')
 bad=dict(event_id='atomic-bad',spid=102,before=1.,after=2.,at=99999999,reason='funded_trade_volume')
 try:m.exchange.price_store.flush([good,bad]);raise AssertionError('Invalid cursor must fail')
 except RuntimeError:pass
 check(m.exchange.price_store.current(101)==before and len(m.exchange.price_store._events)==events,'failed batch rolls back prices and event IDs')
 verify_seed(db,seedfile);check(True,'mutable current prices pass immutable seed verification')
 preserved=m.exchange.price_store.current(101);m.exchange.price_store.close();m=market(db)
 check(m.exchange.price_store.current(101)==preserved,'service reopen never resets current prices')
 check('npc_attribute_value' not in sys.modules,'runtime never imports any valuation model')
 check({k:v for k,v in st.items() if k!='market_simulation'}==assets,'manager balances, cards, XP and grades untouched by price discovery')
 m.exchange.price_store.close()
 db2,seed2=seed(root,'migration');m=market(db2);st=state();st['market_simulation'].pop('price_store_version');st['market_simulation']['quotes']['101']={'factor':1.2,'day':0,'movement':0.,'pending':[{'ratio':99,'at':0}]}
 m.prepare(st);m.exchange.price_store.flush(st['market_simulation']['price_events']);check(m.exchange.price_store.current(101)==120000,'legacy market movement is inherited exactly once')
 m.prepare(st);m.exchange.price_store.flush(st['market_simulation']['price_events']);check(m.exchange.price_store.current(101)==120000,'repeat prepare cannot apply migration twice')
 seed2.unlink();m.exchange.price_store.close();m=market(db2);check(m.exchange.price_store.current(101)==120000,'runtime works without neural model or install seed file');m.exchange.price_store.close()
report=dict(status='PASS',checks=len(checks),details=checks,real_state_written=False,real_price_database_written=False)
(P/'regression.json').write_text(json.dumps(report,indent=2),'utf8');print(json.dumps(report,indent=2))
