"""Standard-library inference for the model selected by the remote training job."""
from pathlib import Path
import math,json,argparse
R=Path(__file__).resolve().parent
class RemoteValueModel:
 def __init__(self,path=None):self.model=json.loads(Path(path or R/'gpu-results/selected-model.json').read_text('utf8'))
 def log_predict(self,attributes):
  x=[float(attributes[f]) for f in self.model['features']]
  if not all(math.isfinite(v) for v in x):raise ValueError('Attributes must be finite')
  m=self.model
  if m['type']=='gpu_attribute_ensemble':
   outputs=[]
   for member in m['members']:
    z=[max(-m['input_clip'],min(m['input_clip'],(v-a)/b)) for v,a,b in zip(x,member['mean'],member['std'])]
    base=[z[i] for i in member['columns']];h=base
    for layer in member['layers']:
     if layer['type']=='linear':h=[sum(a*b for a,b in zip(weights,h))+bias for weights,bias in zip(layer['weight'],layer['bias'])]
     elif layer['type']=='silu':h=[v/(1+math.exp(-v)) if v>-700 else 0. for v in h]
    value=h[0]+sum(a*b for a,b in zip(member['skip_weight'],base))+member['skip_bias']
    if m['kind']=='stars':
     wf,sm=[x[i] for i in m['star_indices']]
     thresholds=((2,3,4,5,6),(1,2,3,4,5))
     for index,v in enumerate((wf,sm)):
      amount=sum(math.log1p(math.exp(w)) for w,t in zip(member['star_raw'][index],thresholds[index]) if v>=t)
      g=sum(a*b for a,b in zip(member['star_gate_weight'][index],base))+member['star_gate_bias'][index]
      value+=amount/(1+math.exp(-g))
    outputs.append(value*member['y_std']+member['y_mean'])
   return sum(outputs)/len(outputs)
  if m['type']=='hgb':
   value=m['baseline']
   for tree in m['trees']:
    i=0
    while not tree[i][5]:
     feature,threshold,left,right,_,_=tree[i];i=left if x[feature]<=threshold else right
    value+=tree[i][4]
   return value
  z=[max(-m['input_clip'],min(m['input_clip'],(v-a)/b)) for v,a,b in zip(x,m['x_mean'],m['x_std'])]
  outputs=[]
  for member in m['members']:
   h=z
   for layer in member['layers']:
    if layer['type']=='linear':h=[sum(a*b for a,b in zip(weights,h))+bias for weights,bias in zip(layer['weight'],layer['bias'])]
    elif layer['type']=='silu':h=[v/(1+math.exp(-v)) if v>-700 else 0. for v in h]
    else:raise ValueError('Unknown layer')
   skip=sum(a*b for a,b in zip(member['skip_weight'],z))+member['skip_bias']
   outputs.append((h[0]+skip)*m['y_std']+m['y_mean'])
  return sum(outputs)/len(outputs)
 def predict(self,attributes):return max(1,round(math.exp(self.log_predict(attributes))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('attributes_json',type=Path);a=p.parse_args();attributes=json.loads(a.attributes_json.read_text('utf-8-sig'))
 print(json.dumps(dict(plus1_historical_reference=RemoteValueModel().predict(attributes),unit='historical normalized EP; calibrate before live use'),ensure_ascii=False))
