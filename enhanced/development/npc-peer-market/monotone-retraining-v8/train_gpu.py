"""GPU XGBoost with hard monotonic constraints and grouped held-out evaluation.

Remote training uses only this run directory. No production path is writable
or even present. Test identities never choose features, iterations or settings.
"""
from pathlib import Path
import os
os.environ.setdefault('OMP_NUM_THREADS', '4')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
import collections
import gzip
import hashlib
import json
import math
import resource
import subprocess
import sys
import time

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P / 'deps'))
import numpy as np
import xgboost as xgb
from features import encode, schema, local_price, role_rating


def read_gz(name):
    with gzip.open(P / name, 'rt', encoding='utf8') as f:
        return json.load(f)


def save(name, obj):
    (P / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), 'utf8')


def metric(y, pred):
    e = np.abs(y - pred)
    return dict(rows=len(e), log_mae=float(e.mean()), median_error_factor=float(np.exp(np.median(e))),
                within_2x=float((e <= math.log(2)).mean()), within_3x=float((e <= math.log(3)).mean()),
                p90_error_factor=float(np.exp(np.quantile(e, .9))))


def main():
    started = time.monotonic()
    config = json.loads((P / 'config.json').read_text('utf8'))
    data = read_gz('training-data.json.gz')
    current = read_gz('current-profiles.json.gz')
    train_ids = {r['playerid'] for r in data if r['partition'] == 'train'}
    val_ids = {r['playerid'] for r in data if r['partition'] == 'validation'}
    test_ids = {r['playerid'] for r in data if r['partition'] == 'test'}
    assert not (train_ids & val_ids or train_ids & test_ids or val_ids & test_ids)
    assert not any(r['kind'] != 'real' and r['partition'] == 'test' for r in data)
    enc = [encode(r['attributes'], config) for r in data]
    y = np.log([r['price'] for r in data])
    # Hard constraints are present in every candidate eligible for selection.
    # The unconstrained ablation is comparison evidence only, never selected.
    candidates = [dict(name='constrained_real_depth4', depth=4, augmented=False, rounds=700, l2=15),
                  dict(name='constrained_augmented_depth4', depth=4, augmented=True, rounds=900, l2=15),
                  dict(name='constrained_augmented_depth6', depth=6, augmented=True, rounds=900, l2=25),
                  dict(name='unconstrained_control', depth=4, augmented=True, rounds=700, l2=15, control=True)]
    print('START', json.dumps(dict(rows=len(data), profiles=len(current), xgboost=xgb.__version__,
                                  gpu=os.environ.get('CUDA_VISIBLE_DEVICES'), groups=[len(train_ids), len(val_ids), len(test_ids)])), flush=True)
    all_results = {}
    family_data = {}
    for family in ['GK', 'OUTFIELD']:
        indices = np.array([i for i, (f, _) in enumerate(enc) if f == family])
        X = np.asarray([enc[i][1] for i in indices], dtype=np.float32)
        names, constraints = schema(config, family)
        by_global = {i: j for j, i in enumerate(indices)}
        dm_all = xgb.DMatrix(X, feature_names=names)
        family_data[family] = (indices, X, names, constraints)
        results = {}
        for candidate in candidates:
            tr = [by_global[i] for i in indices if data[i]['partition'] == 'train' and (candidate['augmented'] or data[i]['kind'] == 'real')]
            va = [by_global[i] for i in indices if data[i]['partition'] == 'validation' and data[i]['kind'] == 'real']
            train_global, val_global = indices[tr], indices[va]
            # Real observations have weight 1; declared synthetic training
            # priors have weight .35. No season/hype weight in the real labels.
            weights = np.array([1. if data[i]['kind'] == 'real' else .35 for i in train_global])
            dtrain = xgb.DMatrix(X[tr], label=y[train_global], weight=weights, feature_names=names)
            dval = xgb.DMatrix(X[va], label=y[val_global], feature_names=names)
            params = dict(device='cuda:0', tree_method='hist', objective='reg:squarederror',
                          eval_metric='mae', max_depth=candidate['depth'], max_bin=512,
                          eta=.04, min_child_weight=12, reg_lambda=candidate['l2'], reg_alpha=.5,
                          subsample=1., colsample_bytree=1., nthread=4, seed=8041,
                          monotone_constraints=tuple([0] * len(names) if candidate.get('control') else constraints))
            booster = xgb.train(params, dtrain, num_boost_round=candidate['rounds'],
                                evals=[(dval, 'validation')], early_stopping_rounds=70, verbose_eval=100)
            booster = booster[:booster.best_iteration + 1]
            runtime_config = json.loads(booster.save_config())
            actual_device = runtime_config['learner']['generic_param']['device']
            assert actual_device.startswith('cuda'), 'Silent CPU fallback is not accepted'
            pred = booster.predict(dm_all)
            validation = metric(y[val_global], pred[va])
            high = [j for j in va if data[indices[j]]['ovr'] >= (80 if family == 'GK' else 82) or data[indices[j]].get('season') in (30, 93)]
            high_score = metric(y[indices[high]], pred[high]) if high else None
            score = validation['log_mae'] + .25 * (high_score['log_mae'] if high_score else validation['log_mae'])
            model_file = family + '-' + candidate['name'] + '.json'
            booster.save_model(P / model_file)
            results[candidate['name']] = dict(validation=validation, high_validation=high_score,
                                               selection_score=score, iterations=len(booster.get_dump()),
                                               device=actual_device, model=model_file, candidate=candidate)
            print('CANDIDATE_DONE', family, candidate['name'], json.dumps(results[candidate['name']]), flush=True)
            save('progress.json', dict(family=family, latest=candidate['name'], completed=results, elapsed=time.monotonic() - started))
        all_results[family] = results
    selected_names = {family: min((name for name in result if name.startswith('constrained_')),
                                  key=lambda name: result[name]['selection_score']) for family, result in all_results.items()}
    models = {}
    report = dict(status='TRAINED_EVALUATING', selected=selected_names, selection_uses_test=False,
                  candidates=all_results, hard_monotonic_constraints=True,
                  synthetic_warning='Explicit previous game-design priors, not observed trades; never used as test labels',
                  production_changed=False, gpu=os.environ.get('CUDA_VISIBLE_DEVICES'), xgboost=xgb.__version__)
    final_predictions = np.empty(len(data))
    control_predictions = np.empty(len(data))
    for family, chosen in selected_names.items():
        indices, X, names, constraints = family_data[family]
        candidate = all_results[family][chosen]['candidate']
        # Refit once on train+validation groups at the selected iteration count.
        outer = [j for j, i in enumerate(indices) if data[i]['partition'] != 'test' and (candidate['augmented'] or data[i]['kind'] == 'real')]
        weights = [1. if data[indices[j]]['kind'] == 'real' else .35 for j in outer]
        params = dict(device='cuda:0', tree_method='hist', objective='reg:squarederror',
                      eval_metric='mae', max_depth=candidate['depth'], max_bin=512, eta=.04,
                      min_child_weight=12, reg_lambda=candidate['l2'], reg_alpha=.5,
                      subsample=1., colsample_bytree=1., nthread=4, seed=8041,
                      monotone_constraints=tuple(constraints))
        model = xgb.train(params, xgb.DMatrix(X[outer], label=y[indices[outer]], weight=weights, feature_names=names),
                          num_boost_round=all_results[family][chosen]['iterations'])
        model.save_model(P / ('final-' + family + '.json'))
        models[family] = model
        final_predictions[indices] = model.predict(xgb.DMatrix(X, feature_names=names))
        control = xgb.Booster(model_file=P / all_results[family]['unconstrained_control']['model'])
        control_predictions[indices] = control.predict(xgb.DMatrix(X, feature_names=names))
    test = np.array([i for i, r in enumerate(data) if r['partition'] == 'test' and r['kind'] == 'real'])
    gk_test = np.array([i for i in test if data[i]['attributes']['preferredposition1'] == 0])
    high_test = np.array([i for i in test if data[i]['ovr'] >= 82 or data[i].get('season') in (30, 93)])
    top_gk_test = np.array([i for i in gk_test if data[i]['ovr'] >= 80 or data[i].get('season') in (30, 93)])
    report['real_test'] = {name: metric(y[ix], final_predictions[ix]) for name, ix in [('overall', test), ('goalkeepers', gk_test), ('high', high_test), ('top_goalkeepers', top_gk_test)] if len(ix)}
    report['unconstrained_control_test'] = metric(y[test], control_predictions[test])
    report['test_by_role'] = {role: metric(y[ix], final_predictions[ix]) for role in sorted(set(config['position_roles']))
                              if len(ix := np.array([i for i in test if config['position_roles'][data[i]['attributes']['preferredposition1']] == role]))}
    # Native booster format is retained along with a self-contained numeric
    # tree export. Production does not need the training libraries or a GPU.
    export = dict(schema=1, type='monotone_role_xgboost', config=config, families={})
    for family, model in models.items():
        raw = json.loads(model.save_raw(raw_format='json'))
        learner = raw['learner']
        base = learner['learner_model_param']['base_score']
        base = float(json.loads(base)[0]) if base.startswith('[') else float(base)
        trees = learner['gradient_booster']['model']['trees']
        export['families'][family] = dict(features=schema(config, family)[0],
                                          monotone_constraints=schema(config, family)[1],
                                          baseline=base, trees=trees)
    with gzip.open(P / 'selected-model.json.gz', 'wt', encoding='utf8') as f:
        json.dump(export, f, separators=(',', ':'))
    save('test-predictions.json', [dict(spid=data[i]['spid'], playerid=data[i]['playerid'],
                                     price=data[i]['price'], log_prediction=float(final_predictions[i])) for i in test])
    # Exhaustive current-roster one-stat increases, on the actual trained GPU
    # boosters. Output prices also include the disclosed monotone low-price guard.
    predictions = {}
    monotonic_checks = 0
    violations = []
    control_violations = 0
    for family, model in models.items():
        profiles = [r for r in current if encode(r, config)[0] == family]
        X = np.asarray([encode(r, config)[1] for r in profiles], dtype=np.float32)
        names = schema(config, family)[0]
        original = model.predict(xgb.DMatrix(X, feature_names=names))
        control = xgb.Booster(model_file=P / all_results[family]['unconstrained_control']['model'])
        control_original = control.predict(xgb.DMatrix(X, feature_names=names))
        for raw, log in zip(profiles, original):
            predictions[raw['spid']] = dict(price=local_price(float(log), raw, config), log_price=float(log),
                                             native_rating=role_rating(raw, config))
        stats = [name for name, constraint in zip(*schema(config, family)) if constraint == 1 and name != 'native_role_rating']
        for field in stats:
            changed = []
            chosen_profiles = []
            original_indices = []
            for j, raw in enumerate(profiles):
                ceiling = 5 if field in ('skillmoves', 'weakfootabilitytypecode') else (250 if field == 'height' else 255)
                if raw[field] >= ceiling:
                    continue
                new = dict(raw); new[field] += 1
                chosen_profiles.append(new); changed.append(encode(new, config)[1]); original_indices.append(j)
            after = model.predict(xgb.DMatrix(np.asarray(changed, dtype=np.float32), feature_names=names))
            control_after = control.predict(xgb.DMatrix(np.asarray(changed, dtype=np.float32), feature_names=names))
            delta = after - original[original_indices]
            control_delta = control_after - control_original[original_indices]
            control_violations += int((control_delta < -1e-5).sum())
            bad = np.flatnonzero(delta < -1e-5)
            for j in bad[:20]:
                violations.append(dict(spid=chosen_profiles[j]['spid'], ability=field, log_delta=float(delta[j])))
            for raw, log, index in zip(chosen_profiles, after, original_indices):
                if local_price(float(log), raw, config) < predictions[profiles[index]['spid']]['price']:
                    violations.append(dict(spid=raw['spid'], ability=field, issue='displayed EP decreased'))
            monotonic_checks += len(after)
            print('AUDIT_STAT', family, field, 'checks', len(after), 'bad', len(bad), flush=True)
        save('audit-progress.json', dict(completed_family=family, checks=monotonic_checks, violations=len(violations)))
    # A stronger numeric profile may legitimately differ in body, role or foot
    # skill. Strict dominance comparisons hold these contexts fixed or improve
    # them in the same declared direction. Trait/animation IDs are never used.
    groups = collections.defaultdict(list)
    for raw in current:
        groups[(raw['playerid'], raw['preferredposition1'], raw['height'], raw['weight'])].append(raw)
    dominance = []
    inversions = []
    strict_fields = sorted(set().union(*(set(x) for x in config['role_weights'].values())) | {'agility', 'balance', 'curve', 'freekickaccuracy', 'penalties', 'weakfootabilitytypecode', 'skillmoves'})
    old_inversions = []
    for group in groups.values():
        for a in group:
            for b in group:
                if a['spid'] == b['spid']:
                    continue
                diffs = [a[f] - b[f] for f in strict_fields]
                if min(diffs) < 0 or max(diffs) <= 0:
                    continue
                pa, pb = predictions[a['spid']]['price'], predictions[b['spid']]['price']
                row = dict(stronger=a['spid'], weaker=b['spid'], new_prices=[pa, pb],
                           old_prices=[a['historical']['initial'], b['historical']['initial']] if a.get('historical') and b.get('historical') else None)
                dominance.append(row)
                if pa < pb:
                    inversions.append(row)
                if row['old_prices'] and row['old_prices'][0] < row['old_prices'][1]:
                    old_inversions.append(row)
    save('dominance-audit.json', dict(comparable_pairs=len(dominance), new_inversions=inversions,
                                     old_inversions=old_inversions, all_pairs=dominance))
    with gzip.open(P / 'current-price-preview.json.gz', 'wt', encoding='utf8') as f:
        json.dump(predictions, f, separators=(',', ':'))
    report.update(status='PASS' if not violations and not inversions else 'FAILED_AUDIT',
                  current_profiles=len(current), single_attribute_checks=monotonic_checks,
                  single_attribute_violations=violations, unconstrained_control_single_stat_decreases=control_violations,
                  dominance_pairs=len(dominance), old_dominance_inversions=len(old_inversions),
                  new_dominance_inversions=len(inversions),
                  new_one_ep_prices=sum(v['price'] == 1 for v in predictions.values()),
                  old_one_ep_prices=sum(r.get('historical', {}).get('current') == 1 for r in current),
                  price_range=[min(v['price'] for v in predictions.values()), max(v['price'] for v in predictions.values())],
                  elapsed_seconds=time.monotonic() - started, maximum_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                  model_sha256=hashlib.sha256((P / 'selected-model.json.gz').read_bytes()).hexdigest(),
                  training_source_sha256=config['source_sha256'],
                  official_activated=False, native_verified=False)
    save('training-report.json', report)
    print('FINAL', json.dumps({k: v for k, v in report.items() if k not in ('candidates', 'test_by_role')}), flush=True)
    if report['status'] != 'PASS':
        raise RuntimeError('Hard monotonicity or dominance gate failed')


if __name__ == '__main__':
    main()
