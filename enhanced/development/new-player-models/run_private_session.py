"""Run supervised, filesystem-guarded model QA services after explicit GUI handoff."""
from pathlib import Path
import json,sys,socket,subprocess,hashlib,time,os
R=Path(__file__).resolve().parent
handoff=json.loads((R/'coordination-gui.json').read_text('utf8'))
granted=handoff.get('ownership_status') in ['MODEL_WINDOW_GRANTED','MODEL_GUI_GRANTED','GUI_RETURNED_TO_MODEL_CHAT']
assert granted or handoff.get('model_chat_may_take_GUI_now') is True,'No explicit model GUI window'
assert granted or handoff.get('model_chat_may_switch_services_now') is True,'No explicit private-service switching window'
session=json.loads((R/'current-native-session.json').read_text('utf8'));P=Path(session['private_server']).resolve()
assert P.parent==Path('D:/FO3QA/modern_player_integration_v2/private-servers').resolve() and P.name.startswith('model9-main-')
meta=json.loads((P/'model-session.json').read_text('utf8'));S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert 'fifazf.exe' not in subprocess.check_output(['tasklist','/FO','CSV','/NH'],text=True).lower()
for port in [443,8088,28002]:
 with socket.socket() as s:assert s.connect_ex(('127.0.0.1',port))!=0,'Stop handed-back services first'
for rel,value in meta['production_code_hashes'].items():assert sha(S/rel)==value,'Production changed; fresh prepare needed: '+rel
for rel,value in meta['current_client_hashes'].items():assert sha(C/rel)==value,'Client changed; fresh prepare needed: '+rel
assert (P/'model-test-roster.json').is_file()
worker=Path('D:/FO3QA/modern_player_integration_v2/private_runtime_worker.py');procs=[]
try:
 for module in ['http_config','messenger']:
  procs.append(subprocess.Popen([sys.executable,'-B','-u',str(worker),'--server',str(P),'--module',module,'--allow-listeners'],cwd=P,env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONDONTWRITEBYTECODE':'1'}))
 print('Private model QA services active; production writes remain forbidden. Ctrl-C stops both workers.',flush=True)
 while all(p.poll() is None for p in procs):time.sleep(.5)
 raise RuntimeError('A model QA service exited')
except KeyboardInterrupt:pass
finally:
 for p in procs:
  if p.poll() is None:p.terminate()
 for p in procs:
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
