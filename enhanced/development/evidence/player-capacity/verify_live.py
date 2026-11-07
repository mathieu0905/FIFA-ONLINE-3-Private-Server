from pathlib import Path
import json,hashlib,ast,copy,requests,urllib3,importlib.util
urllib3.disable_warnings();S=Path('D:/FO3ID/server');O=Path(__file__).parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
inst=json.loads((O/'installation.json').read_text('utf8'));backup=Path(inst['backup'])
old=ast.parse((backup/'0.backup').read_text('utf-8-sig'));new=ast.parse((S/'http_config.py').read_text('utf-8-sig'))
assign=next(n for n in old.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MAX_PLAYERS' for t in n.targets))
assert assign.value.value==200;assign.value.value=2147483647
assert ast.dump(old)==ast.dump(new),'Unrelated source AST changed'
api=requests.get('https://127.0.0.1/coach/me',verify=False,timeout=5);assert api.status_code==200
limits=api.json()['limits'];assert all(limits[k]==2147483647 for k in ('players','baseplayers','firstTeam'))
before=json.loads((O/'state-before-reload.json').read_text('utf8'));after=json.loads((S/'gamedata/state.json').read_text('utf8'))
changed=[k for k in set(before)|set(after) if before.get(k)!=after.get(k)]
assert before['coaches']==after['coaches'] and before['teams']==after['teams'],changed
assert all(k=='market_simulation' for k in changed),changed
assert sha(O/'shop-before-reload.json')==sha(S/'gamedata/shop.json')
helper=S/'patches/player_capacity_preflight.py';spec=importlib.util.spec_from_file_location('capacity_gate',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);gate=m.preflight(S,Path('D:/FO3ID/32795'))
paths=[helper,S/'patches/player-capacity-installed.json',S/'patches/player-capacity-receipt.json',S/'play-local.bat',S/'http_config.py']
r=dict(status='INSTALLED_LIVE_PLAYER_CAPACITY_PASS',previous_limit=200,client_compatible_capacity=2147483647,limits=limits,api_status=api.status_code,preflight=gate,parent=json.loads((S/'patches/player-capacity-installed.json').read_text('utf8'))['parent'],source_ast_only_max_players_changed=True,coaches_unchanged=True,teams_unchanged=True,shop_byte_unchanged=True,state_changed_fields=changed,backup=str(backup),native_over200_verified=False,real_test_cards_added=False,services_restarted=True,game_started=False,API='compose_manifest(server=None,client=None); preflight(server=None,client=None)',hashes={str(p):sha(p) for p in paths})
(O/'handback.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),'utf8');print(json.dumps(r,indent=2))
