"""Installed production prices, legacy contracts, assets and read-only HTTP checks."""
import os,sys,json,hashlib,ssl,urllib.request,re
from pathlib import Path
import bp_pricing as b
from prepare import S,C,sha,write
R=b.R
def audit(event,args):
 if event=='open':
  path,mode,flags=args
  if isinstance(path,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
   if not Path(os.fsdecode(path)).resolve().is_relative_to(R):raise PermissionError('Verification cannot write assets')
 if event=='socket.bind':raise PermissionError('Verification cannot start a server')
sys.addaudithook(audit)
os.environ.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0');sys.path.insert(0,str(S));sys.argv=['http_config.py']
import http_config as h
from product_packs import signature
report=json.loads((R/'build.json').read_text('utf8'));installed=json.loads((R/'installed.json').read_text('utf8'));cfg=json.loads((S/'gamedata/bp_expected_products.json').read_text('utf8'))
actual=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',(S/'play-local.bat').read_bytes());assert len(actual)==1
proof=b.common.load(S/actual[0].decode().replace('\\','/'),'bp_verified_gate').preflight(S,C)
for i,expected in report['issued_pack_contracts'].items():assert signature(dict(pool=h.pack_pool(int(i)),grades=h.pack_grades(int(i))))==expected,('Issued odds changed',i)
for i,price in report['old_chain_prices'].items():assert h.product_price(int(i),1)==price,('Legacy stage price changed',i)
for i,q in cfg['value_prices'].items():assert h.product_price(int(i),1)==q['price'],('Production price differs',i)
for root,t in cfg['chains'].items():
 for steps in t['round_steps']:
  assert sum(h.product_price(i,1) for i in steps)==sum(t['prices'][str(i)] for i in steps)
  if int(root)==71350401:assert sum(h.product_price(i,1) for i in steps)==500000
for i in (98248008,98248018):assert h.pack_grades(i)==[(g,0) for g in range(1,8)]+[(8,100)]
assert {97500048,98248001,98248002}<=set(h.product_packs['retired_sale_items'])
def get(path,post=None):
 req=urllib.request.Request('https://127.0.0.1'+path,data=None if post is None else json.dumps(post).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,context=ssl._create_unverified_context(),timeout=30) as r:assert r.status==200;return json.loads(r.read())
listing=get('/shop/list');items=get('/static/cache/item',dict(itemids=[97310084,98248008,98248018,97500048,98248001,98248002]));samples=[]
for i in (97310084,98248008,98248018):
 d=items[str(i)];price=cfg['value_prices'][str(i)]['price'];assert any(x['bunch']==1 and x['price']==price for x in d['bunches'])
 found=[r for r in listing if r.get('product',{}).get('itemid')==i and r.get('visible')];assert len(found)==1
 # Preserve a real manager's already-used weekly quota; never reset it to make
 # the test buyable. The button must reflect actual remaining allowance.
 assert found[0]['buy']==(found[0]['remained']>0)
 samples.append(dict(id=i,name=d['name'],price=price,expected_bp=cfg['value_prices'][str(i)]['expected_ep'],remaining=found[0]['remained']))
for i in (97500048,98248001,98248002):assert not any(r.get('product',{}).get('itemid')==i and r.get('visible') and r.get('buy') for r in listing)
quote=get('/shop/chain/round/quote?root=71350401');assert quote['result'] is True and quote['quote']['total']==500000
assert all(any(r.get('shopid')==int(root) for r in listing) for root in cfg['chains'])
for p,expected in installed['protected'].items():
 if Path(p).name!='state.json':assert sha(p)==expected,('Protected changed',p)
before=json.loads((R/'fresh-stop-snapshot'/installed['revision']/'state.json').read_text('utf8'));after=json.loads((S/'gamedata/state.json').read_text('utf8'))
business_before={k:v for k,v in before.items() if k!='market_simulation'};business_after={k:v for k,v in after.items() if k!='market_simulation'}
assert business_before==business_after,'Player business state changed after reload'
result=dict(status='PASS',preflight=proof,ratio=dict(ordinary_bp_per_point=report['bp_per_point'],reference_chain_effective_bp_per_point=report['reference_round_expected_bp']/500000,reference_round_expected_bp=report['reference_round_expected_bp'],reference_round_price=500000),samples=samples,priced_products=len(report['products']),new_chain_stages=sum(len(t['packages']) for t in cfg['chains'].values()),issued_pack_contracts_exact=len(report['issued_pack_contracts']),legacy_stage_prices_exact=len(report['old_chain_prices']),live_reference_quote=quote['quote']['total'],old_low_grade_MUL_not_buyable=True,player_assets_preserved=True,shop_preserved=True,client_exit_or_gui=False,native_verified=False)
write(R/'verification.json',result);print(json.dumps(result,ensure_ascii=True))
