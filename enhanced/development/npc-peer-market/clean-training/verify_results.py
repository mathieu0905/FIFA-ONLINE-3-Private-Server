"""Verify portable inference and benchmark arithmetic against remote GPU probes."""
from pathlib import Path
import json,math,sys
P=Path(__file__).resolve().parent;R=P.parent
RESULTS=P/'results/final' if (P/'results/final/training-report.json').exists() else P/'results'
sys.path[:0]=[str(R/'analysis-deps'),str(R/'expanded-training')]
import numpy as np
from expanded_value_model import ExpandedValueModel
model=ExpandedValueModel(RESULTS/'selected-model.json.gz')
probes=json.loads((RESULTS/'inference-probes.json').read_text('utf8'))
errors=[]
for probe in probes:
 assert model.encode(probe['raw'])==probe['encoded']
for probe in probes[:20]:errors.append(abs(model.log_predict(probe['raw'])-probe['log_prediction']))
assert max(errors)<.001,errors
pred=np.load(RESULTS/'test-predictions.npz')
def metrics(y,p):
 e=np.abs(y-p);return dict(log_mae=float(e.mean()),median_error_factor=float(np.exp(np.median(e))),within_2x=float((e<=np.log(2)).mean()),within_3x=float((e<=np.log(3)).mean()),p90_error_factor=float(np.exp(np.quantile(e,.9))))
actual=metrics(pred['y'],pred['new']);report=json.loads((RESULTS/'training-report.json').read_text('utf8'))
for k,v in actual.items():assert abs(v-report['selected_refit_test'][k])<1e-7,(k,v,report['selected_refit_test'][k])
old=metrics(pred['y'],pred['old'])
for k,v in old.items():assert abs(v-report['old_model_on_same_test'][k])<1e-7
rows=json.loads((P/'clean-data.json').read_text('utf8'));by_spid={r['spid']:r for r in rows}
details=[]
for spid,y,new,oldp in zip(pred['spids'],pred['y'],pred['new'],pred['old']):
 r=by_spid[int(spid)];details.append(dict(spid=int(spid),name=r['name'],season=r['season'],position=r['preferredposition1'],price=r['price'],prediction=round(math.exp(float(new))),old_prediction=round(math.exp(float(oldp))),error_factor=math.exp(abs(float(new-y)))))
groups={}
for name,key in [('season','season'),('position','position')]:
 groups[name]={str(v):dict(rows=sum(r[key]==v for r in details),**metrics(pred['y'][[r[key]==v for r in details]],pred['new'][[r[key]==v for r in details]])) for v in sorted({r[key] for r in details})}
out=dict(status='PASS',raw_encoding_probes=len(probes),portable_gpu_probes=len(errors),maximum_log_prediction_difference=max(errors),metrics_recomputed=True,old_model_on_same_test=old,new_model_on_same_test=actual,cohorts=groups,production_changed=False)
if (RESULTS/'extra-test-predictions.npz').exists():
 ep=np.load(RESULTS/'extra-test-predictions.npz');em=metrics(ep['y'],ep['new'])
 for k,v in em.items():assert abs(v-report['extra_test'][k])<1e-7
 out.update(extra_test=em,extra_test_rows=len(ep['y']))
(RESULTS/'local-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf8')
(RESULTS/'test-cards.json').write_text(json.dumps(sorted(details,key=lambda r:-r['error_factor']),ensure_ascii=False,indent=2),'utf8')
print(json.dumps({k:v for k,v in out.items() if k!='cohorts'},ensure_ascii=False,indent=2))
