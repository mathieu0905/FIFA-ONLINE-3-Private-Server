import copy,json,sys,tempfile,threading,types
from pathlib import Path
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');sys.path[:0]=[str(P),str(S)]
from market_supply_settings import SupplySettings,DEFAULTS,validate
from market_simulation import Market
import npc_exchange as npc
checks=[]
def check(ok,name):
 assert ok,name
 checks.append(name)
old=copy.deepcopy(DEFAULTS);del old['rare_listing_seconds'];del old['npc_listing_seconds'];check(validate(old)['rare_listing_seconds']==1800,'Existing online settings migrate compatibly')
with tempfile.TemporaryDirectory(dir=P) as root:
 cfg=SupplySettings(Path(root)/'settings.json',threading.RLock());m=Market.__new__(Market);m.supply_settings=cfg;m.h=types.SimpleNamespace(MAX_GRADE=20);m.unit=lambda seed:.01;m.quote=lambda *a:100;m.quality_pools=lambda:{'elite':(93001075,)}
 tier=dict(key='elite_15',quality='elite',grades=(15,),period=300,slots=5,chance=1.,quantity=1,pool_size=1,expected_per_day=288*5)
 m.supply_plan=lambda:[tier]
 st={'market_simulation':dict(seed='fixture',supply_started_at=0,rare_books={},legacy_supply=[])}
 active=m.rare_stock(st,241);check(all(r['_market_expires']-r['_market_release']==1800 for r in active),'Minute release cadence has independent thirty-minute TTL')
 first=next(r for r in active if r['_market_release']==240);check(first['price']==100 and first['count']==1,'A newly exposed offer has its real price and stock')
 after=m.rare_stock(st,301);check(any(r is first for r in after),'Same offer survives the five-minute batch boundary')
 check(first['_market_expires']==2040 and first['price']==100,'Carry-over preserves signed expiry and price')
 first['count']-=1;check(first not in m.rare_stock(st,302),'Buying a carried offer consumes it immediately')
 check(not any(r['_market_release']==240 for r in m.rare_stock(st,303)),'Repeated reads never refill a sold carried offer')
 held=next(r for r in after if r['_market_release']==180);held['price']=777
 check(any(r is held for r in m.rare_stock(st,601)),'Offer survives multiple batch turnovers')
 check(held['price']==777,'Current market price changes cannot reprice a carried contract')
 check(held not in m.rare_stock(st,held['_market_expires']),'Offer expires exactly at its independent TTL')
 # Upgrade only still-live unsold offers, never resurrect expired or consumed stock.
 row=lambda release,expires,count:dict(spid=93001075,grade=15,price=321,count=count,_market_release=release,_market_expires=expires)
 live=row(240,300,1);expired=row(180,240,1);sold=row(240,300,0)
 legacy=dict(epoch=0,start=0,period=300,slots=5,chance=1,pool_size=1,rows=[live,expired,sold]);state={'market_simulation':dict(seed='fixture',supply_started_at=0,rare_books={'elite_15':legacy},legacy_supply=[])}
 m.rare_stock(state,250);check(live['_market_expires']==2040,'Existing still-live minute offer is extended during migration')
 check(expired['_market_expires']==240 and sold['count']==0,'Expired and sold offers are not revived by migration')
 # Late quoting is preserved when an unquoted surviving opportunity crosses a batch boundary.
 future=row(240,2040,1);future['price']=None;state={'market_simulation':dict(seed='fixture',supply_started_at=0,rare_books={'elite_15':dict(legacy,rows=[future])},legacy_supply=[],independent_offer_lifetime_v2=True)}
 result=m.rare_stock(state,310);check(future in result and future['price']==100,'Carried unquoted stock freezes a valid quote before it becomes purchasable')
 # NPC public offers keep their reserved unit and do not rotate away at five minutes.
 m.featured_rows=lambda *a,**k:[];m.candidates=lambda:();m.record=lambda *a:None;m.unit=lambda s:.01;e=npc.NpcExchange.__new__(npc.NpcExchange);e.market=m;e._preference=lambda *a:1;e._burn=lambda *a:None;npc.TRADE_PER_TICK=0
 state={'market_simulation':{'seed':'fixture'}};w=e.world(state,300);asset=dict(spid=93001075,grade=8,owner=0,quantity=1,cost=100,acquired_at=0,listed_at=0,listing=dict(spid=93001075,grade=8,count=1,price=77));w['assets']['1']=asset;w['serial']=1
 e.advance(state,301);check(asset['listing']['price']==77,'NPC reserved public offer does not rotate away after five minutes')
 check(e.available(asset)==0,'Public unit remains protected from NPC peer trades')
 # Inspect real state on a copy. No real assets are saved by this test.
 real=json.loads((S/'gamedata/state.json').read_text('utf8'));before=copy.deepcopy(real)
 m.supply_plan=lambda:[];m.quality_pools=lambda:{};m.rare_stock(real,__import__('time').time())
 check({k:v for k,v in real.items() if k!='market_simulation'}=={k:v for k,v in before.items() if k!='market_simulation'},'Lifetime migration preserves real player state projection in copied fixture')
(P/'regression.json').write_text(json.dumps(dict(status='PASS',checks=len(checks),details=checks,real_state_written=False),indent=2),'utf8');print('PASS',len(checks))
