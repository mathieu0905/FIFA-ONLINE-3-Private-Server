"""Isolated real pipe/HTTP reproduction; never imports game handlers or state."""
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

CHILD = r'''
import http.server, pathlib, sys
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        for i in range(1500):
            print('request-log-%04d-' % i + 'x' * 300, flush=True)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'coach-list-ok')
    def log_message(self, *args): pass
s = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
pathlib.Path(sys.argv[1]).write_text(str(s.server_port))
s.serve_forever()
'''


def check(source):
    spec = importlib.util.spec_from_file_location('launcher_fixture', source)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    original_stdout = sys.stdout
    blocked = threading.Event()
    entered = threading.Event()

    class BlockedConsole:
        def write(self, text):
            entered.set()
            blocked.wait(15)
        def flush(self): pass

    with tempfile.TemporaryDirectory(prefix='fo3-log-test-') as tmp:
        mod.HERE = tmp
        portfile = pathlib.Path(tmp, 'port')
        child = subprocess.Popen([sys.executable, '-u', '-c', CHILD, str(portfile)],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, bufsize=1)
        pump = threading.Thread(target=mod.pump, args=('fixture', child), daemon=True)
        mirror = None
        try:
            deadline = time.monotonic() + 5
            while not portfile.exists() and time.monotonic() < deadline:
                time.sleep(.02)
            port = int(portfile.read_text())
            sys.stdout = BlockedConsole()
            if hasattr(mod, 'console_worker'):
                mirror = threading.Thread(target=mod.console_worker, daemon=True)
                mirror.start()
            pump.start()
            started = time.monotonic()
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/coaches', timeout=3) as r:
                    ok = r.read() == b'coach-list-ok'
            except TimeoutError:
                ok = False
            elapsed = time.monotonic() - started
            assert entered.is_set(), 'console fault was not exercised'
            count = None
            bounded = None
            if ok:
                log = pathlib.Path(tmp, 'captures', 'fixture-service.log').read_text()
                count = log.count('request-log-')
                assert count == 1500, count
                bounded = mod.CONSOLE_QUEUE.qsize() <= 256
                assert bounded
            return {'source': str(source), 'http_ok': ok, 'seconds': round(elapsed, 3),
                    'file_log_lines': count, 'queue_bounded': bounded}
        finally:
            child.terminate()
            child.wait(timeout=5)
            blocked.set()
            pump.join(timeout=5)
            if mirror:
                mod.CONSOLE_QUEUE.join()
            sys.stdout = original_stdout


if __name__ == '__main__':
    here = pathlib.Path(__file__).parent
    results = [check(here / 'start_all.before.py'), check(pathlib.Path('D:/FO3ID/server/start_all.py'))]
    assert not results[0]['http_ok'] and results[1]['http_ok'], results
    (here / 'backpressure-result.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))
