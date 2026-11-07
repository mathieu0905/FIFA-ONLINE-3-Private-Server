"""Authorized official cutover; publication lock spans stop, install, restart/checks."""
from pathlib import Path
import os,sys,subprocess,time,json,ssl,urllib.request,hashlib,re,copy
import install as d
R=d.R;S=d.S;C=d.C
assert d.read(R/'test-results.json')['status']=='PASS' and d.read(R/'install-tests.json')['status']=='PASS'
assert (R/'checks-runtime/server/product_packs.py').read_bytes()==(R/'payload/product_packs.py').read_bytes()
assert (R/'checks-runtime/server/gamedata/chain_rebalance_products.json').read_bytes()==(R/'payload/chain_rebalance_products.json').read_bytes()
def stop():
 subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],check=True,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.PIPE)
 for _ in range(20):
  q=subprocess.run(['powershell.exe','-NoProfile','-Command',"if(Get-NetTCPConnection -State Listen -LocalPort 443,8088,28002 -ErrorAction SilentlyContinue){exit 1}"],creationflags=subprocess.CREATE_NO_WINDOW)
  if q.returncode==0:return
  time.sleep(.25)
 raise RuntimeError('Managed listeners did not stop')
def start():
 env=os.environ.copy();env.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20')
 with (R/'formal.stdout.log').open('ab') as out,(R/'formal.stderr.log').open('ab') as err:
  p=subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-u',str(S/'start_all.py')],cwd=S,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
 ready=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'wait_services.py'),'--timeout','25'],cwd=S,env=env,capture_output=True,text=True)
 if ready.returncode:raise RuntimeError('Readiness failed: '+ready.stdout+ready.stderr)
 return p.pid,ready.stdout.strip()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(path):
 with opener.open('https://127.0.0.1'+path,timeout=30) as r:return json.load(r)
def business(st):return {k:v for k,v in st.items() if k!='market_simulation'}
with d.locks(S):
 d.closed();p=d.plan()
 if p.get('already_current'):print(json.dumps(d.apply(p)));sys.exit(0)
 beforelive=get('/shop/list')
 stop()
 state=(S/'gamedata/state.json').read_bytes();shop=(S/'gamedata/shop.json').read_bytes()
 before=json.loads(state);error=None
 try:
  d.closed();result=d.apply(p)
  (Path(result['backup'])/'audit-state.json').write_bytes(state);(Path(result['backup'])/'audit-shop.json').write_bytes(shop)
 except BaseException as exc:error=exc
 # A valid complete installed layer is mandatory before restarting even on failure.
 play=(S/'play-local.bat').read_bytes();top='patches/'+re.search(rb'patches\\(\w+_preflight\.py)',play).group(1).decode()
 proof=d.load(S/top,'cutover_valid_top').preflight(S,C)
 pid,ready=start()
 if error:raise error
 rows=get('/shop/list');new=d.read(R/'payload/chain_rebalance_products.json');summary=d.read(R/'summary.json');verified=[]
 for entry in summary['chains']:
  root=entry['root'];row=next(r for r in rows if r['shopid']==root);parts=[row]+row['chained']
  assert len(parts)==5 and all(part['shopid']==root for part in parts)
  costs=[part['product']['staticdata']['bunches'][0]['price'] for part in parts]
  assert costs==entry['prices'] and sum(costs)==entry['round_points']
  assert row['buy'] and row['visible']
  verified.append(dict(root=root,name=entry['name'],prices=costs,round_points=sum(costs),round_yuan=sum(costs)/100,cards=entry['cards']))
 record=before.get('product_chain_rounds',{})
 for root in new['retired_chains']:
  old=next((r for r in rows if r['shopid']==root),None);stage=record.get(str(root),{}).get('stage',0)
  if stage:
   assert old is not None and old['step']==stage and old['chainedproductname'].startswith('旧期续购')
   baseline=next(r for r in beforelive if r['shopid']==root)
   assert [r['product']['staticdata']['bunches'][0]['price'] for r in [old]+old['chained']]==[r['product']['staticdata']['bunches'][0]['price'] for r in [baseline]+baseline['chained']]
  else:assert old is None
 counts=get('/shop/remained/limited')
 for v in verified:
  row=next(r for r in rows if r['shopid']==v['root']);quota=next(r for r in counts if r['shopid']==v['root']);assert quota['buy']==row['buy'] and quota['step']==row['step']
 after=d.read(S/'gamedata/state.json');assert business(after)==business(before),'Concurrent real progress changed; preserve and inspect, do not restore'
 assert (S/'gamedata/shop.json').read_bytes()==shop
 proof=d.load(S/d.SELF,'cutover_final_top').preflight(S,C)
 result.update(service_restart=True,launcher_pid=pid,readiness=ready,formal_checks=dict(status='PASS',chains=verified,old_pending_round_preserved=True,
             business_assets_exact=True,shop_exact=True,real_purchase_executed=False,native_verified=False),preflight=proof,
             hashes={rel:d.sha(S/rel) for rel in [d.SELF,d.MANIFEST,d.RECEIPT,'play-local.bat','product_packs.py','gamedata/chain_rebalance_products.json']},composition_api='compose_manifest(server=None,client=None)')
 (R/'installed-handback.json').write_bytes(d.encoded(result));print(json.dumps({k:result[k] for k in ['status','backup','top_preflight','service_restart','preflight']},ensure_ascii=True))
