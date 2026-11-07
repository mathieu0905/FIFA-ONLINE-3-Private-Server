"""Exercise the actual host routes against temporary assets and a temporary price DB."""
from pathlib import Path
import concurrent.futures,copy,hashlib,importlib.util,json,os,sqlite3,sys,tempfile,types
from fractions import Fraction
from urllib.parse import urlencode
from unittest.mock import patch
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent; S=Path('D:/FO3ID/server')
T=Path(tempfile.mkdtemp(prefix='routes-',dir=R))
source=S if '--installed' in sys.argv else R
sys.argv=['http_config.py']
os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi',FO3_ADMIN_PORT='0')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
protected={str(S/'gamedata'/n):sha(S/'gamedata'/n) for n in ('state.json','shop.json')}
(T/'state.json').write_bytes((S/'gamedata/state.json').read_bytes())
(T/'rates.json').write_bytes((S/'gamedata/enhancement_rates.json').read_bytes())
with sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(T/'prices.sqlite') as dst:src.backup(dst)

def audit(event,args):
    if event=='open':
        p,m,f=args
        if isinstance(p,(str,bytes,os.PathLike)) and ((isinstance(m,str) and any(c in m for c in 'wax+')) or (isinstance(f,int) and f&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))):
            target=Path(os.fsdecode(p)).resolve()
            if not target.is_relative_to(T) and not target.is_relative_to(R):raise PermissionError('Test refuses external write: '+str(target))
    if event=='sqlite3.connect':
        path=str(args[0])
        if path!=':memory:' and 'mode=ro' not in path and not path.startswith(T.as_uri()) and not Path(path).resolve().is_relative_to(T):raise PermissionError('Test refuses writable DB: '+path)
sys.addaudithook(audit)
original_connect=sqlite3.connect
def connect_readonly_formal(database,*args,**kwargs):
    path=str(database)
    if path!=':memory:' and not path.startswith('file:') and Path(path).resolve().is_relative_to(S):
        database=Path(path).resolve().as_uri()+'?mode=ro';kwargs['uri']=True
    return original_connect(database,*args,**kwargs)
sqlite3.connect=connect_readonly_formal
sys.path.insert(0,str(S))
name='enhancement_progression'
text=(R/(name+'.py')).read_text('utf8')
mod=types.ModuleType(name);mod.__file__=str(R/(name+'.py'));sys.modules[name]=mod;exec(compile(text,mod.__file__,'exec'),mod.__dict__)
name='enhancement_settings'
text=(S/(name+'.py')).read_text('utf8').replace("Path(hc.HERE) / 'gamedata' / 'enhancement_rates.json'",repr(str(T/'rates.json'))).replace('path = '+repr(str(T/'rates.json')),'path = Path('+repr(str(T/'rates.json'))+')')
mod=types.ModuleType(name);mod.__file__=str(S/(name+'.py'));sys.modules[name]=mod;exec(compile(text,mod.__file__,'exec'),mod.__dict__)
source_text=(S/'http_config.py').read_text('utf8')
source_text=source_text.replace('STATE = os.path.join(HERE, "gamedata", "state.json")', 'STATE = '+repr(str(T/'state.json'))+'\nMARKET_PRICE_DB_PATH = '+repr(str(T/'prices.sqlite')))
h=types.ModuleType('http_config');h.__file__=str(S/'http_config.py');sys.modules['http_config']=h
exec(compile(source_text,h.__file__,'exec'),h.__dict__)
p=sys.modules['enhancement_progression']; protection=sys.modules['enhancement_protection40']

base=copy.deepcopy(h._state());slot=h._default_slot(base);cases=0
checks=[]
def call(uri):
 path,_,q=uri.partition('?')
 with h.STATE_LOCK:return json.loads((h.ENDPOINTS.get(path) or h.route(path))(q,b'{}')[1])
def getcard(st,ident):return next((c for c in st['teams'][str(slot)]['players'] if h.iid(c)==ident),None)
for material in (6,7,8,9):
 for point in (0,1):
  for protected in (False,True):
   for success in (False,True):
    st=copy.deepcopy(base);st.pop('enhance_restore',None)
    coach=h.my_coach(st);coach['ep']=10**18;coach['es']=10**9
    team=st['teams'][str(slot)]
    a=h.add_player(team,93192181,9);b=h.add_player(team,93192181,material)
    a['locked']=b['locked']=False;a['lock']=b['lock']=False
    aid,bid=h.iid(a),h.iid(b)
    h._save(st)
    query='?protection=1' if protected else ''
    q=call(f'/player/{aid}/enhance2.5/{bid}/preview/{point}/-1/-1'+query)
    assert q['result'],q
    actual=h.enhance25_rate(a,b,bool(point),None,'-1')
    assert abs(q['probability']-actual*100)<=.000500001,(q,actual)
    if protected:
     query='?'+urlencode(dict(protection=1,protection_ack=q['protection']['version'],protection_token=q['protection']['token']))
    ep=h.my_coach(h._state())['ep']
    with patch.object(h.random,'random',return_value=actual-1e-8 if success else actual+1e-8):
     r=call(f'/player/{aid}/enhance2.5/{bid}/{point}/-1/-1'+query)
    assert r['result'] and bool(r['success'])==success,r
    after=h._state();aa,bb=getcard(after,aid),getcard(after,bid)
    assert aa['grade']==(10 if success else 9 if protected else 8)
    assert bool(bb)==(protected and not success)
    assert h.my_coach(after)['ep']==ep-q['enhancepay']
    if protected:
     raw=Path(h.STATE).read_bytes();rr=call(f'/player/{aid}/enhance2.5/{bid}/{point}/-1/-1'+query)
     assert not rr['result'] and Path(h.STATE).read_bytes()==raw
    cases+=1
checks.append('32 real native route cases around exact new probability threshold: materials6/7/8/9, ES off/on, protection off/on, success/failure; displayed rate/execution agree; charges unchanged; protection-v3 keeps both on failure; token replay refused')
r=dict(status='PASS',cases=cases,checks=checks,temporary_state=str(T/'state.json'),formal_asset_writes=False,native_verified=False)
(R/'route-tests.json').write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps(r))
