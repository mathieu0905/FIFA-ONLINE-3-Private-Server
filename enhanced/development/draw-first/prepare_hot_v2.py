"""Prepare the dynamic-route prerequisite without touching the running server."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');O=R/'hot-v2';O.mkdir(exist_ok=True)
src=(S/'hot_update_runtime.py').read_text('utf8').replace('ABI = 1','ABI = 2')
anchor="def compile_handlers(source, filename, routes):"
assert src.count(anchor)==1
src=src.replace(anchor,"""TEMPLATES = {
    '/item/{item_id}/use': (re.compile(r'/item/(?P<item_id>\\w+)/use'),),
    '/item/depottoitem/{item_id}': (re.compile(r'/item/depottoitem/(?P<item_id>\\w+)'),),
    '/bag/{bag_id}/unpack': (re.compile(r'/bag/(?P<bag_id>\\w+)/unpack'),),
}

class RequestHost:
    __slots__ = ('_host', 'hot_path_params')
    def __init__(self, host, params):
        object.__setattr__(self, '_host', host)
        object.__setattr__(self, 'hot_path_params', types.MappingProxyType(params))
    def __getattr__(self, name):
        return getattr(self._host, name)
    def __setattr__(self, name, value):
        raise AttributeError('Request host attributes are read-only')

def compile_handlers(source, filename, routes, allow_templates=False):""")
anchor="        function = namespace.get(name)"
src=src.replace(anchor,"""        if ('{' in path or '}' in path) and (not allow_templates or path not in TEMPLATES):
            raise ValueError('Unsupported dynamic business route')
"""+anchor)
anchor="        return self._handlers.get(path)"
src=src.replace(anchor,"""        exact = self._handlers.get(path)
        if exact is not None:
            return exact
        for template, patterns in TEMPLATES.items():
            fn = self._handlers.get(template)
            if fn is not None:
                match = patterns[0].fullmatch(path)
                if match is not None:
                    # Per-request immutable captures; no host globals or thread locals.
                    return fn(match.groupdict())
        return None""")
src=src.replace("if descriptor['abi'] != ABI or descriptor.get('schema') != 1:","if descriptor['abi'] not in (1, ABI) or descriptor.get('schema') != 1:")
src=src.replace("handlers = compile_handlers(source, str(self.server / relative), descriptor['routes'])", "handlers = compile_handlers(source, str(self.server / relative), descriptor['routes'], allow_templates=descriptor['abi']==2)")
anchor="        bound = {path: (lambda query, body, fn=fn: fn(self.host, query, body)) for path, fn in handlers.items()}"
src=src.replace(anchor,"""        bound = {}
        for path, fn in handlers.items():
            if path in TEMPLATES:
                bound[path] = lambda params, fn=fn: (lambda query, body: fn(RequestHost(self.host, params), query, body))
            else:
                bound[path] = lambda query, body, fn=fn: fn(self.host, query, body)""")
compile(src,'hot_update_runtime.py','exec');(O/'hot_update_runtime.py').write_text(src,encoding='utf8')
publish=(S/'hot_update_publish.py').read_text('utf8').replace('compile_handlers(source, str(args.source), routes)','compile_handlers(source, str(args.source), routes, allow_templates=True)')
compile(publish,'hot_update_publish.py','exec');(O/'hot_update_publish.py').write_text(publish,encoding='utf8')
baseline={str(S/n):hashlib.sha256((S/n).read_bytes()).hexdigest() for n in ('hot_update_runtime.py','hot_update_publish.py')}
(O/'baseline.json').write_text(json.dumps(baseline,indent=2),encoding='utf8')
print(json.dumps(dict(status='PREPARED_ONLY',abi=2,dynamic_routes=3,formal_files_written=False)))
