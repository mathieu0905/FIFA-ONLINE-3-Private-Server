"""Real HTTPS native-contract regression on a private server snapshot; never live POST."""
import copy,datetime,http.server,json,os,pathlib,shutil,ssl,sys,threading,urllib.request
from unittest.mock import patch

sys.dont_write_bytecode=True
WORK=pathlib.Path(__file__).resolve().parent
RUN=WORK/('run-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
ROOT=RUN/'server';ROOT.mkdir(parents=True)
SOURCE=pathlib.Path(r'D:\FO3ID\server')
for src in SOURCE.glob('*.py'):shutil.copyfile(src,ROOT/src.name)
for src in SOURCE.glob('*.json'):shutil.copyfile(src,ROOT/src.name)
for name in ['responses','tools','admin','certs','gamedata']:
 shutil.copytree(SOURCE/name,ROOT/name,ignore=shutil.ignore_patterns('__pycache__','*.log','*.before-*','*.before.*','state.json*'))
shutil.copyfile(WORK/'market_simulation.py',ROOT/'market_simulation.py')
writes=[];blocked=[]
def audit(event,values):
 if event!='open':return
 file,mode,flags=values
 if not isinstance(file,(str,bytes,os.PathLike)):return
 mut=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)))
 if not mut:return
 target=pathlib.Path(os.fsdecode(file)).resolve()
 if not target.is_relative_to(RUN):blocked.append(str(target));raise PermissionError('outside private snapshot: '+str(target))
 writes.append(str(target.relative_to(RUN)))
sys.addaudithook(audit)
os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi',FO3_GAME=r'D:\FO3ID\32795')
sys.path.insert(0,str(ROOT));sys.argv=['http_config.py']
import http_config as h,market_simulation as mod
engine=mod.install(h);assert pathlib.Path(h.STATE).resolve().is_relative_to(ROOT)
# Synthetic state constructed from the shipped team generator, no real manager data.
team=copy.deepcopy(h.roster_team(241))
coach={'_id':h.coach_id(0),'name':'Private market QA','slot':0,'teamid':241,'ep':10**16,'cash':500}
baseline={'coaches':[coach],'defaultcoachid':coach['_id'],'teams':{'0':team},'offers':[]}
# gen_team may have native ids; they are not a user's cards.
checks=[];clock=[1800000000.0];mod.now=lambda:clock[0]
def reset():
 st=copy.deepcopy(baseline);h._save(st);return st
def state():return h._state()
def save(st):h._save(st)
def active(st):return engine.active(st)
def raw():return pathlib.Path(h.STATE).read_bytes()
def passed(s):checks.append(s);print('PASS',s,flush=True)
reset()
ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(ROOT/'certs/server.pem'))
srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),h.H);srv.socket=ctx.wrap_socket(srv.socket,server_side=True)
threading.Thread(target=srv.serve_forever,daemon=True).start();base=f'https://127.0.0.1:{srv.server_address[1]}'
def request(path,obj=None,method=None):
 req=urllib.request.Request(base+path,data=None if obj is None else json.dumps(obj).encode(),method=method,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,context=ssl._create_unverified_context(),timeout=90) as r:return json.loads(r.read())
def fresh(grade=1,seed='stable-sale-seed',origin=False):
 st=state();c,t,slot=active(st);p=h.add_player(t,spid,grade);p.update(levelinfo={'level':9,'exp':237},lr={'11':{'id':7}},_market_sale_seed=seed)
 if origin:p['_market_origin']={'kind':'npc','paid':1,'at':clock[0]}
 save(st);return copy.deepcopy(p)
def listed(p,price=None):
 price=price or request(f'/transfer/price/{spid}/{h.grade_of(p)}')['default']
 out=request('/transfer/offer',{'playerobjectid':h.iid(p),'price':price});assert out['result'],out
 return state()['offers'][-1]
def ep(st):return active(st)[0]['ep']
try:
 spid=min(h.market_spids())
 anchor=h.card_price(spid,1)
 for g in [0,21,999]:
  before=raw();out=request(f'/transfer/purchase/{spid}/{g}/0/purchase',{});assert not out['result'] and raw()==before
  before=raw();out=request(f'/transfer/price/{spid}/{g}');assert not out['result'] and raw()==before
 before=raw();assert request('/transfer/search/999999999')==[] and raw()==before
 for bad in [True,1.5,'oops',None,[],{},0,-1]:
  before=raw();assert not request('/transfer/offer',{'price':bad,'playerobjectid':'bad'})['result'] and raw()==before
 passed('Unknown cards/grades, malformed body and invalid prices cause no state writes')
 # Native searches do local client SQL first, then these HTTP offers. No fake season query.
 with h.closing(h._db()) as db:
  existing={s for(s,) in db.execute('SELECT spid FROM players')}
 allmarket=h.market_spids();season_samples={}
 for s in sorted(allmarket & existing):season_samples.setdefault(s//1000000,s)
 assert 13 in season_samples
 for season,s in season_samples.items():
  rows=request(f'/transfer/search/{s}');assert rows and all(r['spid']==s and r['spid']//1000000==season and 1<=r['grade']<=20 and r['price']>0 and r['count']>0 for r in rows)
 passed(f'Real HTTPS one market card in every {len(season_samples)} available season, including FC13; exact SPID and valid prices/grades')
 # Querying is stable and global: manager switch cannot reroll or refill stock.
 rows=request(f'/transfer/search/{spid}');rows2=request(f'/transfer/search/{spid}');assert rows==rows2
 st=state();other=copy.deepcopy(st['coaches'][0]);other.update(_id=h.coach_id(1),slot=1,name='Second QA');other.pop('_market_owner',None)
 st['coaches'].append(other);st['teams']['1']=copy.deepcopy(st['teams']['0']);save(st)
 before_ep=ep(state());row=next(r for r in rows if r['grade']==1)
 before=raw();assert not request(f'/transfer/purchase/{spid}/1/{row["price"]+1}/purchase',{})['result'] and raw()==before
 for n in range(row['count']):
  before_count=len(active(state())[1]['players']);out=request(f'/transfer/purchase/{spid}/1/{row["price"]}/purchase',{});assert out['result']
  st=state();assert len(active(st)[1]['players'])==before_count+1
  bought=active(st)[1]['players'][-1];assert bought['_market_origin']['kind']=='npc' and bought['grade']==1
 assert ep(state())==before_ep-row['price']*row['count']
 before=raw();assert not request(f'/transfer/purchase/{spid}/1/{row["price"]}/purchase',{})['result'] and raw()==before
 st=state();st['defaultcoachid']=other['_id'];save(st);assert not any(r['grade']==1 for r in request(f'/transfer/search/{spid}'))
 assert request('/transfer/my/offer/list')['offers']==[]
 st=state();st['defaultcoachid']=baseline['defaultcoachid'];save(st)
 passed('Finite inventory: stable refresh, exact debit/full instances, stock exhaustion; manager switch cannot reroll/refill')
 # A global +20 opportunity exists in a future 84-day period, not per queried SPID.
 reset();request(f'/transfer/search/{spid}');st=state();seed=st['market_simulation']['seed'];epoch=int(clock[0]//900)
 tier=next(t for t in engine.supply_plan() if t['key']=='low_20')
 target=next(e for e in range(1,1000) if engine.unit(f'{seed}:rare:low_20:{e}:0:exists') < tier['chance'])
 release=engine.unit(f'{seed}:rare:low_20:{target}:0:release')*(tier['period']-900)
 clock[0]=st['market_simulation']['supply_started_at']+target*tier['period']+release+1
 featured=request('/transfer/top/50');high=next(r for r in featured if r['grade']==20);highspid=high['spid']
 assert high['count']==1 and request(f'/transfer/purchase/{highspid}/20/{high["price"]}/purchase',{})['result']
 before=raw();assert not request(f'/transfer/purchase/{highspid}/20/{high["price"]}/purchase',{})['result'] and raw()==before
 assert not any(r['grade']==20 for r in request(f'/transfer/search/{highspid}'))
 assert not any(r['grade']==20 for r in request('/transfer/top/50'))
 clock[0]+=900;assert next(r for r in request(f'/transfer/search/{spid}') if r['grade']==1)['count']==12
 assert not any(r['grade']==20 for r in request('/transfer/top/50'))
 passed('Whole-world rare +20 opportunity is discoverable, bought once, and never refilled by low-grade refresh or another SPID')
 # Persist original card fields under escrow; listing is not an immediate NPC purchase.
 reset();p=fresh(11);old_ep=ep(state());offer=listed(p)
 assert offer['status']=='selling' and ep(state())==old_ep
 assert not any(h.iid(v)==h.iid(p) for v in active(state())[1]['players'])
 view=request('/transfer/my/offer/list');assert view['offers'][0]['status']=='selling' and not any(k.startswith('_market_') for k in view['offers'][0])
 before=raw();assert not request(f'/transfer/my/offer/completed/{offer["_id"]}',{},method='DELETE')['result'] and raw()==before
 assert request(f'/transfer/my/offer/selling/{offer["_id"]}',{},method='DELETE')['result']
 returned=next(v for v in active(state())[1]['players'] if h.iid(v)==h.iid(p));assert all(returned[k]==v for k,v in p.items()) and ep(state())==old_ep
 before=raw();assert not request(f'/transfer/my/offer/selling/{offer["_id"]}',{},method='DELETE')['result'] and raw()==before
 # Same seed => same wait, cancelling and listing never rerolls the lottery.
 again=listed(p);assert again['_market_due']-again['_market_listed']==offer['_market_due']-offer['_market_listed']
 clock[0]=again['_market_due']+1;view=request('/transfer/my/offer/list');assert view['offers'][0]['status']=='sold'
 assert ep(state())==old_ep
 out=request(f'/transfer/my/offer/completed/{again["_id"]}',{},method='DELETE');assert out['result'] and ep(state())==old_ep+h.sale_net(again)
 before=raw();assert not request(f'/transfer/my/offer/completed/{again["_id"]}',{},method='DELETE')['result'] and raw()==before
 passed('Selling/escrow/cancel preserves exact instance and XP; deterministic wait; delayed sale then exact once-only EP claim')
 # Higher than value prices have the same seed but longer wait. Expiry and native relisting.
 reset();p=fresh();q=request(f'/transfer/price/{spid}/1')['default'];o=listed(p,q*2)
 assert o['_market_due']-o['_market_listed'] >= 86400
 clock[0]=o['_market_expires']+1;assert request('/transfer/my/offer/list')['offers'][0]['status']=='expired'
 before=raw();assert not request(f'/transfer/offer/from/{o["_id"]}',{'price':q*3})['result'] and raw()==before
 assert request(f'/transfer/offer/from/{o["_id"]}',{'price':q})['result']
 new=state()['offers'][0];assert all(new['_market_player'][k]==v for k,v in o['_market_player'].items() if not k.startswith('_market_trial_')) and new['status']=='selling' and new['_id']==o['_id']
 before=raw();assert not request(f'/transfer/offer/from/{o["_id"]}',{'price':q})['result'] and raw()==before
 passed('Overpriced listing waits longer, expires, and native expired-offer relisting preserves escrow/provenance without reroll')
 # Ownership follows manager lifetime, not a reusable numeric slot or deterministic coach id.
 reset();p=fresh();o=listed(p);st=state();other=copy.deepcopy(st['coaches'][0]);other.update(_id=h.coach_id(1),slot=1);other.pop('_market_owner',None)
 st['coaches'].append(other);st['teams']['1']=copy.deepcopy(st['teams']['0']);st['defaultcoachid']=other['_id'];save(st)
 assert request('/transfer/my/offer/list')['offers']==[]
 for uri,body,method in [(f'/transfer/my/offer/selling/{o["_id"]}',{},'DELETE'),(f'/transfer/my/offer/completed/{o["_id"]}',{},'DELETE'),(f'/transfer/offer/from/{o["_id"]}',{'price':q},'POST')]:
  before=raw();assert not request(uri,body,method)['result'] and raw()==before
 st=state();st['defaultcoachid']=baseline['defaultcoachid'];st['coaches'][0].pop('_market_owner');save(st)
 assert request('/transfer/my/offer/list')['offers']==[]
 passed('Cross-manager cancellation/relisting/claim rejected; reused coach id/slot cannot inherit old escrow')
 # Stable anchors and package weights must never follow dynamic quotes.
 reset();st=state();engine.prepare(st);st['market_simulation']['quotes'][str(spid)]={'factor':1.5,'day':int(clock[0]//86400),'movement':0.,'pending':[]};save(st)
 assert h.card_price(spid)==anchor and h.market_reference_price(spid)==anchor
 assert request(f'/transfer/price/{spid}/1')['default']==int(anchor*1.5)
 # Actual signed-off completed transactions only: seeds/clock create deterministic executions.
 reset();factor_history=[]
 for index in range(12):
  seed=next(f'eligible-{index}-{n}' for n in range(10000) if engine.unit(f'eligible-{index}-{n}:attempt:0')>.999)
  p=fresh(seed=seed,origin=index<3)
  q=request(f'/transfer/price/{spid}/1')['default'];o=listed(p,int(q*1.2));clock[0]=max(clock[0]+1801,o['_market_due']+1)
  request('/transfer/my/offer/list');st=state();quote=st['market_simulation']['quotes'].get(str(spid),{});factor_history.append(quote.get('factor',1.))
  assert request(f'/transfer/my/offer/completed/{o["_id"]}',{},method='DELETE')['result']
 assert factor_history[:3]==[1.,1.,1.] and factor_history[3:5]==[1.,1.]
 assert factor_history[-1]>1. and factor_history[-1]<=1.02+1e-9
 assert h.card_price(spid)==anchor
 passed('Only actual organic sales move quote after volume/time gate; NPC resales never pump; reference anchor stays unchanged')
 # Materials cannot wash market origin into an untagged target through enhancement.
 reset();p=fresh(grade=1);material=fresh(grade=1,origin=True);before_n=len(active(state())[1]['players'])
 with patch.object(h.random,'random',return_value=0):
  out=request(f'/player/{h.iid(p)}/enhance/{h.iid(material)}',{},method='PUT')
 assert out['result'];st=state();kept=next(v for v in active(st)[1]['players'] if h.iid(v)==h.iid(p))
 assert kept['_market_origin']['kind']=='npc-derived' and len(active(st)[1]['players'])==before_n-1
 passed('NPC material provenance propagates across native enhancement into surviving target')
 # Cumulative 24h chance, not a high per-refresh chance accidentally compounded.
 reset();probability_results={}
 for ratio,target in ((.8,.92),(1.,.55),(1.1,.18),(1.3,.03),(1.6,.003)):
  observed=0;n=20000;st=state();q=engine.quote(spid,1,st)
  lower,upper={.8:(900,3600),1.:(3600,14400),1.1:(14400,43200),1.3:(28800,86340),1.6:(43200,86340)}[ratio]
  filled_waits=[]
  for i in range(n):
   offer={'spid':spid,'grade':1,'_market_player':{'_market_sale_seed':f'cdf-{i}'}}
   engine.schedule(st,offer,round(q*ratio),clock[0])
   hit=offer['_market_due']<offer['_market_expires'];observed+=hit
   if hit:
    wait=offer['_market_due']-clock[0];assert lower-1e-5<=wait<=upper+1e-5
    filled_waits.append(wait)
  fraction=observed/n;assert abs(fraction-target)<.012,(ratio,fraction,target)
  probability_results[str(ratio)]={'target24h':target,'observed':fraction,'samples':n,'conditional_wait_min':min(filled_waits),'conditional_wait_max':max(filled_waits)}
 passed('100000 deterministic buyer trials match full-24h probabilities and approved fast-clear conditional time ranges; polling never redraws a miss')
 # Lucky profitable speculation is allowed only after the real hold; never an instant loop.
 reset();row=next(r for r in request(f'/transfer/search/{spid}') if r['grade']==1)
 paid=row['price'];assert request(f'/transfer/purchase/{spid}/1/{paid}/purchase',{})['result']
 st=state();bought=active(st)[1]['players'][-1];bought['_market_sale_seed']=next(f'hold-{i}' for i in range(100000) if engine.unit(f'hold-{i}:attempt:0')>.9999);save(st)
 original_time=clock[0];o=listed(bought,int(paid*1.1));assert o['_market_due']>=original_time+3600
 clock[0]=original_time+3599;assert request('/transfer/my/offer/list')['offers'][0]['status']=='selling'
 before=raw();assert not request(f'/transfer/my/offer/completed/{o["_id"]}',{},method='DELETE')['result'] and raw()==before
 clock[0]=o['_market_due']+1;assert request('/transfer/my/offer/list')['offers'][0]['status']=='sold'
 assert request(f'/transfer/my/offer/completed/{o["_id"]}',{},method='DELETE')['result']
 assert not state()['market_simulation']['quotes']
 passed('NPC instant resale cannot settle inside one hour; a lucky later speculative profit remains possible without moving quote')
 # Both NPC inputs carry the latest purchase time and combined basis after upgrading.
 reset();old=fresh(origin=True);clock[0]+=7200;new=fresh(origin=True);before=state();a=next(p for p in active(before)[1]['players'] if h.iid(p)==h.iid(old));b=next(p for p in active(before)[1]['players'] if h.iid(p)==h.iid(new));basis=engine.basis(a)+engine.basis(b)
 with patch.object(h.random,'random',return_value=0):out=request(f'/player/{h.iid(old)}/enhance/{h.iid(new)}',{},method='PUT')
 assert out['result'];kept=next(p for p in active(state())[1]['players'] if h.iid(p)==h.iid(old))
 assert kept['_market_origin']['at']==new['_market_origin']['at'] and kept['_market_origin']['basis']==basis
 assert '_market_merge_snapshot' not in kept
 passed('Enhancement combines latest NPC purchase time and pre-grade-change cost basis without washing origin')
 # Every real Tukar contract route shares held-input and one-commit provenance rules.
 for version in (1,2,3):
  reset();row=next(r for r in request(f'/transfer/search/{spid}') if r['grade']==1)
  for _ in range(4):assert request(f'/transfer/purchase/{spid}/1/{row["price"]}/purchase',{})['result']
  cards=active(state())[1]['players'][-4:];ids=[h.iid(p) for p in cards];budget=sum(engine.basis(p) for p in cards)
  if version==3:
   uri='/trade3/proposal';payload={'id':'default_B01','slotnum':0,'playerids':[{'id':h.iid(p),'spid':spid,'grade':1,'price':h.card_price(spid,1)} for p in cards]};contract='/trade3/contract'
  else:uri=f'/players/trade{2 if version==2 else ""}/proposal';payload={'players':ids};contract=f'/players/trade{2 if version==2 else ""}/contract'
  proposal=request(uri,payload);assert proposal['result'],proposal
  assert all(int(p.get('ep',0))<=budget for p in proposal['props'])
  again=request(uri,payload);assert again['result'] and again['props']==proposal['props']
  chosen=next(i for i,p in enumerate(proposal['props']) if 'spid' in p)
  before=raw();assert not request(contract,{'select':chosen,'selectnum':chosen})['result'] and raw()==before
  clock[0]+=3600
  # A disk failure commits neither ingredient removal nor the replacement/cash.
  real_save=h._save
  with patch.object(h,'_save',side_effect=OSError('injected commit failure')):
   assert not request(contract,{'select':chosen,'selectnum':chosen})['result']
  assert raw()==before
  assert request(contract,{'select':chosen,'selectnum':chosen})['result']
  replacement=active(state())[1]['players'][-1]
  assert replacement['_market_origin']['kind']=='npc-derived' and replacement['_market_origin']['at']==cards[-1]['_market_origin']['at']
  assert replacement['_market_origin']['basis']==budget-int(proposal['props'][chosen].get('ep',0))
  assert all(not any(h.iid(p)==pid for p in active(state())[1]['players']) for pid in ids)
  before=raw();assert not request(contract,{'select':chosen,'selectnum':chosen})['result'] and raw()==before
 passed('Tukar v1/v2/v3 preserve permanent origin, one-hour holds, fixed material rolls, advertised EP caps and single-commit replacements')
 # Same ids with a changed grade cannot redeem an old price, or another manager's proposal.
 reset();cards=[fresh(),fresh()];ids=[h.iid(p) for p in cards];payload={'players':ids}
 assert request('/players/trade/proposal',payload)['result'];st=state();other=copy.deepcopy(st['coaches'][0]);other.update(_id=h.coach_id(1),slot=1);other.pop('_market_owner',None);st['coaches'].append(other);st['teams']['1']=copy.deepcopy(st['teams']['0']);st['defaultcoachid']=other['_id'];save(st)
 before=raw();assert not request('/players/trade/contract',{'select':0})['result'] and raw()==before
 st=state();st['defaultcoachid']=baseline['defaultcoachid'];active(st)[1]['players'][-1]['grade']=2;save(st)
 before=raw();assert not request('/players/trade/contract',{'select':0})['result'] and raw()==before
 passed('Trade owner and card-grade fingerprints block cross-manager and stale-ingredient quotation reuse')
 save({'coaches':[],'defaultcoachid':'','teams':{}});before=raw()
 assert request('/transfer/my/offer/list')['offers']==[]
 assert request(f'/transfer/search/{spid}')==[] and request('/transfer/top/50')==[]
 assert not request(f'/transfer/purchase/{spid}/1/10000/purchase',{})['result']
 assert not request('/transfer/offer',{'price':10000,'playerobjectid':'none'})['result']
 assert not request('/players/trade/proposal',{'players':['a','b']})['result']
 assert raw()==before
 passed('Manager-selection/new-account market prefetch is safe and read-only; no implicit manager or market state is created')
 assert not blocked
 result={'pass':True,'checks':checks,'private_https_port':srv.server_address[1], 'snapshot':str(ROOT),'writes':len(writes),'outside_writes_blocked':blocked,'seasons':sorted(season_samples),'real_state_used':False,'probability_trials':probability_results}
except Exception:
 import traceback
 result={'pass':False,'checks':checks,'traceback':traceback.format_exc(),'snapshot':str(ROOT),'outside_writes_blocked':blocked}
 print(result['traceback']);raise
finally:
 (RUN/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');srv.shutdown()
print('RESULT',RUN/'result.json')
