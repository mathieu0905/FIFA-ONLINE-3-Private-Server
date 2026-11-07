from pathlib import Path
from contextlib import contextmanager
import sys,os,json,re,datetime,importlib.util,copy,shutil,subprocess
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path.insert(0,r'D:\fifaol3');import install_bulk_seasons as tx
MANIFEST='patches/enhancement-font-fix-installed.json';RECEIPT='patches/enhancement-font-fix-receipt.json';SELF='patches/enhancement_font_fix_preflight.py';DOC='docs/工程经验与修改边界.txt'
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
   p=server/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);token=json.dumps(dict(pid=os.getpid(),task='enhancement-font-fix')).encode();os.write(fd,token);os.close(fd);owned.append((p,token))
  yield
 finally:
  for p,token in reversed(owned):
   if p.exists() and p.read_bytes()==token:p.unlink()

def prepare():
 play=(S/'play-local.bat').read_bytes();names=re.findall(rb'patches\\([A-Za-z0-9_]+_preflight\.py)',play);assert len(names)==1
 parent_path='patches/'+names[0].decode();parent=load(S/parent_path,'enhancement_font_fix_parent');proof=parent.preflight(S,C);composed=parent.compose_manifest(S,C)
 assert b'tools\\player_import\\check.py' in play
 (W/'play-local.bat').write_bytes(play.replace(b'patches\\'+names[0],b'patches\\enhancement_font_fix_preflight.py'))
 template=(S/parent_path).read_text(encoding='utf-8')
 parent_status=tx.read(S/parent.RECEIPT)['status']
 for old,new in [(parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(parent_status,'INSTALLED_ENHANCEMENT_FONT_FIX'),(proof['status'],'ENHANCEMENT_FONT_FIX_PREFLIGHT_PASS')]:template=template.replace(old,new)
 needle=' if not required<=seen:';assert template.count(needle)==1
 template=template.replace(needle,' required.update('+repr({(r,p.casefold()) for r,p in TARGETS})+')\n'+needle)
 (W/'enhancement_font_fix_preflight.py').write_text(template,encoding='utf-8')
 for n in NAMES:
  assert tx.sha(C/('data/ui/'+n+'.big'))==json.loads((W/'build.json').read_text())[n]['source_sha256'],'Rebuild on latest client resource'
 entry='\r\n\r\nFO3-ENHANCE-EMBEDDED-FONT-BUTTON-001（2026-11-07）\r\n用户实机截图证实此前自建TextField使用Microsoft YaHei/Arial出现方块/缺字。正式fontconfig.dat的chi段将$NormalFont映射FZLanTingHei-R-GB18030；已直接解析正式fonts_cn.gfx的DefineFont3字表，含28454字形，确认数字、小数点、百分号和强化保护费用中文有字形。仅将两强化ABC的这两个新增字体常量替换成$NormalFont，六处embedFonts false改true，保留索引、全部其它指令、原生标题和数字框位置；字体配置及字库只读并加入完整guard，不改字体资源本身。\r\n用户报告马特乌斯+5/+3按钮灰色：正式只读预览result=true、100%、手续费1324217915，实时EP10494743721853足够，两个实例无锁，未发真实强化测试。静态发现原生余额通知只更新文字而不重算按钮；Control22补重算、Control26末尾按当前两实例对象严格匹配的最新预览同步费用/按钮。保留_available忙锁、余额限制、正数有限费用、过期对象不启用；blocked报价仅允许已有只读说明，原首条guard继续零PUT。不静默切普通付费、不改成功率/保护费/服务端执行/真实资产。按钮漂移修正通过模型回归，不能冒称已重现实机全部触发时序。\r\nD:/fifaol3/enhancement-font-fix保存字体证据、完整指令差分、数值/保护/按钮状态回放和七方法栈流检查。游戏运行只构建/临时回归，任何正式写入前检测并延期；自然退出后fresh正式父层、共同锁、完整guards/receipt policies、seed/valuation/在线配置校验、player_import及目标CAS增量安装，无服务重启/GUI。字体及按钮最终画面待原生验收，不把回放等同实机通过。\r\n'
 (W/'工程经验.txt').write_bytes((S/DOC).read_bytes()+entry.encode('utf-8'))
 payloads=[]
 for n in NAMES:payloads.extend([('client','data/ui/'+n+'.big',n+'.big'),('server','patches/'+n+'.big',n+'.big')])
 payloads.extend([('server',SELF,'enhancement_font_fix_preflight.py'),('server',DOC,'工程经验.txt'),('server','play-local.bat','play-local.bat')])
 files=[];guards={(r['root'],r['relative'].replace('\\','/').casefold()):copy.deepcopy(r) for r in composed['guards']}
 for root,relative,source in payloads:
  row=dict(root=root,relative=relative,source=str(W/source),parent_sha256=tx.digest((S if root=='server' else C)/relative),sha256=tx.sha(W/source));files.append(row);guards[(root,relative.casefold())]={k:row[k] for k in ('root','relative','sha256')}
 for rel,expected in tx.read(W/'font-evidence.json')['dependencies'].items():
  assert tx.sha(C/rel)==expected,'Embedded font dependency changed; rebuild evidence'
  key=('client',rel.casefold())
  if key in guards:assert guards[key]['sha256']==expected
  guards[key]=dict(root='client',relative=rel,sha256=expected)
 assert {(r['root'],r['relative']) for r in files}==TARGETS
 composition=copy.deepcopy(composed);composition.update(guards=list(guards.values()),files_verified=False);composition.setdefault('ancestry',[]).append(dict(layer='enhancement-enhancement-font-fix',native_status='NOT_VERIFIED'))
 revision='enhancement-font-fix-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 m=dict(schema=1,revision=revision,client=str(C),guards=list(guards.values()),composition=composition,state_shop_replaced=False,files=files,parent_preflight=parent_path,
 parent_files={p:tx.sha(S/p) for p in (parent_path,parent.MANIFEST,parent.RECEIPT)},native_status='NOT_VERIFIED',no_service_restart=True)
 tx.atomic_json(W/'manifest.json',m);tx.atomic_json(W/'prepared.json',dict(status='PREPARED',parent_proof=proof,manifest_sha256=tx.sha(W/'manifest.json')))
 return dict(revision=revision,guards=len(m['guards']),payloads=len(files),parent=parent_path)

def verify_parent(m):
 for p,digest in m['parent_files'].items():assert tx.sha(S/p)==digest,('Parent metadata drift',p)
 load(S/m['parent_preflight'],'enhancement_font_fix_current_parent').preflight(S,C)
 for row in m['files']:
  assert tx.sha(row['source'])==row['sha256']
  assert tx.digest(tx.target({'server':S,'client':C},row))==row['parent_sha256'],('Target changed',row['relative'])
 assert not (S/MANIFEST).exists() and not (S/RECEIPT).exists()

def business(st):return {k:v for k,v in st.items() if k!='market_simulation'}

def install():
 # This guard precedes even lock/back-up creation. No restart paths exist.
 if game_active():return dict(status='DEFERRED',message='更新已延后，当前游戏继续运行',formal_files_written=False,service_actions=False)
 assert all(tx.read(W/f)['status']=='PASS' for f in ('tests.json','button-tests.json','stacks.json','install-tests.json'))
 m=tx.read(W/'manifest.json');assert {(r['root'],r['relative']) for r in m['files']}==TARGETS
 if (S/RECEIPT).exists():return load(S/SELF,'enhancement_font_fix_existing').preflight(S,C)
 with locks():
  guard_closed();verify_parent(m)
  before=tx.read(S/'gamedata/state.json');protected={n:tx.digest(S/'gamedata'/n) for n in ('shop.json','enhancement_rates.json','market-supply-config.json','npc-market-seed.json.gz')}
  backup=S/'backups'/m['revision'];backup.mkdir()
  receipt=dict(status='INSTALLED_ENHANCEMENT_FONT_FIX',revision=m['revision'],manifest_sha256=tx.sha(W/'manifest.json'),state_shop_replaced=False,backup=str(backup));tx.atomic_json(backup/'receipt-candidate.json',receipt)
  entries=[r for r in m['files'] if r['relative']!='play-local.bat']+[
   dict(root='server',relative=MANIFEST,source=str(W/'manifest.json'),parent_sha256=None,sha256=tx.sha(W/'manifest.json')),
   dict(root='server',relative=RECEIPT,source=str(backup/'receipt-candidate.json'),parent_sha256=None,sha256=tx.sha(backup/'receipt-candidate.json')),
   next(r for r in m['files'] if r['relative']=='play-local.bat')]
  def validate():
   guard_closed();verify_parent(m)
   assert all(tx.digest(S/'gamedata'/n)==v for n,v in protected.items())
  transaction=tx.commit_transaction({'server':S,'client':C},entries,backup,validate)
  try:
   proof=load(S/SELF,'enhancement_font_fix_installed').preflight(S,C)
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
