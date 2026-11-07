from pathlib import Path
import ast,hashlib,json,re
O=Path(__file__).parent;S=Path('D:/FO3ID/server')
INSERT='''    def handle(self):
        try:
            super().handle()
        except (ssl.SSLEOFError, ConnectionResetError, ConnectionAbortedError,
                BrokenPipeError) as exc:
            # The peer abandoned this request. Never replay a completed mutation,
            # send a second response, or treat a single disconnect as server failure.
            self.close_connection = True
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%H:%M:%S')} HTTP peer disconnected "
                        f"({type(exc).__name__}) from {self.client_address[0]}\\n")

'''
def build(source):
    hits=list(re.finditer(r'(?m)^class H\(http\.server\.BaseHTTPRequestHandler\):\r?\n',source));assert len(hits)==1
    needle=hits[0].group();newline='\r\n' if needle.endswith('\r\n') else '\n'
    h=next(x for x in ast.parse(source).body if isinstance(x,ast.ClassDef) and x.name=='H')
    assert not any(isinstance(x,ast.FunctionDef) and x.name=='handle' for x in h.body),'Handler already changed; rebase'
    result=source.replace(needle,needle+INSERT.replace('\n',newline))
    compile(result,'http_config.py','exec');return result
if __name__=='__main__':
    raw=(S/'http_config.py').read_bytes();source=raw.decode('utf-8-sig');updated=build(source)
    (O/'http_config.fixed.py').write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+updated.encode('utf8'))
    (O/'source-binding.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(raw).hexdigest(),fixed_sha256=hashlib.sha256(updated.encode()).hexdigest(),change='H.handle known-peer-disconnect boundary only'),indent=2),'utf8')
    print('Built narrow HTTP peer-disconnect fix')
