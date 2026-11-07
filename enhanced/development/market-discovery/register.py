from pathlib import Path
import importlib.util,json,hashlib
server=Path('D:/FO3ID/server');backup=server/'backups/market-discovery-20261106-190554';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parent_name='patches/product_packs_preflight.py'
spec=importlib.util.spec_from_file_location('discovery_parent',server/parent_name);p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
c,v=p._compose(server,'D:/FO3ID/32795');guards=v.table(c['guards'])
source=(server/'patches/market_background_preflight.py').read_text('utf8')
source=source.replace('compact_currency_preflight.py','product_packs_preflight.py').replace('compact-currency-release','product-packs-release').replace('market_background_preflight.py','market_discovery_preflight.py').replace('market-background-release','market-discovery-release').replace('MARKET_BACKGROUND','MARKET_DISCOVERY').replace("'http_config.py', ", '').replace("'market-background'", "'market-discovery'")
(server/'patches/market_discovery_preflight.py').write_text(source,'utf8')
launcher=server/'play-local.bat';raw=launcher.read_bytes();assert b'patches\\product_packs_preflight.py' in raw
launcher.write_bytes(raw.replace(b'patches\\product_packs_preflight.py',b'patches\\market_discovery_preflight.py'))
files=[]
for name in ('market_simulation.py','play-local.bat','patches/market_discovery_preflight.py'):
 old=guards.get(('server',name),{}).get('sha256')
 if not name.startswith('patches/'):assert old==sha(backup/name),name
 files.append(dict(root='server',relative=name,parent_sha256=old,sha256=sha(server/name)))
m=dict(release_id='market-discovery-20261106',phase='MARKET_DISCOVERY_WORKER',client_root='D:/FO3ID/32795',state_shop_replaced=False,parent_files={name:sha(server/name) for name in (parent_name,'patches/product-packs-release-manifest.json','patches/product-packs-release-installed.json')},files=files)
manifest=server/'patches/market-discovery-release-manifest.json';manifest.write_text(json.dumps(m,indent=2),'utf8')
(server/'patches/market-discovery-release-installed.json').write_text(json.dumps(dict(release_id=m['release_id'],status='INSTALLED_MARKET_DISCOVERY',manifest_sha256=sha(manifest),backup=str(backup),native_status='NOT_VERIFIED'),indent=2),'utf8')
compile((server/'market_simulation.py').read_text('utf8'),'market_simulation.py','exec')
