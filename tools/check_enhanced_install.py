"""Read-only prerequisite audit; never start servers or alter game files/saves."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import threading
import types

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def placeholder(value):
    if isinstance(value, dict):
        return any(placeholder(v) for v in value.values())
    if isinstance(value, list):
        return any(placeholder(v) for v in value)
    return value == '__GENERATE_LOCALLY__'


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def database_status(path, tables):
    if not path.is_file():
        raise ValueError('Missing database: ' + str(path))
    # Never create a missing database or import the HTTP host and its hooks.
    con = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        if con.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('SQLite quick_check failed')
        names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = set(tables) - names
        if missing:
            raise ValueError('Missing tables: ' + ', '.join(sorted(missing)))
        return con
    except BaseException:
        con.close()
        raise


def audit(server, client, templates=None, hash_assets=False, expected_revision=None):
    server, client = server.resolve(), client.resolve()
    templates = templates or ROOT / 'enhanced/config-templates'
    findings = []

    def check(code, fn):
        try:
            detail = fn()
            findings.append(dict(code=code, passed=True, detail=detail or 'OK'))
        except Exception as exc:
            findings.append(dict(code=code, passed=False, detail=f'{type(exc).__name__}: {exc}'))

    def files(root, names):
        missing = [n for n in names if not (root / n).is_file()]
        if missing:
            raise ValueError('Missing: ' + ', '.join(missing[:10]) + (f' ({len(missing)} total)' if len(missing) > 10 else ''))
        return f'{len(names)} required files present'

    check('enhanced-source', lambda: files(server, ['http_config.py', 'admin.py', 'hot_update_runtime.py', 'product_packs.py', 'market_simulation.py', 'tools/player_import/check.py', 'tools/value_v11/selected-model.json.gz']))
    check('client-files', lambda: files(client, ['fifazf.exe', 'data/data_0.big', 'data/data_3.big', 'data/data_4.big', 'data/data_6.big']))
    check('tls-certificate', lambda: files(server, ['certs/server.pem']))

    def configs():
        names = ['shop.json' if p.name == 'shop.catalogue.json' else p.name for p in templates.glob('*.json*')]
        if not names:
            raise ValueError('Configuration template directory is missing or empty')
        files(server / 'gamedata', names)
        for name in names:
            if not name.endswith('.json'):
                continue
            value = read(server / 'gamedata' / name)
            if placeholder(value):
                raise ValueError(name + ': contains an uninitialized signing-key placeholder')
            if isinstance(value, dict) and isinstance(value.get('hash'), str):
                raw = json.dumps({k: v for k, v in value.items() if k != 'hash'}, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                if hashlib.sha256(raw).hexdigest() != value['hash']:
                    raise ValueError(name + ': configuration content hash mismatch')
            if name in ('pack_catalogue.json', 'product_packs.json'):
                if len(bytes.fromhex(value['token_key'])) != 32:
                    raise ValueError(name + ': signing key must be 32 random bytes')
        return f'{len(names)} configuration inputs present; keys and top-level content hashes checked'
    check('configs-and-keys', configs)

    def player_db():
        con = database_status(server / 'gamedata/fifadb.sqlite', ['players'])
        try:
            ids = {r[0] for r in con.execute('SELECT spid FROM players')}
            registry = read(server / 'gamedata/custom_rosters.json')
            required = {c['fo3_spid'] for c in registry.get('cards', []) if isinstance(c, dict) and isinstance(c.get('fo3_spid'), int) and c.get('enabled') is not False}
            missing = sorted(required - ids)
            if missing:
                raise ValueError(f'{len(missing)} registered custom cards are missing from SQLite; examples: {missing[:8]}. An original client extraction does not build custom seasons.')
            return f'{len(ids)} player rows; {len(required)} registered custom cards found. Native/model validation still required.'
        finally:
            con.close()
    check('player-database', player_db)

    def market_db():
        con = database_status(server / 'gamedata/npc-market-prices.sqlite', ['metadata', 'seeds', 'prices', 'price_events'])
        try:
            meta = dict(con.execute('SELECT key,value FROM metadata'))
            if meta.get('schema') != '1' or not meta.get('fair_revision'):
                raise ValueError('Missing expected fair-value initialization; copying a seed file does not initialize the database')
            source = Path(meta.get('fair_source_database', ''))
            if source.resolve() != (server / 'gamedata/fifadb.sqlite').resolve():
                raise ValueError('Market metadata points to a different player database; rebuild the fresh installation binding')
            return 'SQLite structure and local player-database binding present; full profile/economy validation still required'
        finally:
            con.close()
    check('market-database', market_db)

    def icons():
        asset_root = client / '_cache/games/fo3id/externalAssets/shop'
        expected = {}
        for name in ('shop_icon_manifest.json', 'all_item_icon_manifest.json'):
            for row in read(server / 'gamedata' / name)['items'].values():
                filename = row['filename']
                if Path(filename).name != filename or '/' in filename or '\\' in filename:
                    raise ValueError('Invalid icon filename in manifest')
                expected[filename] = row['sha256']
        missing = [name for name in expected if not (asset_root / name).is_file()]
        if missing:
            raise ValueError(f'{len(missing)} required generated/shop icons missing; examples: {missing[:5]}')
        if hash_assets:
            changed = [name for name, digest in expected.items() if checksum(asset_root / name) != digest]
            if changed:
                raise ValueError(f'{len(changed)} icon hashes differ; examples: {changed[:5]}')
        return f'{len(expected)} icon files present' + ('; hashes checked' if hash_assets else '; hashes not checked (use --hash-assets)')
    check('client-shop-icons', icons)

    def release():
        play = (server / 'play-local.bat').read_text('utf8')
        import re
        matches = re.findall(r'patches[\\/]([a-z0-9_]+_preflight\.py)', play)
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous local release entry in play-local.bat')
        helper = server / 'patches' / matches[0]
        constants = {}
        for node in ast.parse(helper.read_text('utf8')).body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        constants[target.id] = node.value.value
        paths = []
        for name in ('MANIFEST', 'RECEIPT'):
            path = (server / constants[name]).resolve()
            if not path.is_relative_to(server) or path == server:
                raise ValueError('Release metadata path escapes server')
            paths.append(path)
        manifest, receipt = map(read, paths)
        if receipt.get('manifest_sha256') != checksum(paths[0]) or receipt.get('revision') != manifest.get('revision'):
            raise ValueError('Local publication receipt mismatch')
        for relative in ('play-local.bat', helper.relative_to(server).as_posix()):
            guard = next((g for g in manifest['guards'] if g['root'] == 'server' and g['relative'].replace('\\', '/') == relative), None)
            if not guard or guard['sha256'] != checksum(server / relative):
                raise ValueError('Release entry is not bound by local guards: ' + relative)
        return 'Local release entry and receipt present; complete preflight must still be run before launch'
    check('local-release-chain', release)

    def hot_package():
        path = server / 'hot_update_runtime.py'
        if path.read_text('utf8') != (ROOT / 'enhanced/server/hot_update_runtime.py').read_text('utf8'):
            raise ValueError('Runtime differs from this source distribution; review its changes before loading it for inspection')
        spec = importlib.util.spec_from_file_location('_installation_hot_runtime', path)
        runtime = importlib.util.module_from_spec(spec)
        prior = sys.dont_write_bytecode
        try:
            sys.dont_write_bytecode = True
            spec.loader.exec_module(runtime)  # definitions only, never HTTP host
            manager = runtime.Manager(types.SimpleNamespace(STATE_LOCK=threading.RLock()), server)
            revision, handlers = manager.prepare(read(server / 'hot_updates/active.json'))
            reference = read(ROOT / 'enhanced/active-business-source.json')
            if revision != (expected_revision or reference['revision']) or set(handlers) != {r['path'] for r in reference['routes']}:
                raise ValueError('Current package does not match the published enhanced business revision/routes')
            return f'{revision}: {len(handlers)} guarded routes load; this does not prove runtime activation'
        finally:
            sys.dont_write_bytecode = prior
    check('active-business-proof', hot_package)
    check('native-import-certificate-present', lambda: files(server, ['gamedata/player-import-validation.json']))

    blocked = [x['code'] for x in findings if not x['passed']]
    return dict(status='NEEDS_PREPARATION' if blocked else 'PREREQUISITES_PRESENT_NATIVE_PENDING',
                checks=findings, blocked=blocked, starts_services=False,
                writes_game_files=False, validates_native_game=False,
                note='This is a read-only prerequisite audit, not a full installation certificate. Run the local composed preflight and player_import --full, then verify runtime and native gameplay.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', type=Path, required=True)
    parser.add_argument('--client', type=Path, required=True)
    parser.add_argument('--hash-assets', action='store_true')
    parser.add_argument('--expected-revision', help='Your own unique revision for this complete seven-route business package')
    args = parser.parse_args()
    result = audit(args.server, args.client, hash_assets=args.hash_assets, expected_revision=args.expected_revision)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(2 if result['blocked'] else 0)
