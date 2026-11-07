"""Focused follow-up for request-local snapshot caching in the price adapter."""
import copy,json,hashlib
from pathlib import Path
import host
from hot_update_runtime import compile_handlers
R=host.R;h=host.h;source=(R/'business.py').read_bytes();meta=json.loads((R/'business-meta.json').read_text('utf8'));handlers=compile_handlers(source,'snapshot-cache',meta['routes'],allow_templates=True);ns=handlers['/shop/list'].__globals__
base=copy.deepcopy(h._state());base.pop('market_simulation',None)
for c in base['coaches']:
 for k in list(c):
  if k.endswith('_receipts'):c[k]={}
 c['items']=[];c['depot']=[];c['product_purchase_counts']={};c['cash_ledger']=[]
for t in base['teams'].values():t['players']=t.get('players',[])[:1]
base['product_purchase_counts']={};base['product_chain_rounds']={};box={'st':base};reads=[];saves=[]
def read():reads.append(True);return box['st']
def save(st):saves.append(True);box['st']=st
h._state=read;h._save=save;h.coach_me_resources=lambda st,slot:[]
data=ns['pricing_data']();view=ns['pricing_host'](h,data);n=len(reads);a=view._state();b=view._state();assert a is b and a is not box['st'] and len(reads)==n+1
a['snapshot_probe']='detached';assert 'snapshot_probe' not in box['st'];view._save(a);assert box['st'] is a and view._state() is a
def fresh():
 st=copy.deepcopy(base);box['st']=st;c=h.my_coach(st);c['cash']=10**9;return st,c
def call(path,req=None,query=''):return json.loads(handlers[path](h,query,b'' if req is None else json.dumps(req).encode())[1])
try:
 for itemid,bunch,count in ((98448082,0,1),(98448082,1,10),(98432702,0,1)):
  st,c=fresh();n=len(saves);out=call('/shop/purchase',dict(productid=itemid,bunch=bunch));assert out['result'],out
  assert len(saves)==n+1 and out['spent']==data['prices'][str(itemid)]*count
  c=h.my_coach(box['st']);assert c['cash']==10**9-out['spent'] and sum(x['remains'] for x in c['items'] if x['itemid']==itemid)==count
 st,c=fresh();before=copy.deepcopy(st);h._save=lambda st:(_ for _ in ()).throw(OSError('save failure'))
 try:call('/shop/purchase',dict(productid=98448082,bunch=0))
 except OSError:pass
 else:raise AssertionError('save error swallowed')
 assert box['st']==before;h._save=save
 # The same cached snapshot serves the staged transaction and its response.
 st,c=fresh();q=call('/shop/chain/round/quote',query='root=71350101')['quote'];n=len(saves);out=call('/shop/chain/round/purchase',dict(quote=q));assert out['result'] and len(saves)==n+1
 n=len(saves);again=call('/shop/chain/round/purchase',dict(quote=q));assert again['replayed'] and len(saves)==n
 for root,t in ns['volume_data']().items():
  st,c=fresh();st['product_chain_rounds'][root]=dict(rounds=0,stage=1,owner=None)
  row=next(r for r in call('/shop/list') if r['shopid']==int(root));assert row['product']['staticdata']['bunches']==h.item_def(t['steps'][0])['bunches']
 report=dict(status='PASS',source_sha256=hashlib.sha256(source).hexdigest(),checks=['one detached snapshot per request, refreshed after native save','one/ten/choice purchases retain price, grant, limit and single-save semantics','failed native save cannot change cached original state','bulk chain purchase and receipt replay','unversioned historical paid stage prices unchanged'],real_assets_written=False)
 (R/'snapshot-tests.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
finally:host.close()
