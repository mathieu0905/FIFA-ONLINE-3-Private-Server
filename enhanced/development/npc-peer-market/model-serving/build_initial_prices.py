"""Run the selected neural network once, offline; emit only database seed values."""
from pathlib import Path
import os
os.environ['OPENBLAS_NUM_THREADS']='4';os.environ['OMP_NUM_THREADS']='4'
import gzip,hashlib,json,math,sqlite3,sys,time
P=Path(__file__).resolve().parent;R=P.parent;sys.path[:0]=[str(R/'analysis-deps'),str(R/'expanded-training')]
import numpy as np
from expanded_value_model import ExpandedValueModel
MODEL=R/'highend-training/results/selected-model.json.gz';DB=Path('D:/FO3ID/server/gamedata/fifadb.sqlite');model=ExpandedValueModel(MODEL);m=model.model
with sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;rows=[dict(r) for r in db.execute('select spid,'+','.join(m['features'])+' from players order by spid')]
source_rows=[[r['spid']]+[r[f] for f in m['features']] for r in rows];digest=hashlib.sha256(json.dumps(source_rows,separators=(',',':')).encode()).hexdigest()
members=[]
for member in m['members']:
 c=dict(member)
 for key in ('mean','std','skip_weight','star_raw','star_gate_weight','star_gate_bias'):c[key]=np.array(c[key],dtype=np.float64)
 c['star_raw']=np.log1p(np.exp(c['star_raw']));c['layers']=[dict(type=l['type'],**dict(weight=np.array(l['weight'],dtype=np.float64),bias=np.array(l['bias'],dtype=np.float64))) if l['type']=='linear' else l for l in c['layers']];members.append(c)
def predict(raw):
 X=np.array([model.encode(a) for a in raw],dtype=np.float64);outputs=[]
 for member in members:
  z=np.clip((X-member['mean'])/member['std'],-8,8);base=z[:,member['columns']];h=base
  for layer in member['layers']:
   if layer['type']=='linear':h=h@layer['weight'].T+layer['bias']
   else:h=h/(1+np.exp(-np.clip(h,-700,700)))
  value=h[:,0]+base@member['skip_weight']+member['skip_bias'];amount=np.zeros((len(raw),2))
  for j,thresholds in enumerate(((2,3,4,5,6),(1,2,3,4,5))):
   for k,t in enumerate(thresholds):amount[:,j]+=(X[:,m['star_indices'][j]]>=t)*member['star_raw'][j,k]
  gate=1/(1+np.exp(-np.clip(base@member['star_gate_weight'].T+member['star_gate_bias'],-700,700)));value+=(amount*gate).sum(1);outputs.append(value*member['y_std']+member['y_mean'])
 return np.mean(outputs,axis=0)
start=time.monotonic();prices=[];cap=5_600_000_000_000_000;capped=[]
for off in range(0,len(rows),1024):
 batch=rows[off:off+1024];logs=predict(batch)
 for r,v in zip(batch,logs):
  assert math.isfinite(float(v));raw=max(1,round(math.exp(float(v))));price=max(1,raw//1000)
  if price>cap:capped.append(r['spid']);price=cap
  prices.append([r['spid'],price])
 if off%8192==0:print('PRICES',len(prices),'/',len(rows),'seconds',round(time.monotonic()-start,1),flush=True)
sample=[rows[0],next(r for r in rows if r['spid']==30238380),next(r for r in rows if r['spid']==19001625)]
batch=predict(sample);error=max(abs(float(v)-model.log_predict(r)) for r,v in zip(sample,batch));assert error<1e-6,error
source_sha=hashlib.sha256(MODEL.read_bytes()).hexdigest();seed_digest=hashlib.sha256(json.dumps(prices,separators=(',',':')).encode()).hexdigest()
seed=dict(schema=1,model_sha256=source_sha,price_region='kr',denomination_divisor=1000,profile_fields=m['features'],profile_sha256=digest,seed_prices_sha256=seed_digest,rows=prices,policy='One-time initial prices only. Do not rerun or overwrite existing current prices on startup.')
with gzip.open(P/'initial-price-seed.json.gz','wb',compresslevel=1) as file:file.write(json.dumps(seed,separators=(',',':')).encode())
report={k:v for k,v in seed.items() if k!='rows'};report.update(rows=len(prices),capped_spids=capped,elapsed_seconds=time.monotonic()-start,maximum_inference_log_difference=error,source_model_path=str(MODEL),sample_prices={str(spid):price for spid,price in prices if spid in (30238380,30001625,19001625,30037576,84001625)})
(P/'seed-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
