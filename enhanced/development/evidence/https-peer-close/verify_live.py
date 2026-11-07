from pathlib import Path
import ssl,socket,struct,time,json,hashlib,ast,importlib.util,requests,urllib3
urllib3.disable_warnings();S=Path('D:/FO3ID/server');O=Path(__file__).parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
beforelog=(S/'captures/http_config.log').stat().st_size
ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);ctx.check_hostname=False;ctx.verify_mode=ssl.CERT_NONE
conn=ctx.wrap_socket(socket.create_connection(('127.0.0.1',443),timeout=5),server_hostname='APSEODESK172')
conn.sendall(b'GET /cdn/externalAssets/language_chi.big HTTP/1.0\r\nHost: APSEODESK172\r\n\r\n')
head=conn.recv(4096);assert b'200 OK' in head,head[:200]
fd=conn.detach();raw=socket.socket(fileno=fd);raw.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('hh',1,0));raw.close()
deadline=time.monotonic()+4;tail=''
while time.monotonic()<deadline:
    with (S/'captures/http_config.log').open('rb') as f:f.seek(beforelog);tail=f.read().decode('utf8','replace')
    if 'HTTP peer disconnected' in tail:break
    time.sleep(.05)
assert 'HTTP peer disconnected' in tail,'Live response abort did not exercise the fixed handler'
apis={}
for uri in ('/info/my/services/messenger/2','/coaches','/coach/me'):
    r=requests.get('https://127.0.0.1'+uri,verify=False,timeout=5);assert r.status_code==200;apis[uri]=r.status_code
before=json.loads((O/'state-before-reload.json').read_text('utf8'));after=json.loads((S/'gamedata/state.json').read_text('utf8'))
changes=[k for k in set(before)|set(after) if before.get(k)!=after.get(k)]
inst=json.loads((O/'installation.json').read_text('utf8'));backup=Path(inst['backup'])
old=ast.parse((backup/'0.backup').read_text('utf-8-sig'));new=ast.parse((S/'http_config.py').read_text('utf-8-sig'))
cl=next(n for n in new.body if isinstance(n,ast.ClassDef) and n.name=='H');cl.body=[n for n in cl.body if not isinstance(n,ast.FunctionDef) or n.name!='handle'];assert ast.dump(old)==ast.dump(new)
helper=S/'patches/http_disconnect_preflight.py';spec=importlib.util.spec_from_file_location('peer_close_gate',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);gate=m.preflight(S,Path('D:/FO3ID/32795'))
paths=[helper,S/'patches/http-disconnect-installed.json',S/'patches/http-disconnect-receipt.json',S/'http_config.py',S/'play-local.bat']
result=dict(status='INSTALLED_LIVE_HTTPS_DISCONNECT_PASS',live_readonly_TLS_response_abort_logged=True,live_peer_log=tail,post_abort_fresh_GET_200=apis,preflight=gate,parent=json.loads((S/'patches/http-disconnect-installed.json').read_text('utf8'))['parent'],API='compose_manifest(server=None,client=None); preflight(server=None,client=None)',hashes={str(p):sha(p) for p in paths},backup=str(backup),source_ast_delta_only_H_handle=True,state_changed_fields=changes,coaches_equal=before['coaches']==after['coaches'],teams_equal=before['teams']==after['teams'],shop_bytes_equal=sha(O/'shop-before-reload.json')==sha(S/'gamedata/shop.json'),state_shop_written_by_installer=False,services_reloaded_with_explicit_human_timing_approval=True,game_started_or_stopped_by_this_task=False,native_crash_cause_verified=False)
assert result['coaches_equal'] and result['teams_equal'] and result['shop_bytes_equal'],result
(O/'handback.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8');print(json.dumps({k:v for k,v in result.items() if k!='live_peer_log'},indent=2))
