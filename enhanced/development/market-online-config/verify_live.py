from pathlib import Path
import ast,sqlite3
S=Path('D:/FO3ID/server')
def verify(api):
 tree=ast.parse((S/'http_config.py').read_text('utf-8-sig'));scope={'MAX_GRADE':20}
 for name in ('ROLE_WEIGHTS','POS_ROLE','POSOVR','GRADE_BOOST','LINES'):
  node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
  exec(compile(ast.Module(body=[node],type_ignores=[]),'rating-only','exec'),scope)
 scope['GRADE_BOOST']=scope['GRADE_BOOST'][:11]+tuple(24+2*(g-10) for g in range(11,21))
 def inspect(rows):
  assert rows and len(rows)<=200
  ids=[int(r['spid']) for r in rows]
  with sqlite3.connect(str(S/'gamedata/fifadb.sqlite')) as db:
   base={s:(o,pos) for s,o,pos in db.execute('SELECT p.spid, '+scope['POSOVR']+', p.preferredposition1 FROM players p WHERE spid IN ('+','.join('?'*len(ids))+')',ids)}
  values=[]
  for r in rows:
   assert r['count']>0 and r['price']>0
   lv=int((r.get('levelinfo') or {}).get('level',1));bonus=lv-1 if lv<=23 else 22+(lv-22)//2
   values.append(base[int(r['spid'])][0]+scope['GRADE_BOOST'][int(r['grade'])]+bonus)
  assert values==sorted(values,reverse=True),values
  return values,base
 top=api('/transfer/top/50');assert len(top)==200;abilities,_=inspect(top);positions={}
 for pos in ('GK','DF','MF','FW'):
  rows=api('/transfer/top/50/position/'+pos);values,base=inspect(rows)
  assert all(base[int(r['spid'])][1] in scope['LINES'][pos] for r in rows)
  positions[pos]=dict(count=len(rows),abilities=values)
 state=__import__('json').loads((S/'gamedata/state.json').read_text('utf8'))['market_simulation']
 allowed=lambda r:int(r['spid'])//1000000!=84 or int(r['grade'])<=5
 assert all(allowed(r) for table in ('books','rare_books') for batch in state[table].values() for r in batch['rows'])
 assert all(allowed(r) for r in state.get('legacy_supply',[]))
 assert all(allowed(a) for a in state['npc_exchange']['assets'].values() if a.get('listing'))
 rows=api('/transfer/search/84037576');assert rows and all(allowed(r) for r in rows)
 assert all(allowed(r) for r in top)

 cfg=api('/api/market_supply_config');assert cfg['error'] is None and cfg['revision']==cfg['active_revision']
 status=api('/api/market_status');assert status['online_supply_config']['active_revision']==cfg['active_revision']
 assert status['refresh_seconds']==cfg['settings']['regular_refresh_seconds']
 for tier in status['rare_world_limits']:
  batch=state['rare_books'].get(tier['key'])
  if batch and __import__('time').time()<batch['start']+batch['period']:
   assert batch['pool_size']>=tier['pool_size'],tier['key']
 return dict(online_config_revision=cfg['active_revision'],online_config_error=cfg['error'],top_rows=top,abilities=abilities,positions=positions,order_verified=True,im_grades=sorted({r['grade'] for r in rows}),im_cap_verified=True)
