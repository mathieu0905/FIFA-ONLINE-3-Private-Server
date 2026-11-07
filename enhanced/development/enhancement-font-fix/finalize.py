from pathlib import Path
import json,subprocess,re
import install as d
W=d.W;S=d.S;C=d.C
result=d.tx.read(W/'installed-handback.json')
hot=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'hot_update_control.py')],cwd=S,capture_output=True,text=True,check=True)
status=json.loads(hot.stdout)
assert status['watcher_running'] and status['error'] is None
with d.locks():
 play=(S/'play-local.bat').read_bytes()
 actual='patches/'+re.search(rb'patches\\([A-Za-z0-9_]+_preflight\.py)',play).group(1).decode()
 assert actual==d.SELF,'A later legitimate layer is present; retain its descriptor'
 for relative,digest in result['source_hashes'].items():
  root,rel=relative.split('/',1)
  assert d.tx.sha((S if root=='server' else C)/rel)==digest
 result.update(top_preflight=str(S/d.SELF),top_manifest=str(S/d.MANIFEST),top_receipt=str(S/d.RECEIPT),
  composition_api='compose_manifest(server=None,client=None)',state_shop_written=False,
  final_hot_status=status,services_action='No service stop/start/restart',native_verified=False)
 d.tx.atomic_json(W/'installed-handback.json',result)
 d.tx.atomic_json(Path(r'D:\fifaol3\root-current-top.json'),result)
 pending=d.tx.read(W/'pending-handback.json');pending.update(status='FORMAL_RESOURCES_INSTALLED',formal_files_written=True,game_pid=None,installed_handback=str(W/'installed-handback.json'))
 d.tx.atomic_json(W/'pending-handback.json',pending)
print(json.dumps(dict(status=result['status'],hot_update=status,top=actual,files=result['preflight']['files'])))

