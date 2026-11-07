"""Six-file additive server transaction, fresh parent guards, no asset writes."""
from pathlib import Path
from contextlib import contextmanager
import os,sys,json,hashlib,importlib.util,datetime,re,subprocess,shutil
sys.dont_write_bytecode=True
R=Path(__file__).parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
SELF='patches/legacy_chain_preflight.py';MANIFEST='patches/legacy-chain-installed.json';RECEIPT='patches/legacy-chain-receipt.json'
ALLOWED={'http_config.py','legacy_chain_hide.py',SELF,MANIFEST,RECEIPT,'play-local.bat'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf8'))
def encoded(d):return (json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def load(p,name):
 sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def closed():
 result=subprocess.run(['powershell.exe','-NoProfile','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9}'],creationflags=subprocess.CREATE_NO_WINDOW)
 if result.returncode:raise RuntimeError('Game is active; do not interrupt it')
@contextmanager
def locks(server):
 owned=[]
 try:
  for name in ['.shop-release.lock','.fo3-publish.lock']:
   p=server/name;fd=os.open(p,os.O_EXCL|os.O_CREAT|os.O_WRONLY|getattr(os,'O_BINARY',0));payload=encoded(dict(pid=os.getpid(),release='legacy-chain-hide'))
   owned.append((p,fd,payload));os.write(fd,payload);os.fsync(fd)
  yield
 finally:
  for p,fd,payload in reversed(owned):
   os.close(fd)
   if p.exists() and p.read_bytes()==payload:p.unlink()
def validate_roots(server,client,fixture):
 if fixture:
  if not server.is_relative_to(R/'install-tests') or not client.is_relative_to(R/'install-tests'):raise RuntimeError('Fixture escaped task I/O root')
 elif server!=S or client!=C:raise RuntimeError('Only official roots permitted')
def plan(server=S,client=C,fixture=False):
 server=Path(server).resolve();client=Path(client).resolve();validate_roots(server,client,fixture)
 play=(server/'play-local.bat').read_bytes();parent_rel='patches/'+re.search(rb'patches\\(\w+_preflight\.py)',play).group(1).decode();parent_path=server/parent_rel
 if parent_rel==SELF:return dict(already_current=True,preflight=load(parent_path,'rebalance_current').preflight(server,client),server=server,client=client)
 parent=load(parent_path,'rebalance_parent');prior=parent.preflight(server,client);c=parent.compose_manifest(server,client)
 validator=load(S/'patches/startup_market_preflight.py','rebalance_validator')
 if sha(S/'patches/startup_market_preflight.py')!='49eafb6eaa5ec954bfc65c4460aec2a3f14e9bb93dbbf6547cedfded44393d8a':raise RuntimeError('Shared validator changed')
 validator.verify_manifest(c,server,client)
 if not fixture:
  baseline=read(R/'baseline.json')
  for p,h in baseline.items():
   if sha(p)!=h:raise RuntimeError('Build input changed; rebase required: '+p)
 source=(S/'patches/exp_selection_preflight.py').read_text('utf8')
 source=source.replace('exp-selection-installed.json','legacy-chain-installed.json').replace('exp-selection-receipt.json','legacy-chain-receipt.json').replace('exp_selection_preflight.py','legacy_chain_preflight.py').replace('INSTALLED_EXP_SELECTION','INSTALLED_LEGACY_CHAIN_HIDE').replace('EXP_SELECTION_PREFLIGHT_PASS','LEGACY_CHAIN_HIDE_PREFLIGHT_PASS')
 a=source.index('    required=');b=source.index('\n    if not required<=seen:',a)
 source=source[:a]+"    required={('server','http_config.py'),('server','legacy_chain_hide.py'),('server','play-local.bat'),('server',SELF)}"+source[b:]
 source=source.replace('Exact-file read-only gate for a global player database revision.','Read-only guard for withdrawn legacy chain storefront entries.')
 compile(source,SELF,'exec')
 payloads={'http_config.py':(R/'http_config.py').read_bytes(),'legacy_chain_hide.py':(R/'legacy_chain_hide.py').read_bytes(),SELF:source.encode('utf8'),'play-local.bat':play.replace(parent_rel.replace('/','\\').encode(),SELF.replace('/','\\').encode())}
 assert payloads['play-local.bat']!=play
 guards=validator.table(c['guards'])
 for rel,body in payloads.items():
  p=server/rel;key=('server',rel.casefold())
  if key in guards:
   if sha(p)!=guards[key]['sha256']:raise RuntimeError('Parent target mismatch: '+rel)
  elif p.exists():raise RuntimeError('Unregistered target: '+rel)
  guards[key]=dict(root='server',relative=rel,sha256=digest(body))
 c.update(guards=list(guards.values()),files_verified=False)
 c.setdefault('ancestry',[]).append(dict(layer='legacy-chain-hide-v1',native_status='PENDING'))
 revision='legacy-chain-hide-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 m=dict(schema=1,revision=revision,client=str(client),state_shop_replaced=False,guards=c['guards'],composition=c,parent_preflight=parent_rel,parent_preflight_sha256=sha(parent_path))
 payloads[MANIFEST]=encoded(m);payloads[RECEIPT]=encoded(dict(status='INSTALLED_LEGACY_CHAIN_HIDE',revision=revision,manifest_sha256=digest(payloads[MANIFEST]),state_shop_replaced=False))
 assert set(payloads)==ALLOWED
 for rel in [SELF,MANIFEST,RECEIPT,'legacy_chain_hide.py']:
  if (server/rel).exists():raise RuntimeError('Append-only metadata/config already exists: '+rel)
 before={rel:(server/rel).read_bytes() if (server/rel).exists() else None for rel in payloads}
 return dict(server=server,client=client,payloads=payloads,before=before,revision=revision,prior=prior,parent=parent_rel,parent_hash=sha(parent_path))
def apply(p,fail_after=None):
 if p.get('already_current'):return dict(status='ALREADY_CURRENT',preflight=p['preflight'],state_shop_written=False)
 server=p['server'];backup=server/'backups'/p['revision'];backup.mkdir(parents=True)
 for n,(rel,body) in enumerate(p['before'].items()):
  if body is not None:(backup/(str(n)+'-'+Path(rel).name)).write_bytes(body)
 committed=[];order=[r for r in p['payloads'] if r!='play-local.bat']+['play-local.bat']
 try:
  if sha(server/p['parent'])!=p['parent_hash']:raise RuntimeError('Parent helper changed')
  for index,rel in enumerate(order,1):
   target=server/rel
   if (target.read_bytes() if target.exists() else None)!=p['before'][rel]:raise RuntimeError('Concurrent target change: '+rel)
   target.parent.mkdir(parents=True,exist_ok=True);tmp=target.with_name(target.name+'.chain-rebalance.tmp');tmp.write_bytes(p['payloads'][rel]);os.replace(tmp,target);committed.append(rel)
   if fail_after==index:raise OSError('Injected transaction failure')
  proof=load(server/SELF,'rebalance_installed').preflight(server,p['client'])
 except BaseException:
  for rel in reversed(committed):
   target=server/rel
   if target.read_bytes()!=p['payloads'][rel]:raise RuntimeError('Later change retained; refusing rollback overwrite: '+rel)
   if p['before'][rel] is None:target.unlink()
   else:
    tmp=target.with_name(target.name+'.chain-rebalance.rollback');tmp.write_bytes(p['before'][rel]);os.replace(tmp,target)
  raise
 return dict(status='INSTALLED',backup=str(backup),revision=p['revision'],preflight=proof,top_preflight=str(server/SELF),top_manifest=str(server/MANIFEST),top_receipt=str(server/RECEIPT),state_shop_written=False)
if __name__=='__main__':
 with locks(S):
  closed();p=plan()
  if p.get('already_current'):print(json.dumps(apply(p)))
  else:
   (R/'plan.json').write_bytes(encoded(dict(parent=p['parent'],parent_hash=p['parent_hash'],prior=p['prior'],files={r:digest(b) for r,b in p['payloads'].items()})));print('Current parent verified; prepared, no formal payload written')
