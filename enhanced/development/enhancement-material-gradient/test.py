"""Check tier anchors, all stages, actual runtime preview/execute wrappers, and scope."""
from pathlib import Path
import ast, hashlib, importlib.util, json, math, sys, threading, types
sys.dont_write_bytecode = True
W = Path(__file__).resolve().parent
S = Path('D:/FO3ID/server')
def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
p = module(W/'enhancement_progression.py','gradient')
old = module(S/'enhancement_progression.py','baseline')
checks = []
for grade in range(1,21):
    factors = [p.material_factor(grade, m) for m in range(1,grade+1)]
    assert factors[-1] == 1
    assert all(a < b for a,b in zip(factors,factors[1:])), grade
    for m in range(1,21):
        assert old.material_factor(grade,m) <= p.material_factor(grade,m) <= 1
    for m in {1,(grade+2)//3,(2*grade+2)//3,grade}:
        assert abs(p.material_factor(grade,m)-old.material_factor(grade,m)) < 1e-12
checks.append('All grades 1..20: original integer tier-start anchors unchanged, no material nerfs, each material grade strictly better until equal-grade ceiling')
expected = {6:.21,7:7/30,8:77/300,9:.28}
for m,v in expected.items(): assert math.isclose(p.RATES[9]*p.material_factor(9,m),v,abs_tol=1e-12)
checks.append('Main +9 / materials +6,+7,+8,+9 = 21%,23.333333%,25.666667%,28%')
def dump_nodes(path):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text('utf8')).body if isinstance(n,ast.FunctionDef)}
before,after = dump_nodes(S/'enhancement_progression.py'),dump_nodes(W/'enhancement_progression.py')
assert set(before)==set(after)
assert all(before[n]==after[n] for n in before if n not in ('material_factor','install'))
# install itself changes only public probability metadata.
a=(W/'enhancement_progression.py').read_text('utf8')
a=a.replace("material_factors=dict(mode='linear_between_integer_tier_starts', lowest=.35, one_third=.50, two_thirds=.75, equal_or_higher=1., rounding='ceil each threshold; duplicate starts keep higher factor'),",'material_factors=dict(below_one_third=.35, below_two_thirds=.50, below_equal=.75, equal_or_higher=1.),')
assert next(ast.dump(n,include_attributes=False) for n in ast.parse(a).body if isinstance(n,ast.FunctionDef) and n.name=='install')==before['install']
checks.append('Execution, protection selection, failure, restore, fee, payment and quote wrappers remain AST-identical; only factor, version and factor metadata changed')
seen=[]
state={'teams':{'1':{'a':{'grade':9},'b':{'grade':6}}}}
def preview(a,b,points,item,event,query,body):
    seen.append(('preview',points,item))
    pa,pb=h.enhance_pair(state['teams']['1'],a,b)
    return h._json(dict(result=True,probability=round(h.enhance25_rate(pa,pb,points=='1',h.boost_stack(state,item),event)*100,3),needes=10))
def execute(*args):seen.append(('execute',args[2],args[3]));return preview(*args)
h=types.SimpleNamespace(MAX_GRADE=20,grade_of=lambda c:c['grade'],player_value_price=lambda *x:10000,
    ITEMS={i:(None,None,None,{'boost':b},'') for i,b in zip((1000052,1000053,1000054),(.15,.10,.05))},
    ENHANCE_EVENT={},STATE_LOCK=threading.RLock(),ep_enhance25_preview=preview,ep_enhance25=execute,
    ep_enhance25_restore=lambda q,b:('json',b'{}'),ROUTES=[],ENDPOINTS={},_state=lambda:state,
    _default_slot=lambda s:1,enhance_pair=lambda team,a,b:(team['a'],team['b']),
    boost_stack=lambda st,item:None if str(item)=='-1' else {'itemid':int(item)},
    _json=lambda d:('json',json.dumps(d).encode()),enhancement_settings_get=lambda:{'rates':{str(g):p.RATES[g]*100 for g in range(1,20)}})
p.install(h);p.install_runtime(h)
cases=0
for grade in range(1,20):
    for m in range(1,21):
        state['teams']['1'].update(a={'grade':grade},b={'grade':m})
        for point in ('0','1'):
            for item in ('-1','1000052','1000053','1000054'):
                q=json.loads(h.ep_enhance25_preview('a','b',point,item,'1001','',b'{}')[1])
                booster=0 if item=='-1' else h.ITEMS[int(item)][3]['boost']
                bonus=(.1 if point=='1' else 0)+booster
                expect=min(h.ENHANCE_RATE[grade],h.ENHANCE_RATE[grade]*p.material_factor(grade,m)*(1+bonus))
                assert abs(q['probability']-expect*100)<=.00050000001,(grade,m,point,item,q,expect)
                assert q['probability']<=round(h.ENHANCE_RATE[grade]*100,3)
                r=json.loads(h.ep_enhance25('a','b',point,item,'1001','',b'{}')[1])
                assert r['probability']==q['probability']
                if m>=grade:
                    assert seen[-2][1:]==('0','-1')
                    assert q['needes']==0
                cases+=1
    assert h.enhance25_rate({'grade':grade},{'grade':0},True,None,'1001')==1
checks.append('3040 actual runtime preview/execution wrapper combinations: all materials, points, boosters; matching displayed and executed chance; ceiling suppression and +0 behavior unchanged')
result=dict(status='PASS',matrix_cases=cases,checks=checks,tested_outputs=json.loads((W/'build.json').read_text())['outputs'],baseline=json.loads((W/'build.json').read_text())['baseline'],native_verified=False,formal_assets_written=False,
    host_sha256=hashlib.sha256((S/'http_config.py').read_bytes()).hexdigest(),hot_revision=json.loads((S/'hot_updates/active.json').read_text('utf-8-sig'))['revision'])
(W/'tests.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
