from pathlib import Path
import copy,json,math,sys,tempfile,threading,types
from unittest.mock import patch
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');sys.path[:0]=[str(P),str(S)]
from market_supply_settings import SupplySettings,DEFAULTS,validate
from market_simulation import Market
checks=[]
def check(ok,name):
 assert ok,name
 checks.append(name)
def reject(fn):
 try:fn()
 except (ValueError,OSError):return True
 return False
with tempfile.TemporaryDirectory(dir=P) as root:
 path=Path(root)/'settings.json';lock=threading.RLock();cfg=SupplySettings(path,lock)
 check(cfg.get()['active_revision']=='defaults' and cfg.error is None,'Missing file loads existing production defaults')
 for value in (-1,2,float('nan'),float('inf'),True):
  data=copy.deepcopy(DEFAULTS);data['regular_chances']['elite']['10']=value;check(reject(lambda:validate(data)),'Invalid probability rejected '+str(value))
 for key,value in [('regular_refresh_seconds',0),('background_seconds',False),('discovery_seconds',1),('regular_counts',{'1':1}),('rare_overrides',{'elite_21':{}})]:
  data=copy.deepcopy(DEFAULTS);data[key]=value;check(reject(lambda:validate(data)),'Invalid field rejected '+key)
 data=copy.deepcopy(DEFAULTS);data['extra']=1;check(reject(lambda:validate(data)),'Unknown keys rejected')
 data=copy.deepcopy(DEFAULTS);data['regular_refresh_seconds']=3600;data['regular_counts']['10']=7;data['regular_chances']['elite']['10']=1.;data['rare_overrides']={'elite_15':dict(period_seconds=3600,slots=2,chance=.75,quantity=3)}
 before=cfg.get()['revision'];result=cfg.set(dict(revision=before,settings=data));check(result['active_revision']==result['revision']!='defaults','Atomic online update reports actual active revision')
 check(reject(lambda:cfg.set(dict(revision=before,settings=DEFAULTS))),'Stale writer rejected without replacing newer configuration')
 restart=SupplySettings(path,lock);check(restart.data==data,'Settings survive process restart')
 oldraw=path.read_bytes();olddata=copy.deepcopy(cfg.data)
 with patch('market_supply_settings.os.replace',side_effect=OSError('fixture disk failure')):check(reject(lambda:cfg.set(dict(revision=cfg.get()['revision'],settings=DEFAULTS))),'Failed atomic write rejects update')
 check(path.read_bytes()==oldraw and cfg.data==olddata,'Write failure retains disk and active configuration')
 path.write_text('{broken','utf8');cfg.refresh();check(cfg.data==olddata and cfg.error is not None,'Invalid external file retains last good runtime configuration and reports error')
 cfg.set(dict(revision=cfg.get()['revision'],settings=data));check(cfg.error is None,'Admin CAS can repair invalid file')
 path.write_text(json.dumps(DEFAULTS),'utf8');cfg.refresh();check(cfg.data==DEFAULTS,'Valid external atomic configuration is picked up without reload')
 # Two admins racing on one revision: exactly one change wins.
 rev=cfg.get()['revision'];results=[]
 def save(n):
  d=copy.deepcopy(DEFAULTS);d['regular_counts']['1']=n
  try:cfg.set(dict(revision=rev,settings=d));results.append('saved')
  except ValueError:results.append('conflict')
 threads=[threading.Thread(target=save,args=(n,)) for n in (20,30)]
 for t in threads:t.start()
 for t in threads:t.join()
 check(sorted(results)==['conflict','saved'],'Concurrent admin updates have one CAS winner')
 cfg.set(dict(revision=cfg.get()['revision'],settings=DEFAULTS))
 m=Market.__new__(Market);m.h=types.SimpleNamespace(MAX_GRADE=20);m.supply_settings=cfg;m.quality=lambda s:'elite';m.quote=lambda *args:100;m.unit=lambda seed:.999;m._supply_plan=None
 state={'market_simulation':{'seed':'fixture','books':{},'rare_books':{},'supply_started_at':0}}
 original=m.book(state,93001075,100);signed=copy.deepcopy(original);original['rows'][0]['count']=0;sold=copy.deepcopy(original)
 cfg.set(dict(revision=cfg.get()['revision'],settings=data))
 check(m.book(state,93001075,200)==sold,'Config update cannot refill an active sold regular book')
 new=m.book(state,93001075,901);check(new['expires_at']==3600 and next(r['count'] for r in new['rows'] if r['grade']==10)==7,'New interval probability and quantity apply after signed expiry')
 check(all(r['grade']<=5 for r in m.book(state,84037576,901)['rows']),'Online settings cannot bypass IM +5 cap')
 check(m.book(state,93001075,50)==new,'Clock rollback cannot reopen expired or sold books')
 m.quality_pools=lambda:{'low':(1,),'mid':(),'high':(),'elite':(93001075,)}
 plan={r['key']:r for r in m.supply_plan()};rule=plan['elite_15'];check((rule['period'],rule['slots'],rule['chance'],rule['quantity'])==(3600,2,.75,3),'Rare plan updates from active configuration')
 cfg.set(dict(revision=cfg.get()['revision'],settings=DEFAULTS));rule2=next(r for r in m.supply_plan() if r['key']=='elite_15');check(rule2!=rule,'Rare plan cache invalidates on online change')
 cfg.set(dict(revision=cfg.get()['revision'],settings=data));m.unit=lambda seed:.01
 # New rare stock uses configured quantity and schedule, while rereads do not refill.
 m.supply_plan=lambda:[rule];m.quality_pools=lambda:{'elite':(93001075,)}
 stock=m.rare_stock(state,1);check(len(stock)==1 and stock[0]['count']==3,'Rare supply uses configured per-slot quantity')
 stock[0]['count']=0;check(m.rare_stock(state,2)==[],'Configured rare supply remains depleted after repeated reads')
 unchanged=copy.deepcopy(state);cfg.set(dict(revision=cfg.get()['revision'],settings=DEFAULTS));check(state==unchanged,'Admin setting changes never write or mutate player state')
(P/'test_settings.py.result.json').write_text(json.dumps(dict(status='PASS',checks=len(checks),details=checks,real_state_written=False),ensure_ascii=False,indent=2),'utf8');print('PASS',len(checks))
