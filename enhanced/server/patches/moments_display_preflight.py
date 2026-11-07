"""Sealed season84 display/affiliation child of the current main release."""
from pathlib import Path
import hashlib, importlib.util, json, sys
sys.dont_write_bytecode = True
MANIFEST = 'patches/moments-display-release-manifest.json'
RECEIPT = 'patches/moments-display-release-installed.json'
SELF = 'patches/moments_display_preflight.py'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def parent(server, m):
    for relative, digest in m['parent_files'].items():
        if sha(server / relative) != digest:
            raise RuntimeError('Moments display parent changed: ' + relative)
    spec = importlib.util.spec_from_file_location('moments_display_parent', server / m['parent_preflight'])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def compose_parent(p, server, client):
    if hasattr(p, '_compose'):
        import inspect
        if len(inspect.signature(p._compose).parameters) >= 3:
            return p._compose(server, client, p.read(server / p.MANIFEST))
        return p._compose(server, client)
    # This installed narrow parent exposes preflight only. Reproduce its complete,
    # hash-pinned composition without editing historical manifests or scripts.
    if p.MANIFEST != 'patches/fc-retirement-release-manifest.json':
        raise RuntimeError('Parent has no reviewed composition API')
    cfg = p.read(server / p.MANIFEST)
    for relative, digest in cfg['parent_files'].items():
        if p.sha(server / relative) != digest:
            raise RuntimeError('FC retirement ancestor changed: ' + relative)
    ancestor = 'patches/player_value_preflight.py'
    if ancestor not in cfg['parent_files']:
        raise RuntimeError('Unpinned player-value ancestor')
    spec = importlib.util.spec_from_file_location('moments_fc_value_parent', server / ancestor)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    composed, validator = value._compose(server, client)
    guards = validator.table(composed['guards'])
    if set(validator.table(cfg['files'])) != p.ALLOWED:
        raise RuntimeError('FC retirement whitelist changed')
    validator.replace(guards, cfg['files'], {('server', p.SELF): None}, p.ALLOWED)
    receipt = p.read(server / p.RECEIPT)
    if receipt.get('status') != 'INSTALLED_FC13_RETIREMENT' or receipt.get('manifest_sha256') != p.sha(server / p.MANIFEST):
        raise RuntimeError('FC retirement receipt changed')
    for relative in (p.MANIFEST, p.RECEIPT):
        guards[('server', relative.casefold())] = dict(root='server', relative=relative, sha256=p.sha(server / relative))
    registry = p.read(server / 'gamedata/custom_rosters.json')
    if 13028130 in {r['fo3_spid'] for r in registry['cards']} or len(next(s for s in registry['seasons'] if s['id'] == 13)['cards']) != 257:
        raise RuntimeError('FC retirement registry contract changed')
    composed['guards'] = list(guards.values())
    composed['ancestry'].append(dict(layer='fc13-retirement', preserved=True))
    return composed, validator


def _compose(server=None, client=None, m=None, installed=True):
    server = Path(server or Path(__file__).resolve().parent.parent).resolve()
    m = m or read(server / MANIFEST)
    client = Path(client or m['client_root']).resolve()
    if m.get('phase') != 'MOMENTS_DISPLAY_FIX' or m.get('state_shop_replaced') is not False:
        raise RuntimeError('Incorrect moments display scope')
    p = parent(server, m)
    composed, validator = compose_parent(p, server, client)
    guards = validator.table(composed['guards'])
    rows = validator.table(m['files'])
    if set(rows) != {validator.canonical(e) for e in m['target_policy']}:
        raise RuntimeError('Moments display target set changed')
    external = {validator.canonical(e): e['parent_sha256'] for e in m['files'] if validator.canonical(e) not in guards}
    validator.replace(guards, m['files'], external, set(rows))
    if installed:
        receipt = read(server / RECEIPT)
        if receipt.get('status') != 'INSTALLED_MOMENTS_DISPLAY_FIX' or receipt.get('manifest_sha256') != sha(server / MANIFEST) or receipt.get('release_id') != m['release_id']:
            raise RuntimeError('Moments display receipt mismatch')
        for name in (MANIFEST, RECEIPT):
            guards[('server', name.casefold())] = dict(root='server', relative=name, sha256=sha(server / name))
    composed['guards'] = list(guards.values())
    composed['ancestry'].append(dict(layer='moments-display', release_id=m['release_id'], affiliation='传奇时刻', season_id=84, native_status='PENDING'))
    return composed, validator


def compose_manifest(server=None, client=None):
    return _compose(server, client)[0]


def preflight(server=None, client=None):
    server = Path(server or Path(__file__).resolve().parent.parent).resolve()
    m = read(server / MANIFEST)
    composed, validator = _compose(server, client, m)
    result = validator.verify_manifest(composed, server, client or m['client_root'])
    result['status'] = 'READ_ONLY_MOMENTS_DISPLAY_PREFLIGHT_PASS'
    return result


if __name__ == '__main__':
    print(json.dumps(preflight(), ensure_ascii=True, indent=2))
