"""Portable FO3 +1 historical value prototype; read-only, never writes live state."""
from pathlib import Path
import math,json,sqlite3,argparse
ROOT=Path(__file__).resolve().parent
class ValueModel:
 def __init__(self,path=None):
  self.model=json.loads(Path(path or ROOT/'value-model.json').read_text('utf8'))
  self.references=json.loads((ROOT/'historical-reference-prices.json').read_text('utf8'))
 def prepare(self,row):
  row=dict(row);row['season']=row['spid']//1000000
  role=self.model['position_roles'][row['preferredposition1']]
  row['ovr']=sum(row[k]*v for k,v in self.model['role_weights'][role].items())//100
  return row
 def features(self,row):
  values=[]
  for f in self.model['features']:
   if f.startswith('stat:'):v=row[f[5:]]-row['ovr']
   elif ':' not in f:v=row.get(f,0)
   else:
    typ,n=f.split(':');n=int(n)
    if typ=='season':v=int(row['season']==n)
    elif typ=='pos':v=int(row['preferredposition1']==n)
    elif typ=='body':v=int(row['bodytypecode']==n)
    else:v=(int(row.get(typ,0))&0xffffffff)>>n&1
   values.append(v)
  return values
 def log_predict(self,row):
  x=self.features(self.prepare(row));value=self.model['baseline']
  for tree in self.model['trees']:
   i=0
   while not tree[i][5]:
    feature,threshold,left,right,_,_=tree[i]
    i=left if x[feature]<=threshold else right
   value+=tree[i][4]
  return value
 def predict(self,row):return max(1,round(math.exp(self.log_predict(row))))
 def estimate(self,row):
  row=self.prepare(row)
  estimate=self.predict(row)
  observed=self.references.get(str(row['spid']),0)
  return dict(spid=row['spid'],ovr=row['ovr'],estimated_historical_plus1_ep=estimate,reference_anchor_plus1_ep=observed if observed>0 else estimate,anchor_source='historical exact card' if observed>0 else 'model fallback',known_season=row['season'] in self.model['seasons'],scope='historical regional estimate; not current live EP or measured hand feel')
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('spid',type=int);a=parser.parse_args()
 db=sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row
 row=db.execute('select * from players where spid=?',(a.spid,)).fetchone()
 if row is None:parser.error('Unknown SPID')
 result=ValueModel().estimate(row)
 historical=json.loads(Path('D:/FO3ID/server/gamedata/fa_prices.json').read_text('utf8')).get(str(a.spid),0)
 result['observed_historical_plus1_ep']=historical if historical>0 else None
 result['recommended_anchor']='observed historical price' if historical>0 else 'model fallback, needs calibration'
 print(json.dumps(result,ensure_ascii=False,indent=2))
