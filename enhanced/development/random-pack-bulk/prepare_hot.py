"""Rebase the one replaced handler onto every currently active business route."""
from pathlib import Path
import ast, hashlib, json, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SERVER = Path(r'D:\FO3ID\server')
sys.path.insert(0, str(SERVER))
from hot_update_runtime import compile_handlers

def main():
    descriptor = json.loads((SERVER/'hot_updates/active.json').read_text('utf8'))
    source = (SERVER/descriptor['code']).read_bytes()
    assert hashlib.sha256(source).hexdigest() == descriptor['sha256']
    lines = source.decode('utf8').splitlines(keepends=True)
    route = next(r for r in descriptor['routes'] if r['path'] == '/item/{item_id}/use')
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == route['function'])
    assert route['function'] == 'open_pack'
    assert not {'bulk_open', 'bulk_draw'} & {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    new = ''.join(lines[:node.lineno-1] + lines[node.end_lineno:]) + '\n' + (ROOT/'bulk_business.py').read_text('utf8')
    compile_handlers(new.encode(), 'merged_business.py', descriptor['routes'], allow_templates=True)
    (ROOT/'merged_business.py').write_text(new, encoding='utf8')
    proof = dict(expected_revision=descriptor['revision'], routes=descriptor['routes'],
                 parent_code=descriptor['code'], parent_sha256=descriptor['sha256'],
                 bulk_sha256=hashlib.sha256((ROOT/'bulk_business.py').read_bytes()).hexdigest(),
                 merged_sha256=hashlib.sha256(new.encode()).hexdigest())
    (ROOT/'hot-plan.json').write_text(json.dumps(proof, indent=2), encoding='utf8')
    print(json.dumps(proof))

if __name__ == '__main__': main()
