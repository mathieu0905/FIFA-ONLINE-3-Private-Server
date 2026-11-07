"""Official-only installation; an active game defers before locks or any write."""
from pathlib import Path
import sys,os,json,subprocess,time,ssl,urllib.request,re
import install as d
R=d.R;S=d.S;C=d.C
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
PATH='/player/a4534cf19c3af515828e9032/enhance2.5/dd383241d1ac3c32f13bbf38/preview/0/{}/-1'
def call(path):
 with opener.open('https://127.0.0.1'+path,timeout=25) as response:return json.load(response)
def stop():
 subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],check=True,stdout=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
 for _ in range(20):
  result=subprocess.run(['powershell.exe','-NoProfile','-Command','if(Get-NetTCPConnection -State Listen -LocalPort 443,8088,28002 -ErrorAction SilentlyContinue){exit 1}'],creationflags=subprocess.CREATE_NO_WINDOW)
  if result.returncode==0:return
  time.sleep(.25)
 raise RuntimeError('Managed listeners have not stopped; no files written')
def start():
 env=os.environ.copy();env.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20')
 env['PSModulePath']=os.path.expandvars(r'%SystemRoot%\System32\WindowsPowerShell\v1.0\Modules;%ProgramFiles%\WindowsPowerShell\Modules')
 with (R/'formal.stdout.log').open('ab') as out,(R/'formal.stderr.log').open('ab') as err:
  p=subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-u',str(S/'start_all.py')],cwd=S,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
 ready=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'wait_services.py'),'--timeout','25'],cwd=S,env=env,capture_output=True,text=True)
 if ready.returncode:raise RuntimeError('Readiness failed: '+ready.stdout+ready.stderr)
 return p.pid,ready.stdout.strip()
def main():
 try:d.closed()
 except RuntimeError:
  print('DEFERRED_GAME_RUNNING: no formal files, services or session changed');return
 assert d.read(R/'server-tests.json')['status']=='PASS'
 assert d.read(R/'client-guard-tests.json')['status']=='PASS'
 assert d.read(R/'plan-check.json')['status']=='PASS'
 with d.locks(S):
  d.closed();p=d.plan()
  if p.get('already_current'):print(json.dumps(d.apply(p)));return
  normal_before=call(PATH.format('-1'));d.closed()
  # A failed or deferred stop aborts here, without apply or duplicate start.
  stop()
  state=(S/'gamedata/state.json').read_bytes();shop=(S/'gamedata/shop.json').read_bytes();before=json.loads(state)
  error=None;result=None
  try:
   d.closed();result=d.apply(p)
   backup=Path(result['backup']);(backup/'audit-state.json').write_bytes(state);(backup/'audit-shop.json').write_bytes(shop)
  except BaseException as exc:error=exc
  top='patches/'+re.search(rb'patches\\(\w+_preflight\.py)',(S/'play-local.bat').read_bytes()).group(1).decode()
  proof=d.load(S/top,'valid_preview_gate').preflight(S,C)
  pid,ready=start()
  if error:raise error
  normal=call(PATH.format('-1'));blocked=call(PATH.format('1000090'))
  assert normal==normal_before
  assert blocked['result'] and blocked['protection']['blocked'] and not blocked['protection']['available']
  assert blocked['enhancepay']==0 and 'token' not in blocked['protection']
  assert (S/'gamedata/shop.json').read_bytes()==shop
  business=lambda st:{k:v for k,v in st.items() if k!='market_simulation'}
  assert business(d.read(S/'gamedata/state.json'))==business(before),'Concurrent legal progress retained; inspect, never restore stale state'
  check=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'tools/player_import/check.py')],cwd=S,capture_output=True,text=True)
  assert check.returncode==0,check.stdout+check.stderr
  result.update(status='INSTALLED_AND_LIVE_PASS',preflight=proof,top_preflight=str(S/d.SELF),top_manifest=str(S/d.MANIFEST),top_receipt=str(S/d.RECEIPT),
   composition_api='compose_manifest(server=None,client=None)',service_restart=True,launcher_pid=pid,readiness=ready,
   hashes={rel:d.sha(S/rel) for rel in d.ALLOWED},state_shop_written=False,native_game_verified=False,
   validation=dict(server_tests=True,actual_client_guard_replay=True,live_original_fault_preview=blocked,normal_preview_exact=True,business_assets_exact=True,shop_exact=True,player_import=True))
  (R/'installed-handback.json').write_bytes(d.encoded(result))
  (Path(r'D:\fifaol3')/'root-current-top.json').write_bytes(d.encoded(result))
  print(json.dumps(dict(status=result['status'],preflight=proof)))
if __name__=='__main__':main()
