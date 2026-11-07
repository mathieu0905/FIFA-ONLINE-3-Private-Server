"""Boundary regression on exact production endpoints and capacity predicates, memory only."""
from pathlib import Path
import ast,copy,json,random,types
S=Path('D:/FO3ID/server');O=Path(__file__).parent;LIMIT=2_147_483_647
source=(S/'http_config.py').read_text('utf-8-sig');tree=ast.parse(source)
names={'iid','first_team_count','balance_first_team','ep_player_move','ep_transfer_purchase','ep_item_use','ep_bag_unpack','ep_bag_unpackall'}
functions=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[])
tests=[]
def scene(count,limit):
    players=[{'_id':str(i),'spid':1,'grade':1,'levelinfo':{'level':1,'exp':0}} for i in range(count)]
    c={'items':[{'_id':'pack','itemid':123,'remains':1}],'bag':[{'_id':'bag','players':[{'spid':2},{'spid':3}]}],'ep':1000}
    st={'teams':{'0':{'players':players}},'coaches':[c]};saved=[]
    def add(t,spid,grade):
        p={'_id':'new'+str(len(t['players'])),'spid':spid,'grade':grade,'team2':True};t['players'].append(p);return p
    def bag_apply(s,e):
        s['teams']['0']['players'].extend(copy.deepcopy(e['players']));c['bag'].remove(e)
    ns=dict(MAX_PLAYERS=limit,FIRST_TEAM_MAX=limit,_state=lambda:st,_default_slot=lambda st:0,my_coach=lambda st:c,_save=lambda st:saved.append(copy.deepcopy(st)),_json=lambda x:x,coach_me_resources=lambda *args:[],on_market=lambda spid:True,player_value_price=lambda *args:100,coach_me=lambda *args:{'money':{'ep':c['ep']}},add_ep=lambda s,n:c.update(ep=c['ep']+n),add_player=add,ITEMS={},PACKS={123:None},pack_pool=lambda item:[(2,1)],pack_grade=lambda item:1,random=random,json=json,in_squad=lambda *args:False,card_price=lambda *args:1,grade_of=lambda p:p['grade'],bag_apply=bag_apply,bag_reply=lambda st:{'result':True})
    exec(compile(functions,'<exact production capacity endpoints>','exec'),ns)
    return st,c,ns,saved
for endpoint in ('purchase','pack','bag','allbags','firstteam'):
    for limit in (200,LIMIT):
        st,c,n,saves=scene(200,limit);before=copy.deepcopy(st)
        if endpoint=='purchase':result=n['ep_transfer_purchase']('2','1','100','',b'{}')
        elif endpoint=='pack':result=n['ep_item_use']('pack','',b'{}')
        elif endpoint=='bag':result=n['ep_bag_unpack']('bag','',b'{}')
        elif endpoint=='allbags':result=n['ep_bag_unpackall']('',b'{"reqUnpackItems":["bag"]}')
        else:
            st['teams']['0']['players'].append({'_id':'reserve','spid':2,'team2':True})
            before=copy.deepcopy(st);result=n['ep_player_move']('reserve','firstteam','',b'{}')
        if limit==200:
            if endpoint=='allbags':assert len(st['teams']['0']['players'])==200 and len(c['bag'])==1
            else:assert not result['result'] and st==before and not saves
        else:
            assert result['result'] and len(saves)==1
            if endpoint=='purchase':assert len(st['teams']['0']['players'])==201 and c['ep']==900
            elif endpoint=='pack':assert len(st['teams']['0']['players'])==201 and c['items']==[] and c['ep']==1000
            elif endpoint in ('bag','allbags'):assert len(st['teams']['0']['players'])==202 and c['bag']==[] and c['ep']==1000
            else:assert n['first_team_count'](st['teams']['0'])==201
    tests.append(endpoint+': old200 failure preserved as sample; new policy crosses200 without unrelated asset changes')
st,c,n,saves=scene(1000,LIMIT);n['balance_first_team'](st['teams']['0']);assert n['first_team_count'](st['teams']['0'])==1000
tests.append('1000 existing first-team cards keep their assignment; no automatic reserve migration')
st,c,n,saves=scene(201,LIMIT);c['ep']=0;before=copy.deepcopy(st)
assert not n['ep_transfer_purchase']('2','1','100','',b'{}')['result'] and st==before
tests.append('insufficient funds still rejects without mutation after capacity expansion')
predicates=[]
for filename in ('http_config.py','market_simulation.py','pack_cadence.py','pack_catalogue.py','product_packs.py','admin.py'):
    t=ast.parse((S/filename).read_text('utf-8-sig'))
    for x in ast.walk(t):
        if not isinstance(x,ast.Compare):continue
        expr=ast.unparse(x)
        if not any(v in expr for v in ('MAX_PLAYERS','FIRST_TEAM_MAX')):continue
        for count in (200,201,1000,10000):
            st,c,n,saves=scene(count,LIMIT);team=st['teams']['0'];h=types.SimpleNamespace(MAX_PLAYERS=LIMIT)
            context=dict(n,team=team,entry={'players':[{}]*3},e={'players':[{}]*3},h=h,hc=h,self=types.SimpleNamespace(h=h),t=team,st=st)
            allowed=eval(compile(ast.Expression(x),'capacity predicate','eval'),context)
            assert allowed==(isinstance(x.ops[0],(ast.Lt,ast.LtE))), (filename,expr,count,allowed)
        predicates.append(dict(file=filename,line=x.lineno,expression=expr))
assert len(predicates)==11,len(predicates)
tests.append(f'all {len(predicates)} exact capacity predicates in market purchase/cancel, packs, bag, first team and admin accept counts200/201/1000/10000')
encoded=json.dumps({'limits':{'players':LIMIT,'baseplayers':LIMIT,'firstTeam':LIMIT}},allow_nan=False)
assert json.loads(encoded)['limits']['players']==LIMIT and LIMIT==int(LIMIT)&0xffffffff
tests.append('finite JSON uint32-compatible capacity; no null, negative sentinel, Infinity or allocation by capacity')
result=dict(status='CAPACITY_BOUNDARY_REGRESSION_PASS',protocol_capacity=LIMIT,checks=tests,predicates=predicates,real_state_read=False,real_state_written=False,native_verified=False)
(O/'test-results.json').write_text(json.dumps(result,indent=2),'utf8');print(json.dumps(result,indent=2))
