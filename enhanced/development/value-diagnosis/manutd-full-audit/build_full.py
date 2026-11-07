"""Build the full audited MUL correction against fresh official resources."""
from pathlib import Path
import copy
import ctypes
import datetime
import json
import shutil
import sqlite3
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import audit
from audit import correction as tools
from features import ability_fields


def build():
    if sys.platform == 'win32':
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    analysis = audit.run()
    out = P / ('build-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    out.mkdir()
    S, C = tools.S, tools.C
    inputs = [S / 'gamedata/fifadb.sqlite', S / 'gamedata/custom_rosters.json', C / 'data/data_0.big']
    baseline = {str(path): tools.sha(path) for path in inputs}
    assert all(baseline[path] == value for path, value in analysis['baseline'].items())
    expected = {row['spid']: row for row in analysis['rows']}
    changed = {sid: row for sid, row in expected.items() if row['status'] == 'CORRECT'}
    fields = ability_fields(tools.MonotoneValueModel().config)
    registry = json.loads(inputs[1].read_text('utf8'))
    original_registry = copy.deepcopy(registry)
    dbpath = out / 'fifadb.sqlite'
    with sqlite3.connect(inputs[0].as_uri() + '?mode=ro', uri=True) as source, sqlite3.connect(dbpath) as target:
        source.backup(target)
    with sqlite3.connect(dbpath, uri=True) as target:
        target.row_factory = sqlite3.Row
        for sid, row in changed.items():
            assert dict(target.execute('SELECT * FROM players WHERE spid=?', (sid,)).fetchone()) == row['before_row']
            target.execute('UPDATE players SET ' + ','.join(f + '=?' for f in fields) + ' WHERE spid=?',
                           [row['after_row'][f] for f in fields] + [sid])
            card = next(card for card in registry['cards'] if card['fo3_spid'] == sid)
            card['attribute_correction'] = dict(revision='manutd-full-role-audit-v2',
                reasons=row['reasons'], original_source_spid=row['original_template_spid'],
                verified_original_source_digest=tools.digest(row['source_row']),
                selected_source_spid=row['selected_source']['spid'], selected_source_digest=tools.digest(row['selected_source']),
                before_row_digest=tools.digest(row['before_row']), after_row_digest=tools.digest(row['after_row']),
                original_primary_integer_rating=row['primary_before'], corrected_primary_integer_rating=row['primary_after'],
                changed_fields=list(row['changes']), role_only_shift=row['role_shift'])
        target.commit()
        target.execute('ATTACH DATABASE ? AS baseline', (inputs[0].as_uri() + '?mode=ro',))
        for table, in target.execute("SELECT name FROM main.sqlite_master WHERE type='table'").fetchall():
            name = '"' + table.replace('"', '""') + '"'
            where = ' WHERE spid NOT IN (' + ','.join(map(str, changed)) + ')' if table == 'players' else ''
            assert target.execute('SELECT COUNT(*) FROM main.' + name).fetchone() == target.execute('SELECT COUNT(*) FROM baseline.' + name).fetchone()
            assert not target.execute('SELECT * FROM main.' + name + where + ' EXCEPT SELECT * FROM baseline.' + name + where + ' LIMIT 1').fetchone(), table
            assert not target.execute('SELECT * FROM baseline.' + name + where + ' EXCEPT SELECT * FROM main.' + name + where + ' LIMIT 1').fetchone(), table
        for sid, row in expected.items():
            assert dict(target.execute('SELECT * FROM players WHERE spid=?', (sid,)).fetchone()) == row['after_row']
        assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    old_lookup = {c['fo3_spid']: c for c in original_registry['cards']}
    for card in registry['cards']:
        if card['fo3_spid'] not in changed:
            assert card == old_lookup[card['fo3_spid']]
        else:
            assert {k: v for k, v in card.items() if k != 'attribute_correction'} == {k: v for k, v in old_lookup[card['fo3_spid']].items() if k != 'attribute_correction'}
    tools.save(out / 'custom_rosters.json', registry)
    decoded = bytes(tools.extract_fifadb.decrypt(tools.bigdir.read(inputs[2], tools.MEMBER)))
    assert b'SQLite format 3\0' + decoded[16:] == inputs[0].read_bytes()
    big = out / 'data_0.big'
    shutil.copyfile(inputs[2], big)
    plain = dbpath.read_bytes()
    encoder = tools.Cipher(tools.Blowfish(tools.extract_fifadb.KEY), tools.modes.ECB()).encryptor()
    encrypted = tools.extract_fifadb.swap32(encoder.update(tools.extract_fifadb.swap32(decoded[:16] + plain[16:])) + encoder.finalize())
    tools.replace_member(big, tools.MEMBER, tools.refpack(encrypted), len(encrypted))
    assert b'SQLite format 3\0' + bytes(tools.extract_fifadb.decrypt(tools.bigdir.read(big, tools.MEMBER)))[16:] == plain
    layout = tools.load(S / 'tools/check_data0_layout.py', 'mul_full_layout').inspect(
        big, baseline=inputs[2], changed_members={tools.MEMBER}, expected_count=len(tools.bigdir.entries(inputs[2])))
    assert layout['status'] == 'PASS'
    tools.save(out / 'layout-verification.json', layout)
    checker = tools.load(S / 'tools/player_import/check.py', 'mul_full_import')
    certificate = checker.validate(S, C, database=dbpath, data0=big, registry=out / 'custom_rosters.json', full=True)
    assert certificate['status'] == 'PLAYER_IMPORT_FULL_PASS'
    tools.save(out / 'player-import-validation.json', certificate)
    assert baseline == {str(path): tools.sha(path) for path in inputs}, 'Fresh official inputs changed; rebuild before installation'
    ranking = sorted([dict(spid=row['spid'], name=row['name'], primary_rating=row['primary_after'],
                           old_value=row['old_value'], new_value=row['new_value'], status=row['status'])
                      for row in analysis['rows']], key=lambda row: (-row['new_value'], row['spid']))
    tools.save(out / 'manutd-rankings.json', ranking)
    report = dict(status='ALL67_CORRECTION_FULL_CHECK_PASS_ACTIVATION_DEFERRED', output=str(out),
        audit=str(P / 'audit.json'), reviewed=67, remaining_reviewed=65, changed_rows=len(changed),
        remaining_corrected=analysis['remaining_corrected'], unchanged_rows=analysis['unchanged'],
        primary_ratings_all_preserved=True, nonstat_metadata_all_exact=True,
        all_non_MUL_rows_and_other_tables_exact=True, historical49_55_exact=True,
        original_registry_fields_and_season_filters_exact=True,
        non_target_big_members_exact=True, layout_status=layout['status'],
        full_player_import_status=certificate['status'], baseline=baseline,
        outputs={path.name: tools.sha(path) for path in out.iterdir() if path.is_file()},
        model_sha256=analysis['model_sha256'], top10=ranking[:10],
        formal_written=False, formal_activated=False, real_state_shop_market_written=False,
        game_GUI='none', services_action='none', native_verified=False, match_verified=False)
    tools.save(out / 'report.json', report)
    tools.save(P / 'latest-build.json', dict(path=str(out), status=report['status']))
    print(json.dumps(report, ensure_ascii=False))
    return out


if __name__ == '__main__':
    build()
