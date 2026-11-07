"""Temporary-only tests for one-window orchestration and recovery boundaries."""
from pathlib import Path
from types import SimpleNamespace as NS
from contextlib import contextmanager
import hashlib,json,tempfile
import install_with_ucl25 as driver
def run_case(root,mode):
 events=[];records=[];live=[True];s=root/'server';r=root/'households';u_root=root/'ucl';r.mkdir(parents=True);u_root.mkdir();(s/'gamedata').mkdir(parents=True);(s/'gamedata/state.json').write_bytes(b'latest-assets');(s/'gamedata/shop.json').write_bytes(b'latest-shop');(root/'root-current-top.json').write_bytes(b'previous-descriptor')
 @contextmanager
 def locks():events.append('locks');yield;events.append('release')
 def command(args):
  events.append('protected-stop')
  if mode=='stop-failure':raise RuntimeError('protected stop refused')
  live[0]=False
 def restart():events.append('restart');live[0]=True;return 1,'ready'
 def u_commit(data,snapshot):
  assert snapshot=={'state.json':b'latest-assets','shop.json':b'latest-shop'};events.append('ucl-commit')
  if mode=='ucl-failure':raise RuntimeError('ucl CAS failed')
  return {}
 def child(u,script):
  events.append(script)
  if mode=='household-failure':raise RuntimeError('fresh build failed')
 fake_u=NS(idle=lambda:mode!='game-running',read=lambda path:{'status':'PASS','installer_sha256':'hash'} if path.name=='transaction-tests.json' else {'cards_imported':360,'new_native':87,'multiplier':.72,'handoff':'ucl-evidence'},sha=lambda path:'hash',locks=locks,assert_idle=lambda:events.append('idle-check'),plan=lambda:{},get=lambda url:{},listening=lambda:[443,8088,28002] if live[0] else [],run=command,commit=u_commit,restart=restart,finish=lambda *args:events.append('ucl-finish'))
 fake_p=NS(source=NS(read=lambda path:{'status':'PASS','installer_sha256':'hash','plan_sha256':'hash'} if path.name=='transaction-tests.json' else {'coverage':{}}),sha=lambda path:'hash')
 fake_h=NS(prepare=fake_p,plan=lambda:{},commit=lambda data,snapshot:events.append('household-commit') or {},finish=lambda *args:events.append('household-finish'),encoded=lambda obj:b'ours')
 previous={k:getattr(driver,k) for k in ('ROOT','U','S','PY','load','save','child')}
 try:
  driver.ROOT=r;driver.U=u_root;driver.S=s;driver.PY=s/'python.exe';driver.save=lambda name,value:records.append((name,value));driver.child=child
  driver.load=lambda path,name:fake_u if path.parent==u_root else fake_h if path.name=='install.py' else fake_p
  try:driver.main()
  except RuntimeError:
   assert mode in ('stop-failure','ucl-failure','household-failure')
  else:assert mode in ('success','game-running')
 finally:
  for k,v in previous.items():setattr(driver,k,v)
 assert (s/'gamedata/state.json').read_bytes()==b'latest-assets' and (s/'gamedata/shop.json').read_bytes()==b'latest-shop'
 if mode=='game-running':assert not events and len(records)==1 and records[0][1]['formal_files_written'] is False
 if mode=='stop-failure':assert 'ucl-commit' not in events and 'restart' not in events and not records
 if mode=='ucl-failure':assert events.count('restart')==1 and 'household-commit' not in events
 if mode=='household-failure':assert events.count('restart')==1 and 'ucl-finish' in events and 'household-commit' not in events
 if mode=='success':
  assert events.count('restart')==1
  assert events.index('ucl-commit')<events.index('install_builder.py')<events.index('household-commit')<events.index('restart')<events.index('household-finish')<events.index('ucl-finish')
  assert events.index('release')<events.index('household-finish')
 return mode
def main():
 root=Path(__file__).resolve().parent
 with tempfile.TemporaryDirectory(prefix='combined-transaction-',dir=root) as folder:cases=[run_case(Path(folder)/mode,mode) for mode in ('game-running','stop-failure','ucl-failure','household-failure','success')]
 result=dict(status='PASS',cases=cases,case_count=len(cases),orchestrator_sha256=hashlib.sha256((root/'install_with_ucl25.py').read_bytes()).hexdigest(),formal_files_written=False,real_services_action=False)
 (root/'combined-transaction-tests.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result))
if __name__=='__main__':main()
