from pathlib import Path
import json,subprocess,re
import install as d
W=d.W;S=d.S;C=d.C
result=d.tx.read(W/'installed-handback.json')
hot=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'hot_update_control.py')],cwd=S,capture_output=True,text=True,check=True)
status=json.loads(hot.stdout);assert status['watcher_running'] and status['error'] is None
with d.locks():
 actual='patches/'+re.search(rb'patches\\([A-Za-z0-9_]+_preflight\.py)',(S/'play-local.bat').read_bytes()).group(1).decode()
 assert actual==d.SELF,'Later legal layer retained; do not overwrite its descriptor'
 for relative,digest in result['source_hashes'].items():
  root,rel=relative.split('/',1);assert d.tx.sha((S if root=='server' else C)/rel)==digest
 result.update(final_hot_status=status,services_action='Guarded restart after fresh game-idle observation',native_verified=False,service_restart=True,no_service_restart=False)
 d.tx.atomic_json(W/'installed-handback.json',result);d.tx.atomic_json(Path(r'D:\fifaol3\root-current-top.json'),result)
 d.tx.atomic_json(W/'pending-handback.json',dict(status=result['status'],formal_files_written=True,service_restart=True,native_verified=False,installed_handback=str(W/'installed-handback.json')))
print(json.dumps(dict(status=result['status'],top=actual,hot_update=status,meta_hashes=result['meta_hashes'],source_hashes=result['source_hashes'])))
