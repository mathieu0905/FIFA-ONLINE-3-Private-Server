from pathlib import Path
import importlib.util,json,ssl,sys,urllib.parse,urllib.request
sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
spec=importlib.util.spec_from_file_location('wk_check',S/'patches/wonderkid_preflight.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
proof=gate.preflight(S,C)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(path,sql=None):
    data=json.dumps({'sql':sql}).encode() if sql else None
    with opener.open(urllib.request.Request(path,data=data,headers={'Content-Type':'application/json'}),timeout=15) as r:return json.load(r)
base='https://127.0.0.1';roster=get(base+'/static/roster');assert sum(18 in r.get('value',[]) for r in roster['seasons'])==1
rows=get(base+'/static/sql/fifadb','select spid,teamid,leagueid,overallrating from players where spid/1000000=18')
assert len(rows)==40 and all(r['teamid']==999918 and r['leagueid']==2028 and 90<=r['overallrating']<=94 for r in rows)
teams={}
for lang in ('chi','eng','ind','kor','tha','vie'):
    teams[lang]=get(base+'/static/sql/'+lang,'select teamname from team where teamid=999918')
    assert teams[lang]==[{'teamname':'神童' if lang=='chi' else 'Wonderkids'}]
cards=json.loads((R/'install-build-v3/cards.json').read_text('utf-8'));prices=[]
for c in cards:
    p=get('http://127.0.0.1:8088/api/market_price_store?spid='+str(c['fo3_spid'])+'&grade=1')
    assert p['initial_price']>0 and p['current_price']>0 and p['value']>0 and p['runtime_model_loaded'] is False;prices.append(p)
search=get('http://127.0.0.1:8088/api/search?'+urllib.parse.urlencode({'q':'帕托'}))
assert any(p['spid']==18180175 for p in search['rows'])
out=dict(status='PASS',preflight=proof,live_api_cards=40,live_locale_teams=teams,live_price_cards=len(prices),chinese_alias_search=True,real_purchases_performed=False,gui_used=False,native_verified=False,match_verified=False)
(R/'formal-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(out,ensure_ascii=False))
