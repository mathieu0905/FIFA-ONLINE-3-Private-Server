import ast,io,json,threading,types
from pathlib import Path
from hot_update_release import body
R=Path(__file__).parent
source=(R/'http_config.py').read_text('utf8');tree=ast.parse(source)
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='H')
method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_respond')
lock=threading.RLock();calls=[]
manager=types.SimpleNamespace(handler=lambda path:(lambda q,b:('application/json',b'{"hot":true}')) if path=='/shop/hot-test' else None)
env=dict(STATE_LOCK=lock,hot_update_manager=manager,CDN_PREFIX='cdn/',ep_telemetry=lambda q,b:('application/json',b'{}'),ep_empty=lambda q,b:('application/json',b'{}'),ENDPOINTS={},route=lambda path:None,from_file=lambda path:('application/json',b'{"old":true}'))
exec(compile(ast.Module(body=[method],type_ignores=[]),'bootstrap-method','exec'),env)
def request(path):
    handler=types.SimpleNamespace(path=path,headers={},command='GET',rfile=io.BytesIO(),wfile=io.BytesIO(),_log=lambda b:None,send_response=lambda n:calls.append(n),send_header=lambda *a:None,end_headers=lambda:None)
    env['_respond'](handler);assert calls[-1]==200;return handler.wfile.getvalue()
assert request('/shop/hot-test')==b'{"hot":true}'
assert request('/account')==b'{"old":true}'
assert request('/shop/untouched')==b'{"old":true}'
assert 'hot_update_manager.start()' in source and 'hot_update_manager.stop()' in source
result=dict(status='PASS',checks=['generated real H._respond serves selected hot route','core routes retain existing dispatch','other business routes retain existing dispatch','watcher lifecycle wired into existing host startup and cleanup'],production_services_started=False)
(R/'bootstrap-tests.json').write_bytes(body(result));print(json.dumps(result))
