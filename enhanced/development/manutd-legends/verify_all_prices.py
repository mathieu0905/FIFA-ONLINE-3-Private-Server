"""Full installed coverage, quantity quotes, exact contracts and real HTTP metadata."""
import os,json,re,ssl,urllib.request,ast
os.environ['FO3_PRICE_AUDIT_AFTER']='1'
import audit_all_prices as a
import all_prices as p
from prepare import S,C,sha,write
from product_packs import signature
h=a.h;report=a.report;assert report['total']==313 and report['mismatches']==0
before=json.loads((p.R/'build.json').read_text('utf8'));installed=json.loads((p.R/'installed.json').read_text('utf8'))
for i,fingerprint in before['contracts'].items():assert signature(dict(pool=h.pack_pool(int(i)),grades=h.pack_grades(int(i))))==fingerprint
for i,price in before['stage_prices'].items():assert h.product_price(int(i),1)==price
cfg=h.product_packs
reference=cfg['chains']['71350401']
for steps in reference['round_steps']:assert sum(h.product_price(i,1) for i in steps)==500000
def request(path,post=None):
 req=urllib.request.Request('https://127.0.0.1'+path,data=None if post is None else json.dumps(post).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,context=ssl._create_unverified_context(),timeout=30) as r:assert r.status==200;return json.loads(r.read())
ids=[r['id'] for r in report['rows'] if r['group']!='monthly'];data=request('/static/cache/item',dict(itemids=ids));assert set(map(int,data))==set(ids)
quantity_checks=0
for row in report['rows']:
 if row['group']=='monthly':continue
 d=data[str(row['id'])]
 for q in d.get('bunches',[]):assert q['price']==h.product_price(row['id'],q['bunch']);quantity_checks+=1
listing=request('/shop/list');monthly=0;archived_monthly=0
for i in h.MONTHLY:
 entries=[r for r in listing if r.get('product',{}).get('itemid')==i]
 if not entries:
  assert h.pack_cadence.policy(i)[1] is True,'Unexpectedly missing live monthly listing'
  for option in h.item_def(i)['bunches']:assert option['price']==h.product_price(i,option['bunch'])
  archived_monthly+=1;continue
 assert len(entries)==1
 for q in entries[0]['product']['staticdata']['bunches']:assert q['price']==h.product_price(i,q['bunch'])
 monthly+=1
q=request('/shop/chain/round/quote?root=71350401');assert q['result'] is True and q['quote']['total']==500000
for path,wanted in installed['protected'].items():
 if path.endswith('state.json'):continue
 assert sha(path)==wanted
state_before=json.loads((p.R/'fresh-stop-snapshot'/installed['revision']/'state.json').read_text('utf8'));state_after=json.loads((S/'gamedata/state.json').read_text('utf8'))
assert {k:v for k,v in state_before.items() if k!='market_simulation'}=={k:v for k,v in state_after.items() if k!='market_simulation'}
economy=ast.parse((S/'economy.py').read_text('utf8'))
assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='add_cash' and len(n.args)>1 and isinstance(n.args[1],ast.UnaryOp) and isinstance(n.args[1].op,ast.USub) and isinstance(n.args[1].operand,ast.Subscript) and isinstance(n.args[1].operand.slice,ast.Constant) and n.args[1].operand.slice.value=='price' for n in ast.walk(economy))
entry=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',(S/'play-local.bat').read_bytes());assert len(entry)==1;proof=p.common.load(S/entry[0].decode().replace('\\','/'),'all_prices_verified').preflight(S,C)
result=dict(status='PASS',groups=report['groups'],total=313,quote_mismatches=0,changed=before['changed'],http_definitions=len(data),quantity_quotes_checked=quantity_checks,monthly_live_listings=monthly,archived_monthly_metadata_checked=archived_monthly,all_issued_pool_grade_contracts_exact=len(before['contracts']),all_chain_stage_prices_exact=len(before['stage_prices']),reference_round=500000,purchase_uses_verified_definition_price=True,assets_preserved=True,shop_preserved=True,preflight=proof,native_verified=False)
write(p.R/'verification.json',result);print(json.dumps(result))
