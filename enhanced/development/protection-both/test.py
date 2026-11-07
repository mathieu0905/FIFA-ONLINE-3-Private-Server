"""Exercise the actual host routes against temporary assets and a temporary price DB."""
from pathlib import Path
import concurrent.futures,copy,hashlib,importlib.util,json,os,sqlite3,sys,tempfile,types
from fractions import Fraction
from urllib.parse import urlencode
from unittest.mock import patch
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent; S=Path('D:/FO3ID/server')
T=Path(tempfile.mkdtemp(prefix='fo3-capped-'))
source=S if '--installed' in sys.argv else R
sys.argv=['http_config.py']
os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi',FO3_ADMIN_PORT='0')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
protected={str(S/'gamedata'/n):sha(S/'gamedata'/n) for n in ('state.json','shop.json')}
(T/'state.json').write_bytes((S/'gamedata/state.json').read_bytes())
(T/'rates.json').write_bytes(((source if (source/'gamedata/enhancement_rates.json').exists() else S)/'gamedata/enhancement_rates.json').read_bytes())
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
for name in ('enhancement_progression','enhancement_settings','enhancement_protection40','npc_exchange'):
    text=((source if (source/(name+'.py')).exists() else S)/(name+'.py')).read_text('utf8')
    if name=='enhancement_settings':text=text.replace("Path(hc.HERE) / 'gamedata' / 'enhancement_rates.json'",repr(str(T/'rates.json'))).replace('path = '+repr(str(T/'rates.json')),'path = Path('+repr(str(T/'rates.json'))+')')
    mod=types.ModuleType(name);mod.__file__=str((source if (source/(name+'.py')).exists() else S)/(name+'.py'));sys.modules[name]=mod;exec(compile(text,mod.__file__,'exec'),mod.__dict__)
source_text=(S/'http_config.py').read_text('utf8')
source_text=source_text.replace('STATE = os.path.join(HERE, "gamedata", "state.json")', 'STATE = '+repr(str(T/'state.json'))+'\nMARKET_PRICE_DB_PATH = '+repr(str(T/'prices.sqlite')))
h=types.ModuleType('http_config');h.__file__=str(S/'http_config.py');sys.modules['http_config']=h
exec(compile(source_text,h.__file__,'exec'),h.__dict__)
p=sys.modules['enhancement_progression']; protection=sys.modules['enhancement_protection40']
checks=[];matrix=0
rates=[90,85,75,65,55,45,38,32,28,25,20,15,12,10,8,6,5,4,3]
for grade in range(1,20):
    for material in range(1,21):
        a,b=dict(grade=grade),dict(grade=material)
        ceiling=rates[grade-1]/100
        mf=1 if material>=grade else .75 if 3*material>=2*grade else .5 if 3*material>=grade else .35
        for point in (False,True):
            for itemid in (None,1000052,1000053,1000054):
                item=None if itemid is None else {'itemid':itemid}
                extra=(.1 if point else 0)+(h.ITEMS[itemid][3]['boost'] if itemid else 0)
                actual=h.enhance25_rate(a,b,point,item,'1001')
                assert abs(actual-min(ceiling,ceiling*mf*(1+extra)))<1e-12
                assert 0<actual<=ceiling<1
                if material>=grade:assert actual==ceiling
                matrix+=1
    assert h.enhance25_rate(dict(grade=grade),dict(grade=0),True,None,'1001')==1
assert abs(h.enhance25_rate(dict(grade=9),dict(grade=6),True,{'itemid':1000052},'1001')-.2625)<1e-12
assert h.ENHANCE_EVENT['active'] is False and h.EVENT_BOOST==0
checks.append('3040 combinations: all stages/materials/points/items capped, exact equal-material rates, former +9/+6 full-stack=26.25%, event has no effect; +0 does not upgrade')

for base in (1,100,10000,1000000,10**9,10**13):
    prices,strategies=p.expected_curve(base,tuple(h.ENHANCE_RATE))
    assert prices[1]==base and all(a<=b<=p.MAX_DISPLAY_PRICE for a,b in zip(prices,prices[1:]))
    for grade in range(1,20):
        candidates=[]
        for m in range(1,grade+1):
            chance=Fraction(str(h.ENHANCE_RATE[grade]))*Fraction(str(p.material_factor(grade,m)))
            for use_protection in (False,True):
                floor=grade if use_protection else p.failure_grade(grade)
                fee=(2*prices[grade]+4)//5 if use_protection else max(1000,(2*prices[grade]+99)//100)
                # Independent form of geometric retries: successes plus failed-attempt rebuilds.
                attempts=1/chance
                candidate=prices[grade]+(prices[m] if use_protection else attempts*prices[m])+attempts*fee+(attempts-1)*(prices[grade]-prices[floor])
                candidates.append((candidate,m,use_protection))
        best=min(candidates)[0]
        assert prices[grade+1]==min(p.MAX_DISPLAY_PRICE,-(-best.numerator//best.denominator))
    assert prices[2]>=min(p.MAX_DISPLAY_PRICE,2*base)
prices,_=p.expected_curve(1000000,tuple(h.ENHANCE_RATE))
assert prices[2]==2133334 and prices[3]>3*1000000
sample=93192181
base=h.market_engine.exchange.price_store.current(sample)
for grade in range(1,21):assert h.player_value_price(sample,grade)==h.enhancement_expected_value(base,grade)
checks.append('Expected-cost Bellman recurrence checked across cheap/normal/expensive cards, material costs, normal fee floor, 40% protection, failed rebuilds, safe floors, rounding/display limit, persistent live +1 base; original card_price anchor untouched')

baseline=copy.deepcopy(h._state());slot=h._default_slot(baseline)
def fresh(grade=9,material=9):
    st=copy.deepcopy(baseline);st.pop('enhance_restore',None)
    coach=h.my_coach(st);coach['ep']=10**18;coach['es']=1000000
    coach['items']=[i for i in coach.get('items',[]) if i['itemid']!=1000052]+[dict(_id='temp-only-gold',itemid=1000052,remains=5)]
    team=st['teams'][str(slot)]
    a=h.add_player(team,sample,grade);b=h.add_player(team,sample,material)
    a['levelinfo']={'level':12,'exp':43};a['locked']=b['locked']=False
    h._save(st)
    return h.iid(a),h.iid(b)
def call(uri):
    path,_,q=uri.partition('?')
    with h.STATE_LOCK:return json.loads((h.ENDPOINTS.get(path) or h.route(path))(q,b'{}')[1])
def card(st,ident):return next(x for x in st['teams'][str(slot)]['players'] if h.iid(x)==ident)
def uri(a,b,preview=False,point=1,item=-1):return f'/player/{a}/enhance2.5/{b}/'+('preview/' if preview else '')+f'{point}/{item}/1001'
for success in (True,False):
    a,b=fresh();before=h._state();raw=Path(h.STATE).read_bytes()
    out=call(uri(a,b,True,item=1000052));assert out['result'] and out['probability']==28 and out['needes']==0
    assert Path(h.STATE).read_bytes()==raw
    with patch.object(h.random,'random',return_value=0 if success else .999999):out=call(uri(a,b,item=1000052))
    after=h._state();assert out['result'] and out['success']==success
    assert card(after,a)['grade']==(10 if success else 8)
    assert card(after,a)['levelinfo']==card(before,a)['levelinfo']
    assert h.my_coach(after)['items']==h.my_coach(before)['items']
    assert h.my_coach(after)['es']==h.my_coach(before)['es']+(0 if success else h.enhance_es(card(before,a)))
    assert h.my_coach(after)['ep']==h.my_coach(before)['ep']-h.enhance_cost(card(before,a))
    raw=Path(h.STATE).read_bytes();assert not call(uri(a,b,item=1000052))['result'] and Path(h.STATE).read_bytes()==raw
checks.append('Actual normal routes: equal material final cap, preview read-only, no point/item consumed at cap, fee charged once, success/failure grades and XP correct, replay rejected')
for grade,material in ((6,2),(9,6),(12,8),(19,13),(9,9)):
    for success in (True,False):
        a,b=fresh(grade,material);before=h._state()
        q=call(uri(a,b,True,item=protection.ITEM))
        assert q['result'] and 'token' in q['protection'],q
        assert q['enhancepay']==protection.fee(h.player_value_price(sample,grade))
        assert q['needes']==(0 if material>=grade else h.enhance_es(card(before,a)))
        token=urlencode(dict(protection_ack=protection.VERSION,protection_token=q['protection']['token']))
        with patch.object(h.random,'random',return_value=0 if success else .999999):out=call(uri(a,b,item=protection.ITEM)+'?'+token)
        after=h._state();assert out['result'] and out['success']==success
        assert card(after,a)['grade']==grade+success and card(after,a)['levelinfo']==card(before,a)['levelinfo']
        assert any(h.iid(x)==b for x in after['teams'][str(slot)]['players']) == (not success)
        if not success:assert after['teams']==before['teams']
        assert h.my_coach(after)['ep']==h.my_coach(before)['ep']-q['enhancepay']
        spent=0 if material>=grade else h.enhance_es(card(before,a))
        assert h.my_coach(after)['es']==h.my_coach(before)['es']-spent+(0 if success else h.enhance_es(card(before,a)))
        assert 'enhance_restore' not in after
        raw=Path(h.STATE).read_bytes();assert not call(uri(a,b,item=protection.ITEM)+'?'+token)['result'] and Path(h.STATE).read_bytes()==raw
checks.append('Actual protected routes low/high/equal materials: exact 40% new value, no additional fee, failed grade/XP kept, material once, ES normalized, replay no second charge')
if 'independent_checkbox=True' in (source/'enhancement_protection40.py').read_text('utf8'):
    for material in (8,9):
        for success in (True,False):
            a,b=fresh(9,material);before=h._state()
            q=call(uri(a,b,True,item=1000052)+'?protection=1')
            assert q['result'] and 'token' in q['protection']
            assert q['probability']==(26.25 if material==8 else 28)
            assert q['needes']==(100 if material==8 else 0)
            token=urlencode(dict(protection=1,protection_ack=protection.VERSION,protection_token=q['protection']['token']))
            with patch.object(h.random,'random',return_value=0 if success else .999999):out=call(uri(a,b,item=1000052)+'?'+token)
            after=h._state();assert out['result'] and out['success']==success and card(after,a)['grade']==9+success
            assert h.my_coach(after)['items'][-1]['remains']==(4 if material==8 else 5)
            assert h.my_coach(after)['ep']==h.my_coach(before)['ep']-q['enhancepay']
            assert h.my_coach(after)['es']==h.my_coach(before)['es']-(100 if material==8 else 0)+(0 if success else 100)
    rules=call('/info/enhancement/protection/rules');assert rules['independent_checkbox'] and not rules['boost_item_exclusive']
    assert all(str(row['itemid'])!=str(protection.ITEM) for row in h.coach_items(h._state(),slot))
    checks.append('Latest independent protection checkbox preserved: gold+ES+protection success/failure at 26.25%, equal-grade 28% skips useless gold/ES, no fake protection inventory row')
a,b=fresh(9,6);q=call(uri(a,b,True,item=1000052));assert q['probability']==26.25
before=h._state()
with patch.object(h.random,'random',return_value=0):out=call(uri(a,b,item=1000052))
assert out['result'] and h.my_coach(h._state())['items'][-1]['remains']==4
assert h.my_coach(h._state())['es']==h.my_coach(before)['es']-100
checks.append('Beneficial ES and gold item actually consumed, 26.25% preview equals execution probability')
a,b=fresh(9,6);q=call(uri(a,b,True,item=protection.ITEM));token=urlencode(dict(protection_ack=protection.VERSION,protection_token=q['protection']['token']))
raw=Path(h.STATE).read_bytes()
with patch.object(h,'_save',side_effect=OSError('injected')):
    try:call(uri(a,b,item=protection.ITEM)+'?'+token)
    except OSError:pass
    else:raise AssertionError('Expected save failure')
assert Path(h.STATE).read_bytes()==raw
with patch.object(h.random,'random',return_value=.999999),concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    out=list(pool.map(lambda _:call(uri(a,b,item=protection.ITEM)+'?'+token),range(2)))
assert sum(x['result'] for x in out)==1
checks.append('Save failure atomic; concurrent repeated protection token succeeds once')
for grade in (5,10):
    a,b=fresh(grade,1);q=call(uri(a,b,True,item=protection.ITEM));assert q['result'] and 'token' in q['protection']
for grade in (1,5,10):
    a,b=fresh(grade,grade);before=h._state();total=0
    for attempt in range(3):
        q=call(uri(a,b,True,item=-1)+'?protection=1')
        assert q['result'] and 'token' in q['protection']
        token=urlencode(dict(protection=1,protection_ack=protection.VERSION,protection_token=q['protection']['token']))
        with patch.object(h.random,'random',return_value=.999999):out=call(uri(a,b,item=-1)+'?'+token)
        assert out['result'] and not out['success'] and out['protection']['material_kept']
        total+=q['enhancepay'];after=h._state()
        assert after['teams']==before['teams']
        assert h.my_coach(after)['ep']==h.my_coach(before)['ep']-total
        assert len(h.my_coach(after)['protection_attempt_receipts'])==attempt+1
        raw=Path(h.STATE).read_bytes()
        assert call(uri(a,b,item=-1)+'?'+token)['reason']=='PROTECTION_ALREADY_USED'
        assert Path(h.STATE).read_bytes()==raw
checks.append('Natural floors +1/+5/+10: three distinct paid failures keep both exact cards/squads; each fee once; same-token replay rejected by persisted receipt despite unchanged cards')
settings=h.enhancement_settings_get();assert settings['semantics']=='equal_material_ceiling'
bad=dict(settings['rates']);bad['1']=100
try:h.enhancement_settings_set(dict(rates=bad,revision=settings['revision']))
except ValueError:pass
else:raise AssertionError('100% ceiling must be rejected')
assert h.enhancement_settings_get()==settings
new=dict(settings['rates']);new['9']=27
h.enhancement_settings_set(dict(rates=new,revision=settings['revision']))
assert h.enhance25_rate(dict(grade=9),dict(grade=9),True,None,'1001')==.27
assert h.enhancement_expected_value(base,10)!=p.expected_curve(base,tuple(p.RATES))[0][10]
checks.append('Natural floors can protect the material even when the main is already safe; admin ceilings reject 100%, CAS still enforced, online probability edits update value model cache')
# State is live and may advance independently; this test never writes formal paths.
build=json.loads((R/'build.json').read_text('utf8'))
result=dict(status='PASS',matrix_cases=matrix,checks=checks,temporary_state=str(T/'state.json'),formal_asset_writes=False,protected_failure_keeps_both=True,
            tested_outputs={rel:sha(source/rel) for rel in build['outputs']},host_sha256=sha(S/'http_config.py'),hot_revision=json.loads((S/'hot_updates/active.json').read_text('utf8'))['revision'],
            source='installed' if source==S else 'development',sample_base=1000000,sample_value_curve={str(g):v for g,v in enumerate(prices) if g},
            native_verified=False,match_verified=False)
(R/('installed-tests.json' if source==S else 'tests.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=True))
