"""Execute actual upgraded reward handlers entirely in memory."""
import ast,copy,datetime,json,time,uuid
from types import SimpleNamespace
import reward_upgrade as r
from prepare import write
data=json.loads((r.R/'build.json').read_text('utf8'));clock=[1800000000.0]
fake_time=SimpleNamespace(time=lambda:clock[0],gmtime=time.gmtime,strftime=time.strftime)
http=ast.parse((r.R/'http_config.py').read_text('utf8'));economy=ast.parse((r.R/'economy.py').read_text('utf8'))
def functions(parent,names,env):
 found=[copy.deepcopy(n) for n in parent.body if isinstance(n,ast.FunctionDef) and n.name in names];assert {n.name for n in found}==set(names)
 for n in found:n.decorator_list=[]
 exec(compile(ast.Module(body=found,type_ignores=[]),'actual_reward_handlers','exec'),env)
 return env
env=dict(time=fake_time,WIB=7*3600,EP_ITEM=1000000,my_coach=lambda st:st['coaches'][0],new_iid=lambda:uuid.uuid4().hex,daily_table=lambda:data['daily'])
functions(http,{'today_wib','reward_items','bag_add','daily_login'},env)
native_daily=env['daily_login'];st={'coaches':[{}]}
for day in range(7):
 clock[0]=1800000000.0+day*86400;entry=native_daily(st);assert entry['items']==env['reward_items'](data['daily'][day])
 before=copy.deepcopy(st);assert native_daily(st) is None and st==before
assert len(st['coaches'][0]['bag'])==7 and st['coaches'][0]['daily']['streak']==7
clock[0]+=3*86400;native_daily(st);assert st['coaches'][0]['daily']['streak']==1
hc=SimpleNamespace(my_coach=env['my_coach'],today_wib=env['today_wib'],time=fake_time,w3c=str)
eco=dict(hc=hc,START_CASH=500,CASH_MAX=10**9,DAILY_CASH=10000,MATCH_DAILY_CAP=10000,original_daily=native_daily,original_reward=lambda st,stats:{})
installer=next(n for n in economy.body if isinstance(n,ast.FunctionDef) and n.name=='install')
functions(installer,{'balance','add_cash','daily_login','match_reward'},eco)
st={'coaches':[{'cash':77}]};eco['daily_login'](st);assert st['coaches'][0]['cash']==10077
same=copy.deepcopy(st);eco['daily_login'](st);assert st==same
clock[0]+=86400;eco['daily_login'](st);assert st['coaches'][0]['cash']==20077
old={'coaches':[{'cash':77,'cash_daily_day':env['today_wib']()}]};eco['daily_login'](old);assert old['coaches'][0]['cash']==77
scores=[(2,1,1000),(1,1,700),(0,1,400)]
st={'coaches':[{'cash':0}]}
for index,(mine,opp,grant) in enumerate(scores):
 st['match']={'id':str(index)};out=eco['match_reward'](st,dict(myTeam='home',opponentTeam='away',home={'score':mine},away={'score':opp}));assert out['cashreward']['total']==grant
 before=copy.deepcopy(st);eco['match_reward'](st,dict(home={'score':mine},away={'score':opp}));assert st==before
st['match']={'id':'simulated','simulated':True};before=copy.deepcopy(st);eco['match_reward'](st,{});assert st==before
for i in range(30):
 st['match']={'id':'win'+str(i)};eco['match_reward'](st,dict(home={'score':3},away={'score':0}))
assert st['coaches'][0]['cash_match_rewards']['earned']==10000 and st['coaches'][0]['cash']==10000
monthly={int(k):v for k,v in data['monthly'].items()};st={'coaches':[{'monthly':{str(i):dict(expire=clock[0]+40*86400,rewarded=0,since=clock[0]) for i in monthly}}]};saves=[]
monthly_env=dict(env,MONTHLY=monthly,_state=lambda:st,_save=lambda state:saves.append(copy.deepcopy(state)),_json=lambda value:value,monthly_list=lambda state:[],bag_list=lambda state:state['coaches'][0].get('bag',[]))
functions(http,{'ep_monthlypack'},monthly_env)
monthly_env['ep_monthlypack']('',b'{}');assert len(st['coaches'][0]['bag'])==3
for e,i in zip(st['coaches'][0]['bag'],monthly):assert e['items']==[dict(itemid=item,count=n) for item,n in monthly[i][4]]
monthly_env['ep_monthlypack']('',b'{}');assert len(st['coaches'][0]['bag'])==3
clock[0]+=86400;monthly_env['ep_monthlypack']('',b'{}');assert len(st['coaches'][0]['bag'])==6
for m in st['coaches'][0]['monthly'].values():m['expire']=clock[0]-1
clock[0]+=86400;monthly_env['ep_monthlypack']('',b'{}');assert len(st['coaches'][0]['bag'])==6
module=r.common.load(r.R/'pack_value.py','triangular_value_test')
def enumerated(lo,hi):
 if lo==hi:return float(lo)
 num=0
 for k in range(lo//10000-1,hi//10000+2):
  left=max(lo,k*10000-5000);right=min(hi,k*10000+5000)
  if right>left:num+=max(lo,k*10000)*((hi-left)**2-(hi-right)**2)
 return num/((hi-lo)**2)
for bounds in [(0,1000),(0,30000),(18000,19000),(12345,67890),(10000,1000000),(1000000,100000000),(30000,30000)]:assert module.triangular_ep_value(bounds)==enumerated(*bounds)
assert 0<module.triangular_ep_value((10000,10**12))<10**12
for i,new in monthly.items():
 old=data['monthly_before'][str(i)];assert new[2]==old[2]==30 and all(x in new[3] for x in old[3]) and all(x in new[4] for x in old[4])
p=r.plan();write(r.R/'tests.json',dict(status='PASS',checks=['seven actual daily handlers and same-day replay','broken streak without asset reset','10000 daily cash and old claimed flag retained','1000/700/400 real matches, replay, simulation, 10000 cap','three monthly daily claims, duplicate, next-day, expiration','all original monthly now/daily items preserved','exact triangular/rounding/clamp expected BP including huge bounds','fresh parent and resource/receipt composition'],monthly_prices=[x for x in data['prices'] if x['id'] in monthly],parent=p['prior']))
print('Actual reward handlers and valuation tests PASS')
