from pathlib import Path
import sys,importlib.util,types,threading,json,tempfile
R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prepared_hot_v2',R/'hot-v2/hot_update_runtime.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
host=types.SimpleNamespace(STATE_LOCK=threading.RLock(),sentinel=object());manager=m.Manager(host,R)
source='def opened(host, query, body):\n    return (host.hot_path_params["item_id"], query, body, host.sentinel)\n'
routes=[dict(path='/item/{item_id}/use',function='opened')]
try:m.compile_handlers(source,'case',routes)
except ValueError:pass
else:raise AssertionError('ABI1 accepted dynamic route')
fn=m.compile_handlers(source,'case',routes,allow_templates=True)['/item/{item_id}/use']
manager._handlers={'/item/{item_id}/use':lambda params:lambda query,body:fn(m.RequestHost(host,params),query,body)}
a=manager.handler('/item/a_pf_v2_0_deadbeef/use');b=manager.handler('/item/b/use')
assert a('q',b'{}')[:3]==('a_pf_v2_0_deadbeef','q',b'{}') and b('',b'')[0]=='b'
assert manager.handler('/item/a/use/extra') is None and manager.handler('/item/a-b/use') is None
assert manager.handler('/coach/a/use') is None
manager._handlers['/item/b/use']=lambda q,b:'exact';assert manager.handler('/item/b/use')('',b'')=='exact'
manager._handlers={};assert a('',b'')[0]=='a_pf_v2_0_deadbeef'
view=m.RequestHost(host,{'item_id':'x'})
try:view.hot_path_params['item_id']='y'
except TypeError:pass
else:raise AssertionError('Mutable captures')
try:view.sentinel='y'
except AttributeError:pass
else:raise AssertionError('Mutable host view')
for path in ('/coach/{id}/me','/item/{other}/use','/shop/{wildcard}','/item/{item_id}/use/extra'):
 try:m.compile_handlers(source,'bad',[dict(path=path,function='opened')],allow_templates=True)
 except ValueError:pass
 else:raise AssertionError(path)
with tempfile.TemporaryDirectory() as temp:
 root=Path(temp);relative='hot_updates/revisions/dynamic_test/business.py';p=root/relative;p.parent.mkdir(parents=True);p.write_text(source,encoding='utf8')
 data=json.dumps(dict(schema=1,revision='dynamic_test',state_shop_replaced=False,guards=[dict(root='server',relative=relative,sha256=m.digest(p.read_bytes()))])).encode()
 receipt=json.dumps(dict(revision='dynamic_test',manifest_sha256=m.digest(data))).encode()
 (root/'manifest.json').write_bytes(data);(root/'receipt.json').write_bytes(receipt)
 descriptor=dict(schema=1,abi=2,revision='dynamic_test',expected_revision='bootstrap',code=relative,sha256=m.digest(p.read_bytes()),routes=routes,release=dict(manifest='manifest.json',receipt='receipt.json',manifest_sha256=m.digest(data),receipt_sha256=m.digest(receipt)))
 (root/'hot_updates/active.json').write_text(json.dumps(descriptor),encoding='utf8')
 running=m.Manager(host,root);assert running.poll()
 assert running.handler('/item/actual_dynamic_token/use')('q',b'{}')[:3]==('actual_dynamic_token','q',b'{}')
 descriptor['abi']=1
 try:running.prepare(descriptor)
 except ValueError:pass
 else:raise AssertionError('ABI1 descriptor acquired dynamic capabilities')
result=dict(status='PASS',checks=['ABI1 rejects dynamic routes','only three allowlisted business templates supported','captures isolated between requests','captures and host view immutable','exact routes take precedence','full-path matching rejects suffix and unsupported tokens','in-flight handler retains generation','core and arbitrary wildcard templates rejected'],formal_files_written=False,runtime_enabled=False)
result['checks'].append('signed ABI2 descriptor prepares, activates and dispatches dynamic route; ABI1 cannot acquire template capabilities')
(R/'hot-v2/dynamic-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
