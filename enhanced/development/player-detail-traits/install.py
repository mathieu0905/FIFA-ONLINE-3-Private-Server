"""Direct formal installation, deferred without any formal writes while playing."""
from pathlib import Path
import sys,json,datetime,re,gzip,hashlib,time,importlib.util
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
sys.path.insert(0,str(R.parent/'team-balance-household'))
tx=load(R.parent/'team-balance-household/install.py','detail_transaction')
tx.R=R
SELF='patches/player_detail_traits_20261107_v1_preflight.py'
MANIFEST='patches/player-detail-traits-20261107-v1-installed.json'
RECEIPT='patches/player-detail-traits-20261107-v1-receipt.json'
EVIDENCE='patches/player-detail-traits-20261107-v1-evidence.json.gz'
DOC='docs/工程经验与修改边界.txt'
tx.SELF=SELF
def sha(p):return tx.prepare.sha(p)
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def save(p,x):Path(p).write_bytes(tx.encoded(x))
def verify_builds():
 report=read(R/'trait-build/report.json');ui=read(R/'ui-build/ui-report.json');tests=read(R/'tests.json')
 if report['status']!='OFFLINE_BUILD_PASS_INSTALL_DEFERRED' or tests['status']!='PASS':raise RuntimeError('Offline verification missing')
 for path,wanted in report['baseline'].items():
  if sha(path)!=wanted:raise RuntimeError('Current formal baseline changed; rebuild: '+path)
 if sha(ui['source'])!=ui['source_sha256'] or sha(S/'gamedata/fifadb.sqlite')!=ui['history_database_sha256']:raise RuntimeError('UI/history baseline changed; rebuild')
 for name,wanted in report['outputs'].items():
  if sha(R/'trait-build'/name)!=wanted:raise RuntimeError('Work product changed: '+name)
 if sha(R/'ui-build/SquadAssets.big')!=ui['output_sha256']:raise RuntimeError('UI work product changed')
 for name,wanted in tests['tooling'].items():
  if sha(R/name)!=wanted:raise RuntimeError('Tested tool changed: '+name)
 return report,ui,tests
def plan():
 report,ui,tests=verify_builds()
 play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches\\(\w+_preflight\.py)',play)
 if len(matches)!=1:raise RuntimeError('Ambiguous actual entry point')
 parent_rel='patches/'+matches[0].decode();parent=load(S/parent_rel,'detail_fresh_parent')
 prior=parent.preflight(S,C);composition=parent.compose_manifest(S,C)
 load(S/'patches/startup_market_preflight.py','detail_verify_manifest').verify_manifest(composition,S,C)
 guards={(g['root'],g['relative'].replace('\\','/').casefold()):dict(g) for g in composition['guards']}
 old_receipt=read(S/parent.RECEIPT);helper=(S/parent_rel).read_text('utf8')
 for old,new in ((parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),
  (old_receipt['status'],'INSTALLED_PLAYER_DETAIL_TRAITS'),(prior['status'],'PLAYER_DETAIL_TRAITS_PREFLIGHT_PASS')):
  if old not in helper:raise RuntimeError('Fresh parent contract changed')
  helper=helper.replace(old,new)
 compile(helper,SELF,'exec')
 revision='player-detail-traits-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 doc=(S/DOC).read_bytes()+('''\r\n\r\nFO3-PLAYER-DETAIL-TRAITS-20261107-V1\r\n
放大镜详情增加独立俱乐部经历页：按playerid聚合当前正式playerhistory，合并卡片当前球队与客户端原生履历，去重；过滤>=900000赛季占位队，不编造年份或真实经历。historyopen=0时以本层绑定的8208身份快照兜底，后续履历更新须同步重建本页，不能继续沿用旧UI快照。原有能力、合同、特性与可选价格页保留，价格页索引移至3。IM原生特性超过8条时使用相同字体的完整滚动文本，普通赛季沿用原生渲染。\r\n
仅123张84赛季的trait1/badges增量：保留已有位、合并同人其它赛季适用正面特性，并按主位置补足，使可见正面特性数严格多于同名普通赛季最高值。113名非门将具备主位置对应的原生全能金徽章；10名门将补齐原生扑单刀/大力手抛/拳击球等适用特性，不造门将金徽章。原生徽章、特性通过不证明比赛胜率/手感。能力值、身份、模型、其它赛季、playerhistory、价格和资产不改。\r\n
AVM2离线执行验证新页去重/空履历/隐藏履历/大于8条/普通赛季切换，非游戏实机；双端SQLite一致、BIG非目标原压缩字节/顺序、player_import完整校验通过。共同双锁、fresh父层全部guards/receipt policies、备份/CAS、停服实时资产快照保护。游戏运行时必须在写入与停服前延期；不强退、不GUI。实机显示/比赛PENDING。工作证据D:/fifaol3/player-detail-traits/。\r\n''').encode('utf8')
 evidence=gzip.compress(tx.encoded(dict(database=report,ui=ui,tests=tests,changes=read(R/'trait-build/changes.json'))),mtime=0)
 payloads=[('server','gamedata/fifadb.sqlite',R/'trait-build/fifadb.sqlite'),
  ('server','gamedata/custom_rosters.json',R/'trait-build/custom_rosters.json'),
  ('server','gamedata/player-import-validation.json',R/'trait-build/player-import-validation.json'),
  ('client','data/data_0.big',R/'trait-build/data_0.big'),('client','data/ui/SquadAssets.big',R/'ui-build/SquadAssets.big'),
  ('server',DOC,doc),('server',EVIDENCE,evidence),('server',SELF,helper.encode('utf8')),
  ('server','play-local.bat',play.replace(parent_rel.replace('/','\\').encode(),SELF.replace('/','\\').encode()))]
 for root,rel,src in payloads:
  target=(S if root=='server' else C)/rel;key=(root,rel.casefold())
  if key in guards and sha(target)!=guards[key]['sha256']:raise RuntimeError('Current parent target differs: '+rel)
  if rel in (SELF,EVIDENCE) and target.exists():raise RuntimeError('Immutable release path exists')
  guards[key]=dict(root=root,relative=rel,sha256=sha(src) if isinstance(src,Path) else tx.digest(src))
 policies=list(composition.get('receipt_policies',[]))
 if not any(p['root']=='server' and p['relative']==parent.RECEIPT for p in policies):policies.append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in old_receipt.items() if k!='native_status'}))
 composition.update(guards=list(guards.values()),receipt_policies=policies,files_verified=False)
 composition.setdefault('ancestry',[]).append(dict(layer='player-detail-traits',revision=revision,native_status='PENDING'))
 m=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=composition['guards'],composition=composition,
  parent_preflight=parent_rel,parent_preflight_sha256=sha(S/parent_rel),evidence=EVIDENCE,native_status='PENDING')
 mb=tx.encoded(m)
 payloads.extend([('server',MANIFEST,mb),('server',RECEIPT,tx.encoded(dict(status='INSTALLED_PLAYER_DETAIL_TRAITS',revision=revision,manifest_sha256=tx.digest(mb),state_shop_replaced=False,native_status='PENDING')))])
 entries=[]
 for root,rel,src in payloads:
  target=(S if root=='server' else C)/rel
  if rel in (MANIFEST,RECEIPT) and target.exists():raise RuntimeError('Immutable metadata exists')
  entries.append(dict(root=root,relative=rel,target=target,source=src,before=tx.current_hash(target),after=sha(src) if isinstance(src,Path) else tx.digest(src)))
 entries.sort(key=lambda e:e['relative']=='play-local.bat')
 return dict(revision=revision,parent=parent_rel,parent_hash=sha(S/parent_rel),entries=entries,prior=prior)
def main():
 if not tx.idle():
  save(R/'install-status.json',dict(status='DEFERRED_GAME_RUNNING',message='更新已延后，当前游戏继续运行',formal_files_written=False,services_restarted=False))
  print('更新已延后，当前游戏继续运行');return
 with tx.locks():
  tx.assert_idle();p=plan()
  save(R/'install-plan.json',{k:v for k,v in p.items() if k!='entries'})
  coord=read(R.parent/'coordination-current.json')
  if coord.get('current_unhanded_writers') or coord.get('next_formal_writer') or coord.get('queue'):raise RuntimeError('Another formal installation window exists; coordinate before writing')
  old_hot=tx.get('http://127.0.0.1:8088/api/hot_update_status');old_colors=tx.get('https://127.0.0.1/static/info/teamcolor')
  running=bool(tx.listening());stopped=False
  if running:
   tx.assert_idle();tx.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',S/'stop-server.ps1'])
   deadline=time.monotonic()+15
   while tx.listening():
    if time.monotonic()>deadline:raise RuntimeError('Protected stop incomplete; no writes or duplicate starts')
    time.sleep(.2)
   stopped=True
  snapshot={n:(S/'gamedata'/n).read_bytes() for n in ('state.json','shop.json')}
  try:result=tx.commit(p,snapshot)
  except BaseException:
   if stopped:tx.restart()
   raise
  if stopped:result['launcher_pid'],result['readiness']=tx.restart()
  result['services_restarted']=stopped
 # Do not wait for watcher activation while holding either publication lock.
 hot=tx.get('http://127.0.0.1:8088/api/hot_update_status')
 deadline=time.monotonic()+25
 while (hot.get('revision')!=old_hot['revision'] or not hot.get('watcher_running')) and time.monotonic()<deadline:
  time.sleep(.25);hot=tx.get('http://127.0.0.1:8088/api/hot_update_status')
 if hot['revision']!=old_hot['revision'] or hot['routes']!=old_hot['routes'] or not hot['watcher_running'] or hot['error'] is not None:raise RuntimeError('Hot package recovery pending; preserve installed assets')
 assert tx.get('https://127.0.0.1/static/info/teamcolor')['teamColors']==old_colors['teamColors']
 proof=load(S/SELF,'detail_final_gate').preflight(S,C)
 result.update(status='INSTALLED_NATIVE_PENDING',revision=p['revision'],top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),
  composition_api='compose_manifest(server=None,client=None)',files={str(S/n):sha(S/n) for n in (SELF,MANIFEST,RECEIPT,'play-local.bat')},
  preflight=proof,hot_update_status=hot,state_shop_written=False,GUI_used=False,native_verified=False,match_verified=False,locks_released=True)
 save(R/'installed-handback.json',result);save(R/'install-status.json',result)
 # Keep the shared observation current using CAS, and never replace a newer observation.
 top=R.parent/'root-current-top.json';observed=top.read_bytes()
 actual=(S/'play-local.bat').read_bytes()
 if SELF.replace('/','\\').encode() in actual and top.read_bytes()==observed:tx.atomic(tx.encoded(result),top)
 print(json.dumps(result,ensure_ascii=True))
if __name__=='__main__':
 if '--inspect-plan' in sys.argv:
  p=plan();print(json.dumps(dict(status='READ_ONLY_PLAN_PASS',parent=p['parent'],files=[str(e['target']) for e in p['entries']],formal_written=False)))
 else:main()

