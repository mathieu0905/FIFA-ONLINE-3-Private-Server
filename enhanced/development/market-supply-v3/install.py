from pathlib import Path
import json,shutil,hashlib,datetime
root=Path('D:/fifaol3/market-supply-v3');backup=root/('install-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir()
servers=[Path('D:/FO3ID/server'),Path('D:/FO3QA/modern_player_integration_v2/private-servers/ggmu-bellingham-20261106-02')]
old='9a9e7a9124b31178df8e57624de79b47f508e2a1f3a5c5532e5d25fe2ab2a118'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records=[]
for i,server in enumerate(servers):
 p=server/'market_simulation.py';assert sha(p)==old,str(p)
 dest=backup/str(i);dest.mkdir()
 for name in ('market_simulation.py','gamedata/state.json','gamedata/shop.json'):
  source=server/name
  if source.exists():shutil.copyfile(source,dest/source.name)
 records.append({'server':str(server),'backup':str(dest),'old_sha256':sha(p),'assets':{name:sha(server/name) for name in ('gamedata/state.json','gamedata/shop.json','gamedata/fifadb.sqlite','http_config.py') if (server/name).exists()}})
for record in records:
 shutil.copyfile(root/'market_simulation.py',Path(record['server'])/'market_simulation.py')
 record['new_sha256']=sha(Path(record['server'])/'market_simulation.py')
 assert all(sha(Path(record['server'])/name)==digest for name,digest in record['assets'].items())
(root/'installation.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),'utf8')
print(backup)
