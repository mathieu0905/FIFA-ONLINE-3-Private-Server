"""Wait for a genuinely idle official game, then refresh and publish once."""
from pathlib import Path
import ctypes,datetime,json,os,subprocess,sys,time
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
sys.path.insert(0,str(P))
import install
def state(status,**values):
 (P/'waiting-status.json').write_bytes(install.data(dict(status=status,pid=os.getpid(),at=datetime.datetime.now().astimezone().isoformat(),**values)))
def main():
 ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
 state('WAITING_FOR_IDLE_GAME_AND_RELEASE_LOCKS',formal_written=False)
 while True:
  if (P/'cancel-wait').exists():state('CANCELLED_WITHOUT_INSTALLATION',formal_written=False);return
  if (P/'installed-handback.json').exists():state('ALREADY_INSTALLED',handoff=str(P/'installed-handback.json'));return
  if install.game_running() or any((S/name).exists() for name in ['.shop-release.lock','.fo3-publish.lock']):time.sleep(5);continue
  try:
   state('REFRESHING_CURRENT_OFFICIAL_INPUTS',formal_written=False)
   for file in ['build_runtime.py','test_engine.py','audit_catalogue.py','audit_grades.py']:
    r=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-X','utf8','-B',str(P/file)],cwd=P,capture_output=True,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
    with (P/'deferred-preparation.log').open('a',encoding='utf8') as f:f.write(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError('Fresh preparation failed: '+file+'\n'+r.stdout+r.stderr)
   state('ATTEMPTING_IDLE_ONLY_PUBLICATION',formal_written=False)
   if install.install():state('INSTALLED_AND_LIVE_PASS',handoff=str(P/'installed-handback.json'));return
   state('WAITING_FOR_IDLE_GAME_AND_RELEASE_LOCKS',formal_written=False)
  except FileExistsError:
   state('WAITING_FOR_OTHER_PUBLICATION_OWNER',formal_written=False)
  except Exception as e:
   if '当前游戏继续运行' in str(e):state('WAITING_FOR_IDLE_GAME_AND_RELEASE_LOCKS',formal_written=False)
   else:state('STOPPED_FOR_REVIEW',error=str(e),formal_write_state='Inspect commit/installed handback; no forced retry or service restart');raise
  time.sleep(5)
if __name__=='__main__':main()
