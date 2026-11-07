from pathlib import Path
from contextlib import contextmanager,nullcontext
import sys,os,json,re,datetime,importlib.util,copy,shutil,subprocess
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path.insert(0,r'D:\fifaol3');import install_bulk_seasons as tx
MANIFEST='patches/protection-checkbox-installed.json';RECEIPT='patches/protection-checkbox-receipt.json';SELF='patches/protection_checkbox_preflight.py';DOC='docs/工程经验与修改边界.txt'
NAMES=('TeamManagementPlayerEnhancementTabPage','TeamManagementPlayerEnhancingPopupScreen')
TARGETS={('server',p) for p in (SELF,'play-local.bat',DOC,'enhancement_protection40.py')}|{('server','patches/'+n+'.big') for n in NAMES}|{('client','data/ui/'+n+'.big') for n in NAMES}
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
   p=server/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);token=json.dumps(dict(pid=os.getpid(),task='protection-checkbox')).encode();os.write(fd,token);os.close(fd);owned.append((p,token))
  yield
 finally:
  for p,token in reversed(owned):
   if p.exists() and p.read_bytes()==token:p.unlink()

def prepare():
 play=(S/'play-local.bat').read_bytes();names=re.findall(rb'patches\\([A-Za-z0-9_]+_preflight\.py)',play);assert len(names)==1
 parent_path='patches/'+names[0].decode();parent=load(S/parent_path,'protection_checkbox_parent');proof=parent.preflight(S,C);composed=parent.compose_manifest(S,C)
 assert b'tools\\player_import\\check.py' in play
 (W/'play-local.bat').write_bytes(play.replace(b'patches\\'+names[0],b'patches\\protection_checkbox_preflight.py'))
 template=(S/parent_path).read_text(encoding='utf-8')
 parent_status=tx.read(S/parent.RECEIPT)['status']
 for old,new in [(parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(parent_status,'INSTALLED_PROTECTION_CHECKBOX'),(proof['status'],'PROTECTION_CHECKBOX_PREFLIGHT_PASS')]:template=template.replace(old,new)
 needle=' if not required<=seen:';assert template.count(needle)==1
 template=template.replace(needle,' required.update('+repr({(r,p.casefold()) for r,p in TARGETS})+')\n'+needle)
 (W/'protection_checkbox_preflight.py').write_text(template,encoding='utf-8')
 for n in NAMES:
  assert tx.sha(C/('data/ui/'+n+'.big'))==json.loads((W/'client-build.json').read_text())[n]['source_sha256'],'Rebuild on latest client resource'
 entry='\r\n\r\nFO3-INDEPENDENT-PROTECTION-CHECKBOX-001（2026-11-07）\r\n用户要求保护与黄金强化加成不冲突，保护改独立勾选框；并指出数字框本身太丑。新增默认不勾选的保护选项，下拉保留黄金/白银等原生加成道具，重置/换卡取消保护，忙时不可切换。百分比在贴合原图标区域的深色圆角块中居中，去掉生硬矩形文字边框和旧箭头；其它布局不改。继续使用已验证的$NormalFont与嵌入字形。\r\n勾选时预览URI附protection=1，原生确认页沿用实际preview的完整保护条款/签名，执行路径保留所选黄金等itemid；服务端签名绑定经理/卡实例/等级/经验/价格/概率/配置/加成道具itemid和库存快照，单STATE_LOCK/一次_save扣40%保护费（替代2%手续费）、材料和1个加成道具；成败均耗费，失败保级经验保留，点数/活动继续叠加。旧1000090路径兼容，但不再把伪保护道具注入下拉库存。过期/缺库存/改加成/改数量/改概率/伪造签名拒绝，达到100%和安全档不收费保护、非fatal提示取消勾选，不静默改普通付费。旧恢复权益不覆盖，放弃仍双确认。\r\nControl34拒绝先前勾选/道具/点数/卡组的迟到响应，防止取消保护后旧报价覆盖。原强化执行、恢复、确认和签名URI方法字节保留；上轮字体及按钮重算保留。D:/fifaol3/protection-checkbox含真实路由临时存档回归、客户端交互/样式/字节差分、10方法栈流与事务故障验证。所有测试无真实购包/强化或测试资产写入；未操作GUI，不把回放当实机显示通过。运行中不写正式文件/启停；自然结束后fresh最新父层、双锁、备份/CAS、完整guards/policies/seed/valuation/在线cfg/player_import并守护重启加载服务模块。\r\n'
 (W/'工程经验.txt').write_bytes((S/DOC).read_bytes()+entry.encode('utf-8'))
 build=tx.read(W/'server-build.json')
 assert tx.sha(S/'enhancement_protection40.py')==build['source_sha256'],'Protection module changed; rebase required'
 assert tx.sha(W/'enhancement_protection40.py')==build['sha256']
 payloads=[('server','enhancement_protection40.py','enhancement_protection40.py')]
 for n in NAMES:payloads.extend([('client','data/ui/'+n+'.big',n+'.big'),('server','patches/'+n+'.big',n+'.big')])
 payloads.extend([('server',SELF,'protection_checkbox_preflight.py'),('server',DOC,'工程经验.txt'),('server','play-local.bat','play-local.bat')])
 files=[];guards={(r['root'],r['relative'].replace('\\','/').casefold()):copy.deepcopy(r) for r in composed['guards']}
 for root,relative,source in payloads:
  row=dict(root=root,relative=relative,source=str(W/source),parent_sha256=tx.digest((S if root=='server' else C)/relative),sha256=tx.sha(W/source));files.append(row);guards[(root,relative.casefold())]={k:row[k] for k in ('root','relative','sha256')}
 for rel,expected in tx.read(W/'font-evidence.json')['dependencies'].items():
  assert tx.sha(C/rel)==expected,'Embedded font dependency changed; rebuild evidence'
  key=('client',rel.casefold())
  if key in guards:assert guards[key]['sha256']==expected
  guards[key]=dict(root='client',relative=rel,sha256=expected)
 assert {(r['root'],r['relative']) for r in files}==TARGETS
 composition=copy.deepcopy(composed);composition.update(guards=list(guards.values()),files_verified=False);composition.setdefault('ancestry',[]).append(dict(layer='enhancement-protection-checkbox',native_status='NOT_VERIFIED'))
 revision='protection-checkbox-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 m=dict(schema=1,revision=revision,client=str(C),guards=list(guards.values()),composition=composition,state_shop_replaced=False,files=files,parent_preflight=parent_path,
 parent_files={p:tx.sha(S/p) for p in (parent_path,parent.MANIFEST,parent.RECEIPT)},native_status='NOT_VERIFIED',no_service_restart=False)
 tx.atomic_json(W/'manifest.json',m);tx.atomic_json(W/'prepared.json',dict(status='PREPARED',parent_proof=proof,manifest_sha256=tx.sha(W/'manifest.json')))
 return dict(revision=revision,guards=len(m['guards']),payloads=len(files),parent=parent_path)

def verify_parent(m):
 for p,digest in m['parent_files'].items():assert tx.sha(S/p)==digest,('Parent metadata drift',p)
 load(S/m['parent_preflight'],'protection_checkbox_current_parent').preflight(S,C)
 for row in m['files']:
  assert tx.sha(row['source'])==row['sha256']
  assert tx.digest(tx.target({'server':S,'client':C},row))==row['parent_sha256'],('Target changed',row['relative'])
 assert not (S/MANIFEST).exists() and not (S/RECEIPT).exists()

def business(st):return {k:v for k,v in st.items() if k!='market_simulation'}

def install(held=False):
 # This guard precedes even lock/back-up creation. No restart paths exist.
 if game_active():return dict(status='DEFERRED',message='更新已延后，当前游戏继续运行',formal_files_written=False,service_actions=False)
 assert all(tx.read(W/f)['status']=='PASS' for f in ('server-tests.json','client-tests.json','stacks.json','install-tests.json'))
 if not held:raise RuntimeError('Server code requires guarded cutover.py; do not install without idle restart')
 m=tx.read(W/'manifest.json');assert {(r['root'],r['relative']) for r in m['files']}==TARGETS
 if (S/RECEIPT).exists():return load(S/SELF,'protection_checkbox_existing').preflight(S,C)
 with (nullcontext() if held else locks()):
  guard_closed();verify_parent(m)
  before=tx.read(S/'gamedata/state.json');protected={n:tx.digest(S/'gamedata'/n) for n in ('shop.json','enhancement_rates.json','market-supply-config.json','npc-market-seed.json.gz')}
  backup=S/'backups'/m['revision'];backup.mkdir()
  receipt=dict(status='INSTALLED_PROTECTION_CHECKBOX',revision=m['revision'],manifest_sha256=tx.sha(W/'manifest.json'),state_shop_replaced=False,backup=str(backup));tx.atomic_json(backup/'receipt-candidate.json',receipt)
  entries=[r for r in m['files'] if r['relative']!='play-local.bat']+[
   dict(root='server',relative=MANIFEST,source=str(W/'manifest.json'),parent_sha256=None,sha256=tx.sha(W/'manifest.json')),
   dict(root='server',relative=RECEIPT,source=str(backup/'receipt-candidate.json'),parent_sha256=None,sha256=tx.sha(backup/'receipt-candidate.json')),
   next(r for r in m['files'] if r['relative']=='play-local.bat')]
  def validate():
   guard_closed();verify_parent(m)
   assert all(tx.digest(S/'gamedata'/n)==v for n,v in protected.items())
  transaction=tx.commit_transaction({'server':S,'client':C},entries,backup,validate)
  try:
   proof=load(S/SELF,'protection_checkbox_installed').preflight(S,C)
   subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'tools/player_import/check.py')],cwd=S,check=True,capture_output=True,text=True)
   assert business(tx.read(S/'gamedata/state.json'))==business(before),'Concurrent player progress: preserve latest data, never restore snapshot'
   assert all(tx.digest(S/'gamedata'/n)==v for n,v in protected.items())
  except BaseException:
   tx.restore_completed({'server':S,'client':C},transaction,backup);raise
  transaction.update(status='installed',preflight=proof,protected=protected);tx.atomic_json(backup/'transaction.json',transaction)
  result=dict(status='FORMAL_RESOURCES_INSTALLED',preflight=proof,backup=str(backup),business_unchanged=True,protected=protected,no_service_restart=False,native_status='NOT_VERIFIED',player_import_check='PASS',
   source_hashes={r['root']+'/'+r['relative']:r['sha256'] for r in m['files']},meta_hashes={p:tx.sha(S/p) for p in (SELF,MANIFEST,RECEIPT)})
  tx.atomic_json(W/'installed-handback.json',result);return result
if __name__=='__main__':print(json.dumps(prepare() if sys.argv[1:] == ['prepare'] else install(),ensure_ascii=True,indent=2))
