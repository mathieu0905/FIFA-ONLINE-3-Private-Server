"""Function-local ITEMNAMES repair; shared publish lock and guarded idle restart."""
from pathlib import Path
import ast,datetime,importlib.util,inspect,json,os,subprocess,sys,time
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path.insert(0,str(S));import hot_update_release as release
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load(W.parent/'ai-opponent-progression/install.py','achievement_service_primitives');base.R=W
# Current production launch contract; only this installer process's environment.
os.environ['PYTHONUTF8']='1';os.environ['PYTHONIOENCODING']='utf-8'
def closed():
 p=subprocess.run(['powershell.exe','-NoProfile','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9}'],creationflags=subprocess.CREATE_NO_WINDOW)
 if p.returncode:raise RuntimeError('更新已延后，当前游戏继续运行')
base.closed=closed
def payload():
 tests=json.loads((W/'tests.json').read_text('utf8'));assert tests['status']=='PASS' and release.sha(W/'replacement.py')==tests['source_sha256']
 source=(S/'http_config.py').read_text('utf8');node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='ep_itemnames')
 old=ast.get_source_segment(source,node);baseline=(W/'baseline-function.py').read_text('utf8').rstrip()
 assert ast.dump(ast.parse(old))==ast.dump(ast.parse(baseline)),'Current function changed; fresh analysis required'
 lines=source.splitlines(keepends=True);new=''.join(lines[:node.lineno-1])+(W/'replacement.py').read_text('utf8').rstrip()+'\n'+''.join(lines[node.end_lineno:]);compile(new,'http_config.py','exec')
 note='\n\nFO3 ACHIEVEMENT ITEMNAMES LOCALES (2026-11-07)\n原生CoachAchievementListTabPage.onUpdateTooltipData直接把ITEMNAMES[itemid][Localization.LOCALE || kor]传入StringUtil.removeHTML，不对当前语言缺失做逐项回退；旧服务只有ind/kor，chi/eng/tha/vie/tai会得到null，符合22:12:03 UI_ERROR #1009。补齐7种原生locale非空名称，保留原ID与已有ind/kor内容。1222项×7语言及空locale回退的精确字节码片段回放通过；不改成就进度、奖励、领取逻辑或真实资产。未做游戏GUI/原生实机验收。该静态路径不在业务hot ABI范围，游戏关闭后正常受保护重启加载，不能冒称热更新。\n'
 return {'http_config.py':new.encode('utf8'),'docs/工程经验与修改边界.txt':(S/'docs/工程经验与修改边界.txt').read_bytes()+note.encode('utf8')}
def commit(payload):
 # Reuse the mature exact-file CAS/ancestry/receipt transaction in installer scope.
 code=inspect.getsource(release.commit).replace('INSTALLED_HOT_BUSINESS','INSTALLED_ACHIEVEMENT_LOCALES').replace('HOT_BUSINESS_PREFLIGHT_PASS','ACHIEVEMENT_LOCALES_PREFLIGHT_PASS')
 code=code.replace('        for i, e in enumerate(entries):\n            if ', '        for i, e in enumerate(entries):\n            closed()\n            if ')
 ns=dict(vars(release),closed=closed);exec(compile(code,'<achievement release transaction>','exec'),ns)
 return ns['commit'](S,C,'achievement-locales',payload)
def main():
 closed()
 with release.locks(S,'achievement-null-fix'):
  closed();coord=json.loads((W.parent/'coordination-current.json').read_text('utf8'));assert not coord.get('current_unhanded_writers') and not coord.get('next_formal_writer')
  p=payload();oldhot=base.hot_status();release.atomic(W/'pre-stop-hot.json',release.body(oldhot));closed();base.stop()
  result=None;error=None
  try:
   snapshot={name:(S/'gamedata'/name).read_bytes() for name in ('state.json','shop.json')}
   for name,data in snapshot.items():(W/('stopped-'+name)).write_bytes(data)
   result=commit(p);release.atomic(W/'file-transaction-result.json',release.body(result))
  except BaseException as exc:error=exc
  finally:
   # Reopen only after a successful protected stop. A newly running game aborts
   # this path; no forced exit or fallback duplicate launcher is permitted.
   closed();pid,ready=base.start()
  if error:raise error
  deadline=time.monotonic()+90
  while True:
   hot=base.hot_status()
   if hot.get('revision')==oldhot['revision'] and hot.get('watcher_running') and hot.get('error') is None:break
   if time.monotonic()>deadline:raise RuntimeError('Services restored; hot status mismatch; do not restart again')
   time.sleep(.2)
  live=base.call('/static/db/ITEMNAMES');assert live
  for row in live.values():assert all(isinstance(row.get(lang),str) and row[lang] for lang in ('ind','kor','eng','chi','tha','vie','tai'))
  before=json.loads(snapshot['state.json']);after=json.loads((S/'gamedata/state.json').read_bytes());protected=lambda v:{k:x for k,x in v.items() if k!='market_simulation'}
  state_equal=protected(before)==protected(after);shop_equal=snapshot['shop.json']==(S/'gamedata/shop.json').read_bytes()
  result.update(services_restarted=True,services_restored=True,services_action='one protected restart while game closed',launcher_pid=pid,readiness=ready,hot_update_status=hot,live_itemnames_rows=len(live),all_seven_locales=True,state_business_equal=state_equal,shop_equal=shop_equal,game_gui_used=False,native_verified=False,composition_api='compose_manifest(server=None,client=None)',handoff=str(W/'installed-handback.json'))
  release.atomic(W/'installed-handback.json',release.body(result))
  descriptor=json.loads((W.parent/'root-current-top.json').read_text('utf8'));descriptor.update(result,observed_at=datetime.datetime.now().astimezone().isoformat());release.atomic(W.parent/'root-current-top.json',release.body(descriptor))
  assert state_equal and shop_equal,'Concurrent real progress retained, never restore old state/shop'
 return result
if __name__=='__main__':print(json.dumps(main(),ensure_ascii=True))
