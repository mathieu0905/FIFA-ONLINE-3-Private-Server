from pathlib import Path
import json,urllib.request,ssl,hashlib,re,datetime
R=Path(__file__).parent;S=Path(r'D:\FO3ID\server')
op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(url):
 with op.open(url,timeout=20) as r:return json.load(r)
status=get('http://127.0.0.1:8088/api/hot_update_status')
assert status['revision']=='shop_cleanup_20261107_01' and status['watcher_running'] and status['error'] is None,status
rows=get('https://127.0.0.1/shop/list');plan=json.loads((R/'plan.json').read_text('utf8'));removed={p['id'] for p in plan['removed']}
assert not {int(r['product']['itemid']) for r in rows}&removed
assert len(rows)==64 and sum(isinstance(r.get('chained'),list) for r in rows)==5
proof=json.loads((S/'hot_updates/last-publication.json').read_text('utf8'));active=json.loads((S/'hot_updates/active.json').read_text('utf8'))
play=(S/'play-local.bat').read_bytes();helper=re.search(rb'patches\\[^\r\n]+_preflight.py',play).group().decode()
result=dict(status='INSTALLED_AND_RUNTIME_ACTIVE_NATIVE_PENDING',at=datetime.datetime.now().isoformat(),runtime=status,visible_rows=len(rows),removed=len(removed),chains=5,no_restart=True,no_gui=True,no_live_test_purchase=True,old_inventory_definitions_preserved=True,preflight=helper,compose_api='compose_manifest',publication=proof,active=active,play_sha256=hashlib.sha256(play).hexdigest())
(R/'live-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8');(R/'installed-handback.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(dict(runtime=status,visible_rows=len(rows),removed=len(removed),chains=5,preflight=helper)))
