"""Withdraw legacy sales on the official service; never change real stored assets."""
from pathlib import Path
import os,sys,subprocess,time,json,ssl,urllib.request,re
import install as d
R=d.R;S=d.S;C=d.C
assert d.read(R/'test-results.json')['status']=='PASS' and d.read(R/'install-tests.json')['status']=='PASS'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def call(path,body=None):
 req=urllib.request.Request('https://127.0.0.1'+path,data=body,headers={'Content-Type':'application/json'} if body else {})
 with opener.open(req,timeout=30) as response:return json.load(response)
def stop():
 subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],check=True,stdout=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
 for _ in range(20):
  p=subprocess.run(['powershell.exe','-NoProfile','-Command',"if(Get-NetTCPConnection -State Listen -LocalPort 443,8088,28002 -ErrorAction SilentlyContinue){exit 1}"],creationflags=subprocess.CREATE_NO_WINDOW)
  if not p.returncode:return
  time.sleep(.25)
 raise RuntimeError('Managed listeners did not stop')
def start():
 env=os.environ.copy();env.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20');env['PSModulePath']=os.path.expandvars(r'%SystemRoot%\System32\WindowsPowerShell\v1.0\Modules;%ProgramFiles%\WindowsPowerShell\Modules')
 with (R/'formal.stdout.log').open('ab') as out,(R/'formal.stderr.log').open('ab') as err:
  p=subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-u',str(S/'start_all.py')],cwd=S,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
 ready=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'wait_services.py'),'--timeout','25'],cwd=S,env=env,capture_output=True,text=True)
 if ready.returncode:raise RuntimeError('Readiness failed: '+ready.stdout+ready.stderr)
 return p.pid,ready.stdout.strip()
with d.locks(S):
 d.closed();p=d.plan()
 if p.get('already_current'):print(json.dumps(d.apply(p)));sys.exit(0)
 before_rows=call('/shop/list');old_quote=call('/shop/chain/round/quote?root=71231901')
 stop();state=(S/'gamedata/state.json').read_bytes();shop=(S/'gamedata/shop.json').read_bytes();before=json.loads(state);error=None
 try:
  d.closed();result=d.apply(p);backup=Path(result['backup']);(backup/'audit-state.json').write_bytes(state);(backup/'audit-shop.json').write_bytes(shop)
  (R/'installed-payload.json').write_bytes(d.encoded(result))
 except BaseException as exc:error=exc
 top='patches/'+re.search(rb'patches\\(\w+_preflight\.py)',(S/'play-local.bat').read_bytes()).group(1).decode();d.load(S/top,'valid_legacy_gate').preflight(S,C)
 pid,ready=start()
 if error:raise error
 rows=call('/shop/list');byid={r['shopid']:r for r in rows};new={71250101,71250201,71250301,71250401,71250501};assert new<=byid.keys()
 before_map={r['shopid']:r for r in before_rows}
 for root in new:assert byid[root]==before_map[root]
 old={70000001,71010101,71220101,71220201,71230101,71230201,71231901,71240101};assert not old&byid.keys()
 before_mul={r['product']['itemid']:r for r in before_rows if 98248000<=r['product']['itemid']<98249000};after_mul={r['product']['itemid']:r for r in rows if 98248000<=r['product']['itemid']<98249000};assert before_mul==after_mul
 quota=call('/shop/remained/limited');assert not old&{r['shopid'] for r in quota}
 out=call('/shop/purchase',json.dumps(dict(shopid=71231901,productid=71231904,bunch=0)).encode());assert out.get('reason')=='LEGACY_CHAIN_WITHDRAWN'
 assert call('/shop/chain/round/quote?root=71231901').get('reason')=='LEGACY_CHAIN_WITHDRAWN'
 if old_quote.get('result'):
  out=call('/shop/chain/round/purchase',json.dumps(dict(quote=old_quote['quote'])).encode());assert out.get('reason')=='LEGACY_CHAIN_WITHDRAWN'
 after=d.read(S/'gamedata/state.json');business=lambda st:{k:v for k,v in st.items() if k!='market_simulation'}
 assert business(after)==business(before),'Concurrent legal progress differs; preserve and inspect, never restore old state'
 assert (S/'gamedata/shop.json').read_bytes()==shop
 proof=d.load(S/d.SELF,'final_legacy_gate').preflight(S,C)
 result.update(service_restart=True,launcher_pid=pid,readiness=ready,preflight=proof,composition_api='compose_manifest(server=None,client=None)',
  formal_checks=dict(status='PASS',old_chains_absent=True,new_five_chains_exact=True,mul_offers_exact=True,old_single_and_bulk_rejected_without_charge=True,business_assets_exact=True,shop_exact=True,native_verified=False),
  hashes={rel:d.sha(S/rel) for rel in d.ALLOWED})
 (R/'installed-handback.json').write_bytes(d.encoded(result));print(json.dumps(dict(status='INSTALLED_AND_LIVE_PASS',files=proof['files'],backup=result['backup'],top=result['top_preflight'])))
