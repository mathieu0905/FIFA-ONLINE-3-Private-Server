"""Activate the reviewed ABI2 business only through the formal publisher."""
import datetime,json,subprocess,time
import install
R=install.R;S=install.S
v=json.loads((R/'config-installed.json').read_text('utf8'));expected=v['hot_before']['revision']
active=json.loads((S/'hot_updates/active.json').read_text('utf8'));assert active['revision']==expected
review=json.loads((R/'reviewed-payloads.json').read_text('utf8'))
assert install.sha(R/'high8-business.py')==review['files'][str(R/'high8-business.py')]
revision='high8_shop_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
command=[str(S/'.venv/Scripts/python.exe'),'-B',str(S/'hot_update_publish.py'),'--source',str(R/'high8-business.py'),'--revision',revision,'--expected-revision',expected]
for route in active['routes']:command+=['--route',route['path']+'='+route['function']]
result=subprocess.run(command,cwd=S,capture_output=True,text=True,encoding='utf8',creationflags=subprocess.CREATE_NO_WINDOW)
(R/'hot-publish.stdout.log').write_text(result.stdout,'utf8');(R/'hot-publish.stderr.log').write_text(result.stderr,'utf8')
if result.returncode:raise RuntimeError('Formal publisher rejected action: '+result.stdout+result.stderr)
deadline=time.monotonic()+25
while True:
 status=install.d.base.hot_status()
 if status['revision']==revision and status['watcher_running'] and status['error'] is None:break
 if time.monotonic()>deadline:raise RuntimeError('Published but not activated; inspect status without replaying transactions')
 time.sleep(.2)
assert status['routes']==[r['path'] for r in active['routes']] or set(status['routes'])=={r['path'] for r in active['routes']}
(R/'hot-active.json').write_bytes(install.encoded(dict(status='HOT_ACTIVE',revision=revision,runtime=status,publication=json.loads((S/'hot_updates/last-publication.json').read_text('utf8')))))
print(json.dumps(dict(status='HOT_ACTIVE',revision=revision,runtime=status),ensure_ascii=True))
