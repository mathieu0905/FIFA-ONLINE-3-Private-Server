"""Install/reload the current-round button, checking only read-only formal routes."""
from pathlib import Path
import os,sys,subprocess,time,json,ssl,urllib.request,re
import install as d
R=d.R;S=d.S;C=d.C
for name in ['server-tests.json','client-tests.json','install-tests.json']:assert d.read(R/name)['status']=='PASS'
assert d.sha(R/'TileList.big')==d.read(R/'client-build.json')['after_sha256']
assert (R/'checks-runtime/server/http_config.py').read_bytes()==(R/'http_config.py').read_bytes()
assert (R/'checks-runtime/server/chain_round_purchase.py').read_bytes()==(R/'chain_round_purchase.py').read_bytes()
def stop():
 subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],check=True,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.PIPE)
 for _ in range(20):
  p=subprocess.run(['powershell.exe','-NoProfile','-Command',"if(Get-NetTCPConnection -State Listen -LocalPort 443,8088,28002 -ErrorAction SilentlyContinue){exit 1}"],creationflags=subprocess.CREATE_NO_WINDOW)
  if not p.returncode:return
  time.sleep(.25)
 raise RuntimeError('Managed listeners remain active')
def start():
 env=os.environ.copy();env.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20')
 with (R/'formal.stdout.log').open('ab') as out,(R/'formal.stderr.log').open('ab') as err:
  p=subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-u',str(S/'start_all.py')],cwd=S,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
 ready=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'wait_services.py'),'--timeout','25'],cwd=S,env=env,capture_output=True,text=True)
 if ready.returncode:raise RuntimeError('Readiness failed: '+ready.stdout+ready.stderr)
 return p.pid,ready.stdout.strip()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def call(path,body=None):
 req=urllib.request.Request('https://127.0.0.1'+path,data=body,headers={'Content-Type':'application/json'} if body else {})
 with opener.open(req,timeout=30) as r:return json.load(r)
def business(st):return {k:v for k,v in st.items() if k!='market_simulation'}
with d.locks(S):
 d.closed();p=d.plan()
 if p.get('already_current'):print(json.dumps(d.apply(p)));sys.exit(0)
 stop();state=(S/'gamedata/state.json').read_bytes();shop=(S/'gamedata/shop.json').read_bytes();before=json.loads(state);error=None
 try:
  d.closed();result=d.apply(p);backup=Path(result['backup']);(backup/'audit-state.json').write_bytes(state);(backup/'audit-shop.json').write_bytes(shop)
  (R/'installed-payload.json').write_bytes(d.encoded(result))
 except BaseException as exc:error=exc
 play=(S/'play-local.bat').read_bytes();top='patches/'+re.search(rb'patches\\(\w+_preflight\.py)',play).group(1).decode()
 d.load(S/top,'round_cutover_valid').preflight(S,C)
 pid,ready=start()
 if error:raise error
 rows=call('/shop/list');cfg=d.read(S/'gamedata/chain_rebalance_products.json');verified=[]
 for roottext,t in cfg['chains'].items():
  root=int(roottext);row=next(r for r in rows if r['shopid']==root);assert row['round_buy_supported'] and row['round_buy_enabled']
  q=call('/shop/chain/round/quote?root='+roottext)
  assert q['result'] and q['quote']['root']==root and len(q['quote']['signature'])==64
  assert q['quote']['total']==row['round_buy_total']==sum(t['prices'][str(i)] for i in t['steps'])
  assert len(q['quote']['steps'])==row['round_buy_stages']==5
  assert '仅购买当前这一轮' in q['message']
  verified.append(dict(root=root,total=q['quote']['total'],remaining_stages=5))
 rejected=call('/shop/chain/round/purchase',b'{}');assert rejected['result'] is False
 psenv=os.environ.copy();psenv['PSModulePath']=os.path.expandvars(r'%SystemRoot%\System32\WindowsPowerShell\v1.0\Modules;%ProgramFiles%\WindowsPowerShell\Modules')
 ps=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'patches/install-grade20.ps1')],env=psenv,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
 assert ps.returncode==0
 assert d.sha(C/'data/ui/components/TileList.big')==d.sha(S/'patches/TileList.big')==d.read(R/'client-build.json')['after_sha256']
 after=d.read(S/'gamedata/state.json');assert business(after)==business(before),'Concurrent real progress changed; preserve and inspect, never restore'
 assert (S/'gamedata/shop.json').read_bytes()==shop
 proof=d.load(S/d.SELF,'round_cutover_final').preflight(S,C)
 result.update(service_restart=True,launcher_pid=pid,readiness=ready,preflight=proof,
   formal_checks=dict(status='PASS',chains=verified,invalid_purchase_rejected=True,business_assets_exact=True,shop_exact=True,real_purchase_executed=False,native_verified=False),
   hashes={root+'/'+rel:d.sha((S if root=='server' else C)/rel) for root,rel in d.ALLOWED},composition_api='compose_manifest(server=None,client=None)')
 (R/'installed-handback.json').write_bytes(d.encoded(result));print(json.dumps({k:result[k] for k in ['status','backup','service_restart','top_preflight','preflight']}))
