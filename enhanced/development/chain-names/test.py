from pathlib import Path
import sys,os,json,copy,ast,hashlib
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');sys.path.insert(0,str(S));sys.dont_write_bytecode=True;os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi')
def guard(event,args):
 if event=='open' and isinstance(args[0],str) and Path(args[0]).name in ('state.json','shop.json') and args[2]&0x243:raise RuntimeError('Real asset write blocked')
sys.addaudithook(guard)
import market_price_store
market_price_store.MarketPriceStore.flush=lambda s,e:0
import http_config as h
from hot_update_runtime import compile_handlers
build=json.loads((R/'build.json').read_text('utf8'));old_source=(R/'before-business.py').read_bytes();new_source=(R/'business.py').read_bytes()
old=compile_handlers(old_source,'before',build['routes'],allow_templates=True);new=compile_handlers(new_source,'after',build['routes'],allow_templates=True)
ons=old['/shop/list'].__globals__;nns=new['/shop/list'].__globals__
def strip(value):
 if isinstance(value,dict):return {k:strip(v) for k,v in value.items() if k not in ('name','label','description')}
 if isinstance(value,list):return [strip(x) for x in value]
 return value
assert strip(ons['volume_data']())==strip(nns['volume_data']())
def functions(src):return {x.name:x for x in ast.parse(src).body if isinstance(x,ast.FunctionDef)}
of=functions(old_source);nf=functions(new_source)
for name in of:
 if name not in ('volume_data','volume_engine','clean_pack_definition'):assert ast.dump(of[name])==ast.dump(nf[name]),name
oi={x.name:x for x in of['volume_engine'].body if isinstance(x,ast.FunctionDef)};ni={x.name:x for x in nf['volume_engine'].body if isinstance(x,ast.FunctionDef)}
for name in oi:
 if name not in ('definition','chain_entry'):assert ast.dump(oi[name])==ast.dump(ni[name]),name
st=copy.deepcopy(h._state());st['product_chain_rounds']={};h._state=lambda:st;h._save=lambda st:(_ for _ in ()).throw(AssertionError('Unexpected save'))
rows_before=json.loads(old['/shop/list'](h,'',b'')[1]);rows_after=json.loads(new['/shop/list'](h,'',b'')[1]);before_roots={r['shopid']:r for r in rows_before if isinstance(r.get('chained'),list)};after_roots={r['shopid']:r for r in rows_after if isinstance(r.get('chained'),list)}
assert set(before_roots)==set(after_roots)
for root,row in after_roots.items():
 before=before_roots[root];assert row['round_buy_total']==before['round_buy_total']
 for a,b in zip([before]+before['chained'],[row]+row['chained']):
  ad=a['product']['staticdata'];bd=b['product']['staticdata']
  assert ad['bunches']==bd['bunches']
  assert [(i['itemid'],i['count']) for i in ad['items']]==[(i['itemid'],i['count']) for i in bd['items']]
  for child in bd['items']:
   old_def=h.item_def(child['itemid']);clean=child['staticdata'];assert clean['category']==old_def['category']
   assert {k:v for k,v in clean.items() if k not in ('name','description')}=={k:v for k,v in old_def.items() if k not in ('name','description')}
 old_q=ons['volume_engine'](h)['snapshot'](st,root);new_q=nns['volume_engine'](h)['snapshot'](st,root);assert old_q==new_q
 old_signer=ons['volume_engine'](h)['quote'];quote=json.loads(old_signer('root='+str(root),b'')[1])['quote']
 before_cash=h.my_coach(st).get('cash',0);h.my_coach(st)['cash']=0
 # A previously signed quote still reaches the normal funds check, rather than
 # becoming stale due to this text-only release.
 response=json.loads(new['/shop/chain/round/purchase'](h,'',json.dumps(dict(quote=quote)).encode())[1]);assert not response['result'] and '点券不足' in response['message'],response
 h.my_coach(st)['cash']=before_cash
 message=json.loads(new['/shop/chain/round/quote'](h,'root='+str(root),b'')[1])['message']
 for text in ('臻选新期','BP统一价','终极盛宴','海量抽卡','豪华补给','抽卡版','印记','神兽'):
  assert text not in json.dumps(row,ensure_ascii=False) and text not in message,text
 assert [p['product']['staticdata']['name'] for p in [row]+row['chained']]==[json.loads((R/'build.json').read_text('utf8'))['titles'][str(root)]]*5
# Historical paid stages retain their actual original quantities and categories.
root=71350101;st['product_chain_rounds'][str(root)]=dict(rounds=0,stage=2,owner=None)
row=next(r for r in json.loads(new['/shop/list'](h,'',b'')[1]) if r['shopid']==root)
assert row['product']['staticdata']['name']==build['titles'][str(root)]
assert sum(i['count'] for i in row['product']['staticdata']['items'])==2
assert '臻选新期' not in json.dumps(row,ensure_ascii=False)
# Read-only request-local construction must not change the live catalogue.
cfg=copy.deepcopy(h.product_packs);packages=copy.deepcopy(h.PACKAGES);nns['volume_engine'](h);assert h.product_packs==cfg and h.PACKAGES==packages
report=dict(status='PASS',source_sha256=hashlib.sha256(new_source).hexdigest(),chain_titles=[r['chainedproductname'] for r in after_roots.values()],sample_pack_names=[i['staticdata']['name'] for r in after_roots.values() for p in [r]+r['chained'] for i in p['product']['staticdata']['items']],checks=['250 stage quantities and all prices unchanged','purchase, signatures, receipt and other hot functions AST unchanged','all five chain names, tier labels, nested reward names and quote messages clean','old pending quote retains normal validation','historical purchased contents retained','host catalogue unchanged','existing market supply route preserved'],real_assets_written=False,native_verified=False)
(R/'tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k!='sample_pack_names'},ensure_ascii=True))
