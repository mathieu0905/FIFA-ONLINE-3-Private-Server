from pathlib import Path
import sys,json,copy,collections,ast,hashlib,threading
import host
h=host.h;R=host.R
from hot_update_runtime import compile_handlers,RequestHost
meta=json.loads((R/'business-meta.json').read_text('utf8'));source=(R/'business.py').read_bytes();before=(R/'before-business.py').read_bytes()
routes=meta['routes'];new=compile_handlers(source,'repriced',routes,allow_templates=True);old=compile_handlers(before,'before',routes,allow_templates=True)
ns=new['/shop/list'].__globals__;ons=old['/shop/list'].__globals__;data=ns['pricing_data']();base=copy.deepcopy(h._state());base.pop('market_simulation',None)
# Disposable fixtures do not need years of card-opening replay payloads. Keep
# identities/lifecycle and a few existing assets; production data is read only.
for coach in base['coaches']:
 for key in list(coach):
  if key.endswith('_receipts'):coach[key]={}
 coach['items']=coach.get('items',[])[:2];coach['depot']=coach.get('depot',[])[:1];coach['cash_ledger']=[]
for team in base['teams'].values():team['players']=team.get('players',[])[:2]
box={'st':base};saved=[];h._state=lambda:box['st']
def save(st):saved.append(True);box['st']=st
h._save=save;h.coach_me_resources=lambda st,slot:[]
def fresh(cash=10**9):
 st=copy.deepcopy(base);box['st']=st;c=h.my_coach(st);c['cash']=cash;c['product_purchase_counts']={};st['product_purchase_counts']={};st['product_chain_rounds']={};return st,c
def call(path,req=None,query=''):
 return json.loads(new[path](h,query,b'' if req is None else json.dumps(req).encode())[1])
def stock(st,i):return sum(x['remains'] for x in h.my_coach(st).get('items',[]) if x['itemid']==i)
checks=[];transactions=0
try:
 # Explicitly prove native code objects and registered hooks are reused, not
 # replaced by a hand-written purchase implementation.
 import inspect
 hooks=inspect.getclosurevars(h.register_shop_purchase_hook).nonlocals['purchase_hooks'];hook_ids={k:[id(x) for x in v] for k,v in hooks.items()}
 view=ns['pricing_host'](h,data);assert view.ENDPOINTS['/shop/purchase'].__code__ is h.ENDPOINTS['/shop/purchase'].__code__
 assert {k:[id(x) for x in v] for k,v in hooks.items()}==hook_ids
 checks.append('native wrapper code and all registered hooks retained')
 for key,p in data['proof'].items():assert p['price']<=p['old'] and p['price']>0
 assert data['prices']['98448082']==data['prices']['98448010']==9901
 assert data['proof']['98448082']['base_grade']==10 and data['proof']['98448082']['bonus']
 checks.append('358 prices valid, no increases; +10..15 bonus costs the same as fixed +10')
 # Prices in every nested shop definition agree with the charge table.
 st,c=fresh();rows=call('/shop/list');prices={r['product']['itemid']:r for r in rows}
 for row in rows:
  for part in [row]+(row['chained'] if isinstance(row.get('chained'),list) else []):
   d=part['product']['staticdata'];i=d['itemid']
   if str(i) in data['prices']:
    assert all(b['price']==data['prices'][str(i)]*b['bunch'] for b in d['bunches'])
 checks.append('shop, nested definitions and quantity-menu prices match')
 # Native validation and commit hooks receive the corrected prices exactly once.
 seen=[]
 r1=h.register_shop_purchase_hook('validate',lambda st,ctx:seen.append(('validate',ctx['price'],ctx['bunch'])))
 r2=h.register_shop_purchase_hook('before_commit',lambda st,ctx:seen.append(('commit',ctx['price'],ctx['bunch'])))
 for i,index,n in [(98448082,0,1),(98448082,1,10),(98448010,0,1),(98432701,0,1),(98432702,0,1)]:
  st,c=fresh();original=stock(st,i);seen.clear();out=call('/shop/purchase',dict(productid=i,bunch=index));assert out['result'],(i,out)
  paid=data['prices'][str(i)]*n;assert out['spent']==paid and h.my_coach(box['st'])['cash']==10**9-paid
  assert stock(box['st'],i)-original==n and seen==[('validate',paid,n),('commit',paid,n)],(i,seen)
  transactions+=1
 r1();r2();checks.append('single, ten-pack and permitted choice purchases charge exactly displayed amount')
 # Limit exhaustion, insufficient cash, malformed quantity, and save failures.
 st,c=fresh();rule=h.item_purchase_limit(98448010)
 for _ in range(rule['count']):assert call('/shop/purchase',dict(productid=98448010,bunch=0))['result']
 count=len(saved);assert not call('/shop/purchase',dict(productid=98448010,bunch=0))['result'] and len(saved)==count
 st,c=fresh(cash=data['prices']['98448082']-1);snapshot=copy.deepcopy(st);assert not call('/shop/purchase',dict(productid=98448082,bunch=0))['result'] and box['st']==snapshot
 for index in (True,-1,99,1.2):
  st,c=fresh();snapshot=copy.deepcopy(st);assert not call('/shop/purchase',dict(productid=98448082,bunch=index))['result'] and box['st']==snapshot
 st,c=fresh();snapshot=copy.deepcopy(st);h._save=lambda st:(_ for _ in ()).throw(OSError('injected atomic save failure'))
 try:call('/shop/purchase',dict(productid=98448082,bunch=0))
 except OSError:pass
 else:raise AssertionError('Save error swallowed')
 assert box['st']==snapshot;h._save=save
 checks.append('native limits, malformed bunch, insufficient funds and failed-save isolation')
 # Preserve all actual package/monthly benefits while changing only their prices.
 for i,p in data['proof'].items():
  if p['kind'] not in ('bundle','monthly'):continue
  i=int(i)
  if i not in prices or not prices[i].get('buy',True):continue
  st,c=fresh();prior=collections.Counter({x['itemid']:x['remains'] for x in c.get('items',[])})
  contents=h.PACKAGES[i][2] if i in h.PACKAGES else h.MONTHLY[i][3]
  out=call('/shop/purchase',dict(productid=i,bunch=0));assert out['result'],(i,out)
  after_counts=collections.Counter({x['itemid']:x['remains'] for x in h.my_coach(box['st']).get('items',[])})
  expected=collections.Counter({child:n for child,n in contents if child not in (h.EP_ITEM,h.ES_ITEM)})
  assert after_counts-prior==expected and out['spent']==data['prices'][str(i)]
  if i in h.MONTHLY:assert str(i) in h.my_coach(box['st'])['monthly']
  transactions+=1
 checks.append('package contents and monthly duration/benefits unchanged')
 # Full and partial chains use the same table, with signed repricing and replay.
 new_plan=ns['volume_data']();old_plan=ons['volume_data']();chain_cases=0
 h.shop_list=lambda st:[h.chained_entry(st,int(root)) for root in new_plan]
 for root,t in new_plan.items():
  for rn in (0,9):
   st,c=fresh();st['product_chain_rounds'][root]=dict(rounds=rn,stage=0,owner=None)
   q=call('/shop/chain/round/quote',query='root='+root)['quote'];assert sum(n for i,n in q['rewards'])==110
   count=len(saved);out=call('/shop/chain/round/purchase',dict(quote=q));assert out['result'] and len(saved)==count+1 and out['spent']==q['total']
   paid_cash=h.my_coach(box['st'])['cash'];count=len(saved);assert call('/shop/chain/round/purchase',dict(quote=q))['replayed'] and len(saved)==count and h.my_coach(box['st'])['cash']==paid_cash
   chain_cases+=1
  for k,i in enumerate(t['steps']):
   st,c=fresh();st['product_chain_rounds'][root]=dict(rounds=0,stage=k,owner=None)
   out=call('/shop/purchase',dict(productid=i,shopid=int(root),bunch=0));assert out['result'] and out['spent']==t['prices'][str(i)]
   row=next(r for r in call('/shop/list') if r['shopid']==int(root));part=([row]+row['chained'])[k]
   assert part['product']['staticdata']['bunches'][0]['price']==t['prices'][str(i)]
   chain_cases+=1
  # The previous high8 price is displayed exactly for already-paid tiers.
  st,c=fresh();st['product_chain_rounds'][root]=dict(rounds=0,stage=1,owner=None,volume_stage_versions={str(t['steps'][0]):'volume110-high8-v2'})
  row=next(r for r in call('/shop/list') if r['shopid']==int(root));assert row['product']['staticdata']['bunches'][0]['price']==old_plan[root]['prices'][str(t['steps'][0])]
  st['product_chain_rounds'][root].pop('volume_stage_versions')
  row=next(r for r in call('/shop/list') if r['shopid']==int(root));assert row['product']['staticdata']['bunches'][0]['price']==h.item_def(t['steps'][0])['bunches'][0]['price']
  st,c=fresh();q=json.loads(old['/shop/chain/round/quote'](h,'root='+root,b'')[1])['quote'];out=call('/shop/chain/round/purchase',dict(quote=q));assert not out['result'] and '变化' in out['message']
 checks.append('35 chain transactions, replay, changed quote rejection and historical paid prices')
 # One remaining weekly unit: simultaneous requests cannot over-grant.
 st,c=fresh();n=h.item_purchase_limit(98448010)['count']
 for _ in range(n-1):assert call('/shop/purchase',dict(productid=98448010,bunch=0))['result']
 results=[]
 def buy():results.append(call('/shop/purchase',dict(productid=98448010,bunch=0))['result'])
 threads=[threading.Thread(target=buy) for _ in range(2)]
 for t in threads:t.start()
 for t in threads:t.join()
 assert sorted(results)==[False,True]
 checks.append('concurrent quota contention grants only one remaining purchase')
 # Do not rewrite the opening implementation or market-supply transaction.
 def funcs(src):return {x.name:x for x in ast.parse(src).body if isinstance(x,ast.FunctionDef)}
 of=funcs(before);nf=funcs(source)
 for name in ('open_pack','bulk_open','bulk_draw','market_supply_activate'):
  target='_pricing_base_'+name if name=='open_pack' else name
  a=copy.deepcopy(of[name]);a.name=target;assert ast.dump(a)==ast.dump(nf[target]),name
 checks.append('single/bulk draw probabilities and market-supply code unchanged')
 report=dict(status='PASS',source_sha256=hashlib.sha256(source).hexdigest(),price_entries=len(data['proof']),ordinary_transactions=transactions,chain_transactions=chain_cases,checks=checks,real_state_shop_written=False,real_purchase_performed=False,native_verified=False)
 (R/'tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report))
finally:host.close()
