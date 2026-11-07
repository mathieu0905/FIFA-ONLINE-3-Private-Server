from pathlib import Path
import hashlib, importlib.util, json, ssl, urllib.request
SERVER=Path('D:/FO3ID/server');OUT=Path('D:/fifaol3/releases/fc13-retire-ronaldinho-v2')
read=lambda p:json.loads(p.read_text('utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(url):
    with opener.open(url,timeout=20) as response:return response.read()
before=read(SERVER/'gamedata/state.json')
registry=json.loads(get('http://127.0.0.1:8088/api/roster_custom_cards'))
assert len(registry['cards'])==503
fc=next(s for s in registry['seasons'] if s['id']==13)
assert fc['label']=='现役精选' and len(fc['cards'])==257 and 13028130 not in fc['cards']
assert {12028130,84028130}<={r['fo3_spid'] for r in registry['cards']}
rows=json.loads(get('https://127.0.0.1/transfer/search/13028130'))
assert not rows, rows
rules=json.loads(get('https://127.0.0.1/info/player/level_rules'))
assert rules.get('max_level')==30 or rules.get('maxlevel')==30 or rules.get('max')==30
remote=get('https://127.0.0.1/cdn/externalAssets/language_chi.big')
assert hashlib.sha256(remote).hexdigest()==sha(OUT/'language_chi.big')
after=read(SERVER/'gamedata/state.json')
def assets(st):return {k:v for k,v in st.items() if k!='market_simulation'}
assert assets(before)==assets(after)
protected=read(OUT/'installation-PASS.json')['protected_hashes']
for name in ('gamedata/shop.json','gamedata/pack_cadence.json','gamedata/pack_catalogue.json','gamedata/fifadb.sqlite'):
    assert sha(SERVER/name)==protected[name]
spec=importlib.util.spec_from_file_location('fc_final_preflight',SERVER/'patches/fc_retirement_preflight.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
check=module.preflight()
report=dict(status='INSTALLED_LIVE_PROTOCOL_PASS_NATIVE_PENDING',active_fc_cards=257,active_registry_cards=503,
    season_name=fc['label'],ronaldinho_npc_offers=0,legend_cards_preserved=True,legacy_pack_pools_preserved=True,
    assets_preserved=True,cdn_language_hash_verified=True,preflight=check,native_verified=False)
(OUT/'live-PASS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='preflight'},ensure_ascii=True))
