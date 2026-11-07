"""Real Market handlers with detached synthetic state, injectable clock and save failures."""
from pathlib import Path
from types import SimpleNamespace
import copy,sys,json,threading,importlib.util,concurrent.futures
W=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');sys.path.insert(0,str(S))
spec=importlib.util.spec_from_file_location('market_under_test',W/'market_simulation.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
clock=[1800000000.];mod.now=lambda:clock[0];checks=[]
def check(ok,name):
 assert ok,name
 checks.append(name)
def fixture():
 st={'coaches':[{'slot':0,'ep':123,'_market_owner':'owner'}], 'teams':{'0':{'players':[]}},'offers':[],
     'market_simulation':{'buyers':{},'sales':[],'quotes':{}}}
 writes=[];h=SimpleNamespace(STATE_LOCK=threading.RLock(),_default_slot=lambda s:0,_state=lambda:copy.deepcopy(st),_json=lambda d:d,
  NO_BOOST={'igr':0,'vip':0},SALE_FEE=.3,MAX_PLAYERS=1000,MAX_GRADE=20,iid=lambda p:p['_id'],grade_of=lambda p:p['grade'],
  is_starter=lambda t,p:p.get('starter',False),remove_player=lambda t,p:t['players'].remove(p),coach_me_resources=lambda s,n:[],
  add_ep=lambda s,n:s['coaches'][0].update(ep=s['coaches'][0]['ep']+n),sale_net=lambda o:o['price']-o['completefee']['base'])
 def save(s):writes.append(copy.deepcopy(s));st.clear();st.update(copy.deepcopy(s))
 h._save=save
 e=mod.Market.__new__(mod.Market);e.h=h;e.quote=lambda *a:1000;e.valid_card=lambda *a:True
 e.prepare=lambda s:(s['market_simulation'],'owner',s['teams']['0'],0)
 e.exchange=SimpleNamespace(reference_value=lambda *a:1000,price_store=SimpleNamespace(fair=SimpleNamespace(stage_trade=lambda *a:None)))
 return e,st,writes
def player(i='card',grade=20,**extra):return dict(_id=i,spid=93001075,grade=grade,levelinfo={'level':17,'exp':12345},team2=2,jersey=9,**extra)
def offer(e,st,price=1000,i='card'):
 st['teams']['0']['players'].append(player(i));r=e.offer('',json.dumps({'playerobjectid':i,'price':price}).encode());assert r['result'],r;return st['offers'][-1]['_id']
def reprice(e,i,price):return e.recreate(i,'',json.dumps({'price':price}).encode())

e,st,w=fixture();oid=offer(e,st);card=copy.deepcopy(st['offers'][0]['_market_player']);old=copy.deepcopy(st)
wire=e.listing(st)['offers'][0]
check(wire['status']=='waiting' and st['offers'][0]['status']=='selling','Native waiting wire status exposes original change-price/cancel buttons without modifying stored status')
check(not any(k.startswith('_market_') for k in wire),'Private escrow/seed never leaks through native resource list')
seed=card['_market_sale_seed'];check(reprice(e,oid,800)['result'],'Reprice still-selling native offer succeeds')
o=st['offers'][0];check(o['_id']==oid and o['price']==800 and o['completefee']['base']==240 and st['coaches'][0]['ep']==123,'Reprice preserves offer ID and wallet, recalculates fee without moving the card')
check(all(o['_market_player'][k]==card[k] for k in ('_id','spid','grade','levelinfo','team2','jersey')) and o['_market_player']['_market_sale_seed']==seed,'Reprice preserves exact instance/XP/jersey/team and anti-reroll seed')
due=o['_market_due'];clock[0]+=1;before=copy.deepcopy(st);count=len(w)
check(reprice(e,oid,800)['result'] and st==before and len(w)==count,'Identical retry is idempotent and never postpones the buyer')
for bad in (0,-1,499,2501,True,1.5,'oops'):
 before=copy.deepcopy(st);check(not reprice(e,oid,bad)['result'] and st==before,'Reject malformed/out-of-band reprice '+str(bad))
st['coaches'][0]['_market_owner']='other';before=copy.deepcopy(st)
check(not reprice(e,oid,900)['result'] and not e.cancel('waiting',oid,'',b'{}')['result'] and st==before,'Other manager cannot reprice or cancel escrow')
st['coaches'][0]['_market_owner']='owner'
current_card=copy.deepcopy(st['offers'][0]['_market_player'])
check(e.cancel('waiting',oid,'',b'{}')['result'] and len(st['teams']['0']['players'])==1 and not st['offers'],'Native waiting cancel returns exactly one complete player')
check(st['teams']['0']['players'][0]==current_card and not e.cancel('waiting',oid,'',b'{}')['result'],'Cancel replay cannot duplicate cards')

for price,lo,hi in ((500,60,180),(800,180,600),(1000,600,1800)):
 for quantile in (.00001,.2,.99999):
  e,st,w=fixture();e.unit=lambda seed:quantile;oid=offer(e,st,price);o=st['offers'][0]
  check(o['_market_guaranteed'] and lo-1e-6<=o['_market_due']-clock[0]<=hi+1e-6,f'Guaranteed buyer bounded at price {price}, quantile {quantile}')
  clock[0]=o['_market_due'];before_ep=st['coaches'][0]['ep'];r=e.collect(oid,None,'',b'{}')
  check(r['result'] and r['ep']==price-int(price*.3) and st['coaches'][0]['ep']==before_ep+r['ep'],'Bounded sale pays exact after-tax amount once')
  after=copy.deepcopy(st);check(not e.collect(oid,None,'',b'{}')['result'] and st==after,'Collection replay never repeats payout')

e,st,w=fixture()
for i in range(30):offer(e,st,1000,str(i))
clock[0]+=1801;e.settle(st,clock[0])
check(all(o['status']=='sold' for o in st['offers']) and len(st['market_simulation']['sales'])==30,'Thirty same-player +20 listings sell despite legacy daily quota of two')
check(st['coaches'][0]['ep']==123,'Background settlement marks claims without auto-crediting wallet')
e.settle(st,clock[0]);check(len(st['market_simulation']['sales'])==30,'Repeated settlement never records a second sale')
with concurrent.futures.ThreadPoolExecutor(8) as pool:results=list(pool.map(lambda _:e.collect('all',None,'',b'{}'),range(8)))
check(sum(r['result'] for r in results)==1 and st['coaches'][0]['ep']==123+30*700,'Concurrent collect-all credits all claims exactly once')

e,st,w=fixture();oid=offer(e,st,2000);o=st['offers'][0];o['_market_due']=clock[0]+1;clock[0]+=2
r=reprice(e,oid,500)
check(not r['result'] and st['offers'][0]['status']=='sold' and st['offers'][0]['price']==2000,'Already-due settlement wins race against cheaper repricing')
check(not e.cancel('waiting',oid,'',b'{}')['result'] and not st['teams']['0']['players'],'Sold claim cannot be cancelled back into a card')
check(e.collect(oid,None,'',b'{}')['ep']==1400,'Race preserves original earned price and fee')

e,st,w=fixture();oid=offer(e,st,1000);o=st['offers'][0];o['_market_sale_policy']=1;o['_market_due']=o['_market_expires'];o['_market_listed']=clock[0]-4000
o['completefee']['base']=275
st['market_simulation']['buyers'][f'{o["spid"]}:high']={'day':int((clock[0]+7*3600)//86400),'count':100}
e.settle(st,clock[0]);check(o['status']=='sold' and o['price']==1000 and o['completefee']['base']==275,'Existing missed fair-price listing migrates to bounded demand, retaining agreed price and fee')

e,st,w=fixture();oid=offer(e,st,1000);o=st['offers'][0];o['_market_sale_policy']=1;o['_market_due']=o['_market_expires'];clock[0]=o['_market_expires']+1;e.settle(st,clock[0])
check(o['status']=='expired','Already-expired old listing is not silently resurrected')
check(reprice(e,oid,800)['result'] and st['offers'][0]['status']=='selling','Explicit expired-offer relisting remains compatible')

e,st,w=fixture();st['teams']['0']['players'].append(player(_market_origin={'at':clock[0],'basis':900,'paid':900}));r=e.offer('',b'{"playerobjectid":"card","price":500}');o=st['offers'][0]
check(r['result'] and o['_market_due']>=clock[0]+mod.NPC_HOLD_SECONDS,'NPC-purchased/derived cards retain anti-arbitrage hold')

e,st,w=fixture();e.unit=lambda seed:.000001;oid=offer(e,st,2500);o=st['offers'][0]
check(not o['_market_guaranteed'] and o['_market_due']>=o['_market_expires'],'Inflated price is not converted into unconditional buyout')
check(reprice(e,oid,1000)['result'] and st['offers'][0]['_market_guaranteed'],'Reducing an unsellable expensive listing to fair price activates bounded buyer')

e,st,w=fixture();oid=offer(e,st,2000);o=st['offers'][0];clock[0]=o['_market_expires']-30
check(reprice(e,oid,800)['result'] and st['offers'][0]['_market_due']<st['offers'][0]['_market_expires'],'Last-minute reduction still guarantees a buyer before original expiry')
clock[0]=st['offers'][0]['_market_due'];check(e.collect(oid,None,'',b'{}')['result'],'Last-minute buyer can settle and collect normally')
e,st,w=fixture();oid=offer(e,st,2000);o=st['offers'][0];o['_market_sale_policy']=1;o['_market_due']=clock[0]-1
e.settle(st,clock[0]);check(o['status']=='sold','Existing already-due expensive sale is not postponed by migration')

e,st,w=fixture();oid=offer(e,st,2000);o=st['offers'][0];o['_market_due']=clock[0]+1
day=int((clock[0]+7*3600)//86400);st['market_simulation']['buyers'][f'{o["spid"]}:high']={'day':day,'count':2}
clock[0]+=2;e.settle(st,clock[0]);check(o['status']=='selling' and o['_market_due']==o['_market_expires'],'High asking prices retain finite-demand protection')

e,st,w=fixture();oid=offer(e,st,1000);before=copy.deepcopy(st)
def failed_save(s):raise OSError('injected atomic-save failure')
e.h._save=failed_save
try:reprice(e,oid,700);raise AssertionError('missing failure')
except OSError:pass
check(st==before,'Failed reprice save cannot mutate live escrow, deadline, card or wallet')
clock[0]=st['offers'][0]['_market_due']+1
try:e.collect(oid,None,'',b'{}');raise AssertionError('missing failure')
except OSError:pass
check(st==before,'Failed sale/collect save cannot lose a claim or credit unsaved proceeds')
for flags in ({'locked':True},{'lock':True},{'starter':True}):
 e,st,w=fixture();st['teams']['0']['players'].append(player(**flags));before=copy.deepcopy(st)
 check(not e.offer('',b'{"playerobjectid":"card","price":1000}')['result'] and st==before,'Original locked/starter protection remains '+str(flags))

report={'status':'PASS','count':len(checks),'checks':checks,'real_state_written':False,'listeners_started':False}
(W/'regression.json').write_text(json.dumps(report,indent=2),'utf8');print('PASS',len(checks))
