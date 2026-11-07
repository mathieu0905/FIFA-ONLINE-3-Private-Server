"""Install item icons directly into the current official version under shared locks."""
from pathlib import Path
from contextlib import contextmanager
import sys,os,json,re,copy,datetime,hashlib,subprocess,socket,time,importlib.util
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path.insert(0,str(R.parent/'manutd-legends'))
spec=importlib.util.spec_from_file_location('verified_transaction_helper',R.parent/'manutd-legends/install.py');tx=importlib.util.module_from_spec(spec);spec.loader.exec_module(tx)
SELF='patches/chain_caption_preflight.py';MANIFEST='patches/chain-caption-installed.json';RECEIPT='patches/chain-caption-receipt.json'
def sha(p):return tx.sha(p)
def body(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body(v))
def plan():
 play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z0-9_]+_preflight\.py',play);assert len(matches)==1
 rel=matches[0].decode().replace('\\','/');parent_relative=rel;parent=tx.load(S/rel,'icons_parent');prior=parent.preflight(S,C)
 composition=copy.deepcopy(parent.compose_manifest(S,C));table={(x['root'],x['relative'].replace('\\','/').casefold()):x for x in composition['guards']}
 assert len(table)==len(composition['guards'])
 # Derive the new guard from the current guard; keep all inherited validation.
 helper=(S/rel).read_text('utf8')
 helper=helper.replace(parent.MANIFEST,MANIFEST).replace(parent.RECEIPT,RECEIPT).replace(parent.SELF,SELF)
 receipt=json.loads((S/parent.RECEIPT).read_text('utf8'));old_status=receipt['status'];helper=helper.replace(old_status,'INSTALLED_CHAIN_CAPTION')
 old_pre=prior['status'];helper=helper.replace(old_pre,'CHAIN_CAPTION_PREFLIGHT_PASS')
 compile(helper,SELF,'exec')
 build=json.loads((R/'build.json').read_text('utf8'));assert sha(S/'product_packs.py')==build['server_before'];assert sha(C/'data/ui/components/TileList.big')==build['client_before']
 payload=[('server','patches/TileList.big',R/'TileList.big'),('client','data/ui/components/TileList.big',R/'TileList.big'),('server',SELF,helper.encode('utf8'))]
 payload.append(('server','play-local.bat',play.replace(matches[0],SELF.replace('/','\\').encode())))
 entries=[]
 for root,rel,src in payload:
  target=(S if root=='server' else C)/rel;before=sha(target) if target.exists() else None;after=hashlib.sha256(src).hexdigest() if isinstance(src,bytes) else sha(src);key=(root,rel.casefold())
  if key in table:assert table[key]['sha256']==before,('Changed baseline',rel)
  else:assert before is None,('Unregistered existing file',rel)
  table[key]=dict(root=root,relative=rel,sha256=after)
  entries.append(dict(root=root,relative=rel,target=target,source=src,before=before,after=after))
 composition['guards']=list(table.values());composition['files_verified']=False
 composition.setdefault('ancestry',[]).append(dict(layer='CHAIN-CAPTION',native_status='PENDING'))
 policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in receipt.items() if k!='native_status'})
 if not any(x['root']==policy['root'] and x['relative']==policy['relative'] for x in composition.setdefault('receipt_policies',[])):composition['receipt_policies'].append(policy)
 revision='chain-caption-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 m=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=composition['guards'],composition=composition,parent_preflight=parent_relative,fix_count=1)
 mb=body(m);rb=body(dict(status='INSTALLED_CHAIN_CAPTION',revision=revision,manifest_sha256=hashlib.sha256(mb).hexdigest(),state_shop_replaced=False,native_status='PENDING'))
 for relative,src in ((MANIFEST,mb),(RECEIPT,rb)):
  assert not (S/relative).exists();entries.append(dict(root='server',relative=relative,target=S/relative,source=src,before=None,after=hashlib.sha256(src).hexdigest()))
 entries.sort(key=lambda e:e['relative']=='play-local.bat')
 return dict(entries=entries,revision=revision,parent=parent,prior=prior,fixes=1)
@contextmanager
def locks():
 held=[]
 try:
  for name in ('.shop-release.lock','.fo3-publish.lock'):
   p=S/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);raw=body(dict(task='chain-caption',pid=os.getpid()));os.write(fd,raw);os.fsync(fd);held.append((p,fd,raw))
  yield
 finally:
  for p,fd,raw in reversed(held):
   os.close(fd)
   if p.exists() and p.read_bytes()==raw:p.unlink()
def restart():
 env=tx.env();env.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20')
 with (S/'captures/chain-ui-restart.log').open('ab') as log:
  subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-B','-u',str(S/'start_all.py')],cwd=S,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
 subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'wait_services.py'),'--timeout','30'],cwd=S,env=env,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
def main():
 if '--plan' in sys.argv:
  p=plan();out=dict(status='READY_FOR_OFFICIAL_INSTALL',fixes=p['fixes'],files=len(p['entries']),parent_preflight=p['prior'],client_must_be_closed=True,state_shop_written=False)
  write(R/'install-plan.json',out);print(json.dumps(out));return
 with locks():
  coord=json.loads((R.parent/'coordination-current.json').read_text('utf8'))
  assert not coord.get('current_unhanded_writers') and coord.get('next_formal_writer') is None,'Coordination window occupied'
  tx.closed();p=plan();running=bool(tx.listening());stopped=False
  try:
   if running:
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],env=tx.env(),check=True,creationflags=subprocess.CREATE_NO_WINDOW);stopped=True
    deadline=time.monotonic()+15
    while tx.listening():
     if time.monotonic()>deadline:raise RuntimeError('Services still listening')
     time.sleep(.2)
   tx.closed()
   # This is the fresh live snapshot at this transaction's stop, never restored over progress.
   snap=R/'fresh-stop-snapshot'/p['revision'];snap.mkdir(parents=True)
   protected={}
   for name in ('state.json','shop.json'):
    source=S/'gamedata'/name;protected[str(source)]=sha(source);(snap/name).write_bytes(source.read_bytes())
   def verify():
    tx.load(S/SELF,'icons_installed').preflight(S,C)
    for name,value in protected.items():assert sha(name)==value,('Live data changed',name)
   backup=S/'backups'/p['revision'];tx.commit(p['entries'],backup,verify)
   result=dict(status='INSTALLED',revision=p['revision'],fixes=p['fixes'],backup=str(backup),preflight=tx.load(S/SELF,'icons_final').preflight(S,C),top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',state_shop_written=False,protected_hashes=protected,native_status='PENDING',hashes={str(q):sha(q) for q in (S/SELF,S/MANIFEST,S/RECEIPT,S/'play-local.bat')})
   write(R/'installed-handback.json',result)
  finally:
   if running and stopped:restart()
  result['services_restored']=tx.listening()==[443,8088,28002] if running else 'previously_stopped';write(R/'installed-handback.json',result)
  path=R.parent/'root-current-top.json';d=json.loads(path.read_text('utf8'));d.update(status='OBSERVED_CHAIN_CAPTION_INSTALL',observed_at=datetime.datetime.now().astimezone().isoformat(),top_preflight=result['top_preflight'],top_manifest=result['top_manifest'],top_receipt=result['top_receipt'],files=result['hashes'],function_signatures=dict(sha='p',preflight='server=None, client=None',compose_manifest='server=None, client=None'),composition_available=True,physical_preflight_run_by_this_observer=True,state_shop_written=False,services_restored=result['services_restored'],GUI_status='Native pending; no GUI operations',handoff=str(R/'installed-handback.json'))
  tx.atomic(body(d),path);print(json.dumps(result))
if __name__=='__main__':main()
