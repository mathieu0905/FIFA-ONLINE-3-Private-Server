from pathlib import Path
import json,time,os
os.environ['OMP_NUM_THREADS']='4';os.environ['MKL_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4'
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
P=Path(__file__).resolve().parent;O=P/'tree-control';O.mkdir(exist_ok=True);d=np.load(P/'data.npz');X=d['X'];y=d['y'];split=json.loads((P/'split-indices.json').read_text());train=split['train'];val=split['validation'];test=split['test'];report={}
def metric(p,idx):
 e=np.abs(y[idx]-p);return dict(log_mae=float(e.mean()),within_2x=float((e<=np.log(2)).mean()),within_3x=float((e<=np.log(3)).mean()))
for leaf in (20,50):
 m=HistGradientBoostingRegressor(loss='absolute_error',learning_rate=.06,max_iter=500,max_leaf_nodes=23,min_samples_leaf=leaf,l2_regularization=10,early_stopping=False,random_state=2026).fit(X[train],y[train]);report[str(leaf)]=dict(validation=metric(m.predict(X[val]),val),test=metric(m.predict(X[test]),test))
 print('TREE_CONTROL',leaf,json.dumps(report[str(leaf)]),flush=True)
(O/'report.json').write_text(json.dumps(report,indent=2))
