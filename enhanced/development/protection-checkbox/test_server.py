from pathlib import Path
import sys,json,copy,os,tempfile,importlib.util,concurrent.futures,hashlib
from urllib.parse import urlencode
from unittest.mock import patch
sys.dont_write_bytecode=True
W=Path(r'D:\fifaol3\protection-checkbox');S=Path(r'D:\FO3ID\server')
work=Path(tempfile.mkdtemp(prefix='protection40-'))
def audit(event,args):
 if event=='open':
  p,m,f=args
  if isinstance(p,(str,bytes,os.PathLike)) and ((isinstance(m,str) and any(c in m for c in 'wax+')) or (isinstance(f,int) and f&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))):
   target=Path(os.fsdecode(p)).resolve()
   if not target.is_relative_to(work) and not target.is_relative_to(W):raise PermissionError('Test refuses external write: '+str(target))
sys.addaudithook(audit)
os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi',FO3_ADMIN_PORT='0')
sys.path.insert(0,str(S));sys.argv=['http_config.py']
spec=importlib.util.spec_from_file_location('enhancement_protection40',W/'enhancement_protection40.py');p=importlib.util.module_from_spec(spec);sys.modules['enhancement_protection40']=p;spec.loader.exec_module(p)
import http_config as h
baseline=copy.deepcopy(h._state());h.STATE=str(work/'state.json')
assert h._protection40_installed
checks=[];saved=h._save;commits=[]
def save(st):commits.append(1);return saved(st)
h._save=save
slot=h._default_slot(baseline)
def fresh(grade=7,mat=1):
 st=copy.deepcopy(baseline);st.pop('enhance_restore',None)
 c=h.my_coach(st);c['ep']=10**18;c['es']=1000000;c['items']=[row for row in c.get('items',[]) if row.get('itemid') not in (1000052,1000053,1000054)]
 t=st['teams'][str(slot)]
 a=h.add_player(t,93192181,grade);b=h.add_player(t,93192181,mat)
 a['levelinfo']={'level':12,'exp':43};a['jerseyname']='TEST_ONLY_TEMPORARY';a['locked']=b['locked']=False
 h._save(st);return h.iid(a),h.iid(b)
def call(uri):
 path,_,q=uri.partition('?')
 with h.STATE_LOCK:return json.loads((h.ENDPOINTS.get(path) or h.route(path))(q,b'{}')[1])
def preview(a,b,point=0):return call(f'/player/{a}/enhance2.5/{b}/preview/{point}/1000090/-1')
def execute(a,b,q,point=0):
 return call(f'/player/{a}/enhance2.5/{b}/{point}/1000090/-1?'+urlencode({'protection_ack':q['protection']['version'],'protection_token':q['protection']['token']}))
def getcard(st,ident):return next(x for x in st['teams'][str(slot)]['players'] if h.iid(x)==ident)
for success in (True,False):
 for point in (0,1):
  a,b=fresh();before=h._state();pa=copy.deepcopy(getcard(before,a));raw=Path(h.STATE).read_bytes();q=preview(a,b,point)
  assert Path(h.STATE).read_bytes()==raw
  assert q['result'],q
  expected=(h.player_value_price(pa['spid'],7)*2+4)//5
  assert q['enhancepay']==q['protection']['fee']==q['protection']['total_ep']==expected
  assert '40%' in q['protection']['label'] and '替代原强化手续费' in q['protection']['label']
  n=len(commits)
  with patch.object(h.random,'random',return_value=0 if success else .999999):r=execute(a,b,q,point)
  after=h._state();card=getcard(after,a);need=h.enhance_es(pa)
  assert r['result'] and r['success']==success and len(commits)==n+1
  assert card['grade']==7+success and card['levelinfo']==pa['levelinfo'] and card['jerseyname']==pa['jerseyname']
  assert all(h.iid(x)!=b for x in after['teams'][str(slot)]['players'])
  assert h.my_coach(after)['ep']==h.my_coach(before)['ep']-expected
  assert h.my_coach(after)['es']==h.my_coach(before)['es']-need*point+(0 if success else need)
  assert 'enhance_restore' not in after
  raw=Path(h.STATE).read_bytes();assert not execute(a,b,q,point)['result'] and Path(h.STATE).read_bytes()==raw
checks.append('Actual production routes: success/failure and points off/on charge exactly ceil(pre-attempt displayed value*40%), never old fee; grade/XP preserved; material once; original ES math; replay refused')
a,b=fresh();q=preview(a,b);st=h._state();h.my_coach(st)['ep']=q['enhancepay']-1;h._save(st);raw=Path(h.STATE).read_bytes();assert not execute(a,b,q)['result'] and Path(h.STATE).read_bytes()==raw
checks.append('Insufficient EP rejects with no card/currency write')
a,b=fresh();q=preview(a,b);raw=Path(h.STATE).read_bytes()
with patch.object(h,'_save',side_effect=OSError('Injected atomic-save failure')):
 try:execute(a,b,q)
 except OSError:pass
 else:raise AssertionError('save failure expected')
assert Path(h.STATE).read_bytes()==raw
with patch.object(h.random,'random',return_value=.999999):assert execute(a,b,q)['result']
checks.append('Atomic-save failure leaves cards/fee untouched; same quote retry works')
a,b=fresh();q=preview(a,b);n=len(commits)
with patch.object(h.random,'random',return_value=.999999),concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:r=list(pool.map(lambda _:execute(a,b,q),range(2)))
assert sum(x['result'] for x in r)==1 and len(commits)==n+1
checks.append('Concurrent identical quote commits one charge and one material')
a,b=fresh();q=preview(a,b);rates=h.ENHANCE_RATE;h.ENHANCE_RATE=rates[:7]+(.01,)+rates[8:];raw=Path(h.STATE).read_bytes();assert not execute(a,b,q)['result'] and Path(h.STATE).read_bytes()==raw;h.ENHANCE_RATE=rates
q=preview(a,b)
with patch.object(p.time,'time',return_value=p.time.time()+181):assert not execute(a,b,q)['result']
q=preview(a,b);q['protection']['token']+='x';assert not execute(a,b,q)['result']
checks.append('Probability changes, expired or altered confirmation reject without writes')
for g,m in ((4,1),(7,0),(20,1)):
 a,b=fresh(g,m);raw=Path(h.STATE).read_bytes();q=preview(a,b);assert q['result'] and q['protection']['blocked'] and 'token' not in q['protection'] and q['enhancepay']==0 and Path(h.STATE).read_bytes()==raw
checks.append('Already-safe low grades, zero materials and max-grade combinations cannot be charged')
a,b=fresh();st=h._state();st['enhance_restore']={'id':a,'grade':8,'price':240};h._save(st);raw=Path(h.STATE).read_bytes();q=preview(a,b);assert q['result'] and q['protection']['blocked'] and Path(h.STATE).read_bytes()==raw
checks.append('Pending restore rights block new protection without silently deleting old rights')
a,b=fresh();st=h._state();before=h.my_coach(st)['ep'];pa=copy.deepcopy(getcard(st,a))
with patch.object(h.random,'random',return_value=.999999):r=call(f'/player/{a}/enhance2.5/{b}/0/-1/-1')
assert r['result'] and not r['success'] and r['grade']==h.enhancement_failure_grade(pa) and h.my_coach(h._state())['ep']==before-h.enhance_cost(pa)
checks.append('Protection unselected: original charge/drop/restore behavior unchanged')
st=h._state();raw=Path(h.STATE).read_bytes();items=h.coach_items(st,slot);assert sum(i['itemid']==p.ITEM for i in items)==0 and Path(h.STATE).read_bytes()==raw
try:h.inventory_add(h.my_coach(st),p.ITEM,1)
except ValueError:pass
else:raise AssertionError('service must not be granted')
assert p.fee(1)==1 and p.fee(101)==41 and p.fee(1000000)==400000
checks.append('Service appears as optional client selection without stored inventory; cannot gift it; integer fee rounds up exactly')

for g,m in ((8,6),(5,1),(10,1),(20,1)):
 a,b=fresh(g,m);raw=Path(h.STATE).read_bytes();q=call(f'/player/{a}/enhance2.5/{b}/preview/0/1000090/1001')
 assert q['result'] and q['protection']['blocked'] and not q['protection']['available'] and 'token' not in q['protection']
 assert q['enhancepay']==0 and q['protection']['fee']==0
 assert not call(f'/player/{a}/enhance2.5/{b}/0/1000090/1001')['result']
 assert Path(h.STATE).read_bytes()==raw
checks.append('Exact failing +8/+6 100% case and safe floors: successful nonpayable preview, no payment token, execution rejects, zero writes')
a,b=fresh();raw=Path(h.STATE).read_bytes();q=preview('000000000000000000000000',b)
assert q['result'] and q['protection']['blocked'] and Path(h.STATE).read_bytes()==raw
a,b=fresh();st=h._state();st['enhance_restore']={'id':a,'grade':8,'price':240};h._save(st);raw=Path(h.STATE).read_bytes();q=preview(a,b)
assert q['result'] and q['reason']=='RESTORE_PENDING' and q['protection']['can_restore'] and q['protection']['restore']['price']==240
assert q['protection']['discard_token'] and 'token' not in q['protection'] and Path(h.STATE).read_bytes()==raw
st=h._state();st['enhance_restore']['id']='another-manager-card';h._save(st);raw=Path(h.STATE).read_bytes();q=preview(a,b)
assert q['result'] and q['reason']=='RESTORE_OTHER_MANAGER' and 'discard_token' not in q['protection'] and Path(h.STATE).read_bytes()==raw
checks.append('Invalid selection and pending/other-manager restore are nonfatal blocked reads; signed explicit discard and original restore quote preserved')

def boosted_fresh(grade=12,mat=1,count=2):
 a,b=fresh(grade,mat);st=h._state();h.inventory_add(h.my_coach(st),1000052,count);h._save(st);return a,b
def stacked_preview(a,b,point=0,item=1000052,event=-1):
 return call(f'/player/{a}/enhance2.5/{b}/preview/{point}/{item}/{event}?protection=1')
def stacked_execute(a,b,q,point=0,item=1000052,event=-1):
 return call(f'/player/{a}/enhance2.5/{b}/{point}/{item}/{event}?'+urlencode({'protection_ack':q['protection']['version'],'protection_token':q['protection']['token']}))
for success in (True,False):
 for point in (0,1):
  a,b=boosted_fresh();before=h._state();pa=copy.deepcopy(getcard(before,a));booster=h.boost_stack(before,'1000052');before_count=booster['remains'];q=stacked_preview(a,b,point)
  raw=Path(h.STATE).read_bytes();normal=call(f'/player/{a}/enhance2.5/{b}/preview/{point}/1000052/-1');plain=call(f'/player/{a}/enhance2.5/{b}/preview/{point}/-1/-1')
  assert Path(h.STATE).read_bytes()==raw and q['result'] and q['probability']==normal['probability']>plain['probability']
  assert '黄金强化加成' in q['protection']['label'] and '均消耗1个' in q['protection']['label']
  cost=(h.player_value_price(pa['spid'],12)*2+4)//5;n=len(commits)
  with patch.object(h.random,'random',return_value=0 if success else .999999):r=stacked_execute(a,b,q,point)
  after=h._state();assert r['result'] and r['success']==success and len(commits)==n+1
  assert h.my_coach(after)['ep']==h.my_coach(before)['ep']-cost and h.boost_stack(after,'1000052')['remains']==before_count-1
  assert getcard(after,a)['grade']==12+success and getcard(after,a)['levelinfo']==pa['levelinfo']
  assert all(h.iid(card)!=b for card in after['teams'][str(slot)]['players']) and 'enhance_restore' not in after
  raw=Path(h.STATE).read_bytes();assert not stacked_execute(a,b,q,point)['result'] and Path(h.STATE).read_bytes()==raw
checks.append('Gold + independent protection: real routed chance equals native gold preview, above no-gold; point off/on, success/failure one booster/material/40%-fee/atomic save; replay zero charge')
a,b=boosted_fresh(count=1);q=stacked_preview(a,b)
with patch.object(h.random,'random',return_value=.999999):assert stacked_execute(a,b,q)['result']
assert h.boost_stack(h._state(),'1000052') is None
a,b=boosted_fresh();q=stacked_preview(a,b);st=h._state();h.boost_stack(st,'1000052')['remains']+=1;h._save(st);raw=Path(h.STATE).read_bytes()
assert not stacked_execute(a,b,q)['result'] and Path(h.STATE).read_bytes()==raw
a,b=boosted_fresh();st=h._state();h.inventory_add(h.my_coach(st),1000053,1);h._save(st);q=stacked_preview(a,b);raw=Path(h.STATE).read_bytes()
assert not stacked_execute(a,b,q,item=1000053)['result'] and Path(h.STATE).read_bytes()==raw
a,b=fresh(12,1);raw=Path(h.STATE).read_bytes();q=stacked_preview(a,b)
assert q['result'] and q['reason']=='BOOST_ITEM_UNAVAILABLE' and q['protection']['blocked'] and 'token' not in q['protection'] and Path(h.STATE).read_bytes()==raw
checks.append('Last booster removes stack; inventory quantity/path changes invalidate quote; absent booster is nonfatal blocked read with zero spend')
a,b=boosted_fresh();q=stacked_preview(a,b);raw=Path(h.STATE).read_bytes()
with patch.object(h,'_save',side_effect=OSError('Injected stacked atomic-save failure')):
 try:stacked_execute(a,b,q)
 except OSError:pass
 else:raise AssertionError('save failure expected')
assert Path(h.STATE).read_bytes()==raw
with patch.object(h.random,'random',return_value=.999999):assert stacked_execute(a,b,q)['result']
a,b=boosted_fresh();q=stacked_preview(a,b);n=len(commits)
with patch.object(h.random,'random',return_value=.999999),concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(lambda _:stacked_execute(a,b,q),range(2)))
assert sum(row['result'] for row in rows)==1 and len(commits)==n+1
checks.append('Stacked save failure preserves persisted assets; retry works; concurrent same quote commits once')
a,b=boosted_fresh(6,6);raw=Path(h.STATE).read_bytes();q=stacked_preview(a,b)
assert q['result'] and q['protection']['blocked'] and q['probability']==100 and Path(h.STATE).read_bytes()==raw
a,b=boosted_fresh();q=stacked_preview(a,b);raw=Path(h.STATE).read_bytes();st=h._state();pa=getcard(st,a);before_ep=h.my_coach(st)['ep'];before_count=h.boost_stack(st,'1000052')['remains']
with patch.object(h.random,'random',return_value=.999999):r=call(f'/player/{a}/enhance2.5/{b}/0/1000052/-1')
assert r['result'] and h.my_coach(h._state())['ep']==before_ep-h.enhance_cost(pa) and h.boost_stack(h._state(),'1000052')['remains']==before_count-1
assert h.grade_of(getcard(h._state(),a))==h.enhancement_failure_grade(pa)
rules=call('/info/enhancement/protection/rules');assert rules['independent_checkbox'] and not rules['boost_item_exclusive']
checks.append('Capped 100% gold combo needs no paid protection; unchecked gold retains original fee/drop/stock behavior; pseudo service removed from dropdown inventory')
result={'status':'PASS','checks':checks,'native_pass':False,'formal_state_written':False,'temporary_state':str(h.STATE)}
(W/'server-tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=True,indent=2))
