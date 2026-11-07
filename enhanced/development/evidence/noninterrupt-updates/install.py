from pathlib import Path
import copy,datetime,hashlib,importlib.util,json,os,re,sys
sys.dont_write_bytecode=True
R=Path(__file__).parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');W=Path('D:/fifaol3')
sys.path.insert(0,str(W/'manutd-legends'))
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
tx=load(W/'manutd-legends/install.py','noninterrupt_transaction')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def body(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
SELF='patches/noninterrupt_preflight.py';MANIFEST='patches/noninterrupt-installed.json';RECEIPT='patches/noninterrupt-receipt.json'
def main():
 tests=json.loads((R/'tests.json').read_text('utf-8-sig'));assert tests['status']=='PASS' and tests['powershell'].startswith('5.1.')
 held=[]
 try:
  for name in ('.shop-release.lock','.fo3-publish.lock'):
   p=S/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);token=body(dict(task='noninterrupt-updates',pid=os.getpid()));held.append((p,fd,token));os.write(fd,token);os.fsync(fd)
  coord=json.loads((W/'coordination-current.json').read_text('utf8'));assert not coord.get('current_unhanded_writers') and coord.get('next_formal_writer') is None
  rows=json.loads((R/'prepared.json').read_text('utf8'))
  for row in rows:assert sha(Path(row['target']))==row['before'],('Rebase required',row['target'])
  play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z0-9_]+_preflight\.py',play);assert len(matches)==1
  parent_rel=matches[0].decode().replace('\\','/');parent=load(S/parent_rel,'noninterrupt_parent');prior=parent.preflight(S,C)
  comp=copy.deepcopy(parent.compose_manifest(S,C));table={(g['root'],g['relative'].replace('\\','/').casefold()):g for g in comp['guards']};assert len(table)==len(comp['guards'])
  receipt=json.loads((S/parent.RECEIPT).read_text('utf8'))
  helper=(S/parent_rel).read_text('utf8').replace(parent.MANIFEST,MANIFEST).replace(parent.RECEIPT,RECEIPT).replace(parent.SELF,SELF).replace(receipt['status'],'INSTALLED_NONINTERRUPT').replace(prior['status'],'NONINTERRUPT_PREFLIGHT_PASS');compile(helper,SELF,'exec')
  rows+=[dict(target=str(S/SELF),source_bytes=helper.encode(),root='server',relative=SELF,before=None),dict(target=str(S/'play-local.bat'),source_bytes=play.replace(matches[0],SELF.replace('/','\\').encode()),root='server',relative='play-local.bat',before=sha(S/'play-local.bat'))]
  entries=[]
  for row in rows:
   target=Path(row['target']);data=row['source_bytes'] if 'source_bytes' in row else Path(row['source']).read_bytes();after=hashlib.sha256(data).hexdigest()
   assert (sha(target) if target.exists() else None)==row['before']
   if row['root']=='server':
    key=('server',row['relative'].casefold())
    if key in table:assert table[key]['sha256']==row['before'],('Guard baseline changed',row['relative'])
    table[key]=dict(root='server',relative=row['relative'],sha256=after)
   entries.append(dict(root=row['root'],relative=row['relative'],target=target,source=data,before=row['before'],after=after))
  comp.update(guards=list(table.values()),files_verified=False);comp.setdefault('ancestry',[]).append(dict(layer='noninterrupt-updates',native_status='PENDING'))
  policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in receipt.items() if k!='native_status'})
  if not any(p['root']==policy['root'] and p['relative']==policy['relative'] for p in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(policy)
  revision='noninterrupt-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup=S/'backups'/revision
  mb=body(dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_rel))
  rb=body(dict(status='INSTALLED_NONINTERRUPT',revision=revision,manifest_sha256=hashlib.sha256(mb).hexdigest(),state_shop_replaced=False,native_status='PENDING'))
  for rel,data in ((MANIFEST,mb),(RECEIPT,rb)):
   assert not (S/rel).exists();entries.append(dict(root='server',relative=rel,target=S/rel,source=data,before=None,after=hashlib.sha256(data).hexdigest()))
  entries.sort(key=lambda e:e['relative']=='play-local.bat')
  tx.commit(entries,backup,lambda:load(S/SELF,'noninterrupt_installed').preflight(S,C))
  result=dict(status='INSTALLED_NONINTERRUPT',backup=str(backup),preflight=load(S/SELF,'noninterrupt_final').preflight(S,C),top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_available=True,function_signatures=dict(preflight='server=None,client=None',compose_manifest='server=None,client=None'),files={str(p):sha(p) for p in (S/SELF,S/MANIFEST,S/RECEIPT,S/'play-local.bat',S/'stop-server.ps1',S/'AGENTS.md')},services_action='No service stop/start/restart; no game action',state_shop_written=False,tests=tests,native_verified=False,match_verified=False,observed_at=datetime.datetime.now().astimezone().isoformat(),handoff=str(R/'installed-handback.json'))
  (R/'installed-handback.json').write_bytes(body(result));tx.atomic(body(result),W/'root-current-top.json');print(json.dumps(result,ensure_ascii=True))
 finally:
  for p,fd,token in reversed(held):
   os.close(fd)
   if p.exists() and p.read_bytes()==token:p.unlink()
if __name__=='__main__':main()
