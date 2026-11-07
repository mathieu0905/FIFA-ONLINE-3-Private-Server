from pathlib import Path
import os,json,gzip,time
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4';os.environ['MKL_NUM_THREADS']='4'
import numpy as np
from sklearn.linear_model import Ridge
P=Path(__file__).resolve().parent;O=P/'residual-results';O.mkdir(exist_ok=True);d=np.load(P/'data.npz');X=d['X'].astype(np.float64);y=d['y'];base=np.load(P/'frozen-base-predictions.npz')['log_prediction'];schema=json.loads((P/'encoder.json').read_text());meta=json.loads((P/'data-meta.json').read_text());split=json.loads((P/'split-indices.json').read_text());train=np.array(split['train']);val=np.array(split['validation']);test=np.array(split['test']);names=meta['features'];columns=[i for i,f in enumerate(names) if f not in ('weakfootabilitytypecode','skillmoves')]
Z=X[:,columns].copy();mean=np.zeros(Z.shape[1]);std=np.ones(Z.shape[1])
for j,col in enumerate(columns):
 if col<len(meta['base_features']):mean[j]=Z[train,j].mean();std[j]=max(1e-6,Z[train,j].std())
Z=np.clip((Z-mean)/std,-8,8)
def metrics(p,idx):
 e=np.abs(p-y[idx]);return dict(log_mae=float(e.mean()),within_2x=float((e<=np.log(2)).mean()),within_3x=float((e<=np.log(3)).mean()),median_error_factor=float(np.exp(np.median(e))))
results={'frozen_baseline':dict(validation=metrics(base[val],val),test=metrics(base[test],test))};models={};residual=np.clip(y[train]-base[train],-2,2)
for alpha in (10,100,1000,10000):
 model=Ridge(alpha=alpha).fit(Z[train],residual);p=base+model.predict(Z);label=str(alpha);models[label]=(model,p);results[label]=dict(validation=metrics(p[val],val),test=metrics(p[test],test));print('RESIDUAL',alpha,json.dumps(results[label]),flush=True)
# Zero correction is an explicit validation-only safeguard against regression.
choice=min(results,key=lambda key:results[key]['validation']['log_mae']);model,p=models.get(choice,(None,base))
with gzip.open(P/'frozen-base-model.json.gz','rt',encoding='utf8') as file:network=json.load(file)
export=dict(schema=4,type='encoded_residual_ensemble',features=schema['raw_fields'],encoded_features=names,encoder=schema,base_network=network,correction=dict(columns=columns,mean=mean.tolist(),std=std.tolist(),weight=model.coef_.tolist() if model is not None else [0.]*len(columns),bias=float(model.intercept_) if model is not None else 0.),star_monotonicity_preserved=True,price_unit='historical normalized EP at +1')
with gzip.open(O/'selected-model.json.gz','wt',encoding='utf8') as file:json.dump(export,file)
probes=json.loads((P/'encoding-probes.json').read_text())
for probe,i in zip(probes,test[:100]):probe['log_prediction']=float(p[i])
(O/'inference-probes.json').write_text(json.dumps(probes))
report=dict(status='COMPLETED',selected_on_validation=choice,results=results,selected_test=metrics(p[test],test),identity_and_season_excluded=True,base_network_fit='Original numeric network fit on train groups only, checkpoint selected on validation; no refit that had seen validation',correction_weakfoot_skillmoves_excluded_to_preserve_monotonicity=True,raw_fields=len(schema['raw_fields']),encoded_features=len(names),production_changed=False)
(O/'training-report.json').write_text(json.dumps(report,indent=2));print('RESIDUAL_COMPLETED',choice,json.dumps(report['selected_test']),flush=True)
