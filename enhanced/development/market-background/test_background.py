"""Exercise the installed Market with synthetic in-memory state; no real state writes."""
from pathlib import Path
from types import SimpleNamespace
from contextlib import closing
import importlib.util,copy,threading,sqlite3,time,json,logging
p=Path('D:/FO3ID/server/market_simulation.py');spec=importlib.util.spec_from_file_location('market',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
clock=[1800000000.];m.now=lambda:clock[0]
state={'coaches':[{'slot':0,'ep':100}],'teams':{'0':{'players':[]}},'offers':[]};writes=[]
def db():
 c=sqlite3.connect(':memory:');c.execute('create table players(spid integer)');c.executemany('insert into players values(?)',[(x,) for x in range(1,101)]);return c
def save(st):
 state.clear();state.update(copy.deepcopy(st));writes.append(copy.deepcopy(st))
h=SimpleNamespace(STATE_LOCK=threading.RLock(),player_value_price=lambda s,g:1000*g,card_ovr=lambda s:70,GRADE_BOOST={1:0},MAX_GRADE=20,_default_slot=lambda s:0,_state=lambda:copy.deepcopy(state),_save=save,closing=closing,_db=db,market_spids=lambda:set(range(1,101)),card_ovrs=lambda cards:{s:70 for s in cards},on_market=lambda s:s in range(1,101))
e=m.Market(h);checks=[]
def passed(label):checks.append(label);print('PASS',label,flush=True)
assert e.tick();assert state['market_simulation']['books'] and state['market_simulation']['rare_books']
assert state['coaches'][0]['ep']==100 and state['teams']['0']['players']==[]
passed('No HTTP request needed to create scheduled NPC supply; wallet and team preserved')
book=next(iter(state['market_simulation']['books'].values()));row=next(r for r in book['rows'] if r['grade']==1);row['count']=0
snapshot=copy.deepcopy(state);assert not e.tick();assert state==snapshot
passed('Background tick does not refill consumed stock in the current epoch')
owner=state['coaches'][0]['_market_owner']
offer={'_id':'sale-1','spid':1,'grade':1,'price':1000,'status':'selling','_market_due':clock[0]-1,'_market_expires':clock[0]+3600,'_market_owner':owner,'_market_player':{}}
state['offers']=[offer]
threads=[threading.Thread(target=e.tick) for _ in range(4)]
for t in threads:t.start()
for t in threads:t.join()
assert state['offers'][0]['status']=='sold' and len(state['market_simulation']['sales'])==1
assert state['coaches'][0]['ep']==100
assert not e.tick();assert len(state['market_simulation']['sales'])==1
passed('Concurrent background ticks settle once; proceeds await explicit collection')
clock[0]+=901;e.tick();assert all(b['epoch']==int(clock[0]//900) for b in state['market_simulation']['books'].values())
passed('Regular books rotate on schedule without a market page request')
# Three actual eligible sales separated by >=30 minutes cause a bounded price rise.
for i in range(3):
 e.record(state,dict(_id='price-'+str(i),spid=2,grade=1,price=2000,_market_owner=owner,_market_player={}),clock[0]+i*901)
assert 1<state['market_simulation']['quotes']['2']['factor']<=1.005
passed('Actual high-price sales raise the quote after volume/time gate')
# Keep all intentionally failing saves in memory; worker logs the fault and retries.
m.BACKGROUND_SECONDS=.02
original=e.tick;attempts=[0]
def intermittent():
 attempts[0]+=1
 if attempts[0]==1:raise OSError('injected persistence failure')
 return original()
e.tick=intermittent
logging.getLogger('market').addHandler(logging.NullHandler());logging.getLogger('market').propagate=False
assert e.start_background();assert not e.start_background()
deadline=time.monotonic()+2
while e._worker_status['ticks']<2 and time.monotonic()<deadline:time.sleep(.01)
e.stop_background()
assert e._worker_status['ticks']>=2 and e._worker_status['errors']==1 and not e._worker.is_alive()
passed('Worker is singleton, retries visible failures, and stops cleanly')
state['coaches']=[];before=len(writes);assert not original();assert len(writes)==before
passed('No-manager startup never creates a synthetic account')
Path('D:/fifaol3/market-background/unit-result.json').write_text(json.dumps(dict(passed=True,checks=checks),indent=2),'utf8')
