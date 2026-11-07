"""Pure attribute-to-value model. No price, name, season or ID lookup during inference."""
from pathlib import Path
import json,math,argparse,sqlite3
R=Path(__file__).resolve().parent
class AttributeValueModel:
 def __init__(self,path=None):
  self.model=json.loads(Path(path or R/'attributes-value-model.json').read_text('utf8'))
 def log_predict(self,attributes):
  missing=[f for f in self.model['features'] if f not in attributes]
  if missing:raise ValueError('Missing ability inputs: '+','.join(missing))
  x=[float(attributes[f]) for f in self.model['features']]
  if not all(math.isfinite(v) for v in x):raise ValueError('Attributes must be finite numbers')
  value=self.model['baseline']
  for tree in self.model['trees']:
   node=0
   while not tree[node][5]:
    feature,threshold,left,right,_,_=tree[node];node=left if x[feature]<=threshold else right
   value+=tree[node][4]
  return value
 def predict(self,attributes):return max(1,round(math.exp(self.log_predict(attributes))))
 def estimate(self,attributes):
  return dict(estimated_plus1_value=self.predict(attributes),unit=self.model['price_unit'],outside_training_range=[f for f in self.model['features'] if not self.model['feature_ranges'][f][0]<=float(attributes[f])<=self.model['feature_ranges'][f][1]],features_used=len(self.model['features']))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--attributes-json',type=Path);g.add_argument('--spid',type=int,help='Read attributes only from the live DB, never its price');a=p.parse_args()
 if a.attributes_json:attributes=json.loads(a.attributes_json.read_text('utf-8-sig'))
 else:
  with sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True) as db:
   db.row_factory=sqlite3.Row;row=db.execute('select * from players where spid=?',(a.spid,)).fetchone()
   if row is None:p.error('Unknown SPID')
   attributes=dict(row)
 print(json.dumps(AttributeValueModel().estimate(attributes),ensure_ascii=False,indent=2))
