"""Verify the portable network and value the current three official seasons."""
from pathlib import Path
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','4');os.environ.setdefault('OMP_NUM_THREADS','4')
import hashlib,json,math,sqlite3,sys
P=Path(__file__).resolve().parent;R=P.parent;sys.path[:0]=[str(R/'analysis-deps'),str(R/'expanded-training')]
import numpy as np
from expanded_value_model import ExpandedValueModel
F=P/'results';M=F/'selected-model.json.gz';model=ExpandedValueModel(M);m=model.model
def predict(raw):
 X=np.array([model.encode(a) for a in raw],dtype=np.float64);outputs=[]
 for member in m['members']:
  z=np.clip((X-np.array(member['mean']))/np.array(member['std']),-8,8);base=z[:,member['columns']];h=base
  for layer in member['layers']:
   if layer['type']=='linear':h=h@np.array(layer['weight']).T+np.array(layer['bias'])
   else:h=h/(1+np.exp(-np.clip(h,-700,700)))
  value=h[:,0]+base@np.array(member['skip_weight'])+member['skip_bias'];w=np.log1p(np.exp(np.array(member['star_raw'])));amount=np.zeros((len(raw),2))
  for j,thresholds in enumerate(((2,3,4,5,6),(1,2,3,4,5))):
   for k,t in enumerate(thresholds):amount[:,j]+=(X[:,m['star_indices'][j]]>=t)*w[j,k]
  gate=1/(1+np.exp(-np.clip(base@np.array(member['star_gate_weight']).T+np.array(member['star_gate_bias']),-700,700)));value+=(amount*gate).sum(1);outputs.append(value*member['y_std']+member['y_mean'])
 return np.mean(outputs,axis=0)
probes=json.loads((F/'inference-probes.json').read_text('utf8'))
for p in probes:assert model.encode(p['raw'])==p['encoded']
gpu=predict([p['raw'] for p in probes]);err=max(abs(float(v)-p['log_prediction']) for v,p in zip(gpu,probes));assert err<.001,err
standard=max(abs(model.log_predict(p['raw'])-float(v)) for p,v in zip(probes[:3],gpu[:3]));assert standard<1e-6,standard
report=json.loads((F/'training-report.json').read_text('utf8'));t=np.load(F/'test-predictions.npz');dataset=json.loads((P/'dataset.json').read_text('utf8'))
source={r['spid']:r for r in json.loads((R/'clean-training/regional-source.json').read_text('utf8'))['quotes']}
real_by_id={r['spid']:r for r in dataset if r['kind']=='real'}
for r in dataset:
 assert r['region']=='kr'
 if r['kind']=='real':assert r['price']==source[r['spid']]['prices']['kr']
 else:
  assert r['partition'] in ('train','validation') and r['anchor_partition']==r['partition']
  ids=r.get('anchor_spids') or [r['anchor_spid']]
  for i in ids:assert real_by_id[i]['partition']==r['partition']
  if r['rule'].startswith('user_nostalgia') and r.get('anchor_spid'):
   peers=[q for q in real_by_id.values() if q['playerid']==r['playerid']]
   if any(q['season']==30 for q in peers):assert real_by_id[r['anchor_spid']]['season']==30
   elif any(q['season']==93 for q in peers):assert real_by_id[r['anchor_spid']]['season']==93
for i in t['indices']:assert dataset[int(i)]['kind']=='real' and dataset[int(i)]['partition']=='test'
def metrics(actual,pred):
 e=np.abs(actual-pred);return dict(log_mae=float(e.mean()),median_error_factor=float(np.exp(np.median(e))),within_2x=float((e<=np.log(2)).mean()),within_3x=float((e<=np.log(3)).mean()),p90_error_factor=float(np.exp(np.quantile(e,.9))))
actual=metrics(t['y'],t['new'])
for k,v in actual.items():assert abs(v-report['selected_refit_test']['overall'][k])<1e-7
assert report['price_region']=='kr'
verify=dict(status='PASS',encoding_probes=len(probes),gpu_parity_probes=len(probes),maximum_gpu_log_error=err,standard_inference_probes=3,maximum_standard_log_error=standard,real_test_rows=len(t['y']),synthetic_test_rows=0,metrics_recomputed=True,all_real_labels_match_raw_KR_source=True,all_synthetic_anchors_same_partition=True,nostalgia_UL_WL_priority_verified=True)
(F/'local-verification.json').write_text(json.dumps(verify,indent=2),'utf8')
with sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;rows=[dict(r) for r in db.execute('select * from players where spid/1000000 in (19,84,30) order by spid')];names={r['playerid']:r['full'] for r in db.execute('select * from nameschi')}
registry=json.loads(Path('D:/FO3ID/server/gamedata/custom_rosters.json').read_text('utf8'));metadata={r['fo3_spid']:r for r in registry['cards']};quotes={r['spid']:r for r in dataset if r['kind']=='real'};raw=[{f:r[f] for f in m['features']} for r in rows];v=predict(raw)
result=[]
for r,a,p in zip(rows,raw,v):
 pid=r['playerid'];s=r['spid']//1000000;ref=quotes.get(r['spid']);price=max(1,round(math.exp(float(p))));meta=metadata.get(r['spid'],{})
 same=[q for q in quotes.values() if q['playerid']==pid];anchor=next((q for q in same if q['spid']==meta.get('template_spid')),None) if s==84 else None
 if not anchor and same:anchor=max(same,key=lambda q:(q['season']==30,q['season']==93,q['season']==91,q['ovr'],q['price']))
 result.append(dict(spid=r['spid'],playerid=pid,name=meta.get('name_zh') or names.get(pid,str(pid)),season=s,predicted_kr_ep=price,game_ep=price//1000,observed_kr_ep=ref['price'] if ref else None,observed_price_used_in_final_training=bool(ref and ref['partition']!='test'),same_player_anchor_spid=anchor['spid'] if anchor else None,same_player_anchor_kr_ep=anchor['price'] if anchor else None,moments_equivalent_plus8_reference_kr_ep=anchor['price']*1090 if anchor and s==84 else None,raw_attributes=a,encoding_diagnostics=model.diagnostics(a)))
output=dict(status='READ_ONLY_VALUED',price_region='kr',model_sha256=hashlib.sha256(M.read_bytes()).hexdigest(),unit='Raw KR historical EP; game_ep is a denomination preview using /1000, not a currency conversion or installed live quote',rows=result,production_changed=False)
(P/'season-values.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(verify,indent=2))
for r in result:
 if r['season']==30 or (r['season'] in (19,84) and r['playerid'] in (1625,28130,37576,190042,238380)):print(json.dumps({k:r[k] for k in ('spid','name','season','game_ep','observed_kr_ep','same_player_anchor_spid','moments_equivalent_plus8_reference_kr_ep')},ensure_ascii=False))
