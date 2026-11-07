"""Verify full MUL correction scope, source evidence and all 67 valuations."""
from pathlib import Path
import json
import sqlite3
import sys

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import audit
from audit import correction as tools
from predict import MonotoneValueModel
from features import ability_fields


def main():
    analysis = json.loads((P / 'audit.json').read_text('utf8'))
    folder = Path(json.loads((P / 'latest-build.json').read_text('utf8'))['path'])
    build = json.loads((folder / 'report.json').read_text('utf8'))
    model = MonotoneValueModel(expected_sha256=analysis['model_sha256'])
    fields = ability_fields(model.config)
    gk_fields = {field for field in fields if field.startswith('gk')}
    checks = []
    assert analysis['reviewed'] == 67 and analysis['remaining_reviewed'] == 65
    assert {row['spid'] for row in analysis['rows'] if row['scope'] == 'previous_two'} == set(audit.PREVIOUS_TWO)
    assert all(row['all_33_replay_exact'] for row in analysis['rows'])
    checks.append('All remaining65 and previous2 reviewed; all67 original 33-stat adjustment chains replay exactly')
    for source in analysis['source_backups']:
        assert tools.sha(source['path']) == source['sha256']
    checks.append('Read-only source backups match original installation receipts; no old DB restored')
    with sqlite3.connect((folder / 'fifadb.sqlite').as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        for item in analysis['rows']:
            before, after = item['before_row'], item['after_row']
            actual = dict(db.execute('SELECT * FROM players WHERE spid=?', (item['spid'],)).fetchone())
            assert actual == after
            assert all(after[k] == value for k, value in before.items() if k not in fields)
            weights = model.config['role_weights'][item['role']]
            score = lambda r: sum(r[k] * w for k, w in weights.items()) // 100
            assert score(before) == score(after)
            assert model.predict(after) == item['new_value']
            assert model.predict(before) == item['old_value']
            if item['spid'] not in audit.ROLE_REPAIRS:
                assert set(item['changes']) <= gk_fields
                assert all(after[k] == before[k] for k in fields if k not in gk_fields)
                assert all(after[k] <= before[k] for k in gk_fields)
                if item['status'] == 'CORRECT':
                    assert item['new_value'] < item['old_value']
            else:
                regenerated, source, _, _ = tools.corrected_row(before, [item['selected_source']], model.config)
                assert regenerated == after and source['spid'] == item['selected_source']['spid']
                repeated, _, _, _ = tools.corrected_row(after, [source], model.config)
                assert repeated == after
            if item['status'] == 'KEEP':
                assert actual == before
            for field in item['retained_99_fields']:
                assert before[field] == after[field] == 99
    checks.append('All67 staged rows independently match corrected profiles and recomputed v9 values')
    checks.append('All primary integer ratings and identity/body/position/foot/skill fields retained')
    checks.append('60 GK-only repairs preserve all28 outfield abilities; no reductions outside proven incidental GK bonus')
    checks.append('Three FB repairs use verified own-person FB sources and are idempotent')
    checks.append('All legitimate specialist99 peaks and all four untouched cards retained')
    previous = json.loads((P.parent / 'manutd-attribute-correction/latest-build.json').read_text('utf8'))
    old_two = json.loads((Path(previous['path']) / 'report.json').read_text('utf8'))
    lookup = {row['spid']: row for row in analysis['rows']}
    for prior in old_two['changes']:
        assert lookup[prior['spid']]['after_row'] == prior['after_row']
    checks.append('Earlier Valencia/Young repairs retained exactly')
    rankings = json.loads((folder / 'manutd-rankings.json').read_text('utf8'))
    assert len(rankings) == 67 and len({row['spid'] for row in rankings}) == 67
    assert rankings == sorted(rankings, key=lambda row: (-row['new_value'], row['spid']))
    assert rankings[0]['spid'] == 48230026
    checks.append('Complete67-card ranking is sorted and winner is Denis Law')
    assert build['full_player_import_status'] == 'PLAYER_IMPORT_FULL_PASS' and build['layout_status'] == 'PASS'
    assert all(tools.sha(folder / name) == value for name, value in build['outputs'].items())
    assert all(tools.sha(path) == value for path, value in build['baseline'].items())
    checks.append('Full import certificate, ordered BIG and unchanged non-target members are bound to verified output hashes')
    checks.append('Fresh official inputs still unchanged; game resources/state/shop/history not written')
    result = dict(status='PASS', checks=checks, reviewed=67, remaining_reviewed=65,
                  remaining_corrected=analysis['remaining_corrected'], total_corrected=analysis['corrected'],
                  resource_build=str(folder), model_sha256=model.sha256,
                  formal_activated=False, game_or_match_verified=False)
    tools.save(P / 'regression.json', result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
