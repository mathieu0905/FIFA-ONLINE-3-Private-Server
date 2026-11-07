"""Read-only additive bulk roster layer over the installed main XP30 release."""
from pathlib import Path
import hashlib, importlib.util, json, sys
sys.dont_write_bytecode = True
MANIFEST = 'patches/bulk-seasons-release-manifest.json'
RECEIPT = 'patches/bulk-seasons-release-installed.json'
SELF = 'patches/bulk_seasons_preflight.py'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeError('Duplicate bulk metadata key')
            result[key] = value
        return result
    return json.loads(Path(path).read_text('utf-8-sig'), object_pairs_hook=unique)


def parent(server, manifest):
    for relative, digest in manifest['parent_files'].items():
        if sha(server / relative) != digest:
            raise RuntimeError('Bulk parent source changed: ' + relative)
    receipt = read(server / 'patches/xp30-batch-release-installed.json')
    if {k: v for k, v in receipt.items() if k != 'native_status'} != manifest['parent_receipt_identity']:
        raise RuntimeError('Bulk XP parent installation identity changed')
    spec = importlib.util.spec_from_file_location('bulk_xp_parent', server / 'patches/xp30_batch_preflight.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _compose(server=None, client=None, manifest=None, installed=True):
    server = Path(server or Path(__file__).resolve().parent.parent).resolve()
    m = manifest or read(server / MANIFEST)
    client = Path(client or m['client_root']).resolve()
    if m.get('phase') != 'MAIN_BULK_SEASONS' or m.get('state_shop_replaced') is not False:
        raise RuntimeError('Wrong bulk release scope')
    xp = parent(server, m)
    composed = xp.compose_manifest(server, client)
    validator = xp.parent(server, xp.read(server / xp.MANIFEST))
    guards = validator.table(composed['guards'])
    rows = validator.table(m['files'])
    if set(rows) != {validator.canonical(e) for e in m['target_policy']}:
        raise RuntimeError('Bulk target whitelist changed')
    external = {validator.canonical(e): e['parent_sha256'] for e in m['files'] if validator.canonical(e) not in guards}
    validator.replace(guards, m['files'], external, set(rows))
    if installed:
        receipt = read(server / RECEIPT)
        if receipt.get('status') != 'INSTALLED_BULK_SEASONS' or receipt.get('manifest_sha256') != sha(server / MANIFEST) or receipt.get('release_id') != m['release_id']:
            raise RuntimeError('Bulk installation receipt mismatch')
        for name in (MANIFEST, RECEIPT):
            guards[('server', name.casefold())] = dict(root='server', relative=name, sha256=sha(server / name))
    composed['guards'] = list(guards.values())
    composed['ancestry'].append(dict(layer='bulk-seasons', release_id=m['release_id'], native_status='PENDING', registered_cards=504, state_shop_replaced=False))
    return composed, validator


def compose_manifest(server=None, client=None):
    return _compose(server, client)[0]


def preflight(server=None, client=None):
    server = Path(server or Path(__file__).resolve().parent.parent).resolve()
    m = read(server / MANIFEST)
    composed, validator = _compose(server, client, m)
    result = validator.verify_manifest(composed, server, client or m['client_root'])
    result['status'] = 'READ_ONLY_BULK_SEASONS_PREFLIGHT_PASS'
    result['registered_cards'] = 504
    return result


if __name__ == '__main__':
    print(json.dumps(preflight(), ensure_ascii=True, indent=2))
