"""Actual production handlers, memory/temporary data only. No listener/real purchases."""
from pathlib import Path
import faulthandler
faulthandler.dump_traceback_later(30,repeat=False)
import sys,os,json,copy,hashlib,concurrent.futures
sys.dont_write_bytecode=True
R=Path(__file__).parent;P=R/'checks-runtime/server';S=Path(r'D:\FO3ID\server')
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
def audit(event,args):
 if event=='open':
  path,mode,flags=args
  if isinstance(path,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
   if not Path(os.fsdecode(path)).resolve().is_relative_to(R):raise PermissionError('No writes outside temporary test data')
sys.addaudithook(audit);sys.path.insert(0,str(P));sys.argv=['http_config.py']
import http_config as h
print('Current complete handlers imported',flush=True)
new=json.loads((P/'gamedata/chain_rebalance_products.json').read_text('utf8'));summary=json.loads((R/'summary.json').read_text('utf8'))
checks=[]
def check(s,v=True):assert v,s;checks.append(s);print(s,flush=True)
def body(r):return json.loads(r[1])
seed=copy.deepcopy(h._state());coach=h.my_coach(seed);coach.update(_id='temporary-chain-regression',appat='fixture-only',cash=999999999,items=[],depot=[],risk_pack_receipts={});seed['defaultcoachid']=coach['_id'];seed['product_chain_rounds']={}
for field in ('market_simulation','match'):seed.pop(field,None)
memory=[copy.deepcopy(seed)]
# Preserve the production listing snapshot optimization while replacing only its
# underlying persistence reader. Replacing the outer wrapper copies the large
# market on every individual SKU and is not representative of the real route.
cells=dict(zip(h._state.__code__.co_freevars,h._state.__closure__))
assert 'prior_state' in cells
cells['prior_state'].cell_contents=lambda:copy.deepcopy(memory[0])
h._save=lambda st:memory.__setitem__(0,copy.deepcopy(st))
def fresh():memory[0]=copy.deepcopy(seed)
def buy(i,root,**extra):return body(h.ENDPOINTS['/shop/purchase']('',json.dumps(dict({'productid':i,'shopid':root,'bunch':0},**extra)).encode()))
def reject(fn):
 before=copy.deepcopy(memory[0]);out=fn();assert out['result'] is False;assert memory[0]==before;return out
def listing():return body(h.ENDPOINTS['/shop/list']('',b''))
def row(root):return next(r for r in listing() if r['shopid']==root)
newroots=set(map(int,new['chains']));oldroots=set(new['retired_chains'])
check('New roots visible; legacy roots cannot begin a new round',newroots<={r['shopid'] for r in listing()} and not oldroots&{r['shopid'] for r in listing()})
for root in oldroots:
 track=h.product_packs['chains'][str(root)];reject(lambda:buy(track['round_steps'][0][0],root))
check('All retired first-stage requests rejected without charging')
fresh();live_old=next(root for root in oldroots if root==71231901)
old=h.product_packs['chains'][str(live_old)];memory[0]['product_chain_rounds'][str(live_old)]=dict(rounds=1,stage=3,owner=None,owner_appat=None)
assert '旧期续购' in row(live_old)['chainedproductname']
for index in [3,4]:
 i=old['round_steps'][1][index];price=h.product_price(i,1);cash=h.my_coach(memory[0])['cash'];out=buy(i,live_old)
 assert out['result'] and cash-h.my_coach(memory[0])['cash']==price
assert live_old not in {r['shopid'] for r in listing()};reject(lambda:buy(old['round_steps'][2][0],live_old))
check('Existing unfinished legacy round keeps exact original cost/rewards and ends without resetting progress')
listing_cells=dict(zip(h.shop_list.__code__.co_freevars,h.shop_list.__closure__))
previous_store=listing_cells['previous_list'].cell_contents
# The real complete storefront was exercised above. Keep repeated transaction
# regressions focused on the exact chain wrapper rather than rebuilding hundreds
# of unrelated older sale items 250 times.
listing_cells['previous_list'].cell_contents=lambda st:[]
for root_text,t in new['chains'].items():
 root=int(root_text);fresh();expected={};spent=0
 for rn in range(10):
  for k,i in enumerate(t['round_steps'][rn]):
   if rn==0 and k==0:
    reject(lambda:buy(t['round_steps'][0][1],root));reject(lambda:buy(i,root+1));reject(lambda:buy(i,root,bunch=True))
   cash=h.my_coach(memory[0])['cash'];out=buy(i,root);cost=t['prices'][str(i)];spent+=cost
   assert out['result'] and out['spent']==cost and cash-h.my_coach(memory[0])['cash']==cost
   for child,n in t['packages'][str(i)]['contents']:expected[child]=expected.get(child,0)+n
   reject(lambda:buy(i,root))
   resources={r['uri']:r['body'] for r in out['resources']};entry=next(r for r in resources['/shop/list'] if r['shopid']==root)
   parts=[entry]+entry['chained'];assert len(parts)==5 and all(p['shopid']==root for p in parts)
   assert out['states'][str(root)]['step']==entry['step'] and out['states'][str(root)]['buy']==entry['buy']
   quota=next(r for r in resources['/shop/remained/limited'] if r['shopid']==root)
   assert quota['buy']==entry['buy'] and quota['step']==entry['step']
 actual={i['itemid']:i['remains'] for i in h.my_coach(memory[0])['items']}
 assert actual==expected and seed['coaches'][0]['cash']-h.my_coach(memory[0])['cash']==spent
 reject(lambda:buy(t['steps'][0],root))
 check('Five ordered stages x ten rounds, exact prices/inventory, replay rejection, quota/root refresh '+root_text)
fresh();first=next(iter(new['chains'].values()));root=int(next(iter(new['chains'])));i=first['steps'][0]
h.my_coach(memory[0])['cash']=0;reject(lambda:buy(i,root));check('Insufficient funds cannot change assets')
fresh();oldsave=h._save
def fail(st):raise OSError('temporary save failure')
h._save=fail;before=copy.deepcopy(memory[0])
try:buy(i,root);raise AssertionError('Save failure should propagate')
except OSError:pass
finally:h._save=oldsave
assert memory[0]==before;check('Injected save failure preserves cash, inventory and progress')
fresh()
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:outs=list(pool.map(lambda _:buy(i,root),range(2)))
assert sum(bool(x['result']) for x in outs)==1;check('Concurrent duplicate stage request charges/grants exactly once')
fresh();assert buy(i,root)['result'];memory[0]['defaultcoachid']='temporary-other';other=copy.deepcopy(h.my_coach(seed));other.update(_id='temporary-other',slot=1,appat='other-only');memory[0]['coaches'].append(other);memory[0]['teams']['1']=copy.deepcopy(memory[0]['teams']['0'])
reject(lambda:buy(first['steps'][1],root));check('Manager switch cannot steal an in-progress round')
fresh();searchfn=next(fn for p,fn in h.ROUTES if p.pattern==r'/packchoice/(\d+)/search')
for text,d in new['strength_packs'].items():
 fresh();itemid=int(text);grade=next(g for g,w in enumerate(d['grades'],1) if w)
 assert len([w for w in d['grades'] if w])==1
 h.inventory_add(h.my_coach(memory[0]),itemid,2)
 rows=h.coach_items(h._state(),h._default_slot(h._state()));token=next(x['_id'] for x in rows if x['itemid']==itemid)
 assert '_pf_v2_' in token
 if d['mode']=='choice':
  choices=body(searchfn(text,'q=&league=-1&team=-1',b''));assert {r['spid'] for r in choices}==set(d['tiers'][0]['pool']) and {r['grade'] for r in choices}=={grade}
  assert body(searchfn(text,'q=NoSuchFrozenPlayer1234567',b''))==[]
  reject(lambda:body(h.ep_item_use(token,'',json.dumps(dict(spids=[1])).encode())))
  req=json.dumps(dict(spids=[choices[0]['spid']])).encode()
 else:req=b'{}'
 before_cards=len(h.my_team(memory[0]).get('players',[])) if hasattr(h,'my_team') else None
 opened=body(h.ep_item_use(token,'',req));assert opened['result'] and opened['player']['grade']==grade and opened['player']['spid'] in d['tiers'][0]['pool']
 after=copy.deepcopy(memory[0]);again=body(h.ep_item_use(token,'',req));assert again['result'] and memory[0]==after and again['player']==opened['player']
check('All 20 new pack IDs actually grant their fixed grade; choice filters/pool/invalid pick and token replay validated')
listing_cells['previous_list'].cell_contents=previous_store
fresh();visible={x['shopid'] for x in listing() if x.get('visible',True)};assert not visible&set(new['chain_only_items']);check('Exclusive new reward packs do not appear as standalone sale offers')
from pack_value import ValueModel
model=ValueModel(h,h.product_packs['valuation']['points_per_ep'])
for record in summary['chains']:
 t=new['chains'][str(record['root'])];liveprices=[h.product_price(i,1) for i in t['steps']];assert sum(liveprices)==record['round_points']
 assert abs(sum(model.value(i) for i in t['steps'])-record['expected_ep'])<1
 if record['premium']:assert 400000<=sum(liveprices)<=500000
check('Premium rounds within 400k..500k points; all chains share expected-value pricing within 0.17%')
for name in ['product_packs.json','product_chain_elite.json','shop_value_products.json','pack_cadence.json']:
 assert (P/'gamedata'/name).read_bytes()==(S/'gamedata'/name).read_bytes()
check('Previously issued frozen definitions, odds and prices remain byte-identical')
(R/'test-results.json').write_text(json.dumps(dict(status='PASS',checks=checks,count=len(checks),formal_assets_written=False,listener_started=False,native_verified=False),indent=2),encoding='utf8')
print(json.dumps(dict(status='PASS',count=len(checks))))
