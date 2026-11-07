from pathlib import Path
from contextlib import contextmanager, nullcontext
import sys,os,json,re,datetime,importlib.util,copy,shutil,subprocess
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path.insert(0,r'D:\fifaol3');import install_bulk_seasons as tx
MANIFEST='patches/progression20-installed.json';RECEIPT='patches/progression20-receipt.json';SELF='patches/progression20_preflight.py'
TARGETS={('server',p) for p in ('enhancement_progression.py','enhancement_settings.py','http_config.py','enhancement_protection40.py','admin/index.html',SELF,'play-local.bat','patches/TeamManagementPlayerEnhancingPopupScreen.big')}|{('client','data/ui/TeamManagementPlayerEnhancingPopupScreen.big')}
def load(p,n):
 spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def gameclosed():
 out=subprocess.check_output(['tasklist','/FI','IMAGENAME eq fifazf.exe','/FO','CSV','/NH'],text=True,errors='replace')
 if 'fifazf.exe' in out.lower():raise RuntimeError('Wait for human to finish and close game normally')

@contextmanager
def locks(server=S):
 held=[]
 try:
  for name in ('.shop-release.lock','.fo3-publish.lock'):
   p=server/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);token=json.dumps(dict(pid=os.getpid(),task='progression20')).encode();os.write(fd,token);os.close(fd);held.append((p,token))
  yield
 finally:
  for p,token in reversed(held):
   if p.exists() and p.read_bytes()==token:p.unlink()

def prepare():
 play=(S/'play-local.bat').read_bytes();names=re.findall(rb'patches\\([A-Za-z0-9_]+_preflight\.py)',play);assert len(names)==1
 parent_path='patches/'+names[0].decode();parent=load(S/parent_path,'progression20_parent');proof=parent.preflight(S,C);composed=parent.compose_manifest(S,C)
 (W/'play-local.bat').write_bytes(play.replace(b'patches\\'+names[0],b'patches\\progression20_preflight.py'))
 template=(S/'patches/reward_upgrade_preflight.py').read_text(encoding='utf-8')
 template=template.replace('reward-upgrade','progression20').replace('reward_upgrade','progression20').replace('REWARD_UPGRADE','PROGRESSION20')
 required="required={('server','gamedata/fifadb.sqlite'),('client','data/data_0.big'),('server','play-local.bat'),('server',SELF)}"
 assert required in template
 template=template.replace(required,'required='+repr({(r,p.casefold()) for r,p in TARGETS}))
 (W/'progression20_preflight.py').write_text(template,encoding='utf-8')
 payloads=[('server','enhancement_progression.py','enhancement_progression.py'),('server','enhancement_settings.py','enhancement_settings.py'),('server','http_config.py','http_config.py'),('server','enhancement_protection40.py','enhancement_protection40.py'),('server','admin/index.html','index.html'),('client','data/ui/TeamManagementPlayerEnhancingPopupScreen.big','TeamManagementPlayerEnhancingPopupScreen.big'),('server','patches/TeamManagementPlayerEnhancingPopupScreen.big','TeamManagementPlayerEnhancingPopupScreen.big'),('server',SELF,'progression20_preflight.py'),('server','play-local.bat','play-local.bat')]
 files=[];guards={(r['root'],r['relative'].replace('\\','/').casefold()):copy.deepcopy(r) for r in composed['guards']}
 for root,relative,src in payloads:
  row=dict(root=root,relative=relative,source=str(W/src),parent_sha256=tx.digest((S if root=='server' else C)/relative),sha256=tx.sha(W/src));files.append(row);guards[(root,relative.casefold())]={k:row[k] for k in ('root','relative','sha256')}
 assert {(r['root'],r['relative']) for r in files}==TARGETS
 composition=copy.deepcopy(composed);composition['guards']=list(guards.values());composition['files_verified']=False
 composition.setdefault('ancestry',[]).append(dict(layer='progression20',native_status='NOT_VERIFIED'))
 revision='progression20-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 m=dict(schema=1,revision=revision,client=str(C),guards=list(guards.values()),composition=composition,state_shop_replaced=False,files=files,
  parent_preflight=parent_path,parent_files={p:tx.sha(S/p) for p in (parent_path,parent.MANIFEST,parent.RECEIPT)},native_status='NOT_VERIFIED',custom_rates_replaced=False)
 tx.atomic_json(W/'manifest.json',m);tx.atomic_json(W/'prepared.json',dict(status='PREPARED',parent_proof=proof,manifest_sha256=tx.sha(W/'manifest.json')))
 return dict(revision=revision,files=len(m['guards']),payloads=len(files),parent=parent_path)

def verify_parent(m):
 for path,digest in m['parent_files'].items():assert tx.sha(S/path)==digest,('Parent metadata changed',path)
 load(S/m['parent_preflight'],'progression20_current_parent').preflight(S,C)
 for row in m['files']:
  assert tx.sha(row['source'])==row['sha256']
  assert tx.digest(tx.target({'server':S,'client':C},row))==row['parent_sha256'],('Source target changed',row['relative'])
 assert not (S/MANIFEST).exists() and not (S/RECEIPT).exists()

def install(locked=False):
 m=tx.read(W/'manifest.json')
 if (S/RECEIPT).exists():return load(S/SELF,'progression20_existing').preflight(S,C)
 assert {(r['root'],r['relative']) for r in m['files']}==TARGETS
 gameclosed()
 with (nullcontext() if locked else locks()):
  gameclosed();verify_parent(m);backup=S/'backups'/m['revision'];backup.mkdir()
  protected={n:tx.digest(S/'gamedata'/n) for n in ('state.json','shop.json','enhancement_rates.json','pack_cadence.json','pack_catalogue.json','product_packs.json')}
  for n,d in protected.items():
   if d is not None:shutil.copyfile(S/'gamedata'/n,backup/('audit-'+n))
  receipt=dict(status='INSTALLED_PROGRESSION20',revision=m['revision'],manifest_sha256=tx.sha(W/'manifest.json'),state_shop_replaced=False,backup=str(backup))
  tx.atomic_json(backup/'receipt-candidate.json',receipt)
  entries=[r for r in m['files'] if r['relative']!='play-local.bat']+[
   dict(root='server',relative=MANIFEST,source=str(W/'manifest.json'),parent_sha256=None,sha256=tx.sha(W/'manifest.json')),
   dict(root='server',relative=RECEIPT,source=str(backup/'receipt-candidate.json'),parent_sha256=None,sha256=tx.sha(backup/'receipt-candidate.json')),
   next(r for r in m['files'] if r['relative']=='play-local.bat')]
  def validate():
   gameclosed();verify_parent(m)
   assert all(tx.digest(S/'gamedata'/n)==d for n,d in protected.items())
  transaction=tx.commit_transaction({'server':S,'client':C},entries,backup,validate)
  try:
   proof=load(S/SELF,'progression20_installed').preflight(S,C)
   assert all(tx.digest(S/'gamedata'/n)==d for n,d in protected.items())
   transaction.update(status='installed',preflight=proof,protected=protected);tx.atomic_json(backup/'transaction.json',transaction)
  except BaseException:
   tx.restore_completed({'server':S,'client':C},transaction,backup);raise
  result=dict(status='FORMAL_FILES_INSTALLED',runtime_status='PENDING_RELOAD',preflight=proof,backup=str(backup),protected=protected,
   source_hashes={r['relative']:r['sha256'] for r in m['files']},meta_hashes={p:tx.sha(S/p) for p in (SELF,MANIFEST,RECEIPT)},native_status='NOT_VERIFIED')
  tx.atomic_json(W/'installed.json',result);return result
if __name__=='__main__':print(json.dumps(prepare() if sys.argv[1:] == ['prepare'] else install(),ensure_ascii=True,indent=2))
