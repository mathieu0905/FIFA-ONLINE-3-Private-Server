"""Real temporary TLS response-abort regression using the exact production H class.

No business module import, production listener, state/shop, or game process is used.
"""
from pathlib import Path
import ast,contextlib,http.server,ssl,socket,struct,threading,time,json,gzip,tempfile,unittest.mock
O=Path(__file__).parent;S=Path('D:/FO3ID/server');results=[]
def handler(source,log,commit,entered,release):
    h=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='H')
    def drop(q,b):
        commit.append(b);entered.set();assert release.wait(5)
        return 'application/octet-stream',b'X'*(8*1024*1024)
    def ok(q,b):return 'application/json',json.dumps({'result':True,'commits':len(commit)}).encode()
    ns=dict(http=http,ssl=ssl,time=time,LOG=str(log),gzip=gzip,STATE_LOCK=threading.RLock(),CDN_PREFIX='cdn',from_file=lambda p:None,ENDPOINTS={'/drop':drop,'/ok':ok},route=lambda p:None,ep_empty=ok,ep_telemetry=ok,_json=lambda v:('application/json',json.dumps(v).encode()))
    exec(compile(ast.Module(body=[h],type_ignores=[]),'<exact HTTP handler>','exec'),ns)
    H=ns['H']
    class Quiet(H):
        def _log(self,body):pass
    return H,Quiet
def connect(port):
    ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);ctx.check_hostname=False;ctx.verify_mode=ssl.CERT_NONE
    return ctx.wrap_socket(socket.create_connection(('127.0.0.1',port),timeout=5),server_hostname='APSEODESK172')
def abort(client):
    fd=client.detach();raw=socket.socket(fileno=fd)
    raw.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('hh',1,0) if __import__('os').name=='nt' else struct.pack('ii',1,0));raw.close()
with tempfile.TemporaryDirectory(prefix='fo3-https-peer-') as tmp:
    for label,source in [('before',(S/'http_config.py').read_text('utf-8-sig')),('fixed',(O/'http_config.fixed.py').read_text('utf8'))]:
        log=Path(tmp)/(label+'.log');commits=[];entered=threading.Event();release=threading.Event();errors=[]
        H,Quiet=handler(source,log,commits,entered,release)
        class Server(http.server.ThreadingHTTPServer):
            daemon_threads=True
            def handle_error(self,request,address):
                import sys
                errors.append(type(sys.exception()).__name__)
        server=Server(('127.0.0.1',0),Quiet);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(S/'certs/server.pem'));server.socket=ctx.wrap_socket(server.socket,server_side=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();port=server.server_address[1]
        client=connect(port);client.sendall(b'POST /drop HTTP/1.0\r\nHost: APSEODESK172\r\nContent-Length: 2\r\n\r\n{}');assert entered.wait(5)
        abort(client);release.set()
        deadline=time.monotonic()+5
        while time.monotonic()<deadline and not errors and not log.exists():time.sleep(.02)
        assert len(commits)==1,'Aborted response must not replay or roll back the committed request'
        if label=='before':assert errors and errors[0] in ('SSLEOFError','ConnectionResetError','BrokenPipeError'),errors
        else:
            assert not errors,errors
            assert log.exists() and 'HTTP peer disconnected' in log.read_text('utf8')
        client=connect(port);client.sendall(b'GET /ok HTTP/1.0\r\nHost: APSEODESK172\r\n\r\n');data=b''
        while True:
            part=client.recv(8192)
            if not part:break
            data+=part
        client.close();assert b'200 OK' in data and b'"commits": 1' in data
        results.append(dict(case=label+' real TLS response abort',request_committed_once=True,unhandled_errors=list(errors),fresh_request_200=True,disconnect_logged=log.exists()))
        server.shutdown();server.server_close();thread.join(2)
        if label=='fixed':
            for exc in (ssl.SSLEOFError('eof'),ConnectionResetError('reset'),ConnectionAbortedError('aborted'),BrokenPipeError('pipe')):
                obj=H.__new__(H);obj.client_address=('127.0.0.1',1234)
                with unittest.mock.patch.object(http.server.BaseHTTPRequestHandler,'handle',side_effect=exc) as call:
                    obj.handle();assert obj.close_connection is True and call.call_count==1
            results.append(dict(case='known read/write disconnect types close connection exactly once',pass_check=True))
            for exc in (OSError('unexpected I/O failure'),ValueError('programming error'),ssl.SSLError('unrelated TLS failure')):
                obj=H.__new__(H);obj.client_address=('127.0.0.1',1234)
                with unittest.mock.patch.object(http.server.BaseHTTPRequestHandler,'handle',side_effect=exc):
                    try:obj.handle();raise AssertionError('Unexpected error was hidden')
                    except type(exc) as got:assert got is exc
            results.append(dict(case='unrelated OSError ValueError and non-EOF TLS errors still propagate',pass_check=True))
report=dict(status='HTTPS_PEER_DISCONNECT_REGRESSION_PASS',cases=results,production_ports_used=False,business_state_read_or_written=False)
(O/'test-results.json').write_text(json.dumps(report,indent=2),'utf8');print(json.dumps(report,indent=2))
