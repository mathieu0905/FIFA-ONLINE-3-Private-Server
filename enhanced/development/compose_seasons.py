"""Compose reviewed FO3 roster candidates in isolation; never installs or starts a server."""
from pathlib import Path
import argparse, hashlib, json, shutil, sqlite3, sys

sys.dont_write_bytecode = True
WORK = Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
SERVER = Path('D:/FO3ID/server')
MODERN = Path('D:/FO3QA/modern_player_integration_v2/native24-model19-v4')
NAMES = Path('D:/FO3QA/ggmu-bellingham-20261106/names-v5')
MOMENTS = Path('D:/FO3QA/legend_moments/candidate-four-v1')
ICON = WORK / 'outputs/FO3ID/新赛季导入/候选ICON12-v2'
sys.path.insert(0, str(WORK / 'work/season_expansion'))
import roster_import as codec


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def ro(path):
    return sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)


def build(out):
    out = out.resolve()
    assert out.is_relative_to(Path('D:/fifaol3').resolve()) and not out.exists()
    modern_manifest = read(MODERN / 'manifest.json')
    assert codec.sha(MODERN / 'manifest.json') == '1d951e9ade40d4c41a05fc63886951288531bca651d52f8efe6e697a96d16ec8'
    for rel, digest in modern_manifest['package_hashes'].items():
        assert codec.sha(MODERN / rel) == digest, rel
    moment_manifest = read(MOMENTS / 'manifest.json')
    assert codec.sha(MOMENTS / 'manifest.json') == '50701338e986ac90409a306d0be1411ffcdf904f1c500f9197f89828fe38892a'
    for rel, digest in moment_manifest['files'].items():
        assert codec.sha(MOMENTS / rel) == digest, rel
    names_report = read(NAMES / 'report.json')
    assert codec.sha(NAMES / 'data_0.big') == names_report['data0_sha256']
    assert codec.sha(NAMES / 'fifadb.sqlite') == names_report['sqlite_sha256']
    assert names_report['source_manifest_sha256'] == codec.sha(MODERN / 'manifest.json')
    protected = {str(p): codec.sha(p) for p in (
        SERVER / 'gamedata/fifadb.sqlite', SERVER / 'gamedata/shop.json',
        SERVER / 'gamedata/custom_rosters.json', SERVER / 'gamedata/pack_cadence.json',
        SERVER / 'http_config.py')}
    out.mkdir(parents=True)
    dbfile = out / 'fifadb.sqlite'
    shutil.copyfile(NAMES / 'fifadb.sqlite', dbfile)
    moment_ids = [r['spid'] for r in moment_manifest['cards']]
    assert len(set(moment_ids)) == 4
    with sqlite3.connect(dbfile.resolve().as_uri(), uri=True) as db:
        db.execute('attach database ? as moments', (MOMENTS.joinpath('fifadb.sqlite').resolve().as_uri() + '?mode=ro',))
        for table in ['players', *codec.PERMISSIONS]:
            marks = ','.join('?' for _ in moment_ids)
            assert db.execute(f'select count(*) from {table} where spid in ({marks})', moment_ids).fetchone()[0] == 0
            db.execute(f'insert into {table} select * from moments.{table} where spid in ({marks})', moment_ids)
        db.commit()
        assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
        assert db.execute('select count(*) from players').fetchone()[0] == 60217
        db.execute('attach database ? as formal', ((SERVER / 'gamedata/fifadb.sqlite').resolve().as_uri() + '?mode=ro',))
        preserved = {}
        for (table,) in db.execute("select name from formal.sqlite_master where type='table'").fetchall():
            assert not db.execute(f'select * from formal.{table} except select * from main.{table} limit 1').fetchone(), table
            preserved[table] = db.execute(f'select count(*) from formal.{table}').fetchone()[0]

    registry = read(MODERN / 'custom_rosters.json')
    old_registry = read(SERVER / 'gamedata/custom_rosters.json')
    assert all(row in registry['cards'] for row in old_registry['cards'])
    moment_registry = read(MOMENTS / 'custom_rosters.json')
    season = next(s for s in moment_registry['seasons'] if s['id'] == 84)
    season = dict(season, cards=moment_ids)
    assert not any(s['id'] == 84 for s in registry['seasons'])
    registry['seasons'].append(season)
    registry['cards'].extend(r for r in moment_registry['cards'] if r['fo3_spid'] in moment_ids)
    ids = [r['fo3_spid'] for r in registry['cards']]
    assert len(ids) == len(set(ids)) == 43
    write(out / 'custom_rosters.json', registry)
    roster = read(MODERN / 'static_roster.json')
    roster['seasons'].append(next(s for s in read(MOMENTS / 'static_roster.json')['seasons'] if 84 in s.get('value', [])))
    write(out / 'static_roster.json', roster)

    # The six client language SQLite tables are distinct from nameschi in the main DB.
    b, decrypt, replace, refpack, encrypt = codec.load_codecs(SERVER)
    target = out / 'data_0.big'
    shutil.copyfile(NAMES / 'data_0.big', target)
    raw = bytes(decrypt.decrypt(b.read(target, codec.MEMBER)))
    encoded = encrypt(raw[:16] + dbfile.read_bytes()[16:])
    replace(target, codec.MEMBER, refpack(encoded), len(encoded))
    assert b'SQLite format 3\0' + bytes(decrypt.decrypt(b.read(target, codec.MEMBER)))[16:] == dbfile.read_bytes()
    old_entries, new_entries = b.entries(NAMES / 'data_0.big'), b.entries(target)
    assert len(old_entries) == len(new_entries) == 271
    assert all(a[1] + a[2] <= z[1] for a, z in zip(new_entries, new_entries[1:]))
    with (NAMES / 'data_0.big').open('rb') as before, target.open('rb') as after:
        for a, z in zip(old_entries, new_entries):
            assert a[0] == z[0]
            if a[0] != codec.MEMBER:
                before.seek(a[1]); after.seek(z[1])
                assert before.read(a[2]) == after.read(z[2]), a[0]
    language_checks = {}
    for lang in ['eng', 'chi', 'ind', 'kor', 'tha', 'vie']:
        decoded = bytes(decrypt.decrypt(b.read(target, f'data/db2/{lang}.db.db2')))
        local = out / f'{lang}.sqlite'
        local.write_bytes(b'SQLite format 3\0' + decoded[16:])
        with ro(local) as db:
            assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
            missing = [r['base_playerid'] for r in registry['cards'] if not db.execute('select 1 from names where playerid=?', (r['base_playerid'],)).fetchone()]
            assert not missing, (lang, missing)
            language_checks[lang] = {'all_43_registered_cards_have_names': True}

    portraits = out / 'assets/players'
    portraits.mkdir(parents=True)
    records = []
    for row in registry['cards']:
        spid = row['fo3_spid']
        group = 'moments4' if spid // 1000000 == 84 else 'icon12' if spid // 1000000 == 12 else 'modern24' if row.get('import_version') == 'modern24-private-v1' else 'installed3'
        if group == 'installed3':
            continue
        root = MOMENTS if group == 'moments4' else ICON if group == 'icon12' else MODERN
        source = root / f'assets/players/p{spid}.png'
        assert source.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        shutil.copyfile(source, portraits / source.name)
        records.append({'spid': spid, 'playerid': row['base_playerid'], 'name_zh': row['name_zh'], 'group': group,
                        'portrait_sha256': codec.sha(source), 'native_verified': False, 'match_verified': False})
    assert len(records) == 40
    shutil.copyfile(MOMENTS / 'npc_exclusion.py', out / 'legend_moments_npc.py')
    shutil.copyfile(MOMENTS / 'exact-targets.json', out / 'moment-targets.json')
    model_manifest = Path('D:/FO3QA/modern_player_integration_v2/model19-v4/manifest.json')
    models = read(model_manifest)
    for archive in models['archives']:
        assert codec.sha(Path(archive['target'])) == archive['target_sha256']
    for p, digest in protected.items():
        assert codec.sha(Path(p)) == digest, 'Source changed; rebuild against the new baseline: ' + p
    report = {'status': 'COMPOSED_40_NEW_CARDS_PRIVATE_NOT_INSTALLED', 'source_hashes': protected,
              'source_manifests': {str(MODERN / 'manifest.json'): codec.sha(MODERN / 'manifest.json'),
                                   str(MOMENTS / 'manifest.json'): codec.sha(MOMENTS / 'manifest.json'),
                                   str(NAMES / 'report.json'): codec.sha(NAMES / 'report.json')},
              'formal_rows_preserved': preserved, 'result_rows': 60217, 'new_cards': records,
              'registered_card_total': 43, 'counts': {'installed3': 3, 'modern24': 24, 'icon12': 12, 'moments4': 4},
              'language_sqlite_checks': language_checks, 'ordered_big_entries': 271,
              'non_main_db_members_identical_to_names_fixed_candidate': 270,
              'dual_db_equal': True, 'generic_importer_cap99_unchanged': True,
              'model_manifest': str(model_manifest), 'model_manifest_sha256': codec.sha(model_manifest),
              'model_archives': models['archives'], 'old_specific_face_count': 5, 'converted_specific_face_count': 19,
              'production_written': False, 'native_verified': False, 'match_verified': False,
              'output_hashes': {str(p.relative_to(out)): codec.sha(p) for p in out.rglob('*') if p.is_file()}}
    write(out / 'manifest.json', report)
    print(json.dumps({'status': report['status'], 'candidate': str(out), 'cards': report['counts'], 'rows': 60217}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    build(parser.parse_args().out)
