"""Read-only production club eligibility audit; writes evidence beside this script only."""
import ast
import collections
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SERVER = Path('D:/FO3ID/server')
CAREERS = Path('D:/fifaol3/club-history')
LEGEND_CODES = {93, 30, 27, 71, 51, 61, 89, 48, 55, 49}
if '--expanded' in sys.argv:
    LEGEND_CODES.update({12,19})


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    db_path = SERVER / 'gamedata/fifadb.sqlite'
    baseline = {str(p): digest(p) for p in [db_path, SERVER / 'http_config.py']}
    builder = load(CAREERS / 'build.py', 'household_existing_builder')
    collector = load(CAREERS / 'collect.py', 'household_existing_collector')
    mapping = builder.club_map()
    supported = json.loads((SERVER / 'server_display_zh.json').read_text('utf8'))['names_by_id']['TEAMNAMES_CHI.json']
    prices = {int(k) for k in json.loads((SERVER / 'gamedata/fa_prices.json').read_text('utf8'))}
    with sqlite3.connect('file:' + db_path.as_posix() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        market = {r[0] for r in db.execute('SELECT p.spid FROM players p JOIN permid m ON m.spid=p.spid AND m.transferable=1 WHERE p.spid>=1000000 AND p.playerid IN (SELECT playerid FROM namesind)')} | prices
        rows = [dict(r) for r in db.execute('SELECT spid,playerid,teamid FROM players') if r['spid'] in market and r['spid'] // 1000000 in LEGEND_CODES]
        names = {r['playerid']: r['full_eng'] for r in db.execute('SELECT playerid,full_eng FROM namesind')}
        all_cards = collections.defaultdict(list)
        for r in db.execute('SELECT spid,playerid,teamid FROM players WHERE spid>=1000000'):
            all_cards[r['playerid']].append(dict(r))
        histories = collections.defaultdict(set)
        for pid, tid in db.execute('SELECT DISTINCT playerid,teamid FROM playerhistory'):
            histories[pid].add(tid)
        history_size = dict(rows=db.execute('SELECT COUNT(*) FROM playerhistory').fetchone()[0], players=len(histories))
    grouped = collections.defaultdict(list)
    for row in rows:
        grouped[row['playerid']].append(row)
    players = []
    for pid, cards in sorted(grouped.items()):
        record_path = CAREERS / 'records' / f'{pid}.json'
        record = json.loads(record_path.read_text('utf8')) if record_path.exists() else {}
        issues, source_clubs, unresolved = [], set(), []
        if not histories[pid]:
            issues.append('NO_HISTORY_ROWS')
        if record.get('status') == 'OK':
            raw = gzip.decompress(Path(record['raw_file']).read_bytes())
            if hashlib.sha256(raw).hexdigest() != record['raw_sha256']:
                raise RuntimeError(f'Career evidence hash differs: {pid}')
            if collector.parse(raw.decode('utf-8-sig')) != record['career']:
                raise RuntimeError(f'Career parse differs: {pid}')
            if int(record['source_spid']) % 1000000 != pid:
                raise RuntimeError(f'Career identity differs: {pid}')
            for career in record['career']:
                tid = mapping.get(career['club_ko'])
                if tid is None:
                    unresolved.append(dict(reason='UNMAPPED_CLUB_NAME', career=career))
                    continue
                tid = builder.ALIASES.get(tid, tid)
                if str(tid) not in supported:
                    unresolved.append(dict(reason='UNSUPPORTED_CLIENT_CLUB', teamid=tid, career=career))
                    continue
                source_clubs.add(tid)
            missing = source_clubs - histories[pid]
            if missing:
                issues.append('MAPPED_SOURCE_CLUB_MISSING_FROM_HISTORY')
        else:
            missing = set()
            issues.append('NO_VERIFIED_CACHED_CAREER')
        if unresolved:
            issues.append('SOURCE_CLUB_MAPPING_UNRESOLVED')
        # This models production's actual per-card current-club + identity-history union.
        eligibility = {r['spid']: sorted(histories[pid] | {r['teamid']}) for r in all_cards[pid]}
        unequal = len({tuple(v) for v in eligibility.values()}) > 1
        if unequal:
            issues.append('CARD_CURRENT_CLUB_CAUSES_CROSS_SEASON_DIFFERENCE')
        players.append(dict(playerid=pid, name=names.get(pid), legend_cards=cards,
            history_clubs=sorted(histories[pid]), source_status=record.get('status', 'NO_RECORD'),
            source_url=record.get('url'), source_clubs=sorted(source_clubs),
            mapped_source_missing_clubs=sorted(missing), unresolved=unresolved, issues=issues,
            cross_season_current_clubs=sorted({r['teamid'] for r in all_cards[pid]}),
            eligibility_by_spid=eligibility))
    counts = collections.Counter(issue for p in players for issue in p['issues'])
    result = dict(status='READ_ONLY_AUDIT_COMPLETE_NOT_A_COMPLETENESS_CERTIFICATE',
        formal_files_written=False, state_shop_written=False, services_action=False, gui_used=False,
        baseline=baseline, history=history_size, legend_cards=len(rows), legend_identities=len(players),
        source_status=dict(collections.Counter(p['source_status'] for p in players)),
        issue_counts=dict(counts), players=players,
        interpretation=[
            'An empty history does not mean a card lacks every club: its own current teamid still counts.',
            'Current-card team IDs may be all-star placeholders and are not authoritative career evidence.',
            'Cross-season differences are review candidates, not proof that each listed club is genuine.',
            'Verified cached source coverage is not proof of complete real-world senior careers.',
            'Existing eligibilities must be preserved; playing and coaching/academy careers must not be conflated.',
            'Nationalities and club histories are separate mechanisms; club spelling/team-ID aliases require evidence.',
        ])
    for path, expected in baseline.items():
        if digest(Path(path)) != expected:
            raise RuntimeError('Production baseline changed during audit; rerun: ' + path)
    (ROOT / ('audit-expanded.json' if '--expanded' in sys.argv else 'audit.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('players','interpretation')}, ensure_ascii=True))


if __name__ == '__main__':
    main()
