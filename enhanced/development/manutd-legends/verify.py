"""Official read-only verification; never purchase, give cards or operate GUI."""
from pathlib import Path
import ast,collections,hashlib,json,sqlite3,ssl,urllib.request
from prepare import R,S,C,sha,write
from install import load,SELF
def read(p):return json.loads(Path(p).read_text('utf8'))
def get(path,admin=True,binary=False):
 base='http://127.0.0.1:8088' if admin else 'https://127.0.0.1'
 with urllib.request.urlopen(base+path,context=ssl._create_unverified_context(),timeout=30) as response:
  assert response.status==200;data=response.read();return data if binary else json.loads(data)
def fingerprint(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
out=Path(read(R/'latest-build.json')['path']);build=read(out/'build.json');wanted={c['fo3_spid'] for c in build['spec']['cards']}
installed=read(R/'installed-handback.json');proof=load(S/SELF,'mul_verify').preflight(S,C)
rows=get('/api/database_search?season=48&offset=0');assert rows['total']==41;assert {r['spid'] for r in rows['rows']}==wanted
details=[]
for c in build['spec']['cards']:
 detail=get('/api/database_detail?spid='+str(c['fo3_spid']));assert detail['row']==c['row'],c['name_en'];assert detail['ovr']+5==c['display_plus1_ovr'],(detail.get('ovr'),c['name_en'])
 details.append(dict(name=c['name_zh'],spid=c['fo3_spid'],display_level1_plus1=detail['ovr']+5,base_ovr=detail['ovr']))
registry=get('/api/roster_custom_cards');assert set(next(s for s in registry['seasons'] if s['id']==48)['cards'])==wanted
db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)
assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
assert db.execute('select count(*) from playerhistory').fetchone()[0]==47149
faces=0
for f in build['portraits']:
 if not f.get('missing'):
  data=get('/cdn/externalAssets/players/'+f['name'],False,True);assert data.startswith(b'\x89PNG') and hashlib.sha256(data).hexdigest()==f['sha256'];faces+=1
for p,h in installed['protected_hashes'].items():
 if Path(p).name!='state.json':assert sha(p)==h,('Protected file changed',p)
before=read(R/'fresh-stop-snapshot'/installed['revision']/'state.json');after=read(S/'gamedata/state.json')
assert {k:fingerprint(v) for k,v in before.items() if k!='market_simulation'}=={k:fingerprint(v) for k,v in after.items() if k!='market_simulation'},'Player assets changed'
cfg=read(S/'gamedata/manutd_legends_products.json');assert all(set(p['tiers'][0]['pool'])==wanted and p['grades']==[100] for p in cfg['strength_packs'].values())
product_checks=[]
listing=get('/shop/list',False)
for i in cfg['strength_packs']:
 request=urllib.request.Request('https://127.0.0.1/static/cache/item',data=json.dumps(dict(itemids=[int(i)])).encode(),headers={'Content-Type':'application/json'},method='POST')
 with urllib.request.urlopen(request,context=ssl._create_unverified_context(),timeout=30) as response:data=json.loads(response.read())
 assert data[i]['name']==cfg['strength_packs'][i]['name'],data
 assert '41' in data[i]['description'] and '88' in data[i]['description']
 found=[x for x in listing if x.get('product',{}).get('itemid')==int(i)]
 assert len(found)==1 and found[0]['buy'] is True,(i,found)
 product_checks.append(dict(id=i,response=data[i],listing=found[0]))
report=dict(status='LIVE_READ_ONLY_PASS',cards=41,new_cards=34,ratings=details,preflight=proof,portraits_served=faces,missing_existing_portraits=[f['name'] for f in build['portraits'] if f.get('missing')],history_rows=47149,player_assets_preserved=True,shop_unchanged=True,existing_pack_configs_unchanged=True,products=product_checks,native_verified=False,match_verified=False)
write(R/'verification.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ('ratings','products')},ensure_ascii=True))
