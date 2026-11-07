"""Merge verified careers into the current production DB; build one DB member delta."""
from pathlib import Path
from collections import Counter, defaultdict
from contextlib import closing
import datetime
import gzip
import hashlib
import importlib.util
import json
import re
import shutil
import sqlite3
import sys
sys.dont_write_bytecode = True
import manual

ROOT = Path(__file__).resolve().parent
SERVER = Path('D:/FO3ID/server')
CLIENT = Path('D:/FO3ID/32795')
OLD = ROOT.parent / 'club-history'
MEMBER = 'data/db2/fifadb.db.db2'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def merged_rows(database):
    previous = load(OLD/'build.py', 'household_previous_builder')
    parser = load(OLD/'collect.py', 'household_career_parser')
    display = json.loads((SERVER/'server_display_zh.json').read_text('utf8'))['names_by_id']['TEAMNAMES_CHI.json']
    with sqlite3.connect('file:' + Path(database).as_posix() + '?mode=ro', uri=True) as db:
        old = defaultdict(list)
        identities = defaultdict(set)
        for pid, birth, nation in db.execute('SELECT DISTINCT playerid,birthdate,nationality FROM players'):
            identities[pid].add((birth.split(' ')[0], nation))
        for pid, _, tid, start, end, loan in db.execute('SELECT * FROM playerhistory ORDER BY playerid,ordernum'):
            old[pid].append((tid, start, end, loan))
    paths = {int(p.stem): p for p in (OLD/'records').glob('*.json')}
    for p in (ROOT/'sources/refreshed').glob('*.json'):
        # No-exact-ID markers must not remove a previously retained valid source.
        if json.loads(p.read_text('utf8')).get('status') == 'OK':
            paths[int(p.stem)] = p
    records = []
    evidence_hashes = {}
    for pid, path in sorted(paths.items()):
        record = json.loads(path.read_text('utf8'))
        if record.get('status') != 'OK' or pid not in identities:
            continue
        raw = gzip.decompress(Path(record['raw_file']).read_bytes())
        if hashlib.sha256(raw).hexdigest() != record['raw_sha256'] or parser.parse(raw.decode('utf-8-sig')) != record['career']:
            raise RuntimeError('Career evidence differs: ' + str(path))
        if int(record['source_spid']) % 1000000 != pid or record['playerid'] != pid:
            raise RuntimeError('Exact source identity differs')
        records.append(record)
        evidence_hashes[str(path)] = sha(path)
    # Exact official ID mapping, exact installed Korean names and reviewed old
    # license aliases. No edit-distance/name-only player identity matching.
    html = (ROOT/'sources/search-current.html').read_text('utf8')
    pairs = re.findall(r"DataCenter.SetAbilitySearch\('(\d+)', 'n4TeamId'\);[^<]*\"><span>([^<]+)</span>", html)
    from html import unescape
    choices = defaultdict(set)
    for tid, name in pairs:
        choices[unescape(name).strip()].add(int(tid))
    with sqlite3.connect('file:'+(ROOT/'sources/kor.sqlite').as_posix()+'?mode=ro', uri=True) as db:
        for tid, name in db.execute('SELECT teamid,teamname FROM team'):
            if name not in choices:
                choices[name].add(tid)
    mapping = {name: next(iter(ids)) for name, ids in choices.items() if len(ids) == 1}
    for name, (tid, expected) in manual.EXACT_CLUB_ALIASES.items():
        if display.get(str(tid)) != expected:
            raise RuntimeError('Reviewed club identity changed: ' + name)
        mapping[name] = tid
    # A missing dropdown name can be recovered from the old database only when
    # >=3 distinct players independently agree on one team ID at an unambiguous
    # joining year and loan flag. Keep all conflicts for human review.
    votes = defaultdict(list)
    for record in records:
        career = record['career']
        for spell in career:
            name, year = spell['club_ko'], spell['joinedyear']
            if name in mapping or sum(x['joinedyear'] == year for x in career) != 1:
                continue
            matches = {x[0] for x in old.get(record['playerid'], []) if x[1] == year and x[3] == spell['loan']}
            if len(matches) == 1:
                votes[name].append(dict(playerid=record['playerid'], teamid=next(iter(matches)), joinedyear=year))
    recovered = {}
    for name, items in votes.items():
        ids = {x['teamid'] for x in items}
        if len(ids) == 1 and len({x['playerid'] for x in items}) >= 3:
            tid = next(iter(ids))
            if str(tid) in display:
                mapping[name] = tid
                recovered[name] = dict(teamid=tid, installed_name=display[str(tid)], evidence=items)
    incoming = defaultdict(list)
    provenance = defaultdict(list)
    unresolved = []
    for record in records:
        pid = record['playerid']
        for spell in record['career']:
            tid = mapping.get(spell['club_ko'])
            tid = previous.ALIASES.get(tid, tid)
            if tid is None or str(tid) not in display:
                unresolved.append(dict(playerid=pid, name_ko=record['name_ko'], source_url=record['url'],
                    source_club=spell['club_ko'], teamid=tid,
                    reason='UNMAPPED_CLUB_NAME' if tid is None else 'UNSUPPORTED_CLIENT_CLUB'))
                continue
            incoming[pid].append((tid, spell['joinedyear'], spell['endyear'], spell['loan']))
        provenance[pid].append(dict(type='NEXON_EXACT_PLAYER_ID', url=record['url'],
            fetched_utc=record['fetched_utc'], raw_sha256=record['raw_sha256']))
    for pid, (birthday, person, title, career) in manual.DATA.items():
        expected = datetime.date.fromisoformat(birthday)
        for date, nation in identities[pid]:
            month, day, year = map(int, date.split('/'))
            if datetime.date(year, month, day) != expected:
                raise RuntimeError('Manual identity DOB needs review: ' + str(pid))
            if pid >= 999800 and nation != 155:
                raise RuntimeError('Chinese legacy nationality differs')
        if pid not in identities:
            raise RuntimeError('Manual player absent')
        for tid, start, end, loan in career:
            if str(tid) not in display:
                raise RuntimeError('Manual club not supported: ' + str(tid))
        incoming[pid].extend(career)
        provenance[pid].append(dict(type='REVIEWED_LEGACY_ID', person=person, installed_birthdate=birthday,
            url='https://en.wikipedia.org/wiki/'+title, corroborating_urls=manual.EXTRA_SOURCES.get(pid, []),
            scope='Only explicitly reviewed supported senior clubs; unsupported spells are not fabricated',
            birthyear_discrepancy_preserved=(pid == 999600)))
    edits, changes = {}, []
    for pid, career in sorted(incoming.items()):
        before = old.get(pid, [])
        after = previous.merge(before, career)
        if before != after:
            edits[pid] = after
            changes.append(dict(playerid=pid, before=before, after=after,
                added_club_ids=sorted({r[0] for r in after}-{r[0] for r in before}), evidence=provenance[pid]))
    missing_audit = json.loads((ROOT/'audit.json').read_text('utf8'))
    reviewed_missing = []
    for player in missing_audit['players']:
        if 'NO_HISTORY_ROWS' not in player['issues']:
            continue
        pid = player['playerid']
        if pid in manual.UNSUPPORTED_REVIEWS:
            title, clubs = manual.UNSUPPORTED_REVIEWS[pid]
            reviewed_missing.append(dict(playerid=pid, name=player['name'], status='NO_VERIFIED_INSTALLED_CLUB_ID',
                career_clubs=clubs, source_url='https://en.wikipedia.org/wiki/'+title))
        elif pid in edits:
            reviewed_missing.append(dict(playerid=pid, name=player['name'], status='SUPPORTED_HISTORY_REPAIRED',
                club_ids=sorted({r[0] for r in edits[pid]})))
        else:
            raise RuntimeError('Unaccounted missing-history identity: ' + str(pid))
    report = dict(source_careers=len(records), refreshed_ordinary_legend_careers=137,
        source_record_hashes=evidence_hashes, recovered_club_aliases=recovered, unresolved_source_spells=unresolved,
        changed_players=len(edits), new_player_club_eligibilities=sum(len(x['added_club_ids']) for x in changes),
        rows_before=sum(map(len,old.values())), rows_after=sum(map(len,old.values()))+sum(len(v)-len(old.get(k,[])) for k,v in edits.items()),
        missing_history_review=reviewed_missing, old_eligibilities_preserved=True,
        fc27=dict(source='https://www.ea.com/games/ea-sports-fc/ratings', accessible=True,
            total_items=19789, parsed_initial_items=100,
            use='Current-team cross-check and official team-ID labels only; no complete careers or joining years supplied',
            player_attributes_imported=False),
        completeness='Supported verified additions only; unsupported historical clubs and unmapped spells remain explicit')
    return edits, report, changes


def main():
    out = ROOT/'build'
    if out.exists():
        raise RuntimeError('Build exists; inspect it before rebuilding')
    out.mkdir()
    db_path, archive = SERVER/'gamedata/fifadb.sqlite', CLIENT/'data/data_0.big'
    watched = [db_path,archive,SERVER/'http_config.py',SERVER/'server_display_zh.json',ROOT/'manual.py',ROOT/'prepare.py']
    baseline = {str(p):sha(p) for p in watched}
    edits, report, changes = merged_rows(db_path)
    if not edits:
        raise RuntimeError('No verified changes')
    target=out/'fifadb.sqlite'
    shutil.copyfile(db_path,target)
    with sqlite3.connect(target) as db:
        with db:
            for pid, rows in edits.items():
                db.execute('DELETE FROM playerhistory WHERE playerid=?',(pid,))
                db.executemany('INSERT INTO playerhistory(playerid,ordernum,teamid,joinedyear,endyear,loan) VALUES (?,?,?,?,?,?)',
                    [(pid,i,*r) for i,r in enumerate(rows)])
    previous=load(OLD/'build.py','household_db_verification')
    report.update(previous.verify_tables(target,db_path))
    write(out/'coverage-report.json',report)
    write(out/'player-changes.json',changes)
    write(out/'baseline.json',baseline)
    print(json.dumps(dict(changed_players=report['changed_players'],new_eligibilities=report['new_player_club_eligibilities'],recovered_aliases=len(report['recovered_club_aliases']))),flush=True)
    sys.path.insert(0,str(SERVER/'tools/re'))
    import bigdir,refpack
    codec=load(SERVER/'extract_fifadb.py','household_codec')
    decoded=bytes(codec.decrypt(bigdir.read(archive,MEMBER)))
    if hashlib.sha256(b'SQLite format 3\0'+decoded[16:]).hexdigest()!=baseline[str(db_path)]:
        raise RuntimeError('Installed UI database differs between server and client')
    plain=target.read_bytes()
    from cryptography.hazmat.primitives.ciphers import Cipher,modes
    from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
    encoder=Cipher(Blowfish(codec.KEY),modes.ECB()).encryptor()
    encrypted=codec.swap32(encoder.update(codec.swap32(decoded[:16]+plain[16:]))+encoder.finalize())
    packed=refpack.refpack(encrypted)
    output_big=out/'data_0.big'
    shutil.copyfile(archive,output_big)
    ordered=load(ROOT.parent/'global-player-editor/ordered_big.py','household_ordered')
    ordered.replace_member(output_big,MEMBER,packed,len(encrypted))
    if b'SQLite format 3\0'+bytes(codec.decrypt(bigdir.read(output_big,MEMBER)))[16:]!=plain:
        raise RuntimeError('Encrypted resource round-trip differs')
    layout=load(SERVER/'tools/check_data0_layout.py','household_layout').inspect(output_big,archive,{MEMBER},271)
    if layout['status']!='PASS':
        raise RuntimeError('Resource directory/layout differs')
    write(out/'layout-report.json',layout)
    for path,expected in baseline.items():
        if sha(path)!=expected:
            raise RuntimeError('Production baseline changed while building')
    write(out/'build-result.json',dict(status='BUILT_FOR_DIRECT_INSTALL',database_sha256=sha(target),
        big_sha256=sha(output_big),state_shop_written=False,non_target_members_identical=270,
        changed_players=report['changed_players'],new_player_club_eligibilities=report['new_player_club_eligibilities']))
    print('HOUSEHOLD_BUILD_PASS',flush=True)


if __name__=='__main__':
    main()
