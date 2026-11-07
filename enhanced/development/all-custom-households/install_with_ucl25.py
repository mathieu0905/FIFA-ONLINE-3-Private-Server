"""One protected maintenance window for 25UCL plus verified household changes.

Use each validated installer commit unchanged. Rebuild household inputs against
the newly installed UCL files while services remain stopped, then recover once.
No second service, old database overwrite or GUI operation.
"""
from pathlib import Path
import datetime,importlib.util,json,subprocess,sys,time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;U=ROOT.parent/'ucl25-import';S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');PY=S/'.venv/Scripts/python.exe'
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def save(name,value):
 (ROOT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def child(u,name):
 result=subprocess.run([str(PY),'-B',str(ROOT/name)],cwd=ROOT,env=u.environment(),capture_output=True,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
 (ROOT/('combined-'+name+'.stdout.log')).write_text(result.stdout,encoding='utf8');(ROOT/('combined-'+name+'.stderr.log')).write_text(result.stderr,encoding='utf8')
 if result.returncode:raise RuntimeError('Household fresh stage failed: '+name+'\n'+result.stdout+'\n'+result.stderr)
 print('HOUSEHOLD_STAGE_PASS '+name,flush=True)
def main():
 sys.path.insert(0,str(U));u=load(U/'install.py','ucl25_combined_installer')
 if not u.idle():
  save('combined-install-status.json',dict(status='DEFERRED_GAME_RUNNING',formal_files_written=False,services_action=False));print('更新已延后，当前游戏继续运行',flush=True);return
 tests=u.read(U/'transaction-tests.json')
 if tests['status']!='PASS' or tests['installer_sha256']!=u.sha(U/'install.py'):raise RuntimeError('25U transaction tests stale')
 stopped=False;u_result=None;h_result=None;h=None;failure=None
 with u.locks():
  u.assert_idle();data=u.plan();top=ROOT.parent/'root-current-top.json';top_before=top.read_bytes();old_hot=u.get('http://127.0.0.1:8088/api/hot_update_status');before_colors=u.get('https://127.0.0.1/static/info/teamcolor')
  print('FRESH_25U_PLAN_PASS',flush=True)
  if u.listening():
   u.assert_idle();u.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',S/'stop-server.ps1']);deadline=time.monotonic()+15
   while u.listening():
    if time.monotonic()>deadline:raise RuntimeError('Protected stop incomplete; no writes or duplicate service start')
    time.sleep(.2)
   stopped=True
  snapshot={n:(S/'gamedata'/n).read_bytes() for n in ('state.json','shop.json')}
  save('combined-install-status.json',dict(status='PROTECTED_MAINTENANCE_STARTED',formal_files_written=False,services_stopped=stopped))
  try:
   u_result=u.commit(data,snapshot);print('25U_FORMAL_FULL_COMMIT_PASS',flush=True)
   # Rebase against actual just-installed files and active price generation.
   # Only compilation artifacts are written by these child stages.
   for script in ('install_builder.py','install_tests.py','test_install.py'):child(u,script)
   sys.path.insert(0,str(ROOT));load(ROOT/'prepare.py','prepare');h=load(ROOT/'install.py','households_combined_installer')
   transaction=h.prepare.source.read(ROOT/'transaction-tests.json')
   if transaction['status']!='PASS' or transaction['installer_sha256']!=h.prepare.sha(ROOT/'install.py') or transaction['plan_sha256']!=h.prepare.sha(ROOT/'install_plan.py'):raise RuntimeError('Fresh household transaction regression stale')
   household=h.plan();h_result=h.commit(household,snapshot);print('HOUSEHOLDS_FORMAL_FULL_COMMIT_PASS',flush=True)
  except BaseException as error:
   failure=error
   save('combined-install-error.json',dict(error=repr(error),ucl_committed=u_result is not None,household_committed=h_result is not None,assets_restored=False))
  # Never start a duplicate server or override a gameplay protection refusal.
  if stopped:
   if u.listening():raise RuntimeError('Unexpected listener before service recovery; no duplicate start')
   pid,ready=u.restart();print('SERVICES_RECOVERED_ONCE',flush=True)
   if u_result is not None:u_result.update(launcher_pid=pid,readiness=ready,services_restarted=True)
   if h_result is not None:h_result.update(launcher_pid=pid,readiness=ready,services_restarted=True)
 if failure is not None:
  if u_result is not None:u.finish(data,u_result,snapshot,old_hot,top,top_before)
  raise failure
 # Existing watcher must activate after releasing both common locks.
 h.finish(household,h_result,snapshot,old_hot,before_colors,top,top_before)
 u.finish(data,u_result,snapshot,old_hot,top,top_before)
 current=h.prepare.source.read(ROOT/'installed-handback.json');ucl=u.read(U/'installed-handback.json')
 result=dict(status='COMBINED_INSTALLED_AND_RUNTIME_ACTIVE_NATIVE_PENDING',ucl25=ucl,households=current,services_restarted_once=stopped,real_state_shop_replaced=False,GUI_used=False,native_game_verified=False,match_verified=False,full_career_review_complete=False,observed_at=datetime.datetime.now().astimezone().isoformat())
 save('combined-installed-handback.json',result);save('combined-install-status.json',dict(status=result['status'],formal_writer=False,evidence=str(ROOT/'combined-installed-handback.json')))
 # Root descriptor already points to the actual household top. Enrich only our
 # exact descriptor; never replace a newer owner's observation.
 expected=h.encoded(current)
 if top.read_bytes()==expected:
  current.update(combined_25ucl=dict(cards=ucl['cards_imported'],new_native=ucl['new_native'],identity_reused=121,multiplier=ucl['multiplier'],handback=ucl['handoff']),combined_handback=str(ROOT/'combined-installed-handback.json'));h.atomic(h.encoded(current),top)
 print('COMBINED_INSTALL_COMPLETE: 360 25UCL cards plus verified households; native GUI/match pending',flush=True)
if __name__=='__main__':main()
