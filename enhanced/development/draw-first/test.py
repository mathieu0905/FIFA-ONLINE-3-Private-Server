from pathlib import Path
import sys,os,json,copy,importlib.util,importlib.abc,hashlib,collections
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
sys.path.insert(0,str(S));sys.dont_write_bytecode=True;os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi')
def guard(event,args):
 if event=='open' and isinstance(args[0],str) and Path(args[0]).name in ('state.json','shop.json') and args[2]&0x243:raise RuntimeError('Protected asset write')
sys.addaudithook(guard)
class Finder(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname in ('product_packs','draw_first'):return importlib.util.spec_from_file_location(fullname,R/(fullname+'.py'))
sys.meta_path.insert(0,Finder())
import market_price_store,all_item_icons
market_price_store.MarketPriceStore.flush=lambda self,events:0
all_item_icons.install=lambda h:None
import http_config as h
spec=json.loads((R/'draw_first_rules.json').read_text('utf8'));legacy=json.loads((R/'legacy.json').read_text('utf8'));mapping={int(k):v for k,v in spec['mapping'].items()}
st=copy.deepcopy(h._state());h._state=lambda:st;h._save=lambda value:None
for old,d in legacy['packs'].items():
 i=int(old);assert h.item_def(i)['category']==d['category']=='DRAFTPACK'
 assert [list(x) for x in h.pack_pool(i)]==d['pool'];assert [list(x) for x in h.pack_grades(i)]==d['grades']
 new=mapping[i];assert h.item_def(new)['category']=='PLAYERPACK'
 p=dict(h.pack_pool(new));q=dict(d['pool']);a=sum(p.values());b=sum(q.values())
 assert p.keys()==q.keys() and all(abs(p[s]/a-q[s]/b)<1e-12 for s in p)
 assert [list(x) for x in h.pack_grades(new) if x[1]>0]==[x for x in d['grades'] if x[1]>0]
for old,p in legacy['bundles'].items():assert [list(x) for x in h.PACKAGES[int(old)][2]]==p[2]
rows=h.shop_list(st);visible=[r for r in rows if r.get('visible',True) and not isinstance(r.get('chained'),list)]
assert not {int(r['product']['itemid']) for r in visible}&mapping.keys()
assert all(h.item_def(int(r['product']['itemid']))['category']!='DRAFTPACK' for r in visible)
active=set(map(int,h.product_packs['chains']))-set(h.product_packs.get('retired_chains',[]));count=0
for root in active:
 t=h.product_packs['chains'][str(root)]
 for p in t['packages'].values():
  assert all(h.item_def(i)['category']!='DRAFTPACK' for i,n in p['contents'])
  count+=sum(n for i,n in p['contents'])
assert len(active)==5
# Exercise actual product opening/receipt logic against a disposable state copy.
coach=h.my_coach(st);opened=0
runtime_spec=importlib.util.spec_from_file_location('draw_first_dynamic_runtime',R/'hot-v2/hot_update_runtime.py');runtime=importlib.util.module_from_spec(runtime_spec);runtime_spec.loader.exec_module(runtime)
route='/item/{item_id}/use'
fn=runtime.compile_handlers((R/'hot-v2/open_business.py').read_bytes(),'open_business.py',[dict(path=route,function='open_pack')],allow_templates=True)[route]
manager=runtime.Manager(h,R)
manager._handlers={route:lambda params:lambda query,body:fn(runtime.RequestHost(h,params),query,body)}
for raw in spec['packs']:
 i=int(raw);h.inventory_add(coach,i,1)
 inv=h.coach_items(st,h._default_slot(st))
 # Product adapter's opening ID is supplied by the inventory response.
 row=next(x for x in inv if int(x['itemid'])==i)
 token=str(row['_id'])
 handler=manager.handler('/item/'+token+'/use');assert handler is not None
 result=json.loads(handler('',b'{}')[1]);assert result.get('result'),(i,token,result)
 player=result['player'];assert int(player['spid']) in dict(h.pack_pool(i));assert int(player['grade']) in dict((g,w) for g,w in h.pack_grades(i) if w)
 again=json.loads(handler('',b'{}')[1]);assert again.get('replayed') and again['player']==player
 opened+=1
bulk=0
for root in active:
 st.setdefault('product_chain_rounds',{}).pop(str(root),None)
 coach['cash']=10**9
 quote=json.loads(h.ENDPOINTS['/shop/chain/round/quote']('root='+str(root),b'')[1])['quote']
 assert all(h.item_def(i)['category']!='DRAFTPACK' for i,n in quote['rewards'])
 before_cash=coach['cash'];before_counts=collections.Counter({x['itemid']:x['remains'] for x in coach.get('items',[])})
 request=json.dumps(dict(quote=quote)).encode()
 result=json.loads(h.ENDPOINTS['/shop/chain/round/purchase']('',request)[1]);assert result['result'],result
 assert coach['cash']==before_cash-quote['total']
 after_counts=collections.Counter({x['itemid']:x['remains'] for x in coach.get('items',[])})
 assert after_counts-before_counts==collections.Counter(dict(quote['rewards']))
 replay=json.loads(h.ENDPOINTS['/shop/chain/round/purchase']('',request)[1]);assert replay['replayed']
 assert coach['cash']==before_cash-quote['total'] and after_counts==collections.Counter({x['itemid']:x['remains'] for x in coach.get('items',[])})
 tampered=copy.deepcopy(quote);tampered['total']+=1
 assert not json.loads(h.ENDPOINTS['/shop/chain/round/purchase']('',json.dumps(dict(quote=tampered)).encode())[1])['result']
 bulk+=1
report=dict(status='PASS',new_random_packs=opened,opening_via_abi2_dynamic_routes=True,unchanged_old_choices=len(legacy['packs']),unchanged_old_bundles=len(legacy['bundles']),active_chains=len(active),chain_random_units=count,bulk_purchase_and_replay_checks=bulk,visible_choices=0,real_state_written=False,native_verified=False)
def icon_grades(i):
 if i in h.PACKS:return {g for g,w in h.pack_grades(i) if w>0}
 if i in h.PACKAGES:return set().union(*(icon_grades(child) for child,n in h.PACKAGES[i][2]))
 return set()
(R/'icon-rows.json').write_text(json.dumps([dict(id=i,kind='pack' if i in h.PACKS else 'package',definition=h.item_def(i),grades=sorted(icon_grades(i))) for i in list(mapping.values())+list(map(int,h.product_packs['chains']['71350501']['packages']))],ensure_ascii=False),encoding='utf8')
(R/'test-result.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))

