"""Read-only production DB + synthetic in-memory state, no real writes/listeners."""
from pathlib import Path
from types import SimpleNamespace
from contextlib import closing
import sys,copy,json,sqlite3,threading,time,math
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
import market_simulation as m
from npc_exchange import AGENTS,INITIAL_WALLET,MAX_ASSETS,TRADE_PER_TICK
clock=[1800000000.];m.now=lambda:clock[0]
data=json.loads((R/'historical-data.json').read_text('utf8'));selected=data[:180]+data[-20:];ids=tuple(dict.fromkeys(r['spid'] for r in selected));ratings={r['spid']:r['ovr'] for r in selected}
state={'coaches':[{'slot':0,'ep':10**15}],'teams':{'0':{'players':[]}},'offers':[]};writes=[]
def save(st):state.clear();state.update(copy.deepcopy(st));writes.append(1)
def add(team,s,g):
 p={'_id':str(len(team['players'])),'spid':s,'grade':g};team['players'].append(p);return p
h=SimpleNamespace(HERE='D:/FO3ID/server',NPC_VALUE_MODEL_PATH=str(R/'attributes-value-model.json'),STATE_LOCK=threading.RLock(),player_value_price=lambda s,g:0 if g<=0 else 10000*(g+1)**3,card_ovr=lambda s:ratings[s],card_ovrs=lambda cards:{s:ratings[s] for s in cards},GRADE_BOOST={1:5},MAX_GRADE=20,MAX_PLAYERS=1000,_default_slot=lambda s:0,_state=lambda:copy.deepcopy(state),_save=save,closing=closing,_db=lambda:sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True),market_spids=lambda:set(ids),on_market=lambda s:s in ids,LINES={},_json=lambda d:(200,json.dumps(d).encode()),coach_me=lambda st,slot:{'money':{'ep':st['coaches'][slot]['ep']}},add_ep=lambda st,n:st['coaches'][0].update(ep=st['coaches'][0]['ep']+n),add_player=add,coach_me_resources=lambda st,slot:[])
e=m.Market(h);e._candidates=ids;checks=[]
def passed(x):checks.append(x);print('PASS',x,flush=True)
e.tick();world=state['market_simulation']['npc_exchange'];assert world['source_buys']>0 and world['peer_trades']==0
human_before=copy.deepcopy(state['coaches']);team_before=copy.deepcopy(state['teams'])
for i in range(1,161):
 clock[0]+=15;e.tick()
 w=state['market_simulation']['npc_exchange']
 assert sum(a['wallet'] for a in w['agents'])+w['supplier_wallet']+w['fees']==AGENTS*INITIAL_WALLET
 assert len(w['assets'])==w['source_buys']-w['human_buys']<=MAX_ASSETS
 assert all(a['wallet']>=0 for a in w['agents'])
assert w['peer_trades']>100 and len(state['market_simulation']['sales'])>0
assert all(t['buyer']!=t['seller'] for t in w['history'] if t['kind']=='npc_peer')
assert state['coaches']==human_before and state['teams']==team_before
passed('40 simulated minutes: funded distinct-owner peer trades, finite inventory, exact EP conservation, no human asset mutation')
quotes=state['market_simulation']['quotes'];assert any(abs(q['factor']-1)>1e-8 for q in quotes.values())
assert all(.6<=q['factor']<=1.6 and q['movement']<=.0200000001 for q in quotes.values())
passed('Completed NPC trades trigger bounded price changes after the existing volume/time gate')
before=copy.deepcopy(state);e.tick();assert state==before
restarted=m.Market(h);restarted._candidates=ids;restarted.tick();assert state==before
passed('Same time, restart and repeated tick cannot create extra trades or refill stock')
clock[0]+=86400;previous=w['peer_trades'];e.tick();w=state['market_simulation']['npc_exchange'];assert w['peer_trades']-previous<=TRADE_PER_TICK
passed('One-day offline gap produces no catch-up transaction burst')
# Await a published offer with a price distinct from source stock.
for _ in range(6):
 clock[0]+=15;e.tick()
 offers=e.exchange.listings(state,clock[0])
 candidate=next((r for r in offers if not any(x['grade']==r['grade'] and x['price']==r['price'] for x in e.book(state,r['spid'],clock[0])['rows'])),None)
 if candidate:break
assert candidate
lot=candidate['_market_npc_lot'];before_ep=state['coaches'][0]['ep'];before_human=w['human_buys']
res=json.loads(e.purchase(str(candidate['spid']),str(candidate['grade']),str(candidate['price']),'',b'{}')[1]);assert res['result'],res
w=state['market_simulation']['npc_exchange'];assert lot not in w['assets'] and w['human_buys']==before_human+1
assert state['coaches'][0]['ep']==before_ep-candidate['price'] and len(state['teams']['0']['players'])==1
assert sum(a['wallet'] for a in w['agents'])+w['supplier_wallet']+w['fees']==AGENTS*INITIAL_WALLET+candidate['price']
passed('Native purchase of an NPC-owned listing transfers one lot, exact player EP and seller proceeds in one state transaction')
sid=ids[0];base=e.exchange.base_value(sid)
assert e.exchange.reference_value(sid,1)==base and e.exchange.reference_value(sid,0)==0
for g in (2,8,13,20):assert e.exchange.reference_value(sid,g)==base*h.player_value_price(sid,g)//h.player_value_price(sid,1)
passed('Attribute-only +1 value composes exactly with the independent external enhancement multiplier; +0 stays zero')
# Failed persistence must not consume live in-memory fixture inventory or EP.
original_save=h._save
snapshot=copy.deepcopy(state)
clock[0]+=15
def fail_save(st):raise OSError('injected save failure')
h._save=fail_save
try:
 e.tick()
 raise AssertionError('Save failure was hidden')
except OSError:pass
assert state==snapshot
h._save=original_save
e.tick();assert state['market_simulation']['npc_exchange']['last_step']==int(clock[0]//15)
passed('Failed transaction persists no cards/wallet changes; retry commits the step once')
R.joinpath('peer-tests.json').write_text(json.dumps(dict(passed=True,checks=checks,peer_trades=w['peer_trades'],quotes_changed=sum(abs(q['factor']-1)>1e-8 for q in quotes.values()),assets=len(w['assets']),recent=w['history'][-10:]),indent=2),'utf8')
