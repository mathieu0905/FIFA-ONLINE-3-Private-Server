"""Finish read-only installed verification without repeating a successful restart."""
from pathlib import Path
import os,subprocess,json,ssl,urllib.request,hashlib
import install as d
R=d.R;S=d.S;C=d.C
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(uri,body=None):
 req=urllib.request.Request('https://127.0.0.1'+uri,data=body,headers={'Content-Type':'application/json'} if body else {})
 with opener.open(req,timeout=30) as response:return json.load(response)
with d.locks(S):
 manifest=d.read(S/d.MANIFEST);receipt=d.read(S/d.RECEIPT);proof=d.load(S/d.SELF,'formal_round_gate').preflight(S,C)
 backup=S/'backups'/manifest['revision'];before=d.read(backup/'audit-state.json');shop=(backup/'audit-shop.json').read_bytes()
 rows=get('/shop/list');config=d.read(S/'gamedata/chain_rebalance_products.json');verified=[]
 for roottext,t in config['chains'].items():
  root=int(roottext);row=next(x for x in rows if x['shopid']==root);q=get('/shop/chain/round/quote?root='+roottext)
  assert row['round_buy_supported'] and row['round_buy_enabled'] and q['result']
  assert q['quote']['total']==row['round_buy_total']==sum(t['prices'][str(i)] for i in t['steps'])
  assert len(q['quote']['steps'])==row['round_buy_stages']==5 and len(q['quote']['signature'])==64
  verified.append(dict(root=root,total=q['quote']['total'],remaining_stages=5))
 assert get('/shop/chain/round/purchase',b'{}')['result'] is False
 env=os.environ.copy();env['PSModulePath']=os.path.expandvars(r'%SystemRoot%\System32\WindowsPowerShell\v1.0\Modules;%ProgramFiles%\WindowsPowerShell\Modules')
 result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'patches/install-grade20.ps1')],env=env,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
 (R/'powershell-installed-check.json').write_bytes(d.encoded(dict(returncode=result.returncode,stdout=result.stdout.decode('utf8','replace'),stderr=result.stderr.decode('utf8','replace'))))
 assert result.returncode==0
 assert d.sha(C/'data/ui/components/TileList.big')==d.sha(S/'patches/TileList.big')==d.read(R/'client-build.json')['after_sha256']
 after=d.read(S/'gamedata/state.json');business=lambda st:{k:v for k,v in st.items() if k!='market_simulation'}
 assert business(after)==business(before),'Real concurrent progress differs; preserve and inspect rather than restore'
 assert (S/'gamedata/shop.json').read_bytes()==shop
 proof=d.load(S/d.SELF,'formal_round_gate2').preflight(S,C)
 report=dict(status='INSTALLED_AND_FORMAL_READONLY_PASS_NATIVE_PENDING',revision=manifest['revision'],backup=str(backup),top_preflight=str(S/d.SELF),top_manifest=str(S/d.MANIFEST),top_receipt=str(S/d.RECEIPT),preflight=proof,
  composition_api='compose_manifest(server=None,client=None)',service_restart=True,verification_restarted_services=False,
  formal_checks=dict(status='PASS',chains=verified,invalid_purchase_rejected=True,business_assets_exact=True,shop_exact=True,real_purchase_executed=False,native_verified=False),
  hashes={root+'/'+rel:d.sha((S if root=='server' else C)/rel) for root,rel in d.ALLOWED},state_shop_written=False)
 (R/'installed-handback.json').write_bytes(d.encoded(report));print(json.dumps(dict(status=report['status'],files=proof['files'],service_restart=True)))
