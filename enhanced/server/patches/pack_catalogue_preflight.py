"""Read-only hash/ancestry validation for the additive pack catalogue release."""
from pathlib import Path
import hashlib
import json


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def validate(server, client):
    server, client = Path(server).resolve(), Path(client).resolve()
    roots = {'server': server, 'client': client}
    manifest = server/'patches/pack-catalogue-release-manifest.json'
    receipt = read(server/'patches/pack-catalogue-release-installed.json')
    data = read(manifest)
    if receipt.get('status') != 'INSTALLED' or receipt.get('manifest_sha256') != sha(manifest):
        raise RuntimeError('Catalogue installation receipt mismatch')
    if data['parent_shop_manifest_sha256'] != sha(server/'patches/shop-release-manifest.json') or data['parent_roster_manifest_sha256'] != sha(server/'patches/roster-release-manifest.json'):
        raise RuntimeError('Catalogue ancestry changed; rebase the additive release')
    if data['state_shop_replaced'] is not False:
        raise RuntimeError('Unexpected catalogue asset migration')
    allowed = {('server', 'http_config.py'), ('server', 'shop_season_names.py'), ('server', 'pack_catalogue.py'),
               ('server', 'gamedata/pack_catalogue.json'), ('server', 'patches/pack_catalogue_preflight.py'),
               ('client', 'data/ui/teammanagementdraftpackscreen.big')}
    shop = read(server/'patches/shop-release-manifest.json')
    roster = read(server/'patches/roster-release-manifest.json')
    parents = {(r['root'], r['relative'].replace('\\', '/').casefold()): r['sha256']
               for r in shop['files']+shop['unchanged']+roster['files']}
    backup = Path(receipt['backup']).resolve()
    if not backup.is_relative_to(server/'backups'):
        raise RuntimeError('Catalogue backup must be inside server backups')
    replacements = {}
    for row in data['files']:
        root = roots[row['root']]
        rel = Path(row['relative'])
        if rel.is_absolute() or '..' in rel.parts:
            raise RuntimeError('Escaped catalogue target')
        target = (root/rel).resolve()
        pair = (row['root'], str(rel).replace('\\', '/').casefold())
        if pair not in allowed:
            raise RuntimeError('Out-of-scope catalogue target: '+str(rel))
        if pair in replacements or target == root or not target.is_relative_to(root):
            raise RuntimeError('Duplicate catalogue target')
        if str(rel).replace('\\', '/').casefold() in ('gamedata/state.json', 'gamedata/shop.json'):
            raise RuntimeError('Catalogue must not replace player assets/shop state')
        if not target.is_file() or sha(target) != row['sha256']:
            raise RuntimeError('Catalogue installed file differs: ' + str(rel))
        parent = row.get('parent_sha256')
        if pair in parents and parent != parents[pair]:
            raise RuntimeError('Catalogue parent guard differs: '+str(rel))
        if parent is not None and (not (backup/row['root']/rel).is_file() or sha(backup/row['root']/rel) != parent):
            raise RuntimeError('Catalogue parent backup differs: '+str(rel))
        replacements[pair] = row['sha256']
    if set(replacements) != allowed:
        raise RuntimeError('Incomplete catalogue release')
    return replacements
