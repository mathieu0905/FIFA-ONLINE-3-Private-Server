"""Fresh-baseline official removal, deferred before any write while game runs."""
from pathlib import Path
import copy,datetime,importlib.util,json,os,re,shutil,socket,subprocess,sys,time
import build as b
W,S,C=b.W,b.S,b.C;PY=S/'.venv/Scripts/python.exe'
sys.path.insert(0,str(S));import hot_update_release as release
SELF='patches/remove_mbappe_20261107_preflight.py'
MANIFEST='patches/remove-mbappe-20261107-installed.json';RECEIPT='patches/remove-mbappe-20261107-receipt.json'
FORMAL_WRITE_ATTEMPTED=False
SERVICE_ACTIONS=False
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,x):release.atomic(Path(p),b.body(x))
def game_active():
 return 'fifazf.exe' in subprocess.check_output(['tasklist','/FI','IMAGENAME eq fifazf.exe','/FO','CSV','/NH'],text=True,errors='replace').lower()
def idle():
 if game_active():raise RuntimeError('更新已延后，当前游戏继续运行')
def current(p):return b.sha(p) if p.exists() else None
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def env():
 e=dict(os.environ,FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
 e['PSModulePath']=str(Path(e.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/Modules')+';'+str(Path(e.get('ProgramFiles','C:/Program Files'))/'WindowsPowerShell/Modules')
 return e
def run(args):
 r=subprocess.run([str(x) for x in args],cwd=S,env=env(),capture_output=True,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
 if r.returncode:raise RuntimeError(r.stdout+'\n'+r.stderr)
 return r.stdout
def ports():
 out=[]
 for n in (443,8088,28002):
  try:
   with socket.create_connection(('127.0.0.1',n),.2):out.append(n)
  except OSError:pass
 return out
def restart():
 idle()
 if ports():raise RuntimeError('Refusing duplicate service start')
 with (W/'service.stdout.log').open('ab') as out,(W/'service.stderr.log').open('ab') as err:
  p=subprocess.Popen([str(PY),'-B','-u',str(S/'start_all.py')],cwd=S,env=env(),stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
 run([PY,'-B','wait_services.py','--timeout','30']);return p.pid
def migrate(st):
 """Remove active instances only; keep exact historical receipts and balances."""
 out=copy.deepcopy(st);counts={'owned':0,'market_books':0,'npc_assets':0,'offers':0,'bag_cards':0}
 removed_ids=set()
 for t in out.get('teams',{}).values():
  gone=[p for p in t.get('players',[]) if b.blocked(p.get('spid'))]
  removed_ids.update(str(p.get('_id',p.get('id',p.get('spid')))) for p in gone)
  t['players']=[p for p in t.get('players',[]) if not b.blocked(p.get('spid'))];counts['owned']+=len(gone)
 def squad_clean(x):
  if isinstance(x,dict):
   for k,v in list(x.items()):
    if k=='positions' and isinstance(v,list):x[k]=[r for r in v if str(r.get('id',r.get('spid'))) not in removed_ids and not b.blocked(r.get('spid'))]
    elif k=='captain' and str(v) in removed_ids:x[k]=''
    elif k=='kickers' and isinstance(v,list):x[k]=['' if str(r) in removed_ids else r for r in v]
    else:squad_clean(v)
  elif isinstance(x,list):
   for v in x:squad_clean(v)
 for t in out.get('teams',{}).values():squad_clean(t)
 # Presets and tactics can hold instance IDs; never modify receipt subtrees.
 squad_clean(out.get('tactics',{}));squad_clean(out.get('option',{}))
 for coach in out.get('coaches',[]):
  for bag in coach.get('bag',[]):
   if isinstance(bag,dict) and isinstance(bag.get('players'),list):
    old=bag['players'];bag['players']=[p for p in old if not b.blocked(p.get('spid') if isinstance(p,dict) else p)];counts['bag_cards']+=len(old)-len(bag['players'])
 offers=out.get('offers',[]);out['offers']=[r for r in offers if not b.blocked(r.get('spid')) and not b.blocked((r.get('_escrow') or {}).get('spid'))];counts['offers']=len(offers)-len(out['offers'])
 m=out.get('market_simulation',{})
 for section in ('books','rare_books','quotes'):
  d=m.get(section,{})
  if isinstance(d,dict):
   for k in list(d):
    if b.blocked(str(k).split(':')[0]):del d[k];counts['market_books']+=1
 exchange=m.get('npc_exchange',{});assets=exchange.get('assets',{})
 if isinstance(assets,dict):
  for k,v in list(assets.items()):
   if isinstance(v,dict) and b.blocked(v.get('spid')):del assets[k];counts['npc_assets']+=1
 # Keep historical factor/sample evidence; no new pending trades for removed identity.
 q=m.get('identity_quotes',{}).get(str(b.PID))
 if q and q.get('pending'):
  q.setdefault('removed_player_pending_archive',[]).extend(q['pending']);q['pending']=[]
 assert [c.get('cash') for c in st['coaches']]==[c.get('cash') for c in out['coaches']]
 assert [c.get('ep') for c in st['coaches']]==[c.get('ep') for c in out['coaches']]
 return out,counts
def plan():
 idle();p=read(W/'validated-build.json');tests=read(W/'tests.json')
 assert tests['status']=='PASS' and tests['build_sha256']==b.sha(W/'validated-build.json')
 coord=read(W.parent/'coordination-current.json');assert not coord.get('current_unhanded_writers') and not coord.get('next_formal_writer')
 for e in p['payload']:
  assert b.sha(e['source'])==e['after'];target=(S if e['root']=='server' else C)/e['relative'];assert current(target)==e['before'],('Rebuild on latest official file',str(target))
 play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][A-Za-z0-9_]+_preflight\.py',play);assert len(matches)==1
 assert b'tools\\player_import\\check.py' in play
 parent_rel=matches[0].decode().replace('\\','/');assert parent_rel!=SELF
 parent=load(S/parent_rel,'remove_current_parent');prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C));receipt=read(S/parent.RECEIPT)
 guards={(g['root'],g['relative'].replace('\\','/').casefold()):g for g in comp['guards']};assert len(guards)==len(comp['guards'])
 helper=(S/parent_rel).read_text('utf8')
 for old,new in ((parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(receipt['status'],'INSTALLED_REMOVE_MBAPPE'),(prior['status'],'REMOVE_MBAPPE_PREFLIGHT_PASS')):helper=helper.replace(old,new)
 # The new guard requires exact absence; archived economics and model/rig
 # resources are internal evidence, never licensed/selectable player entries.
 extra=''' import sqlite3
 with sqlite3.connect((server/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as database:
  if database.execute('select count(*) from players where playerid=231747 or spid%1000000=231747').fetchone()[0]:raise RuntimeError('Removed player reintroduced')
'''
 anchor=" return dict(nostalgia_fair_value=";assert helper.count(anchor)==1;helper=helper.replace(anchor,extra+anchor);compile(helper,SELF,'exec')
 revision='remove-mbappe-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 note='\n\nFO3-REMOVE-MBAPPE-20261107\n按用户要求移除playerid231747全部4种赛季卡、双端UI/六语言姓名及权限/履历、原生身份、登记和卡池；market_spids旧价并集与add_player阻止所有赛季复入。保留历史经济目录/种子/交易回执与原模型rig内部资源，不改变历史哈希、不将其作为可用球员。原生prepare布局模板改20801，既有骨骼转换基准资源保持。精确原属性归档仅供历史价格完整性验证，当前原目录哈希仍须通过，未来生成目录不加入归档。真实存档仅在停服后fresh事务定点清除目标活动引用，保其它资产与历史回执；游戏运行先延期不写正式、不停服。完整player_import/资源布局/非目标字节校验不代表实机或比赛通过。工作和回执D:/fifaol3/remove-mbappe。\n'
 payload=copy.deepcopy(p['payload'])
 for rel,data in ((SELF,helper.encode('utf8')),('docs/工程经验与修改边界.txt',(S/'docs/工程经验与修改边界.txt').read_bytes()+note.encode('utf8')),('play-local.bat',play.replace(matches[0],SELF.replace('/','\\').encode()))):
  src=W/'artifacts'/Path(rel).name;src.write_bytes(data);payload.append(dict(root='server',relative=rel,source=str(src),before=current(S/rel),after=b.sha(src)))
 for e in payload:
  key=e['root'],e['relative'].casefold()
  if key in guards:assert guards[key]['sha256']==e['before'],('Parent guard drift',key)
  guards[key]=dict(root=e['root'],relative=e['relative'],sha256=e['after'])
 policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in receipt.items() if k!='native_status'})
 if not any(x['root']=='server' and x['relative']==parent.RECEIPT for x in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(policy)
 comp.update(guards=list(guards.values()),files_verified=False);comp.setdefault('ancestry',[]).append(dict(layer='remove-mbappe',revision=revision,native_status='PENDING'))
 manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_rel)
 for rel,data in ((MANIFEST,b.body(manifest)),(RECEIPT,b.body(dict(status='INSTALLED_REMOVE_MBAPPE',revision=revision,manifest_sha256=__import__('hashlib').sha256(b.body(manifest)).hexdigest(),state_shop_replaced=False,native_status='PENDING')))):
  assert not (S/rel).exists();src=W/'artifacts'/Path(rel).name;src.write_bytes(data);payload.append(dict(root='server',relative=rel,source=str(src),before=None,after=b.sha(src)))
 payload.sort(key=lambda e:e['relative']=='play-local.bat');return dict(revision=revision,payload=payload,parent=parent_rel,parent_sha256=b.sha(S/parent_rel))
def commit(p,state_before,shop_before):
 global FORMAL_WRITE_ATTEMPTED
 idle();FORMAL_WRITE_ATTEMPTED=True
 backup=S/'backups'/p['revision'];backup.mkdir(exist_ok=False);(backup/'fresh-state.json').write_bytes(state_before);(backup/'fresh-shop.json').write_bytes(shop_before)
 data,counts=migrate(json.loads(state_before));entries=[]
 for i,e in enumerate(p['payload']):
  e=dict(e);e['target']=(S if e['root']=='server' else C)/e['relative'];e['backup']=backup/str(i)
  assert current(e['target'])==e['before']
  if e['before'] is not None:shutil.copyfile(e['target'],e['backup'])
  entries.append(e)
 state_entry=None
 if data!=json.loads(state_before):
  src=W/'artifacts/fresh-state.json';src.write_bytes(b.body(data));state_entry=dict(root='server',relative='gamedata/state.json',source=str(src),target=S/'gamedata/state.json',backup=backup/'fresh-state.json',before=__import__('hashlib').sha256(state_before).hexdigest(),after=b.sha(src));entries.insert(-1,state_entry)
 journal=dict(status='PREPARED',revision=p['revision'],entries=[{k:str(v) if isinstance(v,Path) else v for k,v in e.items()} for e in entries]);write(backup/'transaction.json',journal);done=[]
 try:
  assert b.sha(S/p['parent'])==p['parent_sha256']
  for e in entries:
   idle();assert current(e['target'])==e['before'];assert b.sha(e['source'])==e['after'];release.atomic(e['target'],Path(e['source']).read_bytes());done.append(e)
  # A fresh interpreter must see proposed model/store code, rather than the
  # parent gate's modules cached during planning.
  proof=json.loads(run([PY,'-B',SELF]))
  full=json.loads(run([PY,'-B','tools/player_import/check.py','--full']));assert full['status']=='PLAYER_IMPORT_FULL_PASS'
  assert (S/'gamedata/shop.json').read_bytes()==shop_before
  assert json.loads((S/'gamedata/state.json').read_bytes())==data
  journal['status']='INSTALLED';write(backup/'transaction.json',journal)
  return dict(backup=str(backup),preflight=proof,player_import=full,removed_active=counts,state_written=state_entry is not None,shop_written=False)
 except BaseException:
  retained=[]
  for e in reversed(done):
   if current(e['target'])!=e['after']:retained.append(str(e['target']));continue
   if e['before'] is None:e['target'].unlink()
   else:release.atomic(e['target'],e['backup'].read_bytes())
  journal.update(status='ROLLED_BACK',later_changes_retained=retained);write(backup/'transaction.json',journal);raise
def main():
 global SERVICE_ACTIONS
 if game_active():
  result=dict(status='DEFERRED_GAME_RUNNING',message='更新已延后，当前游戏继续运行',formal_files_written=False,service_actions=False,validated_build=str(W/'validated-build.json'))
  write(W/'install-status.json',result);print(json.dumps(result,ensure_ascii=True));return
 stopped=False
 assert read(W/'install-tests.json')['status']=='PASS'
 assert read(W/'layout-tests.json')['status']=='PASS'
 with release.locks(S,'remove-mbappe'):
  idle();p=plan();old_hot=json.loads(run([PY,'-B','hot_update_control.py']))
  if ports():
   idle();SERVICE_ACTIONS=True;run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',S/'stop-server.ps1']);stopped=True
   deadline=time.monotonic()+15
   while ports():
    if time.monotonic()>deadline:raise RuntimeError('Protected stop incomplete; no formal writes or duplicate starts')
    time.sleep(.2)
  state=(S/'gamedata/state.json').read_bytes();shop=(S/'gamedata/shop.json').read_bytes()
  try:result=commit(p,state,shop)
  except BaseException:
   if stopped and not game_active() and not ports():restart()
   raise
  if not ports():result['launcher_pid']=restart()
 deadline=time.monotonic()+25
 while True:
  hot=json.loads(run([PY,'-B','hot_update_control.py']))
  if hot['revision']==old_hot['revision'] and hot['watcher_running'] and hot['error'] is None:break
  if time.monotonic()>deadline:raise RuntimeError('Business watcher recovery pending')
  time.sleep(.3)
 result.update(status='INSTALLED_RUNTIME_ACTIVE_NATIVE_PENDING',revision=p['revision'],top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',files={str(S/n):b.sha(S/n) for n in (SELF,MANIFEST,RECEIPT,'play-local.bat')},hot_update_status=hot,services_restored=ports()==[443,8088,28002],services_restarted=stopped,GUI_used=False,native_verified=False,match_verified=False,locks_released=True,handoff=str(W/'installed-handback.json'))
 write(W/'installed-handback.json',result)
 # Reacquire locks for latest-top handback; never overwrite a later publication.
 with release.locks(S,'remove-mbappe-handback'):
  actual=(S/'play-local.bat').read_bytes();top=re.findall(rb'patches[\\/][A-Za-z0-9_]+_preflight\.py',actual)[0].decode().replace('\\','/')
  if top==SELF:write(W.parent/'root-current-top.json',result)
 print(json.dumps(result,ensure_ascii=True))
if __name__=='__main__':
 try:main()
 except RuntimeError as error:
  if str(error)!='更新已延后，当前游戏继续运行':raise
  # A launch racing the first check is also a deferral. The guards in plan()
  # and before stop prevent this path from proceeding to production writes.
  write(W/'install-status.json',dict(status='DEFERRED_GAME_RUNNING',message=str(error),formal_write_attempted=FORMAL_WRITE_ATTEMPTED,service_actions=SERVICE_ACTIONS))
  print(json.dumps(dict(status='DEFERRED_GAME_RUNNING',message=str(error)),ensure_ascii=True))
