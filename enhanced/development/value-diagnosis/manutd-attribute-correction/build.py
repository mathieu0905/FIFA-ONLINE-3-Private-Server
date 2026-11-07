"""Correct two proven role-template inflations; only write working artifacts.

Never import legacy transaction launchers: some execute installs at import time.
The game, services, real saves, market history and official files are untouched.
"""
from pathlib import Path
import ctypes
import datetime
import hashlib
import importlib.util
import json
import shutil
import sqlite3
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
S = Path('D:/FO3ID/server')
C = Path('D:/FO3ID/32795')
TRAIN = Path('D:/fifaol3/npc-peer-market/monotone-retraining-v9')
sys.path[:0] = [str(TRAIN), str(S / 'tools/re'), str(S / 'player_editor'), str(S)]
from predict import MonotoneValueModel
from features import ability_fields, role_rating
import bigdir
import extract_fifadb
from ordered_big import replace_member
from refpack import refpack
from cryptography.hazmat.primitives.ciphers import Cipher, modes
try:
    from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
except ImportError:
    from cryptography.hazmat.primitives.ciphers.algorithms import Blowfish

TARGETS = (48167905, 48152908)
MEMBER = 'data/db2/fifadb.db.db2'


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', 'utf8')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def corrected_row(current, historical, config):
    fields = ability_fields(config)
    role = config['position_roles'][current['preferredposition1']]
    weights = config['role_weights'][role]
    target = sum(current[k] * w for k, w in weights.items()) // 100
    # Source must actually be this person's native role, not simply the row
    # with the largest unrelated overallrating value. Body/model/identity and
    # foot/skill metadata are retained from the current legitimate card.
    candidates = [r for r in historical if r['playerid'] == current['playerid']
                  and r['spid'] >= 1_000_000
                  and config['position_roles'][r['preferredposition1']] == role]
    if not candidates:
        raise ValueError('No verified same-person same-role template')
    score = lambda r: sum(r[k] * w for k, w in weights.items()) / 100
    source = max(candidates, key=lambda r: (score(r), r['spid']))
    choices = []
    for shift in range(81):
        # Lift only the weighted FB-role abilities needed for the already
        # agreed current rating. Other abilities remain the authentic template
        # values, especially finishing, GK and unrelated attacking attributes.
        stats = {k: min(99, max(1, source[k] + shift)) if k in weights else source[k] for k in fields}
        actual = sum(stats[k] * w for k, w in weights.items()) // 100
        if actual == target:
            choices.append((sum(stats[k] >= 99 for k in weights), shift, stats))
    if not choices:
        raise ValueError('Requested role rating cannot be preserved')
    _, shift, stats = min(choices, key=lambda row: (row[0], row[1]))
    result = {**current, **stats}
    assert all(result[k] == v for k, v in current.items() if k not in fields)
    assert sum(result[k] * w for k, w in weights.items()) // 100 == target
    assert all(result[k] == source[k] for k in fields if k not in weights)
    return result, source, shift, target


def build():
    # Run resource compression below normal priority while the user plays.
    if sys.platform == 'win32':
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    P.mkdir(parents=True, exist_ok=True)
    output = P / ('build-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    output.mkdir()
    paths = [S / 'gamedata/fifadb.sqlite', C / 'data/data_0.big', S / 'gamedata/custom_rosters.json']
    baseline = {str(path): sha(path) for path in paths}
    model = MonotoneValueModel()
    config = model.config
    fields = ability_fields(config)
    registry = json.loads(paths[2].read_text('utf8'))
    custom_seasons = {s['id'] for s in registry['seasons']}
    source_db = sqlite3.connect(paths[0].as_uri() + '?mode=ro', uri=True)
    source_db.row_factory = sqlite3.Row
    dbpath = output / 'fifadb.sqlite'
    with sqlite3.connect(dbpath) as target:
        source_db.backup(target)
    decoded = bytes(extract_fifadb.decrypt(bigdir.read(paths[1], MEMBER)))
    assert b'SQLite format 3\0' + decoded[16:] == paths[0].read_bytes()
    changes = []
    with sqlite3.connect(dbpath, uri=True) as target:
        target.row_factory = sqlite3.Row
        for spid in TARGETS:
            old = dict(source_db.execute('SELECT * FROM players WHERE spid=?', (spid,)).fetchone())
            historical = [dict(r) for r in source_db.execute('SELECT * FROM players WHERE playerid=? AND spid>=1000000', (old['playerid'],))
                          if r['spid'] // 1_000_000 not in custom_seasons]
            new, template, shift, rating = corrected_row(old, historical, config)
            target.execute('UPDATE players SET ' + ','.join(f + '=?' for f in fields) + ' WHERE spid=?',
                           [new[f] for f in fields] + [spid])
            card = next(c for c in registry['cards'] if c['fo3_spid'] == spid)
            card['attribute_correction'] = dict(revision='manutd-role-template-v1',
                source_spid=template['spid'], source_row_sha256=digest(template),
                previous_row_sha256=digest(old), corrected_row_sha256=digest(new),
                role='FB', target_primary_integer_rating=rating, role_only_stat_shift=shift,
                policy='Same-person actual-role source; role-weighted abilities calibrated only; all other numeric abilities copied from source. Existing identity/models/position/foot/skill unchanged.')
            name = source_db.execute('SELECT short FROM nameschi WHERE playerid=?', (old['playerid'],)).fetchone()[0]
            changes.append(dict(spid=spid, name=name, original_import_template_spid=card['template_spid'],
                original_import_stat_shift=card.get('stat_shift'), corrected_source_spid=template['spid'],
                source_role='FB', role_only_shift=shift, primary_integer_rating_before=rating,
                primary_integer_rating_after=rating, old_99_count=sum(old[f] == 99 for f in fields),
                new_99_count=sum(new[f] == 99 for f in fields), old_value=model.predict(old), new_value=model.predict(new),
                model_sha256=model.sha256, attribute_changes={f: [old[f], new[f]] for f in fields if old[f] != new[f]},
                before_row=old, after_row=new, source_row=template))
        target.commit()
        target.execute('ATTACH DATABASE ? AS baseline', (paths[0].as_uri() + '?mode=ro',))
        for table, in target.execute("SELECT name FROM main.sqlite_master WHERE type='table'").fetchall():
            quoted = '"' + table.replace('"', '""') + '"'
            where = ' WHERE spid NOT IN (48167905,48152908)' if table == 'players' else ''
            assert target.execute('SELECT COUNT(*) FROM main.' + quoted).fetchone()[0] == target.execute('SELECT COUNT(*) FROM baseline.' + quoted).fetchone()[0]
            assert not target.execute('SELECT * FROM main.' + quoted + where + ' EXCEPT SELECT * FROM baseline.' + quoted + where + ' LIMIT 1').fetchone(), table
            assert not target.execute('SELECT * FROM baseline.' + quoted + where + ' EXCEPT SELECT * FROM main.' + quoted + where + ' LIMIT 1').fetchone(), table
        assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        scores = []
        for row in target.execute('SELECT p.*,n.short AS name FROM players p LEFT JOIN nameschi n USING(playerid) WHERE p.spid/1000000=48'):
            raw = dict(row)
            scores.append(dict(spid=raw['spid'], name=raw['name'], value=model.predict(raw)))
        scores.sort(key=lambda r: (-r['value'], r['spid']))
    source_db.close()
    save(output / 'custom_rosters.json', registry)
    big = output / 'data_0.big'
    shutil.copyfile(paths[1], big)
    plain = dbpath.read_bytes()
    encoder = Cipher(Blowfish(extract_fifadb.KEY), modes.ECB()).encryptor()
    encrypted = extract_fifadb.swap32(encoder.update(extract_fifadb.swap32(decoded[:16] + plain[16:])) + encoder.finalize())
    replace_member(big, MEMBER, refpack(encrypted), len(encrypted))
    assert b'SQLite format 3\0' + bytes(extract_fifadb.decrypt(bigdir.read(big, MEMBER)))[16:] == plain
    layout = load(S / 'tools/check_data0_layout.py', 'attribute_fix_layout')
    layout_result = layout.inspect(big, baseline=paths[1], changed_members={MEMBER}, expected_count=len(bigdir.entries(paths[1])))
    assert layout_result['status'] == 'PASS'
    save(output / 'layout-verification.json', layout_result)
    checker = load(S / 'tools/player_import/check.py', 'attribute_fix_import_check')
    certificate = checker.validate(S, C, database=dbpath, data0=big, registry=output / 'custom_rosters.json', full=True)
    assert certificate['status'] == 'PLAYER_IMPORT_FULL_PASS'
    save(output / 'player-import-validation.json', certificate)
    assert baseline == {str(path): sha(path) for path in paths}, 'Official input changed during build; rebuild before installation'
    report = dict(status='CORRECTED_RESOURCES_FULL_CHECK_PASS_ACTIVATION_DEFERRED', baseline=baseline,
        changes=changes, corrected_manutd_top10=scores[:10],
        scope='Only two season48 attribute rows and appended current provenance; all other DB rows/tables and non-target BIG members unchanged.',
        other_65_main_season_cards_exact=True, historical_49_55_exact=True, nonattribute_metadata_exact=True,
        historical_import_receipts_modified=False, state_shop_written=False, historical_market_db_written=False,
        formal_written=False, formal_activated=False, services_action='none', gui_action='none',
        layout_status=layout_result['status'], player_import_full_status=certificate['status'],
        native_runtime_verified=False, match_verified=False, output=str(output),
        outputs={p.name: sha(p) for p in output.iterdir() if p.is_file()})
    save(output / 'report.json', report)
    save(P / 'latest-build.json', dict(path=str(output), status=report['status']))
    print(json.dumps({k: v for k, v in report.items() if k not in ['changes', 'baseline', 'outputs']}, ensure_ascii=False))
    for c in changes:
        print(json.dumps({k: c[k] for k in ['spid', 'name', 'corrected_source_spid', 'role_only_shift', 'old_99_count', 'new_99_count', 'old_value', 'new_value']}, ensure_ascii=False))
    return output


if __name__ == '__main__':
    build()
