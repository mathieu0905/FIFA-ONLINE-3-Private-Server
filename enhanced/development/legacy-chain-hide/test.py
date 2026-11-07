from pathlib import Path
import os,sys,json,copy
sys.dont_write_bytecode=True
R=Path(__file__).parent;P=R/'checks-runtime/server'
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0');sys.path.insert(0,str(P));sys.argv=['http_config.py']
def audit(event,args):
 if event=='open':
  p,m,f=args
  if isinstance(p,(str,bytes,os.PathLike)) and ((isinstance(m,str) and any(c in m for c in 'wax+')) or (isinstance(f,int) and f&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
   if not Path(os.fsdecode(p)).resolve().is_relative_to(R):raise PermissionError('Only temporary regression data writable')
sys.addaudithook(audit)
import http_config as h,legacy_chain_hide as hide
seed=copy.deepcopy(h._state());seed.pop('market_simulation',None);seed.pop('match',None)
coach=h.my_coach(seed);coach['cash']=999999999;memory=[copy.deepcopy(seed)];saves=[0]
statecells=dict(zip(h._state.__code__.co_freevars,h._state.__closure__));statecells['prior_state'].cell_contents=lambda:copy.deepcopy(memory[0])
def save(st):memory[0]=copy.deepcopy(st);saves[0]+=1
h._save=save
def body(v):return json.loads(v[1])
def get():return body(h.ENDPOINTS['/shop/list']('',b''))
def buy(i,root):return body(h.ENDPOINTS['/shop/purchase']('',json.dumps(dict(productid=i,shopid=root,bunch=0)).encode()))
def quote(root):return body(h.ENDPOINTS['/shop/chain/round/quote']('root='+str(root),b''))
def bulk(q):return body(h.ENDPOINTS['/shop/chain/round/purchase']('',json.dumps(dict(quote=q)).encode()))
old=71231901;memory[0].setdefault('product_chain_rounds',{})[str(old)]=dict(rounds=1,stage=3,owner=None,owner_appat=None)
oldquote=quote(old)['quote'];old_memory=copy.deepcopy(memory[0]);assert bulk(oldquote)['result'];committed=copy.deepcopy(memory[0])
memory[0]=copy.deepcopy(old_memory)
before_rows=get();assert any(r['shopid']==old for r in before_rows)
before_inventory=copy.deepcopy(h.coach_items(h._state(),h._default_slot(h._state())))
before_defs={i:h.item_def(i) for i in [97819000,97819011,97819084]}
hide.install(h);before=copy.deepcopy(memory[0]);n=saves[0];rows=get();retired=h.legacy_chain_withdrawn_roots
assert not {r['shopid'] for r in rows}&retired
assert {71250101,71250201,71250301,71250401,71250501}<={r['shopid'] for r in rows}
assert rows==body(h.from_file('/shop/list')) and memory[0]==before and saves[0]==n
checks=['Old unfinished and completed/history chains absent from every list route; five new chains intact; no state writes']
for route in [lambda:buy(71231904,71231901),lambda:buy(71010101,71010101),lambda:buy(70000001,70000001),lambda:buy(0,900000000+71231904),lambda:quote(old),lambda:bulk(oldquote)]:
 b=copy.deepcopy(memory[0]);n=saves[0];assert route()['result'] is False and memory[0]==b and saves[0]==n
checks.append('Old single-stage, encoded currency alias, quote and previously issued uncommitted bulk quote rejected without charge')
quota=body(h.ENDPOINTS['/shop/remained/limited']('',b''));assert not {r['shopid'] for r in quota}&retired and quota==body(h.from_file('/shop/remained/limited'))
assert not h.chained_entry(h._state(),old)['buy'] and not h.chained_entry(h._state(),old)['visible']
checks.append('Old quota/cache/direct row state also hidden and disabled')
assert h.coach_items(h._state(),h._default_slot(h._state()))==before_inventory
assert all(h.item_def(i)==v for i,v in before_defs.items());assert memory[0]['product_chain_rounds'][str(old)]==old_memory['product_chain_rounds'][str(old)]
checks.append('Paid inventory item definitions, balances and original unfinished progress unchanged')
for root in [71250101,71250201,71250301,71250401,71250501]:
 q=quote(root);assert q['result'];t=h.product_packs['chains'][str(root)]
 i=t['steps'][0];cash=h.my_coach(memory[0])['cash'];out=buy(i,root);assert out['result'] and cash-h.my_coach(memory[0])['cash']==h.product_price(i,1)
 resources={r['uri']:r['body'] for r in out['resources']};assert not {r['shopid'] for r in resources['/shop/list']}&retired
 assert not {r['shopid'] for r in resources['/shop/remained/limited']}&retired
checks.append('All five new first stages still buy at exact price and refresh without legacy rows')
out=bulk(quote(71250301)['quote']);assert out['result']
assert not {r['shopid'] for x in out['resources'] if x['uri']=='/shop/list' for r in x['body']}&retired
checks.append('New bulk completion remains functional and keeps legacy offers filtered')
memory[0]=committed;b=copy.deepcopy(memory[0]);n=saves[0];out=bulk(oldquote)
assert out['result'] and out['replayed'] and memory[0]==b and saves[0]==n
assert not {r['shopid'] for x in out['resources'] if x['uri']=='/shop/list' for r in x['body']}&retired
checks.append('Already committed legacy bulk receipt can retry idempotently without reopening old sales')
mul_before={r['product']['itemid']:r for r in before_rows if 98248000<=r['product']['itemid']<98249000}
mul_after={r['product']['itemid']:r for r in rows if 98248000<=r['product']['itemid']<98249000}
assert mul_before and mul_before==mul_after
checks.append('New MUL +8 offers stay visible and definitions unmodified')
(R/'test-results.json').write_text(json.dumps(dict(status='PASS',count=len(checks),checks=checks,real_assets_written=False,native_verified=False),indent=2),encoding='utf8');print(json.dumps(dict(status='PASS',count=len(checks))))
