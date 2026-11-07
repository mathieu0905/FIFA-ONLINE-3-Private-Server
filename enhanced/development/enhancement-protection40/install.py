from pathlib import Path
from contextlib import contextmanager
import sys,os,json,re,datetime,importlib.util,subprocess,copy,shutil,tempfile
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path.insert(0,str(S.parent.parent/'fifaol3'));import install_bulk_seasons as tx
MANIFEST='patches/protection40-installed.json';RECEIPT='patches/protection40-receipt.json';SELF='patches/protection40_preflight.py'
NAMES=('TeamManagementPlayerEnhancementTabPage','TeamManagementPlayerEnhancingPopupScreen')
TARGETS={('server','http_config.py'),('server','enhancement_protection40.py'),('server','play-local.bat'),('server',SELF)}|{('client','data/ui/'+n+'.big') for n in NAMES}|{('server','patches/'+n+'.big') for n in NAMES}
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def gameclosed():
 text=subprocess.check_output(['tasklist','/FI','IMAGENAME eq fifazf.exe','/FO','CSV','/NH'],text=True,errors='replace')
 if 'fifazf.exe' in text.lower():raise RuntimeError('Game active; wait for human to close normally')

@contextmanager
def locks(server=S):
 held=[]
 try:
  for name in ('.shop-release.lock','.fo3-publish.lock'):
   path=server/name;fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY)
   token=json.dumps({'task':'protection40','pid':os.getpid()}).encode();os.write(fd,token);os.close(fd);held.append((path,token))
  yield
 finally:
  for path,token in reversed(held):
   if path.exists() and path.read_bytes()==token:path.unlink()

def prepare():
 play=(S/'play-local.bat').read_bytes();names=re.findall(rb'patches\\([A-Za-z0-9_]+_preflight\.py)',play);assert len(names)==1
 parent_path='patches/'+names[0].decode();parent=load(S/parent_path,'protection40_parent')
 proof=parent.preflight(S,C);composed=parent.compose_manifest(S,C)
 guards=copy.deepcopy(composed['guards']);index={(r['root'],r['relative'].casefold()):i for i,r in enumerate(guards)}
 raw=(S/'http_config.py').read_bytes();needle=b'if __name__ == "__main__":';assert raw.count(needle)==1 and b'import enhancement_protection40' not in raw
 nl=b'\r\n' if b'\r\n' in raw else b'\n'
 insert=nl.join([b'import enhancement_protection40',b'enhancement_protection40.install(sys.modules[__name__])',b'',b''])
 (W/'http_config.py').write_bytes(raw.replace(needle,insert+needle));compile((W/'http_config.py').read_text(encoding='utf-8-sig'),'http_config.py','exec')
 (W/'play-local.bat').write_bytes(play.replace(b'patches\\'+names[0],b'patches\\protection40_preflight.py'))
 template=(S/'patches/player_capacity_preflight.py').read_text(encoding='utf-8')
 # This exact-file parent template is composed from all latest independent layers.
 # Parent API must pass exact physical proof; frozen simple capacity gate supplies only generic validation code.
 template=template.replace('player-capacity','protection40').replace('player_capacity','protection40').replace('PLAYER_CAPACITY','PROTECTION40')
 old="required={('client','data/ui/teammanagementexpcapsulescreen.big'),('server','experience_levels.py'),('server','http_config.py'),('server','play-local.bat'),('server','patches/protection40_preflight.py')}"
 assert old in template
 required=sorted((r,k.casefold()) for r,k in TARGETS)
 template=template.replace(old,'required='+repr(set(required)))
 (W/'protection40_preflight.py').write_text(template,encoding='utf-8')
 payloads=[('server','enhancement_protection40.py',W/'enhancement_protection40.py'),('server','http_config.py',W/'http_config.py')]
 for n in NAMES:payloads.extend([('client','data/ui/'+n+'.big',W/(n+'.big')),('server','patches/'+n+'.big',W/(n+'.big'))])
 payloads.extend([('server',SELF,W/'protection40_preflight.py'),('server','play-local.bat',W/'play-local.bat')])
 files=[]
 for root,relative,source in payloads:
  row=dict(root=root,relative=relative,source=str(source),parent_sha256=tx.digest((S if root=='server' else C)/relative),sha256=tx.sha(source));files.append(row)
  key=(root,relative.casefold());guard={k:row[k] for k in ('root','relative','sha256')}
  if key in index:guards[index[key]]=guard
  else:index[key]=len(guards);guards.append(guard)
 assert {(r['root'],r['relative']) for r in files}==TARGETS
 composition=copy.deepcopy(composed);composition['guards']=guards;composition['files_verified']=False
 composition.setdefault('ancestry',[]).append(dict(layer='protection40',native_status='NOT_VERIFIED'))
 revision='protection40-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 m=dict(schema=1,revision=revision,client=str(C),guards=guards,composition=composition,state_shop_replaced=False,
        files=files,parent_files={p:tx.sha(S/p) for p in (parent_path,parent.MANIFEST,parent.RECEIPT)},parent_preflight=parent_path,
        rule=dict(fraction_percent=40,base='target pre-attempt player_value_price',ordinary_fee_replaced=True,charged_every_attempt=True),native_status='NOT_VERIFIED')
 tx.atomic_json(W/'manifest.json',m);tx.atomic_json(W/'prepared.json',dict(status='PREPARED',parent_proof=proof,manifest_sha256=tx.sha(W/'manifest.json')))
 return m

def verify_parent(m):
 for path,digest in m['parent_files'].items():assert tx.sha(S/path)==digest,('Parent meta drift',path)
 load(S/m['parent_preflight'],'protection40_parent_now').preflight(S,C)
 for row in m['files']:
  assert tx.sha(row['source'])==row['sha256']
  assert tx.digest(tx.target({'server':S,'client':C},row))==row['parent_sha256'],('Payload drift',row['relative'])
 assert not (S/MANIFEST).exists() and not (S/RECEIPT).exists()

def install():
 m=tx.read(W/'manifest.json')
 if (S/RECEIPT).exists():return load(S/SELF,'protection40_installed').preflight(S,C)
 assert {(r['root'],r['relative']) for r in m['files']}==TARGETS
 gameclosed()
 with locks():
  gameclosed();verify_parent(m)
  backup=S/'backups'/m['revision'];backup.mkdir()
  protected={n:tx.digest(S/'gamedata'/n) for n in ('state.json','shop.json','enhancement_rates.json','pack_cadence.json','pack_catalogue.json','product_packs.json')}
  for name,digest in protected.items():
   if digest is not None:shutil.copyfile(S/'gamedata'/name,backup/('audit-'+name))
  receipt=dict(status='INSTALLED_PROTECTION40',revision=m['revision'],manifest_sha256=tx.sha(W/'manifest.json'),state_shop_replaced=False,backup=str(backup))
  tx.atomic_json(backup/'receipt-candidate.json',receipt)
  entries=[r for r in m['files'] if r['relative']!='play-local.bat']+[
    dict(root='server',relative=MANIFEST,source=str(W/'manifest.json'),parent_sha256=None,sha256=tx.sha(W/'manifest.json')),
    dict(root='server',relative=RECEIPT,source=str(backup/'receipt-candidate.json'),parent_sha256=None,sha256=tx.sha(backup/'receipt-candidate.json')),
    next(r for r in m['files'] if r['relative']=='play-local.bat')]
  def validate():
   gameclosed();verify_parent(m)
   assert all(tx.digest(S/'gamedata'/n)==v for n,v in protected.items())
  transaction=tx.commit_transaction({'server':S,'client':C},entries,backup,validate)
  try:
   proof=load(S/SELF,'protection40_installed').preflight(S,C)
   assert all(tx.digest(S/'gamedata'/n)==v for n,v in protected.items())
   transaction.update(status='installed',preflight=proof,protected=protected);tx.atomic_json(backup/'transaction.json',transaction)
  except BaseException:
   tx.restore_completed({'server':S,'client':C},transaction,backup);raise
  result=dict(status='FORMAL_FILES_INSTALLED',runtime_status='PENDING_SERVICE_RELOAD',native_status='NOT_VERIFIED',preflight=proof,backup=str(backup),protected=protected,source_hashes={r['relative']:r['sha256'] for r in m['files']},meta_hashes={p:tx.sha(S/p) for p in (SELF,MANIFEST,RECEIPT)})
  tx.atomic_json(W/'installed.json',result);return result

if __name__=='__main__':
 print(json.dumps(prepare() if sys.argv[1:] == ['prepare'] else install(),ensure_ascii=True,indent=2))
