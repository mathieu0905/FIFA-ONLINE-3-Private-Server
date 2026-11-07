from pathlib import Path
import json
root=Path('D:/fifaol3/market-supply-v3');r=json.loads((root/'installation.json').read_text('utf8'))[0]
a=json.loads((Path(r['backup'])/'state.json').read_text('utf8'));b=json.loads((Path(r['server'])/'gamedata/state.json').read_text('utf8'))
def diff(a,b,path=''):
 if type(a)!=type(b):print(path,'type changed');return
 if isinstance(a,dict):
  for key in a.keys()|b.keys():
   if key in ('market_simulation','_market_owner'):continue
   if key not in a or key not in b:print(path+'/'+key,'added/removed');continue
   diff(a[key],b[key],path+'/'+key)
 elif isinstance(a,list):
  if len(a)!=len(b):print(path,'length',len(a),len(b))
  for i,(x,y) in enumerate(zip(a,b)):diff(x,y,path+'/'+str(i))
 elif a!=b:print(path,repr(a),repr(b))
diff(a,b)
