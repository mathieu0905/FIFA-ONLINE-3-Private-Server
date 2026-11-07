"""Transaction and asset-preservation regression using disposable data only."""
from pathlib import Path
from contextlib import closing
import gzip,hashlib,importlib.util,json,sqlite3,tempfile
P=Path(__file__).resolve().parent

def main():
 sp=importlib.util.spec_from_file_location('store',P/'market_price_store.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
 with tempfile.TemporaryDirectory(prefix='fo3-valuation-') as t:
  root=Path(t);seed=root/'seed.gz';database=root/'prices.db';packet=root/'new.gz'
  prices=[[1,100],[2,200],[3,300]];digest=lambda v:hashlib.sha256(json.dumps(v,separators=(',',':')).encode()).hexdigest()
  original=dict(schema=1,price_region='kr',rows=prices,model_sha256='a'*64,seed_prices_sha256=digest(prices))
  seed.write_bytes(gzip.compress(json.dumps(original).encode()));m.initialize(database,seed,'old')
  store=m.MarketPriceStore(database);store.flush([dict(event_id='trade-old',spid=1,before=100.,after=101.,at=1.,reason='funded_trade_volume')]);store.close()
  new=dict(schema=1,revision='new',model_sha256='b'*64,rows=[[1,400],[2,500],[3,600]])
  new['prices_sha256']=digest(new['rows']);packet.write_bytes(gzip.compress(json.dumps(new).encode()))
  with closing(sqlite3.connect(database)) as db,db:
   seeds=db.execute('select * from seeds').fetchall();old=db.execute('select * from price_events').fetchall()
   # Force a collision halfway through to prove rollback, including earlier rows.
   db.execute('insert into price_events values(?,?,?,?,?,?,?)',('valuation:new:2',2,200.,500.,1.,'model_recalibration','{}'))
  try:m.apply_calibration(database,packet)
  except sqlite3.IntegrityError:pass
  else:raise AssertionError('Expected mid-transaction failure')
  with closing(sqlite3.connect(database)) as db,db:
   assert db.execute('select basis_price from prices where spid=1').fetchone()[0]==101.
   assert not db.execute("select value from metadata where key='valuation_revision'").fetchone()
   db.execute("delete from price_events where event_id='valuation:new:2'")
  assert m.apply_calibration(database,packet)['applied']
  assert not m.apply_calibration(database,packet)['applied']
  with closing(sqlite3.connect(database)) as db,db:
   assert db.execute('select * from seeds').fetchall()==seeds
   assert db.execute("select * from price_events where event_id='trade-old'").fetchall()==old
   assert db.execute('select count(*) from price_events').fetchone()[0]==4
  m.verify_seed(database,seed)
  store=m.MarketPriceStore(database);store.flush([dict(event_id='trade-new',spid=1,before=400.,after=401.,at=2.,reason='funded_trade_volume')]);store.close()
  assert not m.apply_calibration(database,packet)['applied'];m.verify_calibration(database,packet)
  with closing(sqlite3.connect(database)) as db,db:assert db.execute('select basis_price from prices where spid=1').fetchone()[0]==401.
  state=dict(coaches=[dict(id='real',money=999)],players=[dict(id='owned',exp=19,grade=7)],offers=[dict(price=123)],market_simulation=dict(quotes={'1':dict(basis_price=101.,pending=[dict(id='funded')])},books={'live':dict(rows=[dict(price=111,count=1)])},price_events=[]))
  after=m.migrate_quote_state(state,new)
  assert state['market_simulation']['quotes']['1']['basis_price']==101.
  assert all(after[k]==v for k,v in state.items() if k!='market_simulation')
  assert after['market_simulation']['books']==state['market_simulation']['books']
  assert after['market_simulation']['quotes']['1']['valuation_history'][0]['pending']==[dict(id='funded')]
  assert after==m.migrate_quote_state(after,new)
 result=dict(status='PASS',checks=['atomic rollback on halfway event conflict','one-time idempotent calibration and preserved later funded trades','all historical seeds and old events unchanged','legacy seed guard passes','only market quote bases changed; asset/offer/book preservation','old volume samples archived; quote migration idempotent'],real_assets_written=False)
 (P/'migration-regression.json').write_text(json.dumps(result,indent=2)+'\n','utf8');print(json.dumps(result))

if __name__=='__main__':main()
