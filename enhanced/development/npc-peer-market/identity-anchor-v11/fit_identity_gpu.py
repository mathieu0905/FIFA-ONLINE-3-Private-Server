"""Learn bounded same-player history effects over the GPU ability backbone.

Three identity-group folds produce residuals without training on that player's
prices. Known-player validation/test use only OTHER seasons as prior history.
The final prior table then refits all public real historical observations;
synthetic rows never become name evidence. No production paths are used here.
"""
from pathlib import Path
import os
os.environ.setdefault('OMP_NUM_THREADS', '4')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
import collections
import copy
import gzip
import hashlib
import itertools
import json
import math
import sys
import time

P = Path(__file__).resolve().parent
B = P.parent / 'run-20261107-anchor-v10'
sys.path[:0] = [str(B), str(P.parent / 'run-20261107-monotone-v8/deps')]
import numpy as np
import xgboost as xgb
from train_gpu import VectorFeatures, combined, metric
from features import schema, FAMILIES


def save(name, value):
    (P / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), 'utf8')


def loadgz(path):
    with gzip.open(path, 'rt', encoding='utf8') as file:
        return json.load(file)


def effect(indices, residuals, rows, regularization, cap):
    if not indices or cap == 1:
        return 0., 0, 0
    by_season = collections.defaultdict(list)
    for i in indices:
        by_season[rows[i]['spid'] // 1000000].append(float(residuals[i]))
    season_residuals = [float(np.median(values)) for values in by_season.values()]
    effective = len(by_season) + (2 if any(rows[i]['calibration_anchor'] for i in indices) else 0)
    shrink = effective / (effective + regularization)
    value = float(np.median(season_residuals)) * shrink
    return float(np.clip(value, -math.log(cap), math.log(cap))), len(by_season), effective


def known_cases(indices, rows):
    grouped = collections.defaultdict(list)
    for i in indices:
        grouped[rows[i]['playerid']].append(i)
    cases = []
    for pid, group in sorted(grouped.items()):
        if len({rows[i]['spid'] // 1000000 for i in group}) < 2:
            continue
        # A deterministic season-card target, selected without its price.
        target = max(group, key=lambda i: rows[i]['spid'])
        target_season = rows[target]['spid'] // 1000000
        history = [i for i in group if rows[i]['spid'] // 1000000 != target_season]
        cases.append((target, history))
    return cases


def main():
    started = time.monotonic()
    c = json.loads((B / 'config.json').read_text('utf8'))
    data = loadgz(B / 'training-data.json.gz')
    current = loadgz(B / 'current-profiles.json.gz')
    base_report = json.loads((B / 'training-report.json').read_text('utf8'))
    assert base_report['status'] == 'PASS'
    v = VectorFeatures(c)
    A, wf, sm = v.raw([r['attributes'] for r in data])
    arrays, gate, floor = v.make(A, wf, sm)
    real = np.array([r['kind'] == 'real' for r in data])
    parts = np.array([r['partition'] for r in data])
    keeper = np.array([r['attributes']['preferredposition1'] == 0 for r in data])
    ids = np.array([r['playerid'] for r in data])
    y = np.log([r['price'] for r in data])
    # Metadata-based deterministic player folds, with every season of one
    # player held out together. Outer test identities never enter these fits.
    folds = np.array([int(hashlib.sha256(str(int(pid)).encode()).hexdigest()[:8], 16) % 3 for pid in ids])
    generic_log = np.full(len(data), np.nan)
    models = {}
    for family in FAMILIES:
        models[family] = xgb.Booster(model_file=B / ('final-' + family + '.json'))
        models[family].set_param(dict(device='cuda:0', nthread=4))
    final_logs = {f: models[f].predict(xgb.DMatrix(arrays[f], feature_names=schema(c, f)[0])) for f in FAMILIES}
    final_source = combined(final_logs, gate)
    test = np.flatnonzero(real & (parts == 'test'))
    generic_log[test] = np.log(final_source[test])
    print('START_IDENTITY_OOF', len(data), 'real', int(real.sum()), flush=True)
    for fold in range(3):
        train_mask = (parts != 'test') & (folds != fold)
        held = np.flatnonzero(real & (parts != 'test') & (folds == fold))
        eligible = {30,93,91,27,28}
        cohorts = collections.defaultdict(list)
        for i in np.flatnonzero(train_mask & real):
            r = data[i]
            if r['spid']//1000000 in eligible:
                role = c['position_roles'][r['attributes']['preferredposition1']]
                cohorts[(r['spid']//1000000,role)].append(r['price'])
        cutoffs = {key: sorted(values)[max(0, math.ceil(len(values)*.6)-1)] for key,values in cohorts.items()}
        flags = np.zeros(len(data), dtype=bool)
        for i in np.flatnonzero(train_mask & real):
            r = data[i];season = r['spid']//1000000;role = c['position_roles'][r['attributes']['preferredposition1']]
            flags[i] = r['ovr']>=80 and (season==30 or (season in eligible and r['price']>=cutoffs.get((season,role),float('inf'))))
        fold_logs = {}
        for family in FAMILIES:
            setting = base_report['candidate_info'][base_report['selected'][family]]
            option = setting['option']
            mask = keeper if family=='GK' else ~keeper
            indices = np.flatnonzero(train_mask & mask)
            counts = collections.Counter(int(ids[i]) for i in indices if flags[i])
            weights = [.35 if not real[i] else (option['anchor_weight']/min(3,counts[int(ids[i])]) if flags[i] else 1.) for i in indices]
            params = dict(device='cuda:0', tree_method='hist', objective='reg:squarederror', eval_metric='mae',
                max_depth=option['depth'], max_bin=512, eta=.04, min_child_weight=8,
                reg_lambda=option['regularization'], reg_alpha=.25, nthread=4, seed=11041+fold,
                subsample=1., colsample_bytree=1., monotone_constraints=tuple(schema(c,family)[1]))
            booster = xgb.train(params, xgb.DMatrix(arrays[family][indices],label=y[indices],weight=weights,feature_names=schema(c,family)[0]),num_boost_round=setting['iterations'])
            assert json.loads(booster.save_config())['learner']['generic_param']['device'].startswith('cuda')
            fold_logs[family] = booster.predict(xgb.DMatrix(arrays[family][held],feature_names=schema(c,family)[0]))
            print('OOF_HEAD_DONE',fold,family,'held',len(held),flush=True)
        generic_log[held] = np.log(combined(fold_logs,gate[held]))
        save('progress.json',dict(completed_fold=fold,elapsed=time.monotonic()-started))
    assert np.isfinite(generic_log[real]).all()
    residuals = y-generic_log
    val = np.flatnonzero(real & (parts=='validation'))
    val_cases = known_cases(val,data)
    grid = []
    for regularization,cap in itertools.product([1.,3.,8.,20.],[1.,1.5,2.,3.,5.]):
        targets = np.array([t for t,h in val_cases])
        offsets = np.array([effect(h,residuals,data,regularization,cap)[0] for t,h in val_cases])
        m = metric(y[targets],generic_log[targets]+offsets)
        grid.append(dict(regularization=regularization,cap=cap,validation_known_history=m))
    chosen = min(grid,key=lambda r:r['validation_known_history']['log_mae'])
    lam,cap = chosen['regularization'],chosen['cap']
    def evaluate(cases):
        targets = np.array([t for t,h in cases])
        adjustments = np.array([effect(h,residuals,data,lam,cap)[0] for t,h in cases])
        return dict(cases=len(cases),base=metric(y[targets],generic_log[targets]),with_identity=metric(y[targets],generic_log[targets]+adjustments),
                    protocol='One highest-SPID season held out per player; prior uses other seasons only. Generic backbone excludes the whole identity. Target quote is never prior history.')
    test_cases = known_cases(test,data)
    known_test = evaluate(test_cases)
    # Final history refit: all real public quotes are now permissible evidence.
    # Reported known-history tests ABOVE deliberately excluded target quotes.
    history = collections.defaultdict(list)
    for i in np.flatnonzero(real):
        history[int(ids[i])].append(int(i))
    priors = {}
    # OOF residuals validate how much identity evidence generalizes. The
    # deployable correction must explain what the ACTUAL final backbone still
    # misses; adding the larger OOF error again would double-count base fit.
    deployed_residuals = y - np.log(final_source)
    for pid,indices in history.items():
        offset,seasons,effective = effect(indices,deployed_residuals,data,lam,cap)
        priors[str(pid)] = dict(log_multiplier=offset,multiplier=math.exp(offset),real_quotes=len(indices),
                               seasons=seasons,effective_evidence=effective,anchor_evidence=any(data[i]['calibration_anchor'] for i in indices),
                               confidence='low' if seasons<2 else ('medium' if seasons<5 else 'higher'),
                               fitting='median of per-season deployed-backbone residuals with shrinkage and cap; OOF used separately for regularization selection')
    export = loadgz(B/'selected-model.json.gz')
    export.update(schema=3,type='monotone_max_experts_with_identity_prior',player_priors=priors,
                  base_model_sha256=base_report['model_sha256'])
    export['config']=copy.deepcopy(c)
    export['config']['revision']='identity-anchor-v11'
    export['config']['identity_prior']=dict(regularization=lam,maximum_factor=cap,unknown_player_factor=1.,
        policy='A fixed same-player multiplier across all seasons. Learned only from real public quotes, with whole-identity OOF residuals; no per-card overrides or hand-written fame prices.',
        final_prior_fit_scope='All real historical quote evidence after frozen known-history evaluation; final table fit itself is not an independent test.')
    with gzip.open(P/'selected-model.json.gz','wt',encoding='utf8') as file:json.dump(export,file,separators=(',',':'))
    save('prior-selection.json',dict(chosen=chosen,grid=grid,validation_cases=len(val_cases),selection_uses_test=False))
    save('identity-priors.json',priors)
    save('known-test-cases.json',[dict(playerid=data[t]['playerid'],target_spid=data[t]['spid'],target_price=data[t]['price'],
        history_spids=[data[i]['spid'] for i in h],base_log=float(generic_log[t]),
        prior_log=effect(h,residuals,data,lam,cap)[0]) for t,h in test_cases])
    save('quote-predictions.json',[dict(spid=data[i]['spid'],playerid=data[i]['playerid'],partition=data[i]['partition'],anchor=bool(data[i]['calibration_anchor']),
        target=data[i]['price'],generic_log=float(generic_log[i]),final_base_log=float(math.log(final_source[i])),
        refit_prior_log=priors[str(data[i]['playerid'])]['log_multiplier']) for i in np.flatnonzero(real)])
    raw_current,wf_current,sm_current = v.raw(current)
    prior_factors=np.array([priors.get(str(r['playerid']),{}).get('multiplier',1.) for r in current],dtype=np.float64)
    def predict(A,w,s):
        arr,g,guard=v.make(A,w,s)
        logs={f:models[f].predict(xgb.DMatrix(arr[f],feature_names=schema(c,f)[0])) for f in FAMILIES}
        base=combined(logs,g)
        prices=np.minimum(5_600_000_000_000_000,np.maximum(1,np.rint(base*prior_factors/c['source_price_divisor']+guard))).astype(np.int64)
        return prices,base
    prices,base_source=predict(raw_current,wf_current,sm_current)
    count=0;violations=[]
    for field in v.fields+['weakfootabilitytypecode','skillmoves']:
        A2,w2,s2=raw_current.copy(),wf_current.copy(),sm_current.copy()
        if field in v.fields:
            col=v.fields.index(field);mask=A2[:,col]<255;A2[mask,col]+=1;minimum=1
        elif field=='weakfootabilitytypecode':
            mask=w2<5;w2[mask]+=1;minimum=25
        else:
            mask=s2<4;s2[mask]+=1;minimum=25
        after,_=predict(A2,w2,s2)
        bad=np.flatnonzero(mask & (after-prices<minimum))
        for i in bad[:20]:violations.append(dict(spid=current[i]['spid'],field=field,before=int(prices[i]),after=int(after[i])))
        count+=int(mask.sum());print('AUDIT_STAT',field,int(mask.sum()),'fail',len(bad),flush=True)
    comparisons=np.column_stack([raw_current,wf_current,sm_current]);players=collections.defaultdict(list)
    for i,r in enumerate(current):players[r['playerid']].append(i)
    pairs=0;inversions=[]
    for indices in players.values():
        for a in indices:
            for b in indices:
                if a==b:continue
                delta=comparisons[a]-comparisons[b]
                if delta.min()>=0 and delta.max()>0:
                    pairs+=1
                    if prices[a]<=prices[b]:inversions.append(dict(stronger=current[a]['spid'],weaker=current[b]['spid']))
    with gzip.open(P/'current-price-preview.json.gz','wt',encoding='utf8') as file:
        json.dump({str(r['spid']):dict(price=int(prices[i]),base_source=float(base_source[i]),prior_factor=float(prior_factors[i]),
                 known_identity=str(r['playerid']) in priors) for i,r in enumerate(current)},file,separators=(',',':'))
    report=dict(status='PASS' if not violations and not inversions else 'FAILED_AUDIT',
        model_sha256=hashlib.sha256((P/'selected-model.json.gz').read_bytes()).hexdigest(),base_model_sha256=base_report['model_sha256'],
        GPU='remote physical GPU2; six identity-crossfit GPU heads over v10 GPU backbone',
        learned_identities=len(priors),real_quotes=int(real.sum()),prior_regularization=lam,prior_cap=cap,
        known_validation=evaluate(val_cases),known_test=known_test,
        unseen_identity_test=base_report['test_metrics'],
        test_note='Unseen-identity ability benchmark and known-history test are separate scenarios. Final all-history prior refit is calibration, not a fresh blind test.',
        history_fitting='3-fold whole-player OOF validates/selects regularization; final all-real-history map fits residuals against the actual deployed ability backbone to avoid double counting. Synthetic rows excluded.',
        profiles=len(current),known_profile_count=int(sum(str(r['playerid']) in priors for r in current)),
        strict_checks=count,strict_failures=violations,dominance_pairs=pairs,dominance_failures=inversions,
        price_range=[int(prices.min()),int(prices.max())],one_EP_cards=int((prices==1).sum()),
        formal_written=False,official_activated=False,elapsed_seconds=time.monotonic()-started)
    save('training-report.json',report);print('FINAL',json.dumps(report),flush=True);assert report['status']=='PASS'


if __name__=='__main__':main()
