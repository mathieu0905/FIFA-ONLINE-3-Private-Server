"""Independently verify identity-history protocol and portable model behavior."""
from pathlib import Path
import gzip
import json
import math
import random
import statistics
from predict import IdentityValueModel
from features import ability_fields

P = Path(__file__).resolve().parent
B = P.with_name('anchor-retraining-v10')


def readgz(path):
    with gzip.open(path, 'rt', encoding='utf8') as file:
        return json.load(file)


def main():
    report = json.loads((P/'training-report.json').read_text('utf8'))
    assert report['status']=='PASS'
    model = IdentityValueModel(expected_sha256=report['model_sha256'])
    backbone = readgz(B/'selected-model.json.gz')
    assert model.model['experts']==backbone['experts']
    checks = ['Final identity model retains the separately GPU-trained, audited anchor ability experts']
    data = readgz(B/'training-data.json.gz')
    real = {r['spid']:r for r in data if r['kind']=='real'}
    quote = {r['spid']:r for r in json.loads((P/'quote-predictions.json').read_text('utf8'))}
    assert sum(p['real_quotes'] for p in model.priors.values())==len(real)==17842
    assert len(model.priors)==report['learned_identities']
    checks.append('Identity table evidence consists of all17842 real quotes; synthetic labels do not create name priors')
    cases = json.loads((P/'known-test-cases.json').read_text('utf8'))
    base_errors, adjusted_errors = [], []
    lam = model.config['identity_prior']['regularization']
    cap = model.config['identity_prior']['maximum_factor']
    grouped = {}
    for spid, row in real.items():
        grouped.setdefault(row['playerid'], []).append(row)
    for pid, rows in grouped.items():
        seasons = {}
        for row in rows:
            seasons.setdefault(row['spid']//1000000, []).append(math.log(row['price'])-quote[row['spid']]['final_base_log'])
        evidence = len(seasons)+(2 if any(row['calibration_anchor'] for row in rows) else 0)
        shift = statistics.median(statistics.median(values) for values in seasons.values())*evidence/(evidence+lam)
        shift = min(math.log(cap),max(-math.log(cap),shift))
        assert abs(shift-model.priors[str(pid)]['log_multiplier'])<1e-10
    checks.append('Every final player prior fits the deployed backbone residual, avoiding double counting the larger OOF error')
    for case in cases:
        target = real[case['target_spid']]
        history = [real[sid] for sid in case['history_spids']]
        assert target['partition']=='test' and case['target_spid'] not in case['history_spids']
        assert all(r['playerid']==target['playerid'] and r['partition']=='test' and r['spid']//1000000 != target['spid']//1000000 for r in history)
        season_values = {}
        for r in history:
            season_values.setdefault(r['spid']//1000000,[]).append(math.log(r['price'])-quote[r['spid']]['generic_log'])
        evidence = len(season_values)+(2 if any(r['calibration_anchor'] for r in history) else 0)
        shift = statistics.median(statistics.median(values) for values in season_values.values())*evidence/(evidence+lam)
        shift = min(math.log(cap),max(-math.log(cap),shift))
        assert abs(shift-case['prior_log'])<1e-10
        base_errors.append(abs(math.log(target['price'])-case['base_log']))
        adjusted_errors.append(abs(math.log(target['price'])-case['base_log']-shift))
    assert len(cases)==report['known_test']['cases']
    assert abs(statistics.mean(base_errors)-report['known_test']['base']['log_mae'])<1e-10
    assert abs(statistics.mean(adjusted_errors)-report['known_test']['with_identity']['log_mae'])<1e-10
    assert statistics.mean(adjusted_errors)<statistics.mean(base_errors)
    checks.append('All570 known-history tests independently recomputed: target season quote excluded, same-player other seasons only')
    current = readgz(B/'current-profiles.json.gz')
    preview = readgz(P/'current-price-preview.json.gz')
    rng = random.Random(11042)
    sample = rng.sample(current,700)
    maximum_relative=0.
    for row in sample:
        expected=preview[str(row['spid'])]['price'];actual=model.predict(row)
        relative=abs(actual-expected)/max(1,expected)
        maximum_relative=max(maximum_relative,relative)
        assert abs(actual-expected)<=max(1,expected*.0001)
    checks.append('Portable inference agrees with native-GPU final price link on700 roster profiles within0.01%')
    strict=0
    for row in sample[:30]:
        base=model.predict(row)
        for field in ability_fields(model.config):
            if row[field]>=255:continue
            increased=dict(row);increased[field]+=1
            assert model.predict(increased)>=base+1,(row['spid'],field)
            strict+=1
        for field,upper in [('weakfootabilitytypecode',5),('skillmoves',4)]:
            if row[field]<upper:
                increased=dict(row);increased[field]+=1
                assert model.predict(increased)>=base+25,(row['spid'],field)
                strict+=1
        alias=dict(row,name='任意中文名',name_eng='Alias',preferredposition1=27,height=200,weight=100)
        assert model.predict(alias)==base
        different_season=dict(row,spid=77_000_000+row['playerid'])
        assert model.identity_prior(different_season)==model.identity_prior(row)
    checks.append('Independent strict increases, same-identity cross-season factor and display-name aliases verified')
    known=next(row for row in current if model.identity_prior(row)['real_quotes']>=5)
    unknown_id=999999
    while str(unknown_id) in model.priors:unknown_id-=1
    unknown=dict(known,playerid=unknown_id,spid=13_000_000+unknown_id)
    anonymous={k:v for k,v in unknown.items() if k not in ('playerid','spid')}
    assert model.identity_prior(unknown)['multiplier']==1.
    assert model.predict(unknown)==model.predict(anonymous)
    try:
        model.predict(dict(known,playerid=unknown_id))
    except ValueError:pass
    else:raise AssertionError('Mismatched player/card identity accepted')
    checks.append('Unseen players use factor1, without fame penalty; mismatched card/player identities refused')
    low={field:-3 for field in ability_fields(model.config)}|{'weakfootabilitytypecode':1,'skillmoves':0}
    high={field:255 for field in ability_fields(model.config)}|{'weakfootabilitytypecode':5,'skillmoves':4}
    assert model.predict(low)>1
    upper_source=math.exp(model.log_predict(high))*cap/model.config['source_price_divisor']
    assert upper_source<5_600_000_000_000_000
    assert not report['strict_failures'] and not report['dominance_failures']
    checks.append('Full2128493 native-GPU strict checks and21563 same-player dominance pairs remain valid')
    result=dict(status='PASS',checks=checks,known_history_cases=len(cases),
                strict_local_cases=strict,maximum_portable_price_relative_difference=maximum_relative,
                known_test_base_log_mae=statistics.mean(base_errors),known_test_prior_log_mae=statistics.mean(adjusted_errors),
                prior_cap=cap,model_sha256=model.sha256,formal_activated=False,native_or_match_verified=False)
    (P/'local-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
