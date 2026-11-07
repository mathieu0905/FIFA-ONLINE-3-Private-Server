"""Build hundreds of identity-preserving cards on the composed forty-card baseline."""
from pathlib import Path
import argparse, ast, datetime, hashlib, json, re, shutil, sqlite3, sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
WORK = Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
SERVER = Path('D:/FO3ID/server')
BASE = ROOT / 'candidates/all-seasons-v2'
sys.path.insert(0, str(WORK / 'work/season_expansion'))
import roster_import as codec

POSITIONS = 'GK SW RWB RB RCB CB LCB LB LWB RDM CDM LDM RM RCM CM LCM LM RAM CAM LAM RF CF LF RW RS ST LS LW'.split()
ROLES = 'GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split()
tree = ast.parse((SERVER / 'http_config.py').read_text('utf-8'))
WEIGHTS = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ROLE_WEIGHTS' for t in n.targets))


def read(p):
    return json.loads(p.read_text('utf-8'))


def write(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), 'utf-8')


def ovr(row, pos=None):
    return sum(row[k] * w for k, w in WEIGHTS[ROLES[row['preferredposition1'] if pos is None else pos]].items()) // 100


def build(out):
    out = out.resolve()
    assert out.is_relative_to(ROOT) and not out.exists()
    manifest = read(BASE / 'manifest.json')
    for rel, digest in manifest['output_hashes'].items():
        assert codec.sha(BASE / rel) == digest, rel
    protected = {str(p): codec.sha(p) for p in [SERVER / 'gamedata/fifadb.sqlite', SERVER / 'gamedata/pack_cadence.json', SERVER / 'gamedata/shop.json', SERVER / 'http_config.py']}
    sources = read(ROOT / 'bulk-sources/sources.json')
    ready = [r for r in sources if r['status'] == 'READY_OFFICIAL_SNAPSHOT']
    assert len(sources) == 378, 'Wait for all source jobs before freezing a bulk build'
    icon_meta = read(WORK / 'work/season_expansion/model_compatible_icons.json')
    out.mkdir(parents=True)
    targetdb = out / 'fifadb.sqlite'
    shutil.copyfile(BASE / 'fifadb.sqlite', targetdb)
    registry = read(BASE / 'custom_rosters.json')
    registered = {r['fo3_spid']: r for r in registry['cards']}
    events = []
    skipped = []
    with sqlite3.connect(targetdb.resolve().as_uri(), uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('attach database ? as formal', ((SERVER / 'gamedata/fifadb.sqlite').resolve().as_uri() + '?mode=ro',))

        def insert(row, entry, source_portrait):
            columns = list(row)
            db.execute('insert into players(' + ','.join(columns) + ') values(' + ','.join('?' for _ in columns) + ')', [row[k] for k in columns])
            for table in codec.PERMISSIONS:
                db.execute(f'insert into {table}(spid,licensed,transferable) values(?,1,1)', (row['spid'],))
            assert entry['fo3_spid'] not in registered
            registry['cards'].append(entry)
            registered[entry['fo3_spid']] = entry
            portraits = out / 'assets/players'
            portraits.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_portrait, portraits / f'p{row["spid"]}.png')

        for card in ready:
            pid = card['playerid']
            sid = 13 if card['group'] == 'modern' else 12
            spid = sid * 1000000 + pid
            if spid in registered:
                continue  # Already reviewed forty-card baseline remains byte-for-byte intact.
            assert codec.sha(Path(card['raw_file'])) == card['raw_sha256']
            assert codec.sha(Path(card['portrait_file'])) == card['portrait_sha256']
            if sid == 12:
                template = card['template_spid']
            else:
                template = db.execute('select spid from formal.players where playerid=? and spid>=1000000 and spid/1000000 not in (12,13,84,90,92,96,98) order by overallrating desc,spid desc limit 1', (pid,)).fetchone()
                assert template is not None, pid
                template = template[0]
            row = dict(db.execute('select * from players where spid=?', (template,)).fetchone())
            before = dict(row)
            bonus = 3 if sid == 12 else 0
            for stat in codec.STATS:
                row[stat] = max(1, min(99, round(card['stats'][stat] * .75) + bonus))
            row.update(spid=spid, overallrating=max(1, min(99, round(card['ovr'] * .75) + bonus)), preferredposition1=POSITIONS.index(card['primary_position']))
            if sid == 13:
                html = Path(card['raw_file']).read_text('utf-8')
                birthday = datetime.datetime.strptime(card['physical']['birthdate'], '%Y.%m.%d')
                foot = re.search(r'<span class="etc foot">(.*?)</span>', html, re.S)[1]
                dominant = re.search(r'<strong>([LR])(\d)</strong>', foot)
                weak = re.search(('R' if dominant[1] == 'L' else 'L') + r'(\d)', foot)
                preferred = re.findall(r'<span class="position (?:fw|mf|df|gk)">\s*<span class="txt">([A-Z]+)</span>', html)
                assert preferred[0] == card['primary_position']
                for i in range(1, 4):
                    row['preferredposition' + str(i + 1)] = POSITIONS.index(preferred[i]) if i < len(preferred) else -1
                skill = re.search(r'<span class="etc skill">(.*?)</span>', html, re.S)
                assert skill and '★' in skill[1]
                row.update(birthdate=f'{birthday.month}/{birthday.day}/{birthday.year} 12:00:00 AM',
                           height=int(card['physical']['height'].replace('cm', '').strip()), weight=int(card['physical']['weight'].replace('kg', '').strip()),
                           nationality=card['nationality'], teamid=47 if card['teamid'] == 131681 else card['teamid'], leagueid=card['leagueid'],
                           skillmoves=min(5, skill[1].count('★')), preferredfoot=2 if dominant[1] == 'L' else 1, weakfootabilitytypecode=int(weak[1]),
                           playerjointeamdate='Fri, 06 Nov 2026 00:00:00 GMT', contractvaliduntil=2029)
                assert all(row[k] is not None for k in ('nationality', 'teamid', 'leagueid'))
            entry = dict(fo3_spid=spid, base_playerid=pid, name_zh=card['name_zh'], name_en=card['name_en'], fc_spid=card['fc_spid'],
                         local_season_id=sid, source_season_id=card['fc_spid'] // 1000000, template_spid=template,
                         import_version='bulk-existing-identity-v1', mapping_rule=f'round(FC * 0.75) + {bonus}, clamp1..99',
                         source_url='https://fconline.nexon.com/DataCenter/PlayerInfo?spid=' + str(card['fc_spid']),
                         source_sha256=card['raw_sha256'], model_strategy='retain same player existing FO3 template; original24 retain converted selectors',
                         date_policy='local game contract initialized 2026-11-06 until2029; no assertion of real transfer dates' if sid == 13 else 'retain existing same-player classic metadata',
                         native_pending=True)
            insert(row, entry, Path(card['portrait_file']))
            events.append(dict(spid=spid, playerid=pid, name_zh=card['name_zh'], group=card['group'], template_spid=template,
                               grade1_level1_posovr=ovr(row) + 5, new_raw_max=max(row[s] for s in codec.STATS)))

        # Every compatible ICON identity gets a moment, independent of FC ability endpoint availability.
        moment_checks = []
        for icon in icon_meta:
            pid = icon['playerid']
            spid = 84000000 + pid
            if spid in registered:
                continue
            originals = [dict(r) for r in db.execute('select * from formal.players where playerid=? and spid>=1000000 and spid/1000000 not in (12,13,84,90,92,96,98)', (pid,))]
            old = max(originals, key=lambda r: (ovr(r), r['overallrating'], r['spid']))
            row = old | {s: old[s] + 15 for s in codec.STATS}
            row.update(spid=spid, overallrating=ovr(row) + 5)
            assert max(row[s] for s in codec.STATS) <= 127
            assert all(row[s] + 5 == old[s] + 20 for s in codec.STATS)
            assert all(ovr(row, pos) + 5 == ovr(old, pos) + 20 for pos in range(28))
            name = db.execute('select full from nameschi where playerid=?', (pid,)).fetchone()[0]
            source = next((Path(c['portrait_file']) for c in ready if c['group'] == 'icon' and c['playerid'] == pid), None)
            if source is None:
                for cache in [Path('D:/FO3ID/32795/_cache/games/fo3id/externalAssets/players'), Path('D:/FO3ID/32795/_cache/cdn/externalAssets/players')]:
                    for filename in [f'p{pid}.png', f'p{old["spid"]}.png', *[f'p{r["spid"]}.png' for r in originals]]:
                        candidate = cache / filename
                        if candidate.is_file() and candidate.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
                            source = candidate
                            break
                    if source is not None:
                        break
            if source is None:
                skipped.append(dict(group='moments', playerid=pid, reason='no verified same-PID portrait yet'))
                continue
            entry = dict(fo3_spid=spid, base_playerid=pid, name_zh=name, name_en=icon['names']['full_eng'], local_season_id=84,
                         source_game='FO3', template_spid=old['spid'], import_version='bulk-classic-moments-v1', npc_supply=False,
                         mapping_rule='all33attributes+15; new+1 equals source+9 at same level without teamcolour', native_pending=True)
            insert(row, entry, source)
            event = dict(spid=spid, playerid=pid, name_zh=name, group='moments', template_spid=old['spid'], grade1_level1_posovr=ovr(row) + 5,
                         new_raw_max=max(row[s] for s in codec.STATS))
            events.append(event)
            moment_checks.append(event | dict(all33_stats_equal=True, all28_positions_equal=True))
        db.commit()
        assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
        preserved = {}
        for (table,) in db.execute("select name from formal.sqlite_master where type='table'").fetchall():
            assert not db.execute(f'select * from formal.{table} except select * from main.{table} limit 1').fetchone(), table
            preserved[table] = True
        counts = {sid: db.execute('select count(*) from players where spid/1000000=?', (sid,)).fetchone()[0] for sid in (12, 13, 84)}
        total = db.execute('select count(*) from players').fetchone()[0]
        for season in registry['seasons']:
            season['cards'] = sorted(r['fo3_spid'] for r in registry['cards'] if r['fo3_spid'] // 1000000 == season['id'])
        assert len(registered) == sum(counts.values())
    write(out / 'custom_rosters.json', registry)
    shutil.copyfile(BASE / 'static_roster.json', out / 'static_roster.json')
    # Add portraits from all earlier forty candidates without changing their hashes.
    for source in (BASE / 'assets/players').glob('*.png'):
        target = out / 'assets/players' / source.name
        assert not target.exists() or codec.sha(target) == codec.sha(source)
        shutil.copyfile(source, target)
    b, decrypt, replace, refpack, encrypt = codec.load_codecs(SERVER)
    target = out / 'data_0.big'
    shutil.copyfile(BASE / 'data_0.big', target)
    raw = bytes(decrypt.decrypt(b.read(target, codec.MEMBER)))
    encoded = encrypt(raw[:16] + targetdb.read_bytes()[16:])
    replace(target, codec.MEMBER, refpack(encoded), len(encoded))
    assert b'SQLite format 3\0' + bytes(decrypt.decrypt(b.read(target, codec.MEMBER)))[16:] == targetdb.read_bytes()
    old, new = b.entries(BASE / 'data_0.big'), b.entries(target)
    assert len(old) == len(new) == 271 and all(a[1] + a[2] <= z[1] for a, z in zip(new, new[1:]))
    with (BASE / 'data_0.big').open('rb') as before, target.open('rb') as after:
        for a, z in zip(old, new):
            assert a[0] == z[0]
            if a[0] != codec.MEMBER:
                before.seek(a[1]); after.seek(z[1]); assert before.read(a[2]) == after.read(z[2]), a[0]
    shutil.copyfile(ROOT / 'legend_moments_bulk_npc.py', out / 'legend_moments_bulk_npc.py')
    for path, digest in protected.items():
        assert codec.sha(Path(path)) == digest, path
    report = dict(status='BULK_PRIVATE_DB_BUILT_NATIVE_PENDING', baseline=str(BASE), baseline_manifest_sha256=codec.sha(BASE / 'manifest.json'),
                  rows=total, net_new_vs_formal=total - 60177, season_counts=counts, added_this_build=len(events), cards=events,
                  source_ready=len(ready), source_failures=[r for r in sources if r['status'] != 'READY_OFFICIAL_SNAPSHOT'],
                  skipped=skipped, all_formal_table_rows_preserved=preserved, old_issued_cards_unchanged=True,
                  moment_comparisons=moment_checks, dual_db_equal=True, ordered_entries=271, non_main_db_payloads_identical=270,
                  source_hashes=protected, generic_importer_cap99_unchanged=True, installed=False, production_written=False,
                  native_verified=False, match_verified=False,
                  model_manifest=manifest['model_manifest'], model_manifest_sha256=manifest['model_manifest_sha256'],
                  files={str(p.relative_to(out)): codec.sha(p) for p in out.rglob('*') if p.is_file()})
    write(out / 'manifest.json', report)
    print(json.dumps({k: report[k] for k in ['status', 'rows', 'net_new_vs_formal', 'season_counts', 'added_this_build', 'source_ready', 'skipped']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    build(parser.parse_args().out)
