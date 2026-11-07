import copy,json
import host
from hot_update_runtime import compile_handlers,RequestHost
h=host.h;R=host.R;S=host.S
active=json.loads((S/'hot_updates/active.json').read_text('utf8'));routes=active['routes']
old_handlers=compile_handlers((S/active['code']).read_bytes(),active['code'],routes,allow_templates=True)
handlers=compile_handlers((R/'high8-business.py').read_bytes(),'high8-business.py',routes,allow_templates=True)
old_data=json.loads((R/'volume-before.json').read_text('utf8'));new_data=json.loads((R/'volume-after.json').read_text('utf8'))
base=h._state();slot=h._default_slot(base);coach=h.my_coach(base)
base={k:v for k,v in base.items() if k in ('coaches','teams','defaultcoachid')};base['coaches']=[coach];base['teams']={str(slot):base['teams'][str(slot)]}
coach['items']=[];coach['depot']=[];coach['cash']=10**9;coach['_admin_generation']='high8-chain-test'
base['teams'][str(slot)]['players']=[];base['product_chain_rounds']={};base['product_chain_bulk_receipts']={}
state=copy.deepcopy(base);saves=0
def read():return copy.deepcopy(state)
def save(s):
 global state,saves
 state=copy.deepcopy(s);saves+=1
h._state=read;h._save=save;h.coach_me_resources=lambda st,sl:[]
def call(path,query='',body=None,old=False):
 return json.loads((old_handlers if old else handlers)[path](RequestHost(h,{}),query,json.dumps(body).encode() if body is not None else b'')[1])
cases=[]
try:
 mapping={int(k):v for k,v in json.loads((R/'upgrade-mapping.json').read_text('utf8')).items()}
 for root,t in new_data.items():
  for sid,p in t['packages'].items():
   prior=old_data[root]['packages'][sid]
   assert p['contents']==[[mapping.get(i,i),n] for i,n in prior['contents']]
   if p['contents']==prior['contents']:assert p==prior
   assert all(min(g for g,w in h.pack_grades(i) if w)>=8 or {s//1000000 for s,w in h.pack_pool(i)}=={84} for i,n in p['contents'])
 cases.append('Every future chain reward is high grade except pure moments; counts and untouched stages exact')
 for root,t in new_data.items():
  if root not in h.product_packs['chains']:continue
  state=copy.deepcopy(base);saves=0
  q=call('/shop/chain/round/quote','?root='+root)
  if not q['result']:continue
  q=q['quote'];assert q['total']==sum(t['prices'][str(i)] for i in q['steps'])
  before=h.my_coach(state)['cash'];out=call('/shop/chain/round/purchase',body=dict(quote=q));assert out['result'] and saves==1
  assert h.my_coach(state)['cash']==before-q['total'],(root,before,q['total'],h.my_coach(state)['cash'])
  inventory={r['itemid']:r['remains'] for r in h.my_coach(state)['items']}
  assert inventory==dict(q['rewards'])
  again=call('/shop/chain/round/purchase',body=dict(quote=q));assert again['result'] and again['replayed'] and saves==1
  cases.append('New chain quote, purchase exact rewards/cost and replay '+root)
 # A previously valid low-grade quote must be rejected without charging.
 for root,t in new_data.items():
  if not any(t['packages'][sid]['contents']!=old_data[root]['packages'][sid]['contents'] for sid in t['packages']):continue
  state=copy.deepcopy(base);saves=0;oldq=call('/shop/chain/round/quote','?root='+root,old=True)
  if not oldq['result']:continue
  snap=copy.deepcopy(state);out=call('/shop/chain/round/purchase',body=dict(quote=oldq['quote']))
  assert not out['result'] and state==snap and saves==0
  cases.append('Old signed low-grade quote rejected '+root)
  # Preserve completed volume110-v1 stage contents and price, while later stages upgrade.
  first=t['round_steps'][0][0];coach=h.my_coach(state)
  state['product_chain_rounds'][root]=dict(rounds=0,stage=1,owner=str(coach['_id']),owner_appat=coach.get('appat'),volume_stage_versions={str(first):'volume110-v1'})
  rows=call('/shop/list');row=next(r for r in rows if str(r.get('shopid'))==root)
  completed=next(p for p in [row]+row.get('chained',[]) if p['product']['itemid']==first)
  got=completed['product']['staticdata'];prior=old_data[root]['packages'][str(first)]
  assert [[r['itemid'],r['count']] for r in got['items']]==prior['contents']
  assert got['bunches'][0]['price']==prior['price']
  q=call('/shop/chain/round/quote','?root='+root)['quote'];assert len(q['steps'])==4 and first not in q['steps']
  cases.append('Completed prior-volume stage remains exact; quote only remaining upgraded stages '+root)
 report=dict(status='PASS',case_count=len(cases),cases=cases,real_assets_written=False,native_verified=False)
 (R/'chain-tests.json').write_text(json.dumps(report,indent=2),'utf8');print(json.dumps(report))
finally:host.close()
