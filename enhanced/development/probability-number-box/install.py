from pathlib import Path
from contextlib import contextmanager
import sys,os,json,re,datetime,importlib.util,copy,shutil,subprocess
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path.insert(0,r'D:\fifaol3');import install_bulk_seasons as tx
MANIFEST='patches/probability-number-box-installed.json';RECEIPT='patches/probability-number-box-receipt.json';SELF='patches/probability_number_box_preflight.py';DOC='docs/工程经验与修改边界.txt'
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
   p=server/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);token=json.dumps(dict(pid=os.getpid(),task='probability-number-box')).encode();os.write(fd,token);os.close(fd);owned.append((p,token))
  yield
 finally:
  for p,token in reversed(owned):
   if p.exists() and p.read_bytes()==token:p.unlink()

def prepare():
 play=(S/'play-local.bat').read_bytes();names=re.findall(rb'patches\\([A-Za-z0-9_]+_preflight\.py)',play);assert len(names)==1
 parent_path='patches/'+names[0].decode();parent=load(S/parent_path,'probability_number_box_parent');proof=parent.preflight(S,C);composed=parent.compose_manifest(S,C)
 assert b'tools\\player_import\\check.py' in play
 (W/'play-local.bat').write_bytes(play.replace(b'patches\\'+names[0],b'patches\\probability_number_box_preflight.py'))
 template=(S/parent_path).read_text(encoding='utf-8')
 parent_status=tx.read(S/parent.RECEIPT)['status']
 for old,new in [(parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(parent_status,'INSTALLED_PROBABILITY_NUMBER_BOX'),(proof['status'],'PROBABILITY_NUMBER_BOX_PREFLIGHT_PASS')]:template=template.replace(old,new)
 needle=' if not required<=seen:';assert template.count(needle)==1
 template=template.replace(needle,' required.update('+repr({(r,p.casefold()) for r,p in TARGETS})+')\n'+needle)
 (W/'probability_number_box_preflight.py').write_text(template,encoding='utf-8')
 for n in NAMES:
  assert tx.sha(C/('data/ui/'+n+'.big'))==json.loads((W/'build.json').read_text())[n]['source_sha256'],'Rebuild on latest client resource'
 entry='\r\n\r\nFO3-ENHANCE-PROBABILITY-NUMBER-BOX-001（2026-11-07）\r\n用户反馈新增成功率中文乱码且位置不明显，要求放在“成功率加成”区域的框中，并把该标题直接改成“成功率”。仅替换上一概率显示层五个显示/清空方法中的注入，强化页字段改挂Control._owner.infoPanel.enhanceRate，复用原生中文标题__id7_和原有字形改文案为“成功率”；数字框位于标题下x0/y36/180x40，深底边框、Arial24居中，只显示ASCII数字与百分号，缺失“-”、取数中“...”。保留服务端preview.probability小数和0/100，根据用户截图，确认页定位boostInfoPanel.boostInfoContainer.boostRate，复用原生__id15_标题改为“成功率”，隐藏旧箭头rateContainer，在其原位置添加带边框数字框（宽度跟随原容器、40号Arial、仅百分比），不再在底部提示附近加成功率文字；移除上一新增TextField中的中文输出。其它方法、扣费/签名/blocked保卫/恢复、其它SWF标签和BIG资源成员保持。\r\n工作证据D:/fifaol3/probability-number-box。已做原生静态显示列表路径核对、确定性回放和五方法完整栈流检查，不能代替游戏画面或GFx类型验收。未改变概率/手续费/保护费或真实资产。不启动第二套服务、不启停服务、不操作游戏GUI。游戏运行中准备构建，安装器在任何正式写入前检查并延期；自然结束后fresh顶层、完整guards/receipt policies、seed/valuation/在线配置校验、独立player_import及共同双锁/CAS增量安装。\r\n'
 (W/'工程经验.txt').write_bytes((S/DOC).read_bytes()+entry.encode('utf-8'))
 payloads=[]
 for n in NAMES:payloads.extend([('client','data/ui/'+n+'.big',n+'.big'),('server','patches/'+n+'.big',n+'.big')])
 payloads.extend([('server',SELF,'probability_number_box_preflight.py'),('server',DOC,'工程经验.txt'),('server','play-local.bat','play-local.bat')])
 files=[];guards={(r['root'],r['relative'].replace('\\','/').casefold()):copy.deepcopy(r) for r in composed['guards']}
 for root,relative,source in payloads:
  row=dict(root=root,relative=relative,source=str(W/source),parent_sha256=tx.digest((S if root=='server' else C)/relative),sha256=tx.sha(W/source));files.append(row);guards[(root,relative.casefold())]={k:row[k] for k in ('root','relative','sha256')}
 assert {(r['root'],r['relative']) for r in files}==TARGETS
 composition=copy.deepcopy(composed);composition.update(guards=list(guards.values()),files_verified=False);composition.setdefault('ancestry',[]).append(dict(layer='enhancement-probability-number-box',native_status='NOT_VERIFIED'))
 revision='probability-number-box-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 m=dict(schema=1,revision=revision,client=str(C),guards=list(guards.values()),composition=composition,state_shop_replaced=False,files=files,parent_preflight=parent_path,
 parent_files={p:tx.sha(S/p) for p in (parent_path,parent.MANIFEST,parent.RECEIPT)},native_status='NOT_VERIFIED',no_service_restart=True)
 tx.atomic_json(W/'manifest.json',m);tx.atomic_json(W/'prepared.json',dict(status='PREPARED',parent_proof=proof,manifest_sha256=tx.sha(W/'manifest.json')))
 return dict(revision=revision,guards=len(m['guards']),payloads=len(files),parent=parent_path)

def verify_parent(m):
 for p,digest in m['parent_files'].items():assert tx.sha(S/p)==digest,('Parent metadata drift',p)
 load(S/m['parent_preflight'],'probability_number_box_current_parent').preflight(S,C)
 for row in m['files']:
  assert tx.sha(row['source'])==row['sha256']
  assert tx.digest(tx.target({'server':S,'client':C},row))==row['parent_sha256'],('Target changed',row['relative'])
 assert not (S/MANIFEST).exists() and not (S/RECEIPT).exists()

def business(st):return {k:v for k,v in st.items() if k!='market_simulation'}

def install():
 # This guard precedes even lock/back-up creation. No restart paths exist.
 if game_active():return dict(status='DEFERRED',message='更新已延后，当前游戏继续运行',formal_files_written=False,service_actions=False)
 m=tx.read(W/'manifest.json');assert {(r['root'],r['relative']) for r in m['files']}==TARGETS
 if (S/RECEIPT).exists():return load(S/SELF,'probability_number_box_existing').preflight(S,C)
 with locks():
  guard_closed();verify_parent(m)
  before=tx.read(S/'gamedata/state.json');protected={n:tx.digest(S/'gamedata'/n) for n in ('shop.json','enhancement_rates.json','market-supply-config.json','npc-market-seed.json.gz')}
  backup=S/'backups'/m['revision'];backup.mkdir()
  receipt=dict(status='INSTALLED_PROBABILITY_NUMBER_BOX',revision=m['revision'],manifest_sha256=tx.sha(W/'manifest.json'),state_shop_replaced=False,backup=str(backup));tx.atomic_json(backup/'receipt-candidate.json',receipt)
  entries=[r for r in m['files'] if r['relative']!='play-local.bat']+[
   dict(root='server',relative=MANIFEST,source=str(W/'manifest.json'),parent_sha256=None,sha256=tx.sha(W/'manifest.json')),
   dict(root='server',relative=RECEIPT,source=str(backup/'receipt-candidate.json'),parent_sha256=None,sha256=tx.sha(backup/'receipt-candidate.json')),
   next(r for r in m['files'] if r['relative']=='play-local.bat')]
  def validate():
   guard_closed();verify_parent(m)
   assert all(tx.digest(S/'gamedata'/n)==v for n,v in protected.items())
  transaction=tx.commit_transaction({'server':S,'client':C},entries,backup,validate)
  try:
   proof=load(S/SELF,'probability_number_box_installed').preflight(S,C)
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
