"""Five-file additive server transaction, fresh parent guards, no asset writes."""
from pathlib import Path
from contextlib import contextmanager
import os,sys,json,hashlib,importlib.util,datetime,re,subprocess,shutil
sys.dont_write_bytecode=True
R=Path(__file__).parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
SELF='patches/protection_preview_fix_preflight.py';MANIFEST='patches/protection-preview-fix-installed.json';RECEIPT='patches/protection-preview-fix-receipt.json'
ALLOWED={'enhancement_protection40.py',SELF,MANIFEST,RECEIPT,'play-local.bat'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf8'))
def encoded(d):return (json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def load(p,name):
 sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def closed():
 result=subprocess.run(['powershell.exe','-NoProfile','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9}'],creationflags=subprocess.CREATE_NO_WINDOW)
 if result.returncode:raise RuntimeError('更新已延后，当前游戏继续运行')
@contextmanager
def locks(server):
 owned=[]
 try:
  for name in ['.shop-release.lock','.fo3-publish.lock']:
   p=server/name;fd=os.open(p,os.O_EXCL|os.O_CREAT|os.O_WRONLY|getattr(os,'O_BINARY',0));payload=encoded(dict(pid=os.getpid(),release='protection-preview-fix'))
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
 source=parent_path.read_text('utf8')
 parent_status=read(server/parent.RECEIPT)['status']
 for old,new in [(parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(parent_status,'INSTALLED_PREVIEW_FIX'),(prior['status'],'PROTECTION_PREVIEW_FIX_PREFLIGHT_PASS')]:source=source.replace(old,new)
 a=source.index(' required=');b=source.index('\n if not required<=seen:',a)
 required=source[a:b].rstrip()
 assert required.endswith('}')
 source=source[:a]+required[:-1]+",('server','enhancement_protection40.py')}"+source[b:]
 compile(source,SELF,'exec')
 payloads={'enhancement_protection40.py':(R/'enhancement_protection40.py').read_bytes(),SELF:source.encode('utf8'),'play-local.bat':play.replace(parent_rel.replace('/','\\').encode(),SELF.replace('/','\\').encode())}
 assert payloads['play-local.bat']!=play
 guards=validator.table(c['guards'])
 for rel,body in payloads.items():
  p=server/rel;key=('server',rel.casefold())
  if key in guards:
   if sha(p)!=guards[key]['sha256']:raise RuntimeError('Parent target mismatch: '+rel)
  elif p.exists():raise RuntimeError('Unregistered target: '+rel)
  guards[key]=dict(root='server',relative=rel,sha256=digest(body))
 c.update(guards=list(guards.values()),files_verified=False)
 c.setdefault('ancestry',[]).append(dict(layer='protection-preview-fix-v1',native_status='PENDING'))
 revision='protection-preview-fix-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 m=dict(schema=1,revision=revision,client=str(client),state_shop_replaced=False,guards=c['guards'],composition=c,parent_preflight=parent_rel,parent_preflight_sha256=sha(parent_path))
 payloads[MANIFEST]=encoded(m);payloads[RECEIPT]=encoded(dict(status='INSTALLED_PREVIEW_FIX',revision=revision,manifest_sha256=digest(payloads[MANIFEST]),state_shop_replaced=False))
 assert set(payloads)==ALLOWED
 for rel in [SELF,MANIFEST,RECEIPT]:
  if (server/rel).exists():raise RuntimeError('Append-only metadata/config already exists: '+rel)
 before={rel:(server/rel).read_bytes() if (server/rel).exists() else None for rel in payloads}
 return dict(server=server,client=client,payloads=payloads,before=before,revision=revision,prior=prior,parent=parent_rel,parent_hash=sha(parent_path))
def apply(p,fail_after=None):
 if p.get('already_current'):return dict(status='ALREADY_CURRENT',preflight=p['preflight'],state_shop_written=False)
 closed()
 server=p['server'];backup=server/'backups'/p['revision'];backup.mkdir(parents=True)
 for n,(rel,body) in enumerate(p['before'].items()):
  if body is not None:(backup/(str(n)+'-'+Path(rel).name)).write_bytes(body)
 committed=[];order=[r for r in p['payloads'] if r!='play-local.bat']+['play-local.bat']
 try:
  if sha(server/p['parent'])!=p['parent_hash']:raise RuntimeError('Parent helper changed')
  for index,rel in enumerate(order,1):
   closed()
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
 closed()
 with locks(S):
  closed();p=plan()
  if p.get('already_current'):print(json.dumps(apply(p)))
  else:
   (R/'plan.json').write_bytes(encoded(dict(parent=p['parent'],parent_hash=p['parent_hash'],prior=p['prior'],files={r:digest(b) for r,b in p['payloads'].items()})));print('Current parent verified; prepared, no formal payload written')
