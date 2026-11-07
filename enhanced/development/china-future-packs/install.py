"""Additive high-grade sale configuration; protected cold registration, then ABI2 publish."""
from pathlib import Path
from contextlib import contextmanager
import datetime,hashlib,importlib.util,json,os,subprocess,sys,time
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
spec=importlib.util.spec_from_file_location('card_import_release_common',R.parent/'china-future/install.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
SELF='patches/high8_packs_preflight.py';MANIFEST='patches/high8-packs-installed.json';RECEIPT='patches/high8-packs-receipt.json';DOC=d.DOC
d.R=R;d.SELF=SELF;d.MANIFEST=MANIFEST;d.RECEIPT=RECEIPT;d.base.R=R
sha=d.sha;encoded=d.encoded

@contextmanager
def locks():
 owned=[]
 try:
  for name in ['.shop-release.lock','.fo3-publish.lock']:
   path=S/name;fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);body=encoded(dict(pid=os.getpid(),owner='high8-packs-and-china-future-shop',thread='01a1b3ef-a0a3-79f2-9005-989eb5b9669d'))
   owned.append((path,fd,body));os.write(fd,body);os.fsync(fd)
  yield
 finally:
  for p,fd,b in reversed(owned):
   os.close(fd)
   if p.exists() and p.read_bytes()==b:p.unlink()

def payloads():
 files={('server','gamedata/club_season_products.json'):(R/'club_season_products.json').read_bytes(),('server','gamedata/all_item_icon_manifest.json'):(R/'all_item_icon_manifest.json').read_bytes()}
 for p in (R/'icons').glob('*.png'):
  for directory in ['_cache/games/fo3id/externalAssets/shop/','_cache/cdn/externalAssets/shop/']:files[('client',directory+p.name)]=p.read_bytes()
 return files

def check_inputs():
 v=json.loads((R/'reviewed-payloads.json').read_text('utf8'))
 for p,h in v['files'].items():
  if sha(p)!=h:raise RuntimeError('Reviewed output changed: '+p)
 for p,h in v['baseline'].items():
  if sha(p)!=h:raise RuntimeError('Formal baseline advanced; fresh/retest '+p)
 for name in ['tests.json','chain-tests.json']:
  if json.loads((R/name).read_text('utf8'))['status']!='PASS':raise RuntimeError('Regression missing '+name)

def helper_source(parent):
 h=parent['helper'];source=(S/parent['relative']).read_text('utf8');receipt=json.loads((S/h.RECEIPT).read_text('utf8'))
 for old,new in [(h.SELF,SELF),(h.MANIFEST,MANIFEST),(h.RECEIPT,RECEIPT),(receipt['status'],'INSTALLED_HIGH8_PACKS'),(parent['proof']['status'],'HIGH8_PACKS_PREFLIGHT_PASS')]:source=source.replace(old,new)
 anchor='\n if not required<=seen:';assert source.count(anchor)==1
 source=source.replace(anchor,"\n required.update({('server','gamedata/club_season_products.json'),('server','gamedata/all_item_icon_manifest.json')})"+anchor)
 compile(source,SELF,'exec');return source.encode()

def transact(parent,files,revision):
 d.closed();backup=S/'backups'/revision;backup.mkdir(parents=True)
 guards=parent['validator'].table(parent['composition']['guards'])
 for key in files:
  if d.target(key).exists() and (key[0],key[1].casefold()) not in guards:raise RuntimeError('Existing unregistered file retained: '+str(key))
 before={key:d.target(key).read_bytes() if d.target(key).exists() else None for key in files}
 for rel in [SELF,MANIFEST,RECEIPT,'play-local.bat']:
  if rel!='play-local.bat' and (S/rel).exists():raise RuntimeError('Immutable child metadata already exists')
  before[('server',rel)]=(S/rel).read_bytes() if (S/rel).exists() else None
 for key,body in before.items():
  if body is not None:
   d.closed();p=backup/key[0]/key[1];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
 journal=[]
 try:
  for key,body in files.items():d.commit_file(key,before[key],body,journal)
  helper=helper_source(parent);play=parent['play'].replace(parent['relative'].replace('/','\\').encode(),SELF.replace('/','\\').encode())
  files.update({('server',SELF):helper,('server','play-local.bat'):play})
  composition=parent['composition'];guards=parent['validator'].table(composition['guards'])
  for key,body in files.items():guards[(key[0],key[1].casefold())]=dict(root=key[0],relative=key[1],sha256=hashlib.sha256(body).hexdigest())
  composition.update(guards=list(guards.values()),files_verified=False);composition.setdefault('ancestry',[]).append(dict(layer='high8-packs',native_status='PENDING'))
  manifest=encoded(dict(schema=1,revision=revision,client=str(C),guards=composition['guards'],composition=composition,parent_preflight=parent['relative'],state_shop_replaced=False,new_china_pack_ids=[98432701,98432702]))
  receipt=encoded(dict(status='INSTALLED_HIGH8_PACKS',revision=revision,manifest_sha256=hashlib.sha256(manifest).hexdigest(),state_shop_replaced=False,native_status='PENDING'))
  for rel,body in [(SELF,helper),(MANIFEST,manifest),(RECEIPT,receipt),('play-local.bat',play)]:d.commit_file(('server',rel),before[('server',rel)],body,journal)
  proof=d.load(S/SELF,'installed_high8_guard').preflight(S,C)
  return dict(status='INSTALLED_CONFIGS',revision=revision,backup=str(backup),preflight=proof,top_preflight=str(S/SELF),composition_api='compose_manifest(server=None,client=None)',state_shop_written=False)
 except BaseException:
  d.restore_files(journal);raise

LEDGER='\n\nFO3-HIGH8-PACKS-001（2026-11-07）：用户明确除传奇时刻外在售卡包最低+8。中国明日之星新增随机+8..12（50/25/15/8/2）与固定+8自选；32人冻结池，普通点券价格按现有估值、随机按期望/自选按最大可选值重新计算。低强化在售包和连锁后续低强化奖励采用新SKU，球员逐卡概率不变；已有高强包、传奇时刻+1、已持有旧编号和已完成连锁档位保持原定义/数量/价格，旧回执不改。新业务仅扩展中国明日之星自选商品例外并更新未来连锁包与报价；保留原ABI2七路由、批量随机开包/幂等及旧连锁资产。冷注册配置需要游戏关闭后受保护停服；业务用正式发布工具原子切换，不盲目reload。全量图标清单与两缓存绑定，沿用最新父层全部guards/policies/原生导入检查。临时购买/开包/重放/篡改/满员/并发/保存失败/旧链已完成显示回归，不向真实存档写测试卡/余额。实机显示未验收。证据D:/fifaol3/china-future-packs。\n'

def main():
 try:d.closed()
 except RuntimeError as e:print(str(e));return
 check_inputs()
 with locks():
  d.closed();check_inputs();parent=d.fresh_parent();files=payloads();files[('server',DOC)]=(S/DOC).read_bytes()+LEDGER.encode()
  old_hot=d.base.hot_status()
  try:d.base.stop()
  except RuntimeError:
   if d.game_running():print('更新已延后，当前游戏继续运行');return
   raise
  snapshot={n:(S/'gamedata'/n).read_bytes() for n in ['state.json','shop.json']}
  for n,b in snapshot.items():(R/('stopped-'+n)).write_bytes(b)
  revision='high8-packs-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');result=None;error=None
  try:result=transact(parent,files,revision)
  except BaseException as exc:error=exc
  pid,ready=d.base.start()
  if error:raise error
  result.update(launcher_pid=pid,readiness=ready,services_restored=True)
 deadline=time.monotonic()+20
 while True:
  hot=d.base.hot_status()
  if hot['revision']==old_hot['revision'] and hot['watcher_running'] and hot['error'] is None:break
  if time.monotonic()>deadline:raise RuntimeError('Prior business did not restore; inspect without transaction replay')
  time.sleep(.2)
 with locks():
  business=lambda v:{k:x for k,x in v.items() if k!='market_simulation'}
  assert business(json.loads(snapshot['state.json']))==business(json.loads((S/'gamedata/state.json').read_bytes()))
  assert snapshot['shop.json']==(S/'gamedata/shop.json').read_bytes()
  result.update(status='CONFIGS_ACTIVE_HOT_PUBLISH_PENDING',hot_before=old_hot,state_business_exact=True,shop_exact=True,files={str(S/p):sha(S/p) for p in [SELF,MANIFEST,RECEIPT,'play-local.bat']},native_gui_verified=False)
  (R/'config-installed.json').write_bytes(encoded(result))
 print(json.dumps(result,ensure_ascii=True))

if __name__=='__main__':main()
