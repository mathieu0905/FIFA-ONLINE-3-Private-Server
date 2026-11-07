"""Exercise the actual copied FO3 backend with external writes and binds forbidden."""
from pathlib import Path
import argparse, ast, copy, hashlib, json, os, sqlite3, sys, time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--server', required=True, type=Path)
args = parser.parse_args()
server = args.server.resolve()
assert server.is_relative_to(ROOT / 'private-servers')
prepared = json.loads((server / 'prepare-report.json').read_text('utf-8'))
candidate = Path(prepared['candidate'])
manifest = json.loads((candidate / 'manifest.json').read_text('utf-8'))
registry = json.loads((server / 'gamedata/custom_rosters.json').read_text('utf-8'))
events = []


def guard(path):
    if isinstance(path, (str, bytes, Path)) and not Path(os.fsdecode(path)).resolve().is_relative_to(server):
        raise PermissionError('Bulk QA blocked external write/DB: ' + str(path))


def audit(event, values):
    if event in ('socket.bind', 'subprocess.Popen'):
        raise PermissionError('Bulk QA forbids service/process start')
    if event == 'sqlite3.connect' and str(values[0]) != ':memory:':
        value = str(values[0])
        if value.startswith('file:'):
            from urllib.parse import unquote, urlparse
            value = unquote(urlparse(value).path).lstrip('/')
        guard(value)
    if event == 'open':
        path, mode, flags = values
        if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
            guard(path)
            events.append(str(path))
    elif event in ('os.remove', 'os.rmdir', 'os.mkdir'):
        guard(values[0])
    elif event in ('os.rename', 'os.replace'):
        guard(values[0]); guard(values[1])


sys.addaudithook(audit)
os.chdir(server)
sys.path.insert(0, str(server))
sys.argv = ['http_config.py']
os.environ.update(FO3_ADMIN_PORT='0', FO3_LANGUAGE='chi', FO3_MAX_GRADE='20', FO3_GAME='D:/FO3ID/32795')
import http_config as h
import admin

assert Path(h.HERE).resolve() == server
assert Path(h.gen_teams.DB).resolve() == server / 'gamedata/fifadb.sqlite'
assert h.MAX_GRADE == 20 and h.PLAYER_MAX_LEVEL in (23, 30)
verified_levels = tuple(sorted({1, 20, 23, h.PLAYER_MAX_LEVEL}))
assert not getattr(h, '_breakthrough_balance_installed', False), 'This batch uses the current formal price profile only'
with sqlite3.connect(h.gen_teams.DB) as db:
    assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
    assert db.execute('select count(*) from players').fetchone()[0] == manifest['rows']
    db.row_factory = sqlite3.Row
    names = {r['fo3_spid']: r['name_zh'] for r in registry['cards']}
    wanted = {r['fo3_spid'] for r in registry['cards']}
    market = set(h.market_spids())
    assert wanted <= market
    queries = []
    for index, row in enumerate(registry['cards']):
        result = admin.API['search']({'q': row['name_zh']})
        assert all(r['spid'] >= 1000000 for r in result['rows'])
        # Long common surnames can yield over 60 old cards: use the exact English name as a fallback.
        found = any(r['spid'] == row['fo3_spid'] for r in result['rows'])
        if not found and row.get('name_en'):
            result = admin.API['search']({'q': row['name_en']})
            found = any(r['spid'] == row['fo3_spid'] for r in result['rows'])
        assert found, ('unsearchable_registered_card', row['fo3_spid'], row['name_zh'])
        queries.append(row['fo3_spid'])
        if (index + 1) % 100 == 0:
            print('searches', index + 1, flush=True)
    # Every supported reinforcement price is finite, integral and inside signed 64-bit.
    prices = []
    for spid in sorted(wanted):
        values = [h.card_price(spid, grade) for grade in range(1, 21)]
        assert all(isinstance(v, int) and 0 < v <= 2**63 - 1 for v in values), (spid, values)
        assert values == sorted(values)
        prices.append(dict(spid=spid, grade1=values[0], grade20=values[-1]))
    targets = []
    for entry in registry['cards']:
        spid = entry['fo3_spid']
        if spid // 1000000 != 84:
            continue
        original = dict(db.execute('select * from players where spid=?', (entry['template_spid'],)).fetchone())
        new = dict(db.execute('select * from players where spid=?', (spid,)).fetchone())
        stat_fields = 'strength stamina acceleration sprintspeed jumping agility balance slidingtackle dribbling ballcontrol marking standingtackle crossing shortpassing finishing longpassing shotpower headingaccuracy longshots volleys curve freekickaccuracy penalties interceptions positioning vision reactions aggression gkkicking gkdiving gkhandling gkpositioning gkreflexes'.split()
        assert all(new[k] == original[k] + 15 for k in stat_fields)
        for level in verified_levels:
            for pos in range(28):
                def rating(s, grade):
                    team = dict(players=[dict(spid=s, grade=grade, levelinfo={'level': level, 'exp': 0})], squad={'positions': [dict(spid=s, pos=pos)]}, teamcolors=[])
                    return h.xi_ratings(team)[str(s)]
                assert rating(spid, 1) == rating(original['spid'], 9), (spid, level, pos)
        targets.append(spid)
    engine = h.market_engine
    assert set(targets) == set(engine._legend_moments_bulk_npc_exclusion)
    assert not set(targets) & set(engine.candidates())
    state = copy.deepcopy(h._state())
    engine.prepare(state)
    stamp = time.time()
    for spid in targets:
        assert engine.valid_card(spid, 1)  # Player trading remains supported.
        assert engine.book(copy.deepcopy(state), spid, stamp)['rows'] == []
        result = engine.purchase(spid, 1, 1, {}, b'{}')
        assert 'NOT_EXIST_OFFER' in str(result), (spid, result)
    state['market_simulation']['legacy_supply'] = [dict(spid=targets[0], grade=1, price=1, count=1, _market_release=stamp - 1, _market_expires=stamp + 3600)]
    assert not any(r['spid'] in targets for r in engine.rare_stock(state, stamp))

cadence = json.loads((server / 'gamedata/pack_cadence.json').read_text('utf-8'))
assert len(cadence['legacy']) >= 102
assert len(cadence.get('legacy_lotteries', {})) == 9
assert hashlib.sha256((server / 'gamedata/pack_cadence.json').read_bytes()).hexdigest() == prepared['source_hashes']['gamedata\\pack_cadence.json']
new_cards = wanted - {13158023, 13020801, 13028130}
assert all(not new_cards.intersection(int(pair[0]) for pair in item['pool']) for item in cadence['legacy'].values())
assert hashlib.sha256((server / 'gamedata/state.json').read_bytes()).hexdigest() == prepared['state_copy_sha256']
assert hashlib.sha256((server / 'gamedata/shop.json').read_bytes()).hexdigest() == prepared['shop_copy_sha256']
report = dict(status='PASS_PRIVATE_BULK_RUNTIME_NATIVE_PENDING', sqlite_rows=manifest['rows'],
              registered_searchable=len(queries), all_registered_market_permissions_valid=True,
              price_checks=len(prices) * 20, max_grade20_price=max(r['grade20'] for r in prices), price_profile='current copied formal profile; no BB4',
              prices=prices, moments_count=len(targets), player_max_level=h.PLAYER_MAX_LEVEL,
              actual_position_rating_equalities=len(targets) * len(verified_levels) * 28,
              moments_npc_candidates_direct_book_persisted_rare_and_forged_purchase_blocked=True,
              old_102_pack_pools_unchanged=True, old_9_lotteries_unchanged=True, state_shop_byte_identical=True,
              private_writes=len(events), no_listener=True,
              production_written=False, native_verified=False, match_verified=False)
(server / 'runtime-PASS.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
print(json.dumps({k: report[k] for k in ('status', 'sqlite_rows', 'registered_searchable', 'price_checks', 'moments_count', 'actual_position_rating_equalities')}))
