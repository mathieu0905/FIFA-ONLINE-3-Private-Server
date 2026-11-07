"""Exercise exact production EXP functions with memory-only synthetic cards/stacks."""
from pathlib import Path
import ast,types,functools,json,copy
S=Path('D:/FO3ID/server');O=Path(__file__).parent
tree=ast.parse((S/'http_config.py').read_text('utf-8-sig'))
names={'iid','make_levelinfo','player_levelinfo','gain_exp','use_item'}
ns={'PLAYER_MAX_LEVEL':30,'ITEMS':{500:('fixture','','PLAYER_EXP_CAPSULE',{'exp':500},''),20000:('fixture','','PLAYER_EXP_CAPSULE',{'exp':20000},'')}}
needs=dict(zip(range(23,30),(6000,9000,13500,20000,30000,45000,67500)))
ns['player_need']=lambda lv:needs.get(lv,100*lv)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'<exact production EXP functions>','exec'),ns)
hc=types.SimpleNamespace(**ns)
extension=ast.parse((S/'experience_levels.py').read_text('utf8'))
install=next(n for n in extension.body if isinstance(n,ast.FunctionDef) and n.name=='install')
wrapper=next(n for n in install.body if isinstance(n,ast.FunctionDef) and n.name=='use_item')
wrapped={'hc':hc,'original_use':ns['use_item'],'functools':functools}
exec(compile(ast.Module(body=[wrapper],type_ignores=[]),'<exact production expected-snapshot wrapper>','exec'),wrapped)
use=wrapped['use_item'];passed=[]
def fixture(level=1,exp=0,stock=3,denom=500):
    p={'_id':'synthetic-only','spid':1,'levelinfo':{'level':level,'exp':exp}}
    it={'_id':'synthetic-stack','itemid':denom,'remains':stock}
    coach={'items':[it]};st={'teams':{'0':{'players':[p]}}}
    return st,coach,it,p
def req(f,count):
    st,c,it,p=f;li=hc.player_levelinfo(p)
    return dict(targetid=p['_id'],count=count,expected=dict(level=li['level'],exp=li['exp'],remains=it['remains']))
f=fixture();q=req(f,2);result=use(f[0],0,f[1],f[2],q)
assert result['count']==2 and f[2]['remains']==1 and f[3]['levelinfo']==dict(level=5,exp=0)
passed.append('two 500 coupons consume exactly2 and upgrade level1 to5')
before=copy.deepcopy(f);assert not use(f[0],0,f[1],f[2],q)['result'] and f==before
passed.append('duplicate expected-snapshot request rejected without second consumption')
f=fixture(level=23,stock=16,denom=20000);q=req(f,16);result=use(f[0],0,f[1],f[2],q)
assert result['count']==10 and f[2]['remains']==6 and f[3]['levelinfo']==dict(level=30,exp=0)
passed.append('level23 to30 consumes10 of16; keeps6 unused')
for count in (0,-1,4,1.5,True,'nan',float('inf')):
    f=fixture();before=copy.deepcopy(f)
    assert not use(f[0],0,f[1],f[2],req(f,count))['result'] and f==before
passed.append('invalid zero negative excess fractional boolean nonfinite quantities do not mutate')
for flag in ('lock','locked'):
    f=fixture();f[3][flag]=True;before=copy.deepcopy(f)
    assert not use(f[0],0,f[1],f[2],req(f,2))['result'] and f==before
passed.append('both lock flags reject without mutation')
f=fixture();q=req(f,2);f[2]['remains']=2;before=copy.deepcopy(f)
assert not use(f[0],0,f[1],f[2],q)['result'] and f==before
passed.append('inventory concurrent change rejects stale expected snapshot')
f=fixture();q=req(f,2);f[3]['levelinfo']['exp']=10;before=copy.deepcopy(f)
assert not use(f[0],0,f[1],f[2],q)['result'] and f==before
passed.append('player concurrent experience change rejects stale expected snapshot')
f=fixture();result=use(f[0],0,f[1],f[2],req(f,3));assert result['count']==3 and f[1]['items']==[]
passed.append('exhausted stack removed exactly once')
f=fixture(level=30);before=copy.deepcopy(f);assert not use(f[0],0,f[1],f[2],req(f,1))['result'] and f==before
passed.append('max level rejects without consuming')
# Persistence format round-trip is in memory; no production state/save APIs called.
f=fixture();use(f[0],0,f[1],f[2],req(f,2));stored=json.loads(json.dumps(dict(team=f[0],coach=f[1])))
assert stored['team']['teams']['0']['players'][0]['levelinfo']==dict(level=5,exp=0) and stored['coach']['items'][0]['remains']==1
passed.append('updated experience and inventory survive JSON roundtrip; native reload remains pending')
result=dict(status='PRODUCTION_FUNCTIONS_MEMORY_REGRESSION_PASS',checks=passed,real_state_read=False,real_state_written=False,native_consumption_verified=False)
(O/'batch-server-tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8');print(json.dumps(result,indent=2))
