"""Exercise actual production purchase closures against the new chain in memory."""
from pathlib import Path
from types import SimpleNamespace
import ast,copy,json,threading
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
addon=json.loads((R/'nostalgia-product-addon.json').read_text('utf-8'));tracks={int(k):v for k,v in addon['chains'].items()};root=next(iter(tracks));track=tracks[root]
stages={i:(root,r,k) for r,row in enumerate(track['round_steps']) for k,i in enumerate(row)}
saved=dict(coaches=[dict(_id='synthetic-manager',appat='synthetic-life',cash=100000000,items=[])],teams={'0':{'players':[]}})
save_failure=False
def coach(st):return st['coaches'][0]
def add_cash(st,n,reason):coach(st)['cash']+=n
def inventory_add(c,i,n):
 x=next((x for x in c['items'] if x['itemid']==i),None)
 if x is None:x={'itemid':i,'remains':0};c['items'].append(x)
 x['remains']+=n;return x
def save(st):
 global saved
 if save_failure:raise OSError('injected save failure')
 saved=copy.deepcopy(st)
h=SimpleNamespace(STATE_LOCK=threading.RLock(),_state=lambda:copy.deepcopy(saved),my_coach=coach,add_cash=add_cash,inventory_add=inventory_add,_save=save,_json=lambda v:('application/json',json.dumps(v).encode()),coach_me_resources=lambda st,slot:[],_default_slot=lambda st:0)
tree=ast.parse((S/'product_packs.py').read_text('utf-8'));install=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='install')
names={'chain_record','chain_available','price','purchase'};nodes=[n for n in install.body if isinstance(n,ast.FunctionDef) and n.name in names];assert len(nodes)==4
for node in nodes:node.decorator_list=[]
def forbidden(*a):raise AssertionError('Unexpected fallback')
ns=dict(h=h,tracks=tracks,stages=stages,risks={},bundles={},rules={},copy=copy,json=json,prior_purchase=forbidden,previous_price=forbidden,listing=lambda st:[])
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(S/'product_packs.py'),'exec'),ns)
def buy(i,**extra):
 req=dict(productid=i,shopid=root,bunch=0);req.update(extra);return json.loads(ns['purchase']('',json.dumps(req).encode())[1])
checks=[];initial=copy.deepcopy(saved)
assert not buy(track['round_steps'][0][1])['result'] and saved==initial
assert not buy(track['steps'][0],bunch=1)['result'] and saved==initial
assert not buy(track['steps'][0],bunch=True)['result'] and saved==initial
assert not buy(track['steps'][0],shopid=123)['result'] and saved==initial
checks.append('wrong stage, quantity, boolean and shop id leave all assets unchanged')
save_failure=True
try:buy(track['steps'][0])
except OSError:pass
else:raise AssertionError('Injected failure not propagated')
assert saved==initial;save_failure=False;checks.append('save failure commits neither charge, packages nor progress')
for r,row in enumerate(track['round_steps']):
 for k,i in enumerate(row):
  before=copy.deepcopy(saved);result=buy(i);assert result['result']
  assert coach(saved)['cash']==coach(before)['cash']-track['prices'][str(i)]
  after=copy.deepcopy(saved);assert not buy(i)['result'] and saved==after
 count={x['itemid']:x['remains'] for x in coach(saved)['items']}
 assert count[97819000]==(r+1)*50 and count[97819011]==r+1 and count[97819084]==r+1
 assert saved['product_chain_rounds'][str(root)]['rounds']==r+1
checks.append('all 10 rounds charge the exact stage price and grant 50 random, 1 fixed11 and 1 moment1 per round')
final=copy.deepcopy(saved);assert not buy(track['steps'][0])['result'] and saved==final
assert saved['product_chain_rounds'][str(root)]['rounds']==10
assert coach(saved)['cash']==100000000-604000*10
checks.append('retries never duplicate rewards and completed chain cannot enter an eleventh round')
report=dict(status='MEMORY_CHAIN_FLOW_PASS',rounds=10,purchases=50,random_packages=500,fixed11_packages=10,moment1_packages=10,checks=checks,fixture_in_memory_only=True,production_written=False,native_verified=False)
(R/'chain-flow-result.json').write_text(json.dumps(report,indent=2),'utf-8');print(json.dumps(report,indent=2))
