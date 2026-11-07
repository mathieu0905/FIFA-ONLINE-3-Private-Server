from pathlib import Path
import copy,json,sys,types,urllib.request,time
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');sys.path[:0]=[str(P),str(S)]
from market_simulation import Market
m=Market.__new__(Market);m.h=types.SimpleNamespace(MAX_GRADE=20);m.unit=lambda seed:.01
checks=[]
def check(ok,name):
 assert ok,name
 checks.append(name)
def sample():
 sold=dict(spid=93001075,grade=15,count=0,price=999,_market_release=0,_market_expires=700)
 return {'epoch':0,'start':0,'period':700,'slots':1,'pool_size':54,'chance':.8,'rows':[sold]}
tier=dict(key='elite_15',quality='elite',pool_size=430,expected_per_day=7*86400/700,grades=(15,))
st={'market_simulation':{'seed':'fixture'}};cards=(93001075,84037576,30037576);b=sample();old=copy.deepcopy(b['rows']);m.expand_rare_batch(st,tier,b,cards,80)
check(b['slots']==7 and len(b['rows'])==7,'Expanding old 54-card pool adds six future slots')
check(b['rows'][:1]==old,'Consumed quantity and historical price preserved')
check(all(r['_market_release']>80 and r['_market_expires']<=700 for r in b['rows'][1:]),'Only future windows within original batch lifetime')
check(all(r['spid']//1000000!=84 for r in b['rows'][1:]),'IM cap preserved in new high-grade slots')
check(all(r['price'] is None for r in b['rows'][1:]),'Future prices remain unfrozen until release')
once=copy.deepcopy(b);m.expand_rare_batch(st,tier,b,cards,81);check(b==once,'Repeated requests cannot reroll or refill')
m.expand_rare_batch(st,tier,b,cards,-100);check(b==once,'Clock rollback cannot reopen slots')
b=sample();m.expand_rare_batch(st,tier,b,cards,350);check(all(r['_market_release']>350 for r in b['rows'][1:]),'Offline missed slots are skipped without catch-up stock')
b=sample();b['rows'][0]['count']=1;before=copy.deepcopy(b['rows'][0]);m.expand_rare_batch(st,tier,b,cards,80);check(b['rows'][0]==before,'Visible offers retain count price and expiry')
smaller=dict(tier,pool_size=20);b=sample();before=copy.deepcopy(b);m.expand_rare_batch(st,smaller,b,cards,80);check(b==before,'Pool shrink does not destructively reschedule signed offers')
b=sample();m.unit=lambda seed:.9999;m.expand_rare_batch(st,dict(tier,expected_per_day=3.1*86400/700),b,cards,80);check(len(b['rows'])==1 and b['slots']==4,'Failed chance attempts are recorded and not retryable')
m.unit=lambda seed:.01;m.expand_rare_batch(st,dict(tier,expected_per_day=3.1*86400/700),b,cards,80);check(len(b['rows'])==1,'Changing request time cannot retry failed chance')
# Dry-run all persisted batches on an in-memory copy; no database/state write.
status=json.load(urllib.request.urlopen('http://127.0.0.1:8088/api/market_status',timeout=15));state=json.loads((S/'gamedata/state.json').read_text('utf8'));before=copy.deepcopy(state);stamp=time.time();report=[]
# Real deterministic hash for evidence. Fixture cards only verify scheduling, not player draws.
m.unit=Market.unit
for t in status['rare_world_limits']:
 batch=state['market_simulation']['rare_books'].get(t['key'])
 if not batch or stamp>=batch['start']+batch['period']:continue
 original=copy.deepcopy(batch['rows']);m.expand_rare_batch(state,t,batch,cards,stamp)
 check(batch['rows'][:len(original)]==original,'Real copied batch old rows unchanged: '+t['key'])
 if t['quality']=='elite' and t['grades'][0]>=15:
  report.append(dict(grade=t['grades'][0],old_slots=before['market_simulation']['rare_books'][t['key']]['slots'],new_slots=batch['slots'],future_added=len(batch['rows'])-len(original),next_possible_release=min((r['_market_release'] for r in batch['rows'][len(original):]),default=None)))
check({k:v for k,v in state.items() if k!='market_simulation'}=={k:v for k,v in before.items() if k!='market_simulation'},'Real player state projection unchanged in dry run')
(P/'regression.json').write_text(json.dumps(dict(status='PASS',checks=len(checks),details=checks,dry_run_schedule=report,draws_use_fixture_cards=True,real_state_written=False),ensure_ascii=False,indent=2),'utf8')
print(json.dumps(dict(status='PASS',checks=len(checks),dry_run_schedule=report),ensure_ascii=False))
