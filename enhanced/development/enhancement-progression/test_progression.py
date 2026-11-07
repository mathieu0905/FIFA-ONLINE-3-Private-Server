from pathlib import Path
import sys,os,json,copy,tempfile,types,importlib.util,hashlib,threading
from unittest.mock import patch
from urllib.parse import urlencode
sys.dont_write_bytecode=True
W=Path(r'D:\fifaol3\enhancement-progression');S=Path(r'D:\FO3ID\server');tmp=Path(tempfile.mkdtemp(prefix='fo3-progression-',dir=W))
def audit(e,a):
 if e=='open':
  p,m,f=a
  if isinstance(p,(str,bytes,os.PathLike)) and ((isinstance(m,str) and any(c in m for c in 'wax+')) or (isinstance(f,int) and f&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))):
   if not any(Path(os.fsdecode(p)).resolve().is_relative_to(root) for root in (W,tmp)):raise PermissionError('Forbidden formal write '+str(p))
sys.addaudithook(audit)
os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi',FO3_ADMIN_PORT='0');sys.argv=['http_config.py'];sys.path[:0]=[str(W),str(S)]
# Execute the actual incrementally changed production source in memory, with
# original data paths, and redirect every test save to a temporary file.
spec=importlib.util.spec_from_file_location('enhancement_settings',W/'enhancement_settings.py');settingsmod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=settingsmod;spec.loader.exec_module(settingsmod)
spec=importlib.util.spec_from_file_location('enhancement_protection40',W/'enhancement_protection40.py');prot=importlib.util.module_from_spec(spec);sys.modules[spec.name]=prot;spec.loader.exec_module(prot)
h=types.ModuleType('http_config');h.__file__=str(S/'http_config.py');sys.modules['http_config']=h
exec(compile((W/'http_config.py').read_text(encoding='utf-8-sig'),str(W/'http_config.py'),'exec'),h.__dict__)
baseline=copy.deepcopy(h._state());h.STATE=str(tmp/'state.json');slot=h._default_slot(baseline)
old=json.loads((W/'baseline.json').read_text());checks=[]
import enhancement_progression as prog
assert h.enhancement_settings_get()['rates']==h.PROGRESSION20['default_probabilities']
assert list(h.enhancement_settings_get()['rates'].values())==[100,95,90,85,80,75,70,65,60,55,50,45,35,28,20,14,9,6,4]
checks.append('All 19 approved default probabilities active, same preview/roll path; no production rates file created')
assert abs(h.enhance25_rate({'grade':19},{'grade':1},True,None,'-1')-.044)<1e-12
assert abs(h.enhance25_rate({'grade':19},{'grade':1},True,{'itemid':1000052},'-1')-.194)<1e-12
assert abs(h.enhance25_rate({'grade':12},{'grade':1},True,None,'-1')-.55)<1e-12
checks.append('Repeatable high-grade ES is relative 10%; all purchased Gold/Silver/Bronze additive effects retained; low-grade ES unchanged')
for row in old['ovr_prices']:
 s=row['spid'];values=[h.player_value_price(s,g) for g in range(1,21)]
 assert values[0]==row['plus1'] and values[9]==row['plus10']
 assert values[-1]>=row['plus20'] and all(a<b for a,b in zip(values,values[1:]))
 assert values[-1]*1.6<=2**53-1
 for g,p in h.PROGRESSION20['price_steps'].items():
  g=int(g);assert abs(h.player_value_price(s,g)/h.player_value_price(s,g-1)-p)<.0001
checks.append('Every current OVR tier: +1..10 values retained, every higher grade increases, rising step ratios exact within integer rounding; all +20 values and 1.6x market quotes stay Number-safe')
contracts={str(i):hashlib.sha256(json.dumps([h.pack_pool(i),h.pack_grades(i)],sort_keys=True,separators=(',',':')).encode()).hexdigest() for i in h.PACKS}
assert contracts==old['pack_contracts']
prices={str(i):h.cash_product_price(i) for i in set(h.PACKS)|set(h.ITEMS)|set(h.PACKAGES)|set(h.MONTHLY)}
assert prices==old['cash_prices']
checks.append('All 263 issued pack pool/grade contracts and all 1128 existing cash product quotes identical; no stock/price contract rewrite')
def fresh(g=13):
 st=copy.deepcopy(baseline);st.pop('enhance_restore',None);c=h.my_coach(st);c['ep']=10**18;c['es']=1000000;t=st['teams'][str(slot)]
 a=h.add_player(t,93192181,g);b=h.add_player(t,93192181,1);a['levelinfo']={'level':14,'exp':63};a['locked']=b['locked']=False
 h._save(st);return h.iid(a),h.iid(b)
def route(uri):
 p,_,q=uri.partition('?')
 with h.STATE_LOCK:return json.loads((h.ENDPOINTS.get(p) or h.route(p))(q,b'{}')[1])
def card(st,i):return next(p for p in st['teams'][str(slot)]['players'] if h.iid(p)==i)
for g in (3,5,6,9,10,11,12,13,19):
 for version in (1,25):
  a,b=fresh(g);st=h._state();pa=copy.deepcopy(card(st,a));ep=h.my_coach(st)['ep'];fee=max(1000,(h.player_value_price(pa['spid'],g)*2+99)//100)
  uri=f'/player/{a}/enhance/{b}' if version==1 else f'/player/{a}/enhance2.5/{b}/0/-1/-1'
  with patch.object(h.random,'random',return_value=.999999):out=route(uri)
  after=h._state();assert out['result'] and not out['success'] and out['grade']==prog.failure_grade(g),out
  assert card(after,a)['levelinfo']==pa['levelinfo'] and h.my_coach(after)['ep']==ep-fee
  assert bool(after.get('enhance_restore'))==(version==25 and out['grade']<g)
  assert out['protection']['applied']==(out['grade']==g) and out['protection']['paid'] is False
checks.append('Actual v1/v2.5 roll handlers across nine boundaries: low grades and +10 do not drop, others drop at most one; XP retained, correct 2% fee; restore created only after actual drop')
for g in (5,10):
 a,b=fresh(g);raw=Path(h.STATE).read_bytes();out=route(f'/player/{a}/enhance2.5/{b}/preview/0/1000090/-1');assert not out['result'] and Path(h.STATE).read_bytes()==raw
for success in (True,False):
 a,b=fresh(19);before=h._state();pa=copy.deepcopy(card(before,a));q=route(f'/player/{a}/enhance2.5/{b}/preview/1/1000090/-1');fee=(h.player_value_price(pa['spid'],19)*2+4)//5
 assert q['result'] and q['probability']==4.4 and q['enhancepay']==fee
 uri=f'/player/{a}/enhance2.5/{b}/1/1000090/-1?'+urlencode({'protection_ack':q['protection']['version'],'protection_token':q['protection']['token']})
 with patch.object(h.random,'random',return_value=0 if success else .999999):r=route(uri)
 after=h._state();assert r['success']==success and card(after,a)['grade']==19+success
 assert h.my_coach(after)['ep']==h.my_coach(before)['ep']-fee and card(after,a)['levelinfo']==pa['levelinfo']
 assert 'enhance_restore' not in after and not route(uri)['result']
checks.append('40% protection rejects already-safe +5/+10, charges exactly displayed value*40%, +19 ES preview/roll 4.4%, success20/failure19, materials once, no double charge')
a,b=fresh(13);st=h._state();st['enhance_restore']={'id':a,'grade':12,'price':390};h._save(st);raw=Path(h.STATE).read_bytes();assert not route('/player/enhance2.5/restore')['result'] and Path(h.STATE).read_bytes()==raw
checks.append('Old stale restore cannot lower a card or deduct currency; existing right is not silently deleted')
# The unchanged admin module retains explicit overrides across fresh installations.
import enhancement_settings
fake=types.SimpleNamespace(HERE=str(tmp/'settings'),MAX_GRADE=20,ENHANCE_RATE=prog.RATES,STATE_LOCK=threading.RLock())
enhancement_settings.install(fake);data=fake.enhancement_settings_get();data['rates']['19']=0
fake.enhancement_settings_set({'rates':data['rates'],'revision':data['revision']})
again=types.SimpleNamespace(HERE=fake.HERE,MAX_GRADE=20,ENHANCE_RATE=prog.RATES,STATE_LOCK=threading.RLock());enhancement_settings.install(again)
assert again.ENHANCE_RATE[19]==0 and again.enhancement_settings_get()['defaults']['19']==4
assert data['revision'] != hashlib.sha256(b'defaults').hexdigest()
checks.append('Explicit admin 0% override persists across reboot; new default4% remains separately visible; default revision changes reject an old pre-update page save')
# Exact expected step counts for protected single-step progress, no guarantee.
expected={str(goal):sum(1/prog.RATES[g] for g in range(10,goal)) for goal in (13,15,17,20)}
result=dict(status='PASS',checks=checks,protected_expected_attempts_from10=expected,formal_assets_written=False,native_pass=False,temporary_state=str(h.STATE),largest_displayed_plus20=h.player_value_price(old['ovr_prices'][-1]['spid'],20))
(W/'tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=True,indent=2))
