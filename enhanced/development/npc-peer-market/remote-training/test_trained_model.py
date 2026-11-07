from pathlib import Path
import sys,json,math,argparse
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R))
from predict_trained_value import RemoteValueModel
parser=argparse.ArgumentParser();parser.add_argument('--results',type=Path,default=R/'gpu-results');args=parser.parse_args();D=args.results
m=RemoteValueModel(D/'selected-model.json')
probes=json.loads((D/'inference-probes.json').read_text('utf8'))
errors=[]
for probe in probes:
 attrs=dict(zip(m.model['features'],probe['attributes']))
 errors.append(abs(m.log_predict(attrs)-probe['log_prediction']))
assert max(errors)<1e-4,max(errors)
row=dict(zip(m.model['features'],probes[0]['attributes']))
a=m.predict(dict(row,name='A',playerid=1,season=93,price=1))
b=m.predict(dict(row,name='B',playerid=999,season=13,price=99999999));assert a==b
matrix=[]
for wf in (2,3,4,5):
 for sm in (1,2,3,4):
  attrs=dict(row,weakfootabilitytypecode=wf,skillmoves=sm)
  matrix.append(dict(weakfoot_code=wf,skillmoves_code=sm,value=m.predict(attrs)))
if m.model['kind']=='stars':
 for wf in (2,3,4,5):
  values=[x['value'] for x in matrix if x['weakfoot_code']==wf];assert values==sorted(values)
 for sm in (1,2,3,4):
  values=[x['value'] for x in matrix if x['skillmoves_code']==sm];assert values==sorted(values)
try:m.predict(dict(row,height=float('nan')));raise AssertionError('NaN accepted')
except ValueError:pass
out=dict(passed=True,probes=len(errors),max_log_error=max(errors),identity_season_invariance=True,star_monotonicity=m.model['kind']=='stars',controlled_star_matrix=matrix,production_changed=False)
(D/'local-verification.json').write_text(json.dumps(out,indent=2),'utf8')
print(json.dumps({k:v for k,v in out.items() if k!='controlled_star_matrix'}))
