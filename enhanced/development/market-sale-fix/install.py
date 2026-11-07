"""Official source transaction. No game interruption, no second server, no state restore."""
from pathlib import Path
import sys,os,copy,json,hashlib,datetime,subprocess,ssl,time,re,shutil,urllib.request,socket
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');sys.path.insert(0,str(S))
import hot_update_release as release
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,v):release.atomic(Path(p),release.body(v))
def game_active():
 return 'fifazf.exe' in subprocess.check_output(['tasklist','/FI','IMAGENAME eq fifazf.exe','/FO','CSV','/NH'],text=True,errors='replace',creationflags=subprocess.CREATE_NO_WINDOW).lower()
def idle():
 if game_active():raise RuntimeError('DEFERRED_GAME_RUNNING: 更新已延后，当前游戏继续运行')
def run(args):
 r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
 if r.returncode:raise RuntimeError(r.stdout+'\n'+r.stderr)
 return r.stdout
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def api(path):
 url=('http://127.0.0.1:8088'+path) if path.startswith('/api/') else 'https://127.0.0.1'+path
 with opener.open(url,timeout=15) as r:return json.load(r)
def start():
 with (W/'service.stdout.log').open('ab') as out,(W/'service.stderr.log').open('ab') as err:
  p=subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-B','-u',str(S/'start_all.py')],cwd=S,
   env=dict(os.environ,FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',PYTHONUTF8='1',PYTHONIOENCODING='utf-8'),
   stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
 return p.pid
def sockets_closed():
 for port in (443,8088,28002):
  with socket.socket() as s:
   s.settimeout(.2)
   if s.connect_ex(('127.0.0.1',port))==0:return False
 return True
def wait_stopped():
 deadline=time.monotonic()+12
 while time.monotonic()<deadline:
  if sockets_closed():return
  time.sleep(.2)
 raise RuntimeError('Managed service socket still listening; no duplicate server started')
def wait_ready():
 deadline=time.monotonic()+55;last=None
 while time.monotonic()<deadline:
  try:
   status=api('/api/market_status');services=api('/info/my/services/messenger/2')
   if status.get('player_sale_policy')==2 and status['background']['running'] and status['background']['errors']==0:return status,services
  except Exception as e:last=repr(e)
  time.sleep(.5)
 raise RuntimeError('Runtime not ready: '+str(last))
def protected(st):return {k:v for k,v in st.items() if k not in ('offers','market_simulation')}
def asset(p):return {k:v for k,v in p.items() if not k.startswith('_market_')}
def main():
 if game_active():
  result=dict(status='DEFERRED_GAME_RUNNING',message='更新已延后，当前游戏继续运行',formal_files_written=False,services_action=False)
  write(W/'deferred.json',result);return result
 assert read(W/'regression.json')['status']=='PASS' and read(W/'native-contract.json')['status']=='PASS'
 for rel,h in read(W/'baseline.json').items():assert release.sha(S/rel)==h,'Rebase on latest official source: '+rel
 compile((W/'market_simulation.py').read_text('utf8'),'market_simulation.py','exec')
 hot_before=api('/api/hot_update_status');assert hot_before['watcher_running'] and hot_before['error'] is None
 active_before=release.sha(S/'hot_updates/active.json')
 stopped=False;installed=False
 with release.locks(S,'market-sale-fix'):
  coord=read(W.parent/'coordination-current.json');assert not coord.get('current_unhanded_writers') and not coord.get('next_formal_writer'),'Another writer owns formal install'
  idle();play=(S/'play-local.bat').read_bytes();parent_rel=re.findall(rb'patches[\\/][a-z0-9_]+_preflight\.py',play)[0].decode().replace('\\','/')
  parent=release.load(S/parent_rel,'sale_parent');parent.preflight(S,C)
  assert release.sha(S/'hot_updates/active.json')==active_before,'Concurrent hot package publication; refresh status'
  for rel,h in read(W/'baseline.json').items():assert release.sha(S/rel)==h,'Concurrent source change'
  note='\n\nFO3-MARKET-SALE-FIX (2026-11-07; native GUI pending)\n实际原生TransferMarketProxy.STATUS_SELLING与挂牌renderer期待waiting；存档内部仍用selling，仅响应副本映射waiting，并为原生撤单URI接受waiting别名，不能直接改真实存档状态。客户端原有改价弹窗复用/transfer/offer/from/{id}；允许在售改价，先结算再判断，已成交保留原价款项；同价重放不重排买家时间。卡实例/经验/强化/球衣/队伍/出处保留。\n现价及以下挂牌保证买家，半价约1至3分钟、八折约3至10分钟、现价约10至30分钟，后台tick另有至多一个轮询周期；不受旧同SPID高强化每日两人额度阻挡。高于现价仍有需求概率和买家限额。电脑买入/衍生卡保留原有一小时持有约束，手续费和手动领取保持。仍在售旧挂牌安全采用新策略，旧已到达成交时刻不延期、旧已成交权益/原手续费不回算，旧已过期单不复活。\n65项临时资产事务/并发/失败/重放回归及5项实际客户端字节码契约验证通过；未做真实测试买卖、GUI或比赛验证。REA不支持私有BIG，使用已有bigdir/ABC工具只读核对，无客户端资源替换。后台worker/对象方法不属ABI2业务热更新，必须游戏自然结束后经正式stop-server保护、共同双锁、fresh顶层/资产快照、备份及CAS组合安装并正常重启；不得用reload或强退游戏实现激活，不恢复旧state/shop。\n'.encode('utf8')
  payload={'market_simulation.py':(W/'market_simulation.py').read_bytes(),'docs/工程经验与修改边界.txt':(S/'docs/工程经验与修改边界.txt').read_bytes()+note}
  idle();print('PARENT_AND_BASELINE_PASS',parent_rel,flush=True)
  try:
   # Protection is authoritative. Never continue a failed/deferred stop.
   run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')]);stopped=True
   wait_stopped()
   snap=W/'fresh-install-snapshot'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');snap.mkdir(parents=True)
   for name in ('state.json','shop.json'):shutil.copyfile(S/'gamedata'/name,snap/name)
   before=read(snap/'state.json');shop_hash=release.sha(S/'gamedata/shop.json')
   idle()
   for rel,h in read(W/'baseline.json').items():assert release.sha(S/rel)==h,'Concurrent source change after stop'
   result=release.commit(S,C,'market-sale-fix',payload);installed=True
   print('FORMAL_COMMIT_PASS',result['top_preflight'],flush=True)
   # The already-running launcher exits after its managed children stop. Avoid
   # starting another server until the old sockets have actually disappeared.
   pid=start();stopped=False
   status,services=wait_ready();print('RUNTIME_POLICY_2_READY',pid,flush=True)
   after=read(S/'gamedata/state.json')
   assert protected(before)==protected(after),'Unexpected business progress: retained, never restored'
   assert release.sha(S/'gamedata/shop.json')==shop_hash,'Shop changed: retained, never restored'
   oldoffers={o['_id']:o for o in before.get('offers',[])};newoffers={o['_id']:o for o in after.get('offers',[])}
   assert oldoffers.keys()==newoffers.keys(),'No install-time listing deletion or claim collection'
   for i,o in oldoffers.items():
    n=newoffers[i]
    for key in ('price','completefee','spid','grade','_market_owner','playerobjectid'):
     assert n.get(key)==o.get(key),(i,key)
    assert asset(n.get('_market_player',{}))==asset(o.get('_market_player',{})),i
   result.update(status='INSTALLED_AND_RUNTIME_ACTIVE_NATIVE_PENDING',services_action='Normal protected stop and restart while game absent',services_restarted=True,
    source_sha256=release.sha(S/'market_simulation.py'),runtime_market_policy=status['player_sale_policy'],runtime_reprice=status['reprice_while_selling'],
    runtime_wire_status=status['native_offer_status'],guaranteed_sale=status['guaranteed_sale'],background=status['background'],
    fresh_snapshot=str(snap),business_assets_equal=True,shop_equal=True,existing_offer_count=len(oldoffers),existing_offer_assets_and_terms_preserved=True,
    real_test_purchase=False,real_test_sale=False,GUI_used=False,client_files_written=False,match_verified=False,launcher_pid=pid,
    composition_api='compose_manifest(server=None,client=None)',regression=str(W/'regression.json'),native_contract=str(W/'native-contract.json'))
   write(W/'installed-handback.json',result)
  except BaseException:
   # The release helper CAS-rolls back only its own failed file transaction.
   # Never restore manager state/shop. An installed transaction is left visible
   # with its journal if runtime verification fails, rather than erasing progress.
   if stopped and sockets_closed():start()
   raise
 # Watcher reads signed hot package only after the shared publication lock ends.
 deadline=time.monotonic()+20
 while time.monotonic()<deadline:
  hot=api('/api/hot_update_status')
  if hot['revision']==hot_before['revision'] and hot['routes']==hot_before['routes'] and hot['watcher_running'] and hot['error'] is None:break
  time.sleep(.5)
 else:raise RuntimeError('Existing hot business package not recovered: '+repr(hot))
 result.update(runtime_hot_update=hot,locks_released=True,services_restored=True,observed_at=datetime.datetime.now().astimezone().isoformat())
 write(W/'installed-handback.json',result)
 # Observe latest entry again; never replace another lawful child's descriptor.
 current=(S/'play-local.bat').read_bytes()
 if Path(result['top_preflight']).name.encode() in current:
  descriptor=read(W.parent/'root-current-top.json');descriptor.update(result,handoff=str(W/'installed-handback.json'));write(W.parent/'root-current-top.json',descriptor)
 else:result['later_top_retained']=True;write(W/'installed-handback.json',result)
 return result
if __name__=='__main__':
 try:print(json.dumps(main(),ensure_ascii=True),flush=True)
 except RuntimeError as e:
  if 'DEFERRED_GAME_RUNNING' in str(e) or '更新已延后' in str(e):
   write(W/'deferred.json',dict(status='DEFERRED_GAME_RUNNING',message='更新已延后，当前游戏继续运行',error=str(e)));print(str(e),flush=True)
  else:raise
