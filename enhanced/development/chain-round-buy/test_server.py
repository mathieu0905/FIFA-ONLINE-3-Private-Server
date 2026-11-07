from pathlib import Path
import sys,os,json,copy,concurrent.futures
sys.dont_write_bytecode=True
R=Path(__file__).parent;P=R/'checks-runtime/server'
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0');sys.path.insert(0,str(P));sys.argv=['http_config.py']
def audit(event,args):
 if event=='open':
  path,mode,flags=args
  if isinstance(path,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
   if not Path(os.fsdecode(path)).resolve().is_relative_to(R):raise PermissionError('Test writes restricted to temporary task data')
sys.addaudithook(audit)
import http_config as h,chain_round_purchase as module
native_time=module.time.time
seed=copy.deepcopy(h._state());coach=h.my_coach(seed);coach.update(_id='temporary-round-regression',appat='fixture-only',cash=999999999,items=[],depot=[],risk_pack_receipts={})
seed['defaultcoachid']=coach['_id'];seed['product_chain_rounds']={};seed.pop('product_chain_bulk_receipts',None)
for k in ['market_simulation','match']:seed.pop(k,None)
memory=[copy.deepcopy(seed)];saves=[0]
old_listing=h.shop_list.__closure__[h.shop_list.__code__.co_freevars.index('old_listing')].cell_contents
cells=dict(zip(old_listing.__code__.co_freevars,old_listing.__closure__));cells['previous_list'].cell_contents=lambda st:[]
state_cells=dict(zip(h._state.__code__.co_freevars,h._state.__closure__));state_cells['prior_state'].cell_contents=lambda:copy.deepcopy(memory[0])
def save(st):memory[0]=copy.deepcopy(st);saves[0]+=1
h._save=save
def fresh():memory[0]=copy.deepcopy(seed);saves[0]=0
def body(r):return json.loads(r[1])
def quote(root):return body(h.ENDPOINTS['/shop/chain/round/quote']('root='+str(root),b''))
def buy(q):return body(h.ENDPOINTS['/shop/chain/round/purchase']('',json.dumps(dict(quote=q)).encode()))
def reject(fn):
 before=copy.deepcopy(memory[0]);n=saves[0];out=fn();assert out['result'] is False;assert memory[0]==before and saves[0]==n
def check(s,v=True):assert v,s;checks.append(s);print(s,flush=True)
checks=[]
new=json.loads((P/'gamedata/chain_rebalance_products.json').read_text('utf8'))
for roottext,t in new['chains'].items():
 root=int(roottext);fresh();before=copy.deepcopy(memory[0]);q=quote(root);assert q['result'] and memory[0]==before and saves[0]==0
 cost=sum(t['prices'][str(i)] for i in t['steps']);assert q['quote']['total']==cost
 out=buy(q['quote']);assert out['result'] and out['spent']==cost and saves[0]==1 and seed['coaches'][0]['cash']-h.my_coach(memory[0])['cash']==cost
 assert memory[0]['product_chain_rounds'][roottext]['rounds']==1 and memory[0]['product_chain_rounds'][roottext]['stage']==0
 expected={}
 for i in t['steps']:
  for child,n in t['packages'][str(i)]['contents']:expected[child]=expected.get(child,0)+n
 assert {i['itemid']:i['remains'] for i in h.my_coach(memory[0])['items']}==expected
 before=copy.deepcopy(memory[0]);out2=buy(q['quote']);assert out2['result'] and out2['replayed'] and memory[0]==before and saves[0]==1
 rows={r['uri']:r['body'] for r in out['resources']};entry=next(r for r in rows['/shop/list'] if r['shopid']==root);assert entry['round_buy_enabled'] and entry['round_buy_stages']==5
 check('Five-stage round in one save; exact grants/charge/one-round advance/idempotent retry '+roottext)
root=71250201;t=new['chains'][str(root)]
fresh()
for i in t['steps'][:3]:assert body(h.ENDPOINTS['/shop/purchase']('',json.dumps(dict(productid=i,shopid=root,bunch=0)).encode()))['result']
q=quote(root)['quote'];assert q['stage']==3 and len(q['steps'])==2 and q['total']==sum(t['prices'][str(i)] for i in t['steps'][3:]);before=h.my_coach(memory[0])['cash'];n=saves[0]
assert buy(q)['result'] and before-h.my_coach(memory[0])['cash']==q['total'] and saves[0]==n+1
check('Partly bought round purchases only the remaining two stages')
fresh();q=quote(root)['quote'];bad=copy.deepcopy(q);bad['total']=1;reject(lambda:buy(bad));bad=copy.deepcopy(q);bad['rewards'][0][1]=999;reject(lambda:buy(bad));check('Tampered price/rewards rejected without assets changed')
assert body(h.ENDPOINTS['/shop/purchase']('',json.dumps(dict(productid=t['steps'][0],shopid=root,bunch=0)).encode()))['result'];reject(lambda:buy(q));check('Stale quote after a single-stage purchase rejected')
fresh();q=quote(root)['quote'];original=h.product_price;h.product_price=lambda i,n,*a:original(i,n,*a)+100
reject(lambda:buy(q));h.product_price=original;check('Changed server price invalidates old quote')
fresh();q=quote(root)['quote'];module.time.time=lambda:q['expires']+1
reject(lambda:buy(q));module.time.time=native_time
check('Expired uncommitted quote rejected')
fresh();q=quote(root)['quote'];h.my_coach(memory[0])['cash']=0;reject(lambda:buy(q));check('Insufficient cash rejects the entire purchase')
fresh();q=quote(root)['quote'];oldsave=h._save
def fail(st):raise OSError('injected atomic save failure')
h._save=fail;before=copy.deepcopy(memory[0])
try:buy(q);raise AssertionError('Expected failure')
except OSError:pass
finally:h._save=oldsave
assert memory[0]==before and saves[0]==0;check('Save failure leaves cash/rewards/progress/receipt all unchanged')
fresh();q=quote(root)['quote'];add=h.inventory_add
def badgrant(c,i,n):raise OSError('injected inventory failure')
h.inventory_add=badgrant;before=copy.deepcopy(memory[0])
try:buy(q);raise AssertionError('Expected failure')
except OSError:pass
finally:h.inventory_add=add
assert memory[0]==before and saves[0]==0;check('Grant failure cannot partially charge or advance the round')
fresh();q=quote(root)['quote']
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:results=list(executor.map(lambda _:buy(q),range(2)))
assert all(r['result'] for r in results) and sum(r['replayed'] for r in results)==1 and saves[0]==1
check('Concurrent identical confirmed quotes commit once and return the same receipt')
module.time.time=lambda:q['expires']+600
assert buy(q)['result'] and saves[0]==1;module.time.time=native_time
check('Committed receipt can be retried after quote expiry without charging again')
fresh();q=quote(root)['quote'];h.my_coach(memory[0])['_id']='manager-was-replaced';memory[0]['defaultcoachid']='manager-was-replaced';reject(lambda:buy(q));check('Manager lifecycle change cannot use an old quote')
fresh();memory[0]['product_chain_rounds'][str(root)]=dict(rounds=9,stage=4,owner=None,owner_appat=None);q=quote(root)['quote'];assert len(q['steps'])==1
assert buy(q)['result'];assert not quote(root)['result'];check('Last stage of round ten completes exactly once; no eleventh round')
fresh();legacy=71231901;assert not quote(legacy)['result'];memory[0]['product_chain_rounds'][str(legacy)]=dict(rounds=1,stage=3,owner=None,owner_appat=None)
q=quote(legacy)['quote'];assert len(q['steps'])==2;assert buy(q)['result'];assert not quote(legacy)['result'];check('Legacy unfinished round can finish in bulk; retired next round remains blocked')
(R/'server-tests.json').write_text(json.dumps(dict(status='PASS',count=len(checks),checks=checks,real_assets_written=False,listener_started=False,native_verified=False),indent=2),encoding='utf8');print(json.dumps(dict(status='PASS',count=len(checks))))
