"""Attribute-only value inference: lossless neural weights and fingerprint memoization."""
from pathlib import Path
import argparse,gzip,hashlib,json,math,sqlite3,struct,sys,threading

class AttributeValueModel:
 def __init__(self,path=None):
  self.path=Path(path or Path(__file__).resolve().parent/'gamedata/npc_attribute_value.json')
  self.model=json.loads(self.path.read_text('utf8'));self._lock=threading.RLock();self.cache_hits=0;self.forward_evaluations=0
  if self.model.get('type')!='attribute_neural_binary':return
  root=self.path.parent.resolve()
  def local(name):
   p=(root/name).resolve()
   if not p.is_relative_to(root) or p==root:raise ValueError('Neural asset path escape')
   return p
  weights=local(self.model['weights_file'])
  with weights.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
  if digest!=self.model['weights_sha256']:raise ValueError('Neural weights digest mismatch')
  with gzip.open(weights,'rb') as f:self._buffer=f.read()
  if sys.byteorder!='little':raise RuntimeError('This neural asset is little-endian')
  if len(self._buffer)!=self.model['weights_bytes']:raise ValueError('Neural weight length mismatch')
  self._weights=memoryview(self._buffer).cast('f');self._cache={}
  with gzip.open(local(self.model['cache_file']),'rt',encoding='utf8') as f:cache=json.load(f)
  if cache['model_sha256']!=self.model['source_model_sha256']:raise ValueError('Neural cache model mismatch')
  self._cache=cache['values'];self._codec=struct.Struct('<'+'d'*len(self.model['features']))
  for member in self.model['members']:
   for layer in member['layers']:
    if layer['type']=='linear':
     w,b=layer['weight'],layer['bias'];assert w['count']==w['rows']*w['columns'] and b['count']==w['rows']
     for d in (w,b):assert 0<=d['offset']<=d['offset']+d['count']<=len(self._weights)

 def _array(self,d):return self._weights[d['offset']:d['offset']+d['count']]
 def _input(self,attributes):
  e=self.model['encoder'];values=[];canonical={}
  for f in e['numeric']:
   v=float(attributes[f])
   if not math.isfinite(v):raise ValueError('Nonfinite numeric attribute: '+f)
   values.append(v);canonical[f]=v
  categories={};masks={}
  for f in e['categorical_vocab']:
   v=float(attributes[f])
   if not math.isfinite(v) or v!=int(v):raise ValueError('Category must be an integer: '+f)
   categories[f]=int(v);canonical[f]=v
  for f in e['trait_bits']:
   v=float(attributes[f])
   if not math.isfinite(v) or v!=int(v) or not -2**31<=v<=2**32-1:raise ValueError('Invalid trait mask: '+f)
   masks[f]=int(v)&0xffffffff;canonical[f]=float(masks[f])
  for token in e['encoded_features'][len(e['numeric']):]:
   kind,f,k=token.split(':');k=int(k);values.append(int(categories[f]==k) if kind=='cat' else (masks[f]>>k)&1)
  key=hashlib.sha256(self._codec.pack(*(canonical[f] for f in self.model['features']))).hexdigest()
  return values,key

 def _neural_log(self,x):
  m=self.model;outputs=[]
  for member in m['members']:
   mean=self._array(member['mean']);std=self._array(member['std']);z=[max(-m['input_clip'],min(m['input_clip'],(v-a)/b)) for v,a,b in zip(x,mean,std)];base=[z[i] for i in member['columns']];h=base
   for layer in member['layers']:
    if layer['type']=='linear':
     w=self._array(layer['weight']);b=self._array(layer['bias']);n=layer['weight']['columns'];h=[sum(v*a for v,a in zip(w[i*n:(i+1)*n],h))+bias for i,bias in enumerate(b)]
    else:h=[v/(1+math.exp(-v)) if v>-700 else 0. for v in h]
   value=h[0]+sum(a*b for a,b in zip(self._array(member['skip_weight']),base))+member['skip_bias']
   raw=self._array(member['star_raw']);gate=self._array(member['star_gate_weight']);bias=self._array(member['star_gate_bias']);n=len(base)
   for index,thresholds in enumerate(((2,3,4,5,6),(1,2,3,4,5))):
    amount=sum(math.log1p(math.exp(raw[index*5+j])) for j,t in enumerate(thresholds) if x[m['star_indices'][index]]>=t)
    g=sum(a*b for a,b in zip(gate[index*n:(index+1)*n],base))+bias[index]
    value+=amount/(1+math.exp(-max(-700,min(700,g))))
   outputs.append(value*member['y_std']+member['y_mean'])
  return sum(outputs)/len(outputs)

 def log_predict(self,attributes):
  if self.model.get('type')=='attribute_neural_binary':
   x,_=self._input(attributes);return self._neural_log(x)
  x=[float(attributes[f]) for f in self.model['features']]
  if not all(math.isfinite(v) for v in x):raise ValueError('Attributes must be finite')
  value=self.model['baseline']
  for tree in self.model['trees']:
   i=0
   while not tree[i][5]:
    feature,threshold,left,right,_,_=tree[i];i=left if x[feature]<=threshold else right
   value+=tree[i][4]
  return value
 def predict(self,attributes):
  if self.model.get('type')!='attribute_neural_binary':return max(1,round(math.exp(self.log_predict(attributes))))
  x,key=self._input(attributes)
  with self._lock:
   if key in self._cache:self.cache_hits+=1;return self._cache[key]
   result=max(1,round(math.exp(self._neural_log(x))));self._cache[key]=result;self.forward_evaluations+=1;return result
 def estimate(self,attributes):
  value=self.predict(attributes);ranges=self.model.get('feature_ranges',{})
  return dict(estimated_plus1_value=value,unit=self.model['price_unit'],outside_training_range=[f for f,(lo,hi) in ranges.items() if not lo<=float(attributes[f])<=hi],features_used=len(self.model['features']))
 def status(self):
  return dict(type=self.model.get('type'),revision=self.model.get('revision'),source_model_sha256=self.model.get('source_model_sha256'),price_region=self.model.get('training_region'),features=len(self.model['features']),cached_attribute_profiles=len(getattr(self,'_cache',{})),cache_hits=self.cache_hits,forward_evaluations=self.forward_evaluations)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--spid',type=int,required=True);p.add_argument('--model',type=Path);a=p.parse_args()
 with sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row;r=db.execute('select * from players where spid=?',(a.spid,)).fetchone()
  if r is None:p.error('Unknown SPID')
  print(json.dumps(AttributeValueModel(a.model).estimate(dict(r)),ensure_ascii=False,indent=2))
