"""Read-only formal protocol checks. No purchase or inventory operation."""
from pathlib import Path
import importlib.util,json,re,ssl,sys,time,urllib.request
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
result=json.loads((R/'cutover-result.json').read_text('utf-8'));backup=Path(result['backup'])
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(path):
    with opener.open('https://127.0.0.1'+path,timeout=25) as response:
        assert response.status==200;return json.load(response)
start=time.perf_counter();rows=get('/shop/list');listing_ms=round((time.perf_counter()-start)*1000,2)
counts=get('/shop/remained/limited');byid={r['shopid']:r for r in rows};quota={r['shopid']:r for r in counts}
assert {71240101,97960011,97961011}<=byid.keys()
root=byid[71240101];parts=[root]+root['chained'];assert len(parts)==5
assert all(p['shopid']==71240101 and p['index']==k+1 for k,p in enumerate(parts))
assert quota[71240101]['step']==root['step'] and quota[71240101]['buy']==root['buy']
def cost(row):return row['product']['staticdata']['bunches'][0]['price']
prices=[cost(p) for p in parts];assert sum(prices)==93002
assert cost(byid[97961011])<prices[-1]<cost(byid[97960011])
assert '全账号永久' in byid[97961011]['product']['staticdata']['description']
state=json.loads((S/'gamedata/state.json').read_text('utf-8'));before=json.loads((backup/'audit-state.json').read_text('utf-8'))
assert state['coaches']==before['coaches'] and state['teams']==before['teams'],'Concurrent assets changed; preserve and review, do not restore'
assert (S/'gamedata/shop.json').read_bytes()==(backup/'audit-shop.json').read_bytes()
play=(S/'play-local.bat').read_text('utf-8');name=re.search(r'patches\\(\w+_preflight\.py)',play).group(1)
spec=importlib.util.spec_from_file_location('formal_current_preflight',S/'patches'/name);gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate);proof=gate.preflight(S,C)
report=dict(status='FORMAL_READ_ONLY_PROTOCOL_PASS',preflight=proof,listing_ms=listing_ms,chain_prices=prices,
 round_price=sum(prices),same_pack_prices=dict(once=cost(byid[97961011]),chain=prices[-1],ordinary=cost(byid[97960011])),
 all_stage_shopids_share_root=True,root_and_limited_cache_consistent=True,coaches_and_teams_exact=True,shop_exact=True,
 card_count=sum(len(t.get('players',[])) for t in state['teams'].values()),purchase_executed=False,native_verified=False)
(R/'formal-PASS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(report))
