"""Execute the real install entry with game detected; assert no formal write/stop."""
from pathlib import Path
import importlib.util,json
W=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('sale_install_under_test',W/'install.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.game_active=lambda:True;writes=[]
def deny(*a,**k):raise AssertionError('Formal action attempted while playing')
m.release.locks=deny;m.run=deny;m.start=deny;m.api=deny
def write(p,value):
 assert Path(p).parent==W,'Formal metadata write attempted'
 writes.append((str(p),value))
m.write=write
r=m.main()
assert r['status']=='DEFERRED_GAME_RUNNING' and not r['formal_files_written'] and not r['services_action'] and len(writes)==1
try:m.idle();raise AssertionError('Missing active-game gate')
except RuntimeError as e:assert 'DEFERRED_GAME_RUNNING' in str(e)
(W/'install-gate-tests.json').write_text(json.dumps(dict(status='PASS',checks=2,real_formal_writes=False,real_service_actions=False),indent=2),'utf8')
print('PASS 2 install game-protection checks')
