"""Verify installed reward definitions and read-only APIs without claiming rewards."""
import os,json,re,ssl,urllib.request,ast
os.environ['FO3_PRICE_AUDIT_AFTER']='1'
import audit_all_prices as a
import reward_upgrade as r
from prepare import S,C,sha,write
from product_packs import signature
h=a.h;data=json.loads((r.R/'build.json').read_text('utf8'));installed=json.loads((r.R/'installed.json').read_text('utf8'))
assert a.report['mismatches']==0 and a.report['total']==313
assert h.daily_table()==data['daily'] and h.ECONOMY['daily']==10000 and h.ECONOMY['match_daily_cap']==10000
for i,expected in data['contracts'].items():assert signature(dict(pool=h.pack_pool(int(i)),grades=h.pack_grades(int(i))))==expected
for i,price in data['stage_prices'].items():assert h.product_price(int(i),1)==price
assert sum(h.product_price(i,1) for i in h.product_packs['chains']['71350401']['steps'])==500000
def request(path,post=None,admin=False):
 base='http://127.0.0.1:8088' if admin else 'https://127.0.0.1';req=urllib.request.Request(base+path,data=None if post is None else json.dumps(post).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,context=ssl._create_unverified_context(),timeout=30) as response:assert response.status==200;return json.loads(response.read())
daily=request('/api/daily',admin=True);assert daily['table']==data['daily']
ids=[row['id'] for row in a.rows];definitions=request('/static/cache/item',dict(itemids=ids));assert set(map(int,definitions))==set(ids)
for row in a.rows:
 for option in definitions[str(row['id'])]['bunches']:assert option['price']==h.product_price(row['id'],option['bunch'])
listing=request('/shop/list');monthly=[]
for raw,expected in data['monthly'].items():
 i=int(raw);entries=[e for e in listing if e.get('product',{}).get('itemid')==i and e.get('visible')];assert len(entries)==1
 rule=h.product_packs['limits'][raw];assert rule==dict(count=1,period='month',scope='manager')
 assert h.pack_cadence.policy(i)==({},False)
 d=definitions[raw];assert d['name']==expected[0] and '每月1份' in d['description']
 assert [(x['itemid'],x['count']) for x in d['dailyitems']]==[tuple(x) for x in expected[4]]
 assert [(x['itemid'],x['count']) for x in d['items']]==[tuple(x) for x in expected[3]]
 assert h.product_price(i,1)==h.pack_value_quote(i,'once')
 monthly.append(dict(id=i,name=d['name'],price=h.product_price(i,1),remaining=entries[0]['remained'],days=30,expected_bp=h.pack_expected_value(i)))
for path,expected in installed['protected'].items():
 if not path.endswith('state.json'):assert sha(path)==expected
before=json.loads((r.R/'fresh-stop-snapshot'/installed['revision']/'state.json').read_text('utf8'));after=json.loads((S/'gamedata/state.json').read_text('utf8'))
assert {k:v for k,v in before.items() if k!='market_simulation'}=={k:v for k,v in after.items() if k!='market_simulation'},'Business progress changed'
entry=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',(S/'play-local.bat').read_bytes());assert len(entry)==1;proof=r.common.load(S/entry[0].decode().replace('\\','/'),'reward_verified').preflight(S,C)
result=dict(status='PASS',preflight=proof,daily_cash=10000,seven_day_table=data['daily'],match=data['match'],monthly=monthly,all_313_metadata_prices_verified=True,issued_pack_odds_exact=len(data['contracts']),chain_prices_exact=len(data['stage_prices']),reference_round=500000,actual_daily_or_monthly_claim_executed=False,assets_preserved=True,shop_preserved=True,native_verified=False)
write(r.R/'verification.json',result);print(json.dumps({k:v for k,v in result.items() if k!='seven_day_table'},ensure_ascii=True))
