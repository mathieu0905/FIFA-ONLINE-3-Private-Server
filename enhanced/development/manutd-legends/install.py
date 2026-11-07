"""Direct, locked official install with exact-baseline and rollback protection."""
from pathlib import Path
from contextlib import contextmanager
import copy,datetime,hashlib,importlib.util,json,os,re,shutil,socket,subprocess,sys,time,uuid
from prepare import R,S,C,sha,write
sys.dont_write_bytecode=True
SELF='patches/manutd_legends_preflight.py';MANIFEST='patches/manutd-legends-installed.json';RECEIPT='patches/manutd-legends-receipt.json'
def body(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def digest(b):return hashlib.sha256(b).hexdigest()
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def env():
 e=dict(os.environ);e['PSModulePath']=r'C:\Windows\System32\WindowsPowerShell\v1.0\Modules;C:\Program Files\WindowsPowerShell\Modules';return e
@contextmanager
def locks():
 owned=[]
 try:
  for n in ('.shop-release.lock','.fo3-publish.lock'):
   p=S/n;fd=os.open(p,os.O_EXCL|os.O_CREAT|os.O_WRONLY|os.O_BINARY);b=body(dict(task='manutd-legends',pid=os.getpid(),thread='01a1b14e-63d0-7d13-a4a6-9e1f7d3b2b68'));owned.append((p,fd,b));os.write(fd,b);os.fsync(fd)
  yield
 finally:
  for p,fd,b in reversed(owned):
   os.close(fd)
   if p.exists() and p.read_bytes()==b:p.unlink()
def closed():
 r=subprocess.run(['powershell.exe','-NoProfile','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9}'],env=env(),creationflags=subprocess.CREATE_NO_WINDOW)
 if r.returncode:raise RuntimeError('Game active; installation needs a normally closed client')
def listening():
 ports=[]
 for p in (443,8088,28002):
  try:
   with socket.create_connection(('127.0.0.1',p),.3):ports.append(p)
  except OSError:pass
 return ports
def atomic(source,target):
 target.parent.mkdir(parents=True,exist_ok=True);tmp=target.with_name(target.name+'.mul-'+uuid.uuid4().hex)
 try:
  if isinstance(source,bytes):tmp.write_bytes(source)
  else:shutil.copyfile(source,tmp)
  os.replace(tmp,target)
 finally:tmp.unlink(missing_ok=True)
def fresh(build):
 for p,h in build['baseline'].items():
  if sha(p)!=h:raise RuntimeError('Fresh baseline changed; rebuild: '+p)
def plan():
 out=Path(json.loads((R/'latest-build.json').read_text('utf8'))['path']);build=json.loads((out/'build.json').read_text('utf8'));fresh(build)
 play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',play);assert len(matches)==1
 parent_rel=matches[0].decode().replace('\\','/');assert parent_rel!=SELF
 parent=load(S/parent_rel,'mul_parent');prior=parent.preflight(S,C);composition=copy.deepcopy(parent.compose_manifest(S,C));validator=load(S/'patches/startup_market_preflight.py','mul_validator');validator.verify_manifest(composition,S,C)
 table=validator.table(composition['guards']);helper=(S/parent_rel).read_text('utf8')
 # Derive the small strict guard from the current club-history implementation.
 assert parent_rel=='patches/club_history_preflight.py','Unexpected parent; adapt guard explicitly before installation'
 helper=helper.replace('club-history-installed.json','manutd-legends-installed.json').replace('club-history-receipt.json','manutd-legends-receipt.json').replace('club_history_preflight.py','manutd_legends_preflight.py').replace('INSTALLED_CLUB_HISTORY','INSTALLED_MANUTD_LEGENDS').replace('CLUB_HISTORY_PREFLIGHT_PASS','MANUTD_LEGENDS_PREFLIGHT_PASS').replace('club-history','manutd-legends')
 compile(helper,SELF,'exec')
 payload=[('server','gamedata/fifadb.sqlite',out/'fifadb.sqlite'),('client','data/data_0.big',out/'data_0.big'),('server','gamedata/custom_rosters.json',out/'custom_rosters.json'),('server','product_packs.py',out/'product_packs.py'),('server','gamedata/manutd_legends_products.json',out/'manutd_legends_products.json'),('server',SELF,helper.encode('utf8'))]
 for prefix in ('_cache/games/fo3id','_cache/cdn'):
  for face in build['portraits']:
   if face.get('missing'):continue
   rel=prefix+'/externalAssets/players/'+face['name'];target=C/rel
   if not target.exists() or sha(target)!=face['sha256']:payload.append(('client',rel,out/'portraits'/face['name']))
 payload.append(('server','play-local.bat',play.replace(matches[0],SELF.replace('/','\\').encode())))
 entries=[]
 for root,rel,source in payload:
  target=(S if root=='server' else C)/rel;before=sha(target) if target.exists() else None;after=digest(source) if isinstance(source,bytes) else sha(source);key=(root,rel.casefold())
  if key in table:assert table[key]['sha256']==before,('Guard changed',rel)
  elif target.exists():
   # Existing cache portraits can be unregistered; bind the observed byte hash.
   assert root=='client' and '/players/' in rel,('Unregistered target',rel)
  table[key]=dict(root=root,relative=rel,sha256=after);entries.append(dict(root=root,relative=rel,target=target,source=source,before=before,after=after))
 composition['guards']=list(table.values());composition['files_verified']=False;composition.setdefault('ancestry',[]).append(dict(layer='MUL-41-88-92',native_status='PENDING'))
 # Bind the current parent's immutable receipt even if its compose API omitted a policy.
 policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in json.loads((S/parent.RECEIPT).read_text('utf8')).items() if k!='native_status'})
 if not any(p['root']==policy['root'] and p['relative']==policy['relative'] for p in composition['receipt_policies']):composition['receipt_policies'].append(policy)
 revision='manutd-legends-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 m=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=composition['guards'],composition=composition,parent_preflight=parent_rel,parent_preflight_sha256=sha(S/parent_rel),cards=41,added=34,rating_basis=build['spec']['rating_basis'])
 mb=body(m);rb=body(dict(status='INSTALLED_MANUTD_LEGENDS',revision=revision,manifest_sha256=digest(mb),state_shop_replaced=False,native_status='PENDING'))
 for rel,source in ((MANIFEST,mb),(RECEIPT,rb)):
  assert not (S/rel).exists();entries.append(dict(root='server',relative=rel,target=S/rel,source=source,before=None,after=digest(source)))
 entries.sort(key=lambda e:e['relative']=='play-local.bat')
 return dict(entries=entries,revision=revision,build=build,parent=parent_rel,parent_hash=sha(S/parent_rel),prior=prior)
def commit(entries,backup,verify,fail_after=None,hook=None):
 backup.mkdir(parents=True,exist_ok=False);done=[];journal=[]
 for i,e in enumerate(entries):
  assert (sha(e['target']) if e['target'].exists() else None)==e['before'],'Target changed before backup'
  if e['before'] is not None:shutil.copyfile(e['target'],backup/str(i))
  journal.append({k:str(v) if isinstance(v,Path) else v for k,v in e.items() if k!='source'})
 write(backup/'transaction.json',dict(status='PREPARED',files=journal))
 try:
  for i,e in enumerate(entries):
   if hook:hook(i,e)
   assert (sha(e['target']) if e['target'].exists() else None)==e['before'],'Concurrent target change'
   atomic(e['source'],e['target']);done.append(i)
   if fail_after==i+1:raise OSError('Injected write failure')
  verify();write(backup/'transaction.json',dict(status='INSTALLED',files=journal))
 except BaseException:
  retained=[]
  for i in reversed(done):
   e=entries[i];target=e['target']
   if not target.exists() or sha(target)!=e['after']:retained.append(str(target));continue
   if e['before'] is None:target.unlink()
   else:atomic(backup/str(i),target)
  write(backup/'transaction.json',dict(status='ROLLED_BACK',files=journal,later_changes_retained=retained));raise
def restart():
 e=env();e.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20')
 with (S/'captures/manutd-legends-restart.log').open('ab') as log:subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-B','-u',str(S/'start_all.py')],cwd=S,env=e,stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
 subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'wait_services.py'),'--timeout','30'],cwd=S,env=e,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
def main():
 with locks():
  closed();p=plan();write(R/'status.json',dict(status='INSTALLING',formal_writer=True,revision=p['revision']))
  running=bool(listening());stopped=False;backup=S/'backups'/p['revision']
  try:
   if running:
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],env=env(),check=True,creationflags=subprocess.CREATE_NO_WINDOW);stopped=True
    deadline=time.monotonic()+12
    while listening():
     if time.monotonic()>deadline:raise RuntimeError('Service listeners remain')
     time.sleep(.2)
   closed();fresh(p['build']);assert sha(S/p['parent'])==p['parent_hash']
   protected={str(S/'gamedata'/n):sha(S/'gamedata'/n) for n in ('state.json','shop.json','pack_cadence.json','pack_catalogue.json','product_packs.json','product_chain_elite.json','shop_value_products.json','chain_rebalance_products.json')}
   snap=R/'fresh-stop-snapshot'/p['revision'];snap.mkdir(parents=True)
   for n in ('state.json','shop.json'):shutil.copyfile(S/'gamedata'/n,snap/n)
   def verify():
    load(S/SELF,'mul_installed').preflight(S,C)
    for path,h in protected.items():assert sha(path)==h,('Protected file changed',path)
   commit(p['entries'],backup,verify)
   result=dict(status='INSTALLED',revision=p['revision'],backup=str(backup),preflight=load(S/SELF,'mul_final').preflight(S,C),top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',cards=41,added=34,state_shop_written=False,protected_hashes=protected,native_status='PENDING',match_status='PENDING',hashes={str(t):sha(t) for t in (S/SELF,S/MANIFEST,S/RECEIPT,S/'play-local.bat',S/'gamedata/fifadb.sqlite',C/'data/data_0.big')})
   write(R/'installed-handback.json',result)
  finally:
   if running and stopped:restart()
  result['services_restored']=listening()==[443,8088,28002] if running else 'previously_stopped';write(R/'installed-handback.json',result);write(R/'status.json',dict(status='INSTALLED',formal_writer=False,handback=str(R/'installed-handback.json')))
  descriptor=R.parent/'root-current-top.json';prior=json.loads(descriptor.read_text('utf8'));prior.update(status='OBSERVED_MANUTD_LEGENDS_INSTALL',observed_at=datetime.datetime.now().astimezone().isoformat(),top_preflight=result['top_preflight'],top_manifest=result['top_manifest'],top_receipt=result['top_receipt'],files=result['hashes'],function_signatures=dict(sha='p',preflight='server=None, client=None',compose_manifest='server=None, client=None'),composition_available=True,physical_preflight_run_by_this_observer=True,state_shop_written=False,GUI_status='Native and match pending; no GUI operations',services_restored=result['services_restored']);atomic(body(prior),descriptor)
  print(json.dumps(result,ensure_ascii=True))
if __name__=='__main__':main()
