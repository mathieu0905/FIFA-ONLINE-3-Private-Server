"""Publish one native GFx carrier correction on the actual latest composition."""
from pathlib import Path
import sys,json,re,datetime,gzip,time,importlib.util
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
def load(p,n):
 spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
sys.path.insert(0,'D:/fifaol3/team-balance-household')
tx=load(Path('D:/fifaol3/team-balance-household/install.py'),'carrier_transaction');tx.R=R
SELF='patches/player_detail_native_carrier_preflight.py'
MANIFEST='patches/player-detail-native-carrier-installed.json'
RECEIPT='patches/player-detail-native-carrier-receipt.json'
EVIDENCE='patches/player-detail-native-carrier-evidence.json.gz'
DOC='docs/工程经验与修改边界.txt';tx.SELF=SELF
def sha(p):return tx.prepare.sha(p)
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def save(p,x):Path(p).write_bytes(tx.encoded(x))
def plan():
 b=read(R/'build/report.json');tests=read(R/'tests.json')
 if b['status']!='NATIVE_CARRIER_REPAIR_BUILD_PASS' or tests['status']!='PASS':raise RuntimeError('Carrier checks missing')
 if sha(b['source'])!=b['source_sha256'] or sha(R/'build/SquadAssets.big')!=b['output_sha256']:raise RuntimeError('Carrier baseline changed; rebuild')
 for name,wanted in tests['tooling'].items():
  if sha(R/name)!=wanted:raise RuntimeError('Untested tooling change')
 play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches\\(\w+_preflight\.py)',play)
 if len(matches)!=1:raise RuntimeError('Ambiguous latest entry')
 parent_rel='patches/'+matches[0].decode();parent=load(S/parent_rel,'carrier_actual_parent')
 prior=parent.preflight(S,C);comp=parent.compose_manifest(S,C)
 load(S/'patches/startup_market_preflight.py','carrier_comp_verify').verify_manifest(comp,S,C)
 guards={(g['root'],g['relative'].replace('\\','/').casefold()):dict(g) for g in comp['guards']}
 receipt=read(S/parent.RECEIPT);helper=(S/parent_rel).read_text('utf8')
 for old,new in ((parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(receipt['status'],'INSTALLED_PLAYER_DETAIL_NATIVE_CARRIER'),(prior['status'],'PLAYER_DETAIL_NATIVE_CARRIER_PREFLIGHT_PASS')):
  if old not in helper:raise RuntimeError('Parent contract changed')
  helper=helper.replace(old,new)
 compile(helper,SELF,'exec')
 revision='player-detail-native-carrier-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 doc=(S/DOC).read_bytes()+('''\r\n\r\nFO3-PLAYER-DETAIL-NATIVE-CARRIER-20261107\r\n
用户实机反馈放大镜无响应。本层修正上一层SquadAssets.gfx载体签名错误：原生资源CFX被写成CWS，同时仍含1000/1008/1009扩展标签。恢复原CFX，仅成员前三字节改变；全部已安装ABC、时间轴、字体与纹理标签、其它BIG成员原压缩字节完全不变；保留新增俱乐部经历页与IM特性数据，不回退后续阵容快捷入口/社交等合法子层。\r\n
此前AVM2测试绕过原生GFx加载器，不能证明客户端成功加载。新增签名/专用标签/完整50个ABC与成员差异回归。载体修正只是静态修复证据，放大镜实机打开及比赛均需单独确认；若仍无响应继续查实际加载路径，不把该静态检查称为实机通过。\r\n
游戏运行时安装在任何正式写入/停服前延期；共同双锁、fresh最新compose_manifest全部guards/receipt policies、备份/CAS、最新state/shop快照只核对不恢复。无游戏GUI操作，无测试资产写入。\r\n''').encode('utf8')
 evidence=gzip.compress(tx.encoded(dict(build=b,tests=tests)),mtime=0)
 payloads=[('client','data/ui/SquadAssets.big',R/'build/SquadAssets.big'),('server',DOC,doc),('server',SELF,helper.encode()),('server',EVIDENCE,evidence),
  ('server','play-local.bat',play.replace(parent_rel.replace('/','\\').encode(),SELF.replace('/','\\').encode()))]
 for root,rel,src in payloads:
  target=(S if root=='server' else C)/rel;key=(root,rel.casefold())
  if key in guards and sha(target)!=guards[key]['sha256']:raise RuntimeError('Current parent file changed')
  if rel in (SELF,EVIDENCE) and target.exists():raise RuntimeError('Immutable carrier release exists')
  guards[key]=dict(root=root,relative=rel,sha256=sha(src) if isinstance(src,Path) else tx.digest(src))
 policies=list(comp.get('receipt_policies',[]))
 if not any(p['root']=='server' and p['relative']==parent.RECEIPT for p in policies):policies.append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in receipt.items() if k!='native_status'}))
 comp.update(guards=list(guards.values()),receipt_policies=policies,files_verified=False)
 comp.setdefault('ancestry',[]).append(dict(layer='player-detail-native-carrier',revision=revision,native_status='PENDING'))
 manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_rel,parent_preflight_sha256=sha(S/parent_rel),native_status='PENDING')
 mb=tx.encoded(manifest)
 payloads.extend([('server',MANIFEST,mb),('server',RECEIPT,tx.encoded(dict(status='INSTALLED_PLAYER_DETAIL_NATIVE_CARRIER',revision=revision,manifest_sha256=tx.digest(mb),state_shop_replaced=False,native_status='PENDING')))])
 entries=[]
 for root,rel,src in payloads:
  target=(S if root=='server' else C)/rel
  if rel in (MANIFEST,RECEIPT) and target.exists():raise RuntimeError('Immutable metadata exists')
  entries.append(dict(root=root,relative=rel,target=target,source=src,before=tx.current_hash(target),after=sha(src) if isinstance(src,Path) else tx.digest(src)))
 entries.sort(key=lambda e:e['relative']=='play-local.bat')
 return dict(revision=revision,parent=parent_rel,parent_hash=sha(S/parent_rel),entries=entries,prior=prior)
def main():
 if not tx.idle():
  save(R/'install-status.json',dict(status='DEFERRED_GAME_RUNNING',formal_files_written=False,services_restarted=False,message='更新已延后，当前游戏继续运行'))
  print('更新已延后，当前游戏继续运行');return
 with tx.locks():
  tx.assert_idle();coord=read(R.parent/'coordination-current.json')
  if coord.get('current_unhanded_writers') or coord.get('next_formal_writer') or coord.get('queue'):raise RuntimeError('Another formal writer window requires coordination')
  p=plan();save(R/'install-plan.json',{k:v for k,v in p.items() if k!='entries'})
  top=R.parent/'root-current-top.json';top_before=top.read_bytes()
  hot_before=tx.get('http://127.0.0.1:8088/api/hot_update_status');was_running=bool(tx.listening());stopped=False
  if was_running:
   tx.assert_idle();tx.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',S/'stop-server.ps1'])
   limit=time.monotonic()+15
   while tx.listening():
    if time.monotonic()>limit:raise RuntimeError('Protected stop failed; no writes/start')
    time.sleep(.2)
   stopped=True
  snapshot={n:(S/'gamedata'/n).read_bytes() for n in ('state.json','shop.json')}
  try:result=tx.commit(p,snapshot)
  except BaseException:
   if stopped:tx.restart()
   raise
  if stopped:result['launcher_pid'],result['readiness']=tx.restart()
  result['services_restarted']=stopped
 hot=tx.get('http://127.0.0.1:8088/api/hot_update_status');limit=time.monotonic()+25
 while (hot.get('revision')!=hot_before['revision'] or not hot.get('watcher_running')) and time.monotonic()<limit:
  time.sleep(.25);hot=tx.get('http://127.0.0.1:8088/api/hot_update_status')
 if hot!=hot_before:raise RuntimeError('Hot state changed; preserve installation and inspect')
 proof=load(S/SELF,'carrier_installed').preflight(S,C)
 old=json.loads(snapshot['state.json']);now=read(S/'gamedata/state.json');business=lambda v:{k:x for k,x in v.items() if k!='market_simulation'}
 result.update(status='INSTALLED_NATIVE_OPEN_PENDING',revision=p['revision'],top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',
  files={str(S/n):sha(S/n) for n in (SELF,MANIFEST,RECEIPT,'play-local.bat')},client_files={str(C/'data/ui/SquadAssets.big'):sha(C/'data/ui/SquadAssets.big')},
  preflight=proof,hot_update_status=hot,services_restored=tx.listening()==[443,8088,28002],state_business_equal=business(old)==business(now),shop_equal=(S/'gamedata/shop.json').read_bytes()==snapshot['shop.json'],
  state_shop_written=False,GUI_used=False,native_verified=False,match_verified=False,locks_released=True,observed_at=datetime.datetime.now().astimezone().isoformat())
 save(R/'installed-handback.json',result);save(R/'install-status.json',result)
 if top.read_bytes()==top_before:tx.atomic(tx.encoded(result),top)
 print(json.dumps(result,ensure_ascii=True))
if __name__=='__main__':
 if '--inspect-plan' in sys.argv:
  p=plan();print(json.dumps(dict(status='READ_ONLY_PLAN_PASS',parent=p['parent'],files=[str(e['target']) for e in p['entries']])))
 else:main()
