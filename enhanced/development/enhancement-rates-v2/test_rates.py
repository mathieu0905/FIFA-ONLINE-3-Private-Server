from pathlib import Path
import ast,types,sys,importlib.util,json,threading
W=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');sys.dont_write_bytecode=True
old=ast.parse((S/'enhancement_progression.py').read_text(encoding='utf-8-sig'));new=ast.parse((W/'enhancement_progression.py').read_text(encoding='utf-8-sig'))
def funcs(t):return {n.name:n for n in ast.walk(t) if isinstance(n,ast.FunctionDef)}
a,b=funcs(old),funcs(new)
for name in ('failure_grade','player_value_price','restore'):assert ast.dump(a[name])==ast.dump(b[name]),name
# Only RATES, version/description and one ES boundary change; price factors stay exact.
for key in ('PRICE_STEPS','MAX_DISPLAY_PRICE'):
 value=lambda t:ast.dump(next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id==key for x in n.targets)))
 assert value(old)==value(new)
spec=importlib.util.spec_from_file_location('new_progression',W/'enhancement_progression.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
h=types.ModuleType('h');h.MAX_GRADE=20;h.STATE_LOCK=threading.RLock();h.player_value_price=lambda s,g=1:g*1000;h.grade_of=lambda p:p['grade'];h.ES_BOOST=.1;h.EVENT_BOOST=.1;h.ENHANCE_EVENT={'eventid':1001};h.ITEMS={1000052:('gold',0,'ENHANCEMENT_BOOST',{'boost':.15})};h.ENDPOINTS={};h.ep_enhance25_restore=lambda *a:None;h.enhancement_settings_get=lambda:{'rates':{str(g):m.RATES[g]*100 for g in range(1,20)}}
source=ast.parse((S/'http_config.py').read_text(encoding='utf-8-sig'));exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ('enhance_rate','enhance25_rate')],type_ignores=[]),'<actual core rates>','exec'),h.__dict__)
m.install(h);m.install_runtime(h)
expected={str(g):v for g,v in zip(range(11,20),(20,15,12,10,8,6,5,4,3))}
assert {g:round(h.ENHANCE_RATE[int(g)]*100,8) for g in expected}==expected
count=0
for g in range(1,20):
 for material in (0,1,g):
  for points in (False,True):
   for item in (None,{'itemid':1000052}):
    pa,pb={'grade':g},{'grade':material};base=h.enhance_rate(pa,pb)
    if material==0:want=1
    else:
     bonus=(base*.1 if g>=12 else .1)*points+(.15 if item else 0)+(.1 if g<=9 else 0)
     want=min(1,base+bonus)
    assert abs(h.enhance25_rate(pa,pb,points,item,'1001')-want)<1e-12,(g,material,points,item)
    count+=1
assert abs(h.enhance25_rate({'grade':12},{'grade':1},True,None,'-1')-.165)<1e-12
assert abs(h.enhance25_rate({'grade':19},{'grade':1},True,None,'-1')-.033)<1e-12
r=dict(status='PASS',exact_user_rates=expected,rate_point_material_item_event_combinations=count,plus12_point_rate=16.5,plus19_point_rate=3.3,price_and_floor_and_restore_code_unchanged=True,native_pass=False)
(W/'tests.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2))
