"""Versioned business handlers; never reload the host, persistence or TCP service.

Only reviewed, release-guarded Python function definitions are loaded. This is
an operator deployment mechanism, not a sandbox for untrusted Python code.
"""
import ast
import hashlib
import inspect
import json
import logging
from pathlib import Path
import re
import threading
import types

ABI = 1
PREFIXES = ('/shop/', '/bag/', '/items/', '/item/', '/events/', '/hot/')
EXACT = {'/bag', '/events', '/specifictarget', '/monthlypack'}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def bounded(path, maximum):
    with path.open('rb') as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError('Hot update exceeds size limit')
    return data

def within(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError('Hot update path escapes server')
    return path

def compile_handlers(source, filename, routes):
    tree = ast.parse(source, filename=filename)
    # Loading a generation must not run imports, decorators, defaults or install hooks.
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        if not isinstance(node, ast.FunctionDef):
            raise ValueError('Only function definitions are permitted at module level')
        args = node.args
        if node.decorator_list or node.returns or args.defaults or args.kw_defaults or node.type_params:
            raise ValueError('Decorators, annotations, defaults and type parameters are not supported')
        if any(a.annotation for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)):
            raise ValueError('Annotations are not supported')
    namespace = {'__name__': 'fo3_hot_business', '__builtins__': __builtins__}
    exec(compile(tree, filename, 'exec'), namespace)
    handlers = {}
    for route in routes:
        path, name = route['path'], route['function']
        if path not in EXACT and not path.startswith(PREFIXES):
            raise ValueError('Route belongs to a protected core or unsupported subsystem: ' + path)
        if any(c in path for c in ('?', '#', '\\', '\x00')) or path in handlers:
            raise ValueError('Invalid or duplicate hot route')
        function = namespace.get(name)
        if not isinstance(function, types.FunctionType):
            raise ValueError('Missing business function: ' + name)
        params = list(inspect.signature(function).parameters.values())
        if len(params) != 3 or any(p.kind not in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) for p in params):
            raise ValueError('Business handler must accept (host, query, body)')
        handlers[path] = function
    if not handlers:
        raise ValueError('No business handlers supplied')
    return handlers

class Manager:
    def __init__(self, host, server):
        self.host = host
        self.server = Path(server).resolve()
        self.active_path = self.server / 'hot_updates/active.json'
        self._handlers = {}
        self.revision = 'bootstrap'
        self.error = None
        self._attempt = None
        self._poll_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None

    def status(self):
        with self.host.STATE_LOCK:
            return dict(abi=ABI, revision=self.revision, routes=sorted(self._handlers),
                        error=self.error, watcher_running=bool(self._thread and self._thread.is_alive()))

    def handler(self, path):
        # Host calls this inside the same STATE_LOCK used for the entire request.
        return self._handlers.get(path)

    def prepare(self, descriptor):
        if descriptor['abi'] != ABI or descriptor.get('schema') != 1:
            raise ValueError('Unsupported hot update ABI')
        revision = descriptor['revision']
        if not isinstance(revision, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', revision):
            raise ValueError('Invalid hot revision')
        relative = 'hot_updates/revisions/' + revision + '/business.py'
        if descriptor['code'] != relative:
            raise ValueError('Code must be an immutable versioned business payload')
        source = bounded(within(self.server, relative), 131072)
        if digest(source) != descriptor['sha256']:
            raise ValueError('Business payload hash mismatch')
        proof = descriptor['release']
        manifest_bytes = bounded(within(self.server, proof['manifest']), 8 * 1024 * 1024)
        receipt_bytes = bounded(within(self.server, proof['receipt']), 65536)
        if digest(manifest_bytes) != proof['manifest_sha256'] or digest(receipt_bytes) != proof['receipt_sha256']:
            raise ValueError('Publication proof changed')
        manifest, receipt = json.loads(manifest_bytes), json.loads(receipt_bytes)
        if receipt['manifest_sha256'] != digest(manifest_bytes) or receipt['revision'] != manifest['revision']:
            raise ValueError('Publication receipt mismatch')
        if manifest.get('state_shop_replaced') is not False:
            raise ValueError('Invalid publication scope')
        if not any(g['root'] == 'server' and g['relative'] == relative and g['sha256'] == descriptor['sha256'] for g in manifest['guards']):
            raise ValueError('Business payload is not release guarded')
        if descriptor.get('disabled') is True:
            if descriptor['routes']:
                raise ValueError('Disabled generation must have no routes')
            handlers = {}
        else:
            handlers = compile_handlers(source, str(self.server / relative), descriptor['routes'])
        # Freeze the function selection for a request. Never retry a failed mutation
        # through an older handler: it might have already committed its transaction.
        bound = {path: (lambda query, body, fn=fn: fn(self.host, query, body)) for path, fn in handlers.items()}
        return revision, bound

    def poll(self):
        if not self._poll_lock.acquire(blocking=False):
            return False
        try:
            if not self.active_path.exists():
                return False
            raw = bounded(self.active_path, 65536)
            token = digest(raw)
            if token == self._attempt:
                return False
            try:
                descriptor = json.loads(raw)
                revision, handlers = self.prepare(descriptor)  # compile outside the game transaction lock
                with self.host.STATE_LOCK:
                    if self.revision != 'bootstrap' and descriptor['expected_revision'] != self.revision:
                        raise ValueError('Stale runtime revision; rebase hot update')
                    self._handlers = handlers
                    self.revision = revision
                    self.error = None
                self._attempt = token
                return True
            except Exception as exc:
                self._attempt = token
                self.error = type(exc).__name__ + ': ' + str(exc)
                logging.getLogger(__name__).warning('Hot update rejected; previous generation retained: %s', self.error)
                return False
        finally:
            self._poll_lock.release()

    def _watch(self):
        while not self._stop.wait(0.5):
            try:
                # Never read the publication halfway through a multi-file transaction.
                if not (self.server / '.shop-release.lock').exists():
                    self.poll()
            except Exception:
                logging.getLogger(__name__).exception('Hot update watcher failed; old generation retained')

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._watch, name='business-hot-update', daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)

def install(host):
    manager = Manager(host, host.HERE)
    host.hot_update_manager = manager
    import admin
    admin.READ_ONLY.add('hot_update_status')
    admin.API['hot_update_status'] = lambda *args, **kwargs: manager.status()
    return manager
