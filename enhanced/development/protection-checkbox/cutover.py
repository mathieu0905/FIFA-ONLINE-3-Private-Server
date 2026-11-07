"""Coordinated official cutover; an active client defers before locks/writes."""
from pathlib import Path
import os,sys,json,re,time,subprocess,ssl,urllib.request
import install as d
W=d.W;S=d.S;C=d.C
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def call(uri):
 with opener.open('https://127.0.0.1'+uri,timeout=25) as response:return json.load(response)
def env():
 out=os.environ.copy();out.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20')
 out['PSModulePath']=os.path.expandvars(r'%SystemRoot%\System32\WindowsPowerShell\v1.0\Modules;%ProgramFiles%\WindowsPowerShell\Modules');return out
def stop():
 subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],env=env(),check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
 for _ in range(20):
  result=subprocess.run(['powershell.exe','-NoProfile','-Command','if(Get-NetTCPConnection -State Listen -LocalPort 443,8088,28002 -ErrorAction SilentlyContinue){exit 1}'],env=env(),creationflags=subprocess.CREATE_NO_WINDOW)
  if result.returncode==0:return
  time.sleep(.25)
 raise RuntimeError('Managed listeners have not stopped; no formal payload written')
def start():
 with (W/'formal.stdout.log').open('ab') as out,(W/'formal.stderr.log').open('ab') as err:
  p=subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-u',str(S/'start_all.py')],cwd=S,env=env(),stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
 ready=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'wait_services.py'),'--timeout','25'],cwd=S,env=env(),capture_output=True,text=True)
 if ready.returncode:raise RuntimeError('Readiness failed: '+ready.stdout+ready.stderr)
 return p.pid,ready.stdout.strip()
def main():
 if d.game_active():
  print(json.dumps(dict(status='DEFERRED',formal_files_written=False,service_actions=False,message='更新已延后，当前游戏继续运行'),ensure_ascii=True));return
 with d.locks():
  d.guard_closed();d.prepare();m=d.tx.read(W/'manifest.json');d.verify_parent(m)
  # A deferred/failed stop aborts here, without writes or a duplicate start.
  d.guard_closed();stop()
  state=(S/'gamedata/state.json').read_bytes();shop=(S/'gamedata/shop.json').read_bytes();error=None
  try:result=d.install(held=True)
  except BaseException as exc:error=exc
  actual='patches/'+re.search(rb'patches\\([A-Za-z0-9_]+_preflight\.py)',(S/'play-local.bat').read_bytes()).group(1).decode()
  proof=d.load(S/actual,'valid_protection_checkbox_top').preflight(S,C)
  pid,ready=start()
  if error:raise error
  assert d.business(d.tx.read(S/'gamedata/state.json'))==d.business(json.loads(state)),'New progress retained; never restore an old asset snapshot'
  assert (S/'gamedata/shop.json').read_bytes()==shop
  rules=call('/info/enhancement/protection/rules');assert rules['independent_checkbox'] and not rules['boost_item_exclusive']
  rejected=call('/player/000000000000000000000001/enhance2.5/000000000000000000000002/preview/0/-1/-1?protection=1')
  assert rejected['result'] and rejected['protection']['blocked'] and 'token' not in rejected['protection']
  backup=Path(result['backup']);(backup/'audit-state.json').write_bytes(state);(backup/'audit-shop.json').write_bytes(shop)
  result.update(status='INSTALLED_AND_RUNTIME_ACTIVE',preflight=proof,top_preflight=str(S/d.SELF),top_manifest=str(S/d.MANIFEST),top_receipt=str(S/d.RECEIPT),
   composition_api='compose_manifest(server=None,client=None)',service_restart=True,launcher_pid=pid,readiness=ready,
   runtime_active=True,state_shop_written=False,native_verified=False,live_rules=rules,live_invalid_preview_nonfatal=True)
  d.tx.atomic_json(W/'installed-handback.json',result);d.tx.atomic_json(Path(r'D:\fifaol3\root-current-top.json'),result)
  print(json.dumps(dict(status=result['status'],preflight=proof)))
if __name__=='__main__':main()
