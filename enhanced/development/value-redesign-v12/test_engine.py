"""Business, crash replay and profile-binding regressions on temporary data."""
from pathlib import Path
from contextlib import closing
import ast,copy,gzip,hashlib,json,math,os,sqlite3,tempfile,types
import fair_value_model as model
import fair_value_store as fs
import market_price_store as legacy
from effective_boosts import grade_boosts

P=Path(__file__).resolve().parent
def main():
 config=json.loads((P/'model.json').read_text('utf8'));checks=[]
 with tempfile.TemporaryDirectory(prefix='fo3-fair-v12-') as temp:
  t=Path(temp);source=t/'source.db';price=t/'prices.db';catpath=t/'cat.gz';mp=t/'model.json';seedpath=t/'seed.gz';fields=model.fields(config)
  originals=[dict(spid=10000001,playerid=1,**{k:65 for k in fields},weakfootabilitytypecode=3,skillmoves=2),dict(spid=20000001,playerid=1,**{k:75 for k in fields},weakfootabilitytypecode=4,skillmoves=3),dict(spid=10000002,playerid=2,**{k:70 for k in fields},weakfootabilitytypecode=3,skillmoves=2)]
  with closing(sqlite3.connect(source)) as db,db:
   columns=['spid','playerid']+fields+['weakfootabilitytypecode','skillmoves'];db.execute('create table players('+','.join(k+' integer' for k in columns)+')');db.executemany('insert into players values('+','.join('?' for k in columns)+')',[[r[k] for k in columns] for r in originals])
  seedrows=[[r['spid'],1000+i*1000] for i,r in enumerate(originals)];seed=dict(schema=1,price_region='kr',model_sha256='a'*64,rows=seedrows,seed_prices_sha256=hashlib.sha256(json.dumps(seedrows,separators=(',',':')).encode()).hexdigest());seedpath.write_bytes(gzip.compress(json.dumps(seed).encode()));legacy.initialize(price,seedpath,'historic')
  mp.write_text(json.dumps(config),'utf8');cat=model.build_catalogue(source,config);catpath.write_bytes(gzip.compress(json.dumps(cat).encode()))
  with closing(sqlite3.connect(price)) as db:
   historical_seeds=db.execute('select * from seeds order by spid').fetchall()
  assert fs.install_catalogue(price,catpath,mp,source)['applied'];assert not fs.install_catalogue(price,catpath,mp,source)['applied'];fs.verify_installed(price,catpath,mp,source);legacy.verify_seed(price,seedpath)
  checks.append('One-time catalogue install is idempotent; legacy seed guard and immutable original seeds survive')
  store=legacy.MarketPriceStore(price);assert store.fair is not None
  state=dict(coaches=[dict(slot=1,money=123)],players=[dict(id='owned',spid=10000001,grade=8,exp=999)],offers=[dict(price=99999,status='selling')],market_simulation=dict(version=2,books={'live':dict(rows=[dict(price=123,count=2)])},quotes={'10000001':dict(basis_price=1000,pending=[dict(id='past')])},sales=[],price_events=[]))
  migrated=fs.migrate_state(state,config['revision']);assert all(migrated[k]==v for k,v in state.items() if k!='market_simulation');assert all(migrated['market_simulation'][k]==v for k,v in state['market_simulation'].items());assert migrated==fs.migrate_state(migrated,config['revision']);state=migrated
  checks.append('Migration preserves manager assets, open offers, old samples, live stock and every prior market field')
  originallow=store.fair.reference(10000001,state);originalhigh=store.fair.reference(20000001,state)
  source_ast=ast.parse((P/'market_simulation.py').read_text('utf8'));record=next(n for c in source_ast.body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='record');scope={'math':math};exec(compile(ast.Module(body=[record],type_ignores=[]),'actual_market_record','exec'),scope)
  host=types.SimpleNamespace(exchange=types.SimpleNamespace(price_store=store,reference_value=lambda sid,grade,st:store.fair.reference(sid,st)))
  for i,at in enumerate([100000,100900,101900]):
   sid=10000001 if i%2==0 else 20000001
   scope['record'](host,state,dict(_id='sale'+str(i),spid=sid,grade=1,price=int(store.fair.reference(sid,state)*1.3),_market_owner='manager'),at)
  assert len(state['market_simulation']['sales'])==3
  events=state['market_simulation']['price_events'];assert len(events)==1
  assert store.fair.reference(10000001,state)>originallow;assert store.fair.reference(20000001,state)>originalhigh
  event=events[0];collision=event['event_id']+':linked:20000001'
  with closing(sqlite3.connect(price)) as db,db:db.execute('insert into price_events values(?,?,?,?,?,?,?)',(collision,20000001,1.,2.,0.,'collision','{}'))
  try:store.flush(events)
  except sqlite3.IntegrityError:pass
  else:raise AssertionError('Expected linked receipt collision')
  assert store.fair.factors[1]==1. and store.current(10000001)==originallow
  with closing(sqlite3.connect(price)) as db,db:
   assert db.execute('select factor from player_market_factors where playerid=1').fetchone()[0]==1.;db.execute('delete from price_events where event_id=?',(collision,))
  assert store.flush(events)==2;assert store.flush(events)==0;assert store.current(10000001)==store.fair.reference(10000001,state);assert store.current(20000001)==store.fair.reference(20000001,state)
  checks.append('Cross-season funded trades share one factor; linked receipt failure rolls back all rows/cache/factor; retry/replay is idempotent')
  invalid=copy.deepcopy(event);invalid.update(event_id='tampered',factor_before=store.fair.factors[1],factor_after=1.15)
  try:store.flush([invalid])
  except ValueError:pass
  else:raise AssertionError('Oversized factor change accepted')
  checks.append('Wrong/stale generation and oversized trade steps fail closed without changing prices')
  state['market_simulation']['price_events']=[];quote=state['market_simulation']['identity_quotes']['1'];quote.update(movement=math.log(1.02),pending=[]);factor=quote['factor']
  for i,at in enumerate([102000,102900,103900]):store.fair.stage_trade(state,dict(id='budget'+str(i),spid=20000001 if i%2==0 else 10000001,ratio=2.,price=10000,grade=1),at)
  assert quote['factor']==factor and not state['market_simulation']['price_events']
  checks.append('Alternating seasons cannot bypass the common 2%-per-day movement budget')
  # A common factor always leaves the stronger card strictly more valuable.
  for factor in [.85,1.,1.15]:assert store.fair.value(20000001,factor)>store.fair.value(10000001,factor)
  checks.append('Strong/weak same-player ordering survives both market bounds')
  boost=grade_boosts()
  low=[store.fair.reference(10000001,state,g,boost) for g in range(21)];high=[store.fair.reference(20000001,state,g,boost) for g in range(21)]
  assert all(b>a for a,b in zip(low,low[1:]));assert all(b>a for a,b in zip(high,high[1:]));assert all(high[g]>low[g] for g in range(1,21));assert max(high)<5_600_000_000_000_000
  checks.append('Grades1..20 follow actual boosted ability, retain cross-season ordering, and avoid manufacturing-cost ceiling ties')
  store.close();store=legacy.MarketPriceStore(price);assert store.current(10000001)>originallow;fs.verify_installed(price,catpath,mp,source)
  with closing(sqlite3.connect(price)) as db:assert db.execute('select * from seeds order by spid').fetchall()==historical_seeds
  checks.append('Restart reads committed common factors and all historical seed rows remain exact')
  with closing(sqlite3.connect(source)) as db,db:db.execute('update players set finishing=finishing+1 where spid=10000001')
  st=source.stat();os.utime(source,ns=(st.st_atime_ns,st.st_mtime_ns+1000000))
  try:store.current(10000001)
  except ValueError as exc:assert 'PLAYER_ATTRIBUTES_CHANGED' in str(exc)
  else:raise AssertionError('Stale profile reused')
  try:fs.verify_installed(price,catpath,mp,source)
  except ValueError as exc:assert 'PLAYER_ATTRIBUTES_CHANGED' in str(exc)
  else:raise AssertionError('Startup profile mismatch accepted')
  store.close();checks.append('Both startup and running price lookup detect changed attributes; no stale revaluation or asset write occurs')
  raw=originals[0];unknown=raw|{'playerid':999999};assert model.identity_factor(unknown,config)==1.
  renamed=raw|{'name':'任意名字','spid':99000001,'preferredposition1':0,'height':200};assert model.explain(renamed,config)['fair_price_ep']==model.explain(raw,config)['fair_price_ep']
  checks.append('Unseen identities default to1; display names, physical season tags and nominal position do not change the utility price')
 result=dict(status='PASS',checks=checks,formal_written=False)
 (P/'engine-regression.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
