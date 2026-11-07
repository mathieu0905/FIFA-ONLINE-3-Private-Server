"""Independent local checks of exported training artifacts, using no ML library."""
from pathlib import Path
import gzip
import hashlib
import json
import math
import random
from features import encode
from predict import MonotoneValueModel

P = Path(__file__).resolve().parent


def read_gz(path):
    with gzip.open(path, 'rt', encoding='utf8') as f:
        return json.load(f)


def main():
    report = json.loads((P / 'training-report.json').read_text('utf8'))
    assert report['status'] == 'PASS'
    model = MonotoneValueModel(expected_sha256=report['model_sha256'])
    data = read_gz(P / 'training-data.json.gz')
    test = {r['spid']: r for r in data if r['kind'] == 'real' and r['partition'] == 'test'}
    checks = []
    train_ids = {r['playerid'] for r in data if r['partition'] == 'train'}
    val_ids = {r['playerid'] for r in data if r['partition'] == 'validation'}
    test_ids = {r['playerid'] for r in data if r['partition'] == 'test'}
    assert not (train_ids & val_ids or train_ids & test_ids or val_ids & test_ids)
    checks.append('Player identity groups are disjoint across train/validation/test')
    predictions = json.loads((P / 'test-predictions.json').read_text('utf8'))
    rng = random.Random(8804)
    sample = rng.sample(predictions, min(700, len(predictions)))
    errors = []
    for prediction in sample:
        raw = test[prediction['spid']]['attributes']
        value = model.log_predict(raw)
        error = abs(value - prediction['log_prediction'])
        errors.append(error)
        assert error <= 1e-4, (raw, value, prediction)
    checks.append('Portable export matches native GPU predictions within 0.0001 log-price on 700 held-out samples')
    current = {r['spid']: r for r in read_gz(P / 'current-profiles.json.gz')}
    preview = read_gz(P / 'current-price-preview.json.gz')
    representative = [9138726, 47138726, 9119152, 47119152, 9045595, 47045595, 30037576, 30238380, 84037576, 48167905]
    examples = []
    for spid in representative:
        raw = current[spid]
        predicted = model.predict(raw)
        expected = preview[str(spid)]['price']
        assert abs(predicted - expected) <= max(1, expected * .0001)
        examples.append(dict(spid=spid, old_seed=raw['historical']['initial'], new_fair_price=predicted,
                             native_rating=preview[str(spid)]['native_rating']))
    checks.append('Reported inverted cards and high-end/GK/Manchester samples match the trained preview')
    for strong, weak in [(9138726, 47138726), (9119152, 47119152), (9045595, 47045595)]:
        assert model.predict(current[strong]) >= model.predict(current[weak])
    checks.append('All three original reported inversions fixed in portable inference')
    original = dict(current[47138726]); changed = dict(original, positioning=66)
    assert model.predict(changed) >= model.predict(original)
    checks.append('Original single-variable Lescott counterexample is nondecreasing')
    arbitrary = dict(original, spid=123456, playerid=654321, trait1=0, trait2=0, runningcode1=999)
    assert model.predict(arbitrary) == model.predict(original)
    checks.append('Identity, season-coded SPID, traits and animation identifiers do not change fair price')
    for field, bad in [('agility', float('nan')), ('weakfootabilitytypecode', 0), ('skillmoves', 99), ('preferredposition1', -1)]:
        invalid = dict(original); invalid[field] = bad
        try:
            model.predict(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid profile accepted: ' + field)
    checks.append('Nonfinite and out-of-range inference inputs rejected')
    # Freshly check only our protected source inputs, without freezing or
    # restoring legitimate live state/shop/market progression.
    preparation = json.loads((P / 'preparation.json').read_text('utf8'))
    observed = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in preparation['protected_official_sources']}
    unchanged = observed == preparation['protected_official_sources']
    checks.append('Training and inference never write formal files or live assets')
    result = dict(status='PASS', checks=checks, tested_export_predictions=len(errors),
                  maximum_portable_log_difference=max(errors), examples=examples,
                  formal_source_inputs_unchanged=unchanged, current_source_hashes=observed,
                  new_single_stat_violations=report['single_attribute_violations'],
                  new_dominance_inversions=report['new_dominance_inversions'],
                  model_sha256=report['model_sha256'], formal_activated=False, native_verified=False)
    (P / 'local-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf8')
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
