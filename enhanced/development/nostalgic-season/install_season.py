"""Prepare/install a reversible season19 transaction during coordinator writer window."""
from pathlib import Path
import argparse,copy,datetime,hashlib,importlib.util,json,os,re,shutil,socket,subprocess,sys,time,uuid
sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');B=R/'build-v2/database';U=R/'build-v1/ui'
MANIFEST='patches/nostalgia-installed.json';RECEIPT='patches/nostalgia-receipt.json';SELF='patches/nostalgia_preflight.py'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),'utf-8')
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def parent():
 text=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',text);assert len(matches)==1
 rel=matches[0].decode().replace('\\','/');assert rel!=SELF,'Already installed; use existing preflight'
 mod=load(S/rel,'nostalgia_parent');proof=mod.preflight(S,C);composition=mod.compose_manifest(S,C)
 return rel,mod,composition,text,matches[0],proof
def sources():
 d=read(B/'manifest.json');u=read(U/'ui-manifest.json');seal=read(R/'sealed-result.json')
 assert seal['database_manifest_sha256']==sha(B/'manifest.json') and seal['ui_manifest_sha256']==sha(U/'ui-manifest.json')
 for n,h in d['outputs'].items():assert sha(B/n)==h,'Modified payload '+n
 for n,h in u['output_hashes'].items():assert sha(U/n)==h,'Modified UI '+n
 for n in ('database','data0','registry','roster'):
  row=d['source_files'][n];assert sha(row['path'])==row['sha256'],'Rebuild required: '+row['path']
 for path,h in u['source_hashes'].items():assert sha(path)==h,'Rebase UI required: '+path
 return d,u
def prepare(out):
 out=Path(out).resolve();assert out.is_relative_to(R) and not out.exists();d,u=sources();rel,p,comp,play,old,proof=parent()
 out.mkdir(parents=True);rows=[]
 def add(root,relative,source):
  target=(S if root=='server' else C)/relative;source=Path(source).resolve()
  before=sha(target) if target.exists() else None
  rows.append(dict(root=root,relative=relative,source=str(source),parent_sha256=before,sha256=sha(source)))
 for n in ('fifadb.sqlite','custom_rosters.json'):add('server','gamedata/'+n,B/n)
 add('server','responses/static_roster.json',B/'static_roster.json');add('client','data/data_0.big',B/'data_0.big')
 add('client','data/ui/libs/Module.big',U/'Module.big')
 for n in ('Label.big','PlayerInfoNew.big'):
  add('client','data/ui/components/'+n,U/n);add('server','patches/'+n,U/n)
 add('server','patches/language_chi.big',U/'language_chi.big')
 for prefix in ('_cache/games/fo3id','_cache/cdn'):
  add('client',prefix+'/externalAssets/language_chi.big',U/'language_chi.big')
  for face in d['portraits']:
   assert sha(B/'portraits'/face['name'])==face['sha256']
   add('client',prefix+'/externalAssets/players/'+face['name'],B/'portraits'/face['name'])
 check=read(S/'patches/验证结果.json');check.update(sha256=sha(U/'language_chi.big'),package_bytes=(U/'language_chi.big').stat().st_size,result_keys=13159,latest_roster_import='nostalgia-beasts-v1',nostalgia_native_validation='PENDING')
 # Derive exact key count; never assume the previous dictionary's size.
 sys.path.insert(0,str(S/'tools/re'));import bigdir
 check['result_keys']=len(json.loads(bigdir.read(U/'language_chi.big','data/ui/external/LANGUAGESTRING_CHI.json')))
 write(out/'language-check.json',check);add('server','patches/验证结果.json',out/'language-check.json')
 (out/'play-local.bat').write_bytes(play.replace(old,b'patches\\nostalgia_preflight.py'));add('server','play-local.bat',out/'play-local.bat');add('server',SELF,R/'nostalgia_preflight.py')
 guards={(r['root'],r['relative'].replace('\\','/').casefold()):dict(r) for r in comp['guards']};assert len(guards)==len(comp['guards'])
 for row in rows:
  key=(row['root'],row['relative'].casefold());prior=guards.get(key)
  if prior:assert prior['sha256']==row['parent_sha256'],('Parent guard mismatch',key)
  guards[key]={k:row[k] for k in ('root','relative','sha256')}
 assert not any(key in guards for key in (('server',MANIFEST),('server',RECEIPT)))
 comp=copy.deepcopy(comp);comp['guards']=list(guards.values());comp.setdefault('ancestry',[]).append(dict(layer='nostalgia',season=19,cards=88,native_status='PENDING'))
 revision='nostalgia-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
 m=dict(schema=1,revision=revision,season=19,card_count=88,client=str(C),guards=list(guards.values()),composition=comp,files=rows,parent_files={n:sha(S/n) for n in (rel,p.MANIFEST,p.RECEIPT)},state_shop_replaced=False,native_status='PENDING',database_manifest_sha256=sha(B/'manifest.json'),ui_manifest_sha256=sha(U/'ui-manifest.json'))
 write(out/'nostalgia-installed.json',m)
 result=dict(status='PREPARED_NOT_INSTALLED',release=str(out),revision=revision,payloads=len(rows),manifest_sha256=sha(out/'nostalgia-installed.json'),parent=rel,parent_preflight=proof)
 write(out/'prepare-result.json',result);print(json.dumps(result,ensure_ascii=False,indent=2));return result
def closed():
 r=subprocess.run(['tasklist','/FI','IMAGENAME eq fifazf.exe','/FO','CSV','/NH'],capture_output=True,text=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
 if 'fifazf.exe' in r.stdout.lower():raise RuntimeError('游戏仍在运行；退出后才能安装怀旧赛季')
def listening(port):
 try:
  with socket.create_connection(('127.0.0.1',port),.3):return True
 except OSError:return False
def install(folder,expected,manage_services=False):
 folder=Path(folder).resolve();assert folder.is_relative_to(R)
 path=folder/'nostalgia-installed.json';assert sha(path)==expected;m=read(path)
 assert m['season']==19 and m['card_count']==88 and m['state_shop_replaced'] is False
 def fresh():
  sources();parent()
  for n,h in m['parent_files'].items():assert sha(S/n)==h,'Parent changed: '+n
  for row in m['files']:
   source=Path(row['source']);assert sha(source)==row['sha256'],'Payload changed'
   root=S if row['root']=='server' else C;target=(root/row['relative']).resolve();assert target.is_relative_to(root)
   assert (sha(target) if target.exists() else None)==row['parent_sha256'],'Formal file changed: '+str(target)
 fresh();closed()
 if not manage_services and any(listening(p) for p in (443,8088,28002)):raise RuntimeError('服务仍在运行；本安装器默认不自动停服或重启。等待人类重启通知及协调窗口。')
 lock=S/'.shop-release.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);os.write(fd,str(os.getpid()).encode());os.close(fd)
 second=S/'.fo3-publish.lock'
 try:
  fd=os.open(second,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);os.write(fd,str(os.getpid()).encode());os.close(fd)
 except BaseException:
  lock.unlink();raise
 was_running=listening(443);stopped=False
 sys.path.insert(0,str(S));from player_editor.publish_database import transaction
 try:
  fresh();closed()
  if was_running:
   subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],capture_output=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW);stopped=True
  for _ in range(60):
   if not any(listening(p) for p in (443,8088,28002)):break
   time.sleep(.2)
  else:raise RuntimeError('Service listeners remain; installation refused')
  closed();fresh()
  protected={str(p):sha(p) for p in [S/'gamedata'/n for n in ('state.json','shop.json','pack_cadence.json','pack_catalogue.json','product_packs.json')]}
  backup=S/'backups'/m['revision'];stage=folder/'installation';stage.mkdir()
  receipt=dict(status='INSTALLED_NOSTALGIA',manifest_sha256=expected,revision=m['revision'],backup=str(backup),native_status='PENDING',state_shop_replaced=False)
  write(stage/'nostalgia-receipt.json',receipt)
  pairs=[(Path(r['source']),(S if r['root']=='server' else C)/r['relative']) for r in m['files']]
  pairs.extend([(path,S/MANIFEST),(stage/'nostalgia-receipt.json',S/RECEIPT)])
  def verify():
   assert all(sha(p)==h for p,h in protected.items()),'Protected state/shop/probabilities changed'
   load(S/SELF,'installed_nostalgia').preflight(S,C)
  transaction(pairs,backup,verify)
  result=dict(status='INSTALLED_NATIVE_PENDING',revision=m['revision'],backup=str(backup),preflight=load(S/SELF,'installed_nostalgia_proof').preflight(S,C),protected_unchanged=True,protected=protected)
  write(folder/'installed-result.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
 finally:
  second.unlink(missing_ok=True);lock.unlink(missing_ok=True)
  if stopped:
   env={**os.environ,'FO3_GAME':str(C),'FO3_LANGUAGE':'chi','FO3_MAX_GRADE':'20'}
   with (folder/'service-restart.log').open('ab') as log:subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-B','-u',str(S/'start_all.py')],cwd=S,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('operation',choices=('prepare','install'));p.add_argument('--folder',required=True);p.add_argument('--sha');p.add_argument('--manage-services',action='store_true',help='Only after a new human restart notice and coordinator writer window');a=p.parse_args()
 if a.operation=='prepare':prepare(a.folder)
 else:
  assert a.sha;install(a.folder,a.sha,a.manage_services)
