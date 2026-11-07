from pathlib import Path
import sys,os,json,hashlib,importlib.util
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
os.environ.update(FO3_LANGUAGE='chi',FO3_MAX_GRADE='20');sys.dont_write_bytecode=True;sys.path.insert(0,str(S))
def audit(event,args):
 if event=='open' and isinstance(args[0],str) and Path(args[0]).name in ('state.json','shop.json') and args[2]&(0x1|0x2|0x40|0x200):raise RuntimeError('Protected asset write')
sys.addaudithook(audit)
import http_config as h
rows=json.loads((R/'catalogue.json').read_text('utf8'));manifest=json.loads((R/'all_item_icon_manifest.json').read_text('utf8'))
def strip(v):
 if isinstance(v,list):return [strip(x) for x in v]
 if isinstance(v,dict):return {k:strip(x) for k,x in v.items() if k not in ('itemicon','bundleicon')}
 return v
before={r['id']:strip(h.item_def(r['id'])) for r in rows}
state=h._state();before_shop=strip(h.shop_list(state));before_inv={}
for c in state['coaches']:
 for where in ('items','depot'):before_inv[c['slot'],where]=strip(h.coach_items(state,c['slot'],where))
h.apply_shop()
spec=importlib.util.spec_from_file_location('icon_verify',R/'all_item_icons.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.install(h,manifest,R/'native')
for r in rows:
 d=h.item_def(r['id']);assert strip(d)==before[r['id']],r['id'];assert d['itemicon']==manifest['items'][str(r['id'])]['icon'];assert d['bundleicon']==d['itemicon']
h.apply_shop()
after_shop=strip(h.shop_list(state))
if after_shop!=before_shop:
 (R/'shop-before.json').write_text(json.dumps(before_shop,ensure_ascii=False,indent=2),encoding='utf8');(R/'shop-after.json').write_text(json.dumps(after_shop,ensure_ascii=False,indent=2),encoding='utf8')
assert after_shop==before_shop
for c in state['coaches']:
 for where in ('items','depot'):assert strip(h.coach_items(state,c['slot'],where))==before_inv[c['slot'],where]
# Exercise actual protocol handler, including protection service and nested lottery prizes.
h.apply_shop()
body=json.dumps(dict(itemids=[r['id'] for r in rows])).encode();data=json.loads(h.ENDPOINTS['/static/cache/item']('',body)[1])
checked=0
def walk(v):
 global checked
 if isinstance(v,list):
  for x in v:walk(x)
 if isinstance(v,dict):
  if 'itemicon' in v:
   i=str(v.get('itemid',v.get('productid')))
   if i in manifest['items']:assert v['itemicon']==manifest['items'][i]['icon'],(i,v['itemicon']);checked+=1
  for x in v.values():walk(x)
walk(data);walk(h.shop_list(state))
report=dict(status='PASS',definitions_unchanged_except_icons=len(rows),unique_images=len(set(x['sha256'] for x in manifest['items'].values())),static_api_definitions=len(data),nested_icon_checks=checked,shop_protocol_unchanged=True,live_inventory_unchanged=True,state_shop_written=False,native_status='PENDING')
(R/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
