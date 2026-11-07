from pathlib import Path
import importlib.util,json,tempfile,sys
O=Path(__file__).parent
spec=importlib.util.spec_from_file_location('control',O/'fo3_control.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
compile((O/'fo3_control.py').read_text('utf8'),str(O/'fo3_control.py'),'exec')
m.S=Path('D:/FO3ID/server');assert m.gate().is_file()
tests=['latest formal gate resolved without executing batch']
calls=[]
m.closed=lambda:calls.append('closed');m.validate=lambda:calls.append('validate');m.run=lambda args:calls.append([str(x) for x in args]);m.ready=lambda:False
try:m.start_client();raise AssertionError('offline client allowed')
except RuntimeError as e:assert '服务端尚未' in str(e)
assert calls==['closed'];tests.append('client refused when service offline, no start/restart or resource writes')
calls.clear();m.ready=lambda:True
m.subprocess.Popen=lambda *a,**kw:calls.append(('spawn',a,kw))
m.start_client()
assert len([c for c in calls if isinstance(c,tuple)])==1
assert not any('stop-server' in str(c) or 'start_all' in str(c) for c in calls)
assert any('install-grade20' in str(c) for c in calls) and any('_preflight.py' in str(c) for c in calls)
tests.append('client uses resource checks and latest gate, spawns only client and never restarts services')
calls.clear();m.start_server();assert not calls;tests.append('already-ready server start is zero-mutation no-op')
def playing():raise RuntimeError('playing')
m.closed=playing
try:m.stop_server();raise AssertionError('stop while playing allowed')
except RuntimeError:pass
assert not calls;tests.append('stop rejected while game is running')
with tempfile.TemporaryDirectory() as tmp:
    m.S=Path(tmp);lock=m.S/'.shop-release.lock';lock.write_text('other transaction')
    old=sys.argv;sys.argv=['control','client-start']
    try:
        try:m.main();raise AssertionError('lock ignored')
        except FileExistsError:pass
    finally:sys.argv=old
    assert lock.read_text()=='other transaction'
tests.append('publisher lock conflict preserves owner lock')
(O/'tests.json').write_text(json.dumps(dict(status='PASS',tests=tests,production_actions=False),ensure_ascii=False,indent=2),'utf8')
print('PASS: '+str(len(tests))+' checks; no production service/client actions')
