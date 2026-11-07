from pathlib import Path
import sys,os,json,copy,types,hashlib
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');sys.path.insert(0,str(S));sys.dont_write_bytecode=True;os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi')
def audit(event,args):
 if event=='open' and isinstance(args[0],str) and Path(args[0]).name in ('state.json','shop.json') and args[2]&(0x1|0x2|0x40|0x200):raise RuntimeError('Protected asset write prohibited')
sys.addaudithook(audit)
p=types.ModuleType('product_packs');p.__file__=str(R/'product_packs.py');exec(compile((R/'product_packs.py').read_bytes(),p.__file__,'exec'),p.__dict__);sys.modules['product_packs']=p
import http_config as h
original=h._state();unchanged=json.dumps(original,sort_keys=True);cfg=h.product_packs;retired=set(cfg.get('retired_chains',[]));active=[int(i) for i in cfg['chains'] if int(i) not in retired]
checks=0
for root in active:
 for roundnum in (0,3,9):
  for stage in range(5):
   st=copy.deepcopy(original);c=h.my_coach(st);st.setdefault('product_chain_rounds',{})[str(root)]={'rounds':roundnum,'stage':stage,'owner':str(c['_id']),'owner_appat':c.get('appat')}
   row=h.chained_entry(st,root);parts=[row]+row['chained'];assert row['step']==stage
   for index,part in enumerate(parts):
    assert bool(part['chained']),('No native chained marker',root,index)
    assert part['currentstep']==('complete' if index<stage else 'activity' if index==stage else 'default')
    assert part['product']['itemid']==cfg['chains'][str(root)]['round_steps'][roundnum][index]
    checks+=1
assert json.dumps(original,sort_keys=True)==unchanged

chain_ids={int(i) for track in cfg['chains'].values() for rr in track['round_steps'] for i in rr}
listing_checks=0
for call in (lambda:h.shop_list(copy.deepcopy(original)),lambda:json.loads(h.from_file('/shop/list')[1]),lambda:json.loads(h.ENDPOINTS['/shop/list']('',b'')[1]),lambda:h.shop_list(copy.deepcopy(original))):
 rows=call();roots=[r for r in rows if isinstance(r.get('chained'),list)]
 assert {r['shopid'] for r in roots}==set(active)
 for r in rows:
  iid=int(r['product']['itemid'])
  if iid in chain_ids:assert isinstance(r.get('chained'),list) and r['shopcategory']=='CHAINED'
  if r.get('shopcategory')=='PACKAGE':assert iid not in chain_ids
 listing_checks+=1

result=dict(listing_checks=listing_checks,no_chain_stages_in_package=True,all_five_chains_preserved=True,status='PASS',active_chains=len(active),native_stage_checks=checks,in_memory_only=True,real_purchase_executed=False,state_shop_written=False)
(R/'server-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
