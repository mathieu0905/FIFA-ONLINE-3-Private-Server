from pathlib import Path
import copy,json,sys,types
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');sys.path[:0]=[str(P),str(S)]
import market_simulation as mod
import npc_exchange as npc
M=mod.Market;m=M.__new__(M);m.h=types.SimpleNamespace(MAX_GRADE=20)
checks=[]
def check(ok,name):
 assert ok,name
 checks.append(name)
check(all(m.npc_supply_allowed(84037576,g)==(g<=5) for g in range(1,21)),'IM exact +5 boundary')
check(all(m.npc_supply_allowed(30037576,g) for g in range(1,21)),'Other seasons unchanged')
st=json.loads((S/'gamedata/state.json').read_text('utf8'));before=copy.deepcopy(st)
m.exchange=types.SimpleNamespace(price_store=types.SimpleNamespace(applied=lambda e:False))
m.active=lambda state:({}, {}, 'fixture')
m.prepare(st)
for table in ('books','rare_books'):
 check(all(m.npc_supply_allowed(r['spid'],r['grade']) for b in st['market_simulation'][table].values() for r in b['rows']),table+' removes existing IM high supply')
check({k:v for k,v in st.items() if k!='market_simulation'}=={k:v for k,v in before.items() if k!='market_simulation'},'Real player state projection unchanged in copied state')
a=before['market_simulation']['npc_exchange']['assets'];b=st['market_simulation']['npc_exchange']['assets']
check({k:{f:v for f,v in x.items() if f!='listing'} for k,x in a.items()}=={k:{f:v for f,v in x.items() if f!='listing'} for k,x in b.items()},'NPC inventory retained; only high IM listings withdrawn')
m.quality=lambda s:'low';m.quote=lambda *args:100;m.unit=lambda seed:.000001
fresh={'market_simulation':{'seed':'test','books':{},'rare_books':{},'supply_started_at':0}}
check(max(r['grade'] for r in m.book(fresh,84037576,1000)['rows'])==5,'New regular IM stock capped')
check(max(r['grade'] for r in m.book(fresh,30037576,1000)['rows'])==10,'Other regular grades retained')
m.quality_pools=lambda:{'low':(84037576,)}
m.supply_plan=lambda:[dict(key='test',quality='low',grades=(10,),period=86400,slots=1,chance=1,pool_size=1)]
check(m.rare_stock(fresh,1000)==[],'Rare generator cannot bypass IM cap')
e=npc.NpcExchange.__new__(npc.NpcExchange);e.market=m
state={'market_simulation':{'npc_exchange':{'assets':{'x':dict(spid=84037576,grade=9,listing=dict(count=1)),'y':dict(spid=84037576,grade=5,listing=dict(count=1)),'z':dict(spid=30037576,grade=9,listing=dict(count=1))}}}}
check(len(e.listings(state,0))==2,'Existing NPC high IM listing hidden defensively')
m.featured_rows=lambda *a,**k:[];m.candidates=lambda:(84037576,);m.record=lambda *a:None
e._preference=lambda *a:1;e._burn=lambda *a:None;npc.TRADE_PER_TICK=0
state={'market_simulation':{'seed':'fixture'}}
for step in range(1,12):e.advance(state,step*15)
check(all(m.npc_supply_allowed(a['spid'],a['grade']) for a in state['market_simulation']['npc_exchange']['assets'].values()),'Fallback internal supply obeys cap')
world=e.world(state,180);world['assets']['high']=dict(spid=84037576,grade=10,quantity=1,owner=0,acquired_at=0)
e.advance(state,195)
check('listing' not in world['assets']['high'],'Existing high IM warehouse cannot republish')
(P/'test_cap.py.result.json').write_text(json.dumps(dict(status='PASS',checks=len(checks),details=checks,real_state_written=False),ensure_ascii=False,indent=2),'utf8')
print('PASS',len(checks))
