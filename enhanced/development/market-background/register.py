from pathlib import Path
import importlib.util,json,hashlib,sys
sys.dont_write_bytecode=True
server=Path('D:/FO3ID/server');backup=server/'backups/market-background-20261106-184233';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('parent',server/'patches/compact_currency_preflight.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
c,v=p._compose(server,'D:/FO3ID/32795');g=v.table(c['guards'])
files=[]
for name in ('market_simulation.py','http_config.py','play-local.bat','patches/market_background_preflight.py'):
 old=g.get(('server',name),{}).get('sha256')
 if name in ('market_simulation.py','http_config.py','play-local.bat'):assert old==sha(backup/name),name
 files.append(dict(root='server',relative=name,parent_sha256=old,sha256=sha(server/name)))
m=dict(release_id='market-background-20261106',phase='MARKET_BACKGROUND_WORKER',client_root='D:/FO3ID/32795',state_shop_replaced=False,parent_files={name:sha(server/name) for name in ('patches/compact_currency_preflight.py','patches/compact-currency-release-manifest.json','patches/compact-currency-release-installed.json')},files=files)
manifest=server/'patches/market-background-release-manifest.json';manifest.write_text(json.dumps(m,indent=2),'utf8')
(server/'patches/market-background-release-installed.json').write_text(json.dumps(dict(release_id=m['release_id'],status='INSTALLED_MARKET_BACKGROUND',manifest_sha256=sha(manifest),backup=str(backup),native_status='NOT_VERIFIED'),indent=2),'utf8')
for name in ('market_simulation.py','http_config.py','patches/market_background_preflight.py'):compile((server/name).read_text('utf8'),name,'exec')
