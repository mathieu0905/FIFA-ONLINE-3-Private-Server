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

class ExpandedValueModel:
 def __init__(self,path=None):
  import gzip
  path=Path(path or R/'results/selected-model.json.gz')
  if str(path).endswith('.gz'):
   with gzip.open(path,'rt',encoding='utf8') as file:self.model=json.load(file)
  else:self.model=json.loads(path.read_text('utf8'))
  self.schema=self.model['encoder']
  self.inner=RemoteValueModel.__new__(RemoteValueModel)
  self.inner.model=self.model['base_network'] if self.model['type']=='encoded_residual_ensemble' else dict(self.model,features=self.model['encoded_features'],type='gpu_attribute_ensemble')
 def encode(self,raw):
  missing=[f for f in self.schema['raw_fields'] if f not in raw]
  if missing:raise ValueError('Missing gameplay fields: '+','.join(missing))
  values=[float(raw[f]) for f in self.schema['numeric']]
  if not all(math.isfinite(v) for v in values):raise ValueError('Numeric attributes must be finite')
  categories={};masks={}
  for field in self.schema['categorical_vocab']:
   value=float(raw[field])
   if not math.isfinite(value) or value!=int(value):raise ValueError('Category codes must be integers: '+field)
   categories[field]=int(value)
  for field in self.schema['trait_bits']:
   value=raw[field]
   if isinstance(value,bool) or not math.isfinite(float(value)) or float(value)!=int(value):raise ValueError('Trait masks must be exact integers')
   value=int(value)
   if not -2**31<=value<=2**32-1:raise ValueError('Trait mask outside UInt32')
   masks[field]=value&0xffffffff
  # The explicit vector schema, not JSON object order, defines network columns.
  for feature in self.schema['encoded_features'][len(self.schema['numeric']):]:
   kind,field,number=feature.split(':');number=int(number)
   if kind=='cat':values.append(int(categories[field]==number))
   elif kind=='bit':values.append((masks[field]>>number)&1)
   else:raise ValueError('Unknown encoded feature')
  return values
 def log_predict(self,raw):
  encoded=self.encode(raw)
  if self.model['type']=='encoded_residual_ensemble':
   c=self.model['correction'];z=[max(-8,min(8,(encoded[i]-mean)/std)) for i,mean,std in zip(c['columns'],c['mean'],c['std'])]
   return self.inner.log_predict(raw)+sum(a*b for a,b in zip(c['weight'],z))+c['bias']
  return self.inner.log_predict(dict(zip(self.model['encoded_features'],encoded)))
 def predict(self,raw):return max(1,round(math.exp(self.log_predict(raw))))
 def diagnostics(self,raw):
  self.encode(raw)
  return dict(unknown_categories={f:int(raw[f]) for f,vs in self.schema['categorical_vocab'].items() if int(raw[f]) not in vs},unknown_trait_bits={f:hex((int(raw[f])&0xffffffff)&~sum(1<<b for b in bs)) for f,bs in self.schema['trait_bits'].items() if (int(raw[f])&0xffffffff)&~sum(1<<b for b in bs)})

AttributeValueModel=ExpandedValueModel
