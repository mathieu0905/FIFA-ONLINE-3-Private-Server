import copy,json,threading
from pathlib import Path
import host
from build import RANDOM,CHOICE
from hot_update_runtime import compile_handlers,RequestHost
h=host.h;R=host.R;S=host.S
active=json.loads((S/'hot_updates/active.json').read_text('utf8'))
handlers=compile_handlers((R/'high8-business.py').read_bytes(),'high8-business.py',active['routes'],allow_templates=True)
base=copy.deepcopy(h._state());slot=h._default_slot(base);coach=h.my_coach(base)
base={k:v for k,v in base.items() if k in ('coaches','teams','defaultcoachid')}
base['coaches']=[coach];base['teams']={str(slot):base['teams'][str(slot)]}
coach['items']=[];coach['depot']=[];coach['cash']=1000000;coach['_admin_generation']='china-future-packs-test'
for key in ['risk_pack_receipts','bulk_player_pack_receipts','product_purchase_counts']:coach.pop(key,None)
base.pop('product_purchase_counts',None);base['teams'][str(slot)]['players']=[]
state=copy.deepcopy(base);saves=0
def read():return copy.deepcopy(state)
def save(st):
 global state,saves
 state=copy.deepcopy(st);saves+=1
h._state=read;h._save=save
h.coach_me_resources=lambda st,sl:[dict(uri='/coach/me',body={'items':h.coach_items(st,sl)})]
def reset(i,count=1,capacity=100):
 global state,saves
 state=copy.deepcopy(base);saves=0;h.MAX_PLAYERS=capacity;h.inventory_add(h.my_coach(state),i,count)
 return str(next(r for r in h.coach_items(state,slot) if r['itemid']==i)['_id'])
def call(token,req):return json.loads(handlers['/item/{item_id}/use'](RequestHost(h,{'item_id':token}),'',json.dumps(req).encode())[1])
cases=[]
try:
 old=json.loads((S/'gamedata/club_season_products.json').read_text('utf8'));new=json.loads((R/'club_season_products.json').read_text('utf8'))
 for section in old:
  if section=='hash':continue
  if isinstance(old[section],dict):assert all(new[section][k]==v for k,v in old[section].items())
  else:assert new[section]==old[section]
 cases.append('Every existing product definition, price, pool and limit preserved')
 pool=[int(s) for s,w in h.pack_pool(RANDOM)];assert len(pool)==32 and set(pool)=={int(s) for s,w in h.pack_pool(CHOICE)}
 assert {w for s,w in h.pack_pool(RANDOM)}=={1/32}
 assert [(g,w) for g,w in h.pack_grades(RANDOM) if w]==[(8,50),(9,25),(10,15),(11,8),(12,2)]
 assert [(g,w) for g,w in h.pack_grades(CHOICE) if w]==[(8,1)]
 prices=json.loads((R/'price-proof.json').read_text('utf8'))
 assert all(h.product_price(i,1)==prices[str(i)]['price'] for i in (RANDOM,CHOICE))
 assert h.item_def(RANDOM)['category']=='PLAYERPACK' and h.item_def(CHOICE)['category']=='DRAFTPACK'
 assert h.item_def(CHOICE)['draft']==dict(season=327,grade=8,availables=1)
 assert all(h.item_def(i)['itemicon']==f'FO3N_{i}_V3' for i in (RANDOM,CHOICE))
 cases.append('Exact 32-card frozen pool, random +8..12 and choice +8, native categories/prices/icons')
 # Verify actual active hot shop renderer, not only the cold host listing.
 rows=json.loads(handlers['/shop/list'](RequestHost(h,{}),'',b'')[1]);available={r['product']['itemid']:r for r in rows}
 assert all(i in available and available[i]['buy'] for i in (RANDOM,CHOICE))
 cases.append('Both products visible and purchasable through current hot shop renderer')
 for i,row in available.items():
  if i not in h.PACKS:continue
  seasons={s//1000000 for s,w in h.pack_pool(i)}
  if seasons!={84}:assert min(g for g,w in h.pack_grades(i) if w)>=8,(i,h.item_def(i)['name'])
 cases.append('Every visible on-sale player pack is +8 minimum except pure moments')
 for old,newid in json.loads((R/'upgrade-mapping.json').read_text('utf8')).items():
  assert int(old) not in available and newid in h.PACKS
  a=dict(h.pack_pool(int(old)));b=dict(h.pack_pool(newid));assert a.keys()==b.keys()
  ta=sum(a.values());tb=sum(b.values());assert all(abs(a[s]/ta-b[s]/tb)<1e-12 for s in a)
 cases.append('All retired low-pack player probabilities preserved in new SKU; old inventory definitions retained')
 for i in (RANDOM,CHOICE):
  state=copy.deepcopy(base);saves=0;before=h.my_coach(state)['cash']
  result=json.loads(handlers['/shop/purchase'](RequestHost(h,{}),'',json.dumps(dict(shopid=i,productid=i,bunch=0)).encode())[1])
  assert result['result'],result
  assert h.my_coach(state)['cash']==before-h.product_price(i,1) and saves==1
  assert sum(r['remains'] for r in h.my_coach(state)['items'] if r['itemid']==i)==1
  cases.append('Native atomic point purchase '+str(i))
  empty=copy.deepcopy(base);h.my_coach(empty)['cash']=0;state=empty;saves=0;snapshot=copy.deepcopy(state)
  result=json.loads(handlers['/shop/purchase'](RequestHost(h,{}),'',json.dumps(dict(shopid=i,productid=i,bunch=0)).encode())[1])
  assert not result['result'] and state==snapshot and saves==0
  cases.append('Insufficient point purchase retains assets '+str(i))
 for s in pool:
  token=reset(CHOICE);before=copy.deepcopy(state)
  choices=next(fn for p,fn in h.ROUTES if p.pattern==r'/item/draftpack/(\d+)/players/(\d+)')
  assert json.loads(choices(str(CHOICE),'1','',b'')[1])==[] and state==before and saves==0
  assert len(json.loads(choices(str(CHOICE),'2','',b'')[1]))==32
  out=call(token,dict(spids=[s]));assert out['result'] and out['player']['spid']==s and out['player']['grade']==8 and saves==1
  card=state['teams'][str(slot)]['players'][0];assert h.player_levelinfo(card)['level']==1
  replay=call(token,dict(spids=[s]));assert replay['result'] and replay['replayed'] and saves==1 and len(state['teams'][str(slot)]['players'])==1
  assert not call(token,dict(spids=[next(x for x in pool if x!=s)]))['result'] and saves==1
  cases.append('Choice, cancel and idempotent replay '+str(s))
 for req in [dict(spids=[]),dict(spids=[1]),dict(spids=pool[:2]),dict(spids=[True])]:
  token=reset(CHOICE);snapshot=copy.deepcopy(state);assert not call(token,req)['result'] and state==snapshot and saves==0
 cases.append('Forged, multiple and invalid selections cannot consume or issue')
 token=reset(CHOICE);snapshot=copy.deepcopy(state);assert not call(token+'tamper',dict(spids=[pool[0]]))['result'] and state==snapshot and saves==0
 token=reset(CHOICE,1,0);snapshot=copy.deepcopy(state);assert not call(token,dict(spids=[pool[0]]))['result'] and state==snapshot and saves==0
 cases.append('Tampered inventory token and full roster rejected')
 token=reset(RANDOM,7);req=dict(bulk=True,requestId='china-future-bulk-001',expectedRemains=7)
 out=call(token,req);assert out['result'] and out['opened']==7 and saves==1 and all(p['spid'] in pool and 8<=p['grade']<=12 for p in out['players'])
 assert call(token,req)['replayed'] and saves==1
 cases.append('Existing hot bulk random open and replay remain supported')
 token=reset(CHOICE,3);snapshot=copy.deepcopy(state);assert not call(token,dict(bulk=True,requestId='china-choice-bulk-01',expectedRemains=3))['result'] and state==snapshot
 cases.append('Choice pack cannot enter bulk random opening')
 token=reset(CHOICE);snapshot=copy.deepcopy(state);old_save=h._save
 h._save=lambda st:(_ for _ in ()).throw(OSError('Synthetic atomic save failure'))
 try:call(token,dict(spids=[pool[0]]))
 except OSError:pass
 else:raise AssertionError('Synthetic save failure swallowed')
 finally:h._save=old_save
 assert state==snapshot and saves==0
 cases.append('Save failure keeps both inventory and card assets unchanged')
 token=reset(CHOICE);outputs=[]
 ts=[threading.Thread(target=lambda:outputs.append(call(token,dict(spids=[pool[0]])))) for _ in range(6)]
 for t in ts:t.start()
 for t in ts:t.join()
 assert len(outputs)==6 and all(o['result'] for o in outputs) and saves==1 and len(state['teams'][str(slot)]['players'])==1
 cases.append('Concurrent repeated selection issues exactly one card and saves once')
 report=dict(status='PASS',case_count=len(cases),cases=cases,real_assets_written=False,services_started=False,native_gui_verified=False,random_price=h.product_price(RANDOM,1),choice_price=h.product_price(CHOICE,1))
 (R/'tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');print(json.dumps(report))
finally:host.close()
