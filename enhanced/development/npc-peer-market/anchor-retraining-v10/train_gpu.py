"""GPU fit of anchor-calibrated monotone experts; vectorized full-roster audit."""
from pathlib import Path
import os
os.environ.setdefault('OMP_NUM_THREADS', '4')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
import collections
import gzip
import hashlib
import itertools
import json
import math
import sys
import time

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parent / 'run-20261107-monotone-v8/deps'))
import numpy as np
import xgboost as xgb
from features import ability_fields, schema, encode, GK_FIELDS, FAMILIES


def read(name):
    with gzip.open(P / name, 'rt', encoding='utf8') as f:
        return json.load(f)


def save(name, value):
    (P / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), 'utf8')


def metric(y, p):
    e = np.abs(y - p)
    if not len(e):
        return None
    return dict(rows=len(e), log_mae=float(e.mean()), median_error_factor=float(np.exp(np.median(e))),
                within_2x=float((e <= math.log(2)).mean()), within_3x=float((e <= math.log(3)).mean()),
                p90_error_factor=float(np.exp(np.quantile(e, .9))))


class VectorFeatures:
    def __init__(self, config):
        self.config = config
        self.fields = ability_fields(config)
        self.roles = sorted(config['role_weights'])
        self.weights = np.array([[config['role_weights'][r].get(f, 0) for r in self.roles] for f in self.fields], dtype=np.int64)
        self.gk = [self.fields.index(k) for k in GK_FIELDS]

    def raw(self, rows):
        return (np.asarray([[r[f] for f in self.fields] for r in rows], dtype=np.int64),
                np.asarray([r['weakfootabilitytypecode'] for r in rows], dtype=np.int64),
                np.minimum(4, np.asarray([r['skillmoves'] for r in rows], dtype=np.int64)))

    def make(self, A, wf, sm):
        clipped = np.maximum(0, A)
        role = (clipped @ self.weights) / 100.
        by_role = {r: role[:, i] for i, r in enumerate(self.roles)}
        best_out = np.max(role[:, [i for i, r in enumerate(self.roles) if r != 'GK']], axis=1)
        allround = np.minimum.reduce([np.maximum.reduce([by_role[r] for r in group]) for group in
                                     [('ST', 'CF', 'W'), ('AM', 'CM', 'WM', 'DM'), ('CB', 'SW', 'FB', 'WB')]])
        gk_mean = clipped[:, self.gk].mean(1)
        arrays = {}
        for family in FAMILIES:
            cols = []
            for key in schema(self.config, family)[0]:
                if key.startswith('role:'):
                    value = by_role[key[5:]]
                elif key == 'best_outfield':
                    value = best_out
                elif key == 'allround_min':
                    value = allround
                elif key == 'keeper_mean':
                    value = gk_mean
                elif key == 'keeper_min':
                    value = clipped[:, self.gk].min(1)
                elif key == 'weakfootabilitytypecode':
                    value = wf
                elif key == 'skillmoves':
                    value = sm
                else:
                    value = clipped[:, self.fields.index(key)]
                cols.append(value)
            arrays[family] = np.asarray(cols, dtype=np.float32).T.copy()
        g = self.config['gk_gate']
        gate = np.minimum(1., (gk_mean / g['full_support_mean']) ** g['power'])
        guard, sensitivity = self.config['low_price_guard'], self.config['minimum_price_sensitivity']
        floor = (guard['anchor_ep'] * np.exp(guard['log_slope'] * (role.max(1) - guard['anchor_native_rating']))
                 + (A + 3).sum(1) * sensitivity['ep_per_ability_point']
                 + (wf - 1) * sensitivity['ep_per_weakfoot_star'] + sm * sensitivity['ep_per_skill_star'])
        return arrays, gate, floor


def combined(preds, gate):
    return np.maximum(np.exp(np.minimum(50., preds['OUT'].astype(np.float64))),
                      np.exp(np.minimum(50., preds['GK'].astype(np.float64))) * gate)


def main():
    started = time.monotonic()
    c = json.loads((P / 'config.json').read_text('utf8'))
    data, current = read('training-data.json.gz'), read('current-profiles.json.gz')
    groups = {part: {r['playerid'] for r in data if r['partition'] == part} for part in ['train', 'validation', 'test']}
    assert not (groups['train'] & groups['validation'] or groups['train'] & groups['test'] or groups['validation'] & groups['test'])
    real = np.array([r['kind'] == 'real' for r in data])
    is_keeper = np.array([r['attributes']['preferredposition1'] == 0 for r in data])
    anchor = np.array([r['calibration_anchor'] for r in data])
    high = np.array([r['ovr'] >= 82 or r['spid'] // 1000000 in (30, 93) for r in data])
    partitions = np.array([r['partition'] for r in data])
    y = np.log([r['price'] for r in data])
    vector = VectorFeatures(c)
    A, wf, sm = vector.raw([r['attributes'] for r in data])
    X, gate, floor = vector.make(A, wf, sm)
    for i in range(40):
        for family in FAMILIES:
            assert np.array_equal(X[family][i], np.array(encode(data[i]['attributes'], c, family), dtype=np.float32))
    train_mask = partitions == 'train'
    va = np.flatnonzero(real & (partitions == 'validation'))
    test = np.flatnonzero(real & (partitions == 'test'))
    options = [dict(name='baseline', anchor_weight=1, depth=6, rounds=900, regularization=25),
               dict(name='anchor6', anchor_weight=6, depth=6, rounds=1100, regularization=15),
               dict(name='anchor16', anchor_weight=16, depth=6, rounds=1200, regularization=15),
               dict(name='anchor16_deep', anchor_weight=16, depth=8, rounds=1200, regularization=25)]
    dm_all = {f: xgb.DMatrix(X[f], feature_names=schema(c, f)[0]) for f in FAMILIES}
    candidates, candidate_preds = {}, {}
    def weight(indices, multiplier):
        counts = collections.Counter(data[i]['playerid'] for i in indices if anchor[i])
        return np.array([.35 if not real[i] else (multiplier / min(3, counts[data[i]['playerid']]) if anchor[i] else 1.) for i in indices])
    def params(family, option):
        return dict(device='cuda:0', tree_method='hist', objective='reg:squarederror', eval_metric='mae',
                    max_depth=option['depth'], max_bin=512, eta=.04, min_child_weight=8,
                    reg_lambda=option['regularization'], reg_alpha=.25, nthread=4, seed=10041,
                    subsample=1., colsample_bytree=1., monotone_constraints=tuple(schema(c, family)[1]))
    print('START', json.dumps(dict(gpu=os.environ.get('CUDA_VISIBLE_DEVICES'), rows=len(data), profiles=len(current),
                                  anchor_counts={part: int((anchor & (partitions == part)).sum()) for part in groups})), flush=True)
    for family in FAMILIES:
        family_mask = is_keeper if family == 'GK' else ~is_keeper
        tr = np.flatnonzero(train_mask & family_mask)
        val = np.flatnonzero(real & (partitions == 'validation') & family_mask)
        for option in options:
            def score(prediction, dmatrix):
                e = np.abs(prediction - y[val])
                a = e[anchor[val]].mean() if anchor[val].any() else e.mean()
                h = e[high[val]].mean() if high[val].any() else e.mean()
                return 'calibration_score', float(e.mean() + .4 * a + .1 * h)
            booster = xgb.train(params(family, option), xgb.DMatrix(X[family][tr], label=y[tr], weight=weight(tr, option['anchor_weight']), feature_names=schema(c, family)[0]),
                                num_boost_round=option['rounds'], evals=[(xgb.DMatrix(X[family][val], label=y[val], feature_names=schema(c, family)[0]), 'validation')],
                                custom_metric=score, early_stopping_rounds=90, maximize=False, verbose_eval=150)
            booster = booster[:booster.best_iteration + 1]
            runtime = json.loads(booster.save_config())['learner']
            assert runtime['generic_param']['device'].startswith('cuda'), 'CPU fallback is refused'
            assert runtime['gradient_booster']['tree_train_param']['monotone_constraints'] == '(' + ','.join('1' for _ in schema(c, family)[0]) + ')'
            prediction = booster.predict(dm_all[family])
            name = family + '-' + option['name']
            booster.save_model(P / (name + '.json'))
            candidate_preds[name] = prediction
            candidates[name] = dict(option=option, iterations=len(booster.get_dump()), device='cuda:0',
                                    validation=metric(y[val], prediction[val]), anchor_validation=metric(y[val[anchor[val]]], prediction[val[anchor[val]]]))
            save('progress.json', dict(completed=candidates, elapsed=time.monotonic() - started))
            print('CANDIDATE_DONE', name, json.dumps(candidates[name]), flush=True)
    pairs = []
    for out_option, gk_option in itertools.product(options, repeat=2):
        names = {'OUT': 'OUT-' + out_option['name'], 'GK': 'GK-' + gk_option['name']}
        pred = np.log(combined({f: candidate_preds[names[f]][va] for f in FAMILIES}, gate[va]))
        e = np.abs(y[va] - pred)
        score = float(e.mean() + .4 * e[anchor[va]].mean() + .1 * e[high[va]].mean())
        pairs.append(dict(models=names, overall=metric(y[va], pred), anchors=metric(y[va[anchor[va]]], pred[anchor[va]]), score=score))
    baseline = next(r for r in pairs if r['models'] == {'OUT': 'OUT-baseline', 'GK': 'GK-baseline'})
    eligible = [r for r in pairs if r['overall']['log_mae'] <= baseline['overall']['log_mae'] * 1.05]
    chosen = min(eligible, key=lambda r: r['score'])
    save('selection.json', dict(chosen=chosen, all_pairs=pairs, baseline=baseline,
                               selection_uses_test=False, overall_validation_regression_limit=1.05))
    models = {}
    for family in FAMILIES:
        setting = candidates[chosen['models'][family]]
        family_mask = is_keeper if family == 'GK' else ~is_keeper
        outer = np.flatnonzero((partitions != 'test') & family_mask)
        models[family] = xgb.train(params(family, setting['option']), xgb.DMatrix(X[family][outer], label=y[outer], weight=weight(outer, setting['option']['anchor_weight']), feature_names=schema(c, family)[0]), num_boost_round=setting['iterations'])
        models[family].save_model(P / ('final-' + family + '.json'))
    final_logs = {f: models[f].predict(dm_all[f]) for f in FAMILIES}
    final_source = combined(final_logs, gate)
    final_log = np.log(final_source)
    subsets = {'overall': test, 'anchors': test[anchor[test]], 'high': test[high[test]],
               'goalkeepers': test[is_keeper[test]], 'top_GK': test[is_keeper[test] & high[test]]}
    report = dict(status='AUDITING', selected=chosen['models'], validation_selection=chosen,
                  test_metrics={key: metric(y[indices], final_log[indices]) for key, indices in subsets.items()},
                  training_anchor_fit=metric(y[np.flatnonzero(anchor & (partitions != 'test'))], final_log[np.flatnonzero(anchor & (partitions != 'test'))]),
                  anchor_examples=[dict(spid=data[i]['spid'], target=data[i]['price'], predicted_source=float(final_source[i]), partition=data[i]['partition']) for i in np.flatnonzero(anchor)],
                  selection_uses_test=False, repeated_fixed_benchmark_not_new_blind_test=True,
                  candidate_info=candidates, production_written=False, official_activated=False)
    export = dict(schema=2, type='monotone_max_experts', config=c, experts={})
    for family, booster in models.items():
        raw = json.loads(booster.save_raw(raw_format='json'))['learner']
        base = raw['learner_model_param']['base_score']
        base = float(json.loads(base)[0]) if base.startswith('[') else float(base)
        export['experts'][family] = dict(features=schema(c, family)[0], constraints=schema(c, family)[1], baseline=base, trees=raw['gradient_booster']['model']['trees'])
    with gzip.open(P / 'selected-model.json.gz', 'wt', encoding='utf8') as f:
        json.dump(export, f, separators=(',', ':'))
    save('test-predictions.json', [dict(spid=data[i]['spid'], price=data[i]['price'], log_prediction=float(final_log[i]), anchor=bool(anchor[i])) for i in test])
    # Full audit uses vectorized integer role sums, the SAME GPU boosters and
    # the final rounded EP link. No weak monotonic-only stand-in is tested.
    raw_current, wf_current, sm_current = vector.raw(current)
    def predict(A, wf, sm):
        arrays, g, guard = vector.make(A, wf, sm)
        logs = {f: models[f].predict(xgb.DMatrix(arrays[f], feature_names=schema(c, f)[0])) for f in FAMILIES}
        source = combined(logs, g)
        price = np.minimum(5_600_000_000_000_000, np.maximum(1, np.rint(source / c['source_price_divisor'] + guard))).astype(np.int64)
        return price, np.log(source), logs, g
    prices, original_log, original_experts, current_gate = predict(raw_current, wf_current, sm_current)
    violations, count = [], 0
    irrelevant_gk_changes = []
    for field in vector.fields + ['weakfootabilitytypecode', 'skillmoves']:
        A2, w2, s2 = raw_current.copy(), wf_current.copy(), sm_current.copy()
        if field in vector.fields:
            j = vector.fields.index(field); mask = A2[:, j] < 255; A2[mask, j] += 1; minimum = 1
        elif field == 'weakfootabilitytypecode':
            mask = w2 < 5; w2[mask] += 1; minimum = 25
        else:
            mask = s2 < 4; s2[mask] += 1; minimum = 25
        after, after_log, _, _ = predict(A2, w2, s2)
        bad = np.flatnonzero(mask & (after - prices < minimum))
        for i in bad[:20]:
            violations.append(dict(spid=current[i]['spid'], field=field, before=int(prices[i]), after=int(after[i])))
        count += int(mask.sum())
        if field in GK_FIELDS:
            relevant = np.array([r['preferredposition1'] != 0 for r in current]) & mask
            irrelevant_gk_changes.append(dict(field=field, outfield_cards=int(relevant.sum()), median_EP_increase=float(np.median((after-prices)[relevant])),
                                              max_EP_increase=int((after-prices)[relevant].max()), over_one_percent=int(((after > prices*1.01) & relevant).sum())))
        print('AUDIT_STAT', field, int(mask.sum()), 'strict_failures', len(bad), flush=True)
    by_player = collections.defaultdict(list)
    for i, row in enumerate(current):
        by_player[row['playerid']].append(i)
    dominance_count, inversions = 0, []
    comparable = np.column_stack([raw_current, wf_current, sm_current])
    for indices in by_player.values():
        for a in indices:
            for b in indices:
                if a == b:
                    continue
                diff = comparable[a] - comparable[b]
                if diff.min() >= 0 and diff.max() > 0:
                    dominance_count += 1
                    if prices[a] <= prices[b]:
                        inversions.append(dict(stronger=current[a]['spid'], weaker=current[b]['spid'], prices=[int(prices[a]),int(prices[b])]))
    previews = {str(row['spid']): dict(price=int(prices[i]), log_source=float(original_log[i]),
               active_expert='GK' if np.exp(float(original_experts['GK'][i]))*current_gate[i] > np.exp(float(original_experts['OUT'][i])) else 'OUT') for i, row in enumerate(current)}
    with gzip.open(P / 'current-price-preview.json.gz', 'wt', encoding='utf8') as f:
        json.dump(previews, f, separators=(',', ':'))
    report.update(status='PASS' if not violations and not inversions else 'FAILED_AUDIT', profiles=len(current),
                  strict_single_attribute_checks=count, strict_failures=violations,
                  dominance_pairs=dominance_count, dominance_failures=inversions,
                  irrelevant_GK_sensitivity=irrelevant_gk_changes,
                  one_EP_cards=int((prices == 1).sum()), price_range=[int(prices.min()), int(prices.max())],
                  model_sha256=hashlib.sha256((P/'selected-model.json.gz').read_bytes()).hexdigest(),
                  elapsed_seconds=time.monotonic()-started, trained_on_GPU=True, physical_GPU=os.environ.get('CUDA_VISIBLE_DEVICES'))
    save('training-report.json', report)
    print('FINAL', json.dumps({k:v for k,v in report.items() if k not in ['candidate_info','anchor_examples']}), flush=True)
    assert report['status'] == 'PASS'


if __name__ == '__main__':
    main()
