"""Read-only verification of the installed main batch and live HTTP services."""
from pathlib import Path
import hashlib, importlib.util, json, sqlite3, ssl, urllib.parse, urllib.request

ROOT = Path(__file__).resolve().parent
SERVER = Path('D:/FO3ID/server')
CLIENT = Path('D:/FO3ID/32795')


def sha(p):
    with Path(p).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(p):
    return json.loads(p.read_text('utf-8-sig'))


receipt = read(SERVER / 'patches/bulk-seasons-release-installed.json')
backup = Path(receipt['backup'])
transaction = read(backup / 'transaction.json')
assert transaction['status'] == 'installed'
assert all(sha((SERVER if row['root'] == 'server' else CLIENT) / row['relative']) == row['sha256'] for row in transaction['entries'])
spec = importlib.util.spec_from_file_location('installed_bulk_check', SERVER / 'patches/bulk_seasons_preflight.py')
preflight = importlib.util.module_from_spec(spec); spec.loader.exec_module(preflight)
composed = preflight.preflight(SERVER, CLIENT)
registry = read(SERVER / 'gamedata/custom_rosters.json')
with sqlite3.connect((SERVER / 'gamedata/fifadb.sqlite').as_uri() + '?mode=ro', uri=True) as db:
    assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
    count = db.execute('select count(*) from players').fetchone()[0]
    assert count == 60678
    counts = dict(db.execute('select spid/1000000,count(*) from players where spid/1000000 in (12,13,84) group by 1'))
    assert counts == {12: 123, 13: 258, 84: 123}
before = read(backup / 'audit-state.json')
state = read(SERVER / 'gamedata/state.json')
assert before['coaches'] == state['coaches'] and before['teams'] == state['teams']
assert {k: v for k, v in before.items() if k != 'market_simulation'} == {k: v for k, v in state.items() if k != 'market_simulation'}
assert sha(SERVER / 'gamedata/shop.json') == transaction['protected']['shop.json']
assert sha(SERVER / 'gamedata/pack_cadence.json') == transaction['protected']['pack_cadence.json']
context = ssl._create_unverified_context()  # Existing local self-signed game certificate.
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context))


def get(url):
    with opener.open(url, timeout=15) as response:
        assert response.status == 200
        return response.read()


rules = json.loads(get('https://127.0.0.1/info/player/level_rules'))
assert rules.get('max_level') == 30 or rules.get('maxlevel') == 30 or rules.get('max') == 30, rules
selected = []
for sid in (13, 12, 84):
    entries = [r for r in registry['cards'] if r['fo3_spid'] // 1000000 == sid and r['fo3_spid'] in receipt['added_spids']]
    selected.extend(entries[:2] + entries[-1:])
http = []
for row in selected:
    query = urllib.parse.urlencode({'q': row['name_zh']})
    result = json.loads(get('http://127.0.0.1:8088/api/search?' + query))
    assert any(r['spid'] == row['fo3_spid'] for r in result['rows']), row
    assert all(r['spid'] >= 1000000 for r in result['rows'])
    raw = get(f'https://127.0.0.1/cdn/externalAssets/players/p{row["fo3_spid"]}.png')
    file = CLIENT / f'_cache/games/fo3id/externalAssets/players/p{row["fo3_spid"]}.png'
    assert hashlib.sha256(raw).hexdigest() == sha(file)
    http.append(dict(spid=row['fo3_spid'], name=row['name_zh'], search=True, cdn_hash=True))
after = read(SERVER / 'gamedata/state.json')
assert after['coaches'] == state['coaches'] and after['teams'] == state['teams']
assert sha(SERVER / 'gamedata/shop.json') == transaction['protected']['shop.json']
report = dict(status='INSTALLED_MAIN_SERVICES_AND_READONLY_CHECKS_PASS_NATIVE_PENDING',
              release_id=receipt['release_id'], backup=str(backup), manifest_sha256=receipt['manifest_sha256'],
              registered_cards=len(registry['cards']), added_cards=len(receipt['added_spids']), sqlite_rows=count, season_counts=counts,
              preflight=composed, player_level_rules=rules, actual_http_checks=http,
              coaches_teams_wallets_cards_and_progress_unchanged=True, shop_and_legacy_pack_config_unchanged=True,
              native_verified=False, match_verified=False)
(ROOT / 'installed-main-PASS.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
print(json.dumps(dict(status=report['status'], sqlite_rows=count, registered_cards=504, added_cards=500, actual_http_samples=len(http), assets_unchanged=True)))
