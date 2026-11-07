"""Read-only child of the installed currency layer for the market worker."""
from pathlib import Path
import hashlib, importlib.util, json, sys
sys.dont_write_bytecode = True
MANIFEST = 'patches/market-background-release-manifest.json'
RECEIPT = 'patches/market-background-release-installed.json'
SELF = 'patches/market_background_preflight.py'
PARENT = 'patches/compact_currency_preflight.py'
ALLOWED = {('server', n) for n in ('market_simulation.py', 'http_config.py', 'play-local.bat', SELF)}
PARENT_FILES = {PARENT, 'patches/compact-currency-release-manifest.json',
                'patches/compact-currency-release-installed.json'}

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read(p):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise RuntimeError('Duplicate market metadata key: ' + k)
            result[k] = v
        return result
    return json.loads(Path(p).read_text('utf-8-sig'), object_pairs_hook=unique)

def _compose(server, client, m=None):
    server = Path(server).resolve()
    m = m or read(server / MANIFEST)
    if m.get('phase') != 'MARKET_BACKGROUND_WORKER' or m.get('state_shop_replaced') is not False:
        raise RuntimeError('Unexpected market worker scope')
    if set(m['parent_files']) != PARENT_FILES:
        raise RuntimeError('Wrong market worker parent set')
    for name, digest in m['parent_files'].items():
        if sha(server / name) != digest:
            raise RuntimeError('Market worker parent changed: ' + name)
    spec = importlib.util.spec_from_file_location('market_worker_parent', server / PARENT)
    parent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parent)
    composed, verifier = parent._compose(server, client)
    guards = verifier.table(composed['guards'])
    verifier.replace(guards, m['files'], {('server', SELF): None}, ALLOWED)
    receipt = read(server / RECEIPT)
    if (receipt.get('status') != 'INSTALLED_MARKET_BACKGROUND'
            or receipt.get('release_id') != m['release_id']
            or receipt.get('manifest_sha256') != sha(server / MANIFEST)):
        raise RuntimeError('Market worker receipt mismatch')
    for name in (MANIFEST, RECEIPT):
        guards[('server', name)] = dict(root='server', relative=name, sha256=sha(server / name))
    composed['guards'] = list(guards.values())
    composed['ancestry'].append(dict(layer='market-background', native_status='NOT_VERIFIED'))
    return composed, verifier

def compose_manifest(server=None, client=None):
    server = Path(server or Path(__file__).resolve().parent.parent)
    m = read(server / MANIFEST)
    return _compose(server, client or m['client_root'], m)[0]

def preflight(server=None, client=None):
    server = Path(server or Path(__file__).resolve().parent.parent)
    m = read(server / MANIFEST)
    composed, verifier = _compose(server, client or m['client_root'], m)
    result = verifier.verify_manifest(composed, server, client or m['client_root'])
    result['status'] = 'READ_ONLY_MARKET_BACKGROUND_PASS'
    return result

if __name__ == '__main__':
    print(json.dumps(preflight(), ensure_ascii=True, indent=2))
