"""Trace all 67 MUL cards and correct only proven import-generated artifacts."""
from pathlib import Path
import hashlib
import json
import sqlite3
import sys

P = Path(__file__).resolve().parent
S = Path('D:/FO3ID/server')
R = Path('D:/fifaol3/manutd-legends')
sys.path[:0] = [str(P.parent / 'manutd-attribute-correction'),
               'D:/fifaol3/npc-peer-market/monotone-retraining-v9']
import build as correction
from predict import MonotoneValueModel
from features import ability_fields

ROLE_REPAIRS = (48167905, 48152908, 48003484)
PREVIOUS_TWO = (48167905, 48152908)


def backup_db(record):
    meta = json.loads(record.read_text('utf8'))
    folder = Path(meta['backup'])
    journal = json.loads((folder / 'transaction.json').read_text('utf8'))
    index = next(i for i, row in enumerate(journal['files'])
                 if row['root'] == 'server' and row['relative'] == 'gamedata/fifadb.sqlite')
    path = folder / str(index)
    expected = journal['files'][index]['before']
    assert correction.sha(path) == expected, 'Original source backup hash differs'
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    return db, dict(path=str(path), sha256=expected, receipt=str(record))


def run():
    model = MonotoneValueModel()
    stats = ability_fields(model.config)
    gk_fields = [field for field in stats if field.startswith('gk')]
    baseline = {str(path): correction.sha(path) for path in
                [S / 'gamedata/fifadb.sqlite', S / 'gamedata/custom_rosters.json']}
    db = sqlite3.connect((S / 'gamedata/fifadb.sqlite').as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    original, first_proof = backup_db(R / 'installed-handback.json')
    expansion, expansion_proof = backup_db(R / 'service-expansion/installed.json')
    initial = {card['fo3_spid']: card for card in json.loads((R / 'roster.json').read_text('utf8'))['cards']}
    organized = Path(json.loads((R / 'season-organize/latest-build.json').read_text('utf8'))['path'])
    steps = {row['spid']: row['stat_shift'] for row in json.loads((organized / 'build.json').read_text('utf8'))['ratings']}
    registry = json.loads((S / 'gamedata/custom_rosters.json').read_text('utf8'))
    metadata = {row['fo3_spid']: row for row in registry['cards']}
    custom = {row['id'] for row in registry['seasons']}
    results = []
    for record in db.execute('SELECT * FROM players WHERE spid/1000000=48 ORDER BY spid'):
        live = dict(record)
        sid = live['spid']
        card = metadata[sid]
        if sid in initial:
            spec = initial[sid]
            source = dict(original.execute('SELECT * FROM players WHERE spid=?', (spec['template_spid'],)).fetchone())
            assert correction.digest(source) == spec['source_row_sha256'], ('Import source row digest differs', sid)
            replay = {field: min(99, max(1, spec['row'][field] + steps[sid])) for field in stats}
            trace = dict(kind='initial_41_then_primary_plus2', initial_shift=spec['stat_shift'],
                         later_global_shift=steps[sid], original_source_digest=spec['source_row_sha256'])
        else:
            source = dict(expansion.execute('SELECT * FROM players WHERE spid=?', (card['template_spid'],)).fetchone())
            replay = {field: min(99, max(1, source[field] + card['stat_shift'])) for field in stats}
            trace = dict(kind='expansion_26_global_shift', initial_shift=card['stat_shift'],
                         later_global_shift=0, original_source_digest=correction.digest(source))
        # The -3/+3 transaction was reversed exactly. Refuse any later unrelated
        # attribute edit rather than replacing it with an old snapshot.
        assert all(live[field] == replay[field] for field in stats), ('Later legitimate attribute change; review before correction', sid)
        assert live['playerid'] == source['playerid']
        role = model.config['position_roles'][live['preferredposition1']]
        after = dict(live)
        selected = source
        shift = None
        reasons = []
        if sid in ROLE_REPAIRS:
            histories = [dict(row) for row in db.execute('SELECT * FROM players WHERE playerid=? AND spid>=1000000', (live['playerid'],))
                         if row['spid'] // 1_000_000 not in custom]
            after, selected, shift, _ = correction.corrected_row(live, histories, model.config)
            reasons.append('wrong_role_source_and_unrelated_global_boost')
        elif role != 'GK':
            # Do not reset the intended legend uplift in the 28 outfield
            # abilities. Remove only the trace-proven, incidental GK increase.
            # Never increase a GK stat that was deliberately lowered.
            for field in gk_fields:
                if after[field] > source[field]:
                    after[field] = source[field]
            if after != live:
                reasons.append('mechanical_non_role_GK_increase')
        weights = model.config['role_weights'][role]
        score = lambda row: sum(row[k] * w for k, w in weights.items()) // 100
        assert score(live) == score(after)
        assert all(after[k] == value for k, value in live.items() if k not in stats)
        if sid not in ROLE_REPAIRS:
            assert all(after[k] == live[k] for k in stats if k not in gk_fields)
        name = db.execute('SELECT short FROM nameschi WHERE playerid=?', (live['playerid'],)).fetchone()[0]
        results.append(dict(spid=sid, name=name, role=role,
            scope='previous_two' if sid in PREVIOUS_TWO else 'remaining65',
            status='CORRECT' if after != live else 'KEEP', reasons=reasons,
            original_template_spid=card['template_spid'], source_trace=trace, all_33_replay_exact=True,
            source_row=source, selected_source=selected, role_shift=shift,
            before_row=live, after_row=after, primary_before=score(live), primary_after=score(after),
            changes={field: [live[field], after[field]] for field in stats if live[field] != after[field]},
            retained_99_fields=[field for field in stats if live[field] == after[field] == 99],
            old_value=model.predict(live), new_value=model.predict(after)))
    assert len(results) == 67 and sum(row['scope'] == 'remaining65' for row in results) == 65
    assert baseline == {path: correction.sha(path) for path in baseline}, 'Official input changed during audit'
    for connection in [db, original, expansion]:
        connection.close()
    report = dict(status='ALL67_TRACE_REPLAY_PASS', reviewed=67, remaining_reviewed=65,
        corrected=sum(row['status'] == 'CORRECT' for row in results),
        remaining_corrected=sum(row['status'] == 'CORRECT' and row['scope'] == 'remaining65' for row in results),
        unchanged=sum(row['status'] == 'KEEP' for row in results),
        policy='Only three proven wrong-role source repairs plus incidental non-role GK boosts; retain all other 28-outfield-ability legend improvements, specialist 99 peaks, all primary integer ratings and non-stat metadata.',
        all_primary_ratings_preserved=True, source_backups=[first_proof, expansion_proof], baseline=baseline,
        model_sha256=model.sha256, rows=results, formal_written=False, state_shop_written=False)
    correction.save(P / 'audit.json', report)
    return report


if __name__ == '__main__':
    report = run()
    print(json.dumps({key: value for key, value in report.items() if key not in ['rows', 'baseline']}, ensure_ascii=False))
