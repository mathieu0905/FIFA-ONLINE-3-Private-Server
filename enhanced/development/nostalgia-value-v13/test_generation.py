"""New generation transaction, archive verification, retry and market factor conservation."""
from pathlib import Path
from contextlib import closing
import copy,gzip,hashlib,importlib.util,json,sqlite3,tempfile,types,sys
import fair_value_model as m
import fair_value_store as new
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
def load(path,name):
 sp=importlib.util.spec_from_file_location(name,path);v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v);return v
def writecat(path,value):path.write_bytes(gzip.compress(json.dumps(value).encode()))
def main():
 old=load(S/'fair_value_store.py','old_fair_generation');storemodule=load(S/'market_price_store.py','v13_store_contract');original=json.loads((S/'gamedata/fair-value-v12-model.json').read_text('utf8'));out=Path(json.loads((P/'latest-build.json').read_text('utf8'))['path']);latest=json.loads((out/'model.json').read_text('utf8'));checks=[]
 cached=sys.modules.get('fair_value_store');sys.modules['fair_value_store']=old
 maintenance=load(P/'fair_value_store.py','v13_unique_maintenance_regression');assert maintenance.install_catalogue.__code__.co_filename==str(P/'fair_value_store.py');assert sys.modules['fair_value_store'] is old
 sys.modules['fair_value_store']=cached;checks.append('Isolated maintenance loader uses new migration even when parent preflight cached old module; no reload of old module')
 with tempfile.TemporaryDirectory(prefix='fo3-v13-generation-') as folder:
  t=Path(folder);source=t/'source.db';database=t/'prices.db';oldfile=t/'old.json';newfile=t/'new.json';oldcat=t/'old.gz';newcat=t/'new.gz';seedpath=t/'seed.gz'
  fields=m.fields(original);columns=['spid','playerid']+fields+['weakfootabilitytypecode','skillmoves'];raw=[dict(spid=10000001,playerid=1,**{k:70 for k in fields},weakfootabilitytypecode=3,skillmoves=2),dict(spid=20000001,playerid=1,**{k:80 for k in fields},weakfootabilitytypecode=4,skillmoves=3)]
  with closing(sqlite3.connect(source)) as db,db:
   db.execute('create table players('+','.join(k+' integer' for k in columns)+')');db.executemany('insert into players values('+','.join('?' for _ in columns)+')',[[r[k] for k in columns] for r in raw])
  rows=[[r['spid'],1000] for r in raw];seed=dict(schema=1,price_region='kr',model_sha256='a'*64,rows=rows,seed_prices_sha256=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest());writecat(seedpath,seed);storemodule.initialize(database,seedpath,'seed');oldfile.write_text(json.dumps(original),'utf8');oldcatalogue=m.build_catalogue(source,original);writecat(oldcat,oldcatalogue);old.install_catalogue(database,oldcat,oldfile,source)
  # An already-earned shared market movement must survive currency/model changes.
  live=storemodule.MarketPriceStore(database);state={'market_simulation':{'fair_revision':original['revision'],'identity_quotes':{}}}
  for i,at in enumerate([100000,100900,101900]):live.fair.stage_trade(state,dict(id='earned'+str(i),spid=10000001,ratio=1.2,price=10,grade=1),at)
  live.flush(state['market_simulation']['price_events']);state['market_simulation']['price_events']=[];factor=live.fair.factors[1];live.close();assert factor>1.
  with closing(sqlite3.connect(database)) as db:before_prices=db.execute('select * from prices order by spid').fetchall();before_values=db.execute('select * from fair_values order by spid').fetchall();before_events=db.execute('select * from price_events order by event_id').fetchall();before_seeds=db.execute('select * from seeds').fetchall()
  with closing(sqlite3.connect(source)) as db,db:db.execute('update players set finishing=finishing-5 where spid=10000001')
  newfile.write_text(json.dumps(latest),'utf8');newcatalogue=m.build_catalogue(source,latest);newcatalogue['expected_previous_revision']=original['revision'];writecat(newcat,newcatalogue)
  collision='fair-calibration:'+latest['revision']+':20000001'
  with closing(sqlite3.connect(database)) as db,db:db.execute('insert into price_events values(?,?,?,?,?,?,?)',(collision,20000001,1.,2.,0.,'fixture_conflict','{}'))
  try:new.install_catalogue(database,newcat,newfile,source)
  except sqlite3.IntegrityError:pass
  else:raise AssertionError('Expected partial-generation receipt collision')
  with closing(sqlite3.connect(database)) as db,db:
   assert db.execute('select * from prices order by spid').fetchall()==before_prices;assert db.execute('select * from fair_values order by spid').fetchall()==before_values;assert not db.execute("select name from sqlite_master where name='fair_generation_history'").fetchone();db.execute('delete from price_events where event_id=?',(collision,))
  checks.append('Mid-generation conflict rolls back active values, prices, archive schema and metadata atomically')
  assert new.install_catalogue(database,newcat,newfile,source)['applied'];assert not new.install_catalogue(database,newcat,newfile,source)['applied']
  assert new.verify_installed(database,oldcat,oldfile,source)['status']=='FAIR_VALUE_HISTORICAL_GENERATION_PASS';new.verify_installed(database,newcat,newfile,source)
  with closing(sqlite3.connect(database)) as db:
   assert db.execute('select factor from player_market_factors where playerid=1').fetchone()[0]==factor
   assert db.execute('select * from seeds').fetchall()==before_seeds
   assert all(db.execute('select * from price_events where event_id=?',(r[0],)).fetchone()==r for r in before_events)
  checks.append('Upgrade/retry preserves previous seeds/trades and earned market factor; archives verify independently of changed current attributes')
  migrated=new.migrate_state(state,latest['revision']);assert migrated['market_simulation']['identity_quotes']==state['market_simulation']['identity_quotes'];assert migrated==new.migrate_state(migrated,latest['revision']);checks.append('State generation migration preserves current factor, daily budget and assets, and is idempotent')
  live=storemodule.MarketPriceStore(database);assert live.fair.revision==latest['revision'];assert live.fair.factors[1]==factor;assert live.current(20000001)>live.current(10000001);live.close()
  with closing(sqlite3.connect(database)) as db,db:db.execute('update fair_value_history set economic_value=economic_value+1 where revision=? and spid=10000001',(original['revision'],))
  try:new.verify_installed(database,oldcat,oldfile,source)
  except ValueError:pass
  else:raise AssertionError('Historical generation tamper accepted')
  checks.append('Archived valuation tampering is rejected; old source is not falsely checked against the new roster')
  wrong=dict(newcatalogue,revision='another',expected_previous_revision='unexpected')
  # A wrong parent is refused even when model/profile input is otherwise valid.
  wrongcfg=dict(latest,revision='another');wrong['model_sha256']=hashlib.sha256(m.canonical(wrongcfg)).hexdigest();newfile.write_text(json.dumps(wrongcfg),'utf8');writecat(newcat,wrong)
  try:new.install_catalogue(database,newcat,newfile,source)
  except ValueError as exc:assert 'generation changed' in str(exc)
  else:raise AssertionError('Wrong publication parent accepted')
  checks.append('Generation CAS rejects replacing a newer/different valuation')
 result=dict(status='PASS',checks=checks,formal_written=False);(P/'generation-regression.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
