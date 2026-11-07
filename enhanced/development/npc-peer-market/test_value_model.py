from pathlib import Path
import sys,os,json,math
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4'
sys.path.insert(0,'D:/fifaol3/npc-peer-market/analysis-deps');sys.path.insert(0,'D:/fifaol3/npc-peer-market')
source=Path('D:/fifaol3/npc-peer-market/fit_value_model.py').read_text('utf-8-sig')
ns={'__file__':'D:/fifaol3/npc-peer-market/fit_value_model.py'}
exec(compile(source.split('train,test=')[0],ns['__file__'],'exec'),ns)
X,y,rows=ns['X'],ns['y'],ns['rows'];m=ns['HistGradientBoostingRegressor'](loss='absolute_error',learning_rate=.08,max_iter=240,max_leaf_nodes=23,min_samples_leaf=20,l2_regularization=5,random_state=2026).fit(X,y)
from predict_value import ValueModel
v=ValueModel();indexes=list(range(0,len(rows),max(1,len(rows)//200)))
a=m.predict(X[indexes]);b=[v.log_predict(rows[i]) for i in indexes]
error=max(abs(float(x)-z) for x,z in zip(a,b));assert error<1e-9,error
known=next(r for r in rows if r['spid']==30001625);assert v.estimate(known)['reference_anchor_plus1_ep']==known['price']
# Unknown IDs do not accidentally inherit an existing card's exact price.
unknown=dict(known,spid=13000001);out=v.estimate(unknown);assert out['anchor_source']=='model fallback' and not out['known_season']
result=dict(portable_prediction_checks=len(indexes),max_log_error=error,known_historical_premium_preserved=True,unknown_season_flagged=True,production_changed=False)
Path('D:/fifaol3/npc-peer-market/prototype-tests.json').write_text(json.dumps(result,indent=2),'utf8');print(result)
