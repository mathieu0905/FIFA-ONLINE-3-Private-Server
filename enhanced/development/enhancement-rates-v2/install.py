from pathlib import Path
from contextlib import contextmanager, nullcontext
import sys,os,json,re,datetime,importlib.util,copy,shutil,subprocess
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path.insert(0,r'D:\fifaol3');import install_bulk_seasons as tx
DOC='docs/工程经验与修改边界.txt'
LEGIT_DOC_SHA='acc016fe07aaeef66b68d5ea14df5d5724c0ef40164d4485f9410128d49eb605'
MANIFEST='patches/ratesv2-installed.json';RECEIPT='patches/ratesv2-receipt.json';SELF='patches/ratesv2_preflight.py'
TARGETS={('server',p) for p in ('enhancement_progression.py','enhancement_protection40.py','admin/index.html',SELF,'play-local.bat',DOC)}
def load(p,n):
 spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def server_only_maintenance_allowed():
 assert all(root=='server' for root,path in TARGETS),'This user-authorized live maintenance is server-only'

@contextmanager
def locks(server=S):
 held=[]
 try:
  for name in ('.shop-release.lock','.fo3-publish.lock'):
   p=server/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);token=json.dumps(dict(pid=os.getpid(),task='ratesv2')).encode();os.write(fd,token);os.close(fd);held.append((p,token))
  yield
 finally:
  for p,token in reversed(held):
   if p.exists() and p.read_bytes()==token:p.unlink()

def parent_proof(parent):
 composed=parent.compose_manifest(S,C);roots={'server':S,'client':C};seen=set();adopted=[]
 for row in composed['guards']:
  root=roots[row['root']];path=(root/row['relative']).resolve();key=(row['root'],row['relative'].replace('\\','/').casefold())
  assert path.is_relative_to(root) and key not in seen;seen.add(key)
  if tx.sha(path)!=row['sha256']:
   assert row['root']=='server' and row['relative']==DOC,'Unrelated parent drift: '+str(key)
   base=S/'backups/progression20-20261107-000846-389515/工程经验修改前.txt'
   assert tx.sha(base)==row['sha256'] and tx.sha(path)==LEGIT_DOC_SHA
   assert path.read_bytes().startswith(base.read_bytes())
   adopted.append(dict(relative=DOC,parent_sha256=row['sha256'],legitimate_append_sha256=LEGIT_DOC_SHA,proof_backup=str(base)))
 for policy in composed.get('receipt_policies',[]):
  data=tx.read(roots[policy['root']]/policy['relative']);assert {k:v for k,v in data.items() if k!='native_status'}==policy['installation_fields']
 return dict(status='PARENT_ALL_FILES_VERIFIED_WITH_EXACT_OWN_DOCUMENT_APPEND',files=len(seen),adopted_document_append=adopted),composed

def prepare():
 play=(S/'play-local.bat').read_bytes();names=re.findall(rb'patches\\([A-Za-z0-9_]+_preflight\.py)',play);assert len(names)==1
 parent_path='patches/'+names[0].decode();parent=load(S/parent_path,'ratesv2_parent');proof,composed=parent_proof(parent)
 (W/'play-local.bat').write_bytes(play.replace(b'patches\\'+names[0],b'patches\\ratesv2_preflight.py'))
 template=(S/'patches/reward_upgrade_preflight.py').read_text(encoding='utf-8')
 template=template.replace('reward-upgrade','ratesv2').replace('reward_upgrade','ratesv2').replace('REWARD_UPGRADE','RATESV2')
 required="required={('server','gamedata/fifadb.sqlite'),('client','data/data_0.big'),('server','play-local.bat'),('server',SELF)}"
 assert required in template
 template=template.replace(required,'required='+repr({(r,p.casefold()) for r,p in TARGETS}))
 (W/'ratesv2_preflight.py').write_text(template,encoding='utf-8')
 payloads=[('server','enhancement_progression.py','enhancement_progression.py'),('server','enhancement_protection40.py','enhancement_protection40.py'),('server','admin/index.html','index.html'),('server',SELF,'ratesv2_preflight.py'),('server',DOC,'工程经验.txt'),('server','play-local.bat','play-local.bat')]
 files=[];guards={(r['root'],r['relative'].replace('\\','/').casefold()):copy.deepcopy(r) for r in composed['guards']}
 for root,relative,src in payloads:
  row=dict(root=root,relative=relative,source=str(W/src),parent_sha256=tx.digest((S if root=='server' else C)/relative),sha256=tx.sha(W/src));files.append(row);guards[(root,relative.casefold())]={k:row[k] for k in ('root','relative','sha256')}
 assert {(r['root'],r['relative']) for r in files}==TARGETS
 composition=copy.deepcopy(composed);composition['guards']=list(guards.values());composition['files_verified']=False
 composition.setdefault('ancestry',[]).append(dict(layer='ratesv2',native_status='NOT_VERIFIED'))
 revision='ratesv2-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 m=dict(schema=1,revision=revision,client=str(C),guards=list(guards.values()),composition=composition,state_shop_replaced=False,files=files,
  parent_preflight=parent_path,parent_files={p:tx.sha(S/p) for p in (parent_path,parent.MANIFEST,parent.RECEIPT)},native_status='NOT_VERIFIED',custom_rates_replaced=False)
 tx.atomic_json(W/'manifest.json',m);tx.atomic_json(W/'prepared.json',dict(status='PREPARED',parent_proof=proof,manifest_sha256=tx.sha(W/'manifest.json')))
 return dict(revision=revision,files=len(m['guards']),payloads=len(files),parent=parent_path)

def verify_parent(m):
 for path,digest in m['parent_files'].items():assert tx.sha(S/path)==digest,('Parent metadata changed',path)
 parent_proof(load(S/m['parent_preflight'],'ratesv2_current_parent'))
 for row in m['files']:
  assert tx.sha(row['source'])==row['sha256']
  assert tx.digest(tx.target({'server':S,'client':C},row))==row['parent_sha256'],('Source target changed',row['relative'])
 assert not (S/MANIFEST).exists() and not (S/RECEIPT).exists()

def install(locked=False):
 m=tx.read(W/'manifest.json')
 if (S/RECEIPT).exists():return load(S/SELF,'ratesv2_existing').preflight(S,C)
 assert {(r['root'],r['relative']) for r in m['files']}==TARGETS
 server_only_maintenance_allowed()
 with (nullcontext() if locked else locks()):
  server_only_maintenance_allowed();verify_parent(m);backup=S/'backups'/m['revision'];backup.mkdir()
  protected={n:tx.digest(S/'gamedata'/n) for n in ('state.json','shop.json','enhancement_rates.json','pack_cadence.json','pack_catalogue.json','product_packs.json')}
  for n,d in protected.items():
   if d is not None:shutil.copyfile(S/'gamedata'/n,backup/('audit-'+n))
  receipt=dict(status='INSTALLED_RATESV2',revision=m['revision'],manifest_sha256=tx.sha(W/'manifest.json'),state_shop_replaced=False,backup=str(backup))
  tx.atomic_json(backup/'receipt-candidate.json',receipt)
  entries=[r for r in m['files'] if r['relative']!='play-local.bat']+[
   dict(root='server',relative=MANIFEST,source=str(W/'manifest.json'),parent_sha256=None,sha256=tx.sha(W/'manifest.json')),
   dict(root='server',relative=RECEIPT,source=str(backup/'receipt-candidate.json'),parent_sha256=None,sha256=tx.sha(backup/'receipt-candidate.json')),
   next(r for r in m['files'] if r['relative']=='play-local.bat')]
  def validate():
   server_only_maintenance_allowed();verify_parent(m)
   assert all(tx.digest(S/'gamedata'/n)==d for n,d in protected.items())
  transaction=tx.commit_transaction({'server':S,'client':C},entries,backup,validate)
  try:
   proof=load(S/SELF,'ratesv2_installed').preflight(S,C)
   assert all(tx.digest(S/'gamedata'/n)==d for n,d in protected.items())
   transaction.update(status='installed',preflight=proof,protected=protected);tx.atomic_json(backup/'transaction.json',transaction)
  except BaseException:
   tx.restore_completed({'server':S,'client':C},transaction,backup);raise
  result=dict(status='FORMAL_FILES_INSTALLED',runtime_status='PENDING_RELOAD',preflight=proof,backup=str(backup),protected=protected,
   source_hashes={r['relative']:r['sha256'] for r in m['files']},meta_hashes={p:tx.sha(S/p) for p in (SELF,MANIFEST,RECEIPT)},native_status='NOT_VERIFIED')
  tx.atomic_json(W/'installed.json',result);return result
if __name__=='__main__':print(json.dumps(prepare() if sys.argv[1:] == ['prepare'] else install(),ensure_ascii=True,indent=2))
