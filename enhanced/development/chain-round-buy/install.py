"""Six-file additive server transaction, fresh parent guards, no asset writes."""
from pathlib import Path
from contextlib import contextmanager
import os,sys,json,hashlib,importlib.util,datetime,re,subprocess,shutil
sys.dont_write_bytecode=True
R=Path(__file__).parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
SELF='patches/round_buy_preflight.py';MANIFEST='patches/round-buy-installed.json';RECEIPT='patches/round-buy-receipt.json'
ALLOWED={('server',n) for n in ['http_config.py','chain_round_purchase.py','patches/TileList.big',SELF,MANIFEST,RECEIPT,'play-local.bat']}|{('client','data/ui/components/TileList.big')}
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
   p=server/name;fd=os.open(p,os.O_EXCL|os.O_CREAT|os.O_WRONLY|getattr(os,'O_BINARY',0));payload=encoded(dict(pid=os.getpid(),release='chain-round-buy'))
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
 source=source.replace('exp-selection-installed.json','round-buy-installed.json').replace('exp-selection-receipt.json','round-buy-receipt.json').replace('exp_selection_preflight.py','round_buy_preflight.py').replace('INSTALLED_EXP_SELECTION','INSTALLED_ROUND_BUY').replace('EXP_SELECTION_PREFLIGHT_PASS','ROUND_BUY_PREFLIGHT_PASS')
 a=source.index('    required=');b=source.index('\n    if not required<=seen:',a)
 source=source[:a]+"    required={('server','http_config.py'),('server','chain_round_purchase.py'),('server','patches/tilelist.big'),('client','data/ui/components/tilelist.big'),('server','play-local.bat'),('server',SELF)}"+source[b:]
 source=source.replace('Exact-file read-only gate for a global player database revision.','Read-only guard for the atomic current-round purchase button.')
 compile(source,SELF,'exec')
 payloads={('server','http_config.py'):(R/'http_config.py').read_bytes(),('server','chain_round_purchase.py'):(R/'chain_round_purchase.py').read_bytes(),('server','patches/TileList.big'):(R/'TileList.big').read_bytes(),('client','data/ui/components/TileList.big'):(R/'TileList.big').read_bytes(),('server',SELF):source.encode('utf8'),('server','play-local.bat'):play.replace(parent_rel.replace('/','\\').encode(),SELF.replace('/','\\').encode())}
 assert payloads[('server','play-local.bat')]!=play
 def target(key):return (server if key[0]=='server' else client)/key[1]
 guards=validator.table(c['guards'])
 for resource,body in payloads.items():
  root,rel=resource;p=target(resource);key=(root,rel.casefold())
  if key in guards:
   if sha(p)!=guards[key]['sha256']:raise RuntimeError('Parent target mismatch: '+str(rel))
  elif p.exists():raise RuntimeError('Unregistered target: '+str(rel))
  guards[key]=dict(root=root,relative=rel,sha256=digest(body))
 c.update(guards=list(guards.values()),files_verified=False)
 c.setdefault('ancestry',[]).append(dict(layer='round-purchase-button-v1',native_status='PENDING'))
 revision='round-buy-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 m=dict(schema=1,revision=revision,client=str(client),state_shop_replaced=False,guards=c['guards'],composition=c,parent_preflight=parent_rel,parent_preflight_sha256=sha(parent_path))
 payloads[('server',MANIFEST)]=encoded(m);payloads[('server',RECEIPT)]=encoded(dict(status='INSTALLED_ROUND_BUY',revision=revision,manifest_sha256=digest(payloads[('server',MANIFEST)]),state_shop_replaced=False))
 assert set(payloads)==ALLOWED
 for rel in [SELF,MANIFEST,RECEIPT,'chain_round_purchase.py']:
  if (server/rel).exists():raise RuntimeError('Append-only metadata/config already exists: '+str(rel))
 before={key:target(key).read_bytes() if target(key).exists() else None for key in payloads}
 return dict(server=server,client=client,payloads=payloads,before=before,revision=revision,prior=prior,parent=parent_rel,parent_hash=sha(parent_path))
def apply(p,fail_after=None):
 if p.get('already_current'):return dict(status='ALREADY_CURRENT',preflight=p['preflight'],state_shop_written=False)
 server=p['server'];client=p['client'];target=lambda key:(server if key[0]=='server' else client)/key[1];backup=server/'backups'/p['revision'];backup.mkdir(parents=True)
 for n,(rel,body) in enumerate(p['before'].items()):
  if body is not None:(backup/(str(n)+'-'+Path(rel[1]).name)).write_bytes(body)
 committed=[];order=[r for r in p['payloads'] if r!=('server','play-local.bat')]+[('server','play-local.bat')]
 try:
  if sha(server/p['parent'])!=p['parent_hash']:raise RuntimeError('Parent helper changed')
  for index,rel in enumerate(order,1):
   destination=target(rel)
   if (destination.read_bytes() if destination.exists() else None)!=p['before'][rel]:raise RuntimeError('Concurrent target change: '+str(rel))
   destination.parent.mkdir(parents=True,exist_ok=True);tmp=destination.with_name(destination.name+'.round-buy.tmp');tmp.write_bytes(p['payloads'][rel]);os.replace(tmp,destination);committed.append(rel)
   if fail_after==index:raise OSError('Injected transaction failure')
  proof=load(server/SELF,'rebalance_installed').preflight(server,p['client'])
 except BaseException:
  for rel in reversed(committed):
   destination=target(rel)
   if destination.read_bytes()!=p['payloads'][rel]:raise RuntimeError('Later change retained; refusing rollback overwrite: '+str(rel))
   if p['before'][rel] is None:destination.unlink()
   else:
    tmp=destination.with_name(destination.name+'.round-buy.rollback');tmp.write_bytes(p['before'][rel]);os.replace(tmp,destination)
  raise
 return dict(status='INSTALLED',backup=str(backup),revision=p['revision'],preflight=proof,top_preflight=str(server/SELF),top_manifest=str(server/MANIFEST),top_receipt=str(server/RECEIPT),state_shop_written=False)
if __name__=='__main__':
 with locks(S):
  closed();p=plan()
  if p.get('already_current'):print(json.dumps(apply(p)))
  else:
   (R/'plan.json').write_bytes(encoded(dict(parent=p['parent'],parent_hash=p['parent_hash'],prior=p['prior'],files={root+'/'+rel:digest(b) for (root,rel),b in p['payloads'].items()})));print('Current parent verified; prepared, no formal payload written')
