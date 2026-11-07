from pathlib import Path
from contextlib import contextmanager
import sys,os,json,re,datetime,importlib.util,copy,shutil,subprocess
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path.insert(0,r'D:\fifaol3');import install_bulk_seasons as tx
MANIFEST='patches/probability-ui-installed.json';RECEIPT='patches/probability-ui-receipt.json';SELF='patches/probability_ui_preflight.py';DOC='docs/工程经验与修改边界.txt'
NAMES=('TeamManagementPlayerEnhancementTabPage','TeamManagementPlayerEnhancingPopupScreen')
TARGETS={('server',p) for p in (SELF,'play-local.bat',DOC)}|{('server','patches/'+n+'.big') for n in NAMES}|{('client','data/ui/'+n+'.big') for n in NAMES}
def load(p,n):
 spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def game_active():
 return 'fifazf.exe' in subprocess.check_output(['tasklist','/FI','IMAGENAME eq fifazf.exe','/FO','CSV','/NH'],text=True,errors='replace').lower()

def guard_closed():
 if game_active():raise RuntimeError('更新已延后，当前游戏继续运行')

@contextmanager
def locks(server=S):
 owned=[]
 try:
  for name in ('.shop-release.lock','.fo3-publish.lock'):
   p=server/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);token=json.dumps(dict(pid=os.getpid(),task='probability-ui')).encode();os.write(fd,token);os.close(fd);owned.append((p,token))
  yield
 finally:
  for p,token in reversed(owned):
   if p.exists() and p.read_bytes()==token:p.unlink()

def prepare():
 play=(S/'play-local.bat').read_bytes();names=re.findall(rb'patches\\([A-Za-z0-9_]+_preflight\.py)',play);assert len(names)==1
 parent_path='patches/'+names[0].decode();parent=load(S/parent_path,'probability_ui_parent');proof=parent.preflight(S,C);composed=parent.compose_manifest(S,C)
 assert b'tools\\player_import\\check.py' in play
 (W/'play-local.bat').write_bytes(play.replace(b'patches\\'+names[0],b'patches\\probability_ui_preflight.py'))
 template=(S/'patches/protection_preview_fix_preflight.py').read_text(encoding='utf-8')
 template=template.replace('protection-preview-fix','probability-ui').replace('protection_preview_fix','probability_ui').replace('INSTALLED_PREVIEW_FIX','INSTALLED_PROBABILITY_UI').replace('PROTECTION_PREVIEW_FIX_PREFLIGHT_PASS','PROBABILITY_UI_PREFLIGHT_PASS')
 needle=' if not required<=seen:';assert template.count(needle)==1
 template=template.replace(needle,' required.update('+repr({(r,p.casefold()) for r,p in TARGETS})+')\n'+needle)
 (W/'probability_ui_preflight.py').write_text(template,encoding='utf-8')
 for n in NAMES:
  assert tx.sha(C/('data/ui/'+n+'.big'))==json.loads((W/'build.json').read_text())[n]['source_sha256'],'Rebuild on latest client resource'
 entry='''\r\n\r\nFO3-ENHANCE-PROBABILITY-UI-001（2026-11-07）\r\n用户要求强化页面全部显示成功率。两强化BIG仅四个Control方法与popup onQuery追加数字TextField，读取实际preview.probability，不从等级表重算；0/100/16.5/3.3等数字保留，小数不转uint，缺失/NaN/越界显示破折号，新请求显示计算中，换卡/清空清旧值。确认弹窗使用同一info.probability，blocked保护显示实际概率和不可用后缀，不改label/blocked守卫、支付/签名/恢复/执行。只读字节证明所有其它方法records/trait/旧签名/非ABC标签/其它BIG成员压缩字节保持，原空格/保级/费用显示保留。\r\n构建和临时回放见D:/fifaol3/enhancement-probability-ui/build.json、tests.json、stacks.json；原生字体/布局/GFx类型与实际游玩未验证，不把字节码回放写成native通过。Control y92..116处于ES行与cost y120之间，popup使用原caution label父坐标上移40，静态边界验证不等于实际画面。\r\n游戏运行期间只分析构建，没有正式写/服务启停/GUI，也没有要求退出。protection-preview-fix owner先完成非fatal读取修复并交还后，按实际最新父层、seed/在线cfg验证、全部guards/receipt policies、player_import独立入口、共同锁与目标CAS提交本纯资源层；如果游戏重开则零写延期，不停服/断线。安装状态与确切基线/hash/备份/资产保护见本目录installed-handback.json；不改任何概率、保护费、真实存档或旧商品。\r\n'''
 (W/'工程经验.txt').write_bytes((S/DOC).read_bytes()+entry.encode('utf-8'))
 payloads=[]
 for n in NAMES:payloads.extend([('client','data/ui/'+n+'.big',n+'.big'),('server','patches/'+n+'.big',n+'.big')])
 payloads.extend([('server',SELF,'probability_ui_preflight.py'),('server',DOC,'工程经验.txt'),('server','play-local.bat','play-local.bat')])
 files=[];guards={(r['root'],r['relative'].replace('\\','/').casefold()):copy.deepcopy(r) for r in composed['guards']}
 for root,relative,source in payloads:
  row=dict(root=root,relative=relative,source=str(W/source),parent_sha256=tx.digest((S if root=='server' else C)/relative),sha256=tx.sha(W/source));files.append(row);guards[(root,relative.casefold())]={k:row[k] for k in ('root','relative','sha256')}
 assert {(r['root'],r['relative']) for r in files}==TARGETS
 composition=copy.deepcopy(composed);composition.update(guards=list(guards.values()),files_verified=False);composition.setdefault('ancestry',[]).append(dict(layer='enhancement-probability-ui',native_status='NOT_VERIFIED'))
 revision='probability-ui-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 m=dict(schema=1,revision=revision,client=str(C),guards=list(guards.values()),composition=composition,state_shop_replaced=False,files=files,parent_preflight=parent_path,
 parent_files={p:tx.sha(S/p) for p in (parent_path,parent.MANIFEST,parent.RECEIPT)},native_status='NOT_VERIFIED',no_service_restart=True)
 tx.atomic_json(W/'manifest.json',m);tx.atomic_json(W/'prepared.json',dict(status='PREPARED',parent_proof=proof,manifest_sha256=tx.sha(W/'manifest.json')))
 return dict(revision=revision,guards=len(m['guards']),payloads=len(files),parent=parent_path)

def verify_parent(m):
 for p,digest in m['parent_files'].items():assert tx.sha(S/p)==digest,('Parent metadata drift',p)
 load(S/m['parent_preflight'],'probability_ui_current_parent').preflight(S,C)
 for row in m['files']:
  assert tx.sha(row['source'])==row['sha256']
  assert tx.digest(tx.target({'server':S,'client':C},row))==row['parent_sha256'],('Target changed',row['relative'])
 assert not (S/MANIFEST).exists() and not (S/RECEIPT).exists()

def business(st):return {k:v for k,v in st.items() if k!='market_simulation'}

def install():
 # This guard precedes even lock/back-up creation. No restart paths exist.
 if game_active():return dict(status='DEFERRED',message='更新已延后，当前游戏继续运行',formal_files_written=False,service_actions=False)
 m=tx.read(W/'manifest.json');assert {(r['root'],r['relative']) for r in m['files']}==TARGETS
 if (S/RECEIPT).exists():return load(S/SELF,'probability_ui_existing').preflight(S,C)
 with locks():
  guard_closed();verify_parent(m)
  before=tx.read(S/'gamedata/state.json');protected={n:tx.digest(S/'gamedata'/n) for n in ('shop.json','enhancement_rates.json','market-supply-config.json','npc-market-seed.json.gz')}
  backup=S/'backups'/m['revision'];backup.mkdir()
  receipt=dict(status='INSTALLED_PROBABILITY_UI',revision=m['revision'],manifest_sha256=tx.sha(W/'manifest.json'),state_shop_replaced=False,backup=str(backup));tx.atomic_json(backup/'receipt-candidate.json',receipt)
  entries=[r for r in m['files'] if r['relative']!='play-local.bat']+[
   dict(root='server',relative=MANIFEST,source=str(W/'manifest.json'),parent_sha256=None,sha256=tx.sha(W/'manifest.json')),
   dict(root='server',relative=RECEIPT,source=str(backup/'receipt-candidate.json'),parent_sha256=None,sha256=tx.sha(backup/'receipt-candidate.json')),
   next(r for r in m['files'] if r['relative']=='play-local.bat')]
  def validate():
   guard_closed();verify_parent(m)
   assert all(tx.digest(S/'gamedata'/n)==v for n,v in protected.items())
  transaction=tx.commit_transaction({'server':S,'client':C},entries,backup,validate)
  try:
   proof=load(S/SELF,'probability_ui_installed').preflight(S,C)
   subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'tools/player_import/check.py')],cwd=S,check=True,capture_output=True,text=True)
   assert business(tx.read(S/'gamedata/state.json'))==business(before),'Concurrent player progress: preserve latest data, never restore snapshot'
   assert all(tx.digest(S/'gamedata'/n)==v for n,v in protected.items())
  except BaseException:
   tx.restore_completed({'server':S,'client':C},transaction,backup);raise
  transaction.update(status='installed',preflight=proof,protected=protected);tx.atomic_json(backup/'transaction.json',transaction)
  result=dict(status='FORMAL_RESOURCES_INSTALLED',preflight=proof,backup=str(backup),business_unchanged=True,protected=protected,no_service_restart=True,native_status='NOT_VERIFIED',player_import_check='PASS',
   source_hashes={r['root']+'/'+r['relative']:r['sha256'] for r in m['files']},meta_hashes={p:tx.sha(S/p) for p in (SELF,MANIFEST,RECEIPT)})
  tx.atomic_json(W/'installed-handback.json',result);return result
if __name__=='__main__':print(json.dumps(prepare() if sys.argv[1:] == ['prepare'] else install(),ensure_ascii=True,indent=2))
