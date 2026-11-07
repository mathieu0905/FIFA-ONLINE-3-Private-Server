"""Value from height, weight and ability attributes only. No identity or season inputs."""
from pathlib import Path
import sys,os,json,math,collections,hashlib
os.environ.setdefault('OMP_NUM_THREADS','4');os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'analysis-deps'))
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupShuffleSplit
rows=json.loads((R/'historical-data.json').read_text('utf8'))
rows=[r for r in rows if r['season'] not in (12,13,48,84) and r['height']>0 and r['weight']>0]
keys=list(rows[0]);stats=[k for k in keys[keys.index('acceleration'):keys.index('volleys')+1] if k!='potential']
extra=['weakfootabilitytypecode','skillmoves','attackingworkrate','defensiveworkrate']
features=['height','weight']+stats+extra
assert not set(features)&{'spid','playerid','season','name','price','internationalrep','overallrating','ovr','teamid','trait1','trait2'}
X=np.array([[float(r[k]) for k in features] for r in rows]);y=np.log([r['price'] for r in rows]);groups=np.array([r['playerid'] for r in rows])
train,test=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=2026).split(X,y,groups));assert not set(groups[train])&set(groups[test])
def metric(pred):
 err=np.abs(pred-y[test]);return dict(log_mae=float(np.mean(err)),median_error_factor=float(np.exp(np.median(err))),within_2x=float(np.mean(err<=math.log(2))),within_3x=float(np.mean(err<=math.log(3))),p90_error_factor=float(np.exp(np.quantile(err,.9))))
buckets=collections.defaultdict(list)
for i in train:buckets[rows[i]['ovr']].append(y[i])
med={k:np.median(v) for k,v in buckets.items()};baseline=np.array([med[min(med,key=lambda k:abs(k-rows[i]['ovr']))] for i in test])
params=dict(loss='absolute_error',learning_rate=.06,max_iter=400,max_leaf_nodes=31,min_samples_leaf=20,l2_regularization=10,random_state=2026)
m=HistGradientBoostingRegressor(**params).fit(X[train],y[train]);pred=m.predict(X[test]);results={'ovr_only_benchmark':metric(baseline),'height_weight_abilities_only':metric(pred)}
print('METRICS',json.dumps(results),flush=True)
# Individual permutation measures predictive association only, not causal price effects.
rng=np.random.default_rng(2026);subset=rng.choice(test,min(1600,len(test)),replace=False);base=float(np.mean(np.abs(m.predict(X[subset])-y[subset])));importance={}
for j,f in enumerate(features):
 z=X[subset].copy();z[:,j]=X[rng.permutation(subset),j];importance[f]=float(np.mean(np.abs(m.predict(z)-y[subset]))-base)
# Identify same-position examples where a lower OVR is predicted more expensive.
examples=[];testrows=[]
for i,p in zip(test,pred):
 r=rows[i];testrows.append(dict(spid=r['spid'],name=r['name'],season=r['season'],position=r['preferredposition1'],ovr=r['ovr'],height=r['height'],weight=r['weight'],predicted_price=round(math.exp(p)),observed_price=r['price']))
for a in sorted(testrows,key=lambda r:-r['predicted_price']):
 candidates=[b for b in testrows if b['position']==a['position'] and a['ovr']+1<=b['ovr']<=a['ovr']+3 and b['predicted_price']*1.5<a['predicted_price']]
 if candidates:
  b=min(candidates,key=lambda r:abs(r['ovr']-a['ovr']));examples.append(dict(lower_ovr=a,higher_ovr=b))
 if len(examples)>=8:break
# Fit final portable trees; no source historical price table is loaded by the predictor.
m.fit(X,y);trees=[]
for group in m._predictors:
 n=group[0].nodes;assert not any(n['is_categorical'])
 trees.append([[int(r['feature_idx']),float(r['num_threshold']),int(r['left']),int(r['right']),float(r['value']),int(r['is_leaf'])] for r in n])
model=dict(schema=1,scope='height-weight-abilities-only',features=features,baseline=float(m._baseline_prediction[0,0]),trees=trees,feature_ranges={f:[float(X[:,i].min()),float(X[:,i].max())] for i,f in enumerate(features)},price_unit='historical normalized EP at +1; calibrate scale before live use',source_price_sha256=hashlib.sha256((R/'historical-reference-prices.json').read_bytes()).hexdigest())
(R/'attributes-value-model.json').write_text(json.dumps(model),'utf8')
# Save independent training implementation probes for standard-library evaluator parity.
probes=[dict(attributes={f:rows[i][f] for f in features},log_prediction=float(v)) for i,v in zip(range(0,len(rows),max(1,len(rows)//200)),m.predict(X[::max(1,len(rows)//200)]))]
(R/'attributes-probes.json').write_text(json.dumps(probes),'utf8')
report=dict(training_rows=len(rows),ability_fields=stats,input_fields=features,test_rows=len(test),unseen_test_players=len(set(groups[test])),validation=results,feature_permutation_log_mae_increase=dict(sorted(importance.items(),key=lambda kv:-kv[1])),lower_ovr_higher_value_examples=examples,excluded_inputs=['player identity/name','season','team/nationality','reputation','historical price lookup at inference','OVR as a model input','unmapped trait/animation identifiers'],production_changed=False,limitations=['Training labels still reflect historical scarcity and popularity that physical inputs cannot fully explain.','Height/weight are proxies, not measured native animation or physical-model collision behavior.','Only plus1 base values are fitted; enhancement and market supply/demand must be separate multipliers.','Individual feature importance is predictive association, not causal hand-feel evidence.'])
(R/'attributes-analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print('FEATURES',len(features),'STATS',len(stats),'TOP',list(report['feature_permutation_log_mae_increase'].items())[:10],flush=True)
