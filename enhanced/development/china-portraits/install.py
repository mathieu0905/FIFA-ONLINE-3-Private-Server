"""Portrait-only guarded release. Never stops services or operates the game GUI."""
from contextlib import contextmanager
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
spec=importlib.util.spec_from_file_location('portrait_release_common',R.parent/'china-future/install.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
SELF='patches/china_portraits_preflight.py';MANIFEST='patches/china-portraits-installed.json';RECEIPT='patches/china-portraits-receipt.json';CERT=d.CERT;DOC=d.DOC
d.R=R;d.SELF=SELF;d.MANIFEST=MANIFEST;d.RECEIPT=RECEIPT
sha=d.sha;encoded=d.encoded
@contextmanager
def locks():
 owned=[]
 try:
  for name in ['.shop-release.lock','.fo3-publish.lock']:
   p=S/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);body=encoded(dict(pid=os.getpid(),owner='china-future-real-portraits',thread='01a1b3ef-a0a3-79f2-9005-989eb5b9669d'));owned.append((p,fd,body));os.write(fd,body);os.fsync(fd)
  yield
 finally:
  for p,fd,b in reversed(owned):
   os.close(fd)
   if p.exists() and p.read_bytes()==b:p.unlink()
def check_inputs():
 v=json.loads((R/'reviewed-payloads.json').read_text('utf8'));baseline=json.loads((R/'baseline.json').read_text('utf8'))
 for p,h in v['files'].items():
  if sha(p)!=h:raise RuntimeError('Reviewed work changed '+p)
 for p,h in baseline.items():
  current=sha(p) if Path(p).exists() else None
  if current==h:continue
  # A live client may have downloaded the same old certified placeholder into
  # its second cache after preparation. Accept only that byte-identical copy.
  if '_cache\\cdn\\' in p and current is not None:
   main=p.replace('_cache\\cdn\\','_cache\\games\\fo3id\\')
   if baseline.get(main)==current and sha(main)==current:continue
  raise RuntimeError('Formal input advanced; fresh/review '+p)
 if json.loads((R/'tests.json').read_text('utf8'))['status']!='PASS':raise RuntimeError('Portrait regression missing')
def payloads():
 files={('server','gamedata/custom_rosters.json'):(R/'custom_rosters.json').read_bytes(),('server','gamedata/china-future-portraits.json'):(R/'portrait-manifest.json').read_bytes()}
 for p in (R/'native').glob('p*.png'):
  for directory in ['_cache/games/fo3id/externalAssets/players/','_cache/cdn/externalAssets/players/']:files[('client',directory+p.name)]=p.read_bytes()
 assert len(files)==66;return files
def helper_source(parent):
 h=parent['helper'];text=(S/parent['relative']).read_text('utf8');receipt=json.loads((S/h.RECEIPT).read_text('utf8'))
 for old,new in [(h.SELF,SELF),(h.MANIFEST,MANIFEST),(h.RECEIPT,RECEIPT),(receipt['status'],'INSTALLED_CHINA_PORTRAITS'),(parent['proof']['status'],'CHINA_PORTRAITS_PREFLIGHT_PASS')]:text=text.replace(old,new)
 anchor='\n if not required<=seen:';assert text.count(anchor)==1
 text=text.replace(anchor,"\n required.update({('server','gamedata/custom_rosters.json'),('server','gamedata/china-future-portraits.json'),('server','gamedata/player-import-validation.json')})"+anchor)
 compile(text,SELF,'exec');return text.encode('utf8')
def transact(parent,files,revision):
 d.closed();backup=S/'backups'/revision;backup.mkdir(parents=True)
 guards=parent['validator'].table(parent['composition']['guards']);baseline=json.loads((R/'baseline.json').read_text('utf8'))
 for key in files:
  p=d.target(key)
  if p.exists() and (key[0],key[1].casefold()) not in guards:
   path=str(p)
   main=path.replace('_cache\\cdn\\','_cache\\games\\fo3id\\')
   if key[0]!='client' or main==path or baseline.get(main)!=sha(p) or sha(main)!=sha(p):raise RuntimeError('Unregistered later resource retained: '+path)
 before={k:d.target(k).read_bytes() if d.target(k).exists() else None for k in files}
 for rel in [CERT,SELF,MANIFEST,RECEIPT,'play-local.bat']:
  if rel in [SELF,MANIFEST,RECEIPT] and (S/rel).exists():raise RuntimeError('Immutable child already exists')
  before[('server',rel)]=(S/rel).read_bytes() if (S/rel).exists() else None
 for key,body in before.items():
  if body is not None:
   d.closed();p=backup/key[0]/key[1];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
 journal=[]
 try:
  for k,b in files.items():d.commit_file(k,before[k],b,journal)
  checker=d.load(S/'tools/player_import/check.py','formal_portraits_checker');full=checker.validate(S,C,full=True)
  assert full['status']=='PLAYER_IMPORT_FULL_PASS'
  cert=encoded(full);d.commit_file(('server',CERT),before[('server',CERT)],cert,journal);files[('server',CERT)]=cert
  helper=helper_source(parent);play=parent['play'].replace(parent['relative'].replace('/','\\').encode(),SELF.replace('/','\\').encode())
  files.update({('server',SELF):helper,('server','play-local.bat'):play})
  composition=parent['composition'];guardmap=parent['validator'].table(composition['guards'])
  for k,b in files.items():guardmap[(k[0],k[1].casefold())]=dict(root=k[0],relative=k[1],sha256=hashlib.sha256(b).hexdigest())
  composition.update(guards=list(guardmap.values()),files_verified=False);composition.setdefault('ancestry',[]).append(dict(layer='china-real-portraits',native_status='PENDING'))
  manifest=encoded(dict(schema=1,revision=revision,client=str(C),guards=composition['guards'],composition=composition,parent_preflight=parent['relative'],state_shop_replaced=False,portraits=32,services_restarted=False))
  receipt=encoded(dict(status='INSTALLED_CHINA_PORTRAITS',revision=revision,manifest_sha256=hashlib.sha256(manifest).hexdigest(),state_shop_replaced=False,native_status='PENDING'))
  for rel,b in [(SELF,helper),(MANIFEST,manifest),(RECEIPT,receipt),('play-local.bat',play)]:d.commit_file(('server',rel),before[('server',rel)],b,journal)
  proof=d.load(S/SELF,'installed_portraits_gate').preflight(S,C)
  return dict(status='PORTRAITS_INSTALLED_NATIVE_PENDING',revision=revision,preflight=proof,full_player_import=full['status'],backup=str(backup),portraits=32,services_restarted=False,top_preflight=str(S/SELF),composition_api='compose_manifest(server=None,client=None)',files={str(S/p):sha(S/p) for p in [SELF,MANIFEST,RECEIPT,'play-local.bat']})
 except BaseException:
  d.restore_files(journal);raise
LEDGER='\n\nFO3-CHINA-PORTRAITS-002（2026-11-07）：通用3D外貌与卡面头像是独立资源。先前仅导入实名剪影占位，虽然HTTP200/完整性检查通过，但不等于真人头像已配齐。此次32人逐人核对署名照片：足协队员页25人、达姆官网李昊炎、署名资料吕孟洋、按名字/俱乐部/年龄区分的5个Sofa球员档案；原图/来源URL/SHA及导入PNG均记录，拒绝默认/重复头像，不通过面相猜身份。仅标准化为有界等比纹理，不生成/改造脸、不裁切换背景。双缓存同一SPID同图并更新registry来源、完整player_import证书及新层，原照片来源另存manifest。此前测试使用剪影完整性不能冒充真人照片验收；今后新增头像类型必须实查。游戏运行或启动期间延期，文件CAS原子替换并继承完整guards/policies，不改BIG/SQL/身体参数/强化/商品/热包/真实资产，不需服务重启。界面显示和缓存刷新仍需分别验收，实机未测不得宣称通过。证据D:/fifaol3/china-portraits。\n'
def main():
 try:d.closed()
 except RuntimeError as e:print(str(e));return
 check_inputs()
 with locks():
  d.closed();check_inputs();parent=d.fresh_parent();files=payloads();files[('server',DOC)]=(S/DOC).read_bytes()+LEDGER.encode('utf8')
  hot_before=d.base.hot_status();snapshot={n:(S/'gamedata'/n).read_bytes() for n in ['state.json','shop.json']}
  revision='china-portraits-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');result=transact(parent,files,revision)
  hot=d.base.hot_status();assert hot==hot_before
  business=lambda x:{k:v for k,v in x.items() if k!='market_simulation'}
  result.update(hot_update_status=hot,state_written=False,shop_written=False,state_business_unchanged=business(json.loads(snapshot['state.json']))==business(json.loads((S/'gamedata/state.json').read_bytes())),shop_unchanged=snapshot['shop.json']==(S/'gamedata/shop.json').read_bytes(),native_gui_verified=False)
  (R/'installed-handback.json').write_bytes(encoded(result));(R.parent/'root-current-top.json').write_bytes(encoded(result));print(json.dumps(result,ensure_ascii=True))
if __name__=='__main__':main()
