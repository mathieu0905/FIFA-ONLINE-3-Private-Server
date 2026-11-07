"""Regress the demonstrated template-selection bug without official writes."""
from pathlib import Path
import copy
import json
import sqlite3
import sys

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import build
from predict import MonotoneValueModel
from features import ability_fields


def main():
    latest = json.loads((P / 'latest-build.json').read_text('utf8'))
    output = Path(latest['path'])
    report = json.loads((output / 'report.json').read_text('utf8'))
    model = MonotoneValueModel()
    checks = []
    for item in report['changes']:
        before, source, expected = item['before_row'], item['source_row'], item['after_row']
        original = copy.deepcopy(before)
        wrong_role = dict(source, spid=item['original_import_template_spid'], preferredposition1=12, overallrating=255)
        current, selected, shift, rating = build.corrected_row(before, [wrong_role, source], model.config)
        assert selected['spid'] == item['corrected_source_spid'] and current == expected
        assert before == original
        checks.append('Prefer verified FB source over a higher-overall wrong-role row: ' + str(item['spid']))
        again, _, _, _ = build.corrected_row(current, [source], model.config)
        assert again == current
        checks.append('Repeat correction is idempotent: ' + str(item['spid']))
        for choices in [[wrong_role], [dict(source, playerid=source['playerid'] + 1)]]:
            try:
                build.corrected_row(before, choices, model.config)
            except ValueError:
                pass
            else:
                raise AssertionError('Wrong person/role source was accepted')
        checks.append('Wrong-person or wrong-role fallback refused: ' + str(item['spid']))
        fields = ability_fields(model.config)
        assert all(current[k] == before[k] for k in current if k not in fields)
        assert model.predict(current) == item['new_value']
        assert item['primary_integer_rating_before'] == item['primary_integer_rating_after'] == 86
        assert item['new_99_count'] == 0
        checks.append('Identity/body/positions/foot/skill unchanged, primary86 retained and new value reproducible: ' + str(item['spid']))
    # Read the staged rows independently, not merely the construction report.
    with sqlite3.connect((output / 'fifadb.sqlite').as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        for item in report['changes']:
            assert dict(db.execute('SELECT * FROM players WHERE spid=?', (item['spid'],)).fetchone()) == item['after_row']
    assert report['layout_status'] == 'PASS' and report['player_import_full_status'] == 'PLAYER_IMPORT_FULL_PASS'
    checks.append('Independent staged-row readback, ordered BIG layout and full player_import checks pass')
    result = dict(status='PASS', checks=checks, formal_written=False, state_shop_written=False,
                  native_verified=False, target_build=str(output), scope='Two proven template inflations only')
    (P / 'regression.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
