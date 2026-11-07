import copy,json,sys,tempfile,threading,types
from pathlib import Path
from unittest.mock import patch
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');sys.path[:0]=[str(S),str(P)]
from market_supply_settings import SupplySettings,DEFAULTS
from market_simulation import Market
from activation import market_supply_activate
checks=[]
def check(ok,name):
 assert ok,name
 checks.append(name)
def rejected(fn):
 try:fn()
 except (ValueError,OSError):return True
 return False
with tempfile.TemporaryDirectory(dir=P) as root:
 lock=threading.RLock();control=SupplySettings(Path(root)/'config.json',lock);engine=Market.__new__(Market);engine.supply_settings=control;engine.h=types.SimpleNamespace(MAX_GRADE=20);engine._supply_plan=None;engine.quality_pools=lambda:dict(low=(1000001,),mid=(),high=(),elite=(93001075,));engine.quote=lambda *a:1234;engine.unit=lambda seed:.01;engine.has_active=lambda st:True
 visible=dict(spid=93001075,grade=15,price=222,count=2,_market_release=10,_market_expires=9999,_market_supply_key='elite_15')
 sold=dict(visible,grade=16,count=0,price=555)
 future=dict(visible,grade=20,count=1,price=None,_market_release=10000,_market_expires=11000)
 original=dict(coaches=[dict(name='protected',money=123456)],teams={'0':{'players':[dict(id='real',grade=16,spid=93001075)]}},offers=[dict(player='human',count=1)],market_simulation=dict(seed='fixture',supply_started_at=0,books={},legacy_supply=[],rare_books={'elite_15':dict(epoch=0,start=0,period=604800,slots=1,chance=1,pool_size=1,rows=[visible,sold,future])}))
 store=[copy.deepcopy(original)];saves=[]
 def save(st):store[0]=copy.deepcopy(st);saves.append(1)
 host=types.SimpleNamespace(STATE_LOCK=lock,market_engine=engine,_state=lambda:copy.deepcopy(store[0]),_save=save,_json=lambda r:r)
 settings=copy.deepcopy(DEFAULTS);settings['rare_overrides']={b+'_'+str(g):dict(period_seconds=300,slots=5,chance=1.,quantity=1) for b in ('low','mid','high','elite') for g in range(11,21)}
 params=dict(revision=control.get()['revision'],settings=settings)
 with patch('time.time',return_value=1000):result=market_supply_activate(host,{},json.dumps(params).encode())
 check(result['result'] and len(saves)==1,'Online minute transition commits once')
 check({k:v for k,v in store[0].items() if k!='market_simulation'}=={k:v for k,v in original.items() if k!='market_simulation'},'Player cards balances managers and human offers preserved')
 legacy=store[0]['market_simulation']['legacy_supply'];check(visible in legacy and sold in legacy,'Visible quote and consumed history preserved exactly')
 check(next(r for r in legacy if r['price'] is None)['count']==0,'Unquoted weekly future slots cancelled without creating extra cards')
 batches=store[0]['market_simulation']['rare_books'];check(all(b['period']==300 and b['slots']==5 for b in batches.values()),'Old multiweek batches become five-minute blocks immediately')
 rows=batches['elite_15']['rows'];check([r['_market_release'] for r in rows]==[900,960,1020,1080,1140],'Independent opportunities are exactly one minute apart')
 check(all(r['count']==1 for r in rows),'Successful minute roll lists one unit')
 once=copy.deepcopy(store[0])
 with patch('time.time',return_value=1010):again=market_supply_activate(host,{},json.dumps(params).encode())
 check(again['replayed'] and len(saves)==1 and store[0]==once,'Replay is idempotent even with original old CAS revision')
 other=copy.deepcopy(params);other['settings']['rare_overrides']['elite_20']['chance']=.1
 check(rejected(lambda:market_supply_activate(host,{},json.dumps(other).encode())),'Stale different settings rejected')
 bad=copy.deepcopy(other);bad['revision']=control.get()['revision'];bad['settings']['rare_overrides']['elite_20']['slots']=1
 check(rejected(lambda:market_supply_activate(host,{},json.dumps(bad).encode())),'Non-minute configuration cannot use minute transition')
 current=copy.deepcopy(store[0]);active=engine.rare_stock(current,1000);new=[r for r in active if r.get('_market_release')==960];check(len(new)==20,'Each nonempty quality and grade has a current minute slot')
 for r in new:r['count']=0
 check(not any(r.get('_market_release')==960 for r in engine.rare_stock(current,1010)),'Repeated minute reads cannot refill a consumed slot')
 check(any(r.get('_market_release')==1020 for r in engine.rare_stock(current,1021)),'Next minute exposes a genuinely new slot')
 # Failure before save rolls configuration back; an error after commit preserves its receipt.
 for committed in (False,True):
  before=copy.deepcopy(store[0]);oldsettings=copy.deepcopy(control.data);change=copy.deepcopy(settings);change['rare_overrides']['elite_20']['chance']=.3 if committed else .2
  request=dict(revision=control.get()['revision'],settings=change)
  def fail(st):
   if committed:store[0]=copy.deepcopy(st)
   raise OSError('fixture write error')
  host._save=fail
  with patch('time.time',return_value=1100):
   if committed:
    out=market_supply_activate(host,{},json.dumps(request).encode());check(out['committed'] and control.data==change,'Post-commit exception preserves committed state and config without replay')
   else:
    check(rejected(lambda:market_supply_activate(host,{},json.dumps(request).encode())),'Pre-commit failure surfaced')
    check(store[0]==before and control.data==oldsettings,'Pre-commit failure retains state and restores previous config')
 # Probability is independently keyed per slot, with no timing-based reroll.
 for chance in (.35,.25,.15,.08,.04,.02):
  n=20000;hits=sum(Market.unit('fixture:rare:elite:0:'+str(i)+':exists')<chance for i in range(n));check(abs(hits/n-chance)<.012,'Minute chance sampling matches '+str(chance))
(P/'regression.json').write_text(json.dumps(dict(status='PASS',checks=len(checks),details=checks,real_state_written=False),indent=2),'utf8');print('PASS',len(checks))
